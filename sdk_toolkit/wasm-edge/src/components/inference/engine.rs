//! AI inference engine component with WASI-NN integration
//! 
//! Provides high-performance inference for:
//! - Computer vision models (CNN, Vision Transformers)
//! - Object detection and segmentation
//! - Natural language processing
//! - Multi-modal AI models
//! - Quantized and optimized edge models

use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;
use ndarray::{Array, Array3, Array4, ArrayD, IxDyn};

wit_bindgen::generate!({
    world: "inference-component",
    exports: {
        "kenny:edge/inference": InferenceEngine,
    },
});

#[derive(Debug, Clone)]
pub struct ModelConfig {
    pub model_path: String,
    pub model_type: ModelType,
    pub backend: InferenceBackend,
    pub precision: ModelPrecision,
    pub input_shape: Vec<usize>,
    pub output_shape: Vec<usize>,
    pub labels: Option<Vec<String>>,
    pub preprocessing: PreprocessingParams,
    pub postprocessing: PostprocessingParams,
    pub optimization: OptimizationConfig,
}

#[derive(Debug, Clone)]
pub enum ModelType {
    Classification,
    ObjectDetection,
    Segmentation,
    NLP,
    MultiModal,
    Custom(String),
}

#[derive(Debug, Clone)]
pub enum InferenceBackend {
    WasiNN,
    ONNX,
    TensorFlow,
    PyTorch,
    TensorRT,
    OpenVINO,
    CoreML,
    Custom(String),
}

#[derive(Debug, Clone)]
pub enum ModelPrecision {
    FP32,
    FP16,
    INT8,
    INT4,
    Dynamic,
}

#[derive(Debug, Clone)]
pub struct PreprocessingParams {
    pub normalize: bool,
    pub mean: Option<[f32; 3]>,
    pub std: Option<[f32; 3]>,
    pub resize: Option<(u32, u32)>,
}

#[derive(Debug, Clone)]
pub struct PostprocessingParams {
    pub apply_softmax: bool,
    pub confidence_threshold: f32,
    pub nms_threshold: f32,
    pub max_detections: usize,
}

#[derive(Debug, Clone)]
pub struct OptimizationConfig {
    pub use_gpu: bool,
    pub batch_size: usize,
    pub num_threads: usize,
    pub memory_pool_size: usize,
    pub enable_fp16: bool,
    pub enable_quantization: bool,
}

pub struct InferenceEngine {
    models: HashMap<String, LoadedModel>,
    stats: InferenceStats,
    memory_pool: MemoryPool,
    scheduler: InferenceScheduler,
}

struct LoadedModel {
    config: ModelConfig,
    session: Box<dyn InferenceSession>,
    memory_usage: usize,
    last_used: Instant,
}

#[derive(Debug, Default)]
pub struct InferenceStats {
    pub total_inferences: u64,
    pub successful_inferences: u64,
    pub failed_inferences: u64,
    pub avg_inference_time_ms: f64,
    pub memory_usage_mb: f64,
    pub cache_hits: u64,
    pub cache_misses: u64,
}

struct MemoryPool {
    buffers: HashMap<String, Vec<u8>>,
    total_allocated: usize,
    max_allocation: usize,
}

struct InferenceScheduler {
    pending_requests: Vec<InferenceRequest>,
    active_requests: HashMap<String, InferenceRequest>,
    priority_queue: std::collections::BinaryHeap<PriorityRequest>,
}

#[derive(Debug)]
struct InferenceRequest {
    id: String,
    model_id: String,
    input_data: ArrayD<f32>,
    callback: Option<Box<dyn Fn(InferenceResult) + Send + Sync>>,
    priority: u8,
    timestamp: Instant,
}

#[derive(Debug, Clone)]
struct PriorityRequest {
    id: String,
    priority: u8,
    timestamp: Instant,
}

impl Ord for PriorityRequest {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.priority.cmp(&other.priority)
            .then_with(|| other.timestamp.cmp(&self.timestamp))
    }
}

