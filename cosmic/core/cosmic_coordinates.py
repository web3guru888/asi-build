"""
Cosmic Coordinate System

Advanced coordinate system for universe-scale positioning and navigation.
Handles multiple coordinate systems and transformations between them.
"""

import logging
import numpy as np
from typing import Tuple, Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import threading

logger = logging.getLogger(__name__)

class CoordinateSystem(Enum):
    """Supported coordinate systems"""
    CARTESIAN = "cartesian"           # (x, y, z, t)
    SPHERICAL = "spherical"          # (r, theta, phi, t)
    GALACTIC = "galactic"            # Galactic coordinates
    SUPERGALACTIC = "supergalactic"  # Supergalactic coordinates
    COMOVING = "comoving"            # Comoving coordinates (expanding universe)
    CONFORMAL = "conformal"          # Conformal time coordinates
    PLANCK_UNITS = "planck"          # Natural Planck units
    REDSHIFT = "redshift"            # Redshift-based distance

@dataclass
class CoordinateTransform:
    """Represents a coordinate transformation"""
    from_system: CoordinateSystem
    to_system: CoordinateSystem
    transformation_matrix: np.ndarray
    inverse_matrix: np.ndarray
    scale_factors: Optional[Tuple[float, float, float, float]] = None

@dataclass
class SpatialRegion:
    """Defines a region in space for cosmic operations"""
    region_id: str
    coordinate_system: CoordinateSystem
    center: Tuple[float, float, float, float]
    dimensions: Tuple[float, float, float]  # Size in each dimension
    shape: str = "box"  # box, sphere, cylinder
    properties: Optional[Dict[str, Any]] = None

