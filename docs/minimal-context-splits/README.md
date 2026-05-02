# Minimal Context Benchmark Splits

Generated at: `2026-05-02T16:59:06.325934+00:00`
Input: `docs/minimal-context-gold-candidates.jsonl`
Input records: 645
Schema: `repoprover.minimal_context_splits.v1`

These splits separate oracle proof-fill examples from stricter evaluation tracks. The goal is to make leakage explicit so a 100% score says what capability was actually bought.

## `oracle_proof_fill`

- File: `oracle_proof_fill.jsonl`
- Records: 645
- Leakage levels: `{'oracle_upper_bound': 645}`
- Allowed context policy: May include target-derived TeX/source spans, target-derived Lean file context, and selected Lean predecessors from the current minimal-context record.
- Target policy: Lean target statement/skeleton is available with proof/body replaced by sorry.
- Estimated use: Upper-bound proof-fill/great-context benchmark. If a system gets 100%, it can fill proofs when a strong oracle has already selected the relevant statement and context.
- Limitations:
  - Not an honest autoformalization benchmark: minimal_context was selected after seeing the target.
  - May reward using target/source labels and target-shaped Lean context.

## `oracle_source_statement`

- File: `oracle_source_statement.jsonl`
- Records: 645
- Leakage levels: `{'source_statement_oracle_prefix_lean': 645}`
- Allowed context policy: Selected target TeX/source span may be label-derived, but Lean context is restricted to imports, file-scope context, and predecessor chunks strictly before the target Lean range.
- Target policy: Target TeX/source chunk is available; target Lean statement should be withheld by consumers.
- Estimated use: Measures formalizing a known next mathematical text chunk into Lean using only prefix Lean dependencies.
- Limitations:
  - The source chunk can still be oracle-selected by a Lean comment label.
  - The JSON record retains output line ranges/declaration names for grading; prompts should not expose a target Lean statement.

## `prefix_next_declaration`

- File: `prefix_next_declaration.jsonl`
- Records: 645
- Leakage levels: `{'honest_prefix_with_documented_source_alignment_limitations': 645}`
- Allowed context policy: Lean context is prefix-only: file context and predecessor chunks must end strictly before the target in the same Lean file (or be from a lexicographically earlier Lean file when present in the input). TeX context is a window ending strictly before the aligned target source span; the target source span itself is withheld.
- Target policy: Next declaration identity is for grading only; target Lean statement and target source span should be withheld.
- Estimated use: Closest feed-forward split available from current records: predict the next Lean declaration from prior Lean and prior TeX context.
- Limitations:
  - Current records do not contain a full non-oracle TeX cursor, so the prefix TeX window is anchored by the target-aligned source span start.
  - Because that anchor is target-derived, this is not yet a fully certified feed-forward corpus split.
  - Only predecessor chunks already present in the input record can be retained; missing true dependencies are not recovered here.

## Important limitation for the prefix track

The current source records are aligned to target declarations by labels/comments. The prefix track withholds the target TeX span, but its source window is still anchored by the target-derived alignment point. It is therefore marked as target-derived in each source span and should be treated as a best-effort feed-forward split, not as a fully certified chronological corpus split.