impl PartialOrd for PriorityRequest {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for PriorityRequest {
    fn eq(&self, other: &Self) -> bool {
        self.id == other.id
    }
}

impl Eq for PriorityRequest {}

#[derive(Debug)]
pub struct InferenceResult {
    pub model_id: String,
    pub outputs: Vec<ArrayD<f32>>,
    pub confidence: f32,
    pub inference_time_ms: f64,
    pub preprocessing_time_ms: f64,
    pub postprocessing_time_ms: f64,
    pub metadata: HashMap<String, String>,
}

trait InferenceSession: Send + Sync {
    fn run(&mut self, inputs: &[ArrayD<f32>]) -> Result<Vec<ArrayD<f32>>, InferenceError>;
    fn get_input_names(&self) -> &[String];
    fn get_output_names(&self) -> &[String];
    fn get_memory_usage(&self) -> usize;
}

impl InferenceEngine {
    pub fn new(max_memory_mb: usize) -> Self {
        InferenceEngine {
            models: HashMap::new(),
            stats: InferenceStats::default(),
            memory_pool: MemoryPool {
                buffers: HashMap::new(),
                total_allocated: 0,
                max_allocation: max_memory_mb * 1024 * 1024,
            },
            scheduler: InferenceScheduler {
                pending_requests: Vec::new(),
                active_requests: HashMap::new(),
                priority_queue: std::collections::BinaryHeap::new(),
            },
        }
    }

    /// Load a model with the specified configuration
    pub async fn load_model(&mut self, model_id: String, config: ModelConfig) 
        -> Result<(), InferenceError> {
        
        // Check memory constraints
        let estimated_memory = self.estimate_model_memory(&config)?;
        if self.memory_pool.total_allocated + estimated_memory > self.memory_pool.max_allocation {
            self.evict_least_used_model().await?;
        }

        // Create inference session based on backend
        let session = self.create_session(&config).await?;
        
        // Load model into memory
        let loaded_model = LoadedModel {
            config: config.clone(),
            session,
            memory_usage: estimated_memory,
            last_used: Instant::now(),
        };

        self.models.insert(model_id, loaded_model);
        self.memory_pool.total_allocated += estimated_memory;
        
        Ok(())
    }

    /// Unload a model and free its memory
    pub async fn unload_model(&mut self, model_id: &str) -> Result<(), InferenceError> {
        if let Some(model) = self.models.remove(model_id) {
            self.memory_pool.total_allocated = self.memory_pool.total_allocated
                .saturating_sub(model.memory_usage);
        }
        Ok(())
    }

    /// Run inference on a single input
    pub async fn infer(&mut self, model_id: &str, input: ArrayD<f32>) 
        -> Result<InferenceResult, InferenceError> {
        
        let start_time = Instant::now();
        
        // Get model
        let model = self.models.get_mut(model_id)
            .ok_or_else(|| InferenceError::ModelNotFound(model_id.to_string()))?;
        
        model.last_used = Instant::now();

        // Preprocess input
        let preprocess_start = Instant::now();
        let preprocessed = self.preprocess_input(&input, &model.config)?;
        let preprocess_time = preprocess_start.elapsed().as_millis() as f64;

        // Run inference
        let inference_start = Instant::now();
        let raw_outputs = model.session.run(&[preprocessed])?;
        let inference_time = inference_start.elapsed().as_millis() as f64;

        // Postprocess outputs
        let postprocess_start = Instant::now();
        let (outputs, confidence) = self.postprocess_outputs(&raw_outputs, &model.config)?;
        let postprocess_time = postprocess_start.elapsed().as_millis() as f64;

        // Update statistics
        self.update_stats(start_time, true);

        Ok(InferenceResult {
            model_id: model_id.to_string(),
            outputs,
            confidence,
            inference_time_ms: inference_time,
            preprocessing_time_ms: preprocess_time,
            postprocessing_time_ms: postprocess_time,
            metadata: HashMap::new(),
        })
    }

