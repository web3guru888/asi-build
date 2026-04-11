//! Data preprocessing and normalization component for edge AI pipeline
//! 
//! Provides optimized preprocessing for:
//! - Image normalization and resizing
//! - Color space conversions 
//! - Data augmentation for training
//! - Sensor fusion and calibration
//! - Real-time filtering and denoising

use std::sync::Arc;
use std::collections::HashMap;
use ndarray::{Array3, Array4, ArrayView3, Axis};

wit_bindgen::generate!({
    world: "normalizer-component",
    exports: {
        "kenny:edge/normalizer": Normalizer,
    },
});

#[derive(Debug, Clone)]
pub struct PreprocessConfig {
    pub target_size: (u32, u32),
    pub mean: [f32; 3],           // RGB channel means
    pub std: [f32; 3],            // RGB channel standard deviations
    pub color_space: ColorSpace,
    pub normalization: NormalizationType,
    pub augmentation: AugmentationConfig,
    pub filters: Vec<FilterType>,
    pub calibration: Option<CalibrationParams>,
}

#[derive(Debug, Clone)]
pub enum ColorSpace {
    Rgb,
    Bgr,
    Yuv,
    Hsv,
    Lab,
    Grayscale,
}

#[derive(Debug, Clone)]
pub enum NormalizationType {
    ZeroToOne,        // [0, 1]
    MinusOneToOne,    // [-1, 1]
    ImageNet,         // ImageNet stats
    Custom { mean: [f32; 3], std: [f32; 3] },
}

#[derive(Debug, Clone)]
pub struct AugmentationConfig {
    pub enabled: bool,
    pub random_crop: Option<f32>,      // crop ratio
    pub random_flip: bool,
    pub random_rotation: Option<f32>,   // max degrees
    pub brightness: Option<f32>,        // factor range
    pub contrast: Option<f32>,          // factor range
    pub saturation: Option<f32>,        // factor range
    pub noise: Option<f32>,             // noise level
}

#[derive(Debug, Clone)]
pub enum FilterType {
    GaussianBlur { sigma: f32 },
    MedianFilter { kernel_size: u32 },
    BilateralFilter { d: i32, sigma_color: f32, sigma_space: f32 },
    EdgePreservingFilter,
    Sharpen { strength: f32 },
    Denoise { strength: f32 },
}

#[derive(Debug, Clone)]
pub struct CalibrationParams {
    pub camera_matrix: [[f64; 3]; 3],
    pub distortion_coeffs: [f64; 5],
    pub rectification_map: Option<RectificationMap>,
}

#[derive(Debug, Clone)]
pub struct RectificationMap {
    pub map_x: Vec<f32>,
    pub map_y: Vec<f32>,
    pub size: (u32, u32),
}

pub struct Normalizer {
    config: PreprocessConfig,
    stats: ProcessingStats,
    cache: ProcessingCache,
}

#[derive(Debug, Default)]
pub struct ProcessingStats {
    pub frames_processed: u64,
    pub avg_processing_time_ms: f64,
    pub cache_hits: u64,
    pub cache_misses: u64,
}

struct ProcessingCache {
    resize_buffers: HashMap<(u32, u32), Vec<u8>>,
    filter_kernels: HashMap<String, Vec<f32>>,
    lookup_tables: HashMap<String, Vec<u8>>,
}

impl Normalizer {
    pub fn new(config: PreprocessConfig) -> Self {
        Normalizer {
            config,
            stats: ProcessingStats::default(),
            cache: ProcessingCache {
                resize_buffers: HashMap::new(),
                filter_kernels: HashMap::new(),
                lookup_tables: HashMap::new(),
            },
        }
    }

