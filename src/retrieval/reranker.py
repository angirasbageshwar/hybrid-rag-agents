"""Cross-encoder reranker: the precision stage after hybrid recall.

Bi-encoders (embeddings) score query and doc separately — fast but coarse.
A cross-encoder reads (query, doc) TOGETHER through one transformer, so it
catches subtle relevance the fusion step can't. We rerank ~20-40 fused
candidates and keep only the best `rerank_top_k` for the LLM context.
"""
from __future__ import annotations

from sentence_transformers import CrossEncoder

from src.config import settings

_reranker: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(settings.reranker_model)
    return _reranker


def rerank(query: str, candidates: list[dict], top_k: int | None = None) -> list[dict]:
    if not candidates:
        return []
    top_k = top_k or settings.rerank_top_k
    pairs = [(query, c["text"]) for c in candidates]
    scores = get_reranker().predict(pairs)
    order = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)
    return [{**candidates[i], "rerank_score": float(scores[i])} for i in order[:top_k]]
