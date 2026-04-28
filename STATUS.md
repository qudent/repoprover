# RepoProver - Status

## Current State
RepoProver is locally installed with Python and Lean/Lake available through
`.venv` and `elan`. The toy project has been validated end to end with
OpenRouter `z-ai/glm-5.1` through sketch, review, merge, and final `lake build`.
The current research thread is a minimal-context gold-standard pilot for using
the published Algebraic Combinatorics formalization as supervision for bounded
RepoProver runs.

`STATUS.md` is the single coordination source of truth for this repo.

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
This is a plan towards the goal "made as much progress as possible towards derisking and getting something publishable given the budget and time horizon I gave to you."
- Trust: the trust should be _in the data format of the gold standard set_, ie annotation of the generated lemmata in the final optimization loop, you don't need to put trust into STATUS.md
- I would recommend working on the gold standard set generation, keeping track of spend and time (ie probably first develop something, derisk with some pages, then higher...). you can generate it with python scripts, and yourself. Also check how hard the used context would be to infer from the textbook LaTeX only.
- You should make decisions yourself in that timeframe, commit at decision points. bias for action, I can rewind if I don't like something.
- generate the gold standard set based on the real thing, using codex itself and scripts. Decide how wellreasoned and how easily generable this "minimal backwards context" (ie relevant text, relevant used lemmata, relevant previous formalization defs etc) is
- if you run out of context, start a new codex_commit_push as in ~/learnings/scripts/codex_wrap.sh until budget is spent
- make sure you have enough reasoning.

## Recent Results
- OpenRouter `z-ai/glm-5.1` completed the toy sketch/review/merge path; toy
  commits were `97c3bd9` sketch, `ed17e510` merge, and `eef1daf` follow-up
  issues.
- Provider-specific tool-call metadata is preserved in the shared tool loop, and
  a live `gemini-3-flash-preview` one-tool continuation smoke passes.
- Final Qwen review of the three updated pilot records cost about `$0.005024`
  for 11,793 prompt tokens and 1,350 completion tokens.
