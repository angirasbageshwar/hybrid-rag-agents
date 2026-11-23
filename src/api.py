"""FastAPI wrapper — the container's entrypoint on EKS.

GET  /                           -> web UI (web/index.html)
POST /brief {"question": "..."}  -> verified executive briefing + audit trail
POST /brief/stream               -> same, as NDJSON events (one per agent step)
GET  /info                       -> model, documents, web-verification status
GET  /documents/{name}           -> the source PDF (citations link here)
GET  /health                     -> k8s liveness/readiness probe target
"""
from dotenv import load_dotenv
load_dotenv()

import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.agents.graph import generate_brief, stream_brief
from src.config import settings
from src.ingestion.pdf_parser import load_docstore
from src.tracing import report_tracing_status

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "data" / "sample_docs"
WEB_DIR = ROOT / "web"

app = FastAPI(title="Enterprise Knowledge Network", version="1.1.0")
print(report_tracing_status())


class BriefRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class Source(BaseModel):
    id: str
    source: str
    page: int | None = None
    kind: str
    text: str


class BriefResponse(BaseModel):
    brief: str
    grounded: bool
    support_ratio: float | None = None
    revisions_used: int
    verification: str
    sources: list[Source] = []
    elapsed_s: float | None = None


def _response(state: dict, started: float) -> BriefResponse:
    critique = state.get("critique", {})
    return BriefResponse(
        brief=state.get("final_brief", ""),
        grounded=bool(critique.get("grounded")),
        support_ratio=critique.get("support_ratio"),
        revisions_used=state.get("revision_count", 0),
        verification=state.get("verification", ""),
        sources=[Source(**{k: c.get(k) for k in Source.model_fields})
                 for c in state.get("retrieved", [])],
        elapsed_s=round(time.time() - started, 1),
    )


def _friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if any(s in msg for s in ("429", "RESOURCE_EXHAUSTED", "rate limit", "quota")):
        return ("The AI model's free usage limit was reached. Wait a minute and try again; "
                "if it keeps happening, the daily limit is used up (see HOW_TO_USE.pdf).")
    if any(s in msg for s in ("401", "403", "API key", "PERMISSION_DENIED")):
        return "The AI provider rejected the API key. Check the key in your .env file."
    if any(s in msg for s in ("504", "DEADLINE_EXCEEDED", "timed out")):
        return "The AI model took too long to respond. Please try again."
    if "6333" in msg or "Connection refused" in msg:
        return "The vector database (Qdrant) is not reachable. Is Docker running?"
    if "Docstore not found" in msg:
        return "No documents are indexed yet. Run scripts/02_ingest.py first."
    return f"Something went wrong: {msg[:300]}"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/info")
def info() -> dict:
    try:
        chunks = load_docstore()
    except FileNotFoundError:
        chunks = []
    counts: dict[str, int] = {}
    for c in chunks:
        counts[c["source"]] = counts.get(c["source"], 0) + 1
    return {
        "model": settings.llm_model.partition(":")[2] or settings.llm_model,
        "web_verification": bool(settings.tavily_api_key),
        "max_revisions": settings.max_revisions,
        "documents": [{"name": n, "chunks": k} for n, k in sorted(counts.items())],
    }


@app.get("/documents/{name}", include_in_schema=False)
def document(name: str) -> FileResponse:
    path = (DOCS_DIR / name).resolve()
    if path.parent != DOCS_DIR.resolve() or not path.is_file():
        raise HTTPException(404, "Document not found")
    return FileResponse(path, media_type="application/pdf")


@app.post("/brief", response_model=BriefResponse)
def brief(req: BriefRequest) -> BriefResponse:
    started = time.time()
    try:
        state = generate_brief(req.question)
    except Exception as exc:
        raise HTTPException(502, _friendly_error(exc)) from exc
    return _response(state, started)


@app.post("/brief/stream")
def brief_stream(req: BriefRequest) -> StreamingResponse:
    """NDJSON: {"type":"step",...} per agent, then {"type":"result"} or {"type":"error"}."""
    def events():
        started = time.time()
        try:
            for node, nxt, state in stream_brief(req.question):
                critique = state.get("critique", {})
                yield json.dumps({
                    "type": "step", "node": node, "next": nxt,
                    "pass": state.get("revision_count", 0) + 1,
                    "chunks": len(state.get("retrieved", [])),
                    "grounded": critique.get("grounded"),
                    "support_ratio": critique.get("support_ratio"),
                    "verification_skipped": "skipped" in state.get("verification", ""),
                    "elapsed_s": round(time.time() - started, 1),
                }) + "\n"
            yield json.dumps({"type": "result",
                              **_response(state, started).model_dump()}) + "\n"
        except Exception as exc:
            print(f"[api] error: {exc!r}")
            yield json.dumps({"type": "error", "message": _friendly_error(exc)}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")
