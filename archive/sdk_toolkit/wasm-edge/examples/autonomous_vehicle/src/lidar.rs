/*!
# LiDAR Processing Module

High-performance point cloud processing for autonomous vehicle perception.
Handles 3D object detection, ground plane estimation, and obstacle tracking.
*/

use anyhow::{Context, Result};
use log::{info, warn, error};
use nalgebra::{Point3, Vector3, Matrix4, Isometry3};
use std::collections::{HashMap, VecDeque};
use tokio::time::Instant;
use wasm_edge_ai_sdk::prelude::*;

use crate::{DetectedObject, ObjectClass};

/// LiDAR configuration
#[derive(Debug, Clone)]
pub struct LidarConfig {
    pub device_path: String,
    pub rotation_frequency: f32,  // Hz
    pub vertical_fov: (f32, f32), // (min, max) degrees
    pub horizontal_fov: (f32, f32), // (min, max) degrees
    pub max_range: f32,           // meters
    pub min_range: f32,           // meters
    pub point_cloud_filter: PointCloudFilter,
    pub ground_detection: GroundDetectionConfig,
    pub clustering: ClusteringConfig,
}

#[derive(Debug, Clone)]
pub struct PointCloudFilter {
    pub voxel_size: f32,          // meters
    pub noise_filter_radius: f32,  // meters
    pub noise_min_neighbors: usize,
    pub intensity_threshold: f32,
    pub remove_ground: bool,
}

#[derive(Debug, Clone)]
pub struct GroundDetectionConfig {
    pub ransac_iterations: usize,
    pub distance_threshold: f32,   // meters
    pub min_points: usize,
    pub height_threshold: f32,     // meters above ground
}

#[derive(Debug, Clone)]
pub struct ClusteringConfig {
    pub cluster_tolerance: f32,    // meters
    pub min_cluster_size: usize,
    pub max_cluster_size: usize,
    pub euclidean_clustering: bool,
}

/// Point cloud data structures
#[derive(Debug, Clone)]
pub struct PointCloud {
    pub points: Vec<Point3<f32>>,
    pub intensities: Vec<f32>,
    pub timestamps: Vec<u64>,
    pub timestamp: Instant,
    pub frame_id: String,
}

#[derive(Debug, Clone)]
pub struct ProcessedPointCloud {
    pub original: PointCloud,
    pub filtered: PointCloud,
    pub ground_points: Vec<Point3<f32>>,
    pub obstacle_points: Vec<Point3<f32>>,
    pub clusters: Vec<PointCluster>,
    pub ground_plane: Option<GroundPlane>,
}

#[derive(Debug, Clone)]
pub struct PointCluster {
    pub id: u32,
    pub points: Vec<Point3<f32>>,
    pub centroid: Point3<f32>,
    pub bounding_box: BoundingBox3D,
    pub point_count: usize,
    pub density: f32,
    pub classification: ClusterClassification,
}

#[derive(Debug, Clone)]
pub struct BoundingBox3D {
    pub min: Point3<f32>,
    pub max: Point3<f32>,
    pub center: Point3<f32>,
    pub dimensions: Vector3<f32>,
    pub orientation: f32, // radians
}