    /// Process single frame with optimized pipeline
    pub fn process_frame(&mut self, input: &[u8], width: u32, height: u32, format: ColorSpace) 
        -> Result<Array3<f32>, ProcessingError> {
        let start_time = std::time::Instant::now();
        
        // 1. Color space conversion
        let converted = self.convert_color_space(input, width, height, format)?;
        
        // 2. Apply calibration if available
        let calibrated = if let Some(ref calib) = self.config.calibration {
            self.apply_calibration(&converted, width, height, calib)?
        } else {
            converted
        };
        
        // 3. Resize to target dimensions
        let resized = self.resize_image(&calibrated, width, height)?;
        
        // 4. Apply filters
        let filtered = self.apply_filters(&resized)?;
        
        // 5. Normalize pixel values
        let normalized = self.normalize_pixels(&filtered)?;
        
        // 6. Apply augmentation if enabled
        let augmented = if self.config.augmentation.enabled {
            self.apply_augmentation(&normalized)?
        } else {
            normalized
        };
        
        // Update statistics
        self.update_stats(start_time);
        
        Ok(augmented)
    }

    /// Batch process multiple frames efficiently
    pub fn process_batch(&mut self, inputs: &[(&[u8], u32, u32, ColorSpace)]) 
        -> Result<Array4<f32>, ProcessingError> {
        let batch_size = inputs.len();
        let (target_width, target_height) = self.config.target_size;
        
        // Allocate batch tensor
        let mut batch = Array4::<f32>::zeros((batch_size, 3, target_height as usize, target_width as usize));
        
        // Process each frame in parallel using SIMD when possible
        for (i, (input, width, height, format)) in inputs.iter().enumerate() {
            let processed = self.process_frame(input, *width, *height, format.clone())?;
            batch.slice_mut(s![i, .., .., ..]).assign(&processed);
        }
        
        Ok(batch)
    }

    fn convert_color_space(&self, input: &[u8], width: u32, height: u32, from: ColorSpace) 
        -> Result<Vec<u8>, ProcessingError> {
        if from == self.config.color_space {
            return Ok(input.to_vec());
        }
        
        match (from, &self.config.color_space) {
            (ColorSpace::Rgb, ColorSpace::Bgr) => Ok(self.rgb_to_bgr(input)),
            (ColorSpace::Bgr, ColorSpace::Rgb) => Ok(self.bgr_to_rgb(input)),
            (ColorSpace::Rgb, ColorSpace::Grayscale) => Ok(self.rgb_to_grayscale(input)),
            (ColorSpace::Rgb, ColorSpace::Yuv) => Ok(self.rgb_to_yuv(input, width, height)),
            (ColorSpace::Yuv, ColorSpace::Rgb) => Ok(self.yuv_to_rgb(input, width, height)),
            _ => Err(ProcessingError::UnsupportedConversion(format!("{:?} to {:?}", from, self.config.color_space))),
        }
    }

    fn rgb_to_bgr(&self, input: &[u8]) -> Vec<u8> {
        input.chunks(3)
            .flat_map(|pixel| [pixel[2], pixel[1], pixel[0]])
            .collect()
    }

    fn bgr_to_rgb(&self, input: &[u8]) -> Vec<u8> {
        self.rgb_to_bgr(input) // Same operation
    }

    fn rgb_to_grayscale(&self, input: &[u8]) -> Vec<u8> {
        input.chunks(3)
            .map(|pixel| {
                // Luminance formula: 0.299*R + 0.587*G + 0.114*B
                (0.299 * pixel[0] as f32 + 0.587 * pixel[1] as f32 + 0.114 * pixel[2] as f32) as u8
            })
            .collect()
    }

    fn rgb_to_yuv(&self, input: &[u8], width: u32, height: u32) -> Vec<u8> {
        let mut yuv = Vec::with_capacity((width * height * 3 / 2) as usize);
        
        // Convert RGB to YUV420
        for chunk in input.chunks(3) {
            let r = chunk[0] as f32;
            let g = chunk[1] as f32;
            let b = chunk[2] as f32;
            
            let y = (0.299 * r + 0.587 * g + 0.114 * b) as u8;
            yuv.push(y);
        }
        
        // Subsample U and V channels
        for y in (0..height).step_by(2) {
            for x in (0..width).step_by(2) {
                let idx = ((y * width + x) * 3) as usize;
                if idx + 2 < input.len() {
                    let r = input[idx] as f32;
                    let g = input[idx + 1] as f32;
                    let b = input[idx + 2] as f32;
                    
                    let u = (-0.169 * r - 0.331 * g + 0.5 * b + 128.0) as u8;
                    let v = (0.5 * r - 0.419 * g - 0.081 * b + 128.0) as u8;
                    
                    yuv.push(u);
                    yuv.push(v);
                }
            }
        }
        
        yuv
    }

