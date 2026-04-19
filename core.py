import PyPDF2
import io
import pytesseract
from pdf2image import convert_from_bytes
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
import time

def get_model_info(model_id):
    """Retorna metadados precisos baseados na tabela oficial da IARA."""
    mid = model_id.lower()
    info = {
        "size": "Não identificado",
        "cutoff": "Desconhecida",
        "desc": "Informações não disponíveis.",
        "context": "Desconhecido",
        "score": 99
    }
    
    if "qwen3-8b" in mid:
        info.update({"size": "≈ 8.2B", "cutoff": "2025", "context": "32k - 131k", "desc": "Alibaba Qwen3: Forte em raciocínio e código.", "score": 4})
    elif "qwen3-4b-thinking" in mid:
        info.update({"size": "≈ 4B", "cutoff": "2025", "context": "~262k", "desc": "Alibaba Qwen3 (Thinking): Exibe cadeia de raciocínio explícita.", "score": 3})
    elif "qwen3-4b" in mid:
        info.update({"size": "≈ 4B", "cutoff": "Abril 2025", "context": "32k - 131k", "desc": "Alibaba Qwen3: Bom custo-benefício e multilíngue.", "score": 2})
    elif "gemma-4-e2b" in mid:
        info.update({"size": "≈ 2.3B/5.1B", "cutoff": "Abril 2026", "context": "128k", "desc": "Google Gemma 4: Leve, multimodal (texto/img/audio).", "score": 1})
    elif "gemma-4-e4b" in mid:
        info.update({"size": "≈ 4.5B/8B", "cutoff": "2026", "context": "128k", "desc": "Google Gemma 4: Intermediário, foco em agentes e código.", "score": 2})
    elif "mistral-7b-instruct-v0.2" in mid:
        info.update({"size": "≈ 7.3B", "cutoff": "Jan 2024", "context": "~32k", "desc": "Mistral AI: Otimizado para seguir instruções.", "score": 4})
    
    elif info["score"] == 99:
        if any(x in mid for x in ["2b", "3b", "tiny"]):
            info["size"], info["score"] = "Pequeno (1-3B)", 10
        elif any(x in mid for x in ["7b", "8b", "9b"]):
            info["size"], info["score"] = "Médio (7-9B)", 11
            
    return info

def process_single_page(page_num, page_obj, file_bytes):
    """Processa uma única página do PDF (Extração direta ou OCR)."""
    try:
        text = page_obj.extract_text()
        # Se a página parece ser uma imagem (pouco texto), roda OCR
        if not text or len(text.strip()) < 10:
            images = convert_from_bytes(file_bytes, first_page=page_num + 1, last_page=page_num + 1)
            if images:
                text = pytesseract.image_to_string(images[0], lang='por+eng')
        return {"page": page_num + 1, "content": text or ""}
    except Exception as e:
        return {"page": page_num + 1, "content": f"Erro na página {page_num + 1}: {str(e)}"}

def extract_text_from_pdf(file_bytes):
    """Extrai texto de um PDF usando processamento paralelo para OCR."""
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    num_pages = len(pdf_reader.pages)
    
    pages_results = []
    # Usando ThreadPoolExecutor para paralelizar o OCR das páginas
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_single_page, i, pdf_reader.pages[i], file_bytes) for i in range(num_pages)]
        for future in futures:
            pages_results.append(future.result())
    
    # Ordena resultados para garantir a ordem correta das páginas
    pages_results.sort(key=lambda x: x["page"])
    
    full_text = ""
    for p in pages_results:
        full_text += f"\n--- Página {p['page']} ---\n{p['content']}"
        
    return pages_results, full_text

def generate_summary(client, model, text):
    """Gera o resumo executivo via LLM."""
    max_chars = 100000 
    text_to_summarize = text[:max_chars]
    
    prompt = f"""Você é a IARA. Sua missão é criar um resumo EXECUTIVO, DENSO e CONCISO do documento abaixo.
    
    ESTRUTURA OBRIGATÓRIA:
    1. Comece com um cabeçalho "### 📑 Resumo Executivo" e forneça uma síntese de no máximo 3 linhas.
    2. Depois, use "### 🔍 Detalhes Principais" e use tópicos (bullet points) para cobrir o documento inteiro de forma sintetizada.
    
    DIRETRIZES:
    - Vá direto ao ponto, frases curtas, sem verbosidade.
    - NÃO use saudações ou apresentações.
    - Responda em Português (Brasil).
    
    DOCUMENTO:
    ---
    {text_to_summarize}
    ---
    """
    
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2500
    )
    return resp.choices[0].message.content

def chat_response(client, model, messages, temperature, max_tokens):
    """Executa a chamada de chat e retorna resposta e métricas."""
    start_time = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    end_time = time.time()
    
    return response, end_time - start_time
