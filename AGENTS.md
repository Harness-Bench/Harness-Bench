# Repository Navigation and Contribution Rules

## Source of truth

- Implementation is authoritative for implemented behavior.
- Versioned schemas are authoritative for serialized data contracts.
- `docs/` records intent, constraints, and decisions; docs must not claim unimplemented behavior.
- `README.md` is an overview, not a substitute for detailed specifications.

## Before changing code

1. Read the nearest `index.md` and relevant design document.
2. Identify affected schemas, interfaces, tests, and consumers.
3. Preserve explicit unknowns; do not silently invent missing requirements.
4. Update tests and documentation in the same change.
5. Record architectural decisions that alter module boundaries or semantics.

## Meaning-preservation rules

- Keep one canonical definition for each term; link to it rather than duplicating it.
- Separate requirements, hypotheses, implementation status, and observed results.
- Do not conflate task difficulty with environment complexity.
- Do not infer success from an agent's narrative.
- Do not compare runs as matched if material conditions differ.
- Label assumptions and unverified claims explicitly.

## Navigation

Each major directory has an `index.md` describing its purpose, contents, and boundaries. Keep it short and update it when the directory structure or ownership changes.
