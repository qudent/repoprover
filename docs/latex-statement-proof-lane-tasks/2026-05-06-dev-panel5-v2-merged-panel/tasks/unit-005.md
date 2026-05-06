# Proof-Lane Task unit-005

## Policy
Use only the visible source/context below. Do not inspect or infer hidden aligned Lean target declarations.

## Source
- ID: `AlgebraicCombinatorics/tex/SymmetricFunctions/MonomialSymmetric.tex:prop.sf.Npar-as-par`
- Path: `AlgebraicCombinatorics/tex/SymmetricFunctions/MonomialSymmetric.tex`
- Labels: `prop.sf.Npar-as-par`

```tex
\begin{proposition}
\label{prop.sf.Npar-as-par}There is a bijection%
\begin{align*}
\left\{  \text{partitions of length }\leq N\right\}   &  \rightarrow\left\{
N\text{-partitions}\right\}  ,\\
\left(  \lambda_{1},\lambda_{2},\ldots,\lambda_{\ell}\right)   &
\mapsto\left(  \lambda_{1},\lambda_{2},\ldots,\lambda_{\ell}%
,\underbrace{0,0,\ldots,0}_{N-\ell\text{ zeroes}}\right)  .
\end{align*}

\end{proposition}
```

## Current Outcome
- Generation status: `cannot_prove_from_visible_context`
- Verification failure class: `declined_cannot_prove`
- Reported status: `cannot_prove_from_visible_context`

## Model Notes
- The visible context provides NPartition structure, toPartition, and filter_ne_zero_sum, but the bijection requires constructing an inverse map from Nat.Partition with parts.card ≤ N to NPartition N, proving antitone of the padded function, and proving left_inv and right_inv. The antitone proof requires case analysis on in-range vs out-of-range indices, using sortedness of the original partition parts. The checked fallback candidates (List.Pairwise.rel_get_of_le, List.sortedGE_iff_antitone_get, etc.) provide ingredients for the in-range case, but the full construction is complex and the visible context does not provide a direct lemma for the padded antitone function. The proof strategy note suggests a multi-step helper plan, but implementing it fully from the visible context is beyond the scope of a single repair step without additional project context or a preexisting bijection lemma.

## Task
Try to produce complete Lean declarations from the visible context. If the context is still insufficient, record the missing checked facts precisely.
