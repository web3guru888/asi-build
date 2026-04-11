"""
Holographic system configuration
"""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class DisplayConfig:
    """Display configuration"""

    resolution_x: int = 1920
    resolution_y: int = 1080
    resolution_z: int = 512  # Depth resolution
    refresh_rate: float = 60.0
    field_of_view: float = 110.0  # degrees
    interpupillary_distance: float = 64.0  # mm
    display_type: str = "volumetric"  # volumetric, light_field, holographic
    brightness: float = 1.0
    contrast: float = 1.0
    gamma: float = 2.2


@dataclass
class RenderingConfig:
    """Rendering configuration"""

    quality: str = "high"  # low, medium, high, ultra
    anti_aliasing: bool = True
    anisotropic_filtering: int = 16
    shadow_quality: str = "high"
    particle_count: int = 100000
    max_polygons: int = 10000000
    texture_resolution: int = 2048
    shader_quality: str = "high"
    physics_enabled: bool = True
    lighting_model: str = "pbr"  # pbr, blinn_phong, lambert


@dataclass
class GestureConfig:
    """Gesture recognition configuration"""

    enabled: bool = True
    sensitivity: float = 0.8
    hand_tracking: bool = True
    eye_tracking: bool = True
    body_tracking: bool = True
    voice_commands: bool = True
    gesture_threshold: float = 0.7
    interaction_distance: float = 2.0  # meters
    calibration_required: bool = True


@dataclass
class AudioConfig:
    """Spatial audio configuration"""

    enabled: bool = True
    sample_rate: int = 48000
    bit_depth: int = 24
    channels: int = 8  # Spatial audio channels
    reverb_enabled: bool = True
    doppler_effect: bool = True
    distance_attenuation: bool = True
    hrtf_enabled: bool = True  # Head-Related Transfer Function


@dataclass
class NetworkConfig:
    """Network configuration for remote holograms"""

    enabled: bool = True
    server_address: str = "localhost"
    server_port: int = 8080
    use_compression: bool = True
    compression_quality: float = 0.8
    encryption_enabled: bool = True
    max_bandwidth: int = 100  # Mbps
    latency_compensation: bool = True


@dataclass
class SecurityConfig:
    """Security configuration"""

    encryption_enabled: bool = True
    authentication_required: bool = True
    access_control_enabled: bool = True
    audit_logging: bool = True
    secure_storage: bool = True
    privacy_mode: bool = False
    data_retention_days: int = 30


@dataclass
class PerformanceConfig:
    """Performance optimization configuration"""

    max_fps: float = 120.0
    vsync_enabled: bool = True
    adaptive_quality: bool = True
    level_of_detail: bool = True
    occlusion_culling: bool = True
    frustum_culling: bool = True
    batch_rendering: bool = True
    multi_threading: bool = True
    gpu_acceleration: bool = True


