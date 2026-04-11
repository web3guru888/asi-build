"""Tests for holographic module (Candidate 8)."""
import pytest
import numpy as np
import math


class TestSpatialMath:
    """Test 3D math utilities."""

    def _math(self):
        from src.asi_build.holographic.core.math_utils import SpatialMath
        return SpatialMath

    def _vec(self, x, y, z):
        from src.asi_build.holographic.core.base import Vector3D
        return Vector3D(x, y, z)

    def _quat(self, w, x, y, z):
        from src.asi_build.holographic.core.base import Quaternion
        return Quaternion(w, x, y, z)

    def test_distance_3d(self):
        sm = self._math()
        d = sm.distance_3d(self._vec(0, 0, 0), self._vec(3, 4, 0))
        assert abs(d - 5.0) < 1e-6

    def test_dot_product(self):
        sm = self._math()
        result = sm.dot_product(self._vec(1, 2, 3), self._vec(4, 5, 6))
        assert result == 32.0

    def test_cross_product(self):
        sm = self._math()
        result = sm.cross_product(self._vec(1, 0, 0), self._vec(0, 1, 0))
        assert abs(result.z - 1.0) < 1e-6
        assert abs(result.x) < 1e-6
        assert abs(result.y) < 1e-6

    def test_angle_between_perpendicular(self):
        sm = self._math()
        angle = sm.angle_between_vectors(self._vec(1, 0, 0), self._vec(0, 1, 0))
        assert abs(angle - math.pi / 2) < 0.01

    def test_angle_between_parallel(self):
        sm = self._math()
        angle = sm.angle_between_vectors(self._vec(1, 0, 0), self._vec(2, 0, 0))
        assert abs(angle) < 0.01

    def test_reflect_vector(self):
        sm = self._math()
        v = self._vec(1, -1, 0)
        normal = self._vec(0, 1, 0)
        reflected = sm.reflect_vector(v, normal)
        assert abs(reflected.x - 1.0) < 1e-6
        assert abs(reflected.y - 1.0) < 1e-6

    def test_lerp_at_zero(self):
        sm = self._math()
        a = self._vec(0, 0, 0)
        b = self._vec(10, 10, 10)
        result = sm.lerp_vector(a, b, 0.0)
        assert abs(result.x) < 1e-6

    def test_lerp_at_one(self):
        sm = self._math()
        a = self._vec(0, 0, 0)
        b = self._vec(10, 10, 10)
        result = sm.lerp_vector(a, b, 1.0)
        assert abs(result.x - 10.0) < 1e-6

    def test_euler_to_quaternion_identity(self):
        sm = self._math()
        q = sm.euler_to_quaternion(0, 0, 0)
        assert abs(q.w - 1.0) < 1e-6
        assert abs(q.x) < 1e-6

    def test_quaternion_euler_roundtrip(self):
        sm = self._math()
        pitch, yaw, roll = 0.3, 0.5, 0.1
        q = sm.euler_to_quaternion(pitch, yaw, roll)
        p2, y2, r2 = sm.quaternion_to_euler(q)
        assert abs(pitch - p2) < 0.01
        assert abs(yaw - y2) < 0.01
        assert abs(roll - r2) < 0.01

    def test_perspective_matrix_shape(self):
        sm = self._math()
        mat = sm.create_perspective_matrix(math.radians(60), 16/9, 0.1, 100)
        assert mat.shape == (4, 4)

    def test_look_at_matrix_shape(self):
        sm = self._math()
        mat = sm.create_look_at_matrix(
            self._vec(0, 0, 5), self._vec(0, 0, 0), self._vec(0, 1, 0)
        )
        assert mat.shape == (4, 4)

    def test_ray_sphere_intersection_hit(self):
        sm = self._math()
        origin = self._vec(0, 0, -5)
        direction = self._vec(0, 0, 1)
        center = self._vec(0, 0, 0)
        result = sm.ray_sphere_intersection(origin, direction, center, 1.0)
        assert result is not None
        assert result[0] < result[1]

    def test_ray_sphere_intersection_miss(self):
        sm = self._math()
        origin = self._vec(0, 5, -5)
        direction = self._vec(0, 0, 1)
        center = self._vec(0, 0, 0)
        result = sm.ray_sphere_intersection(origin, direction, center, 1.0)
        assert result is None

    def test_barycentric_inside_triangle(self):
        sm = self._math()
        a, b, c = self._vec(0, 0, 0), self._vec(1, 0, 0), self._vec(0, 1, 0)
        p = self._vec(0.2, 0.2, 0)
        assert sm.point_in_triangle(p, a, b, c)

    def test_barycentric_outside_triangle(self):
        sm = self._math()
        a, b, c = self._vec(0, 0, 0), self._vec(1, 0, 0), self._vec(0, 1, 0)
        p = self._vec(2, 2, 0)
        assert not sm.point_in_triangle(p, a, b, c)


class TestVolumeRenderer:
    """Test volume rendering math."""

    def test_ray_box_intersection(self):
        from src.asi_build.holographic.display.volumetric_display import VolumeRenderer
        vr = VolumeRenderer((32, 32, 32))
        from src.asi_build.holographic.core.base import Vector3D
        origin = Vector3D(0, 0, 5)
        direction = Vector3D(0, 0, -1)
        t_min, t_max = vr._ray_box_intersection(origin, direction)
        assert t_min < t_max
        assert t_min >= 0

    def test_trilinear_interpolation_center(self):
        from src.asi_build.holographic.display.volumetric_display import VolumeRenderer
        from src.asi_build.holographic.core.base import Vector3D
        vr = VolumeRenderer((16, 16, 16))
        # Set all voxels to 1
        vr.volume_data.fill(1.0)
        pos = Vector3D(0, 0, 0)  # center of volume
        sample = vr._sample_volume(pos)
        assert all(s >= 0 for s in sample)

    def test_add_voxel_within_bounds(self):
        from src.asi_build.holographic.display.volumetric_display import VolumeRenderer
        from src.asi_build.holographic.core.base import Vector3D
        vr = VolumeRenderer((16, 16, 16))
        vr.add_voxel(Vector3D(0, 0, 0), (1.0, 0.0, 0.0, 1.0), intensity=0.8)
        assert vr.density_data.max() > 0
