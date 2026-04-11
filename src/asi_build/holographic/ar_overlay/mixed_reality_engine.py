"""
Mixed Reality Engine for seamless AR/VR holographic experiences
"""

import asyncio
import logging
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from ..core.base import (
    HolographicBase,
    HolographicPerformanceMonitor,
    RenderingError,
    Transform3D,
    Vector3D,
)
from ..core.math_utils import SpatialMath

logger = logging.getLogger(__name__)


class RealityMode(Enum):
    """Mixed reality modes"""

    PURE_VR = "pure_vr"
    AR_OVERLAY = "ar_overlay"
    MIXED_REALITY = "mixed_reality"
    PASSTHROUGH = "passthrough"
    HYBRID = "hybrid"


class TrackingMethod(Enum):
    """Object tracking methods"""

    MARKER_BASED = "marker_based"
    MARKERLESS = "markerless"
    SLAM = "slam"
    INSIDE_OUT = "inside_out"
    OUTSIDE_IN = "outside_in"


@dataclass
class RealWorldObject:
    """Real world object representation"""

    object_id: str
    object_type: str
    position: Vector3D
    orientation: Transform3D
    bounding_box: Tuple[Vector3D, Vector3D]  # min, max
    confidence: float
    last_detected: float
    tracking_method: TrackingMethod
    features: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.last_detected == 0:
            self.last_detected = time.time()


@dataclass
class VirtualObject:
    """Virtual object for AR overlay"""

    object_id: str
    object_type: str
    position: Vector3D
    orientation: Transform3D
    scale: Vector3D
    visibility: float  # 0-1
    occlusion_enabled: bool
    shadow_casting: bool
    material_properties: Dict[str, Any]
    animation_state: Dict[str, Any] = field(default_factory=dict)

    def is_visible(self) -> bool:
        """Check if object is visible"""
        return self.visibility > 0.01


@dataclass
class SpatialAnchor:
    """Spatial anchor for persistent AR placement"""

    anchor_id: str
    world_position: Vector3D
    world_orientation: Transform3D
    confidence: float
    creation_time: float
    last_updated: float
    persistence_data: bytes
    tracking_quality: float = 1.0

    def __post_init__(self):
        if self.creation_time == 0:
            self.creation_time = time.time()
        if self.last_updated == 0:
            self.last_updated = time.time()


