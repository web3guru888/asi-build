# Benchmark Results

Performance and correctness benchmarks for the ASI:BUILD cognitive modules.

Tracking issue: [#24](https://github.com/web3guru888/asi-build/issues/24)  
Benchmark script: [`benchmarks/bench_consciousness.py`](https://github.com/web3guru888/asi-build/blob/main/benchmarks/bench_consciousness.py)  
Results directory: [`benchmarks/results/`](https://github.com/web3guru888/asi-build/tree/main/benchmarks/results)

---

## Consciousness Module — Run 2026-04-11T18:19Z

Commit: `693742e` (IIT Φ fix applied)  
Environment: Python 3.10, 3 repeats per test  

### Global Workspace Theory (GWT)

| Metric | Value |
|--------|-------|
| Processors | 8 |
| Content items competing | 50 |
| Submit latency (mean) | **0.059 ms** |
| Submit latency (p95) | 0.079 ms |
| Update latency (mean) | **0.018 ms** |
| Update latency (p95) | 0.020 ms |

**Interpretation**: Sub-millisecond broadcast is ideal for perception loops. Real-time robotics typically budgets 10ms per cycle — GWT consumes < 1% of that budget at 50-item scale.

### Attention Schema Theory (AST)

| Metric | Value |
|--------|-------|
| Competing targets | 20 |
| Competition latency (mean) | **0.117 ms** |
| Competition latency (stdev) | 0.017 ms |
| Awareness query latency (mean) | **0.008 ms** |
| Awareness query latency (stdev) | 0.005 ms |

**Interpretation**: AST runs in well under 1ms for 20 targets. The awareness query (reading attention state) is an order of magnitude faster than the competition itself — appropriate for a module that generates many more queries than competitions.

### IIT Φ (Integrated Information Theory)

| n (nodes) | Φ (mean) | Time (ms) | Bipartitions explored |
|-----------|---------|-----------|-----------------------|
| 2 | 0.0 | 0.119 | 1 |
| 3 | 0.0 | 0.077 | 3 |
| 4 | ~0.0 | 0.077 | 7 |
| 5 | 0.0 | 0.077 | 15 |
| 6 | 0.0 | 0.091 | 31 |
| 7 | ~0.0 | 0.136 | 63 |
| 8 | 0.0 | 0.168 | 127 |

**Why Φ ≈ 0.0?** This is expected for the random connectivity matrices used in this benchmark run. A random network with uniform connection probability has no privileged partition — every bipartition cuts roughly equal information flow, so the MIP (Minimum Information Partition) has near-zero Φ.

Non-zero Φ requires **structured asymmetry**:
- Tononi & Koch (2008) triangle-with-feedback → Φ ≈ 0.5
- Oizumi et al. (2014) XOR gate network → Φ ≈ 1.0
- Fully-connected ring with feedback → Φ > 0

**Scaling**: The benchmark confirms O(2^n) bipartition count. Timing scales sub-linearly relative to bipartitions (0.077ms at 3 bipartitions → 0.168ms at 127), suggesting the per-partition computation is very fast and the overhead is in the bookkeeping.

**Status**: ✅ Timing benchmarks validated. Canonical test networks needed for Φ correctness verification (see issue #24).

---

## Cognitive Blackboard — Known Numbers

Measured inline during integration testing (not yet in the benchmark suite):

| Metric | Value |
|--------|-------|
| Write throughput | **~20,000 entries/sec** |
| Point-query latency | **~12 µs** |
| Subscriber notification lag | **< 1 ms** |
| Thread safety | ✅ (RLock + threading.Condition) |

---

## Planned Benchmarks

The following are not yet implemented. See issue #24 and discussion #29 for roadmap:

| Module | Metrics to capture |
|--------|-------------------|
| **Knowledge Graph** | `add_triple()` throughput, `query_at()` latency, A* pathfinding time by graph size |
| **Homomorphic Encryption** | BGV/BFV encrypt/decrypt/multiply time vs. plaintext baseline; ciphertext expansion ratio |
| **Safety formal_verify** | Verification time as formula complexity grows (atoms → nested quantifiers → ring axioms) |
| **Rings Network** | DID auth latency, Chord DHT lookup time, reputation propagation delay |
| **IIT Φ (canonical networks)** | Verify Φ matches IIT 3.0 reference values for Tononi/Koch standard networks |

---

## Running the Benchmarks

```bash
# Install benchmark dependencies
pip install -e ".[dev]"

# Full suite
python3 benchmarks/bench_consciousness.py

# Individual suites
python3 benchmarks/bench_consciousness.py iit
python3 benchmarks/bench_consciousness.py gwt
python3 benchmarks/bench_consciousness.py ast

# Options
python3 benchmarks/bench_consciousness.py --max-n 12    # larger IIT networks
python3 benchmarks/bench_consciousness.py --repeats 5   # more timing repeats
python3 benchmarks/bench_consciousness.py --no-save     # don't write JSON
```

Results are written to `benchmarks/results/bench_consciousness_<timestamp>.json`.

---

## Contributing Benchmarks

To add a benchmark for another module:

1. Create `benchmarks/bench_<module>.py` following the pattern in `bench_consciousness.py`
2. Output a Markdown table to stdout and a JSON file to `benchmarks/results/`
3. Add results to this wiki page
4. Reference the tracking issue

The [Testing Strategy](Testing-Strategy) page has guidance on property tests and golden files, which complement timing benchmarks.
