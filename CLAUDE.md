# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**IARA** (Inteligência Analítica) is a local conversational assistant and technical report generator built with Streamlit + FastAPI-style Python backend. It connects to **LM Studio** (local LLM runtime) for inference — it uses the OpenAI SDK but points to a local endpoint, not the OpenAI API.

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
docker ps                                              # Container status
curl http://localhost:8501                             # App health
docker exec -it streamlit-llm-chat tesseract --version # OCR check
docker compose logs -f                                 # Live logs
```

## Architecture

```
frontend/iara.py   ← Streamlit UI, session state, theming, chat loop
backend/core.py    ← PDF/OCR extraction, LLM calls, model metadata DB
logger_config.py   ← Centralized RotatingFileHandler (5MB, 3 backups)
```

### Key Backend Functions (`backend/core.py`)

- `get_model_info(model_id)` — Returns metadata (context window, cutoff date, features) for homologated models
- `extract_text_from_pdf(file_bytes)` — Parallel page extraction via `ThreadPoolExecutor(4)`; falls back to Tesseract OCR if PyPDF2 yields < 10 chars
- `generate_summary(client, model, text)` — Generates an executive Markdown report
- `chat_response(client, model, messages)` — Streams LLM response, logs timing metrics

### Key Frontend Patterns (`frontend/iara.py`)

- All UI state lives in `st.session_state` (theme, messages, extracted text, selected model)
- Theming is done via CSS injection: "Deep Sea PRO" (dark) / "Coastal Blue PRO" (light)
- Model discovery calls multiple fallback URLs to handle Docker, WSL, and bare-metal setups

### LM Studio Connection

The app tries these URLs in order until one responds:

```python
[
    os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1"),
    "http://localhost:1234/v1",
    "http://127.0.0.1:1234/v1",
    "http://172.17.0.1:1234/v1",  # ... Docker bridge variants
    "http://172.26.240.1:1234/v1", # WSL-specific
]
```

LM Studio must be running on the host with a model loaded before starting the app.

## Environment

- `.env` — Only variable needed: `LM_STUDIO_URL=http://host.docker.internal:1234/v1`
- Docker container name: `streamlit-llm-chat`
- Exposed port: `8501`

## Homologated Models

Seven models are formally supported with hardcoded metadata in `backend/core.py:get_model_info()`:
`qwen3-8b`, `qwen3-4b-thinking`, `qwen3-4b`, `llama-4-8b`, `gemma-4-e4b`, `gemma-4-e2b`, `mistral-7b`.
Adding a new model requires updating that function's lookup dict.

## CI/CD

GitHub Actions (`.github/workflows/docker-build.yml`) triggers on push/PR to `main`: builds the Docker image and verifies the container starts successfully.
