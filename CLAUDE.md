# CLAUDE.md — OpenLibrarian

## What is OpenLibrarian?

OpenLibrarian is an open-source, MCP-native document retrieval service. Users point it at a document source (S3 bucket, GCS, local directory), and it automatically syncs, parses, chunks, embeds, and indexes those documents. It then exposes a Model Context Protocol (MCP) server that any MCP client (Claude Desktop, Claude Code, Cursor, custom agents) can use to search and retrieve document content.

**Design philosophy:** Minimal config, zero infrastructure, maximum utility. Two commands to go from "I have docs in S3" to "Claude can search them."

```bash
pip install openlibrarian
openlibrarian init        # interactive setup → writes config
openlibrarian sync        # pull, parse, chunk, embed → local index
openlibrarian serve       # start MCP server
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Document Sources                       │
│  ┌─────────┐  ┌─────────┐  ┌───────────┐               │
│  │   S3    │  │   GCS   │  │  Local FS │  (+ more)     │
│  └────┬────┘  └────┬────┘  └─────┬─────┘               │
│       └────────────┼─────────────┘                       │
│                    ▼                                      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              Sync Engine                             │ │
│  │  - Pulls new/changed/deleted files                  │ │
│  │  - Tracks file hashes for incremental sync          │ │
│  │  - Supports polling interval or one-shot            │ │
│  └──────────────────────┬──────────────────────────────┘ │
│                         ▼                                 │
│  ┌─────────────────────────────────────────────────────┐ │
│  │            Ingestion Pipeline                        │ │
│  │  1. Parse: docling (PDF, DOCX, PPTX, HTML, MD, TXT)│ │
│  │  2. Chunk: semantic (structure-aware) or recursive   │ │
│  │  3. Embed: OpenAI or local sentence-transformers     │ │
│  └──────────────────────┬──────────────────────────────┘ │
│                         ▼                                 │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              Vector Store (LanceDB)                  │ │
│  │  - Embedded, no server required                     │ │
│  │  - Stored at ~/.openlibrarian/index/                │ │
│  │  - Supports local disk or S3-backed (enterprise)    │ │
│  └──────────────────────┬──────────────────────────────┘ │
│                         ▼                                 │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              MCP Server                              │ │
│  │  - Exposes: search, list_sources, get_document_ctx  │ │
│  │  - Transport: stdio (local) or SSE (remote/team)    │ │
│  │  - Reads only from local index — no credentials     │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Key Separation of Concerns

- **Sync/Indexing** knows about document sources and credentials. It writes to the local index.
- **MCP Server** knows only about the local index directory. It has zero credential awareness. This means no tokens or secrets leak into MCP client configs.

## Project Structure

```
openlibrarian/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── LICENSE                      # MIT
│
├── src/
│   └── openlibrarian/
│       ├── __init__.py
│       ├── cli.py               # CLI entrypoint (Click/Typer)
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── models.py        # Pydantic config models
│       │   └── loader.py        # Load/write ~/.openlibrarian/config.yaml
│       │
│       ├── sources/             # Document source connectors
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract base: list_files, download_file, get_hash
│       │   ├── s3.py            # S3 source (boto3)
│       │   ├── gcs.py           # GCS source (google-cloud-storage) — v1.1
│       │   └── local.py         # Local filesystem source
│       │
│       ├── sync/                # Sync engine
│       │   ├── __init__.py
│       │   └── engine.py        # Incremental sync: hash tracking, add/update/delete
│       │
│       ├── pipeline/            # Ingestion pipeline
│       │   ├── __init__.py
│       │   ├── parser.py        # Document parsing (docling)
│       │   ├── chunker.py       # Chunking strategies (semantic + recursive fallback)
│       │   └── embedder.py      # Embedding (OpenAI API / sentence-transformers)
│       │
│       ├── store/               # Vector store
│       │   ├── __init__.py
│       │   └── lancedb.py       # LanceDB read/write operations
│       │
│       └── server/              # MCP server
│           ├── __init__.py
│           └── mcp.py           # MCP tool definitions and server setup
│
├── tests/
│   ├── conftest.py
│   ├── test_sources/
│   ├── test_sync/
│   ├── test_pipeline/
│   ├── test_store/
│   └── test_server/
│
└── examples/
    ├── claude_desktop_config.json
    └── sample_config.yaml
