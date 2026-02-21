"""
Ingestion script — indexes one or more repositories into ChromaDB.

Usage:
    python ingest.py <repo_path1> [<repo_path2> ...]
    python ingest.py --git <url1> [<url2> ...] [--branch main]
    python ingest.py <repo_path> --force
"""

import sys
import time
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel

from core import config
from core.loader import load_from_directory, load_from_multiple_git
from core.chunker import chunk_documents
from core.vectorstore import create_vectorstore, clear_vectorstore

console = Console()


def ingest_local(repo_paths: list[str], force: bool = False):
    """Index one or more local repositories into the vector store."""
    repo_list = "\n".join(f"  • {p}" for p in repo_paths)

    console.print(
        Panel(
            f"[bold cyan]Indexing:[/]\n{repo_list}\n\n"
            f"[bold cyan]Provider:[/] {config.PROVIDER}\n"
            f"[bold cyan]Embed Model:[/] "
            f"{config.OLLAMA_EMBED_MODEL if config.PROVIDER == 'ollama' else config.OPENAI_EMBED_MODEL}",
            title="🧠 Code Assistant — Ingestion",
            border_style="cyan",
        )
    )

    persist_dir = Path(config.CHROMA_PERSIST_DIR).resolve()
    if persist_dir.exists() and not force:
        console.print(f"\n[yellow]⚠ Vector store already exists at {persist_dir}[/]")
        response = console.input("[bold]Re-index? [y/N]: [/]")
        if response.lower() != "y":
            console.print("[green]✓ Using existing index.[/]")
            return
        clear_vectorstore()
    elif persist_dir.exists() and force:
        clear_vectorstore()
        console.print("[dim]Cleared old index (--force).[/]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:

        task = progress.add_task("📂 Loading repository files...", total=3)
        start = time.time()

        all_documents = []
        for repo_path in repo_paths:
            docs = load_from_directory(repo_path)
            repo_name = Path(repo_path).name
            for doc in docs:
                doc.metadata["repository"] = repo_name
            all_documents.extend(docs)

        progress.update(task, advance=1)
        console.print(
            f"   [green]✓[/] Loaded [bold]{len(all_documents)}[/] files "
            f"from {len(repo_paths)} repo(s) in {time.time() - start:.1f}s"
        )

        progress.update(task, description="✂️  Chunking code...")
        start = time.time()
        chunks = chunk_documents(all_documents)
        progress.update(task, advance=1)
        console.print(f"   [green]✓[/] Created [bold]{len(chunks)}[/] chunks in {time.time() - start:.1f}s")

        progress.update(task, description="🔢 Embedding & storing...")
        start = time.time()
        create_vectorstore(chunks)
        progress.update(task, advance=1)
        console.print(f"   [green]✓[/] Embedded and stored in {time.time() - start:.1f}s")

    languages: dict[str, int] = {}
    for doc in all_documents:
        lang = doc.metadata.get("language", "unknown")
        languages[lang] = languages.get(lang, 0) + 1

    lang_summary = ", ".join(
        f"{lang}: {cnt}" for lang, cnt in sorted(languages.items(), key=lambda x: -x[1])[:8]
    )
    console.print(
        Panel(
            f"[bold green]✓ Indexing complete![/]\n\n"
            f"  Files:     {len(all_documents)}\n"
            f"  Chunks:    {len(chunks)}\n"
            f"  Languages: {lang_summary}\n"
            f"  Stored at: {config.CHROMA_PERSIST_DIR}",
            title="📊 Summary", border_style="green",
        )
    )


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        console.print(
            Panel(
                "[bold]Usage:[/]\n"
                "  python ingest.py <path1> [<path2> ...]        Index local repo(s)\n"
                "  python ingest.py --git <url1> [<url2> ...]    Clone & index git repo(s)\n"
                "  python ingest.py <path> --force               Force re-index\n"
                "  python ingest.py --git <url> --branch <name>  Specify branch\n",
                title="🧠 Code Assistant — Ingestion",
                border_style="cyan",
            )
        )
        return

    force = "--force" in args
    args  = [a for a in args if a != "--force"]

    if args[0] == "--git":
        branch = "main"
        if "--branch" in args:
            idx    = args.index("--branch")
            branch = args[idx + 1] if idx + 1 < len(args) else "main"
            args   = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

        urls = [a for a in args[1:] if a and not a.startswith("--")]
        if not urls:
            console.print("[red]Error: --git requires at least one URL[/]")
            return

        persist_dir = Path(config.CHROMA_PERSIST_DIR).resolve()
        if persist_dir.exists() and not force:
            resp = console.input("\n[yellow]⚠ Vector store exists.[/] Clear and re-index? [Y/n]: ")
            if resp.lower() == "n":
                console.print("[green]✓ Keeping existing index.[/]")
                return
            clear_vectorstore()
        elif persist_dir.exists() and force:
            clear_vectorstore()

        console.print(f"[cyan]Cloning {len(urls)} repo(s) on branch '{branch}'...[/]\n")
        documents = load_from_multiple_git(urls, branch)
        console.print(f"[green]✓ Loaded {len(documents)} files[/]")
        chunks = chunk_documents(documents)
        console.print(f"[green]✓ Created {len(chunks)} chunks[/]")
        create_vectorstore(chunks)
        console.print(f"[bold green]✓ Done! Stored in {config.CHROMA_PERSIST_DIR}[/]")

    else:
        repo_paths = [a for a in args if Path(a).is_dir()]
        for inv in [a for a in args if not Path(a).is_dir()]:
            console.print(f"[yellow]Warning: skipping '{inv}' — not a directory[/]")
        if not repo_paths:
            console.print("[red]Error: no valid directories provided[/]")
            return
        ingest_local(repo_paths, force=force)


if __name__ == "__main__":
    main()
