# 🧠 IARA Memory Snapshot - April 22, 2026

Este documento registra o estado atual do projeto IARA após os testes e preparativos com o módulo Azure e a consolidação do ambiente.

## 📌 Estado Atual
- **Versão:** v2.3 "Stable Core" (Transição para v2.4).
- **Stack:** Streamlit + Python + Docker + LM Studio (Local) + Azure OpenAI.
- **Core:** Processamento de PDF/OCR robusto, streaming de chat ativo, métricas de performance.
- **Recent Work:** 
    - Otimização de modelos para GPUs de 8GB.
    - Testes bem-sucedidos do módulo de integração com Azure OpenAI (`ref/app_streamlit.py`).
    - Consolidação da infraestrutura local vs. cloud (Azure).

## 📂 Arquivos Chave e Funções
- `frontend/iara.py`: Interface principal com temas Marítimos (Dark/Light).
- `backend/core.py`: Lógica de extração e conexão com LLMs locais.
- `ref/app_streamlit.py`: Interface base para o Azure OpenAI Chat (testada e funcional).
- `restart.sh`: Script de automação para rebuild do container Docker.

## 🎯 Próximos Passos
- Implementar o ajuste estrutural importante solicitado pelo usuário.
- Possível integração da lógica do Azure com o Core (IARA).

## 🛠️ Verificação do Sistema
- Interface Azure testada com sucesso e tratando erros via `conexao.py`.
- Docker container `streamlit-llm-chat` operacional com o setup local.
- Conexão local operando plenamente com OCR e processamento de documentos.

---
*Snapshot criado em 22/04/2026 - Versão congelada antes do ajuste.*
