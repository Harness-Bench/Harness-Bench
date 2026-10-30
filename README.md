# HarnessBench

**A Reproducible Benchmark for Agent Harnesses**

HarnessBench is a local-first evaluation framework for measuring model–harness performance under explicit task, runtime, and network conditions.

## Foundation map

- `docs/vision.md` — purpose, boundaries, and non-goals.
- `docs/benchmark-ontology.md` — canonical entities and task descriptor contract.
- `docs/evaluation-model.md` — domains D1–D13 and independent B/E/N/H axes.
- `docs/multilingual-semantic-integrity.md` — first-class cross-lingual meaning-preservation evaluation.
- `docs/experimental-design.md` — matched comparisons, ablation, uncertainty, and language-path experiments.
- `docs/documentation.md` — docs-alongside-code layers, status labels, and maintenance rules.
- `docs/runtime-contract.md` — adapter/runtime/verifier boundaries and run status contract.
- `docs/validity-and-contamination.md` — benchmark validity and contamination limits.
- `docs/final-audit.md` — audit decisions, addressed gaps, remaining implementation gates.
- `docs/roadmap.md` — P0–P4 milestones and exit gates.

The repository is a **foundation scaffold**, not a working benchmark runner yet. Do not infer implementation or test success from the presence of skeleton modules.

## v0.1 workflow

`Task Definition → Experiment → Run → Independent Verification → Comparison Report`

## What it evaluates

- **Comparative performance:** compare harnesses under matched conditions.
- **Mechanism effects:** use ablations to estimate the effect of individual mechanisms.
- **Model–harness interaction:** test whether effects differ across model capability levels.
- **Operational quality:** measure success, reliability, cost, latency, robustness, and safety separately.

## Design invariants

1. A result is meaningful only with its task, model, harness, environment, network profile, budgets, and versions recorded.
2. Experiment definitions are separate from individual runs.
3. Success is determined by a verifier, not by the agent's self-report.
4. Task difficulty and environment complexity are separate axes.
5. Comparison scores must not hide quality–cost or quality–safety trade-offs.
6. Unknown, missing, invalid, and failed are distinct states.
7. The runtime enforces network and resource limits; prompts do not enforce security boundaries.
8. Benchmark and verifier versions are immutable once used by a recorded run.

## Repository map

- `docs/vision.md` — mission, scope, and non-goals.
- `docs/architecture.md` — component boundaries and data flow.
- `docs/documentation.md` — documentation placement and update rules.
- `docs/evaluation-model.md` — evaluation axes and terminology.
- `docs/experimental-design.md` — fair comparison and mechanism analysis.
- `docs/security-model.md` — runtime isolation and threat boundaries.
- `docs/roadmap.md` — milestones and acceptance criteria.
- `docs/decisions/` — durable architecture decisions.
- `schemas/` — machine-readable contract drafts.
- `benchmarks/` — benchmark and task definitions.
- `src/harnessbench/` — implementation packages.
- `tests/` — unit, integration, contract, and reproducibility tests.

## Status

This archive is a **repository foundation**, not a working benchmark implementation. Interfaces and schemas are initial drafts; validate them before treating them as stable contracts.

## Start here

1. Read `docs/vision.md`.
2. Read `docs/evaluation-model.md` and `docs/experimental-design.md`.
3. Follow `docs/roadmap.md` in order.
4. Record consequential design changes in `docs/decisions/`.
5. Run `python scripts/check_docs.py` after changing package boundaries or documentation.
