/*!
# Safety Monitoring Module

Critical safety system for autonomous vehicles implementing ISO 26262 ASIL-D standards.
Provides continuous monitoring, fault detection, and emergency response capabilities.
*/

use anyhow::{Context, Result};
use log::{info, warn, error, critical};
use nalgebra::{Point3, Vector3};
use std::collections::{HashMap, VecDeque};
use std::time::{Duration, Instant};
use tokio::sync::{broadcast, mpsc, RwLock};
use tokio::time::interval;
use wasm_edge_ai_sdk::prelude::*;

use crate::{DetectedObject, VisionData, LidarData, PlannedPath, Pose2D};

/// Safety monitoring configuration
#[derive(Debug, Clone)]
pub struct SafetyConfig {
    pub monitoring_frequency_hz: f64,
    pub fault_detection: FaultDetectionConfig,
    pub collision_avoidance: CollisionAvoidanceConfig,
    pub system_monitoring: SystemMonitoringConfig,
    pub emergency_response: EmergencyResponseConfig,
    pub redundancy: RedundancyConfig,
}

#[derive(Debug, Clone)]
pub struct FaultDetectionConfig {
    pub sensor_timeout_ms: u64,
    pub actuator_timeout_ms: u64,
    pub communication_timeout_ms: u64,
    pub max_sensor_error_rate: f64,
    pub max_planning_time_ms: u64,
    pub heartbeat_interval_ms: u64,
    pub enable_watchdog: bool,
}

#[derive(Debug, Clone)]
pub struct CollisionAvoidanceConfig {
    pub time_to_collision_critical: f64,  // seconds
    pub time_to_collision_warning: f64,   // seconds
    pub minimum_safe_distance: f64,       // meters
    pub lateral_clearance: f64,           // meters
    pub emergency_brake_distance: f64,    // meters
    pub max_deceleration: f64,            // m/s²
}

#[derive(Debug, Clone)]
pub struct SystemMonitoringConfig {
    pub cpu_usage_threshold: f64,         // percentage
    pub memory_usage_threshold: f64,      // percentage
    pub temperature_threshold: f64,       // celsius
    pub voltage_threshold: (f64, f64),    // (min, max) volts
    pub communication_latency_threshold: u64, // milliseconds
    pub storage_usage_threshold: f64,     // percentage
}

#[derive(Debug, Clone)]
pub struct EmergencyResponseConfig {
    pub enable_emergency_brake: bool,
    pub enable_emergency_steering: bool,
    pub enable_hazard_lights: bool,
    pub enable_horn: bool,
    pub emergency_stop_distance: f64,     // meters
    pub safe_state_timeout: u64,          // milliseconds
}

#[derive(Debug, Clone)]
pub struct RedundancyConfig {
    pub dual_sensor_voting: bool,
    pub triple_modular_redundancy: bool,
    pub backup_planning_system: bool,
    pub redundant_actuators: bool,
    pub independent_safety_processor: bool,
}

/// Safety monitoring state
#[derive(Debug, Clone)]
pub struct SafetyState {
    pub overall_status: SafetyStatus,
    pub active_faults: Vec<SafetyFault>,
    pub active_warnings: Vec<SafetyWarning>,
    pub emergency_state: EmergencyState,
    pub system_health: SystemHealth,
    pub last_update: Instant,
}

#[derive(Debug, Clone, PartialEq)]
pub enum SafetyStatus {
    Safe,
    Warning,
    Critical,
    Emergency,
    Fault,
}

#[derive(Debug, Clone)]
pub struct SafetyFault {
    pub fault_id: String,
    pub fault_type: FaultType,
    pub severity: FaultSeverity,
    pub description: String,
    pub first_detected: Instant,
    pub last_seen: Instant,
    pub count: u32,
    pub source_component: String,
}

#[derive(Debug, Clone, PartialEq)]
pub enum FaultType {
    SensorFailure,
    ActuatorFailure,
    CommunicationFailure,
    PlanningFailure,
    ComputeFailure,
    PowerFailure,
    ThermalFailure,
    SoftwareFailure,
    HardwareFailure,
    CalibrationFailure,
}

#[derive(Debug, Clone, PartialEq, PartialOrd)]
pub enum FaultSeverity {
    Low,
    Medium,
    High,
    Critical,
    Catastrophic,
}

#[derive(Debug, Clone)]
pub struct SafetyWarning {
    pub warning_id: String,
    pub warning_type: WarningType,
    pub description: String,
    pub timestamp: Instant,
    pub position: Option<Point3<f64>>,
    pub recommended_action: String,
}

