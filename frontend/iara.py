"""Interface principal da IARA — Streamlit UI.

Responsabilidades deste módulo:
  - Renderizar tema, sidebar e área de chat
  - Delegar processamento de documento a backend.core
  - Delegar conexão/descoberta de modelos a backend.providers
  - Manter estado da sessão via st.session_state
"""

import os
import sys
import time

import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.core import (
    CHAT_MAX_CHARS,
    CHAT_HISTORY_TURNS,
    chat_response,
    extract_text_from_pdf,
    generate_summary,
    get_model_info,
)
from backend.providers import (
    discover_local_models,
    get_azure_client,
    get_local_client,
    list_azure_deployments,
)
from logger_config import get_logger

logger = get_logger("frontend-iara")

# ---------------------------------------------------------------------------
# Configuração inicial
# ---------------------------------------------------------------------------

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Escuro"

st.set_page_config(page_title="IARA - Inteligência Analítica", page_icon="🧜‍♀️", layout="wide")

with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #1E40AF; margin-bottom: 20px;'>🧜‍♀️ IARA</h1>", unsafe_allow_html=True)

    theme_label = "🌙 Ativar Modo Escuro" if st.session_state.theme_mode == "Claro" else "☀️ Ativar Modo Claro"
    theme_sel = st.toggle(theme_label, value=(st.session_state.theme_mode == "Claro"))

    if theme_sel and st.session_state.theme_mode == "Escuro":
        st.session_state.theme_mode = "Claro"
        st.rerun()
    elif not theme_sel and st.session_state.theme_mode == "Claro":
        st.session_state.theme_mode = "Escuro"
        st.rerun()

    st.divider()

# ---------------------------------------------------------------------------
# Tema
# ---------------------------------------------------------------------------

if st.session_state.theme_mode == "Escuro":
    c_bg, c_side = "#0B1117", "#161B22"
    c_text, c_accent = "#F0F6FC", "#1F6FEB"
    c_secondary, c_border = "#21262D", "#1F6FEB"
    c_shadow = "rgba(0,0,0,0.6)"
else:
    c_bg, c_side = "#ECF2F9", "#D1E3F8"
    c_text = "#051124"
    c_accent = "#001A33"
    c_secondary = "#FFFFFF"
    c_border = "#001A33"
    c_shadow = "rgba(0,26,51,0.2)"

