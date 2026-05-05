#!/usr/bin/env python3
"""Run a target-statement-withheld source-to-Lean live evaluation.

This is stricter than oracle proof-fill: prompts include the selected TeX/source
chunk plus prefix Lean context, but not the target Lean statement/skeleton/name.
For theorem/lemma records, grading appends the gold statement in a private check
name and tries to prove it from the model-generated theorem. The gold statement
is used only by the grader, never in the prompt.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.materialize_minimal_context_smoke import (  # noqa: E402
    DECL_RE,
    SelectedRecord,
    copy_lake_cache,
    copy_project_config,
    context_close_commands,
    load_jsonl,
    read_line_range,
    render_ordered_context_and_predecessors,
)
from scripts.run_minimal_context_eval import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_PRICE,
    estimate_payload_cost,
    summarize_openrouter_response_cost,
    write_json,
    write_jsonl,
)
from scripts.review_minimal_context_records import DEFAULT_BASE_URL  # noqa: E402

GENERATED_DECL_RE = re.compile(
    r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
    r"(?:theorem|lemma)\s+(?P<name>[^\s:\{\(\[]+)",
    re.MULTILINE,
)
BLOCK_BOUNDARY_RE = re.compile(
    r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
    r"(?:(?:theorem|lemma|def|abbrev|instance|class|structure|inductive|example)\b|(?:scoped\s+)?notation\b|end\b)"
)
LOCAL_EXAMPLE_RE = re.compile(r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*(?:example|theorem|lemma)\b")
SCOPED_NOTATION_RE = re.compile(r"scoped\s+notation\s+(?P<lhs>.*?)\s*=>\s*(?P<rhs>.*)$")
PART_LABEL_RE = re.compile(r"\.([a-z])$")
CONTEXT_NOTATION_HEADER_RE = re.compile(r"^-- File context: (?P<path>.*):(?P<start>\d+)-(?P<end>\d+) \(notation\)$")
LOCAL_MODULE_PREFIX = "AlgebraicCombinatorics."
CONTEXT_MODES = ("target-comment", "source-only")
TEX_ENV_RE = re.compile(r"\\begin\{(?P<env>theorem|lemma|proposition|definition|corollary|example|equation|align\*?)\}")
TEX_ENV_BOUNDARY_RE = re.compile(
    r"\\(?P<kind>begin|end)\{(?P<env>theorem|lemma|proposition|definition|corollary|example|equation|align\*?)\}"
)
TEX_LABEL_RE = re.compile(r"\\label\{(?P<label>[^}]+)\}")
TEX_REF_RE = re.compile(r"\\(?:ref|eqref)\{(?P<label>[^}]+)\}")
TEX_PART_RE = re.compile(r"\\textbf\{\((?P<part>[a-z])\)\}|\\item\s+(?:\\textbf\{\((?P<item_part>[a-z])\)\})?")
SOURCE_KEYWORD_PATTERNS = [
    ("finite coefficient", re.compile(r"\bfinite\b|all but finitely|first\s+\$?n|coefficient of")),
    ("summability", re.compile(r"summable|well-defined|all but finitely|infinite sum")),
    ("limit", re.compile(r"limit|lim|converge|stabiliz")),
    ("substitution", re.compile(r"substitut|composition|\\circ")),
    ("negative binomial", re.compile(r"negative|binomial|\\dbinom|choose")),
    ("inverse power", re.compile(r"inverse|\^-|1\s*\+\s*x|\(1\+x\)")),
    ("partition", re.compile(r"partition|parts|largest part|transpose")),
    ("permutation", re.compile(r"permutation|transposition|swap|cycle|power")),
    ("shifted coefficient", re.compile(r"shift|x\^\{?k\}?|coefficient")),
]


@dataclass(frozen=True)
class SourceEvalRecord:
    index: int
    selected: SelectedRecord


def _source_line_count(row: dict[str, Any]) -> int:
    total = 0
    for span in row.get("minimal_context", {}).get("source_spans", []):
        start, end = span.get("line_range", [0, 0])
        total += max(0, int(end) - int(start) + 1)
    return total


def _output_line_count(row: dict[str, Any]) -> int:
    start, end = row.get("output", {}).get("line_range", [0, 0])
    return max(0, int(end) - int(start) + 1)


def _corpus_sort_key(row: dict[str, Any]) -> tuple[str, int, str]:
    return (
        str(row.get("output", {}).get("lean_path", "")),
        int(row.get("output", {}).get("line_range", [0, 0])[0]),
        str(row.get("id") or row.get("record_id")),
    )


def _easy_sort_key(row: dict[str, Any]) -> tuple[int, int, int, str, int, str]:
    return (
        _source_line_count(row),
        _output_line_count(row),
        len(row.get("minimal_context", {}).get("lean_predecessors", [])),
        str(row.get("alignment", {}).get("source_method", "")),
        int(row.get("output", {}).get("line_range", [0, 0])[0]),
        str(row.get("id") or row.get("record_id")),
    )


def _spread_pick(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0 or limit >= len(candidates):
        return candidates
    if limit == 1:
        return [candidates[0]]
    return [candidates[round(i * (len(candidates) - 1) / (limit - 1))] for i in range(limit)]


def select_source_statement_records(
    rows: list[dict[str, Any]], limit: int, sample_mode: str = "corpus-spread"
) -> list[SourceEvalRecord]:
    candidates = [
        row
        for row in rows
        if len(row.get("output", {}).get("declaration_names", [])) == 1
        and row.get("output", {}).get("chunk_kind") in {"theorem", "lemma"}
        and row.get("minimal_context", {}).get("source_spans")
    ]
    if sample_mode == "easy":
        picked = sorted(candidates, key=_easy_sort_key)
        if limit > 0:
            picked = picked[:limit]
    elif sample_mode == "stratified-easy":
        by_ease = sorted(candidates, key=_easy_sort_key)
        pool_size = len(by_ease) if limit <= 0 else min(len(by_ease), max(limit * 4, limit))
        picked = _spread_pick(sorted(by_ease[:pool_size], key=_corpus_sort_key), limit)
    elif sample_mode == "corpus-spread":
        picked = _spread_pick(sorted(candidates, key=_corpus_sort_key), limit)
    else:
        raise ValueError(f"unknown sample mode: {sample_mode}")
    return [SourceEvalRecord(index=i, selected=SelectedRecord(row)) for i, row in enumerate(picked, start=1)]


def source_snippets(project_root: Path, record: SelectedRecord) -> list[dict[str, Any]]:
    snippets: list[dict[str, Any]] = []
    for span in record.source_spans:
        start, end = [int(value) for value in span["line_range"]]
        snippets.append(
            {
                "path": span["path"],
                "line_range": [start, end],
                "labels": span.get("labels", []),
                "snippet": read_line_range(project_root / str(span["path"]), (start, end)),
            }
        )
    return snippets


def _tex_plain_text(text: str) -> str:
    plain = re.sub(r"%.*", "", text)
    plain = re.sub(r"\\(?:label|ref|eqref)\{[^}]+\}", " ", plain)
    plain = re.sub(r"\\(?:begin|end)\{[^}]+\}", " ", plain)
    plain = re.sub(r"\\textbf\{([^}]*)\}", r"\1", plain)
    plain = re.sub(r"\\emph\{([^}]*)\}", r"\1", plain)
    plain = re.sub(r"\\[A-Za-z]+\*?(?:\[[^]]*\])?", " ", plain)
    plain = re.sub(r"[{}$]", " ", plain)
    return re.sub(r"\s+", " ", plain).strip()


def _sentence_excerpts(text: str, *, count: int = 2) -> list[str]:
    plain = _tex_plain_text(text)
    if not plain:
        return []
    pieces = [piece.strip() for piece in re.split(r"(?<=[.!?])\s+", plain) if piece.strip()]
    if not pieces:
        return [plain[:260]]
    return [piece[:260] for piece in pieces[:count]]


def _part_excerpts(text: str) -> list[dict[str, str]]:
    parts: list[dict[str, str]] = []
    matches = list(TEX_PART_RE.finditer(text))
    for index, match in enumerate(matches):
        prefix = text[max(0, match.start() - 90) : match.start()]
        if "\\ref{" in prefix or "\\eqref{" in prefix:
            continue
        part = match.group("part") or match.group("item_part") or ""
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else min(len(text), start + 500)
        excerpt = _tex_plain_text(text[start:end])[:260]
        parts.append({"part": part, "excerpt": excerpt})
    return parts[:8]


def _tex_environment_balance(text: str) -> dict[str, list[str]]:
    stack: list[str] = []
    unmatched_end: list[str] = []
    for match in TEX_ENV_BOUNDARY_RE.finditer(text):
        kind = match.group("kind")
        env = match.group("env")
        if kind == "begin":
            stack.append(env)
            continue
        if stack and stack[-1] == env:
            stack.pop()
        elif env in stack:
            while stack:
                popped = stack.pop()
                if popped == env:
                    break
        else:
            unmatched_end.append(env)
    return {"unclosed": stack, "unmatched_end": unmatched_end}


def tex_source_focus(snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract focus cues from TeX/source snippets without using Lean targets."""

    focus_rows: list[dict[str, Any]] = []
    for snippet in snippets:
        text = str(snippet.get("snippet") or "")
        line_range = list(snippet.get("line_range") or [])
        line_count = 0
        if len(line_range) == 2:
            line_count = int(line_range[1]) - int(line_range[0]) + 1
        lower_text = text.lower()
        cues = [name for name, pattern in SOURCE_KEYWORD_PATTERNS if pattern.search(lower_text)]
        row = {
            "path": snippet.get("path"),
            "line_range": line_range,
            "line_count": line_count,
            "span_labels": list(snippet.get("labels") or []),
            "declared_labels": TEX_LABEL_RE.findall(text),
            "referenced_labels": TEX_REF_RE.findall(text)[:12],
            "environments": [match.group("env") for match in TEX_ENV_RE.finditer(text)],
            "part_markers": _part_excerpts(text),
            "keyword_cues": cues,
            "opening_excerpts": _sentence_excerpts(text[:1200]),
            "closing_excerpts": _sentence_excerpts(text[-1200:]),
            "span_risks": [],
            "policy": "derived only from provided TeX/source snippet; no target Lean comments, names, or statements",
        }
        if line_count >= 25:
            row["span_risks"].append("broad_source_span")
        env_balance = _tex_environment_balance(text)
        for env in env_balance["unclosed"]:
            row["span_risks"].append(f"snippet_ends_with_unclosed_environment:{env}")
        for env in env_balance["unmatched_end"]:
            row["span_risks"].append(f"snippet_starts_after_environment_begin:{env}")
        focus_rows.append(row)
    return focus_rows


def _record_comment_labels(record: SelectedRecord) -> list[str]:
    return [str(label) for label in record.row.get("alignment", {}).get("comment_labels", [])]


def _source_span_labels(record: SelectedRecord) -> list[str]:
    labels: list[str] = []
    for span in record.source_spans:
        labels.extend(str(label) for label in span.get("labels", []))
    return labels


def _strip_doc_comment(lines: list[str]) -> str:
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        stripped = re.sub(r"^/--\s?", "", stripped)
        stripped = re.sub(r"^/-!\s?", "", stripped)
        stripped = re.sub(r"\s?-/\s*$", "", stripped)
        stripped = re.sub(r"^\*\s?", "", stripped)
        cleaned.append(stripped.rstrip())
    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return "\n".join(cleaned)


def _preceding_doc_comment(project_root: Path, record: SelectedRecord) -> dict[str, Any] | None:
    lean_file = project_root / record.lean_path
    if not lean_file.exists():
        return None
    lines = lean_file.read_text(encoding="utf-8").splitlines()
    declaration_index = record.line_range[0] - 1
    for candidate_index in range(record.line_range[0] - 1, min(record.line_range[1], len(lines))):
        if DECL_RE.match(lines[candidate_index]):
            declaration_index = candidate_index
            break
    index = declaration_index - 1
    while index >= 0 and not lines[index].strip():
        index -= 1
    if index < 0:
        return None

    start = index
    if lines[index].strip().endswith("-/"):
        while start >= 0 and not lines[start].lstrip().startswith(("/--", "/-!")):
            start -= 1
        if start < 0:
            return None
    elif lines[index].lstrip().startswith("--"):
        while start > 0 and lines[start - 1].lstrip().startswith("--"):
            start -= 1
    else:
        return None

    text = _strip_doc_comment(lines[start : index + 1])
    if not text:
        return None
    return {
        "path": record.lean_path,
        "line_range": [start + 1, index + 1],
        "text": text,
        "policy": "source-facing Lean doc comment only; target Lean declaration name and statement remain withheld",
    }


