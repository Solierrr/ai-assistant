import uuid
from types import SimpleNamespace

import pytest
from langchain_core.embeddings import FakeEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from src.rag.vectorstore import qdrant_store


def test_build_faq_index_retorna_indice_pesquisavel(monkeypatch):
    client = QdrantClient(":memory:")
    monkeypatch.setattr(qdrant_store, "_get_client", lambda: client)
    monkeypatch.setattr(qdrant_store, "_get_embeddings", lambda: FakeEmbeddings(size=8))

    index = qdrant_store.build_faq_index()
    resultados = index.similarity_search("garantia", k=1)

    assert len(resultados) >= 1


def test_build_faq_index_e_idempotente(monkeypatch):
    client = QdrantClient(":memory:")
    monkeypatch.setattr(qdrant_store, "_get_client", lambda: client)
    monkeypatch.setattr(qdrant_store, "_get_embeddings", lambda: FakeEmbeddings(size=8))

    qdrant_store.build_faq_index()
    total_antes = client.count(qdrant_store._COLLECTION_NAME).count
    qdrant_store.build_faq_index()
    total_depois = client.count(qdrant_store._COLLECTION_NAME).count

    assert total_antes == total_depois


def test_build_faq_index_remove_pontos_orfaos(monkeypatch):
    client = QdrantClient(":memory:")
    monkeypatch.setattr(qdrant_store, "_get_client", lambda: client)
    monkeypatch.setattr(qdrant_store, "_get_embeddings", lambda: FakeEmbeddings(size=8))

    qdrant_store.build_faq_index()
    total_original = client.count(qdrant_store._COLLECTION_NAME).count

    orfao_id = str(uuid.uuid4())
    client.upsert(
        collection_name=qdrant_store._COLLECTION_NAME,
        points=[PointStruct(id=orfao_id, vector=[1.0] * 8, payload={})],
    )

    qdrant_store.build_faq_index()

    assert client.count(qdrant_store._COLLECTION_NAME).count == total_original
    assert client.retrieve(qdrant_store._COLLECTION_NAME, ids=[orfao_id]) == []


def test_build_faq_index_sem_chunks_nao_apaga_indice(monkeypatch):
    client = QdrantClient(":memory:")
    monkeypatch.setattr(qdrant_store, "_get_client", lambda: client)
    monkeypatch.setattr(qdrant_store, "_get_embeddings", lambda: FakeEmbeddings(size=8))

    qdrant_store.build_faq_index()
    total_original = client.count(qdrant_store._COLLECTION_NAME).count

    monkeypatch.setattr(
        qdrant_store, "PyPDFLoader", lambda _: SimpleNamespace(load=list)
    )
    with pytest.raises(RuntimeError):
        qdrant_store.build_faq_index()

    assert client.count(qdrant_store._COLLECTION_NAME).count == total_original


def test_load_faq_index_reaproveita_cache(monkeypatch):
    monkeypatch.setattr(qdrant_store, "_store_cache", "indice_fake")
    assert qdrant_store.load_faq_index() == "indice_fake"


def test_load_faq_index_levanta_erro_se_colecao_vazia(monkeypatch):
    monkeypatch.setattr(qdrant_store, "_store_cache", None)
    monkeypatch.setattr(qdrant_store, "_get_client", lambda: QdrantClient(":memory:"))

    with pytest.raises(RuntimeError):
        qdrant_store.load_faq_index()


def test_get_client_levanta_erro_sem_config(monkeypatch):
    monkeypatch.setattr(qdrant_store, "_client", None)
    monkeypatch.setattr(qdrant_store.settings, "QDRANT_URL", None)
    monkeypatch.setattr(qdrant_store.settings, "QDRANT_API_KEY", "algum-valor")

    with pytest.raises(RuntimeError):
        qdrant_store._get_client()
