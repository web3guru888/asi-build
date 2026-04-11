"""
Main holographic engine - orchestrates all holographic components
"""

import asyncio
import logging
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from .base import (
    HolographicBase, 
    HolographicPerformanceMonitor,
    InitializationError,
    Vector3D,
    Transform3D
)
from .config import HolographicConfig
from .event_system import HolographicEventSystem
from .math_utils import SpatialMath

logger = logging.getLogger(__name__)

class HolographicEngine(HolographicBase):
    """
    Main holographic engine that orchestrates all holographic components
    """
    
    def __init__(self, config: Optional[HolographicConfig] = None):
        super().__init__("HolographicEngine")
        self.config = config or HolographicConfig()
        self.event_system = HolographicEventSystem()
        self.performance_monitor = HolographicPerformanceMonitor()
        
        # Component managers
        self.display_manager = None
        self.gesture_manager = None
        self.audio_manager = None
        self.visualization_manager = None
        self.telepresence_manager = None
        self.ar_manager = None
        self.storage_manager = None
        self.physics_manager = None
        self.security_manager = None
        self.networking_manager = None
        
        # Runtime state
        self.running = False
        self.paused = False
        self.frame_count = 0
        self.last_frame_time = 0.0
        self.target_fps = self.config.performance.max_fps
        self.frame_time = 1.0 / self.target_fps
        
        # Threading
        self.main_loop_task = None
        self.update_executor = ThreadPoolExecutor(max_workers=8)
        
        # Callbacks
        self.update_callbacks = []
        self.render_callbacks = []
        self.frame_callbacks = []
        
        logger.info(f"HolographicEngine initialized with config: {self.config.get_config_dict()}")
    
    async def initialize(self) -> bool:
        """Initialize the holographic engine and all components"""
        try:
            logger.info("Initializing HolographicEngine...")
            
            # Validate configuration
            if not self.config.validate_config():
                raise InitializationError("Invalid configuration")
            
            # Initialize event system
            await self.event_system.initialize()
            
            # Initialize component managers (imported dynamically to avoid circular imports)
            await self._initialize_display_manager()
            await self._initialize_gesture_manager()
            await self._initialize_audio_manager()
            await self._initialize_visualization_manager()
            await self._initialize_telepresence_manager()
            await self._initialize_ar_manager()
            await self._initialize_storage_manager()
            await self._initialize_physics_manager()
            await self._initialize_security_manager()
            await self._initialize_networking_manager()
            
            # Subscribe to system events
            self.event_system.subscribe("system.shutdown", self._on_system_shutdown)
            self.event_system.subscribe("system.pause", self._on_system_pause)
            self.event_system.subscribe("system.resume", self._on_system_resume)
            self.event_system.subscribe("config.updated", self._on_config_updated)
            
            self.initialized = True
            logger.info("HolographicEngine initialized successfully")
            
            # Emit initialization complete event
            await self.event_system.emit("engine.initialized", {"engine_id": self.id})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize HolographicEngine: {e}")
            raise InitializationError(f"Engine initialization failed: {e}")
    
    async def _initialize_display_manager(self):
        """Initialize display manager"""
        try:
            from ..display import VolumetricDisplayManager
            self.display_manager = VolumetricDisplayManager(self.config.display)
            await self.display_manager.initialize()
            logger.info("Display manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize display manager: {e}")
            raise
    
    async def _initialize_gesture_manager(self):
        """Initialize gesture manager"""
        try:
            from ..gestures import GestureManager
            self.gesture_manager = GestureManager(self.config.gesture)
            await self.gesture_manager.initialize()
            logger.info("Gesture manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize gesture manager: {e}")
            raise
    
    async def _initialize_audio_manager(self):
        """Initialize spatial audio manager"""
        try:
            from ..audio import SpatialAudioManager
            self.audio_manager = SpatialAudioManager(self.config.audio)
            await self.audio_manager.initialize()
            logger.info("Audio manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize audio manager: {e}")
            raise
    
    async def _initialize_visualization_manager(self):
        """Initialize visualization manager"""
        try:
            from ..visualization import HolographicVisualizationManager
            self.visualization_manager = HolographicVisualizationManager(self.config.rendering)
            await self.visualization_manager.initialize()
            logger.info("Visualization manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize visualization manager: {e}")
            raise
    
    async def _initialize_telepresence_manager(self):
        """Initialize telepresence manager"""
        try:
            from ..telepresence import TelepresenceManager
            self.telepresence_manager = TelepresenceManager(self.config.network)
            await self.telepresence_manager.initialize()
            logger.info("Telepresence manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize telepresence manager: {e}")
            raise
    
    async def _initialize_ar_manager(self):
        """Initialize AR overlay manager"""
        try:
            from ..ar_overlay import AROverlayManager
            self.ar_manager = AROverlayManager(self.config.display)
            await self.ar_manager.initialize()
            logger.info("AR manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AR manager: {e}")
            raise
    
    async def _initialize_storage_manager(self):
        """Initialize holographic storage manager"""
        try:
            from ..storage import HolographicStorageManager
            self.storage_manager = HolographicStorageManager(self.config.security)
            await self.storage_manager.initialize()
            logger.info("Storage manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize storage manager: {e}")
            raise
    
    async def _initialize_physics_manager(self):
        """Initialize physics manager"""
        try:
            from ..physics import HolographicPhysicsManager
            self.physics_manager = HolographicPhysicsManager(self.config.performance)
            await self.physics_manager.initialize()
            logger.info("Physics manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize physics manager: {e}")
            raise
    
    async def _initialize_security_manager(self):
        """Initialize security manager"""
        try:
            from ..security import HolographicSecurityManager
            self.security_manager = HolographicSecurityManager(self.config.security)
            await self.security_manager.initialize()
            logger.info("Security manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize security manager: {e}")
            raise
    
    async def _initialize_networking_manager(self):
        """Initialize networking manager"""
        try:
            from ..networking import HolographicNetworkManager
            self.networking_manager = HolographicNetworkManager(self.config.network)
            await self.networking_manager.initialize()
            logger.info("Networking manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize networking manager: {e}")
            raise
    
    async def start(self):
        """Start the holographic engine main loop"""
        if not self.initialized:
            await self.initialize()
        
        if self.running:
            logger.warning("Engine is already running")
            return
        
        logger.info("Starting HolographicEngine main loop...")
        self.running = True
        self.last_frame_time = time.perf_counter()
        
        # Start the main loop
        self.main_loop_task = asyncio.create_task(self._main_loop())
        
        # Emit engine started event
        await self.event_system.emit("engine.started", {"engine_id": self.id})
        
        logger.info("HolographicEngine started successfully")
    
    async def stop(self):
        """Stop the holographic engine"""
        if not self.running:
            return
        
        logger.info("Stopping HolographicEngine...")
        self.running = False
        
        # Cancel main loop
        if self.main_loop_task:
            self.main_loop_task.cancel()
            try:
                await self.main_loop_task
            except asyncio.CancelledError:
                pass
        
        # Emit engine stopped event
        await self.event_system.emit("engine.stopped", {"engine_id": self.id})
        
        logger.info("HolographicEngine stopped")
    
    async def pause(self):
        """Pause the holographic engine"""
        if not self.running or self.paused:
            return
        
        logger.info("Pausing HolographicEngine...")
        self.paused = True
        
        # Pause all managers
        managers = [
            self.display_manager, self.gesture_manager, self.audio_manager,
            self.visualization_manager, self.telepresence_manager, self.ar_manager,
            self.storage_manager, self.physics_manager, self.security_manager,
            self.networking_manager
        ]
        
        for manager in managers:
            if manager and hasattr(manager, 'pause'):
                await manager.pause()
        
        await self.event_system.emit("engine.paused", {"engine_id": self.id})
        logger.info("HolographicEngine paused")
    
    async def resume(self):
        """Resume the holographic engine"""
        if not self.running or not self.paused:
            return
        
        logger.info("Resuming HolographicEngine...")
        self.paused = False
        
        # Resume all managers
        managers = [
            self.display_manager, self.gesture_manager, self.audio_manager,
            self.visualization_manager, self.telepresence_manager, self.ar_manager,
            self.storage_manager, self.physics_manager, self.security_manager,
            self.networking_manager
        ]
        
        for manager in managers:
            if manager and hasattr(manager, 'resume'):
                await manager.resume()
        
        await self.event_system.emit("engine.resumed", {"engine_id": self.id})
        logger.info("HolographicEngine resumed")
    
    async def _main_loop(self):
        """Main engine update loop"""
        logger.info("HolographicEngine main loop started")
        
        try:
            while self.running:
                if self.paused:
                    await asyncio.sleep(0.1)
                    continue
                
                # Calculate frame timing
                current_time = time.perf_counter()
                delta_time = current_time - self.last_frame_time
                
                self.performance_monitor.start_timer("frame")
                
                # Update all systems
                await self._update_frame(delta_time)
                
                # Render frame
                await self._render_frame(delta_time)
                
                # Frame complete
                await self._complete_frame(delta_time)
                
                frame_duration = self.performance_monitor.end_timer("frame")
                
                # Frame rate limiting
                if frame_duration < self.frame_time:
                    sleep_time = self.frame_time - frame_duration
                    await asyncio.sleep(sleep_time)
                
                self.last_frame_time = current_time
                self.frame_count += 1
                
                # Log performance every 60 frames
                if self.frame_count % 60 == 0:
                    fps = self.performance_monitor.get_fps("frame")
                    logger.debug(f"Engine FPS: {fps:.1f}, Frame: {self.frame_count}")
                
        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await self.event_system.emit("engine.error", {"error": str(e), "engine_id": self.id})
        finally:
            logger.info("HolographicEngine main loop ended")
    
    async def _update_frame(self, delta_time: float):
        """Update all systems for current frame"""
        # Update all managers
        update_tasks = []
        
        managers = [
            self.display_manager, self.gesture_manager, self.audio_manager,
            self.visualization_manager, self.telepresence_manager, self.ar_manager,
            self.storage_manager, self.physics_manager, self.security_manager,
            self.networking_manager
        ]
        
        for manager in managers:
            if manager and manager.is_enabled():
                update_tasks.append(manager.update(delta_time))
        
        # Update in parallel
        if update_tasks:
            await asyncio.gather(*update_tasks, return_exceptions=True)
        
        # Call update callbacks
        for callback in self.update_callbacks:
            try:
                await callback(delta_time)
            except Exception as e:
                logger.error(f"Error in update callback: {e}")
    
    async def _render_frame(self, delta_time: float):
        """Render current frame"""
        if self.display_manager and self.display_manager.is_enabled():
            await self.display_manager.render()
        
        # Call render callbacks
        for callback in self.render_callbacks:
            try:
                await callback(delta_time)
            except Exception as e:
                logger.error(f"Error in render callback: {e}")
    
    async def _complete_frame(self, delta_time: float):
        """Complete frame processing"""
        # Call frame callbacks
        for callback in self.frame_callbacks:
            try:
                await callback(delta_time, self.frame_count)
            except Exception as e:
                logger.error(f"Error in frame callback: {e}")
        
        # Emit frame complete event
        if self.frame_count % 30 == 0:  # Every 30 frames
            await self.event_system.emit("engine.frame_batch", {
                "frame_count": self.frame_count,
                "fps": self.performance_monitor.get_fps("frame"),
                "engine_id": self.id
            })
    
    def add_update_callback(self, callback: Callable):
        """Add update callback"""
        if callback not in self.update_callbacks:
            self.update_callbacks.append(callback)
    
    def remove_update_callback(self, callback: Callable):
        """Remove update callback"""
        if callback in self.update_callbacks:
            self.update_callbacks.remove(callback)
    
    def add_render_callback(self, callback: Callable):
        """Add render callback"""
        if callback not in self.render_callbacks:
            self.render_callbacks.append(callback)
    
    def remove_render_callback(self, callback: Callable):
        """Remove render callback"""
        if callback in self.render_callbacks:
            self.render_callbacks.remove(callback)
    
    def add_frame_callback(self, callback: Callable):
        """Add frame callback"""
        if callback not in self.frame_callbacks:
            self.frame_callbacks.append(callback)
    
    def remove_frame_callback(self, callback: Callable):
        """Remove frame callback"""
        if callback in self.frame_callbacks:
            self.frame_callbacks.remove(callback)
    
    async def shutdown(self):
        """Shutdown the holographic engine"""
        logger.info("Shutting down HolographicEngine...")
        
        # Stop the engine
        await self.stop()
        
        # Shutdown all managers
        managers = [
            self.display_manager, self.gesture_manager, self.audio_manager,
            self.visualization_manager, self.telepresence_manager, self.ar_manager,
            self.storage_manager, self.physics_manager, self.security_manager,
            self.networking_manager
        ]
        
        for manager in managers:
            if manager:
                try:
                    await manager.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down manager {manager.__class__.__name__}: {e}")
        
        # Shutdown event system
        await self.event_system.shutdown()
        
        # Clear callbacks
        self.update_callbacks.clear()
        self.render_callbacks.clear()
        self.frame_callbacks.clear()
        
        # Shutdown executor
        self.update_executor.shutdown(wait=True)
        
        self.initialized = False
        logger.info("HolographicEngine shutdown complete")
    
    async def _on_system_shutdown(self, event_data: Dict[str, Any]):
        """Handle system shutdown event"""
        await self.shutdown()
    
    async def _on_system_pause(self, event_data: Dict[str, Any]):
        """Handle system pause event"""
        await self.pause()
    
    async def _on_system_resume(self, event_data: Dict[str, Any]):
        """Handle system resume event"""
        await self.resume()
    
    async def _on_config_updated(self, event_data: Dict[str, Any]):
        """Handle configuration update event"""
        logger.info("Configuration updated, applying changes...")
        
        # Update target FPS
        self.target_fps = self.config.performance.max_fps
        self.frame_time = 1.0 / self.target_fps
        
        # Notify all managers of config update
        managers = [
            self.display_manager, self.gesture_manager, self.audio_manager,
            self.visualization_manager, self.telepresence_manager, self.ar_manager,
            self.storage_manager, self.physics_manager, self.security_manager,
            self.networking_manager
        ]
        
        for manager in managers:
            if manager and hasattr(manager, 'on_config_updated'):
                try:
                    await manager.on_config_updated(self.config)
                except Exception as e:
                    logger.error(f"Error updating config for {manager.__class__.__name__}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        return {
            "engine_id": self.id,
            "running": self.running,
            "paused": self.paused,
            "initialized": self.initialized,
            "frame_count": self.frame_count,
            "fps": self.performance_monitor.get_fps("frame"),
            "target_fps": self.target_fps,
            "managers": {
                "display": self.display_manager is not None and self.display_manager.is_enabled(),
                "gesture": self.gesture_manager is not None and self.gesture_manager.is_enabled(),
                "audio": self.audio_manager is not None and self.audio_manager.is_enabled(),
                "visualization": self.visualization_manager is not None and self.visualization_manager.is_enabled(),
                "telepresence": self.telepresence_manager is not None and self.telepresence_manager.is_enabled(),
                "ar": self.ar_manager is not None and self.ar_manager.is_enabled(),
                "storage": self.storage_manager is not None and self.storage_manager.is_enabled(),
                "physics": self.physics_manager is not None and self.physics_manager.is_enabled(),
                "security": self.security_manager is not None and self.security_manager.is_enabled(),
                "networking": self.networking_manager is not None and self.networking_manager.is_enabled()
            }
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            "fps": self.performance_monitor.get_fps("frame"),
            "frame_count": self.frame_count,
            "frame_time_avg": self.performance_monitor.get_average_time("frame"),
            "update_time_avg": self.performance_monitor.get_average_time("update"),
            "render_time_avg": self.performance_monitor.get_average_time("render"),
            "memory_usage": self._get_memory_usage(),
            "gpu_usage": self._get_gpu_usage()
        }
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage statistics"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent()
            }
        except ImportError:
            return {"error": "psutil not available"}
    
    def _get_gpu_usage(self) -> Dict[str, Any]:
        """Get GPU usage statistics"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                return {
                    "utilization": gpu.load * 100,
                    "memory_used": gpu.memoryUsed,
                    "memory_total": gpu.memoryTotal,
                    "memory_percent": (gpu.memoryUsed / gpu.memoryTotal) * 100,
                    "temperature": gpu.temperature
                }
        except ImportError:
            pass
        return {"error": "GPU monitoring not available"}