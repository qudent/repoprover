# RepoProver - Status
## Overall direction
We want to build a gold standard "minimal context" dataset from this repo+formalization, so that we can iterate graph for this formalization and learn how to replicat the previous 100k$ autoformalization for much cheaper with open models or so. The idea is to get a "gold standard" dataset that we can iterate on with cheap models.

## Next autonomous deliverable

Next autonomous deliverable:
Clean up the algebraic combinatorics repo (and write into algebraic-combinatorics/CLEANUP_NOTE.md what you did) as follows: Remove duplicate latex source (eg summarized files that repeat the original chapter texts). Step after that: Make a 'gold standard' dataset mapping each output chunk of lean (at the appropriate level - maybe lemma or so? make choice yourself after looking) to the minimal context necessary to produce it - so, previous latex snippets, and previous lean formalizations that specify something necessary to know, with a mapping on a file:line levels. no circular dependencies. report how hard it would be to reproduce that. you can do that selection with a small model and verify. make a report how hard the "context selection" task is and what challenges you encountered. The "gold standard minimal context mapping generation task" should become replicable and cost tracked (as said, in a file format that maps lines to context). next autonomous deliverable is this gold standard dataset with mapping. Finish after you did that. Also make a report how much it cost, and how long it takes.

Deliverable: A minimal context mapping (mapping line regions/files to lines), and tooling to generate it. should use open source agents.

Avoid editing above the line except to preserve new human direction.
-------
Start time of work: 2026-04-28T15:52:46Z
Remaining openrouter budget: about 7.22 $ after the April 28 model refresh and
Qwen3.6 generation/review rerun; refresh credits before more live runs.


## Current State
RepoProver is locally installed with Python in `.venv` and Lean/Lake through
`elan`. The Algebraic Combinatorics vendored snapshot has been cleaned of
duplicate/generated blueprint chapter artifacts while retaining canonical
TeX/Lean sources. The requested deliverable now exists: a complete deterministic
whole-corpus context graph and declaration-level minimal-context collection for
the vendored book/formalization snapshot, plus a reproducible local generator
and documented data format. The reviewed 14-record seed remains the higher-trust
subset for model-evaluation experiments.
The first selected-record RepoProver smoke has also been run and recorded as a
concrete benchmark failure: the chosen context was sufficient, but
`qwen/qwen3-coder` repeatedly produced malformed tool-call/edit arguments and
was stopped before a PR was submitted. A deterministic high-trust candidate
filter now selects the exact-label, bounded-size, file/line-validated subset of
the whole-corpus records for the next review/smoke queue. Current OpenRouter
model selection has been refreshed from live catalog data: `qwen/qwen3-coder`
is historical, while `qwen/qwen3.6-35b-a3b` is now the default open-weight Qwen
model for minimal-context JSON generation/review. `Goedel-Prover-V2-32B` is the
best documented self-hosted Lean-prover candidate found in current research,
but it is not available in the OpenRouter catalog. The 863 deterministic gold
candidates now have a zero-cost static adversarial review pass: only 35 are
mechanically clean, 656 need predecessor-context narrowing, and 172 are rejected
for mechanical issues before semantic review.

## Active Goals
- [x] Validate local RepoProver, Lean, and at least one live provider path.
- [x] Build the first minimal-context pilot records and reviewer workflow.
- [x] Add a generator for candidate records from real upstream TeX/Lean chunks.
- [x] Revise generated records into a cleaner low-trust benchmark seed set.
- [x] Scale generation/review to enough FPS chunks to expose recurring missing
  context patterns without curating away hard failures.
- [x] Generate a complete whole-corpus context graph and minimal-context
  collection with a documented reproducible pipeline and data format.
- [x] Feed selected records into a bounded RepoProver smoke so failures become
  concrete benchmark examples.

## TODO Plan
- [x] Apply the Qwen review findings to the four generated records, especially
  missing imports for `binom_neg_one`, explicit `k <= n` context for
  `binom_factorial_formula`, and separating TeX insufficiency from Lean/API
  insufficiency in the double-factorial records.