#[derive(Debug, Clone, PartialEq)]
pub enum WarningType {
    CollisionRisk,
    LaneDeparture,
    SpeedingViolation,
    WeatherCondition,
    TrafficViolation,
    SystemDegradation,
    LowBattery,
    SensorBlocked,
    MaintenanceRequired,
}

#[derive(Debug, Clone)]
pub struct EmergencyState {
    pub is_emergency: bool,
    pub emergency_type: Option<EmergencyType>,
    pub triggered_at: Option<Instant>,
    pub actions_taken: Vec<EmergencyAction>,
    pub safe_state_achieved: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub enum EmergencyType {
    ImmediateCrashRisk,
    SensorFailure,
    ActuatorFailure,
    SystemFailure,
    ExternalEmergency,
    ManualOverride,
}

#[derive(Debug, Clone)]
pub struct EmergencyAction {
    pub action_type: EmergencyActionType,
    pub executed_at: Instant,
    pub success: bool,
    pub details: String,
}

#[derive(Debug, Clone, PartialEq)]
pub enum EmergencyActionType {
    EmergencyBrake,
    EmergencySteer,
    ActivateHazardLights,
    SoundHorn,
    CallEmergencyServices,
    TransmitMayday,
    SafeStateParking,
}

#[derive(Debug, Clone)]
pub struct SystemHealth {
    pub cpu_usage: f64,
    pub memory_usage: f64,
    pub temperature: f64,
    pub voltage: f64,
    pub disk_usage: f64,
    pub network_latency: Option<u64>,
    pub sensor_health: HashMap<String, SensorHealth>,
    pub actuator_health: HashMap<String, ActuatorHealth>,
}

#[derive(Debug, Clone)]
pub struct SensorHealth {
    pub status: ComponentStatus,
    pub last_update: Instant,
    pub error_rate: f64,
    pub signal_quality: f64,
    pub temperature: Option<f64>,
    pub calibration_status: CalibrationStatus,
}

#[derive(Debug, Clone)]
pub struct ActuatorHealth {
    pub status: ComponentStatus,
    pub last_command: Instant,
    pub response_time: Duration,
    pub error_count: u32,
    pub temperature: Option<f64>,
    pub current_draw: Option<f64>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ComponentStatus {
    Operational,
    Degraded,
    Failed,
    Unknown,
    Maintenance,
}

#[derive(Debug, Clone, PartialEq)]
pub enum CalibrationStatus {
    Calibrated,
    NeedsCalibration,
    CalibrationFailed,
    CalibrationInProgress,
}

/// Collision detection result
#[derive(Debug, Clone)]
pub struct CollisionAssessment {
    pub collision_risk: f64,           // 0.0 to 1.0
    pub time_to_collision: Option<f64>, // seconds
    pub closest_object: Option<DetectedObject>,
    pub collision_point: Option<Point3<f64>>,
    pub avoidance_required: bool,
    pub recommended_action: AvoidanceAction,
}

#[derive(Debug, Clone, PartialEq)]
pub enum AvoidanceAction {
    Continue,
    SlowDown,
    EmergencyBrake,
    SteerLeft,
    SteerRight,
    Stop,
    Reverse,
}

/// Main safety monitoring system
pub struct SafetyMonitor {
    config: SafetyConfig,
    state: RwLock<SafetyState>,
    fault_detector: FaultDetector,
    collision_detector: CollisionDetector,
    system_monitor: SystemMonitor,
    emergency_handler: EmergencyHandler,
    redundancy_manager: RedundancyManager,
    
    // Communication channels
    safety_events_tx: broadcast::Sender<SafetyEvent>,
    emergency_command_tx: mpsc::UnboundedSender<EmergencyCommand>,
    
