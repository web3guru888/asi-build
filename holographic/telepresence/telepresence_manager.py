"""
Holographic telepresence manager for real-time remote collaboration
"""

import asyncio
import logging
import time
import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor
import websockets
import ssl

from ..core.base import (
    HolographicBase, 
    Vector3D, 
    Transform3D,
    HolographicPerformanceMonitor
)
from ..core.config import NetworkConfig

logger = logging.getLogger(__name__)

class PresenceState(Enum):
    """Remote presence state"""
    OFFLINE = "offline"
    CONNECTING = "connecting"
    ONLINE = "online"
    STREAMING = "streaming"
    DISCONNECTED = "disconnected"

class HologramType(Enum):
    """Types of holographic content"""
    AVATAR = "avatar"
    OBJECT = "object"
    ENVIRONMENT = "environment"
    ANNOTATION = "annotation"
    MEDIA = "media"

@dataclass
class RemoteUser:
    """Remote user representation"""
    user_id: str
    username: str
    avatar_url: Optional[str]
    position: Vector3D
    orientation: Transform3D
    state: PresenceState
    last_seen: float
    capabilities: Dict[str, Any]
    
    def __post_init__(self):
        if self.last_seen == 0:
            self.last_seen = time.time()

@dataclass
class HolographicContent:
    """Holographic content data"""
    content_id: str
    content_type: HologramType
    owner_id: str
    position: Vector3D
    orientation: Transform3D
    scale: Vector3D
    data: bytes
    metadata: Dict[str, Any]
    timestamp: float
    compressed: bool = True
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()

@dataclass
class SpatialStream:
    """Spatial data stream"""
    stream_id: str
    source_id: str
    stream_type: str  # video, audio, hologram, haptic
    quality_level: int
    bitrate: int
    frame_rate: float
    latency_ms: float
    active: bool = True

