# RepoProver Codex Log Audit For Eight-Hour Report

Generated: `2026-05-06T06:00Z`

Scope matched to `reports/REPORT-20260506T053800Z.md`: approximately
`2026-05-05T21:38Z` through `2026-05-06T05:42Z`.

Primary log sources:

- `/home/name/.codex/log/codex-tui.log`
- `/home/name/.codex/sessions/2026/05/06/rollout-2026-05-06T05-32-35-019dfbc6-11b4-70a1-9b0d-85420bbd903b.jsonl`
- Repo artifacts under `docs/latex-statement-*` and the prior report.

No secrets were needed or copied. The audit used passive reads only.

## Executive Summary

The eight hours were not mostly one long Lean build or one expensive model call.
They were a dense sequence of small Codex-driven loops: inspect artifacts, edit
prompt/script behavior, run focused tests, run one paid or no-cost pipeline step,
verify, inspect JSON/Lean errors, commit, repeat. The main implementation thread
was `019df556-de1a-7422-9dde-2d68226a1c96`, visible in
`codex-tui.log`; the native per-session JSONL for that thread was not present in
`/home/name/.codex/sessions`, so the TUI log is the authoritative Codex trace.

Approximate time allocation from timestamped `ToolCall` events in the main
thread, attributing wall-clock gaps to the preceding activity and capping each
gap at 10 minutes:

| Bucket | Approx. minutes | Interpretation |
|---|---:|---|
| Process waits / polling | 184 | Mostly waiting on subprocesses launched by Codex: model calls, Lean checks, pytest, hydration, verification, and follow-up polls. |
| Artifact inspection | 85 | `jq`, `sed`, `rg`, and ad hoc Python over JSON artifacts, prompts, verifier output, Mathlib source, and run summaries. |
| Code edits | 68 | `apply_patch` blocks changing scripts/tests/docs/status. |
| Lean / hydration / verification | 43 | Direct calls to hydration, verification, repair-context-pack builders, and Lean probes. Some Lean/model time is also inside process waits. |
| Git/status/reporting | 40 | Frequent status checks, diffs, adds, commits/amends, and report coordination. |
| Paid/model loop commands | 19 | Direct launch time for OpenRouter-facing scripts; actual model wait time is partly counted under process waits. |
| Tests | 16 | Focused pytest and `py_compile` checks. |
| Other / coordination | 24 | Planning/status/tool overhead. |

There was little evidence of idle time. The extraction found only one
tool-to-tool gap above 3 minutes in the main thread, a 3.1 minute wait at
`2026-05-06T04:20:26Z` on a 180-second subprocess poll. The bottleneck is not
dead air; it is too many serial micro-iterations around the same failure modes.

Paid provider cost was small compared with agent and local loop time. The prior
report's de-duplicated saved-response total was 92 provider calls,
approximately 1.35M prompt tokens, 97k completion tokens, and `$0.24826311`.
The Codex parent thread itself consumed very large OpenAI context by the end:
the TUI log records `20,656,742` input tokens, `45,438` output tokens, and
`17,858` reasoning tokens by `2026-05-06T05:34:37Z` for the main turn.

## Timeline And Concentration

The commit timeline from the child worktree matches the prior report. Early
work, from roughly `21:46Z` to `00:37Z`, broadened the pipeline: theorem-level
hydration/generation, inverse uniqueness, determinant transpose, semantic
coverage, local context, batch smoke artifacts, fallback search, and repair
loops. This period touched multiple theorem units and produced real positive
signals.

From about `03:06Z` onward, the loop became heavily concentrated on
`prop.sf.Npar-as-par` / NPartition:

| Period | Main focus | Outcome |
|---|---|---|
| `21:42-22:53Z` | Build theorem-level context/generation/verification path, inverse uniqueness, determinant transpose, first batch | Several new capabilities and first compile/semantic wins. |
| `23:03-00:37Z` | Fallback Mathlib search, local predecessor context, repair loops, symmetric and determinant batch repair | More infrastructure, `e_n = 0` and mixed determinants improve. |
| `01:10-02:59Z` | Hidden-context filtering, visible support, failure taxonomy, context-gap diagnosis | Stronger benchmark honesty and better diagnostics. |
| `03:06-05:25Z` | NPartition helper planning, Nat.Partition hydration, bridge facts, representation control, zero-padding, normalizer, Kimi comparison | Failure narrows but score remains `not_generated_cannot_prove`; multiple paid retries on one hard unit. |
| `05:28-05:42Z` | Diverse4/Vandermonde fallback ranking and report generation | Useful generic fallback-ranking fix plus prior report. |