def source_focus(project_root: Path, record: SelectedRecord, *, context_mode: str = "target-comment") -> dict[str, Any]:
    if context_mode not in CONTEXT_MODES:
        raise ValueError(f"unknown context mode: {context_mode}")
    source_labels = _source_span_labels(record)
    comment_labels = [] if context_mode == "source-only" else _record_comment_labels(record)
    source_label_set = set(source_labels)
    specific_labels = [
        label
        for label in comment_labels
        if label not in source_label_set and any(label.startswith(f"{source_label}.") for source_label in source_labels)
    ]
    specific_parts = []
    for label in specific_labels:
        match = PART_LABEL_RE.search(label)
        if match:
            specific_parts.append(match.group(1))
    target_comment = None if context_mode == "source-only" else _preceding_doc_comment(project_root, record)
    target_comment_labels = []
    if target_comment is not None:
        target_comment_labels.extend(re.findall(r"Label:\s*([A-Za-z0-9_.-]+(?:\s*\([a-z]\))?)", target_comment["text"]))
        target_comment_labels.extend(re.findall(r"\(([a-z])\)", target_comment["text"]))
    return {
        "source_span_labels": source_labels,
        "record_comment_labels": comment_labels,
        "specific_source_labels": specific_labels,
        "specific_labeled_parts": specific_parts,
        "target_declaration_source_comment": target_comment,
        "target_comment_labels_or_parts": target_comment_labels,
        "context_mode": context_mode,
        "instruction": (
            "If the source snippet contains multiple labeled or numbered parts, formalize only the specific "
            "part/source span indicated by visible source labels or explicit focus metadata. Do not conjoin "
            "all parts unless the record labels identify the whole multi-part result."
            if context_mode == "source-only"
            else "If the source snippet contains multiple labeled or numbered parts, formalize only the specific "
            "part/source span indicated by specific_source_labels, specific_labeled_parts, or "
            "target_declaration_source_comment. Do not conjoin all parts unless the record labels identify "
            "the whole multi-part result. The target_declaration_source_comment is source-facing prose only; "
            "it is not the hidden Lean target statement."
        ),
    }


def _read_context_window(path: Path, line: int, *, before: int = 10, after: int = 24, before_line: int | None = None) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = max(1, line - before)
    end = min(len(lines), line + after)
    if before_line is not None:
        end = min(end, before_line - 1)
    return "\n".join(lines[start - 1 : end]).rstrip()


def _declaration_start(lines: list[str], index: int) -> int:
    start = index
    while start > 0:
        previous = lines[start - 1].strip()
        if previous.startswith("/--") or previous.startswith("@[") or previous.startswith("--") or previous.startswith("/-!"):
            start -= 1
            continue
        if previous and start < index and lines[start].lstrip().startswith(("*", "##")):
            start -= 1
            continue
        break
    return start


def _prior_example_blocks(project_root: Path, record: SelectedRecord, limit: int = 4) -> list[str]:
    lean_file = project_root / record.lean_path
    if not lean_file.exists():
        return []
    lines = lean_file.read_text(encoding="utf-8").splitlines()
    target_start = record.line_range[0]
    source_text = "\n".join(snippet.get("snippet", "") for snippet in source_snippets(project_root, record)).lower()
    keywords = ["submatrix", "submatrixOfFinset"]
    if "diagonal" in source_text:
        keywords.append("diagonal")
    if "minor" in source_text or "det" in source_text:
        keywords.extend([".det", "Matrix.det", "det_", "updateRow", "updateCol"])
    if "column" in source_text or "columns" in source_text or "colop" in source_text:
        keywords.extend(["det_swap_cols", "det_zero_col", "det_add_col", "det_add_smul_col", "updateCol"])
    if "laurent" in source_text or "x^{\\pm" in source_text or "x,x^{-1}" in source_text:
        keywords.extend(["LaurentPolynomial", "K[T;T⁻¹]", "T_mul", "T_zero"])
    if "coefficient" in source_text or "\\left[  x^" in source_text or "fps" in source_text:
        keywords.extend(["coeff", "PowerSeries.X", "coeff_X", "coeff_one_X"])
    if "binom" in source_text or "choose" in source_text or "pascal" in source_text or "\\binom" in source_text:
        keywords.extend(["Ring.choose", "Nat.choose", "choose_succ_succ", "pascal_identity"])
    if "tableau" in source_text or "content" in source_text or "x_t" in source_text:
        keywords.extend(["Tableau", "contentTableau", "xPow", "monomialTableau"])

    starts: list[int] = []
    for index, line in enumerate(lines[: target_start - 1]):
        if LOCAL_EXAMPLE_RE.match(line):
            starts.append(index)
    candidates: list[tuple[tuple[int, int], str]] = []
    for offset, start_index in enumerate(starts):
        end_index = starts[offset + 1] if offset + 1 < len(starts) else target_start - 1
        block_start = _declaration_start(lines, start_index)
        block_lines = _trim_trailing_annotation_blocks(lines[block_start:end_index])
        if len(block_lines) > 45:
            continue
        block = "\n".join(block_lines).rstrip()
        score = sum(1 for keyword in keywords if keyword in block)
        if score == 0:
            continue
        candidates.append(((score, start_index), block))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [block for _, block in candidates[:limit]]


def _source_keywords(project_root: Path, record: SelectedRecord) -> list[str]:
    source_text = "\n".join(snippet.get("snippet", "") for snippet in source_snippets(project_root, record)).lower()
    labels = " ".join(_source_span_labels(record) + _record_comment_labels(record)).lower()
    combined = f"{source_text}\n{labels}"
    keywords = ["submatrix", "submatrixOfFinset"]
    if "diagonal" in combined:
        keywords.append("diagonal")
    if "minor" in combined or "det" in combined:
        keywords.extend([".det", "Matrix.det", "det_", "updateRow", "updateCol"])
    if "column" in combined or "columns" in combined or "colop" in combined:
        keywords.extend(["det_swap_cols", "det_zero_col", "det_add_col", "det_add_smul_col", "updateCol"])
    if "row" in combined or "rowop" in combined:
        keywords.extend(["det_swap_rows", "det_zero_row", "det_add_row", "det_add_smul_row", "updateRow"])
    if "laurent" in combined or "x^{\\pm" in combined or "x,x^{-1}" in combined:
        keywords.extend(["LaurentPolynomial", "K[T;T⁻¹]", "T_mul", "T_zero"])
    if "coefficient" in combined or "\\left[  x^" in combined or "fps" in combined:
        keywords.extend(["coeff", "PowerSeries.X", "coeff_X", "coeff_one_X"])
    if "binom" in combined or "choose" in combined or "pascal" in combined or "\\binom" in combined:
        keywords.extend(["Ring.choose", "Nat.choose", "choose_succ_succ", "pascal_identity"])
    if "tableau" in combined or "content" in combined or "x_t" in combined:
        keywords.extend(["Tableau", "contentTableau", "xPow", "monomialTableau"])
    if "substitution" in combined or "subst" in combined or "comp" in combined or "∘" in combined:
        keywords.extend(["subst", "HasSubst", "coeff_subst", "fps_comp_coeff", "fps_subs", "subst_X"])
    if "bivar" in combined or "multivar" in combined or "y^" in combined or "embedunivinbiv" in combined:
        keywords.extend(["embedUnivInBiv", "coeff_embedUnivInBiv", "BivFPS", "Finsupp.single"])
    if "multipliable" in combined or "infprod" in combined or "infinite product" in combined:
        keywords.extend(["Multipliable", "comp_prod", "xnEquiv_comp", "comp_prod_finite", "comp_prod_multipliable"])
    if "simple transposition" in combined or "def.perm.si" in combined or "s_i" in combined:
        keywords.extend(["simpleTransposition", "Equiv.swap", "swap_apply_of_ne_of_ne", "Fin.ext_iff"])
    seen: set[str] = set()
    ordered: list[str] = []
    for keyword in keywords:
        if keyword not in seen:
            ordered.append(keyword)
            seen.add(keyword)
    return ordered


def _prior_named_declaration_blocks(project_root: Path, record: SelectedRecord, limit: int = 4) -> list[str]:
    lean_file = project_root / record.lean_path
    if not lean_file.exists():
        return []
    lines = lean_file.read_text(encoding="utf-8").splitlines()
    target_start = record.line_range[0]
    keywords = _source_keywords(project_root, record)
    prior_blocks: dict[str, tuple[int, int, str]] = {}
    candidates: list[tuple[tuple[int, int], int, int, str, str]] = []
    for index, line in enumerate(lines[: target_start - 1], start=1):
        match = DECL_RE.match(line)
        if not match or match.group("kind") not in {"theorem", "lemma", "def", "abbrev"}:
            continue
        name = str(match.group("name") or "")
        if not name:
            continue
        block = _named_declaration_block(lines, name, before_line=target_start)
        if block is None:
            continue
        start, end, text = block
        if end >= target_start or len(text.splitlines()) > 40:
            continue
        prior_blocks[name] = (start, end, text)
        score = sum(1 for keyword in keywords if keyword in text or keyword in name)
        if score == 0:
            continue
        candidates.append(((score, start), start, end, name, text))
    candidates.sort(key=lambda item: item[0], reverse=True)
    blocks: list[str] = []
    selected = candidates[:limit]
    selected_names = {name for _, _, _, name, _ in selected}
    dependency_names: set[str] = set()
    for _, start, _, name, text in selected:
        for dependency_name, (dependency_start, _, _) in prior_blocks.items():
            if dependency_name == name or dependency_name in selected_names or dependency_start >= start:
                continue
            if re.search(rf"(?<![A-Za-z0-9_']){re.escape(dependency_name)}(?![A-Za-z0-9_'])", text):
                dependency_names.add(dependency_name)
    ordered_items: list[tuple[int, int, str, str]] = [
        (*prior_blocks[name][:2], name, prior_blocks[name][2])
        for name in dependency_names
    ]
    ordered_items.extend((start, end, name, text) for _, start, end, name, text in selected)
    seen: set[str] = set()
    for start, end, name, text in sorted(ordered_items, key=lambda item: item[0]):
        if name in seen:
            continue
        blocks.append(f"-- Local API retrieval: {record.lean_path}:{start}-{end} ({name})\n{text}")
        seen.add(name)
    return blocks


def _imported_label_declaration_blocks(project_root: Path, record: SelectedRecord, limit: int = 3) -> list[str]:
    """Find imported local declarations whose doc comments carry source labels.

    This is intentionally label-driven and skips the target file. It lets prompts
    see already-imported source-aligned APIs, without reading the withheld target
    declaration from the file being generated.
    """

    labels = sorted(
        {label for label in _source_span_labels(record) + _record_comment_labels(record) if label},
        key=len,
        reverse=True,
    )
    if not labels:
        return []

    target_path = Path(record.lean_path)
    blocks: list[tuple[int, str, str]] = []
    seen_names: set[tuple[str, str]] = set()
    for module in record.imports:
        rel_path = local_import_path(str(module))
        if rel_path is None or rel_path == target_path:
            continue
        path = project_root / rel_path
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines, start=1):
            matched_label = next((label for label in labels if label in line), None)
            if matched_label is None:
                continue
            for candidate_index in range(index, min(len(lines), index + 18) + 1):
                match = DECL_RE.match(lines[candidate_index - 1])
                if not match or match.group("kind") not in {"theorem", "lemma", "def", "abbrev"}:
                    continue
                name = str(match.group("name") or "")
                if not name or (str(rel_path), name) in seen_names:
                    break
                block = _named_declaration_block(lines, name, after_line=index)
                if block is None:
                    break
                start, end, text = block
                if len(text.splitlines()) > 90:
                    text = "\n".join(text.splitlines()[:90]).rstrip() + "\n-- ... declaration truncated ..."
                blocks.append(
                    (
                        start,
                        name,
                        f"-- Imported API retrieval by source label `{matched_label}`: {rel_path}:{start}-{end} ({name})\n{text}",
                    )
                )
                seen_names.add((str(rel_path), name))
                break
    blocks.sort(key=lambda item: item[0])
    return [block for _, _, block in blocks[:limit]]


