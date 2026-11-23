"""Agent 1's toolbox: parse enterprise PDFs (10-Ks, contracts) into clean chunks.

Uses `unstructured` to detect document layout. Tables are kept as standalone
chunks (HTML when available) so numbers never get shredded mid-row.

Swap-in alternative: LlamaParse — replace `parse_pdf` with a LlamaParse call
and keep the same Chunk output shape; the rest of the pipeline won't notice.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path

from unstructured.partition.pdf import partition_pdf
from unstructured.chunking.title import chunk_by_title

from src.config import settings


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    page: int | None
    kind: str  # "table" | "text"

    def to_dict(self) -> dict:
        return asdict(self)


def _make_id(source: str, text: str) -> str:
    return hashlib.sha1(f"{source}::{text}".encode()).hexdigest()[:16]


def parse_pdf(path: str | Path) -> list[Chunk]:
    """Parse one PDF into table chunks + title-aware narrative chunks."""
    path = Path(path)
    print(f"[ingest] parsing {path.name} (strategy={settings.pdf_strategy}) ...")

    elements = partition_pdf(
        filename=str(path),
        strategy=settings.pdf_strategy,        # "hi_res" = layout model, best for nested tables
        infer_table_structure=True,            # emit table HTML when strategy supports it
    )

    chunks: list[Chunk] = []
    narrative_elements = []

    for el in elements:
        if el.category == "Table":
            html = getattr(el.metadata, "text_as_html", None)
            text = html or el.text
            chunks.append(Chunk(
                id=_make_id(path.name, text),
                text=f"[TABLE from {path.name}]\n{text}",
                source=path.name,
                page=getattr(el.metadata, "page_number", None),
                kind="table",
            ))
        else:
            narrative_elements.append(el)

    for piece in chunk_by_title(narrative_elements, max_characters=1200,
                                combine_text_under_n_chars=200):
        text = piece.text.strip()
        if len(text) < 40:
            continue
        chunks.append(Chunk(
            id=_make_id(path.name, text),
            text=text,
            source=path.name,
            page=getattr(piece.metadata, "page_number", None),
            kind="text",
        ))

    print(f"[ingest] {path.name}: {len(chunks)} chunks "
          f"({sum(c.kind == 'table' for c in chunks)} tables)")
    return chunks


def save_docstore(chunks: list[Chunk], path: str | Path = None) -> None:
    """Persist chunks as JSONL — this file is the source of truth BM25 rebuilds from."""
    path = Path(path or settings.docstore_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    print(f"[ingest] wrote docstore -> {path} ({len(chunks)} chunks)")


def load_docstore(path: str | Path = None) -> list[dict]:
    path = Path(path or settings.docstore_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Docstore not found at {path}. Run `python scripts/02_ingest.py` first.")
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
