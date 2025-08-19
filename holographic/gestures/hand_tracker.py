"""
Advanced 3D hand tracking for holographic interaction
"""

import numpy as np
import asyncio
import logging
import time
import cv2
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import math
import threading
from concurrent.futures import ThreadPoolExecutor

from ..core.base import (
    HolographicBase, 
    Vector3D, 
    Transform3D,
    HolographicPerformanceMonitor,
    GestureRecognitionError
)
from ..core.math_utils import SpatialMath

logger = logging.getLogger(__name__)

class HandSide(Enum):
    """Hand side enumeration"""
    LEFT = "left"
    RIGHT = "right"
    UNKNOWN = "unknown"

class FingerType(Enum):
    """Finger type enumeration"""
    THUMB = "thumb"
    INDEX = "index"
    MIDDLE = "middle"
    RING = "ring"
    PINKY = "pinky"

@dataclass
class Joint3D:
    """3D joint position with confidence"""
    position: Vector3D
    confidence: float
    velocity: Vector3D = None
    acceleration: Vector3D = None
    
    def __post_init__(self):
        if self.velocity is None:
            self.velocity = Vector3D(0, 0, 0)
        if self.acceleration is None:
            self.acceleration = Vector3D(0, 0, 0)

@dataclass
class Finger:
    """Finger representation with joints"""
    finger_type: FingerType
    joints: List[Joint3D]  # MCP, PIP, DIP, TIP
    extended: bool = False
    
    @property
    def tip_position(self) -> Vector3D:
        """Get fingertip position"""
        return self.joints[-1].position if self.joints else Vector3D(0, 0, 0)
    
    @property
    def length(self) -> float:
        """Calculate finger length"""
        if len(self.joints) < 2:
            return 0.0
        
        total_length = 0.0
        for i in range(1, len(self.joints)):
            total_length += SpatialMath.distance_3d(
                self.joints[i-1].position, 
                self.joints[i].position
            )
        return total_length

@dataclass
class HandLandmarks:
    """Complete hand landmark data"""
    hand_id: str
    side: HandSide
    wrist: Joint3D
    fingers: Dict[FingerType, Finger]
    palm_center: Vector3D
    palm_normal: Vector3D
    confidence: float
    timestamp: float
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()
    
    @property
    def fingertips(self) -> Dict[FingerType, Vector3D]:
        """Get all fingertip positions"""
        return {
            finger_type: finger.tip_position 
            for finger_type, finger in self.fingers.items()
        }
    
    def distance_between_fingers(self, finger1: FingerType, finger2: FingerType) -> float:
        """Calculate distance between fingertips"""
        if finger1 in self.fingers and finger2 in self.fingers:
            return SpatialMath.distance_3d(
                self.fingers[finger1].tip_position,
                self.fingers[finger2].tip_position
            )
        return float('inf')
    
    def is_pinching(self, threshold: float = 0.03) -> bool:
        """Check if thumb and index finger are pinching"""
        return self.distance_between_fingers(FingerType.THUMB, FingerType.INDEX) < threshold
    
    def is_fist(self, threshold: float = 0.8) -> bool:
        """Check if hand is making a fist"""
        extended_count = sum(1 for finger in self.fingers.values() if finger.extended)
        return extended_count <= 1  # Only thumb might be extended in a fist
    
    def is_open_palm(self, threshold: float = 0.8) -> bool:
        """Check if hand is an open palm"""
        extended_count = sum(1 for finger in self.fingers.values() if finger.extended)
        return extended_count >= 4  # At least 4 fingers extended

