# Homomorphic Computing

The `homomorphic` module is one of ASI:BUILD's most sophisticated components — **12,349 lines across 51 files** implementing Fully Homomorphic Encryption (FHE), Multi-Party Computation (MPC), Zero-Knowledge Proofs (ZKP), Private Set Intersection (PSI), and threshold cryptography. It enables privacy-preserving computation: running ML inference on encrypted data without ever decrypting it.

## Architecture Overview

```
homomorphic/
├── core/          # Polynomial ring arithmetic, encryption primitives, noise analysis
│   ├── polynomial.py   # R_q = Z[X]/(X^n+1), RNS representation, NTT multiplication
│   ├── encryption.py   # Ciphertext/Plaintext, Encryptor, Decryptor
│   ├── keys.py         # KeyGenerator, SecretKey, PublicKey, RelinKey, GaloisKeys
│   ├── noise.py        # Noise budget tracking, growth analysis
│   ├── evaluation.py   # Homomorphic add/mul/rotate/rescale
│   ├── modular.py      # Modular arithmetic utilities
│   ├── parameters.py   # FHEParameters, ParameterGenerator
│   ├── optimization.py # Bootstrapping, parameter optimization
│   └── utils.py        # Encoding utilities, batching helpers
├── schemes/       # BFV, BGV, CKKS concrete implementations
│   ├── bfv.py     # Fan-Vercauteren: integer arithmetic (~700 LOC)
│   ├── bgv.py     # Brakerski-Gentry-Vaikuntanathan: BGV variant (~770 LOC)
│   └── ckks.py    # Cheon-Kim-Kim-Song: approximate arithmetic (~755 LOC)
├── ml/            # Privacy-preserving ML over encrypted data
│   ├── neural_networks.py  # Encrypted NN inference (~709 LOC)
│   ├── linear_models.py    # Encrypted logistic/linear regression (~611 LOC)
│   ├── training.py         # FHE-compatible training procedures
│   ├── inference.py        # Encrypted model inference pipeline
│   ├── clustering.py       # K-means / GMM on ciphertext
│   ├── ensemble.py         # Encrypted ensemble methods
│   ├── metrics.py          # Encrypted evaluation metrics
│   ├── privacy.py          # DP + FHE composition
│   └── preprocessing.py    # Encrypted data preprocessing
├── mpc/           # Multi-Party Computation
│   ├── protocols.py         # BGW, GMW protocols (~564 LOC)
│   ├── mpc_engine.py        # Orchestration layer (~430 LOC)
│   ├── shamir.py            # Shamir secret sharing
│   ├── beaver.py            # Beaver triple generation
│   ├── garbled_circuits.py  # Yao's garbled circuits
│   ├── oblivious_transfer.py# OT protocols (OT, OT extension)
│   └── zero_knowledge.py    # Sigma protocols, ZKPoK
├── zkp/           # Zero-Knowledge Proofs
│   ├── zk_proofs.py    # Schnorr, Fiat-Shamir, Bulletproofs light
│   ├── zk_snarks.py    # Groth16, PLONK (simplified)
│   └── bulletproofs.py # Range proofs, aggregated proofs
├── psi/           # Private Set Intersection
│   ├── psi_protocols.py     # DH-based PSI, hash-based PSI
│   ├── psi_cardinality.py   # PSI-Cardinality (learn only |A∩B|)
│   └── multi_party_psi.py   # N-party PSI protocols
├── threshold/     # Threshold Cryptography
│   ├── threshold_encryption.py       # (t,n)-threshold ElGamal
│   ├── threshold_schemes.py          # Secret sharing schemes
│   └── distributed_key_generation.py # DKG protocols
└── database/      # Encrypted databases
    ├── encrypted_db.py       # Homomorphic database engine
    ├── encrypted_indexing.py # Encrypted B-tree, index structures
    └── encrypted_search.py   # Oblivious RAM, keyword search
```

## The FHE Schemes

### CKKS — Approximate Arithmetic (Floating-Point)

CKKS (Cheon-Kim-Kim-Song, 2017) is the go-to scheme for privacy-preserving ML because it natively handles **real and complex numbers** with bounded approximation error.

```python
from asi_build.homomorphic.schemes.ckks import CKKSScheme, CKKSPlaintext

scheme = CKKSScheme(poly_degree=8192, scale=2**40)
pk, sk = scheme.generate_keys()

# Encode 4096 complex numbers into a single ciphertext (batched SIMD)
plaintext = CKKSPlaintext(values=[1.5, 2.7, 0.3, ...], scale=2**40)
ciphertext = scheme.encrypt(plaintext, pk)

# Homomorphic addition and multiplication — no decryption needed
ct_sum  = scheme.add(ciphertext, ciphertext)
ct_prod = scheme.multiply(ciphertext, ciphertext)

# Rescale to manage scale growth after multiplication
ct_prod = scheme.rescale(ct_prod)

# Decrypt at the end
result = scheme.decrypt(ct_prod, sk)
# result ≈ original^2 (with small approximation error)
```

