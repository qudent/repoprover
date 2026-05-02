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
Remaining OpenRouter budget: about `$7.03` after the corrected April 28
semantic-review sample run; refresh credits before larger live runs.

## Current State
RepoProver is locally installed with Python in `.venv` and Lean/Lake through
`elan`. The Algebraic Combinatorics vendored snapshot has a deterministic
whole-corpus context graph, declaration-level minimal-context records, 645
exact-label gold candidates, and a 24-record semantic-review sample. Current
DeepSeek model choice remains `deepseek/deepseek-v4-pro`. A one-record
Mathlib-only evaluation pipeline now exists: it materializes a Lean target with
recorded TeX snippets, file-scope Lean context, predecessor snippets, and a
target `sorry`, then emits the exact DeepSeek/OpenRouter prompt payload and
review command without making paid calls by default.

## Active Goals
- [x] Generate a complete whole-corpus context graph and minimal-context
  collection with a documented reproducible pipeline and data format.
- [x] Feed selected records into a bounded RepoProver smoke so failures become
  concrete benchmark examples.
- [x] Mechanically review the 645 exact-label gold candidates at `$0.00` cost.
- [x] Create a deterministic 24-record semantic-review queue from accepted
  candidates.
- [x] Run a corrected live Qwen3.6 semantic review over the 24-record sample.
- [x] Build an API-free one-record minimal-context evaluation materializer and
  DeepSeek V4 Pro prompt/command emitter. An honest benchmark splitter now also
  writes leakage-aware oracle/source/prefix tracks under
  `docs/minimal-context-splits/`.

## TODO Plan
- [x] Add file-context-aware, Mathlib-only target materialization.
- [x] Add `scripts/run_minimal_context_eval.py` for selected-record JSONL,
  evidence, prompt payload, exact review/live command artifacts, and API-free
  DeepSeek V4 budget estimates.
- [x] Add API-free tests around materialization and eval artifact emission.
- [x] Add `scripts/split_minimal_context_benchmark.py` for leakage-aware
  `oracle_proof_fill`, `oracle_source_statement`, and
  `prefix_next_declaration` records plus manifest/report docs.
- [x] Estimate the current oracle proof-fill dataset cost: 473 theorem/lemma
  records selected, about 2.03M prompt tokens plus at most 3.87M completion
  tokens, estimated max `$4.2543` on `deepseek/deepseek-v4-pro` at current
  OpenRouter catalog pricing. No paid call was made because
  `OPENROUTER_API_KEY` is missing in this execution environment.
- [x] Run a live bounded `deepseek/deepseek-v4-pro` smoke with
  `--call-openrouter --max-tokens 32768` after loading `OPENROUTER_API_KEY`
  from interactive Bash startup without printing the secret. The first
  oracle-proof-fill record completed successfully and Lean-checked after
  materializer context-order/transitive-predecessor fixes; actual reported cost
  was `$0.002583465`.
- [ ] Next broader research step: design a model-selected segmentation task
  using the current best open-weight reviewer/critic as an adjudicator.

## Blockers
- Whole-corpus/gold-candidate records are machine-generated, not fully
  human-certified. The 24-record semantic-review sample is model-reviewed, not
  final gold.
- The eval runner now makes paid OpenRouter calls when `--call-openrouter` is
  explicit and `OPENROUTER_API_KEY` is loaded. In this Hermes environment the
  key is available through interactive Bash startup (`bash -ic`) rather than the
  default non-interactive shell; never print the secret value.
- Some materialized Mathlib-only projects may still expose missing non-local
  transitive Lean context in the record itself. Same-file predecessor
  dependencies are now expanded by the smoke materializer, and file-context
  commands are rendered in source order with predecessor snippets; imported-file
  or semantic dependencies can still be useful benchmark failures rather than
  script failures.
- Full `uv run pytest` still includes the vendored
  `algebraic-combinatorics/blueprint/test_docgen_data.py`, which fails because
  `../docbuild/.lake/build/doc/declarations/declaration-data.bmp` is absent.
  Focused repo tests passed.
## Recent Results
- `scripts/materialize_minimal_context_smoke.py` now defaults to
  `docs/minimal-context-gold-candidates.jsonl`, imports `Mathlib` only unless
  `--include-record-imports` is set, and materializes recorded `file_context`
  before predecessor snippets and the target `sorry`.
