# Source-statement live eval results

- Generated at: `2026-05-05T13:16:47.514712+00:00`
- Model: `deepseek/deepseek-v4-pro`
- Max tokens: `32768`
- Reasoning effort: `high`
- Repair attempts: `0`
- Repair max tokens: `32768`
- Repair reasoning effort: `high`
- Context mode: `source-only`
- Preflight only: `False`
- Generation only: `True`
- Reuse project: `False`
- Concurrency: `2`
- Sample mode: `corpus-spread`
- Global cost cap: `$0.100000`
- Records attempted: 2 / selected 2
- Successes: 0
- Success rate: 0.0%
- Preflight successes: 0 / 0
- Generation successes: 1 / 1
- Actual reported cost: `$0.020311`
- Failure classes: `{"openrouter_error": 1}`

Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.

| # | Result | Record | Generated name | Cost | Error / Lean output |
|---:|---|---|---|---:|---|
| 1 | FAIL | `AlgebraicCombinatorics/CauchyBinet.lean:AlgebraicCombinatorics.CauchyBinet.det_diagonal_submatrix_eq` | `` |  | openrouter_JSONDecodeError: Expecting value: line 331 column 1 (char 1815) |
| 2 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/SchurBasics.lean:alternant_swap` | `alternant_properties` | $0.020311 |  |
