"""
LLM provider abstraction — returns the right chat model
based on the configured provider (OpenAI or Ollama).
"""

from langchain_core.language_models import BaseChatModel
from . import config


def get_llm() -> BaseChatModel:
    """
    Return a chat LLM based on config.PROVIDER.

    - "gemini" → ChatGoogleGenerativeAI (requires GEMINI_API_KEY)
    - "openai" → ChatOpenAI (requires OPENAI_API_KEY)
    - "ollama" → ChatOllama (requires Ollama running locally)
    """
    if config.PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=config.GEMINI_LLM_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.1,
        )

    elif config.PROVIDER == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.OPENAI_LLM_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
            temperature=0.1,
        )

    elif config.PROVIDER == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=config.OLLAMA_LLM_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            temperature=0.1,
        )

    else:
        raise ValueError(
            f"Unknown provider '{config.PROVIDER}'. Use 'gemini', 'openai', or 'ollama'."
        )