**Key parameters:**
| Parameter | Typical value | Effect |
|-----------|--------------|--------|
| `poly_degree` (n) | 4096–32768 | Security level + throughput |
| `scale` (Δ) | 2^30–2^50 | Precision bits |
| `modulus_chain` | [q0, q1, ..., qL] | Multiplication depth L |
| `security_level` | 128 bits | Governs n, q selection |

**Slot batching**: An n-degree CKKS ciphertext encodes n/2 complex numbers in parallel. Operations are SIMD — one multiply costs the same whether you're computing 1 or 4096 dot products simultaneously.

### BFV — Exact Integer Arithmetic

BFV (Fan-Vercauteren, 2012) provides exact arithmetic modulo a plaintext modulus `t`. Ideal for classification problems, integer comparisons, and evaluation of Boolean circuits.

```python
from asi_build.homomorphic.schemes.bfv import BFVScheme

scheme = BFVScheme(poly_degree=4096, plaintext_modulus=65537)
# Encrypt, add, multiply exactly — no approximation error
```

### BGV — Noise-Efficient Integer FHE

BGV (Brakerski-Gentry-Vaikuntanathan, 2012) modifies noise management via modulus-switching rather than rescaling. Often more efficient than BFV for deep circuits.

## The NTT Bug — A Case Study in RNS Arithmetic

