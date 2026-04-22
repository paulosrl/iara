"""Núcleo de processamento da IARA.

Responsabilidades:
  - Metadados de modelos homologados (get_model_info)
  - Extração de texto de PDFs com fallback para OCR (extract_text_from_pdf)
  - Geração de relatório executivo via LLM (generate_summary)
  - Chat em streaming com histórico (chat_response)

Dependências externas: PyPDF2, pdf2image, pytesseract, openai.
Não importa nada de backend.providers — este módulo é independente de provedor.
"""

import io
import os
import time
from concurrent.futures import ThreadPoolExecutor

import PyPDF2
import pytesseract
from pdf2image import convert_from_bytes

from logger_config import get_logger

logger = get_logger("backend-core")

# Desabilita proxies para que conexões locais com o LM Studio não sejam redirecionadas
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

# Limites de contexto enviado ao LLM (em caracteres)
CHAT_MAX_CHARS = 20_000     # Contexto máximo no chat interativo (~5k tokens)
SUMMARY_MAX_CHARS = 20_000  # Contexto máximo na geração de relatório (~5k tokens)
CHAT_HISTORY_TURNS = 6      # Número de mensagens do histórico enviadas por rodada


# ---------------------------------------------------------------------------
# Metadados de modelos
# ---------------------------------------------------------------------------

