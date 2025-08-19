/*!
# Vehicle Control Module

Low-level vehicle control interface for autonomous vehicle actuation.
Provides steering, throttle, brake, and transmission control with safety limits.
*/

use anyhow::{Context, Result};
use log::{info, warn, error};
use std::time::{Duration, Instant};
use tokio::sync::{mpsc, RwLock};
use tokio::time::interval;
use wasm_edge_ai_sdk::prelude::*;

use crate::{Waypoint, EmergencyCommand};

/// Vehicle control configuration
#[derive(Debug, Clone)]
pub struct VehicleControlConfig {
    pub max_steering_angle: f64,     // radians
    pub max_steering_rate: f64,      // rad/s
    pub max_throttle: f64,           // 0.0 to 1.0
    pub max_brake_pressure: f64,     // 0.0 to 1.0
    pub max_acceleration: f64,       // m/s²
    pub max_deceleration: f64,       // m/s²
    pub control_frequency_hz: f64,
    pub pid_params: PIDParameters,
    pub safety_limits: SafetyLimits,
    pub actuator_config: ActuatorConfig,
}

#[derive(Debug, Clone)]
pub struct PIDParameters {
    pub steering_kp: f64,
    pub steering_ki: f64,
    pub steering_kd: f64,
    pub speed_kp: f64,
    pub speed_ki: f64,
    pub speed_kd: f64,
    pub max_integral_windup: f64,
}

#[derive(Debug, Clone)]
pub struct SafetyLimits {
    pub max_lateral_acceleration: f64, // m/s²
    pub max_jerk: f64,                 // m/s³
    pub min_following_distance: f64,   // meters
    pub max_speed_in_turn: f64,        // m/s
    pub emergency_brake_threshold: f64, // m/s²
}

#[derive(Debug, Clone)]
pub struct ActuatorConfig {
    pub steering_response_time_ms: u64,
    pub throttle_response_time_ms: u64,
    pub brake_response_time_ms: u64,
    pub enable_abs: bool,
    pub enable_traction_control: bool,
    pub enable_stability_control: bool,
}

/// Vehicle control commands
#[derive(Debug, Clone)]
pub struct VehicleCommand {
    pub steering_angle: f64,    // radians (-max to +max)
    pub throttle: f64,         // 0.0 to 1.0
    pub brake: f64,            // 0.0 to 1.0
    pub target_speed: f64,     // m/s
    pub gear: GearState,
    pub timestamp: Instant,
}

#[derive(Debug, Clone, PartialEq)]
pub enum GearState {
    Park,
    Reverse,
    Neutral,
    Drive,
    Sport,
    Manual(u8),
}

/// Vehicle state feedback
#[derive(Debug, Clone)]
pub struct VehicleState {
    pub position: (f64, f64),          // (x, y) in meters
    pub heading: f64,                  // radians
    pub speed: f64,                    // m/s
    pub acceleration: f64,             // m/s²
    pub steering_angle: f64,           // radians
    pub wheel_speeds: [f64; 4],        // rad/s [FL, FR, RL, RR]
    pub throttle_position: f64,        // 0.0 to 1.0
    pub brake_pressure: f64,           // 0.0 to 1.0
    pub gear: GearState,
    pub engine_rpm: f64,
    pub fuel_level: f64,               // 0.0 to 1.0
    pub battery_voltage: f64,          // volts
    pub timestamp: Instant,
}

