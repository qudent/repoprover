# LaTeX Statement Panel Run

- Generated: `2026-05-06T17:51:29.678078+00:00`
- Panel: `docs/latex-statement-unit004-prior-deps-panel-2026-05-06.json`
- Output root: `docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high`
- Stop reason: `completed`
- Unit count: 1

## Stage Results

| Stage | Exit | Seconds | Command |
|---|---:|---:|---|
| `context_selection` | 0 | 14.216 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/run_latex_statement_context_selection.py --output docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/context-selection --model deepseek/deepseek-v4-flash --base-url https://openrouter.ai/api/v1 --max-tokens 8192 --temperature 0.0 --unit-id AlgebraicCombinatorics/tex/SignedCounting/SubtractiveMethods.tex:lem.cancel.all-even.l1 --reasoning-effort none` |
| `hydration` | 0 | 51.264 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/hydrate_latex_statement_context.py --run docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/context-selection --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 120.0 --summary docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/context-selection/eval/mathlib-hydration-summary.json` |
| `generation` | 0 | 178.728 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/run_latex_statement_generation.py --selector-run docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/context-selection --output docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/generation --model deepseek/deepseek-v4-pro --base-url https://openrouter.ai/api/v1 --max-tokens 32768 --temperature 0.0 --max-units-per-call 1 --reasoning-effort high` |
| `verification` | 0 | 56.052 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/verify_latex_statement_generation.py --generation-run docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/generation --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 360.0 --output docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/eval/verification-results.json --materialize-visible-support --support-timeout-seconds 360.0 --support-mode assumption` |
| `gold_comparison` | 0 | 0.09 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/compare_latex_statement_generation_to_gold.py --selector-run docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/context-selection --generation-run docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/generation --verification-results docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/eval/verification-results.json --output docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/eval/gold-comparison-results.json` |
| `semantic_coverage` | 0 | 1.117 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/verify_latex_statement_semantic_coverage.py --selector-run docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/context-selection --generation-run docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/generation --verification-results docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/eval/verification-results.json --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 360.0 --output docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/eval/semantic-coverage-results.json` |

## Metrics

```json
{
  "context_selection": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/context-selection",
    "budget_only": false,
    "paid_call_made": true,
    "valid_json": true,
    "elapsed_seconds": 12.782,
    "cost": 0.00087402,
    "prompt_tokens": 4805,
    "completion_tokens": 719,
    "reasoning_tokens": 0,
    "cached_prompt_tokens": 0,
    "units_selected": 1
  },
  "hydration": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/context-selection/eval/mathlib-hydration-summary.json",
    "batch_count": 1,
    "request_count": 2,
    "exact_identifier_count": 1,
    "fallback_exact_identifier_count": 8,
    "lean_check_statuses": [
      "ok"
    ],
    "fallback_lean_check_statuses": [
      "ok"
    ]
  },
  "generation": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/generation",
    "budget_only": false,
    "paid_call_made": true,
    "valid_json": true,
    "elapsed_seconds": 177.573,
    "cost": 0.01084977,
    "prompt_tokens": 10290,
    "completion_tokens": 7326,
    "reasoning_tokens": 6924,
    "cached_prompt_tokens": 0,
    "batch_count": 1,
    "normalized_unit_count": 0
  },
  "verification": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/eval/verification-results.json",
    "unit_count": 1,
    "compile_passed_units": 0,
    "failure_class_counts": {
      "compile_failure": 1
    },
    "materialize_visible_support": true
  },
  "gold_comparison": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/eval/gold-comparison-results.json",
    "unit_count": 1,
    "compile_passed_units": 0,
    "compiled_name_overlap_units": 0,
    "compiled_needs_semantic_review_units": 0,
    "coverage_status_counts": {
      "compile_failure": 1
    }
  },
  "semantic_coverage": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/eval/semantic-coverage-results.json",
    "unit_count": 1,
    "all_aligned_gold_proved_units": 0,
    "coverage_status_counts": {
      "generated_not_compiled": 1
    }
  }
}
```
