#!/usr/bin/env python3
"""Statically estimate explicit Lean API usage in generated project code.

This is a source scan, not an elaborated Lean dependency extractor. Qualified
references that exactly match declarations are high precision. Long bare names
that uniquely match one scanned declaration are useful medium-precision signals.
Ambiguous bare names are counted as forms, not resolved declarations.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DECL_RE = re.compile(
    r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
    r"(?P<kind>theorem|lemma|def|abbrev|instance|class|structure|inductive|axiom|constant|opaque)"
    r"\s+(?P<name>[^\s:\{\(\[]+)"
)
NAMESPACE_RE = re.compile(r"^\s*namespace\s+(?P<name>[A-Za-z0-9_'. ]+)\s*$")
SECTION_RE = re.compile(r"^\s*(?:noncomputable\s+)?section(?:\s+(?P<name>[A-Za-z0-9_'.]+))?\s*$")
END_RE = re.compile(r"^\s*end(?:\s+(?P<name>[A-Za-z0-9_'.]+))?\s*$")
TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_'.])([A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*)"
    r"(?![A-Za-z0-9_'.])"
)

KEYWORDS = {
    "theorem",
    "lemma",
    "def",
    "abbrev",
    "instance",
    "class",
    "structure",
    "inductive",
    "axiom",
    "constant",
    "opaque",
    "by",
    "where",
    "match",
    "with",
    "if",
    "then",
    "else",
    "let",
    "in",
    "fun",
    "forall",
    "exists",
    "do",
    "have",
    "show",
    "from",
    "calc",
    "import",
    "namespace",
    "section",
    "end",
    "open",
    "variable",
    "variables",
    "universe",
    "universes",
    "noncomputable",
    "private",
    "protected",
    "unsafe",
    "partial",
    "mutual",
    "deriving",
    "macro",
    "syntax",
    "notation",
    "scoped",
    "attribute",
    "simp",
    "simpa",
    "rw",
    "rwa",
    "erw",
    "exact",
    "apply",
    "refine",
    "intro",
    "intros",
    "constructor",
    "cases",
    "rcases",
    "induction",
    "subst",
    "rename_i",
    "simp_all",
    "aesop",
    "omega",
    "linarith",
    "nlinarith",
    "ring",
    "ring_nf",
    "norm_num",
    "rfl",
    "decide",
    "tauto",
    "contradiction",
    "assumption",
    "ext",
    "funext",
    "convert",
    "congr",
    "split",
    "left",
    "right",
    "use",
    "obtain",
    "specialize",
    "revert",
    "generalize",
    "change",
    "dsimp",
    "unfold",
    "repeat",
    "first",
    "all_goals",
    "any_goals",
    "try",
    "done",
    "skip",
    "next",
    "case",
    "conv",
    "at",
    "only",
    "using",
    "type",
    "Type",
    "Prop",
    "Sort",
    "True",
    "False",
}

COMMON_LOCAL_NAMES = {
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "N",
    "M",
    "R",
    "K",
    "L",
    "G",
    "H",
    "I",
    "J",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "P",
    "Q",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
    "hi",
    "hj",
    "hk",
    "hl",
    "hm",
    "hn",
    "hp",
    "hq",
    "hr",
    "hs",
    "ht",
    "hf",
    "hg",
    "ha",
    "hb",
    "hc",
    "hd",
    "he",
    "h1",
    "h2",
    "ih",
    "this",
}


def strip_comments_and_strings(text: str) -> str:
    output: list[str] = []
    block_depth = 0
    for line in text.splitlines():
        index = 0
        buffer: list[str] = []
        in_string = False
        escaped = False
        while index < len(line):
            if block_depth == 0 and not in_string and line.startswith("/-", index):
                block_depth += 1
                index += 2
                continue
            if block_depth > 0:
                if line.startswith("/-", index):
                    block_depth += 1
                    index += 2
                    continue
                if line.startswith("-/", index):
                    block_depth -= 1
                    index += 2
                    continue
                index += 1
                continue
            char = line[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                buffer.append(" ")
                index += 1
                continue
            if line.startswith("--", index):
                break
            if char == '"':
                in_string = True
                buffer.append(" ")
                index += 1
                continue
            buffer.append(char)
            index += 1
        output.append("".join(buffer))
    return "\n".join(output)


def parse_decl_names(files: list[Path]) -> dict[str, str]:
    names: dict[str, str] = {}
    for path in files:
        namespace_stack: list[str] = []
        scope_stack: list[tuple[str, list[str]]] = []
        for line in strip_comments_and_strings(path.read_text(encoding="utf-8")).splitlines():
            if match := NAMESPACE_RE.match(line):
                parts = [part for part in match.group("name").strip().split() if part]
                namespace_stack.extend(parts)
                scope_stack.append(("namespace", parts))
                continue
            if SECTION_RE.match(line):
                scope_stack.append(("section", []))
                continue
            if END_RE.match(line):
                if scope_stack:
                    kind, parts = scope_stack.pop()
                    if kind == "namespace":
                        for _ in parts:
                            if namespace_stack:
                                namespace_stack.pop()
                continue
            if match := DECL_RE.match(line):
                raw_name = match.group("name").strip("`")
                if not raw_name or raw_name.startswith(("[", "{", "(")):
                    continue
                if raw_name.startswith("«") and raw_name.endswith("»"):
                    raw_name = raw_name[1:-1]
                full_name = raw_name if "." in raw_name or not namespace_stack else ".".join(namespace_stack + [raw_name])
                names[full_name] = match.group("kind")
    return names


def percentile_summary(values: list[int]) -> dict[str, int]:
    ordered = sorted(values)
    if not ordered:
        return {"median": 0, "p90": 0, "p95": 0, "max": 0}
    return {
        "median": ordered[round((len(ordered) - 1) * 0.5)],
        "p90": ordered[round((len(ordered) - 1) * 0.9)],
        "p95": ordered[round((len(ordered) - 1) * 0.95)],
        "max": ordered[-1],
    }


def load_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_simple_index(names: set[str]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for full_name in names:
        index[full_name.split(".")[-1]].add(full_name)
    return index


def classify_text(
    text: str,
    *,
    self_names: set[str],
    mathlib_full: set[str],
    mathlib_simple: dict[str, set[str]],
    project_full: set[str],
    project_simple: dict[str, set[str]],
) -> dict[str, set[str]]:
    self_simple = {name.split(".")[-1] for name in self_names}
    output = {
        "mathlib_qualified_exact": set(),
        "mathlib_long_unique_bare": set(),
        "mathlib_ambiguous_long_bare_forms": set(),
        "project_qualified_exact": set(),
        "project_long_unique_bare": set(),
        "project_ambiguous_long_bare_forms": set(),
    }
    for token in TOKEN_RE.findall(strip_comments_and_strings(text)):
        if token in KEYWORDS or token in self_names or token.split(".")[-1] in self_simple:
            continue
        if token in mathlib_full:
            output["mathlib_qualified_exact"].add(token)
            continue
        if token in project_full:
            output["project_qualified_exact"].add(token)
            continue
        if "." in token:
            parts = token.split(".")
            matched = False
            for index in range(1, len(parts)):
                suffix = ".".join(parts[index:])
                if suffix in mathlib_full:
                    output["mathlib_qualified_exact"].add(suffix)
                    matched = True
                    break
                if suffix in project_full:
                    output["project_qualified_exact"].add(suffix)
                    matched = True
                    break
            if matched:
                continue
            simple = parts[-1]
        else:
            simple = token
        if simple in COMMON_LOCAL_NAMES or len(simple) < 4:
            continue
        if simple in project_simple:
            project_matches = project_simple[simple] - self_names
            if len(project_matches) == 1:
                output["project_long_unique_bare"].update(project_matches)
            elif len(project_matches) > 1:
                output["project_ambiguous_long_bare_forms"].add(simple)
        if simple in mathlib_simple:
            mathlib_matches = mathlib_simple[simple]
            if len(mathlib_matches) == 1:
                output["mathlib_long_unique_bare"].update(mathlib_matches)
            elif len(mathlib_matches) > 1:
                output["mathlib_ambiguous_long_bare_forms"].add(simple)
    return output


def union(rows: list[tuple[dict[str, Any], dict[str, set[str]]]], key: str) -> set[str]:
    values: set[str] = set()
    for _, classified in rows:
        values.update(classified[key])
    return values


def merged_count(rows: list[tuple[dict[str, Any], dict[str, set[str]]]], keys: list[str]) -> int:
    values: set[str] = set()
    for _, classified in rows:
        for key in keys:
            values.update(classified[key])
    return len(values)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path("algebraic-combinatorics"))
    parser.add_argument("--records", type=Path, default=Path("docs/minimal-context-full-records.jsonl"))
    parser.add_argument("--mathlib-root", type=Path, default=None)
    parser.add_argument("--max-top", type=int, default=25)
    args = parser.parse_args()

    project_root = args.project_root
    mathlib_root = args.mathlib_root or project_root / ".lake/packages/mathlib/Mathlib"
    mathlib_names = parse_decl_names(sorted(mathlib_root.rglob("*.lean")))
    mathlib_full = set(mathlib_names)
    mathlib_simple = build_simple_index(mathlib_full)

    records = load_records(args.records)
    project_full = {
        name
        for record in records
        for name in record.get("output", {}).get("declaration_names") or []
    }
    project_simple = build_simple_index(project_full)

    file_lines: dict[str, list[str]] = {}

    def record_text(record: dict[str, Any]) -> str:
        path = record["output"]["lean_path"]
        if path not in file_lines:
            file_lines[path] = (project_root / path).read_text(encoding="utf-8").splitlines()
        start, end = record["output"]["line_range"]
        return "\n".join(file_lines[path][start - 1 : end])

    classified_rows: list[tuple[dict[str, Any], dict[str, set[str]]]] = []
    for record in records:
        classified_rows.append(
            (
                record,
                classify_text(
                    record_text(record),
                    self_names=set(record.get("output", {}).get("declaration_names") or []),
                    mathlib_full=mathlib_full,
                    mathlib_simple=mathlib_simple,
                    project_full=project_full,
                    project_simple=project_simple,
                ),
            )
        )

    theorem_rows = [
        row for row in classified_rows if row[0].get("output", {}).get("chunk_kind") in {"theorem", "lemma"}
    ]
    labels: dict[str, list[tuple[dict[str, Any], dict[str, set[str]]]]] = defaultdict(list)
    for record, classified in classified_rows:
        if record.get("alignment", {}).get("source_method") != "lean_comment_label":
            continue
        for label in record.get("alignment", {}).get("comment_labels") or []:
            labels[label].append((record, classified))
    label_items = list(labels.items())

    def series(rows: list[tuple[dict[str, Any], dict[str, set[str]]]], key: str) -> list[int]:
        return [len(classified[key]) for _, classified in rows]

    def high_medium_math_count(rows: list[tuple[dict[str, Any], dict[str, set[str]]]]) -> list[int]:
        return [
            len(classified["mathlib_qualified_exact"] | classified["mathlib_long_unique_bare"])
            for _, classified in rows
        ]

    def high_medium_project_count(rows: list[tuple[dict[str, Any], dict[str, set[str]]]]) -> list[int]:
        return [
            len(classified["project_qualified_exact"] | classified["project_long_unique_bare"])
            for _, classified in rows
        ]

    result = {
        "mathlib_names_scanned": len(mathlib_full),
        "project_declarations": len(project_full),
        "records_scanned": len(records),
        "caveat": (
            "Static source scan after stripping comments/strings. Qualified exact names are high precision. "
            "Long unique bare names are medium precision after filtering common locals and names shorter than 4. "
            "This still misses notation, elaboration, typeclass search, simp internals, tactic-generated "
            "dependencies, and ambiguous bare references."
        ),
        "global_unique": {
            "mathlib_qualified_exact": len(union(classified_rows, "mathlib_qualified_exact")),
            "mathlib_qualified_plus_long_unique_bare": len(
                union(classified_rows, "mathlib_qualified_exact")
                | union(classified_rows, "mathlib_long_unique_bare")
            ),
            "mathlib_long_unique_bare_only": len(union(classified_rows, "mathlib_long_unique_bare")),
            "mathlib_ambiguous_long_bare_forms": len(
                union(classified_rows, "mathlib_ambiguous_long_bare_forms")
            ),
            "project_qualified_exact": len(union(classified_rows, "project_qualified_exact")),
            "project_qualified_plus_long_unique_bare": len(
                union(classified_rows, "project_qualified_exact")
                | union(classified_rows, "project_long_unique_bare")
            ),
        },
        "per_declaration_all": {
            "mathlib_qualified_exact": percentile_summary(series(classified_rows, "mathlib_qualified_exact")),
            "mathlib_qualified_plus_long_unique_bare": percentile_summary(
                high_medium_math_count(classified_rows)
            ),
            "project_qualified_exact": percentile_summary(series(classified_rows, "project_qualified_exact")),
            "project_qualified_plus_long_unique_bare": percentile_summary(
                high_medium_project_count(classified_rows)
            ),
            "ambiguous_long_bare_mathlib_forms": percentile_summary(
                series(classified_rows, "mathlib_ambiguous_long_bare_forms")
            ),
        },
        "per_declaration_theorem_lemma_only": {
            "records": len(theorem_rows),
            "mathlib_qualified_exact": percentile_summary(series(theorem_rows, "mathlib_qualified_exact")),
            "mathlib_qualified_plus_long_unique_bare": percentile_summary(high_medium_math_count(theorem_rows)),
            "project_qualified_exact": percentile_summary(series(theorem_rows, "project_qualified_exact")),
            "project_qualified_plus_long_unique_bare": percentile_summary(high_medium_project_count(theorem_rows)),
        },
        "per_exact_tex_label": {
            "labels": len(label_items),
            "decls_per_label": percentile_summary([len(rows) for _, rows in label_items]),
            "mathlib_qualified_exact": percentile_summary(
                [merged_count(rows, ["mathlib_qualified_exact"]) for _, rows in label_items]
            ),
            "mathlib_qualified_plus_long_unique_bare": percentile_summary(
                [
                    merged_count(rows, ["mathlib_qualified_exact", "mathlib_long_unique_bare"])
                    for _, rows in label_items
                ]
            ),
            "project_qualified_exact": percentile_summary(
                [merged_count(rows, ["project_qualified_exact"]) for _, rows in label_items]
            ),
            "project_qualified_plus_long_unique_bare": percentile_summary(
                [
                    merged_count(rows, ["project_qualified_exact", "project_long_unique_bare"])
                    for _, rows in label_items
                ]
            ),
            "ambiguous_long_bare_mathlib_forms": percentile_summary(
                [merged_count(rows, ["mathlib_ambiguous_long_bare_forms"]) for _, rows in label_items]
            ),
        },
        "top_mathlib_qualified_namespaces": Counter(
            ref.split(".")[0] if "." in ref else "(root)"
            for ref in union(classified_rows, "mathlib_qualified_exact")
        ).most_common(args.max_top),
        "top_mathlib_qualified_refs_by_declaration_occurrence": Counter(
            ref for _, classified in classified_rows for ref in classified["mathlib_qualified_exact"]
        ).most_common(args.max_top),
        "top_project_qualified_refs_by_declaration_occurrence": Counter(
            ref for _, classified in classified_rows for ref in classified["project_qualified_exact"]
        ).most_common(args.max_top),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
