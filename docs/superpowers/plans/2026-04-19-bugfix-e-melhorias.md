# Bugfix e Melhorias IARA v2.3 — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir todos os bugs críticos e aplicar as melhorias de qualidade identificadas na análise do codebase IARA v2.2.

**Architecture:** Todas as mudanças são cirúrgicas — sem refatorações estruturais. Os dois arquivos principais (`frontend/iara.py`, `backend/core.py`) recebem correções isoladas. O `Dockerfile` recebe `curl`. Um `.env.example` é adicionado.

**Tech Stack:** Python 3.12, Streamlit 1.32.2, PyPDF2, pytesseract, ThreadPoolExecutor, OpenAI SDK (local), Docker.

---

## Mapa de Arquivos

| Arquivo | Mudanças |
|---|---|
| `Dockerfile` | Adicionar `curl` ao apt-get |
| `backend/core.py` | Fix thread safety PyPDF2; fix bare except; fix memória OCR |
| `frontend/iara.py` | Fix get_models_cached (executor shutdown); fix bare except; streaming no chat; contexto de chat; CSS classe interna |
| `.env.example` | Criar arquivo novo |

---

## Task 1: Adicionar `curl` ao Dockerfile

**Files:**
- Modify: `Dockerfile:12-18`

- [ ] **Step 1: Editar Dockerfile para incluir curl**

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    libtesseract-dev \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 2: Verificar que o healthcheck funciona**

```bash
docker compose up --build -d
docker inspect streamlit-llm-chat --format='{{json .State.Health.Status}}'
# Esperado: "healthy" após ~40s
```

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "fix: adiciona curl ao Dockerfile para healthcheck funcionar"
```

---

## Task 2: Fix bare `except` em `get_models_cached`

**Files:**
- Modify: `frontend/iara.py:227`

- [ ] **Step 1: Substituir `except:` por `except Exception:`**

Linha atual:
```python
        except: return None
```
Substituir por:
```python
        except Exception:
            return None
```

- [ ] **Step 2: Commit**

```bash
git add frontend/iara.py
git commit -m "fix: substituir bare except por except Exception em get_models_cached"
```

---

## Task 3: Fix `get_models_cached` — retornar no primeiro URL disponível

**Files:**
- Modify: `frontend/iara.py:229-234`

**Problema:** O `return res` dentro de `with ThreadPoolExecutor` dispara `shutdown(wait=True)`, fazendo o executor aguardar TODOS os 8 futures, mesmo após encontrar o primeiro URL que responde.

- [ ] **Step 1: Substituir o loop `as_completed` para cancelar futures pendentes**

Código atual:
```python
    with ThreadPoolExecutor(max_workers=len(urls)) as ex:
        futures = {ex.submit(check, u): u for u in urls}
        for f in as_completed(futures):
            res = f.result()
            if res: return res
    return None, ["Sem Conexão"]
```

Código novo:
```python
    with ThreadPoolExecutor(max_workers=len(urls)) as ex:
        futures = {ex.submit(check, u): u for u in urls}
        result = None
        for f in as_completed(futures):
            res = f.result()
            if res and result is None:
                result = res
                # Cancelar futures ainda pendentes
                for pending_f in futures:
                    pending_f.cancel()
                break
        # shutdown(wait=True) acontece aqui ao sair do with,
        # mas futures cancelados retornam imediatamente
    return result if result else (None, ["Sem Conexão"])
