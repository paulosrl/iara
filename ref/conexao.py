"""Camada de conexao para Azure OpenAI (API v1).

Variaveis obrigatorias no `.env`:
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_DEPLOYMENT

Variavel opcional:
- AZURE_OPENAI_DEPLOYMENTS (lista separada por virgula para UI)
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

_client: OpenAI | None = None


def _obrigatoria(nome: str) -> str:
    """Retorna variavel de ambiente obrigatoria ou levanta erro claro."""
    valor = (os.getenv(nome) or "").strip()
    if not valor:
        raise ValueError(f"Defina {nome} no .env")
    return valor


def _carregar_env() -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _texto_resposta(response: object) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise RuntimeError("A API respondeu sem choices.")

    texto = (choices[0].message.content or "").strip()
    if not texto:
        raise RuntimeError("A API respondeu sem conteudo de texto.")
    return texto


def _cliente() -> OpenAI:
    global _client
    if _client is None:
        _carregar_env()
        endpoint = _obrigatoria("AZURE_OPENAI_ENDPOINT").rstrip("/")
        _client = OpenAI(
            api_key=_obrigatoria("AZURE_OPENAI_API_KEY"),
            base_url=f"{endpoint}/openai/v1/",
        )
    return _client


def listar_deployments() -> list[str]:
    """Retorna deployments disponiveis para selecao na interface."""
    _carregar_env()
    padrao = _obrigatoria("AZURE_OPENAI_DEPLOYMENT")
    extras = (os.getenv("AZURE_OPENAI_DEPLOYMENTS") or "").strip()
    lista = [padrao] + [item.strip() for item in extras.split(",") if item.strip()]

    # Remove repetidos sem perder ordem, evitando opcoes duplicadas na UI.
    return list(dict.fromkeys(lista))


def responder_chat(
    mensagens: list[dict[str, str]], deployment: str | None = None
) -> str:
    """Envia mensagens no formato chat.completions e retorna texto."""
    if not mensagens:
        raise ValueError("Envie ao menos uma mensagem para o chat.")

    client = _cliente()
    deployment_final = (deployment or _obrigatoria("AZURE_OPENAI_DEPLOYMENT")).strip()
    if not deployment_final:
        raise ValueError("Deployment vazio. Informe um deployment valido.")

    response = client.chat.completions.create(
        model=deployment_final,
        messages=mensagens,
    )
    return _texto_resposta(response)


def testar_conexao(pergunta: str = "Responda apenas com 'ok'.") -> str:
    """Executa uma chamada simples ao deployment padrao e retorna texto."""
    return responder_chat([{"role": "user", "content": pergunta}])
