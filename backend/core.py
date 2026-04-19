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

def get_model_info(model_id):
    """Retorna metadados e especificações técnicas do modelo selecionado."""
    mid = model_id.lower()
    info = {
        "size": "Não identificado",
        "cutoff": "Desconhecida",
        "desc": "Informações não disponíveis.",
        "context": "Desconhecido",
        "score": 99
    }
    
    # Configurações para modelos homologados IARA
    if "qwen3-8b" in mid:
        info.update({"size": "≈ 8.2B", "cutoff": "2025", "context": "32k - 131k", "desc": "Alibaba Qwen3: Alta performance em raciocínio técnico.", "score": 4})
    elif "qwen3-4b-thinking" in mid:
        info.update({"size": "≈ 4B", "cutoff": "2025", "context": "~262k", "desc": "Alibaba Qwen3 (Thinking): Cadeia de raciocínio explícita.", "score": 3})
    elif "qwen3-4b" in mid:
        info.update({"size": "≈ 4B", "cutoff": "Abril 2025", "context": "32k - 131k", "desc": "Alibaba Qwen3: Arquitetura eficiente para uso geral.", "score": 2})
    elif "gemma-4-e2b" in mid:
        info.update({"size": "≈ 2.3B/5.1B", "cutoff": "Abril 2026", "context": "128k", "desc": "Google Gemma 4: Modelo leve e multimodal.", "score": 1})
    elif "gemma-4-e4b" in mid:
        info.update({"size": "≈ 4.5B/8B", "cutoff": "2026", "context": "128k", "desc": "Google Gemma 4: Foco em agentes e automação.", "score": 2})
    elif "mistral-7b-instruct-v0.2" in mid:
        info.update({"size": "≈ 7.3B", "cutoff": "Jan 2024", "context": "~32k", "desc": "Mistral AI: Otimizado para seguir instruções complexas.", "score": 4})
    
    # Inferência genérica baseada no ID do modelo
    elif info["score"] == 99:
        if any(x in mid for x in ["2b", "3b", "tiny"]):
            info["size"], info["score"] = "Compacto (1-3B)", 10
        elif any(x in mid for x in ["7b", "8b", "9b"]):
            info["size"], info["score"] = "Médio (7-9B)", 11
            
    return info

def process_single_page(page_num, page_obj, file_bytes):
    """Realiza a extração de texto ou OCR de uma única página do PDF."""
    try:
        text = page_obj.extract_text()
        # Se o texto for insuficiente, tenta OCR
        if not text or len(text.strip()) < 10:
            images = convert_from_bytes(file_bytes, first_page=page_num + 1, last_page=page_num + 1)
            if images:
                text = pytesseract.image_to_string(images[0], lang='por+eng')
        return {"page": page_num + 1, "content": text or ""}
    except Exception as e:
        logger.error(f"Erro no processamento da página {page_num + 1}: {e}")
        return {"page": page_num + 1, "content": f"Erro na página {page_num + 1}: {str(e)}"}

def extract_text_from_pdf(file_bytes):
    """Coordena a extração de texto de PDFs usando processamento paralelo para OCR."""
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    num_pages = len(pdf_reader.pages)
    pages_results = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_single_page, i, pdf_reader.pages[i], file_bytes) for i in range(num_pages)]
        for future in futures:
            pages_results.append(future.result())
    
    pages_results.sort(key=lambda x: x["page"])
    full_text = ""
    for p in pages_results:
        full_text += f"\n\n## 📄 Página {p['page']}\n\n{p['content']}"
    return pages_results, full_text

def generate_summary(client, model, text):
    """Solicita ao LLM a geração de um relatório executivo de alta densidade."""
    max_chars = 100000 
    text_to_summarize = text[:max_chars]
    prompt = f"""Você é a IARA, uma IA especialista em análise de documentos. 
Sua missão é criar um RESUMO EXECUTIVO de ALTA DENSIDADE.

ESTRUTURA OBRIGATÓRIA (Use Markdown):
# 📑 Relatório Executivo
> Síntese analítica (máximo 4 linhas).

## 🔍 Fatos Relevantes e Pontos Chave
- Liste fatos, datas, valores e decisões.
- Ultra-conciso: um ponto por linha.

## ⚖️ Conclusão ou Status
- Resultado final ou estado presente do assunto tratado.

DOCUMENTO:
---
{text_to_summarize}
---
"""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2500
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.error(f"Falha na geração do resumo: {e}")
        raise e

def chat_response(client, model, messages, temperature=0.7, max_tokens=4096):
    """Envia o histórico de chat para o modelo local e captura métricas de tempo."""
    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        end_time = time.time()
        logger.info(f"API Call Success: {model} em {end_time - start_time:.2f}s")
        return response, end_time - start_time
    except Exception as e:
        logger.error(f"Erro na API de Chat: {e}")
        raise e
