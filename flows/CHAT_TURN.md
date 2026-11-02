<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Turno de atendimento

O turno valida acesso, recupera contexto e executa especialistas até produzir uma resposta. A interação completa está em [ASSISTANT_CHAT.md](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/ASSISTANT_CHAT.md).

```mermaid
flowchart TD
 A[JWT e mensagem] --> B[Valida dono e grava entrada]
 B --> C[Guardrail e resumo]
 C --> D[Roteador]
 D --> E[Especialista]
 E --> D
 D --> F[Orquestrador e juiz]
 F --> G[Guardrail de saída]
 G --> H[Grava resposta e retorna resultado]
```

Token inválido, conversa de outra pessoa e corpo inválido impedem o turno. O FAQ e as ferramentas podem informar indisponibilidade. Falhas de atualização de fatos são registradas sem substituir a resposta.
