# Modo debug (`POST /debug/chat`)

Roda um turno do assistente e devolve, junto da resposta, o que cada nó do grafo
recebeu e devolveu e cada chamada de LLM feita dentro dele. É para o playground do
sandbox e para uso interno; não faz parte do contrato do `/chat` e não aparece no OpenAPI.

## Segurança

A rota responde `404` quando qualquer uma das condições abaixo falha, sem revelar que existe:

- `DEBUG_ADMIN_SUBS` tem ao menos um UUID válido. Não há outra flag: o modo está sempre
  ativo, e esvaziar a lista é o que o desliga.
- `ENVIRONMENT` é `LOCAL`, `DEV`, `QA` ou `PROD` (sem diferenciar maiúsculas). É uma
  lista de permitidos: um valor desconhecido (`PRD`, `staging`, vazio) bloqueia, mesmo
  com admins configurados.

Em PROD o modo funciona como nos outros ambientes, e quem controla o acesso é
`DEBUG_ADMIN_SUBS`: sem admins listados a rota responde 404; para fechá-la de novo,
esvazie a lista. O turno usa o grafo e os
LLMs reais, com a identidade do admin: gasta cota e custo reais, e as leituras no
`api-core` são dados reais. Em PROD, use só contas de teste.

Depois disso, o JWT é validado pelo mesmo JWKS do `/chat`:

| Situação | Status |
|---|---|
| Sem `Authorization: Bearer` ou token inválido | `401` |
| `sub` fora de `DEBUG_ADMIN_SUBS` (ou lista vazia) | `403` |

Cada turno autorizado deixa uma linha de log com o `sub` e o ambiente
(`Turno de debug (sub=..., ambiente=...)`), para ter rastro de quem usou.

`DEBUG_ADMIN_SUBS` é uma lista de UUIDs separados por vírgula. Entradas que não são
UUID são ignoradas; lista vazia (ou só com entradas inválidas) fecha a rota com 404.

## Requisição

Mesmo corpo do `/chat`, mais a persona (opcional):

```json
{ "conversation_id": "t1", "message": "oi", "persona": "demandante" }
```

`persona` é `demandante` (padrão) ou `profissional`. O token do usuário é repassado ao
turno como no `/chat`.

## Resposta

```json
{
  "response": "...",
  "specialists_used": ["faq_reader"],
  "workflow_steps": ["router", "faq_reader"],
  "messenger_conversation_id": null,
  "debug": {
    "environment": "QA",
    "persona": "demandante",
    "persisted": true,
    "duration_ms": 1840.2,
    "route": "faq_reader",
    "judge": { "status": "approved", "retries": 0 },
    "nodes": [
      {
        "order": 1,
        "node": "router",
        "started_at": "2026-10-21T12:00:00+00:00",
        "duration_ms": 412.5,
        "status": "ok",
        "input": { "message_count": 1, "last_message": { "type": "human", "content": "oi" } },
        "output": { "route": "faq_reader" },
        "llm_calls": [
          {
            "model": "llama-3.3",
            "prompt": [{ "type": "human", "content": "..." }],
            "completion": "faq_reader",
            "tokens_in": 120,
            "tokens_out": 4,
            "latency_ms": 380.1,
            "error": null
          }
        ],
        "error": null
      }
    ],
    "llm_calls_outside_nodes": [],
    "truncated": false
  }
}
```

- `nodes` segue a ordem de execução. Um nó que roda de novo (por exemplo o
  `orchestrator` depois de um retry do `judge`) aparece como outro registro.
- `output` é o que o nó devolveu ao estado; por isso `route`, `judge_status`,
  `judge_retries` e `turn_agents` aparecem sem código por nó.
- `input` traz só as chaves de controle do estado, a quantidade de mensagens e a
  última mensagem, não o histórico inteiro.
- `tokens_*` e `model` podem vir `null` quando o provedor não informa.
- Se o turno falha, a rota devolve `500` com `{ "detail": "...", "debug": {...} }`,
  e o `debug` traz o que foi coletado até ali.

## Execução personalizada de um nó

Reexecuta só um nó de um turno já feito, com os prompts `system` trocados, e para nele.

```json
{
  "conversation_id": "t1", "message": "oi",
  "custom": {
    "turn": 0, "node": "router", "occurrence": 0, "stop_after_node": true,
    "prompts": [{ "call": 0, "prompt": [{ "type": "system", "content": "texto novo" }, { "type": "human", "content": "oi" }] }]
  }
}
```

