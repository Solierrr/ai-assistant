import os

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

_PDF_PATH = os.path.join(os.path.dirname(__file__), "..", "FAQ_v1.pdf")
_INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", ".faiss_index", "faq")

_embeddings = None
_index_cache = None


def _get_embeddings():
    """Instancia o modelo de embeddings do Google sob demanda (lazy)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    return _embeddings


def build_faq_index() -> FAISS:
    """Lê o PDF do FAQ, quebra em chunks e monta o índice FAISS do zero."""
    loader = PyPDFLoader(_PDF_PATH)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)

    index = FAISS.from_documents(chunks, _get_embeddings())
    os.makedirs(os.path.dirname(_INDEX_PATH), exist_ok=True)
    index.save_local(_INDEX_PATH)
    return index


def load_faq_index() -> FAISS:
    """Carrega o índice já persistido em disco, ou monta na primeira chamada."""
    global _index_cache
    if _index_cache is not None:
        return _index_cache

    if os.path.exists(_INDEX_PATH):
        _index_cache = FAISS.load_local(
            _INDEX_PATH, _get_embeddings(), allow_dangerous_deserialization=True
        )
    else:
        _index_cache = build_faq_index()

    return _index_cache
