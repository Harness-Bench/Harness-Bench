# Runtime

Owns environment setup/reset, isolation, resource limits, network enforcement, timeout, and cleanup.

- `isolated.py`: bubblewrap-backed runtime with resource limits, N0 offline and N2 host-network policies, initial-state reset, and trace capture.
