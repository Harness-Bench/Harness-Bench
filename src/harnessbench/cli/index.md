# CLI

Parses commands and invokes application workflows. Business rules belong in domain/application modules, not CLI handlers.

- `main.py`: argument parsing plus the `validate-task`, `run-task`, and `show-run` commands.
- `workflows.py`: run orchestration, persistence, verification, and report reload.
