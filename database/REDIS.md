<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Cliente Redis

Existe um cliente assíncrono Redis com TLS e verificação por `ping`. Ele usa as variáveis `UPSTASH_REDIS_*`.

Não foi encontrado contrato de chaves, TTL ou escrita de memória de conversa neste cliente, porque os checkpoints ficam no MongoDB e o cache de ferramentas MCP é uma lista em memória do processo. O Redis, portanto, não armazena a memória dos turnos.
