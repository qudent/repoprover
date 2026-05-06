#!/usr/bin/env python3
"""Run context selection on LaTeX-statement units.

This is the theorem-level counterpart to ``run_source_context_selection.py``.
It takes rows from ``docs/latex-statement-gold-candidates.jsonl`` and asks a
model to produce an ordered declaration plan plus separate source/project/
Mathlib context requests.

Target Lean alignments for the selected unit are withheld from the prompt. Prior
source references may expose already-formalized project declarations when they
belong to earlier/referenced source units.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
LEAN_BLOCK_COMMENT_RE = re.compile(r"/-.*?-/", re.DOTALL)
LEAN_LINE_COMMENT_RE = re.compile(r"--.*$")
LEAN_DECL_RE = re.compile(
    r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
    r"(?P<kind>theorem|lemma|def|abbrev|instance|class|structure|inductive)\s+"
    r"(?P<name>[^\s:\{\(\[]+)"
)
LEAN_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")
COMMON_LOCAL_DEPENDENCY_NAMES = {
    "by",
    "fun",
    "if",
    "then",
    "else",
    "let",
    "in",
    "where",
    "match",
    "with",
    "intro",
    "exact",
    "simp",
    "rw",
    "have",
    "show",
    "calc",
    "Type",
    "Prop",
    "Nat",
    "Fin",
}
STRUCTURE_SUPPORT_LOCAL_NAMES = {"ext", "ext'", "ext_parts", "parts_ext_iff"}


@dataclass(frozen=True)
class SelectedUnit:
    public_key: str
    row: dict[str, Any]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return rows


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def select_units(
    rows: list[dict[str, Any]],
    limit: int,
    *,
    offset: int = 0,
    unit_id: str | None = None,
    unit_ids: list[str] | None = None,
) -> list[SelectedUnit]:
    selected: list[SelectedUnit] = []
    skipped = 0
    requested_ids = list(unit_ids or [])
    if unit_id:
        requested_ids.append(unit_id)
    requested_id_set = set(requested_ids)
    for row in rows:
        if row.get("selection", {}).get("status") != "gold_candidate":
            continue
        if requested_id_set and row.get("id") not in requested_id_set:
            continue
        if not requested_id_set and skipped < offset:
            skipped += 1
            continue
        selected.append(SelectedUnit(public_key=f"unit-{len(selected) + 1:03d}", row=row))
        if not requested_id_set and limit and len(selected) >= limit:
            break
        if requested_id_set and len(selected) >= len(requested_id_set):
            break
    if not selected:
        raise ValueError("no LaTeX statement gold candidates selected")
    missing_ids = requested_id_set.difference(str(item.row.get("id")) for item in selected)
    if missing_ids:
        raise ValueError(f"requested unit ids not found or not gold candidates: {sorted(missing_ids)}")
    return selected


def unit_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["id"]): row for row in rows}


def public_source_unit(row: dict[str, Any]) -> dict[str, Any]:
    source = row["source_unit"]
    return {
        "id": row["id"],
        "environment": source["environment"],
        "path": source["path"],
        "line_range": source["line_range"],
        "labels": source.get("labels", []),
        "referenced_labels": source.get("referenced_labels", []),
        "part_markers": source.get("part_markers", []),
        "source_text": source["source_text"],
        "parse_warnings": source.get("parse_warnings", []),
    }


def declaration_snippet(decl: dict[str, Any], project_root: Path | None) -> dict[str, Any]:
    if project_root is None:
        return {}
    path = project_root / str(decl.get("path") or "")
    line_range = decl.get("line_range") or []
    if not path.exists() or len(line_range) != 2:
        return {}
    start, end = int(line_range[0]), int(line_range[1])
    lines = path.read_text(encoding="utf-8").splitlines()
    declaration_lines = lines[start - 1 : min(end, start + 39)]
    declaration_text = "\n".join(declaration_lines).rstrip()
    snippet = compact_declaration_text(declaration_text, kind=str(decl.get("kind") or ""))
    return {
        "lean_snippet": snippet[:3000],
        "snippet_truncated": end - start + 1 > 40 or len(snippet) > 3000,
        "snippet_policy": "statement_or_definition_body_only",
    }


def declaration_stub(decl: dict[str, Any], *, project_root: Path | None = None, source: str) -> dict[str, Any]:
    row = {
        "name": decl["full_name"],
        "kind": decl["kind"],
        "path": decl["path"],
        "line_range": decl["line_range"],
        "module": decl.get("module"),
        "imports": decl.get("imports", []),
        "declared_source_labels": decl.get("declared_source_labels", []),
        "referenced_source_labels": decl.get("referenced_source_labels", []),
        "file_context": decl.get("file_context", []),
        "context_source": source,
    }
    row.update(declaration_snippet(decl, project_root))
    return row


def compact_declaration_text(text: str, *, kind: str) -> str:
    """Keep project context compact by removing theorem proofs from snippets."""

    if kind not in {"theorem", "lemma"}:
        return trim_trailing_attributes(text)
    kept: list[str] = []
    for line in text.splitlines():
        if ":= by" in line:
            before, _ = line.split(":= by", 1)
            if before.rstrip():
                kept.append(before.rstrip())
            break
        if line.strip().endswith(":="):
            kept.append(line.rsplit(":=", 1)[0].rstrip())
            break
        kept.append(line)
    return trim_trailing_attributes("\n".join(kept).rstrip())


def strip_lean_comments(text: str) -> str:
    without_blocks = LEAN_BLOCK_COMMENT_RE.sub("", text)
    lines = [LEAN_LINE_COMMENT_RE.sub("", line).rstrip() for line in without_blocks.splitlines()]
    compact: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        compact.append(line)
        previous_blank = blank
    return "\n".join(compact).strip()


def trim_trailing_attributes(text: str) -> str:
    lines = text.rstrip().splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and lines[-1].strip().startswith("@["):
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()
    return "\n".join(lines).rstrip()


def local_declaration_spans(lines: list[str]) -> list[dict[str, Any]]:
    starts: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines, start=1):
        match = LEAN_DECL_RE.match(line)
        if match:
            starts.append((index, match.group("kind"), match.group("name")))

    spans: list[dict[str, Any]] = []
    for position, (start, kind, name) in enumerate(starts):
        next_start = starts[position + 1][0] if position + 1 < len(starts) else len(lines) + 1
        spans.append({"start": start, "end": next_start - 1, "kind": kind, "name": name})
    return spans


def local_declaration_name(name: str) -> str:
    return name.split(".")[-1]


def local_dependency_tokens(snippets: list[str]) -> set[str]:
    tokens: set[str] = set()
    for snippet in snippets:
        tokens.update(LEAN_IDENTIFIER_RE.findall(snippet))
    return {token for token in tokens if token not in COMMON_LOCAL_DEPENDENCY_NAMES}


def local_name_referenced_by_snippets(snippets: list[str], name: str) -> bool:
    local = local_declaration_name(name)
    if local in COMMON_LOCAL_DEPENDENCY_NAMES:
        return False
    pattern = re.compile(rf"\b{re.escape(local)}\b")
    for snippet in snippets:
        for match in pattern.finditer(snippet):
            if match.start() > 0 and snippet[match.start() - 1] == ".":
                prefix = snippet[: match.start() - 1]
                qualifier_match = re.search(r"([A-Za-z_][A-Za-z0-9_']*)\s*$", prefix)
                qualifier = qualifier_match.group(1) if qualifier_match else ""
                if qualifier and qualifier[0].isupper():
                    continue
            return True
    return False


def structure_support_spans(
    *,
    spans: list[dict[str, Any]],
    structure_spans: list[dict[str, Any]],
    withheld_names: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0 or not structure_spans:
        return []
    support: list[dict[str, Any]] = []
    for structure in structure_spans:
        structure_start = int(structure["start"])
        for span in spans:
            if int(span["start"]) <= structure_start:
                continue
            name = local_declaration_name(str(span["name"]))
            if name in withheld_names or name not in STRUCTURE_SUPPORT_LOCAL_NAMES:
                continue
            support.append(span)
            if len(support) >= limit:
                return support
    return support


def declaration_start_with_attributes(lines: list[str], start: int) -> int:
    index = start - 2
    while index >= 0:
        if not lines[index].strip():
            break
        if not lines[index].strip().startswith("@["):
            break
        index -= 1
    return index + 2


def local_predecessor_row(
    *,
    lines: list[str],
    span: dict[str, Any],
    relative_path: str,
    end_limit: int,
    context_source: str,
) -> dict[str, Any]:
    start = int(span["start"])
    snippet_start = declaration_start_with_attributes(lines, start)
    end = min(int(span["end"]), end_limit)
    declaration_text = "\n".join(lines[snippet_start - 1 : min(end, start + 39)]).rstrip()
    snippet = trim_trailing_attributes(strip_lean_comments(declaration_text))
    return {
        "name": span["name"],
        "kind": span["kind"],
        "path": relative_path,
        "line_range": [snippet_start, end],
        "lean_snippet": snippet[:3000],
        "snippet_truncated": end - start + 1 > 40 or len(snippet) > 3000,
        "context_source": context_source,
        "benchmark_honesty": (
            "Uses post-hoc target file/line placement only to select earlier declarations; "
            "current-unit aligned/referencing declarations are omitted."
        ),
    }


def withheld_local_declaration_names(row: dict[str, Any]) -> dict[str, set[str]]:
    """Return same-source Lean declarations that must not become support context."""

    hidden_by_path: dict[str, set[str]] = {}
    alignment = row.get("posthoc_lean_alignment", {}) or {}
    for key in ("aligned_lean_declarations", "referencing_lean_declarations"):
        for declaration in alignment.get(key) or []:
            path = str(declaration.get("path") or "")
            full_name = str(declaration.get("full_name") or declaration.get("name") or "")
            local_name = local_declaration_name(full_name)
            if path and local_name:
                hidden_by_path.setdefault(path, set()).add(local_name)
    return hidden_by_path


def target_file_predecessor_declarations(
    row: dict[str, Any],
    *,
    project_root: Path | None,
    limit: int = 4,
    dependency_limit: int = 4,
    structure_support_limit: int = 2,
) -> list[dict[str, Any]]:
    """Collect same-file declarations before the hidden target declaration.

    This uses post-hoc placement metadata only to define a cut line. It must not
    expose current-unit target or target-like declarations themselves.
    """

    if project_root is None or limit <= 0:
        return []
    alignment = row.get("posthoc_lean_alignment", {}) or {}
    aligned = alignment.get("aligned_lean_declarations", []) or []
    withheld_by_path = withheld_local_declaration_names(row)
    target_locations: dict[str, int] = {}
    for declaration in aligned:
        path = str(declaration.get("path") or "")
        line_range = declaration.get("line_range") or []
        if not path or len(line_range) != 2:
            continue
        start = int(line_range[0])
        target_locations[path] = min(start, target_locations.get(path, start))

    predecessors: list[dict[str, Any]] = []
    for relative_path, target_start in sorted(target_locations.items()):
        path = project_root / relative_path
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        withheld_names = withheld_by_path.get(relative_path, set())
        spans = [
            span
            for span in local_declaration_spans(lines)
            if int(span["start"]) < target_start and local_declaration_name(str(span["name"])) not in withheld_names
        ]
        selected_spans = spans[-limit:]
        selected_names = {str(span["name"]) for span in selected_spans}
        selected_snippets = [
            local_predecessor_row(
                lines=lines,
                span=span,
                relative_path=relative_path,
                end_limit=target_start - 1,
                context_source="same_file_before_selected_unit_line",
            )
            for span in selected_spans
        ]
        selected_snippet_texts = [row["lean_snippet"] for row in selected_snippets]
        dependency_tokens = local_dependency_tokens(selected_snippet_texts)
        dependency_spans: list[dict[str, Any]] = []
        if dependency_limit > 0 and dependency_tokens:
            for span in spans:
                name = str(span["name"])
                if name in selected_names:
                    continue
                if local_name_referenced_by_snippets(selected_snippet_texts, name):
                    dependency_spans.append(span)
            dependency_spans = dependency_spans[-dependency_limit:]
        support_spans = structure_support_spans(
            spans=spans,
            structure_spans=[span for span in [*dependency_spans, *selected_spans] if span.get("kind") == "structure"],
            withheld_names=withheld_names,
            limit=structure_support_limit,
        )
        for span in [*dependency_spans, *support_spans, *selected_spans]:
            predecessors.append(
                local_predecessor_row(
                    lines=lines,
                    span=span,
                    relative_path=relative_path,
                    end_limit=target_start - 1,
                    context_source=(
                        "same_file_dependency_of_local_predecessor"
                        if span in dependency_spans
                        else "same_file_structure_support"
                        if span in support_spans
                        else "same_file_before_selected_unit_line"
                    ),
                )
            )
    return predecessors[-(limit + max(dependency_limit, 0) + max(structure_support_limit, 0)) :]


def project_declarations_for_prior(
    prior: dict[str, Any],
    *,
    project_root: Path | None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    declarations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    alignment = prior.get("posthoc_lean_alignment", {})
    sources = [
        ("aligned_prior_declaration", alignment.get("aligned_lean_declarations", [])),
        ("referencing_prior_declaration", alignment.get("referencing_lean_declarations", [])),
    ]
    for source, decls in sources:
        for decl in decls or []:
            key = (str(decl.get("path") or ""), str(decl.get("full_name") or ""))
            if key in seen:
                continue
            declarations.append(declaration_stub(decl, project_root=project_root, source=source))
            seen.add(key)
            if len(declarations) >= limit:
                return declarations
    return declarations


def candidate_context_refs(row: dict[str, Any], *, max_previous_same_file: int | None) -> list[dict[str, Any]]:
    candidates = row.get("context_candidates", {})
    refs: list[dict[str, Any]] = []
    refs.extend(candidates.get("referenced_source_units", []))
    previous_same_file = list(candidates.get("previous_same_file_source_units", []))
    if max_previous_same_file is not None and max_previous_same_file >= 0:
        previous_same_file = previous_same_file[-max_previous_same_file:] if max_previous_same_file else []
    refs.extend(previous_same_file)
    return refs


def prior_project_context(
    row: dict[str, Any],
    rows_by_id: dict[str, dict[str, Any]],
    *,
    project_root: Path | None = None,
    max_previous_same_file: int | None = 2,
    declarations_per_prior_unit: int = 4,
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []

    for ref in candidate_context_refs(row, max_previous_same_file=max_previous_same_file):
        unit_id = ref.get("unit_id")
        if not unit_id:
            continue
        if str(unit_id) == str(row.get("id") or ""):
            continue
        prior = rows_by_id.get(str(unit_id))
        if prior is None:
            continue
        declarations = project_declarations_for_prior(prior, project_root=project_root, limit=declarations_per_prior_unit)
        if declarations:
            contexts.append(
                {
                    "source_unit_id": prior["id"],
                    "source_labels": prior["source_unit"].get("labels", []),
                    "reason": (
                        "Earlier or explicitly referenced source unit with project declarations. "
                        "These declarations are prior context, not aligned target declarations for the selected unit."
                    ),
                    "project_declarations": declarations,
                }
            )
    return contexts


def local_file_context_candidates(prior_contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect compact local Lean context from safe prior project declarations."""

    seen: set[tuple[str, str, str, tuple[int, ...]]] = set()
    candidates: list[dict[str, Any]] = []
    for context in prior_contexts:
        for decl in context.get("project_declarations") or []:
            for span in decl.get("file_context") or []:
                line_range = tuple(int(value) for value in span.get("line_range") or [])
                key = (
                    str(span.get("path") or ""),
                    str(span.get("kind") or ""),
                    str(span.get("name") or ""),
                    line_range,
                )
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    {
                        "path": span.get("path"),
                        "kind": span.get("kind"),
                        "name": span.get("name"),
                        "line_range": span.get("line_range"),
                        "source": "file_context_from_prior_project_declaration",
                        "reason": (
                            "Local Lean context observed around safe prior project declarations. "
                            "Use as placement/style guidance; do not assume hidden target declarations."
                        ),
                    }
                )
    return candidates


