# 🚩 CHECKPOINT: IARA v2.3 - Bugfixes e Melhorias de Qualidade

**Data:** 19 de Abril de 2026
**Versão:** v2.3 "Stable Core"
**GitHub:** [paulosrl/iara](https://github.com/paulosrl/iara)
**Status:** 100% Estável | Bugs críticos corrigidos | Streaming ativo

Este checkpoint registra as correções aplicadas após análise estática do codebase v2.2.

## ✅ Correções Aplicadas (v2.2 → v2.3):

- **Dockerfile**: `curl` adicionado para healthcheck funcionar corretamente.
- **`get_models_cached`**: `bare except` substituído por `except Exception`; executor agora cancela futures pendentes e retorna no primeiro URL disponível.
- **`extract_text_from_pdf`**: Páginas do PyPDF2 extraídas sequencialmente antes de paralelizar (thread safety); workers limitados a 2 para PDFs grandes (controle de memória).
- **Chat**: Streaming real ativado (`stream=True`) — resposta exibida token a token via `st.write_stream`; histórico ampliado de 3 para 10 mensagens.
- **CSS**: Removido seletor interno `.st-emotion-cache-*` que quebrava a cada atualização do Streamlit.
- **`.env.example`**: Criado para documentar as variáveis de ambiente necessárias.

## 🚀 Arquivos Modificados:
1. `Dockerfile` — curl adicionado
2. `frontend/iara.py` — get_models_cached, streaming, CSS
3. `backend/core.py` — thread safety, streaming, memória OCR
4. `.env.example` — criado

## 🔒 Checkpoint Anterior:
- v2.2 "Full Resilience" — commit `bb28bc8`

---
*Certificado por: Paulo Lima + Claude Sonnet 4.6*

## 🚩 NOVO CHECKPOINT: Pré-Ajuste v2.4 (Atualizado)
**Data:** 22 de Abril de 2026
**Objetivo:** Preservar estado estável e testado da v2.3 antes do ajuste estrutural importante.
- Snapshot de memória atualizado em `MEMORY_SNAPSHOT.md`.
- Backend local (LM Studio) totalmente funcional e otimizado para GPUs de 8GB.
- Interface Azure (`ref/app_streamlit.py`) validada e testada com sucesso.
- Versão congelada, aguardando o ajuste crítico do usuário.
