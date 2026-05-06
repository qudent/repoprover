# LaTeX Statement Panel Run

- Generated: `2026-05-06T09:13:03.211380+00:00`
- Panel: `docs/latex-statement-fresh-slice-2026-05-06.json`
- Output root: `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1-support-scoped-rerun`
- Stop reason: `completed`
- Unit count: 5

## Stage Results

| Stage | Exit | Seconds | Command |
|---|---:|---:|---|
| `context_selection` | 0 | 0.0 | `reuse existing selector run` |
| `generation` | 0 | 0.0 | `reuse existing generation run` |
| `verification` | 0 | 562.506 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/verify_latex_statement_generation.py --generation-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/generation --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 120.0 --output docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1-support-scoped-rerun/eval/verification-results.json --materialize-visible-support --support-timeout-seconds 30.0` |
| `gold_comparison` | 0 | 0.08 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/compare_latex_statement_generation_to_gold.py --selector-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/context-selection --generation-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/generation --verification-results docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1-support-scoped-rerun/eval/verification-results.json --output docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1-support-scoped-rerun/eval/gold-comparison-results.json` |
| `semantic_coverage` | 0 | 33.378 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/verify_latex_statement_semantic_coverage.py --selector-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/context-selection --generation-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/generation --verification-results docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1-support-scoped-rerun/eval/verification-results.json --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 120.0 --output docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1-support-scoped-rerun/eval/semantic-coverage-results.json` |

## Metrics

```json
{
  "context_selection": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/context-selection",
    "budget_only": false,
    "paid_call_made": true,
    "valid_json": true,
    "elapsed_seconds": 151.406,
    "cost": 0.0064647,
    "prompt_tokens": 28677,
    "completion_tokens": 2431,
    "reasoning_tokens": 0,
    "cached_prompt_tokens": 0,
    "units_selected": 5
  },
  "hydration": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/context-selection/eval/mathlib-hydration-summary.json",
    "batch_count": 1,
    "request_count": 10,
    "exact_identifier_count": 9,
    "fallback_exact_identifier_count": 8,
    "lean_check_statuses": [
      "lean_errors"
    ],
    "fallback_lean_check_statuses": [
      "ok"
    ]
  },
  "generation": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/generation",
    "budget_only": false,
    "paid_call_made": true,
    "valid_json": true,
    "elapsed_seconds": 43.746,
    "cost": 0.0062877416,
    "prompt_tokens": 43029,
    "completion_tokens": 2447,
    "reasoning_tokens": 0,
    "cached_prompt_tokens": 3072,
    "batch_count": 5,
    "normalized_unit_count": 3
  },
  "verification": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1-support-scoped-rerun/eval/verification-results.json",
    "unit_count": 5,
    "compile_passed_units": 1,
    "failure_class_counts": {
      "compile_failure": 1,
      "compiled": 1,
      "declined_cannot_prove": 3
    },
    "materialize_visible_support": true
  },
  "gold_comparison": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1-support-scoped-rerun/eval/gold-comparison-results.json",
    "unit_count": 5,
    "compile_passed_units": 1,
    "compiled_name_overlap_units": 0,
    "compiled_needs_semantic_review_units": 1,
    "coverage_status_counts": {
      "compile_failure": 1,
      "compiled_needs_semantic_review": 1,
      "not_generated_cannot_prove": 3
    }
  },
  "semantic_coverage": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1-support-scoped-rerun/eval/semantic-coverage-results.json",
    "unit_count": 5,
    "all_aligned_gold_proved_units": 1,
    "coverage_status_counts": {
      "all_aligned_gold_proved": 1,
      "generated_not_compiled": 4
    }
  }
}
```
