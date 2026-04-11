"""
SingularityNET Compatibility and Integration
===========================================

Integration layer for compatibility with SingularityNET ecosystem,
enabling AGI services to be published, discovered, and consumed
through the SingularityNET marketplace and protocol.
"""

import asyncio
import json
import hashlib
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
import uuid
import base64

from .core import CommunicationMessage, MessageType

logger = logging.getLogger(__name__)

class ServiceCategory(Enum):
    """SingularityNET service categories."""
    AI_TRAINING = "ai_training"
    COMPUTER_VISION = "computer_vision"
    NATURAL_LANGUAGE = "natural_language"
    SPEECH_RECOGNITION = "speech_recognition"
    MACHINE_TRANSLATION = "machine_translation"
    DATA_ANALYTICS = "data_analytics"
    RECOMMENDATION = "recommendation"
    OPTIMIZATION = "optimization"
    SIMULATION = "simulation"
    ROBOTICS = "robotics"
    BLOCKCHAIN = "blockchain"
    BIOINFORMATICS = "bioinformatics"

class PaymentChannel(Enum):
    """Payment channel states."""
    OPENING = "opening"
    ACTIVE = "active"
    CHALLENGED = "challenged"
    CLOSING = "closing"
    CLOSED = "closed"

@dataclass
class SGTToken:
    """SingularityNET token representation."""
    amount: int  # Amount in cogs (10^-8 AGI)
    channel_id: str
    nonce: int
    signature: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'amount': self.amount,
            'channel_id': self.channel_id,
            'nonce': self.nonce,
            'signature': self.signature
        }

@dataclass
class ServiceMetadata:
    """Service metadata for SingularityNET registration."""
    service_id: str
    organization_id: str
    service_name: str
    service_description: str
    service_category: ServiceCategory
    version: str
    price_per_call: int  # In cogs
    endpoints: List[Dict[str, str]]
    encoding: str = "proto"
    service_type: str = "grpc"
    model_ipfs_hash: str = ""
    mpe_address: str = ""  # Multi-Party Escrow address
    groups: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_proto_metadata(self) -> Dict[str, Any]:
        """Convert to protobuf-compatible metadata."""
        return {
            'version': 1,
            'display_name': self.service_name,
            'encoding': self.encoding,
            'service_type': self.service_type,
            'model_ipfs_hash': self.model_ipfs_hash,
            'mpe_address': self.mpe_address,
            'pricing': {
                'price_model': 'fixed_price',
                'price_in_cogs': self.price_per_call
            },
            'groups': self.groups or [{
                'group_name': 'default_group',
                'group_id': base64.b64encode(self.service_id.encode()).decode(),
                'pricing': [{
                    'default': True,
                    'price_in_cogs': self.price_per_call,
                    'method_pricing': []
                }]
            }],
            'endpoints': self.endpoints,
            'service_description': {
                'description': self.service_description,
                'url': '',
                'json': '{}',
                'model_ipfs_hash': self.model_ipfs_hash
            }
        }

@dataclass
class PaymentChannelInfo:
    """Payment channel information."""
    channel_id: str
    sender: str
    recipient: str
    value: int  # Total channel value in cogs
    nonce: int
    expiration: int  # Block number
    signer: str
    signature: str
    state: PaymentChannel = PaymentChannel.ACTIVE
    
    def is_expired(self, current_block: int) -> bool:
        """Check if channel is expired."""
        return current_block >= self.expiration

@dataclass
class ServiceCall:
    """Represents a service call in SingularityNET."""
    call_id: str
    service_id: str
    method_name: str
    input_data: Any
    payment_channel: PaymentChannelInfo
    payment_amount: int
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, processing, completed, failed
    result: Any = None
    error: Optional[str] = None