/// Control system status
#[derive(Debug, Clone)]
pub struct ControlStatus {
    pub is_enabled: bool,
    pub control_mode: ControlMode,
    pub last_command: Option<VehicleCommand>,
    pub steering_error: f64,
    pub speed_error: f64,
    pub actuator_status: ActuatorStatus,
    pub safety_status: ControlSafetyStatus,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ControlMode {
    Manual,
    Autonomous,
    Emergency,
    Assisted,
    Calibration,
}

#[derive(Debug, Clone)]
pub struct ActuatorStatus {
    pub steering_health: ActuatorHealth,
    pub throttle_health: ActuatorHealth,
    pub brake_health: ActuatorHealth,
    pub transmission_health: ActuatorHealth,
}

#[derive(Debug, Clone)]
pub struct ActuatorHealth {
    pub operational: bool,
    pub last_response: Instant,
    pub error_count: u32,
    pub temperature: Option<f64>,
    pub current_draw: Option<f64>,
    pub position_feedback: Option<f64>,
}

#[derive(Debug, Clone)]
pub struct ControlSafetyStatus {
    pub steering_limited: bool,
    pub speed_limited: bool,
    pub emergency_stop_active: bool,
    pub abs_active: bool,
    pub traction_control_active: bool,
    pub stability_control_active: bool,
}

/// PID Controller implementation
#[derive(Debug)]
struct PIDController {
    kp: f64,
    ki: f64,
    kd: f64,
    integral: f64,
    last_error: f64,
    last_time: Instant,
    max_integral: f64,
}

impl PIDController {
    fn new(kp: f64, ki: f64, kd: f64, max_integral: f64) -> Self {
        Self {
            kp,
            ki,
            kd,
            integral: 0.0,
            last_error: 0.0,
            last_time: Instant::now(),
            max_integral,
        }
    }
    
    fn update(&mut self, error: f64, dt: f64) -> f64 {
        // Proportional term
        let proportional = self.kp * error;
        
        // Integral term with windup protection
        self.integral += error * dt;
        self.integral = self.integral.clamp(-self.max_integral, self.max_integral);
        let integral = self.ki * self.integral;
        
        // Derivative term
        let derivative = if dt > 0.0 {
            self.kd * (error - self.last_error) / dt
        } else {
            0.0
        };
        
        self.last_error = error;
        
        proportional + integral + derivative
    }
    
    fn reset(&mut self) {
        self.integral = 0.0;
        self.last_error = 0.0;
        self.last_time = Instant::now();
    }
}

/// Main vehicle control system
pub struct VehicleController {
    config: VehicleControlConfig,
    current_state: RwLock<VehicleState>,
    control_status: RwLock<ControlStatus>,
    steering_pid: RwLock<PIDController>,
    speed_pid: RwLock<PIDController>,
    
    // Communication channels
    command_rx: mpsc::UnboundedReceiver<VehicleCommand>,
    emergency_rx: mpsc::UnboundedReceiver<EmergencyCommand>,
    state_tx: mpsc::UnboundedSender<VehicleState>,
    
    // Control task handle
    control_handle: Option<tokio::task::JoinHandle<()>>,
    
