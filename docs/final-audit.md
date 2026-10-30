# Foundation Final Audit

Audit scope: repository foundation and specification consistency, not runtime correctness. No implementation, benchmark execution, or end-to-end test result is implied by this document.

## Decisions carried forward

- Generic, local-first evaluation foundation; initial demonstration domains: coding and cybersecurity.
- Comparison and mechanism-level evaluation together; matched comparisons, ablation, interaction, model×harness interaction, and environment transfer.
- Python modular monolith; CLI + SQLite/JSONL/artifact storage; adapters; isolated runtime; independent verifier.
- Independent axes: task B0–B4, environment E0–E3, network N0–N2, mechanism manifest H0–H5.
- Experiment (question/conditions/design) is distinct from Run (one actual attempt).
- Include ~1B and older models as well as stronger models; distinguish intrinsic model capability from harness delta.
- Multilingual semantic integrity is a first-class domain, including natural languages, programming languages, mixed artifacts, translation, compression, and handoffs.

## Gaps identified and addressed in this revision

- Added canonical benchmark ontology and task contract minimum.
- Added first-class multilingual semantic integrity subdomains, path conditions, invariants, metrics, and test categories.
- Expanded metrics to include verifier quality, semantic drift, uncertainty, and critical constraint inversions.
- Added runtime/adapter contracts and explicit failure-state distinctions.
- Added validity, contamination, and empirical difficulty-calibration requirements.
- Expanded experimental design to include language-path experiments and verifier validation.

## Remaining implementation work (not a spec defect)

- Validate run records against the run schema at the persistence boundary.
- Route agent execution through the isolated runtime and add secret redaction.
- Implement N1/N2 network profiles and test them independently.
- Add representative task packs and golden evidence fixtures, including multilingual pairs.
- Validate verifier calibration, false acceptance/rejection, and known failure modes.
- Establish empirically calibrated difficulty and a held-out evaluation lifecycle.

## Post-audit implementation status

The P1 vertical slice and P2 matched-comparison baseline were implemented after this audit:

- task and experiment schema loading/validation;
- run lifecycle, condition manifests, and run records;
- recorded baseline model adapter, file-action harness with a mechanism toggle, and independent file verifier;
- persisted run records/artifacts and CLI `validate-task`, `run-task`, `show-run`, `run-experiment`, and `show-experiment`;
- matched-condition checks, repeated runs, Wilson uncertainty intervals, and separate quality/cost reporting;
- a bubblewrap-backed isolated runtime with workspace reset, resource limits, N0 network enforcement, trace capture, and cleanup.

These do not change the release gate: isolation, representative task packs, verifier validation, and empirical calibration remain open.

## Consistency checks

- Domains D1–D13 describe *what is measured*; B0–B4 describe task complexity; E0–E3 describe environment; N0–N2 describe network; H0–H5 describe mechanism families. They are not interchangeable.
- Model, harness, runtime, verifier, and analyzer responsibilities are separated.
- A verifier failure is not a task failure; infrastructure failure is not silently a model failure.
- Multilingual is not only a task tag: semantic invariants and transformation paths are explicit.
- Raw outcomes are preserved; no universal scalar score is required for v0.1.
- Claims of causality require matched controls; unmatched comparisons are labelled.
- Security enforcement belongs to the runtime, not prompts.
- v0.1 scope remains a foundation and small vertical slice, not exhaustive benchmark coverage.

## Release gate

Do not call the foundation implementation-complete until P0 specification review is signed off and P1 vertical slice passes contract/integration tests. This ZIP is a specification/repository scaffold; it does not claim those runtime gates have passed.
