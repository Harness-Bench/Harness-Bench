# ADR-0003: N1 Controlled Egress Through a Unix-Socket Proxy

- **Status:** Accepted for v0.1
- **Decision:** Implement N1 as a private network namespace plus an exact host/port allowlist enforced by a host-side HTTP(S) proxy. The sandbox reaches the proxy through a read-only Unix socket and a loopback TCP bridge; direct host-network access is unavailable.
- **Context:** Unprivileged bubblewrap can remove network access but cannot install host firewall rules or create a routed veth with an allowlist. A proxy is the enforceable mechanism available without elevated privileges.
- **Consequences:** N1 supports proxy-aware HTTP requests and CONNECT tunnels to allowlisted host/port endpoints. It does not provide transparent interception, protocol filtering, or TLS inspection; a CONNECT tunnel can carry any protocol to an allowlisted endpoint. Allowed and denied host/port decisions are recorded as trace events without request paths or payloads. N2 still uses host networking without packet-level monitoring.
- **Revisit when:** transparent interception, non-HTTP protocols, or stronger isolation require a privileged network runtime, eBPF enforcement, or a dedicated sandbox service.
