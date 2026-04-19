#!/bin/bash
echo "🧜‍♀️ Reiniciando IARA - Inteligência Artificial Regional de Análise..."
docker-compose down
docker-compose up --build -d
echo "✅ Containers reiniciados! Logs iniciais:"
docker-compose logs --tail=10
echo "--------------------------------------------------"
echo "Dica: Se houver erros no chat, verifique o arquivo app_errors.log"
