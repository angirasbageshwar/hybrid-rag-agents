"""Shared state that flows through the LangGraph. Every node reads from and
writes small updates into this one dictionary."""
from typing import TypedDict


class BriefState(TypedDict, total=False):
    question: str            # the executive's ask
    retrieved: list[dict]    # reranked chunks from hybrid search
    findings: str            # Researcher's synthesis (with [chunk_id] citations)
    verification: str        # Fact-Checker's web-verified claim report
    critique: dict           # Critic's Self-RAG grade {"grounded": bool, ...}
    feedback: str            # Critic's fix-it notes fed back to the Researcher
    revision_count: int      # how many Self-RAG loops we've run
    final_brief: str         # the polished executive briefing
