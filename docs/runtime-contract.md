# Runtime & Adapter Contracts

## Contract boundaries

- **Model adapter:** invokes a declared model/runtime and records request parameters, response, token/resource usage where available, and provider errors.
- **Harness adapter:** launches a declared harness/configuration and reports events/artifacts; it cannot declare its own run successful.
- **Runtime controller:** enforces isolation, permissions, resource/time limits, network policy, setup/reset, and cleanup outside model prompts.
- **Verifier:** consumes task criteria and evidence with access separation where feasible; emits structured verdicts and evidence references. Verifier outcomes are `passed`, `failed`, or `invalid`; `invalid` is a verifier/evidence problem, not a task failure.
- **Analyzer:** reads immutable records and emits versioned metrics; it does not mutate source runs.

## Required run record

Freeze model and harness revisions/configs, runtime/container image, OS/dependencies, tools and permissions, environment/network policy, language path, budget limits, seed when supported, task version, verifier version, timestamps, exit status, artifacts, and provenance. Record unavailable values explicitly.

## Lifecycle and status

`planned → prepared → running → collected → verified → analyzed`

Terminal statuses must distinguish setup failure, execution failure, timeout, resource limit, policy violation, adapter failure, verifier failure, invalid evidence, task failure, partial success, and success. Infrastructure failure must not be silently scored as task failure. Preserve partial artifacts on failure when safe.

## Isolation

Untrusted code and agents never execute directly on the host. Enforce least privilege and network egress at runtime, redact secrets before persistence, cap CPU/memory/disk/process/time, and test cleanup and reset behavior independently.