    // Hardware interfaces
    steering_actuator: SteeringActuator,
    throttle_actuator: ThrottleActuator,
    brake_actuator: BrakeActuator,
    transmission_actuator: TransmissionActuator,
}

/// Hardware actuator interfaces
struct SteeringActuator {
    current_angle: f64,
    target_angle: f64,
    max_rate: f64,
    is_operational: bool,
}

struct ThrottleActuator {
    current_position: f64,
    target_position: f64,
    response_time: Duration,
    is_operational: bool,
}

struct BrakeActuator {
    current_pressure: f64,
    target_pressure: f64,
    response_time: Duration,
    abs_enabled: bool,
    is_operational: bool,
}

struct TransmissionActuator {
    current_gear: GearState,
    target_gear: GearState,
    shift_in_progress: bool,
    is_operational: bool,
}

impl VehicleController {
    /// Create new vehicle controller
    pub fn new(
        config: VehicleControlConfig,
        command_rx: mpsc::UnboundedReceiver<VehicleCommand>,
        emergency_rx: mpsc::UnboundedReceiver<EmergencyCommand>,
        state_tx: mpsc::UnboundedSender<VehicleState>,
    ) -> Result<Self> {
        info!("Initializing vehicle control system");
        
        let initial_state = VehicleState {
            position: (0.0, 0.0),
            heading: 0.0,
            speed: 0.0,
            acceleration: 0.0,
            steering_angle: 0.0,
            wheel_speeds: [0.0; 4],
            throttle_position: 0.0,
            brake_pressure: 0.0,
            gear: GearState::Park,
            engine_rpm: 0.0,
            fuel_level: 1.0,
            battery_voltage: 12.0,
            timestamp: Instant::now(),
        };
        
        let control_status = ControlStatus {
            is_enabled: false,
            control_mode: ControlMode::Manual,
            last_command: None,
            steering_error: 0.0,
            speed_error: 0.0,
            actuator_status: ActuatorStatus {
                steering_health: ActuatorHealth {
                    operational: true,
                    last_response: Instant::now(),
                    error_count: 0,
                    temperature: Some(25.0),
                    current_draw: Some(0.5),
                    position_feedback: Some(0.0),
                },
                throttle_health: ActuatorHealth {
                    operational: true,
                    last_response: Instant::now(),
                    error_count: 0,
                    temperature: Some(60.0),
                    current_draw: Some(2.0),
                    position_feedback: Some(0.0),
                },
                brake_health: ActuatorHealth {
                    operational: true,
                    last_response: Instant::now(),
                    error_count: 0,
                    temperature: Some(40.0),
                    current_draw: Some(1.0),
                    position_feedback: Some(0.0),
                },
                transmission_health: ActuatorHealth {
                    operational: true,
                    last_response: Instant::now(),
                    error_count: 0,
                    temperature: Some(80.0),
                    current_draw: Some(3.0),
                    position_feedback: None,
                },
            },
            safety_status: ControlSafetyStatus {
                steering_limited: false,
                speed_limited: false,
                emergency_stop_active: false,
                abs_active: false,
                traction_control_active: false,
                stability_control_active: false,
            },
        };
        
        let steering_pid = PIDController::new(
            config.pid_params.steering_kp,
            config.pid_params.steering_ki,
            config.pid_params.steering_kd,
            config.pid_params.max_integral_windup,
        );
        
        let speed_pid = PIDController::new(
            config.pid_params.speed_kp,
            config.pid_params.speed_ki,
            config.pid_params.speed_kd,
            config.pid_params.max_integral_windup,
        );
        
        // Initialize actuators
        let steering_actuator = SteeringActuator::new(&config.actuator_config)?;
        let throttle_actuator = ThrottleActuator::new(&config.actuator_config)?;
        let brake_actuator = BrakeActuator::new(&config.actuator_config)?;
        let transmission_actuator = TransmissionActuator::new(&config.actuator_config)?;
        
        Ok(Self {
            config,
            current_state: RwLock::new(initial_state),
            control_status: RwLock::new(control_status),
            steering_pid: RwLock::new(steering_pid),
            speed_pid: RwLock::new(speed_pid),
            command_rx,
            emergency_rx,
            state_tx,
            control_handle: None,
            steering_actuator,
            throttle_actuator,
            brake_actuator,
            transmission_actuator,
        })
    }
    
    /// Start vehicle control system
    pub async fn start(&mut self) -> Result<()> {
        info!("Starting vehicle control system");
        
        // Enable control system
        {
            let mut status = self.control_status.write().await;
            status.is_enabled = true;
            status.control_mode = ControlMode::Autonomous;
        }
        
        let control_interval = Duration::from_secs_f64(1.0 / self.config.control_frequency_hz);
        let mut interval_timer = interval(control_interval);
        
        // Clone necessary components for the control task
        let current_state = self.current_state.clone();
        let control_status = self.control_status.clone();
        let steering_pid = self.steering_pid.clone();
        let speed_pid = self.speed_pid.clone();
        let state_tx = self.state_tx.clone();
        let config = self.config.clone();
        
        // Move receivers into the task
        let mut command_rx = std::mem::replace(&mut self.command_rx, {
            let (_, rx) = mpsc::unbounded_channel();
            rx
        });
        let mut emergency_rx = std::mem::replace(&mut self.emergency_rx, {
            let (_, rx) = mpsc::unbounded_channel();
            rx
        });
        
        let control_handle = tokio::spawn(async move {
            loop {
                tokio::select! {
                    // Handle incoming commands
                    command = command_rx.recv() => {
                        if let Some(cmd) = command {
                            if let Err(e) = Self::process_vehicle_command(
                                &current_state, 
                                &control_status, 
                                &steering_pid, 
                                &speed_pid, 
                                cmd, 
                                &config
                            ).await {
                                error!("Failed to process vehicle command: {}", e);
                            }
                        }
                    },
                    
                    // Handle emergency commands
                    emergency = emergency_rx.recv() => {
                        if let Some(cmd) = emergency {
                            if let Err(e) = Self::process_emergency_command(
                                &current_state, 
                                &control_status, 
                                cmd, 
                                &config
                            ).await {
                                error!("Failed to process emergency command: {}", e);
                            }
                        }
                    },
                    
                    // Control loop tick
                    _ = interval_timer.tick() => {
                        if let Err(e) = Self::control_loop_tick(
                            &current_state, 
                            &control_status, 
                            &state_tx, 
                            &config
                        ).await {
                            error!("Control loop tick failed: {}", e);
                        }
                    },
                }
            }
        });
        
        self.control_handle = Some(control_handle);
        Ok(())
    }
    