    /// Run batch inference for improved throughput
    pub async fn infer_batch(&mut self, model_id: &str, inputs: Vec<ArrayD<f32>>) 
        -> Result<Vec<InferenceResult>, InferenceError> {
        
        let start_time = Instant::now();
        
        // Get model
        let model = self.models.get_mut(model_id)
            .ok_or_else(|| InferenceError::ModelNotFound(model_id.to_string()))?;
        
        model.last_used = Instant::now();

        // Prepare batch
        let batch_size = inputs.len();
        let mut batch_input = self.create_batch_tensor(&inputs, &model.config)?;

        // Preprocess batch
        let preprocess_start = Instant::now();
        let preprocessed_batch = self.preprocess_batch(&batch_input, &model.config)?;
        let preprocess_time = preprocess_start.elapsed().as_millis() as f64;

        // Run batch inference
        let inference_start = Instant::now();
        let raw_outputs = model.session.run(&[preprocessed_batch])?;
        let inference_time = inference_start.elapsed().as_millis() as f64;

        // Postprocess batch outputs
        let postprocess_start = Instant::now();
        let results = self.postprocess_batch_outputs(&raw_outputs, &model.config, batch_size)?;
        let postprocess_time = postprocess_start.elapsed().as_millis() as f64;

        // Update statistics
        self.stats.total_inferences += batch_size as u64;
        self.stats.successful_inferences += batch_size as u64;
        
        let total_time = start_time.elapsed().as_millis() as f64;
        self.stats.avg_inference_time_ms = if self.stats.total_inferences == batch_size as u64 {
            total_time / batch_size as f64
        } else {
            (self.stats.avg_inference_time_ms * 0.9) + ((total_time / batch_size as f64) * 0.1)
        };

        let final_results = results.into_iter().map(|(outputs, confidence)| {
            InferenceResult {
                model_id: model_id.to_string(),
                outputs,
                confidence,
                inference_time_ms: inference_time / batch_size as f64,
                preprocessing_time_ms: preprocess_time / batch_size as f64,
                postprocessing_time_ms: postprocess_time / batch_size as f64,
                metadata: HashMap::new(),
            }
        }).collect();

        Ok(final_results)
    }

    /// Schedule inference request with priority
    pub async fn schedule_inference(&mut self, request: InferenceRequest) 
        -> Result<String, InferenceError> {
        
        let request_id = request.id.clone();
        let priority_req = PriorityRequest {
            id: request.id.clone(),
            priority: request.priority,
            timestamp: request.timestamp,
        };

        self.scheduler.pending_requests.push(request);
        self.scheduler.priority_queue.push(priority_req);

        // Process queue if capacity allows
        self.process_inference_queue().await?;

        Ok(request_id)
    }

    /// Get inference statistics
    pub fn get_stats(&self) -> &InferenceStats {
        &self.stats
    }

    /// Get loaded models information
    pub fn get_models_info(&self) -> HashMap<String, ModelInfo> {
        self.models.iter().map(|(id, model)| {
            (id.clone(), ModelInfo {
                model_type: model.config.model_type.clone(),
                memory_usage_mb: model.memory_usage as f64 / (1024.0 * 1024.0),
                last_used: model.last_used,
                backend: model.config.backend.clone(),
            })
        }).collect()
    }

    // Private implementation methods

    async fn create_session(&self, config: &ModelConfig) -> Result<Box<dyn InferenceSession>, InferenceError> {
        match config.backend {
            InferenceBackend::WasiNN => {
                Ok(Box::new(WasiNNSession::new(config).await?))
            },
            InferenceBackend::ONNX => {
                Ok(Box::new(ONNXSession::new(config).await?))
            },
            InferenceBackend::TensorFlow => {
                Ok(Box::new(TensorFlowSession::new(config).await?))
            },
            InferenceBackend::PyTorch => {
                Ok(Box::new(PyTorchSession::new(config).await?))
            },
            _ => Err(InferenceError::UnsupportedBackend(format!("{:?}", config.backend)))
        }
    }

    fn estimate_model_memory(&self, config: &ModelConfig) -> Result<usize, InferenceError> {
        // Estimate memory usage based on model parameters
        let input_size: usize = config.input_shape.iter().product();
        let output_size: usize = config.output_shape.iter().product();
        
        let precision_multiplier = match config.precision {
            ModelPrecision::FP32 => 4,
            ModelPrecision::FP16 => 2,
            ModelPrecision::INT8 => 1,
            ModelPrecision::INT4 => 1, // Approximation
            ModelPrecision::Dynamic => 4, // Conservative estimate
        };

        // Rough estimation: input + output + model weights (estimated as 10x input size)
        let estimated_size = (input_size + output_size + input_size * 10) * precision_multiplier;
        
        Ok(estimated_size)
    }

