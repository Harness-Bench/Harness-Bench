# CLI

Parses commands and invokes application workflows. Business rules belong in domain/application modules, not CLI handlers.

- `main.py`: argument parsing plus the `validate-task`, `run-task`, `show-run`, `run-experiment`, `show-experiment`, and `run-command` commands.
- `workflows.py`: run orchestration, persistence, verification, and report reload.
- `experiment_workflows.py`: experiment execution, report persistence, and report loading.
- `command_workflows.py`: isolated command execution, trace persistence, artifact collection, and verification.
- `run_lifecycle.py`: shared status-transition and record-persistence helpers.