```

## Tech Stack

| Component         | Library                          | Why                                                      |
| ----------------- | -------------------------------- | -------------------------------------------------------- |
| CLI               | `typer`                          | Clean CLI with type hints, auto-generated help            |
| Config            | `pydantic` + `pyyaml`           | Validated config models, YAML serialization               |
| Document parsing  | `docling`                        | Best OSS doc parser — PDF, DOCX, PPTX, HTML, MD, tables |
| Chunking          | Custom (structure-aware)         | Use docling's document structure for semantic splits      |
| Embeddings        | `openai` / `sentence-transformers` | OpenAI for simplicity, local for privacy                |
| Vector store      | `lancedb`                        | Embedded (no server), fast, Arrow-native, S3-compatible  |
| MCP server        | `mcp` (official Python SDK)      | Standard MCP protocol implementation                     |
| S3 access         | `boto3`                          | AWS standard                                             |
| Hashing           | `hashlib` (stdlib)               | Track file changes for incremental sync                  |

## Config

Default location: `~/.openlibrarian/config.yaml`

```yaml
# Document source
source:
  type: s3                    # s3 | gcs | local
  bucket: my-company-docs
  prefix: ""                  # optional: only index docs under this prefix
  region: us-west-2
  # Credentials: uses AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY env vars,
  # or ~/.aws/credentials profile. NO credentials stored in config file.

# Embedding configuration
embeddings:
  provider: openai            # openai | local
  model: text-embedding-3-small  # only for openai
  # API key: uses OPENAI_API_KEY env var. NOT stored in config.

# Chunking configuration
chunking:
  strategy: semantic          # semantic | recursive
  max_tokens: 512
  overlap_tokens: 50

# Server configuration
server:
  transport: stdio            # stdio | sse
  host: 127.0.0.1            # only for sse
  port: 8080                  # only for sse
  token: null                 # optional: bearer token for sse mode

# Index location
index:
  path: ~/.openlibrarian/index/
```

## MCP Tools Exposed

### `search`
Semantic search over all indexed documents.

```json
{
  "name": "search",
  "description": "Search indexed documents using natural language queries.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "Natural language search query" },
      "top_k": { "type": "integer", "default": 5, "description": "Number of results to return" },
      "source_filter": { "type": "string", "description": "Optional: filter by source filename or path glob" }
    },
    "required": ["query"]
  }
}
```

Returns: Array of chunks with content, source file, page/section, relevance score.

### `list_sources`
List all indexed documents with metadata.

```json
{
  "name": "list_sources",
  "description": "List all documents in the index with metadata.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "prefix": { "type": "string", "description": "Optional: filter by path prefix" }
    }
  }
}
```

Returns: Array of documents with filename, path, size, last modified, chunk count.

### `get_document_context`
Get broader context from a specific document (useful after search to expand around a result).

```json
{
  "name": "get_document_context",
  "description": "Retrieve extended context from a specific document section.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "source": { "type": "string", "description": "Document path/filename" },
      "section": { "type": "string", "description": "Optional: section heading to focus on" },
      "chunk_id": { "type": "string", "description": "Optional: expand context around this chunk" }
    },
    "required": ["source"]
  }
}
```

## Deployment Modes

### Local (MVP — build this first)
- Everything runs on the user's machine
- Index stored at `~/.openlibrarian/index/`
- MCP transport: stdio
- No auth needed
- Target: individual developers

### Team (v2)
- Server runs on shared infra (VM, container, internal server)
- Index on local disk or shared volume
- MCP transport: SSE over HTTP
- Auth: bearer token via env var
- Target: small teams (5-50 people)

### Enterprise (v2+)
- Managed sync (cron, Lambda, or daemon)
- Index backed by S3 (LanceDB supports this natively)
- Auth: OIDC/SSO integration
- Target: organizations

## Development Guidelines

### Code Style
- Python 3.11+
- Type hints everywhere — use Pydantic models for data structures
- Use `ruff` for linting and formatting
- Docstrings on all public functions (Google style)
- Keep modules focused — each file should do one thing

### Error Handling
- Use custom exception hierarchy rooted at `OpenLibrarianError`
- Never swallow exceptions silently
- Provide actionable error messages (e.g., "AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or configure an AWS profile.")

### Testing
- Use `pytest` with `pytest-asyncio` for async tests
- Mock external services (S3, OpenAI) in unit tests
- Use temp directories for index tests
- Aim for high coverage on the pipeline and sync engine — these are where bugs hide

### Abstractions
The source, embedder, and store layers use abstract base classes so backends can be swapped:

```python
# sources/base.py
class DocumentSource(ABC):
    @abstractmethod
    async def list_files(self) -> list[FileMetadata]: ...
    @abstractmethod
    async def download_file(self, path: str, dest: Path) -> None: ...
    @abstractmethod
    async def get_file_hash(self, path: str) -> str: ...

