# Proof-Lane Task unit-005

## Policy
Use only the visible source/context below. Do not inspect or infer hidden aligned Lean target declarations.

## Source
- ID: `AlgebraicCombinatorics/tex/SymmetricFunctions/PieriJacobiTrudi.tex:thm.sf.jt-e`
- Path: `AlgebraicCombinatorics/tex/SymmetricFunctions/PieriJacobiTrudi.tex`
- Labels: `thm.sf.jt-e`

```tex
\begin{theorem}
[Second Jacobi--Trudi formula]\label{thm.sf.jt-e}Let $\lambda$ and $\mu$ be
two partitions. Let $\lambda^{t}$ and $\mu^{t}$ be the transposes of $\lambda$
and $\mu$. Let $M\in\mathbb{N}$ be such that both $\lambda^{t}$ and $\mu^{t}$
have length $\leq M$. We extend the partitions $\lambda^{t}$ and $\mu^{t}$ to
$M$-tuples (by inserting zeroes at the end). Write these $M$-tuples
$\lambda^{t}$ and $\mu^{t}$ as $\lambda^{t}=\left(  \lambda_{1}^{t}%
,\lambda_{2}^{t},\ldots,\lambda_{M}^{t}\right)  $ and $\mu=\left(  \mu_{1}%
^{t},\mu_{2}^{t},\ldots,\mu_{M}^{t}\right)  $. Then,%
\[
s_{\lambda/\mu}=\det\left(  \left(  e_{\lambda_{i}^{t}-\mu_{j}^{t}%
-i+j}\right)  _{1\leq i\leq M,\ 1\leq j\leq M}\right)  .
\]

\end{theorem}
```

## Current Outcome
- Generation status: `cannot_prove_from_visible_context`
- Verification failure class: `declined_cannot_prove`
- Reported status: `cannot_prove_from_visible_context`

## Model Notes
- The theorem statement is incomplete; the proof is missing. The definition of jacobiTrudiMatrixE uses esymm with a nonnegative index via .toNat, assuming the index is nonnegative. The selector sketch mentions transpose partitions, but the current formalization uses lam, mu directly; the transpose aspect is not captured. The proof would likely use the first Jacobi-Trudi formula and the omega involution.

## Task
Try to produce complete Lean declarations from the visible context. If the context is still insufficient, record the missing checked facts precisely.
