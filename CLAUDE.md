# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**kotlin-mcp** is a local MCP (Model Context Protocol) server that summarizes Kotlin and Java source files into compact structural representations for AI agents. It uses tree-sitter for parsing and exposes two MCP tools: `summarize_file_tool` (single file) and `summarize_module_tool` (recursive directory).

## Tech Stack

- Python 3.11+, managed with `uv`
- MCP SDK: `mcp[cli]` (FastMCP)
- Parsing: `tree-sitter` with `tree-sitter-kotlin` and `tree-sitter-java`

## Common Commands

```bash
# Install dependencies
uv sync

# Run the MCP server locally
uv run python -m kotlin_mcp

# Install as global CLI tool
uv tool install .

# Run as global CLI (after install)
kotlin-mcp

# Register with Claude Code
claude mcp add kotlin-summarizer -- kotlin-mcp
```

## Architecture

The server entry point is `src/kotlin_mcp/server.py`, which uses FastMCP to register two tools that delegate to `summarizer.py`.

**Parsing pipeline:** `server.py` → `summarizer.py` → `parsers/{kotlin,java}.py` → `parsers/base.py`

- `parsers/base.py` — Dataclasses (`FileSummary`, `ClassInfo`, `FunctionInfo`) and abstract `BaseParser`
- `parsers/kotlin.py` — `KotlinParser`: extracts packages, imports, classes (data/enum/interface/object), functions (with suspend/annotation support)
- `parsers/java.py` — `JavaParser`: extracts packages, imports, classes/interfaces/enums, methods
- `summarizer.py` — Orchestrates parsing, file collection, formatting. Skips generated files (`BuildConfig`, `R.java`, `*Binding.*`) and test files (`*Test.*`, `*Spec.*`)
- `server.py` — FastMCP server with `summarize_file_tool` and `summarize_module_tool`

Output is plain text (not JSON), optimized for LLM readability. Private members are marked with `← private`.
