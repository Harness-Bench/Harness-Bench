# Storage

Persists immutable run manifests, verification records, traces, and artifact references. Keep storage replaceable.

- `store.py`: filesystem layout and atomic writes for `runs/<run_id>/run.json` plus artifacts.
