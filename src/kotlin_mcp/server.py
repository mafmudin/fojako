from mcp.server.fastmcp import FastMCP

from .summarizer import summarize_file, summarize_module

mcp = FastMCP("kotlin-summarizer")


@mcp.tool()
def summarize_file_tool(path: str) -> str:
    """Summarize a single Kotlin or Java file into its structural representation.

    Args:
        path: Absolute path to a .kt or .java file.
    """
    return summarize_file(path)


@mcp.tool()
def summarize_module_tool(path: str, depth: int | None = None) -> str:
    """Recursively summarize all .kt and .java files under a directory.

    Args:
        path: Absolute path to the module directory.
        depth: How many directory levels to recurse (default: unlimited).
    """
    return summarize_module(path, depth)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
