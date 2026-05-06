# LaTeX Statement Panel Run

- Generated: `2026-05-06T14:16:36.371801+00:00`
- Panel: `docs/latex-statement-fresh-slice-2026-05-06.json`
- Output root: `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1`
- Stop reason: `completed`
- Unit count: 5

## Stage Results

| Stage | Exit | Seconds | Command |
|---|---:|---:|---|
| `context_selection` | 0 | 0.0 | `reuse existing selector run` |
| `hydration` | 0 | 48.532 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/hydrate_latex_statement_context.py --run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/context-selection --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 120.0 --summary docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/context-selection/eval/mathlib-hydration-summary.json` |
| `generation` | 0 | 0.0 | `reuse existing generation run` |
| `verification` | 0 | 1158.772 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/verify_latex_statement_generation.py --generation-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/generation --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 120.0 --output docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/eval/verification-results.json --materialize-visible-support --support-timeout-seconds 30.0` |
| `gold_comparison` | 0 | 0.138 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/compare_latex_statement_generation_to_gold.py --selector-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/context-selection --generation-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/generation --verification-results docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/eval/verification-results.json --output docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/eval/gold-comparison-results.json` |
| `semantic_coverage` | 0 | 1.78 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/verify_latex_statement_semantic_coverage.py --selector-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/context-selection --generation-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/generation --verification-results docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/eval/verification-results.json --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 120.0 --output docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/eval/semantic-coverage-results.json` |

## Metrics

```json
{
  "context_selection": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/context-selection",
    "budget_only": false,
    "paid_call_made": true,
    "valid_json": true,
    "elapsed_seconds": 31.242,
    "cost": 0.00502572,
    "prompt_tokens": 32066,
    "completion_tokens": 1916,
    "reasoning_tokens": 0,
    "cached_prompt_tokens": 0,
    "units_selected": 5
  },
  "hydration": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/context-selection/eval/mathlib-hydration-summary.json",
    "batch_count": 1,
    "request_count": 6,
    "exact_identifier_count": 5,
    "fallback_exact_identifier_count": 8,
    "lean_check_statuses": [
      "lean_errors"
    ],
    "fallback_lean_check_statuses": [
      "lean_errors"
    ]
  },
  "generation": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/generation",
    "budget_only": false,
    "paid_call_made": true,
    "valid_json": true,
    "elapsed_seconds": 18.057,
    "cost": 0.006082748,
    "prompt_tokens": 44527,
    "completion_tokens": 2283,
    "reasoning_tokens": 0,
    "cached_prompt_tokens": 5760,
    "batch_count": 5,
    "normalized_unit_count": 2
  },
  "verification": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/eval/verification-results.json",
    "unit_count": 5,
    "compile_passed_units": 0,
    "failure_class_counts": {
      "compile_failure": 1,
      "declined_cannot_prove": 4
    },
    "materialize_visible_support": true
  },
  "gold_comparison": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/eval/gold-comparison-results.json",
    "unit_count": 5,
    "compile_passed_units": 0,
    "compiled_name_overlap_units": 0,
    "compiled_needs_semantic_review_units": 0,
    "coverage_status_counts": {
      "compile_failure": 1,
      "not_generated_cannot_prove": 4
    }
  },
  "semantic_coverage": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/eval/semantic-coverage-results.json",
    "unit_count": 5,
    "all_aligned_gold_proved_units": 0,
    "coverage_status_counts": {
      "generated_not_compiled": 5
    }
  }
}
```
