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
and documented data format. The exact-label gold-candidate queue contains 645
bounded, file/line-validated records, and the zero-cost static adversarial
review now mechanically accepts all 645 before semantic review. The reviewed
14-record seed remains the higher-trust subset for model-evaluation
experiments. The first selected-record RepoProver smoke is a recorded benchmark
failure: context was sufficient, but `qwen/qwen3-coder` repeatedly produced
malformed tool-call/edit arguments and was stopped before PR submission.
Current OpenRouter model selection has been refreshed from live catalog data:
`qwen/qwen3.6-35b-a3b` is the default open-weight Qwen model for
minimal-context JSON generation/review with `--reasoning-effort none`.

## Active Goals
- [x] Generate a complete whole-corpus context graph and minimal-context
  collection with a documented reproducible pipeline and data format.
- [x] Feed selected records into a bounded RepoProver smoke so failures become
  concrete benchmark examples.
- [x] Mechanically review the 645 exact-label gold candidates at `$0.00` cost.

## TODO Plan
- [x] Clean duplicate/generated vendored TeX artifacts and document cleanup.
- [x] Build deterministic whole-corpus context graph and record format.
- [x] Generate and review the 14-record seed with cost tracking.
- [x] Filter 645 higher-trust exact-label gold candidates from 5,684 records.
- [x] Run static adversarial review over all 645 candidates at `$0.00` cost.
- [x] Run one selected-record RepoProver smoke and record the Qwen tool-loop
  failure.
- [ ] Next useful step: semantically review a small stratified sample from the
  645 mechanically accepted candidates, or try a bounded smoke with a stronger
  current model and the repeated-tool-error guard.

## Blockers
- The whole-corpus records are complete machine-generated candidates, not
  fully human-certified gold. Trust fields distinguish exact Lean-comment label
  matches from low-trust manifest-position fallbacks and unmapped Lean support
  files.
- The 645/645 static review only proves mechanical consistency. It normalizes
  Lean subpart labels to parent TeX labels and strips comments before scanning
  for `sorry`/`admit`; it does not prove semantic minimality.
- `qwen/qwen3.6-35b-a3b` and `qwen/qwen3.6-27b` returned empty content on the
  first JSON generation request unless OpenRouter reasoning was disabled. Use
  `--reasoning-effort none` for schema-bound generation/review scripts.
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
- Current whole-corpus artifacts: 5,684 declaration records, 790 TeX labels,
  6,573 graph nodes, and 40,436 graph edges. Source alignment methods: 1,062
  `lean_comment_label`, 4,400 `manifest_position_fallback`, 222 `unmapped`.
- Canonical reviewed seed: 14 `NotationsExamples.lean` records; recorded
  generation/review cost `$0.036813`. Qwen3.6 comparison rerun cost about
  `$0.022390` token-estimated.
- `docs/minimal-context-gold-candidates.jsonl` contains 645 exact-label,
  bounded records. `docs/minimal-context-gold-candidate-static-review.jsonl`
  now reports 645 `provisionally_accept`, 0 issue categories, `$0.00` model
  cost.
- Static reviewer false positives were fixed in
  `scripts/adversarial_review_gold_candidates.py`: parent TeX labels cover
  Lean subpart references, and `sorry`/`admit` checks ignore comments.
- Focused validation passed:
  `uv run pytest tests/test_minimal_context_static_adversarial_review.py`.

## Agent Notes
- `STATUS.md` is the single coordination source of truth for this repo;
- Whole-corpus deliverable artifacts are `docs/minimal-context-graph.json`,
  `docs/minimal-context-full-records.jsonl`,
  `docs/minimal-context-gold-candidates.jsonl`,
  `docs/minimal-context-format.md`,
  `docs/minimal-context-whole-corpus-report.md`, and
  `scripts/generate_context_graph.py`.
- Static-review artifacts are
  `scripts/adversarial_review_gold_candidates.py` and
  `docs/minimal-context-gold-candidate-static-review.{jsonl,md}`.
- Reviewed seed and comparison artifacts are in
  `docs/minimal-context-generated-records*.jsonl`,
  `docs/minimal-context-generated-review*.jsonl`, and
  `docs/open-model-research-2026-04-28.md`.
- `docs/minimal-context-repoprover-smoke-report.md` records the first
  selected-record RepoProver smoke and its Qwen tool-use failure.
- `scripts/materialize_minimal_context_smoke.py` generates one-record smoke
  projects with snippet-only TeX, a single target `sorry`, and pre-seeded
  `.repoprover/state.json`; use `--lake-cache-from` to avoid another Mathlib
  download on this low-disk machine.
- `docs/minimal-context-budget-plan.md` records the pilot schema, cost model,
  and execution strategy; keep concrete run commands and budget notes there or
  in this file, not in project-agnostic learnings.
- Use `scripts/estimate_openrouter_budget.py` after live runs to recompute costs
  from actual token logs and current OpenRouter pricing.
- The next Qwen-style smoke should keep the default
  `--max-consecutive-tool-errors 3`; lower `--max-iterations` only if the smoke
  target should be strictly budget-capped beyond the repeated-error guard.
