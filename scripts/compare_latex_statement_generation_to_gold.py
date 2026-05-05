#!/usr/bin/env python3
"""Post-hoc compare theorem-level generated declarations to aligned Lean gold."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def local_name(name: str) -> str:
    return name.split(".")[-1]


def generation_output_paths(run_dir: Path) -> list[Path]:
    if run_dir.is_file():
        return [run_dir]
    return sorted(run_dir.glob("batch-*/generation-output.json"))


def verification_results(run_dir: Path, path: Path | None = None) -> dict[str, dict[str, Any]]:
    if path is None:
        path = run_dir / "eval" / "verification-results.json"
    if not path.exists():
        return {}
    data = read_json(path)
    rows: dict[str, dict[str, Any]] = {}
    for batch in data.get("batches") or []:
        for unit in batch.get("units") or []:
            if unit.get("unit_key"):
                rows[str(unit["unit_key"])] = unit
    return rows


def compare(selector_run: Path, generation_run: Path, *, verification_path: Path | None = None) -> dict[str, Any]:
    selected_units = read_jsonl(selector_run / "eval" / "selected-units.jsonl")
    selected_by_key = {f"unit-{index + 1:03d}": row for index, row in enumerate(selected_units)}
    verification_by_key = verification_results(generation_run, verification_path)

    unit_rows: list[dict[str, Any]] = []
    for output_path in generation_output_paths(generation_run):
        output = read_json(output_path)
        for generated in output.get("units") or []:
            unit_key = str(generated.get("unit_key") or "")
            selected = selected_by_key.get(unit_key, {})
            aligned = selected.get("posthoc_lean_alignment", {}).get("aligned_lean_declarations", [])
            aligned_full = [str(decl.get("full_name") or "") for decl in aligned if decl.get("full_name")]
            aligned_local = [local_name(name) for name in aligned_full]
            generated_names = [str(name) for name in generated.get("declaration_names") or []]
            generated_local = [local_name(name) for name in generated_names]
            full_overlap = sorted(set(generated_names) & set(aligned_full))
            local_overlap = sorted(set(generated_local) & set(aligned_local))
            verification = verification_by_key.get(unit_key, {})
            compile_passed = bool(verification.get("compile_passed"))
            if not compile_passed:
                coverage_status = "not_compiled"
            elif full_overlap or local_overlap:
                coverage_status = "compiled_name_overlap"
            else:
                coverage_status = "compiled_needs_semantic_review"
            unit_rows.append(
                {
                    "unit_key": unit_key,
                    "source_unit_id": selected.get("id"),
                    "generated_declaration_names": generated_names,
                    "gold_aligned_full_names": aligned_full,
                    "gold_aligned_local_names": aligned_local,
                    "full_name_overlap": full_overlap,
                    "local_name_overlap": local_overlap,
                    "compile_passed": compile_passed,
                    "coverage_status": coverage_status,
                }
            )

    return {
        "schema_version": "repoprover.latex_statement_gold_comparison.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selector_run": str(selector_run),
        "generation_run": str(generation_run),
        "unit_count": len(unit_rows),
        "compile_passed_units": sum(1 for row in unit_rows if row["compile_passed"]),
        "compiled_name_overlap_units": sum(1 for row in unit_rows if row["coverage_status"] == "compiled_name_overlap"),
        "compiled_needs_semantic_review_units": sum(
            1 for row in unit_rows if row["coverage_status"] == "compiled_needs_semantic_review"
        ),
        "units": unit_rows,
        "caveat": (
            "This is a post-hoc exact-name overlap check, not a semantic theorem-equivalence proof. "
            "Compiled outputs without name overlap may still be useful source-theorem formalizations."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-run", type=Path, required=True)
    parser.add_argument("--generation-run", type=Path, required=True)
    parser.add_argument(
        "--verification-results",
        type=Path,
        help="Optional verification-results JSON to decide which generated units are compile-clean.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = compare(args.selector_run, args.generation_run, verification_path=args.verification_results)
    write_json(args.output, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
