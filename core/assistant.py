"""
Coding Assistant — RAG chain that combines retriever + LLM + prompt
to answer questions about your codebase.
"""

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .retriever import get_retriever
from .llm import get_llm


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
    """Format retrieved documents into a readable context block."""
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

        parts.append(
            f"--- File: {source}{chunk_info}{repo_info} [{language}] ---\n"
            f"{doc.page_content}\n"
        )

    return "\n".join(parts)


class CodingAssistant:
    """RAG-powered coding assistant."""

    def __init__(self):
        self.retriever = get_retriever()
        self.llm = get_llm()
        self.history: list[HumanMessage | AIMessage] = []

    def ask(self, question: str) -> tuple[str, list[Document]]:
        """Ask a question about the codebase."""
        relevant_docs = self.retriever.invoke(question)
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
        relevant_docs = self.retriever.invoke(question)
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
