"""Core entities and invariants; provider-agnostic.

Owns canonical identifiers, state transitions, and invariants shared by the
rest of the system. Must not depend on provider SDKs, adapters, storage, or
CLI code.

See ``index.md`` in this package and ``docs/benchmark-ontology.md``.
"""