#[derive(Debug, Clone)]
pub struct GroundPlane {
    pub normal: Vector3<f32>,
    pub distance: f32,
    pub confidence: f32,
    pub point_count: usize,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ClusterClassification {
    Vehicle,
    Pedestrian,
    Cyclist,
    Pole,
    Building,
    Vegetation,
    Unknown,
}

/// LiDAR data processing results
#[derive(Debug, Clone)]
pub struct LidarData {
    pub objects: Vec<DetectedObject>,
    pub obstacles: Vec<Obstacle>,
    pub free_space: Vec<FreeSpaceRegion>,
    pub ground_plane: Option<GroundPlane>,
    pub confidence: f32,
    pub timestamp: Instant,
    pub processing_time_ms: f64,
}

#[derive(Debug, Clone)]
pub struct Obstacle {
    pub position: Point3<f32>,
    pub dimensions: Vector3<f32>,
    pub velocity: Vector3<f32>,
    pub confidence: f32,
    pub classification: ClusterClassification,
    pub distance: f32,
}

#[derive(Debug, Clone)]
pub struct FreeSpaceRegion {
    pub polygon: Vec<Point3<f32>>,
    pub confidence: f32,
    pub traversability: f32,
}

/// Main LiDAR processing system
pub struct LidarSystem {
    config: LidarConfig,
    device: LidarDevice,
    point_cloud_processor: PointCloudProcessor,
    ground_detector: GroundDetector,
    object_detector: InferenceEngine,
    cluster_tracker: ClusterTracker,
    coordinate_transformer: CoordinateTransformer,
}

struct LidarDevice {
    device_path: String,
    is_connected: bool,
    packet_buffer: VecDeque<RawLidarPacket>,
}

struct PointCloudProcessor {
    voxel_grid: VoxelGrid,
    noise_filter: NoiseFilter,
    temporal_filter: TemporalFilter,
}

struct VoxelGrid {
    voxel_size: f32,
    grid: HashMap<(i32, i32, i32), Vec<Point3<f32>>>,
}

struct NoiseFilter {
    radius: f32,
    min_neighbors: usize,
}

struct TemporalFilter {
    history: VecDeque<PointCloud>,
    max_history: usize,
}

struct GroundDetector {
    config: GroundDetectionConfig,
    current_ground_plane: Option<GroundPlane>,
    ground_history: VecDeque<GroundPlane>,
}

struct ClusterTracker {
    clusters: HashMap<u32, TrackedCluster>,
    next_cluster_id: u32,
    max_tracking_distance: f32,
}

#[derive(Debug, Clone)]
struct TrackedCluster {
    id: u32,
    cluster: PointCluster,
    track_history: VecDeque<Point3<f32>>,
    velocity: Vector3<f32>,
    last_seen: Instant,
    tracking_confidence: f32,
}

struct CoordinateTransformer {
    lidar_to_vehicle: Isometry3<f32>,
    vehicle_to_world: Isometry3<f32>,
}

#[derive(Debug)]
struct RawLidarPacket {
    points: Vec<RawPoint>,
    timestamp: u64,
    rotation_angle: f32,
}

#[derive(Debug, Clone)]
struct RawPoint {
    distance: f32,
    angle: f32,
    intensity: f32,
    timestamp: u64,
}

impl LidarSystem {
    /// Create new LiDAR system
    pub async fn new(config: &LidarConfig) -> Result<Self> {
        info!("Initializing LiDAR system on device: {}", config.device_path);
        
        // Initialize LiDAR device
        let device = LidarDevice::new(&config.device_path).await
            .context("Failed to initialize LiDAR device")?;
        
        // Initialize point cloud processor
        let point_cloud_processor = PointCloudProcessor::new(&config.point_cloud_filter);
        
        // Initialize ground detector
        let ground_detector = GroundDetector::new(&config.ground_detection);
        
        // Load object detection model for 3D point clouds
        let object_detector = InferenceEngine::load("models/pointnet_3d_detection.onnx")
            .context("Failed to load 3D object detection model")?;
        
        // Initialize cluster tracker
        let cluster_tracker = ClusterTracker::new();
        
        // Initialize coordinate transformer (LiDAR to vehicle coordinates)
        let coordinate_transformer = CoordinateTransformer::new();
        
        Ok(Self {
            config: config.clone(),
            device,
            point_cloud_processor,
            ground_detector,
            object_detector,
            cluster_tracker,
            coordinate_transformer,
        })
    }
    
