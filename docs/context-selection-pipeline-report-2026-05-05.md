# Context-Selection Pipeline Report - 2026-05-05

## Executive Assessment

The user's overall approach makes sense: source-to-Lean autoformalization should
not ask a proof model to guess every Lean API from memory. A cheap selector that
first sketches the formalization and requests tight Mathlib/project context is
the right architectural direction.

The current setup shows that this helps, but it also shows the most important
gap: the pipeline is currently evaluated at the Lean-declaration level, while a
book LaTeX theorem is often a multi-declaration work item. Treating "one book
LaTeX theorem" as the *planning unit* is sensible. Treating it as "one generated
Lean theorem row" is usually too rigid.

The better target architecture is:

1. One LaTeX theorem/environment is a source work item.
2. The context selector decomposes it into one or more Lean declarations plus
   required Mathlib and previous-project context.
3. The generator emits a small Lean file or declaration sequence.
4. Verification reports individual declaration success plus whole-theorem
   completion.

The current benchmark mostly uses one row per existing Lean declaration, aligned
back to TeX labels. That is useful for controlled evaluation, but it creates a
source-unit mismatch: several benchmark rows may share one LaTeX theorem label.

## Current Pipeline

### Data and Record Unit

The durable candidate records come from the existing Lean formalization:

- `docs/minimal-context-full-records.jsonl`
- `docs/minimal-context-gold-candidates.jsonl`

Each row is one Lean declaration:

- `output.lean_path`
- `output.declaration_names`
- `output.line_range`
- `minimal_context.source_spans`
- `alignment.comment_labels`

The TeX label/source span is context metadata. It is not currently the atomic
target. This is why the term "gold standard dataset" is potentially misleading:
it is a declaration-level gold/eval set, not a book-theorem-level gold set.

### Source-Only Prompt Assembly

For generation and selector runs, `context_mode=source-only` removes target Lean
statement/name/doc-comment guidance. The model sees:

- TeX/source snippets and label-derived focus.
- TeX structure cues: labels, environments, part markers, broad-span risks.
- Lean prefix context before the target line.
- Same-file prior declarations that share visible source labels.
- Imported project declarations that share visible source labels.
- Local examples and Lean environment guidance.
- Mathlib context selected by the previous context-selection round.

The target Lean name, target Lean statement, and original proof are withheld.

### Context-Selection Round

The context selector uses a cheap model (`deepseek/deepseek-v4-flash` works best
so far) to return:

- a source-focus summary;
- the selected source part;
- a formalization sketch;
- local context needed;
- previous project declarations to include;
- Mathlib names/search queries to hydrate;
- uncertainties;
- now, a `supporting_context_boundary` explaining what prior/imported facts are
  support only and should not be bundled into the target theorem.

The selector output is written before any gold comparison. Mathlib hydration
then searches local Mathlib source for requested names/queries and adds snippets
to the generation context pack.

### Generation Round

The proof generator currently emits one theorem/lemma JSON object:

- `lean_declaration`
- `declaration_name`
- `used_context`
- `notes`

This is the piece that currently conflicts with "one book theorem as unit": the
prompt asks for one Lean theorem/lemma, even when the source theorem naturally
decomposes into several Lean declarations.

### Verification

Generated declarations are materialized into a Lean project and checked in two
ways:

- generated-only Lean compilation;
- hidden gold grader check against the existing target declaration.

The gold grader is useful for measuring declaration-level reproduction. It is
not yet a theorem-level "did we formalize this book theorem?" verifier.

## Evidence So Far

### Selector Behavior

Best selector mode so far:

- model: `deepseek/deepseek-v4-flash`
- reasoning: omitted / no reasoning mode
- batch size: `2`

Observed selector probes:

- Kimi K2.6 with low/no reasoning returned no usable content or spent output on
  hidden reasoning.
- DeepSeek V4 Flash with reasoning also wasted output budget.
- Gemini Flash returned text but often truncated JSON.
- DeepSeek V4 Flash with no reasoning produced valid JSON and useful Mathlib
  hydration.

The latest paid declaration-progress selector run:

`docs/source-statement-runs/2026-05-05-context-selection-decl-progress-diverse3-paid/`

- records: `3`
- paid calls: `2`
- cost: `$0.00558124`
- target-name leaks: `0`
- Mathlib hydration: enabled

It improved the key `prod-lim-conv` failure: the selector selected only the
equality statement and marked the prior multipliability theorem as support-only.

### Generation and Verification Counts

Honesty caveats:

- The strict 6-row run reached `6/6`, but it used target-comment context and is
  debugging evidence only.