class IPFSConnector:
    """Connector for IPFS operations."""
    
    def __init__(self, ipfs_endpoint: str = "http://localhost:5001"):
        self.ipfs_endpoint = ipfs_endpoint
        self.pinned_hashes: Set[str] = set()
    
    async def add_content(self, content: Union[str, bytes, Dict]) -> str:
        """Add content to IPFS and return hash."""
        # Simplified IPFS implementation
        # In production, this would use actual IPFS API
        
        if isinstance(content, dict):
            content = json.dumps(content, sort_keys=True)
        elif isinstance(content, str):
            content = content.encode('utf-8')
        
        # Create hash (simplified)
        hash_obj = hashlib.sha256(content)
        ipfs_hash = f"Qm{base64.b32encode(hash_obj.digest()).decode().lower()[:44]}"
        
        # In real implementation, would upload to IPFS
        logger.info(f"Added content to IPFS: {ipfs_hash}")
        
        return ipfs_hash
    
    async def get_content(self, ipfs_hash: str) -> Optional[bytes]:
        """Retrieve content from IPFS."""
        # Simplified implementation
        # In production, would retrieve from IPFS network
        logger.info(f"Retrieved content from IPFS: {ipfs_hash}")
        return b'{"mock": "ipfs_content"}'
    
    async def pin_content(self, ipfs_hash: str):
        """Pin content to prevent garbage collection."""
        self.pinned_hashes.add(ipfs_hash)
        logger.info(f"Pinned IPFS content: {ipfs_hash}")

class EthereumConnector:
    """Connector for Ethereum blockchain operations."""
    
    def __init__(self, network: str = "mainnet", private_key: Optional[str] = None):
        self.network = network
        self.private_key = private_key
        self.contract_addresses = {
            'registry': '0x663422c6999ff94933dbcb388623952cf2407f6f',
            'mpe': '0x62ad5fc87986a1c2323a13b299170af6fbb3b3df',
            'agi_token': '0x8eb24319393716668d768dcec29356ae9cffe285'
        }
        
        # Mock blockchain state
        self.mock_services = {}
        self.mock_channels = {}
        self.mock_balances = {}
        self.current_block = 15000000
    
    async def register_service(self, metadata: ServiceMetadata) -> str:
        """Register service on SingularityNET registry."""
        # Create service registration transaction
        service_key = f"{metadata.organization_id}_{metadata.service_id}"
        
        # Convert metadata to IPFS hash
        ipfs_hash = await self._upload_metadata_to_ipfs(metadata)
        
        # Mock blockchain registration
        self.mock_services[service_key] = {
            'metadata_hash': ipfs_hash,
            'organization': metadata.organization_id,
            'service_id': metadata.service_id,
            'price': metadata.price_per_call,
            'registered_at': self.current_block
        }
        
        logger.info(f"Registered service {service_key} on SingularityNET")
        return service_key
    
    async def update_service_metadata(self, service_key: str, metadata: ServiceMetadata) -> bool:
        """Update service metadata."""
        if service_key not in self.mock_services:
            return False
        
        ipfs_hash = await self._upload_metadata_to_ipfs(metadata)
        self.mock_services[service_key]['metadata_hash'] = ipfs_hash
        self.mock_services[service_key]['updated_at'] = self.current_block
        
        return True
    
    async def create_payment_channel(self, recipient: str, value: int, expiration: int) -> PaymentChannelInfo:
        """Create payment channel."""
        channel_id = str(uuid.uuid4())
        
        channel_info = PaymentChannelInfo(
            channel_id=channel_id,
            sender="0x" + "0" * 38 + "sender",  # Mock address
            recipient=recipient,
            value=value,
            nonce=0,
            expiration=expiration,
            signer="0x" + "0" * 38 + "signer",
            signature="0x" + "0" * 128  # Mock signature
        )
        
        self.mock_channels[channel_id] = channel_info
        
        logger.info(f"Created payment channel {channel_id} with value {value} cogs")
        return channel_info
    
    async def close_payment_channel(self, channel_id: str) -> bool:
        """Close payment channel."""
        if channel_id in self.mock_channels:
            self.mock_channels[channel_id].state = PaymentChannel.CLOSING
            logger.info(f"Closed payment channel {channel_id}")
            return True
        return False
    
    async def get_agi_balance(self, address: str) -> int:
        """Get AGI token balance."""
        return self.mock_balances.get(address, 1000000)  # Mock 1M cogs balance
    
    async def _upload_metadata_to_ipfs(self, metadata: ServiceMetadata) -> str:
        """Upload service metadata to IPFS."""
        # This would use the IPFSConnector in production
        proto_metadata = metadata.to_proto_metadata()
        content = json.dumps(proto_metadata)
        
        # Mock IPFS hash
        hash_input = f"{metadata.service_id}_{metadata.version}_{content}"
        hash_obj = hashlib.sha256(hash_input.encode())
        return f"Qm{base64.b32encode(hash_obj.digest()).decode().lower()[:44]}"