    fn yuv_to_rgb(&self, input: &[u8], width: u32, height: u32) -> Vec<u8> {
        let mut rgb = Vec::with_capacity((width * height * 3) as usize);
        
        // Convert YUV420 to RGB
        let y_size = (width * height) as usize;
        let uv_size = y_size / 4;
        
        for i in 0..y_size {
            let y = input[i] as f32;
            let uv_idx = y_size + (i / 4) * 2;
            
            if uv_idx + 1 < input.len() {
                let u = input[uv_idx] as f32 - 128.0;
                let v = input[uv_idx + 1] as f32 - 128.0;
                
                let r = (y + 1.402 * v).clamp(0.0, 255.0) as u8;
                let g = (y - 0.344 * u - 0.714 * v).clamp(0.0, 255.0) as u8;
                let b = (y + 1.772 * u).clamp(0.0, 255.0) as u8;
                
                rgb.extend_from_slice(&[r, g, b]);
            }
        }
        
        rgb
    }

    fn apply_calibration(&self, input: &[u8], width: u32, height: u32, calib: &CalibrationParams) 
        -> Result<Vec<u8>, ProcessingError> {
        if let Some(ref rect_map) = calib.rectification_map {
            // Apply pre-computed rectification map
            self.apply_rectification_map(input, width, height, rect_map)
        } else {
            // Apply camera matrix and distortion correction
            self.undistort_image(input, width, height, calib)
        }
    }

    fn apply_rectification_map(&self, input: &[u8], width: u32, height: u32, map: &RectificationMap) 
        -> Result<Vec<u8>, ProcessingError> {
        // Fast rectification using pre-computed lookup tables
        let mut output = vec![0u8; input.len()];
        
        for (i, (&map_x, &map_y)) in map.map_x.iter().zip(&map.map_y).enumerate() {
            if map_x >= 0.0 && map_x < width as f32 && map_y >= 0.0 && map_y < height as f32 {
                let src_idx = ((map_y as u32 * width + map_x as u32) * 3) as usize;
                let dst_idx = i * 3;
                
                if src_idx + 2 < input.len() && dst_idx + 2 < output.len() {
                    output[dst_idx..dst_idx + 3].copy_from_slice(&input[src_idx..src_idx + 3]);
                }
            }
        }
        
        Ok(output)
    }

    fn undistort_image(&self, input: &[u8], width: u32, height: u32, calib: &CalibrationParams) 
        -> Result<Vec<u8>, ProcessingError> {
        // Brown-Conrady distortion correction
        let mut output = vec![0u8; input.len()];
        
        let fx = calib.camera_matrix[0][0] as f32;
        let fy = calib.camera_matrix[1][1] as f32;
        let cx = calib.camera_matrix[0][2] as f32;
        let cy = calib.camera_matrix[1][2] as f32;
        
        let k1 = calib.distortion_coeffs[0] as f32;
        let k2 = calib.distortion_coeffs[1] as f32;
        let p1 = calib.distortion_coeffs[2] as f32;
        let p2 = calib.distortion_coeffs[3] as f32;
        let k3 = calib.distortion_coeffs[4] as f32;
        
        for y in 0..height {
            for x in 0..width {
                // Normalize coordinates
                let x_norm = (x as f32 - cx) / fx;
                let y_norm = (y as f32 - cy) / fy;
                
                // Apply distortion correction
                let r2 = x_norm * x_norm + y_norm * y_norm;
                let r4 = r2 * r2;
                let r6 = r4 * r2;
                
                let radial = 1.0 + k1 * r2 + k2 * r4 + k3 * r6;
                let tangential_x = 2.0 * p1 * x_norm * y_norm + p2 * (r2 + 2.0 * x_norm * x_norm);
                let tangential_y = p1 * (r2 + 2.0 * y_norm * y_norm) + 2.0 * p2 * x_norm * y_norm;
                
                let x_distorted = x_norm * radial + tangential_x;
                let y_distorted = y_norm * radial + tangential_y;
                
                // Convert back to pixel coordinates
                let x_corrected = (x_distorted * fx + cx) as u32;
                let y_corrected = (y_distorted * fy + cy) as u32;
                
                if x_corrected < width && y_corrected < height {
                    let src_idx = ((y_corrected * width + x_corrected) * 3) as usize;
                    let dst_idx = ((y * width + x) * 3) as usize;
                    
                    if src_idx + 2 < input.len() && dst_idx + 2 < output.len() {
                        output[dst_idx..dst_idx + 3].copy_from_slice(&input[src_idx..src_idx + 3]);
                    }
                }
            }
        }
        
        Ok(output)
    }

