# Kotlin MCP — Engineering Context

## Goal
Build a local MCP server that summarizes Kotlin and Java source files into
compact structural representations, so AI agents consume less tokens when
understanding a codebase.

---

## Project Location
```
~/tools/kotlin-mcp
```

---

## Tech Stack
| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| MCP SDK | `mcp[cli]` (official Anthropic) |
| Parser | `tree-sitter`, `tree-sitter-kotlin`, `tree-sitter-java` |
| Package manager | `uv` |

---

## Project Structure
```
~/tools/kotlin-mcp/
├── pyproject.toml
├── README.md
├── .python-version          # 3.11
└── src/
    └── kotlin_mcp/
        ├── __init__.py
        ├── server.py        # MCP server entrypoint
        ├── summarizer.py    # Core summarization logic
        └── parsers/
            ├── __init__.py
            ├── base.py      # Abstract base parser
            ├── kotlin.py    # Kotlin-specific parser
            └── java.py      # Java-specific parser
```

---

## MCP Tools (v1)

### 1. `summarize_file`
Summarize a single Kotlin or Java file into its structural representation.

**Input:**
```json
{
  "path": "/absolute/path/to/File.kt"
}
```

**Output:**
```
File: UserRepository.kt
Package: com.example.data.repository

Classes:
  class UserRepository(
    private val dao: UserDao,
    private val api: ApiService
  )

Functions:
  + getUser(id: String): Flow<User>
  + updateUser(user: User): Result<Unit>
  - buildQuery(filter: Filter): Query   ← private

Imports (external):
  - kotlinx.coroutines.flow.Flow
  - javax.inject.Inject
```

### 2. `summarize_module`
Recursively summarize all `.kt` and `.java` files under a given directory path.

**Input:**
```json
{
  "path": "/absolute/path/to/module/",
  "depth": 2
}
```
- `depth`: how many directory levels to recurse (default: unlimited)

**Output:**
Per-file summaries grouped by package, plus a module-level overview:
```
Module: com.example.data (12 files)

Packages:
  com.example.data.repository (3 files)
    - UserRepository.kt
    - ProductRepository.kt
    - OrderRepository.kt
  com.example.data.model (5 files)
    ...

--- Per-file summaries below ---
[same format as summarize_file, repeated per file]
```

---

## Parser Contract

Each parser (Kotlin, Java) must implement `base.py`:

```python
class BaseParser:
    def parse(self, source: str) -> FileSummary:
        ...
```

`FileSummary` is a dataclass:
```python
@dataclass
class FileSummary:
    file_name: str
    package: str
    classes: list[ClassInfo]
    top_level_functions: list[FunctionInfo]
    imports: list[str]
    has_syntax_errors: bool = False          # flag if tree-sitter found errors
    error_snippets: list[str] = field(default_factory=list)  # snippet around error node

@dataclass
class ClassInfo:
    name: str
    kind: str              # class, data class, interface, object, enum
    constructor_params: list[str]
    functions: list[FunctionInfo]
    annotations: list[str]  # e.g. ["@Entity", "@Inject"]

@dataclass
class FunctionInfo:
    name: str
    params: list[str]
    return_type: str
    is_private: bool
    is_suspend: bool = False                 # coroutines support
    annotations: list[str] = field(default_factory=list)  # e.g. ["@GET", "@Override"]
```

---

## What to Extract (tree-sitter nodes)

### Kotlin
| Target | tree-sitter node |
|---|---|
| Package | `package_header` |
| Import | `import_header` |
| Class | `class_declaration` |
| Object | `object_declaration` |
| Interface | `class_declaration` (with `interface` modifier) |
| Data class | `class_declaration` (with `data` modifier) |
| Function | `function_declaration` |
| Constructor params | `primary_constructor` → `class_parameter` |

### Java
| Target | tree-sitter node |
|---|---|
| Package | `package_declaration` |
| Import | `import_declaration` |
| Class | `class_declaration` |
| Interface | `interface_declaration` |
| Method | `method_declaration` |
| Constructor | `constructor_declaration` |

---

## MCP Server Registration (Claude Code)

After project is built, register with:
```bash
claude mcp add kotlin-summarizer -- uv run --directory ~/tools/kotlin-mcp python -m kotlin_mcp.server
```

---

## Setup Steps for Claude Code to Execute

1. Verify `uv` is installed (`uv --version`), install if not:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Create project:
   ```bash
   mkdir -p ~/tools/kotlin-mcp
   cd ~/tools/kotlin-mcp
   uv init --python 3.11
   ```

3. Add dependencies:
   ```bash
   uv add "mcp[cli]" tree-sitter tree-sitter-kotlin tree-sitter-java
   ```

4. Implement files following structure above.

5. Test locally:
   ```bash
   uv run python -m kotlin_mcp.server
   ```

6. Register MCP:
   ```bash
   claude mcp add kotlin-summarizer -- uv run --directory ~/tools/kotlin-mcp python -m kotlin_mcp.server
   ```

---

## Out of Scope (v1)
- Filter by class type
- Dependency graph
- Incremental / watch mode
- Caching

## Notes
- Output is plain text, not JSON — optimized for LLM readability
- Private functions included but marked with `←  private`
- Skip generated files: `BuildConfig.kt`, `R.java`, `*Binding.kt`
- Skip test files by default (`*Test.kt`, `*Spec.kt`)
