"""STEP 2 — Ingest every PDF in data/sample_docs into BOTH indexes:
   PDFs -> unstructured parser -> chunks -> (a) Qdrant dense vectors
                                            (b) docstore.jsonl for BM25
Prereq: Qdrant running (`docker compose up -d`)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from src.ingestion.pdf_parser import parse_pdf, save_docstore
from src.retrieval.vector_store import index_chunks

DOCS_DIR = Path(__file__).resolve().parents[1] / "data" / "sample_docs"


def main() -> None:
    pdfs = sorted(DOCS_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs in {DOCS_DIR}. Run scripts/01_generate_sample_data.py "
                         "or drop your own files there.")
    all_chunks = []
    for pdf in pdfs:
        all_chunks.extend(parse_pdf(pdf))

    chunk_dicts = [c.to_dict() for c in all_chunks]
    save_docstore(all_chunks)          # sparse source of truth
    index_chunks(chunk_dicts)          # dense vectors -> Qdrant
    print(f"\n✅ Ingestion complete: {len(all_chunks)} chunks across {len(pdfs)} PDFs")


if __name__ == "__main__":
    main()
