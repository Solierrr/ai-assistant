from unittest.mock import MagicMock, patch

from src.agents.specialist.faq_reader.tools.faq_retriever import faq_retriever


def test_faq_retriever_retorna_trechos_relevantes():
    fake_doc = MagicMock(page_content="O prazo de garantia é de 5 anos.")
    fake_index = MagicMock()
    fake_index.similarity_search.return_value = [fake_doc]

    with patch(
        "src.agents.specialist.faq_reader.tools.faq_retriever.load_faq_index",
        return_value=fake_index,
    ):
        resultado = faq_retriever.invoke({"query": "qual o prazo de garantia?"})

    assert "5 anos" in resultado


def test_faq_retriever_sem_resultados():
    fake_index = MagicMock()
    fake_index.similarity_search.return_value = []

    with patch(
        "src.agents.specialist.faq_reader.tools.faq_retriever.load_faq_index",
        return_value=fake_index,
    ):
        resultado = faq_retriever.invoke({"query": "pergunta aleatória"})

    assert "Nenhum trecho relevante" in resultado
