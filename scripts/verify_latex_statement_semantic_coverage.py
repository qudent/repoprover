#!/usr/bin/env python3
"""Post-hoc semantic coverage checks for LaTeX-statement generations.

This verifier is intentionally grader-only: it reads aligned Lean declarations
from the LaTeX statement gold metadata after generation, materializes the
original target statement under a fresh check name, and tries to prove it from
the generated theorem with the same ``simpa using`` style criterion used by the
source-statement live evaluator.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.materialize_minimal_context_smoke import declaration_body_marker_index
    from scripts.run_source_statement_live_eval import generated_application_candidates
    from scripts.verify_latex_statement_generation import parse_lean_json
except ModuleNotFoundError:
    from materialize_minimal_context_smoke import declaration_body_marker_index
    from run_source_statement_live_eval import generated_application_candidates
    from verify_latex_statement_generation import parse_lean_json


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_NAME = "__repoprover_latex_statement_check"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def generation_output_paths(run_dir: Path) -> list[Path]:
    if run_dir.is_file():
        return [run_dir]
    return sorted(run_dir.glob("batch-*/generation-output.json"))


def verification_results(run_dir: Path) -> dict[str, dict[str, Any]]:
    path = run_dir / "eval" / "verification-results.json"
    if not path.exists():
        return {}
    data = read_json(path)
    rows: dict[str, dict[str, Any]] = {}
    for batch in data.get("batches") or []:
        for unit in batch.get("units") or []:
            unit_key = str(unit.get("unit_key") or "")
            if unit_key:
                rows[unit_key] = unit
    return rows


def selected_units_by_key(selector_run: Path) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(selector_run / "eval" / "selected-units.jsonl")
    return {f"unit-{index + 1:03d}": row for index, row in enumerate(rows)}


def renamed_gold_head(project_root: Path, aligned: dict[str, Any]) -> tuple[str, str]:
    path = project_root / str(aligned["path"])
    start, end = aligned["line_range"]
    lines = path.read_text(encoding="utf-8").splitlines()
    original = "\n".join(lines[int(start) - 1 : int(end)]).rstrip() + "\n"
    marker = declaration_body_marker_index(original)
    head = original[:marker].rstrip()
    renamed = re.sub(
        r"(\b(?:theorem|lemma)\s+)([^\s:\{\(\[]+)",
        rf"\1{CHECK_NAME}",
        head,
        count=1,
    )
    return original, renamed


def target_file_prefix(project_root: Path, aligned: dict[str, Any]) -> str:
    path = project_root / str(aligned["path"])
    start = int(aligned["line_range"][0])
    return "\n".join(path.read_text(encoding="utf-8").splitlines()[: start - 1]).rstrip()


def declaration_head_for_name(body: str, name: str) -> str:
    pattern = re.compile(
        r"(?m)^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
        r"(?:theorem|lemma)\s+" + re.escape(name) + r"(?=$|[\s:\{\(\[])"
    )
    match = pattern.search(body)
    if not match:
        return body
    chunk = body[match.start() :]
    try:
        marker = declaration_body_marker_index(chunk)
    except ValueError:
        return chunk.splitlines()[0]
    return chunk[:marker].rstrip()


def gold_check_declaration(
    *,
    generated_names: list[str],
    generated_body: str,
    gold_head: str,
) -> str:
    candidates: list[str] = []
    for name in generated_names:
        generated_head = declaration_head_for_name(generated_body, name)
        for candidate_head in (generated_head, gold_head):
            for candidate in generated_application_candidates(name, candidate_head):
                # Named candidates are useful in some declaration-level checks,
                # but for theorem-level alternate statements they can introduce
                # invalid binder names from either side and obscure the actual
                # semantic failure.
                if ":=" in candidate:
                    continue
                if candidate not in candidates:
                    candidates.append(candidate)
    if not candidates:
        tactic = "  fail"
    else:
        tactic = "\n".join(["  first", *(f"  | simpa using {candidate}" for candidate in candidates)])
    return gold_head + " := by\n" + tactic + "\n"


def build_semantic_check_source(
    *,
    project_root: Path,
    aligned: dict[str, Any],
    generated_names: list[str],
    generated_body: str,
) -> str:
    _original, gold_head = renamed_gold_head(project_root, aligned)
    parts = [
        target_file_prefix(project_root, aligned),
        "",
        "/-! RepoProver post-hoc semantic coverage check.",
        "The aligned gold statement below is grader-only and was not shown to generation. -/",
        "",
        "-- Generated declaration(s) under the original target file prefix context.",
        generated_body.strip(),
        "",
        "-- Grader-only check: original aligned statement proved from generated theorem(s).",
        gold_check_declaration(generated_names=generated_names, generated_body=generated_body, gold_head=gold_head).rstrip(),
        "",
    ]
    return "\n".join(part for part in parts if part is not None).rstrip() + "\n"


def run_lean_file(path: Path, *, project_root: Path, timeout_seconds: float) -> dict[str, Any]:
    result = subprocess.run(
        ["lake", "env", "lean", "--json", str(path.resolve())],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "returncode": result.returncode,
        "messages": parse_lean_json(result.stdout),
        "stderr": result.stderr,
    }


def classify_failure(*, passed: bool, messages: list[dict[str, Any]], stderr: str) -> str:
    if passed:
        return "semantic_covered"
    text = "\n".join(str(message.get("data") or "") for message in messages)
    text = f"{text}\n{stderr}"
    if "no such file or directory" in text:
        return "harness_error"
    if "Application type mismatch" in text or "Invalid argument name" in text:
        return "shape_mismatch_against_oracle"
    if "Unknown identifier" in text or "unknown identifier" in text:
        return "generated_application_unusable"
    return "semantic_grader_failed"


def check_aligned_declaration(
    *,
    project_root: Path,
    semantic_root: Path,
    unit_key: str,
    aligned_index: int,
    aligned: dict[str, Any],
    generated_names: list[str],
    generated_body: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    if str(aligned.get("kind") or "") not in {"theorem", "lemma"}:
        return {
            "gold_full_name": aligned.get("full_name"),
            "gold_kind": aligned.get("kind"),
            "coverage_status": "unsupported_gold_kind",
            "semantic_check_passed": False,
        }

    lean_source = build_semantic_check_source(
        project_root=project_root,
        aligned=aligned,
        generated_names=generated_names,
        generated_body=generated_body,
    )
    lean_path = semantic_root / unit_key / f"gold-{aligned_index + 1:03d}.lean"
    lean_path.parent.mkdir(parents=True, exist_ok=True)
    lean_path.write_text(lean_source, encoding="utf-8")
    lean_result = run_lean_file(lean_path, project_root=project_root, timeout_seconds=timeout_seconds)
    errors = [message for message in lean_result["messages"] if message.get("severity") == "error"]
    passed = lean_result["returncode"] == 0 and not errors
    failure_class = classify_failure(passed=passed, messages=lean_result["messages"], stderr=lean_result["stderr"])
    return {
        "gold_full_name": aligned.get("full_name"),
        "gold_kind": aligned.get("kind"),
        "gold_path": aligned.get("path"),
        "gold_line_range": aligned.get("line_range"),
        "generated_declaration_names": generated_names,
        "lean_source_path": str(lean_path),
        "lean_returncode": lean_result["returncode"],
        "lean_error_count": len(errors),
        "semantic_check_passed": passed,
        "coverage_status": "semantic_grader_passed" if passed else "semantic_grader_failed",
        "failure_class": failure_class,
        "messages": lean_result["messages"],
        "stderr": lean_result["stderr"],
    }


def compare(args: argparse.Namespace) -> dict[str, Any]:
    selected_by_key = selected_units_by_key(args.selector_run)
    verification_by_key = verification_results(args.generation_run)
    units: list[dict[str, Any]] = []

    semantic_root = args.output.parent / "semantic-coverage"
    for output_path in generation_output_paths(args.generation_run):
        output = read_json(output_path)
        for generated in output.get("units") or []:
            unit_key = str(generated.get("unit_key") or "")
            selected = selected_by_key.get(unit_key, {})
            aligned_rows = selected.get("posthoc_lean_alignment", {}).get("aligned_lean_declarations", [])
            generated_body = str(generated.get("lean_file_body") or "")
            generated_names = [str(name) for name in generated.get("declaration_names") or []]
            compile_passed = bool(verification_by_key.get(unit_key, {}).get("compile_passed"))
            checks: list[dict[str, Any]] = []
            if compile_passed:
                for index, aligned in enumerate(aligned_rows):
                    checks.append(
                        check_aligned_declaration(
                            project_root=args.project_root,
                            semantic_root=semantic_root,
                            unit_key=unit_key,
                            aligned_index=index,
                            aligned=aligned,
                            generated_names=generated_names,
                            generated_body=generated_body,
                            timeout_seconds=args.timeout_seconds,
                        )
                    )
            passed_count = sum(1 for row in checks if row.get("semantic_check_passed"))
            if not compile_passed:
                coverage_status = "generated_not_compiled"
            elif aligned_rows and passed_count == len(aligned_rows):
                coverage_status = "all_aligned_gold_proved"
            elif passed_count:
                coverage_status = "partial_aligned_gold_proved"
            elif aligned_rows:
                coverage_status = "no_aligned_gold_proved"
            else:
                coverage_status = "no_aligned_gold_to_check"
            units.append(
                {
                    "unit_key": unit_key,
                    "source_unit_id": selected.get("id"),
                    "generation_output": str(output_path),
                    "compile_passed": compile_passed,
                    "aligned_gold_declaration_count": len(aligned_rows),
                    "semantic_passed_gold_declarations": passed_count,
                    "coverage_status": coverage_status,
                    "checks": checks,
                }
            )

    return {
        "schema_version": "repoprover.latex_statement_semantic_coverage.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selector_run": str(args.selector_run),
        "generation_run": str(args.generation_run),
        "project_root": str(args.project_root),
        "unit_count": len(units),
        "all_aligned_gold_proved_units": sum(1 for row in units if row["coverage_status"] == "all_aligned_gold_proved"),
        "partial_aligned_gold_proved_units": sum(
            1 for row in units if row["coverage_status"] == "partial_aligned_gold_proved"
        ),
        "no_aligned_gold_proved_units": sum(1 for row in units if row["coverage_status"] == "no_aligned_gold_proved"),
        "units": units,
        "caveat": (
            "This is post-hoc oracle verification. Gold declarations are read only by the grader, "
            "after generation, and are not source-only prompt context."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-run", type=Path, required=True)
    parser.add_argument("--generation-run", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = compare(args)
    write_json(args.output, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