def get_model_info(model_id: str, provider: str = "local") -> dict:
    """Retorna metadados e especificações técnicas do modelo para filtragem na UI.

    Args:
        model_id: Identificador do modelo (ex: "llama-4-8b", "gpt-4o").
        provider: "local" para LM Studio ou "azure" para Azure OpenAI.

    Returns:
        Dicionário com chaves: size, cutoff, cutoff_year, desc, context,
        context_val, think, vision, fabricante, size_class, params,
        context_detail, score.
        O campo `score` define a ordem de exibição (menor = maior prioridade).
    """
    mid = model_id.lower()

    # Valores padrão para modelos não homologados
    info: dict = {
        "size": "Não identificado",
        "cutoff": "2025",
        "cutoff_year": 2025,
        "desc": "Informações não disponíveis.",
        "context": "128k",
        "context_val": 131072,
        "think": False,
        "vision": False,
        "fabricante": "Desconhecido",
        "size_class": "N/A",
        "params": "Desconhecido",
        "context_detail": "128k (Padrão)",
        "score": 99,
    }

    # --- Provedor Azure: metadados genéricos por família GPT ---
    if provider == "azure":
        info.update({
            "size": "Cloud",
            "cutoff": "2024+",
            "cutoff_year": 2024,
            "context": "128k+",
            "context_val": 128000,
            "fabricante": "Microsoft Azure (OpenAI)",
            "size_class": "Enterprise",
            "params": "Cloud",
            "context_detail": "Gerenciado pela Nuvem",
            "score": 0,  # Prioridade máxima na ordenação
        })
        if "gpt-5" in mid or "gpt5" in mid:
            info.update({
                "desc": "Azure OpenAI GPT-5: A próxima geração de inteligência, raciocínio avançado e análise profunda.",
                "vision": True,
            })
        elif "gpt-4" in mid or "gpt4" in mid:
            info.update({
                "desc": "Azure OpenAI GPT-4: Inteligência de classe mundial para tarefas complexas.",
                "vision": True,
            })
        elif "gpt-35" in mid or "gpt35" in mid:
            info.update({"desc": "Azure OpenAI GPT-3.5: Rápido, eficiente e ideal para a maioria das tarefas."})
        else:
            info.update({"desc": "Modelo Enterprise hospedado no Azure OpenAI."})
        return info

    # --- Modelos homologados locais para GPU 8GB ---
    # Ordenados por score: menor = maior prioridade na UI

    if "qwen2.5-7b" in mid or "qwen2.5_7b" in mid:
        context_1m = "1m" in mid
        info.update({
            "size": "≈ 7B",
            "cutoff": "2024",
            "cutoff_year": 2024,
            "context": "1M" if context_1m else "128k",
            "context_val": 1_048_576 if context_1m else 131072,
            "think": False,
            "vision": False,
            "fabricante": "Alibaba / Qwen",
            "size_class": "Medium",
            "params": "7B",
            "context_detail": "1M tokens (Janela Estendida)" if context_1m else "128k tokens (Nativo)",
            "desc": "Qwen 2.5 7B: Melhor custo-benefício para GPU 8GB — rápido, preciso e excelente em português.",
            "score": 1,
        })
    elif "qwen2.5-coder-3b" in mid or "qwen2.5_coder_3b" in mid:
        info.update({
            "size": "≈ 3B",
            "cutoff": "2024",
            "cutoff_year": 2024,
            "context": "32k",
            "context_val": 32768,
            "think": False,
            "vision": False,
            "fabricante": "Alibaba / Qwen",
            "size_class": "Small",
            "params": "3B",
            "context_detail": "32k tokens (Nativo)",
            "desc": "Qwen 2.5 Coder 3B: Ultra-rápido. Focado em código, mas funciona bem para análise estruturada.",
            "score": 2,
        })
    elif "qwen2.5-3b" in mid or "qwen2.5_3b" in mid:
        info.update({
            "size": "≈ 3B",
            "cutoff": "2024",
            "cutoff_year": 2024,
            "context": "32k",
            "context_val": 32768,
            "think": False,
            "vision": False,
            "fabricante": "Alibaba / Qwen",
            "size_class": "Small",
            "params": "3B",
            "context_detail": "32k tokens (Nativo)",
            "desc": "Qwen 2.5 3B: Ultra-rápido para respostas imediatas. Ideal para chats curtos e perguntas objetivas.",
            "score": 3,
        })
    elif "phi-4-mini" in mid or "phi4-mini" in mid:
        is_reasoning = "reasoning" in mid
        info.update({
            "size": "≈ 3.8B",
            "cutoff": "2024",
            "cutoff_year": 2024,
            "context": "128k",
            "context_val": 131072,
            "think": is_reasoning,
            "vision": False,
            "fabricante": "Microsoft",
            "size_class": "Small+",
            "params": "3.8B",
            "context_detail": "128k tokens (Nativo)",
            "desc": (
                "Phi-4 Mini Reasoning: Raciocínio profundo ativado — ideal para análises complexas e dedução lógica."
                if is_reasoning else
                "Phi-4 Mini: Raciocínio analítico superior ao tamanho — excelente para relatórios estruturados."
            ),
            "score": 4,
        })
    elif "mistral-7b" in mid or "mistral_7b" in mid:
        info.update({
            "size": "≈ 7B",
            "cutoff": "2023",
            "cutoff_year": 2023,
            "context": "32k",
            "context_val": 32768,
            "think": False,
            "vision": False,
            "fabricante": "Mistral AI",
            "size_class": "Medium",
            "params": "7B",
            "context_detail": "32k tokens (Nativo)",
            "desc": "Mistral 7B: Sólido e estável para análise de documentos. Boa velocidade de inferência.",
            "score": 5,
        })
    elif "gemma-3n" in mid or "gemma3n" in mid:
        info.update({
            "size": "≈ 4B",
            "cutoff": "2025",
            "cutoff_year": 2025,
            "context": "128k",
            "context_val": 131072,
            "think": False,
            "vision": False,
            "fabricante": "Google DeepMind",
            "size_class": "Small+",
            "params": "4B",
            "context_detail": "128k tokens (Nativo)",
            "desc": "Gemma 3n 4B: Arquitetura eficiente de nova geração — boa velocidade com qualidade analítica sólida.",
            "score": 6,
        })
    elif any(x in mid for x in ["gemma-3-4b", "gemma3-4b", "gemma-3-1b", "gemma3-1b"]):
        info.update({
            "size": "≈ 4B",
            "cutoff": "2025",
            "cutoff_year": 2025,
            "context": "128k",
            "context_val": 131072,
            "think": False,
            "vision": False,
            "fabricante": "Google DeepMind",
            "size_class": "Small+",
            "params": "4B",
            "context_detail": "128k tokens (Nativo)",
            "desc": "Gemma 3 4B: Versão eficiente da família Gemma para GPU 8GB.",
            "score": 7,
        })
    elif any(x in mid for x in ["gemma-4-e2b", "gemma4-e2b"]):
        info.update({
            "size": "≈ 2B",
            "cutoff": "Abril 2026",
            "cutoff_year": 2026,
            "context": "128k",
            "context_val": 128000,
            "think": False,
            "vision": True,
            "fabricante": "Google DeepMind",
            "size_class": "Small",
            "params": "2B",
            "context_detail": "128k tokens (Multimodal)",
            "desc": "Gemma 4 2B: O mais rápido da lista — ótimo para respostas imediatas quando velocidade é prioridade.",
            "score": 9,
        })
    elif any(x in mid for x in ["gemma-4-e4b", "gemma4-e4b"]):
        info.update({
            "size": "≈ 4.5B",
            "cutoff": "Abril 2026",
            "cutoff_year": 2026,
            "context": "128k",
            "context_val": 128000,
            "think": False,
            "vision": True,
            "fabricante": "Google DeepMind",
            "size_class": "Small+",
            "params": "4.5B",
            "context_detail": "128k tokens (Multimodal)",
            "desc": "Gemma 4 4.5B: Use quando precisar de visão/multimodalidade. Para texto puro, prefira Qwen 2.5.",
            "score": 8,
        })
    # --- Inferência genérica por tamanho para modelos não homologados ---
    elif any(x in mid for x in ["2b", "3b", "tiny"]):
        info["size"] = "Compacto (1-3B)"
        info["score"] = 20
    elif any(x in mid for x in ["7b", "8b", "9b"]):
        info["size"] = "Médio (7-9B)"
        info["score"] = 21

    return info


