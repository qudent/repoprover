#!/usr/bin/env python3
"""Generate minimal-context gold-standard candidate records.

This script is deliberately separate from RepoProver runs. It fetches real
Lean/TeX files from the published Algebraic Combinatorics repository, splits a
Lean file into small output chunks, asks an OpenRouter model for the smallest
backward context needed to reproduce each chunk, and writes JSONL records with
embedded trust, time, and spend metadata.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

try:
    from scripts.review_minimal_context_records import (
        DEFAULT_BASE_URL,
        DEFAULT_SOURCE_BASE,
        ReviewUsage,
        estimate_usage,
        extract_json_object,
        fetch_repo_file,
        numbered_snippet,
        openrouter_prices,
        write_jsonl,
    )
except ModuleNotFoundError:
    from review_minimal_context_records import (
        DEFAULT_BASE_URL,
        DEFAULT_SOURCE_BASE,
        ReviewUsage,
        estimate_usage,
        extract_json_object,
        fetch_repo_file,
        numbered_snippet,
        openrouter_prices,
        write_jsonl,
    )


DEFAULT_MODEL = "qwen/qwen3-coder"
GENERATOR_VERSION = "minimal-context-record-generator-v1"
MODEL_TRUST_CAPS = {
    "source_span": 0.65,
    "lean_dependency_graph": 0.55,
    "model_extraction": 0.45,
    "human_review": 0.0,
}
DECL_RE = re.compile(
    r"^\s*(?P<private>private\s+)?(?P<noncomputable>noncomputable\s+)?"
    r"(?P<kind>theorem|lemma|def|abbrev|instance|class|structure|inductive)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_']*)(?=\s|:|\{|\(|\[)"
)


@dataclass(frozen=True)
class LeanDeclaration:
    kind: str
    name: str
    full_name: str
    declaration_line: int
    start_line: int
    end_line: int
    is_private: bool


@dataclass(frozen=True)
class CandidateChunk:
    declarations: list[LeanDeclaration]
    start_line: int
    end_line: int
    snippet: str

    @property
    def declaration_names(self) -> list[str]:
        return [decl.full_name for decl in self.declarations]

    @property
    def record_suffix(self) -> str:
        return ".".join(decl.name for decl in self.declarations)


def current_namespace(lines: list[str], line_number: int) -> str:
    namespace = ""
    for line in lines[: line_number - 1]:
        match = re.match(r"^\s*namespace\s+(.+?)\s*$", line)
        if match:
            namespace = match.group(1).strip()
            continue
        match = re.match(r"^\s*end\s+(.+?)\s*$", line)
        if match and match.group(1).strip() == namespace:
            namespace = ""
    return namespace


def declaration_display_start(lines: list[str], declaration_index: int) -> int:
    start = declaration_index
    while start > 0 and lines[start - 1].strip().startswith("@["):
        start -= 1

    if start > 0 and lines[start - 1].strip().endswith("-/"):
        comment_start = start - 1
        while comment_start > 0 and not lines[comment_start].lstrip().startswith(("/--", "/-!")):
            comment_start -= 1
        if lines[comment_start].lstrip().startswith(("/--", "/-!")):
            start = comment_start
            while start > 0 and lines[start - 1].strip().startswith("@["):
                start -= 1
    return start + 1


def trim_declaration_end(lines: list[str], end_line: int) -> int:
    while end_line > 1:
        stripped = lines[end_line - 1].strip()
        if not stripped or stripped.startswith("end "):
            end_line -= 1
            continue
        break
    return end_line


def parse_lean_declarations(lean_text: str, include_private: bool = False) -> list[LeanDeclaration]:
    lines = lean_text.splitlines()
    raw: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        match = DECL_RE.match(line)
        if not match:
            continue
        is_private = bool(match.group("private"))
        namespace = current_namespace(lines, index)
        name = match.group("name")
        raw.append(
            {
                "kind": match.group("kind"),
                "name": name,
                "full_name": f"{namespace}.{name}" if namespace else name,
                "declaration_line": index,
                "start_line": declaration_display_start(lines, index - 1),
                "is_private": is_private,
            }
        )

    declarations: list[LeanDeclaration] = []
    for offset, decl in enumerate(raw):
        next_start = raw[offset + 1]["start_line"] if offset + 1 < len(raw) else len(lines) + 1
        end_line = trim_declaration_end(lines, next_start - 1)
        declarations.append(
            LeanDeclaration(
                kind=decl["kind"],
                name=decl["name"],
                full_name=decl["full_name"],
                declaration_line=decl["declaration_line"],
                start_line=decl["start_line"],
                end_line=end_line,
                is_private=decl["is_private"],
            )
        )
    if include_private:
        return declarations
    return [decl for decl in declarations if not decl.is_private]


def select_declarations(
    declarations: list[LeanDeclaration],
    after_line: int,
    before_line: int,
    limit: int,
) -> list[LeanDeclaration]:
    selected = [
        decl
        for decl in declarations
        if decl.declaration_line >= after_line and (before_line <= 0 or decl.declaration_line <= before_line)
    ]
    return selected[:limit] if limit else selected


def chunk_declarations(
    declarations: list[LeanDeclaration],
    lean_text: str,
    chunk_size: int,
) -> list[CandidateChunk]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    lines = lean_text.splitlines()
    chunks: list[CandidateChunk] = []
    for index in range(0, len(declarations), chunk_size):
        group = declarations[index : index + chunk_size]
        start_line = group[0].start_line
        end_line = group[-1].end_line
        chunks.append(
            CandidateChunk(
                declarations=group,
                start_line=start_line,
                end_line=end_line,
                snippet=numbered_snippet(lean_text, start_line, end_line, context=0),
            )
        )
    return chunks


def parse_line_range(value: str | None, total_lines: int) -> tuple[int, int]:
    if not value:
        return (1, total_lines)
    match = re.fullmatch(r"(\d+):(\d+)", value)
    if not match:
        raise ValueError("--tex-range must use START:END")
    start = max(1, int(match.group(1)))
    end = min(total_lines, int(match.group(2)))
    if start > end:
        raise ValueError("--tex-range START must be <= END")
    return (start, end)


def generation_prompt(
    *,
    chapter_id: str,
    lean_path: str,
    tex_path: str,
    candidate: CandidateChunk,
    tex_snippet: str,
) -> list[dict[str, str]]:
    system = (
        "You generate adversarial benchmark records for Lean textbook formalization. "
        "Given a known-good Lean output chunk and a real textbook TeX excerpt, identify the "
        "smallest sufficient backward context an agent would need before writing that Lean. "
        "Keep ugly mismatches and missing-context risk explicit. Return exactly one JSON object."
    )
    schema = {
        "record_suffix": "short id suffix, usually the main declaration name",
        "chunk_kind": "definition | theorem | lemma | theorem_cluster | definition_cluster | proof_support_cluster",
        "source_spans": [
            {
                "path": tex_path,
                "line_range": [1, 2],
                "labels": ["tex labels if present"],
                "reason": "why this span is needed",
            }
        ],
        "lean_predecessors": [
            {
                "path": lean_path,
                "declaration": "fully.qualified.name",
                "reason": "notation/API/proof dependency reused by the output",
            }
        ],
        "imports": ["specific Lean imports when inferable, otherwise Mathlib"],
        "mathlib_context": ["specific Mathlib names or tactics needed"],
        "tex_only_inferability": {
            "score": "0 to 1; how likely the Lean chunk could be inferred from TeX alone",
            "assessment": "short explanation",
            "missing_from_tex_only": ["Lean-only APIs, typeclass constraints, imports, proof lemmas"],
        },
        "trust": {
            "source_span": "0 to 1",
            "lean_dependency_graph": "0 to 1",
            "model_extraction": "0 to 1",
            "human_review": 0,
        },
        "review_notes": ["durable notes, including mismatches and failure-sensitive details"],
    }
    user = (
        f"Chapter id: {chapter_id}\n"
        f"Lean path: {lean_path}\n"
        f"Target declaration names: {json.dumps(candidate.declaration_names)}\n"
        f"Target Lean line range: [{candidate.start_line}, {candidate.end_line}]\n\n"
        "Required JSON shape:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Known-good Lean output chunk:\n"
        f"{candidate.snippet}\n\n"
        "Textbook TeX excerpt with line numbers:\n"
        f"{tex_snippet}\n\n"
        "Do not include the Lean output itself in your JSON. Make the context minimal but honest. "
        "If the TeX alone is not enough to infer the Lean, say exactly what Lean/mathlib context is missing. "
        "Use lean_predecessors only for local predecessor declarations from the Lean file; put Mathlib facts, "
        "tactics, and imported APIs in mathlib_context."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def usage_to_dict(usage: ReviewUsage) -> dict[str, Any]:
    return {
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "estimated_cost_usd": usage.cost_usd,
    }


def resolve_local_declaration(name: str, local_declarations: dict[str, LeanDeclaration]) -> str | None:
    if name in local_declarations:
        return name
    normalized_name = name.replace("'", "")
    short_matches = [
        full_name
        for full_name, declaration in local_declarations.items()
        if declaration.name == name
        or full_name.endswith(f".{name}")
        or declaration.name.replace("'", "") == normalized_name
        or full_name.replace("'", "").endswith(f".{normalized_name}")
    ]
    if len(short_matches) == 1:
        return short_matches[0]
    return None


def normalize_context_fields(
    model_record: dict[str, Any],
    local_declarations: dict[str, LeanDeclaration],
    lean_path: str,
    local_namespace: str = "",
) -> tuple[list[dict[str, str]], list[str]]:
    lean_predecessors: list[dict[str, str]] = []
    mathlib_context: list[str] = []
    seen_predecessors: set[str] = set()
    seen_mathlib: set[str] = set()

    def add_mathlib(value: str) -> None:
        value = str(value).strip()
        if local_namespace and value.startswith(f"{local_namespace}."):
            value = value[len(local_namespace) + 1 :]
        if value and value not in seen_mathlib:
            mathlib_context.append(value)
            seen_mathlib.add(value)

    def add_local(full_name: str, reason: str) -> None:
        if full_name in seen_predecessors:
            return
        lean_predecessors.append({"path": lean_path, "declaration": full_name, "reason": reason})
        seen_predecessors.add(full_name)

    for predecessor in model_record.get("lean_predecessors") or []:
        declaration = str(predecessor.get("declaration", "")).strip()
        full_name = resolve_local_declaration(declaration, local_declarations)
        if full_name:
            add_local(full_name, str(predecessor.get("reason", "local predecessor declaration")))
        else:
            add_mathlib(declaration)

    for value in model_record.get("mathlib_context") or []:
        value = str(value).strip()
        full_name = resolve_local_declaration(value, local_declarations)
        if full_name:
            add_local(full_name, "Generator listed this as context; resolved as a local predecessor declaration.")
        else:
            add_mathlib(value)

    return lean_predecessors, mathlib_context


def call_generator(
    client: OpenAI,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    prices: dict[str, tuple[float, float]],
) -> tuple[dict[str, Any], str, ReviewUsage, float]:
    started = time.monotonic()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    elapsed = time.monotonic() - started
    content = response.choices[0].message.content or ""
    parsed = extract_json_object(content)
    usage = estimate_usage(response, model, prices)
    return parsed, content, usage, elapsed


def normalize_model_record(
    *,
    model_record: dict[str, Any],
    candidate: CandidateChunk,
    chapter_id: str,
    lean_path: str,
    tex_path: str,
    model: str,
    source_base_url: str,
    usage: ReviewUsage,
    elapsed_seconds: float,
    generated_at: str,
    raw_response: str,
    local_declarations: dict[str, LeanDeclaration] | None = None,
) -> dict[str, Any]:
    suffix = str(model_record.get("record_suffix") or candidate.record_suffix)
    suffix = re.sub(r"[^A-Za-z0-9_.:-]+", "-", suffix).strip("-") or candidate.record_suffix

    raw_trust = {
        "source_span": 0.25,
        "lean_dependency_graph": 0.25,
        "model_extraction": 0.25,
        "human_review": 0.0,
        **(model_record.get("trust") or {}),
    }
    trust = {
        key: min(float(raw_trust.get(key) or 0.0), cap)
        for key, cap in MODEL_TRUST_CAPS.items()
    }
    trust_notes = []
    for key, cap in MODEL_TRUST_CAPS.items():
        if float(raw_trust.get(key) or 0.0) > cap:
            trust_notes.append(f"{key} trust capped at {cap} for unreviewed model-generated data.")
    lean_predecessors, mathlib_context = normalize_context_fields(
        model_record,
        local_declarations or {},
        lean_path,
        local_namespace=".".join(candidate.declarations[0].full_name.split(".")[:-1]),
    )

    tex_only = model_record.get("tex_only_inferability") or {}
    record = {
        "id": f"{chapter_id}:{suffix}",
        "chapter_id": chapter_id,
        "output": {
            "lean_path": lean_path,
            "declaration_names": candidate.declaration_names,
            "line_range": [candidate.start_line, candidate.end_line],
            "chunk_kind": model_record.get("chunk_kind", "theorem_cluster"),
        },
        "minimal_context": {
            "source_spans": model_record.get("source_spans")
            or [{"path": tex_path, "line_range": [1, 1], "labels": [], "reason": "model did not identify a span"}],
            "lean_predecessors": lean_predecessors,
            "imports": model_record.get("imports") or ["Mathlib"],
            "mathlib_context": mathlib_context,
        },
        "tex_only_inferability": {
            "score": tex_only.get("score", 0.0),
            "assessment": tex_only.get("assessment", "not assessed"),
            "missing_from_tex_only": tex_only.get("missing_from_tex_only", []),
        },
        "trust": trust,
        "review_notes": [*(model_record.get("review_notes") or []), *trust_notes],
        "generation": {
            "generated_at": generated_at,
            "generator_version": GENERATOR_VERSION,
            "generator_model": model,
            "source_base_url": source_base_url,
            "elapsed_seconds": round(elapsed_seconds, 3),
            **usage_to_dict(usage),
        },
        "raw_model_response": raw_response,
    }
    return record


def print_generation_summary(rows: list[dict[str, Any]], output: Path) -> None:
    total_prompt = sum(int(row["generation"].get("prompt_tokens") or 0) for row in rows)
    total_completion = sum(int(row["generation"].get("completion_tokens") or 0) for row in rows)
    total_cost = sum(float(row["generation"].get("estimated_cost_usd") or 0.0) for row in rows)
    print(f"wrote {len(rows)} records to {output}")
    print(f"generation usage: {total_prompt:,} prompt / {total_completion:,} completion, ${total_cost:.6f}")
    for row in rows:
        print(
            f"- {row['id']}: tex-only={row['tex_only_inferability'].get('score')} "
            f"trust={json.dumps(row['trust'], sort_keys=True)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter-id", required=True)
    parser.add_argument("--lean-path", required=True)
    parser.add_argument("--tex-path", required=True)
    parser.add_argument("--output", type=Path, default=Path("docs/minimal-context-generated-records.jsonl"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--source-base-url", default=DEFAULT_SOURCE_BASE)
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/minimal-context-sources"))
    parser.add_argument("--after-line", type=int, default=1, help="First Lean declaration line to consider.")
    parser.add_argument("--before-line", type=int, default=0, help="Last Lean declaration line to consider.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum declarations selected before chunking; 0 means all.")
    parser.add_argument("--chunk-size", type=int, default=1, help="Number of declarations per generated record.")
    parser.add_argument("--tex-range", help="TeX excerpt range as START:END. Defaults to the full TeX file.")
    parser.add_argument("--include-private", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--dry-run", action="store_true", help="Print candidate evidence and do not call OpenRouter.")
    parser.add_argument("--keep-raw-response", action="store_true", help="Keep raw_model_response in output JSONL.")
    args = parser.parse_args()

    lean_text = fetch_repo_file(args.lean_path, args.source_base_url, args.cache_dir)
    tex_text = fetch_repo_file(args.tex_path, args.source_base_url, args.cache_dir)
    all_declarations = parse_lean_declarations(lean_text, include_private=True)
    declarations = [decl for decl in all_declarations if args.include_private or not decl.is_private]
    selected = select_declarations(declarations, args.after_line, args.before_line, args.limit)
    if not selected:
        print("error: no Lean declarations selected", file=sys.stderr)
        return 1
    candidates = chunk_declarations(selected, lean_text, args.chunk_size)
    tex_start, tex_end = parse_line_range(args.tex_range, len(tex_text.splitlines()))
    tex_snippet = numbered_snippet(tex_text, tex_start, tex_end, context=0)

    if args.dry_run:
        evidence = [
            {
                "declaration_names": candidate.declaration_names,
                "lean_line_range": [candidate.start_line, candidate.end_line],
                "lean_snippet": candidate.snippet,
                "tex_path": args.tex_path,
                "tex_line_range": [tex_start, tex_end],
            }
            for candidate in candidates
        ]
        print(json.dumps(evidence, indent=2))
        return 0

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("error: OPENROUTER_API_KEY is not set", file=sys.stderr)
        return 1

    client = OpenAI(base_url=DEFAULT_BASE_URL, api_key=api_key)
    prices = openrouter_prices([args.model])
    generated_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        messages = generation_prompt(
            chapter_id=args.chapter_id,
            lean_path=args.lean_path,
            tex_path=args.tex_path,
            candidate=candidate,
            tex_snippet=tex_snippet,
        )
        try:
            model_record, raw_response, usage, elapsed = call_generator(
                client=client,
                model=args.model,
                messages=messages,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                prices=prices,
            )
        except Exception as exc:
            print(f"error: generation failed for {candidate.record_suffix}: {exc}", file=sys.stderr)
            return 1
        row = normalize_model_record(
            model_record=model_record,
            candidate=candidate,
            chapter_id=args.chapter_id,
            lean_path=args.lean_path,
            tex_path=args.tex_path,
            model=args.model,
            source_base_url=args.source_base_url,
            usage=usage,
            elapsed_seconds=elapsed,
            generated_at=generated_at,
            raw_response=raw_response,
            local_declarations={
                declaration.full_name: declaration
                for declaration in all_declarations
                if declaration.declaration_line < candidate.start_line
            },
        )
        if not args.keep_raw_response:
            row.pop("raw_model_response", None)
        rows.append(row)
        write_jsonl(args.output, rows)
        cost = usage.cost_usd
        cost_text = f", ${cost:.6f}" if isinstance(cost, int | float) else ""
        print(
            f"generated {row['id']}: {usage.prompt_tokens} prompt / {usage.completion_tokens} completion{cost_text}",
            file=sys.stderr,
        )

    print_generation_summary(rows, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
