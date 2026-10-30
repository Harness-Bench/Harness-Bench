# Validity, Contamination & Difficulty

## Threats to validity

- **Construct validity:** task measures a different skill than its label claims.
- **Internal validity:** model, harness, budget, tools, or environment differ across compared conditions.
- **Verifier validity:** scorer shares the same blind spots or incorrectly accepts plausible-looking output.
- **External validity:** benchmark results do not transfer to real workflows or unrepresented languages/domains.
- **Contamination:** model may have seen public tasks or close variants during training.
- **Sampling bias:** task set overweights easy, English, or one ecosystem cases.

## Controls

Version all task/verifier/environment assets; preserve provenance; maintain public development and held-out sets where feasible; use controlled paraphrases/variants and periodic refresh; disclose contamination checks and residual uncertainty; use human adjudication for critical semantic cases; calibrate difficulty empirically; include negative, ambiguous, insufficient-context, and adversarial cases; and report results by task family/language/model class rather than only aggregate.

No procedure can prove that a task is uncontaminated. State what was checked, what was not checked, and confidence limits.
