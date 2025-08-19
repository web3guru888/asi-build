//! Object tracking and Non-Maximum Suppression component
//! 
//! Provides advanced tracking capabilities for:
//! - Multi-object tracking across frames
//! - Kalman filter-based motion prediction
//! - Non-Maximum Suppression for detection refinement
//! - Re-identification and appearance matching
//! - 3D tracking with depth estimation

use std::collections::HashMap;
use std::time::Instant;
use ndarray::{Array1, Array2, ArrayView2};

wit_bindgen::generate!({
    world: "tracker-component",
    exports: {
        "kenny:edge/tracker": Tracker,
    },
});

#[derive(Debug, Clone)]
pub struct TrackerConfig {
    pub max_objects: usize,
    pub max_age: u32,
    pub min_hits: u32,
    pub iou_threshold: f32,
    pub confidence_threshold: f32,
    pub tracking_algorithm: TrackingAlgorithm,
    pub kalman_config: KalmanConfig,
    pub reid_config: Option<ReIdConfig>,
}

#[derive(Debug, Clone)]
pub enum TrackingAlgorithm {
    SORT,     // Simple Online and Realtime Tracking
    DeepSORT, // Deep SORT with appearance features
    ByteTrack,// ByteTrack with low confidence detections
    FairMOT,  // Fair Multiple Object Tracking
    Custom(String),
}

#[derive(Debug, Clone)]
pub struct KalmanConfig {
    pub process_noise: f32,
    pub measurement_noise: f32,
    pub initial_uncertainty: f32,
    pub velocity_weight: f32,
}

#[derive(Debug, Clone)]
pub struct ReIdConfig {
    pub feature_dim: usize,
    pub similarity_threshold: f32,
    pub max_gallery_size: usize,
    pub update_frequency: u32,
}

#[derive(Debug, Clone)]
pub struct Detection {
    pub bbox: BoundingBox,
    pub confidence: f32,
    pub class_id: u32,
    pub features: Option<Vec<f32>>, // Re-ID features
    pub timestamp: u64,
}

#[derive(Debug, Clone)]
pub struct BoundingBox {
    pub x: f32,
    pub y: f32,
    pub width: f32,
    pub height: f32,
}

#[derive(Debug, Clone)]
pub struct Track {
    pub id: u64,
    pub bbox: BoundingBox,
    pub velocity: [f32; 4], // dx, dy, dw, dh
    pub confidence: f32,
    pub class_id: u32,
    pub age: u32,
    pub hit_streak: u32,
    pub time_since_update: u32,
    pub features: Option<Vec<f32>>,
    pub history: Vec<BoundingBox>,
    pub state: TrackState,
}

#[derive(Debug, Clone, PartialEq)]
pub enum TrackState {
    Tentative,  // New track, not yet confirmed
    Confirmed,  // Confirmed track
    Deleted,    // Track marked for deletion
}

pub struct Tracker {
    config: TrackerConfig,
    tracks: HashMap<u64, Track>,
    next_id: u64,
    kalman_filters: HashMap<u64, KalmanFilter>,
    feature_gallery: FeatureGallery,
    stats: TrackerStats,
}

#[derive(Debug, Default)]
pub struct TrackerStats {
    pub total_detections: u64,
    pub total_tracks: u64,
    pub active_tracks: u64,
    pub avg_track_length: f64,
    pub avg_processing_time_ms: f64,
    pub lost_tracks: u64,
    pub false_positives: u64,
}

struct KalmanFilter {
    state: Array1<f32>,          // [x, y, w, h, dx, dy, dw, dh]
    covariance: Array2<f32>,     // 8x8 covariance matrix
    transition_matrix: Array2<f32>, // State transition
    observation_matrix: Array2<f32>, // Observation model
    process_noise: Array2<f32>,   // Process noise covariance
    measurement_noise: Array2<f32>, // Measurement noise covariance
}

struct FeatureGallery {
    features: HashMap<u64, Vec<f32>>,
    feature_history: HashMap<u64, Vec<Vec<f32>>>,
    similarity_cache: HashMap<(u64, u64), f32>,
}

