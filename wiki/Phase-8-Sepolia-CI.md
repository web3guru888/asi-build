# Phase 8.5 — Sepolia CI: contract redeployment, bridge health, and on-chain fuzz testing

Phase 8.5 closes out Phase 8 by wiring the three deployed Sepolia testnet contracts into a live CI/CD pipeline.  It extends the Docker/Helm infrastructure from Phase 8.4 with on-chain integration tests, automated contract redeployment, bridge health monitoring, and Prometheus alerting.

---

## Motivation

| Gap | Solution |
|-----|---------|
| Contract addresses hard-coded | `config/sepolia.json` written by CI on every tagged release |
| No on-chain regression tests | Forge fuzz tests (`--fuzz-runs 1000`) run in every PR |
| Bridge health invisible to ops | `SepoliaBridgeUnreachable` Prometheus alert + scrape job |
| Manual redeploy on upgrade | `sepolia.yml` GitHub Actions workflow deploys on `v*` tag push |
| No smoke test post-deploy | `bridge_smoke_test.py` deposits 1 bASI and verifies event |

---

## Deployed contract addresses (Sepolia testnet)

| Contract | Address |
|----------|---------|
| RingsBridge | `0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca` |
| Groth16Verifier | `0x9186fc5e27c15aEDbA2512687F2eF2E5aC7C0e59` |
| BridgedToken bASI | `0x257dDA1fa34eb847060EcB743E808B65099FB497` |
| Chain ID | 11155111 (Sepolia) |

---

## Architecture overview

```
GitHub Actions
│
├── fuzz-contracts  (every PR)
│   └── forge test --fuzz-runs 1000 -vvv
│
└── v* tag push
    ├── deploy-contracts
    │   ├── forge script Deploy.s.sol --broadcast --verify
    │   └── extract_addresses.py → config/sepolia.json
    ├── bridge-health  (needs deploy-contracts)
    │   └── bridge_smoke_test.py
    │       ├── approve + deposit 1 bASI
    │       ├── assert Deposit event
    │       └── withdraw + assert Withdrawal event
    └── update-config  (commits sepolia.json back to repo)

Runtime (docker-compose / Helm)
│
├── sepolia-exporter  (port 9101)
│   ├── Counter: sepolia_bridge_deposits_total
│   ├── Counter: sepolia_bridge_withdrawals_total
│   ├── Gauge:   sepolia_bridge_balance_basi
│   ├── Gauge:   sepolia_block_height
│   └── Histogram: sepolia_exporter_scrape_duration_seconds
│
├── prometheus  →  scrapes via ServiceMonitor
│   └── alert: SepoliaBridgeUnreachable (absent > 5 min)
│
└── ExplainAPI  (Phase 8.3)
    └── GET /health/sepolia → 200 ok / 503 unreachable
```

---

## Deliverables

### 1. `.github/workflows/sepolia.yml` — 3-job CI workflow

```yaml
name: Sepolia CI
on:
  push:
    tags: ["v*"]
  workflow_dispatch:
  pull_request:
    paths: ["contracts/**"]

jobs:
  fuzz-contracts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: foundry-rs/foundry-toolchain@v1
      - name: Fuzz test contracts
        run: forge test --fuzz-runs 1000 -vvv

  deploy-contracts:
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: foundry-rs/foundry-toolchain@v1
      - name: Deploy contracts
        env:
          SEPOLIA_RPC:  ${{ secrets.SEPOLIA_RPC }}
          DEPLOYER_PK:  ${{ secrets.DEPLOYER_PK }}
        run: |
          cd contracts/
          forge script script/Deploy.s.sol \
            --rpc-url $SEPOLIA_RPC \
            --private-key $DEPLOYER_PK \
            --broadcast --verify
          python scripts/extract_addresses.py deployments/sepolia/ \
            > ../config/sepolia.json
      - uses: actions/upload-artifact@v4
        with:
          name: sepolia-config
          path: config/sepolia.json

  bridge-health:
    needs: deploy-contracts
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { name: sepolia-config, path: config/ }
      - name: Smoke test bridge
        env:
          SEPOLIA_RPC: ${{ secrets.SEPOLIA_RPC }}
        run: |
          python scripts/bridge_smoke_test.py \
            --rpc $SEPOLIA_RPC \
            --config config/sepolia.json
```

---

### 2. `scripts/extract_addresses.py`

Reads Foundry broadcast JSONs and writes `config/sepolia.json`:

