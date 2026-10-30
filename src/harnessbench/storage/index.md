# Storage

Persists immutable run manifests, verification records, traces, and artifact references. Keep storage replaceable.

- `store.py`: filesystem layout and atomic writes for `runs/<run_id>/run.json` plus artifacts.
- `run_schema.py`: validates run records against `schemas/run.schema.json` at the persistence boundary.
- `redaction.py`: replaces configured secret values in persisted manifests and artifacts.
