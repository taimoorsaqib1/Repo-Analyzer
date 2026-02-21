# Repo Analyzer - Comprehensive Technical Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [File-by-File Documentation](#file-by-file-documentation)
4. [Data Flow](#data-flow)
5. [Configuration System](#configuration-system)
6. [Dependencies](#dependencies)

---

## Project Overview

**Repo Analyzer** is a sophisticated RAG (Retrieval-Augmented Generation) based coding assistant that enables developers to have natural language conversations about any codebase. The system indexes source code into a vector database and uses semantic search combined with large language models to provide intelligent, context-aware answers about code.

### Key Features
- Multi-provider LLM support (OpenAI and Ollama)
- Language-aware code chunking (25+ programming languages)
- Persistent vector storage using ChromaDB
- Interactive rich CLI interface
- Git repository cloning and indexing
- Conversation history and context retention
- Multi-turn dialogue support
- Source reference tracking

### Technology Stack
- **Framework**: LangChain (orchestration and RAG pipeline)
- **Vector Database**: ChromaDB (persistent embeddings storage)
- **Embedding Models**: OpenAI text-embedding-3-small / Ollama nomic-embed-text
- **LLM Models**: OpenAI GPT-4 / Ollama qwen2.5-coder
- **CLI Framework**: Rich (terminal UI)
- **Version Control**: GitPython (repository cloning)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                         (cli.py)                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CODING ASSISTANT                             │
│                    (assistant.py)                               │
│  ┌──────────────┐         ┌─────────────┐                      │
│  │  Retriever   │ ◄─────► │     LLM     │                      │
│  └──────────────┘         └─────────────┘                      │
└──────┬────────────────────────────────┬─────────────────────────┘
       │                                │
       ▼                                ▼
┌─────────────────┐            ┌──────────────────┐
│ Vector Store    │            │  LLM Provider    │
│ (vectorstore.py)│            │  (llm.py)        │
│                 │            │                  │
│  ChromaDB       │            │  OpenAI/Ollama   │
└─────────────────┘            └──────────────────┘
       ▲
       │
┌──────┴───────────────────────────────────────────────────────┐
│                   INGESTION PIPELINE                          │
│                   (ingest.py)                                 │
│                                                               │
│  ┌──────────┐    ┌──────────┐    ┌────────────┐             │
│  │  Loader  │───►│ Chunker  │───►│ Embeddings │             │
│  │(loader.py)│   │(chunker.py)│  │(embeddings.│             │
│  └──────────┘    └──────────┘    │    py)     │             │
│                                   └────────────┘             │
└───────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **Ingestion Phase** (Offline):
   - Loader loads source files from disk/git
   - Chunker splits files into semantic chunks
   - Embeddings converts chunks to vectors
   - VectorStore persists vectors to ChromaDB

2. **Query Phase** (Runtime):
   - User inputs question via CLI
   - Assistant retrieves relevant code chunks
   - LLM processes question + context
   - Response formatted and displayed

---

## File-by-File Documentation

### 1. config.py

**Purpose**: Centralized configuration management using environment variables.

**Dependencies**:
- `os` - Environment variable access
- `pathlib.Path` - Path manipulation
- `dotenv` - .env file parsing

#### Functions & Variables

##### `load_dotenv(Path(__file__).parent / ".env")`
- **Description**: Loads environment variables from `.env` file in project root
- **Location**: Module level (executed on import)

##### Configuration Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PROVIDER` | str | `"ollama"` | AI provider selection: "openai" or "ollama" |
| `OPENAI_API_KEY` | str | `""` | OpenAI API authentication key |
| `OPENAI_EMBED_MODEL` | str | `"text-embedding-3-small"` | OpenAI embedding model identifier |
| `OPENAI_LLM_MODEL` | str | `"gpt-4"` | OpenAI chat model identifier |
| `OLLAMA_BASE_URL` | str | `"http://localhost:11434"` | Ollama server endpoint |
| `OLLAMA_EMBED_MODEL` | str | `"nomic-embed-text"` | Ollama embedding model name |
| `OLLAMA_LLM_MODEL` | str | `"qwen2.5-coder:1.5b"` | Ollama chat model name |
| `CHROMA_PERSIST_DIR` | str | `"./chroma_db"` | ChromaDB persistence directory |
| `CHROMA_COLLECTION` | str | `"codebase"` | ChromaDB collection name |
| `CHUNK_SIZE` | int | `1500` | Maximum characters per code chunk |
| `CHUNK_OVERLAP` | int | `200` | Overlapping characters between chunks |
| `INCLUDE_EXTENSIONS` | set[str] | {...} | Allowed file extensions for indexing |
| `EXCLUDE_DIRS` | set[str] | {...} | Directories to skip during indexing |
| `RETRIEVER_K` | int | `3` | Number of chunks to retrieve per query |
| `RETRIEVER_SEARCH_TYPE` | str | `"mmr"` | Search algorithm: "similarity" or "mmr" |

**Architecture Notes**:
- Single source of truth for all configuration
- Type-safe with explicit type annotations
- Validated defaults prevent missing config errors
- Environment-first approach enables easy deployment configuration

---

### 2. embeddings.py

**Purpose**: Abstraction layer for embedding model providers.

**Dependencies**:
- `langchain_core.embeddings.Embeddings` - Base embedding interface
- `config` - Configuration access

#### Functions

##### `get_embeddings() -> Embeddings`

**Description**: Factory function that returns the appropriate embedding model based on configuration.

**Returns**: 
- `OpenAIEmbeddings` or `OllamaEmbeddings` instance

**Behavior**:
- **OpenAI Provider**:
  - Creates `OpenAIEmbeddings` instance
  - Uses `config.OPENAI_EMBED_MODEL`
  - Requires valid `config.OPENAI_API_KEY`
  
- **Ollama Provider**:
  - Creates `OllamaEmbeddings` instance
  - Uses `config.OLLAMA_EMBED_MODEL`
  - Connects to `config.OLLAMA_BASE_URL`

**Raises**:
- `ValueError` - If provider is not "openai" or "ollama"

**Architecture Notes**:
- Implements Strategy pattern for provider switching
- Lazy imports prevent unnecessary dependency loading
- Enables testing with mock embeddings

**Example Usage**:
```python
embeddings = get_embeddings()
vectors = embeddings.embed_documents(["code snippet 1", "code snippet 2"])
```

---

### 3. llm.py

**Purpose**: Abstraction layer for Large Language Model providers.

**Dependencies**:
- `langchain_core.language_models.BaseChatModel` - Base LLM interface
- `config` - Configuration access

#### Functions

##### `get_llm() -> BaseChatModel`

**Description**: Factory function that returns the appropriate chat model based on configuration.

**Returns**: 
- `ChatOpenAI` or `ChatOllama` instance

**Behavior**:
- **OpenAI Provider**:
  - Creates `ChatOpenAI` instance
  - Uses `config.OPENAI_LLM_MODEL`
  - Requires valid `config.OPENAI_API_KEY`
  - Sets temperature to 0.1 (deterministic responses)
  
- **Ollama Provider**:
  - Creates `ChatOllama` instance
  - Uses `config.OLLAMA_LLM_MODEL`
  - Connects to `config.OLLAMA_BASE_URL`
  - Sets temperature to 0.1 (deterministic responses)

**Raises**:
- `ValueError` - If provider is not "openai" or "ollama"

**Configuration**:
- Temperature: `0.1` - Low temperature for consistent, factual code answers

**Architecture Notes**:
- Mirror implementation of embeddings.py for consistency
- Lazy imports reduce startup time
- Temperature hardcoded for code-specific use case

**Example Usage**:
```python
llm = get_llm()
response = llm.invoke([HumanMessage(content="Explain this code")])
```

---

### 4. loader.py

**Purpose**: Repository loader that converts source files into LangChain Document objects with metadata.

**Dependencies**:
- `os`, `stat`, `shutil` - File system operations
- `pathlib.Path` - Path manipulation
- `langchain_core.documents.Document` - Document container
- `git.Repo` - Git operations
- `config` - Filter configuration

#### Functions

##### `_force_remove_readonly(func, path, _)`

**Description**: Error handler for `shutil.rmtree` that removes read-only flags on Windows.

**Parameters**:
- `func` - The function that raised the error (e.g., `os.remove`)
- `path` - Path to the file/directory
- `_` - Exception info (unused)

**Purpose**: Fixes Windows .git directory removal issues

---

##### `_should_include(filepath: Path) -> bool`

**Description**: Determines if a file should be indexed based on extension and path.

**Parameters**:
- `filepath` (Path) - File path to check

**Returns**: 
- `bool` - True if file should be included

**Logic**:
1. Check if extension is in `config.INCLUDE_EXTENSIONS`
2. Check if any path component is in `config.EXCLUDE_DIRS`
3. Return False if either check fails

**Example**:
```python
_should_include(Path("src/main.py"))        # True
_should_include(Path("node_modules/lib.js")) # False
_should_include(Path("test.txt"))           # True
_should_include(Path("binary.exe"))         # False
```

---

##### `_detect_language(filepath: Path) -> str`

**Description**: Maps file extension to programming language identifier.

**Parameters**:
- `filepath` (Path) - File path

**Returns**: 
- `str` - Language name (e.g., "python", "javascript", "unknown")

**Supported Languages** (40+ extensions):
- Python (.py)
- JavaScript/TypeScript (.js, .ts, .jsx, .tsx)
- Java (.java)
- Go (.go)
- Rust (.rs)
- C/C++ (.c, .cpp, .h, .hpp)
- HTML/CSS (.html, .css, .scss)
- Config formats (.json, .yaml, .toml)
- Shell scripts (.sh, .bat, .ps1)
- Mobile (.dart, .swift, .kt)
- Web (.rb, .php)

---

##### `load_from_directory(repo_path: str) -> list[Document]`

**Description**: Recursively walks a directory tree and loads all matching source files.

**Parameters**:
- `repo_path` (str) - Path to repository root

**Returns**: 
- `list[Document]` - List of Document objects with content and metadata

**Process**:
1. Resolve absolute path
2. Walk directory tree using `os.walk`
3. Prune excluded directories in-place (optimization)
4. Filter files by extension and path
5. Read file content (UTF-8, ignore errors)
6. Skip empty files and files > 500KB
7. Create Document with metadata

**Document Metadata**:
- `source` - Relative path (forward slashes)
- `filename` - Base filename
- `language` - Detected language
- `extension` - File extension (lowercase)
- `size_bytes` - Content length

**Error Handling**:
- Silently skips unreadable files
- Ignores encoding errors
- Counts skipped files

**Raises**:
- `FileNotFoundError` - If `repo_path` doesn't exist

**Example**:
```python
docs = load_from_directory("/path/to/project")
print(f"Loaded {len(docs)} files")
print(docs[0].metadata)
# {'source': 'src/main.py', 'filename': 'main.py', 'language': 'python', ...}
```

---

##### `load_from_git(clone_url: str, branch: str = "main", clone_to: str = "./repo_clone") -> list[Document]`

**Description**: Clones a Git repository and loads its files as Documents.

**Parameters**:
- `clone_url` (str) - Git repository URL
- `branch` (str) - Branch name (default: "main")
- `clone_to` (str) - Local clone destination (default: "./repo_clone")

**Returns**: 
- `list[Document]` - Loaded documents from cloned repository

**Process**:
1. Check if clone path exists
2. If exists, verify if same repository:
   - **Same repo**: Pull latest changes
   - **Different repo**: Delete and re-clone
3. If not exists: Clone repository
4. Call `load_from_directory()` on clone path

**Smart Caching**:
- Compares remote URLs (normalized)
- Reuses existing clone when possible
- Automatically updates via pull

**Error Handling**:
- Uses `_force_remove_readonly` for Windows compatibility
- Validates existing clones

**Example**:
```python
docs = load_from_git(
    "https://github.com/user/repo.git",
    branch="develop"
)
```

**Architecture Notes**:
- Separation of concerns (git vs file loading)
- Idempotent operation (safe to re-run)

---

### 5. chunker.py

**Purpose**: Language-aware text splitter that maintains code structure integrity.

**Dependencies**:
- `langchain_text_splitters.RecursiveCharacterTextSplitter` - Base splitter
- `langchain_text_splitters.Language` - Language enum
- `langchain_core.documents.Document` - Document container
- `config` - Chunk configuration

#### Constants

##### `_EXT_TO_LANGUAGE: dict[str, Language]`

**Description**: Mapping from file extensions to LangChain Language enums.

**Purpose**: Enables language-aware splitting that respects:
- Function/class boundaries
- Code block structure
- Language-specific syntax

**Supported Languages**:
- Python, JavaScript, TypeScript (+ JSX/TSX variants)
- Java, Go, Rust
- C, C++
- Ruby, PHP, Swift
- HTML, Markdown

---

#### Functions

##### `_get_splitter(extension: str) -> RecursiveCharacterTextSplitter`

**Description**: Returns an appropriate text splitter for the given file extension.

**Parameters**:
- `extension` (str) - File extension (e.g., ".py")

**Returns**: 
- `RecursiveCharacterTextSplitter` - Configured splitter instance

**Behavior**:

**Language-Aware Splitting** (if language detected):
- Uses `RecursiveCharacterTextSplitter.from_language()`
- Respects function/class boundaries
- Uses language-specific separators
- Chunk size: `config.CHUNK_SIZE`
- Chunk overlap: `config.CHUNK_OVERLAP`

**Generic Splitting** (fallback):
- Uses custom separator hierarchy:
  1. `\n\n` - Paragraph/block boundaries
  2. `\n` - Line boundaries
  3. ` ` - Word boundaries
  4. `""` - Character level (last resort)
- Same chunk size/overlap as above

**Example**:
```python
# Python file - uses language-aware splitting
splitter = _get_splitter(".py")

# Unknown extension - uses generic splitting
splitter = _get_splitter(".xyz")
```

---

##### `chunk_documents(documents: list[Document]) -> list[Document]`

**Description**: Splits a list of Documents into smaller, overlapping chunks with enriched metadata.

**Parameters**:
- `documents` (list[Document]) - Full-file documents from loader

**Returns**: 
- `list[Document]` - Chunked documents with position metadata

**Process**:
1. Iterate through each document
2. Get appropriate splitter for file extension
3. Split document into chunks
4. Enrich each chunk with position metadata:
   - `chunk_index` - 0-based chunk number
   - `total_chunks` - Total chunks for this file
5. Preserve all original metadata
6. Append to result list

**Metadata Preservation**:
- Original metadata (source, language, etc.) is maintained
- Additional metadata is added (not replaced)

**Example**:
```python
full_docs = load_from_directory("./src")
chunks = chunk_documents(full_docs)

print(f"Files: {len(full_docs)}, Chunks: {len(chunks)}")
# Files: 10, Chunks: 47

print(chunks[0].metadata)
# {
#   'source': 'main.py',
#   'filename': 'main.py',
#   'language': 'python',
#   'chunk_index': 0,
#   'total_chunks': 5,
#   ...
# }
```

**Architecture Notes**:
- Chunk overlap prevents context loss at boundaries
- Position metadata enables source tracking
- Language-aware splitting maintains code semantics

---

### 6. vectorstore.py

**Purpose**: ChromaDB vector store management (create, load, clear operations).

**Dependencies**:
- `pathlib.Path` - Path manipulation
- `langchain_core.documents.Document` - Document container
- `langchain_chroma.Chroma` - ChromaDB integration
- `chromadb` - Direct ChromaDB client (for deletion)
- `config` - Storage configuration
- `embeddings.get_embeddings` - Embedding model factory

#### Functions

##### `clear_vectorstore() -> None`

**Description**: Safely deletes the existing ChromaDB collection.

**Process**:
1. Check if persist directory exists
2. Try API-based deletion (preferred):
   - Initialize ChromaDB client
   - List collections
   - Delete target collection by name
3. Fallback to directory deletion if API fails
4. Silently succeeds if directory doesn't exist

**Why Two Methods?**:
- **API deletion**: Safe, doesn't corrupt database
- **Directory deletion**: Handles locked/corrupted databases

**Example**:
```python
clear_vectorstore()  # Safe to call even if DB doesn't exist
```

**Architecture Notes**:
- Prevents file lock issues on Windows
- Idempotent operation
- No-op if already cleared

---

##### `create_vectorstore(documents: list[Document]) -> Chroma`

**Description**: Creates and persists a new ChromaDB collection from documents.

**Parameters**:
- `documents` (list[Document]) - Chunked documents with embeddings

**Returns**: 
- `Chroma` - Vector store instance

**Process**:
1. Resolve and create persist directory
2. Get embedding function from config
3. Create ChromaDB collection using `Chroma.from_documents()`:
   - Embeds all documents
   - Stores vectors with metadata
   - Persists to disk
4. Return store instance

**Persistence**:
- Automatically saves to `config.CHROMA_PERSIST_DIR`
- Creates collection `config.CHROMA_COLLECTION`
- Survives process restart

**Example**:
```python
chunks = chunk_documents(documents)
store = create_vectorstore(chunks)
```

**Performance Notes**:
- Embedding is the slowest operation
- Progress depends on:
  - Number of chunks
  - Embedding model speed
  - API rate limits (if using OpenAI)

---

##### `load_vectorstore() -> Chroma`

**Description**: Loads an existing persisted ChromaDB collection.

**Returns**: 
- `Chroma` - Vector store instance

**Raises**:
- `FileNotFoundError` - If persist directory doesn't exist

**Process**:
1. Check persist directory exists
2. Get embedding function (must match original)
3. Initialize Chroma with existing collection
4. Return store instance

**Requirements**:
- Same embedding model as used during creation
- Intact persist directory

**Example**:
```python
try:
    store = load_vectorstore()
except FileNotFoundError:
    print("Run ingest.py first!")
```

**Architecture Notes**:
- Read-only operation (doesn't modify DB)
- Fast startup (no embedding needed)
- Embedding function required for query embedding

---

### 7. retriever.py

**Purpose**: Wraps ChromaDB with intelligent retrieval using Maximal Marginal Relevance (MMR).

**Dependencies**:
- `langchain_core.vectorstores.VectorStoreRetriever` - Retriever interface
- `config` - Retrieval configuration
- `vectorstore.load_vectorstore` - Vector store loader

#### Functions

##### `get_retriever() -> VectorStoreRetriever`

**Description**: Creates a retriever from the persisted vector store with MMR search.

**Returns**: 
- `VectorStoreRetriever` - Configured retriever instance

**Configuration**:
- **Search Type**: `config.RETRIEVER_SEARCH_TYPE` (default: "mmr")
- **K**: `config.RETRIEVER_K` (default: 3 chunks)

**Search Algorithm - MMR (Maximal Marginal Relevance)**:
- Balances relevance with diversity
- Algorithm:
  1. Find most relevant chunks (high cosine similarity)
  2. Remove near-duplicates
  3. Select diverse set covering different aspects

**Benefits of MMR**:
- Avoids redundant chunks from same file
- Better coverage of codebase
- More comprehensive context for LLM

**Alternative Search Types**:
- `"similarity"` - Pure cosine similarity (may return duplicates)
- `"mmr"` - Diverse relevant results (recommended)

**Example**:
```python
retriever = get_retriever()
docs = retriever.invoke("How does authentication work?")
# Returns 3 diverse, relevant chunks
```

**Architecture Notes**:
- Lazy loading (loads DB on first call)
- Stateless (can create multiple instances)
- Configurable via config.py

---

### 8. assistant.py

**Purpose**: RAG-powered coding assistant combining retrieval, LLM, and prompt engineering.

**Dependencies**:
- `langchain_core.documents.Document` - Document container
- `langchain_core.messages` - Message types (Human, AI, System)
- `retriever.get_retriever` - Retriever factory
- `llm.get_llm` - LLM factory

#### Constants

##### `SYSTEM_PROMPT: str`

**Description**: System message that defines the assistant's role and behavior.

**Content**:
```
You are an expert senior software engineer acting as a coding assistant.
You have access to relevant source code from the user's project.

Your responsibilities:
1. Answer questions about the codebase accurately and concisely.
2. Explain how code works, including control flow and design patterns.
3. Suggest improvements, refactors, or bug fixes when asked.
4. Reference specific files and line-level details when relevant.

Guidelines:
- Ground your answers in the provided code context.
- Use code blocks with language tags.
- Be concise but thorough.
- Reference files using metadata paths.
```

**Purpose**: 
- Sets expert persona
- Defines scope and capabilities
- Establishes output format expectations
- Prevents hallucination by grounding in context

---

#### Functions

##### `_format_context(docs: list[Document]) -> str`

**Description**: Formats retrieved documents into a readable context block for the LLM.

**Parameters**:
- `docs` (list[Document]) - Retrieved code chunks

**Returns**: 
- `str` - Formatted context string

**Format**:
```
--- File: src/main.py (chunk 1/3) [python] ---
<code content>

--- File: src/utils.js (chunk 1/1) [javascript] ---
<code content>
```

**Metadata Included**:
- Source file path
- Chunk position (if applicable)
- Programming language
- Code content

**Purpose**:
- Makes context clear to LLM
- Enables file-specific references
- Shows chunk relationships

---

#### Classes

##### `CodingAssistant`

**Description**: Main RAG assistant class that orchestrates retrieval and generation.

**Attributes**:
- `retriever` (VectorStoreRetriever) - Code chunk retriever
- `llm` (BaseChatModel) - Language model
- `history` (list[HumanMessage | AIMessage]) - Conversation history

---

###### `__init__(self)`

**Description**: Initializes the assistant with retriever and LLM.

**Process**:
1. Load retriever from vector store
2. Load LLM from config
3. Initialize empty conversation history

**May Raise**:
- `FileNotFoundError` - If vector store doesn't exist

---

###### `ask(self, question: str) -> tuple[str, list[Document]]`

**Description**: Processes a question and returns an answer with source documents.

**Parameters**:
- `question` (str) - User's question about the codebase

**Returns**: 
- `tuple[str, list[Document]]` - (answer_text, source_documents)

**Process**:
1. **Retrieval**: Invoke retriever with question
   - Semantic search in vector store
   - Returns K most relevant chunks
   
2. **Context Building**: Format retrieved docs
   
3. **Message Construction**:
   - System prompt (role definition)
   - Last 10 history messages (5 exchanges)
   - Current question with context
   
4. **LLM Invocation**: Send messages to LLM
   
5. **History Update**: Store question and answer
   
6. **Return**: Answer text and source docs

**Conversation Memory**:
- Keeps last 10 messages (rolling window)
- Maintains context across turns
- Prevents context overflow

**Example**:
```python
assistant = CodingAssistant()
answer, sources = assistant.ask("What does the login function do?")
print(answer)
for doc in sources:
    print(doc.metadata['source'])
```

---

###### `clear_history(self)`

**Description**: Clears conversation history for fresh context.

**Purpose**:
- Reset conversation state
- Prevent context bleed between topics
- Free memory

**Example**:
```python
assistant.clear_history()  # Start fresh conversation
```

---

###### `get_sources(self, docs: list[Document]) -> list[str]`

**Description**: Extracts unique source file paths from documents.

**Parameters**:
- `docs` (list[Document]) - Retrieved documents

**Returns**: 
- `list[str]` - Unique source paths in order of appearance

**Process**:
1. Iterate through documents
2. Extract 'source' from metadata
3. Track seen sources in set
4. Maintain insertion order in list

**Example**:
```python
sources = assistant.get_sources(docs)
# ['src/auth.py', 'src/utils.py', 'tests/test_auth.py']
```

**Architecture Notes**:
- Preserves order for UI display
- Deduplicates for clarity

---

### 9. ingest.py

**Purpose**: Command-line script for indexing repositories into ChromaDB.

**Dependencies**:
- `sys` - Command-line arguments
- `time` - Performance timing
- `shutil` - Directory operations
- `pathlib.Path` - Path manipulation
- `rich` - Terminal UI components
- `config` - Configuration
- `loader` - File loading
- `chunker` - Document chunking
- `vectorstore` - Vector storage

#### Global Objects

##### `console: Console`

**Description**: Rich console instance for styled output.

---

#### Functions

##### `ingest_local(repo_path: str, force: bool = False)`

**Description**: Indexes a local repository into the vector store with progress tracking.

**Parameters**:
- `repo_path` (str) - Path to local repository
- `force` (bool) - Skip confirmation if vector store exists

**Process**:
1. **Display Banner**: Show config (provider, model)

2. **Existing Store Check**:
   - If exists and not force: Prompt user
   - If user declines: Exit
   - If force or user confirms: Clear old store

3. **Loading Phase**:
   - Call `load_from_directory()`
   - Show progress spinner
   - Display file count and timing

4. **Chunking Phase**:
   - Call `chunk_documents()`
   - Show progress spinner
   - Display chunk count and timing

5. **Embedding Phase**:
   - Call `create_vectorstore()`
   - Show progress spinner
   - Display timing

6. **Summary**:
   - Total files and chunks
   - Language breakdown (top 8)
   - Storage location

**Progress UI**:
```
🧠 Code Assistant — Ingestion
   Provider: ollama
   Embed Model: nomic-embed-text

⠹ Embedding & storing... ━━━━━━━━━━━━━━━━━━━━━━ 100%
   ✓ Loaded 47 files in 0.3s
   ✓ Created 152 chunks in 0.1s
   ✓ Embedded and stored in 5.2s

📊 Summary
   Files: 47
   Chunks: 152
   Languages: python: 35, javascript: 8, markdown: 2, json: 2
   Stored at: ./chroma_db
```

**Example**:
```python
ingest_local("/path/to/repo", force=True)
```

---

##### `main()`

**Description**: Main entry point that parses arguments and executes ingestion.

**Command-Line Interface**:

**Help** (`--help`, `-h`):
```bash
python ingest.py --help
```

**Local Repository**:
```bash
python ingest.py /path/to/repo
python ingest.py /path/to/repo --force
```

**Git Repository**:
```bash
python ingest.py --git <url>
python ingest.py --git <url> --branch develop
```

**Argument Parsing**:
1. Check for help flag
2. Extract `--force` flag
3. Detect `--git` mode:
   - Extract URL (required)
   - Extract branch (optional, default: "main")
4. Else: Local mode

**Git Mode Behavior**:
- Always prompts before clearing (unless force)
- Clones to `./repo_clone`
- Indexes cloned repository

**Local Mode Behavior**:
- Validates directory exists
- Calls `ingest_local()`

**Example Usage**:
```bash
# Index local folder
python ingest.py ./my-project

# Force re-index
python ingest.py ./my-project --force

# Clone and index
python ingest.py --git https://github.com/user/repo.git

# Clone specific branch
python ingest.py --git https://github.com/user/repo.git --branch dev
```

---

### 10. cli.py

**Purpose**: Interactive terminal UI for chatting with the coding assistant.

**Dependencies**:
- `sys` - Exit handling
- `rich.console.Console` - Terminal output
- `rich.panel.Panel` - UI panels
- `rich.markdown.Markdown` - Markdown rendering
- `rich.theme.Theme` - Color themes
- `config` - Configuration display
- `assistant.CodingAssistant` - RAG assistant (lazy import)

#### Constants

##### `theme: Theme`

**Description**: Custom Rich theme for colored output.

**Colors**:
- `info`: cyan
- `success`: green
- `warning`: yellow
- `error`: red bold
- `user`: bold white
- `assistant`: bright_white
- `source`: dim cyan

---

##### `console: Console`

**Description**: Rich console with custom theme.

---

##### `BANNER: str`

**Description**: ASCII art banner for application startup.

```
   ____          _         _            _     _              _
  / ___|___   __| | ___   / \   ___ ___(_)___| |_ __ _ _ __ | |_
 | |   / _ \ / _` |/ _ \ / _ \ / __/ __| / __| __/ _` | '_ \| __|
 | |__| (_) | (_| |  __// ___ \\__ \__ \ \__ \ || (_| | | | | |_
  \____\___/ \__,_|\___/_/   \_\___/___/_|___/\__\__,_|_| |_|\__|
```

---

##### `HELP_TEXT: str`

**Description**: Command reference text.

**Commands**:
- `/help` - Show help
- `/clear` - Clear history
- `/sources` - Show last sources
- `/config` - Show configuration
- `/quit` - Exit

---

#### Functions

##### `show_banner()`

**Description**: Displays application banner with provider info.

**Output**:
```
┌────────────────────────────────────────┐
│ <ASCII Banner>                         │
│   Provider: OLLAMA — 🏠 qwen2.5-coder │
│   Type /help for commands              │
└────────────────────────────────────────┘
```

---

##### `main()`

**Description**: Main event loop for the interactive CLI.

**Process**:

1. **Initialization**:
   ```python
   show_banner()
   from assistant import CodingAssistant
   assistant = CodingAssistant()
   ```

2. **Error Handling**:
   - Import errors: Suggest running ingest.py
   - FileNotFoundError: No index found
   - Other exceptions: Display error

3. **Main Loop**:
   ```python
   while True:
       question = input("You ❯ ")
       if question.startswith("/"):
           handle_command()
       else:
           answer, docs = assistant.ask(question)
           display_answer()
   ```

**Command Handlers**:

- **`/quit`, `/exit`, `/q`**: Exit application
  ```
  Goodbye! 👋
  ```

- **`/help`, `/h`**: Display help text
  
- **`/clear`**: Clear conversation history
  ```
  ✓ Conversation history cleared.
  ```

- **`/sources`**: Show sources from last answer
  ```
  📄 Sources from last answer:
    • src/auth.py
    • src/database.py
  ```

- **`/config`**: Display current configuration
  ```
  ⚙️  Configuration
  Provider: ollama
  LLM Model: qwen2.5-coder:1.5b
  Embed Model: nomic-embed-text
  Vector Store: ./chroma_db
  Retriever K: 3
  Chunk Size: 1500
  ```

**Question Handling**:
1. Show "Thinking..." spinner
2. Call `assistant.ask(question)`
3. Display answer in panel (Markdown formatted)
4. Show source files below answer (up to 4, "+N more")

**Example Output**:
```
You ❯ How does the login system work?

┌─────────────────────────────────────────────┐
│ 🤖 Assistant                                │
├─────────────────────────────────────────────┤
│ The login system uses JWT tokens...         │
│                                             │
│ ```python                                   │
│ def login(username, password):              │
│     ...                                     │
│ ```                                         │
└─────────────────────────────────────────────┘
  📄 Sources: src/auth.py │ src/models.py
```

**Error Handling**:
- Keyboard interrupt (Ctrl+C): Graceful exit
- EOF (Ctrl+D): Graceful exit
- Empty input: Ignore
- Unknown command: Warning message
- Query errors: Display error, continue loop

**Architecture Notes**:
- Lazy import prevents startup if index missing
- Stateful conversation via assistant.history
- Rich UI provides excellent UX

---

## Data Flow

### Ingestion Pipeline (Offline)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. INPUT                                                        │
│    Repository Path or Git URL                                  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. LOADING (loader.py)                                          │
│    • Walk directory tree                                       │
│    • Filter by extension (config.INCLUDE_EXTENSIONS)           │
│    • Skip excluded dirs (config.EXCLUDE_DIRS)                  │
│    • Read file contents (UTF-8)                                │
│    • Create Documents with metadata                            │
│                                                                 │
│    Output: List[Document] - Full files                         │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. CHUNKING (chunker.py)                                        │
│    • Detect language from extension                            │
│    • Get language-aware splitter                               │
│    • Split respecting code boundaries                          │
│    • Add chunk position metadata                               │
│                                                                 │
│    Config: CHUNK_SIZE=1500, CHUNK_OVERLAP=200                  │
│    Output: List[Document] - Code chunks                        │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. EMBEDDING (embeddings.py + vectorstore.py)                  │
│    • Get embedding model (OpenAI/Ollama)                       │
│    • Convert each chunk to vector                              │
│    • Store vectors + metadata in ChromaDB                      │
│    • Persist to disk (CHROMA_PERSIST_DIR)                      │
│                                                                 │
│    Output: Persisted ChromaDB collection                       │
└─────────────────────────────────────────────────────────────────┘
```

### Query Pipeline (Runtime)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. INPUT                                                        │
│    User Question: "How does authentication work?"              │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. RETRIEVAL (retriever.py)                                     │
│    • Embed question using same model                           │
│    • Semantic search in vector store                           │
│    • MMR algorithm (relevant + diverse)                        │
│    • Return top K chunks (default: 3)                          │
│                                                                 │
│    Output: List[Document] - Relevant code chunks               │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. CONTEXT FORMATTING (assistant.py)                            │
│    • Format chunks into readable context                       │
│    • Include file paths, languages, chunk positions            │
│    • Build message array:                                      │
│      1. System prompt (role definition)                        │
│      2. Conversation history (last 10 messages)                │
│      3. Context + question                                     │
│                                                                 │
│    Output: List[Message] - LLM input                           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. GENERATION (llm.py)                                          │
│    • Send messages to LLM (OpenAI/Ollama)                      │
│    • LLM synthesizes answer from context                       │
│    • Return response text                                      │
│                                                                 │
│    Config: temperature=0.1 (deterministic)                     │
│    Output: String - Answer text                                │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. OUTPUT (cli.py)                                              │
│    • Render answer as Markdown                                 │
│    • Display source files                                      │
│    • Update conversation history                               │
│    • Wait for next question                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration System

### Environment Variables (.env)

The application uses a single `.env` file for all configuration. This follows the [12-factor app](https://12factor.net/config) methodology.

**File Location**: Project root (same directory as Python files)

**Loading**: Automatic via `config.py` module import

### Configuration Categories

#### 1. Provider Selection

```bash
PROVIDER=ollama  # or "openai"
```

**Purpose**: Switches between local (Ollama) and cloud (OpenAI) providers.

**Impact**:
- Changes embedding model source
- Changes LLM source
- Affects cost (OpenAI is paid, Ollama is free)
- Affects latency (OpenAI is cloud, Ollama is local)

---

#### 2. OpenAI Configuration

```bash
OPENAI_API_KEY=sk-...
OPENAI_EMBED_MODEL=text-embedding-3-small
OPENAI_LLM_MODEL=gpt-4
```

**Models Available**:
- **Embeddings**: 
  - `text-embedding-3-small` (1536 dims, cheap)
  - `text-embedding-3-large` (3072 dims, better quality)
  - `text-embedding-ada-002` (legacy)
  
- **LLM**:
  - `gpt-4` (most capable)
  - `gpt-4-turbo` (faster, cheaper)
  - `gpt-3.5-turbo` (fastest, cheapest)

**Cost Considerations**:
- Embedding: ~$0.02 per 1M tokens
- GPT-4: ~$0.03 per 1K tokens (input)

---

#### 3. Ollama Configuration

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=qwen2.5-coder:1.5b
```

**Requirements**:
- Ollama installed and running
- Models pulled locally

**Model Installation**:
```bash
ollama pull nomic-embed-text
ollama pull qwen2.5-coder:1.5b
```

**Recommended Models**:
- **Embeddings**: 
  - `nomic-embed-text` (768 dims, fast)
  - `mxbai-embed-large` (1024 dims, better quality)
  
- **LLM**:
  - `qwen2.5-coder:1.5b` (fast, 1.5B params)
  - `deepseek-coder:6.7b` (better quality, 6.7B params)
  - `codellama:13b` (highest quality, 13B params)

---

#### 4. Vector Store Configuration

```bash
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION=codebase
```

**CHROMA_PERSIST_DIR**:
- Where ChromaDB stores data
- Can be absolute or relative path
- Should be excluded from git

**CHROMA_COLLECTION**:
- Collection name within ChromaDB
- Allows multiple projects in same DB
- Change for each project

---

#### 5. Chunking Configuration

```bash
CHUNK_SIZE=1500
CHUNK_OVERLAP=200
```

**CHUNK_SIZE**:
- Maximum characters per chunk
- Larger = more context per chunk
- Smaller = more precise retrieval
- Recommended: 1000-2000

**CHUNK_OVERLAP**:
- Characters shared between chunks
- Prevents context loss at boundaries
- Recommended: 10-20% of chunk size

**Trade-offs**:
- **Large chunks**: Better context, may exceed token limits
- **Small chunks**: More precise, may miss context
- **Large overlap**: Better continuity, more storage
- **Small overlap**: Less redundancy, may miss connections

---

#### 6. Retrieval Configuration

```bash
RETRIEVER_K=3
RETRIEVER_SEARCH_TYPE=mmr
```

**RETRIEVER_K**:
- Number of chunks to retrieve
- More = more context, slower
- Less = faster, may miss info
- Recommended: 3-5

**RETRIEVER_SEARCH_TYPE**:
- `"similarity"` - Pure cosine similarity
- `"mmr"` - Maximal Marginal Relevance (diverse results)

---

#### 7. File Filters

```python
INCLUDE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".rs", ".cpp", ".c",
    # ... 25+ extensions
}

EXCLUDE_DIRS = {
    ".git", "__pycache__", "node_modules",
    "venv", ".venv", "dist", "build",
    # ... common build/cache directories
}
```

**Purpose**: Control what gets indexed

**Customization**:
Edit in `config.py` to add/remove extensions or directories.

---

## Dependencies

### Core Framework

```
langchain>=0.3.0
langchain-community>=0.3.0
```
**Purpose**: RAG orchestration, document handling, message abstraction

---

### LLM Providers

```
langchain-openai>=0.2.0
openai>=1.0.0
tiktoken>=0.7.0
```
**Purpose**: OpenAI integration (embeddings + chat)

```
langchain-ollama>=0.2.0
```
**Purpose**: Ollama integration (local models)

---

### Vector Database

```
langchain-chroma>=0.2.0
chromadb>=0.5.0
```
**Purpose**: Persistent vector storage and similarity search

---

### Utilities

```
gitpython>=3.1.0
```
**Purpose**: Git repository cloning

```
python-dotenv>=1.0.0
```
**Purpose**: Environment variable loading

```
rich>=13.0.0
```
**Purpose**: Terminal UI (colors, panels, progress bars)

---

### Dependency Tree

```
repo-analyzer/
├── langchain (core)
│   ├── langchain-openai → openai, tiktoken
│   ├── langchain-ollama → (connects to Ollama server)
│   ├── langchain-chroma → chromadb
│   └── langchain-community → (shared utilities)
├── gitpython → git (system)
├── python-dotenv → (no deps)
└── rich → (no deps)
```

---

## Architecture Patterns

### 1. Factory Pattern

Used in `embeddings.py` and `llm.py`:

```python
def get_embeddings() -> Embeddings:
    if config.PROVIDER == "openai":
        return OpenAIEmbeddings(...)
    elif config.PROVIDER == "ollama":
        return OllamaEmbeddings(...)
```

**Benefits**:
- Abstraction from concrete implementations
- Easy to switch providers
- Centralizes creation logic

---

### 2. Lazy Imports

Used throughout for provider-specific modules:

```python
def get_llm():
    if config.PROVIDER == "openai":
        from langchain_openai import ChatOpenAI  # Import only if needed
        return ChatOpenAI(...)
```

**Benefits**:
- Faster startup (don't load unused code)
- Clear error messages (missing deps for unused provider)
- Reduced memory footprint

---

### 3. Separation of Concerns

Each module has a single, clear responsibility:

| Module | Responsibility |
|--------|---------------|
| config.py | Configuration management |
| loader.py | File I/O and Git operations |
| chunker.py | Text splitting |
| embeddings.py | Embedding abstraction |
| vectorstore.py | Database operations |
| retriever.py | Search logic |
| llm.py | LLM abstraction |
| assistant.py | RAG orchestration |
| cli.py | User interface |
| ingest.py | Ingestion workflow |

**Benefits**:
- Easy to test individual components
- Clear boundaries
- Easy to modify one part without affecting others

---

### 4. Metadata Enrichment Pipeline

Documents gain metadata at each stage:

```
Load:        {source, filename, language, extension, size_bytes}
      ↓
Chunk:       + {chunk_index, total_chunks}
      ↓
Retrieve:    (same metadata preserved)
      ↓
Format:      Used to display file references
```

---

### 5. Configuration as Code

All settings in `config.py` with:
- Type annotations
- Sensible defaults
- Environment variable overrides
- Single source of truth

---

## Performance Considerations

### Ingestion Performance

**Bottlenecks** (in order):
1. **Embedding** - 90% of time
   - Solution: Use faster model (Ollama local)
   - Batch size optimization (handled by LangChain)

2. **File I/O** - 5% of time
   - Solution: Already uses efficient walking

3. **Chunking** - 5% of time
   - Negligible impact

**Optimization Tips**:
- Use Ollama for fast ingestion (no API limits)
- Incremental indexing (not yet implemented)
- Parallel embedding (ChromaDB handles this)

---

### Query Performance

**Latency Breakdown**:
- **Vector search**: ~10-50ms (fast)
- **LLM generation**: ~1-5s (slow)
  - OpenAI: 1-2s
  - Ollama: 2-5s (depends on model size)

**Optimization Tips**:
- Lower `RETRIEVER_K` (3 is optimal)
- Use smaller LLM (qwen2.5-coder:1.5b vs 13b)
- Reduce chunk overlap (less storage, similar quality)

---

### Memory Usage

**Ingestion**:
- Peak: ~500MB for 1000 files
- ChromaDB persists to disk (no memory overhead)

**Query**:
- Peak: ~200MB + model size
  - qwen2.5-coder:1.5b → ~2GB
  - deepseek-coder:6.7b → ~7GB

---

## Error Handling Strategies

### 1. Graceful Degradation

**Example**: File loading skips unreadable files
```python
try:
    content = filepath.read_text()
except Exception:
    skipped += 1
    continue
```

---

### 2. User-Friendly Messages

**Example**: Missing vector store
```python
raise FileNotFoundError(
    f"No vector store found at {persist_dir}. "
    "Run `python ingest.py <repo_path>` first."
)
```

---

### 3. Idempotent Operations

**Example**: Clearing vector store
```python
if not persist_dir.exists():
    return  # No-op if already cleared
```

---

### 4. Validation at Boundaries

**Example**: Provider validation
```python
if config.PROVIDER not in ("openai", "ollama"):
    raise ValueError(f"Unknown provider '{config.PROVIDER}'")
```

---

## Extension Points

### Adding a New LLM Provider

1. Add config variables to `config.py`:
```python
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet")
```

2. Extend `llm.py`:
```python
def get_llm():
    if config.PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(...)
```

3. Update documentation

---

### Adding New File Types

1. Add extensions to `config.INCLUDE_EXTENSIONS`:
```python
INCLUDE_EXTENSIONS = {
    # ... existing ...
    ".sol", ".vy",  # Solidity, Vyper
}
```

2. Add language detection to `loader.py`:
```python
ext_to_lang = {
    # ... existing ...
    ".sol": "solidity",
    ".vy": "vyper",
}
```

3. Add splitter support to `chunker.py` (if LangChain supports it)

---

### Custom Retrieval Strategies

Modify `retriever.py`:

```python
def get_retriever():
    store = load_vectorstore()
    
    # Custom retrieval logic
    return store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "score_threshold": 0.7,
            "k": 5,
        }
    )
```

---

## Testing Strategy (Not Implemented)

### Recommended Test Structure

```
tests/
├── test_config.py          # Config validation
├── test_loader.py          # File loading logic
├── test_chunker.py         # Chunking correctness
├── test_vectorstore.py     # DB operations
├── test_retriever.py       # Search quality
├── test_assistant.py       # RAG pipeline
└── fixtures/
    └── sample_repo/        # Test repository
```

### Key Test Scenarios

1. **Config**: Environment variable parsing
2. **Loader**: Filter logic, metadata extraction
3. **Chunker**: Chunk boundaries, overlap
4. **VectorStore**: CRUD operations
5. **Retriever**: Relevance, diversity
6. **Assistant**: End-to-end RAG flow

---

## Security Considerations

### 1. API Key Protection

- **Never commit `.env`** - already in `.gitignore`
- Use environment variables in production
- Rotate keys regularly

---

### 2. Input Validation

- File paths validated before reading
- User input not executed (no eval/exec)
- Git URLs sanitized by GitPython

---

### 3. Data Privacy

- Code indexed locally (ChromaDB persistence)
- OpenAI: Code sent to API (check terms)
- Ollama: Everything local (more private)

---

### 4. Dependency Security

- Pin versions in `requirements.txt`
- Regular `pip audit` checks
- Update dependencies for CVEs

---

## Troubleshooting Guide

### Common Issues

#### 1. "No vector store found"

**Cause**: Haven't run ingestion yet

**Solution**:
```bash
python ingest.py /path/to/repo
```

---

#### 2. "Failed to initialize assistant"

**Cause**: Ollama not running or wrong model

**Solution**:
```bash
# Start Ollama
ollama serve

# Pull model
ollama pull qwen2.5-coder:1.5b
ollama pull nomic-embed-text
```

---

#### 3. "OpenAI API Error"

**Cause**: Invalid API key or quota exceeded

**Solution**:
- Check `OPENAI_API_KEY` in `.env`
- Verify billing on OpenAI dashboard
- Switch to Ollama for free alternative

---

#### 4. "Git clone failed"

**Cause**: Invalid URL, auth required, or network issue

**Solution**:
- Verify URL is correct
- For private repos, use SSH or token auth
- Check network/firewall

---

#### 5. "ChromaDB collection already exists"

**Cause**: Re-running ingestion without `--force`

**Solution**:
```bash
python ingest.py /path/to/repo --force
```

---

## Future Improvements

### Potential Enhancements

1. **Incremental Indexing**: Only re-index changed files
2. **Multi-Repository Support**: Index multiple repos simultaneously
3. **Code Execution**: Run code snippets in sandbox
4. **Graph-Based RAG**: Use call graphs for better context
5. **Semantic Caching**: Cache common queries
6. **Web UI**: Browser-based interface
7. **IDE Integration**: VS Code extension
8. **Streaming Responses**: Real-time LLM output
9. **Custom Embeddings**: Fine-tuned models for code
10. **Analytics**: Query logs and improvement tracking

---

## Appendix: File Statistics

| File | Lines | Functions/Classes | Purpose |
|------|-------|-------------------|---------|
| config.py | 47 | 0 / 0 | Configuration |
| embeddings.py | 33 | 1 / 0 | Embedding factory |
| llm.py | 37 | 1 / 0 | LLM factory |
| loader.py | 142 | 5 / 0 | File loading |
| chunker.py | 80 | 3 / 0 | Code chunking |
| vectorstore.py | 78 | 3 / 0 | Vector DB ops |
| retriever.py | 25 | 1 / 0 | Search logic |
| assistant.py | 108 | 2 / 1 | RAG orchestration |
| ingest.py | 159 | 2 / 0 | Ingestion CLI |
| cli.py | 185 | 2 / 0 | Interactive UI |
| **Total** | **894** | **20 / 1** | **Full system** |

---

**Document Version**: 1.0  
**Last Updated**: {{ current_date }}  
**Project**: Repo Analyzer - AI Coding Assistant  
**Author**: Auto-generated documentation
