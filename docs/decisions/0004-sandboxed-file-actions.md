# ADR-0004: Apply File Actions Inside the Isolated Runtime

- **Status:** Accepted for v0.1
- **Decision:** Parse and validate model file actions on the host, serialize the validated write plan, and apply it inside the bubblewrap runtime through a stdin-fed helper process. Persist the runtime trace with the run and redact configured secret values from run records and artifacts.
- **Context:** The recorded-response and live-model paths previously wrote files in-process. That left the file-action baseline outside the runtime boundary used by the command harness and made the isolation claim inconsistent across task kinds.
- **Consequences:** File-action execution now shares the runtime policy, workspace reset, resource limits, trace capture, and cleanup path. The model request remains host-side because the adapter boundary is outside the sandbox. The runtime requires `bwrap`; environments without it skip the affected integration tests and fail closed at execution. Redaction is value-based and covers secrets explicitly supplied by the caller; it does not discover arbitrary secret material.
- **Revisit when:** model requests also need runtime routing, the action protocol expands beyond file writes, or secret discovery requires a dedicated secret store.
