# Phase 14.2 — SandboxRunner

> **Status:** 🟡 Spec'd | **Issue:** [#388](https://github.com/web3guru888/asi-build/issues/388) | **Phase:** 14 — Code Synthesis Engine

---

## Overview

`SandboxRunner` safely executes synthesised code in an isolated environment, capturing `stdout`, `stderr`, exit codes, and timing data. It enforces configurable timeouts and resource limits, and integrates with `CodeSynthesiser` so that synthesised patches can be automatically validated before entering the planning pipeline.

---

## `ExecutionBackend` Enum

```python
from enum import Enum, auto

class ExecutionBackend(Enum):
    SUBPROCESS = auto()   # asyncio.create_subprocess_exec (default, zero-deps)
    DOCKER     = auto()   # docker SDK — full container isolation
    WASM       = auto()   # Wasmtime/Wasmer — language-agnostic sandboxing
    NSJAIL     = auto()   # nsjail binary — Linux namespace + seccomp
```

---

## Frozen Dataclasses

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class ResourceLimits:
    """Per-execution resource ceiling."""
    max_memory_mb: int  = 256    # RSS ceiling (MB)
    max_cpu_s: float    = 10.0   # CPU-time ceiling (seconds)
    max_open_files: int = 64     # ulimit -n equivalent

@dataclass(frozen=True)
class ExecutionRequest:
    """Inputs for a single sandbox execution."""
    code: str
    language: str                            # "python", "javascript", "bash"
    timeout_s: float                         = 30.0
    resource_limits: ResourceLimits          = field(default_factory=ResourceLimits)
    stdin: Optional[str]                     = None

@dataclass(frozen=True)
class ExecutionResult:
    """Outputs from a single sandbox execution."""
    stdout: str
    stderr: str
    exit_code: int
    elapsed_s: float
    timed_out: bool
    backend: ExecutionBackend
    memory_exceeded: bool = False

@dataclass(frozen=True)
class SandboxConfig:
    """Runtime configuration for SandboxRunner."""
    backend: ExecutionBackend        = ExecutionBackend.SUBPROCESS
    default_timeout_s: float         = 30.0
    resource_limits: ResourceLimits  = field(default_factory=ResourceLimits)
    docker_image: str                = "python:3.12-slim"
    wasm_engine: str                 = "wasmtime"
    nsjail_path: str                 = "/usr/sbin/nsjail"
```

---

## `SandboxRunner` Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SandboxRunner(Protocol):
    """Isolated code execution sandbox."""

    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a single request and return its result."""
        ...

    async def batch_run(
        self, requests: list[ExecutionRequest]
    ) -> list[ExecutionResult]:
        """Execute multiple requests concurrently."""
        ...

    def stats(self) -> dict[str, int | float]:
        """Return accumulated execution statistics."""
        ...

    def reset(self) -> None:
        """Reset all counters and internal state."""
        ...
```

---

## `SubprocessSandboxRunner` Implementation

### Resource Limits via `resource` stdlib

```python
import resource

def _make_preexec(limits: ResourceLimits):
    """Returns a preexec_fn that applies resource limits in the child process."""
    def _set():
        # Address space (RSS) ceiling
        mem = limits.max_memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
        # CPU time ceiling
        cpu = int(limits.max_cpu_s) + 1
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        # Open file descriptors
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            (limits.max_open_files, limits.max_open_files)
        )
    return _set
```

> `preexec_fn` runs in the **child process** after `fork()` but before `exec()` — it cannot affect the parent event loop and is POSIX-only.

### `run()` — Core Execution

