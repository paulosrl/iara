# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**IARA** (Inteligência Analítica) is a local conversational assistant and PDF report generator built with Streamlit. It connects to **LM Studio** (local LLM runtime) or **Azure OpenAI** for inference, using the OpenAI SDK pointed at the appropriate endpoint.

## Running the Application

```bash
# Recommended (Docker - rebuilds and restarts cleanly)
bash restart.sh

# Docker manual
docker compose up --build -d
docker compose logs -f

# Local development (without Docker)
pip install -r requirements.txt
streamlit run frontend/iara.py
```

## Verification

```bash
docker ps                                               # Container status
curl http://localhost:8501/_stcore/health               # App health (real healthcheck)
docker exec -it streamlit-llm-chat tesseract --version  # OCR check
docker compose logs -f                                  # Live logs
```

## Architecture

```
frontend/iara.py       ← Streamlit UI, session state, theming, chat loop
backend/core.py        ← PDF/OCR extraction, LLM calls, model metadata, context limits
backend/providers.py   ← LM Studio discovery + Azure OpenAI client (all connection logic)
logger_config.py       ← Centralized RotatingFileHandler (5MB, 3 backups, configurable via LOG_FILE env)
```

### backend/core.py — Processamento

Constants:
- `CHAT_MAX_CHARS = 20_000` — Max characters sent as document context per chat message
- `SUMMARY_MAX_CHARS = 20_000` — Max characters sent for report generation
- `CHAT_HISTORY_TURNS = 6` — Number of past messages included per request

Key functions:
- `get_model_info(model_id, provider)` — Returns metadata (score, context window, features) for homologated models. Score defines UI ordering (lower = higher priority).
- `extract_text_from_pdf(file_bytes)` — Sequential PyPDF2 extraction + parallel Tesseract OCR fallback for pages with < 10 chars
- `generate_summary(client, model, text)` — Returns a streaming response for real-time Markdown report display
- `chat_response(client, model, messages)` — Returns `(stream, start_time)` tuple

### backend/providers.py — Conexão

- `discover_local_models()` — Tests all LM Studio URLs in parallel, returns first responding `(url, models_list)`
- `get_local_client(url)` — Creates an OpenAI client pointed at LM Studio
- `get_azure_client()` — Thread-safe singleton Azure OpenAI client (double-checked locking)
- `list_azure_deployments()` — Returns deployments from `.env` vars

### frontend/iara.py — UI

- All state in `st.session_state`: `theme_mode`, `messages`, `full_text`, `document_summary`, `last_file`, `proc_time`, `active_url`, `provider`
- `_get_local_models_cached()` — `@st.cache_resource` wrapper over `discover_local_models()`
- "Limpar Chat" clears all session keys: messages, full_text, document_summary, last_file, proc_time
- Theming via CSS injection: "Deep Sea PRO" (dark) / "Coastal Blue PRO" (light)

### LM Studio Connection

`providers.py` tests these URLs in parallel (timeout 0.8s each), returns first to respond:

```python
[
    os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1"),
    "http://localhost:1234/v1",
    "http://127.0.0.1:1234/v1",
    "http://172.17.0.1:1234/v1",
    "http://172.18.0.1:1234/v1",
    "http://172.20.0.1:1234/v1",
    "http://172.26.240.1:1234/v1",  # WSL-specific gateway
    "http://192.168.1.1:1234/v1",
]
```

LM Studio must be running on the host with at least one model loaded.

## Environment

- `.env` — See `.env.example` for all variables (LM Studio + Azure OpenAI + logging)
- Docker container name: `streamlit-llm-chat`
- Exposed port: `8501`

## Homologated Models (GPU 8GB)

Defined in `backend/core.py:get_model_info()`. Score determines UI display order (lower = first):

| Score | Model ID pattern | Params | Notes |
|-------|-----------------|--------|-------|
| 0 | Azure GPT family | Cloud | Azure provider, always top |
| 1 | `qwen2.5-7b` | 7B | Best overall for 8GB GPU |
| 2 | `qwen2.5-coder-3b` | 3B | Fast, structured analysis |
| 3 | `qwen2.5-3b` | 3B | Ultra-fast chat |
| 4 | `phi-4-mini` / `phi-4-mini-reasoning` | 3.8B | Reasoning flag auto-detected |
| 5 | `mistral-7b` | 7B | Stable, good inference speed |
| 6 | `gemma-3n` | 4B | Efficient new architecture |
| 7 | `gemma-3-4b` | 4B | Gemma 3 standard |
| 8 | `gemma-4-e4b` | 4.5B | Use for vision/multimodal |
| 9 | `gemma-4-e2b` | 2B | Fastest, when speed is critical |

Models with score > 10 are filtered out of the UI. Non-homologated models get score 20–21 (generic inference by size substring).

**LM Studio tip:** Set Context Length to 8192 for the `qwen2.5-7b-instruct-1m` model — the 1M context window allocates VRAM proportionally, leaving little room for fast inference.

## CI/CD

GitHub Actions (`.github/workflows/docker-build.yml`) triggers on push/PR to `main`:
1. Builds Docker image
2. Starts container and polls `/_stcore/health` up to 15 times (2s interval)
3. Prints container logs on failure
