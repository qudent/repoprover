# RepoProver

[![Paper PDF](https://img.shields.io/badge/Paper-PDF-red?style=for-the-badge)](auto_textbook_formalization.pdf)
[![Formalization](https://img.shields.io/badge/Formalization-GitHub-green?style=for-the-badge)](https://github.com/facebookresearch/algebraic-combinatorics)
[![Blueprint Website](https://img.shields.io/badge/Blueprint-Website-blue?style=for-the-badge)](https://faabian.github.io/algebraic-combinatorics/)
[![Blueprint PDF](https://img.shields.io/badge/Blueprint-PDF-red?style=for-the-badge)](https://github.com/facebookresearch/algebraic-combinatorics/blob/main/blueprint/print/print.pdf)

Code for [Automatic Textbook Formalization (Gloeckle, Rammal, Arnal, Munos, Cabannes, Synnaeve, Hayat, 2026)](auto_textbook_formalization.pdf).

RepoProver is a multi-agent scaffold for large-scale formalization of mathematics textbooks in Lean. It orchestrates multiple LLM agents that collaborate on a shared git repository with the Lean project: sketcher agents translate definitions and theorem statements, prover agents fill in proofs, and reviewer agents enforce quality via pull request reviews. Coordination happens through a lightweight file-system-based issue tracker and a merge queue that ensures the main branch always builds.

This code produced an [automatic formalization](https://github.com/facebookresearch/algebraic-combinatorics) of the graduate textbook [Algebraic Combinatorics](https://arxiv.org/abs/2506.00738) by Darij Grinberg.

## Scale of the current Algebraic Combinatorics corpus

These counts are from the local vendored snapshot under
`algebraic-combinatorics/` as of 2026-05-05. Token counts are rough
characters-divided-by-four estimates, intended for budget sizing rather than
exact tokenizer accounting.

| Surface | Measured scale |
|---|---:|
| TeX source files | 45 |
| TeX source bytes | 1,508,796 |
| TeX source estimated tokens | ~377,000 |
| Unique TeX labels | 768 |
| Theorem-like TeX environments | 462 total, 360 labeled |
| Generated Lean declaration records | 5,684 |
| Exact Lean-doc-comment to TeX-label alignments | 1,062 |
| Deterministic gold-candidate declaration records | 645 |
| Local Mathlib Lean files | 7,648 |
| Local Mathlib source bytes | ~87.4 MB |
| Local Mathlib source estimated tokens | ~21.9M |
| Mathlib doc/module comments | 84,971 comments, ~15.4 MB |
| Mathlib doc/module comment estimated tokens | ~3.78M |

The theorem-like TeX environments counted here are `theorem`, `lemma`,
`proposition`, `corollary`, `definition`, `conjecture`, `statement`, and
`example`. The current minimal-context benchmark is declaration-level: one row
per Lean declaration, aligned back to TeX labels. A single book theorem can
therefore correspond to several Lean declarations.

The context-selection experiments do not put all Mathlib docs in the prompt. In
the latest three-record declaration-progress selector probe, the selector chose
5 unique Mathlib names and hydration inserted 20 local Mathlib source snippets:
7,408 characters, or about 1,850 estimated tokens. The final selected context
packs for those three records carried about 13,300 characters, or 3,300
estimated tokens, including selector notes and project-context summaries. That
is roughly 0.05-0.09% of the estimated Mathlib doc-comment token pool for the
probe, which is the intended operating regime: tight context packs, not broad
Mathlib dumps.

### Imported Lean surface and likely context needs

The generated Algebraic Combinatorics Lean files are built in a very broad
environment. In the current snapshot, all 52 non-root project modules import
root `Mathlib` directly. Those files have 143 direct import statements total:
52 `Mathlib` imports and 91 project-module imports. The root
`AlgebraicCombinatorics.lean` file then imports the 52 project modules.

This means "what is imported" is much larger than "what a generator should see
in prompt context":

| Surface imported or available | Scale |
|---|---:|
| Project Lean source modules | 52 |
| Project named declarations in context graph | 5,684 |
| Project theorem declarations | 2,402 |
| Project lemma declarations | 2,070 |
| Project definition declarations | 1,042 |
| Project instances / abbrevs / structures / inductives | 74 / 60 / 30 / 6 |
| Non-root project modules importing root `Mathlib` | 52 / 52 |
| Mathlib named declarations from a comment-stripped source regex scan | ~211,900 |
| Mathlib theorem/lemma declarations from that scan | ~165,000 |
| Mathlib definition declarations from that scan | ~29,500 |
| Mathlib instance declarations from that scan | ~11,000 |

The Mathlib declaration scan is approximate because it is a fast source scan,
not an elaborated Lean environment dump. It is still the right order of
magnitude for context-selection difficulty: a source-only generator should not
be expected to guess a few exact APIs and signatures out of roughly two hundred
thousand imported declarations.

Mathlib is also topically broad. The largest local Mathlib directories by
scanned named declarations are:

| Mathlib area | Scanned declarations |
|---|---:|
| `Algebra` | ~33,400 |
| `Analysis` | ~22,900 |
| `Data` | ~21,300 |
| `CategoryTheory` | ~21,000 |
| `Topology` | ~18,700 |
| `RingTheory` | ~14,800 |
| `Order` | ~13,600 |
| `LinearAlgebra` | ~10,000 |
| `MeasureTheory` | ~9,900 |
| `Combinatorics` | ~5,600 |

The declaration-level gold-candidate records suggest that the non-Mathlib
context actually needed around a target is much smaller, but not zero. For the
645 mechanically clean gold candidates:

| Candidate-context measure | Median | p90 | p95 | Max |
|---|---:|---:|---:|---:|
| Source span lines | 32 | 64 | 77 | 80 |
| Local predecessor declarations | 1 | 4 | 6 | 10 |
| Active file-context spans | 4 | 7 | 7 | 9 |
| Target output declaration lines | 9 | 29 | 36 | 50 |
| Source + file context + predecessor text, estimated tokens | ~540 | ~1,260 | ~1,720 | ~4,770 |

These estimates exclude selected Mathlib API snippets. The current selector
probe data suggests that a tight Mathlib addition can often be on the order of
hundreds of tokens per declaration when the selector picks exact names, but that
is not yet certified across the full corpus.

Theorem-level units are often multi-declaration units. Among exact
Lean-comment-to-TeX-label alignments, 415 source labels are represented; 227 of
those labels map to more than one Lean declaration. Declarations per exact label
have median 2, p90 6, p95 8, and max 29. This is why the revised pipeline treats
one LaTeX theorem/environment as a planning unit and Lean declarations as
inner-loop verification units.

The practical takeaway is that guessing is hard for two separate reasons:
first, the imported Mathlib search space is enormous and diverse; second, even
with the right mathematics, the model must choose the same theorem shape,
supporting project declarations, local notation, namespace/import context, and
exact Mathlib signatures. Context selection is intended to reduce that problem
to a small, explicit context pack so remaining failures are closer to genuinely
wrong math or wrong assumptions.

## Setup

Requires Python 3.10+. Install in editable mode:

```bash
pip install -e .
```

## Preparing a formalization project

RepoProver operates on a Lean project repository. Before running, you need to set up:

1. **Create a Lean project with Mathlib** and build it:
   ```bash
   lake init MyProject math
   lake update
   lake build
   ```

2. **Add LaTeX source files** under a `tex/` directory inside the project, organized by topic:
   ```
   MyProject/
   ├── lakefile.lean
   ├── lean-toolchain
   ├── lake-manifest.json
   ├── MyProject.lean           # root import file
   ├── MyProject/
   │   └── tex/                 # LaTeX source chapters
   │       ├── all.tex          # full textbook source (optional)
   │       ├── Topic1/
   │       │   ├── Chapter1.tex
   │       │   └── Chapter2.tex
   │       └── Topic2/
   │           └── ...
   ├── manifest.json            # chapter manifest (see below)
   ├── CONTENTS.md              # structure documentation (see below)
   └── issues/                  # issue tracker (see below)
   ```

   The tex files should be split by chapter/section so each can be assigned to a sketcher agent independently. An `all.tex` with the full source can be included for reference. Note that tex files are read-only — agents can read them but never modify source material.

3. **Create a `CONTENTS.md`** at the project root documenting the structure of tex sources and corresponding Lean files. The coordinator generates an initial version from the manifest, and agents update it as the Lean codebase evolves. It serves as the central reference for project structure, proof status and architecture notes.

4. **Create a `manifest.json`** at the project root listing the chapters to formalize and their target theorems/definitions. Each chapter entry has:
   - `id`: unique identifier for the chapter
   - `title`: human-readable chapter title
   - `source_path`: path to the LaTeX source file (relative to project root)
   - `target_theorems`: list of theorem/definition IDs to formalize from this chapter

   See [`configs/example_manifest.json`](configs/example_manifest.json) for a full example from the algebraic combinatorics case study.

5. **Create an empty `issues/` directory** at the project root. Agents use this as a lightweight file-system-based issue tracker — they create short YAML files here to flag blockers, request refactorings, or coordinate work across chapters.

6. **Initialize git** (with branch name `main`) in the project if not already done — RepoProver uses git for version control, branching and merging.

## Usage

### Running the coordinator

```bash
python -m repoprover run /path/to/lean/project --pool-size 10
```

This starts the main coordinator loop which launches sketcher, prover, maintainer and reviewer agents, manages the merge queue and tracks progress. The project state is saved in `.repoprover/` inside the Lean project directory.

Use `--clean` to start from scratch, `--verbose` for debug logging.

### Multi-node (SLURM)

For distributed runs across multiple machines, use the stool launcher:

```bash
python -m repoprover.stool --name myrun --project /path/to/lean/project
```

The stool launcher snapshots the repoprover code to a dump directory, symlinks the Lean project (avoiding slow copies of `.lake/` and `.git/`) and submits a SLURM job. Rank 0 runs the coordinator in a background thread; all ranks (including rank 0) run as workers that pull tasks from the coordinator.

Options:

- `--launcher bash` — run directly if already inside an `salloc` session
- `--pool-size N` — number of Lean REPL instances per node (default: 10)
- `--nodes N` — number of SLURM nodes (default: 1)
- `--agents-per-target N` — max parallel agents per theorem/issue (default: 1)
- `--prs-to-issues` — convert pending PRs to issues when resuming a run
- `--clean` — wipe state and restart from scratch
- `--dirs-exists-ok` — reuse an existing dump directory

See [`configs/example.yaml`](configs/example.yaml) for an example configuration.

### Analysis scripts

```bash
# Token usage breakdown by agent type and outcome
python scripts/count_tokens.py /path/to/lean/project

# Agent efficiency plots over time
python scripts/plot_agent_efficiency.py /path/to/lean/project --out ./plots

# Audit minimal-context pilot records with OpenRouter
python scripts/review_minimal_context_records.py \
  --model qwen/qwen3.6-35b-a3b \
  --reasoning-effort none
```

### Smoke test

A toy project is included under `examples/toy_project/` for quick testing. The setup script copies the files to a working directory, initializes git, fetches Mathlib and builds the project:

```bash
bash examples/toy_project/setup.sh /tmp/repoprover-toy-test
```

Then run repoprover on it:

```bash
source .venv/bin/activate
python -m repoprover run /tmp/repoprover-toy-test --pool-size 1 --provider google --no-background-agents --verbose
```

The toy project has one chapter with 4 trivial targets (a definition and 3 theorems about doubling natural numbers).
Add `--stop-after-first-merge` when you only want a bounded first-merge smoke
instead of continuing into follow-up proof or maintenance work.

Use `--provider {anthropic,openai,google,openrouter}` to select the LLM backend. If omitted, RepoProver chooses the first configured provider API key from the environment.

### Trajectory viewer

To inspect agent trajectories from a run:

```bash
python -m repoprover.viewer --dir /path/to/lean/project/runs --port 8080
```

## License

This project is licensed under the terms in [LICENSE](LICENSE).
