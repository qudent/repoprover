# Vendored Snapshot Cleanup

This vendored copy keeps the canonical Lean and textbook sources needed for
minimal-context dataset work, while dropping duplicate or generated blueprint
artifacts that repeat the same chapter content.

Removed:

- `blueprint/src/chapter_*.tex`: blueprint chapter copies with Lean annotations
  that substantially duplicate `AlgebraicCombinatorics/tex/**`.
- `blueprint/src/print.pdf`, `blueprint/print/`, and `blueprint/web/`:
  generated documentation outputs not needed for source-line mapping.

Kept:

- `AlgebraicCombinatorics/**/*.lean`: the formalization output source.
- `AlgebraicCombinatorics/tex/**`: the canonical textbook TeX source used for
  evidence spans.
- `manifest.json`, `blueprint/lean_decls`, and blueprint helper scripts:
  lightweight metadata that can still help map Lean declarations to source
  targets.

Upstream source: `facebookresearch/algebraic-combinatorics` at commit
`b6022318e986a0c20764569208ba8ebbe1c04dbf`.
