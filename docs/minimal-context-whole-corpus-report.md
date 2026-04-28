# Whole-Corpus Minimal Context Deliverable

Generated on 2026-04-28 with `scripts/generate_context_graph.py`.

## Deliverable Status

The repo now has a complete deterministic context graph and declaration-level
minimal-context collection for the vendored Algebraic Combinatorics book and
formalization snapshot.

- Graph: `docs/minimal-context-graph.json`
- Records: `docs/minimal-context-full-records.jsonl`
- Format contract: `docs/minimal-context-format.md`
- Generator: `scripts/generate_context_graph.py`

Regeneration command:

```bash
uv run python scripts/generate_context_graph.py \
  --project-root algebraic-combinatorics \
  --graph-output docs/minimal-context-graph.json \
  --records-output docs/minimal-context-full-records.jsonl
```

The generator is local-only, deterministic, and cost-free: it does not call
OpenRouter, GitHub, or Lean.

## Current Corpus Summary

Latest generated summary:

```json
{
  "edge_count": 57342,
  "lean_declaration_count": 5684,
  "node_count": 9914,
  "record_count": 5684,
  "source_alignment_methods": {
    "lean_comment_label": 1036,
    "manifest_position_fallback": 4427,
    "unmapped": 221
  },
  "source_label_count": 4107,
  "unresolved_or_low_trust_count": 4648
}
```

The JSONL collection has one record for every named declaration parsed from the
formalization:

- 2,402 theorems
- 2,070 lemmas
- 1,042 definitions
- 74 instances
- 60 abbrevs
- 30 structures
- 6 inductives

## What Counts As Complete

Complete means every named Lean declaration has:

- an output file and inclusive line range;
- direct imports and transitive import closure;
- local predecessor context from nearby declarations;
- lexical predecessor links to prior declarations when the names occur in the
  output chunk;
- source context when the generator can infer it, with explicit trust and method
  metadata.

The graph also includes all TeX labels found under
`AlgebraicCombinatorics/tex/` and all source/Lean containment and context edges.

## Trust Boundary

This is a complete candidate collection, not a fully human-reviewed gold set.
The trust fields encode that distinction:

- `lean_comment_label` source spans have `source_span = 0.75`.
- `manifest_position_fallback` source spans have `source_span = 0.2`.
- `unmapped` source context has `source_span = 0.0`.
- dependency context is static and heuristic, so `lean_dependency_graph` remains
  low until checked against Lean proof dependencies or reviewed by a stronger
  model/human.

The high-quality reviewed seed remains
`docs/minimal-context-generated-records.jsonl`; the new full-corpus files are
the reproducible substrate for scaling that review process.
