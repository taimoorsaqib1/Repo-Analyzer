"""
Embedding provider abstraction — returns the right embedding model
based on the configured provider (OpenAI or Ollama).
"""

from langchain_core.embeddings import Embeddings
from . import config


def get_embeddings() -> Embeddings:
    """
    Return an embedding model based on config.PROVIDER.

    - "openai" → OpenAIEmbeddings (requires OPENAI_API_KEY)
    - "ollama" → OllamaEmbeddings (requires Ollama running locally)
    """
    if config.PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=config.OPENAI_EMBED_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
        )

    elif config.PROVIDER == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=config.OLLAMA_EMBED_MODEL,
            base_url=config.OLLAMA_BASE_URL,
        )

    else:
        raise ValueError(
            f"Unknown provider '{config.PROVIDER}'. Use 'openai' or 'ollama'."
        )
