"""Tests for the minimal-context DeepSeek eval runner."""

from argparse import Namespace
from pathlib import Path

import json

from scripts.run_minimal_context_eval import (
    DEFAULT_MODEL,
    DEFAULT_PRICE,
    estimate_payload_cost,
    materialize_budget_report,
    materialize_eval,
    summarize_openrouter_response_cost,
)


def test_estimate_payload_cost_uses_prompt_and_completion_prices() -> None:
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [{"role": "user", "content": "a" * 400}],
        "max_tokens": 100,
    }

    estimate = estimate_payload_cost(payload, DEFAULT_PRICE)

    assert estimate["prompt_chars"] == 400
    assert estimate["estimated_prompt_tokens"] == 100
    assert estimate["max_completion_tokens"] == 100
    assert estimate["estimated_max_cost_usd"] == (100 * DEFAULT_PRICE.prompt_per_token) + (
        100 * DEFAULT_PRICE.completion_per_token
    )


def test_summarize_openrouter_response_cost_prefers_actual_usage_cost() -> None:
    response = {
        "model": DEFAULT_MODEL,
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "cost": 0.00123,
        },
    }

    summary = summarize_openrouter_response_cost(response, DEFAULT_PRICE)

    assert summary["actual_cost_usd"] == 0.00123
    assert summary["estimated_cost_from_usage_usd"] == (10 * DEFAULT_PRICE.prompt_per_token) + (
        20 * DEFAULT_PRICE.completion_per_token
    )


def test_materialize_eval_writes_prompt_payload_without_api_call(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "lakefile.lean").write_text("import Lake\n", encoding="utf-8")
    (source_root / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
    (source_root / "Demo.lean").write_text(
        "\n".join(
            [
                "import Mathlib",
                "namespace Demo",
                "",
                "/-- True is true. -/",
                "theorem target : True := by",
                "  trivial",
                "",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (source_root / "Demo.tex").write_text("A proposition whose proof is immediate.\n", encoding="utf-8")
    records = tmp_path / "records.jsonl"
    records.write_text(
        (
            '{"id":"demo:target","chapter_id":"demo",'
            '"output":{"lean_path":"Demo.lean","declaration_names":["Demo.target"],'
            '"line_range":[4,6],"chunk_kind":"theorem"},'
            '"minimal_context":{"imports":["Mathlib"],'
            '"source_spans":[{"path":"Demo.tex","line_range":[1,1],"labels":["demo"]}],'
            '"file_context":[{"path":"Demo.lean","kind":"namespace","name":"Demo","line_range":[2,2]}],'
            '"lean_predecessors":[]},'
            '"trust":{"human_review":0.0,"source_span":0.75,"lean_dependency_graph":0.35}}\n'
        ),
        encoding="utf-8",
    )

    output = tmp_path / "eval-project"
    paths = materialize_eval(
        Namespace(
            records=records,
            project_root=source_root,
            output=output,
            record_id=[],
            limit=1,
            force=False,
            lake_cache_from=None,
            no_git=True,
            include_record_imports=False,
            model=DEFAULT_MODEL,
            max_tokens=8192,
            temperature=0.0,
            reasoning_effort="high",
            source_context=0,
            lean_context=0,
        )
    )

    payload = paths["payload"].read_text(encoding="utf-8")
    assert DEFAULT_MODEL in payload
    assert "Fill the target Lean declaration" in payload
    assert "theorem target : True := by\\n  sorry" in payload

    assert paths["selected_records"].read_text(encoding="utf-8").count("\n") == 1
    review_command = (output / "eval" / "review-command.txt").read_text(encoding="utf-8")
    assert "scripts/review_minimal_context_records.py" in review_command
    assert "--model deepseek/deepseek-v4-pro" in review_command