- The current meaningful evidence is source-only/context-selected.

Source-only generation:

- 11-row source-only plus compile repair: best `4/11`.
- easy-8 source-only: `1/8`.

Context-selected/project-context generation:

- first context-selected probe: `0/2`.
- project-context 2-record run:
  - generation: `2/2`;
  - verification: `1/2`;
  - pass: `alternant_swap` via imported previous theorem.
- diverse3 project-context run:
  - selector: valid for `3/3`;
  - generation: `3/3`;
  - verification: `1/3`;
  - pass: `isInverse_unique` via imported previous theorem.

Latest declaration-progress generation-only run:

`docs/source-statement-runs/2026-05-05-decl-progress-diverse3-generation-paid/`

- generation outputs: `3/3`;
- cost from partial/final result artifacts: `$0.019770489`;
- not Lean-verified yet.

Generated outputs from that run:

```lean
theorem tprod'_eq_of_coeffStabilizesTo_partial_prod' {f : ℕ → PowerSeries K} {lim : PowerSeries K}
    (h : CoeffStabilizesTo (fun i => ∏ j ∈ Finset.range (i + 1), f j) lim)
    (hconst : ∀ i, constantCoeff (f i) = 1) :
    tprod' f (isMultipliable_of_coeffStabilizesTo_partial_prod' h hconst) = lim :=
  tprod'_eq_of_coeffStabilizesTo_partial_prod h hconst
```

```lean
theorem isInverse_unique {a b c : L} (h1 : IsInverse a b) (h2 : IsInverse a c) : b = c :=
  AlgebraicCombinatorics.DividingFPS.inverse_unique h1 h2
```

```lean
theorem laurentPoly_unity_and_invertible : (1 : LaurentPoly K) = T 0 ∧ IsUnit (T 1 : LaurentPoly K) := by
  constructor
  · exact laurentPolynomial_one_eq_T_zero
  · exact T_isUnit
```

The first two look much better than the previous generation. The Laurent output
is still broad and likely mismatched to the declaration-level `T_inv` target.

## Does One Book LaTeX Theorem as Elementary Unit Work?

It works as the orchestration unit, not as the current one-row verifier unit.

Why one LaTeX theorem as one Lean declaration does not work reliably:

- A single source theorem often contains multiple claims, parts, or implicit
  constructions.
- Lean frequently splits these into definitions, instances, helper lemmas, and
  final theorems.
- Some book claims correspond to typeclass instances rather than propositions.
- Some Lean declarations are wrappers around earlier imported formalizations.
- Some source theorem environments contain a theorem plus subsequent
  definitions/propositions in the source span.

The Laurent failure is the clearest example. The book theorem says roughly:

- the Laurent-polynomial module is a commutative algebra;
- the unity is `T 0`;
- `x` is invertible.

The current benchmark row was the single Lean declaration `T_inv`. The generator
produced a bundled unity-and-invertibility theorem. For book-level progress, that
is partially useful. For the current declaration-level grader, it is wrong.

Recommended interpretation:

- **Book theorem**: planning and accounting unit.
- **Lean declaration**: generation and verification subtask.
- **Theorem pass**: all required declarations for that source theorem compile
  and the final intended statement(s) are proven.

## Neuralgic Points

### 1. Source Unit Mismatch

The current evaluator asks for one theorem/lemma per row. The user's mental model
is one book theorem per unit. Both are valid, but they belong at different
levels. The pipeline needs an explicit theorem-to-declarations planning layer.

### 2. Source-Part Selection

Many TeX spans are broad. In the 64-row audit, most spans were broad or
multi-environment. The selector must decide which part of a shared source label
is the current declaration target. The new `same_label_progress_summary` and
`supporting_context_boundary` fields are a first fix, but not a complete
solution.

### 3. Target-Shape Selection

Even when the model understands the math, it can choose the wrong Lean statement
shape:

- conjunction instead of a single equality;
- raw equations instead of a local predicate;
- bundled theorem instead of one declaration;
- typeclass assertion where Lean expects an instance or existing instance use.

This is currently a larger source of failure than raw Mathlib name lookup.

### 4. Mathlib Context Retrieval

Mathlib context collection is implemented and useful, but still shallow:

- the selector proposes names/queries;
- local Mathlib source is searched;
- snippets are inserted into `minimal_context.mathlib_context`.

Weaknesses:

- search can return overloaded or wrong namespace hits;
- snippets are not checked with `#check`;
- selected names are not always sufficient to determine theorem shape;
- the field `mathlib_context` currently also carries selector notes and project
  context, so it is overloaded.

