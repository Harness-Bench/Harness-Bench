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
variable at invocation time, sends it only in the request `Authorization`
header, and does not persist it in the run record or model-response artifacts.
The endpoint is reached from the host process; model output is treated as
untrusted and parsed before file actions are applied.

Current limits:

- N0 uses a private network namespace with no egress; N2 shares the host network
  namespace and therefore provides open egress without packet-level monitoring;
- N1 controlled egress is not implemented. The default policy rejects N1 at
  construction, and a policy that explicitly allows N1 returns
  `policy_violation` rather than running without an allowlist;
- the command harness routes execution through this runtime; the
  recorded-response and live-model file-action paths remain in-process;
- routing the file-action paths through the runtime, N1 allowlisting, N2
  monitoring, general secret redaction, and separate verifier access remain
  open.
