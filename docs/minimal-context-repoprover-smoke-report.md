# Minimal-Context RepoProver Smoke Report

Run timestamp: 2026-04-28T16:44Z.

## Materialized Smoke

The first bounded smoke used
`ac-notations-and-elementary-facts-examples:binom_zero_of_lt`, selected from
`docs/minimal-context-generated-records.jsonl` because it is a short,
Qwen-reviewed, direct Mathlib-wrapper theorem.

The smoke project was generated with:

```bash
uv run python scripts/materialize_minimal_context_smoke.py \
  --output /tmp/repoprover-minctx-binom-zero \
  --force \
  --lake-cache-from /tmp/repoprover-toy-gemini3-flash
```

The generated project has one target theorem with one `sorry`, a snippet-only
source TeX file, and `.repoprover/state.json` pre-marking the chapter as
sketched so RepoProver launches a prover instead of a sketcher.

Dry validation passed:

```bash
uv run python -m repoprover status /tmp/repoprover-minctx-binom-zero --chapters
lake env lean AlgebraicCombinatorics/FPS/NotationsExamples.lean
```

`repoprover status` reported 1/1 chapters sketched and 0 PRs. `lake env lean`
compiled the generated file with the expected single `sorry` warning.

## Live Run

Command:

```bash
uv run python -m repoprover run /tmp/repoprover-minctx-binom-zero \
  --pool-size 1 \
  --provider openrouter \
  --model qwen/qwen3-coder \
  --no-background-agents \
  --stop-after-first-merge \
  --verbose
```

Run artifact:
`/tmp/repoprover-minctx-binom-zero/runs/20260428-164407/`.

The run was manually stopped after the prover entered a repeated malformed-tool
loop. No PR was submitted or merged.

Observed token/cost estimate from the run logs:

```json
{
  "input_tokens": 245172,
  "output_tokens": 2000,
  "estimated_qwen_cost_usd": 0.05753784
}
```

## Failure Example

The target proof is trivial and independently checks:

```lean
theorem binom_zero_of_lt {m n : ℕ} (h : m < n) : m.choose n = 0 := by
  exact Nat.choose_eq_zero_of_lt h
```

The Qwen prover found the relevant Mathlib theorem but repeatedly called
`lean_check` with invalid Lean code:

```lean
{'n': 'ℕ'}
```

It then attempted `file_edit` with the same malformed string as both
`old_string` and `new_string`, despite reading the exact target lines. This is
a concrete benchmark failure mode: the selected minimal context was sufficient,
but the open model/tool loop failed at tool-call argument construction and edit
selection.

## Notes For Next Smokes

- The materializer now strips the unused `checkdecls` dependency from generated
  smoke projects and ignores all generated `.lake/` state.
- Use this record as a low-risk harness check before harder examples. A stronger
  tool-calling model should merge it in one prover pass.
- For Qwen-style runs, add a low max-iteration or repeated-tool-error kill rule
  before scaling. This run spent about six cents on a failure that was obvious
  after the third malformed `lean_check`.