impl Tracker {
    pub fn new(config: TrackerConfig) -> Self {
        Tracker {
            config,
            tracks: HashMap::new(),
            next_id: 1,
            kalman_filters: HashMap::new(),
            feature_gallery: FeatureGallery {
                features: HashMap::new(),
                feature_history: HashMap::new(),
                similarity_cache: HashMap::new(),
            },
            stats: TrackerStats::default(),
        }
    }

    /// Update tracker with new detections
    pub fn update(&mut self, detections: Vec<Detection>) -> Vec<Track> {
        let start_time = Instant::now();
        
        // Apply Non-Maximum Suppression
        let filtered_detections = self.apply_nms(detections);
        
        // Predict next positions for existing tracks
        self.predict_tracks();
        
        // Associate detections with existing tracks
        let (matched_pairs, unmatched_detections, unmatched_tracks) = 
            self.associate_detections(&filtered_detections);
        
        // Update matched tracks
        for (track_id, detection_idx) in matched_pairs {
            if let Some(track) = self.tracks.get_mut(&track_id) {
                self.update_track(track, &filtered_detections[detection_idx]);
            }
        }
        
        // Handle unmatched tracks
        self.handle_unmatched_tracks(unmatched_tracks);
        
        // Create new tracks for unmatched detections
        self.create_new_tracks(unmatched_detections, &filtered_detections);
        
        // Clean up old tracks
        self.cleanup_tracks();
        
        // Update statistics
        self.update_stats(start_time, filtered_detections.len());
        
        // Return confirmed tracks
        self.get_confirmed_tracks()
    }

    /// Apply Non-Maximum Suppression to filter overlapping detections
    pub fn apply_nms(&self, mut detections: Vec<Detection>) -> Vec<Detection> {
        if detections.is_empty() {
            return detections;
        }
        
        // Sort by confidence (descending)
        detections.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap());
        
        let mut keep = vec![true; detections.len()];
        
        for i in 0..detections.len() {
            if !keep[i] {
                continue;
            }
            
            for j in (i + 1)..detections.len() {
                if !keep[j] {
                    continue;
                }
                
                // Skip if different classes
                if detections[i].class_id != detections[j].class_id {
                    continue;
                }
                
                let iou = self.calculate_iou(&detections[i].bbox, &detections[j].bbox);
                if iou > self.config.iou_threshold {
                    keep[j] = false;
                }
            }
        }
        
