# Repo Analyzer — AI Coding Assistant

An AI-powered coding assistant that lets you **chat with any GitHub repository** using Retrieval-Augmented Generation (RAG). Add one or more repo URLs and it clones, indexes, and analyses them — then lets you ask questions through a **web UI** or a **terminal CLI**.

---

## Features

### Core
- **Multi-repo support** — analyze several repositories in a single session
- **Dual provider** — use **OpenAI** or a **local Ollama** model (fully offline)
- **Language-aware chunking** — code split at function/class boundaries with contextual headers
- **Real-time streaming** — tokens stream in both the web app and the CLI
- **Conversation memory** — multi-turn questions with full history
- **Source file references** — every answer links to the exact files used
- Supports 25+ file types: Python, JS/TS, Go, Rust, Java, C/C++, HTML, CSS, SQL, and more

### Phase 1 — Retrieval Quality
- **Hybrid Search (BM25 + MMR + RRF)** — keyword and semantic search merged via Reciprocal Rank Fusion
- **Contextual Retrieval** — each chunk prefixed with a file-level context header for better embedding quality
- **Cross-encoder Re-ranking** — top results re-scored by `BAAI/bge-reranker-base` before passing to the LLM

### Phase 2 — UI & Persistence
- **3-tab Web App** — Overview · Explorer · Chat
- **Workspace persistence** — save and reload named sessions (repos + vector collection) from a local SQLite registry
- **File Explorer** — browse the indexed file tree of any ingested repo
- **Code Viewer** — click any file to read it with syntax highlighting (50+ languages via highlight.js)
- **Markdown chat** — answers rendered as formatted Markdown with code blocks
- **Source chips** — clickable file references jump straight to the Code Viewer
- **Auto-generated repo summaries** — purpose, features, use cases, tech stack, architecture, entry points, getting started, and limitations

---

## Project Structure

```
Repo-Analyzer/
├── core/                   # All RAG logic (importable package)
│   ├── assistant.py        # RAG chain — retriever + cross-encoder re-ranker + LLM + streaming
│   ├── chunker.py          # Language-aware code splitter with contextual headers
│   ├── config.py           # Centralized config (reads .env)
│   ├── embeddings.py       # Embedding model factory (OpenAI / Ollama)
│   ├── llm.py              # LLM factory (OpenAI / Ollama)
│   ├── loader.py           # File loader + multi-repo Git clone helper
│   ├── retriever.py        # Hybrid BM25 + MMR retriever with Reciprocal Rank Fusion
│   ├── vectorstore.py      # ChromaDB create / load / clear helpers (named collections)
│   └── workspace.py        # SQLite workspace registry (save / load / list / delete)
├── web/                    # Web application
│   ├── server.py           # FastAPI backend — ingest, chat, workspaces, file tree, file content
│   └── static/
│       ├── index.html      # 3-tab SPA (Overview / Explorer / Chat)
│       ├── style.css       # Dark design system (~1000 lines)
│       └── app.js          # Frontend logic — workspaces, file tree, code viewer, markdown chat
├── data/                   # Runtime data (auto-created, git-ignored)
│   ├── chroma_db/          # Vector database (per-session UUID collections)
│   ├── repo_clone/         # Cloned repos
│   └── workspaces.db       # SQLite workspace registry
├── cli.py                  # Terminal chat interface
├── ingest.py               # Ingestion CLI (local paths or Git URLs)
├── requirements.txt
└── .env                    # Your config (copy from .env.example)
```

---

## Quick Start

### 1. Clone this repo

