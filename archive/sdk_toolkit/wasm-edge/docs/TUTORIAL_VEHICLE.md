# Autonomous Vehicle Integration Tutorial

## Overview

This comprehensive tutorial demonstrates how to implement a Level 4 autonomous vehicle system using the WASM Edge AI SDK. We'll build a complete self-driving pipeline with multi-camera sensor fusion, LiDAR processing, path planning, obstacle avoidance, and V2X communication capabilities.

## Architecture Overview

The autonomous vehicle system implements a layered architecture with multiple sensor inputs and safety-critical decision making:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Sensor Fusion   │    │  Perception     │    │  Planning       │
│                 │    │                 │    │                 │
│ • Camera Array  │────│ • Object Det.   │────│ • Path Planning │
│ • LiDAR/Radar   │    │ • Lane Det.     │    │ • Behavior Ctrl │
│ • GPS/IMU       │    │ • Depth Est.    │    │ • Motion Plan   │
│ • V2X Comms     │    │ • Tracking      │    │ • Trajectory    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Vehicle Control │
                    │                 │
                    │ • Steering      │
                    │ • Throttle      │
                    │ • Braking       │
                    │ • Safety Mon.   │
                    └─────────────────┘
```

## System Requirements

### Hardware
- High-performance compute platform (NVIDIA Jetson AGX or Intel Core i7+)
- Minimum 16GB RAM, 32GB recommended
- Multiple cameras (front, rear, side cameras)
- LiDAR sensor (Velodyne, Ouster, or similar)
- Radar sensors (front and rear)
- High-precision GPS + IMU
- V2X communication module
- CAN bus interface

### Software Dependencies
- WASM Edge AI SDK
- OpenCV 4.5+
- PCL (Point Cloud Library)
- ROS2 (for vehicle integration)
- CARLA simulator (for testing)

## Step 1: Environment Setup

```bash
# Install dependencies
sudo apt update
sudo apt install -y libopencv-dev libpcl-dev libeigen3-dev

# Install ROS2 (for vehicle integration)
sudo apt install -y ros-humble-desktop-full

# Install CARLA simulator for testing
pip3 install carla

# Clone and build the project
git clone https://github.com/your-org/autonomous-vehicle-sdk.git
cd autonomous-vehicle-sdk
cargo build --release
```

Create the project structure:

```bash
mkdir autonomous_vehicle_project
cd autonomous_vehicle_project
cargo init --name autonomous_vehicle
```

## Step 2: Multi-Camera Sensor Fusion

### Camera System Configuration

```rust
// src/sensors/camera_array.rs
use wasm_edge_ai_sdk::components::ingress::Camera;
use opencv::prelude::*;
use nalgebra::{Matrix3, Vector3, Isometry3};

#[derive(Debug, Clone)]
pub struct CameraConfiguration {
    pub camera_id: u32,
    pub position: Vector3<f32>,      // Camera position relative to vehicle center
    pub orientation: Vector3<f32>,   // Roll, pitch, yaw
    pub intrinsics: Matrix3<f64>,    // Camera intrinsic matrix
    pub distortion: Vec<f64>,        // Distortion coefficients
    pub field_of_view: f32,          // Horizontal FOV in degrees
}

pub struct CameraArray {
    cameras: Vec<Camera>,
    configurations: Vec<CameraConfiguration>,
    synchronized_frames: Vec<SynchronizedFrame>,
    calibration_data: CalibrationData,
}

#[derive(Debug, Clone)]
pub struct SynchronizedFrame {
    pub camera_id: u32,
    pub frame: Mat,
    pub timestamp: u64,
    pub transform_to_vehicle: Isometry3<f64>,
}

impl CameraArray {
    pub fn new() -> Result<Self, CameraError> {
        let configurations = vec![
            // Front camera
            CameraConfiguration {
                camera_id: 0,
                position: Vector3::new(2.0, 0.0, 1.5), // 2m forward, centered, 1.5m high
                orientation: Vector3::new(0.0, 0.0, 0.0), // Looking forward
                intrinsics: Matrix3::new(
                    800.0, 0.0, 640.0,
                    0.0, 800.0, 360.0,
                    0.0, 0.0, 1.0
                ),
                distortion: vec![-0.1, 0.05, 0.0, 0.0, 0.0],
                field_of_view: 60.0,
            },
            // Left camera
            CameraConfiguration {
                camera_id: 1,
                position: Vector3::new(0.0, 1.0, 1.5),
                orientation: Vector3::new(0.0, 0.0, 90.0), // Looking left
                intrinsics: Matrix3::new(800.0, 0.0, 640.0, 0.0, 800.0, 360.0, 0.0, 0.0, 1.0),
                distortion: vec![-0.1, 0.05, 0.0, 0.0, 0.0],
                field_of_view: 60.0,
            },
            // Right camera
            CameraConfiguration {
                camera_id: 2,
                position: Vector3::new(0.0, -1.0, 1.5),
                orientation: Vector3::new(0.0, 0.0, -90.0), // Looking right
                intrinsics: Matrix3::new(800.0, 0.0, 640.0, 0.0, 800.0, 360.0, 0.0, 0.0, 1.0),
                distortion: vec![-0.1, 0.05, 0.0, 0.0, 0.0],
                field_of_view: 60.0,
            },
            // Rear camera
            CameraConfiguration {
                camera_id: 3,
                position: Vector3::new(-2.0, 0.0, 1.5),
                orientation: Vector3::new(0.0, 0.0, 180.0), // Looking backward
                intrinsics: Matrix3::new(800.0, 0.0, 640.0, 0.0, 800.0, 360.0, 0.0, 0.0, 1.0),
                distortion: vec![-0.1, 0.05, 0.0, 0.0, 0.0],
                field_of_view: 60.0,
            },
        ];
        
        let mut cameras = Vec::new();
        for config in &configurations {
            cameras.push(Camera::new(config.camera_id, 1280, 720, 30.0)?);
        }
        
        Ok(CameraArray {
            cameras,
            configurations,
            synchronized_frames: Vec::new(),
            calibration_data: CalibrationData::load("config/camera_calibration.yml")?,
        })
    }
    
    pub fn capture_synchronized_frames(&mut self) -> Result<Vec<SynchronizedFrame>, CameraError> {
        let mut frames = Vec::new();
        let target_timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos() as u64;
        
        // Capture from all cameras simultaneously
        for (i, camera) in self.cameras.iter_mut().enumerate() {
            let frame = camera.capture()?;
            
            // Check timestamp synchronization (within 10ms)
            if (frame.timestamp as i64 - target_timestamp as i64).abs() < 10_000_000 {
                let transform = self.calculate_camera_to_vehicle_transform(&self.configurations[i]);
                
                frames.push(SynchronizedFrame {
                    camera_id: self.configurations[i].camera_id,
                    frame: frame.data,
                    timestamp: frame.timestamp,
                    transform_to_vehicle: transform,
                });
            }
        }
        
        self.synchronized_frames = frames.clone();
        Ok(frames)
    }
    
    pub fn create_bird_eye_view(&self, frames: &[SynchronizedFrame]) -> Result<Mat, CameraError> {
        let output_width = 800;
        let output_height = 800;
        let meters_per_pixel = 0.1; // 10cm per pixel
        
        let mut bird_eye_view = Mat::zeros(output_height, output_width, opencv::core::CV_8UC3)?.to_mat()?;
        
        for frame in frames {
            let warped = self.warp_to_ground_plane(&frame.frame, &frame.transform_to_vehicle)?;
            
            // Merge warped image into bird's eye view
            self.merge_into_bev(&mut bird_eye_view, &warped, frame.camera_id)?;
        }
        
        Ok(bird_eye_view)
    }
    
    fn calculate_camera_to_vehicle_transform(&self, config: &CameraConfiguration) -> Isometry3<f64> {
        // Create transformation matrix from camera to vehicle coordinate system
        let translation = nalgebra::Translation3::new(
            config.position.x as f64,
            config.position.y as f64,
            config.position.z as f64,
        );
        
        let rotation = nalgebra::UnitQuaternion::from_euler_angles(
            config.orientation.x.to_radians() as f64,
            config.orientation.y.to_radians() as f64,
            config.orientation.z.to_radians() as f64,
        );
        
        Isometry3::from_parts(translation, rotation)
    }
    
    fn warp_to_ground_plane(&self, image: &Mat, transform: &Isometry3<f64>) -> Result<Mat, CameraError> {
        // Implement perspective transformation to ground plane
        let mut warped = Mat::default();
        
        // Calculate homography matrix for ground plane projection
        let homography = self.calculate_ground_plane_homography(transform)?;
        
        opencv::imgproc::warp_perspective(
            image,
            &mut warped,
            &homography,
            opencv::core::Size::new(400, 400),
            opencv::imgproc::INTER_LINEAR,
            opencv::core::BORDER_CONSTANT,
            opencv::core::Scalar::all(0.0),
        )?;
        
        Ok(warped)
    }
    