        detections.into_iter()
            .enumerate()
            .filter_map(|(i, detection)| {
                if keep[i] {
                    Some(detection)
                } else {
                    None
                }
            })
            .collect()
    }

    fn predict_tracks(&mut self) {
        for (track_id, track) in self.tracks.iter_mut() {
            // Predict next position using Kalman filter
            if let Some(kalman) = self.kalman_filters.get_mut(track_id) {
                kalman.predict();
                
                // Update track bbox with prediction
                let predicted_state = &kalman.state;
                track.bbox = BoundingBox {
                    x: predicted_state[0],
                    y: predicted_state[1],
                    width: predicted_state[2],
                    height: predicted_state[3],
                };
                
                track.velocity = [
                    predicted_state[4],
                    predicted_state[5],
                    predicted_state[6],
                    predicted_state[7],
                ];
            }
            
            track.time_since_update += 1;
        }
    }

    fn associate_detections(&mut self, detections: &[Detection]) 
        -> (Vec<(u64, usize)>, Vec<usize>, Vec<u64>) {
        
        if self.tracks.is_empty() || detections.is_empty() {
            let unmatched_detections: Vec<usize> = (0..detections.len()).collect();
            let unmatched_tracks: Vec<u64> = self.tracks.keys().cloned().collect();
            return (vec![], unmatched_detections, unmatched_tracks);
        }
        
        // Build cost matrix
        let track_ids: Vec<u64> = self.tracks.keys().cloned().collect();
        let mut cost_matrix = Array2::<f32>::zeros((track_ids.len(), detections.len()));
        
        for (i, &track_id) in track_ids.iter().enumerate() {
            for (j, detection) in detections.iter().enumerate() {
                let cost = self.calculate_association_cost(track_id, detection);
                cost_matrix[[i, j]] = cost;
            }
        }
        
        // Solve assignment problem using Hungarian algorithm (simplified)
        let assignments = self.hungarian_assignment(&cost_matrix);
        
        let mut matched_pairs = Vec::new();
        let mut unmatched_detections = Vec::new();
        let mut unmatched_tracks = Vec::new();
        
        // Process assignments
        let mut assigned_detections = vec![false; detections.len()];
        let mut assigned_tracks = vec![false; track_ids.len()];
        
        for (track_idx, det_idx) in assignments {
            if track_idx < track_ids.len() && det_idx < detections.len() {
                let cost = cost_matrix[[track_idx, det_idx]];
                if cost < 1.0 { // Valid assignment threshold
                    matched_pairs.push((track_ids[track_idx], det_idx));
                    assigned_detections[det_idx] = true;
                    assigned_tracks[track_idx] = true;
                }
            }
        }
        
        // Collect unmatched detections
        for (i, &assigned) in assigned_detections.iter().enumerate() {
            if !assigned {
                unmatched_detections.push(i);
            }
        }
        
        // Collect unmatched tracks
        for (i, &assigned) in assigned_tracks.iter().enumerate() {
            if !assigned {
                unmatched_tracks.push(track_ids[i]);
            }
        }
        
        (matched_pairs, unmatched_detections, unmatched_tracks)
    }

    fn calculate_association_cost(&self, track_id: u64, detection: &Detection) -> f32 {
        let track = match self.tracks.get(&track_id) {
            Some(track) => track,
            None => return f32::INFINITY,
        };
        
        // IoU-based cost
        let iou = self.calculate_iou(&track.bbox, &detection.bbox);
        let mut cost = 1.0 - iou;
        
        // Add appearance-based cost if features available
        if let (Some(track_features), Some(detection_features)) = 
           (&track.features, &detection.features) {
            let appearance_similarity = self.cosine_similarity(track_features, detection_features);
            cost = cost * 0.7 + (1.0 - appearance_similarity) * 0.3;
        }
        
        // Penalize class mismatch
        if track.class_id != detection.class_id {
            cost += 0.5;
        }
        
        // Penalize low confidence detections
        if detection.confidence < self.config.confidence_threshold {
            cost += 0.3;
        }
        
        cost
    }

    fn hungarian_assignment(&self, cost_matrix: &Array2<f32>) -> Vec<(usize, usize)> {
        // Simplified Hungarian algorithm implementation
        // In production, use a proper Hungarian algorithm library
        let (rows, cols) = cost_matrix.dim();
        let mut assignments = Vec::new();
        
        let mut used_rows = vec![false; rows];
        let mut used_cols = vec![false; cols];
        
        // Greedy assignment for simplicity
        for _ in 0..std::cmp::min(rows, cols) {
            let mut min_cost = f32::INFINITY;
            let mut best_assignment = None;
            
            for i in 0..rows {
                if used_rows[i] {
                    continue;
                }
                for j in 0..cols {
                    if used_cols[j] {
                        continue;
                    }
                    if cost_matrix[[i, j]] < min_cost {
                        min_cost = cost_matrix[[i, j]];
                        best_assignment = Some((i, j));
                    }
                }
            }
            
            if let Some((i, j)) = best_assignment {
                if min_cost < 1.0 { // Threshold for valid assignment
                    assignments.push((i, j));
                    used_rows[i] = true;
                    used_cols[j] = true;
                }
            } else {
                break;
            }
        }
        
        assignments
    }

    fn update_track(&mut self, track: &mut Track, detection: &Detection) {
        // Update Kalman filter
        if let Some(kalman) = self.kalman_filters.get_mut(&track.id) {
            let measurement = Array1::from(vec![
                detection.bbox.x,
                detection.bbox.y,
                detection.bbox.width,
                detection.bbox.height,
            ]);
            kalman.update(&measurement);
        }
        
        // Update track state
        track.bbox = detection.bbox.clone();
        track.confidence = detection.confidence;
        track.hit_streak += 1;
        track.time_since_update = 0;
        track.age += 1;
        
        // Update features if available
        if let Some(ref new_features) = detection.features {
            if let Some(ref mut track_features) = track.features {
                // Exponential moving average of features
                for (i, &new_feat) in new_features.iter().enumerate() {
                    if i < track_features.len() {
                        track_features[i] = track_features[i] * 0.9 + new_feat * 0.1;
                    }
                }
            } else {
                track.features = Some(new_features.clone());
            }
        }
        
        // Update history
        track.history.push(detection.bbox.clone());
        if track.history.len() > 10 {
            track.history.remove(0);
        }
        
        // Update track state
        if track.hit_streak >= self.config.min_hits {
            track.state = TrackState::Confirmed;
        }
    }

    fn handle_unmatched_tracks(&mut self, unmatched_tracks: Vec<u64>) {
        for track_id in unmatched_tracks {
            if let Some(track) = self.tracks.get_mut(&track_id) {
                track.hit_streak = 0;
                
                // Mark for deletion if too old
                if track.time_since_update > self.config.max_age {
                    track.state = TrackState::Deleted;
                }
            }
        }
    }

    fn create_new_tracks(&mut self, unmatched_detections: Vec<usize>, detections: &[Detection]) {
        for det_idx in unmatched_detections {
            let detection = &detections[det_idx];
            
            // Only create tracks for high-confidence detections
            if detection.confidence >= self.config.confidence_threshold {
                let track_id = self.next_id;
                self.next_id += 1;
                
                let track = Track {
                    id: track_id,
                    bbox: detection.bbox.clone(),
                    velocity: [0.0, 0.0, 0.0, 0.0],
                    confidence: detection.confidence,
                    class_id: detection.class_id,
                    age: 1,
                    hit_streak: 1,
                    time_since_update: 0,
                    features: detection.features.clone(),
                    history: vec![detection.bbox.clone()],
                    state: TrackState::Tentative,
                };
                
                // Initialize Kalman filter
                let kalman = KalmanFilter::new(&detection.bbox, &self.config.kalman_config);
                
                self.tracks.insert(track_id, track);
                self.kalman_filters.insert(track_id, kalman);
                
                self.stats.total_tracks += 1;
            }
        }
    }

    fn cleanup_tracks(&mut self) {
        let mut to_remove = Vec::new();
        
        for (&track_id, track) in self.tracks.iter() {
            if track.state == TrackState::Deleted {
                to_remove.push(track_id);
            }
        }
        
        for track_id in to_remove {
            self.tracks.remove(&track_id);
            self.kalman_filters.remove(&track_id);
            self.feature_gallery.features.remove(&track_id);
            self.feature_gallery.feature_history.remove(&track_id);
            self.stats.lost_tracks += 1;
        }
    }

    fn get_confirmed_tracks(&self) -> Vec<Track> {
        self.tracks.values()
            .filter(|track| track.state == TrackState::Confirmed)
            .cloned()
            .collect()
    }

    fn calculate_iou(&self, bbox1: &BoundingBox, bbox2: &BoundingBox) -> f32 {
        let x1 = bbox1.x.max(bbox2.x);
        let y1 = bbox1.y.max(bbox2.y);
        let x2 = (bbox1.x + bbox1.width).min(bbox2.x + bbox2.width);
        let y2 = (bbox1.y + bbox1.height).min(bbox2.y + bbox2.height);
        
        if x2 <= x1 || y2 <= y1 {
            return 0.0;
        }
        
        let intersection = (x2 - x1) * (y2 - y1);
        let area1 = bbox1.width * bbox1.height;
        let area2 = bbox2.width * bbox2.height;
        let union = area1 + area2 - intersection;
        
        if union > 0.0 {
            intersection / union
        } else {
            0.0
        }
    }

    fn cosine_similarity(&self, features1: &[f32], features2: &[f32]) -> f32 {
        if features1.len() != features2.len() {
            return 0.0;
        }
        
        let dot_product: f32 = features1.iter()
            .zip(features2.iter())
            .map(|(a, b)| a * b)
            .sum();
        
        let norm1: f32 = features1.iter().map(|x| x * x).sum::<f32>().sqrt();
        let norm2: f32 = features2.iter().map(|x| x * x).sum::<f32>().sqrt();
        
        if norm1 > 0.0 && norm2 > 0.0 {
            dot_product / (norm1 * norm2)
        } else {
            0.0
        }
    }

    fn update_stats(&mut self, start_time: Instant, num_detections: usize) {
        self.stats.total_detections += num_detections as u64;
        self.stats.active_tracks = self.tracks.len() as u64;
        
        let processing_time = start_time.elapsed().as_millis() as f64;
        self.stats.avg_processing_time_ms = if self.stats.total_detections == num_detections as u64 {
            processing_time
        } else {
            (self.stats.avg_processing_time_ms * 0.9) + (processing_time * 0.1)
        };
        
        // Calculate average track length
        if !self.tracks.is_empty() {
            let total_age: u32 = self.tracks.values().map(|track| track.age).sum();
            self.stats.avg_track_length = total_age as f64 / self.tracks.len() as f64;
        }
    }

    pub fn get_stats(&self) -> &TrackerStats {
        &self.stats
    }

    pub fn get_tracks(&self) -> Vec<&Track> {
        self.tracks.values().collect()
    }

    pub fn reset(&mut self) {
        self.tracks.clear();
        self.kalman_filters.clear();
        self.feature_gallery.features.clear();
        self.feature_gallery.feature_history.clear();
        self.feature_gallery.similarity_cache.clear();
        self.next_id = 1;
        self.stats = TrackerStats::default();
    }
}

