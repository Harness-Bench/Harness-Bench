# Domain

Owns core entities, identifiers, state transitions, and invariants. Must not depend on provider SDKs or CLI code.

- `task.py`: schema-validated task entity shared by registry, runtime, and verification.
- `run.py`: run lifecycle statuses, terminal outcomes, condition manifests, and run records.
