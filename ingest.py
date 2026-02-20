"""
Ingestion script — indexes a repository into the ChromaDB vector store.

Usage:
    python ingest.py <repo_path>
    python ingest.py --git <clone_url> [--branch main]
"""

import sys
import time
import shutil
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel

import config
from loader import load_from_directory, load_from_git
from chunker import chunk_documents
from vectorstore import create_vectorstore

console = Console()


def ingest_local(repo_path: str, force: bool = False):
    """Index a local repository into the vector store."""

    console.print(
        Panel(
            f"[bold cyan]Indexing:[/] {repo_path}\n"
            f"[bold cyan]Provider:[/] {config.PROVIDER}\n"
            f"[bold cyan]Embed Model:[/] "
            f"{config.OLLAMA_EMBED_MODEL if config.PROVIDER == 'ollama' else config.OPENAI_EMBED_MODEL}",
            title="🧠 Code Assistant — Ingestion",
            border_style="cyan",
        )
    )

    # Check for existing vector store
    persist_dir = Path(config.CHROMA_PERSIST_DIR).resolve()
    if persist_dir.exists() and not force:
        console.print(
            f"\n[yellow]⚠ Vector store already exists at {persist_dir}[/]"
        )
        console.print("[yellow]  Use --force to re-index, or just run cli.py[/]\n")
        response = console.input("[bold]Re-index? [y/N]: [/]")
        if response.lower() != "y":
            console.print("[green]✓ Using existing index.[/]")
            return
        shutil.rmtree(persist_dir)
        console.print("[dim]Cleared old index.[/]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:

        # Step 1: Load files
        task = progress.add_task("📂 Loading repository files...", total=3)
        start = time.time()
        documents = load_from_directory(repo_path)
        progress.update(task, advance=1)
        console.print(
            f"   [green]✓[/] Loaded [bold]{len(documents)}[/] files "
            f"in {time.time() - start:.1f}s"
        )

        # Step 2: Chunk
        progress.update(task, description="✂️  Chunking code...")
        start = time.time()
        chunks = chunk_documents(documents)
        progress.update(task, advance=1)
        console.print(
            f"   [green]✓[/] Created [bold]{len(chunks)}[/] chunks "
            f"in {time.time() - start:.1f}s"
        )

        # Step 3: Embed & store
        progress.update(task, description="🔢 Embedding & storing...")
        start = time.time()
        create_vectorstore(chunks)
        progress.update(task, advance=1)
        console.print(
            f"   [green]✓[/] Embedded and stored "
            f"in {time.time() - start:.1f}s"
        )

    # Summary
    languages = {}
    for doc in documents:
        lang = doc.metadata.get("language", "unknown")
        languages[lang] = languages.get(lang, 0) + 1

    lang_summary = ", ".join(
        f"{lang}: {count}" for lang, count in sorted(
            languages.items(), key=lambda x: -x[1]
        )[:8]
    )

    console.print(
        Panel(
            f"[bold green]✓ Indexing complete![/]\n\n"
            f"  Files: {len(documents)}\n"
            f"  Chunks: {len(chunks)}\n"
            f"  Languages: {lang_summary}\n"
            f"  Stored at: {config.CHROMA_PERSIST_DIR}",
            title="📊 Summary",
            border_style="green",
        )
    )


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        console.print(
            Panel(
                "[bold]Usage:[/]\n"
                "  python ingest.py <repo_path>          Index a local repository\n"
                "  python ingest.py --git <url>           Clone & index a git repo\n"
                "  python ingest.py <repo_path> --force   Force re-index\n",
                title="🧠 Code Assistant — Ingestion",
                border_style="cyan",
            )
        )
        return

    force = "--force" in args
    args = [a for a in args if a != "--force"]

    if args[0] == "--git":
        if len(args) < 2:
            console.print("[red]Error: --git requires a URL[/]")
            return
        url = args[1]
        branch = args[3] if len(args) > 3 and args[2] == "--branch" else "main"
        console.print(f"[cyan]Cloning {url} (branch: {branch})...[/]")
        documents = load_from_git(url, branch)
        chunks = chunk_documents(documents)
        create_vectorstore(chunks)
        console.print("[green]✓ Done![/]")
    else:
        repo_path = args[0]
        if not Path(repo_path).is_dir():
            console.print(f"[red]Error: '{repo_path}' is not a directory[/]")
            return
        ingest_local(repo_path, force=force)


if __name__ == "__main__":
    main()
