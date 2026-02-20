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

import config


def _force_remove_readonly(func, path, _):
    """Error handler for shutil.rmtree — clears read-only flag then retries (needed for .git on Windows)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _should_include(filepath: Path) -> bool:
    """Check if a file should be included based on extension and path."""
    # Check extension
    if filepath.suffix.lower() not in config.INCLUDE_EXTENSIONS:
        return False

    # Check excluded directories
    parts = filepath.parts
    for part in parts:
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

    Args:
        repo_path: Path to the local repository.

    Returns:
        List of LangChain Document objects with metadata.
    """
    repo_root = Path(repo_path).resolve()
    if not repo_root.is_dir():
        raise FileNotFoundError(f"Directory not found: {repo_root}")

    documents: list[Document] = []
    skipped = 0

    for root, dirs, files in os.walk(repo_root):
        # Prune excluded directories in-place
        dirs[:] = [d for d in dirs if d not in config.EXCLUDE_DIRS]

        for filename in files:
            filepath = Path(root) / filename
            relative_path = filepath.relative_to(repo_root)

            if not _should_include(relative_path):
                skipped += 1
                continue

            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                skipped += 1
                continue

            # Skip empty files
            if not content.strip():
                skipped += 1
                continue

            # Skip very large files (>500KB)
            if len(content) > 500_000:
                skipped += 1
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
    clone_to: str = "./repo_clone",
) -> list[Document]:
    """
    Clone a git repository and load it as Documents.

    Args:
        clone_url: Git clone URL.
        branch: Branch to checkout.
        clone_to: Local path to clone into.

    Returns:
        List of LangChain Document objects.
    """
    clone_path = Path(clone_to).resolve()

    if clone_path.exists():
        # Check if the existing clone is the same repo
        try:
            existing_repo = GitRepo(clone_path)
            existing_url = existing_repo.remotes.origin.url.rstrip("/").rstrip(".git")
            new_url = clone_url.rstrip("/").rstrip(".git")
            same_repo = existing_url == new_url
        except Exception:
            same_repo = False

        if same_repo:
            # Same repo — just pull latest
            existing_repo.remotes.origin.pull()
        else:
            # Different repo — wipe and re-clone
            shutil.rmtree(clone_path, onerror=_force_remove_readonly)
            GitRepo.clone_from(clone_url, clone_path, branch=branch)
    else:
        GitRepo.clone_from(clone_url, clone_path, branch=branch)

    return load_from_directory(str(clone_path))
