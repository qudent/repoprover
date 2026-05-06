#!/usr/bin/env python3
"""Mine source-visible context candidates from proof-lane decline notes.

This is a source-only diagnostic: it does not read gold-candidate alignment rows
or elaborated target dependencies. It passively scans saved proof-lane outputs,
target-hidden proof-lane task dossiers, and project Lean source files. Candidate
declarations found here still need prompt-safety filtering before they can be
used as model-facing context for a benchmark run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_latex_statement_generation import write_json  # noqa: E402
from scripts.run_latex_statement_generation_repair import load_generation_output  # noqa: E402


DECL_RE = re.compile(
    r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial|nonrec)\s+)*"
    r"(?P<kind>theorem|lemma|def|abbrev|instance|class|structure|inductive|axiom|constant|opaque)"
    r"\s+(?P<name>[^\s:\{\(\[]+)"
)
NAMESPACE_RE = re.compile(r"^\s*namespace\s+(?P<name>[A-Za-z0-9_'. ]+)\s*$")
SECTION_RE = re.compile(r"^\s*(?:noncomputable\s+)?section(?:\s+(?P<name>[A-Za-z0-9_'.]+))?\s*$")
END_RE = re.compile(r"^\s*end(?:\s+(?P<name>[A-Za-z0-9_'.]+))?\s*$")
IDENT_RE = re.compile(
    r"(?<![A-Za-z0-9_'.])([A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*)"
    r"(?![A-Za-z0-9_'])"
)

STOPWORDS = {
    "a",
    "about",
    "additional",
    "all",
    "also",
    "and",
    "api",
    "are",
    "argument",
    "available",
    "because",
    "been",
    "beyond",
    "but",
    "cannot",
    "case",
    "checked",
    "clean",
    "code",
    "complete",
    "completed",
    "complex",
    "constructing",
    "context",
    "correct",
    "could",
    "declared",
    "definition",
    "definitions",
    "diagnosis",
    "direct",
    "does",
    "due",
    "empty",
    "encode",
    "enough",
    "failed",
    "fail",
    "fails",
    "fact",
    "facts",
    "file",
    "from",
    "full",
    "function",
    "general",
    "has",
    "have",
    "helper",
    "here",
    "identifiers",
    "identity",
    "implementing",
    "insufficient",
    "into",
    "is",
    "jacobi",
    "lemma",
    "lemmas",
    "left_inv",
    "local",
    "missing",
    "model",
    "not",
    "notes",
    "only",
    "over",
    "predecessors",
    "proof",
    "prove",
    "provided",
    "provides",
    "require",
    "requires",
    "right",
    "right_inv",
    "scope",
    "single",
    "source",
    "statement",
    "step",
    "strategy",
    "structure",
    "that",
    "the",
    "their",
    "therefore",
    "these",
    "this",
    "those",
    "through",
    "trudi",
    "type",
    "types",
    "using",
    "visible",
    "which",
    "with",
    "without",
    "working",
    "would",
    "cannot_prove_from_visible_context",
}

LEAN_NAMESPACE_ONLY = {
    "Fin",
    "Finset",
    "Function",
    "Int",
    "List",
    "Mathlib",
    "Matrix",
    "Nat",
    "Nat.Partition",
    "PowerSeries",
    "Prop",
    "Rat",
    "Ring",
    "Semiring",
    "CommSemiring",
    "CommRing",
    "Field",
    "IsUnit",
    "SimpleDigraph",
    "Sort",
    "Subtype",
    "True",
    "Type",
    "ZMod",
    "API",
    "Jacobi",
    "Trudi",
}


@dataclass(frozen=True)
class Declaration:
    full_name: str
    local_name: str
    kind: str
    path: str
    line: int
    snippet: str


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def strip_comments_and_strings(text: str) -> str:
    output: list[str] = []
    block_depth = 0
    for line in text.splitlines():
        index = 0
        buffer: list[str] = []
        in_string = False
        escaped = False
        while index < len(line):
            if block_depth == 0 and not in_string and line.startswith("/-", index):
                block_depth += 1
                index += 2
                continue
            if block_depth > 0:
                if line.startswith("/-", index):
                    block_depth += 1
                    index += 2
                    continue
                if line.startswith("-/", index):
                    block_depth -= 1
                    index += 2
                    continue
                index += 1
                continue
            char = line[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                buffer.append(" ")
                index += 1
                continue
            if line.startswith("--", index):
                break
            if char == '"':
                in_string = True
                buffer.append(" ")
                index += 1
                continue
            buffer.append(char)
            index += 1
        output.append("".join(buffer))
    return "\n".join(output)


def lean_source_files(project_root: Path) -> list[Path]:
    return sorted(
        path
        for path in project_root.rglob("*.lean")
        if ".lake" not in path.parts and path.name != "lakefile.lean"
    )


def normalize_decl_name(raw_name: str) -> str:
    name = raw_name.strip().strip("`")
    if name.startswith("«") and name.endswith("»"):
        name = name[1:-1]
    return name


def snippet_from_lines(lines: list[str], start_index: int, *, max_lines: int = 32) -> str:
    end_index = start_index + 1
    while end_index < len(lines) and end_index - start_index < max_lines:
        clean = strip_comments_and_strings(lines[end_index])
        if DECL_RE.match(clean) and end_index > start_index + 1:
            break
        end_index += 1
    return "\n".join(lines[start_index:end_index]).strip()


def parse_project_declarations(project_root: Path) -> list[Declaration]:
    declarations: list[Declaration] = []
    for path in lean_source_files(project_root):
        original_lines = path.read_text(encoding="utf-8").splitlines()
        clean_lines = strip_comments_and_strings("\n".join(original_lines)).splitlines()
        namespace_stack: list[str] = []
        scope_stack: list[tuple[str, list[str]]] = []
        for index, line in enumerate(clean_lines):
            if match := NAMESPACE_RE.match(line):
                parts = [part for part in match.group("name").strip().split() if part]
                namespace_stack.extend(parts)
                scope_stack.append(("namespace", parts))
                continue
            if SECTION_RE.match(line):
                scope_stack.append(("section", []))
                continue
            if END_RE.match(line):
                if scope_stack:
                    kind, parts = scope_stack.pop()
                    if kind == "namespace":
                        for _ in parts:
                            if namespace_stack:
                                namespace_stack.pop()
                continue
            if match := DECL_RE.match(line):
                raw_name = normalize_decl_name(match.group("name"))
                if not raw_name or raw_name.startswith(("[", "{", "(")):
                    continue
                full_name = raw_name if "." in raw_name or not namespace_stack else ".".join(namespace_stack + [raw_name])
                declarations.append(
                    Declaration(
                        full_name=full_name,
                        local_name=full_name.split(".")[-1],
                        kind=match.group("kind"),
                        path=display_path(path),
                        line=index + 1,
                        snippet=snippet_from_lines(original_lines, index),
                    )
                )
    return declarations


def generation_outputs_for_run(run_dir: Path) -> list[dict[str, Any]]:
    merged = run_dir / "eval" / "merged-generation-output.json"
    if merged.exists():
        return list(load_generation_output(merged).get("units") or [])
    units: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("batch-*/generation-output.json")):
        units.extend(load_generation_output(path).get("units") or [])
    return units


def infer_task_dir(run_dir: Path) -> Path | None:
    for name in ("proof-lane-generation-results.json", "generation-results.json"):
        path = run_dir / "eval" / name
        if not path.exists():
            continue
        try:
            task_dir = read_json(path).get("proof_lane_task_dir")
        except (OSError, json.JSONDecodeError):
            continue
        if task_dir:
            return Path(str(task_dir))
    return None


def load_tasks(task_dir: Path | None) -> dict[str, dict[str, Any]]:
    if task_dir is None:
        return {}
    tasks_dir = task_dir / "tasks"
    paths = sorted(tasks_dir.glob("*.json")) if tasks_dir.exists() else []
    tasks: dict[str, dict[str, Any]] = {}
    for path in paths:
        task = read_json(path)
        unit_key = str(task.get("unit_key") or "")
        if unit_key:
            tasks[unit_key] = task
    return tasks


def walk_values(value: Any) -> list[Any]:
    values = [value]
    if isinstance(value, dict):
        for child in value.values():
            values.extend(walk_values(child))
    elif isinstance(value, list):
        for child in value:
            values.extend(walk_values(child))
    return values


def visible_decl_names(task: dict[str, Any]) -> set[str]:
    names: set[str] = set()

    def add_name(value: Any) -> None:
        if isinstance(value, str) and value:
            names.add(value)
            names.add(value.split(".")[-1])

    contexts = [task.get("visible_prompt_context") or {}]
    for context in list(contexts):
        nested = context.get("visible_prompt_context") if isinstance(context, dict) else None
        if isinstance(nested, dict):
            contexts.append(nested)
    for context in contexts:
        for planned in context.get("planned_declarations") or []:
            for project_context in planned.get("available_prior_project_context") or []:
                for declaration in project_context.get("project_declarations") or []:
                    add_name(declaration.get("name"))
            for declaration in planned.get("local_file_predecessor_declarations") or []:
                add_name(declaration.get("name"))
            for item in planned.get("hydrated_mathlib_context") or []:
                if (item.get("lean_check") or {}).get("status") == "checked":
                    add_name(item.get("exact_identifier") or item.get("name") or item.get("query"))
                for related in item.get("related_mathlib_declarations") or []:
                    if (related.get("lean_check") or {}).get("status") == "checked":
                        add_name(related.get("name"))
        for repair_context in context.get("additional_checked_repair_context") or []:
            for item in repair_context.get("checked_signatures") or []:
                add_name(item.get("name"))
            for item in repair_context.get("selected_visible_context") or []:
                add_name(item.get("name_or_label"))
    return names


def task_visible_text(task: dict[str, Any]) -> str:
    return json.dumps(task, sort_keys=True, ensure_ascii=False)


def looks_like_context_identifier(token: str) -> bool:
    if token in LEAN_NAMESPACE_ONLY:
        return False
    if token in STOPWORDS or token.lower() in STOPWORDS:
        return False
    if "." in token and token.split(".")[0][:1].islower():
        return False
    if len(token) <= 2 and "." not in token and "_" not in token and "'" not in token:
        return False
    if "." in token:
        return True
    if "_" in token or "'" in token:
        return True
    return any(char.isupper() for char in token)


def extract_note_identifiers(notes: list[Any]) -> list[str]:
    seen: set[str] = set()
    identifiers: list[str] = []
    for note in notes:
        if not isinstance(note, str):
            continue
        for token in IDENT_RE.findall(note):
            if not looks_like_context_identifier(token):
                continue
            if token not in seen:
                seen.add(token)
                identifiers.append(token)
    return identifiers


def declaration_indexes(declarations: list[Declaration]) -> tuple[dict[str, Declaration], dict[str, list[Declaration]]]:
    by_full = {declaration.full_name: declaration for declaration in declarations}
    by_local: dict[str, list[Declaration]] = {}
    for declaration in declarations:
        by_local.setdefault(declaration.local_name, []).append(declaration)
    return by_full, by_local


def candidate_records(
    identifier: str,
    *,
    by_full: dict[str, Declaration],
    by_local: dict[str, list[Declaration]],
    visible_names: set[str],
    visible_text: str,
    max_candidates: int,
) -> list[dict[str, Any]]:
    candidate_map: dict[str, tuple[Declaration, str]] = {}

    def add(declaration: Declaration, match_kind: str) -> None:
        existing = candidate_map.get(declaration.full_name)
        if existing is None:
            candidate_map[declaration.full_name] = (declaration, match_kind)

    if identifier in by_full:
        add(by_full[identifier], "exact_full_name")
    if "." in identifier:
        suffix = "." + identifier
        for declaration in by_full.values():
            if declaration.full_name.endswith(suffix):
                add(declaration, "suffix_full_name")
    local = identifier.split(".")[-1]
    dotted_head = identifier.split(".")[0] if "." in identifier else ""
    allow_local_fallback = "." not in identifier or dotted_head[:1].isupper()
    if allow_local_fallback:
        for declaration in by_local.get(local, []):
            add(declaration, "exact_local_name")
    if not candidate_map and "." not in identifier and len(identifier) >= 5:
        for declaration in by_full.values():
            if identifier in declaration.full_name:
                add(declaration, "substring_full_name")

    def sort_key(item: tuple[str, tuple[Declaration, str]]) -> tuple[int, str]:
        ranks = {
            "exact_full_name": 0,
            "suffix_full_name": 1,
            "exact_local_name": 2,
            "substring_full_name": 3,
        }
        declaration, match_kind = item[1]
        return (ranks.get(match_kind, 99), declaration.full_name)

    records: list[dict[str, Any]] = []
    for _, (declaration, match_kind) in sorted(candidate_map.items(), key=sort_key)[:max_candidates]:
        selected = declaration.full_name in visible_names or declaration.local_name in visible_names
        records.append(
            {
                "name": declaration.full_name,
                "local_name": declaration.local_name,
                "kind": declaration.kind,
                "path": declaration.path,
                "line": declaration.line,
                "match_kind": match_kind,
                "selected_as_project_or_local_context": selected,
                "name_string_visible_in_task": (
                    declaration.full_name in visible_text
                    or declaration.local_name in visible_text
                    or identifier in visible_text
                ),
                "snippet": declaration.snippet,
            }
        )
    return records


def classify_identifier(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "not_found_in_project_index"
    if any(candidate["selected_as_project_or_local_context"] for candidate in candidates):
        return "found_and_selected_as_visible_context"
    if any(candidate["name_string_visible_in_task"] for candidate in candidates):
        return "found_and_name_mentioned_but_declaration_not_selected"
    return "found_but_not_visible"


def analyze_unit(
    *,
    run_dir: Path,
    unit: dict[str, Any],
    task: dict[str, Any],
    by_full: dict[str, Declaration],
    by_local: dict[str, list[Declaration]],
    max_candidates: int,
) -> dict[str, Any]:
    notes = list(unit.get("notes") or [])
    identifiers = extract_note_identifiers(notes)
    visible_names = visible_decl_names(task)
    visible_text = task_visible_text(task) if task else ""
    results: list[dict[str, Any]] = []
    class_counts: dict[str, int] = {}
    for identifier in identifiers:
        candidates = candidate_records(
            identifier,
            by_full=by_full,
            by_local=by_local,
            visible_names=visible_names,
            visible_text=visible_text,
            max_candidates=max_candidates,
        )
        classification = classify_identifier(candidates)
        class_counts[classification] = class_counts.get(classification, 0) + 1
        results.append(
            {
                "identifier": identifier,
                "classification": classification,
                "candidate_count": len(candidates),
                "candidates": candidates,
            }
        )

    return {
        "run_dir": display_path(run_dir),
        "unit_key": unit.get("unit_key"),
        "status": unit.get("status"),
        "notes": notes,
        "extracted_identifier_count": len(identifiers),
        "identifier_class_counts": dict(sorted(class_counts.items())),
        "identifier_results": results,
    }


def summarize_units(units: list[dict[str, Any]]) -> dict[str, Any]:
    class_counts: dict[str, int] = {}
    unit_count_by_run: dict[str, int] = {}
    for unit in units:
        unit_count_by_run[str(unit["run_dir"])] = unit_count_by_run.get(str(unit["run_dir"]), 0) + 1
        for classification, count in (unit.get("identifier_class_counts") or {}).items():
            class_counts[classification] = class_counts.get(classification, 0) + int(count)
    return {
        "declined_unit_count": len(units),
        "unit_count_by_run": dict(sorted(unit_count_by_run.items())),
        "identifier_class_counts": dict(sorted(class_counts.items())),
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    declarations = parse_project_declarations(args.project_root)
    by_full, by_local = declaration_indexes(declarations)
    rows: list[dict[str, Any]] = []
    task_dirs: dict[Path, dict[str, dict[str, Any]]] = {}

    for run_dir in args.proof_lane_generation_run:
        task_dir = args.proof_lane_task_dir or infer_task_dir(run_dir)
        if task_dir not in task_dirs:
            task_dirs[task_dir] = load_tasks(task_dir)
        tasks = task_dirs[task_dir]
        for unit in generation_outputs_for_run(run_dir):
            if unit.get("status") != "cannot_prove_from_visible_context":
                continue
            if args.unit_key and str(unit.get("unit_key") or "") not in set(args.unit_key):
                continue
            rows.append(
                analyze_unit(
                    run_dir=run_dir,
                    unit=unit,
                    task=tasks.get(str(unit.get("unit_key") or ""), {}),
                    by_full=by_full,
                    by_local=by_local,
                    max_candidates=args.max_candidates,
                )
            )

    return {
        "schema_version": "repoprover.proof_lane_decline_context_mining.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": display_path(args.project_root),
        "proof_lane_generation_runs": [display_path(path) for path in args.proof_lane_generation_run],
        "project_declaration_count": len(declarations),
        "project_file_count": len(lean_source_files(args.project_root)),
        "summary": summarize_units(rows),
        "units": rows,
        "benchmark_honesty_caveat": (
            "This report does not use gold alignment or elaborated target dependencies. It scans "
            "the project source tree and target-hidden proof-lane dossiers only. Because the current "
            "repo contains the finished formalization, candidate declarations must still be filtered "
            "against target-hidden/current-unit policy before being placed into model prompts."
        ),
    }


def markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Proof-Lane Decline Context Mining",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Scope",
        f"- Project root: `{summary['project_root']}`",
        f"- Project declarations indexed: `{summary['project_declaration_count']}`",
        f"- Project files indexed: `{summary['project_file_count']}`",
        f"- Declined units analyzed: `{summary['summary']['declined_unit_count']}`",
        f"- Identifier classes: `{json.dumps(summary['summary']['identifier_class_counts'], sort_keys=True)}`",
        "",
        "## Caveat",
        summary["benchmark_honesty_caveat"],
        "",
        "## Units",
    ]
    for unit in summary["units"]:
        lines.extend(
            [
                "",
                f"### {unit['run_dir']} / {unit['unit_key']}",
                "",
                f"- Status: `{unit['status']}`",
                f"- Identifier classes: `{json.dumps(unit['identifier_class_counts'], sort_keys=True)}`",
                "",
            ]
        )
        for result in unit["identifier_results"]:
            candidates = result["candidates"]
            if candidates:
                candidate_text = "; ".join(
                    f"`{candidate['name']}` ({candidate['kind']}, {candidate['path']}:{candidate['line']}, {candidate['match_kind']})"
                    for candidate in candidates[:3]
                )
            else:
                candidate_text = "no project-source candidate"
            lines.append(
                f"- `{result['identifier']}`: `{result['classification']}`; {candidate_text}"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof-lane-generation-run", type=Path, action="append", required=True)
    parser.add_argument("--proof-lane-task-dir", type=Path)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--unit-key", action="append")
    parser.add_argument("--max-candidates", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    summary = analyze(args)
    write_json(args.output, summary)
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