def _notation_surface(lhs: str) -> str:
    parts: list[str] = []
    for match in re.finditer(r'"([^"]*)"|([A-Za-z_][A-Za-z0-9_\']*)', lhs):
        quoted, bare = match.groups()
        parts.append(quoted if quoted is not None else bare)
    return "".join(parts).strip() or lhs


def _rhs_head_identifier(rhs: str) -> str | None:
    match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_']*)\b", rhs)
    return match.group(1) if match else None


def _named_declaration_block(lines: list[str], name: str, *, before_line: int | None = None, after_line: int = 1) -> tuple[int, int, str] | None:
    matches: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines, start=1):
        if index < after_line:
            continue
        if before_line is not None and index >= before_line:
            break
        match = DECL_RE.match(line)
        if not match or match.group("name") != name:
            continue
        start_index = _declaration_start(lines, index - 1)
        end_index = len(lines)
        for next_index in range(index, len(lines)):
            if BLOCK_BOUNDARY_RE.match(lines[next_index]):
                end_index = _declaration_start(lines, next_index)
                break
        if before_line is not None:
            end_index = min(end_index, before_line - 1)
        block_lines = _trim_trailing_annotation_blocks(lines[start_index:end_index])
        block = "\n".join(block_lines).rstrip()
        end_index = start_index + len(block_lines)
        matches.append((start_index + 1, end_index, block))
    return matches[-1] if matches else None


def _trim_trailing_annotation_blocks(lines: list[str]) -> list[str]:
    block_lines = list(lines)
    changed = True
    while changed:
        changed = False
        while block_lines and not block_lines[-1].strip():
            block_lines.pop()
            changed = True
        if not block_lines:
            break
        tail = block_lines[-1].lstrip()
        if tail.startswith(("@[", "--")):
            block_lines.pop()
            changed = True
            continue
        if tail.startswith(("/--", "/-!")):
            block_lines.pop()
            changed = True
            continue
        if tail == "-/" or tail.startswith("-/") or tail.endswith("-/"):
            start = len(block_lines) - 1
            while start >= 0 and not block_lines[start].lstrip().startswith(("/--", "/-!")):
                start -= 1
            if start >= 0:
                del block_lines[start:]
                changed = True
    return block_lines


def _notation_support_blocks(project_root: Path, rel_path: str, notation_line_number: int, target_line: int) -> list[str]:
    path = project_root / rel_path
    lines = path.read_text(encoding="utf-8").splitlines()
    notation_line = lines[notation_line_number - 1]
    match = SCOPED_NOTATION_RE.search(notation_line)
    if not match:
        return []
    helper_name = _rhs_head_identifier(match.group("rhs"))
    if not helper_name:
        return []

    blocks: list[str] = []
    helper_block = _named_declaration_block(lines, helper_name, before_line=notation_line_number)
    if helper_block is not None:
        start, end, text = helper_block
        blocks.append(f"-- Local notation support: {rel_path}:{start}-{end} ({helper_name})\n{text}")

    apply_block = _named_declaration_block(
        lines,
        f"{helper_name}_apply",
        after_line=notation_line_number + 1,
        before_line=target_line,
    )
    if apply_block is not None:
        start, end, text = apply_block
        blocks.append(f"-- Local notation support: {rel_path}:{start}-{end} ({helper_name}_apply)\n{text}")
    return blocks


def _declaration_names_in_text(text: str) -> set[str]:
    names: set[str] = set()
    for line in text.splitlines():
        match = DECL_RE.match(line)
        if match and match.group("name"):
            names.add(str(match.group("name")))
    return names


def source_statement_context(
    project_root: Path,
    record: SelectedRecord,
    *,
    include_imported_label_api: bool = True,
) -> tuple[list[str], list[str]]:
    context_parts, context_closes = render_ordered_context_and_predecessors(project_root, record)
    expanded: list[str] = []
    seen_declaration_names = {name for part in context_parts for name in _declaration_names_in_text(part)}
    seen_context_bodies: set[str] = set()
    skip_next_body: str | None = None
    for index, part in enumerate(context_parts):
        if skip_next_body is not None and part.strip() == skip_next_body:
            skip_next_body = None
            continue
        header = part.splitlines()[0] if part.splitlines() else part
        if match := CONTEXT_NOTATION_HEADER_RE.match(header):
            next_body = context_parts[index + 1].strip() if index + 1 < len(context_parts) else ""
            if next_body and any(next_body in existing for existing in expanded):
                skip_next_body = next_body
                continue
            for block in _notation_support_blocks(project_root, match.group("path"), int(match.group("start")), record.line_range[0]):
                block_names = _declaration_names_in_text(block)
                if block_names and block_names <= seen_declaration_names:
                    continue
                expanded.append(block)
                seen_declaration_names.update(block_names)
        body = part.strip()
        if body in seen_context_bodies:
            continue
        expanded.append(part)
        if body:
            seen_context_bodies.add(body)
    for block in _prior_named_declaration_blocks(project_root, record):
        block_names = _declaration_names_in_text(block)
        if block_names and block_names <= seen_declaration_names:
            continue
        body = block.strip()
        if body in seen_context_bodies:
            continue
        expanded.append(block)
        seen_declaration_names.update(block_names)
        seen_context_bodies.add(body)
    if include_imported_label_api:
        for block in _imported_label_declaration_blocks(project_root, record):
            block_names = _declaration_names_in_text(block)
            if block_names and block_names <= seen_declaration_names:
                continue
            body = block.strip()
            if body in seen_context_bodies:
                continue
            expanded.append(block)
            seen_declaration_names.update(block_names)
            seen_context_bodies.add(body)
    return expanded, context_closes


def lean_environment_context(project_root: Path) -> dict[str, Any]:
    """Small, stable Lean/mathlib version context for source-statement prompts.

    The model often has stale Lean/mathlib priors. This is intentionally concise:
    it gives the current toolchain and common migration pitfalls observed in live
    source-statement failures without leaking the withheld target statement.
    """

    toolchain_path = project_root / "lean-toolchain"
    toolchain = toolchain_path.read_text(encoding="utf-8").strip() if toolchain_path.exists() else "unknown"
    return {
        "toolchain": toolchain,
        "imports": ["Mathlib"],
        "current_version_guidance": [
            "Generated code is checked with the repository lean-toolchain and current Mathlib, not Lean 3 or an older Lean 4 snapshot.",
            "Prefer Lean 4 syntax: `fun x => ...`, `by` tactic blocks, namespaces/dot notation as shown in the prompt, and current Mathlib names from displayed context.",
            "Do not invent old/deprecated identifiers such as guessed `*_apply`, `det_swap_rows`, `CommAlgebra`, or `LaurentPolynomial.X` unless they are explicitly present in context; use displayed local APIs or prove by unfolding/simping.",
            "For power-series coefficients, follow the local examples' argument order such as `coeff n (X : R⟦X⟧)`, not `coeff (X : R⟦X⟧) n`.",
            "For Laurent polynomial samples, prefer displayed current APIs such as `LaurentPolynomial.T n` and local notation `K[T;T⁻¹]`; do not use bare polynomial `X` for Laurent polynomials.",
            "Do not make typeclass objects (`CommRing α`, `Algebra R A`, etc.) components of an `∧`; those are types/classes, not propositions. Put them as assumptions/instances or use theorem statements about terms instead.",
            "If the source theorem is a narrow identity, formalize that identity directly rather than a broad bundled theorem whose components will not match the grader's withheld statement.",
        ],
        "available_reference_corpus": [
            "Current-version mathlib source can be searched locally at /tmp/mathlib4-v4.28.0-src when preparing/evaluating prompts.",
            "Use nearby repository Lean prefix/local examples first; use mathlib source snippets only as API/style evidence, not as a source for the withheld target statement.",
        ],
    }


def local_lean_style(project_root: Path, record: SelectedRecord) -> dict[str, Any]:
    notation_contracts: list[dict[str, str]] = []
    examples: list[str] = []
    seen_examples: set[str] = set()

    for span in record.file_context:
        if str(span.get("kind", "")) != "notation":
            continue
        path = project_root / str(span["path"])
        start, _ = [int(value) for value in span["line_range"]]
        notation_line = read_line_range(path, (start, start)).strip()
        if match := SCOPED_NOTATION_RE.search(notation_line):
            notation_contracts.append(
                {
                    "notation": _notation_surface(match.group("lhs").strip()),
                    "raw_notation": match.group("lhs").strip(),
                    "expands_to": match.group("rhs").strip(),
                    "source_line": f"{span['path']}:{start}",
                }
            )
        window = _read_context_window(path, start, before_line=record.line_range[0])
        if window and window not in seen_examples:
            examples.append(window)
            seen_examples.add(window)

    for block in _prior_example_blocks(project_root, record):
        if block not in seen_examples:
            examples.append(block)
            seen_examples.add(block)

    guidance = [
        "Match the local Lean style shown in local_lean_style.examples when it applies; prefer exact APIs and argument order already used in this file.",
        "Use only identifiers that appear in the Lean prefix context/local examples or are standard Mathlib identifiers; do not cite or invent raw helper names from guessed notation expansions.",
        "If the local examples use a domain-specific API such as `Ring.choose`, `updateCol`, or a local theorem name, keep that exact API family instead of falling back to a more familiar but different API such as `Nat.choose` or `Matrix.updateColumn`.",
    ]
    for contract in notation_contracts:
        guidance.append(
            f"The scoped notation {contract['notation']} expands to {contract['expands_to']}; use the exact surface syntax and keep the matrix argument after the bracketed index sets."
        )
        guidance.append(
            "If a helper theorem for this notation is not displayed in the prompt, do not name it directly; use an explicit Mathlib form or prove by unfolding/simping displayed definitions."
        )

    return {
        "guidance": guidance,
        "notation_contracts": notation_contracts,
        "examples": examples[:5],
    }


