/*!
# Humanoid Robot AI System

Advanced humanoid robot control system with multi-modal AI capabilities.
Integrates vision, speech, motion planning, and human-robot interaction.

## Features
- Full-body motion control with inverse kinematics
- Real-time computer vision and object recognition
- Natural language processing and speech synthesis
- Human pose estimation and gesture recognition
- Emotion recognition and social interaction
- Safety monitoring and collision avoidance
- Edge AI inference with WASM runtime

## Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vision AI     │    │   Speech AI     │    │   Motion AI     │
│   - Face Rec    │    │   - STT/TTS     │    │   - Kinematics  │
│   - Gesture     │    │   - NLP         │    │   - Balance     │
│   - SLAM        │    │   - Emotion     │    │   - Gait        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Central Brain  │
                    │  - Behavior     │
                    │  - Planning     │
                    │  - Safety       │
                    └─────────────────┘
```
*/

use anyhow::{Context, Result};
use log::{info, warn, error};
use std::sync::Arc;
use tokio::sync::{broadcast, mpsc, RwLock};
use tokio::time::{interval, Duration};
use clap::Parser;
use serde::{Deserialize, Serialize};

mod vision;
mod speech;
mod motion;
mod behavior;
mod safety;
mod interaction;
mod hardware;
mod config;

use vision::VisionSystem;
use speech::SpeechSystem;
use motion::MotionSystem;
use behavior::BehaviorPlanner;
use safety::SafetyMonitor;
use interaction::InteractionManager;
use hardware::HardwareInterface;
use config::RobotConfig;

/// Command line arguments
#[derive(Parser, Debug)]
#[clap(author, version, about, long_about = None)]
struct Args {
    /// Configuration file path
    #[clap(short, long, value_parser, default_value = "config/robot.yaml")]
    config: String,
    
    /// Robot mode
    #[clap(short, long, value_enum, default_value = "autonomous")]
    mode: RobotMode,
    
    /// Enable simulation mode
    #[clap(short, long)]
    simulation: bool,
    
    /// Enable debug logging
    #[clap(short, long)]
    debug: bool,
    
    /// Hardware interface type
    #[clap(long, value_enum, default_value = "real")]
    hardware: HardwareType,
}

#[derive(clap::ValueEnum, Clone, Debug)]
enum RobotMode {
    Autonomous,
    Teleoperated,
    Interactive,
    Demonstration,
    Maintenance,
}

#[derive(clap::ValueEnum, Clone, Debug)]
enum HardwareType {
    Real,
    Simulation,
    Mock,
}

