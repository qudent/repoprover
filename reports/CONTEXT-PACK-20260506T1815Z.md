# RepoProver Autoformalization Context Pack

Generated: `2026-05-06T18:15Z`

Purpose: compact discussion pack for an external LLM reviewing the current
RepoProver theorem-level LaTeX-to-Lean autoformalization approach. This report
was prepared by passive file inspection in
`/home/name/repos/repoprover.worktrees/discussion-context-pack-20260506T1815Z`.
No provider calls, Lean checks, Lake builds, or process control were run.

## Executive Summary

RepoProver has pivoted from declaration-row autoformalization to theorem-level
LaTeX source units. The production unit is one theorem-like LaTeX environment.
For each unit, the pipeline selects visible source, visible prior source,
visible previous project declarations, same-file predecessor declarations, local
file/import/style context, and checked Mathlib APIs. It then asks a model to
generate one or more Lean declarations, verifies them with Lean, and only then
uses hidden aligned Lean gold declarations for post-hoc diagnostic comparison
and semantic coverage.

Current evidence is useful but weak. The fresh honest open-model full-panel
proof-lane reruns score `0/5` semantic for both DeepSeek V4 Pro no-reasoning and
Kimi K2.6 no-reasoning. A targeted DeepSeek V4 Pro high-reasoning run on fresh
units `002` and `004` reaches `1/2` compile and `1/2` semantic at cost
`$0.018949238`. Earlier fresh-slice pipeline evidence is `1/5`, and a later
transitive-localdeps panel regressed to `0/5` under stricter support-assumption
verification. The main failures now look like proof synthesis, missing or badly
used project APIs, ill-typed generated terms, and verifier/import support
overhead, not placeholder/sorry contract violations.

## Pipeline Shape

The current theorem-level loop:

1. Build/select theorem-like LaTeX units from
   `docs/latex-statement-units.jsonl` and
   `docs/latex-statement-gold-candidates.jsonl`.
2. Run target-hidden context selection:
   `scripts/run_latex_statement_context_selection.py`.
3. Hydrate requested project/Mathlib context by Lean-checking exact
   identifiers and fallback candidates:
   `scripts/hydrate_latex_statement_context.py`.
4. Generate Lean declarations:
   `scripts/run_latex_statement_generation.py`.
5. Verify generated-only Lean:
   `scripts/verify_latex_statement_generation.py`.
6. Run exact gold comparison and post-hoc semantic coverage:
   `scripts/compare_latex_statement_generation_to_gold.py` and
   `scripts/verify_latex_statement_semantic_coverage.py`.
7. For failures, run repair-context selection and repair generation:
   `scripts/run_latex_statement_repair_context_selection.py` and
   `scripts/run_latex_statement_repair_loop.py`.
8. For clean declines or stubborn compile failures, build target-hidden
   proof-lane tasks:
   `scripts/build_latex_statement_proof_lane_tasks.py`.
9. Run proof-lane generation and acceptance overlays:
   `scripts/run_latex_statement_proof_lane_generation.py` and
   `scripts/run_latex_statement_proof_lane_acceptance.py`.

Dataset scale from `docs/latex-statement-dataset-report.md` and `STATUS.md`:

| Item | Count |
|---|---:|
| Source theorem-like units | 462 |
| Gold-candidate units with explicit Lean `Label:` alignment | 114 |
| Total aligned Lean declarations | 414 |
| Multi-declaration gold-candidate units | 65 |

Important distinction: a LaTeX source unit can align to several Lean
declarations. Lean is still the compile unit, but benchmark coverage is judged
at the source theorem/environment level.

## Benchmark Honesty Rules

The intended honest run is target-hidden:

- The model must not see aligned target Lean names, statements, or proofs for
  the selected source unit.
- Gold declarations are oracle/diagnostic context only and are used after
  generation for exact-name comparison or semantic proof coverage.
- Prompt payloads record benchmark policy keys such as
  `target_lean_available_to_generator: false`,
  `target_lean_available_to_proof_lane_generator: false`,
  `posthoc_alignment_hidden: true`, and
  `gold_comparison_is_posthoc_only: true`.
- The proof-lane task builder records the same anti-cheating policy and strips
  aligned target declarations plus post-hoc gold metadata from task JSON/MD.

Known caveats and fixes:

- Earlier work fixed target-import leakage: verifier imports are filtered so
  generated code cannot import the target module containing the hidden aligned
  declaration.