```bash
git clone https://github.com/taimoorsaqib1/Repo-Analyzer.git
cd Repo-Analyzer
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file in the project root:

```env
PROVIDER=ollama
OLLAMA_LLM_MODEL=qwen2.5-coder:7b
OLLAMA_EMBED_MODEL=nomic-embed-text
```

---

## Option A — Web App (Recommended)

```bash
python web/server.py
```

Open **http://localhost:8000** in your browser.

### Overview Tab
1. Paste one or more GitHub repo URLs in the sidebar
2. Set the branch (default: `main`) and click **Analyze Repos**
3. The app clones, indexes, and generates rich overview cards with purpose, features, tech stack, architecture, entry points, and more

### Explorer Tab
- Browse the full file tree of every indexed repo
- Click any file to open it in the **Code Viewer** panel with syntax highlighting

### Chat Tab
- Ask natural-language questions about the code
- Answers are fully Markdown-rendered with code blocks and syntax highlighting
- Source chips below each answer are clickable — they open the referenced file in the Code Viewer

### Workspaces
- Click **Save Session** to persist the current repos and vector collection under a name
- Saved workspaces appear in the sidebar — click to reload any previous session instantly
- Workspaces are stored in `data/workspaces.db` (SQLite, local)

---

## Option B — Terminal CLI

### Index repositories

```bash
# Single remote repo
python ingest.py --git https://github.com/owner/repo

# Multiple remote repos
python ingest.py --git https://github.com/user/repo1 https://github.com/user/repo2

# Specific branch
python ingest.py --git https://github.com/owner/repo --branch develop

# Local folders
python ingest.py /path/to/repo1 /path/to/repo2

# Force re-index
python ingest.py --git https://github.com/owner/repo --force
```

### Chat

```bash
python cli.py
```

#### CLI Commands

| Command | Description |
|---|---|
| `/help` | Show available commands |
| `/clear` | Clear conversation history |
| `/sources` | Show source files from the last answer |
| `/config` | Show current configuration |
| `/quit` | Exit and clean up session data |

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PROVIDER` | `ollama` | `openai` or `ollama` |
| `OPENAI_API_KEY` | — | Your OpenAI API key |
| `OPENAI_EMBED_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `OPENAI_LLM_MODEL` | `gpt-4` | OpenAI chat model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `OLLAMA_LLM_MODEL` | `qwen2.5-coder:7b` | Ollama chat model |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | Vector database location |
| `REPO_CLONE_DIR` | `./data/repo_clone` | Cloned repos location |
| `CHUNK_SIZE` | `1500` | Tokens per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `RETRIEVER_K` | `6` | Chunks retrieved per query |

### Using Ollama (local, free, offline)

```bash
# Install Ollama from https://ollama.com, then:
ollama pull qwen2.5-coder:7b   # LLM (recommended for 6 GB+ VRAM)
ollama pull nomic-embed-text   # Embeddings
```

Set `PROVIDER=ollama` in `.env`.

### Using OpenAI

Set `PROVIDER=openai` and `OPENAI_API_KEY=sk-...` in `.env`.

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) *(if using local models)*
- OpenAI API key *(if using OpenAI)*

Key Python packages (see `requirements.txt` for full list):

| Package | Purpose |
|---|---|
| `langchain` / `langchain-community` | RAG chain, document loaders |
| `langchain-ollama` | Ollama LLM + embeddings integration |
| `langchain-openai` | OpenAI LLM + embeddings integration |
| `langchain-chroma` | ChromaDB vector store integration |
| `chromadb` | Persistent vector database |
| `rank_bm25` | BM25 keyword retriever (Phase 1) |
| `sentence-transformers` | Cross-encoder re-ranker — `BAAI/bge-reranker-base` (Phase 1) |
| `fastapi` + `uvicorn` | Web server |
| `gitpython` | Git clone support |

---

## License

MIT

- **Web App** — modern dark UI with repo overview cards and streaming chat
- **Auto-generated repo summaries** — purpose, features, use cases, tech stack, architecture, entry points, getting started, and limitations
- **Interactive CLI** — full-featured terminal chat with rich formatting
- **Dual provider** — use **OpenAI** or a **local Ollama** model (fully offline)
- **Language-aware chunking** — code split at function/class boundaries
- **Real-time streaming** — tokens stream in the web app and CLI
- **Session cleanup** — ChromaDB and cloned repos wiped automatically on exit
- Supports 25+ file types: Python, JS/TS, Go, Rust, Java, C/C++, HTML, CSS, SQL, and more
- Conversation memory across multi-turn questions
- Source file references shown for every answer

---

## Project Structure

```
Repo-Analyzer/
├── core/                   # All RAG logic (importable package)
│   ├── assistant.py        # RAG chain — retriever + LLM + prompt + streaming
│   ├── chunker.py          # Language-aware code splitter
│   ├── config.py           # Centralized config (reads .env)
│   ├── embeddings.py       # Embedding model factory (OpenAI / Ollama)
│   ├── llm.py              # LLM factory (OpenAI / Ollama)
│   ├── loader.py           # File loader + multi-repo Git clone helper
│   ├── retriever.py        # ChromaDB MMR retriever
│   └── vectorstore.py      # ChromaDB create / load / clear helpers
├── web/                    # Web application
│   ├── server.py           # FastAPI backend with SSE streaming
│   └── static/
│       ├── index.html      # Single-page app
│       ├── style.css       # Dark theme UI
│       └── app.js          # Frontend logic (no framework)
├── data/                   # Runtime data (auto-created, auto-deleted)
│   ├── chroma_db/          # Vector database
│   └── repo_clone/         # Cloned repos, one folder per repo
├── cli.py                  # Terminal chat interface
├── ingest.py               # Ingestion CLI (local paths or Git URLs)
├── requirements.txt
└── .env                    # Your config
```

---

## Quick Start

### 1. Clone this repo

```bash
git clone https://github.com/taimoorsaqib1/Repo-Analyzer.git
cd Repo-Analyzer
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file in the project root:

