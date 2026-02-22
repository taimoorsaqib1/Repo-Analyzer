"""
FastAPI web server for Repo Analyzer — Phase 2 edition.

New in Phase 2:
  • Workspace persistence  — save / load / delete named sessions (SQLite)
  • File tree API          — browse indexed repo file structures
  • File content API       — read any indexed file (for code viewer)
  • Chat history clear     — reset conversation without re-indexing
  • Per-session ChromaDB   — each ingest gets a unique collection name

Run with:
    python web/server.py
    uvicorn web.server:app --reload   (from project root)
"""

import json
import shutil
import asyncio
import uuid
import sys
from pathlib import Path
from typing import AsyncGenerator, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

# ── Project root on sys.path ─────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.loader import load_from_git, _extract_repo_name
from core.chunker import chunk_documents
from core.vectorstore import create_vectorstore, clear_vectorstore
from core.assistant import CodingAssistant
from core import config
from core import workspace as ws_store

# ── App & Static Files ───────────────────────────────────────────────────────
app = FastAPI(title="Repo Analyzer")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Session State ─────────────────────────────────────────────────────────────
session: dict = {
    "repos":      [],    # list of repo metadata dicts
    "assistant":  None,  # CodingAssistant instance after indexing
    "collection": None,  # active ChromaDB collection name (unique per ingest)
}


# ── Request Models ────────────────────────────────────────────────────────────
class IngestRequest(BaseModel):
    urls:   list[str]
    branch: str = "main"

class ChatRequest(BaseModel):
    question: str

class SaveWorkspaceRequest(BaseModel):
    name: str

class LoadWorkspaceRequest(BaseModel):
    name: str


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/repos")
def get_repos():
    return {
        "repos":   session["repos"],
        "indexed": len(session["repos"]) > 0,
    }


# ── Ingest ────────────────────────────────────────────────────────────────────
@app.post("/api/ingest")
async def ingest(req: IngestRequest):
    """Clone + index repos — streams SSE progress events."""

    async def event_stream() -> AsyncGenerator[str, None]:
        def send(event_type: str, **data) -> str:
            return f"data: {json.dumps({'type': event_type, **data})}\n\n"

        try:
            # Give this ingest its own isolated ChromaDB collection
            collection_name = f"ws_{uuid.uuid4().hex[:12]}"

            # Clear only the previous session collection, not saved workspaces
            if session.get("collection"):
                await asyncio.to_thread(clear_vectorstore, session["collection"])

            session["repos"]      = []
            session["assistant"]  = None
            session["collection"] = collection_name

            all_documents = []

            for url in req.urls:
                repo_name = _extract_repo_name(url)
                yield send("progress", message=f"⬇ Cloning {repo_name}…")
                await asyncio.sleep(0)

                docs = await asyncio.to_thread(load_from_git, url, req.branch)
                for doc in docs:
                    doc.metadata["repository"] = repo_name
                all_documents.extend(docs)

                langs: dict[str, int] = {}
                for doc in docs:
                    lang = doc.metadata.get("language", "unknown")
                    langs[lang] = langs.get(lang, 0) + 1
                top_langs = dict(sorted(langs.items(), key=lambda x: -x[1])[:6])

                session["repos"].append({
                    "name":       repo_name,
                    "url":        url,
                    "file_count": len(docs),
                    "languages":  top_langs,
                    "summary":    None,
                })

                yield send("progress", message=f"✔ Loaded {len(docs)} files from {repo_name}")
                await asyncio.sleep(0)

            yield send("progress", message=f"✂ Chunking {len(all_documents)} files…")
            await asyncio.sleep(0)
            chunks = await asyncio.to_thread(chunk_documents, all_documents)
            yield send("progress", message=f"✔ Created {len(chunks)} chunks")
            await asyncio.sleep(0)

            yield send("progress", message="🔢 Embedding & storing in vector database…")
            await asyncio.sleep(0)
            await asyncio.to_thread(create_vectorstore, chunks, collection_name)
            yield send("progress", message="✔ Vector database ready")
            await asyncio.sleep(0)

            session["assistant"] = CodingAssistant(collection_name)

            for i, repo_meta in enumerate(session["repos"]):
                yield send("progress", message=f"🧠 Summarising {repo_meta['name']}…")
                await asyncio.sleep(0)
                summary = await asyncio.to_thread(
                    _generate_summary, repo_meta["name"], session["assistant"]
                )
                session["repos"][i]["summary"] = summary

            yield send("done", repos=session["repos"])

        except Exception as e:
            yield send("error", message=str(e))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _generate_summary(repo_name: str, assistant: CodingAssistant) -> dict:
    """Ask the LLM to produce a structured JSON summary of the repo."""
    prompt = (
        f'Analyse the repository "{repo_name}" from the code you have access to.\n'
        "Respond with ONLY a JSON object — no markdown, no explanation — exactly:\n"
        "{\n"
        '  "overview": "2-3 sentence description",\n'
        '  "purpose": "One sentence: problem + who it is for",\n'
        '  "key_features": ["feature 1", "feature 2", "feature 3", "feature 4", "feature 5"],\n'
        '  "use_cases": ["use case 1", "use case 2", "use case 3"],\n'
        '  "tech_stack": ["tech 1", "tech 2", "tech 3"],\n'
        '  "external_dependencies": ["Redis", "PostgreSQL"],\n'
        '  "entry_points": ["filename.py — description"],\n'
        '  "architecture": "Brief structural description",\n'
        '  "getting_started": "Brief install/run instructions",\n'
        '  "limitations": ["caveat 1", "caveat 2"]\n'
        "}"
    )
    try:
        answer, _ = assistant.ask(prompt)
        answer = answer.strip()
        if "```" in answer:
            for part in answer.split("```"):
                part = part.strip()
                if part.startswith("{"):
                    answer = part; break
                if part.startswith("json"):
                    answer = part[4:].strip(); break
        return json.loads(answer)
    except Exception:
        return {
            "overview": f"{repo_name} has been indexed.",
            "purpose": "Use the chat to learn more.",
            "key_features": ["Use the chat to explore features"],
            "use_cases": [], "tech_stack": [], "external_dependencies": [],
            "entry_points": [], "architecture": "Use the chat to explore architecture",
            "getting_started": "Use the chat for setup instructions", "limitations": [],
        }


