# ai-assistant

Assistente de IA da Solaria para o **demandante** na web: ajuda a encontrar as melhores placas solares e itens de fixação para o contexto dele, e os profissionais e empresas que se encaixam, e repassa ao `ai-operational` os pedidos de ação no SaaS. É um grafo LangGraph atrás de uma API FastAPI, com guardrails de entrada e saída, memória de conversa e de longo prazo, e ferramentas por MCP. Outros agentes (o `ai-geographic`, no mobile) também o consultam por A2A.

Fora do escopo dele, por decisão de arquitetura: operar telas do SaaS (é do `ai-operational`) e geografia, clima e rotas (é do `ai-geographic`). Ver o [documento 12](https://github.com/Megueutu/VersioSpec/blob/main/projects/solaria/entrega/12-arquitetura-dos-agentes-de-ia-2026-10-18.md) do VersioSpec.

## Como uma mensagem é tratada

```
input_guardrail → condense_memory → router ─┬→ faq_reader ─────────┐
                                            ├→ professional_suggester ┤
                                            ├→ agency_suggester ──────┤  voltam ao router,
                                            ├→ solar_panel_specialist ┤  que decide se já basta
                                            ├→ solar_calculator ──────┘
                                            ├→ operational_delegate ──→ fim (resposta vai direto ao usuário)
                                            └→ orchestrator → judge → output_guardrail → fim
```

| Etapa | O que faz |
|---|---|
| `input_guardrail` | Regex de injeção e de dados internos, anonimiza PII (CNPJ, CPF, telefone, e-mail) e classifica a mensagem por LLM; bloqueia o que não é permitido |
| `condense_memory` | Resume a conversa quando ela cresce |
| `router` | Escolhe um especialista por vez, ou o orquestrador quando já há informação suficiente; com uma decisão pendente do agente operacional, devolve a mensagem direto a ele |
| `faq_reader` | Responde sobre a plataforma com RAG no Qdrant (coleção `faq`) |
| `solar_panel_specialist` | Conteúdo técnico, recomendação de placas (`recomendar_ofertas`) e de itens de fixação (`listar_itens_de_fixacao`) |
| `professional_suggester` | Recomenda profissionais (`recomendar_profissionais`, `listar_profissoes`, `buscar_tecnicos_credenciados`) |
| `agency_suggester` | Recomenda empresas fornecedoras (`recomendar_fornecedores`) |
| `solar_calculator` | Estimativa preliminar de consumo, geração, investimento e payback, pelas ferramentas do billscanner |
| `operational_delegate` | Delega ao `ai-operational` por A2A, com o JWT do usuário; a proposta volta exatamente como foi escrita |
| `orchestrator` | Compõe a resposta final a partir do que os especialistas reuniram |
| `judge` | Valida a resposta (alucinação, aderência) e pede uma nova tentativa antes de bloquear |
| `output_guardrail` | Revisão de conformidade por LLM e remoção de PII |

O ranking de placas, profissionais e empresas é determinístico e vem da `api-recommendation`; o LLM só cruza as necessidades do usuário com o top-N e explica a escolha. Para buscas por proximidade, `listar_minhas_unidades` lê as unidades do usuário no `api-core` com o JWT dele (só para a persona `demandante`).

## Endpoints

| Rota | Uso |
|---|---|
| `POST /chat` | Recebe `{conversation_id, message}` com `Authorization: Bearer <JWT>` e devolve `{response, specialists_used, workflow_steps, messenger_conversation_id}`; o JWT do `api-auth` é validado antes do turno (`401` se inválido ou expirado; `503` fora do `LOCAL` sem `JWT_JWKS_URL`) |
| `POST /debug/chat` | Só interno, fora do OpenAPI, só para os admins de `DEBUG_ADMIN_SUBS` (inclusive em PROD): o mesmo corpo do `/chat` mais `persona`, e devolve também o `debug` com a entrada e a saída de cada nó. Ver [docs/debug-endpoint.md](./docs/debug-endpoint.md) |
| `GET /health` | Estado do serviço e das chaves de LLM que faltam |
| `GET /.well-known/agent-card.json` | Agent Card A2A (habilidade `recomendar-produtos`) |
| `POST /a2a` | JSON-RPC do A2A 1.0; exige o mesmo `Authorization: Bearer`; a persona (`demandante` ou `profissional`) vai em `message.metadata` |

O [openapi.yaml](./openapi.yaml) descreve `POST /chat` e `GET /health`; ele não cobre o A2A.

## Memória

| Tipo | Onde | Detalhe |
|---|---|---|
| Conversa (curto prazo) | Mongo, `dbagents.conversation_checkpoints` (checkpointer do LangGraph) | Persiste entre reinícios; expira em `CHECKPOINT_TTL_DIAS` (30) |
| Mensagens e observabilidade | `api-messenger` | Cada turno grava a mensagem do usuário e a do assistente; o `messenger_conversation_id` volta no `/chat` |
| Longo prazo (fatos do usuário) | Mongo, `user_memory` | Extraído ao fim do turno, em segundo plano; limitações em [docs/long-term-memory-limitations.md](./docs/long-term-memory-limitations.md) |

O JWT do usuário e a persona ficam em variáveis de contexto (`src/core/security/request_context.py`), nunca no estado do grafo, porque o checkpointer grava o estado no Mongo.

## Ferramentas (MCP e A2A)

- **MCP**, `mcp-database` (`MCP_URL`, `MCP_API_KEY`): `recomendar_ofertas`, `recomendar_profissionais`, `recomendar_fornecedores`, `listar_profissoes`, `buscar_tecnicos_credenciados`, `listar_itens_de_fixacao`. Se uma ferramenta some do servidor, o cliente avisa no log em vez de deixar o especialista mudo.
- **A2A**: serve o próprio Agent Card e recebe delegações; delega ao `ai-operational` (`A2A_OPERATIONAL_URL`). Módulo `ai_lib.a2a` da `solaria-lib`. Requisitos em [13-requisitos-mcp-e-a2a](https://github.com/Megueutu/VersioSpec/blob/main/projects/solaria/entrega/13-requisitos-mcp-e-a2a-2026-10-18.md).

## LLM

Uma chave por provedor, lidas do ambiente pela `solaria-lib` (`GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`). `LLM_PROVIDER_ORDER` define a ordem e o fallback entre provedores (por exemplo `gemini,groq,openai`); `LLM_MODEL_GEMINI`, `LLM_MODEL_GROQ` e `LLM_MODEL_OPENAI` escolhem o modelo (o da OpenAI não tem padrão). O custo por turno e a timeline aparecem em [docs/observability-cost.md](./docs/observability-cost.md) e [docs/observability-langsmith.md](./docs/observability-langsmith.md).

## Variáveis de ambiente

As chaves e URLs vêm do Infisical (`make vault ENV=local|qa|prod`, pastas `/database /llm /agent-queue`). O [.env.example](./.env.example) lista todas. As principais:

| Variável | Uso |
|---|---|
| `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `LLM_PROVIDER_ORDER`, `LLM_MODEL_OPENAI` | LLM |
| `MONGODB_URI` | Checkpointer e memória de longo prazo |
| `DB_MONGO_AGENTS` | Banco Mongo dos agentes (`dbagents`; `dbagentsqa` em QA) |
| `API_MESSENGER_URL` | Conversas e mensagens |
| `JWT_JWKS_URL`, `JWT_ISSUER` | Validação do JWT do usuário (RS256, emitido pelo `api-auth`) |
| `CORS_ALLOWED_ORIGINS` | Origens do navegador autorizadas a chamar a API (CORS), separadas por vírgula; sem credenciais e sem `*` |
| `MCP_URL`, `MCP_API_KEY` | `mcp-database` |
| `API_CORE_URL` | Unidades do usuário |
| `A2A_PUBLIC_URL`, `A2A_OPERATIONAL_URL` | Agent Card e destino da delegação de ações |
| `QDRANT_URL`, `QDRANT_API_KEY` | RAG do FAQ |
| `SOLARIA_LANGSMITH_*` | Rastreamento no LangSmith (opcional) |
| `ENVIRONMENT` | `LOCAL` (padrão), `QA` ou `PROD` |
| `DEBUG_ADMIN_SUBS` | Modo debug (`POST /debug/chat`): UUIDs (`sub` do JWT) dos admins, separados por vírgula; vazio fecha a rota (inclusive em `PROD`) |

## Como rodar

```bash
make install            # cria o .venv e instala as dependências
make vault ENV=local    # grava o .env a partir do Infisical
make dev                # uvicorn src.api.app:app --reload
make test               # pytest com cobertura
make lint
```

Para conversar pelo terminal sem a API, defina `TEST_USER_TOKEN` (um JWT do `api-auth` ou do mock-idp em `scripts/dev/mock_idp`) e rode `python main.py`.

## O que o Confluence promete e o que existe

| Prometido | Situação |
|---|---|
| Roteador, Orquestrador, Guardrail e validação de alucinação | Existem (`router`, `orchestrator`, `input_guardrail` e `output_guardrail`, `judge`) |
| Especialista em placa solar, sugestor de fornecedor e de profissional, FAQ | Existem |
| Calculador solar | Existe (não estava na lista do Confluence) |
| Triagem de serviço, recomendação de categoria | Não existem neste serviço |
| Verificação profissional e de CNPJ | Não é deste serviço: é do `ai-validation` |
| Resposta em streaming | Não existe: o `/chat` devolve a resposta inteira (pode demorar; o cliente precisa de timeout maior que 60 s) |

## Documentação

- [docs/nps.md](./docs/nps.md): avaliação da conversa (`messenger_conversation_id`)
- [docs/observability-cost.md](./docs/observability-cost.md) e [docs/observability-langsmith.md](./docs/observability-langsmith.md)
- [docs/long-term-memory-limitations.md](./docs/long-term-memory-limitations.md)

## Contribuindo

Conventional Commits em inglês e minúsculas (`feat:`, `fix:`...), branch `tipo/descricao-curta` e PR com o modelo do repositório. `main` é a base de trabalho; a `qa` recebe a sincronização da `main`.
