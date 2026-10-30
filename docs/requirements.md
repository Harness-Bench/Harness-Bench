# Requirements

## Functional requirements

- **FR-01 Experiment definition:** tasks, conditions, budgets, repetitions, comparison intent.
- **FR-02 Condition capture:** model, harness/mechanisms, runtime, environment, network, language path, versions/settings.
- **FR-03 Execution:** stable adapter contract; timeout and resource policy.
- **FR-04 Evidence capture:** normalized events, traces, artifacts, exit status, provenance.
- **FR-05 Independent verification:** versioned verifier, explicit evidence, separate verifier failure state.
- **FR-06 Analysis:** quality, reliability, efficiency, robustness, safety, semantic integrity, verification quality, reproducibility separately.
- **FR-07 Ablation:** matched mechanism toggles and interaction experiments.
- **FR-08 Reproducibility:** reconstructable manifests and rerunnable experiments.
- **FR-09 Validation:** invalid configuration, missing evidence, condition mismatch, incomplete run detection.
- **FR-10 Benchmark ontology:** versioned task domains, task levels, environment/network profiles, language axes and mechanism manifests.
- **FR-11 Multilingual integrity:** evaluate direct, translated, transformed, mixed-language and handoff paths where applicable.
- **FR-12 Evaluator validation:** test scorer/verifier accuracy, calibration, false acceptance/rejection, and known failure modes.
- **FR-13 Validity controls:** provenance, held-out sets where feasible, contamination disclosure, difficulty calibration, perturbation variants.

## Non-functional requirements

- **NFR-01 Local-first:** core workflows function without hosted control plane.
- **NFR-02 Extensible:** new adapters/tasks/verifiers do not require unrelated core changes.
- **NFR-03 Auditable:** result links to run, conditions, evidence, verifier and analysis versions.
- **NFR-04 Safe by default:** untrusted agents and benchmark code are isolated.
- **NFR-05 Explicit uncertainty:** unknown, missing, invalid, failed, not-applicable, and unverified are distinct.
- **NFR-06 Deterministic analysis:** same records and analysis version yield same aggregates.
- **NFR-07 Semantic traceability:** critical task constraints can be traced through transformations and handoffs.

## v0.1 acceptance

A feature is complete only when contracts and tests cover it. See `roadmap.md` and `final-audit.md`; skeleton files alone do not satisfy acceptance.
