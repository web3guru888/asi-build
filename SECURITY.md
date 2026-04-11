# Security Policy

## Supported Versions

ASI:BUILD is research software in early alpha. We provide security fixes on a best-effort basis:

| Version | Supported |
|---------|-----------|
| `main` (latest) | ✅ Active development |
| `v0.1.0-alpha` | ✅ Best-effort |
| Older | ❌ |

---

## Scope

ASI:BUILD is a local Python research framework with no network-facing server components by default. The main security concerns are:

- **Cypher/query injection** — `graph_intelligence` and `knowledge_graph` modules that accept user-provided queries
- **Dependency vulnerabilities** — transitive dependencies (NumPy, NetworkX, PyTorch, etc.)
- **Deserialization** — pickle-based model loading, particularly in `optimization` and `federated` modules
- **Credential handling** — `configs/` files that accept API keys or cloud credentials
- **MCP server** (`servers/`) — if exposed over the network, the MCP surface should be audited

Out of scope (by design):
- The `archive/` directory — experimental v1 code, not maintained
- Module stubs that do not execute real code

---

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report security issues via one of:

1. **GitHub private vulnerability disclosure**: Use the "Report a vulnerability" button on the [Security tab](https://github.com/web3guru888/asi-build/security/advisories/new)
2. **Email**: Contact the maintainer via GitHub profile

### What to include

- A description of the vulnerability and its impact
- Steps to reproduce (minimal code example preferred)
- Affected module(s) and version(s)
- Any proposed fix, if you have one

### What to expect

- **Acknowledgment** within 72 hours
- **Initial assessment** within 1 week
- **Fix or advisory** within 30 days for confirmed critical issues

We follow responsible disclosure: we will coordinate with you before any public disclosure and give credit in the security advisory.

---

## Known Security Considerations

### Cypher Injection

The `graph_intelligence` module builds Cypher queries from user-provided strings. Always use parameterized queries rather than string interpolation with user input.

### Pickle Deserialization

The `optimization` module can load PyTorch model checkpoints. Only load checkpoints from trusted sources. We plan to migrate to `safetensors` format in v0.3.0.

### Federated Learning

The `federated` module implements Byzantine-tolerant aggregation, but the network transport layer is stub-level in the current alpha. Do not use the federated module in a real networked deployment without a security review.

---

## Dependency Security

We run `pip-audit` as part of CI. To check your local install:

```bash
pip install pip-audit
pip-audit
```

To report a vulnerability in a dependency (not in our code), please report it to the upstream project. We will update the dependency when a fix is available.

---

*Last updated: 2026-04-11*