class MultiCameraSystem:
    """Multi-camera system for 3D hand tracking"""
    
    def __init__(self, camera_count: int = 2):
        self.camera_count = camera_count
        self.cameras = []
        self.camera_matrices = []
        self.distortion_coeffs = []
        self.stereo_calibrated = False
        
        # Stereo calibration data
        self.fundamental_matrix = None
        self.essential_matrix = None
        self.rotation_matrix = None
        self.translation_vector = None
        
    def add_camera(self, camera_id: int, camera_matrix: np.ndarray, 
                   distortion_coeffs: np.ndarray):
        """Add a camera to the system"""
        self.cameras.append(camera_id)
        self.camera_matrices.append(camera_matrix)
        self.distortion_coeffs.append(distortion_coeffs)
    
    def calibrate_stereo(self, object_points: List[np.ndarray], 
                        image_points_left: List[np.ndarray],
                        image_points_right: List[np.ndarray],
                        image_size: Tuple[int, int]) -> bool:
        """Calibrate stereo camera system"""
        try:
            if len(self.camera_matrices) < 2:
                return False
            
            # Stereo calibration
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            
            ret, _, _, _, _, R, T, E, F = cv2.stereoCalibrate(
                object_points,
                image_points_left,
                image_points_right,
                self.camera_matrices[0],
                self.distortion_coeffs[0],
                self.camera_matrices[1],
                self.distortion_coeffs[1],
                image_size,
                criteria=criteria
            )
            
            if ret:
                self.rotation_matrix = R
                self.translation_vector = T
                self.essential_matrix = E
                self.fundamental_matrix = F
                self.stereo_calibrated = True
                logger.info("Stereo calibration successful")
                return True
            
        except Exception as e:
            logger.error(f"Stereo calibration failed: {e}")
        
        return False
    
    def triangulate_points(self, points_left: np.ndarray, 
                          points_right: np.ndarray) -> np.ndarray:
        """Triangulate 3D points from stereo images"""
        if not self.stereo_calibrated or len(self.camera_matrices) < 2:
            raise ValueError("Stereo system not calibrated")
        
        # Create projection matrices
        P1 = np.hstack([self.camera_matrices[0], np.zeros((3, 1))])
        P2 = np.hstack([
            self.camera_matrices[1] @ self.rotation_matrix,
            self.camera_matrices[1] @ self.translation_vector
        ])
        
        # Triangulate points
        points_4d = cv2.triangulatePoints(P1, P2, points_left.T, points_right.T)
        
        # Convert to 3D (homogeneous to cartesian)
        points_3d = points_4d[:3] / points_4d[3]
        
        return points_3d.T

