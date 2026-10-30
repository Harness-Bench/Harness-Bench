# Multilingual & Semantic Integrity

## Status and purpose

This is a first-class evaluation domain, not a metadata tag and not a translation-only subtest. It measures whether a model/harness preserves and correctly uses meaning across languages, representations, context transformations, and agent boundaries. It is especially important when testing ~1B and older models, where a harness may preserve capability, amplify it, or introduce semantic damage.

## Subdomains

- **M1 Cross-lingual understanding:** interpret intent and constraints across source/target languages.
- **M2 Semantic preservation:** preserve propositions and critical constraints through translation, summary, compression, planning, and handoff.
- **M3 Transformation verification:** detect meaning changes introduced by a translator, summarizer, compiler, or agent.
- **M4 Mixed-language reasoning:** reason over multilingual prompts, code/comments/docs/logs, and language switches.
- **M5 Language-specific competence:** account for language-specific morphology, pragmatics, ambiguity, honorifics/register where relevant, and tokenization effects without confusing this with task difficulty.
- **M6 Cross-lingual conflict resolution:** identify disagreement between source and transformed text; preserve uncertainty and request clarification when evidence is insufficient.

## Independent language dimensions

1. Natural-language source and output languages.
2. Programming language(s).
3. Artifact/interface language(s): code comments, documentation, logs, CLI output, identifiers.
4. Language mixing and directionality.
5. Transformation chain and number of hops.
6. Model/harness translation route and whether a verifier sees source, translation, or both.

## Semantic invariants

Represent expected meaning as explicit constraints whenever feasible: negation, actor/subject, action, object, quantifiers, preconditions, exceptions, temporal order, units/numbers, permissions, safety boundaries, uncertainty/modality, reference resolution, and contradiction status. Use structured gold labels plus human adjudication for ambiguous cases. String similarity is not a correctness metric.

Example: source says “non-admin users must not delete records.” A translation changing this to “admin users must not delete records” is a critical actor/permission inversion even if the sentence is fluent.

## Transformation-path conditions

- **A Direct:** model receives the original task.
- **B Transform:** task is translated/summarized/compressed before execution.
- **C Transform + verify:** independent verifier compares transformed content with source invariants.
- **D Transform + verify + recovery:** detected drift triggers correction or re-planning.
- **E Full path:** include enabled context compiler, decomposition, multi-agent handoffs, tool outputs, and final integration.

Use paired semantically equivalent tasks across language pairs. Do not assume all language versions have equal difficulty; calibrate and report this separately.

## Required measures

- End-task correctness and artifact quality.
- Critical constraint preservation rate.
- Critical semantic inversion rate (report separately; never bury in average score).
- Drift detection precision/recall and false-alarm rate.
- Recovery success after detected drift.
- Uncertainty/clarification calibration.
- Added latency, tokens, tool calls, and cost.
- Verifier performance against independently adjudicated cases.

Report each language pair/direction and transformation path; do not aggregate away weak languages. Distinguish source model error, transformation error, verifier error, and downstream execution error where evidence permits.

## Minimum test categories

Negation; actor/reference swap; numbers/units; quantifiers; conditions/exceptions; permission/authority; temporal ordering; uncertainty/modality; pronoun/coreference; ambiguity; contradiction; mixed-language code/docs/logs; multi-hop summary/compression; handoff between agents; insufficient context requiring clarification.

## Validity notes

Machine-generated translations are not gold truth. Use human-reviewed references or explicit semantic constraints for critical cases. The verifier must not be assumed correct simply because it is a separate model. Record whether verifier and evaluated model share a model family or translation system. Preserve original, transformed, verified, corrected, and final artifacts for audit.