def domain_statement_shape_guidance(
    record: SelectedRecord,
    *,
    snippets: list[dict[str, Any]],
    context_parts: list[str],
    target_focus: dict[str, Any],
    context_mode: str = "target-comment",
) -> list[dict[str, Any]]:
    if context_mode not in CONTEXT_MODES:
        raise ValueError(f"unknown context mode: {context_mode}")
    source_text = "\n".join(str(snippet.get("snippet", "")) for snippet in snippets).lower()
    visible_labels = _source_span_labels(record)
    if context_mode != "source-only":
        visible_labels += _record_comment_labels(record)
    labels = " ".join(visible_labels).lower()
    target_comment = target_focus.get("target_declaration_source_comment") or {}
    target_comment_text = str(target_comment.get("text", "")).lower()
    imports = " ".join(record.imports)
    prefix = "\n".join(context_parts)
    combined = f"{source_text}\n{labels}\n{target_comment_text}\n{imports}\n{record.lean_path}"
    hidden_target_names = "" if context_mode == "source-only" else " ".join(record.declaration_names).lower()

    guidance: list[dict[str, Any]] = []
    fps_limit_signal = (
        "AlgebraicCombinatorics.FPS.Limits" in imports
        or "Details/Limits.lean" in record.lean_path
        or "CoeffStabilizesTo" in prefix
    )
    summability_signal = any(term in combined for term in ["summable", "sum-lim", "partial sum", "partial sums"])
    limit_signal = any(term in combined for term in ["limit", "lim.", "lim-"])
    if fps_limit_signal and summability_signal and limit_signal:
        limit_preferred = [
            "Use the repository's coefficientwise limit API when it is displayed or imported: `CoeffStabilizesTo`, `IsSummable`, and `tsum'`.",
            "Phrase finite partial sums with `Finset.range`; this file uses partial sums indexed by an upper natural bound.",
        ]
        if context_mode != "source-only":
            limit_preferred.append(
                "For a theorem/comment named like `isSummable_of_coeffStabilizesTo_partial_sum'`, prefer the narrow conclusion `IsSummable f`; for a theorem/comment named like `tsum'_eq...`, prefer only the `tsum'` equality."
            )
        limit_avoid = [
            "Do not translate this FPS limit prose into Mathlib's topological `HasSum`, `Summable`, or `∑'` API unless that exact API appears in the local context.",
            "Do not add topological assumptions such as `TopologicalSpace K⟦X⟧` just because the prose says limit.",
            "Do not bundle `IsSummable f` and `tsum' f ... = L` into a conjunction unless the source focus asks for the combined theorem.",
        ]
        if context_mode != "source-only" and "family is summable" in target_comment_text and "limit equals" not in target_comment_text:
            limit_preferred.append(
                "For this source focus, the statement shape should conclude only `IsSummable f` from the partial-sum stabilization hypothesis."
            )
            limit_avoid.append(
                "Do not include a `tsum'` equality, an `And.intro`, or any `∧` in this theorem when the source-facing target comment only asks that the family is summable."
            )
        guidance.append(
            {
                "domain": "formal power series limits",
                "trigger": "source/import context discusses summable FPS families, partial sums, and limits",
                "preferred_statement_family": limit_preferred,
                "avoid_statement_family": limit_avoid,
            }
        )

    fps_indeterminate_signal = (
        "FPSDefinition.lean" in record.lean_path
        or "def.fps.x" in labels
        or "indeterminate" in combined
    ) and ("x" in combined or "coeff" in combined or "coefficient" in combined)
    if fps_indeterminate_signal:
        guidance.append(
            {
                "domain": "formal power series indeterminate",
                "trigger": "source context describes the FPS indeterminate `X` and its coefficients",
                "preferred_statement_family": [
                    "Use the current Mathlib/PowerSeries coefficient API for `X`, especially displayed or standard facts such as `coeff_X` and `coeff_one_X`.",
                    "For coefficient identities about `X`, prove by rewriting/simping with the coefficient API; do not use `rfl` unless Lean has shown the equality is definitional.",
                ],
                "avoid_statement_family": [
                    "Do not unfold `X` into raw `MvPowerSeries` internals unless local examples already do that.",
                    "Do not assume `coeff n X = if n = 1 then 1 else 0` is definitional.",
                ],
            }
        )
    x_power_shift_signal = any(term in combined for term in ["x^k", "x ^ k", "x^{k}", "x ^{k}"])
    if fps_indeterminate_signal and x_power_shift_signal:
        guidance.append(
            {
                "domain": "formal power series multiplication by powers of X",
                "trigger": "source or target comment describes shifting coefficients by multiplying with `X^k`",
                "preferred_statement_family": [
                    "Respect the side of multiplication in the source focus: `f * X ^ k` should use/right-match `coeff_mul_X_pow`; `X ^ k * f` should use/right-match `coeff_X_pow_mul`.",
                    "If the target source comment says `f * X^k shifts f`, do not answer only the left-multiplication theorem `X^k * f` or the special `X * f` equality form.",
                    "For shifted-coefficient targets, prefer the displayed coefficient theorem shape over an equality to `PowerSeries.mk` unless the source focus explicitly asks for a whole-series equality.",
                ],
                "avoid_statement_family": [
                    "Do not use a nearby predecessor with the opposite multiplication order as the generated statement.",
                    "Do not collapse the generalized `X^k` source into the special `X` case unless the source focus says `k = 1`.",
                ],
            }
        )
    elif fps_indeterminate_signal and "lem.fps.xa" in labels:
        guidance.append(
            {
                "domain": "formal power series multiplication by X",
                "trigger": "source label `lem.fps.xa` describes multiplying an FPS by the indeterminate `X`",
                "preferred_statement_family": [
                    "For the special `x a = (0, a_0, a_1, ...)` source sentence, prefer the left-multiplication statement `X * f = PowerSeries.mk ...` or the displayed coefficient form for `X * f`.",
                    "Use displayed local facts such as `coeff_X_mul` when they appear in the prefix/local examples.",
                ],
                "avoid_statement_family": [
                    "Do not upgrade this special `X * f` source sentence into the later generalized `f * X ^ k` theorem unless the source explicitly mentions a power `k`.",
                ],
            }
        )

    substitution_signal = "Substitution.lean" in record.lean_path or "prop.fps.subs.rules" in labels
    if substitution_signal:
        finite_coeff_signal = any(
            term in combined
            for term in [
                "fps_comp_coeff_finite",
                "finite coefficient",
                "finite composition",
                "finsum",
                "support subset",
                "alternative coefficient formula",
                "actually finite",
                "for any fixed n",
                "d > n",
            ]
        )
        preferred_substitution = [
            "For the rule `g ∘ X = g`, state `PowerSeries.subst X g = g` and use the local `HasSubst.X'`/`coeff_subst'` style when needed.",
            "Keep the argument order from displayed local APIs: `PowerSeries.subst inner outer`, so `PowerSeries.subst X g` means substitute `X` into `g`.",
            "If proving by coefficients, the local proof pattern is `ext n`; rewrite with `coeff_subst'`; then use `coeff_X_pow` and `finsum_eq_single`.",
            "After `rw [coeff_subst' ha g n]`, simplify scalar actions with `simp only [coeff_X_pow, smul_eq_mul]` before applying `finsum_eq_single`; do not apply a multiplication-valued `finsum_eq_single` directly to a scalar-action goal.",
        ]
        avoid_substitution = [
            "Do not use the finite-composition helper with a separately inferred `constantCoeff X = 0` when a direct `HasSubst.X'` proof is available.",
            "Do not swap the rule into `PowerSeries.subst g X = g`; that is a different local lemma.",
        ]
        if finite_coeff_signal:
            preferred_substitution.extend(
                [
                    "For finite coefficient formulas for substitution, derive the infinite coefficient formula from `fps_comp_coeff`, then restrict the finite sum with `finsum_eq_sum_of_support_subset`.",
                    "Use Lean's standard support-subset proof shape: `apply finsum_eq_sum_of_support_subset`; then `intro d hd`; then prove the term is unsupported outside `Finset.range (n + 1)`.",
                    "The support proof usually shows terms outside `Finset.range (n + 1)` vanish: from `d ∉ Finset.range (n + 1)`, derive `n < d`, use `fps_subs_wd_firstCoeffs`, and finish the coefficient term with `mul_zero`.",
                ]
            )
            avoid_substitution.append(
                "Do not use guessed helpers such as `finsum_eq_finset_sum` or wrong-arity `finsum_eq_sum`."
            )
            avoid_substitution.append(
                "Do not write pseudo-syntax such as `∀ d in ...`, `intro d in`, or binder forms copied from mathematical prose; use ordinary Lean binders and tactics."
            )
        guidance.append(
            {
                "domain": "formal power series substitution",
                "trigger": "source context is a substitution rule for formal power series",
                "preferred_statement_family": preferred_substitution,
                "avoid_statement_family": avoid_substitution,
            }
        )

    negative_binomial_signal = (
        "DividingFPS.lean" in record.lean_path
        or "newtonbinomial" in combined
        or "oneplusx_pow_neg" in combined
        or "ring.choose (-(n" in combined
    )
    if negative_binomial_signal:
        guidance.append(
            {
                "domain": "negative binomial formal power series",
                "trigger": "source context describes inverse powers of `1 + X` and negative binomial coefficients",
                "preferred_statement_family": [
                    "For the negative-binomial inverse-power theorem, use the exact local binder/typeclass shape `{F : Type*} [Field F] [BinomialRing F] (n : ℕ)`.",
                    "State the right hand side as `PowerSeries.mk fun k => (Ring.choose (-(n : ℤ)) k : F)`; keep the negative upper argument in `ℤ` and cast the coefficient to `F`.",
                    "Prefer the displayed local helper `fps_onePlusX_pow_neg' n` when it appears in context; if Lean needs explicit type arguments, write them by name, e.g. `fps_onePlusX_pow_neg' (F := F) n`.",
                ],
                "avoid_statement_family": [
                    "Do not change the upper argument to `-(n : F)` or leave `BinomialRing`/coefficient types to metavariable inference.",
                    "Do not replace the local `Ring.choose` family with `Nat.choose` or an ad hoc binomial coefficient definition.",
                    "Do not apply the helper as `fps_onePlusX_pow_neg' F n`; the first explicit positional argument is the natural exponent, not the type.",
                ],
            }
        )

    multivariate_signal = "Multivariate.lean" in record.lean_path or "mulvar" in labels or "embedunivinbiv" in combined
    if multivariate_signal:
        guidance.append(
            {
                "domain": "multivariate FPS coefficient projection",
                "trigger": "source context compares coefficients in front of `y^k` using `embedUnivInBiv`",
                "preferred_statement_family": [
                    "For equality of embedded bivariate series, prove sequence equality by `funext k`; then `ext n`; then apply `congrArg` at `Finsupp.single 0 n + Finsupp.single 1 k`.",
                    "Use the displayed lemma `coeff_embedUnivInBiv` explicitly on both sides of the congruence before finishing; do not rely on a single `simpa` to discover the coefficient projection.",
                ],
                "avoid_statement_family": [
                    "Do not call `PowerSeries.ext` when the current goal is already a coefficient equality.",
                    "Do not leave the goal as an equality of raw `embedUnivInBiv` evaluations; rewrite it with `coeff_embedUnivInBiv`.",
                ],
            }
        )

    infprod_substitution_signal = (
        "InfiniteProducts2.lean" in record.lean_path
        and ("infprod" in labels or "multipliable" in combined or "prod_f" in combined)
    )
    if infprod_substitution_signal:
        guidance.append(
            {
                "domain": "formal power series infinite product substitution",
                "trigger": "source focus describes substitution through an infinite product via finite coefficient approximators",
                "preferred_statement_family": [
                    "Follow the target source comment's approximator API: hypotheses should quantify finite sets `M`/`J` and coefficients of finite products, plus a `prod_f` and `hprod` if the comment mentions them.",
                    "If the source comment says `hprod` works for any approximator `M`, state `hprod` as `∀ n M, approximator M n → coeff n prod_f = coeff n (∏ i ∈ M, f i)`, not as existence of some finite product.",
                    "Use displayed local helpers such as `comp_prod_finite`, `xnEquiv_comp`, `comp_prod_approx_determines`, and `comp_prod_multipliable`.",
                    "State the result as `∀ n, ∃ M, coeff n (prod_f.subst g) = coeff n (∏ i ∈ M, (f i).subst g)` when the source comment says the infinite product is represented by `prod_f`; keep approximator facts inside the proof, not bundled in the conclusion.",
                ],
                "avoid_statement_family": [
                    "Do not switch to Mathlib/topological `Multipliable`, `∏'`, `map_tprod`, or continuity APIs unless those exact assumptions are in the source focus and displayed local context.",
                    "Do not add `TopologicalSpace K⟦X⟧` assumptions to satisfy an invented topological theorem.",
                ],
            }
        )

    partition_transpose_signal = (
        "Partitions/Basics.lean" in record.lean_path
        or "prop.pars.pkn=dual" in labels
        or ("transpose" in combined and "largest part" in combined and "number of parts" in combined)
    )
    if partition_transpose_signal:
        partition_zero_signal = (
            "partition 0" in combined
            or "partition of 0" in combined
            or "partitions of 0" in combined
            or "empty partition" in combined
            or "has no parts" in combined
            or "parts_eq_zero" in hidden_target_names
            or "parts_eq_zero" in prefix
        )
        preferred_partition = [
            "Use the displayed local API for partitions: `numParts p`, `largestPart p`, `transpose`, `transpose_transpose`, `transpose_length_eq_largestPart`, and `transpose_largestPart_eq_length` when present.",
            "Treat `numParts` and `largestPart` as functions unless local context shows field notation.",
            "For cardinalities of filtered `Finset.univ`, prefer a current Mathlib bijection/image/cardinality API that actually exists in this Lean version; avoid guessed names.",
        ]
        avoid_partition = [
            "Do not call non-existent helpers such as `Finset.card_congr`.",
            "Do not use `.numParts` or `.largestPart` field notation when Lean reports that the partition type is not inferred.",
        ]
        if partition_zero_signal:
            preferred_partition.extend(
                [
                    "For `(p : Partition 0)`, prefer the direct statement `p.parts = 0` and prove it with the standard/imported fact `partition_zero_parts p`.",
                    "If the source-facing target comment says the partition of 0 has no parts, do not instead prove uniqueness as an equality between partition objects.",
                    "Only use local wrappers such as `parts_card_zero` or `eq_iff_parts_eq` if those exact declarations are displayed in the prompt prefix or examples.",
                ]
            )
            avoid_partition.append(
                "Do not invent partition fields or methods such as `.entries` or `.sum_eq`; use the displayed `parts` API."
            )
            avoid_partition.append(
                "Do not cite later same-file wrappers such as `eq_iff_parts_eq` unless they appear in the prompt; they may be after the withheld target declaration."
            )
        guidance.append(
            {
                "domain": "partition transpose cardinality",
                "trigger": "source context uses partition transpose to swap number of parts and largest part",
                "preferred_statement_family": preferred_partition,
                "avoid_statement_family": avoid_partition,
            }
        )
    permutation_signal = "Permutations/Basics.lean" in record.lean_path or "def.perm.si" in labels
    if permutation_signal:
        permutation_power_signal = any(
            term in combined
            for term in [
                "α^(n+1)",
                "α ^ (n+1)",
                "α ^ (n + 1)",
                "perm_pow",
                "power",
                "iterate",
            ]
        )
        simple_transposition_is_swap_signal = (
            "is a swap" in combined
            or "are swaps" in combined
            or "2-cycles" in combined
            or "isswap" in hidden_target_names
        )
        preferred_permutation = [
            "Use the local `simpleTransposition` definition and `Equiv.swap_apply_of_ne_of_ne` proof shape when proving a fixed point.",
            "For the fixed-point theorem, prefer assumptions on values, e.g. `k.val ≠ i.val` and `k.val ≠ i.val + 1`, if the displayed local context uses `Fin` representatives.",
            "If the source says `k ≠ i, i+1`, make the generated statement match the local index representation rather than inventing new `Fin` literals.",
        ]
        avoid_permutation = [
            "Do not produce a theorem whose assumptions are stronger/different Fin-object inequalities if the source focus likely expects value inequalities.",
            "Do not rely on bare `simp [simpleTransposition, h1, h2]` when `Equiv.swap_apply_of_ne_of_ne` gives the exact proof obligation.",
        ]
        if permutation_power_signal:
            preferred_permutation.extend(
                [
                    "When the source focus is the group-power law for `α^(n+1)`, prefer the theorem statement `α ^ (n + 1) = α ^ n * α` over a pointwise statement about iterated functions.",
                    "For powers of permutations, use current `Equiv.Perm`/function coercion APIs such as `pow_succ`, `pow_succ'`, `Equiv.Perm.coe_mul`, `Equiv.Perm.mul_apply`, `Function.comp_apply`, and `Function.iterate_succ_apply'`.",
                    "When proving pointwise statements about `(α ^ (n + 1)) x`, rewrite multiplication/application through the permutation coercion API instead of applying a generic equivalence helper.",
                ]
            )
            avoid_permutation.append(
                "Do not formalize the power law as `Function.iterate`/`^[n]` unless the source focus explicitly asks for pointwise iteration."
            )
            avoid_permutation.append("Do not use nonexistent helpers such as `Equiv.mul_apply`.")
        if simple_transposition_is_swap_signal:
            preferred_permutation.extend(
                [
                    "If the source says the simple transposition is a swap, state `(simpleTransposition i).IsSwap`; this is not just an equality-to-transposition theorem.",
                    "For an `IsSwap` proof, use the constructor-style proof shape: provide the two swapped `Fin` points with `use`, prove they are distinct, then prove the permutation equals the swap.",
                    "Use a displayed local `IsSwap` theorem directly if one appears in context, or prove `IsSwap` from displayed `simpleTransposition`/swap facts.",
                ]
            )
            avoid_permutation.append(
                "Do not answer only `simpleTransposition i = transposition ...` when the requested statement shape is `Perm.IsSwap`."
            )
            avoid_permutation.append(
                "Do not invent unavailable helper names such as `Equiv.swap_isSwap`; use the `IsSwap` constructor/proof shape instead."
            )
        guidance.append(
            {
                "domain": "simple transposition statement shape",
                "trigger": "source focus describes the simple transposition `s_i` and the fixed-point case",
                "preferred_statement_family": preferred_permutation,
                "avoid_statement_family": avoid_permutation,
            }
        )
    return guidance