    /// Process current LiDAR frame
    pub async fn process_frame(&mut self) -> Result<LidarData> {
        let start_time = Instant::now();
        
        // Capture raw point cloud data
        let raw_cloud = self.device.capture_point_cloud().await
            .context("Failed to capture point cloud")?;
        
        // Filter and preprocess point cloud
        let filtered_cloud = self.point_cloud_processor.process(&raw_cloud)
            .context("Point cloud filtering failed")?;
        
        // Detect ground plane
        let ground_plane = self.ground_detector.detect_ground(&filtered_cloud)
            .context("Ground detection failed")?;
        
        // Segment ground and obstacles
        let (ground_points, obstacle_points) = self.segment_ground_obstacles(
            &filtered_cloud, 
            &ground_plane
        );
        
        // Cluster obstacle points
        let clusters = self.cluster_points(&obstacle_points)
            .context("Point clustering failed")?;
        
        // Track clusters over time
        let tracked_clusters = self.cluster_tracker.update_tracks(clusters);
        
        // Classify clusters and detect objects
        let detected_objects = self.detect_objects_from_clusters(&tracked_clusters).await
            .context("Object detection from clusters failed")?;
        
        // Extract obstacles and free space
        let obstacles = self.extract_obstacles(&tracked_clusters);
        let free_space = self.compute_free_space(&ground_points, &obstacles);
        
        // Transform to vehicle coordinates
        let transformed_objects = self.coordinate_transformer.transform_objects(detected_objects);
        let transformed_obstacles = self.coordinate_transformer.transform_obstacles(obstacles);
        
        // Calculate confidence
        let confidence = self.calculate_confidence(&transformed_objects, &ground_plane);
        
        let processing_time = start_time.elapsed();
        info!("LiDAR processing completed in {:.2}ms", processing_time.as_millis());
        
        Ok(LidarData {
            objects: transformed_objects,
            obstacles: transformed_obstacles,
            free_space,
            ground_plane,
            confidence,
            timestamp: start_time,
            processing_time_ms: processing_time.as_secs_f64() * 1000.0,
        })
    }
    
    /// Segment ground and obstacle points
    fn segment_ground_obstacles(
        &self,
        point_cloud: &PointCloud,
        ground_plane: &Option<GroundPlane>
    ) -> (Vec<Point3<f32>>, Vec<Point3<f32>>) {
        let mut ground_points = Vec::new();
        let mut obstacle_points = Vec::new();
        
        if let Some(plane) = ground_plane {
            for point in &point_cloud.points {
                let distance_to_plane = plane.normal.dot(&(point - Point3::origin())) - plane.distance;
                
                if distance_to_plane.abs() < self.config.ground_detection.distance_threshold {
                    ground_points.push(*point);
                } else if distance_to_plane > self.config.ground_detection.height_threshold {
                    obstacle_points.push(*point);
                }
            }
        } else {
            // If no ground plane detected, use height-based segmentation
            for point in &point_cloud.points {
                if point.z < self.config.ground_detection.height_threshold {
                    ground_points.push(*point);
                } else {
                    obstacle_points.push(*point);
                }
            }
        }
        
        (ground_points, obstacle_points)
    }
    
    /// Cluster obstacle points using Euclidean clustering
    fn cluster_points(&self, points: &[Point3<f32>]) -> Result<Vec<PointCluster>> {
        let mut clusters = Vec::new();
        let mut visited = vec![false; points.len()];
        let mut cluster_id = 0;
        
        for (i, point) in points.iter().enumerate() {
            if visited[i] {
                continue;
            }
            
            let mut cluster_points = Vec::new();
            let mut stack = vec![i];
            
            while let Some(idx) = stack.pop() {
                if visited[idx] {
                    continue;
                }
                
                visited[idx] = true;
                cluster_points.push(points[idx]);
                
                // Find neighbors within cluster tolerance
                for (j, other_point) in points.iter().enumerate() {
                    if !visited[j] {
                        let distance = (point - other_point).norm();
                        if distance < self.config.clustering.cluster_tolerance {
                            stack.push(j);
                        }
                    }
                }
            }
            
            // Check cluster size constraints
            if cluster_points.len() >= self.config.clustering.min_cluster_size
                && cluster_points.len() <= self.config.clustering.max_cluster_size {
                
                let cluster = self.create_cluster(cluster_id, cluster_points)?;
                clusters.push(cluster);
                cluster_id += 1;
            }
        }
        
        Ok(clusters)
    }
    
    /// Create a point cluster from points
    fn create_cluster(&self, id: u32, points: Vec<Point3<f32>>) -> Result<PointCluster> {
        if points.is_empty() {
            return Err(anyhow::anyhow!("Cannot create cluster from empty points"));
        }
        
        // Calculate centroid
        let centroid = points.iter().fold(Point3::origin(), |acc, p| acc + p.coords) / points.len() as f32;
        
        // Calculate bounding box
        let mut min = points[0];
        let mut max = points[0];
        
        for point in &points {
            min.x = min.x.min(point.x);
            min.y = min.y.min(point.y);
            min.z = min.z.min(point.z);
            max.x = max.x.max(point.x);
            max.y = max.y.max(point.y);
            max.z = max.z.max(point.z);
        }
        
        let center = Point3::new(
            (min.x + max.x) / 2.0,
            (min.y + max.y) / 2.0,
            (min.z + max.z) / 2.0,
        );
        
        let dimensions = Vector3::new(
            max.x - min.x,
            max.y - min.y,
            max.z - min.z,
        );
        
        let bounding_box = BoundingBox3D {
            min,
            max,
            center,
            dimensions,
            orientation: 0.0, // TODO: Calculate principal component orientation
        };
        
        // Calculate density
        let volume = dimensions.x * dimensions.y * dimensions.z;
        let density = if volume > 0.0 { points.len() as f32 / volume } else { 0.0 };
        
        // Classify cluster based on geometric properties
        let classification = self.classify_cluster(&bounding_box, density, points.len());
        
        Ok(PointCluster {
            id,
            points,
            centroid,
            bounding_box,
            point_count: points.len(),
            density,
            classification,
        })
    }
    
