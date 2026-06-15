"""
Vektör depolama modülü: sentence-transformers ile embedding üretir,
ChromaDB'ye kaydeder ve benzerlik araması yapar.
"""

import os
from typing import Any, Dict, List, Optional

import chromadb
from sentence_transformers import SentenceTransformer

# Kalıcı depolama dizini (docker volume ile eşleşir)
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = "documents"

# Retrieval için özel eğitilmiş çok dilli model (MiniLM'den belirgin şekilde daha iyi)
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"

# Bu skoru geçemeyen chunk'lar context'e dahil edilmez
MIN_RELEVANCE_SCORE = 0.40
# En yüksek skordan bu kadar düşük olan chunk'lar elenir (ayrı belgelerden gelen gürültüyü keser)
RELATIVE_GAP = 0.05

# Uygulama yaşam döngüsü boyunca tek örnek (singleton) nesneler
_embedding_model: Optional[SentenceTransformer] = None
_collection = None


def _get_model() -> SentenceTransformer:
    """Embedding modelini ilk çağrıda yükler, sonraki çağrılarda önbellekten döner."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def _get_collection():
    """ChromaDB koleksiyonunu döner; yoksa oluşturur."""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  # kosinüs benzerliği
        )
    return _collection


def _encode_passages(model: SentenceTransformer, texts: List[str]) -> List[List[float]]:
    """
    E5 modeli pasajları 'passage: ' prefix ile encode eder.
    Bu prefix retrieval kalitesini önemli ölçüde artırır.
    """
    prefixed = [f"passage: {t}" for t in texts]
    return model.encode(prefixed, show_progress_bar=False).tolist()


def _encode_query(model: SentenceTransformer, text: str) -> List[float]:
    """E5 modeli sorguları 'query: ' prefix ile encode eder."""
    return model.encode([f"query: {text}"], show_progress_bar=False).tolist()[0]


def add_document_chunks(doc_id: str, filename: str, chunks: List[str]) -> int:
    """
    Chunk listesini embedding'e dönüştürüp ChromaDB'ye kaydeder.
    Her chunk için benzersiz ID: '<doc_id>_chunk_<index>'
    """
    model = _get_model()
    collection = _get_collection()

    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    embeddings = _encode_passages(model, chunks)
    metadatas = [
        {"doc_id": doc_id, "filename": filename, "chunk_index": i}
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    return len(chunks)


def search_similar_chunks(
    query: str,
    doc_ids: Optional[List[str]] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Sorgu metnine en yakın chunk'ları döner.
    doc_ids verilirse yalnızca o belgelerde arar.
    """
    model = _get_model()
    collection = _get_collection()

    # Koleksiyon boşsa erken çık
    total = collection.count()
    if total == 0:
        return []

    # ChromaDB filtresi
    where: Optional[Dict] = None
    if doc_ids:
        where = (
            {"doc_id": doc_ids[0]}
            if len(doc_ids) == 1
            else {"doc_id": {"$in": doc_ids}}
        )

    # Filtrelenmiş kayıt sayısını kontrol et (n_results > kayıt sayısı hata verir)
    if where:
        filtered = collection.get(where=where, include=[])
        available = len(filtered["ids"])
    else:
        available = total

    if available == 0:
        return []

    n_results = min(top_k, available)
    query_embedding = _encode_query(model, query)

    query_params: Dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        query_params["where"] = where

    results = collection.query(**query_params)

    # Mesafeyi benzerlik skoruna çevir (cosine distance = 1 - cosine_similarity)
    all_chunks = []
    for i in range(len(results["documents"][0])):
        score = round(max(0.0, 1 - results["distances"][0][i]), 4)
        all_chunks.append(
            {
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": score,
            }
        )

    if not all_chunks:
        return []

    # Mutlak alt eşik: tamamen alakasız chunk'ları at
    all_chunks = [c for c in all_chunks if c["score"] >= MIN_RELEVANCE_SCORE]

    if not all_chunks:
        return []

    # Görece eşik: en yüksek skorun RELATIVE_GAP altında kalan chunk'ları at
    # (aynı sorguda birden fazla belge varsa yalnızca gerçekten ilgili olanları tutar)
    max_score = all_chunks[0]["score"]
    similar_chunks = [c for c in all_chunks if c["score"] >= max_score - RELATIVE_GAP]

    return similar_chunks


def delete_document(doc_id: str) -> int:
    """Belgeye ait tüm chunk'ları ChromaDB'den siler. Silinen sayısını döner."""
    collection = _get_collection()
    existing = collection.get(where={"doc_id": doc_id}, include=[])

    if not existing["ids"]:
        return 0

    collection.delete(ids=existing["ids"])
    return len(existing["ids"])


def list_documents() -> List[Dict[str, Any]]:
    """Koleksiyondaki tüm benzersiz belgeleri chunk sayısıyla listeler."""
    collection = _get_collection()
    all_meta = collection.get(include=["metadatas"])

    if not all_meta["metadatas"]:
        return []

    docs: Dict[str, Dict] = {}
    for meta in all_meta["metadatas"]:
        doc_id = meta["doc_id"]
        if doc_id not in docs:
            docs[doc_id] = {
                "doc_id": doc_id,
                "filename": meta["filename"],
                "chunk_count": 0,
            }
        docs[doc_id]["chunk_count"] += 1

    return list(docs.values())
