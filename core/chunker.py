"""
Code-aware text chunker — splits documents using language-appropriate
separators so that functions/classes stay together when possible.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_core.documents import Document

from . import config


_EXT_TO_LANGUAGE: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".js": Language.JS,
    ".ts": Language.TS,
    ".jsx": Language.JS,
    ".tsx": Language.TS,
    ".java": Language.JAVA,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".cpp": Language.CPP,
    ".c": Language.CPP,
    ".h": Language.CPP,
    ".hpp": Language.CPP,
    ".rb": Language.RUBY,
    ".php": Language.PHP,
    ".swift": Language.SWIFT,
    ".html": Language.HTML,
    ".md": Language.MARKDOWN,
}


def _get_splitter(extension: str) -> RecursiveCharacterTextSplitter:
    lang = _EXT_TO_LANGUAGE.get(extension)

    if lang is not None:
        return RecursiveCharacterTextSplitter.from_language(
            language=lang,
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
        )

    return RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )


def chunk_documents(documents: list[Document]) -> list[Document]:
    """
    Split a list of Documents into smaller chunks.
    Uses language-aware splitting when possible.
    """
    all_chunks: list[Document] = []

    for doc in documents:
        extension = doc.metadata.get("extension", "")
        splitter = _get_splitter(extension)

        chunks = splitter.split_documents([doc])

        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                "chunk_index": i,
                "total_chunks": len(chunks),
            })
            all_chunks.append(chunk)

    return all_chunks
