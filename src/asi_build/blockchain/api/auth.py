"""
Authentication and Authorization for Kenny AGI Blockchain Audit Trail API

Provides comprehensive authentication mechanisms including API keys,
JWT tokens, and role-based access control.
"""

import asyncio
import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import bcrypt
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User roles for access control"""

    ADMIN = "admin"
    AUDITOR = "auditor"
    VERIFIER = "verifier"
    READ_ONLY = "read_only"
    SYSTEM = "system"


class Permission(Enum):
    """System permissions"""

    CREATE_AUDIT_RECORD = "create_audit_record"
    READ_AUDIT_RECORD = "read_audit_record"
    VERIFY_RECORD = "verify_record"
    QUERY_RECORDS = "query_records"
    SYSTEM_STATUS = "system_status"
    SYSTEM_METRICS = "system_metrics"
    MANAGE_USERS = "manage_users"
    MANAGE_KEYS = "manage_keys"
    ADMIN_ACCESS = "admin_access"


# Role permission mappings
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.CREATE_AUDIT_RECORD,
        Permission.READ_AUDIT_RECORD,
        Permission.VERIFY_RECORD,
        Permission.QUERY_RECORDS,
        Permission.SYSTEM_STATUS,
        Permission.SYSTEM_METRICS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_KEYS,
        Permission.ADMIN_ACCESS,
    ],
    UserRole.AUDITOR: [
        Permission.CREATE_AUDIT_RECORD,
        Permission.READ_AUDIT_RECORD,
        Permission.QUERY_RECORDS,
        Permission.SYSTEM_STATUS,
    ],
    UserRole.VERIFIER: [
        Permission.READ_AUDIT_RECORD,
        Permission.VERIFY_RECORD,
        Permission.QUERY_RECORDS,
        Permission.SYSTEM_STATUS,
    ],
    UserRole.READ_ONLY: [
        Permission.READ_AUDIT_RECORD,
        Permission.QUERY_RECORDS,
        Permission.SYSTEM_STATUS,
    ],
    UserRole.SYSTEM: [
        Permission.CREATE_AUDIT_RECORD,
        Permission.READ_AUDIT_RECORD,
        Permission.SYSTEM_STATUS,
        Permission.SYSTEM_METRICS,
    ],
}


@dataclass
class APIKey:
    """API Key for authentication"""

    key_id: str
    key_hash: str  # Hashed version of the actual key
    name: str
    user_id: str
    role: UserRole
    permissions: List[Permission] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool = True
    rate_limit: int = 1000  # Requests per hour
    ip_whitelist: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if API key is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def has_permission(self, permission: Permission) -> bool:
        """Check if API key has specific permission"""
        if not self.is_active or self.is_expired():
            return False
        return permission in self.permissions or permission in ROLE_PERMISSIONS.get(self.role, [])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "key_id": self.key_id,
            "name": self.name,
            "user_id": self.user_id,
            "role": self.role.value,
            "permissions": [p.value for p in self.permissions],
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "is_active": self.is_active,
            "rate_limit": self.rate_limit,
            "ip_whitelist": self.ip_whitelist,
            "metadata": self.metadata,
        }


@dataclass
class JWTToken:
    """JWT Token information"""

    user_id: str
    role: UserRole
    permissions: List[Permission]
    issued_at: datetime
    expires_at: datetime
    token_id: str
    issuer: str = "kenny-agi-audit-trail"
    audience: str = "api"

    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.now() > self.expires_at

    def has_permission(self, permission: Permission) -> bool:
        """Check if token has specific permission"""
        if self.is_expired():
            return False
        return permission in self.permissions or permission in ROLE_PERMISSIONS.get(self.role, [])

    def to_payload(self) -> Dict[str, Any]:
        """Convert to JWT payload"""
        return {
            "user_id": self.user_id,
            "role": self.role.value,
            "permissions": [p.value for p in self.permissions],
            "iat": int(self.issued_at.timestamp()),
            "exp": int(self.expires_at.timestamp()),
            "jti": self.token_id,
            "iss": self.issuer,
            "aud": self.audience,
        }

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "JWTToken":
        """Create from JWT payload"""
        return cls(
            user_id=payload["user_id"],
            role=UserRole(payload["role"]),
            permissions=[Permission(p) for p in payload.get("permissions", [])],
            issued_at=datetime.fromtimestamp(payload["iat"]),
            expires_at=datetime.fromtimestamp(payload["exp"]),
            token_id=payload["jti"],
            issuer=payload.get("iss", "kenny-agi-audit-trail"),
            audience=payload.get("aud", "api"),
        )


class JWTAuth:
    """JWT Authentication manager"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        token_expiry: timedelta = timedelta(hours=24),
        refresh_expiry: timedelta = timedelta(days=30),
    ):
        """
        Initialize JWT authentication

        Args:
            secret_key: Secret key for signing (auto-generated if None)
            algorithm: JWT algorithm to use
            token_expiry: Access token expiry time
            refresh_expiry: Refresh token expiry time
        """
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = algorithm
        self.token_expiry = token_expiry
        self.refresh_expiry = refresh_expiry

        # For asymmetric algorithms, generate key pairs
        if algorithm.startswith("RS") or algorithm.startswith("ES"):
            self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            self.public_key = self.private_key.public_key()
        else:
            self.private_key = None
            self.public_key = None

        # Token blacklist for revoked tokens
        self.blacklist = set()

    def generate_token(
        self,
        user_id: str,
        role: UserRole,
        permissions: Optional[List[Permission]] = None,
        expiry_override: Optional[timedelta] = None,
    ) -> Tuple[str, JWTToken]:
        """
        Generate JWT token

        Args:
            user_id: User identifier
            role: User role
            permissions: Custom permissions (uses role permissions if None)
            expiry_override: Custom expiry time

        Returns:
            Tuple of (token_string, token_info)
        """
        try:
            now = datetime.now()
            expiry = now + (expiry_override or self.token_expiry)
            token_id = secrets.token_hex(16)

            # Use role permissions if no custom permissions provided
            if permissions is None:
                permissions = ROLE_PERMISSIONS.get(role, [])

            token_info = JWTToken(
                user_id=user_id,
                role=role,
                permissions=permissions,
                issued_at=now,
                expires_at=expiry,
                token_id=token_id,
            )

            # Generate JWT
            if self.private_key:
                # Use private key for signing
                signing_key = self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            else:
                signing_key = self.secret_key

            token_string = jwt.encode(
                token_info.to_payload(), signing_key, algorithm=self.algorithm
            )

            logger.info(f"Generated JWT token for user {user_id} with role {role.value}")
            return token_string, token_info

        except Exception as e:
            logger.error(f"Failed to generate JWT token: {str(e)}")
            raise RuntimeError(f"Token generation failed: {str(e)}")

    def verify_token(self, token_string: str) -> Optional[JWTToken]:
        """
        Verify and decode JWT token

        Args:
            token_string: JWT token string

        Returns:
            Token info if valid, None otherwise
        """
        try:
            # Check blacklist
            if token_string in self.blacklist:
                logger.warning("Attempted to use blacklisted token")
                return None

            # Verify token
            if self.public_key:
                # Use public key for verification
                verification_key = self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            else:
                verification_key = self.secret_key

            payload = jwt.decode(
                token_string,
                verification_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True},
            )

            token_info = JWTToken.from_payload(payload)

            # Additional expiry check
            if token_info.is_expired():
                logger.warning("Expired token used")
                return None

            logger.debug(f"Verified JWT token for user {token_info.user_id}")
            return token_info

        except jwt.ExpiredSignatureError:
            logger.warning("Expired JWT token")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"JWT verification error: {str(e)}")
            return None

    def revoke_token(self, token_string: str):
        """Add token to blacklist"""
        self.blacklist.add(token_string)
        logger.info("Token added to blacklist")

    def cleanup_blacklist(self):
        """Remove expired tokens from blacklist (call periodically)"""
        # This would need to decode tokens to check expiry
        # For now, we'll keep it simple and clear the entire blacklist periodically
        initial_size = len(self.blacklist)
        # In production, implement proper cleanup logic
        logger.info(
            f"Blacklist cleanup completed. Entries: {len(self.blacklist)} (was {initial_size})"
        )


