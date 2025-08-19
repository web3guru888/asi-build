# Homomorphic Encryption Module for Kenny

A comprehensive implementation of fully homomorphic encryption (FHE) schemes including CKKS, BFV, BGV, and advanced cryptographic protocols.

## Overview

This module provides a complete homomorphic encryption framework with:

- **Core FHE Schemes**: CKKS, BFV, BGV implementations
- **Encrypted Machine Learning**: Neural networks, linear models, ensemble methods
- **Secure Multi-Party Computation**: BGW, GMW protocols with networking
- **Private Set Intersection**: DH-based and OT-based PSI protocols
- **Encrypted Databases**: Searchable encryption and encrypted queries
- **Zero-Knowledge Proofs**: Schnorr, range proofs, zk-SNARKs, Bulletproofs
- **Threshold Cryptography**: Distributed key generation and threshold schemes

## Quick Start

```python
from homomorphic import CKKSScheme, SecurityLevel, SchemeType
from homomorphic.core.base import FHEConfiguration

# Create CKKS configuration
config = FHEConfiguration(
    scheme_type=SchemeType.CKKS,
    security_level=SecurityLevel.MEDIUM,
    polynomial_modulus_degree=8192,
    coefficient_modulus=[60, 40, 40, 60],
    scale=2**40
)

# Initialize scheme
scheme = CKKSScheme(config)
keys = scheme.generate_keys()

# Encrypt data
data = [1.5, 2.7, 3.14, 4.2]
plaintext = scheme.encode(data)
ciphertext = scheme.encrypt(plaintext)

# Perform operations
result = scheme.multiply(ciphertext, ciphertext)
result = scheme.rescale(result)

# Decrypt result
decrypted = scheme.decrypt(result)
values = scheme.decode(decrypted)
print(f"Result: {values}")
```

## Architecture

### Core Components

- **`core/`**: Base FHE operations, polynomial arithmetic, parameter generation
- **`schemes/`**: CKKS, BFV, BGV scheme implementations
- **`ml/`**: Encrypted machine learning models and algorithms
- **`mpc/`**: Secure multi-party computation protocols
- **`psi/`**: Private set intersection implementations
- **`database/`**: Encrypted database operations
- **`zkp/`**: Zero-knowledge proof systems
- **`threshold/`**: Threshold cryptography schemes

### Supported Schemes

1. **CKKS**: Approximate arithmetic on real/complex numbers
2. **BFV**: Exact arithmetic on integers with batching
3. **BGV**: Exact arithmetic with efficient modulus switching

### Machine Learning Support

- **Neural Networks**: Encrypted deep learning with polynomial activations
- **Linear Models**: Encrypted linear/logistic regression
- **Ensemble Methods**: Encrypted random forests and gradient boosting
- **Clustering**: Encrypted K-means and DBSCAN
- **Preprocessing**: Encrypted scaling and normalization

### Security Features

- **128-384 bit security levels**
- **Noise management and estimation**
- **Differential privacy integration**
- **Secure aggregation protocols**
- **Zero-knowledge proofs for verification**

## Performance

The implementation is optimized for:
- **Number Theoretic Transform (NTT)** for fast polynomial operations
- **Lazy relinearization** to reduce computational overhead
- **Batching/SIMD** operations for vectorized computations
- **Memory-efficient** ciphertext representation
- **Parallel evaluation** of circuits

## Examples

### Encrypted Machine Learning

```python
from homomorphic.ml import EncryptedNeuralNetwork, EncryptedLinearRegression
from homomorphic.core.base import FHEConfiguration, SchemeType, SecurityLevel

# Configure CKKS for ML
config = FHEConfiguration(
    scheme_type=SchemeType.CKKS,
    security_level=SecurityLevel.MEDIUM,
    polynomial_modulus_degree=16384,
    coefficient_modulus=[60, 40, 40, 40, 60],
    scale=2**40
)

# Create encrypted neural network
network_config = [
    LayerConfig("dense", 784, 128, activation="relu"),
    LayerConfig("dense", 128, 64, activation="relu"), 
    LayerConfig("dense", 64, 10, activation="sigmoid")
]

network = EncryptedNeuralNetwork(config, network_config)
keys = network.generate_keys()

# Load pretrained weights
network.load_pretrained_weights(pretrained_weights)

# Encrypt input and predict
encrypted_input = network.encrypt_input(input_data)
encrypted_output = network.predict(encrypted_input)
prediction = network.decrypt_output(encrypted_output)
```

### Secure Multi-Party Computation

```python
from homomorphic.mpc import MPCEngine

# Initialize MPC engine
mpc = MPCEngine("bgw", threshold=2, num_parties=3)

# Add parties
mpc.add_party(0, "party0.example.com")
mpc.add_party(1, "party1.example.com") 
mpc.add_party(2, "party2.example.com")

# Define computation
circuit = {
    "inputs": {"x": 10, "y": 20, "z": 30},
    "operations": [
        {"type": "add", "inputs": ["x", "y"], "output": "sum_xy"},
        {"type": "multiply", "inputs": ["sum_xy", "z"], "output": "result"}
    ],
    "outputs": ["result"]
}

# Execute secure computation
results = mpc.execute_circuit(circuit)
print(f"Secure computation result: {results['result']}")
```

### Private Set Intersection

```python
from homomorphic.psi import DHBasedPSI

# Initialize PSI protocol
psi = DHBasedPSI()

# Define sets
set_a = {"alice@example.com", "bob@example.com", "charlie@example.com"}
set_b = {"bob@example.com", "david@example.com", "eve@example.com"}

# Compute intersection
intersection = psi.compute_intersection(set_a, set_b)
print(f"Common elements: {intersection}")
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest homomorphic/tests/

# Run specific test categories  
python -m pytest homomorphic/tests/test_ckks.py
python -m pytest homomorphic/tests/test_ml.py
python -m pytest homomorphic/tests/test_mpc.py

# Run with coverage
python -m pytest --cov=homomorphic homomorphic/tests/
```

## Benchmarks

Performance benchmarks for different operations:

```bash
# Run benchmarks
python homomorphic/benchmarks/run_benchmarks.py

# Specific scheme benchmarks
python homomorphic/benchmarks/ckks_benchmark.py
python homomorphic/benchmarks/ml_benchmark.py
```

## Security Considerations

- **Parameter Selection**: Use recommended parameters for target security level
- **Noise Management**: Monitor noise budget to prevent decryption failures
- **Key Management**: Securely store and distribute encryption keys
- **Side-Channel Protection**: Implementation includes basic timing attack mitigations
- **Verification**: Zero-knowledge proofs available for result verification

## Dependencies

- NumPy for numerical operations
- PyCryptodome for cryptographic primitives  
- Optional: multiprocessing for parallel operations

## License

This implementation is part of the Kenny project and follows the project's licensing terms.

## Contributing

Contributions welcome! Please see the main Kenny project for contribution guidelines.

## References

- Brakerski, Gentry, Vaikuntanathan: Fully Homomorphic Encryption schemes
- Cheon, Kim, Kim, Song: CKKS scheme for approximate arithmetic
- Ben-Or, Goldwasser, Wigderson: BGW protocol for MPC
- Goldreich, Micali, Wigderson: GMW protocol for boolean circuits