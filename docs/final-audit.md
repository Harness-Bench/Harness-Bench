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

- Add N2 packet-level monitoring; N0, N1 allowlist egress, and N2 host-network policies are implemented and tested.
- Add representative task packs and golden evidence fixtures, including multilingual pairs.
- Evaluate at least one small/older and one stronger model with configured provider credentials.
- Calibrate the verifier against adjudicated real-task cases.
- Establish empirically calibrated difficulty and a held-out evaluation lifecycle.

## Post-audit implementation status

The P1 vertical slice and P2 matched-comparison baseline were implemented after this audit:

- task and experiment schema loading/validation;
- run lifecycle, condition manifests, and run records;
- recorded baseline model adapter, file-action harness with a mechanism toggle, and independent file verifier;
- persisted run records/artifacts and CLI `validate-task`, `run-task`, `show-run`, `run-experiment`, and `show-experiment`;
- matched-condition checks, repeated runs, Wilson uncertainty intervals, and separate quality/cost reporting;
- a bubblewrap-backed isolated runtime with workspace reset, resource limits, N0 isolation, N1 allowlist egress, N2 host-network policy, trace capture, and cleanup;
- an isolated command harness that persists runtime traces and artifact evidence;
- an OpenAI-compatible model adapter and `run-model-task` path with mock-server tests;
- a synthetic verifier-calibration pack with false-accept/reject metrics;
- run-record validation against `schemas/run.schema.json` on both save and load;
- file-action execution inside the isolated runtime with runtime traces;
- persisted-evidence redaction for configured secret values.

These do not change the release gate: real-model evaluation, N2 monitoring, representative task packs, verifier validation, and empirical calibration remain open.

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

The P1–P3 fixture baseline passes contract, unit, integration, and reproducibility tests, and the v0.1 fixture-baseline release report is published. Do not call this a general benchmark release until P0 review sign-off, real-model evaluation, N2 monitoring, representative task packs, adjudicated verifier calibration, and empirical calibration are complete. See `release-report.md`.