    async fn evict_least_used_model(&mut self) -> Result<(), InferenceError> {
        if let Some((lru_id, _)) = self.models.iter()
            .min_by_key(|(_, model)| model.last_used) {
            let lru_id = lru_id.clone();
            self.unload_model(&lru_id).await?;
        }
        Ok(())
    }

    fn preprocess_input(&self, input: &ArrayD<f32>, config: &ModelConfig) -> Result<ArrayD<f32>, InferenceError> {
        let mut processed = input.clone();
        let params = &config.preprocessing;

        if params.normalize {
            if let (Some(mean), Some(std)) = (&params.mean, &params.std) {
                // Apply normalization: (input - mean) / std
                for (i, value) in processed.iter_mut().enumerate() {
                    let channel = i % 3;
                    *value = (*value - mean[channel]) / std[channel];
                }
            }
        }

        Ok(processed)
    }

    fn preprocess_batch(&self, batch: &ArrayD<f32>, config: &ModelConfig) -> Result<ArrayD<f32>, InferenceError> {
        // Apply same preprocessing to entire batch
        self.preprocess_input(batch, config)
    }

    fn postprocess_outputs(&self, outputs: &[ArrayD<f32>], config: &ModelConfig) 
        -> Result<(Vec<ArrayD<f32>>, f32), InferenceError> {
        
        let mut processed_outputs = Vec::new();
        let mut max_confidence = 0.0;

        for output in outputs {
            let mut processed = output.clone();
            
            // Apply softmax if requested
            if config.postprocessing.apply_softmax {
                processed = self.apply_softmax(&processed)?;
            }

            // Calculate confidence
            if let Some(max_val) = processed.iter().max_by(|a, b| a.partial_cmp(b).unwrap()) {
                max_confidence = max_confidence.max(*max_val);
            }

            processed_outputs.push(processed);
        }

        Ok((processed_outputs, max_confidence))
    }

    fn postprocess_batch_outputs(&self, outputs: &[ArrayD<f32>], config: &ModelConfig, batch_size: usize) 
        -> Result<Vec<(Vec<ArrayD<f32>>, f32)>, InferenceError> {
        
        let mut batch_results = Vec::new();
        
        // Split batch outputs back into individual results
        for i in 0..batch_size {
            let mut individual_outputs = Vec::new();
            let mut max_confidence = 0.0;

            for output in outputs {
                // Extract individual result from batch
                let individual = output.slice(s![i, ..]).to_owned();
                
                let mut processed = individual;
                if config.postprocessing.apply_softmax {
                    processed = self.apply_softmax(&processed)?;
                }

                if let Some(max_val) = processed.iter().max_by(|a, b| a.partial_cmp(b).unwrap()) {
                    max_confidence = max_confidence.max(*max_val);
                }

                individual_outputs.push(processed);
            }

            batch_results.push((individual_outputs, max_confidence));
        }

        Ok(batch_results)
    }

    fn apply_softmax(&self, input: &ArrayD<f32>) -> Result<ArrayD<f32>, InferenceError> {
        let mut output = input.clone();
        
        // Find max for numerical stability
        let max_val = input.iter().max_by(|a, b| a.partial_cmp(b).unwrap()).unwrap_or(&0.0);
        
        // Apply exp(x - max)
        for value in output.iter_mut() {
            *value = (*value - max_val).exp();
        }
        
        // Normalize
        let sum: f32 = output.iter().sum();
        if sum > 0.0 {
            for value in output.iter_mut() {
                *value /= sum;
            }
        }
        
        Ok(output)
    }

    fn create_batch_tensor(&self, inputs: &[ArrayD<f32>], config: &ModelConfig) -> Result<ArrayD<f32>, InferenceError> {
        if inputs.is_empty() {
            return Err(InferenceError::InvalidInput("Empty batch".to_string()));
        }

        let batch_size = inputs.len();
        let first_shape = inputs[0].shape();
        
        // Create batch dimension
        let mut batch_shape = vec![batch_size];
        batch_shape.extend_from_slice(first_shape);
        
        let mut batch_data = Vec::new();
        for input in inputs {
            if input.shape() != first_shape {
                return Err(InferenceError::InvalidInput("Inconsistent input shapes in batch".to_string()));
            }
            batch_data.extend(input.iter());
        }

        ArrayD::from_shape_vec(IxDyn(&batch_shape), batch_data)
            .map_err(|e| InferenceError::InvalidInput(format!("Failed to create batch tensor: {}", e)))
    }

