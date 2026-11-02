# 0005. Juiz como LLM separado, e não o Jev

## Contexto

O juiz (decisão [0003](0003-roteador-especialistas-orquestrador-juiz.md)) recebe a resposta escrita pelo orquestrador e devolve `APROVADO` ou `REPROVADO` com uma justificativa (`src/workflow/nodes/judge_node.py`). Resposta fora do formato esperado conta como reprovação.

Em setembro de 2026 a TypeSafe AI lançou o Jev, um modelo de uma categoria nova que ela chama de "System One". Ele foi comparado ao juiz atual porque também produz decisões tipadas.

## Decisão

O juiz é um LLM chamado separadamente do orquestrador.

## O que é o Jev

Segundo as fontes listadas no fim (a maior parte vem do próprio fabricante):

- Recebe um estado em texto e um conjunto de perguntas tipadas, e devolve decisões estruturadas com probabilidade e confiança, em uma passada paralela. Os tipos de pergunta são `Choice` (escolha entre opções), `Score` (nota em níveis ordenados) e `Noul` (sim ou não com probabilidade).
- Não gera texto livre, código nem explicação escrita. Por isso não serve ao lado conversacional do assistente: o orquestrador e os especialistas escrevem respostas em linguagem natural.
- É treinado com um método próprio (RLCD) para que as probabilidades sejam calibradas: uma confiança de 0,9 deve acertar cerca de 90% das vezes. O ponto forte dele são decisões com probabilidade bem calibrada em fluxos automatizados, como classificação, roteamento e pontuação, e não o texto de uma conversa.
- A latência informada é de 70 a 500 ms e o preço, US$ 0,042 por milhão de tokens de entrada, sem cobrança de saída.

## Por quê

- **Justificativa em texto.** O juiz do assistente devolve o veredito junto do motivo, escrito em português. O Jev devolve probabilidades, sem texto explicativo.
- **Integração existente.** O juiz usa a cadeia de LLMs que o serviço já tem (Gemini, Groq e OpenAI), com tratamento de falha fail-closed: se o juiz falha, a resposta é reprovada.
- **Disponibilidade.** A API própria do Jev está em acesso antecipado, com lista de espera, e há uma versão beta no OpenRouter com contexto de 32 mil tokens. O juiz fica no caminho de toda resposta, então precisa de um provedor com disponibilidade já estabelecida.
- **Evidências publicadas.** Os números vêm do fabricante: acurácia média de 67,8% em 4 fluxos, contra 73,1% a 74,1% dos modelos de fronteira comparados, com referências geradas por esses próprios modelos. A DataCamp registra que não houve reprodução por terceiros até o momento. A garantia de "não alucinar" vale para o formato da saída, não para a correção do conteúdo.

## Consequências

- Cada turno inclui uma chamada de LLM no juiz, já contada no custo por passo.
- O motivo de cada reprovação fica em texto.

## Fontes

- [Introducing System One Models & Jev, TypeSafe AI](https://typesafe.ai/blog/introducing-system-one-models-and-jev) (fabricante)
- [System One models and Jev, DataCamp](https://www.datacamp.com/blog/system-one-models-jev)
- [O que é Jev, o System One Model da TypeSafe AI, Hora de Codar](https://horadecodar.com.br/jev-system-one-model-typesafe-ai/)