# ── Chat ──────────────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Stream chat tokens as SSE events."""
    if not session["assistant"]:
        raise HTTPException(status_code=400, detail="No repositories indexed yet.")

    async def stream_response() -> AsyncGenerator[str, None]:
        try:
            gen  = session["assistant"].stream_ask(req.question)
            docs = None
            for item in gen:
                if isinstance(item, str):
                    yield f"data: {json.dumps({'type': 'token', 'content': item})}\n\n"
                    await asyncio.sleep(0)
                else:
                    docs = item
            sources = session["assistant"].get_sources(docs) if docs else []
            yield f"data: {json.dumps({'type': 'done', 'sources': sources})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat/clear")
def clear_chat_history():
    """Reset conversation history without re-indexing."""
    if session["assistant"]:
        session["assistant"].clear_history()
    return {"success": True}


# ── Workspace Management ──────────────────────────────────────────────────────
@app.get("/api/workspaces")
def list_workspaces():
    return {"workspaces": ws_store.list_workspaces()}


@app.post("/api/workspaces/save")
def save_workspace(req: SaveWorkspaceRequest):
    """Persist the current session under a user-specified name."""
    if not session["repos"]:
        raise HTTPException(status_code=400, detail="Nothing indexed to save.")
    if not session.get("collection"):
        raise HTTPException(status_code=400, detail="No active collection.")
    ws_store.save_workspace(req.name, session["repos"], session["collection"])
    return {"success": True, "name": req.name}


@app.post("/api/workspaces/load")
def load_workspace(req: LoadWorkspaceRequest):
    """Restore a saved workspace — zero re-cloning needed."""
    record = ws_store.load_workspace(req.name)
    if not record:
        raise HTTPException(status_code=404, detail=f"Workspace '{req.name}' not found.")
    try:
        session["repos"]      = record["repos"]
        session["collection"] = record["collection"]
        session["assistant"]  = CodingAssistant(record["collection"])
        return {"success": True, "repos": record["repos"]}
    except FileNotFoundError:
        raise HTTPException(
            status_code=409,
            detail="Vector database for this workspace is missing. Re-index it.",
        )


@app.delete("/api/workspaces/{name}")
def delete_workspace(name: str):
    """Delete a workspace and its ChromaDB collection."""
    record = ws_store.load_workspace(name)
    if not record:
        raise HTTPException(status_code=404, detail=f"Workspace '{name}' not found.")
    clear_vectorstore(record["collection"])
    ws_store.delete_workspace(name)
    return {"success": True}


# ── File Explorer ─────────────────────────────────────────────────────────────
def _build_tree(root: Path, base: Path, exclude: set[str]) -> dict:
    """Recursively build a JSON-serialisable file-tree dict."""
    node: dict = {
        "name": root.name,
        "path": str(root.relative_to(base)).replace("\\", "/"),
    }
    if root.is_dir():
        node["type"] = "dir"
        children = []
        for child in sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if child.name in exclude or child.name.startswith("."):
                continue
            children.append(_build_tree(child, base, exclude))
        node["children"] = children
    else:
        node["type"] = "file"
        node["ext"]  = root.suffix.lower()
    return node


@app.get("/api/files")
def get_files(repo: Optional[str] = None):
    """Return the file tree for indexed repos (optionally filtered by ?repo=name)."""
    clone_root = Path(config.REPO_CLONE_DIR).resolve()
    if not clone_root.exists():
        return {"trees": []}

    targets = (
        [clone_root / repo]
        if repo
        else [p for p in clone_root.iterdir() if p.is_dir()]
    )
    trees = [
        _build_tree(d, clone_root, config.EXCLUDE_DIRS)
        for d in targets if d.exists()
    ]
    return {"trees": trees}


@app.get("/api/file")
def get_file_content(path: str):
    """
    Return raw text of a file inside the clone directory.
    Path is relative to REPO_CLONE_DIR; path traversal is blocked.
    """
    clone_root = Path(config.REPO_CLONE_DIR).resolve()
    target     = (clone_root / path.lstrip("/")).resolve()

    if not str(target).startswith(str(clone_root)):
        raise HTTPException(status_code=403, detail="Access denied.")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
        ".go": "go", ".rs": "rust", ".cpp": "cpp", ".c": "c",
        ".h": "cpp", ".rb": "ruby", ".php": "php", ".swift": "swift",
        ".html": "html", ".css": "css", ".json": "json",
        ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
        ".md": "markdown", ".sh": "bash", ".sql": "sql",
    }
    return {
        "content":  content,
        "language": ext_map.get(target.suffix.lower(), "plaintext"),
        "path":     path,
    }


# ── Clear Session ─────────────────────────────────────────────────────────────
@app.post("/api/clear")
def clear_session():
    """Delete the active vector collection, cloned repos, and reset state."""
    try:
        if session.get("collection"):
            clear_vectorstore(session["collection"])
        repo_clone_dir = Path(config.REPO_CLONE_DIR)
        if repo_clone_dir.exists():
            shutil.rmtree(repo_clone_dir)
        session["repos"]      = []
        session["assistant"]  = None
        session["collection"] = None
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        app_dir=str(Path(__file__).parent),
    )