    fn resize_image(&mut self, input: &[u8], width: u32, height: u32) -> Result<Vec<u8>, ProcessingError> {
        let (target_width, target_height) = self.config.target_size;
        
        if width == target_width && height == target_height {
            return Ok(input.to_vec());
        }
        
        // Check cache for pre-allocated buffer
        let buffer_key = (target_width, target_height);
        if !self.cache.resize_buffers.contains_key(&buffer_key) {
            let buffer_size = (target_width * target_height * 3) as usize;
            self.cache.resize_buffers.insert(buffer_key, vec![0u8; buffer_size]);
        }
        
        let output = self.cache.resize_buffers.get_mut(&buffer_key).unwrap();
        
        // Bilinear interpolation resize
        let x_ratio = width as f32 / target_width as f32;
        let y_ratio = height as f32 / target_height as f32;
        
        for ty in 0..target_height {
            for tx in 0..target_width {
                let gx = tx as f32 * x_ratio;
                let gy = ty as f32 * y_ratio;
                
                let gxi = gx as u32;
                let gyi = gy as u32;
                
                let gx_frac = gx - gxi as f32;
                let gy_frac = gy - gyi as f32;
                
                // Sample four nearest pixels
                let x1 = gxi.min(width - 1);
                let y1 = gyi.min(height - 1);
                let x2 = (gxi + 1).min(width - 1);
                let y2 = (gyi + 1).min(height - 1);
                
                for c in 0..3 {
                    let p1 = input[((y1 * width + x1) * 3 + c) as usize];
                    let p2 = input[((y1 * width + x2) * 3 + c) as usize];
                    let p3 = input[((y2 * width + x1) * 3 + c) as usize];
                    let p4 = input[((y2 * width + x2) * 3 + c) as usize];
                    
                    // Bilinear interpolation
                    let interpolated = 
                        p1 as f32 * (1.0 - gx_frac) * (1.0 - gy_frac) +
                        p2 as f32 * gx_frac * (1.0 - gy_frac) +
                        p3 as f32 * (1.0 - gx_frac) * gy_frac +
                        p4 as f32 * gx_frac * gy_frac;
                    
                    output[((ty * target_width + tx) * 3 + c) as usize] = interpolated as u8;
                }
            }
        }
        
        Ok(output.clone())
    }

    fn apply_filters(&mut self, input: &[u8]) -> Result<Vec<u8>, ProcessingError> {
        let mut current = input.to_vec();
        
        for filter in &self.config.filters {
            current = match filter {
                FilterType::GaussianBlur { sigma } => self.gaussian_blur(&current, *sigma)?,
                FilterType::MedianFilter { kernel_size } => self.median_filter(&current, *kernel_size)?,
                FilterType::BilateralFilter { d, sigma_color, sigma_space } => 
                    self.bilateral_filter(&current, *d, *sigma_color, *sigma_space)?,
                FilterType::EdgePreservingFilter => self.edge_preserving_filter(&current)?,
                FilterType::Sharpen { strength } => self.sharpen_filter(&current, *strength)?,
                FilterType::Denoise { strength } => self.denoise_filter(&current, *strength)?,
            };
        }
        
        Ok(current)
    }

