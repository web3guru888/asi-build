/*!
# Vision System Module

Advanced computer vision system for humanoid robots.
Handles face recognition, pose estimation, object detection, and SLAM.
*/

use anyhow::{Context, Result};
use log::{info, warn, error};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};

use crate::{CameraFrame, DetectedHuman, BodyPose, Keypoint, EmotionClassification, Emotion};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VisionConfig {
    pub cameras: Vec<CameraConfig>,
    pub face_recognition: FaceRecognitionConfig,
    pub pose_estimation: PoseEstimationConfig,
    pub object_detection: ObjectDetectionConfig,
    pub slam: SlamConfig,
    pub processing_frequency_hz: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CameraConfig {
    pub camera_id: String,
    pub device_path: String,
    pub resolution: (u32, u32),
    pub fps: f32,
    pub calibration_file: String,
    pub position: CameraPosition,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CameraPosition {
    Head,
    Chest,
    LeftHand,
    RightHand,
    External,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FaceRecognitionConfig {
    pub enabled: bool,
    pub model_path: String,
    pub recognition_threshold: f64,
    pub max_faces: usize,
    pub age_estimation: bool,
    pub gender_estimation: bool,
    pub emotion_recognition: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PoseEstimationConfig {
    pub enabled: bool,
    pub model_path: String,
    pub confidence_threshold: f64,
    pub keypoint_count: usize,
    pub tracking_enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObjectDetectionConfig {
    pub enabled: bool,
    pub model_path: String,
    pub confidence_threshold: f64,
    pub nms_threshold: f64,
    pub max_objects: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SlamConfig {
    pub enabled: bool,
    pub map_resolution: f64,
    pub max_range: f64,
    pub loop_closure_threshold: f64,
}

#[derive(Debug, Clone)]
pub struct VisionResults {
    pub detected_humans: Vec<DetectedHuman>,
    pub detected_objects: Vec<DetectedObject>,
    pub facial_landmarks: Vec<FacialLandmarks>,
    pub scene_map: Option<SceneMap>,
    pub processing_time_ms: f64,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub struct DetectedObject {
    pub object_id: String,
    pub class_name: String,
    pub confidence: f64,
    pub bounding_box: BoundingBox,
    pub position_3d: Option<[f64; 3]>,
    pub properties: HashMap<String, String>,
}

#[derive(Debug, Clone)]
pub struct BoundingBox {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
}

#[derive(Debug, Clone)]
pub struct FacialLandmarks {
    pub person_id: String,
    pub landmarks: Vec<[f64; 2]>,
    pub confidence: f64,
    pub face_quality: f64,
}

#[derive(Debug, Clone)]
pub struct SceneMap {
    pub map_points: Vec<MapPoint>,
    pub camera_poses: Vec<CameraPose>,
    pub confidence: f64,
    pub scale: f64,
}

#[derive(Debug, Clone)]
pub struct MapPoint {
    pub position: [f64; 3],
    pub color: [u8; 3],
    pub observations: usize,
    pub confidence: f64,
}

#[derive(Debug, Clone)]
pub struct CameraPose {
    pub position: [f64; 3],
    pub orientation: [f64; 4], // quaternion
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

pub struct VisionSystem {
    config: VisionConfig,
    cameras: HashMap<String, Camera>,
    face_recognizer: Arc<FaceRecognizer>,
    pose_estimator: Arc<PoseEstimator>,
    object_detector: Arc<ObjectDetector>,
    slam_system: Option<Arc<SlamSystem>>,
    processing_stats: Arc<RwLock<ProcessingStats>>,
}

#[derive(Debug, Default)]
struct ProcessingStats {
    frames_processed: u64,
    total_processing_time_ms: f64,
    average_fps: f64,
    last_update: Option<chrono::DateTime<chrono::Utc>>,
}

struct Camera {
    id: String,
    device: Box<dyn CameraDevice>,
    calibration: CameraCalibration,
}

trait CameraDevice: Send + Sync {
    fn capture_frame(&mut self) -> Result<CameraFrame>;
    fn set_parameter(&mut self, param: &str, value: f64) -> Result<()>;
    fn get_info(&self) -> CameraInfo;
}

#[derive(Debug, Clone)]
struct CameraInfo {
    pub resolution: (u32, u32),
    pub fps: f32,
    pub format: String,
}

#[derive(Debug, Clone)]
struct CameraCalibration {
    pub intrinsic_matrix: [[f64; 3]; 3],
    pub distortion_coefficients: Vec<f64>,
    pub extrinsic_matrix: [[f64; 4]; 4],
}

struct FaceRecognizer {
    config: FaceRecognitionConfig,
    face_database: Arc<RwLock<FaceDatabase>>,
    emotion_classifier: EmotionClassifier,
}

#[derive(Debug)]
struct FaceDatabase {
    known_faces: HashMap<String, FaceEmbedding>,
    face_counter: u64,
}

#[derive(Debug, Clone)]
struct FaceEmbedding {
    embedding: Vec<f32>,
    metadata: FaceMetadata,
}

#[derive(Debug, Clone)]
struct FaceMetadata {
    person_id: String,
    name: Option<String>,
    age_estimate: Option<u32>,
    gender_estimate: Option<String>,
    first_seen: chrono::DateTime<chrono::Utc>,
    last_seen: chrono::DateTime<chrono::Utc>,
    confidence: f64,
}

struct EmotionClassifier {
    model: Box<dyn EmotionModel>,
}

trait EmotionModel: Send + Sync {
    fn classify_emotion(&self, face_image: &[u8], width: u32, height: u32) -> Result<EmotionClassification>;
}

struct PoseEstimator {
    config: PoseEstimationConfig,
    pose_tracker: Option<PoseTracker>,
}

struct PoseTracker {
    tracked_poses: HashMap<String, TrackedPose>,
    next_track_id: u64,
}

#[derive(Debug, Clone)]
struct TrackedPose {
    track_id: String,
    pose_history: Vec<(BodyPose, chrono::DateTime<chrono::Utc>)>,
    confidence: f64,
    last_seen: chrono::DateTime<chrono::Utc>,
}

struct ObjectDetector {
    config: ObjectDetectionConfig,
    object_tracker: Option<ObjectTracker>,
}

struct ObjectTracker {
    tracked_objects: HashMap<String, TrackedObject>,
    next_object_id: u64,
}

#[derive(Debug, Clone)]
struct TrackedObject {
    object_id: String,
    class_name: String,
    position_history: Vec<([f64; 3], chrono::DateTime<chrono::Utc>)>,
    confidence: f64,
    last_seen: chrono::DateTime<chrono::Utc>,
}

struct SlamSystem {
    config: SlamConfig,
    map: Arc<RwLock<SceneMap>>,
    keyframes: Vec<Keyframe>,
}

#[derive(Debug, Clone)]
struct Keyframe {
    id: u64,
    pose: CameraPose,
    features: Vec<Feature>,
    image_data: Vec<u8>,
}

#[derive(Debug, Clone)]
struct Feature {
    position_2d: [f64; 2],
    position_3d: Option<[f64; 3]>,
    descriptor: Vec<f32>,
    confidence: f64,
}

impl VisionSystem {
    pub async fn new(config: &VisionConfig) -> Result<Self> {
        info!("Initializing vision system with {} cameras", config.cameras.len());
        
        // Initialize cameras
        let mut cameras = HashMap::new();
        for camera_config in &config.cameras {
            let camera = Camera::new(camera_config).await?;
            cameras.insert(camera_config.camera_id.clone(), camera);
        }
        
        // Initialize face recognizer
        let face_recognizer = Arc::new(FaceRecognizer::new(&config.face_recognition).await?);
        
        // Initialize pose estimator
        let pose_estimator = Arc::new(PoseEstimator::new(&config.pose_estimation).await?);
        
        // Initialize object detector
        let object_detector = Arc::new(ObjectDetector::new(&config.object_detection).await?);
        
        // Initialize SLAM system if enabled
        let slam_system = if config.slam.enabled {
            Some(Arc::new(SlamSystem::new(&config.slam).await?))
        } else {
            None
        };
        
        Ok(Self {
            config: config.clone(),
            cameras,
            face_recognizer,
            pose_estimator,
            object_detector,
            slam_system,
            processing_stats: Arc::new(RwLock::new(ProcessingStats::default())),
        })
    }
    
    pub async fn start(&self) -> Result<()> {
        info!("Starting vision system");
        
        // Initialize camera devices
        for camera in self.cameras.values() {
            camera.device.get_info();
        }
        
        Ok(())
    }
    
    pub async fn stop(&self) -> Result<()> {
        info!("Stopping vision system");
        Ok(())
    }
    
    pub async fn capture_frames(&self) -> Result<Vec<CameraFrame>> {
        let mut frames = Vec::new();
        
        for camera in self.cameras.values() {
            match camera.capture_frame() {
                Ok(frame) => frames.push(frame),
                Err(e) => warn!("Failed to capture frame from camera {}: {}", camera.id, e),
            }
        }
        
        Ok(frames)
    }
    
    pub async fn process_frames(&self, frames: &[CameraFrame]) -> Result<VisionResults> {
        let start_time = std::time::Instant::now();
        
        if frames.is_empty() {
            return Ok(VisionResults {
                detected_humans: Vec::new(),
                detected_objects: Vec::new(),
                facial_landmarks: Vec::new(),
                scene_map: None,
                processing_time_ms: 0.0,
                timestamp: chrono::Utc::now(),
            });
        }
        
        // Process all frames in parallel
        let (humans, objects, landmarks, map_update) = tokio::try_join!(
            self.detect_humans(frames),
            self.detect_objects(frames),
            self.extract_facial_landmarks(frames),
            self.update_slam(frames),
        )?;
        
        let processing_time = start_time.elapsed().as_millis() as f64;
        
        // Update processing statistics
        {
            let mut stats = self.processing_stats.write().await;
            stats.frames_processed += frames.len() as u64;
            stats.total_processing_time_ms += processing_time;
            stats.last_update = Some(chrono::Utc::now());
            
            if stats.frames_processed > 0 {
                stats.average_fps = 1000.0 * stats.frames_processed as f64 / stats.total_processing_time_ms;
            }
        }
        
        Ok(VisionResults {
            detected_humans: humans,
            detected_objects: objects,
            facial_landmarks: landmarks,
            scene_map: map_update,
            processing_time_ms: processing_time,
            timestamp: chrono::Utc::now(),
        })
    }
    
    async fn detect_humans(&self, frames: &[CameraFrame]) -> Result<Vec<DetectedHuman>> {
        let mut all_humans = Vec::new();
        
        for frame in frames {
            // Face detection and recognition
            let faces = self.face_recognizer.detect_faces(frame).await?;
            
            // Pose estimation
            let poses = self.pose_estimator.estimate_poses(frame).await?;
            
            // Combine face and pose information
            let humans = self.combine_face_and_pose(faces, poses)?;
            all_humans.extend(humans);
        }
        
        // Remove duplicates and track across frames
        Ok(self.deduplicate_humans(all_humans))
    }
    
    async fn detect_objects(&self, frames: &[CameraFrame]) -> Result<Vec<DetectedObject>> {
        let mut all_objects = Vec::new();
        
        for frame in frames {
            let objects = self.object_detector.detect_objects(frame).await?;
            all_objects.extend(objects);
        }
        
        Ok(all_objects)
    }
    
    async fn extract_facial_landmarks(&self, frames: &[CameraFrame]) -> Result<Vec<FacialLandmarks>> {
        let mut all_landmarks = Vec::new();
        
        for frame in frames {
            let landmarks = self.face_recognizer.extract_landmarks(frame).await?;
            all_landmarks.extend(landmarks);
        }
        
        Ok(all_landmarks)
    }
    
    async fn update_slam(&self, frames: &[CameraFrame]) -> Result<Option<SceneMap>> {
        if let Some(ref slam) = self.slam_system {
            slam.process_frames(frames).await
        } else {
            Ok(None)
        }
    }
    
    fn combine_face_and_pose(&self, faces: Vec<FaceDetection>, poses: Vec<PoseDetection>) -> Result<Vec<DetectedHuman>> {
        let mut humans = Vec::new();
        
        // Simple nearest neighbor matching between faces and poses
        for face in faces {
            let mut best_pose = None;
            let mut best_distance = f64::INFINITY;
            
            for pose in &poses {
                if let Some(head_keypoint) = pose.keypoints.iter().find(|k| k.joint_name == "head") {
                    let face_center_x = face.bounding_box.x + face.bounding_box.width / 2.0;
                    let face_center_y = face.bounding_box.y + face.bounding_box.height / 2.0;
                    
                    let distance = ((head_keypoint.position[0] - face_center_x).powi(2) + 
                                   (head_keypoint.position[1] - face_center_y).powi(2)).sqrt();
                    
                    if distance < best_distance && distance < 50.0 { // 50 pixel threshold
                        best_distance = distance;
                        best_pose = Some(pose.clone());
                    }
                }
            }
            
            let human = DetectedHuman {
                person_id: face.person_id.clone(),
                face_landmarks: face.landmarks,
                body_pose: best_pose.map(|p| BodyPose {
                    keypoints: p.keypoints,
                    confidence: p.confidence,
                    timestamp: chrono::Utc::now(),
                }).unwrap_or_else(|| BodyPose {
                    keypoints: Vec::new(),
                    confidence: 0.0,
                    timestamp: chrono::Utc::now(),
                }),
                estimated_age: face.age_estimate,
                estimated_gender: face.gender_estimate,
                emotion: face.emotion,
                distance: face.distance,
                engagement_level: self.calculate_engagement_level(&face),
            };
            
            humans.push(human);
        }
        
        Ok(humans)
    }
    
    fn deduplicate_humans(&self, humans: Vec<DetectedHuman>) -> Vec<DetectedHuman> {
        // Simple deduplication based on face similarity
        // In a real implementation, this would use more sophisticated tracking
        let mut unique_humans = Vec::new();
        
        for human in humans {
            let mut is_duplicate = false;
            
            for existing in &unique_humans {
                if self.are_same_person(&human, existing) {
                    is_duplicate = true;
                    break;
                }
            }
            
            if !is_duplicate {
                unique_humans.push(human);
            }
        }
        
        unique_humans
    }
    
    fn are_same_person(&self, human1: &DetectedHuman, human2: &DetectedHuman) -> bool {
        // Simple check based on person ID
        human1.person_id == human2.person_id
    }
    
    fn calculate_engagement_level(&self, face: &FaceDetection) -> f64 {
        // Calculate engagement based on:
        // - Eye contact (looking at camera)
        // - Facial expression
        // - Distance from camera
        // - Duration of interaction
        
        let mut engagement = 0.5; // Base engagement
        
        // Eye contact bonus
        if face.looking_at_camera {
            engagement += 0.3;
        }
        
        // Emotion bonus
        match face.emotion.primary_emotion {
            Emotion::Happy | Emotion::Excited => engagement += 0.2,
            Emotion::Angry | Emotion::Sad => engagement -= 0.2,
            _ => {}
        }
        
        // Distance penalty (further away = less engaged)
        if face.distance > 3.0 {
            engagement -= 0.1;
        }
        
        engagement.clamp(0.0, 1.0)
    }
    
    pub async fn get_processing_stats(&self) -> ProcessingStats {
        self.processing_stats.read().await.clone()
    }
}

// Helper structures for internal processing
#[derive(Debug, Clone)]
struct FaceDetection {
    person_id: String,
    bounding_box: BoundingBox,
    landmarks: Vec<[f64; 2]>,
    age_estimate: Option<u32>,
    gender_estimate: Option<crate::Gender>,
    emotion: EmotionClassification,
    distance: f64,
    looking_at_camera: bool,
    confidence: f64,
}

#[derive(Debug, Clone)]
struct PoseDetection {
    keypoints: Vec<Keypoint>,
    confidence: f64,
    bounding_box: BoundingBox,
}

impl Camera {
    async fn new(config: &CameraConfig) -> Result<Self> {
        let device = Box::new(SimulatedCamera::new(config)?);
        let calibration = CameraCalibration::load(&config.calibration_file)?;
        
        Ok(Self {
            id: config.camera_id.clone(),
            device,
            calibration,
        })
    }
    
    fn capture_frame(&self) -> Result<CameraFrame> {
        self.device.capture_frame()
    }
}

// Simulated camera for testing
struct SimulatedCamera {
    config: CameraConfig,
    frame_counter: std::sync::atomic::AtomicU64,
}

impl SimulatedCamera {
    fn new(config: &CameraConfig) -> Result<Self> {
        Ok(Self {
            config: config.clone(),
            frame_counter: std::sync::atomic::AtomicU64::new(0),
        })
    }
}

impl CameraDevice for SimulatedCamera {
    fn capture_frame(&mut self) -> Result<CameraFrame> {
        let frame_number = self.frame_counter.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        
        // Generate simulated frame data
        let (width, height) = self.config.resolution;
        let pixel_count = (width * height * 3) as usize; // RGB
        let image_data = vec![128u8; pixel_count]; // Gray image
        
        Ok(CameraFrame {
            camera_id: self.config.camera_id.clone(),
            image_data,
            timestamp: chrono::Utc::now(),
            width,
            height,
            format: crate::ImageFormat::RGB8,
        })
    }
    
    fn set_parameter(&mut self, _param: &str, _value: f64) -> Result<()> {
        Ok(())
    }
    
    fn get_info(&self) -> CameraInfo {
        CameraInfo {
            resolution: self.config.resolution,
            fps: self.config.fps,
            format: "RGB8".to_string(),
        }
    }
}

impl CameraCalibration {
    fn load(_path: &str) -> Result<Self> {
        // Return default calibration for simulation
        Ok(Self {
            intrinsic_matrix: [
                [800.0, 0.0, 320.0],
                [0.0, 800.0, 240.0],
                [0.0, 0.0, 1.0],
            ],
            distortion_coefficients: vec![0.0, 0.0, 0.0, 0.0, 0.0],
            extrinsic_matrix: [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
        })
    }
}

impl FaceRecognizer {
    async fn new(config: &FaceRecognitionConfig) -> Result<Self> {
        let face_database = Arc::new(RwLock::new(FaceDatabase {
            known_faces: HashMap::new(),
            face_counter: 0,
        }));
        
        let emotion_classifier = EmotionClassifier {
            model: Box::new(SimulatedEmotionModel::new()?),
        };
        
        Ok(Self {
            config: config.clone(),
            face_database,
            emotion_classifier,
        })
    }
    
    async fn detect_faces(&self, frame: &CameraFrame) -> Result<Vec<FaceDetection>> {
        // Simulate face detection
        if frame.image_data.is_empty() {
            return Ok(Vec::new());
        }
        
        // Generate simulated face detection
        let face = FaceDetection {
            person_id: "person_1".to_string(),
            bounding_box: BoundingBox {
                x: 100.0,
                y: 100.0,
                width: 200.0,
                height: 200.0,
            },
            landmarks: vec![
                [150.0, 150.0], // Left eye
                [250.0, 150.0], // Right eye
                [200.0, 180.0], // Nose
                [200.0, 220.0], // Mouth
            ],
            age_estimate: Some(30),
            gender_estimate: Some(crate::Gender::Unknown),
            emotion: EmotionClassification {
                primary_emotion: Emotion::Neutral,
                confidence: 0.8,
                all_emotions: vec![
                    (Emotion::Neutral, 0.8),
                    (Emotion::Happy, 0.15),
                    (Emotion::Sad, 0.05),
                ],
            },
            distance: 2.0,
            looking_at_camera: true,
            confidence: 0.9,
        };
        
        Ok(vec![face])
    }
    
    async fn extract_landmarks(&self, _frame: &CameraFrame) -> Result<Vec<FacialLandmarks>> {
        // Simulate landmark extraction
        Ok(vec![FacialLandmarks {
            person_id: "person_1".to_string(),
            landmarks: vec![
                [150.0, 150.0], [250.0, 150.0], [200.0, 180.0], [200.0, 220.0]
            ],
            confidence: 0.9,
            face_quality: 0.85,
        }])
    }
}

// Simulated emotion model
struct SimulatedEmotionModel;

impl SimulatedEmotionModel {
    fn new() -> Result<Self> {
        Ok(Self)
    }
}

impl EmotionModel for SimulatedEmotionModel {
    fn classify_emotion(&self, _face_image: &[u8], _width: u32, _height: u32) -> Result<EmotionClassification> {
        Ok(EmotionClassification {
            primary_emotion: Emotion::Neutral,
            confidence: 0.8,
            all_emotions: vec![
                (Emotion::Neutral, 0.8),
                (Emotion::Happy, 0.15),
                (Emotion::Sad, 0.05),
            ],
        })
    }
}

impl PoseEstimator {
    async fn new(config: &PoseEstimationConfig) -> Result<Self> {
        let pose_tracker = if config.tracking_enabled {
            Some(PoseTracker {
                tracked_poses: HashMap::new(),
                next_track_id: 0,
            })
        } else {
            None
        };
        
        Ok(Self {
            config: config.clone(),
            pose_tracker,
        })
    }
    
    async fn estimate_poses(&self, _frame: &CameraFrame) -> Result<Vec<PoseDetection>> {
        // Simulate pose detection
        let pose = PoseDetection {
            keypoints: vec![
                Keypoint {
                    joint_name: "head".to_string(),
                    position: [200.0, 100.0, 0.0],
                    confidence: 0.9,
                },
                Keypoint {
                    joint_name: "neck".to_string(),
                    position: [200.0, 150.0, 0.0],
                    confidence: 0.85,
                },
                Keypoint {
                    joint_name: "left_shoulder".to_string(),
                    position: [150.0, 180.0, 0.0],
                    confidence: 0.8,
                },
                Keypoint {
                    joint_name: "right_shoulder".to_string(),
                    position: [250.0, 180.0, 0.0],
                    confidence: 0.8,
                },
            ],
            confidence: 0.85,
            bounding_box: BoundingBox {
                x: 100.0,
                y: 50.0,
                width: 200.0,
                height: 400.0,
            },
        };
        
        Ok(vec![pose])
    }
}

impl ObjectDetector {
    async fn new(config: &ObjectDetectionConfig) -> Result<Self> {
        let object_tracker = Some(ObjectTracker {
            tracked_objects: HashMap::new(),
            next_object_id: 0,
        });
        
        Ok(Self {
            config: config.clone(),
            object_tracker,
        })
    }
    
    async fn detect_objects(&self, _frame: &CameraFrame) -> Result<Vec<DetectedObject>> {
        // Simulate object detection
        Ok(vec![
            DetectedObject {
                object_id: "chair_1".to_string(),
                class_name: "chair".to_string(),
                confidence: 0.85,
                bounding_box: BoundingBox {
                    x: 300.0,
                    y: 200.0,
                    width: 100.0,
                    height: 150.0,
                },
                position_3d: Some([1.5, 0.5, 0.0]),
                properties: HashMap::new(),
            }
        ])
    }
}

impl SlamSystem {
    async fn new(config: &SlamConfig) -> Result<Self> {
        let map = Arc::new(RwLock::new(SceneMap {
            map_points: Vec::new(),
            camera_poses: Vec::new(),
            confidence: 0.0,
            scale: 1.0,
        }));
        
        Ok(Self {
            config: config.clone(),
            map,
            keyframes: Vec::new(),
        })
    }
    
    async fn process_frames(&self, _frames: &[CameraFrame]) -> Result<Option<SceneMap>> {
        // Simulate SLAM processing
        let map = self.map.read().await.clone();
        Ok(Some(map))
    }
}

impl Default for VisionConfig {
    fn default() -> Self {
        Self {
            cameras: vec![
                CameraConfig {
                    camera_id: "head_camera".to_string(),
                    device_path: "/dev/video0".to_string(),
                    resolution: (640, 480),
                    fps: 30.0,
                    calibration_file: "config/head_camera_calibration.yaml".to_string(),
                    position: CameraPosition::Head,
                }
            ],
            face_recognition: FaceRecognitionConfig {
                enabled: true,
                model_path: "models/face_recognition.onnx".to_string(),
                recognition_threshold: 0.6,
                max_faces: 10,
                age_estimation: true,
                gender_estimation: true,
                emotion_recognition: true,
            },
            pose_estimation: PoseEstimationConfig {
                enabled: true,
                model_path: "models/pose_estimation.onnx".to_string(),
                confidence_threshold: 0.5,
                keypoint_count: 17,
                tracking_enabled: true,
            },
            object_detection: ObjectDetectionConfig {
                enabled: true,
                model_path: "models/object_detection.onnx".to_string(),
                confidence_threshold: 0.5,
                nms_threshold: 0.4,
                max_objects: 50,
            },
            slam: SlamConfig {
                enabled: false, // Disabled by default due to computational cost
                map_resolution: 0.05,
                max_range: 10.0,
                loop_closure_threshold: 0.7,
            },
            processing_frequency_hz: 30.0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_vision_system_creation() {
        let config = VisionConfig::default();
        let system = VisionSystem::new(&config).await;
        assert!(system.is_ok());
    }
    
    #[tokio::test]
    async fn test_frame_capture() {
        let config = VisionConfig::default();
        let system = VisionSystem::new(&config).await.unwrap();
        
        let frames = system.capture_frames().await.unwrap();
        assert_eq!(frames.len(), 1); // One camera configured
    }
    
    #[test]
    fn test_bounding_box() {
        let bbox = BoundingBox {
            x: 100.0,
            y: 100.0,
            width: 200.0,
            height: 200.0,
        };
        
        assert_eq!(bbox.x, 100.0);
        assert_eq!(bbox.width, 200.0);
    }
}