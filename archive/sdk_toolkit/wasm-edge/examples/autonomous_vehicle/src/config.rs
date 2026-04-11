/*!
# Configuration Module

Centralized configuration management for autonomous vehicle system.
Handles loading, validation, and hot-reloading of configuration parameters.
*/

use anyhow::{Context, Result};
use log::{info, warn, error};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tokio::fs;
use tokio::sync::{broadcast, RwLock};
use tokio::time::{interval, Duration};

use crate::{
    VisionConfig, LidarConfig, PlannerConfig, SafetyConfig, 
    VehicleControlConfig, V2XConfig
};

/// Master configuration for autonomous vehicle
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutonomousVehicleConfig {
    pub metadata: ConfigMetadata,
    pub vehicle: VehicleSystemConfig,
    pub perception: PerceptionConfig,
    pub planning: PlanningSystemConfig,
    pub control: ControlSystemConfig,
    pub safety: SafetySystemConfig,
    pub communication: CommunicationSystemConfig,
    pub logging: LoggingConfig,
    pub performance: PerformanceConfig,
    pub calibration: CalibrationConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigMetadata {
    pub version: String,
    pub created_at: String,
    pub last_modified: String,
    pub author: String,
    pub description: String,
    pub vehicle_model: String,
    pub deployment_environment: DeploymentEnvironment,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum DeploymentEnvironment {
    Development,
    Testing,
    Staging,
    Production,
    Simulation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VehicleSystemConfig {
    pub vehicle_id: String,
    pub make: String,
    pub model: String,
    pub year: u16,
    pub vin: Option<String>,
    pub license_plate: Option<String>,
    pub dimensions: VehicleDimensions,
    pub mass: VehicleMass,
    pub powertrain: PowertrainConfig,
    pub autonomous_level: AutonomyLevel,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VehicleDimensions {
    pub length: f64,         // meters
    pub width: f64,          // meters
    pub height: f64,         // meters
    pub wheelbase: f64,      // meters
    pub track_width: f64,    // meters
    pub ground_clearance: f64, // meters
    pub turning_radius: f64, // meters
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VehicleMass {
    pub curb_weight: f64,    // kg
    pub gross_weight: f64,   // kg
    pub payload_capacity: f64, // kg
    pub center_of_gravity: (f64, f64, f64), // (x, y, z) in meters
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PowertrainConfig {
    pub type_: PowertrainType,
    pub max_power: f64,      // kW
    pub max_torque: f64,     // Nm
    pub transmission: TransmissionType,
    pub fuel_capacity: f64,  // liters or kWh
    pub efficiency: f64,     // km/L or km/kWh
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum PowertrainType {
    Internal,     // ICE
    Electric,     // BEV
    Hybrid,       // HEV
    PluginHybrid, // PHEV
    FuelCell,     // FCEV
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum TransmissionType {
    Manual,
    Automatic,
    CVT,
    DirectDrive,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum AutonomyLevel {
    Level0, // No automation
    Level1, // Driver assistance
    Level2, // Partial automation
    Level3, // Conditional automation
    Level4, // High automation
    Level5, // Full automation
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerceptionConfig {
    pub vision: VisionSystemConfig,
    pub lidar: LidarSystemConfig,
    pub radar: RadarSystemConfig,
    pub ultrasonic: UltrasonicSystemConfig,
    pub gps: GpsSystemConfig,
    pub imu: ImuSystemConfig,
    pub sensor_fusion: SensorFusionConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VisionSystemConfig {
    pub cameras: Vec<CameraConfig>,
    pub calibration_file: String,
    pub models_path: String,
    pub detection_threshold: f32,
    pub enable_gpu: bool,
    pub frame_rate: f32,
    pub resolution: (u32, u32),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CameraConfig {
    pub camera_id: u32,
    pub name: String,
    pub position: CameraPosition,
    pub mounting_location: (f64, f64, f64), // (x, y, z) relative to vehicle center
    pub orientation: (f64, f64, f64),       // (roll, pitch, yaw) in radians
    pub resolution: (u32, u32),
    pub fps: f32,
    pub fov_degrees: f32,
    pub exposure_mode: ExposureMode,
    pub auto_focus: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum CameraPosition {
    Front,
    Rear,
    Left,
    Right,
    FrontLeft,
    FrontRight,
    RearLeft,
    RearRight,
    Interior,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ExposureMode {
    Auto,
    Manual,
    Sports,
    Night,
    Backlight,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LidarSystemConfig {
    pub lidars: Vec<LidarConfig>,
    pub point_cloud_processing: PointCloudProcessingConfig,
    pub ground_detection: GroundDetectionConfig,
    pub clustering: ClusteringConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LidarConfig {
    pub lidar_id: u32,
    pub name: String,
    pub device_path: String,
    pub mounting_location: (f64, f64, f64), // (x, y, z) relative to vehicle center
    pub orientation: (f64, f64, f64),       // (roll, pitch, yaw) in radians
    pub rotation_frequency: f32,            // Hz
    pub vertical_fov: (f32, f32),          // (min, max) degrees
    pub horizontal_fov: (f32, f32),        // (min, max) degrees
    pub max_range: f32,                    // meters
    pub min_range: f32,                    // meters
    pub angular_resolution: f32,           // degrees
    pub range_accuracy: f32,               // meters
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PointCloudProcessingConfig {
    pub voxel_size: f32,
    pub noise_filter_radius: f32,
    pub noise_min_neighbors: usize,
    pub intensity_threshold: f32,
    pub remove_ground: bool,
    pub max_points_per_frame: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GroundDetectionConfig {
    pub ransac_iterations: usize,
    pub distance_threshold: f32,
    pub min_points: usize,
    pub height_threshold: f32,
    pub plane_angle_threshold: f32, // radians
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClusteringConfig {
    pub cluster_tolerance: f32,
    pub min_cluster_size: usize,
    pub max_cluster_size: usize,
    pub euclidean_clustering: bool,
    pub dbscan_eps: f32,
    pub dbscan_min_points: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RadarSystemConfig {
    pub radars: Vec<RadarConfig>,
    pub enable_doppler: bool,
    pub max_range: f32,
    pub angular_resolution: f32,
    pub range_resolution: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RadarConfig {
    pub radar_id: u32,
    pub name: String,
    pub frequency_ghz: f32,
    pub mounting_location: (f64, f64, f64),
    pub orientation: (f64, f64, f64),
    pub fov_degrees: f32,
    pub max_range: f32,
    pub min_range: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UltrasonicSystemConfig {
    pub sensors: Vec<UltrasonicConfig>,
    pub enable_parking_assist: bool,
    pub detection_threshold: f32,
    pub max_range: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UltrasonicConfig {
    pub sensor_id: u32,
    pub name: String,
    pub mounting_location: (f64, f64, f64),
    pub orientation: (f64, f64, f64),
    pub frequency_khz: f32,
    pub beam_angle: f32,
    pub max_range: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GpsSystemConfig {
    pub receiver_type: GpsReceiverType,
    pub rtk_enabled: bool,
    pub rtk_base_station: Option<String>,
    pub update_rate_hz: f32,
    pub accuracy_threshold: f32, // meters
    pub antenna_location: (f64, f64, f64),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum GpsReceiverType {
    StandardGPS,
    DGPS,
    RTK,
    PPP,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImuSystemConfig {
    pub imu_type: ImuType,
    pub mounting_location: (f64, f64, f64),
    pub orientation: (f64, f64, f64),
    pub sample_rate_hz: f32,
    pub accelerometer_range: f32,   // g
    pub gyroscope_range: f32,       // deg/s
    pub magnetometer_enabled: bool,
    pub temperature_compensation: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ImuType {
    MEMS,
    Fiber,
    Ring,
    Tactical,
    Navigation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorFusionConfig {
    pub fusion_algorithm: FusionAlgorithm,
    pub kalman_filter: KalmanFilterConfig,
    pub data_association: DataAssociationConfig,
    pub track_management: TrackManagementConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum FusionAlgorithm {
    ExtendedKalmanFilter,
    UnscentedKalmanFilter,
    ParticleFilter,
    MultiHypothesisTracker,
    JointProbabilisticDataAssociation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KalmanFilterConfig {
    pub process_noise: f64,
    pub measurement_noise: f64,
    pub initial_uncertainty: f64,
    pub max_prediction_time: f64, // seconds
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataAssociationConfig {
    pub gating_threshold: f64,
    pub association_algorithm: AssociationAlgorithm,
    pub max_association_distance: f64, // meters
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum AssociationAlgorithm {
    NearestNeighbor,
    GlobalNearestNeighbor,
    MunkresBipartite,
    Auction,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrackManagementConfig {
    pub track_initiation_threshold: usize,
    pub track_termination_threshold: usize,
    pub max_missed_detections: usize,
    pub max_track_age: f64, // seconds
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlanningSystemConfig {
    pub global_planner: GlobalPlannerConfig,
    pub local_planner: LocalPlannerConfig,
    pub behavior_planner: BehaviorPlannerConfig,
    pub route_planner: RoutePlannerConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlobalPlannerConfig {
    pub algorithm: GlobalPlanningAlgorithm,
    pub planning_horizon: f64,    // seconds
    pub planning_resolution: f64, // meters
    pub replanning_frequency: f64, // Hz
    pub cost_weights: CostWeights,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum GlobalPlanningAlgorithm {
    AStar,
    HybridAStar,
    RRT,
    RRTStar,
    PRM,
    LatticeState,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostWeights {
    pub distance: f64,
    pub time: f64,
    pub comfort: f64,
    pub safety: f64,
    pub fuel_efficiency: f64,
    pub traffic_rules: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalPlannerConfig {
    pub algorithm: LocalPlanningAlgorithm,
    pub planning_horizon: f64,    // seconds
    pub time_resolution: f64,     // seconds
    pub lateral_resolution: f64,  // meters
    pub max_curvature: f64,       // 1/meters
    pub comfort_limits: ComfortLimits,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum LocalPlanningAlgorithm {
    PolynomialTrajectory,
    SplineTrajectory,
    OptimalControl,
    ModelPredictiveControl,
    PotentialField,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComfortLimits {
    pub max_acceleration: f64,       // m/s²
    pub max_deceleration: f64,       // m/s²
    pub max_lateral_acceleration: f64, // m/s²
    pub max_jerk: f64,               // m/s³
    pub max_angular_velocity: f64,   // rad/s
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BehaviorPlannerConfig {
    pub state_machine: StateMachineConfig,
    pub decision_making: DecisionMakingConfig,
    pub maneuver_planning: ManeuverPlanningConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateMachineConfig {
    pub states: Vec<BehaviorState>,
    pub transitions: Vec<StateTransition>,
    pub default_state: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BehaviorState {
    pub name: String,
    pub description: String,
    pub max_speed: f64,
    pub following_distance: f64,
    pub lane_change_allowed: bool,
    pub overtaking_allowed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateTransition {
    pub from_state: String,
    pub to_state: String,
    pub condition: String,
    pub trigger_threshold: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionMakingConfig {
    pub decision_algorithm: DecisionAlgorithm,
    pub risk_assessment: RiskAssessmentConfig,
    pub uncertainty_handling: UncertaintyHandlingConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum DecisionAlgorithm {
    RuleBased,
    MachineLearning,
    ReinforcementLearning,
    GameTheory,
    MonteCarloTreeSearch,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskAssessmentConfig {
    pub risk_threshold: f64,
    pub time_horizons: Vec<f64>, // seconds
    pub risk_factors: Vec<RiskFactor>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskFactor {
    pub name: String,
    pub weight: f64,
    pub threshold: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UncertaintyHandlingConfig {
    pub confidence_threshold: f64,
    pub conservative_mode: bool,
    pub fallback_behavior: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManeuverPlanningConfig {
    pub lane_change: LaneChangeConfig,
    pub intersection: IntersectionConfig,
    pub parking: ParkingConfig,
    pub emergency: EmergencyManeuverConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LaneChangeConfig {
    pub min_gap_distance: f64,     // meters
    pub min_gap_time: f64,         // seconds
    pub comfort_acceleration: f64,  // m/s²
    pub max_lane_change_time: f64, // seconds
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntersectionConfig {
    pub approach_speed: f64,       // m/s
    pub stop_line_buffer: f64,     // meters
    pub yellow_light_behavior: YellowLightBehavior,
    pub right_of_way_timeout: f64, // seconds
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum YellowLightBehavior {
    Stop,
    Proceed,
    Evaluate,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParkingConfig {
    pub parallel_parking: bool,
    pub perpendicular_parking: bool,
    pub angle_parking: bool,
    pub min_parking_space: (f64, f64), // (length, width) in meters
    pub parking_precision: f64,        // meters
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmergencyManeuverConfig {
    pub emergency_braking: bool,
    pub emergency_steering: bool,
    pub collision_avoidance: bool,
    pub minimum_safe_distance: f64, // meters
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutePlannerConfig {
    pub map_provider: MapProvider,
    pub routing_algorithm: RoutingAlgorithm,
    pub traffic_data_enabled: bool,
    pub real_time_updates: bool,
    pub route_preferences: RoutePreferences,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum MapProvider {
    OpenStreetMap,
    HERE,
    TomTom,
    Google,
    Custom,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum RoutingAlgorithm {
    Dijkstra,
    AStar,
    BidirectionalDijkstra,
    ContractionHierarchies,
    OSRM,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutePreferences {
    pub prefer_highways: bool,
    pub avoid_tolls: bool,
    pub avoid_ferries: bool,
    pub eco_routing: bool,
    pub route_optimization: RouteOptimization,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum RouteOptimization {
    Fastest,
    Shortest,
    MostEconomical,
    Balanced,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ControlSystemConfig {
    pub longitudinal_control: LongitudinalControlConfig,
    pub lateral_control: LateralControlConfig,
    pub actuator_control: ActuatorControlConfig,
    pub control_frequency: f64, // Hz
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LongitudinalControlConfig {
    pub controller_type: ControllerType,
    pub pid_params: PIDParams,
    pub mpc_params: Option<MPCParams>,
    pub speed_limits: SpeedLimits,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ControllerType {
    PID,
    ModelPredictiveControl,
    AdaptiveControl,
    SlidingMode,
    FuzzyLogic,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PIDParams {
    pub kp: f64,
    pub ki: f64,
    pub kd: f64,
    pub integral_limit: f64,
    pub derivative_filter: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MPCParams {
    pub prediction_horizon: usize,
    pub control_horizon: usize,
    pub weight_output: f64,
    pub weight_control: f64,
    pub weight_delta_control: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpeedLimits {
    pub max_speed: f64,          // m/s
    pub max_acceleration: f64,   // m/s²
    pub max_deceleration: f64,   // m/s²
    pub emergency_deceleration: f64, // m/s²
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LateralControlConfig {
    pub controller_type: ControllerType,
    pub pid_params: PIDParams,
    pub stanley_params: Option<StanleyParams>,
    pub pure_pursuit_params: Option<PurePursuitParams>,
    pub steering_limits: SteeringLimits,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StanleyParams {
    pub k_cross_track: f64,
    pub k_heading: f64,
    pub soft_bound: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PurePursuitParams {
    pub lookahead_distance: f64, // meters
    pub lookahead_time: f64,     // seconds
    pub min_lookahead: f64,      // meters
    pub max_lookahead: f64,      // meters
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SteeringLimits {
    pub max_steering_angle: f64, // radians
    pub max_steering_rate: f64,  // rad/s
    pub max_steering_acceleration: f64, // rad/s²
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActuatorControlConfig {
    pub throttle: ActuatorConfig,
    pub brake: ActuatorConfig,
    pub steering: ActuatorConfig,
    pub transmission: ActuatorConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActuatorConfig {
    pub response_time: f64,      // seconds
    pub deadband: f64,           // units specific to actuator
    pub saturation_limits: (f64, f64), // (min, max)
    pub calibration_curve: Vec<CalibrationPoint>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationPoint {
    pub input: f64,
    pub output: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SafetySystemConfig {
    pub monitoring_frequency: f64, // Hz
    pub fault_detection: FaultDetectionConfig,
    pub collision_avoidance: CollisionAvoidanceConfig,
    pub emergency_response: EmergencyResponseConfig,
    pub redundancy: RedundancyConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FaultDetectionConfig {
    pub sensor_timeout: f64,     // seconds
    pub actuator_timeout: f64,   // seconds
    pub communication_timeout: f64, // seconds
    pub max_error_rate: f64,     // percentage
    pub watchdog_enabled: bool,
    pub diagnostic_frequency: f64, // Hz
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CollisionAvoidanceConfig {
    pub time_to_collision_warning: f64, // seconds
    pub time_to_collision_critical: f64, // seconds
    pub minimum_safe_distance: f64,     // meters
    pub lateral_clearance: f64,         // meters
    pub emergency_brake_threshold: f64, // m/s²
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmergencyResponseConfig {
    pub enable_emergency_brake: bool,
    pub enable_emergency_steering: bool,
    pub enable_hazard_lights: bool,
    pub enable_emergency_communication: bool,
    pub safe_stop_procedure: SafeStopProcedure,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SafeStopProcedure {
    ImmediateStop,
    ControlledStop,
    MinimumRiskManeuver,
    PullOver,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedundancyConfig {
    pub sensor_redundancy: bool,
    pub actuator_redundancy: bool,
    pub processor_redundancy: bool,
    pub communication_redundancy: bool,
    pub power_redundancy: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommunicationSystemConfig {
    pub v2x: V2XSystemConfig,
    pub cellular: CellularConfig,
    pub wifi: WiFiConfig,
    pub bluetooth: BluetoothConfig,
    pub can_bus: CanBusConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct V2XSystemConfig {
    pub enabled: bool,
    pub dsrc_enabled: bool,
    pub cv2x_enabled: bool,
    pub broadcast_frequency: f64, // Hz
    pub communication_range: f64, // meters
    pub encryption_enabled: bool,
    pub message_priorities: MessagePriorities,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessagePriorities {
    pub emergency: u8,
    pub safety: u8,
    pub traffic: u8,
    pub infotainment: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CellularConfig {
    pub enabled: bool,
    pub provider: String,
    pub apn: String,
    pub data_limit: Option<u64>, // bytes per month
    pub roaming_enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WiFiConfig {
    pub enabled: bool,
    pub auto_connect: bool,
    pub preferred_networks: Vec<WiFiNetwork>,
    pub hotspot_mode: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WiFiNetwork {
    pub ssid: String,
    pub password: Option<String>,
    pub security: WiFiSecurity,
    pub priority: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum WiFiSecurity {
    Open,
    WEP,
    WPA,
    WPA2,
    WPA3,
    Enterprise,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BluetoothConfig {
    pub enabled: bool,
    pub discoverable: bool,
    pub auto_pairing: bool,
    pub supported_profiles: Vec<BluetoothProfile>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum BluetoothProfile {
    A2DP,
    HFP,
    HID,
    OPP,
    SPP,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CanBusConfig {
    pub interfaces: Vec<CanInterface>,
    pub baudrate: u32,
    pub extended_frames: bool,
    pub error_handling: CanErrorHandling,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CanInterface {
    pub name: String,
    pub enabled: bool,
    pub filters: Vec<CanFilter>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CanFilter {
    pub can_id: u32,
    pub can_mask: u32,
    pub extended: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum CanErrorHandling {
    Ignore,
    Log,
    Alert,
    Shutdown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoggingConfig {
    pub log_level: LogLevel,
    pub log_destinations: Vec<LogDestination>,
    pub rotation: LogRotation,
    pub data_retention: DataRetention,
    pub privacy: PrivacyConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum LogLevel {
    Trace,
    Debug,
    Info,
    Warn,
    Error,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogDestination {
    pub name: String,
    pub type_: LogDestinationType,
    pub enabled: bool,
    pub format: LogFormat,
    pub filters: Vec<LogFilter>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum LogDestinationType {
    File,
    Console,
    Syslog,
    Remote,
    Database,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum LogFormat {
    Plain,
    JSON,
    XML,
    CSV,
    Binary,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogFilter {
    pub component: String,
    pub level: LogLevel,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogRotation {
    pub enabled: bool,
    pub max_file_size: u64,      // bytes
    pub max_files: u32,
    pub rotation_frequency: RotationFrequency,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum RotationFrequency {
    Hourly,
    Daily,
    Weekly,
    Monthly,
    SizeBased,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataRetention {
    pub sensor_data_days: u32,
    pub log_data_days: u32,
    pub video_data_days: u32,
    pub diagnostic_data_days: u32,
    pub auto_cleanup: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrivacyConfig {
    pub anonymize_location: bool,
    pub encrypt_sensitive_data: bool,
    pub data_sharing_consent: bool,
    pub pii_detection: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceConfig {
    pub system_monitoring: SystemMonitoringConfig,
    pub resource_limits: ResourceLimits,
    pub optimization: OptimizationConfig,
    pub profiling: ProfilingConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemMonitoringConfig {
    pub enabled: bool,
    pub monitoring_frequency: f64, // Hz
    pub cpu_threshold: f64,        // percentage
    pub memory_threshold: f64,     // percentage
    pub disk_threshold: f64,       // percentage
    pub temperature_threshold: f64, // celsius
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceLimits {
    pub max_cpu_usage: f64,        // percentage
    pub max_memory_usage: u64,     // bytes
    pub max_disk_usage: u64,       // bytes
    pub max_network_bandwidth: u64, // bytes/second
    pub max_concurrent_tasks: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptimizationConfig {
    pub enable_compiler_optimizations: bool,
    pub enable_gpu_acceleration: bool,
    pub enable_caching: bool,
    pub cache_size_limit: u64,     // bytes
    pub parallel_processing: bool,
    pub thread_pool_size: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfilingConfig {
    pub enabled: bool,
    pub profile_frequency: f64,    // Hz
    pub profile_duration: f64,     // seconds
    pub output_format: ProfileFormat,
    pub components_to_profile: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ProfileFormat {
    FlameGraph,
    CallGraph,
    Timeline,
    Statistics,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationConfig {
    pub camera_calibration: CameraCalibrationConfig,
    pub lidar_calibration: LidarCalibrationConfig,
    pub imu_calibration: ImuCalibrationConfig,
    pub wheel_calibration: WheelCalibrationConfig,
    pub auto_calibration: AutoCalibrationConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CameraCalibrationConfig {
    pub intrinsic_calibration: bool,
    pub extrinsic_calibration: bool,
    pub stereo_calibration: bool,
    pub calibration_target: CalibrationTarget,
    pub calibration_frequency: CalibrationFrequency,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum CalibrationTarget {
    Checkerboard,
    Circles,
    AsymmetricCircles,
    ArUco,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum CalibrationFrequency {
    Manual,
    Startup,
    Daily,
    Weekly,
    Monthly,
    Continuous,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LidarCalibrationConfig {
    pub intensity_calibration: bool,
    pub range_calibration: bool,
    pub multi_lidar_calibration: bool,
    pub ground_plane_calibration: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImuCalibrationConfig {
    pub accelerometer_calibration: bool,
    pub gyroscope_calibration: bool,
    pub magnetometer_calibration: bool,
    pub temperature_compensation: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WheelCalibrationConfig {
    pub wheel_radius_calibration: bool,
    pub wheelbase_calibration: bool,
    pub track_width_calibration: bool,
    pub odometry_calibration: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoCalibrationConfig {
    pub enabled: bool,
    pub calibration_triggers: Vec<CalibrationTrigger>,
    pub validation_threshold: f64,
    pub backup_calibration: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum CalibrationTrigger {
    TimeInterval,
    PerformanceDegradation,
    EnvironmentChange,
    ManualRequest,
    MaintenanceMode,
}

/// Configuration management system
pub struct ConfigurationManager {
    config: Arc<RwLock<AutonomousVehicleConfig>>,
    config_path: PathBuf,
    watch_enabled: bool,
    update_tx: broadcast::Sender<ConfigUpdate>,
    file_watcher_handle: Option<tokio::task::JoinHandle<()>>,
}

#[derive(Debug, Clone)]
pub enum ConfigUpdate {
    ConfigReloaded,
    ConfigValidationFailed(String),
    ConfigFileChanged,
    ConfigSaved,
}

impl ConfigurationManager {
    /// Create new configuration manager
    pub async fn new<P: AsRef<Path>>(config_path: P) -> Result<Self> {
        let config_path = config_path.as_ref().to_path_buf();
        
        // Load configuration from file
        let config = Self::load_config(&config_path).await?;
        
        // Validate configuration
        Self::validate_config(&config)?;
        
        let (update_tx, _) = broadcast::channel(100);
        
        Ok(Self {
            config: Arc::new(RwLock::new(config)),
            config_path,
            watch_enabled: false,
            update_tx,
            file_watcher_handle: None,
        })
    }
    
    /// Load configuration from file
    async fn load_config(path: &Path) -> Result<AutonomousVehicleConfig> {
        let content = fs::read_to_string(path).await
            .context(format!("Failed to read config file: {:?}", path))?;
        
        let config: AutonomousVehicleConfig = if path.extension().and_then(|s| s.to_str()) == Some("yaml") || 
                                                path.extension().and_then(|s| s.to_str()) == Some("yml") {
            serde_yaml::from_str(&content)
                .context("Failed to parse YAML configuration")?
        } else {
            serde_json::from_str(&content)
                .context("Failed to parse JSON configuration")?
        };
        
        info!("Loaded configuration from {:?}", path);
        Ok(config)
    }
    
    /// Validate configuration
    fn validate_config(config: &AutonomousVehicleConfig) -> Result<()> {
        // Basic validation checks
        if config.vehicle.vehicle_id.is_empty() {
            return Err(anyhow::anyhow!("Vehicle ID cannot be empty"));
        }
        
        if config.vehicle.dimensions.length <= 0.0 || config.vehicle.dimensions.width <= 0.0 {
            return Err(anyhow::anyhow!("Vehicle dimensions must be positive"));
        }
        
        if config.perception.vision.cameras.is_empty() {
            warn!("No cameras configured in vision system");
        }
        
        if config.safety.monitoring_frequency <= 0.0 {
            return Err(anyhow::anyhow!("Safety monitoring frequency must be positive"));
        }
        
        if config.control.control_frequency <= 0.0 {
            return Err(anyhow::anyhow!("Control frequency must be positive"));
        }
        
        // Validate PID parameters
        for controller in [&config.control.longitudinal_control.pid_params, 
                          &config.control.lateral_control.pid_params] {
            if controller.kp < 0.0 || controller.ki < 0.0 || controller.kd < 0.0 {
                return Err(anyhow::anyhow!("PID parameters must be non-negative"));
            }
        }
        
        info!("Configuration validation passed");
        Ok(())
    }
    
    /// Get current configuration
    pub async fn get_config(&self) -> AutonomousVehicleConfig {
        self.config.read().await.clone()
    }
    
    /// Update configuration
    pub async fn update_config(&self, new_config: AutonomousVehicleConfig) -> Result<()> {
        // Validate new configuration
        Self::validate_config(&new_config)?;
        
        // Update in-memory configuration
        {
            let mut config = self.config.write().await;
            *config = new_config;
        }
        
        // Save to file
        self.save_config().await?;
        
        // Notify listeners
        let _ = self.update_tx.send(ConfigUpdate::ConfigReloaded);
        
        info!("Configuration updated successfully");
        Ok(())
    }
    
    /// Save configuration to file
    pub async fn save_config(&self) -> Result<()> {
        let config = self.config.read().await;
        
        let content = if self.config_path.extension().and_then(|s| s.to_str()) == Some("yaml") || 
                        self.config_path.extension().and_then(|s| s.to_str()) == Some("yml") {
            serde_yaml::to_string(&*config)
                .context("Failed to serialize configuration to YAML")?
        } else {
            serde_json::to_string_pretty(&*config)
                .context("Failed to serialize configuration to JSON")?
        };
        
        fs::write(&self.config_path, content).await
            .context("Failed to write configuration file")?;
        
        let _ = self.update_tx.send(ConfigUpdate::ConfigSaved);
        
        info!("Configuration saved to {:?}", self.config_path);
        Ok(())
    }
    
    /// Enable/disable file watching for hot reloading
    pub async fn set_file_watching(&mut self, enabled: bool) -> Result<()> {
        if enabled && !self.watch_enabled {
            self.start_file_watcher().await?;
        } else if !enabled && self.watch_enabled {
            self.stop_file_watcher().await?;
        }
        
        self.watch_enabled = enabled;
        Ok(())
    }
    
    /// Start file watcher for hot reloading
    async fn start_file_watcher(&mut self) -> Result<()> {
        let config_path = self.config_path.clone();
        let config = self.config.clone();
        let update_tx = self.update_tx.clone();
        
        let watcher_handle = tokio::spawn(async move {
            let mut interval_timer = interval(Duration::from_secs(1));
            let mut last_modified = std::time::SystemTime::UNIX_EPOCH;
            
            loop {
                interval_timer.tick().await;
                
                if let Ok(metadata) = std::fs::metadata(&config_path) {
                    if let Ok(modified) = metadata.modified() {
                        if modified > last_modified {
                            last_modified = modified;
                            
                            match Self::load_config(&config_path).await {
                                Ok(new_config) => {
                                    if let Err(e) = Self::validate_config(&new_config) {
                                        error!("Configuration validation failed: {}", e);
                                        let _ = update_tx.send(ConfigUpdate::ConfigValidationFailed(e.to_string()));
                                        continue;
                                    }
                                    
                                    {
                                        let mut config_guard = config.write().await;
                                        *config_guard = new_config;
                                    }
                                    
                                    let _ = update_tx.send(ConfigUpdate::ConfigReloaded);
                                    info!("Configuration hot-reloaded from file");
                                },
                                Err(e) => {
                                    error!("Failed to reload configuration: {}", e);
                                    let _ = update_tx.send(ConfigUpdate::ConfigValidationFailed(e.to_string()));
                                }
                            }
                        }
                    }
                }
            }
        });
        
        self.file_watcher_handle = Some(watcher_handle);
        info!("File watcher started for configuration hot-reloading");
        Ok(())
    }
    
    /// Stop file watcher
    async fn stop_file_watcher(&mut self) -> Result<()> {
        if let Some(handle) = self.file_watcher_handle.take() {
            handle.abort();
        }
        
        info!("File watcher stopped");
        Ok(())
    }
    
    /// Subscribe to configuration updates
    pub fn subscribe_updates(&self) -> broadcast::Receiver<ConfigUpdate> {
        self.update_tx.subscribe()
    }
    
    /// Get specific subsystem configuration
    pub async fn get_vision_config(&self) -> VisionConfig {
        let config = self.config.read().await;
        VisionConfig {
            cameras: config.perception.vision.cameras.iter().map(|c| {
                crate::vision::CameraConfig {
                    camera_id: c.camera_id,
                    position: match c.position {
                        CameraPosition::Front => crate::vision::CameraPosition::Front,
                        CameraPosition::Rear => crate::vision::CameraPosition::Rear,
                        CameraPosition::Left => crate::vision::CameraPosition::Left,
                        CameraPosition::Right => crate::vision::CameraPosition::Right,
                        _ => crate::vision::CameraPosition::Front,
                    },
                    resolution: c.resolution,
                    fps: c.fps,
                    fov_degrees: c.fov_degrees,
                }
            }).collect(),
            calibration_file: config.perception.vision.calibration_file.clone(),
            models_path: config.perception.vision.models_path.clone(),
            detection_threshold: config.perception.vision.detection_threshold,
            enable_gpu: config.perception.vision.enable_gpu,
        }
    }
    
    /// Get LiDAR configuration
    pub async fn get_lidar_config(&self) -> LidarConfig {
        let config = self.config.read().await;
        crate::lidar::LidarConfig {
            device_path: config.perception.lidar.lidars.first()
                .map(|l| l.device_path.clone())
                .unwrap_or_else(|| "/dev/ttyUSB0".to_string()),
            rotation_frequency: config.perception.lidar.lidars.first()
                .map(|l| l.rotation_frequency)
                .unwrap_or(10.0),
            vertical_fov: config.perception.lidar.lidars.first()
                .map(|l| l.vertical_fov)
                .unwrap_or((-15.0, 15.0)),
            horizontal_fov: config.perception.lidar.lidars.first()
                .map(|l| l.horizontal_fov)
                .unwrap_or((-180.0, 180.0)),
            max_range: config.perception.lidar.lidars.first()
                .map(|l| l.max_range)
                .unwrap_or(100.0),
            min_range: config.perception.lidar.lidars.first()
                .map(|l| l.min_range)
                .unwrap_or(0.1),
            point_cloud_filter: crate::lidar::PointCloudFilter {
                voxel_size: config.perception.lidar.point_cloud_processing.voxel_size,
                noise_filter_radius: config.perception.lidar.point_cloud_processing.noise_filter_radius,
                noise_min_neighbors: config.perception.lidar.point_cloud_processing.noise_min_neighbors,
                intensity_threshold: config.perception.lidar.point_cloud_processing.intensity_threshold,
                remove_ground: config.perception.lidar.point_cloud_processing.remove_ground,
            },
            ground_detection: crate::lidar::GroundDetectionConfig {
                ransac_iterations: config.perception.lidar.ground_detection.ransac_iterations,
                distance_threshold: config.perception.lidar.ground_detection.distance_threshold,
                min_points: config.perception.lidar.ground_detection.min_points,
                height_threshold: config.perception.lidar.ground_detection.height_threshold,
            },
            clustering: crate::lidar::ClusteringConfig {
                cluster_tolerance: config.perception.lidar.clustering.cluster_tolerance,
                min_cluster_size: config.perception.lidar.clustering.min_cluster_size,
                max_cluster_size: config.perception.lidar.clustering.max_cluster_size,
                euclidean_clustering: config.perception.lidar.clustering.euclidean_clustering,
            },
        }
    }
    
    /// Create default configuration
    pub fn create_default_config() -> AutonomousVehicleConfig {
        AutonomousVehicleConfig {
            metadata: ConfigMetadata {
                version: "1.0.0".to_string(),
                created_at: chrono::Utc::now().format("%Y-%m-%d %H:%M:%S").to_string(),
                last_modified: chrono::Utc::now().format("%Y-%m-%d %H:%M:%S").to_string(),
                author: "Kenny AI System".to_string(),
                description: "Default autonomous vehicle configuration".to_string(),
                vehicle_model: "Generic AV".to_string(),
                deployment_environment: DeploymentEnvironment::Development,
            },
            vehicle: VehicleSystemConfig {
                vehicle_id: "AV_001".to_string(),
                make: "Generic".to_string(),
                model: "Autonomous Vehicle".to_string(),
                year: 2025,
                vin: None,
                license_plate: None,
                dimensions: VehicleDimensions {
                    length: 4.5,
                    width: 1.8,
                    height: 1.5,
                    wheelbase: 2.7,
                    track_width: 1.6,
                    ground_clearance: 0.15,
                    turning_radius: 5.5,
                },
                mass: VehicleMass {
                    curb_weight: 1500.0,
                    gross_weight: 2000.0,
                    payload_capacity: 500.0,
                    center_of_gravity: (1.2, 0.0, 0.6),
                },
                powertrain: PowertrainConfig {
                    type_: PowertrainType::Electric,
                    max_power: 150.0,
                    max_torque: 300.0,
                    transmission: TransmissionType::DirectDrive,
                    fuel_capacity: 60.0,
                    efficiency: 4.5,
                },
                autonomous_level: AutonomyLevel::Level4,
            },
            // ... (rest of the default configuration would be filled in)
            // For brevity, showing key sections only
            perception: PerceptionConfig {
                vision: VisionSystemConfig {
                    cameras: vec![
                        CameraConfig {
                            camera_id: 0,
                            name: "Front Camera".to_string(),
                            position: CameraPosition::Front,
                            mounting_location: (2.0, 0.0, 1.5),
                            orientation: (0.0, 0.0, 0.0),
                            resolution: (1920, 1080),
                            fps: 30.0,
                            fov_degrees: 60.0,
                            exposure_mode: ExposureMode::Auto,
                            auto_focus: true,
                        }
                    ],
                    calibration_file: "config/camera_calibration.yml".to_string(),
                    models_path: "models".to_string(),
                    detection_threshold: 0.5,
                    enable_gpu: true,
                    frame_rate: 30.0,
                    resolution: (1920, 1080),
                },
                // ... other perception configs
                lidar: LidarSystemConfig {
                    lidars: vec![],
                    point_cloud_processing: PointCloudProcessingConfig {
                        voxel_size: 0.1,
                        noise_filter_radius: 0.5,
                        noise_min_neighbors: 5,
                        intensity_threshold: 50.0,
                        remove_ground: true,
                        max_points_per_frame: 100000,
                    },
                    ground_detection: GroundDetectionConfig {
                        ransac_iterations: 1000,
                        distance_threshold: 0.1,
                        min_points: 100,
                        height_threshold: 0.3,
                        plane_angle_threshold: 0.1,
                    },
                    clustering: ClusteringConfig {
                        cluster_tolerance: 0.5,
                        min_cluster_size: 10,
                        max_cluster_size: 10000,
                        euclidean_clustering: true,
                        dbscan_eps: 0.3,
                        dbscan_min_points: 5,
                    },
                },
                radar: RadarSystemConfig {
                    radars: vec![],
                    enable_doppler: true,
                    max_range: 200.0,
                    angular_resolution: 1.0,
                    range_resolution: 0.1,
                },
                ultrasonic: UltrasonicSystemConfig {
                    sensors: vec![],
                    enable_parking_assist: true,
                    detection_threshold: 0.1,
                    max_range: 5.0,
                },
                gps: GpsSystemConfig {
                    receiver_type: GpsReceiverType::RTK,
                    rtk_enabled: true,
                    rtk_base_station: None,
                    update_rate_hz: 10.0,
                    accuracy_threshold: 0.1,
                    antenna_location: (0.0, 0.0, 1.8),
                },
                imu: ImuSystemConfig {
                    imu_type: ImuType::MEMS,
                    mounting_location: (0.0, 0.0, 0.5),
                    orientation: (0.0, 0.0, 0.0),
                    sample_rate_hz: 100.0,
                    accelerometer_range: 16.0,
                    gyroscope_range: 2000.0,
                    magnetometer_enabled: true,
                    temperature_compensation: true,
                },
                sensor_fusion: SensorFusionConfig {
                    fusion_algorithm: FusionAlgorithm::ExtendedKalmanFilter,
                    kalman_filter: KalmanFilterConfig {
                        process_noise: 0.1,
                        measurement_noise: 0.5,
                        initial_uncertainty: 1.0,
                        max_prediction_time: 0.5,
                    },
                    data_association: DataAssociationConfig {
                        gating_threshold: 3.0,
                        association_algorithm: AssociationAlgorithm::GlobalNearestNeighbor,
                        max_association_distance: 10.0,
                    },
                    track_management: TrackManagementConfig {
                        track_initiation_threshold: 3,
                        track_termination_threshold: 5,
                        max_missed_detections: 3,
                        max_track_age: 10.0,
                    },
                },
            },
            // ... (continue with other subsystem defaults)
            planning: PlanningSystemConfig {
                global_planner: GlobalPlannerConfig {
                    algorithm: GlobalPlanningAlgorithm::HybridAStar,
                    planning_horizon: 10.0,
                    planning_resolution: 0.5,
                    replanning_frequency: 1.0,
                    cost_weights: CostWeights {
                        distance: 1.0,
                        time: 1.5,
                        comfort: 2.0,
                        safety: 5.0,
                        fuel_efficiency: 1.2,
                        traffic_rules: 10.0,
                    },
                },
                local_planner: LocalPlannerConfig {
                    algorithm: LocalPlanningAlgorithm::OptimalControl,
                    planning_horizon: 5.0,
                    time_resolution: 0.1,
                    lateral_resolution: 0.1,
                    max_curvature: 0.2,
                    comfort_limits: ComfortLimits {
                        max_acceleration: 2.0,
                        max_deceleration: 6.0,
                        max_lateral_acceleration: 4.0,
                        max_jerk: 1.0,
                        max_angular_velocity: 1.0,
                    },
                },
                behavior_planner: BehaviorPlannerConfig {
                    state_machine: StateMachineConfig {
                        states: vec![],
                        transitions: vec![],
                        default_state: "cruise".to_string(),
                    },
                    decision_making: DecisionMakingConfig {
                        decision_algorithm: DecisionAlgorithm::RuleBased,
                        risk_assessment: RiskAssessmentConfig {
                            risk_threshold: 0.7,
                            time_horizons: vec![1.0, 3.0, 5.0],
                            risk_factors: vec![],
                        },
                        uncertainty_handling: UncertaintyHandlingConfig {
                            confidence_threshold: 0.8,
                            conservative_mode: true,
                            fallback_behavior: "safe_stop".to_string(),
                        },
                    },
                    maneuver_planning: ManeuverPlanningConfig {
                        lane_change: LaneChangeConfig {
                            min_gap_distance: 20.0,
                            min_gap_time: 3.0,
                            comfort_acceleration: 1.5,
                            max_lane_change_time: 5.0,
                        },
                        intersection: IntersectionConfig {
                            approach_speed: 8.0,
                            stop_line_buffer: 2.0,
                            yellow_light_behavior: YellowLightBehavior::Evaluate,
                            right_of_way_timeout: 5.0,
                        },
                        parking: ParkingConfig {
                            parallel_parking: true,
                            perpendicular_parking: true,
                            angle_parking: true,
                            min_parking_space: (5.5, 2.2),
                            parking_precision: 0.1,
                        },
                        emergency: EmergencyManeuverConfig {
                            emergency_braking: true,
                            emergency_steering: true,
                            collision_avoidance: true,
                            minimum_safe_distance: 2.0,
                        },
                    },
                },
                route_planner: RoutePlannerConfig {
                    map_provider: MapProvider::OpenStreetMap,
                    routing_algorithm: RoutingAlgorithm::AStar,
                    traffic_data_enabled: true,
                    real_time_updates: true,
                    route_preferences: RoutePreferences {
                        prefer_highways: false,
                        avoid_tolls: false,
                        avoid_ferries: true,
                        eco_routing: true,
                        route_optimization: RouteOptimization::Balanced,
                    },
                },
            },
            control: ControlSystemConfig {
                longitudinal_control: LongitudinalControlConfig {
                    controller_type: ControllerType::PID,
                    pid_params: PIDParams {
                        kp: 0.5,
                        ki: 0.05,
                        kd: 0.02,
                        integral_limit: 10.0,
                        derivative_filter: 0.1,
                    },
                    mpc_params: None,
                    speed_limits: SpeedLimits {
                        max_speed: 50.0,
                        max_acceleration: 3.0,
                        max_deceleration: 8.0,
                        emergency_deceleration: 9.8,
                    },
                },
                lateral_control: LateralControlConfig {
                    controller_type: ControllerType::PID,
                    pid_params: PIDParams {
                        kp: 1.0,
                        ki: 0.1,
                        kd: 0.05,
                        integral_limit: 10.0,
                        derivative_filter: 0.1,
                    },
                    stanley_params: Some(StanleyParams {
                        k_cross_track: 2.0,
                        k_heading: 1.0,
                        soft_bound: 1.0,
                    }),
                    pure_pursuit_params: Some(PurePursuitParams {
                        lookahead_distance: 10.0,
                        lookahead_time: 1.0,
                        min_lookahead: 5.0,
                        max_lookahead: 20.0,
                    }),
                    steering_limits: SteeringLimits {
                        max_steering_angle: 0.6,
                        max_steering_rate: 2.0,
                        max_steering_acceleration: 5.0,
                    },
                },
                actuator_control: ActuatorControlConfig {
                    throttle: ActuatorConfig {
                        response_time: 0.1,
                        deadband: 0.02,
                        saturation_limits: (0.0, 1.0),
                        calibration_curve: vec![],
                    },
                    brake: ActuatorConfig {
                        response_time: 0.05,
                        deadband: 0.01,
                        saturation_limits: (0.0, 1.0),
                        calibration_curve: vec![],
                    },
                    steering: ActuatorConfig {
                        response_time: 0.02,
                        deadband: 0.005,
                        saturation_limits: (-0.6, 0.6),
                        calibration_curve: vec![],
                    },
                    transmission: ActuatorConfig {
                        response_time: 0.5,
                        deadband: 0.0,
                        saturation_limits: (0.0, 4.0),
                        calibration_curve: vec![],
                    },
                },
                control_frequency: 50.0,
            },
            safety: SafetySystemConfig {
                monitoring_frequency: 50.0,
                fault_detection: FaultDetectionConfig {
                    sensor_timeout: 0.1,
                    actuator_timeout: 0.05,
                    communication_timeout: 0.2,
                    max_error_rate: 5.0,
                    watchdog_enabled: true,
                    diagnostic_frequency: 10.0,
                },
                collision_avoidance: CollisionAvoidanceConfig {
                    time_to_collision_warning: 3.0,
                    time_to_collision_critical: 1.0,
                    minimum_safe_distance: 2.0,
                    lateral_clearance: 0.5,
                    emergency_brake_threshold: 9.8,
                },
                emergency_response: EmergencyResponseConfig {
                    enable_emergency_brake: true,
                    enable_emergency_steering: true,
                    enable_hazard_lights: true,
                    enable_emergency_communication: true,
                    safe_stop_procedure: SafeStopProcedure::ControlledStop,
                },
                redundancy: RedundancyConfig {
                    sensor_redundancy: true,
                    actuator_redundancy: false,
                    processor_redundancy: false,
                    communication_redundancy: true,
                    power_redundancy: false,
                },
            },
            communication: CommunicationSystemConfig {
                v2x: V2XSystemConfig {
                    enabled: true,
                    dsrc_enabled: true,
                    cv2x_enabled: true,
                    broadcast_frequency: 10.0,
                    communication_range: 1000.0,
                    encryption_enabled: true,
                    message_priorities: MessagePriorities {
                        emergency: 0,
                        safety: 1,
                        traffic: 3,
                        infotainment: 5,
                    },
                },
                cellular: CellularConfig {
                    enabled: true,
                    provider: "carrier".to_string(),
                    apn: "v2x.carrier.com".to_string(),
                    data_limit: Some(10_000_000_000), // 10GB
                    roaming_enabled: false,
                },
                wifi: WiFiConfig {
                    enabled: true,
                    auto_connect: true,
                    preferred_networks: vec![],
                    hotspot_mode: false,
                },
                bluetooth: BluetoothConfig {
                    enabled: true,
                    discoverable: false,
                    auto_pairing: false,
                    supported_profiles: vec![BluetoothProfile::HFP, BluetoothProfile::A2DP],
                },
                can_bus: CanBusConfig {
                    interfaces: vec![
                        CanInterface {
                            name: "can0".to_string(),
                            enabled: true,
                            filters: vec![],
                        }
                    ],
                    baudrate: 500000,
                    extended_frames: true,
                    error_handling: CanErrorHandling::Log,
                },
            },
            logging: LoggingConfig {
                log_level: LogLevel::Info,
                log_destinations: vec![
                    LogDestination {
                        name: "console".to_string(),
                        type_: LogDestinationType::Console,
                        enabled: true,
                        format: LogFormat::Plain,
                        filters: vec![],
                    },
                    LogDestination {
                        name: "file".to_string(),
                        type_: LogDestinationType::File,
                        enabled: true,
                        format: LogFormat::JSON,
                        filters: vec![],
                    }
                ],
                rotation: LogRotation {
                    enabled: true,
                    max_file_size: 100_000_000, // 100MB
                    max_files: 10,
                    rotation_frequency: RotationFrequency::Daily,
                },
                data_retention: DataRetention {
                    sensor_data_days: 7,
                    log_data_days: 30,
                    video_data_days: 3,
                    diagnostic_data_days: 90,
                    auto_cleanup: true,
                },
                privacy: PrivacyConfig {
                    anonymize_location: false,
                    encrypt_sensitive_data: true,
                    data_sharing_consent: false,
                    pii_detection: true,
                },
            },
            performance: PerformanceConfig {
                system_monitoring: SystemMonitoringConfig {
                    enabled: true,
                    monitoring_frequency: 1.0,
                    cpu_threshold: 80.0,
                    memory_threshold: 85.0,
                    disk_threshold: 90.0,
                    temperature_threshold: 80.0,
                },
                resource_limits: ResourceLimits {
                    max_cpu_usage: 90.0,
                    max_memory_usage: 8_000_000_000, // 8GB
                    max_disk_usage: 100_000_000_000, // 100GB
                    max_network_bandwidth: 1_000_000_000, // 1Gbps
                    max_concurrent_tasks: 100,
                },
                optimization: OptimizationConfig {
                    enable_compiler_optimizations: true,
                    enable_gpu_acceleration: true,
                    enable_caching: true,
                    cache_size_limit: 1_000_000_000, // 1GB
                    parallel_processing: true,
                    thread_pool_size: 8,
                },
                profiling: ProfilingConfig {
                    enabled: false,
                    profile_frequency: 0.1,
                    profile_duration: 60.0,
                    output_format: ProfileFormat::FlameGraph,
                    components_to_profile: vec![],
                },
            },
            calibration: CalibrationConfig {
                camera_calibration: CameraCalibrationConfig {
                    intrinsic_calibration: true,
                    extrinsic_calibration: true,
                    stereo_calibration: false,
                    calibration_target: CalibrationTarget::Checkerboard,
                    calibration_frequency: CalibrationFrequency::Weekly,
                },
                lidar_calibration: LidarCalibrationConfig {
                    intensity_calibration: true,
                    range_calibration: true,
                    multi_lidar_calibration: false,
                    ground_plane_calibration: true,
                },
                imu_calibration: ImuCalibrationConfig {
                    accelerometer_calibration: true,
                    gyroscope_calibration: true,
                    magnetometer_calibration: true,
                    temperature_compensation: true,
                },
                wheel_calibration: WheelCalibrationConfig {
                    wheel_radius_calibration: true,
                    wheelbase_calibration: true,
                    track_width_calibration: true,
                    odometry_calibration: true,
                },
                auto_calibration: AutoCalibrationConfig {
                    enabled: true,
                    calibration_triggers: vec![
                        CalibrationTrigger::TimeInterval,
                        CalibrationTrigger::PerformanceDegradation,
                    ],
                    validation_threshold: 0.95,
                    backup_calibration: true,
                },
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    
    #[tokio::test]
    async fn test_config_creation_and_validation() {
        let config = ConfigurationManager::create_default_config();
        let result = ConfigurationManager::validate_config(&config);
        assert!(result.is_ok());
    }
    
    #[tokio::test]
    async fn test_config_save_and_load() {
        let config = ConfigurationManager::create_default_config();
        
        // Create temporary file
        let temp_file = NamedTempFile::new().unwrap();
        let temp_path = temp_file.path();
        
        // Test JSON format
        let json_content = serde_json::to_string_pretty(&config).unwrap();
        tokio::fs::write(temp_path, json_content).await.unwrap();
        
        let loaded_config = ConfigurationManager::load_config(temp_path).await.unwrap();
        assert_eq!(config.vehicle.vehicle_id, loaded_config.vehicle.vehicle_id);
    }
    
    #[tokio::test]
    async fn test_configuration_manager() {
        let config = ConfigurationManager::create_default_config();
        
        // Create temporary file
        let temp_file = NamedTempFile::new().unwrap();
        let temp_path = temp_file.path();
        
        // Write initial config
        let json_content = serde_json::to_string_pretty(&config).unwrap();
        tokio::fs::write(temp_path, json_content).await.unwrap();
        
        // Create configuration manager
        let manager = ConfigurationManager::new(temp_path).await.unwrap();
        
        // Test getting configuration
        let retrieved_config = manager.get_config().await;
        assert_eq!(config.vehicle.vehicle_id, retrieved_config.vehicle.vehicle_id);
    }
    
    #[test]
    fn test_config_validation_failures() {
        let mut config = ConfigurationManager::create_default_config();
        
        // Test empty vehicle ID
        config.vehicle.vehicle_id = "".to_string();
        assert!(ConfigurationManager::validate_config(&config).is_err());
        
        // Reset and test invalid dimensions
        config = ConfigurationManager::create_default_config();
        config.vehicle.dimensions.length = -1.0;
        assert!(ConfigurationManager::validate_config(&config).is_err());
        
        // Reset and test invalid monitoring frequency
        config = ConfigurationManager::create_default_config();
        config.safety.monitoring_frequency = -1.0;
        assert!(ConfigurationManager::validate_config(&config).is_err());
    }
}