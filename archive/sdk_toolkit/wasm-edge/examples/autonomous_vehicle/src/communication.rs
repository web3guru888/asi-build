/*!
# Communication Module

V2X (Vehicle-to-Everything) communication system for autonomous vehicles.
Provides V2V, V2I, V2P, and V2N communication capabilities with edge AI integration.
*/

use anyhow::{Context, Result};
use log::{info, warn, error};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::net::{IpAddr, SocketAddr};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tokio::net::UdpSocket;
use tokio::sync::{broadcast, mpsc, RwLock};
use tokio::time::interval;
use wasm_edge_ai_sdk::prelude::*;

use crate::{DetectedObject, VehicleState, SafetyWarning, Pose2D};

/// V2X communication configuration
#[derive(Debug, Clone)]
pub struct V2XConfig {
    pub vehicle_id: String,
    pub communication_range: f64,        // meters
    pub broadcast_interval_ms: u64,
    pub message_retention_ms: u64,
    pub encryption_enabled: bool,
    pub protocols: ProtocolConfig,
    pub message_priorities: MessagePriorities,
    pub network_config: NetworkConfig,
}

#[derive(Debug, Clone)]
pub struct ProtocolConfig {
    pub dsrc_enabled: bool,              // Dedicated Short Range Communications
    pub cv2x_enabled: bool,              // Cellular V2X
    pub wifi_enabled: bool,              // IEEE 802.11p
    pub ethernet_enabled: bool,          // Wired backbone
    pub can_bus_enabled: bool,           // CAN bus integration
}

#[derive(Debug, Clone)]
pub struct MessagePriorities {
    pub emergency_priority: u8,          // 0-7, 0 = highest
    pub safety_priority: u8,
    pub traffic_priority: u8,
    pub infotainment_priority: u8,
    pub maintenance_priority: u8,
}

#[derive(Debug, Clone)]
pub struct NetworkConfig {
    pub dsrc_frequency: f64,             // MHz
    pub cellular_apn: String,
    pub wifi_ssid: String,
    pub ethernet_interface: String,
    pub can_interface: String,
    pub multicast_address: IpAddr,
    pub unicast_port: u16,
    pub broadcast_port: u16,
}

/// V2X message types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum V2XMessage {
    // Vehicle-to-Vehicle (V2V)
    BasicSafetyMessage(BasicSafetyMessage),
    EmergencyVehicleAlert(EmergencyVehicleAlert),
    IntersectionMovementAssist(IntersectionMovementAssist),
    BlindSpotWarning(BlindSpotWarning),
    ForwardCollisionWarning(ForwardCollisionWarning),
    
    // Vehicle-to-Infrastructure (V2I)
    SignalPhaseAndTiming(SignalPhaseAndTiming),
    RoadSideAlert(RoadSideAlert),
    TrafficInformationMessage(TrafficInformationMessage),
    ParkingInformation(ParkingInformation),
    
    // Vehicle-to-Pedestrian (V2P)
    PedestrianSafetyMessage(PedestrianSafetyMessage),
    VulnerableRoadUserAlert(VulnerableRoadUserAlert),
    
    // Vehicle-to-Network (V2N)
    WeatherInformation(WeatherInformation),
    TrafficFlowOptimization(TrafficFlowOptimization),
    RemoteDiagnostics(RemoteDiagnostics),
    OverTheAirUpdate(OverTheAirUpdate),
}

