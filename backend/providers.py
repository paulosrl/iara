"""Camada de provedores de LLM da IARA.

Centraliza toda a lógica de conexão e descoberta de modelos para os dois
provedores suportados:

  - Local  → LM Studio (OpenAI-compatible, roda na máquina do usuário)
  - Nuvem  → Azure OpenAI (requer variáveis de ambiente no .env)

Variáveis obrigatórias para Azure (definir no .env):
  AZURE_OPENAI_API_KEY      Chave de API do recurso Azure OpenAI
  AZURE_OPENAI_ENDPOINT     URL do recurso (ex: https://meu-recurso.openai.azure.com)
  AZURE_OPENAI_DEPLOYMENT   Nome do deployment padrão (ex: gpt-4o)

Variável opcional:
  AZURE_OPENAI_DEPLOYMENTS  Deployments extras separados por vírgula para a UI
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from backend.core import get_model_info

# ---------------------------------------------------------------------------
# URLs candidatas para o LM Studio (testadas em paralelo na descoberta)
# ---------------------------------------------------------------------------
_LM_STUDIO_URLS = [
    os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1"),
    "http://localhost:1234/v1",
    "http://127.0.0.1:1234/v1",
    "http://172.17.0.1:1234/v1",
    "http://172.18.0.1:1234/v1",
    "http://172.20.0.1:1234/v1",
    "http://172.26.240.1:1234/v1",  # Gateway WSL específico do ambiente
    "http://192.168.1.1:1234/v1",
]

# ---------------------------------------------------------------------------
# Provedor local — LM Studio
# ---------------------------------------------------------------------------

def discover_local_models() -> tuple[str | None, list[str]]:
    """Testa todas as URLs do LM Studio em paralelo e retorna a primeira ativa.

    Returns:
        (url_ativa, lista_de_modelos) ou (None, ["Sem Conexão"]) se nenhuma responder.
    """
    def _check(url: str) -> tuple[str, list[str]] | None:
        try:
            client = OpenAI(base_url=url, api_key="not-needed", timeout=0.8)
            resp = client.models.list()
            ids = [m.id for m in resp.data if "embed" not in m.id.lower()]
            return url, sorted(ids, key=lambda x: get_model_info(x)["score"])
        except Exception:
            return None

    result = None
    with ThreadPoolExecutor(max_workers=len(_LM_STUDIO_URLS)) as executor:
        futures = {executor.submit(_check, url): url for url in _LM_STUDIO_URLS}
        for future in as_completed(futures):
            res = future.result()
            if res is not None and result is None:
                result = res
                executor.shutdown(wait=False, cancel_futures=True)
                break

    return result if result else (None, ["Sem Conexão"])


def get_local_client(url: str) -> OpenAI:
    """Cria um cliente OpenAI apontando para o LM Studio na URL informada."""
    return OpenAI(base_url=url, api_key="not-needed")


# ---------------------------------------------------------------------------
# Provedor Azure OpenAI
# ---------------------------------------------------------------------------

_azure_client: OpenAI | None = None
_azure_lock = threading.Lock()


def _load_env() -> None:
    """Carrega o .env da raiz do projeto."""
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _require_env(name: str) -> str:
    """Retorna variável de ambiente obrigatória ou levanta ValueError claro."""
    value = (os.getenv(name) or "").strip()
    if not value:
        raise ValueError(f"Defina {name} no arquivo .env")
    return value


def get_azure_client() -> OpenAI:
    """Retorna o cliente Azure OpenAI. Singleton thread-safe (double-checked locking)."""
    global _azure_client
    if _azure_client is None:
        with _azure_lock:
            if _azure_client is None:
                _load_env()
                endpoint = _require_env("AZURE_OPENAI_ENDPOINT").rstrip("/")
                _azure_client = OpenAI(
                    api_key=_require_env("AZURE_OPENAI_API_KEY"),
                    base_url=f"{endpoint}/openai/v1/",
                )
    return _azure_client


def list_azure_deployments() -> list[str]:
    """Retorna lista de deployments disponíveis para exibição na interface.

    Combina AZURE_OPENAI_DEPLOYMENT (obrigatório) com AZURE_OPENAI_DEPLOYMENTS
    (opcional, separado por vírgula), removendo duplicatas sem alterar a ordem.
    """
    _load_env()
    default = _require_env("AZURE_OPENAI_DEPLOYMENT")
    extras = (os.getenv("AZURE_OPENAI_DEPLOYMENTS") or "").strip()
    all_deployments = [default] + [d.strip() for d in extras.split(",") if d.strip()]
    return list(dict.fromkeys(all_deployments))
