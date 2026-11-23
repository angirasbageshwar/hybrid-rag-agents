"""Sparse side of hybrid search: classic BM25 keyword matching.

Why keep BM25 next to vectors? Exact tokens — 'Q3 2025', 'clause 14.2',
ticker symbols, part numbers — are where embeddings go blurry and keyword
match stays razor sharp.
"""
from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from src.ingestion.pdf_parser import load_docstore

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Store:
    """In-memory BM25 index rebuilt from the docstore JSONL (source of truth)."""

    def __init__(self) -> None:
        self.docs: list[dict] = load_docstore()
        corpus = [_tokenize(d["text"]) for d in self.docs]
        self.index = BM25Okapi(corpus)
        print(f"[bm25] indexed {len(self.docs)} chunks")

    def search(self, query: str, top_k: int) -> list[dict]:
        scores = self.index.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [{**self.docs[i], "bm25_score": float(scores[i])} for i in ranked]
