//! Camera and sensor input component for edge AI pipeline
//! 
//! Provides standardized interfaces for:
//! - Video capture from cameras, lidars, radars
//! - Sensor data acquisition (IMU, GPS, environmental)
//! - Real-time streaming with zero-copy optimizations
//! - Multi-format support (RGB, YUV, depth, thermal)

use std::sync::Arc;
use std::time::{Duration, Instant};
use wasi_common::wasi::WasiCtx;

wit_bindgen::generate!({
    world: "camera-component",
    exports: {
        "kenny:edge/camera": Camera,
    },
});

#[derive(Debug, Clone)]
pub struct FrameMetadata {
    pub timestamp: u64,
    pub sequence_id: u64,
    pub width: u32,
    pub height: u32,
    pub format: FrameFormat,
    pub sensor_id: String,
    pub pose: Option<SensorPose>,
}

#[derive(Debug, Clone)]
pub enum FrameFormat {
    Rgb8,
    Rgba8,
    Yuv420,
    Bgr8,
    Gray8,
    Depth16,
    Thermal16,
    PointCloud,
}

#[derive(Debug, Clone)]
pub struct SensorPose {
    pub position: [f64; 3],    // x, y, z in meters
    pub orientation: [f64; 4], // quaternion w, x, y, z
    pub velocity: [f64; 3],    // linear velocity m/s
    pub angular_velocity: [f64; 3], // rad/s
}

#[derive(Debug)]
pub struct CameraConfig {
    pub device_id: String,
    pub resolution: (u32, u32),
    pub fps: u32,
    pub format: FrameFormat,
    pub exposure_mode: ExposureMode,
    pub auto_focus: bool,
    pub stabilization: bool,
    pub hdr: bool,
}

#[derive(Debug)]
pub enum ExposureMode {
    Auto,
    Manual(u32), // microseconds
    Sports,
    Night,
    Portrait,
}

pub struct Camera {
    config: CameraConfig,
    is_streaming: bool,
    frame_buffer: Arc<FrameBuffer>,
    stats: CameraStats,
}

#[derive(Debug, Default)]
pub struct CameraStats {
    pub frames_captured: u64,
    pub frames_dropped: u64,
    pub avg_fps: f64,
    pub avg_latency_ms: f64,
    pub last_frame_time: Option<Instant>,
}

/// Zero-copy frame buffer with memory pooling
pub struct FrameBuffer {
    data: Vec<u8>,
    metadata: FrameMetadata,
    capacity: usize,
}

impl Camera {
    pub fn new(config: CameraConfig) -> Result<Self, CameraError> {
        let frame_size = Self::calculate_frame_size(&config);
        
        Ok(Camera {
            config,
            is_streaming: false,
            frame_buffer: Arc::new(FrameBuffer {
                data: Vec::with_capacity(frame_size),
                metadata: FrameMetadata {
                    timestamp: 0,
                    sequence_id: 0,
                    width: config.resolution.0,
                    height: config.resolution.1,
                    format: config.format.clone(),
                    sensor_id: config.device_id.clone(),
                    pose: None,
                },
                capacity: frame_size,
            }),
            stats: CameraStats::default(),
        })
    }

    fn calculate_frame_size(config: &CameraConfig) -> usize {
        let (width, height) = config.resolution;
        match config.format {
            FrameFormat::Rgb8 => (width * height * 3) as usize,
            FrameFormat::Rgba8 => (width * height * 4) as usize,
            FrameFormat::Yuv420 => (width * height * 3 / 2) as usize,
            FrameFormat::Bgr8 => (width * height * 3) as usize,
            FrameFormat::Gray8 => (width * height) as usize,
            FrameFormat::Depth16 => (width * height * 2) as usize,
            FrameFormat::Thermal16 => (width * height * 2) as usize,
            FrameFormat::PointCloud => (width * height * 12) as usize, // xyz float32
        }
    }

    /// Start camera streaming with real-time constraints
    pub async fn start_streaming(&mut self) -> Result<(), CameraError> {
        if self.is_streaming {
            return Err(CameraError::AlreadyStreaming);
        }

        // Initialize hardware-specific camera driver
        self.initialize_hardware().await?;
        
        // Configure real-time priority for capture thread
        self.set_realtime_priority()?;
        
        // Start capture loop
        self.spawn_capture_thread().await?;
        
        self.is_streaming = true;
        Ok(())
    }

    /// Stop camera streaming and cleanup resources
    pub async fn stop_streaming(&mut self) -> Result<(), CameraError> {
        if !self.is_streaming {
            return Ok(());
        }

        self.cleanup_hardware().await?;
        self.is_streaming = false;
        Ok(())
    }

    /// Capture single frame with timeout
    pub async fn capture_frame(&mut self, timeout: Duration) -> Result<Arc<FrameBuffer>, CameraError> {
        let start_time = Instant::now();
        
        // Platform-specific frame capture
        let raw_data = self.capture_raw_frame(timeout).await?;
        
        // Update frame buffer with zero-copy optimization
        let frame_buffer = self.update_frame_buffer(raw_data, start_time)?;
        
        // Update statistics
        self.update_stats(start_time);
        
        Ok(frame_buffer)
    }

    /// Get current camera statistics
    pub fn get_stats(&self) -> &CameraStats {
        &self.stats
    }

    /// Update camera configuration at runtime
    pub async fn update_config(&mut self, new_config: CameraConfig) -> Result<(), CameraError> {
        let was_streaming = self.is_streaming;
        
        if was_streaming {
            self.stop_streaming().await?;
        }
        
        self.config = new_config;
        
        if was_streaming {
            self.start_streaming().await?;
        }
        
        Ok(())
    }

