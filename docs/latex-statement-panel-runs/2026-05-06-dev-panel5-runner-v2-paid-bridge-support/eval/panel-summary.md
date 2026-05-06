# LaTeX Statement Panel Run

- Generated: `2026-05-06T07:07:37.804964+00:00`
- Panel: `/home/name/repos/repoprover/docs/latex-statement-dev-panel-2026-05-06.json`
- Output root: `docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support`
- Stop reason: `completed`
- Unit count: 5

## Stage Results

| Stage | Exit | Seconds | Command |
|---|---:|---:|---|
| `context_selection` | 0 | 0.0 | `reuse existing selector run` |
| `generation` | 0 | 41.584 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/run_latex_statement_generation.py --selector-run docs/latex-statement-context-runs/2026-05-06-dev-panel5-v1-paid-bridge-hydrated --output docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/generation --model deepseek/deepseek-v4-flash --base-url https://openrouter.ai/api/v1 --max-tokens 8192 --temperature 0.0 --max-units-per-call 1 --reasoning-effort none` |
| `verification` | 0 | 590.741 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/verify_latex_statement_generation.py --generation-run docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/generation --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 120.0 --output docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/eval/verification-results.json --materialize-visible-support --support-timeout-seconds 30.0` |
| `gold_comparison` | 0 | 0.081 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/compare_latex_statement_generation_to_gold.py --selector-run docs/latex-statement-context-runs/2026-05-06-dev-panel5-v1-paid-bridge-hydrated --generation-run docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/generation --verification-results docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/eval/verification-results.json --output docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/eval/gold-comparison-results.json` |
| `semantic_coverage` | 0 | 47.643 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/verify_latex_statement_semantic_coverage.py --selector-run docs/latex-statement-context-runs/2026-05-06-dev-panel5-v1-paid-bridge-hydrated --generation-run docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/generation --verification-results docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/eval/verification-results.json --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 120.0 --output docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/eval/semantic-coverage-results.json` |

## Metrics

```json
{
  "context_selection": {
    "path": "docs/latex-statement-context-runs/2026-05-06-dev-panel5-v1-paid-bridge-hydrated",
    "budget_only": false,
    "paid_call_made": true,
    "valid_json": true,
    "elapsed_seconds": 115.186,
    "cost": 0.003094084,
    "prompt_tokens": 17077,
    "completion_tokens": 9219,
    "reasoning_tokens": 6914,
    "cached_prompt_tokens": 16768,
    "units_selected": 5
  },
  "hydration": {
    "path": "docs/latex-statement-context-runs/2026-05-06-dev-panel5-v1-paid-bridge-hydrated/eval/mathlib-hydration-summary.json",
    "batch_count": 1,
    "request_count": 7,
    "exact_identifier_count": 6,
    "fallback_exact_identifier_count": 27,
    "lean_check_statuses": [
      "lean_errors"
    ],
    "fallback_lean_check_statuses": [
      "ok"
    ]
  },
  "generation": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/generation",
    "budget_only": false,
    "paid_call_made": true,
    "valid_json": true,
    "elapsed_seconds": 40.307,
    "cost": 0.0053754232,
    "prompt_tokens": 36897,
    "completion_tokens": 2192,
    "reasoning_tokens": 0,
    "cached_prompt_tokens": 2944,
    "batch_count": 5,
    "normalized_unit_count": 2
  },
  "verification": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/eval/verification-results.json",
    "unit_count": 5,
    "compile_passed_units": 2,
    "failure_class_counts": {
      "compile_failure": 1,
      "compiled": 2,
      "declined_cannot_prove": 2
    },
    "materialize_visible_support": true
  },
  "gold_comparison": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/eval/gold-comparison-results.json",
    "unit_count": 5,
    "compile_passed_units": 2,
    "compiled_name_overlap_units": 1,
    "compiled_needs_semantic_review_units": 1,
    "coverage_status_counts": {
      "compile_failure": 1,
      "compiled_name_overlap": 1,
      "compiled_needs_semantic_review": 1,
      "not_generated_cannot_prove": 2
    }
  },
  "semantic_coverage": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-v2-paid-bridge-support/eval/semantic-coverage-results.json",
    "unit_count": 5,
    "all_aligned_gold_proved_units": 1,
    "coverage_status_counts": {
      "all_aligned_gold_proved": 1,
      "generated_not_compiled": 3,
      "no_aligned_gold_proved": 1
    }
  }
}
```
