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
from ref.conexao import listar_deployments, _cliente as get_azure_client
from logger_config import get_logger

logger = get_logger("frontend-iara")

# --- Configurações Iniciais de Estado ---
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Escuro"

# --- Interface e Barra Lateral (Definição de Tema Primeiro) ---
st.set_page_config(page_title="IARA - Inteligência Analítica", page_icon="🧜‍♀️", layout="wide")

with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #1E40AF; margin-bottom: 20px;'>🧜‍♀️ IARA</h1>", unsafe_allow_html=True)
    
    # Toggle de Tema Dinâmico e Centralizado
    theme_label = "🌙 Ativar Modo Escuro" if st.session_state.theme_mode == "Claro" else "☀️ Ativar Modo Claro"
    theme_sel = st.toggle(theme_label, value=(st.session_state.theme_mode == "Claro"))
    
    if theme_sel and st.session_state.theme_mode == "Escuro":
        st.session_state.theme_mode = "Claro"
        st.rerun()
    elif not theme_sel and st.session_state.theme_mode == "Claro":
        st.session_state.theme_mode = "Escuro"
        st.rerun()
    
    st.divider()

# Definição de Paleta de Contraste Máximo
if st.session_state.theme_mode == "Escuro":
    # Deep Sea PRO (Azul Forte e Sóbrio)
    c_bg, c_side = "#0B1117", "#161B22"
    c_text, c_accent = "#F0F6FC", "#1F6FEB"
    c_secondary, c_border = "#21262D", "#1F6FEB"
    c_shadow = "rgba(0,0,0,0.6)"
else:
    # Coastal Blue PRO (Marinho Noite sobre Fundo Azulado)
    c_bg, c_side = "#ECF2F9", "#D1E3F8"
    c_text = "#051124"   
    c_accent = "#001A33" # Marinho Noite
    c_secondary = "#FFFFFF" 
    c_border = "#001A33" 
    c_shadow = "rgba(0,26,51,0.2)"

