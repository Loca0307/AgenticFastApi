import os

from langchain_openai import ChatOpenAI


DEFAULT_MODEL = "qwen3:14b"
DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"


def get_chat_model() -> ChatOpenAI:
    """Create the chat model used by the LangGraph agents.

    Ollama exposes an OpenAI-compatible API at /v1, so ChatOpenAI can talk to
    it by changing the base URL and using any non-empty API key.
    """

    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY", "ollama"),
        base_url=os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL),
    )
