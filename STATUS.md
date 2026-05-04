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
DeepSeek model choice remains `deepseek/deepseek-v4-pro`. The stricter
target-statement-withheld source-eval runner now emits notation-aware Lean
prefix context, local style guidance, current Lean/mathlib environment guidance,
specific source-part focus metadata, and a bounded concurrent live-eval
supervisor path. Active dispatch follow-up is a manual/oracle-assisted repair
diagnostic for the documented failed source-statement record
`AlgebraicCombinatorics/CauchyBinet.lean:AlgebraicCombinatorics.CauchyBinet.det_diagonal_submatrix_eq`.

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
- [ ] Produce a reproducible manual/oracle-assisted diagnostic for the failed
  target-statement-withheld Cauchy--Binet record, preserving benchmark honesty
  by keeping the withheld gold Lean statement out of any model-facing prompt
  path and labeling gold inspection as diagnostic-only.

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
- [x] Start the stricter target-statement-withheld `oracle_source_statement`
  live eval path. Added tooling and ran initial DeepSeek V4 calls; first
  completed selected record failed under Lean, and lower caps returned no JSON
  because the model spent the completion budget on reasoning tokens.
- [x] Harden the source-statement prompt/context after the first Cauchy--Binet
  failure: include local notation support, local style examples, helper-name
  constraints, and specific multi-part source focus.
- [x] Add a non-blocking stratified/easier source-statement batch path with
  bounded concurrency, per-record timeouts, partial results, cost-cap guarding,
  and failure-class aggregation.
- [x] Completed the restarted remaining-5 source-statement batch after Hermes
  restart (`proc_cc541d87914d`, output
  `/tmp/repoprover-source-statement-concurrent-live-10b-resume-remaining5`).
  Across the interrupted+resumed 10-record stratified/easy run: 10 paid calls,
  0 successes, `$0.132727462` reported cost, failure classes
  `generated_lean_does_not_compile=9` and `grader_gold_statement_not_proved=1`.
- [x] Diagnosed the 10 failed source-statement attempts without more paid calls:
  failures were not just generic proof difficulty; several show stale/missing
  Lean API priors (`det_swap_rows`, `LaurentPolynomial.X`, `CommAlgebra`),
  invalid proposition/typeclass bundling, overly broad theorem statements, and
  some prompt/materialized-context noise such as duplicate predecessor snippets.
  Downloaded current mathlib v4.28.0 source to `/tmp/mathlib4-v4.28.0-src` for
  API/style lookup and added current Lean/mathlib environment/migration guidance
  to the live-eval prompt.
- [ ] Next broader research step: analyze whether context deduplication and
  mathlib/API retrieval snippets improve source-statement pass rate on a cheap
  dry/local diagnostic set before spending more on DeepSeek/OpenRouter.
- [ ] For the active repair handoff, create a small script/report that records
  the failed generated Lean evidence available from
  `docs/source-statement-live-eval-report.md`, the grader-only gold statement,
  the `simpa using <generated theorem>` semantic-equivalence criterion, and
  either a compiling improved check project or exact Lean/API blockers.

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
- The prior 10-record stratified/easy live artifacts are not present under
  `/tmp` in this session, so the active diagnostic uses the documented
  Cauchy--Binet fallback failure from `docs/source-statement-live-eval-report.md`.
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
- Added `scripts/run_source_statement_live_eval.py` and
  `docs/source-statement-live-eval-report.md` for the stricter
  target-statement-withheld source-to-Lean restart. A 30-record budget-only
  corpus-spread sample estimates 47,410 prompt tokens plus up to 983,040
  completion tokens at a 32,768 cap (`$0.8759` max). Initial live DeepSeek V4
  attempts completed only the first Cauchy--Binet record before being killed;
  it failed Lean verification at 32,768/high, while 8,192 and 4,096 caps
  returned no JSON content because all completion tokens were spent on
  reasoning. Completed live spend for these attempts was about `$0.0187`.
- Patched `scripts/run_source_statement_live_eval.py` so source-statement
  prompts include local Lean style guidance/examples, insert local notation
  support declarations into the Lean prefix context, forbid invented raw helper
  names, and focus multi-part source chunks on the specific record label (for
  Cauchy--Binet, `lem.det.minors-diag.a`). Added focused prompt tests and ran a
  one-record budget-only smoke; no paid provider call was made.
