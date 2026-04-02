"""RQ1: Collect compression metrics across dataset projects.

Usage:
    uv run python evaluation/collect_metrics.py --datasets evaluation/datasets.json --output evaluation/results/rq1_metrics.csv

Walks each project directory, summarizes every .kt/.java file, and records
compression metrics to a CSV for analysis.
"""

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

# Add project root to path so we can import kotlin_mcp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kotlin_mcp.summarizer import (
    summarize_file,
    _collect_files,
    SKIP_PATTERNS,
    SKIP_SUFFIXES,
    SKIP_TEST_SUFFIXES,
)
from token_counter import compute_metrics, count_tokens_tiktoken

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CSV_HEADERS = [
    "project",
    "project_size_category",
    "file_path",
    "file_name",
    "language",
    "original_lines",
    "original_chars",
    "original_tokens",
    "summary_lines",
    "summary_chars",
    "summary_tokens",
    "compression_ratio",
    "token_reduction_rate",
    "structural_elements",
    "information_density",
    "num_classes",
    "num_functions",
]


def classify_project_size(file_count: int) -> str:
    if file_count < 50:
        return "small"
    elif file_count <= 200:
        return "medium"
    else:
        return "large"


def count_structural_from_source(source: str, suffix: str) -> tuple[int, int]:
    """Rough count of classes and functions from source for metadata."""
    num_classes = 0
    num_functions = 0
    for line in source.split("\n"):
        stripped = line.strip()
        if suffix == ".kt":
            if any(
                stripped.startswith(kw)
                for kw in [
                    "class ",
                    "data class ",
                    "interface ",
                    "object ",
                    "enum class ",
                    "sealed class ",
                    "abstract class ",
                    "open class ",
                    "internal class ",
                    "private class ",
                ]
            ):
                num_classes += 1
            if stripped.startswith("fun ") or " fun " in stripped:
                num_functions += 1
        else:  # .java
            if any(
                kw in stripped
                for kw in [
                    "class ",
                    "interface ",
                    "enum ",
                ]
            ):
                if not stripped.startswith("//") and not stripped.startswith("*"):
                    num_classes += 1
    return num_classes, num_functions


def process_project(
    project_name: str,
    project_path: Path,
    size_category: str,
) -> list[dict]:
    """Process all files in a project, return list of metric rows."""
    rows = []
    files = _collect_files(project_path, depth=None)
    logger.info(
        "Project %s: found %d files at %s", project_name, len(files), project_path
    )

    for file_path in sorted(files):
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            summary = summarize_file(str(file_path))

            if summary.startswith("Error:"):
                logger.warning("Skipping %s: %s", file_path, summary)
                continue

            metrics = compute_metrics(source, summary)
            num_classes, num_functions = count_structural_from_source(
                source, file_path.suffix
            )

            rows.append(
                {
                    "project": project_name,
                    "project_size_category": size_category,
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "language": "kotlin" if file_path.suffix == ".kt" else "java",
                    "num_classes": num_classes,
                    "num_functions": num_functions,
                    **metrics,
                }
            )
        except Exception as e:
            logger.error("Error processing %s: %s", file_path, e)

    return rows


def main():
    parser = argparse.ArgumentParser(description="Collect RQ1 compression metrics")
    parser.add_argument(
        "--datasets",
        type=str,
        default="evaluation/datasets.json",
        help="Path to datasets JSON file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation/results/rq1_metrics.csv",
        help="Output CSV path",
    )
    args = parser.parse_args()

    # Load dataset definitions
    with open(args.datasets) as f:
        datasets = json.load(f)

    all_rows = []
    for project in datasets["projects"]:
        project_path = Path(project["path"]).expanduser()
        if not project_path.exists():
            logger.warning("Project path not found, skipping: %s", project_path)
            continue

        files = _collect_files(project_path, depth=None)
        size_category = project.get(
            "size_category", classify_project_size(len(files))
        )

        rows = process_project(project["name"], project_path, size_category)
        all_rows.extend(rows)

    # Write CSV
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(all_rows)

    logger.info("Wrote %d rows to %s", len(all_rows), output_path)

    # Print summary
    if all_rows:
        tokens_orig = sum(r["original_tokens"] for r in all_rows)
        tokens_summ = sum(r["summary_tokens"] for r in all_rows)
        overall_cr = tokens_summ / tokens_orig if tokens_orig > 0 else 0
        print(f"\n=== Summary ===")
        print(f"Total files processed: {len(all_rows)}")
        print(f"Total original tokens: {tokens_orig:,}")
        print(f"Total summary tokens:  {tokens_summ:,}")
        print(f"Overall compression ratio: {overall_cr:.4f}")
        print(f"Overall token reduction:   {1 - overall_cr:.1%}")


if __name__ == "__main__":
    main()
