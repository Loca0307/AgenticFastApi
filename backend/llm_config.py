import os

from langchain_openai import ChatOpenAI

LOCAL_API_KEY = "ollama"
LOCAL_MODEL = "qwen3:14b"
LOCAL_BASE_URL = "http://127.0.0.1:11434/v1"
PRODUCTION_MODEL = "gpt-5.4-mini"


def is_production() -> bool:
    """Return true when running in AWS Lambda or an explicit production env."""

    return (
        os.getenv("APP_ENV", "").lower() == "production"
        or os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
    )


def get_chat_model() -> ChatOpenAI:
    """Create the chat model used by the LangGraph agents.

    Local development uses Ollama's OpenAI-compatible API. AWS Lambda uses the
    real OpenAI API and reads its API key from the Lambda environment.
    """

    if is_production():
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", PRODUCTION_MODEL),
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    return ChatOpenAI(
        model=os.getenv("OLLAMA_MODEL", os.getenv("OPENAI_MODEL", LOCAL_MODEL)),
        temperature=0.7,
        api_key=os.getenv("OLLAMA_API_KEY", LOCAL_API_KEY),
        base_url=os.getenv("OLLAMA_BASE_URL", os.getenv("OPENAI_BASE_URL", LOCAL_BASE_URL)),
    )
