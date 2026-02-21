"""
Centralized configuration — reads .env and exposes typed settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (one level above core/)
load_dotenv(Path(__file__).parent.parent / ".env")

# ── Provider ──────────────────────────────────────────────
PROVIDER: str = os.getenv("PROVIDER", "ollama").lower()

# ── OpenAI ────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBED_MODEL: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
OPENAI_LLM_MODEL: str = os.getenv("OPENAI_LLM_MODEL", "gpt-4")

# ── Ollama ────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL: str = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5-coder:7b")

# ── ChromaDB ──────────────────────────────────────────────
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "codebase")

# ── Repository Cloning ────────────────────────────────────
REPO_CLONE_DIR: str = os.getenv("REPO_CLONE_DIR", "./data/repo_clone")

# ── Chunking ─────────────────────────────────────────────
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1500"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

# ── File Filters ──────────────────────────────────────────
INCLUDE_EXTENSIONS: set[str] = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".rs", ".cpp", ".c", ".h", ".hpp",
    ".html", ".css", ".scss",
    ".json", ".yaml", ".yml", ".toml",
    ".md", ".txt",
    ".sql", ".sh", ".bat", ".ps1",
    ".dart", ".swift", ".kt", ".rb", ".php",
}

EXCLUDE_DIRS: set[str] = {
    ".git", "__pycache__", "node_modules", "venv", ".venv",
    "env", ".env", "dist", "build", ".next", ".nuxt",
    "target", "bin", "obj", ".idea", ".vscode",
    "chroma_db", ".chroma", "egg-info",
}

# ── Retriever ─────────────────────────────────────────────
RETRIEVER_K: int = int(os.getenv("RETRIEVER_K", "6"))
RETRIEVER_SEARCH_TYPE: str = "mmr"