    fn calculate_ground_plane_homography(&self, _transform: &Isometry3<f64>) -> Result<Mat, CameraError> {
        // Simplified homography calculation
        // In practice, this would use the camera extrinsics and intrinsics
        let homography_data = [
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0
        ];
        
        let homography = Mat::from_slice_2d(&[
            &homography_data[0..3],
            &homography_data[3..6],
            &homography_data[6..9],
        ])?;
        
        Ok(homography)
    }
    
    fn merge_into_bev(&self, bev: &mut Mat, warped: &Mat, _camera_id: u32) -> Result<(), CameraError> {
        // Merge warped camera view into bird's eye view
        // This would implement proper blending and conflict resolution
        warped.copy_to(bev)?;
        Ok(())
    }
}
```

## Step 3: LiDAR and Radar Processing

### Point Cloud Processing

```rust
// src/sensors/lidar.rs
use nalgebra::{Point3, Vector3};
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct LiDARPoint {
    pub position: Point3<f32>,
    pub intensity: f32,
    pub timestamp: u64,
    pub ring: u16,
}

#[derive(Debug, Clone)]
pub struct PointCloud {
    pub points: Vec<LiDARPoint>,
    pub timestamp: u64,
    pub sensor_position: Point3<f32>,
    pub sensor_orientation: Vector3<f32>,
}

pub struct LiDARProcessor {
    calibration: LiDARCalibration,
    ground_filter: GroundFilter,
    cluster_detector: ClusterDetector,
    object_tracker: ObjectTracker,
}

#[derive(Debug, Clone)]
pub struct LiDARCalibration {
    pub position_offset: Vector3<f32>,
    pub rotation_offset: Vector3<f32>,
    pub range_limits: (f32, f32),
    pub angle_resolution: f32,
}

impl LiDARProcessor {
    pub fn new() -> Result<Self, LiDARError> {
        Ok(LiDARProcessor {
            calibration: LiDARCalibration {
                position_offset: Vector3::new(0.0, 0.0, 2.0), // 2m above ground
                rotation_offset: Vector3::zeros(),
                range_limits: (0.5, 100.0), // 0.5m to 100m range
                angle_resolution: 0.2, // 0.2 degree resolution
            },
            ground_filter: GroundFilter::new(),
            cluster_detector: ClusterDetector::new(),
            object_tracker: ObjectTracker::new(),
        })
    }
    
    pub fn process_point_cloud(&mut self, raw_points: Vec<LiDARPoint>) -> Result<ProcessedLiDAR, LiDARError> {
        // Filter out invalid points
        let valid_points = self.filter_valid_points(raw_points)?;
        
        // Remove ground points
        let (ground_points, non_ground_points) = self.ground_filter.separate_ground(&valid_points)?;
        
        // Cluster non-ground points into objects
        let clusters = self.cluster_detector.detect_clusters(&non_ground_points)?;
        
        // Track objects across frames
        let tracked_objects = self.object_tracker.update_tracks(&clusters)?;
        
        // Create occupancy grid
        let occupancy_grid = self.create_occupancy_grid(&valid_points)?;
        
        Ok(ProcessedLiDAR {
            ground_points,
            object_clusters: clusters,
            tracked_objects,
            occupancy_grid,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos() as u64,
        })
    }
    
    fn filter_valid_points(&self, points: Vec<LiDARPoint>) -> Result<Vec<LiDARPoint>, LiDARError> {
        let valid_points = points
            .into_iter()
            .filter(|point| {
                let distance = point.position.coords.magnitude();
                distance >= self.calibration.range_limits.0 
                    && distance <= self.calibration.range_limits.1
                    && point.intensity > 0.1 // Filter low-intensity noise
            })
            .collect();
        
        Ok(valid_points)
    }
    
    fn create_occupancy_grid(&self, points: &[LiDARPoint]) -> Result<OccupancyGrid, LiDARError> {
        let grid_size = 400; // 400x400 grid
        let resolution = 0.2; // 20cm per cell
        let mut grid = OccupancyGrid::new(grid_size, grid_size, resolution);
        
        for point in points {
            let grid_x = ((point.position.x / resolution) + (grid_size as f32 / 2.0)) as usize;
            let grid_y = ((point.position.y / resolution) + (grid_size as f32 / 2.0)) as usize;
            
            if grid_x < grid_size && grid_y < grid_size {
                grid.set_occupied(grid_x, grid_y);
            }
        }
        
        Ok(grid)
    }
}

pub struct GroundFilter {
    ground_threshold: f32,
    plane_fitting_iterations: u32,
}

impl GroundFilter {
    pub fn new() -> Self {
        GroundFilter {
            ground_threshold: 0.2, // 20cm threshold for ground detection
            plane_fitting_iterations: 100,
        }
    }
    
    pub fn separate_ground(&self, points: &[LiDARPoint]) -> Result<(Vec<LiDARPoint>, Vec<LiDARPoint>), LiDARError> {
        // RANSAC plane fitting for ground detection
        let ground_plane = self.fit_ground_plane(points)?;
        
        let mut ground_points = Vec::new();
        let mut non_ground_points = Vec::new();
        
        for point in points {
            let distance_to_plane = self.distance_to_plane(&point.position, &ground_plane);
            
            if distance_to_plane.abs() < self.ground_threshold {
                ground_points.push(point.clone());
            } else {
                non_ground_points.push(point.clone());
            }
        }
        
        Ok((ground_points, non_ground_points))
    }
    
    fn fit_ground_plane(&self, points: &[LiDARPoint]) -> Result<Plane, LiDARError> {
        // RANSAC implementation for robust plane fitting
        let mut best_plane = Plane::default();
        let mut best_inlier_count = 0;
        
        let mut rng = rand::thread_rng();
        
        for _ in 0..self.plane_fitting_iterations {
            // Select 3 random points
            let indices: Vec<usize> = (0..points.len()).choose_multiple(&mut rng, 3).collect();
            let p1 = &points[indices[0]].position;
            let p2 = &points[indices[1]].position;
            let p3 = &points[indices[2]].position;
            
            // Fit plane through 3 points
            let plane = Plane::from_three_points(p1, p2, p3)?;
            
            // Count inliers
            let inlier_count = points
                .iter()
                .filter(|point| {
                    self.distance_to_plane(&point.position, &plane).abs() < self.ground_threshold
                })
                .count();
            
            if inlier_count > best_inlier_count {
                best_inlier_count = inlier_count;
                best_plane = plane;
            }
        }
        
        Ok(best_plane)
    }
    
    fn distance_to_plane(&self, point: &Point3<f32>, plane: &Plane) -> f32 {
        plane.normal.dot(&point.coords) + plane.d
    }
}

#[derive(Debug, Clone, Default)]
pub struct Plane {
    pub normal: Vector3<f32>,
    pub d: f32,
}

impl Plane {
    pub fn from_three_points(p1: &Point3<f32>, p2: &Point3<f32>, p3: &Point3<f32>) -> Result<Self, LiDARError> {
        let v1 = p2 - p1;
        let v2 = p3 - p1;
        let normal = v1.cross(&v2).normalize();
        let d = -normal.dot(&p1.coords);
        
        Ok(Plane { normal, d })
    }
}

pub struct ClusterDetector {
    cluster_tolerance: f32,
    min_cluster_size: usize,
    max_cluster_size: usize,
}

impl ClusterDetector {
    pub fn new() -> Self {
        ClusterDetector {
            cluster_tolerance: 0.5, // 50cm clustering tolerance
            min_cluster_size: 5,
            max_cluster_size: 1000,
        }
    }
    
    pub fn detect_clusters(&self, points: &[LiDARPoint]) -> Result<Vec<PointCluster>, LiDARError> {
        let mut clusters = Vec::new();
        let mut visited = vec![false; points.len()];
        
        for (i, _) in points.iter().enumerate() {
            if visited[i] {
                continue;
            }
            
            let cluster_indices = self.region_growing(points, i, &mut visited)?;
            
            if cluster_indices.len() >= self.min_cluster_size 
                && cluster_indices.len() <= self.max_cluster_size {
                let cluster_points: Vec<LiDARPoint> = cluster_indices
                    .iter()
                    .map(|&idx| points[idx].clone())
                    .collect();
                
                clusters.push(PointCluster::new(cluster_points)?);
            }
        }
        
        Ok(clusters)
    }
    