- `turn` é a posição do turno na conversa de debug (0 é o primeiro) e `occurrence` é a
  qual execução do nó no turno (um nó pode repetir, como o router depois de um
  especialista). `prompts[].call` é o índice da chamada de LLM dentro do nó.
- O estado de entrada vem do checkpoint da thread `debug:<sub>:<conversation_id>`: ele
  é copiado para uma thread descartável (apagada ao fim), o grafo roda só esse nó e
  para nele. A conversa de debug original não muda.
- Só mensagens `system` são trocadas, na mesma posição em que estavam no prompt; o
  histórico e a pergunta do usuário nunca mudam.
- A resposta traz só esse nó em `debug.nodes` e `debug.custom` com `node`, `turn`,
  `occurrence`, `stopped: true`, `overrides_applied` e `next` (os nós que viriam em
  seguida). `response` vem vazio.
- Erros: `404` (turno, nó ou ocorrência inexistente), `409` (não foi possível
  reconstruir a entrada do nó), `400` (corpo inválido, `VALIDATION_ERROR`) e `422` (nó bloqueado).
- `debug.turn` (resposta normal e `500`) é o índice do turno que acabou de rodar: é o
  valor a enviar em `custom.turn` para reexecutar um nó dele. Vem `null` se o histórico
  não pôde ser lido.
- Nós que não podem ser reexecutados respondem `422` com o motivo. Hoje só `operational_delegate`: no debug a delegação ao ai-operational é
  simulada (nada é enviado ao outro agente, nem nos turnos normais de debug), então não
  há prompt para editar.
- A mesma chamada de LLM que o wrapper de modelo repete (execução externa e interna com
  as mesmas mensagens) conta uma vez só, tanto no `debug` quanto no `call` dos `prompts`.
- Se o prompt veio com `prompt_complete: false`, não o reenvie: o texto
  mascarado substituiria o original.
- Os checkpoints expiram em `CHECKPOINT_TTL_DIAS` (30 por padrão); depois disso o turno
  responde `404`. A leitura do histórico para no máximo 2.000 checkpoints.
- Cada reexecução deixa uma linha de log com o `sub`, o nó, o turno e a quantidade de
  prompts, sem o conteúdo dos prompts.


## Limites e privacidade

- CPF, CNPJ, telefone e e-mail são trocados por `[CPF]`, `[CNPJ]`, `[TELEFONE]` e
  `[EMAIL]` em todo o bloco `debug`. Isso é uma segunda camada: o texto original
  continua indo ao LangSmith como no `/chat`.
- `pii_map`, `user_id` e `user_memory` do estado nunca são copiados.
- Os prompts das chamadas de LLM saem inteiros, sem limite de tamanho, para poderem
  ser editados na execução personalizada. Cada chamada de LLM traz `prompt_complete`,
  que é `false` quando alguma mensagem `system` teve dado pessoal mascarado; nesse caso
  o prompt não deve ser editado.
- Os demais textos (entrada e saída dos nós, resposta do LLM) são cortados em 4.000
  caracteres; quando algo é cortado, `truncated` é `true`.
- O trace dos nós existe só na resposta do turno e não é guardado. O que o turno normal grava no `api-messenger` (conversa, mensagens e steps) está em "O que o modo debug grava e não grava".

## O que o modo debug grava e não grava

O turno normal roda com `persist=False, save_history=True`: cria a conversa e grava a mensagem do usuário, a resposta e os steps de observabilidade no `api-messenger` (a conversa nasce com `userDetails.source = "debug"`, `assistant` e `threadId`, para aparecer em Conversas e Dashboards e ser filtrada do uso real), mas não lê nem atualiza a memória de longo prazo. A execução personalizada de um nó não grava nada. Duas ressalvas:

- O estado do grafo continua indo para o checkpointer, na thread
  `debug:<sub>:<conversation_id>`, separada das conversas reais.
- O tráfego aparece no LangSmith com `metadata.source = "debug"` (o `/chat` usa
  `"chat"`) e `metadata.persona`, para filtrar do uso real.

## Variáveis

| Variável | Padrão | Uso |
|---|---|---|
| `DEBUG_ADMIN_SUBS` | vazio | UUIDs (`sub` do JWT) autorizados, separados por vírgula |

Exemplo para testar no QA:

```bash
curl -X POST "$URL/debug/chat" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"conversation_id":"t1","message":"oi"}'
```

## Fora do escopo

Este modo só existe no `ai-assistant`. Os outros serviços não têm equivalente, e o
coletor (`src/workflow/observability/debug_tracker.py`) pode ir para a `solaria-lib`
se for reaproveitado.
