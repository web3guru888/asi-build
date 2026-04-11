"""
Comprehensive tests for the holographic module.

Covers:
- base types (Vector3D, Quaternion, Transform3D, BoundingBox3D)
- SpatialMath (distance, dot, cross, angles, projections, lerp/slerp, matrices, ray casts)
- HolographicPerformanceMonitor
- SpatialHash
- HolographicBase lifecycle
- HolographicConfig + sub-configs + validation + presets
- HolographicEventSystem (sync events, subscribe/unsubscribe, filters, history, stats)
- LightFieldProcessor (init, slices, bilinear sampling, camera array, performance stats)
- LightRay plenoptic coords
- HolographicEngine (status, callbacks, config)
- VolumeRenderer (init, set_volume_data, add_voxel, clear)
- VolumetricDisplay (layers, camera)
- Physics datatypes (PhysicsProperties, Force, CollisionEvent, SpatialGrid, QuantumSimulator)
- HolographicPhysicsManager (bodies, forces, constraints, gravity)
- SpatialAudioManager (sources, listener, reverb zones, master volume)
- MixedRealityEngine (virtual objects, spatial anchors, reality modes, camera pose)
- HandTracker types (Joint3D, Finger, HandLandmarks, pinch/fist/open_palm)
- TelepresenceManager (init, event handlers, remote users)
- Exceptions
"""

import asyncio
import math
import sys
import time
import types
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _vec(x=0.0, y=0.0, z=0.0):
    from src.asi_build.holographic.core.base import Vector3D

    return Vector3D(x, y, z)


def _quat(w=1.0, x=0.0, y=0.0, z=0.0):
    from src.asi_build.holographic.core.base import Quaternion

    return Quaternion(w, x, y, z)


# ===========================================================================
# 1.  Base types  (base.py)
# ===========================================================================


class TestVector3D:
    """Tests for Vector3D dataclass."""

    def test_add(self):
        v = _vec(1, 2, 3) + _vec(4, 5, 6)
        assert (v.x, v.y, v.z) == (5, 7, 9)

    def test_sub(self):
        v = _vec(10, 20, 30) - _vec(1, 2, 3)
        assert (v.x, v.y, v.z) == (9, 18, 27)

    def test_mul_scalar(self):
        v = _vec(1, 2, 3) * 3
        assert (v.x, v.y, v.z) == (3, 6, 9)

    def test_magnitude_unit(self):
        assert abs(_vec(3, 4, 0).magnitude() - 5.0) < 1e-6

    def test_magnitude_zero(self):
        assert _vec(0, 0, 0).magnitude() == 0.0

    def test_normalize(self):
        n = _vec(0, 0, 5).normalize()
        assert abs(n.z - 1.0) < 1e-6 and abs(n.x) < 1e-6 and abs(n.y) < 1e-6

    def test_normalize_zero_vector(self):
        n = _vec(0, 0, 0).normalize()
        assert (n.x, n.y, n.z) == (0, 0, 0)

    def test_to_array(self):
        arr = _vec(1, 2, 3).to_array()
        np.testing.assert_array_equal(arr, [1, 2, 3])


class TestQuaternion:
    """Tests for Quaternion dataclass."""

    def test_identity_normalize(self):
        q = _quat(1, 0, 0, 0).normalize()
        assert abs(q.w - 1.0) < 1e-6

    def test_normalize_non_unit(self):
        q = _quat(2, 0, 0, 0).normalize()
        assert abs(q.w - 1.0) < 1e-6

    def test_to_matrix_identity(self):
        R = _quat(1, 0, 0, 0).to_matrix()
        np.testing.assert_allclose(R, np.eye(3), atol=1e-6)

    def test_to_matrix_shape(self):
        R = _quat(0.707, 0.707, 0, 0).to_matrix()
        assert R.shape == (3, 3)

    def test_rotation_matrix_orthogonal(self):
        q = _quat(0.5, 0.5, 0.5, 0.5).normalize()
        R = q.to_matrix()
        np.testing.assert_allclose(R @ R.T, np.eye(3), atol=1e-6)

    def test_rotation_matrix_det_one(self):
        q = _quat(0.5, 0.5, 0.5, 0.5).normalize()
        R = q.to_matrix()
        assert abs(np.linalg.det(R) - 1.0) < 1e-6


class TestTransform3D:
    """Tests for Transform3D."""

    def test_default_init(self):
        from src.asi_build.holographic.core.base import Transform3D

        t = Transform3D()
        assert t.position.x == 0 and t.position.y == 0 and t.position.z == 0
        assert t.rotation.w == 1 and t.rotation.x == 0
        assert t.scale.x == 1 and t.scale.y == 1 and t.scale.z == 1

    def test_to_matrix_shape(self):
        from src.asi_build.holographic.core.base import Transform3D

        M = Transform3D().to_matrix()
        assert M.shape == (4, 4)

    def test_identity_transform_is_identity(self):
        from src.asi_build.holographic.core.base import Transform3D

        M = Transform3D().to_matrix()
        np.testing.assert_allclose(M, np.eye(4), atol=1e-6)

    def test_translation_only(self):
        from src.asi_build.holographic.core.base import Transform3D

        t = Transform3D(position=_vec(5, 10, 15))
        M = t.to_matrix()
        assert abs(M[0, 3] - 5) < 1e-6
        assert abs(M[1, 3] - 10) < 1e-6
        assert abs(M[2, 3] - 15) < 1e-6


class TestBoundingBox3D:
    """Tests for BoundingBox3D."""

    def test_contains_inside(self):
        from src.asi_build.holographic.core.base import BoundingBox3D

        bb = BoundingBox3D(min_point=_vec(-1, -1, -1), max_point=_vec(1, 1, 1))
        assert bb.contains(_vec(0, 0, 0))

    def test_contains_outside(self):
        from src.asi_build.holographic.core.base import BoundingBox3D

        bb = BoundingBox3D(min_point=_vec(-1, -1, -1), max_point=_vec(1, 1, 1))
        assert not bb.contains(_vec(2, 0, 0))

    def test_contains_boundary(self):
        from src.asi_build.holographic.core.base import BoundingBox3D

        bb = BoundingBox3D(min_point=_vec(0, 0, 0), max_point=_vec(1, 1, 1))
        assert bb.contains(_vec(0, 0, 0))  # Edge is inclusive

    def test_volume(self):
        from src.asi_build.holographic.core.base import BoundingBox3D

        bb = BoundingBox3D(min_point=_vec(0, 0, 0), max_point=_vec(2, 3, 4))
        assert abs(bb.volume() - 24.0) < 1e-6


class TestEnums:
    """Test enum values exist."""

    def test_hologram_types(self):
        from src.asi_build.holographic.core.base import HologramType

        assert HologramType.STATIC.value == "static"
        assert HologramType.VOLUMETRIC.value == "volumetric"

    def test_render_quality(self):
        from src.asi_build.holographic.core.base import RenderQuality

        assert RenderQuality.LOW.value == "low"
        assert RenderQuality.ULTRA.value == "ultra"

    def test_interaction_modes(self):
        from src.asi_build.holographic.core.base import InteractionMode

        assert InteractionMode.GESTURE.value == "gesture"
        assert InteractionMode.BRAIN.value == "brain"


class TestExceptions:
    """Test custom exceptions."""

    def test_exception_hierarchy(self):
        from src.asi_build.holographic.core.base import (
            CalibrationError,
            GestureRecognitionError,
            HolographicException,
            InitializationError,
            RenderingError,
        )

        assert issubclass(InitializationError, HolographicException)
        assert issubclass(RenderingError, HolographicException)
        assert issubclass(CalibrationError, HolographicException)
        assert issubclass(GestureRecognitionError, HolographicException)

    def test_exceptions_are_catchable(self):
        from src.asi_build.holographic.core.base import HolographicException, InitializationError

        with pytest.raises(HolographicException):
            raise InitializationError("test")