    /// Stop vehicle control system
    pub async fn stop(&mut self) -> Result<()> {
        info!("Stopping vehicle control system");
        
        // Disable control system
        {
            let mut status = self.control_status.write().await;
            status.is_enabled = false;
            status.control_mode = ControlMode::Manual;
        }
        
        // Stop control task
        if let Some(handle) = self.control_handle.take() {
            handle.abort();
        }
        
        // Apply parking brake
        self.apply_emergency_stop().await?;
        
        Ok(())
    }
    
    /// Execute trajectory waypoint
    pub async fn execute_waypoint(&self, waypoint: &Waypoint) -> Result<()> {
        let command = VehicleCommand {
            steering_angle: waypoint.steering_angle,
            throttle: self.speed_to_throttle(waypoint.velocity),
            brake: 0.0,
            target_speed: waypoint.velocity,
            gear: GearState::Drive,
            timestamp: Instant::now(),
        };
        
        self.process_vehicle_command(
            &self.current_state,
            &self.control_status,
            &self.steering_pid,
            &self.speed_pid,
            command,
            &self.config,
        ).await
    }
    
    /// Get current vehicle state
    pub async fn get_vehicle_state(&self) -> VehicleState {
        self.current_state.read().await.clone()
    }
    
    /// Get control status
    pub async fn get_control_status(&self) -> ControlStatus {
        self.control_status.read().await.clone()
    }
    
    /// Apply emergency stop
    pub async fn apply_emergency_stop(&self) -> Result<()> {
        warn!("Applying emergency stop");
        
        let emergency_command = VehicleCommand {
            steering_angle: 0.0,
            throttle: 0.0,
            brake: 1.0, // Full brake
            target_speed: 0.0,
            gear: GearState::Park,
            timestamp: Instant::now(),
        };
        
        // Apply immediately without PID control
        self.apply_direct_command(&emergency_command).await?;
        
        // Update safety status
        {
            let mut status = self.control_status.write().await;
            status.safety_status.emergency_stop_active = true;
            status.control_mode = ControlMode::Emergency;
        }
        
        Ok(())
    }
    
    // Internal control methods
    
    async fn process_vehicle_command(
        current_state: &RwLock<VehicleState>,
        control_status: &RwLock<ControlStatus>,
        steering_pid: &RwLock<PIDController>,
        speed_pid: &RwLock<PIDController>,
        command: VehicleCommand,
        config: &VehicleControlConfig,
    ) -> Result<()> {
        // Check if control is enabled
        {
            let status = control_status.read().await;
            if !status.is_enabled || status.control_mode == ControlMode::Emergency {
                return Ok(()); // Ignore commands in emergency mode
            }
        }
        
        // Apply safety limits
        let safe_command = Self::apply_safety_limits(&command, config)?;
        
        // Calculate control outputs using PID
        let steering_output = {
            let state = current_state.read().await;
            let steering_error = safe_command.steering_angle - state.steering_angle;
            let dt = command.timestamp.duration_since(state.timestamp).as_secs_f64();
            
            let mut pid = steering_pid.write().await;
            pid.update(steering_error, dt)
        };
        
        let speed_output = {
            let state = current_state.read().await;
            let speed_error = safe_command.target_speed - state.speed;
            let dt = command.timestamp.duration_since(state.timestamp).as_secs_f64();
            
            let mut pid = speed_pid.write().await;
            pid.update(speed_error, dt)
        };
        
        // Apply control outputs
        let final_command = VehicleCommand {
            steering_angle: safe_command.steering_angle + steering_output,
            throttle: if speed_output > 0.0 { 
                safe_command.throttle + speed_output.abs() 
            } else { 
                0.0 
            },
            brake: if speed_output < 0.0 { 
                safe_command.brake + speed_output.abs() 
            } else { 
                safe_command.brake 
            },
            target_speed: safe_command.target_speed,
            gear: safe_command.gear,
            timestamp: safe_command.timestamp,
        };
        
        // Update control status
        {
            let mut status = control_status.write().await;
            status.last_command = Some(final_command.clone());
            let state = current_state.read().await;
            status.steering_error = final_command.steering_angle - state.steering_angle;
            status.speed_error = final_command.target_speed - state.speed;
        }
        
        // Apply command to actuators (simulated)
        Self::apply_actuator_commands(&final_command).await?;
        
        Ok(())
    }
    