```python
import json, sys
from pathlib import Path
from datetime import datetime, timezone

def extract_addresses(broadcast_dir: str) -> dict:
    bd = Path(broadcast_dir)
    if not bd.exists():
        raise FileNotFoundError(f"Broadcast dir not found: {broadcast_dir}")

    result: dict[str, str] = {}
    for run_file in bd.glob("*.json"):
        data = json.loads(run_file.read_text())
        for tx in data.get("transactions", []):
            name = tx.get("contractName")
            addr = tx.get("contractAddress")
            if name and addr:
                result[name] = addr

    # Merge with existing config to preserve unchanged addresses
    config_path = Path("config/sepolia.json")
    existing = json.loads(config_path.read_text()) if config_path.exists() else {}

    merged = {
        **existing,
        "rings_bridge":     result.get("RingsBridge",     existing.get("rings_bridge", "")),
        "groth16_verifier": result.get("Groth16Verifier", existing.get("groth16_verifier", "")),
        "bridged_token":    result.get("BridgedToken",    existing.get("bridged_token", "")),
        "chain_id":         11155111,
        "deployed_at":      datetime.now(timezone.utc).isoformat(),
    }
    return merged

if __name__ == "__main__":
    print(json.dumps(extract_addresses(sys.argv[1]), indent=2))
```

---

### 3. `scripts/bridge_smoke_test.py`

```python
from web3 import Web3
import json, sys, time, random, argparse

def run_smoke_test(rpc_url: str, config_path: str) -> None:
    cfg = json.loads(open(config_path).read())
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
    assert w3.is_connected(), "RPC unreachable"

    bridge = w3.eth.contract(address=cfg["rings_bridge"],  abi=BRIDGE_ABI)
    token  = w3.eth.contract(address=cfg["bridged_token"], abi=ERC20_ABI)

    # Approve + Deposit
    token.functions.approve(cfg["rings_bridge"], 1).transact({"from": TEST_ACCOUNT})
    tx      = bridge.functions.deposit(1, DUMMY_PROOF).transact({"from": TEST_ACCOUNT})
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    logs    = bridge.events.Deposit().process_receipt(receipt)
    assert len(logs) == 1 and logs[0]["args"]["amount"] == 1

    # Withdraw
    tx2      = bridge.functions.withdraw(DUMMY_NULLIFIER).transact({"from": TEST_ACCOUNT})
    receipt2 = w3.eth.wait_for_transaction_receipt(tx2)
    logs2    = bridge.events.Withdrawal().process_receipt(receipt2)
    assert len(logs2) == 1

    print(json.dumps({"status": "ok", "block": receipt["blockNumber"]}))

def _with_retry(fn, retries: int = 5):
    for attempt in range(retries):
        try:
            return fn()
        except Exception:
            time.sleep(2 ** attempt + random.uniform(0, 1))
    raise RuntimeError("RPC unreachable after retries")
```

---

### 4. `config/sepolia-exporter.py`

```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from web3 import Web3
import time, json
from pathlib import Path

DEPOSITS  = Counter("sepolia_bridge_deposits_total",          "Cumulative deposits")
WITHDRAWS = Counter("sepolia_bridge_withdrawals_total",        "Cumulative withdrawals")
BALANCE   = Gauge(  "sepolia_bridge_balance_basi",            "bASI balance of bridge (wei)")
BLOCK     = Gauge(  "sepolia_block_height",                   "Latest Sepolia block")
DURATION  = Histogram("sepolia_exporter_scrape_duration_seconds", "Scrape latency")

def scrape(w3: Web3, bridge, token, last_block: int) -> int:
    t0 = time.monotonic()
    try:
        current = w3.eth.block_number
        BLOCK.set(current)
        BALANCE.set(token.functions.balanceOf(bridge.address).call() / 1e18)
        for _ in bridge.events.Deposit().get_logs(fromBlock=last_block):
            DEPOSITS.inc()
        for _ in bridge.events.Withdrawal().get_logs(fromBlock=last_block):
            WITHDRAWS.inc()
        return current
    finally:
        DURATION.observe(time.monotonic() - t0)

if __name__ == "__main__":
    cfg = json.loads(Path("config/sepolia.json").read_text())
    w3  = Web3(Web3.HTTPProvider(cfg["rpc_url"]))
    start_http_server(9101)
    last = w3.eth.block_number
    while True:
        last = scrape(w3, bridge_contract, token_contract, last)
        time.sleep(15)
```

---

### 5. `config/alerts/sepolia.yml` — Prometheus alert rules

```yaml
groups:
  - name: sepolia
    rules:
      - alert: SepoliaBridgeUnreachable
        expr: absent(up{job="sepolia_bridge"} == 1)
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Sepolia RingsBridge not reachable"
          description: >
            No successful scrape from the sepolia_bridge Prometheus job for
            more than 5 minutes.  Check network connectivity and exporter logs.

      - alert: SepoliaBridgeDepositStalled
        expr: increase(sepolia_bridge_deposits_total[30m]) == 0
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "No Sepolia bridge deposits in 30 min"
          description: >
            No Deposit events recorded on RingsBridge for 30 min.
            May indicate low activity (testnet) or a contract issue.
```

---

### 6. `config/sepolia.json` — pinned addresses

```json
{
  "rings_bridge":     "0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca",
  "groth16_verifier": "0x9186fc5e27c15aEDbA2512687F2eF2E5aC7C0e59",
  "bridged_token":    "0x257dDA1fa34eb847060EcB743E808B65099FB497",
  "chain_id":         11155111,
  "deployed_at":      "2026-04-12T00:00:00Z"
}
```