/// Basic Safety Message (BSM) - Core V2V message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BasicSafetyMessage {
    pub message_id: String,
    pub timestamp: u64,
    pub vehicle_id: String,
    pub position: Position,
    pub motion: MotionState,
    pub vehicle_size: VehicleSize,
    pub basic_vehicle_class: VehicleClass,
    pub vehicle_safety_extensions: Option<VehicleSafetyExtensions>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub latitude: f64,      // degrees
    pub longitude: f64,     // degrees
    pub elevation: f64,     // meters
    pub heading: f64,       // degrees (0-359)
    pub accuracy: f64,      // meters
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MotionState {
    pub speed: f64,         // m/s
    pub acceleration: f64,  // m/s²
    pub yaw_rate: f64,      // deg/s
    pub steering_angle: f64, // degrees
    pub brake_status: BrakeStatus,
    pub throttle_position: f64, // 0-100%
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VehicleSize {
    pub length: f64,        // meters
    pub width: f64,         // meters
    pub height: f64,        // meters
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum VehicleClass {
    Motorcycle,
    PassengerCar,
    LightTruck,
    HeavyTruck,
    Transit,
    Emergency,
    Maintenance,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum BrakeStatus {
    Unavailable,
    Off,
    On,
    EngagedPartially,
    EngagedFully,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VehicleSafetyExtensions {
    pub path_history: Vec<PathHistoryPoint>,
    pub path_prediction: Vec<PathPredictionPoint>,
    pub hazard_lights: bool,
    pub abs_active: bool,
    pub traction_control_active: bool,
    pub stability_control_active: bool,
    pub airbag_status: AirbagStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathHistoryPoint {
    pub latitude_offset: f64,    // meters from current position
    pub longitude_offset: f64,   // meters from current position
    pub time_offset: f64,        // seconds ago
    pub speed: f64,              // m/s
    pub heading: f64,            // degrees
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathPredictionPoint {
    pub latitude_offset: f64,    // meters from current position
    pub longitude_offset: f64,   // meters from current position
    pub time_offset: f64,        // seconds in future
    pub confidence: f64,         // 0-1
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AirbagStatus {
    pub driver_deployed: bool,
    pub passenger_deployed: bool,
    pub side_deployed: bool,
}

/// Emergency Vehicle Alert
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmergencyVehicleAlert {
    pub message_id: String,
    pub timestamp: u64,
    pub vehicle_id: String,
    pub emergency_type: EmergencyVehicleType,
    pub response_type: EmergencyResponseType,
    pub position: Position,
    pub destination: Option<Position>,
    pub estimated_arrival: Option<u64>,
    pub lane_clearance_requested: Vec<u8>, // Lane numbers
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum EmergencyVehicleType {
    Fire,
    Police,
    Ambulance,
    Emergency,
    Maintenance,
    Utility,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum EmergencyResponseType {
    Emergency,
    NonEmergency,
    Exercise,
}

/// Signal Phase and Timing (SPAT) message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignalPhaseAndTiming {
    pub message_id: String,
    pub timestamp: u64,
    pub intersection_id: u32,
    pub signal_groups: Vec<SignalGroup>,
    pub regional_extensions: Option<HashMap<String, String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignalGroup {
    pub signal_group_id: u8,
    pub state: SignalState,
    pub time_remaining: Option<u16>, // seconds
    pub time_to_change: Option<u16>, // seconds
    pub confidence: u8,              // 0-15
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SignalState {
    Unavailable,
    Dark,
    StopThenProceed,
    StopAndRemain,
    PreMovement,
    PermissiveMovementAllowed,
    ProtectedMovementAllowed,
    PermissiveClearance,
    ProtectedClearance,
    CautionConflictingTraffic,
}

/// Road Side Alert
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoadSideAlert {
    pub message_id: String,
    pub timestamp: u64,
    pub alert_type: RoadSideAlertType,
    pub location: Position,
    pub affected_lanes: Vec<u8>,
    pub description: String,
    pub severity: AlertSeverity,
    pub expected_duration: Option<u64>, // seconds
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum RoadSideAlertType {
    Accident,
    Construction,
    HazardousMaterial,
    IncidentZone,
    WeatherCondition,
    RoadClosure,
    TrafficJam,
    EmergencyVehicles,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, PartialOrd)]
pub enum AlertSeverity {
    Info,
    Warning,
    Critical,
    Emergency,
}

/// Pedestrian Safety Message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PedestrianSafetyMessage {
    pub message_id: String,
    pub timestamp: u64,
    pub pedestrian_id: String,
    pub position: Position,
    pub velocity: Velocity,
    pub pedestrian_type: PedestrianType,
    pub activity: PedestrianActivity,
    pub crossing_intention: Option<CrossingIntention>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Velocity {
    pub speed: f64,         // m/s
    pub heading: f64,       // degrees
    pub vertical_speed: f64, // m/s (climbing/descending)
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum PedestrianType {
    Pedestrian,
    Cyclist,
    Wheelchair,
    Stroller,
    PersonalMobilityDevice,
    Animal,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum PedestrianActivity {
    Walking,
    Running,
    Stationary,
    Cycling,
    Crossing,
    WaitingToCross,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrossingIntention {
    pub intends_to_cross: bool,
    pub crossing_direction: f64, // degrees
    pub confidence: f64,         // 0-1
    pub time_to_crossing: Option<f64>, // seconds
}

/// Communication statistics
#[derive(Debug, Default, Clone)]
pub struct CommunicationStats {
    pub messages_sent: u64,
    pub messages_received: u64,
    pub messages_dropped: u64,
    pub bytes_transmitted: u64,
    pub bytes_received: u64,
    pub average_latency_ms: f64,
    pub packet_loss_rate: f64,
    pub active_connections: u32,
    pub last_update: Option<Instant>,
}

/// Main V2X communication system
pub struct V2XCommunicationSystem {
    config: V2XConfig,
    vehicle_state: RwLock<VehicleState>,
    received_messages: RwLock<HashMap<String, (V2XMessage, Instant)>>,
    communication_stats: RwLock<CommunicationStats>,
    
    // Communication channels
    outbound_tx: mpsc::UnboundedSender<V2XMessage>,
    inbound_rx: mpsc::UnboundedReceiver<V2XMessage>,
    alert_tx: broadcast::Sender<V2XAlert>,
    
    // Network interfaces
    dsrc_socket: Option<UdpSocket>,
    cellular_interface: Option<CellularInterface>,
    wifi_socket: Option<UdpSocket>,
    can_interface: Option<CanInterface>,
    
    // Background tasks
    broadcast_handle: Option<tokio::task::JoinHandle<()>>,
    receive_handle: Option<tokio::task::JoinHandle<()>>,
    cleanup_handle: Option<tokio::task::JoinHandle<()>>,
}

/// V2X alerts generated from received messages
#[derive(Debug, Clone)]
pub enum V2XAlert {
    CollisionWarning {
        other_vehicle_id: String,
        time_to_collision: f64,
        collision_point: Position,
        severity: AlertSeverity,
    },
    EmergencyVehicleApproaching {
        vehicle_id: String,
        vehicle_type: EmergencyVehicleType,
        estimated_arrival: f64,
        requested_action: String,
    },
    TrafficSignalChange {
        intersection_id: u32,
        signal_group: u8,
        new_state: SignalState,
        time_remaining: Option<u16>,
    },
    RoadHazard {
        alert_type: RoadSideAlertType,
        location: Position,
        distance: f64,
        severity: AlertSeverity,
    },
    PedestrianAlert {
        pedestrian_id: String,
        location: Position,
        crossing_intention: bool,
        time_to_crossing: Option<f64>,
    },
}

/// Network interface implementations
struct CellularInterface {
    apn: String,
    signal_strength: i8, // dBm
    network_type: String, // "4G", "5G", etc.
    data_usage: u64,     // bytes
}

struct CanInterface {
    interface_name: String,
    bitrate: u32,
    error_count: u32,
    message_count: u64,
}

impl V2XCommunicationSystem {
    /// Create new V2X communication system
    pub async fn new(config: V2XConfig) -> Result<Self> {
        info!("Initializing V2X communication system for vehicle: {}", config.vehicle_id);
        
        let (outbound_tx, outbound_rx) = mpsc::unbounded_channel();
        let (inbound_tx, inbound_rx) = mpsc::unbounded_channel();
        let (alert_tx, _) = broadcast::channel(100);
        
        // Initialize network interfaces based on configuration
        let dsrc_socket = if config.protocols.dsrc_enabled {
            Some(Self::init_dsrc_socket(&config.network_config).await?)
        } else {
            None
        };
        
        let cellular_interface = if config.protocols.cv2x_enabled {
            Some(Self::init_cellular_interface(&config.network_config).await?)
        } else {
            None
        };
        
        let wifi_socket = if config.protocols.wifi_enabled {
            Some(Self::init_wifi_socket(&config.network_config).await?)
        } else {
            None
        };
        
        let can_interface = if config.protocols.can_bus_enabled {
            Some(Self::init_can_interface(&config.network_config).await?)
        } else {
            None
        };
        
        let initial_vehicle_state = VehicleState {
            position: (0.0, 0.0),
            heading: 0.0,
            speed: 0.0,
            acceleration: 0.0,
            steering_angle: 0.0,
            wheel_speeds: [0.0; 4],
            throttle_position: 0.0,
            brake_pressure: 0.0,
            gear: crate::vehicle_control::GearState::Park,
            engine_rpm: 0.0,
            fuel_level: 1.0,
            battery_voltage: 12.0,
            timestamp: Instant::now(),
        };
        
        Ok(Self {
            config,
            vehicle_state: RwLock::new(initial_vehicle_state),
            received_messages: RwLock::new(HashMap::new()),
            communication_stats: RwLock::new(CommunicationStats::default()),
            outbound_tx,
            inbound_rx,
            alert_tx,
            dsrc_socket,
            cellular_interface,
            wifi_socket,
            can_interface,
            broadcast_handle: None,
            receive_handle: None,
            cleanup_handle: None,
        })
    }
    
    /// Start V2X communication
    pub async fn start(&mut self) -> Result<()> {
        info!("Starting V2X communication system");
        
        // Start broadcast task
        self.start_broadcast_task().await?;
        
        // Start receive task
        self.start_receive_task().await?;
        
        // Start cleanup task
        self.start_cleanup_task().await?;
        
        Ok(())
    }
    
    /// Stop V2X communication
    pub async fn stop(&mut self) -> Result<()> {
        info!("Stopping V2X communication system");
        
        // Stop background tasks
        if let Some(handle) = self.broadcast_handle.take() {
            handle.abort();
        }
        if let Some(handle) = self.receive_handle.take() {
            handle.abort();
        }
        if let Some(handle) = self.cleanup_handle.take() {
            handle.abort();
        }
        
        Ok(())
    }
    
    /// Update vehicle state for broadcasting
    pub async fn update_vehicle_state(&self, state: VehicleState) -> Result<()> {
        let mut vehicle_state = self.vehicle_state.write().await;
        *vehicle_state = state;
        Ok(())
    }
    
    /// Send V2X message
    pub async fn send_message(&self, message: V2XMessage) -> Result<()> {
        self.outbound_tx.send(message)
            .context("Failed to queue outbound message")?;
        
        // Update statistics
        {
            let mut stats = self.communication_stats.write().await;
            stats.messages_sent += 1;
            stats.last_update = Some(Instant::now());
        }
        
        Ok(())
    }
    
    /// Get received messages of specific type
    pub async fn get_received_messages<T>(&self) -> Vec<T> 
    where
        T: Clone + for<'de> Deserialize<'de>,
    {
        let messages = self.received_messages.read().await;
        let mut result = Vec::new();
        
        for (message, _timestamp) in messages.values() {
            // This is simplified - in practice would need proper type matching
            // For now, return empty vector
        }
        
        result
    }
    
    /// Subscribe to V2X alerts
    pub fn subscribe_alerts(&self) -> broadcast::Receiver<V2XAlert> {
        self.alert_tx.subscribe()
    }
    
    /// Get communication statistics
    pub async fn get_stats(&self) -> CommunicationStats {
        self.communication_stats.read().await.clone()
    }
    
    /// Process safety-critical messages for immediate alerts
    pub async fn process_safety_message(&self, message: &V2XMessage) -> Result<()> {
        match message {
            V2XMessage::EmergencyVehicleAlert(alert) => {
                let vehicle_state = self.vehicle_state.read().await;
                let distance = self.calculate_distance(
                    &self.vehicle_state_to_position(&vehicle_state),
                    &alert.position,
                );
                
                if distance < self.config.communication_range {
                    let time_to_arrival = alert.estimated_arrival
                        .map(|eta| eta as f64 / 1000.0) // Convert to seconds
                        .unwrap_or(60.0);
                    
                    let v2x_alert = V2XAlert::EmergencyVehicleApproaching {
                        vehicle_id: alert.vehicle_id.clone(),
                        vehicle_type: alert.emergency_type.clone(),
                        estimated_arrival: time_to_arrival,
                        requested_action: format!("Clear lanes: {:?}", alert.lane_clearance_requested),
                    };
                    
                    let _ = self.alert_tx.send(v2x_alert);
                }
            },
            
            V2XMessage::BasicSafetyMessage(bsm) => {
                if let Some(collision_alert) = self.check_collision_risk(bsm).await? {
                    let _ = self.alert_tx.send(collision_alert);
                }
            },
            
            V2XMessage::RoadSideAlert(alert) => {
                let vehicle_state = self.vehicle_state.read().await;
                let distance = self.calculate_distance(
                    &self.vehicle_state_to_position(&vehicle_state),
                    &alert.location,
                );
                
                if distance < 1000.0 { // 1km alert range
                    let v2x_alert = V2XAlert::RoadHazard {
                        alert_type: alert.alert_type.clone(),
                        location: alert.location.clone(),
                        distance,
                        severity: alert.severity.clone(),
                    };
                    
                    let _ = self.alert_tx.send(v2x_alert);
                }
            },
            
            V2XMessage::PedestrianSafetyMessage(psm) => {
                let vehicle_state = self.vehicle_state.read().await;
                let distance = self.calculate_distance(
                    &self.vehicle_state_to_position(&vehicle_state),
                    &psm.position,
                );
                
                if distance < 50.0 { // 50m pedestrian alert range
                    let crossing_intention = psm.crossing_intention
                        .as_ref()
                        .map(|ci| ci.intends_to_cross)
                        .unwrap_or(false);
                    
                    let time_to_crossing = psm.crossing_intention
                        .as_ref()
                        .and_then(|ci| ci.time_to_crossing);
                    
                    let v2x_alert = V2XAlert::PedestrianAlert {
                        pedestrian_id: psm.pedestrian_id.clone(),
                        location: psm.position.clone(),
                        crossing_intention,
                        time_to_crossing,
                    };
                    
                    let _ = self.alert_tx.send(v2x_alert);
                }
            },
            
            _ => {
                // Other message types processed in background
            }
        }
        
        Ok(())
    }
    
    // Internal implementation methods
    
    async fn start_broadcast_task(&mut self) -> Result<()> {
        let vehicle_state = self.vehicle_state.clone();
        let outbound_tx = self.outbound_tx.clone();
        let config = self.config.clone();
        let stats = self.communication_stats.clone();
        
        let broadcast_handle = tokio::spawn(async move {
            let mut interval_timer = interval(Duration::from_millis(config.broadcast_interval_ms));
            
            loop {
                interval_timer.tick().await;
                
                // Generate and send Basic Safety Message
                if let Ok(bsm) = Self::generate_basic_safety_message(&vehicle_state, &config).await {
                    if let Err(e) = outbound_tx.send(V2XMessage::BasicSafetyMessage(bsm)) {
                        error!("Failed to send BSM: {}", e);
                    } else {
                        let mut stats_guard = stats.write().await;
                        stats_guard.messages_sent += 1;
                    }
                }
            }
        });
        
        self.broadcast_handle = Some(broadcast_handle);
        Ok(())
    }
    
    async fn start_receive_task(&mut self) -> Result<()> {
        // This would be implemented to receive from actual network interfaces
        // For now, create a placeholder task
        
        let received_messages = self.received_messages.clone();
        let alert_tx = self.alert_tx.clone();
        let stats = self.communication_stats.clone();
        
        let receive_handle = tokio::spawn(async move {
            // Simulate receiving messages
            let mut interval_timer = interval(Duration::from_secs(5));
            
            loop {
                interval_timer.tick().await;
                
                // Simulate processing received messages
                let mut stats_guard = stats.write().await;
                stats_guard.messages_received += 1;
            }
        });
        
        self.receive_handle = Some(receive_handle);
        Ok(())
    }
    
    async fn start_cleanup_task(&mut self) -> Result<()> {
        let received_messages = self.received_messages.clone();
        let retention_duration = Duration::from_millis(self.config.message_retention_ms);
        
        let cleanup_handle = tokio::spawn(async move {
            let mut interval_timer = interval(Duration::from_secs(10)); // Cleanup every 10 seconds
            
            loop {
                interval_timer.tick().await;
                
                let now = Instant::now();
                let mut messages = received_messages.write().await;
                
                // Remove expired messages
                messages.retain(|_, (_, timestamp)| {
                    now.duration_since(*timestamp) < retention_duration
                });
            }
        });
        
        self.cleanup_handle = Some(cleanup_handle);
        Ok(())
    }
    
    async fn generate_basic_safety_message(
        vehicle_state: &RwLock<VehicleState>,
        config: &V2XConfig,
    ) -> Result<BasicSafetyMessage> {
        let state = vehicle_state.read().await;
        let timestamp = SystemTime::now().duration_since(UNIX_EPOCH)?.as_millis() as u64;
        
        let position = Position {
            latitude: state.position.0,  // Would be actual GPS coordinates
            longitude: state.position.1,
            elevation: 0.0,              // Would be from GPS/altimeter
            heading: state.heading.to_degrees(),
            accuracy: 2.0,               // GPS accuracy in meters
        };
        
        let motion = MotionState {
            speed: state.speed,
            acceleration: state.acceleration,
            yaw_rate: 0.0,               // Would be from gyroscope
            steering_angle: state.steering_angle.to_degrees(),
            brake_status: if state.brake_pressure > 0.1 {
                BrakeStatus::On
            } else {
                BrakeStatus::Off
            },
            throttle_position: state.throttle_position * 100.0, // Convert to percentage
        };
        
        let vehicle_size = VehicleSize {
            length: 4.5,  // Would be from vehicle configuration
            width: 1.8,
            height: 1.5,
        };
        
        Ok(BasicSafetyMessage {
            message_id: format!("{}_{}", config.vehicle_id, timestamp),
            timestamp,
            vehicle_id: config.vehicle_id.clone(),
            position,
            motion,
            vehicle_size,
            basic_vehicle_class: VehicleClass::PassengerCar,
            vehicle_safety_extensions: None, // Would include path history/prediction
        })
    }
    
    async fn check_collision_risk(&self, bsm: &BasicSafetyMessage) -> Result<Option<V2XAlert>> {
        let vehicle_state = self.vehicle_state.read().await;
        let our_position = self.vehicle_state_to_position(&vehicle_state);
        
        // Calculate distance to other vehicle
        let distance = self.calculate_distance(&our_position, &bsm.position);
        
        if distance < 100.0 { // Only check vehicles within 100m
            // Simple collision prediction
            let relative_speed = (vehicle_state.speed - bsm.motion.speed).abs();
            
            if relative_speed > 0.1 && distance > 0.1 {
                let time_to_collision = distance / relative_speed;
                
                if time_to_collision < 5.0 { // 5 second warning threshold
                    let severity = if time_to_collision < 2.0 {
                        AlertSeverity::Critical
                    } else {
                        AlertSeverity::Warning
                    };
                    
                    return Ok(Some(V2XAlert::CollisionWarning {
                        other_vehicle_id: bsm.vehicle_id.clone(),
                        time_to_collision,
                        collision_point: bsm.position.clone(),
                        severity,
                    }));
                }
            }
        }
        
        Ok(None)
    }
    
    fn vehicle_state_to_position(&self, state: &VehicleState) -> Position {
        Position {
            latitude: state.position.0,
            longitude: state.position.1,
            elevation: 0.0,
            heading: state.heading.to_degrees(),
            accuracy: 2.0,
        }
    }
    
    fn calculate_distance(&self, pos1: &Position, pos2: &Position) -> f64 {
        // Simplified distance calculation
        // In reality, would use proper geospatial calculations
        let dx = pos1.latitude - pos2.latitude;
        let dy = pos1.longitude - pos2.longitude;
        ((dx * dx + dy * dy).sqrt()) * 111000.0 // Rough conversion to meters
    }
    
    // Network interface initialization methods
    
    async fn init_dsrc_socket(config: &NetworkConfig) -> Result<UdpSocket> {
        let addr = SocketAddr::new(config.multicast_address, config.broadcast_port);
        let socket = UdpSocket::bind(addr).await
            .context("Failed to bind DSRC socket")?;
        
        info!("DSRC socket initialized on {}", addr);
        Ok(socket)
    }
    
    async fn init_cellular_interface(config: &NetworkConfig) -> Result<CellularInterface> {
        // Initialize cellular interface
        info!("Initializing cellular interface with APN: {}", config.cellular_apn);
        
        Ok(CellularInterface {
            apn: config.cellular_apn.clone(),
            signal_strength: -70, // dBm
            network_type: "5G".to_string(),
            data_usage: 0,
        })
    }
    
    async fn init_wifi_socket(config: &NetworkConfig) -> Result<UdpSocket> {
        let addr = SocketAddr::new("0.0.0.0".parse().unwrap(), config.unicast_port);
        let socket = UdpSocket::bind(addr).await
            .context("Failed to bind WiFi socket")?;
        
        info!("WiFi socket initialized on {}", addr);
        Ok(socket)
    }
    
    async fn init_can_interface(config: &NetworkConfig) -> Result<CanInterface> {
        // Initialize CAN interface
        info!("Initializing CAN interface: {}", config.can_interface);
        
        Ok(CanInterface {
            interface_name: config.can_interface.clone(),
            bitrate: 500000, // 500 kbps
            error_count: 0,
            message_count: 0,
        })
    }
}

impl Default for V2XConfig {
    fn default() -> Self {
        Self {
            vehicle_id: "AV001".to_string(),
            communication_range: 1000.0,    // 1km
            broadcast_interval_ms: 100,     // 10 Hz
            message_retention_ms: 5000,     // 5 seconds
            encryption_enabled: true,
            protocols: ProtocolConfig {
                dsrc_enabled: true,
                cv2x_enabled: true,
                wifi_enabled: true,
                ethernet_enabled: false,
                can_bus_enabled: true,
            },
            message_priorities: MessagePriorities {
                emergency_priority: 0,      // Highest
                safety_priority: 1,
                traffic_priority: 3,
                infotainment_priority: 5,
                maintenance_priority: 7,    // Lowest
            },
            network_config: NetworkConfig {
                dsrc_frequency: 5905.0,     // MHz
                cellular_apn: "v2x.operator.com".to_string(),
                wifi_ssid: "V2X_Network".to_string(),
                ethernet_interface: "eth0".to_string(),
                can_interface: "can0".to_string(),
                multicast_address: "239.255.1.1".parse().unwrap(),
                unicast_port: 4001,
                broadcast_port: 4002,
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_v2x_system_creation() {
        let config = V2XConfig::default();
        let system = V2XCommunicationSystem::new(config).await;
        assert!(system.is_ok());
    }
    
    #[tokio::test]
    async fn test_basic_safety_message_generation() {
        let vehicle_state = RwLock::new(VehicleState {
            position: (37.7749, -122.4194), // San Francisco coordinates
            heading: 0.0,
            speed: 15.0,
            acceleration: 0.0,
            steering_angle: 0.0,
            wheel_speeds: [250.0; 4],
            throttle_position: 0.3,
            brake_pressure: 0.0,
            gear: crate::vehicle_control::GearState::Drive,
            engine_rpm: 2000.0,
            fuel_level: 0.75,
            battery_voltage: 12.6,
            timestamp: Instant::now(),
        });
        
        let config = V2XConfig::default();
        let bsm = V2XCommunicationSystem::generate_basic_safety_message(&vehicle_state, &config).await;
        
        assert!(bsm.is_ok());
        let bsm = bsm.unwrap();
        assert_eq!(bsm.vehicle_id, config.vehicle_id);
        assert_eq!(bsm.motion.speed, 15.0);
    }
    
    #[test]
    fn test_distance_calculation() {
        let config = V2XConfig::default();
        let system = V2XCommunicationSystem {
            config: config.clone(),
            vehicle_state: RwLock::new(VehicleState {
                position: (0.0, 0.0),
                heading: 0.0,
                speed: 0.0,
                acceleration: 0.0,
                steering_angle: 0.0,
                wheel_speeds: [0.0; 4],
                throttle_position: 0.0,
                brake_pressure: 0.0,
                gear: crate::vehicle_control::GearState::Park,
                engine_rpm: 0.0,
                fuel_level: 1.0,
                battery_voltage: 12.0,
                timestamp: Instant::now(),
            }),
            received_messages: RwLock::new(HashMap::new()),
            communication_stats: RwLock::new(CommunicationStats::default()),
            outbound_tx: mpsc::unbounded_channel().0,
            inbound_rx: mpsc::unbounded_channel().1,
            alert_tx: broadcast::channel(10).0,
            dsrc_socket: None,
            cellular_interface: None,
            wifi_socket: None,
            can_interface: None,
            broadcast_handle: None,
            receive_handle: None,
            cleanup_handle: None,
        };
        
        let pos1 = Position {
            latitude: 0.0,
            longitude: 0.0,
            elevation: 0.0,
            heading: 0.0,
            accuracy: 1.0,
        };
        
        let pos2 = Position {
            latitude: 0.001, // ~111 meters
            longitude: 0.0,
            elevation: 0.0,
            heading: 0.0,
            accuracy: 1.0,
        };
        
        let distance = system.calculate_distance(&pos1, &pos2);
        assert!(distance > 100.0 && distance < 120.0); // Should be approximately 111 meters
    }
}