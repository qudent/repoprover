# NPartition Helper Route Diagnostic - 2026-05-06

This is a post-hoc diagnostic artifact. It uses the local Lean source only to
understand why source-only repair runs declined. It must not be used as
model-facing context for benchmark runs.

## Source Unit

- Source unit:
  `AlgebraicCombinatorics/tex/SymmetricFunctions/MonomialSymmetric.tex:prop.sf.Npar-as-par`
- Latest source-only retry:
  `docs/latex-statement-repair-loop-runs/2026-05-06-npartition-representation-control-v1-paid/`
- Latest result: clean `declined_cannot_prove`; gold comparison
  `not_generated_cannot_prove`

## What The Local Lean Source Shows

The existing Lean development uses the same high-level route that the selector
was approaching:

- convert a `Nat.Partition` to an `NPartition` by sorting `p.parts` in
  decreasing order and padding with zeros;
- prove the padded function is antitone using
  `Multiset.pairwise_sort` and `List.Pairwise.rel_get_of_le`;
- convert an `NPartition` back to a `Nat.Partition` by mapping over
  `Finset.univ.val` and filtering out zeros;
- prove the filtered-map length bound with `Multiset.card_le_card`,
  `Multiset.filter_le`, `Multiset.card_map`, and `simp` over `Finset.univ`;
- prove the padded construction has the right size using
  `Multiset.length_sort`, `Multiset.sort_eq`, `List.ofFn_get`,
  `List.sum_ofFn`, `Finset.sum_union`, `Finset.sum_eq_zero`, and
  `Finset.sum_map`.

The selector had already learned many of the names, but the generator's final
decline treated the unordered `Nat.Partition.parts : Multiset ℕ` representation
as if it fundamentally blocked the ordered tuple construction. The local source
shows that this is the wrong generic conclusion: canonicalizing an unordered
finite representation by sorting is a valid proof route when the required
sort/get/cardinality/sum facts are present.

## Generic Pipeline Lesson

For theorem-level units, context selection should not stop at "the source uses
an ordered tuple but Lean stores a multiset/finite set." It should sketch a
canonical representative when appropriate and request the facts needed for that
representative:

- sort or enumeration construction;
- orderedness or pointwise access lemmas;
- length/cardinality bounds for filtered or mapped finite data;
- sum-preservation and out-of-range zero-padding lemmas;
- same-unit helper statements that expose these obligations before the main
  theorem.

This lesson is generic and has been added to the repair-context and repair
generation prompts. The prompt change does not mention hidden target names or
the specific gold declarations.
