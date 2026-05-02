# Source-statement live eval report

Date: 2026-05-02

## What this measures

This is the stricter `oracle_source_statement` setting, not oracle proof-fill.
The prompt includes:

- the target TeX/source chunk selected by the current dataset alignment;
- Mathlib plus recorded prefix Lean context/predecessors;
- no target Lean statement;
- no target Lean declaration name;
- no original proof skeleton.

The grader keeps the gold Lean statement out of the prompt. After the model returns a theorem/lemma, the grader materializes a Mathlib-only Lean project and appends a private check theorem whose statement is the withheld gold statement and whose proof is:

```lean
by
  simpa using <model_generated_theorem>
```

A success therefore means the model generated a theorem strong/equivalent enough to prove the withheld target statement, and the file Lean-checks. This is still not fully end-to-end feed-forward autoformalization because the source chunk is oracle-selected by the existing label alignment.

## Tooling added

`scripts/run_source_statement_live_eval.py` runs this target-statement-withheld eval. It supports:

- deterministic corpus-spread sampling over theorem/lemma records;
- API-free budget-only mode;
- live OpenRouter calls guarded by `OPENROUTER_API_KEY`;
- per-record payload/response/cost artifacts;
- Lean verification of generated declarations against withheld gold statements;
- per-call timeout and no OpenAI client retries.

Budget-only 30-record sample:

```text
selected records: 30
estimated prompt tokens: 47,410
max completion tokens at 32,768 cap: 983,040
estimated max cost: $0.87586815
```

## Live attempts

Three live attempts were made with `deepseek/deepseek-v4-pro` via interactive Bash so `OPENROUTER_API_KEY` was available. No secret value was printed.

All attempts only completed the first selected record before being killed due the first/next OpenRouter call taking too long for this interactive run.

First selected record:

```text
AlgebraicCombinatorics/CauchyBinet.lean:AlgebraicCombinatorics.CauchyBinet.det_diagonal_submatrix_eq
```

### Attempt A: 30-record, 32,768 cap, high reasoning

Artifacts: `/tmp/repoprover-source-statement-eval-30-live/`

- completed paid calls: 1
- successes: 0
- cost: `$0.00795267`
- finish reason: `stop`
- usage: 1,382 prompt tokens, 8,450 completion tokens
- completion-token details reported 7,953 reasoning tokens

Model returned a theorem named `det_minors_diag`, but it did not compile. The Lean checker reported, among other errors:

```text
Unknown identifier `submatrixOfFinset` at quotation precheck
unexpected token 'in'; expected ','
Unknown identifier `det_minors_diag`
```

So this was a model/formulation failure under the stricter target-statement-withheld prompt, not a successful proof-fill.

### Attempt B: 10-record, 8,192 cap, high reasoning

Artifacts: `/tmp/repoprover-source-statement-eval-10-live/`

- completed paid calls: 1
- successes: 0
- cost: `$0.00717605`
- finish reason: `length`
- usage: 1,382 prompt tokens, 8,192 completion tokens
- all completion tokens were reported as reasoning tokens
- assistant message content was null, so JSON parsing failed

This showed that 8,192 tokens is too low for DeepSeek V4 in this stricter setting: it can spend the whole completion budget on hidden reasoning and return no JSON content.

### Attempt C: 20-record, 4,096 cap, no explicit reasoning-effort

Artifacts: `/tmp/repoprover-source-statement-eval-20-fast-live/`

- completed paid calls: 1
- successes: 0
- cost: `$0.00361253`
- finish reason: `length`
- usage: 1,382 prompt tokens, 4,096 completion tokens
- all completion tokens were reported as reasoning tokens
- assistant message content was null, so JSON parsing failed

Removing explicit high reasoning did not stop the provider/model from using the completion budget as reasoning for this hard prompt.

## Current conclusion

The real target-statement-withheld restart is underway as tooling, but the first live evidence is very different from oracle proof-fill:

- oracle proof-fill one-record smoke succeeded cheaply;
- target-statement-withheld source-to-Lean did not succeed on the first selected Cauchy--Binet record;
- lower token caps are actively misleading for DeepSeek V4 here because completions may contain only reasoning and no answer;
- a substantial percentage estimate cannot honestly be claimed from one completed record.

The available evidence points away from a 90% easy setting and toward either low first-pass success or a need for a different selection/prompt/repair loop before running a larger batch.

## Next recommended run

Do not keep rerunning the same hard first record sequentially. The next batch should either:

1. sample easier/smaller source-statement records first, or
2. run per-record calls as independent background jobs so one slow call does not block the whole batch, and use a high enough cap (at least 32,768) to get actual content.

Scoring should continue to report three separate failure classes:

- no content / length due reasoning-token exhaustion;
- generated Lean does not parse/compile;
- generated theorem compiles but does not prove withheld gold statement.
