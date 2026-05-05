# Cheap Autoformalization Iteration Plan

Date: 2026-05-05

## Objective

Validate whether RepoProver can cheaply iterate from the gold-standard
minimal-context dataset toward feed-forward textbook formalization.

The current source-statement benchmark is still oracle-assisted: the source
span and prefix Lean context come from the gold records, and the hidden target
Lean statement is used only by the grader. The next useful goal is not a single
large spend. It is to spend the remaining autonomous OpenRouter budget only on
experiments that decide which missing pipeline pieces matter most.

## Current Best Pipeline

Use `scripts/run_source_statement_live_eval.py` with:

- target Lean statement and target declaration name withheld;
- source chunk, local prefix context, local style/API examples, and current
  Lean/mathlib migration guidance in the prompt;
- `--include-record-imports` so local imported modules are copied and built;
- `--repair-attempts 1` so generated-only compiler failures can trigger one
  repair prompt without exposing grader feedback.

First-pass prompting alone is not enough on the current diagnostic slice. The
best measured recipe is first pass plus one generated-only repair round.

## Budget Envelope

Treat `$7` as the total autonomous research spend envelope, not as the desired
size of any final run. Keep at least `$1` unspent for follow-up diagnostics.

API-free estimate from:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --output /tmp/repoprover-source-statement-budget-80-repair1 \
  --limit 80 \
  --sample-mode stratified-easy \
  --include-record-imports \
  --repair-attempts 1 \
  --max-tokens 32768 \
  --max-actual-cost-usd 7 \
  --budget-only
```

Result: 80 selected records, 0 paid calls, estimated reserved max `$4.774908`
for one initial call plus one reserved repair call per record. This is a
conservative max-token reservation; actual prior DeepSeek calls used much less
than the cap.

## Spend Gates

1. Run a 12-record stratified-easy live probe with repair enabled and a hard
   cap of `$0.80`.
2. Stop early if fewer than half of completed records pass after six paid
   records, or if failures are dominated by one repeated prompt/context bug.
3. If the 12-record probe reaches at least 50% success and no benchmark leak is
   found, run a 40-record stratified-easy probe with a hard cap of `$3.00`.
4. Spend any remaining budget on the highest-frequency failure class only:
   local context selection, current Mathlib API retrieval, or repair prompt
   shape.

Suggested first live command:

```bash
bash -ic 'UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --output /tmp/repoprover-source-statement-live-12-repair1-$(date -u +%Y%m%dT%H%M%SZ) \
  --limit 12 \
  --sample-mode stratified-easy \
  --include-record-imports \
  --lake-cache-from algebraic-combinatorics \
  --reuse-project \
  --repair-attempts 1 \
  --max-tokens 32768 \
  --max-actual-cost-usd 0.80 \
  --concurrency 1'
```

Before any paid run, use the same selected shape in verifier preflight mode:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --output /tmp/repoprover-source-statement-preflight-12-reuse \
  --limit 12 \
  --sample-mode stratified-easy \
  --include-record-imports \
  --lake-cache-from algebraic-combinatorics \
  --reuse-project \
  --preflight-only \
  --lean-timeout 90 \
  --concurrency 1
```

For recoverable paid generation logs, decouple provider calls from Lean checks
and write generation artifacts directly under a git-trackable run directory:

```bash
bash -ic 'UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records /tmp/repoprover-source-statement-preflight-passing-6.jsonl \
  --output docs/source-statement-runs/2026-05-05-preflight-passing-6-generation \
  --limit 6 \
  --sample-mode corpus-spread \
  --generation-only \
  --repair-attempts 0 \
  --max-tokens 32768 \
  --max-actual-cost-usd 0.30 \
  --concurrency 3'
```

That mode records `openrouter-payload.json`, `openrouter-response.json`,
`openrouter-cost-summary.json`, `model-assistant-content.txt`,
`model-output.json`, and `generated-lean-declaration.lean` for each paid row,
without creating Lean project trees. Lean verification should consume those
artifacts separately with a pool of reusable materialized projects:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/verify_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-preflight-passing-6-generation \
  --work-root /tmp/repoprover-source-statement-verify-preflight-passing-6 \
  --include-record-imports \
  --lake-cache-from algebraic-combinatorics \
  --workers 1 \
  --lean-timeout 90
```

Use `--workers 1` by default. It keeps verification simple, uses one reusable
Lean project, and still records a separate result for every generated
declaration instead of stopping at the first failure. On the six-record
generation probe, serial verification took `172.92s` total, about `29s` per
record, and the reusable verifier work tree was about `20M`. More workers are a
later throughput optimization, not needed for small probes.

## Missing Pipeline Tasks

- Context picking validation: compare the gold minimal context against cheaper
  automatic selectors before larger source-statement spend. Measure whether the
  selected source spans, file-context commands, local imports, and predecessor
  declarations are sufficient to compile the hidden statement when the target
  statement is known only to the verifier.
- Domain API retrieval: add a small retrieval layer for current Mathlib/local
  API snippets when failures mention stale names or stuck typeclass inference.
- Repair loop promotion: the runner now supports one or more generated-only
  repair attempts, but larger live runs should report initial-vs-repaired
  success separately before treating repair as part of the baseline.
- Feed-forward ordering: once the oracle source-statement benchmark mostly
  succeeds, switch from independent records to file-order generation where
  accepted generated statements become candidate predecessors for later records.

## Trust Scoring Boundary

Do not implement trust scoring yet. The user requested it only after the
iterative textbook pipeline mostly succeeds.

When that gate is reached, each generated declaration should enter the
dependency graph with a trust score derived from:

- whether it passed generated-only compile;
- whether it proved the hidden gold statement by `simpa using ...`;
- whether later records depended on it successfully;
- whether later failures produce evidence that the statement was too weak,
  over-generalized, or semantically mismatched.

Later failures should be able to open an investigation task on earlier generated
statements rather than assuming every prior compiled theorem is fully faithful.
