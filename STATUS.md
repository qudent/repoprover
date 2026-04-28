# RepoProver - Status

## Current State
RepoProver is installed locally in `.venv`, and Lean/Lake are installed through `elan`. The toy Lean project validates with OpenRouter `z-ai/glm-5.1` through sketch, review, merge, and final `lake build`; minimal-context gold-standard work now has a reviewed first FPS pilot scaffold and a reusable OpenRouter reviewer script.

## Active Goals
- [x] Install local Python and Lean dependencies.
- [x] Validate the toy Lean project setup and build.
- [x] Get the toy RepoProver sketch/review/merge loop to completion with a reliable model/provider path.
- [x] Document model experiments and relevant commit hashes.
- [x] Turn the whiteboard minimal-context/budget request into an initial plan, estimator, and pilot records.
- [x] Review and harden the first minimal-context pilot records.
- [ ] Minimize exact Mathlib imports/dependencies for the reviewed pilot records.

## Blockers
- The Google `gemini-2.5-flash` toy RepoProver run reaches real LLM/tool/build execution, but the sketcher repeatedly chooses nonexistent Nat parity imports and can hit the agent iteration limit without emitting a completion marker.
- No current blocker for basic Gemini 3 Flash tool-call continuation. Full toy sketch/review/merge validation with `gemini-3-flash-preview` still has not been rerun after the transcript fix.
- The first minimal-context records remain low-trust: Qwen reviewed and hardened them, but no human has reviewed them and broad `Mathlib` imports are not minimized.
- `deepseek/deepseek-v4-pro` is not a useful reviewer at the current 4,096 completion-token cap: live calls spent hidden reasoning tokens and returned empty message content.

## Recent Results
- Created `.venv` with `uv` and installed RepoProver in editable mode.
- Installed `elan`; the toy setup fetched Lean `v4.28.0`, Mathlib, REPL, and completed `lake build`.
- Added CLI provider/model configuration, OpenRouter support, `--no-background-agents`, and passed focused tests.
- Tried a clean toy run at `/tmp/repoprover-toy-gemini3-flash` with `--provider google --model gemini-3-flash-preview`; it failed deterministically on the Gemini thought-signature requirement before any Lean edit could be tested.
- Reused the built toy tree for `--provider openrouter --model z-ai/glm-5.1`; GLM 5.1 created, repaired, reviewed, and merged the toy sketch. Toy commits: `97c3bd9` sketch, `ed17e510` merge, `eef1daf` generated follow-up issues.
- Checked `facebookresearch/algebraic-combinatorics` via the GitHub tree API; no tracked `.repoprover/learnings.json` or similar learnings file exists in the published repo.
- Preserved provider-specific tool-call metadata in the shared tool loop, added a regression test for `extra_content.google.thought_signature`, and passed a live `gemini-3-flash-preview` one-tool smoke.
- Added `--stop-after-first-merge` so bounded smoke tests can land one PR and exit before follow-up maintain/proof agents spend more tokens.
- Added `scripts/estimate_openrouter_budget.py`, `docs/minimal-context-budget-plan.md`, and three low-trust pilot JSONL records for the first FPS chapter. A live `qwen/qwen3-coder` extraction pass used 11,582 input tokens and 404 output tokens for `$0.0038658`; the observed OpenRouter balance was about `$7.42`.
- Added `scripts/review_minimal_context_records.py` plus focused tests. A live `qwen/qwen3-coder` review of all three records used 11,321 prompt tokens and 1,298 completion tokens for `$0.004827`; the records were updated with missing dependencies and reviewer notes.
- A live `deepseek/deepseek-v4-pro` reviewer attempt used 13,819 prompt tokens and 12,288 completion tokens for `$0.016702`, but produced parse-error rows because the model returned empty content after hidden reasoning.

## Next Steps
- Rerun a clean bounded toy smoke with `--stop-after-first-merge` when disk space permits or after reusing/cleaning the existing `/tmp/repoprover-toy-gemini3-flash` tree carefully.
- Replace broad `Mathlib` imports in the pilot records with exact module-level context, then rerun `scripts/review_minimal_context_records.py --model qwen/qwen3-coder`.
- If continuing planning, use `scripts/estimate_openrouter_budget.py` after each run to recompute costs from actual token logs and live OpenRouter pricing.
