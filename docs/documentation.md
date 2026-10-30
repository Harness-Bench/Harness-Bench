# Documentation Alongside Code

Documentation lives at the boundary it describes. Canonical meaning stays in
`docs/`; each code package carries a short contract next to its implementation.

## Layers

| Layer | Location | Purpose |
| --- | --- | --- |
| Canonical specification | `docs/*.md` | Intent, requirements, invariants, and terminology |
| Architecture decision | `docs/decisions/` | Why a boundary or semantic changed, and when to revisit |
| Package contract | `src/harnessbench/**/index.md` | Purpose, contents, boundaries, and ownership |
| API contract | Python docstrings | What a module, class, or function guarantees, and where its full contract lives |
| Test contract | `tests/**/index.md` | What a test layer covers and what it does not |

## Rules

1. Define each term once in `docs/` and link to it. Package docs and docstrings
   summarize; they do not create a second definition.
2. Do not claim unimplemented behavior. Mark scaffolds and drafts explicitly.
3. A package docstring states the package's responsibility and boundary, then
   links to its colocated `index.md` and the canonical specification.
4. Keep `index.md` short: purpose, contents, and boundaries. Update it when the
   directory structure or ownership changes.
5. Comments explain why a non-obvious decision or invariant exists. Docstrings
   state contracts. Do not narrate code line by line.
6. A change that alters an interface, schema meaning, or module boundary updates
   the adjacent docs, schemas, and tests in the same change.
7. Never put credentials, host-specific paths, or run outputs in documentation.

## Status vocabulary

Use these labels when status matters:

- **Implemented** — behavior exists and contract tests cover it.
- **Scaffold** — structure exists; behavior is not implemented.
- **Draft** — proposed contract; not validated.
- **Deferred** — intentionally outside the current scope.

The P1–P3 fixture baseline is **Implemented** and covered by contract,
integration, unit, and reproducibility tests; remaining P4 gates are tracked in
`roadmap.md` and `final-audit.md`. Treat a package or module as **Scaffold**
only where its colocated `index.md` or docstring says so; do not infer
unimplemented behavior from directory presence alone.

## Adding or moving a package

1. Add an `index.md` beside the package with its purpose and boundaries.
2. Add a module docstring that states the short contract and links to the
   local `index.md` and the canonical specification.
3. Update the nearest parent `index.md` if the structure or ownership changed.
4. Run `python scripts/check_docs.py`.

## Validation

`scripts/check_docs.py` is read-only. It fails when a Python package under
`src/harnessbench/` lacks a module docstring or a colocated `index.md`, when a
test layer lacks an `index.md`, or when a top-level docs page is not linked
from `docs/index.md`.
