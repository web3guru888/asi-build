"""
Main integration class for Kenny's holographic systems
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
import threading
from pathlib import Path

from ..core.base import HolographicBase, Vector3D, Transform3D
from ..core.config import HolographicConfig
from ..core.engine import HolographicEngine
from ..display import VolumetricDisplayManager
from ..gestures import GestureManager
from ..telepresence import TelepresenceManager
from ..ar_overlay import AROverlayManager
from ..physics import HolographicPhysicsManager
from ..audio import SpatialAudioManager

logger = logging.getLogger(__name__)

@dataclass
class KennyScreenData:
    """Screen data from Kenny's screen monitor"""
    screenshot_path: str
    timestamp: float
    ocr_text: List[str]
    ui_elements: List[Dict[str, Any]]
    detected_objects: List[Dict[str, Any]]
    screen_resolution: Tuple[int, int]

@dataclass
class HolographicOverlay:
    """Holographic overlay for Kenny's screen"""
    overlay_id: str
    position: Vector3D
    content_type: str  # text, ui_element, visualization
    content_data: Any
    visibility: float
    duration: float
    interactive: bool

class KennyHolographicIntegration(HolographicBase):
    """
    Main integration class for Kenny's holographic systems
    Bridges Kenny's existing UI automation with holographic capabilities
    """
    
    def __init__(self, kenny_config_path: str = None):
        super().__init__("KennyHolographicIntegration")
        
        # Load Kenny's configuration
        self.kenny_config = self._load_kenny_config(kenny_config_path)
        
        # Initialize holographic configuration
        self.holo_config = HolographicConfig()
        
        # Core holographic systems
        self.holographic_engine = None
        self.display_manager = None
        self.gesture_manager = None
        self.telepresence_manager = None
        self.ar_manager = None
        self.physics_manager = None
        self.audio_manager = None
        
        # Kenny integration components
        self.screen_monitor_integration = None
        self.ai_command_integration = None
        self.workflow_integration = None
        
        # Current screen state
        self.current_screen_data: Optional[KennyScreenData] = None
        self.holographic_overlays: Dict[str, HolographicOverlay] = {}
        
        # Integration settings
        self.holographic_mode_enabled = False
        self.ar_overlay_enabled = True
        self.gesture_control_enabled = True
        self.spatial_audio_enabled = True
        
        # Event handlers
        self.event_handlers = {
            'screen_updated': [],
            'ui_element_detected': [],
            'command_executed': [],
            'gesture_detected': [],
            'hologram_created': []
        }
        
        logger.info("KennyHolographicIntegration initialized")
    
    def _load_kenny_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load Kenny's configuration"""
        try:
            if config_path is None:
                # Try to find Kenny's config
                possible_paths = [
                    Path(__file__).parent.parent.parent / "config_manager.py",
                    Path(__file__).parent.parent.parent / "autonomous_config.json",
                    Path(__file__).parent.parent.parent / "safety_config.json"
                ]
                
                for path in possible_paths:
                    if path.exists():
                        if path.suffix == '.json':
                            with open(path, 'r') as f:
                                return json.load(f)
                        elif path.suffix == '.py':
                            # Load from Python config module
                            return self._load_python_config(path)
            
            return {}  # Default empty config
            
        except Exception as e:
            logger.error(f"Failed to load Kenny config: {e}")
            return {}
    
    def _load_python_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from Python module"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("kenny_config", config_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            # Extract configuration attributes
            config = {}
            for attr in dir(config_module):
                if not attr.startswith('_'):
                    config[attr] = getattr(config_module, attr)
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load Python config: {e}")
            return {}
    
    async def initialize(self) -> bool:
        """Initialize all holographic systems"""
        try:
            logger.info("Initializing Kenny holographic integration...")
            
            # Initialize holographic engine
            self.holographic_engine = HolographicEngine(self.holo_config)
            await self.holographic_engine.initialize()
            
            # Initialize display manager
            self.display_manager = VolumetricDisplayManager(self.holo_config.display)
            await self.display_manager.initialize()
            
            # Initialize gesture manager
            if self.gesture_control_enabled:
                await self._initialize_gesture_manager()
            
            # Initialize AR overlay manager
            if self.ar_overlay_enabled:
                await self._initialize_ar_manager()
            
            # Initialize telepresence manager
            await self._initialize_telepresence_manager()
            
            # Initialize physics manager
            await self._initialize_physics_manager()
            
            # Initialize spatial audio manager
            if self.spatial_audio_enabled:
                await self._initialize_audio_manager()
            
            # Initialize Kenny integration components
            await self._initialize_kenny_integrations()
            
            # Start holographic engine
            await self.holographic_engine.start()
            
            self.initialized = True
            logger.info("Kenny holographic integration initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Kenny holographic integration: {e}")
            return False
    
    async def _initialize_gesture_manager(self):
        """Initialize gesture recognition"""
        try:
            from ..gestures import GestureManager
            gesture_config = {
                'confidence_threshold': 0.8,
                'tracking_distance': 0.15,
                'smoothing_enabled': True,
                'camera_count': 1  # Use single camera for Kenny integration
            }
            
            self.gesture_manager = GestureManager(gesture_config)
            await self.gesture_manager.initialize()
            
            # Connect gesture events to Kenny commands
            self.gesture_manager.add_event_handler('gesture_detected', self._on_gesture_detected)
            
            logger.info("Gesture manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize gesture manager: {e}")
            self.gesture_control_enabled = False
    
    async def _initialize_ar_manager(self):
        """Initialize AR overlay manager"""
        try:
            from ..ar_overlay import AROverlayManager
            
            self.ar_manager = AROverlayManager(self.holo_config.display)
            await self.ar_manager.initialize()
            
            logger.info("AR overlay manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize AR manager: {e}")
            self.ar_overlay_enabled = False
    
    async def _initialize_telepresence_manager(self):
        """Initialize telepresence manager"""
        try:
            self.telepresence_manager = TelepresenceManager(self.holo_config.network)
            await self.telepresence_manager.initialize()
            
            logger.info("Telepresence manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize telepresence manager: {e}")
            # Continue without telepresence
            self.telepresence_manager = None
    
    async def _initialize_physics_manager(self):
        """Initialize physics manager"""
        try:
            physics_config = {
                'gravity': [0, -9.81, 0],
                'time_step': 1.0 / 60.0,
                'max_substeps': 10
            }
            
            self.physics_manager = HolographicPhysicsManager(physics_config)
            await self.physics_manager.initialize()
            
            logger.info("Physics manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize physics manager: {e}")
            # Continue without physics
            self.physics_manager = None
    
    async def _initialize_audio_manager(self):
        """Initialize spatial audio manager"""
        try:
            self.audio_manager = SpatialAudioManager(self.holo_config.audio)
            await self.audio_manager.initialize()
            
            logger.info("Spatial audio manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize audio manager: {e}")
            self.spatial_audio_enabled = False
    
    async def _initialize_kenny_integrations(self):
        """Initialize Kenny-specific integration components"""
        try:
            # Screen monitor integration
            from .screen_monitor_integration import ScreenMonitorIntegration
            self.screen_monitor_integration = ScreenMonitorIntegration(self)
            await self.screen_monitor_integration.initialize()
            
            # AI command integration
            from .ai_command_integration import AICommandIntegration
            self.ai_command_integration = AICommandIntegration(self)
            await self.ai_command_integration.initialize()
            
            # Workflow integration
            from .workflow_integration import WorkflowIntegration
            self.workflow_integration = WorkflowIntegration(self)
            await self.workflow_integration.initialize()
            
            logger.info("Kenny integration components initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kenny integrations: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown all holographic systems"""
        logger.info("Shutting down Kenny holographic integration...")
        
        # Shutdown holographic engine
        if self.holographic_engine:
            await self.holographic_engine.shutdown()
        
        # Shutdown all managers
        managers = [
            self.display_manager,
            self.gesture_manager,
            self.telepresence_manager,
            self.ar_manager,
            self.physics_manager,
            self.audio_manager
        ]
        
        for manager in managers:
            if manager:
                try:
                    await manager.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down manager: {e}")
        
        # Shutdown Kenny integrations
        integrations = [
            self.screen_monitor_integration,
            self.ai_command_integration,
            self.workflow_integration
        ]
        
        for integration in integrations:
            if integration:
                try:
                    await integration.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down integration: {e}")
        
        # Clear data
        self.holographic_overlays.clear()
        self.current_screen_data = None
        
        self.initialized = False
        logger.info("Kenny holographic integration shutdown complete")
    
    async def enable_holographic_mode(self):
        """Enable full holographic mode"""
        if not self.initialized:
            await self.initialize()
        
        self.holographic_mode_enabled = True
        
        # Start all systems
        if self.display_manager:
            # Switch to primary display
            self.display_manager.set_active_display("primary")
        
        if self.gesture_manager:
            await self.gesture_manager.start_tracking()
        
        if self.audio_manager:
            await self.audio_manager.start_processing()
        
        if self.physics_manager:
            await self.physics_manager.start_simulation()
        
        logger.info("Holographic mode enabled")
    
    async def disable_holographic_mode(self):
        """Disable holographic mode"""
        self.holographic_mode_enabled = False
        
        # Stop systems
        if self.gesture_manager:
            await self.gesture_manager.stop_tracking()
        
        if self.audio_manager:
            await self.audio_manager.stop_processing()
        
        if self.physics_manager:
            await self.physics_manager.stop_simulation()
        
        # Clear overlays
        self.holographic_overlays.clear()
        
        logger.info("Holographic mode disabled")
    
    async def update_screen_data(self, screenshot_path: str, ocr_text: List[str],
                               ui_elements: List[Dict[str, Any]], 
                               screen_resolution: Tuple[int, int]):
        """Update current screen data from Kenny's screen monitor"""
        self.current_screen_data = KennyScreenData(
            screenshot_path=screenshot_path,
            timestamp=time.time(),
            ocr_text=ocr_text,
            ui_elements=ui_elements,
            detected_objects=[],  # Will be populated by analysis
            screen_resolution=screen_resolution
        )
        
        # Process screen data for holographic overlays
        if self.holographic_mode_enabled:
            await self._process_screen_for_holograms()
        
        # Trigger events
        await self._trigger_event('screen_updated', self.current_screen_data)
    
    async def _process_screen_for_holograms(self):
        """Process screen data to create holographic overlays"""
        if not self.current_screen_data:
            return
        
        # Create holographic overlays for UI elements
        for ui_element in self.current_screen_data.ui_elements:
            await self._create_ui_hologram(ui_element)
        
        # Create text holograms for important OCR text
        await self._create_text_holograms(self.current_screen_data.ocr_text)
        
        # Update AR overlays
        if self.ar_manager:
            await self._update_ar_overlays()
    
    async def _create_ui_hologram(self, ui_element: Dict[str, Any]):
        """Create holographic overlay for UI element"""
        try:
            element_id = ui_element.get('id', f"ui_{len(self.holographic_overlays)}")
            
            # Convert screen coordinates to 3D position
            screen_x = ui_element.get('x', 0)
            screen_y = ui_element.get('y', 0)
            
            # Map screen coordinates to 3D space
            position = self._screen_to_3d_position(screen_x, screen_y)
            
            # Create holographic overlay
            overlay = HolographicOverlay(
                overlay_id=element_id,
                position=position,
                content_type='ui_element',
                content_data=ui_element,
                visibility=0.8,
                duration=5.0,  # 5 seconds
                interactive=True
            )
            
            self.holographic_overlays[element_id] = overlay
            
            # Add to display manager
            if self.display_manager:
                display = self.display_manager.get_active_display()
                if display:
                    await display.add_voxel(
                        "default",
                        position,
                        (0.2, 0.8, 1.0, 0.8),  # Blue holographic color
                        intensity=1.0,
                        size=0.05
                    )
            
        except Exception as e:
            logger.error(f"Error creating UI hologram: {e}")
    
    async def _create_text_holograms(self, ocr_text: List[str]):
        """Create holographic overlays for important text"""
        try:
            important_keywords = ['error', 'warning', 'success', 'complete', 'failed', 'ok', 'cancel']
            
            for i, text in enumerate(ocr_text):
                text_lower = text.lower()
                
                # Check if text contains important keywords
                if any(keyword in text_lower for keyword in important_keywords):
                    text_id = f"text_{i}"
                    
                    # Position text holograms in a line
                    position = Vector3D(-2.0 + i * 0.5, 1.0, -1.0)
                    
                    overlay = HolographicOverlay(
                        overlay_id=text_id,
                        position=position,
                        content_type='text',
                        content_data=text,
                        visibility=0.9,
                        duration=3.0,
                        interactive=False
                    )
                    
                    self.holographic_overlays[text_id] = overlay
                    
                    # Add to display manager with color based on content
                    if self.display_manager:
                        display = self.display_manager.get_active_display()
                        if display:
                            color = self._get_text_color(text_lower)
                            await display.add_voxel(
                                "default",
                                position,
                                color,
                                intensity=1.0,
                                size=0.03
                            )
            
        except Exception as e:
            logger.error(f"Error creating text holograms: {e}")
    
    def _get_text_color(self, text: str) -> Tuple[float, float, float, float]:
        """Get holographic color based on text content"""
        if any(word in text for word in ['error', 'failed', 'warning']):
            return (1.0, 0.2, 0.2, 0.9)  # Red
        elif any(word in text for word in ['success', 'complete', 'ok']):
            return (0.2, 1.0, 0.2, 0.9)  # Green
        elif any(word in text for word in ['info', 'notice']):
            return (0.2, 0.2, 1.0, 0.9)  # Blue
        else:
            return (1.0, 1.0, 1.0, 0.8)  # White
    
    def _screen_to_3d_position(self, screen_x: int, screen_y: int) -> Vector3D:
        """Convert screen coordinates to 3D holographic position"""
        if not self.current_screen_data:
            return Vector3D(0, 0, 0)
        
        width, height = self.current_screen_data.screen_resolution
        
        # Normalize screen coordinates
        norm_x = (screen_x / width) * 2.0 - 1.0  # -1 to 1
        norm_y = (1.0 - screen_y / height) * 2.0 - 1.0  # -1 to 1 (inverted Y)
        
        # Map to 3D space
        return Vector3D(norm_x * 2.0, norm_y * 1.5, -0.5)
    
    async def _update_ar_overlays(self):
        """Update AR overlays based on current screen"""
        if not self.ar_manager:
            return
        
        try:
            # Update AR overlays for each holographic overlay
            for overlay_id, overlay in self.holographic_overlays.items():
                if overlay.interactive:
                    await self.ar_manager.add_virtual_object(
                        overlay_id,
                        overlay.content_type,
                        overlay.position,
                        Vector3D(0.1, 0.1, 0.1),  # Small scale
                        {'color': (0.2, 0.8, 1.0), 'transparency': 0.2}
                    )
            
        except Exception as e:
            logger.error(f"Error updating AR overlays: {e}")
    
    async def execute_holographic_command(self, command: str, parameters: Dict[str, Any] = None) -> bool:
        """Execute a holographic command"""
        try:
            params = parameters or {}
            
            if command == "create_hologram":
                return await self._create_custom_hologram(params)
            
            elif command == "play_spatial_audio":
                return await self._play_spatial_audio(params)
            
            elif command == "start_telepresence":
                return await self._start_telepresence(params)
            
            elif command == "enable_gesture_control":
                return await self._enable_gesture_control(params)
            
            elif command == "create_physics_object":
                return await self._create_physics_object(params)
            
            else:
                logger.warning(f"Unknown holographic command: {command}")
                return False
            
        except Exception as e:
            logger.error(f"Error executing holographic command {command}: {e}")
            return False
    
    async def _create_custom_hologram(self, params: Dict[str, Any]) -> bool:
        """Create custom hologram"""
        position = Vector3D(**params.get('position', {'x': 0, 'y': 0, 'z': 0}))
        color = params.get('color', (0.2, 0.8, 1.0, 0.8))
        size = params.get('size', 0.1)
        
        if self.display_manager:
            display = self.display_manager.get_active_display()
            if display:
                hologram_id = await display.add_voxel("default", position, color, 1.0, size)
                return hologram_id is not None
        
        return False
    
    async def _play_spatial_audio(self, params: Dict[str, Any]) -> bool:
        """Play spatial audio"""
        if not self.audio_manager:
            return False
        
        position = Vector3D(**params.get('position', {'x': 0, 'y': 0, 'z': 0}))
        audio_file = params.get('audio_file', '')
        
        # Load audio file (simplified)
        import numpy as np
        audio_data = np.random.random(44100).astype(np.float32)  # 1 second of noise
        
        from ..audio import AudioSourceType
        source_id = await self.audio_manager.add_audio_source(
            f"spatial_{int(time.time())}",
            AudioSourceType.POINT,
            position,
            audio_data
        )
        
        if source_id:
            await self.audio_manager.play_audio_source(source_id)
            return True
        
        return False
    
    async def _start_telepresence(self, params: Dict[str, Any]) -> bool:
        """Start telepresence session"""
        if not self.telepresence_manager:
            return False
        
        server_url = params.get('server_url', 'localhost:8080')
        return await self.telepresence_manager.connect_to_server(server_url)
    
    async def _enable_gesture_control(self, params: Dict[str, Any]) -> bool:
        """Enable gesture control"""
        if not self.gesture_manager:
            return False
        
        await self.gesture_manager.start_tracking()
        return True
    
    async def _create_physics_object(self, params: Dict[str, Any]) -> bool:
        """Create physics object"""
        if not self.physics_manager:
            return False
        
        from ..physics import PhysicsBodyType, PhysicsProperties
        
        object_id = params.get('object_id', f"physics_{int(time.time())}")
        position = Vector3D(**params.get('position', {'x': 0, 'y': 0, 'z': 0}))
        
        properties = PhysicsProperties(
            mass=params.get('mass', 1.0),
            restitution=params.get('restitution', 0.5),
            friction=params.get('friction', 0.5)
        )
        
        return await self.physics_manager.add_physics_body(
            object_id,
            PhysicsBodyType.DYNAMIC,
            position,
            properties
        )
    
    async def _on_gesture_detected(self, gesture_data: Dict[str, Any]):
        """Handle detected gesture"""
        try:
            gesture_type = gesture_data.get('type', 'unknown')
            confidence = gesture_data.get('confidence', 0.0)
            
            if confidence < 0.8:
                return
            
            # Map gestures to Kenny commands
            if gesture_type == 'point':
                # Trigger click at pointed location
                target_position = gesture_data.get('target_position')
                if target_position and self.ai_command_integration:
                    await self.ai_command_integration.execute_gesture_command('click', target_position)
            
            elif gesture_type == 'swipe_right':
                # Next item/page
                if self.ai_command_integration:
                    await self.ai_command_integration.execute_gesture_command('next', {})
            
            elif gesture_type == 'swipe_left':
                # Previous item/page
                if self.ai_command_integration:
                    await self.ai_command_integration.execute_gesture_command('previous', {})
            
            elif gesture_type == 'pinch':
                # Zoom/select
                if self.ai_command_integration:
                    await self.ai_command_integration.execute_gesture_command('select', gesture_data)
            
            # Trigger event
            await self._trigger_event('gesture_detected', gesture_data)
            
        except Exception as e:
            logger.error(f"Error handling gesture: {e}")
    
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
    
    def get_holographic_status(self) -> Dict[str, Any]:
        """Get status of all holographic systems"""
        return {
            "holographic_mode_enabled": self.holographic_mode_enabled,
            "ar_overlay_enabled": self.ar_overlay_enabled,
            "gesture_control_enabled": self.gesture_control_enabled,
            "spatial_audio_enabled": self.spatial_audio_enabled,
            "active_overlays": len(self.holographic_overlays),
            "display_manager": self.display_manager is not None and self.display_manager.initialized,
            "gesture_manager": self.gesture_manager is not None and self.gesture_manager.initialized,
            "telepresence_manager": self.telepresence_manager is not None and self.telepresence_manager.initialized,
            "ar_manager": self.ar_manager is not None and self.ar_manager.initialized,
            "physics_manager": self.physics_manager is not None and self.physics_manager.initialized,
            "audio_manager": self.audio_manager is not None and self.audio_manager.initialized,
            "engine_running": self.holographic_engine is not None and self.holographic_engine.running,
            "current_screen_data": self.current_screen_data is not None
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from all systems"""
        metrics = {}
        
        if self.holographic_engine:
            metrics["engine"] = self.holographic_engine.get_performance_metrics()
        
        if self.display_manager:
            display = self.display_manager.get_active_display()
            if display:
                metrics["display"] = display.get_performance_stats()
        
        if self.gesture_manager:
            metrics["gestures"] = self.gesture_manager.get_performance_stats()
        
        if self.audio_manager:
            metrics["audio"] = self.audio_manager.get_performance_stats()
        
        if self.physics_manager:
            metrics["physics"] = self.physics_manager.get_performance_stats()
        
        return metrics