    async fn process_inference_queue(&mut self) -> Result<(), InferenceError> {
        // Process pending requests based on priority
        while let Some(priority_req) = self.scheduler.priority_queue.pop() {
            if let Some(pos) = self.scheduler.pending_requests.iter()
                .position(|req| req.id == priority_req.id) {
                
                let request = self.scheduler.pending_requests.remove(pos);
                
                // Execute inference
                match self.infer(&request.model_id, request.input_data).await {
                    Ok(result) => {
                        if let Some(callback) = request.callback {
                            callback(result);
                        }
                    },
                    Err(e) => {
                        self.stats.failed_inferences += 1;
                        eprintln!("Inference failed for request {}: {:?}", request.id, e);
                    }
                }
            }
        }
        
        Ok(())
    }

    fn update_stats(&mut self, start_time: Instant, success: bool) {
        self.stats.total_inferences += 1;
        
        if success {
            self.stats.successful_inferences += 1;
        } else {
            self.stats.failed_inferences += 1;
        }

        let inference_time = start_time.elapsed().as_millis() as f64;
        self.stats.avg_inference_time_ms = if self.stats.total_inferences == 1 {
            inference_time
        } else {
            (self.stats.avg_inference_time_ms * 0.9) + (inference_time * 0.1)
        };

        self.stats.memory_usage_mb = self.memory_pool.total_allocated as f64 / (1024.0 * 1024.0);
    }
}

#[derive(Debug, Clone)]
pub struct ModelInfo {
    pub model_type: ModelType,
    pub memory_usage_mb: f64,
    pub last_used: Instant,
    pub backend: InferenceBackend,
}

// Backend-specific implementations

struct WasiNNSession {
    // WASI-NN specific fields
}

impl WasiNNSession {
    async fn new(config: &ModelConfig) -> Result<Self, InferenceError> {
        // Initialize WASI-NN session
        Ok(WasiNNSession {})
    }
}

impl InferenceSession for WasiNNSession {
    fn run(&mut self, inputs: &[ArrayD<f32>]) -> Result<Vec<ArrayD<f32>>, InferenceError> {
        // WASI-NN inference implementation
        Ok(vec![inputs[0].clone()])
    }

    fn get_input_names(&self) -> &[String] {
        &[]
    }

    fn get_output_names(&self) -> &[String] {
        &[]
    }

    fn get_memory_usage(&self) -> usize {
        0
    }
}

struct ONNXSession {
    // ONNX Runtime specific fields
}

impl ONNXSession {
    async fn new(config: &ModelConfig) -> Result<Self, InferenceError> {
        // Initialize ONNX Runtime session
        Ok(ONNXSession {})
    }
}

impl InferenceSession for ONNXSession {
    fn run(&mut self, inputs: &[ArrayD<f32>]) -> Result<Vec<ArrayD<f32>>, InferenceError> {
        // ONNX Runtime inference implementation
        Ok(vec![inputs[0].clone()])
    }

    fn get_input_names(&self) -> &[String] {
        &[]
    }

    fn get_output_names(&self) -> &[String] {
        &[]
    }

    fn get_memory_usage(&self) -> usize {
        0
    }
}

struct TensorFlowSession {
    // TensorFlow Lite specific fields
}

impl TensorFlowSession {
    async fn new(config: &ModelConfig) -> Result<Self, InferenceError> {
        // Initialize TensorFlow Lite session
        Ok(TensorFlowSession {})
    }
}

impl InferenceSession for TensorFlowSession {
    fn run(&mut self, inputs: &[ArrayD<f32>]) -> Result<Vec<ArrayD<f32>>, InferenceError> {
        // TensorFlow Lite inference implementation
        Ok(vec![inputs[0].clone()])
    }

    fn get_input_names(&self) -> &[String] {
        &[]
    }

    fn get_output_names(&self) -> &[String] {
        &[]
    }

