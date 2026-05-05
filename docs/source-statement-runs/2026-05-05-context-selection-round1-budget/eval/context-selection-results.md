# Source context-selection results

- Generated at: `2026-05-05T13:05:32.011100+00:00`
- Model: `deepseek/deepseek-v4-pro`
- Price source: `openrouter-catalog-live`
- Prompt/completion price per 1M tokens: `$0.435000` / `$0.870000`
- Context length: `1048576`
- Max tokens: `8192`
- Reasoning effort: `low`
- Round: `round1-formalization-sketch-and-context-needs`
- Budget only: `True`
- Records selected: `8`
- Batches: `2` of size `4`
- Paid calls made: `0`
- Actual reported cost: `$0.000000`
- Hydrate Mathlib: `True`
- Compare gold after selection: `True`
- Payload target-name leaks: `0`

Selector prompts use source-only context and do not include target Lean declaration names, statements, or proofs. Gold comparison, when enabled, is written only after selector output exists.

| Batch | Records | Paid | Cost | Status |
|---:|---:|---|---:|---|
| 1 | 4 | False | $0.000000 | `budget_only` |
| 2 | 4 | False | $0.000000 | `budget_only` |