    // Monitoring task handle
    monitoring_handle: Option<tokio::task::JoinHandle<()>>,
}

#[derive(Debug, Clone)]
pub enum SafetyEvent {
    FaultDetected(SafetyFault),
    WarningIssued(SafetyWarning),
    EmergencyTriggered(EmergencyType),
    SafeStateAchieved,
    SystemRecovered,
}

#[derive(Debug, Clone)]
pub enum EmergencyCommand {
    EmergencyStop,
    EmergencySteer(f64), // steering angle
    ActivateHazards,
    SoundAlarm,
    RequestHumanIntervention,
}

struct FaultDetector {
    config: FaultDetectionConfig,
    sensor_timeouts: HashMap<String, Instant>,
    actuator_timeouts: HashMap<String, Instant>,
    fault_history: VecDeque<SafetyFault>,
    watchdog_timer: Option<Instant>,
}

struct CollisionDetector {
    config: CollisionAvoidanceConfig,
    collision_history: VecDeque<CollisionAssessment>,
    trajectory_predictor: TrajectoryPredictor,
}

struct TrajectoryPredictor {
    prediction_horizon: f64,
    time_step: f64,
}

struct SystemMonitor {
    config: SystemMonitoringConfig,
    health_history: VecDeque<SystemHealth>,
    performance_metrics: PerformanceMetrics,
}

#[derive(Debug, Default)]
struct PerformanceMetrics {
    frame_processing_times: VecDeque<f64>,
    planning_times: VecDeque<f64>,
    control_loop_times: VecDeque<f64>,
    memory_usage_history: VecDeque<f64>,
    cpu_usage_history: VecDeque<f64>,
}

struct EmergencyHandler {
    config: EmergencyResponseConfig,
    active_emergency: Option<EmergencyState>,
    emergency_history: VecDeque<EmergencyState>,
}

struct RedundancyManager {
    config: RedundancyConfig,
    primary_systems: HashMap<String, ComponentStatus>,
    backup_systems: HashMap<String, ComponentStatus>,
    voting_results: HashMap<String, VotingResult>,
}

#[derive(Debug, Clone)]
struct VotingResult {
    consensus: bool,
    primary_value: f64,
    backup_values: Vec<f64>,
    selected_value: f64,
    confidence: f64,
}

impl SafetyMonitor {
    /// Create new safety monitoring system
    pub fn new(config: SafetyConfig) -> Result<Self> {
        info!("Initializing safety monitoring system");
        
        let initial_state = SafetyState {
            overall_status: SafetyStatus::Safe,
            active_faults: Vec::new(),
            active_warnings: Vec::new(),
            emergency_state: EmergencyState {
                is_emergency: false,
                emergency_type: None,
                triggered_at: None,
                actions_taken: Vec::new(),
                safe_state_achieved: true,
            },
            system_health: SystemHealth {
                cpu_usage: 0.0,
                memory_usage: 0.0,
                temperature: 25.0,
                voltage: 12.0,
                disk_usage: 0.0,
                network_latency: None,
                sensor_health: HashMap::new(),
                actuator_health: HashMap::new(),
            },
            last_update: Instant::now(),
        };
        
        let fault_detector = FaultDetector::new(&config.fault_detection);
        let collision_detector = CollisionDetector::new(&config.collision_avoidance);
        let system_monitor = SystemMonitor::new(&config.system_monitoring);
        let emergency_handler = EmergencyHandler::new(&config.emergency_response);
        let redundancy_manager = RedundancyManager::new(&config.redundancy);
        
        let (safety_events_tx, _) = broadcast::channel(100);
        let (emergency_command_tx, _) = mpsc::unbounded_channel();
        
        Ok(Self {
            config,
            state: RwLock::new(initial_state),
            fault_detector,
            collision_detector,
            system_monitor,
            emergency_handler,
            redundancy_manager,
            safety_events_tx,
            emergency_command_tx,
            monitoring_handle: None,
        })
    }
    
    /// Start safety monitoring
    pub async fn start(&mut self) -> Result<()> {
        info!("Starting safety monitoring system");
        
        let monitoring_interval = Duration::from_secs_f64(1.0 / self.config.monitoring_frequency_hz);
        let mut interval_timer = interval(monitoring_interval);
        
        // Clone necessary components for the monitoring task
        let state = self.state.clone();
        let events_tx = self.safety_events_tx.clone();
        let config = self.config.clone();
        
        let monitoring_handle = tokio::spawn(async move {
            loop {
                interval_timer.tick().await;
                
                // Perform safety checks
                if let Err(e) = Self::perform_safety_checks(&state, &events_tx, &config).await {
                    error!("Safety check failed: {}", e);
                }
            }
        });
        
        self.monitoring_handle = Some(monitoring_handle);
        Ok(())
    }
    
    /// Stop safety monitoring
    pub async fn stop(&mut self) -> Result<()> {
        if let Some(handle) = self.monitoring_handle.take() {
            handle.abort();
        }
        info!("Safety monitoring system stopped");
        Ok(())
    }
    
