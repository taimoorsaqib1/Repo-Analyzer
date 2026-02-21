"""
Smart retriever — wraps the vector store with MMR search
for diverse, relevant results.
"""

from langchain_core.vectorstores import VectorStoreRetriever

from . import config
from .vectorstore import load_vectorstore


def get_retriever() -> VectorStoreRetriever:
    """
    Create a retriever from the persisted vector store.
    Uses Maximal Marginal Relevance (MMR) search to balance
    relevance with diversity.
    """
    store = load_vectorstore()

    retriever = store.as_retriever(
        search_type=config.RETRIEVER_SEARCH_TYPE,
        search_kwargs={"k": config.RETRIEVER_K},
    )

    return retriever