The next improvement should split:

- `selected_mathlib_context`;
- `selected_project_context`;
- `selector_statement_plan`;
- `proof_notes`.

### 5. Previous-Project Context

This is the strongest positive result. The verified passes came from selecting
and applying previous project theorems:

- `alternant_swap` via imported `AlgebraicCombinatorics.alternant_swap`;
- `isInverse_unique` via imported `inverse_unique`.

Risk: previous-project context can accidentally reveal a target-shaped theorem
when imported declarations have the same source label and similar names. The
current audit reports target-name leaks and allowed previous-project overlaps,
but theorem-level production should distinguish "usable prior theorem" from
"the exact target was visible."

### 6. Prompt Size and Batching

Batch size `2` works with the current verbose schema. Batch size `4` has often
truncated. Batching remains attractive, but the schema needs to be smaller or
split into two rounds:

1. cheap source-part and context-name selection;
2. hydration/verification/second-round context refinement only when needed.

### 7. Benchmark Honesty

The current rows are generated from the existing Lean formalization. This is
fine for measuring whether target-blind source/context prompts can reproduce
known declarations. It is not the same as proving that the system can formalize
a new book theorem from scratch.

Gold comparison must stay post-hoc. It should never feed target Lean statements
into the selector/generator for source-only experiments.

### 8. Verification Surface

Serial Lean verification is not currently the conceptual bottleneck. The harder
issue is that the verifier expects one generated declaration matching one hidden
target. For theorem-level production, the verifier should accept a generated
file containing multiple declarations and report per-declaration and final
source-theorem status.

## Recommended Pipeline Revision

### Stage A: Source Theorem Index

Parse each LaTeX theorem/environment into a source work item:

- source file/path/range;
- labels;
- theorem/proposition/definition kind;
- part markers;
- referenced previous labels;
- nearby definitions/notations.

### Stage B: Theorem-Level Planning Selector

Prompt a cheap selector to produce:

- mathematical claim decomposition;
- likely Lean declarations needed;
- prior source labels/theorems needed;
- Mathlib areas and exact APIs to hydrate;
- uncertainty list.

Output should be a list of declaration tasks, not one theorem.

### Stage C: Context Hydration

Resolve requested context with tools:

- local project declarations by source label and imports;
- Mathlib source snippets;
- `#check` or Lean environment lookup for exact signatures;
- namespace/import provenance.

### Stage D: Second-Round Context Critic

Only when useful, ask a cheap model:

- Is the selected context enough for each declaration task?
- Are there overloaded/wrong Mathlib names?
- Are prior facts support-only or target conclusions?

### Stage E: Generation

Generate either:

- one declaration at a time, if the source theorem decomposes cleanly; or
- one small Lean file containing ordered declarations for the source theorem.

The latter matches the user's "one book theorem" intuition better.

### Stage F: Verification and Repair

Verify:

- generated-only compile;
- each planned declaration;
- final theorem-level source objective.

Repair should use compiler errors and visible context only. For hard cases, a
coding agent can inspect the generated project and fix a small fraction of
failures.

## Full Current Prompt Contracts

The exact instantiated prompts, including full dynamic context, are logged in
the run artifacts. Representative current payloads:

- selector batch 1:
  `docs/source-statement-runs/2026-05-05-context-selection-decl-progress-diverse3-paid/batch-001/context-selection-payload.json`
- selector batch 2:
  `docs/source-statement-runs/2026-05-05-context-selection-decl-progress-diverse3-paid/batch-002/context-selection-payload.json`
- generator record 1:
  `docs/source-statement-runs/2026-05-05-decl-progress-diverse3-generation-paid/record-001/openrouter-payload.json`
- generator record 2:
  `docs/source-statement-runs/2026-05-05-decl-progress-diverse3-generation-paid/record-002/openrouter-payload.json`
- generator record 3:
  `docs/source-statement-runs/2026-05-05-decl-progress-diverse3-generation-paid/record-003/openrouter-payload.json`

Below are the full static prompt contracts from the current code path.

### Context Selector System Prompt

```text
You are a Lean 4/Mathlib context-selection agent. Your task is to prepare a compact context pack for a later autoformalization agent. You see only source-side mathematical text plus prefix/local Lean context. The target Lean declaration name, statement, and proof are withheld. Return exactly one JSON object.
```

### Context Selector User Prompt Skeleton

