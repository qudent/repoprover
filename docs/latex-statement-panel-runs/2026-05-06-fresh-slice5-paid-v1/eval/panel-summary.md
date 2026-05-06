# LaTeX Statement Panel Run

- Generated: `2026-05-06T08:52:27.101922+00:00`
- Panel: `docs/latex-statement-fresh-slice-2026-05-06.json`
- Output root: `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1`
- Stop reason: `completed`
- Unit count: 5

## Stage Results

| Stage | Exit | Seconds | Command |
|---|---:|---:|---|
| `context_selection` | 0 | 152.808 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/run_latex_statement_context_selection.py --output docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/context-selection --model deepseek/deepseek-v4-flash --base-url https://openrouter.ai/api/v1 --max-tokens 8192 --temperature 0.0 --unit-id AlgebraicCombinatorics/tex/Determinants/LGV2.tex:cor.lgv.catalan-hankel-det-0 --unit-id AlgebraicCombinatorics/tex/FPS/DividingFPS.tex:cor.fps.invertible.field --unit-id AlgebraicCombinatorics/tex/FPS/NonIntegerPowers.tex:prop.binom.nCk-2i-qedmo.CN --unit-id AlgebraicCombinatorics/tex/SignedCounting/SubtractiveMethods.tex:lem.cancel.all-even.l1 --unit-id AlgebraicCombinatorics/tex/SymmetricFunctions/PieriJacobiTrudi.tex:thm.sf.jt-e --reasoning-effort none` |
| `hydration` | 0 | 60.633 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/hydrate_latex_statement_context.py --run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/context-selection --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 120.0 --summary docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/context-selection/eval/mathlib-hydration-summary.json` |
| `generation` | 0 | 45.001 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/run_latex_statement_generation.py --selector-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/context-selection --output docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/generation --model deepseek/deepseek-v4-flash --base-url https://openrouter.ai/api/v1 --max-tokens 8192 --temperature 0.0 --max-units-per-call 1 --reasoning-effort none` |
| `verification` | 0 | 715.825 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/verify_latex_statement_generation.py --generation-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/generation --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 120.0 --output docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/eval/verification-results.json --materialize-visible-support --support-timeout-seconds 30.0` |
| `gold_comparison` | 0 | 0.097 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/compare_latex_statement_generation_to_gold.py --selector-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/context-selection --generation-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/generation --verification-results docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/eval/verification-results.json --output docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/eval/gold-comparison-results.json` |
| `semantic_coverage` | 0 | 1.475 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/verify_latex_statement_semantic_coverage.py --selector-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/context-selection --generation-run docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/generation --verification-results docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/eval/verification-results.json --project-root /home/name/repos/repoprover/algebraic-combinatorics --timeout-seconds 120.0 --output docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/eval/semantic-coverage-results.json` |

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
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/eval/verification-results.json",
    "unit_count": 5,
    "compile_passed_units": 0,
    "failure_class_counts": {
      "compile_failure": 2,
      "declined_cannot_prove": 3
    },
    "materialize_visible_support": true
  },
  "gold_comparison": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/eval/gold-comparison-results.json",
    "unit_count": 5,
    "compile_passed_units": 0,
    "compiled_name_overlap_units": 0,
    "compiled_needs_semantic_review_units": 0,
    "coverage_status_counts": {
      "compile_failure": 2,
      "not_generated_cannot_prove": 3
    }
  },
  "semantic_coverage": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/eval/semantic-coverage-results.json",
    "unit_count": 5,
    "all_aligned_gold_proved_units": 0,
    "coverage_status_counts": {
      "generated_not_compiled": 5
    }
  }
}
```
