"""
ChromaDB vector store — create, persist, and load the vector database.
"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_chroma import Chroma

import config
from embeddings import get_embeddings


def create_vectorstore(documents: list[Document]) -> Chroma:
    """
    Create a new ChromaDB collection from documents and persist it.

    Args:
        documents: Chunked Documents to embed and store.

    Returns:
        A Chroma vector store instance.
    """
    persist_dir = Path(config.CHROMA_PERSIST_DIR).resolve()
    persist_dir.mkdir(parents=True, exist_ok=True)

    embedding_fn = get_embeddings()

    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embedding_fn,
        collection_name=config.CHROMA_COLLECTION,
        persist_directory=str(persist_dir),
    )

    return vectorstore


def load_vectorstore() -> Chroma:
    """
    Load an existing persisted ChromaDB collection.

    Returns:
        A Chroma vector store instance.

    Raises:
        FileNotFoundError: If the persist directory doesn't exist.
    """
    persist_dir = Path(config.CHROMA_PERSIST_DIR).resolve()

    if not persist_dir.exists():
        raise FileNotFoundError(
            f"No vector store found at {persist_dir}. "
            "Run `python ingest.py <repo_path>` first to index a repository."
        )

    embedding_fn = get_embeddings()

    vectorstore = Chroma(
        collection_name=config.CHROMA_COLLECTION,
        embedding_function=embedding_fn,
        persist_directory=str(persist_dir),
    )

    return vectorstore
