<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Execução local

Para rodar, é preciso ter Python, `make`, MongoDB e acesso aos modelos e aos serviços integrados, lembrando que o Dockerfile usa `python:latest` e não fixa uma versão. O guia comum aos serviços Python está em [PYTHON.md](https://github.com/Solierrr/docs-warehouse/blob/main/readme/running/PYTHON.md).

Execute `make install`, `make vault` e `make dev`, sabendo que o cofre exporta as pastas `/database`, `/redis`, `/llm`, `/agent-queue` e `/service-keys` e que o servidor sobe a aplicação `src.api.app:app`.

| Comando | Efeito |
|---|---|
| `make test` | Pytest com cobertura |
| `make lint` | Ruff nos módulos selecionados |
| `make build` | Compilação dos módulos |
| `make openapi` | Exportação do contrato |
| `python -m src.rag.indexing.ingest_faq` | Reconstrói explicitamente o índice do FAQ |

Abra `/docs` e teste `/ready` antes de chamar `/chat`, usando um JWT emitido pelo `api-auth`, porque fora do ambiente `LOCAL` o acesso é recusado quando o JWKS não está configurado. O índice do FAQ não é criado durante uma requisição, e enquanto ele não existir o especialista responde que a informação está indisponível.