```python
import asyncio, os, tempfile, time

_INTERP_MAP = {"python": "python3", "javascript": "node", "bash": "bash"}
_EXT_MAP    = {"python": ".py", "javascript": ".js", "bash": ".sh"}

async def run(self, request: ExecutionRequest) -> ExecutionResult:
    backend_label = self._config.backend.name
    ext = _EXT_MAP.get(request.language, ".py")

    with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False) as f:
        f.write(request.code)
        tmp_path = f.name

    interp = _INTERP_MAP.get(request.language, "python3")
    t0 = time.monotonic()
    timed_out = memory_exceeded = False

    try:
        proc = await asyncio.create_subprocess_exec(
            interp, tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if request.stdin else None,
            preexec_fn=self._make_preexec(request.resource_limits),
        )
        stdin_bytes = request.stdin.encode() if request.stdin else None
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(stdin_bytes),
            timeout=request.timeout_s,
        )
        exit_code = proc.returncode or 0
        stdout = stdout_b.decode(errors="replace")
        stderr = stderr_b.decode(errors="replace")
    except asyncio.TimeoutError:
        timed_out = True
        proc.kill()
        await proc.wait()   # reap zombie
        stdout, stderr, exit_code = "", "Execution timed out", -1
        TMOUT.labels(backend=backend_label).inc()
    except MemoryError:
        memory_exceeded = True
        stdout, stderr, exit_code = "", "Memory limit exceeded", -1
        MEMEX.labels(backend=backend_label).inc()
    except Exception as exc:
        stdout, stderr, exit_code = "", str(exc), -1
        ERRS.labels(backend=backend_label).inc()
    finally:
        os.unlink(tmp_path)

    elapsed = time.monotonic() - t0
    RUNS.labels(backend=backend_label, language=request.language).inc()
    ELAPS.labels(backend=backend_label).observe(elapsed)

    async with self._lock:
        self._total_runs   += 1
        self._total_elapsed += elapsed
        if timed_out:
            self._timeouts += 1

    return ExecutionResult(
        stdout=stdout, stderr=stderr, exit_code=exit_code,
        elapsed_s=elapsed, timed_out=timed_out,
        backend=self._config.backend,
        memory_exceeded=memory_exceeded,
    )
```

### `batch_run()` — Concurrent Execution with Partial Failure

```python
async def batch_run(
    self, requests: list[ExecutionRequest]
) -> list[ExecutionResult]:
    raw = await asyncio.gather(
        *[self.run(r) for r in requests],
        return_exceptions=True,
    )
    return [
        r if isinstance(r, ExecutionResult)
        else ExecutionResult(
            stdout="", stderr=str(r), exit_code=-1,
            elapsed_s=0.0, timed_out=False,
            backend=self._config.backend,
        )
        for r in raw
    ]
```

### `stats()` and `reset()`

```python
def stats(self) -> dict[str, int | float]:
    return {
        "total_runs":     self._total_runs,
        "timeouts":       self._timeouts,
        "errors":         self._errors,
        "total_elapsed_s": self._total_elapsed,
    }

def reset(self) -> None:
    self._total_runs = self._timeouts = self._errors = 0
    self._total_elapsed = 0.0
```

### Factory

```python
def make_sandbox_runner(config: SandboxConfig | None = None) -> SandboxRunner:
    cfg = config or SandboxConfig()
    if cfg.backend == ExecutionBackend.SUBPROCESS:
        return SubprocessSandboxRunner(cfg)
    raise NotImplementedError(f"Backend {cfg.backend} not yet implemented")
```

---

## Integration with `CodeSynthesiser`

`SynthesisResult` gains an optional `execution` field:

```python
@dataclass(frozen=True)
class SynthesisResult:
    code: str
    strategy: SynthesisStrategy
    refinement_rounds: int
    tokens_used: int
    elapsed_s: float
    execution: ExecutionResult | None = None   # NEW in Phase 14.2
```

`synthesise()` accepts an optional `sandbox` parameter:

```python
class InMemoryCodeSynthesiser:
    async def synthesise(
        self,
        request: SynthesisRequest,
        sandbox: SandboxRunner | None = None,   # NEW
    ) -> SynthesisResult:
        ...
        result = SynthesisResult(code=code, ...)
        if sandbox is not None:
            exec_req = ExecutionRequest(
                code=code,
                language=request.target_language,
                timeout_s=self._config.sandbox_timeout_s,
            )
            execution = await sandbox.run(exec_req)
            result = dataclasses.replace(result, execution=execution)
        return result
```

### `CognitiveCycle._synthesis_step()` wiring

