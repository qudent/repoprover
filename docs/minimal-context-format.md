# Minimal Context Data Format

Status: legacy declaration-level format. The canonical generated JSON artifacts
(`docs/minimal-context-full-records.jsonl`,
`docs/minimal-context-gold-candidates.jsonl`,
`docs/minimal-context-graph.json`, and `docs/minimal-context-splits/`) were
retired from `main` after the LaTeX-statement dataset pivot. They are preserved
at `checkpoint/before-per-latex-statement-dataset` and
`checkpoint-before-per-latex-statement-dataset`.

This is the durable data contract for the whole-corpus minimal-context artifacts.

## Artifacts

- `docs/minimal-context-graph.json`: complete context graph for the vendored
  Algebraic Combinatorics source/formalization snapshot.
- `docs/minimal-context-full-records.jsonl`: one candidate minimal-context
  record per named Lean declaration.
- `docs/minimal-context-gold-candidates.jsonl`: deterministic higher-trust
  subset selected from the full records for the next review/smoke queue.
- `docs/minimal-context-splits/`: leakage-aware benchmark tracks generated from
  the candidate records, with a manifest/report and per-record policy metadata.
- `scripts/generate_context_graph.py`: deterministic generator. It uses only
  local files and makes no network or model calls.
- `scripts/filter_minimal_context_gold_candidates.py`: deterministic selector
  for exact-label, bounded-size, file/line-validated gold candidates.

Regenerate with:

```bash
uv run python scripts/generate_context_graph.py \
  --project-root algebraic-combinatorics \
  --graph-output docs/minimal-context-graph.json \
  --records-output docs/minimal-context-full-records.jsonl
```

Regenerate the higher-trust review queue with:

```bash
uv run python scripts/filter_minimal_context_gold_candidates.py \
  --input docs/minimal-context-full-records.jsonl \
  --output docs/minimal-context-gold-candidates.jsonl \
  --report-output docs/minimal-context-gold-candidates-report.md
```

Regenerate leakage-aware benchmark splits with:

```bash
uv run python scripts/split_minimal_context_benchmark.py \
  --input docs/minimal-context-gold-candidates.jsonl \
  --output-dir docs/minimal-context-splits
```

## JSONL Record Schema

Each line of `minimal-context-full-records.jsonl` is one declaration-level
record:

```json
{
  "id": "AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm",
  "chapter_id": "ac-notations-and-elementary-facts-examples",
  "output": {
    "lean_path": "AlgebraicCombinatorics/FPS/NotationsExamples.lean",
    "declaration_names": ["AlgebraicCombinatorics.FPS.binom_symm"],
    "line_range": [355, 360],
    "chunk_kind": "theorem"
  },
  "minimal_context": {
    "source_spans": [
      {
        "path": "AlgebraicCombinatorics/tex/FPS/Notations.tex",
        "line_range": [155, 185],
        "labels": ["thm.binom.sym"],
        "reason": "Lean doc comment references this TeX label.",
        "method": "lean_comment_label"
      }
    ],
    "lean_predecessors": [],
    "imports": ["Mathlib"],
    "import_closure": ["Mathlib"],
    "mathlib_context": [
      "Mathlib APIs referenced by imported modules; exact proof-level facts not statically certified."
    ]
  },
  "alignment": {
    "source_method": "lean_comment_label",
    "comment_labels": ["thm.binom.sym"],
    "paired_source_path": "AlgebraicCombinatorics/tex/FPS/Notations.tex"
  },
  "trust": {
    "source_span": 0.75,
    "lean_dependency_graph": 0.45,
    "model_extraction": 0.0,
    "human_review": 0.0
  },
  "review_notes": [],
  "generation": {
    "generator_version": "whole-corpus-context-graph-v1",
    "generator_kind": "deterministic_static_analysis"
  }
}
```

Line ranges are 1-indexed and inclusive. Paths are relative to
`algebraic-combinatorics/`.

## Graph Schema

`minimal-context-graph.json` has:

- `schema_version`: currently `repoprover.context_graph.v1`.
- `summary`: counts and alignment-method distribution.
- `nodes`: source files, TeX labels, Lean files, Lean declarations, and import
  modules.
- `edges`: typed links.
- `unresolved`: low-trust or unmapped records that need review before being
  called gold.

Main edge kinds:

- `contains`: file-to-label and file-to-declaration containment.
- `imports`: declaration-to-direct-import module.
- `source_context`: declaration-to-source label/file context.
- `lean_context`: declaration-to-predecessor declaration context.

## Alignment Methods

- `lean_comment_label`: highest-confidence deterministic source alignment. A
  Lean doc comment explicitly references a TeX label found in the source tree.
- `manifest_position_fallback`: low-trust alignment. The Lean file is paired to
  a manifest chapter and the source span is the nearest target label by relative
  position.
- `chapter_fallback`: very low-trust alignment to a whole TeX chapter.
- `unmapped`: no TeX chapter was inferred for the Lean file.

