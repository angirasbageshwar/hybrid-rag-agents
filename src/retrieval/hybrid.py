"""Hybrid search = dense (Qdrant) + sparse (BM25), fused with Reciprocal Rank
Fusion, then sharpened by the cross-encoder reranker.

RRF in one line: a document's fused score is the sum over each ranked list of
1 / (k + rank). No score normalization headaches — only positions matter.
"""
from __future__ import annotations

from src.config import settings
from src.retrieval.bm25_store import BM25Store
from src.retrieval.reranker import rerank
from src.retrieval.vector_store import dense_search

_bm25: BM25Store | None = None


def _get_bm25() -> BM25Store:
    global _bm25
    if _bm25 is None:
        _bm25 = BM25Store()
    return _bm25


def _rrf_fuse(result_lists: list[list[dict]], k: int) -> list[dict]:
    scores: dict[str, float] = {}
    seen: dict[str, dict] = {}
    for results in result_lists:
        for rank, doc in enumerate(results):
            did = doc["id"]
            scores[did] = scores.get(did, 0.0) + 1.0 / (k + rank + 1)
            seen.setdefault(did, doc)
    fused = sorted(scores, key=scores.get, reverse=True)
    return [{**seen[did], "rrf_score": scores[did]} for did in fused]


def hybrid_search(query: str) -> list[dict]:
    """Full pipeline: recall wide (dense + sparse) -> fuse -> rerank precise."""
    dense = dense_search(query, settings.dense_top_k)
    sparse = _get_bm25().search(query, settings.sparse_top_k)
    fused = _rrf_fuse([dense, sparse], settings.rrf_k)
    top = rerank(query, fused, settings.rerank_top_k)
    print(f"[hybrid] dense={len(dense)} sparse={len(sparse)} "
          f"fused={len(fused)} -> reranked top {len(top)}")
    return top
