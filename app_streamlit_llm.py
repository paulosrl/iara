import streamlit as st
from openai import OpenAI
import time
import os
from core import get_model_info, extract_text_from_pdf, generate_summary, chat_response

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
    
    default_url = os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1")
    try:
        tmp_client = OpenAI(base_url=default_url, api_key="not-needed")
        available_models = [m.id for m in tmp_client.models.list().data if "embed" not in m.id.lower()]
        available_models = sorted(available_models, key=lambda x: get_model_info(x)["score"])
    except:
        available_models = ["Erro ao conectar"]

    selected_model = st.selectbox("IA para análise:", available_models)
    m_info = get_model_info(selected_model)
    st.info(f"**📋 Detalhes:**\n- **Tamanho:** {m_info['size']}\n- **Corte:** {m_info['cutoff']}\n- **Contexto:** {m_info['context']}\n- **Sobre:** {m_info['desc']}")

    st.divider()
    st.subheader("📁 Envio de Documento")
    uploaded_file = st.file_uploader("Arquivos TXT ou PDF", type=["txt", "pdf"], help="200 MB por arquivo")

    extracted_text = None
    if uploaded_file:
        if uploaded_file.type == "text/plain":
            extracted_text = uploaded_file.read().decode("utf-8")
            st.session_state.pages_data = [{"page": 1, "content": extracted_text}]
        else:
            with st.spinner("🧜‍♀️ Extraindo texto (OCR Paralelo)..."):
                pages, full_text = extract_text_from_pdf(uploaded_file.read())
                st.session_state.pages_data = pages
                extracted_text = full_text
        st.success(f"✅ {uploaded_file.name} carregado!")

    st.divider()
    with st.expander("🌐 Servidor", expanded=False):
        lm_studio_url = st.text_input("URL", value=default_url)

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

if extracted_text:
    # Gestão de Resumo
    if "document_summary" not in st.session_state or st.session_state.get("last_file") != uploaded_file.name:
        st.session_state.document_summary = None
        st.session_state.last_file = uploaded_file.name

    if st.session_state.document_summary is None:
        try:
            summary_client = OpenAI(base_url=lm_studio_url, api_key="not-needed")
            st.session_state.document_summary = generate_summary(summary_client, selected_model, extracted_text)
        except Exception as e:
            st.session_state.document_summary = f"⚠️ Erro no resumo: {e}"

    summary_label = "🧜‍♀️Resumo do documento ✅" if st.session_state.document_summary else "⏳ Processando resumo..."
    with st.expander(summary_label, expanded=True):
        st.markdown(st.session_state.document_summary or "Processando...")

    st.divider()
    st.subheader("💬 Chat com o Documento")

    # Exibição das Mensagens
    for msg in st.session_state.messages:
        avatar = "🧜‍♀️" if msg["role"] == "assistant" else "🏊"
        with st.chat_message(msg["role"], avatar=avatar):
            if msg.get("reasoning"):
                with st.expander("💭 Pensamento"): st.write(msg["reasoning"])
            st.markdown(msg["content"])
            if msg.get("metrics"):
                m = msg["metrics"]
                st.caption(f"⏱️ {m['time']:.2f}s | 📤 {m['prompt']} | 📥 {m['completion']}")

    # Input do Chat
    if user_input := st.chat_input("Faça uma pergunta sobre o documento..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🏊"): st.markdown(user_input)

        try:
            client = OpenAI(base_url=lm_studio_url, api_key="not-needed")
            sys_prompt = f"Você é a IARA. Responda baseado no DOCUMENTO:\n\n{extracted_text}\n\nREGRAS:\n1. Comece com 'Resumo Executivo'.\n2. Responda apenas sobre o documento."
            
            full_messages = [{"role": "system", "content": sys_prompt}]
            for m in st.session_state.messages[-5:]: # Janela de 5 mensagens
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
                st.rerun() # Refresh para carregar métricas corretamente no caption

        except Exception as e:
            st.error(f"Erro na conexão: {e}")

else:
    st.info("👈 **Comece carregando um arquivo na barra lateral**")

st.divider()
st.caption("🧜‍♀️ **IARA** | Assistente conversacional local com GPU")
