#!/usr/bin/env python3
"""Build prompt-safe project-context packs from proof-lane decline mining.

The input decline-context report is source-only. This pack builder optionally
uses gold-candidate metadata as an exclusion filter only: aligned/referencing
declarations for the same source unit are removed, but their names/snippets are
not written into the pack.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_latex_statement_generation import write_json  # noqa: E402


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


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


def load_task(run_dir: Path, unit_key: str) -> dict[str, Any]:
    task_dir = infer_task_dir(run_dir)
    if task_dir is None:
        return {}
    path = task_dir / "tasks" / f"{unit_key}.json"
    if not path.exists():
        return {}
    return read_json(path)


def declaration_name(declaration: dict[str, Any]) -> str | None:
    name = declaration.get("full_name") or declaration.get("name")
    return str(name) if name else None


def normalize_project_path(path: str, project_root_name: str) -> str:
    parts = Path(path).parts
    if parts and parts[0] == project_root_name:
        return str(Path(*parts[1:]))
    return str(Path(path))


def load_hidden_filters(gold_candidates: Path, project_root_name: str) -> dict[str, dict[str, Any]]:
    filters: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(gold_candidates):
        source_id = str(row.get("id") or "")
        posthoc = row.get("posthoc_lean_alignment") or {}
        names: set[str] = set()
        local_names: set[str] = set()
        ranges: list[dict[str, Any]] = []
        for key in ("aligned_lean_declarations", "referencing_lean_declarations"):
            for declaration in posthoc.get(key) or []:
                name = declaration_name(declaration)
                if name:
                    names.add(name)
                    local_names.add(name.split(".")[-1])
                path = declaration.get("path")
                line_range = declaration.get("line_range")
                if path and isinstance(line_range, list) and len(line_range) == 2:
                    ranges.append(
                        {
                            "path": normalize_project_path(str(path), project_root_name),
                            "start": int(line_range[0]),
                            "end": int(line_range[1]),
                        }
                    )
        filters[source_id] = {
            "hidden_name_count": len(names),
            "hidden_range_count": len(ranges),
            "names": names,
            "local_names": local_names,
            "ranges": ranges,
        }
    return filters


def candidate_in_hidden_range(candidate: dict[str, Any], hidden_filter: dict[str, Any], project_root_name: str) -> bool:
    path = normalize_project_path(str(candidate.get("path") or ""), project_root_name)
    try:
        line = int(candidate.get("line") or 0)
    except (TypeError, ValueError):
        return False
    for range_record in hidden_filter.get("ranges") or []:
        if path == range_record["path"] and range_record["start"] <= line <= range_record["end"]:
            return True
    return False


def candidate_mentions_current_source_label(candidate: dict[str, Any], labels: list[str]) -> bool:
    snippet = str(candidate.get("snippet") or "")
    return any(label and label in snippet for label in labels)


def candidate_is_hidden(
    candidate: dict[str, Any],
    *,
    source_labels: list[str],
    hidden_filter: dict[str, Any],
    project_root_name: str,
) -> bool:
    name = str(candidate.get("name") or "")
    if name in hidden_filter.get("names", set()):
        return True
    if candidate_in_hidden_range(candidate, hidden_filter, project_root_name):
        return True
    return candidate_mentions_current_source_label(candidate, source_labels)


def select_candidates(
    identifier_result: dict[str, Any],
    *,
    source_labels: list[str],
    hidden_filter: dict[str, Any],
    project_root_name: str,
    max_candidates_per_identifier: int,
) -> tuple[list[dict[str, Any]], int]:
    selected: list[dict[str, Any]] = []
    excluded = 0
    for candidate in identifier_result.get("candidates") or []:
        if candidate_is_hidden(
            candidate,
            source_labels=source_labels,
            hidden_filter=hidden_filter,
            project_root_name=project_root_name,
        ):
            excluded += 1
            continue
        selected.append(
            {
                "identifier_from_decline_note": identifier_result.get("identifier"),
                "name": candidate.get("name"),
                "kind": candidate.get("kind"),
                "path": candidate.get("path"),
                "line": candidate.get("line"),
                "lean_snippet": candidate.get("snippet"),
                "match_kind": candidate.get("match_kind"),
                "context_source": "proof_lane_decline_context_miner_project_source_candidate",
                "safety_policy": (
                    "Candidate came from a target-hidden proof-lane decline note and project-source "
                    "scan. Same-source aligned/referencing target declarations were used only as an "
                    "exclusion filter and are not included in this pack."
                ),
            }
        )
        if len(selected) >= max_candidates_per_identifier:
            break
    return selected, excluded


def build_unit_pack(
    unit: dict[str, Any],
    *,
    hidden_filters: dict[str, dict[str, Any]],
    project_root_name: str,
    max_candidates_per_identifier: int,
) -> dict[str, Any]:
    run_dir = Path(str(unit.get("run_dir") or ""))
    unit_key = str(unit.get("unit_key") or "")
    task = load_task(run_dir, unit_key)
    source = task.get("source_unit") or {}
    source_id = str(source.get("id") or "")
    source_labels = [str(label) for label in source.get("labels") or []]
    hidden_filter = hidden_filters.get(source_id) or {
        "hidden_name_count": 0,
        "hidden_range_count": 0,
        "names": set(),
        "local_names": set(),
        "ranges": [],
    }
    selected_context: list[dict[str, Any]] = []
    skipped_identifiers: list[dict[str, Any]] = []
    excluded_hidden_candidate_count = 0
    for result in unit.get("identifier_results") or []:
        if result.get("classification") != "found_and_name_mentioned_but_declaration_not_selected":
            continue
        candidates, excluded = select_candidates(
            result,
            source_labels=source_labels,
            hidden_filter=hidden_filter,
            project_root_name=project_root_name,
            max_candidates_per_identifier=max_candidates_per_identifier,
        )
        excluded_hidden_candidate_count += excluded
        if candidates:
            selected_context.extend(candidates)
        else:
            skipped_identifiers.append(
                {
                    "identifier_from_decline_note": result.get("identifier"),
                    "reason": "all_candidates_filtered_or_absent",
                    "hidden_filter_applied": bool(hidden_filter.get("hidden_name_count") or hidden_filter.get("hidden_range_count")),
                }
            )

    return {
        "unit_key": unit_key,
        "source_unit_id": source_id,
        "source_labels": source_labels,
        "run_dir": unit.get("run_dir"),
        "selected_project_context": selected_context,
        "selected_project_context_count": len(selected_context),
        "skipped_identifiers": skipped_identifiers,
        "excluded_hidden_candidate_count": excluded_hidden_candidate_count,
        "hidden_filter_stats": {
            "same_source_hidden_name_count": hidden_filter.get("hidden_name_count", 0),
            "same_source_hidden_range_count": hidden_filter.get("hidden_range_count", 0),
        },
    }


def build_pack(args: argparse.Namespace) -> dict[str, Any]:
    report = read_json(args.decline_context_report)
    project_root_name = Path(str(report.get("project_root") or "algebraic-combinatorics")).name
    hidden_filters = load_hidden_filters(args.gold_candidates, project_root_name) if args.gold_candidates else {}
    units = [
        build_unit_pack(
            unit,
            hidden_filters=hidden_filters,
            project_root_name=project_root_name,
            max_candidates_per_identifier=args.max_candidates_per_identifier,
        )
        for unit in report.get("units") or []
    ]
    total_context = sum(int(unit["selected_project_context_count"]) for unit in units)
    total_excluded = sum(int(unit["excluded_hidden_candidate_count"]) for unit in units)
    return {
        "schema_version": "repoprover.proof_lane_decline_context_pack.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decline_context_report": display_path(args.decline_context_report),
        "gold_candidates_filter": display_path(args.gold_candidates) if args.gold_candidates else None,
        "gold_filter_policy": (
            "Gold-candidate metadata is used only to exclude same-source aligned/referencing target "
            "declarations. Hidden target names and snippets are not emitted."
            if args.gold_candidates
            else "No gold-candidate exclusion filter was applied."
        ),
        "unit_count": len(units),
        "selected_project_context_count": total_context,
        "excluded_hidden_candidate_count": total_excluded,
        "units": units,
    }


def markdown(pack: dict[str, Any]) -> str:
    lines = [
        "# Proof-Lane Decline Context Pack",
        "",
        f"Generated: `{pack['generated_at']}`",
        f"Decline report: `{pack['decline_context_report']}`",
        f"Selected project-context snippets: `{pack['selected_project_context_count']}`",
        f"Hidden candidates excluded: `{pack['excluded_hidden_candidate_count']}`",
        "",
        "## Policy",
        pack["gold_filter_policy"],
        "",
        "## Units",
    ]
    for unit in pack["units"]:
        lines.extend(
            [
                "",
                f"### {unit['unit_key']} - `{unit['source_unit_id']}`",
                "",
                f"- Selected project context: `{unit['selected_project_context_count']}`",
                f"- Hidden candidates excluded: `{unit['excluded_hidden_candidate_count']}`",
                "",
            ]
        )
        for context in unit["selected_project_context"]:
            lines.append(
                f"- `{context['identifier_from_decline_note']}` -> `{context['name']}` "
                f"({context['kind']}, {context['path']}:{context['line']})"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decline-context-report", type=Path, required=True)
    parser.add_argument("--gold-candidates", type=Path, default=REPO_ROOT / "docs/latex-statement-gold-candidates.jsonl")
    parser.add_argument("--max-candidates-per-identifier", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    pack = build_pack(args)
    write_json(args.output, pack)
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown(pack), encoding="utf-8")
    print(json.dumps(pack, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
