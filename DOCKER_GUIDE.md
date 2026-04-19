# 🐳 Guia de Containers IARA (v2.2)

Este documento fornece um roteiro passo a passo para configurar, rodar e manter a IARA utilizando Docker. O uso de containers garante que todas as dependências (como o Tesseract OCR e a biblioteca Poppler) estejam configuradas corretamente sem poluir seu sistema operacional.

## 📋 Pré-requisitos

1.  **Docker Desktop** instalado e em execução.
2.  **WSL2** (para usuários Windows) configurado como motor do Docker.
3.  **LM Studio** rodando no **Host** (seu computador) com o servidor local ativo na porta 1234.

## 🚀 Roteiro Passo a Passo

### 1. Preparação do Ambiente
Certifique-se de que não há outros serviços ocupando a porta **8501** (porta padrão do Streamlit).

### 2. Inicialização Automática (Recomendado)
A IARA possui um script de automação que cuida da limpeza e reinicialização dos containers:

```bash
./restart.sh
```

**O que este script faz?**
- Interrompe qualquer container antigo da IARA.
- Remove resíduos de rede ou "órfãos".
- Reconstrói a imagem (`build`) para garantir que novas alterações no código sejam aplicadas.
- Sobe o serviço em modo *detached* (segundo plano).
- Exibe os últimos logs para confirmação.

### 3. Verificação de Execução
Após rodar o script, verifique se o container está saudável:

```bash
docker ps
```
Você deve ver o container `streamlit-llm-chat` com o status `Up` e a porta `0.0.0.0:8501->8501/tcp`.

### 4. Acesso à Interface
Abrir seu navegador e acesse:
👉 **[http://localhost:8501](http://localhost:8501)**

## 🛡️ Configuração de Rede (LM Studio)

Como a IARA roda dentro de um container, ela precisa de um "endereço especial" para falar com o LM Studio que está rodando fora dele (no seu Windows/Linux).

- No menu lateral da IARA, o sistema tentará automaticamente o endereço: `http://host.docker.internal:1234/v1`.
- Certifique-se de que a opção **"Cross-Origin Resource Sharing (CORS)"** esteja ativada no LM Studio.

## 🔍 Resolução de Problemas

### Os containers não sobem?
Tente forçar a remoção de volumes antigos:
```bash
docker compose down -v
docker compose up --build
```

### O OCR não funciona?
Verifique se o Tesseract está instalado na imagem rodando o comando dentro do container:
```bash
docker exec -it streamlit-llm-chat tesseract --version
```

### Logs em Tempo Real
Para monitorar o que está acontecendo "por debaixo do capô":
```bash
docker compose logs -f
```

---
*IARA - Estabilidade e Performance em Containers.*
