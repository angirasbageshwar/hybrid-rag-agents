"""STEP 3 — Ask the multi-agent network a question from the terminal.

Example:
  python scripts/03_ask.py "Summarize ACME's Q3 2025 revenue by segment and flag any contract risks."
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from src.agents.graph import generate_brief
from src.tracing import report_tracing_status


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python scripts/03_ask.py "your question"')
    print(report_tracing_status())
    question = " ".join(sys.argv[1:])
    state = generate_brief(question)

    print("\n" + "=" * 78)
    print(state.get("final_brief", "(no brief produced)"))
    print("=" * 78)
    c = state.get("critique", {})
    print(f"\nSelf-RAG grade -> grounded={c.get('grounded')} "
          f"support_ratio={c.get('support_ratio')} "
          f"revisions_used={state.get('revision_count', 0)}")


if __name__ == "__main__":
    main()
