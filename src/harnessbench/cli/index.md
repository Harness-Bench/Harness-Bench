# CLI

Parses commands and invokes application workflows. Business rules belong in domain/application modules, not CLI handlers.

- `main.py`: argument parsing plus the `validate-task`, `run-task`, `show-run`, `run-experiment`, and `show-experiment` commands.
- `workflows.py`: run orchestration, persistence, verification, and report reload.
- `experiment_workflows.py`: experiment execution, report persistence, and report loading.