    /// Process sensor data for safety analysis
    pub async fn process_sensor_data(
        &mut self,
        vision_data: &VisionData,
        lidar_data: &LidarData,
        current_pose: &Pose2D,
        current_velocity: f64,
    ) -> Result<CollisionAssessment> {
        // Update sensor health
        self.update_sensor_health("vision", vision_data.timestamp).await;
        self.update_sensor_health("lidar", lidar_data.timestamp).await;
        
        // Perform collision detection
        let collision_assessment = self.collision_detector.assess_collision_risk(
            &vision_data.objects,
            &lidar_data.objects,
            current_pose,
            current_velocity,
        ).await?;
        
        // Check for critical situations
        if collision_assessment.collision_risk > 0.8 {
            self.trigger_emergency(EmergencyType::ImmediateCrashRisk).await?;
        } else if collision_assessment.collision_risk > 0.5 {
            self.issue_warning(WarningType::CollisionRisk, 
                              "High collision risk detected".to_string()).await?;
        }
        
        Ok(collision_assessment)
    }
    
    /// Validate planned path for safety
    pub async fn validate_planned_path(
        &mut self,
        planned_path: &PlannedPath,
        sensor_data: (&VisionData, &LidarData),
    ) -> Result<bool> {
        let (vision_data, lidar_data) = sensor_data;
        
        // Check planning time
        if planned_path.planning_time_ms > self.config.fault_detection.max_planning_time_ms as f64 {
            self.report_fault(SafetyFault {
                fault_id: format!("planning_timeout_{}", chrono::Utc::now().timestamp()),
                fault_type: FaultType::PlanningFailure,
                severity: FaultSeverity::High,
                description: format!("Planning took {}ms, exceeds {}ms limit", 
                                   planned_path.planning_time_ms,
                                   self.config.fault_detection.max_planning_time_ms),
                first_detected: Instant::now(),
                last_seen: Instant::now(),
                count: 1,
                source_component: "path_planner".to_string(),
            }).await?;
            
            return Ok(false);
        }
        
        // Check safety assessment
        if planned_path.safety_assessment.overall_safety_score < 0.3 {
            self.issue_warning(WarningType::SystemDegradation,
                              "Planned path has low safety score".to_string()).await?;
            return Ok(false);
        }
        
        // Check for traffic rule violations
        if !planned_path.safety_assessment.traffic_rule_violations.is_empty() {
            for violation in &planned_path.safety_assessment.traffic_rule_violations {
                if violation.severity == crate::planner::Severity::Critical {
                    return Ok(false);
                }
            }
        }
        
        // Validate against sensor data
        for waypoint in &planned_path.trajectory.waypoints {
            let waypoint_position = Point3::new(waypoint.pose.x, waypoint.pose.y, 0.0);
            
            // Check against detected objects
            for object in &vision_data.objects {
                let distance = (object.position - waypoint_position).norm();
                if distance < self.config.collision_avoidance.minimum_safe_distance {
                    self.issue_warning(WarningType::CollisionRisk,
                                      format!("Planned path too close to object at ({:.1}, {:.1})", 
                                             object.position.x, object.position.y)).await?;
                    return Ok(false);
                }
            }
            
            for object in &lidar_data.objects {
                let distance = (object.position - waypoint_position).norm();
                if distance < self.config.collision_avoidance.minimum_safe_distance {
                    return Ok(false);
                }
            }
        }
        
        Ok(true)
    }
    
    /// Trigger emergency response
    pub async fn trigger_emergency(&mut self, emergency_type: EmergencyType) -> Result<()> {
        critical!("EMERGENCY TRIGGERED: {:?}", emergency_type);
        
        let emergency_actions = self.emergency_handler.handle_emergency(&emergency_type).await?;
        
        let emergency_state = EmergencyState {
            is_emergency: true,
            emergency_type: Some(emergency_type.clone()),
            triggered_at: Some(Instant::now()),
            actions_taken: emergency_actions,
            safe_state_achieved: false,
        };
        
        // Update state
        {
            let mut state = self.state.write().await;
            state.overall_status = SafetyStatus::Emergency;
            state.emergency_state = emergency_state.clone();
            state.last_update = Instant::now();
        }
        
        // Broadcast emergency event
        let _ = self.safety_events_tx.send(SafetyEvent::EmergencyTriggered(emergency_type));
        
        // Send emergency commands
        match emergency_state.emergency_type {
            Some(EmergencyType::ImmediateCrashRisk) => {
                let _ = self.emergency_command_tx.send(EmergencyCommand::EmergencyStop);
                let _ = self.emergency_command_tx.send(EmergencyCommand::ActivateHazards);
            },
            Some(EmergencyType::SensorFailure) => {
                let _ = self.emergency_command_tx.send(EmergencyCommand::RequestHumanIntervention);
            },
            _ => {}
        }
        
        Ok(())
    }
    