    async fn process_emergency_command(
        current_state: &RwLock<VehicleState>,
        control_status: &RwLock<ControlStatus>,
        emergency: EmergencyCommand,
        config: &VehicleControlConfig,
    ) -> Result<()> {
        match emergency {
            EmergencyCommand::EmergencyStop => {
                let emergency_command = VehicleCommand {
                    steering_angle: 0.0,
                    throttle: 0.0,
                    brake: 1.0,
                    target_speed: 0.0,
                    gear: GearState::Park,
                    timestamp: Instant::now(),
                };
                
                Self::apply_actuator_commands(&emergency_command).await?;
                
                let mut status = control_status.write().await;
                status.safety_status.emergency_stop_active = true;
                status.control_mode = ControlMode::Emergency;
            },
            
            EmergencyCommand::EmergencySteer(angle) => {
                let current_state_guard = current_state.read().await;
                let emergency_command = VehicleCommand {
                    steering_angle: angle.clamp(-config.max_steering_angle, config.max_steering_angle),
                    throttle: 0.0,
                    brake: 0.5, // Moderate braking while steering
                    target_speed: current_state_guard.speed * 0.5, // Reduce speed
                    gear: GearState::Drive,
                    timestamp: Instant::now(),
                };
                
                Self::apply_actuator_commands(&emergency_command).await?;
            },
            
            _ => {
                // Other emergency commands handled elsewhere
            }
        }
        
        Ok(())
    }
    
    async fn control_loop_tick(
        current_state: &RwLock<VehicleState>,
        control_status: &RwLock<ControlStatus>,
        state_tx: &mpsc::UnboundedSender<VehicleState>,
        config: &VehicleControlConfig,
    ) -> Result<()> {
        // Update vehicle state from sensors (simulated)
        let updated_state = Self::read_vehicle_sensors(config).await?;
        
        // Update current state
        {
            let mut state = current_state.write().await;
            *state = updated_state.clone();
        }
        
        // Send state update
        let _ = state_tx.send(updated_state);
        
        // Perform safety checks
        Self::perform_safety_checks(current_state, control_status, config).await?;
        
        Ok(())
    }
    
    fn apply_safety_limits(command: &VehicleCommand, config: &VehicleControlConfig) -> Result<VehicleCommand> {
        let mut safe_command = command.clone();
        
        // Limit steering angle
        safe_command.steering_angle = safe_command.steering_angle
            .clamp(-config.max_steering_angle, config.max_steering_angle);
        
        // Limit throttle
        safe_command.throttle = safe_command.throttle.clamp(0.0, config.max_throttle);
        
        // Limit brake
        safe_command.brake = safe_command.brake.clamp(0.0, config.max_brake_pressure);
        
        // Limit target speed
        safe_command.target_speed = safe_command.target_speed.clamp(0.0, 50.0); // 50 m/s max
        
        Ok(safe_command)
    }
    
    async fn apply_actuator_commands(command: &VehicleCommand) -> Result<()> {
        // Simulate applying commands to hardware
        // In a real implementation, this would interface with CAN bus or similar
        
        info!("Applying vehicle command: steering={:.3}, throttle={:.3}, brake={:.3}", 
              command.steering_angle, command.throttle, command.brake);
        
        // Simulate actuator response time
        tokio::time::sleep(Duration::from_millis(10)).await;
        
        Ok(())
    }
    