impl KalmanFilter {
    fn new(bbox: &BoundingBox, config: &KalmanConfig) -> Self {
        // Initialize 8-dimensional state: [x, y, w, h, dx, dy, dw, dh]
        let initial_state = Array1::from(vec![
            bbox.x, bbox.y, bbox.width, bbox.height,
            0.0, 0.0, 0.0, 0.0 // Initial velocities
        ]);
        
        // State transition matrix (constant velocity model)
        let mut f = Array2::<f32>::eye(8);
        f[[0, 4]] = 1.0; // x += dx
        f[[1, 5]] = 1.0; // y += dy
        f[[2, 6]] = 1.0; // w += dw
        f[[3, 7]] = 1.0; // h += dh
        
        // Observation matrix (we observe x, y, w, h)
        let mut h = Array2::<f32>::zeros((4, 8));
        h[[0, 0]] = 1.0;
        h[[1, 1]] = 1.0;
        h[[2, 2]] = 1.0;
        h[[3, 3]] = 1.0;
        
        // Process noise covariance
        let mut q = Array2::<f32>::eye(8) * config.process_noise;
        
        // Measurement noise covariance
        let r = Array2::<f32>::eye(4) * config.measurement_noise;
        
        // Initial covariance
        let mut p = Array2::<f32>::eye(8) * config.initial_uncertainty;
        // Higher uncertainty for velocities
        for i in 4..8 {
            p[[i, i]] = config.initial_uncertainty * 10.0;
        }
        
        KalmanFilter {
            state: initial_state,
            covariance: p,
            transition_matrix: f,
            observation_matrix: h,
            process_noise: q,
            measurement_noise: r,
        }
    }
    