The NPartition concentration was useful as a development case because it forced
fixes for real bugs: `do_not_use_identifiers` sanitation, checked bridge notes,
representation control, zero-padding decomposition, and placeholder
normalization. It was also the place where the loop became least efficient:
many runs were variations on the same theorem after the high-level blocker had
already become "fresh same-unit proof synthesis is too hard for this model."

## Evidence Table

| Evidence | Reference | What it shows |
|---|---|---|
| Main implementation thread starts late-window turn | `/home/name/.codex/log/codex-tui.log:1104322` | Thread `019df556-de1a-7422-9dde-2d68226a1c96` begins the relevant work at `2026-05-05T21:42:42Z`. |
| First hydration/generation probe loop | `codex-tui.log:1104903`, `1105422`, `1105463`, `1106062` | Hydration, budget generation, paid generation, then verification were run within the first 11 minutes. |
| First commit checkpoint | `codex-tui.log:1106860`; git commit `770b251` at `21:46:23Z` | The first coherent unit, "Add theorem-level hydration and generation probes", landed quickly. |
| Repeated focused tests and commits | `codex-tui.log:1109223`, `1109986`, `1110047`, `1111977`, `1112738` | The loop repeatedly used pytest/compile checks before amending/committing pipeline changes. |
| NPartition zero-padding context selection | `codex-tui.log:1163745`, `1163785`, `1163939`, `1164015` | Zero-padding repair context was selected, hydrated, and packed as a checked context route. |
| NPartition zero-padding repair and verification | `codex-tui.log:1164296`, `1164353`, `1164373`, `1164430`, `1164470` | Repair generated a skeleton, then verification/comparison/cost inspection confirmed it did not pass honestly. |
| Normalizer added after placeholder skeletons | `codex-tui.log:1164859`, `1164986`, `1165271`, `1165402` | The loop converted incomplete generated outputs into clean `cannot_prove_from_visible_context` artifacts. |
| Current model lookup before Kimi retry | `codex-tui.log:1165638` | Model choice was checked live from OpenRouter rather than guessed from memory. |
| Kimi comparison run | `codex-tui.log:1165659`, `1165716`, `1165736`, `1165795` | Kimi K2.6 produced a larger skeleton but still failed the no-placeholder contract; cost was inspected. |
| Diverse4/Vandermonde fallback-ranking work | `codex-tui.log:1166174`, `1166302`, `1166483`, `1167987`, `1168309` | A separate theorem exposed fallback ranking issues and produced a generic Mathlib-ranking fix. |
| Prior report subagent metadata | `/home/name/.codex/sessions/2026/05/06/rollout-2026-05-06T05-32-35-019dfbc6-11b4-70a1-9b0d-85420bbd903b.jsonl:1` | The prior report was a subagent spawned from the main thread, nickname `Peirce`, cwd `/home/name/repos/repoprover`. |
| Prior report's initial history commands | same JSONL `:21`, `:22`, `:174`, `:175` | The report agent used git history as a major source, then moved history inspection into a temp worktree after correction. |
| Prior report write and autosave | same JSONL `:233`, `:253` | Report file was written at `05:41:54Z`; autosave commit `b49b5ec` recorded it. |

## Diagnosis Of Loop Bottlenecks

1. The loop was too serial.

Each theorem attempt ran as a hand-steered chain: inspect, patch, test, run
selector/generator/repair, verify, inspect, patch again. That made sense while
the pipeline API was changing, but after the repair loop shape stabilized the
same actions should have been batched.

2. The feedback target narrowed too much.

After `03:06Z`, NPartition became the dominant feedback case. It was a valuable
dev case, but it caused local prompt lessons to be repeatedly optimized against
one theorem. This made every new fix look plausible while giving weak evidence
that the fix generalized.

3. A hard proof-synthesis blocker was treated as a context-selection blocker for
too long.

By the zero-padding phase, checked context packs had many relevant facts and no
failed requests, yet the model still generated placeholders. Further selector
prompt edits were lower yield than switching lanes: either a Lean-specialized
proof agent/manual proof pass, or a fixed panel that measures whether the
generic rule helps other units.

4. Codex context grew very large.

The main thread accumulated over 20M input tokens by `05:34Z`. Even with caching,
large context increases latency, makes the agent more likely to inspect
historical context repeatedly, and raises the cost of every reasoning step. The
report subagent alone reached about 5M input tokens by `05:42Z`.