```json
{
  "task": "For each record, sketch the formalization and select the tight local/Mathlib context a later proof-writing model should see. Prefer a few thousand tokens or less of Mathlib facts per record.",
  "required_json_schema": {
    "records": [
      {
        "record_key": "record-001",
        "source_focus_summary": "what precise source statement or part should be formalized",
        "selected_source_part": "the single declaration-level source part chosen for the withheld row; not a bundle of prior/supporting facts",
        "source_part_rationale": "why this one part was chosen, using source labels and prefix progress when available",
        "supporting_context_boundary": "which displayed prior/imported facts are support only and must not be restated or bundled into the target theorem",
        "formalization_sketch": [
          "Lean-level sketch of the likely statement shape and proof plan, without inventing hidden target names"
        ],
        "needed_local_context": [
          {
            "name_or_snippet": "displayed local declaration/notation/variable needed",
            "why_needed": "role in statement/proof"
          }
        ],
        "candidate_project_context": [
          {
            "name": "previous imported project declaration name, if useful",
            "expected_signature_or_shape": "signature shape if known from the provided context",
            "why_needed": "why this previous formalized statement belongs in the later context pack",
            "confidence": 0.0
          }
        ],
        "mathlib_queries": [
          "narrow Mathlib search phrase or expected declaration name, e.g. Nat.choose_symm"
        ],
        "candidate_mathlib_context": [
          {
            "name": "exact or likely Mathlib declaration name",
            "kind": "theorem|lemma|def|notation|tactic|typeclass|unknown",
            "expected_signature_or_shape": "signature shape if known",
            "why_needed": "why this belongs in the later context pack",
            "confidence": 0.0
          }
        ],
        "proof_notes": [
          "brief notes that may prevent API/type-signature mistakes"
        ],
        "uncertainties": [
          "what may require Mathlib/source lookup in a second round"
        ]
      }
    ]
  },
  "selection_budget": {
    "max_added_context_tokens_per_record": 4000,
    "prefer_exact_signatures_over_long_files": true,
    "prefer_few_precise_facts_over_broad_import_dumps": true
  },
  "instructions": [
    "Do not ask for or infer the withheld target Lean declaration name, statement, or proof.",
    "Do not rely on legacy broad `Mathlib` imports as context; select concrete APIs/signatures/docstrings needed by the later generator.",
    "If a Mathlib name is uncertain, return a narrow search query plus the expected type/signature shape.",
    "Include previous formalized local declarations only if they are displayed in the prefix/local context.",
    "If `source_progress_context.imported_source_label_declarations` contains a previous imported project theorem matching the selected source part, include it in `candidate_project_context` and prefer it over reproving a long result.",
    "The benchmark rows are declaration-level targets aligned to source labels, not one row per LaTeX theorem environment. Select one likely target declaration, not every claim under the label.",
    "If `source_progress_context.same_label_progress_summary` or `prior_same_label_declarations` shows that earlier declarations already formalized source parts, do not re-formalize those parts or bundle them into a conjunction; select the remaining/next declaration-level part.",
    "Do not infer that the target should bundle all imported/prior same-label facts just because several such facts are available. Put reused facts in `candidate_project_context` and explain their boundary in `supporting_context_boundary`.",
    "Separate mathematical understanding from Lean API uncertainty in `uncertainties`.",
    "Do not over-select: every requested fact should have a role in statement typing or proof construction."
  ],
  "global_mathlib_overview": "<computed from local Mathlib tree>",
  "records": "<source-only per-record payloads>"
}
```

### Proof Generator System Prompt

```text
You are a Lean 4 autoformalization agent working in a current Mathlib-only project. You must formalize the provided TeX/math source chunk into one Lean theorem or lemma, including a proof, using only the Lean prefix context provided. The target Lean statement, target declaration name, and original proof are intentionally withheld. Avoid stale Lean 3/old Mathlib syntax and identifiers; follow the lean_environment/current_version_guidance and local Lean examples. Return exactly one JSON object.
```

### Proof Generator User Prompt Skeleton