class TelepresenceManager(HolographicBase):
    """
    Main telepresence manager for holographic remote collaboration
    Handles real-time streaming of holographic content and remote user presence
    """
    
    def __init__(self, config: NetworkConfig):
        super().__init__("TelepresenceManager")
        self.config = config
        self.performance_monitor = HolographicPerformanceMonitor()
        
        # Network components
        self.server_address = config.server_address
        self.server_port = config.server_port
        self.use_encryption = config.encryption_enabled
        self.ssl_context = None
        
        # Connection management
        self.websocket_server = None
        self.connected_clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.remote_users: Dict[str, RemoteUser] = {}
        
        # Content management
        self.shared_content: Dict[str, HolographicContent] = {}
        self.spatial_streams: Dict[str, SpatialStream] = {}
        
        # Local user
        self.local_user_id = f"user_{int(time.time())}"
        self.local_position = Vector3D(0, 0, 0)
        self.local_orientation = Transform3D()
        
        # Streaming
        self.streaming_active = False
        self.stream_executor = ThreadPoolExecutor(max_workers=8)
        
        # Quality management
        self.adaptive_quality = True
        self.target_latency_ms = 50
        self.quality_levels = {
            1: {"resolution": (256, 256), "bitrate": 500},
            2: {"resolution": (512, 512), "bitrate": 1000},
            3: {"resolution": (1024, 1024), "bitrate": 2000},
            4: {"resolution": (2048, 2048), "bitrate": 4000}
        }
        
        # Event handlers
        self.event_handlers = {
            "user_joined": [],
            "user_left": [],
            "content_shared": [],
            "content_updated": [],
            "stream_started": [],
            "stream_ended": []
        }
        
        logger.info(f"TelepresenceManager initialized for {self.server_address}:{self.server_port}")
    
    async def initialize(self) -> bool:
        """Initialize the telepresence manager"""
        try:
            logger.info("Initializing TelepresenceManager...")
            
            # Setup SSL context if encryption is enabled
            if self.use_encryption:
                await self._setup_ssl_context()
            
            # Initialize hologram encoder
            await self._initialize_encoder()
            
            # Initialize presence renderer
            await self._initialize_renderer()
            
            self.initialized = True
            logger.info("TelepresenceManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize TelepresenceManager: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the telepresence manager"""
        logger.info("Shutting down TelepresenceManager...")
        
        # Stop streaming
        await self.stop_streaming()
        
        # Close server
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        # Clear connections and data
        self.connected_clients.clear()
        self.remote_users.clear()
        self.shared_content.clear()
        self.spatial_streams.clear()
        
        # Shutdown executor
        self.stream_executor.shutdown(wait=True)
        
        self.initialized = False
        logger.info("TelepresenceManager shutdown complete")
    
    async def _setup_ssl_context(self):
        """Setup SSL context for secure connections"""
        try:
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            # In production, load actual certificates
            # self.ssl_context.load_cert_chain("cert.pem", "key.pem")
            logger.info("SSL context configured")
        except Exception as e:
            logger.error(f"Failed to setup SSL context: {e}")
            self.use_encryption = False
    
    async def _initialize_encoder(self):
        """Initialize hologram encoder"""
        from .hologram_encoder import HologramEncoder
        self.hologram_encoder = HologramEncoder(self.config)
        await self.hologram_encoder.initialize()
        logger.info("Hologram encoder initialized")
    
    async def _initialize_renderer(self):
        """Initialize presence renderer"""
        from .presence_renderer import PresenceRenderer
        self.presence_renderer = PresenceRenderer(self.config)
        await self.presence_renderer.initialize()
        logger.info("Presence renderer initialized")
    
    async def start_server(self) -> bool:
        """Start telepresence server"""
        try:
            logger.info(f"Starting telepresence server on {self.server_address}:{self.server_port}")
            
            # Start WebSocket server
            self.websocket_server = await websockets.serve(
                self._handle_client_connection,
                self.server_address,
                self.server_port,
                ssl=self.ssl_context if self.use_encryption else None,
                ping_interval=10,
                ping_timeout=5
            )
            
            logger.info("Telepresence server started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start telepresence server: {e}")
            return False
    
    async def connect_to_server(self, server_url: str) -> bool:
        """Connect to a remote telepresence server"""
        try:
            logger.info(f"Connecting to telepresence server: {server_url}")
            
            # Connect as client
            uri = f"{'wss' if self.use_encryption else 'ws'}://{server_url}"
            
            async with websockets.connect(
                uri,
                ssl=self.ssl_context if self.use_encryption else None,
                ping_interval=10,
                ping_timeout=5
            ) as websocket:
                
                # Send join message
                await self._send_join_message(websocket)
                
                # Start client message loop
                await self._client_message_loop(websocket)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            return False
    
    async def _handle_client_connection(self, websocket, path):
        """Handle incoming client connection"""
        client_id = f"client_{id(websocket)}"
        self.connected_clients[client_id] = websocket
        
        logger.info(f"Client {client_id} connected from {websocket.remote_address}")
        
        try:
            await self._server_message_loop(websocket, client_id)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Cleanup
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
            await self._handle_user_left(client_id)
    
    async def _server_message_loop(self, websocket, client_id: str):
        """Main message loop for server"""
        async for message in websocket:
            try:
                data = json.loads(message)
                await self._process_message(websocket, client_id, data)
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def _client_message_loop(self, websocket):
        """Main message loop for client"""
        async for message in websocket:
            try:
                data = json.loads(message)
                await self._process_server_message(data)
            except json.JSONDecodeError:
                logger.error("Invalid JSON received from server")
            except Exception as e:
                logger.error(f"Error processing server message: {e}")
    
    async def _process_message(self, websocket, client_id: str, data: Dict[str, Any]):
        """Process incoming message from client"""
        message_type = data.get("type")
        
        if message_type == "join":
            await self._handle_user_join(websocket, client_id, data)
        elif message_type == "position_update":
            await self._handle_position_update(client_id, data)
        elif message_type == "share_content":
            await self._handle_share_content(client_id, data)
        elif message_type == "update_content":
            await self._handle_update_content(client_id, data)
        elif message_type == "start_stream":
            await self._handle_start_stream(client_id, data)
        elif message_type == "stream_data":
            await self._handle_stream_data(client_id, data)
        elif message_type == "stop_stream":
            await self._handle_stop_stream(client_id, data)
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def _process_server_message(self, data: Dict[str, Any]):
        """Process message from server when acting as client"""
        message_type = data.get("type")
        
        if message_type == "user_joined":
            await self._handle_remote_user_joined(data)
        elif message_type == "user_left":
            await self._handle_remote_user_left(data)
        elif message_type == "user_update":
            await self._handle_remote_user_update(data)
        elif message_type == "content_shared":
            await self._handle_remote_content_shared(data)
        elif message_type == "content_updated":
            await self._handle_remote_content_updated(data)
        elif message_type == "stream_started":
            await self._handle_remote_stream_started(data)
        elif message_type == "stream_data":
            await self._handle_remote_stream_data(data)
    
    async def _send_join_message(self, websocket):
        """Send join message to server"""
        join_data = {
            "type": "join",
            "user_id": self.local_user_id,
            "username": f"User_{self.local_user_id[-6:]}",
            "position": {
                "x": self.local_position.x,
                "y": self.local_position.y,
                "z": self.local_position.z
            },
            "capabilities": {
                "holographic_display": True,
                "spatial_audio": True,
                "haptic_feedback": False
            }
        }
        
        await websocket.send(json.dumps(join_data))
    
    async def _handle_user_join(self, websocket, client_id: str, data: Dict[str, Any]):
        """Handle user join"""
        user_id = data.get("user_id", client_id)
        username = data.get("username", f"User_{user_id[-6:]}")
        position_data = data.get("position", {"x": 0, "y": 0, "z": 0})
        
        user = RemoteUser(
            user_id=user_id,
            username=username,
            avatar_url=data.get("avatar_url"),
            position=Vector3D(**position_data),
            orientation=Transform3D(),
            state=PresenceState.ONLINE,
            last_seen=time.time(),
            capabilities=data.get("capabilities", {})
        )
        
        self.remote_users[user_id] = user
        
        # Broadcast to other clients
        await self._broadcast_message({
            "type": "user_joined",
            "user": asdict(user)
        }, exclude_client=client_id)
        
        # Send existing users to new client
        for existing_user in self.remote_users.values():
            if existing_user.user_id != user_id:
                await websocket.send(json.dumps({
                    "type": "user_joined",
                    "user": asdict(existing_user)
                }))
        
        # Send existing content
        for content in self.shared_content.values():
            await websocket.send(json.dumps({
                "type": "content_shared",
                "content": self._serialize_content(content)
            }))
        
        # Trigger event
        await self._trigger_event("user_joined", user)
        
        logger.info(f"User {username} ({user_id}) joined")
    
    async def _handle_user_left(self, client_id: str):
        """Handle user leaving"""
        # Find user by client ID
        user_to_remove = None
        for user_id, user in self.remote_users.items():
            if user_id == client_id or user.user_id == client_id:
                user_to_remove = user_id
                break
        
        if user_to_remove:
            user = self.remote_users[user_to_remove]
            del self.remote_users[user_to_remove]
            
            # Broadcast to other clients
            await self._broadcast_message({
                "type": "user_left",
                "user_id": user_to_remove
            })
            
            # Trigger event
            await self._trigger_event("user_left", user)
            
            logger.info(f"User {user.username} ({user_to_remove}) left")
    
    async def _handle_position_update(self, client_id: str, data: Dict[str, Any]):
        """Handle user position update"""
        user_id = data.get("user_id", client_id)
        
        if user_id in self.remote_users:
            user = self.remote_users[user_id]
            position_data = data.get("position", {})
            orientation_data = data.get("orientation", {})
            
            user.position = Vector3D(**position_data)
            if orientation_data:
                user.orientation = Transform3D(**orientation_data)
            user.last_seen = time.time()
            
            # Broadcast to other clients
            await self._broadcast_message({
                "type": "user_update",
                "user_id": user_id,
                "position": position_data,
                "orientation": orientation_data
            }, exclude_client=client_id)
    
    async def _handle_share_content(self, client_id: str, data: Dict[str, Any]):
        """Handle content sharing"""
        content_data = data.get("content", {})
        
        content = HolographicContent(
            content_id=content_data.get("content_id", f"content_{int(time.time())}"),
            content_type=HologramType(content_data.get("content_type", "object")),
            owner_id=content_data.get("owner_id", client_id),
            position=Vector3D(**content_data.get("position", {"x": 0, "y": 0, "z": 0})),
            orientation=Transform3D(),
            scale=Vector3D(**content_data.get("scale", {"x": 1, "y": 1, "z": 1})),
            data=bytes(content_data.get("data", ""), 'utf-8'),
            metadata=content_data.get("metadata", {}),
            timestamp=time.time()
        )
        
        self.shared_content[content.content_id] = content
        
        # Broadcast to all clients
        await self._broadcast_message({
            "type": "content_shared",
            "content": self._serialize_content(content)
        })
        
        # Trigger event
        await self._trigger_event("content_shared", content)
        
        logger.info(f"Content {content.content_id} shared by {content.owner_id}")
    
    async def _handle_start_stream(self, client_id: str, data: Dict[str, Any]):
        """Handle stream start request"""
        stream_data = data.get("stream", {})
        
        stream = SpatialStream(
            stream_id=stream_data.get("stream_id", f"stream_{int(time.time())}"),
            source_id=stream_data.get("source_id", client_id),
            stream_type=stream_data.get("stream_type", "hologram"),
            quality_level=stream_data.get("quality_level", 2),
            bitrate=stream_data.get("bitrate", 1000),
            frame_rate=stream_data.get("frame_rate", 30.0),
            latency_ms=0.0
        )
        
        self.spatial_streams[stream.stream_id] = stream
        
        # Broadcast stream start
        await self._broadcast_message({
            "type": "stream_started",
            "stream": asdict(stream)
        }, exclude_client=client_id)
        
        # Trigger event
        await self._trigger_event("stream_started", stream)
        
        logger.info(f"Stream {stream.stream_id} started by {stream.source_id}")
    
    async def _handle_stream_data(self, client_id: str, data: Dict[str, Any]):
        """Handle incoming stream data"""
        stream_id = data.get("stream_id")
        frame_data = data.get("frame_data")
        frame_number = data.get("frame_number", 0)
        timestamp = data.get("timestamp", time.time())
        
        if stream_id in self.spatial_streams:
            stream = self.spatial_streams[stream_id]
            
            # Calculate latency
            current_time = time.time()
            latency_ms = (current_time - timestamp) * 1000
            stream.latency_ms = latency_ms
            
            # Forward to other clients
            await self._broadcast_message({
                "type": "stream_data",
                "stream_id": stream_id,
                "frame_data": frame_data,
                "frame_number": frame_number,
                "timestamp": timestamp
            }, exclude_client=client_id)
            
            # Adaptive quality adjustment
            if self.adaptive_quality:
                await self._adjust_stream_quality(stream)
    
    async def _adjust_stream_quality(self, stream: SpatialStream):
        """Adjust stream quality based on performance"""
        target_latency = self.target_latency_ms
        
        if stream.latency_ms > target_latency * 1.5:
            # Reduce quality
            if stream.quality_level > 1:
                stream.quality_level -= 1
                quality_settings = self.quality_levels[stream.quality_level]
                stream.bitrate = quality_settings["bitrate"]
                logger.info(f"Reduced quality for stream {stream.stream_id} to level {stream.quality_level}")
        
        elif stream.latency_ms < target_latency * 0.8:
            # Increase quality
            if stream.quality_level < max(self.quality_levels.keys()):
                stream.quality_level += 1
                quality_settings = self.quality_levels[stream.quality_level]
                stream.bitrate = quality_settings["bitrate"]
                logger.info(f"Increased quality for stream {stream.stream_id} to level {stream.quality_level}")
    
    async def _broadcast_message(self, message: Dict[str, Any], exclude_client: str = None):
        """Broadcast message to all connected clients"""
        message_json = json.dumps(message)
        
        disconnected_clients = []
        
        for client_id, websocket in self.connected_clients.items():
            if client_id != exclude_client:
                try:
                    await websocket.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.append(client_id)
                except Exception as e:
                    logger.error(f"Error sending to client {client_id}: {e}")
                    disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
            await self._handle_user_left(client_id)
    
    def _serialize_content(self, content: HolographicContent) -> Dict[str, Any]:
        """Serialize holographic content for transmission"""
        return {
            "content_id": content.content_id,
            "content_type": content.content_type.value,
            "owner_id": content.owner_id,
            "position": {"x": content.position.x, "y": content.position.y, "z": content.position.z},
            "orientation": {
                "position": {"x": content.orientation.position.x, "y": content.orientation.position.y, "z": content.orientation.position.z},
                "rotation": {"w": content.orientation.rotation.w, "x": content.orientation.rotation.x, "y": content.orientation.rotation.y, "z": content.orientation.rotation.z},
                "scale": {"x": content.orientation.scale.x, "y": content.orientation.scale.y, "z": content.orientation.scale.z}
            },
            "scale": {"x": content.scale.x, "y": content.scale.y, "z": content.scale.z},
            "data": content.data.decode('utf-8') if content.data else "",
            "metadata": content.metadata,
            "timestamp": content.timestamp
        }
    
    async def _trigger_event(self, event_type: str, data: Any):
        """Trigger event handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")
    
    def add_event_handler(self, event_type: str, handler):
        """Add event handler"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler):
        """Remove event handler"""
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
    
    async def update_local_position(self, position: Vector3D, orientation: Transform3D = None):
        """Update local user position"""
        self.local_position = position
        if orientation:
            self.local_orientation = orientation
        
        # Broadcast to all connected clients
        message = {
            "type": "position_update",
            "user_id": self.local_user_id,
            "position": {"x": position.x, "y": position.y, "z": position.z}
        }
        
        if orientation:
            message["orientation"] = {
                "position": {"x": orientation.position.x, "y": orientation.position.y, "z": orientation.position.z},
                "rotation": {"w": orientation.rotation.w, "x": orientation.rotation.x, "y": orientation.rotation.y, "z": orientation.rotation.z},
                "scale": {"x": orientation.scale.x, "y": orientation.scale.y, "z": orientation.scale.z}
            }
        
        await self._broadcast_message(message)
    
    async def share_holographic_content(self, content_type: HologramType, data: bytes,
                                      position: Vector3D, metadata: Dict[str, Any] = None) -> str:
        """Share holographic content with remote users"""
        content_id = f"content_{int(time.time() * 1000)}"
        
        content = HolographicContent(
            content_id=content_id,
            content_type=content_type,
            owner_id=self.local_user_id,
            position=position,
            orientation=Transform3D(),
            scale=Vector3D(1, 1, 1),
            data=data,
            metadata=metadata or {},
            timestamp=time.time()
        )
        
        self.shared_content[content_id] = content
        
        # Broadcast to all clients
        await self._broadcast_message({
            "type": "content_shared",
            "content": self._serialize_content(content)
        })
        
        logger.info(f"Shared holographic content {content_id}")
        return content_id
    
    async def start_holographic_stream(self, stream_type: str = "hologram", 
                                     quality_level: int = 2) -> str:
        """Start holographic stream"""
        stream_id = f"stream_{int(time.time() * 1000)}"
        
        quality_settings = self.quality_levels.get(quality_level, self.quality_levels[2])
        
        stream = SpatialStream(
            stream_id=stream_id,
            source_id=self.local_user_id,
            stream_type=stream_type,
            quality_level=quality_level,
            bitrate=quality_settings["bitrate"],
            frame_rate=30.0,
            latency_ms=0.0
        )
        
        self.spatial_streams[stream_id] = stream
        self.streaming_active = True
        
        # Broadcast stream start
        await self._broadcast_message({
            "type": "stream_started",
            "stream": asdict(stream)
        })
        
        # Start streaming loop
        asyncio.create_task(self._streaming_loop(stream))
        
        logger.info(f"Started holographic stream {stream_id}")
        return stream_id
    
    async def _streaming_loop(self, stream: SpatialStream):
        """Main streaming loop"""
        logger.info(f"Streaming loop started for {stream.stream_id}")
        
        frame_number = 0
        frame_interval = 1.0 / stream.frame_rate
        
        try:
            while self.streaming_active and stream.active:
                start_time = time.time()
                
                # Capture and encode frame
                frame_data = await self._capture_holographic_frame(stream)
                
                if frame_data:
                    # Send frame data
                    await self._broadcast_message({
                        "type": "stream_data",
                        "stream_id": stream.stream_id,
                        "frame_data": frame_data,
                        "frame_number": frame_number,
                        "timestamp": start_time
                    })
                
                frame_number += 1
                
                # Maintain frame rate
                elapsed = time.time() - start_time
                if elapsed < frame_interval:
                    await asyncio.sleep(frame_interval - elapsed)
                
        except Exception as e:
            logger.error(f"Error in streaming loop: {e}")
        finally:
            logger.info(f"Streaming loop ended for {stream.stream_id}")
    
    async def _capture_holographic_frame(self, stream: SpatialStream) -> Optional[str]:
        """Capture holographic frame for streaming"""
        try:
            # In practice, this would capture actual holographic data
            # For now, return mock data
            quality_settings = self.quality_levels[stream.quality_level]
            resolution = quality_settings["resolution"]
            
            # Mock frame data
            frame_data = {
                "resolution": resolution,
                "format": "holographic",
                "data": f"mock_frame_data_{time.time()}"
            }
            
            return json.dumps(frame_data)
            
        except Exception as e:
            logger.error(f"Error capturing holographic frame: {e}")
            return None
    
    async def stop_streaming(self):
        """Stop all streaming"""
        self.streaming_active = False
        
        # Mark all streams as inactive
        for stream in self.spatial_streams.values():
            stream.active = False
        
        # Broadcast stream stop
        await self._broadcast_message({
            "type": "streams_stopped",
            "user_id": self.local_user_id
        })
        
        logger.info("Stopped all streaming")
    
    def get_remote_users(self) -> Dict[str, RemoteUser]:
        """Get all remote users"""
        return self.remote_users.copy()
    
    def get_shared_content(self) -> Dict[str, HolographicContent]:
        """Get all shared content"""
        return self.shared_content.copy()
    
    def get_active_streams(self) -> Dict[str, SpatialStream]:
        """Get all active streams"""
        return {sid: stream for sid, stream in self.spatial_streams.items() if stream.active}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        active_streams = self.get_active_streams()
        
        return {
            "connected_clients": len(self.connected_clients),
            "remote_users": len(self.remote_users),
            "shared_content": len(self.shared_content),
            "active_streams": len(active_streams),
            "average_latency": np.mean([s.latency_ms for s in active_streams.values()]) if active_streams else 0,
            "total_bitrate": sum(s.bitrate for s in active_streams.values()),
            "streaming_active": self.streaming_active,
            "encryption_enabled": self.use_encryption
        }