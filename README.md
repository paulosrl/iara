# 🧜‍♀️ IARA - Inteligência Artificial Regional de Análise

**IARA** é um assistente conversacional local e gerador de arquivos Markdown (.md), projetado para processar documentos (PDF/TXT) usando modelos de linguagem rodando localmente via LM Studio.

## 🚀 Funcionalidades

- **Chat com Contexto de Arquivo**: Carregue PDFs ou TXTs (até 200MB) e faça perguntas sobre o conteúdo.
- **Extração de Texto (OCR)**: Suporte automático a PDFs digitalizados (imagens) através de OCR.
- **Exportação Inteligente**: Gere um arquivo `.md` consolidado com todo o texto extraído e organizado por páginas.
- **Métricas em Tempo Real**: Visualize tempo de resposta e consumo de tokens (enviados/recebidos).
- **Suporte a Chain-of-Thought (CoT)**: Interface preparada para exibir o raciocínio de modelos como Qwen Thinking e Gemma.

## 🧠 Modelos Suportados e Especificações

Aqui estão os modelos homologados e configurados na IARA:

| Modelo (ID) | Tipo / Uso principal | Parâmetros | Contexto Máximo | Data de Corte | Origem |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **qwen/qwen3-8b** | Uso geral / Código | ≈ 8.2B | 32k - 131k | 2025 | Alibaba |
| **qwen/qwen3-4b** | Compacto / Eficiente | ≈ 4B | 32k - 131k | Abril 2025 | Alibaba |
| **qwen/qwen3-4b-thinking** | Raciocínio Complexo | ≈ 4B | ~262k | 2025 | Alibaba |
| **google/gemma-4-e2b** | Leve / Multimodal | ≈ 2.3B/5.1B | 128k | Abril 2026 | Google |
| **google/gemma-4-e4b** | Intermediário / Agentes | ≈ 4.5B/8B | 128k | 2026 | Google |
| **mistral-7b-instruct-v0.2**| Instruções / Chat | ≈ 7.3B | ~32k | Jan 2024 | Mistral |

---

## 🛠️ Instalação e Execução

### Pré-requisitos
- Python 3.10+
- LM Studio rodando com o servidor local ativo (`localhost:1234`)
- Tesseract OCR (para leitura de imagens em PDF)

### Passos
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute a aplicação:
   ```bash
   streamlit run app_streamlit_llm.py
   ```

## 🌊 Sobre o Nome
Inspirada na lenda amazônica, a **IARA** (Mãe das Águas) emerge dos rios para guiar a navegação através de grandes volumes de dados e documentos, transformando informação bruta em conhecimento claro.

---
*IARA - Assistente conversacional usando modelos locais com GPU.*