```

- [ ] **Step 2: Verificar comportamento**

Iniciar a app com LM Studio ativo e observar nos logs que a conexão é estabelecida sem aguardar todos os timeouts:
```bash
streamlit run frontend/iara.py
# A sidebar deve mostrar o modelo disponível em < 2s
```

- [ ] **Step 3: Commit**

```bash
git add frontend/iara.py
git commit -m "fix: get_models_cached retorna no primeiro URL disponível e cancela futures pendentes"
```

---

## Task 4: Fix thread safety do PyPDF2

**Files:**
- Modify: `backend/core.py:79-94`

**Problema:** `pdf_reader.pages[i]` é acessado de múltiplas threads. O `PdfReader` não é thread-safe e mantém estado interno durante leitura de páginas.

- [ ] **Step 1: Extrair todos os objetos de página sequencialmente antes de paralelizar**

Código atual:
```python
def extract_text_from_pdf(file_bytes):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    num_pages = len(pdf_reader.pages)
    pages_results = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_single_page, i, pdf_reader.pages[i], file_bytes) for i in range(num_pages)]
        for future in futures:
            pages_results.append(future.result())
```

Código novo:
```python
def extract_text_from_pdf(file_bytes):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    # Extrair objetos de página sequencialmente (PyPDF2 não é thread-safe)
    pages = list(pdf_reader.pages)
    num_pages = len(pages)
    pages_results = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_single_page, i, pages[i], file_bytes) for i in range(num_pages)]
        for future in futures:
            pages_results.append(future.result())
```

- [ ] **Step 2: Verificar que PDFs grandes ainda processam corretamente**

Testar com um PDF de múltiplas páginas via interface Streamlit.

- [ ] **Step 3: Commit**

```bash
git add backend/core.py
git commit -m "fix: extrair páginas do PyPDF2 sequencialmente antes de paralelizar (thread safety)"
```

---

## Task 5: Reduzir uso de memória no OCR paralelo

**Files:**
- Modify: `backend/core.py:63-77`

**Problema:** Cada worker recebe `file_bytes` (o PDF completo) e re-decodifica só para converter uma página. Para PDFs grandes com muitos workers, isso multiplica o uso de memória.

**Solução:** Usar `convert_from_bytes` com `output_folder` temporário ou limitar workers proporcionalmente ao tamanho do arquivo. A solução mais simples e segura é reduzir `max_workers` dinamicamente para PDFs grandes.

- [ ] **Step 1: Ajustar `max_workers` com base no número de páginas**

Código atual:
```python
    with ThreadPoolExecutor(max_workers=4) as executor:
```

Código novo:
```python
    # Limitar workers: máx 4, mas não mais que o número de páginas
    # Para PDFs grandes, mantém máx 2 workers para controlar memória
    workers = min(4, num_pages) if num_pages <= 20 else 2
    with ThreadPoolExecutor(max_workers=workers) as executor:
```

- [ ] **Step 2: Commit**

```bash
git add backend/core.py
git commit -m "fix: limitar workers de OCR para PDFs grandes para controlar uso de memória"
```

---

## Task 6: Adicionar streaming real ao chat

**Files:**
- Modify: `backend/core.py:139-154`
- Modify: `frontend/iara.py:376-387`

**Problema:** `chat_response` não usa `stream=True`, então a UI fica bloqueada até a resposta completa chegar.

- [ ] **Step 1: Modificar `chat_response` para retornar um stream**

Código atual em `backend/core.py`:
```python
def chat_response(client, model, messages, temperature=0.7, max_tokens=4096):
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
```

Código novo:
```python
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
        logger.error(f"Erro na API de Chat: {e}")
        raise e
```

- [ ] **Step 2: Atualizar o frontend para consumir o stream com `st.write_stream`**

Código atual em `frontend/iara.py` (linhas ~376-387):
```python
        try:
            client = OpenAI(base_url=st.session_state.active_url, api_key="not-needed")
            sys_prompt = f"Você é a IARA. Responda baseado no DOCUMENTO:\n{st.session_state.full_text[:60000]}"
            msgs = [{"role": "system", "content": sys_prompt}] + st.session_state.messages[-3:]
            
            with st.chat_message("assistant", avatar="🧜‍♀️"):
                resp, _ = chat_response(client, selected_model, msgs)
                content = resp.choices[0].message.content
                st.markdown(content)
                st.session_state.messages.append({"role": "assistant", "content": content})
        except Exception as e:
            st.error(f"Erro no Chat: {e}")
