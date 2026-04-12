# ASI:BUILD Benchmarks

Performance and correctness benchmarks for the ASI:BUILD consciousness module.

## Running Benchmarks

```bash
# Full suite (IIT Φ + GWT + AST)
python3 benchmarks/bench_consciousness.py

# Single suite
python3 benchmarks/bench_consciousness.py iit
python3 benchmarks/bench_consciousness.py gwt
python3 benchmarks/bench_consciousness.py ast

# Options
python3 benchmarks/bench_consciousness.py --max-n 10   # larger IIT networks
python3 benchmarks/bench_consciousness.py --repeats 5  # more timing repetitions
python3 benchmarks/bench_consciousness.py --no-save    # don't write JSON results
```

Results are saved to `benchmarks/results/` as timestamped JSON files.

## Current Results (2026-04-11)

### IIT Φ — Scaling by Network Size

| n  | Φ (mean) | time (ms) | bipartitions |
|----|----------|-----------|--------------|
| 2  | 0.0000   | ~0.1 ms   | 1            |
| 3  | 0.0000   | ~0.1 ms   | 3            |
| 4  | 0.0000   | ~0.1 ms   | 7            |
| 5  | 0.0000   | ~0.1 ms   | 15           |
| 6  | 0.0000   | ~0.1 ms   | 31           |
| 7  | 0.0000   | ~0.1 ms   | 63           |
| 8  | 0.0000   | ~0.2 ms   | 127          |

**Observation**: Φ = 0.0 for fully-connected networks with uniform 0.5 weights. This
is expected behavior — a fully-connected symmetric network has no information partition
advantage, so MIP cost → 0. See [issue #24](https://github.com/web3guru888/asi-build/issues/24)
for discussion of biologically-plausible test cases with non-zero Φ.

### GWT — Broadcast Latency (8 processors, 50 contents)

| Operation         | Mean    | p95     |
|-------------------|---------|---------|
| submit_content()  | 0.06 ms | 0.08 ms |
| update()          | 0.02 ms | 0.02 ms |

### AST — Attention (20 targets)

| Operation                  | Mean    | ±σ      |
|----------------------------|---------|---------|
| compete_for_attention()    | 0.12 ms | 0.02 ms |
| generate_awareness()       | 0.01 ms | <0.01ms |

## Tracking

- Issue: [#24 — Add benchmark suite for consciousness module](https://github.com/web3guru888/asi-build/issues/24)
- Discussion: [#21 — How should we evaluate module quality?](https://github.com/web3guru888/asi-build/discussions/21)
