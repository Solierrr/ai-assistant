# AI Assistant

O `ai-assistant` é o serviço de assistente de IA conversacional do marketplace B2B do setor fotovoltaico da Solaria. Ele orquestra múltiplos agentes especializados (leitura de FAQ, sugestão de agências, sugestão de profissionais, especialista em painel solar) através de um grafo de estado construído com LangGraph, aplicando guardrails de entrada e saída, anonimização de PII e um `judge` que valida a resposta final antes de devolvê-la ao usuário. O repositório expõe duas formas de interação: um loop de chat via terminal (`main.py`), usado para testes manuais rápidos do workflow, e uma API HTTP construída com FastAPI (`src/api/app.py`) que enfileira mensagens em um Redis Stream e as processa de forma assíncrona por um pool de consumers, devolvendo o resultado por polling.

<p>

[![License](https://img.shields.io/github/license/Solierrr/ai-assistant)](https://github.com/Solierrr/ai-assistant/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/ai-assistant)](https://github.com/Solierrr/ai-assistant/commits)
[![GitHub Issues](https://img.shields.io/github/issues/Solierrr/ai-assistant)](https://github.com/Solierrr/ai-assistant/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/ai-assistant)](https://github.com/Solierrr/ai-assistant/pulls)
[![GitHub Contributors](https://img.shields.io/github/contributors/Solierrr/ai-assistant)](https://github.com/Solierrr/ai-assistant/graphs/contributors)
[![Release](https://img.shields.io/github/v/release/Solierrr/ai-assistant)](https://github.com/Solierrr/ai-assistant/releases)

</p>

<div align="center">

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,langchain,mongodb,redis,docker" height="48" alt="Stack do ai-assistant">
  </a>
</p>

<p>

[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?logo=langchain&logoColor=white)](https://www.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?logo=langgraph&logoColor=white)](https://www.langchain.com/langgraph)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

</p>

</div>

## Aprofunde-se no Projeto!

- [ARCHITECTURE.md](./ARCHITECTURE.md), estrutura do repositório, o grafo de agentes em LangGraph, a camada de infraestrutura Mongo/Redis e a diferença entre o loop de chat local e a API.
- [RUNNING.md](./RUNNING.md), como rodar o projeto localmente, dependências e impedimentos de credenciais.
- {link do arquivo de deployment}, pipeline padrão da organização (build, publish, ArgoCD).

## Contribuindo

- [CONTRIBUTING.md](https://github.com/Solierrr/.github/blob/main/CONTRIBUTING.md), convenções de commit, branch e Pull Request.
- [CODE_OF_CONDUCT.md](https://github.com/Solierrr/.github/blob/main/CODE_OF_CONDUCT.md), código de conduta do projeto.
- [SECURITY.md](https://github.com/Solierrr/.github/blob/main/SECURITY.md), como reportar vulnerabilidades de segurança.
