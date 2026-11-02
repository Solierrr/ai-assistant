<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Arquitetura

A aplicação FastAPI executa um grafo LangGraph. O [grafo](https://github.com/Solierrr/ai-assistant/blob/main/src/workflow/graph/graph.py) reúne guardrail de entrada, resumo, roteador, especialistas, orquestrador, juiz e guardrail de saída.

```mermaid
flowchart LR
 C[Cliente ou agente] -->|HTTP ou A2A e JWT| A[FastAPI]
 A --> G[LangGraph]
 G --> M[(MongoDB)]
 G --> Q[(Qdrant)]
 G -->|MCP e X-Service-Key| MCP[mcp-database]
 G -->|A2A e JWT| O[ai-operational]
 G -->|HTTP e JWT| CORE[api-core]
 G -->|HTTP e chave de serviço| MSG[api-messenger]
```

O código se divide entre `src/api/`, com as rotas e os schemas, `src/workflow/`, com a execução e a revisão das respostas, e `src/agents/`, com os especialistas e os prompts. Os clientes externos ficam em `src/infra/`, e `src/rag/` mantém a ingestão e a recuperação do FAQ.

| Integração | Uso |
|---|---|
| `api-auth` | Validação JWT por JWKS público |
| `mcp-database` | Ferramentas de recomendação com `X-Service-Key` e suporte a chave legada |
| `api-core` | Unidades da pessoa, com JWT |
| `api-messenger` | Conversas, mensagens e etapas |
| `ai-operational` | Delegação A2A com JWT e persona |
| Qdrant e provedores LLM | Recuperação vetorial e geração |

JWT e persona ficam no contexto da requisição, fora do estado persistido. O runner usa lock em memória por conversa e compara o dono salvo no checkpoint. A leitura desse dono, porém, continua em caso de erro no checkpoint. Essa limitação não deve ser confundida com isolamento entre réplicas.

A delegação operacional encerra o grafo diretamente, para preservar o texto da proposta, enquanto os demais especialistas voltam ao roteador. A memória e os índices estão descritos em `database/`, a versão vem de `version.txt`, o readiness confere o Mongo com limite de dois segundos e a telemetria registra etapas e custos, com rastreamento opcional.

## Ecossistema de IA e diagramas

Os 5 serviços de IA e como se ligam:

| Serviço | Papel | Fala com |
|---|---|---|
| `ai-assistant` (este) | Agente principal: recomenda placas, profissionais e empresas, responde dúvidas da plataforma e calcula estimativas solares | Usuário (web), `ai-operational` e `ai-geographic` (A2A) |
| `ai-operational` | Operar o SaaS: guiar tarefas, mostrar dados do usuário e executar ações só com aceite explícito | Só o `ai-assistant` (A2A) |
| `ai-geographic` | Copiloto de campo do profissional: rota, clima e potencial solar | App mobile; delega produtos ao `ai-assistant` (A2A) |
| `ai-validation` | Valida certificados NR-10 e NR-35 e CNPJ de empresas | `web-app` (REST, com o JWT do usuário) |
| `ai-accessibility` | Modera imagens e sugere texto alternativo | Serviço interno (REST, chave de serviço) |

## 1. Visão de alto nível

```mermaid
flowchart TB
    subgraph Clientes
        WEB["web-app<br/>demandante e profissional"]
        MOB["app mobile<br/>profissional em campo"]
        UPL["serviço chamador<br/>(backend interno)"]
    end

    subgraph IA["Serviços de IA (FastAPI)"]
        ASS["ai-assistant<br/>agente principal"]
        OPS["ai-operational<br/>ações no SaaS"]
        GEO["ai-geographic<br/>copiloto de campo"]
        VAL["ai-validation<br/>certificados e CNPJ"]
        ACC["ai-accessibility<br/>moderação e alt text"]
    end

    subgraph Plataforma["Plataforma Solaria"]
        CORE["api-core<br/>SaaS"]
        MSG["api-messenger<br/>mensagens e observabilidade"]
        APIG["api-google<br/>viabilidade solar"]
    end

    subgraph Ferramentas["Dados e ferramentas externas"]
        MCPDB["mcp-database (MCP)"]
        MAPS["Google Maps (MCP)"]
        QDR[("Qdrant<br/>RAG do FAQ")]
        BILL["billscanner"]
        BR["BrasilAPI<br/>Receita Federal"]
    end

    MONGO[("MongoDB<br/>checkpoints e memória")]
    LLM["Provedores de LLM<br/>Gemini, Groq, OpenAI"]

    WEB -->|"POST /chat + JWT"| ASS
    MOB -->|"POST /chat + JWT"| GEO
    WEB -->|"REST + JWT do usuário"| VAL
    UPL -->|"REST + X-Service-Key"| ACC

    GEO ==>|"A2A: produtos"| ASS
    ASS ==>|"A2A: ações no SaaS"| OPS

    OPS -->|"JWT do usuário"| CORE
    ASS -->|"unidades do usuário"| CORE
    ASS -->|MCP| MCPDB
    ASS --> QDR
    ASS --> BILL
    GEO -->|MCP| MAPS
    GEO --> APIG
    VAL --> BR

    ASS --> MONGO
    GEO --> MONGO
    OPS --> MONGO
    ASS -.-> MSG
    GEO -.-> MSG
    OPS -.-> MSG
    IA ==>|"todos os 5 serviços"| LLM
```


Linhas grossas entre serviços de IA são chamadas entre agentes (A2A); as tracejadas até o `api-messenger` são o registro das mensagens e dos passos de cada turno. O JWT do usuário é emitido pelo `api-auth` e validado por cada serviço que recebe conversa. O JWT do usuário atravessa a cadeia inteira: o `ai-geographic` repassa o do profissional ao `ai-assistant`, e o `ai-assistant` repassa o do usuário ao `ai-operational`, que o usa no `api-core`. Assim cada serviço age com as permissões de quem pediu, nunca com uma credencial própria mais ampla.

## 2. Como uma mensagem percorre o grafo

O grafo é um `StateGraph` do LangGraph (`src/workflow/graph/graph.py`) com 12 nós. O roteador escolhe um especialista por vez; cada especialista devolve o resultado ao roteador, que decide se já há informação suficiente (até 3 especialistas por pedido, `MAX_SPECIALISTS_PER_REQUEST`) e só então chama o orquestrador.

```mermaid
flowchart TD
    START([mensagem do usuário]) --> IG["input_guardrail<br/>regex de injeção, anonimiza PII,<br/>classifica por LLM"]
    IG -->|"bloqueada"| END1(["REFUSED<br/>ou DEGRADED se o guardrail falhou<br/>(detalhe em 2.1)"])
    IG -->|permitida| CM["condense_memory<br/>resume conversa longa"]
    CM --> R{"router<br/>escolhe um especialista<br/>por vez"}

    R --> FAQ["faq_reader<br/>RAG no Qdrant"]
    R --> SPS["solar_panel_specialist<br/>placas e fixação (MCP)"]
    R --> PS["professional_suggester<br/>profissionais (MCP)"]
    R --> AS["agency_suggester<br/>empresas (MCP)"]
    R --> SC["solar_calculator<br/>estimativa (billscanner)"]
    R --> OD["operational_delegate<br/>A2A para o ai-operational"]

    FAQ --> R
    SPS --> R
    PS --> R
    AS --> R
    SC --> R

    OD -->|"proposta ou confirmação,<br/>exatamente como veio"| END2(["ANSWERED<br/>ou TOOL_FAILED se o ai-operational<br/>estiver indisponível"])

    R -->|"responde direto<br/>(nenhum especialista necessário)"| OG
    R -->|"informação suficiente"| ORQ["orchestrator<br/>compõe a resposta final"]
    ORQ --> J{"judge<br/>alucinação e aderência"}
    J -->|"reprovada: 1 nova tentativa"| ORQ
    J -->|aprovada| OG["output_guardrail<br/>conformidade por LLM,<br/>remove PII"]
    J -->|"reprovada de novo"| BL["resposta trocada por<br/>pedido de reformulação"]
    BL --> OG

    OG -->|"aprovada ou corrigida"| OK(["ANSWERED<br/>resposta ao usuário"])
    OG -->|"era o pedido de reformulação"| RJ(["REFUSED<br/>ANSWER_REJECTED"])
    OG -->|"guardrail falhou:<br/>mensagem genérica"| DG(["DEGRADED<br/>GUARDRAIL_UNAVAILABLE"])

    classDef ok fill:#d4edda,stroke:#28a745,color:#000
    classDef recusa fill:#f8d7da,stroke:#dc3545,color:#000
    classDef aviso fill:#fff3cd,stroke:#e0a800,color:#000
    class OK,END2 ok
    class END1,RJ recusa
    class DG aviso
```

Verde é sucesso (`ANSWERED`), vermelho é recusa e amarelo é degradação. Quando o roteador não precisa de especialista (por exemplo, uma saudação), ele responde direto e a resposta segue para o guardrail de saída, sem passar pelo juiz. Os dois guardrails e o juiz têm caminho próprio para recusa e falha; eles estão detalhados nas subseções 2.1 a 2.3.

### 2.1 Guardrail de entrada

Antes de qualquer especialista, a mensagem passa por três filtros em sequência. Se a avaliação falha, o guardrail bloqueia (fail-closed): nunca deixa passar o que não conseguiu avaliar.

```mermaid
flowchart TD
    M(["mensagem do usuário"]) --> R1{"regex de injeção<br/>de prompt?"}
    R1 -->|sim| B1(["REFUSED<br/>MANIPULATION_ATTEMPT"])
    R1 -->|não| R2{"pede dado interno?<br/>(prompt, chaves, credenciais)"}
    R2 -->|sim| B2(["REFUSED<br/>INTERNAL_DATA_REQUEST"])
    R2 -->|não| AN["anonimiza PII<br/>CPF, CNPJ, telefone e e-mail<br/>viram tokens; o mapa fica no estado"]
    AN --> CL["classificador por LLM<br/>devolve CATEGORIA e JUSTIFICATIVA"]
    CL -->|"falha ou formato inválido"| B3(["DEGRADED<br/>GUARDRAIL_UNAVAILABLE"])
    CL -->|APROVADO| OK(["segue para condense_memory<br/>com o texto anonimizado"])
    CL -->|"FORA_ESCOPO ou REDIRECIONAR"| B4(["REFUSED<br/>OUT_OF_SCOPE"])
    CL -->|MANIPULACAO| B1
    CL -->|DADOS_INTERNOS| B2
    CL -->|INFORMACAO_FALSA| B5(["REFUSED<br/>FALSE_INFORMATION"])
```

Toda recusa devolve a mesma mensagem ao usuário ("não posso processar essa solicitação por políticas de segurança"), sem revelar qual filtro barrou.

### 2.2 Juiz, recusa da resposta e guardrail de saída

O orquestrador escreve a resposta, mas quem decide se ela sai é o juiz, uma chamada separada. Se a resposta é reprovada, ela é apagada do estado e o orquestrador refaz uma vez; se reprovar de novo, o usuário recebe um pedido para reformular a pergunta.

```mermaid
flowchart TD
    ORQ["orchestrator<br/>escreve a resposta"] --> J{"judge<br/>STATUS: APROVADO ou REPROVADO"}
    J -->|APROVADO| OG
    J -->|"REPROVADO, ou o juiz falhou,<br/>ou respondeu fora do formato"| Q{"já refez<br/>uma vez?"}
    Q -->|"não"| RT["apaga a resposta<br/>judge_retries = 1"]
    RT --> ORQ
    Q -->|"sim"| BL["apaga a resposta e coloca:<br/>Não foi possível gerar uma resposta confiável.<br/>Poderia reformular sua pergunta?"]
    BL --> OG
    OG["output_guardrail<br/>revisão de conformidade por LLM"] -->|APROVADO| FIM(["resposta ao usuário<br/>PII devolvida pelo mapa"])
    OG -->|"CORRIGIDO: texto revisado"| FIM
    OG -->|"falha ou formato inválido"| FB["resposta genérica:<br/>Não foi possível processar sua solicitação<br/>no momento. Tente novamente em instantes."]
    FB --> FIM2(["DEGRADED<br/>GUARDRAIL_UNAVAILABLE"])
    BL -.-> RJ(["REFUSED<br/>ANSWER_REJECTED"])
```

Um juiz que falha conta como reprovação: a resposta só sai se o juiz disser explicitamente que aprova.

### 2.3 Como o resultado do turno é decidido

O `/chat` sempre responde 200 para o que acontece dentro da conversa e informa o desfecho em `outcome` e `reason`, lidos dos passos registrados no turno (`src/api/outcome.py`).

```mermaid
flowchart TD
    S(["estado final do turno"]) --> A{"algum passo<br/>input_guardrail_blocked_*?"}
    A -->|"falha_avaliacao_guardrail"| D1(["DEGRADED<br/>GUARDRAIL_UNAVAILABLE"])
    A -->|"outra categoria"| R(["REFUSED<br/>motivo da categoria"])
    A -->|não| B{"resposta é a mensagem genérica<br/>do guardrail de saída?"}
    B -->|sim| D1
    B -->|não| C{"houve judge_blocked?"}
    C -->|sim| R2(["REFUSED<br/>ANSWER_REJECTED"])
    C -->|não| E{"resposta é a de<br/>agente operacional indisponível?"}
    E -->|sim| T(["TOOL_FAILED<br/>OPERATIONAL_AGENT_UNAVAILABLE"])
    E -->|não| OK(["ANSWERED"])
```

Pontos que explicam o desenho:

- **Hub e raios.** Todo especialista volta ao roteador. Isso permite combinar fontes (por exemplo, FAQ e recomendação de placas) sem acoplar um especialista ao outro, e um especialista novo entra registrando a rota em `src/workflow/config.py`.
- **Atalho do agente operacional.** A resposta do `operational_delegate` não passa pelo orquestrador, pelo juiz nem pelo guardrail de saída: uma proposta de ação precisa chegar ao usuário exatamente como foi escrita pelo agente que a vai executar, e esse agente já aplicou os guardrails dele. Quando ele espera a decisão do usuário (aceitar, recusar, questionar), o estado guarda `awaiting_decision` e a próxima mensagem volta direto a ele.
- **Juiz com uma nova tentativa.** Se o juiz reprova, o orquestrador refaz a resposta uma vez (`MAX_JUDGE_RETRIES = 1`); reprovada de novo, o turno termina como `REFUSED / ANSWER_REJECTED`.
- **Falha não é erro.** O que acontece dentro da conversa volta como `200` com `outcome` e `reason` (`ANSWERED`, `REFUSED`, `DEGRADED`, `TOOL_FAILED`), para o cliente tratar sem confundir com falha de infraestrutura.

## 3. Delegação A2A

O A2A (Agent2Agent, JSON-RPC) é como um agente pede trabalho a outro sem conhecer o interior dele. O módulo é o `ai_lib.a2a` da `solaria-lib`; cada serviço publica um Agent Card em `GET /.well-known/agent-card.json` e recebe chamadas em `POST /a2a`.

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuário
    participant A as ai-assistant
    participant O as ai-operational
    participant C as api-core

    U->>A: "Cadastra uma placa de 550 Wp por R$ 900"
    A->>A: guardrail de entrada e roteador (operational_delegate)
    A->>O: A2A: texto + JWT do usuário + persona
    O->>C: lê modelos aprovados e empresa do usuário (JWT)
    C-->>O: dados do usuário
    O->>O: monta a proposta, assina e guarda como pendente
    O-->>A: "Posso cadastrar esta oferta, mas só depois do seu aceite..."
    A-->>U: proposta exatamente como foi escrita
    Note over A,O: awaiting_decision = true: a próxima mensagem volta ao ai-operational

    U->>A: "sim"
    A->>O: A2A: "sim" (mesma conversa)
    O->>O: confere assinatura, validade e dono da proposta
    O->>C: POST /offers com o JWT do usuário
    C-->>O: oferta criada
    O-->>A: confirmação
    A-->>U: "Pronto, a oferta foi cadastrada"
```

A ligação no sentido contrário é a do `ai-geographic`: quando o profissional em campo pergunta sobre produtos, o copiloto delega ao `ai-assistant`.

```mermaid
sequenceDiagram
    autonumber
    actor P as Profissional (app mobile)
    participant G as ai-geographic
    participant A as ai-assistant
    participant M as mcp-database

    P->>G: "Qual placa serve para telhado pequeno?"
    G->>G: router escolhe product_advisor
    G->>A: A2A: texto + JWT do profissional + persona "profissional"
    A->>A: valida o JWT (sem token ou inválido: responde pedindo login)
    A->>A: confere o dono da conversa (context_id)
    A->>M: MCP: recomendar_ofertas
    M-->>A: ranking determinístico
    A->>A: grafo completo: guardrails, juiz e guardrail de saída
    A-->>G: texto da resposta
    G-->>P: resposta no tom do copiloto
    Note over G,A: se a delegação falhar, o turno termina como<br/>TOOL_FAILED (PRODUCT_ADVISOR_UNAVAILABLE)
```

Com a persona `profissional` o assistente recomenda só com dados públicos, sem usar unidade nem empresa cadastradas.

Nada grava sem o aceite exato do usuário. A proposta é assinada (HMAC), expira em 15 minutos, é presa ao usuário que a pediu e há um teto de gravações por conversa. As regras estão descritas no `docs/ARCHITECTURE.md` do `ai-operational`.

## 4. Dados e memória

```mermaid
flowchart LR
    subgraph Turno["Um turno"]
        REQ["POST /chat<br/>JWT + conversation_id"]
        G["grafo LangGraph"]
        BG["extração de fatos<br/>em segundo plano"]
    end

    CTX["variáveis de contexto<br/>JWT e persona<br/>(nunca no estado do grafo)"]
    CK[("Mongo: conversation_checkpoints<br/>curto prazo, TTL 30 dias")]
    UM[("Mongo: user_memory<br/>fatos do usuário, longo prazo")]
    MSG["api-messenger<br/>mensagens e passos do turno"]
    QD[("Qdrant: coleção faq<br/>FAQ_v1.pdf em trechos")]

    REQ --> CTX
    REQ --> G
    G <--> CK
    UM -->|"lido no início do turno"| G
    G --> BG
    BG -->|"gravado no fim"| UM
    G -->|"mensagem do usuário e da resposta"| MSG
    G -->|"faq_reader: busca por similaridade"| QD
```

| Camada | Onde | Para quê |
|---|---|---|
| Sessão por usuário | `thread_id` no checkpointer do LangGraph (Mongo) | Continuar a conversa entre turnos e reinícios; o acesso é conferido por usuário (`conversation_access`) |
| Longo prazo | `user_memory` no Mongo | Fatos do usuário aprendidos em conversas anteriores |
| Histórico e observabilidade | `api-messenger` | Cada turno grava a mensagem do usuário, a resposta e os passos (`StepTracker`) |
| RAG | Qdrant, coleção `faq` | O `faq_reader` busca trechos do `FAQ_v1.pdf` e responde citando a fonte |

O JWT e a persona ficam em variáveis de contexto porque o checkpointer grava o estado inteiro no Mongo: um token no estado seria persistido.

### 4.1 O ciclo de um turno no `runner`

```mermaid
sequenceDiagram
    autonumber
    participant API as POST /chat
    participant R as runner (execute_turn)
    participant MG as MongoDB
    participant MS as api-messenger
    participant G as grafo LangGraph
    participant BG as tarefa em segundo plano

    API->>R: conversation_id, mensagem, JWT, persona
    R->>R: trava a conversa (um turno por vez)
    R->>R: decodifica o JWT e confere o dono da conversa
    R->>MS: cria ou reaproveita a conversa e grava a mensagem anonimizada
    R->>MG: lê os fatos do usuário (user_memory)
    R->>G: ainvoke com StepTracker, OpenTelemetry e LangSmith opcional
    G-->>R: estado final (resposta, passos, desfecho)
    R->>MS: grava a resposta anonimizada com specialists_used e workflow_steps
    R-->>API: resposta, outcome e reason
    R-)BG: extrai fatos novos da troca
    BG->>MG: atualiza user_memory