# CSS Dinâmico (Sintonia de Bordas e Espaçamento)
st.markdown(f"""
<style>
    :root {{ --primary-color: {c_accent}; }}

    /* REMOVER ESPAÇO NO TOPO DA SIDEBAR */
    [data-testid="stSidebarUserContent"] {{
        padding-top: 2rem !important;
    }}

    /* Configuração Global */
    .stApp {{
        background-color: {c_bg};
        color: {c_text} !important;
    }}

    /* Sidebar Hierarchy & Alignment */
    section[data-testid="stSidebar"] {{
        background-color: {c_side} !important;
        border-right: 3px solid {c_border} !important;
    }}
    /* Redução de Gaps entre blocos no Menu Esquerdo */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
        gap: 0.5rem !important;
    }}
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] p {{
        color: {c_text} !important;
    }}
    /* Alinhar Widgets na Sidebar à Esquerda */
    [data-testid="stSidebar"] [data-testid="stCheckbox"] {{
        display: flex;
        justify-content: flex-start !important;
        width: 100%;
        margin-top: 0px !important;
        padding-left: 10px;
    }}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
        text-align: left !important;
        font-weight: 600 !important;
    }}

    /* Títulos e Textos Principais */
    h1, h2, h3, h4, h5, h6, b, strong {{
        color: {c_accent} !important;
        font-family: 'Inter', sans-serif;
    }}
    .stMarkdown p, .stMarkdown li, .stMarkdown span {{
        color: {c_text} !important;
        font-weight: 500;
    }}

    /* Fix Geral para Botões - Espaçamento Ajustado */
    .stButton button, .stDownloadButton button {{
        background-color: {c_accent} !important;
        color: white !important;
        border: 2px solid {c_accent} !important;
        font-weight: 600 !important;
        margin-top: 10px !important; 
        box-shadow: 0 4px 10px {c_shadow};
    }}
    .stButton button p, .stDownloadButton button p {{
        color: white !important;
    }}
    .stButton button:hover, .stDownloadButton button:hover {{
        opacity: 0.9 !important;
        color: white !important;
    }}

    /* File Uploader - Compacto */
    div[data-testid="stFileUploader"] {{
        background-color: {c_secondary} !important;
        padding: 12px;
        border-radius: 12px;
        border: 2px dashed {c_border} !important;
        box-shadow: 0 4px 6px {c_shadow};
    }}
    div[data-testid="stFileUploader"] button {{
        border: 2px solid {c_accent} !important;
        color: {c_accent} !important;
        background-color: transparent !important;
    }}
    div[data-testid="stFileUploader"] button:hover {{
        background-color: {c_accent} !important;
        color: white !important;
    }}
    div[data-testid="stFileUploader"] section {{
        background-color: transparent !important;
    }}
    div[data-testid="stFileUploader"] label, 
    div[data-testid="stFileUploader"] span, 
    div[data-testid="stFileUploader"] small {{
        color: {c_text} !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }}

    /* Ficha Técnica Card - Mais compacto */
    .model-details {{
        background-color: {c_secondary} !important;
        padding: 12px !important;
        border-radius: 15px !important;
        border: 2px solid {c_border} !important;
        color: {c_text} !important;
        margin-top: 10px !important;
        box-shadow: 0 8px 30px {c_shadow};
    }}
    .model-details b {{ color: {c_accent} !important; font-size: 0.9rem; }}

    /* Chat Balões */
    .stChatMessage {{
        background-color: {c_secondary} !important;
        border: 1px solid {c_border} !important;
        border-radius: 20px !important;
        box-shadow: 0 2px 10px {c_shadow};
        padding: 15px !important;
    }}

    /* Selectbox e Inputs - Contorno Escuro e Texto Visível */
    div[data-baseweb="select"] > div {{
        background-color: {c_secondary} !important;
        border: 2px solid {c_border} !important;
        color: {c_text} !important;
    }}
    /* Cor do texto selecionado e placeholder */
    div[data-baseweb="select"] [data-testid="stMarkdownContainer"] p {{
        color: {c_text} !important;
    }}
    /* Dropdown List (O menu que abre) */
    ul[role="listbox"] {{
        background-color: {c_secondary} !important;
        border: 1px solid {c_border} !important;
    }}
    li[role="option"] {{
        color: {c_text} !important;
        background-color: {c_secondary} !important;
    }}
    li[role="option"]:hover {{
        background-color: {c_side} !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- Gestão de Estado ---
if "active_url" not in st.session_state: st.session_state.active_url = None
if "messages" not in st.session_state: st.session_state.messages = []
if "full_text" not in st.session_state: st.session_state.full_text = None

# --- Motor de Descoberta (Completo e Rápido) ---
@st.cache_resource(show_spinner=False)
def get_models_cached():
    """Restaura a lista completa de conexões para garantir funcionamento em WSL/Docker."""
    urls = [
        os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1"),
        "http://localhost:1234/v1",
        "http://127.0.0.1:1234/v1",
        "http://172.17.0.1:1234/v1",
        "http://172.18.0.1:1234/v1",
        "http://172.20.0.1:1234/v1",
        "http://172.26.240.1:1234/v1", # Essencial para o seu ambiente
        "http://192.168.1.1:1234/v1"
    ]
    
    def check(url):
        try:
            client = OpenAI(base_url=url, api_key="not-needed", timeout=0.8)
            resp = client.models.list()
            ids = [m.id for m in resp.data if "embed" not in m.id.lower()]
            return url, sorted(ids, key=lambda x: get_model_info(x)["score"])
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=len(urls)) as ex:
        futures = {ex.submit(check, u): u for u in urls}
        result = None
        for f in as_completed(futures):
            res = f.result()
            if res and result is None:
                result = res
                for pending in futures:
                    pending.cancel()
                break
    return result if result else (None, ["Sem Conexão"])

# --- Barra Lateral (Configurações e Filtros) ---
with st.sidebar:
    # Seção de Documentos
    st.subheader("📑 Documento")
    uploaded_file = st.file_uploader("Arraste um PDF ou TXT", type=["txt", "pdf"], label_visibility="collapsed")
    
    st.subheader("🤖 Modelo")
    
    # Seleção de Provedor
    provider = st.radio("Provedor:", ["Local (LM Studio)", "Nuvem (Azure OpenAI)"], horizontal=True, label_visibility="collapsed")
    st.session_state.provider = "azure" if "Azure" in provider else "local"

    if st.session_state.provider == "local":
        active_url, raw_models = get_models_cached()
    else:
        try:
            raw_models = listar_deployments()
            active_url = "azure_api"
        except Exception as e:
            st.error(f"Erro no Azure: {e}")
            raw_models = []
            active_url = None

    if active_url:
        st.session_state.active_url = active_url
        
        # Extração de limites dinâmicos para os filtros
        available_contexts = sorted(list(set(get_model_info(m, provider=st.session_state.provider)["context_val"] // 1024 for m in raw_models)))
        available_years = sorted(list(set(get_model_info(m, provider=st.session_state.provider)["cutoff_year"] for m in raw_models)))
        
        # Filtros Dinâmicos
        with st.expander("⚙️ Filtros Avançados"):
            f_think = st.checkbox("Raciocínio (Thinking)")
            f_vision = st.checkbox("Visão (Imagens)")
            
            # Ajuste dinâmico da Janela (Select Slider só com valores que existem)
            label_ctx = f"Janela Mínima [{min(available_contexts)}k - {max(available_contexts)}k]"
            if len(available_contexts) > 1:
                f_context = st.select_slider(label_ctx, options=available_contexts, value=min(available_contexts), format_func=lambda x: f"{x}k")
            else:
                f_context = available_contexts[0] if available_contexts else 128
                st.caption(f"Janela única: {f_context}k")
            
            # Ajuste dinâmico do Ano
            label_year = f"Ano de Corte [{min(available_years)} - {max(available_years)}]"
            if len(available_years) > 1:
                f_year = st.slider(label_year, min(available_years), max(available_years), min(available_years))
            else:
                f_year = available_years[0] if available_years else 2025
                st.caption(f"Ano único: {f_year}")

        # Lógica de Filtragem (Defensiva e Homologada)
        filtered_models = []
        for m_id in raw_models:
            info = get_model_info(m_id, provider=st.session_state.provider)
            
            # Filtro de Homologação (Apenas Top 2: Elite 8GB)
            if info.get("score", 99) > 2: continue
            
            if f_think and not info.get("think", False): continue
            if f_vision and not info.get("vision", False): continue
            
            ctx_val = info.get("context_val", 131072)
            if ctx_val < (f_context * 1024): continue
            
            cut_year = info.get("cutoff_year", 2025)
            if cut_year < f_year: continue
            
            filtered_models.append(m_id)

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
        st.session_state.messages = []
        st.rerun()
        
    if st.button("🔄 Resetar Rede", use_container_width=True):
        st.cache_resource.clear()
        st.session_state.active_url = None
        st.rerun()

# --- Conteúdo Principal ---
st.markdown(f"<h1 style='color: {c_accent};'>🧜‍♀️ IARA</h1>", unsafe_allow_html=True)
st.markdown("##### Assistente conversacional de PDFs e gerador de relatórios")

if selected_model:
    st.markdown(f"🤖 **Modelo Ativo:** `{selected_model}`")

# Processamento do Documento
if uploaded_file:
    if st.session_state.get("last_file") != uploaded_file.name:
        st.session_state.full_text = None
        st.session_state.document_summary = None
        st.session_state.messages = []
        st.session_state.last_file = uploaded_file.name

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
            st.error(f"Erro: {e}")

if st.session_state.get("full_text"):
    # Trava de Segurança
    if not st.session_state.active_url:
        st.warning("⚠️ Conecte ao provedor para habilitar a análise.")
    else:
        if not st.session_state.get("document_summary"):
            st.info("📄 Documento carregado em memória. Selecione o provedor e modelo desejados na barra lateral.")
            if st.button(f"🚀 Gerar Relatório Executivo com {selected_model}", use_container_width=True, type="primary"):
                try:
                    if st.session_state.provider == "azure":
                        client = get_azure_client()
                    else:
                        client = OpenAI(base_url=st.session_state.active_url, api_key="not-needed")
                    with st.spinner("🧜‍♀️ Gerando relatório de alta densidade..."):
                        start_proc = time.time()
                        st.session_state.document_summary = generate_summary(client, selected_model, st.session_state.full_text)
                        st.session_state.proc_time = time.time() - start_proc
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro na análise: {e}")

    if st.session_state.get("document_summary"):
        with st.expander("📑 Relatório Executivo", expanded=True):
            st.markdown(st.session_state.document_summary)
            if "proc_time" in st.session_state:
                st.caption(f"⏱️ Tempo de processamento: {st.session_state.proc_time:.2f}s")
            # Exportação
            file_name_export = st.session_state.get("last_file", "documento")
            full_md = f"# Relatório IARA: {file_name_export}\n\n{st.session_state.document_summary}\n\n---\n\n{st.session_state.full_text}"
            st.download_button("📥 Exportar Relatório (.md)", data=full_md, file_name=f"IARA_Relatorio.md", mime="text/markdown", use_container_width=True)

        st.divider()
        st.markdown(f"<h3 style='color: {c_accent};'>💬 Pesquisa e Chat com o Documento</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color: #8B949E; margin-bottom: 20px;'>O relatório acima é o resumo padrão. Use a caixa de texto na parte inferior da tela para <b>fazer perguntas específicas</b>, pesquisar valores ocultos ou pedir novas análises.</p>", unsafe_allow_html=True)
        
        # Chat Interativo
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar="🧜‍♀️" if msg["role"] == "assistant" else "🏊"):
                st.markdown(msg["content"])

        user_input = st.chat_input("Pesquise no documento (ex: Quais são os riscos apontados?)...")
        if user_input and st.session_state.active_url:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user", avatar="🏊"): st.markdown(user_input)
            
            try:
                if st.session_state.provider == "azure":
                    client = get_azure_client()
                else:
                    client = OpenAI(base_url=st.session_state.active_url, api_key="not-needed")
                sys_prompt = f"Você é a IARA. Responda baseado no DOCUMENTO:\n{st.session_state.full_text[:60000]}"
                msgs = [{"role": "system", "content": sys_prompt}] + st.session_state.messages[-10:]

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
