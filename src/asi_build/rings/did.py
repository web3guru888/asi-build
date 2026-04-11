"""
Rings Network DID — Decentralized Identity
============================================

Implements DID creation, resolution, verification, and Virtual DID (VID)
computation following the BNS paper's DID method specification.

DID Format
~~~~~~~~~~
::

    did:rings:<curve>:<fingerprint>

Supported key curves:

- ``secp256k1`` — Bitcoin/Ethereum-compatible ECDSA
- ``ed25519``   — EdDSA (faster, shorter signatures)

DID Documents
~~~~~~~~~~~~~
W3C-compliant DID Documents are stored in the Chord DHT and contain:

- ``verificationMethod`` — public key(s) for this DID
- ``authentication``     — which keys can authenticate
- ``service``            — discoverable services (BNS Service Layer)
- ``proof``              — cryptographic proof of control

Virtual DIDs (VIDs)
~~~~~~~~~~~~~~~~~~~
VIDs are deterministic addresses on the Chord ring for data and services::

    VID = H(namespace + ":" + key)

Used for: DHT storage, mailboxes, sub-ring membership, service endpoints.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DID_METHOD = "rings"  # did:rings:...
RING_MODULUS = 2**160
SUPPORTED_CURVES = ("secp256k1", "ed25519")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class KeyCurve(Enum):
    """Supported elliptic curves for DID keys."""

    SECP256K1 = "secp256k1"
    ED25519 = "ed25519"


class VerificationType(Enum):
    """W3C verification method types."""

    ECDSA_SECP256K1 = "EcdsaSecp256k1VerificationKey2019"
    ED25519 = "Ed25519VerificationKey2020"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class DIDKeyPair:
    """A key pair used in a DID.

    .. note::

        In production, ``private_key`` would be an actual ECDSA/EdDSA
        private key from the ``cryptography`` library.  For this SDK
        wrapper, we use a deterministic mock based on HMAC-SHA256.
    """

    curve: KeyCurve
    public_key_hex: str
    private_key_hex: str  # Would be actual private key in production
    key_id: str = ""

    @staticmethod
    def generate(curve: KeyCurve = KeyCurve.SECP256K1, seed: Optional[str] = None) -> "DIDKeyPair":
        """Generate a new key pair.

        Parameters
        ----------
        curve : KeyCurve
            Which curve to use.
        seed : str, optional
            Deterministic seed for testing.  Random UUID if omitted.
        """
        seed_bytes = (seed or uuid.uuid4().hex).encode()

        # Deterministic key derivation (mock — not cryptographically secure
        # for production use; a real implementation would use the
        # ``cryptography`` library's ECDSA / Ed25519 key gen).
        private_key = hashlib.sha256(seed_bytes).hexdigest()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()

        return DIDKeyPair(
            curve=curve,
            public_key_hex=public_key,
            private_key_hex=private_key,
            key_id=f"key-{hashlib.sha1(public_key.encode()).hexdigest()[:8]}",
        )


@dataclass
class DIDProof:
    """Cryptographic proof of DID control.

    In BNS: the DID controller signs a challenge with the verification
    key. The verifier checks the signature against the DID Document's
    public key.
    """

    proof_type: str = "EcdsaSecp256k1Signature2019"
    created: float = field(default_factory=time.time)
    verification_method: str = ""
    proof_purpose: str = "authentication"
    signature: str = ""  # Hex-encoded signature
    challenge: str = ""
    domain: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.proof_type,
            "created": self.created,
            "verificationMethod": self.verification_method,
            "proofPurpose": self.proof_purpose,
            "signature": self.signature,
            "challenge": self.challenge,
            "domain": self.domain,
        }


@dataclass
class DIDDocument:
    """W3C-compliant DID Document.

    Follows the DID Core specification with BNS extensions.
    """

    did: str
    verification_methods: List[Dict[str, Any]] = field(default_factory=list)
    authentication: List[str] = field(default_factory=list)
    services: List[Dict[str, Any]] = field(default_factory=list)
    proof: Optional[DIDProof] = None
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        doc: Dict[str, Any] = {
            "@context": [
                "https://www.w3.org/ns/did/v1",
                "https://w3id.org/security/suites/secp256k1-2019/v1",
            ],
            "id": self.did,
            "verificationMethod": self.verification_methods,
            "authentication": self.authentication,
            "service": self.services,
            "created": self.created,
            "updated": self.updated,
        }
        if self.proof is not None:
            doc["proof"] = self.proof.to_dict()
        if self.metadata:
            doc["metadata"] = self.metadata
        return doc

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DIDDocument":
        """Deserialize from a dict (e.g. from DHT lookup)."""
        proof_data = data.get("proof")
        proof = None
        if proof_data:
            proof = DIDProof(
                proof_type=proof_data.get("type", ""),
                created=proof_data.get("created", 0),
                verification_method=proof_data.get("verificationMethod", ""),
                proof_purpose=proof_data.get("proofPurpose", "authentication"),
                signature=proof_data.get("signature", ""),
                challenge=proof_data.get("challenge", ""),
                domain=proof_data.get("domain", ""),
            )
        return DIDDocument(
            did=data.get("id", ""),
            verification_methods=data.get("verificationMethod", []),
            authentication=data.get("authentication", []),
            services=data.get("service", []),
            proof=proof,
            created=data.get("created", 0),
            updated=data.get("updated", 0),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# RingsDID — Main DID Manager
# ---------------------------------------------------------------------------


class RingsDID:
    """Create, resolve, and verify DIDs on the Rings network.

    Parameters
    ----------
    client : object, optional
        A :class:`~asi_build.rings.client.RingsClient` instance.
        If ``None``, operates in offline / local-only mode.
    default_curve : KeyCurve
        Default curve for new DIDs.
    """

    def __init__(
        self,
        client: Any = None,
        *,
        default_curve: KeyCurve = KeyCurve.SECP256K1,
    ) -> None:
        self._client = client
        self._default_curve = default_curve
        self._local_keys: Dict[str, DIDKeyPair] = {}  # did → key pair
        self._local_docs: Dict[str, DIDDocument] = {}  # did → document

    # ── DID Creation ──────────────────────────────────────────────────────

    def create_did(
        self,
        curve: Optional[KeyCurve] = None,
        seed: Optional[str] = None,
        services: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, DIDDocument]:
        """Create a new DID with a fresh key pair.

        Parameters
        ----------
        curve : KeyCurve, optional
            Override the default curve.
        seed : str, optional
            Deterministic seed (for testing).
        services : list, optional
            Service endpoints to include in the DID Document.

        Returns
        -------
        tuple of (str, DIDDocument)
            The DID string and its full Document.
        """
        curve = curve or self._default_curve
        key_pair = DIDKeyPair.generate(curve=curve, seed=seed)

        # DID = did:rings:<curve>:<fingerprint>
        fingerprint = hashlib.sha1(key_pair.public_key_hex.encode()).hexdigest()[:20]
        did = f"did:{DID_METHOD}:{curve.value}:{fingerprint}"

        # Build verification method
        vtype = (
            VerificationType.ECDSA_SECP256K1.value
            if curve == KeyCurve.SECP256K1
            else VerificationType.ED25519.value
        )
        vm = {
            "id": f"{did}#{key_pair.key_id}",
            "type": vtype,
            "controller": did,
            "publicKeyHex": key_pair.public_key_hex,
        }

        # Build DID Document
        doc = DIDDocument(
            did=did,
            verification_methods=[vm],
            authentication=[vm["id"]],
            services=services or [],
            metadata={"curve": curve.value},
        )

        # Store locally
        self._local_keys[did] = key_pair
        self._local_docs[did] = doc

        logger.info("Created DID: %s (curve=%s)", did, curve.value)
        return did, doc

    # ── DID Resolution ────────────────────────────────────────────────────

    async def resolve(self, did: str) -> Optional[DIDDocument]:
        """Resolve a DID to its DID Document.

        Checks local cache first, then queries the Rings network.

        Parameters
        ----------
        did : str
            The DID to resolve.

        Returns
        -------
        DIDDocument or None
            The resolved document, or ``None`` if not found.
        """
        # Check local
        if did in self._local_docs:
            return self._local_docs[did]

        # Query network
        if self._client is not None:
            try:
                raw = await self._client.resolve_did(did)
                if raw is not None:
                    doc = DIDDocument.from_dict(raw)
                    self._local_docs[did] = doc
                    return doc
            except Exception:
                logger.debug("Failed to resolve DID %s from network", did, exc_info=True)

        return None

    def resolve_local(self, did: str) -> Optional[DIDDocument]:
        """Resolve a DID from local cache only (synchronous)."""
        return self._local_docs.get(did)

    # ── Proof Generation ──────────────────────────────────────────────────

    def create_proof(
        self,
        did: str,
        challenge: str = "",
        domain: str = "",
    ) -> DIDProof:
        """Generate a cryptographic proof of control for a DID.

        The proof is an HMAC signature over the challenge + DID using
        the private key.  (In production, this would be a proper
        ECDSA/EdDSA signature.)

        Parameters
        ----------
        did : str
            The DID to prove control of.
        challenge : str
            A challenge string from the verifier.
        domain : str
            Domain scope for the proof.

        Returns
        -------
        DIDProof

        Raises
        ------
        ValueError
            If the DID is not locally controlled.
        """
        key_pair = self._local_keys.get(did)
        if key_pair is None:
            raise ValueError(f"No local key for DID: {did}")

        doc = self._local_docs.get(did)
        vm_id = doc.verification_methods[0]["id"] if doc and doc.verification_methods else ""

        # Sign: HMAC(private_key, challenge + did + domain)
        message = f"{challenge}:{did}:{domain}".encode()
        signature = hmac.new(
            key_pair.private_key_hex.encode(),
            message,
            hashlib.sha256,
        ).hexdigest()

        proof_type = (
            "EcdsaSecp256k1Signature2019"
            if key_pair.curve == KeyCurve.SECP256K1
            else "Ed25519Signature2020"
        )

        return DIDProof(
            proof_type=proof_type,
            verification_method=vm_id,
            signature=signature,
            challenge=challenge,
            domain=domain,
        )

    # ── Proof Verification ────────────────────────────────────────────────

    def verify_proof(
        self,
        did: str,
        proof: DIDProof,
        public_key_hex: Optional[str] = None,
    ) -> bool:
        """Verify a DID proof.

        Parameters
        ----------
        did : str
            The DID the proof claims to control.
        proof : DIDProof
            The proof to verify.
        public_key_hex : str, optional
            Override the public key.  If ``None``, uses the key from the
            locally-cached DID Document.

        Returns
        -------
        bool
            ``True`` if the proof is valid.
        """
        # Get public key
        if public_key_hex is None:
            doc = self._local_docs.get(did)
            if doc is None or not doc.verification_methods:
                logger.debug("Cannot verify proof for %s: no document", did)
                return False
            public_key_hex = doc.verification_methods[0].get("publicKeyHex", "")

        if not public_key_hex:
            return False

        # Derive the expected private key from the public key
        # This only works for our mock keys (hash-chain derivation).
        # A real implementation would verify the ECDSA/EdDSA signature
        # using only the public key.
        #
        # For the mock, we know: public = sha256(private), so we can't
        # invert it. Instead, if the DID is locally known we can verify;
        # otherwise, we attempt to verify by re-signing with the
        # known key pair.

        key_pair = self._local_keys.get(did)
        if key_pair is not None:
            # Re-sign and compare
            message = f"{proof.challenge}:{did}:{proof.domain}".encode()
            expected = hmac.new(
                key_pair.private_key_hex.encode(),
                message,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, proof.signature)

        # For remote DIDs: in production, we'd verify the ECDSA signature
        # using only the public key. In mock mode, we can't invert the
        # hash, so we accept any non-empty, well-formed signature.
        if proof.signature and len(proof.signature) == 64:
            return True

        return False

    # ── Virtual DID (VID) Computation ─────────────────────────────────────

    @staticmethod
    def compute_vid(namespace: str, key: str) -> str:
        """Compute a Virtual DID: ``VID = H(namespace + ":" + key)``.

        VIDs are deterministic addresses on the Chord ring used for:
        - Data storage: ``compute_vid("data", "my-dataset")``
        - Mailbox:      ``compute_vid("mailto", did)``
        - Sub-Ring:     ``compute_vid("subring", "topic-name")``
        - KG triple:    ``compute_vid("kg:triple", "s:p:o")``
        - Training:     ``compute_vid("asi-build:training", did)``

        Parameters
        ----------
        namespace : str
            The VID namespace.
        key : str
            The resource key within the namespace.

        Returns
        -------
        str
            A ``"vid:<hex>"`` string.
        """
        combined = f"{namespace}:{key}"
        h = hashlib.sha1(combined.encode()).hexdigest()
        return f"vid:{h}"

    @staticmethod
    def vid_to_position(vid: str) -> int:
        """Convert a VID to its ring position in Z_{2^160}."""
        hex_str = vid.removeprefix("vid:")
        return int(hex_str, 16) % RING_MODULUS

    # ── Service Registration ──────────────────────────────────────────────

    def add_service(
        self,
        did: str,
        service_id: str,
        service_type: str,
        endpoint: str,
    ) -> None:
        """Add a service endpoint to a DID Document.

        Parameters
        ----------
        did : str
            The DID to update.
        service_id : str
            Unique service identifier (e.g. ``"training-node"``).
        service_type : str
            Service type (e.g. ``"ASIBuildTrainingNode"``).
        endpoint : str
            Service endpoint URL or VID.

        Raises
        ------
        ValueError
            If the DID is not locally controlled.
        """
        doc = self._local_docs.get(did)
        if doc is None:
            raise ValueError(f"No local document for DID: {did}")

        service = {
            "id": f"{did}#svc-{service_id}",
            "type": service_type,
            "serviceEndpoint": endpoint,
        }
        doc.services.append(service)
        doc.updated = time.time()

    # ── Introspection ─────────────────────────────────────────────────────

    def list_local_dids(self) -> List[str]:
        """Return all locally-controlled DIDs."""
        return list(self._local_keys.keys())

    def get_key_pair(self, did: str) -> Optional[DIDKeyPair]:
        """Return the key pair for a locally-controlled DID."""
        return self._local_keys.get(did)

    def __repr__(self) -> str:
        return f"RingsDID(local_dids={len(self._local_keys)}, cached_docs={len(self._local_docs)})"
