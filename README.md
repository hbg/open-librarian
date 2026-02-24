# OpenLibrarian

Turn any folder of documents into a searchable knowledge base that AI assistants can query directly. Point it at your docs, run two commands, and Claude (or any MCP client) can search them.

RAG shouldn't be a moat. This makes it a 3-command setup.

## How it works

```
Your documents (local folder, S3 bucket)
        ↓
   openlibrarian sync     ← parses, chunks, embeds, indexes
        ↓
   Local vector index     ← stored at ~/.openlibrarian/index/
        ↓
   openlibrarian serve    ← starts MCP server
        ↓
   Claude / Cursor / any MCP client can search your docs
```

No infrastructure to manage. No database to run. Everything lives on your machine.

## Quickstart

### 1. Install

```bash
pip install openlibrarian
```

You'll also need an OpenAI API key for embeddings. You can either set it as an environment variable:

```bash
export OPENAI_API_KEY="sk-..."
```

Or add it to your config file after running `openlibrarian init` (see [Configuration](#configuration)).

### 2. Set up

```bash
openlibrarian init
```

This walks you through an interactive setup. It'll ask for your document source (local folder or S3 bucket) and save a config file to `~/.openlibrarian/config.yaml`.

### 3. Index your documents

```bash
openlibrarian sync
```

This pulls your documents, parses them (PDF, DOCX, PPTX, HTML, Markdown, plain text), splits them into chunks, generates embeddings, and stores everything in a local vector index.

Sync is incremental — run it again and it only processes files that changed.

### 4. Start the MCP server

```bash
openlibrarian serve
```

That's it. Now connect an MCP client.

## Connecting MCP clients

OpenLibrarian runs as a **stdio MCP server** — the standard way for local MCP tools to communicate. Here's how to connect it from each client.

### Claude Desktop

Add this to your Claude Desktop config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "openlibrarian": {
      "command": "openlibrarian",
      "args": ["serve"]
    }
  }
}
```

Restart Claude Desktop. You'll see OpenLibrarian's tools (search, list_sources, get_document_context) available in the tools menu.

### Claude Code

Add it to your project settings (`.claude/settings.json`) or global settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "openlibrarian": {
      "command": "openlibrarian",
      "args": ["serve"]
    }
  }
}
```

Or add it from the CLI:

```bash
claude mcp add openlibrarian -- openlibrarian serve
```

### Cursor

Go to **Cursor Settings > MCP** and add a new server:

- **Name:** `openlibrarian`
- **Type:** `stdio`
- **Command:** `openlibrarian serve`

### Other MCP clients

Any MCP client that supports stdio transport can connect. The server command is:

```bash
openlibrarian serve
```

If your client needs a full path to the binary, use:

```bash
which openlibrarian
```

If you installed into a virtualenv, point to the full path:

```json
{
  "mcpServers": {
    "openlibrarian": {
      "command": "/path/to/your/venv/bin/openlibrarian",
      "args": ["serve"]
    }
  }
}
```

## What your AI assistant can do

Once connected, your assistant gets three tools:

| Tool | What it does |
|------|-------------|
| **search** | Semantic search across all your indexed documents. Ask a question in plain English, get the most relevant chunks back. |
| **list_sources** | See every document in the index — useful for asking "what do we have?" |
| **get_document_context** | Pull extended context from a specific document or section — great for diving deeper after a search result. |

You don't need to call these tools yourself. Just ask your assistant questions and it will use them automatically:

> "What does our onboarding guide say about setting up SSH keys?"
>
> "Summarize the key points from the Q4 report."
>
> "What documents do we have about deployment?"

## Supported document types

OpenLibrarian uses [docling](https://github.com/DS4SD/docling) for parsing, which handles:

- **PDF** (including scanned documents with OCR)
- **DOCX** (Word documents)
- **PPTX** (PowerPoint presentations)
- **HTML**
- **Markdown** (.md)
- **Plain text** (.txt)

Markdown and plain text files are parsed directly without docling for speed.

## Document sources

### Local folder

Point it at any directory on your machine:

```bash
openlibrarian init
# Choose "local", enter the path to your docs folder
```

### S3 bucket

Point it at an S3 bucket (uses your existing AWS credentials):

```bash
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."

openlibrarian init
# Choose "s3", enter bucket name and optional prefix
```

Credentials are **never** stored in the config file. They're read from environment variables or `~/.aws/credentials`, just like the AWS CLI.

## Configuration

Config lives at `~/.openlibrarian/config.yaml`. You can edit it directly:

```yaml
source:
  type: local
  path: /Users/you/Documents/company-docs

embeddings:
  provider: openai
  model: text-embedding-3-small
  api_key: sk-...            # optional — can also use OPENAI_API_KEY env var

chunking:
  strategy: semantic       # or "recursive"
  max_tokens: 512
  overlap_tokens: 50

server:
  transport: stdio

index:
  path: ~/.openlibrarian/index/
```

Use `--config` / `-c` with any command to use a different config file:

```bash
openlibrarian sync -c ~/my-other-config.yaml
```

## Security design

The MCP server has **zero access to your credentials**. It only reads the local vector index. This means:

- No API keys or AWS secrets are passed to MCP clients
- The server can't access your document sources directly
- Client configs contain no sensitive information

Sync and serving are deliberately separated. Sync knows about your credentials and writes to the index. The server only reads from the index.

## Development

```bash
git clone https://github.com/your-org/openlibrarian.git
cd openlibrarian
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/
```

## License

MIT
