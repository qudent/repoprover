"""Tests for theorem-level Mathlib context hydration."""

from scripts.hydrate_latex_statement_context import (
    build_check_source,
    checked_parent_identifier,
    fallback_mathlib_candidates,
    find_mathlib_declarations,
    hydrate_output,
    iter_mathlib_requests,
    related_names_for_declaration,
    split_exact_identifier_list,
    structure_field_names,
)


def _selector_output() -> dict:
    return {
        "units": [
            {
                "unit_key": "unit-001",
                "planned_declarations": [
                    {
                        "task_id": "unit-001-task-1",
                        "source_part": "whole unit",
                        "needed_mathlib_context": [
                            {
                                "name_or_query": "Nat.add_comm",
                                "expected_signature_or_shape": "a + b = b + a",
                                "why_needed": "commute addition",
                            },
                            {
                                "name_or_query": "PowerSeries coefficient theorem",
                                "expected_signature_or_shape": "coeff n f",
                                "why_needed": "narrow search fallback",
                            },
                        ],
                    }
                ],
            }
        ]
    }


def test_iter_mathlib_requests_extracts_exact_and_query_items() -> None:
    requests = iter_mathlib_requests(_selector_output())

    assert [request.query for request in requests] == ["Nat.add_comm", "PowerSeries coefficient theorem"]
    assert requests[0].exact_identifier == "Nat.add_comm"
    assert requests[1].exact_identifier is None
    assert requests[0].expected_signature_or_shape == "a + b = b + a"


def test_build_check_source_maps_check_lines() -> None:
    source, line_to_name = build_check_source(
        ["Nat.add_comm", "IsUnit"],
        imports=["Mathlib"],
        opens=["open PowerSeries"],
    )

    assert "#check Nat.add_comm" in source
    assert line_to_name == {3: "Nat.add_comm", 4: "IsUnit"}


def test_split_exact_identifier_list() -> None:
    assert split_exact_identifier_list("mul_assoc, one_mul, mul_one") == [
        "mul_assoc",
        "one_mul",
        "mul_one",
    ]
    assert split_exact_identifier_list("PowerSeries coefficient theorem") == []


def test_hydrate_output_marks_non_exact_queries(monkeypatch, tmp_path) -> None:
    def fake_check_names(names, *, project_root, imports, opens, timeout_seconds):
        return {
            "status": "ok",
            "checked": {
                "Nat.add_comm": {
                    "status": "checked",
                    "signature": "Nat.add_comm (n m : Nat) : n + m = m + n",
                }
            },
        }

    monkeypatch.setattr("scripts.hydrate_latex_statement_context.lean_check_names", fake_check_names)

    hydrated = hydrate_output(
        _selector_output(),
        project_root=tmp_path,
        imports=["Mathlib"],
        opens=[],
        timeout_seconds=1,
    )

    assert hydrated["request_count"] == 2
    assert hydrated["exact_identifier_count"] == 1
    assert hydrated["hydrated_mathlib_context"][0]["lean_check"]["status"] == "checked"
    assert hydrated["hydrated_mathlib_context"][1]["lean_check"]["status"] == "not_exact_identifier"


