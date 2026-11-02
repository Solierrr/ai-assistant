<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# API

O [contrato HTTP](https://github.com/Solierrr/ai-assistant/blob/main/openapi.yaml) é gerado por `make openapi`, e as rotas `/docs` e `/openapi.json` só existem quando `DOCS_ENABLED` está ligado. A rota `/chat` e as chamadas A2A exigem o JWT da pessoa.

```http
POST /chat
Authorization: Bearer <token>
Content-Type: application/json

{"conversation_id":"consulta-local","message":"Quero comparar placas para meu projeto"}
```

A resposta traz o texto, o `outcome`, o `reason`, os especialistas acionados, as etapas e o `messenger_conversation_id`, que é o identificador usado para avaliar a conversa no serviço de mensagens. O retorno chega de uma vez, sem streaming.

O Agent Card fica em `/.well-known/agent-card.json` e o JSON-RPC do A2A em `/a2a`, com a persona enviada nos metadados do A2A, e por isso o protocolo fica fora do OpenAPI. A rota `/debug/chat` é administrativa, também fora do contrato público, e só atende os administradores configurados.

Os erros HTTP seguem o formato de [ERRORS.md](https://github.com/Solierrr/docs-warehouse/blob/main/docs/standards/ERRORS.md), mas uma resposta 200 ainda pode indicar recusa, degradação ou falha de ferramenta, por isso o cliente deve conferir os campos `outcome` e `reason`.