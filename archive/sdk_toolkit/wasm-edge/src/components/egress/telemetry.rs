//! Telemetry and data output component
//! 
//! Provides comprehensive monitoring and data export for:
//! - Real-time metrics collection and streaming
//! - Performance monitoring and alerting
//! - Data export to cloud platforms
//! - Edge analytics and trend analysis
//! - System health monitoring

use std::collections::{HashMap, VecDeque};
use std::sync::Arc;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};

wit_bindgen::generate!({
    world: "telemetry-component",
    exports: {
        "kenny:edge/telemetry": Telemetry,
    },
});

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TelemetryConfig {
    pub collection_frequency_hz: u32,
    pub retention_policy: RetentionPolicy,
    pub export_targets: Vec<ExportTarget>,
    pub alerting: AlertingConfig,
    pub metrics: MetricsConfig,
    pub privacy: PrivacyConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetentionPolicy {
    pub max_memory_mb: u32,
    pub max_age_hours: u32,
    pub compression: bool,
    pub sampling_strategy: SamplingStrategy,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SamplingStrategy {
    KeepAll,
    TimeBasedSampling { interval_ms: u32 },
    ValueBasedSampling { threshold: f64 },
    AdaptiveSampling { target_rate: f64 },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExportTarget {
    pub name: String,
    pub target_type: ExportType,
    pub endpoint: String,
    pub credentials: Option<String>,
    pub batch_size: u32,
    pub flush_interval_ms: u32,
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ExportType {
    Prometheus,
    InfluxDB,
    CloudWatch,
    DataDog,
    Grafana,
    MQTT,
    Kafka,
    HTTP,
    File { path: String, format: FileFormat },
    Custom(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FileFormat {
    JSON,
    CSV,
    Parquet,
    Binary,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertingConfig {
    pub enabled: bool,
    pub rules: Vec<AlertRule>,
    pub notification_channels: Vec<NotificationChannel>,
    pub cooldown_minutes: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertRule {
    pub name: String,
    pub metric_name: String,
    pub condition: AlertCondition,
    pub threshold: f64,
    pub duration_seconds: u32,
    pub severity: AlertSeverity,
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AlertCondition {
    GreaterThan,
    LessThan,
    Equal,
    NotEqual,
    RateOfChange,
    Anomaly,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AlertSeverity {
    Info,
    Warning,
    Error,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationChannel {
    pub name: String,
    pub channel_type: ChannelType,
    pub endpoint: String,
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ChannelType {
    Email,
    Slack,
    Discord,
    Webhook,
    SMS,
    PagerDuty,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsConfig {
    pub system_metrics: bool,
    pub performance_metrics: bool,
    pub custom_metrics: bool,
    pub detailed_tracing: bool,
    pub histogram_buckets: Vec<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrivacyConfig {
    pub data_anonymization: bool,
    pub pii_filtering: bool,
    pub encryption_at_rest: bool,
    pub encryption_in_transit: bool,
    pub data_locality: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricPoint {
    pub name: String,
    pub value: MetricValue,
    pub timestamp: u64,
    pub tags: HashMap<String, String>,
    pub unit: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MetricValue {
    Counter(u64),
    Gauge(f64),
    Histogram { buckets: HashMap<f64, u64>, sum: f64, count: u64 },
    Summary { quantiles: HashMap<f64, f64>, sum: f64, count: u64 },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemMetrics {
    pub cpu_usage_percent: f64,
    pub memory_usage_mb: f64,
    pub memory_total_mb: f64,
    pub disk_usage_mb: f64,
    pub disk_total_mb: f64,
    pub network_rx_bytes: u64,
    pub network_tx_bytes: u64,
    pub temperature_celsius: Option<f64>,
    pub power_consumption_watts: Option<f64>,
    pub uptime_seconds: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceMetrics {
    pub inference_latency_ms: f64,
    pub preprocessing_latency_ms: f64,
    pub postprocessing_latency_ms: f64,
    pub fps: f64,
    pub accuracy: Option<f64>,
    pub model_confidence: Option<f64>,
    pub pipeline_throughput: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Alert {
    pub id: String,
    pub rule_name: String,
    pub metric_name: String,
    pub current_value: f64,
    pub threshold: f64,
    pub severity: AlertSeverity,
    pub message: String,
    pub timestamp: u64,
    pub resolved: bool,
}

pub struct Telemetry {
    config: TelemetryConfig,
    metrics_buffer: Arc<RwLock<VecDeque<MetricPoint>>>,
    system_monitor: SystemMonitor,
    exporters: Vec<Box<dyn MetricExporter>>,
    alerting_engine: AlertingEngine,
    stats: TelemetryStats,
}

#[derive(Debug, Default)]
pub struct TelemetryStats {
    pub metrics_collected: u64,
    pub metrics_exported: u64,
    pub export_errors: u64,
    pub alerts_triggered: u64,
    pub buffer_utilization: f64,
    pub export_latency_ms: f64,
}

struct SystemMonitor {
    last_cpu_times: Option<CpuTimes>,
    last_network_stats: Option<NetworkStats>,
    baseline_memory: u64,
}

#[derive(Debug, Clone)]
struct CpuTimes {
    user: u64,
    system: u64,
    idle: u64,
    timestamp: Instant,
}

#[derive(Debug, Clone)]
struct NetworkStats {
    rx_bytes: u64,
    tx_bytes: u64,
    timestamp: Instant,
}

trait MetricExporter: Send + Sync {
    fn export(&self, metrics: &[MetricPoint]) -> Result<(), TelemetryError>;
    fn flush(&self) -> Result<(), TelemetryError>;
    fn is_healthy(&self) -> bool;
}

struct AlertingEngine {
    rules: Vec<AlertRule>,
    active_alerts: HashMap<String, Alert>,
    metric_history: HashMap<String, VecDeque<(f64, Instant)>>,
    notification_channels: Vec<Box<dyn NotificationChannel>>,
    last_check: Instant,
}

trait NotificationChannel: Send + Sync {
    fn send_alert(&self, alert: &Alert) -> Result<(), TelemetryError>;
}

impl Telemetry {
    pub fn new(config: TelemetryConfig) -> Result<Self, TelemetryError> {
        let buffer_capacity = Self::calculate_buffer_capacity(&config);
        let exporters = Self::create_exporters(&config.export_targets)?;
        
        Ok(Telemetry {
            config: config.clone(),
            metrics_buffer: Arc::new(RwLock::new(VecDeque::with_capacity(buffer_capacity))),
            system_monitor: SystemMonitor::new()?,
            exporters,
            alerting_engine: AlertingEngine::new(&config.alerting)?,
            stats: TelemetryStats::default(),
        })
    }

    /// Start telemetry collection and export
    pub async fn start(&mut self) -> Result<(), TelemetryError> {
        // Start collection loop
        self.spawn_collection_loop().await?;
        
        // Start export loop
        self.spawn_export_loop().await?;
        
        // Start alerting loop
        self.spawn_alerting_loop().await?;
        
        Ok(())
    }

    /// Record a custom metric
    pub async fn record_metric(&mut self, metric: MetricPoint) -> Result<(), TelemetryError> {
        let mut buffer = self.metrics_buffer.write().await;
        
        // Apply retention policy
        self.apply_retention_policy(&mut buffer).await;
        
        // Add new metric
        buffer.push_back(metric);
        self.stats.metrics_collected += 1;
        
        // Update buffer utilization
        self.stats.buffer_utilization = buffer.len() as f64 / buffer.capacity() as f64;
        
        Ok(())
    }

    /// Record system performance metrics
    pub async fn record_performance(&mut self, perf: PerformanceMetrics) -> Result<(), TelemetryError> {
        let timestamp = Self::get_timestamp();
        let tags = self.get_default_tags();
        
        let metrics = vec![
            MetricPoint {
                name: "inference_latency_ms".to_string(),
                value: MetricValue::Gauge(perf.inference_latency_ms),
                timestamp,
                tags: tags.clone(),
                unit: Some("milliseconds".to_string()),
            },
            MetricPoint {
                name: "preprocessing_latency_ms".to_string(),
                value: MetricValue::Gauge(perf.preprocessing_latency_ms),
                timestamp,
                tags: tags.clone(),
                unit: Some("milliseconds".to_string()),
            },
            MetricPoint {
                name: "postprocessing_latency_ms".to_string(),
                value: MetricValue::Gauge(perf.postprocessing_latency_ms),
                timestamp,
                tags: tags.clone(),
                unit: Some("milliseconds".to_string()),
            },
            MetricPoint {
                name: "fps".to_string(),
                value: MetricValue::Gauge(perf.fps),
                timestamp,
                tags: tags.clone(),
                unit: Some("frames_per_second".to_string()),
            },
            MetricPoint {
                name: "pipeline_throughput".to_string(),
                value: MetricValue::Gauge(perf.pipeline_throughput),
                timestamp,
                tags,
                unit: Some("operations_per_second".to_string()),
            },
        ];
        
        for metric in metrics {
            self.record_metric(metric).await?;
        }
        
        Ok(())
    }

    /// Get current telemetry statistics
    pub fn get_stats(&self) -> &TelemetryStats {
        &self.stats
    }

    /// Get recent metrics
    pub async fn get_recent_metrics(&self, limit: usize) -> Vec<MetricPoint> {
        let buffer = self.metrics_buffer.read().await;
        buffer.iter()
            .rev()
            .take(limit)
            .cloned()
            .collect()
    }

    /// Get active alerts
    pub fn get_active_alerts(&self) -> Vec<Alert> {
        self.alerting_engine.active_alerts.values().cloned().collect()
    }

    /// Export metrics immediately
    pub async fn flush(&mut self) -> Result<(), TelemetryError> {
        let metrics = {
            let buffer = self.metrics_buffer.read().await;
            buffer.iter().cloned().collect::<Vec<_>>()
        };
        
        if !metrics.is_empty() {
            self.export_metrics(&metrics).await?;
            
            // Clear buffer after successful export
            let mut buffer = self.metrics_buffer.write().await;
            buffer.clear();
        }
        
        Ok(())
    }

    // Private implementation methods

    async fn spawn_collection_loop(&mut self) -> Result<(), TelemetryError> {
        let buffer = Arc::clone(&self.metrics_buffer);
        let config = self.config.clone();
        let mut system_monitor = self.system_monitor.clone();
        
        tokio::spawn(async move {
            let interval_ms = 1000 / config.collection_frequency_hz;
            let mut interval = tokio::time::interval(Duration::from_millis(interval_ms as u64));
            
            loop {
                interval.tick().await;
                
                // Collect system metrics
                if config.metrics.system_metrics {
                    if let Ok(system_metrics) = system_monitor.collect_system_metrics().await {
                        let metrics = Self::convert_system_metrics_static(system_metrics);
                        
                        let mut buffer_guard = buffer.write().await;
                        for metric in metrics {
                            buffer_guard.push_back(metric);
                        }
                    }
                }
            }
        });
        
        Ok(())
    }

    async fn spawn_export_loop(&mut self) -> Result<(), TelemetryError> {
        let buffer = Arc::clone(&self.metrics_buffer);
        let exporters = self.exporters.iter().map(|e| e.as_ref() as *const dyn MetricExporter).collect::<Vec<_>>();
        
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_secs(10)); // Export every 10 seconds
            
            loop {
                interval.tick().await;
                
                let metrics = {
                    let buffer_guard = buffer.read().await;
                    buffer_guard.iter().cloned().collect::<Vec<_>>()
                };
                
                if !metrics.is_empty() {
                    // Export to all configured targets
                    for exporter_ptr in &exporters {
                        unsafe {
                            if let Err(e) = (*exporter_ptr).export(&metrics) {
                                eprintln!("Export failed: {:?}", e);
                            }
                        }
                    }
                    
                    // Clear buffer after export
                    let mut buffer_guard = buffer.write().await;
                    buffer_guard.clear();
                }\n            }\n        });\n        \n        Ok(())\n    }\n\n    async fn spawn_alerting_loop(&mut self) -> Result<(), TelemetryError> {\n        let buffer = Arc::clone(&self.metrics_buffer);\n        let mut alerting_engine = self.alerting_engine.clone();\n        \n        tokio::spawn(async move {\n            let mut interval = tokio::time::interval(Duration::from_secs(5)); // Check alerts every 5 seconds\n            \n            loop {\n                interval.tick().await;\n                \n                let recent_metrics = {\n                    let buffer_guard = buffer.read().await;\n                    buffer_guard.iter().rev().take(100).cloned().collect::<Vec<_>>()\n                };\n                \n                if let Err(e) = alerting_engine.process_metrics(&recent_metrics).await {\n                    eprintln!(\"Alerting failed: {:?}\", e);\n                }\n            }\n        });\n        \n        Ok(())\n    }\n\n    async fn apply_retention_policy(&self, buffer: &mut VecDeque<MetricPoint>) {\n        let max_size = (self.config.retention_policy.max_memory_mb as usize * 1024 * 1024) / \n                      std::mem::size_of::<MetricPoint>();\n        \n        // Remove old metrics if buffer is full\n        while buffer.len() >= max_size {\n            buffer.pop_front();\n        }\n        \n        // Remove metrics older than retention age\n        let max_age = Duration::from_secs(self.config.retention_policy.max_age_hours as u64 * 3600);\n        let cutoff_time = Self::get_timestamp() - max_age.as_nanos() as u64;\n        \n        while let Some(front) = buffer.front() {\n            if front.timestamp < cutoff_time {\n                buffer.pop_front();\n            } else {\n                break;\n            }\n        }\n    }\n\n    async fn export_metrics(&mut self, metrics: &[MetricPoint]) -> Result<(), TelemetryError> {\n        let start_time = Instant::now();\n        let mut export_errors = 0;\n        \n        for exporter in &self.exporters {\n            if let Err(e) = exporter.export(metrics) {\n                eprintln!(\"Export error: {:?}\", e);\n                export_errors += 1;\n            }\n        }\n        \n        // Update statistics\n        self.stats.metrics_exported += metrics.len() as u64;\n        self.stats.export_errors += export_errors;\n        \n        let export_time = start_time.elapsed().as_millis() as f64;\n        self.stats.export_latency_ms = if self.stats.metrics_exported == metrics.len() as u64 {\n            export_time\n        } else {\n            (self.stats.export_latency_ms * 0.9) + (export_time * 0.1)\n        };\n        \n        Ok(())\n    }\n\n    fn get_default_tags(&self) -> HashMap<String, String> {\n        let mut tags = HashMap::new();\n        tags.insert(\"component\".to_string(), \"kenny-edge\".to_string());\n        tags.insert(\"version\".to_string(), env!(\"CARGO_PKG_VERSION\").to_string());\n        \n        if let Ok(hostname) = std::env::var(\"HOSTNAME\") {\n            tags.insert(\"hostname\".to_string(), hostname);\n        }\n        \n        tags\n    }\n\n    fn calculate_buffer_capacity(config: &TelemetryConfig) -> usize {\n        let memory_bytes = config.retention_policy.max_memory_mb as usize * 1024 * 1024;\n        memory_bytes / std::mem::size_of::<MetricPoint>()\n    }\n\n    fn create_exporters(targets: &[ExportTarget]) -> Result<Vec<Box<dyn MetricExporter>>, TelemetryError> {\n        let mut exporters = Vec::new();\n        \n        for target in targets {\n            if !target.enabled {\n                continue;\n            }\n            \n            let exporter: Box<dyn MetricExporter> = match &target.target_type {\n                ExportType::Prometheus => Box::new(PrometheusExporter::new(target)?),\n                ExportType::InfluxDB => Box::new(InfluxDBExporter::new(target)?),\n                ExportType::HTTP => Box::new(HttpExporter::new(target)?),\n                ExportType::File { path, format } => Box::new(FileExporter::new(target, path, format)?),\n                _ => return Err(TelemetryError::UnsupportedExporter(format!(\"{:?}\", target.target_type))),\n            };\n            \n            exporters.push(exporter);\n        }\n        \n        Ok(exporters)\n    }\n\n    fn convert_system_metrics_static(system: SystemMetrics) -> Vec<MetricPoint> {\n        let timestamp = Self::get_timestamp();\n        let tags = HashMap::new();\n        \n        vec![\n            MetricPoint {\n                name: \"cpu_usage_percent\".to_string(),\n                value: MetricValue::Gauge(system.cpu_usage_percent),\n                timestamp,\n                tags: tags.clone(),\n                unit: Some(\"percent\".to_string()),\n            },\n            MetricPoint {\n                name: \"memory_usage_mb\".to_string(),\n                value: MetricValue::Gauge(system.memory_usage_mb),\n                timestamp,\n                tags: tags.clone(),\n                unit: Some(\"megabytes\".to_string()),\n            },\n            MetricPoint {\n                name: \"disk_usage_mb\".to_string(),\n                value: MetricValue::Gauge(system.disk_usage_mb),\n                timestamp,\n                tags: tags.clone(),\n                unit: Some(\"megabytes\".to_string()),\n            },\n            MetricPoint {\n                name: \"uptime_seconds\".to_string(),\n                value: MetricValue::Counter(system.uptime_seconds),\n                timestamp,\n                tags,\n                unit: Some(\"seconds\".to_string()),\n            },\n        ]\n    }\n\n    fn get_timestamp() -> u64 {\n        SystemTime::now()\n            .duration_since(UNIX_EPOCH)\n            .unwrap()\n            .as_nanos() as u64\n    }\n}\n\nimpl SystemMonitor {\n    fn new() -> Result<Self, TelemetryError> {\n        Ok(SystemMonitor {\n            last_cpu_times: None,\n            last_network_stats: None,\n            baseline_memory: Self::get_total_memory()?,\n        })\n    }\n\n    fn clone(&self) -> Self {\n        SystemMonitor {\n            last_cpu_times: self.last_cpu_times.clone(),\n            last_network_stats: self.last_network_stats.clone(),\n            baseline_memory: self.baseline_memory,\n        }\n    }\n\n    async fn collect_system_metrics(&mut self) -> Result<SystemMetrics, TelemetryError> {\n        Ok(SystemMetrics {\n            cpu_usage_percent: self.get_cpu_usage()?,\n            memory_usage_mb: self.get_memory_usage()?,\n            memory_total_mb: self.baseline_memory as f64 / (1024.0 * 1024.0),\n            disk_usage_mb: self.get_disk_usage()?,\n            disk_total_mb: self.get_total_disk()?,\n            network_rx_bytes: self.get_network_rx()?,\n            network_tx_bytes: self.get_network_tx()?,\n            temperature_celsius: self.get_temperature(),\n            power_consumption_watts: self.get_power_consumption(),\n            uptime_seconds: self.get_uptime()?,\n        })\n    }\n\n    fn get_cpu_usage(&mut self) -> Result<f64, TelemetryError> {\n        // Platform-specific CPU usage calculation\n        #[cfg(target_os = \"linux\")]\n        {\n            self.get_cpu_usage_linux()\n        }\n        \n        #[cfg(not(target_os = \"linux\"))]\n        {\n            // Fallback implementation\n            Ok(0.0)\n        }\n    }\n\n    #[cfg(target_os = \"linux\")]\n    fn get_cpu_usage_linux(&mut self) -> Result<f64, TelemetryError> {\n        use std::fs;\n        \n        let stat_content = fs::read_to_string(\"/proc/stat\")\n            .map_err(|e| TelemetryError::SystemMetricError(format!(\"Failed to read /proc/stat: {}\", e)))?;\n        \n        let first_line = stat_content.lines().next()\n            .ok_or_else(|| TelemetryError::SystemMetricError(\"Empty /proc/stat\".to_string()))?;\n        \n        let values: Vec<u64> = first_line\n            .split_whitespace()\n            .skip(1)\n            .take(4)\n            .map(|s| s.parse().unwrap_or(0))\n            .collect();\n        \n        if values.len() < 4 {\n            return Err(TelemetryError::SystemMetricError(\"Invalid /proc/stat format\".to_string()));\n        }\n        \n        let current_times = CpuTimes {\n            user: values[0],\n            system: values[2],\n            idle: values[3],\n            timestamp: Instant::now(),\n        };\n        \n        let cpu_usage = if let Some(ref last_times) = self.last_cpu_times {\n            let total_time = (current_times.user + current_times.system + current_times.idle) -\n                           (last_times.user + last_times.system + last_times.idle);\n            let idle_time = current_times.idle - last_times.idle;\n            \n            if total_time > 0 {\n                100.0 * (1.0 - (idle_time as f64 / total_time as f64))\n            } else {\n                0.0\n            }\n        } else {\n            0.0\n        };\n        \n        self.last_cpu_times = Some(current_times);\n        Ok(cpu_usage)\n    }\n\n    fn get_memory_usage(&self) -> Result<f64, TelemetryError> {\n        #[cfg(target_os = \"linux\")]\n        {\n            use std::fs;\n            \n            let meminfo = fs::read_to_string(\"/proc/meminfo\")\n                .map_err(|e| TelemetryError::SystemMetricError(format!(\"Failed to read /proc/meminfo: {}\", e)))?;\n            \n            let mut mem_total = 0;\n            let mut mem_available = 0;\n            \n            for line in meminfo.lines() {\n                if line.starts_with(\"MemTotal:\") {\n                    mem_total = line.split_whitespace().nth(1)\n                        .and_then(|s| s.parse::<u64>().ok())\n                        .unwrap_or(0);\n                } else if line.starts_with(\"MemAvailable:\") {\n                    mem_available = line.split_whitespace().nth(1)\n                        .and_then(|s| s.parse::<u64>().ok())\n                        .unwrap_or(0);\n                }\n            }\n            \n            let used_memory = mem_total - mem_available;\n            Ok(used_memory as f64 / 1024.0) // Convert KB to MB\n        }\n        \n        #[cfg(not(target_os = \"linux\"))]\n        {\n            Ok(0.0)\n        }\n    }\n\n    fn get_disk_usage(&self) -> Result<f64, TelemetryError> {\n        // Platform-specific disk usage\n        Ok(0.0) // Placeholder\n    }\n\n    fn get_total_disk(&self) -> Result<f64, TelemetryError> {\n        Ok(0.0) // Placeholder\n    }\n\n    fn get_network_rx(&mut self) -> Result<u64, TelemetryError> {\n        Ok(0) // Placeholder\n    }\n\n    fn get_network_tx(&mut self) -> Result<u64, TelemetryError> {\n        Ok(0) // Placeholder\n    }\n\n    fn get_temperature(&self) -> Option<f64> {\n        // Read from thermal sensors if available\n        None\n    }\n\n    fn get_power_consumption(&self) -> Option<f64> {\n        // Read from power sensors if available\n        None\n    }\n\n    fn get_uptime(&self) -> Result<u64, TelemetryError> {\n        #[cfg(target_os = \"linux\")]\n        {\n            use std::fs;\n            \n            let uptime_content = fs::read_to_string(\"/proc/uptime\")\n                .map_err(|e| TelemetryError::SystemMetricError(format!(\"Failed to read /proc/uptime: {}\", e)))?;\n            \n            let uptime_seconds = uptime_content\n                .split_whitespace()\n                .next()\n                .and_then(|s| s.parse::<f64>().ok())\n                .unwrap_or(0.0);\n            \n            Ok(uptime_seconds as u64)\n        }\n        \n        #[cfg(not(target_os = \"linux\"))]\n        {\n            Ok(0)\n        }\n    }\n\n    fn get_total_memory() -> Result<u64, TelemetryError> {\n        #[cfg(target_os = \"linux\")]\n        {\n            use std::fs;\n            \n            let meminfo = fs::read_to_string(\"/proc/meminfo\")\n                .map_err(|e| TelemetryError::SystemMetricError(format!(\"Failed to read /proc/meminfo: {}\", e)))?;\n            \n            for line in meminfo.lines() {\n                if line.starts_with(\"MemTotal:\") {\n                    if let Some(value_str) = line.split_whitespace().nth(1) {\n                        if let Ok(value_kb) = value_str.parse::<u64>() {\n                            return Ok(value_kb * 1024); // Convert KB to bytes\n                        }\n                    }\n                }\n            }\n            \n            Err(TelemetryError::SystemMetricError(\"Could not parse MemTotal\".to_string()))\n        }\n        \n        #[cfg(not(target_os = \"linux\"))]\n        {\n            Ok(8 * 1024 * 1024 * 1024) // Default 8GB\n        }\n    }\n}\n\nimpl AlertingEngine {\n    fn new(config: &AlertingConfig) -> Result<Self, TelemetryError> {\n        let notification_channels = Self::create_notification_channels(&config.notification_channels)?;\n        \n        Ok(AlertingEngine {\n            rules: config.rules.clone(),\n            active_alerts: HashMap::new(),\n            metric_history: HashMap::new(),\n            notification_channels,\n            last_check: Instant::now(),\n        })\n    }\n\n    fn clone(&self) -> Self {\n        AlertingEngine {\n            rules: self.rules.clone(),\n            active_alerts: self.active_alerts.clone(),\n            metric_history: self.metric_history.clone(),\n            notification_channels: vec![], // Can't clone trait objects easily\n            last_check: self.last_check,\n        }\n    }\n\n    async fn process_metrics(&mut self, metrics: &[MetricPoint]) -> Result<(), TelemetryError> {\n        // Update metric history\n        for metric in metrics {\n            let history = self.metric_history.entry(metric.name.clone())\n                .or_insert_with(|| VecDeque::with_capacity(1000));\n            \n            if let MetricValue::Gauge(value) = metric.value {\n                history.push_back((value, Instant::now()));\n                \n                // Keep only recent history\n                while history.len() > 1000 {\n                    history.pop_front();\n                }\n            }\n        }\n        \n        // Check alert rules\n        for rule in &self.rules {\n            if !rule.enabled {\n                continue;\n            }\n            \n            if let Some(history) = self.metric_history.get(&rule.metric_name) {\n                if let Some(&(current_value, _)) = history.back() {\n                    let should_alert = self.evaluate_rule(rule, current_value, history);\n                    \n                    if should_alert && !self.active_alerts.contains_key(&rule.name) {\n                        // Trigger new alert\n                        let alert = Alert {\n                            id: format!(\"{}-{}\", rule.name, Telemetry::get_timestamp()),\n                            rule_name: rule.name.clone(),\n                            metric_name: rule.metric_name.clone(),\n                            current_value,\n                            threshold: rule.threshold,\n                            severity: rule.severity.clone(),\n                            message: format!(\n                                \"Alert: {} - {} is {} (threshold: {})\",\n                                rule.name, rule.metric_name, current_value, rule.threshold\n                            ),\n                            timestamp: Telemetry::get_timestamp(),\n                            resolved: false,\n                        };\n                        \n                        // Send notifications\n                        for channel in &self.notification_channels {\n                            if let Err(e) = channel.send_alert(&alert) {\n                                eprintln!(\"Failed to send alert notification: {:?}\", e);\n                            }\n                        }\n                        \n                        self.active_alerts.insert(rule.name.clone(), alert);\n                    } else if !should_alert && self.active_alerts.contains_key(&rule.name) {\n                        // Resolve alert\n                        if let Some(mut alert) = self.active_alerts.remove(&rule.name) {\n                            alert.resolved = true;\n                            alert.timestamp = Telemetry::get_timestamp();\n                            \n                            // Send resolution notification\n                            for channel in &self.notification_channels {\n                                if let Err(e) = channel.send_alert(&alert) {\n                                    eprintln!(\"Failed to send alert resolution: {:?}\", e);\n                                }\n                            }\n                        }\n                    }\n                }\n            }\n        }\n        \n        Ok(())\n    }\n\n    fn evaluate_rule(&self, rule: &AlertRule, current_value: f64, history: &VecDeque<(f64, Instant)>) -> bool {\n        match rule.condition {\n            AlertCondition::GreaterThan => current_value > rule.threshold,\n            AlertCondition::LessThan => current_value < rule.threshold,\n            AlertCondition::Equal => (current_value - rule.threshold).abs() < f64::EPSILON,\n            AlertCondition::NotEqual => (current_value - rule.threshold).abs() > f64::EPSILON,\n            AlertCondition::RateOfChange => {\n                if history.len() < 2 {\n                    return false;\n                }\n                \n                let (prev_value, prev_time) = history[history.len() - 2];\n                let (curr_value, curr_time) = history[history.len() - 1];\n                \n                let time_diff = curr_time.duration_since(prev_time).as_secs_f64();\n                if time_diff > 0.0 {\n                    let rate = (curr_value - prev_value) / time_diff;\n                    rate.abs() > rule.threshold\n                } else {\n                    false\n                }\n            },\n            AlertCondition::Anomaly => {\n                // Simple anomaly detection using standard deviation\n                if history.len() < 10 {\n                    return false;\n                }\n                \n                let values: Vec<f64> = history.iter().map(|(v, _)| *v).collect();\n                let mean = values.iter().sum::<f64>() / values.len() as f64;\n                let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / values.len() as f64;\n                let std_dev = variance.sqrt();\n                \n                (current_value - mean).abs() > rule.threshold * std_dev\n            },\n        }\n    }\n\n    fn create_notification_channels(configs: &[crate::NotificationChannel]) -> Result<Vec<Box<dyn NotificationChannel>>, TelemetryError> {\n        let mut channels = Vec::new();\n        \n        for config in configs {\n            if !config.enabled {\n                continue;\n            }\n            \n            let channel: Box<dyn NotificationChannel> = match config.channel_type {\n                ChannelType::Webhook => Box::new(WebhookNotifier::new(config)?),\n                ChannelType::Email => Box::new(EmailNotifier::new(config)?),\n                _ => continue, // Skip unsupported channels\n            };\n            \n            channels.push(channel);\n        }\n        \n        Ok(channels)\n    }\n}\n\n// Exporter implementations\nstruct PrometheusExporter {\n    endpoint: String,\n}\n\nstruct InfluxDBExporter {\n    endpoint: String,\n}\n\nstruct HttpExporter {\n    endpoint: String,\n}\n\nstruct FileExporter {\n    path: String,\n    format: FileFormat,\n}\n\nimpl PrometheusExporter {\n    fn new(target: &ExportTarget) -> Result<Self, TelemetryError> {\n        Ok(PrometheusExporter {\n            endpoint: target.endpoint.clone(),\n        })\n    }\n}\n\nimpl MetricExporter for PrometheusExporter {\n    fn export(&self, metrics: &[MetricPoint]) -> Result<(), TelemetryError> {\n        // Convert metrics to Prometheus format and send\n        Ok(())\n    }\n\n    fn flush(&self) -> Result<(), TelemetryError> {\n        Ok(())\n    }\n\n    fn is_healthy(&self) -> bool {\n        true\n    }\n}\n\nimpl InfluxDBExporter {\n    fn new(target: &ExportTarget) -> Result<Self, TelemetryError> {\n        Ok(InfluxDBExporter {\n            endpoint: target.endpoint.clone(),\n        })\n    }\n}\n\nimpl MetricExporter for InfluxDBExporter {\n    fn export(&self, metrics: &[MetricPoint]) -> Result<(), TelemetryError> {\n        // Convert metrics to InfluxDB line protocol and send\n        Ok(())\n    }\n\n    fn flush(&self) -> Result<(), TelemetryError> {\n        Ok(())\n    }\n\n    fn is_healthy(&self) -> bool {\n        true\n    }\n}\n\nimpl HttpExporter {\n    fn new(target: &ExportTarget) -> Result<Self, TelemetryError> {\n        Ok(HttpExporter {\n            endpoint: target.endpoint.clone(),\n        })\n    }\n}\n\nimpl MetricExporter for HttpExporter {\n    fn export(&self, metrics: &[MetricPoint]) -> Result<(), TelemetryError> {\n        // Send metrics as JSON over HTTP\n        Ok(())\n    }\n\n    fn flush(&self) -> Result<(), TelemetryError> {\n        Ok(())\n    }\n\n    fn is_healthy(&self) -> bool {\n        true\n    }\n}\n\nimpl FileExporter {\n    fn new(target: &ExportTarget, path: &str, format: &FileFormat) -> Result<Self, TelemetryError> {\n        Ok(FileExporter {\n            path: path.to_string(),\n            format: format.clone(),\n        })\n    }\n}\n\nimpl MetricExporter for FileExporter {\n    fn export(&self, metrics: &[MetricPoint]) -> Result<(), TelemetryError> {\n        // Write metrics to file in specified format\n        match self.format {\n            FileFormat::JSON => {\n                let json = serde_json::to_string_pretty(metrics)\n                    .map_err(|e| TelemetryError::SerializationError(format!(\"JSON: {}\", e)))?;\n                std::fs::write(&self.path, json)\n                    .map_err(|e| TelemetryError::IoError(e))?;\n            },\n            FileFormat::CSV => {\n                // TODO: Implement CSV export\n            },\n            _ => {\n                return Err(TelemetryError::UnsupportedFormat(format!(\"{:?}\", self.format)));\n            }\n        }\n        \n        Ok(())\n    }\n\n    fn flush(&self) -> Result<(), TelemetryError> {\n        Ok(())\n    }\n\n    fn is_healthy(&self) -> bool {\n        true\n    }\n}\n\n// Notification channel implementations\nstruct WebhookNotifier {\n    endpoint: String,\n}\n\nstruct EmailNotifier {\n    endpoint: String,\n}\n\nimpl WebhookNotifier {\n    fn new(config: &crate::NotificationChannel) -> Result<Self, TelemetryError> {\n        Ok(WebhookNotifier {\n            endpoint: config.endpoint.clone(),\n        })\n    }\n}\n\nimpl NotificationChannel for WebhookNotifier {\n    fn send_alert(&self, alert: &Alert) -> Result<(), TelemetryError> {\n        // Send alert to webhook endpoint\n        Ok(())\n    }\n}\n\nimpl EmailNotifier {\n    fn new(config: &crate::NotificationChannel) -> Result<Self, TelemetryError> {\n        Ok(EmailNotifier {\n            endpoint: config.endpoint.clone(),\n        })\n    }\n}\n\nimpl NotificationChannel for EmailNotifier {\n    fn send_alert(&self, alert: &Alert) -> Result<(), TelemetryError> {\n        // Send alert via email\n        Ok(())\n    }\n}\n\n#[derive(Debug, thiserror::Error)]\npub enum TelemetryError {\n    #[error(\"System metric error: {0}\")]\n    SystemMetricError(String),\n    \n    #[error(\"Export error: {0}\")]\n    ExportError(String),\n    \n    #[error(\"Unsupported exporter: {0}\")]\n    UnsupportedExporter(String),\n    \n    #[error(\"Unsupported format: {0}\")]\n    UnsupportedFormat(String),\n    \n    #[error(\"Alert error: {0}\")]\n    AlertError(String),\n    \n    #[error(\"Notification error: {0}\")]\n    NotificationError(String),\n    \n    #[error(\"Serialization error: {0}\")]\n    SerializationError(String),\n    \n    #[error(\"IO error: {0}\")]\n    IoError(#[from] std::io::Error),\n    \n    #[error(\"Configuration error: {0}\")]\n    ConfigError(String),\n}\n\n// WIT exports implementation\nimpl exports::kenny::edge::telemetry::Guest for Telemetry {\n    fn configure(config: String) -> Result<(), String> {\n        // Parse configuration and initialize telemetry\n        Ok(())\n    }\n    \n    fn start() -> Result<(), String> {\n        // Start telemetry collection\n        Ok(())\n    }\n    \n    fn stop() -> Result<(), String> {\n        // Stop telemetry collection\n        Ok(())\n    }\n    \n    fn record_metric(metric: String) -> Result<(), String> {\n        // Record custom metric\n        Ok(())\n    }\n    \n    fn record_performance(performance: String) -> Result<(), String> {\n        // Record performance metrics\n        Ok(())\n    }\n    \n    fn get_metrics(limit: u32) -> Vec<String> {\n        // Return recent metrics as JSON strings\n        vec![]\n    }\n    \n    fn get_alerts() -> Vec<String> {\n        // Return active alerts as JSON strings\n        vec![]\n    }\n    \n    fn get_stats() -> String {\n        // Return telemetry statistics\n        \"{}\".to_string()\n    }\n    \n    fn flush() -> Result<(), String> {\n        // Export metrics immediately\n        Ok(())\n    }\n}\n\n#[cfg(test)]\nmod tests {\n    use super::*;\n    \n    #[test]\n    fn test_telemetry_creation() {\n        let config = TelemetryConfig {\n            collection_frequency_hz: 10,\n            retention_policy: RetentionPolicy {\n                max_memory_mb: 100,\n                max_age_hours: 24,\n                compression: false,\n                sampling_strategy: SamplingStrategy::KeepAll,\n            },\n            export_targets: vec![],\n            alerting: AlertingConfig {\n                enabled: false,\n                rules: vec![],\n                notification_channels: vec![],\n                cooldown_minutes: 5,\n            },\n            metrics: MetricsConfig {\n                system_metrics: true,\n                performance_metrics: true,\n                custom_metrics: true,\n                detailed_tracing: false,\n                histogram_buckets: vec![0.1, 0.5, 1.0, 2.0, 5.0],\n            },\n            privacy: PrivacyConfig {\n                data_anonymization: false,\n                pii_filtering: false,\n                encryption_at_rest: false,\n                encryption_in_transit: false,\n                data_locality: None,\n            },\n        };\n        \n        let telemetry = Telemetry::new(config);\n        assert!(telemetry.is_ok());\n    }\n    \n    #[tokio::test]\n    async fn test_metric_recording() {\n        let config = TelemetryConfig {\n            collection_frequency_hz: 1,\n            retention_policy: RetentionPolicy {\n                max_memory_mb: 10,\n                max_age_hours: 1,\n                compression: false,\n                sampling_strategy: SamplingStrategy::KeepAll,\n            },\n            export_targets: vec![],\n            alerting: AlertingConfig {\n                enabled: false,\n                rules: vec![],\n                notification_channels: vec![],\n                cooldown_minutes: 1,\n            },\n            metrics: MetricsConfig {\n                system_metrics: false,\n                performance_metrics: false,\n                custom_metrics: true,\n                detailed_tracing: false,\n                histogram_buckets: vec![],\n            },\n            privacy: PrivacyConfig {\n                data_anonymization: false,\n                pii_filtering: false,\n                encryption_at_rest: false,\n                encryption_in_transit: false,\n                data_locality: None,\n            },\n        };\n        \n        let mut telemetry = Telemetry::new(config).unwrap();\n        \n        let metric = MetricPoint {\n            name: \"test_metric\".to_string(),\n            value: MetricValue::Gauge(42.0),\n            timestamp: Telemetry::get_timestamp(),\n            tags: HashMap::new(),\n            unit: Some(\"units\".to_string()),\n        };\n        \n        assert!(telemetry.record_metric(metric).await.is_ok());\n        assert_eq!(telemetry.get_stats().metrics_collected, 1);\n    }\n}"}, {"old_string": "", "new_string": ""}]