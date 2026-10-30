# Local Runs

Local experiment outputs are runtime data, not source. Keep large or sensitive outputs out of version control unless a fixture is intentionally curated.

Layout per run:

- `runs/<run_id>/run.json`: versioned run manifest.
- `runs/<run_id>/artifacts/`: evidence and output files referenced by the manifest.
