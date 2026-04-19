#!/bin/bash
# IARA GitHub Sync & Repair Script
# Este script resolve o erro 'remote-https' e sincroniza o código.

echo "🧜‍♀️ Iniciando Reparo do Sincronismo IARA..."

# 1. Tentar instalar dependências (pode pedir senha)
echo "🔍 Verificando dependências do sistema..."
sudo apt-get update && sudo apt-get install -y libcurl4-openssl-dev git-all

# 2. Resetar o Remote para garantir rota limpa
echo "🔄 Resetando rotas do GitHub..."
git remote remove origin 2>/dev/null
git remote add origin https://github.com/paulosrl/iara.git

# 3. Tentar o Push
echo "🚀 Subindo código para https://github.com/paulosrl/iara ..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo "✅ Sincronização concluída com sucesso!"
else
    echo "⚠️ Erro no HTTPS. Tentando via SSH como fallback..."
    git remote set-url origin git@github.com:paulosrl/iara.git
    git push -u origin main
fi
