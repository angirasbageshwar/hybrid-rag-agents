"""One place to construct the chat model, so swapping providers is a 1-line env change."""
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from src.config import settings


def _as_text(msg: AIMessage) -> AIMessage:
    """Some providers (e.g. Gemini) return content as a list of blocks; agents expect a str."""
    if isinstance(msg.content, str):
        return msg
    text = "".join(
        b if isinstance(b, str) else b.get("text", "")
        for b in msg.content
        if isinstance(b, str) or b.get("type") == "text"
    )
    return AIMessage(content=text, usage_metadata=msg.usage_metadata)


def _chat_model(spec: str, temperature: float, max_retries: int):
    provider, _, model = spec.strip().partition(":")
    return init_chat_model(model=model, model_provider=provider,
                           temperature=temperature, max_retries=max_retries)


def get_llm(temperature: float = 0.1):
    """Returns a LangChain chat model. `LLM_MODEL` env decides the provider.

    Examples: "openai:gpt-4o-mini", "anthropic:claude-sonnet-4-5",
              "google_genai:gemini-3.6-flash", "groq:llama-3.3-70b-versatile"
    `LLM_FALLBACKS` adds backup models tried in order if the main one fails.
    """
    backups = [s for s in settings.llm_fallbacks.split(",") if s.strip()]
    # With backups configured, fail over quickly instead of retrying a spent quota.
    llm = _chat_model(settings.llm_model, temperature, 1 if backups else 6)
    if backups:
        llm = llm.with_fallbacks([_chat_model(s, temperature, 2) for s in backups])
    return llm | RunnableLambda(_as_text)
