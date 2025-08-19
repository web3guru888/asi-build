"""
P2P Node Discovery and Coordination System
Implements decentralized node discovery using DHT and gossip protocols
"""

import asyncio
import logging
import hashlib
import time
import json
import socket
import random
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
import aiohttp
import aiodns
from collections import defaultdict
import struct
import ipaddress

@dataclass
class PeerInfo:
    """Information about a peer node"""
    peer_id: str
    ip_address: str
    port: int
    public_key: str
    capabilities: Dict[str, Any]
    last_seen: float
    reputation: float
    is_bootstrap: bool
    version: str
    network_id: str

@dataclass
class NetworkMessage:
    """P2P network message"""
    message_id: str
    message_type: str
    sender_id: str
    recipient_id: Optional[str]  # None for broadcast
    payload: Dict[str, Any]
    timestamp: float
    ttl: int
    signature: Optional[str]

class DistributedHashTable:
    """Simplified Kademlia-style DHT for peer discovery"""
    
    def __init__(self, node_id: str, k_bucket_size: int = 20):
        self.node_id = node_id
        self.k_bucket_size = k_bucket_size
        self.routing_table: Dict[int, List[PeerInfo]] = {}
        self.storage: Dict[str, Any] = {}
        
        # Initialize routing table with empty buckets
        for i in range(160):  # 160 bits for SHA-1 based node IDs
            self.routing_table[i] = []
        
        self.logger = logging.getLogger(__name__)
    
    def _xor_distance(self, id1: str, id2: str) -> int:
        """Calculate XOR distance between two node IDs"""
        bytes1 = bytes.fromhex(id1)
        bytes2 = bytes.fromhex(id2)
        
        distance = 0
        for b1, b2 in zip(bytes1, bytes2):
            distance = (distance << 8) | (b1 ^ b2)
        
        return distance
    
    def _get_bucket_index(self, peer_id: str) -> int:
        """Get routing table bucket index for a peer"""
        distance = self._xor_distance(self.node_id, peer_id)
        
        if distance == 0:
            return 0
        
        # Find the position of the most significant bit
        return distance.bit_length() - 1
    
    def add_peer(self, peer: PeerInfo) -> bool:
        """Add peer to routing table"""
        if peer.peer_id == self.node_id:
            return False
        
        bucket_index = self._get_bucket_index(peer.peer_id)
        bucket = self.routing_table[bucket_index]
        
        # Check if peer already exists
        for i, existing_peer in enumerate(bucket):
            if existing_peer.peer_id == peer.peer_id:
                bucket[i] = peer  # Update existing peer
                return True
        
        # Add new peer if bucket has space
        if len(bucket) < self.k_bucket_size:
            bucket.append(peer)
            self.logger.debug(f"Added peer {peer.peer_id[:8]}... to bucket {bucket_index}")
            return True
        
        # Bucket is full - implement LRU replacement
        # For simplicity, replace the oldest peer
        oldest_peer = min(bucket, key=lambda p: p.last_seen)
        if peer.last_seen > oldest_peer.last_seen:
            bucket.remove(oldest_peer)
            bucket.append(peer)
            return True
        
        return False
    
    def find_closest_peers(self, target_id: str, count: int = 20) -> List[PeerInfo]:
        """Find closest peers to target ID"""
        all_peers = []
        for bucket in self.routing_table.values():
            all_peers.extend(bucket)
        
        # Sort by XOR distance to target
        all_peers.sort(key=lambda p: self._xor_distance(p.peer_id, target_id))
        
        return all_peers[:count]
    
    def store(self, key: str, value: Any) -> bool:
        """Store key-value pair in DHT"""
        self.storage[key] = {
            'value': value,
            'timestamp': time.time(),
            'ttl': 3600  # 1 hour TTL
        }
        return True
    
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve value from DHT"""
        if key in self.storage:
            item = self.storage[key]
            
            # Check TTL
            if time.time() - item['timestamp'] > item['ttl']:
                del self.storage[key]
                return None
            
            return item['value']
        
        return None
    
    def get_bucket_info(self) -> Dict[int, int]:
        """Get information about routing table buckets"""
        return {i: len(bucket) for i, bucket in self.routing_table.items() if bucket}

class GossipProtocol:
    """Gossip protocol for information dissemination"""
    
    def __init__(self, node_id: str, max_gossip_peers: int = 3):
        self.node_id = node_id
        self.max_gossip_peers = max_gossip_peers
        self.message_cache: Dict[str, NetworkMessage] = {}
        self.cache_ttl = 300  # 5 minutes
        
        self.logger = logging.getLogger(__name__)
    
    def should_gossip_message(self, message: NetworkMessage) -> bool:
        """Determine if message should be gossiped"""
        # Don't gossip expired messages
        if time.time() - message.timestamp > message.ttl:
            return False
        
        # Don't gossip messages we've already seen
        if message.message_id in self.message_cache:
            return False
        
        # Don't gossip direct messages
        if message.recipient_id is not None and message.recipient_id != self.node_id:
            return False
        
        return True
    
    def cache_message(self, message: NetworkMessage):
        """Cache message to prevent duplicate gossip"""
        self.message_cache[message.message_id] = message
        
        # Cleanup old messages
        current_time = time.time()
        expired_messages = [
            msg_id for msg_id, msg in self.message_cache.items()
            if current_time - msg.timestamp > self.cache_ttl
        ]
        
        for msg_id in expired_messages:
            del self.message_cache[msg_id]
    
    def select_gossip_peers(self, available_peers: List[PeerInfo]) -> List[PeerInfo]:
        """Select peers for gossiping"""
        # Randomly select peers, preferring higher reputation
        weighted_peers = [(peer, max(0.1, peer.reputation)) for peer in available_peers]
        
        selected = []
        while len(selected) < self.max_gossip_peers and weighted_peers:
            # Weighted random selection
            total_weight = sum(weight for _, weight in weighted_peers)
            r = random.uniform(0, total_weight)
            
            cumulative = 0
            for i, (peer, weight) in enumerate(weighted_peers):
                cumulative += weight
                if r <= cumulative:
                    selected.append(peer)
                    weighted_peers.pop(i)
                    break
        
        return selected

class P2PNetworkManager:
    """Main P2P network manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Node configuration
        self.node_id = config.get('node_id') or self._generate_node_id()
        self.listen_port = config.get('listen_port', 8080)
        self.public_ip = config.get('public_ip')
        self.network_id = config.get('network_id', 'kenny-agi-training')
        
        # P2P components
        self.dht = DistributedHashTable(self.node_id, config.get('k_bucket_size', 20))
        self.gossip = GossipProtocol(self.node_id, config.get('max_gossip_peers', 3))
        
        # Network state
        self.bootstrap_nodes: List[PeerInfo] = []
        self.connected_peers: Dict[str, PeerInfo] = {}
        self.message_handlers: Dict[str, callable] = {}
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'peers_discovered': 0,
            'connections_established': 0,
            'start_time': time.time()
        }
        
        self.running = False
        self.server = None
        
        self.logger = logging.getLogger(__name__)
    
    def _generate_node_id(self) -> str:
        """Generate unique node ID"""
        # Use MAC address + timestamp for uniqueness
        import uuid
        mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) 
                               for i in range(0, 48, 8)][::-1])
        
        id_input = f"{mac_address}:{time.time()}:{random.random()}"
        return hashlib.sha1(id_input.encode()).hexdigest()
    
    async def start(self, bootstrap_nodes: List[str] = None):
        """Start P2P network manager"""
        self.running = True
        
        # Discover public IP if not provided
        if not self.public_ip:
            self.public_ip = await self._discover_public_ip()
        
        # Start HTTP server for peer communication
        await self._start_http_server()
        
        # Load bootstrap nodes
        if bootstrap_nodes:
            await self._load_bootstrap_nodes(bootstrap_nodes)
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._peer_discovery_loop()),
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._maintenance_loop()),
        ]
        
        self.logger.info(f"P2P network started - Node ID: {self.node_id[:8]}...")
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.logger.info("P2P network tasks cancelled")
    
    async def stop(self):
        """Stop P2P network manager"""
        self.running = False
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        self.logger.info("P2P network stopped")
    
    async def _discover_public_ip(self) -> str:
        """Discover public IP address"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.ipify.org?format=json') as response:
                    data = await response.json()
                    return data['ip']
        except Exception as e:
            self.logger.warning(f"Failed to discover public IP: {e}")
            return '127.0.0.1'
    
    async def _start_http_server(self):
        """Start HTTP server for peer communication"""
        from aiohttp import web
        
        app = web.Application()
        app.router.add_post('/p2p/message', self._handle_http_message)
        app.router.add_get('/p2p/peers', self._handle_peer_list_request)
        app.router.add_post('/p2p/handshake', self._handle_handshake)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.listen_port)
        await site.start()
        
        self.logger.info(f"HTTP server started on port {self.listen_port}")
    
    async def _load_bootstrap_nodes(self, bootstrap_addresses: List[str]):
        """Load and connect to bootstrap nodes"""
        for address in bootstrap_addresses:
            try:
                ip, port = address.split(':')
                port = int(port)
                
                # Attempt handshake with bootstrap node
                peer_info = await self._perform_handshake(ip, port)
                if peer_info:
                    peer_info.is_bootstrap = True
                    self.bootstrap_nodes.append(peer_info)
                    self.dht.add_peer(peer_info)
                    
                    self.logger.info(f"Connected to bootstrap node: {ip}:{port}")
                
            except Exception as e:
                self.logger.warning(f"Failed to connect to bootstrap node {address}: {e}")
    
    async def _perform_handshake(self, ip: str, port: int) -> Optional[PeerInfo]:
        """Perform handshake with a peer"""
        try:
            handshake_data = {
                'node_id': self.node_id,
                'ip_address': self.public_ip,
                'port': self.listen_port,
                'network_id': self.network_id,
                'version': '1.0.0',
                'capabilities': {
                    'federated_learning': True,
                    'secure_aggregation': True,
                    'differential_privacy': True
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'http://{ip}:{port}/p2p/handshake',
                    json=handshake_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        peer_data = await response.json()
                        
                        peer_info = PeerInfo(
                            peer_id=peer_data['node_id'],
                            ip_address=peer_data['ip_address'],
                            port=peer_data['port'],
                            public_key=peer_data.get('public_key', ''),
                            capabilities=peer_data.get('capabilities', {}),
                            last_seen=time.time(),
                            reputation=0.5,  # Initial neutral reputation
                            is_bootstrap=False,
                            version=peer_data.get('version', ''),
                            network_id=peer_data.get('network_id', '')
                        )
                        
                        return peer_info
        
        except Exception as e:
            self.logger.debug(f"Handshake failed with {ip}:{port}: {e}")
        
        return None
    
    async def _handle_handshake(self, request):
        """Handle incoming handshake request"""
        try:
            data = await request.json()
            
            # Validate network ID
            if data.get('network_id') != self.network_id:
                return web.json_response({'error': 'Network ID mismatch'}, status=400)
            
            # Create peer info
            peer_info = PeerInfo(
                peer_id=data['node_id'],
                ip_address=data['ip_address'],
                port=data['port'],
                public_key=data.get('public_key', ''),
                capabilities=data.get('capabilities', {}),
                last_seen=time.time(),
                reputation=0.5,
                is_bootstrap=False,
                version=data.get('version', ''),
                network_id=data['network_id']
            )
            
            # Add to DHT
            self.dht.add_peer(peer_info)
            self.connected_peers[peer_info.peer_id] = peer_info
            
            self.stats['connections_established'] += 1
            
            # Respond with our info
            response_data = {
                'node_id': self.node_id,
                'ip_address': self.public_ip,
                'port': self.listen_port,
                'network_id': self.network_id,
                'version': '1.0.0',
                'capabilities': {
                    'federated_learning': True,
                    'secure_aggregation': True,
                    'differential_privacy': True
                }
            }
            
            return web.json_response(response_data)
        
        except Exception as e:
            self.logger.error(f"Handshake handling error: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def _handle_http_message(self, request):
        """Handle incoming P2P message"""
        try:
            data = await request.json()
            
            message = NetworkMessage(
                message_id=data['message_id'],
                message_type=data['message_type'],
                sender_id=data['sender_id'],
                recipient_id=data.get('recipient_id'),
                payload=data['payload'],
                timestamp=data['timestamp'],
                ttl=data['ttl'],
                signature=data.get('signature')
            )
            
            await self._process_message(message)
            self.stats['messages_received'] += 1
            
            return web.json_response({'status': 'received'})
        
        except Exception as e:
            self.logger.error(f"Message handling error: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def _handle_peer_list_request(self, request):
        """Handle request for peer list"""
        try:
            # Return a subset of known peers
            all_peers = []
            for bucket in self.dht.routing_table.values():
                all_peers.extend(bucket)
            
            # Limit response size
            peer_sample = random.sample(all_peers, min(20, len(all_peers)))
            
            peer_list = [
                {
                    'peer_id': peer.peer_id,
                    'ip_address': peer.ip_address,
                    'port': peer.port,
                    'capabilities': peer.capabilities,
                    'reputation': peer.reputation
                }
                for peer in peer_sample
            ]
            
            return web.json_response({'peers': peer_list})
        
        except Exception as e:
            self.logger.error(f"Peer list request error: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def _peer_discovery_loop(self):
        """Main peer discovery loop"""
        while self.running:
            try:
                # Request peer lists from connected peers
                discovery_tasks = []
                for peer in list(self.connected_peers.values()):
                    task = asyncio.create_task(self._discover_peers_from(peer))
                    discovery_tasks.append(task)
                
                if discovery_tasks:
                    await asyncio.gather(*discovery_tasks, return_exceptions=True)
                
                # Periodic bootstrap node reconnection
                if len(self.connected_peers) < 5:  # Low connectivity
                    for bootstrap_node in self.bootstrap_nodes:
                        if bootstrap_node.peer_id not in self.connected_peers:
                            peer_info = await self._perform_handshake(
                                bootstrap_node.ip_address, 
                                bootstrap_node.port
                            )
                            if peer_info:
                                self.connected_peers[peer_info.peer_id] = peer_info
            
            except Exception as e:
                self.logger.error(f"Peer discovery error: {e}")
            
            await asyncio.sleep(30)  # Discovery every 30 seconds
    
    async def _discover_peers_from(self, peer: PeerInfo):
        """Discover new peers from an existing peer"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'http://{peer.ip_address}:{peer.port}/p2p/peers',
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        for peer_data in data.get('peers', []):
                            new_peer = PeerInfo(
                                peer_id=peer_data['peer_id'],
                                ip_address=peer_data['ip_address'],
                                port=peer_data['port'],
                                public_key='',
                                capabilities=peer_data.get('capabilities', {}),
                                last_seen=time.time(),
                                reputation=peer_data.get('reputation', 0.5),
                                is_bootstrap=False,
                                version='',
                                network_id=self.network_id
                            )
                            
                            # Try to connect to new peer
                            if (new_peer.peer_id != self.node_id and 
                                new_peer.peer_id not in self.connected_peers):
                                
                                connected_peer = await self._perform_handshake(
                                    new_peer.ip_address, 
                                    new_peer.port
                                )
                                
                                if connected_peer:
                                    self.connected_peers[connected_peer.peer_id] = connected_peer
                                    self.stats['peers_discovered'] += 1
        
        except Exception as e:
            self.logger.debug(f"Peer discovery from {peer.peer_id[:8]}... failed: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to maintain connections"""
        while self.running:
            try:
                heartbeat_message = {
                    'message_id': hashlib.sha256(f"{self.node_id}{time.time()}".encode()).hexdigest(),
                    'message_type': 'heartbeat',
                    'sender_id': self.node_id,
                    'recipient_id': None,  # Broadcast
                    'payload': {
                        'timestamp': time.time(),
                        'capabilities': {
                            'federated_learning': True,
                            'secure_aggregation': True,
                            'differential_privacy': True
                        }
                    },
                    'timestamp': time.time(),
                    'ttl': 60,
                    'signature': None
                }
                
                await self.broadcast_message(heartbeat_message)
            
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
            
            await asyncio.sleep(60)  # Heartbeat every minute
    
    async def _maintenance_loop(self):
        """Perform network maintenance tasks"""
        while self.running:
            try:
                current_time = time.time()
                
                # Remove stale peers
                stale_peers = []
                for peer_id, peer in self.connected_peers.items():
                    if current_time - peer.last_seen > 300:  # 5 minutes timeout
                        stale_peers.append(peer_id)
                
                for peer_id in stale_peers:
                    del self.connected_peers[peer_id]
                    self.logger.info(f"Removed stale peer: {peer_id[:8]}...")
                
                # DHT maintenance
                # TODO: Implement DHT bucket refresh, key expiration, etc.
                
            except Exception as e:
                self.logger.error(f"Maintenance error: {e}")
            
            await asyncio.sleep(120)  # Maintenance every 2 minutes
    
    async def broadcast_message(self, message_data: Dict[str, Any]):
        """Broadcast message to connected peers"""
        message = NetworkMessage(
            message_id=message_data['message_id'],
            message_type=message_data['message_type'],
            sender_id=message_data['sender_id'],
            recipient_id=message_data.get('recipient_id'),
            payload=message_data['payload'],
            timestamp=message_data['timestamp'],
            ttl=message_data['ttl'],
            signature=message_data.get('signature')
        )
        
        # Cache message to prevent loops
        self.gossip.cache_message(message)
        
        # Select peers for gossip
        gossip_peers = self.gossip.select_gossip_peers(list(self.connected_peers.values()))
        
        # Send to selected peers
        send_tasks = []
        for peer in gossip_peers:
            task = asyncio.create_task(self._send_message_to_peer(peer, message))
            send_tasks.append(task)
        
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)
            self.stats['messages_sent'] += len(send_tasks)
    
    async def _send_message_to_peer(self, peer: PeerInfo, message: NetworkMessage):
        """Send message to specific peer"""
        try:
            message_data = asdict(message)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'http://{peer.ip_address}:{peer.port}/p2p/message',
                    json=message_data,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    
                    if response.status != 200:
                        self.logger.warning(f"Message send failed to {peer.peer_id[:8]}...")
        
        except Exception as e:
            self.logger.debug(f"Failed to send message to {peer.peer_id[:8]}...: {e}")
    
    async def _process_message(self, message: NetworkMessage):
        """Process received message"""
        # Update sender's last seen time
        if message.sender_id in self.connected_peers:
            self.connected_peers[message.sender_id].last_seen = time.time()
        
        # Handle different message types
        if message.message_type == 'heartbeat':
            await self._handle_heartbeat(message)
        elif message.message_type == 'training_announcement':
            await self._handle_training_announcement(message)
        elif message.message_type == 'model_update':
            await self._handle_model_update(message)
        
        # Gossip message if appropriate
        if self.gossip.should_gossip_message(message):
            await self._gossip_message(message)
        
        # Call registered handlers
        if message.message_type in self.message_handlers:
            try:
                await self.message_handlers[message.message_type](message)
            except Exception as e:
                self.logger.error(f"Message handler error: {e}")
    
    async def _handle_heartbeat(self, message: NetworkMessage):
        """Handle heartbeat message"""
        # Update peer capabilities and reputation
        sender_id = message.sender_id
        if sender_id in self.connected_peers:
            peer = self.connected_peers[sender_id]
            peer.capabilities.update(message.payload.get('capabilities', {}))
            # Slight reputation increase for active heartbeat
            peer.reputation = min(1.0, peer.reputation + 0.001)
    
    async def _handle_training_announcement(self, message: NetworkMessage):
        """Handle training round announcement"""
        self.logger.info(f"Received training announcement: {message.payload}")
    
    async def _handle_model_update(self, message: NetworkMessage):
        """Handle model update message"""
        self.logger.info(f"Received model update from {message.sender_id[:8]}...")
    
    async def _gossip_message(self, message: NetworkMessage):
        """Gossip message to other peers"""
        gossip_peers = self.gossip.select_gossip_peers(
            [p for p in self.connected_peers.values() if p.peer_id != message.sender_id]
        )
        
        tasks = []
        for peer in gossip_peers:
            task = asyncio.create_task(self._send_message_to_peer(peer, message))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def register_message_handler(self, message_type: str, handler: callable):
        """Register handler for specific message type"""
        self.message_handlers[message_type] = handler
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics"""
        uptime = time.time() - self.stats['start_time']
        
        return {
            'node_id': self.node_id,
            'connected_peers': len(self.connected_peers),
            'bootstrap_nodes': len(self.bootstrap_nodes),
            'dht_buckets': len([b for b in self.dht.routing_table.values() if b]),
            'messages_sent': self.stats['messages_sent'],
            'messages_received': self.stats['messages_received'],
            'peers_discovered': self.stats['peers_discovered'],
            'connections_established': self.stats['connections_established'],
            'uptime_seconds': uptime,
            'public_ip': self.public_ip,
            'listen_port': self.listen_port
        }
    
    def get_peer_list(self) -> List[Dict[str, Any]]:
        """Get list of connected peers"""
        return [
            {
                'peer_id': peer.peer_id,
                'ip_address': peer.ip_address,
                'port': peer.port,
                'reputation': peer.reputation,
                'last_seen': peer.last_seen,
                'capabilities': peer.capabilities,
                'is_bootstrap': peer.is_bootstrap
            }
            for peer in self.connected_peers.values()
        ]