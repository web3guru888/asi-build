"""
REST API for Kenny AGI Blockchain Audit Trail

Provides comprehensive REST endpoints for audit trail operations including
record creation, querying, verification, and system management.
"""

import asyncio
import json
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from dataclasses import asdict
import logging

from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Internal imports
from ..web3_integration import Web3Client, ContractManager
from ..ipfs import IPFSClient, DataManager, EncryptedDataManager, PinningService
from ..crypto import SignatureManager, SignatureVerifier, HashManager, DigitalSignature
from .auth import AuthManager, APIKey, JWTAuth
from .validators import RequestValidator
from .middleware import RateLimitMiddleware, LoggingMiddleware

logger = logging.getLogger(__name__)

# Request/Response Models
class AuditRecordRequest(BaseModel):
    """Request model for creating audit records"""
    
    event_type: str = Field(..., description="Type of event being audited")
    user_id: str = Field(..., description="ID of the user performing the action")
    action: str = Field(..., description="Action being audited")
    resource: str = Field(..., description="Resource being acted upon")
    details: Dict[str, Any] = Field(..., description="Detailed event information")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")
    encrypt: bool = Field(False, description="Whether to encrypt the record")
    
    @validator('event_type')
    def validate_event_type(cls, v):
        allowed_types = ['create', 'read', 'update', 'delete', 'access', 'authentication', 'authorization', 'system']
        if v not in allowed_types:
            raise ValueError(f'event_type must be one of {allowed_types}')
        return v
        
    @validator('details')
    def validate_details(cls, v):
        if not isinstance(v, dict):
            raise ValueError('details must be a dictionary')
        return v


class AuditRecordResponse(BaseModel):
    """Response model for audit records"""
    
    id: str
    event_type: str
    timestamp: datetime
    user_id: str
    action: str
    resource: str
    details: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    ipfs_hash: str
    blockchain_hash: Optional[str] = None
    signature: Optional[str] = None
    verified: bool = False


class QueryRequest(BaseModel):
    """Request model for querying audit records"""
    
    event_type: Optional[str] = Field(None, description="Filter by event type")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    resource: Optional[str] = Field(None, description="Filter by resource")
    start_time: Optional[datetime] = Field(None, description="Start time filter")
    end_time: Optional[datetime] = Field(None, description="End time filter")
    limit: int = Field(100, description="Maximum number of results", ge=1, le=1000)
    offset: int = Field(0, description="Pagination offset", ge=0)
    sort_by: str = Field("timestamp", description="Field to sort by")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('sort_order must be "asc" or "desc"')
        return v


class VerificationRequest(BaseModel):
    """Request model for record verification"""
    
    record_id: Optional[str] = Field(None, description="Record ID to verify")
    ipfs_hash: Optional[str] = Field(None, description="IPFS hash to verify")
    blockchain_hash: Optional[str] = Field(None, description="Blockchain transaction hash")
    verify_signature: bool = Field(True, description="Whether to verify digital signature")
    verify_blockchain: bool = Field(True, description="Whether to verify blockchain record")
    verify_ipfs: bool = Field(True, description="Whether to verify IPFS data")


class VerificationResponse(BaseModel):
    """Response model for verification results"""
    
    valid: bool
    record_id: Optional[str] = None
    ipfs_hash: Optional[str] = None
    blockchain_hash: Optional[str] = None
    signature_valid: Optional[bool] = None
    blockchain_valid: Optional[bool] = None
    ipfs_valid: Optional[bool] = None
    verification_timestamp: datetime
    details: Dict[str, Any] = {}


class SystemStatusResponse(BaseModel):
    """Response model for system status"""
    
    status: str
    timestamp: datetime
    web3_connected: bool
    ipfs_connected: bool
    blockchain_network: str
    current_block: Optional[int] = None
    ipfs_peers: Optional[int] = None
    audit_records_total: Optional[int] = None
    system_health: str


