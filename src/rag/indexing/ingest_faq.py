from src.rag.vectorstore.qdrant_store import build_faq_index

if __name__ == "__main__":
    build_faq_index()
    print("Índice do FAQ atualizado na coleção Qdrant.")
