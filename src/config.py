"""Central configuration. Every knob lives here; values come from .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM — "provider:model" string consumed by langchain's init_chat_model
    llm_model: str = "openai:gpt-4o-mini"
    # Comma-separated backups tried in order when the main model errors
    # (e.g. free-tier daily quota): "google_genai:gemini-3.5-flash-lite,groq:..."
    llm_fallbacks: str = ""

    # Vector DB
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "enterprise_docs"

    # Local (free) embedding + reranking models
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Hybrid retrieval knobs
    dense_top_k: int = 20        # candidates from vector search
    sparse_top_k: int = 20       # candidates from BM25
    rerank_top_k: int = 6        # final chunks handed to the LLM
    rrf_k: int = 60              # Reciprocal Rank Fusion constant

    # Ingestion
    pdf_strategy: str = "fast"   # "hi_res" for best table extraction
    docstore_path: str = "data/docstore.jsonl"

    # Web verification
    tavily_api_key: str = ""
    max_claims_to_verify: int = 4

    # Self-RAG loop
    max_revisions: int = 2


settings = Settings()
