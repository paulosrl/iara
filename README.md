# 🧜‍♀️ IARA - Inteligência Analítica (v2.3)

![Build Status](https://github.com/paulosrl/iara/actions/workflows/docker-build.yml/badge.svg)

**GitHub:** [paulosrl/iara](https://github.com/paulosrl/iara)

**IARA** é um assistente conversacional local e gerador de relatórios técnicos de alto impacto, otimizado para o processamento de grandes volumes de dados via modelos de linguagem executados no LM Studio.

## 🚀 Funcionalidades Principais (v2.3)

- **Streaming em Tempo Real**: Respostas exibidas token a token via API de Chat otimizada.
- **Análise Contextual de Documentos**: Suporte robusto a PDFs (com OCR Tesseract) e TXT de até 200MB.
- **Thread-Safety & Resiliência**: Extração de PDFs sequencial (PyPDF2) com workers OCR paralelos e limitados para proteção de memória.
- **Maritime PRO UI (UX-Optimized)**: Interface moderna com temas dinâmicos (**Deep Sea** e **Coastal Blue**) e histórico ampliado para 10 mensagens.
- **Descoberta Paralela**: Localização instantânea e robusta de servidores LM Studio na rede local ou Docker.
- **Janelas Expandidas**: Otimizado para modelos de nova geração (Qwen3/Gemma 4) com suporte a até 262k tokens de contexto.

## 🧠 Modelos Homologados (v2.3)

| Modelo                      | Fabricante      | Classe  | Parâmetros (Efetivos) | Máx. Janela de Contexto   | Corte (Data) |
| --------------------------- | --------------- | ------- | --------------------- | ------------------------- | ------------ |
| qwen/qwen3-4b-thinking      | Alibaba / Qwen  | Small   | 4B (Thinking/CoT)     | 262.144 (Alta Densidade)  | Junho/2025   |
| qwen/qwen3-8b               | Alibaba / Qwen  | Medium  | ≈ 8.2B                | 131.072 (YaRN)            | Maio/2025    |
| qwen/qwen3-4b               | Alibaba / Qwen  | Small   | 4B                    | 131.072 (YaRN)            | Junho/2025   |
| google/gemma-4-e4b          | Google DeepMind | Small+  | 4.5B (≈8B Embedded)   | 128.000 (Multimodal)      | Abril/2026   |
| google/gemma-4-e2b          | Google DeepMind | Small   | 2.3B (≈5.1B Embedded) | 128.000 (Multimodal)      | Abril/2026   |
| meta/llama-4-8b             | Meta / Llama 4  | Medium  | 8B                    | 128.000 (Nativo)          | Dezembro/2025|
| mistral-7b-instruct-v0.3    | Mistral AI      | Medium  | 7.3B                  | 128.000 (Otimizado)       | Jan/2025     |

## 🎨 Interface e Acessibilidade

A IARA v2.3 mantém o refinamento do sistema **Maritime PRO**, permitindo alternar entre:
- **Deep Sea (Dark)**: Fundo azul profundo (\#0B1117\) para redução de fadiga ocular em ambientes escuros.
- **Coastal Blue (Light)**: Fundo azul-gelo de alto contraste com texto Marinho Meia-Noite para máxima legibilidade diurna.

## 🛠️ Instalação e Uso

A IARA é distribuída via **Docker** para garantir que todas as dependências de OCR e processamento de PDFs funcionem perfeitamente.

### 🐳 Guia de Containers (Passo a Passo)
Para um roteiro detalhado de configuração e rede, consulte nosso:
👉 **[Guia de Containers (DOCKER_GUIDE.md)](DOCKER_GUIDE.md)**

### Inicialização Rápida (Recomendado)
Certifique-se de que o Docker esteja rodando e execute:
\\ash
bash restart.sh
\
### Execução Manual (Desenvolvimento)
1. Instale dependências: \pip install -r requirements.txt2. Configure o Tesseract OCR no seu SO.
3. Execute: \streamlit run frontend/iara.py
---
*IARA - Transformando dados em conhecimento estratégico local.*