Committed to the repo; updated automatically on each `v*` release by the `deploy-contracts` job.

---

## ExplainAPI integration (Phase 8.3)

New endpoint added to ExplainAPI:

```
GET /health/sepolia
Authorization: X-API-Key <key>

200 OK:
{
  "rings_bridge":     "0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca",
  "groth16_verifier": "0x9186fc5e27c15aEDbA2512687F2eF2E5aC7C0e59",
  "bridged_token":    "0x257dDA1fa34eb847060EcB743E808B65099FB497",
  "block_height":     7823400,
  "status":           "ok"
}

503 Service Unavailable:
{ "status": "unreachable", "last_seen_block": 7823395 }
```

`ExplainAPI` reads `config/sepolia.json` at startup and injects a `SepoliaHealthChecker` into the FastAPI dependency graph.

---

## Prometheus metrics (5)

| Metric | Type | Description |
|--------|------|-------------|
| `sepolia_bridge_deposits_total` | Counter | Cumulative `Deposit` events on RingsBridge |
| `sepolia_bridge_withdrawals_total` | Counter | Cumulative `Withdrawal` events |
| `sepolia_bridge_balance_basi` | Gauge | bASI balance of RingsBridge (in ETH units) |
| `sepolia_block_height` | Gauge | Latest Sepolia block number |
| `sepolia_exporter_scrape_duration_seconds` | Histogram | Scrape latency per poll cycle |

### PromQL examples

```promql
# Deposit rate (per 5 min)
rate(sepolia_bridge_deposits_total[5m])

# bASI balance held in bridge
sepolia_bridge_balance_basi

# Scrape latency p99
histogram_quantile(0.99,
  rate(sepolia_exporter_scrape_duration_seconds_bucket[5m]))

# Is exporter up?
up{job="sepolia_bridge"}
```

---

## Test targets (12)

| # | Target | Method |
|---|--------|--------|
| 1 | `extract_addresses` reads broadcast JSON correctly | unit |
| 2 | `extract_addresses` raises `FileNotFoundError` on missing dir | unit |
| 3 | `bridge_smoke_test` deposit flow (mock web3) | unit |
| 4 | `bridge_smoke_test` withdrawal flow (mock web3) | unit |
| 5 | `bridge_smoke_test` exits 1 on missing Deposit event | unit |
| 6 | `SepoliaBridgeExporter.collect()` returns all 5 metrics | unit |
| 7 | Exporter handles RPC timeout gracefully (no crash) | unit |
| 8 | `deposits_total` increments on new Deposit event | unit |
| 9 | `ExplainAPI /health/sepolia` returns 200 when RPC ok | integration |
| 10 | `ExplainAPI /health/sepolia` returns 503 when RPC unreachable | integration |
| 11 | Forge unit: `RingsBridge.deposit` emits correct event | forge |
| 12 | Forge fuzz: `RingsBridge.withdraw` (1000 runs) never panics | forge |

---

## Implementation order (10 steps)

1. Commit `config/sepolia.json` with pinned addresses
2. `scripts/extract_addresses.py` + tests 1–2
3. `scripts/bridge_smoke_test.py` + tests 3–5
4. `config/sepolia-exporter.py` + tests 6–8
5. `config/alerts/sepolia.yml` — alert rules
6. Update `docker-compose.yml` — add `sepolia-exporter` service (port 9101)
7. Update `charts/asi-build/` — add exporter Deployment + ServiceMonitor
8. `.github/workflows/sepolia.yml` — 3-job CI workflow
9. ExplainAPI `/health/sepolia` endpoint + integration tests 9–10
10. Forge test suite updates + tests 11–12

---

## Phase 8 roadmap

| Sub-phase | Focus | Issue | Status |
|-----------|-------|-------|--------|
| 8.1 | DecisionTracer (causal attribution) | #276 | ✅ spec complete |
| 8.2 | CausalGraph (DAG + critical path) | #280 | ✅ spec complete |
| 8.3 | ExplainAPI (HTTP introspection) | #283 | ✅ spec complete |
| 8.4 | Docker/Helm (containerisation) | #291 | ✅ spec complete |
| **8.5** | **Sepolia CI (on-chain integration)** | **#295** | 🟡 in progress |

---

## Related

- **Issue**: [#295 — Phase 8.5 — Sepolia CI](https://github.com/web3guru888/asi-build/issues/295)
- **Discussion** (Show & Tell): [#296](https://github.com/web3guru888/asi-build/discussions/296)
- **Discussion** (Q&A): [#297](https://github.com/web3guru888/asi-build/discussions/297)
- **Prev phase**: [Phase-8-Docker-Helm](Phase-8-Docker-Helm)
- **Phase 8 tracker**: [Phase 8 roadmap](https://github.com/web3guru888/asi-build/issues/109)
