"""
Hybrid retriever — combines BM25 keyword search with ChromaDB MMR
vector search using Reciprocal Rank Fusion (RRF) for higher precision.

Keyword search catches exact symbol names / error strings that pure
vector search misses; vector search catches semantically similar code
that keyword search misses. RRF merges both ranked lists so docs that
appear in both get a strong boost.
"""

from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever

from . import config
from .vectorstore import load_vectorstore


def _reciprocal_rank_fusion(
    results_lists: list[list[Document]], k: int = 60
) -> list[Document]:
    """
    Merge multiple ranked result lists with Reciprocal Rank Fusion.
    Documents appearing in several lists receive a cumulative score boost.
    Formula: score(d) = Σ  1 / (k + rank(d, list))
    """
    scores: dict[str, float] = {}
    docs_map: dict[str, Document] = {}

    for results in results_lists:
        for rank, doc in enumerate(results):
            # Stable identity key: source path + chunk index + first 50 chars
            doc_id = (
                doc.metadata.get("source", "")
                + str(doc.metadata.get("chunk_index", ""))
                + doc.page_content[:50]
            )
            if doc_id not in docs_map:
                scores[doc_id] = 0.0
                docs_map[doc_id] = doc
            scores[doc_id] += 1.0 / (k + rank + 1)

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [docs_map[i] for i in sorted_ids]


def _load_all_documents(collection_name: str | None = None) -> list[Document]:
    """
    Pull every stored document from ChromaDB for BM25 corpus construction.
    Called once per CodingAssistant instantiation.
    """
    store = load_vectorstore(collection_name)
    collection = store._collection
    result = collection.get(include=["documents", "metadatas"])

    docs: list[Document] = []
    for content, metadata in zip(result["documents"], result["metadatas"]):
        docs.append(Document(page_content=content, metadata=metadata or {}))
    return docs


class HybridRetriever:
    """
    Fuses BM25 (keyword) and ChromaDB MMR (vector) results via RRF.
    Exposes a single `.invoke(query)` interface compatible with
    the rest of the codebase.
    """

    def __init__(self, vector_retriever, bm25_retriever: BM25Retriever):
        self._vector = vector_retriever
        self._bm25 = bm25_retriever

    def invoke(self, query: str) -> list[Document]:
        vector_results = self._vector.invoke(query)
        bm25_results = self._bm25.invoke(query)
        fused = _reciprocal_rank_fusion([vector_results, bm25_results])
        return fused[: config.RETRIEVER_K]


def get_retriever(collection_name: str | None = None) -> HybridRetriever:
    """
    Build and return a HybridRetriever that combines:
      • ChromaDB MMR vector search (semantic similarity + diversity)
      • BM25 keyword search (exact token matching)
    Results are merged with Reciprocal Rank Fusion.
    """
    store = load_vectorstore(collection_name)

    vector_retriever = store.as_retriever(
        search_type=config.RETRIEVER_SEARCH_TYPE,
        search_kwargs={"k": config.RETRIEVER_K},
    )

    all_docs = _load_all_documents(collection_name)
    bm25_retriever = BM25Retriever.from_documents(
        all_docs, k=config.RETRIEVER_K
    )

    return HybridRetriever(vector_retriever, bm25_retriever)
