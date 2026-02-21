"""
Interactive CLI — chat with your codebase using the coding assistant.

Usage:
    python cli.py
"""

import sys
import shutil
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.theme import Theme

from core import config


theme = Theme({
    "info": "cyan", "success": "green", "warning": "yellow",
    "error": "red bold", "user": "bold white",
    "assistant": "bright_white", "source": "dim cyan",
})

console = Console(theme=theme)

BANNER = r"""
   ____          _         _            _     _              _
  / ___|___   __| | ___   / \   ___ ___(_)___| |_ __ _ _ __ | |_
 | |   / _ \ / _` |/ _ \ / _ \ / __/ __| / __| __/ _` | '_ \| __|
 | |__| (_) | (_| |  __// ___ \\__ \__ \ \__ \ || (_| | | | | |_
  \____\___/ \__,_|\___/_/   \_\___/___/_|___/\__\__,_|_| |_|\__|
"""

HELP_TEXT = """
[bold cyan]Commands:[/]
  /help     Show this help message
  /clear    Clear conversation history
  /sources  Show sources from last answer
  /config   Show current configuration
  /quit     Exit the assistant
"""


def cleanup_session():
    console.print("\n[dim]Cleaning up session data...[/]")
    for path_str in (config.CHROMA_PERSIST_DIR, config.REPO_CLONE_DIR):
        p = Path(path_str)
        if p.exists():
            try:
                shutil.rmtree(p)
                console.print(f"  [green]✓[/] Removed {p}")
            except Exception as e:
                console.print(f"  [yellow]⚠[/] Could not remove {p}: {e}")
    console.print("[dim]Session cleanup complete.[/]")


def show_banner():
    provider_info = (
        f"{config.PROVIDER.upper()} — "
        f"{'🔑 ' + config.OPENAI_LLM_MODEL if config.PROVIDER == 'openai' else '🏠 ' + config.OLLAMA_LLM_MODEL}"
    )
    console.print(
        Panel(
            f"[bold cyan]{BANNER}[/]\n"
            f"  [dim]Provider: {provider_info}[/]\n"
            f"  [dim]Type /help for commands, /quit to exit[/]",
            border_style="cyan", padding=(0, 2),
        )
    )


def main():
    show_banner()

    try:
        from core.assistant import CodingAssistant
    except Exception as e:
        console.print(f"[error]Failed to initialize assistant: {e}[/]")
        console.print("[warning]Index a repo first: python ingest.py --git <url>[/]")
        return

    try:
        assistant = CodingAssistant()
    except FileNotFoundError as e:
        console.print(f"[error]{e}[/]")
        console.print(
            "\n[warning]Index a repository first:[/]\n"
            "  python ingest.py --git <url>\n"
            "  python ingest.py --git <url1> <url2> ...\n"
        )
        return
    except Exception as e:
        console.print(f"[error]Failed to initialize: {e}[/]")
        return

    last_sources = []
    console.print("\n[success]✓ Assistant ready! Ask me anything about your code.[/]\n")

    while True:
        try:
            question = console.input("[bold cyan]You ❯ [/]").strip()
        except (KeyboardInterrupt, EOFError):
            cleanup_session()
            console.print("\n[dim]Goodbye! 👋[/]")
            break

        if not question:
            continue

        if question.startswith("/"):
            cmd = question.lower().split()[0]

            if cmd in ("/quit", "/exit", "/q"):
                cleanup_session()
                console.print("[dim]Goodbye! 👋[/]")
                break

            elif cmd in ("/help", "/h"):
                console.print(HELP_TEXT)

            elif cmd == "/clear":
                assistant.clear_history()
                console.print("[success]✓ Conversation history cleared.[/]\n")

            elif cmd == "/sources":
                if last_sources:
                    console.print("\n[bold]📄 Sources from last answer:[/]")
                    for src in last_sources:
                        console.print(f"  [source]• {src}[/]")
                    console.print()
                else:
                    console.print("[warning]No sources yet — ask a question first.[/]\n")

            elif cmd == "/config":
                console.print(
                    Panel(
                        f"Provider:     {config.PROVIDER}\n"
                        f"LLM Model:    {config.OLLAMA_LLM_MODEL if config.PROVIDER == 'ollama' else config.OPENAI_LLM_MODEL}\n"
                        f"Embed Model:  {config.OLLAMA_EMBED_MODEL if config.PROVIDER == 'ollama' else config.OPENAI_EMBED_MODEL}\n"
                        f"Vector Store: {config.CHROMA_PERSIST_DIR}\n"
                        f"Repos Dir:    {config.REPO_CLONE_DIR}\n"
                        f"Retriever K:  {config.RETRIEVER_K}\n"
                        f"Chunk Size:   {config.CHUNK_SIZE}",
                        title="⚙️  Configuration", border_style="cyan",
                    )
                )
            else:
                console.print(f"[warning]Unknown command: {cmd}. Type /help[/]\n")
            continue

        console.print()
        with console.status("[cyan]Thinking...[/]", spinner="dots"):
            try:
                answer, docs = assistant.ask(question)
                last_sources = assistant.get_sources(docs)
            except Exception as e:
                console.print(f"[error]Error: {e}[/]\n")
                continue

        console.print(
            Panel(
                Markdown(answer),
                title="🤖 Assistant",
                border_style="bright_white",
                padding=(1, 2),
            )
        )

        if last_sources:
            source_text = " │ ".join(last_sources[:4])
            if len(last_sources) > 4:
                source_text += f" │ +{len(last_sources) - 4} more"
            console.print(f"  [source]📄 Sources: {source_text}[/]\n")


if __name__ == "__main__":
    main()