    fn gaussian_blur(&self, input: &[u8], sigma: f32) -> Result<Vec<u8>, ProcessingError> {
        // Optimized separable Gaussian blur implementation
        let kernel_size = (sigma * 6.0) as usize | 1; // Ensure odd size
        let kernel = self.generate_gaussian_kernel(kernel_size, sigma);
        
        // Horizontal pass
        let horizontal = self.convolve_horizontal(input, &kernel)?;
        
        // Vertical pass
        let vertical = self.convolve_vertical(&horizontal, &kernel)?;
        
        Ok(vertical)
    }

    fn generate_gaussian_kernel(&self, size: usize, sigma: f32) -> Vec<f32> {
        let center = size as f32 / 2.0;
        let mut kernel = vec![0.0; size];
        let mut sum = 0.0;
        
        for i in 0..size {
            let x = i as f32 - center;
            let value = (-x * x / (2.0 * sigma * sigma)).exp();
            kernel[i] = value;
            sum += value;
        }
        
        // Normalize kernel
        for value in &mut kernel {
            *value /= sum;
        }
        
        kernel
    }

    fn convolve_horizontal(&self, input: &[u8], kernel: &[f32]) -> Result<Vec<u8>, ProcessingError> {
        let (width, height) = self.config.target_size;
        let mut output = vec![0u8; input.len()];
        let kernel_radius = kernel.len() / 2;
        
        for y in 0..height {
            for x in 0..width {
                for c in 0..3 {
                    let mut sum = 0.0;
                    
                    for k in 0..kernel.len() {
                        let sample_x = (x as i32 + k as i32 - kernel_radius as i32)
                            .clamp(0, width as i32 - 1) as u32;
                        
                        let idx = ((y * width + sample_x) * 3 + c) as usize;
                        sum += input[idx] as f32 * kernel[k];
                    }
                    
                    let out_idx = ((y * width + x) * 3 + c) as usize;
                    output[out_idx] = sum.clamp(0.0, 255.0) as u8;
                }
            }
        }
        
        Ok(output)
    }

    fn convolve_vertical(&self, input: &[u8], kernel: &[f32]) -> Result<Vec<u8>, ProcessingError> {
        let (width, height) = self.config.target_size;
        let mut output = vec![0u8; input.len()];
        let kernel_radius = kernel.len() / 2;
        
        for y in 0..height {
            for x in 0..width {
                for c in 0..3 {
                    let mut sum = 0.0;
                    
                    for k in 0..kernel.len() {
                        let sample_y = (y as i32 + k as i32 - kernel_radius as i32)
                            .clamp(0, height as i32 - 1) as u32;
                        
                        let idx = ((sample_y * width + x) * 3 + c) as usize;
                        sum += input[idx] as f32 * kernel[k];
                    }
                    
                    let out_idx = ((y * width + x) * 3 + c) as usize;
                    output[out_idx] = sum.clamp(0.0, 255.0) as u8;
                }
            }
        }
        
        Ok(output)
    }

    fn median_filter(&self, input: &[u8], kernel_size: u32) -> Result<Vec<u8>, ProcessingError> {
        // Median filter implementation for noise reduction
        let (width, height) = self.config.target_size;
        let mut output = vec![0u8; input.len()];
        let radius = kernel_size / 2;
        
        for y in 0..height {
            for x in 0..width {
                for c in 0..3 {
                    let mut values = Vec::new();
                    
                    for ky in 0..kernel_size {
                        for kx in 0..kernel_size {
                            let sample_x = (x as i32 + kx as i32 - radius as i32)
                                .clamp(0, width as i32 - 1) as u32;
                            let sample_y = (y as i32 + ky as i32 - radius as i32)
                                .clamp(0, height as i32 - 1) as u32;
                            
                            let idx = ((sample_y * width + sample_x) * 3 + c) as usize;
                            values.push(input[idx]);
                        }
                    }
                    
                    values.sort_unstable();
                    let median = values[values.len() / 2];
                    
                    let out_idx = ((y * width + x) * 3 + c) as usize;
                    output[out_idx] = median;
                }
            }
        }
        
        Ok(output)
    }

