# Observabilidade com LangSmith

Tracing opcional das execuções do grafo no LangSmith. Vem **desligado** por
padrão e, por enquanto, é para QA com usuários de teste.

## Como ligar

Variáveis lidas pelo `settings` (no Infisical, pasta `/observability` do ambiente):

| Variável | Padrão | Uso |
|---|---|---|
| `SOLARIA_LANGSMITH_ENABLED` | `false` | Liga o tracing |
| `SOLARIA_LANGSMITH_API_KEY` | — | Chave do LangSmith |
| `SOLARIA_LANGSMITH_PROJECT` | `solaria-local` | Projeto (use `solaria-qa`, `solaria-prod`) |
| `SOLARIA_LANGSMITH_ENDPOINT` | padrão do SDK | Só para região ou instância própria |
| `SOLARIA_LANGSMITH_SAMPLING_RATE` | `1.0` | Fração dos turnos enviados |

**Não use `LANGSMITH_*` nem `LANGCHAIN_*`.** Esses nomes ligam o tracing global
do LangChain sozinhos: ele usa um `Client` sem anonymizer e envia também a
extração de memória em segundo plano, com a mensagem do usuário crua. A subida
da API registra um aviso se alguma delas estiver `true`.

## O que é enviado

- Um trace por turno do `/chat`, com todos os nós do grafo.
- Metadata: `conversation_id` (o do `api-messenger`, não o `thread_id`),
  `environment`, `assistant` e `source`. Tag: o ambiente em minúsculas.
- Para achar os traces de uma conversa, filtre por metadata:
  `and(eq(metadata_key, "conversation_id"), eq(metadata_value, "<id>"))`.

## Limites

- **Mascaramento por regex.** CPF, CNPJ, telefone e e-mail viram `[CPF]`,
  `[CNPJ]`, `[TELEFONE]` e `[EMAIL]`. Nome e endereço **não** são mascarados, e
  as memórias do usuário entram no prompt. Use só usuários de teste.
- **Plano gratuito:** 1 seat, 5.000 traces por mês (teto rígido até cadastrar
  cartão) e 14 dias de retenção.
- O custo por step e o histórico continuam no `StepTracker` e no
  `api-messenger` (ver `observability-cost.md`).