- [x] Keep rejected or ugly cases in the dataset with explicit trust and review
  metadata; do not drop them just because they are bad examples.
- [x] Generate the next 10-20 FPS records from real upstream chunks, tracking
  elapsed time, token usage, estimated OpenRouter cost, and
  `tex_only_inferability`.
- [x] Review the larger batch with a cheap adversarial reviewer before spending
  on RepoProver runs.
- [x] Select the lowest-risk direct Mathlib-wrapper records for the first
  retrieval/prompt smoke, while keeping double-factorial/divisibility records as
  hard negatives.
- [x] Run a cheap formatting/dry smoke before any live bounded build loop.
- [x] Run one live `--stop-after-first-merge` RepoProver smoke with enough model
  reasoning/context for Lean version, Mathlib API, and predecessor declarations.
- [x] Add a low max-iteration or repeated-tool-error kill rule before running
  more open-model RepoProver smokes.
- [x] Filter the whole-corpus records into a higher-trust gold-candidate subset
  before using them as benchmark labels.
- [x] Refresh OSS model choices online and rerun batch-2 generation/review with
  a current OpenRouter Qwen model.
- [x] Optionally adversarially review the 863 gold candidates before treating
  them as final gold labels.

## Blockers
- The whole-corpus records are complete machine-generated candidates, not
  fully human-certified gold. Trust fields distinguish exact Lean-comment label
  matches from low-trust manifest-position fallbacks and unmapped Lean support
  files.
- Static adversarial review found that many apparent exact labels were TeX
  references rather than label definitions because the graph generator's label
  extractor accepts both `\label{...}` and `\ref{...}` tokens. Treat the 172
  rejected gold candidates as mechanically invalid until label extraction is
  separated.
- The canonical generated records are Qwen-reviewed but not human-reviewed; keep
  their trust fields low and use reviewer verdicts for downstream selection.
  The newer Qwen3.6 rerun is a comparison artifact, not a human-certified gold
  replacement.
- Current reviewed verdicts are 1 provisionally accepted, 9 revise, and 4
  reject. Rejected records are intentional hard negatives, not cleanup targets.
- `deepseek/deepseek-v4-pro` is not useful as a reviewer under the tested
  4,096 completion-token cap because live calls spent hidden reasoning tokens
  and returned empty content.
- `qwen/qwen3.6-35b-a3b` and `qwen/qwen3.6-27b` returned empty content on the
  first JSON generation request unless OpenRouter reasoning was disabled. Use
  `--reasoning-effort none` for schema-bound generation/review scripts.
- A clean bounded `gemini-3-flash-preview` toy run has not been rerun after the
  thought-signature transcript fix, though the direct one-tool continuation
  smoke passed.
- Disk and existing `/tmp/repoprover-toy-gemini3-flash` state need care before
  another full toy or benchmark smoke; accidental `.lake` cache under the
  vendored snapshot was removed after cleanup.
- `qwen/qwen3-coder` is not currently reliable for this prover/tool loop even
  on the trivial `binom_zero_of_lt` record: it found the right Mathlib theorem
  but repeatedly called `lean_check`/`file_edit` with malformed strings such as
  `{'n': 'ℕ'}`. Treat this as a model/tool-use failure, not a context-selection
  failure.
- The full `uv run pytest` suite currently includes the vendored
  `algebraic-combinatorics/blueprint/test_docgen_data.py`, which fails because
  `../docbuild/.lake/build/doc/declarations/declaration-data.bmp` is not
  present. The repo-local focused tests passed.
## Recent Results
- Removed duplicate/generated blueprint artifacts from
  `algebraic-combinatorics/` and documented the cleanup in
  `algebraic-combinatorics/CLEANUP_NOTE.md`; vendored tree is about 23 MB.
- Folded the first Qwen review into `docs/minimal-context-generated-records.jsonl`
  while preserving the rejected double-factorial case as a hard negative.
