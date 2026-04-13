# Phase 14.3 — TestHarness

> **Phase 14 — Autonomous Code Synthesis** · Sub-phase 3 of 5

## Overview

`TestHarness` closes the autonomous self-improvement loop introduced in Phase 14. After `CodeSynthesiser` (14.1) produces code and `SandboxRunner` (14.2) executes it, `TestHarness` runs the generated test suite, collects pass/fail verdicts, and routes the signals back to `CodeSynthesiser.refine()` when the pass rate falls below a configurable threshold.

This creates a fully autonomous cycle inside `CognitiveCycle._synthesis_step()`:

```
synthesise → execute → test → (refine if pass_rate < threshold) → return
```

---

## Architecture

### Data Flow

```
Observation
    │
    ▼
CognitiveCycle._synthesis_step()
    │
    ├─► CodeSynthesiser.synthesise(req, sandbox)
    │       └─► SynthesisResult { code, tests[] }
    │
    ├─► build suite: [TestCase(id, source_code), ...]
    │
    ├─► TestHarness.run_suite(suite, sandbox)
    │       │
    │       ├─► asyncio.Semaphore(max_parallelism)
    │       ├─► asyncio.gather(*_run_one(c) for c in cases)
    │       └─► SubprocessTestHarness.run(case, sandbox)
    │               └─► SandboxRunner.run(ExecutionRequest)
    │                       ├── subprocess backend
    │                       ├── docker backend
    │                       ├── wasm backend
    │                       └── nsjail backend
    │
    ├─► list[TestResult] { verdict, duration_s, stdout, stderr, returncode }
    │
    ├─► pass_rate = PASS count / total count
    │
    └─► if pass_rate < synthesis_pass_threshold:
            CodeSynthesiser.refine(result, failing_tests=failing_verdicts)
                └─► SynthesisResult (refined)
```

---

## Enumerations

```python
class TestVerdictEnum(str, Enum):
    PASS    = "PASS"
    FAIL    = "FAIL"
    ERROR   = "ERROR"
    TIMEOUT = "TIMEOUT"


class TestSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"
```

---

## Frozen Dataclasses

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class TestCase:
    """A single pytest-compatible test case to be executed by TestHarness."""
    id: str
    source_code: str           # pytest-compatible Python source
    timeout_s: float = 30.0
    severity: TestSeverity = TestSeverity.MEDIUM
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class TestResult:
    """Outcome of executing one TestCase."""
    case_id: str
    verdict: TestVerdictEnum
    duration_s: float
    stdout: str
    stderr: str
    returncode: int


@dataclass(frozen=True)
class HarnessStats:
    """Running statistics for a TestHarness instance."""
    total_run: int
    passed: int
    failed: int
    errored: int
    timed_out: int
    mean_duration_s: float
    pass_rate: float           # passed / total_run  (0.0 when total_run == 0)


@dataclass(frozen=True)
class HarnessConfig:
    """Configuration for SubprocessTestHarness."""
    max_parallelism: int     = 8
    default_timeout_s: float = 30.0
    retry_on_error: bool     = True
    max_retries: int         = 2
    collect_coverage: bool   = False
```

---

## `TestHarness` Protocol

```python
@runtime_checkable
class TestHarness(Protocol):
    """Protocol for test execution backends."""

    async def run(
        self, case: TestCase, sandbox: SandboxRunner
    ) -> TestResult:
        """Execute one TestCase via sandbox; apply retry logic on ERROR."""
        ...

    async def run_suite(
        self, cases: Sequence[TestCase], sandbox: SandboxRunner
    ) -> list[TestResult]:
        """Execute all cases concurrently (bounded by max_parallelism).

        Never raises — partial failures are coerced to TestResult(verdict=ERROR).
        Always returns list of len == len(cases).
        """
        ...

    def stats(self) -> HarnessStats:
        """Return cumulative stats since last reset()."""
        ...

    def reset(self) -> None:
        """Zero all stats counters."""
        ...
```

---

## `SubprocessTestHarness` Implementation Skeleton

```python
import asyncio
from typing import Sequence

