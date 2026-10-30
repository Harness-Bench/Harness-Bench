# Decision Records

Store consequential architecture decisions as numbered ADRs. Each record states context, decision, consequences, and revisit conditions.

- `0001-modular-monolith.md`: Python modular monolith for v0.1.
- `0002-openai-compatible-model-boundary.md`: live model access through an OpenAI-compatible chat-completions boundary.
- `0003-n1-controlled-egress-proxy.md`: N1 allowlisting through a Unix-socket HTTP(S) proxy.
- `0004-sandboxed-file-actions.md`: file-action writes run inside the isolated runtime with redacted persistence.
