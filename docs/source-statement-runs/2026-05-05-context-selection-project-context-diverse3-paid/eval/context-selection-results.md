# Source context-selection results

- Generated at: `2026-05-05T14:35:50.172569+00:00`
- Model: `deepseek/deepseek-v4-flash`
- Price source: `openrouter-catalog-live`
- Prompt/completion price per 1M tokens: `$0.140000` / `$0.280000`
- Context length: `1048576`
- Max tokens: `8192`
- Reasoning effort: ``
- Round: `project-context-diverse3-selector`
- Budget only: `False`
- Records selected: `3`
- Batches: `2` of size `2`
- Paid calls made: `2`
- Actual reported cost: `$0.004149`
- Hydrate Mathlib: `True`
- Compare gold after selection: `True`
- Payload target-name leaks: `0`
- Allowed previous-project name overlaps: `0`

Selector prompts use source-only context and do not include target Lean declaration names, statements, or proofs. Gold comparison, when enabled, is written only after selector output exists.

| Batch | Records | Paid | Cost | Status |
|---:|---:|---|---:|---|
| 1 | 2 | True | $0.002360 | `ok` |
| 2 | 1 | True | $0.001789 | `ok` |
