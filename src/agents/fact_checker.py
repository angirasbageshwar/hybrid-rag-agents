"""Agent 2 — Fact-Checker.
Pulls the most important externally-checkable claims out of the memo, hits a
live web search API (Tavily) for each, and asks the LLM for a verdict.
Degrades gracefully to 'skipped' when no TAVILY_API_KEY is configured."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts import CLAIM_EXTRACTOR_SYSTEM, VERIFIER_SYSTEM
from src.agents.state import BriefState
from src.config import settings
from src.llm import get_llm


def _extract_claims(findings: str) -> list[str]:
    llm = get_llm(temperature=0.0)
    msg = llm.invoke([
        SystemMessage(content=CLAIM_EXTRACTOR_SYSTEM.format(n=settings.max_claims_to_verify)),
        HumanMessage(content=findings),
    ])
    raw = msg.content.strip().strip("`")
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()
    try:
        claims = json.loads(raw)
        return [str(c) for c in claims][: settings.max_claims_to_verify]
    except json.JSONDecodeError:
        return []


def _web_search(query: str) -> list[dict]:
    from tavily import TavilyClient  # local import: optional dependency path
    client = TavilyClient(api_key=settings.tavily_api_key)
    res = client.search(query=query, max_results=3)
    return res.get("results", [])


def fact_checker_node(state: BriefState) -> dict:
    if not settings.tavily_api_key:
        print("[fact-checker] TAVILY_API_KEY missing — skipping web verification")
        return {"verification": "Web verification skipped (no TAVILY_API_KEY configured)."}

    claims = _extract_claims(state["findings"])
    print(f"[fact-checker] verifying {len(claims)} claims against the live web")
    if not claims:
        return {"verification": "No externally checkable claims were identified."}

    llm = get_llm(temperature=0.0)
    lines = []
    for claim in claims:
        try:
            hits = _web_search(claim)
        except Exception as exc:  # network / quota issues shouldn't kill the run
            lines.append(f"- CLAIM: {claim}\n  UNVERIFIED — search error: {exc}")
            continue
        snippets = "\n".join(
            f"[{h.get('title','?')} | {h.get('url','')}] {h.get('content','')[:400]}"
            for h in hits
        ) or "No results."
        verdict = llm.invoke([
            SystemMessage(content=VERIFIER_SYSTEM),
            HumanMessage(content=f"CLAIM: {claim}\n\nWEB SNIPPETS:\n{snippets}"),
        ]).content.strip()
        lines.append(f"- CLAIM: {claim}\n  {verdict}")

    return {"verification": "\n".join(lines)}
