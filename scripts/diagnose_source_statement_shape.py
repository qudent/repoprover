#!/usr/bin/env python3
"""Diagnose source-statement generation shape issues without hidden gold."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.materialize_minimal_context_smoke import load_jsonl  # noqa: E402
from scripts.run_minimal_context_eval import write_json  # noqa: E402


WarningRow = dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _get_user_payload(payload: dict[str, Any]) -> dict[str, Any]:
    for message in payload.get("messages", []):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _context_text(user_payload: dict[str, Any]) -> str:
    context = user_payload.get("context")
    if not isinstance(context, dict):
        return ""
    parts = [
        context.get("target_source_focus"),
        context.get("source_statement_or_chunk"),
        context.get("domain_statement_shape_guidance"),
        context.get("local_lean_style"),
    ]
    return "\n".join(_json_text(part) for part in parts if part is not None)


def _excerpt(text: str, pattern: str, *, window: int = 90) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    start = max(0, match.start() - window)
    end = min(len(text), match.end() + window)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _warning(
    code: str,
    message: str,
    *,
    visible_cue: str = "",
    generated_cue: str = "",
    recommendation: str = "",
    severity: str = "warning",
) -> WarningRow:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "visible_cue": visible_cue,
        "generated_cue": generated_cue,
        "recommendation": recommendation,
    }


def diagnose_shape(user_payload: dict[str, Any], declaration: str) -> list[WarningRow]:
    """Return warnings based only on visible prompt context and generated Lean."""

    context_text = _context_text(user_payload)
    context_lower = context_text.lower()
    warnings: list[WarningRow] = []

    if (
        "embedunivinbiv" in context_lower
        and "sequence equality" in context_lower
        and re.search(r":\s*∀\s+\w+\s*,\s*\w+\s+\w+\s*=\s*\w+\s+\w+", declaration)
    ):
        warnings.append(
            _warning(
                "pointwise_conclusion_instead_of_sequence_equality",
                "Generated statement concludes pointwise equality where the visible context asks for sequence equality.",
                visible_cue=_excerpt(context_text, r"sequence equality|embedUnivInBiv"),
                generated_cue=_excerpt(declaration, r":\s*∀\s+\w+\s*,\s*\w+\s+\w+\s*=\s*\w+\s+\w+"),
                recommendation="Prefer a statement whose conclusion is function/sequence equality, proving it with `funext k` internally.",
            )
        )

    source_mentions_right_x_pow = (
        "f * x^k" in context_lower
        or "f * x ^ k" in context_lower
        or "`f * x^k" in context_lower
        or "`f * x ^ k" in context_lower
    )
    if source_mentions_right_x_pow:
        generated_lower = declaration.lower()
        wrong_side = re.search(r"\bx\s*\*\s*\w+", declaration, flags=re.IGNORECASE) is not None
        special_x_case = "x ^ k" not in generated_lower and "x^k" not in generated_lower
        whole_series_mk = "PowerSeries.mk" in declaration
        if wrong_side or special_x_case or whole_series_mk:
            warnings.append(
                _warning(
                    "wrong_x_power_multiplication_side_or_shape",
                    "Visible context asks for the general right-multiplication `f * X^k` coefficient shape, but the generated statement appears to use the wrong side, a special `X` case, or whole-series `mk` equality.",
                    visible_cue=_excerpt(context_text, r"f \* X\^k|f \* X \^ k|right-match|coefficient theorem shape"),
                    generated_cue=_excerpt(declaration, r"X\s*\*|PowerSeries\.mk|X\s*\^\s*k"),
                    recommendation="Use the right-multiplication coefficient theorem shape for `f * X ^ k`; do not collapse to `X * f` or a special whole-series equality unless the source asks for it.",
                )
            )

    if (
        "simple transposition" in context_lower
        and ("value inequalities" in context_lower or "k ≠ i, i+1" in context_lower)
        and re.search(r"\bk\s*≠\s*⟨", declaration)
        and "k.val" not in declaration
    ):
        warnings.append(
            _warning(
                "fin_object_inequality_instead_of_value_inequality",
                "Generated statement uses constructed `Fin` object inequalities where the visible local guidance asks for value inequalities.",
                visible_cue=_excerpt(context_text, r"value inequalities|k ≠ i, i\+1"),
                generated_cue=_excerpt(declaration, r"\bk\s*≠\s*⟨[^)]+"),
                recommendation="Use assumptions on values such as `k.val ≠ i.val` and `k.val ≠ i.val + 1`, then discharge the `Fin` inequalities inside the proof.",
            )
        )

    if (
        ("prod_f" in context_text or "finite approximator" in context_lower)
        and ("infinite product" in context_lower or "finite coefficient approximators" in context_lower)
        and re.search(r"∏'|Multipliable|map_tprod|TopologicalSpace|Continuous", declaration)
    ):
        warnings.append(
            _warning(
                "topological_infprod_api_instead_of_local_approximator",
                "Generated statement appears to switch from the visible finite-approximator API to topological infinite-product APIs.",
                visible_cue=_excerpt(context_text, r"finite approximator|prod_f|finite coefficient approximators"),
                generated_cue=_excerpt(declaration, r"∏'|Multipliable|map_tprod|TopologicalSpace|Continuous"),
                recommendation="Stay in the local coefficient-approximator API with finite sets `M`/`J` and `prod_f` when those are the visible cues.",
            )
        )

    if (
        ("g ∘ x = g" in context_lower or "powerseries.subst x g" in context_lower or "subst x g" in context_lower)
        and re.search(r"PowerSeries\.subst\s+g\s+X", declaration)
    ):
        warnings.append(
            _warning(
                "substitution_argument_order_swapped",
                "Visible context asks for `PowerSeries.subst X g`, but the generated declaration appears to use `PowerSeries.subst g X`.",
                visible_cue=_excerpt(context_text, r"PowerSeries\.subst X g|subst X g|g ∘ X = g"),
                generated_cue=_excerpt(declaration, r"PowerSeries\.subst\s+g\s+X"),
                recommendation="Keep the local argument order `PowerSeries.subst inner outer`; for `g ∘ X = g`, state `PowerSeries.subst X g = g`.",
            )
        )

    if (
        "hassubst.x'" in context_lower
        and "coeff_subst'" in context_lower
        and "fps_comp_coeff" in declaration
    ):
        warnings.append(
            _warning(
                "substitution_proof_uses_avoided_finite_composition_helper",
                "Visible guidance suggests the direct `HasSubst.X'`/`coeff_subst'` proof shape, but the generated proof uses the avoided finite-composition helper.",
                visible_cue=_excerpt(context_text, r"HasSubst\.X'|coeff_subst'|finite-composition helper"),
                generated_cue=_excerpt(declaration, r"fps_comp_coeff"),
                recommendation="Prefer `ext n`; rewrite with `coeff_subst'`; then use `coeff_X_pow` and `finsum_eq_single`.",
                severity="info",
            )
        )

    return warnings


def diagnose_record(
    run_output: Path,
    row: dict[str, Any],
    index: int,
    *,
    payload_name: str,
    model_output_name: str,
) -> dict[str, Any]:
    record_dir = run_output / f"record-{index:03d}"
    result: dict[str, Any] = {
        "index": index,
        "record_id": str(row.get("id") or row.get("record_id")),
        "record_dir": str(record_dir),
        "warnings": [],
    }
    payload_path = record_dir / payload_name
    model_output_path = record_dir / model_output_name
    if not payload_path.exists():
        result["failure_class"] = "missing_payload"
        result["warning_count"] = 0
        return result
    if not model_output_path.exists():
        result["failure_class"] = "missing_model_output"
        result["warning_count"] = 0
        return result

    payload = _read_json(payload_path)
    model_output = _read_json(model_output_path)
    user_payload = _get_user_payload(payload)
    declaration = str(model_output.get("lean_declaration") or "")
    result["generated_name"] = model_output.get("declaration_name")
    if not user_payload:
        result["failure_class"] = "missing_user_payload"
        result["warning_count"] = 0
        return result
    if not declaration.strip():
        result["failure_class"] = "missing_declaration"
        result["warning_count"] = 0
        return result

    warnings = diagnose_shape(user_payload, declaration)
    result["warnings"] = warnings
    result["warning_count"] = len(warnings)
    result["warning_codes"] = [warning["code"] for warning in warnings]
    write_json(record_dir / "shape-diagnostic.json", result)
    return result


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def render_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Source-statement shape diagnostic",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Run output: `{summary['run_output']}`",
        f"- Payload artifact: `{summary['payload_name']}`",
        f"- Model artifact: `{summary['model_output_name']}`",
        f"- Records: {summary['records_completed']}",
        f"- Records with warnings: {summary['records_with_warnings']}",
        f"- Warning codes: `{json.dumps(summary['warning_codes'], sort_keys=True)}`",
        "",
        "| # | Warnings | Record | Generated name | Codes |",
        "|---:|---:|---|---|---|",
    ]
    for row in summary["results"]:
        codes = ", ".join(row.get("warning_codes") or [])
        lines.append(
            f"| {row['index']} | {row.get('warning_count', 0)} | `{row['record_id']}` | `{row.get('generated_name') or ''}` | `{codes}` |"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    selected_path = args.run_output / "eval" / "selected-records.jsonl"
    selected_rows = load_jsonl(selected_path)
    results = [
        diagnose_record(
            args.run_output,
            row,
            index,
            payload_name=args.payload_name,
            model_output_name=args.model_output_name,
        )
        for index, row in enumerate(selected_rows, start=1)
    ]
    warning_codes = Counter(
        warning["code"]
        for row in results
        for warning in row.get("warnings", [])
    )
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_output": str(args.run_output),
        "payload_name": args.payload_name,
        "model_output_name": args.model_output_name,
        "records_completed": len(results),
        "records_with_warnings": sum(1 for row in results if row.get("warning_count", 0) > 0),
        "warning_codes": dict(sorted(warning_codes.items())),
        "results": results,
    }
    eval_dir = args.run_output / "eval"
    write_json(eval_dir / "shape-diagnostic-results.json", summary)
    write_jsonl(eval_dir / "shape-diagnostic-results.jsonl", results)
    render_markdown(eval_dir / "shape-diagnostic-results.md", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-output", type=Path, required=True)
    parser.add_argument("--payload-name", default="openrouter-payload.json")
    parser.add_argument("--model-output-name", default="model-output.json")
    return parser.parse_args()


if __name__ == "__main__":
    summary = run(parse_args())
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))