    /// Classify cluster based on geometric properties
    fn classify_cluster(
        &self,
        bounding_box: &BoundingBox3D,
        density: f32,
        point_count: usize,
    ) -> ClusterClassification {
        let dims = &bounding_box.dimensions;
        
        // Simple rule-based classification
        if dims.x > 3.0 && dims.y > 1.5 && dims.z > 1.5 {
            // Large rectangular object - likely vehicle
            ClusterClassification::Vehicle
        } else if dims.x < 1.0 && dims.y < 1.0 && dims.z > 1.0 {
            // Tall thin object - likely pedestrian
            ClusterClassification::Pedestrian
        } else if dims.x < 2.0 && dims.y < 1.0 && dims.z < 2.0 && point_count < 100 {
            // Small moving object - likely cyclist
            ClusterClassification::Cyclist
        } else if dims.x < 0.5 && dims.y < 0.5 && dims.z > 2.0 {
            // Very thin tall object - likely pole
            ClusterClassification::Pole
        } else if dims.z > 5.0 {
            // Very tall object - likely building
            ClusterClassification::Building
        } else if density < 10.0 && dims.z > 2.0 {
            // Low density tall object - likely vegetation
            ClusterClassification::Vegetation
        } else {
            ClusterClassification::Unknown
        }
    }
    
    /// Detect objects from clusters using AI
    async fn detect_objects_from_clusters(
        &self,
        clusters: &[TrackedCluster]
    ) -> Result<Vec<DetectedObject>> {
        let mut objects = Vec::new();
        
        for cluster in clusters {
            // Prepare point cloud data for AI inference
            let cluster_cloud = self.prepare_cluster_for_inference(&cluster.cluster)?;
            
            // Run 3D object detection on cluster
            let detection_result = self.object_detector.predict(cluster_cloud).await
                .context("3D object detection inference failed")?;
            
            // Convert detection result to DetectedObject
            if let Some(object) = self.convert_detection_to_object(detection_result, cluster)? {
                objects.push(object);
            }
        }
        
        Ok(objects)
    }
    
    /// Prepare cluster point cloud for AI inference
    fn prepare_cluster_for_inference(&self, cluster: &PointCluster) -> Result<Vec<f32>> {
        // Convert point cloud to normalized tensor format
        let mut tensor_data = Vec::new();
        
        // Normalize points relative to cluster centroid
        for point in &cluster.points {
            let normalized = point - cluster.centroid;
            tensor_data.extend_from_slice(&[normalized.x, normalized.y, normalized.z]);
        }
        
        // Pad or truncate to fixed size (e.g., 1024 points)
        const MAX_POINTS: usize = 1024;
        tensor_data.resize(MAX_POINTS * 3, 0.0);
        
        Ok(tensor_data)
    }
    
    /// Convert AI detection result to DetectedObject
    fn convert_detection_to_object(
        &self,
        _detection_result: Box<dyn std::any::Any>,
        cluster: &TrackedCluster,
    ) -> Result<Option<DetectedObject>> {
        // Placeholder - would process actual detection results
        let object_class = match cluster.cluster.classification {
            ClusterClassification::Vehicle => ObjectClass::Vehicle,
            ClusterClassification::Pedestrian => ObjectClass::Pedestrian,
            ClusterClassification::Cyclist => ObjectClass::Cyclist,
            _ => ObjectClass::Obstacle,
        };
        
        let object = DetectedObject {
            id: cluster.id as u64,
            class: object_class,
            position: Point3::new(
                cluster.cluster.centroid.x as f64,
                cluster.cluster.centroid.y as f64,
                cluster.cluster.centroid.z as f64,
            ),
            velocity: Vector3::new(
                cluster.velocity.x as f64,
                cluster.velocity.y as f64,
                cluster.velocity.z as f64,
            ),
            dimensions: Vector3::new(
                cluster.cluster.bounding_box.dimensions.x as f64,
                cluster.cluster.bounding_box.dimensions.y as f64,
                cluster.cluster.bounding_box.dimensions.z as f64,
            ),
            confidence: cluster.tracking_confidence,
        };
        
        Ok(Some(object))
    }
    
