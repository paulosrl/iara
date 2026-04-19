import streamlit as st
import os
import sys
import json
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuração de caminhos para módulos locais
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.core import get_model_info, extract_text_from_pdf, generate_summary, chat_response
from logger_config import get_logger

logger = get_logger("frontend-iara")

# --- Interface e Estilização ---
st.set_page_config(page_title="IARA - Assistente Local", page_icon="🧜‍♀️", layout="wide")

st.markdown("""
<style>
    div[data-testid="stChatInput"] { 
        border: 2px solid #4A90E2 !important; 
        border-radius: 10px !important; 
        background-color: #1E1E1E !important; 
    }
    div[data-testid="stChatInput"]:focus-within { 
        border-color: #1A237E !important; 
        box-shadow: 0 0 10px rgba(26, 35, 126, 0.5) !important; 
    }
    html, body, [class*="css"] { font-size: 15px !important; }
    .stMarkdown, p, li { font-size: 15px !important; line-height: 1.5 !important; }
    
    div.stDownloadButton > button {
        background-color: #1E3A8A !important;
        color: white !important;
        border: none !important;
        transition: 0.3s ease !important;
    }
    div.stDownloadButton > button:hover {
        background-color: #059669 !important;
        color: white !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Gestão de Estado ---
if "active_url" not in st.session_state: st.session_state.active_url = None
if "messages" not in st.session_state: st.session_state.messages = []
if "full_text" not in st.session_state: st.session_state.full_text = None

# --- Motor de Descoberta ---
def test_url(url):
    """Verifica a disponibilidade de um endpoint do LM Studio."""
    try:
        client = OpenAI(base_url=url, api_key="not-needed", timeout=1.5)
        models = client.models.list()
        ids = [m.id for m in models.data if "embed" not in m.id.lower()]
        return url, sorted(ids, key=lambda x: get_model_info(x)["score"])
    except Exception:
        return None

def get_models_turbo():
    """Descobre servidores ativos em paralelo para otimizar o carregamento inicial."""
    if st.session_state.active_url:
        res = test_url(st.session_state.active_url)
        if res: return res[0], res[1]

    urls_to_try = [
        os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1"),
        "http://172.17.0.1:1234/v1",
        "http://172.26.240.1:1234/v1",
        "http://127.0.0.1:1234/v1"
    ]
    
    with ThreadPoolExecutor(max_workers=len(urls_to_try)) as executor:
        futures = {executor.submit(test_url, url): url for url in urls_to_try}
        for future in as_completed(futures):
            result = future.result()
            if result:
                st.session_state.active_url = result[0]
                return result[0], result[1]
                
    return None, ["Erro de Conexão"]

# --- Barra Lateral ---
with st.sidebar:
    st.title("🧜‍♀️ IARA")
    st.subheader("📁 Envio de Documento")
    uploaded_file = st.file_uploader("Arquivos TXT ou PDF", type=["txt", "pdf"])
    
    st.divider()
    st.subheader("🧠 Escolha o Modelo")
    active_url, available_models = get_models_turbo()
    
    if active_url:
        selected_model = st.selectbox("IA para análise:", available_models)
        st.session_state.active_url = active_url
        m_info = get_model_info(selected_model)
        st.info(f"**📋 Detalhes:**\n- **Contexto:** {m_info['context']}\n- **Sobre:** {m_info['desc']}")
    else:
        st.error("❌ LM Studio não detectado.")
        st.info("Inicie o servidor local no LM Studio para prosseguir.")
        selected_model = None

    st.divider()
    with st.expander("🌐 Servidor", expanded=False):
        st.text_input("URL Ativa", value=st.session_state.active_url or "Buscando...", disabled=True)
        if st.button("🔄 Resetar Rede", use_container_width=True):
            st.session_state.active_url = None
            st.rerun()

    if st.button("🗑️ Limpar Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- Conteúdo Principal ---
st.title("🧜‍♀️ IARA")
st.markdown("### Assistente conversacional e gerador de relatórios técnicos")

if selected_model:
    st.markdown(f"🤖 **Modelo Ativo:** `{selected_model}`")

# Processamento do Documento
if uploaded_file and not st.session_state.full_text:
    st.info("📖 **Lendo documento...**")
    with st.status("🔍 Extraindo conteúdo...", expanded=True) as status:
        try:
            if uploaded_file.type == "text/plain":
                st.session_state.full_text = uploaded_file.read().decode("utf-8")
            else:
                _, full_text = extract_text_from_pdf(uploaded_file.read())
                st.session_state.full_text = full_text
            
            st.session_state.last_processed = uploaded_file.name
            status.update(label="✅ Conteúdo extraído com sucesso!", state="complete")
            st.rerun()
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            st.error(f"Erro ao processar arquivo: {e}")
            st.stop()

st.markdown("---")

if st.session_state.full_text and uploaded_file:
    # Geração de Resumo Executivo
    if "document_summary" not in st.session_state or st.session_state.get("last_file") != uploaded_file.name:
        try:
            client = OpenAI(base_url=st.session_state.active_url, api_key="not-needed")
            with st.spinner("🧜‍♀️ Gerando análise técnica..."):
                st.session_state.document_summary = generate_summary(client, selected_model, st.session_state.full_text)
                st.session_state.last_file = uploaded_file.name
        except Exception as e:
            logger.error(f"Erro na geração de resumo: {e}")
            st.session_state.document_summary = f"⚠️ Indisponível: {e}"

    # Painel de Resumo e Exportação
    with st.expander("📑 Relatório Executivo", expanded=True):
        st.markdown(st.session_state.document_summary)
        full_md = f"# Relatório IARA: {uploaded_file.name}\n\n{st.session_state.document_summary}\n\n---\n\n{st.session_state.full_text}"
        st.download_button("📥 Exportar Relatório (.md)", data=full_md, file_name="IARA_Relatorio.md", mime="text/markdown", use_container_width=True)

    st.divider()
    st.subheader("💬 Chat Interativo")

    # Exibição de Histórico
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🧜‍♀️" if msg["role"] == "assistant" else "🏊"):
            st.markdown(msg["content"])

    # Interface de Chat
    if not st.session_state.active_url:
        st.warning("⚠️ Conecte ao LM Studio para habilitar o chat.")
        user_input = None
    else:
        user_input = st.chat_input("Faça perguntas sobre o documento...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🏊"): 
            st.markdown(user_input)
        
        try:
            client = OpenAI(base_url=st.session_state.active_url, api_key="not-needed")
            # Janela de contexto segura (80k caracteres)
            sys_prompt = f"Você é a IARA. Responda baseado no DOCUMENTO:\n{st.session_state.full_text[:80000]}"
            msgs = [{"role": "system", "content": sys_prompt}] + st.session_state.messages[-5:]
            
            with st.chat_message("assistant", avatar="🧜‍♀️"):
                with st.spinner("Analisando contexto..."):
                    resp, duration = chat_response(client, selected_model, msgs)
                    content = resp.choices[0].message.content
                    st.markdown(content)
                    logger.info(f"Chat: Resposta gerada em {duration:.2f}s")
                    st.session_state.messages.append({"role": "assistant", "content": content})
                    st.rerun()
        except Exception as e:
            logger.error(f"Erro no chat: {e}")
            st.error(f"Falha na comunicação com a IA: {e}")
elif not uploaded_file:
    st.info("⬅️ **Aguardando o carregamento de um documento para iniciar a análise.**")

st.divider()
st.caption("🧜‍♀️ IARA | Inteligência Analítica com GPU Local")
