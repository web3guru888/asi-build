"""
Spatial audio manager for immersive holographic experiences
"""

import asyncio
import logging
import time
import numpy as np
import threading
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import math

from ..core.base import (
    HolographicBase, 
    Vector3D, 
    Transform3D,
    HolographicPerformanceMonitor
)
from ..core.math_utils import SpatialMath
from ..core.config import AudioConfig

logger = logging.getLogger(__name__)

class AudioSourceType(Enum):
    """Types of audio sources"""
    POINT = "point"
    AMBIENT = "ambient"
    DIRECTIONAL = "directional"
    SPATIAL = "spatial"
    BINAURAL = "binaural"

@dataclass
class AudioSource:
    """3D audio source"""
    source_id: str
    source_type: AudioSourceType
    position: Vector3D
    orientation: Vector3D
    audio_data: np.ndarray
    sample_rate: int
    volume: float = 1.0
    pitch: float = 1.0
    doppler_enabled: bool = True
    reverb_enabled: bool = True
    occlusion_factor: float = 0.0
    distance_attenuation: bool = True
    max_distance: float = 100.0
    rolloff_factor: float = 1.0
    playing: bool = False
    looping: bool = False
    current_time: float = 0.0
    
    def __post_init__(self):
        if self.orientation is None:
            self.orientation = Vector3D(0, 0, -1)  # Forward direction

@dataclass
class AudioListener:
    """3D audio listener (user's ears)"""
    position: Vector3D
    orientation: Transform3D
    velocity: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 0))
    head_radius: float = 0.09  # Average head radius in meters
    ear_distance: float = 0.17  # Distance between ears
    hrtf_profile: str = "default"

@dataclass
class ReverbZone:
    """Reverb/acoustic zone"""
    zone_id: str
    center: Vector3D
    size: Vector3D
    reverb_time: float
    damping: float
    early_reflections: float
    late_reflections: float
    room_size: float

