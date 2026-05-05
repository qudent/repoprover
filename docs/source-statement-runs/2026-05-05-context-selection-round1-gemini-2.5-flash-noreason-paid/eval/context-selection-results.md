# Source context-selection results

- Generated at: `2026-05-05T13:05:07.774769+00:00`
- Model: `google/gemini-2.5-flash`
- Price source: `openrouter-catalog-live`
- Prompt/completion price per 1M tokens: `$0.300000` / `$2.500000`
- Context length: `1048576`
- Max tokens: `4096`
- Reasoning effort: ``
- Round: `round1-formalization-sketch-and-context-needs`
- Budget only: `False`
- Records selected: `2`
- Batches: `1` of size `2`
- Paid calls made: `1`
- Actual reported cost: `$0.014736`
- Hydrate Mathlib: `True`
- Compare gold after selection: `True`
- Payload target-name leaks: `0`

Selector prompts use source-only context and do not include target Lean declaration names, statements, or proofs. Gold comparison, when enabled, is written only after selector output exists.

| Batch | Records | Paid | Cost | Status |
|---:|---:|---|---:|---|
| 1 | 2 | True | $0.014736 | `no_content_or_length` |
