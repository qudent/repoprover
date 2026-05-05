"""Tests for target-statement-withheld source-statement eval prompts."""

from __future__ import annotations

import argparse
import copy
import json
import threading
import time
from pathlib import Path

from scripts.materialize_minimal_context_smoke import SelectedRecord
from scripts.run_source_statement_live_eval import (
    balanced_tex_line_range,
    build_messages,
    build_repair_messages,
    classify_lean_failure,
    copy_local_import_closure,
    generated_application_candidates,
    gold_check_declaration,
    import_modules_from_lean,
    local_import_path,
    materialize_candidate_project,
    run,
    select_source_statement_records,
    tex_source_focus,
)


def _write_fixture_project(tmp_path: Path) -> tuple[Path, SelectedRecord]:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "Demo.lean").write_text(
        "\n".join(
            [
                "import Mathlib",
                "open scoped Matrix BigOperators",
                "open Finset Matrix",
                "",
                "namespace Demo",
                "",
                "variable {R : Type*} [CommRing R]",
                "",
                "/-- The submatrix helper used by the local notation. -/",
                "noncomputable def submatrixOfFinset {n m : Nat} (A : Matrix (Fin n) (Fin m) R)",
                "    (U : Finset (Fin n)) (V : Finset (Fin m)) :",
                "    Matrix (Fin U.card) (Fin V.card) R :=",
                "  A.submatrix (U.orderEmbOfFin rfl) (V.orderEmbOfFin rfl)",
                "",
                "/-- Notation for submatrices: `sub[U,V] A` denotes sub_U^V A. -/",
                'scoped notation "sub[" U "," V "] " A => submatrixOfFinset A U V',
                "",
                "/-- Local style example: use Mathlib's `.submatrix` API for diagonal principal minors. -/",
                "example {n : Nat} (d : Fin n -> R) (P : Finset (Fin n)) :",
                "    ((Matrix.diagonal d).submatrix (P.orderEmbOfFin rfl) (P.orderEmbOfFin rfl)).det =",
                "    ∏ i ∈ P, d i := by",
                "  sorry",
                "",
                "/-- Named local API that should be retrievable before the target. -/",
                "theorem det_local_api : True := by",
                "  trivial",
                "",
                "/-- Part (a): target declaration withheld in prompts.",
                "    Label: demo.minors.a -/",
                "theorem target {n : Nat} (d : Fin n -> R) (P : Finset (Fin n)) : True := by",
                "  trivial",
                "",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "Demo.tex").write_text(
        "\\begin{lemma}\\label{demo.minors} Then: "
        "\\textbf{(a)} principal minors are products. "
        "\\textbf{(b)} off-diagonal minors vanish.\\end{lemma}\n",
        encoding="utf-8",
    )
    row = {
        "id": "Demo.lean:Demo.target",
        "alignment": {
            "comment_labels": ["demo.minors", "demo.minors.a"],
            "paired_source_path": "Demo.tex",
            "source_method": "lean_comment_label",
        },
        "output": {
            "lean_path": "Demo.lean",
            "declaration_names": ["Demo.target"],
            "line_range": [28, 31],
            "chunk_kind": "theorem",
        },
        "minimal_context": {
            "source_spans": [{"path": "Demo.tex", "line_range": [1, 1], "labels": ["demo.minors"]}],
            "file_context": [
                {"path": "Demo.lean", "kind": "open", "line_range": [2, 2], "name": "open scoped Matrix BigOperators"},
                {"path": "Demo.lean", "kind": "open", "line_range": [3, 3], "name": "open Finset Matrix"},
                {"path": "Demo.lean", "kind": "namespace", "line_range": [5, 5], "name": "Demo"},
                {"path": "Demo.lean", "kind": "variable", "line_range": [7, 7], "name": "variable {R : Type*} [CommRing R]"},
                {
                    "path": "Demo.lean",
                    "kind": "notation",
                    "line_range": [16, 16],
                    "name": 'scoped notation "sub[" U "," V "] " A => submatrixOfFinset A U V',
                },
            ],
            "lean_predecessors": [],
            "mathlib_context": ["Mathlib context"],
        },
    }
    return project_root, SelectedRecord(row)


def test_source_statement_prompt_includes_local_style_and_notation_contract(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)

    messages = build_messages(project_root, record)
    user = json.loads(messages[1]["content"])
    context = user["context"]
    local_style = context["local_lean_style"]
    guide = "\n".join(local_style["guidance"])
    examples = "\n".join(local_style["examples"])

    assert "sub[U,V] A" in guide
    assert "submatrixOfFinset A U V" in guide
    assert "do not cite or invent raw helper names" in guide
    assert "more familiar but different API" in guide
    assert "scoped notation" in examples
    assert "noncomputable def submatrixOfFinset" in examples
    assert "((Matrix.diagonal d).submatrix" in examples
    assert "theorem target" not in examples


def test_source_statement_prompt_focuses_specific_part_of_multipart_source(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)

    messages = build_messages(project_root, record)
    user = json.loads(messages[1]["content"])
    instructions = "\n".join(user["instructions"])
    focus = user["context"]["target_source_focus"]

    assert focus["specific_source_labels"] == ["demo.minors.a"]
    assert focus["specific_labeled_parts"] == ["a"]
    assert "formalize only the specified labeled part/source span" in instructions
    assert "Do not conjoin all parts" in instructions


def test_source_statement_prompt_includes_tex_derived_focus(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)

    messages = build_messages(project_root, record, context_mode="source-only")
    user = json.loads(messages[1]["content"])
    tex_focus = user["context"]["tex_source_focus"][0]

    assert tex_focus["declared_labels"] == ["demo.minors"]
    assert "lemma" in tex_focus["environments"]
    assert tex_focus["part_markers"][0]["part"] == "a"
    assert "principal minors" in tex_focus["part_markers"][0]["excerpt"]
    assert "Demo.target" not in json.dumps(tex_focus)
    assert "theorem target" not in json.dumps(tex_focus)
    assert tex_focus["policy"].startswith("derived only from provided TeX")


def test_tex_source_focus_flags_unclosed_environment_after_closed_earlier_environment() -> None:
    focus = tex_source_focus(
        [
            {
                "path": "Demo.tex",
                "line_range": [10, 20],
                "labels": ["def.demo"],
                "snippet": (
                    "\\begin{definition}\\label{def.demo}A definition.\\end{definition}\n"
                    "\\begin{example}An example.\\end{example}\n"
                    "\\begin{proposition}\n"
                ),
            }
        ]
    )[0]

    assert "snippet_ends_with_unclosed_environment:proposition" in focus["span_risks"]


def test_balanced_tex_line_range_expands_to_close_environment(tmp_path: Path) -> None:
    tex = tmp_path / "Demo.tex"
    tex.write_text(
        "\n".join(
            [
                "\\begin{definition}",
                "\\label{def.demo}A definition.",
                "\\end{definition}",
                "\\begin{proposition}",
                "The useful proposition body.",
                "\\end{proposition}",
                "Afterward.",
            ]
        ),
        encoding="utf-8",
    )

    start, end, reasons = balanced_tex_line_range(tex, 2, 4)

    assert (start, end) == (1, 6)
    assert reasons == [
        "expanded_backward_to_include_environment_begin",
        "expanded_forward_to_close_environment",
    ]


def test_source_statement_prompt_includes_current_lean_environment_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")

    messages = build_messages(project_root, record)
    system = messages[0]["content"]
    user = json.loads(messages[1]["content"])
    instructions = "\n".join(user["instructions"])
    environment = user["context"]["lean_environment"]
    guidance = "\n".join(environment["current_version_guidance"])

    assert "current Mathlib-only project" in system
    assert environment["toolchain"] == "leanprover/lean4:v4.28.0"
    assert "Lean 3" in guidance
    assert "LaurentPolynomial.X" in guidance
    assert "typeclass objects" in guidance
    assert "Use current Lean 4/Mathlib syntax" in instructions
    assert "do not bundle typeclass instances" in instructions
    assert "Do not introduce theorem-local `where` definitions" in instructions
    assert "Every nonstandard helper theorem or local API" in instructions


def test_repair_prompt_uses_generated_only_error_without_grader_feedback(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    messages = build_messages(project_root, record)

    repair_messages = build_repair_messages(
        original_messages=messages,
        failed_declaration="theorem bad : True := by\n  exact missingFact",
        generated_only_lean_result={"exit_code": 1, "output": "unknown identifier 'missingFact'"},
    )
    system = repair_messages[0]["content"]
    user = json.loads(repair_messages[1]["content"])
    prompt_text = json.dumps(user, ensure_ascii=False)

    assert "target Lean statement and target declaration name are still withheld" in system
    assert "theorem bad : True" in user["failed_generated_declaration"]
    assert "unknown identifier 'missingFact'" in user["generated_only_lean_output"]
    assert "__repoprover_source_statement_check" not in prompt_text
    assert "theorem target" not in prompt_text


def test_source_statement_context_does_not_duplicate_notation_support(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    row = copy.deepcopy(record.row)
    row["minimal_context"]["lean_predecessors"] = [
        {"path": "Demo.lean", "declaration": "Demo.submatrixOfFinset", "line_range": [9, 13]},
    ]

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    prefix = user["context"]["lean_prefix_context"]

    assert prefix.count("noncomputable def submatrixOfFinset") == 1
    assert "Do not redeclare definitions" in "\n".join(user["instructions"])
    assert "apply it to the needed variables" in "\n".join(user["instructions"])


def test_source_statement_context_includes_retrieved_local_api_without_target(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)

    messages = build_messages(project_root, record)
    user = json.loads(messages[1]["content"])
    prefix = user["context"]["lean_prefix_context"]
    target_path = materialize_candidate_project(
        project_root=project_root,
        output_root=tmp_path / "out",
        record=record,
        lean_declaration="theorem generated : True := by\n  trivial",
        generated_name="generated",
        lake_cache_from=None,
        include_grader=False,
    )
    materialized = target_path.read_text(encoding="utf-8")

    assert "-- Local API retrieval: Demo.lean" in prefix
    assert "theorem det_local_api : True := by" in prefix
    assert "Part (a): target declaration withheld" not in prefix
    assert "theorem det_local_api : True := by" in materialized
    assert "theorem target" not in prefix
    assert "theorem target" not in materialized


def test_source_statement_context_retrieves_imported_label_api_without_target(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    imported = project_root / "AlgebraicCombinatorics" / "FPS" / "Limits.lean"
    imported.parent.mkdir(parents=True)
    imported.write_text(
        "\n".join(
            [
                "import Mathlib",
                "namespace Demo",
                "",
                "/-- Imported theorem aligned to the same source part.",
                "Label: demo.minors.a -/",
                "theorem imported_label_api : True := by",
                "  trivial",
                "",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["minimal_context"]["imports"] = ["Mathlib", "AlgebraicCombinatorics.FPS.Limits"]

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    prefix = user["context"]["lean_prefix_context"]

    assert "Imported API retrieval by source label `demo.minors.a`" in prefix
    assert "theorem imported_label_api : True := by" in prefix
    assert "theorem target" not in prefix

    target_path = materialize_candidate_project(
        project_root=project_root,
        output_root=tmp_path / "out-imported",
        record=SelectedRecord(row),
        lean_declaration="theorem generated : True := imported_label_api",
        generated_name="generated",
        lake_cache_from=None,
        include_record_imports=True,
        include_grader=False,
    )
    materialized = target_path.read_text(encoding="utf-8")
    assert "import AlgebraicCombinatorics.FPS.Limits" in materialized
    assert "theorem imported_label_api : True := by" not in materialized
    assert "theorem target" not in materialized


def test_source_statement_prompt_includes_fps_limit_shape_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "If the family is summable, the limit of the partial sums is the infinite sum.\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["minimal_context"]["imports"] = ["Mathlib", "AlgebraicCombinatorics.FPS.Limits"]

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance = user["context"]["domain_statement_shape_guidance"]
    guidance_text = json.dumps(guidance)

    assert user["context"]["available_imports"] == ["Mathlib", "AlgebraicCombinatorics.FPS.Limits"]
    assert "formal power series limits" in guidance_text
    assert "CoeffStabilizesTo" in guidance_text
    assert "IsSummable" in guidance_text
    assert "tsum'" in guidance_text
    assert "Do not bundle `IsSummable f` and `tsum' f ... = L` into a conjunction" in guidance_text
    assert "TopologicalSpace" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_narrows_fps_limit_when_comment_only_asks_summable(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "If the limit of partial sums exists, then the family is summable and later the sum can be identified.\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["minimal_context"]["imports"] = ["Mathlib", "AlgebraicCombinatorics.FPS.Limits"]
    lines = (project_root / "Demo.lean").read_text(encoding="utf-8").splitlines()
    lines[27] = "/-- If partial sums converge, the family is summable - detailed proof."
    lines[28] = "    Label: demo.minors.a -/"
    (project_root / "Demo.lean").write_text("\n".join(lines) + "\n", encoding="utf-8")

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"], ensure_ascii=False)

    assert "conclude only `IsSummable f`" in guidance_text
    assert "Do not include a `tsum'` equality" in guidance_text
    assert "And.intro" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_includes_fps_indeterminate_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "Definition def.fps.x: the indeterminate x has coefficient 1 at x^1 and 0 elsewhere.\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["def.fps.x"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["def.fps.x"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/FPSDefinition.lean"

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"], ensure_ascii=False)

    assert "formal power series indeterminate" in guidance_text
    assert "coeff_X" in guidance_text
    assert "coeff_one_X" in guidance_text
    assert "rfl" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_includes_x_power_multiplication_shape_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "Lemma lem.fps.xa: f * X^k shifts f by k positions.\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["lem.fps.xa"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["lem.fps.xa"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/FPSDefinition.lean"

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"], ensure_ascii=False)

    assert "formal power series multiplication by powers of X" in guidance_text
    assert "coeff_mul_X_pow" in guidance_text
    assert "coeff_X_pow_mul" in guidance_text
    assert "opposite multiplication order" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_keeps_special_x_shift_separate_from_x_power_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "Lemma lem.fps.xa: x a is the FPS (0, a_0, a_1, a_2, ...).\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["lem.fps.xa"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["lem.fps.xa"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/FPSDefinition.lean"

    messages = build_messages(project_root, SelectedRecord(row), context_mode="source-only")
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"], ensure_ascii=False)

    assert "formal power series multiplication by X" in guidance_text
    assert "formal power series multiplication by powers of X" not in guidance_text
    assert "X * f" in guidance_text
    assert "f * X ^ k" in guidance_text


def test_source_statement_prompt_includes_substitution_shape_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text("Proposition prop.fps.subs.rules: g composed with X equals g.\n", encoding="utf-8")
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["prop.fps.subs.rules"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["prop.fps.subs.rules"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/FPS/Substitution.lean"

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"], ensure_ascii=False)

    assert "formal power series substitution" in guidance_text
    assert "PowerSeries.subst X g" in guidance_text
    assert "HasSubst.X'" in guidance_text
    assert "coeff_subst'" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_includes_finite_finsum_substitution_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "Lemma fps_comp_coeff_finite: the coefficient of finite composition follows by restricting finsum support.\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["fps_comp_coeff_finite"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["fps_comp_coeff_finite"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/FPS/Substitution.lean"

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"], ensure_ascii=False)

    assert "finsum_eq_sum_of_support_subset" in guidance_text
    assert "apply finsum_eq_sum_of_support_subset" in guidance_text
    assert "intro d hd" in guidance_text
    assert "fps_subs_wd_firstCoeffs" in guidance_text
    assert "wrong-arity `finsum_eq_sum`" in guidance_text
    assert "intro d in" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_includes_negative_binomial_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "Theorem fps_newtonBinomial_neg gives the inverse of (1 + X)^n using Ring.choose (-(n : ℤ)).\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["fps_newtonBinomial_neg"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["fps_newtonBinomial_neg"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/DividingFPS.lean"

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"], ensure_ascii=False)

    assert "negative binomial formal power series" in guidance_text
    assert "negative-binomial inverse-power theorem" in guidance_text
    assert "fps_onePlusX_pow_neg'" in guidance_text
    assert "fps_onePlusX_pow_neg' (F := F) n" in guidance_text
    assert "fps_onePlusX_pow_neg' F n" in guidance_text
    assert "Ring.choose (-(n : ℤ)) k : F" in guidance_text
    assert "BinomialRing F" in guidance_text
    assert "fps_newtonBinomial_neg" not in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_includes_multivariate_projection_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "Proposition prop.fps.mulvar.comp-y-coeff compares coefficients of y^k in K[[x,y]].\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["prop.fps.mulvar.comp-y-coeff"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["prop.fps.mulvar.comp-y-coeff"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/FPS/Multivariate.lean"

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"])

    assert "multivariate FPS coefficient projection" in guidance_text
    assert "coeff_embedUnivInBiv" in guidance_text
    assert "Finsupp.single 0 n + Finsupp.single 1 k" in guidance_text
    assert "PowerSeries.ext" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_includes_infprod_substitution_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "Proposition prop.fps.subs.rule-infprod: multipliable products use prod_f and finite approximators M/J.\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["prop.fps.subs.rule-infprod"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["prop.fps.subs.rule-infprod"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/Details/InfiniteProducts2.lean"

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"])

    assert "formal power series infinite product substitution" in guidance_text
    assert "prod_f" in guidance_text
    assert "comp_prod_finite" in guidance_text
    assert "map_tprod" in guidance_text
    assert "TopologicalSpace" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_includes_partition_transpose_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "Proposition prop.pars.pkn=dual: transpose swaps number of parts with largest part.\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["prop.pars.pkn=dual"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["prop.pars.pkn=dual"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/Partitions/Basics.lean"

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"])

    assert "partition transpose cardinality" in guidance_text
    assert "transpose_transpose" in guidance_text
    assert "transpose_length_eq_largestPart" in guidance_text
    assert "Finset.card_congr" in guidance_text
    assert ".numParts" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_includes_partition_zero_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "For p : Partition 0, the parts of p are zero, so there is a unique partition of 0.\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["partition_zero"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["partition_zero"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/Partitions/Basics.lean"

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"])

    assert "partition_zero_parts" in guidance_text
    assert "p.parts" in guidance_text
    assert "p.parts = 0" in guidance_text
    assert ".entries" in guidance_text
    assert ".sum_eq" in guidance_text
    assert "unless they appear in the prompt" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_includes_simple_transposition_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "Definition def.perm.si: simple transposition s_i fixes k when k is not i or i+1.\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["def.perm.si"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["def.perm.si"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/Permutations/Basics.lean"

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"])

    assert "simple transposition statement shape" in guidance_text
    assert "Equiv.swap_apply_of_ne_of_ne" in guidance_text
    assert "k.val" in guidance_text
    assert "i.val" in guidance_text
    assert "Fin-object inequalities" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_includes_permutation_power_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "For a permutation α, the power α ^ (n + 1) applies as α after α ^ n by function composition.\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["perm_pow_succ"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["perm_pow_succ"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/Permutations/Basics.lean"

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"], ensure_ascii=False)

    assert "Equiv.Perm.coe_mul" in guidance_text
    assert "Function.comp_apply" in guidance_text
    assert "α ^ (n + 1) = α ^ n * α" in guidance_text
    assert "Function.iterate" in guidance_text
    assert "Equiv.mul_apply" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_includes_simple_transposition_isswap_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "Demo.tex").write_text(
        "The simple transposition s_i is a swap.\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = ["simpleTransposition_isSwap"]
    row["minimal_context"]["source_spans"][0]["labels"] = ["simpleTransposition_isSwap"]
    row["output"]["lean_path"] = "AlgebraicCombinatorics/Permutations/Basics.lean"

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"])

    assert "(simpleTransposition i).IsSwap" in guidance_text
    assert "constructor-style proof shape" in guidance_text
    assert "displayed local `IsSwap` theorem" in guidance_text
    assert "simpleTransposition_isSwap" not in guidance_text
    assert "Equiv.swap_isSwap" in guidance_text
    assert "Do not answer only `simpleTransposition i = transposition ...`" in guidance_text
    assert "theorem target" not in guidance_text


def test_source_statement_prompt_includes_source_facing_target_comment(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)

    messages = build_messages(project_root, record)
    user = json.loads(messages[1]["content"])
    focus = user["context"]["target_source_focus"]

    assert focus["target_declaration_source_comment"]["text"].startswith("Part (a): target declaration withheld")
    assert focus["target_declaration_source_comment"]["policy"].startswith("source-facing Lean doc comment")
    assert "target Lean declaration name and statement remain withheld" in focus["target_declaration_source_comment"]["policy"]
    assert "theorem target" not in json.dumps(focus)


def test_source_only_context_mode_excludes_target_comment_and_target_labels(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)

    messages = build_messages(project_root, record, context_mode="source-only")
    user = json.loads(messages[1]["content"])
    context = user["context"]
    focus = context["target_source_focus"]
    serialized = json.dumps(context, ensure_ascii=False)

    assert context["context_mode"] == "source-only"
    assert focus["context_mode"] == "source-only"
    assert focus["target_declaration_source_comment"] is None
    assert focus["record_comment_labels"] == []
    assert focus["specific_source_labels"] == []
    assert "Part (a): target declaration withheld" not in serialized
    assert "demo.minors.a" not in serialized
    assert "Demo.target" not in serialized
    assert "theorem target" not in serialized


def test_source_only_context_mode_does_not_use_hidden_name_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    row = copy.deepcopy(record.row)
    row["alignment"]["comment_labels"] = []
    row["minimal_context"]["source_spans"][0]["labels"] = ["def.perm.si"]
    row["minimal_context"]["source_spans"][0]["path"] = "Demo.tex"
    row["output"]["lean_path"] = "AlgebraicCombinatorics/Permutations/Basics.lean"
    row["output"]["declaration_names"] = ["AlgebraicCombinatorics.simpleTransposition_isSwap"]
    (project_root / "Demo.tex").write_text("The simple transposition s_i swaps i and i+1.\n", encoding="utf-8")

    messages = build_messages(project_root, SelectedRecord(row), context_mode="source-only")
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["context"]["domain_statement_shape_guidance"])

    assert "(simpleTransposition i).IsSwap" not in guidance_text
    assert "constructor-style proof shape" not in guidance_text
    assert "simpleTransposition_isSwap" not in guidance_text


def test_source_only_context_mode_disables_imported_label_api_retrieval(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    imported_path = project_root / "AlgebraicCombinatorics/Imported.lean"
    imported_path.parent.mkdir(parents=True, exist_ok=True)
    imported_path.write_text(
        "\n".join(
            [
                "namespace Demo",
                "",
                "/-- A tempting imported theorem.",
                "Label: demo.minors -/",
                "theorem imported_by_label : True := by",
                "  trivial",
                "",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    row = copy.deepcopy(record.row)
    row["minimal_context"]["imports"] = ["Mathlib", "AlgebraicCombinatorics.Imported"]

    target_comment_messages = build_messages(project_root, SelectedRecord(row), context_mode="target-comment")
    target_comment_context = json.loads(target_comment_messages[1]["content"])["context"]
    source_only_messages = build_messages(project_root, SelectedRecord(row), context_mode="source-only")
    source_only_context = json.loads(source_only_messages[1]["content"])["context"]

    assert "imported_by_label" in json.dumps(target_comment_context)
    assert "imported_by_label" not in json.dumps(source_only_context)


def test_generated_application_candidates_try_explicit_then_all_binders() -> None:
    head = """theorem __repoprover_source_statement_check {n : ℕ} (d : Fin n → R) (P : Finset (Fin n)) :
    ((Matrix.diagonal d).submatrix (P.orderEmbOfFin rfl) (P.orderEmbOfFin rfl)).det =
    ∏ i ∈ P, d i"""

    assert generated_application_candidates("generated", head) == ["generated d P", "generated n d P", "generated"]


def test_generated_application_candidates_ignore_doc_comment_binders() -> None:
    head = """/-- Source says this holds for each `(k : ℕ)`. -/
theorem __repoprover_source_statement_check (k : ℕ) :
    (PowerSeries.X : PowerSeries ℚ) ^ k = PowerSeries.X ^ k"""

    assert generated_application_candidates("generated", head) == ["generated k", "generated"]


def test_generated_application_candidates_ignore_parenthesized_terms_in_statement() -> None:
    head = """theorem __repoprover_source_statement_check {lam mu : Fin N → ℕ} (T : Tableau lam mu) :
    (monomialTableau T : MvPolynomial (Fin N) R) = xPow (contentTableau T)"""

    assert generated_application_candidates("generated", head) == ["generated T", "generated lam mu T", "generated"]


def test_generated_application_candidates_parse_nested_type_binders() -> None:
    head = """theorem generated (α : Equiv.Perm X) (n : ℕ) :
    α ^ (n + 1) = α ^ n * α"""

    assert generated_application_candidates("generated", head) == ["generated α n", "generated"]


def test_gold_check_tries_generated_binder_order_before_gold_order(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "Demo.lean").write_text(
        "\n".join(
            [
                "import Mathlib",
                "namespace Demo",
                "theorem target (n k : ℕ) : n + k = n + k := by",
                "  rfl",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    record = SelectedRecord(
        {
            "id": "Demo.lean:Demo.target",
            "alignment": {},
            "output": {"lean_path": "Demo.lean", "declaration_names": ["Demo.target"], "line_range": [3, 4]},
            "minimal_context": {"source_spans": [], "lean_predecessors": [], "file_context": []},
        }
    )
    generated = "theorem generated (k n : ℕ) : n + k = n + k := by\n  rfl"

    check = gold_check_declaration(project_root, record, "generated", generated)

    assert "simpa using generated k n" in check
    assert "simpa using generated n k" in check
    assert check.index("generated k n") < check.index("generated n k")


def test_copy_local_import_closure_copies_recursive_local_imports(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    output_root = tmp_path / "out"
    dep = project_root / "AlgebraicCombinatorics" / "Dep.lean"
    mid = project_root / "AlgebraicCombinatorics" / "Mid.lean"
    dep.parent.mkdir(parents=True)
    dep.write_text("import Mathlib\n\ndef dep : True := True.intro\n", encoding="utf-8")
    mid.write_text("import AlgebraicCombinatorics.Dep\n\ndef mid : True := dep\n", encoding="utf-8")

    assert local_import_path("AlgebraicCombinatorics.Mid") == Path("AlgebraicCombinatorics/Mid.lean")
    assert import_modules_from_lean(mid) == ["AlgebraicCombinatorics.Dep"]

    copy_local_import_closure(
        project_root,
        output_root,
        ["Mathlib", "AlgebraicCombinatorics.Mid"],
        skip_paths=set(),
    )

    assert (output_root / "AlgebraicCombinatorics" / "Mid.lean").exists()
    assert (output_root / "AlgebraicCombinatorics" / "Dep.lean").exists()


def test_materialize_candidate_project_can_include_record_imports_without_copying_target(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    target = project_root / "AlgebraicCombinatorics" / "Target.lean"
    dep = project_root / "AlgebraicCombinatorics" / "Dep.lean"
    target.parent.mkdir(parents=True)
    (project_root / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
    (project_root / "lake-manifest.json").write_text('{"version":"1.1.0","packages":[],"name":"demo"}\n', encoding="utf-8")
    (project_root / "lakefile.lean").write_text(
        "import Lake\nopen Lake DSL\npackage «demo» where\nlean_lib «AlgebraicCombinatorics» where\n  globs := #[.submodules `AlgebraicCombinatorics]\n",
        encoding="utf-8",
    )
    dep.write_text("import Mathlib\nnamespace AlgebraicCombinatorics\ndef dep : True := True.intro\nend AlgebraicCombinatorics\n", encoding="utf-8")
    target.write_text(
        "import Mathlib\nimport AlgebraicCombinatorics.Dep\nnamespace AlgebraicCombinatorics\ntheorem target : True := dep\nend AlgebraicCombinatorics\n",
        encoding="utf-8",
    )
    record = SelectedRecord(
        {
            "id": "AlgebraicCombinatorics/Target.lean:AlgebraicCombinatorics.target",
            "output": {
                "lean_path": "AlgebraicCombinatorics/Target.lean",
                "declaration_names": ["AlgebraicCombinatorics.target"],
                "line_range": [4, 4],
                "chunk_kind": "theorem",
            },
            "minimal_context": {
                "imports": ["Mathlib", "AlgebraicCombinatorics.Dep"],
                "file_context": [
                    {
                        "path": "AlgebraicCombinatorics/Target.lean",
                        "kind": "namespace",
                        "name": "AlgebraicCombinatorics",
                        "line_range": [3, 3],
                    },
                ],
                "lean_predecessors": [],
                "source_spans": [{"path": "source.tex", "line_range": [1, 1]}],
            },
        }
    )
    (project_root / "source.tex").write_text("true\n", encoding="utf-8")

    target_path = materialize_candidate_project(
        project_root=project_root,
        output_root=tmp_path / "out",
        record=record,
        lean_declaration="theorem generated : True := dep",
        generated_name="generated",
        lake_cache_from=None,
        include_record_imports=True,
    )

    text = target_path.read_text(encoding="utf-8")
    assert "import AlgebraicCombinatorics.Dep" in text
    assert "theorem target : True := dep" not in text
    assert (tmp_path / "out" / "AlgebraicCombinatorics" / "Dep.lean").exists()


def test_materialize_candidate_project_can_omit_grader_for_repair_prompts(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)

    target_path = materialize_candidate_project(
        project_root=project_root,
        output_root=tmp_path / "out",
        record=record,
        lean_declaration="theorem generated : True := by\n  trivial",
        generated_name="generated",
        lake_cache_from=None,
        include_grader=False,
    )

    text = target_path.read_text(encoding="utf-8")
    assert "theorem generated : True := by" in text
    assert "__repoprover_source_statement_check" not in text
    assert "theorem target" not in text


def test_materialize_candidate_project_can_reuse_existing_output_root(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    output_root = tmp_path / "out"
    output_root.mkdir()
    sentinel = output_root / "sentinel.txt"
    sentinel.write_text("keep me\n", encoding="utf-8")

    materialize_candidate_project(
        project_root=project_root,
        output_root=output_root,
        record=record,
        lean_declaration="theorem generated : True := by\n  trivial",
        generated_name="generated",
        lake_cache_from=None,
        include_grader=False,
        clean_output=False,
    )

    assert sentinel.exists()
    assert (output_root / "Demo.lean").exists()


def test_classify_lean_failure_separates_missing_mathlib_cache() -> None:
    output = "AlgebraicCombinatorics/CauchyBinet.lean:1:0: error: unknown module prefix 'Mathlib'\nNo directory 'Mathlib' or file 'Mathlib.olean'"

    assert classify_lean_failure(output) == "lean_environment_missing_mathlib_cache"


def _write_records(path: Path, row: dict, count: int) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for index in range(count):
            cloned = copy.deepcopy(row)
            cloned["id"] = f"Demo.lean:Demo.target{index}"
            cloned["output"]["declaration_names"] = [f"Demo.target{index}"]
            handle.write(json.dumps(cloned, ensure_ascii=False) + "\n")


def _run_args(project_root: Path, records: Path, output: Path, **overrides: object) -> argparse.Namespace:
    values = {
        "records": records,
        "project_root": project_root,
        "output": output,
        "limit": 4,
        "model": "test/model",
        "base_url": "https://example.invalid/api/v1",
        "max_tokens": 128,
        "temperature": 0.0,
        "reasoning_effort": None,
        "repair_attempts": 0,
        "repair_max_tokens": 128,
        "repair_reasoning_effort": None,
        "preflight_only": False,
        "generation_only": False,
        "reuse_project": False,
        "lake_cache_from": None,
        "include_record_imports": False,
        "lean_timeout": 1,
        "openrouter_timeout": 1.0,
        "max_actual_cost_usd": 2.0,
        "concurrency": 2,
        "sample_mode": "corpus-spread",
        "budget_only": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _fake_response(content: str, *, finish_reason: str = "stop", cost: float = 0.0001) -> dict:
    return {
        "model": "test/model",
        "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30, "cost": cost},
    }


def test_source_statement_live_eval_runs_records_concurrently_and_writes_partials(
    tmp_path: Path, monkeypatch
) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 4)

    active = 0
    max_active = 0
    lock = threading.Lock()

    def fake_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        body = json.dumps(
            {
                "lean_declaration": "theorem generated : True := by\n  trivial",
                "declaration_name": "generated",
                "used_context": [],
                "notes": [],
            }
        )
        return _fake_response(body)

    monkeypatch.setattr("scripts.run_source_statement_live_eval.call_openrouter", fake_call_openrouter)
    monkeypatch.setattr(
        "scripts.run_source_statement_live_eval.run_lean",
        lambda project_root, target_path, timeout: {"exit_code": 0, "output": ""},
    )

    summary = run(_run_args(project_root, records_path, tmp_path / "out"))

    assert max_active == 2
    assert summary["records_attempted"] == 4
    assert summary["paid_calls_made"] == 4
    assert summary["successes"] == 4
    assert summary["failure_classes"] == {}
    partial_jsonl = tmp_path / "out/eval/partial-results.jsonl"
    assert len(partial_jsonl.read_text(encoding="utf-8").splitlines()) == 4
    generated_path = tmp_path / "out/record-001/generated-lean-declaration.lean"
    assert generated_path.read_text(encoding="utf-8") == "theorem generated : True := by\n  trivial\n"
    parsed_json_path = tmp_path / "out/record-001/model-output.json"
    assert json.loads(parsed_json_path.read_text(encoding="utf-8"))["declaration_name"] == "generated"


def test_source_statement_live_eval_repairs_generated_only_compile_failure(
    tmp_path: Path, monkeypatch
) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 1)
    calls: list[dict] = []
    responses = [
        {
            "lean_declaration": "theorem bad : True := by\n  exact missingFact",
            "declaration_name": "bad",
            "used_context": [],
            "notes": [],
        },
        {
            "lean_declaration": "theorem repaired : True := by\n  trivial",
            "declaration_name": "repaired",
            "used_context": ["compiler error"],
            "notes": [],
        },
    ]

    def fake_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        calls.append(payload)
        return _fake_response(json.dumps(responses[len(calls) - 1]), cost=0.0002)

    def fake_run_lean(project_root: Path, target_path: Path, timeout: int) -> dict:
        text = target_path.read_text(encoding="utf-8")
        if "missingFact" in text:
            return {"exit_code": 1, "output": "unknown identifier 'missingFact'"}
        return {"exit_code": 0, "output": ""}

    monkeypatch.setattr("scripts.run_source_statement_live_eval.call_openrouter", fake_call_openrouter)
    monkeypatch.setattr("scripts.run_source_statement_live_eval.run_lean", fake_run_lean)

    summary = run(_run_args(project_root, records_path, tmp_path / "out", limit=1, repair_attempts=1))
    row = summary["results"][0]

    assert len(calls) == 2
    assert summary["paid_calls_made"] == 2
    assert summary["actual_cost_usd"] == 0.0004
    assert summary["successes"] == 1
    assert row["repair_attempts_used"] == 1
    assert row["final_declaration_source"] == "repair-attempt-001"
    assert (tmp_path / "out/record-001/generated-only-lean.json").exists()
    assert (tmp_path / "out/record-001/repair-attempt-001-openrouter-payload.json").exists()
    assert (tmp_path / "out/record-001/repair-attempt-001-lean-declaration.lean").read_text(encoding="utf-8") == (
        "theorem repaired : True := by\n  trivial\n"
    )


def test_source_statement_live_eval_does_not_repair_grader_failures(tmp_path: Path, monkeypatch) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 1)
    calls = 0

    def fake_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        nonlocal calls
        calls += 1
        body = json.dumps(
            {
                "lean_declaration": "theorem generated : True := by\n  trivial",
                "declaration_name": "generated",
                "used_context": [],
                "notes": [],
            }
        )
        return _fake_response(body)

    def fake_run_lean(project_root: Path, target_path: Path, timeout: int) -> dict:
        text = target_path.read_text(encoding="utf-8")
        if "__repoprover_source_statement_check" in text:
            return {"exit_code": 1, "output": "error: unsolved goals\n__repoprover_source_statement_check"}
        return {"exit_code": 0, "output": ""}

    monkeypatch.setattr("scripts.run_source_statement_live_eval.call_openrouter", fake_call_openrouter)
    monkeypatch.setattr("scripts.run_source_statement_live_eval.run_lean", fake_run_lean)

    summary = run(_run_args(project_root, records_path, tmp_path / "out", limit=1, repair_attempts=1))
    row = summary["results"][0]

    assert calls == 1
    assert summary["paid_calls_made"] == 1
    assert summary["successes"] == 0
    assert row["repair_attempts_used"] == 0
    assert row["repair_results"] == []
    assert summary["failure_classes"] == {"grader_gold_statement_not_proved": 1}


def test_source_statement_live_eval_preflight_makes_no_openrouter_call(tmp_path: Path, monkeypatch) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 2)

    def fail_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        raise AssertionError("preflight must not call OpenRouter")

    monkeypatch.setattr("scripts.run_source_statement_live_eval.call_openrouter", fail_call_openrouter)
    monkeypatch.setattr(
        "scripts.run_source_statement_live_eval.run_lean",
        lambda project_root, target_path, timeout: {"exit_code": 0, "output": ""},
    )

    summary = run(
        _run_args(
            project_root,
            records_path,
            tmp_path / "out",
            limit=2,
            preflight_only=True,
            reuse_project=True,
            concurrency=1,
        )
    )

    assert summary["records_attempted"] == 0
    assert summary["paid_calls_made"] == 0
    assert summary["successes"] == 0
    assert summary["preflight_successes"] == 2
    assert summary["preflight_success_rate"] == 1.0
    assert [row["status"] for row in summary["results"]] == ["preflight_only", "preflight_only"]
    assert all(row["success"] for row in summary["results"])
    assert (tmp_path / "out/shared-project/Demo.lean").exists()


def test_source_statement_live_eval_generation_only_skips_lean_check(tmp_path: Path, monkeypatch) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 2)

    def fake_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        body = json.dumps(
            {
                "lean_declaration": "theorem generated : True := by\n  trivial",
                "declaration_name": "generated",
                "used_context": [],
                "notes": [],
            }
        )
        return _fake_response(body, cost=0.0003)

    def fail_run_lean(project_root: Path, target_path: Path, timeout: int) -> dict:
        raise AssertionError("generation-only mode must not run Lean")

    monkeypatch.setattr("scripts.run_source_statement_live_eval.call_openrouter", fake_call_openrouter)
    monkeypatch.setattr("scripts.run_source_statement_live_eval.run_lean", fail_run_lean)

    summary = run(_run_args(project_root, records_path, tmp_path / "out", limit=2, generation_only=True))

    assert summary["paid_calls_made"] == 2
    assert summary["actual_cost_usd"] == 0.0006
    assert summary["generation_successes"] == 2
    assert summary["generation_success_rate"] == 1.0
    assert summary["successes"] == 0
    assert [row["status"] for row in summary["results"]] == ["generation_only", "generation_only"]
    assert (tmp_path / "out/record-001/openrouter-response.json").exists()
    assert (tmp_path / "out/record-001/generated-lean-declaration.lean").exists()
    assert not (tmp_path / "out/record-001/project").exists()


def test_source_statement_live_eval_reuse_project_requires_serial_execution(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 1)

    try:
        run(_run_args(project_root, records_path, tmp_path / "out", reuse_project=True, concurrency=2))
    except ValueError as exc:
        assert "--reuse-project requires --concurrency 1" in str(exc)
    else:
        raise AssertionError("expected --reuse-project to reject concurrent execution")


def test_source_statement_live_eval_persists_raw_assistant_content_before_json_parse(
    tmp_path: Path, monkeypatch
) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 1)
    raw_content = "not json, but this is the model text we paid for"

    monkeypatch.setattr(
        "scripts.run_source_statement_live_eval.call_openrouter",
        lambda payload, base_url, timeout: _fake_response(raw_content),
    )

    summary = run(_run_args(project_root, records_path, tmp_path / "out", limit=1))

    assert summary["failure_classes"] == {"invalid_model_json": 1}
    raw_path = tmp_path / "out/record-001/model-assistant-content.txt"
    assert raw_path.read_text(encoding="utf-8") == raw_content


def test_source_statement_live_eval_enforces_global_estimated_cost_cap(
    tmp_path: Path, monkeypatch
) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 2)

    def fail_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        raise AssertionError("cost-capped records must not call OpenRouter")

    monkeypatch.setattr("scripts.run_source_statement_live_eval.call_openrouter", fail_call_openrouter)

    summary = run(
        _run_args(
            project_root,
            records_path,
            tmp_path / "out",
            limit=2,
            max_tokens=32768,
            max_actual_cost_usd=0.00001,
        )
    )

    assert summary["records_attempted"] == 0
    assert summary["paid_calls_made"] == 0
    assert summary["failure_classes"] == {"skipped_cost_cap": 2}


def test_source_statement_live_eval_classifies_length_no_content(tmp_path: Path, monkeypatch) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 1)

    monkeypatch.setattr(
        "scripts.run_source_statement_live_eval.call_openrouter",
        lambda payload, base_url, timeout: _fake_response("", finish_reason="length"),
    )

    summary = run(_run_args(project_root, records_path, tmp_path / "out", limit=1))

    assert summary["records_attempted"] == 1
    assert summary["failure_classes"] == {"no_content_or_length": 1}


def test_source_statement_sample_mode_easy_prefers_smaller_records() -> None:
    rows = []
    for index, (source_end, output_end, predecessor_count) in enumerate([(20, 7, 2), (3, 5, 0), (8, 4, 1)]):
        rows.append(
            {
                "id": f"r{index}",
                "output": {
                    "lean_path": "Demo.lean",
                    "declaration_names": [f"Demo.t{index}"],
                    "line_range": [4, output_end],
                    "chunk_kind": "theorem",
                },
                "minimal_context": {
                    "source_spans": [{"path": "Demo.tex", "line_range": [1, source_end]}],
                    "lean_predecessors": [{"declaration": f"p{n}"} for n in range(predecessor_count)],
                },
            }
        )

    selected = select_source_statement_records(rows, limit=2, sample_mode="easy")

    assert [item.selected.record_id for item in selected] == ["r1", "r2"]
