# RepoProver Experimental Timing Report

Generated: `2026-05-06T22:02:22Z`

This report summarizes current timing for one theorem-level experimental
evaluation round and the persistent Lean REPL experiment. It uses committed run
artifacts only; no provider calls were made for this report.

## Reference Runs

Main timing comparison artifact:

- Generation run:
  `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-pro-highreason-units002-004`
- Best current cold-process verifier:
  `eval/verification-results-360s-batched-open-support.json`
- REPL verifier attempt:
  `eval/verification-results-360s-repl.json`

The two-unit artifact is useful because it has both an easy compiled FPS unit
(`unit-002`) and a harder signed-counting failure (`unit-004`).

## Current Cold-Process Verifier

After support and inferred-open batching, the current cold verifier checks the
two-unit DeepSeek-high artifact in:

| Metric | Value |
|---|---:|
| Units | 2 |
| Compile passed | 1 |
| Lean calls | 10 |
| Lean elapsed | 154.669s |
| Unit 002 batch | 63.295s |
| Unit 004 batch | 91.374s |

Stage breakdown:

| Stage | Unit 002 | Unit 004 |
|---|---:|---:|
| Inferred-open validation | 15.454s | 12.253s |
| Support availability/materialization | 36.326s | 36.324s |
| Final generated file check | 11.515s | 42.797s |

The cold-process bottleneck is repeated startup/import cost. Even after
batching, each validation/final check starts `lake env lean --stdin --json`.

## Persistent REPL Attempt

I implemented an optional verifier backend:

```bash
--lean-backend repl
```

It uses `lake exe repl` through `src/repoprover/lean_checker.py`, keeps one
process warm, and caches imported environments. The first full attempt
completed but was worse overall:

| Metric | Value |
|---|---:|
| Warmup (`import Mathlib`) | 30.371s |
| Units | 2 |
| Compile passed | 1 |
| Lean calls | 14 |
| Lean elapsed excluding warmup | 990.488s |
| Lean elapsed including warmup | 1020.859s |

The final per-statement checks after warmup were the promising part:

| Unit | Final generated file check |
|---|---:|
| unit-002 | 0.436s |
| unit-004 | 32.454s |

But inferred-open validation timed out and dominated the run:

| Stage | Unit 002 | Unit 004 |
|---|---:|---:|
| Inferred-open validation | 483.160s | 469.873s |
| Support availability/materialization | 1.984s | 2.581s |
| Final generated file check | 0.436s | 32.454s |

Interpretation: the REPL can make already-warmed final/support checks fast, but
the current open-validation path interacts badly with `lake exe repl` and hit
360s timeouts before falling back.

## Hybrid Attempt

I added:

```bash
--repl-open-validation-backend cold_process
```

to keep inferred-open validation on the old cold path while using the REPL for
support/final checks. This also did not finish usefully on this 8 GB server. It
ran for more than 16 minutes, filled swap, and exposed that cold Lean timeouts
could orphan `lean --stdin --json` children after the `lake` parent died.

I stopped that failed timing run and patched the cold timeout path to launch
Lean in its own process group and kill the process tree on timeout.

## One Experimental Round Today

For a rough current end-to-end round:

| Run shape | Model time/cost | Lean verification |
|---|---:|---:|
| Fresh 5-unit Flash panel | 31.242s selector + 18.057s generation, `$0.011108468` total | older artifact lacks Lean elapsed; honest full-panel checks take several minutes |
| DeepSeek-high 2-unit proof lane | provider cost `$0.018949238` | 154.669s current cold verifier |
| Unit004 high-reasoning diagnostic | 12.782s selector + 177.573s generation, `$0.01172379` | 55.913s verification in the panel artifact |

Current practical estimate:

- Cheap Flash-style five-unit rounds are model-cheap and mostly Lean/checker
  bound once generated outputs exist.
- High-reasoning single hard-unit rounds are model-latency bound during
  generation, then Lean-bound during verification.
- Current verification cost is strongly affected by number of generated units,
  number of visible support candidates, and whether generated proof terms cause
  heartbeat-heavy Lean elaboration.

## Parallelization

Model calls can be parallelized more aggressively when budget allows, especially
because selector/generation calls are independent per unit or per small batch.
The existing pipeline already separates paid output logging from verification,
so a queue-based model lane plus verifier lane is feasible.

Lean verification parallelization is constrained on this machine. During the
hybrid REPL attempt, one REPL process used about 5.5 GiB RSS and swap became
full while a cold `lean --stdin --json` child also ran. On this 8 GB server,
multiple Lean workers can easily make the run slower or unstable. Safer near
term options:

- keep one Lean worker on this machine;
- reduce Lean calls by batching and caching;
- use a larger-memory box for parallel Lean lanes;
- avoid mixing a large REPL process with concurrent cold Lean subprocesses.

## Bottom Line

The persistent REPL implementation is present, but it is not yet the production
answer. It proves that post-warmup final statement checks can be very fast
(`0.436s` for the easy unit), but the current verifier has stages that make the
REPL backend worse end-to-end. The best current production path remains the
batched cold-process verifier, with the next optimization target being a safer
single-process Lean service that handles import/open/support checks without
orphaning subprocesses or exhausting memory.
