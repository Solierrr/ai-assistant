<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Delegação operacional

O assistente encaminha um pedido de ação ao agente operacional preservando a identidade da pessoa.

```mermaid
sequenceDiagram
 participant A as Assistente
 participant O as ai-operational
 A->>O: A2A com JWT, persona e contexto
 alt Proposta ou resposta disponível
 O-->>A: Texto e resultado
 A->>A: Preserva texto e decisão pendente
 else Falha de delegação
 O-->>A: Falha ou resposta vazia
 A->>A: Informa indisponibilidade
 end
```

A resposta delegada não passa de novo pelo orquestrador nem pelo juiz, e quando há uma decisão pendente a próxima mensagem da pessoa volta direto ao agente operacional. No modo de debug sem persistência, a delegação é apenas simulada.