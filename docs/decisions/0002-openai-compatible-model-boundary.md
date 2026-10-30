# ADR-0002: Use an OpenAI-Compatible Chat-Completions Boundary

- **Status:** Accepted for v0.1
- **Decision:** Add one live model adapter that speaks the OpenAI-compatible `/chat/completions` protocol, with the endpoint and model supplied per run and the API key read from an environment variable.
- **Context:** The benchmark needs a real-model path without committing the core to one vendor SDK. Many local and hosted providers expose the same chat-completions shape.
- **Consequences:** One adapter can reach multiple providers and local mock servers; provider-specific features such as streaming, tool calls, and native token accounting are not covered. Credentials are resolved at invocation time and are not written to run records. Model output remains untrusted and is still applied by the in-process file-action harness.
- **Revisit when:** provider-specific behavior, streaming, or tool-call protocols become necessary for valid comparisons.