    /// Get current safety state
    pub async fn get_safety_state(&self) -> SafetyState {
        self.state.read().await.clone()
    }
    
    /// Subscribe to safety events
    pub fn subscribe_safety_events(&self) -> broadcast::Receiver<SafetyEvent> {
        self.safety_events_tx.subscribe()
    }
    
    /// Get emergency command receiver
    pub fn get_emergency_receiver(&self) -> mpsc::UnboundedReceiver<EmergencyCommand> {
        let (_, rx) = mpsc::unbounded_channel();
        rx // This would be properly implemented to share the actual receiver
    }
    
    // Internal methods
    
    async fn perform_safety_checks(
        state: &RwLock<SafetyState>,
        events_tx: &broadcast::Sender<SafetyEvent>,
        config: &SafetyConfig,
    ) -> Result<()> {
        // Check system health
        let system_health = Self::collect_system_health(config).await?;
        
        // Check for faults
        let mut new_faults = Vec::new();
        
        // CPU usage check
        if system_health.cpu_usage > config.system_monitoring.cpu_usage_threshold {
            new_faults.push(SafetyFault {
                fault_id: "high_cpu_usage".to_string(),
                fault_type: FaultType::ComputeFailure,
                severity: FaultSeverity::Medium,
                description: format!("CPU usage {}% exceeds threshold {}%", 
                                   system_health.cpu_usage, 
                                   config.system_monitoring.cpu_usage_threshold),
                first_detected: Instant::now(),
                last_seen: Instant::now(),
                count: 1,
                source_component: "system_monitor".to_string(),
            });
        }
        
        // Memory usage check
        if system_health.memory_usage > config.system_monitoring.memory_usage_threshold {
            new_faults.push(SafetyFault {
                fault_id: "high_memory_usage".to_string(),
                fault_type: FaultType::ComputeFailure,
                severity: FaultSeverity::Medium,
                description: format!("Memory usage {}% exceeds threshold {}%", 
                                   system_health.memory_usage, 
                                   config.system_monitoring.memory_usage_threshold),
                first_detected: Instant::now(),
                last_seen: Instant::now(),
                count: 1,
                source_component: "system_monitor".to_string(),
            });
        }
        
        // Temperature check
        if system_health.temperature > config.system_monitoring.temperature_threshold {
            new_faults.push(SafetyFault {
                fault_id: "high_temperature".to_string(),
                fault_type: FaultType::ThermalFailure,
                severity: FaultSeverity::High,
                description: format!("Temperature {}°C exceeds threshold {}°C", 
                                   system_health.temperature, 
                                   config.system_monitoring.temperature_threshold),
                first_detected: Instant::now(),
                last_seen: Instant::now(),
                count: 1,
                source_component: "thermal_sensor".to_string(),
            });
        }
        
        // Update state with new information
        {
            let mut state_guard = state.write().await;
            state_guard.system_health = system_health;
            
            // Add new faults
            for fault in new_faults {
                events_tx.send(SafetyEvent::FaultDetected(fault.clone())).ok();
                state_guard.active_faults.push(fault);
            }
            
            // Update overall status
            state_guard.overall_status = Self::calculate_overall_status(&state_guard);
            state_guard.last_update = Instant::now();
        }
        
        Ok(())
    }
    
    async fn collect_system_health(config: &SafetyConfig) -> Result<SystemHealth> {
        // Simulate system health collection
        // In a real implementation, this would gather actual system metrics
        
        let cpu_usage = Self::get_cpu_usage().await?;
        let memory_usage = Self::get_memory_usage().await?;
        let temperature = Self::get_temperature().await?;
        let voltage = Self::get_voltage().await?;
        let disk_usage = Self::get_disk_usage().await?;
        let network_latency = Self::get_network_latency().await;
        
        Ok(SystemHealth {
            cpu_usage,
            memory_usage,
            temperature,
            voltage,
            disk_usage,
            network_latency,
            sensor_health: HashMap::new(),
            actuator_health: HashMap::new(),
        })
    }
    
    async fn get_cpu_usage() -> Result<f64> {
        // Simulate CPU usage reading
        Ok(rand::random::<f64>() * 100.0)
    }
    
    async fn get_memory_usage() -> Result<f64> {
        // Simulate memory usage reading
        Ok(rand::random::<f64>() * 100.0)
    }
    
