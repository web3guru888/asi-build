# Homomorphic Encryption

> **Maturity**: `alpha` · **Adapter**: `None` (Issue #120 open)

Fully Homomorphic Encryption (FHE) implementation supporting computation on encrypted data. Provides three FHE schemes (CKKS for approximate arithmetic, BFV for exact integer arithmetic, BGV for modular arithmetic), encrypted machine learning (neural networks, linear/logistic regression), secure multi-party computation (MPC), private set intersection (PSI), threshold cryptography, zero-knowledge proof generation, and an encrypted database for secure storage.

20 exported classes covering the full FHE stack.

## Key Classes

| Class | Description |
|-------|-------------|
| `FHECore` | Core FHE operations |
| `KeyGenerator` | Public/private/evaluation key generation |
| `Encryptor` | Encryption of plaintext data |
| `Decryptor` | Decryption of ciphertext data |
| `Evaluator` | Homomorphic operations on ciphertexts |
| `CKKSScheme` | CKKS scheme for approximate arithmetic |
| `BFVScheme` | BFV scheme for exact integer arithmetic |
| `BGVScheme` | BGV scheme for modular arithmetic |
| `EncryptedNeuralNetwork` | Neural network inference on encrypted data |
| `EncryptedLinearRegression` | Linear regression on encrypted data |
| `EncryptedLogisticRegression` | Logistic regression on encrypted data |
| `SecureMultiPartyComputation` | MPC protocols |
| `ThresholdScheme` | Threshold cryptography |
| `PrivateSetIntersection` | PSI protocols |
| `EncryptedDatabase` | Encrypted storage layer |
| `ZKProofSystem` | Zero-knowledge proof generation and verification |
| `SecurityLevel` | Security parameter configuration |
| `PerformanceBenchmark` | FHE performance benchmarking utilities |

## Example Usage

```python
from asi_build.homomorphic import KeyGenerator, Encryptor, Evaluator, CKKSScheme
keygen = KeyGenerator(scheme=CKKSScheme(), security_level=128)
keys = keygen.generate()
enc = Encryptor(keys.public_key)
ct1, ct2 = enc.encrypt(3.14), enc.encrypt(2.71)
ct_sum = Evaluator(keys.eval_key).add(ct1, ct2)
```

## Blackboard Integration

No blackboard adapter yet (tracked as Issue #120). When implemented, it would publish encryption/decryption metrics and secure computation results.