/// Main robot system state
#[derive(Debug, Clone)]
pub struct RobotState {
    pub pose: RobotPose,
    pub joint_states: JointStates,
    pub sensor_data: SensorData,
    pub interaction_state: InteractionState,
    pub behavior_state: BehaviorState,
    pub safety_status: SafetyStatus,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RobotPose {
    pub position: [f64; 3],      // x, y, z in meters
    pub orientation: [f64; 4],   // quaternion (w, x, y, z)
    pub velocity: [f64; 3],      // linear velocity
    pub angular_velocity: [f64; 3], // angular velocity
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JointStates {
    pub positions: Vec<f64>,     // radians
    pub velocities: Vec<f64>,    // rad/s
    pub efforts: Vec<f64>,       // Nm
    pub names: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct SensorData {
    pub camera_frames: Vec<CameraFrame>,
    pub depth_data: Option<DepthFrame>,
    pub audio_data: Option<AudioFrame>,
    pub imu_data: ImuData,
    pub force_sensors: Vec<ForceSensor>,
    pub proximity_sensors: Vec<ProximitySensor>,
}

#[derive(Debug, Clone)]
pub struct CameraFrame {
    pub camera_id: String,
    pub image_data: Vec<u8>,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub width: u32,
    pub height: u32,
    pub format: ImageFormat,
}

#[derive(Debug, Clone)]
pub enum ImageFormat {
    RGB8,
    BGR8,
    RGBA8,
    Grayscale,
}

#[derive(Debug, Clone)]
pub struct DepthFrame {
    pub depth_data: Vec<f32>,
    pub width: u32,
    pub height: u32,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub struct AudioFrame {
    pub samples: Vec<f32>,
    pub sample_rate: u32,
    pub channels: u32,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub struct ImuData {
    pub acceleration: [f64; 3],
    pub angular_velocity: [f64; 3],
    pub magnetic_field: [f64; 3],
    pub orientation: [f64; 4],
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub struct ForceSensor {
    pub sensor_id: String,
    pub force: [f64; 3],         // x, y, z
    pub torque: [f64; 3],        // around x, y, z
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub struct ProximitySensor {
    pub sensor_id: String,
    pub distance: f64,           // meters
    pub angle: f64,              // radians
    pub confidence: f64,         // 0.0 to 1.0
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub struct InteractionState {
    pub detected_humans: Vec<DetectedHuman>,
    pub current_conversation: Option<Conversation>,
    pub emotional_state: EmotionalState,
    pub attention_focus: AttentionFocus,
}

#[derive(Debug, Clone)]
pub struct DetectedHuman {
    pub person_id: String,
    pub face_landmarks: Vec<[f64; 2]>,
    pub body_pose: BodyPose,
    pub estimated_age: Option<u32>,
    pub estimated_gender: Option<Gender>,
    pub emotion: EmotionClassification,
    pub distance: f64,
    pub engagement_level: f64,   // 0.0 to 1.0
}

#[derive(Debug, Clone)]
pub struct BodyPose {
    pub keypoints: Vec<Keypoint>,
    pub confidence: f64,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub struct Keypoint {
    pub joint_name: String,
    pub position: [f64; 3],      // x, y, z
    pub confidence: f64,
}

#[derive(Debug, Clone)]
pub enum Gender {
    Male,
    Female,
    Unknown,
}

#[derive(Debug, Clone)]
pub struct EmotionClassification {
    pub primary_emotion: Emotion,
    pub confidence: f64,
    pub all_emotions: Vec<(Emotion, f64)>,
}

#[derive(Debug, Clone)]
pub enum Emotion {
    Happy,
    Sad,
    Angry,
    Surprised,
    Fearful,
    Disgusted,
    Neutral,
    Confused,
    Excited,
}

#[derive(Debug, Clone)]
pub struct Conversation {
    pub conversation_id: String,
    pub participants: Vec<String>,
    pub messages: Vec<ConversationMessage>,
    pub context: ConversationContext,
    pub start_time: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub struct ConversationMessage {
    pub speaker: String,
    pub text: String,
    pub audio_data: Option<Vec<f32>>,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub sentiment: SentimentAnalysis,
    pub intent: IntentClassification,
}

#[derive(Debug, Clone)]
pub struct SentimentAnalysis {
    pub polarity: f64,           // -1.0 (negative) to 1.0 (positive)
    pub confidence: f64,
}

#[derive(Debug, Clone)]
pub struct IntentClassification {
    pub intent: Intent,
    pub confidence: f64,
    pub entities: Vec<Entity>,
}

#[derive(Debug, Clone)]
pub enum Intent {
    Greeting,
    Question,
    Command,
    Request,
    Complaint,
    Compliment,
    Goodbye,
    SmallTalk,
    Emergency,
    Unknown,
}

#[derive(Debug, Clone)]
pub struct Entity {
    pub entity_type: String,
    pub value: String,
    pub confidence: f64,
}

#[derive(Debug, Clone)]
pub struct ConversationContext {
    pub topic: Option<String>,
    pub mood: Emotion,
    pub formality_level: FormalityLevel,
    pub language: String,
}

#[derive(Debug, Clone)]
pub enum FormalityLevel {
    Formal,
    Informal,
    Casual,
    Professional,
}

#[derive(Debug, Clone)]
pub struct EmotionalState {
    pub current_emotion: Emotion,
    pub intensity: f64,          // 0.0 to 1.0
    pub stability: f64,          // how quickly emotions change
    pub personality_traits: PersonalityTraits,
}

#[derive(Debug, Clone)]
pub struct PersonalityTraits {
    pub extroversion: f64,       // 0.0 to 1.0
    pub agreeableness: f64,
    pub conscientiousness: f64,
    pub neuroticism: f64,
    pub openness: f64,
}

#[derive(Debug, Clone)]
pub struct AttentionFocus {
    pub primary_target: Option<AttentionTarget>,
    pub attention_level: f64,    // 0.0 to 1.0
    pub focus_duration: Duration,
    pub distractions: Vec<AttentionTarget>,
}

#[derive(Debug, Clone)]
pub struct AttentionTarget {
    pub target_type: TargetType,
    pub target_id: String,
    pub position: [f64; 3],
    pub importance: f64,         // 0.0 to 1.0
    pub last_updated: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub enum TargetType {
    Person,
    Object,
    Sound,
    Event,
    Task,
}

#[derive(Debug, Clone)]
pub struct BehaviorState {
    pub current_behavior: Behavior,
    pub behavior_stack: Vec<Behavior>,
    pub goals: Vec<Goal>,
    pub current_task: Option<Task>,
    pub execution_status: ExecutionStatus,
}

#[derive(Debug, Clone)]
pub struct Behavior {
    pub behavior_id: String,
    pub behavior_type: BehaviorType,
    pub priority: f64,           // 0.0 to 1.0
    pub parameters: std::collections::HashMap<String, String>,
    pub start_time: chrono::DateTime<chrono::Utc>,
    pub expected_duration: Option<Duration>,
}

#[derive(Debug, Clone)]
pub enum BehaviorType {
    Idle,
    Following,
    Interacting,
    Demonstrating,
    Navigating,
    Manipulating,
    Speaking,
    Listening,
    Observing,
    Emergency,
}

#[derive(Debug, Clone)]
pub struct Goal {
    pub goal_id: String,
    pub description: String,
    pub goal_type: GoalType,
    pub priority: f64,
    pub deadline: Option<chrono::DateTime<chrono::Utc>>,
    pub completion_criteria: Vec<CompletionCriterion>,
    pub progress: f64,           // 0.0 to 1.0
}

#[derive(Debug, Clone)]
pub enum GoalType {
    Navigate,
    Interact,
    Learn,
    Perform,
    Assist,
    Entertain,
    Demonstrate,
}

#[derive(Debug, Clone)]
pub struct CompletionCriterion {
    pub criterion_type: String,
    pub target_value: f64,
    pub current_value: f64,
    pub tolerance: f64,
}

#[derive(Debug, Clone)]
pub struct Task {
    pub task_id: String,
    pub task_type: TaskType,
    pub description: String,
    pub steps: Vec<TaskStep>,
    pub current_step: usize,
    pub estimated_duration: Duration,
    pub start_time: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub enum TaskType {
    Motion,
    Communication,
    Perception,
    Manipulation,
    Navigation,
    Social,
}

#[derive(Debug, Clone)]
pub struct TaskStep {
    pub step_id: String,
    pub description: String,
    pub action: Action,
    pub preconditions: Vec<Condition>,
    pub postconditions: Vec<Condition>,
    pub timeout: Option<Duration>,
}

#[derive(Debug, Clone)]
pub struct Action {
    pub action_type: ActionType,
    pub parameters: std::collections::HashMap<String, f64>,
    pub target: Option<String>,
}

#[derive(Debug, Clone)]
pub enum ActionType {
    MoveTo,
    RotateTo,
    Speak,
    Gesture,
    GraspObject,
    ReleaseObject,
    LookAt,
    WaitFor,
    RecordData,
}

#[derive(Debug, Clone)]
pub struct Condition {
    pub condition_type: ConditionType,
    pub parameters: std::collections::HashMap<String, f64>,
    pub tolerance: f64,
}

#[derive(Debug, Clone)]
pub enum ConditionType {
    Position,
    Orientation,
    JointAngle,
    ForceDetected,
    ObjectVisible,
    SpeechHeard,
    TimeElapsed,
    HumanPresent,
}

#[derive(Debug, Clone)]
pub enum ExecutionStatus {
    NotStarted,
    Running,
    Paused,
    Completed,
    Failed,
    Cancelled,
    Waiting,
}

#[derive(Debug, Clone)]
pub struct SafetyStatus {
    pub overall_status: SafetyLevel,
    pub active_constraints: Vec<SafetyConstraint>,
    pub collision_risk: f64,     // 0.0 to 1.0
    pub fall_risk: f64,          // 0.0 to 1.0
    pub emergency_stop_active: bool,
    pub last_safety_check: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub enum SafetyLevel {
    Safe,
    Caution,
    Warning,
    Danger,
    Emergency,
}

#[derive(Debug, Clone)]
pub struct SafetyConstraint {
    pub constraint_type: ConstraintType,
    pub description: String,
    pub severity: SafetyLevel,
    pub active_since: chrono::DateTime<chrono::Utc>,
    pub parameters: std::collections::HashMap<String, f64>,
}

#[derive(Debug, Clone)]
pub enum ConstraintType {
    JointLimit,
    VelocityLimit,
    ForceLimit,
    CollisionAvoidance,
    FallPrevention,
    HumanSafety,
    WorkspaceLimit,
    PowerLimit,
}

/// Main humanoid robot system
pub struct HumanoidRobot {
    config: Arc<RobotConfig>,
    state: Arc<RwLock<RobotState>>,
    
    // Core subsystems
    vision_system: Arc<VisionSystem>,
    speech_system: Arc<SpeechSystem>,
    motion_system: Arc<MotionSystem>,
    behavior_planner: Arc<BehaviorPlanner>,
    safety_monitor: Arc<SafetyMonitor>,
    interaction_manager: Arc<InteractionManager>,
    hardware_interface: Arc<HardwareInterface>,
    
    // Communication channels
    command_tx: mpsc::UnboundedSender<RobotCommand>,
    status_tx: broadcast::Sender<RobotStatus>,
    
    // Task handles
    main_loop_handle: Option<tokio::task::JoinHandle<()>>,
    subsystem_handles: Vec<tokio::task::JoinHandle<()>>,
}

#[derive(Debug, Clone)]
pub enum RobotCommand {
    Start,
    Stop,
    Pause,
    Resume,
    ExecuteTask(Task),
    SetBehavior(Behavior),
    UpdateGoal(Goal),
    EmergencyStop,
    Speak(String),
    MoveTo { position: [f64; 3], orientation: [f64; 4] },
    LookAt { target: [f64; 3] },
    Gesture { gesture_name: String },
    SetMode(RobotMode),
}

#[derive(Debug, Clone)]
pub enum RobotStatus {
    Initializing,
    Ready,
    Running,
    Paused,
    Error(String),
    EmergencyStop,
    ShuttingDown,
}

impl HumanoidRobot {
    /// Create new humanoid robot system
    pub async fn new(config: RobotConfig) -> Result<Self> {
        info!("Initializing humanoid robot system");
        
        let config = Arc::new(config);
        
        // Initialize core state
        let initial_state = RobotState {
            pose: RobotPose {
                position: [0.0, 0.0, 0.0],
                orientation: [1.0, 0.0, 0.0, 0.0], // Identity quaternion
                velocity: [0.0, 0.0, 0.0],
                angular_velocity: [0.0, 0.0, 0.0],
            },
            joint_states: JointStates {
                positions: vec![0.0; config.hardware.joint_count],
                velocities: vec![0.0; config.hardware.joint_count],
                efforts: vec![0.0; config.hardware.joint_count],
                names: config.hardware.joint_names.clone(),
            },
            sensor_data: SensorData {
                camera_frames: Vec::new(),
                depth_data: None,
                audio_data: None,
                imu_data: ImuData {
                    acceleration: [0.0, 0.0, 9.81], // Earth gravity
                    angular_velocity: [0.0, 0.0, 0.0],
                    magnetic_field: [0.0, 0.0, 0.0],
                    orientation: [1.0, 0.0, 0.0, 0.0],
                    timestamp: chrono::Utc::now(),
                },
                force_sensors: Vec::new(),
                proximity_sensors: Vec::new(),
            },
            interaction_state: InteractionState {
                detected_humans: Vec::new(),
                current_conversation: None,
                emotional_state: EmotionalState {
                    current_emotion: Emotion::Neutral,
                    intensity: 0.5,
                    stability: 0.8,
                    personality_traits: PersonalityTraits {
                        extroversion: 0.7,
                        agreeableness: 0.8,
                        conscientiousness: 0.9,
                        neuroticism: 0.2,
                        openness: 0.8,
                    },
                },
                attention_focus: AttentionFocus {
                    primary_target: None,
                    attention_level: 0.0,
                    focus_duration: Duration::from_secs(0),
                    distractions: Vec::new(),
                },
            },
            behavior_state: BehaviorState {
                current_behavior: Behavior {
                    behavior_id: "idle".to_string(),
                    behavior_type: BehaviorType::Idle,
                    priority: 0.1,
                    parameters: std::collections::HashMap::new(),
                    start_time: chrono::Utc::now(),
                    expected_duration: None,
                },
                behavior_stack: Vec::new(),
                goals: Vec::new(),
                current_task: None,
                execution_status: ExecutionStatus::NotStarted,
            },
            safety_status: SafetyStatus {
                overall_status: SafetyLevel::Safe,
                active_constraints: Vec::new(),
                collision_risk: 0.0,
                fall_risk: 0.0,
                emergency_stop_active: false,
                last_safety_check: chrono::Utc::now(),
            },
            timestamp: chrono::Utc::now(),
        };
        
        let state = Arc::new(RwLock::new(initial_state));
        
        // Initialize subsystems
        let vision_system = Arc::new(VisionSystem::new(&config.vision).await?);
        let speech_system = Arc::new(SpeechSystem::new(&config.speech).await?);
        let motion_system = Arc::new(MotionSystem::new(&config.motion).await?);
        let behavior_planner = Arc::new(BehaviorPlanner::new(&config.behavior).await?);
        let safety_monitor = Arc::new(SafetyMonitor::new(&config.safety).await?);
        let interaction_manager = Arc::new(InteractionManager::new(&config.interaction).await?);
        let hardware_interface = Arc::new(HardwareInterface::new(&config.hardware).await?);
        
        // Setup communication channels
        let (command_tx, _) = mpsc::unbounded_channel();
        let (status_tx, _) = broadcast::channel(100);
        
        Ok(Self {
            config,
            state,
            vision_system,
            speech_system,
            motion_system,
            behavior_planner,
            safety_monitor,
            interaction_manager,
            hardware_interface,
            command_tx,
            status_tx,
            main_loop_handle: None,
            subsystem_handles: Vec::new(),
        })
    }
    
    /// Start the robot system
    pub async fn start(&mut self) -> Result<()> {
        info!("Starting humanoid robot system");
        
        // Start all subsystems
        self.vision_system.start().await?;
        self.speech_system.start().await?;
        self.motion_system.start().await?;
        self.behavior_planner.start().await?;
        self.safety_monitor.start().await?;
        self.interaction_manager.start().await?;
        self.hardware_interface.start().await?;
        
        // Start main control loop
        self.start_main_loop().await?;
        
        // Broadcast ready status
        let _ = self.status_tx.send(RobotStatus::Ready);
        
        info!("Humanoid robot system started successfully");
        Ok(())
    }
    
    /// Stop the robot system
    pub async fn stop(&mut self) -> Result<()> {
        info!("Stopping humanoid robot system");
        
        // Broadcast shutdown status
        let _ = self.status_tx.send(RobotStatus::ShuttingDown);
        
        // Stop main loop
        if let Some(handle) = self.main_loop_handle.take() {
            handle.abort();
        }
        
        // Stop all subsystem handles
        for handle in self.subsystem_handles.drain(..) {
            handle.abort();
        }
        
        // Stop subsystems
        self.hardware_interface.stop().await?;
        self.interaction_manager.stop().await?;
        self.safety_monitor.stop().await?;
        self.behavior_planner.stop().await?;
        self.motion_system.stop().await?;
        self.speech_system.stop().await?;
        self.vision_system.stop().await?;
        
        info!("Humanoid robot system stopped");
        Ok(())
    }
    
    /// Send command to robot
    pub async fn send_command(&self, command: RobotCommand) -> Result<()> {
        self.command_tx.send(command)
            .context("Failed to send command")?;
        Ok(())
    }
    
    /// Get current robot state
    pub async fn get_state(&self) -> RobotState {
        self.state.read().await.clone()
    }
    
    /// Subscribe to robot status updates
    pub fn subscribe_status(&self) -> broadcast::Receiver<RobotStatus> {
        self.status_tx.subscribe()
    }
    
    // Internal methods
    
    async fn start_main_loop(&mut self) -> Result<()> {
        let state = Arc::clone(&self.state);
        let config = Arc::clone(&self.config);
        let status_tx = self.status_tx.clone();
        
        // Clone subsystem references
        let vision_system = Arc::clone(&self.vision_system);
        let speech_system = Arc::clone(&self.speech_system);
        let motion_system = Arc::clone(&self.motion_system);
        let behavior_planner = Arc::clone(&self.behavior_planner);
        let safety_monitor = Arc::clone(&self.safety_monitor);
        let interaction_manager = Arc::clone(&self.interaction_manager);
        let hardware_interface = Arc::clone(&self.hardware_interface);
        
        let main_loop_handle = tokio::spawn(async move {
            let mut control_interval = interval(Duration::from_millis(
                (1000.0 / config.control.update_frequency_hz) as u64
            ));
            
            let _ = status_tx.send(RobotStatus::Running);
            
            loop {
                control_interval.tick().await;
                
                // Main control cycle
                if let Err(e) = Self::control_cycle(
                    &state,
                    &vision_system,
                    &speech_system,
                    &motion_system,
                    &behavior_planner,
                    &safety_monitor,
                    &interaction_manager,
                    &hardware_interface,
                ).await {
                    error!("Control cycle error: {}", e);
                    let _ = status_tx.send(RobotStatus::Error(e.to_string()));
                }
            }
        });
        
        self.main_loop_handle = Some(main_loop_handle);
        Ok(())
    }
    
    async fn control_cycle(
        state: &Arc<RwLock<RobotState>>,
        vision_system: &Arc<VisionSystem>,
        speech_system: &Arc<SpeechSystem>,
        motion_system: &Arc<MotionSystem>,
        behavior_planner: &Arc<BehaviorPlanner>,
        safety_monitor: &Arc<SafetyMonitor>,
        interaction_manager: &Arc<InteractionManager>,
        hardware_interface: &Arc<HardwareInterface>,
    ) -> Result<()> {
        let start_time = chrono::Utc::now();
        
        // 1. Gather sensor data
        let sensor_data = Self::collect_sensor_data(
            vision_system,
            speech_system,
            hardware_interface,
        ).await?;
        
        // 2. Update perception and world model
        let perception_results = Self::update_perception(
            &sensor_data,
            vision_system,
            speech_system,
        ).await?;
        
        // 3. Analyze human interactions
        let interaction_results = interaction_manager.process_interactions(
            &perception_results
        ).await?;
        
        // 4. Safety monitoring
        let safety_status = safety_monitor.check_safety(
            &sensor_data,
            &perception_results,
        ).await?;
        
        // 5. Behavior planning and decision making
        let behavior_decision = behavior_planner.plan_behavior(
            &perception_results,
            &interaction_results,
            &safety_status,
        ).await?;
        
        // 6. Motion planning and control
        let motion_commands = motion_system.plan_motion(
            &behavior_decision,
            &safety_status,
        ).await?;
        
        // 7. Execute commands
        hardware_interface.execute_commands(&motion_commands).await?;
        
        // 8. Update robot state
        {
            let mut state_guard = state.write().await;
            state_guard.sensor_data = sensor_data;
            state_guard.interaction_state = interaction_results;
            state_guard.safety_status = safety_status;
            state_guard.behavior_state = behavior_decision;
            state_guard.timestamp = start_time;
        }
        
        Ok(())
    }
    
    async fn collect_sensor_data(
        vision_system: &Arc<VisionSystem>,
        speech_system: &Arc<SpeechSystem>,
        hardware_interface: &Arc<HardwareInterface>,
    ) -> Result<SensorData> {
        // Collect data from all sensors in parallel
        let (camera_frames, audio_data, hardware_data) = tokio::try_join!(
            vision_system.capture_frames(),
            speech_system.capture_audio(),
            hardware_interface.read_sensors(),
        )?;
        
        Ok(SensorData {
            camera_frames,
            depth_data: None, // Would be extracted from camera frames
            audio_data,
            imu_data: hardware_data.imu_data,
            force_sensors: hardware_data.force_sensors,
            proximity_sensors: hardware_data.proximity_sensors,
        })
    }
    
    async fn update_perception(
        sensor_data: &SensorData,
        vision_system: &Arc<VisionSystem>,
        speech_system: &Arc<SpeechSystem>,
    ) -> Result<PerceptionResults> {
        // Process visual perception
        let visual_perception = vision_system.process_frames(&sensor_data.camera_frames).await?;
        
        // Process audio perception
        let audio_perception = if let Some(ref audio) = sensor_data.audio_data {
            Some(speech_system.process_audio(audio).await?)
        } else {
            None
        };
        
        Ok(PerceptionResults {
            visual_perception,
            audio_perception,
            timestamp: chrono::Utc::now(),
        })
    }
}

// Helper structures for internal communication
#[derive(Debug, Clone)]
pub struct PerceptionResults {
    pub visual_perception: vision::VisionResults,
    pub audio_perception: Option<speech::AudioResults>,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub struct HardwareData {
    pub imu_data: ImuData,
    pub force_sensors: Vec<ForceSensor>,
    pub proximity_sensors: Vec<ProximitySensor>,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Parse command line arguments
    let args = Args::parse();
    
    // Initialize logging
    if args.debug {
        env_logger::Builder::from_default_env()
            .filter_level(log::LevelFilter::Debug)
            .init();
    } else {
        env_logger::Builder::from_default_env()
            .filter_level(log::LevelFilter::Info)
            .init();
    }
    
    info!("Starting Kenny Humanoid Robot System");
    info!("Mode: {:?}, Hardware: {:?}, Simulation: {}", 
          args.mode, args.hardware, args.simulation);
    
    // Load configuration
    let config = RobotConfig::load(&args.config).await
        .context("Failed to load robot configuration")?;
    
    // Create robot system
    let mut robot = HumanoidRobot::new(config).await
        .context("Failed to create robot system")?;
    
    // Setup signal handling for graceful shutdown
    let mut term_signal = signal_hook::iterator::Signals::new(&[
        signal_hook::consts::SIGTERM,
        signal_hook::consts::SIGINT,
    ])?;
    
    // Start robot system
    robot.start().await
        .context("Failed to start robot system")?;
    
    // Subscribe to status updates
    let mut status_rx = robot.subscribe_status();
    
    info!("Robot system started. Press Ctrl+C to stop.");
    
    // Main event loop
    loop {
        tokio::select! {
            // Handle status updates
            status = status_rx.recv() => {
                match status {
                    Ok(RobotStatus::Error(error)) => {
                        error!("Robot error: {}", error);
                    },
                    Ok(RobotStatus::EmergencyStop) => {
                        warn!("Emergency stop activated");
                    },
                    Ok(status) => {
                        info!("Robot status: {:?}", status);
                    },
                    Err(_) => break,
                }
            },
            
            // Handle shutdown signals
            signal = tokio::task::spawn_blocking(move || term_signal.forever().next()) => {
                if let Ok(Some(_)) = signal {
                    info!("Shutdown signal received");
                    break;
                }
            },
        }
    }
    
    // Graceful shutdown
    info!("Shutting down robot system...");
    robot.stop().await
        .context("Failed to stop robot system")?;
    
    info!("Robot system shutdown complete");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    
    #[tokio::test]
    async fn test_robot_creation() {
        let config = RobotConfig::default();
        let robot = HumanoidRobot::new(config).await;
        assert!(robot.is_ok());
    }
    
    #[tokio::test]
    async fn test_robot_state_initialization() {
        let config = RobotConfig::default();
        let robot = HumanoidRobot::new(config).await.unwrap();
        
        let state = robot.get_state().await;
        assert_eq!(state.pose.position, [0.0, 0.0, 0.0]);
        assert_eq!(state.safety_status.overall_status, SafetyLevel::Safe);
    }
    
    #[test]
    fn test_emotion_classification() {
        let emotion = EmotionClassification {
            primary_emotion: Emotion::Happy,
            confidence: 0.85,
            all_emotions: vec![
                (Emotion::Happy, 0.85),
                (Emotion::Neutral, 0.10),
                (Emotion::Excited, 0.05),
            ],
        };
        
        assert_eq!(emotion.primary_emotion, Emotion::Happy);
        assert!(emotion.confidence > 0.8);
    }
    
    #[test]
    fn test_behavior_state_transitions() {
        let mut behavior_state = BehaviorState {
            current_behavior: Behavior {
                behavior_id: "idle".to_string(),
                behavior_type: BehaviorType::Idle,
                priority: 0.1,
                parameters: std::collections::HashMap::new(),
                start_time: chrono::Utc::now(),
                expected_duration: None,
            },
            behavior_stack: Vec::new(),
            goals: Vec::new(),
            current_task: None,
            execution_status: ExecutionStatus::NotStarted,
        };
        
        assert_eq!(behavior_state.current_behavior.behavior_type, BehaviorType::Idle);
        
        // Test behavior change
        behavior_state.current_behavior.behavior_type = BehaviorType::Interacting;
        assert_eq!(behavior_state.current_behavior.behavior_type, BehaviorType::Interacting);
    }
    
    #[test]
    fn test_safety_constraint_creation() {
        let constraint = SafetyConstraint {
            constraint_type: ConstraintType::VelocityLimit,
            description: "Maximum joint velocity exceeded".to_string(),
            severity: SafetyLevel::Warning,
            active_since: chrono::Utc::now(),
            parameters: {
                let mut params = std::collections::HashMap::new();
                params.insert("max_velocity".to_string(), 2.0);
                params.insert("current_velocity".to_string(), 2.5);
                params
            },
        };
        
        assert_eq!(constraint.constraint_type, ConstraintType::VelocityLimit);
        assert_eq!(constraint.severity, SafetyLevel::Warning);
        assert!(constraint.parameters.contains_key("max_velocity"));
    }
}