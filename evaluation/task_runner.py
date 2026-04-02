"""RQ2: Task-based evaluation harness.

Runs tasks against Claude API under three conditions:
  1. Full Code — all source files as context
  2. Summary Only — structural summaries from kotlin-mcp
  3. Summary + On-demand — summary first, can request specific files

Usage:
    uv run python evaluation/task_runner.py \
        --tasks evaluation/tasks_instantiated.json \
        --datasets evaluation/datasets.json \
        --output evaluation/results/rq2_responses.json \
        --condition full|summary|hybrid \
        --model claude-sonnet-4-20250514
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import anthropic

from kotlin_mcp.summarizer import summarize_module, _collect_files

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are evaluating a Kotlin/Java codebase. Answer the question based only on the provided context.
Be specific: mention exact class names, file names, package names, and method signatures when relevant.
If the provided context is insufficient to answer, say so explicitly and explain what information is missing."""

MAX_CONTEXT_TOKENS = 180_000  # Leave room for response


def load_full_source(project_path: Path) -> str:
    """Load all .kt/.java source files as a single string."""
    files = _collect_files(project_path, depth=None)
    parts = []
    for f in sorted(files):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            rel = f.relative_to(project_path)
            parts.append(f"=== {rel} ===\n{content}")
        except Exception as e:
            logger.warning("Failed to read %s: %s", f, e)
    return "\n\n".join(parts)


def load_summary(project_path: Path) -> str:
    """Generate structural summary for the project."""
    return summarize_module(str(project_path))


def run_task_full(
    client: anthropic.Anthropic,
    model: str,
    question: str,
    source_context: str,
) -> dict:
    """Condition 1: Full source code as context."""
    messages = [
        {
            "role": "user",
            "content": f"Here is the full source code of the project:\n\n{source_context}\n\n---\n\nQuestion: {question}",
        }
    ]
    return _call_api(client, model, messages)


def run_task_summary(
    client: anthropic.Anthropic,
    model: str,
    question: str,
    summary_context: str,
) -> dict:
    """Condition 2: Summary only as context."""
    messages = [
        {
            "role": "user",
            "content": f"Here is a structural summary of the project (signatures, classes, methods — no implementation bodies):\n\n{summary_context}\n\n---\n\nQuestion: {question}",
        }
    ]
    return _call_api(client, model, messages)


def run_task_hybrid(
    client: anthropic.Anthropic,
    model: str,
    question: str,
    summary_context: str,
    project_path: Path,
) -> dict:
    """Condition 3: Summary first, then allow requesting specific files.

    Uses a two-turn conversation:
    1. Provide summary + question, ask LLM if it needs any full files
    2. If it requests files, provide them and re-ask
    """
    messages = [
        {
            "role": "user",
            "content": (
                f"Here is a structural summary of the project (signatures, classes, methods — no implementation bodies):\n\n"
                f"{summary_context}\n\n---\n\n"
                f"Question: {question}\n\n"
                f"If you need to see the full source of specific files to answer accurately, "
                f"list them as: REQUEST_FILES: file1.kt, file2.java\n"
                f"Otherwise, answer the question directly."
            ),
        }
    ]

    result = _call_api(client, model, messages)

    # Check if the model requested files
    response_text = result["response"]
    if "REQUEST_FILES:" in response_text:
        requested_line = ""
        for line in response_text.split("\n"):
            if "REQUEST_FILES:" in line:
                requested_line = line.split("REQUEST_FILES:")[-1].strip()
                break

        if requested_line:
            requested_files = [f.strip() for f in requested_line.split(",")]
            file_contents = _load_requested_files(project_path, requested_files)

            messages.append({"role": "assistant", "content": response_text})
            messages.append(
                {
                    "role": "user",
                    "content": f"Here are the requested files:\n\n{file_contents}\n\nNow please answer the original question: {question}",
                }
            )

            result2 = _call_api(client, model, messages)
            # Combine token usage
            result2["input_tokens"] += result["input_tokens"]
            result2["output_tokens"] += result["output_tokens"]
            result2["files_requested"] = requested_files
            result2["turns"] = 2
            return result2

    result["files_requested"] = []
    result["turns"] = 1
    return result


