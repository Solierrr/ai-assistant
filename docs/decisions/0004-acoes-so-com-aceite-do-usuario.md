# 0004. Ação que grava dados só com aceite explícito do usuário

## Contexto

Pedir "cadastra uma oferta" ou "cancela esse pedido" a um agente de IA é pedir que ele altere dados reais. Um modelo pode errar ao interpretar, ou ser induzido por texto malicioso (prompt injection) vindo da própria conversa ou de dados lidos de outras fontes.

## Decisão

- O `ai-assistant` **nunca grava**. Pedidos de ação são delegados ao `ai-operational` por A2A.
- O `ai-operational` **propõe antes de executar**: monta a proposta com os dados exatos e só executa depois do aceite do usuário. Uma resposta de "aceitar" vinda do LLM não vale: o aceite é conferido por comparação com frases exatas, e ações irreversíveis (encerrar oferta, cancelar pedido) exigem a palavra "confirmo".
- A proposta é **assinada (HMAC), expira em 15 minutos, é presa ao usuário** que a pediu e o que foi mostrado é exatamente o que será gravado.
- Os ids usados vêm só dos dados do próprio usuário no `api-core` (lidos com o JWT dele), nunca de texto escrito pelo modelo.
- Há um teto de gravações por conversa e uma lista de ações proibidas (compra, pagamento, exclusão, transferência, senha, cargo e permissão).
- A resposta do agente operacional chega ao usuário **sem passar pelo orquestrador, pelo juiz nem pelo guardrail de saída** do assistente, para a proposta não ser reescrita no caminho.

## Por quê

- Um aceite verificado em código não depende de o modelo "entender" que o usuário concordou, nem de um texto injetado dizer que ele concordou.
- Assinar a proposta impede trocar o conteúdo entre a proposta e a execução; a validade e o dono impedem reaproveitar uma proposta antiga ou de outro usuário.
- O que o usuário vê antes de aceitar é o que será gravado, e a decisão de executar fica com ele.

## Consequências

- Toda ação passa por duas mensagens: a proposta e o aceite.
- Dados lidos do `api-core` e de ferramentas são tratados como dados, nunca como instrução: entram marcados e sanitizados nos prompts.
- Os detalhes de implementação estão no `docs/ARCHITECTURE.md` do `ai-operational`.