class SingularityNetIntegration:
    """
    SingularityNET Compatibility and Integration Layer
    
    Provides full integration with the SingularityNET ecosystem,
    enabling AGI services to participate in the decentralized
    AI marketplace.
    """
    
    def __init__(self, protocol, organization_id: str = "kenny_agi_org"):
        self.protocol = protocol
        self.organization_id = organization_id
        self.ipfs_connector = IPFSConnector()
        self.ethereum_connector = EthereumConnector()
        
        # Service management
        self.registered_services: Dict[str, ServiceMetadata] = {}
        self.active_channels: Dict[str, PaymentChannelInfo] = {}
        self.service_calls: Dict[str, ServiceCall] = {}
        
        # Integration history
        self.integration_history: List[Dict[str, Any]] = []
        
        # Initialize default services
        self._initialize_default_services()
    
    def _initialize_default_services(self):
        """Initialize default AGI services for SingularityNET."""
        # Reasoning service
        reasoning_service = ServiceMetadata(
            service_id="agi_reasoning",
            organization_id=self.organization_id,
            service_name="AGI Reasoning Service",
            service_description="Advanced reasoning and inference capabilities",
            service_category=ServiceCategory.AI_TRAINING,
            version="1.0.0",
            price_per_call=100,  # 100 cogs per call
            endpoints=[{
                "endpoint": f"https://services.{self.organization_id}.io/reasoning",
                "group_name": "default_group"
            }]
        )
        
        # Knowledge processing service
        knowledge_service = ServiceMetadata(
            service_id="knowledge_processing",
            organization_id=self.organization_id,
            service_name="Knowledge Graph Processing",
            service_description="Knowledge graph creation, merging, and reasoning",
            service_category=ServiceCategory.DATA_ANALYTICS,
            version="1.0.0",
            price_per_call=150,
            endpoints=[{
                "endpoint": f"https://services.{self.organization_id}.io/knowledge",
                "group_name": "default_group"
            }]
        )
        
        # Communication translation service
        translation_service = ServiceMetadata(
            service_id="cognitive_translation",
            organization_id=self.organization_id,
            service_name="Cognitive Architecture Translation",
            service_description="Translation between different cognitive architectures",
            service_category=ServiceCategory.MACHINE_TRANSLATION,
            version="1.0.0",
            price_per_call=200,
            endpoints=[{
                "endpoint": f"https://services.{self.organization_id}.io/translation",
                "group_name": "default_group"
            }]
        )
        
        # Store services
        self.registered_services.update({
            reasoning_service.service_id: reasoning_service,
            knowledge_service.service_id: knowledge_service,
            translation_service.service_id: translation_service
        })
    
    async def register_service_on_network(self, service_metadata: ServiceMetadata) -> str:
        """Register service on SingularityNET."""
        try:
            # Upload service metadata to IPFS
            metadata_dict = service_metadata.to_proto_metadata()
            ipfs_hash = await self.ipfs_connector.add_content(metadata_dict)
            service_metadata.model_ipfs_hash = ipfs_hash
            
            # Register on Ethereum registry
            service_key = await self.ethereum_connector.register_service(service_metadata)
            
            # Store locally
            self.registered_services[service_metadata.service_id] = service_metadata
            
            # Record registration
            self._record_integration_event("service_registered", {
                'service_id': service_metadata.service_id,
                'service_key': service_key,
                'ipfs_hash': ipfs_hash
            })
            
            logger.info(f"Successfully registered service {service_metadata.service_id} on SingularityNET")
            return service_key
            
        except Exception as e:
            logger.error(f"Error registering service: {e}")
            raise
    
    async def update_service_metadata(self, service_id: str, new_metadata: ServiceMetadata) -> bool:
        """Update service metadata on SingularityNET."""
        if service_id not in self.registered_services:
            raise ValueError(f"Service {service_id} not registered")
        
        try:
            # Upload new metadata to IPFS
            metadata_dict = new_metadata.to_proto_metadata()
            ipfs_hash = await self.ipfs_connector.add_content(metadata_dict)
            new_metadata.model_ipfs_hash = ipfs_hash
            
            # Update on Ethereum
            service_key = f"{new_metadata.organization_id}_{service_id}"
            success = await self.ethereum_connector.update_service_metadata(service_key, new_metadata)
            
            if success:
                self.registered_services[service_id] = new_metadata
                self._record_integration_event("service_updated", {
                    'service_id': service_id,
                    'new_ipfs_hash': ipfs_hash
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating service metadata: {e}")
            return False
    
    async def create_payment_channel(self, recipient_address: str, value_cogs: int, 
                                   expiration_blocks: int = 1000) -> PaymentChannelInfo:
        """Create payment channel for service payments."""
        current_block = self.ethereum_connector.current_block
        expiration = current_block + expiration_blocks
        
        channel_info = await self.ethereum_connector.create_payment_channel(
            recipient_address, value_cogs, expiration
        )
        
        self.active_channels[channel_info.channel_id] = channel_info
        
        self._record_integration_event("payment_channel_created", {
            'channel_id': channel_info.channel_id,
            'value': value_cogs,
            'expiration': expiration
        })
        
        return channel_info
    
    async def call_service(self, service_id: str, method_name: str, 
                         input_data: Any, payment_channel_id: str,
                         payment_amount: int) -> ServiceCall:
        """Call a service on SingularityNET."""
        if payment_channel_id not in self.active_channels:
            raise ValueError(f"Payment channel {payment_channel_id} not found")
        
        channel = self.active_channels[payment_channel_id]
        if channel.state != PaymentChannel.ACTIVE:
            raise ValueError(f"Payment channel {payment_channel_id} not active")
        
        # Create service call
        call_id = str(uuid.uuid4())
        service_call = ServiceCall(
            call_id=call_id,
            service_id=service_id,
            method_name=method_name,
            input_data=input_data,
            payment_channel=channel,
            payment_amount=payment_amount
        )
        
        self.service_calls[call_id] = service_call
        
        try:
            # Execute service call (mock implementation)
            result = await self._execute_service_call(service_call)
            
            service_call.result = result
            service_call.status = "completed"
            
            # Update payment channel nonce
            channel.nonce += 1
            
            self._record_integration_event("service_called", {
                'call_id': call_id,
                'service_id': service_id,
                'payment_amount': payment_amount,
                'success': True
            })
            
        except Exception as e:
            service_call.error = str(e)
            service_call.status = "failed"
            
            self._record_integration_event("service_call_failed", {
                'call_id': call_id,
                'service_id': service_id,
                'error': str(e)
            })
        
        return service_call
    
    async def _execute_service_call(self, service_call: ServiceCall) -> Any:
        """Execute service call (mock implementation)."""
        # This would contain actual service execution logic
        service_id = service_call.service_id
        method_name = service_call.method_name
        input_data = service_call.input_data
        
        # Mock service responses
        if service_id == "agi_reasoning":
            if method_name == "infer":
                return {
                    "conclusion": f"inferred_result_for_{input_data}",
                    "confidence": 0.85,
                    "reasoning_chain": ["premise1", "rule1", "conclusion"]
                }
        
        elif service_id == "knowledge_processing":
            if method_name == "process_graph":
                return {
                    "processed_graph": {
                        "nodes": ["node1", "node2"],
                        "edges": ["edge1"],
                        "insights": ["insight1", "insight2"]
                    },
                    "statistics": {"nodes": 2, "edges": 1}
                }
        
        elif service_id == "cognitive_translation":
            if method_name == "translate":
                return {
                    "translated_content": f"translated_{input_data}",
                    "source_architecture": "neural",
                    "target_architecture": "symbolic",
                    "confidence": 0.9
                }
        
        # Default response
        return {"result": f"processed_{input_data}", "service": service_id}
    
    async def provide_service(self, service_call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide service execution for incoming calls."""
        service_id = service_call_data.get('service_id')
        method_name = service_call_data.get('method_name')
        input_data = service_call_data.get('input_data')
        
        if service_id not in self.registered_services:
            raise ValueError(f"Service {service_id} not available")
        
        # Validate payment (simplified)
        payment_info = service_call_data.get('payment')
        if not payment_info:
            raise ValueError("Payment information required")
        
        # Execute service
        try:
            service_call = ServiceCall(
                call_id=str(uuid.uuid4()),
                service_id=service_id,
                method_name=method_name,
                input_data=input_data,
                payment_channel=None,  # Would be properly set in production
                payment_amount=payment_info.get('amount', 0)
            )
            
            result = await self._execute_service_call(service_call)
            
            return {
                "success": True,
                "result": result,
                "call_id": service_call.call_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def discover_services(self, category: Optional[ServiceCategory] = None,
                              search_terms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Discover services on SingularityNET."""
        # Mock service discovery
        discovered_services = []
        
        # Add some mock external services
        external_services = [
            {
                'service_id': 'external_nlp_service',
                'organization_id': 'nlp_org',
                'service_name': 'Advanced NLP Processing',
                'category': ServiceCategory.NATURAL_LANGUAGE.value,
                'price_per_call': 50,
                'description': 'Advanced natural language processing and understanding'
            },
            {
                'service_id': 'cv_recognition',
                'organization_id': 'vision_org', 
                'service_name': 'Computer Vision Recognition',
                'category': ServiceCategory.COMPUTER_VISION.value,
                'price_per_call': 75,
                'description': 'Object detection and image classification'
            },
            {
                'service_id': 'optimization_solver',
                'organization_id': 'opt_org',
                'service_name': 'Optimization Solver',
                'category': ServiceCategory.OPTIMIZATION.value,
                'price_per_call': 200,
                'description': 'Solve complex optimization problems'
            }
        ]
        
        # Filter by category if specified
        if category:
            external_services = [s for s in external_services if s['category'] == category.value]
        
        # Filter by search terms if specified
        if search_terms:
            filtered_services = []
            for service in external_services:
                service_text = f"{service['service_name']} {service['description']}".lower()
                if any(term.lower() in service_text for term in search_terms):
                    filtered_services.append(service)
            external_services = filtered_services
        
        discovered_services.extend(external_services)
        
        self._record_integration_event("services_discovered", {
            'count': len(discovered_services),
            'category': category.value if category else 'all',
            'search_terms': search_terms or []
        })
        
        return discovered_services
    
    async def get_service_metadata(self, organization_id: str, service_id: str) -> Optional[Dict[str, Any]]:
        """Get service metadata from SingularityNET."""
        service_key = f"{organization_id}_{service_id}"
        
        # Check local services first
        if service_id in self.registered_services:
            metadata = self.registered_services[service_id]
            return metadata.to_proto_metadata()
        
        # Mock external service metadata retrieval
        if service_key in self.ethereum_connector.mock_services:
            service_info = self.ethereum_connector.mock_services[service_key]
            ipfs_hash = service_info['metadata_hash']
            
            # Retrieve metadata from IPFS
            metadata_content = await self.ipfs_connector.get_content(ipfs_hash)
            if metadata_content:
                return json.loads(metadata_content.decode('utf-8'))
        
        return None
    
    def _record_integration_event(self, event_type: str, event_data: Dict[str, Any]):
        """Record integration event for monitoring."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'event_data': event_data
        }
        
        self.integration_history.append(event)
        
        # Keep history limited
        if len(self.integration_history) > 1000:
            self.integration_history = self.integration_history[-800:]
    
    async def handle_singularitynet_message(self, message: CommunicationMessage):
        """Handle SingularityNET-related messages."""
        payload = message.payload
        action = payload.get('action')
        
        try:
            if action == 'service_call':
                await self._handle_service_call_request(message)
            elif action == 'service_discovery':
                await self._handle_service_discovery_request(message)
            elif action == 'payment_channel_request':
                await self._handle_payment_channel_request(message)
            else:
                logger.warning(f"Unknown SingularityNET action: {action}")
                
        except Exception as e:
            logger.error(f"Error handling SingularityNET message: {e}")
    
    async def _handle_service_call_request(self, message: CommunicationMessage):
        """Handle service call request."""
        payload = message.payload
        
        result = await self.provide_service(payload.get('service_call_data', {}))
        
        response_message = CommunicationMessage(
            id=str(uuid.uuid4()),
            sender_id=self.protocol.identity.id,
            receiver_id=message.sender_id,
            message_type=MessageType.CAPABILITY_RESPONSE,
            timestamp=datetime.now(),
            payload={
                'action': 'service_call_response',
                'original_message_id': message.id,
                'result': result
            }
        )
        
        await self.protocol.send_message(response_message)
    
    async def _handle_service_discovery_request(self, message: CommunicationMessage):
        """Handle service discovery request."""
        payload = message.payload
        category = payload.get('category')
        search_terms = payload.get('search_terms')
        
        if category:
            category = ServiceCategory(category)
        
        services = await self.discover_services(category, search_terms)
        
        response_message = CommunicationMessage(
            id=str(uuid.uuid4()),
            sender_id=self.protocol.identity.id,
            receiver_id=message.sender_id,
            message_type=MessageType.CAPABILITY_RESPONSE,
            timestamp=datetime.now(),
            payload={
                'action': 'service_discovery_response',
                'original_message_id': message.id,
                'services': services
            }
        )
        
        await self.protocol.send_message(response_message)
    
    async def _handle_payment_channel_request(self, message: CommunicationMessage):
        """Handle payment channel creation request."""
        payload = message.payload
        recipient = payload.get('recipient')
        value = payload.get('value', 1000)
        
        try:
            channel_info = await self.create_payment_channel(recipient, value)
            
            response_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=message.sender_id,
                message_type=MessageType.CAPABILITY_RESPONSE,
                timestamp=datetime.now(),
                payload={
                    'action': 'payment_channel_response',
                    'original_message_id': message.id,
                    'success': True,
                    'channel_info': {
                        'channel_id': channel_info.channel_id,
                        'value': channel_info.value,
                        'expiration': channel_info.expiration
                    }
                }
            )
            
        except Exception as e:
            response_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=message.sender_id,
                message_type=MessageType.CAPABILITY_RESPONSE,
                timestamp=datetime.now(),
                payload={
                    'action': 'payment_channel_response',
                    'original_message_id': message.id,
                    'success': False,
                    'error': str(e)
                }
            )
        
        await self.protocol.send_message(response_message)
    
    def get_integration_statistics(self) -> Dict[str, Any]:
        """Get SingularityNET integration statistics."""
        return {
            'registered_services': len(self.registered_services),
            'active_payment_channels': len(self.active_channels),
            'completed_service_calls': len([c for c in self.service_calls.values() if c.status == 'completed']),
            'failed_service_calls': len([c for c in self.service_calls.values() if c.status == 'failed']),
            'total_integration_events': len(self.integration_history),
            'organization_id': self.organization_id,
            'service_categories': list(set(s.service_category.value for s in self.registered_services.values()))
        }