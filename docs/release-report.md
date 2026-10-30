# v0.1 Fixture-Baseline Release Report

**Date:** 2026-10-30

**Status:** fixture-baseline release. This is not a real-model benchmark result
and does not establish model or harness performance.

## Scope

This release covers the P1–P3 roadmap slices:

- versioned task and experiment contracts;
- run lifecycle, condition manifests, persisted run/artifact records, and
  run-schema validation on save and load;
- a recorded baseline model adapter and executable file-action harness that
  applies writes inside the isolated runtime;
- an OpenAI-compatible model adapter for live chat-completions endpoints;
- an isolated command harness with runtime trace persistence;
- independent file verification and a synthetic verifier-calibration pack;
- matched-comparison and ablation analysis with repeated runs and Wilson intervals;
- a bubblewrap-backed isolated runtime with resource limits, N0 network
  isolation, N1 allowlist egress, N2 host-network policy, trace capture,
  workspace reset, and cleanup;
- redaction of configured secret values from persisted run records and artifacts.

The example pack contains two synthetic tasks: `echo` and `nested-write`.
The `echo` experiment compares a baseline harness with an
`append_trailing_newline` mechanism.

## Verification evidence

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check src tests scripts
python scripts/check_docs.py
harnessbench validate-task benchmarks/examples/echo/task.json
harnessbench run-task benchmarks/examples/echo/task.json \
  --model-response benchmarks/examples/echo/model_response.json
harnessbench run-experiment benchmarks/examples/echo/experiment.json
harnessbench show-experiment experiment-echo-newline
harnessbench run-command benchmarks/examples/echo/task.json \
  --command "sh -c \"printf 'hello harnessbench\\n' > greeting.txt\""
harnessbench run-command benchmarks/examples/echo/task.json \
  --network-profile N1 --allow-host 127.0.0.1:8000 \
  --command "python3 -c '...'"
harnessbench calibrate-verifier benchmarks/examples/verifier-calibration/pack.json
```

At release preparation: 139 tests passed, lint passed, documentation checks
passed, the CLI smoke path produced a persisted `success` run plus a matched
ablation report, the isolated command path produced verified runs with N0, N1,
and N2 network policies, the synthetic calibration pack reported zero false
acceptances/rejections, and the live-model path was exercised against a local
mock chat-completions server.

Post-release hardening added run-record validation against
`schemas/run.schema.json` at both the save and load boundaries, routed
file-action writes through the isolated runtime with persisted runtime traces,
and added persisted-evidence redaction for configured secret values. The
current suite has 151 passing tests, and lint and documentation checks still
pass.

## P4 exit criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| End-to-end workflow passes | Met for fixture baseline | `tests/integration/test_cli_run.py`, `test_experiment_workflow.py`, `test_command_workflow.py` |
| Schema and adapter contracts tested | Met | `tests/contract/`, `tests/integration/test_run_store.py`, `tests/unit/test_file_action_harness.py` |
| Verifier calibration harness | Met for synthetic pack | `benchmarks/examples/verifier-calibration/`, `tests/unit/test_verifier_calibration.py` |
| Small/older and stronger model evaluation when accessible | Not performed | Adapter exists, but no provider credentials are configured; only recorded responses and a local mock server were used |
| Network policy enforcement | Met for N0/N1/N2; N2 monitoring open | `tests/integration/test_isolated_runtime.py`, `tests/unit/test_egress_proxy.py` |
| Results include provenance and verifier version | Met | Run condition manifests and `tests/reproducibility/test_experiment_replay.py` |
| Known limitations published | Met | This report |

The real-model gate remains open. No claim is made about model capability,
harness effectiveness, or leaderboard ranking.

## Known limitations

- The default baseline adapter replays a recorded response. `run-model-task`
  calls an OpenAI-compatible endpoint, but no provider is configured in the
  repository and no real-model benchmark result is included.
- The file-action harness applies writes inside the isolated runtime. The model
  request itself is made from the host process, so endpoint access is not
  sandboxed.
- N0, N1, and N2 policies are implemented. N1 supports proxy-aware HTTP
  requests and CONNECT tunnels to allowlisted host/port endpoints; it does not
  provide transparent interception, protocol filtering, TLS inspection, or
  wildcard hosts. N1 records host/port decisions, not request paths or payloads.
  N2 provides open host-network access without packet-level monitoring.
- The example pack is synthetic and tiny; it is not representative of coding,
  cybersecurity, or multilingual benchmark coverage.
- Verifier calibration against adjudicated real-task cases is not established;
  the included calibration pack is synthetic.
- Task difficulty is not empirically calibrated; there is no held-out set.
- Multilingual and semantic-integrity tasks are not included.
- Storage uses filesystem records, not SQLite; retention and garbage collection
  policies are not implemented.
- Uncertainty reporting is a Wilson interval over repeated synthetic runs. It
  is not a paired task-level inference or a substitute for independent tasks.
- Secrets are read from one environment variable and are redacted from
  persisted run records and artifacts. Separate verifier access and broader
  secret-source integration are not implemented.
- Isolated-runtime and file-action integration tests require `bwrap`; they skip
  when bubblewrap is absent.

## Release gate

This report closes the fixture-baseline scope only. P0 review sign-off,
real-model evaluation, N2 monitoring, representative task packs, calibration
against adjudicated verifier cases, and empirical calibration remain open
before claiming a general benchmark release.
