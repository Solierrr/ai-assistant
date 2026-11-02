<p align="center">
  <img src="./assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

<p align="center">
  <img src="./assets/readme/stacks/python.png" width="100" hspace="8" alt="Python" title="Python">
  <img src="./assets/readme/stacks/mongodb.png" width="100" hspace="8" alt="MongoDB" title="MongoDB">
  <img src="./assets/readme/stacks/qdrant.png" width="100" hspace="8" alt="Qdrant" title="Qdrant">
  <img src="./assets/readme/stacks/upstash.png" width="100" hspace="8" alt="Upstash" title="Upstash">
  <img src="./assets/readme/stacks/jwt.png" width="100" hspace="8" alt="JWT" title="JWT">
  <img src="./assets/readme/stacks/langchain.png" width="100" hspace="8" alt="LangChain" title="LangChain">
  <img src="./assets/readme/stacks/gemini.png" width="100" hspace="8" alt="Gemini" title="Gemini">
  <img src="./assets/readme/stacks/groq.png" width="100" hspace="8" alt="Groq" title="Groq">
</p>

# Assistente de recomendações

[![License](https://img.shields.io/github/license/Solierrr/ai-assistant)](https://github.com/Solierrr/ai-assistant/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/ai-assistant)](https://github.com/Solierrr/ai-assistant/commits)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/ai-assistant)](https://github.com/Solierrr/ai-assistant/pulls)
[![Release](https://img.shields.io/github/v/release/Solierrr/ai-assistant)](https://github.com/Solierrr/ai-assistant/releases)

O assistente ajuda quem procura equipamentos, profissionais e fornecedores para um projeto de energia solar. Ele reúne as necessidades informadas na conversa, consulta dados da plataforma e explica as alternativas encontradas. Também oferece estimativas preliminares e encaminha pedidos de operação ao agente responsável por executar ações.

A conversa usa especialistas organizados em um grafo, com memória no MongoDB e consulta ao FAQ no Qdrant. O acesso depende do JWT da pessoa. As recomendações são obtidas por ferramentas e os registros da conversa são enviados ao serviço de mensagens. Outros agentes podem consultar o mesmo assistente pelo protocolo de delegação.

## Aprofunde-se no Projeto!

- [OVERVIEW.md](./docs/OVERVIEW.md), finalidade e regras de produto.
- [ARCHITECTURE.md](./docs/ARCHITECTURE.md), componentes, dados e integrações.
- [RUNNING.md](./docs/RUNNING.md), preparação e execução local.
- [API.md](./docs/API.md), autenticação e uso do contrato.
- [DEPLOY.md](./docs/DEPLOY.md), ambientes e publicação.
- [STATUS.md](./docs/STATUS.md), limites observados.
- [Dados](./database/), modelos e responsabilidades de persistência.
- [Fluxos](./flows/), etapas e casos de erro do repositório.
- [PENDENCIAS.md](./PENDENCIAS.md), questões para revisão.

## Contribuindo

- [CONTRIBUTING.md](https://github.com/Solierrr/.github/blob/main/.github/CONTRIBUTING.md), convenções de contribuição.
- [CODE_OF_CONDUCT.md](https://github.com/Solierrr/.github/blob/main/CODE_OF_CONDUCT.md), código de conduta.
- [SECURITY.md](https://github.com/Solierrr/.github/blob/main/SECURITY.md), relato de vulnerabilidades.
