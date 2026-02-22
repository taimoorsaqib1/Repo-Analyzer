"""
ChromaDB vector store — create, persist, and load the vector database.
"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_chroma import Chroma

from . import config
from .embeddings import get_embeddings


def _resolve_collection(collection_name: str | None) -> str:
    return collection_name or config.CHROMA_COLLECTION


def clear_vectorstore(collection_name: str | None = None) -> None:
    """Delete a named ChromaDB collection (defaults to config collection)."""
    import chromadb
    import shutil

    name = _resolve_collection(collection_name)
    persist_dir = Path(config.CHROMA_PERSIST_DIR).resolve()
    if not persist_dir.exists():
        return

    try:
        client = chromadb.PersistentClient(path=str(persist_dir))
        existing = [c.name for c in client.list_collections()]
        if name in existing:
            client.delete_collection(name)
    except Exception:
        if collection_name is None:
            # Only nuke the whole dir when clearing the default collection
            shutil.rmtree(persist_dir, ignore_errors=True)


def create_vectorstore(
    documents: list[Document],
    collection_name: str | None = None,
) -> Chroma:
    """Create a new named ChromaDB collection from documents and persist it."""
    name = _resolve_collection(collection_name)
    persist_dir = Path(config.CHROMA_PERSIST_DIR).resolve()
    persist_dir.mkdir(parents=True, exist_ok=True)

    embedding_fn = get_embeddings()

    return Chroma.from_documents(
        documents=documents,
        embedding=embedding_fn,
        collection_name=name,
        persist_directory=str(persist_dir),
    )


def load_vectorstore(collection_name: str | None = None) -> Chroma:
    """Load an existing persisted ChromaDB collection by name."""
    name = _resolve_collection(collection_name)
    persist_dir = Path(config.CHROMA_PERSIST_DIR).resolve()

    if not persist_dir.exists():
        raise FileNotFoundError(
            f"No vector store found at {persist_dir}. "
            "Index a repository first."
        )

    embedding_fn = get_embeddings()

    return Chroma(
        collection_name=name,
        embedding_function=embedding_fn,
        persist_directory=str(persist_dir),
    )