class CosmicCoordinateSystem:
    """
    Advanced coordinate system for cosmic engineering
    
    Handles multiple coordinate systems, transformations between them,
    and provides utilities for universe-scale positioning.
    """
    
    def __init__(self):
        """Initialize cosmic coordinate system"""
        self.lock = threading.RLock()
        
        # Current primary coordinate system
        self.primary_system = CoordinateSystem.CARTESIAN
        
        # Transformation matrices between coordinate systems
        self.transforms: Dict[str, CoordinateTransform] = {}
        
        # Defined spatial regions
        self.spatial_regions: Dict[str, SpatialRegion] = {}
        
        # Physical constants for coordinate calculations
        self.c = 2.998e8  # m/s - speed of light
        self.H0 = 67.4    # km/s/Mpc - Hubble constant
        self.planck_length = 1.616e-35  # m
        self.planck_time = 5.391e-44    # s
        
        # Initialize standard transformations
        self._initialize_transformations()
        
        # Define standard cosmic regions
        self._define_standard_regions()
        
        logger.info("Cosmic Coordinate System initialized")
    
    def _initialize_transformations(self):
        """Initialize standard coordinate transformations"""
        # Cartesian <-> Spherical
        self._add_cartesian_spherical_transforms()
        
        # Planck units transformations
        self._add_planck_unit_transforms()
        
        # Cosmological coordinate transforms
        self._add_cosmological_transforms()
    
    def _add_cartesian_spherical_transforms(self):
        """Add Cartesian <-> Spherical coordinate transforms"""
        # Note: These are handled by special functions rather than matrices
        # due to the nonlinear nature of the transformation
        pass
    
    def _add_planck_unit_transforms(self):
        """Add transformations to/from Planck units"""
        # Planck unit scaling factors
        planck_scales = np.array([
            self.planck_length,  # x
            self.planck_length,  # y
            self.planck_length,  # z
            self.planck_time     # t
        ])
        
        # Create transformation matrices
        to_planck = np.diag(1.0 / planck_scales)
        from_planck = np.diag(planck_scales)
        
        transform_key = f"{CoordinateSystem.CARTESIAN.value}_to_{CoordinateSystem.PLANCK_UNITS.value}"
        self.transforms[transform_key] = CoordinateTransform(
            from_system=CoordinateSystem.CARTESIAN,
            to_system=CoordinateSystem.PLANCK_UNITS,
            transformation_matrix=to_planck,
            inverse_matrix=from_planck,
            scale_factors=tuple(planck_scales)
        )
    
    def _add_cosmological_transforms(self):
        """Add cosmological coordinate transformations"""
        # Comoving coordinate transformation (simplified)
        # In reality, this depends on the scale factor a(t)
        
        # For now, use identity transformation (flat space approximation)
        identity = np.eye(4)
        
        transform_key = f"{CoordinateSystem.CARTESIAN.value}_to_{CoordinateSystem.COMOVING.value}"
        self.transforms[transform_key] = CoordinateTransform(
            from_system=CoordinateSystem.CARTESIAN,
            to_system=CoordinateSystem.COMOVING,
            transformation_matrix=identity,
            inverse_matrix=identity
        )
    
    def _define_standard_regions(self):
        """Define standard cosmic regions"""
        # Observable Universe
        self.define_spatial_region(
            "observable_universe",
            CoordinateSystem.CARTESIAN,
            center=(0, 0, 0, 0),
            dimensions=(8.8e26, 8.8e26, 8.8e26),  # Observable universe diameter
            shape="sphere",
            properties={"description": "Observable universe"}
        )
        
        # Local Group
        self.define_spatial_region(
            "local_group",
            CoordinateSystem.GALACTIC,
            center=(0, 0, 0, 0),
            dimensions=(3e22, 3e22, 3e22),  # ~10 million light years
            shape="sphere",
            properties={"description": "Local Group of galaxies"}
        )
        
        # Solar System
        self.define_spatial_region(
            "solar_system",
            CoordinateSystem.CARTESIAN,
            center=(0, 0, 0, 0),
            dimensions=(1.8e13, 1.8e13, 1.8e13),  # ~120 AU diameter
            shape="sphere",
            properties={"description": "Solar System"}
        )
        
        # Planck Scale Region
        self.define_spatial_region(
            "planck_scale",
            CoordinateSystem.PLANCK_UNITS,
            center=(0, 0, 0, 0),
            dimensions=(10, 10, 10),  # 10 Planck lengths
            shape="box",
            properties={"description": "Planck scale physics region"}
        )
    
    def convert_coordinates(self,
                          coordinates: Tuple[float, float, float, float],
                          from_system: CoordinateSystem,
                          to_system: CoordinateSystem) -> Tuple[float, float, float, float]:
        """
        Convert coordinates between different systems
        
        Args:
            coordinates: (x, y, z, t) coordinates
            from_system: Source coordinate system
            to_system: Target coordinate system
            
        Returns:
            Converted coordinates
        """
        with self.lock:
            if from_system == to_system:
                return coordinates
            
            # Handle special non-linear transformations
            if from_system == CoordinateSystem.CARTESIAN and to_system == CoordinateSystem.SPHERICAL:
                return self._cartesian_to_spherical(coordinates)
            elif from_system == CoordinateSystem.SPHERICAL and to_system == CoordinateSystem.CARTESIAN:
                return self._spherical_to_cartesian(coordinates)
            
            # Handle matrix-based transformations
            transform_key = f"{from_system.value}_to_{to_system.value}"
            
            if transform_key in self.transforms:
                transform = self.transforms[transform_key]
                coord_vector = np.array(coordinates)
                transformed = transform.transformation_matrix @ coord_vector
                return tuple(transformed)
            
            # Try inverse transformation
            inverse_key = f"{to_system.value}_to_{from_system.value}"
            if inverse_key in self.transforms:
                transform = self.transforms[inverse_key]
                coord_vector = np.array(coordinates)
                transformed = transform.inverse_matrix @ coord_vector
                return tuple(transformed)
            
            # No direct transformation available
            logger.warning(f"No transformation available from {from_system} to {to_system}")
            return coordinates
    
    def _cartesian_to_spherical(self, coordinates: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        """Convert Cartesian to spherical coordinates"""
        x, y, z, t = coordinates
        
        r = np.sqrt(x**2 + y**2 + z**2)
        theta = np.arccos(z / r) if r > 0 else 0
        phi = np.arctan2(y, x)
        
        return (r, theta, phi, t)
    
    def _spherical_to_cartesian(self, coordinates: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        """Convert spherical to Cartesian coordinates"""
        r, theta, phi, t = coordinates
        
        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)
        
        return (x, y, z, t)
    
    def calculate_distance(self,
                          point1: Tuple[float, float, float, float],
                          point2: Tuple[float, float, float, float],
                          coordinate_system: CoordinateSystem = CoordinateSystem.CARTESIAN,
                          metric: str = "euclidean") -> float:
        """
        Calculate distance between two points
        
        Args:
            point1: First point coordinates
            point2: Second point coordinates  
            coordinate_system: Coordinate system being used
            metric: Distance metric (euclidean, minkowski, proper)
            
        Returns:
            Distance between points
        """
        with self.lock:
            # Convert to Cartesian if needed
            if coordinate_system != CoordinateSystem.CARTESIAN:
                p1_cart = self.convert_coordinates(point1, coordinate_system, CoordinateSystem.CARTESIAN)
                p2_cart = self.convert_coordinates(point2, coordinate_system, CoordinateSystem.CARTESIAN)
            else:
                p1_cart = point1
                p2_cart = point2
            
            x1, y1, z1, t1 = p1_cart
            x2, y2, z2, t2 = p2_cart
            
            if metric == "euclidean":
                # Spatial distance only
                return np.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
            
            elif metric == "minkowski":
                # Spacetime interval with c=1
                c = self.c
                ds2 = -c**2 * (t2 - t1)**2 + (x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2
                return np.sqrt(abs(ds2))
            
            elif metric == "proper":
                # Proper distance in expanding universe
                spatial_distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
                
                # Apply scale factor correction (simplified)
                # In reality, this requires integration over cosmic time
                avg_time = (t1 + t2) / 2
                scale_factor = self._calculate_scale_factor(avg_time)
                
                return spatial_distance / scale_factor
            
            else:
                raise ValueError(f"Unknown metric: {metric}")
    
    def _calculate_scale_factor(self, cosmic_time: float) -> float:
        """Calculate cosmological scale factor at given time"""
        # Simplified scale factor calculation
        # a(t) = a0 * (t/t0)^(2/3) for matter-dominated universe
        # This is a gross oversimplification
        
        t0 = 4.35e17  # Current age of universe in seconds
        if cosmic_time <= 0:
            return 1e-10  # Very early universe
        
        return (cosmic_time / t0)**(2/3)
    
    def define_spatial_region(self,
                            region_id: str,
                            coordinate_system: CoordinateSystem,
                            center: Tuple[float, float, float, float],
                            dimensions: Tuple[float, float, float],
                            shape: str = "box",
                            properties: Optional[Dict[str, Any]] = None) -> bool:
        """
        Define a spatial region for cosmic operations
        
        Args:
            region_id: Unique identifier for region
            coordinate_system: Coordinate system for region
            center: Center coordinates (x, y, z, t)
            dimensions: Size in each spatial dimension
            shape: Shape of region (box, sphere, cylinder)
            properties: Additional properties
            
        Returns:
            True if successful
        """
        with self.lock:
            if region_id in self.spatial_regions:
                logger.warning(f"Spatial region {region_id} already exists")
                return False
            
            region = SpatialRegion(
                region_id=region_id,
                coordinate_system=coordinate_system,
                center=center,
                dimensions=dimensions,
                shape=shape,
                properties=properties or {}
            )
            
            self.spatial_regions[region_id] = region
            
            logger.info(f"Defined spatial region {region_id}")
            logger.info(f"Center: {center}, Dimensions: {dimensions}")
            
            return True
    
    def point_in_region(self,
                       point: Tuple[float, float, float, float],
                       region_id: str) -> bool:
        """
        Check if a point is within a defined spatial region
        
        Args:
            point: Point coordinates
            region_id: ID of spatial region
            
        Returns:
            True if point is in region
        """
        with self.lock:
            if region_id not in self.spatial_regions:
                logger.error(f"Spatial region {region_id} not found")
                return False
            
            region = self.spatial_regions[region_id]
            
            # Convert point to region's coordinate system
            point_in_system = self.convert_coordinates(
                point, self.primary_system, region.coordinate_system
            )
            
            px, py, pz, pt = point_in_system
            cx, cy, cz, ct = region.center
            dx, dy, dz = region.dimensions
            
            if region.shape == "box":
                return (abs(px - cx) <= dx/2 and 
                       abs(py - cy) <= dy/2 and 
                       abs(pz - cz) <= dz/2)
            
            elif region.shape == "sphere":
                radius = dx / 2  # Use first dimension as radius
                distance = np.sqrt((px - cx)**2 + (py - cy)**2 + (pz - cz)**2)
                return distance <= radius
            
            elif region.shape == "cylinder":
                # Cylinder along z-axis
                radial_distance = np.sqrt((px - cx)**2 + (py - cy)**2)
                height_check = abs(pz - cz) <= dz/2
                radius_check = radial_distance <= dx/2  # Use x-dimension as radius
                return height_check and radius_check
            
            else:
                logger.warning(f"Unknown region shape: {region.shape}")
                return False
    
    def calculate_redshift_distance(self, redshift: float) -> float:
        """
        Calculate distance based on cosmological redshift
        
        Args:
            redshift: Cosmological redshift z
            
        Returns:
            Distance in meters
        """
        # Simplified calculation - in reality, this requires integration
        # over the Hubble parameter H(z)
        
        c = self.c
        H0_si = self.H0 * 1000 / (3.086e22)  # Convert to SI units
        
        # Approximate for small z
        if redshift < 0.1:
            return c * redshift / H0_si
        
        # More accurate for larger z (still simplified)
        # Assumes flat universe with Omega_m = 0.3, Omega_Lambda = 0.7
        omega_m = 0.3
        omega_lambda = 0.7
        
        # Integral approximation
        def integrand(z):
            return 1.0 / np.sqrt(omega_m * (1 + z)**3 + omega_lambda)
        
        # Simple numerical integration
        z_values = np.linspace(0, redshift, 1000)
        dz = z_values[1] - z_values[0]
        integral = np.sum([integrand(z) for z in z_values]) * dz
        
        distance = (c / H0_si) * integral
        return distance
    
    def get_coordinate_system_info(self, system: CoordinateSystem) -> Dict[str, Any]:
        """Get information about a coordinate system"""
        info = {
            "name": system.value,
            "description": "",
            "units": "",
            "typical_scale": ""
        }
        
        if system == CoordinateSystem.CARTESIAN:
            info.update({
                "description": "Standard Cartesian coordinates (x, y, z, t)",
                "units": "meters, seconds",
                "typical_scale": "Any scale"
            })
        elif system == CoordinateSystem.SPHERICAL:
            info.update({
                "description": "Spherical coordinates (r, theta, phi, t)",
                "units": "meters, radians, seconds",
                "typical_scale": "Stellar to galactic"
            })
        elif system == CoordinateSystem.PLANCK_UNITS:
            info.update({
                "description": "Natural Planck units",
                "units": "Planck lengths, Planck times",
                "typical_scale": "Quantum gravity scale"
            })
        elif system == CoordinateSystem.COMOVING:
            info.update({
                "description": "Comoving coordinates (expanding universe)",
                "units": "Comoving distance, conformal time",
                "typical_scale": "Cosmological"
            })
        
        return info
    
    def get_region_info(self, region_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a spatial region"""
        with self.lock:
            if region_id not in self.spatial_regions:
                return None
            
            region = self.spatial_regions[region_id]
            
            # Calculate region volume
            dx, dy, dz = region.dimensions
            if region.shape == "box":
                volume = dx * dy * dz
            elif region.shape == "sphere":
                radius = dx / 2
                volume = (4/3) * np.pi * radius**3
            elif region.shape == "cylinder":
                radius = dx / 2
                height = dz
                volume = np.pi * radius**2 * height
            else:
                volume = 0
            
            return {
                "region_id": region.region_id,
                "coordinate_system": region.coordinate_system.value,
                "center": region.center,
                "dimensions": region.dimensions,
                "shape": region.shape,
                "volume": volume,
                "properties": region.properties
            }
    
    def list_regions(self) -> List[str]:
        """List all defined spatial regions"""
        with self.lock:
            return list(self.spatial_regions.keys())
    
    def set_primary_system(self, system: CoordinateSystem):
        """Set the primary coordinate system"""
        with self.lock:
            self.primary_system = system
            logger.info(f"Primary coordinate system set to {system.value}")
    
    def emergency_shutdown(self):
        """Emergency shutdown of coordinate system"""
        with self.lock:
            logger.critical("Cosmic Coordinate System emergency shutdown")
            # Reset to standard systems
            self.primary_system = CoordinateSystem.CARTESIAN
    
    def reset_to_baseline(self):
        """Reset coordinate system to baseline"""
        with self.lock:
            logger.info("Resetting Cosmic Coordinate System to baseline")
            self.primary_system = CoordinateSystem.CARTESIAN
            # Keep standard regions but clear any custom ones
            standard_regions = ["observable_universe", "local_group", "solar_system", "planck_scale"]
            custom_regions = [rid for rid in self.spatial_regions.keys() if rid not in standard_regions]
            for rid in custom_regions:
                del self.spatial_regions[rid]
            
            logger.info("Cosmic Coordinate System reset to baseline")