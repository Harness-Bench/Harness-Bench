# Harness Adapters

Launch or connect to harnesses and normalize their observable events. Adapters do not determine task success.

- `base.py`: harness adapter protocol and result value object.
- `file_actions.py`: baseline harness that applies `write_file` actions from a model response and supports the `append_trailing_newline` mechanism.
