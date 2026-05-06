#!/usr/bin/env python3
"""Select extra context for repairing theorem-level generation failures.

This is a second-round context selector. It sees the source-only generation
context, the failed generated Lean, and verifier errors. It does not see hidden
aligned target Lean declarations. Its output is deliberately context-shaped: a
proof-strategy note plus tight Mathlib/project/local context requests that can
be hydrated before another repair attempt.
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

from scripts.run_latex_statement_generation import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    build_generation_messages,
    extract_message_content,
    maybe_parse_json,
    read_json,
    response_cost_summary,
    write_json,
)
from scripts.run_latex_statement_generation_repair import (  # noqa: E402
    flatten_verification_units,
    load_generation_output,
    load_raw_invalid_generation_output,
    load_verification_results,
)


def build_hydratable_selector_output(selection: dict[str, Any]) -> dict[str, Any]:
    """Convert repair-context output into the shape expected by the hydrator."""

    units: list[dict[str, Any]] = []
    for unit in selection.get("units") or []:
        unit_key = str(unit.get("unit_key") or "")
        needed_mathlib_context = unit.get("needed_mathlib_context") or []
        units.append(
            {
                "unit_key": unit_key,
                "planned_declarations": [
                    {
                        "task_id": f"{unit_key}-repair-context-1",
                        "source_part": "repair_context_selection",
                        "needed_mathlib_context": needed_mathlib_context,
                    }
                ],
            }
        )
    return {
        "schema_version": "repoprover.latex_statement_repair_context_hydratable.v1",
        "units": units,
    }


def load_previous_checked_repair_context(generation_run: Path) -> list[Any]:
    payload_path = generation_run / "batch-001" / "repair-payload.json"
    if not payload_path.exists():
        payload_path = generation_run / "batch-001" / "generation-payload.json"
    if not payload_path.exists():
        return []
    try:
        payload = read_json(payload_path)
        messages = payload.get("messages") or []
        user_message = next((message for message in messages if message.get("role") == "user"), None)
        if not user_message:
            return []
        user_payload = json.loads(str(user_message.get("content") or ""))
    except (json.JSONDecodeError, OSError, TypeError, StopIteration):
        return []
    context = user_payload.get("additional_checked_repair_context") or []
    return context if isinstance(context, list) else [context]


def build_repair_context_messages(
    *,
    selector_run: Path,
    generation_run: Path,
    verification_results: Path,
    source_coverage_review_unit_keys: list[str] | None = None,
) -> list[dict[str, str]]:
    generation_messages = build_generation_messages(selector_run)
    generation_user = next(message for message in generation_messages if message["role"] == "user")
    generation_payload = json.loads(generation_user["content"])
    failed_output = load_generation_output(generation_run)
    verification = load_verification_results(verification_results)

    system = (
        "You are a Lean 4/Mathlib repair-context planning agent. Select the "
        "small extra context needed to repair failed source-only Lean generation. "
        "The hidden aligned target Lean declarations, names, statements, and "
        "proofs are withheld. Return exactly one JSON object."
    )
    user = {
        "task": (
            "For each failed unit, analyze the generated Lean failure and select "
            "additional context that should be hydrated before the next repair "
            "attempt. First sketch a proof route from the visible source, prior "
            "project/local context, and verifier errors. Then request only the "
            "Mathlib/project/local facts needed for that route. If a unit is "
            "listed in source_coverage_review_unit_keys, Lean may already compile; "
            "review the visible source text against the generated declarations and "
            "select context for any missing source cases, alternatives, displayed "
            "equations, or subclaims."
        ),
        "required_json_schema": {
            "units": [
                {
                    "unit_key": "unit-001",
                    "failure_analysis": "why the current attempt failed",
                    "repair_strategy_note": (
                        "brief proof plan using visible context plus requested "
                        "checked ingredients; prose only, no hidden target names"
                    ),
                    "selected_visible_context": [
                        {
                            "context_kind": "source|prior_project|local_file_predecessor|local_file_style",
                            "name_or_label": "visible source label or visible Lean declaration name",
                            "why_needed": "how it supports the repair proof route",
                        }
                    ],
                    "same_unit_helper_plan": [
                        {
                            "role": "definition|lemma|theorem",
                            "fresh_name_hint": "descriptive non-gold helper name to introduce",
                            "statement_sketch": "helper statement to prove from visible context",
                            "depends_on": ["fresh_name_hint values or visible context names"],
                            "needed_checked_ingredients": ["Mathlib/project/local facts needed for this helper"],
                            "why_needed": "which part of the main source theorem this helper supports",
                        }
                    ],
                    "needed_mathlib_context": [
                        {
                            "name_or_query": "exact Mathlib name or narrow search query",
                            "expected_signature_or_shape": "expected checked type/signature/docstring",
                            "why_needed": "how this fact is used in the repair proof",
                        }
                    ],
                    "do_not_use_identifiers": [
                        "exact Lean identifiers known to be unavailable from verifier errors or failed hydration"
                    ],
                    "missing_or_uncertain_context": ["remaining context to resolve if hydration fails"],
                    "selector_confidence": 0.0,
                }
            ]
        },
        "rules": [
            "Do not infer or reveal hidden target Lean declaration names/statements/proofs.",
            "Do not output Lean theorem code; this stage selects context only.",
            "Do not request a direct theorem whose name Lean already reported as unknown.",
            "Do not stop at a missing direct theorem if a proof can be decomposed into smaller visible project/local and Mathlib facts.",
            "Request every Mathlib bridge lemma needed by your own repair_strategy_note, including cardinality, coercion, order, equality-rewrite, empty-sum, and simplification facts.",
            "If your proof route says two expressions are equal or equivalent, request the exact theorem or simp lemma that justifies that conversion unless it is already shown in visible context.",
            "If your proof route uses `List.Pairwise`, `List.Sorted`, `Monotone`, or `Antitone`, request the checked pointwise/application lemmas that turn that relation into inequalities on `List.get`, function values, or indexed entries.",
            "If your proof route needs a cardinality bound for filtered or mapped finite data, request both the map/filter cardinality facts and the domain-cardinality facts, for example `Multiset.card_map`, `Multiset.filter_le`, `Multiset.card_le_card`, `Finset.card_univ`, and `Fintype.card_fin` when those shapes apply.",
            "If the source describes ordered tuples/lists but visible Lean context represents the same data as an unordered finite collection such as `Multiset` or `Finset`, consider a canonicalization route by sorting or enumerating that collection. Request the sort/enumeration, orderedness/get, length/cardinality, sum-preservation, and zero-padding facts needed for that route instead of treating unordered representation alone as missing context.",
            "For zero-padded sorted/enumerated data, do not require a single preexisting padded-antitone theorem. Plan a local helper proof by case-splitting in-range/out-of-range indices and request the pointwise sorted/get lemmas and zero-bound facts needed for those cases.",
            "Use previous project declarations only if they are shown in original_generation_task.",
            "Use local_file_predecessor_declarations only if they are shown in original_generation_task.",
            "Keep Mathlib requests tight. Prefer exact names when known; otherwise use narrow search queries with expected shapes.",
            "Separate source, prior project, local file, and Mathlib context in the output.",
            "If the visible context is fundamentally insufficient, explain that in missing_or_uncertain_context rather than inventing facts.",
            "If the repair route requires new intermediate facts inside this same source unit, list them in same_unit_helper_plan with fresh descriptive names. Do not classify such facts as missing ambient context unless they cannot be proved from visible source plus requested checked ingredients.",
            "same_unit_helper_plan must not contain hidden aligned target names; use role/statement sketches and fresh names only.",
            "If visible source/project/local context already fixes the carrier types or representation, same_unit_helper_plan must refine those visible types with helper defs/lemmas, not introduce a replacement carrier type or ambient representation. Only propose a new type/structure when the source unit itself defines one and no visible project representation exists.",
            "do_not_use_identifiers must contain exact Lean identifiers only, not expressions or prose. Put warnings about invalid expression shapes in missing_or_uncertain_context instead.",
            "If raw_invalid_generation_output is present, treat it as unverified prior scratchpad only: use it to understand the attempted route, but do not request or rely on identifiers unless visible context and Lean-checked signatures justify them.",
            "For units listed in source_coverage_review_unit_keys, do not rely on hidden gold data; use only the visible source text and generated output to identify missing source coverage.",
        ],
        "original_generation_task": generation_payload,
        "failed_generation_output": failed_output,
        "raw_invalid_generation_output": load_raw_invalid_generation_output(generation_run),
        "previous_checked_repair_context": load_previous_checked_repair_context(generation_run),
        "source_coverage_review_unit_keys": source_coverage_review_unit_keys or [],
        "verification_results": {
            "compile_passed_units": verification.get("compile_passed_units"),
            "unit_count": verification.get("unit_count"),
            "units": flatten_verification_units(verification),
        },
        "benchmark_policy": {
            "target_lean_available_to_context_selector": False,
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

    messages = build_repair_context_messages(
        selector_run=args.selector_run,
        generation_run=args.generation_run,
        verification_results=args.verification_results,
        source_coverage_review_unit_keys=getattr(args, "source_coverage_review_unit_key", None),
    )
    request_payload: dict[str, Any] = {
        "model": args.model,
        "messages": messages,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "response_format": {"type": "json_object"},
    }
    if args.reasoning_effort:
        request_payload["extra_body"] = {"reasoning": {"effort": args.reasoning_effort, "exclude": True}}
    write_json(batch_dir / "repair-context-selection-payload.json", request_payload)

    summary: dict[str, Any] = {
        "schema_version": "repoprover.latex_statement_repair_context_selection.v1",
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
        write_json(eval_dir / "repair-context-selection-results.json", summary)
        return summary

    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    client = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url=args.base_url)
    started = time.monotonic()
    response = client.chat.completions.create(**request_payload)
    summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
    summary["paid_call_made"] = True
    write_json(batch_dir / "repair-context-selection-response.json", response.model_dump())
    content = extract_message_content(response)
    (batch_dir / "repair-context-selection-assistant-content.txt").write_text(content, encoding="utf-8")
    parsed, parse_error = maybe_parse_json(content)
    summary["parse_error"] = parse_error
    summary["valid_json"] = parsed is not None
    summary["cost_summary"] = response_cost_summary(response, args.model)
    if parsed is not None:
        write_json(batch_dir / "repair-context-selection-output.json", parsed)
        write_json(batch_dir / "context-selection-output.json", build_hydratable_selector_output(parsed))
    write_json(eval_dir / "repair-context-selection-results.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-run", type=Path, required=True)
    parser.add_argument("--generation-run", type=Path, required=True)
    parser.add_argument("--verification-results", type=Path, required=True)
    parser.add_argument(
        "--source-coverage-review-unit-key",
        action="append",
        help=(
            "Unit key whose generated Lean compiles but should be reviewed for "
            "visible source coverage; may be repeated. This does not include gold declarations."
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--reasoning-effort",
        default="none",
        help="OpenRouter reasoning effort override; use 'none' for schema-bound JSON selection.",
    )
    parser.add_argument("--budget-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
