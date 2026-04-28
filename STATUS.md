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
Remaining openrouter budget: 7.287381 $


## Current State
RepoProver is locally installed with Python in `.venv` and Lean/Lake through
`elan`. The Algebraic Combinatorics vendored snapshot has been cleaned of
duplicate/generated blueprint chapter artifacts while retaining canonical
TeX/Lean sources. The requested deliverable now exists: a complete deterministic
whole-corpus context graph and declaration-level minimal-context collection for
the vendored book/formalization snapshot, plus a reproducible local generator
and documented data format. The reviewed 14-record seed remains the higher-trust
subset for model-evaluation experiments.

## Active Goals
- [x] Validate local RepoProver, Lean, and at least one live provider path.
- [x] Build the first minimal-context pilot records and reviewer workflow.
- [x] Add a generator for candidate records from real upstream TeX/Lean chunks.
- [x] Revise generated records into a cleaner low-trust benchmark seed set.
- [x] Scale generation/review to enough FPS chunks to expose recurring missing
  context patterns without curating away hard failures.
- [x] Generate a complete whole-corpus context graph and minimal-context
  collection with a documented reproducible pipeline and data format.
- [ ] Feed selected records into a bounded RepoProver smoke so failures become
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
- [ ] Select the lowest-risk direct Mathlib-wrapper records for the first
  retrieval/prompt smoke, while keeping double-factorial/divisibility records as
  hard negatives.
- [ ] Run a cheap formatting/dry smoke before any live bounded build loop.
- [ ] Run one live `--stop-after-first-merge` RepoProver smoke with enough model
  reasoning/context for Lean version, Mathlib API, and predecessor declarations.
- [ ] Optionally review/filter the whole-corpus fallback records into a higher
  trust gold subset before using them as benchmark labels.

## Blockers
- The whole-corpus records are complete machine-generated candidates, not
  fully human-certified gold. Trust fields distinguish exact Lean-comment label
  matches from low-trust manifest-position fallbacks and unmapped Lean support
  files.
- The canonical generated records are Qwen-reviewed but not human-reviewed; keep
  their trust fields low and use reviewer verdicts for downstream selection.
- Current reviewed verdicts are 1 provisionally accepted, 9 revise, and 4
  reject. Rejected records are intentional hard negatives, not cleanup targets.
- `deepseek/deepseek-v4-pro` is not useful as a reviewer under the tested
  4,096 completion-token cap because live calls spent hidden reasoning tokens
  and returned empty content.
- A clean bounded `gemini-3-flash-preview` toy run has not been rerun after the
  thought-signature transcript fix, though the direct one-tool continuation
  smoke passed.
- Disk and existing `/tmp/repoprover-toy-gemini3-flash` state need care before
  another full toy or benchmark smoke; accidental `.lake` cache under the
  vendored snapshot was removed after cleanup.
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
- Earlier toy validation succeeded with OpenRouter `z-ai/glm-5.1`; toy commits
  were `97c3bd9` sketch, `ed17e510` merge, and `eef1daf` follow-up issues.

## Agent Notes
- `STATUS.md` is the single coordination source of truth for this repo;
- Whole-corpus deliverable artifacts are `docs/minimal-context-graph.json`,
  `docs/minimal-context-full-records.jsonl`,
  `docs/minimal-context-format.md`,
  `docs/minimal-context-whole-corpus-report.md`, and
  `scripts/generate_context_graph.py`.
- Main reviewed benchmark artifacts are `docs/minimal-context-pilot-records.jsonl`,
  `docs/minimal-context-generated-records.jsonl`, and
  `docs/minimal-context-generated-review-qwen3-coder-report.md`.
- Batch 2 artifacts are
  `docs/minimal-context-generated-records-batch2.jsonl`,
  `docs/minimal-context-generated-review-batch2-qwen3-coder.jsonl`, and
  `docs/minimal-context-generated-review-batch2-qwen3-coder-report.md`.
- `docs/minimal-context-generation-report.md` is the current human-readable
  deliverable report for the minimal-context mapping seed set.
- `algebraic-combinatorics/` is a vendored snapshot of
  `facebookresearch/algebraic-combinatorics` from commit
  `b6022318e986a0c20764569208ba8ebbe1c04dbf`; its nested `.git` directory was
  intentionally removed before commit.
- `docs/minimal-context-budget-plan.md` records the pilot schema, cost model,
  and execution strategy; keep concrete run commands and budget notes there or
  in this file, not in project-agnostic learnings.
- Use `scripts/estimate_openrouter_budget.py` after live runs to recompute costs
  from actual token logs and current OpenRouter pricing.