def build_prompt_context(project_root: Path, record: SelectedRecord, *, context_mode: str = "target-comment") -> dict[str, Any]:
    if context_mode not in CONTEXT_MODES:
        raise ValueError(f"unknown context mode: {context_mode}")
    context_parts, _ = source_statement_context(
        project_root,
        record,
        include_imported_label_api=context_mode != "source-only",
    )
    snippets = source_snippets(project_root, record)
    focus = source_focus(project_root, record, context_mode=context_mode)
    return {
        "source_statement_or_chunk": snippets,
        "tex_source_focus": tex_source_focus(snippets),
        "target_source_focus": focus,
        "context_mode": context_mode,
        "available_imports": record.imports,
        "lean_prefix_context": "\n".join(context_parts).strip(),
        "lean_environment": lean_environment_context(project_root),
        "local_lean_style": local_lean_style(project_root, record),
        "domain_statement_shape_guidance": domain_statement_shape_guidance(
            record,
            snippets=snippets,
            context_parts=context_parts,
            target_focus=focus,
            context_mode=context_mode,
        ),
        "mathlib_context": record.mathlib_context,
        "benchmark_policy": {
            "target_lean_statement_available_to_model": False,
            "target_declaration_name_available_to_model": False,
            "grading_uses_withheld_gold_statement": True,
        },
    }


def build_messages(project_root: Path, record: SelectedRecord, *, context_mode: str = "target-comment") -> list[dict[str, str]]:
    system = (
        "You are a Lean 4 autoformalization agent working in a current Mathlib-only project. "
        "You must formalize the provided TeX/math source chunk into one Lean theorem or lemma, "
        "including a proof, using only the Lean prefix context provided. The target Lean statement, "
        "target declaration name, and original proof are intentionally withheld. Avoid stale Lean 3/old Mathlib "
        "syntax and identifiers; follow the lean_environment/current_version_guidance and local Lean examples. "
        "Return exactly one JSON object."
    )
    schema = {
        "lean_declaration": "one complete Lean theorem or lemma, including proof/body; do not include imports or markdown",
        "declaration_name": "the local name you gave that theorem/lemma",
        "used_context": ["short list of source/context facts used"],
        "notes": ["brief caveats, if any"],
    }
    user = {
        "task": "Formalize the source chunk as one Lean theorem/lemma and prove it.",
        "required_json_schema": schema,
        "instructions": [
            "Do not use sorry, admit, aesop? placeholders, or comments standing in for proof.",
            "Do not include import statements; the generated file already imports Mathlib.",
            "Do not assume access to the withheld target Lean statement or name.",
            "For multi-part TeX chunks, formalize only the specified labeled part/source span. Do not conjoin all parts unless the record explicitly asks for the whole multi-part result.",
            "Do not cite or invent raw helper names that are not present in the Lean prefix context/local examples; prefer displayed local style and standard Mathlib APIs.",
            "Do not redeclare definitions, structures, abbrevs, notation helpers, or instances already present in the Lean prefix context; reference them directly.",
            "Do not introduce theorem-local `where` definitions or redefine concepts such as summability, limits, binomial coefficients, or matrix operations. If a needed definition is not in context, state a narrower theorem using the displayed APIs.",
            "Use current Lean 4/Mathlib syntax and API names; if your memory conflicts with displayed local context, trust the displayed context.",
            "State a single proposition-level theorem/lemma that is likely to match the specified source part; do not bundle typeclass instances or unrelated source parts into conjunctions.",
            "Every nonstandard helper theorem or local API used in the proof should appear explicitly in the Lean prefix context or local examples. If it is not displayed, do not use its name.",
            "If an existing theorem or lemma in the prefix context has binders, apply it to the needed variables rather than using the theorem constant bare.",
            "Prefer the narrowest theorem directly supported by the source sentence; avoid generalizing to a stronger forall/if statement unless that exact shape is in the source or prefix context.",
            "Prefer a short proof if the prefix context already contains the needed fact.",
        ],
        "context": build_prompt_context(project_root, record, context_mode=context_mode),
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)}]


def build_repair_messages(
    *,
    original_messages: list[dict[str, str]],
    failed_declaration: str,
    generated_only_lean_result: dict[str, Any],
    shape_diagnostic_warnings: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    shape_diagnostic_warnings = shape_diagnostic_warnings or []
    system = (
        "You are a Lean 4 repair agent. Repair exactly one generated theorem/lemma so it compiles "
        "in the displayed current Lean/mathlib project. The original target Lean statement and target "
        "declaration name are still withheld. Do not ask for or infer hidden grader text. Use only the "
        "source chunk, prefix context, imports, local examples, the failed generated declaration, and "
        "compiler errors or visible-context shape diagnostics. Return exactly one JSON object."
    )
    original_user_payload = json.loads(original_messages[1]["content"])
    schema = {
        "lean_declaration": "one complete corrected Lean theorem or lemma including proof/body",
        "declaration_name": "the local name of the corrected theorem/lemma",
        "used_context": ["short list of source/context/compiler facts used"],
        "notes": ["brief caveats, if any"],
    }
    repair_domain_guidance = repair_domain_guidance_from_failure(
        original_user_payload=original_user_payload,
        failed_declaration=failed_declaration,
        generated_only_lean_result=generated_only_lean_result,
    )
    user = {
        "task": "Repair the failed generated Lean declaration. Return one complete theorem or lemma including proof; no imports and no markdown.",
        "required_json_schema": schema,
        "repair_rules": [
            "Do not use sorry, admit, placeholders, or comments as proof.",
            "Do not return a conjunction or broad bundled theorem when the source focus is a narrow identity.",
            "If the previous declaration over-generalized, narrow it to the single source sentence most directly supported by the context.",
            "Use explicit type annotations for polymorphic terms when Lean could leave typeclass metavariables stuck.",
            "For PowerSeries coefficients use argument order `coeff n f`.",
            "For Laurent polynomials use `LaurentPolynomial.T n`, not bare `X` or bare `T` unless the prefix context defines it.",
            "Do not redeclare context definitions; reference them directly.",
            "Do not add theorem-local `where` definitions or redefine project concepts; repair using the displayed APIs instead.",
            "Do not introduce helper theorem names that were not displayed in the original context or compiler output.",
            "If shape diagnostics are provided, rewrite the statement/proof to address those visible-context warnings without using or guessing hidden grader text.",
        ],
        "original_prompt_user_payload": original_user_payload,
        "failed_generated_declaration": failed_declaration,
        "generated_only_lean_exit_code": generated_only_lean_result.get("exit_code"),
        "generated_only_lean_output": generated_only_lean_result.get("output", ""),
    }
    if repair_domain_guidance:
        user["repair_domain_guidance"] = repair_domain_guidance
    if shape_diagnostic_warnings:
        user["shape_diagnostic_warnings"] = shape_diagnostic_warnings
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)}]


