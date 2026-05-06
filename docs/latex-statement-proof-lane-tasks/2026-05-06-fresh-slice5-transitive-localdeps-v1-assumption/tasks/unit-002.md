# Proof-Lane Task unit-002

## Policy
Use only the visible source/context below. Do not inspect or infer hidden aligned Lean target declarations.

## Source
- ID: `AlgebraicCombinatorics/tex/FPS/DividingFPS.tex:cor.fps.invertible.field`
- Path: `AlgebraicCombinatorics/tex/FPS/DividingFPS.tex`
- Labels: `cor.fps.invertible.field`

```tex
\begin{corollary}
\label{cor.fps.invertible.field}Assume that $K$ is a field. Let $a\in K\left[
\left[  x\right]  \right]  $. Then, the FPS $a$ is invertible in $K\left[
\left[  x\right]  \right]  $ if and only if $\left[  x^{0}\right]  a\neq0$.
\end{corollary}
```

## Current Outcome
- Generation status: `generated`
- Verification failure class: `compile_failure`
- Reported status: `generated`

## Model Notes
- Uses PowerSeries.isUnit_iff_constantCoeff from Mathlib; the field condition is used to convert IsUnit (constantCoeff a) to constantCoeff a ≠ 0 via Units.ne_zero and Units.mk0.

## Task
Try to produce complete Lean declarations from the visible context. If the context is still insufficient, record the missing checked facts precisely.
