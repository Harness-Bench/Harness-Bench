# Harness Adapters

Launch or connect to harnesses and normalize their observable events. Adapters do not determine task success.

- `base.py`: harness adapter protocol and result value object.
- `file_actions.py`: baseline harness that validates `write_file` actions and applies them inside the isolated runtime; supports the `append_trailing_newline` mechanism.
- `command.py`: command harness that executes inside the isolated bubblewrap runtime.