```json
{
  "task": "Formalize the source chunk as one Lean theorem/lemma and prove it.",
  "required_json_schema": {
    "lean_declaration": "one complete Lean theorem or lemma, including proof/body; do not include imports or markdown",
    "declaration_name": "the local name you gave that theorem/lemma",
    "used_context": [
      "short list of source/context facts used"
    ],
    "notes": [
      "brief caveats, if any"
    ]
  },
  "instructions": [
    "Do not use sorry, admit, aesop? placeholders, or comments standing in for proof.",
    "Do not include import statements; the generated file already imports Mathlib.",
    "Do not assume access to the withheld target Lean statement or name.",
    "For multi-part TeX chunks, formalize only the specified labeled part/source span. Do not conjoin all parts unless the record explicitly asks for the whole multi-part result.",
    "This benchmark row expects one declaration-level theorem/lemma, not a restatement of every source claim sharing the same TeX label.",
    "Do not cite or invent raw helper names that are not present in the Lean prefix context/local examples; prefer displayed local style and standard Mathlib APIs.",
    "Do not redeclare definitions, structures, abbrevs, notation helpers, or instances already present in the Lean prefix context; reference them directly.",
    "Do not introduce theorem-local `where` definitions or redefine concepts such as summability, limits, binomial coefficients, or matrix operations. If a needed definition is not in context, state a narrower theorem using the displayed APIs.",
    "Use current Lean 4/Mathlib syntax and API names; if your memory conflicts with displayed local context, trust the displayed context.",
    "State a single proposition-level theorem/lemma that is likely to match the specified source part; do not bundle typeclass instances or unrelated source parts into conjunctions.",
    "Every nonstandard helper theorem or local API used in the proof should appear explicitly in the Lean prefix context or local examples. If it is not displayed, do not use its name.",
    "If source_progress_context lists imported_source_label_declarations for the selected source part, prefer applying those previous formalized project theorems over reproving a long imported result.",
    "If source_progress_context says a prior/imported same-label declaration is support only, use it as a proof fact but do not include it as an extra conclusion of the generated theorem.",
    "When a displayed local/project signature uses named implicit arguments such as `(R := R)`, preserve those named arguments in your theorem statement and proof terms rather than relying on typeclass inference.",
    "If an existing theorem or lemma in the prefix context has binders, apply it to the needed variables rather than using the theorem constant bare.",
    "Prefer the narrowest theorem directly supported by the source sentence; avoid generalizing to a stronger forall/if statement unless that exact shape is in the source or prefix context.",
    "Prefer a short proof if the prefix context already contains the needed fact."
  ],
  "context": "<source-only context pack with selected Mathlib/project context>"
}
```

### Repair System Prompt

```text
You are a Lean 4 repair agent. Repair exactly one generated theorem/lemma so it compiles in the displayed current Lean/mathlib project. The original target Lean statement and target declaration name are still withheld. Do not ask for or infer hidden grader text. Use only the source chunk, prefix context, imports, local examples, the failed generated declaration, and compiler errors or visible-context shape diagnostics. Return exactly one JSON object.
```

### Repair User Prompt Skeleton

```json
{
  "task": "Repair the failed generated Lean declaration. Return one complete theorem or lemma including proof; no imports and no markdown.",
  "required_json_schema": {
    "lean_declaration": "one complete corrected Lean theorem or lemma including proof/body",
    "declaration_name": "the local name of the corrected theorem/lemma",
    "used_context": [
      "short list of source/context/compiler facts used"
    ],
    "notes": [
      "brief caveats, if any"
    ]
  },
  "repair_rules": [
    "Do not use sorry, admit, placeholders, or comments as proof.",
    "Do not return a conjunction or broad bundled theorem when the source focus is a narrow identity.",
    "If the previous declaration over-generalized, narrow it to the single source sentence most directly supported by the context.",
    "Use explicit type annotations for polymorphic terms when Lean could leave typeclass metavariables stuck.",
    "For PowerSeries coefficients use argument order `coeff n f`.",
    "For Laurent polynomials use `LaurentPolynomial.T n`, not bare `X` or bare `T` unless the prefix context defines it.",
    "Do not redeclare context definitions; reference them directly.",
    "Do not add theorem-local `where` definitions or redefine project concepts; repair using the displayed APIs instead.",
    "Do not introduce helper theorem names that were not displayed in the original context or compiler output.",
    "If shape diagnostics are provided, rewrite the statement/proof to address those visible-context warnings without using or guessing hidden grader text."
  ],
  "original_prompt_user_payload": "<original generator user payload>",
  "failed_generated_declaration": "<failed Lean declaration>",
  "generated_only_lean_exit_code": "<compiler exit code>",
  "generated_only_lean_output": "<compiler output>",
  "repair_domain_guidance": "<optional visible-context repair hints>",
  "shape_diagnostic_warnings": "<optional target-blind shape diagnostics>"
}
```

## Bottom Line

The approach is plausible, but the pipeline should be reframed:

- Use one book LaTeX theorem as a source theorem work item.
- Let the selector decompose it into Lean declaration tasks.
- Keep declaration-level verification as the inner loop.
- Report theorem-level completion as the outer loop.

The current declaration-level benchmark is still valuable because it exposes
precisely where context selection, statement planning, and proof generation
fail. It should not be mistaken for the final production unit.
