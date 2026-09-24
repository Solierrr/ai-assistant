from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage

import src.workflow.nodes.output_guardrail_node as node


def test_output_guardrail_preserves_token_until_authorized_result_read(monkeypatch):
    llm = Mock()
    llm.with_structured_output.return_value.invoke.return_value = SimpleNamespace(
        resposta_revisada="Ola, [PII_NOME].", foi_corrigida=True
    )
    monkeypatch.setattr(node, "llm_groq", Mock(return_value=llm))
    result = node.output_guardrail_node(
        {"messages": [AIMessage(content="Resposta", id="1")], "pii_map": {"[PII_NOME]": "Ana"}}
    )

    assert result["messages"][1].content == "Ola, [PII_NOME]."