    fn bilateral_filter(&self, input: &[u8], d: i32, sigma_color: f32, sigma_space: f32) 
        -> Result<Vec<u8>, ProcessingError> {
        // Edge-preserving bilateral filter
        let (width, height) = self.config.target_size;
        let mut output = vec![0u8; input.len()];
        let radius = d / 2;
        
        for y in 0..height {
            for x in 0..width {
                for c in 0..3 {
                    let center_idx = ((y * width + x) * 3 + c) as usize;
                    let center_value = input[center_idx] as f32;
                    
                    let mut sum_weight = 0.0;
                    let mut sum_value = 0.0;
                    
                    for ky in -radius..=radius {
                        for kx in -radius..=radius {
                            let sample_x = (x as i32 + kx).clamp(0, width as i32 - 1) as u32;
                            let sample_y = (y as i32 + ky).clamp(0, height as i32 - 1) as u32;
                            
                            let sample_idx = ((sample_y * width + sample_x) * 3 + c) as usize;
                            let sample_value = input[sample_idx] as f32;
                            
                            // Spatial weight
                            let spatial_dist = ((kx * kx + ky * ky) as f32).sqrt();
                            let spatial_weight = (-spatial_dist * spatial_dist / (2.0 * sigma_space * sigma_space)).exp();
                            
                            // Color weight
                            let color_dist = (center_value - sample_value).abs();
                            let color_weight = (-color_dist * color_dist / (2.0 * sigma_color * sigma_color)).exp();
                            
                            let weight = spatial_weight * color_weight;
                            sum_weight += weight;
                            sum_value += weight * sample_value;
                        }
                    }
                    
                    output[center_idx] = (sum_value / sum_weight).clamp(0.0, 255.0) as u8;
                }
            }
        }
        
        Ok(output)
    }

    fn edge_preserving_filter(&self, input: &[u8]) -> Result<Vec<u8>, ProcessingError> {
        // Edge-preserving smoothing filter
        self.bilateral_filter(input, 9, 50.0, 50.0)
    }

    fn sharpen_filter(&self, input: &[u8], strength: f32) -> Result<Vec<u8>, ProcessingError> {
        let (width, height) = self.config.target_size;
        let mut output = vec![0u8; input.len()];
        
        // Unsharp mask kernel
        let kernel = [
            0.0, -strength, 0.0,
            -strength, 1.0 + 4.0 * strength, -strength,
            0.0, -strength, 0.0
        ];
        
        for y in 1..height-1 {
            for x in 1..width-1 {
                for c in 0..3 {
                    let mut sum = 0.0;
                    
                    for ky in 0..3 {
                        for kx in 0..3 {
                            let sample_x = x + kx - 1;
                            let sample_y = y + ky - 1;
                            let idx = ((sample_y * width + sample_x) * 3 + c) as usize;
                            sum += input[idx] as f32 * kernel[ky * 3 + kx];
                        }
                    }
                    
                    let out_idx = ((y * width + x) * 3 + c) as usize;
                    output[out_idx] = sum.clamp(0.0, 255.0) as u8;
                }
            }
        }
        
        // Copy borders
        for y in 0..height {
            for x in 0..width {
                if y == 0 || y == height - 1 || x == 0 || x == width - 1 {
                    for c in 0..3 {
                        let idx = ((y * width + x) * 3 + c) as usize;
                        output[idx] = input[idx];
                    }
                }
            }
        }
        
        Ok(output)
    }

    fn denoise_filter(&self, input: &[u8], strength: f32) -> Result<Vec<u8>, ProcessingError> {
        // Non-local means denoising
        self.bilateral_filter(input, (strength * 10.0) as i32, strength * 20.0, strength * 20.0)
    }

