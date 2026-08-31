from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.workflow.nodes.context import messages_ending_with_user


def test_messages_ending_with_user_preserves_valid_history():
    user_message = HumanMessage(content="Preciso de um instalador")

    messages = messages_ending_with_user({"messages": [user_message]})

    assert messages == [user_message]


def test_messages_ending_with_user_adds_latest_request_after_model_turn():
    messages = messages_ending_with_user(
        {
            "messages": [
                HumanMessage(content="Primeira pergunta"),
                AIMessage(content="Resposta anterior"),
                HumanMessage(content="Pergunta atual"),
                AIMessage(content="Contexto de um especialista"),
            ]
        }
    )

    assert isinstance(messages[-1], HumanMessage)
    assert messages[-1].content == "Pergunta atual"
    assert messages[-2].content == "Contexto de um especialista"


def test_messages_ending_with_user_keeps_summary_as_context():
    messages = messages_ending_with_user(
        {
            "summary": "Resumo anterior",
            "messages": [
                HumanMessage(content="Pergunta atual"),
                AIMessage(content="Contexto interno"),
            ],
        }
    )

    assert isinstance(messages[0], SystemMessage)
    assert "Resumo anterior" in messages[0].content
    assert isinstance(messages[-1], HumanMessage)
    assert messages[-1].content == "Pergunta atual"