class HandTracker(HolographicBase):
    """
    Advanced 3D hand tracking system using multiple cameras
    and neural networks for robust gesture recognition
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("HandTracker")
        self.config = config
        self.performance_monitor = HolographicPerformanceMonitor()
        
        # Camera system
        self.camera_system = MultiCameraSystem(config.get('camera_count', 2))
        self.camera_feeds = {}
        
        # Hand detection models
        self.hand_detector = None
        self.landmark_detector = None
        self.model_initialized = False
        
        # Tracking state
        self.tracked_hands: Dict[str, HandLandmarks] = {}
        self.hand_history: Dict[str, List[HandLandmarks]] = {}
        self.max_history_length = 30
        
        # Processing
        self.processing_executor = ThreadPoolExecutor(max_workers=4)
        self.tracking_active = False
        
        # Kalman filters for smoothing
        self.kalman_filters: Dict[str, Dict[str, Any]] = {}
        
        # Configuration
        self.confidence_threshold = config.get('confidence_threshold', 0.7)
        self.tracking_distance_threshold = config.get('tracking_distance', 0.1)
        self.smoothing_enabled = config.get('smoothing_enabled', True)
        
        logger.info("HandTracker initialized")
    
    async def initialize(self) -> bool:
        """Initialize the hand tracker"""
        try:
            logger.info("Initializing HandTracker...")
            
            # Initialize ML models
            await self._initialize_models()
            
            # Setup camera system
            await self._setup_cameras()
            
            # Initialize Kalman filters
            self._initialize_kalman_filters()
            
            self.initialized = True
            logger.info("HandTracker initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize HandTracker: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the hand tracker"""
        logger.info("Shutting down HandTracker...")
        
        self.tracking_active = False
        
        # Clear tracking data
        self.tracked_hands.clear()
        self.hand_history.clear()
        self.kalman_filters.clear()
        
        # Close camera feeds
        for feed in self.camera_feeds.values():
            if hasattr(feed, 'release'):
                feed.release()
        self.camera_feeds.clear()
        
        # Shutdown executor
        self.processing_executor.shutdown(wait=True)
        
        self.initialized = False
        logger.info("HandTracker shutdown complete")
    
    async def _initialize_models(self):
        """Initialize hand detection and landmark models"""
        try:
            # In a real implementation, this would load MediaPipe, OpenPose, or custom models
            # For now, we'll create placeholder models
            
            self.hand_detector = HandDetectorModel()
            self.landmark_detector = LandmarkDetectorModel()
            
            self.model_initialized = True
            logger.info("Hand tracking models initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            raise
    
    async def _setup_cameras(self):
        """Setup camera system"""
        try:
            camera_count = self.config.get('camera_count', 2)
            
            for i in range(camera_count):
                # In practice, this would connect to actual cameras
                # For simulation, we'll create mock camera feeds
                camera_feed = MockCameraFeed(i)
                self.camera_feeds[f"camera_{i}"] = camera_feed
                
                # Add camera to system with default calibration
                camera_matrix = np.array([
                    [800, 0, 320],
                    [0, 800, 240],
                    [0, 0, 1]
                ], dtype=np.float32)
                
                distortion = np.zeros(5, dtype=np.float32)
                
                self.camera_system.add_camera(i, camera_matrix, distortion)
            
            # Simulate stereo calibration
            if camera_count >= 2:
                self._simulate_stereo_calibration()
            
            logger.info(f"Setup {camera_count} cameras")
            
        except Exception as e:
            logger.error(f"Failed to setup cameras: {e}")
            raise
    
    def _simulate_stereo_calibration(self):
        """Simulate stereo calibration for testing"""
        # Create mock calibration data
        object_points = [np.random.random((9, 3)).astype(np.float32) for _ in range(10)]
        image_points_left = [np.random.random((9, 2)).astype(np.float32) for _ in range(10)]
        image_points_right = [np.random.random((9, 2)).astype(np.float32) for _ in range(10)]
        
        # Simulate successful calibration
        self.camera_system.stereo_calibrated = True
        self.camera_system.rotation_matrix = np.eye(3, dtype=np.float32)
        self.camera_system.translation_vector = np.array([0.1, 0, 0], dtype=np.float32).reshape(3, 1)
        
        logger.info("Stereo calibration simulated")
    
    def _initialize_kalman_filters(self):
        """Initialize Kalman filters for hand smoothing"""
        if not self.smoothing_enabled:
            return
        
        # Kalman filter for each joint
        # State: [x, y, z, vx, vy, vz]
        # Measurement: [x, y, z]
        
        self.kalman_template = {
            'filter': cv2.KalmanFilter(6, 3),
            'initialized': False
        }
        
        # Configure Kalman filter
        kalman = self.kalman_template['filter']
        
        # Transition matrix (constant velocity model)
        dt = 1.0 / 30.0  # Assume 30 FPS
        kalman.transitionMatrix = np.array([
            [1, 0, 0, dt, 0, 0],
            [0, 1, 0, 0, dt, 0],
            [0, 0, 1, 0, 0, dt],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]
        ], dtype=np.float32)
        
        # Measurement matrix
        kalman.measurementMatrix = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0]
        ], dtype=np.float32)
        
        # Process noise
        kalman.processNoiseCov = np.eye(6, dtype=np.float32) * 0.01
        
        # Measurement noise
        kalman.measurementNoiseCov = np.eye(3, dtype=np.float32) * 0.1
        
        # Error covariance
        kalman.errorCovPost = np.eye(6, dtype=np.float32)
    
    async def start_tracking(self):
        """Start hand tracking"""
        if not self.initialized or self.tracking_active:
            return
        
        logger.info("Starting hand tracking...")
        self.tracking_active = True
        
        # Start tracking loop
        asyncio.create_task(self._tracking_loop())
    
    async def stop_tracking(self):
        """Stop hand tracking"""
        logger.info("Stopping hand tracking...")
        self.tracking_active = False
    
    async def _tracking_loop(self):
        """Main tracking loop"""
        logger.info("Hand tracking loop started")
        
        try:
            while self.tracking_active:
                self.performance_monitor.start_timer("hand_tracking")
                
                # Capture frames from all cameras
                frames = await self._capture_frames()
                
                if frames:
                    # Detect and track hands
                    hands = await self._process_frames(frames)
                    
                    # Update tracking state
                    await self._update_tracking(hands)
                
                tracking_time = self.performance_monitor.end_timer("hand_tracking")
                
                # Maintain frame rate
                await asyncio.sleep(max(0, 1/30 - tracking_time))  # 30 FPS target
                
        except Exception as e:
            logger.error(f"Error in tracking loop: {e}")
        finally:
            logger.info("Hand tracking loop ended")
    
    async def _capture_frames(self) -> Dict[str, np.ndarray]:
        """Capture frames from all cameras"""
        frames = {}
        
        capture_tasks = []
        for camera_id, feed in self.camera_feeds.items():
            task = asyncio.get_event_loop().run_in_executor(
                self.processing_executor, feed.capture_frame
            )
            capture_tasks.append((camera_id, task))
        
        # Wait for all captures
        for camera_id, task in capture_tasks:
            try:
                frame = await task
                if frame is not None:
                    frames[camera_id] = frame
            except Exception as e:
                logger.error(f"Failed to capture from {camera_id}: {e}")
        
        return frames
    
    async def _process_frames(self, frames: Dict[str, np.ndarray]) -> List[HandLandmarks]:
        """Process frames to detect and track hands"""
        hands = []
        
        # Process each camera's frame
        detection_tasks = []
        for camera_id, frame in frames.items():
            task = asyncio.get_event_loop().run_in_executor(
                self.processing_executor, 
                self._detect_hands_in_frame, 
                frame, camera_id
            )
            detection_tasks.append(task)
        
        # Collect 2D detections
        camera_detections = await asyncio.gather(*detection_tasks, return_exceptions=True)
        
        # Triangulate 3D positions if we have stereo
        if (len(camera_detections) >= 2 and 
            self.camera_system.stereo_calibrated and
            not any(isinstance(det, Exception) for det in camera_detections)):
            
            hands = await self._triangulate_3d_hands(camera_detections)
        else:
            # Use single camera with depth estimation
            for detection in camera_detections:
                if not isinstance(detection, Exception) and detection:
                    hands.extend(detection)
        
        return hands
    
    def _detect_hands_in_frame(self, frame: np.ndarray, camera_id: str) -> List[HandLandmarks]:
        """Detect hands in a single frame"""
        try:
            # Placeholder hand detection
            # In practice, this would use MediaPipe, OpenPose, or custom models
            
            hands = []
            
            # Simulate hand detection
            if self.hand_detector and self.landmark_detector:
                # Mock detection - in practice would run actual inference
                detected_hands = self.hand_detector.detect(frame)
                
                for detection in detected_hands:
                    landmarks = self.landmark_detector.extract_landmarks(frame, detection)
                    if landmarks:
                        hands.append(landmarks)
            
            return hands
            
        except Exception as e:
            logger.error(f"Error detecting hands in frame: {e}")
            return []
    
    async def _triangulate_3d_hands(self, camera_detections: List[List[HandLandmarks]]) -> List[HandLandmarks]:
        """Triangulate 3D hand positions from multiple cameras"""
        try:
            if len(camera_detections) < 2:
                return []
            
            left_hands = camera_detections[0]
            right_hands = camera_detections[1]
            
            hands_3d = []
            
            # Match hands between cameras and triangulate
            for left_hand in left_hands:
                for right_hand in right_hands:
                    # Simple matching based on hand side and position
                    if left_hand.side == right_hand.side:
                        # Triangulate landmarks
                        hand_3d = await self._triangulate_hand_landmarks(left_hand, right_hand)
                        if hand_3d:
                            hands_3d.append(hand_3d)
                        break
            
            return hands_3d
            
        except Exception as e:
            logger.error(f"Error triangulating 3D hands: {e}")
            return []
    
    async def _triangulate_hand_landmarks(self, left_hand: HandLandmarks, 
                                        right_hand: HandLandmarks) -> Optional[HandLandmarks]:
        """Triangulate landmarks from stereo hands"""
        try:
            # Create arrays of corresponding points
            left_points = []
            right_points = []
            
            # Add wrist
            left_points.append([left_hand.wrist.position.x, left_hand.wrist.position.y])
            right_points.append([right_hand.wrist.position.x, right_hand.wrist.position.y])
            
            # Add finger joints
            for finger_type in FingerType:
                if finger_type in left_hand.fingers and finger_type in right_hand.fingers:
                    left_finger = left_hand.fingers[finger_type]
                    right_finger = right_hand.fingers[finger_type]
                    
                    for left_joint, right_joint in zip(left_finger.joints, right_finger.joints):
                        left_points.append([left_joint.position.x, left_joint.position.y])
                        right_points.append([right_joint.position.x, right_joint.position.y])
            
            # Triangulate points
            left_array = np.array(left_points, dtype=np.float32)
            right_array = np.array(right_points, dtype=np.float32)
            
            points_3d = self.camera_system.triangulate_points(left_array, right_array)
            
            # Reconstruct hand landmarks
            hand_3d = await self._reconstruct_3d_hand(left_hand, points_3d)
            
            return hand_3d
            
        except Exception as e:
            logger.error(f"Error triangulating hand landmarks: {e}")
            return None
    
    async def _reconstruct_3d_hand(self, reference_hand: HandLandmarks, 
                                 points_3d: np.ndarray) -> HandLandmarks:
        """Reconstruct 3D hand from triangulated points"""
        point_idx = 0
        
        # Reconstruct wrist
        wrist_3d = Joint3D(
            position=Vector3D(points_3d[point_idx, 0], points_3d[point_idx, 1], points_3d[point_idx, 2]),
            confidence=reference_hand.wrist.confidence
        )
        point_idx += 1
        
        # Reconstruct fingers
        fingers_3d = {}
        for finger_type in FingerType:
            if finger_type in reference_hand.fingers:
                ref_finger = reference_hand.fingers[finger_type]
                joints_3d = []
                
                for ref_joint in ref_finger.joints:
                    if point_idx < len(points_3d):
                        joint_3d = Joint3D(
                            position=Vector3D(
                                points_3d[point_idx, 0], 
                                points_3d[point_idx, 1], 
                                points_3d[point_idx, 2]
                            ),
                            confidence=ref_joint.confidence
                        )
                        joints_3d.append(joint_3d)
                        point_idx += 1
                
                fingers_3d[finger_type] = Finger(
                    finger_type=finger_type,
                    joints=joints_3d,
                    extended=ref_finger.extended
                )
        
        # Calculate palm center and normal
        palm_center = self._calculate_palm_center(wrist_3d, fingers_3d)
        palm_normal = self._calculate_palm_normal(fingers_3d)
        
        hand_3d = HandLandmarks(
            hand_id=reference_hand.hand_id,
            side=reference_hand.side,
            wrist=wrist_3d,
            fingers=fingers_3d,
            palm_center=palm_center,
            palm_normal=palm_normal,
            confidence=reference_hand.confidence,
            timestamp=time.time()
        )
        
        return hand_3d
    
    def _calculate_palm_center(self, wrist: Joint3D, fingers: Dict[FingerType, Finger]) -> Vector3D:
        """Calculate palm center from landmarks"""
        positions = [wrist.position]
        
        # Add MCP joints (first joint of each finger)
        for finger in fingers.values():
            if finger.joints:
                positions.append(finger.joints[0].position)
        
        # Average position
        if positions:
            avg_x = sum(p.x for p in positions) / len(positions)
            avg_y = sum(p.y for p in positions) / len(positions)
            avg_z = sum(p.z for p in positions) / len(positions)
            return Vector3D(avg_x, avg_y, avg_z)
        
        return wrist.position
    
    def _calculate_palm_normal(self, fingers: Dict[FingerType, Finger]) -> Vector3D:
        """Calculate palm normal vector"""
        try:
            # Use index, middle, and ring finger MCP joints to define palm plane
            if (FingerType.INDEX in fingers and FingerType.MIDDLE in fingers and 
                FingerType.RING in fingers):
                
                index_mcp = fingers[FingerType.INDEX].joints[0].position
                middle_mcp = fingers[FingerType.MIDDLE].joints[0].position
                ring_mcp = fingers[FingerType.RING].joints[0].position
                
                # Calculate normal using cross product
                v1 = middle_mcp - index_mcp
                v2 = ring_mcp - index_mcp
                normal = SpatialMath.cross_product(v1, v2).normalize()
                
                return normal
        except Exception:
            pass
        
        # Default normal (pointing up)
        return Vector3D(0, 1, 0)
    
    async def _update_tracking(self, detected_hands: List[HandLandmarks]):
        """Update hand tracking state"""
        current_time = time.time()
        
        # Match detected hands with tracked hands
        matched_hands = {}
        unmatched_detections = detected_hands.copy()
        
        for hand_id, tracked_hand in self.tracked_hands.items():
            best_match = None
            best_distance = float('inf')
            
            for detection in unmatched_detections:
                # Calculate distance between palm centers
                distance = SpatialMath.distance_3d(
                    tracked_hand.palm_center, detection.palm_center
                )
                
                if (distance < self.tracking_distance_threshold and 
                    distance < best_distance and 
                    tracked_hand.side == detection.side):
                    
                    best_match = detection
                    best_distance = distance
            
            if best_match:
                # Update existing hand
                updated_hand = await self._update_hand_tracking(
                    hand_id, tracked_hand, best_match
                )
                matched_hands[hand_id] = updated_hand
                unmatched_detections.remove(best_match)
        
        # Add new hands
        for detection in unmatched_detections:
            hand_id = f"hand_{len(self.tracked_hands)}_{int(current_time)}"
            detection.hand_id = hand_id
            matched_hands[hand_id] = detection
            
            # Initialize Kalman filter for new hand
            if self.smoothing_enabled:
                self._initialize_hand_kalman_filter(hand_id, detection)
        
        # Remove lost hands
        lost_hands = set(self.tracked_hands.keys()) - set(matched_hands.keys())
        for hand_id in lost_hands:
            logger.debug(f"Lost tracking for hand {hand_id}")
            if hand_id in self.kalman_filters:
                del self.kalman_filters[hand_id]
        
        # Update tracked hands
        self.tracked_hands = matched_hands
        
        # Update history
        for hand_id, hand in self.tracked_hands.items():
            if hand_id not in self.hand_history:
                self.hand_history[hand_id] = []
            
            self.hand_history[hand_id].append(hand)
            
            # Limit history length
            if len(self.hand_history[hand_id]) > self.max_history_length:
                self.hand_history[hand_id] = self.hand_history[hand_id][-self.max_history_length:]
    
    async def _update_hand_tracking(self, hand_id: str, tracked_hand: HandLandmarks,
                                  detection: HandLandmarks) -> HandLandmarks:
        """Update hand tracking with new detection"""
        # Apply smoothing if enabled
        if self.smoothing_enabled and hand_id in self.kalman_filters:
            smoothed_hand = await self._apply_kalman_smoothing(hand_id, detection)
            return smoothed_hand
        else:
            # Use detection directly
            detection.hand_id = hand_id
            return detection
    
    async def _apply_kalman_smoothing(self, hand_id: str, 
                                    detection: HandLandmarks) -> HandLandmarks:
        """Apply Kalman filtering for smooth tracking"""
        try:
            # Apply smoothing to each joint
            smoothed_hand = HandLandmarks(
                hand_id=hand_id,
                side=detection.side,
                wrist=detection.wrist,  # Will be updated below
                fingers={},
                palm_center=detection.palm_center,
                palm_normal=detection.palm_normal,
                confidence=detection.confidence,
                timestamp=detection.timestamp
            )
            
            hand_filters = self.kalman_filters[hand_id]
            
            # Smooth wrist
            if 'wrist' in hand_filters:
                smoothed_pos = self._smooth_joint_position(
                    hand_filters['wrist'], detection.wrist.position
                )
                smoothed_hand.wrist = Joint3D(
                    position=smoothed_pos,
                    confidence=detection.wrist.confidence
                )
            
            # Smooth fingers
            for finger_type, finger in detection.fingers.items():
                smoothed_joints = []
                
                for i, joint in enumerate(finger.joints):
                    filter_key = f"{finger_type.value}_{i}"
                    
                    if filter_key in hand_filters:
                        smoothed_pos = self._smooth_joint_position(
                            hand_filters[filter_key], joint.position
                        )
                        smoothed_joints.append(Joint3D(
                            position=smoothed_pos,
                            confidence=joint.confidence
                        ))
                    else:
                        smoothed_joints.append(joint)
                
                smoothed_hand.fingers[finger_type] = Finger(
                    finger_type=finger_type,
                    joints=smoothed_joints,
                    extended=finger.extended
                )
            
            # Recalculate palm center and normal
            smoothed_hand.palm_center = self._calculate_palm_center(
                smoothed_hand.wrist, smoothed_hand.fingers
            )
            smoothed_hand.palm_normal = self._calculate_palm_normal(smoothed_hand.fingers)
            
            return smoothed_hand
            
        except Exception as e:
            logger.error(f"Error applying Kalman smoothing: {e}")
            return detection
    
    def _smooth_joint_position(self, kalman_filter: Dict[str, Any], 
                             position: Vector3D) -> Vector3D:
        """Smooth joint position using Kalman filter"""
        try:
            filter_obj = kalman_filter['filter']
            
            if not kalman_filter['initialized']:
                # Initialize filter state
                filter_obj.statePre = np.array([
                    position.x, position.y, position.z, 0, 0, 0
                ], dtype=np.float32).reshape(6, 1)
                
                filter_obj.statePost = filter_obj.statePre.copy()
                kalman_filter['initialized'] = True
            
            # Predict
            prediction = filter_obj.predict()
            
            # Update with measurement
            measurement = np.array([position.x, position.y, position.z], dtype=np.float32).reshape(3, 1)
            filter_obj.correct(measurement)
            
            # Return smoothed position
            state = filter_obj.statePost
            return Vector3D(float(state[0]), float(state[1]), float(state[2]))
            
        except Exception as e:
            logger.error(f"Error in Kalman smoothing: {e}")
            return position
    
    def _initialize_hand_kalman_filter(self, hand_id: str, hand: HandLandmarks):
        """Initialize Kalman filters for a new hand"""
        if not self.smoothing_enabled:
            return
        
        hand_filters = {}
        
        # Wrist filter
        wrist_filter = {
            'filter': cv2.KalmanFilter(6, 3),
            'initialized': False
        }
        self._configure_kalman_filter(wrist_filter['filter'])
        hand_filters['wrist'] = wrist_filter
        
        # Finger joint filters
        for finger_type, finger in hand.fingers.items():
            for i, joint in enumerate(finger.joints):
                filter_key = f"{finger_type.value}_{i}"
                joint_filter = {
                    'filter': cv2.KalmanFilter(6, 3),
                    'initialized': False
                }
                self._configure_kalman_filter(joint_filter['filter'])
                hand_filters[filter_key] = joint_filter
        
        self.kalman_filters[hand_id] = hand_filters
    
    def _configure_kalman_filter(self, kalman_filter):
        """Configure a Kalman filter with default parameters"""
        dt = 1.0 / 30.0  # 30 FPS
        
        # Transition matrix
        kalman_filter.transitionMatrix = np.array([
            [1, 0, 0, dt, 0, 0],
            [0, 1, 0, 0, dt, 0],
            [0, 0, 1, 0, 0, dt],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]
        ], dtype=np.float32)
        
        # Measurement matrix
        kalman_filter.measurementMatrix = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0]
        ], dtype=np.float32)
        
        # Noise matrices
        kalman_filter.processNoiseCov = np.eye(6, dtype=np.float32) * 0.01
        kalman_filter.measurementNoiseCov = np.eye(3, dtype=np.float32) * 0.1
        kalman_filter.errorCovPost = np.eye(6, dtype=np.float32)
    
    def get_tracked_hands(self) -> Dict[str, HandLandmarks]:
        """Get currently tracked hands"""
        return self.tracked_hands.copy()
    
    def get_hand_by_side(self, side: HandSide) -> Optional[HandLandmarks]:
        """Get hand by side (left/right)"""
        for hand in self.tracked_hands.values():
            if hand.side == side:
                return hand
        return None
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "tracking_time": self.performance_monitor.get_average_time("hand_tracking"),
            "fps": self.performance_monitor.get_fps("hand_tracking"),
            "tracked_hands": len(self.tracked_hands),
            "cameras_active": len(self.camera_feeds),
            "stereo_calibrated": self.camera_system.stereo_calibrated,
            "smoothing_enabled": self.smoothing_enabled,
            "model_initialized": self.model_initialized
        }

