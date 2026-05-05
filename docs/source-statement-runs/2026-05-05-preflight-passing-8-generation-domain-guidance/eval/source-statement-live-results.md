# Source-statement live eval results

- Generated at: `2026-05-05T04:33:54.792872+00:00`
- Model: `deepseek/deepseek-v4-pro`
- Max tokens: `32768`
- Reasoning effort: `high`
- Repair attempts: `0`
- Repair max tokens: `32768`
- Repair reasoning effort: `high`
- Preflight only: `False`
- Generation only: `True`
- Reuse project: `False`
- Concurrency: `4`
- Sample mode: `corpus-spread`
- Global cost cap: `$0.350000`
- Records attempted: 8 / selected 8
- Successes: 0
- Success rate: 0.0%
- Preflight successes: 0 / 0
- Generation successes: 8 / 8
- Actual reported cost: `$0.051891`
- Failure classes: `{}`

Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.

| # | Result | Record | Generated name | Cost | Error / Lean output |
|---:|---|---|---|---:|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/InfiniteProducts2.lean:PowerSeries.comp_prod_infinite` | `subst_tprod` | $0.010469 |  |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `det_swap_cols` | $0.005988 |  |
| 3 | FAIL | `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.eq_of_embedUnivInBiv_eq` | `comp_y_coeff` | $0.003108 |  |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_subs_X_right` | `fps_subst_X` | $0.010128 |  |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.coeff_mul_X_pow` | `lem_fps_xa` | $0.006994 |  |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.size_eq` | `parts_sum` | $0.005887 |  |
| 7 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_apply_of_ne` | `simpleTransposition_apply_of_ne_ne` | $0.006748 |  |
| 8 | FAIL | `AlgebraicCombinatorics/Permutations/Inversions1.lean:AlgebraicCombinatorics.lexLt_irrefl` | `lexLt_irrefl` | $0.002569 |  |