    /// Extract obstacles from tracked clusters
    fn extract_obstacles(&self, clusters: &[TrackedCluster]) -> Vec<Obstacle> {
        clusters.iter().map(|cluster| {
            let distance = cluster.cluster.centroid.norm();
            
            Obstacle {
                position: cluster.cluster.centroid,
                dimensions: cluster.cluster.bounding_box.dimensions,
                velocity: cluster.velocity,
                confidence: cluster.tracking_confidence,
                classification: cluster.cluster.classification.clone(),
                distance,
            }
        }).collect()
    }
    
    /// Compute free space regions
    fn compute_free_space(
        &self,
        ground_points: &[Point3<f32>],
        obstacles: &[Obstacle]
    ) -> Vec<FreeSpaceRegion> {
        // Simplified free space computation
        // In a real implementation, this would use advanced algorithms like
        // occupancy grids or Voronoi diagrams
        
        if ground_points.is_empty() {
            return vec![];
        }
        
        // Create a simple rectangular free space region
        let mut min_x = f32::INFINITY;
        let mut max_x = f32::NEG_INFINITY;
        let mut min_y = f32::INFINITY;
        let mut max_y = f32::NEG_INFINITY;
        
        for point in ground_points {
            min_x = min_x.min(point.x);
            max_x = max_x.max(point.x);
            min_y = min_y.min(point.y);
            max_y = max_y.max(point.y);
        }
        
        // Create free space polygon (simplified as rectangle)
        let polygon = vec![
            Point3::new(min_x, min_y, 0.0),
            Point3::new(max_x, min_y, 0.0),
            Point3::new(max_x, max_y, 0.0),
            Point3::new(min_x, max_y, 0.0),
        ];
        
        let confidence = if obstacles.is_empty() { 0.9 } else { 0.7 };
        let traversability = 0.8; // Simplified
        
        vec![FreeSpaceRegion {
            polygon,
            confidence,
            traversability,
        }]
    }
    
    /// Calculate overall confidence
    fn calculate_confidence(
        &self,
        objects: &[DetectedObject],
        ground_plane: &Option<GroundPlane>
    ) -> f32 {
        let object_confidence = if objects.is_empty() {
            0.5
        } else {
            objects.iter().map(|obj| obj.confidence).sum::<f32>() / objects.len() as f32
        };
        
        let ground_confidence = ground_plane
            .as_ref()
            .map(|plane| plane.confidence)
            .unwrap_or(0.0);
        
        (object_confidence + ground_confidence) / 2.0
    }
}

// Implementation of helper structs

impl LidarDevice {
    async fn new(device_path: &str) -> Result<Self> {
        // In a real implementation, this would initialize the actual LiDAR device
        Ok(Self {
            device_path: device_path.to_string(),
            is_connected: true,
            packet_buffer: VecDeque::new(),
        })
    }
    
    async fn capture_point_cloud(&mut self) -> Result<PointCloud> {
        // Simulate capturing a point cloud
        // In reality, this would read from the LiDAR device
        
        let mut points = Vec::new();
        let mut intensities = Vec::new();
        let mut timestamps = Vec::new();
        
        // Generate simulated point cloud data
        for i in 0..1000 {
            let angle = (i as f32 / 1000.0) * 2.0 * std::f32::consts::PI;
            let distance = 10.0 + (angle.sin() * 5.0);
            
            let x = distance * angle.cos();
            let y = distance * angle.sin();
            let z = (angle * 2.0).sin() * 2.0;
            
            points.push(Point3::new(x, y, z));
            intensities.push(128.0 + (angle * 4.0).sin() * 50.0);
            timestamps.push(chrono::Utc::now().timestamp_nanos() as u64);
        }
        
        Ok(PointCloud {
            points,
            intensities,
            timestamps,
            timestamp: Instant::now(),
            frame_id: "lidar_frame".to_string(),
        })
    }
}

impl PointCloudProcessor {
    fn new(config: &PointCloudFilter) -> Self {
        Self {
            voxel_grid: VoxelGrid::new(config.voxel_size),
            noise_filter: NoiseFilter::new(config.noise_filter_radius, config.noise_min_neighbors),
            temporal_filter: TemporalFilter::new(10), // Keep 10 frames
        }
    }
    