_RETURNCODE_VERDICT: dict[int, TestVerdictEnum] = {
    0:   TestVerdictEnum.PASS,
    1:   TestVerdictEnum.FAIL,
    124: TestVerdictEnum.TIMEOUT,
}


class SubprocessTestHarness:
    """Concrete TestHarness that delegates execution to a SandboxRunner."""

    def __init__(self, config: HarnessConfig = HarnessConfig()) -> None:
        self._config = config
        self._total_run = 0
        self._passed = 0
        self._failed = 0
        self._errored = 0
        self._timed_out = 0
        self._total_duration = 0.0

    async def run(self, case: TestCase, sandbox: SandboxRunner) -> TestResult:
        """Execute case, retry on ERROR up to config.max_retries."""
        attempt = 0
        t0 = asyncio.get_event_loop().time()

        while True:
            exec_req = ExecutionRequest(
                code=case.source_code,
                timeout_s=case.timeout_s or self._config.default_timeout_s,
            )
            exec_result = await sandbox.run(exec_req)
            duration = asyncio.get_event_loop().time() - t0
            verdict = _RETURNCODE_VERDICT.get(
                exec_result.returncode, TestVerdictEnum.ERROR
            )

            if verdict == TestVerdictEnum.ERROR and self._config.retry_on_error:
                attempt += 1
                if attempt <= self._config.max_retries:
                    continue
            break

        self._update_stats(verdict, duration)
        return TestResult(
            case_id=case.id,
            verdict=verdict,
            duration_s=duration,
            stdout=exec_result.stdout,
            stderr=exec_result.stderr,
            returncode=exec_result.returncode,
        )

    async def run_suite(
        self, cases: Sequence[TestCase], sandbox: SandboxRunner
    ) -> list[TestResult]:
        """Run all cases concurrently, bounded by max_parallelism semaphore."""
        sem = asyncio.Semaphore(self._config.max_parallelism)

        async def _run_one(case: TestCase) -> TestResult:
            async with sem:
                try:
                    return await self.run(case, sandbox)
                except Exception as exc:  # noqa: BLE001
                    self._update_stats(TestVerdictEnum.ERROR, 0.0)
                    return TestResult(
                        case_id=case.id,
                        verdict=TestVerdictEnum.ERROR,
                        duration_s=0.0,
                        stdout="",
                        stderr=str(exc),
                        returncode=-1,
                    )

        return list(await asyncio.gather(*(_run_one(c) for c in cases)))

    def stats(self) -> HarnessStats:
        """Return a frozen snapshot of current stats."""
        total = self._total_run
        return HarnessStats(
            total_run=total,
            passed=self._passed,
            failed=self._failed,
            errored=self._errored,
            timed_out=self._timed_out,
            mean_duration_s=self._total_duration / total if total else 0.0,
            pass_rate=self._passed / total if total else 0.0,
        )

    def reset(self) -> None:
        """Zero all counters."""
        self._total_run = self._passed = self._failed = 0
        self._errored = self._timed_out = 0
        self._total_duration = 0.0

    def _update_stats(self, verdict: TestVerdictEnum, duration: float) -> None:
        self._total_run += 1
        self._total_duration += duration
        if verdict == TestVerdictEnum.PASS:
            self._passed += 1
        elif verdict == TestVerdictEnum.FAIL:
            self._failed += 1
        elif verdict == TestVerdictEnum.TIMEOUT:
            self._timed_out += 1
        else:
            self._errored += 1
        # Prometheus
        _HARNESS_TESTS_RUN.inc()
        _HARNESS_DURATION.observe(duration)
        if verdict == TestVerdictEnum.PASS:
            _HARNESS_PASS.inc()
        elif verdict == TestVerdictEnum.FAIL:
            _HARNESS_FAIL.inc()
        else:
            _HARNESS_ERROR.inc()
```

---

## Factory Function

```python
def make_subprocess_harness(
    config: HarnessConfig | None = None,
) -> TestHarness:
    """Create a SubprocessTestHarness with the given config."""
    return SubprocessTestHarness(config or HarnessConfig())