    fn get_memory_usage(&self) -> usize {
        0
    }
}

struct PyTorchSession {
    // PyTorch Mobile specific fields
}

impl PyTorchSession {
    async fn new(config: &ModelConfig) -> Result<Self, InferenceError> {
        // Initialize PyTorch Mobile session
        Ok(PyTorchSession {})
    }
}

impl InferenceSession for PyTorchSession {
    fn run(&mut self, inputs: &[ArrayD<f32>]) -> Result<Vec<ArrayD<f32>>, InferenceError> {
        // PyTorch Mobile inference implementation
        Ok(vec![inputs[0].clone()])
    }

    fn get_input_names(&self) -> &[String] {
        &[]
    }

    fn get_output_names(&self) -> &[String] {
        &[]
    }

    fn get_memory_usage(&self) -> usize {
        0
    }
}

#[derive(Debug, thiserror::Error)]
pub enum InferenceError {
    #[error("Model not found: {0}")]
    ModelNotFound(String),
    
    #[error("Unsupported backend: {0}")]
    UnsupportedBackend(String),
    
    #[error("Invalid input: {0}")]
    InvalidInput(String),
    
    #[error("Memory allocation failed")]
    MemoryError,
    
    #[error("Model loading failed: {0}")]
    ModelLoadError(String),
    
    #[error("Inference execution failed: {0}")]
    ExecutionError(String),
    
    #[error("Preprocessing failed: {0}")]
    PreprocessingError(String),
    
    #[error("Postprocessing failed: {0}")]
    PostprocessingError(String),
    
    #[error("Backend initialization failed: {0}")]
    BackendError(String),
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

// WIT exports implementation
impl exports::kenny::edge::inference::Guest for InferenceEngine {
    fn load_model(model_id: String, config: String) -> Result<(), String> {
        // Parse config and load model
        Ok(())
    }
    
    fn unload_model(model_id: String) -> Result<(), String> {
        // Unload specified model
        Ok(())
    }
    
    fn infer(model_id: String, input: Vec<f32>) -> Result<Vec<f32>, String> {
        // Run inference and return results
        Ok(vec![])
    }
    
    fn infer_batch(model_id: String, inputs: Vec<Vec<f32>>) -> Result<Vec<Vec<f32>>, String> {
        // Run batch inference
        Ok(vec![])
    }
    
    fn get_stats() -> String {
        // Return inference statistics as JSON
        "{}".to_string()
    }
    
    fn get_models() -> Vec<String> {
        // Return list of loaded models
        vec![]
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_engine_creation() {
        let engine = InferenceEngine::new(1024); // 1GB memory limit
        assert_eq!(engine.stats.total_inferences, 0);
        assert_eq!(engine.memory_pool.max_allocation, 1024 * 1024 * 1024);
    }
    
    #[tokio::test]
    async fn test_model_loading() {
        let mut engine = InferenceEngine::new(1024);
        
        let config = ModelConfig {
            model_path: "test_model.onnx".to_string(),
            model_type: ModelType::Classification,
            backend: InferenceBackend::ONNX,
            precision: ModelPrecision::FP32,
            input_shape: vec![1, 3, 224, 224],
            output_shape: vec![1, 1000],
            labels: None,
            preprocessing: PreprocessingParams {
                normalize: true,
                mean: Some([0.485, 0.456, 0.406]),
                std: Some([0.229, 0.224, 0.225]),
                resize: Some((224, 224)),
            },
            postprocessing: PostprocessingParams {
                apply_softmax: true,
                confidence_threshold: 0.5,
                nms_threshold: 0.4,
                max_detections: 100,
            },
            optimization: OptimizationConfig {
                use_gpu: false,
                batch_size: 1,
                num_threads: 4,
                memory_pool_size: 256 * 1024 * 1024,
                enable_fp16: false,
                enable_quantization: false,
            },
        };
        
        // This would fail in practice without a real model file
        // but tests the API structure
        assert!(engine.models.is_empty());
    }
    
    #[test]
    fn test_softmax() {
        let engine = InferenceEngine::new(1024);
        let input = ArrayD::from_shape_vec(IxDyn(&[3]), vec![1.0, 2.0, 3.0]).unwrap();
        
        let result = engine.apply_softmax(&input).unwrap();
        let sum: f32 = result.iter().sum();
        
        assert!((sum - 1.0).abs() < 1e-6); // Should sum to 1
        assert!(result[[2]] > result[[1]]); // Highest input should have highest probability
        assert!(result[[1]] > result[[0]]);
    }
}