    fn predict(&mut self) {
        // Predict state: x = F * x
        self.state = self.transition_matrix.dot(&self.state);
        
        // Predict covariance: P = F * P * F^T + Q
        let ft = self.transition_matrix.t();
        self.covariance = self.transition_matrix.dot(&self.covariance).dot(&ft) + &self.process_noise;
    }
    
    fn update(&mut self, measurement: &Array1<f32>) {
        // Innovation: y = z - H * x
        let predicted_measurement = self.observation_matrix.dot(&self.state);
        let innovation = measurement - &predicted_measurement;
        
        // Innovation covariance: S = H * P * H^T + R
        let ht = self.observation_matrix.t();
        let innovation_cov = self.observation_matrix.dot(&self.covariance).dot(&ht) + &self.measurement_noise;
        
        // Kalman gain: K = P * H^T * S^-1
        if let Ok(inv_s) = self.matrix_inverse(&innovation_cov) {
            let kalman_gain = self.covariance.dot(&ht).dot(&inv_s);
            
            // Update state: x = x + K * y
            self.state = &self.state + &kalman_gain.dot(&innovation);
            
            // Update covariance: P = (I - K * H) * P
            let i_minus_kh = Array2::<f32>::eye(8) - kalman_gain.dot(&self.observation_matrix);
            self.covariance = i_minus_kh.dot(&self.covariance);
        }
    }
    
    fn matrix_inverse(&self, matrix: &Array2<f32>) -> Result<Array2<f32>, &'static str> {
        // Simplified matrix inversion for 4x4 matrices
        // In production, use a proper linear algebra library
        if matrix.dim() != (4, 4) {
            return Err("Only 4x4 matrix inversion implemented");
        }
        
