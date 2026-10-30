"""Environment lifecycle and enforced execution policy.

Owns setup/reset, isolation, resource and time limits, network policy, and
cleanup. Enforcement happens here, not in model or harness prompts.

See ``index.md`` in this package and ``docs/runtime-contract.md``.
"""
