"""Dense side of hybrid search: local sentence-transformer embeddings -> Qdrant."""
from __future__ import annotations

import uuid

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from src.config import settings

_embedder: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(settings.embedding_model)
    return _embedder


def get_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection(client: QdrantClient) -> None:
    if not client.collection_exists(settings.qdrant_collection):
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=models.VectorParams(
                size=settings.embedding_dim,
                distance=models.Distance.COSINE,
            ),
        )
        print(f"[qdrant] created collection '{settings.qdrant_collection}'")


def index_chunks(chunks: list[dict]) -> None:
    """Embed every chunk and upsert into Qdrant with full payload."""
    client = get_client()
    ensure_collection(client)
    embedder = get_embedder()

    texts = [c["text"] for c in chunks]
    vectors = embedder.encode(texts, batch_size=64, show_progress_bar=True,
                              normalize_embeddings=True)

    points = [
        models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, c["id"])),
            vector=vec.tolist(),
            payload=c,
        )
        for c, vec in zip(chunks, vectors)
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)
    print(f"[qdrant] upserted {len(points)} vectors")


def dense_search(query: str, top_k: int | None = None) -> list[dict]:
    """Return chunk payloads ranked by cosine similarity."""
    client = get_client()
    qvec = get_embedder().encode(query, normalize_embeddings=True).tolist()
    res = client.query_points(
        collection_name=settings.qdrant_collection,
        query=qvec,
        limit=top_k or settings.dense_top_k,
        with_payload=True,
    )
    return [{**p.payload, "dense_score": p.score} for p in res.points]
