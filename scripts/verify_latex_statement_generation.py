#!/usr/bin/env python3
"""Verify theorem-level generated Lean file bodies."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMPORTS = ["Mathlib"]
DEFAULT_OPENS = ["open scoped Polynomial BigOperators", "open PowerSeries Finset"]
PLACEHOLDER_RE = re.compile(r"\b(sorry|admit|aesop\?)\b")
LEAN_COMMENT_RE = re.compile(r"(^|\n)\s*(--|/-)")
LEAN_BLOCK_COMMENT_RE = re.compile(r"/-.*?-/", re.DOTALL)
LEAN_LINE_COMMENT_RE = re.compile(r"--.*$")
LEAN_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*$")
LEAN_DOTTED_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)+$")
LEAN_DECL_KIND_RE = re.compile(
    r"(?m)^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
    r"(theorem|lemma|def|abbrev|instance|structure|class|inductive)\s+"
)
LEAN_DECL_RE = re.compile(
    r"(?m)^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
    r"(?:theorem|lemma|def|abbrev|instance|structure|class|inductive)\s+([^\s:\{\(\[]+)"
)
LEAN_ASSUME_DECL_START_RE = re.compile(
    r"(?m)^(\s*)(?:(?:private|protected|noncomputable|unsafe|partial|nonrec)\s+)*"
    r"(?:theorem|lemma|def|abbrev|axiom)\s+"
)
LEAN_DECL_NAME_LINE_RE = re.compile(
    r"(?m)^\s*(?:(?:private|protected|noncomputable|unsafe|partial|nonrec)\s+)*"
    r"(?:theorem|lemma|def|abbrev|instance|structure|class|inductive|axiom)\s+([^\s:\{\(\[]+)"
)
LEAN_DECL_KIND_LINE_RE = re.compile(
    r"(?m)^\s*(?:(?:private|protected|noncomputable|unsafe|partial|nonrec)\s+)*"
    r"(theorem|lemma|def|abbrev|instance|structure|class|inductive|axiom)\s+"
)
LEAN_NAMESPACE_RE = re.compile(r"^\s*namespace\s+([A-Za-z0-9_'. ]+)\s*$")
LEAN_SECTION_RE = re.compile(r"^\s*(?:noncomputable\s+)?section(?:\s+[A-Za-z0-9_'.]+)?\s*$")
LEAN_END_RE = re.compile(r"^\s*end(?:\s+([A-Za-z0-9_'.]+))?\s*$")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def generation_output_paths(run_dir: Path) -> list[Path]:
    if run_dir.is_file():
        return [run_dir]
    return sorted(run_dir.glob("batch-*/generation-output.json"))


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            out.append(value)
            seen.add(value)
    return out


def lean_module_from_path(path_text: str) -> str | None:
    if not path_text:
        return None
    path = Path(path_text)
    if path.suffix == ".lean":
        path = path.with_suffix("")
    parts = [part for part in path.parts if part and part not in {".", ".."}]
    if not parts:
        return None
    module = ".".join(parts)
    return module if LEAN_DOTTED_NAME_RE.fullmatch(module) else None


def lean_module_path(module: str) -> Path | None:
    if not LEAN_DOTTED_NAME_RE.fullmatch(module):
        return None
    return Path(*module.split(".")).with_suffix(".lean")


def project_source_path(project_root: Path, path_text: str) -> Path | None:
    if not path_text:
        return None
    path = Path(path_text)
    candidates: list[Path] = []
    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.extend([project_root / path, REPO_ROOT / path, project_root.parent / path])
        if path.parts and path.parts[0] == project_root.name:
            candidates.append(project_root.parent / path)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def scoped_source_decl_name(raw_name: str, namespace_stack: list[str]) -> str:
    name = raw_name.strip().strip("`")
    if name.startswith("_root_."):
        return name.removeprefix("_root_.")
    if namespace_stack:
        return ".".join([*namespace_stack, name])
    return name


@lru_cache(maxsize=512)
def source_declarations_for_path(path_text: str) -> tuple[tuple[int, str, str], ...]:
    path = Path(path_text)
    if not path.exists():
        return ()
    namespace_stack: list[str] = []
    scope_stack: list[tuple[str, list[str]]] = []
    declarations: list[tuple[int, str, str]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if match := LEAN_NAMESPACE_RE.match(line):
            parts = [part for part in match.group(1).strip().split() if part]
            namespace_stack.extend(parts)
            scope_stack.append(("namespace", parts))
            continue
        if LEAN_SECTION_RE.match(line):
            scope_stack.append(("section", []))
            continue
        if LEAN_END_RE.match(line):
            if scope_stack:
                kind, parts = scope_stack.pop()
                if kind == "namespace":
                    for _ in parts:
                        if namespace_stack:
                            namespace_stack.pop()
            continue
        if match := LEAN_DECL_NAME_LINE_RE.match(line):
            raw_name = match.group(1).strip().strip("`")
            if raw_name and not raw_name.startswith(("[", "{", "(")):
                full_name = scoped_source_decl_name(raw_name, namespace_stack)
                declarations.append((line_number, full_name, full_name.split(".")[-1]))
    return tuple(declarations)


def resolve_source_declaration_name(
    name: str, *, project_root: Path | None, path_text: str, line_text: str
) -> str:
    if project_root is None:
        return name
    source_path = project_source_path(project_root, path_text)
    if source_path is None:
        return name
    declarations = source_declarations_for_path(str(source_path))
    try:
        line = int(line_text or 0)
    except ValueError:
        line = 0
    if line:
        for declaration_line, full_name, _local_name in declarations:
            if declaration_line == line:
                return full_name
    if not name:
        return name
    matches: list[str] = []
    suffix = f".{name}"
    for _line, full_name, local_name in declarations:
        if full_name == name or full_name.endswith(suffix) or local_name == name:
            matches.append(full_name)
    unique_matches = unique_in_order(matches)
    return unique_matches[0] if len(unique_matches) == 1 else name


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


def import_reaches_hidden_target_module(project_root: Path, module: str, hidden_modules: set[str]) -> bool:
    stack = [module]
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if current in hidden_modules:
            return True
        rel_path = lean_module_path(current)
        if rel_path is None:
            continue
        source = project_root / rel_path
        for imported in import_modules_from_lean(source):
            if imported not in seen:
                stack.append(imported)
    return False


def selector_run_for_generation_run(generation_run: Path) -> Path | None:
    if generation_run.is_file():
        return None
    results_path = generation_run / "eval" / "generation-results.json"
    if not results_path.exists():
        return None
    try:
        results = read_json(results_path)
    except (OSError, json.JSONDecodeError):
        return None
    selector_run = str(results.get("selector_run") or "")
    if selector_run:
        return Path(selector_run)
    proof_lane_task_dir = str(results.get("proof_lane_task_dir") or "")
    if not proof_lane_task_dir:
        return None
    summary_path = Path(proof_lane_task_dir) / "proof-lane-summary.json"
    if not summary_path.exists():
        return None
    try:
        proof_lane_summary = read_json(summary_path)
    except (OSError, json.JSONDecodeError):
        return None
    selector_run = str(proof_lane_summary.get("selector_run") or "")
    return Path(selector_run) if selector_run else None


def selected_units_by_key(selector_run: Path | None) -> dict[str, dict[str, Any]]:
    if selector_run is None:
        return {}
    selected_path = selector_run / "eval" / "selected-units.jsonl"
    if not selected_path.exists():
        return {}
    rows = read_jsonl(selected_path)
    return {f"unit-{index + 1:03d}": row for index, row in enumerate(rows)}


def unit_keys_in_generation_output(output_json: dict[str, Any]) -> list[str]:
    return unique_in_order([str(unit.get("unit_key") or "") for unit in output_json.get("units") or []])


def hidden_target_modules_for_units(
    selected_by_key: dict[str, dict[str, Any]], unit_keys: list[str]
) -> list[str]:
    modules: list[str] = []
    for unit_key in unit_keys:
        selected = selected_by_key.get(unit_key) or {}
        aligned_rows = selected.get("posthoc_lean_alignment", {}).get("aligned_lean_declarations", [])
        for aligned in aligned_rows:
            module = str(aligned.get("module") or "") or (lean_module_from_path(str(aligned.get("path") or "")) or "")
            if module and LEAN_DOTTED_NAME_RE.fullmatch(module):
                modules.append(module)
    return unique_in_order(modules)


def hidden_target_namespaces_for_units(
    selected_by_key: dict[str, dict[str, Any]], unit_keys: list[str]
) -> list[str]:
    namespaces: list[str] = []
    for unit_key in unit_keys:
        selected = selected_by_key.get(unit_key) or {}
        aligned_rows = selected.get("posthoc_lean_alignment", {}).get("aligned_lean_declarations", [])
        for aligned in aligned_rows:
            namespace = maybe_namespace(str(aligned.get("full_name") or ""))
            if namespace:
                namespaces.append(namespace)
    return unique_in_order(namespaces)


def open_namespaces(open_statement: str) -> list[str]:
    parts = open_statement.split()
    if len(parts) < 2 or parts[0] != "open" or parts[1] == "scoped":
        return []
    return [part for part in parts[1:] if LEAN_NAME_RE.fullmatch(part)]


def module_under_namespace(module: str, namespace: str) -> bool:
    return module == namespace or module.startswith(f"{namespace}.")


def module_contains_namespace_segment(module: str, namespace: str) -> bool:
    return namespace in module.split(".")


def namespace_matches_hidden(namespace: str, hidden_namespaces: set[str]) -> bool:
    return namespace in hidden_namespaces or any(hidden.endswith(f".{namespace}") for hidden in hidden_namespaces)


def should_filter_open_statement(
    open_statement: str,
    *,
    hidden_namespaces: set[str],
    filtered_imports: list[str],
    kept_imports: list[str],
) -> bool:
    for namespace in open_namespaces(open_statement):
        if namespace_matches_hidden(namespace, hidden_namespaces):
            return True
        removed_namespace_imports = [module for module in filtered_imports if module_under_namespace(module, namespace)]
        kept_namespace_imports = [module for module in kept_imports if module_under_namespace(module, namespace)]
        if removed_namespace_imports and not kept_namespace_imports:
            return True
        removed_segment_imports = [module for module in filtered_imports if module_contains_namespace_segment(module, namespace)]
        kept_segment_imports = [module for module in kept_imports if module_contains_namespace_segment(module, namespace)]
        if removed_segment_imports and not kept_segment_imports:
            return True
    return False


def maybe_namespace(name: str) -> str | None:
    if not LEAN_DOTTED_NAME_RE.fullmatch(name):
        return None
    parts = name.split(".")
    if len(parts) < 2:
        return None
    namespace = ".".join(parts[:-1])
    return namespace if namespace not in {"Mathlib"} else None


def local_declaration_name(name: str) -> str:
    return name.split(".")[-1]


def iter_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(iter_dicts(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(iter_dicts(child))
    return found


def explicit_open_statement(item: dict[str, Any]) -> str | None:
    kind = str(item.get("kind") or "")
    name = str(item.get("name") or "").strip()
    if not name:
        return None
    if kind == "namespace" and LEAN_NAME_RE.fullmatch(name):
        return f"open {name}"
    if kind == "open":
        if name.startswith("open "):
            return name
        if LEAN_NAME_RE.fullmatch(name):
            return f"open {name}"
    return None


def explicit_variable_statement(item: dict[str, Any]) -> str | None:
    if str(item.get("kind") or "") != "variable":
        return None
    name = str(item.get("name") or "").strip()
    if name.endswith(" in"):
        return None
    return name if name.startswith("variable ") else None


def strip_lean_comments(source: str) -> str:
    without_blocks = LEAN_BLOCK_COMMENT_RE.sub("", source)
    lines: list[str] = []
    for line in without_blocks.splitlines():
        lines.append(LEAN_LINE_COMMENT_RE.sub("", line).rstrip())
    compact: list[str] = []
    previous_blank = False
    for line in lines:
        stripped = line.strip()
        blank = not stripped
        if blank and previous_blank:
            continue
        compact.append(line)
        previous_blank = blank
    return "\n".join(compact).strip()


def support_namespace_closers(support_context: list[str]) -> list[str]:
    stack: list[str] = []
    for item in support_context:
        for line in item.splitlines():
            stripped = line.strip()
            if stripped.startswith("namespace "):
                name = stripped.removeprefix("namespace ").strip()
                if name:
                    stack.append(name)
            elif stripped == "end" or stripped.startswith("end "):
                name = stripped.removeprefix("end").strip()
                if name and name in stack:
                    while stack:
                        popped = stack.pop()
                        if popped == name:
                            break
                elif stack:
                    stack.pop()
    return [f"end {name}" for name in reversed(stack)]


def support_snippet_is_complete(snippet: str) -> bool:
    if not snippet or PLACEHOLDER_RE.search(snippet) or not LEAN_DECL_RE.search(snippet):
        return False
    kinds = set(LEAN_DECL_KIND_RE.findall(snippet))
    if kinds <= {"theorem", "lemma"}:
        return ":=" in snippet
    if kinds & {"structure", "class", "inductive"}:
        return " where" in snippet or "\nwhere" in snippet or ":=" in snippet
    return ":=" in snippet or " where" in snippet or "\nwhere" in snippet


def support_snippet_is_assumable(snippet: str) -> bool:
    return bool(snippet and not PLACEHOLDER_RE.search(snippet) and LEAN_DECL_RE.search(snippet))


def trim_support_snippet(snippet: str) -> str:
    lines = snippet.splitlines()
    trimmed: list[str] = []
    seen_declaration = False
    for line in lines:
        stripped = line.strip()
        if seen_declaration and (
            stripped.startswith("namespace ")
            or stripped.startswith("section")
            or stripped.startswith("end ")
            or stripped == "end"
            or stripped.startswith("variable ")
            or stripped.startswith("@[")
        ):
            break
        if LEAN_DECL_KIND_RE.match(line):
            seen_declaration = True
        trimmed.append(line)
    return "\n".join(trimmed).strip()


def support_candidate_sort_key(candidate: dict[str, str]) -> tuple[str, int, str]:
    path = (candidate.get("path") or "").removeprefix("algebraic-combinatorics/").lower()
    try:
        line = int(candidate.get("line") or 0)
    except ValueError:
        line = 0
    line_key = line if line > 0 else 1_000_000_000
    return (path, line_key, candidate.get("name") or "")


def declaration_namespace(name: str) -> str:
    if not LEAN_DOTTED_NAME_RE.fullmatch(name):
        return ""
    parts = name.split(".")
    if len(parts) <= 1:
        return ""
    return ".".join(parts[:-1])


def declaration_name_from_text(text: str) -> str:
    match = LEAN_DECL_NAME_LINE_RE.search(text)
    return match.group(1).strip().strip("`") if match else ""


def declaration_kind_from_text(text: str) -> str:
    match = LEAN_DECL_KIND_LINE_RE.search(text)
    return match.group(1) if match else ""


def top_level_colon_exists(text: str) -> bool:
    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}", "⟨": "⟩"}
    closing = set(pairs.values())
    for char in text:
        if char in pairs:
            depth += 1
        elif char in closing and depth > 0:
            depth -= 1
        elif char == ":" and depth == 0:
            return True
    return False


def declaration_header_without_body(text: str) -> str:
    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}", "⟨": "⟩"}
    closing = set(pairs.values())
    index = 0
    while index < len(text):
        char = text[index]
        if char in pairs:
            depth += 1
            index += 1
            continue
        if char in closing and depth > 0:
            depth -= 1
            index += 1
            continue
        if depth == 0 and text.startswith(":=", index):
            return text[:index].rstrip()
        if depth == 0 and text.startswith("where", index):
            before = text[index - 1] if index else " "
            after = text[index + len("where")] if index + len("where") < len(text) else " "
            if before.isspace() and after.isspace():
                return text[:index].rstrip()
        index += 1
    return text.rstrip()


def wrapper_namespace(indexed_name: str, declared_name: str) -> str:
    if not LEAN_DOTTED_NAME_RE.fullmatch(indexed_name) or not declared_name:
        return ""
    indexed_parts = indexed_name.split(".")
    declared_parts = declared_name.split(".")
    if len(indexed_parts) <= len(declared_parts):
        return ""
    if indexed_parts[-len(declared_parts) :] == declared_parts:
        return ".".join(indexed_parts[: -len(declared_parts)])
    if len(declared_parts) == 1:
        return ".".join(indexed_parts[:-1])
    return ""


def declaration_signature_assumption(text: str) -> str:
    kind = declaration_kind_from_text(text)
    if kind not in {"theorem", "lemma", "def", "abbrev", "axiom"}:
        return text
    text = declaration_header_without_body(text)
    if kind in {"def", "abbrev"} and not top_level_colon_exists(text):
        return ""
    return LEAN_ASSUME_DECL_START_RE.sub(r"\1axiom ", text, count=1).strip()


def support_assumption_text(text: str, declaration_name: str) -> str:
    lines = text.splitlines()
    declaration_index = next((index for index, line in enumerate(lines) if LEAN_DECL_KIND_RE.match(line)), None)
    if declaration_index is None:
        return text
    prefix = lines[:declaration_index]
    declaration_lines = lines[declaration_index:]
    suffix: list[str] = []
    while declaration_lines and declaration_lines[-1].strip() == "end":
        suffix.insert(0, declaration_lines.pop())
    declaration_text = "\n".join(declaration_lines).strip()
    declared_name = declaration_name_from_text(declaration_text)
    kinds = set(LEAN_DECL_KIND_RE.findall(declaration_text))
    if kinds & {"theorem", "lemma", "def", "abbrev"}:
        assumed_text = declaration_signature_assumption(declaration_text)
        if assumed_text:
            declaration_text = assumed_text
    block_lines = [*prefix, declaration_text, *suffix]
    block = "\n".join(line for line in block_lines if line.strip()).strip()
    namespace = wrapper_namespace(declaration_name, declared_name)
    if namespace:
        block = f"namespace {namespace}\n{block}\nend {namespace}"
    return block


def visible_support_candidates_for_unit(
    unit_payload: dict[str, Any], *, assumption_mode: bool = False, project_root: Path | None = None
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    variables_by_path: dict[str, list[str]] = {}
    for item in iter_dicts(unit_payload):
        variable = explicit_variable_statement(item)
        if variable:
            path = str(item.get("path") or "")
            if path:
                variables_by_path.setdefault(path, []).append(variable)
            continue
        snippet = item.get("lean_snippet")
        if isinstance(snippet, str):
            cleaned = trim_support_snippet(strip_lean_comments(snippet))
            is_usable = support_snippet_is_assumable(cleaned) if assumption_mode else support_snippet_is_complete(cleaned)
            if is_usable:
                path = str(item.get("path") or "")
                raw_line = item.get("line") or ""
                if not raw_line and isinstance(item.get("line_range"), list) and item["line_range"]:
                    raw_line = item["line_range"][0]
                line = str(raw_line or "")
                name = str(item.get("full_name") or item.get("name") or "")
                name = resolve_source_declaration_name(
                    name,
                    project_root=project_root,
                    path_text=path,
                    line_text=line,
                )
                text = support_snippet_block(cleaned, variables_by_path.get(path, []))
                if assumption_mode:
                    text = support_assumption_text(text, name)
                candidates.append(
                    {
                        "kind": str(item.get("kind") or "lean_snippet"),
                        "name": name,
                        "path": path,
                        "line": line,
                        "text": text,
                    }
                )
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for candidate in candidates:
        text = candidate["text"]
        if text not in seen:
            unique.append(candidate)
            seen.add(text)
    return sorted(unique, key=support_candidate_sort_key)


def support_snippet_block(snippet: str, variables: list[str]) -> str:
    scoped_variables = unique_in_order(variables)
    if not scoped_variables:
        return snippet
    return "\n".join(["section", *scoped_variables, snippet, "end"])


def user_payload_from_generation_payload(output_path: Path) -> dict[str, Any]:
    payload_path = output_path.with_name("generation-payload.json")
    if not payload_path.exists():
        return {}
    payload = read_json(payload_path)
    messages = payload.get("messages") or []
    user_message = next((message for message in messages if message.get("role") == "user"), None)
    if not user_message:
        return {}
    try:
        user_payload = json.loads(str(user_message.get("content") or ""))
    except json.JSONDecodeError:
        return {}
    return user_payload if isinstance(user_payload, dict) else {}


def generation_prompt_units(user_payload: dict[str, Any]) -> list[dict[str, Any]]:
    units = user_payload.get("units")
    if isinstance(units, list):
        return [unit for unit in units if isinstance(unit, dict)]
    proof_lane_tasks = user_payload.get("proof_lane_tasks")
    if isinstance(proof_lane_tasks, list):
        return [unit for unit in proof_lane_tasks if isinstance(unit, dict)]
    original_task = user_payload.get("original_generation_task")
    if isinstance(original_task, dict) and isinstance(original_task.get("units"), list):
        return [unit for unit in original_task["units"] if isinstance(unit, dict)]
    return []


def visible_support_candidates_by_unit(
    output_path: Path, *, assumption_mode: bool = False, project_root: Path | None = None
) -> dict[str, list[dict[str, str]]]:
    units = generation_prompt_units(user_payload_from_generation_payload(output_path))
    return {
        str(unit.get("unit_key") or ""): visible_support_candidates_for_unit(
            unit, assumption_mode=assumption_mode, project_root=project_root
        )
        for unit in units
        if unit.get("unit_key")
    }


def payload_context(output_path: Path) -> dict[str, list[str]]:
    user_payload = user_payload_from_generation_payload(output_path)
    if not user_payload:
        return {"imports": [], "opens": []}

    imports: list[str] = []
    opens: list[str] = []
    for item in iter_dicts(user_payload):
        module = str(item.get("module") or "")
        if module and LEAN_DOTTED_NAME_RE.fullmatch(module):
            imports.append(module)
        for imported in item.get("imports") or []:
            imported_text = str(imported)
            if imported_text and LEAN_DOTTED_NAME_RE.fullmatch(imported_text):
                imports.append(imported_text)
        open_statement = explicit_open_statement(item)
        if open_statement:
            opens.append(open_statement)
    return {
        "imports": unique_in_order(imports),
        "opens": unique_in_order(opens),
    }


def build_lean_source(
    body: str, *, imports: list[str], opens: list[str], support_context: list[str] | None = None
) -> str:
    lines = [f"import {name}" for name in imports]
    lines.extend(opens)
    if support_context:
        lines.extend(item.rstrip() for item in support_context if item.strip())
        lines.extend(support_namespace_closers(support_context))
    lines.append(body.rstrip())
    return "\n".join(lines) + "\n"


def lean_errors(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [message for message in result["messages"] if message.get("severity") == "error"]


def open_trial_source_and_ranges(
    open_statements: list[str],
    *,
    imports: list[str],
    base_opens: list[str],
    accepted_opens: list[str],
) -> tuple[str, dict[str, tuple[int, int]]]:
    lines = [f"import {name}" for name in imports]
    lines.extend(base_opens)
    lines.extend(accepted_opens)
    ranges: dict[str, tuple[int, int]] = {}
    for statement in open_statements:
        start_line = len(lines) + 1
        lines.append(statement)
        ranges[statement] = (start_line, start_line)
    lines.append("")
    return "\n".join(lines) + "\n", ranges


def validate_open_statements_sequential(
    open_statements: list[str],
    *,
    project_root: Path,
    imports: list[str],
    base_opens: list[str],
    timeout_seconds: float,
) -> dict[str, Any]:
    accepted: list[str] = []
    rejected: list[dict[str, Any]] = []
    lean_call_count = 0
    elapsed_seconds = 0.0
    for statement in open_statements:
        trial_opens = [*base_opens, *accepted, statement]
        result = run_lean_source(
            build_lean_source("", imports=imports, opens=trial_opens),
            project_root=project_root,
            timeout_seconds=timeout_seconds,
        )
        lean_call_count += 1
        elapsed_seconds += float(result.get("elapsed_seconds") or 0.0)
        errors = lean_errors(result)
        if result["returncode"] == 0 and not errors:
            accepted.append(statement)
            continue
        rejected.append(
            {
                "open_statement": statement,
                "lean_returncode": result["returncode"],
                "lean_error_count": len(errors),
                "messages": result["messages"][:5],
                "stderr": result["stderr"],
                "elapsed_seconds": result.get("elapsed_seconds"),
            }
        )
    return {
        "accepted": accepted,
        "rejected": rejected,
        "lean_call_count": lean_call_count,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "validation_strategy": "sequential",
    }


def validate_open_statements(
    open_statements: list[str],
    *,
    project_root: Path,
    imports: list[str],
    base_opens: list[str],
    timeout_seconds: float,
) -> dict[str, Any]:
    accepted: list[str] = []
    pending = list(open_statements)
    rejected_by_statement: dict[str, dict[str, Any]] = {}
    lean_call_count = 0
    elapsed_seconds = 0.0
    while pending:
        source, ranges = open_trial_source_and_ranges(
            pending,
            imports=imports,
            base_opens=base_opens,
            accepted_opens=accepted,
        )
        result = run_lean_source(source, project_root=project_root, timeout_seconds=timeout_seconds)
        lean_call_count += 1
        elapsed_seconds += float(result.get("elapsed_seconds") or 0.0)
        errors = [message for message in result["messages"] if message.get("severity") == "error"]
        if result["returncode"] != 0 and (not errors or errors_outside_ranges(result["messages"], ranges)):
            fallback = validate_open_statements_sequential(
                open_statements,
                project_root=project_root,
                imports=imports,
                base_opens=base_opens,
                timeout_seconds=timeout_seconds,
            )
            fallback["lean_call_count"] = int(fallback.get("lean_call_count") or 0) + lean_call_count
            fallback["elapsed_seconds"] = round(
                float(fallback.get("elapsed_seconds") or 0.0) + elapsed_seconds,
                3,
            )
            fallback["validation_strategy"] = "sequential_fallback"
            return fallback
        if result["returncode"] == 0 and not errors:
            accepted.extend(pending)
            pending = []
            break

        next_pending: list[str] = []
        progress = False
        for statement in pending:
            start_line, end_line = ranges[statement]
            statement_errors = [
                message
                for message in messages_in_line_range(result["messages"], start_line, end_line)
                if message.get("severity") == "error"
            ]
            if not statement_errors:
                accepted.append(statement)
                progress = True
                continue
            rejected_by_statement[statement] = {
                "open_statement": statement,
                "lean_returncode": result["returncode"],
                "lean_error_count": len(statement_errors),
                "messages": statement_errors[:5],
                "stderr": result["stderr"],
                "elapsed_seconds": result.get("elapsed_seconds"),
            }
            next_pending.append(statement)
        if not progress:
            break
        pending = next_pending
    rejected = [rejected_by_statement[statement] for statement in pending if statement in rejected_by_statement]
    return {
        "accepted": accepted,
        "rejected": rejected,
        "lean_call_count": lean_call_count,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "validation_strategy": "batched",
    }


def declared_names_in_body(body: str) -> list[str]:
    return unique_in_order([match.group(1) for match in LEAN_DECL_RE.finditer(body)])


def parse_lean_json(stdout: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        messages.append(
            {
                "severity": payload.get("severity"),
                "kind": payload.get("kind"),
                "data": payload.get("data"),
                "line": payload.get("pos", {}).get("line"),
                "column": payload.get("pos", {}).get("column"),
            }
        )
    return messages


def run_lean_source(
    source: str,
    *,
    project_root: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    command = ["lake", "env", "lean", "--stdin", "--json"]
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=project_root,
            input=source,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed_seconds = round(time.monotonic() - started, 3)
        stdout = (
            exc.stdout.decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        timeout_message = f"Lean command timed out after {timeout_seconds} seconds"
        return {
            "returncode": 124,
            "messages": parse_lean_json(stdout),
            "stderr": f"{stderr}\n{timeout_message}".strip(),
            "elapsed_seconds": elapsed_seconds,
        }
    return {
        "returncode": result.returncode,
        "messages": parse_lean_json(result.stdout),
        "stderr": result.stderr,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def support_trial_source_and_ranges(
    *,
    imports: list[str],
    opens: list[str],
    support_context: list[str],
    candidates: list[dict[str, str]],
) -> tuple[str, dict[str, tuple[int, int]]]:
    lines = [f"import {name}" for name in imports]
    lines.extend(opens)
    for item in support_context:
        lines.extend(item.rstrip().splitlines())
    ranges: dict[str, tuple[int, int]] = {}
    candidate_texts: list[str] = []
    for candidate in candidates:
        text = candidate["text"]
        candidate_texts.append(text)
        candidate_lines = text.rstrip().splitlines() or [""]
        start_line = len(lines) + 1
        lines.extend(candidate_lines)
        ranges[text] = (start_line, len(lines))
    lines.extend(support_namespace_closers([*support_context, *candidate_texts]))
    lines.append("")
    return "\n".join(lines) + "\n", ranges


def message_line(message: dict[str, Any]) -> int:
    try:
        return int(message.get("line") or 0)
    except (TypeError, ValueError):
        return 0


def messages_in_line_range(messages: list[dict[str, Any]], start_line: int, end_line: int) -> list[dict[str, Any]]:
    return [message for message in messages if start_line <= message_line(message) <= end_line]


def errors_outside_ranges(
    messages: list[dict[str, Any]], ranges: dict[str, tuple[int, int]]
) -> list[dict[str, Any]]:
    outside: list[dict[str, Any]] = []
    for message in messages:
        if message.get("severity") != "error":
            continue
        line = message_line(message)
        if not any(start_line <= line <= end_line for start_line, end_line in ranges.values()):
            outside.append(message)
    return outside


def materialize_visible_support_context_sequential(
    candidates: list[dict[str, str]],
    *,
    project_root: Path,
    imports: list[str],
    opens: list[str],
    timeout_seconds: float,
) -> dict[str, Any]:
    accepted: list[dict[str, str]] = []
    support_context: list[str] = []
    seen_text: set[str] = set()
    pending: list[dict[str, str]] = []
    for candidate in sorted(candidates, key=support_candidate_sort_key):
        text = candidate["text"]
        if text in seen_text:
            continue
        seen_text.add(text)
        pending.append(candidate)
    final_rejections: dict[str, dict[str, Any]] = {}
    lean_call_count = 0
    elapsed_seconds = 0.0
    while pending:
        next_pending: list[dict[str, str]] = []
        progress = False
        for candidate in pending:
            text = candidate["text"]
            trial_context = [*support_context, text]
            result = run_lean_source(
                build_lean_source("", imports=imports, opens=opens, support_context=trial_context),
                project_root=project_root,
                timeout_seconds=timeout_seconds,
            )
            lean_call_count += 1
            elapsed_seconds += float(result.get("elapsed_seconds") or 0.0)
            errors = [message for message in result["messages"] if message.get("severity") == "error"]
            if result["returncode"] == 0 and not errors:
                support_context.append(text)
                accepted.append({key: value for key, value in candidate.items() if key != "text"})
                progress = True
            else:
                final_rejections[text] = {
                    **{key: value for key, value in candidate.items() if key != "text"},
                    "lean_returncode": result["returncode"],
                    "lean_error_count": len(errors),
                    "messages": result["messages"][:5],
                    "stderr": result["stderr"],
                    "elapsed_seconds": result.get("elapsed_seconds"),
                }
                next_pending.append(candidate)
        if not progress:
            break
        pending = next_pending
    rejected = [final_rejections[candidate["text"]] for candidate in pending if candidate["text"] in final_rejections]
    return {
        "support_context": support_context,
        "accepted": accepted,
        "rejected": rejected,
        "candidate_count": len(candidates),
        "lean_call_count": lean_call_count,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "materialization_strategy": "sequential",
    }


def materialize_visible_support_context(
    candidates: list[dict[str, str]],
    *,
    project_root: Path,
    imports: list[str],
    opens: list[str],
    timeout_seconds: float,
) -> dict[str, Any]:
    accepted: list[dict[str, str]] = []
    support_context: list[str] = []
    seen_text: set[str] = set()
    pending: list[dict[str, str]] = []
    for candidate in sorted(candidates, key=support_candidate_sort_key):
        text = candidate["text"]
        if text in seen_text:
            continue
        seen_text.add(text)
        pending.append(candidate)
    final_rejections: dict[str, dict[str, Any]] = {}
    lean_call_count = 0
    elapsed_seconds = 0.0
    while pending:
        source, ranges = support_trial_source_and_ranges(
            imports=imports,
            opens=opens,
            support_context=support_context,
            candidates=pending,
        )
        result = run_lean_source(source, project_root=project_root, timeout_seconds=timeout_seconds)
        lean_call_count += 1
        elapsed_seconds += float(result.get("elapsed_seconds") or 0.0)
        errors = [message for message in result["messages"] if message.get("severity") == "error"]
        if result["returncode"] != 0 and (not errors or errors_outside_ranges(result["messages"], ranges)):
            fallback = materialize_visible_support_context_sequential(
                candidates,
                project_root=project_root,
                imports=imports,
                opens=opens,
                timeout_seconds=timeout_seconds,
            )
            fallback["lean_call_count"] = int(fallback.get("lean_call_count") or 0) + lean_call_count
            fallback["elapsed_seconds"] = round(
                float(fallback.get("elapsed_seconds") or 0.0) + elapsed_seconds,
                3,
            )
            fallback["materialization_strategy"] = "sequential_fallback"
            return fallback
        if result["returncode"] == 0 and not errors:
            for candidate in pending:
                support_context.append(candidate["text"])
                accepted.append({key: value for key, value in candidate.items() if key != "text"})
            pending = []
            break

        next_pending: list[dict[str, str]] = []
        progress = False
        for candidate in pending:
            text = candidate["text"]
            start_line, end_line = ranges[text]
            candidate_errors = [
                message
                for message in messages_in_line_range(result["messages"], start_line, end_line)
                if message.get("severity") == "error"
            ]
            if not candidate_errors:
                support_context.append(text)
                accepted.append({key: value for key, value in candidate.items() if key != "text"})
                progress = True
                continue
            final_rejections[text] = {
                **{key: value for key, value in candidate.items() if key != "text"},
                "lean_returncode": result["returncode"],
                "lean_error_count": len(candidate_errors),
                "messages": candidate_errors[:5],
                "stderr": result["stderr"],
                "elapsed_seconds": result.get("elapsed_seconds"),
            }
            next_pending.append(candidate)
        if not progress:
            break
        pending = next_pending
    rejected = [final_rejections[candidate["text"]] for candidate in pending if candidate["text"] in final_rejections]
    return {
        "support_context": support_context,
        "accepted": accepted,
        "rejected": rejected,
        "candidate_count": len(candidates),
        "lean_call_count": lean_call_count,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "materialization_strategy": "batched",
    }


def available_support_candidate_names_audit(
    candidates: list[dict[str, str]],
    *,
    project_root: Path,
    imports: list[str],
    opens: list[str],
    timeout_seconds: float,
) -> dict[str, Any]:
    names = unique_in_order(
        [
            str(candidate.get("name") or "")
            for candidate in candidates
            if LEAN_NAME_RE.fullmatch(str(candidate.get("name") or ""))
        ]
    )
    if not names:
        return {"availability": {}, "lean_call_count": 0, "elapsed_seconds": 0.0}
    body_lines: list[str] = []
    name_lines: dict[str, int] = {}
    line_offset = len(imports) + len(opens)
    for name in names:
        body_lines.append(f"#check {name}")
        name_lines[name] = line_offset + len(body_lines)
    result = run_lean_source(
        build_lean_source("\n".join(body_lines), imports=imports, opens=opens),
        project_root=project_root,
        timeout_seconds=timeout_seconds,
    )
    base_line_errors = [
        message
        for message in result["messages"]
        if message.get("severity") == "error" and int(message.get("line") or 0) <= line_offset
    ]
    if base_line_errors:
        availability = {name: False for name in names}
        return {
            "availability": availability,
            "lean_call_count": 1,
            "elapsed_seconds": result.get("elapsed_seconds") or 0.0,
        }
    error_lines = {
        int(message.get("line") or 0)
        for message in result["messages"]
        if message.get("severity") == "error"
    }
    availability = {name: name_lines[name] not in error_lines for name in names}
    return {
        "availability": availability,
        "lean_call_count": 1,
        "elapsed_seconds": result.get("elapsed_seconds") or 0.0,
    }


def available_support_candidate_names(
    candidates: list[dict[str, str]],
    *,
    project_root: Path,
    imports: list[str],
    opens: list[str],
    timeout_seconds: float,
) -> dict[str, bool]:
    return available_support_candidate_names_audit(
        candidates,
        project_root=project_root,
        imports=imports,
        opens=opens,
        timeout_seconds=timeout_seconds,
    )["availability"]


def unique_support_candidates(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    seen_text: set[str] = set()
    seen_names: set[str] = set()
    unique: list[dict[str, str]] = []
    for candidate in sorted(candidates, key=support_candidate_sort_key):
        text = candidate["text"]
        name = str(candidate.get("name") or "")
        if text in seen_text or (name and name in seen_names):
            continue
        seen_text.add(text)
        if name:
            seen_names.add(name)
        unique.append(candidate)
    return unique


def verify_generation_output(
    output_json: dict[str, Any],
    *,
    project_root: Path,
    imports: list[str],
    opens: list[str],
    support_context_by_unit: dict[str, list[str]] | None = None,
    support_audit_by_unit: dict[str, dict[str, Any]] | None = None,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for unit in output_json.get("units") or []:
        unit_key = str(unit.get("unit_key") or "")
        body = str(unit.get("lean_file_body") or "")
        status = str(unit.get("status") or "generated")
        declaration_names = unit.get("declaration_names", [])
        body_declaration_names = declared_names_in_body(body)
        placeholders = sorted(set(PLACEHOLDER_RE.findall(body)))
        contract_violations: list[str] = []
        if status == "cannot_prove_from_visible_context" and body.strip():
            contract_violations.append("cannot_prove_output_must_have_empty_lean_file_body")
        if status == "cannot_prove_from_visible_context" and declaration_names:
            contract_violations.append("cannot_prove_output_must_have_empty_declaration_names")
        if status == "generated" and not body.strip():
            contract_violations.append("generated_output_must_have_nonempty_lean_file_body")
        if placeholders:
            contract_violations.append("generated_lean_contains_placeholder")
        if status == "generated" and LEAN_COMMENT_RE.search(body):
            contract_violations.append("generated_lean_must_not_include_comments")
        reported_local_names = [local_declaration_name(str(name)) for name in declaration_names]
        if status == "generated" and sorted(reported_local_names) != sorted(body_declaration_names):
            contract_violations.append("declaration_names_must_match_lean_file_body_declarations")

        if status == "cannot_prove_from_visible_context" and not body.strip():
            lean_result = {"returncode": None, "messages": [], "stderr": "", "skipped_reason": status}
        else:
            source = build_lean_source(
                body,
                imports=imports,
                opens=opens,
                support_context=(support_context_by_unit or {}).get(unit_key, []),
            )
            lean_result = run_lean_source(source, project_root=project_root, timeout_seconds=timeout_seconds)
        errors = lean_errors(lean_result)
        compile_passed = (
            status == "generated"
            and lean_result["returncode"] == 0
            and not placeholders
            and not contract_violations
        )
        row = {
            "unit_key": unit.get("unit_key"),
            "reported_status": status,
            "declaration_names": declaration_names,
            "body_declaration_names": body_declaration_names,
            "placeholder_tokens": placeholders,
            "contract_violations": contract_violations,
            "lean_returncode": lean_result["returncode"],
            "lean_error_count": len(errors),
            "lean_elapsed_seconds": lean_result.get("elapsed_seconds"),
            "compile_passed": compile_passed,
            "messages": lean_result["messages"],
            "stderr": lean_result["stderr"],
            "skipped_reason": lean_result.get("skipped_reason"),
            "visible_support_context": (support_audit_by_unit or {}).get(unit_key),
        }
        row["failure_class"] = verification_failure_class(row)
        rows.append(row)
    return rows


def verification_failure_class(unit: dict[str, Any]) -> str:
    if unit.get("compile_passed"):
        return "compiled"
    if unit.get("contract_violations"):
        return "contract_violation"
    if unit.get("skipped_reason") == "cannot_prove_from_visible_context":
        return "declined_cannot_prove"
    if unit.get("lean_returncode") is None:
        return "not_checked"
    return "compile_failure"


def failure_class_counts(units: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for unit in units:
        failure_class = str(unit.get("failure_class") or "unclassified")
        counts[failure_class] = counts.get(failure_class, 0) + 1
    return dict(sorted(counts.items()))


def support_audit_lean_call_count(support_audit_by_unit: dict[str, dict[str, Any]]) -> int:
    return sum(int(audit.get("lean_call_count") or 0) for audit in support_audit_by_unit.values())


def support_audit_elapsed_seconds(support_audit_by_unit: dict[str, dict[str, Any]]) -> float:
    return sum(float(audit.get("elapsed_seconds") or 0.0) for audit in support_audit_by_unit.values())


def unit_lean_call_count(units: list[dict[str, Any]]) -> int:
    return sum(1 for unit in units if unit.get("lean_returncode") is not None)


def unit_lean_elapsed_seconds(units: list[dict[str, Any]]) -> float:
    return sum(float(unit.get("lean_elapsed_seconds") or 0.0) for unit in units)


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_paths = generation_output_paths(args.generation_run)
    if not output_paths:
        raise FileNotFoundError(f"no generation-output.json files found under {args.generation_run}")
    filter_target_module_imports = bool(getattr(args, "filter_target_module_imports", True))
    selected_by_key = (
        selected_units_by_key(selector_run_for_generation_run(args.generation_run))
        if filter_target_module_imports
        else {}
    )
    batches: list[dict[str, Any]] = []
    for output_path in output_paths:
        output_json = read_json(output_path)
        inferred = payload_context(output_path) if args.infer_context else {"imports": [], "opens": []}
        hidden_target_modules = (
            hidden_target_modules_for_units(selected_by_key, unit_keys_in_generation_output(output_json))
            if filter_target_module_imports
            else []
        )
        hidden_target_namespaces = (
            hidden_target_namespaces_for_units(selected_by_key, unit_keys_in_generation_output(output_json))
            if filter_target_module_imports
            else []
        )
        hidden_module_set = set(hidden_target_modules)
        inferred_imports = [
            name
            for name in inferred["imports"]
            if not import_reaches_hidden_target_module(args.project_root, name, hidden_module_set)
        ]
        filtered_imports = [name for name in inferred["imports"] if name not in inferred_imports]
        hidden_namespace_set = set(hidden_target_namespaces)
        inferred_opens = [
            statement
            for statement in inferred["opens"]
            if not should_filter_open_statement(
                statement,
                hidden_namespaces=hidden_namespace_set,
                filtered_imports=filtered_imports,
                kept_imports=inferred_imports,
            )
        ]
        filtered_opens = [statement for statement in inferred["opens"] if statement not in inferred_opens]
        imports = unique_in_order([*args.imports, *inferred_imports])
        rejected_invalid_opens: list[dict[str, Any]] = []
        open_validation_stats = {"lean_call_count": 0, "elapsed_seconds": 0.0, "validation_strategy": None}
        if getattr(args, "validate_inferred_opens", True) and inferred_opens:
            open_validation = validate_open_statements(
                inferred_opens,
                project_root=args.project_root,
                imports=imports,
                base_opens=args.opens,
                timeout_seconds=getattr(args, "open_timeout_seconds", args.timeout_seconds),
            )
            inferred_opens = open_validation["accepted"]
            rejected_invalid_opens = open_validation["rejected"]
            open_validation_stats = {
                "lean_call_count": open_validation["lean_call_count"],
                "elapsed_seconds": open_validation["elapsed_seconds"],
                "validation_strategy": open_validation.get("validation_strategy"),
            }
        opens = unique_in_order([*args.opens, *inferred_opens])
        support_context_by_unit: dict[str, list[str]] = {}
        support_audit_by_unit: dict[str, dict[str, Any]] = {}
        if getattr(args, "materialize_visible_support", False):
            support_mode = str(getattr(args, "support_mode", "body") or "body")
            assumption_mode = support_mode == "assumption"
            support_candidates = visible_support_candidates_by_unit(
                output_path,
                assumption_mode=assumption_mode,
                project_root=args.project_root,
            )
            for unit_key, candidates in support_candidates.items():
                if assumption_mode:
                    sorted_candidates = unique_support_candidates(candidates)
                    availability_audit = available_support_candidate_names_audit(
                        sorted_candidates,
                        project_root=args.project_root,
                        imports=imports,
                        opens=opens,
                        timeout_seconds=getattr(args, "support_timeout_seconds", args.timeout_seconds),
                    )
                    available_names = availability_audit["availability"]
                    skipped = [
                        {
                            **{key: value for key, value in candidate.items() if key != "text"},
                            "reason": "already_available_from_imports",
                        }
                        for candidate in sorted_candidates
                        if available_names.get(str(candidate.get("name") or ""), False)
                    ]
                    accepted_candidates = [
                        candidate
                        for candidate in sorted_candidates
                        if not available_names.get(str(candidate.get("name") or ""), False)
                    ]
                    support = materialize_visible_support_context(
                        accepted_candidates,
                        project_root=args.project_root,
                        imports=imports,
                        opens=opens,
                        timeout_seconds=getattr(args, "support_timeout_seconds", args.timeout_seconds),
                    )
                    support_context_by_unit[unit_key] = support["support_context"]
                    support_audit_by_unit[unit_key] = {
                        "candidate_count": len(sorted_candidates),
                        "accepted_count": len(support["accepted"]),
                        "rejected_count": len(support["rejected"]),
                        "skipped_count": len(skipped),
                        "lean_call_count": int(availability_audit["lean_call_count"])
                        + int(support["lean_call_count"]),
                        "elapsed_seconds": round(
                            float(availability_audit["elapsed_seconds"])
                            + float(support["elapsed_seconds"]),
                            3,
                        ),
                        "availability_lean_call_count": availability_audit["lean_call_count"],
                        "availability_elapsed_seconds": availability_audit["elapsed_seconds"],
                        "materialization_lean_call_count": support["lean_call_count"],
                        "materialization_elapsed_seconds": support["elapsed_seconds"],
                        "materialization_strategy": support.get("materialization_strategy"),
                        "support_mode": support_mode,
                        "accepted": support["accepted"],
                        "skipped": skipped,
                        "rejected": support["rejected"],
                    }
                    continue
                support = materialize_visible_support_context(
                    candidates,
                    project_root=args.project_root,
                    imports=imports,
                    opens=opens,
                    timeout_seconds=getattr(args, "support_timeout_seconds", args.timeout_seconds),
                )
                support_context_by_unit[unit_key] = support["support_context"]
                support_audit_by_unit[unit_key] = {
                    "candidate_count": support["candidate_count"],
                    "accepted_count": len(support["accepted"]),
                    "rejected_count": len(support["rejected"]),
                    "skipped_count": 0,
                    "lean_call_count": support["lean_call_count"],
                    "elapsed_seconds": support["elapsed_seconds"],
                    "materialization_lean_call_count": support["lean_call_count"],
                    "materialization_elapsed_seconds": support["elapsed_seconds"],
                    "materialization_strategy": support.get("materialization_strategy"),
                    "support_mode": support_mode,
                    "accepted": support["accepted"],
                    "skipped": [],
                    "rejected": support["rejected"],
                }
        units = verify_generation_output(
            output_json,
            project_root=args.project_root,
            imports=imports,
            opens=opens,
            support_context_by_unit=support_context_by_unit,
            support_audit_by_unit=support_audit_by_unit,
            timeout_seconds=args.timeout_seconds,
        )
        batches.append(
            {
                "generation_output": str(output_path),
                "imports": imports,
                "opens": opens,
                "inferred_imports": inferred_imports,
                "unfiltered_inferred_imports": inferred["imports"],
                "hidden_target_modules": hidden_target_modules,
                "filtered_target_module_imports": filtered_imports,
                "inferred_opens": inferred_opens,
                "unfiltered_inferred_opens": inferred["opens"],
                "hidden_target_namespaces": hidden_target_namespaces,
                "filtered_target_namespace_opens": filtered_opens,
                "filtered_invalid_inferred_opens": rejected_invalid_opens,
                "open_validation_stats": open_validation_stats,
                "materialize_visible_support": bool(getattr(args, "materialize_visible_support", False)),
                "support_mode": str(getattr(args, "support_mode", "body") or "body"),
                "units": units,
                "compile_passed_units": sum(1 for unit in units if unit["compile_passed"]),
                "failure_class_counts": failure_class_counts(units),
                "unit_count": len(units),
                "lean_call_count": (
                    int(open_validation_stats["lean_call_count"])
                    + support_audit_lean_call_count(support_audit_by_unit)
                    + unit_lean_call_count(units)
                ),
                "lean_elapsed_seconds": round(
                    float(open_validation_stats["elapsed_seconds"])
                    + support_audit_elapsed_seconds(support_audit_by_unit)
                    + unit_lean_elapsed_seconds(units),
                    3,
                ),
            }
        )
    summary = {
        "schema_version": "repoprover.latex_statement_generation_verification.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generation_run": str(args.generation_run),
        "project_root": str(args.project_root),
        "base_imports": args.imports,
        "base_opens": args.opens,
        "infer_context": args.infer_context,
        "filter_target_module_imports": filter_target_module_imports,
        "validate_inferred_opens": bool(getattr(args, "validate_inferred_opens", True)),
        "materialize_visible_support": bool(getattr(args, "materialize_visible_support", False)),
        "support_mode": str(getattr(args, "support_mode", "body") or "body"),
        "batches": batches,
        "compile_passed_units": sum(batch["compile_passed_units"] for batch in batches),
        "failure_class_counts": failure_class_counts(
            [unit for batch in batches for unit in batch["units"]]
        ),
        "unit_count": sum(batch["unit_count"] for batch in batches),
        "lean_call_count": sum(int(batch.get("lean_call_count") or 0) for batch in batches),
        "lean_elapsed_seconds": round(
            sum(float(batch.get("lean_elapsed_seconds") or 0.0) for batch in batches),
            3,
        ),
    }
    write_json(args.output, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation-run", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--imports", nargs="+", default=DEFAULT_IMPORTS)
    parser.add_argument("--opens", nargs="*", default=DEFAULT_OPENS)
    parser.add_argument(
        "--no-infer-context",
        dest="infer_context",
        action="store_false",
        help="Disable imports/opens inferred from generation-payload project context.",
    )
    parser.set_defaults(infer_context=True)
    parser.add_argument(
        "--allow-target-module-imports",
        dest="filter_target_module_imports",
        action="store_false",
        help=(
            "Do not remove inferred imports for modules containing hidden aligned target declarations. "
            "Default keeps generated-only verification target-blind."
        ),
    )
    parser.set_defaults(filter_target_module_imports=True)
    parser.add_argument(
        "--no-validate-inferred-opens",
        dest="validate_inferred_opens",
        action="store_false",
        help="Do not Lean-check inferred open statements before generated declaration verification.",
    )
    parser.set_defaults(validate_inferred_opens=True)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--open-timeout-seconds", type=float, default=30.0)
    parser.add_argument(
        "--materialize-visible-support",
        action="store_true",
        help=(
            "Before checking generated declarations, incrementally materialize Lean snippets "
            "that were visible in the generation prompt and compile under the target-blind import policy."
        ),
    )
    parser.add_argument("--support-timeout-seconds", type=float, default=30.0)
    parser.add_argument(
        "--support-mode",
        choices=["body", "assumption"],
        default="body",
        help=(
            "How to materialize visible prompt support. `body` incrementally Lean-checks copied snippets; "
            "`assumption` inserts statement/signature axioms and skips names already available from imports."
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