class HolographicConfig:
    """Main holographic system configuration"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "holographic_config.json"
        self.config_dir = Path(__file__).parent.parent / "config"
        self.config_path = self.config_dir / self.config_file

        # Initialize with defaults
        self.display = DisplayConfig()
        self.rendering = RenderingConfig()
        self.gesture = GestureConfig()
        self.audio = AudioConfig()
        self.network = NetworkConfig()
        self.security = SecurityConfig()
        self.performance = PerformanceConfig()

        # Load configuration if file exists
        self.load_config()

    def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    data = json.load(f)

                    # Update configurations
                    if "display" in data:
                        self.display = DisplayConfig(**data["display"])
                    if "rendering" in data:
                        self.rendering = RenderingConfig(**data["rendering"])
                    if "gesture" in data:
                        self.gesture = GestureConfig(**data["gesture"])
                    if "audio" in data:
                        self.audio = AudioConfig(**data["audio"])
                    if "network" in data:
                        self.network = NetworkConfig(**data["network"])
                    if "security" in data:
                        self.security = SecurityConfig(**data["security"])
                    if "performance" in data:
                        self.performance = PerformanceConfig(**data["performance"])

                return True
        except Exception as e:
            print(f"Error loading config: {e}")
        return False

    def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)

            data = {
                "display": asdict(self.display),
                "rendering": asdict(self.rendering),
                "gesture": asdict(self.gesture),
                "audio": asdict(self.audio),
                "network": asdict(self.network),
                "security": asdict(self.security),
                "performance": asdict(self.performance),
            }

            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving config: {e}")
        return False

    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return {
            "display": asdict(self.display),
            "rendering": asdict(self.rendering),
            "gesture": asdict(self.gesture),
            "audio": asdict(self.audio),
            "network": asdict(self.network),
            "security": asdict(self.security),
            "performance": asdict(self.performance),
        }

    def update_config(self, section: str, updates: Dict[str, Any]) -> bool:
        """Update specific configuration section"""
        try:
            if section == "display":
                for key, value in updates.items():
                    if hasattr(self.display, key):
                        setattr(self.display, key, value)
            elif section == "rendering":
                for key, value in updates.items():
                    if hasattr(self.rendering, key):
                        setattr(self.rendering, key, value)
            elif section == "gesture":
                for key, value in updates.items():
                    if hasattr(self.gesture, key):
                        setattr(self.gesture, key, value)
            elif section == "audio":
                for key, value in updates.items():
                    if hasattr(self.audio, key):
                        setattr(self.audio, key, value)
            elif section == "network":
                for key, value in updates.items():
                    if hasattr(self.network, key):
                        setattr(self.network, key, value)
            elif section == "security":
                for key, value in updates.items():
                    if hasattr(self.security, key):
                        setattr(self.security, key, value)
            elif section == "performance":
                for key, value in updates.items():
                    if hasattr(self.performance, key):
                        setattr(self.performance, key, value)
            else:
                return False

            return True
        except Exception as e:
            print(f"Error updating config: {e}")
        return False

    def validate_config(self) -> bool:
        """Validate configuration values"""
        try:
            # Validate display config
            if self.display.resolution_x <= 0 or self.display.resolution_y <= 0:
                return False
            if self.display.refresh_rate <= 0 or self.display.refresh_rate > 500:
                return False
            if self.display.field_of_view <= 0 or self.display.field_of_view > 180:
                return False

            # Validate rendering config
            if self.rendering.quality not in ["low", "medium", "high", "ultra"]:
                return False
            if self.rendering.particle_count < 0:
                return False

            # Validate gesture config
            if self.gesture.sensitivity < 0 or self.gesture.sensitivity > 1:
                return False
            if self.gesture.gesture_threshold < 0 or self.gesture.gesture_threshold > 1:
                return False

            # Validate audio config
            if self.audio.sample_rate not in [44100, 48000, 96000, 192000]:
                return False
            if self.audio.bit_depth not in [16, 24, 32]:
                return False

            # Validate network config
            if self.network.server_port < 1 or self.network.server_port > 65535:
                return False
            if self.network.compression_quality < 0 or self.network.compression_quality > 1:
                return False

            # Validate performance config
            if self.performance.max_fps <= 0 or self.performance.max_fps > 1000:
                return False

            return True
        except Exception:
            return False

    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.display = DisplayConfig()
        self.rendering = RenderingConfig()
        self.gesture = GestureConfig()
        self.audio = AudioConfig()
        self.network = NetworkConfig()
        self.security = SecurityConfig()
        self.performance = PerformanceConfig()

    def get_quality_preset(self, preset: str) -> Dict[str, Any]:
        """Get quality preset configurations"""
        presets = {
            "low": {
                "rendering": {
                    "quality": "low",
                    "anti_aliasing": False,
                    "shadow_quality": "low",
                    "particle_count": 10000,
                    "texture_resolution": 512,
                },
                "performance": {"max_fps": 30.0, "adaptive_quality": True, "level_of_detail": True},
            },
            "medium": {
                "rendering": {
                    "quality": "medium",
                    "anti_aliasing": True,
                    "shadow_quality": "medium",
                    "particle_count": 50000,
                    "texture_resolution": 1024,
                },
                "performance": {"max_fps": 60.0, "adaptive_quality": True, "level_of_detail": True},
            },
            "high": {
                "rendering": {
                    "quality": "high",
                    "anti_aliasing": True,
                    "shadow_quality": "high",
                    "particle_count": 100000,
                    "texture_resolution": 2048,
                },
                "performance": {
                    "max_fps": 90.0,
                    "adaptive_quality": False,
                    "level_of_detail": True,
                },
            },
            "ultra": {
                "rendering": {
                    "quality": "ultra",
                    "anti_aliasing": True,
                    "shadow_quality": "ultra",
                    "particle_count": 200000,
                    "texture_resolution": 4096,
                },
                "performance": {
                    "max_fps": 120.0,
                    "adaptive_quality": False,
                    "level_of_detail": False,
                },
            },
        }

        return presets.get(preset, presets["high"])

    def apply_quality_preset(self, preset: str) -> bool:
        """Apply a quality preset"""
        try:
            preset_config = self.get_quality_preset(preset)

            for section, config in preset_config.items():
                if not self.update_config(section, config):
                    return False

            return True
        except Exception:
            return False