class SpatialAudioManager(HolographicBase):
    """
    Advanced spatial audio manager for holographic experiences
    Provides 3D positioned audio with HRTF, reverb, and Doppler effects
    """
    
    def __init__(self, config: AudioConfig):
        super().__init__("SpatialAudioManager")
        self.config = config
        self.performance_monitor = HolographicPerformanceMonitor()
        
        # Audio configuration
        self.sample_rate = config.sample_rate
        self.channels = config.channels
        self.bit_depth = config.bit_depth
        self.buffer_size = 1024
        
        # Audio sources and listener
        self.audio_sources: Dict[str, AudioSource] = {}
        self.listener = AudioListener(
            position=Vector3D(0, 0, 0),
            orientation=Transform3D()
        )
        
        # Reverb zones
        self.reverb_zones: Dict[str, ReverbZone] = {}
        
        # Audio processing
        self.audio_processor = None
        self.hrtf_processor = None
        self.reverb_processor = None
        self.audio_output = None
        
        # Processing pipeline
        self.processing_active = False
        self.audio_executor = ThreadPoolExecutor(max_workers=4)
        
        # Audio buffers
        self.output_buffer = np.zeros((self.buffer_size, self.channels), dtype=np.float32)
        self.temp_buffers = {}
        
        # Effects settings
        self.master_volume = 1.0
        self.doppler_factor = 1.0
        self.speed_of_sound = 343.0  # m/s at 20°C
        self.distance_model = "inverse"  # inverse, linear, exponential
        
        # HRTF database
        self.hrtf_database = {}
        self.hrtf_enabled = config.hrtf_enabled
        
        logger.info("SpatialAudioManager initialized")
    
    async def initialize(self) -> bool:
        """Initialize the spatial audio manager"""
        try:
            logger.info("Initializing SpatialAudioManager...")
            
            # Initialize audio processor
            await self._initialize_audio_processor()
            
            # Initialize HRTF
            if self.hrtf_enabled:
                await self._initialize_hrtf()
            
            # Initialize reverb
            if self.config.reverb_enabled:
                await self._initialize_reverb()
            
            # Initialize audio output
            await self._initialize_audio_output()
            
            # Create default reverb zone
            await self._create_default_reverb_zone()
            
            self.initialized = True
            logger.info("SpatialAudioManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SpatialAudioManager: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the spatial audio manager"""
        logger.info("Shutting down SpatialAudioManager...")
        
        # Stop processing
        await self.stop_processing()
        
        # Stop all audio sources
        for source in self.audio_sources.values():
            source.playing = False
        
        # Clear data
        self.audio_sources.clear()
        self.reverb_zones.clear()
        self.temp_buffers.clear()
        
        # Close audio output
        if self.audio_output:
            await self.audio_output.close()
        
        # Shutdown executor
        self.audio_executor.shutdown(wait=True)
        
        self.initialized = False
        logger.info("SpatialAudioManager shutdown complete")
    
    async def _initialize_audio_processor(self):
        """Initialize audio processing pipeline"""
        from .spatial_processor import SpatialAudioProcessor
        self.audio_processor = SpatialAudioProcessor(self.config)
        await self.audio_processor.initialize()
        logger.info("Audio processor initialized")
    
    async def _initialize_hrtf(self):
        """Initialize Head-Related Transfer Function processing"""
        try:
            # Load HRTF database
            await self._load_hrtf_database()
            
            # Initialize HRTF processor
            self.hrtf_processor = HRTFProcessor(self.hrtf_database)
            
            logger.info("HRTF processing initialized")
        except Exception as e:
            logger.error(f"Failed to initialize HRTF: {e}")
            self.hrtf_enabled = False
    
    async def _load_hrtf_database(self):
        """Load HRTF database"""
        # In practice, this would load actual HRTF measurements
        # For now, create a simple synthetic HRTF
        
        elevations = range(-40, 91, 10)  # -40° to 90°
        azimuths = range(0, 360, 5)     # 0° to 355°
        
        for elevation in elevations:
            for azimuth in azimuths:
                # Create synthetic HRTF (simplified)
                left_ear, right_ear = self._generate_synthetic_hrtf(elevation, azimuth)
                self.hrtf_database[(elevation, azimuth)] = {
                    'left': left_ear,
                    'right': right_ear
                }
        
        logger.info(f"Loaded HRTF database with {len(self.hrtf_database)} positions")
    
    def _generate_synthetic_hrtf(self, elevation: int, azimuth: int) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic HRTF for testing"""
        # Very simplified HRTF generation
        filter_length = 128
        
        # Calculate interaural time difference (ITD)
        azimuth_rad = math.radians(azimuth)
        itd_samples = int(self.listener.ear_distance * math.sin(azimuth_rad) / 
                         self.speed_of_sound * self.sample_rate)
        
        # Calculate interaural level difference (ILD)
        head_shadow = max(0.1, 1.0 - abs(math.sin(azimuth_rad)) * 0.3)
        
        # Create simple filters
        left_filter = np.zeros(filter_length)
        right_filter = np.zeros(filter_length)
        
        # Add delay for ITD
        if itd_samples > 0:
            right_filter[min(itd_samples, filter_length-1)] = head_shadow
            left_filter[0] = 1.0
        else:
            left_filter[min(abs(itd_samples), filter_length-1)] = head_shadow
            right_filter[0] = 1.0
        
        return left_filter, right_filter
    
    async def _initialize_reverb(self):
        """Initialize reverb processing"""
        self.reverb_processor = ReverbProcessor(self.config)
        await self.reverb_processor.initialize()
        logger.info("Reverb processing initialized")
    
    async def _initialize_audio_output(self):
        """Initialize audio output system"""
        try:
            # In practice, initialize actual audio output device
            self.audio_output = AudioOutput(self.config)
            await self.audio_output.initialize()
            logger.info("Audio output initialized")
        except Exception as e:
            logger.error(f"Failed to initialize audio output: {e}")
            # Continue without audio output for testing
            self.audio_output = None
    
    async def _create_default_reverb_zone(self):
        """Create default reverb zone"""
        await self.add_reverb_zone(
            "default",
            Vector3D(0, 0, 0),
            Vector3D(50, 50, 50),
            reverb_time=1.5,
            damping=0.5
        )
    
    async def start_processing(self):
        """Start audio processing"""
        if not self.initialized or self.processing_active:
            return
        
        logger.info("Starting audio processing...")
        self.processing_active = True
        
        # Start processing loop
        asyncio.create_task(self._processing_loop())
    
    async def stop_processing(self):
        """Stop audio processing"""
        logger.info("Stopping audio processing...")
        self.processing_active = False
    
    async def _processing_loop(self):
        """Main audio processing loop"""
        logger.info("Audio processing loop started")
        
        frame_time = self.buffer_size / self.sample_rate
        
        try:
            while self.processing_active:
                loop_start = time.time()
                self.performance_monitor.start_timer("audio_frame")
                
                # Process audio frame
                await self._process_audio_frame()
                
                frame_duration = self.performance_monitor.end_timer("audio_frame")
                
                # Maintain real-time processing
                elapsed = time.time() - loop_start
                if elapsed < frame_time:
                    await asyncio.sleep(frame_time - elapsed)
                
        except Exception as e:
            logger.error(f"Error in audio processing loop: {e}")
        finally:
            logger.info("Audio processing loop ended")
    
    async def _process_audio_frame(self):
        """Process single audio frame"""
        # Clear output buffer
        self.output_buffer.fill(0)
        
        # Process each active audio source
        for source in self.audio_sources.values():
            if source.playing and len(source.audio_data) > 0:
                await self._process_audio_source(source)
        
        # Apply master volume
        self.output_buffer *= self.master_volume
        
        # Send to audio output
        if self.audio_output:
            await self.audio_output.write_buffer(self.output_buffer)
    
    async def _process_audio_source(self, source: AudioSource):
        """Process single audio source"""
        try:
            # Get source audio data for current frame
            source_buffer = await self._get_source_audio(source)
            
            if source_buffer is None or len(source_buffer) == 0:
                return
            
            # Calculate 3D audio parameters
            audio_params = await self._calculate_3d_parameters(source)
            
            # Apply 3D audio processing
            processed_audio = await self._apply_3d_processing(source_buffer, audio_params)
            
            # Mix into output buffer
            await self._mix_audio(processed_audio, audio_params)
            
            # Update source time
            source.current_time += self.buffer_size / self.sample_rate
            
        except Exception as e:
            logger.error(f"Error processing audio source {source.source_id}: {e}")
    
    async def _get_source_audio(self, source: AudioSource) -> Optional[np.ndarray]:
        """Get audio data from source for current frame"""
        start_sample = int(source.current_time * source.sample_rate)
        end_sample = start_sample + self.buffer_size
        
        # Check if we've reached the end
        if start_sample >= len(source.audio_data):
            if source.looping:
                source.current_time = 0.0
                start_sample = 0
                end_sample = self.buffer_size
            else:
                source.playing = False
                return None
        
        # Extract audio data
        if end_sample > len(source.audio_data):
            if source.looping:
                # Wrap around
                part1 = source.audio_data[start_sample:]
                part2 = source.audio_data[:end_sample - len(source.audio_data)]
                audio_data = np.concatenate([part1, part2])
            else:
                # Pad with zeros
                audio_data = np.zeros(self.buffer_size)
                available_samples = len(source.audio_data) - start_sample
                audio_data[:available_samples] = source.audio_data[start_sample:]
        else:
            audio_data = source.audio_data[start_sample:end_sample]
        
        return audio_data
    
    async def _calculate_3d_parameters(self, source: AudioSource) -> Dict[str, Any]:
        """Calculate 3D audio parameters for source"""
        # Distance calculations
        distance = SpatialMath.distance_3d(source.position, self.listener.position)
        direction = (source.position - self.listener.position).normalize()
        
        # Distance attenuation
        if source.distance_attenuation:
            if self.distance_model == "inverse":
                attenuation = 1.0 / (1.0 + source.rolloff_factor * distance)
            elif self.distance_model == "linear":
                attenuation = max(0.0, 1.0 - distance / source.max_distance)
            else:  # exponential
                attenuation = math.exp(-source.rolloff_factor * distance)
        else:
            attenuation = 1.0
        
        # Doppler effect
        doppler_shift = 1.0
        if source.doppler_enabled and hasattr(source, 'velocity'):
            relative_velocity = SpatialMath.dot_product(
                source.velocity - self.listener.velocity, 
                direction
            )
            doppler_shift = (self.speed_of_sound - relative_velocity) / self.speed_of_sound
            doppler_shift = max(0.1, min(10.0, doppler_shift))  # Limit extreme values
        
        # Spatial position relative to listener
        listener_forward = Vector3D(0, 0, -1)  # Simplified
        listener_right = Vector3D(1, 0, 0)
        listener_up = Vector3D(0, 1, 0)
        
        # Convert to listener space
        relative_pos = source.position - self.listener.position
        local_x = SpatialMath.dot_product(relative_pos, listener_right)
        local_y = SpatialMath.dot_product(relative_pos, listener_up)
        local_z = SpatialMath.dot_product(relative_pos, listener_forward)
        
        # Calculate angles
        azimuth = math.atan2(local_x, -local_z)  # Horizontal angle
        elevation = math.atan2(local_y, math.sqrt(local_x**2 + local_z**2))  # Vertical angle
        
        # Convert to degrees
        azimuth_deg = math.degrees(azimuth)
        elevation_deg = math.degrees(elevation)
        
        return {
            'distance': distance,
            'attenuation': attenuation,
            'doppler_shift': doppler_shift,
            'azimuth': azimuth_deg,
            'elevation': elevation_deg,
            'occlusion': source.occlusion_factor,
            'volume': source.volume
        }
    
    async def _apply_3d_processing(self, audio_data: np.ndarray, 
                                 params: Dict[str, Any]) -> np.ndarray:
        """Apply 3D audio processing to audio data"""
        # Start with original audio
        processed = audio_data.copy()
        
        # Apply pitch shift for Doppler
        if abs(params['doppler_shift'] - 1.0) > 0.01:
            processed = await self._apply_pitch_shift(processed, params['doppler_shift'])
        
        # Apply HRTF if enabled
        if self.hrtf_enabled and self.hrtf_processor:
            processed = await self._apply_hrtf(processed, params)
        else:
            # Simple panning
            processed = await self._apply_simple_panning(processed, params)
        
        # Apply distance attenuation
        processed *= params['attenuation']
        
        # Apply volume
        processed *= params['volume']
        
        # Apply occlusion
        if params['occlusion'] > 0:
            processed = await self._apply_occlusion(processed, params['occlusion'])
        
        return processed
    
    async def _apply_hrtf(self, audio_data: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply HRTF processing"""
        if not self.hrtf_processor:
            return await self._apply_simple_panning(audio_data, params)
        
        return await self.hrtf_processor.process(
            audio_data, params['azimuth'], params['elevation']
        )
    
    async def _apply_simple_panning(self, audio_data: np.ndarray, 
                                  params: Dict[str, Any]) -> np.ndarray:
        """Apply simple stereo panning"""
        # Convert azimuth to pan value (-1 to 1)
        azimuth_rad = math.radians(params['azimuth'])
        pan = math.sin(azimuth_rad)
        
        # Calculate left and right gains
        left_gain = (1.0 - pan) * 0.5 + 0.5
        right_gain = (1.0 + pan) * 0.5 + 0.5
        
        # Create stereo output
        stereo_output = np.zeros((len(audio_data), 2))
        stereo_output[:, 0] = audio_data * left_gain
        stereo_output[:, 1] = audio_data * right_gain
        
        return stereo_output
    
    async def _apply_pitch_shift(self, audio_data: np.ndarray, shift_factor: float) -> np.ndarray:
        """Apply pitch shift for Doppler effect"""
        # Simple pitch shift using resampling
        # In practice, would use more sophisticated algorithms
        
        if abs(shift_factor - 1.0) < 0.01:
            return audio_data
        
        # Resample data
        original_length = len(audio_data)
        new_length = int(original_length / shift_factor)
        
        # Simple linear interpolation
        if new_length != original_length:
            indices = np.linspace(0, original_length - 1, new_length)
            resampled = np.interp(indices, np.arange(original_length), audio_data)
            
            # Pad or truncate to original length
            if new_length < original_length:
                result = np.zeros(original_length)
                result[:new_length] = resampled
            else:
                result = resampled[:original_length]
            
            return result
        
        return audio_data
    
    async def _apply_occlusion(self, audio_data: np.ndarray, occlusion_factor: float) -> np.ndarray:
        """Apply audio occlusion (muffling)"""
        if occlusion_factor <= 0:
            return audio_data
        
        # Simple low-pass filter for occlusion
        # In practice, would use proper filter design
        cutoff_freq = 1000 * (1.0 - occlusion_factor)  # Hz
        
        # Simple exponential smoothing as low-pass filter
        alpha = math.exp(-2 * math.pi * cutoff_freq / self.sample_rate)
        filtered = np.zeros_like(audio_data)
        
        if len(filtered) > 0:
            filtered[0] = audio_data[0]
            for i in range(1, len(audio_data)):
                filtered[i] = alpha * filtered[i-1] + (1-alpha) * audio_data[i]
        
        return filtered
    
    async def _mix_audio(self, processed_audio: np.ndarray, params: Dict[str, Any]):
        """Mix processed audio into output buffer"""
        if processed_audio.ndim == 1:
            # Mono to stereo
            stereo_audio = np.column_stack([processed_audio, processed_audio])
        else:
            stereo_audio = processed_audio
        
        # Ensure correct size
        mix_length = min(len(self.output_buffer), len(stereo_audio))
        
        # Mix with output buffer
        self.output_buffer[:mix_length] += stereo_audio[:mix_length]
    
    async def add_audio_source(self, source_id: str, source_type: AudioSourceType,
                             position: Vector3D, audio_data: np.ndarray,
                             sample_rate: int = None) -> bool:
        """Add audio source to the scene"""
        try:
            if source_id in self.audio_sources:
                logger.warning(f"Audio source {source_id} already exists")
                return False
            
            source = AudioSource(
                source_id=source_id,
                source_type=source_type,
                position=position,
                orientation=Vector3D(0, 0, -1),
                audio_data=audio_data,
                sample_rate=sample_rate or self.sample_rate
            )
            
            self.audio_sources[source_id] = source
            
            logger.info(f"Added audio source {source_id} at {position}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding audio source: {e}")
            return False
    
    async def remove_audio_source(self, source_id: str) -> bool:
        """Remove audio source"""
        if source_id in self.audio_sources:
            del self.audio_sources[source_id]
            logger.info(f"Removed audio source {source_id}")
            return True
        return False
    
    async def play_audio_source(self, source_id: str, looping: bool = False) -> bool:
        """Start playing audio source"""
        if source_id in self.audio_sources:
            source = self.audio_sources[source_id]
            source.playing = True
            source.looping = looping
            source.current_time = 0.0
            logger.info(f"Started playing audio source {source_id}")
            return True
        return False
    
    async def stop_audio_source(self, source_id: str) -> bool:
        """Stop playing audio source"""
        if source_id in self.audio_sources:
            source = self.audio_sources[source_id]
            source.playing = False
            logger.info(f"Stopped audio source {source_id}")
            return True
        return False
    
    async def set_source_position(self, source_id: str, position: Vector3D) -> bool:
        """Update audio source position"""
        if source_id in self.audio_sources:
            self.audio_sources[source_id].position = position
            return True
        return False
    
    async def set_listener_position(self, position: Vector3D, orientation: Transform3D = None):
        """Update listener position and orientation"""
        self.listener.position = position
        if orientation:
            self.listener.orientation = orientation
    
    async def add_reverb_zone(self, zone_id: str, center: Vector3D, size: Vector3D,
                            reverb_time: float = 1.5, damping: float = 0.5) -> bool:
        """Add reverb zone to the scene"""
        try:
            zone = ReverbZone(
                zone_id=zone_id,
                center=center,
                size=size,
                reverb_time=reverb_time,
                damping=damping,
                early_reflections=0.3,
                late_reflections=0.7,
                room_size=1.0
            )
            
            self.reverb_zones[zone_id] = zone
            
            logger.info(f"Added reverb zone {zone_id} at {center}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding reverb zone: {e}")
            return False
    
    def set_master_volume(self, volume: float):
        """Set master volume"""
        self.master_volume = max(0.0, min(2.0, volume))
    
    def get_audio_sources(self) -> Dict[str, AudioSource]:
        """Get all audio sources"""
        return self.audio_sources.copy()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "frame_time": self.performance_monitor.get_average_time("audio_frame"),
            "processing_fps": self.performance_monitor.get_fps("audio_frame"),
            "audio_sources": len(self.audio_sources),
            "active_sources": len([s for s in self.audio_sources.values() if s.playing]),
            "reverb_zones": len(self.reverb_zones),
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "buffer_size": self.buffer_size,
            "hrtf_enabled": self.hrtf_enabled,
            "processing_active": self.processing_active
        }

