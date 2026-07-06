# ASI:BUILD — Tooling & Skills Audit (2026-07-06)

Continuous-improvement pass #1 (Beast Atlas pattern). Auditor: beast-engineer.
Scope: `src/asi_build/` + `tests/` on `main` (working baseline commit `2d40c52`).

---

## 1. Baseline (Phase 0)

| Metric | Before | After this pass |
|---|---|---|
| Test collection | 3,610 collected / **26 import errors** (missing `pycryptodome`, `web3`, `aiosqlite`; `did_to_bytes32` missing from source) | 5,183 collected / **0 errors** |
| Test results (local, module-chunked) | 5,008 passed / 23 failed / 104 skipped | **5,072+ passed / 0 failed** / ~104 env-gated skips |
| CI status | **Red since 2026-04-15** (every job) | Green target — deps fixed, format restored, event-loop pollution fixed |
| black | 104 files non-compliant | clean |
| isort | non-compliant | clean |
| ruff (all E/F rules) | 2,538 findings, **36× F821 undefined-name (real bugs)** | F821: **0**; 2,502 remaining (mostly F401 unused-import 1,580, F405 star-imports 416) |
| bandit | 45 HIGH / 67 MEDIUM / 707 LOW | 40 HIGH (35× B324 MD5-annotation TODO, 5× B413 false positive) |
| Coverage | unknown (CI never got past collection) | **43%** (84,961 stmts / 48,505 missed — CI py3.11) |
| CI test job (py3.11, single process) | red | **5,078 passed / 0 failed / 108 skipped** in 15m50s |

Skips are environment-gated: snarkjs/circom binaries (23), Sepolia keys + funded
account (48), torch (structural modules), Memgraph/Neo4j live instances.

### Bugs found & fixed in this pass
1. **`contract_client.py` had drifted from `RingsBridge.sol`** — string vs `bytes32`
   ringsDID, missing `withdraw` parameter, wrong function names
   (`pause`/`setRateLimit`/`remainingDailyLimit` don't exist on-chain), stale
   event/struct shapes. Client calldata would not match the deployed contract. (`cf6f825`)
2. **`AuditLogger` never writes when any foreign handler is attached** to its
   process-global named loggers; re-init with a new `log_dir` silently kept the old
   one; file-handle leak. #1282 (`8eae108`)
3. **41 CI-only failures**: sync→async `_run` helpers used
   `asyncio.get_event_loop().run_until_complete()`, broken after
   `test_beacon_client` closes the main-thread loop. (`ba8ae04`)
4. **9 latent NameErrors** (missing imports / undefined vars) incl. 🟢 modules:
   `bci` SSVEP detector crashed on every `detect()` call (`import time` missing),
   `consciousness/predictive_processing` (`Set`), `integrations/agents/main`
   (`sys`), `blockchain/contract_manager` (`asyncio`), etc. (`78174a2`)
5. **Security**: `shell=True` wget invocation (command injection via dataset URL) and
   zip-slip/tar-slip in `optimization/scripts` downloaders. (`1317bf3`)
6. **Stale tests** never updated alongside features (#1242 `chain_id`, b9adfa3
   deployed-chain registry, evolved withdraw signature). #1283 (`8eae108`)

### Open issues filed
- **#1284** — DID→bytes32 divergence: `bridge_cli.py` uses sha256, canonical
  helper/Forge tests use keccak256. Needs a protocol decision + CLI refactor.

---

## 2. Tooling inventory & gaps (Phase 1)

### Present & working
| Tool | Status |
|---|---|
| pytest + pytest-asyncio (`asyncio_mode=auto`) | ✅ 5.1k tests |
| coverage / pytest-cov | ✅ configured in pyproject |
| black (line 100, py311) + isort (black profile) | ✅ enforced in CI, tree now compliant |
| mypy | ⚠️ configured, non-blocking in CI (huge untyped surface) |
| GitHub Actions CI (lint / test 3.10–3.13 / security) | ✅ existed but red since April — now repaired & extended |
| bandit | ✅ in CI (non-blocking) |
| Makefile targets | ✅ install/test/lint/format/clean |

### Gaps → recommendations (Python-native preferred)
| Gap | Recommendation | Status |
|---|---|---|
| Fast linter catching real bugs (undefined names, syntax) | **ruff** — blocking `E9,F63,F7,F82` gate; full report non-blocking | ✅ **installed + in CI** (`b2c2a65`) |
| Dependency CVE audit | **pip-audit** (safety invocation was broken: `--file pyproject.toml` is not a supported input — the step always no-opped) | ✅ **in CI**, non-blocking |
| Dead-import cleanup | `ruff --select F401 --fix` (1,580 findings) — mechanical, big diff; do as dedicated commit | 📋 proposed |
| Star-import hygiene | 416× F405 + 18× F403 — mostly `archive`-style re-export patterns in `src`; needs per-module review | 📋 proposed |
| Property-based testing / fuzzing | **hypothesis** for `homomorphic` (known correctness issues per CLAUDE.md), `knowledge_graph` A*, codec/SSZ round-trips | 📋 proposed next pass |
| Benchmark harness | **pytest-benchmark** for `homomorphic`, `graph_intelligence`, `consciousness` hot paths; store JSON baselines in CI artifacts | 📋 proposed next pass |
| Profiling | py-spy (sampling, no code changes) when perf work starts | 📋 on demand |
| Test-order robustness | `pytest-randomly` — would have caught the event-loop and AuditLogger pollution years earlier. Add once suite proven stable | 📋 proposed |
| Timeout guard | pytest-timeout — some ZK tests run 8+ min; a hang currently stalls CI to the 6h limit | 📋 proposed |
| Type coverage | Incremental mypy strictness per 🟢 module (start: `safety`, `knowledge_graph`) | 📋 long-term |
| Solidity toolchain | Foundry exists (`contracts/test/RingsBridge.t.sol`) but no CI job; add forge-test job with foundry-toolchain action | 📋 proposed |

### Notes for future passes
- **Memory**: full suite in a single pytest process peaks >1 GB (OOM-killed in a
  1 GB container at ~75%). GitHub runners (7 GB) are fine. Locally: chunk per module.
- `pyproject.toml` `[project.urls] Repository` points at gitlab.com/asi-build — stale.
- `pages-build-deployment` workflow fails on every push (Pages misconfiguration,
  independent of CI).
- Codecov upload rejected: `Token required — not valid tokenless upload`. Needs a
  `CODECOV_TOKEN` repo secret (admin-only; contributor token can't set it).
- `archive/` intentionally untouched per CLAUDE.md.