# ---------------------------------------------------------------------------
# Extração de texto de PDF
# ---------------------------------------------------------------------------

def _run_ocr(file_bytes: bytes, page_num: int) -> str:
    """Executa OCR em uma página específica via pdf2image + Tesseract.

    Usa first_page/last_page para isolar a página sem compartilhar estado,
    tornando a função segura para execução paralela em threads.

    Args:
        file_bytes: Conteúdo bruto do PDF.
        page_num: Índice zero-based da página.

    Returns:
        Texto extraído pelo OCR, ou string vazia se não houver imagem.
    """
    images = convert_from_bytes(
        file_bytes,
        first_page=page_num + 1,
        last_page=page_num + 1,
        fmt="jpeg",
        dpi=150,  # Equilíbrio entre velocidade e precisão
    )
    if not images:
        return ""
    return pytesseract.image_to_string(images[0], lang='por+eng', config='--psm 3')


def extract_text_from_pdf(file_bytes: bytes) -> tuple[list[dict], str]:
    """Extrai texto de todas as páginas de um PDF.

    Estratégia em dois passos:
      1. Leitura de texto direta via PyPDF2 — sequencial (não é thread-safe).
      2. OCR via Tesseract — paralelizado apenas nas páginas sem texto suficiente.

    Args:
        file_bytes: Conteúdo bruto do arquivo PDF.

    Returns:
        Tupla (pages_results, full_text) onde:
          - pages_results: lista de dicts {"page": int, "content": str}
          - full_text: string única com todo o conteúdo formatado em Markdown
    """
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    pages = list(pdf_reader.pages)
    num_pages = len(pages)

    # Passo 1: extração sequencial (PyPDF2 não é thread-safe)
    raw_texts: list[str] = []
    for page_obj in pages:
        try:
            raw_texts.append(page_obj.extract_text() or "")
        except Exception as e:
            logger.warning(f"Falha ao extrair texto de página: {e}")
            raw_texts.append("")

    # Passo 2: OCR paralelo apenas nas páginas sem texto suficiente (< 10 chars)
    needs_ocr = [i for i, t in enumerate(raw_texts) if len(t.strip()) < 10]
    if needs_ocr:
        start_ocr = time.time()
        with ThreadPoolExecutor(max_workers=min(8, len(needs_ocr))) as executor:
            futures = {executor.submit(_run_ocr, file_bytes, i): i for i in needs_ocr}
            for future, page_num in futures.items():
                try:
                    raw_texts[page_num] = future.result()
                except Exception as e:
                    logger.error(f"Erro no OCR da página {page_num + 1}: {e}")
                    raw_texts[page_num] = f"[Erro no OCR da Página {page_num + 1}: {e}]"
        logger.info(f"OCR de {len(needs_ocr)} páginas em {time.time() - start_ocr:.2f}s")

    pages_results = [{"page": i + 1, "content": raw_texts[i]} for i in range(num_pages)]
    full_text = "".join(
        f"\n\n## 📄 Página {p['page']}\n\n{p['content']}"
        for p in pages_results
    )
    logger.info(f"Extração concluída: {num_pages} páginas.")
    return pages_results, full_text