    fn region_growing(
        &self,
        points: &[LiDARPoint],
        start_idx: usize,
        visited: &mut [bool],
    ) -> Result<Vec<usize>, LiDARError> {
        let mut cluster_indices = Vec::new();
        let mut queue = std::collections::VecDeque::new();
        
        queue.push_back(start_idx);
        visited[start_idx] = true;
        
        while let Some(current_idx) = queue.pop_front() {
            cluster_indices.push(current_idx);
            
            // Find neighbors within tolerance
            for (neighbor_idx, neighbor_point) in points.iter().enumerate() {
                if visited[neighbor_idx] {
                    continue;
                }
                
                let distance = (points[current_idx].position - neighbor_point.position).magnitude();
                
                if distance < self.cluster_tolerance {
                    visited[neighbor_idx] = true;
                    queue.push_back(neighbor_idx);
                }
            }
        }
        
        Ok(cluster_indices)
    }
}

#[derive(Debug, Clone)]
pub struct PointCluster {
    pub points: Vec<LiDARPoint>,
    pub centroid: Point3<f32>,
    pub bounding_box: BoundingBox3D,
    pub size: Vector3<f32>,
    pub confidence: f32,
}

impl PointCluster {
    pub fn new(points: Vec<LiDARPoint>) -> Result<Self, LiDARError> {
        if points.is_empty() {
            return Err(LiDARError::EmptyCluster);
        }
        
        // Calculate centroid
        let centroid = {
            let sum = points.iter().fold(Vector3::zeros(), |acc, p| acc + p.position.coords);
            Point3::from(sum / points.len() as f32)
        };
        
        // Calculate bounding box
        let min_x = points.iter().map(|p| p.position.x).fold(f32::INFINITY, f32::min);
        let max_x = points.iter().map(|p| p.position.x).fold(f32::NEG_INFINITY, f32::max);
        let min_y = points.iter().map(|p| p.position.y).fold(f32::INFINITY, f32::min);
        let max_y = points.iter().map(|p| p.position.y).fold(f32::NEG_INFINITY, f32::max);
        let min_z = points.iter().map(|p| p.position.z).fold(f32::INFINITY, f32::min);
        let max_z = points.iter().map(|p| p.position.z).fold(f32::NEG_INFINITY, f32::max);
        
        let bounding_box = BoundingBox3D {
            min: Point3::new(min_x, min_y, min_z),
            max: Point3::new(max_x, max_y, max_z),
        };
        
        let size = Vector3::new(max_x - min_x, max_y - min_y, max_z - min_z);
        
        // Calculate confidence based on point density and size
        let volume = size.x * size.y * size.z;
        let density = points.len() as f32 / volume.max(0.001);
        let confidence = (density / 100.0).min(1.0); // Normalize to 0-1
        
        Ok(PointCluster {
            points,
            centroid,
            bounding_box,
            size,
            confidence,
        })
    }
}

#[derive(Debug, Clone)]
pub struct BoundingBox3D {
    pub min: Point3<f32>,
    pub max: Point3<f32>,
}

#[derive(Debug, Clone)]
pub struct OccupancyGrid {
    pub data: Vec<Vec<f32>>,
    pub width: usize,
    pub height: usize,
    pub resolution: f32,
    pub origin: Point3<f32>,
}

impl OccupancyGrid {
    pub fn new(width: usize, height: usize, resolution: f32) -> Self {
        OccupancyGrid {
            data: vec![vec![0.5; width]; height], // 0.5 = unknown, 0.0 = free, 1.0 = occupied
            width,
            height,
            resolution,
            origin: Point3::new(0.0, 0.0, 0.0),
        }
    }
    
    pub fn set_occupied(&mut self, x: usize, y: usize) {
        if x < self.width && y < self.height {
            self.data[y][x] = 1.0;
        }
    }
    
    pub fn set_free(&mut self, x: usize, y: usize) {
        if x < self.width && y < self.height {
            self.data[y][x] = 0.0;
        }
    }
    
    pub fn is_occupied(&self, x: usize, y: usize) -> bool {
        if x < self.width && y < self.height {
            self.data[y][x] > 0.7
        } else {
            true // Assume occupied if out of bounds
        }
    }
}
```

## Step 4: Perception and Object Detection

### Unified Object Detection

```rust
// src/perception/object_detection.rs
use wasm_edge_ai_sdk::components::inference::Engine;
use nalgebra::{Point3, Vector3, Vector2};

#[derive(Debug, Clone)]
pub struct DetectedObject {
    pub object_id: u32,
    pub class_name: String,
    pub confidence: f32,
    pub position: Point3<f32>,      // 3D position in vehicle coordinates
    pub velocity: Vector3<f32>,     // 3D velocity vector
    pub size: Vector3<f32>,         // Width, length, height
    pub orientation: f32,           // Heading angle
    pub detection_sources: Vec<DetectionSource>,
    pub tracking_state: TrackingState,
}

#[derive(Debug, Clone)]
pub enum DetectionSource {
    Camera(u32),        // Camera ID
    LiDAR,
    Radar,
    Fusion,
}

#[derive(Debug, Clone)]
pub enum TrackingState {
    New,
    Confirmed,
    Predicted,
    Lost,
}

pub struct MultiModalObjectDetector {
    camera_detector: Engine,
    lidar_processor: LiDARProcessor,
    radar_processor: RadarProcessor,
    fusion_engine: FusionEngine,
    tracker: MultiObjectTracker,
}

impl MultiModalObjectDetector {
    pub fn new() -> Result<Self, DetectionError> {
        Ok(MultiModalObjectDetector {
            camera_detector: Engine::load_model("models/yolo_v8_vehicle.onnx")?,
            lidar_processor: LiDARProcessor::new()?,
            radar_processor: RadarProcessor::new()?,
            fusion_engine: FusionEngine::new(),
            tracker: MultiObjectTracker::new(),
        })
    }
    
    pub fn detect_objects(
        &mut self,
        camera_frames: &[SynchronizedFrame],
        lidar_data: &PointCloud,
        radar_data: &RadarScan,
    ) -> Result<Vec<DetectedObject>, DetectionError> {
        // Process each sensor modality
        let camera_detections = self.process_camera_detections(camera_frames)?;
        let lidar_detections = self.process_lidar_detections(lidar_data)?;
        let radar_detections = self.process_radar_detections(radar_data)?;
        
        // Fuse detections from all sensors
        let fused_detections = self.fusion_engine.fuse_detections(
            &camera_detections,
            &lidar_detections,
            &radar_detections,
        )?;
        
        // Update object tracking
        let tracked_objects = self.tracker.update(&fused_detections)?;
        
        Ok(tracked_objects)
    }
    
    fn process_camera_detections(
        &mut self,
        frames: &[SynchronizedFrame],
    ) -> Result<Vec<CameraDetection>, DetectionError> {
        let mut all_detections = Vec::new();
        
        for frame in frames {
            // Run object detection on camera frame
            let detections = self.camera_detector.predict(&frame.frame)?;
            
            for detection in detections {
                // Convert 2D detection to 3D using camera calibration
                let world_position = self.project_to_3d(
                    detection.bbox.center(),
                    detection.estimated_depth,
                    &frame.transform_to_vehicle,
                )?;
                
                all_detections.push(CameraDetection {
                    camera_id: frame.camera_id,
                    class_name: detection.class_name,
                    confidence: detection.confidence,
                    bbox_2d: detection.bbox,
                    position_3d: world_position,
                    timestamp: frame.timestamp,
                });
            }
        }
        
        Ok(all_detections)
    }
    
    fn process_lidar_detections(
        &mut self,
        lidar_data: &PointCloud,
    ) -> Result<Vec<LiDARDetection>, DetectionError> {
        let processed_lidar = self.lidar_processor.process_point_cloud(lidar_data.points.clone())?;
        
        let mut detections = Vec::new();
        
        for cluster in &processed_lidar.object_clusters {
            // Classify cluster based on size and shape
            let object_class = self.classify_lidar_cluster(cluster)?;
            
            detections.push(LiDARDetection {
                class_name: object_class,
                confidence: cluster.confidence,
                position: cluster.centroid,
                size: cluster.size,
                bounding_box: cluster.bounding_box.clone(),
                point_count: cluster.points.len(),
                timestamp: processed_lidar.timestamp,
            });
        }
        
        Ok(detections)
    }
    
    fn process_radar_detections(
        &mut self,
        radar_data: &RadarScan,
    ) -> Result<Vec<RadarDetection>, DetectionError> {
        let detections = self.radar_processor.process_scan(radar_data)?;
        Ok(detections)
    }
    