def strip_declaration_file_context(prior_contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stripped_contexts: list[dict[str, Any]] = []
    for context in prior_contexts:
        stripped_context = dict(context)
        stripped_declarations = []
        for declaration in context.get("project_declarations") or []:
            stripped = dict(declaration)
            stripped.pop("file_context", None)
            stripped_declarations.append(stripped)
        stripped_context["project_declarations"] = stripped_declarations
        stripped_contexts.append(stripped_context)
    return stripped_contexts


def previous_source_context(
    row: dict[str, Any],
    rows_by_id: dict[str, dict[str, Any]],
    *,
    max_previous_same_file: int | None = 2,
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    seen: set[str] = set()

    for ref in candidate_context_refs(row, max_previous_same_file=max_previous_same_file):
        unit_id = str(ref.get("unit_id") or "")
        if not unit_id or unit_id in seen:
            continue
        prior = rows_by_id.get(unit_id)
        if prior is None:
            continue
        contexts.append(
            {
                "reason": "Earlier or explicitly referenced source theorem-like unit.",
                "source_unit": public_source_unit(prior),
            }
        )
        seen.add(unit_id)
    return contexts


def build_messages(
    selected: list[SelectedUnit],
    all_rows: list[dict[str, Any]],
    *,
    source_units: list[dict[str, Any]] | None = None,
    project_root: Path | None = None,
    max_previous_same_file: int | None = 2,
    declarations_per_prior_unit: int = 4,
    local_predecessor_declarations: int = 4,
    local_predecessor_dependency_declarations: int = 4,
) -> list[dict[str, str]]:
    source_rows_by_id = unit_index(source_units or all_rows)
    system = (
        "You are a Lean 4/Mathlib context-planning agent. Prepare a compact "
        "context pack for formalizing a LaTeX theorem-like source unit. The "
        "target Lean declarations aligned to the selected source unit are "
        "withheld. Return exactly one JSON object."
    )
    payload = {
        "task": (
            "For each LaTeX source unit, decompose the source into ordered Lean "
            "declaration tasks and select tight context for each task. The "
            "context inventory must be separate: source text, previous book/source "
            "statements, previous project declarations, local file/import/style "
            "context, and selected Mathlib APIs."
        ),
        "schema": {
            "units": [
                {
                    "unit_key": "unit-001",
                    "source_focus_summary": "short summary",
                    "formalization_risks": ["source ambiguity, missing notation, broad multi-part theorem"],
                    "planned_declarations": [
                        {
                            "task_id": "unit-001-task-1",
                            "kind": "def|theorem|lemma|instance|notation|unknown",
                            "role": "main_claim|same_unit_helper",
                            "source_part": "whole unit or part marker",
                            "target_statement_sketch": (
                                "prose mathematical target sketch; do not write exact Lean syntax, "
                                "declaration names, or guessed API argument order"
                            ),
                            "depends_on_task_ids": [
                                "earlier same-unit helper task ids that this task should use"
                            ],
                            "needed_source_context": ["source labels/statements"],
                            "needed_project_context": [
                                {
                                    "name": "previous project declaration if provided or likely needed",
                                    "why_needed": "supporting theorem/definition/notation",
                                }
                            ],
                            "needed_mathlib_context": [
                                {
                                    "name_or_query": "exact Mathlib name or narrow search query",
                                    "expected_signature_or_shape": "expected type/signature/docstring",
                                    "why_needed": "definition/proof/tactic support",
                                }
                            ],
                            "missing_or_uncertain_context": ["what a second lookup round should resolve"],
                        }
                    ],
                    "context_pack_size_risk": "low|medium|high",
                    "selector_confidence": 0.0,
                }
            ]
        },
        "rules": [
            "Do not infer or reveal hidden target Lean declaration names for the selected unit.",
            "Do not write theorem/lemma Lean code in target_statement_sketch; exact API syntax belongs in needed_mathlib_context and will be hydrated by tools.",
            "Do not bundle all source parts into one conjunction unless the source unit itself requires that shape.",
            "When a source theorem states a result for several cases such as upper/lower, left/right, or an `or` hypothesis, prefer separate narrow planned_declarations for each case when the checked APIs or natural Lean statements are case-specific. Do not collapse case-specific source claims into one disjunctive theorem just to reduce task count.",
            "If a broad source unit needs a construction or auxiliary lemma before the main claim can be stated/proved, split it into ordered planned_declarations with role same_unit_helper followed by role main_claim and explicit depends_on_task_ids.",
            "Same-unit helper tasks are declarations for the later generator to create from the selected source unit, not prior context. Do not use hidden aligned/referencing Lean names for them.",
            "Use previous project declarations only if they are shown under prior_project_context.",
            "Use local_file_predecessor_declarations only as same-file helper/style context; the selected unit's aligned/referencing target declarations are omitted.",
            "Do not treat Mathlib as the only context; enumerate source/project/local/Mathlib context separately.",
            "Prefer exact Mathlib names when known; otherwise give a narrow query plus expected signature shape.",
            "Keep added context tight: prefer a few thousand tokens or less per source unit.",
        ],
        "units": [],
    }

    for item in selected:
        row = item.row
        prior_contexts = prior_project_context(
            row,
            source_rows_by_id,
            project_root=project_root,
            max_previous_same_file=max_previous_same_file,
            declarations_per_prior_unit=declarations_per_prior_unit,
        )
        payload["units"].append(
            {
                "unit_key": item.public_key,
                "source_unit": public_source_unit(row),
                "source_context_candidates": {
                    "selected_context_refs": candidate_context_refs(
                        row,
                        max_previous_same_file=max_previous_same_file,
                    ),
                    "selection_policy": (
                        "All explicit referenced source units plus the most recent same-file predecessor "
                        "units up to max_previous_same_file_context."
                    ),
                    "max_previous_same_file_context": max_previous_same_file,
                },
                "previous_source_context": previous_source_context(
                    row,
                    source_rows_by_id,
                    max_previous_same_file=max_previous_same_file,
                ),
                "prior_project_context": strip_declaration_file_context(prior_contexts),
                "local_file_context_candidates": local_file_context_candidates(prior_contexts),
                "local_file_predecessor_declarations": target_file_predecessor_declarations(
                    row,
                    project_root=project_root,
                    limit=local_predecessor_declarations,
                    dependency_limit=local_predecessor_dependency_declarations,
                ),
                "benchmark_policy": {
                    "target_lean_available_to_selector": False,
                    "posthoc_alignment_hidden": True,
                    "local_file_context_source": "prior_project_declarations_only",
                    "local_file_predecessor_declaration_source": (
                        "same Lean file declarations before selected unit placement line, plus shallow "
                        "same-file dependencies and nearby structure extensionality support referenced by "
                        "those predecessor snippets; benchmark-only placement metadata, current-unit "
                        "aligned/referencing declarations omitted"
                    ),
                },
            }
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)},
    ]


