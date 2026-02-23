"""
Embedding provider abstraction — returns the right embedding model
based on the configured provider (OpenAI or Ollama) or EMBED_PROVIDER override.

When PROVIDER=gemini, EMBED_PROVIDER defaults to "local" (sentence-transformers)
so that bulk indexing never hits Gemini API rate limits. Gemini is only used
for chat (far fewer API calls).
"""

from langchain_core.embeddings import Embeddings
from . import config


def get_embeddings() -> Embeddings:
    """
    Return an embedding model based on config.EMBED_PROVIDER.

    - "local"  → HuggingFaceEmbeddings / sentence-transformers (free, offline)
    - "gemini" → GoogleGenerativeAIEmbeddings (requires GEMINI_API_KEY)
    - "openai" → OpenAIEmbeddings (requires OPENAI_API_KEY)
    - "ollama" → OllamaEmbeddings (requires Ollama running locally)
    """
    embed_provider = config.EMBED_PROVIDER

    if embed_provider == "local":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=config.LOCAL_EMBED_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

    elif embed_provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=config.GEMINI_EMBED_MODEL,
            google_api_key=config.GEMINI_API_KEY,
        )

    elif embed_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=config.OPENAI_EMBED_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
        )

    elif embed_provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=config.OLLAMA_EMBED_MODEL,
            base_url=config.OLLAMA_BASE_URL,
        )

    else:
        raise ValueError(
            f"Unknown embed provider '{embed_provider}'. Use 'local', 'gemini', 'openai', or 'ollama'."
        )