- Hardened `scripts/run_source_statement_live_eval.py` for live batches:
  `--concurrency` defaults to 4, `--sample-mode` supports `corpus-spread`,
  `easy`, and `stratified-easy`, each record writes independent payload/response
  artifacts, completed rows are streamed to `eval/partial-results.jsonl`, and
  the summary aggregates `failure_classes`. The global cost cap is checked
  before launching calls using estimated max cost plus in-flight reservations.
- API-free verification passed:
  `UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run pytest
  tests/test_source_statement_live_eval.py` and
  `UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python
  scripts/run_source_statement_live_eval.py --output
  /tmp/repoprover-source-statement-concurrency-budget --limit 10 --sample-mode
  stratified-easy --concurrency 4 --budget-only`; the smoke selected 10 records,
  wrote 10 partial-result rows, and made 0 paid calls.
- Patched `scripts/run_source_statement_live_eval.py` to persist paid model
  output explicitly: `record-NNN/model-assistant-content.txt` for raw assistant
  content, `record-NNN/model-output.json` for parsed JSON, and
  `record-NNN/generated-lean-declaration.lean` for the exact generated Lean
  declaration. Focused tests pass with
  `UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run pytest
  tests/test_source_statement_live_eval.py`.
- Reran one live `deepseek/deepseek-v4-pro` stratified-easy source-statement
  record with the persistence patch. Latest artifacts are in
  `/tmp/repoprover-source-statement-rerun-store-generated-cachefix-20260504T230856Z`;
  the stored generated Lean is `record-001/generated-lean-declaration.lean` for
  `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.sum_choose_pow_eq`.
  The paid call cost `$0.004565325`; success remained 0 because Lean checking
  ended in dependency setup noise (`git` exit 128 while cloning mathlib), so this
  run verifies artifact capture but is not an honest compile/grader result.
- Reran the documented Cauchy--Binet failure with `--sample-mode corpus-spread
  --limit 1` so the actual generated text is preserved. Artifacts are in
  `/tmp/repoprover-source-statement-cauchy-store-generated-20260504T231258Z`;
  the generated Lean declaration is `record-001/generated-lean-declaration.lean`
  and the raw assistant JSON is `record-001/model-assistant-content.txt`. The
  paid call cost `$0.008763075`; DeepSeek generated `det_sub_diagonal`, but Lean
  checking again failed before semantic grading because the local Mathlib package
  cache lacks built `Mathlib.olean` files (`unknown module prefix 'Mathlib'`).
  This run verifies exact Cauchy output capture, not a compile/grader result.
- Current dispatcher classified the target-statement-withheld follow-up as
  `active-orchestration`, selected the documented Cauchy--Binet failure because
  no prior 10-record `/tmp` artifacts were available, and verified the gold
  statement lives at
  `algebraic-combinatorics/AlgebraicCombinatorics/CauchyBinet.lean:3410`.

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
- `scripts/run_source_statement_live_eval.py` is the stricter source-statement
  live-eval runner: target Lean statement/name withheld from the prompt, source
  chunk provided, generated theorem checked against a grader-only gold
  statement. It now adds local notation support/style context, specific
  source-part focus metadata, persists raw and parsed model outputs plus the
  exact generated Lean declaration under each `record-NNN/`, uses bounded
  per-record concurrency, conservative cost-cap launch checks, partial-result
  streaming, and failure-class aggregation. Current live attempts and the
  concurrent command shape are documented in
  `docs/source-statement-live-eval-report.md`; avoid low completion caps because
  DeepSeek V4 can spend all returned tokens on reasoning and produce null
  content.
- `docs/minimal-context-budget-plan.md` records the pilot schema, cost model,
  and execution strategy; keep concrete run commands and budget notes there or
  in this file, not in project-agnostic learnings.
- Use `scripts/estimate_openrouter_budget.py` after live runs to recompute costs
- Active handoff should remain explicitly labeled manual/oracle-assisted:
  inspecting the withheld gold statement is allowed only as a diagnostic oracle,
  not as feed-forward benchmark input or a success claim in the model prompt.
  from actual token logs and current OpenRouter pricing.
- The next Qwen-style smoke should keep the default
  `--max-consecutive-tool-errors 3`; lower `--max-iterations` only if the smoke
  target should be strictly budget-capped beyond the repeated-error guard.
