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
SCOPED_NOTATION_RE = re.compile(r"scoped\s+notation\s+(?P<lhs>.*?)\s*=>\s*(?P<rhs>.*)$")
PART_LABEL_RE = re.compile(r"\.([a-z])$")
CONTEXT_NOTATION_HEADER_RE = re.compile(r"^-- File context: (?P<path>.*):(?P<start>\d+)-(?P<end>\d+) \(notation\)$")


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


def _record_comment_labels(record: SelectedRecord) -> list[str]:
    return [str(label) for label in record.row.get("alignment", {}).get("comment_labels", [])]


def _source_span_labels(record: SelectedRecord) -> list[str]:
    labels: list[str] = []
    for span in record.source_spans:
        labels.extend(str(label) for label in span.get("labels", []))
    return labels


def source_focus(record: SelectedRecord) -> dict[str, Any]:
    source_labels = _source_span_labels(record)
    comment_labels = _record_comment_labels(record)
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
    return {
        "source_span_labels": source_labels,
        "record_comment_labels": comment_labels,
        "specific_source_labels": specific_labels,
        "specific_labeled_parts": specific_parts,
        "instruction": (
            "If the source snippet contains multiple labeled or numbered parts, formalize only the specific "
            "part/source span indicated by specific_source_labels or specific_labeled_parts. Do not conjoin "
            "all parts unless the record labels identify the whole multi-part result."
        ),
    }


def _read_context_window(path: Path, line: int, *, before: int = 10, after: int = 24) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = max(1, line - before)
    end = min(len(lines), line + after)
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


def _prior_example_blocks(project_root: Path, record: SelectedRecord, limit: int = 2) -> list[str]:
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
        keywords.append(".det")

    starts: list[int] = []
    for index, line in enumerate(lines[: target_start - 1]):
        if re.match(r"^\s*(?:example|theorem|lemma)\b", line):
            starts.append(index)
    candidates: list[tuple[tuple[int, int], str]] = []
    for offset, start_index in enumerate(starts):
        end_index = starts[offset + 1] if offset + 1 < len(starts) else target_start - 1
        block_start = _declaration_start(lines, start_index)
        block_lines = lines[block_start:end_index]
        if len(block_lines) > 45:
            continue
        block = "\n".join(block_lines).rstrip()
        score = sum(1 for keyword in keywords if keyword in block)
        if score == 0:
            continue
        candidates.append(((score, start_index), block))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [block for _, block in candidates[:limit]]


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
            if DECL_RE.match(lines[next_index]):
                end_index = _declaration_start(lines, next_index)
                break
        if before_line is not None:
            end_index = min(end_index, before_line - 1)
        block_lines = lines[start_index:end_index]
        while block_lines and not block_lines[-1].strip():
            block_lines.pop()
        while block_lines and block_lines[-1].lstrip().startswith(("/--", "/-!", "@[", "--")):
            block_lines.pop()
            while block_lines and not block_lines[-1].strip():
                block_lines.pop()
        block = "\n".join(block_lines).rstrip()
        end_index = start_index + len(block_lines)
        matches.append((start_index + 1, end_index, block))
    return matches[-1] if matches else None


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


def source_statement_context(project_root: Path, record: SelectedRecord) -> tuple[list[str], list[str]]:
    context_parts, context_closes = render_ordered_context_and_predecessors(project_root, record)
    expanded: list[str] = []
    for part in context_parts:
        if match := CONTEXT_NOTATION_HEADER_RE.match(part):
            expanded.extend(
                _notation_support_blocks(project_root, match.group("path"), int(match.group("start")), record.line_range[0])
            )
        expanded.append(part)
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
        window = _read_context_window(path, start)
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
        "examples": examples[:3],
    }


def build_prompt_context(project_root: Path, record: SelectedRecord) -> dict[str, Any]:
    context_parts, _ = source_statement_context(project_root, record)
    return {
        "source_statement_or_chunk": source_snippets(project_root, record),
        "target_source_focus": source_focus(record),
        "lean_prefix_context": "\n".join(context_parts).strip(),
        "lean_environment": lean_environment_context(project_root),
        "local_lean_style": local_lean_style(project_root, record),
        "mathlib_context": record.mathlib_context,
        "benchmark_policy": {
            "target_lean_statement_available_to_model": False,
            "target_declaration_name_available_to_model": False,
            "grading_uses_withheld_gold_statement": True,
        },
    }


def build_messages(project_root: Path, record: SelectedRecord) -> list[dict[str, str]]:
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
            "Use current Lean 4/Mathlib syntax and API names; if your memory conflicts with displayed local context, trust the displayed context.",
            "State a single proposition-level theorem/lemma that is likely to match the specified source part; do not bundle typeclass instances or unrelated source parts into conjunctions.",
            "Prefer a short proof if the prefix context already contains the needed fact.",
        ],
        "context": build_prompt_context(project_root, record),
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)}]


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


def gold_check_declaration(project_root: Path, record: SelectedRecord, generated_name: str) -> str:
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
    return head + f" := by\n  simpa using {generated_name}\n"


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
) -> Path:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)
    copy_project_config(project_root, output_root)
    if lake_cache_from is not None:
        copy_lake_cache(lake_cache_from, output_root)

    context_parts, context_closes = source_statement_context(project_root, record)
    imports = ["Mathlib"]
    parts: list[str] = [*(f"import {module}" for module in imports), ""]
    parts.append("/-! Source-statement eval target. The target Lean statement was withheld from the model. -/")
    parts.append("")
    parts.extend(context_parts)
    if context_parts:
        parts.append("")
    parts.append("-- Model-generated declaration starts here.")
    parts.append(lean_declaration.strip())
    parts.append("")
    parts.append("-- Grader-only check: original target statement, proved from the model theorem.")
    parts.append(gold_check_declaration(project_root, record, generated_name).rstrip())
    parts.append("")
    parts.extend(context_closes)

    target_path = output_root / record.lean_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return target_path