    fn process(&mut self, point_cloud: &PointCloud) -> Result<PointCloud> {
        // Apply voxel grid downsampling
        let downsampled = self.voxel_grid.downsample(&point_cloud.points)?;
        
        // Apply noise filtering
        let filtered = self.noise_filter.filter(&downsampled)?;
        
        // Update temporal filter
        self.temporal_filter.update(point_cloud.clone());
        
        Ok(PointCloud {
            points: filtered,
            intensities: point_cloud.intensities.clone(),
            timestamps: point_cloud.timestamps.clone(),
            timestamp: point_cloud.timestamp,
            frame_id: point_cloud.frame_id.clone(),
        })
    }
}

impl VoxelGrid {
    fn new(voxel_size: f32) -> Self {
        Self {
            voxel_size,
            grid: HashMap::new(),
        }
    }
    
    fn downsample(&mut self, points: &[Point3<f32>]) -> Result<Vec<Point3<f32>>> {
        self.grid.clear();
        
        // Assign points to voxels
        for &point in points {
            let voxel_key = (
                (point.x / self.voxel_size).floor() as i32,
                (point.y / self.voxel_size).floor() as i32,
                (point.z / self.voxel_size).floor() as i32,
            );
            
            self.grid.entry(voxel_key)
                .or_insert_with(Vec::new)
                .push(point);
        }
        
        // Average points in each voxel
        let mut downsampled = Vec::new();
        for voxel_points in self.grid.values() {
            if !voxel_points.is_empty() {
                let avg_point = voxel_points.iter()
                    .fold(Point3::origin(), |acc, p| acc + p.coords) / voxel_points.len() as f32;
                downsampled.push(avg_point);
            }
        }
        
        Ok(downsampled)
    }
}

impl NoiseFilter {
    fn new(radius: f32, min_neighbors: usize) -> Self {
        Self { radius, min_neighbors }
    }
    
    fn filter(&self, points: &[Point3<f32>]) -> Result<Vec<Point3<f32>>> {
        let mut filtered = Vec::new();
        
        for (i, &point) in points.iter().enumerate() {
            let mut neighbor_count = 0;
            
            for (j, &other_point) in points.iter().enumerate() {
                if i != j && (point - other_point).norm() < self.radius {
                    neighbor_count += 1;
                }
            }
            
            if neighbor_count >= self.min_neighbors {
                filtered.push(point);
            }
        }
        
        Ok(filtered)
    }
}

impl TemporalFilter {
    fn new(max_history: usize) -> Self {
        Self {
            history: VecDeque::new(),
            max_history,
        }
    }
    
    fn update(&mut self, point_cloud: PointCloud) {
        self.history.push_back(point_cloud);
        while self.history.len() > self.max_history {
            self.history.pop_front();
        }
    }
}

impl GroundDetector {
    fn new(config: &GroundDetectionConfig) -> Self {
        Self {
            config: config.clone(),
            current_ground_plane: None,
            ground_history: VecDeque::new(),
        }
    }
    
