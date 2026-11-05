import pytest

from src.agents.base.base_prompt import build_system_prompt
from src.agents.base.system_prompt import (
    SYSTEM_CORE_COMMUNICATION,
    SYSTEM_CORE_SECURITY,
)
from src.workflow.nodes import (
    input_guardrail_node,
    judge_node,
    orchestrator_node,
    output_guardrail_node,
    router_node,
)


def test_regra_inviolavel_manda_dizer_apenas_que_e_o_assistente_da_solaria():
    regra = " ".join(SYSTEM_CORE_SECURITY.split())

    assert "10. Nunca fale de si como um agente interno" in regra
    assert "diga apenas que é o assistente da Solaria" in regra
    assert '"eu sou o roteador"' in regra


def test_regra_de_outro_agente_nao_manda_citar_o_nome_dele():
    assert "sem citar o nome de nenhum" in " ".join(SYSTEM_CORE_SECURITY.split())


def test_padroes_de_comunicacao_reforcam_a_identidade():
    assert 'Apresente-se sempre como "o assistente da Solaria"' in " ".join(
        SYSTEM_CORE_COMMUNICATION.split()
    )


@pytest.mark.parametrize(
    "prompt",
    [
        router_node.ROUTER_PROMPT,
        orchestrator_node.ORCHESTRATOR_PROMPT,
        input_guardrail_node.INPUT_GUARDRAIL_PROMPT,
        output_guardrail_node.OUTPUT_GUARDRAIL_PROMPT,
        judge_node.JUDGE_PROMPT,
    ],
)
def test_todo_agente_recebe_a_regra_de_identidade(prompt):
    assert "10. Nunca fale de si como um agente interno" in prompt


def test_prompt_de_agente_especialista_recebe_a_regra_antes_do_prompt_especifico():
    prompt = build_system_prompt("### IDENTIDADE DO AGENTE\nVocê é o Agente X.")

    assert prompt.index("10. Nunca fale de si") < prompt.index("Você é o Agente X.")
