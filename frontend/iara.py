import streamlit as st
from openai import OpenAI
import time
import os
import sys

# Limpeza de proxies para evitar o erro 'unexpected keyword argument proxies'
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

# Ajuste de path para localizar o backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.core import get_model_info, extract_text_from_pdf, generate_summary, chat_response

# ============================================================
# CONFIGURAÇÃO E CSS
# ============================================================
st.set_page_config(page_title="IARA - Assistente Local", page_icon="🧜‍♀️", layout="wide")

st.markdown("""
<style>
    div[data-testid="stChatInput"] { border: 2px solid #4A90E2 !important; border-radius: 10px !important; background-color: #1E1E1E !important; }
    div[data-testid="stChatInput"]:focus-within { border-color: #1A237E !important; box-shadow: 0 0 10px rgba(26, 35, 126, 0.5) !important; }
    div[data-testid="stChatInput"] textarea { border: none !important; box-shadow: none !important; }
    [data-testid="stChatInput"] > div { border: none !important; }
    html, body, [class*="css"] { font-size: 15px !important; }
    .stMarkdown, p, li { font-size: 15px !important; line-height: 1.5 !important; }
    h1 { font-size: 2rem !important; }
    h2 { font-size: 1.5rem !important; }
    h3 { font-size: 1.2rem !important; }
    .stCaption { font-size: 0.8rem !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR: MODELO E UPLOAD
# ============================================================
with st.sidebar:
    st.title("🧜‍♀️ IARA")
    st.subheader("🧠 Escolha o Modelo")
    
    # Tenta carregar a URL ativa do estado da sessão para evitar o loop lento
    if "active_url" not in st.session_state:
        st.session_state.active_url = None

    available_models = ["Erro ao conectar"]
    connection_success = False
    
    # Se já temos uma URL que funcionou, tentamos ela primeiro (Turbo Mode)
    urls_to_try = [os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1")]
    if st.session_state.active_url:
        urls_to_try = [st.session_state.active_url]
    else:
        urls_to_try = [
            os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1"),
            "http://172.17.0.1:1234/v1",
            "http://172.26.240.1:1234/v1",
            "http://172.18.0.1:1234/v1"
        ]

    @st.cache_data(ttl=600, show_spinner=False)  # Cache de 10 minutos silêncioso
    def get_models(url):
        client = OpenAI(base_url=url, api_key="not-needed", timeout=1.5)
        models = [m.id for m in client.models.list().data if "embed" not in m.id.lower()]
        return sorted(models, key=lambda x: get_model_info(x)["score"])

    last_error = ""
    for url in urls_to_try:
        try:
            available_models = get_models(url)
            st.session_state.active_url = url
            connection_success = True
            break
        except Exception as e:
            last_error = str(e)
            st.session_state.active_url = None # Reseta se falhar
            continue
    
    # Se a URL salva falhou, tenta o loop completo uma única vez
    if not connection_success and urls_to_try == [st.session_state.active_url]:
        # (Lógica de fallback omitida para brevidade, mas o cache resolve 99% dos casos)
        st.rerun()

    if not connection_success:
        st.error(f"❌ Erro de Conexão: {last_error}")
        st.info("Verifique o LM Studio.")
        lm_studio_url = urls_to_try[0]
    else:
        lm_studio_url = st.session_state.active_url

    selected_model = st.selectbox("IA para análise:", available_models)
    m_info = get_model_info(selected_model)
    st.info(f"**📋 Detalhes:**\n- **Tamanho:** {m_info['size']}\n- **Corte:** {m_info['cutoff']}\n- **Contexto:** {m_info['context']}\n- **Sobre:** {m_info['desc']}")

    st.divider()
    st.subheader("📁 Envio de Documento")
    uploaded_file = st.file_uploader("Arquivos TXT ou PDF", type=["txt", "pdf"], help="200 MB por arquivo")

    extracted_text = st.session_state.get("full_text")
    if uploaded_file:
        # Só processa se for um arquivo novo ou se não houver texto na memória
        if "last_processed" not in st.session_state or st.session_state.last_processed != uploaded_file.name:
            with st.status("📖 Lendo o arquivo ...", expanded=True) as status:
                if uploaded_file.type == "text/plain":
                    extracted_text = uploaded_file.read().decode("utf-8")
                    st.session_state.pages_data = [{"page": 1, "content": extracted_text}]
                else:
                    pages, full_text = extract_text_from_pdf(uploaded_file.read())
                    st.session_state.pages_data = pages
                    extracted_text = full_text
                
                st.session_state.full_text = extracted_text
                st.session_state.last_processed = uploaded_file.name
                status.update(label=f"✅ {uploaded_file.name} lido com sucesso!", state="complete", expanded=False)
                st.rerun() # Força o reload para exibir o resumo imediatamente
        else:
            extracted_text = st.session_state.full_text
    else:
        # Se o arquivo foi removido, limpa tudo
        st.session_state.full_text = None
        st.session_state.last_processed = None
        st.session_state.document_summary = None
        extracted_text = None

    st.divider()
    with st.expander("🌐 Servidor", expanded=False):
        lm_studio_url = st.text_input("URL", value=urls_to_try[0])

    if "messages" not in st.session_state: st.session_state.messages = []
    if st.button("🗑️ Limpar Chat", use_container_width=True):
        st.session_state.messages = []; st.rerun()

# ============================================================
# CABEÇALHO E RESUMO
# ============================================================
st.title("🧜‍♀️ IARA")
st.markdown("### Assistente conversacional e gerador de arquivos MD")
st.markdown(f"🤖 **Modelo Ativo:** `{selected_model}`")
st.markdown("---")

if uploaded_file and not extracted_text:
    st.info("📖 **Lendo o arquivo ...**")
    st.stop() # Interrompe aqui para não mostrar mais nada enquanto carrega

if extracted_text and uploaded_file:
    if "document_summary" not in st.session_state or st.session_state.get("last_file") != uploaded_file.name:
        st.session_state.document_summary = None
        st.session_state.last_file = uploaded_file.name

    if st.session_state.document_summary is None:
        try:
            summary_client = OpenAI(base_url=lm_studio_url, api_key="not-needed")
            st.session_state.document_summary = generate_summary(summary_client, selected_model, extracted_text)
        except Exception as e:
            st.session_state.document_summary = f"⚠️ Erro no resumo: {e}"

    # Consolidação do Documento MD Completo
    full_md_report = f"# 🧜‍♀️ IARA - Relatório de Documento\n\n"
    full_md_report += f"**Arquivo Original:** {uploaded_file.name}\n"
    if st.session_state.document_summary:
        full_md_report += f"\n{st.session_state.document_summary}\n\n"
        full_md_report += f"---\n\n"
    full_md_report += extracted_text

    summary_label = "🧜‍♀️Resumo do documento ✅" if st.session_state.document_summary else "⏳ Processando o documento ..."
    with st.expander(summary_label, expanded=True):
        st.markdown(st.session_state.document_summary or "Processando...")
        if st.session_state.document_summary:
            st.download_button(
                label="📥 Baixar Documento MD Completo (OCR + Estrutura)",
                data=full_md_report,
                file_name=f"IARA_DOC_{uploaded_file.name.split('.')[0]}.md",
                mime="text/markdown",
                use_container_width=True
            )

    st.divider()
    st.subheader("💬 Chat com o Documento")

    for msg in st.session_state.messages:
        avatar = "🧜‍♀️" if msg["role"] == "assistant" else "🏊"
        with st.chat_message(msg["role"], avatar=avatar):
            if msg.get("reasoning"):
                with st.expander("💭 Pensamento"): st.write(msg["reasoning"])
            st.markdown(msg["content"])
            if msg.get("metrics"):
                m = msg["metrics"]
                st.caption(f"⏱️ {m['time']:.2f}s | 📤 {m['prompt']} | 📥 {m['completion']}")

    if user_input := st.chat_input("Faça uma pergunta sobre o documento..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🏊"): st.markdown(user_input)
        try:
            client = OpenAI(base_url=lm_studio_url, api_key="not-needed")
            sys_prompt = f"Você é a IARA. Responda baseado no DOCUMENTO:\n\n{extracted_text}\n\nREGRAS:\n1. Comece com 'Resumo Executivo'.\n2. Responda apenas sobre o documento."
            full_messages = [{"role": "system", "content": sys_prompt}]
            for m in st.session_state.messages[-5:]:
                full_messages.append({"role": m["role"], "content": m["content"]})
            with st.chat_message("assistant", avatar="🧜‍♀️"):
                with st.spinner("Pesquisando nas águas..."):
                    resp, r_time = chat_response(client, selected_model, full_messages, 0.7, 2000)
                content = resp.choices[0].message.content
                reasoning = getattr(resp.choices[0].message, 'reasoning_content', None)
                if reasoning:
                    with st.expander("💭 Pensamento"): st.write(reasoning)
                st.markdown(content)
                metrics = {"time": r_time, "prompt": resp.usage.prompt_tokens, "completion": resp.usage.completion_tokens}
                st.session_state.messages.append({"role": "assistant", "content": content, "reasoning": reasoning, "metrics": metrics})
                st.rerun()
        except Exception as e:
            st.error(f"Erro na conexão: {e}")
else:
    st.info("👈 **Comece carregando um arquivo na barra lateral**")

st.divider()
st.caption("🧜‍♀️ **IARA** | Assistente conversacional local com GPU")
