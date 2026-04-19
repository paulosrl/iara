# 🧜‍♀️ IARA - Inteligência Artificial Regional de Análise

**IARA** é um assistente conversacional local e gerador de relatórios técnicos, otimizado para o processamento de grandes volumes de documentos (PDF/TXT) via modelos de linguagem executados localmente no LM Studio.

## 🚀 Funcionalidades Principais

- **Análise Contextual de Documentos**: Suporte a PDFs (com OCR automático) e arquivos de texto de até 200MB.
- **Relatórios Executivos**: Geração automática de sínteses técnicas de alta densidade em formato Markdown.
- **Descoberta Inteligente de Servidor**: Localização automática de instâncias do LM Studio na rede local ou em containers Docker.
- **Segurança e Estabilidade**: Sistema de logs detalhado e travas de segurança para evitar crashes em caso de desconexão.
- **Alta Janela de Contexto**: Otimizado para modelos Qwen3, Gemma 4 e Mistral com processamento de até 80k caracteres de contexto.

## 🧠 Modelos Homologados

| Modelo | Especialidade | Contexto | Origem |
| :--- | :--- | :--- | :--- |
| **Qwen3-8B** | Raciocínio Geral / Código | 131k | Alibaba |
| **Qwen3-4B-Thinking** | Lógica Complexa (Chain-of-Thought) | 262k | Alibaba |
| **Gemma-4-E2B** | Multimodal / Leve | 128k | Google |
| **Mistral-7B** | Seguimento de Instruções | 32k | Mistral |

## 🛠️ Instalação e Uso

### Pré-requisitos
- Python 3.10+
- LM Studio ativo com o Server Local em execução.
- Tesseract OCR (para leitura de imagens).

### Execução via Script (Recomendado)
Para rodar ou reiniciar o ambiente Docker completo:
```bash
bash restart.sh
```

### Execução Manual (Local)
1. Instalar dependências: `pip install -r requirements.txt`
2. Rodar interface: `streamlit run frontend/iara.py`

## 📁 Estrutura do Projeto

- `frontend/`: Interface de usuário em Streamlit.
- `backend/`: Lógica de processamento de documentos e integração com APIs.
- `logger_config.py`: Gestão centralizada de logs e diagnósticos.
- `app_errors.log`: Registro de eventos e erros em tempo real (gerado automaticamente).

---
*IARA - Transformando dados brutos em conhecimento estratégico local.*