Issue [#8](https://github.com/web3guru888/asi-build/issues/8) exposed a subtle correctness bug in the polynomial ring's coefficient reduction. Understanding it illuminates the entire RNS representation:

### Background: RNS (Residue Number System)

Modern FHE implementations avoid bignum arithmetic by decomposing the large coefficient modulus Q into a product of small, co-prime 64-bit primes:

```
Q = q₀ × q₁ × q₂ × ... × qₖ₋₁
```

A polynomial in `Z_Q[X]/(X^n+1)` is stored as **k separate polynomials**, each in `Z_qᵢ[X]/(X^n+1)`. This is the RNS (or CRT) representation. It enables:
- All arithmetic in native 64-bit integers (no bignums)
- NTT (Number Theoretic Transform) per prime — O(n log n) polynomial multiplication
- Modulus-switching by dropping one prime per level

### The Bug

In `polynomial.py`, `_reduce_coefficients()` previously iterated `for i in range(len(moduli))` — which is `k`, the number of primes. This left all coefficients at index `i ≥ k` **unreduced**. In an n=4096 ring with k=3 primes, indices 3..4095 were never reduced mod their respective qi.

The consequence: NTT multiplication produced wrong ciphertexts. Decryption failures, or worse, silently wrong results.

### The Fix (commit `bb787dc` → closed [#8](https://github.com/web3guru888/asi-build/issues/8))

```python
# BEFORE (wrong): only iterates over k moduli entries
for i, q in enumerate(self.ring.coefficient_modulus):
    self.coefficients[i] = self.coefficients[i] % q

# AFTER (correct): wraps modulus index for all n coefficients
num_moduli = len(self.ring.coefficient_modulus)
for i in range(len(self.coefficients)):   # full n-length vector
    q = self.ring.coefficient_modulus[i % num_moduli]
    self.coefficients[i] = self.coefficients[i] % q
```

This one-line fix — changing `range(len(moduli))` to `range(len(coefficients))` with index wrapping — unblocked 92 homomorphic tests.

**Lesson**: RNS layout requires careful distinction between "number of moduli" (k) and "number of coefficients" (n). They are independent, and off-by-one errors in index arithmetic are silent but catastrophic.

## Privacy-Preserving ML

The `ml/` sub-package implements machine learning directly on ciphertext.

### Encrypted Neural Network Inference

```python
from asi_build.homomorphic.ml.neural_networks import EncryptedNeuralNetwork

# Load a plaintext model, convert weights to HE-compatible form
enn = EncryptedNeuralNetwork(scheme='ckks', hidden_dim=128)
enn.load_weights(plaintext_model)

# Client encrypts their input
encrypted_input = enn.encrypt_input(user_data, public_key)

# Server runs inference on ciphertext — never sees plaintext
encrypted_output = enn.forward(encrypted_input)

# Client decrypts the result
predictions = enn.decrypt_output(encrypted_output, secret_key)
```

**Approximation challenge**: CKKS requires polynomial approximations of non-linear activations. ReLU(x) ≈ x²/4 + x/2 + 1/4 (degree-2 approximation) works for shallow nets but degrades for deep ones. The module provides configurable polynomial approximation degrees.

### Encrypted Logistic Regression

```python
from asi_build.homomorphic.ml.linear_models import EncryptedLogisticRegression

model = EncryptedLogisticRegression(scheme='bfv', features=32)
# Train on encrypted data, predict on encrypted queries
```

### Encrypted Metrics

```python
from asi_build.homomorphic.ml.metrics import EncryptedMetrics

# Compute accuracy, precision, recall on encrypted predictions
# Neither party learns the other's labels or predictions
metrics = EncryptedMetrics(scheme='ckks')
acc = metrics.encrypted_accuracy(enc_predictions, enc_labels)
```

## Multi-Party Computation (MPC)

MPC enables **n parties** to jointly compute a function without any party revealing their private input.

### Supported Protocols

| Protocol | Security model | Best for |
|----------|---------------|----------|
| BGW | Information-theoretic, honest majority | High-value, small circuits |
| GMW | Semi-honest / malicious | General functions |
| Yao's Garbled Circuits | Semi-honest, 2-party | Boolean circuits |
| Beaver Triples | Pre-processing + online | Multiplication gates |
| OT Extension | Communication-efficient | Large-scale OT |

```python
from asi_build.homomorphic.mpc.mpc_engine import MPCEngine
from asi_build.homomorphic.mpc.protocols import BGWProtocol

engine = MPCEngine(num_parties=3, threshold=1)
protocol = BGWProtocol(threshold=1, num_parties=3, modulus=2**31-1)

# Each party secret-shares their input
shares = protocol.share_secret(my_private_value)

# Jointly evaluate sum without revealing inputs
result = engine.evaluate_sum([my_share], [party1_share, party2_share])
```

## Zero-Knowledge Proofs (ZKP)

### Implemented Proof Systems

**Sigma Protocols** (`zk_proofs.py`):
- Schnorr identification / signature
- Fiat-Shamir heuristic (non-interactive transform)
- ZKPoK (proof of knowledge) of discrete log

**Bulletproofs** (`bulletproofs.py`):
- Range proofs: prove 0 ≤ v < 2ⁿ without revealing v
- Aggregated range proofs: batch multiple commitments
- Inner product proofs (building block for Bulletproofs)

**zk-SNARKs** (`zk_snarks.py`):
- Groth16 (3 G1 elements, 1 G2 element proof size)
- PLONK (universal trusted setup)
- Note: Current implementation is a structural prototype; elliptic curve arithmetic uses simplified placeholders pending a libsnark/arkworks binding.

### Usage Pattern

```python
from asi_build.homomorphic.zkp.zk_proofs import SchnorrProof

# Prover: prove knowledge of x such that g^x = h (without revealing x)
proof = SchnorrProof.prove(generator=g, public_value=h, secret=x)

# Verifier: check the proof
is_valid = SchnorrProof.verify(generator=g, public_value=h, proof=proof)
assert is_valid  # convinced without learning x
```

## Private Set Intersection (PSI)

PSI lets two parties compute `A ∩ B` without either learning anything about `A \ B` or `B \ A`.

### Protocols

| Protocol | Round complexity | Use case |
|----------|-----------------|----------|
| DH-based PSI | 2 rounds | Simple 2-party |
| Hash-based PSI | 1 round | Fast but weaker |
| PSI-Cardinality | 2 rounds | Learn only \|A∩B\| |
| N-party PSI | O(n) rounds | Multi-party |

```python
from asi_build.homomorphic.psi.psi_protocols import DHBasedPSI

psi = DHBasedPSI(prime=2**31 - 1)
intersection = psi.compute_intersection(
    set_a={"alice@example.com", "bob@example.com"},
    set_b={"bob@example.com", "carol@example.com"}
)
# intersection = {"bob@example.com"}
# Alice doesn't learn Carol is in set_b
# Bob (server) doesn't learn Alice's full set
```

**Application in ASI:BUILD**: PSI enables multi-agent knowledge sharing where agents can discover common knowledge-graph nodes without exposing their private subgraphs.

## Threshold Cryptography

Threshold encryption distributes trust: a (t, n)-threshold scheme requires t-of-n parties to collaborate for decryption. No single party can decrypt alone.

```python
from asi_build.homomorphic.threshold.threshold_encryption import ThresholdEncryption

# 2-of-3 threshold: any 2 parties can decrypt
te = ThresholdEncryption(threshold=2, num_parties=3)
setup = te.setup()  # Distribute key shares to parties

# Encrypt with shared public key
ciphertext = te.encrypt(message=42, public_key=setup["public_key"])

# Partial decryption from 2 parties
pd1 = te.partial_decrypt(ciphertext, setup["private_shares"][0])
pd2 = te.partial_decrypt(ciphertext, setup["private_shares"][1])

# Combine to recover plaintext
plaintext = te.combine_decryptions([pd1, pd2])
assert plaintext == 42
```

**Distributed Key Generation (DKG)**: The `distributed_key_generation.py` module implements Pedersen DKG, allowing parties to generate a shared key without any trusted dealer.

## Encrypted Databases

The `database/` sub-package implements homomorphic query evaluation:

- **Encrypted B-tree indexing**: Range queries on encrypted data
- **Keyword search**: Searchable symmetric encryption (SSE)
- **Oblivious RAM (ORAM)**: Access pattern-hiding memory
- **Encrypted joins**: Cross-table operations on ciphertext

```python
from asi_build.homomorphic.database.encrypted_db import EncryptedDatabase

db = EncryptedDatabase(scheme='ckks')
db.insert_encrypted(record_id=1, encrypted_record=enc_data)
results = db.query_encrypted(encrypted_query_vector)
```

## Integration with ASI:BUILD

### With Federated Learning

The federated learning module and homomorphic computing compose naturally: aggregate gradients under FHE so the aggregation server never sees individual model updates (as opposed to DP alone, which adds noise but the server still sees gradients in plaintext).

```python
# FederatedBlackboardAdapter can request HE-encrypted gradient aggregation
from asi_build.homomorphic.schemes.ckks import CKKSScheme
from asi_build.federated_learning.aggregator import SecureAggregator

agg = SecureAggregator(he_scheme=CKKSScheme(...))
encrypted_aggregate = agg.aggregate_encrypted(encrypted_gradients)
```

### With the Cognitive Blackboard

A planned `HomomorphicBlackboardAdapter` (Issue [#TBD]) would allow Blackboard entries to be stored and queried in encrypted form — enabling privacy-preserving multi-agent state sharing. Agents could write encrypted observations; other agents could query without the Blackboard node learning the plaintext.

### Phase 2 Vision: Encrypted IIT Φ

The most ambitious integration: computing **IIT Φ on encrypted neural activations** (Discussion [#31](https://github.com/web3guru888/asi-build/discussions/31)). The challenge is that IIT Φ requires max-over-bipartitions — a comparison operation that is expensive under FHE. Active research direction.

## Performance Characteristics

| Operation | Scheme | Approximate time |
|-----------|--------|-----------------|
| Key generation | CKKS n=4096 | ~10ms |
| Encryption (1 slot) | CKKS | ~1ms |
| Encryption (batched 2048 slots) | CKKS | ~5ms |
| Homomorphic add | CKKS | ~0.1ms |
| Homomorphic multiply | CKKS | ~5ms |
| Rescale | CKKS | ~2ms |
| Linear layer (128→64, encrypted) | CKKS | ~50ms |
| Full neural net inference | CKKS | ~100ms–10s depending on depth |

Performance is hardware-dependent. These are rough in-Python estimates; production FHE (SEAL, OpenFHE, HElib) achieves 10-100x speedup via AVX-512 SIMD.

## Open Research Questions

1. **Bootstrapping**: Current CKKS implementation doesn't implement bootstrapping (refreshing noise budget for unlimited-depth computation). What's the right API design?

2. **Activation approximation**: At what polynomial degree does activation approximation become indistinguishable from the true function for ASI:BUILD's use cases?

3. **HE + DP composition**: The privacy guarantee of FHE (computational) + DP (information-theoretic) composing to give a stronger combined guarantee — is the current composition in `ml/privacy.py` tight?

4. **ZK-SNARK production path**: The current ZK-SNARK stubs need real elliptic curve arithmetic (BN254 or BLS12-381). Should we bind to arkworks-rs via PyO3, or implement a pure Python version for correctness testing?

5. **Multi-key FHE**: Multiple agents each have their own key pair. Can they jointly evaluate a function on their combined encrypted inputs? Multi-key CKKS (MKCKKS) is theoretically possible — is it feasible in Python?

## Related

- [[Federated-Learning]] — DP + FHE composition for gradient privacy
- [[Quantum-Computing]] — quantum-safe FHE parameter selection
- [[Research-Notes]] — NTT bug post-mortem
- [[Safety-Module]] — formal verification of cryptographic protocols
- Issue [#8](https://github.com/web3guru888/asi-build/issues/8) — NTT bug (closed, fixed)
- Issue [#31](https://github.com/web3guru888/asi-build/discussions/31) — Encrypted IIT Φ research direction
