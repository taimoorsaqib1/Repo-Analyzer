"""
Code-aware text chunker — splits documents using language-appropriate
separators so that functions/classes stay together when possible.

Contextual Retrieval enhancement:
  Each chunk's embedded content is prefixed with a compact file-level
  header (file path, language, and the first lines of the file).  This
  ensures that even a small chunk of a deeply nested helper function
  carries enough context for the embedding model to place it correctly
  in vector space — dramatically reducing "lost chunk" retrieval errors.

  The original raw code is preserved in metadata["original_content"]
  so the LLM prompt and the UI always show clean, undecorated code.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_core.documents import Document

from . import config

# Maximum characters of a file's header to prepend to every chunk.
_HEADER_PREVIEW_CHARS = 400


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


def _build_contextual_content(
    chunk: Document,
    file_header: str,
) -> str:
    """
    Wrap a chunk's raw code with file-level context for richer embeddings.

    The resulting string is stored in page_content (what gets embedded).
    The original code lives in metadata["original_content"] for clean
    display in the UI and LLM prompt.

    Format:
        [File: path/to/file.py] [Language: python] [Repo: repo-name]
        [File Header]
        <first N chars of the file>
        ---
        <chunk code>
    """
    source = chunk.metadata.get("source", "")
    lang = chunk.metadata.get("language", "")
    repo = chunk.metadata.get("repository", "")
    raw = chunk.page_content

    tags: list[str] = []
    if source:
        tags.append(f"[File: {source}]")
    if lang:
        tags.append(f"[Language: {lang}]")
    if repo:
        tags.append(f"[Repo: {repo}]")

    lines = " ".join(tags)

    # Only include the header preview when it differs meaningfully from
    # the chunk itself (avoids doubling single-chunk files).
    header_section = ""
    if file_header and file_header.strip()[:100] != raw.strip()[:100]:
        header_section = f"\n[File Header]\n{file_header}\n"

    return f"{lines}{header_section}\n---\n{raw}"


def chunk_documents(documents: list[Document]) -> list[Document]:
    """
    Split a list of Documents into smaller chunks.

    Steps per document:
      1. Language-aware splitting
      2. Metadata enrichment (chunk index, total chunks)
      3. Contextual content wrapping for higher-quality embeddings
    """
    all_chunks: list[Document] = []

    for doc in documents:
        extension = doc.metadata.get("extension", "")
        splitter = _get_splitter(extension)

        chunks = splitter.split_documents([doc])

        # Grab the top of the file as context — trim trailing whitespace
        file_header = doc.page_content[:_HEADER_PREVIEW_CHARS].strip()

        for i, chunk in enumerate(chunks):
            original_content = chunk.page_content

            chunk.metadata.update({
                "chunk_index": i,
                "total_chunks": len(chunks),
                # Preserve raw code for display / prompt use
                "original_content": original_content,
            })

            # Replace page_content with context-enriched version for embedding
            chunk.page_content = _build_contextual_content(chunk, file_header)

            all_chunks.append(chunk)

    return all_chunks