```

### 4.2 RAG do FAQ

A fonte externa indicada é o `FAQ_v1.pdf`, indexado no Qdrant Cloud. O índice é montado fora da requisição e consultado durante o turno.

**Ingestão** (`python -m src.rag.indexing.ingest_faq`, `src/rag/vectorstore/qdrant_store.py`):

```mermaid
flowchart TD
    PDF["FAQ_v1.pdf"] --> L["PyPDFLoader"]
    L --> SP["divide em trechos<br/>500 caracteres, sobreposição 50"]
    SP --> V{"algum trecho<br/>extraído?"}
    V -->|"não"| ERR(["erro: aborta sem tocar no índice"])
    V -->|"sim"| ID["id de cada trecho = uuid5 do conteúdo"]
    ID --> EM["embeddings Gemini<br/>gemini-embedding-001"]
    EM --> UP[("Qdrant, coleção faq<br/>cria a coleção se não existir<br/>upsert idempotente")]
    UP --> DEL["remove trechos órfãos<br/>(ids que não estão no PDF atual)"]
    DEL --> OK(["índice atualizado"])

    classDef ok fill:#d4edda,stroke:#28a745,color:#000
    classDef recusa fill:#f8d7da,stroke:#dc3545,color:#000
    class OK ok
    class ERR recusa