- Generated 10 additional `NotationsExamples.lean` records for lines 263-370
  with `qwen/qwen3-coder`, costing about `$0.014325`, then reviewed them with
  Qwen for about `$0.010873`.
- Canonical generated dataset now has 14 records, generation cost `$0.020880`,
  review cost `$0.015932`, and total recorded token-estimated cost `$0.036813`.
- Added `docs/minimal-context-generation-report.md` summarizing artifacts, cost,
  elapsed time, review outcomes, and context-selection difficulty.
- Added `scripts/generate_context_graph.py`, which deterministically emits
  `docs/minimal-context-graph.json` and
  `docs/minimal-context-full-records.jsonl` from local vendored sources with no
  network/model spend.
- Removed duplicate aggregate TeX sources
  `AlgebraicCombinatorics/tex/all.tex` and
  `AlgebraicCombinatorics/tex/detnotes.tex`; regenerated the graph/records so
  no context span points at either file.
- Current whole-corpus generation produced 5,684 declaration records, 812 TeX
  labels, 6,617 graph nodes, and 54,047 graph edges in about 23 seconds. Source
  alignment methods: 1,034 `lean_comment_label`, 4,429
  `manifest_position_fallback`, 221 `unmapped`.
- Added `docs/minimal-context-format.md`,
  `docs/minimal-context-whole-corpus-report.md`, and focused generator tests;
  `uv run pytest tests/test_context_graph_generation.py
  tests/test_minimal_context_review.py` passed, and graph/JSONL validation
  passed.
- Added `scripts/materialize_minimal_context_smoke.py` and tests, then
  materialized `/tmp/repoprover-minctx-binom-zero` from
  `ac-notations-and-elementary-facts-examples:binom_zero_of_lt`; RepoProver
  status showed 1/1 chapters sketched and `lake env lean` compiled with the
  expected single `sorry` warning.
- Ran a bounded live OpenRouter smoke with `qwen/qwen3-coder`; it was stopped
  after repeated malformed `lean_check`/`file_edit` calls. Logs are under
  `/tmp/repoprover-minctx-binom-zero/runs/20260428-164407/`, and
  `scripts/estimate_openrouter_budget.py` estimates 245,172 input tokens,
  2,000 output tokens, and `$0.05753784` cost.
- Added a shared repeated-tool-error kill rule to `run_tool_loop`: by default,
  three consecutive identical failing tool calls stop the agent with
  `repeated_tool_error`. `repoprover run` now also exposes `--max-iterations`
  and `--max-consecutive-tool-errors`.
- Verified the guard with `uv run pytest tests/test_tool_loop.py
  tests/test_recording.py` and `uv run python -m repoprover run --help`; full
  `uv run pytest` got 282 passing tests plus the unrelated missing-docbuild
  vendored blueprint failure.
- Added `scripts/filter_minimal_context_gold_candidates.py`, which selects
  863 exact `lean_comment_label` records from the 5,684-record whole corpus
  with valid file/line spans and bounded context size. Outputs are
  `docs/minimal-context-gold-candidates.jsonl` and
  `docs/minimal-context-gold-candidates-report.md`; model/API cost was `$0.00`.
- Verified the selector and adjacent minimal-context helpers with
  `uv run pytest tests/test_minimal_context_gold_filter.py
  tests/test_context_graph_generation.py tests/test_minimal_context_review.py`
  (14 passed).
- Earlier toy validation succeeded with OpenRouter `z-ai/glm-5.1`; toy commits
  were `97c3bd9` sketch, `ed17e510` merge, and `eef1daf` follow-up issues.
- Researched current model versions online and against the live OpenRouter
  catalog. Added `docs/open-model-research-2026-04-28.md`; Qwen3.6 is current,
  and specialized Lean provers found in the literature are not on OpenRouter.
- Updated minimal-context OpenRouter defaults from `qwen/qwen3-coder` or
  `deepseek/deepseek-v4-pro` to `qwen/qwen3.6-35b-a3b`; added
  `--reasoning-effort` to generation/review scripts and repaired JSON parsing
  for LaTeX backslashes in model output.
