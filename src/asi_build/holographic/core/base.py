"""
Base holographic system classes and utilities
"""

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


class HologramType(Enum):
    """Types of holograms"""

    STATIC = "static"
    DYNAMIC = "dynamic"
    INTERACTIVE = "interactive"
    VOLUMETRIC = "volumetric"
    SURFACE = "surface"
    PARTICLE = "particle"


class RenderQuality(Enum):
    """Rendering quality levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    REALTIME = "realtime"


class InteractionMode(Enum):
    """Interaction modes"""

    GESTURE = "gesture"
    VOICE = "voice"
    GAZE = "gaze"
    TOUCH = "touch"
    BRAIN = "brain"
    HYBRID = "hybrid"


@dataclass
class Vector3D:
    """3D vector representation"""

    x: float
    y: float
    z: float

    def __add__(self, other):
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def magnitude(self):
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        mag = self.magnitude()
        if mag > 0:
            return Vector3D(self.x / mag, self.y / mag, self.z / mag)
        return Vector3D(0, 0, 0)

    def to_array(self):
        return np.array([self.x, self.y, self.z])


@dataclass
class Quaternion:
    """Quaternion for 3D rotations"""

    w: float
    x: float
    y: float
    z: float

    def normalize(self):
        norm = np.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)
        if norm > 0:
            return Quaternion(self.w / norm, self.x / norm, self.y / norm, self.z / norm)
        return Quaternion(1, 0, 0, 0)

    def to_matrix(self):
        """Convert to rotation matrix"""
        q = self.normalize()
        return np.array(
            [
                [
                    1 - 2 * (q.y**2 + q.z**2),
                    2 * (q.x * q.y - q.w * q.z),
                    2 * (q.x * q.z + q.w * q.y),
                ],
                [
                    2 * (q.x * q.y + q.w * q.z),
                    1 - 2 * (q.x**2 + q.z**2),
                    2 * (q.y * q.z - q.w * q.x),
                ],
                [
                    2 * (q.x * q.z - q.w * q.y),
                    2 * (q.y * q.z + q.w * q.x),
                    1 - 2 * (q.x**2 + q.y**2),
                ],
            ]
        )


@dataclass
class Transform3D:
    """3D transformation"""

    position: Vector3D
    rotation: Quaternion
    scale: Vector3D

    def __init__(self, position=None, rotation=None, scale=None):
        self.position = position or Vector3D(0, 0, 0)
        self.rotation = rotation or Quaternion(1, 0, 0, 0)
        self.scale = scale or Vector3D(1, 1, 1)

    def to_matrix(self):
        """Convert to transformation matrix"""
        R = self.rotation.to_matrix()
        S = np.diag([self.scale.x, self.scale.y, self.scale.z])
        T = np.eye(4)
        T[:3, :3] = R @ S
        T[:3, 3] = self.position.to_array()
        return T


@dataclass
class BoundingBox3D:
    """3D bounding box"""

    min_point: Vector3D
    max_point: Vector3D

    def contains(self, point: Vector3D) -> bool:
        return (
            self.min_point.x <= point.x <= self.max_point.x
            and self.min_point.y <= point.y <= self.max_point.y
            and self.min_point.z <= point.z <= self.max_point.z
        )

    def volume(self) -> float:
        size = self.max_point - self.min_point
        return size.x * size.y * size.z


class HolographicBase(ABC):
    """Base class for all holographic components"""

    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.id = f"{self.name}_{int(time.time() * 1000)}"
        self.enabled = True
        self.initialized = False
        self.logger = logging.getLogger(f"holographic.{self.name}")
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=4)

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the component"""
        pass

    @abstractmethod
    async def shutdown(self):
        """Shutdown the component"""
        pass

    async def update(self, delta_time: float):
        """Update component state"""
        pass

    def enable(self):
        """Enable the component"""
        with self._lock:
            self.enabled = True

    def disable(self):
        """Disable the component"""
        with self._lock:
            self.enabled = False

    def is_enabled(self) -> bool:
        """Check if component is enabled"""
        return self.enabled