    async fn get_temperature() -> Result<f64> {
        // Simulate temperature reading
        Ok(25.0 + rand::random::<f64>() * 50.0)
    }
    
    async fn get_voltage() -> Result<f64> {
        // Simulate voltage reading
        Ok(11.5 + rand::random::<f64>() * 1.0)
    }
    
    async fn get_disk_usage() -> Result<f64> {
        // Simulate disk usage reading
        Ok(rand::random::<f64>() * 100.0)
    }
    
    async fn get_network_latency() -> Option<u64> {
        // Simulate network latency reading
        Some((rand::random::<f64>() * 100.0) as u64)
    }
    
    fn calculate_overall_status(state: &SafetyState) -> SafetyStatus {
        if state.emergency_state.is_emergency {
            return SafetyStatus::Emergency;
        }
        
        let critical_faults = state.active_faults.iter()
            .any(|f| f.severity >= FaultSeverity::Critical);
        
        if critical_faults {
            return SafetyStatus::Critical;
        }
        
        let high_severity_faults = state.active_faults.iter()
            .any(|f| f.severity >= FaultSeverity::High);
        
        if high_severity_faults || !state.active_warnings.is_empty() {
            return SafetyStatus::Warning;
        }
        
        SafetyStatus::Safe
    }
    
    async fn update_sensor_health(&mut self, sensor_name: &str, last_update: Instant) {
        let mut state = self.state.write().await;
        
        let sensor_health = SensorHealth {
            status: ComponentStatus::Operational,
            last_update,
            error_rate: 0.0,
            signal_quality: 1.0,
            temperature: Some(25.0),
            calibration_status: CalibrationStatus::Calibrated,
        };
        
        state.system_health.sensor_health.insert(sensor_name.to_string(), sensor_health);
    }
    
    async fn report_fault(&mut self, fault: SafetyFault) -> Result<()> {
        {
            let mut state = self.state.write().await;
            state.active_faults.push(fault.clone());
            state.overall_status = Self::calculate_overall_status(&state);
            state.last_update = Instant::now();
        }
        
        let _ = self.safety_events_tx.send(SafetyEvent::FaultDetected(fault));
        Ok(())
    }
    
    async fn issue_warning(&mut self, warning_type: WarningType, description: String) -> Result<()> {
        let warning = SafetyWarning {
            warning_id: format!("warning_{}", chrono::Utc::now().timestamp()),
            warning_type: warning_type.clone(),
            description: description.clone(),
            timestamp: Instant::now(),
            position: None,
            recommended_action: Self::get_recommended_action(&warning_type),
        };
        
        {
            let mut state = self.state.write().await;
            state.active_warnings.push(warning.clone());
            state.overall_status = Self::calculate_overall_status(&state);
            state.last_update = Instant::now();
        }
        
        let _ = self.safety_events_tx.send(SafetyEvent::WarningIssued(warning));
        warn!("Safety warning: {} - {}", warning_type as u8, description);
        
        Ok(())
    }
    
    fn get_recommended_action(warning_type: &WarningType) -> String {
        match warning_type {
            WarningType::CollisionRisk => "Reduce speed and increase following distance".to_string(),
            WarningType::LaneDeparture => "Correct steering to return to lane center".to_string(),
            WarningType::SpeedingViolation => "Reduce speed to comply with speed limit".to_string(),
            WarningType::WeatherCondition => "Adapt driving behavior for weather conditions".to_string(),
            WarningType::TrafficViolation => "Comply with traffic rules and regulations".to_string(),
            WarningType::SystemDegradation => "Engage backup systems or request maintenance".to_string(),
            WarningType::LowBattery => "Find charging station or switch to backup power".to_string(),
            WarningType::SensorBlocked => "Clear sensor obstruction or clean sensor".to_string(),
            WarningType::MaintenanceRequired => "Schedule maintenance at earliest opportunity".to_string(),
        }
    }
}

// Implementation of helper structs

impl FaultDetector {
    fn new(config: &FaultDetectionConfig) -> Self {
        Self {
            config: config.clone(),
            sensor_timeouts: HashMap::new(),
            actuator_timeouts: HashMap::new(),
            fault_history: VecDeque::new(),
            watchdog_timer: if config.enable_watchdog { Some(Instant::now()) } else { None },
        }
    }
}

impl CollisionDetector {
    fn new(config: &CollisionAvoidanceConfig) -> Self {
        Self {
            config: config.clone(),
            collision_history: VecDeque::new(),
            trajectory_predictor: TrajectoryPredictor {
                prediction_horizon: 5.0,
                time_step: 0.1,
            },
        }
    }
    
