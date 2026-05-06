# Partial Proof Diagnostic Summary

- Generated at: `2026-05-06T13:32:48.119151+00:00`
- Generation runs: `docs/latex-statement-proof-lane-generation-runs/2026-05-06-fresh-slice5-unit001-decline-context-forced-paid-v1`
- Raw files: `1`
- Diagnosed units: `1`
- Diagnostic classes: `{'lean_errors_before_or_at_placeholder': 1}`

Interpretation: `lean_accepts_with_placeholder` means Lean accepted the visible-context body up to placeholders such as `sorry`; `lean_errors_before_or_at_placeholder` means a repair agent first needs concrete Lean/context fixes before finishing the proof.

## Units

| Unit | Class | Lean errors | Placeholders | Support | Raw output |
|---|---|---:|---|---:|---|
| unit-001 | `lean_errors_before_or_at_placeholder` | 38 | `sorry` | 42/42 | `docs/latex-statement-proof-lane-generation-runs/2026-05-06-fresh-slice5-unit001-decline-context-forced-paid-v1/batch-001/raw-generation-output.json` |

## unit-001

- Source unit: `AlgebraicCombinatorics/tex/Determinants/LGV2.tex:cor.lgv.catalan-hankel-det-0`
- Status: `cannot_prove_from_visible_context`
- Declaration names: `catalan_hankel_det_one`
- Used context: `catalanHankelMatrix, pathWeightMatrix, dyckDigraph_pathFinite, dyckUnitArcWeight, xDecreasing, yIncreasing, lgv_nonpermutable, catalanHankelMatrix_eq_pathWeightMatrix, nipatWeightSum, nipatFinset, pathTupleWeight`
- Contract violations: `cannot_prove_output_must_have_empty_lean_file_body, cannot_prove_output_must_have_empty_declaration_names, generated_lean_contains_placeholder`
- Visible support accepted/rejected: `42/0`
- Model notes:
  - The proof uses the LGV nonpermutable lemma to reduce the determinant to a sum over non-intersecting path tuples. The equality of the Catalan Hankel matrix to the path weight matrix is given by catalanHankelMatrix_eq_pathWeightMatrix. The sorting conditions for the source and target vertices are verified. The final simplification of the nipat weight sum to 1 requires additional lemmas about the structure of non-intersecting path tuples in the Dyck digraph with unit arc weights, which are not yet available in the visible context. The proof is incomplete at the last step.
- First Lean messages:
  - `error` line `17`: Redundant alternative: Any expression matching   north will match one of the preceding alternatives
  - `error` line `20`: Unknown identifier `LatticeStep`
  - `warning` line `23`: declaration uses `sorry`
  - `warning` line `24`: unused variable `p`  Note: This linter can be disabled with `set_option linter.unusedVariables false`
  - `error` line `51`: Unknown identifier `V`
  - `error` line `58`: Unknown identifier `V`
  - `error` line `74`: Unknown identifier `pathWeightAux`
  - `error` line `76`: Unknown identifier `V`