- Reran batch-2 generation with `qwen/qwen3.6-35b-a3b --reasoning-effort none`:
  10 records, 27,304 prompt / 7,115 completion tokens, estimated `$0.011269`.
  The Qwen3.6 review used 22,709 prompt / 7,729 completion tokens, estimated
  `$0.011121`, with verdicts 1 provisionally accepted, 6 revise, 3 reject.
- Added `scripts/adversarial_review_gold_candidates.py`, tests, and the
  generated review artifacts
  `docs/minimal-context-gold-candidate-static-review.{jsonl,md}`. The local
  pass reviewed all 863 selected candidates in under a second at `$0.00` model
  cost, with verdicts 35 provisionally accepted, 656 revise, and 172 reject.
  Issue categories were 170 source spans that cite a `\ref` rather than a
  defining `\label`, 4 incomplete Lean outputs containing `sorry`/`admit`, 2
  parsed line-range mismatches, 39 unrepresented doc-comment labels, and 2,069
  likely oversized predecessor entries.

## Agent Notes
- `STATUS.md` is the single coordination source of truth for this repo;
- Whole-corpus deliverable artifacts are `docs/minimal-context-graph.json`,
  `docs/minimal-context-full-records.jsonl`,
  `docs/minimal-context-gold-candidates.jsonl`,
  `docs/minimal-context-format.md`,
  `docs/minimal-context-whole-corpus-report.md`, and
  `scripts/generate_context_graph.py`.
- Gold-candidate selector artifacts are
  `scripts/filter_minimal_context_gold_candidates.py`,
  `docs/minimal-context-gold-candidates.jsonl`, and
  `docs/minimal-context-gold-candidates-report.md`. This subset is higher
  trust but not human-certified; dependency context remains heuristic.
- Main reviewed benchmark artifacts are `docs/minimal-context-pilot-records.jsonl`,
  `docs/minimal-context-generated-records.jsonl`, and
  `docs/minimal-context-generated-review-qwen3-coder-report.md`.
- Batch 2 artifacts are
  `docs/minimal-context-generated-records-batch2.jsonl`,
  `docs/minimal-context-generated-review-batch2-qwen3-coder.jsonl`, and
  `docs/minimal-context-generated-review-batch2-qwen3-coder-report.md`.
- Qwen3.6 refresh artifacts are
  `docs/open-model-research-2026-04-28.md`,
  `docs/minimal-context-generated-records-batch2-qwen3.6-35b-a3b.jsonl`,
  `docs/minimal-context-generated-review-batch2-qwen3.6-35b-a3b.jsonl`, and
  `docs/minimal-context-generated-review-batch2-qwen3.6-35b-a3b-report.md`.
- `docs/minimal-context-generation-report.md` is the current human-readable
  deliverable report for the minimal-context mapping seed set.
- `docs/minimal-context-repoprover-smoke-report.md` records the first
  selected-record RepoProver smoke and its Qwen tool-use failure.
- `scripts/materialize_minimal_context_smoke.py` generates one-record smoke
  projects with snippet-only TeX, a single target `sorry`, and pre-seeded
  `.repoprover/state.json`; use `--lake-cache-from` to avoid another Mathlib
  download on this low-disk machine.
- `algebraic-combinatorics/` is a vendored snapshot of
  `facebookresearch/algebraic-combinatorics` from commit
  `b6022318e986a0c20764569208ba8ebbe1c04dbf`; its nested `.git` directory was
  intentionally removed before commit.
- `docs/minimal-context-budget-plan.md` records the pilot schema, cost model,
  and execution strategy; keep concrete run commands and budget notes there or
  in this file, not in project-agnostic learnings.
- Use `scripts/estimate_openrouter_budget.py` after live runs to recompute costs
  from actual token logs and current OpenRouter pricing.
- The next Qwen-style smoke should keep the default
  `--max-consecutive-tool-errors 3`; lower `--max-iterations` only if the smoke
  target should be strictly budget-capped beyond the repeated-error guard.
