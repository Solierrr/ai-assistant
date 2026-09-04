# Rodando o Projeto Localmente

Este repositório é Python. Diferente da maioria dos serviços da organização, o entrypoint local não é `uvicorn` — é `python main.py`, que sobe um loop de chat direto no terminal, conectando no Mongo e conversando com o grafo de agentes via `input()`. Clone, crie um ambiente virtual, instale as dependências do `requirements.txt` e rode o `main.py`. Antes de iniciar, verifique a seção de impedimentos abaixo — o loop de chat sobe mesmo sem todas as credenciais, mas os agentes que dependem de LLM ou Redis falham em runtime sem elas.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,mongodb,redis,github" height="48" alt="Rodando o Projeto — ai-assistant">
  </a>
</p>

## Possíveis Impedimentos

- **Python instalado localmente**, o `Dockerfile` usa `python:latest` sem fixar versão, então use a versão mais recente do Python 3 disponível (`sonar-project.properties` referencia `3.14`) — {a confirmar} a versão mínima suportada.
- **MongoDB acessível**, `main.py` chama `MongoDBClient.connect()` no `startup()` antes de abrir o loop de chat, então é necessária uma instância Mongo alcançável em `DB_MONGO_URI` (local via Docker, ou remota) — sem ela, a aplicação não sobe.
- **Chaves de LLM (`GOOGLE_API_KEY`, `GROQ_API_KEY`)**, os agentes usam Gemini (`src/core/llm/llm_gemini.py`) e Groq (`src/core/llm/llm_groq.py`); sem essas chaves o loop de chat sobe, mas qualquer turno que dependa do LLM falha.
- **Redis (Upstash) apenas se for rodar a API**, o loop de chat (`main.py`) não usa Redis, mas a API (`src/api/app.py`) depende de `UPSTASH_AGENTS_HOST`/`UPSTASH_AGENTS_PASSWORD` para publicar e consumir eventos do stream de chat — sem isso, apenas o `uvicorn` sobe rodando a API é afetado, não o `main.py`.
- **Secrets locais**, variáveis de ambiente equivalentes às injetadas em runtime pelo [Infisical](https://infisical.com) precisam ser criadas manualmente em um `.env` local a partir do `.env.example` — sem elas, a aplicação sobe mas falha ao tentar se conectar em dependências externas.

## Instalação do Projeto

### Iniciando o repositório com o Github

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=github,vscode" height="48" alt="Frameworks">
  </a>
</p>

Clone o repositório e abra no VS Code.

```Comandos para clonar o repositório
git clone https://github.com/Solierrr/ai-assistant.git
cd ./ai-assistant
code . -r
```

### Instalando dependências necessárias para rodar o projeto localmente

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python" height="48" alt="Frameworks">
  </a>
</p>

Crie um ambiente virtual antes de instalar as dependências, para não poluir o Python global da máquina. Copie o `.env.example` para `.env` e preencha os valores necessários antes de subir a aplicação.

```Comandos para instalação de dependências
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```

O comando `python main.py` sobe o loop de chat no terminal — digite uma mensagem e pressione Enter para conversar com o grafo de agentes; digite `sair`, `fim` ou `quit` para encerrar.

### Rodando a API (opcional)

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=fastapi" height="48" alt="API">
  </a>
</p>

O repositório também expõe uma API HTTP (`src/api/app.py`), usada em produção junto com um consumer de Redis Stream. Para rodá-la localmente é necessário ter Redis (Upstash ou local) configurado além do Mongo:

```Comando para subir a API localmente
uvicorn src.api.app:app --reload --port 8000
```

Isso expõe `GET /health`, `POST /chat` (enfileira a mensagem e devolve um `event_id`) e `GET /chat/{event_id}` (consulta o resultado processado pelo consumer). O `Dockerfile` do repositório não define `CMD`/`ENTRYPOINT`, então o comando efetivo usado no container de produção é {a confirmar} — provavelmente definido no manifesto do [Infra-gitops](https://github.com/Solierrr/infra-gitops).

## Rodando os testes

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,pytest" height="48" alt="Testes">
  </a>
</p>

```Comando para rodar a suíte de testes
pytest
```
