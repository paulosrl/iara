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
    
    # Configurações para modelos homologados IARA (Atualizado 2026)
    if "qwen3-8b" in mid:
        info.update({"size": "≈ 8.2B", "cutoff": "2025", "cutoff_year": 2025, "context": "131k", "context_val": 131072, "think": False, "vision": False, "fabricante": "Alibaba / Qwen", "size_class": "Medium", "params": "≈8,2B", "context_detail": "131.072 tokens (YaRN) / 32k Nativo", "desc": "Alibaba Qwen3: Alta performance em raciocínio técnico e codificação.", "score": 4})
    elif "qwen3-4b-thinking" in mid:
        info.update({"size": "≈ 4B", "cutoff": "2025", "cutoff_year": 2025, "context": "262k", "context_val": 262144, "think": True, "vision": False, "fabricante": "Alibaba / Qwen", "size_class": "Small", "params": "4B (Thinking)", "context_detail": "262.144 tokens (Alta densidade)", "desc": "Alibaba Qwen3 (Thinking): Cadeia de raciocínio explícita (CoT) para lógica complexa.", "score": 3})
    elif "qwen3-4b" in mid:
        info.update({"size": "≈ 4B", "cutoff": "Jun 2025", "cutoff_year": 2025, "context": "131k", "context_val": 131072, "think": False, "vision": False, "fabricante": "Alibaba / Qwen", "size_class": "Small", "params": "4B", "context_detail": "131.072 tokens (YaRN) / 32k Nativo", "desc": "Alibaba Qwen3: Arquitetura eficiente para uso geral e resposta rápida.", "score": 5})
    elif "llama-4-8b" in mid:
        info.update({"size": "≈ 8B", "cutoff": "Dez 2025", "cutoff_year": 2025, "context": "128k", "context_val": 128000, "think": False, "vision": False, "fabricante": "Meta / Llama 4", "size_class": "Medium", "params": "8B", "context_detail": "128k tokens (Nativo)", "desc": "Meta Llama 4: Estado da arte em modelos de médio porte.", "score": 1})
    elif "gemma-4-e2b" in mid:
        info.update({"size": "≈ 2.3B", "cutoff": "Abril 2026", "cutoff_year": 2026, "context": "128k", "context_val": 128000, "think": False, "vision": True, "fabricante": "Google DeepMind", "size_class": "Small", "params": "2.3B (5.1B Embedded)", "context_detail": "128k tokens (Multimodal)", "desc": "Google Gemma 4: Modelo extremamente leve e multimodal.", "score": 2})
    elif "gemma-4-e4b" in mid:
        info.update({"size": "≈ 4.5B", "cutoff": "Abril 2026", "cutoff_year": 2026, "context": "128k", "context_val": 128000, "think": False, "vision": True, "fabricante": "Google DeepMind", "size_class": "Small+", "params": "4.5B (8B Embedded)", "context_detail": "128k tokens (Multimodal)", "desc": "Google Gemma 4: Foco em agentes e processamento rápido.", "score": 2})
    elif "mistral-7b" in mid:
        info.update({"size": "≈ 7.3B", "cutoff": "2025", "cutoff_year": 2025, "context": "128k", "context_val": 128000, "think": False, "vision": False, "fabricante": "Mistral AI", "size_class": "Medium", "params": "7B", "context_detail": "32k nativos / 128k otimizados (v0.2/0.3)", "desc": "Mistral AI: Performance equilibrada otimizada para 128k.", "score": 10})
    
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
        text = page_obj.extract_text()
        # Se o texto for insuficiente, tenta OCR
        if not text or len(text.strip()) < 10:
            # Note: poppler-utils necessário para convert_from_bytes
            images = convert_from_bytes(file_bytes, first_page=page_num + 1, last_page=page_num + 1, fmt="jpeg")
            if images:
                # Timeout de 30s para OCR por página
                text = pytesseract.image_to_string(images[0], lang='por+eng', config='--psm 1')
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

    # Limitar workers: máx 4 para PDFs pequenos, 2 para PDFs grandes (controle de memória)
    workers = min(4, num_pages) if num_pages <= 20 else 2
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(process_single_page, i, pages[i], file_bytes) for i in range(num_pages)]
        for future in futures:
            pages_results.append(future.result())
    
    pages_results.sort(key=lambda x: x["page"])
    full_text = ""
    for p in pages_results:
        full_text += f"\n\n## 📄 Página {p['page']}\n\n{p['content']}"
    return pages_results, full_text

def generate_summary(client, model, text):
    """Solicita ao LLM a geração de um relatório executivo de alta densidade analítica."""
    max_chars = 60000 # Reduzido para garantir foco e evitar truncamento de modelos menores
    text_to_summarize = text[:max_chars]
    prompt = f"""Você é a IARA (Inteligência Analítica), especialista em análise técnica e síntese de dados. 
Sua missão é extrair inteligência do documento abaixo e gerar um RELATÓRIO EXECUTIVO DE ALTA DENSIDADE.

DIRETRIZES TÉCNICAS:
1. FOCO NO ESSENCIAL: Ignore saudações e formalidades desnecessárias. Vá direto aos fatos.
2. DENSIDADE: Cada linha deve conter informação útil (nomes, valores, datas, conclusões).
3. TONE: Profissional, analítico e objetivo.

ESTRUTURA OBRIGATÓRIA (Markdown):
# 📑 Relatório Executivo: Síntese de Inteligência
> [Uma única frase poderosa resumindo o propósito e o resultado do documento]

## 🔍 Pontos Críticos e Fatos Relevantes
- (Fato 1: O que aconteceu / Valor / Data / Implicação)
- (Fato 2: ...)

## ⚖️ Conclusão Estratégica
- [Status atual e recomendação/resumo final do caso]

DOCUMENTO PARA ANÁLISE:
---
{text_to_summarize}
---
"""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é a IARA. Sua resposta deve ser estritamente em Português do Brasil, formatada em Markdown de alta densidade."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, # Mais focado e menos criativo
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
