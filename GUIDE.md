# 📘 GUIDE — Project 1: Enterprise Multi-Agent Knowledge Network
### Explained in simple words, from zero

---

## 1. What did we actually build?

Imagine a company hires **three people** to answer a hard question like
*"How did our robotics revenue do last quarter, and are there risks in our big contract?"*

1. **A Researcher** — goes into the company's filing cabinet (PDFs: financial
   reports, legal contracts), pulls the right pages, and writes a memo. Every
   sentence in the memo has a footnote pointing to the exact page it came from.
2. **A Fact-Checker** — takes the memo's big claims and Googles them (live web
   search) to see if the outside world agrees.
3. **A Critic** — a strict editor who compares the memo against the pulled
   pages, sentence by sentence. If even one sentence isn't backed by the
   documents, the memo goes **back to the Researcher** with red-pen notes.

Only when the Critic approves does a final **executive briefing** go out.

That team is exactly what this project builds — except the three people are
three AI agents wired together with **LangGraph**, and the filing cabinet is a
**hybrid search engine**. The "send it back" step is the famous
**Self-RAG loop**, and it's what makes "zero hallucinations" a real engineering
goal instead of a marketing line: unsupported claims literally cannot pass the gate.

---

## 2. The big ideas, one by one (simple words)

### 🧠 RAG (Retrieval-Augmented Generation)
An LLM alone answers from memory — and memory lies confidently. RAG means:
**first fetch the real documents, then let the model answer using ONLY those
documents.** The model becomes an open-book exam taker instead of a guesser.

### 🔢 Embeddings & dense vectors (the "meaning" search)
Every text chunk is converted into a list of 384 numbers (a **vector**) that
encodes its *meaning*. Similar meanings → similar numbers. So "revenue grew"
and "sales increased" land near each other even though they share no words.
We store these vectors in **Qdrant**, a database built to answer *"which
stored vectors are closest to this query vector?"* in milliseconds.

### 🔤 BM25 sparse search (the "exact words" search)
Embeddings are great at meaning but blurry on exact tokens. Ask for
*"Clause 14.2"* or *"Q3 2025"* and a meaning-search may hand you Clause 9 from
Q2. **BM25** is classic keyword scoring (a smarter cousin of what old search
engines used) — it's razor sharp on exact codes, tickers, dates, part numbers.

### 🤝 Hybrid search + RRF (best of both)
We run **both** searches and merge them with **Reciprocal Rank Fusion**:
each result earns points based on its *position* in each list —
`1 / (60 + rank)` — and points add up. No messy score normalization; a chunk
that ranks well in either list floats to the top. (Code: `src/retrieval/hybrid.py`.)

### 🎯 Cross-encoder reranker (the precision pass)
Embedding search compares query and document *separately* (fast, coarse).
A **cross-encoder** reads the query and a candidate chunk **together** through
one transformer and outputs a single relevance score (slow, precise). So the
strategy is: recall ~40 candidates cheaply → rerank them carefully → keep the
best 6 for the LLM. Wide net, then a fine sieve.

### 📄 Table-aware PDF parsing (`unstructured`)
Financial PDFs hide their gold in **nested tables**. Naive text extraction
shreds a table into word soup ("148.2 96.7 EMEA…"). The `unstructured` library
detects layout and hands tables over as **whole HTML blocks**, which we keep as
single chunks — so "Industrial Automation, EMEA, Q3 2025 = 96.7" stays intact.
(LlamaParse is a drop-in alternative; the swap point is marked in `pdf_parser.py`.)

