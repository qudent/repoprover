#!/usr/bin/env python3
"""Generate a LaTeX-statement-level dataset for Algebraic Combinatorics.

The old minimal-context collection used one Lean declaration as the benchmark
row.  This generator makes the source theorem/definition environment the outer
unit: one row per theorem-like LaTeX environment, with post-hoc links to Lean
declarations that explicitly declare a matching source ``Label:`` in their doc
comments.

No model calls are made.  The Lean links are evaluation metadata only; consumers
must not expose target Lean declarations to a source-to-Lean generator.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.generate_context_graph import (
        AGGREGATE_TEX_FILENAMES,
        COMMENT_LABEL_RE,
        LABEL_TOKEN_RE,
        TEX_LABEL_RE,
        clean_label_token,
        parse_lean_declarations,
        read_manifest,
        relpath,
    )
except ModuleNotFoundError:
    from generate_context_graph import (
        AGGREGATE_TEX_FILENAMES,
        COMMENT_LABEL_RE,
        LABEL_TOKEN_RE,
        TEX_LABEL_RE,
        clean_label_token,
        parse_lean_declarations,
        read_manifest,
        relpath,
    )


GENERATOR_VERSION = "latex-statement-dataset-v1"
THEOREM_ENVIRONMENTS = (
    "theorem",
    "lemma",
    "proposition",
    "corollary",
    "definition",
    "conjecture",
    "statement",
    "example",
)
TEX_ENV_TOKEN_RE = re.compile(
    r"\\(?P<kind>begin|end)\{(?P<env>" + "|".join(THEOREM_ENVIRONMENTS) + r")\}"
)
TEX_REF_RE = re.compile(r"\\(?:ref|eqref|autoref|cref|Cref)\{([^}]+)\}")
PART_MARKER_RE = re.compile(r"\\textbf\{\((?P<part>[A-Za-z0-9ivxlcdmIVXLCDM]+)\)\}")
LEAN_LABEL_CLAUSE_RE = re.compile(r"Label:\s*(?P<body>.*?)(?:-\s*/|\n|$)")


@dataclass(frozen=True)
class LatexStatementUnit:
    id: str
    path: str
    environment: str
    unit_index: int
    line_range: tuple[int, int]
    labels: tuple[str, ...]
    referenced_labels: tuple[str, ...]
    part_markers: tuple[dict[str, Any], ...]
    source_text: str
    chapter_id: str | None
    manifest_target_labels: tuple[str, ...]
    parse_warnings: tuple[str, ...] = ()


def numbered_range(start: int, end: int) -> list[int]:
    return [int(start), int(end)]


def estimate_tokens(text: str) -> int:
    return (len(text) + 3) // 4


def unique_in_order(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = clean_label_token(value)
        if cleaned and cleaned not in seen:
            out.append(cleaned)
            seen.add(cleaned)
    return tuple(out)


def unit_id(path: str, start_line: int, labels: tuple[str, ...], unit_index: int) -> str:
    if labels:
        return f"{path}:{labels[0]}"
    return f"{path}:unlabeled-{unit_index:04d}-line-{start_line}"


def extract_part_markers(source_text: str, start_line: int) -> tuple[dict[str, Any], ...]:
    parts: list[dict[str, Any]] = []
    for offset, line in enumerate(source_text.splitlines(), start=0):
        for match in PART_MARKER_RE.finditer(line):
            parts.append(
                {
                    "part": match.group("part").lower(),
                    "line": start_line + offset,
                    "marker": match.group(0),
                }
            )
    return tuple(parts)


def parse_latex_statement_units(project_root: Path) -> list[LatexStatementUnit]:
    chapters = read_manifest(project_root)
    chapter_by_source = {chapter["source_path"]: chapter for chapter in chapters}
    manifest_targets_by_source = {
        chapter["source_path"]: set(chapter.get("target_theorems", [])) for chapter in chapters
    }
    tex_root = project_root / "AlgebraicCombinatorics" / "tex"
    units: list[LatexStatementUnit] = []

    for path in sorted(tex_root.rglob("*.tex")):
        if path.name in AGGREGATE_TEX_FILENAMES:
            continue
        rel = relpath(path, project_root)
        lines = path.read_text(encoding="utf-8").splitlines()
        active_stack: list[dict[str, Any]] = []
        local_index = 0

        for line_number, line in enumerate(lines, start=1):
            for match in TEX_ENV_TOKEN_RE.finditer(line):
                kind = match.group("kind")
                env = match.group("env")
                if kind == "begin":
                    active_stack.append({"env": env, "start_line": line_number})
                    continue
                if kind == "end" and active_stack:
                    match_index = None
                    for index in range(len(active_stack) - 1, -1, -1):
                        if active_stack[index]["env"] == env:
                            match_index = index
                            break
                    if match_index is None:
                        match_index = len(active_stack) - 1
                    parse_warnings: tuple[str, ...] = ()
                    active = active_stack.pop(match_index)
                    if active["env"] != env:
                        parse_warnings = (f"mismatched_end_environment:{env}",)
                    local_index += 1
                    start_line = int(active["start_line"])
                    end_line = line_number
                    source_text = "\n".join(lines[start_line - 1 : end_line])
                    labels = unique_in_order(TEX_LABEL_RE.findall(source_text))
                    referenced = tuple(
                        label for label in unique_in_order(TEX_REF_RE.findall(source_text)) if label not in labels
                    )
                    manifest_targets = tuple(
                        label for label in labels if label in manifest_targets_by_source.get(rel, set())
                    )
                    chapter = chapter_by_source.get(rel, {})
                    units.append(
                        LatexStatementUnit(
                            id=unit_id(rel, start_line, labels, local_index),
                            path=rel,
                            environment=active["env"],
                            unit_index=local_index,
                            line_range=(start_line, end_line),
                            labels=labels,
                            referenced_labels=referenced,
                            part_markers=extract_part_markers(source_text, start_line),
                            source_text=source_text,
                            chapter_id=chapter.get("id"),
                            manifest_target_labels=manifest_targets,
                            parse_warnings=parse_warnings,
                        )
                    )

    units.sort(key=lambda unit: (unit.path, unit.line_range[0], unit.unit_index))
    return units


def extract_declared_source_labels(comment_text: str) -> tuple[str, ...]:
    labels: list[str] = []
    for match in LEAN_LABEL_CLAUSE_RE.finditer(comment_text):
        body = match.group("body")
        labels.extend(re.findall(r"`([^`]+)`", body))
        labels.extend(LABEL_TOKEN_RE.findall(body))
    return unique_in_order(labels)


def extract_referenced_source_labels(comment_text: str) -> tuple[str, ...]:
    labels = [*COMMENT_LABEL_RE.findall(comment_text), *LABEL_TOKEN_RE.findall(comment_text)]
    declared = set(extract_declared_source_labels(comment_text))
    return tuple(label for label in unique_in_order(labels) if label not in declared)


def declared_label_matches_unit(declared_label: str, unit_label: str) -> bool:
    if declared_label == unit_label:
        return True
    if declared_label.startswith(f"{unit_label}."):
        return True
    if declared_label.startswith(f"{unit_label}("):
        return True
    return False


def parse_lean_label_declarations(project_root: Path) -> list[dict[str, Any]]:
    lean_root = project_root / "AlgebraicCombinatorics"
    rows: list[dict[str, Any]] = []
    for path in sorted(lean_root.rglob("*.lean")):
        declarations = parse_lean_declarations(project_root, path)
        lines = path.read_text(encoding="utf-8").splitlines()
        for declaration in declarations:
            start, _ = declaration.line_range
            comment_text = "\n".join(lines[start - 1 : declaration.declaration_line])
            declared_labels = extract_declared_source_labels(comment_text)
            referenced_labels = extract_referenced_source_labels(comment_text)
            if not declared_labels and not referenced_labels:
                continue
            rows.append(
                {
                    "path": declaration.path,
                    "module": declaration.module,
                    "kind": declaration.kind,
                    "name": declaration.name,
                    "full_name": declaration.full_name,
                    "line_range": numbered_range(*declaration.line_range),
                    "declared_source_labels": list(declared_labels),
                    "referenced_source_labels": list(referenced_labels),
                    "file_context": list(declaration.file_context),
                    "imports": list(declaration.imports),
                }
            )
    return rows


def build_label_indexes(lean_rows: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    declared: dict[str, list[dict[str, Any]]] = defaultdict(list)
    referenced: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in lean_rows:
        for label in row.get("declared_source_labels", []):
            declared[label].append(row)
        for label in row.get("referenced_source_labels", []):
            referenced[label].append(row)
    return declared, referenced


def aligned_declarations_for_unit(
    unit: LatexStatementUnit,
    declared_index: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    if not unit.labels:
        return selected
    for declared_label, rows in declared_index.items():
        if not any(declared_label_matches_unit(declared_label, label) for label in unit.labels):
            continue
        for row in rows:
            key = (row["path"], row["full_name"])
            if key in seen:
                continue
            selected.append(row)
            seen.add(key)
    selected.sort(key=lambda row: (row["path"], row["line_range"][0], row["full_name"]))
    return selected


def referencing_declarations_for_unit(
    unit: LatexStatementUnit,
    referenced_index: dict[str, list[dict[str, Any]]],
    aligned: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    aligned_keys = {(row["path"], row["full_name"]) for row in aligned}
    seen: set[tuple[str, str]] = set()
    for label in unit.labels:
        for row in referenced_index.get(label, []):
            key = (row["path"], row["full_name"])
            if key in aligned_keys or key in seen:
                continue
            selected.append(row)
            seen.add(key)
    selected.sort(key=lambda row: (row["path"], row["line_range"][0], row["full_name"]))
    return selected


def source_context_candidates(unit: LatexStatementUnit, units: list[LatexStatementUnit]) -> dict[str, Any]:
    by_label: dict[str, LatexStatementUnit] = {}
    for candidate in units:
        for label in candidate.labels:
            by_label[label] = candidate

    prior_same_file = [
        candidate
        for candidate in units
        if candidate.path == unit.path and candidate.line_range[1] < unit.line_range[0] and candidate.labels
    ][-8:]
    referenced_units = []
    for label in unit.referenced_labels:
        candidate = by_label.get(label)
        if candidate is None:
            referenced_units.append({"label": label, "resolved": False})
        else:
            referenced_units.append(
                {
                    "label": label,
                    "resolved": True,
                    "unit_id": candidate.id,
                    "path": candidate.path,
                    "environment": candidate.environment,
                    "line_range": numbered_range(*candidate.line_range),
                    "labels": list(candidate.labels),
                }
            )

    return {
        "previous_same_file_source_units": [
            {
                "unit_id": candidate.id,
                "environment": candidate.environment,
                "line_range": numbered_range(*candidate.line_range),
                "labels": list(candidate.labels),
            }
            for candidate in prior_same_file
        ],
        "referenced_source_units": referenced_units,
    }


def row_for_unit(
    unit: LatexStatementUnit,
    *,
    units: list[LatexStatementUnit],
    declared_index: dict[str, list[dict[str, Any]]],
    referenced_index: dict[str, list[dict[str, Any]]],
    generated_at: str,
) -> dict[str, Any]:
    aligned = aligned_declarations_for_unit(unit, declared_index)
    references = referencing_declarations_for_unit(unit, referenced_index, aligned)
    return {
        "id": unit.id,
        "schema_version": "repoprover.latex_statement_unit.v1",
        "generation": {
            "generator_version": GENERATOR_VERSION,
            "generator_kind": "deterministic_static_analysis",
            "generated_at": generated_at,
            "model_cost_usd": 0.0,
        },
        "source_unit": {
            "unit_kind": "latex_environment",
            "environment": unit.environment,
            "path": unit.path,
            "line_range": numbered_range(*unit.line_range),
            "labels": list(unit.labels),
            "referenced_labels": list(unit.referenced_labels),
            "part_markers": list(unit.part_markers),
            "source_text": unit.source_text,
            "source_characters": len(unit.source_text),
            "source_estimated_tokens": estimate_tokens(unit.source_text),
            "chapter_id": unit.chapter_id,
            "manifest_target_labels": list(unit.manifest_target_labels),
            "parse_warnings": list(unit.parse_warnings),
        },
        "context_candidates": source_context_candidates(unit, units),
        "posthoc_lean_alignment": {
            "target_lean_available_to_generator": False,
            "method": "lean_doc_comment_declared_label" if aligned else "none",
            "aligned_declaration_count": len(aligned),
            "aligned_lean_declarations": aligned,
            "referencing_declaration_count": len(references),
            "referencing_lean_declarations": references[:20],
            "alignment_caveat": (
                "Lean links are post-hoc evaluation metadata from explicit `Label:` doc comments. "
                "They are not context for generation and are not human-certified proof dependencies."
            ),
        },
        "trust": {
            "source_unit": 0.9,
            "lean_alignment": 0.7 if aligned else 0.0,
            "human_review": 0.0,
        },
        "selection": {
            "status": "gold_candidate" if unit.labels and aligned else "source_unit_only",
            "criteria": "one theorem-like LaTeX environment; gold_candidate requires a source label and at least one explicit Lean `Label:` alignment",
        },
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def percentile(values: list[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((pct / 100) * (len(ordered) - 1))))
    return int(ordered[index])


def summary_payload(rows: list[dict[str, Any]], elapsed_seconds: float) -> dict[str, Any]:
    aligned_counts = [row["posthoc_lean_alignment"]["aligned_declaration_count"] for row in rows]
    gold_rows = [row for row in rows if row["selection"]["status"] == "gold_candidate"]
    gold_aligned_counts = [row["posthoc_lean_alignment"]["aligned_declaration_count"] for row in gold_rows]
    env_counts = Counter(row["source_unit"]["environment"] for row in rows)
    labeled_count = sum(1 for row in rows if row["source_unit"]["labels"])
    with_parts = sum(1 for row in rows if row["source_unit"]["part_markers"])
    manifest_target_count = sum(1 for row in rows if row["source_unit"]["manifest_target_labels"])
    parse_warning_counts = Counter(
        warning for row in rows for warning in row["source_unit"].get("parse_warnings", [])
    )

    return {
        "schema_version": "repoprover.latex_statement_dataset_report.v1",
        "generator_version": GENERATOR_VERSION,
        "generated_at": rows[0]["generation"]["generated_at"] if rows else datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "model_cost_usd": 0.0,
        "source_units": len(rows),
        "labeled_source_units": labeled_count,
        "unlabeled_source_units": len(rows) - labeled_count,
        "manifest_target_units": manifest_target_count,
        "gold_candidate_units": len(gold_rows),
        "aligned_source_units": sum(1 for value in aligned_counts if value > 0),
        "multi_declaration_gold_units": sum(1 for value in gold_aligned_counts if value > 1),
        "total_aligned_lean_declarations": sum(gold_aligned_counts),
        "source_units_with_parts": with_parts,
        "parse_warning_counts": dict(sorted(parse_warning_counts.items())),
        "environment_counts": dict(sorted(env_counts.items())),
        "aligned_declarations_per_gold_unit": {
            "median": statistics.median(gold_aligned_counts) if gold_aligned_counts else 0,
            "p90": percentile(gold_aligned_counts, 90),
            "p95": percentile(gold_aligned_counts, 95),
            "max": max(gold_aligned_counts) if gold_aligned_counts else 0,
        },
    }


def render_report(payload: dict[str, Any], *, units_path: Path, gold_path: Path) -> str:
    lines = [
        "# LaTeX Statement Unit Dataset Report",
        "",
        "Generated by `scripts/generate_latex_statement_dataset.py`.",
        "",
        "## Summary",
        "",
        "| Measure | Value |",
        "|---|---:|",
        f"| Source theorem-like units | {payload['source_units']} |",
        f"| Labeled source units | {payload['labeled_source_units']} |",
        f"| Manifest target units | {payload['manifest_target_units']} |",
        f"| Gold-candidate units with explicit Lean `Label:` alignment | {payload['gold_candidate_units']} |",
        f"| Multi-declaration gold-candidate units | {payload['multi_declaration_gold_units']} |",
        f"| Total aligned Lean declarations | {payload['total_aligned_lean_declarations']} |",
        f"| Source units with explicit part markers | {payload['source_units_with_parts']} |",
        f"| Source units with parser warnings | {sum(payload['parse_warning_counts'].values())} |",
        f"| Model cost | ${payload['model_cost_usd']:.2f} |",
        "",
        "## Environment Counts",
        "",
        "| Environment | Units |",
        "|---|---:|",
    ]
    for env, count in payload["environment_counts"].items():
        lines.append(f"| `{env}` | {count} |")
    if payload["parse_warning_counts"]:
        lines.extend(
            [
                "",
                "## Parser Warnings",
                "",
                "| Warning | Units |",
                "|---|---:|",
            ]
        )
        for warning, count in payload["parse_warning_counts"].items():
            lines.append(f"| `{warning}` | {count} |")
    dist = payload["aligned_declarations_per_gold_unit"]
    lines.extend(
        [
            "",
            "## Aligned Declarations Per Gold Unit",
            "",
            "| Median | p90 | p95 | Max |",
            "|---:|---:|---:|---:|",
            f"| {dist['median']} | {dist['p90']} | {dist['p95']} | {dist['max']} |",
            "",
            "## Files",
            "",
            f"- `{units_path}`: all theorem-like LaTeX environments, one row per source environment.",
            f"- `{gold_path}`: subset with at least one source label and at least one explicit Lean `Label:` alignment.",
            "",
            "## Honesty Caveats",
            "",
            "- This is a theorem/source-unit dataset, not a proof-dependency oracle.",
            "- Lean alignments are post-hoc evaluation metadata and must be hidden from generation prompts.",
            "- The alignment uses explicit Lean doc-comment `Label:` clauses, not arbitrary `\\ref{...}` mentions.",
            "- A single LaTeX unit can map to several Lean declarations; theorem-level evaluation should measure coverage of the unit, while Lean remains the inner compile-check unit.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path("algebraic-combinatorics"))
    parser.add_argument("--units-output", type=Path, default=Path("docs/latex-statement-units.jsonl"))
    parser.add_argument("--gold-output", type=Path, default=Path("docs/latex-statement-gold-candidates.jsonl"))
    parser.add_argument("--report-output", type=Path, default=Path("docs/latex-statement-dataset-report.md"))
    parser.add_argument("--summary-output", type=Path, default=Path("docs/latex-statement-dataset-summary.json"))
    args = parser.parse_args()

    started = time.monotonic()
    generated_at = datetime.now(timezone.utc).isoformat()
    project_root = args.project_root.resolve()
    units = parse_latex_statement_units(project_root)
    lean_rows = parse_lean_label_declarations(project_root)
    declared_index, referenced_index = build_label_indexes(lean_rows)
    rows = [
        row_for_unit(
            unit,
            units=units,
            declared_index=declared_index,
            referenced_index=referenced_index,
            generated_at=generated_at,
        )
        for unit in units
    ]
    gold_rows = [row for row in rows if row["selection"]["status"] == "gold_candidate"]
    payload = summary_payload(rows, time.monotonic() - started)

    write_jsonl(args.units_output, rows)
    write_jsonl(args.gold_output, gold_rows)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report_output.write_text(
        render_report(payload, units_path=args.units_output, gold_path=args.gold_output),
        encoding="utf-8",
    )

    print(f"wrote units: {args.units_output} ({len(rows)} source units)")
    print(f"wrote gold candidates: {args.gold_output} ({len(gold_rows)} source units)")
    print(f"wrote report: {args.report_output}")
    print(f"elapsed_seconds: {payload['elapsed_seconds']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