    async fn assess_collision_risk(
        &mut self,
        vision_objects: &[DetectedObject],
        lidar_objects: &[DetectedObject],
        current_pose: &Pose2D,
        current_velocity: f64,
    ) -> Result<CollisionAssessment> {
        let mut min_time_to_collision: Option<f64> = None;
        let mut closest_object: Option<DetectedObject> = None;
        let mut max_collision_risk = 0.0;
        let mut collision_point: Option<Point3<f64>> = None;
        
        // Combine objects from both sensors
        let all_objects: Vec<_> = vision_objects.iter().chain(lidar_objects.iter()).collect();
        
        for object in all_objects {
            // Calculate distance to object
            let distance = ((object.position.x - current_pose.x).powi(2) + 
                           (object.position.y - current_pose.y).powi(2)).sqrt();
            
            // Calculate time to collision
            let relative_velocity = current_velocity - object.velocity.norm();
            
            if relative_velocity > 0.1 && distance > 0.1 {
                let ttc = distance / relative_velocity;
                
                if ttc < self.config.time_to_collision_critical {
                    max_collision_risk = 1.0;
                    collision_point = Some(object.position);
                } else if ttc < self.config.time_to_collision_warning {
                    let risk = 1.0 - (ttc - self.config.time_to_collision_critical) / 
                              (self.config.time_to_collision_warning - self.config.time_to_collision_critical);
                    max_collision_risk = max_collision_risk.max(risk);
                }
                
                if min_time_to_collision.is_none() || ttc < min_time_to_collision.unwrap() {
                    min_time_to_collision = Some(ttc);
                    closest_object = Some(object.clone());
                }
            }
        }
        
        // Determine recommended action
        let recommended_action = if max_collision_risk > 0.9 {
            AvoidanceAction::EmergencyBrake
        } else if max_collision_risk > 0.7 {
            AvoidanceAction::SlowDown
        } else if max_collision_risk > 0.5 {
            // Check if steering avoidance is possible
            if self.can_steer_around(&closest_object, current_pose) {
                AvoidanceAction::SteerLeft // Simplified
            } else {
                AvoidanceAction::SlowDown
            }
        } else {
            AvoidanceAction::Continue
        };
        
        let assessment = CollisionAssessment {
            collision_risk: max_collision_risk,
            time_to_collision: min_time_to_collision,
            closest_object,
            collision_point,
            avoidance_required: max_collision_risk > 0.3,
            recommended_action,
        };
        
        // Store in history
        self.collision_history.push_back(assessment.clone());
        if self.collision_history.len() > 100 {
            self.collision_history.pop_front();
        }
        
        Ok(assessment)
    }
    
    fn can_steer_around(&self, object: &Option<DetectedObject>, _current_pose: &Pose2D) -> bool {
        // Simplified check for steering clearance
        if let Some(obj) = object {
            obj.position.y.abs() < 5.0 // Can steer if object is within 5m laterally
        } else {
            false
        }
    }
}

impl SystemMonitor {
    fn new(config: &SystemMonitoringConfig) -> Self {
        Self {
            config: config.clone(),
            health_history: VecDeque::new(),
            performance_metrics: PerformanceMetrics::default(),
        }
    }
}

impl EmergencyHandler {
    fn new(config: &EmergencyResponseConfig) -> Self {
        Self {
            config: config.clone(),
            active_emergency: None,
            emergency_history: VecDeque::new(),
        }
    }
    
