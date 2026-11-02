<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Deploy

O workflow declara QA em https://ai-assistant-5ljd.onrender.com, readiness em `/ready` e verificação do cluster de produção. O processo comum está em [QA_RENDER.md](https://github.com/Solierrr/docs-warehouse/blob/main/readme/deploy/QA_RENDER.md) e [PROD_GKE_ARGOCD.md](https://github.com/Solierrr/docs-warehouse/blob/main/readme/deploy/PROD_GKE_ARGOCD.md).

O Dockerfile inicia o Uvicorn na porta 8000, e o serviço está publicado no QA, no Render, e na produção, no cluster. Antes de validar o atendimento, configure o Mongo, os serviços integrados, os modelos e o índice do FAQ.