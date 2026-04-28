#!/usr/bin/env python3
"""Generate a whole-corpus context graph and minimal-context collection.

This is the deterministic, reproducible counterpart to
``generate_minimal_context_records.py``. It does not call an LLM. It parses the
vendored Algebraic Combinatorics TeX/Lean tree, builds source/declaration/import
nodes, and emits:

* a graph JSON file with nodes, edges, and unresolved alignment notes;
* a JSONL collection with one candidate minimal-context record per named Lean
  declaration.

The output is intentionally conservative: exact TeX label/comment matches get
higher trust; position-based fallbacks are complete but low-trust.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GENERATOR_VERSION = "whole-corpus-context-graph-v1"
AGGREGATE_TEX_FILENAMES = {"all.tex", "detnotes.tex"}
DECL_KINDS = "theorem|lemma|def|abbrev|instance|class|structure|inductive"
DECL_RE = re.compile(
    rf"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
    rf"(?P<kind>{DECL_KINDS})"
    rf"(?:\s+(?P<name>[^\s:\{{\(\[]+))?"
)
IMPORT_RE = re.compile(r"^\s*import\s+(?P<module>[A-Za-z0-9_'.]+)\s*$")
NAMESPACE_RE = re.compile(r"^\s*namespace\s+(?P<name>[A-Za-z0-9_'. ]+)\s*$")
SECTION_RE = re.compile(r"^\s*section(?:\s+[A-Za-z0-9_'.]+)?\s*$")
END_RE = re.compile(r"^\s*end(?:\s+(?P<name>[A-Za-z0-9_'.]+))?\s*$")
TEX_LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
COMMENT_LABEL_RE = re.compile(r"\\(?:label|ref)\{([^}]+)\}")
LABEL_TOKEN_RE = re.compile(
    r"\b(?:def|prop|thm|lem|cor|conv|exa|exe|sol|sec|subsec|eq|pf)"
    r"\.[A-Za-z0-9_.()=+\-/*]+"
)
LEAN_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")
TOP_LEVEL_LABEL_PREFIXES = {
    "def",
    "prop",
    "thm",
    "lem",
    "cor",
    "conv",
    "exa",
    "exe",
    "sol",
    "sec",
    "subsec",
}


@dataclass(frozen=True)
class TexLabel:
    label: str
    path: str
    line: int
    line_range: tuple[int, int]
    kind: str


@dataclass(frozen=True)
class LeanDecl:
    id: str
    kind: str
    name: str
    full_name: str
    path: str
    module: str
    declaration_line: int
    line_range: tuple[int, int]
    comment_labels: tuple[str, ...]
    imports: tuple[str, ...]


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def lean_module_from_path(path: str) -> str:
    return path.removesuffix(".lean").replace("/", ".")


def line_count(text: str) -> int:
    return max(1, len(text.splitlines()))


def numbered_range(start: int, end: int) -> list[int]:
    return [int(start), int(end)]


def stable_node_id(kind: str, value: str) -> str:
    return f"{kind}:{value}"


def extract_labels(text: str) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for label in [*COMMENT_LABEL_RE.findall(text), *LABEL_TOKEN_RE.findall(text)]:
        cleaned = clean_label_token(label)
        if cleaned and cleaned not in seen:
            labels.append(cleaned)
            seen.add(cleaned)
    return labels


def clean_label_token(label: str) -> str:
    cleaned = label.strip().rstrip(".,;:")
    while cleaned.endswith("**"):
        cleaned = cleaned[:-2].rstrip(".,;:")
    if cleaned.endswith(")") and "(" not in cleaned:
        cleaned = cleaned[:-1]
    return cleaned


def is_top_level_label(label: str) -> bool:
    return label.split(".", 1)[0] in TOP_LEVEL_LABEL_PREFIXES


def parse_tex_labels(project_root: Path) -> dict[str, TexLabel]:
    tex_root = project_root / "AlgebraicCombinatorics" / "tex"
    raw_by_path: dict[str, list[tuple[str, int]]] = {}
    for path in sorted(tex_root.rglob("*.tex")):
        if path.name in AGGREGATE_TEX_FILENAMES:
            continue
        rel = relpath(path, project_root)
        raw: list[tuple[str, int]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for label in TEX_LABEL_RE.findall(line):
                raw.append((label, line_number))
        raw_by_path[rel] = raw

    labels: dict[str, TexLabel] = {}
    for path, raw in raw_by_path.items():
        text_lines = (project_root / path).read_text(encoding="utf-8").splitlines()
        top_level = [(label, line) for label, line in raw if is_top_level_label(label)]
        for label, line in raw:
            next_top = next((candidate_line for _, candidate_line in top_level if candidate_line > line), None)
            end = (next_top - 1) if next_top else len(text_lines)
            kind = label.split(".", 1)[0]
            tex_label = TexLabel(
                label=label,
                path=path,
                line=line,
                line_range=(line, max(line, end)),
                kind=kind,
            )
            existing = labels.get(label)
            if existing is None or should_replace_tex_label(existing, tex_label):
                labels[label] = tex_label
    return labels


def should_replace_tex_label(existing: TexLabel, candidate: TexLabel) -> bool:
    """Prefer chapter-local TeX over aggregate files when labels duplicate."""

    existing_is_aggregate = Path(existing.path).name in AGGREGATE_TEX_FILENAMES
    candidate_is_aggregate = Path(candidate.path).name in AGGREGATE_TEX_FILENAMES
    if existing_is_aggregate != candidate_is_aggregate:
        return existing_is_aggregate and not candidate_is_aggregate
    return len(candidate.path) < len(existing.path)


def declaration_display_start(lines: list[str], declaration_index: int) -> int:
    start = declaration_index
    while start > 0 and lines[start - 1].strip().startswith("@["):
        start -= 1

    if start > 0 and lines[start - 1].strip().endswith("-/"):
        comment_start = start - 1
        while comment_start > 0 and not lines[comment_start].lstrip().startswith(("/--", "/-!")):
            comment_start -= 1
        if lines[comment_start].lstrip().startswith(("/--", "/-!")):
            start = comment_start
            while start > 0 and lines[start - 1].strip().startswith("@["):
                start -= 1
    return start + 1


def trim_declaration_end(lines: list[str], end_line: int) -> int:
    while end_line > 1:
        stripped = lines[end_line - 1].strip()
        if not stripped or stripped.startswith("end "):
            end_line -= 1
            continue
        break
    return end_line


def namespace_prefix(stack: list[str]) -> str:
    parts: list[str] = []
    for item in stack:
        parts.extend(part for part in item.split(".") if part)
    return ".".join(parts)


def parse_imports(text: str) -> list[str]:
    return [match.group("module") for line in text.splitlines() if (match := IMPORT_RE.match(line))]


def parse_lean_declarations(project_root: Path, lean_path: Path) -> list[LeanDecl]:
    text = lean_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    path = relpath(lean_path, project_root)
    module = lean_module_from_path(path)
    imports = tuple(parse_imports(text))
    namespace_stack: list[str] = []
    section_depth = 0
    raw: list[dict[str, Any]] = []

    for index, line in enumerate(lines, start=1):
        if match := NAMESPACE_RE.match(line):
            namespace_stack.append(match.group("name").strip())
            continue
        if SECTION_RE.match(line):
            section_depth += 1
            continue
        if match := END_RE.match(line):
            name = match.group("name")
            if name and namespace_stack and namespace_stack[-1].split(".")[-1] == name.split(".")[-1]:
                namespace_stack.pop()
            elif not name and section_depth > 0:
                section_depth -= 1
            elif namespace_stack:
                namespace_stack.pop()
            continue

        match = DECL_RE.match(line)
        if not match:
            continue
        name = match.group("name")
        if not name or name == ":":
            continue
        if name.startswith("[") or name.startswith("{") or name.startswith("("):
            continue
        start_line = declaration_display_start(lines, index - 1)
        comment_text = "\n".join(lines[start_line - 1 : index])
        prefix = namespace_prefix(namespace_stack)
        full_name = f"{prefix}.{name}" if prefix else name
        raw.append(
            {
                "kind": match.group("kind"),
                "name": name,
                "full_name": full_name,
                "declaration_line": index,
                "start_line": start_line,
                "comment_labels": tuple(extract_labels(comment_text)),
            }
        )

    declarations: list[LeanDecl] = []
    for offset, decl in enumerate(raw):
        next_start = raw[offset + 1]["start_line"] if offset + 1 < len(raw) else len(lines) + 1
        end_line = trim_declaration_end(lines, next_start - 1)
        decl_id = stable_node_id("lean_decl", f"{path}:{decl['full_name']}")
        declarations.append(
            LeanDecl(
                id=decl_id,
                kind=decl["kind"],
                name=decl["name"],
                full_name=decl["full_name"],
                path=path,
                module=module,
                declaration_line=decl["declaration_line"],
                line_range=(decl["start_line"], end_line),
                comment_labels=decl["comment_labels"],
                imports=imports,
            )
        )
    return declarations


def read_manifest(project_root: Path) -> list[dict[str, Any]]:
    manifest_path = project_root / "manifest.json"
    if not manifest_path.exists():
        return []
    return list(json.loads(manifest_path.read_text(encoding="utf-8")).get("chapters", []))


def build_source_path_lookup(project_root: Path, chapters: list[dict[str, Any]]) -> dict[str, str]:
    by_stem: dict[str, str] = {}
    for chapter in chapters:
        source_path = chapter["source_path"]
        by_stem[Path(source_path).stem] = source_path

    explicit = {
        "AlgebraicCombinatorics/FPS/NotationsExamples.lean": "AlgebraicCombinatorics/tex/FPS/Notations.tex",
        "AlgebraicCombinatorics/FPSDefinition.lean": "AlgebraicCombinatorics/tex/FPS/FPSDefinition.tex",
        "AlgebraicCombinatorics/DividingFPS.lean": "AlgebraicCombinatorics/tex/FPS/DividingFPS.tex",
        "AlgebraicCombinatorics/QBinomialBasic.lean": "AlgebraicCombinatorics/tex/Partitions/QBinomialBasic.tex",
        "AlgebraicCombinatorics/PentagonalJacobi.lean": "AlgebraicCombinatorics/tex/Partitions/PentagonalJacobi.tex",
        "AlgebraicCombinatorics/DeterminantsBasic.lean": "AlgebraicCombinatorics/tex/Determinants/BasicProperties.tex",
        "AlgebraicCombinatorics/CauchyBinet.lean": "AlgebraicCombinatorics/tex/Determinants/CauchyBinet.tex",
        "AlgebraicCombinatorics/DesnanotJacobi.lean": "AlgebraicCombinatorics/tex/Determinants/DesnanotJacobi.tex",
        "AlgebraicCombinatorics/SignedCounting/BooleanMobiusInversion.lean": (
            "AlgebraicCombinatorics/tex/SignedCounting/InclusionExclusion2.tex"
        ),
    }

    lookup: dict[str, str] = dict(explicit)
    lean_root = project_root / "AlgebraicCombinatorics"
    for lean_path in sorted(lean_root.rglob("*.lean")):
        rel = relpath(lean_path, project_root)
        if rel in lookup:
            continue
        stem = lean_path.stem
        if stem in by_stem:
            lookup[rel] = by_stem[stem]
            continue
        relative_parts = Path(rel).parts
        if len(relative_parts) >= 3:
            candidate = Path("AlgebraicCombinatorics", "tex", *relative_parts[1:]).with_suffix(".tex").as_posix()
            if (project_root / candidate).exists():
                lookup[rel] = candidate
    return lookup


def chapter_for_source(chapters: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {chapter["source_path"]: chapter for chapter in chapters}


def module_path_index(declarations: list[LeanDecl]) -> dict[str, list[LeanDecl]]:
    by_module: dict[str, list[LeanDecl]] = defaultdict(list)
    for declaration in declarations:
        by_module[declaration.module].append(declaration)
    for rows in by_module.values():
        rows.sort(key=lambda row: row.declaration_line)
    return by_module


def transitive_imports(module: str, direct_imports: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    queue: deque[str] = deque(direct_imports.get(module, []))
    while queue:
        imported = queue.popleft()
        if imported in seen:
            continue
        seen.add(imported)
        queue.extend(direct_imports.get(imported, []))
    return seen


def source_span_for_declaration(
    declaration: LeanDecl,
    tex_labels: dict[str, TexLabel],
    source_lookup: dict[str, str],
    chapter_by_source: dict[str, dict[str, Any]],
    project_root: Path,
) -> tuple[list[dict[str, Any]], str, float, list[str]]:
    spans: list[dict[str, Any]] = []
    notes: list[str] = []
    matched_labels = [label for label in declaration.comment_labels if label in tex_labels]
    for label in matched_labels:
        tex = tex_labels[label]
        spans.append(
            {
                "path": tex.path,
                "line_range": numbered_range(*tex.line_range),
                "labels": [label],
                "reason": "Lean doc comment references this TeX label.",
                "method": "lean_comment_label",
            }
        )
    if spans:
        return spans, "lean_comment_label", 0.75, notes

    source_path = source_lookup.get(declaration.path)
    if not source_path:
        notes.append("No TeX source file was inferred for this Lean file.")
        return [], "unmapped", 0.0, notes

    chapter = chapter_by_source.get(source_path, {})
    target_labels = [label for label in chapter.get("target_theorems", []) if label in tex_labels]
    lean_lines = line_count((project_root / declaration.path).read_text(encoding="utf-8"))
    tex_lines = line_count((project_root / source_path).read_text(encoding="utf-8"))
    projected_line = max(1, min(tex_lines, round(declaration.declaration_line / lean_lines * tex_lines)))
    eligible = [tex_labels[label] for label in target_labels if tex_labels[label].line <= projected_line]
    if not eligible:
        eligible = [tex_labels[label] for label in target_labels]
    if eligible:
        tex = min(eligible, key=lambda row: abs(row.line - projected_line))
        spans.append(
            {
                "path": tex.path,
                "line_range": numbered_range(*tex.line_range),
                "labels": [tex.label],
                "reason": "Position fallback to the nearest manifest target label in the paired TeX chapter.",
                "method": "manifest_position_fallback",
            }
        )
        notes.append(
            "Source span is a position-based fallback, not a verified exact minimal source match."
        )
        return spans, "manifest_position_fallback", 0.2, notes

    spans.append(
        {
            "path": source_path,
            "line_range": [1, tex_lines],
            "labels": [],
            "reason": "Chapter-level fallback because no target label was available.",
            "method": "chapter_fallback",
        }
    )
    notes.append("Source span is a whole-chapter fallback and should be narrowed before gold use.")
    return spans, "chapter_fallback", 0.05, notes


def declaration_snippet(project_root: Path, declaration: LeanDecl) -> str:
    lines = (project_root / declaration.path).read_text(encoding="utf-8").splitlines()
    start, end = declaration.line_range
    return "\n".join(lines[start - 1 : end])


def find_predecessors(
    declaration: LeanDecl,
    declarations_by_module: dict[str, list[LeanDecl]],
    direct_imports: dict[str, list[str]],
    by_short_name: dict[str, list[LeanDecl]],
    project_root: Path,
    local_window: int,
    max_references: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    predecessors: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(row: LeanDecl, reason: str, method: str) -> None:
        if row.id == declaration.id or row.id in seen:
            return
        if row.path == declaration.path and row.declaration_line >= declaration.declaration_line:
            return
        predecessors.append(
            {
                "path": row.path,
                "declaration": row.full_name,
                "line_range": numbered_range(*row.line_range),
                "reason": reason,
                "method": method,
            }
        )
        seen.add(row.id)

    same_module = declarations_by_module.get(declaration.module, [])
    prior_local = [row for row in same_module if row.declaration_line < declaration.declaration_line]
    if local_window > 0:
        for row in prior_local[-local_window:]:
            add(row, "Nearest preceding declaration in the same Lean file.", "local_predecessor_window")

    imported_modules = transitive_imports(declaration.module, direct_imports)
    snippet = declaration_snippet(project_root, declaration)
    words = Counter(LEAN_WORD_RE.findall(snippet))
    lexical_hits = 0
    for word, _ in words.most_common():
        if lexical_hits >= max_references:
            break
        if len(word) < 3:
            continue
        for row in by_short_name.get(word, []):
            if row.path == declaration.path:
                if row.declaration_line < declaration.declaration_line:
                    add(row, "Declaration name appears in the Lean output chunk.", "lexical_reference")
                    lexical_hits += 1
            elif row.module in imported_modules:
                add(row, "Imported declaration name appears in the Lean output chunk.", "lexical_reference")
                lexical_hits += 1
            if lexical_hits >= max_references:
                break

    return predecessors, sorted(imported_modules)


def record_for_declaration(
    declaration: LeanDecl,
    *,
    project_root: Path,
    tex_labels: dict[str, TexLabel],
    source_lookup: dict[str, str],
    chapter_by_source: dict[str, dict[str, Any]],
    declarations_by_module: dict[str, list[LeanDecl]],
    direct_imports: dict[str, list[str]],
    by_short_name: dict[str, list[LeanDecl]],
    local_window: int,
    max_references: int,
) -> dict[str, Any]:
    source_spans, source_method, source_trust, notes = source_span_for_declaration(
        declaration,
        tex_labels,
        source_lookup,
        chapter_by_source,
        project_root,
    )
    lean_predecessors, import_closure = find_predecessors(
        declaration,
        declarations_by_module,
        direct_imports,
        by_short_name,
        project_root,
        local_window,
        max_references,
    )
    source_path = source_lookup.get(declaration.path)
    chapter = chapter_by_source.get(source_path or "", {})
    dependency_trust = 0.45 if any(row["method"] == "lexical_reference" for row in lean_predecessors) else 0.25
    return {
        "id": f"{declaration.path}:{declaration.full_name}",
        "chapter_id": chapter.get("id"),
        "output": {
            "lean_path": declaration.path,
            "declaration_names": [declaration.full_name],
            "line_range": numbered_range(*declaration.line_range),
            "chunk_kind": declaration.kind,
        },
        "minimal_context": {
            "source_spans": source_spans,
            "lean_predecessors": lean_predecessors,
            "imports": list(declaration.imports),
            "import_closure": import_closure,
            "mathlib_context": ["Mathlib APIs referenced by imported modules; exact proof-level facts not statically certified."],
        },
        "alignment": {
            "source_method": source_method,
            "comment_labels": list(declaration.comment_labels),
            "paired_source_path": source_path,
        },
        "trust": {
            "source_span": source_trust,
            "lean_dependency_graph": dependency_trust,
            "model_extraction": 0.0,
            "human_review": 0.0,
        },
        "review_notes": notes,
        "generation": {
            "generator_version": GENERATOR_VERSION,
            "generator_kind": "deterministic_static_analysis",
        },
    }


def build_graph(records: list[dict[str, Any]], declarations: list[LeanDecl], tex_labels: dict[str, TexLabel]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()

    def add_node(node: dict[str, Any]) -> None:
        if node["id"] not in seen_nodes:
            nodes.append(node)
            seen_nodes.add(node["id"])

    def add_edge(source: str, target: str, kind: str, **extra: Any) -> None:
        key = (source, target, kind)
        if key in seen_edges:
            return
        edge = {"source": source, "target": target, "kind": kind}
        edge.update(extra)
        edges.append(edge)
        seen_edges.add(key)

    source_files = sorted({tex.path for tex in tex_labels.values()})
    for path in source_files:
        add_node({"id": stable_node_id("source_file", path), "kind": "source_file", "path": path})
    for tex in tex_labels.values():
        node_id = stable_node_id("source_label", f"{tex.path}:{tex.label}")
        add_node(
            {
                "id": node_id,
                "kind": "source_label",
                "path": tex.path,
                "label": tex.label,
                "line_range": numbered_range(*tex.line_range),
            }
        )
        add_edge(stable_node_id("source_file", tex.path), node_id, "contains")

    for declaration in declarations:
        add_node(
            {
                "id": declaration.id,
                "kind": "lean_decl",
                "path": declaration.path,
                "module": declaration.module,
                "declaration": declaration.full_name,
                "declaration_kind": declaration.kind,
                "line_range": numbered_range(*declaration.line_range),
            }
        )
        file_id = stable_node_id("lean_file", declaration.path)
        add_node({"id": file_id, "kind": "lean_file", "path": declaration.path, "module": declaration.module})
        add_edge(file_id, declaration.id, "contains")
        for module in declaration.imports:
            import_id = stable_node_id("lean_import", module)
            add_node({"id": import_id, "kind": "lean_import", "module": module})
            add_edge(declaration.id, import_id, "imports")

    for record in records:
        decl_id = stable_node_id("lean_decl", f"{record['output']['lean_path']}:{record['output']['declaration_names'][0]}")
        for span in record["minimal_context"].get("source_spans", []):
            for label in span.get("labels", []):
                target = stable_node_id("source_label", f"{span['path']}:{label}")
                add_edge(decl_id, target, "source_context", method=span.get("method"))
            if not span.get("labels"):
                target = stable_node_id("source_file", span["path"])
                add_edge(decl_id, target, "source_context", method=span.get("method"))
        for predecessor in record["minimal_context"].get("lean_predecessors", []):
            target = stable_node_id("lean_decl", f"{predecessor['path']}:{predecessor['declaration']}")
            add_edge(decl_id, target, "lean_context", method=predecessor.get("method"))

    source_methods = Counter(row["alignment"]["source_method"] for row in records)
    unresolved = [
        {
            "record_id": row["id"],
            "reason": "; ".join(row["review_notes"]) or "unmapped",
        }
        for row in records
        if row["alignment"]["source_method"] in {"unmapped", "chapter_fallback", "manifest_position_fallback"}
    ]
    return {
        "schema_version": "repoprover.context_graph.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_version": GENERATOR_VERSION,
        "summary": {
            "source_label_count": len(tex_labels),
            "lean_declaration_count": len(declarations),
            "record_count": len(records),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "source_alignment_methods": dict(sorted(source_methods.items())),
            "unresolved_or_low_trust_count": len(unresolved),
        },
        "nodes": nodes,
        "edges": edges,
        "unresolved": unresolved,
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path("algebraic-combinatorics"))
    parser.add_argument("--graph-output", type=Path, default=Path("docs/minimal-context-graph.json"))
    parser.add_argument("--records-output", type=Path, default=Path("docs/minimal-context-full-records.jsonl"))
    parser.add_argument(
        "--local-window",
        type=int,
        default=0,
        help="Number of nearest preceding declarations to include before lexical references.",
    )
    parser.add_argument("--max-references", type=int, default=20)
    args = parser.parse_args()

    started = time.monotonic()
    project_root = args.project_root.resolve()
    chapters = read_manifest(project_root)
    tex_labels = parse_tex_labels(project_root)
    source_lookup = build_source_path_lookup(project_root, chapters)
    chapter_by_source = chapter_for_source(chapters)

    declarations: list[LeanDecl] = []
    lean_root = project_root / "AlgebraicCombinatorics"
    for path in sorted(lean_root.rglob("*.lean")):
        declarations.extend(parse_lean_declarations(project_root, path))
    declarations.sort(key=lambda row: (row.path, row.declaration_line, row.full_name))

    declarations_by_module = module_path_index(declarations)
    direct_imports = {module: list(rows[0].imports) for module, rows in declarations_by_module.items() if rows}
    by_short_name: dict[str, list[LeanDecl]] = defaultdict(list)
    for declaration in declarations:
        by_short_name[declaration.name].append(declaration)

    records = [
        record_for_declaration(
            declaration,
            project_root=project_root,
            tex_labels=tex_labels,
            source_lookup=source_lookup,
            chapter_by_source=chapter_by_source,
            declarations_by_module=declarations_by_module,
            direct_imports=direct_imports,
            by_short_name=by_short_name,
            local_window=args.local_window,
            max_references=args.max_references,
        )
        for declaration in declarations
    ]
    graph = build_graph(records, declarations, tex_labels)
    graph["summary"]["elapsed_seconds"] = round(time.monotonic() - started, 3)

    args.graph_output.parent.mkdir(parents=True, exist_ok=True)
    args.graph_output.write_text(json.dumps(graph, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_jsonl(args.records_output, records)

    print(f"wrote graph: {args.graph_output} ({graph['summary']['node_count']} nodes, {graph['summary']['edge_count']} edges)")
    print(f"wrote records: {args.records_output} ({len(records)} declarations)")
    print(f"source alignment methods: {json.dumps(graph['summary']['source_alignment_methods'], sort_keys=True)}")
    print(f"elapsed_seconds: {graph['summary']['elapsed_seconds']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
