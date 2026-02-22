"""
Coding Assistant — RAG chain that combines retriever + LLM + prompt
to answer questions about your codebase.

Phase 1 enhancements:
  • Hybrid retrieval (BM25 + MMR via RRF) — done in retriever.py
  • Contextual chunk enrichment — done in chunker.py
  • Cross-encoder re-ranking — applied here before building the prompt.
    After the hybrid retriever returns its fused top-K candidates, a
    lightweight CrossEncoder scores every (query, chunk) pair and keeps
    only the best RERANKER_TOP_N.  This removes low-relevance chunks that
    survived RRF and sharpens the context window sent to the LLM.
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .retriever import get_retriever
from .llm import get_llm

# ── Re-ranker config ──────────────────────────────────────────────────────────
# BAAI/bge-reranker-base is small (~280 MB), runs on CPU, and
# significantly outperforms bi-encoder ranking on code Q&A benchmarks.
_RERANKER_MODEL = "BAAI/bge-reranker-base"
_RERANKER_TOP_N = 4          # docs kept after re-ranking
_reranker = None             # lazy singleton


def _get_reranker():
    """Lazily load the CrossEncoder so start-up stays fast."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder  # type: ignore
            _reranker = CrossEncoder(_RERANKER_MODEL)
        except Exception:
            # Graceful degradation: if sentence-transformers is missing
            # or the model fails to load, skip re-ranking silently.
            _reranker = False
    return _reranker


def _rerank(query: str, docs: list[Document]) -> list[Document]:
    """
    Score every (query, chunk) pair with a cross-encoder and return
    the top _RERANKER_TOP_N documents sorted by descending relevance.

    Falls back to the original ranked list when the re-ranker is
    unavailable so the assistant still works without sentence-transformers.
    """
    if not docs:
        return docs

    reranker = _get_reranker()
    if not reranker:
        # Re-ranker unavailable — return as-is (hybrid retriever already
        # applied RRF, so ordering is already meaningful).
        return docs[:_RERANKER_TOP_N]

    # Use original_content if present (clean code without context header)
    texts = [
        doc.metadata.get("original_content", doc.page_content)
        for doc in docs
    ]
    pairs = [(query, text) for text in texts]
    scores = reranker.predict(pairs)

    scored = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:_RERANKER_TOP_N]]


SYSTEM_PROMPT = """\
You are an expert senior software engineer acting as a coding assistant.
You have access to relevant source code from the user's project.

Your responsibilities:
1. Answer questions about the codebase accurately and concisely.
2. Explain how code works, including control flow and design patterns.
3. Suggest improvements, refactors, or bug fixes when asked.
4. Reference specific files and line-level details when relevant.

Guidelines:
- Ground your answers in the provided code context. If the context doesn't
  contain enough information, say so honestly.
- Use code blocks with language tags when showing code.
- Be concise but thorough.
- When referencing files, use the source path from the metadata.
"""


def _format_context(docs: list[Document]) -> str:
    """
    Format retrieved (and re-ranked) documents into a readable context block.
    Uses metadata["original_content"] when available so the LLM sees clean
    code without the embedding context header injected by the chunker.
    """
    parts: list[str] = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        language = doc.metadata.get("language", "")
        repo = doc.metadata.get("repository", "")
        repo_info = f" [{repo}]" if repo else ""
        chunk_info = ""
        if "chunk_index" in doc.metadata:
            chunk_info = (
                f" (chunk {doc.metadata['chunk_index']+1}"
                f"/{doc.metadata['total_chunks']})"
            )

        # Prefer the preserved original code over the enriched embedding text
        content = doc.metadata.get("original_content", doc.page_content)

        parts.append(
            f"--- File: {source}{chunk_info}{repo_info} [{language}] ---\n"
            f"{content}\n"
        )

    return "\n".join(parts)


class CodingAssistant:
    """RAG-powered coding assistant."""

    def __init__(self, collection_name: str | None = None):
        self.retriever = get_retriever(collection_name)
        self.llm = get_llm()
        self.history: list[HumanMessage | AIMessage] = []

    def ask(self, question: str) -> tuple[str, list[Document]]:
        """Ask a question about the codebase."""
        # 1. Hybrid retrieval (BM25 + MMR via RRF)
        relevant_docs = self.retriever.invoke(question)
        # 2. Cross-encoder re-ranking — keeps only the most relevant chunks
        relevant_docs = _rerank(question, relevant_docs)
        context = _format_context(relevant_docs)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *self.history[-10:],
            HumanMessage(
                content=(
                    f"Here is the relevant code from the project:\n\n"
                    f"{context}\n\n"
                    f"Question: {question}"
                )
            ),
        ]

        response = self.llm.invoke(messages)
        answer = response.content

        self.history.append(HumanMessage(content=question))
        self.history.append(AIMessage(content=answer))

        return answer, relevant_docs

    def stream_ask(self, question: str):
        """
        Stream tokens for a question. Yields str tokens, then
        finally yields a tuple (sources_list,) to signal completion.
        """
        # 1. Hybrid retrieval (BM25 + MMR via RRF)
        relevant_docs = self.retriever.invoke(question)
        # 2. Cross-encoder re-ranking — keeps only the most relevant chunks
        relevant_docs = _rerank(question, relevant_docs)
        context = _format_context(relevant_docs)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *self.history[-10:],
            HumanMessage(
                content=(
                    f"Here is the relevant code from the project:\n\n"
                    f"{context}\n\n"
                    f"Question: {question}"
                )
            ),
        ]

        full_answer = ""
        for chunk in self.llm.stream(messages):
            token = chunk.content
            full_answer += token
            yield token

        self.history.append(HumanMessage(content=question))
        self.history.append(AIMessage(content=full_answer))

        # Signal done — yield docs as final item
        yield relevant_docs

    def clear_history(self):
        """Clear conversation history."""
        self.history.clear()

    def get_sources(self, docs: list[Document]) -> list[str]:
        """Extract unique source file paths from documents."""
        seen: set[str] = set()
        sources: list[str] = []
        for doc in docs:
            src = doc.metadata.get("source", "unknown")
            repo = doc.metadata.get("repository", "")
            label = f"{repo}/{src}" if repo else src
            if label not in seen:
                seen.add(label)
                sources.append(label)
        return sources
