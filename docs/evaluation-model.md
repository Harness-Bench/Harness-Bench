# Evaluation Model

## Independent classification axes

Never compress these axes into one difficulty label.

### Task level (B0–B4)
- **B0 Atomic:** one bounded decision/action.
- **B1 Sequential:** multiple dependent steps.
- **B2 Stateful:** inspect/modify state and respond to feedback or errors.
- **B3 System:** cross files, tools, or services.
- **B4 Open-ended:** ambiguous requirements, design trade-offs, or novel failure modes.

### Environment (E0–E3)
- **E0 Controlled:** fixed input and controlled state.
- **E1 Executable:** real commands/files.
- **E2 Stateful system:** multiple services, changing state, or injected faults.
- **E3 Workflow-like:** bounded real-user workflow.

### Network (N0–N2)
- **N0 Offline:** external network blocked.
- **N1 Controlled:** allowlist or controlled services.
- **N2 Open:** general access under declared, monitored policy; not synonymous with unrestricted access.

### Mechanism manifest (H0–H5 families; not ranks)
- **H0 Model-only baseline**
- **H1 Tool execution**
- **H2 Context management** (retrieval, summarization, compaction, state retention)
- **H3 Control and recovery** (validation, retries, error recovery, stop conditions)
- **H4 Multi-agent orchestration**
- **H5 Adaptive system**

A system can combine mechanisms. Store each mechanism and its configuration explicitly; H labels are not a single ordered score.

## Evaluation domains (what is measured)

These are orthogonal domains; one task may exercise several. The benchmark registry must use canonical IDs and explicit task-to-domain mappings.

- **D1 Understanding & semantic interpretation:** intent, ambiguity, reference resolution, assumptions, constraints, unknowns.
- **D2 Planning & decomposition:** dependency ordering, coverage, plan feasibility, decomposition loss.
- **D3 Tool use & execution:** correct tool choice, arguments, state changes, execution discipline.
- **D4 Context & state integrity:** retrieval, context selection, compaction, memory/state consistency.
- **D5 Verification & evidence:** independent checks, evidence quality, verifier calibration.
- **D6 Recovery & correction:** diagnosis, rollback, retry quality, recovery from false starts.
- **D7 Orchestration & coordination:** delegation, handoff fidelity, integration, conflict resolution.
- **D8 Adaptation & resource allocation:** escalation, stopping, budget/model/tool selection.
- **D9 Safety & security:** least privilege, boundary enforcement, secret handling, policy compliance.
- **D10 User intent & interaction:** clarification, uncertainty disclosure, consent/approval boundaries.
- **D11 Environment & integration:** dependency/setup robustness, workflow integration, repeatability.
- **D12 Generalization & transfer:** unseen variants, perturbation resistance, domain/environment transfer.
- **D13 Multilingual & semantic integrity:** cross-lingual understanding and preservation; specified further in `multilingual-semantic-integrity.md`.

Do not treat these domains as mutually exclusive, a mandatory progression, or one composite score.

## Language axes

Record separately: (1) natural-language input/output languages, (2) programming languages, (3) interface/artifact languages (logs, docs, code comments, CLI output), (4) transformation path (direct, translate, summarize, compress, handoff, or combinations), and (5) language mixing. Do not use English-only tests as a proxy for general capability.

## Model coverage and capability separation

Include small/older and stronger models when available. Record exact model/revision, runtime/provider, inference parameters, context limits, quantization/offload where relevant, and budget. Report model-only baseline, harness outcome, and the delta; do not attribute a gain to the harness when model, budget, tools, or environment also changed.

## Outcome dimensions

Report independently:
- **Quality:** independently verified success, partial completion, artifact correctness.
- **Reliability:** failure rate, run-to-run variance, recovery.
- **Efficiency:** wall time, tokens, tool calls, cost, resource use.
- **Robustness:** response to controlled perturbations/faults.
- **Safety:** attempted and successful policy violations, boundary failures.
- **Semantic integrity:** critical constraint preservation and drift across transformations.
- **Verification quality:** verifier precision/recall, false acceptance/rejection, calibration.
- **Reproducibility:** condition completeness and rerun consistency.

Unknown/unavailable is not zero. Keep raw outcomes and per-task evidence.
