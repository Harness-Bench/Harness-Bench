# Verifier Calibration Pack

Synthetic labeled cases for the file verifier. Each case declares success
criteria, workspace files, and the expected verifier status.

Cases cover exact matches, missing files, wrong content, unknown criteria,
empty criteria, and workspace path escapes. Metrics include false acceptance,
false rejection, accuracy, and unexpected invalid results.

- `pack.json`: calibration cases consumed by `harnessbench calibrate-verifier`.
