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


def project_modules(project_root: Path) -> list[str]:
    lean_root = project_root / "AlgebraicCombinatorics"
    modules: list[str] = []
    for path in sorted(lean_root.rglob("*.lean")):
        rel = path.relative_to(project_root).with_suffix("")
        modules.append(".".join(rel.parts))
    return modules


def run_lean_scan(project_root: Path, output: Path) -> None:
    modules = project_modules(project_root)
    cmd = [
        "lake",
        "env",
        "lean",
        "--run",
        str((REPO_ROOT / "scripts/lean_dependency_scan.lean").resolve()),
        *modules,
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


def record_declaration_names(record: dict[str, Any]) -> list[str]:
    names: list[str] = []
    names.extend(str(name) for name in record.get("output", {}).get("declaration_names") or [])
    for decl in record.get("posthoc_lean_alignment", {}).get("aligned_lean_declarations") or []:
        name = decl.get("full_name") or decl.get("name")
        if name:
            names.append(str(name))
    return names


def record_kind(record: dict[str, Any]) -> str:
    if record.get("output", {}).get("chunk_kind"):
        return str(record["output"]["chunk_kind"])
    if record.get("source_unit", {}).get("environment"):
        return str(record["source_unit"]["environment"])
    aligned = record.get("posthoc_lean_alignment", {}).get("aligned_lean_declarations") or []
    kinds = {str(decl.get("kind")) for decl in aligned if decl.get("kind")}
    if len(kinds) == 1:
        return next(iter(kinds))
    return "unknown"


def record_labels(record: dict[str, Any]) -> list[str]:
    alignment = record.get("alignment", {})
    if alignment.get("source_method") == "lean_comment_label":
        return [str(label) for label in alignment.get("comment_labels") or []]
    posthoc = record.get("posthoc_lean_alignment", {})
    if posthoc.get("method") == "lean_doc_comment_declared_label":
        return [str(label) for label in record.get("source_unit", {}).get("labels") or []]
    return []


def record_schema(records: list[dict[str, Any]]) -> str:
    schemas = {str(record.get("schema_version", "minimal_context_record")) for record in records}
    if len(schemas) == 1:
        return next(iter(schemas))
    return "mixed"


def deps_for_record(record: dict[str, Any], scan: dict[str, dict[str, Any]]) -> tuple[set[str], set[str], set[str], list[str]]:
    mathlib: set[str] = set()
    project: set[str] = set()
    other: set[str] = set()
    missing: list[str] = []
    for declaration in record_declaration_names(record):
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

    theorem_rows = [row for row in record_rows if record_kind(row["record"]) in {"theorem", "lemma"}]

    labels: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in record_rows:
        record = row["record"]
        for label in record_labels(record):
            labels[label].append(row)

    def merged_count(rows: list[dict[str, Any]], key: str) -> int:
        merged: set[str] = set()
        for row in rows:
            merged.update(row[key])
        return len(merged)

    def declaration_count(rows: list[dict[str, Any]]) -> int:
        return sum(len(record_declaration_names(row["record"])) for row in rows)

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
        "record_schema": record_schema(records),
        "scan_rows": len(scan),
        "record_count": len(records),
        "declarations_per_record": percentile_summary([len(record_declaration_names(record)) for record in records]),
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
            "records_per_label": percentile_summary([len(rows) for rows in labels.values()]),
            "declarations_per_label": percentile_summary([declaration_count(rows) for rows in labels.values()]),
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
    parser.add_argument("--records", type=Path, default=REPO_ROOT / "docs/latex-statement-gold-candidates.jsonl")
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
