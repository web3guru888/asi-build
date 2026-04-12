#!/usr/bin/env python3
"""
Benchmark Suite — ASI:BUILD Consciousness Module
================================================

Measures wall-clock time and result quality for:
  1. IIT Φ computation at different network sizes (O(2^n) scaling)
  2. Global Workspace Theory broadcast latency
  3. Attention Schema Theory attention-competition latency

Usage:
    python3 benchmarks/bench_consciousness.py           # all benchmarks
    python3 benchmarks/bench_consciousness.py iit       # IIT only
    python3 benchmarks/bench_consciousness.py gwt       # GWT only
    python3 benchmarks/bench_consciousness.py ast       # AST only

Output: Markdown table to stdout + JSON file to benchmarks/results/

Tracking issue: https://github.com/web3guru888/asi-build/issues/24
"""

import argparse
import json
import statistics
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── project root must be on sys.path ─────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# ── helpers ───────────────────────────────────────────────────────────────────

def _mean(xs: List[float]) -> float:
    return statistics.mean(xs) if xs else float("nan")

def _stdev(xs: List[float]) -> float:
    return statistics.stdev(xs) if len(xs) > 1 else 0.0

def _timer(fn, repeats: int = 3):
    """Run fn() `repeats` times, return (results, times_ms)."""
    times, results = [], []
    for _ in range(repeats):
        t0 = time.perf_counter()
        r = fn()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
        results.append(r)
    return results, times


# ═══════════════════════════════════════════════════════════════════════════════
# 1. IIT Φ BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════════════

def _make_iit_system(n_nodes: int):
    """Build an IIT system with n_nodes fully-connected nodes."""
    from asi_build.consciousness.integrated_information import (
        IntegratedInformationTheory,
        SystemElement,
        Connection,
    )

    iit = IntegratedInformationTheory()

    # Add nodes
    node_ids = [f"n{i}" for i in range(n_nodes)]
    for nid in node_ids:
        elem = SystemElement(element_id=nid, state=0.5)
        iit.add_element(elem)

    # Fully-connected directed graph
    for src in node_ids:
        for dst in node_ids:
            if src != dst:
                conn = Connection(from_element=src, to_element=dst, weight=0.5)
                iit.add_connection(conn)

    # Run one step to seed the activation history
    iit.update_system_state()

    return iit


def bench_iit(repeats: int = 3, max_n: int = 8) -> List[Dict[str, Any]]:
    """
    Benchmark IIT Φ across network sizes 2..max_n.

    Returns a list of result dicts, one per n.
    """
    rows = []
    for n in range(2, max_n + 1):
        iit = _make_iit_system(n)

        results, times = _timer(lambda: iit.calculate_phi(), repeats=repeats)
        phi_values = [r for r in results if isinstance(r, float)]

        row = {
            "n": n,
            "phi_mean": _mean(phi_values),
            "phi_stdev": _stdev(phi_values),
            "time_ms_mean": _mean(times),
            "time_ms_stdev": _stdev(times),
            "partitions": 2 ** (n - 1) - 1,  # number of non-trivial bipartitions
        }
        rows.append(row)

        # Early exit if it's getting too slow (>10 s per call)
        if _mean(times) > 10_000:
            print(f"  [IIT] n={n} took {_mean(times):.0f} ms — stopping scale-out", file=sys.stderr)
            break

    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GLOBAL WORKSPACE THEORY BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════════════