def test_hydrate_output_lean_checks_fallback_candidates(monkeypatch, tmp_path) -> None:
    def fake_check_names(names, *, project_root, imports, opens, timeout_seconds):
        checked = {}
        for name in names:
            if name == "Finset.powersetCard_eq_empty":
                checked[name] = {
                    "status": "checked",
                    "signature": "Finset.powersetCard_eq_empty : powersetCard n s = ∅ ↔ s.card < n",
                }
            else:
                checked[name] = {"status": "error", "error": f"Unknown constant `{name}`"}
        return {"status": "ok", "checked": checked}

    def fake_fallback(
        query,
        *,
        project_root,
        limit=8,
        expected_signature_or_shape="",
        diagnostic_text="",
    ):
        return [
            {
                "name": "Finset.powersetCard_eq_empty",
                "kind": "lemma",
                "path": "Mathlib/Data/Finset/Powerset.lean",
                "line_number": 222,
                "declaration_line": "lemma powersetCard_eq_empty : powersetCard n s = ∅ ↔ s.card < n := by",
                "matched_tokens": ["powersetCard"],
                "score": 10,
            }
        ]

    monkeypatch.setattr("scripts.hydrate_latex_statement_context.lean_check_names", fake_check_names)
    monkeypatch.setattr("scripts.hydrate_latex_statement_context.fallback_mathlib_candidates", fake_fallback)

    hydrated = hydrate_output(
        {
            "units": [
                {
                    "unit_key": "unit-001",
                    "planned_declarations": [
                        {
                            "task_id": "unit-001-task-1",
                            "source_part": "repair",
                            "needed_mathlib_context": [
                                {"name_or_query": "Finset.powersetCard_eq_empty_of_lt"}
                            ],
                        }
                    ],
                }
            ]
        },
        project_root=tmp_path,
        imports=["Mathlib"],
        opens=[],
        timeout_seconds=1,
    )

    fallback = hydrated["hydrated_mathlib_context"][0]["fallback_mathlib_candidates"][0]
    assert fallback["name"] == "Finset.powersetCard_eq_empty"
    assert fallback["lean_check"]["status"] == "checked"
    assert hydrated["fallback_exact_identifier_count"] == 1


def test_find_mathlib_declarations_extracts_structure_source(tmp_path) -> None:
    mathlib_file = tmp_path / ".lake/packages/mathlib/Mathlib/Demo/Partition.lean"
    mathlib_file.parent.mkdir(parents=True)
    mathlib_file.write_text(
        "\n".join(
            [
                "namespace Nat",
                "/-- A partition of n. -/",
                "@[ext]",
                "structure Partition (n : ℕ) where",
                "  /-- positive parts -/",
                "  parts : Multiset ℕ",
                "  parts_sum : parts.sum = n",
                "deriving DecidableEq",
                "",
                "namespace Partition",
                "theorem ext {n : ℕ} {x y : Partition n} (h : x.parts = y.parts) : x = y := by",
                "  cases x; cases y; simp_all",
                "end Partition",
                "end Nat",
            ]
        ),
        encoding="utf-8",
    )

    found = find_mathlib_declarations(["Nat.Partition"], project_root=tmp_path)

    declaration = found["Nat.Partition"]
    assert declaration["kind"] == "structure"
    assert declaration["path"] == ".lake/packages/mathlib/Mathlib/Demo/Partition.lean"
    assert "structure Partition" in declaration["source_snippet"]
    assert structure_field_names(declaration["source_snippet"]) == ["parts", "parts_sum"]
    assert related_names_for_declaration("Nat.Partition", declaration) == [
        "Nat.Partition.parts",
        "Nat.Partition.parts_sum",
        "Nat.Partition.ext",
        "Nat.Partition.ext_iff",
    ]