# pipeline/embedder.py
class Embedder(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

# store/base.py (if needed later)
class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, chunks: list[Chunk]) -> None: ...
    @abstractmethod
    async def search(self, query_vector: list[float], top_k: int) -> list[SearchResult]: ...
```

### Commit Convention
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Keep commits atomic — one logical change per commit

## Build Order (Priority)

### Phase 1: MVP — Local end-to-end
1. **Project scaffolding** — pyproject.toml, package structure, CLI skeleton with typer
2. **Config system** — Pydantic models, YAML load/save, `openlibrarian init` command
3. **Local source** — implement `DocumentSource` for local filesystem (easiest to test with)
4. **S3 source** — implement `DocumentSource` for S3 with boto3
5. **Parser** — docling integration, extract text + structure from supported file types
6. **Chunker** — semantic chunking using docling's structure, recursive fallback
7. **Embedder** — OpenAI embeddings via API
8. **LanceDB store** — write chunks + vectors, search by vector similarity
9. **Sync engine** — hash tracking, incremental add/update/delete, `openlibrarian sync` command
10. **MCP server** — expose `search`, `list_sources`, `get_document_context` via stdio
11. **Integration test** — end-to-end: local dir with sample docs → sync → search via MCP

### Phase 2: Polish
- Local embedding support (sentence-transformers)
- Better chunking heuristics (table handling, code blocks)
- `--watch` mode for continuous sync
- Progress bars and better CLI output
- Comprehensive error messages
- README with quickstart guide

### Phase 3: Team/Enterprise
- SSE transport for remote MCP serving
- Bearer token auth
- S3-backed LanceDB index
- Docker image
- Managed sync daemon mode

## Quick Reference: Key Decisions

| Decision               | Choice                    | Rationale                                                    |
| ---------------------- | ------------------------- | ------------------------------------------------------------ |
| Language               | Python                    | Best ecosystem for ML/embeddings, MCP SDK available          |
| Vector DB              | LanceDB (embedded)        | Zero infra, fast, supports S3 backend for scale-out          |
| Doc parser             | docling                   | Best OSS option, structure-aware, handles most formats       |
| Default embeddings     | OpenAI text-embedding-3-small | Cheap ($0.02/1M tokens), high quality, most users have key |
| Config format          | YAML                      | Human-readable, standard for CLI tools                       |
| MCP SDK                | `mcp` (Python, official)  | First-party, well-maintained                                 |
| CLI framework          | Typer                     | Modern, type-hint-driven, auto help generation               |
| No credentials in MCP  | By design                 | MCP server reads local index only — clean separation         |
