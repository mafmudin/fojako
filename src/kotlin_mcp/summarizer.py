import logging
import os
from pathlib import Path

from .parsers.base import FileSummary, ClassInfo, FunctionInfo
from .parsers.kotlin import KotlinParser
from .parsers.java import JavaParser

logger = logging.getLogger(__name__)

SKIP_PATTERNS = {"BuildConfig.kt", "R.java", "BR.java"}
SKIP_SUFFIXES = {"Binding.kt", "Binding.java"}
SKIP_TEST_SUFFIXES = {"Test.kt", "Test.java", "Spec.kt", "Spec.java"}

_kotlin_parser = KotlinParser()
_java_parser = JavaParser()


def summarize_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"Error: file not found: {path}"
    if not p.suffix in (".kt", ".java"):
        return f"Error: unsupported file type: {p.suffix}"

    source = p.read_text(encoding="utf-8", errors="replace")
    parser = _kotlin_parser if p.suffix == ".kt" else _java_parser
    summary = parser.parse(source, file_name=p.name)
    return _format_summary(summary)


def summarize_module(path: str, depth: int | None = None) -> str:
    root = Path(path)
    if not root.exists():
        return f"Error: directory not found: {path}"
    if not root.is_dir():
        return f"Error: not a directory: {path}"

    files = _collect_files(root, depth)
    if not files:
        return f"No .kt or .java files found under {path}"

    # Group by package
    summaries: list[FileSummary] = []
    for f in sorted(files):
        source = f.read_text(encoding="utf-8", errors="replace")
        parser = _kotlin_parser if f.suffix == ".kt" else _java_parser
        summaries.append(parser.parse(source, file_name=f.name))

    packages: dict[str, list[str]] = {}
    for s in summaries:
        pkg = s.package or "(default)"
        packages.setdefault(pkg, []).append(s.file_name)

    lines: list[str] = []
    lines.append(f"Module: {root.name} ({len(summaries)} files)")
    lines.append("")
    lines.append("Packages:")
    for pkg, file_names in sorted(packages.items()):
        lines.append(f"  {pkg} ({len(file_names)} files)")
        for fn in sorted(file_names):
            lines.append(f"    - {fn}")
    lines.append("")
    lines.append("--- Per-file summaries below ---")
    lines.append("")

    for s in summaries:
        lines.append(_format_summary(s))
        lines.append("")

    output = "\n".join(lines)
    _auto_save(root, output)
    return output


def _auto_save(root: Path, output: str) -> None:
    """Save summary to .kotlin-summary/{module_name}.md inside the target directory."""
    try:
        summary_dir = root / ".kotlin-summary"
        summary_dir.mkdir(exist_ok=True)
        dest = summary_dir / f"{root.name}.md"
        dest.write_text(output, encoding="utf-8")
        logger.info("Summary saved to %s", dest)
    except OSError as e:
        logger.warning("Failed to save summary to %s: %s", root / ".kotlin-summary", e)


def _collect_files(root: Path, depth: int | None) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip our own output directory
        if ".kotlin-summary" in dirnames:
            dirnames.remove(".kotlin-summary")

        if depth is not None:
            rel = Path(dirpath).relative_to(root)
            if len(rel.parts) >= depth:
                dirnames.clear()
                continue

        for fname in filenames:
            if fname in SKIP_PATTERNS:
                continue
            if any(fname.endswith(s) for s in SKIP_SUFFIXES):
                continue
            if any(fname.endswith(s) for s in SKIP_TEST_SUFFIXES):
                continue
            if fname.endswith(".kt") or fname.endswith(".java"):
                files.append(Path(dirpath) / fname)
    return files


def _format_summary(s: FileSummary) -> str:
    lines: list[str] = []
    lines.append(f"File: {s.file_name}")
    if s.package:
        lines.append(f"Package: {s.package}")

    if s.has_syntax_errors:
        lines.append(f"⚠ Syntax errors detected ({len(s.error_snippets)})")

    if s.classes:
        lines.append("")
        lines.append("Classes:")
        for cls in s.classes:
            lines.append(_format_class(cls))

    if s.top_level_functions:
        lines.append("")
        lines.append("Functions:")
        for fn in s.top_level_functions:
            lines.append(_format_function(fn, indent="  "))

    ext_imports = [i for i in s.imports if not i.startswith(s.package + ".") if s.package]
    if ext_imports:
        lines.append("")
        lines.append("Imports (external):")
        for imp in ext_imports:
            lines.append(f"  - {imp}")

    return "\n".join(lines)


def _format_class(cls: ClassInfo) -> str:
    lines: list[str] = []
    ann = " ".join(cls.annotations)
    header = f"  {ann + ' ' if ann else ''}{cls.kind} {cls.name}"
    if cls.constructor_params:
        header += "("
        lines.append(header)
        for i, p in enumerate(cls.constructor_params):
            comma = "," if i < len(cls.constructor_params) - 1 else ""
            lines.append(f"    {p}{comma}")
        lines.append("  )")
    else:
        lines.append(header)

    for fn in cls.functions:
        lines.append(_format_function(fn, indent="    "))

    return "\n".join(lines)


def _format_function(fn: FunctionInfo, indent: str = "  ") -> str:
    prefix = "-" if fn.is_private else "+"
    suspend = "suspend " if fn.is_suspend else ""
    ann = " ".join(fn.annotations)
    ann_str = f"{ann} " if ann else ""
    params_str = ", ".join(fn.params)
    ret = f": {fn.return_type}" if fn.return_type else ""
    private_mark = "  ← private" if fn.is_private else ""
    return f"{indent}{prefix} {ann_str}{suspend}{fn.name}({params_str}){ret}{private_mark}"
