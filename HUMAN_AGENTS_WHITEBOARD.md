# RepoProver - Human/Agents Whiteboard

## Active Human Prompts
- No unresolved prompt. The first minimal-context records have been attacked by a live Qwen reviewer and hardened, but still need human review before being treated as gold.

## Agent Notes
- Local install is complete. Toy Lean setup/build succeeds at `/tmp/repoprover-toy-test`.
- RepoProver reaches real LLM/tool/build execution on the toy project with `--provider google --no-background-agents`, but Gemini did not complete the sketch cleanly in the latest run.
- Run logs are under `/tmp/repoprover-toy-test/runs/20260427-164853/`.
- A clean `gemini-3-flash-preview` toy attempt was created at `/tmp/repoprover-toy-gemini3-flash`; the model ID works for direct chat. The OpenAI-compatible tool loop now preserves provider-specific tool-call metadata, including Gemini thought signatures, and a live one-tool continuation smoke passes.
- OpenRouter `z-ai/glm-5.1` succeeded through the bounded toy sketch/review/merge path in `/tmp/repoprover-toy-gemini3-flash`; final `lake build` passes. The run was stopped after the coordinator launched follow-up maintain contributors.
- Pricing estimate for the first-merge toy formalization is about $0.10 on Gemini 3 Flash Preview standard paid pricing, based on completed sketch plus two reviewer token totals.
- Experiment guide: `docs/model-experiments.md`.
- Whiteboard request addressed in `docs/minimal-context-budget-plan.md`: it defines the minimal-context record schema, first FPS chapter pilot scope, OpenRouter budget estimates for `$7.42` observed / `$10` intended / `$50` larger pilot, and next execution plan.
- Added `scripts/estimate_openrouter_budget.py` for live OpenRouter price/balance estimates from actual RepoProver token logs.
- Added `--stop-after-first-merge` to bound smoke tests. It means: after the first approved PR merges and passes the merge build, the coordinator exits before launching maintain/proof follow-up agents.
- Live cheap extraction pass: `qwen/qwen3-coder` over first chapter excerpts produced three seed records at 11,582 input tokens / 404 output tokens / `$0.0038658`; records were line-checked and kept low-trust.
- Added `scripts/review_minimal_context_records.py` to fetch published TeX/Lean snippets and run OpenRouter reviewer audits over the JSONL records.
- DeepSeek reviewer attempt (`deepseek/deepseek-v4-pro`) reached OpenRouter and billed about `$0.016702`, but returned empty content after the 4,096 completion-token cap; keep the parse-error report as a provider failure example.
- Qwen reviewer pass (`qwen/qwen3-coder`) reviewed all three records for about `$0.004827`. Records were hardened with added Mathlib/proof dependencies, a clipped evidence bug fix, and low-trust review notes.

## Open Questions
- Should the next pass spend budget on exact Mathlib import minimization for these three records, or scale the same Qwen review process to more FPS chunks first?