def test_hydrate_output_adds_checked_structure_neighborhood(monkeypatch, tmp_path) -> None:
    def fake_check_names(names, *, project_root, imports, opens, timeout_seconds):
        checked = {}
        for name in names:
            checked[name] = {
                "status": "checked",
                "signature": f"{name} : checked",
            }
        return {"status": "ok", "checked": checked}

    def fake_find_declarations(names, *, project_root):
        assert names == ["Nat.Partition"]
        return {
            "Nat.Partition": {
                "name": "Nat.Partition",
                "kind": "structure",
                "path": "Mathlib/Combinatorics/Enumerative/Partition/Basic.lean",
                "line_number": 57,
                "declaration_line": "structure Partition (n : ℕ) where",
                "source_snippet": "\n".join(
                    [
                        "structure Partition (n : ℕ) where",
                        "  parts : Multiset ℕ",
                        "  parts_pos : ∀ {i}, i ∈ parts → 0 < i",
                        "  parts_sum : parts.sum = n",
                    ]
                ),
                "source_snippet_truncated": False,
            }
        }

    monkeypatch.setattr("scripts.hydrate_latex_statement_context.lean_check_names", fake_check_names)
    monkeypatch.setattr("scripts.hydrate_latex_statement_context.find_mathlib_declarations", fake_find_declarations)

    hydrated = hydrate_output(
        {
            "units": [
                {
                    "unit_key": "unit-001",
                    "planned_declarations": [
                        {
                            "task_id": "unit-001-task-1",
                            "source_part": "whole unit",
                            "needed_mathlib_context": [{"name_or_query": "Nat.Partition"}],
                        }
                    ],
                }
            ]
        },
        project_root=tmp_path,
        imports=["Mathlib"],
        opens=[],
        timeout_seconds=1,
    )

    row = hydrated["hydrated_mathlib_context"][0]
    assert row["source_declaration"]["kind"] == "structure"
    related = row["related_mathlib_declarations"]
    assert [item["name"] for item in related] == [
        "Nat.Partition.parts",
        "Nat.Partition.parts_pos",
        "Nat.Partition.parts_sum",
        "Nat.Partition.ext",
        "Nat.Partition.ext_iff",
    ]
    assert all(item["lean_check"]["status"] == "checked" for item in related)
    assert hydrated["related_exact_identifier_count"] == 5


def test_checked_parent_identifier_uses_longest_checked_prefix() -> None:
    assert (
        checked_parent_identifier("Nat.Partition.length", {"Nat", "Nat.Partition"})
        == "Nat.Partition"
    )
    assert checked_parent_identifier("Nat.Partition.length", {"Nat.Partition.parts"}) is None


def test_hydrate_output_suppresses_unrelated_fallbacks_for_checked_parent(monkeypatch, tmp_path) -> None:
    def fake_check_names(names, *, project_root, imports, opens, timeout_seconds):
        checked = {}
        for name in names:
            if name == "Nat.Partition.length":
                checked[name] = {"status": "error", "error": "Unknown constant"}
            else:
                checked[name] = {"status": "checked", "signature": f"{name} : checked"}
        return {"status": "ok", "checked": checked}

    def fake_fallback(
        query,
        *,
        project_root,
        limit=8,
        expected_signature_or_shape="",
        diagnostic_text="",
    ):
        return [
            {
                "name": "Nat.toDigits_length",
                "kind": "lemma",
                "path": "Mathlib/Data/Nat/Digits.lean",
                "line_number": 1,
                "declaration_line": "lemma toDigits_length : True := by trivial",
                "matched_tokens": ["length"],
                "score": 1,
            }
        ]

    def fake_find_declarations(names, *, project_root):
        return {
            "Nat.Partition": {
                "name": "Nat.Partition",
                "kind": "structure",
                "source_snippet": "structure Partition (n : ℕ) where\n  parts : Multiset ℕ",
            }
        }

    monkeypatch.setattr("scripts.hydrate_latex_statement_context.lean_check_names", fake_check_names)
    monkeypatch.setattr("scripts.hydrate_latex_statement_context.fallback_mathlib_candidates", fake_fallback)
    monkeypatch.setattr("scripts.hydrate_latex_statement_context.find_mathlib_declarations", fake_find_declarations)

    hydrated = hydrate_output(
        {
            "units": [
                {
                    "unit_key": "unit-001",
                    "planned_declarations": [
                        {
                            "task_id": "unit-001-task-1",
                            "source_part": "whole unit",
                            "needed_mathlib_context": [
                                {"name_or_query": "Nat.Partition"},
                                {"name_or_query": "Nat.Partition.length"},
                            ],
                        }
                    ],
                }
            ]
        },
        project_root=tmp_path,
        imports=["Mathlib"],
        opens=[],
        timeout_seconds=1,
    )

    failed = hydrated["hydrated_mathlib_context"][1]
    assert failed["query"] == "Nat.Partition.length"
    assert failed["fallback_mathlib_candidates"] == []
    assert failed["fallback_suppression"] == {
        "checked_parent": "Nat.Partition",
        "policy": "failed_member_request_scoped_to_checked_parent",
        "removed_candidate_count": 1,
    }


