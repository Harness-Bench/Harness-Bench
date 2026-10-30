# Runtime

Owns environment setup/reset, isolation, resource limits, network enforcement, timeout, and cleanup.

- `isolated.py`: bubblewrap-backed runtime with resource limits, N0/N1/N2 network policies, initial-state reset, and trace capture.
- `network.py`: N1 exact host/port allowlist proxy, Unix-socket bridge, and egress decision events.
