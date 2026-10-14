# NPS

O NPS (0 a 10) é pedido pelo front e gravado no `api-messenger`. O `ai-assistant`
não decide quando pedir; ele só devolve o id da conversa.

## Fluxo

1. `POST /chat` devolve `messenger_conversation_id`, o id da conversa no
   `api-messenger`. O `conversation_id` que o front envia é só o `thread_id`.
2. O front decide o momento (fechar o chat ou inatividade) e mostra a escala de 0 a 10.
3. O front chama `POST /messaging/nps` no `api-messenger`, com o mesmo JWT:

```json
{ "conversationId": "<messenger_conversation_id>", "score": 9, "environment": "QA" }
```

## Regras do endpoint

- Classificação: 0-6 detrator, 7-8 neutro, 9-10 promotor. NPS = % promotores − % detratores.
- O usuário precisa participar da conversa (403 caso contrário).
- A conversa precisa ser do chatbot (422 caso contrário).
- Uma resposta por conversa (409 na segunda).

## O que o front precisa fazer

- Guardar o `messenger_conversation_id` da **última** resposta do `/chat` e usar esse valor no NPS.
- Tratar o 409 como sucesso silencioso: com gatilho por inatividade, a tela pode aparecer duas vezes.

## Limite

O id fica em memória (`_conversations_por_thread`). Depois de um restart do serviço,
a primeira mensagem de um `thread_id` antigo abre uma conversa nova no `api-messenger`,
e o `messenger_conversation_id` devolvido passa a ser o da nova conversa. Uma mesma sessão
pode então ter duas notas, uma por conversa. Para um NPS definitivo, o mapeamento
`thread_id → conversa` precisa ser persistido.