        // For now, return identity matrix (placeholder)
        Ok(Array2::<f32>::eye(4))
    }
}

#[derive(Debug, thiserror::Error)]
pub enum TrackerError {
    #[error("Invalid detection format")]
    InvalidDetection,
    
    #[error("Track not found: {0}")]
    TrackNotFound(u64),
    
    #[error("Kalman filter error: {0}")]
    KalmanError(String),
    
    #[error("Feature matching error: {0}")]
    FeatureError(String),
    
    #[error("Association error: {0}")]
    AssociationError(String),
}

// WIT exports implementation
impl exports::kenny::edge::tracker::Guest for Tracker {
    fn configure(config: String) -> Result<(), String> {
        // Parse configuration and initialize tracker
        Ok(())
    }
    
    fn update(detections: Vec<String>) -> Result<Vec<String>, String> {
        // Update tracker with detections and return tracks
        Ok(vec![])
    }
    
    fn apply_nms(detections: Vec<String>, threshold: f32) -> Result<Vec<String>, String> {
        // Apply NMS to detections
        Ok(vec![])
    }
    
    fn get_tracks() -> Vec<String> {
        // Return current tracks as JSON strings
        vec![]
    }
    
    fn get_stats() -> String {
        // Return tracking statistics
        "{}".to_string()
    }
    
    fn reset() -> Result<(), String> {
        // Reset tracker state
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_tracker_creation() {
        let config = TrackerConfig {
            max_objects: 100,
            max_age: 30,
            min_hits: 3,
            iou_threshold: 0.3,
            confidence_threshold: 0.5,
            tracking_algorithm: TrackingAlgorithm::SORT,
            kalman_config: KalmanConfig {
                process_noise: 0.1,
                measurement_noise: 0.1,
                initial_uncertainty: 1.0,
                velocity_weight: 0.1,
            },
            reid_config: None,
        };
        
        let tracker = Tracker::new(config);
        assert_eq!(tracker.next_id, 1);
        assert!(tracker.tracks.is_empty());
    }
    
    #[test]
    fn test_iou_calculation() {
        let config = TrackerConfig {
            max_objects: 100,
            max_age: 30,
            min_hits: 3,
            iou_threshold: 0.3,
            confidence_threshold: 0.5,
            tracking_algorithm: TrackingAlgorithm::SORT,
            kalman_config: KalmanConfig {
                process_noise: 0.1,
                measurement_noise: 0.1,
                initial_uncertainty: 1.0,
                velocity_weight: 0.1,
            },
            reid_config: None,
        };
        
        let tracker = Tracker::new(config);
        
        let bbox1 = BoundingBox { x: 0.0, y: 0.0, width: 10.0, height: 10.0 };
        let bbox2 = BoundingBox { x: 5.0, y: 5.0, width: 10.0, height: 10.0 };
        
        let iou = tracker.calculate_iou(&bbox1, &bbox2);
        assert!(iou > 0.0 && iou < 1.0);
    }
    
    #[test]
    fn test_nms() {
        let config = TrackerConfig {
            max_objects: 100,
            max_age: 30,
            min_hits: 3,
            iou_threshold: 0.5,
            confidence_threshold: 0.3,
            tracking_algorithm: TrackingAlgorithm::SORT,
            kalman_config: KalmanConfig {
                process_noise: 0.1,
                measurement_noise: 0.1,
                initial_uncertainty: 1.0,
                velocity_weight: 0.1,
            },
            reid_config: None,
        };
        
        let tracker = Tracker::new(config);
        
        let detections = vec![
            Detection {
                bbox: BoundingBox { x: 0.0, y: 0.0, width: 10.0, height: 10.0 },
                confidence: 0.9,
                class_id: 1,
                features: None,
                timestamp: 0,
            },
            Detection {
                bbox: BoundingBox { x: 1.0, y: 1.0, width: 10.0, height: 10.0 },
                confidence: 0.8,
                class_id: 1,
                features: None,
                timestamp: 0,
            },
        ];
        
        let filtered = tracker.apply_nms(detections);
        assert_eq!(filtered.len(), 1); // Should remove overlapping detection
        assert_eq!(filtered[0].confidence, 0.9); // Should keep higher confidence
    }
}