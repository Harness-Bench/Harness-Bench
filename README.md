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
- `docs/release-report.md` — v0.1 fixture-baseline scope, evidence, and limitations.

The repository is a **foundation with P1/P2/P3 vertical slices**, not a complete benchmark. Do not infer broad implementation, benchmark coverage, or test success beyond the recorded checks.

## v0.1 workflow

`Task Definition → Experiment → Run → Independent Verification → Comparison Report`

## Current vertical slice

Task loading, schema validation, recorded and live-model execution, file
verification, run persistence, and matched-comparison analysis are
implemented.

```bash
harnessbench validate-task benchmarks/examples/echo/task.json

harnessbench run-task benchmarks/examples/echo/task.json \
  --model-response benchmarks/examples/echo/model_response.json

harnessbench show-run <run_id>

harnessbench run-experiment benchmarks/examples/echo/experiment.json
harnessbench show-experiment experiment-echo-newline

harnessbench run-command benchmarks/examples/echo/task.json \
  --command "sh -c \"printf 'hello harnessbench\\n' > greeting.txt\""

harnessbench run-command benchmarks/examples/echo/task.json \
  --network-profile N1 --allow-host 127.0.0.1:8000 \
  --command "python3 -c '...'"

OPENAI_API_KEY=... harnessbench run-model-task benchmarks/examples/echo/task.json \
  --endpoint http://localhost:8000/v1 --model local-model

harnessbench calibrate-verifier benchmarks/examples/verifier-calibration/pack.json
```

The recorded-response and live-model file-action paths apply writes inside the
bubblewrap runtime with resource limits, trace capture, and cleanup. The model
request itself is made from the host process. N0 blocks egress, N1 permits only
exact `--allow-host` entries through an HTTP(S) proxy, and N2 shares the host
network. `run-model-task` calls an OpenAI-compatible chat-completions endpoint;
no provider credentials or real-model result are included in this repository.
Configured secret values are redacted from persisted run records and artifacts.
N2 packet-level monitoring remains open.

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
- `docs/release-report.md` — v0.1 scope, evidence, and published limitations.
- `docs/decisions/` — durable architecture decisions.
- `schemas/` — machine-readable contract drafts.
- `benchmarks/` — benchmark and task definitions.
- `src/harnessbench/` — implementation packages.
- `tests/` — unit, integration, contract, and reproducibility tests.

## Status

The repository has a **v0.1 fixture-baseline release**: P1/P2/P3 slices, a second example task, reproducibility checks, and an isolated command-execution path. See [`docs/release-report.md`](docs/release-report.md) for evidence and limitations. This is not a real-model benchmark result; the real-model, N2 monitoring, and calibration gates remain open.

## Start here

1. Read `docs/vision.md`.
2. Read `docs/evaluation-model.md` and `docs/experimental-design.md`.
3. Follow `docs/roadmap.md` in order.
4. Record consequential design changes in `docs/decisions/`.
5. Run `python scripts/check_docs.py` after changing package boundaries or documentation.
