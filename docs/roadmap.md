# Roadmap

## P0 — Specification freeze

**Deliver:** vision, requirements, benchmark ontology, multilingual semantic integrity, runtime contract, validity/contamination, evaluation model, experimental design, architecture, security model, schemas, decision log.

**Exit criteria:**
- core terms have one canonical definition;
- domains, task/environment/network axes, mechanism manifests, and language/transformation axes are explicitly distinct;
- multilingual semantic invariants and verifier validation are specified;
- task/model/harness/runtime/verifier contracts and failure statuses are explicit;
- task level, environment level, network profile, and mechanism manifest are independent;
- Experiment and Run are separate entities;
- verifier evidence and failure categories are defined;
- v0.1 acceptance criteria are testable.

## P1 — Minimal vertical slice

**Status:** complete — see `tests/integration/test_run_workflow.py` and `tests/integration/test_cli_run.py`.

**Deliver:** one task definition, one baseline adapter, one executable harness adapter, one verifier, persisted Run and artifacts, CLI path to a result.

**Exit criteria:**
- task can be loaded, validated, run, and independently verified;
- infrastructure failure is distinct from task failure;
- run conditions and versions are stored;
- report can be regenerated from stored records.

## P2 — Matched comparison and ablation

**Status:** complete — see `tests/integration/test_experiment_workflow.py`, `tests/integration/test_cli_experiment.py`, and `tests/unit/test_compare.py`.

**Deliver:** condition matrix, at least two harness configurations, mechanism toggle, repeated runs, basic uncertainty reporting.

**Exit criteria:**
- matched conditions are checked automatically;
- unmatched comparisons are explicitly labelled;
- mechanism on/off comparison can be reproduced;
- quality and cost are reported separately.

## P3 — Isolated runtime

**Status:** complete — see `tests/integration/test_isolated_runtime.py`.

**Deliver:** environment setup/reset, resource limits, network enforcement, trace capture, cleanup and failure recovery.

**Exit criteria:**
- policy enforcement is tested independently;
- timeout, crash, setup failure, and policy violation are distinct outcomes;
- repeated runs start from declared initial state.

## P4 — Validation and v0.1 release

**Deliver:** contract/integration/reproducibility tests, example benchmark pack, documented limitations, release report.

**Exit criteria:**
- end-to-end workflow passes;
- schema and adapter contracts are tested;
- at least one small/older model and one stronger model can be evaluated when accessible;
- all results include provenance and verifier version;
- known limitations are published.

## Deferred beyond v0.1

Distributed execution, broad domain coverage, adaptive benchmark generation, advanced causal designs, universal composite scores, and specialized inference runtimes.

## Change control

A milestone is complete only when its exit criteria are met. If scope changes, update this roadmap and the affected specification before implementation expands.
