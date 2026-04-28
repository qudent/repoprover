# Minimal Context Data Format

This is the durable data contract for the whole-corpus minimal-context artifacts.

## Artifacts

- `docs/minimal-context-graph.json`: complete context graph for the vendored
  Algebraic Combinatorics source/formalization snapshot.
- `docs/minimal-context-full-records.jsonl`: one candidate minimal-context
  record per named Lean declaration.
- `docs/minimal-context-gold-candidates.jsonl`: deterministic higher-trust
  subset selected from the full records for the next review/smoke queue.
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
        "line_range": [154, 161],
        "labels": ["thm.binom.sym"],
        "reason": "Lean doc comment references this TeX label.",
        "method": "lean_comment_label"
      }
    ],
    "lean_predecessors": [
      {
        "path": "AlgebraicCombinatorics/FPS/NotationsExamples.lean",
        "declaration": "AlgebraicCombinatorics.FPS.binom_zero_of_lt",
        "line_range": [348, 353],
        "reason": "Nearest preceding declaration in the same Lean file.",
        "method": "local_predecessor_window"
      }
    ],
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
