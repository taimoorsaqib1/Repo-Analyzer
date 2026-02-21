"""
Repository loader — loads code files from a local directory or git URL
into LangChain Document objects with rich metadata.
"""

import os
import stat
import shutil
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from git import Repo as GitRepo

from . import config


def _extract_repo_name(clone_url: str) -> str:
    """Extract repository name from a git clone URL."""
    url = clone_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.split("/")[-1]


def _force_remove_readonly(func, path, _):
    """Error handler for shutil.rmtree — clears read-only flag then retries (needed for .git on Windows)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _should_include(filepath: Path) -> bool:
    """Check if a file should be included based on extension and path."""
    if filepath.suffix.lower() not in config.INCLUDE_EXTENSIONS:
        return False
    for part in filepath.parts:
        if part in config.EXCLUDE_DIRS:
            return False
    return True


def _detect_language(filepath: Path) -> str:
    """Detect programming language from file extension."""
    ext_to_lang = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".tsx": "tsx", ".jsx": "jsx", ".java": "java",
        ".go": "go", ".rs": "rust", ".cpp": "cpp", ".c": "c",
        ".h": "c", ".hpp": "cpp", ".html": "html", ".css": "css",
        ".scss": "scss", ".json": "json", ".yaml": "yaml",
        ".yml": "yaml", ".toml": "toml", ".md": "markdown",
        ".sql": "sql", ".sh": "bash", ".bat": "batch",
        ".ps1": "powershell", ".dart": "dart", ".swift": "swift",
        ".kt": "kotlin", ".rb": "ruby", ".php": "php",
        ".txt": "text",
    }
    return ext_to_lang.get(filepath.suffix.lower(), "unknown")


def load_from_directory(repo_path: str) -> list[Document]:
    """
    Walk a local directory and load all code files as Documents.
    """
    repo_root = Path(repo_path).resolve()
    if not repo_root.is_dir():
        raise FileNotFoundError(f"Directory not found: {repo_root}")

    documents: list[Document] = []

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in config.EXCLUDE_DIRS]

        for filename in files:
            filepath = Path(root) / filename
            relative_path = filepath.relative_to(repo_root)

            if not _should_include(relative_path):
                continue

            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            if not content.strip():
                continue

            if len(content) > 500_000:
                continue

            doc = Document(
                page_content=content,
                metadata={
                    "source": str(relative_path).replace("\\", "/"),
                    "filename": filepath.name,
                    "language": _detect_language(filepath),
                    "extension": filepath.suffix.lower(),
                    "size_bytes": len(content),
                },
            )
            documents.append(doc)

    return documents


def load_from_git(
    clone_url: str,
    branch: str = "main",
    clone_to: Optional[str] = None,
) -> list[Document]:
    """
    Clone a git repository and load it as Documents.
    Each repo is cloned to its own subfolder inside REPO_CLONE_DIR.
    """
    if clone_to is None:
        repo_name = _extract_repo_name(clone_url)
        clone_to = os.path.join(config.REPO_CLONE_DIR, repo_name)

    clone_path = Path(clone_to).resolve()

    if clone_path.exists():
        try:
            existing_repo = GitRepo(clone_path)
            existing_url = existing_repo.remotes.origin.url.rstrip("/")
            if existing_url.endswith(".git"):
                existing_url = existing_url[:-4]
            new_url = clone_url.rstrip("/")
            if new_url.endswith(".git"):
                new_url = new_url[:-4]
            same_repo = existing_url == new_url
        except Exception:
            same_repo = False

        if same_repo:
            existing_repo.remotes.origin.pull()
        else:
            shutil.rmtree(clone_path, onerror=_force_remove_readonly)
            clone_path.parent.mkdir(parents=True, exist_ok=True)
            GitRepo.clone_from(clone_url, clone_path, branch=branch)
    else:
        clone_path.parent.mkdir(parents=True, exist_ok=True)
        GitRepo.clone_from(clone_url, clone_path, branch=branch)

    return load_from_directory(str(clone_path))


def load_from_multiple_git(
    clone_urls: list[str],
    branch: str = "main",
) -> list[Document]:
    """
    Clone multiple git repositories and combine their Documents.
    """
    all_documents: list[Document] = []

    for clone_url in clone_urls:
        docs = load_from_git(clone_url, branch)
        repo_name = _extract_repo_name(clone_url)
        for doc in docs:
            doc.metadata["repository"] = repo_name
        all_documents.extend(docs)

    return all_documents
