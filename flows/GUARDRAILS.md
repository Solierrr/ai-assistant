<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Revisão da resposta

A revisão identifica pedidos fora do escopo, manipulação e dados internos, e confere a resposta antes de entregá-la.

```mermaid
flowchart TD
 A[Mensagem] --> B{Entrada aceita?}
 B -->|não| C[Recusa]
 B -->|sim| D[Especialistas e resposta]
 D --> E{Juiz aprova?}
 E -->|não| F[Revê resposta ou recusa]
 E -->|sim| G[Guardrail de saída]
 G --> H[Resposta]
```

A indisponibilidade do guardrail pode produzir resultado degradado. A recusa é expressa no resultado do turno e não equivale necessariamente a erro HTTP.
