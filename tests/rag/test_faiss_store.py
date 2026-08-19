from langchain_core.embeddings import FakeEmbeddings

from src.rag.vectorstore import faiss_store


def test_build_faq_index_retorna_indice_pesquisavel(tmp_path, monkeypatch):
    monkeypatch.setattr(faiss_store, "_INDEX_PATH", str(tmp_path / "faq"))
    monkeypatch.setattr(faiss_store, "_get_embeddings", lambda: FakeEmbeddings(size=8))

    index = faiss_store.build_faq_index()
    resultados = index.similarity_search("garantia", k=1)

    assert len(resultados) >= 1


def test_load_faq_index_reaproveita_cache(monkeypatch):
    monkeypatch.setattr(faiss_store, "_index_cache", "indice_fake")
    assert faiss_store.load_faq_index() == "indice_fake"