- Earlier visible-support materialization could false-reject or leak unrelated
  support variables; scoped support materialization fixed this.
- The support-assumption checking fix made assumption materialization stricter.
  It exposed that some earlier "visible support" was not actually accepted by
  Lean as assumptions.
- `unit004` (`lem.cancel.all-even.l1`) is now dev-contaminated: repeated
  diagnostics induced generic rules about finite sign-vector carriers and
  prior-dependency closure. Its latest rerun is useful as a diagnostic, not
  held-out evidence.
- Clean `cannot_prove_from_visible_context` is counted as a quality/contract
  signal, not proof progress.
- Current bottom-line viability is not a `$100`/90% proof of concept. The
  artifacts show useful cheap selector/context components plus unresolved
  proof-lane and context-routing blockers.

## Current Panels And Units

Fixed dev panel:
`docs/latex-statement-dev-panel-2026-05-06.json`. This is explicitly
development-contaminated and should not be treated as held out.

Fresh slice:
`docs/latex-statement-fresh-slice-2026-05-06.json`. It was fresh before its
first run, but after debugging it became development evidence too.

| Panel | Unit | Source label | Gold/development role |
|---|---|---|---|
| Dev | `unit-001` | `lem.fps.prod.irlv.cong-div` | unresolved FPS/project-context gap |
| Dev | `unit-002` | `thm.det.triang` | known Mathlib/local-style positive control |
| Dev | `unit-003` | `thm.commring.inverse-uni` | known previous-project context control |
| Dev | `unit-004` | `prop.binom.vandermonde.NN` | Mathlib bridge/proof-planning case |
| Dev | `unit-005` | `prop.sf.Npar-as-par` | hard same-unit helper planning case |
| Fresh | `unit-001` | `cor.lgv.catalan-hankel-det-0` | determinant/LGV/Catalan context stress |
| Fresh | `unit-002` | `cor.fps.invertible.field` | FPS/project-context control |
| Fresh | `unit-003` | `prop.binom.nCk-2i-qedmo.CN` | binomial/FPS identity context check |
| Fresh | `unit-004` | `lem.cancel.all-even.l1` | finite signed-sum expansion check |
| Fresh | `unit-005` | `thm.sf.jt-e` | hard symmetric-function determinant theorem |

## Curated Source Excerpts

The repository contains the source under
`algebraic-combinatorics/AlgebraicCombinatorics/tex/`. The original source
paths in dataset records omit the leading `algebraic-combinatorics/` prefix.
The following excerpts are the immediate theorem environments and nearby
context. A larger "roughly 30 pages" source manifest appears below instead of
dumping every raw line into this report.

### Dev Panel Source Windows

`thm.commring.inverse-uni`:
`algebraic-combinatorics/AlgebraicCombinatorics/tex/FPS/DividingFPS.tex:64-73`

```tex
Our next goal is to study inverses of FPSs in $K\left[  \left[  x\right]
\right]  $, answering in particular the natural question ...
which elements of $K\left[  \left[  x\right]  \right]  $ have
inverses...

\begin{theorem}
\label{thm.commring.inverse-uni}Let $L$ be a commutative ring. Let $a\in L$.
Then, there is \textbf{at most one} inverse of $a$.
\end{theorem}
```

`thm.det.triang`:
`algebraic-combinatorics/AlgebraicCombinatorics/tex/Determinants/BasicProperties.tex:587-596`

```tex
\begin{theorem}
[Determinants of triangular matrices]\label{thm.det.triang}Let $n\in
\mathbb{N}$. Let $A\in K^{n\times n}$ be a triangular (i.e., lower-triangular
or upper-triangular) $n\times n$-matrix. Then, the determinant of the matrix
$A$ is the product of its diagonal entries. That is,%
\[
\det A=A_{1,1}A_{2,2}\cdots A_{n,n}.
\]
\end{theorem}
```

`lem.fps.prod.irlv.cong-div`:
`algebraic-combinatorics/AlgebraicCombinatorics/tex/Details/InfiniteProducts1.tex:384-407`

```tex
In order to prove Proposition \ref{prop.fps.div-mulable}, we need a lemma (an
analogue of Lemma \ref{lem.fps.prod.irlv.cong-mul} for division instead of multiplication):

\begin{lemma}
\label{lem.fps.prod.irlv.cong-div}Let $a,b,c,d\in K\left[  \left[  x\right]
\right]  $ be four FPSs such that $c$ and $d$ are invertible. Let
$n\in\mathbb{N}$. Assume that
\[
\left[  x^{m}\right]  a=\left[  x^{m}\right]  b ...
\]
Assume further that ...
Then,
\[
\left[  x^{m}\right]  \dfrac{a}{c}=\left[  x^{m}\right]  \dfrac{b}{d}
...
\]
\end{lemma}
```

