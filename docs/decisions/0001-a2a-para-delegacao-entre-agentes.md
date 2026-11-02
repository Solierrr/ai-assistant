# 0001. A2A para um agente delegar trabalho a outro

## Contexto

Dois agentes da Solaria precisam pedir trabalho a outro agente:

- o `ai-assistant` recebe pedidos de ação no SaaS (cadastrar oferta, pausar, cancelar pedido) que só o `ai-operational` sabe fazer com segurança;
- o `ai-geographic`, usado pelo profissional em campo, recebe dúvidas sobre produtos que só o `ai-assistant` sabe responder.

Ferramentas de dados (recomendação, profissões, itens de fixação, mapas) já eram consumidas por MCP. A pergunta era como um agente chama outro.

## Decisão

A comunicação entre agentes usa A2A (Agent2Agent, JSON-RPC), pelo módulo `ai_lib.a2a` da `solaria-lib`. Cada agente que recebe delegações publica um Agent Card em `GET /.well-known/agent-card.json` e atende em `POST /a2a`. Quem delega usa `delegate(...)`, repassando o JWT do usuário e a persona (`demandante` ou `profissional`).

- `ai-assistant` publica o card (habilidade `recomendar-produtos`) e delega ao `ai-operational`.
- `ai-operational` publica o card (habilidade `operar-saas`).
- `ai-geographic` só consome A2A e não publica card, porque nenhum agente delega a ele.

## Por quê

- **O JWT do usuário viaja junto.** O agente que recebe age com as permissões de quem pediu. O `ai-operational` chama o `api-core` com o token do próprio usuário, então não existe credencial de serviço com poder amplo para ser desviada.
- **Cada agente fica dono do seu fluxo.** Uma proposta de ação tem estado (pendente, aceita, expirada) que vive no `ai-operational`. Com A2A o `ai-assistant` não precisa conhecer esse estado: só repassa a mensagem e a resposta, e marca `awaiting_decision` para a próxima mensagem voltar ao mesmo agente.
- **Contrato conhecido e descoberta.** O Agent Card descreve o que o agente faz, então um agente novo pode ser chamado sem alterar o chamador além do endereço.
- **MCP e A2A resolvem coisas diferentes.** MCP dá ferramentas a um agente (uma função com entrada e saída). A2A conversa com outro agente que raciocina, mantém contexto da conversa (`context_id`) e pode pedir mais informação (`input_required`). Por isso dados vão por MCP e delegação por A2A.

## Consequências

- Uma falha do agente remoto não derruba o turno: vira `TOOL_FAILED` com o motivo (`OPERATIONAL_AGENT_UNAVAILABLE` no assistente, `PRODUCT_ADVISOR_UNAVAILABLE` no geográfico) e uma mensagem clara ao usuário.
- A resposta do agente operacional segue direto ao usuário, sem orquestrador, juiz nem guardrail de saída do assistente (ver [0004](./0004-acoes-so-com-aceite-do-usuario.md)).
- Há um salto de rede a mais por delegação, então o tempo total do turno soma o do agente remoto. A latência por passo fica registrada no `StepTracker`.
- Os endereços vêm de variáveis de ambiente (`A2A_OPERATIONAL_URL`, `A2A_ASSISTANT_URL`, `A2A_PUBLIC_URL`).
