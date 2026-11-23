"""Agent 3 — Critic (Self-RAG grader).
Grades the findings memo against the *actual retrieved chunks*. If any claim
lacks support, it fails the draft and writes precise fix-it feedback, which
routes the graph back to the Researcher — the anti-hallucination loop."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts import CRITIC_SYSTEM
from src.agents.state import BriefState
from src.llm import get_llm


def _safe_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        # Fail CLOSED: an unparseable grade is treated as "not grounded".
        return {"grounded": False, "support_ratio": 0.0,
                "issues": ["Critic output was not valid JSON"],
                "feedback": "Rewrite using only sentences directly supported by the chunks."}


def critic_node(state: BriefState) -> dict:
    print("[critic] grading draft for hallucination (Self-RAG)")
    chunks_text = "\n\n".join(
        f"[{c['id']}] {c['text']}" for c in state.get("retrieved", [])
    )
    llm = get_llm(temperature=0.0)
    msg = llm.invoke([
        SystemMessage(content=CRITIC_SYSTEM),
        HumanMessage(content=(
            f"RETRIEVED CHUNKS:\n{chunks_text}\n\nFINDINGS MEMO:\n{state['findings']}"
        )),
    ])
    grade = _safe_json(msg.content)
    grounded = bool(grade.get("grounded"))
    rev = state.get("revision_count", 0)
    print(f"[critic] grounded={grounded} support={grade.get('support_ratio')} "
          f"(revision {rev})")

    update: dict = {"critique": grade}
    if not grounded:
        update["revision_count"] = rev + 1
        update["feedback"] = grade.get("feedback", "Remove all unsupported claims.")
    return update
