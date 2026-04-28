#!/usr/bin/env python3
"""Deterministically attack minimal-context gold candidates.

This pass is deliberately local and cost-free. It does not certify the math;
it checks the review surface for mechanical failures that make a candidate a
bad gold label: wrong target declaration, missing source labels, circular or
future Lean context, unreachable imported predecessors, incomplete Lean output,
and obvious predecessor over-inclusion.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.filter_minimal_context_gold_candidates import read_jsonl, write_jsonl
from scripts.generate_context_graph import LeanDecl, lean_module_from_path, parse_lean_declarations


REVIEWER_VERSION = "gold-candidate-static-adversarial-review-v1"
INCOMPLETE_RE = re.compile(r"\b(?:sorry|admit)\b")
DECL_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")
LABEL_KIND_BY_OUTPUT_KIND = {
    "def": {"def"},
    "abbrev": {"def"},
    "structure": {"def"},
    "class": {"def"},
    "instance": {"def"},
    "theorem": {"thm", "lem", "prop", "cor", "conv", "eq"},
    "lemma": {"thm", "lem", "prop", "cor", "conv", "eq"},
}


@dataclass(frozen=True)
class StaticReview:
    record_id: str
    verdict: str
    source_span_assessment: str
    lean_context_assessment: str
    missing_context: list[str]
    oversized_context: list[str]
    label_or_line_issues: list[str]
    recommended_record_edits: list[str]
    trust_updates: dict[str, float]
    review_notes: list[str]


class ProjectText:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._cache: dict[str, list[str] | None] = {}

    def lines(self, relative_path: str) -> list[str] | None:
        if relative_path not in self._cache:
            path = self.root / relative_path
            self._cache[relative_path] = path.read_text(encoding="utf-8").splitlines() if path.exists() else None
        return self._cache[relative_path]

    def snippet(self, relative_path: str, line_range: list[int] | tuple[int, int]) -> str:
        lines = self.lines(relative_path)
        if lines is None:
            return ""
        start, end = [int(value) for value in line_range]
        return "\n".join(lines[start - 1 : end])


def build_declaration_index(project_root: Path) -> dict[tuple[str, str], LeanDecl]:
    declarations: dict[tuple[str, str], LeanDecl] = {}
    lean_root = project_root / "AlgebraicCombinatorics"
    for lean_path in sorted(lean_root.rglob("*.lean")):
        for declaration in parse_lean_declarations(project_root, lean_path):
            declarations[(declaration.path, declaration.full_name)] = declaration
    return declarations


def short_name(declaration: str) -> str:
    return declaration.split(".")[-1]


def declaration_words(snippet: str) -> set[str]:
    return set(DECL_WORD_RE.findall(snippet))


def source_label_present(snippet: str, label: str) -> bool:
    return re.search(r"\\label\{" + re.escape(label) + r"\}", snippet) is not None


def classify_label_kind(record: dict[str, Any], labels: set[str]) -> list[str]:
    expected = LABEL_KIND_BY_OUTPUT_KIND.get(record["output"].get("chunk_kind", ""), set())
    if not expected:
        return []
    mismatches = []
    for label in sorted(labels):
        prefix = label.split(".", 1)[0]
        if prefix not in expected:
            mismatches.append(
                f"Source label `{label}` has prefix `{prefix}`, which is unusual for output kind "
                f"`{record['output'].get('chunk_kind')}`."
            )
    return mismatches


def review_record(
    record: dict[str, Any],
    declarations: dict[tuple[str, str], LeanDecl],
    project_text: ProjectText,
) -> StaticReview:
    output = record["output"]
    minimal_context = record["minimal_context"]
    target_names = output.get("declaration_names") or []
    target_name = target_names[0] if target_names else ""
    target_key = (output["lean_path"], target_name)
    target_declaration = declarations.get(target_key)
    target_snippet = project_text.snippet(output["lean_path"], output["line_range"])

    missing_context: list[str] = []
    oversized_context: list[str] = []
    label_or_line_issues: list[str] = []
    recommended_edits: list[str] = []
    notes: list[str] = []

    if not target_names:
        label_or_line_issues.append("Output has no declaration_names entry.")
    elif len(target_names) > 1:
        recommended_edits.append("Split multi-declaration output into one declaration-level gold record.")

    if target_declaration is None:
        label_or_line_issues.append(
            f"Target declaration `{target_name}` was not parsed at `{output['lean_path']}`."
        )
    else:
        parsed_range = list(target_declaration.line_range)
        if parsed_range != list(output["line_range"]):
            label_or_line_issues.append(
                f"Output line_range {output['line_range']} does not match parsed declaration range {parsed_range}."
            )
        parsed_labels = set(target_declaration.comment_labels)
        aligned_labels = set(record.get("alignment", {}).get("comment_labels", []))
        if parsed_labels != aligned_labels:
            label_or_line_issues.append(
                "Alignment comment_labels do not match labels parsed from the Lean doc comment: "
                f"record={sorted(aligned_labels)}, parsed={sorted(parsed_labels)}."
            )

    if INCOMPLETE_RE.search(target_snippet):
        label_or_line_issues.append("Target Lean output contains `sorry` or `admit`, so it is not a complete gold output.")

    source_span_labels: set[str] = set()
    for span in minimal_context.get("source_spans", []):
        labels = set(span.get("labels") or [])
        source_span_labels.update(labels)
        if span.get("method") != "lean_comment_label":
            label_or_line_issues.append(f"Source span `{span.get('path')}` does not use lean_comment_label.")
        snippet = project_text.snippet(span["path"], span["line_range"])
        if not snippet:
            label_or_line_issues.append(f"Source span `{span['path']}:{span['line_range']}` has no readable text.")
        for label in sorted(labels):
            if not source_label_present(snippet, label):
                label_or_line_issues.append(
                    f"Source span `{span['path']}:{span['line_range']}` does not contain `\\label{{{label}}}`."
                )

    aligned_labels = set(record.get("alignment", {}).get("comment_labels", []))
    missing_source_labels = sorted(aligned_labels - source_span_labels)
    if missing_source_labels:
        missing_context.append(
            "Lean doc-comment label(s) are not represented by source_spans: "
            + ", ".join(f"`{label}`" for label in missing_source_labels)
            + "."
        )
        recommended_edits.append("Add source_spans for every exact Lean doc-comment label or explain why a label is non-source.")

    for note in classify_label_kind(record, source_span_labels):
        notes.append(note)

    output_start = int(output["line_range"][0])
    output_words = declaration_words(target_snippet)
    seen_predecessors: set[tuple[str, str]] = set()
    import_closure = set(minimal_context.get("import_closure") or [])
    direct_imports = set(minimal_context.get("imports") or [])
    reachable_modules = import_closure | direct_imports

    for predecessor in minimal_context.get("lean_predecessors", []):
        pred_key = (predecessor["path"], predecessor["declaration"])
        pred_name = predecessor["declaration"]
        pred_range = [int(value) for value in predecessor["line_range"]]
        if pred_key in seen_predecessors:
            oversized_context.append(f"Duplicate predecessor `{pred_name}` appears more than once.")
            continue
        seen_predecessors.add(pred_key)

        if pred_key == target_key:
            label_or_line_issues.append(f"Predecessor `{pred_name}` is the target declaration itself.")
        if predecessor["path"] == output["lean_path"] and pred_range[1] >= output_start:
            label_or_line_issues.append(
                f"Predecessor `{pred_name}` at {predecessor['path']}:{pred_range} is not strictly before the target."
            )
        if predecessor["path"] != output["lean_path"]:
            module = lean_module_from_path(predecessor["path"])
            if module not in reachable_modules:
                missing_context.append(
                    f"Cross-file predecessor `{pred_name}` is in module `{module}`, which is not in imports/import_closure."
                )

        parsed_predecessor = declarations.get(pred_key)
        if parsed_predecessor is None:
            label_or_line_issues.append(
                f"Predecessor `{pred_name}` was not parsed at `{predecessor['path']}`."
            )
        elif list(parsed_predecessor.line_range) != pred_range:
            label_or_line_issues.append(
                f"Predecessor `{pred_name}` line_range {pred_range} does not match parsed range "
                f"{list(parsed_predecessor.line_range)}."
            )

        pred_short = short_name(pred_name)
        if pred_short not in output_words and predecessor.get("method") in {
            "lexical_reference",
            "local_predecessor_window",
        }:
            oversized_context.append(
                f"Predecessor `{pred_name}` is not named in the target output; check whether it is necessary."
            )

    if label_or_line_issues:
        verdict = "reject"
    elif missing_context or oversized_context or recommended_edits:
        verdict = "revise"
    else:
        verdict = "provisionally_accept"

    if label_or_line_issues:
        recommended_edits.append("Regenerate or manually repair line/label metadata before using this as a gold label.")
    if oversized_context:
        recommended_edits.append("Narrow lean_predecessors to declarations actually needed to reproduce the target.")
    if not missing_context and not label_or_line_issues:
        source_span_assessment = "Exact source labels are present in local TeX spans."
    else:
        source_span_assessment = "Source or label coverage has mechanical issues."
    if not label_or_line_issues and not missing_context:
        lean_context_assessment = "Lean context is acyclic and reachable by imports; necessity is still heuristic."
    else:
        lean_context_assessment = "Lean context has mechanical reachability, identity, or ordering issues."

    current_trust = record.get("trust", {})
    trust_updates = {
        "source_span": float(current_trust.get("source_span", 0.0)),
        "lean_dependency_graph": float(current_trust.get("lean_dependency_graph", 0.0)),
        "model_extraction": float(current_trust.get("model_extraction", 0.0)),
        "human_review": 0.0,
    }
    if verdict == "provisionally_accept":
        trust_updates["source_span"] = max(trust_updates["source_span"], 0.8)
        trust_updates["lean_dependency_graph"] = max(trust_updates["lean_dependency_graph"], 0.55)
    elif verdict == "revise":
        trust_updates["lean_dependency_graph"] = min(trust_updates["lean_dependency_graph"], 0.35)
    else:
        trust_updates["source_span"] = min(trust_updates["source_span"], 0.25)
        trust_updates["lean_dependency_graph"] = min(trust_updates["lean_dependency_graph"], 0.2)

    notes.insert(0, f"Reviewed by `{REVIEWER_VERSION}`; deterministic static checks only, not human math review.")
    return StaticReview(
        record_id=record["id"],
        verdict=verdict,
        source_span_assessment=source_span_assessment,
        lean_context_assessment=lean_context_assessment,
        missing_context=sorted(set(missing_context)),
        oversized_context=sorted(set(oversized_context)),
        label_or_line_issues=sorted(set(label_or_line_issues)),
        recommended_record_edits=sorted(set(recommended_edits)),
        trust_updates=trust_updates,
        review_notes=notes,
    )


def write_summary(path: Path, rows: list[dict[str, Any]], records_path: Path, elapsed_seconds: float) -> None:
    verdict_counts = Counter(row["review"]["verdict"] for row in rows)
    issue_counts: Counter[str] = Counter()
    source_issue_counts: Counter[str] = Counter()
    lean_issue_counts: Counter[str] = Counter()
    kind_counts = Counter(row["evidence_summary"]["chunk_kind"] for row in rows)
    for row in rows:
        review = row["review"]
        for issue in review.get("label_or_line_issues", []):
            issue_counts[issue] += 1
        for issue in review.get("missing_context", []):
            source_issue_counts[issue] += 1
        for issue in review.get("oversized_context", []):
            lean_issue_counts[issue] += 1

    payload = {
        "records_reviewed": len(rows),
        "reviewer": REVIEWER_VERSION,
        "verdicts": dict(sorted(verdict_counts.items())),
        "chunk_kinds": dict(sorted(kind_counts.items())),
        "top_label_or_line_issues": issue_counts.most_common(20),
        "top_missing_context_issues": source_issue_counts.most_common(20),
        "top_oversized_context_issues": lean_issue_counts.most_common(20),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "model_cost_usd": 0.0,
    }

    lines = [
        "# Minimal Context Gold Candidate Static Adversarial Review",
        "",
        "Generated by `scripts/adversarial_review_gold_candidates.py`.",
        "",
        "## Hypothesis",
        "",
        "A deterministic attack pass can cheaply remove mechanically invalid gold candidates before spending model budget on semantic review.",
        "",
        "## Kill Criteria",
        "",
        "Reject records with wrong target identity, incomplete Lean output, missing source labels, circular/future predecessors, or unreachable cross-file predecessors. Mark records for revision when predecessor context is probably oversized.",
        "",
        "## Artifacts",
        "",
        f"- Input: `{records_path.as_posix()}`",
        f"- Review JSONL: `{path.with_suffix('.jsonl').as_posix()}`",
        "- Model/API cost: `$0.00` (deterministic local checks only)",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(payload, indent=2, sort_keys=True),
        "```",
        "",
        "## Trust Boundary",
        "",
        "This review proves only mechanical consistency. A `provisionally_accept` verdict still means the label needs human or model semantic review before being called final gold.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=Path("docs/minimal-context-gold-candidates.jsonl"))
    parser.add_argument("--project-root", type=Path, default=Path("algebraic-combinatorics"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/minimal-context-gold-candidate-static-review.jsonl"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("docs/minimal-context-gold-candidate-static-review.md"),
    )
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    started = time.monotonic()
    reviewed_at = datetime.now(timezone.utc).isoformat()
    args = parse_args()
    records = read_jsonl(args.records)
    if args.limit:
        records = records[: args.limit]
    declarations = build_declaration_index(args.project_root)
    project_text = ProjectText(args.project_root)

    rows: list[dict[str, Any]] = []
    for record in records:
        review = review_record(record, declarations, project_text)
        rows.append(
            {
                "record_id": record["id"],
                "reviewed_at": reviewed_at,
                "reviewer": REVIEWER_VERSION,
                "evidence_summary": {
                    "lean_path": record["output"]["lean_path"],
                    "lean_line_range": record["output"]["line_range"],
                    "declaration_names": record["output"].get("declaration_names", []),
                    "chunk_kind": record["output"].get("chunk_kind"),
                    "source_spans": [
                        {
                            "path": span["path"],
                            "line_range": span["line_range"],
                            "labels": span.get("labels", []),
                        }
                        for span in record["minimal_context"].get("source_spans", [])
                    ],
                },
                "review": review.__dict__,
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0},
            }
        )

    write_jsonl(args.output, rows)
    elapsed = time.monotonic() - started
    write_summary(args.summary, rows, args.records, elapsed)
    print(
        json.dumps(
            {
                "records_reviewed": len(rows),
                "output": args.output.as_posix(),
                "summary": args.summary.as_posix(),
                "verdicts": dict(sorted(Counter(row["review"]["verdict"] for row in rows).items())),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