### 🔁 Self-RAG (the anti-hallucination loop)
After drafting, the **Critic** agent gets both the draft AND the raw retrieved
chunks and must output a JSON verdict: `grounded: true/false`, a support ratio,
the exact unsupported sentences, and fix-it feedback. `grounded: false` routes
the graph **back to the Researcher** (max 2 loops, so it can't spin forever).
Two safety details worth noticing in `critic.py`:
- If the Critic's JSON can't be parsed, we **fail closed** — treat it as
  not-grounded rather than shipping an unverified draft.
- The loop cap lives in config (`MAX_REVISIONS`), not hard-coded.

### 🕸️ LangGraph (why not just one big prompt?)
LangGraph lets us draw the workflow as a **state machine**: nodes (agents) and
edges (routes), including a *conditional* edge ("grounded? → finalize : revise").
One big prompt can't loop, can't be unit-tested per step, and can't be traced
per step. (CrewAI is the role-based alternative the spec allows; the graph
design translates directly.)

### 🔍 LangSmith (watching the agents think)
Set three env vars and every run records itself: each node's inputs/outputs,
**latency per step, tokens per step**, and the full reasoning path. When the
Critic loops twice, you see both loops. This is LLMOps: you can't fix what you
can't see.

---

## 3. Follow one question through the system

> You ask: *"Summarize ACME's Q3 revenue by segment and flag contract risks."*

1. **Researcher** embeds your question → Qdrant returns 20 meaning-matches;
   BM25 returns 20 keyword-matches ("Q3", "segment") → RRF fuses → cross-encoder
   keeps the best 6 chunks (including the revenue **table** and MSA clauses).
2. Researcher writes a memo, citing chunk ids like `[a1b2c3d4]`.
3. **Fact-Checker** extracts up to 4 checkable claims, searches the live web
   (Tavily), and labels each `SUPPORTED / CONTRADICTED / UNVERIFIED`.
4. **Critic** grades the memo vs. the 6 chunks. Say it finds one invented
   number → `grounded: false` + feedback → **back to step 1** with the notes.
5. Second pass survives the Critic → **Finalize** writes the briefing:
   *Bottom Line / Key Findings (with citations) / External Verification /
   Risks & Caveats.* You get the answer **plus the audit trail**.

---

## 4. File map & the order to read them

| # | File | What it does (one line) |
|---|------|--------------------------|
| 1 | `.env.example` | All keys & knobs — copy to `.env` |
| 2 | `src/config.py` | Every tunable in one typed settings class |
| 3 | `src/ingestion/pdf_parser.py` | PDFs → table-aware chunks → `docstore.jsonl` |
| 4 | `src/retrieval/vector_store.py` | Embeds chunks → Qdrant (dense) |
| 5 | `src/retrieval/bm25_store.py` | Keyword index rebuilt from the docstore |
| 6 | `src/retrieval/hybrid.py` | RRF fusion of both lists |
| 7 | `src/retrieval/reranker.py` | Cross-encoder precision pass |
| 8 | `src/agents/state.py` | The shared dict flowing between agents |
| 9 | `src/agents/prompts.py` | Every prompt, auditable in one file |
| 10 | `src/agents/researcher.py` | Agent 1 |
| 11 | `src/agents/fact_checker.py` | Agent 2 (live web) |
| 12 | `src/agents/critic.py` | Agent 3 (Self-RAG grader) |
| 13 | `src/agents/graph.py` | LangGraph wiring incl. the revision loop |
| 14 | `src/api.py` | FastAPI endpoint (`POST /brief`) |
| 15 | `scripts/01…03` | Generate data → ingest → ask |
| 16 | `Dockerfile`, `k8s/` | Container + EKS manifests |

Run order lives in `README.md` (5 commands).

---

## 5. Design decisions you should be able to defend

- **Why local embedding models?** MiniLM runs free & on-CPU; retrieval quality
  is decided far more by the reranker + fusion than by a premium embedder.
  Swapping to a hosted embedder is a 2-line change in `vector_store.py`.
- **Why is the docstore JSONL the "source of truth" for BM25?** Rebuilding the
  keyword index from a plain file avoids pickle/version headaches and keeps the
  two indexes provably in sync (same file feeds both).
- **Why cap revisions at 2?** Each loop costs tokens and latency; empirically
  the 3rd pass rarely fixes what the 2nd didn't. The Critic's verdict still
  ships in the API response, so a still-ungrounded brief is *labeled* as such.
- **Why does the Fact-Checker degrade instead of crash without a key?** A
  verification layer should never take down the core answer path; it reports
  "skipped" honestly.

---

## 6. What can go wrong (and the fix)

| Symptom | Cause → Fix |
|---|---|
| `Connection refused :6333` | Qdrant down → `docker compose up -d` |
| `Docstore not found` | Skipped ingestion → `python scripts/02_ingest.py` |
| Tables come back as word soup | `fast` strategy on complex PDFs → `PDF_STRATEGY=hi_res` + `pip install unstructured-inference` |
| Critic loops every time | Question isn't answerable from the corpus — the system is *refusing to make things up*, which is the point. Add the right documents. |
| Slow first query | Models (embedder, reranker) download once, then cache |

---

## 7. Say it in an interview (30 seconds)

> "I built a multi-agent briefing system on LangGraph. Retrieval is hybrid —
> Qdrant dense vectors fused with BM25 via Reciprocal Rank Fusion, then a
> cross-encoder reranks. A Researcher agent drafts with chunk-level citations,
> a Fact-Checker verifies claims against live web search, and a Critic runs a
> Self-RAG grading loop that bounces ungrounded drafts back with feedback —
> failing closed on unparseable grades. It's containerized, ships with EKS
> manifests, and every step's tokens and latency are traced in LangSmith."

## 8. Ways to extend it
Add a fourth "Chart" agent that renders the table data; persist BM25 in
Elasticsearch/OpenSearch for scale; add Qdrant payload filters (per-department
access control); cache repeated questions; evaluate retrieval with a golden
question set (hit-rate@k before/after the reranker — great W&B-style experiment).