class HolographicPerformanceMonitor:
    """Performance monitoring for holographic operations"""

    def __init__(self):
        self.metrics = {}
        self.start_times = {}
        self._lock = threading.Lock()

    def start_timer(self, operation: str):
        """Start timing an operation"""
        with self._lock:
            self.start_times[operation] = time.perf_counter()

    def end_timer(self, operation: str):
        """End timing and record metric"""
        with self._lock:
            if operation in self.start_times:
                duration = time.perf_counter() - self.start_times[operation]
                if operation not in self.metrics:
                    self.metrics[operation] = []
                self.metrics[operation].append(duration)
                del self.start_times[operation]
                return duration
        return 0.0

    def get_average_time(self, operation: str) -> float:
        """Get average time for operation"""
        with self._lock:
            if operation in self.metrics and self.metrics[operation]:
                return sum(self.metrics[operation]) / len(self.metrics[operation])
        return 0.0

    def get_fps(self, operation: str = "frame") -> float:
        """Get frames per second"""
        avg_time = self.get_average_time(operation)
        return 1.0 / avg_time if avg_time > 0 else 0.0

    def clear_metrics(self):
        """Clear all metrics"""
        with self._lock:
            self.metrics.clear()
            self.start_times.clear()


class SpatialHash:
    """Spatial hash for efficient 3D spatial queries"""

    def __init__(self, cell_size: float = 1.0):
        self.cell_size = cell_size
        self.grid = {}
        self._lock = threading.RLock()

    def _hash_position(self, position: Vector3D) -> Tuple[int, int, int]:
        """Hash position to grid cell"""
        return (
            int(position.x // self.cell_size),
            int(position.y // self.cell_size),
            int(position.z // self.cell_size),
        )

    def insert(self, obj_id: str, position: Vector3D, radius: float = 0.0):
        """Insert object into spatial hash"""
        with self._lock:
            # Insert into all cells that the object touches
            min_cell = self._hash_position(
                Vector3D(position.x - radius, position.y - radius, position.z - radius)
            )
            max_cell = self._hash_position(
                Vector3D(position.x + radius, position.y + radius, position.z + radius)
            )

            for x in range(min_cell[0], max_cell[0] + 1):
                for y in range(min_cell[1], max_cell[1] + 1):
                    for z in range(min_cell[2], max_cell[2] + 1):
                        cell = (x, y, z)
                        if cell not in self.grid:
                            self.grid[cell] = set()
                        self.grid[cell].add(obj_id)

    def remove(self, obj_id: str, position: Vector3D, radius: float = 0.0):
        """Remove object from spatial hash"""
        with self._lock:
            min_cell = self._hash_position(
                Vector3D(position.x - radius, position.y - radius, position.z - radius)
            )
            max_cell = self._hash_position(
                Vector3D(position.x + radius, position.y + radius, position.z + radius)
            )

            for x in range(min_cell[0], max_cell[0] + 1):
                for y in range(min_cell[1], max_cell[1] + 1):
                    for z in range(min_cell[2], max_cell[2] + 1):
                        cell = (x, y, z)
                        if cell in self.grid:
                            self.grid[cell].discard(obj_id)
                            if not self.grid[cell]:
                                del self.grid[cell]

    def query_radius(self, position: Vector3D, radius: float) -> set:
        """Query objects within radius"""
        with self._lock:
            result = set()
            min_cell = self._hash_position(
                Vector3D(position.x - radius, position.y - radius, position.z - radius)
            )
            max_cell = self._hash_position(
                Vector3D(position.x + radius, position.y + radius, position.z + radius)
            )

            for x in range(min_cell[0], max_cell[0] + 1):
                for y in range(min_cell[1], max_cell[1] + 1):
                    for z in range(min_cell[2], max_cell[2] + 1):
                        cell = (x, y, z)
                        if cell in self.grid:
                            result.update(self.grid[cell])

            return result


class HolographicException(Exception):
    """Base exception for holographic system"""

    pass


class InitializationError(HolographicException):
    """Raised when component initialization fails"""

    pass


class RenderingError(HolographicException):
    """Raised when rendering fails"""

    pass


class CalibrationError(HolographicException):
    """Raised when calibration fails"""

    pass


class GestureRecognitionError(HolographicException):
    """Raised when gesture recognition fails"""

    pass
