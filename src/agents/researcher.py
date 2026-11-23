"""Agent 1 — Researcher.
Runs hybrid retrieval + cross-encoder reranking, then synthesizes a cited
findings memo. On Self-RAG revision passes it also receives the Critic's
feedback and must repair the draft."""
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts import RESEARCHER_SYSTEM, RESEARCHER_REVISION_SUFFIX
from src.agents.state import BriefState
from src.llm import get_llm
from src.retrieval.hybrid import hybrid_search


def _format_chunks(chunks: list[dict]) -> str:
    blocks = []
    for c in chunks:
        blocks.append(
            f"<chunk id=\"{c['id']}\" source=\"{c['source']}\" "
            f"page=\"{c.get('page')}\" kind=\"{c['kind']}\">\n{c['text']}\n</chunk>"
        )
    return "\n\n".join(blocks)


def researcher_node(state: BriefState) -> dict:
    question = state["question"]
    feedback = state.get("feedback", "")
    rev = state.get("revision_count", 0)
    print(f"\n[researcher] pass {rev + 1} — retrieving for: {question!r}")

    chunks = hybrid_search(question)

    system = RESEARCHER_SYSTEM
    if feedback:
        system += RESEARCHER_REVISION_SUFFIX.format(feedback=feedback)

    llm = get_llm(temperature=0.1)
    msg = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=(
            f"QUESTION:\n{question}\n\nRETRIEVED CHUNKS:\n{_format_chunks(chunks)}"
        )),
    ])
    return {"retrieved": chunks, "findings": msg.content}
