import os
import uuid

from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    FilterSelector,
    HasIdCondition,
    VectorParams,
)

from src.core.config.settings import settings

_PDF_PATH = os.path.join(os.path.dirname(__file__), "..", "FAQ_v1.pdf")
_COLLECTION_NAME = "solaria-faq"
_NAMESPACE_CHUNKS = uuid.UUID("f4f5f6f7-0000-0000-0000-000000000000")

_embeddings = None
_client = None
_store_cache = None


def _get_embeddings():
    """Instancia o modelo de embeddings do Google sob demanda (lazy)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001", api_key=settings.GOOGLE_API_KEY
        )
    return _embeddings


def _get_client() -> QdrantClient:
    """Cliente do Qdrant Cloud, reaproveitado entre chamadas."""
    global _client
    if _client is None:
        if not settings.QDRANT_URL or not settings.QDRANT_API_KEY:
            raise RuntimeError(
                "QDRANT_URL e QDRANT_API_KEY precisam estar configurados nas settings"
            )
        _client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    return _client


def _chunk_id(texto: str) -> str:
    """ID determinístico por conteúdo — reindexar não duplica, é upsert."""
    return str(uuid.uuid5(_NAMESPACE_CHUNKS, texto))


def _indice_populado(client: QdrantClient) -> bool:
    """Coleção existir não basta — pode ter ficado vazia por uma falha
    no meio de uma indexação anterior."""
    if not client.collection_exists(_COLLECTION_NAME):
        return False
    return client.count(_COLLECTION_NAME).count > 0


def build_faq_index() -> QdrantVectorStore:
    """Lê o PDF do FAQ, faz upsert idempotente na coleção Qdrant e remove
    chunks órfãos (que existiam numa versão anterior do PDF). Pensado pra
    rodar via script de ingestão, fora do caminho de uma requisição."""
    loader = PyPDFLoader(_PDF_PATH)
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)

    if not chunks:
        raise RuntimeError(
            f"Nenhum chunk extraído de {_PDF_PATH}; abortando para não apagar o índice"
        )

    embeddings = _get_embeddings()
    dimensao = len(embeddings.embed_query("dimensionamento"))

    client = _get_client()
    if not client.collection_exists(_COLLECTION_NAME):
        client.create_collection(
            collection_name=_COLLECTION_NAME,
            vectors_config=VectorParams(size=dimensao, distance=Distance.COSINE),
        )

    store = QdrantVectorStore(
        client=client, collection_name=_COLLECTION_NAME, embedding=embeddings
    )
    ids = [_chunk_id(c.page_content) for c in chunks]
    store.add_documents(chunks, ids=ids)

    client.delete(
        collection_name=_COLLECTION_NAME,
        points_selector=FilterSelector(
            filter=Filter(must_not=[HasIdCondition(has_id=ids)])
        ),
    )
    return store


def load_faq_index() -> QdrantVectorStore:
    """Carrega a coleção já indexada. Não indexa sozinho — se estiver
    vazia ou ausente, é sinal de que a ingestão ainda não rodou."""
    global _store_cache
    if _store_cache is not None:
        return _store_cache

    client = _get_client()
    if not _indice_populado(client):
        raise RuntimeError(
            f"Coleção '{_COLLECTION_NAME}' vazia ou inexistente. "
            "Rode: python -m src.rag.indexing.ingest_faq"
        )

    _store_cache = QdrantVectorStore(
        client=client, collection_name=_COLLECTION_NAME, embedding=_get_embeddings()
    )
    return _store_cache
