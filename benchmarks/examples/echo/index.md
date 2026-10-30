# Echo Greeting Task

Minimal filesystem task for the first vertical slice. The agent must create
`greeting.txt` with exact content. Success is determined by file criteria, not
by the agent's report.

- `task.json`: task definition validated against `schemas/task.schema.json`.
- `model_response.json`: recorded baseline response with one `write_file` action.
- `model_response_no_newline.json`: response used to demonstrate the newline-normalization mechanism.
- `experiment.json`: two-condition ablation with three repetitions per condition.