```

**Consulta durante um turno** (`faq_reader_node` e `faq_retriever`):

```mermaid
flowchart TD
    Q(["dúvida sobre a plataforma"]) --> R{"router"}
    R -->|"escolhe faq_reader"| FR["faq_reader<br/>agente com a ferramenta faq_retriever"]
    FR --> T["faq_retriever(pergunta)"]
    T --> EQ["embedding da pergunta<br/>Gemini gemini-embedding-001"]
    EQ --> SS["busca por similaridade<br/>Qdrant, coleção faq, k = 3"]
    SS -->|"3 trechos"| TR["trechos do FAQ"]
    SS -->|"nenhum resultado"| N1["Nenhum trecho relevante<br/>encontrado no FAQ."]
    SS -->|"Qdrant fora, ou coleção vazia<br/>(ingestão não rodou)"| N2["FAQ indisponível<br/>no momento."]
    TR --> RES["faq_reader redige a resposta<br/>a partir do que a ferramenta devolveu"]
    N1 --> RES
    N2 --> RES
    RES --> R2{"router<br/>já há informação suficiente?"}
    R2 -->|"precisa de outra fonte (até 3)"| OUT["outro especialista"]
    OUT --> R2
    R2 -->|"sim"| ORQ["orchestrator"]
    ORQ --> J{"judge"}
    J -->|"aprovada"| OG["output_guardrail"]
    J -->|"reprovada: 1 nova tentativa"| ORQ
    J -->|"reprovada de novo"| RJ(["REFUSED<br/>ANSWER_REJECTED"])
    OG --> OK(["ANSWERED<br/>resposta ao usuário"])

    classDef ok fill:#d4edda,stroke:#28a745,color:#000
    classDef recusa fill:#f8d7da,stroke:#dc3545,color:#000
    class OK ok
    class RJ recusa