# ---------------------------------------------------------------------------
# Geração de relatório executivo
# ---------------------------------------------------------------------------

def generate_summary(client, model: str, text: str):
    """Gera um relatório executivo em Markdown a partir do texto do documento.

    Retorna um stream de chunks (igual ao chat_response) para que o frontend
    possa exibir o texto em tempo real com st.write_stream, eliminando o
    spinner bloqueante.

    Usa os primeiros SUMMARY_MAX_CHARS caracteres para controlar o tamanho
    do contexto enviado ao LLM. Inclui fallback automático para modelos que
    não aceitam o parâmetro `temperature` (ex: GPT-5 via Azure).

    Args:
        client: Cliente OpenAI (local ou Azure).
        model: ID do modelo/deployment.
        text: Texto completo extraído do documento.

    Returns:
        Stream de chunks da API OpenAI.

    Raises:
        Exception: Repassa a exceção original se ambas as tentativas falharem.
    """
    prompt = f"""Por favor, atue como um analista de dados e extraia as informações principais do documento fornecido abaixo.
Crie um resumo executivo claro e objetivo.

Diretrizes:
- Mantenha o foco nos fatos essenciais.
- Extraia dados relevantes como nomes, valores, datas e conclusões.
- Utilize um tom profissional e analítico.

Por favor, utilize a seguinte estrutura em Markdown:
# 📑 Relatório Executivo
> [Breve resumo do propósito do documento]

## 🔍 Pontos Críticos e Fatos Relevantes
- (Fato 1: Detalhe)
- (Fato 2: Detalhe)

## ⚖️ Conclusão
- [Status atual e recomendação final]

Documento para análise:
---
{text[:SUMMARY_MAX_CHARS]}
---
"""
    system_msg = {
        "role": "system",
        "content": "Atue como um assistente de análise de documentos. Responda em Português do Brasil utilizando formatação em Markdown.",
    }
    try:
        return client.chat.completions.create(
            model=model,
            messages=[system_msg, {"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2500,
            stream=True,
        )
    except Exception as e:
        if "max_completion_tokens" in str(e).lower() or "temperature" in str(e).lower():
            try:
                return client.chat.completions.create(
                    model=model,
                    messages=[system_msg, {"role": "user", "content": prompt}],
                    max_completion_tokens=2500,
                    stream=True,
                )
            except Exception as e2:
                logger.error(f"Falha na geração do resumo (fallback): {e2}")
                raise e2
        logger.error(f"Falha na geração do resumo: {e}")
        raise e


# ---------------------------------------------------------------------------
# Chat em streaming
# ---------------------------------------------------------------------------

def chat_response(client, model: str, messages: list, temperature: float = 0.7, max_tokens: int = 1024):
    """Envia o histórico de mensagens e retorna um stream de tokens.

    Inclui fallback para modelos que não aceitam `temperature` (ex: GPT-5 Azure).

    Args:
        client: Cliente OpenAI (local ou Azure).
        model: ID do modelo/deployment.
        messages: Histórico de mensagens no formato [{"role": ..., "content": ...}].
        temperature: Criatividade do modelo (0.0–1.0). Padrão: 0.7.
        max_tokens: Limite de tokens na resposta. Padrão: 1024.

    Returns:
        Tupla (stream, start_time) onde stream é o iterável de chunks.

    Raises:
        Exception: Repassa a exceção original se ambas as tentativas falharem.
    """
    start_time = time.time()
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        logger.info(f"Stream iniciado: {model} em {time.time() - start_time:.2f}s")
        return stream, start_time
    except Exception as e:
        if "max_completion_tokens" in str(e).lower() or "temperature" in str(e).lower():
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_completion_tokens=max_tokens,
                    stream=True,
                )
                logger.info(f"Stream (fallback) iniciado: {model} em {time.time() - start_time:.2f}s")
                return stream, start_time
            except Exception as e2:
                logger.error(f"Erro no stream (fallback): {e2}")
                raise e2
        logger.error(f"Erro no stream: {e}")
        raise e
