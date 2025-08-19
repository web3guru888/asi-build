"""
Spatial mathematics utilities for holographic operations
"""

import numpy as np
import math
from typing import Tuple, List, Optional, Union
from .base import Vector3D, Quaternion, Transform3D

class SpatialMath:
    """Spatial mathematics utilities for 3D holographic operations"""
    
    @staticmethod
    def distance_3d(p1: Vector3D, p2: Vector3D) -> float:
        """Calculate distance between two 3D points"""
        return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2 + (p2.z - p1.z)**2)
    
    @staticmethod
    def dot_product(v1: Vector3D, v2: Vector3D) -> float:
        """Calculate dot product of two vectors"""
        return v1.x * v2.x + v1.y * v2.y + v1.z * v2.z
    
    @staticmethod
    def cross_product(v1: Vector3D, v2: Vector3D) -> Vector3D:
        """Calculate cross product of two vectors"""
        return Vector3D(
            v1.y * v2.z - v1.z * v2.y,
            v1.z * v2.x - v1.x * v2.z,
            v1.x * v2.y - v1.y * v2.x
        )
    
    @staticmethod
    def angle_between_vectors(v1: Vector3D, v2: Vector3D) -> float:
        """Calculate angle between two vectors in radians"""
        dot = SpatialMath.dot_product(v1.normalize(), v2.normalize())
        # Clamp to avoid numerical errors
        dot = max(-1.0, min(1.0, dot))
        return math.acos(dot)
    
    @staticmethod
    def project_vector(v: Vector3D, onto: Vector3D) -> Vector3D:
        """Project vector v onto vector 'onto'"""
        onto_normalized = onto.normalize()
        projection_length = SpatialMath.dot_product(v, onto_normalized)
        return onto_normalized * projection_length
    
    @staticmethod
    def reflect_vector(v: Vector3D, normal: Vector3D) -> Vector3D:
        """Reflect vector v across surface with given normal"""
        normal_normalized = normal.normalize()
        return v - normal_normalized * (2 * SpatialMath.dot_product(v, normal_normalized))
    
    @staticmethod
    def lerp_vector(v1: Vector3D, v2: Vector3D, t: float) -> Vector3D:
        """Linear interpolation between two vectors"""
        t = max(0.0, min(1.0, t))  # Clamp t to [0, 1]
        return v1 + (v2 - v1) * t
    
    @staticmethod
    def slerp_quaternion(q1: Quaternion, q2: Quaternion, t: float) -> Quaternion:
        """Spherical linear interpolation between quaternions"""
        t = max(0.0, min(1.0, t))
        
        # Normalize quaternions
        q1 = q1.normalize()
        q2 = q2.normalize()
        
        # Calculate dot product
        dot = q1.w * q2.w + q1.x * q2.x + q1.y * q2.y + q1.z * q2.z
        
        # If dot product is negative, slerp won't take the shorter path
        if dot < 0.0:
            q2 = Quaternion(-q2.w, -q2.x, -q2.y, -q2.z)
            dot = -dot
        
        # If the inputs are too close for comfort, linearly interpolate
        if dot > 0.9995:
            result = Quaternion(
                q1.w + t * (q2.w - q1.w),
                q1.x + t * (q2.x - q1.x),
                q1.y + t * (q2.y - q1.y),
                q1.z + t * (q2.z - q1.z)
            )
            return result.normalize()
        
        # Calculate the angle between the quaternions
        theta_0 = math.acos(abs(dot))
        sin_theta_0 = math.sin(theta_0)
        theta = theta_0 * t
        sin_theta = math.sin(theta)
        
        s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
        s1 = sin_theta / sin_theta_0
        
        return Quaternion(
            s0 * q1.w + s1 * q2.w,
            s0 * q1.x + s1 * q2.x,
            s0 * q1.y + s1 * q2.y,
            s0 * q1.z + s1 * q2.z
        )
    
    @staticmethod
    def euler_to_quaternion(pitch: float, yaw: float, roll: float) -> Quaternion:
        """Convert Euler angles (in radians) to quaternion"""
        # Abbreviations for the various angular functions
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        
        return Quaternion(
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy
        )
    
    @staticmethod
    def quaternion_to_euler(q: Quaternion) -> Tuple[float, float, float]:
        """Convert quaternion to Euler angles (pitch, yaw, roll) in radians"""
        q = q.normalize()
        
        # Roll (x-axis rotation)
        sinr_cosp = 2 * (q.w * q.x + q.y * q.z)
        cosr_cosp = 1 - 2 * (q.x * q.x + q.y * q.y)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        
        # Pitch (y-axis rotation)
        sinp = 2 * (q.w * q.y - q.z * q.x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)  # Use 90 degrees if out of range
        else:
            pitch = math.asin(sinp)
        
        # Yaw (z-axis rotation)
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        
        return pitch, yaw, roll
    
    @staticmethod
    def transform_point(point: Vector3D, transform: Transform3D) -> Vector3D:
        """Transform a point by a transformation matrix"""
        # Convert point to homogeneous coordinates
        point_homo = np.array([point.x, point.y, point.z, 1.0])
        
        # Apply transformation
        result_homo = transform.to_matrix() @ point_homo
        
        # Convert back to 3D
        return Vector3D(result_homo[0], result_homo[1], result_homo[2])
    
    @staticmethod
    def inverse_transform_point(point: Vector3D, transform: Transform3D) -> Vector3D:
        """Inverse transform a point"""
        # Calculate inverse transformation matrix
        transform_matrix = transform.to_matrix()
        inverse_matrix = np.linalg.inv(transform_matrix)
        
        # Convert point to homogeneous coordinates
        point_homo = np.array([point.x, point.y, point.z, 1.0])
        
        # Apply inverse transformation
        result_homo = inverse_matrix @ point_homo
        
        # Convert back to 3D
        return Vector3D(result_homo[0], result_homo[1], result_homo[2])
    
    @staticmethod
    def screen_to_world(screen_x: float, screen_y: float, depth: float,
                       view_matrix: np.ndarray, projection_matrix: np.ndarray,
                       viewport_width: int, viewport_height: int) -> Vector3D:
        """Convert screen coordinates to world coordinates"""
        # Normalize screen coordinates to [-1, 1]
        ndc_x = (2.0 * screen_x) / viewport_width - 1.0
        ndc_y = 1.0 - (2.0 * screen_y) / viewport_height
        ndc_z = 2.0 * depth - 1.0
        
        # Convert to clip coordinates
        clip_coords = np.array([ndc_x, ndc_y, ndc_z, 1.0])
        
        # Convert to view coordinates
        view_projection_matrix = projection_matrix @ view_matrix
        inverse_vp_matrix = np.linalg.inv(view_projection_matrix)
        world_coords = inverse_vp_matrix @ clip_coords
        
        # Perspective divide
        if world_coords[3] != 0:
            world_coords /= world_coords[3]
        
        return Vector3D(world_coords[0], world_coords[1], world_coords[2])
    
    @staticmethod
    def world_to_screen(world_point: Vector3D, view_matrix: np.ndarray,
                       projection_matrix: np.ndarray, viewport_width: int,
                       viewport_height: int) -> Tuple[float, float, float]:
        """Convert world coordinates to screen coordinates"""
        # Convert to homogeneous coordinates
        world_homo = np.array([world_point.x, world_point.y, world_point.z, 1.0])
        
        # Apply view and projection transformations
        view_projection_matrix = projection_matrix @ view_matrix
        clip_coords = view_projection_matrix @ world_homo
        
        # Perspective divide
        if clip_coords[3] != 0:
            ndc_coords = clip_coords / clip_coords[3]
        else:
            ndc_coords = clip_coords
        
        # Convert to screen coordinates
        screen_x = (ndc_coords[0] + 1.0) * 0.5 * viewport_width
        screen_y = (1.0 - ndc_coords[1]) * 0.5 * viewport_height
        depth = (ndc_coords[2] + 1.0) * 0.5
        
        return screen_x, screen_y, depth
    
    @staticmethod
    def create_look_at_matrix(eye: Vector3D, target: Vector3D, up: Vector3D) -> np.ndarray:
        """Create a look-at view matrix"""
        # Calculate camera coordinate system
        forward = (target - eye).normalize()
        right = SpatialMath.cross_product(forward, up.normalize()).normalize()
        camera_up = SpatialMath.cross_product(right, forward)
        
        # Create rotation matrix
        rotation = np.array([
            [right.x, camera_up.x, -forward.x, 0],
            [right.y, camera_up.y, -forward.y, 0],
            [right.z, camera_up.z, -forward.z, 0],
            [0, 0, 0, 1]
        ])
        
        # Create translation matrix
        translation = np.array([
            [1, 0, 0, -eye.x],
            [0, 1, 0, -eye.y],
            [0, 0, 1, -eye.z],
            [0, 0, 0, 1]
        ])
        
        return rotation @ translation
    
    @staticmethod
    def create_perspective_matrix(fov: float, aspect: float, near: float, far: float) -> np.ndarray:
        """Create a perspective projection matrix"""
        f = 1.0 / math.tan(fov * 0.5)
        
        return np.array([
            [f / aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (far + near) / (near - far), (2 * far * near) / (near - far)],
            [0, 0, -1, 0]
        ])
    
    @staticmethod
    def create_orthographic_matrix(left: float, right: float, bottom: float,
                                 top: float, near: float, far: float) -> np.ndarray:
        """Create an orthographic projection matrix"""
        return np.array([
            [2 / (right - left), 0, 0, -(right + left) / (right - left)],
            [0, 2 / (top - bottom), 0, -(top + bottom) / (top - bottom)],
            [0, 0, -2 / (far - near), -(far + near) / (far - near)],
            [0, 0, 0, 1]
        ])
    
    @staticmethod
    def frustum_planes_from_matrix(mvp_matrix: np.ndarray) -> List[np.ndarray]:
        """Extract frustum planes from MVP matrix"""
        # Extract the six planes: left, right, bottom, top, near, far
        planes = []
        
        # Left plane
        left = mvp_matrix[3] + mvp_matrix[0]
        planes.append(left / np.linalg.norm(left[:3]))
        
        # Right plane
        right = mvp_matrix[3] - mvp_matrix[0]
        planes.append(right / np.linalg.norm(right[:3]))
        
        # Bottom plane
        bottom = mvp_matrix[3] + mvp_matrix[1]
        planes.append(bottom / np.linalg.norm(bottom[:3]))
        
        # Top plane
        top = mvp_matrix[3] - mvp_matrix[1]
        planes.append(top / np.linalg.norm(top[:3]))
        
        # Near plane
        near = mvp_matrix[3] + mvp_matrix[2]
        planes.append(near / np.linalg.norm(near[:3]))
        
        # Far plane
        far = mvp_matrix[3] - mvp_matrix[2]
        planes.append(far / np.linalg.norm(far[:3]))
        
        return planes
    
    @staticmethod
    def point_in_frustum(point: Vector3D, frustum_planes: List[np.ndarray]) -> bool:
        """Check if point is inside frustum"""
        point_homo = np.array([point.x, point.y, point.z, 1.0])
        
        for plane in frustum_planes:
            if np.dot(plane, point_homo) < 0:
                return False
        
        return True
    
    @staticmethod
    def sphere_in_frustum(center: Vector3D, radius: float, frustum_planes: List[np.ndarray]) -> bool:
        """Check if sphere intersects or is inside frustum"""
        center_homo = np.array([center.x, center.y, center.z, 1.0])
        
        for plane in frustum_planes:
            distance = np.dot(plane, center_homo)
            if distance < -radius:
                return False
        
        return True
    
    @staticmethod
    def ray_sphere_intersection(ray_origin: Vector3D, ray_direction: Vector3D,
                              sphere_center: Vector3D, sphere_radius: float) -> Optional[Tuple[float, float]]:
        """Calculate ray-sphere intersection"""
        oc = ray_origin - sphere_center
        a = SpatialMath.dot_product(ray_direction, ray_direction)
        b = 2.0 * SpatialMath.dot_product(oc, ray_direction)
        c = SpatialMath.dot_product(oc, oc) - sphere_radius * sphere_radius
        
        discriminant = b * b - 4 * a * c
        
        if discriminant < 0:
            return None
        
        sqrt_discriminant = math.sqrt(discriminant)
        t1 = (-b - sqrt_discriminant) / (2.0 * a)
        t2 = (-b + sqrt_discriminant) / (2.0 * a)
        
        return (t1, t2)
    
    @staticmethod
    def ray_plane_intersection(ray_origin: Vector3D, ray_direction: Vector3D,
                             plane_point: Vector3D, plane_normal: Vector3D) -> Optional[float]:
        """Calculate ray-plane intersection"""
        denom = SpatialMath.dot_product(plane_normal, ray_direction)
        
        if abs(denom) < 1e-6:  # Ray is parallel to plane
            return None
        
        t = SpatialMath.dot_product(plane_point - ray_origin, plane_normal) / denom
        
        if t >= 0:
            return t
        
        return None
    
    @staticmethod
    def barycentric_coordinates(p: Vector3D, a: Vector3D, b: Vector3D, c: Vector3D) -> Tuple[float, float, float]:
        """Calculate barycentric coordinates of point p relative to triangle abc"""
        v0 = c - a
        v1 = b - a
        v2 = p - a
        
        dot00 = SpatialMath.dot_product(v0, v0)
        dot01 = SpatialMath.dot_product(v0, v1)
        dot02 = SpatialMath.dot_product(v0, v2)
        dot11 = SpatialMath.dot_product(v1, v1)
        dot12 = SpatialMath.dot_product(v1, v2)
        
        inv_denom = 1 / (dot00 * dot11 - dot01 * dot01)
        u = (dot11 * dot02 - dot01 * dot12) * inv_denom
        v = (dot00 * dot12 - dot01 * dot02) * inv_denom
        w = 1.0 - u - v
        
        return u, v, w
    
    @staticmethod
    def point_in_triangle(p: Vector3D, a: Vector3D, b: Vector3D, c: Vector3D) -> bool:
        """Check if point is inside triangle"""
        u, v, w = SpatialMath.barycentric_coordinates(p, a, b, c)
        return u >= 0 and v >= 0 and w >= 0