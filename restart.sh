#!/bin/bash
echo "🧜‍♀️ Reiniciando IARA - Inteligência Artificial Regional de Análise..."

# Força a parada e remoção total para evitar conflitos de nome e rede
docker compose down --remove-orphans 2>/dev/null
docker stop streamlit-llm-chat 2>/dev/null
docker rm streamlit-llm-chat 2>/dev/null

# Tenta subir novamente com o melhor motor disponível (BuildKit-first)
export DOCKER_BUILDKIT=1
export COMPOSE_BAKE=1

if docker compose up --build -d 2>/tmp/docker_out; then
    cat /tmp/docker_out
else
    # Fallback silencioso se o BuildKit falhar no ambiente
    DOCKER_BUILDKIT=0 COMPOSE_BAKE=0 docker compose up --build -d
fi

echo "✅ Containers reiniciados! Logs iniciais:"
docker compose logs --tail=10
echo "--------------------------------------------------"
echo "🚀 IARA está online em: http://localhost:8501"
echo "Dica: Se houver erros no chat, verifique o arquivo app_errors.log"
