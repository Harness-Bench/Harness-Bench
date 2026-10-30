# ADR-0001: Start with a Python Modular Monolith

- **Status:** Accepted for v0.1
- **Decision:** Start with one Python application divided into explicit modules and contracts.
- **Context:** The first risk is validating evaluation semantics and reproducibility, not scaling service deployment.
- **Consequences:** Lower operational complexity and simpler local execution; module boundaries must remain clean to preserve future extraction options.
- **Revisit when:** measured concurrency, isolation, deployment, or team ownership requirements justify separate services.
