"""
ChromaDB vector store — create, persist, and load the vector database.
"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_chroma import Chroma

from . import config
from .embeddings import get_embeddings


def clear_vectorstore() -> None:
    """Delete the existing ChromaDB collection."""
    import shutil
    import chromadb

    persist_dir = Path(config.CHROMA_PERSIST_DIR).resolve()
    if not persist_dir.exists():
        return

    try:
        client = chromadb.PersistentClient(path=str(persist_dir))
        collections = [c.name for c in client.list_collections()]
        if config.CHROMA_COLLECTION in collections:
            client.delete_collection(config.CHROMA_COLLECTION)
    except Exception:
        shutil.rmtree(persist_dir, ignore_errors=True)


def create_vectorstore(documents: list[Document]) -> Chroma:
    """Create a new ChromaDB collection from documents and persist it."""
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
    """Load an existing persisted ChromaDB collection."""
    persist_dir = Path(config.CHROMA_PERSIST_DIR).resolve()

    if not persist_dir.exists():
        raise FileNotFoundError(
            f"No vector store found at {persist_dir}. "
            "Index a repository first."
        )

    embedding_fn = get_embeddings()

    return Chroma(
        collection_name=config.CHROMA_COLLECTION,
        embedding_function=embedding_fn,
        persist_directory=str(persist_dir),
    )