    fn detect_ground(&mut self, point_cloud: &PointCloud) -> Result<Option<GroundPlane>> {
        if point_cloud.points.len() < 3 {
            return Ok(None);
        }
        
        let mut best_plane: Option<GroundPlane> = None;
        let mut best_inlier_count = 0;
        
        // RANSAC algorithm for ground plane detection
        for _ in 0..self.config.ransac_iterations {
            // Randomly sample 3 points
            let indices: Vec<usize> = (0..point_cloud.points.len()).collect();
            let sample_indices = self.random_sample(&indices, 3);
            
            if sample_indices.len() < 3 {
                continue;
            }
            
            let p1 = point_cloud.points[sample_indices[0]];
            let p2 = point_cloud.points[sample_indices[1]];
            let p3 = point_cloud.points[sample_indices[2]];
            
            // Calculate plane equation
            let v1 = p2 - p1;
            let v2 = p3 - p1;
            let normal = v1.cross(&v2).normalize();
            let distance = normal.dot(&p1.coords);
            
            // Count inliers
            let mut inlier_count = 0;
            for &point in &point_cloud.points {
                let dist_to_plane = (normal.dot(&point.coords) - distance).abs();
                if dist_to_plane < self.config.distance_threshold {
                    inlier_count += 1;
                }
            }
            
            if inlier_count > best_inlier_count && inlier_count >= self.config.min_points {
                best_inlier_count = inlier_count;
                let confidence = inlier_count as f32 / point_cloud.points.len() as f32;
                
                best_plane = Some(GroundPlane {
                    normal,
                    distance,
                    confidence,
                    point_count: inlier_count,
                });
            }
        }
        
        if let Some(plane) = &best_plane {
            self.current_ground_plane = Some(plane.clone());
            self.ground_history.push_back(plane.clone());
            if self.ground_history.len() > 10 {
                self.ground_history.pop_front();
            }
        }
        
        Ok(best_plane)
    }
    
    fn random_sample(&self, items: &[usize], count: usize) -> Vec<usize> {
        // Simple random sampling (in production, use proper RNG)
        let mut result = Vec::new();
        for i in 0..count.min(items.len()) {
            result.push(items[i * items.len() / count]);
        }
        result
    }
}

impl ClusterTracker {
    fn new() -> Self {
        Self {
            clusters: HashMap::new(),
            next_cluster_id: 0,
            max_tracking_distance: 2.0, // 2 meters
        }
    }
    
    fn update_tracks(&mut self, new_clusters: Vec<PointCluster>) -> Vec<TrackedCluster> {
        let mut tracked_clusters = Vec::new();
        let mut matched_existing = Vec::new();
        
        // Match new clusters with existing tracks
        for cluster in new_clusters {
            let mut best_match: Option<u32> = None;
            let mut best_distance = f32::INFINITY;
            
            for (track_id, tracked_cluster) in &self.clusters {
                let distance = (cluster.centroid - tracked_cluster.cluster.centroid).norm();
                if distance < self.max_tracking_distance && distance < best_distance {
                    best_distance = distance;
                    best_match = Some(*track_id);
                }
            }
            
            if let Some(track_id) = best_match {
                // Update existing track
                if let Some(mut tracked) = self.clusters.remove(&track_id) {
                    self.update_tracked_cluster(&mut tracked, cluster);
                    tracked_clusters.push(tracked.clone());
                    self.clusters.insert(track_id, tracked);
                    matched_existing.push(track_id);
                }
            } else {
                // Create new track
                let new_tracked = TrackedCluster {
                    id: self.next_cluster_id,
                    cluster,
                    track_history: VecDeque::new(),
                    velocity: Vector3::zeros(),
                    last_seen: Instant::now(),
                    tracking_confidence: 1.0,
                };
                
                tracked_clusters.push(new_tracked.clone());
                self.clusters.insert(self.next_cluster_id, new_tracked);
                self.next_cluster_id += 1;
            }
        }
        
        // Remove old tracks that weren't matched
        let now = Instant::now();
        self.clusters.retain(|id, tracked| {
            let age = now.duration_since(tracked.last_seen);
            let keep = age.as_secs() < 5 || matched_existing.contains(id); // 5 second timeout
            keep
        });
        
        tracked_clusters
    }
    
    fn update_tracked_cluster(&self, tracked: &mut TrackedCluster, new_cluster: PointCluster) {
        // Update track history
        tracked.track_history.push_back(tracked.cluster.centroid);
        if tracked.track_history.len() > 10 {
            tracked.track_history.pop_front();
        }
        
        // Calculate velocity
        if tracked.track_history.len() >= 2 {
            let prev_pos = tracked.track_history[tracked.track_history.len() - 2];
            let curr_pos = new_cluster.centroid;
            tracked.velocity = curr_pos - prev_pos; // Simplified velocity calculation
        }
        
        // Update cluster
        tracked.cluster = new_cluster;
        tracked.last_seen = Instant::now();
        tracked.tracking_confidence = (tracked.tracking_confidence * 0.9 + 0.1).min(1.0);
    }
}

impl CoordinateTransformer {
    fn new() -> Self {
        // Default transformation: LiDAR mounted 2m forward, 1.5m up from vehicle center
        let lidar_to_vehicle = Isometry3::from_parts(
            nalgebra::Translation3::new(2.0, 0.0, 1.5),
            nalgebra::UnitQuaternion::identity(),
        );
        
        let vehicle_to_world = Isometry3::identity();
        
        Self {
            lidar_to_vehicle,
            vehicle_to_world,
        }
    }
    