st.markdown(f"""
<style>
    :root {{ --primary-color: {c_accent}; }}

    [data-testid="stSidebarUserContent"] {{ padding-top: 2rem !important; }}

    .stApp {{ background-color: {c_bg}; color: {c_text} !important; }}

    section[data-testid="stSidebar"] {{
        background-color: {c_side} !important;
        border-right: 3px solid {c_border} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 0.5rem !important; }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p {{ color: {c_text} !important; }}
    [data-testid="stSidebar"] [data-testid="stCheckbox"] {{
        display: flex; justify-content: flex-start !important;
        width: 100%; margin-top: 0px !important; padding-left: 10px;
    }}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
        text-align: left !important; font-weight: 600 !important;
    }}

    h1, h2, h3, h4, h5, h6, b, strong {{
        color: {c_accent} !important; font-family: 'Inter', sans-serif;
    }}
    .stMarkdown p, .stMarkdown li, .stMarkdown span {{
        color: {c_text} !important; font-weight: 500;
    }}

    .stButton button, .stDownloadButton button {{
        background-color: {c_accent} !important; color: white !important;
        border: 2px solid {c_accent} !important; font-weight: 600 !important;
        margin-top: 10px !important; box-shadow: 0 4px 10px {c_shadow};
    }}
    .stButton button p, .stDownloadButton button p {{ color: white !important; }}
    .stButton button:hover, .stDownloadButton button:hover {{
        opacity: 0.9 !important; color: white !important;
    }}

    div[data-testid="stFileUploader"] {{
        background-color: {c_secondary} !important; padding: 12px;
        border-radius: 12px; border: 2px dashed {c_border} !important;
        box-shadow: 0 4px 6px {c_shadow};
    }}
    div[data-testid="stFileUploader"] button {{
        border: 2px solid {c_accent} !important;
        color: {c_accent} !important; background-color: transparent !important;
    }}
    div[data-testid="stFileUploader"] button:hover {{
        background-color: {c_accent} !important; color: white !important;
    }}
    div[data-testid="stFileUploader"] section {{ background-color: transparent !important; }}
    div[data-testid="stFileUploader"] label,
    div[data-testid="stFileUploader"] span,
    div[data-testid="stFileUploader"] small {{
        color: {c_text} !important; font-weight: 600 !important; opacity: 1 !important;
    }}

    .model-details {{
        background-color: {c_secondary} !important; padding: 12px !important;
        border-radius: 15px !important; border: 2px solid {c_border} !important;
        color: {c_text} !important; margin-top: 10px !important;
        box-shadow: 0 8px 30px {c_shadow};
    }}
    .model-details b {{ color: {c_accent} !important; font-size: 0.9rem; }}

    .stChatMessage {{
        background-color: {c_secondary} !important; border: 1px solid {c_border} !important;
        border-radius: 20px !important; box-shadow: 0 2px 10px {c_shadow}; padding: 15px !important;
    }}

    div[data-baseweb="select"] > div {{
        background-color: {c_secondary} !important;
        border: 2px solid {c_border} !important; color: {c_text} !important;
    }}
    div[data-baseweb="select"] [data-testid="stMarkdownContainer"] p {{ color: {c_text} !important; }}
    ul[role="listbox"] {{
        background-color: {c_secondary} !important; border: 1px solid {c_border} !important;
    }}
    li[role="option"] {{ color: {c_text} !important; background-color: {c_secondary} !important; }}
    li[role="option"]:hover {{ background-color: {c_side} !important; }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Estado da sessão
# ---------------------------------------------------------------------------

if "active_url" not in st.session_state:
    st.session_state.active_url = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "full_text" not in st.session_state:
    st.session_state.full_text = None

# ---------------------------------------------------------------------------
# Descoberta de modelos (cacheada por sessão)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _get_local_models_cached() -> tuple[str | None, list[str]]:
    return discover_local_models()

# ---------------------------------------------------------------------------
# Sidebar — configurações
# ---------------------------------------------------------------------------

with st.sidebar:
    st.subheader("📑 Documento")
    uploaded_file = st.file_uploader(
        "Arraste um PDF ou TXT", type=["txt", "pdf"], label_visibility="collapsed"
    )

    st.subheader("🤖 Modelo")
    provider = st.radio(
        "Provedor:", ["Local (LM Studio)", "Nuvem (Azure OpenAI)"],
        horizontal=True, label_visibility="collapsed",
    )
    st.session_state.provider = "azure" if "Azure" in provider else "local"

    if st.session_state.provider == "local":
        active_url, raw_models = _get_local_models_cached()
    else:
        try:
            raw_models = list_azure_deployments()
            active_url = "azure_api"
        except Exception as e:
            st.error(f"Erro no Azure: {e}")
            raw_models = []
            active_url = None

    if active_url:
        st.session_state.active_url = active_url

        filtered_models = [
            m for m in raw_models
            if get_model_info(m, provider=st.session_state.provider)["score"] <= 10
        ]

        if not filtered_models:
            st.warning("Nenhum modelo compatível.")
            selected_model = None
        else:
            selected_model = st.selectbox("IA para análise:", filtered_models, label_visibility="collapsed")
            m_info = get_model_info(selected_model, provider=st.session_state.provider)
            st.markdown(f"""
                <div class="model-details">
                    <b>📋 Ficha Técnica:</b><br>
                    <b>Fabricante:</b> {m_info.get('fabricante')}<br>
                    <b>Modelo:</b> {selected_model}<br>
                    <b>Classe:</b> {m_info.get('size_class')} ({m_info.get('params')})<br>
                    <b>Janela:</b> {m_info.get('context_detail')}<br>
                    <b>Corte:</b> {m_info.get('cutoff')}<br>
                    <b>Resumo:</b> {m_info.get('desc')}
                </div>
            """, unsafe_allow_html=True)
    else:
        if st.session_state.provider == "local":
            st.error("❌ LM Studio não detectado.")
            st.info("Inicie o servidor local no LM Studio para prosseguir.")
        else:
            st.error("❌ Falha na conexão com Azure.")
            st.info("Verifique as variáveis de ambiente no arquivo .env.")
        selected_model = None

    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)

    if st.button("🗑️ Limpar Chat", use_container_width=True):
        for key in ("messages", "full_text", "document_summary", "last_file", "proc_time"):
            st.session_state.pop(key, None)
        st.rerun()

    if st.button("🔄 Resetar Rede", use_container_width=True):
        st.cache_resource.clear()
        st.session_state.active_url = None
        st.rerun()

# ---------------------------------------------------------------------------
# Área principal
# ---------------------------------------------------------------------------

st.markdown(f"<h1 style='color: {c_accent};'>🧜‍♀️ IARA</h1>", unsafe_allow_html=True)
st.markdown("##### Assistente conversacional de PDFs e gerador de relatórios")

if selected_model:
    st.markdown(f"🤖 **Modelo Ativo:** `{selected_model}`")

# Detecta troca de arquivo e reseta o estado
if uploaded_file and st.session_state.get("last_file") != uploaded_file.name:
    st.session_state.full_text = None
    st.session_state.document_summary = None
    st.session_state.messages = []
    st.session_state.last_file = uploaded_file.name

# Extração do documento
if uploaded_file and not st.session_state.get("full_text"):
    st.info("📖 **Lendo documento...**")
    with st.status("🔍 Extraindo conteúdo...", expanded=True) as status:
        try:
            if uploaded_file.type == "text/plain":
                st.session_state.full_text = uploaded_file.read().decode("utf-8")
            else:
                _, full_text = extract_text_from_pdf(uploaded_file.read())
                st.session_state.full_text = full_text
            status.update(label="✅ Conteúdo extraído com sucesso!", state="complete")
            st.rerun()
        except Exception as e:
            st.error(f"Erro na extração: {e}")

if st.session_state.get("full_text"):
    # Aviso quando o documento excede o limite de contexto do chat
    doc_len = len(st.session_state.full_text)
    if doc_len > CHAT_MAX_CHARS:
        pct = CHAT_MAX_CHARS * 100 // doc_len
        st.warning(
            f"⚠️ Documento grande ({doc_len:,} caracteres). "
            f"O chat utilizará os primeiros {CHAT_MAX_CHARS:,} caracteres ({pct}% do total)."
        )

    if not st.session_state.active_url:
        st.warning("⚠️ Conecte ao provedor para habilitar a análise.")
    else:
        if not st.session_state.get("document_summary"):
            st.info("📄 Documento carregado. Selecione o modelo na barra lateral e gere o relatório.")
            if st.button(f"🚀 Gerar Relatório Executivo com {selected_model}", use_container_width=True, type="primary"):
                try:
                    client = (
                        get_azure_client()
                        if st.session_state.provider == "azure"
                        else get_local_client(st.session_state.active_url)
                    )
                    start_proc = time.time()
                    stream = generate_summary(client, selected_model, st.session_state.full_text)
                    with st.empty():
                        st.session_state.document_summary = st.write_stream(
                            chunk.choices[0].delta.content or ""
                            for chunk in stream
                            if chunk.choices and chunk.choices[0].delta.content
                        )
                    st.session_state.proc_time = time.time() - start_proc
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro na análise: {e}")

    if st.session_state.get("document_summary"):
        with st.expander("📑 Relatório Executivo", expanded=True):
            st.markdown(st.session_state.document_summary)
            if "proc_time" in st.session_state:
                st.caption(f"⏱️ Tempo de processamento: {st.session_state.proc_time:.2f}s")
            file_name_export = st.session_state.get("last_file", "documento")
            full_md = (
                f"# Relatório IARA: {file_name_export}\n\n"
                f"{st.session_state.document_summary}\n\n---\n\n"
                f"{st.session_state.full_text}"
            )
            st.download_button(
                "📥 Exportar Relatório (.md)",
                data=full_md,
                file_name="IARA_Relatorio.md",
                mime="text/markdown",
                use_container_width=True,
            )

        st.divider()
        st.markdown(f"<h3 style='color: {c_accent};'>💬 Pesquisa e Chat com o Documento</h3>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color: #8B949E; margin-bottom: 20px;'>O relatório acima é o resumo padrão. "
            "Use a caixa abaixo para <b>fazer perguntas específicas</b> sobre o documento.</p>",
            unsafe_allow_html=True,
        )

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar="🧜‍♀️" if msg["role"] == "assistant" else "🏊"):
                st.markdown(msg["content"])

        user_input = st.chat_input("Pesquise no documento (ex: Quais são os riscos apontados?)...")
        if user_input and st.session_state.active_url:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user", avatar="🏊"):
                st.markdown(user_input)

            try:
                client = (
                    get_azure_client()
                    if st.session_state.provider == "azure"
                    else get_local_client(st.session_state.active_url)
                )
                context = st.session_state.full_text[:CHAT_MAX_CHARS]
                msgs = [
                    {"role": "system", "content": f"Você é a IARA. Responda baseado no DOCUMENTO:\n{context}"},
                    *st.session_state.messages[-CHAT_HISTORY_TURNS:],
                ]
                with st.chat_message("assistant", avatar="🧜‍♀️"):
                    stream, _ = chat_response(client, selected_model, msgs)
                    content = st.write_stream(
                        chunk.choices[0].delta.content or ""
                        for chunk in stream
                        if chunk.choices and chunk.choices[0].delta.content
                    )
                    st.session_state.messages.append({"role": "assistant", "content": content})
            except Exception as e:
                st.error(f"Erro no chat: {e}")

st.divider()
st.caption("🧜‍♀️ IARA v2.4 | Inteligência Analítica | 2026")
