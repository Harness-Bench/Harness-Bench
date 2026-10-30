# Nested Write Task

Minimal second example task. The agent must create `out/result.txt` with exact
content, exercising nested-path creation and verification.

- `task.json`: task definition validated against `schemas/task.schema.json`.
- `model_response.json`: recorded baseline response with one `write_file` action.