def test_fallback_mathlib_candidates_scores_local_mathlib_declarations(tmp_path) -> None:
    mathlib_file = tmp_path / ".lake/packages/mathlib/Mathlib/Demo/Symmetric.lean"
    mathlib_file.parent.mkdir(parents=True)
    mathlib_file.write_text(
        "\n".join(
            [
                "namespace MvPolynomial",
                "section CommSemiring",
                "end CommSemiring",
                "theorem esymm_eq_sum_subtype (n : Nat) : True := by trivial",
                "theorem unrelated : True := by trivial",
                "end MvPolynomial",
            ]
        ),
        encoding="utf-8",
    )

    candidates = fallback_mathlib_candidates("MvPolynomial.esymm_eq_zero_of_lt", project_root=tmp_path)

    assert candidates[0]["name"] == "MvPolynomial.esymm_eq_sum_subtype"
    assert "esymm" in candidates[0]["matched_tokens"]


def test_fallback_mathlib_candidates_keep_qualified_namespace_root(tmp_path) -> None:
    mathlib_file = tmp_path / ".lake/packages/mathlib/Mathlib/Demo/Vandermonde.lean"
    mathlib_file.parent.mkdir(parents=True)
    mathlib_file.write_text(
        "\n".join(
            [
                "namespace Matrix",
                "theorem vandermonde : True := by trivial",
                "end Matrix",
                "namespace Nat",
                "theorem choose_mul_succ_eq (n k : Nat) : True := by trivial",
                "end Nat",
            ]
        ),
        encoding="utf-8",
    )

    candidates = fallback_mathlib_candidates("Nat.vandermonde", project_root=tmp_path)

    assert all(candidate["name"].startswith("Nat.") for candidate in candidates)
    assert "Matrix.vandermonde" not in {candidate["name"] for candidate in candidates}


def test_fallback_mathlib_candidates_prefer_local_name_tokens(tmp_path) -> None:
    mathlib_file = tmp_path / ".lake/packages/mathlib/Mathlib/Demo/Choose.lean"
    mathlib_file.parent.mkdir(parents=True)
    mathlib_file.write_text(
        "\n".join(
            [
                "namespace Nat",
                "theorem sqrt_mul_sqrt_lt_succ (n : Nat) : True := by trivial",
                "theorem choose_mul_succ_eq (n k : Nat) : True := by trivial",
                "end Nat",
            ]
        ),
        encoding="utf-8",
    )

    candidates = fallback_mathlib_candidates("Nat.choose_sq_ge_choose_mul_choose_succ", project_root=tmp_path)

    assert [candidate["name"] for candidate in candidates] == ["Nat.choose_mul_succ_eq"]


def test_fallback_mathlib_candidates_prefer_name_matches_over_type_sort_mentions(tmp_path) -> None:
    mathlib_file = tmp_path / ".lake/packages/mathlib/Mathlib/Demo/MultisetSort.lean"
    mathlib_file.parent.mkdir(parents=True)
    mathlib_file.write_text(
        "\n".join(
            [
                "namespace Multiset",
                "theorem strongInductionOn_eq {p : Multiset α → Sort u} (s : Multiset α) : True := by trivial",
                "theorem sort_eq (s : Multiset α) : True := by trivial",
                "def sort (s : Multiset α) : List α := []",
                "end Multiset",
            ]
        ),
        encoding="utf-8",
    )

    candidates = fallback_mathlib_candidates("Multiset.sort_eq_sort", project_root=tmp_path)

    assert [candidate["name"] for candidate in candidates] == ["Multiset.sort_eq", "Multiset.sort"]