    async fn read_vehicle_sensors(config: &VehicleControlConfig) -> Result<VehicleState> {
        // Simulate reading vehicle sensors
        // In a real implementation, this would read from CAN bus, wheel encoders, etc.
        
        Ok(VehicleState {
            position: (0.0, 0.0), // Would be updated from GPS/odometry
            heading: 0.0,
            speed: 15.0 + (rand::random::<f64>() - 0.5) * 2.0, // Simulate some noise
            acceleration: 0.0,
            steering_angle: 0.0,
            wheel_speeds: [
                250.0 + rand::random::<f64>() * 10.0,
                250.0 + rand::random::<f64>() * 10.0,
                250.0 + rand::random::<f64>() * 10.0,
                250.0 + rand::random::<f64>() * 10.0,
            ],
            throttle_position: 0.3,
            brake_pressure: 0.0,
            gear: GearState::Drive,
            engine_rpm: 2000.0,
            fuel_level: 0.75,
            battery_voltage: 12.6,
            timestamp: Instant::now(),
        })
    }
    
    async fn perform_safety_checks(
        current_state: &RwLock<VehicleState>,
        control_status: &RwLock<ControlStatus>,
        config: &VehicleControlConfig,
    ) -> Result<()> {
        let state = current_state.read().await;
        let mut status = control_status.write().await;
        
        // Check for over-speed
        if state.speed > 60.0 { // 60 m/s limit
            status.safety_status.speed_limited = true;
            warn!("Vehicle speed {} exceeds safety limit", state.speed);
        } else {
            status.safety_status.speed_limited = false;
        }
        
        // Check steering angle limits
        if state.steering_angle.abs() > config.max_steering_angle * 1.1 {
            status.safety_status.steering_limited = true;
            warn!("Steering angle {} exceeds safety limit", state.steering_angle);
        } else {
            status.safety_status.steering_limited = false;
        }
        
        // Check for wheel slip (simplified)
        let avg_wheel_speed = state.wheel_speeds.iter().sum::<f64>() / 4.0;
        let wheel_speed_variation = state.wheel_speeds.iter()
            .map(|&speed| (speed - avg_wheel_speed).abs())
            .max_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
            .unwrap_or(0.0);
        
        if wheel_speed_variation > 50.0 { // 50 rad/s variation threshold
            status.safety_status.traction_control_active = true;
        } else {
            status.safety_status.traction_control_active = false;
        }
        
        Ok(())
    }
    
    fn speed_to_throttle(&self, target_speed: f64) -> f64 {
        // Simple mapping from speed to throttle position
        // In reality, this would be more complex and consider current speed, load, etc.
        (target_speed / 30.0).clamp(0.0, 1.0) // Assume 30 m/s at full throttle
    }
    
    async fn apply_direct_command(&self, command: &VehicleCommand) -> Result<()> {
        // Apply command directly without PID control (for emergencies)
        Self::apply_actuator_commands(command).await
    }
}

// Implementation of actuator structs

impl SteeringActuator {
    fn new(config: &ActuatorConfig) -> Result<Self> {
        Ok(Self {
            current_angle: 0.0,
            target_angle: 0.0,
            max_rate: 2.0, // rad/s
            is_operational: true,
        })
    }
    
    async fn set_angle(&mut self, angle: f64) -> Result<()> {
        self.target_angle = angle;
        
        // Simulate actuator response
        let angle_diff = self.target_angle - self.current_angle;
        let max_change = self.max_rate * 0.02; // Assuming 50Hz update rate
        
        if angle_diff.abs() <= max_change {
            self.current_angle = self.target_angle;
        } else {
            self.current_angle += max_change * angle_diff.signum();
        }
        
        Ok(())
    }
}

impl ThrottleActuator {
    fn new(config: &ActuatorConfig) -> Result<Self> {
        Ok(Self {
            current_position: 0.0,
            target_position: 0.0,
            response_time: Duration::from_millis(config.throttle_response_time_ms),
            is_operational: true,
        })
    }
    
    async fn set_position(&mut self, position: f64) -> Result<()> {
        self.target_position = position.clamp(0.0, 1.0);
        
        // Simulate first-order response
        let alpha = 0.1; // Response rate
        self.current_position += alpha * (self.target_position - self.current_position);
        
        Ok(())
    }
}

impl BrakeActuator {
    fn new(config: &ActuatorConfig) -> Result<Self> {
        Ok(Self {
            current_pressure: 0.0,
            target_pressure: 0.0,
            response_time: Duration::from_millis(config.brake_response_time_ms),
            abs_enabled: config.enable_abs,
            is_operational: true,
        })
    }
    