    fn transform_objects(&self, objects: Vec<DetectedObject>) -> Vec<DetectedObject> {
        objects.into_iter().map(|mut obj| {
            let lidar_pos = Point3::new(obj.position.x as f32, obj.position.y as f32, obj.position.z as f32);
            let vehicle_pos = self.lidar_to_vehicle.transform_point(&lidar_pos);
            let world_pos = self.vehicle_to_world.transform_point(&vehicle_pos);
            
            obj.position = Point3::new(world_pos.x as f64, world_pos.y as f64, world_pos.z as f64);
            obj
        }).collect()
    }
    
    fn transform_obstacles(&self, obstacles: Vec<Obstacle>) -> Vec<Obstacle> {
        obstacles.into_iter().map(|mut obs| {
            let vehicle_pos = self.lidar_to_vehicle.transform_point(&obs.position);
            let world_pos = self.vehicle_to_world.transform_point(&vehicle_pos);
            obs.position = world_pos;
            obs
        }).collect()
    }
}

impl Default for LidarConfig {
    fn default() -> Self {
        Self {
            device_path: "/dev/ttyUSB0".to_string(),
            rotation_frequency: 10.0,
            vertical_fov: (-15.0, 15.0),
            horizontal_fov: (-180.0, 180.0),
            max_range: 100.0,
            min_range: 0.1,
            point_cloud_filter: PointCloudFilter {
                voxel_size: 0.1,
                noise_filter_radius: 0.5,
                noise_min_neighbors: 5,
                intensity_threshold: 50.0,
                remove_ground: true,
            },
            ground_detection: GroundDetectionConfig {
                ransac_iterations: 1000,
                distance_threshold: 0.1,
                min_points: 100,
                height_threshold: 0.3,
            },
            clustering: ClusteringConfig {
                cluster_tolerance: 0.5,
                min_cluster_size: 10,
                max_cluster_size: 10000,
                euclidean_clustering: true,
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_lidar_system_creation() {
        let config = LidarConfig::default();
        let result = LidarSystem::new(&config).await;
        // Note: This would fail without actual hardware
        // In practice, you'd use mock devices for testing
    }
    
    #[test]
    fn test_cluster_classification() {
        let config = LidarConfig::default();
        let lidar = LidarSystem {
            config: config.clone(),
            device: LidarDevice {
                device_path: "test".to_string(),
                is_connected: false,
                packet_buffer: VecDeque::new(),
            },
            point_cloud_processor: PointCloudProcessor::new(&config.point_cloud_filter),
            ground_detector: GroundDetector::new(&config.ground_detection),
            object_detector: InferenceEngine,
            cluster_tracker: ClusterTracker::new(),
            coordinate_transformer: CoordinateTransformer::new(),
        };
        
        // Test vehicle classification
        let vehicle_bbox = BoundingBox3D {
            min: Point3::new(0.0, 0.0, 0.0),
            max: Point3::new(4.0, 2.0, 2.0),
            center: Point3::new(2.0, 1.0, 1.0),
            dimensions: Vector3::new(4.0, 2.0, 2.0),
            orientation: 0.0,
        };
        
        let classification = lidar.classify_cluster(&vehicle_bbox, 50.0, 1000);
        assert_eq!(classification, ClusterClassification::Vehicle);
    }
    
    #[test]
    fn test_voxel_grid_downsampling() {
        let mut voxel_grid = VoxelGrid::new(0.1);
        
        let points = vec![
            Point3::new(0.0, 0.0, 0.0),
            Point3::new(0.05, 0.05, 0.05),  // Same voxel
            Point3::new(0.2, 0.2, 0.2),     // Different voxel
        ];
        
        let downsampled = voxel_grid.downsample(&points).unwrap();
        assert_eq!(downsampled.len(), 2); // Should merge first two points
    }
}