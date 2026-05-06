#!/usr/bin/env python3
"""Post-hoc context-gap diagnostics for theorem-level generation runs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def local_name(name: str) -> str:
    return name.removeprefix("_root_.").split(".")[-1]


def sorted_names(values: set[str]) -> list[str]:
    return sorted(value for value in values if value)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def overlap_summary(selected: set[str], gold: set[str]) -> dict[str, Any]:
    selected_local = {local_name(name) for name in selected}
    gold_local = {local_name(name) for name in gold}
    return {
        "selected_count": len(selected),
        "gold_count": len(gold),
        "exact_overlap": sorted_names(selected & gold),
        "local_name_overlap": sorted_names(selected_local & gold_local),
        "gold_missing_exact_sample": sorted_names(gold - selected)[:20],
    }


def implementation_auxiliary(name: str) -> bool:
    return (
        name.startswith("_private.")
        or "._proof_" in name
        or "._simp_" in name
        or ".match_" in name
    )


def missing_against_selected(gold: set[str], selected: set[str]) -> set[str]:
    selected_local = {local_name(name) for name in selected}
    return {
        name
        for name in gold
        if name not in selected and local_name(name) not in selected_local
    }


def load_gold_candidates(path: Path) -> dict[str, dict[str, Any]]:
    return {str(row["id"]): row for row in read_jsonl(path)}


def load_scan(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        rows[str(row["declaration"])] = row
    return rows


def user_payload_from_request(path: Path) -> dict[str, Any]:
    request = read_json(path)
    for message in request.get("messages") or []:
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {}
    return {}


def payloads_for_run(run_dir: Path) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("batch-*/generation-payload.json")):
        payload = user_payload_from_request(path)
        if payload:
            payloads.append(payload)
    return payloads


def generation_units_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("units"), list):
        return list(payload["units"])
    original = payload.get("original_generation_task")
    if isinstance(original, dict) and isinstance(original.get("units"), list):
        return list(original["units"])
    return []


def names_from_project_context(contexts: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for context in contexts:
        for declaration in context.get("project_declarations") or []:
            name = declaration.get("name")
            if name:
                names.add(str(name))
    return names


def selected_context_for_unit(run_dir: Path, unit_key: str) -> dict[str, Any]:
    mathlib_names: set[str] = set()
    project_names: set[str] = set()
    local_predecessor_names: set[str] = set()
    repair_checked_names: set[str] = set()
    visible_context_names: set[str] = set()
    source_context_refs: set[str] = set()

    for payload in payloads_for_run(run_dir):
        for unit in generation_units_from_payload(payload):
            if str(unit.get("unit_key") or "") != unit_key:
                continue
            for item in unit.get("previous_source_context") or []:
                source = item.get("source_unit") if isinstance(item, dict) else None
                source_id = source.get("id") if isinstance(source, dict) else None
                if source_id:
                    source_context_refs.add(str(source_id))
            for task in unit.get("planned_declarations") or []:
                project_names.update(names_from_project_context(task.get("available_prior_project_context") or []))
                for predecessor in task.get("local_file_predecessor_declarations") or []:
                    if predecessor.get("name"):
                        local_predecessor_names.add(str(predecessor["name"]))
                for item in task.get("hydrated_mathlib_context") or []:
                    if (item.get("lean_check") or {}).get("status") != "checked":
                        continue
                    name = item.get("exact_identifier") or item.get("name") or item.get("query")
                    if name:
                        mathlib_names.add(str(name))
                    for related in item.get("related_mathlib_declarations") or []:
                        if (related.get("lean_check") or {}).get("status") != "checked":
                            continue
                        related_name = related.get("name")
                        if related_name:
                            mathlib_names.add(str(related_name))
        for context in payload.get("additional_checked_repair_context") or []:
            for item in context.get("checked_signatures") or []:
                if str(item.get("unit_key") or "") == unit_key and item.get("name"):
                    repair_checked_names.add(str(item["name"]))
            for item in context.get("selected_visible_context") or []:
                if str(item.get("unit_key") or "") == unit_key and item.get("name_or_label"):
                    visible_context_names.add(str(item["name_or_label"]))

    return {
        "mathlib_checked_names": sorted_names(mathlib_names),
        "project_context_names": sorted_names(project_names),
        "local_predecessor_names": sorted_names(local_predecessor_names),
        "repair_checked_names": sorted_names(repair_checked_names),
        "visible_context_names": sorted_names(visible_context_names),
        "source_context_refs": sorted_names(source_context_refs),
        "all_selected_lean_names": sorted_names(
            mathlib_names | project_names | local_predecessor_names | repair_checked_names
        ),
    }


def declaration_names(declarations: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for declaration in declarations:
        name = declaration.get("full_name") or declaration.get("name")
        if name:
            names.append(str(name))
    return names


def deps_for_declarations(names: list[str], scan: dict[str, dict[str, Any]]) -> dict[str, Any]:
    mathlib: set[str] = set()
    project: set[str] = set()
    other: set[str] = set()
    missing_scan_rows: list[str] = []
    for name in names:
        row = scan.get(name)
        if row is None:
            missing_scan_rows.append(name)
            continue
        mathlib.update(str(item) for item in row.get("used_mathlib") or [])
        project.update(str(item) for item in row.get("used_project") or [])
        other.update(str(item) for item in row.get("used_other") or [])
    return {
        "mathlib": sorted_names(mathlib),
        "project": sorted_names(project),
        "other_count": len(other),
        "missing_scan_rows": sorted(missing_scan_rows),
    }


def gold_context_for_source(source_unit_id: str, gold_by_id: dict[str, dict[str, Any]], scan: dict[str, dict[str, Any]]) -> dict[str, Any]:
    gold = gold_by_id.get(source_unit_id, {})
    posthoc = gold.get("posthoc_lean_alignment") or {}
    aligned = posthoc.get("aligned_lean_declarations") or []
    referencing = posthoc.get("referencing_lean_declarations") or []
    aligned_names = declaration_names(aligned)
    referencing_names = declaration_names(referencing)
    aligned_deps = deps_for_declarations(aligned_names, scan)
    extended_deps = deps_for_declarations([*aligned_names, *referencing_names], scan)
    return {
        "aligned_declaration_names": aligned_names,
        "referencing_declaration_names": referencing_names,
        "aligned_dependency_union": aligned_deps,
        "aligned_plus_referencing_dependency_union": extended_deps,
    }


def classify_gap(*, selected: dict[str, Any], gold: dict[str, Any], source: dict[str, Any]) -> str:
    selected_names = set(selected["all_selected_lean_names"])
    gold_project = set(gold["aligned_dependency_union"]["project"])
    salient_project = {name for name in gold_project if not implementation_auxiliary(name)}
    same_source_names = set(gold["aligned_declaration_names"]) | set(gold["referencing_declaration_names"])
    missing_same_source = missing_against_selected(salient_project & same_source_names, selected_names)
    if missing_same_source:
        return "gold_uses_same_source_intermediate_declarations"
    if missing_against_selected(salient_project, selected_names):
        return "missing_project_context_against_gold_direct_deps"
    if missing_against_selected(set(gold["aligned_dependency_union"]["mathlib"]), selected_names):
        return "missing_mathlib_context_against_gold_direct_deps"
    if source.get("failure_class") == "declined_cannot_prove":
        return "generator_declined_despite_direct_dependency_overlap"
    return "no_clear_gap_from_direct_deps"


def analyze_source(source: dict[str, Any], gold_by_id: dict[str, dict[str, Any]], scan: dict[str, dict[str, Any]]) -> dict[str, Any]:
    run_dir = Path(str(source["best_run"]))
    unit_key = str(source["unit_key"])
    selected = selected_context_for_unit(run_dir, unit_key)
    gold = gold_context_for_source(str(source["source_unit_id"]), gold_by_id, scan)
    selected_mathlib = set(selected["mathlib_checked_names"]) | set(selected["repair_checked_names"])
    selected_project = set(selected["project_context_names"]) | set(selected["local_predecessor_names"])
    all_selected = set(selected["all_selected_lean_names"])
    aligned_deps = gold["aligned_dependency_union"]
    return {
        "source_unit_id": source["source_unit_id"],
        "best_run": source["best_run"],
        "unit_key": unit_key,
        "failure_class": source.get("failure_class"),
        "error_pattern": source.get("error_pattern"),
        "selected_context": {
            "mathlib_checked_count": len(selected["mathlib_checked_names"]),
            "repair_checked_count": len(selected["repair_checked_names"]),
            "project_context_count": len(selected["project_context_names"]),
            "local_predecessor_count": len(selected["local_predecessor_names"]),
            "source_context_ref_count": len(selected["source_context_refs"]),
            "mathlib_checked_names": selected["mathlib_checked_names"][:20],
            "repair_checked_names": selected["repair_checked_names"][:20],
            "project_context_names": selected["project_context_names"][:20],
            "local_predecessor_names": selected["local_predecessor_names"][:20],
        },
        "gold_context": {
            "aligned_declaration_names": gold["aligned_declaration_names"],
            "referencing_declaration_names": gold["referencing_declaration_names"],
            "aligned_mathlib_dep_count": len(aligned_deps["mathlib"]),
            "aligned_project_dep_count": len(aligned_deps["project"]),
            "aligned_salient_project_dep_count": len(
                [name for name in aligned_deps["project"] if not implementation_auxiliary(name)]
            ),
            "aligned_missing_scan_rows": aligned_deps["missing_scan_rows"],
        },
        "overlap": {
            "mathlib": overlap_summary(selected_mathlib, set(aligned_deps["mathlib"])),
            "project": overlap_summary(selected_project, set(aligned_deps["project"])),
            "all_lean": overlap_summary(all_selected, set(aligned_deps["mathlib"]) | set(aligned_deps["project"])),
        },
        "gap_class": classify_gap(selected=selected, gold=gold, source=source),
        "diagnostic_caveat": (
            "Post-hoc diagnostic only. Gold declarations and elaborated direct dependencies are not "
            "available to source-only selector/generator prompts, and direct dependency sets include "
            "implementation details rather than a minimal necessary context proof."
        ),
    }


def analyze(
    *,
    failure_summary: Path,
    gold_candidates: Path,
    scan_jsonl: Path,
    include_compiled: bool = False,
) -> dict[str, Any]:
    failure_data = read_json(failure_summary)
    gold_by_id = load_gold_candidates(gold_candidates)
    scan = load_scan(scan_jsonl)
    sources = [
        source
        for source in failure_data.get("best_sources") or []
        if include_compiled or source.get("failure_class") != "compiled"
    ]
    rows = [analyze_source(source, gold_by_id, scan) for source in sources]
    gap_counts: dict[str, int] = {}
    for row in rows:
        key = str(row["gap_class"])
        gap_counts[key] = gap_counts.get(key, 0) + 1
    return {
        "schema_version": "repoprover.latex_statement_context_gap_summary.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "failure_summary": display_path(failure_summary),
        "gold_candidates": display_path(gold_candidates),
        "scan_jsonl": display_path(scan_jsonl),
        "include_compiled": include_compiled,
        "source_unit_count": len(rows),
        "gap_class_counts": dict(sorted(gap_counts.items())),
        "sources": rows,
        "benchmark_honesty_caveat": (
            "This artifact intentionally uses post-hoc gold declarations and elaborated dependency scans "
            "only to diagnose context-selection failures. It must not be used as model-facing context "
            "for source-only benchmark runs."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--failure-summary", type=Path, default=REPO_ROOT / "docs/latex-statement-failure-taxonomy-summary.json")
    parser.add_argument("--gold-candidates", type=Path, default=REPO_ROOT / "docs/latex-statement-gold-candidates.jsonl")
    parser.add_argument("--scan-jsonl", type=Path, default=REPO_ROOT / "docs/lean-elaborated-direct-deps.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-compiled", action="store_true")
    args = parser.parse_args()
    summary = analyze(
        failure_summary=args.failure_summary,
        gold_candidates=args.gold_candidates,
        scan_jsonl=args.scan_jsonl,
        include_compiled=args.include_compiled,
    )
    write_json(args.output, summary)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
