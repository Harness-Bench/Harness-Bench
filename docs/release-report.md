# v0.1 Fixture-Baseline Release Report

**Date:** 2026-10-30

**Status:** fixture-baseline release. This is not a real-model benchmark result
and does not establish model or harness performance.

## Scope

This release covers the P1–P3 roadmap slices:

- versioned task and experiment contracts;
- run lifecycle, condition manifests, and persisted run/artifact records;
- a recorded baseline model adapter and executable file-action harness;
- an OpenAI-compatible model adapter for live chat-completions endpoints;
- an isolated command harness with runtime trace persistence;
- independent file verification and a synthetic verifier-calibration pack;
- matched-comparison and ablation analysis with repeated runs and Wilson intervals;
- a bubblewrap-backed isolated runtime with resource limits, N0 network
  enforcement, trace capture, workspace reset, and cleanup.

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
harnessbench calibrate-verifier benchmarks/examples/verifier-calibration/pack.json
```

At release preparation: 118 tests passed, lint passed, documentation checks
passed, the CLI smoke path produced a persisted `success` run plus a matched
ablation report, the isolated command path produced a verified run with a
runtime trace, the synthetic calibration pack reported zero false
acceptances/rejections, and the live-model path was exercised against a local
mock chat-completions server.

## P4 exit criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| End-to-end workflow passes | Met for fixture baseline | `tests/integration/test_cli_run.py`, `test_experiment_workflow.py`, `test_command_workflow.py` |
| Schema and adapter contracts tested | Met | `tests/contract/`, `tests/unit/test_file_action_harness.py` |
| Verifier calibration harness | Met for synthetic pack | `benchmarks/examples/verifier-calibration/`, `tests/unit/test_verifier_calibration.py` |
| Small/older and stronger model evaluation when accessible | Not performed | Adapter exists, but no provider credentials are configured; only recorded responses and a local mock server were used |
| Results include provenance and verifier version | Met | Run condition manifests and `tests/reproducibility/test_experiment_replay.py` |
| Known limitations published | Met | This report |

The real-model gate remains open. No claim is made about model capability,
harness effectiveness, or leaderboard ranking.

## Known limitations

- The default baseline adapter replays a recorded response. `run-model-task`
  calls an OpenAI-compatible endpoint, but no provider is configured in the
  repository and no real-model benchmark result is included.
- The file-action harness runs in-process. The command harness runs inside the
  isolated runtime, but neither the recorded-response nor live-model
  file-action path is sandboxed.
- Only N0 offline network policy is implemented. N1/N2 requests fail closed
  with `policy_violation`.
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
- Secrets are read from one environment variable and are not written to run
  records, but general secret redaction and separate verifier access are not
  implemented.
- Isolated-runtime tests require `bwrap`; they skip when bubblewrap is absent.

## Release gate

This report closes the fixture-baseline scope only. P0 review sign-off,
real-model evaluation, representative task packs, calibration against
adjudicated verifier cases, and empirical calibration remain open before
claiming a general benchmark release.