```

Código novo:
```python
        try:
            client = OpenAI(base_url=st.session_state.active_url, api_key="not-needed")
            sys_prompt = f"Você é a IARA. Responda baseado no DOCUMENTO:\n{st.session_state.full_text[:60000]}"
            msgs = [{"role": "system", "content": sys_prompt}] + st.session_state.messages[-10:]
            
            with st.chat_message("assistant", avatar="🧜‍♀️"):
                stream, _ = chat_response(client, selected_model, msgs)
                # st.write_stream consome o gerador e exibe token a token
                content = st.write_stream(
                    chunk.choices[0].delta.content or ""
                    for chunk in stream
                    if chunk.choices and chunk.choices[0].delta.content
                )
                st.session_state.messages.append({"role": "assistant", "content": content})
        except Exception as e:
            st.error(f"Erro no Chat: {e}")
```

Nota: o histórico também foi aumentado de `-3:` para `-10:` nesta etapa.

- [ ] **Step 3: Testar streaming na interface**

Iniciar a app, carregar um documento e enviar uma pergunta. A resposta deve aparecer token a token em vez de toda de uma vez.

- [ ] **Step 4: Commit**

```bash
git add backend/core.py frontend/iara.py
git commit -m "feat: streaming real no chat (stream=True) e histórico ampliado para 10 mensagens"
```

---

## Task 7: Substituir classe CSS interna do Streamlit

**Files:**
- Modify: `frontend/iara.py:65-66`

**Problema:** `.st-emotion-cache-6qob1r` é uma classe gerada internamente que muda a cada versão do Streamlit.

- [ ] **Step 1: Remover a regra CSS frágil**

Código atual:
```css
    /* Para versões que usam containers internos específicos */
    .st-emotion-cache-6qob1r {
        padding-top: 1rem !important;
    }
```

Ação: remover completamente esse bloco. O padding já é tratado pelo seletor estável `[data-testid="stSidebarUserContent"]` na linha acima.

- [ ] **Step 2: Verificar sidebar visualmente**

Iniciar a app e confirmar que o espaçamento do topo da sidebar continua correto.

- [ ] **Step 3: Commit**

```bash
git add frontend/iara.py
git commit -m "fix: remover seletor CSS interno do Streamlit que quebra a cada atualização"
```

---

## Task 8: Criar `.env.example`

**Files:**
- Create: `.env.example`

- [ ] **Step 1: Criar o arquivo**

```bash
# .env.example — copie para .env e ajuste conforme seu ambiente
# URL do servidor LM Studio
# Docker/WSL: use host.docker.internal
# Local (sem Docker): use localhost
LM_STUDIO_URL=http://host.docker.internal:1234/v1
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: adicionar .env.example com variáveis necessárias"
```

---

## Task 9: Commit final e atualizar CHECKPOINT.md

- [ ] **Step 1: Atualizar CHECKPOINT.md para v2.3**

Registrar as correções aplicadas.

- [ ] **Step 2: Commit final**

```bash
git add CHECKPOINT.md
git commit -m "chore: IARA v2.3 — bugfixes e melhorias de qualidade certificados"
```

---

## Verificação End-to-End

Após todas as tasks:

```bash
# 1. Build Docker
bash restart.sh

# 2. Verificar healthcheck
sleep 40 && docker inspect streamlit-llm-chat --format='{{json .State.Health.Status}}'
# Esperado: "healthy"

# 3. Abrir app
curl -s http://localhost:8501 | grep -c "IARA"
# Esperado: >= 1

# 4. Logs limpos
docker compose logs --tail=20
# Sem erros de conexão

# 5. Teste manual
# - Acessar http://localhost:8501
# - Fazer upload de um PDF
# - Verificar streaming do chat (tokens aparecem progressivamente)
# - Testar o botão "Resetar Rede"
```