def bench_gwt(repeats: int = 5, n_processors: int = 8, n_contents: int = 50) -> Dict[str, Any]:
    """
    Benchmark GWT broadcast latency.

    Measures:
      - submit_content() latency (content enters the competition queue)
      - update() latency (trigger coalition formation + broadcast)
    """
    from asi_build.consciousness.global_workspace import (
        GlobalWorkspaceTheory,
        WorkspaceContent,
        CognitiveProcessor,
    )

    gwt = GlobalWorkspaceTheory()

    # Register some processors
    specializations = ["perception", "reasoning", "memory", "attention"]
    for i in range(n_processors):
        proc = CognitiveProcessor(
            processor_id=f"proc_{i}",
            specialization=specializations[i % len(specializations)],
            processing_capacity=0.5 + (i % 4) * 0.1,
        )
        gwt.add_processor(proc)

    # Benchmark: submit + update cycle
    submit_times, update_times = [], []
    for _ in range(n_contents):
        content = WorkspaceContent(
            content_id=str(uuid.uuid4()),
            data={"value": 42},
            source="proc_0",
            activation_level=0.7,
        )

        t0 = time.perf_counter()
        gwt.submit_content(content)
        t1 = time.perf_counter()
        submit_times.append((t1 - t0) * 1_000)

        t0 = time.perf_counter()
        gwt.update()
        t1 = time.perf_counter()
        update_times.append((t1 - t0) * 1_000)

    return {
        "n_processors": n_processors,
        "n_contents": n_contents,
        "submit_ms_mean": _mean(submit_times),
        "submit_ms_p95": sorted(submit_times)[int(len(submit_times) * 0.95)],
        "update_ms_mean": _mean(update_times),
        "update_ms_p95": sorted(update_times)[int(len(update_times) * 0.95)],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ATTENTION SCHEMA THEORY BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════════════

def bench_ast(repeats: int = 5, n_targets: int = 20) -> Dict[str, Any]:
    """
    Benchmark AST attention competition and awareness generation.
    """
    from asi_build.consciousness.attention_schema import AttentionSchemaTheory, AttentionTarget

    ast = AttentionSchemaTheory()

    # Add attention targets
    target_types = ["object", "event", "concept"]
    for i in range(n_targets):
        t = AttentionTarget(
            target_id=f"obj_{i}",
            target_type=target_types[i % 3],
            salience=0.3 + (i % 7) * 0.1,
            location=(float(i % 5), float(i // 5), 0.0),
        )
        ast.add_attention_target(t)

    compete_times, awareness_times = [], []
    for _ in range(repeats):
        t0 = time.perf_counter()
        ast.compete_for_attention()
        t1 = time.perf_counter()
        compete_times.append((t1 - t0) * 1_000)

        t0 = time.perf_counter()
        ast.generate_awareness()
        t1 = time.perf_counter()
        awareness_times.append((t1 - t0) * 1_000)

    return {
        "n_targets": n_targets,
        "compete_ms_mean": _mean(compete_times),
        "compete_ms_stdev": _stdev(compete_times),
        "awareness_ms_mean": _mean(awareness_times),
        "awareness_ms_stdev": _stdev(awareness_times),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTING
# ═══════════════════════════════════════════════════════════════════════════════

def print_iit_table(rows: List[Dict[str, Any]]) -> None:
    print("\n### IIT Φ — Scaling by Network Size\n")
    print(f"{'n':>4}  {'Φ (mean)':>10}  {'±σ':>8}  {'time (ms)':>12}  {'±σ':>8}  {'bipartitions':>14}")
    print("-" * 66)
    for r in rows:
        print(
            f"{r['n']:>4}  {r['phi_mean']:>10.4f}  {r['phi_stdev']:>8.4f}"
            f"  {r['time_ms_mean']:>12.2f}  {r['time_ms_stdev']:>8.2f}"
            f"  {r['partitions']:>14,}"
        )


def print_gwt_table(r: Dict[str, Any]) -> None:
    print("\n### GWT — Broadcast Latency\n")
    print(f"  Processors: {r['n_processors']}, Contents submitted: {r['n_contents']}")
    print(f"  submit_content():  mean={r['submit_ms_mean']:.3f} ms  p95={r['submit_ms_p95']:.3f} ms")
    print(f"  update():          mean={r['update_ms_mean']:.3f} ms  p95={r['update_ms_p95']:.3f} ms")


def print_ast_table(r: Dict[str, Any]) -> None:
    print("\n### AST — Attention Competition & Awareness\n")
    print(f"  Targets: {r['n_targets']}")
    print(f"  compete_for_attention(): mean={r['compete_ms_mean']:.3f} ms  ±{r['compete_ms_stdev']:.3f}")
    print(f"  generate_awareness():    mean={r['awareness_ms_mean']:.3f} ms  ±{r['awareness_ms_stdev']:.3f}")


def save_results(results: Dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%S")
    out_path = out_dir / f"bench_consciousness_{ts}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {out_path}", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="ASI:BUILD consciousness benchmarks")
    parser.add_argument("suite", nargs="?", choices=["iit", "gwt", "ast"],
                        help="Run only this suite (default: all)")
    parser.add_argument("--repeats", type=int, default=3, help="Timing repetitions (default: 3)")
    parser.add_argument("--max-n", type=int, default=8,
                        help="Max IIT network size to benchmark (default: 8)")
    parser.add_argument("--no-save", action="store_true", help="Skip saving JSON results")
    args = parser.parse_args()

    run_iit = args.suite in (None, "iit")
    run_gwt = args.suite in (None, "gwt")
    run_ast = args.suite in (None, "ast")

    print("# ASI:BUILD Consciousness Benchmark Results")
    print(f"# Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print(f"# Issue: https://github.com/web3guru888/asi-build/issues/24\n")

    all_results: Dict[str, Any] = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    if run_iit:
        print("Running IIT Φ benchmark...", file=sys.stderr)
        iit_rows = bench_iit(repeats=args.repeats, max_n=args.max_n)
        print_iit_table(iit_rows)
        all_results["iit"] = iit_rows

    if run_gwt:
        print("Running GWT benchmark...", file=sys.stderr)
        gwt_result = bench_gwt(repeats=args.repeats)
        print_gwt_table(gwt_result)
        all_results["gwt"] = gwt_result

    if run_ast:
        print("Running AST benchmark...", file=sys.stderr)
        ast_result = bench_ast(repeats=args.repeats)
        print_ast_table(ast_result)
        all_results["ast"] = ast_result

    if not args.no_save:
        out_dir = Path(__file__).parent / "results"
        save_results(all_results, out_dir)


if __name__ == "__main__":
    main()
