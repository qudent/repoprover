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
    hydrated_requests: list[dict[str, Any]] = []
    for request in requests:
        check_result = checked.get(request.exact_identifier or "", {})
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