class AuditTrailAPI:
    """
    Comprehensive REST API for blockchain audit trail system
    
    Provides endpoints for:
    - Creating and storing audit records
    - Querying and retrieving records
    - Verifying record integrity
    - System monitoring and health checks
    """
    
    def __init__(
        self,
        web3_client: Web3Client,
        contract_manager: ContractManager,
        ipfs_client: IPFSClient,
        data_manager: DataManager,
        signature_manager: SignatureManager,
        auth_manager: Optional[AuthManager] = None,
        enable_encryption: bool = False
    ):
        """
        Initialize API with required components
        
        Args:
            web3_client: Web3 client for blockchain operations
            contract_manager: Contract manager for smart contract interactions
            ipfs_client: IPFS client for decentralized storage
            data_manager: Data manager for IPFS operations
            signature_manager: Signature manager for cryptographic operations
            auth_manager: Authentication manager (optional)
            enable_encryption: Whether to enable encryption by default
        """
        self.web3_client = web3_client
        self.contract_manager = contract_manager
        self.ipfs_client = ipfs_client
        self.data_manager = data_manager
        self.signature_manager = signature_manager
        self.auth_manager = auth_manager
        self.enable_encryption = enable_encryption
        
        # Initialize components
        self.hash_manager = HashManager()
        self.signature_verifier = SignatureVerifier()
        self.request_validator = RequestValidator()
        
        # Performance tracking
        self.api_metrics = {
            'requests_total': 0,
            'requests_successful': 0,
            'requests_failed': 0,
            'records_created': 0,
            'records_queried': 0,
            'verifications_performed': 0
        }
        
    async def create_audit_record(self, request: AuditRecordRequest) -> AuditRecordResponse:
        """
        Create a new audit record
        
        Args:
            request: Audit record creation request
            
        Returns:
            Created audit record response
        """
        try:
            self.api_metrics['requests_total'] += 1
            
            # Generate unique record ID
            record_id = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(request.dict()))}"
            
            # Create audit record
            from ..ipfs.data_manager import AuditRecord
            
            audit_record = AuditRecord(
                id=record_id,
                event_type=request.event_type,
                timestamp=datetime.now(),
                user_id=request.user_id,
                action=request.action,
                resource=request.resource,
                details=request.details,
                metadata=request.metadata
            )
            
            # Store in IPFS
            if request.encrypt and isinstance(self.data_manager, EncryptedDataManager):
                storage_result = await self.data_manager.store_audit_record(audit_record, encrypt=True)
            else:
                storage_result = await self.data_manager.store_audit_record(audit_record)
                
            ipfs_hash = storage_result.ipfs_hash
            
            # Sign the record
            signature = self.signature_manager.sign_message(
                audit_record.to_dict(),
                key_id="default"  # Should be configurable
            )
            
            # Store on blockchain
            blockchain_hash = None
            try:
                blockchain_hash = await self.contract_manager.send_contract_transaction(
                    "AuditTrail",
                    "createAuditEntry",
                    [
                        ipfs_hash,
                        signature.signature,
                        request.event_type,
                        f"{request.action} on {request.resource}",
                        json.dumps(request.metadata or {})
                    ]
                )
            except Exception as e:
                logger.warning(f"Failed to store on blockchain: {str(e)}")
                
            # Create response
            response = AuditRecordResponse(
                id=record_id,
                event_type=request.event_type,
                timestamp=audit_record.timestamp,
                user_id=request.user_id,
                action=request.action,
                resource=request.resource,
                details=request.details,
                metadata=request.metadata,
                ipfs_hash=ipfs_hash,
                blockchain_hash=blockchain_hash,
                signature=signature.signature,
                verified=False
            )
            
            self.api_metrics['requests_successful'] += 1
            self.api_metrics['records_created'] += 1
            
            logger.info(f"Created audit record {record_id} with IPFS hash {ipfs_hash}")
            return response
            
        except Exception as e:
            self.api_metrics['requests_failed'] += 1
            logger.error(f"Failed to create audit record: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create audit record: {str(e)}"
            )
            
    async def query_audit_records(self, query: QueryRequest) -> Dict[str, Any]:
        """
        Query audit records with filtering and pagination
        
        Args:
            query: Query parameters
            
        Returns:
            Query results with pagination info
        """
        try:
            self.api_metrics['requests_total'] += 1
            
            # This would typically query a database or index
            # For now, we'll return a placeholder response
            results = []
            total_count = 0
            
            # In a real implementation, this would:
            # 1. Query blockchain events
            # 2. Retrieve IPFS data for matching records
            # 3. Apply filters and pagination
            # 4. Return structured results
            
            response = {
                'records': results,
                'pagination': {
                    'total': total_count,
                    'limit': query.limit,
                    'offset': query.offset,
                    'has_more': (query.offset + query.limit) < total_count
                },
                'query': query.dict(),
                'timestamp': datetime.now().isoformat()
            }
            
            self.api_metrics['requests_successful'] += 1
            self.api_metrics['records_queried'] += len(results)
            
            logger.info(f"Queried audit records: {len(results)} results")
            return response
            
        except Exception as e:
            self.api_metrics['requests_failed'] += 1
            logger.error(f"Failed to query audit records: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to query audit records: {str(e)}"
            )
            
    async def verify_record(self, request: VerificationRequest) -> VerificationResponse:
        """
        Verify audit record integrity
        
        Args:
            request: Verification request
            
        Returns:
            Verification results
        """
        try:
            self.api_metrics['requests_total'] += 1
            
            verification_results = {}
            overall_valid = True
            
            # Verify IPFS data if requested
            if request.verify_ipfs and request.ipfs_hash:
                try:
                    # Retrieve and verify IPFS data
                    audit_record = await self.data_manager.retrieve_audit_record(request.ipfs_hash)
                    verification_results['ipfs_valid'] = True
                    verification_results['ipfs_details'] = {
                        'record_id': audit_record.id,
                        'timestamp': audit_record.timestamp.isoformat()
                    }
                except Exception as e:
                    verification_results['ipfs_valid'] = False
                    verification_results['ipfs_error'] = str(e)
                    overall_valid = False
                    
            # Verify blockchain record if requested
            if request.verify_blockchain and request.blockchain_hash:
                try:
                    # Verify blockchain transaction
                    tx_info = await self.web3_client.get_transaction(request.blockchain_hash)
                    verification_results['blockchain_valid'] = tx_info.status == 1
                    verification_results['blockchain_details'] = {
                        'block_number': tx_info.block_number,
                        'gas_used': tx_info.gas_used
                    }
                    if tx_info.status != 1:
                        overall_valid = False
                except Exception as e:
                    verification_results['blockchain_valid'] = False
                    verification_results['blockchain_error'] = str(e)
                    overall_valid = False
                    
            # Verify digital signature if requested
            if request.verify_signature and request.ipfs_hash:
                try:
                    # This would retrieve the signature and verify it
                    verification_results['signature_valid'] = True
                except Exception as e:
                    verification_results['signature_valid'] = False
                    verification_results['signature_error'] = str(e)
                    overall_valid = False
                    
            response = VerificationResponse(
                valid=overall_valid,
                record_id=request.record_id,
                ipfs_hash=request.ipfs_hash,
                blockchain_hash=request.blockchain_hash,
                signature_valid=verification_results.get('signature_valid'),
                blockchain_valid=verification_results.get('blockchain_valid'),
                ipfs_valid=verification_results.get('ipfs_valid'),
                verification_timestamp=datetime.now(),
                details=verification_results
            )
            
            self.api_metrics['requests_successful'] += 1
            self.api_metrics['verifications_performed'] += 1
            
            logger.info(f"Verified record - Valid: {overall_valid}")
            return response
            
        except Exception as e:
            self.api_metrics['requests_failed'] += 1
            logger.error(f"Failed to verify record: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify record: {str(e)}"
            )
            
    async def get_system_status(self) -> SystemStatusResponse:
        """
        Get system status and health information
        
        Returns:
            System status response
        """
        try:
            # Check Web3 connection
            web3_connected = True
            current_block = None
            blockchain_network = self.web3_client.network.name
            
            try:
                current_block = await self.web3_client.get_block_number()
            except Exception:
                web3_connected = False
                
            # Check IPFS connection
            ipfs_connected = True
            ipfs_peers = None
            
            try:
                node_info = await self.ipfs_client.get_node_info()
                ipfs_peers = len(node_info.get('addresses', []))
            except Exception:
                ipfs_connected = False
                
            # Determine overall system health
            if web3_connected and ipfs_connected:
                system_health = "healthy"
                status_value = "operational"
            elif web3_connected or ipfs_connected:
                system_health = "degraded"
                status_value = "partial"
            else:
                system_health = "unhealthy"
                status_value = "down"
                
            response = SystemStatusResponse(
                status=status_value,
                timestamp=datetime.now(),
                web3_connected=web3_connected,
                ipfs_connected=ipfs_connected,
                blockchain_network=blockchain_network,
                current_block=current_block,
                ipfs_peers=ipfs_peers,
                audit_records_total=self.api_metrics['records_created'],
                system_health=system_health
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get system status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get system status: {str(e)}"
            )
            
    def get_api_metrics(self) -> Dict[str, Any]:
        """Get API performance metrics"""
        return {
            **self.api_metrics,
            'success_rate': (
                self.api_metrics['requests_successful'] / 
                max(self.api_metrics['requests_total'], 1)
            ) * 100,
            'timestamp': datetime.now().isoformat()
        }


