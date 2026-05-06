#!/usr/bin/env python3
"""Diagnose raw partial proof bodies saved by generation contract enforcement.

This script is a no-provider diagnostic lane. It inspects raw model outputs such
as ``raw-generation-output.json`` that were preserved before normalization,
checks whether their Lean bodies elaborate with visible prompt context, and
summarizes whether the blocker is a pure unfinished proof or earlier Lean
errors/context gaps.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_latex_statement_generation import write_json  # noqa: E402
import scripts.verify_latex_statement_generation as verify  # noqa: E402


RAW_OUTPUT_FILENAMES = ("raw-generation-output.json", "raw-repair-output.json")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def raw_output_paths(generation_run: Path) -> list[Path]:
    if generation_run.is_file():
        return [generation_run] if generation_run.name in RAW_OUTPUT_FILENAMES else []
    paths: list[Path] = []
    for filename in RAW_OUTPUT_FILENAMES:
        paths.extend(sorted(generation_run.glob(f"batch-*/{filename}")))
    return sorted(paths)


def prompt_units_by_key(raw_path: Path) -> dict[str, dict[str, Any]]:
    payload = verify.user_payload_from_generation_payload(raw_path)
    return {
        str(unit.get("unit_key") or ""): unit
        for unit in verify.generation_prompt_units(payload)
        if unit.get("unit_key")
    }


def load_decline_context_pack(path: Path | None) -> dict[tuple[str, str], dict[str, Any]]:
    if path is None:
        return {}
    data = read_json(path)
    packs: dict[tuple[str, str], dict[str, Any]] = {}
    for unit in data.get("units") or []:
        source_unit_id = str(unit.get("source_unit_id") or "")
        unit_key = str(unit.get("unit_key") or "")
        if source_unit_id and unit_key:
            packs[(source_unit_id, unit_key)] = unit
    return packs


def extra_support_candidates_by_unit(
    raw_path: Path, pack_path: Path | None, *, assumption_mode: bool
) -> dict[str, list[dict[str, str]]]:
    packs = load_decline_context_pack(pack_path)
    if not packs:
        return {}
    candidates: dict[str, list[dict[str, str]]] = {}
    for unit_key, unit in prompt_units_by_key(raw_path).items():
        source_unit_id = str((unit.get("source_unit") or {}).get("id") or "")
        pack = packs.get((source_unit_id, unit_key))
        if not pack:
            continue
        candidates[unit_key] = verify.visible_support_candidates_for_unit(
            {
                "unit_key": unit_key,
                "diagnostic_decline_context_pack": pack,
            },
            assumption_mode=assumption_mode,
        )
    return candidates


def source_path_to_withheld_module(path_text: str) -> str | None:
    if not path_text:
        return None
    path = Path(path_text)
    if path.suffix != ".tex":
        return None
    parts = list(path.with_suffix("").parts)
    if "AlgebraicCombinatorics" in parts:
        start = parts.index("AlgebraicCombinatorics")
        parts = parts[start:]
    if "tex" in parts:
        parts.remove("tex")
    if not parts:
        return None
    module = ".".join(parts)
    return module if verify.LEAN_DOTTED_NAME_RE.fullmatch(module) else None


def withheld_source_modules(raw_path: Path) -> list[str]:
    modules: list[str] = []
    for unit in prompt_units_by_key(raw_path).values():
        source = unit.get("source_unit") or {}
        module = source_path_to_withheld_module(str(source.get("path") or ""))
        if module:
            modules.append(module)
    return verify.unique_in_order(modules)


def compact_message(message: dict[str, Any]) -> dict[str, Any]:
    data = str(message.get("data") or "")
    if len(data) > 700:
        data = data[:697] + "..."
    return {
        "severity": message.get("severity"),
        "kind": message.get("kind"),
        "line": message.get("line"),
        "column": message.get("column"),
        "data": data,
    }


def diagnostic_class(row: dict[str, Any], body: str) -> str:
    if not body.strip():
        return "no_raw_body"
    if row.get("lean_returncode") not in (0, None) or row.get("lean_error_count"):
        return "lean_errors_before_or_at_placeholder"
    if row.get("placeholder_tokens"):
        return "lean_accepts_with_placeholder"
    if row.get("contract_violations"):
        return "contract_only_lean_accepts"
    return "raw_complete_candidate"


def materialize_support(
    *,
    raw_path: Path,
    project_root: Path,
    imports: list[str],
    opens: list[str],
    enabled: bool,
    timeout_seconds: float,
    decline_context_pack: Path | None = None,
    support_mode: str = "body",
) -> tuple[dict[str, list[str]], dict[str, dict[str, Any]]]:
    if not enabled:
        return {}, {}
    support_context_by_unit: dict[str, list[str]] = {}
    support_audit_by_unit: dict[str, dict[str, Any]] = {}
    assumption_mode = support_mode == "assumption"
    candidates_by_unit = verify.visible_support_candidates_by_unit(raw_path, assumption_mode=assumption_mode)
    for unit_key, extra_candidates in extra_support_candidates_by_unit(
        raw_path, decline_context_pack, assumption_mode=assumption_mode
    ).items():
        candidates_by_unit.setdefault(unit_key, []).extend(extra_candidates)
    for unit_key, candidates in candidates_by_unit.items():
        if assumption_mode:
            seen_text: set[str] = set()
            sorted_candidates = []
            for candidate in sorted(candidates, key=verify.support_candidate_sort_key):
                if candidate["text"] in seen_text:
                    continue
                seen_text.add(candidate["text"])
                sorted_candidates.append(candidate)
            support_context_by_unit[unit_key] = [candidate["text"] for candidate in sorted_candidates]
            support_audit_by_unit[unit_key] = {
                "candidate_count": len(sorted_candidates),
                "accepted_count": len(sorted_candidates),
                "rejected_count": 0,
                "assumption_mode": True,
                "accepted": [
                    {key: value for key, value in candidate.items() if key != "text"}
                    for candidate in sorted_candidates
                ],
                "rejected": [],
            }
            continue
        support = verify.materialize_visible_support_context(
            candidates,
            project_root=project_root,
            imports=imports,
            opens=opens,
            timeout_seconds=timeout_seconds,
        )
        support_context_by_unit[unit_key] = support["support_context"]
        support_audit_by_unit[unit_key] = {
            "candidate_count": support["candidate_count"],
            "accepted_count": len(support["accepted"]),
            "rejected_count": len(support["rejected"]),
            "accepted": support["accepted"],
            "rejected": support["rejected"],
        }
    return support_context_by_unit, support_audit_by_unit


def context_for_raw_path(args: argparse.Namespace, raw_path: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    inferred = verify.payload_context(raw_path) if args.infer_context else {"imports": [], "opens": []}
    withheld_modules = set(withheld_source_modules(raw_path)) if args.filter_source_module_imports else set()
    inferred_imports = [
        name
        for name in inferred["imports"]
        if not verify.import_reaches_hidden_target_module(args.project_root, name, withheld_modules)
    ]
    filtered_source_imports = [name for name in inferred["imports"] if name not in inferred_imports]
    imports = verify.unique_in_order([*args.imports, *inferred_imports])
    inferred_opens = [
        statement
        for statement in inferred["opens"]
        if not verify.should_filter_open_statement(
            statement,
            hidden_namespaces=withheld_modules,
            filtered_imports=filtered_source_imports,
            kept_imports=inferred_imports,
        )
    ]
    filtered_source_opens = [statement for statement in inferred["opens"] if statement not in inferred_opens]
    rejected_invalid_opens: list[dict[str, Any]] = []
    if args.validate_inferred_opens and inferred_opens:
        validation = verify.validate_open_statements(
            inferred_opens,
            project_root=args.project_root,
            imports=imports,
            base_opens=args.opens,
            timeout_seconds=args.open_timeout_seconds,
        )
        inferred_opens = validation["accepted"]
        rejected_invalid_opens = validation["rejected"]
    opens = verify.unique_in_order([*args.opens, *inferred_opens])
    return imports, opens, {
        "inferred_imports": inferred["imports"],
        "inferred_opens": inferred["opens"],
        "withheld_source_modules": sorted(withheld_modules),
        "filtered_source_module_imports": filtered_source_imports,
        "filtered_source_module_opens": filtered_source_opens,
        "accepted_inferred_imports": inferred_imports,
        "accepted_inferred_opens": inferred_opens,
        "rejected_invalid_inferred_opens": rejected_invalid_opens,
    }


def diagnose_raw_path(args: argparse.Namespace, raw_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_output = read_json(raw_path)
    prompt_units = prompt_units_by_key(raw_path)
    imports, opens, context_audit = context_for_raw_path(args, raw_path)
    support_context_by_unit, support_audit_by_unit = materialize_support(
        raw_path=raw_path,
        project_root=args.project_root,
        imports=imports,
        opens=opens,
        enabled=args.materialize_visible_support,
        timeout_seconds=args.support_timeout_seconds,
        decline_context_pack=args.decline_context_pack,
        support_mode=args.support_mode,
    )
    verification_rows = verify.verify_generation_output(
        raw_output,
        project_root=args.project_root,
        imports=imports,
        opens=opens,
        support_context_by_unit=support_context_by_unit,
        support_audit_by_unit=support_audit_by_unit,
        timeout_seconds=args.timeout_seconds,
    )
    raw_units = {str(unit.get("unit_key") or ""): unit for unit in raw_output.get("units") or []}
    allowed_keys = set(args.unit_key or [])
    diagnostics: list[dict[str, Any]] = []
    for row in verification_rows:
        unit_key = str(row.get("unit_key") or "")
        if allowed_keys and unit_key not in allowed_keys:
            continue
        raw_unit = raw_units.get(unit_key, {})
        body = str(raw_unit.get("lean_file_body") or "")
        if not body.strip() and not args.include_empty_raw_units:
            continue
        prompt_unit = prompt_units.get(unit_key, {})
        source = prompt_unit.get("source_unit") or {}
        support_audit = support_audit_by_unit.get(unit_key) or {}
        diagnostics.append(
            {
                "unit_key": unit_key,
                "source_unit_id": source.get("id"),
                "source_path": source.get("path"),
                "raw_output_path": str(raw_path),
                "status": raw_unit.get("status"),
                "declaration_names": raw_unit.get("declaration_names") or [],
                "used_context": raw_unit.get("used_context") or [],
                "notes": raw_unit.get("notes") or [],
                "diagnostic_class": diagnostic_class(row, body),
                "body_char_count": len(body),
                "placeholder_tokens": row.get("placeholder_tokens") or [],
                "contract_violations": row.get("contract_violations") or [],
                "lean_returncode": row.get("lean_returncode"),
                "lean_error_count": row.get("lean_error_count"),
                "first_messages": [compact_message(message) for message in (row.get("messages") or [])[:8]],
                "visible_support_context": {
                    "candidate_count": support_audit.get("candidate_count", 0),
                    "accepted_count": support_audit.get("accepted_count", 0),
                    "rejected_count": support_audit.get("rejected_count", 0),
                    "assumption_mode": support_audit.get("assumption_mode", False),
                    "accepted": support_audit.get("accepted", []),
                    "rejected": support_audit.get("rejected", [])[:8],
                },
            }
        )
    raw_summary = {
        "raw_output_path": str(raw_path),
        "imports": imports,
        "opens": opens,
        **context_audit,
        "raw_unit_count": len(raw_output.get("units") or []),
        "diagnosed_unit_count": len(diagnostics),
    }
    return diagnostics, raw_summary


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# Partial Proof Diagnostic Summary",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Generation runs: `{', '.join(summary['generation_runs'])}`",
        f"- Raw files: `{summary['raw_file_count']}`",
        f"- Diagnosed units: `{summary['diagnosed_unit_count']}`",
        f"- Diagnostic classes: `{summary['diagnostic_class_counts']}`",
        "",
        "Interpretation: `lean_accepts_with_placeholder` means Lean accepted the visible-context body up to placeholders such as `sorry`; `lean_errors_before_or_at_placeholder` means a repair agent first needs concrete Lean/context fixes before finishing the proof.",
        "",
        "## Units",
        "",
        "| Unit | Class | Lean errors | Placeholders | Support | Raw output |",
        "|---|---|---:|---|---:|---|",
    ]
    for unit in summary["units"]:
        support = unit["visible_support_context"]
        placeholders = ", ".join(unit["placeholder_tokens"]) or "-"
        lines.append(
            "| {unit_key} | `{klass}` | {errors} | `{placeholders}` | {accepted}/{candidates} | `{raw}` |".format(
                unit_key=unit["unit_key"],
                klass=unit["diagnostic_class"],
                errors=unit["lean_error_count"],
                placeholders=placeholders,
                accepted=support["accepted_count"],
                candidates=support["candidate_count"],
                raw=unit["raw_output_path"],
            )
        )
    for unit in summary["units"]:
        lines.extend(
            [
                "",
                f"## {unit['unit_key']}",
                "",
                f"- Source unit: `{unit.get('source_unit_id')}`",
                f"- Status: `{unit.get('status')}`",
                f"- Declaration names: `{', '.join(unit.get('declaration_names') or [])}`",
                f"- Used context: `{', '.join(unit.get('used_context') or [])}`",
                f"- Contract violations: `{', '.join(unit.get('contract_violations') or [])}`",
                f"- Visible support accepted/rejected: `{unit['visible_support_context']['accepted_count']}/{unit['visible_support_context']['rejected_count']}`",
            ]
        )
        if unit.get("notes"):
            lines.append("- Model notes:")
            lines.extend(f"  - {note}" for note in unit["notes"])
        if unit.get("first_messages"):
            lines.append("- First Lean messages:")
            for message in unit["first_messages"]:
                lines.append(
                    "  - `{severity}` line `{line}`: {data}".format(
                        severity=message.get("severity"),
                        line=message.get("line"),
                        data=str(message.get("data") or "").replace("\n", " "),
                    )
                )
    lines.append("")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    raw_paths: list[Path] = []
    for generation_run in args.generation_run:
        raw_paths.extend(raw_output_paths(generation_run))
    raw_paths = sorted(dict.fromkeys(raw_paths))
    if not raw_paths:
        raise FileNotFoundError("no raw-generation-output.json or raw-repair-output.json files found")

    units: list[dict[str, Any]] = []
    raw_summaries: list[dict[str, Any]] = []
    for raw_path in raw_paths:
        diagnostics, raw_summary = diagnose_raw_path(args, raw_path)
        units.extend(diagnostics)
        raw_summaries.append(raw_summary)

    class_counts = dict(sorted(Counter(unit["diagnostic_class"] for unit in units).items()))
    summary = {
        "schema_version": "repoprover.latex_statement_partial_proof_diagnostics.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generation_runs": [str(path) for path in args.generation_run],
        "decline_context_pack": str(args.decline_context_pack) if args.decline_context_pack else None,
        "raw_file_count": len(raw_paths),
        "diagnosed_unit_count": len(units),
        "diagnostic_class_counts": class_counts,
        "raw_files": raw_summaries,
        "units": units,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "partial-proof-diagnostics.json", summary)
    (args.output / "partial-proof-diagnostics.md").write_text(markdown_summary(summary), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation-run", type=Path, action="append", required=True)
    parser.add_argument("--decline-context-pack", type=Path)
    parser.add_argument("--unit-key", action="append")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--imports", nargs="+", default=verify.DEFAULT_IMPORTS)
    parser.add_argument("--opens", nargs="*", default=verify.DEFAULT_OPENS)
    parser.add_argument("--no-infer-context", dest="infer_context", action="store_false")
    parser.set_defaults(infer_context=True)
    parser.add_argument("--allow-source-module-imports", dest="filter_source_module_imports", action="store_false")
    parser.set_defaults(filter_source_module_imports=True)
    parser.add_argument("--no-validate-inferred-opens", dest="validate_inferred_opens", action="store_false")
    parser.set_defaults(validate_inferred_opens=True)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--open-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--no-materialize-visible-support", dest="materialize_visible_support", action="store_false")
    parser.set_defaults(materialize_visible_support=True)
    parser.add_argument("--support-mode", choices=["body", "assumption"], default="body")
    parser.add_argument("--support-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--include-empty-raw-units", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