`prop.binom.vandermonde.NN`:
`algebraic-combinatorics/AlgebraicCombinatorics/tex/FPS/FPSDefinition.tex:854-867`

```tex
\subsubsection{\label{subsec.gf.defs.cvi}The Chu--Vandermonde identity}

\begin{proposition}
\label{prop.binom.vandermonde.NN}Let $a,b\in\mathbb{N}$, and let
$n\in\mathbb{N}$. Then,%
\begin{equation}
\dbinom{a+b}{n}=\sum_{k=0}^{n}\dbinom{a}{k}\dbinom{b}{n-k}.
\label{eq.prop.binom.vandermonde.NN.eq}%
\end{equation}
\end{proposition}
```

`prop.sf.Npar-as-par`:
`algebraic-combinatorics/AlgebraicCombinatorics/tex/SymmetricFunctions/MonomialSymmetric.tex:8-31`

```tex
\begin{definition}
\label{def.sf.Npar}An $N$\emph{-partition} will mean a weakly decreasing
$N$-tuple of nonnegative integers. ...
\end{definition}

\begin{proposition}
\label{prop.sf.Npar-as-par}There is a bijection%
\begin{align*}
\left\{  \text{partitions of length }\leq N\right\}   &  \rightarrow\left\{
N\text{-partitions}\right\}  ,\\
\left(  \lambda_{1},\lambda_{2},\ldots,\lambda_{\ell}\right)   &
\mapsto\left(  \lambda_{1},\lambda_{2},\ldots,\lambda_{\ell}%
,\underbrace{0,0,\ldots,0}_{N-\ell\text{ zeroes}}\right)  .
\end{align*}
\end{proposition}
```

### Fresh Slice Source Windows

`cor.lgv.catalan-hankel-det-0`:
`algebraic-combinatorics/AlgebraicCombinatorics/tex/Determinants/LGV2.tex:327-343`

```tex
\begin{corollary}
\label{cor.lgv.catalan-hankel-det-0}Let $k\in\mathbb{N}$. Recall the Catalan
numbers $c_{n}=\dfrac{1}{n+1}\dbinom{2n}{n}$ for all $n\in\mathbb{N}$. Then,%
\[
\det\left(  \left(  c_{i+j-2}\right)  _{1\leq i\leq k,\ 1\leq j\leq k}\right)
= ... =1.
\]
\end{corollary}
```

`cor.fps.invertible.field`:
`algebraic-combinatorics/AlgebraicCombinatorics/tex/FPS/DividingFPS.tex:309-316`

```tex
We note a particularly simple corollary of Proposition
\ref{prop.fps.invertible} when $K$ is a field:

\begin{corollary}
\label{cor.fps.invertible.field}Assume that $K$ is a field. Let $a\in K\left[
\left[  x\right]  \right]  $. Then, the FPS $a$ is invertible ... iff
\left[  x^{0}\right]  a\neq0$.
\end{corollary}
```

`prop.binom.nCk-2i-qedmo.CN`:
`algebraic-combinatorics/AlgebraicCombinatorics/tex/FPS/NonIntegerPowers.tex:598-608`

```tex
Let us show yet another application of powers with non-integer exponents and
the generalized Newton formula. We shall show the following binomial identity:

\begin{proposition}
\label{prop.binom.nCk-2i-qedmo.CN}Let $n\in\mathbb{C}$ and $k\in\mathbb{N}$.
Then,%
\[
\sum_{i=0}^{k}\dbinom{n+i-1}{i}\dbinom{n}{k-2i}=\dbinom{n+k-1}{k}.
\]
\end{proposition}
```

`lem.cancel.all-even.l1`:
`algebraic-combinatorics/AlgebraicCombinatorics/tex/SignedCounting/SubtractiveMethods.tex:140-154`

