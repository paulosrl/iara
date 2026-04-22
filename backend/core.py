import PyPDF2
import io
import pytesseract
import time
import os
from pdf2image import convert_from_bytes
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from logger_config import get_logger

logger = get_logger("backend-core")

# Desabilita proxies para conexões locais com o LM Studio
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

def get_model_info(model_id, provider="local"):
    """Retorna metadados e especificações técnicas estruturadas para filtragem avançada."""
    mid = model_id.lower()
    info = {
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
        "score": 99
    }
    
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
            "score": 0 # Altíssima prioridade
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
            info.update({
                "desc": "Azure OpenAI GPT-3.5: Rápido, eficiente e ideal para a maioria das tarefas.",
            })
        else:
            info.update({
                "desc": "Modelo Enterprise hospedado no Azure OpenAI.",
            })
        return info

    # Configurações para modelos homologados IARA (Top 2 - Elite 8GB)
    # Foco total em Llama 3.1 (Cérebro) e Gemma 4 (Visão/Velocidade)
    if any(x in mid for x in ["llama-4-8b", "llama4-8b", "llama-3.1-8b"]):
        info.update({"size": "≈ 8B", "cutoff": "2024/2025", "cutoff_year": 2025, "context": "128k", "context_val": 128000, "think": False, "vision": False, "fabricante": "Meta / Llama", "size_class": "Medium", "params": "8B", "context_detail": "128k tokens (Nativo)", "desc": "Meta Llama: O melhor cérebro analítico para relatórios complexos e extração de fatos.", "score": 1})
    elif any(x in mid for x in ["gemma-4-e4b", "gemma4-e4b"]):
        info.update({"size": "≈ 4.5B", "cutoff": "Abril 2026", "cutoff_year": 2026, "context": "128k", "context_val": 128000, "think": False, "vision": True, "fabricante": "Google DeepMind", "size_class": "Small+", "params": "4.5B", "context_detail": "128k tokens (Multimodal)", "desc": "Google Gemma 4: Especialista em visão e multimodalidade, ideal para documentos com imagens e gráficos.", "score": 2})
    
    # Inferência genérica baseada no ID do modelo
    elif info["score"] == 99:
        if any(x in mid for x in ["2b", "3b", "tiny"]):
            info["size"], info["score"] = "Compacto (1-3B)", 20
        elif any(x in mid for x in ["7b", "8b", "9b"]):
            info["size"], info["score"] = "Médio (7-9B)", 21
            
    return info

def process_single_page(page_num, page_obj, file_bytes):
    """Realiza a extração de texto ou OCR de uma única página do PDF."""
    try:
        start_page = time.time()
        text = page_obj.extract_text()
        # Se o texto for insuficiente, tenta OCR
        if not text or len(text.strip()) < 10:
            # Note: poppler-utils necessário para convert_from_bytes
            # Adicionado dpi=150 para equilíbrio entre velocidade e precisão
            images = convert_from_bytes(file_bytes, first_page=page_num + 1, last_page=page_num + 1, fmt="jpeg", dpi=150)
            if images:
                # Mudança para --psm 3 (mais rápido que o psm 1 em muitos casos)
                text = pytesseract.image_to_string(images[0], lang='por+eng', config='--psm 3')
        
        duration = time.time() - start_page
        logger.info(f"Página {page_num + 1} processada em {duration:.2f}s")
        return {"page": page_num + 1, "content": text or ""}
    except Exception as e:
        logger.error(f"Erro no processamento da página {page_num + 1}: {e}")
        return {"page": page_num + 1, "content": f"[Erro no OCR da Página {page_num + 1}: {str(e)}]"}

def extract_text_from_pdf(file_bytes):
    """Coordena a extração de texto de PDFs usando processamento paralelo para OCR."""
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    # Extrair objetos de página sequencialmente — PyPDF2 não é thread-safe
    pages = list(pdf_reader.pages)
    num_pages = len(pages)
    pages_results = []

    # Aumentar workers para aproveitar melhor CPUs multicore (comum em setups com GPU)
    workers = min(8, num_pages) if num_pages <= 50 else 4
    start_total = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(process_single_page, i, pages[i], file_bytes) for i in range(num_pages)]
        for future in futures:
            pages_results.append(future.result())
    
    pages_results.sort(key=lambda x: x["page"])
    full_text = ""
    for p in pages_results:
        full_text += f"\n\n## 📄 Página {p['page']}\n\n{p['content']}"
    
    logger.info(f"Extração total concluída em {time.time() - start_total:.2f}s para {num_pages} páginas.")
    return pages_results, full_text

def generate_summary(client, model, text):
    """Solicita ao LLM a geração de um relatório executivo de alta densidade analítica."""
    max_chars = 40000 # Reduzido de 60k para 40k para maior velocidade
    text_to_summarize = text[:max_chars]
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
{text_to_summarize}
---
"""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Atue como um assistente de análise de documentos. Responda em Português do Brasil utilizando formatação em Markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, # Mais focado e menos criativo
            max_tokens=2500
        )
        return resp.choices[0].message.content
    except Exception as e:
        error_msg = str(e).lower()
        if "max_completion_tokens" in error_msg or "temperature" in error_msg:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Atue como um assistente de análise de documentos. Responda em Português do Brasil utilizando formatação em Markdown."},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=2500
                )
                return resp.choices[0].message.content
            except Exception as e2:
                logger.error(f"Falha na geração do resumo (fallback): {e2}")
                raise e2
        logger.error(f"Falha na geração do resumo: {e}")
        raise e

def chat_response(client, model, messages, temperature=0.7, max_tokens=4096):
    """Envia o histórico de chat e retorna um stream de tokens."""
    start_time = time.time()
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        logger.info(f"API Stream iniciado: {model} em {time.time() - start_time:.2f}s")
        return stream, start_time
    except Exception as e:
        error_msg = str(e).lower()
        if "max_completion_tokens" in error_msg or "temperature" in error_msg:
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_completion_tokens=max_tokens,
                    stream=True
                )
                logger.info(f"API Stream (fallback) iniciado: {model} em {time.time() - start_time:.2f}s")
                return stream, start_time
            except Exception as e2:
                logger.error(f"Erro na API de Chat (fallback): {e2}")
                raise e2
        logger.error(f"Erro na API de Chat: {e}")
        raise e
