# Source-Statement Preflight-Passing Six V2 Comparison

Date: 2026-05-05

## Change Tested

The v2 prompt/context update added:

- stronger instructions against theorem-local `where` definitions and project
  concept redefinitions;
- stronger instructions against using helper names not displayed in context;
- richer nearby local examples for determinant/binomial records;
- local API-family guidance such as `Ring.choose` vs `Nat.choose`.

## Generation Run

Artifacts:
`docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-v2`

The run was stopped after the last provider request hung for too long.

- Completed paid responses: 5/6
- Parseable generations: 5/5 completed
- Reported OpenRouter cost: `$0.048314638`
- Missing output: record 3,
  `AlgebraicCombinatorics.Det.det_add_smul_col`

## Verification

Serial reusable-project verification:

- Records considered: 6
- Successes: 0
- Failure classes:
  - `generated_lean_does_not_compile`: 3
  - `grader_gold_statement_not_proved`: 1
  - `verification_error`: 1
  - `missing_model_output`: 1
- Verification time: `206.74s`
- Verifier worktree size: about `20M`

## Comparison To V1

V1 completed all 6 provider responses for `$0.079889403` and verified at 0/6:
5 generated-only compile failures and 1 hidden-grader mismatch.

V2 also verified at 0 successes on completed outputs. The wording/local-example
change was not enough to move the benchmark. It did reduce some specific
symptoms but did not solve the core issue: DeepSeek still needs exact local API
retrieval, not just more general instructions.

Examples:

- `pascal_identity_succ` still generated a Nat `choose` theorem (`binom_rec`)
  instead of the local `Ring.choose` target, so it compiled but failed the
  hidden grader.
- determinant records still used unavailable matrix/update APIs such as
  `updateColumn`.
- partition records still used plausible but wrong local names/tactics.

## Decision

Prompt wording/local examples alone were not enough, so the next step was local
API retrieval. That zero-cost retrieval pass is now documented in
`docs/source-statement-local-api-retrieval-preflight.md`: it materializes nearby
source-keyed local declarations while still withholding the target declaration
name and statement, and the six-record shared-project preflight passes 6/6.

The next paid probe should stay small and generation-only, archive every
OpenRouter response under `docs/source-statement-runs/...`, and then run the
separate verifier consumer over those artifacts.
