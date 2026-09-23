import logging

from langchain_core.tools import tool

from src.rag.vectorstore.qdrant_store import load_faq_index

logger = logging.getLogger(__name__)


@tool
def faq_retriever(query: str) -> str:
    """Busca trechos relevantes do FAQ oficial do Solária para responder
    dúvidas de usuários sobre o produto, planos, garantia, instalação etc.
    Use sempre que a pergunta parecer ser sobre política, procedimento ou
    informação institucional do FAQ."""
    try:
        index = load_faq_index()
        resultados = index.similarity_search(query, k=3)
    except Exception as erro:  # noqa: BLE001
        logger.warning("Falha ao consultar o FAQ: %s", erro)
        return "FAQ indisponível no momento."

    if not resultados:
        return "Nenhum trecho relevante encontrado no FAQ."

    return "\n\n---\n\n".join(doc.page_content for doc in resultados)