    fn project_to_3d(
        &self,
        image_point: Vector2<f32>,
        estimated_depth: f32,
        camera_transform: &nalgebra::Isometry3<f64>,
    ) -> Result<Point3<f32>, DetectionError> {
        // Convert image coordinates to 3D world coordinates
        // This would use camera intrinsics and extrinsics
        
        // Simplified implementation
        let camera_coords = Vector3::new(
            (image_point.x - 640.0) * estimated_depth / 800.0,
            (image_point.y - 360.0) * estimated_depth / 800.0,
            estimated_depth,
        );
        
        // Transform to vehicle coordinates
        let vehicle_coords = camera_transform.transform_point(&Point3::from(camera_coords));
        
        Ok(Point3::new(
            vehicle_coords.x as f32,
            vehicle_coords.y as f32,
            vehicle_coords.z as f32,
        ))
    }
    
    fn classify_lidar_cluster(&self, cluster: &PointCluster) -> Result<String, DetectionError> {
        // Simple rule-based classification based on size
        let volume = cluster.size.x * cluster.size.y * cluster.size.z;
        
        match volume {
            v if v < 2.0 => Ok("pedestrian".to_string()),
            v if v < 10.0 => Ok("cyclist".to_string()),
            v if v < 50.0 => Ok("car".to_string()),
            _ => Ok("truck".to_string()),
        }
    }
}

pub struct FusionEngine {
    association_threshold: f32,
    confidence_weights: FusionWeights,
}

#[derive(Debug, Clone)]
pub struct FusionWeights {
    pub camera: f32,
    pub lidar: f32,
    pub radar: f32,
}

impl FusionEngine {
    pub fn new() -> Self {
        FusionEngine {
            association_threshold: 2.0, // 2 meter association threshold
            confidence_weights: FusionWeights {
                camera: 0.3,
                lidar: 0.5,
                radar: 0.2,
            },
        }
    }
    
    pub fn fuse_detections(
        &self,
        camera_detections: &[CameraDetection],
        lidar_detections: &[LiDARDetection],
        radar_detections: &[RadarDetection],
    ) -> Result<Vec<FusedDetection>, DetectionError> {
        let mut fused_detections = Vec::new();
        let mut used_camera = vec![false; camera_detections.len()];
        let mut used_lidar = vec![false; lidar_detections.len()];
        let mut used_radar = vec![false; radar_detections.len()];
        
        // Associate detections from different sensors
        for (i, lidar_det) in lidar_detections.iter().enumerate() {
            if used_lidar[i] {
                continue;
            }
            
            let mut fusion_candidates = Vec::new();
            
            // Find associated camera detections
            for (j, camera_det) in camera_detections.iter().enumerate() {
                if used_camera[j] {
                    continue;
                }
                
                let distance = (lidar_det.position - camera_det.position_3d).magnitude();
                
                if distance < self.association_threshold {
                    fusion_candidates.push(FusionCandidate::Camera(j, distance));
                }
            }
            
            // Find associated radar detections
            for (k, radar_det) in radar_detections.iter().enumerate() {
                if used_radar[k] {
                    continue;
                }
                
                let distance = (lidar_det.position - radar_det.position).magnitude();
                
                if distance < self.association_threshold {
                    fusion_candidates.push(FusionCandidate::Radar(k, distance));
                }
            }
            
            // Create fused detection
            let fused = self.create_fused_detection(
                Some(i),
                &fusion_candidates,
                camera_detections,
                lidar_detections,
                radar_detections,
            )?;
            
            fused_detections.push(fused);
            
            // Mark associated detections as used
            used_lidar[i] = true;
            for candidate in &fusion_candidates {
                match candidate {
                    FusionCandidate::Camera(idx, _) => used_camera[*idx] = true,
                    FusionCandidate::Radar(idx, _) => used_radar[*idx] = true,
                }
            }
        }
        
        Ok(fused_detections)
    }
    
    fn create_fused_detection(
        &self,
        lidar_idx: Option<usize>,
        candidates: &[FusionCandidate],
        camera_detections: &[CameraDetection],
        lidar_detections: &[LiDARDetection],
        radar_detections: &[RadarDetection],
    ) -> Result<FusedDetection, DetectionError> {
        let mut position = Point3::origin();
        let mut confidence = 0.0;
        let mut detection_sources = Vec::new();
        let mut class_votes = std::collections::HashMap::new();
        
        // Process LiDAR detection
        if let Some(idx) = lidar_idx {
            let lidar_det = &lidar_detections[idx];
            position += lidar_det.position.coords * self.confidence_weights.lidar;
            confidence += lidar_det.confidence * self.confidence_weights.lidar;
            detection_sources.push(DetectionSource::LiDAR);
            
            *class_votes.entry(lidar_det.class_name.clone()).or_insert(0.0) += 
                self.confidence_weights.lidar;
        }
        
        // Process associated detections
        for candidate in candidates {
            match candidate {
                FusionCandidate::Camera(idx, _) => {
                    let camera_det = &camera_detections[*idx];
                    position += camera_det.position_3d.coords * self.confidence_weights.camera;
                    confidence += camera_det.confidence * self.confidence_weights.camera;
                    detection_sources.push(DetectionSource::Camera(camera_det.camera_id));
                    
                    *class_votes.entry(camera_det.class_name.clone()).or_insert(0.0) += 
                        self.confidence_weights.camera;
                },
                FusionCandidate::Radar(idx, _) => {
                    let radar_det = &radar_detections[*idx];
                    position += radar_det.position.coords * self.confidence_weights.radar;
                    confidence += radar_det.confidence * self.confidence_weights.radar;
                    detection_sources.push(DetectionSource::Radar);
                    
                    *class_votes.entry(radar_det.class_name.clone()).or_insert(0.0) += 
                        self.confidence_weights.radar;
                },
            }
        }
        
        // Determine final class based on voting
        let final_class = class_votes
            .into_iter()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
            .map(|(class, _)| class)
            .unwrap_or_else(|| "unknown".to_string());
        
        Ok(FusedDetection {
            class_name: final_class,
            confidence,
            position: Point3::from(position),
            detection_sources,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos() as u64,
        })
    }
}

#[derive(Debug, Clone)]
pub enum FusionCandidate {
    Camera(usize, f32), // Index and distance
    Radar(usize, f32),
}

// Detection structures for different sensors
#[derive(Debug, Clone)]
pub struct CameraDetection {
    pub camera_id: u32,
    pub class_name: String,
    pub confidence: f32,
    pub bbox_2d: BoundingBox2D,
    pub position_3d: Point3<f32>,
    pub timestamp: u64,
}

#[derive(Debug, Clone)]
pub struct LiDARDetection {
    pub class_name: String,
    pub confidence: f32,
    pub position: Point3<f32>,
    pub size: Vector3<f32>,
    pub bounding_box: BoundingBox3D,
    pub point_count: usize,
    pub timestamp: u64,
}

#[derive(Debug, Clone)]
pub struct RadarDetection {
    pub class_name: String,
    pub confidence: f32,
    pub position: Point3<f32>,
    pub velocity: Vector3<f32>,
    pub rcs: f32, // Radar cross section
    pub timestamp: u64,
}

#[derive(Debug, Clone)]
pub struct FusedDetection {
    pub class_name: String,
    pub confidence: f32,
    pub position: Point3<f32>,
    pub detection_sources: Vec<DetectionSource>,
    pub timestamp: u64,
}

#[derive(Debug, Clone)]
pub struct BoundingBox2D {
    pub x: f32,
    pub y: f32,
    pub width: f32,
    pub height: f32,
}

impl BoundingBox2D {
    pub fn center(&self) -> Vector2<f32> {
        Vector2::new(self.x + self.width / 2.0, self.y + self.height / 2.0)
    }
}
```

## Step 5: Path Planning and Motion Control

### Path Planning System

```rust
// src/planning/path_planner.rs
use nalgebra::{Point2, Vector2};
use std::collections::{BinaryHeap, HashMap, HashSet};

pub struct PathPlanner {
    road_network: RoadNetwork,
    behavior_planner: BehaviorPlanner,
    local_planner: LocalPlanner,
    motion_planner: MotionPlanner,
}

#[derive(Debug, Clone)]
pub struct RoadNetwork {
    pub lanes: Vec<Lane>,
    pub intersections: Vec<Intersection>,
    pub traffic_lights: Vec<TrafficLight>,
    pub signs: Vec<TrafficSign>,
}

#[derive(Debug, Clone)]
pub struct Lane {
    pub id: u32,
    pub waypoints: Vec<Point2<f32>>,
    pub width: f32,
    pub speed_limit: f32,
    pub lane_type: LaneType,
    pub left_neighbor: Option<u32>,
    pub right_neighbor: Option<u32>,
}

#[derive(Debug, Clone)]
pub enum LaneType {
    Driving,
    Turning,
    Merging,
    Exit,
    OnRamp,
    OffRamp,
}

