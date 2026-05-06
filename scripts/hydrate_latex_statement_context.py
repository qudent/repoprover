#!/usr/bin/env python3
"""Hydrate theorem-level selector Mathlib requests with Lean ``#check`` output."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMPORTS = ["Mathlib"]
DEFAULT_OPENS = ["open scoped Polynomial BigOperators", "open PowerSeries Finset"]
LEAN_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*")
DECL_RE = re.compile(
    r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
    r"(?P<kind>theorem|lemma|def|abbrev|instance|class|structure|inductive)\s+"
    r"(?P<name>[^\s:\{\(\[]+)"
)
STRUCTURE_FIELD_RE = re.compile(r"^\s+(?P<name>[A-Za-z_][A-Za-z0-9_']*)\s*:")
NAMESPACE_RE = re.compile(r"^\s*namespace\s+(?P<name>[A-Za-z0-9_'. ]+)\s*$")
END_RE = re.compile(r"^\s*end(?:\s+(?P<name>[A-Za-z0-9_'.]+))?\s*$")


@dataclass(frozen=True)
class ContextRequest:
    unit_key: str
    task_id: str
    source_part: str
    request_index: int
    query: str
    expected_signature_or_shape: str
    why_needed: str
    exact_identifier: str | None


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def clean_identifier(value: str) -> str | None:
    text = value.strip().strip("`")
    if LEAN_IDENTIFIER_RE.fullmatch(text):
        return text
    return None


def split_exact_identifier_list(value: str) -> list[str]:
    parts = [part.strip().strip("`") for part in re.split(r"[,;]", value)]
    return [part for part in parts if LEAN_IDENTIFIER_RE.fullmatch(part)]


def identifier_tokens(value: str) -> list[str]:
    raw_parts = re.split(r"[^A-Za-z0-9']+", value.replace(".", "_"))
    ignored = {"theorem", "lemma", "def", "of", "the", "a", "an"}
    tokens = []
    for part in raw_parts:
        cleaned = part.strip("_").lower()
        if len(cleaned) >= 2 and cleaned not in ignored:
            tokens.append(cleaned)
    return list(dict.fromkeys(tokens))


def important_identifier_tokens(tokens: list[str]) -> list[str]:
    common_shape_tokens = {
        "eq",
        "zero",
        "one",
        "lt",
        "gt",
        "le",
        "ge",
        "iff",
        "mpr",
        "mp",
        "add",
        "sub",
        "mul",
        "pow",
        "sq",
        "succ",
        "pred",
    }
    namespace_tokens = {"mathlib", "mvpolynomial", "matrix", "finset", "nat", "int"}
    return [token for token in tokens if token not in common_shape_tokens and token not in namespace_tokens]


def query_namespace_root(query: str) -> str | None:
    identifier = clean_identifier(query)
    if not identifier or "." not in identifier:
        return None
    return identifier.split(".", 1)[0]


def query_local_tokens(query: str) -> list[str]:
    identifier = clean_identifier(query) or query
    local_name = identifier.rsplit(".", 1)[-1]
    return important_identifier_tokens(identifier_tokens(local_name))


def candidate_name_root(candidate: dict[str, Any]) -> str:
    return str(candidate.get("name") or "").split(".", 1)[0]


def candidate_local_haystack(candidate: dict[str, Any]) -> str:
    name = str(candidate.get("name") or "")
    local_name = name.rsplit(".", 1)[-1]
    return f"{local_name} {candidate.get('declaration_line') or ''}".lower()


def filter_fallback_candidates_for_query(query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    root = query_namespace_root(query)
    if root:
        candidates = [candidate for candidate in candidates if candidate_name_root(candidate) == root]
    local_tokens = query_local_tokens(query)
    if local_tokens:
        local_matches = [
            candidate
            for candidate in candidates
            if any(token in candidate_local_haystack(candidate) for token in local_tokens)
        ]
        if local_matches:
            candidates = local_matches
    return candidates


def checked_parent_identifier(identifier: str | None, checked_exact_names: set[str]) -> str | None:
    if not identifier or "." not in identifier:
        return None
    parts = identifier.split(".")
    for size in range(len(parts) - 1, 0, -1):
        parent = ".".join(parts[:size])
        if parent in checked_exact_names:
            return parent
    return None


def namespace_prefix(stack: list[str]) -> str:
    parts: list[str] = []
    for item in stack:
        parts.extend(part for part in item.split(".") if part)
    return ".".join(parts)


def namespace_end_matches(stack: list[str], end_name: str | None) -> bool:
    if not stack or not end_name:
        return False
    top = stack[-1]
    return end_name == top or end_name == top.split(".")[-1]


def fallback_mathlib_candidates(query: str, *, project_root: Path, limit: int = 8) -> list[dict[str, Any]]:
    tokens = identifier_tokens(query)
    if not tokens:
        return []
    important_tokens = important_identifier_tokens(tokens)
    mathlib_root = project_root / ".lake" / "packages" / "mathlib" / "Mathlib"
    if not mathlib_root.exists():
        return []
    candidates: list[dict[str, Any]] = []
    for path in sorted(mathlib_root.rglob("*.lean")):
        namespace_stack: list[str] = []
        rel = path.relative_to(project_root).as_posix()
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            namespace_match = NAMESPACE_RE.match(line)
            if namespace_match:
                namespace_stack.append(namespace_match.group("name"))
                continue
            end_match = END_RE.match(line)
            if end_match and namespace_end_matches(namespace_stack, end_match.group("name")):
                namespace_stack.pop()
                continue
            decl_match = DECL_RE.match(line)
            if not decl_match:
                continue
            name = decl_match.group("name")
            haystack = f"{namespace_prefix(namespace_stack)}.{name} {line}".lower()
            matched = [token for token in tokens if token in haystack]
            if not matched:
                continue
            important_matched = [token for token in important_tokens if token in haystack]
            if important_tokens and not important_matched:
                continue
            score = len(matched) + (3 * len(important_matched))
            if name.lower() in query.lower():
                score += 2
            candidates.append(
                {
                    "name": ".".join(part for part in [namespace_prefix(namespace_stack), name] if part),
                    "kind": decl_match.group("kind"),
                    "path": rel,
                    "line_number": line_number,
                    "declaration_line": line.strip(),
                    "matched_tokens": matched,
                    "score": score,
                }
            )
    candidates = filter_fallback_candidates_for_query(query, candidates)
    candidates.sort(key=lambda item: (-int(item["score"]), str(item["path"]), int(item["line_number"])))
    return candidates[:limit]


def declaration_snippet_lines(lines: list[str], *, start_line: int, end_line: int, max_lines: int = 40) -> str:
    """Return a compact source snippet for a declaration span."""

    snippet_start = max(1, start_line)
    index = snippet_start - 2
    while index >= 0:
        stripped = lines[index].strip()
        if not stripped or not (stripped.startswith("@[") or stripped.startswith("/--")):
            break
        snippet_start = index + 1
        if stripped.startswith("/--"):
            break
        index -= 1
    snippet_end = min(end_line, start_line + max_lines - 1)
    return "\n".join(lines[snippet_start - 1 : snippet_end]).rstrip()


def find_mathlib_declarations(names: list[str], *, project_root: Path) -> dict[str, dict[str, Any]]:
    """Find source declarations for fully-qualified Mathlib names.

    ``#check`` is often too terse for checked types such as structures: it says
    only that the type exists. A compact source declaration gives generators the
    real field/projection names without exposing any target project theorem.
    """

    wanted = set(names)
    if not wanted:
        return {}
    mathlib_root = project_root / ".lake" / "packages" / "mathlib" / "Mathlib"
    if not mathlib_root.exists():
        return {}

    found: dict[str, dict[str, Any]] = {}
    for path in sorted(mathlib_root.rglob("*.lean")):
        if wanted.issubset(found):
            break
        rel = path.relative_to(project_root).as_posix()
        lines = path.read_text(encoding="utf-8").splitlines()
        namespace_stack: list[str] = []
        declaration_starts: list[dict[str, Any]] = []
        for line_number, line in enumerate(lines, start=1):
            namespace_match = NAMESPACE_RE.match(line)
            if namespace_match:
                namespace_stack.append(namespace_match.group("name"))
                continue
            end_match = END_RE.match(line)
            if end_match and namespace_end_matches(namespace_stack, end_match.group("name")):
                namespace_stack.pop()
                continue
            decl_match = DECL_RE.match(line)
            if not decl_match:
                continue
            name = ".".join(part for part in [namespace_prefix(namespace_stack), decl_match.group("name")] if part)
            declaration_starts.append(
                {
                    "name": name,
                    "kind": decl_match.group("kind"),
                    "line_number": line_number,
                    "declaration_line": line.strip(),
                }
            )
        for index, declaration in enumerate(declaration_starts):
            name = str(declaration["name"])
            if name not in wanted or name in found:
                continue
            start = int(declaration["line_number"])
            end = (
                int(declaration_starts[index + 1]["line_number"]) - 1
                if index + 1 < len(declaration_starts)
                else len(lines)
            )
            snippet = declaration_snippet_lines(lines, start_line=start, end_line=end)
            found[name] = {
                **declaration,
                "path": rel,
                "source_snippet": snippet[:3000],
                "source_snippet_truncated": (end - start + 1) > 40 or len(snippet) > 3000,
            }
    return found


def structure_field_names(source_snippet: str) -> list[str]:
    fields: list[str] = []
    for line in source_snippet.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("/-") or stripped.startswith("--"):
            continue
        if stripped.startswith(("namespace ", "deriving ", "where")):
            continue
        match = STRUCTURE_FIELD_RE.match(line)
        if match:
            fields.append(match.group("name"))
    return list(dict.fromkeys(fields))


def related_names_for_declaration(name: str, declaration: dict[str, Any], *, limit: int = 8) -> list[str]:
    kind = str(declaration.get("kind") or "")
    if kind not in {"structure", "class"}:
        return []
    fields = [f"{name}.{field}" for field in structure_field_names(str(declaration.get("source_snippet") or ""))]
    support = [f"{name}.ext", f"{name}.ext_iff"]
    return list(dict.fromkeys(fields + support))[:limit]


def request_from_item(
    *,
    unit_key: str,
    task_id: str,
    source_part: str,
    request_index: int,
    item: Any,
) -> ContextRequest:
    if isinstance(item, dict):
        query = str(item.get("name_or_query") or item.get("name") or item.get("query") or "").strip()
        expected = str(item.get("expected_signature_or_shape") or "").strip()
        why = str(item.get("why_needed") or "").strip()
    else:
        query = str(item).strip()
        expected = ""
        why = ""
    return ContextRequest(
        unit_key=unit_key,
        task_id=task_id,
        source_part=source_part,
        request_index=request_index,
        query=query,
        expected_signature_or_shape=expected,
        why_needed=why,
        exact_identifier=clean_identifier(query),
    )


def iter_mathlib_requests(model_json: dict[str, Any]) -> list[ContextRequest]:
    requests: list[ContextRequest] = []
    for unit in model_json.get("units") or []:
        unit_key = str(unit.get("unit_key") or "")
        for task in unit.get("planned_declarations") or []:
            task_id = str(task.get("task_id") or "")
            source_part = str(task.get("source_part") or "")
            for index, item in enumerate(task.get("needed_mathlib_context") or [], start=1):
                request = request_from_item(
                    unit_key=unit_key,
                    task_id=task_id,
                    source_part=source_part,
                    request_index=index,
                    item=item,
                )
                split_identifiers = split_exact_identifier_list(request.query) if request.exact_identifier is None else []
                if split_identifiers and len(split_identifiers) > 1:
                    for split_index, identifier in enumerate(split_identifiers, start=1):
                        requests.append(
                            ContextRequest(
                                unit_key=request.unit_key,
                                task_id=request.task_id,
                                source_part=request.source_part,
                                request_index=(request.request_index * 100) + split_index,
                                query=identifier,
                                expected_signature_or_shape=request.expected_signature_or_shape,
                                why_needed=request.why_needed,
                                exact_identifier=identifier,
                            )
                        )
                elif request.query:
                    requests.append(request)
    return requests


def build_check_source(names: list[str], *, imports: list[str], opens: list[str]) -> tuple[str, dict[int, str]]:
    lines: list[str] = [f"import {name}" for name in imports]
    lines.extend(opens)
    line_to_name: dict[int, str] = {}
    for name in names:
        lines.append(f"#check {name}")
        line_to_name[len(lines)] = name
    return "\n".join(lines) + "\n", line_to_name


def parse_lean_json(stdout: str, line_to_name: dict[int, str]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {
        name: {"status": "missing_message", "messages": []} for name in line_to_name.values()
    }
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        line_number = int(payload.get("pos", {}).get("line") or 0)
        name = line_to_name.get(line_number)
        if name is None:
            continue
        message = {
            "severity": payload.get("severity"),
            "data": payload.get("data"),
            "line": line_number,
        }
        current = results[name]
        current.setdefault("messages", []).append(message)
        if payload.get("severity") == "information":
            current["status"] = "checked"
            current["signature"] = payload.get("data")
        elif current.get("status") != "checked":
            current["status"] = "error"
            current["error"] = payload.get("data")
    return results


def lean_check_names(
    names: list[str],
    *,
    project_root: Path,
    imports: list[str],
    opens: list[str],
    timeout_seconds: float,
) -> dict[str, Any]:
    unique_names = list(dict.fromkeys(names))
    source, line_to_name = build_check_source(unique_names, imports=imports, opens=opens)
    if not unique_names:
        return {
            "status": "no_exact_identifiers",
            "checked": {},
            "lean_source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        }
    cmd = ["lake", "env", "lean", "--stdin", "--json"]
    result = subprocess.run(
        cmd,
        cwd=project_root,
        input=source,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "status": "ok" if result.returncode == 0 else "lean_errors",
        "command": cmd,
        "returncode": result.returncode,
        "stderr": result.stderr,
        "checked": parse_lean_json(result.stdout, line_to_name),
        "lean_source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
    }


def hydrate_output(
    model_json: dict[str, Any],
    *,
    project_root: Path,
    imports: list[str],
    opens: list[str],
    timeout_seconds: float,
) -> dict[str, Any]:
    requests = iter_mathlib_requests(model_json)
    exact_names = [request.exact_identifier for request in requests if request.exact_identifier]
    check = lean_check_names(
        [name for name in exact_names if name],
        project_root=project_root,
        imports=imports,
        opens=opens,
        timeout_seconds=timeout_seconds,
    )
    checked = check.get("checked", {})
    request_fallbacks: dict[int, list[dict[str, Any]]] = {}
    request_fallback_suppression: dict[int, dict[str, Any]] = {}
    fallback_names: list[str] = []
    checked_exact_name_set = {
        name for name in exact_names if name and (checked.get(name, {}) or {}).get("status") == "checked"
    }
    for request in requests:
        check_result = checked.get(request.exact_identifier or "", {})
        if (not request.exact_identifier) or check_result.get("status") != "checked":
            fallback_candidates = fallback_mathlib_candidates(request.query, project_root=project_root)
            parent = checked_parent_identifier(request.exact_identifier, checked_exact_name_set)
            if parent:
                scoped_candidates = [
                    candidate
                    for candidate in fallback_candidates
                    if str(candidate.get("name") or "").startswith(f"{parent}.")
                ]
                if len(scoped_candidates) != len(fallback_candidates):
                    request_fallback_suppression[id(request)] = {
                        "policy": "failed_member_request_scoped_to_checked_parent",
                        "checked_parent": parent,
                        "removed_candidate_count": len(fallback_candidates) - len(scoped_candidates),
                    }
                fallback_candidates = scoped_candidates
            request_fallbacks[id(request)] = fallback_candidates
            fallback_names.extend(str(candidate["name"]) for candidate in fallback_candidates if candidate.get("name"))

    fallback_check = lean_check_names(
        fallback_names,
        project_root=project_root,
        imports=imports,
        opens=opens,
        timeout_seconds=timeout_seconds,
    )
    fallback_checked = fallback_check.get("checked", {})
    exact_source_declarations = find_mathlib_declarations(
        [name for name in exact_names if name and (checked.get(name, {}) or {}).get("status") == "checked"],
        project_root=project_root,
    )
    related_names_by_exact: dict[str, list[str]] = {}
    related_names: list[str] = []
    for name, declaration in exact_source_declarations.items():
        names = related_names_for_declaration(name, declaration)
        related_names_by_exact[name] = names
        related_names.extend(names)

    related_check = lean_check_names(
        related_names,
        project_root=project_root,
        imports=imports,
        opens=opens,
        timeout_seconds=timeout_seconds,
    )
    related_checked = related_check.get("checked", {})

    hydrated_requests: list[dict[str, Any]] = []
    for request in requests:
        check_result = checked.get(request.exact_identifier or "", {})
        fallback_candidates = []
        for candidate in request_fallbacks.get(id(request), []):
            row = dict(candidate)
            row["lean_check"] = fallback_checked.get(str(row.get("name") or ""), {"status": "missing_message"})
            fallback_candidates.append(row)
        exact_source_declaration = exact_source_declarations.get(request.exact_identifier or "")
        related_declarations = []
        for related_name in related_names_by_exact.get(request.exact_identifier or "", []):
            related_declarations.append(
                {
                    "name": related_name,
                    "relationship": "checked_projection_or_extensionality_for_selected_type",
                    "lean_check": related_checked.get(related_name, {"status": "missing_message"}),
                }
            )
        hydrated_requests.append(
            {
                "unit_key": request.unit_key,
                "task_id": request.task_id,
                "source_part": request.source_part,
                "request_index": request.request_index,
                "query": request.query,
                "expected_signature_or_shape": request.expected_signature_or_shape,
                "why_needed": request.why_needed,
                "exact_identifier": request.exact_identifier,
                "lean_check": check_result if request.exact_identifier else {"status": "not_exact_identifier"},
                "source_declaration": exact_source_declaration,
                "related_mathlib_declarations": related_declarations,
                "fallback_suppression": request_fallback_suppression.get(id(request)),
                "fallback_mathlib_candidates": fallback_candidates,
            }
        )
    return {
        "schema_version": "repoprover.latex_statement_context_hydration.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(project_root),
        "imports": imports,
        "opens": opens,
        "request_count": len(requests),
        "exact_identifier_count": len(set(name for name in exact_names if name)),
        "lean_check_status": check.get("status"),
        "lean_check": check,
        "fallback_exact_identifier_count": len(set(fallback_names)),
        "fallback_lean_check_status": fallback_check.get("status"),
        "fallback_lean_check": fallback_check,
        "related_exact_identifier_count": len(set(related_names)),
        "related_lean_check_status": related_check.get("status"),
        "related_lean_check": related_check,
        "hydrated_mathlib_context": hydrated_requests,
    }


def output_paths_from_run(run_dir: Path) -> list[Path]:
    if run_dir.is_file():
        return [run_dir]
    return sorted(run_dir.glob("batch-*/context-selection-output.json"))


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_paths = output_paths_from_run(args.run)
    if not output_paths:
        raise FileNotFoundError(f"no context-selection-output.json files found under {args.run}")
    summaries: list[dict[str, Any]] = []
    for output_path in output_paths:
        hydrated = hydrate_output(
            read_json(output_path),
            project_root=args.project_root,
            imports=args.imports,
            opens=args.opens,
            timeout_seconds=args.timeout_seconds,
        )
        destination = output_path.with_name("mathlib-lean-hydrated-context.json")
        write_json(destination, hydrated)
        summaries.append(
            {
                "output_path": str(output_path),
                "hydrated_path": str(destination),
                "request_count": hydrated["request_count"],
                "exact_identifier_count": hydrated["exact_identifier_count"],
                "lean_check_status": hydrated["lean_check_status"],
                "fallback_exact_identifier_count": hydrated["fallback_exact_identifier_count"],
                "fallback_lean_check_status": hydrated["fallback_lean_check_status"],
            }
        )
    summary = {
        "schema_version": "repoprover.latex_statement_context_hydration_run.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run": str(args.run),
        "batches": summaries,
    }
    if args.summary:
        write_json(args.summary, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="Run directory or one context-selection-output.json file.")
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--imports", nargs="+", default=DEFAULT_IMPORTS)
    parser.add_argument("--opens", nargs="*", default=DEFAULT_OPENS)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
