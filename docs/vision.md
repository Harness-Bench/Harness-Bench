# Vision

## Mission

HarnessBench is a local-first, reproducible benchmark for separating **base-model capability**, **harness mechanism effects**, and **execution-environment effects**. It combines end-to-end system comparison with mechanism-level evaluation.

## Questions it must answer

1. Which system performs better under matched conditions, on which task families, and with what uncertainty?
2. Which mechanism changes the outcome, and is the result causal or only a bundled comparison?
3. Does the effect vary by model capability, language, task, environment, or network policy?
4. Does the harness preserve or amplify the useful capability of small (including ~1B) and older models, and where does it fail?
5. Are answers and artifacts semantically faithful through translation, summarization, context compression, decomposition, and agent handoffs?
6. Can results be independently verified, audited, and reproduced?

## Scope

v0.1 is a **generic evaluation foundation**, initially demonstrated on coding and cybersecurity. The core must not assume English, Python, a single provider, or a single harness architecture. It is local-first and starts as a Python modular monolith with adapters and versioned task packs.

## Principles

- Comparison and mechanism evaluation are designed together.
- Model, harness, task, environment, network, language, and verifier are separately recorded.
- Independent evidence-based verification; never trust agent self-report as ground truth.
- Preserve unknowns, uncertainty, contradictions, and provenance rather than silently normalizing them.
- No universal scalar score that hides trade-offs.
- Validate the evaluator and verifier, not only the system under test.
- Build small, reproducible vertical slices before broad coverage.

## Non-goals for v0.1

- Exhaustive coverage of all models, harnesses, languages, and domains.
- Claiming benchmark scores prove general intelligence or real-world safety.
- A proprietary inference engine, distributed execution, or adaptive benchmark generation.
- Treating translation as a language tag or assuming string similarity proves semantic preservation.
