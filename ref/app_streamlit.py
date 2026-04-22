"""Interface Streamlit para conversar com Azure OpenAI."""

import streamlit as st
from openai import APIConnectionError, BadRequestError

from conexao import listar_deployments, responder_chat


st.set_page_config(page_title="Azure Chat", layout="centered")
st.title("Azure Chat")
st.caption("Escolha o deployment e converse em uma interface de chat.")

try:
    deployments = listar_deployments()
except Exception as exc:
    st.error(f"Falha ao carregar configuracao: {type(exc).__name__}: {exc}")
    st.stop()

with st.sidebar:
    st.subheader("Configuracao")
    deployment = st.selectbox("Modelo (deployment)", deployments, index=0)
    if st.button("Nova conversa", use_container_width=True):
        st.session_state.mensagens = []
        st.rerun()

if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

boas_vindas = {
    "role": "assistant",
    "content": f"Pronto. Modelo ativo: `{deployment}`.\n\nPergunte o que quiser.",
}
# mensagens[0] e sempre a mensagem de boas-vindas do assistant;
# e atualizada a cada rerun para refletir o deployment selecionado na sidebar.
if not st.session_state.mensagens:
    st.session_state.mensagens.append(boas_vindas)
else:
    st.session_state.mensagens[0] = boas_vindas

for mensagem in st.session_state.mensagens:
    with st.chat_message(mensagem["role"]):
        st.markdown(mensagem["content"])

prompt = st.chat_input("Digite sua pergunta")
if prompt:
    st.session_state.mensagens.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    erro_na_requisicao = False
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                resposta = responder_chat(
                    st.session_state.mensagens,
                    deployment=deployment,
                )
            except ValueError as exc:
                resposta = f"Erro de configuracao: {exc}"
                erro_na_requisicao = True
            except APIConnectionError:
                resposta = "Erro de conexao com Azure OpenAI. Verifique rede/firewall."
                erro_na_requisicao = True
            except BadRequestError as exc:
                erro = str(exc)
                if "unknown_model" in erro:
                    resposta = (
                        "Deployment invalido no Azure. Selecione um deployment existente "
                        "na lista e confira AZURE_OPENAI_DEPLOYMENTS/AZURE_OPENAI_DEPLOYMENT."
                    )
                elif "unavailable_model" in erro:
                    resposta = (
                        "Deployment indisponivel neste recurso/regiao (unavailable_model). "
                        "Selecione outro deployment ativo na lista."
                    )
                else:
                    resposta = f"Requisicao invalida: {exc}"
                erro_na_requisicao = True
            except Exception as exc:
                resposta = f"Falha ao responder: {type(exc).__name__}: {exc}"
                erro_na_requisicao = True
        st.markdown(resposta)

    if not erro_na_requisicao:
        st.session_state.mensagens.append({"role": "assistant", "content": resposta})
