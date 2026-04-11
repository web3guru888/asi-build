"""
Volumetric display system for true 3D holographic rendering
"""

import numpy as np
import asyncio
import logging
import time
import threading
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import math

from ..core.base import (
    HolographicBase, 
    Vector3D, 
    Transform3D,
    HolographicPerformanceMonitor,
    RenderingError
)
from ..core.config import DisplayConfig

logger = logging.getLogger(__name__)

@dataclass
class VoxelData:
    """3D voxel data for volumetric rendering"""
    position: Vector3D
    color: Tuple[float, float, float, float]  # RGBA
    intensity: float
    size: float
    active: bool = True
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array for GPU processing"""
        return np.array([
            self.position.x, self.position.y, self.position.z,
            self.color[0], self.color[1], self.color[2], self.color[3],
            self.intensity, self.size, float(self.active)
        ])

@dataclass
class VolumetricLayer:
    """Layer in volumetric display"""
    layer_id: str
    depth: float
    resolution: Tuple[int, int]
    voxels: List[VoxelData]
    opacity: float = 1.0
    blend_mode: str = "alpha"  # alpha, additive, multiply
    enabled: bool = True

class VolumeRenderer:
    """Advanced volume rendering engine"""
    
    def __init__(self, resolution: Tuple[int, int, int]):
        self.resolution = resolution  # X, Y, Z resolution
        self.width, self.height, self.depth = resolution
        
        # Volume data
        self.volume_data = np.zeros(resolution + (4,), dtype=np.float32)  # RGBA
        self.density_data = np.zeros(resolution, dtype=np.float32)
        
        # Rendering parameters
        self.step_size = 1.0 / max(resolution)
        self.opacity_threshold = 0.01
        self.max_samples = 512
        
        # Transfer functions
        self.color_transfer = np.zeros((256, 4), dtype=np.float32)
        self.opacity_transfer = np.zeros(256, dtype=np.float32)
        
        # GPU acceleration (if available)
        self.gpu_enabled = False
        self.gpu_context = None
        
        self._init_transfer_functions()
        self._init_gpu_resources()
    
    def _init_transfer_functions(self):
        """Initialize default transfer functions"""
        # Linear color ramp from blue to red
        for i in range(256):
            t = i / 255.0
            self.color_transfer[i] = [t, 0.5, 1.0 - t, 1.0]
            self.opacity_transfer[i] = t
    
    def _init_gpu_resources(self):
        """Initialize GPU resources if available"""
        try:
            # Attempt to initialize GPU context (OpenGL/Vulkan/CUDA)
            # This is a placeholder for actual GPU initialization
            self.gpu_enabled = False  # Set to True when GPU is available
            logger.info("GPU acceleration not available, using CPU rendering")
        except Exception as e:
            logger.warning(f"Failed to initialize GPU resources: {e}")
            self.gpu_enabled = False
    
    def set_volume_data(self, data: np.ndarray):
        """Set volume data for rendering"""
        if data.shape[:3] != self.resolution:
            raise ValueError(f"Data shape {data.shape} doesn't match resolution {self.resolution}")
        
        if len(data.shape) == 3:
            # Grayscale volume, convert to RGBA
            self.volume_data[:,:,:,0] = data
            self.volume_data[:,:,:,1] = data
            self.volume_data[:,:,:,2] = data
            self.volume_data[:,:,:,3] = np.ones_like(data)
        elif len(data.shape) == 4 and data.shape[3] == 4:
            # RGBA volume
            self.volume_data = data.astype(np.float32)
        else:
            raise ValueError(f"Unsupported data format: {data.shape}")
        
        # Update density data
        self.density_data = np.sqrt(np.sum(self.volume_data[:,:,:,:3]**2, axis=3))
    
    def add_voxel(self, position: Vector3D, color: Tuple[float, float, float, float], 
                  intensity: float = 1.0):
        """Add a voxel to the volume"""
        # Convert world position to voxel coordinates
        x = int((position.x + 1.0) * 0.5 * self.width)
        y = int((position.y + 1.0) * 0.5 * self.height)
        z = int((position.z + 1.0) * 0.5 * self.depth)
        
        # Bounds checking
        if 0 <= x < self.width and 0 <= y < self.height and 0 <= z < self.depth:
            self.volume_data[x, y, z] = np.array(color) * intensity
            self.density_data[x, y, z] = intensity
    
    def clear_volume(self):
        """Clear all volume data"""
        self.volume_data.fill(0)
        self.density_data.fill(0)
    
    def render_slice(self, slice_depth: float, view_matrix: np.ndarray, 
                    projection_matrix: np.ndarray) -> np.ndarray:
        """Render a single depth slice"""
        # Convert slice depth to voxel coordinate
        z_index = int(slice_depth * self.depth)
        z_index = max(0, min(z_index, self.depth - 1))
        
        # Get slice data
        slice_data = self.volume_data[:, :, z_index]
        
        # Apply transfer functions
        rendered_slice = np.zeros((self.height, self.width, 4), dtype=np.float32)
        
        for y in range(self.height):
            for x in range(self.width):
                color = slice_data[x, y]
                density = self.density_data[x, y, z_index]
                
                if density > self.opacity_threshold:
                    # Apply transfer function
                    density_index = int(density * 255)
                    density_index = max(0, min(density_index, 255))
                    
                    opacity = self.opacity_transfer[density_index]
                    transfer_color = self.color_transfer[density_index]
                    
                    # Blend colors
                    final_color = color[:3] * transfer_color[:3]
                    final_alpha = color[3] * opacity
                    
                    rendered_slice[y, x] = [final_color[0], final_color[1], 
                                          final_color[2], final_alpha]
        
        return rendered_slice
    
    def render_volume(self, view_matrix: np.ndarray, projection_matrix: np.ndarray,
                     camera_position: Vector3D) -> np.ndarray:
        """Render the complete volume using ray marching"""
        if self.gpu_enabled:
            return self._render_volume_gpu(view_matrix, projection_matrix, camera_position)
        else:
            return self._render_volume_cpu(view_matrix, projection_matrix, camera_position)
    
    def _render_volume_cpu(self, view_matrix: np.ndarray, projection_matrix: np.ndarray,
                          camera_position: Vector3D) -> np.ndarray:
        """CPU-based volume rendering"""
        output = np.zeros((self.height, self.width, 4), dtype=np.float32)
        
        # Create rays for each pixel
        for y in range(self.height):
            for x in range(self.width):
                # Convert screen coordinates to world ray
                ray_origin, ray_direction = self._screen_to_ray(
                    x, y, view_matrix, projection_matrix, camera_position
                )
                
                # March along the ray
                color = self._march_ray(ray_origin, ray_direction)
                output[y, x] = color
        
        return output
    
    def _render_volume_gpu(self, view_matrix: np.ndarray, projection_matrix: np.ndarray,
                          camera_position: Vector3D) -> np.ndarray:
        """GPU-accelerated volume rendering"""
        # Placeholder for GPU implementation
        # Would use OpenGL compute shaders, CUDA, or Vulkan
        logger.warning("GPU rendering not implemented, falling back to CPU")
        return self._render_volume_cpu(view_matrix, projection_matrix, camera_position)
    
    def _screen_to_ray(self, screen_x: int, screen_y: int, view_matrix: np.ndarray,
                      projection_matrix: np.ndarray, camera_position: Vector3D) -> Tuple[Vector3D, Vector3D]:
        """Convert screen coordinates to world ray"""
        # Normalize screen coordinates
        ndc_x = (2.0 * screen_x / self.width) - 1.0
        ndc_y = 1.0 - (2.0 * screen_y / self.height)
        
        # Convert to world coordinates
        inv_vp = np.linalg.inv(projection_matrix @ view_matrix)
        
        near_point = inv_vp @ np.array([ndc_x, ndc_y, -1.0, 1.0])
        far_point = inv_vp @ np.array([ndc_x, ndc_y, 1.0, 1.0])
        
        # Perspective divide
        near_point /= near_point[3]
        far_point /= far_point[3]
        
        ray_origin = Vector3D(near_point[0], near_point[1], near_point[2])
        ray_end = Vector3D(far_point[0], far_point[1], far_point[2])
        ray_direction = (ray_end - ray_origin).normalize()
        
        return ray_origin, ray_direction
    
    def _march_ray(self, ray_origin: Vector3D, ray_direction: Vector3D) -> np.ndarray:
        """March along ray and accumulate color"""
        color = np.array([0.0, 0.0, 0.0, 0.0])
        
        # Find intersection with volume bounds
        t_min, t_max = self._ray_box_intersection(ray_origin, ray_direction)
        
        if t_min >= t_max:
            return color
        
        # March along the ray
        t = t_min
        while t < t_max and color[3] < 0.95:  # Early termination
            # Current position
            pos = ray_origin + ray_direction * t
            
            # Sample volume at this position
            sample_color = self._sample_volume(pos)
            
            if sample_color[3] > 0:
                # Alpha blending
                alpha = sample_color[3] * self.step_size
                color[:3] = color[:3] * (1.0 - alpha) + sample_color[:3] * alpha
                color[3] = color[3] + alpha * (1.0 - color[3])
            
            t += self.step_size
        
        return color
    
    def _ray_box_intersection(self, ray_origin: Vector3D, ray_direction: Vector3D) -> Tuple[float, float]:
        """Calculate ray intersection with volume bounding box"""
        # Volume bounds [-1, 1] in all dimensions
        box_min = Vector3D(-1.0, -1.0, -1.0)
        box_max = Vector3D(1.0, 1.0, 1.0)
        
        # Calculate intersection
        inv_dir = Vector3D(
            1.0 / ray_direction.x if ray_direction.x != 0 else float('inf'),
            1.0 / ray_direction.y if ray_direction.y != 0 else float('inf'),
            1.0 / ray_direction.z if ray_direction.z != 0 else float('inf')
        )
        
        t1 = (box_min.x - ray_origin.x) * inv_dir.x
        t2 = (box_max.x - ray_origin.x) * inv_dir.x
        
        t_min = min(t1, t2)
        t_max = max(t1, t2)
        
        t1 = (box_min.y - ray_origin.y) * inv_dir.y
        t2 = (box_max.y - ray_origin.y) * inv_dir.y
        
        t_min = max(t_min, min(t1, t2))
        t_max = min(t_max, max(t1, t2))
        
        t1 = (box_min.z - ray_origin.z) * inv_dir.z
        t2 = (box_max.z - ray_origin.z) * inv_dir.z
        
        t_min = max(t_min, min(t1, t2))
        t_max = min(t_max, max(t1, t2))
        
        return max(0.0, t_min), max(0.0, t_max)
    
    def _sample_volume(self, position: Vector3D) -> np.ndarray:
        """Sample volume at world position using trilinear interpolation"""
        # Convert world position to voxel coordinates
        x = (position.x + 1.0) * 0.5 * (self.width - 1)
        y = (position.y + 1.0) * 0.5 * (self.height - 1)
        z = (position.z + 1.0) * 0.5 * (self.depth - 1)
        
        # Bounds checking
        if x < 0 or x >= self.width - 1 or y < 0 or y >= self.height - 1 or z < 0 or z >= self.depth - 1:
            return np.array([0.0, 0.0, 0.0, 0.0])
        
        # Trilinear interpolation
        x0, x1 = int(x), int(x) + 1
        y0, y1 = int(y), int(y) + 1
        z0, z1 = int(z), int(z) + 1
        
        xd = x - x0
        yd = y - y0
        zd = z - z0
        
        # Sample 8 neighboring voxels
        c000 = self.volume_data[x0, y0, z0]
        c001 = self.volume_data[x0, y0, z1]
        c010 = self.volume_data[x0, y1, z0]
        c011 = self.volume_data[x0, y1, z1]
        c100 = self.volume_data[x1, y0, z0]
        c101 = self.volume_data[x1, y0, z1]
        c110 = self.volume_data[x1, y1, z0]
        c111 = self.volume_data[x1, y1, z1]
        
        # Interpolate
        c00 = c000 * (1 - xd) + c100 * xd
        c01 = c001 * (1 - xd) + c101 * xd
        c10 = c010 * (1 - xd) + c110 * xd
        c11 = c011 * (1 - xd) + c111 * xd
        
        c0 = c00 * (1 - yd) + c10 * yd
        c1 = c01 * (1 - yd) + c11 * yd
        
        return c0 * (1 - zd) + c1 * zd

class VolumetricDisplay(HolographicBase):
    """Main volumetric display system"""
    
    def __init__(self, config: DisplayConfig):
        super().__init__("VolumetricDisplay")
        self.config = config
        self.performance_monitor = HolographicPerformanceMonitor()
        
        # Display parameters
        self.resolution = (config.resolution_x, config.resolution_y, config.resolution_z)
        self.field_of_view = math.radians(config.field_of_view)
        self.aspect_ratio = config.resolution_x / config.resolution_y
        
        # Volume renderer
        self.volume_renderer = VolumeRenderer(self.resolution)
        
        # Layers
        self.layers: Dict[str, VolumetricLayer] = {}
        self.layer_order: List[str] = []
        
        # View parameters
        self.camera_position = Vector3D(0, 0, 3)
        self.camera_target = Vector3D(0, 0, 0)
        self.camera_up = Vector3D(0, 1, 0)
        
        # Rendering state
        self.view_matrix = np.eye(4)
        self.projection_matrix = np.eye(4)
        self.current_frame = None
        
        # Threading
        self.render_executor = ThreadPoolExecutor(max_workers=4)
        self.rendering = False
        
        logger.info(f"VolumetricDisplay initialized with resolution {self.resolution}")
    
    async def initialize(self) -> bool:
        """Initialize the volumetric display"""
        try:
            logger.info("Initializing VolumetricDisplay...")
            
            # Initialize view matrices
            self._update_view_matrix()
            self._update_projection_matrix()
            
            # Create default layer
            await self.create_layer("default", 0.0)
            
            self.initialized = True
            logger.info("VolumetricDisplay initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize VolumetricDisplay: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the volumetric display"""
        logger.info("Shutting down VolumetricDisplay...")
        
        self.rendering = False
        
        # Clear all layers
        self.layers.clear()
        self.layer_order.clear()
        
        # Clear volume data
        self.volume_renderer.clear_volume()
        
        # Shutdown executor
        self.render_executor.shutdown(wait=True)
        
        self.initialized = False
        logger.info("VolumetricDisplay shutdown complete")
    
    async def create_layer(self, layer_id: str, depth: float, 
                          resolution: Optional[Tuple[int, int]] = None) -> VolumetricLayer:
        """Create a new volumetric layer"""
        if layer_id in self.layers:
            raise ValueError(f"Layer {layer_id} already exists")
        
        if resolution is None:
            resolution = (self.config.resolution_x, self.config.resolution_y)
        
        layer = VolumetricLayer(
            layer_id=layer_id,
            depth=depth,
            resolution=resolution,
            voxels=[]
        )
        
        self.layers[layer_id] = layer
        
        # Insert in depth order
        self.layer_order.append(layer_id)
        self.layer_order.sort(key=lambda lid: self.layers[lid].depth)
        
        logger.info(f"Created volumetric layer '{layer_id}' at depth {depth}")
        return layer
    
    async def remove_layer(self, layer_id: str) -> bool:
        """Remove a volumetric layer"""
        if layer_id not in self.layers:
            return False
        
        del self.layers[layer_id]
        self.layer_order.remove(layer_id)
        
        logger.info(f"Removed volumetric layer '{layer_id}'")
        return True
    
    async def add_voxel(self, layer_id: str, position: Vector3D, 
                       color: Tuple[float, float, float, float],
                       intensity: float = 1.0, size: float = 1.0) -> str:
        """Add a voxel to a layer"""
        if layer_id not in self.layers:
            raise ValueError(f"Layer {layer_id} does not exist")
        
        voxel = VoxelData(
            position=position,
            color=color,
            intensity=intensity,
            size=size
        )
        
        self.layers[layer_id].voxels.append(voxel)
        
        # Update volume renderer
        self.volume_renderer.add_voxel(position, color, intensity)
        
        voxel_id = f"{layer_id}_voxel_{len(self.layers[layer_id].voxels)}"
        return voxel_id
    
    async def remove_voxel(self, layer_id: str, voxel_index: int) -> bool:
        """Remove a voxel from a layer"""
        if layer_id not in self.layers:
            return False
        
        layer = self.layers[layer_id]
        if 0 <= voxel_index < len(layer.voxels):
            del layer.voxels[voxel_index]
            return True
        
        return False
    
    async def clear_layer(self, layer_id: str) -> bool:
        """Clear all voxels from a layer"""
        if layer_id not in self.layers:
            return False
        
        self.layers[layer_id].voxels.clear()
        return True
    
    def set_camera_position(self, position: Vector3D, target: Vector3D, up: Vector3D):
        """Set camera view parameters"""
        self.camera_position = position
        self.camera_target = target
        self.camera_up = up
        self._update_view_matrix()
    
    def _update_view_matrix(self):
        """Update view matrix"""
        from ..core.math_utils import SpatialMath
        self.view_matrix = SpatialMath.create_look_at_matrix(
            self.camera_position, self.camera_target, self.camera_up
        )
    
    def _update_projection_matrix(self):
        """Update projection matrix"""
        from ..core.math_utils import SpatialMath
        self.projection_matrix = SpatialMath.create_perspective_matrix(
            self.field_of_view, self.aspect_ratio, 0.1, 100.0
        )
    
    async def render(self) -> np.ndarray:
        """Render the current volumetric frame"""
        if not self.enabled or not self.initialized:
            return None
        
        self.performance_monitor.start_timer("volumetric_render")
        
        try:
            self.rendering = True
            
            # Update volume data from layers
            await self._update_volume_data()
            
            # Render volume
            frame = await asyncio.get_event_loop().run_in_executor(
                self.render_executor,
                self.volume_renderer.render_volume,
                self.view_matrix,
                self.projection_matrix,
                self.camera_position
            )
            
            self.current_frame = frame
            
            render_time = self.performance_monitor.end_timer("volumetric_render")
            logger.debug(f"Volumetric render completed in {render_time:.3f}s")
            
            return frame
            
        except Exception as e:
            logger.error(f"Error rendering volumetric display: {e}")
            raise RenderingError(f"Volumetric rendering failed: {e}")
        finally:
            self.rendering = False
    
    async def _update_volume_data(self):
        """Update volume renderer with current layer data"""
        # Clear existing volume data
        self.volume_renderer.clear_volume()
        
        # Add voxels from all enabled layers
        for layer_id in self.layer_order:
            layer = self.layers[layer_id]
            if not layer.enabled:
                continue
            
            for voxel in layer.voxels:
                if voxel.active:
                    # Apply layer opacity
                    color = list(voxel.color)
                    color[3] *= layer.opacity
                    
                    self.volume_renderer.add_voxel(
                        voxel.position, tuple(color), voxel.intensity
                    )
    
    async def animate_voxel(self, layer_id: str, voxel_index: int,
                           target_position: Vector3D, duration: float):
        """Animate voxel to target position"""
        if layer_id not in self.layers:
            return False
        
        layer = self.layers[layer_id]
        if voxel_index >= len(layer.voxels):
            return False
        
        voxel = layer.voxels[voxel_index]
        start_position = voxel.position
        start_time = time.time()
        
        while time.time() - start_time < duration:
            progress = (time.time() - start_time) / duration
            progress = min(1.0, progress)
            
            # Smooth interpolation
            smooth_progress = 3 * progress**2 - 2 * progress**3
            
            from ..core.math_utils import SpatialMath
            voxel.position = SpatialMath.lerp_vector(
                start_position, target_position, smooth_progress
            )
            
            await asyncio.sleep(0.016)  # ~60 FPS
        
        voxel.position = target_position
        return True
    
    def get_layer_info(self, layer_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a layer"""
        if layer_id not in self.layers:
            return None
        
        layer = self.layers[layer_id]
        return {
            "layer_id": layer.layer_id,
            "depth": layer.depth,
            "resolution": layer.resolution,
            "voxel_count": len(layer.voxels),
            "opacity": layer.opacity,
            "blend_mode": layer.blend_mode,
            "enabled": layer.enabled
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "render_time": self.performance_monitor.get_average_time("volumetric_render"),
            "fps": self.performance_monitor.get_fps("volumetric_render"),
            "resolution": self.resolution,
            "layer_count": len(self.layers),
            "total_voxels": sum(len(layer.voxels) for layer in self.layers.values()),
            "rendering": self.rendering,
            "gpu_enabled": self.volume_renderer.gpu_enabled
        }

class VolumetricDisplayManager(HolographicBase):
    """Manager for multiple volumetric displays"""
    
    def __init__(self, config: DisplayConfig):
        super().__init__("VolumetricDisplayManager")
        self.config = config
        self.displays: Dict[str, VolumetricDisplay] = {}
        self.active_display: Optional[str] = None
        
    async def initialize(self) -> bool:
        """Initialize the display manager"""
        try:
            logger.info("Initializing VolumetricDisplayManager...")
            
            # Create default display
            await self.create_display("primary")
            self.active_display = "primary"
            
            self.initialized = True
            logger.info("VolumetricDisplayManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize VolumetricDisplayManager: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the display manager"""
        logger.info("Shutting down VolumetricDisplayManager...")
        
        # Shutdown all displays
        for display in self.displays.values():
            await display.shutdown()
        
        self.displays.clear()
        self.active_display = None
        
        self.initialized = False
        logger.info("VolumetricDisplayManager shutdown complete")
    
    async def create_display(self, display_id: str) -> VolumetricDisplay:
        """Create a new volumetric display"""
        if display_id in self.displays:
            raise ValueError(f"Display {display_id} already exists")
        
        display = VolumetricDisplay(self.config)
        await display.initialize()
        
        self.displays[display_id] = display
        
        logger.info(f"Created volumetric display '{display_id}'")
        return display
    
    async def remove_display(self, display_id: str) -> bool:
        """Remove a volumetric display"""
        if display_id not in self.displays:
            return False
        
        await self.displays[display_id].shutdown()
        del self.displays[display_id]
        
        if self.active_display == display_id:
            self.active_display = None
        
        logger.info(f"Removed volumetric display '{display_id}'")
        return True
    
    def set_active_display(self, display_id: str) -> bool:
        """Set the active display"""
        if display_id not in self.displays:
            return False
        
        self.active_display = display_id
        return True
    
    def get_active_display(self) -> Optional[VolumetricDisplay]:
        """Get the active display"""
        if self.active_display and self.active_display in self.displays:
            return self.displays[self.active_display]
        return None
    
    async def render(self) -> Optional[np.ndarray]:
        """Render the active display"""
        display = self.get_active_display()
        if display:
            return await display.render()
        return None
    
    async def update(self, delta_time: float):
        """Update all displays"""
        for display in self.displays.values():
            if display.is_enabled():
                await display.update(delta_time)