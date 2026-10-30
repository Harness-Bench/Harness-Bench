# CLI

Parses commands and invokes application workflows. Business rules belong in domain/application modules, not CLI handlers.

- `main.py`: argument parsing plus the `validate-task`, `run-task`, `run-model-task`, `show-run`, `run-experiment`, `show-experiment`, `run-command`, and `calibrate-verifier` commands.
- `workflows.py`: run orchestration, persistence, verification, and report reload.
- `experiment_workflows.py`: experiment execution, report persistence, and report loading.
- `command_workflows.py`: isolated command execution, trace persistence, artifact collection, and verification.
- `runtime_outcomes.py`: shared mapping from runtime results to run statuses and failure details.
- `run_lifecycle.py`: shared status-transition and record-persistence helpers.
