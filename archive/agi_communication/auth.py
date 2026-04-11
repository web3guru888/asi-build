"""
Inter-AGI Authentication and Trust Establishment
==============================================

Advanced authentication and trust management system for secure
AGI-to-AGI communications with reputation tracking and zero-trust principles.
"""

import asyncio
import json
import hashlib
import hmac
import time
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import jwt
import logging
import uuid
import base64
import secrets

from .core import CommunicationMessage, MessageType, AGIIdentity

logger = logging.getLogger(__name__)

class TrustLevel(Enum):
    """Trust levels for AGI interactions."""
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"

class AuthenticationMethod(Enum):
    """Authentication methods."""
    PKI_CERTIFICATE = "pki_certificate"
    JWT_TOKEN = "jwt_token"
    CHALLENGE_RESPONSE = "challenge_response"
    MULTI_FACTOR = "multi_factor"
    ZERO_KNOWLEDGE_PROOF = "zero_knowledge_proof"
    BLOCKCHAIN_IDENTITY = "blockchain_identity"

@dataclass
class TrustRecord:
    """Record of trust interactions with an AGI."""
    agi_id: str
    trust_score: float  # 0-1
    reputation_points: int
    successful_interactions: int
    failed_interactions: int
    last_interaction: datetime
    trust_level: TrustLevel
    verification_methods: List[str] = field(default_factory=list)
    attestations: List[Dict[str, Any]] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    def update_trust(self, success: bool, impact: float = 1.0):
        """Update trust based on interaction outcome."""
        if success:
            self.successful_interactions += 1
            self.reputation_points += int(10 * impact)
            # Gradually increase trust
            self.trust_score = min(1.0, self.trust_score + 0.01 * impact)
        else:
            self.failed_interactions += 1
            # Decrease trust more aggressively for failures
            self.trust_score = max(0.0, self.trust_score - 0.05 * impact)
        
        self.last_interaction = datetime.now()
        self._update_trust_level()
    
    def _update_trust_level(self):
        """Update trust level based on trust score."""
        if self.trust_score >= 0.9:
            self.trust_level = TrustLevel.VERIFIED
        elif self.trust_score >= 0.7:
            self.trust_level = TrustLevel.HIGH
        elif self.trust_score >= 0.5:
            self.trust_level = TrustLevel.MEDIUM
        elif self.trust_score >= 0.2:
            self.trust_level = TrustLevel.LOW
        else:
            self.trust_level = TrustLevel.UNTRUSTED

@dataclass
class AuthenticationCredentials:
    """Authentication credentials for an AGI."""
    agi_id: str
    public_key: bytes
    private_key: Optional[bytes] = None
    certificate: Optional[bytes] = None
    jwt_secret: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    is_revoked: bool = False

@dataclass
class ChallengeResponse:
    """Challenge-response authentication data."""
    challenge_id: str
    challenge_data: str
    expected_response: str
    created_at: datetime
    expires_at: datetime
    attempts: int = 0
    max_attempts: int = 3

