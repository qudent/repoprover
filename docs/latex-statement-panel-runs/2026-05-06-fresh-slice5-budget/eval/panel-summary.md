# LaTeX Statement Panel Run

- Generated: `2026-05-06T08:51:43.868685+00:00`
- Panel: `docs/latex-statement-fresh-slice-2026-05-06.json`
- Output root: `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-budget`
- Stop reason: `budget_only_after_context_selection`
- Unit count: 5

## Stage Results

| Stage | Exit | Seconds | Command |
|---|---:|---:|---|
| `context_selection` | 0 | 1.353 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/run_latex_statement_context_selection.py --output docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-budget/context-selection --model deepseek/deepseek-v4-flash --base-url https://openrouter.ai/api/v1 --max-tokens 8192 --temperature 0.0 --unit-id AlgebraicCombinatorics/tex/Determinants/LGV2.tex:cor.lgv.catalan-hankel-det-0 --unit-id AlgebraicCombinatorics/tex/FPS/DividingFPS.tex:cor.fps.invertible.field --unit-id AlgebraicCombinatorics/tex/FPS/NonIntegerPowers.tex:prop.binom.nCk-2i-qedmo.CN --unit-id AlgebraicCombinatorics/tex/SignedCounting/SubtractiveMethods.tex:lem.cancel.all-even.l1 --unit-id AlgebraicCombinatorics/tex/SymmetricFunctions/PieriJacobiTrudi.tex:thm.sf.jt-e --reasoning-effort none --budget-only` |

## Metrics

```json
{
  "context_selection": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-budget/context-selection",
    "budget_only": true,
    "paid_call_made": false,
    "valid_json": false,
    "elapsed_seconds": null,
    "cost": 0.0,
    "prompt_tokens": null,
    "completion_tokens": null,
    "reasoning_tokens": null,
    "cached_prompt_tokens": null,
    "units_selected": 5
  },
  "hydration": null,
  "generation": null,
  "verification": null,
  "gold_comparison": null,
  "semantic_coverage": null
}
```
