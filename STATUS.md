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
- `scripts/generate_minimal_context_records.py` generates new candidate records
  from real upstream TeX/Lean chunks, embedding generator spend, elapsed time,
  capped unreviewed trust, and LaTeX-only inferability.
- `docs/minimal-context-generated-records.jsonl` has four next-binomial
  candidate records generated from `Notations.tex` / `NotationsExamples.lean`.
- `docs/minimal-context-generated-review-qwen3-coder-report.md` audits those
  generated records; verdicts were revise, revise, reject, revise.
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
- The four generated records are also low trust. They are useful as
  failure-sensitive benchmark candidates, but the reviewer rejected the
  double-factorial support lemma record and requested revisions for the other
  three.
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
- Trust is now in the generated record format via `trust`, `generation`, and
  `tex_only_inferability`; keep status focused on project state, not per-record
  trust.
- Next decision point: revise the four generated records using the reviewer
  findings, especially separating textbook source insufficiency from Lean/API
  context insufficiency for double factorial and divisibility lemmas.
- Then generate the next 10-20 FPS records with the generator, preserving
  rejected/ugly cases instead of curating them away.
- After one larger generation/review batch, select the lowest-risk records
  (`binom_factorial_formula`-style direct Mathlib wrappers) for a bounded
  retrieval/prompt smoke; keep the double-factorial records as hard negatives.
- You should make decisions yourself in that timeframe, commit at decision points. bias for action, I can rewind if I don't like something.
- generate the gold standard set based on the real thing, using codex itself and scripts. Decide how wellreasoned and how easily generable this "minimal backwards context" (ie relevant text, relevant used lemmata, relevant previous formalization defs etc) is
- if you run out of context, start a new codex_commit_push as in ~/learnings/scripts/codex_wrap.sh until budget is spent
- make sure you have enough reasoning.

## Recent Results
- Added and live-tested `scripts/generate_minimal_context_records.py`.
  The committed generation pass produced four records for lines 202-261 of
  `NotationsExamples.lean`, costing `$0.006556` for 11,790 prompt and 2,201
  completion tokens.
- Ran a live adversarial Qwen review over the generated records, costing
  `$0.005059` for 10,681 prompt and 1,505 completion tokens. Including
  calibration/regeneration attempts, this session spent about `$0.037040` on
  OpenRouter.
- OpenRouter `z-ai/glm-5.1` completed the toy sketch/review/merge path; toy
  commits were `97c3bd9` sketch, `ed17e510` merge, and `eef1daf` follow-up
  issues.
- Provider-specific tool-call metadata is preserved in the shared tool loop, and
  a live `gemini-3-flash-preview` one-tool continuation smoke passes.
- Final Qwen review of the three updated pilot records cost about `$0.005024`
  for 11,793 prompt tokens and 1,350 completion tokens.