# ===========================================================================
# 2.  HolographicPerformanceMonitor
# ===========================================================================


class TestPerformanceMonitor:
    def _mon(self):
        from src.asi_build.holographic.core.base import HolographicPerformanceMonitor

        return HolographicPerformanceMonitor()

    def test_start_end_returns_positive(self):
        m = self._mon()
        m.start_timer("op")
        dur = m.end_timer("op")
        assert dur >= 0

    def test_average_time(self):
        m = self._mon()
        m.start_timer("op")
        m.end_timer("op")
        m.start_timer("op")
        m.end_timer("op")
        avg = m.get_average_time("op")
        assert avg >= 0

    def test_unknown_op_average(self):
        m = self._mon()
        assert m.get_average_time("unknown") == 0.0

    def test_get_fps_no_data(self):
        m = self._mon()
        assert m.get_fps("frame") == 0.0

    def test_clear_metrics(self):
        m = self._mon()
        m.start_timer("a")
        m.end_timer("a")
        m.clear_metrics()
        assert m.get_average_time("a") == 0.0

    def test_end_timer_without_start(self):
        m = self._mon()
        assert m.end_timer("never_started") == 0.0


# ===========================================================================
# 3.  SpatialHash
# ===========================================================================


class TestSpatialHash:
    def _hash(self, cell_size=1.0):
        from src.asi_build.holographic.core.base import SpatialHash

        return SpatialHash(cell_size)

    def test_insert_and_query(self):
        sh = self._hash()
        sh.insert("a", _vec(0.5, 0.5, 0.5))
        result = sh.query_radius(_vec(0.5, 0.5, 0.5), 1.0)
        assert "a" in result

    def test_query_empty(self):
        sh = self._hash()
        result = sh.query_radius(_vec(0, 0, 0), 1.0)
        assert len(result) == 0

    def test_insert_and_remove(self):
        sh = self._hash()
        sh.insert("a", _vec(0, 0, 0))
        sh.remove("a", _vec(0, 0, 0))
        result = sh.query_radius(_vec(0, 0, 0), 1.0)
        assert "a" not in result

    def test_multiple_objects(self):
        sh = self._hash()
        sh.insert("a", _vec(0, 0, 0))
        sh.insert("b", _vec(0.5, 0, 0))
        sh.insert("c", _vec(100, 100, 100))
        result = sh.query_radius(_vec(0, 0, 0), 2.0)
        assert "a" in result
        assert "b" in result
        assert "c" not in result

    def test_insert_with_radius(self):
        sh = self._hash(cell_size=1.0)
        sh.insert("big", _vec(0, 0, 0), radius=2.0)
        result = sh.query_radius(_vec(1.5, 0, 0), 0.1)
        assert "big" in result


# ===========================================================================
# 4.  SpatialMath  (math_utils.py)
# ===========================================================================


class TestSpatialMath:
    def _sm(self):
        from src.asi_build.holographic.core.math_utils import SpatialMath

        return SpatialMath

    # ---- basic vector ops ----
    def test_distance_3d(self):
        assert abs(self._sm().distance_3d(_vec(0, 0, 0), _vec(3, 4, 0)) - 5.0) < 1e-6

    def test_dot_product(self):
        assert self._sm().dot_product(_vec(1, 2, 3), _vec(4, 5, 6)) == 32.0

    def test_cross_product_orthogonal(self):
        c = self._sm().cross_product(_vec(1, 0, 0), _vec(0, 1, 0))
        assert abs(c.z - 1.0) < 1e-6

    def test_cross_product_parallel_is_zero(self):
        c = self._sm().cross_product(_vec(1, 0, 0), _vec(2, 0, 0))
        assert abs(c.magnitude()) < 1e-6

    def test_angle_perpendicular(self):
        angle = self._sm().angle_between_vectors(_vec(1, 0, 0), _vec(0, 1, 0))
        assert abs(angle - math.pi / 2) < 0.01

    def test_angle_parallel(self):
        angle = self._sm().angle_between_vectors(_vec(1, 0, 0), _vec(5, 0, 0))
        assert abs(angle) < 0.01

    def test_angle_antiparallel(self):
        angle = self._sm().angle_between_vectors(_vec(1, 0, 0), _vec(-1, 0, 0))
        assert abs(angle - math.pi) < 0.01

    # ---- projection ----
    def test_project_vector(self):
        proj = self._sm().project_vector(_vec(3, 4, 0), _vec(1, 0, 0))
        assert abs(proj.x - 3.0) < 1e-6
        assert abs(proj.y) < 1e-6

    # ---- reflection ----
    def test_reflect_vector(self):
        r = self._sm().reflect_vector(_vec(1, -1, 0), _vec(0, 1, 0))
        assert abs(r.x - 1.0) < 1e-6
        assert abs(r.y - 1.0) < 1e-6

    # ---- lerp ----
    def test_lerp_zero(self):
        r = self._sm().lerp_vector(_vec(0, 0, 0), _vec(10, 10, 10), 0.0)
        assert abs(r.x) < 1e-6

    def test_lerp_one(self):
        r = self._sm().lerp_vector(_vec(0, 0, 0), _vec(10, 10, 10), 1.0)
        assert abs(r.x - 10.0) < 1e-6

    def test_lerp_half(self):
        r = self._sm().lerp_vector(_vec(0, 0, 0), _vec(10, 0, 0), 0.5)
        assert abs(r.x - 5.0) < 1e-6

    def test_lerp_clamps(self):
        r = self._sm().lerp_vector(_vec(0, 0, 0), _vec(10, 0, 0), 2.0)
        assert abs(r.x - 10.0) < 1e-6

    # ---- slerp ----
    def test_slerp_identity(self):
        q1 = _quat(1, 0, 0, 0)
        q2 = _quat(1, 0, 0, 0)
        r = self._sm().slerp_quaternion(q1, q2, 0.5)
        assert abs(r.w - 1.0) < 0.01

    def test_slerp_endpoints(self):
        q1 = _quat(1, 0, 0, 0)
        q2 = _quat(0.707, 0.707, 0, 0)
        r0 = self._sm().slerp_quaternion(q1, q2, 0.0)
        assert abs(r0.w - 1.0) < 0.01
        r1 = self._sm().slerp_quaternion(q1, q2, 1.0)
        n = r1.normalize()
        assert abs(n.x) > 0.3  # Should be close to q2

    # ---- euler / quaternion ----
    def test_euler_to_quat_identity(self):
        q = self._sm().euler_to_quaternion(0, 0, 0)
        assert abs(q.w - 1.0) < 1e-6

    def test_euler_quat_roundtrip(self):
        sm = self._sm()
        p, y, r = 0.3, 0.5, 0.1
        q = sm.euler_to_quaternion(p, y, r)
        p2, y2, r2 = sm.quaternion_to_euler(q)
        assert abs(p - p2) < 0.01
        assert abs(y - y2) < 0.01
        assert abs(r - r2) < 0.01

    # ---- transform_point ----
    def test_transform_point_identity(self):
        from src.asi_build.holographic.core.base import Transform3D

        sm = self._sm()
        pt = sm.transform_point(_vec(1, 2, 3), Transform3D())
        assert abs(pt.x - 1.0) < 1e-6

    def test_transform_point_translation(self):
        from src.asi_build.holographic.core.base import Transform3D

        sm = self._sm()
        t = Transform3D(position=_vec(10, 0, 0))
        pt = sm.transform_point(_vec(1, 0, 0), t)
        assert abs(pt.x - 11.0) < 1e-6

    def test_inverse_transform_roundtrip(self):
        from src.asi_build.holographic.core.base import Transform3D

        sm = self._sm()
        t = Transform3D(position=_vec(5, 5, 5))
        original = _vec(1, 2, 3)
        transformed = sm.transform_point(original, t)
        restored = sm.inverse_transform_point(transformed, t)
        assert abs(restored.x - original.x) < 1e-4
        assert abs(restored.y - original.y) < 1e-4

    # ---- matrices ----
    def test_perspective_matrix(self):
        mat = self._sm().create_perspective_matrix(math.radians(60), 16 / 9, 0.1, 100)
        assert mat.shape == (4, 4)
        assert mat[3, 2] == -1  # Perspective projection marker

    def test_orthographic_matrix(self):
        mat = self._sm().create_orthographic_matrix(-10, 10, -10, 10, 0.1, 100)
        assert mat.shape == (4, 4)

    def test_look_at_matrix(self):
        mat = self._sm().create_look_at_matrix(_vec(0, 0, 5), _vec(0, 0, 0), _vec(0, 1, 0))
        assert mat.shape == (4, 4)

    # ---- screen ↔ world ----
    def test_screen_to_world_and_back(self):
        sm = self._sm()
        view = sm.create_look_at_matrix(_vec(0, 0, 5), _vec(0, 0, 0), _vec(0, 1, 0))
        proj = sm.create_perspective_matrix(math.radians(60), 1.0, 0.1, 100)
        w, h = 800, 600
        wp = sm.screen_to_world(400, 300, 0.5, view, proj, w, h)
        sx, sy, sd = sm.world_to_screen(wp, view, proj, w, h)
        assert abs(sx - 400) < 2.0
        assert abs(sy - 300) < 2.0

    # ---- ray casts ----
    def test_ray_sphere_hit(self):
        result = self._sm().ray_sphere_intersection(
            _vec(0, 0, -5), _vec(0, 0, 1), _vec(0, 0, 0), 1.0
        )
        assert result is not None
        assert result[0] < result[1]

    def test_ray_sphere_miss(self):
        result = self._sm().ray_sphere_intersection(
            _vec(0, 5, -5), _vec(0, 0, 1), _vec(0, 0, 0), 1.0
        )
        assert result is None

    def test_ray_plane_intersection_hit(self):
        t = self._sm().ray_plane_intersection(
            _vec(0, 1, 0), _vec(0, -1, 0), _vec(0, 0, 0), _vec(0, 1, 0)
        )
        assert t is not None
        assert abs(t - 1.0) < 1e-6

    def test_ray_plane_parallel(self):
        t = self._sm().ray_plane_intersection(
            _vec(0, 1, 0), _vec(1, 0, 0), _vec(0, 0, 0), _vec(0, 1, 0)
        )
        assert t is None

    # ---- barycentric / point-in-triangle ----
    def test_barycentric_inside(self):
        a, b, c = _vec(0, 0, 0), _vec(1, 0, 0), _vec(0, 1, 0)
        u, v, w = self._sm().barycentric_coordinates(_vec(0.2, 0.2, 0), a, b, c)
        assert u >= 0 and v >= 0 and w >= 0

    def test_point_in_triangle_inside(self):
        a, b, c = _vec(0, 0, 0), _vec(1, 0, 0), _vec(0, 1, 0)
        assert self._sm().point_in_triangle(_vec(0.2, 0.2, 0), a, b, c)

    def test_point_in_triangle_outside(self):
        a, b, c = _vec(0, 0, 0), _vec(1, 0, 0), _vec(0, 1, 0)
        assert not self._sm().point_in_triangle(_vec(2, 2, 0), a, b, c)

    # ---- frustum ----
    def test_frustum_planes_extraction(self):
        sm = self._sm()
        proj = sm.create_perspective_matrix(math.radians(60), 1.0, 0.1, 100)
        view = sm.create_look_at_matrix(_vec(0, 0, 5), _vec(0, 0, 0), _vec(0, 1, 0))
        mvp = proj @ view
        planes = sm.frustum_planes_from_matrix(mvp)
        assert len(planes) == 6

    def test_point_in_frustum_center(self):
        sm = self._sm()
        proj = sm.create_perspective_matrix(math.radians(90), 1.0, 0.1, 100)
        view = np.eye(4)
        mvp = proj @ view
        planes = sm.frustum_planes_from_matrix(mvp)
        # A point at origin should be in front of camera looking at -Z
        # But center of frustum for camera at origin looking -Z is (0,0,-50)
        assert sm.point_in_frustum(_vec(0, 0, -5), planes)