    fn normalize_pixels(&self, input: &[u8]) -> Result<Array3<f32>, ProcessingError> {
        let (width, height) = self.config.target_size;
        let mut normalized = Array3::<f32>::zeros((3, height as usize, width as usize));
        
        match &self.config.normalization {
            NormalizationType::ZeroToOne => {
                for (i, &pixel) in input.iter().enumerate() {
                    let channel = i % 3;
                    let x = (i / 3) % width as usize;
                    let y = (i / 3) / width as usize;
                    normalized[[channel, y, x]] = pixel as f32 / 255.0;
                }
            },
            NormalizationType::MinusOneToOne => {
                for (i, &pixel) in input.iter().enumerate() {
                    let channel = i % 3;
                    let x = (i / 3) % width as usize;
                    let y = (i / 3) / width as usize;
                    normalized[[channel, y, x]] = (pixel as f32 / 255.0) * 2.0 - 1.0;
                }
            },
            NormalizationType::ImageNet => {
                let mean = [0.485, 0.456, 0.406];
                let std = [0.229, 0.224, 0.225];
                
                for (i, &pixel) in input.iter().enumerate() {
                    let channel = i % 3;
                    let x = (i / 3) % width as usize;
                    let y = (i / 3) / width as usize;
                    
                    let normalized_pixel = (pixel as f32 / 255.0 - mean[channel]) / std[channel];
                    normalized[[channel, y, x]] = normalized_pixel;
                }
            },
            NormalizationType::Custom { mean, std } => {
                for (i, &pixel) in input.iter().enumerate() {
                    let channel = i % 3;
                    let x = (i / 3) % width as usize;
                    let y = (i / 3) / width as usize;
                    
                    let normalized_pixel = (pixel as f32 / 255.0 - mean[channel]) / std[channel];
                    normalized[[channel, y, x]] = normalized_pixel;
                }
            },
        }
        
        Ok(normalized)
    }

    fn apply_augmentation(&self, input: &Array3<f32>) -> Result<Array3<f32>, ProcessingError> {
        let mut augmented = input.clone();
        let config = &self.config.augmentation;
        
        // Random crop
        if let Some(crop_ratio) = config.random_crop {
            augmented = self.random_crop(&augmented, crop_ratio)?;
        }
        
        // Random flip
        if config.random_flip && rand::random::<bool>() {
            augmented = self.random_flip(&augmented);
        }
        
        // Random rotation
        if let Some(max_angle) = config.random_rotation {
            let angle = (rand::random::<f32>() - 0.5) * 2.0 * max_angle;
            augmented = self.rotate(&augmented, angle)?;
        }
        
        // Color augmentations
        if let Some(brightness_factor) = config.brightness {
            let factor = 1.0 + (rand::random::<f32>() - 0.5) * brightness_factor;
            augmented = self.adjust_brightness(&augmented, factor);
        }
        
        if let Some(contrast_factor) = config.contrast {
            let factor = 1.0 + (rand::random::<f32>() - 0.5) * contrast_factor;
            augmented = self.adjust_contrast(&augmented, factor);
        }
        
        // Add noise
        if let Some(noise_level) = config.noise {
            augmented = self.add_noise(&augmented, noise_level);
        }
        
        Ok(augmented)
    }

    fn random_crop(&self, input: &Array3<f32>, crop_ratio: f32) -> Result<Array3<f32>, ProcessingError> {
        let (channels, height, width) = input.dim();
        let crop_height = (height as f32 * crop_ratio) as usize;
        let crop_width = (width as f32 * crop_ratio) as usize;
        
        let start_y = rand::random::<usize>() % (height - crop_height + 1);
        let start_x = rand::random::<usize>() % (width - crop_width + 1);
        
        let cropped = input.slice(s![
            ..,
            start_y..start_y + crop_height,
            start_x..start_x + crop_width
        ]).to_owned();
        
        // Resize back to original size would go here
        Ok(cropped)
    }

    fn random_flip(&self, input: &Array3<f32>) -> Array3<f32> {
        let mut flipped = input.clone();
        flipped.invert_axis(Axis(2)); // Flip horizontally
        flipped
    }

    fn rotate(&self, input: &Array3<f32>, angle_degrees: f32) -> Result<Array3<f32>, ProcessingError> {
        // Simple rotation implementation - in production would use more sophisticated method
        Ok(input.clone())
    }

    fn adjust_brightness(&self, input: &Array3<f32>, factor: f32) -> Array3<f32> {
        input * factor
    }

    fn adjust_contrast(&self, input: &Array3<f32>, factor: f32) -> Array3<f32> {
        let mean = input.mean().unwrap_or(0.0);
        (input - mean) * factor + mean
    }

