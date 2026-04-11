"""
Dimensional Coordinate System
============================

Manages dimensional coordinates for multiverse navigation,
providing precise positioning across parallel universes and dimensions.
"""

import numpy as np
import logging
import math
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import uuid
import time


@dataclass
class DimensionalCoordinate:
    """
    Represents a coordinate in multidimensional space.
    
    Uses extended spacetime coordinates (x, y, z, t) plus additional
    dimensional coordinates (w, v, u) for higher-dimensional navigation.
    """
    
    # Spatial coordinates (3D space)
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    # Temporal coordinate
    t: float = field(default_factory=time.time)
    
    # Extra-dimensional coordinates
    w: float = 0.0  # 4th spatial dimension
    v: float = 0.0  # 5th dimension (often probability/quantum)
    u: float = 0.0  # 6th dimension (consciousness/information)
    
    # Quantum properties
    uncertainty: float = 0.0  # Heisenberg uncertainty
    probability: float = 1.0  # Probability of existence at this coordinate
    coherence: float = 1.0    # Quantum coherence factor
    
    # Metadata
    coordinate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    universe_id: Optional[str] = None
    reference_frame: str = "absolute"
    coordinate_system: str = "cartesian"
    precision: float = 1e-12
    
    def __post_init__(self):
        """Initialize coordinate with validation."""
        # Ensure probability is valid
        self.probability = max(0.0, min(1.0, self.probability))
        
        # Ensure coherence is valid
        self.coherence = max(0.0, min(1.0, self.coherence))
        
        # Ensure uncertainty is non-negative
        self.uncertainty = max(0.0, self.uncertainty)
    
    def to_array(self) -> np.ndarray:
        """Convert coordinate to numpy array."""
        return np.array([self.x, self.y, self.z, self.t, self.w, self.v, self.u])
    
    def to_spatial_array(self) -> np.ndarray:
        """Get spatial coordinates only (x, y, z)."""
        return np.array([self.x, self.y, self.z])
    
    def to_spacetime_array(self) -> np.ndarray:
        """Get spacetime coordinates (x, y, z, t)."""
        return np.array([self.x, self.y, self.z, self.t])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert coordinate to dictionary."""
        return {
            'coordinate_id': self.coordinate_id,
            'x': self.x, 'y': self.y, 'z': self.z, 't': self.t,
            'w': self.w, 'v': self.v, 'u': self.u,
            'uncertainty': self.uncertainty,
            'probability': self.probability,
            'coherence': self.coherence,
            'universe_id': self.universe_id,
            'reference_frame': self.reference_frame,
            'coordinate_system': self.coordinate_system
        }
    
    @classmethod
    def from_array(cls, array: np.ndarray, **kwargs) -> 'DimensionalCoordinate':
        """Create coordinate from numpy array."""
        if len(array) < 3:
            raise ValueError("Array must have at least 3 elements (x, y, z)")
        
        coord = cls(
            x=float(array[0]),
            y=float(array[1]),
            z=float(array[2]),
            **kwargs
        )
        
        if len(array) > 3:
            coord.t = float(array[3])
        if len(array) > 4:
            coord.w = float(array[4])
        if len(array) > 5:
            coord.v = float(array[5])
        if len(array) > 6:
            coord.u = float(array[6])
        
        return coord
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DimensionalCoordinate':
        """Create coordinate from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def distance_to(self, other: 'DimensionalCoordinate') -> float:
        """
        Calculate distance to another coordinate.
        
        Uses weighted Euclidean distance across all dimensions.
        """
        if not isinstance(other, DimensionalCoordinate):
            raise TypeError("Can only calculate distance to another DimensionalCoordinate")
        
        # Spatial distance (3D)
        spatial_dist = math.sqrt(
            (self.x - other.x)**2 + 
            (self.y - other.y)**2 + 
            (self.z - other.z)**2
        )
        
        # Temporal distance (scaled)
        temporal_dist = abs(self.t - other.t) * 1e-6  # Scale down time
        
        # Extra-dimensional distances
        w_dist = abs(self.w - other.w)
        v_dist = abs(self.v - other.v) * 0.1  # Probability dimension weight
        u_dist = abs(self.u - other.u) * 0.1  # Consciousness dimension weight
        
        # Combined distance
        total_distance = math.sqrt(
            spatial_dist**2 + temporal_dist**2 + 
            w_dist**2 + v_dist**2 + u_dist**2
        )
        
        return total_distance
    
    def spatial_distance_to(self, other: 'DimensionalCoordinate') -> float:
        """Calculate spatial distance only (x, y, z)."""
        return math.sqrt(
            (self.x - other.x)**2 + 
            (self.y - other.y)**2 + 
            (self.z - other.z)**2
        )
    
    def temporal_distance_to(self, other: 'DimensionalCoordinate') -> float:
        """Calculate temporal distance only."""
        return abs(self.t - other.t)
    
    def dimensional_distance_to(self, other: 'DimensionalCoordinate') -> float:
        """Calculate extra-dimensional distance (w, v, u)."""
        return math.sqrt(
            (self.w - other.w)**2 + 
            (self.v - other.v)**2 + 
            (self.u - other.u)**2
        )
    
    def add(self, other: Union['DimensionalCoordinate', np.ndarray, List[float]]) -> 'DimensionalCoordinate':
        """Add another coordinate or vector to this coordinate."""
        if isinstance(other, DimensionalCoordinate):
            return DimensionalCoordinate(
                x=self.x + other.x,
                y=self.y + other.y,
                z=self.z + other.z,
                t=self.t + other.t,
                w=self.w + other.w,
                v=self.v + other.v,
                u=self.u + other.u,
                uncertainty=math.sqrt(self.uncertainty**2 + other.uncertainty**2),
                probability=self.probability * other.probability,
                coherence=self.coherence * other.coherence,
                universe_id=self.universe_id,
                reference_frame=self.reference_frame
            )
        elif isinstance(other, (np.ndarray, list)):
            other_array = np.array(other)
            self_array = self.to_array()
            
            # Pad shorter array with zeros
            max_len = max(len(self_array), len(other_array))
            self_padded = np.pad(self_array, (0, max_len - len(self_array)))
            other_padded = np.pad(other_array, (0, max_len - len(other_array)))
            
            result_array = self_padded + other_padded
            return DimensionalCoordinate.from_array(
                result_array,
                uncertainty=self.uncertainty,
                probability=self.probability,
                coherence=self.coherence,
                universe_id=self.universe_id,
                reference_frame=self.reference_frame
            )
        else:
            raise TypeError("Can only add DimensionalCoordinate, array, or list")
    
    def subtract(self, other: 'DimensionalCoordinate') -> 'DimensionalCoordinate':
        """Subtract another coordinate from this coordinate."""
        if not isinstance(other, DimensionalCoordinate):
            raise TypeError("Can only subtract DimensionalCoordinate")
        
        return DimensionalCoordinate(
            x=self.x - other.x,
            y=self.y - other.y,
            z=self.z - other.z,
            t=self.t - other.t,
            w=self.w - other.w,
            v=self.v - other.v,
            u=self.u - other.u,
            uncertainty=math.sqrt(self.uncertainty**2 + other.uncertainty**2),
            probability=self.probability,  # Keep original probability
            coherence=min(self.coherence, other.coherence),
            universe_id=self.universe_id,
            reference_frame=self.reference_frame
        )
    
    def scale(self, factor: float) -> 'DimensionalCoordinate':
        """Scale coordinate by a factor."""
        return DimensionalCoordinate(
            x=self.x * factor,
            y=self.y * factor,
            z=self.z * factor,
            t=self.t * factor,
            w=self.w * factor,
            v=self.v * factor,
            u=self.u * factor,
            uncertainty=self.uncertainty * abs(factor),
            probability=self.probability,
            coherence=self.coherence,
            universe_id=self.universe_id,
            reference_frame=self.reference_frame
        )
    
    def normalize(self) -> 'DimensionalCoordinate':
        """Normalize coordinate to unit magnitude."""
        magnitude = self.magnitude()
        if magnitude == 0:
            return self.copy()
        
        return self.scale(1.0 / magnitude)
    
    def magnitude(self) -> float:
        """Calculate magnitude of coordinate vector."""
        return math.sqrt(
            self.x**2 + self.y**2 + self.z**2 + 
            self.w**2 + self.v**2 + self.u**2
        )
    
    def copy(self) -> 'DimensionalCoordinate':
        """Create a copy of this coordinate."""
        return DimensionalCoordinate(
            x=self.x, y=self.y, z=self.z, t=self.t,
            w=self.w, v=self.v, u=self.u,
            uncertainty=self.uncertainty,
            probability=self.probability,
            coherence=self.coherence,
            universe_id=self.universe_id,
            reference_frame=self.reference_frame,
            coordinate_system=self.coordinate_system,
            precision=self.precision
        )
    
    def transform_to_frame(self, target_frame: str) -> 'DimensionalCoordinate':
        """Transform coordinate to different reference frame."""
        if target_frame == self.reference_frame:
            return self.copy()
        
        # Simplified frame transformations
        if self.reference_frame == "absolute" and target_frame == "relative":
            # Convert to relative coordinates (center at origin)
            return self.copy()
        elif self.reference_frame == "relative" and target_frame == "absolute":
            # Convert to absolute coordinates
            return self.copy()
        else:
            # For other transformations, return copy for now
            # In a full implementation, this would include Lorentz transformations,
            # coordinate system rotations, etc.
            transformed = self.copy()
            transformed.reference_frame = target_frame
            return transformed
    
    def apply_uncertainty(self, noise_level: float = 0.1) -> 'DimensionalCoordinate':
        """Apply quantum uncertainty to coordinate."""
        # Generate random noise based on uncertainty principle
        noise = np.random.normal(0, noise_level, 7)
        
        return DimensionalCoordinate(
            x=self.x + noise[0] * self.uncertainty,
            y=self.y + noise[1] * self.uncertainty,
            z=self.z + noise[2] * self.uncertainty,
            t=self.t + noise[3] * self.uncertainty,
            w=self.w + noise[4] * self.uncertainty,
            v=self.v + noise[5] * self.uncertainty,
            u=self.u + noise[6] * self.uncertainty,
            uncertainty=self.uncertainty * (1.0 + noise_level),
            probability=self.probability * math.exp(-noise_level),
            coherence=self.coherence * (1.0 - noise_level * 0.1),
            universe_id=self.universe_id,
            reference_frame=self.reference_frame
        )
    
    def create_branch(self, deviation: float = 0.1) -> 'DimensionalCoordinate':
        """Create a branched coordinate with quantum deviation."""
        # Create quantum variations
        variations = np.random.normal(0, deviation, 7)
        
        return DimensionalCoordinate(
            x=self.x + variations[0],
            y=self.y + variations[1],
            z=self.z + variations[2],
            t=self.t,  # Keep same time
            w=self.w + variations[4],
            v=self.v + variations[5],
            u=self.u + variations[6],
            uncertainty=self.uncertainty * (1.0 + deviation),
            probability=self.probability * 0.5,  # Split probability
            coherence=self.coherence * (1.0 - deviation),
            universe_id=None,  # New universe
            reference_frame=self.reference_frame
        )
    
    def interpolate_to(self, other: 'DimensionalCoordinate', t: float) -> 'DimensionalCoordinate':
        """
        Interpolate between this coordinate and another.
        
        Args:
            other: Target coordinate
            t: Interpolation parameter (0.0 = self, 1.0 = other)
        """
        t = max(0.0, min(1.0, t))  # Clamp to [0, 1]
        
        return DimensionalCoordinate(
            x=self.x + t * (other.x - self.x),
            y=self.y + t * (other.y - self.y),
            z=self.z + t * (other.z - self.z),
            t=self.t + t * (other.t - self.t),
            w=self.w + t * (other.w - self.w),
            v=self.v + t * (other.v - self.v),
            u=self.u + t * (other.u - self.u),
            uncertainty=self.uncertainty + t * (other.uncertainty - self.uncertainty),
            probability=self.probability + t * (other.probability - self.probability),
            coherence=self.coherence + t * (other.coherence - self.coherence),
            universe_id=self.universe_id if t < 0.5 else other.universe_id,
            reference_frame=self.reference_frame
        )
    
    def is_valid(self) -> bool:
        """Check if coordinate is valid."""
        # Check for NaN or infinite values
        coords = [self.x, self.y, self.z, self.t, self.w, self.v, self.u]
        if any(math.isnan(c) or math.isinf(c) for c in coords):
            return False
        
        # Check probability bounds
        if not (0.0 <= self.probability <= 1.0):
            return False
        
        # Check coherence bounds
        if not (0.0 <= self.coherence <= 1.0):
            return False
        
        # Check uncertainty
        if self.uncertainty < 0:
            return False
        
        return True
    
    def to_spherical(self) -> Tuple[float, float, float]:
        """Convert spatial coordinates to spherical (r, theta, phi)."""
        r = math.sqrt(self.x**2 + self.y**2 + self.z**2)
        
        if r == 0:
            return (0.0, 0.0, 0.0)
        
        theta = math.acos(self.z / r)  # Polar angle
        phi = math.atan2(self.y, self.x)  # Azimuthal angle
        
        return (r, theta, phi)
    
    def to_cylindrical(self) -> Tuple[float, float, float]:
        """Convert spatial coordinates to cylindrical (rho, phi, z)."""
        rho = math.sqrt(self.x**2 + self.y**2)
        phi = math.atan2(self.y, self.x)
        
        return (rho, phi, self.z)
    
    def __add__(self, other):
        """Addition operator."""
        return self.add(other)
    
    def __sub__(self, other):
        """Subtraction operator."""
        return self.subtract(other)
    
    def __mul__(self, factor):
        """Multiplication operator."""
        if isinstance(factor, (int, float)):
            return self.scale(factor)
        else:
            raise TypeError("Can only multiply by scalar")
    
    def __rmul__(self, factor):
        """Reverse multiplication operator."""
        return self.__mul__(factor)
    
    def __eq__(self, other):
        """Equality operator with precision tolerance."""
        if not isinstance(other, DimensionalCoordinate):
            return False
        
        tolerance = min(self.precision, other.precision)
        
        return (
            abs(self.x - other.x) < tolerance and
            abs(self.y - other.y) < tolerance and
            abs(self.z - other.z) < tolerance and
            abs(self.t - other.t) < tolerance and
            abs(self.w - other.w) < tolerance and
            abs(self.v - other.v) < tolerance and
            abs(self.u - other.u) < tolerance
        )
    
    def __str__(self) -> str:
        """String representation."""
        return (f"DimensionalCoordinate("
                f"x={self.x:.3f}, y={self.y:.3f}, z={self.z:.3f}, "
                f"t={self.t:.3f}, w={self.w:.3f}, v={self.v:.3f}, u={self.u:.3f}, "
                f"p={self.probability:.3f})")
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (f"DimensionalCoordinate(id={self.coordinate_id[:8]}..., "
                f"coords=({self.x:.3f}, {self.y:.3f}, {self.z:.3f}, {self.t:.3f}, "
                f"{self.w:.3f}, {self.v:.3f}, {self.u:.3f}), "
                f"uncertainty={self.uncertainty:.6f}, "
                f"probability={self.probability:.3f}, "
                f"universe={self.universe_id})")


