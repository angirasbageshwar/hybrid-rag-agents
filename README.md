# Project 1 — Enterprise Multi-Agent Knowledge Network (Hybrid RAG)

An autonomous 3-agent system that reads unstructured corporate PDFs (financial
statements, legal contracts), cross-checks facts against the **live web**, and
produces **verified executive briefings** guarded by a Self-RAG anti-hallucination loop.

```
                 ┌──────────────── Self-RAG revision loop ───────────────┐
                 │                                                       │
 Question ──► RESEARCHER ──► FACT-CHECKER ──► CRITIC ──grounded──► FINALIZE ──► Brief
              (hybrid RAG:    (Tavily live     (grades draft vs
               Qdrant dense    web search +    retrieved chunks,
               + BM25 sparse   claim verdicts) fails ➜ feedback)
               + RRF fusion
               + cross-encoder rerank)
```

## Tech stack (maps 1:1 to the spec)
| Requirement | Implementation |
|---|---|
| Dense vectors | Qdrant + `all-MiniLM-L6-v2` (local, free) |
| Sparse keyword search | BM25 (`rank_bm25`) rebuilt from `data/docstore.jsonl` |
| Fusion | Reciprocal Rank Fusion — `src/retrieval/hybrid.py` |
| Reranker | Cross-encoder `ms-marco-MiniLM-L-6-v2` |
| Multi-agent framework | **LangGraph** (CrewAI-compatible design; loop is explicit) |
| PDF + nested tables | `unstructured` (`hi_res` mode) — LlamaParse swap noted in `pdf_parser.py` |
| Live web verification | Tavily Search API |
| Self-RAG | `src/agents/critic.py` + conditional edge in `graph.py` |
| Tracing (tokens/latency/steps) | LangSmith — auto via env vars |
| Container / Cloud | `Dockerfile`, `docker-compose.yml`, `k8s/` for **AWS EKS** |

## Build order (files, in the order they matter)
1. `.env.example` → copy to `.env`, add keys
2. `src/config.py` — every tunable knob
3. `src/ingestion/pdf_parser.py` — PDFs → table-aware chunks → `docstore.jsonl`
4. `src/retrieval/vector_store.py` → `bm25_store.py` → `hybrid.py` → `reranker.py`
5. `src/agents/` — `state.py` → `prompts.py` → `researcher.py` → `fact_checker.py` → `critic.py` → `graph.py`
6. `src/api.py` — FastAPI service
7. `scripts/01…03` — runnable steps · `k8s/` — EKS deploy

## Run it (exact order)
```bash
# 0. Python 3.11 recommended
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # add OPENAI_API_KEY (or Anthropic) + TAVILY_API_KEY

# 1. Start the vector DB
docker compose up -d                                    # Qdrant → http://localhost:6333/dashboard

# 2. Sample data (already included in data/sample_docs; re-generate anytime)
python scripts/01_generate_sample_data.py

# 3. Ingest → builds BOTH indexes (Qdrant dense + BM25 docstore)
python scripts/02_ingest.py

# 4. Ask the agent network
python scripts/03_ask.py "Summarize ACME's Q3 2025 revenue by segment and flag any contract risks in the MSA."

# 5. Or run the API
uvicorn src.api:app --reload --port 8080
curl -X POST localhost:8080/brief -H 'Content-Type: application/json' \
     -d '{"question":"What is ACME'\''s liability cap and how did Autonomous Systems perform?"}'
```

### Watch the agents think (LangSmith)
Set in `.env`: `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY=...`,
`LANGSMITH_PROJECT=knowledge-network` → open smith.langchain.com → your project.
You'll see every node, its latency, and **token consumption per step**.

## Deploy to AWS EKS
```bash
aws ecr create-repository --repository-name knowledge-network
docker build -t <ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/knowledge-network:v1 .
docker push  <ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/knowledge-network:v1

eksctl create cluster --name knowledge-net --nodes 2 --node-type t3.large
kubectl create secret generic llm-keys \
  --from-literal=OPENAI_API_KEY=... --from-literal=TAVILY_API_KEY=... \
  --from-literal=LANGSMITH_API_KEY=...
kubectl apply -f k8s/qdrant.yaml
kubectl apply -f k8s/deployment.yaml       # edit the image URI first
kubectl get svc knowledge-network-api      # EXTERNAL-IP → POST /brief
```
Note: on EKS you must re-run ingestion against the in-cluster Qdrant
(`kubectl port-forward svc/qdrant 6333:6333` then `python scripts/02_ingest.py`).

## Better tables
`PDF_STRATEGY=fast` (default) = quick start. For complex **nested tables** set
`PDF_STRATEGY=hi_res` in `.env` and `pip install "unstructured[pdf]" unstructured-inference`
(downloads a layout-detection model; the Dockerfile already includes poppler + tesseract).

## Troubleshooting
- `Connection refused :6333` → Qdrant isn't up → `docker compose up -d`
- `Docstore not found` → run step 3 (`scripts/02_ingest.py`)
- Critic always fails → your PDFs may be scanned images → use `hi_res` (OCR)
- Rate limits → lower `MAX_REVISIONS=1`, `max_claims_to_verify` in config

📘 **Plain-English walkthrough of every concept:** see `GUIDE.md`.