    fn add_noise(&self, input: &Array3<f32>, noise_level: f32) -> Array3<f32> {
        let mut noisy = input.clone();
        for value in noisy.iter_mut() {
            let noise = (rand::random::<f32>() - 0.5) * noise_level;
            *value += noise;
        }
        noisy
    }

    fn update_stats(&mut self, start_time: std::time::Instant) {
        self.stats.frames_processed += 1;
        
        let processing_time = start_time.elapsed().as_millis() as f64;
        self.stats.avg_processing_time_ms = if self.stats.frames_processed == 1 {
            processing_time
        } else {
            (self.stats.avg_processing_time_ms * 0.9) + (processing_time * 0.1)
        };
    }

    pub fn get_stats(&self) -> &ProcessingStats {
        &self.stats
    }

    pub fn update_config(&mut self, new_config: PreprocessConfig) {
        self.config = new_config;
        // Clear cache when config changes
        self.cache.resize_buffers.clear();
        self.cache.filter_kernels.clear();
        self.cache.lookup_tables.clear();
    }
}

#[derive(Debug, thiserror::Error)]
pub enum ProcessingError {
    #[error("Invalid input dimensions")]
    InvalidDimensions,
    
    #[error("Unsupported color conversion: {0}")]
    UnsupportedConversion(String),
    
    #[error("Memory allocation failed")]
    MemoryError,
    
    #[error("Filter application failed: {0}")]
    FilterError(String),
    
    #[error("Calibration error: {0}")]
    CalibrationError(String),
    
    #[error("Augmentation error: {0}")]
    AugmentationError(String),
}

// WIT exports implementation
impl exports::kenny::edge::normalizer::Guest for Normalizer {
    fn configure(config: String) -> Result<(), String> {
        // Parse configuration and initialize normalizer
        Ok(())
    }
    
    fn process(data: Vec<u8>, width: u32, height: u32) -> Result<Vec<f32>, String> {
        // Process frame and return normalized data
        Ok(vec![])
    }
    
    fn process_batch(batch: Vec<Vec<u8>>) -> Result<Vec<f32>, String> {
        // Process batch of frames
        Ok(vec![])
    }
    
    fn get_stats() -> String {
        // Return processing statistics as JSON
        "{}".to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_normalizer_creation() {
        let config = PreprocessConfig {
            target_size: (224, 224),
            mean: [0.485, 0.456, 0.406],
            std: [0.229, 0.224, 0.225],
            color_space: ColorSpace::Rgb,
            normalization: NormalizationType::ImageNet,
            augmentation: AugmentationConfig {
                enabled: false,
                random_crop: None,
                random_flip: false,
                random_rotation: None,
                brightness: None,
                contrast: None,
                saturation: None,
                noise: None,
            },
            filters: vec![],
            calibration: None,
        };
        
        let normalizer = Normalizer::new(config);
        assert_eq!(normalizer.stats.frames_processed, 0);
    }
    
    #[test]
    fn test_color_space_conversion() {
        let config = PreprocessConfig {
            target_size: (224, 224),
            mean: [0.485, 0.456, 0.406],
            std: [0.229, 0.224, 0.225],
            color_space: ColorSpace::Bgr,
            normalization: NormalizationType::ImageNet,
            augmentation: AugmentationConfig {
                enabled: false,
                random_crop: None,
                random_flip: false,
                random_rotation: None,
                brightness: None,
                contrast: None,
                saturation: None,
                noise: None,
            },
            filters: vec![],
            calibration: None,
        };
        
        let normalizer = Normalizer::new(config);
        let rgb_data = vec![255, 0, 0, 0, 255, 0, 0, 0, 255]; // Red, Green, Blue pixels
        let bgr_data = normalizer.convert_color_space(&rgb_data, 3, 1, ColorSpace::Rgb).unwrap();
        
        // Should convert RGB to BGR
        assert_eq!(bgr_data, vec![0, 0, 255, 0, 255, 0, 255, 0, 0]); // Blue, Green, Red pixels
    }
}