```python
class CognitiveCycle:
    def __init__(
        self,
        ...,
        synthesiser: CodeSynthesiser | None = None,
        sandbox: SandboxRunner | None = None,
    ) -> None:
        self._synthesiser = synthesiser
        self._sandbox     = sandbox

    async def _synthesis_step(
        self, request: SynthesisRequest
    ) -> SynthesisResult | None:
        if self._synthesiser is None:
            return None
        return await self._synthesiser.synthesise(
            request, sandbox=self._sandbox
        )
```

---

## Data Flow

```
Observation ──► CognitiveCycle._synthesis_step()
                        │
                        ▼
               CodeSynthesiser.synthesise(request, sandbox=runner)
                        │
                        ├──► _build_prompt() ──► _call_llm() ──► code: str
                        │
                        └──► SandboxRunner.run(ExecutionRequest)
                                    │
                                    ├── write code to tempfile
                                    ├── asyncio.create_subprocess_exec
                                    ├── asyncio.wait_for (timeout enforcement)
                                    ├── resource.setrlimit (preexec_fn)
                                    └── ExecutionResult(stdout, stderr, exit_code, ...)
                        │
                        ▼
               SynthesisResult(code=..., execution=ExecutionResult(...))
                        │
                        ▼
               CognitiveCycle ──► PatchSelector (Phase 14.4)
```

---

## Backend Selection Guide

