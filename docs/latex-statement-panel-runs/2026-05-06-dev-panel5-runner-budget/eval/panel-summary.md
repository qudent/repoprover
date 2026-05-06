# LaTeX Statement Panel Run

- Generated: `2026-05-06T06:19:00.277588+00:00`
- Panel: `/home/name/repos/repoprover/docs/latex-statement-dev-panel-2026-05-06.json`
- Output root: `docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-budget`
- Stop reason: `budget_only_after_context_selection`
- Unit count: 5

## Stage Results

| Stage | Exit | Seconds | Command |
|---|---:|---:|---|
| `context_selection` | 0 | 1.445 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/run_latex_statement_context_selection.py --output docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-budget/context-selection --model deepseek/deepseek-v4-flash --base-url https://openrouter.ai/api/v1 --max-tokens 8192 --temperature 0.0 --unit-id AlgebraicCombinatorics/tex/FPS/DividingFPS.tex:thm.commring.inverse-uni --unit-id AlgebraicCombinatorics/tex/Determinants/BasicProperties.tex:thm.det.triang --unit-id AlgebraicCombinatorics/tex/Details/InfiniteProducts1.tex:lem.fps.prod.irlv.cong-div --unit-id AlgebraicCombinatorics/tex/FPS/FPSDefinition.tex:prop.binom.vandermonde.NN --unit-id AlgebraicCombinatorics/tex/SymmetricFunctions/MonomialSymmetric.tex:prop.sf.Npar-as-par --reasoning-effort none --budget-only` |

## Metrics

```json
{
  "context_selection": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-budget/context-selection",
    "budget_only": true,
    "paid_call_made": false,
    "valid_json": false,
    "elapsed_seconds": null,
    "cost": 0.0,
    "prompt_tokens": null,
    "completion_tokens": null,
    "reasoning_tokens": null,
    "units_selected": 5
  },
  "hydration": null,
  "generation": null,
  "verification": null,
  "gold_comparison": null,
  "semantic_coverage": null
}
```
