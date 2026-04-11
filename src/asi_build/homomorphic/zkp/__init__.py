"""Zero-Knowledge Proof systems."""

try:
    from .zk_proofs import ZKProofSystem, SchnorrProof, RangeProof
except (ImportError, ModuleNotFoundError, SyntaxError):
    ZKProofSystem = None
    SchnorrProof = None
    RangeProof = None
try:
    from .zk_snarks import ZKSNARKs, Groth16
except (ImportError, ModuleNotFoundError, SyntaxError):
    ZKSNARKs = None
    Groth16 = None
try:
    from .bulletproofs import Bulletproofs
except (ImportError, ModuleNotFoundError, SyntaxError):
    Bulletproofs = None

__all__ = ["ZKProofSystem", "SchnorrProof", "RangeProof", "ZKSNARKs", "Groth16", "Bulletproofs"]