    async fn set_pressure(&mut self, pressure: f64) -> Result<()> {
        self.target_pressure = pressure.clamp(0.0, 1.0);
        
        // Simulate brake response
        let alpha = 0.2; // Faster response than throttle
        self.current_pressure += alpha * (self.target_pressure - self.current_pressure);
        
        // ABS simulation (simplified)
        if self.abs_enabled && self.current_pressure > 0.8 {
            // Simulate ABS modulation
            self.current_pressure *= 0.95;
        }
        
        Ok(())
    }
}

impl TransmissionActuator {
    fn new(config: &ActuatorConfig) -> Result<Self> {
        Ok(Self {
            current_gear: GearState::Park,
            target_gear: GearState::Park,
            shift_in_progress: false,
            is_operational: true,
        })
    }
    
    async fn set_gear(&mut self, gear: GearState) -> Result<()> {
        if self.current_gear != gear && !self.shift_in_progress {
            self.target_gear = gear;
            self.shift_in_progress = true;
            
            // Simulate shift time
            tokio::time::sleep(Duration::from_millis(500)).await;
            
            self.current_gear = self.target_gear.clone();
            self.shift_in_progress = false;
        }
        
        Ok(())
    }
}

impl Default for VehicleControlConfig {
    fn default() -> Self {
        Self {
            max_steering_angle: 0.6,     // ~35 degrees
            max_steering_rate: 2.0,      // 2 rad/s
            max_throttle: 1.0,
            max_brake_pressure: 1.0,
            max_acceleration: 4.0,       // 4 m/s²
            max_deceleration: 8.0,       // 8 m/s²
            control_frequency_hz: 50.0,  // 50 Hz
            pid_params: PIDParameters {
                steering_kp: 1.0,
                steering_ki: 0.1,
                steering_kd: 0.05,
                speed_kp: 0.5,
                speed_ki: 0.05,
                speed_kd: 0.02,
                max_integral_windup: 10.0,
            },
            safety_limits: SafetyLimits {
                max_lateral_acceleration: 4.0,  // 4 m/s²
                max_jerk: 2.0,                  // 2 m/s³
                min_following_distance: 20.0,   // 20 meters
                max_speed_in_turn: 15.0,        // 15 m/s
                emergency_brake_threshold: 9.8, // 1g
            },
            actuator_config: ActuatorConfig {
                steering_response_time_ms: 50,
                throttle_response_time_ms: 100,
                brake_response_time_ms: 30,
                enable_abs: true,
                enable_traction_control: true,
                enable_stability_control: true,
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_pid_controller() {
        let mut pid = PIDController::new(1.0, 0.1, 0.05, 10.0);
        
        let output = pid.update(1.0, 0.1); // 1.0 error, 0.1s time step
        assert!(output > 0.0); // Should produce positive output for positive error
    }
    
    #[test]
    fn test_safety_limits() {
        let config = VehicleControlConfig::default();
        
        let unsafe_command = VehicleCommand {
            steering_angle: 2.0, // Exceeds max
            throttle: 1.5,       // Exceeds max
            brake: -0.5,         // Invalid
            target_speed: 100.0, // Very high
            gear: GearState::Drive,
            timestamp: Instant::now(),
        };
        
        let safe_command = VehicleController::apply_safety_limits(&unsafe_command, &config).unwrap();
        
        assert!(safe_command.steering_angle <= config.max_steering_angle);
        assert!(safe_command.throttle <= config.max_throttle);
        assert!(safe_command.brake >= 0.0);
    }
    
    #[tokio::test]
    async fn test_vehicle_controller_creation() {
        let config = VehicleControlConfig::default();
        let (cmd_tx, cmd_rx) = mpsc::unbounded_channel();
        let (emg_tx, emg_rx) = mpsc::unbounded_channel();
        let (state_tx, _state_rx) = mpsc::unbounded_channel();
        
        let controller = VehicleController::new(config, cmd_rx, emg_rx, state_tx);
        assert!(controller.is_ok());
    }
}