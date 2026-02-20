# Repo Analyzer — AI Coding Assistant

An AI-powered coding assistant that lets you **chat with any GitHub repository** using Retrieval-Augmented Generation (RAG). Point it at a local folder or a Git URL, and it indexes every source file into a vector database so you can ask natural-language questions about the codebase.

---

## Features

- **Clone or load** any Git repository automatically
- **Indexes** source files into a ChromaDB vector store (persistent)
- **Interactive CLI** — chat in your terminal with a rich UI
- **Dual provider support** — use **OpenAI** (GPT-4, etc.) or a **local Ollama** model
- Supports 25+ file types: Python, JS/TS, Go, Rust, Java, C/C++, HTML, CSS, SQL, and more
- Conversation memory — retains context across multi-turn questions
- Shows source file references for every answer

---

## Project Structure

```
.
├── assistant.py      # RAG chain — retriever + LLM + prompt
├── chunker.py        # Splits source files into overlapping chunks
├── cli.py            # Interactive terminal UI (rich)
├── config.py         # Centralized config (reads .env)
├── embeddings.py     # Embedding model factory (OpenAI / Ollama)
├── ingest.py         # Indexes a repo into ChromaDB
├── llm.py            # LLM factory (OpenAI / Ollama)
├── loader.py         # File loader + Git clone helper
├── retriever.py      # ChromaDB retriever wrapper
├── vectorstore.py    # ChromaDB create / load helpers
├── requirements.txt  # Python dependencies
└── .env.example      # Environment variable template
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

```bash
cp .env.example .env
```

Edit `.env` and set your provider and API keys (see [Configuration](#configuration)).

### 4. Index a repository

**Local folder:**
```bash
python ingest.py /path/to/your/project
```

**Remote Git URL:**
```bash
python ingest.py --git https://github.com/owner/repo.git
python ingest.py --git https://github.com/owner/repo.git --branch dev
```

### 5. Chat with the codebase

```bash
python cli.py
```

---

## Configuration

Copy `.env.example` to `.env` and fill in the values:

| Variable | Default | Description |
|---|---|---|
| `PROVIDER` | `ollama` | `openai` or `ollama` |
| `OPENAI_API_KEY` | — | Your OpenAI API key |
| `OPENAI_EMBED_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `OPENAI_LLM_MODEL` | `gpt-4` | OpenAI chat model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `OLLAMA_LLM_MODEL` | `deepseek-coder` | Ollama chat model |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | Where ChromaDB data is stored |
| `CHROMA_COLLECTION` | `codebase` | ChromaDB collection name |
| `CHUNK_SIZE` | `1500` | Token size per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |

### Using Ollama (local, free)

1. Install [Ollama](https://ollama.com)
2. Pull a coding model: `ollama pull deepseek-coder`
3. Pull an embedding model: `ollama pull nomic-embed-text`
4. Set `PROVIDER=ollama` in `.env`

### Using OpenAI

1. Set `PROVIDER=openai` in `.env`
2. Set your `OPENAI_API_KEY`

---

## CLI Commands

| Command | Description |
|---|---|
| `/help` | Show available commands |
| `/clear` | Clear conversation history |
| `/sources` | Show source files from the last answer |
| `/config` | Show current configuration |
| `/quit` | Exit the assistant |

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) (if using local models)
- OpenAI API key (if using OpenAI)

---

## License

MIT