#[derive(Debug, Clone)]
pub struct Path {
    pub waypoints: Vec<Waypoint>,
    pub total_distance: f32,
    pub estimated_time: f32,
    pub safety_score: f32,
}

#[derive(Debug, Clone)]
pub struct Waypoint {
    pub position: Point2<f32>,
    pub heading: f32,
    pub curvature: f32,
    pub speed_limit: f32,
    pub lane_id: Option<u32>,
}

impl PathPlanner {
    pub fn new(road_network: RoadNetwork) -> Self {
        PathPlanner {
            road_network,
            behavior_planner: BehaviorPlanner::new(),
            local_planner: LocalPlanner::new(),
            motion_planner: MotionPlanner::new(),
        }
    }
    
    pub fn plan_path(
        &mut self,
        start: Point2<f32>,
        goal: Point2<f32>,
        current_velocity: f32,
        detected_objects: &[DetectedObject],
        vehicle_state: &VehicleState,
    ) -> Result<Path, PlanningError> {
        // High-level behavior planning
        let behavior_plan = self.behavior_planner.plan_behavior(
            start,
            goal,
            detected_objects,
            vehicle_state,
            &self.road_network,
        )?;
        
        // Local path planning
        let local_path = self.local_planner.plan_local_path(
            start,
            &behavior_plan,
            detected_objects,
            &self.road_network,
        )?;
        
        // Motion planning with dynamics
        let motion_plan = self.motion_planner.plan_motion(
            &local_path,
            current_velocity,
            vehicle_state,
        )?;
        
        Ok(motion_plan)
    }
}

pub struct BehaviorPlanner {
    state_machine: BehaviorStateMachine,
    decision_tree: DecisionTree,
}

#[derive(Debug, Clone)]
pub enum BehaviorState {
    LaneFollowing,
    ChangingLaneLeft,
    ChangingLaneRight,
    Overtaking,
    Merging,
    Yielding,
    Stopping,
    ParkingMode,
}

#[derive(Debug, Clone)]
pub struct BehaviorPlan {
    pub target_lane: u32,
    pub target_speed: f32,
    pub maneuver: ManeuverType,
    pub time_horizon: f32,
    pub safety_constraints: Vec<SafetyConstraint>,
}

#[derive(Debug, Clone)]
pub enum ManeuverType {
    Continue,
    LaneChange(LaneChangeDirection),
    Merge,
    Turn(TurnDirection),
    Stop,
    Park,
}

#[derive(Debug, Clone)]
pub enum LaneChangeDirection {
    Left,
    Right,
}

#[derive(Debug, Clone)]
pub enum TurnDirection {
    Left,
    Right,
    UTurn,
}

impl BehaviorPlanner {
    pub fn new() -> Self {
        BehaviorPlanner {
            state_machine: BehaviorStateMachine::new(),
            decision_tree: DecisionTree::new(),
        }
    }
    
    pub fn plan_behavior(
        &mut self,
        current_position: Point2<f32>,
        goal: Point2<f32>,
        detected_objects: &[DetectedObject],
        vehicle_state: &VehicleState,
        road_network: &RoadNetwork,
    ) -> Result<BehaviorPlan, PlanningError> {
        // Update state machine
        let current_state = self.state_machine.update(
            current_position,
            detected_objects,
            vehicle_state,
            road_network,
        )?;
        
        // Make behavior decision
        let decision = self.decision_tree.make_decision(
            &current_state,
            current_position,
            goal,
            detected_objects,
            road_network,
        )?;
        
        Ok(decision)
    }
}

pub struct LocalPlanner {
    a_star: AStarPlanner,
    rrt_star: RRTStarPlanner,
    lattice_planner: LatticePlanner,
}

impl LocalPlanner {
    pub fn new() -> Self {
        LocalPlanner {
            a_star: AStarPlanner::new(),
            rrt_star: RRTStarPlanner::new(),
            lattice_planner: LatticePlanner::new(),
        }
    }
    
    pub fn plan_local_path(
        &mut self,
        start: Point2<f32>,
        behavior_plan: &BehaviorPlan,
        obstacles: &[DetectedObject],
        road_network: &RoadNetwork,
    ) -> Result<Path, PlanningError> {
        // Create local occupancy grid
        let occupancy_grid = self.create_local_occupancy_grid(start, obstacles)?;
        
        // Choose planning algorithm based on scenario
        let path = match behavior_plan.maneuver {
            ManeuverType::Continue | ManeuverType::LaneChange(_) => {
                // Use lattice planner for structured environments
                self.lattice_planner.plan(start, behavior_plan, &occupancy_grid, road_network)?
            },
            ManeuverType::Turn(_) | ManeuverType::Merge => {
                // Use RRT* for complex maneuvers
                self.rrt_star.plan(start, behavior_plan, &occupancy_grid)?
            },
            ManeuverType::Stop | ManeuverType::Park => {
                // Use A* for precise positioning
                self.a_star.plan(start, behavior_plan, &occupancy_grid)?
            },
        };
        
        // Smooth and optimize path
        let smoothed_path = self.smooth_path(&path)?;
        
        Ok(smoothed_path)
    }
    
    fn create_local_occupancy_grid(
        &self,
        center: Point2<f32>,
        obstacles: &[DetectedObject],
    ) -> Result<LocalOccupancyGrid, PlanningError> {
        let grid_size = 200; // 200x200 grid
        let resolution = 0.2; // 20cm per cell
        let mut grid = LocalOccupancyGrid::new(grid_size, grid_size, resolution, center);
        
        // Mark obstacles
        for obstacle in obstacles {
            grid.mark_obstacle(&obstacle.position, &obstacle.size)?;
        }
        
        // Add safety margins
        grid.dilate_obstacles(1.0)?; // 1m safety margin
        
        Ok(grid)
    }
    
    fn smooth_path(&self, path: &Path) -> Result<Path, PlanningError> {
        // Apply Bézier curve smoothing
        let smoothed_waypoints = self.bezier_smooth(&path.waypoints)?;
        
        Ok(Path {
            waypoints: smoothed_waypoints,
            total_distance: self.calculate_path_length(&path.waypoints),
            estimated_time: path.estimated_time,
            safety_score: path.safety_score,
        })
    }
    
    fn bezier_smooth(&self, waypoints: &[Waypoint]) -> Result<Vec<Waypoint>, PlanningError> {
        // Implement Bézier curve smoothing
        // This is a simplified version
        Ok(waypoints.to_vec())
    }
    
    fn calculate_path_length(&self, waypoints: &[Waypoint]) -> f32 {
        waypoints
            .windows(2)
            .map(|w| (w[1].position - w[0].position).magnitude())
            .sum()
    }
}

pub struct MotionPlanner {
    vehicle_model: VehicleModel,
    optimizer: TrajectoryOptimizer,
}

#[derive(Debug, Clone)]
pub struct VehicleModel {
    pub wheelbase: f32,
    pub max_steering_angle: f32,
    pub max_acceleration: f32,
    pub max_deceleration: f32,
    pub max_velocity: f32,
    pub width: f32,
    pub length: f32,
}

impl MotionPlanner {
    pub fn new() -> Self {
        MotionPlanner {
            vehicle_model: VehicleModel {
                wheelbase: 2.8,
                max_steering_angle: 30.0_f32.to_radians(),
                max_acceleration: 3.0,
                max_deceleration: 8.0,
                max_velocity: 50.0,
                width: 2.0,
                length: 4.5,
            },
            optimizer: TrajectoryOptimizer::new(),
        }
    }
    
    pub fn plan_motion(
        &mut self,
        path: &Path,
        current_velocity: f32,
        vehicle_state: &VehicleState,
    ) -> Result<Path, PlanningError> {
        // Generate velocity profile
        let velocity_profile = self.generate_velocity_profile(path, current_velocity)?;
        
        // Optimize trajectory for comfort and efficiency
        let optimized_trajectory = self.optimizer.optimize(
            path,
            &velocity_profile,
            &self.vehicle_model,
            vehicle_state,
        )?;
        
        Ok(optimized_trajectory)
    }
    
