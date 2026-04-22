"""Script simples para testar conexao com Azure OpenAI."""

from conexao import testar_conexao


def main() -> int:
    """Executa um teste simples e retorna codigo de saida de shell."""
    try:
        print(testar_conexao("Responda apenas com 'ok'."))
        return 0
    except Exception as exc:
        print(f"Falha no teste de conexao: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