def repair_domain_guidance_from_failure(
    *,
    original_user_payload: dict[str, Any],
    failed_declaration: str,
    generated_only_lean_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return visible compiler-context repair hints without using hidden gold."""

    compiler_output = str(generated_only_lean_result.get("output") or "")
    context_text = json.dumps(original_user_payload.get("context") or {}, ensure_ascii=False)
    combined = "\n".join([context_text, failed_declaration, compiler_output])
    combined_lower = combined.lower()
    guidance: list[dict[str, Any]] = []

    if "fps_oneplusx_pow_neg'" in combined_lower or "hpows (powerseries" in combined_lower:
        preferred = [
            "If using the displayed helper `fps_onePlusX_pow_neg'`, apply it as `fps_onePlusX_pow_neg' n` or with named implicit type arguments such as `fps_onePlusX_pow_neg' (F := F) n`.",
            "For the inverse-power negative-binomial formula, keep the exponent binder natural: `(n : ℕ)` and conclusion `((1 + PowerSeries.X : PowerSeries F)⁻¹) ^ n = PowerSeries.mk fun k => (Ring.choose (-(n : ℤ)) k : F)`.",
        ]
        avoid = [
            "Do not call `fps_onePlusX_pow_neg' F n`; the type parameter is implicit and the first explicit positional argument is the natural exponent.",
            "Do not repair by using integer powers such as `(1 + PowerSeries.X : PowerSeries F) ^ (n : ℤ)` when the compiler reports no `HPow (PowerSeries F) ℤ ...` instance.",
        ]
        guidance.append(
            {
                "domain": "negative binomial repair",
                "trigger": "generated declaration or compiler output mentions the local `fps_onePlusX_pow_neg'` helper or integer-power instance failure",
                "preferred_repair_shape": preferred,
                "avoid_repair_shape": avoid,
            }
        )

    if "finsum_eq_sum_of_support_subset" in failed_declaration and "support" in compiler_output.lower():
        guidance.append(
            {
                "domain": "finite finsum support repair",
                "trigger": "generated proof misuses `finsum_eq_sum_of_support_subset` support-membership hypothesis",
                "preferred_repair_shape": [
                    "After `apply finsum_eq_sum_of_support_subset`, the proof obligation is a support-subset goal: `intro d hd` gives support membership, and the goal is membership in the finite set.",
                    "For a range `(Finset.range (n + 1))`, prove membership by contradiction: simplify membership in the range, assume the negation, derive `n < d`, use the displayed vanishing helper such as `fps_subs_wd_firstCoeffs g hg d n`, rewrite `Function.mem_support` at `hd`, and close from the resulting contradiction.",
                    "Use `rw [hz, mul_zero] at hd` for a product term that vanishes because the coefficient factor is zero.",
                ],
                "avoid_repair_shape": [
                    "Do not treat `hd` as a proof of `d ∉ Finset.range (n + 1)` or as a proof of `n < d`; it is support membership.",
                    "Do not try to prove vanishing directly as the final goal after `intro d hd`; first prove that every supported index lies in the finite range.",
                ],
            }
        )

    return guidance


def build_payload(*, model: str, messages: list[dict[str, str]], max_tokens: int, temperature: float, reasoning_effort: str | None) -> dict[str, Any]:
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


def extract_generated_name(declaration: str, declared_name: str | None) -> str | None:
    if declared_name:
        return declared_name.strip().strip("`")
    match = GENERATED_DECL_RE.search(declaration)
    if match:
        return match.group("name")
    return None


def declaration_binder_names(declaration_head: str, *, include_implicit: bool) -> list[str]:
    """Extract simple binder variable names from a theorem/lemma head."""
    names: list[str] = []
    declaration_match = re.search(r"\b(?:theorem|lemma)\b", declaration_head)
    signature = declaration_head[declaration_match.start() :] if declaration_match else declaration_head
    head_match = re.match(r"\s*(?:theorem|lemma)\s+[^\s:\{\(\[]+", signature)
    if head_match:
        binder_source = signature[head_match.end() :]
        depth = 0
        stop = len(binder_source)
        for index, char in enumerate(binder_source):
            if char in "({[":
                depth += 1
            elif char in ")}]" and depth > 0:
                depth -= 1
            elif char == ":" and depth == 0:
                stop = index
                break
        signature = binder_source[:stop]
    index = 0
    while index < len(signature):
        opener = signature[index]
        if opener not in "({":
            index += 1
            continue
        closer = ")" if opener == "(" else "}"
        depth = 1
        end = index + 1
        while end < len(signature) and depth:
            if signature[end] == opener:
                depth += 1
            elif signature[end] == closer:
                depth -= 1
            end += 1
        if depth:
            break
        group = signature[index + 1 : end - 1]
        index = end
        if opener == "{" and not include_implicit:
            continue
        colon_index: int | None = None
        nested = 0
        for group_index, char in enumerate(group):
            if char in "({[":
                nested += 1
            elif char in ")}]" and nested > 0:
                nested -= 1
            elif char == ":" and nested == 0:
                colon_index = group_index
                break
        if colon_index is None:
            continue
        binder_text = group[:colon_index].strip()
        for name in binder_text.split():
            if name and re.match(r"^[^\W\d][\w']*$", name, flags=re.UNICODE) and name != "_":
                if name not in names:
                    names.append(name)
    return names


def generated_application_candidates(generated_name: str, declaration_head: str) -> list[str]:
    explicit_args = declaration_binder_names(declaration_head, include_implicit=False)
    all_args = declaration_binder_names(declaration_head, include_implicit=True)
    candidates: list[str] = []
    for args in (explicit_args, all_args):
        app = " ".join([generated_name, *args]) if args else generated_name
        if app not in candidates:
            candidates.append(app)
    if generated_name not in candidates:
        candidates.append(generated_name)
    return candidates


def local_import_path(module: str) -> Path | None:
    if not module.startswith(LOCAL_MODULE_PREFIX):
        return None
    return Path(*module.split(".")).with_suffix(".lean")


def import_modules_from_lean(path: Path) -> list[str]:
    modules: list[str] = []
    if not path.exists():
        return modules
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("import "):
            continue
        modules.extend(part for part in stripped.removeprefix("import ").split() if part)
    return modules


def copy_local_import_closure(
    project_root: Path,
    output_root: Path,
    modules: list[str],
    *,
    skip_paths: set[Path],
) -> None:
    stack = list(reversed(modules))
    seen: set[str] = set()
    while stack:
        module = stack.pop()
        if module in seen:
            continue
        seen.add(module)
        rel_path = local_import_path(module)
        if rel_path is None or rel_path in skip_paths:
            continue
        source = project_root / rel_path
        if not source.exists():
            continue
        destination = output_root / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        for imported in reversed(import_modules_from_lean(source)):
            if imported not in seen:
                stack.append(imported)


def _declaration_head(declaration: str) -> str:
    marker = declaration.find(":=")
    return declaration[:marker].rstrip() if marker != -1 else declaration.rstrip()


def gold_check_declaration(project_root: Path, record: SelectedRecord, generated_name: str, generated_declaration: str) -> str:
    original = read_line_range(project_root / record.lean_path, record.line_range)
    marker = original.find(":=")
    if marker == -1:
        raise ValueError(f"target declaration lacks ':=': {record.record_id}")
    head = original[:marker].rstrip()
    head = re.sub(
        r"(\b(?:theorem|lemma)\s+)([^\s:\{\(\[]+)",
        r"\1__repoprover_source_statement_check",
        head,
        count=1,
    )
    candidates: list[str] = []
    for candidate_head in (_declaration_head(generated_declaration), head):
        for candidate in generated_application_candidates(generated_name, candidate_head):
            if candidate not in candidates:
                candidates.append(candidate)
    tactic_lines = ["  first", *(f"  | simpa using {candidate}" for candidate in candidates)]
    return head + " := by\n" + "\n".join(tactic_lines) + "\n"


def contains_forbidden_placeholder(declaration: str) -> bool:
    return bool(re.search(r"\b(sorry|admit|by\s*omega\s*\?)\b", declaration))


def materialize_candidate_project(
    *,
    project_root: Path,
    output_root: Path,
    record: SelectedRecord,
    lean_declaration: str,
    generated_name: str,
    lake_cache_from: Path | None,
    include_record_imports: bool = False,
    include_grader: bool = True,
    clean_output: bool = True,
) -> Path:
    if clean_output and output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    copy_project_config(project_root, output_root)
    if lake_cache_from is not None:
        copy_lake_cache(lake_cache_from, output_root)

    context_parts, context_closes = source_statement_context(project_root, record, include_imported_label_api=False)
    imports = record.imports if include_record_imports else ["Mathlib"]
    if "Mathlib" not in imports:
        imports = ["Mathlib", *imports]
    if include_record_imports:
        copy_local_import_closure(project_root, output_root, imports, skip_paths={Path(record.lean_path)})
    parts: list[str] = [*(f"import {module}" for module in imports), ""]
    parts.append("/-! Source-statement eval target. The target Lean statement was withheld from the model. -/")
    parts.append("")
    parts.extend(context_parts)
    if context_parts:
        parts.append("")
    parts.append("-- Model-generated declaration starts here.")
    parts.append(lean_declaration.strip())
    if include_grader:
        parts.append("")
        parts.append("-- Grader-only check: original target statement, proved from the model theorem.")
        parts.append(gold_check_declaration(project_root, record, generated_name, lean_declaration).rstrip())
    parts.append("")
    parts.extend(context_closes)

    target_path = output_root / record.lean_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return target_path


def run_lean(project_root: Path, target_path: Path, timeout: int) -> dict[str, Any]:
    local_imports = [module for module in import_modules_from_lean(target_path) if local_import_path(module) is not None]
    if local_imports:
        build_proc = subprocess.run(
            ["uv", "run", "lake", "build", *local_imports],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        if build_proc.returncode != 0:
            return {"exit_code": build_proc.returncode, "output": build_proc.stdout[-8000:]}
    rel = target_path.relative_to(project_root)
    proc = subprocess.run(
        ["uv", "run", "lake", "env", "lean", str(rel)],
        cwd=project_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return {"exit_code": proc.returncode, "output": proc.stdout[-8000:]}


def call_openrouter(payload: dict[str, Any], base_url: str, timeout: float) -> dict[str, Any]:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    client = OpenAI(base_url=base_url, api_key=key, timeout=timeout, max_retries=0)
    response = client.chat.completions.create(**payload)
    return response.model_dump(mode="json")


def parse_model_json(response: dict[str, Any]) -> dict[str, Any]:
    content = response["choices"][0]["message"].get("content") or ""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def response_message_content(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content") or "")


def write_text_artifact(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_generated_model_artifacts(record_dir: Path, *, assistant_content: str, model_json: dict[str, Any]) -> None:
    write_json(record_dir / "model-output.json", model_json)
    declaration = str(model_json.get("lean_declaration") or "")
    if declaration and not declaration.endswith("\n"):
        declaration += "\n"
    write_text_artifact(record_dir / "generated-lean-declaration.lean", declaration)


def write_repair_model_artifacts(record_dir: Path, attempt: int, *, assistant_content: str, model_json: dict[str, Any]) -> None:
    prefix = f"repair-attempt-{attempt:03d}"
    write_text_artifact(record_dir / f"{prefix}-assistant-content.txt", assistant_content)
    write_json(record_dir / f"{prefix}-model-output.json", model_json)
    declaration = str(model_json.get("lean_declaration") or "")
    if declaration and not declaration.endswith("\n"):
        declaration += "\n"
    write_text_artifact(record_dir / f"{prefix}-lean-declaration.lean", declaration)


def response_finish_reason(response: dict[str, Any]) -> str | None:
    choices = response.get("choices") or []
    if not choices:
        return None
    reason = choices[0].get("finish_reason")
    return str(reason) if reason is not None else None


def classify_lean_failure(output: str) -> str:
    if "unknown module prefix 'Mathlib'" in output or "No directory 'Mathlib' or file 'Mathlib.olean'" in output:
        return "lean_environment_missing_mathlib_cache"
    if "__repoprover_source_statement_check" in output:
        return "grader_gold_statement_not_proved"
    return "generated_lean_does_not_compile"


def classify_error(stage: str, exc: Exception, *, finish_reason: str | None = None) -> str:
    message = str(exc).lower()
    exc_name = type(exc).__name__.lower()
    if stage == "openrouter":
        if "timeout" in message or "timeout" in exc_name or "timed out" in message:
            return "openrouter_timeout"
        return "openrouter_error"
    if stage == "model_json":
        if finish_reason == "length":
            return "no_content_or_length"
        if "empty content" in message or "null content" in message:
            return "no_content_or_length"
        return "invalid_model_json"
    if stage == "model_contract":
        if "forbidden placeholder" in message:
            return "forbidden_placeholder"
        if "missing lean_declaration" in message:
            return "missing_declaration"
        return "model_contract_error"
    return "eval_error"


def actual_cost_from_row(row: dict[str, Any]) -> float:
    total = 0.0
    cost_summary = row.get("cost_summary", {})
    if cost_summary.get("actual_cost_usd") is not None:
        total += float(cost_summary["actual_cost_usd"])
    for repair in row.get("repair_results", []):
        repair_cost = repair.get("cost_summary", {})
        if repair_cost.get("actual_cost_usd") is not None:
            total += float(repair_cost["actual_cost_usd"])
    return total


def paid_call_count_from_row(row: dict[str, Any]) -> int:
    total = 1 if row.get("response_received") else 0
    total += sum(1 for repair in row.get("repair_results", []) if repair.get("response_received"))
    return total


def aggregate_failure_classes(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in results:
        failure_class = row.get("failure_class")
        if failure_class:
            counts[str(failure_class)] = counts.get(str(failure_class), 0) + 1
    return dict(sorted(counts.items()))


def prepare_record_run(args: argparse.Namespace, item: SourceEvalRecord) -> dict[str, Any]:
    record = item.selected
    record_dir = args.output / f"record-{item.index:03d}"
    messages = build_messages(args.project_root, record, context_mode=args.context_mode)
    payload = build_payload(
        model=args.model,
        messages=messages,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        reasoning_effort=args.reasoning_effort,
    )
    estimate = estimate_payload_cost(payload)
    estimated_max_cost = float(estimate.get("estimated_max_cost_usd") or 0.0)
    repair_attempts = max(0, int(getattr(args, "repair_attempts", 0) or 0))
    repair_payload = build_payload(
        model=args.model,
        messages=messages,
        max_tokens=args.repair_max_tokens,
        temperature=args.temperature,
        reasoning_effort=args.repair_reasoning_effort,
    )
    repair_estimate = estimate_payload_cost(repair_payload)
    repair_estimated_max_cost = float(repair_estimate.get("estimated_max_cost_usd") or 0.0)
    reserved_estimated_cost = estimated_max_cost + repair_attempts * repair_estimated_max_cost
    row: dict[str, Any] = {
        "index": item.index,
        "record_id": record.record_id,
        "lean_path": record.lean_path,
        "gold_declaration_names": record.declaration_names,
        "gold_line_range": list(record.line_range),
        "prompt_policy": (
            "target Lean statement/name withheld; target source chunk provided; "
            f"context_mode={args.context_mode}"
        ),
        "context_mode": args.context_mode,
        "budget_estimate": estimate,
        "repair_budget_estimate": repair_estimate,
        "repair_attempts_configured": repair_attempts,
        "reserved_estimated_max_cost_usd": reserved_estimated_cost,
    }
    write_json(record_dir / "openrouter-payload.json", payload)
    return {
        "item": item,
        "record": record,
        "record_dir": record_dir,
        "messages": messages,
        "payload": payload,
        "estimated_max_cost_usd": reserved_estimated_cost,
        "row": row,
    }


def lean_check_candidate(
    *,
    args: argparse.Namespace,
    record: SelectedRecord,
    record_dir: Path,
    project_subdir: str,
    declaration: str,
    generated_name: str,
    include_grader: bool,
) -> dict[str, Any]:
    output_root = args.output / "shared-project" if args.reuse_project else record_dir / project_subdir
    target_path = materialize_candidate_project(
        project_root=args.project_root,
        output_root=output_root,
        record=record,
        lean_declaration=declaration,
        generated_name=generated_name,
        lake_cache_from=args.lake_cache_from,
        include_record_imports=args.include_record_imports,
        include_grader=include_grader,
        clean_output=not args.reuse_project,
    )
    return run_lean(output_root, target_path, args.lean_timeout)


def run_repair_attempt(
    args: argparse.Namespace,
    *,
    record: SelectedRecord,
    record_dir: Path,
    original_messages: list[dict[str, str]],
    failed_declaration: str,
    generated_only_lean_result: dict[str, Any],
    attempt: int,
) -> dict[str, Any]:
    messages = build_repair_messages(
        original_messages=original_messages,
        failed_declaration=failed_declaration,
        generated_only_lean_result=generated_only_lean_result,
    )
    payload = build_payload(
        model=args.model,
        messages=messages,
        max_tokens=args.repair_max_tokens,
        temperature=args.temperature,
        reasoning_effort=args.repair_reasoning_effort,
    )
    prefix = f"repair-attempt-{attempt:03d}"
    write_json(record_dir / f"{prefix}-openrouter-payload.json", payload)
    row: dict[str, Any] = {
        "attempt": attempt,
        "budget_estimate": estimate_payload_cost(payload),
    }

    try:
        response = call_openrouter(payload, args.base_url, args.openrouter_timeout)
    except Exception as exc:  # noqa: BLE001
        row["api_request_attempted"] = True
        row["response_received"] = False
        row["success"] = False
        row["failure_class"] = classify_error("openrouter", exc)
        row["error"] = f"openrouter_{type(exc).__name__}: {exc}"
        return row

    row["api_request_attempted"] = True
    row["response_received"] = True
    write_json(record_dir / f"{prefix}-openrouter-response.json", response)
    cost_summary = summarize_openrouter_response_cost(response)
    write_json(record_dir / f"{prefix}-openrouter-cost-summary.json", cost_summary)
    row["cost_summary"] = cost_summary
    row["finish_reason"] = response_finish_reason(response)

    assistant_content = response_message_content(response)
    try:
        if not assistant_content.strip():
            raise ValueError("model returned empty content")
        model_json = parse_model_json(response)
        write_repair_model_artifacts(record_dir, attempt, assistant_content=assistant_content, model_json=model_json)
    except Exception as exc:  # noqa: BLE001
        row["success"] = False
        row["failure_class"] = classify_error("model_json", exc, finish_reason=row["finish_reason"])
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row

    try:
        declaration = str(model_json.get("lean_declaration") or "")
        generated_name = extract_generated_name(declaration, model_json.get("declaration_name"))
        row["model_json"] = model_json
        row["generated_name"] = generated_name
        row["forbidden_placeholder"] = contains_forbidden_placeholder(declaration)
        if not declaration.strip() or not generated_name:
            raise ValueError("missing lean_declaration or declaration_name")
        if row["forbidden_placeholder"]:
            raise ValueError("model output contains forbidden placeholder")
    except Exception as exc:  # noqa: BLE001
        row["success"] = False
        row["failure_class"] = classify_error("model_contract", exc)
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row

    row["success"] = True
    return row


def run_one_record(args: argparse.Namespace, prepared: dict[str, Any]) -> dict[str, Any]:
    record: SelectedRecord = prepared["record"]
    record_dir: Path = prepared["record_dir"]
    payload: dict[str, Any] = prepared["payload"]
    original_messages: list[dict[str, str]] = prepared["messages"]
    row = dict(prepared["row"])

    if args.preflight_only:
        row["paid_call_made"] = False
        row["status"] = "preflight_only"
        try:
            preflight_result = lean_check_candidate(
                args=args,
                record=record,
                record_dir=record_dir,
                project_subdir="preflight-project",
                declaration="theorem __repoprover_source_statement_preflight : True := by\n  trivial",
                generated_name="__repoprover_source_statement_preflight",
                include_grader=False,
            )
            write_json(record_dir / "preflight-lean.json", preflight_result)
            row["preflight_lean_check"] = preflight_result
            row["success"] = preflight_result["exit_code"] == 0
            if not row["success"]:
                row["failure_class"] = "verifier_preflight_failed"
        except Exception as exc:  # noqa: BLE001 - preflight should produce row-level failures.
            row["success"] = False
            row["failure_class"] = "verifier_preflight_error"
            row["error"] = f"{type(exc).__name__}: {exc}"
        return row

    if args.budget_only:
        row["paid_call_made"] = False
        row["status"] = "budget_only"
        return row

    try:
        response = call_openrouter(payload, args.base_url, args.openrouter_timeout)
    except Exception as exc:  # noqa: BLE001 - timeout/API failure should not abort the batch.
        row["paid_call_made"] = True
        row["api_request_attempted"] = True
        row["response_received"] = False
        row["success"] = False
        row["failure_class"] = classify_error("openrouter", exc)
        row["error"] = f"openrouter_{type(exc).__name__}: {exc}"
        return row

    row["api_request_attempted"] = True
    row["response_received"] = True
    write_json(record_dir / "openrouter-response.json", response)
    cost_summary = summarize_openrouter_response_cost(response)
    write_json(record_dir / "openrouter-cost-summary.json", cost_summary)
    row["cost_summary"] = cost_summary
    row["finish_reason"] = response_finish_reason(response)

    assistant_content = response_message_content(response)
    write_text_artifact(record_dir / "model-assistant-content.txt", assistant_content)

    try:
        if not assistant_content.strip():
            raise ValueError("model returned empty content")
        model_json = parse_model_json(response)
        write_generated_model_artifacts(record_dir, assistant_content=assistant_content, model_json=model_json)
    except Exception as exc:  # noqa: BLE001 - classify malformed provider content.
        row["success"] = False
        row["failure_class"] = classify_error("model_json", exc, finish_reason=row["finish_reason"])
        row["error"] = f"{type(exc).__name__}: {exc}"
        row["paid_call_made"] = True
        return row

    try:
        declaration = str(model_json.get("lean_declaration") or "")
        generated_name = extract_generated_name(declaration, model_json.get("declaration_name"))
        row["model_json"] = model_json
        row["generated_name"] = generated_name
        row["forbidden_placeholder"] = contains_forbidden_placeholder(declaration)
        if not declaration.strip() or not generated_name:
            raise ValueError("missing lean_declaration or declaration_name")
        if row["forbidden_placeholder"]:
            raise ValueError("model output contains forbidden placeholder")
    except Exception as exc:  # noqa: BLE001 - per-record contract failures should continue.
        row["success"] = False
        row["failure_class"] = classify_error("model_contract", exc)
        row["error"] = f"{type(exc).__name__}: {exc}"
        row["paid_call_made"] = True
        return row

    if args.generation_only:
        row["paid_call_made"] = True
        row["status"] = "generation_only"
        row["generation_success"] = True
        row["success"] = False
        return row

    row["repair_results"] = []
    row["repair_attempts_used"] = 0

    current_declaration = declaration
    current_generated_name = str(generated_name)
    for attempt in range(0, max(0, int(getattr(args, "repair_attempts", 0) or 0)) + 1):
        project_subdir = "project" if attempt == 0 else f"repair-attempt-{attempt:03d}-generated-only-project"
        try:
            generated_only_lean = lean_check_candidate(
                args=args,
                record=record,
                record_dir=record_dir,
                project_subdir=project_subdir,
                declaration=current_declaration,
                generated_name=current_generated_name,
                include_grader=False,
            )
            artifact_name = "generated-only-lean.json" if attempt == 0 else f"repair-attempt-{attempt:03d}-generated-only-lean.json"
            write_json(record_dir / artifact_name, generated_only_lean)
            if attempt == 0:
                row["generated_only_lean_check"] = generated_only_lean
            else:
                row["repair_results"][-1]["generated_only_lean_check"] = generated_only_lean
            if generated_only_lean["exit_code"] != 0:
                row["success"] = False
                row["failure_class"] = "generated_lean_does_not_compile"
                row["lean_check"] = generated_only_lean
                if attempt >= int(getattr(args, "repair_attempts", 0) or 0):
                    break
                repair_row = run_repair_attempt(
                    args,
                    record=record,
                    record_dir=record_dir,
                    original_messages=original_messages,
                    failed_declaration=current_declaration,
                    generated_only_lean_result=generated_only_lean,
                    attempt=attempt + 1,
                )
                row["repair_results"].append(repair_row)
                if not repair_row.get("success"):
                    row["success"] = False
                    row["failure_class"] = repair_row.get("failure_class")
                    row["error"] = repair_row.get("error")
                    break
                if not repair_row.get("model_json"):
                    break
                current_declaration = str(repair_row["model_json"].get("lean_declaration") or "")
                current_generated_name = str(repair_row.get("generated_name") or "")
                row["repair_attempts_used"] = attempt + 1
                continue

            graded_lean = lean_check_candidate(
                args=args,
                record=record,
                record_dir=record_dir,
                project_subdir="project" if attempt == 0 else f"repair-attempt-{attempt:03d}-graded-project",
                declaration=current_declaration,
                generated_name=current_generated_name,
                include_grader=True,
            )
            if attempt == 0:
                row["lean_check"] = graded_lean
            else:
                row["repair_results"][-1]["graded_lean_check"] = graded_lean
                row["lean_check"] = graded_lean
            row["success"] = graded_lean["exit_code"] == 0
            if row["success"]:
                row["failure_class"] = None
                row["generated_name"] = current_generated_name
                row["final_declaration_source"] = "initial" if attempt == 0 else f"repair-attempt-{attempt:03d}"
            else:
                row["failure_class"] = "grader_gold_statement_not_proved"
            break
        except Exception as exc:  # noqa: BLE001 - per-record eval should continue.
            row["success"] = False
            row["failure_class"] = "materialization_or_lean_error"
            row["error"] = f"{type(exc).__name__}: {exc}"
            break

    row["paid_call_made"] = True
    return row


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sorted_results(results_by_index: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    return [results_by_index[index] for index in sorted(results_by_index)]


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not hasattr(args, "context_mode"):
        args.context_mode = "target-comment"
    if args.context_mode not in CONTEXT_MODES:
        raise ValueError(f"unknown context mode: {args.context_mode}")
    rows = load_jsonl(args.records)
    records = select_source_statement_records(rows, args.limit, args.sample_mode)
    if not records:
        raise ValueError("no theorem/lemma source-statement records selected")
    if args.concurrency < 1:
        raise ValueError("--concurrency must be at least 1")
    if args.preflight_only and args.budget_only:
        raise ValueError("--preflight-only and --budget-only are mutually exclusive")
    if args.generation_only and (args.preflight_only or args.budget_only):
        raise ValueError("--generation-only cannot be combined with --preflight-only or --budget-only")
    if args.reuse_project and args.concurrency != 1:
        raise ValueError("--reuse-project requires --concurrency 1 because generated target files are overwritten in place")

    eval_dir = args.output / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    selected_rows = [item.selected.row for item in records]
    write_jsonl(eval_dir / "selected-records.jsonl", selected_rows)

    partial_jsonl = eval_dir / "partial-results.jsonl"
    if partial_jsonl.exists():
        partial_jsonl.unlink()
    prepared_records = [prepare_record_run(args, item) for item in records]
    if args.budget_only or args.preflight_only:
        results = [run_one_record(args, prepared) for prepared in prepared_records]
        for row in results:
            append_jsonl(partial_jsonl, row)
        write_json(eval_dir / "partial-results.json", {"results": results})
    else:
        results_by_index: dict[int, dict[str, Any]] = {}
        running: dict[concurrent.futures.Future[dict[str, Any]], dict[str, Any]] = {}
        next_record = 0
        reserved_cost = 0.0
        completed_actual_cost = 0.0

        def record_partial_result(future: concurrent.futures.Future[dict[str, Any]]) -> None:
            nonlocal reserved_cost, completed_actual_cost
            prepared = running.pop(future)
            reserved_cost -= float(prepared["estimated_max_cost_usd"])
            try:
                row = future.result()
            except Exception as exc:  # noqa: BLE001 - worker bugs still become row-level failures.
                item: SourceEvalRecord = prepared["item"]
                row = dict(prepared["row"])
                row["paid_call_made"] = False
                row["success"] = False
                row["failure_class"] = "worker_error"
                row["error"] = f"{type(exc).__name__}: {exc}"
                row["index"] = item.index
            completed_actual_cost += actual_cost_from_row(row)
            results_by_index[int(row["index"])] = row
            append_jsonl(partial_jsonl, row)
            write_json(eval_dir / "partial-results.json", {"results": sorted_results(results_by_index)})

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            while next_record < len(prepared_records) or running:
                launched = False
                while next_record < len(prepared_records) and len(running) < args.concurrency:
                    prepared = prepared_records[next_record]
                    estimated_cost = float(prepared["estimated_max_cost_usd"])
                    cost_cap = float(args.max_actual_cost_usd or 0.0)
                    if cost_cap and completed_actual_cost >= cost_cap:
                        if running:
                            break
                        row = dict(prepared["row"])
                        row["paid_call_made"] = False
                        row["success"] = False
                        row["failure_class"] = "skipped_cost_cap"
                        row["error"] = "global cost cap already reached; no request launched"
                        results_by_index[int(row["index"])] = row
                        append_jsonl(partial_jsonl, row)
                        write_json(eval_dir / "partial-results.json", {"results": sorted_results(results_by_index)})
                        next_record += 1
                        launched = True
                        continue
                    if cost_cap and completed_actual_cost + reserved_cost + estimated_cost > cost_cap:
                        if running:
                            break
                        row = dict(prepared["row"])
                        row["paid_call_made"] = False
                        row["success"] = False
                        row["failure_class"] = "skipped_cost_cap"
                        row["error"] = (
                            "estimated per-record max cost would exceed remaining global cost cap "
                            f"(${estimated_cost:.6f} > ${max(0.0, cost_cap - completed_actual_cost):.6f})"
                        )
                        results_by_index[int(row["index"])] = row
                        append_jsonl(partial_jsonl, row)
                        write_json(eval_dir / "partial-results.json", {"results": sorted_results(results_by_index)})
                        next_record += 1
                        launched = True
                        continue
                    future = executor.submit(run_one_record, args, prepared)
                    running[future] = prepared
                    reserved_cost += estimated_cost
                    next_record += 1
                    launched = True

                if not running:
                    if not launched and next_record < len(prepared_records):
                        continue
                    break

                done, _ = concurrent.futures.wait(
                    running,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                for future in done:
                    record_partial_result(future)

        results = sorted_results(results_by_index)

    total_actual_cost = 0.0
    paid_calls = 0
    for row in results:
        paid_calls += paid_call_count_from_row(row)
        total_actual_cost += actual_cost_from_row(row)

    attempted = [row for row in results if row.get("paid_call_made")]
    successes = [row for row in attempted if row.get("success")]
    preflight_rows = [row for row in results if row.get("status") == "preflight_only"]
    preflight_successes = [row for row in preflight_rows if row.get("success")]
    generation_rows = [row for row in results if row.get("status") == "generation_only"]
    generation_successes = [row for row in generation_rows if row.get("generation_success")]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_selected": len(records),
        "records_completed": len(results),
        "records_attempted": len(attempted),
        "successes": len(successes),
        "success_rate": (len(successes) / len(attempted)) if attempted else None,
        "preflight_successes": len(preflight_successes),
        "preflight_success_rate": (len(preflight_successes) / len(preflight_rows)) if preflight_rows else None,
        "generation_successes": len(generation_successes),
        "generation_success_rate": (len(generation_successes) / len(generation_rows)) if generation_rows else None,
        "paid_calls_made": paid_calls,
        "actual_cost_usd": total_actual_cost,
        "model": args.model,
        "max_tokens": args.max_tokens,
        "reasoning_effort": args.reasoning_effort,
        "concurrency": args.concurrency,
        "sample_mode": args.sample_mode,
        "max_actual_cost_usd": args.max_actual_cost_usd,
        "repair_attempts": args.repair_attempts,
        "repair_max_tokens": args.repair_max_tokens,
        "repair_reasoning_effort": args.repair_reasoning_effort,
        "context_mode": args.context_mode,
        "preflight_only": args.preflight_only,
        "generation_only": args.generation_only,
        "reuse_project": args.reuse_project,
        "failure_classes": aggregate_failure_classes(results),
        "results": results,
    }
    write_json(eval_dir / "source-statement-live-results.json", summary)
    render_markdown(eval_dir / "source-statement-live-results.md", summary)
    return summary


def render_markdown(path: Path, summary: dict[str, Any]) -> None:
    rate = summary["success_rate"]
    lines = [
        "# Source-statement live eval results",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Model: `{summary['model']}`",
        f"- Max tokens: `{summary['max_tokens']}`",
        f"- Reasoning effort: `{summary['reasoning_effort']}`",
        f"- Repair attempts: `{summary['repair_attempts']}`",
        f"- Repair max tokens: `{summary['repair_max_tokens']}`",
        f"- Repair reasoning effort: `{summary['repair_reasoning_effort']}`",
        f"- Context mode: `{summary['context_mode']}`",
        f"- Preflight only: `{summary['preflight_only']}`",
        f"- Generation only: `{summary['generation_only']}`",
        f"- Reuse project: `{summary['reuse_project']}`",
        f"- Concurrency: `{summary['concurrency']}`",
        f"- Sample mode: `{summary['sample_mode']}`",
        f"- Global cost cap: `${float(summary['max_actual_cost_usd'] or 0.0):.6f}`",
        f"- Records attempted: {summary['records_attempted']} / selected {summary['records_selected']}",
        f"- Successes: {summary['successes']}",
        f"- Success rate: {rate:.1%}" if rate is not None else "- Success rate: n/a",
        (
            f"- Preflight successes: {summary['preflight_successes']} / "
            f"{sum(1 for row in summary['results'] if row.get('status') == 'preflight_only')}"
        ),
        (
            f"- Generation successes: {summary['generation_successes']} / "
            f"{sum(1 for row in summary['results'] if row.get('status') == 'generation_only')}"
        ),
        f"- Actual reported cost: `${summary['actual_cost_usd']:.6f}`",
        f"- Failure classes: `{json.dumps(summary['failure_classes'], sort_keys=True)}`",
        "",
        "Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.",
        "",
        "| # | Result | Record | Generated name | Cost | Error / Lean output |",
        "|---:|---|---|---|---:|---|",
    ]
    for row in summary["results"]:
        if row.get("status") == "budget_only":
            result = "BUDGET"
        elif row.get("failure_class") == "skipped_cost_cap":
            result = "SKIP"
        else:
            result = "PASS" if row.get("success") else "FAIL"
        cost = row.get("cost_summary", {}).get("actual_cost_usd")
        cost_text = f"${float(cost):.6f}" if cost is not None else ""
        err = row.get("error") or row.get("lean_check", {}).get("output", "")
        err = " ".join(str(err).split())[:220]
        lines.append(
            f"| {row['index']} | {result} | `{row['record_id']}` | `{row.get('generated_name') or ''}` | {cost_text} | {err} |"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=REPO_ROOT / "docs/minimal-context-splits/oracle_source_statement.jsonl")
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--max-tokens", type=int, default=32768)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--repair-attempts", type=int, default=0, help="Generated-only compiler-feedback repair attempts.")
    parser.add_argument("--repair-max-tokens", type=int, default=None, help="Max tokens for each repair call. Defaults to --max-tokens.")
    parser.add_argument(
        "--repair-reasoning-effort",
        default=None,
        help="Reasoning effort for repair calls. Defaults to --reasoning-effort.",
    )
    parser.add_argument("--lake-cache-from", type=Path, default=None)
    parser.add_argument(
        "--include-record-imports",
        action="store_true",
        help="Copy and import local modules listed in each record instead of checking in a Mathlib-only project.",
    )
    parser.add_argument("--lean-timeout", type=int, default=90)
    parser.add_argument("--openrouter-timeout", type=float, default=240.0)
    parser.add_argument("--max-actual-cost-usd", type=float, default=2.0)
    parser.add_argument("--concurrency", type=int, default=4, help="Maximum records to run concurrently.")
    parser.add_argument(
        "--sample-mode",
        choices=["corpus-spread", "easy", "stratified-easy"],
        default="corpus-spread",
        help="Record selection mode. `stratified-easy` spreads over the easiest candidate pool.",
    )
    parser.add_argument("--budget-only", action="store_true")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Materialize and Lean-check selected records with a trivial generated theorem; make no paid calls.",
    )
    parser.add_argument(
        "--generation-only",
        action="store_true",
        help="Call the provider and persist model artifacts, but do not run Lean verification.",
    )
    parser.add_argument(
        "--reuse-project",
        action="store_true",
        help="Reuse one materialized Lean project under the output directory. Requires --concurrency 1.",
    )
    parser.add_argument(
        "--context-mode",
        choices=CONTEXT_MODES,
        default="target-comment",
        help=(
            "`target-comment` keeps source-facing target Lean doc comments and alignment comment labels in prompts. "
            "`source-only` removes target doc comments, target-derived comment labels, and hidden declaration-name "
            "guidance triggers for a more realistic TeX/source-context prompt."
        ),
    )
    args = parser.parse_args()
    if args.repair_max_tokens is None:
        args.repair_max_tokens = args.max_tokens
    if args.repair_reasoning_effort is None:
        args.repair_reasoning_effort = args.reasoning_effort
    return args


if __name__ == "__main__":
    summary = run(parse_args())
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))
