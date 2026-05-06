# Proof-Lane Task unit-001

## Policy
Use only the visible source/context below. Do not inspect or infer hidden aligned Lean target declarations.

## Source
- ID: `AlgebraicCombinatorics/tex/Details/InfiniteProducts1.tex:lem.fps.prod.irlv.cong-div`
- Path: `AlgebraicCombinatorics/tex/Details/InfiniteProducts1.tex`
- Labels: `lem.fps.prod.irlv.cong-div`

```tex
\begin{lemma}
\label{lem.fps.prod.irlv.cong-div}Let $a,b,c,d\in K\left[  \left[  x\right]
\right]  $ be four FPSs such that $c$ and $d$ are invertible. Let
$n\in\mathbb{N}$. Assume that
\[
\left[  x^{m}\right]  a=\left[  x^{m}\right]  b\ \ \ \ \ \ \ \ \ \ \text{for
each }m\in\left\{  0,1,\ldots,n\right\}  .
\]
Assume further that%
\[
\left[  x^{m}\right]  c=\left[  x^{m}\right]  d\ \ \ \ \ \ \ \ \ \ \text{for
each }m\in\left\{  0,1,\ldots,n\right\}  .
\]
Then,
\[
\left[  x^{m}\right]  \dfrac{a}{c}=\left[  x^{m}\right]  \dfrac{b}%
{d}\ \ \ \ \ \ \ \ \ \ \text{for each }m\in\left\{  0,1,\ldots,n\right\}  .
\]

\end{lemma}
```

## Current Outcome
- Generation status: `cannot_prove_from_visible_context`
- Verification failure class: `declined_cannot_prove`
- Reported status: `cannot_prove_from_visible_context`

## Model Notes
- The lemma xnEquiv_mul_of_coeff_eq failed to compile due to missing Semiring K instance. The visible context does not provide a working lemma for coefficient-wise equality of products, and no lemma for coefficient-wise equality of inverses is available. The source requires a lemma that if c and d are units with equal coefficients up to n, then their inverses also have equal coefficients up to n, which is not available in the visible context. The checked signature PowerSeries.coeff_inv is over fields, not general commutative rings with IsUnit, and cannot be used here.

## Task
Try to produce complete Lean declarations from the visible context. If the context is still insufficient, record the missing checked facts precisely.