```

O índice é criado pela ingestão. Em qualquer um dos três resultados da busca, o `faq_reader` responde com o que a ferramenta devolveu, e o desfecho do turno segue as regras da seção 2.3. Quem confere a resposta final contra alucinação é o juiz.

## 5. Observabilidade e custo

```mermaid
flowchart LR
    NOS["cada nó e cada chamada de LLM ou ferramenta"] --> ST["StepTracker<br/>tokens, latência, custo, erro por passo"]
    ST --> MSG["api-messenger<br/>llm-observability"]
    NOS --> OT["OpenTelemetry<br/>métricas e traces OTLP"]
    NOS -.->|"opcional, SOLARIA_LANGSMITH_ENABLED"| LS["LangSmith<br/>trace por turno, PII mascarada"]
    NOS --> DBG["POST /debug/chat<br/>entrada e saída de cada nó, só admins"]
```

O requisito de SRE da disciplina e onde cada item está:

| Item | Situação |
|---|---|
| Custo por chamada | Existe: `costUsd` por passo, calculado dos tokens e da tabela de preços `src/core/config/model_pricing.py` |
| Latência entre agentes e tempo total | Registrada por passo no `StepTracker` e enviada ao `api-messenger` |
| Índice de erros | Cada passo de erro é registrado com categoria (`rate_limited`, `timeout`, `connection_error`), e todo turno devolve `outcome` e `reason` |

## 6. Requisitos da disciplina e onde cada um está

| Requisito (Inteligência Artificial, mínimo para o 7,0) | Onde está |
|---|---|
| API em FastAPI | `src/api/app.py` (`/chat`, `/health`, `/ready`, `/a2a`) |
| Multiagente, no mínimo 5 agentes | 8 agentes com prompt próprio (roteador, orquestrador, juiz, FAQ, especialista em placas, sugestor de profissionais, sugestor de empresas, calculador solar) e o nó que delega ao `ai-operational`; fora deste serviço há ainda os agentes do `ai-operational` e do `ai-geographic` |
| LangChain para os agentes | `src/agents/base/base_agent.py` (`build_agent`) e um módulo de prompt por agente |
| LangGraph para orquestração | `src/workflow/graph/graph.py` |
| Sessões por usuário | JWT validado por requisição e `thread_id` por conversa, com checagem de dono |
| Memória de longo prazo | `user_memory` (`src/workflow/memory/memory_extraction.py`) |
| MCP e A2A | MCP com o `mcp-database` (`src/infra/mcp/client.py`); A2A como servidor (`src/a2a/server.py`) e como cliente (`operational_delegate_node.py`) |
| RAG com fonte externa indicada | `faq_reader` com Qdrant (`src/rag/`), fonte `FAQ_v1.pdf`; recomendações vêm do `mcp-database` e da `api-recommendation` |
| Juiz contra alucinação | `src/workflow/nodes/judge_node.py` |
| Guardrail | Entrada e saída: regex de injeção, anonimização de PII, classificação e revisão por LLM |
| Observabilidade e SRE | Seção 5 |
| Desenho de arquitetura de alto nível | Seção 1 deste documento |

## 7. Complexidade do projeto

O que torna este projeto mais do que um chatbot com um prompt:

1. **Orquestração com estado.** 12 nós, arestas condicionais, laço do roteador com limite de especialistas e laço do juiz com nova tentativa, tudo sobre um estado tipado persistido a cada passo.
2. **Três protocolos de integração.** REST para clientes e serviços da plataforma, MCP para ferramentas de dados e Google Maps, A2A para falar com outros agentes. Cada um tem autenticação e falhas próprias, e o desfecho de cada falha chega ao usuário de forma clara (`TOOL_FAILED` com motivo).
3. **Cadeia de agentes entre serviços.** O assistente é ao mesmo tempo servidor A2A (recebe do `ai-geographic`) e cliente A2A (delega ao `ai-operational`). O JWT do usuário precisa atravessar os dois saltos sem ser guardado no estado e sem dar mais permissão do que o usuário tem.
4. **Segurança em camadas.** Validação do JWT (RS256 por JWKS), checagem de dono da conversa, regex de injeção e de pedido de dados internos, anonimização de PII (CNPJ, CPF, telefone, e-mail) com remoção na saída, classificação por LLM na entrada e revisão de conformidade por LLM na saída, juiz contra alucinação e, para ações, aceite explícito do usuário.
5. **Três tipos de memória** com ciclos de vida diferentes: checkpoints com TTL de 30 dias, fatos de longo prazo extraídos em segundo plano e histórico no `api-messenger`.
6. **Tolerância a falhas de LLM.** Três provedores (Gemini, Groq, OpenAI) com ordem configurável e fallback entre eles, e degradação explícita (`DEGRADED`) quando o guardrail não consegue avaliar.
7. **Duas personas** (`demandante` e `profissional`) que mudam o que o agente pode ler e recomendar.
8. **Observabilidade por passo**, com custo por chamada, mais um modo debug para administradores que mostra a entrada e a saída de cada nó e permite reexecutar um nó com o prompt editado.
9. **Contrato e qualidade automatizados.** OpenAPI gerado do código e conferido no CI, erros em `application/problem+json`, `ruff`, `pytest` com cobertura e SonarQube.