class CryptographicManager:
    """Manages cryptographic operations for authentication."""
    
    def __init__(self):
        self.key_pairs: Dict[str, Tuple[bytes, bytes]] = {}  # agi_id -> (private, public)
        self.symmetric_keys: Dict[str, bytes] = {}  # session_id -> key
    
    def generate_key_pair(self, agi_id: str) -> Tuple[bytes, bytes]:
        """Generate RSA key pair for AGI."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        self.key_pairs[agi_id] = (private_pem, public_pem)
        return private_pem, public_pem
    
    def sign_message(self, message: str, private_key_pem: bytes) -> str:
        """Sign message with private key."""
        private_key = serialization.load_pem_private_key(
            private_key_pem, password=None
        )
        
        message_bytes = message.encode('utf-8')
        signature = private_key.sign(
            message_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_signature(self, message: str, signature: str, public_key_pem: bytes) -> bool:
        """Verify message signature."""
        try:
            public_key = serialization.load_pem_public_key(public_key_pem)
            signature_bytes = base64.b64decode(signature)
            message_bytes = message.encode('utf-8')
            
            public_key.verify(
                signature_bytes,
                message_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False
    
    def encrypt_message(self, message: str, public_key_pem: bytes) -> str:
        """Encrypt message with public key."""
        public_key = serialization.load_pem_public_key(public_key_pem)
        message_bytes = message.encode('utf-8')
        
        # RSA can only encrypt limited data, so we use hybrid encryption
        # Generate symmetric key
        symmetric_key = secrets.token_bytes(32)  # 256-bit key
        
        # Encrypt symmetric key with RSA
        encrypted_key = public_key.encrypt(
            symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Encrypt message with symmetric key
        iv = secrets.token_bytes(16)
        cipher = Cipher(algorithms.AES(symmetric_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        
        # Pad message to multiple of 16 bytes
        pad_length = 16 - (len(message_bytes) % 16)
        padded_message = message_bytes + bytes([pad_length] * pad_length)
        
        encrypted_message = encryptor.update(padded_message) + encryptor.finalize()
        
        # Combine encrypted key, IV, and encrypted message
        combined = encrypted_key + iv + encrypted_message
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt_message(self, encrypted_message: str, private_key_pem: bytes) -> str:
        """Decrypt message with private key."""
        private_key = serialization.load_pem_private_key(
            private_key_pem, password=None
        )
        
        combined = base64.b64decode(encrypted_message)
        
        # Extract components
        encrypted_key = combined[:256]  # RSA 2048-bit = 256 bytes
        iv = combined[256:272]  # 16 bytes IV
        encrypted_data = combined[272:]
        
        # Decrypt symmetric key
        symmetric_key = private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Decrypt message
        cipher = Cipher(algorithms.AES(symmetric_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_message = decryptor.update(encrypted_data) + decryptor.finalize()
        
        # Remove padding
        pad_length = padded_message[-1]
        message_bytes = padded_message[:-pad_length]
        
        return message_bytes.decode('utf-8')
    
    def generate_session_key(self, session_id: str) -> bytes:
        """Generate symmetric session key."""
        key = secrets.token_bytes(32)
        self.symmetric_keys[session_id] = key
        return key

class InterAGIAuthenticator:
    """
    Inter-AGI Authentication and Trust Establishment System
    
    Provides secure authentication, trust management, and reputation
    tracking for AGI communications.
    """
    
    def __init__(self, protocol):
        self.protocol = protocol
        self.crypto_manager = CryptographicManager()
        self.trust_records: Dict[str, TrustRecord] = {}
        self.credentials: Dict[str, AuthenticationCredentials] = {}
        self.active_challenges: Dict[str, ChallengeResponse] = {}
        self.authentication_history: List[Dict[str, Any]] = []
        
        # Initialize own credentials
        self._initialize_own_credentials()
    
    def _initialize_own_credentials(self):
        """Initialize authentication credentials for this AGI."""
        agi_id = self.protocol.identity.id
        private_key, public_key = self.crypto_manager.generate_key_pair(agi_id)
        
        credentials = AuthenticationCredentials(
            agi_id=agi_id,
            public_key=public_key,
            private_key=private_key,
            jwt_secret=secrets.token_urlsafe(32)
        )
        
        self.credentials[agi_id] = credentials
        self.protocol.identity.public_key = base64.b64encode(public_key).decode('utf-8')
    
    async def start(self):
        """Start the authentication service."""
        logger.info("Inter-AGI authentication service started")
    
    async def stop(self):
        """Stop the authentication service."""
        logger.info("Inter-AGI authentication service stopped")
    
    async def authenticate_agi(self, agi_id: str, method: AuthenticationMethod) -> bool:
        """Authenticate an AGI using specified method."""
        try:
            if method == AuthenticationMethod.PKI_CERTIFICATE:
                return await self._authenticate_pki(agi_id)
            elif method == AuthenticationMethod.JWT_TOKEN:
                return await self._authenticate_jwt(agi_id)
            elif method == AuthenticationMethod.CHALLENGE_RESPONSE:
                return await self._authenticate_challenge_response(agi_id)
            elif method == AuthenticationMethod.MULTI_FACTOR:
                return await self._authenticate_multi_factor(agi_id)
            else:
                logger.warning(f"Unsupported authentication method: {method}")
                return False
        
        except Exception as e:
            logger.error(f"Authentication error for {agi_id}: {e}")
            return False
    
    async def _authenticate_pki(self, agi_id: str) -> bool:
        """Authenticate using PKI certificates."""
        if agi_id not in self.credentials:
            return False
        
        credentials = self.credentials[agi_id]
        if credentials.is_revoked or (credentials.expires_at and datetime.now() > credentials.expires_at):
            return False
        
        # In practice, this would verify certificate chain
        return True
    
    async def _authenticate_jwt(self, agi_id: str) -> bool:
        """Authenticate using JWT tokens."""
        # This would involve JWT token validation
        # Simplified implementation
        return agi_id in self.credentials
    
    async def _authenticate_challenge_response(self, agi_id: str) -> bool:
        """Authenticate using challenge-response mechanism."""
        # Generate challenge
        challenge_id = str(uuid.uuid4())
        challenge_data = secrets.token_urlsafe(32)
        
        # Expected response is signed challenge
        if agi_id not in self.credentials:
            return False
        
        credentials = self.credentials[agi_id]
        expected_response = self.crypto_manager.sign_message(
            challenge_data, credentials.private_key
        )
        
        challenge = ChallengeResponse(
            challenge_id=challenge_id,
            challenge_data=challenge_data,
            expected_response=expected_response,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=5)
        )
        
        self.active_challenges[challenge_id] = challenge
        
        # Send challenge (simplified - in practice would be sent via message)
        # Return True if response matches expected
        return True
    
    async def _authenticate_multi_factor(self, agi_id: str) -> bool:
        """Authenticate using multiple factors."""
        # Combine PKI and challenge-response
        pki_result = await self._authenticate_pki(agi_id)
        challenge_result = await self._authenticate_challenge_response(agi_id)
        
        return pki_result and challenge_result
    
    def sign_message(self, message: CommunicationMessage) -> str:
        """Sign a communication message."""
        agi_id = self.protocol.identity.id
        if agi_id not in self.credentials:
            raise ValueError("No credentials available for signing")
        
        credentials = self.credentials[agi_id]
        message_content = json.dumps(message.to_dict(), sort_keys=True)
        
        return self.crypto_manager.sign_message(message_content, credentials.private_key)
    
    async def verify_message(self, message: CommunicationMessage) -> bool:
        """Verify message signature."""
        if not message.signature:
            return False
        
        sender_id = message.sender_id
        if sender_id not in self.credentials:
            # Try to get public key from known AGIs
            if sender_id in self.protocol.known_agis:
                known_agi = self.protocol.known_agis[sender_id]
                if known_agi.public_key:
                    public_key = base64.b64decode(known_agi.public_key)
                    message_content = json.dumps(message.to_dict(), sort_keys=True)
                    return self.crypto_manager.verify_signature(
                        message_content, message.signature, public_key
                    )
            return False
        
        credentials = self.credentials[sender_id]
        message_content = json.dumps(message.to_dict(), sort_keys=True)
        
        verified = self.crypto_manager.verify_signature(
            message_content, message.signature, credentials.public_key
        )
        
        # Update trust based on verification result
        self.update_trust(sender_id, verified, impact=0.1)
        
        return verified
    
    def establish_trust(self, agi_id: str, initial_trust: float = 0.5) -> TrustRecord:
        """Establish trust relationship with an AGI."""
        if agi_id in self.trust_records:
            return self.trust_records[agi_id]
        
        trust_record = TrustRecord(
            agi_id=agi_id,
            trust_score=initial_trust,
            reputation_points=0,
            successful_interactions=0,
            failed_interactions=0,
            last_interaction=datetime.now(),
            trust_level=TrustLevel.MEDIUM
        )
        
        self.trust_records[agi_id] = trust_record
        return trust_record
    
    def update_trust(self, agi_id: str, success: bool, impact: float = 1.0):
        """Update trust score for an AGI."""
        if agi_id not in self.trust_records:
            self.establish_trust(agi_id)
        
        trust_record = self.trust_records[agi_id]
        trust_record.update_trust(success, impact)
        
        # Update AGI identity trust score if available
        if agi_id in self.protocol.known_agis:
            self.protocol.known_agis[agi_id].trust_score = trust_record.trust_score
    
    def get_trust_level(self, agi_id: str) -> TrustLevel:
        """Get trust level for an AGI."""
        if agi_id in self.trust_records:
            return self.trust_records[agi_id].trust_level
        return TrustLevel.UNTRUSTED
    
    def add_attestation(self, agi_id: str, attestation: Dict[str, Any]):
        """Add attestation for an AGI."""
        if agi_id not in self.trust_records:
            self.establish_trust(agi_id)
        
        self.trust_records[agi_id].attestations.append(attestation)
    
    def revoke_credentials(self, agi_id: str):
        """Revoke credentials for an AGI."""
        if agi_id in self.credentials:
            self.credentials[agi_id].is_revoked = True
        
        if agi_id in self.trust_records:
            self.trust_records[agi_id].trust_score = 0.0
            self.trust_records[agi_id].trust_level = TrustLevel.UNTRUSTED
            self.trust_records[agi_id].risk_factors.append("credentials_revoked")
    
    async def handle_trust_verification(self, message: CommunicationMessage):
        """Handle trust verification request from another AGI."""
        payload = message.payload
        action = payload.get('action')
        
        try:
            if action == 'trust_query':
                await self._handle_trust_query(message)
            elif action == 'attestation':
                await self._handle_attestation(message)
            elif action == 'challenge':
                await self._handle_challenge(message)
            elif action == 'challenge_response':
                await self._handle_challenge_response(message)
            else:
                logger.warning(f"Unknown trust verification action: {action}")
        
        except Exception as e:
            logger.error(f"Error handling trust verification: {e}")
    
    async def _handle_trust_query(self, message: CommunicationMessage):
        """Handle trust query request."""
        payload = message.payload
        queried_agi = payload.get('agi_id')
        
        if queried_agi in self.trust_records:
            trust_record = self.trust_records[queried_agi]
            trust_info = {
                'agi_id': queried_agi,
                'trust_score': trust_record.trust_score,
                'trust_level': trust_record.trust_level.value,
                'reputation_points': trust_record.reputation_points,
                'interaction_count': trust_record.successful_interactions + trust_record.failed_interactions,
                'success_rate': (
                    trust_record.successful_interactions / 
                    max(1, trust_record.successful_interactions + trust_record.failed_interactions)
                )
            }
        else:
            trust_info = {
                'agi_id': queried_agi,
                'trust_score': 0.5,  # Default neutral trust
                'trust_level': TrustLevel.MEDIUM.value,
                'known': False
            }
        
        response_message = CommunicationMessage(
            id=str(uuid.uuid4()),
            sender_id=self.protocol.identity.id,
            receiver_id=message.sender_id,
            message_type=MessageType.TRUST_VERIFICATION,
            timestamp=datetime.now(),
            payload={
                'action': 'trust_response',
                'original_message_id': message.id,
                'trust_info': trust_info
            }
        )
        
        await self.protocol.send_message(response_message)
    
    async def _handle_attestation(self, message: CommunicationMessage):
        """Handle attestation from another AGI."""
        payload = message.payload
        attestation = payload.get('attestation')
        subject_agi = payload.get('subject_agi')
        
        if attestation and subject_agi:
            self.add_attestation(subject_agi, {
                'attestor': message.sender_id,
                'attestation': attestation,
                'timestamp': datetime.now().isoformat(),
                'verified': True  # In practice, would verify attestation
            })
    
    async def _handle_challenge(self, message: CommunicationMessage):
        """Handle authentication challenge."""
        payload = message.payload
        challenge_data = payload.get('challenge_data')
        challenge_id = payload.get('challenge_id')
        
        if not challenge_data or not challenge_id:
            return
        
        # Sign the challenge
        agi_id = self.protocol.identity.id
        if agi_id in self.credentials:
            credentials = self.credentials[agi_id]
            response = self.crypto_manager.sign_message(
                challenge_data, credentials.private_key
            )
            
            # Send response
            response_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=message.sender_id,
                message_type=MessageType.TRUST_VERIFICATION,
                timestamp=datetime.now(),
                payload={
                    'action': 'challenge_response',
                    'challenge_id': challenge_id,
                    'response': response
                }
            )
            
            await self.protocol.send_message(response_message)
    
    async def _handle_challenge_response(self, message: CommunicationMessage):
        """Handle challenge response."""
        payload = message.payload
        challenge_id = payload.get('challenge_id')
        response = payload.get('response')
        
        if challenge_id not in self.active_challenges:
            return
        
        challenge = self.active_challenges[challenge_id]
        challenge.attempts += 1
        
        # Verify response
        if response == challenge.expected_response:
            # Authentication successful
            self.update_trust(message.sender_id, True, impact=0.2)
            del self.active_challenges[challenge_id]
        else:
            # Authentication failed
            self.update_trust(message.sender_id, False, impact=0.2)
            
            # Remove challenge if max attempts reached
            if challenge.attempts >= challenge.max_attempts:
                del self.active_challenges[challenge_id]
    
    def get_authentication_statistics(self) -> Dict[str, Any]:
        """Get authentication statistics."""
        total_trust_records = len(self.trust_records)
        if total_trust_records == 0:
            return {'total_trust_records': 0}
        
        trust_levels = [record.trust_level for record in self.trust_records.values()]
        trust_scores = [record.trust_score for record in self.trust_records.values()]
        
        trust_level_counts = {level.value: 0 for level in TrustLevel}
        for level in trust_levels:
            trust_level_counts[level.value] += 1
        
        return {
            'total_trust_records': total_trust_records,
            'trust_level_distribution': trust_level_counts,
            'average_trust_score': sum(trust_scores) / len(trust_scores),
            'active_challenges': len(self.active_challenges),
            'credentials_managed': len(self.credentials)
        }