# ===========================================================================
# 5.  HolographicConfig  (config.py)
# ===========================================================================


class TestHolographicConfig:
    def test_defaults_valid(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        assert cfg.validate_config()

    def test_default_display(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        assert cfg.display.resolution_x == 1920
        assert cfg.display.resolution_y == 1080

    def test_update_config(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        assert cfg.update_config("display", {"resolution_x": 3840})
        assert cfg.display.resolution_x == 3840

    def test_update_invalid_section(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        assert not cfg.update_config("nonexistent", {"foo": 1})

    def test_get_config_dict(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        d = cfg.get_config_dict()
        assert "display" in d and "rendering" in d and "audio" in d

    def test_reset_to_defaults(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        cfg.display.resolution_x = 9999
        cfg.reset_to_defaults()
        assert cfg.display.resolution_x == 1920

    def test_validate_rejects_negative_resolution(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        cfg.display.resolution_x = -1
        assert not cfg.validate_config()

    def test_validate_rejects_bad_quality(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        cfg.rendering.quality = "insane"
        assert not cfg.validate_config()

    def test_validate_rejects_bad_sample_rate(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        cfg.audio.sample_rate = 22050
        assert not cfg.validate_config()

    def test_validate_rejects_bad_port(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        cfg.network.server_port = 0
        assert not cfg.validate_config()

    def test_quality_preset_low(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        preset = cfg.get_quality_preset("low")
        assert preset["rendering"]["quality"] == "low"

    def test_apply_quality_preset(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        assert cfg.apply_quality_preset("ultra")
        assert cfg.rendering.quality == "ultra"
        assert cfg.rendering.texture_resolution == 4096

    def test_apply_invalid_preset_gets_high(self):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        preset = cfg.get_quality_preset("imaginary")
        assert preset["rendering"]["quality"] == "high"

    def test_save_and_load_config(self, tmp_path):
        from src.asi_build.holographic.core.config import HolographicConfig

        cfg = HolographicConfig()
        cfg.config_dir = tmp_path
        cfg.config_path = tmp_path / "test_config.json"
        cfg.display.resolution_x = 4096
        assert cfg.save_config()
        cfg2 = HolographicConfig()
        cfg2.config_dir = tmp_path
        cfg2.config_path = tmp_path / "test_config.json"
        cfg2.load_config()
        assert cfg2.display.resolution_x == 4096


class TestSubConfigs:
    """Verify individual config dataclasses."""

    def test_display_config_defaults(self):
        from src.asi_build.holographic.core.config import DisplayConfig

        d = DisplayConfig()
        assert d.field_of_view == 110.0

    def test_rendering_config_defaults(self):
        from src.asi_build.holographic.core.config import RenderingConfig

        r = RenderingConfig()
        assert r.lighting_model == "pbr"

    def test_gesture_config_defaults(self):
        from src.asi_build.holographic.core.config import GestureConfig

        g = GestureConfig()
        assert g.sensitivity == 0.8

    def test_audio_config_defaults(self):
        from src.asi_build.holographic.core.config import AudioConfig

        a = AudioConfig()
        assert a.hrtf_enabled is True

    def test_network_config_defaults(self):
        from src.asi_build.holographic.core.config import NetworkConfig

        n = NetworkConfig()
        assert n.server_port == 8080

    def test_security_config_defaults(self):
        from src.asi_build.holographic.core.config import SecurityConfig

        s = SecurityConfig()
        assert s.data_retention_days == 30

    def test_performance_config_defaults(self):
        from src.asi_build.holographic.core.config import PerformanceConfig

        p = PerformanceConfig()
        assert p.max_fps == 120.0


# ===========================================================================
# 6.  HolographicEventSystem  (event_system.py)
# ===========================================================================


class TestHolographicEvent:
    def test_event_creation(self):
        from src.asi_build.holographic.core.event_system import EventPriority, HolographicEvent

        e = HolographicEvent(name="test", data={"k": 1}, timestamp=time.time())
        assert e.name == "test"
        assert e.event_id is not None

    def test_event_to_dict(self):
        from src.asi_build.holographic.core.event_system import EventPriority, HolographicEvent

        e = HolographicEvent(name="test", data={}, timestamp=1.0)
        d = e.to_dict()
        assert d["name"] == "test"
        assert "event_id" in d

    def test_event_from_dict_roundtrip(self):
        from src.asi_build.holographic.core.event_system import EventPriority, HolographicEvent

        e = HolographicEvent(name="foo", data={"x": 42}, timestamp=1.0, priority=EventPriority.HIGH)
        d = e.to_dict()
        e2 = HolographicEvent.from_dict(d)
        assert e2.name == "foo"
        assert e2.priority == EventPriority.HIGH


class TestEventSystemSync:
    """Test synchronous event pathway (no asyncio needed)."""

    def _es(self):
        from src.asi_build.holographic.core.event_system import HolographicEventSystem

        return HolographicEventSystem()

    def test_subscribe_and_emit_sync(self):
        es = self._es()
        received = []
        es.subscribe("test_event", lambda data: received.append(data))
        es.emit_sync("test_event", {"val": 42})
        assert len(received) == 1
        assert received[0]["val"] == 42

    def test_unsubscribe(self):
        es = self._es()
        received = []
        cb = lambda data: received.append(data)
        es.subscribe("ev", cb)
        assert es.unsubscribe("ev", cb)
        es.emit_sync("ev", {})
        assert len(received) == 0

    def test_unsubscribe_all(self):
        es = self._es()
        es.subscribe("ev", lambda d: None)
        es.subscribe("ev", lambda d: None)
        count = es.unsubscribe_all("ev")
        assert count == 2

    def test_unsubscribe_nonexistent(self):
        es = self._es()
        assert not es.unsubscribe("nothing", lambda d: None)

    def test_priority_ordering(self):
        from src.asi_build.holographic.core.event_system import EventPriority

        es = self._es()
        order = []
        es.subscribe("ev", lambda d: order.append("normal"), EventPriority.NORMAL)
        es.subscribe("ev", lambda d: order.append("high"), EventPriority.HIGH)
        es.subscribe("ev", lambda d: order.append("critical"), EventPriority.CRITICAL)
        es.emit_sync("ev")
        assert order[0] == "critical"
        assert order[1] == "high"
        assert order[2] == "normal"

    def test_global_filter_blocks(self):
        es = self._es()
        received = []
        es.subscribe("ev", lambda d: received.append(1))
        es.add_global_filter(lambda event: False)  # Block all
        es.emit_sync("ev")
        assert len(received) == 0

    def test_global_filter_remove(self):
        es = self._es()
        f = lambda event: False
        es.add_global_filter(f)
        es.remove_global_filter(f)
        received = []
        es.subscribe("ev", lambda d: received.append(1))
        es.emit_sync("ev")
        assert len(received) == 1

    def test_event_history(self):
        es = self._es()
        es.emit_sync("ev1")
        es.emit_sync("ev2")
        history = es.get_event_history()
        assert len(history) == 2

    def test_event_history_filter_by_name(self):
        es = self._es()
        es.emit_sync("ev1")
        es.emit_sync("ev2")
        es.emit_sync("ev1")
        history = es.get_event_history(event_name="ev1")
        assert len(history) == 2

    def test_event_history_limit(self):
        es = self._es()
        for i in range(10):
            es.emit_sync(f"ev{i}")
        history = es.get_event_history(limit=3)
        assert len(history) == 3

    def test_clear_history(self):
        es = self._es()
        es.emit_sync("ev")
        es.clear_history()
        assert len(es.get_event_history()) == 0

    def test_statistics(self):
        es = self._es()
        es.subscribe("x", lambda d: None)
        es.emit_sync("x")
        stats = es.get_statistics()
        assert stats["events_emitted"] == 1
        assert stats["events_processed"] == 1

    def test_clear_statistics(self):
        es = self._es()
        es.emit_sync("x")
        es.clear_statistics()
        assert es.stats["events_emitted"] == 0

    def test_wildcard_subscribe(self):
        es = self._es()
        received = []
        es.subscribe("system.*", lambda d: received.append(1))
        es.emit_sync("system.startup")
        assert len(received) == 1

    def test_history_max_size(self):
        es = self._es()
        es.max_history_size = 5
        for i in range(10):
            es.emit_sync(f"ev{i}")
        assert len(es.event_history) <= 5


# ===========================================================================
# 7.  LightFieldProcessor  (light_field.py)
# ===========================================================================


class TestLightRay:
    def test_plenoptic_coords(self):
        from src.asi_build.holographic.core.light_field import LightRay

        ray = LightRay(
            origin=_vec(1, 2, 0),
            direction=_vec(0, 0, -1),
            color=(1.0, 0.0, 0.0),
            intensity=1.0,
        )
        u, v, s, t = ray.to_plenoptic_coords(50.0)
        assert u == 1.0 and v == 2.0  # Position on sensor plane
        # Focal plane positions should be computed
        assert isinstance(s, float) and isinstance(t, float)

    def test_plenoptic_coords_zero_direction_z(self):
        from src.asi_build.holographic.core.light_field import LightRay

        ray = LightRay(
            origin=_vec(3, 4, 0),
            direction=_vec(1, 0, 0),  # z=0
            color=(0, 0, 0),
            intensity=0,
        )
        u, v, s, t = ray.to_plenoptic_coords(50.0)
        assert s == 3.0 and t == 4.0  # Falls back to origin


class TestLightFieldProcessorInit:
    def test_init_shapes(self):
        from src.asi_build.holographic.core.light_field import LightFieldProcessor

        lfp = LightFieldProcessor(resolution=(4, 4, 8, 8))
        assert lfp.light_field.shape == (4, 4, 8, 8, 3)
        assert lfp.depth_field.shape == (4, 4, 8, 8)

    def test_get_set_slice(self):
        from src.asi_build.holographic.core.light_field import LightFieldProcessor

        lfp = LightFieldProcessor(resolution=(4, 4, 8, 8))
        img = np.ones((8, 8, 3), dtype=np.float32)
        lfp.set_light_field_slice(0, 0, img)
        result = lfp.get_light_field_slice(0, 0)
        np.testing.assert_array_equal(result, img)

    def test_get_slice_out_of_bounds(self):
        from src.asi_build.holographic.core.light_field import LightFieldProcessor

        lfp = LightFieldProcessor(resolution=(2, 2, 4, 4))
        assert lfp.get_light_field_slice(10, 10) is None

    def test_bilinear_sample(self):
        from src.asi_build.holographic.core.light_field import LightFieldProcessor

        lfp = LightFieldProcessor(resolution=(2, 2, 4, 4))
        lfp.light_field[0, 0, :, :, :] = 0.5
        sample = lfp._bilinear_sample(0, 0, 1.5, 1.5)
        assert sample.shape == (3,)
        assert all(abs(s - 0.5) < 1e-6 for s in sample)

    def test_performance_stats(self):
        from src.asi_build.holographic.core.light_field import LightFieldProcessor

        lfp = LightFieldProcessor(resolution=(2, 2, 4, 4))
        stats = lfp.get_performance_stats()
        assert "camera_count" in stats
        assert "memory_usage_mb" in stats
        assert stats["gpu_enabled"] is False


class TestLightFieldCamera:
    def test_view_matrix(self):
        from src.asi_build.holographic.core.light_field import LightFieldCamera

        cam = LightFieldCamera(
            position=_vec(0, 0, 5),
            direction=_vec(0, 0, -1),
            up=_vec(0, 1, 0),
            field_of_view=math.radians(60),
            resolution=(64, 64),
            focal_length=0.05,
            aperture_size=2.8,
        )
        V = cam.get_view_matrix()
        assert V.shape == (4, 4)

    def test_projection_matrix(self):
        from src.asi_build.holographic.core.light_field import LightFieldCamera

        cam = LightFieldCamera(
            position=_vec(0, 0, 0),
            direction=_vec(0, 0, -1),
            up=_vec(0, 1, 0),
            field_of_view=math.radians(60),
            resolution=(64, 64),
            focal_length=0.05,
            aperture_size=2.8,
        )
        P = cam.get_projection_matrix()
        assert P.shape == (4, 4)


# ===========================================================================
# 8.  HolographicEngine  (engine.py)  — no full init (too many deps)
# ===========================================================================


class TestHolographicEnginePartial:
    """Test engine without calling initialize() (avoids sub-manager imports)."""

    def test_creation(self):
        from src.asi_build.holographic.core.engine import HolographicEngine

        engine = HolographicEngine()
        assert engine.running is False
        assert engine.frame_count == 0

    def test_status_before_init(self):
        from src.asi_build.holographic.core.engine import HolographicEngine

        engine = HolographicEngine()
        status = engine.get_status()
        assert status["running"] is False
        assert status["initialized"] is False

    def test_callbacks_add_remove(self):
        from src.asi_build.holographic.core.engine import HolographicEngine

        engine = HolographicEngine()
        cb = lambda dt: None
        engine.add_update_callback(cb)
        assert cb in engine.update_callbacks
        engine.remove_update_callback(cb)
        assert cb not in engine.update_callbacks

    def test_render_callback_add_remove(self):
        from src.asi_build.holographic.core.engine import HolographicEngine

        engine = HolographicEngine()
        cb = lambda dt: None
        engine.add_render_callback(cb)
        assert cb in engine.render_callbacks
        engine.remove_render_callback(cb)
        assert cb not in engine.render_callbacks

    def test_frame_callback(self):
        from src.asi_build.holographic.core.engine import HolographicEngine

        engine = HolographicEngine()
        cb = lambda dt, fc: None
        engine.add_frame_callback(cb)
        assert len(engine.frame_callbacks) == 1
        engine.remove_frame_callback(cb)
        assert len(engine.frame_callbacks) == 0

    def test_performance_metrics(self):
        from src.asi_build.holographic.core.engine import HolographicEngine

        engine = HolographicEngine()
        metrics = engine.get_performance_metrics()
        assert "fps" in metrics
        assert "frame_count" in metrics

    def test_enable_disable(self):
        from src.asi_build.holographic.core.engine import HolographicEngine

        engine = HolographicEngine()
        engine.disable()
        assert not engine.is_enabled()
        engine.enable()
        assert engine.is_enabled()


# ===========================================================================
# 9.  VolumeRenderer + VolumetricDisplay  (display/volumetric_display.py)
# ===========================================================================


class TestVolumeRenderer:
    def _renderer(self, res=(16, 16, 16)):
        from src.asi_build.holographic.display.volumetric_display import VolumeRenderer

        return VolumeRenderer(res)

    def test_init_shapes(self):
        vr = self._renderer()
        assert vr.volume_data.shape == (16, 16, 16, 4)
        assert vr.density_data.shape == (16, 16, 16)

    def test_set_volume_data_grayscale(self):
        vr = self._renderer((8, 8, 8))
        data = np.random.rand(8, 8, 8).astype(np.float32)
        vr.set_volume_data(data)
        # RGBA should have the grayscale in all three color channels
        np.testing.assert_allclose(vr.volume_data[:, :, :, 0], data, atol=1e-6)

    def test_set_volume_data_rgba(self):
        vr = self._renderer((8, 8, 8))
        data = np.random.rand(8, 8, 8, 4).astype(np.float32)
        vr.set_volume_data(data)
        np.testing.assert_allclose(vr.volume_data, data, atol=1e-6)

    def test_set_volume_data_wrong_shape_raises(self):
        vr = self._renderer((8, 8, 8))
        data = np.zeros((4, 4, 4))
        with pytest.raises(ValueError, match="doesn't match"):
            vr.set_volume_data(data)

    def test_set_volume_data_unsupported_format_raises(self):
        vr = self._renderer((8, 8, 8))
        data = np.zeros((8, 8, 8, 2))  # 2 channels — unsupported
        with pytest.raises(ValueError, match="Unsupported data format"):
            vr.set_volume_data(data)

    def test_add_voxel(self):
        vr = self._renderer((16, 16, 16))
        vr.add_voxel(_vec(0, 0, 0), (1.0, 0.0, 0.0, 1.0), intensity=0.8)
        assert vr.density_data.max() > 0

    def test_add_voxel_out_of_bounds_no_crash(self):
        vr = self._renderer((16, 16, 16))
        vr.add_voxel(_vec(100, 100, 100), (1.0, 0.0, 0.0, 1.0))
        # Should not crash; out-of-bounds voxels are silently ignored

    def test_clear_volume(self):
        vr = self._renderer((8, 8, 8))
        vr.volume_data.fill(1.0)
        vr.density_data.fill(1.0)
        vr.clear_volume()
        assert vr.volume_data.max() == 0
        assert vr.density_data.max() == 0


class TestVoxelData:
    def test_to_array(self):
        from src.asi_build.holographic.display.volumetric_display import VoxelData

        vd = VoxelData(position=_vec(1, 2, 3), color=(0.5, 0.6, 0.7, 1.0), intensity=0.9, size=1.0)
        arr = vd.to_array()
        assert len(arr) == 10
        assert arr[0] == 1.0  # position.x


class TestVolumetricDisplay:
    def _display(self):
        from src.asi_build.holographic.core.config import DisplayConfig
        from src.asi_build.holographic.display.volumetric_display import VolumetricDisplay

        return VolumetricDisplay(DisplayConfig())

    @pytest.mark.asyncio
    async def test_create_layer(self):
        d = self._display()
        layer = await d.create_layer("test", depth=0.5)
        assert layer is not None
        assert layer.layer_id == "test"

    @pytest.mark.asyncio
    async def test_create_duplicate_layer_raises(self):
        d = self._display()
        await d.create_layer("test", depth=0.5)
        with pytest.raises(ValueError, match="already exists"):
            await d.create_layer("test", depth=0.5)

    @pytest.mark.asyncio
    async def test_remove_layer(self):
        d = self._display()
        await d.create_layer("test", depth=0.5)
        assert await d.remove_layer("test")

    @pytest.mark.asyncio
    async def test_remove_nonexistent_layer(self):
        d = self._display()
        assert not await d.remove_layer("nope")

    @pytest.mark.asyncio
    async def test_clear_layer(self):
        d = self._display()
        await d.create_layer("test", depth=0.5)
        assert await d.clear_layer("test")

    def test_set_camera_position(self):
        d = self._display()
        d.set_camera_position(_vec(0, 0, 5), _vec(0, 0, 0), _vec(0, 1, 0))
        # Camera matrices should be updated
        assert d.camera_position.x == 0 and d.camera_position.z == 5

    @pytest.mark.asyncio
    async def test_get_layer_info(self):
        d = self._display()
        await d.create_layer("layer1", depth=0.3)
        info = d.get_layer_info("layer1")
        assert info is not None
        assert info["layer_id"] == "layer1"

    def test_get_layer_info_missing(self):
        d = self._display()
        assert d.get_layer_info("missing") is None

    def test_performance_stats(self):
        d = self._display()
        stats = d.get_performance_stats()
        assert "layer_count" in stats


# ===========================================================================
# 10.  Physics  (physics/physics_manager.py)
# ===========================================================================


class TestPhysicsTypes:
    def test_physics_properties_defaults(self):
        from src.asi_build.holographic.physics.physics_manager import PhysicsProperties

        pp = PhysicsProperties()
        assert pp.mass == 1.0
        assert pp.restitution == 0.5

    def test_force_is_active(self):
        from src.asi_build.holographic.physics.physics_manager import Force, ForceType

        f = Force(
            force_id="f1",
            force_type=ForceType.GRAVITY,
            magnitude=_vec(0, -9.81, 0),
            point_of_application=_vec(0, 0, 0),
            duration=1.0,
            start_time=100.0,
        )
        assert f.is_active(100.5)
        assert not f.is_active(200.0)

    def test_force_infinite_duration(self):
        from src.asi_build.holographic.physics.physics_manager import Force, ForceType

        f = Force(
            force_id="f2",
            force_type=ForceType.GRAVITY,
            magnitude=_vec(0, -9.81, 0),
            point_of_application=_vec(0, 0, 0),
            start_time=0.0,
        )
        # Override start_time to avoid auto time.time()
        f.start_time = 0.0
        assert f.is_active(999999.0)

    def test_physics_body_type_enum(self):
        from src.asi_build.holographic.physics.physics_manager import PhysicsBodyType

        assert PhysicsBodyType.DYNAMIC.value == "dynamic"
        assert PhysicsBodyType.STATIC.value == "static"


class TestSpatialGrid:
    def test_insert_and_potential_pairs(self):
        from src.asi_build.holographic.physics.physics_manager import SpatialGrid

        sg = SpatialGrid(cell_size=2.0)
        sg.insert("a", _vec(0, 0, 0))
        sg.insert("b", _vec(0.5, 0, 0))
        sg.insert("c", _vec(100, 100, 100))
        pairs = sg.get_potential_pairs()
        # a and b should be in same cell
        assert any(("a" in p and "b" in p) for p in pairs)

    def test_clear(self):
        from src.asi_build.holographic.physics.physics_manager import SpatialGrid

        sg = SpatialGrid()
        sg.insert("a", _vec(0, 0, 0))
        sg.clear()
        assert len(sg.get_potential_pairs()) == 0


class TestQuantumSimulator:
    def test_quantum_simulator_init(self):
        from src.asi_build.holographic.physics.physics_manager import QuantumSimulator

        qs = QuantumSimulator(config={})
        assert qs.quantum_states == {}

    def test_add_and_entangle(self):
        from src.asi_build.holographic.physics.physics_manager import QuantumSimulator

        qs = QuantumSimulator(config={})
        qs.add_quantum_body("a")
        qs.add_quantum_body("b")
        qs.entangle_bodies("a", "b")
        assert ("a", "b") in qs.entanglement_pairs

    def test_evolve(self):
        from src.asi_build.holographic.physics.physics_manager import QuantumSimulator

        qs = QuantumSimulator(config={})
        qs.add_quantum_body("a")
        qs.evolve_quantum_states(0.016)  # Should not crash


class TestPhysicsManagerBasic:
    """Test HolographicPhysicsManager without calling initialize() (avoids missing sub-modules)."""

    def _mgr(self):
        from src.asi_build.holographic.physics.physics_manager import HolographicPhysicsManager

        return HolographicPhysicsManager(config={})

    def test_creation(self):
        mgr = self._mgr()
        assert mgr.gravity.y == pytest.approx(-9.81)
        assert mgr.simulation_active is False

    def test_set_gravity(self):
        mgr = self._mgr()
        mgr.set_gravity(_vec(0, -1.62, 0))  # Moon gravity
        assert mgr.gravity.y == pytest.approx(-1.62)

    def test_set_electromagnetic_field(self):
        mgr = self._mgr()
        mgr.set_electromagnetic_field(_vec(1, 0, 0))
        assert mgr.electromagnetic_field.x == 1.0

    def test_get_physics_body_missing(self):
        mgr = self._mgr()
        assert mgr.get_physics_body("nonexistent") is None

    def test_collision_events_empty(self):
        mgr = self._mgr()
        assert mgr.get_collision_events() == []

    @pytest.mark.asyncio
    async def test_add_and_get_body(self):
        from src.asi_build.holographic.physics.physics_manager import PhysicsBodyType

        mgr = self._mgr()
        result = await mgr.add_physics_body("box1", PhysicsBodyType.DYNAMIC, _vec(0, 5, 0))
        assert result is True
        body = mgr.get_physics_body("box1")
        assert body is not None
        assert body.position.y == 5.0

    @pytest.mark.asyncio
    async def test_add_duplicate_body(self):
        from src.asi_build.holographic.physics.physics_manager import PhysicsBodyType

        mgr = self._mgr()
        await mgr.add_physics_body("box1", PhysicsBodyType.DYNAMIC, _vec(0, 0, 0))
        result = await mgr.add_physics_body("box1", PhysicsBodyType.DYNAMIC, _vec(1, 1, 1))
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_body(self):
        from src.asi_build.holographic.physics.physics_manager import PhysicsBodyType

        mgr = self._mgr()
        await mgr.add_physics_body("box1", PhysicsBodyType.DYNAMIC, _vec(0, 0, 0))
        assert await mgr.remove_physics_body("box1")
        assert mgr.get_physics_body("box1") is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self):
        mgr = self._mgr()
        assert not await mgr.remove_physics_body("nope")

    @pytest.mark.asyncio
    async def test_apply_force(self):
        from src.asi_build.holographic.physics.physics_manager import PhysicsBodyType

        mgr = self._mgr()
        await mgr.add_physics_body("box1", PhysicsBodyType.DYNAMIC, _vec(0, 0, 0))
        fid = await mgr.apply_force("box1", _vec(10, 0, 0))
        assert fid != ""
        assert len(mgr.get_physics_body("box1").forces) == 1

    @pytest.mark.asyncio
    async def test_apply_force_missing_body(self):
        mgr = self._mgr()
        fid = await mgr.apply_force("nope", _vec(10, 0, 0))
        assert fid == ""

    @pytest.mark.asyncio
    async def test_add_constraint(self):
        from src.asi_build.holographic.physics.physics_manager import PhysicsBodyType

        mgr = self._mgr()
        await mgr.add_physics_body("a", PhysicsBodyType.DYNAMIC, _vec(0, 0, 0))
        await mgr.add_physics_body("b", PhysicsBodyType.DYNAMIC, _vec(1, 0, 0))
        cid = await mgr.add_constraint("spring", "a", "b", {"stiffness": 100})
        assert cid != ""
        assert cid in mgr.constraints

    def test_performance_stats(self):
        mgr = self._mgr()
        stats = mgr.get_performance_stats()
        assert "physics_bodies" in stats


# ===========================================================================
# 11.  SpatialAudioManager  (audio/spatial_audio_manager.py)
# ===========================================================================


class TestSpatialAudioManager:
    def _mgr(self):
        from src.asi_build.holographic.audio.spatial_audio_manager import SpatialAudioManager
        from src.asi_build.holographic.core.config import AudioConfig

        return SpatialAudioManager(AudioConfig())

    def test_creation(self):
        mgr = self._mgr()
        assert mgr.master_volume == 1.0

    def test_set_master_volume(self):
        mgr = self._mgr()
        mgr.set_master_volume(0.5)
        assert mgr.master_volume == 0.5

    @pytest.mark.asyncio
    async def test_set_listener_position(self):
        mgr = self._mgr()
        await mgr.set_listener_position(_vec(1, 2, 3))
        assert mgr.listener.position.x == 1.0

    @pytest.mark.asyncio
    async def test_add_audio_source(self):
        from src.asi_build.holographic.audio.spatial_audio_manager import AudioSourceType

        mgr = self._mgr()
        audio = np.zeros(48000, dtype=np.float32)
        result = await mgr.add_audio_source("src1", AudioSourceType.POINT, _vec(0, 0, 0), audio)
        assert result is True
        assert "src1" in mgr.get_audio_sources()

    @pytest.mark.asyncio
    async def test_remove_audio_source(self):
        from src.asi_build.holographic.audio.spatial_audio_manager import AudioSourceType

        mgr = self._mgr()
        audio = np.zeros(48000, dtype=np.float32)
        await mgr.add_audio_source("src1", AudioSourceType.POINT, _vec(0, 0, 0), audio)
        assert await mgr.remove_audio_source("src1")
        assert "src1" not in mgr.get_audio_sources()

    @pytest.mark.asyncio
    async def test_remove_nonexistent_source(self):
        mgr = self._mgr()
        assert not await mgr.remove_audio_source("nope")

    @pytest.mark.asyncio
    async def test_add_reverb_zone(self):
        mgr = self._mgr()
        result = await mgr.add_reverb_zone("zone1", _vec(0, 0, 0), _vec(10, 10, 10))
        assert result is True

    @pytest.mark.asyncio
    async def test_set_source_position(self):
        from src.asi_build.holographic.audio.spatial_audio_manager import AudioSourceType

        mgr = self._mgr()
        audio = np.zeros(48000, dtype=np.float32)
        await mgr.add_audio_source("src1", AudioSourceType.POINT, _vec(0, 0, 0), audio)
        assert await mgr.set_source_position("src1", _vec(5, 5, 5))

    def test_performance_stats(self):
        mgr = self._mgr()
        stats = mgr.get_performance_stats()
        assert "audio_sources" in stats


# ===========================================================================
# 12.  HandTracker types  (gestures/hand_tracker.py)
# ===========================================================================


def _ensure_cv2_mock():
    """Mock cv2 before any gesture module import."""
    if "cv2" not in sys.modules or not isinstance(sys.modules["cv2"], MagicMock):
        mock_cv2 = MagicMock()
        mock_cv2.ORB_create.return_value = MagicMock()
        mock_cv2.BFMatcher.return_value = MagicMock()
        mock_cv2.COLOR_BGR2GRAY = 6
        mock_cv2.NORM_HAMMING = 6
        mock_cv2.RANSAC = 8
        sys.modules["cv2"] = mock_cv2
    # Force reload of gesture module so it picks up the mock
    import importlib

    if "src.asi_build.holographic.gestures.hand_tracker" in sys.modules:
        importlib.reload(sys.modules["src.asi_build.holographic.gestures.hand_tracker"])
    if "src.asi_build.holographic.gestures" in sys.modules:
        importlib.reload(sys.modules["src.asi_build.holographic.gestures"])


class TestHandTrackerTypes:
    """Test gesture data types (cv2 mocked at module level)."""

    @classmethod
    def setup_class(cls):
        _ensure_cv2_mock()

    def test_joint3d(self):
        from src.asi_build.holographic.gestures.hand_tracker import Joint3D

        j = Joint3D(position=_vec(1, 2, 3), confidence=0.95)
        assert j.position.x == 1.0

    def test_finger_tip_position(self):
        from src.asi_build.holographic.gestures.hand_tracker import Finger, FingerType, Joint3D

        joints = [
            Joint3D(position=_vec(0, 0, 0), confidence=1.0),
            Joint3D(position=_vec(1, 0, 0), confidence=1.0),
            Joint3D(position=_vec(2, 0, 0), confidence=1.0),
            Joint3D(position=_vec(3, 0, 0), confidence=1.0),
        ]
        f = Finger(finger_type=FingerType.INDEX, joints=joints)
        tip = f.tip_position
        assert tip.x == 3.0

    def test_finger_length(self):
        from src.asi_build.holographic.gestures.hand_tracker import Finger, FingerType, Joint3D

        joints = [
            Joint3D(position=_vec(0, 0, 0), confidence=1.0),
            Joint3D(position=_vec(1, 0, 0), confidence=1.0),
            Joint3D(position=_vec(2, 0, 0), confidence=1.0),
            Joint3D(position=_vec(3, 0, 0), confidence=1.0),
        ]
        f = Finger(finger_type=FingerType.INDEX, joints=joints)
        assert abs(f.length - 3.0) < 1e-6

    def test_hand_landmarks_fingertips(self):
        from src.asi_build.holographic.gestures.hand_tracker import (
            Finger,
            FingerType,
            HandLandmarks,
            HandSide,
            Joint3D,
        )

        def _make_finger(ft, tip_x):
            joints = [
                Joint3D(position=_vec(0, 0, 0), confidence=1.0),
                Joint3D(position=_vec(tip_x * 0.33, 0, 0), confidence=1.0),
                Joint3D(position=_vec(tip_x * 0.66, 0, 0), confidence=1.0),
                Joint3D(position=_vec(tip_x, 0, 0), confidence=1.0),
            ]
            return Finger(finger_type=ft, joints=joints)

        fingers = {
            FingerType.THUMB: _make_finger(FingerType.THUMB, 1),
            FingerType.INDEX: _make_finger(FingerType.INDEX, 2),
            FingerType.MIDDLE: _make_finger(FingerType.MIDDLE, 3),
            FingerType.RING: _make_finger(FingerType.RING, 4),
            FingerType.PINKY: _make_finger(FingerType.PINKY, 5),
        }
        hl = HandLandmarks(
            hand_id="right_0",
            side=HandSide.RIGHT,
            wrist=Joint3D(position=_vec(0, 0, 0), confidence=1.0),
            fingers=fingers,
            palm_center=_vec(0, 0, 0),
            palm_normal=_vec(0, 0, 1),
            confidence=0.9,
            timestamp=time.time(),
        )
        tips = hl.fingertips
        assert FingerType.INDEX in tips
        assert tips[FingerType.INDEX].x == 2.0

    def test_hand_side_enum(self):
        from src.asi_build.holographic.gestures.hand_tracker import HandSide

        assert HandSide.LEFT.value == "left"
        assert HandSide.RIGHT.value == "right"

    def test_finger_type_enum(self):
        from src.asi_build.holographic.gestures.hand_tracker import FingerType

        assert len(FingerType) == 5


# ===========================================================================
# 13.  MixedRealityEngine  (ar_overlay/mixed_reality_engine.py)
# ===========================================================================


class TestMixedRealityEngine:
    """Test MRE without cv2 by mocking it."""

    @classmethod
    def setup_class(cls):
        _ensure_cv2_mock()

    def _engine(self):
        _ensure_cv2_mock()
        from src.asi_build.holographic.ar_overlay.mixed_reality_engine import MixedRealityEngine

        return MixedRealityEngine(config={})

    def test_creation(self):
        engine = self._engine()
        assert engine.tracking_active is False

    @pytest.mark.asyncio
    async def test_add_virtual_object(self):
        engine = self._engine()
        result = await engine.add_virtual_object("cube1", "cube", _vec(0, 1, 0))
        assert result is True

    @pytest.mark.asyncio
    async def test_add_duplicate_virtual_object_overwrites(self):
        engine = self._engine()
        await engine.add_virtual_object("cube1", "cube", _vec(0, 0, 0))
        result = await engine.add_virtual_object("cube1", "cube", _vec(1, 1, 1))
        # MRE allows overwriting existing objects
        assert result is True
        assert len(engine.get_virtual_objects()) == 1

    @pytest.mark.asyncio
    async def test_remove_virtual_object(self):
        engine = self._engine()
        await engine.add_virtual_object("cube1", "cube", _vec(0, 0, 0))
        assert await engine.remove_virtual_object("cube1")
        assert "cube1" not in engine.get_virtual_objects()

    @pytest.mark.asyncio
    async def test_remove_nonexistent_object(self):
        engine = self._engine()
        assert not await engine.remove_virtual_object("nope")

    @pytest.mark.asyncio
    async def test_get_virtual_objects(self):
        engine = self._engine()
        await engine.add_virtual_object("a", "sphere", _vec(0, 0, 0))
        await engine.add_virtual_object("b", "cube", _vec(1, 1, 1))
        objs = engine.get_virtual_objects()
        assert len(objs) == 2

    @pytest.mark.asyncio
    async def test_create_spatial_anchor(self):
        engine = self._engine()
        result = await engine.create_spatial_anchor("anchor1", _vec(0, 0, 0))
        assert result is True

    @pytest.mark.asyncio
    async def test_create_duplicate_anchor_overwrites(self):
        engine = self._engine()
        await engine.create_spatial_anchor("anchor1", _vec(0, 0, 0))
        result = await engine.create_spatial_anchor("anchor1", _vec(1, 1, 1))
        # MRE allows overwriting existing anchors
        assert result is True
        assert len(engine.get_spatial_anchors()) == 1

    def test_set_reality_mode(self):
        from src.asi_build.holographic.ar_overlay.mixed_reality_engine import RealityMode

        engine = self._engine()
        engine.set_reality_mode(RealityMode.MIXED_REALITY)
        assert engine.reality_mode == RealityMode.MIXED_REALITY

    def test_get_camera_pose(self):
        engine = self._engine()
        pose = engine.get_camera_pose()
        assert hasattr(pose, "position")

    def test_performance_stats(self):
        engine = self._engine()
        stats = engine.get_performance_stats()
        assert "virtual_objects" in stats
        assert "spatial_anchors" in stats

    def test_reality_mode_enum(self):
        _ensure_cv2_mock()
        from src.asi_build.holographic.ar_overlay.mixed_reality_engine import RealityMode

        assert RealityMode.AR_OVERLAY.value == "ar_overlay"
        assert RealityMode.PURE_VR.value == "pure_vr"

    def test_tracking_method_enum(self):
        _ensure_cv2_mock()
        from src.asi_build.holographic.ar_overlay.mixed_reality_engine import TrackingMethod

        assert TrackingMethod.SLAM.value == "slam"


# ===========================================================================
# 14.  TelepresenceManager  (telepresence/telepresence_manager.py)
# ===========================================================================


class TestTelepresenceManager:
    def _mock_websockets(self):
        """Mock websockets if not installed."""
        if "websockets" not in sys.modules or not isinstance(
            sys.modules.get("websockets"), MagicMock
        ):
            sys.modules["websockets"] = MagicMock()
            sys.modules["websockets.serve"] = MagicMock()

    def _mgr(self):
        self._mock_websockets()
        from src.asi_build.holographic.core.config import NetworkConfig
        from src.asi_build.holographic.telepresence.telepresence_manager import TelepresenceManager

        return TelepresenceManager(NetworkConfig())

    def test_creation(self):
        mgr = self._mgr()
        assert mgr.websocket_server is None

    def test_get_remote_users_empty(self):
        mgr = self._mgr()
        assert mgr.get_remote_users() == {}

    def test_get_shared_content_empty(self):
        mgr = self._mgr()
        assert mgr.get_shared_content() == {}

    def test_get_active_streams_empty(self):
        mgr = self._mgr()
        assert mgr.get_active_streams() == {}

    def test_add_event_handler(self):
        mgr = self._mgr()
        handler = lambda data: None
        mgr.add_event_handler("user_joined", handler)
        assert handler in mgr.event_handlers.get("user_joined", [])

    def test_remove_event_handler(self):
        mgr = self._mgr()
        handler = lambda data: None
        mgr.add_event_handler("user_joined", handler)
        mgr.remove_event_handler("user_joined", handler)
        assert handler not in mgr.event_handlers.get("user_joined", [])

    def test_performance_stats(self):
        mgr = self._mgr()
        stats = mgr.get_performance_stats()
        assert "connected_clients" in stats

    def test_presence_state_enum(self):
        self._mock_websockets()
        from src.asi_build.holographic.telepresence.telepresence_manager import PresenceState

        assert PresenceState.ONLINE.value == "online"
        assert PresenceState.OFFLINE.value == "offline"


# ===========================================================================
# 15.  Module-level __init__ lazy loading
# ===========================================================================


class TestModuleLazyImport:
    def test_version(self):
        from src.asi_build.holographic import __version__

        assert __version__ == "1.0.0"

    def test_spatial_math_import(self):
        from src.asi_build.holographic import SpatialMath

        assert hasattr(SpatialMath, "distance_3d")

    def test_holographic_config_import(self):
        from src.asi_build.holographic import HolographicConfig

        cfg = HolographicConfig()
        assert cfg.validate_config()

    def test_bad_attribute_raises(self):
        import src.asi_build.holographic as holo

        with pytest.raises(AttributeError):
            _ = holo.NonexistentClass

    def test_all_exports(self):
        from src.asi_build.holographic import __all__

        assert "SpatialMath" in __all__
        assert "HolographicEngine" in __all__


# ===========================================================================
# 16.  HolographicBase abstract interface
# ===========================================================================


class TestHolographicBase:
    def test_cannot_instantiate_directly(self):
        from src.asi_build.holographic.core.base import HolographicBase

        with pytest.raises(TypeError):
            HolographicBase()

    def test_concrete_subclass(self):
        from src.asi_build.holographic.core.base import HolographicBase

        class ConcreteHolo(HolographicBase):
            async def initialize(self) -> bool:
                self.initialized = True
                return True

            async def shutdown(self):
                self.initialized = False

        obj = ConcreteHolo("test")
        assert obj.name == "test"
        assert obj.enabled is True
        assert obj.initialized is False

    def test_enable_disable(self):
        from src.asi_build.holographic.core.base import HolographicBase

        class ConcreteHolo(HolographicBase):
            async def initialize(self) -> bool:
                return True

            async def shutdown(self):
                pass

        obj = ConcreteHolo()
        obj.disable()
        assert not obj.is_enabled()
        obj.enable()
        assert obj.is_enabled()


# ===========================================================================
# 17.  EventSubscriber
# ===========================================================================


class TestEventSubscriber:
    def test_valid_subscriber(self):
        from src.asi_build.holographic.core.event_system import EventPriority, EventSubscriber

        cb = lambda data: None
        sub = EventSubscriber(cb, "test_event", EventPriority.HIGH)
        assert sub.is_valid()
        assert sub.callback is cb

    def test_subscriber_priority(self):
        from src.asi_build.holographic.core.event_system import EventPriority, EventSubscriber

        sub = EventSubscriber(lambda d: None, "ev", EventPriority.CRITICAL)
        assert sub.priority == EventPriority.CRITICAL


# ===========================================================================
# 18.  Integration: config ↔ engine defaults
# ===========================================================================


class TestConfigEngineIntegration:
    def test_engine_respects_fps_from_config(self):
        from src.asi_build.holographic.core.config import HolographicConfig
        from src.asi_build.holographic.core.engine import HolographicEngine

        cfg = HolographicConfig()
        cfg.performance.max_fps = 90.0
        engine = HolographicEngine(config=cfg)
        assert engine.target_fps == 90.0
        assert abs(engine.frame_time - 1.0 / 90.0) < 1e-6
