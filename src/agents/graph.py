"""Wires the three agents into a LangGraph state machine with a Self-RAG loop.

    START -> researcher -> fact_checker -> critic --grounded?--> finalize -> END
                 ^                                   |
                 +---------- revise (feedback) ------+   (max MAX_REVISIONS loops)

Note: the spec allows CrewAI as an alternative; LangGraph was chosen because
conditional edges make the revision loop explicit and unit-testable.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from src.agents.critic import critic_node
from src.agents.fact_checker import fact_checker_node
from src.agents.prompts import FINALIZER_SYSTEM
from src.agents.researcher import researcher_node
from src.agents.state import BriefState
from src.config import settings
from src.llm import get_llm


def finalize_node(state: BriefState) -> dict:
    print("[finalize] composing executive briefing")
    llm = get_llm(temperature=0.2)
    critique = state.get("critique", {})
    msg = llm.invoke([
        SystemMessage(content=FINALIZER_SYSTEM),
        HumanMessage(content=(
            f"QUESTION:\n{state['question']}\n\n"
            f"GROUNDED FINDINGS:\n{state['findings']}\n\n"
            f"WEB VERIFICATION:\n{state.get('verification','(none)')}\n\n"
            f"CRITIC NOTES:\n{critique.get('issues', [])}"
        )),
    ])
    return {"final_brief": msg.content}


def route_after_critic(state: BriefState) -> str:
    grounded = bool(state.get("critique", {}).get("grounded"))
    if grounded or state.get("revision_count", 0) >= settings.max_revisions:
        return "finalize"
    return "revise"


def build_graph():
    g = StateGraph(BriefState)
    g.add_node("researcher", researcher_node)
    g.add_node("fact_checker", fact_checker_node)
    g.add_node("critic", critic_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "researcher")
    g.add_edge("researcher", "fact_checker")
    g.add_edge("fact_checker", "critic")
    g.add_conditional_edges("critic", route_after_critic,
                            {"revise": "researcher", "finalize": "finalize"})
    g.add_edge("finalize", END)
    return g.compile()


def generate_brief(question: str) -> dict:
    """Public entrypoint used by both the CLI and the FastAPI service."""
    app = build_graph()
    result = app.invoke({"question": question, "revision_count": 0},
                        config={"recursion_limit": 25})
    return result


_NEXT = {"researcher": "fact_checker", "fact_checker": "critic", "finalize": None}


def stream_brief(question: str):
    """Same run as `generate_brief`, but yields (node, next_node, state) after
    every agent step so a UI can show live progress."""
    app = build_graph()
    state: dict = {"question": question, "revision_count": 0}
    for update in app.stream(dict(state), config={"recursion_limit": 25},
                             stream_mode="updates"):
        for node, delta in update.items():
            state.update(delta or {})
            nxt = (("researcher" if route_after_critic(state) == "revise" else "finalize")
                   if node == "critic" else _NEXT.get(node))
            yield node, nxt, state