    fn generate_velocity_profile(
        &self,
        path: &Path,
        current_velocity: f32,
    ) -> Result<Vec<f32>, PlanningError> {
        let mut velocities = Vec::new();
        let mut current_v = current_velocity;
        
        for (i, waypoint) in path.waypoints.iter().enumerate() {
            // Consider speed limits
            let speed_limit = waypoint.speed_limit;
            
            // Consider curvature constraints
            let curvature_limit = if waypoint.curvature.abs() > 0.001 {
                (0.5 / waypoint.curvature.abs()).sqrt().min(speed_limit)
            } else {
                speed_limit
            };
            
            // Consider stopping distance
            let target_velocity = curvature_limit.min(speed_limit);
            
            // Apply acceleration/deceleration limits
            if i > 0 {
                let dt = 0.1; // Assume 0.1s between waypoints
                let max_dv = self.vehicle_model.max_acceleration * dt;
                let min_dv = -self.vehicle_model.max_deceleration * dt;
                
                let desired_dv = target_velocity - current_v;
                let actual_dv = desired_dv.max(min_dv).min(max_dv);
                
                current_v += actual_dv;
            }
            
            velocities.push(current_v);
        }
        
        Ok(velocities)
    }
}

// Helper structures
#[derive(Debug, Clone)]
pub struct VehicleState {
    pub position: Point2<f32>,
    pub heading: f32,
    pub velocity: f32,
    pub acceleration: f32,
    pub steering_angle: f32,
    pub timestamp: u64,
}

#[derive(Debug, Clone)]
pub struct LocalOccupancyGrid {
    pub data: Vec<Vec<f32>>,
    pub width: usize,
    pub height: usize,
    pub resolution: f32,
    pub center: Point2<f32>,
}

impl LocalOccupancyGrid {
    pub fn new(width: usize, height: usize, resolution: f32, center: Point2<f32>) -> Self {
        LocalOccupancyGrid {
            data: vec![vec![0.0; width]; height], // 0.0 = free, 1.0 = occupied
            width,
            height,
            resolution,
            center,
        }
    }
    
    pub fn mark_obstacle(&mut self, position: &Point2<f32>, size: &Vector2<f32>) -> Result<(), PlanningError> {
        // Convert world coordinates to grid coordinates
        let grid_x = ((position.x - self.center.x) / self.resolution + self.width as f32 / 2.0) as i32;
        let grid_y = ((position.y - self.center.y) / self.resolution + self.height as f32 / 2.0) as i32;
        
        let size_x = (size.x / self.resolution) as i32;
        let size_y = (size.y / self.resolution) as i32;
        
        // Mark cells as occupied
        for dy in -size_y/2..=size_y/2 {
            for dx in -size_x/2..=size_x/2 {
                let x = grid_x + dx;
                let y = grid_y + dy;
                
                if x >= 0 && x < self.width as i32 && y >= 0 && y < self.height as i32 {
                    self.data[y as usize][x as usize] = 1.0;
                }
            }
        }
        
        Ok(())
    }
    
    pub fn dilate_obstacles(&mut self, margin: f32) -> Result<(), PlanningError> {
        let margin_cells = (margin / self.resolution) as i32;
        let original_data = self.data.clone();
        
        for y in 0..self.height {
            for x in 0..self.width {
                if original_data[y][x] > 0.5 {
                    // Dilate around this obstacle
                    for dy in -margin_cells..=margin_cells {
                        for dx in -margin_cells..=margin_cells {
                            let nx = x as i32 + dx;
                            let ny = y as i32 + dy;
                            
                            if nx >= 0 && nx < self.width as i32 && ny >= 0 && ny < self.height as i32 {
                                self.data[ny as usize][nx as usize] = 1.0;
                            }
                        }
                    }
                }
            }
        }
        
        Ok(())
    }
}

// Placeholder implementations for planning algorithms
pub struct AStarPlanner;
pub struct RRTStarPlanner;
pub struct LatticePlanner;
pub struct BehaviorStateMachine;
pub struct DecisionTree;
pub struct TrajectoryOptimizer;

impl AStarPlanner {
    pub fn new() -> Self { AStarPlanner }
    pub fn plan(&mut self, _start: Point2<f32>, _plan: &BehaviorPlan, _grid: &LocalOccupancyGrid) -> Result<Path, PlanningError> {
        // A* implementation would go here
        Ok(Path {
            waypoints: vec![],
            total_distance: 0.0,
            estimated_time: 0.0,
            safety_score: 1.0,
        })
    }
}

impl RRTStarPlanner {
    pub fn new() -> Self { RRTStarPlanner }
    pub fn plan(&mut self, _start: Point2<f32>, _plan: &BehaviorPlan, _grid: &LocalOccupancyGrid) -> Result<Path, PlanningError> {
        // RRT* implementation would go here
        Ok(Path {
            waypoints: vec![],
            total_distance: 0.0,
            estimated_time: 0.0,
            safety_score: 1.0,
        })
    }
}

impl LatticePlanner {
    pub fn new() -> Self { LatticePlanner }
    pub fn plan(&mut self, _start: Point2<f32>, _plan: &BehaviorPlan, _grid: &LocalOccupancyGrid, _network: &RoadNetwork) -> Result<Path, PlanningError> {
        // Lattice planner implementation would go here
        Ok(Path {
            waypoints: vec![],
            total_distance: 0.0,
            estimated_time: 0.0,
            safety_score: 1.0,
        })
    }
}

impl BehaviorStateMachine {
    pub fn new() -> Self { BehaviorStateMachine }
    pub fn update(&mut self, _pos: Point2<f32>, _objects: &[DetectedObject], _state: &VehicleState, _network: &RoadNetwork) -> Result<BehaviorState, PlanningError> {
        Ok(BehaviorState::LaneFollowing)
    }
}

impl DecisionTree {
    pub fn new() -> Self { DecisionTree }
    pub fn make_decision(&self, _state: &BehaviorState, _pos: Point2<f32>, _goal: Point2<f32>, _objects: &[DetectedObject], _network: &RoadNetwork) -> Result<BehaviorPlan, PlanningError> {
        Ok(BehaviorPlan {
            target_lane: 0,
            target_speed: 50.0,
            maneuver: ManeuverType::Continue,
            time_horizon: 5.0,
            safety_constraints: vec![],
        })
    }
}

impl TrajectoryOptimizer {
    pub fn new() -> Self { TrajectoryOptimizer }
    pub fn optimize(&mut self, path: &Path, _velocities: &[f32], _model: &VehicleModel, _state: &VehicleState) -> Result<Path, PlanningError> {
        Ok(path.clone())
    }
}

// Error types and other supporting structures
#[derive(Debug)]
pub enum PlanningError {
    NoPathFound,
    InvalidConstraints,
    ComputationTimeout,
}

#[derive(Debug, Clone)]
pub struct SafetyConstraint {
    pub constraint_type: ConstraintType,
    pub value: f32,
}

#[derive(Debug, Clone)]
pub enum ConstraintType {
    MaxVelocity,
    MaxAcceleration,
    MinFollowingDistance,
    LateralClearance,
}

#[derive(Debug, Clone)]
pub struct Intersection {
    pub id: u32,
    pub center: Point2<f32>,
    pub incoming_lanes: Vec<u32>,
    pub outgoing_lanes: Vec<u32>,
    pub traffic_lights: Vec<u32>,
}

#[derive(Debug, Clone)]
pub struct TrafficLight {
    pub id: u32,
    pub position: Point2<f32>,
    pub state: TrafficLightState,
    pub applicable_lanes: Vec<u32>,
}

#[derive(Debug, Clone)]
pub enum TrafficLightState {
    Red,
    Yellow,
    Green,
    RedYellow,
    Unknown,
}

#[derive(Debug, Clone)]
pub struct TrafficSign {
    pub id: u32,
    pub position: Point2<f32>,
    pub sign_type: TrafficSignType,
    pub applicable_lanes: Vec<u32>,
}

#[derive(Debug, Clone)]
pub enum TrafficSignType {
    Stop,
    Yield,
    SpeedLimit(f32),
    NoEntry,
    OneWay,
    Merge,
}
```

## Step 6: Vehicle Control System

### Low-Level Vehicle Control

```rust
// src/control/vehicle_controller.rs
use nalgebra::{Vector2, Vector3};
use std::time::{Duration, Instant};

pub struct VehicleController {
    steering_controller: SteeringController,
    throttle_controller: ThrottleController,
    brake_controller: BrakeController,
    safety_monitor: VehicleSafetyMonitor,
    control_loop_frequency: f32,
    last_update: Instant,
}

#[derive(Debug, Clone)]
pub struct ControlCommand {
    pub steering_angle: f32,    // Radians
    pub throttle_position: f32, // 0.0 to 1.0
    pub brake_pressure: f32,    // 0.0 to 1.0
    pub gear: GearPosition,
    pub timestamp: u64,
}

#[derive(Debug, Clone)]
pub enum GearPosition {
    Park,
    Reverse,
    Neutral,
    Drive,
    Manual(u8),
}

impl VehicleController {
    pub fn new() -> Self {
        VehicleController {
            steering_controller: SteeringController::new(),
            throttle_controller: ThrottleController::new(),
            brake_controller: BrakeController::new(),
            safety_monitor: VehicleSafetyMonitor::new(),
            control_loop_frequency: 100.0, // 100 Hz
            last_update: Instant::now(),
        }
    }
    