def test_fallback_mathlib_candidates_uses_signature_shape_and_aliases(tmp_path) -> None:
    mathlib_file = tmp_path / ".lake/packages/mathlib/Mathlib/Demo/ListPairwise.lean"
    mathlib_file.parent.mkdir(parents=True)
    mathlib_file.write_text(
        "\n".join(
            [
                "namespace List",
                "theorem rel_of_sorted_cons (h : l.Pairwise R) : True := by trivial",
                "theorem Pairwise.rel_get_of_le (h : l.Pairwise R) {a b : Fin l.length} (hab : a ≤ b) : True := by trivial",
                "alias Sorted.rel_get_of_le := Pairwise.rel_get_of_le",
                "end List",
            ]
        ),
        encoding="utf-8",
    )

    candidates = fallback_mathlib_candidates(
        "List.Sorted.rel_of_lt",
        project_root=tmp_path,
        expected_signature_or_shape="List.Sorted r l -> i ≤ j -> r (l.get i) (l.get j)",
        diagnostic_text="`List.Sorted` has been deprecated: Use `List.Pairwise` instead",
    )

    names = [candidate["name"] for candidate in candidates]
    assert "List.Pairwise.rel_get_of_le" in names
    assert "List.Sorted.rel_get_of_le" in names


def test_fallback_mathlib_candidates_bridges_multiset_sum_sort_shape(tmp_path) -> None:
    mathlib_file = tmp_path / ".lake/packages/mathlib/Mathlib/Demo/MultisetSort.lean"
    mathlib_file.parent.mkdir(parents=True)
    mathlib_file.write_text(
        "\n".join(
            [
                "namespace Multiset",
                "def sort (s : Multiset α) : List α := []",
                "lemma sum_map_div (s : Multiset α) : True := by trivial",
                "theorem sort_eq (s : Multiset α) : True := by trivial",
                "end Multiset",
            ]
        ),
        encoding="utf-8",
    )

    candidates = fallback_mathlib_candidates(
        "Multiset.sum_sort",
        project_root=tmp_path,
        expected_signature_or_shape="(Multiset.sort r s).sum = s.sum",
    )

    names = [candidate["name"] for candidate in candidates[:2]]
    assert names == ["Multiset.sort_eq", "Multiset.sum_coe"]


def test_fallback_mathlib_candidates_bridges_sorted_antitone_shape(tmp_path) -> None:
    mathlib_file = tmp_path / ".lake/packages/mathlib/Mathlib/Demo/ListPairwise.lean"
    mathlib_file.parent.mkdir(parents=True)
    mathlib_file.write_text(
        "\n".join(
            [
                "namespace List",
                "theorem sortedGE_iff_antitone_get : True := by trivial",
                "theorem Pairwise.rel_get_of_le : True := by trivial",
                "theorem Pairwise.rel_get_of_lt : True := by trivial",
                "end List",
            ]
        ),
        encoding="utf-8",
    )

    candidates = fallback_mathlib_candidates(
        "List.sum_of_sorted_antitone",
        project_root=tmp_path,
        expected_signature_or_shape="If a list is sorted by (· ≥ ·), then the function i ↦ list.get i is antitone on Fin (list.length).",
    )

    names = [candidate["name"] for candidate in candidates[:3]]
    assert names == [
        "List.Pairwise.rel_get_of_le",
        "List.Pairwise.rel_get_of_lt",
        "List.sortedGE_iff_antitone_get",
    ]


def test_fallback_mathlib_candidates_bridges_multiset_filter_card_le_shape(tmp_path) -> None:
    mathlib_file = tmp_path / ".lake/packages/mathlib/Mathlib/Demo/MultisetCard.lean"
    mathlib_file.parent.mkdir(parents=True)
    mathlib_file.write_text(
        "\n".join(
            [
                "namespace Multiset",
                "theorem card_filter_le_iff : True := by trivial",
                "theorem filter_le : True := by trivial",
                "theorem card_le_card : True := by trivial",
                "end Multiset",
            ]
        ),
        encoding="utf-8",
    )

    candidates = fallback_mathlib_candidates(
        "Multiset.card_filter_le",
        project_root=tmp_path,
        expected_signature_or_shape="(Multiset.filter p s).card ≤ s.card",
    )

    names = [candidate["name"] for candidate in candidates[:2]]
    assert names == ["Multiset.filter_le", "Multiset.card_le_card"]