```

---

## `CognitiveCycle._synthesis_step()` Integration

```python
async def _synthesis_step(self, obs: Observation) -> SynthesisResult:
    """Synthesise code, optionally test it, optionally refine on failure."""
    req = SynthesisRequest(
        prompt=obs.text,
        strategy=self._config.synthesis_strategy,
    )
    result = await self._synthesiser.synthesise(req, sandbox=self._sandbox)

    # Phase 14.3 — run generated tests to validate synthesised code
    if self._harness is not None and result.tests:
        suite = [
            TestCase(id=f"t{i}", source_code=t)
            for i, t in enumerate(result.tests)
        ]
        verdicts = await self._harness.run_suite(suite, self._sandbox)
        pass_rate = (
            sum(1 for v in verdicts if v.verdict == TestVerdictEnum.PASS)
            / len(verdicts)
        )
        if pass_rate < self._config.synthesis_pass_threshold:
            failing = [v for v in verdicts if v.verdict != TestVerdictEnum.PASS]
            result = await self._synthesiser.refine(result, failing_tests=failing)

    return result
```

`_harness` defaults to `None` — when absent, `_synthesis_step()` skips the test loop entirely with zero overhead.

---

## Verdict Mapping Table

| returncode | verdict | pytest meaning | action |
|------------|---------|---------------|--------|
| `0` | `PASS` | all tests passed | none |
| `1` | `FAIL` | ≥1 assertion failed | feed to refine(); do NOT retry |
| `124` | `TIMEOUT` | GNU `timeout` killed process | do NOT retry |
| any other | `ERROR` | crash / syntax error / OOM | retry up to `max_retries` |

---

## Backend Selection Guide

Inherited from `SandboxRunner` — `TestHarness` uses whichever `SandboxRunner` backend is injected:

| Backend | Isolation | Startup cost | Suitable for |
|---------|-----------|-------------|--------------|
| `SUBPROCESS` | OS process | ~5 ms | Unit tests, fast CI |
| `DOCKER` | container | ~500 ms | Integration, untrusted code |
| `WASM` | WASM sandbox | ~20 ms | Multi-language, high parallelism |
| `NSJAIL` | namespace jail | ~30 ms | Production, security-critical |

---

## Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

_HARNESS_TESTS_RUN = Counter(
    "asi_harness_tests_run_total",
    "Total test executions attempted",
)
_HARNESS_PASS = Counter(
    "asi_harness_pass_total",
    "Tests returning PASS verdict",
)
_HARNESS_FAIL = Counter(
    "asi_harness_fail_total",
    "Tests returning FAIL verdict",
)
_HARNESS_ERROR = Counter(
    "asi_harness_error_total",
    "Tests returning ERROR or TIMEOUT verdict",
)
_HARNESS_DURATION = Histogram(
    "asi_harness_duration_seconds",
    "Per-test wall-clock duration",
    buckets=[1, 5, 15, 30, 60, 120],
)
```

### PromQL Reference

| Panel | Query |
|-------|-------|
| Pass rate | `rate(asi_harness_pass_total[5m]) / rate(asi_harness_tests_run_total[5m])` |
| Tests / min | `rate(asi_harness_tests_run_total[1m]) * 60` |
| Duration p95 | `histogram_quantile(0.95, rate(asi_harness_duration_seconds_bucket[5m]))` |
| Error rate | `rate(asi_harness_error_total[5m]) / rate(asi_harness_tests_run_total[5m])` |

### Grafana Alert YAML

```yaml
groups:
  - name: asi_harness
    rules:
      - alert: LowTestPassRate
        expr: |
          rate(asi_harness_pass_total[5m])
          / rate(asi_harness_tests_run_total[5m]) < 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "TestHarness pass rate below 80%"
          description: "Pass rate {{ $value | humanizePercentage }} over last 5 min"

      - alert: HighTestErrorRate
        expr: |
          rate(asi_harness_error_total[5m])
          / rate(asi_harness_tests_run_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "TestHarness error rate above 10%"
```

---

## mypy Compliance Table

