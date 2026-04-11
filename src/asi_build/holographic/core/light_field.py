"""
Light field generation and processing for holographic displays
"""

import asyncio
import logging
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from .base import (
    HolographicBase,
    HolographicPerformanceMonitor,
    RenderingError,
    Transform3D,
    Vector3D,
)
from .math_utils import SpatialMath

logger = logging.getLogger(__name__)


@dataclass
class LightRay:
    """Represents a light ray in 4D light field space"""

    origin: Vector3D
    direction: Vector3D
    color: Tuple[float, float, float]  # RGB
    intensity: float
    wavelength: float = 550.0  # nm
    polarization: Optional[Vector3D] = None
    phase: float = 0.0

    def to_plenoptic_coords(self, focal_length: float) -> Tuple[float, float, float, float]:
        """Convert to plenoptic coordinates (u, v, s, t)"""
        # Project ray to focal plane
        if self.direction.z != 0:
            t_focal = -focal_length / self.direction.z
            focal_x = self.origin.x + t_focal * self.direction.x
            focal_y = self.origin.y + t_focal * self.direction.y
        else:
            focal_x = self.origin.x
            focal_y = self.origin.y

        # Plenoptic coordinates
        u = self.origin.x  # Position on sensor plane
        v = self.origin.y
        s = focal_x  # Position on focal plane
        t = focal_y

        return u, v, s, t


@dataclass
class LightFieldCamera:
    """Virtual camera for light field capture"""

    position: Vector3D
    direction: Vector3D
    up: Vector3D
    field_of_view: float
    resolution: Tuple[int, int]
    focal_length: float
    aperture_size: float

    def get_view_matrix(self) -> np.ndarray:
        """Get camera view matrix"""
        return SpatialMath.create_look_at_matrix(
            self.position, self.position + self.direction, self.up
        )

    def get_projection_matrix(self) -> np.ndarray:
        """Get camera projection matrix"""
        aspect = self.resolution[0] / self.resolution[1]
        return SpatialMath.create_perspective_matrix(self.field_of_view, aspect, 0.1, 1000.0)