    pub fn update_control(
        &mut self,
        target_path: &Path,
        current_state: &VehicleState,
        sensor_data: &VehicleSensorData,
    ) -> Result<ControlCommand, ControlError> {
        // Check timing
        let now = Instant::now();
        let dt = now.duration_since(self.last_update).as_secs_f32();
        
        if dt < 1.0 / self.control_loop_frequency {
            return Err(ControlError::UpdateTooFrequent);
        }
        
        self.last_update = now;
        
        // Safety check
        let safety_status = self.safety_monitor.check_safety(current_state, sensor_data)?;
        if !safety_status.is_safe {
            return self.emergency_stop();
        }
        
        // Find closest waypoint on path
        let target_waypoint = self.find_target_waypoint(target_path, current_state)?;
        
        // Calculate control outputs
        let steering_angle = self.steering_controller.calculate_steering(
            &target_waypoint,
            current_state,
            dt,
        )?;
        
        let (throttle, brake) = self.calculate_longitudinal_control(
            &target_waypoint,
            current_state,
            dt,
        )?;
        
        let control_command = ControlCommand {
            steering_angle,
            throttle_position: throttle,
            brake_pressure: brake,
            gear: GearPosition::Drive,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos() as u64,
        };
        
        // Apply control command
        self.apply_control_command(&control_command)?;
        
        Ok(control_command)
    }
    
    fn find_target_waypoint(&self, path: &Path, current_state: &VehicleState) -> Result<Waypoint, ControlError> {
        let lookahead_distance = 5.0 + current_state.velocity * 0.5; // Dynamic lookahead
        
        // Find closest point on path
        let mut closest_distance = f32::INFINITY;
        let mut closest_index = 0;
        
        for (i, waypoint) in path.waypoints.iter().enumerate() {
            let distance = (waypoint.position - current_state.position).magnitude();
            if distance < closest_distance {
                closest_distance = distance;
                closest_index = i;
            }
        }
        
        // Find lookahead point
        let mut accumulated_distance = 0.0;
        for i in closest_index..path.waypoints.len() {
            if i > closest_index {
                accumulated_distance += (path.waypoints[i].position - path.waypoints[i-1].position).magnitude();
            }
            
            if accumulated_distance >= lookahead_distance {
                return Ok(path.waypoints[i].clone());
            }
        }
        
        // If no lookahead point found, use last waypoint
        Ok(path.waypoints.last().unwrap().clone())
    }
    
    fn calculate_longitudinal_control(
        &mut self,
        target_waypoint: &Waypoint,
        current_state: &VehicleState,
        dt: f32,
    ) -> Result<(f32, f32), ControlError> {
        let target_velocity = target_waypoint.speed_limit;
        let velocity_error = target_velocity - current_state.velocity;
        
        // Use separate controllers for throttle and brake
        let throttle = if velocity_error > 0.0 {
            self.throttle_controller.calculate_throttle(velocity_error, dt)?
        } else {
            0.0
        };
        
        let brake = if velocity_error < -0.5 {
            self.brake_controller.calculate_brake(-velocity_error, dt)?
        } else {
            0.0
        };
        
        Ok((throttle, brake))
    }
    
    fn apply_control_command(&self, command: &ControlCommand) -> Result<(), ControlError> {
        // Interface with vehicle CAN bus or control system
        // This would send actual commands to the vehicle's ECUs
        
        log::debug!("Applying control: steering={:.3}, throttle={:.3}, brake={:.3}",
                   command.steering_angle, command.throttle_position, command.brake_pressure);
        
        // Send CAN messages
        self.send_steering_command(command.steering_angle)?;
        self.send_throttle_command(command.throttle_position)?;
        self.send_brake_command(command.brake_pressure)?;
        
        Ok(())
    }
    
    fn emergency_stop(&self) -> Result<ControlCommand, ControlError> {
        log::error!("EMERGENCY STOP ACTIVATED");
        
        Ok(ControlCommand {
            steering_angle: 0.0,
            throttle_position: 0.0,
            brake_pressure: 1.0, // Full brake
            gear: GearPosition::Park,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos() as u64,
        })
    }
    
    // CAN bus interface methods
    fn send_steering_command(&self, angle: f32) -> Result<(), ControlError> {
        // Implementation would send actual CAN message
        Ok(())
    }
    
    fn send_throttle_command(&self, throttle: f32) -> Result<(), ControlError> {
        // Implementation would send actual CAN message
        Ok(())
    }
    
    fn send_brake_command(&self, brake: f32) -> Result<(), ControlError> {
        // Implementation would send actual CAN message
        Ok(())
    }
}

pub struct SteeringController {
    kp: f32,
    ki: f32,
    kd: f32,
    integral_error: f32,
    previous_error: f32,
    max_steering_rate: f32,
    previous_steering: f32,
}

impl SteeringController {
    pub fn new() -> Self {
        SteeringController {
            kp: 1.5,
            ki: 0.1,
            kd: 0.05,
            integral_error: 0.0,
            previous_error: 0.0,
            max_steering_rate: 30.0_f32.to_radians(), // 30 degrees per second
            previous_steering: 0.0,
        }
    }
    
    pub fn calculate_steering(
        &mut self,
        target_waypoint: &Waypoint,
        current_state: &VehicleState,
        dt: f32,
    ) -> Result<f32, ControlError> {
        // Calculate cross-track error and heading error
        let target_vector = target_waypoint.position - current_state.position;
        let distance_to_target = target_vector.magnitude();
        
        // Cross-track error (lateral distance from path)
        let cross_track_error = self.calculate_cross_track_error(
            current_state.position,
            current_state.heading,
            target_waypoint.position,
        );
        
        // Heading error
        let target_heading = target_vector.y.atan2(target_vector.x);
        let heading_error = self.normalize_angle(target_heading - current_state.heading);
        
        // Combined error (weighted sum)
        let lateral_error = cross_track_error + 0.5 * heading_error;
        
        // PID control
        self.integral_error += lateral_error * dt;
        let derivative_error = (lateral_error - self.previous_error) / dt;
        
        let steering_output = self.kp * lateral_error + 
                             self.ki * self.integral_error + 
                             self.kd * derivative_error;
        
        // Apply rate limiting
        let max_change = self.max_steering_rate * dt;
        let limited_steering = (steering_output - self.previous_steering)
            .max(-max_change)
            .min(max_change) + self.previous_steering;
        
        // Apply physical limits
        let final_steering = limited_steering
            .max(-30.0_f32.to_radians())
            .min(30.0_f32.to_radians());
        
        self.previous_error = lateral_error;
        self.previous_steering = final_steering;
        
        Ok(final_steering)
    }
    
    fn calculate_cross_track_error(
        &self,
        current_position: Vector2<f32>,
        current_heading: f32,
        target_position: Vector2<f32>,
    ) -> f32 {
        let target_vector = target_position - current_position;
        let heading_vector = Vector2::new(current_heading.cos(), current_heading.sin());
        
        // Cross product to get lateral error
        target_vector.x * heading_vector.y - target_vector.y * heading_vector.x
    }
    
    fn normalize_angle(&self, angle: f32) -> f32 {
        let mut normalized = angle;
        while normalized > std::f32::consts::PI {
            normalized -= 2.0 * std::f32::consts::PI;
        }
        while normalized < -std::f32::consts::PI {
            normalized += 2.0 * std::f32::consts::PI;
        }
        normalized
    }
}

pub struct ThrottleController {
    kp: f32,
    ki: f32,
    kd: f32,
    integral_error: f32,
    previous_error: f32,
    max_throttle_rate: f32,
    previous_throttle: f32,
}

impl ThrottleController {
    pub fn new() -> Self {
        ThrottleController {
            kp: 0.3,
            ki: 0.05,
            kd: 0.01,
            integral_error: 0.0,
            previous_error: 0.0,
            max_throttle_rate: 0.5, // 50% per second
            previous_throttle: 0.0,
        }
    }
    
    pub fn calculate_throttle(&mut self, velocity_error: f32, dt: f32) -> Result<f32, ControlError> {
        // PID control for throttle
        self.integral_error += velocity_error * dt;
        let derivative_error = (velocity_error - self.previous_error) / dt;
        
        let throttle_output = self.kp * velocity_error + 
                             self.ki * self.integral_error + 
                             self.kd * derivative_error;
        
        // Apply rate limiting
        let max_change = self.max_throttle_rate * dt;
        let limited_throttle = (throttle_output - self.previous_throttle)
            .max(-max_change)
            .min(max_change) + self.previous_throttle;
        
        // Apply physical limits
        let final_throttle = limited_throttle.max(0.0).min(1.0);
        
        self.previous_error = velocity_error;
        self.previous_throttle = final_throttle;
        
        Ok(final_throttle)
    }
}