class SLAM:
    """Simultaneous Localization and Mapping system"""

    def __init__(self):
        self.map_points: List[Vector3D] = []
        self.keyframes: List[Dict[str, Any]] = []
        self.camera_poses: List[Transform3D] = []
        self.feature_extractor = None
        self.bundle_adjuster = None
        self.loop_closure_detector = None

        # ORB feature extractor for visual SLAM
        self.orb = cv2.ORB_create(nfeatures=1000)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        # Camera parameters
        self.camera_matrix = np.eye(3)
        self.distortion_coeffs = np.zeros(5)

        self.initialized = False

    def initialize(self, camera_matrix: np.ndarray, distortion_coeffs: np.ndarray):
        """Initialize SLAM system"""
        self.camera_matrix = camera_matrix
        self.distortion_coeffs = distortion_coeffs
        self.initialized = True

    def process_frame(self, frame: np.ndarray, timestamp: float) -> Optional[Transform3D]:
        """Process camera frame and return camera pose"""
        if not self.initialized:
            return None

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Extract features
            keypoints, descriptors = self.orb.detectAndCompute(gray, None)

            if descriptors is None or len(keypoints) < 10:
                return None

            # Track features and estimate pose
            current_pose = self._estimate_pose(keypoints, descriptors, timestamp)

            # Update map
            self._update_map(keypoints, descriptors, current_pose, timestamp)

            return current_pose

        except Exception as e:
            logger.error(f"Error in SLAM processing: {e}")
            return None

    def _estimate_pose(self, keypoints, descriptors, timestamp: float) -> Optional[Transform3D]:
        """Estimate camera pose from features"""
        if not self.keyframes:
            # First frame - initialize
            self._initialize_map(keypoints, descriptors, timestamp)
            return Transform3D()

        # Match with previous keyframe
        last_keyframe = self.keyframes[-1]
        last_descriptors = last_keyframe["descriptors"]

        matches = self.matcher.match(descriptors, last_descriptors)

        if len(matches) < 20:
            return None

        # Extract matched points
        current_points = np.float32([keypoints[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        previous_points = np.float32(
            [last_keyframe["keypoints"][m.trainIdx].pt for m in matches]
        ).reshape(-1, 1, 2)

        # Estimate essential matrix
        essential_matrix, mask = cv2.findEssentialMat(
            current_points,
            previous_points,
            self.camera_matrix,
            method=cv2.RANSAC,
            prob=0.999,
            threshold=1.0,
        )

        if essential_matrix is None:
            return None

        # Recover pose
        _, R, t, mask = cv2.recoverPose(
            essential_matrix, current_points, previous_points, self.camera_matrix
        )

        # Convert to Transform3D
        position = Vector3D(-t[0, 0], -t[1, 0], -t[2, 0])

        # Convert rotation matrix to quaternion
        from scipy.spatial.transform import Rotation

        rotation_scipy = Rotation.from_matrix(R.T)
        quat = rotation_scipy.as_quat()  # [x, y, z, w]

        from ..core.base import Quaternion

        rotation = Quaternion(quat[3], quat[0], quat[1], quat[2])  # w, x, y, z

        return Transform3D(position, rotation, Vector3D(1, 1, 1))

    def _initialize_map(self, keypoints, descriptors, timestamp: float):
        """Initialize the map with first keyframe"""
        keyframe = {
            "keypoints": keypoints,
            "descriptors": descriptors,
            "timestamp": timestamp,
            "pose": Transform3D(),
        }

        self.keyframes.append(keyframe)
        self.camera_poses.append(Transform3D())

    def _update_map(self, keypoints, descriptors, pose: Transform3D, timestamp: float):
        """Update SLAM map with new observations"""
        # Add new keyframe if significant motion
        if self._should_add_keyframe(pose):
            keyframe = {
                "keypoints": keypoints,
                "descriptors": descriptors,
                "timestamp": timestamp,
                "pose": pose,
            }

            self.keyframes.append(keyframe)
            self.camera_poses.append(pose)

            # Triangulate new map points
            self._triangulate_new_points(keyframe)

            # Limit keyframes
            max_keyframes = 50
            if len(self.keyframes) > max_keyframes:
                self.keyframes = self.keyframes[-max_keyframes:]
                self.camera_poses = self.camera_poses[-max_keyframes:]

    def _should_add_keyframe(self, current_pose: Transform3D) -> bool:
        """Determine if a new keyframe should be added"""
        if not self.camera_poses:
            return True

        last_pose = self.camera_poses[-1]

        # Translation threshold
        translation_distance = SpatialMath.distance_3d(current_pose.position, last_pose.position)

        # Rotation threshold
        rotation_angle = math.acos(
            abs(
                SpatialMath.dot_product(
                    Vector3D(1, 0, 0), Vector3D(1, 0, 0)  # Simplified rotation check
                )
            )
        )

        return translation_distance > 0.1 or rotation_angle > 0.1

    def _triangulate_new_points(self, keyframe: Dict[str, Any]):
        """Triangulate new 3D map points"""
        # Simplified triangulation
        # In practice, this would triangulate matched features between keyframes
        pass

    def get_map_points(self) -> List[Vector3D]:
        """Get current map points"""
        return self.map_points.copy()

    def get_camera_trajectory(self) -> List[Transform3D]:
        """Get camera trajectory"""
        return self.camera_poses.copy()


class MixedRealityEngine(HolographicBase):
    """
    Advanced Mixed Reality Engine for seamless AR/VR experiences
    Handles real-world tracking, virtual object rendering, and occlusion
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__("MixedRealityEngine")
        self.config = config
        self.performance_monitor = HolographicPerformanceMonitor()

        # Reality mode
        self.reality_mode = RealityMode.MIXED_REALITY
        self.transition_active = False

        # Camera system
        self.camera_feed = None
        self.camera_calibrated = False
        self.camera_matrix = np.eye(3)
        self.distortion_coeffs = np.zeros(5)

        # Tracking systems
        self.slam_system = SLAM()
        self.object_tracker = None
        self.tracking_active = False

        # World understanding
        self.real_world_objects: Dict[str, RealWorldObject] = {}
        self.virtual_objects: Dict[str, VirtualObject] = {}
        self.spatial_anchors: Dict[str, SpatialAnchor] = {}

        # Rendering
        self.virtual_renderer = None
        self.occlusion_renderer = None
        self.lighting_estimator = None

        # Camera pose
        self.current_camera_pose = Transform3D()
        self.pose_history: List[Transform3D] = []
        self.max_pose_history = 100

        # Processing
        self.processing_executor = ThreadPoolExecutor(max_workers=6)

        # Performance settings
        self.target_fps = config.get("target_fps", 60)
        self.quality_level = config.get("quality_level", "high")

        logger.info("MixedRealityEngine initialized")

    async def initialize(self) -> bool:
        """Initialize the mixed reality engine"""
        try:
            logger.info("Initializing MixedRealityEngine...")

            # Initialize camera
            await self._initialize_camera()

            # Initialize tracking systems
            await self._initialize_tracking()

            # Initialize rendering systems
            await self._initialize_rendering()

            # Initialize SLAM
            self.slam_system.initialize(self.camera_matrix, self.distortion_coeffs)

            self.initialized = True
            logger.info("MixedRealityEngine initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize MixedRealityEngine: {e}")
            return False

    async def shutdown(self):
        """Shutdown the mixed reality engine"""
        logger.info("Shutting down MixedRealityEngine...")

        # Stop tracking
        self.tracking_active = False

        # Clear data
        self.real_world_objects.clear()
        self.virtual_objects.clear()
        self.spatial_anchors.clear()
        self.pose_history.clear()

        # Close camera
        if self.camera_feed:
            self.camera_feed.release()

        # Shutdown executor
        self.processing_executor.shutdown(wait=True)

        self.initialized = False
        logger.info("MixedRealityEngine shutdown complete")

    async def _initialize_camera(self):
        """Initialize camera system"""
        try:
            # Initialize camera feed
            self.camera_feed = cv2.VideoCapture(0)

            if not self.camera_feed.isOpened():
                raise RuntimeError("Failed to open camera")

            # Set camera properties
            self.camera_feed.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camera_feed.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.camera_feed.set(cv2.CAP_PROP_FPS, self.target_fps)

            # Load camera calibration or use defaults
            await self._load_camera_calibration()

            logger.info("Camera system initialized")

        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            # Use mock camera for testing
            self.camera_feed = MockCamera()
            await self._load_camera_calibration()

    async def _load_camera_calibration(self):
        """Load camera calibration data"""
        try:
            # In practice, load from calibration file
            # For now, use default values
            self.camera_matrix = np.array(
                [[800, 0, 640], [0, 800, 360], [0, 0, 1]], dtype=np.float32
            )

            self.distortion_coeffs = np.zeros(5, dtype=np.float32)
            self.camera_calibrated = True

            logger.info("Camera calibration loaded")

        except Exception as e:
            logger.error(f"Failed to load camera calibration: {e}")
            self.camera_calibrated = False

    async def _initialize_tracking(self):
        """Initialize object tracking systems"""
        try:
            # Initialize object tracker
            from .object_tracker import ObjectTracker

            self.object_tracker = ObjectTracker(self.config)
            await self.object_tracker.initialize()

            logger.info("Tracking systems initialized")

        except Exception as e:
            logger.error(f"Failed to initialize tracking: {e}")
            # Continue without tracking
            self.object_tracker = None

    async def _initialize_rendering(self):
        """Initialize rendering systems"""
        try:
            # Initialize virtual renderer
            self.virtual_renderer = VirtualObjectRenderer(self.config)

            # Initialize occlusion renderer
            self.occlusion_renderer = OcclusionRenderer(self.config)

            # Initialize lighting estimator
            self.lighting_estimator = LightingEstimator(self.config)

            logger.info("Rendering systems initialized")

        except Exception as e:
            logger.error(f"Failed to initialize rendering: {e}")
            raise

    async def start_tracking(self):
        """Start mixed reality tracking"""
        if not self.initialized or self.tracking_active:
            return

        logger.info("Starting MR tracking...")
        self.tracking_active = True

        # Start tracking loop
        asyncio.create_task(self._tracking_loop())

    async def stop_tracking(self):
        """Stop mixed reality tracking"""
        logger.info("Stopping MR tracking...")
        self.tracking_active = False

    async def _tracking_loop(self):
        """Main tracking and rendering loop"""
        logger.info("MR tracking loop started")

        frame_interval = 1.0 / self.target_fps

        try:
            while self.tracking_active:
                loop_start = time.time()
                self.performance_monitor.start_timer("mr_frame")

                # Capture camera frame
                frame = await self._capture_camera_frame()

                if frame is not None:
                    # Process frame
                    await self._process_frame(frame, loop_start)

                frame_time = self.performance_monitor.end_timer("mr_frame")

                # Maintain frame rate
                elapsed = time.time() - loop_start
                if elapsed < frame_interval:
                    await asyncio.sleep(frame_interval - elapsed)

        except Exception as e:
            logger.error(f"Error in MR tracking loop: {e}")
        finally:
            logger.info("MR tracking loop ended")

    async def _capture_camera_frame(self) -> Optional[np.ndarray]:
        """Capture frame from camera"""
        try:
            if self.camera_feed:
                ret, frame = self.camera_feed.read()
                if ret:
                    return frame
        except Exception as e:
            logger.error(f"Error capturing camera frame: {e}")

        return None

    async def _process_frame(self, frame: np.ndarray, timestamp: float):
        """Process camera frame for tracking and rendering"""
        try:
            # SLAM tracking
            pose_task = asyncio.get_event_loop().run_in_executor(
                self.processing_executor, self.slam_system.process_frame, frame.copy(), timestamp
            )

            # Object detection
            objects_task = asyncio.get_event_loop().run_in_executor(
                self.processing_executor, self._detect_objects, frame.copy()
            )

            # Lighting estimation
            lighting_task = asyncio.get_event_loop().run_in_executor(
                self.processing_executor, self._estimate_lighting, frame.copy()
            )

            # Wait for all tasks
            camera_pose, detected_objects, lighting_info = await asyncio.gather(
                pose_task, objects_task, lighting_task, return_exceptions=True
            )

            # Update camera pose
            if camera_pose and not isinstance(camera_pose, Exception):
                self.current_camera_pose = camera_pose
                self._update_pose_history(camera_pose)

            # Update real world objects
            if detected_objects and not isinstance(detected_objects, Exception):
                await self._update_real_world_objects(detected_objects)

            # Update lighting
            if lighting_info and not isinstance(lighting_info, Exception):
                await self._update_lighting(lighting_info)

            # Render mixed reality frame
            await self._render_mixed_reality(frame)

        except Exception as e:
            logger.error(f"Error processing MR frame: {e}")

    def _detect_objects(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect real world objects in frame"""
        try:
            if self.object_tracker:
                return self.object_tracker.detect_objects(frame)
        except Exception as e:
            logger.error(f"Error detecting objects: {e}")

        return []

    def _estimate_lighting(self, frame: np.ndarray) -> Dict[str, Any]:
        """Estimate lighting conditions from frame"""
        try:
            if self.lighting_estimator:
                return self.lighting_estimator.estimate(frame)
        except Exception as e:
            logger.error(f"Error estimating lighting: {e}")

        return {"ambient": 0.5, "directional": Vector3D(0, 1, 0)}

    def _update_pose_history(self, pose: Transform3D):
        """Update camera pose history"""
        self.pose_history.append(pose)

        if len(self.pose_history) > self.max_pose_history:
            self.pose_history = self.pose_history[-self.max_pose_history :]

    async def _update_real_world_objects(self, detections: List[Dict[str, Any]]):
        """Update real world object tracking"""
        current_time = time.time()

        # Update existing objects or create new ones
        for detection in detections:
            object_id = detection.get("object_id", f"obj_{len(self.real_world_objects)}")

            if object_id in self.real_world_objects:
                # Update existing object
                obj = self.real_world_objects[object_id]
                obj.position = Vector3D(**detection.get("position", obj.position.__dict__))
                obj.confidence = detection.get("confidence", obj.confidence)
                obj.last_detected = current_time
            else:
                # Create new object
                obj = RealWorldObject(
                    object_id=object_id,
                    object_type=detection.get("type", "unknown"),
                    position=Vector3D(**detection.get("position", {"x": 0, "y": 0, "z": 0})),
                    orientation=Transform3D(),
                    bounding_box=(Vector3D(0, 0, 0), Vector3D(1, 1, 1)),
                    confidence=detection.get("confidence", 0.5),
                    last_detected=current_time,
                    tracking_method=TrackingMethod.MARKERLESS,
                    features=detection.get("features", {}),
                )

                self.real_world_objects[object_id] = obj

        # Remove old objects
        stale_threshold = 5.0  # seconds
        stale_objects = [
            obj_id
            for obj_id, obj in self.real_world_objects.items()
            if current_time - obj.last_detected > stale_threshold
        ]

        for obj_id in stale_objects:
            del self.real_world_objects[obj_id]

    async def _update_lighting(self, lighting_info: Dict[str, Any]):
        """Update lighting information for virtual objects"""
        # Update lighting for all virtual objects
        for virtual_obj in self.virtual_objects.values():
            if "lighting" not in virtual_obj.material_properties:
                virtual_obj.material_properties["lighting"] = {}

            virtual_obj.material_properties["lighting"].update(lighting_info)

    async def _render_mixed_reality(self, camera_frame: np.ndarray):
        """Render mixed reality scene"""
        try:
            if self.reality_mode == RealityMode.PURE_VR:
                # Render only virtual content
                await self._render_vr_scene()

            elif self.reality_mode == RealityMode.AR_OVERLAY:
                # Render virtual objects over real camera feed
                await self._render_ar_overlay(camera_frame)

            elif self.reality_mode == RealityMode.MIXED_REALITY:
                # Full mixed reality with occlusion
                await self._render_mixed_scene(camera_frame)

            elif self.reality_mode == RealityMode.PASSTHROUGH:
                # Show camera feed with minimal overlay
                await self._render_passthrough(camera_frame)

        except Exception as e:
            logger.error(f"Error rendering MR scene: {e}")

    async def _render_ar_overlay(self, camera_frame: np.ndarray):
        """Render AR overlay on camera frame"""
        # Render virtual objects on top of camera frame
        for virtual_obj in self.virtual_objects.values():
            if virtual_obj.is_visible():
                await self._render_virtual_object(virtual_obj, camera_frame)

    async def _render_mixed_scene(self, camera_frame: np.ndarray):
        """Render full mixed reality scene with occlusion"""
        # Render with proper occlusion handling
        occlusion_mask = await self._compute_occlusion_mask(camera_frame)

        for virtual_obj in self.virtual_objects.values():
            if virtual_obj.is_visible():
                await self._render_virtual_object_with_occlusion(
                    virtual_obj, camera_frame, occlusion_mask
                )

    async def _render_virtual_object(self, virtual_obj: VirtualObject, background: np.ndarray):
        """Render a virtual object"""
        if self.virtual_renderer:
            await self.virtual_renderer.render_object(
                virtual_obj, self.current_camera_pose, background
            )

    async def _render_virtual_object_with_occlusion(
        self, virtual_obj: VirtualObject, background: np.ndarray, occlusion_mask: np.ndarray
    ):
        """Render virtual object with occlusion"""
        if self.virtual_renderer and self.occlusion_renderer:
            await self.occlusion_renderer.render_with_occlusion(
                virtual_obj, self.current_camera_pose, background, occlusion_mask
            )

    async def _compute_occlusion_mask(self, frame: np.ndarray) -> np.ndarray:
        """Compute occlusion mask from real world objects"""
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)

        for real_obj in self.real_world_objects.values():
            # Project object bounding box to screen
            screen_bbox = await self._project_object_to_screen(real_obj)
            if screen_bbox:
                x1, y1, x2, y2 = screen_bbox
                mask[y1:y2, x1:x2] = 255

        return mask

    async def _project_object_to_screen(
        self, real_obj: RealWorldObject
    ) -> Optional[Tuple[int, int, int, int]]:
        """Project real world object to screen coordinates"""
        try:
            # Project 3D bounding box to 2D screen
            min_point, max_point = real_obj.bounding_box

            # Create 8 corners of bounding box
            corners_3d = [
                min_point,
                Vector3D(max_point.x, min_point.y, min_point.z),
                Vector3D(min_point.x, max_point.y, min_point.z),
                Vector3D(min_point.x, min_point.y, max_point.z),
                Vector3D(max_point.x, max_point.y, min_point.z),
                Vector3D(max_point.x, min_point.y, max_point.z),
                Vector3D(min_point.x, max_point.y, max_point.z),
                max_point,
            ]

            # Project to screen
            screen_points = []
            for corner in corners_3d:
                screen_x, screen_y, _ = SpatialMath.world_to_screen(
                    corner, self.current_camera_pose.to_matrix(), self.camera_matrix, 1280, 720
                )
                screen_points.append((int(screen_x), int(screen_y)))

            if screen_points:
                xs, ys = zip(*screen_points)
                return (min(xs), min(ys), max(xs), max(ys))

        except Exception as e:
            logger.error(f"Error projecting object to screen: {e}")

        return None

    async def add_virtual_object(
        self,
        object_id: str,
        object_type: str,
        position: Vector3D,
        scale: Vector3D = None,
        material_properties: Dict[str, Any] = None,
    ) -> bool:
        """Add virtual object to the scene"""
        try:
            virtual_obj = VirtualObject(
                object_id=object_id,
                object_type=object_type,
                position=position,
                orientation=Transform3D(),
                scale=scale or Vector3D(1, 1, 1),
                visibility=1.0,
                occlusion_enabled=True,
                shadow_casting=True,
                material_properties=material_properties or {},
            )

            self.virtual_objects[object_id] = virtual_obj

            logger.info(f"Added virtual object {object_id} at {position}")
            return True

        except Exception as e:
            logger.error(f"Error adding virtual object: {e}")
            return False

    async def remove_virtual_object(self, object_id: str) -> bool:
        """Remove virtual object from scene"""
        if object_id in self.virtual_objects:
            del self.virtual_objects[object_id]
            logger.info(f"Removed virtual object {object_id}")
            return True

        return False

    async def create_spatial_anchor(
        self, anchor_id: str, position: Vector3D, orientation: Transform3D = None
    ) -> bool:
        """Create spatial anchor for persistent AR placement"""
        try:
            anchor = SpatialAnchor(
                anchor_id=anchor_id,
                world_position=position,
                world_orientation=orientation or Transform3D(),
                confidence=0.8,
                creation_time=time.time(),
                last_updated=time.time(),
                persistence_data=b"",  # Would contain actual persistence data
                tracking_quality=1.0,
            )

            self.spatial_anchors[anchor_id] = anchor

            logger.info(f"Created spatial anchor {anchor_id} at {position}")
            return True

        except Exception as e:
            logger.error(f"Error creating spatial anchor: {e}")
            return False

    def set_reality_mode(self, mode: RealityMode):
        """Set reality mode"""
        if mode != self.reality_mode:
            logger.info(f"Switching reality mode from {self.reality_mode} to {mode}")
            self.reality_mode = mode

    def get_camera_pose(self) -> Transform3D:
        """Get current camera pose"""
        return self.current_camera_pose

    def get_real_world_objects(self) -> Dict[str, RealWorldObject]:
        """Get detected real world objects"""
        return self.real_world_objects.copy()

    def get_virtual_objects(self) -> Dict[str, VirtualObject]:
        """Get virtual objects"""
        return self.virtual_objects.copy()

    def get_spatial_anchors(self) -> Dict[str, SpatialAnchor]:
        """Get spatial anchors"""
        return self.spatial_anchors.copy()

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "frame_time": self.performance_monitor.get_average_time("mr_frame"),
            "fps": self.performance_monitor.get_fps("mr_frame"),
            "reality_mode": self.reality_mode.value,
            "tracking_active": self.tracking_active,
            "camera_calibrated": self.camera_calibrated,
            "real_objects": len(self.real_world_objects),
            "virtual_objects": len(self.virtual_objects),
            "spatial_anchors": len(self.spatial_anchors),
            "slam_keyframes": len(self.slam_system.keyframes),
            "slam_map_points": len(self.slam_system.map_points),
        }


# Mock and helper classes
class MockCamera:
    """Mock camera for testing"""

    def __init__(self):
        self.frame_count = 0

    def read(self):
        """Return mock frame"""
        self.frame_count += 1
        frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        return True, frame

    def release(self):
        """Release camera"""
        pass


class VirtualObjectRenderer:
    """Virtual object renderer"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def render_object(
        self, virtual_obj: VirtualObject, camera_pose: Transform3D, background: np.ndarray
    ):
        """Render virtual object"""
        # Placeholder for actual rendering
        pass


class OcclusionRenderer:
    """Occlusion-aware renderer"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def render_with_occlusion(
        self,
        virtual_obj: VirtualObject,
        camera_pose: Transform3D,
        background: np.ndarray,
        occlusion_mask: np.ndarray,
    ):
        """Render with occlusion"""
        # Placeholder for occlusion rendering
        pass


class LightingEstimator:
    """Real-world lighting estimator"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def estimate(self, frame: np.ndarray) -> Dict[str, Any]:
        """Estimate lighting from frame"""
        # Simple lighting estimation
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ambient = np.mean(gray) / 255.0

        return {"ambient": ambient, "directional": Vector3D(0, 1, 0), "color_temperature": 5500}