```tex
We shall now prove Theorem \ref{thm.cancel.all-even} by formalizing and
generalizing this argument. We begin with the obvious generalization ...

\begin{lemma}
\label{lem.cancel.all-even.l1}Let $n,d\in\mathbb{N}$. Then,%
\begin{align*}
&  \sum_{\left(  e_{1},e_{2},\ldots,e_{d}\right)  \in\left\{  1,-1\right\}
^{d}}\left(  e_{1}+e_{2}+\cdots+e_{d}\right)  ^{n}\\
&  =\sum_{\left(  x_{1},x_{2},\ldots,x_{n}\right)  \in\left[  d\right]  ^{n}%
}\ \ \sum_{\left(  e_{1},e_{2},\ldots,e_{d}\right)  \in\left\{  1,-1\right\}
^{d}}e_{x_{1}}e_{x_{2}}\cdots e_{x_{n}}.
\end{align*}
\end{lemma}
```

`thm.sf.jt-e`:
`algebraic-combinatorics/AlgebraicCombinatorics/tex/SymmetricFunctions/PieriJacobiTrudi.tex:443-461`

```tex
The \emph{second Jacobi--Trudi formula} involves elementary symmetric
polynomials $e_{n}$ ... and transpose partitions ...

\begin{theorem}
[Second Jacobi--Trudi formula]\label{thm.sf.jt-e}Let $\lambda$ and $\mu$ be
two partitions. Let $\lambda^{t}$ and $\mu^{t}$ be the transposes ...
Then,%
\[
s_{\lambda/\mu}=\det\left(  \left(  e_{\lambda_{i}^{t}-\mu_{j}^{t}%
-i+j}\right)  _{1\leq i\leq M,\ 1\leq j\leq M}\right)  .
\]
\end{theorem}
```

### Expanded Source Manifest

Open these windows for a roughly 30-page source pack with local definitions,
proof sketches, and surrounding theorem environments:

- `algebraic-combinatorics/AlgebraicCombinatorics/tex/FPS/DividingFPS.tex:58-82`
- `algebraic-combinatorics/AlgebraicCombinatorics/tex/FPS/DividingFPS.tex:250-324`
- `algebraic-combinatorics/AlgebraicCombinatorics/tex/Determinants/BasicProperties.tex:560-606`
- `algebraic-combinatorics/AlgebraicCombinatorics/tex/Details/InfiniteProducts1.tex:340-430`
- `algebraic-combinatorics/AlgebraicCombinatorics/tex/FPS/FPSDefinition.tex:830-885`
- `algebraic-combinatorics/AlgebraicCombinatorics/tex/SymmetricFunctions/MonomialSymmetric.tex:1-80`
- `algebraic-combinatorics/AlgebraicCombinatorics/tex/Determinants/LGV2.tex:260-380`
- `algebraic-combinatorics/AlgebraicCombinatorics/tex/FPS/NonIntegerPowers.tex:560-640`
- `algebraic-combinatorics/AlgebraicCombinatorics/tex/SignedCounting/SubtractiveMethods.tex:100-190`
- `algebraic-combinatorics/AlgebraicCombinatorics/tex/SymmetricFunctions/PieriJacobiTrudi.tex:390-490`

## Hidden Gold Lean Declarations

This section is diagnostic/oracle context. It is not model-facing in honest
generation, repair, or proof-lane runs.

| Source label | Hidden aligned Lean declaration(s) and location |
|---|---|
| `thm.commring.inverse-uni` | `isInverse_unique`, `algebraic-combinatorics/AlgebraicCombinatorics/FPS/CommutativeRings.lean:484-494` |
| `cor.fps.invertible.field` | `fps_invertible_iff_constantCoeff_ne_zero`, `algebraic-combinatorics/AlgebraicCombinatorics/DividingFPS.lean:199-205` |
| `thm.det.triang` | `det_upperTriangular`, `det_lowerTriangular`, `algebraic-combinatorics/AlgebraicCombinatorics/DeterminantsBasic.lean:434-449` |
| `lem.fps.prod.irlv.cong-div` | `xnEquiv_div`, `algebraic-combinatorics/AlgebraicCombinatorics/FPS/InfiniteProducts1.lean:149-164` |
| `prop.binom.vandermonde.NN` | `vandermonde_nat`, `algebraic-combinatorics/AlgebraicCombinatorics/FPSDefinition.lean:797-801` |
| `prop.sf.Npar-as-par` | `ofPartition_size` plus related conversion lemmas, `algebraic-combinatorics/AlgebraicCombinatorics/SymmetricFunctions/NPartition.lean:577-636` |
| `cor.lgv.catalan-hankel-det-0` | `catalan_hankel_det`, `algebraic-combinatorics/AlgebraicCombinatorics/Determinants/LGV2.lean:6082-6110` |
| `prop.binom.nCk-2i-qedmo.CN` | `binomialIdentity`, `algebraic-combinatorics/AlgebraicCombinatorics/FPS/NonIntegerPowers.lean:2256-2269` |
| `lem.cancel.all-even.l1` | `sum_signSum_pow_eq_sum_signProduct`, `algebraic-combinatorics/AlgebraicCombinatorics/SignedCounting/SubtractiveMethods.lean:154-177` |
| `thm.sf.jt-e` | `jacobiTrudi_e`, `algebraic-combinatorics/AlgebraicCombinatorics/SymmetricFunctions/PieriJacobiTrudi.lean:2662-2692` |