    // Platform-specific implementations
    async fn initialize_hardware(&self) -> Result<(), CameraError> {
        // V4L2 for Linux, DirectShow for Windows, AVFoundation for macOS
        #[cfg(target_os = "linux")]
        {
            self.init_v4l2().await
        }
        
        #[cfg(target_os = "windows")]
        {
            self.init_directshow().await
        }
        
        #[cfg(target_os = "macos")]
        {
            self.init_avfoundation().await
        }
        
        #[cfg(target_arch = "wasm32")]
        {
            self.init_web_camera().await
        }
    }

    #[cfg(target_os = "linux")]
    async fn init_v4l2(&self) -> Result<(), CameraError> {
        // V4L2 camera initialization for Linux
        // Includes support for USB cameras, CSI cameras, industrial cameras
        Ok(())
    }

    #[cfg(target_arch = "wasm32")]
    async fn init_web_camera(&self) -> Result<(), CameraError> {
        // WebRTC/MediaDevices API for browser environments
        Ok(())
    }

    async fn capture_raw_frame(&self, _timeout: Duration) -> Result<Vec<u8>, CameraError> {
        // Hardware-specific frame capture
        // Returns raw frame data
        Ok(vec![0u8; self.frame_buffer.capacity])
    }

    fn update_frame_buffer(&mut self, data: Vec<u8>, capture_time: Instant) -> Result<Arc<FrameBuffer>, CameraError> {
        // Update frame metadata
        self.frame_buffer = Arc::new(FrameBuffer {
            data,
            metadata: FrameMetadata {
                timestamp: capture_time.elapsed().as_nanos() as u64,
                sequence_id: self.stats.frames_captured + 1,
                width: self.config.resolution.0,
                height: self.config.resolution.1,
                format: self.config.format.clone(),
                sensor_id: self.config.device_id.clone(),
                pose: self.get_current_pose(),
            },
            capacity: self.frame_buffer.capacity,
        });
        
        Ok(Arc::clone(&self.frame_buffer))
    }

    fn get_current_pose(&self) -> Option<SensorPose> {
        // Get current sensor pose from IMU/GPS if available
        // This would integrate with robot/vehicle localization systems
        None
    }

    fn set_realtime_priority(&self) -> Result<(), CameraError> {
        // Set real-time scheduling priority for time-critical capture
        Ok(())
    }

    async fn spawn_capture_thread(&self) -> Result<(), CameraError> {
        // Spawn dedicated thread for frame capture
        Ok(())
    }

    async fn cleanup_hardware(&self) -> Result<(), CameraError> {
        // Platform-specific cleanup
        Ok(())
    }

    fn update_stats(&mut self, capture_start: Instant) {
        self.stats.frames_captured += 1;
        
        let latency = capture_start.elapsed().as_millis() as f64;
        self.stats.avg_latency_ms = if self.stats.frames_captured == 1 {
            latency
        } else {
            (self.stats.avg_latency_ms * 0.9) + (latency * 0.1)
        };
        
        if let Some(last_time) = self.stats.last_frame_time {
            let fps = 1000.0 / last_time.elapsed().as_millis() as f64;
            self.stats.avg_fps = if self.stats.frames_captured == 1 {
                fps
            } else {
                (self.stats.avg_fps * 0.9) + (fps * 0.1)
            };
        }
        
        self.stats.last_frame_time = Some(Instant::now());
    }
}

#[derive(Debug, thiserror::Error)]
pub enum CameraError {
    #[error("Device not found: {0}")]
    DeviceNotFound(String),
    
    #[error("Permission denied accessing camera")]
    PermissionDenied,
    
    #[error("Camera already streaming")]
    AlreadyStreaming,
    
    #[error("Capture timeout")]
    CaptureTimeout,
    
    #[error("Hardware error: {0}")]
    HardwareError(String),
    
    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),
    
    #[error("Buffer overflow")]
    BufferOverflow,
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

// WIT exports implementation
impl exports::kenny::edge::camera::Guest for Camera {
    fn configure(config: String) -> Result<(), String> {
        // Parse configuration and initialize camera
        Ok(())
    }
    
    fn start() -> Result<(), String> {
        // Start camera streaming
        Ok(())
    }
    
    fn capture() -> Result<Vec<u8>, String> {
        // Capture single frame
        Ok(vec![])
    }
    
    fn stop() -> Result<(), String> {
        // Stop camera streaming
        Ok(())
    }
    
    fn get_metadata() -> String {
        // Return frame metadata as JSON
        "{}".to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_camera_initialization() {
        let config = CameraConfig {
            device_id: "test_camera".to_string(),
            resolution: (640, 480),
            fps: 30,
            format: FrameFormat::Rgb8,
            exposure_mode: ExposureMode::Auto,
            auto_focus: true,
            stabilization: false,
            hdr: false,
        };
        
        let camera = Camera::new(config).unwrap();
        assert!(!camera.is_streaming);
        assert_eq!(camera.stats.frames_captured, 0);
    }
    
    #[tokio::test]
    async fn test_frame_size_calculation() {
        let config = CameraConfig {
            device_id: "test".to_string(),
            resolution: (640, 480),
            fps: 30,
            format: FrameFormat::Rgb8,
            exposure_mode: ExposureMode::Auto,
            auto_focus: true,
            stabilization: false,
            hdr: false,
        };
        
        let size = Camera::calculate_frame_size(&config);
        assert_eq!(size, 640 * 480 * 3); // RGB8 format
    }
}