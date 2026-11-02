# 0003. Roteador, especialistas, orquestrador e juiz

## Contexto

O assistente responde sobre assuntos de natureza diferente (dúvida da plataforma, recomendação de placa, profissional, empresa, estimativa solar, pedido de ação). Um único prompt com todas as ferramentas ficaria grande, caro e fácil de errar.

## Decisão

O fluxo é um grafo LangGraph com papéis separados:

1. **Guardrail de entrada**: bloqueia o que não é permitido antes de gastar qualquer chamada de especialista.
2. **Roteador**: escolhe um especialista por vez, ou o orquestrador quando já há informação suficiente. Cada especialista usado volta ao roteador, com limite de 3 por pedido.
3. **Especialistas**: um por assunto, cada um com prompt e ferramentas próprios (`faq_reader`, `solar_panel_specialist`, `professional_suggester`, `agency_suggester`, `solar_calculator`, `operational_delegate`).
4. **Orquestrador**: compõe a resposta única a partir do que os especialistas reuniram.
5. **Juiz**: confere alucinação e aderência. Se reprova, o orquestrador refaz uma vez; reprovada de novo, o turno é recusado.
6. **Guardrail de saída**: revisão de conformidade e remoção de PII.

## Por quê

- **Prompts pequenos e focados** reduzem erro e custo por chamada, e cada especialista pode ser testado sozinho.
- **Quem escreve a resposta final não é quem a confere.** O juiz é uma chamada separada, o que reduz a chance de o mesmo viés aprovar a própria alucinação.
- **O juiz é um LLM, e não um modelo de decisão como o Jev.** O Jev não escreve texto e devolve só probabilidades; o juiz do assistente devolve o veredito com a justificativa em texto. Os motivos estão na [decisão 0005](0005-juiz-llm-em-vez-de-jev.md).
- **O que é cálculo ou ranking não é do LLM.** O ranking de placas, profissionais e empresas é determinístico, vem da `api-recommendation`, e o LLM só cruza as necessidades do usuário com as melhores opções e explica a escolha.
- **Fonte indicada.** O `faq_reader` responde com RAG sobre o `FAQ_v1.pdf` indexado no Qdrant; recomendações vêm das ferramentas MCP.
- **Especialista novo é barato de acrescentar**: um prompt, um nó e a rota em `src/workflow/config.py`.

## Consequências

- Cada resposta soma as chamadas de LLM das suas etapas (guardrail, roteador, especialistas, orquestrador, juiz, guardrail de saída, extração de memória), e o custo de cada passo fica registrado no `StepTracker`.
- O tempo de resposta soma as etapas: o `/chat` devolve a resposta completa de uma vez, e o cliente usa timeout acima de 60 s.
- Há uma tabela de desfechos (`ANSWERED`, `REFUSED`, `DEGRADED`, `TOOL_FAILED`) para o cliente entender o que aconteceu sem tratar como erro HTTP.
