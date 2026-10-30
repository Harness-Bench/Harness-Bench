# Benchmark Ontology

## Canonical entities

- **Benchmark:** versioned collection and its intended construct/scope.
- **Task pack:** versioned domain-focused subset and task generator/fixtures.
- **Task:** immutable task definition, inputs, initial state, constraints, expected outcomes, and verifier contract.
- **Condition:** model + harness/mechanism manifest + runtime/environment/network + language path + budget.
- **Experiment:** comparison question, condition matrix, sampling/repetition plan, and analysis plan.
- **Run:** one concrete execution attempt under one frozen condition.
- **Evidence:** logs, tool events, state snapshots, output artifacts, and provenance.
- **Verification:** versioned assessment of evidence against criteria; includes verifier status.
- **Analysis:** deterministic transformation of stored runs/verification into metrics.
- **Report:** versioned presentation of analysis, uncertainty, exclusions, and limitations.

## Orthogonal task descriptors

Each task may declare multiple evaluation domains (D1–D13), one task level (B0–B4), environment profile (E0–E3), network profile (N0–N2), applicable language dimensions, security/risk level, expected duration/budget, and required verifier capabilities. These labels describe different properties and must not be merged into one level.

## Task contract minimum

A task definition should specify:
- stable ID and semantic version;
- domain tags and intended construct;
- prompt/input and language/transformation metadata;
- initial state/environment fixture and reset rule;
- allowed tools, permissions, network profile, and budgets;
- explicit success criteria and partial-credit policy, if any;
- required evidence and verifier interface;
- expected failure classes and critical invariants;
- provenance, license, creation/review date, and split (public/dev/held-out);
- known ambiguity, limitations, and difficulty calibration status.

## Scoring discipline

Separate task success from policy compliance, infrastructure health, and verifier health. Keep raw task-level outcomes. Unknown/not-applicable/invalid/unverified are distinct states. Composite scores are deferred until weighting and sensitivity can be justified.
