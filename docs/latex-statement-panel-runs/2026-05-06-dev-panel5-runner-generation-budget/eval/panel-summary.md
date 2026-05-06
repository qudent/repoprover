# LaTeX Statement Panel Run

- Generated: `2026-05-06T06:19:17.680424+00:00`
- Panel: `/home/name/repos/repoprover/docs/latex-statement-dev-panel-2026-05-06.json`
- Output root: `docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-generation-budget`
- Stop reason: `budget_only_after_generation`
- Unit count: 5

## Stage Results

| Stage | Exit | Seconds | Command |
|---|---:|---:|---|
| `context_selection` | 0 | 0.0 | `reuse existing selector run` |
| `generation` | 0 | 1.045 | `/home/name/repos/repoprover/.venv/bin/python3 scripts/run_latex_statement_generation.py --selector-run docs/latex-statement-context-runs/2026-05-06-dev-panel5-v1-paid-reasoning-none --output docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-generation-budget/generation --model deepseek/deepseek-v4-flash --base-url https://openrouter.ai/api/v1 --max-tokens 8192 --temperature 0.0 --max-units-per-call 1 --reasoning-effort none --budget-only` |

## Metrics

```json
{
  "context_selection": {
    "path": "docs/latex-statement-context-runs/2026-05-06-dev-panel5-v1-paid-reasoning-none",
    "budget_only": false,
    "paid_call_made": true,
    "valid_json": true,
    "elapsed_seconds": 33.785,
    "cost": 0.00300286,
    "prompt_tokens": 17077,
    "completion_tokens": 2186,
    "reasoning_tokens": 0,
    "units_selected": 5
  },
  "hydration": {
    "path": "docs/latex-statement-context-runs/2026-05-06-dev-panel5-v1-paid-reasoning-none/eval/mathlib-hydration-summary.json",
    "batch_count": 1,
    "request_count": 7,
    "exact_identifier_count": 7,
    "fallback_exact_identifier_count": 19,
    "lean_check_statuses": [
      "lean_errors"
    ],
    "fallback_lean_check_statuses": [
      "ok"
    ]
  },
  "generation": {
    "path": "docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-generation-budget/generation",
    "budget_only": true,
    "paid_call_made": false,
    "valid_json": true,
    "elapsed_seconds": null,
    "cost": 0.0,
    "prompt_tokens": null,
    "completion_tokens": null,
    "reasoning_tokens": null,
    "batch_count": 5,
    "normalized_unit_count": 0
  },
  "verification": null,
  "gold_comparison": null,
  "semantic_coverage": null
}
```
