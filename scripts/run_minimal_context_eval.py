#!/usr/bin/env python3
"""Materialize and optionally run one minimal-context DeepSeek benchmark."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.materialize_minimal_context_smoke import (
    SelectedRecord,
    load_jsonl,
    materialize_smoke_project,
    select_records,
)
from scripts.review_minimal_context_records import DEFAULT_BASE_URL, build_evidence_bundle


DEFAULT_MODEL = "deepseek/deepseek-v4-pro"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def shell_join(parts: list[str]) -> str:
    return " ".join("'" + part.replace("'", "'\"'\"'") + "'" if any(ch.isspace() for ch in part) else part for part in parts)


def build_formalization_messages(record: SelectedRecord, evidence: dict[str, Any], target_lean: str) -> list[dict[str, str]]:
    system = (
        "You are a Lean 4 formalization agent working in a Mathlib-only benchmark project. "
        "Use the provided TeX snippets, file-scope Lean context, predecessor Lean snippets, "
        "and target skeleton to replace exactly one sorry. Return exactly one JSON object and no markdown."
    )
    schema = {
        "record_id": record.record_id,
        "lean_declaration": "complete replacement Lean declaration for the target, including the proof/body",
        "used_context": ["short list of TeX or Lean facts used"],
        "notes": ["short caveats, if any"],
    }
    user = (
        "Fill the target Lean declaration. The benchmark project imports Mathlib only by default, "
        "then inserts the recorded file context and predecessor snippets before this target.\n\n"
        f"Required JSON schema:\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n\n"
        f"Evidence bundle:\n{json.dumps(evidence, indent=2, ensure_ascii=False)}\n\n"
        f"Materialized target file:\n```lean\n{target_lean}\n```"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_openrouter_payload(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    reasoning_effort: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    if reasoning_effort:
        payload["extra_body"] = {"reasoning": {"effort": reasoning_effort, "exclude": True}}
    return payload


def review_command(args: argparse.Namespace, selected_records_path: Path, eval_dir: Path) -> str:
    command = [
        "uv",
        "run",
        "python",
        "scripts/review_minimal_context_records.py",
        "--records",
        str(selected_records_path),
        "--source-root",
        str(args.project_root),
        "--model",
        args.model,
        "--max-tokens",
        str(args.max_tokens),
        "--output",
        str(eval_dir / "deepseek-review.jsonl"),
        "--summary",
        str(eval_dir / "deepseek-review.md"),
        "--summary-title",
        "Minimal-Context DeepSeek Evaluation Review",
        "--limit",
        "1",
    ]
    if args.reasoning_effort:
        command.extend(["--reasoning-effort", args.reasoning_effort])
    return shell_join(command)


def materialize_eval(args: argparse.Namespace) -> dict[str, Path]:
    rows = load_jsonl(args.records)
    selected = select_records(rows, args.record_id, args.limit)
    if len(selected) != 1:
        raise ValueError("evaluation runner currently supports exactly one selected record")

    record = selected[0]
    materialize_smoke_project(
        args.project_root,
        args.output,
        selected,
        force=args.force,
        lake_cache_from=args.lake_cache_from,
        init_git=not args.no_git,
        use_record_imports=args.include_record_imports,
    )

    eval_dir = args.output / "eval"
    selected_records_path = eval_dir / "selected-record.jsonl"
    write_jsonl(selected_records_path, [record.row])

    evidence = build_evidence_bundle(
        record.row,
        source_base_url="https://example.invalid",
        cache_dir=None,
        source_root=args.project_root,
        source_context=args.source_context,
        lean_context=args.lean_context,
    )
    evidence_path = eval_dir / "evidence.json"
    write_json(evidence_path, evidence)

    target_lean_path = args.output / record.lean_path
    target_lean = target_lean_path.read_text(encoding="utf-8")
    messages = build_formalization_messages(record, evidence, target_lean)
    payload = build_openrouter_payload(
        model=args.model,
        messages=messages,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        reasoning_effort=args.reasoning_effort,
    )
    payload_path = eval_dir / "openrouter-formalization-payload.json"
    write_json(payload_path, payload)

    formalization_command = (
        "OPENROUTER_API_KEY=$OPENROUTER_API_KEY uv run python "
        "scripts/run_minimal_context_eval.py "
        f"--records {args.records} --project-root {args.project_root} --output {args.output} "
        f"--record-id {record.record_id} --force --call-openrouter --model {args.model} "
        f"--max-tokens {args.max_tokens}"
    )
    if args.reasoning_effort:
        formalization_command += f" --reasoning-effort {args.reasoning_effort}"
    (eval_dir / "openrouter-formalization-command.txt").write_text(formalization_command + "\n", encoding="utf-8")
    (eval_dir / "review-command.txt").write_text(review_command(args, selected_records_path, eval_dir) + "\n", encoding="utf-8")

    contents = [
        "# Minimal Context DeepSeek Eval",
        "",
        f"- Record: `{record.record_id}`",
        f"- Model: `{args.model}`",
        f"- Target file: `{target_lean_path.relative_to(args.output)}`",
        f"- Prompt payload: `{payload_path.relative_to(args.output)}`",
        f"- Evidence: `{evidence_path.relative_to(args.output)}`",
        "",
        "No OpenRouter call is made unless `--call-openrouter` is passed.",
    ]
    (eval_dir / "README.md").write_text("\n".join(contents) + "\n", encoding="utf-8")

    return {
        "eval_dir": eval_dir,
        "payload": payload_path,
        "evidence": evidence_path,
        "selected_records": selected_records_path,
        "target_lean": target_lean_path,
    }


def call_openrouter(payload_path: Path, output_path: Path) -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set; refusing to make a paid OpenRouter call")

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    extra_body = payload.pop("extra_body", None)
    if extra_body:
        payload["extra_body"] = extra_body
    client = OpenAI(base_url=DEFAULT_BASE_URL, api_key=api_key)
    response = client.chat.completions.create(**payload)
    content = response.model_dump(mode="json")
    content["recorded_at"] = datetime.now(timezone.utc).isoformat()
    write_json(output_path, content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=Path("docs/minimal-context-gold-candidates.jsonl"))
    parser.add_argument("--project-root", type=Path, default=Path("algebraic-combinatorics"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--record-id", action="append", default=[], help="Record id to materialize.")
    parser.add_argument("--limit", type=int, default=1, help="Number of auto-selected records. Must be 1.")
    parser.add_argument("--force", action="store_true", help="Overwrite the output directory.")
    parser.add_argument("--no-git", action="store_true", help="Do not initialize a git repository in the output.")
    parser.add_argument(
        "--lake-cache-from",
        type=Path,
        help="Optional Lean project whose .lake/packages directory should be symlinked.",
    )
    parser.add_argument(
        "--include-record-imports",
        action="store_true",
        help="Import the record's local import list instead of the default Mathlib-only benchmark baseline.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--reasoning-effort",
        choices=["minimal", "low", "medium", "high", "xhigh"],
        default="high",
        help="OpenRouter reasoning effort for DeepSeek. Use max-tokens 8192+ for reasoning models.",
    )
    parser.add_argument("--source-context", type=int, default=6)
    parser.add_argument("--lean-context", type=int, default=0)
    parser.add_argument(
        "--call-openrouter",
        action="store_true",
        help="Make the bounded OpenRouter call after writing the exact payload. Requires OPENROUTER_API_KEY.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        paths = materialize_eval(args)
        if args.call_openrouter:
            call_openrouter(paths["payload"], paths["eval_dir"] / "openrouter-response.json")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Materialized eval project: {args.output}")
    print(f"Prompt payload: {paths['payload']}")
    print(f"Review command: {paths['eval_dir'] / 'review-command.txt'}")
    if args.call_openrouter:
        print(f"OpenRouter response: {paths['eval_dir'] / 'openrouter-response.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
