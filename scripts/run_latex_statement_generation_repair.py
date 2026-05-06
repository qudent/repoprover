#!/usr/bin/env python3
"""Repair theorem-level LaTeX statement generation failures.

The repair prompt is still source-only: it reuses the selector/generation
context pack, plus the generated Lean body and Lean verifier errors. Hidden
aligned target declarations remain withheld.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_latex_statement_generation import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    build_generation_messages,
    enforce_generation_contracts,
    extract_message_content,
    maybe_parse_json,
    read_json,
    response_cost_summary,
    write_json,
)


def load_generation_output(generation_run: Path) -> dict[str, Any]:
    path = generation_run / "batch-001" / "generation-output.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json(path)


def load_raw_invalid_generation_output(generation_run: Path) -> dict[str, Any] | None:
    for name in ("raw-generation-output.json", "raw-repair-output.json"):
        path = generation_run / "batch-001" / name
        if path.exists():
            return {
                "path": str(path),
                "policy": (
                    "Unverified prior model output preserved because the normalized "
                    "consumer-facing artifact enforced the cannot-prove empty-output "
                    "contract. Use only for failure analysis; do not treat any Lean "
                    "code here as checked or acceptable."
                ),
                "output": read_json(path),
            }
    return None


def load_verification_results(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json(path)


def load_extra_context(paths: list[Path] | None) -> list[Any]:
    contexts: list[Any] = []
    for path in paths or []:
        contexts.append(read_json(path))
    return contexts


def filter_unit_keyed_lists(value: Any, unit_keys: set[str] | None) -> Any:
    """Filter nested context-pack lists whose items carry public unit keys."""

    if not unit_keys:
        return value
    if isinstance(value, dict):
        return {key: filter_unit_keyed_lists(item, unit_keys) for key, item in value.items()}
    if isinstance(value, list):
        has_unit_keyed_items = any(isinstance(item, dict) and "unit_key" in item for item in value)
        items = value
        if has_unit_keyed_items:
            items = [
                item
                for item in value
                if not isinstance(item, dict) or str(item.get("unit_key") or "") in unit_keys
            ]
        return [filter_unit_keyed_lists(item, unit_keys) for item in items]
    return value


def load_filtered_extra_context(paths: list[Path] | None, unit_keys: set[str] | None) -> list[Any]:
    return [filter_unit_keyed_lists(context, unit_keys) for context in load_extra_context(paths)]


def flatten_verification_units(verification: dict[str, Any]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for batch in verification.get("batches") or []:
        for unit in batch.get("units") or []:
            units.append(unit)
    return units


def filter_units_by_key(units: list[dict[str, Any]], unit_keys: set[str] | None) -> list[dict[str, Any]]:
    if not unit_keys:
        return units
    return [unit for unit in units if str(unit.get("unit_key") or "") in unit_keys]


def build_repair_messages(
    *,
    selector_run: Path,
    generation_run: Path,
    verification_results: Path,
    extra_context_paths: list[Path] | None = None,
    unit_keys: set[str] | None = None,
) -> list[dict[str, str]]:
    generation_messages = build_generation_messages(selector_run)
    generation_user = next(message for message in generation_messages if message["role"] == "user")
    generation_payload = json.loads(generation_user["content"])
    failed_output = load_generation_output(generation_run)
    verification = load_verification_results(verification_results)
    generation_payload["units"] = filter_units_by_key(generation_payload.get("units") or [], unit_keys)
    failed_output = {
        **failed_output,
        "units": filter_units_by_key(failed_output.get("units") or [], unit_keys),
    }
    verification_units = filter_units_by_key(flatten_verification_units(verification), unit_keys)

    system = (
        "You are a Lean 4 autoformalization repair agent. Repair failed Lean "
        "generation for LaTeX theorem-like source units using only the visible "
        "source/context pack, the generated Lean attempt, and Lean verifier "
        "errors. Hidden aligned Lean declarations, names, statements, and proofs "
        "are still withheld. Return exactly one JSON object."
    )
    user = {
        "task": (
            "Repair the failed generated Lean file bodies. Prefer a complete "
            "Lean-compiling repair when the visible context is enough. If the "
            "visible context is not enough, report cannot_prove_from_visible_context "
            "with exactly empty lean_file_body and empty declaration_names."
        ),
        "required_json_schema": generation_payload["required_json_schema"],
        "repair_instructions": [
            "Do not use sorry, admit, placeholders, or comments standing in for proof.",
            "Do not include Lean line comments or block comments inside lean_file_body.",
            "Do not include imports or markdown fences in lean_file_body.",
            "Do not ask for or infer the hidden aligned Lean declaration names/statements/proofs.",
            "Do not use any identifier that Lean already reported as Unknown constant or unknown identifier.",
            "Do not use a hydrated Mathlib exact_identifier whose lean_check.status is not `checked`.",
            "Fallback Mathlib candidates are search hints only; use them only when the shown declaration line is sufficient.",
            "Use local_file_predecessor_declarations and available_prior_project_context exactly as visible helper context.",
            "If additional_checked_repair_context contains proof_strategy_notes, selected_visible_context, or checked_signatures, attempt that checked route before declaring cannot_prove_from_visible_context.",
            "If additional_checked_repair_context contains same_unit_helper_plan, introduce those helper definitions/lemmas before the repaired main declaration when their sketches are supported by visible context and checked signatures.",
            "Use fresh descriptive helper names from same_unit_helper_plan only as newly introduced declarations; do not treat them as preexisting project facts.",
            "Do not introduce a replacement carrier type or ambient representation when visible source/project/local context already fixes the representation; helper declarations must be over the visible types unless the source unit itself defines a new type.",
            "If visible context represents ordered source data as an unordered finite collection (`Multiset`, `Finset`, or a finite enumeration), a checked sort/enumeration route can be a valid local helper plan. Implement the needed sorted/enumerated representative and prove its orderedness, length/cardinality, sum-preservation, and zero-padding obligations from checked facts before declaring the source order unavailable.",
            "For zero-padded sorted/enumerated representatives, a direct library theorem for the whole padded function is not required. Use local case splits for in-range and out-of-range indices, pointwise sorted/get lemmas, arithmetic monotonicity, and zero-bound facts when those ingredients are checked or elementary.",
            "When same_unit_helper_plan decomposes zero-padding, implement helpers in dependency order: padded definition, in-range get lemma, out-of-range zero lemma, antitone/order case split, sum-preservation split, and inverse/extensionality lemmas.",
            "Treat checked_signatures in additional_checked_repair_context as authoritative only when their source says they were hydrated with Lean #check or are checked fallback candidates.",
            "If additional_checked_repair_context contains fallback_resolved_context_requests, the original requested identifier is unavailable but the listed checked fallback candidates are valid replacements; do not treat that original request as an unresolved blocker.",
            "If additional_checked_repair_context contains fallback_bridge_notes, follow those generic checked-fallback rewrite/application routes before declaring a composite proof step unavailable.",
            "Respect do_not_use_identifiers and failed_or_unchecked_context_requests from additional_checked_repair_context.",
            "If additional_checked_repair_context contains discarded_do_not_use_items, treat them as schema sanitation notes only; they are not forbidden Lean identifiers.",
            "Do not claim a proof ingredient is missing when it is listed in additional_checked_repair_context checked_signatures or selected_visible_context.",
            "For finite sums and products over a Finset, use Lean's membership-binder notation `∑ x ∈ s, f x` and `∏ x ∈ s, f x`; Lean v4.28 does not accept `∑ x in s, ...` or `∏ x in s, ...`.",
            "If raw_invalid_generation_output is present, treat it as unverified prior scratchpad only: use it to understand the attempted route, but do not copy identifiers or proof steps unless visible context and Lean-checked signatures justify them.",
            "If notes describe a simpler corrected proof, implement that proof in lean_file_body instead of saying it will be adjusted later.",
            "If status is cannot_prove_from_visible_context, lean_file_body must be exactly empty and declaration_names must be an empty list.",
            "When status is cannot_prove_from_visible_context, do not use lean_file_body as a scratchpad. Put analysis in notes only; lean_file_body must be exactly \"\" and declaration_names exactly [].",
            "The repair output must be directly acceptable as a generation-output.json file.",
        ],
        "original_generation_task": generation_payload,
        "failed_generation_output": failed_output,
        "verification_results": {
            "compile_passed_units": sum(1 for unit in verification_units if unit.get("compile_passed")),
            "unit_count": len(verification_units),
            "units": verification_units,
        },
        "additional_checked_repair_context": load_filtered_extra_context(extra_context_paths, unit_keys),
        "raw_invalid_generation_output": load_raw_invalid_generation_output(generation_run),
        "benchmark_policy": {
            "target_lean_available_to_repair": False,
            "posthoc_alignment_hidden": True,
            "gold_comparison_is_posthoc_only": True,
        },
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, indent=2, sort_keys=True, ensure_ascii=False)}]


def run(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = args.output
    batch_dir = run_dir / "batch-001"
    eval_dir = run_dir / "eval"
    batch_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)

    messages = build_repair_messages(
        selector_run=args.selector_run,
        generation_run=args.generation_run,
        verification_results=args.verification_results,
        extra_context_paths=args.extra_context,
        unit_keys=set(getattr(args, "unit_key", None) or []) or None,
    )
    request_payload = {
        "model": args.model,
        "messages": messages,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "response_format": {"type": "json_object"},
    }
    if args.reasoning_effort:
        request_payload["extra_body"] = {"reasoning": {"effort": args.reasoning_effort, "exclude": True}}
    write_json(batch_dir / "generation-payload.json", request_payload)
    write_json(batch_dir / "repair-payload.json", request_payload)

    summary: dict[str, Any] = {
        "schema_version": "repoprover.latex_statement_generation_repair.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selector_run": str(args.selector_run),
        "generation_run": str(args.generation_run),
        "verification_results": str(args.verification_results),
        "output_path": str(run_dir),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "budget_only": args.budget_only,
        "paid_call_made": False,
        "valid_json": False,
        "parse_error": None,
    }
    if args.budget_only:
        write_json(eval_dir / "repair-results.json", summary)
        write_json(eval_dir / "generation-results.json", summary)
        return summary

    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    client = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url=args.base_url)
    started = time.monotonic()
    response = client.chat.completions.create(**request_payload)
    summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
    summary["paid_call_made"] = True
    write_json(batch_dir / "generation-response.json", response.model_dump())
    write_json(batch_dir / "repair-response.json", response.model_dump())
    content = extract_message_content(response)
    (batch_dir / "generation-assistant-content.txt").write_text(content, encoding="utf-8")
    (batch_dir / "repair-assistant-content.txt").write_text(content, encoding="utf-8")
    parsed, parse_error = maybe_parse_json(content)
    summary["parse_error"] = parse_error
    summary["valid_json"] = parsed is not None
    summary["cost_summary"] = response_cost_summary(response, args.model)
    if parsed is not None:
        normalized, contract_report = enforce_generation_contracts(parsed)
        if contract_report["normalized_unit_count"]:
            write_json(batch_dir / "raw-generation-output.json", parsed)
            write_json(batch_dir / "raw-repair-output.json", parsed)
        summary["contract_enforcement"] = contract_report
        write_json(batch_dir / "generation-output.json", normalized)
        write_json(batch_dir / "repair-output.json", normalized)
    write_json(eval_dir / "repair-results.json", summary)
    write_json(eval_dir / "generation-results.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-run", type=Path, required=True)
    parser.add_argument("--generation-run", type=Path, required=True)
    parser.add_argument("--verification-results", type=Path, required=True)
    parser.add_argument("--unit-key", action="append", help="Repair only the selected public unit key; may be repeated.")
    parser.add_argument(
        "--extra-context",
        type=Path,
        action="append",
        help="Additional JSON context pack for a repair round; may be repeated.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--reasoning-effort",
        default="none",
        help="OpenRouter reasoning effort override; use 'none' for schema-bound JSON repair.",
    )
    parser.add_argument("--budget-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