```env
PROVIDER=ollama
OLLAMA_LLM_MODEL=qwen2.5-coder:7b
OLLAMA_EMBED_MODEL=nomic-embed-text
```

---

## Option A — Web App (Recommended)

```bash
python web/server.py
```

Open **http://localhost:8000** in your browser.

1. Paste one or more GitHub repo URLs in the sidebar
2. Set the branch (default: `main`) and click **Analyze Repos**
3. The app clones, indexes, and generates rich overview cards:
   - 🎯 Purpose · ✨ Key Features · 💡 Use Cases
   - 🛠 Tech Stack · 🔗 External Dependencies · 📊 Languages
   - 🏗 Architecture · 🚪 Entry Points · 🚀 Getting Started · ⚠ Limitations
4. Switch to the **Chat** tab to ask questions in real time
5. Click **Clear Session** — everything is wiped automatically

---

## Option B — Terminal CLI

### Index repositories

```bash
# Single remote repo
python ingest.py --git https://github.com/owner/repo

# Multiple remote repos
python ingest.py --git https://github.com/user/repo1 https://github.com/user/repo2

# Specific branch
python ingest.py --git https://github.com/owner/repo --branch develop

# Local folders
python ingest.py /path/to/repo1 /path/to/repo2

# Force re-index
python ingest.py --git https://github.com/owner/repo --force
```

### Chat

```bash
python cli.py
```

#### CLI Commands

| Command | Description |
|---|---|
| `/help` | Show available commands |
| `/clear` | Clear conversation history |
| `/sources` | Show source files from the last answer |
| `/config` | Show current configuration |
| `/quit` | Exit and clean up session data |

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PROVIDER` | `ollama` | `openai` or `ollama` |
| `OPENAI_API_KEY` | — | Your OpenAI API key |
| `OPENAI_EMBED_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `OPENAI_LLM_MODEL` | `gpt-4` | OpenAI chat model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `OLLAMA_LLM_MODEL` | `qwen2.5-coder:7b` | Ollama chat model |
| `CHROMA_PERSIST_DIR` | `./data/chroma_db` | Vector database location |
| `REPO_CLONE_DIR` | `./data/repo_clone` | Cloned repos location |
| `CHUNK_SIZE` | `1500` | Tokens per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `RETRIEVER_K` | `6` | Chunks retrieved per query |

### Using Ollama (local, free, offline)

```bash
# Install Ollama from https://ollama.com, then:
ollama pull qwen2.5-coder:7b   # LLM (recommended for 6GB+ VRAM)
ollama pull nomic-embed-text   # Embeddings
```

Set `PROVIDER=ollama` in `.env`.

### Using OpenAI

Set `PROVIDER=openai` and `OPENAI_API_KEY=sk-...` in `.env`.

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) (if using local models)
- OpenAI API key (if using OpenAI)

---

## License

MIT