- Added `scripts/run_minimal_context_eval.py`. It writes
  `eval/selected-record.jsonl`, `eval/evidence.json`,
  `eval/openrouter-formalization-payload.json`,
  `eval/openrouter-formalization-cost-estimate.json`,
  `eval/openrouter-formalization-command.txt`, and `eval/review-command.txt`;
  `--budget-only` emits per-record API-free budget estimates.
- Documented the one-record DeepSeek eval flow in
  `docs/minimal-context-format.md`.
- Verified dry materialization from
  `docs/minimal-context-semantic-review-sample.jsonl` at
  `/tmp/repoprover-minimal-context-eval` and ran the review script with
  `--dry-run`; no API call was made.
- Focused validation passed with
  `UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run pytest
  tests/test_minimal_context_smoke_materializer.py
  tests/test_minimal_context_eval_runner.py
  tests/test_minimal_context_review.py`.
- Added `scripts/split_minimal_context_benchmark.py` and generated
  `docs/minimal-context-splits/{oracle_proof_fill,oracle_source_statement,prefix_next_declaration}.jsonl`
  plus `manifest.json`/`README.md` from the 645 candidate records. Focused split
  tests pass with `UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run pytest
  tests/test_split_minimal_context_benchmark.py`.
- Ran an API-free DeepSeek V4 budget estimate over
  `docs/minimal-context-splits/oracle_proof_fill.jsonl`: 473 selected proof-fill
  theorem/lemma records, 2,030,412 estimated prompt tokens, 3,874,816 max
  completion tokens, estimated max cost `$4.2543`; no paid calls because the
  OpenRouter key is missing in the default non-interactive shell.
- Ran a paid one-record DeepSeek V4 Pro oracle-proof-fill smoke for
  `PowerSeries.logbar_constantCoeff` with `--max-tokens 32768`: OpenRouter used
  4,257 prompt tokens and 841 completion tokens for `$0.002583465`; the returned
  Lean declaration `... := constantCoeff_logbar` compiles in the fixed generated
  project.

## Agent Notes
- `STATUS.md` is the single coordination source of truth for this repo;
- Whole-corpus deliverable artifacts are `docs/minimal-context-graph.json`,
  `docs/minimal-context-full-records.jsonl`,
  `docs/minimal-context-gold-candidates.jsonl`,
  `docs/minimal-context-splits/`,
  `docs/minimal-context-format.md`,
  `docs/minimal-context-whole-corpus-report.md`, and
  `scripts/generate_context_graph.py`.
- Static-review artifacts are
  `scripts/adversarial_review_gold_candidates.py` and
  `docs/minimal-context-gold-candidate-static-review.{jsonl,md}`.
- Semantic-review queue artifacts are
  `scripts/sample_minimal_context_semantic_review.py` and
  `docs/minimal-context-semantic-review-sample.{jsonl,md}`.
- Corrected semantic-review artifacts are
  `docs/minimal-context-semantic-review-qwen3.6-35b-a3b.{jsonl,md}` and
  `docs/minimal-context-semantic-review-analysis.md`.
- High-reasoning model-selection/probe notes are in
  `docs/minimal-context-high-reasoning-review-probe.md`; partial probe outputs
  are `docs/minimal-context-semantic-review-deepseek-v3.2-speciale-high.*`.
- `scripts/materialize_minimal_context_smoke.py` generates one-record smoke
  projects with snippet-only TeX, a single target `sorry`, pre-seeded
  `.repoprover/state.json`, and Mathlib-only imports by default. It renders
  file-context commands and predecessor snippets in original source order and
  expands same-file predecessor dependencies referenced by predecessor snippets;
  use `--lake-cache-from` to avoid another Mathlib download on this low-disk
  machine.
- `scripts/run_minimal_context_eval.py` is the DeepSeek V4 Pro one-record
  prompt/command emitter. It refuses paid calls unless `--call-openrouter` is
  passed and `OPENROUTER_API_KEY` is set.
- `docs/minimal-context-budget-plan.md` records the pilot schema, cost model,
  and execution strategy; keep concrete run commands and budget notes there or
  in this file, not in project-agnostic learnings.
- Use `scripts/estimate_openrouter_budget.py` after live runs to recompute costs
  from actual token logs and current OpenRouter pricing.
- The next Qwen-style smoke should keep the default
  `--max-consecutive-tool-errors 3`; lower `--max-iterations` only if the smoke
  target should be strictly budget-capped beyond the repeated-error guard.