# Helper classes
class HRTFProcessor:
    """HRTF processing for binaural audio"""
    
    def __init__(self, hrtf_database: Dict):
        self.hrtf_database = hrtf_database
    
    async def process(self, audio_data: np.ndarray, azimuth: float, elevation: float) -> np.ndarray:
        """Apply HRTF processing"""
        # Find closest HRTF
        best_match = self._find_closest_hrtf(azimuth, elevation)
        
        if best_match:
            left_filter, right_filter = best_match
            
            # Apply HRTF filters (convolution)
            left_output = np.convolve(audio_data, left_filter, mode='same')
            right_output = np.convolve(audio_data, right_filter, mode='same')
            
            return np.column_stack([left_output, right_output])
        
        # Fallback to simple panning
        pan = math.sin(math.radians(azimuth))
        left_gain = (1.0 - pan) * 0.5 + 0.5
        right_gain = (1.0 + pan) * 0.5 + 0.5
        
        return np.column_stack([audio_data * left_gain, audio_data * right_gain])
    
    def _find_closest_hrtf(self, azimuth: float, elevation: float) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Find closest HRTF in database"""
        best_distance = float('inf')
        best_hrtf = None
        
        for (elev, azim), hrtf in self.hrtf_database.items():
            distance = math.sqrt((elevation - elev)**2 + (azimuth - azim)**2)
            if distance < best_distance:
                best_distance = distance
                best_hrtf = (hrtf['left'], hrtf['right'])
        
        return best_hrtf

class ReverbProcessor:
    """Reverb processor for spatial audio"""
    
    def __init__(self, config: AudioConfig):
        self.config = config
        self.reverb_lines = []
        self.initialized = False
    
    async def initialize(self):
        """Initialize reverb processor"""
        # Initialize delay lines for reverb
        self.initialized = True
    
    async def process(self, audio_data: np.ndarray, reverb_params: Dict[str, Any]) -> np.ndarray:
        """Apply reverb processing"""
        if not self.initialized:
            return audio_data
        
        # Simple reverb using delay and feedback
        reverb_time = reverb_params.get('reverb_time', 1.5)
        damping = reverb_params.get('damping', 0.5)
        
        # Create simple echo effect as reverb
        delay_samples = int(0.1 * self.config.sample_rate)  # 100ms delay
        
        if len(audio_data) > delay_samples:
            reverb_signal = np.zeros_like(audio_data)
            reverb_signal[delay_samples:] = audio_data[:-delay_samples] * 0.3
            
            return audio_data + reverb_signal * damping
        
        return audio_data

class AudioOutput:
    """Audio output system"""
    
    def __init__(self, config: AudioConfig):
        self.config = config
        self.initialized = False
    
    async def initialize(self):
        """Initialize audio output"""
        # In practice, initialize actual audio device
        self.initialized = True
    
    async def write_buffer(self, buffer: np.ndarray):
        """Write audio buffer to output"""
        # In practice, send to audio device
        pass
    
    async def close(self):
        """Close audio output"""
        self.initialized = False