class DimensionalSpace:
    """
    Represents a dimensional space containing multiple coordinates.
    
    Provides utilities for coordinate collections, transformations,
    and spatial analysis operations.
    """
    
    def __init__(self, coordinates: Optional[List[DimensionalCoordinate]] = None):
        """Initialize dimensional space."""
        self.coordinates = coordinates or []
        self.space_id = str(uuid.uuid4())
        self.reference_frame = "absolute"
        self.logger = logging.getLogger("multiverse.dimensional_space")
    
    def add_coordinate(self, coordinate: DimensionalCoordinate):
        """Add a coordinate to the space."""
        if not coordinate.is_valid():
            raise ValueError("Invalid coordinate")
        
        self.coordinates.append(coordinate)
    
    def remove_coordinate(self, coordinate_id: str) -> bool:
        """Remove a coordinate by ID."""
        for i, coord in enumerate(self.coordinates):
            if coord.coordinate_id == coordinate_id:
                del self.coordinates[i]
                return True
        return False
    
    def get_coordinate(self, coordinate_id: str) -> Optional[DimensionalCoordinate]:
        """Get a coordinate by ID."""
        for coord in self.coordinates:
            if coord.coordinate_id == coordinate_id:
                return coord
        return None
    
    def find_nearest_coordinate(self, target: DimensionalCoordinate) -> Optional[DimensionalCoordinate]:
        """Find the nearest coordinate to a target."""
        if not self.coordinates:
            return None
        
        nearest = self.coordinates[0]
        min_distance = target.distance_to(nearest)
        
        for coord in self.coordinates[1:]:
            distance = target.distance_to(coord)
            if distance < min_distance:
                min_distance = distance
                nearest = coord
        
        return nearest
    
    def find_coordinates_in_radius(self, center: DimensionalCoordinate, 
                                  radius: float) -> List[DimensionalCoordinate]:
        """Find all coordinates within a radius of center."""
        return [
            coord for coord in self.coordinates
            if center.distance_to(coord) <= radius
        ]
    
    def calculate_center_of_mass(self) -> Optional[DimensionalCoordinate]:
        """Calculate center of mass of all coordinates."""
        if not self.coordinates:
            return None
        
        # Weight by probability
        total_weight = sum(coord.probability for coord in self.coordinates)
        if total_weight == 0:
            return None
        
        weighted_coords = np.zeros(7)
        
        for coord in self.coordinates:
            coord_array = coord.to_array()
            weighted_coords += coord_array * coord.probability
        
        weighted_coords /= total_weight
        
        center = DimensionalCoordinate.from_array(
            weighted_coords,
            reference_frame=self.reference_frame
        )
        
        return center
    
    def calculate_bounding_box(self) -> Optional[Tuple[DimensionalCoordinate, DimensionalCoordinate]]:
        """Calculate bounding box of all coordinates."""
        if not self.coordinates:
            return None
        
        coords_array = np.array([coord.to_array() for coord in self.coordinates])
        
        min_coords = np.min(coords_array, axis=0)
        max_coords = np.max(coords_array, axis=0)
        
        min_coord = DimensionalCoordinate.from_array(
            min_coords, reference_frame=self.reference_frame
        )
        max_coord = DimensionalCoordinate.from_array(
            max_coords, reference_frame=self.reference_frame
        )
        
        return (min_coord, max_coord)
    
    def transform_all(self, target_frame: str):
        """Transform all coordinates to target reference frame."""
        for coord in self.coordinates:
            transformed = coord.transform_to_frame(target_frame)
            # Update in place
            coord.x, coord.y, coord.z = transformed.x, transformed.y, transformed.z
            coord.t, coord.w, coord.v, coord.u = transformed.t, transformed.w, transformed.v, transformed.u
            coord.reference_frame = target_frame
        
        self.reference_frame = target_frame
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the dimensional space."""
        if not self.coordinates:
            return {'coordinate_count': 0}
        
        coords_array = np.array([coord.to_array() for coord in self.coordinates])
        probabilities = [coord.probability for coord in self.coordinates]
        coherences = [coord.coherence for coord in self.coordinates]
        uncertainties = [coord.uncertainty for coord in self.coordinates]
        
        return {
            'coordinate_count': len(self.coordinates),
            'space_id': self.space_id,
            'reference_frame': self.reference_frame,
            'coordinate_means': np.mean(coords_array, axis=0).tolist(),
            'coordinate_stds': np.std(coords_array, axis=0).tolist(),
            'probability_stats': {
                'mean': np.mean(probabilities),
                'std': np.std(probabilities),
                'min': np.min(probabilities),
                'max': np.max(probabilities)
            },
            'coherence_stats': {
                'mean': np.mean(coherences),
                'std': np.std(coherences),
                'min': np.min(coherences),
                'max': np.max(coherences)
            },
            'uncertainty_stats': {
                'mean': np.mean(uncertainties),
                'std': np.std(uncertainties),
                'min': np.min(uncertainties),
                'max': np.max(uncertainties)
            }
        }
    
    def __len__(self) -> int:
        """Number of coordinates in space."""
        return len(self.coordinates)
    
    def __iter__(self):
        """Iterate over coordinates."""
        return iter(self.coordinates)
    
    def __getitem__(self, index: int) -> DimensionalCoordinate:
        """Get coordinate by index."""
        return self.coordinates[index]