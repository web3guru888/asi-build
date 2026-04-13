# Research Notes

This page documents known science gaps, implementation problems, and research questions in ASI:BUILD. We believe in radical transparency about what works and what doesn't.

---

## IIT Φ: ✅ Fixed (2026-04-11, commit 693742e)

**Module**: `consciousness/`  
**Issue**: [#6](https://github.com/web3guru888/asi-build/issues/6) — **Closed**  
**Status**: ✅ Fixed — correct TPM-based IIT 3.0 with MIP bipartition enumeration

### What Was Wrong

The original implementation computed Φ as an entropy difference when connections are cut:

```python
# WRONG: this is not IIT Φ
phi = entropy(state_distribution) - sum(entropy(partition) for partition in bipartitions)
```

This is neither theoretically grounded nor numerically equivalent to IIT 3.0. Worse, the entropy was computed on the activation history buffer, which is empty on a freshly constructed instance — so Φ was always 0.0 regardless of network topology. See [Discussion #23](https://github.com/web3guru888/asi-build/discussions/23) for the full bug walkthrough.

### What Was Fixed (commit [693742e](https://github.com/web3guru888/asi-build/commit/693742e))

Correct IIT 3.0 (Oizumi, Albantakis & Tononi 2014) via three new methods in `integrated_information.py`:

1. **`_build_tpm(sorted_nodes, cut_from, cut_to)`** — constructs a 2ⁿ×n Transition Probability Matrix from node weights/biases. Unidirectional cuts zero out connection weights from one partition to another *before* building the TPM.

2. **`_phi_of_partition(tpm, cut_from, cut_to)`** — computes whole-system and cut-system cause-effect repertoires, returns their KL divergence.

3. **`compute_phi()`** — enumerates all bipartitions (2^(n-1) − 1), returns the *minimum* KL divergence — the MIP Φ.

### Test Result After Fix

```
test_phi_recurrent_integrated_network  PASSED  Φ = 0.524 (bidirectional 3-node sigmoid network)
```

All 3,164 tests now passing, 0 failures.

### Remaining Gaps vs Full PyPhi

- Higher-order concept Φ (per-mechanism)
- SIA (System Irreducibility Analysis)  
- Validation against reference networks from the Tononi lab

Ongoing tracking: Issue [#24](https://github.com/web3guru888/asi-build/issues/24) (benchmark suite).

### References
- Oizumi, M., Albantakis, L. & Tononi, G. (2014). [From the Phenomenology to the Mechanisms of Consciousness](https://doi.org/10.1371/journal.pcbi.1003588)
- PyPhi documentation: https://pyphi.readthedocs.io/
- Barrett, A.B. & Seth, A.K. (2011). Practical measures of integrated information for time-series data

---

## Safety Formal Verification: Auto-Prove Bug

**Module**: `safety/`  
**Issue**: [#7](https://github.com/web3guru888/asi-build/issues/7) — ✅ **CLOSED**  
**Status**: ✅ Fixed in [ce0e3f0](https://github.com/web3guru888/asi-build/commit/ce0e3f0) — 72 new tests, 0 auto-prove possible

### Fixed (2026-04-11)

5 root causes identified and fixed:

1. **Bare `except` → `sp.Symbol(formula)`** — parse failures wrapped formula as a symbol; same-formula premise+conclusion auto-proved. Fixed with shared `parse_logic_formula()` that raises `FormulaParseError`.

2. **8 ethical axioms all parsed to `sp.true`** — missing `'->'→'>'` operator replacement caused all axioms to be trivially True. Fixed: `EthicalAxiom._parse_formula` now delegates to shared parser.

3. **Ungrounded conclusion symbols** — prover was checking `⊢ satisfies_safety_constraint_xyz` (a fresh symbol). Fixed: now uses constraint's `formal_specification` (e.g. `~causes_harm`).

4. **Model checking only checked 2 models** — `{all True}` and `{all False}`. Fixed: exhaustive enumeration of all 2ⁿ assignments, SAT fallback at n=20.

5. **String-template natural deduction** — fragile pattern matching. Fixed: symbolic forward-chaining with SymPy `Implies` (modus ponens/tollens, syllogisms).

### 72 Tests Added

```
parse_logic_formula:     19 tests (operators, quantifiers, errors)
auto-prove blocking:      8 tests (ungrounded, unrelated, empty premises)
valid entailments:       12 tests (modus ponens/tollens, contrapositive)
invalid fallacies:        7 tests (affirming consequent, denying antecedent)
contradiction handling:   3 tests (ex falso blocked)
axiom parsing:            4 tests (not sp.true, has free symbols)
model checking:           4 tests (exhaustive enumeration, counterexamples)
ethical engine:           8 tests (harmful rejected, safe accepted)
natural deduction:        5 tests (symbolic chains)
parse error handling:     2 tests
```

### Open Research Question

The SymPy/exhaustive approach works for small formulas (n ≤ 20 vars). For larger constraint sets, two paths:
- **Z3 SMT** — `pip install z3-solver`, handles quantified formulas, fast incremental solving
- **Lean 4 / Coq** — machine-checkable proof certificates, steep integration cost

Discussion: [#26](https://github.com/web3guru888/asi-build/discussions/26)

### References
- Z3 Python API: https://z3prover.github.io/api/html/namespacez3py.html
- de Moura, L. & Bjørner, N. (2008). Z3: An Efficient SMT Solver

---

## Homomorphic Encryption: NTT Coefficient Mixing ✅ Fixed (2026-04-11)

**Module**: `homomorphic/`  
**Issue**: [#8](https://github.com/web3guru888/asi-build/issues/8) — **Closed**  
**Status**: ✅ Fixed — correct RNS coefficient indexing with modulus wrapping

### What Was Wrong

The `_multiply_ntt()` method in `polynomial.py` used `zip()` to iterate over the NTT-domain coefficient arrays and the coefficient moduli chain simultaneously. Since `zip` truncates to the shortest iterable, only `len(moduli)` coefficients (typically 2–4) were multiplied instead of all `n` (typically 1024 or 4096). The remaining coefficients were silently zeroed, producing garbage polynomial products.

```python
# WRONG — zip truncates to shortest, mixes moduli
result_ntt = [
    (a * b) % q for a, b, q in zip(self_ntt, other_ntt, self.ring.coefficient_modulus)
]
```

The same pattern affected `_reduce_coefficients`, causing coefficient reduction to apply only to the first few entries.

### What Was Fixed

The fix iterates over all `n` coefficient positions and wraps the modulus index:

```python
# CORRECT — wraps modulus index over all n coefficients
num_moduli = len(self.ring.coefficient_modulus)
result_ntt = [
    (self_ntt[i] * other_ntt[i]) % self.ring.coefficient_modulus[i % num_moduli]
    for i in range(len(self_ntt))
]
```

This correctly implements RNS (Residue Number System) polynomial arithmetic where a single polynomial's coefficients are distributed across a modulus chain.

### Verification

All 92 homomorphic encryption tests pass post-fix:
```
$ python3 -m pytest tests/test_homomorphic.py -q
92 passed in 29.95s
```

Key tests: `test_poly_mul_multi_modulus_rns`, `test_poly_mul_negacyclic_all_coefficients_reduced`, `test_bfv_encrypt_decrypt_roundtrip`.

**Discussion**: [#30 — Show & Tell: Fixing the Homomorphic NTT Bug](https://github.com/web3guru888/asi-build/discussions/30)

### References
- Longa, P. & Naehrig, M. (2016). [Speeding up the Number Theoretic Transform for Faster Ideal Lattice-Based Cryptography](https://eprint.iacr.org/2016/504)
- OpenFHE: https://openfhe.org/

---

## Open Research Questions

Beyond the known bugs, ASI:BUILD touches several areas where the research consensus is incomplete:

### 1. Consciousness Measurement
Even if we fix IIT Φ to be numerically correct, it's unclear whether Φ is a good proxy for consciousness in artificial systems. Global Workspace Theory (GWT) and Higher-Order Thought (HOT) theories make different predictions. The `consciousness` module should ideally be theory-agnostic with pluggable metrics.

**Discussion thread**: [#10 — Why a Cognitive Blackboard?](https://github.com/web3guru888/asi-build/discussions/10)

### 2. Distributed Coherence
When two ASI:BUILD nodes exchange blackboard entries over Rings Network, they may form inconsistent beliefs. There's no consensus protocol yet. Possible approaches: CRDT-based blackboard, Paxos-style commit, or probabilistic reconciliation.

**Issue**: [#19 — Rings ↔ Blackboard integration](https://github.com/web3guru888/asi-build/issues/19)

### 3. Cross-Module Grounding
29 modules using 29 different internal representations creates a symbol grounding problem. The Cognitive Blackboard provides a common schema but doesn't solve semantic alignment between, e.g., the `vision` module's feature vectors and the `reasoning` module's logical predicates.

**Discussion**: [#12 — Phase 4 Roadmap](https://github.com/web3guru888/asi-build/discussions/12)

### 4. Privacy-Preserving Consciousness Metrics (NEW — Phase 2 Research)

Now that homomorphic encryption is correct, the question arises: can we compute IIT Φ or GWT broadcast strength on **encrypted** neural activations? This would enable privacy-preserving AGI evaluation where a user submits ciphertext and receives an encrypted consciousness score.

**Key challenges**:
- IIT Φ requires a minimization over exponentially many bipartitions — needs polynomial approximation of sign/min in CKKS
- CKKS noise budget may not survive the full TPM computation depth for large n
- GWT may be more HE-friendly (fewer matrix operations)

**Open questions**:
- What is the multiplicative depth of one IIT Φ computation for n=4,8,16?
- Can a differentiable softmin approximation of Φ remain meaningful after CKKS noise?
- Is Option B (partial decrypt of TPM intermediates) an acceptable privacy model?

**Discussion**: [#31 — Phase 2: Privacy-Preserving Consciousness](https://github.com/web3guru888/asi-build/discussions/31)

---

*Last updated: April 2026. Contributions welcome — see [Contributing](Contributing) for how to add research notes.*
