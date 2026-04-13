# Phase 14.3 — `TestHarness`: autonomous test execution and verdict routing

**Phase**: 14.3 of the ASI-Build Autonomous Self-Improvement Loop  
**Depends on**: Phase 14.2 `SandboxRunner` (#388)  
**Issue**: [#391](https://github.com/web3guru888/asi-build/issues/391)  
**Show & Tell**: [#392](https://github.com/web3guru888/asi-build/discussions/392) | **Q&A**: [#393](https://github.com/web3guru888/asi-build/discussions/393)

---

## Motivation

`SandboxRunner` can execute a synthesised patch and capture its `stdout`, `stderr`, and return code. But raw return codes are not enough — the synthesis loop needs **structured verdicts**: did the patch _pass_ all tests, _fail_ some, _time out_, or _error_ during execution? `TestHarness` bridges this gap: it interprets execution results, routes verdicts, supports **parallel test suites**, and feeds `pass_rate` statistics upstream to `PatchSelector`.

---

## Design

### `TestVerdictEnum` — enum

```python
class TestVerdictEnum(str, Enum):
    PASS    = "pass"     # all assertions succeeded
    FAIL    = "fail"     # ≥ 1 assertion failed
    TIMEOUT = "timeout"  # execution exceeded timeout_s
    ERROR   = "error"    # unexpected exception / harness crash
```

### `TestSeverity` — enum

```python
class TestSeverity(str, Enum):
    CRITICAL = "critical"   # blocks selection entirely
    HIGH     = "high"       # strongly penalises composite score
    MEDIUM   = "medium"     # moderate penalty
    LOW      = "low"        # informational; does not affect selection
```

### Frozen Dataclasses

```python
@dataclass(frozen=True)
class TestCase:
    test_id:     str              # e.g. "test_audit_record_frozen"
    patch_id:    str              # links to SynthesisResult.patch_id
    command:     tuple[str, ...]  # argv to pass to SandboxRunner
    timeout_s:   float = 30.0
    severity:    TestSeverity = TestSeverity.HIGH
    tags:        tuple[str, ...] = ()

@dataclass(frozen=True)
class TestResult:
    test_id:    str
    patch_id:   str
    verdict:    TestVerdictEnum
    duration_s: float
    stdout:     str
    stderr:     str
    returncode: int

@dataclass(frozen=True)
class HarnessStats:
    total:      int
    passed:     int
    failed:     int
    timed_out:  int
    errored:    int
    pass_rate:  float       # passed / total (0.0 if total == 0)
    duration_s: float       # wall-clock for entire suite

@dataclass(frozen=True)
class HarnessConfig:
    max_parallelism:  int   = 8
    timeout_s:        float = 30.0
    retry_on_error:   bool  = True
    max_retries:      int   = 2
```

---

## `TestHarness` — Protocol

```python
@runtime_checkable
class TestHarness(Protocol):
    async def run(
        self,
        test: TestCase,
        sandbox: SandboxRunner,
    ) -> TestResult: ...

    async def run_suite(
        self,
        tests: Sequence[TestCase],
        sandbox: SandboxRunner,
    ) -> tuple[list[TestResult], HarnessStats]: ...

    def stats(self) -> HarnessStats: ...
    def reset(self) -> None: ...
```

---

## `SubprocessTestHarness` — concrete implementation

### `run()` — verdict mapping

```python
async def run(self, test: TestCase, sandbox: SandboxRunner) -> TestResult:
    start = time.monotonic()
    req = ExecutionRequest(
        patch_id=test.patch_id,
        command=test.command,
        timeout_s=test.timeout_s,
        resource_limits=ResourceLimits(),
    )
    exec_result = await sandbox.run(req)
    duration_s = time.monotonic() - start

    # Verdict mapping:
    # returncode 0   → PASS
    # returncode 1   → FAIL  (pytest convention)
    # returncode 124 → TIMEOUT (GNU timeout convention)
    # anything else  → ERROR
    if exec_result.timed_out:
        verdict = TestVerdictEnum.TIMEOUT
    elif exec_result.returncode == 0:
        verdict = TestVerdictEnum.PASS
    elif exec_result.returncode == 1:
        verdict = TestVerdictEnum.FAIL
    else:
        verdict = TestVerdictEnum.ERROR

    # Retry on ERROR (not on FAIL/TIMEOUT)
    if verdict == TestVerdictEnum.ERROR and self._cfg.retry_on_error:
        for _ in range(self._cfg.max_retries):
            exec_result = await sandbox.run(req)
            if not exec_result.timed_out and exec_result.returncode in (0, 1):
                verdict = (
                    TestVerdictEnum.PASS if exec_result.returncode == 0
                    else TestVerdictEnum.FAIL
                )
                break

    result = TestResult(
        test_id=test.test_id,
        patch_id=test.patch_id,
        verdict=verdict,
        duration_s=duration_s,
        stdout=exec_result.stdout,
        stderr=exec_result.stderr,
        returncode=exec_result.returncode,
    )
    self._update_stats(result)
    return result
```

### `run_suite()` — parallel execution with semaphore

```python
async def run_suite(
    self,
    tests: Sequence[TestCase],
    sandbox: SandboxRunner,
) -> tuple[list[TestResult], HarnessStats]:
    sem = asyncio.Semaphore(self._cfg.max_parallelism)

    async def _bounded(test: TestCase) -> TestResult:
        async with sem:
            try:
                return await self.run(test, sandbox)
            except Exception as exc:
                # Partial-failure coercion — never let one bad test crash the suite
                return TestResult(
                    test_id=test.test_id, patch_id=test.patch_id,
                    verdict=TestVerdictEnum.ERROR, duration_s=0.0,
                    stdout="", stderr=str(exc), returncode=-1,
                )

    results = await asyncio.gather(*(_bounded(t) for t in tests))
    passed = sum(1 for r in results if r.verdict == TestVerdictEnum.PASS)
    stats = HarnessStats(
        total=len(results),
        passed=passed,
        failed=sum(1 for r in results if r.verdict == TestVerdictEnum.FAIL),
        timed_out=sum(1 for r in results if r.verdict == TestVerdictEnum.TIMEOUT),
        errored=sum(1 for r in results if r.verdict == TestVerdictEnum.ERROR),
        pass_rate=passed / len(results) if results else 0.0,
        duration_s=sum(r.duration_s for r in results),
    )
    return list(results), stats
```

---

## `CognitiveCycle._synthesis_step()` integration

```python
async def _synthesis_step(self) -> None:
    harness: TestHarness = self._harness     # injected via constructor
    sandbox: SandboxRunner = self._sandbox

    patch = await self._synthesiser.synthesise(request)
    results, stats = await harness.run_suite(test_cases, sandbox)

    if stats.pass_rate >= self._cfg.pass_rate_threshold:
        selection = await self._selector.select(candidates)
        # apply patch …
    else:
        await self.replan()   # trigger ReplanningEngine

    _HARNESS_PASS_RATE.observe(stats.pass_rate)
```

---

## Data Flow

```
CognitiveCycle
    └─► _synthesis_step()
            │
            ▼
    CodeSynthesiser.synthesise()    ← Phase 14.1
            │  SynthesisResult (patch code)
            ▼
    SubprocessTestHarness.run_suite()
            │  Sequence[TestCase] + SandboxRunner
            ▼
    SandboxRunner.run()             ← Phase 14.2  ×N (parallel, semaphore)
            │  ExecutionResult (returncode / stdout / stderr)
            ▼
    Verdict Mapping (0→PASS / 1→FAIL / 124→TIMEOUT / else→ERROR)
            │  ERROR → retry loop (max_retries)
            ▼
    HarnessStats (pass_rate, counts)
            │
            ▼
    pass_rate ≥ threshold → PatchSelector.select()  ← Phase 14.4
    pass_rate < threshold → CognitiveCycle.replan()  ← Phase 10.5
```

---

## Verdict Mapping Table

| `returncode` | `timed_out` | Verdict | Meaning | Action |
|---|---|---|---|---|
| 0 | False | `PASS` | All assertions OK | Proceed to PatchSelector |
| 1 | False | `FAIL` | ≥1 assertion failed | Lower composite score |
| 124 | True | `TIMEOUT` | Exceeded `timeout_s` | Penalise; no retry |
| other | False | `ERROR` | Harness crash | Retry up to `max_retries` |

---

## Backend Selection Guide

| Scenario | Recommended backend |
|---|---|
| CI / GitHub Actions | `SUBPROCESS` (fast, no Docker daemon) |
| Multi-language sandboxing | `DOCKER` (language-agnostic images) |
| Browser-native / serverless | `WASM` |
| Maximum isolation (Linux only) | `NSJAIL` |

---

## Prometheus Metrics

| Metric | Type | Description |
|---|---|---|
| `asi_harness_runs_total` | Counter | Individual test executions, labelled by `verdict` |
| `asi_harness_run_duration_seconds` | Histogram | Single-test wall-clock time |
| `asi_harness_suite_pass_rate` | Histogram | Suite-level pass_rate (0.0 – 1.0) |
| `asi_harness_retries_total` | Counter | ERROR-triggered retries |
| `asi_harness_suite_duration_seconds` | Histogram | Full suite wall-clock (incl. parallelism) |

### Example PromQL

```promql
# 5-min rolling suite pass-rate
histogram_quantile(0.5, rate(asi_harness_suite_pass_rate_bucket[5m]))

# Error rate over all runs
rate(asi_harness_runs_total{verdict="error"}[5m])
  / rate(asi_harness_runs_total[5m])
```

### Grafana Alert YAML

```yaml
- alert: HarnessHighErrorRate
  expr: |
    rate(asi_harness_runs_total{verdict="error"}[5m])
    / rate(asi_harness_runs_total[5m]) > 0.1
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "TestHarness error rate > 10 % for 2 min"

- alert: HarnessSuitePassRateLow
  expr: |
    histogram_quantile(0.5, rate(asi_harness_suite_pass_rate_bucket[10m])) < 0.7
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Median suite pass rate below 70 % — PatchSelector will frequently replan"
```

---

## mypy Compliance Table

| Symbol | Annotation style |
|---|---|
| `TestVerdictEnum` | `str, Enum` — safe for JSON / GraphQL serialisation |
| `TestSeverity` | `str, Enum` |
| `TestCase`, `TestResult`, `HarnessStats`, `HarnessConfig` | `@dataclass(frozen=True)` — all fields typed |
| `TestHarness` | `Protocol` + `@runtime_checkable` → `isinstance()` safe |
| `SubprocessTestHarness` | structural subtype of `TestHarness` |
| `run()` / `run_suite()` | `async def` — no `Union` of sync/async |

---

## Test Targets (12)

1. `test_test_result_frozen` — mutation raises `FrozenInstanceError`
2. `test_run_pass_verdict` — `returncode=0` → `PASS`
3. `test_run_fail_verdict` — `returncode=1` → `FAIL`
4. `test_run_timeout_verdict` — `timed_out=True` → `TIMEOUT`
5. `test_run_error_retry` — `returncode=2` → `ERROR` → retried → `PASS`
6. `test_run_suite_parallel` — `asyncio.gather` fan-out, semaphore respected
7. `test_run_suite_partial_failure` — single crashing run coerced to `ERROR`, suite continues
8. `test_pass_rate_zero_tests` — empty suite → `pass_rate=0.0`, no division error
9. `test_pass_rate_full_pass` — all tests pass → `pass_rate=1.0`
10. `test_harness_stats_accumulation` — `stats()` counts increase monotonically
11. `test_harness_reset` — `reset()` clears all counters
12. `test_cognitive_cycle_harness_integration` — mock `SandboxRunner.run()` returns `ExecutionResult`; assert `CognitiveCycle._synthesis_step()` calls `harness.run_suite()` and triggers `replan()` when `pass_rate < threshold`

---

## Implementation Order (14 steps)

1. `TestVerdictEnum` + `TestSeverity` enums
2. `TestCase` frozen dataclass
3. `TestResult` frozen dataclass
4. `HarnessStats` frozen dataclass (`pass_rate` computed property)
5. `HarnessConfig` frozen dataclass
6. `TestHarness` Protocol + `@runtime_checkable`
7. `SubprocessTestHarness.__init__()` + `_cfg`, `_stats` state
8. `SubprocessTestHarness.run()` — verdict mapping + retry loop
9. `SubprocessTestHarness._update_stats()` — thread-safe counter
10. `SubprocessTestHarness.run_suite()` — semaphore + `asyncio.gather` + partial-failure coercion
11. `SubprocessTestHarness.stats()` / `reset()`
12. `HarnessFactory` — `HarnessConfig.backend` dispatch
13. 5 Prometheus metrics + registration
14. `CognitiveCycle._synthesis_step()` injection + `pass_rate` threshold + `replan()` trigger

---

## Phase 14 Roadmap

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 14.1 | `CodeSynthesiser` | #385 | 🟡 In Progress |
| 14.2 | `SandboxRunner` | #388 | 🟡 In Progress |
| **14.3** | **`TestHarness`** | **#391** | **🟡 In Progress** |
| 14.4 | `PatchSelector` | #394 | 🟡 In Progress |
| 14.5 | `SynthesisAudit` | #397 | 🟡 In Progress |

---

## Integration with Other Phases

| Upstream | Interface | Direction |
|---|---|---|
| Phase 14.2 `SandboxRunner` | `SandboxRunner.run(ExecutionRequest)` | TestHarness calls Sandbox |
| Phase 14.1 `CodeSynthesiser` | `SynthesisResult.patch_id` | patch_id threaded through TestCase |
| Phase 10.5 `ReplanningEngine` | `CognitiveCycle.replan()` | low pass_rate triggers replan |
| Phase 14.4 `PatchSelector` | `HarnessStats` → composite score | stats flow into selector |
| Phase 14.5 `SynthesisAudit` | `AuditRecord(event_type=TEST_VERDICT, ...)` | verdict written to audit ledger |