5. The artifact surface is auditable but not summarized enough for live control.

The saved payloads/responses are good. The missing piece is a small live
dashboard per run: unit, stage, cost, elapsed time, checked/failed context
counts, verifier class, and whether the run is a repeat of the same unit.

## Where Work Moved Forward

- Theorem-level source units became the main benchmark surface.
- Context selection split source, prior source, project, local, and Mathlib
  channels.
- Mathlib hydration became more reliable through exact checks, type
  neighborhoods, fallback candidates, bridge facts, and later declaration
  excerpt/docstring-aware ranking.
- Verification became more honest by filtering hidden imports and opens.
- Semantic coverage separated "compiled Lean" from "covered source meaning."
- Repair loops became autonomous enough to select additional context and retry.
- Failure taxonomy and context-gap diagnostics made unresolved cases legible.
- Placeholder/comment/ellipsis skeletons stopped counting as generated proof
  attempts.

## Where Work Circled

- NPartition had many paid and no-cost variants after the same core blocker was
  clear: the model could sketch helper structure but could not complete local
  proofs honestly.
- Several prompt rules were introduced from one datapoint and then immediately
  tested on that same datapoint, which is useful debugging but weak benchmark
  evidence.
- Some runs repeated a full context/repair flow to test small prompt or
  hydration changes that could have been first measured in a no-cost artifact
  diff or on a broader panel.

## One-Theorem Concentration And Five-Theorem Panel

Yes, work was over-concentrated on one theorem in the final third of the window.
The concentration was justified for root-cause analysis, but it became a poor
training-loop signal once NPartition had been classified as a same-unit helper
proof-synthesis problem.

A fixed 5-theorem panel would improve signal substantially. It should include:

- one already-solved easy positive to catch regressions;
- one determinant-style theorem where local/project context matters;
- one symmetric-function theorem that exercises repair context;
- NPartition as the known hard development case;
- one unrelated fresh holdout theorem not used to author the latest prompt rule.

Run every prompt/hydration change against the panel before another single-case
retry. Score per theorem should include: compile status, semantic coverage,
failure class, provider cost, elapsed wall time, checked context count, failed
context count, and whether output was normalized. NPartition can remain in the
panel, but a NPartition-only win should not be treated as general progress.

## Recommendations For Speeding Up The Training Loop

1. Freeze a 5-theorem dev panel now.

Make the next loop command panel-based by default. Single-theorem retry should
require an explicit diagnostic reason.

2. Add a one-command panel runner.

The runner should execute context selection, hydration, generation, verification,
gold comparison, semantic grading, and bounded repair for the panel, then emit a
single compact JSON/Markdown summary. That removes many manual `jq`/`sed` loops.

3. Use no-cost dry-run gates before paid retries.

For prompt/schema/hydration edits, first run: payload generation, hydration,
checked context pack build, prompt diff, and contract validation. Only call the
model when those summaries differ in an intended way.

4. Stop after two failed same-class retries on one theorem.

If the failure class and blocker do not change after two attempts, route the
case to a different lane: Lean proof agent/manual proof, Mathlib search
improvement, or dataset/source-context diagnosis.

5. Split "context lookup" from "proof synthesis" decisions.

When checked context count is high and failed context count is zero, the next
action should usually be proof-lane work, not more context prompt tuning.

6. Keep Codex sessions smaller.

Use short report/diagnostic subagents for audits and retire long context once a
report lands. The parent thread became a large context sink; future training
loops should hand off through compact run summaries rather than retaining the
whole interactive history.

7. Add a run ledger.

A small `docs/latex-statement-run-ledger.jsonl` or generated report should
record one row per run: timestamp, unit ids, stage, model, cost, elapsed time,
artifact path, failure class, and next decision. This would make "where did the
time go?" answerable without scanning 600MB of TUI logs.

8. Treat NPartition as dev-set contaminated.

Keep it for debugging hard same-unit helper synthesis, but validate generic
rules on fresh theorem units before counting them as benchmark improvements.

## Caveats

- Native session JSONL for the main implementation thread was not found under
  `/home/name/.codex/sessions`; the complete per-turn audit had to come from
  the large TUI log.
- The time allocation is approximate. It attributes gaps between logged tool
  calls to the preceding activity and caps individual gaps at 10 minutes.
- Provider spend is artifact-derived from saved response JSON, not an
  account-level billing statement.
- Some subprocess wait time could be OpenRouter, Lean, pytest, or hydration
  depending on the launched command; the log records the polling, not always the
  internal phase timing.
