#!/usr/bin/env python3
"""Summarize an elaborated Lean dependency scan.

The raw scan is produced by ``scripts/lean_dependency_scan.lean`` and contains
resolved constants from Lean ``ConstantInfo`` type/value expressions. This is
closer to real dependency accounting than source-text scanning, but it is still
a direct-constant scan: it does not automatically take the transitive closure of
every referenced theorem's proof.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def percentile_summary(values: list[int]) -> dict[str, int]:
    ordered = sorted(values)
    if not ordered:
        return {"median": 0, "p90": 0, "p95": 0, "max": 0}
    return {
        "median": ordered[round((len(ordered) - 1) * 0.5)],
        "p90": ordered[round((len(ordered) - 1) * 0.9)],
        "p95": ordered[round((len(ordered) - 1) * 0.95)],
        "max": ordered[-1],
    }


def run_lean_scan(project_root: Path, output: Path) -> None:
    cmd = [
        "lake",
        "env",
        "lean",
        "--run",
        str((REPO_ROOT / "scripts/lean_dependency_scan.lean").resolve()),
    ]
    with output.open("w", encoding="utf-8") as handle:
        subprocess.run(cmd, cwd=project_root, stdout=handle, check=True)


def load_scan(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[str(row["declaration"])] = row
    return rows


def deps_for_record(record: dict[str, Any], scan: dict[str, dict[str, Any]]) -> tuple[set[str], set[str], set[str], list[str]]:
    mathlib: set[str] = set()
    project: set[str] = set()
    other: set[str] = set()
    missing: list[str] = []
    for declaration in record.get("output", {}).get("declaration_names") or []:
        row = scan.get(declaration)
        if row is None:
            missing.append(declaration)
            continue
        mathlib.update(row.get("used_mathlib") or [])
        project.update(row.get("used_project") or [])
        other.update(row.get("used_other") or [])
    return mathlib, project, other, missing


def summarize(records: list[dict[str, Any]], scan: dict[str, dict[str, Any]]) -> dict[str, Any]:
    record_rows: list[dict[str, Any]] = []
    missing_declarations: set[str] = set()
    for record in records:
        mathlib, project, other, missing = deps_for_record(record, scan)
        missing_declarations.update(missing)
        record_rows.append(
            {
                "record": record,
                "mathlib": mathlib,
                "project": project,
                "other": other,
            }
        )

    theorem_rows = [
        row for row in record_rows if row["record"].get("output", {}).get("chunk_kind") in {"theorem", "lemma"}
    ]

    labels: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in record_rows:
        record = row["record"]
        if record.get("alignment", {}).get("source_method") != "lean_comment_label":
            continue
        for label in record.get("alignment", {}).get("comment_labels") or []:
            labels[label].append(row)

    def merged_count(rows: list[dict[str, Any]], key: str) -> int:
        merged: set[str] = set()
        for row in rows:
            merged.update(row[key])
        return len(merged)

    global_mathlib: set[str] = set()
    global_project: set[str] = set()
    global_other: set[str] = set()
    for row in record_rows:
        global_mathlib.update(row["mathlib"])
        global_project.update(row["project"])
        global_other.update(row["other"])

    raw_project_mathlib_counts = [
        int(row.get("used_mathlib_count", 0))
        for row in scan.values()
        if str(row.get("kind")) in {"theorem", "def", "opaque", "inductive", "constructor", "recursor", "axiom", "quot"}
    ]

    return {
        "scan_rows": len(scan),
        "record_count": len(records),
        "missing_record_declarations": len(missing_declarations),
        "global_unique": {
            "mathlib_direct_constants": len(global_mathlib),
            "project_direct_constants": len(global_project),
            "other_direct_constants": len(global_other),
        },
        "per_record_all": {
            "mathlib_direct_constants": percentile_summary([len(row["mathlib"]) for row in record_rows]),
            "project_direct_constants": percentile_summary([len(row["project"]) for row in record_rows]),
            "other_direct_constants": percentile_summary([len(row["other"]) for row in record_rows]),
        },
        "per_record_theorem_lemma_only": {
            "records": len(theorem_rows),
            "mathlib_direct_constants": percentile_summary([len(row["mathlib"]) for row in theorem_rows]),
            "project_direct_constants": percentile_summary([len(row["project"]) for row in theorem_rows]),
            "other_direct_constants": percentile_summary([len(row["other"]) for row in theorem_rows]),
        },
        "per_exact_tex_label": {
            "labels": len(labels),
            "declarations_per_label": percentile_summary([len(rows) for rows in labels.values()]),
            "mathlib_direct_constants": percentile_summary(
                [merged_count(rows, "mathlib") for rows in labels.values()]
            ),
            "project_direct_constants": percentile_summary(
                [merged_count(rows, "project") for rows in labels.values()]
            ),
            "other_direct_constants": percentile_summary(
                [merged_count(rows, "other") for rows in labels.values()]
            ),
        },
        "raw_project_declaration_rows": {
            "mathlib_direct_constants": percentile_summary(raw_project_mathlib_counts),
        },
        "caveat": (
            "Lean-derived direct constants are extracted from elaborated ConstantInfo type/value expressions. "
            "They resolve notation, overloads, typeclass arguments, tactic-produced terms, and proof terms "
            "stored in the environment. They do not include the transitive closure of every referenced "
            "constant unless requested by a separate closure pass."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--records", type=Path, default=REPO_ROOT / "docs/minimal-context-full-records.jsonl")
    parser.add_argument("--scan-jsonl", type=Path, default=REPO_ROOT / "docs/lean-elaborated-direct-deps.jsonl")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "docs/lean-elaborated-direct-deps-summary.json")
    parser.add_argument("--no-run-lean", action="store_true", help="Reuse --scan-jsonl instead of running Lean.")
    args = parser.parse_args()

    if not args.no_run_lean:
        run_lean_scan(args.project_root, args.scan_jsonl)
    records = load_records(args.records)
    scan = load_scan(args.scan_jsonl)
    summary = summarize(records, scan)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
