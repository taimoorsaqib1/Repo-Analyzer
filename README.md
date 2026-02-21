# Repo Analyzer — AI Coding Assistant

An AI-powered coding assistant that lets you **chat with any GitHub repository** using Retrieval-Augmented Generation (RAG). Add one or more repo URLs and it clones, indexes, and analyses them — then lets you ask natural-language questions through a **web UI** or a **terminal CLI**.

---

## Features

- **Multi-repo support** — analyze several repositories in a single session
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