| Environment | Backend | Reason |
|-------------|---------|--------|
| Local dev / CI | SUBPROCESS | Zero deps, ~2ms overhead, easy debugging |
| Staging (Linux) | NSJAIL | Strong isolation, ~20ms, no Docker daemon |
| Production (multi-language) | DOCKER | Full container isolation, language-agnostic |
| Untrusted WASM modules | WASM | Byte-level sandbox, no fs/network access |

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sandbox_runs_total` | Counter | `backend`, `language` | Total executions |
| `sandbox_timeouts_total` | Counter | `backend` | Timeout hits |
| `sandbox_errors_total` | Counter | `backend` | Unexpected errors |
| `sandbox_elapsed_seconds` | Histogram | `backend` | Wall-clock time per execution |
| `sandbox_memory_exceeded_total` | Counter | `backend` | Memory ceiling hits |

**Histogram buckets:** `[0.1, 0.5, 1, 5, 30, +Inf]`

**PromQL — timeout rate:**
```promql
rate(sandbox_timeouts_total[5m])
/ rate(sandbox_runs_total[5m])
```

**PromQL — p95 latency:**
```promql
histogram_quantile(0.95, rate(sandbox_elapsed_seconds_bucket[5m]))
```

**Grafana alert — high timeout rate:**
```yaml
- alert: SandboxHighTimeoutRate
  expr: >
    rate(sandbox_timeouts_total[5m])
    / rate(sandbox_runs_total[5m]) > 0.10
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Sandbox timeout rate >10% on {{ $labels.backend }}"
```

---

## mypy Strict Compliance

| Symbol | Notes |
|--------|-------|
| `ResourceLimits` | `frozen=True` — `int`/`float` fields with defaults |
| `ExecutionRequest` | `frozen=True` — `stdin: Optional[str]` explicit |
| `ExecutionResult` | `frozen=True` — `backend: ExecutionBackend` not Optional |
| `SandboxConfig` | `frozen=True` — `docker_image: str` not Optional |
| `SandboxRunner` | `@runtime_checkable` Protocol |
| `SubprocessSandboxRunner.run` | return `ExecutionResult` — no implicit `Any` |
| `batch_run` | return `list[ExecutionResult]` — exceptions coerced |

Run: `mypy src/sandbox_runner.py --strict`

---

## Test Targets (12)

| # | Test name | What it covers |
|---|-----------|----------------|
| 1 | `test_subprocess_run_success` | Python snippet returns exit 0 + captured stdout |
| 2 | `test_subprocess_timeout_enforcement` | Infinite loop killed within `timeout_s + 0.5s` |
| 3 | `test_subprocess_stderr_capture` | `sys.stderr.write()` captured in `ExecutionResult.stderr` |
| 4 | `test_batch_run_parallelism` | 5 snippets complete faster than sequential sum |
| 5 | `test_resource_limit_memory` | Snippet exceeding `max_memory_mb` sets `memory_exceeded=True` |
| 6 | `test_resource_limit_cpu` | CPU-intensive snippet honours `max_cpu_s` |
| 7 | `test_docker_backend_mock` | DOCKER backend calls `docker run` with correct image + flags |
| 8 | `test_wasm_backend_mock` | WASM backend invokes wasmtime with compiled module |
| 9 | `test_stats_accumulation` | `stats()` reflects `total_runs`, `timeouts`, `total_elapsed_s` |
| 10 | `test_reset_clears_stats` | `reset()` zeroes all counters |
| 11 | `test_synthesiser_integration` | `synthesise(sandbox=mock_runner)` populates `result.execution` |
| 12 | `test_prometheus_metrics_increment` | Prometheus counters increment on run/timeout/error |

---

## Implementation Order (14 steps)

1. Define `ResourceLimits` dataclass
2. Define `ExecutionRequest` dataclass
3. Define `ExecutionResult` dataclass
4. Define `SandboxConfig` dataclass
5. Define `ExecutionBackend` enum
6. Define `SandboxRunner` Protocol (`@runtime_checkable`)
7. Implement `SubprocessSandboxRunner._make_preexec()`
8. Implement `SubprocessSandboxRunner.run()` — happy path
9. Add `asyncio.TimeoutError` handling
10. Add `MemoryError` / generic exception handling
11. Implement `batch_run()` via `asyncio.gather`
12. Implement `stats()` and `reset()`
13. Add Prometheus instrumentation (5 metrics)
14. Update `SynthesisResult` + `synthesise(sandbox=)` in `CodeSynthesiser`

---

## Acceptance Criteria

- [ ] `SandboxRunner` Protocol passes `isinstance(runner, SandboxRunner)`
- [ ] `SubprocessSandboxRunner` handles SUBPROCESS backend end-to-end
- [ ] Timeout enforced within `timeout_s + 500ms` grace
- [ ] Resource limits applied via `resource` stdlib `preexec_fn`
- [ ] `batch_run` uses `asyncio.gather` for true concurrency
- [ ] All 5 Prometheus metrics increment correctly
- [ ] `CodeSynthesiser.synthesise(sandbox=runner)` populates `result.execution`
- [ ] 12 test targets pass with `pytest -q`
- [ ] Zero mypy errors under `--strict`

---

## Phase 14 Roadmap

| Sub-phase | Component | Issue | Discussions | Wiki | Status |
|-----------|-----------|-------|-------------|------|--------|
| 14.1 | CodeSynthesiser | [#385](https://github.com/web3guru888/asi-build/issues/385) | [#384](https://github.com/web3guru888/asi-build/discussions/384) / [#386](https://github.com/web3guru888/asi-build/discussions/386) / [#387](https://github.com/web3guru888/asi-build/discussions/387) | [Phase-14-Code-Synthesiser](Phase-14-Code-Synthesiser) | 🟡 spec'd |
| 14.2 | SandboxRunner | [#388](https://github.com/web3guru888/asi-build/issues/388) | [#389](https://github.com/web3guru888/asi-build/discussions/389) / [#390](https://github.com/web3guru888/asi-build/discussions/390) | **this page** | 🟡 spec'd |
| 14.3 | TestHarness | TBD | TBD | TBD | ⏳ |
| 14.4 | PatchSelector | TBD | TBD | TBD | ⏳ |
| 14.5 | SynthesisAudit | TBD | TBD | TBD | ⏳ |

---

## Phase 14 → Phase 13 Integration

| Phase 14 component | Uses from Phase 13 |
|--------------------|--------------------|
| CodeSynthesiser | `WorldModel.state_snapshot()` as prompt context |
| SandboxRunner | `CognitiveCycle._synthesis_step()` — wired alongside synthesiser |
| TestHarness (14.3) | `WorldModel` — validates synthesised plan against simulated world |
| PatchSelector (14.4) | `DreamPlanner` — selects best patch based on imagined rollout score |
| SynthesisAudit (14.5) | `WorldModelDashboard` — exports audit trail as JSON-LD |

---

*119th wiki page — part of the ASI-Build Phase 14: Code Synthesis Engine series.*