def run_lean(project_root: Path, target_path: Path, timeout: int) -> dict[str, Any]:
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


def response_finish_reason(response: dict[str, Any]) -> str | None:
    choices = response.get("choices") or []
    if not choices:
        return None
    reason = choices[0].get("finish_reason")
    return str(reason) if reason is not None else None


def classify_lean_failure(output: str) -> str:
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
    payload = build_payload(
        model=args.model,
        messages=build_messages(args.project_root, record),
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        reasoning_effort=args.reasoning_effort,
    )
    estimate = estimate_payload_cost(payload)
    row: dict[str, Any] = {
        "index": item.index,
        "record_id": record.record_id,
        "lean_path": record.lean_path,
        "gold_declaration_names": record.declaration_names,
        "gold_line_range": list(record.line_range),
        "prompt_policy": "target Lean statement/name withheld; target source chunk provided",
        "budget_estimate": estimate,
    }
    write_json(record_dir / "openrouter-payload.json", payload)
    return {
        "item": item,
        "record": record,
        "record_dir": record_dir,
        "payload": payload,
        "estimated_max_cost_usd": float(estimate.get("estimated_max_cost_usd") or 0.0),
        "row": row,
    }


def run_one_record(args: argparse.Namespace, prepared: dict[str, Any]) -> dict[str, Any]:
    record: SelectedRecord = prepared["record"]
    record_dir: Path = prepared["record_dir"]
    payload: dict[str, Any] = prepared["payload"]
    row = dict(prepared["row"])

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

    try:
        if not response_message_content(response).strip():
            raise ValueError("model returned empty content")
        model_json = parse_model_json(response)
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

    try:
        target_path = materialize_candidate_project(
            project_root=args.project_root,
            output_root=record_dir / "project",
            record=record,
            lean_declaration=declaration,
            generated_name=str(generated_name),
            lake_cache_from=args.lake_cache_from,
        )
        lean_result = run_lean(record_dir / "project", target_path, args.lean_timeout)
        row["lean_check"] = lean_result
        row["success"] = lean_result["exit_code"] == 0
        if not row["success"]:
            row["failure_class"] = classify_lean_failure(str(lean_result.get("output") or ""))
    except Exception as exc:  # noqa: BLE001 - per-record eval should continue.
        row["success"] = False
        row["failure_class"] = "materialization_or_lean_error"
        row["error"] = f"{type(exc).__name__}: {exc}"

    row["paid_call_made"] = True
    return row


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sorted_results(results_by_index: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    return [results_by_index[index] for index in sorted(results_by_index)]


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows = load_jsonl(args.records)
    records = select_source_statement_records(rows, args.limit, args.sample_mode)
    if not records:
        raise ValueError("no theorem/lemma source-statement records selected")
    if args.concurrency < 1:
        raise ValueError("--concurrency must be at least 1")

    eval_dir = args.output / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    selected_rows = [item.selected.row for item in records]
    write_jsonl(eval_dir / "selected-records.jsonl", selected_rows)

    partial_jsonl = eval_dir / "partial-results.jsonl"
    if partial_jsonl.exists():
        partial_jsonl.unlink()
    prepared_records = [prepare_record_run(args, item) for item in records]
    if args.budget_only:
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
            cost = row.get("cost_summary", {}).get("actual_cost_usd")
            if cost is not None:
                completed_actual_cost += float(cost)
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
        if row.get("response_received"):
            paid_calls += 1
        cost_summary = row.get("cost_summary", {})
        if cost_summary.get("actual_cost_usd") is not None:
            total_actual_cost += float(cost_summary["actual_cost_usd"])

    attempted = [row for row in results if row.get("paid_call_made")]
    successes = [row for row in attempted if row.get("success")]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_selected": len(records),
        "records_completed": len(results),
        "records_attempted": len(attempted),
        "successes": len(successes),
        "success_rate": (len(successes) / len(attempted)) if attempted else None,
        "paid_calls_made": paid_calls,
        "actual_cost_usd": total_actual_cost,
        "model": args.model,
        "max_tokens": args.max_tokens,
        "reasoning_effort": args.reasoning_effort,
        "concurrency": args.concurrency,
        "sample_mode": args.sample_mode,
        "max_actual_cost_usd": args.max_actual_cost_usd,
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
        f"- Concurrency: `{summary['concurrency']}`",
        f"- Sample mode: `{summary['sample_mode']}`",
        f"- Global cost cap: `${float(summary['max_actual_cost_usd'] or 0.0):.6f}`",
        f"- Records attempted: {summary['records_attempted']} / selected {summary['records_selected']}",
        f"- Successes: {summary['successes']}",
        f"- Success rate: {rate:.1%}" if rate is not None else "- Success rate: n/a",
        f"- Actual reported cost: `${summary['actual_cost_usd']:.6f}`",
        f"- Failure classes: `{json.dumps(summary['failure_classes'], sort_keys=True)}`",
        "",
        "Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; the generated theorem compiled; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.",
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
    parser.add_argument("--lake-cache-from", type=Path, default=None)
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
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    summary = run(parse_args())
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))
