# Security Model

## Trust boundary

The model, harness, task content, tool output, and downloaded artifacts may be untrusted. The host, runtime controller, secret store, and verifier are trusted components whose integrity must be protected.

## Required controls

- Run agents in isolated environments with least privilege.
- Enforce network egress in the runtime, not in prompts.
- Apply CPU, memory, disk, process, and wall-time limits.
- Keep credentials out of task artifacts and traces; redact sensitive values before persistence.
- Separate verifier access from agent access where feasible.
- Version task definitions, hidden tests, verifiers, and environment images.
- Preserve audit logs for policy violations and abnormal termination.
- Never run untrusted benchmark code directly on the host.

## Network profiles

N0, N1, and N2 are policy profiles, not trust levels. Each run must record the actual enforcement mechanism and policy. A label without enforcement evidence is insufficient.

## Security result categories

Distinguish:
- attempted policy violation;
- blocked violation;
- successful boundary escape;
- insufficient evidence;
- runtime/control failure.

A blocked attempt may be a safety success for the runtime and still be a task failure. Report both dimensions separately.

## Implemented baseline (P3)

`runtime/isolated.py` uses bubblewrap when available and fails closed otherwise. For N0 it creates user, PID, IPC, UTS, and cgroup namespaces; drops capabilities; binds `/usr` and `/etc` read-only; mounts `/tmp` as tmpfs; and exposes only the workspace as writable. It applies CPU, address-space, file-size, process, and wall-clock limits, captures stdout/stderr and exit status, and removes the workspace on cleanup.

The OpenAI-compatible model adapter resolves its API key from an environment
variable at invocation time and sends it only in the request `Authorization`
header. The recorded-response and live-model file-action paths apply their
writes inside the isolated runtime. The model request itself is made from the
host process; model output is treated as untrusted and validated before it is
passed to the sandbox. Configured secret values are redacted from persisted run
records and artifacts.

N1 uses a private network namespace and an exact host/port allowlist enforced
by a host-side HTTP(S) proxy. The sandbox reaches the proxy through a read-only
Unix socket and a loopback bridge. Direct host-network access is unavailable.
Allowed and denied host/port decisions are recorded in the runtime trace without
request paths or payloads.

Current limits:

- N0 uses a private network namespace with no egress; N2 shares the host network
  namespace and therefore provides open egress without packet-level monitoring;
- N1 requires at least one allowlist entry and fails closed otherwise. It
  supports proxy-aware HTTP requests and CONNECT tunnels to allowlisted
  host/port endpoints, but does not provide transparent interception, protocol
  filtering, TLS inspection, or wildcard hosts;
- the command harness and file-action paths route execution through this
  runtime; the model request remains host-side;
- N2 monitoring, separate verifier access, and broader secret-source
  integration remain open.