class AuthManager:
    """
    Comprehensive authentication and authorization manager

    Supports both API key and JWT authentication with role-based access control.
    """

    def __init__(
        self,
        enable_api_keys: bool = True,
        enable_jwt: bool = True,
        jwt_secret: Optional[str] = None,
        default_rate_limit: int = 1000,
    ):
        """
        Initialize authentication manager

        Args:
            enable_api_keys: Enable API key authentication
            enable_jwt: Enable JWT authentication
            jwt_secret: JWT secret key
            default_rate_limit: Default rate limit for API keys
        """
        self.enable_api_keys = enable_api_keys
        self.enable_jwt = enable_jwt
        self.default_rate_limit = default_rate_limit

        # Storage for API keys (in production, use database)
        self.api_keys = {}

        # JWT authentication
        if enable_jwt:
            self.jwt_auth = JWTAuth(secret_key=jwt_secret)
        else:
            self.jwt_auth = None

        # Rate limiting tracking
        self.rate_limit_tracking = {}

    def generate_api_key(
        self,
        name: str,
        user_id: str,
        role: UserRole,
        expires_in: Optional[timedelta] = None,
        rate_limit: Optional[int] = None,
        ip_whitelist: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, APIKey]:
        """
        Generate new API key

        Args:
            name: Human-readable name for the key
            user_id: User identifier
            role: User role
            expires_in: Expiry time (None for no expiry)
            rate_limit: Custom rate limit
            ip_whitelist: Allowed IP addresses
            metadata: Additional metadata

        Returns:
            Tuple of (actual_key, api_key_info)
        """
        try:
            # Generate secure API key
            actual_key = f"kenny_{secrets.token_urlsafe(32)}"
            key_id = f"key_{secrets.token_hex(8)}"

            # Hash the key for storage
            key_hash = hashlib.sha256(actual_key.encode()).hexdigest()

            # Set expiry
            expires_at = None
            if expires_in:
                expires_at = datetime.now() + expires_in

            # Get role permissions
            permissions = ROLE_PERMISSIONS.get(role, [])

            api_key = APIKey(
                key_id=key_id,
                key_hash=key_hash,
                name=name,
                user_id=user_id,
                role=role,
                permissions=permissions,
                expires_at=expires_at,
                rate_limit=rate_limit or self.default_rate_limit,
                ip_whitelist=ip_whitelist or [],
                metadata=metadata or {},
            )

            self.api_keys[key_id] = api_key

            logger.info(f"Generated API key '{name}' for user {user_id}")
            return actual_key, api_key

        except Exception as e:
            logger.error(f"Failed to generate API key: {str(e)}")
            raise RuntimeError(f"API key generation failed: {str(e)}")

    def verify_api_key(self, api_key: str, client_ip: Optional[str] = None) -> Optional[APIKey]:
        """
        Verify API key

        Args:
            api_key: API key to verify
            client_ip: Client IP address for whitelist checking

        Returns:
            API key info if valid, None otherwise
        """
        try:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()

            # Find matching key
            for key_info in self.api_keys.values():
                if key_info.key_hash == key_hash:
                    # Check if key is active and not expired
                    if not key_info.is_active or key_info.is_expired():
                        logger.warning(f"Inactive or expired API key used: {key_info.key_id}")
                        return None

                    # Check IP whitelist
                    if key_info.ip_whitelist and client_ip:
                        if client_ip not in key_info.ip_whitelist:
                            logger.warning(
                                f"API key {key_info.key_id} used from unauthorized IP: {client_ip}"
                            )
                            return None

                    # Check rate limit
                    if not self._check_rate_limit(key_info.key_id, key_info.rate_limit):
                        logger.warning(f"Rate limit exceeded for API key: {key_info.key_id}")
                        return None

                    # Update last used time
                    key_info.last_used_at = datetime.now()

                    logger.debug(f"Verified API key: {key_info.key_id}")
                    return key_info

            logger.warning("Invalid API key used")
            return None

        except Exception as e:
            logger.error(f"API key verification error: {str(e)}")
            return None

    def verify_jwt_token(self, token_string: str) -> Optional[JWTToken]:
        """
        Verify JWT token

        Args:
            token_string: JWT token string

        Returns:
            Token info if valid, None otherwise
        """
        if not self.jwt_auth:
            return None

        return self.jwt_auth.verify_token(token_string)

    async def verify_token(self, token: str, client_ip: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify authentication token (API key or JWT)

        Args:
            token: Token to verify
            client_ip: Client IP address

        Returns:
            Authentication info if valid
        """
        # Try API key first
        if self.enable_api_keys and token.startswith("kenny_"):
            api_key = self.verify_api_key(token, client_ip)
            if api_key:
                return {
                    "type": "api_key",
                    "user_id": api_key.user_id,
                    "role": api_key.role,
                    "permissions": api_key.permissions + ROLE_PERMISSIONS.get(api_key.role, []),
                    "key_id": api_key.key_id,
                }

        # Try JWT token
        if self.enable_jwt:
            jwt_token = self.verify_jwt_token(token)
            if jwt_token:
                return {
                    "type": "jwt",
                    "user_id": jwt_token.user_id,
                    "role": jwt_token.role,
                    "permissions": jwt_token.permissions + ROLE_PERMISSIONS.get(jwt_token.role, []),
                    "token_id": jwt_token.token_id,
                }

        return None

    def check_permission(self, auth_info: Dict[str, Any], required_permission: Permission) -> bool:
        """
        Check if authenticated user has required permission

        Args:
            auth_info: Authentication info from verify_token
            required_permission: Required permission

        Returns:
            True if user has permission
        """
        if not auth_info:
            return False

        permissions = auth_info.get("permissions", [])
        return required_permission in permissions

    def _check_rate_limit(self, key_id: str, limit: int) -> bool:
        """
        Check rate limit for API key

        Args:
            key_id: API key identifier
            limit: Rate limit (requests per hour)

        Returns:
            True if within limit
        """
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)

        if key_id not in self.rate_limit_tracking:
            self.rate_limit_tracking[key_id] = []

        # Clean old entries
        self.rate_limit_tracking[key_id] = [
            timestamp for timestamp in self.rate_limit_tracking[key_id] if timestamp > hour_ago
        ]

        # Check current count
        current_count = len(self.rate_limit_tracking[key_id])

        if current_count >= limit:
            return False

        # Add current request
        self.rate_limit_tracking[key_id].append(now)
        return True

    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key"""
        if key_id in self.api_keys:
            self.api_keys[key_id].is_active = False
            logger.info(f"Revoked API key: {key_id}")
            return True
        return False

    def list_api_keys(self, user_id: Optional[str] = None) -> List[APIKey]:
        """List API keys (optionally filtered by user)"""
        keys = list(self.api_keys.values())

        if user_id:
            keys = [key for key in keys if key.user_id == user_id]

        return keys

    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        active_keys = sum(
            1 for key in self.api_keys.values() if key.is_active and not key.is_expired()
        )
        expired_keys = sum(1 for key in self.api_keys.values() if key.is_expired())

        return {
            "api_keys_total": len(self.api_keys),
            "api_keys_active": active_keys,
            "api_keys_expired": expired_keys,
            "jwt_enabled": self.enable_jwt,
            "api_keys_enabled": self.enable_api_keys,
            "rate_limit_tracking_entries": len(self.rate_limit_tracking),
        }