| Symbol | Kind | `--strict` status |
|--------|------|-------------------|
| `TestVerdictEnum` | `str, Enum` | ✅ |
| `TestSeverity` | `str, Enum` | ✅ |
| `TestCase` | frozen dataclass | ✅ |
| `TestResult` | frozen dataclass | ✅ |
| `HarnessStats` | frozen dataclass | ✅ |
| `HarnessConfig` | frozen dataclass | ✅ |
| `TestHarness` | `Protocol @runtime_checkable` | ✅ |
| `SubprocessTestHarness` | fully typed | ✅ |
| `make_subprocess_harness` | typed factory | ✅ |

---

## Test Targets (12)

1. `test_run_pass` — passing pytest file returns `PASS` verdict
2. `test_run_fail` — failing assertion returns `FAIL` verdict
3. `test_run_timeout` — exceeds `timeout_s` returns `TIMEOUT` verdict
4. `test_run_error` — syntax error in test source returns `ERROR` verdict
5. `test_retry_on_error` — `ERROR` verdict retries up to `max_retries` times
6. `test_run_suite_parallel` — semaphore limits concurrent executions to `max_parallelism`
7. `test_run_suite_partial_failure` — one `FAIL` does not abort the rest of the suite
8. `test_stats_accumulation` — `HarnessStats` counters update correctly after each `run()`
9. `test_stats_pass_rate` — `pass_rate` computed as `passed / total_run`
10. `test_reset_clears_stats` — `reset()` zeroes all counters
11. `test_integration_synthesiser_loop` — full `synthesise → test → refine` cycle with mock harness
12. `test_mypy_clean` — `mypy --strict` passes on the harness module

---

## Implementation Order (14 steps)

1. Add `TestVerdictEnum` + `TestSeverity` to `asi_build/enums.py`
2. Add `TestCase` frozen dataclass (`id`, `source_code`, `timeout_s`, `severity`, `tags`)
3. Add `TestResult` frozen dataclass (`case_id`, `verdict`, `duration_s`, `stdout`, `stderr`, `returncode`)
4. Add `HarnessStats` frozen dataclass (`total_run`, `passed`, `failed`, `errored`, `timed_out`, `mean_duration_s`, `pass_rate`)
5. Add `HarnessConfig` frozen dataclass
6. Define `TestHarness` Protocol in `asi_build/protocols.py`
7. Implement `SubprocessTestHarness.__init__()` — initialise stats counters
8. Implement `SubprocessTestHarness.run()` — delegate to `SandboxRunner`, map `returncode → verdict`, retry loop
9. Implement `SubprocessTestHarness.run_suite()` — `asyncio.gather` + semaphore + partial-failure coercion
10. Implement `SubprocessTestHarness.stats()` and `reset()`
11. Register 5 Prometheus metrics (`Counter` × 4, `Histogram` × 1)
12. Wire `CognitiveCycle._synthesis_step()` harness injection + `synthesis_pass_threshold` config field
13. Add factory `make_subprocess_harness(config: HarnessConfig) -> TestHarness`
14. Write 12 tests with mock `SandboxRunner.run()` returning `ExecutionResult`

---

## Phase 14 Roadmap

| Sub-phase | Component | Issue | Role | Depends on |
|-----------|-----------|-------|------|------------|
| 14.1 | `CodeSynthesiser` | #385 | Generate code + tests from LLM | Phase 13 WorldModel |
| 14.2 | `SandboxRunner` | #388 | Execute code in isolated backend | `CodeSynthesiser` |
| 14.3 | `TestHarness` | #391 | Run tests, collect verdicts | `SandboxRunner` |
| 14.4 | `PatchSelector` | TBD | Rank + select best synthesis result | `TestHarness` |
| 14.5 | `SynthesisAudit` | TBD | Log + explain synthesis decisions | All of 14.1–14.4 |

### Phase 14 → Phase 13 Integration

| Phase 14 component | Uses from Phase 13 |
|--------------------|-------------------|
| `CodeSynthesiser` | `WorldModel.predict()` for context-conditioned prompts |
| `SandboxRunner` | Independent — pure execution backend |
| `TestHarness` | `SandboxRunner` as execution backend; `CodeSynthesiser.refine()` for feedback |
| `PatchSelector` | `WorldModel.score()` for ranking synthesised patches |
| `SynthesisAudit` | `WorldModelDashboard` for export + observability |
