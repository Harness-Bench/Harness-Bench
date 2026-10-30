# Architecture

## Execution path

`Benchmark/Task → Experiment → Condition Matrix → Run → Evidence → Verification → Analysis → Report`

## Components and ownership

- `domain/`: core entities and invariants; no provider-specific logic.
- `registry/`: load and validate versioned benchmark/task definitions.
- `adapters/models/`: model invocation and provider metadata.
- `adapters/harnesses/`: harness launch, configuration, and result collection.
- `runtime/`: environment lifecycle, isolation, resource limits, network policy.
- `verification/`: independent outcome and policy checks.
- `storage/`: persisted records, traces, and artifact references.
- `analysis/`: metrics, matched comparisons, uncertainty, ablation analysis.
- `cli/`: user-facing commands; orchestration only, not business rules.

## Key boundaries

1. `Experiment` describes intended conditions; `Run` records one execution.
2. Adapters translate external systems to internal contracts; they do not define success.
3. Runtime enforces execution constraints; harness prompts are not a security boundary.
4. Verifiers consume task criteria and evidence; they do not trust agent claims.
5. Analysis consumes stored, versioned results and does not mutate source runs.

## Initial implementation shape

Use a Python modular monolith. Keep module interfaces explicit; do not split into services until measured needs justify it. Storage can begin with SQLite for structured records and JSONL/artifact files for traces, provided the storage interface remains replaceable.

## Run lifecycle

`planned → prepared → running → collected → verified → analyzed`

Terminal failure states must distinguish setup failure, execution failure, timeout, policy violation, verifier failure, and task failure. Never silently convert infrastructure failures into task failures.