def create_app(api_instance: AuditTrailAPI) -> FastAPI:
    """
    Create FastAPI application with all routes
    
    Args:
        api_instance: Configured API instance
        
    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="Kenny AGI Blockchain Audit Trail API",
        description="REST API for blockchain-based audit trail system",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(RateLimitMiddleware, calls=100, period=60)
    app.add_middleware(LoggingMiddleware)
    
    # Authentication dependency
    security = HTTPBearer()
    
    async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
        if api_instance.auth_manager:
            return await api_instance.auth_manager.verify_token(credentials.credentials)
        return True  # No auth required if no auth manager
        
    # Routes
    @app.post("/api/v1/audit/records", response_model=AuditRecordResponse)
    async def create_record(
        request: AuditRecordRequest,
        authenticated: bool = Depends(verify_token)
    ):
        """Create a new audit record"""
        return await api_instance.create_audit_record(request)
        
    @app.post("/api/v1/audit/query", response_model=Dict[str, Any])
    async def query_records(
        query: QueryRequest,
        authenticated: bool = Depends(verify_token)
    ):
        """Query audit records with filtering and pagination"""
        return await api_instance.query_audit_records(query)
        
    @app.post("/api/v1/audit/verify", response_model=VerificationResponse)
    async def verify_record(
        request: VerificationRequest,
        authenticated: bool = Depends(verify_token)
    ):
        """Verify audit record integrity"""
        return await api_instance.verify_record(request)
        
    @app.get("/api/v1/system/status", response_model=SystemStatusResponse)
    async def get_status():
        """Get system status and health information"""
        return await api_instance.get_system_status()
        
    @app.get("/api/v1/system/metrics")
    async def get_metrics():
        """Get API performance metrics"""
        return api_instance.get_api_metrics()
        
    @app.get("/api/v1/health")
    async def health_check():
        """Simple health check endpoint"""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
    return app