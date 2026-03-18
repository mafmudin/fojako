# Kotlin MCP

Local MCP server that summarizes Kotlin and Java source files into compact structural representations, so AI agents consume fewer tokens when understanding a codebase.

## Tech Stack

- **Language**: Python 3.11+
- **MCP SDK**: `mcp[cli]` (official Anthropic)
- **Parser**: `tree-sitter` with `tree-sitter-kotlin` and `tree-sitter-java`
- **Package manager**: `uv`

## Installation

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install as global CLI tool
uv tool install .
```

After installation, `kotlin-mcp` is available globally from any terminal.

## MCP Tools

### `summarize_file_tool`

Summarize a single `.kt` or `.java` file into its structural representation.

**Input:**
```json
{ "path": "/absolute/path/to/File.kt" }
```

**Output:**
```
File: UserRepository.kt
Package: com.example.data.repository

Classes:
  @Inject class UserRepository(
    private val dao: UserDao,
    private val api: ApiService
  )
    + suspend getUser(id: String): Flow<User>
    + suspend updateUser(user: User): Result<Unit>
    - buildQuery(filter: Filter): Query  ← private

Imports (external):
  - kotlinx.coroutines.flow.Flow
  - javax.inject.Inject
```

### `summarize_module_tool`

Recursively summarize all `.kt` and `.java` files under a directory.

**Input:**
```json
{
  "path": "/absolute/path/to/module/",
  "depth": 2
}
```

- `depth`: directory levels to recurse (default: unlimited)

**Output:** Per-file summaries grouped by package, plus a module-level overview.

## Register with Claude Code

```bash
claude mcp add kotlin-summarizer -- kotlin-mcp
```

## Skipped Files

- Generated files: `BuildConfig.kt`, `R.java`, `*Binding.kt`
- Test files: `*Test.kt`, `*Spec.kt`, `*Test.java`, `*Spec.java`
