# Arquitetura do Repositório

O `ai-assistant` é organizado como um grafo de agentes sobre LangGraph, com duas portas de entrada distintas para o mesmo workflow. A primeira é `main.py`, um loop de chat de terminal que conecta direto no Mongo, compila o grafo e invoca cada turno via `input()` — pensado para debug e teste manual do comportamento dos agentes, sem passar por fila ou rede. A segunda é `src/api/app.py`, uma aplicação FastAPI que não expõe o workflow de forma síncrona: ela publica a mensagem recebida em um Redis Stream (Upstash) e devolve `202 Accepted` imediatamente, enquanto um pool de consumers assíncronos (`AGENT_CONSUMER_COUNT`) processa a fila, executa o grafo e grava o resultado em uma chave de resultado com TTL, consultável depois via polling em `GET /chat/{event_id}`. Esse desenho desacopla o tempo de resposta da API do tempo de execução do LLM/dos agentes, e permite escalar consumers de forma independente da camada HTTP.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,langchain,mongodb,redis" height="48" alt="Arquitetura do ai-assistant">
  </a>
</p>

- **Grafo de workflow (LangGraph)**, definido em `src/workflow/graph/graph.py`, entra por `input_guardrail`, passa por `condense_memory` e `router`, que decide qual especialista chamar (`faq_reader`, `professional_suggester`, `agency_suggester`, `solar_panel_specialist` ou direto `orchestrator`), sempre retornando ao `router` até a decisão final seguir para `orchestrator` → `judge` → `output_guardrail`. O `judge` pode mandar o fluxo de volta para `orchestrator` em caso de retentativa antes de liberar a resposta.
- **Persistência de curto prazo via Mongo**, o próprio grafo usa um checkpointer Mongo (`src/memory/session/mongo_checkpointer.py`) para manter o estado da conversa entre turnos por `thread_id` (o `conversation_id`), enquanto `src/infra/database/mongo/` concentra cliente assíncrono (`mongodb_client.py`), cliente síncrono (`mongodb_sync_client.py`), criação de índices, repositórios (`conversation_repository.py`, `message_repository.py`) e schemas de `conversations`/`messages`, além de coleções auxiliares de auditoria (`ai_logs`, `agent_executions`, `rag_documents`, `agent_memories`, `hallucination_reviews`) listadas em `collections.py`.
- **Fila assíncrona via Redis Streams**, a API não chama o grafo diretamente, ela publica um `AgentEvent` (`src/infra/messaging/event.py` / `publisher.py`) no stream `AGENT_STREAM_CHATBOT`, e o consumer (`src/infra/messaging/consumer.py`), iniciado no `lifespan` do FastAPI, lê o grupo de consumer, chama `handle_chat_event` (que por sua vez roda `execute_turn` do workflow) e grava o resultado via `result_store.py`, com nova tentativa automática (`AGENT_CONSUMER_MAX_ATTEMPTS`) e reclamo de mensagens pendentes (`xautoclaim`) em caso de falha.
- **Guardrails e privacidade**, `src/core/guardrails/` concentra a detecção de padrões de prompt injection (`injection_patterns.py`) e a anonimização de PII (`anonymize.py`), aplicada tanto na entrada quanto na saída do `execute_turn` (`src/workflow/runner.py`) antes de qualquer log de interação ser persistido no Mongo.
- **CLI/loop de chat local, não API HTTP síncrona**, ao rodar `python main.py` a aplicação conecta no Mongo, compila o grafo e processa cada mensagem digitada no terminal chamando `execute_turn` diretamente, sem Redis, sem fila e sem HTTP — é o caminho mais rápido para testar o comportamento dos agentes durante o desenvolvimento, mas não é o modo usado pela API de produção.
- **Agentes especialistas**, cada nó de agente em `src/workflow/nodes/` tem um prompt correspondente em `src/agents/specialist/` (ex.: `orchestrator_prompt.py`, `router_prompt.py`, `judge_prompt.py`), e a base compartilhada de agente (memória, prompt, execução) fica em `src/agents/base/`.
- **RAG sobre FAQ**, `src/rag/` mantém um índice FAISS (`vectorstore/faiss_store.py`) construído a partir de `src/rag/FAQ_v1.pdf`, consumido pelo agente `faq_reader` através de `src/agents/specialist/faq_reader/tools/faq_retriever.py`.
- **Sem `CMD`/`ENTRYPOINT` definido no Dockerfile**, o `Dockerfile` na raiz apenas instala dependências e expõe a porta `8000` (`EXPOSE 8000`), sugerindo que o processo real da imagem (`python main.py` ou `uvicorn src.api.app:app`) é definido fora do repositório, {a confirmar} no manifesto de deploy do [Infra-gitops](https://github.com/Solierrr/infra-gitops).

```Tree do Repositório
├── main.py                          # loop de chat via terminal (CLI, não HTTP)
├── Dockerfile                       # sem CMD/ENTRYPOINT definido, EXPOSE 8000
├── requirements.txt
├── pytest.ini
├── sonar-project.properties
├── .env.example
├── LICENSE
├── src/
│   ├── agents/
│   │   ├── base/                    # agente base (memória, prompt, execução)
│   │   ├── factory/
│   │   ├── shared/
│   │   └── specialist/               # prompts: router, judge, orchestrator, faq_reader, ...
│   ├── api/
│   │   ├── app.py                   # FastAPI: lifespan, /health, inclui router de chat
│   │   ├── middleware/
│   │   ├── routes/
│   │   │   └── chat.py              # POST /chat (enfileira) e GET /chat/{event_id} (consulta)
│   │   └── schemas/
│   │       └── chat.py
│   ├── core/
│   │   ├── config/settings.py       # Settings (pydantic-settings), lê .env
│   │   ├── exceptions/
│   │   ├── guardrails/               # anonimização de PII e detecção de prompt injection
│   │   ├── llm/                      # clientes LLM (Gemini, Groq)
│   │   ├── logging/
│   │   ├── observability/
│   │   └── utils/
│   ├── infra/
│   │   ├── cache/
│   │   ├── database/
│   │   │   └── mongo/                # cliente, índices, repositórios, schemas, coleções
│   │   ├── external/
│   │   └── messaging/                # publisher, consumer, event, redis_client, result_store
│   ├── memory/
│   │   └── session/mongo_checkpointer.py  # checkpointer do LangGraph em Mongo
│   ├── rag/
│   │   ├── FAQ_v1.pdf
│   │   ├── embeddings/
│   │   ├── indexing/
│   │   ├── retrievers/
│   │   └── vectorstore/faiss_store.py
│   ├── tools/
│   └── workflow/
│       ├── graph/graph.py           # definição do StateGraph e compilação
│       ├── nodes/                   # um nó por agente/etapa do grafo
│       ├── edges/routing_edges.py   # funções de decisão condicional entre nós
│       ├── state/state.py           # GraphState
│       ├── runner.py                # execute_turn: roda o grafo por turno
│       └── event_handler.py         # ponte entre evento do Redis e execute_turn
└── tests/                            # espelha a estrutura de src/
```
