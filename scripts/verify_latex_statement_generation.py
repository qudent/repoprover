#!/usr/bin/env python3
"""Verify theorem-level generated Lean file bodies."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMPORTS = ["Mathlib"]
DEFAULT_OPENS = ["open scoped Polynomial BigOperators", "open PowerSeries Finset"]
PLACEHOLDER_RE = re.compile(r"\b(sorry|admit|aesop\?)\b")
LEAN_DOTTED_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)+$")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def maybe_namespace(name: str) -> str | None:
    if not LEAN_DOTTED_NAME_RE.fullmatch(name):
        return None
    parts = name.split(".")
    if len(parts) < 2:
        return None
    namespace = ".".join(parts[:-1])
    return namespace if namespace not in {"Mathlib"} else None


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


def payload_context(output_path: Path) -> dict[str, list[str]]:
    payload_path = output_path.with_name("generation-payload.json")
    if not payload_path.exists():
        return {"imports": [], "opens": []}
    payload = read_json(payload_path)
    messages = payload.get("messages") or []
    user_message = next((message for message in messages if message.get("role") == "user"), None)
    if not user_message:
        return {"imports": [], "opens": []}
    try:
        user_payload = json.loads(str(user_message.get("content") or ""))
    except json.JSONDecodeError:
        return {"imports": [], "opens": []}

    imports: list[str] = []
    namespaces: list[str] = []
    for item in iter_dicts(user_payload):
        module = str(item.get("module") or "")
        if module and LEAN_DOTTED_NAME_RE.fullmatch(module):
            imports.append(module)
        for imported in item.get("imports") or []:
            imported_text = str(imported)
            if imported_text and LEAN_DOTTED_NAME_RE.fullmatch(imported_text):
                imports.append(imported_text)
        if str(item.get("kind") or "") == "namespace":
            namespace = str(item.get("name") or "")
            if namespace and LEAN_DOTTED_NAME_RE.fullmatch(namespace):
                namespaces.append(namespace)
        name = str(item.get("name") or "")
        namespace = maybe_namespace(name)
        if namespace:
            namespaces.append(namespace)
    return {
        "imports": unique_in_order(imports),
        "opens": [f"open {namespace}" for namespace in unique_in_order(namespaces)],
    }


def build_lean_source(body: str, *, imports: list[str], opens: list[str]) -> str:
    lines = [f"import {name}" for name in imports]
    lines.extend(opens)
    lines.append(body.rstrip())
    return "\n".join(lines) + "\n"


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
    result = subprocess.run(
        ["lake", "env", "lean", "--stdin", "--json"],
        cwd=project_root,
        input=source,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "returncode": result.returncode,
        "messages": parse_lean_json(result.stdout),
        "stderr": result.stderr,
    }


def verify_generation_output(
    output_json: dict[str, Any],
    *,
    project_root: Path,
    imports: list[str],
    opens: list[str],
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for unit in output_json.get("units") or []:
        body = str(unit.get("lean_file_body") or "")
        status = str(unit.get("status") or "generated")
        placeholders = sorted(set(PLACEHOLDER_RE.findall(body)))
        contract_violations: list[str] = []
        if status == "cannot_prove_from_visible_context" and body.strip():
            contract_violations.append("cannot_prove_output_must_have_empty_lean_file_body")
        if status == "generated" and not body.strip():
            contract_violations.append("generated_output_must_have_nonempty_lean_file_body")
        if placeholders:
            contract_violations.append("generated_lean_contains_placeholder")

        if status == "cannot_prove_from_visible_context" and not body.strip():
            lean_result = {"returncode": None, "messages": [], "stderr": "", "skipped_reason": status}
        else:
            source = build_lean_source(body, imports=imports, opens=opens)
            lean_result = run_lean_source(source, project_root=project_root, timeout_seconds=timeout_seconds)
        errors = [message for message in lean_result["messages"] if message.get("severity") == "error"]
        rows.append(
            {
                "unit_key": unit.get("unit_key"),
                "reported_status": status,
                "declaration_names": unit.get("declaration_names", []),
                "placeholder_tokens": placeholders,
                "contract_violations": contract_violations,
                "lean_returncode": lean_result["returncode"],
                "lean_error_count": len(errors),
                "compile_passed": (
                    status == "generated"
                    and lean_result["returncode"] == 0
                    and not placeholders
                    and not contract_violations
                ),
                "messages": lean_result["messages"],
                "stderr": lean_result["stderr"],
                "skipped_reason": lean_result.get("skipped_reason"),
            }
        )
    return rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_paths = generation_output_paths(args.generation_run)
    if not output_paths:
        raise FileNotFoundError(f"no generation-output.json files found under {args.generation_run}")
    batches: list[dict[str, Any]] = []
    for output_path in output_paths:
        inferred = payload_context(output_path) if args.infer_context else {"imports": [], "opens": []}
        imports = unique_in_order([*args.imports, *inferred["imports"]])
        opens = unique_in_order([*args.opens, *inferred["opens"]])
        units = verify_generation_output(
            read_json(output_path),
            project_root=args.project_root,
            imports=imports,
            opens=opens,
            timeout_seconds=args.timeout_seconds,
        )
        batches.append(
            {
                "generation_output": str(output_path),
                "imports": imports,
                "opens": opens,
                "inferred_imports": inferred["imports"],
                "inferred_opens": inferred["opens"],
                "units": units,
                "compile_passed_units": sum(1 for unit in units if unit["compile_passed"]),
                "unit_count": len(units),
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
        "batches": batches,
        "compile_passed_units": sum(batch["compile_passed_units"] for batch in batches),
        "unit_count": sum(batch["unit_count"] for batch in batches),
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
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