Some hidden gold is not fully proved in the source project. For example,
`catalan_hankel_det_general` uses `sorry` at `LGV2.lean:6079-6080`, and
`jacobiTrudi_e` uses `sorry` at `PieriJacobiTrudi.lean:2691-2692`. That matters
when interpreting "gold" as current-project oracle context: it aligns source
intent and declarations, but it is not always a complete proof corpus.

## Current Results And Artifact Paths

### Fresh/Full-Panel Open-Model Runs

Latest honest open-model full-panel proof-lane reruns are summarized by
`reports/latex-statement-failure-overview-20260506T1740Z.md`.

| Run | Artifact root | Compile | Semantic | Main failure shape |
|---|---|---:|---:|---|
| DeepSeek V4 Pro no-reasoning | `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-pro` | `0/5` | `0/5` | 4 clean declines, 1 compile failure; unknown `isUnit_of_ne_zero` |
| Kimi K2.6 no-reasoning | `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-kimi-k2-6` | `0/5` | `0/5` | 3 clean declines, 2 compile failures; missing API and proof-tactic shape |
| DeepSeek V4 Pro high-reasoning units 002+004 | `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-pro-highreason-units002-004` | `1/2` | `1/2` | unit 002 compiles/proves; unit 004 fails on ill-typed term/API/proof shape/timeout |

Run ledger rows are in `docs/latex-statement-run-ledger.jsonl`. The DeepSeek
high two-unit row records cost `$0.018949238`, prompt tokens `15028`,
completion tokens `17567`, reasoning tokens `16293`, verification artifact
`eval/verification-results-360s-batched-open-support.json`, and semantic
artifact `eval/semantic-coverage-360s.json`.

### Fresh Slice History

Fresh-slice first-run summary:
`docs/latex-statement-fresh-slice-2026-05-06-summary.md`.

Key results:

- Initial paid selector/generation:
  `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/`.
- No-cost support-scoped rerun:
  `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1-support-scoped-rerun/`.
- After support/semantic verifier fixes: `1/5` compile and `1/5` semantic,
  proving the FPS field invertibility unit.
- Compact repair loop:
  `docs/latex-statement-repair-loop-runs/2026-05-06-fresh-slice5-repair-v1-paid-v2-compact/`.
  It preserved `1/5` and did not add compile coverage.
- Targeted signed-sum finiteness retry:
  `docs/latex-statement-repair-loop-runs/2026-05-06-fresh-slice5-unit004-finiteness-merged/`.
  It converted the all-even signed-sum failure from impossible `Fin d -> Int`
  carrier generation to a clean decline around missing/insufficient sign-vector
  bridge proof.

### Transitive Localdeps Fresh-Slice Panel

Latest full fresh-slice localdeps panel:
`docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/`.

Panel summary:
`docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/eval/panel-summary.md`.

Metrics:

- Context selection cost `$0.00502572`.
- Generation cost `$0.006082748`.
- Verification with visible support took `1158.772` seconds.
- Verification result: `0/5` compiled, failure classes
  `{compile_failure: 1, declined_cannot_prove: 4}`.
- Semantic coverage: `0/5`, with all five units `generated_not_compiled`.

This artifact is useful for prompt/context diagnostics, but it is not an
acceptance win.

### Unit004 Prior-Dependency Diagnostic

Targeted unit004 diagnostic:
`docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/`.

Panel:
`docs/latex-statement-unit004-prior-deps-panel-2026-05-06.json`.

Key result:

- Selector model: `deepseek/deepseek-v4-flash`, no reasoning.
- Generation model: `deepseek/deepseek-v4-pro`, high reasoning.
- Total panel cost from ledger: `$0.01172379`.
- Verification: `0/1`, compile failure, `4` Lean calls, `55.913` Lean seconds.
- Hydration accepted exact/fallback context with `ok` Lean checks.
- Support context accepted all 11 assumptions after adding dependency closure.
- Remaining blocker: generated proof shape, especially around rewriting
  `signSum`, `signProduct`, and local dependency use.

Repair-context selection for this run:
`docs/latex-statement-repair-loop-runs/2026-05-06-unit004-prior-deps-pro-high-r1/`.
Ledger row: cost `$0.01161189`, valid JSON, repair generation did not complete
before the user redirected. This paid attempt is preserved and should not be
overwritten.

### Partial Repair-Context Selection

Current repair-context selection artifacts:

- `docs/latex-statement-repair-loop-runs/2026-05-06-unit004-prior-deps-pro-high-r1/round-01-context/batch-001/repair-context-selection-payload.json`
- `docs/latex-statement-repair-loop-runs/2026-05-06-unit004-prior-deps-pro-high-r1/round-01-context/batch-001/repair-context-selection-output.json`
- `docs/latex-statement-repair-loop-runs/2026-05-06-unit004-prior-deps-pro-high-r1/round-01-context/checked-repair-context.json`
- `docs/latex-statement-repair-loop-runs/2026-05-06-unit004-prior-deps-pro-high-r1/round-01-context/eval/repair-context-selection-results.json`

### Verifier Timing Before/After

DeepSeek high two-unit verification artifacts:

| Artifact | Lean calls | Lean seconds | Result |
|---|---:|---:|---|
| `eval/verification-results-360s.json` | 28 | 367.128 | `1/2` compile |
| `eval/verification-results-360s-batched-support.json` | 12 | 167.373 | `1/2` compile |
| `eval/verification-results-360s-batched-open-support.json` | 10 | 154.669 | `1/2` compile, `1/2` semantic |

The improvement came from batching support materialization and inferred-open
validation, but repeated `lake env lean --stdin --json` startup still dominates
the runtime.

### Failure Overview

Latest overview:
`reports/latex-statement-failure-overview-20260506T1740Z.md`.

Current failure classes:

- clean `cannot_prove_from_visible_context` declines;
- missing context/API, e.g. unknown identifiers;
- ill-typed generated terms;
- proof-tactic shape errors such as bad rewrites or failed `apply`;
- resource/search timeout in one high-reasoning unit004 attempt.

Current overview reports no no-sorry/placeholder contract violations.

## Model-Facing Prompt Arrangement

Full payloads are saved as JSON before paid calls. Do not paste them wholesale
into a chat unless needed; some are 100k+ characters. Use the paths below.

### Context Selection

Script: `scripts/run_latex_statement_context_selection.py`.

Representative payload:
`docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/context-selection/batch-001/context-selection-payload.json`.

Payload top-level keys:
`extra_body`, `max_tokens`, `messages`, `model`, `response_format`,
`temperature`.

System message:

```text
You are a Lean 4/Mathlib context-planning agent. Prepare a compact context pack for formalizing a LaTeX theorem-like source unit. The target Lean declarations aligned to the selected source unit are withheld. Return exactly one JSON object.
```

User-message JSON shape starts with `rules`, `schema`, and `task`. It then
contains unit records with source text, source-context candidates,
prior-project context, local file context candidates, local predecessor
declarations, and benchmark policy.

Representative rules:

```text
Do not infer or reveal hidden target Lean declaration names for the selected unit.
Do not write theorem/lemma Lean code in target_statement_sketch; exact API syntax belongs in needed_mathlib_context and will be hydrated by tools.
Use previous project declarations only if they are shown under prior_project_context.
Use local_file_predecessor_declarations only as same-file helper/style context; the selected unit's aligned/referencing target declarations are omitted.
Do not treat Mathlib as the only context; enumerate source/project/local/Mathlib context separately.
```

### Generation

Script: `scripts/run_latex_statement_generation.py`.

Representative payload:
`docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/generation/batch-001/generation-payload.json`.

System message:

```text
You are a Lean 4 autoformalization agent. Generate a small ordered sequence of Lean declarations for the provided LaTeX theorem-like unit. Use only the source text, selector plan, previous-project context if shown, and Lean-checked Mathlib signatures in the prompt. The original aligned Lean declarations, names, statements, and proofs are withheld. Return exactly one JSON object.
```

Important instruction blocks:

```text
Do not use sorry, admit, placeholders, or comments standing in for proof.
Do not include import statements or markdown fences.
Do not ask for or infer the hidden aligned Lean declaration names/statements/proofs.
Treat selector_unchecked_statement_sketch as non-authoritative mathematical intent only; do not copy its Lean syntax verbatim.
Follow the Lean-checked signatures exactly when they differ from the selector's expected shape.
Never use a hydrated Mathlib exact_identifier whose lean_check.status is not `checked`; treat it as unavailable even if the selector expected it to exist.
If you cannot produce a complete proof from visible context, set status to cannot_prove_from_visible_context and leave lean_file_body empty.
```

Output contract keys include status, declaration names, `lean_file_body`, notes,
and per-planned-declaration metadata. The exact JSON schema is embedded in the
payload.

### Repair Context

Script: `scripts/run_latex_statement_repair_context_selection.py`.

Representative payload:
`docs/latex-statement-repair-loop-runs/2026-05-06-unit004-prior-deps-pro-high-r1/round-01-context/batch-001/repair-context-selection-payload.json`.

System message from recent report:

```text
You are a Lean 4/Mathlib repair-context planning agent. Select the small extra context needed to repair failed source-only Lean generation. The hidden aligned target Lean declarations, names, statements, and proofs are withheld. Return exactly one JSON object.
```

The selector sees the original generation payload, failed output, raw invalid
scratchpad if preserved, verifier errors, prior checked repair context, and
optional source-coverage review keys. It returns failure analysis, repair
strategy, selected visible context, same-unit helper plan, needed Mathlib
context, `do_not_use_identifiers`, and uncertainty notes.

### Proof Lane

Scripts:

- `scripts/build_latex_statement_proof_lane_tasks.py`
- `scripts/run_latex_statement_proof_lane_generation.py`
- `scripts/run_latex_statement_proof_lane_acceptance.py`

Representative payload:
`docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-pro-highreason-units002-004/batch-001/generation-payload.json`.

System message:

```text
You are a Lean 4 proof-synthesis coding agent. Solve target-hidden LaTeX-statement proof-lane tasks by producing complete Lean declarations from only the visible source/context dossier. The aligned target Lean declarations are withheld. Return exactly one JSON object.
```

Representative proof-lane instructions:

```text
Do not use sorry, admit, placeholders, ellipses, or comments standing in for proof.
Use only the source text, visible prompt context, verifier-visible support context, and checked Mathlib/project/local facts shown in each task.
Treat selector sketches and previous failed generations as diagnostic intent only; Lean-checked signatures and visible source text are authoritative.
If a task contains decline_context_pack.selected_project_context, treat those snippets as newly acquired visible project/local context after target-hidden filtering.
If the visible context is insufficient, set status to cannot_prove_from_visible_context, lean_file_body to exactly empty string, and declaration_names to exactly [].
```

## What Seems To Be Working

- The theorem-level dataset and explicit `Label:` alignments give a concrete
  unit surface and diagnostic oracle.
- Prompt payloads are saved before paid calls, making runs auditable.
- Target-hidden policy is now explicit in payloads and proof-lane task metadata.
- Visible-support materialization and post-hoc semantic coverage have caught
  false rejects and can prove generated statements against gold via bridge
  checks.
- Cheap context selection/hydration can often find plausible exact APIs or
  fallback candidates.
- The verifier has better failure taxonomy and no current placeholder/sorry
  contract failures.
- Batching support/open checks materially reduced Lean-call overhead on the
  two-unit DeepSeek high run.

## What Is Failing

- Fresh held-out-like acceptance is still poor: current honest open-model
  full-panel proof-lane runs are `0/5`; the best current targeted DeepSeek high
  result is `1/2`.
- Selectors and generators still miss, invent, or misuse APIs, especially
  project-local APIs.
- Some source units require nontrivial helper-library development, not just a
  one-shot theorem proof.
- Generated proof tactic shape is brittle even when visible context is accepted.
- Hard symmetric-function and LGV/Catalan units expose large local theory gaps.
- Lean verification remains slow because repeated isolated Lean invocations
  still pay import/startup costs.
- Some aligned "gold" declarations themselves contain `sorry`, so gold is not
  always a fully checked proof oracle.

## Questions For The External LLM

1. Is the theorem-level unit granularity right, or should generation split
   earlier into typed helper obligations before proof synthesis?
2. How should context selection distinguish "missing facts" from "facts present
   but generator cannot use them" without leaking target gold?
