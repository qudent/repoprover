# RepoProver - Status
# Overall direction
As in AGENTS.md

Make as much autonomous progress as possible towards a publishable
minimal-context benchmark with the remaining roughly `$7` OpenRouter budget and
the requested 3 hour work window. Focus on generating a gold-standard set
from the real Algebraic Combinatorics formalization, using scripts plus Codex
judgment, while tracking spend/time and how inferable each needed backward
context item is from textbook LaTeX alone. Trust belongs in the benchmark data
format, not as loose status prose.

Avoid editing above the line except to preserve new human direction.
-------
Start time of work: <insert current time here when you start work>
Remaining openrouter budget: <insert remaining budget> $


## Current State
RepoProver is locally installed with Python in `.venv` and Lean/Lake through
`elan`. The toy project has completed a bounded sketch/review/merge path with
OpenRouter `z-ai/glm-5.1`, and the current research thread is a minimal-context
gold-standard pilot using the published Algebraic Combinatorics TeX/Lean corpus
as supervision for later bounded RepoProver runs.

## Active Goals
- [x] Validate local RepoProver, Lean, and at least one live provider path.
- [x] Build the first minimal-context pilot records and reviewer workflow.
- [x] Add a generator for candidate records from real upstream TeX/Lean chunks.
- [ ] Revise generated records into a cleaner low-trust benchmark seed set.
- [ ] Scale generation/review to enough FPS chunks to expose recurring missing
  context patterns without curating away hard failures.
- [ ] Feed selected records into a bounded RepoProver smoke so failures become
  concrete benchmark examples.

## TODO Plan
- [ ] Apply the Qwen review findings to the four generated records, especially
  missing imports for `binom_neg_one`, explicit `k <= n` context for
  `binom_factorial_formula`, and separating TeX insufficiency from Lean/API
  insufficiency in the double-factorial records.
- [ ] Keep rejected or ugly cases in the dataset with explicit trust and review
  metadata; do not drop them just because they are bad examples.
- [ ] Generate the next 10-20 FPS records from real upstream chunks, tracking
  elapsed time, token usage, estimated OpenRouter cost, and
  `tex_only_inferability`.
- [ ] Review the larger batch with a cheap adversarial reviewer before spending
  on RepoProver runs.
- [ ] Select the lowest-risk direct Mathlib-wrapper records for the first
  retrieval/prompt smoke, while keeping double-factorial/divisibility records as
  hard negatives.
- [ ] Run a cheap formatting/dry smoke before any live bounded build loop.
- [ ] Run one live `--stop-after-first-merge` RepoProver smoke with enough model
  reasoning/context for Lean version, Mathlib API, and predecessor declarations.
- [ ] After each decision point, update this file and commit the coherent unit.

## Blockers
- Vendoring `facebookresearch/algebraic-combinatorics` is still blocked in the
  shell despite the latest user note about sandboxing: `git clone --depth 1
  https://github.com/facebookresearch/algebraic-combinatorics
  algebraic-combinatorics` failed with `Could not resolve host: github.com`,
  `getent hosts github.com` returned nothing, and direct-IP `curl` to GitHub
  could not connect. The GitHub connector can inspect individual files, but it
  does not provide a way to materialize a complete local checkout.
- The generated records are not yet human-reviewed and remain low trust by
  design; their trust fields must drive downstream selection.
- The latest Qwen review rejected `prod_odd_eq_doubleFactorial` and requested
  revisions for the other three generated records.
- `deepseek/deepseek-v4-pro` is not useful as a reviewer under the tested
  4,096 completion-token cap because live calls spent hidden reasoning tokens
  and returned empty content.
- A clean bounded `gemini-3-flash-preview` toy run has not been rerun after the
  thought-signature transcript fix, though the direct one-tool continuation
  smoke passed.
- Disk and existing `/tmp/repoprover-toy-gemini3-flash` state need care before
  another full toy or benchmark smoke.
## Recent Results
- Retried cloning the formalization repo after the user said the environment
  should now work without sandboxing; shell network is still blocked, no
  `algebraic-combinatorics/` directory was created, and there is nothing to
  remove under `.git` or commit as a vendored checkout.
- Attempted to clone the formalization repo into `algebraic-combinatorics/`;
  no files were created because local network access to GitHub is unavailable.
- Added a root `AGENTS.md` contributor guide covering repo layout, `uv`/pytest
  commands, toy Lean smoke testing, coding style, and PR expectations.
- Added and live-tested `scripts/generate_minimal_context_records.py`; the
  committed generation pass produced four records for lines 202-261 of
  `NotationsExamples.lean`, costing about `$0.006556`.
- Ran a live adversarial Qwen review over those generated records; verdicts
  were revise, revise, reject, revise, costing about `$0.005059`.
- Including calibration and regeneration attempts, the generator/reviewer work
  in the last committed session spent about `$0.037040` on OpenRouter.
- Earlier toy validation succeeded with OpenRouter `z-ai/glm-5.1`; toy commits
  were `97c3bd9` sketch, `ed17e510` merge, and `eef1daf` follow-up issues.

## Agent Notes
- `STATUS.md` is the single coordination source of truth for this repo;
- Main benchmark artifacts are `docs/minimal-context-pilot-records.jsonl`,
  `docs/minimal-context-generated-records.jsonl`, and
  `docs/minimal-context-generated-review-qwen3-coder-report.md`.
- `docs/minimal-context-budget-plan.md` records the pilot schema, cost model,
  and execution strategy; keep concrete run commands and budget notes there or
  in this file, not in project-agnostic learnings.
- Use `scripts/estimate_openrouter_budget.py` after live runs to recompute costs
  from actual token logs and current OpenRouter pricing.