def extract_message_content(response: Any) -> str:
    try:
        return str(response.choices[0].message.content or "")
    except Exception:
        return ""


def maybe_parse_json(text: str) -> tuple[dict[str, Any] | None, str | None]:
    stripped = text.strip()
    if not stripped:
        return None, "empty_output"
    try:
        return json.loads(stripped), None
    except json.JSONDecodeError as exc:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(stripped[start : end + 1]), None
            except json.JSONDecodeError:
                pass
        return None, str(exc)


def response_cost_summary(response: Any, model: str) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    raw_usage = usage.model_dump() if hasattr(usage, "model_dump") else dict(usage or {})
    return {
        "model": model,
        "usage": raw_usage,
        "openrouter_reported_cost": raw_usage.get("cost"),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.records)
    source_units = read_jsonl(args.source_units) if args.source_units else rows
    selected = select_units(rows, args.limit, offset=args.offset, unit_ids=args.unit_id)
    messages = build_messages(
        selected,
        rows,
        source_units=source_units,
        project_root=args.project_root,
        max_previous_same_file=args.max_previous_same_file_context,
        declarations_per_prior_unit=args.prior_project_declarations_per_unit,
        local_predecessor_declarations=args.local_predecessor_declarations,
        local_predecessor_dependency_declarations=args.local_predecessor_dependency_declarations,
    )
    run_dir = args.output
    batch_dir = run_dir / "batch-001"
    eval_dir = run_dir / "eval"
    batch_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)

    request_payload: dict[str, Any] = {
        "model": args.model,
        "messages": messages,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "response_format": {"type": "json_object"},
    }
    if args.reasoning_effort:
        request_payload["extra_body"] = {"reasoning": {"effort": args.reasoning_effort, "exclude": True}}
    write_json(batch_dir / "context-selection-payload.json", request_payload)
    write_jsonl(eval_dir / "selected-units.jsonl", [item.row for item in selected])

    summary: dict[str, Any] = {
        "schema_version": "repoprover.latex_statement_context_selection.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_input": len(rows),
        "units_selected": len(selected),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "budget_only": args.budget_only,
        "paid_call_made": False,
        "valid_json": False,
        "parse_error": None,
        "output_path": str(run_dir),
    }

    if args.budget_only:
        write_json(eval_dir / "context-selection-results.json", summary)
        return summary

    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    client = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url=args.base_url)
    started = time.monotonic()
    response = client.chat.completions.create(**request_payload)
    summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
    summary["paid_call_made"] = True
    write_json(batch_dir / "context-selection-response.json", response.model_dump())
    content = extract_message_content(response)
    (batch_dir / "context-selection-assistant-content.txt").write_text(content, encoding="utf-8")
    parsed, parse_error = maybe_parse_json(content)
    summary["parse_error"] = parse_error
    summary["valid_json"] = parsed is not None
    summary["cost_summary"] = response_cost_summary(response, args.model)
    if parsed is not None:
        write_json(batch_dir / "context-selection-output.json", parsed)
    write_json(eval_dir / "context-selection-results.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=REPO_ROOT / "docs/latex-statement-gold-candidates.jsonl")
    parser.add_argument("--source-units", type=Path, default=REPO_ROOT / "docs/latex-statement-units.jsonl")
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--offset", type=int, default=0, help="Skip this many gold candidates before selection.")
    parser.add_argument("--unit-id", action="append", help="Select exact source-unit id; may be repeated.")
    parser.add_argument(
        "--max-previous-same-file-context",
        type=int,
        default=2,
        help="Include at most this many most-recent same-file predecessor units; explicit references are always kept.",
    )
    parser.add_argument(
        "--prior-project-declarations-per-unit",
        type=int,
        default=4,
        help="Maximum prior project declarations to expose per selected prior source unit.",
    )
    parser.add_argument(
        "--local-predecessor-declarations",
        type=int,
        default=4,
        help=(
            "Maximum same-Lean-file declarations before the hidden target line to expose as local "
            "predecessor context. Uses post-hoc placement metadata but omits the target declaration."
        ),
    )
    parser.add_argument(
        "--local-predecessor-dependency-declarations",
        type=int,
        default=4,
        help=(
            "Maximum earlier same-file declarations to add when their names are referenced by selected "
            "local predecessor snippets. Uses the same target-blind placement cut as local predecessors."
        ),
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--reasoning-effort",
        help="OpenRouter reasoning effort override; use 'none' for schema-bound JSON selection.",
    )
    parser.add_argument("--budget-only", action="store_true")
    args = parser.parse_args()

    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