3. Should proof-lane tasks be delegated to a coding-agent loop with local Lean
   feedback instead of a single JSON generation call?
4. What is the best target-hidden way to mine project-local API routes from
   surrounding files without using aligned target declarations?
5. How should the evaluator handle source units whose existing aligned Lean
   declarations contain `sorry`?
6. Is the current clean-decline contract too conservative, or is it correctly
   preventing invalid proof sketches?
7. What verifier architecture would reduce repeated import/startup overhead
   while preserving isolation against target-import leakage?
8. Which failure class should be attacked first if the goal is a credible
   cost/coverage curve: context selection, proof synthesis, helper-library
   construction, or verifier speed?

## Additional Artifact Manifest

Reports:

- `reports/REPORT-20260506T1500Z.md`: broad eight-hour pipeline report with
  prompt arrangement, timeline, and metrics through `15:00Z`.
- `reports/latex-statement-failure-overview-20260506T1740Z.md`: latest failure
  overview for open-model and high-reasoning proof-lane runs.
- `docs/npartition-helper-route-diagnostic-2026-05-06.md`: post-hoc local-source
  diagnostic for `prop.sf.Npar-as-par`; not model-facing benchmark context.

Datasets and panels:

- `docs/latex-statement-units.jsonl`
- `docs/latex-statement-gold-candidates.jsonl`
- `docs/latex-statement-dataset-report.md`
- `docs/latex-statement-dev-panel-2026-05-06.json`
- `docs/latex-statement-dev-panel-2026-05-06-summary.md`
- `docs/latex-statement-fresh-slice-2026-05-06.json`
- `docs/latex-statement-fresh-slice-2026-05-06-summary.md`
- `docs/latex-statement-unit004-prior-deps-panel-2026-05-06.json`
- `configs/latex-statement-model-ablation-2026-05-06.json`

Run ledgers and summaries:

- `docs/latex-statement-run-ledger.jsonl`
- `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/eval/panel-summary.md`
- `docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/eval/panel-summary.md`

Prompt payloads:

- `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/context-selection/batch-001/context-selection-payload.json`
- `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/generation/batch-001/generation-payload.json`
- `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-pro-highreason-units002-004/batch-001/generation-payload.json`
- `docs/latex-statement-repair-loop-runs/2026-05-06-unit004-prior-deps-pro-high-r1/round-01-context/batch-001/repair-context-selection-payload.json`

Verification/semantic outputs:

- `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-pro/eval/verification-results-360s.json`
- `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-kimi-k2-6/eval/verification-results-360s.json`
- `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-pro-highreason-units002-004/eval/verification-results-360s-batched-open-support.json`
- `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-pro-highreason-units002-004/eval/semantic-coverage-360s.json`
- `docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/eval/verification-results.json`
- `docs/latex-statement-panel-runs/2026-05-06-unit004-prior-deps-pro-high/eval/semantic-coverage-results.json`

## Passive Stale-Worktree Triage

This is inspection-only guidance for the parent. I did not delete or merge any
worktrees.

| Worktree | State from passive diff/status | Parent recommendation |
|---|---|---|
| `/home/name/repos/repoprover-report-inspect-20260506T0535Z` | Detached `HEAD` at autosave `4910ad3`; diff vs current `main` shows small changes around repair-loop summary/payload artifacts and `scripts/hydrate_latex_statement_context.py`. | Needs parent review before cleanup; may be obsolete if hydration changes are already superseded, but not obviously empty. |
| `/home/name/repos/repoprover.worktrees/codex-log-audit-20260506T0615Z` | Branch `codex-log-audit-20260506T0615Z`; contains `reports/REPORT-20260506T0615Z-codex-log-audit-followup.md` plus `STATUS.md` update. | Looks finishable/mergeable as a report-only branch if parent wants the audit follow-up. |
| `/home/name/repos/repoprover.worktrees/last8h-report-20260506T1500Z` | Branch `last8h-report-20260506T1500Z`; contains `REPORT-20260506T1500Z.md` plus many run artifacts and code/test changes from parent-era work. | Do not blindly delete. Parent should diff against current `main` and salvage/merge report plus any run artifacts not already consumed. |
| `/home/name/repos/repoprover.worktrees/discussion-context-pack-20260506T1815Z` | This child branch; report-only work added here after inspection. | Merge/consume this report commit first; cleanup this child worktree only after parent has the commit. |
