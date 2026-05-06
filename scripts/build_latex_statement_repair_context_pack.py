#!/usr/bin/env python3
"""Build a checked repair context pack from repair-context selection output."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LEAN_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def load_selection(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "batch-001" / "repair-context-selection-output.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json(path)


def load_hydration(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "batch-001" / "mathlib-lean-hydrated-context.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json(path)


def mathlib_request_index(selection: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    index: dict[tuple[str, int], dict[str, Any]] = {}
    for unit in selection.get("units") or []:
        unit_key = str(unit.get("unit_key") or "")
        for request_index, request in enumerate(unit.get("needed_mathlib_context") or [], start=1):
            index[(unit_key, request_index)] = request
    return index


def clean_identifier(value: Any) -> str | None:
    text = str(value or "").strip().strip("`")
    if LEAN_IDENTIFIER_RE.fullmatch(text):
        return text
    return None


def fallback_bridge_note(record: dict[str, Any], checked_fallback_names: list[str]) -> dict[str, Any] | None:
    """Explain how to compose checked fallback facts for common missing direct lemmas."""

    names = set(checked_fallback_names)
    query_text = " ".join(
        str(record.get(key) or "")
        for key in ("name_or_query", "exact_identifier", "expected_signature_or_shape", "why_needed")
    )
    if {"Multiset.sort_eq", "Multiset.sum_coe"}.issubset(names):
        return {
            "unit_key": record.get("unit_key"),
            "task_id": record.get("task_id"),
            "bridge_kind": "multiset_sort_sum_preservation",
            "unavailable_direct_request": record.get("exact_identifier") or record.get("name_or_query"),
            "checked_fallback_candidates": [
                name for name in checked_fallback_names if name in {"Multiset.sort_eq", "Multiset.sum_coe"}
            ],
            "proof_guidance": (
                "There may be no direct theorem for the requested sorted-list sum equality. "
                "Use `Multiset.sort_eq` to identify the multiset coerced from the sorted list "
                "with the original multiset, and `Multiset.sum_coe` to move between list sum "
                "and multiset sum. For a goal shaped like `(s.sort r).sum = s.sum`, first "
                "rewrite by `Multiset.sum_coe (s.sort r)` in the reverse direction, then "
                "close the multiset-sum equality with "
                "`congrArg Multiset.sum (Multiset.sort_eq s r)`, adapted to local names."
            ),
        }
    if (
        {"List.Pairwise.rel_get_of_le", "List.Pairwise.rel_get_of_lt"} & names
        and "antitone" in query_text.lower()
    ):
        return {
            "unit_key": record.get("unit_key"),
            "task_id": record.get("task_id"),
            "bridge_kind": "sorted_list_pointwise_order",
            "unavailable_direct_request": record.get("exact_identifier") or record.get("name_or_query"),
            "checked_fallback_candidates": [
                name
                for name in checked_fallback_names
                if name
                in {
                    "List.Pairwise.rel_get_of_le",
                    "List.Pairwise.rel_get_of_lt",
                    "List.sortedGE_iff_antitone_get",
                }
            ],
            "proof_guidance": (
                "There may be no direct padded-antitone theorem. Use the checked sorted/Pairwise "
                "fact for the sorted list, then apply `List.Pairwise.rel_get_of_le` or "
                "`List.Pairwise.rel_get_of_lt` to in-range indices. Handle padded out-of-range "
                "indices by local case splits and zero-bound arithmetic rather than requiring a "
                "single library theorem for the whole padded function."
            ),
        }
    if "Nat.add_choose_eq" in names and (
        "Finset.Nat.sum_antidiagonal_eq_sum_range_succ" in names
        or "Finset.Nat.sum_antidiagonal_eq_sum_range_succ_mk" in names
    ):
        return {
            "unit_key": record.get("unit_key"),
            "task_id": record.get("task_id"),
            "bridge_kind": "vandermonde_antidiagonal_to_range_sum",
            "unavailable_direct_request": record.get("exact_identifier") or record.get("name_or_query"),
            "checked_fallback_candidates": [
                name
                for name in checked_fallback_names
                if name
                in {
                    "Nat.add_choose_eq",
                    "Finset.Nat.sum_antidiagonal_eq_sum_range_succ",
                    "Finset.Nat.sum_antidiagonal_eq_sum_range_succ_mk",
                }
            ],
            "proof_guidance": (
                "`Nat.add_choose_eq` is Vandermonde's identity in antidiagonal form. "
                "When the source statement uses a range/Icc sum over `k` with term "
                "`a.choose k * b.choose (n - k)`, rewrite the antidiagonal sum with "
                "`Finset.Nat.sum_antidiagonal_eq_sum_range_succ` or the `_mk` variant, "
                "then adjust `range n.succ` versus `Icc 0 n` by finite-set extensionality "
                "or simp-normalization."
            ),
        }
    return None


def build_context_pack(
    *,
    selection: dict[str, Any],
    hydration: dict[str, Any],
    repair_context_run: Path | None = None,
) -> dict[str, Any]:
    request_index = mathlib_request_index(selection)
    checked_signatures: list[dict[str, Any]] = []
    failed_or_unchecked: list[dict[str, Any]] = []
    fallback_resolved: list[dict[str, Any]] = []
    fallback_bridge_notes: list[dict[str, Any]] = []

    for row in hydration.get("hydrated_mathlib_context") or []:
        unit_key = str(row.get("unit_key") or "")
        index = int(row.get("request_index") or 0)
        original = request_index.get((unit_key, index), {})
        lean_check = row.get("lean_check") or {}
        record = {
            "unit_key": unit_key,
            "task_id": row.get("task_id"),
            "name_or_query": row.get("query"),
            "exact_identifier": row.get("exact_identifier"),
            "expected_signature_or_shape": row.get("expected_signature_or_shape"),
            "why_needed": row.get("why_needed") or original.get("why_needed"),
            "lean_check": lean_check,
        }
        if lean_check.get("status") == "checked":
            checked_signatures.append(
                {
                    "unit_key": unit_key,
                    "task_id": row.get("task_id"),
                    "name": row.get("exact_identifier") or row.get("query"),
                    "signature": lean_check.get("signature"),
                    "why_needed": row.get("why_needed") or original.get("why_needed"),
                    "source": "autonomous_repair_context_selection_hydrated_with_lean_check",
                }
            )
            for related in row.get("related_mathlib_declarations") or []:
                related_check = related.get("lean_check") or {}
                if related_check.get("status") != "checked":
                    continue
                checked_signatures.append(
                    {
                        "unit_key": unit_key,
                        "task_id": row.get("task_id"),
                        "name": related.get("name"),
                        "signature": related_check.get("signature"),
                        "why_needed": (
                            f"Checked related declaration for selected {row.get('exact_identifier') or row.get('query')}: "
                            f"{row.get('why_needed') or original.get('why_needed') or ''}"
                        ).strip(),
                        "source": "autonomous_repair_context_selection_checked_related_declaration",
                        "related_to": row.get("exact_identifier") or row.get("query"),
                    }
                )
        else:
            checked_fallback_names: list[str] = []
            for candidate in (row.get("fallback_mathlib_candidates") or [])[:4]:
                candidate_check = candidate.get("lean_check") or {}
                if candidate_check.get("status") == "checked":
                    checked_fallback_names.append(str(candidate.get("name") or ""))
                    checked_signatures.append(
                        {
                            "unit_key": unit_key,
                            "task_id": row.get("task_id"),
                            "name": candidate.get("name"),
                            "signature": candidate_check.get("signature"),
                            "why_needed": (
                                f"Checked fallback candidate for failed request {row.get('query')}: "
                                f"{row.get('why_needed') or original.get('why_needed') or ''}"
                            ).strip(),
                            "source": "autonomous_repair_context_selection_checked_fallback_candidate",
                            "fallback_for_query": row.get("query"),
                            "declaration_line": candidate.get("declaration_line"),
                        }
                    )
            if checked_fallback_names:
                fallback_resolved.append(
                    {
                        **record,
                        "resolved_by_checked_fallback_candidates": checked_fallback_names,
                        "policy": (
                            "The requested direct identifier did not check, but the listed "
                            "fallback candidates did. Treat the requested identifier as "
                            "unavailable and use the checked fallback signatures instead."
                        ),
                    }
                )
                note = fallback_bridge_note(record, checked_fallback_names)
                if note is not None:
                    fallback_bridge_notes.append(note)
            else:
                failed_or_unchecked.append(record)

    proof_strategy_notes: list[dict[str, Any]] = []
    same_unit_helper_plan: list[dict[str, Any]] = []
    selected_visible_context: list[dict[str, Any]] = []
    do_not_use_identifiers: list[str] = []
    discarded_do_not_use_items: list[dict[str, Any]] = []
    missing_or_uncertain_context: list[dict[str, Any]] = []
    for unit in selection.get("units") or []:
        unit_key = str(unit.get("unit_key") or "")
        proof_strategy_notes.append(
            {
                "unit_key": unit_key,
                "failure_analysis": unit.get("failure_analysis"),
                "proof_strategy_note": unit.get("repair_strategy_note"),
                "selector_confidence": unit.get("selector_confidence"),
            }
        )
        for item in unit.get("selected_visible_context") or []:
            selected_visible_context.append({"unit_key": unit_key, **item})
        for item in unit.get("same_unit_helper_plan") or []:
            same_unit_helper_plan.append({"unit_key": unit_key, **item})
        for name in unit.get("do_not_use_identifiers") or []:
            cleaned = clean_identifier(name)
            if cleaned:
                if cleaned not in do_not_use_identifiers:
                    do_not_use_identifiers.append(cleaned)
            else:
                discarded_do_not_use_items.append(
                    {
                        "unit_key": unit_key,
                        "item": name,
                        "reason": "not_an_exact_lean_identifier",
                    }
                )
        for item in unit.get("missing_or_uncertain_context") or []:
            missing_or_uncertain_context.append({"unit_key": unit_key, "item": item})

    return {
        "schema_version": "repoprover.latex_statement_checked_repair_context.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repair_context_run": str(repair_context_run) if repair_context_run else None,
        "benchmark_honesty_caveat": (
            "Autonomous second-round repair-context selector output. Hidden aligned target Lean "
            "declarations, statements, names, and proofs are not included. Mathlib signatures here "
            "are included only after Lean #check hydration."
        ),
        "proof_strategy_notes": proof_strategy_notes,
        "same_unit_helper_plan": same_unit_helper_plan,
        "selected_visible_context": selected_visible_context,
        "checked_signatures": checked_signatures,
        "fallback_resolved_context_requests": fallback_resolved,
        "fallback_bridge_notes": fallback_bridge_notes,
        "failed_or_unchecked_context_requests": failed_or_unchecked,
        "do_not_use_identifiers": do_not_use_identifiers,
        "discarded_do_not_use_items": discarded_do_not_use_items,
        "missing_or_uncertain_context": missing_or_uncertain_context,
        "raw_selection_output": selection,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    pack = build_context_pack(
        selection=load_selection(args.repair_context_run),
        hydration=load_hydration(args.repair_context_run),
        repair_context_run=args.repair_context_run,
    )
    write_json(args.output, pack)
    return {
        "schema_version": "repoprover.latex_statement_checked_repair_context_build.v1",
        "output": str(args.output),
        "checked_signature_count": len(pack["checked_signatures"]),
        "fallback_resolved_context_request_count": len(pack["fallback_resolved_context_requests"]),
        "fallback_bridge_note_count": len(pack["fallback_bridge_notes"]),
        "failed_or_unchecked_context_request_count": len(pack["failed_or_unchecked_context_requests"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair-context-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