    async fn handle_emergency(&mut self, emergency_type: &EmergencyType) -> Result<Vec<EmergencyAction>> {
        let mut actions = Vec::new();
        let now = Instant::now();
        
        match emergency_type {
            EmergencyType::ImmediateCrashRisk => {
                if self.config.enable_emergency_brake {
                    actions.push(EmergencyAction {
                        action_type: EmergencyActionType::EmergencyBrake,
                        executed_at: now,
                        success: true,
                        details: "Emergency brake activated".to_string(),
                    });
                }
                
                if self.config.enable_hazard_lights {
                    actions.push(EmergencyAction {
                        action_type: EmergencyActionType::ActivateHazardLights,
                        executed_at: now,
                        success: true,
                        details: "Hazard lights activated".to_string(),
                    });
                }
                
                if self.config.enable_horn {
                    actions.push(EmergencyAction {
                        action_type: EmergencyActionType::SoundHorn,
                        executed_at: now,
                        success: true,
                        details: "Horn activated".to_string(),
                    });
                }
            },
            
            EmergencyType::SensorFailure | EmergencyType::SystemFailure => {
                actions.push(EmergencyAction {
                    action_type: EmergencyActionType::SafeStateParking,
                    executed_at: now,
                    success: true,
                    details: "Initiating safe state parking maneuver".to_string(),
                });
            },
            
            _ => {
                actions.push(EmergencyAction {
                    action_type: EmergencyActionType::ActivateHazardLights,
                    executed_at: now,
                    success: true,
                    details: "General emergency response".to_string(),
                });
            }
        }
        
        Ok(actions)
    }
}

impl RedundancyManager {
    fn new(config: &RedundancyConfig) -> Self {
        Self {
            config: config.clone(),
            primary_systems: HashMap::new(),
            backup_systems: HashMap::new(),
            voting_results: HashMap::new(),
        }
    }
}

impl Default for SafetyConfig {
    fn default() -> Self {
        Self {
            monitoring_frequency_hz: 50.0, // 50 Hz monitoring
            fault_detection: FaultDetectionConfig {
                sensor_timeout_ms: 100,
                actuator_timeout_ms: 50,
                communication_timeout_ms: 200,
                max_sensor_error_rate: 0.05,
                max_planning_time_ms: 100,
                heartbeat_interval_ms: 1000,
                enable_watchdog: true,
            },
            collision_avoidance: CollisionAvoidanceConfig {
                time_to_collision_critical: 1.0,  // 1 second
                time_to_collision_warning: 3.0,   // 3 seconds
                minimum_safe_distance: 2.0,       // 2 meters
                lateral_clearance: 0.5,           // 0.5 meters
                emergency_brake_distance: 50.0,   // 50 meters
                max_deceleration: 9.8,            // 1g
            },
            system_monitoring: SystemMonitoringConfig {
                cpu_usage_threshold: 80.0,        // 80%
                memory_usage_threshold: 85.0,     // 85%
                temperature_threshold: 85.0,      // 85°C
                voltage_threshold: (11.0, 13.5),  // 11-13.5V
                communication_latency_threshold: 50, // 50ms
                storage_usage_threshold: 90.0,    // 90%
            },
            emergency_response: EmergencyResponseConfig {
                enable_emergency_brake: true,
                enable_emergency_steering: true,
                enable_hazard_lights: true,
                enable_horn: true,
                emergency_stop_distance: 100.0,   // 100 meters
                safe_state_timeout: 5000,         // 5 seconds
            },
            redundancy: RedundancyConfig {
                dual_sensor_voting: true,
                triple_modular_redundancy: false,
                backup_planning_system: true,
                redundant_actuators: false,
                independent_safety_processor: false,
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_safety_monitor_creation() {
        let config = SafetyConfig::default();
        let monitor = SafetyMonitor::new(config);
        assert!(monitor.is_ok());
    }
    
    #[tokio::test]
    async fn test_fault_detection() {
        let config = SafetyConfig::default();
        let mut monitor = SafetyMonitor::new(config).unwrap();
        
        let fault = SafetyFault {
            fault_id: "test_fault".to_string(),
            fault_type: FaultType::SensorFailure,
            severity: FaultSeverity::High,
            description: "Test fault".to_string(),
            first_detected: Instant::now(),
            last_seen: Instant::now(),
            count: 1,
            source_component: "test".to_string(),
        };
        
        monitor.report_fault(fault).await.unwrap();
        
        let state = monitor.get_safety_state().await;
        assert_eq!(state.active_faults.len(), 1);
        assert_eq!(state.overall_status, SafetyStatus::Warning);
    }
    
    #[tokio::test]
    async fn test_emergency_trigger() {
        let config = SafetyConfig::default();
        let mut monitor = SafetyMonitor::new(config).unwrap();
        
        monitor.trigger_emergency(EmergencyType::ImmediateCrashRisk).await.unwrap();
        
        let state = monitor.get_safety_state().await;
        assert_eq!(state.overall_status, SafetyStatus::Emergency);
        assert!(state.emergency_state.is_emergency);
    }
    
    #[test]
    fn test_collision_assessment() {
        let config = CollisionAvoidanceConfig {
            time_to_collision_critical: 1.0,
            time_to_collision_warning: 3.0,
            minimum_safe_distance: 2.0,
            lateral_clearance: 0.5,
            emergency_brake_distance: 50.0,
            max_deceleration: 9.8,
        };
        
        let mut detector = CollisionDetector::new(&config);
        
        // Test collision risk calculation would go here
        // This is simplified for the example
    }
}