def _load_requested_files(project_path: Path, file_names: list[str]) -> str:
    """Find and load specific files by name from the project."""
    parts = []
    all_files = _collect_files(project_path, depth=None)
    file_map = {f.name: f for f in all_files}

    for name in file_names:
        name = name.strip()
        if name in file_map:
            try:
                content = file_map[name].read_text(encoding="utf-8", errors="replace")
                rel = file_map[name].relative_to(project_path)
                parts.append(f"=== {rel} ===\n{content}")
            except Exception as e:
                parts.append(f"=== {name} === (error: {e})")
        else:
            parts.append(f"=== {name} === (file not found)")

    return "\n\n".join(parts)


def _call_api(
    client: anthropic.Anthropic,
    model: str,
    messages: list[dict],
) -> dict:
    """Call Claude API and return response with token usage."""
    start = time.time()
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    elapsed = time.time() - start

    return {
        "response": response.content[0].text,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "latency_seconds": round(elapsed, 2),
        "model": model,
        "stop_reason": response.stop_reason,
    }


def main():
    parser = argparse.ArgumentParser(description="RQ2 task-based evaluation")
    parser.add_argument(
        "--tasks",
        type=str,
        required=True,
        help="Path to instantiated tasks JSON",
    )
    parser.add_argument(
        "--datasets",
        type=str,
        default="evaluation/datasets.json",
        help="Path to datasets JSON",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation/results/rq2_responses.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--condition",
        type=str,
        choices=["full", "summary", "hybrid"],
        required=True,
        help="Experiment condition",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-20250514",
        help="Claude model to use",
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Run only for a specific project name (optional)",
    )
    args = parser.parse_args()

    client = anthropic.Anthropic()

    with open(args.tasks) as f:
        tasks_data = json.load(f)

    with open(args.datasets) as f:
        datasets = json.load(f)

    project_map = {p["name"]: Path(p["path"]).expanduser() for p in datasets["projects"]}

    results = []
    tasks = tasks_data["tasks"]

    for task in tasks:
        project_name = task["project"]
        if args.project and project_name != args.project:
            continue

        project_path = project_map.get(project_name)
        if not project_path or not project_path.exists():
            logger.warning("Project %s not found, skipping", project_name)
            continue

        question = task["question"]
        task_id = task["id"]
        logger.info("Running task %s [%s] on project %s", task_id, args.condition, project_name)

        try:
            if args.condition == "full":
                source = load_full_source(project_path)
                result = run_task_full(client, args.model, question, source)
            elif args.condition == "summary":
                summary = load_summary(project_path)
                result = run_task_summary(client, args.model, question, summary)
            elif args.condition == "hybrid":
                summary = load_summary(project_path)
                result = run_task_hybrid(
                    client, args.model, question, summary, project_path
                )

            results.append(
                {
                    "task_id": task_id,
                    "project": project_name,
                    "category": task["category"],
                    "question": question,
                    "condition": args.condition,
                    **result,
                }
            )

        except Exception as e:
            logger.error("Error on task %s: %s", task_id, e)
            results.append(
                {
                    "task_id": task_id,
                    "project": project_name,
                    "category": task["category"],
                    "question": question,
                    "condition": args.condition,
                    "error": str(e),
                }
            )

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Append to existing results if file exists
    existing = []
    if output_path.exists():
        with open(output_path) as f:
            existing = json.load(f)

    existing.extend(results)
    with open(output_path, "w") as f:
        json.dump(existing, f, indent=2)

    logger.info("Saved %d results to %s", len(results), output_path)

    # Print token usage summary
    total_input = sum(r.get("input_tokens", 0) for r in results)
    total_output = sum(r.get("output_tokens", 0) for r in results)
    print(f"\n=== Token Usage ({args.condition}) ===")
    print(f"Tasks run: {len(results)}")
    print(f"Total input tokens:  {total_input:,}")
    print(f"Total output tokens: {total_output:,}")


if __name__ == "__main__":
    main()