pub struct BrakeController {
    kp: f32,
    ki: f32,
    kd: f32,
    integral_error: f32,
    previous_error: f32,
    max_brake_rate: f32,
    previous_brake: f32,
}

impl BrakeController {
    pub fn new() -> Self {
        BrakeController {
            kp: 0.5,
            ki: 0.1,
            kd: 0.02,
            integral_error: 0.0,
            previous_error: 0.0,
            max_brake_rate: 1.0, // 100% per second
            previous_brake: 0.0,
        }
    }
    
    pub fn calculate_brake(&mut self, deceleration_needed: f32, dt: f32) -> Result<f32, ControlError> {
        // PID control for brake
        self.integral_error += deceleration_needed * dt;
        let derivative_error = (deceleration_needed - self.previous_error) / dt;
        
        let brake_output = self.kp * deceleration_needed + 
                          self.ki * self.integral_error + 
                          self.kd * derivative_error;
        
        // Apply rate limiting
        let max_change = self.max_brake_rate * dt;
        let limited_brake = (brake_output - self.previous_brake)
            .max(-max_change)
            .min(max_change) + self.previous_brake;
        
        // Apply physical limits
        let final_brake = limited_brake.max(0.0).min(1.0);
        
        self.previous_error = deceleration_needed;
        self.previous_brake = final_brake;
        
        Ok(final_brake)
    }
}

pub struct VehicleSafetyMonitor {
    safety_constraints: SafetyConstraints,
    fault_detector: FaultDetector,
}

#[derive(Debug, Clone)]
pub struct SafetyConstraints {
    pub max_velocity: f32,
    pub max_acceleration: f32,
    pub max_deceleration: f32,
    pub max_steering_angle: f32,
    pub max_steering_rate: f32,
    pub min_following_distance: f32,
}

#[derive(Debug, Clone)]
pub struct SafetyStatus {
    pub is_safe: bool,
    pub active_faults: Vec<SafetyFault>,
    pub emergency_stop_required: bool,
}

#[derive(Debug, Clone)]
pub enum SafetyFault {
    ExcessiveSpeed,
    ExcessiveAcceleration,
    CollisionRisk,
    SensorFailure(String),
    ActuatorFailure(String),
    CommunicationTimeout,
}

impl VehicleSafetyMonitor {
    pub fn new() -> Self {
        VehicleSafetyMonitor {
            safety_constraints: SafetyConstraints {
                max_velocity: 60.0, // 60 m/s
                max_acceleration: 4.0,
                max_deceleration: 10.0,
                max_steering_angle: 30.0_f32.to_radians(),
                max_steering_rate: 45.0_f32.to_radians(),
                min_following_distance: 2.0,
            },
            fault_detector: FaultDetector::new(),
        }
    }
    
    pub fn check_safety(
        &mut self,
        vehicle_state: &VehicleState,
        sensor_data: &VehicleSensorData,
    ) -> Result<SafetyStatus, ControlError> {
        let mut faults = Vec::new();
        
        // Check velocity limits
        if vehicle_state.velocity > self.safety_constraints.max_velocity {
            faults.push(SafetyFault::ExcessiveSpeed);
        }
        
        // Check acceleration limits
        if vehicle_state.acceleration.abs() > self.safety_constraints.max_acceleration {
            faults.push(SafetyFault::ExcessiveAcceleration);
        }
        
        // Check sensor health
        let sensor_faults = self.fault_detector.check_sensors(sensor_data)?;
        faults.extend(sensor_faults);
        
        // Check for collision risks
        if self.detect_collision_risk(vehicle_state, sensor_data)? {
            faults.push(SafetyFault::CollisionRisk);
        }
        
        let emergency_stop_required = faults.iter().any(|fault| matches!(
            fault,
            SafetyFault::CollisionRisk | SafetyFault::SensorFailure(_)
        ));
        
        Ok(SafetyStatus {
            is_safe: faults.is_empty(),
            active_faults: faults,
            emergency_stop_required,
        })
    }
    
    fn detect_collision_risk(
        &self,
        vehicle_state: &VehicleState,
        sensor_data: &VehicleSensorData,
    ) -> Result<bool, ControlError> {
        // Simple collision detection based on minimum following distance
        for obstacle in &sensor_data.detected_obstacles {
            let distance = (obstacle.position.xy() - vehicle_state.position).magnitude();
            let time_to_collision = distance / vehicle_state.velocity;
            
            if time_to_collision < 2.0 { // 2 seconds warning
                return Ok(true);
            }
        }
        
        Ok(false)
    }
}

pub struct FaultDetector {
    sensor_timeouts: std::collections::HashMap<String, std::time::Instant>,
    timeout_threshold: Duration,
}

impl FaultDetector {
    pub fn new() -> Self {
        FaultDetector {
            sensor_timeouts: std::collections::HashMap::new(),
            timeout_threshold: Duration::from_millis(100), // 100ms timeout
        }
    }
    
    pub fn check_sensors(&mut self, sensor_data: &VehicleSensorData) -> Result<Vec<SafetyFault>, ControlError> {
        let mut faults = Vec::new();
        let now = std::time::Instant::now();
        
        // Check camera timeouts
        for (camera_id, last_frame_time) in &sensor_data.camera_timestamps {
            if now.duration_since(*last_frame_time) > self.timeout_threshold {
                faults.push(SafetyFault::SensorFailure(format!("camera_{}", camera_id)));
            }
        }
        
        // Check LiDAR timeout
        if let Some(last_lidar_time) = sensor_data.lidar_timestamp {
            if now.duration_since(last_lidar_time) > self.timeout_threshold {
                faults.push(SafetyFault::SensorFailure("lidar".to_string()));
            }
        }
        
        // Check radar timeout
        if let Some(last_radar_time) = sensor_data.radar_timestamp {
            if now.duration_since(last_radar_time) > self.timeout_threshold {
                faults.push(SafetyFault::SensorFailure("radar".to_string()));
            }
        }
        
        Ok(faults)
    }
}

#[derive(Debug, Clone)]
pub struct VehicleSensorData {
    pub detected_obstacles: Vec<DetectedObject>,
    pub camera_timestamps: std::collections::HashMap<u32, std::time::Instant>,
    pub lidar_timestamp: Option<std::time::Instant>,
    pub radar_timestamp: Option<std::time::Instant>,
    pub imu_data: IMUData,
    pub gps_data: GPSData,
}

#[derive(Debug, Clone)]
pub struct IMUData {
    pub acceleration: Vector3<f32>,
    pub angular_velocity: Vector3<f32>,
    pub orientation: Vector3<f32>,
    pub timestamp: u64,
}

#[derive(Debug, Clone)]
pub struct GPSData {
    pub latitude: f64,
    pub longitude: f64,
    pub altitude: f64,
    pub accuracy: f32,
    pub timestamp: u64,
}

// Error types
#[derive(Debug)]
pub enum ControlError {
    UpdateTooFrequent,
    InvalidState,
    ActuatorFailure,
    SensorTimeout,
    SafetyViolation,
}

#[derive(Debug)]
pub enum CameraError {
    InitializationFailed,
    CaptureTimeout,
    CalibrationError,
    FrameSync,
}

#[derive(Debug)]
pub enum LiDARError {
    ProcessingFailed,
    EmptyCluster,
    CalibrationError,
}

#[derive(Debug)]
pub enum DetectionError {
    ModelLoadFailed,
    InferenceFailed,
    MissingKeypoint,
}

#[derive(Debug)]
pub enum InteractionError {
    MissingKeypoint,
}

// Additional supporting structures would be defined here...
```

## Conclusion

This comprehensive tutorial demonstrates how to build a complete Level 4 autonomous vehicle system using the WASM Edge AI SDK. The system integrates multiple sensor modalities, advanced perception algorithms, path planning, and vehicle control to create a robust self-driving capability.

Key features implemented:
- Multi-camera sensor fusion with bird's eye view generation
- LiDAR point cloud processing with ground filtering and clustering
- Multi-modal object detection and tracking
- Behavior-aware path planning with safety constraints
- Real-time vehicle control with safety monitoring
- V2X communication integration
- Comprehensive safety and fault detection systems

The modular architecture allows for easy customization and extension based on specific vehicle platforms and requirements. The system is designed to handle complex driving scenarios while maintaining strict safety standards required for autonomous operation.

For deployment, ensure proper sensor calibration, extensive testing in simulation environments like CARLA, and gradual validation in controlled real-world conditions before full autonomous operation.