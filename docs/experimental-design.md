# Experimental Design

## Experiment types

1. **Matched comparison:** same task versions, initial states, budgets, tools, environment, network, and scoring rules.
2. **Mechanism ablation:** toggle one declared mechanism while holding material conditions fixed.
3. **Interaction:** test combinations that may reinforce or interfere.
4. **Model × harness interaction:** estimate whether effects differ by model capability class, including small/older models.
5. **Environment transfer:** compare controlled and workflow-like settings.
6. **Language-path experiment:** compare equivalent tasks across language and transformation paths.
7. **Verifier validation:** measure evaluator errors against adjudicated/known cases, including adversarial and multilingual cases.

## Fairness and attribution

Record task/version, model/revision/settings, harness/revision/manifest, tool permissions, budgets, environment image/dependencies/resources, network policy, language axes, verifier/scorer versions, and seed where applicable. Automatically detect mismatches. Label unmatched comparisons; do not make causal claims from them. If an intervention changes several factors, call it a bundled intervention.

## Paired design and repetitions

Pair conditions by task and initial state where possible. Repeat stochastic runs; report sample sizes, uncertainty, and task-level paired outcomes. Repeated runs on one task are not independent tasks. Keep exclusions and reasons visible; do not drop failed runs silently.

## Multilingual semantic-integrity conditions

For semantically equivalent source tasks, compare at least where applicable:
- A: direct task in its original language;
- B: translate then execute;
- C: translate + independent semantic verification;
- D: translate + verification + correction/recovery;
- E: full harness path, including summarization/compression/handoffs if enabled.

Use a language-independent canonical constraint representation where practical. Score meaning, not lexical similarity. Include negation, quantifiers, conditions, exceptions, units/numbers, permissions, uncertainty, references, contradictions, and safety-critical boundaries. Verify the verifier itself. Report language pair, direction, translation method, and transformation chain.

## Metrics and scoring

Keep task outcomes, semantic invariants, evidence, and metric definitions. Avoid a universal score in v0.1. If a composite is later introduced, publish weights, normalization, missing-data rules, and sensitivity analysis. Report critical constraint inversion separately from ordinary errors.

## Validity controls

- Split public development examples from held-out/private evaluation where feasible.
- Version task, test, verifier, and environment artifacts; record provenance and publication date.
- Use paraphrases, controlled variants, and contamination checks; disclose that contamination cannot be ruled out perfectly.
- Calibrate task difficulty empirically; do not infer it only from author labels or model leaderboard scores.
- Include positive, negative, ambiguous, insufficient-context, and adversarial examples.
- Include infrastructure-failure controls so setup/runtime failures are not mis-scored as model failures.

## Minimum report

Include benchmark/task pack versions, model/harness/runtime manifests, environment/network/language conditions, budgets, repetitions, raw success/failure counts, independent verification results, uncertainty, invalid/excluded runs, semantic-integrity metrics when relevant, provenance, and known limitations.
