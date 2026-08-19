from langchain_core.tools import tool

from src.rag.vectorstore.faiss_store import load_faq_index


@tool
def faq_retriever(query: str) -> str:
    """Busca trechos relevantes do FAQ oficial do Solária para responder
    dúvidas de usuários sobre o produto, planos, garantia, instalação etc.
    Use sempre que a pergunta parecer ser sobre política, procedimento ou
    informação institucional do FAQ."""
    index = load_faq_index()
    resultados = index.similarity_search(query, k=3)

    if not resultados:
        return "Nenhum trecho relevante encontrado no FAQ."

    return "\n\n---\n\n".join(doc.page_content for doc in resultados)