This whole-corpus collection is complete as a machine-generated candidate
dataset, not fully human-certified gold. Trust fields are intentionally low for
fallbacks so review and model-evaluation code can filter them.

## Gold Candidate Selection

`minimal-context-gold-candidates.jsonl` is a filtered subset, not a separate
human-certified dataset. The current selector keeps records with:

- exact `lean_comment_label` source alignment;
- non-empty labeled source spans using the same method;
- validated output, source, and predecessor file/line ranges;
- at most 80 total source lines, 50 output lines, and 10 Lean predecessors.

Selected rows include a top-level `selection` object documenting the selector
version, criteria, timestamp, and caveat. Skipped records remain in
`minimal-context-full-records.jsonl`; use the filter report for skipped-reason
counts.

## Leakage-Aware Benchmark Splits

`docs/minimal-context-splits/` is generated by
`scripts/split_minimal_context_benchmark.py`. It writes three JSONL tracks plus
`manifest.json` and `README.md`. Every split record keeps the original grading
fields and adds `benchmark_metadata` with `track`, `leakage_level`,
`allowed_context_policy`, `target_policy`, `estimated_use`, and `limitations`.

Tracks:

- `oracle_proof_fill`: the existing great-context/proof-fill setup. It is
  explicitly marked `oracle_upper_bound`; target Lean statement/skeleton and
  target-derived context are allowed.
- `oracle_source_statement`: target TeX/source chunk may still be selected from
  target labels, but Lean file context and predecessor chunks are filtered to
  ranges strictly before the target. Consumers should not expose the target Lean
  statement even though output fields remain for grading.
- `prefix_next_declaration`: best-effort feed-forward split. Lean context is
  prefix-only. TeX context is a prefix window before the aligned target source
  span, and the target source span is withheld. Because current records do not
  contain a non-oracle TeX cursor, the source-window anchor is still marked as
  target-derived in metadata; this is a documented limitation, not a certified
  leak-free corpus split.

## One-Record DeepSeek Evaluation

The minimal evaluation pipeline materializes a single benchmark project from
`docs/minimal-context-gold-candidates.jsonl` or
`docs/minimal-context-semantic-review-sample.jsonl`. The generated Lean target
imports `Mathlib` only by default, inserts recorded `file_context` lines such as
`open`, `namespace`, `section`, and `variable`, inserts predecessor Lean
snippets, and replaces the target body/proof with `sorry`.

Emit the exact DeepSeek V4 Pro prompt payload and review command without making
an OpenRouter call:

```bash
uv run python scripts/run_minimal_context_eval.py \
  --records docs/minimal-context-semantic-review-sample.jsonl \
  --project-root algebraic-combinatorics \
  --output /tmp/repoprover-minimal-context-eval \
  --force \
  --no-git
```

The output project contains:

- `eval/selected-record.jsonl`: the single record under test.
- `eval/evidence.json`: local TeX, file-context, predecessor, and target
  evidence assembled by the same helper used by
  `scripts/review_minimal_context_records.py`.
- `eval/openrouter-formalization-payload.json`: the exact OpenRouter chat
  payload for `deepseek/deepseek-v4-pro`.
- `eval/openrouter-formalization-cost-estimate.json`: tokenizer-free prompt
  size and max-cost estimate from the payload, using the current DeepSeek V4
  Pro OpenRouter price snapshot in the script.
- `eval/openrouter-formalization-command.txt`: the bounded live-call command.
- `eval/review-command.txt`: the exact DeepSeek review command using
  `scripts/review_minimal_context_records.py`.

For a small API-free batch budget report, use `--budget-only`; it does not
materialize a Lean project and does not call OpenRouter:

```bash
uv run python scripts/run_minimal_context_eval.py \
  --records docs/minimal-context-semantic-review-sample.jsonl \
  --project-root algebraic-combinatorics \
  --output /tmp/repoprover-oracle-context-deepseek-budget \
  --limit 5 \
  --max-tokens 8192 \
  --budget-only \
  --no-git
```

This writes `eval/openrouter-budget-estimate.{json,md}` with per-record prompt
chars, estimated prompt tokens, max-completion-token cost, and exact one-record
live commands. The latest checked-in small-batch report is
`docs/minimal-context-deepseek-live-batch-report.md`.

Only pass `--call-openrouter` for an explicit bounded paid smoke, and only when
`OPENROUTER_API_KEY` is set:

```bash
uv run python scripts/run_minimal_context_eval.py \
  --records docs/minimal-context-semantic-review-sample.jsonl \
  --project-root algebraic-combinatorics \
  --output /tmp/repoprover-minimal-context-eval \
  --force \
  --no-git \
  --call-openrouter \
  --max-tokens 8192 \
  --reasoning-effort high
```

After a live call, `eval/openrouter-response-cost-summary.json` records any
OpenRouter-reported actual cost from `usage.cost`/`usage.total_cost`; if the
response only has token counts, it also computes the estimated cost from the
same price snapshot.

Use `--include-record-imports` only when you want to evaluate with the record's
local import list instead of the stricter Mathlib-only baseline.
