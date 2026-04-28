# RepoProver - Status

## Current State
RepoProver is locally installed with Python and Lean/Lake available through
`.venv` and `elan`. The toy project has been validated end to end with
OpenRouter `z-ai/glm-5.1` through sketch, review, merge, and final `lake build`.
The current research thread is a minimal-context gold-standard pilot for using
the published Algebraic Combinatorics formalization as supervision for bounded
RepoProver runs.

`STATUS.md` is the single coordination source of truth for this repo. There is
no separate human-agent whiteboard; active prompts, review notes, open questions,
agent handoff notes, and TODOs belong here until resolved.

## Active Goal
Build a small, reviewed minimal-context benchmark and use it in a bounded
RepoProver smoke so failures become concrete examples for the next iteration.

## Current Assets
- `docs/minimal-context-budget-plan.md` describes the pilot scope, schema,
  OpenRouter cost estimates, and first execution plan.
- `docs/minimal-context-pilot-records.jsonl` has three first-FPS pilot records.
  They were extracted with `qwen/qwen3-coder`, reviewed with the same model, and
  hardened with missing dependencies and exact imports.
- `scripts/review_minimal_context_records.py` audits pilot records against
  published TeX and Lean snippets through OpenRouter.
- `scripts/estimate_openrouter_budget.py` recomputes model costs from token logs
  and current OpenRouter prices.
- `--stop-after-first-merge` bounds RepoProver smoke tests after the first
  approved PR lands and builds.

## Trust And Blockers
- The three pilot records are still low trust: no human has reviewed them, and
  their narrowed imports were checked only against isolated output ranges, not a
  full chapter integration.
- `deepseek/deepseek-v4-pro` is not useful as a reviewer at the current
  4,096 completion-token cap because live calls consumed hidden reasoning tokens
  and returned empty content.
- A clean bounded `gemini-3-flash-preview` toy run has not been rerun after the
  thought-signature transcript fix. The direct one-tool continuation smoke did
  pass.
- Disk and existing `/tmp/repoprover-toy-gemini3-flash` state need care before
  running another full toy smoke.

## TODO Plan For Human Review
- [ ] Decide whether the next milestone is a retrieval/prompt smoke using the
  three reviewed FPS records, or more record generation before integration.
- [ ] If using the three records now, define the smallest prompt/retrieval hook:
  how records are selected, where they are injected, and how token use is logged.
- [ ] Add a minimal implementation that can feed selected JSONL records into one
  bounded `repoprover run` without changing the broader coordinator contract.
- [ ] Run one cheap dry or narrow smoke first to verify formatting, prompt size,
  and record selection before spending on a live LLM build loop.
- [ ] Run one live `--stop-after-first-merge` smoke with the cheapest model that
  can plausibly complete the task, then save missing-context failures as new
  benchmark examples.
- [ ] After the smoke, update the record trust fields and this status file with
  what failed, what context was missing, and whether to scale to more FPS chunks.

## Recent Results
- OpenRouter `z-ai/glm-5.1` completed the toy sketch/review/merge path; toy
  commits were `97c3bd9` sketch, `ed17e510` merge, and `eef1daf` follow-up
  issues.
- Provider-specific tool-call metadata is preserved in the shared tool loop, and
  a live `gemini-3-flash-preview` one-tool continuation smoke passes.
- Final Qwen review of the three updated pilot records cost about `$0.005024`
  for 11,793 prompt tokens and 1,350 completion tokens.
