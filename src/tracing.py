"""LangSmith tracing bootstrap.

LangGraph auto-emits traces when these env vars are set — no code changes needed.
This helper just tells the operator whether tracing is live.
"""
import os


def report_tracing_status() -> str:
    enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    has_key = bool(os.getenv("LANGSMITH_API_KEY"))
    project = os.getenv("LANGSMITH_PROJECT", "default")
    if enabled and has_key:
        return f"[tracing] LangSmith ON -> project '{project}' (token usage, latency, and every agent step will be recorded)"
    return "[tracing] LangSmith OFF — set LANGSMITH_TRACING=true and LANGSMITH_API_KEY in .env to record agent runs"