# Mock classes for testing
class HandDetectorModel:
    """Mock hand detector for testing"""
    
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Mock hand detection"""
        # Return mock detections
        return [
            {"bbox": [100, 100, 200, 200], "confidence": 0.9, "side": "right"},
            {"bbox": [300, 100, 400, 200], "confidence": 0.8, "side": "left"}
        ]

class LandmarkDetectorModel:
    """Mock landmark detector for testing"""
    
    def extract_landmarks(self, frame: np.ndarray, detection: Dict[str, Any]) -> Optional[HandLandmarks]:
        """Mock landmark extraction"""
        # Create mock hand landmarks
        try:
            side = HandSide.RIGHT if detection["side"] == "right" else HandSide.LEFT
            
            # Mock wrist position
            wrist = Joint3D(
                position=Vector3D(0.5, 0.5, 0.5),
                confidence=0.9
            )
            
            # Mock fingers
            fingers = {}
            for finger_type in FingerType:
                joints = []
                for i in range(4):  # MCP, PIP, DIP, TIP
                    joint_pos = Vector3D(
                        0.5 + i * 0.1, 
                        0.5 + i * 0.1, 
                        0.5 + i * 0.05
                    )
                    joints.append(Joint3D(position=joint_pos, confidence=0.8))
                
                fingers[finger_type] = Finger(
                    finger_type=finger_type,
                    joints=joints,
                    extended=True
                )
            
            hand = HandLandmarks(
                hand_id="",
                side=side,
                wrist=wrist,
                fingers=fingers,
                palm_center=Vector3D(0.5, 0.5, 0.5),
                palm_normal=Vector3D(0, 1, 0),
                confidence=detection["confidence"],
                timestamp=time.time()
            )
            
            return hand
            
        except Exception:
            return None

class MockCameraFeed:
    """Mock camera feed for testing"""
    
    def __init__(self, camera_id: int):
        self.camera_id = camera_id
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture a mock frame"""
        # Return a random frame for testing
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)