class LightFieldProcessor(HolographicBase):
    """
    Advanced light field processing system for holographic rendering
    Supports plenoptic cameras, light field synthesis, and view interpolation
    """

    def __init__(self, resolution: Tuple[int, int, int, int]):
        super().__init__("LightFieldProcessor")
        self.performance_monitor = HolographicPerformanceMonitor()

        # Light field dimensions (u, v, s, t)
        self.u_res, self.v_res, self.s_res, self.t_res = resolution
        self.resolution = resolution

        # Light field data
        self.light_field = np.zeros(resolution + (3,), dtype=np.float32)  # RGB
        self.depth_field = np.zeros(resolution, dtype=np.float32)
        self.confidence_field = np.zeros(resolution, dtype=np.float32)

        # Camera array for light field capture
        self.camera_array: List[LightFieldCamera] = []
        self.camera_grid_size = (8, 8)  # Default 8x8 camera array

        # Processing parameters
        self.focal_length = 50.0  # mm
        self.baseline = 10.0  # mm between cameras
        self.disparity_range = (0.1, 100.0)

        # GPU acceleration
        self.gpu_enabled = False
        self.gpu_context = None

        # Threading
        self.processing_executor = ThreadPoolExecutor(max_workers=8)

        logger.info(f"LightFieldProcessor initialized with resolution {resolution}")

    async def initialize(self) -> bool:
        """Initialize the light field processor"""
        try:
            logger.info("Initializing LightFieldProcessor...")

            # Initialize camera array
            await self._setup_camera_array()

            # Initialize GPU resources
            self._init_gpu_resources()

            self.initialized = True
            logger.info("LightFieldProcessor initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize LightFieldProcessor: {e}")
            return False

    async def shutdown(self):
        """Shutdown the light field processor"""
        logger.info("Shutting down LightFieldProcessor...")

        # Clear light field data
        self.light_field.fill(0)
        self.depth_field.fill(0)
        self.confidence_field.fill(0)

        # Clear camera array
        self.camera_array.clear()

        # Shutdown executor
        self.processing_executor.shutdown(wait=True)

        self.initialized = False
        logger.info("LightFieldProcessor shutdown complete")

    def _init_gpu_resources(self):
        """Initialize GPU resources for acceleration"""
        try:
            # Placeholder for GPU initialization
            # Would use CUDA, OpenCL, or compute shaders
            self.gpu_enabled = False
            logger.info("GPU acceleration not available, using CPU processing")
        except Exception as e:
            logger.warning(f"Failed to initialize GPU resources: {e}")
            self.gpu_enabled = False

    async def _setup_camera_array(self):
        """Setup virtual camera array for light field capture"""
        self.camera_array.clear()

        grid_width, grid_height = self.camera_grid_size

        for i in range(grid_height):
            for j in range(grid_width):
                # Calculate camera position
                x_offset = (j - grid_width / 2.0) * self.baseline / 1000.0  # Convert to meters
                y_offset = (i - grid_height / 2.0) * self.baseline / 1000.0

                camera = LightFieldCamera(
                    position=Vector3D(x_offset, y_offset, 0),
                    direction=Vector3D(0, 0, -1),
                    up=Vector3D(0, 1, 0),
                    field_of_view=math.radians(60),
                    resolution=(self.s_res, self.t_res),
                    focal_length=self.focal_length / 1000.0,  # Convert to meters
                    aperture_size=2.8,
                )

                self.camera_array.append(camera)

        logger.info(f"Setup {len(self.camera_array)} cameras in {grid_width}x{grid_height} array")

    async def capture_light_field(self, scene_data: Any) -> bool:
        """Capture light field from scene"""
        self.performance_monitor.start_timer("light_field_capture")

        try:
            # Clear existing data
            self.light_field.fill(0)
            self.depth_field.fill(0)
            self.confidence_field.fill(1.0)

            # Capture from each camera
            capture_tasks = []
            for i, camera in enumerate(self.camera_array):
                task = self._capture_camera_view(camera, scene_data, i)
                capture_tasks.append(task)

            # Process captures in parallel
            results = await asyncio.gather(*capture_tasks, return_exceptions=True)

            # Integrate results into light field
            await self._integrate_captures(results)

            capture_time = self.performance_monitor.end_timer("light_field_capture")
            logger.info(f"Light field capture completed in {capture_time:.3f}s")

            return True

        except Exception as e:
            logger.error(f"Error capturing light field: {e}")
            return False

    async def _capture_camera_view(
        self, camera: LightFieldCamera, scene_data: Any, camera_index: int
    ) -> Dict[str, Any]:
        """Capture view from a single camera"""
        # Calculate camera position in grid
        grid_width = self.camera_grid_size[0]
        u_index = camera_index % grid_width
        v_index = camera_index // grid_width

        # Render camera view (placeholder - would integrate with actual renderer)
        image = await self._render_camera_view(camera, scene_data)
        depth = await self._render_depth_view(camera, scene_data)

        return {
            "u_index": u_index,
            "v_index": v_index,
            "image": image,
            "depth": depth,
            "camera": camera,
        }

    async def _render_camera_view(self, camera: LightFieldCamera, scene_data: Any) -> np.ndarray:
        """Render RGB image from camera viewpoint"""
        # Placeholder implementation
        # In practice, this would render the scene from camera's perspective

        def render_task():
            # Simulate rendering
            image = np.random.random((self.t_res, self.s_res, 3)).astype(np.float32)

            # Add some structure for testing
            center_x, center_y = self.s_res // 2, self.t_res // 2
            y, x = np.ogrid[: self.t_res, : self.s_res]
            dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
            image[dist < 50] = [1.0, 0.5, 0.2]  # Orange center

            return image

        return await asyncio.get_event_loop().run_in_executor(self.processing_executor, render_task)

    async def _render_depth_view(self, camera: LightFieldCamera, scene_data: Any) -> np.ndarray:
        """Render depth map from camera viewpoint"""

        # Placeholder implementation
        def depth_task():
            # Simulate depth rendering
            center_x, center_y = self.s_res // 2, self.t_res // 2
            y, x = np.ogrid[: self.t_res, : self.s_res]
            dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
            depth = 1.0 + dist / 100.0  # Depth increases with distance from center
            return depth.astype(np.float32)

        return await asyncio.get_event_loop().run_in_executor(self.processing_executor, depth_task)

    async def _integrate_captures(self, capture_results: List[Dict[str, Any]]):
        """Integrate camera captures into light field"""
        for result in capture_results:
            if isinstance(result, Exception):
                logger.error(f"Camera capture failed: {result}")
                continue

            u_idx = result["u_index"]
            v_idx = result["v_index"]
            image = result["image"]
            depth = result["depth"]

            # Store in light field
            self.light_field[u_idx, v_idx, :, :, :] = image
            self.depth_field[u_idx, v_idx, :, :] = depth

    async def synthesize_view(
        self,
        camera_position: Vector3D,
        camera_direction: Vector3D,
        camera_up: Vector3D,
        output_resolution: Tuple[int, int],
    ) -> np.ndarray:
        """Synthesize novel view from light field"""
        self.performance_monitor.start_timer("view_synthesis")

        try:
            output_width, output_height = output_resolution
            synthesized_view = np.zeros((output_height, output_width, 3), dtype=np.float32)

            # Create virtual camera
            virtual_camera = LightFieldCamera(
                position=camera_position,
                direction=camera_direction,
                up=camera_up,
                field_of_view=math.radians(60),
                resolution=output_resolution,
                focal_length=self.focal_length / 1000.0,
                aperture_size=2.8,
            )

            # Synthesize each pixel
            synthesis_tasks = []
            batch_size = output_height // 8  # Process in batches

            for i in range(0, output_height, batch_size):
                end_row = min(i + batch_size, output_height)
                task = self._synthesize_pixel_batch(
                    virtual_camera, synthesized_view, i, end_row, output_width
                )
                synthesis_tasks.append(task)

            # Process batches in parallel
            await asyncio.gather(*synthesis_tasks)

            synthesis_time = self.performance_monitor.end_timer("view_synthesis")
            logger.debug(f"View synthesis completed in {synthesis_time:.3f}s")

            return synthesized_view

        except Exception as e:
            logger.error(f"Error synthesizing view: {e}")
            raise RenderingError(f"View synthesis failed: {e}")

    async def _synthesize_pixel_batch(
        self,
        virtual_camera: LightFieldCamera,
        output_image: np.ndarray,
        start_row: int,
        end_row: int,
        width: int,
    ):
        """Synthesize a batch of pixels"""

        def synthesis_task():
            for y in range(start_row, end_row):
                for x in range(width):
                    # Convert pixel to world ray
                    ray_origin, ray_direction = self._pixel_to_ray(x, y, virtual_camera)

                    # Sample light field along ray
                    color = self._sample_light_field_ray(ray_origin, ray_direction)
                    output_image[y, x] = color

        await asyncio.get_event_loop().run_in_executor(self.processing_executor, synthesis_task)

    def _pixel_to_ray(
        self, pixel_x: int, pixel_y: int, camera: LightFieldCamera
    ) -> Tuple[Vector3D, Vector3D]:
        """Convert pixel coordinates to world ray"""
        # Normalize pixel coordinates
        ndc_x = (2.0 * pixel_x / camera.resolution[0]) - 1.0
        ndc_y = 1.0 - (2.0 * pixel_y / camera.resolution[1])

        # Convert to camera space
        view_matrix = camera.get_view_matrix()
        proj_matrix = camera.get_projection_matrix()

        # Create ray
        near_point = np.array([ndc_x, ndc_y, -1.0, 1.0])
        far_point = np.array([ndc_x, ndc_y, 1.0, 1.0])

        # Transform to world space
        inv_vp = np.linalg.inv(proj_matrix @ view_matrix)
        world_near = inv_vp @ near_point
        world_far = inv_vp @ far_point

        # Perspective divide
        world_near /= world_near[3]
        world_far /= world_far[3]

        ray_origin = Vector3D(world_near[0], world_near[1], world_near[2])
        ray_end = Vector3D(world_far[0], world_far[1], world_far[2])
        ray_direction = (ray_end - ray_origin).normalize()

        return ray_origin, ray_direction

    def _sample_light_field_ray(self, ray_origin: Vector3D, ray_direction: Vector3D) -> np.ndarray:
        """Sample light field along a ray"""
        # Find best matching cameras and interpolate
        camera_weights = self._compute_camera_weights(ray_origin, ray_direction)

        color = np.array([0.0, 0.0, 0.0])
        total_weight = 0.0

        for i, (weight, u_idx, v_idx) in enumerate(camera_weights):
            if weight > 0.01:  # Threshold for contribution
                # Project ray to camera's image plane
                s_idx, t_idx = self._project_ray_to_camera(ray_origin, ray_direction, u_idx, v_idx)

                if 0 <= s_idx < self.s_res and 0 <= t_idx < self.t_res:
                    # Bilinear interpolation
                    sampled_color = self._bilinear_sample(u_idx, v_idx, s_idx, t_idx)
                    color += weight * sampled_color
                    total_weight += weight

        if total_weight > 0:
            color /= total_weight

        return np.clip(color, 0.0, 1.0)

    def _compute_camera_weights(
        self, ray_origin: Vector3D, ray_direction: Vector3D
    ) -> List[Tuple[float, int, int]]:
        """Compute weights for cameras based on ray"""
        weights = []

        grid_width, grid_height = self.camera_grid_size

        for v_idx in range(grid_height):
            for u_idx in range(grid_width):
                camera = self.camera_array[v_idx * grid_width + u_idx]

                # Compute weight based on camera position and ray
                camera_to_ray = ray_origin - camera.position
                distance = camera_to_ray.magnitude()

                # Angular weight based on ray direction and camera direction
                angle_weight = max(0.0, SpatialMath.dot_product(ray_direction, camera.direction))

                # Distance weight (closer cameras have more influence)
                distance_weight = 1.0 / (1.0 + distance)

                total_weight = angle_weight * distance_weight
                weights.append((total_weight, u_idx, v_idx))

        # Sort by weight and return top contributors
        weights.sort(key=lambda x: x[0], reverse=True)
        return weights[:4]  # Use top 4 cameras

    def _project_ray_to_camera(
        self, ray_origin: Vector3D, ray_direction: Vector3D, u_idx: int, v_idx: int
    ) -> Tuple[float, float]:
        """Project ray to camera's image plane"""
        camera = self.camera_array[v_idx * self.camera_grid_size[0] + u_idx]

        # Transform ray to camera space
        view_matrix = camera.get_view_matrix()

        # Ray in camera space
        ray_origin_homo = np.array([ray_origin.x, ray_origin.y, ray_origin.z, 1.0])
        ray_end_homo = np.array(
            [
                ray_origin.x + ray_direction.x,
                ray_origin.y + ray_direction.y,
                ray_origin.z + ray_direction.z,
                1.0,
            ]
        )

        cam_ray_origin = view_matrix @ ray_origin_homo
        cam_ray_end = view_matrix @ ray_end_homo

        # Project to image plane (z = -focal_length)
        if cam_ray_end[2] != cam_ray_origin[2]:
            t = (-camera.focal_length - cam_ray_origin[2]) / (cam_ray_end[2] - cam_ray_origin[2])
            image_x = cam_ray_origin[0] + t * (cam_ray_end[0] - cam_ray_origin[0])
            image_y = cam_ray_origin[1] + t * (cam_ray_end[1] - cam_ray_origin[1])

            # Convert to pixel coordinates
            s_idx = (image_x / camera.focal_length + 0.5) * self.s_res
            t_idx = (image_y / camera.focal_length + 0.5) * self.t_res

            return s_idx, t_idx

        return -1, -1  # Invalid projection

    def _bilinear_sample(self, u_idx: int, v_idx: int, s: float, t: float) -> np.ndarray:
        """Bilinear sampling from light field"""
        s0, t0 = int(s), int(t)
        s1, t1 = min(s0 + 1, self.s_res - 1), min(t0 + 1, self.t_res - 1)

        # Interpolation weights
        ws = s - s0
        wt = t - t0

        # Sample four corners
        c00 = self.light_field[u_idx, v_idx, s0, t0]
        c01 = self.light_field[u_idx, v_idx, s0, t1]
        c10 = self.light_field[u_idx, v_idx, s1, t0]
        c11 = self.light_field[u_idx, v_idx, s1, t1]

        # Bilinear interpolation
        c0 = c00 * (1 - ws) + c10 * ws
        c1 = c01 * (1 - ws) + c11 * ws

        return c0 * (1 - wt) + c1 * wt

    async def refocus_image(
        self, focus_depth: float, aperture_size: float, output_resolution: Tuple[int, int]
    ) -> np.ndarray:
        """Generate refocused image from light field"""
        self.performance_monitor.start_timer("refocus")

        try:
            output_width, output_height = output_resolution
            refocused_image = np.zeros((output_height, output_width, 3), dtype=np.float32)

            # Process in batches for better performance
            batch_size = output_height // 8
            refocus_tasks = []

            for i in range(0, output_height, batch_size):
                end_row = min(i + batch_size, output_height)
                task = self._refocus_pixel_batch(
                    refocused_image, i, end_row, output_width, focus_depth, aperture_size
                )
                refocus_tasks.append(task)

            await asyncio.gather(*refocus_tasks)

            refocus_time = self.performance_monitor.end_timer("refocus")
            logger.debug(f"Refocus completed in {refocus_time:.3f}s")

            return refocused_image

        except Exception as e:
            logger.error(f"Error refocusing image: {e}")
            raise RenderingError(f"Refocus failed: {e}")

    async def _refocus_pixel_batch(
        self,
        output_image: np.ndarray,
        start_row: int,
        end_row: int,
        width: int,
        focus_depth: float,
        aperture_size: float,
    ):
        """Refocus a batch of pixels"""

        def refocus_task():
            grid_width, grid_height = self.camera_grid_size

            for y in range(start_row, end_row):
                for x in range(width):
                    # Normalize pixel coordinates
                    s_coord = x / width
                    t_coord = y / output_image.shape[0]

                    color = np.array([0.0, 0.0, 0.0])
                    weight_sum = 0.0

                    # Integrate over aperture
                    for v_idx in range(grid_height):
                        for u_idx in range(grid_width):
                            # Calculate shift based on focus depth
                            u_shift = (u_idx - grid_width / 2.0) / focus_depth
                            v_shift = (v_idx - grid_height / 2.0) / focus_depth

                            # Apply aperture mask
                            aperture_dist = math.sqrt(u_shift**2 + v_shift**2)
                            if aperture_dist > aperture_size:
                                continue

                            # Sample shifted position
                            s_sample = s_coord + u_shift / self.s_res
                            t_sample = t_coord + v_shift / self.t_res

                            # Bounds check
                            if 0 <= s_sample < 1 and 0 <= t_sample < 1:
                                s_idx = s_sample * (self.s_res - 1)
                                t_idx = t_sample * (self.t_res - 1)

                                sample_color = self._bilinear_sample(u_idx, v_idx, s_idx, t_idx)

                                # Aperture weight (gaussian)
                                weight = math.exp(-(aperture_dist**2) / (2 * aperture_size**2))

                                color += weight * sample_color
                                weight_sum += weight

                    if weight_sum > 0:
                        color /= weight_sum

                    output_image[y, x] = np.clip(color, 0.0, 1.0)

        await asyncio.get_event_loop().run_in_executor(self.processing_executor, refocus_task)

    def estimate_depth_map(self, output_resolution: Tuple[int, int]) -> np.ndarray:
        """Estimate depth map from light field using disparity"""
        output_width, output_height = output_resolution
        depth_map = np.zeros((output_height, output_width), dtype=np.float32)

        # Use stereo matching between central cameras
        center_u = self.u_res // 2
        center_v = self.v_res // 2

        # Reference and target cameras
        ref_u, ref_v = center_u, center_v
        target_u, target_v = center_u + 1, center_v

        if target_u < self.u_res:
            ref_image = self.light_field[ref_u, ref_v]
            target_image = self.light_field[target_u, target_v]

            # Simple block matching for disparity
            block_size = 5
            max_disparity = 32

            for y in range(block_size, output_height - block_size):
                for x in range(block_size, output_width - block_size):
                    best_disparity = 0
                    best_cost = float("inf")

                    # Extract reference block
                    ref_block = ref_image[
                        y - block_size : y + block_size + 1, x - block_size : x + block_size + 1
                    ]

                    # Search for best match
                    for d in range(max_disparity):
                        if x - d - block_size >= 0:
                            target_block = target_image[
                                y - block_size : y + block_size + 1,
                                x - d - block_size : x - d + block_size + 1,
                            ]

                            # Sum of squared differences
                            cost = np.sum((ref_block - target_block) ** 2)

                            if cost < best_cost:
                                best_cost = cost
                                best_disparity = d

                    # Convert disparity to depth
                    if best_disparity > 0:
                        depth = self.baseline / (best_disparity * 0.001)  # Approximate depth
                    else:
                        depth = 100.0  # Far depth

                    depth_map[y, x] = depth

        return depth_map

    def get_light_field_slice(self, u_idx: int, v_idx: int) -> np.ndarray:
        """Get a 2D slice of the light field"""
        if 0 <= u_idx < self.u_res and 0 <= v_idx < self.v_res:
            return self.light_field[u_idx, v_idx]
        return None

    def set_light_field_slice(self, u_idx: int, v_idx: int, image: np.ndarray):
        """Set a 2D slice of the light field"""
        if (
            0 <= u_idx < self.u_res
            and 0 <= v_idx < self.v_res
            and image.shape[:2] == (self.t_res, self.s_res)
        ):
            self.light_field[u_idx, v_idx] = image

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "capture_time": self.performance_monitor.get_average_time("light_field_capture"),
            "synthesis_time": self.performance_monitor.get_average_time("view_synthesis"),
            "refocus_time": self.performance_monitor.get_average_time("refocus"),
            "resolution": self.resolution,
            "camera_count": len(self.camera_array),
            "gpu_enabled": self.gpu_enabled,
            "memory_usage_mb": self.light_field.nbytes / (1024 * 1024),
        }
