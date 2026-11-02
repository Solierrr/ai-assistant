# 0002. Um serviço por responsabilidade, e nem todo serviço de IA é um agente do A2A

## Contexto

A Solaria tem cinco serviços de IA. Era possível pôr tudo no `ai-assistant`. Os serviços têm públicos, permissões e riscos diferentes.

## Decisão

| Serviço | Por que é separado | Está no A2A? |
|---|---|---|
| `ai-assistant` | Agente principal da web: recomenda e explica, nunca grava no SaaS | Sim (servidor e cliente) |
| `ai-operational` | Executa ações no SaaS. Só o `ai-assistant` o chama, e só com o JWT do usuário | Sim (servidor) |
| `ai-geographic` | Copiloto do profissional em campo, no app mobile, com ferramentas próprias (Google Maps) | Sim (só cliente) |
| `ai-validation` | Validação de certificados e CNPJ: entrada e saída estruturadas, decisão final em código | Não |
| `ai-accessibility` | Moderação de imagem e texto alternativo: uma análise por imagem | Não |

O escopo de cada agente é fechado por arquitetura: o `ai-assistant` não opera telas do SaaS (é do `ai-operational`) nem faz geografia, clima e rotas (é do `ai-geographic`). Quando a pergunta cai fora, ele delega ou indica a quem pertence.

## Por quê

- **Superfície de risco separada.** O poder de gravar dados fica num único serviço, pequeno, com regras próprias (aceite explícito, proposta assinada, limite de gravações). Um erro de prompt no assistente de recomendação não chega a uma gravação.
- **Públicos diferentes.** O `ai-geographic` serve o profissional no mobile; o `ai-assistant` e o `ai-operational` servem a web. Cada um tem personas, ferramentas e prompts próprios, e podem evoluir e escalar separados.
- **Ferramentas diferentes.** O geográfico usa o MCP do Google Maps e a viabilidade solar do `api-google`; o assistente usa o `mcp-database`, o Qdrant e o billscanner. Juntar tudo daria um roteador com muitas ferramentas e mais chance de escolher a errada.
- **`ai-validation` e `ai-accessibility` não conversam.** Recebem um documento ou uma imagem e devolvem um veredito. Não têm sessão, memória nem diálogo, então não há o que delegar por A2A. Quem precisa deles chama a API REST: o `ai-validation` recebe o JWT do usuário emitido pelo `api-auth` (o navegador o chama direto, por isso tem CORS), e o `ai-accessibility` recebe a chave de serviço do chamador. Neles a decisão final é determinística, em código, e o modelo só extrai e classifica, o que facilita auditar e testar a regra de negócio.

## Consequências

- Cada serviço tem seu pipeline de publicação, `/health` e `/ready`.
- Os cinco seguem o mesmo padrão (FastAPI, guardrails, modo debug, erros em `application/problem+json`), para quem conhece um entender os outros.
- Um agente novo que precise conversar com os demais entra pelo A2A, com Agent Card e `POST /a2a`.
