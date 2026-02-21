"""
FastAPI web server for the Code Assistant.

Run with:
    python web/server.py
    or
    uvicorn web.server:app --reload  (from project root)
"""

import json
import shutil
import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

# Add project root to sys.path so core.* imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.loader import load_from_git, _extract_repo_name
from core.chunker import chunk_documents
from core.vectorstore import create_vectorstore, clear_vectorstore
from core.assistant import CodingAssistant
from core import config

# ── App & Static Files ───────────────────────────────────────────────────────
app = FastAPI(title="Code Assistant")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Session State ─────────────────────────────────────────────────────────────
session: dict = {
    "repos": [],        # list of repo metadata dicts
    "assistant": None,  # CodingAssistant instance after indexing
}


# ── Request Models ────────────────────────────────────────────────────────────
class IngestRequest(BaseModel):
    urls: list[str]
    branch: str = "main"


class ChatRequest(BaseModel):
    question: str


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/repos")
def get_repos():
    return {
        "repos": session["repos"],
        "indexed": len(session["repos"]) > 0,
    }


@app.post("/api/ingest")
async def ingest(req: IngestRequest):
    """
    Clone + index repos. Streams Server-Sent Events (SSE) with progress.
    Final event includes repo summaries.
    """

    async def event_stream() -> AsyncGenerator[str, None]:
        def send(event_type: str, **data) -> str:
            return f"data: {json.dumps({'type': event_type, **data})}\n\n"

        try:
            # Reset session
            clear_vectorstore()
            session["repos"] = []
            session["assistant"] = None

            all_documents = []

            for url in req.urls:
                repo_name = _extract_repo_name(url)
                yield send("progress", message=f"⬇ Cloning {repo_name}...")
                await asyncio.sleep(0)  # yield control

                docs = await asyncio.to_thread(load_from_git, url, req.branch)

                # Tag every doc with its repo name
                for doc in docs:
                    doc.metadata["repository"] = repo_name

                all_documents.extend(docs)

                # Compute language breakdown
                langs: dict[str, int] = {}
                for doc in docs:
                    lang = doc.metadata.get("language", "unknown")
                    langs[lang] = langs.get(lang, 0) + 1
                top_langs = dict(sorted(langs.items(), key=lambda x: -x[1])[:6])

                session["repos"].append({
                    "name": repo_name,
                    "url": url,
                    "file_count": len(docs),
                    "languages": top_langs,
                    "summary": None,
                })

                yield send("progress", message=f"✔ Loaded {len(docs)} files from {repo_name}")
                await asyncio.sleep(0)

            yield send("progress", message=f"✂ Chunking {len(all_documents)} files...")
            await asyncio.sleep(0)
            chunks = await asyncio.to_thread(chunk_documents, all_documents)
            yield send("progress", message=f"✔ Created {len(chunks)} chunks")
            await asyncio.sleep(0)

            yield send("progress", message="🔢 Embedding & storing in vector database...")
            await asyncio.sleep(0)
            await asyncio.to_thread(create_vectorstore, chunks)
            yield send("progress", message="✔ Vector database ready")
            await asyncio.sleep(0)

            # Initialise assistant
            session["assistant"] = CodingAssistant()

            # Generate a summary per repo
            for i, repo_meta in enumerate(session["repos"]):
                yield send("progress", message=f"🧠 Summarising {repo_meta['name']}...")
                await asyncio.sleep(0)
                summary = await asyncio.to_thread(_generate_summary, repo_meta["name"], session["assistant"])
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
        "Respond with ONLY a JSON object — no markdown, no explanation — using exactly this structure:\n"
        "{\n"
        '  "overview": "2-3 sentence description of what this project does",\n'
        '  "purpose": "One sentence: what problem does this solve and for whom?",\n'
        '  "key_features": ["feature 1", "feature 2", "feature 3", "feature 4", "feature 5"],\n'
        '  "use_cases": ["use case 1", "use case 2", "use case 3"],\n'
        '  "tech_stack": ["tech 1", "tech 2", "tech 3"],\n'
        '  "external_dependencies": ["e.g. Redis", "PostgreSQL", "Stripe API"],\n'
        '  "entry_points": ["filename.py — what it does", "another.py — what it does"],\n'
        '  "architecture": "Brief description of how the project is structured",\n'
        '  "getting_started": "Brief description of how to install and run the project",\n'
        '  "limitations": ["known limitation or caveat 1", "limitation 2"]\n'
        "}"
    )

    try:
        answer, _ = assistant.ask(prompt)
        answer = answer.strip()
        # Strip markdown fences if the model adds them
        if "```" in answer:
            parts = answer.split("```")
            for part in parts:
                if part.strip().startswith("{"):
                    answer = part.strip()
                    break
                if part.startswith("json"):
                    answer = part[4:].strip()
                    break
        return json.loads(answer)
    except Exception:
        return {
            "overview": f"{repo_name} has been indexed. Ask the assistant anything about it.",
            "purpose": "Use the chat to learn more.",
            "key_features": ["Use the chat to explore features"],
            "use_cases": [],
            "tech_stack": [],
            "external_dependencies": [],
            "entry_points": [],
            "architecture": "Use the chat to explore the architecture",
            "getting_started": "Use the chat to explore setup instructions",
            "limitations": [],
        }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Stream chat tokens as SSE events (real LLM streaming)."""
    if not session["assistant"]:
        raise HTTPException(status_code=400, detail="No repositories indexed yet.")

    async def stream_response() -> AsyncGenerator[str, None]:
        try:
            gen = session["assistant"].stream_ask(req.question)
            docs = None

            for item in gen:
                if isinstance(item, str):
                    yield f"data: {json.dumps({'type': 'token', 'content': item})}\n\n"
                    await asyncio.sleep(0)
                else:
                    # Last yield is the docs list
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


@app.post("/api/clear")
def clear_session():
    """Delete vector store + cloned repos, reset session."""
    try:
        clear_vectorstore()
        repo_clone_dir = Path(config.REPO_CLONE_DIR)
        if repo_clone_dir.exists():
            shutil.rmtree(repo_clone_dir)

        session["repos"] = []
        session["assistant"] = None
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False, app_dir=str(Path(__file__).parent))
