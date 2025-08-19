/*!
# Behavior Planning System

High-level behavior planning and decision making for humanoid robots.
Implements hierarchical task planning, goal management, and adaptive behavior selection.
*/

use anyhow::{Context, Result};
use log::{info, warn, error, debug};
use std::collections::{HashMap, VecDeque};
use std::sync::Arc;
use tokio::sync::{RwLock, mpsc, broadcast};
use tokio::time::{interval, Duration, Instant};
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

use crate::{
    BehaviorState, Behavior, BehaviorType, Goal, GoalType, Task, TaskType, TaskStep, Action, ActionType,
    Condition, ConditionType, ExecutionStatus, CompletionCriterion, InteractionState, SafetyStatus,
    EmotionalState, AttentionFocus, Intent, Emotion
};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BehaviorConfig {
    pub planning: PlanningConfig,
    pub decision_making: DecisionMakingConfig,
    pub goal_management: GoalManagementConfig,
    pub adaptation: AdaptationConfig,
    pub social_behavior: SocialBehaviorConfig,
    pub learning: LearningConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlanningConfig {
    pub planner_type: PlannerType,
    pub planning_horizon: Duration,
    pub replanning_interval: Duration,
    pub max_plan_depth: usize,
    pub contingency_planning: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PlannerType {
    HierarchicalTaskNetwork,
    BehaviorTree,
    StateMachine,
    ReinforcementLearning,
    HybridApproach,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionMakingConfig {
    pub decision_strategy: DecisionStrategy,
    pub uncertainty_threshold: f64,
    pub confidence_required: f64,
    pub risk_tolerance: f64,
    pub time_pressure_factor: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DecisionStrategy {
    UtilityBased,
    RuleBased,
    ProbabilisticReasoning,
    MultiCriteriaDecision,
    NeuralNetwork,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GoalManagementConfig {
    pub max_concurrent_goals: usize,
    pub goal_prioritization: PrioritizationStrategy,
    pub goal_expiry_time: Duration,
    pub automatic_goal_generation: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PrioritizationStrategy {
    Priority,
    Deadline,
    Utility,
    Social,
    Safety,
    Hybrid,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdaptationConfig {
    pub adaptation_enabled: bool,
    pub learning_rate: f64,
    pub adaptation_threshold: f64,
    pub personality_adaptation: bool,
    pub context_adaptation: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SocialBehaviorConfig {
    pub social_awareness: bool,
    pub personal_space_radius: f64,
    pub eye_contact_probability: f64,
    pub gesture_frequency: f64,
    pub politeness_level: f64,
    pub cultural_adaptation: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LearningConfig {
    pub learning_enabled: bool,
    pub experience_buffer_size: usize,
    pub learning_algorithm: LearningAlgorithm,
    pub exploration_rate: f64,
    pub memory_retention: Duration,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LearningAlgorithm {
    ReinforcementLearning,
    ImitationLearning,
    ContinualLearning,
    MetaLearning,
    TransferLearning,
}

#[derive(Debug, Clone)]
pub struct BehaviorDecision {
    pub selected_behavior: Behavior,
    pub confidence: f64,
    pub reasoning: String,
    pub alternative_behaviors: Vec<AlternativeBehavior>,
    pub expected_outcomes: Vec<ExpectedOutcome>,
    pub risk_assessment: RiskAssessment,
}

#[derive(Debug, Clone)]
pub struct AlternativeBehavior {
    pub behavior: Behavior,
    pub utility_score: f64,
    pub feasibility: f64,
    pub risk_level: f64,
}

#[derive(Debug, Clone)]
pub struct ExpectedOutcome {
    pub outcome_type: OutcomeType,
    pub probability: f64,
    pub utility: f64,
    pub time_to_achieve: Duration,
}

#[derive(Debug, Clone)]
pub enum OutcomeType {
    GoalAchievement,
    SocialPositive,
    SocialNegative,
    SafetyConcern,
    LearningOpportunity,
    ResourceConsumption,
}

#[derive(Debug, Clone)]
pub struct RiskAssessment {
    pub overall_risk: f64,
    pub safety_risk: f64,
    pub social_risk: f64,
    pub task_failure_risk: f64,
    pub mitigation_strategies: Vec<MitigationStrategy>,
}

#[derive(Debug, Clone)]
pub struct MitigationStrategy {
    pub strategy_type: MitigationType,
    pub description: String,
    pub effectiveness: f64,
    pub cost: f64,
}

#[derive(Debug, Clone)]
pub enum MitigationType {
    Avoidance,
    Mitigation,
    Contingency,
    Monitoring,
    Escalation,
}

#[derive(Debug, Clone)]
pub struct PlanningContext {
    pub current_situation: SituationAssessment,
    pub available_resources: Resources,
    pub environmental_constraints: Vec<Constraint>,
    pub social_context: SocialContext,
    pub temporal_context: TemporalContext,
}

#[derive(Debug, Clone)]
pub struct SituationAssessment {
    pub situation_type: SituationType,
    pub urgency_level: f64,
    pub complexity_level: f64,
    pub ambiguity_level: f64,
    pub social_dynamics: SocialDynamics,
}

#[derive(Debug, Clone)]
pub enum SituationType {
    Normal,
    Emergency,
    Social,
    Task,
    Learning,
    Maintenance,
}

#[derive(Debug, Clone)]
pub struct SocialDynamics {
    pub human_count: usize,
    pub interaction_intensity: f64,
    pub social_roles: HashMap<String, SocialRole>,
    pub group_mood: Emotion,
    pub authority_structure: Vec<AuthorityRelation>,
}

#[derive(Debug, Clone)]
pub struct SocialRole {
    pub role_name: String,
    pub authority_level: f64,
    pub expertise_domains: Vec<String>,
    pub social_influence: f64,
}

#[derive(Debug, Clone)]
pub struct AuthorityRelation {
    pub superior: String,
    pub subordinate: String,
    pub authority_type: AuthorityType,
}

#[derive(Debug, Clone)]
pub enum AuthorityType {
    Formal,
    Expertise,
    Social,
    Situational,
}

#[derive(Debug, Clone)]
pub struct Resources {
    pub computational_capacity: f64,
    pub energy_level: f64,
    pub memory_available: f64,
    pub physical_capabilities: PhysicalCapabilities,
    pub social_capital: f64,
}

#[derive(Debug, Clone)]
pub struct PhysicalCapabilities {
    pub mobility: f64,
    pub manipulation: f64,
    pub sensing: f64,
    pub communication: f64,
    pub endurance: f64,
}

#[derive(Debug, Clone)]
pub struct Constraint {
    pub constraint_id: String,
    pub constraint_type: ConstraintType,
    pub severity: f64,
    pub duration: Option<Duration>,
    pub affected_capabilities: Vec<String>,
}

#[derive(Debug, Clone)]
pub enum ConstraintType {
    Physical,
    Social,
    Temporal,
    Resource,
    Safety,
    Legal,
}

#[derive(Debug, Clone)]
pub struct SocialContext {
    pub interaction_mode: InteractionMode,
    pub formality_level: f64,
    pub cultural_context: CulturalContext,
    pub relationship_status: HashMap<String, RelationshipStatus>,
}

#[derive(Debug, Clone)]
pub enum InteractionMode {
    OneOnOne,
    SmallGroup,
    LargeGroup,
    Public,
    Formal,
    Casual,
}

#[derive(Debug, Clone)]
pub struct CulturalContext {
    pub culture_name: String,
    pub communication_style: CommunicationStyle,
    pub personal_space_norms: f64,
    pub hierarchy_importance: f64,
    pub time_orientation: TimeOrientation,
}

#[derive(Debug, Clone)]
pub enum CommunicationStyle {
    Direct,
    Indirect,
    Formal,
    Informal,
    HighContext,
    LowContext,
}

#[derive(Debug, Clone)]
pub enum TimeOrientation {
    Monochronic,
    Polychronic,
    PastOriented,
    PresentOriented,
    FutureOriented,
}

#[derive(Debug, Clone)]
pub struct RelationshipStatus {
    pub person_id: String,
    pub relationship_type: RelationshipType,
    pub trust_level: f64,
    pub familiarity: f64,
    pub interaction_history: Vec<InteractionRecord>,
}

#[derive(Debug, Clone)]
pub enum RelationshipType {
    Stranger,
    Acquaintance,
    Friend,
    Colleague,
    Authority,
    Family,
    Professional,
}

#[derive(Debug, Clone)]
pub struct InteractionRecord {
    pub timestamp: DateTime<Utc>,
    pub interaction_type: String,
    pub outcome: InteractionOutcome,
    pub satisfaction: f64,
}

#[derive(Debug, Clone)]
pub enum InteractionOutcome {
    Positive,
    Negative,
    Neutral,
    Successful,
    Failed,
    Incomplete,
}

#[derive(Debug, Clone)]
pub struct TemporalContext {
    pub time_pressure: f64,
    pub deadlines: Vec<Deadline>,
    pub schedule_constraints: Vec<ScheduleConstraint>,
    pub temporal_preferences: TemporalPreferences,
}

#[derive(Debug, Clone)]
pub struct Deadline {
    pub task_id: String,
    pub deadline: DateTime<Utc>,
    pub importance: f64,
    pub flexibility: f64,
}

#[derive(Debug, Clone)]
pub struct ScheduleConstraint {
    pub start_time: DateTime<Utc>,
    pub end_time: DateTime<Utc>,
    pub constraint_type: String,
    pub negotiability: f64,
}

#[derive(Debug, Clone)]
pub struct TemporalPreferences {
    pub preferred_pace: f64,
    pub time_allocation_strategy: TimeAllocationStrategy,
    pub multitasking_preference: f64,
}

#[derive(Debug, Clone)]
pub enum TimeAllocationStrategy {
    Sequential,
    Parallel,
    Adaptive,
    PriorityBased,
}

pub struct BehaviorPlanner {
    config: BehaviorConfig,
    current_state: Arc<RwLock<BehaviorState>>,
    
    // Planning components
    task_planner: Arc<TaskPlanner>,
    goal_manager: Arc<GoalManager>,
    decision_engine: Arc<DecisionEngine>,
    adaptation_engine: Arc<AdaptationEngine>,
    social_behavior_manager: Arc<SocialBehaviorManager>,
    
    // Knowledge and memory
    behavior_library: Arc<RwLock<BehaviorLibrary>>,
    experience_memory: Arc<RwLock<ExperienceMemory>>,
    world_model: Arc<RwLock<WorldModel>>,
    
    // Communication
    behavior_tx: broadcast::Sender<BehaviorDecision>,
    update_rx: Option<mpsc::UnboundedReceiver<BehaviorUpdate>>,
    update_tx: mpsc::UnboundedSender<BehaviorUpdate>,
}

#[derive(Debug, Clone)]
pub enum BehaviorUpdate {
    NewGoal(Goal),
    GoalCompleted(String),
    SituationChanged(SituationAssessment),
    EmergencyDetected(String),
    LearningUpdate(LearningEvent),
}

#[derive(Debug, Clone)]
pub struct LearningEvent {
    pub event_type: LearningEventType,
    pub data: HashMap<String, String>,
    pub timestamp: DateTime<Utc>,
    pub importance: f64,
}

#[derive(Debug, Clone)]
pub enum LearningEventType {
    SuccessfulBehavior,
    FailedBehavior,
    NewStrategy,
    PreferenceUpdate,
    SkillImprovement,
}

struct TaskPlanner {
    config: PlanningConfig,
    planning_algorithms: HashMap<PlannerType, Box<dyn PlanningAlgorithm>>,
}

trait PlanningAlgorithm: Send + Sync {
    fn plan(&self, context: &PlanningContext, goals: &[Goal]) -> Result<Vec<Task>>;
    fn replan(&self, current_plan: &[Task], new_context: &PlanningContext) -> Result<Vec<Task>>;
}

struct GoalManager {
    config: GoalManagementConfig,
    active_goals: Arc<RwLock<VecDeque<Goal>>>,
    goal_history: Arc<RwLock<Vec<Goal>>>,
    goal_prioritizer: Box<dyn GoalPrioritizer>,
}

trait GoalPrioritizer: Send + Sync {
    fn prioritize_goals(&self, goals: &mut VecDeque<Goal>, context: &PlanningContext);
    fn should_add_goal(&self, goal: &Goal, current_goals: &VecDeque<Goal>) -> bool;
}

struct DecisionEngine {
    config: DecisionMakingConfig,
    decision_strategies: HashMap<DecisionStrategy, Box<dyn DecisionStrategy>>,
    utility_calculator: Arc<UtilityCalculator>,
}

trait DecisionStrategy: Send + Sync {
    fn make_decision(&self, alternatives: &[AlternativeBehavior], context: &PlanningContext) -> Result<BehaviorDecision>;
    fn assess_confidence(&self, decision: &BehaviorDecision) -> f64;
}

struct UtilityCalculator {
    utility_functions: HashMap<String, Box<dyn UtilityFunction>>,
}

trait UtilityFunction: Send + Sync {
    fn calculate_utility(&self, behavior: &Behavior, context: &PlanningContext) -> f64;
}

struct AdaptationEngine {
    config: AdaptationConfig,
    adaptation_history: Arc<RwLock<Vec<AdaptationRecord>>>,
    personality_model: Arc<RwLock<PersonalityModel>>,
}

#[derive(Debug, Clone)]
struct AdaptationRecord {
    timestamp: DateTime<Utc>,
    situation: String,
    original_behavior: String,
    adapted_behavior: String,
    outcome: f64,
}

#[derive(Debug, Clone)]
struct PersonalityModel {
    traits: HashMap<String, f64>,
    adaptation_rate: f64,
    stability: f64,
}

struct SocialBehaviorManager {
    config: SocialBehaviorConfig,
    social_rules: Arc<RwLock<SocialRuleSet>>,
    interaction_patterns: Arc<RwLock<InteractionPatterns>>,
}

#[derive(Debug, Clone)]
struct SocialRuleSet {
    rules: Vec<SocialRule>,
}

#[derive(Debug, Clone)]
struct SocialRule {
    rule_id: String,
    condition: SocialCondition,
    action: SocialAction,
    priority: f64,
}

#[derive(Debug, Clone)]
struct SocialCondition {
    context_requirements: Vec<String>,
    participant_requirements: Vec<String>,
    situation_requirements: Vec<String>,
}

#[derive(Debug, Clone)]
struct SocialAction {
    action_type: String,
    parameters: HashMap<String, String>,
    expected_outcome: String,
}

#[derive(Debug, Clone)]
struct InteractionPatterns {
    patterns: HashMap<String, InteractionPattern>,
}

#[derive(Debug, Clone)]
struct InteractionPattern {
    pattern_name: String,
    triggers: Vec<String>,
    sequence: Vec<InteractionStep>,
    success_criteria: Vec<String>,
}

#[derive(Debug, Clone)]
struct InteractionStep {
    step_type: String,
    timing: Duration,
    required_actions: Vec<String>,
    expected_responses: Vec<String>,
}

struct BehaviorLibrary {
    behaviors: HashMap<String, BehaviorTemplate>,
    behavior_hierarchies: Vec<BehaviorHierarchy>,
}

#[derive(Debug, Clone)]
struct BehaviorTemplate {
    name: String,
    behavior_type: BehaviorType,
    preconditions: Vec<Condition>,
    effects: Vec<Effect>,
    parameters: HashMap<String, ParameterDefinition>,
    success_criteria: Vec<SuccessCriterion>,
}

#[derive(Debug, Clone)]
struct Effect {
    effect_type: String,
    parameters: HashMap<String, f64>,
    probability: f64,
}

#[derive(Debug, Clone)]
struct ParameterDefinition {
    name: String,
    parameter_type: String,
    default_value: String,
    constraints: Vec<String>,
}

#[derive(Debug, Clone)]
struct SuccessCriterion {
    criterion_type: String,
    threshold: f64,
    measurement: String,
}

#[derive(Debug, Clone)]
struct BehaviorHierarchy {
    parent_behavior: String,
    child_behaviors: Vec<String>,
    composition_type: CompositionType,
}

#[derive(Debug, Clone)]
enum CompositionType {
    Sequential,
    Parallel,
    Conditional,
    Iterative,
}

struct ExperienceMemory {
    experiences: VecDeque<Experience>,
    experience_index: HashMap<String, Vec<usize>>,
    max_size: usize,
}

#[derive(Debug, Clone)]
struct Experience {
    id: String,
    timestamp: DateTime<Utc>,
    situation: SituationAssessment,
    behavior_executed: String,
    outcome: ExperienceOutcome,
    learned_lessons: Vec<String>,
    importance: f64,
}

#[derive(Debug, Clone)]
struct ExperienceOutcome {
    success: bool,
    utility_achieved: f64,
    side_effects: Vec<String>,
    satisfaction: f64,
}

struct WorldModel {
    entities: HashMap<String, Entity>,
    relationships: Vec<Relationship>,
    environmental_state: EnvironmentalState,
    temporal_state: TemporalState,
}

#[derive(Debug, Clone)]
struct Entity {
    id: String,
    entity_type: String,
    properties: HashMap<String, String>,
    state: EntityState,
}

#[derive(Debug, Clone)]
enum EntityState {
    Static,
    Dynamic,
    Interactive,
    Temporal,
}

#[derive(Debug, Clone)]
struct Relationship {
    from_entity: String,
    to_entity: String,
    relationship_type: String,
    strength: f64,
    properties: HashMap<String, String>,
}

#[derive(Debug, Clone)]
struct EnvironmentalState {
    location: String,
    physical_conditions: HashMap<String, f64>,
    social_conditions: HashMap<String, f64>,
    dynamic_factors: Vec<DynamicFactor>,
}

#[derive(Debug, Clone)]
struct DynamicFactor {
    factor_name: String,
    current_value: f64,
    trend: f64,
    prediction: Option<f64>,
}

#[derive(Debug, Clone)]
struct TemporalState {
    current_time: DateTime<Utc>,
    time_zone: String,
    schedule_state: ScheduleState,
    temporal_patterns: Vec<TemporalPattern>,
}

#[derive(Debug, Clone)]
struct ScheduleState {
    current_activities: Vec<String>,
    upcoming_activities: Vec<ScheduledActivity>,
    free_time_slots: Vec<TimeSlot>,
}

#[derive(Debug, Clone)]
struct ScheduledActivity {
    activity_name: String,
    start_time: DateTime<Utc>,
    duration: Duration,
    importance: f64,
    flexibility: f64,
}

#[derive(Debug, Clone)]
struct TimeSlot {
    start_time: DateTime<Utc>,
    duration: Duration,
    availability: f64,
}

#[derive(Debug, Clone)]
struct TemporalPattern {
    pattern_name: String,
    frequency: Duration,
    confidence: f64,
    next_occurrence: Option<DateTime<Utc>>,
}

impl BehaviorPlanner {
    pub async fn new(config: &BehaviorConfig) -> Result<Self> {
        info!("Initializing behavior planner");
        
        // Initialize core components
        let task_planner = Arc::new(TaskPlanner::new(&config.planning).await?);
        let goal_manager = Arc::new(GoalManager::new(&config.goal_management).await?);
        let decision_engine = Arc::new(DecisionEngine::new(&config.decision_making).await?);
        let adaptation_engine = Arc::new(AdaptationEngine::new(&config.adaptation).await?);
        let social_behavior_manager = Arc::new(SocialBehaviorManager::new(&config.social_behavior).await?);
        
        // Initialize knowledge systems
        let behavior_library = Arc::new(RwLock::new(BehaviorLibrary::new().await?));
        let experience_memory = Arc::new(RwLock::new(ExperienceMemory::new(config.learning.experience_buffer_size)));
        let world_model = Arc::new(RwLock::new(WorldModel::new().await?));
        
        // Initialize state
        let initial_state = BehaviorState {
            current_behavior: Behavior {
                behavior_id: "initialization".to_string(),
                behavior_type: BehaviorType::Idle,
                priority: 0.1,
                parameters: HashMap::new(),
                start_time: Utc::now(),
                expected_duration: None,
            },
            behavior_stack: Vec::new(),
            goals: Vec::new(),
            current_task: None,
            execution_status: ExecutionStatus::NotStarted,
        };
        
        let current_state = Arc::new(RwLock::new(initial_state));
        
        // Setup communication
        let (behavior_tx, _) = broadcast::channel(100);
        let (update_tx, update_rx) = mpsc::unbounded_channel();
        
        Ok(Self {
            config: config.clone(),
            current_state,
            task_planner,
            goal_manager,
            decision_engine,
            adaptation_engine,
            social_behavior_manager,
            behavior_library,
            experience_memory,
            world_model,
            behavior_tx,
            update_rx: Some(update_rx),
            update_tx,
        })
    }
    
    pub async fn start(&self) -> Result<()> {
        info!("Starting behavior planner");
        
        // Start goal management
        self.goal_manager.start().await?;
        
        // Start adaptation engine
        self.adaptation_engine.start().await?;
        
        Ok(())
    }
    
    pub async fn stop(&self) -> Result<()> {
        info!("Stopping behavior planner");
        Ok(())
    }
    
    pub async fn plan_behavior(
        &self,
        perception_results: &crate::PerceptionResults,
        interaction_results: &InteractionState,
        safety_status: &SafetyStatus,
    ) -> Result<BehaviorState> {
        debug!("Planning behavior based on current context");
        
        // 1. Update world model with perception results
        self.update_world_model(perception_results).await?;
        
        // 2. Assess current situation
        let situation = self.assess_situation(perception_results, interaction_results, safety_status).await?;
        
        // 3. Create planning context
        let context = self.create_planning_context(&situation, interaction_results).await?;
        
        // 4. Check for emergencies
        if self.is_emergency_situation(&situation) {
            return self.handle_emergency(&situation).await;
        }
        
        // 5. Update goals based on situation
        self.update_goals(&context, interaction_results).await?;
        
        // 6. Get current goals
        let goals = self.goal_manager.get_active_goals().await;
        
        // 7. Plan tasks for goals
        let tasks = self.task_planner.plan_tasks(&context, &goals).await?;
        
        // 8. Generate behavior alternatives
        let alternatives = self.generate_behavior_alternatives(&tasks, &context).await?;
        
        // 9. Make behavior decision
        let decision = self.decision_engine.make_decision(&alternatives, &context).await?;
        
        // 10. Apply social behavior modifications
        let social_behavior = self.social_behavior_manager.adapt_behavior(&decision.selected_behavior, &context).await?;
        
        // 11. Apply personal adaptation
        let adapted_behavior = self.adaptation_engine.adapt_behavior(&social_behavior, &context).await?;
        
        // 12. Update behavior state
        let mut state = self.current_state.write().await;
        state.current_behavior = adapted_behavior;
        state.goals = goals;
        state.current_task = tasks.first().cloned();
        state.execution_status = ExecutionStatus::Running;
        
        // 13. Record experience for learning
        self.record_experience(&decision, &context).await?;
        
        // 14. Broadcast decision
        let _ = self.behavior_tx.send(decision);
        
        Ok(state.clone())
    }
    
    async fn update_world_model(&self, perception_results: &crate::PerceptionResults) -> Result<()> {
        let mut world_model = self.world_model.write().await;
        
        // Update entities based on visual perception
        for human in &perception_results.visual_perception.detected_humans {
            let entity = Entity {
                id: human.person_id.clone(),
                entity_type: "human".to_string(),
                properties: {
                    let mut props = HashMap::new();
                    props.insert("distance".to_string(), human.distance.to_string());
                    props.insert("engagement".to_string(), human.engagement_level.to_string());
                    if let Some(age) = human.estimated_age {
                        props.insert("age".to_string(), age.to_string());
                    }
                    props
                },
                state: EntityState::Dynamic,
            };
            world_model.entities.insert(human.person_id.clone(), entity);
        }
        
        // Update objects
        for object in &perception_results.visual_perception.detected_objects {
            let entity = Entity {
                id: object.object_id.clone(),
                entity_type: object.class_name.clone(),
                properties: {
                    let mut props = HashMap::new();
                    props.insert("confidence".to_string(), object.confidence.to_string());
                    if let Some(pos) = object.position_3d {
                        props.insert("x".to_string(), pos[0].to_string());
                        props.insert("y".to_string(), pos[1].to_string());
                        props.insert("z".to_string(), pos[2].to_string());
                    }
                    props
                },
                state: EntityState::Static,
            };
            world_model.entities.insert(object.object_id.clone(), entity);
        }
        
        // Update temporal state
        world_model.temporal_state.current_time = Utc::now();
        
        Ok(())
    }
    
    async fn assess_situation(
        &self,
        perception_results: &crate::PerceptionResults,
        interaction_results: &InteractionState,
        safety_status: &SafetyStatus,
    ) -> Result<SituationAssessment> {
        // Determine situation type
        let situation_type = if safety_status.overall_status != crate::SafetyLevel::Safe {
            SituationType::Emergency
        } else if !interaction_results.detected_humans.is_empty() {
            SituationType::Social
        } else {
            SituationType::Normal
        };
        
        // Calculate urgency based on various factors
        let urgency_level = self.calculate_urgency(safety_status, interaction_results).await;
        
        // Calculate complexity
        let complexity_level = self.calculate_complexity(perception_results, interaction_results).await;
        
        // Calculate ambiguity
        let ambiguity_level = self.calculate_ambiguity(perception_results).await;
        
        // Assess social dynamics
        let social_dynamics = self.assess_social_dynamics(interaction_results).await;
        
        Ok(SituationAssessment {
            situation_type,
            urgency_level,
            complexity_level,
            ambiguity_level,
            social_dynamics,
        })
    }
    
    async fn calculate_urgency(&self, safety_status: &SafetyStatus, interaction_results: &InteractionState) -> f64 {
        let mut urgency = 0.0;
        
        // Safety urgency
        urgency += match safety_status.overall_status {
            crate::SafetyLevel::Emergency => 1.0,
            crate::SafetyLevel::Danger => 0.8,
            crate::SafetyLevel::Warning => 0.6,
            crate::SafetyLevel::Caution => 0.3,
            crate::SafetyLevel::Safe => 0.0,
        };
        
        // Social urgency (if someone is trying to interact)
        if let Some(ref conversation) = interaction_results.current_conversation {
            if let Some(last_message) = conversation.messages.last() {
                match last_message.intent.intent {
                    Intent::Emergency => urgency += 0.9,
                    Intent::Question | Intent::Request => urgency += 0.4,
                    Intent::Command => urgency += 0.6,
                    _ => urgency += 0.2,
                }
            }
        }
        
        urgency.min(1.0)
    }
    
    async fn calculate_complexity(&self, perception_results: &crate::PerceptionResults, interaction_results: &InteractionState) -> f64 {
        let mut complexity = 0.0;
        
        // Visual complexity
        complexity += (perception_results.visual_perception.detected_humans.len() as f64 * 0.1).min(0.5);
        complexity += (perception_results.visual_perception.detected_objects.len() as f64 * 0.02).min(0.3);
        
        // Social complexity
        complexity += (interaction_results.detected_humans.len() as f64 * 0.15).min(0.6);
        
        // Conversation complexity
        if let Some(ref conversation) = interaction_results.current_conversation {
            complexity += (conversation.participants.len() as f64 * 0.1).min(0.4);
            complexity += (conversation.messages.len() as f64 * 0.02).min(0.2);
        }
        
        complexity.min(1.0)
    }
    
    async fn calculate_ambiguity(&self, perception_results: &crate::PerceptionResults) -> f64 {
        let mut ambiguity = 0.0;
        
        // Check confidence levels in visual perception
        for human in &perception_results.visual_perception.detected_humans {
            ambiguity += (1.0 - human.body_pose.confidence) * 0.1;
            ambiguity += (1.0 - human.emotion.confidence) * 0.1;
        }
        
        for object in &perception_results.visual_perception.detected_objects {
            ambiguity += (1.0 - object.confidence) * 0.05;
        }
        
        // Check audio perception confidence if available
        if let Some(ref audio) = perception_results.audio_perception {
            // This would check speech recognition confidence
            // For now, we'll use a placeholder
            ambiguity += 0.1;
        }
        
        ambiguity.min(1.0)
    }
    
    async fn assess_social_dynamics(&self, interaction_results: &InteractionState) -> SocialDynamics {
        let human_count = interaction_results.detected_humans.len();
        
        let interaction_intensity = if let Some(ref conversation) = interaction_results.current_conversation {
            // Calculate based on recent message frequency and emotional intensity
            conversation.messages.len() as f64 * 0.1
        } else {
            0.0
        }.min(1.0);
        
        let mut social_roles = HashMap::new();
        for (i, human) in interaction_results.detected_humans.iter().enumerate() {
            social_roles.insert(
                human.person_id.clone(),
                SocialRole {
                    role_name: format!("person_{}", i),
                    authority_level: 0.5, // Default authority
                    expertise_domains: Vec::new(),
                    social_influence: human.engagement_level,
                }
            );
        }
        
        let group_mood = if !interaction_results.detected_humans.is_empty() {
            // Average emotion across detected humans
            interaction_results.detected_humans[0].emotion.primary_emotion.clone()
        } else {
            Emotion::Neutral
        };
        
        SocialDynamics {
            human_count,
            interaction_intensity,
            social_roles,
            group_mood,
            authority_structure: Vec::new(), // Would be populated with known relationships
        }
    }
    
    async fn create_planning_context(&self, situation: &SituationAssessment, interaction_results: &InteractionState) -> Result<PlanningContext> {
        // Get current resources
        let resources = self.assess_available_resources().await;
        
        // Identify constraints
        let constraints = self.identify_constraints(situation).await;
        
        // Assess social context
        let social_context = self.assess_social_context(interaction_results).await;
        
        // Assess temporal context
        let temporal_context = self.assess_temporal_context().await;
        
        Ok(PlanningContext {
            current_situation: situation.clone(),
            available_resources: resources,
            environmental_constraints: constraints,
            social_context,
            temporal_context,
        })
    }
    
    async fn assess_available_resources(&self) -> Resources {
        // In a real system, this would query actual resource states
        Resources {
            computational_capacity: 0.8,
            energy_level: 0.9,
            memory_available: 0.7,
            physical_capabilities: PhysicalCapabilities {
                mobility: 0.9,
                manipulation: 0.8,
                sensing: 0.95,
                communication: 0.9,
                endurance: 0.85,
            },
            social_capital: 0.7,
        }
    }
    
    async fn identify_constraints(&self, situation: &SituationAssessment) -> Vec<Constraint> {
        let mut constraints = Vec::new();
        
        // Add safety constraints based on situation
        if situation.urgency_level > 0.7 {
            constraints.push(Constraint {
                constraint_id: "high_urgency".to_string(),
                constraint_type: ConstraintType::Temporal,
                severity: situation.urgency_level,
                duration: Some(Duration::from_secs(300)), // 5 minutes
                affected_capabilities: vec!["planning_time".to_string()],
            });
        }
        
        // Add social constraints
        if situation.social_dynamics.human_count > 0 {
            constraints.push(Constraint {
                constraint_id: "social_presence".to_string(),
                constraint_type: ConstraintType::Social,
                severity: 0.5,
                duration: None,
                affected_capabilities: vec!["movement".to_string(), "noise_level".to_string()],
            });
        }
        
        constraints
    }
    
    async fn assess_social_context(&self, interaction_results: &InteractionState) -> SocialContext {
        let interaction_mode = match interaction_results.detected_humans.len() {
            0 => InteractionMode::Public,
            1 => InteractionMode::OneOnOne,
            2..=5 => InteractionMode::SmallGroup,
            _ => InteractionMode::LargeGroup,
        };
        
        let formality_level = if let Some(ref conversation) = interaction_results.current_conversation {
            conversation.context.formality_level as f64 / 4.0 // Convert enum to 0-1 scale
        } else {
            0.5
        };
        
        let cultural_context = CulturalContext {
            culture_name: "default".to_string(),
            communication_style: CommunicationStyle::Direct,
            personal_space_norms: 1.2, // meters
            hierarchy_importance: 0.5,
            time_orientation: TimeOrientation::PresentOriented,
        };
        
        let mut relationship_status = HashMap::new();
        for human in &interaction_results.detected_humans {
            relationship_status.insert(
                human.person_id.clone(),
                RelationshipStatus {
                    person_id: human.person_id.clone(),
                    relationship_type: RelationshipType::Stranger, // Default
                    trust_level: 0.5,
                    familiarity: 0.1,
                    interaction_history: Vec::new(),
                }
            );
        }
        
        SocialContext {
            interaction_mode,
            formality_level,
            cultural_context,
            relationship_status,
        }
    }
    
    async fn assess_temporal_context(&self) -> TemporalContext {
        TemporalContext {
            time_pressure: 0.3, // Default moderate time pressure
            deadlines: Vec::new(),
            schedule_constraints: Vec::new(),
            temporal_preferences: TemporalPreferences {
                preferred_pace: 0.7,
                time_allocation_strategy: TimeAllocationStrategy::Adaptive,
                multitasking_preference: 0.6,
            },
        }
    }
    
    fn is_emergency_situation(&self, situation: &SituationAssessment) -> bool {
        matches!(situation.situation_type, SituationType::Emergency) || situation.urgency_level > 0.9
    }
    
    async fn handle_emergency(&self, situation: &SituationAssessment) -> Result<BehaviorState> {
        warn!("Emergency situation detected, executing emergency behavior");
        
        let emergency_behavior = Behavior {
            behavior_id: "emergency_response".to_string(),
            behavior_type: BehaviorType::Emergency,
            priority: 1.0,
            parameters: {
                let mut params = HashMap::new();
                params.insert("urgency".to_string(), situation.urgency_level.to_string());
                params
            },
            start_time: Utc::now(),
            expected_duration: Some(Duration::from_secs(60)),
        };
        
        let mut state = self.current_state.write().await;
        state.current_behavior = emergency_behavior;
        state.execution_status = ExecutionStatus::Running;
        
        Ok(state.clone())
    }
    
    async fn update_goals(&self, context: &PlanningContext, interaction_results: &InteractionState) -> Result<()> {
        // Generate automatic goals based on situation
        if self.config.goal_management.automatic_goal_generation {
            let new_goals = self.generate_automatic_goals(context, interaction_results).await?;
            
            for goal in new_goals {
                self.goal_manager.add_goal(goal).await?;
            }
        }
        
        Ok(())
    }
    
    async fn generate_automatic_goals(&self, context: &PlanningContext, interaction_results: &InteractionState) -> Result<Vec<Goal>> {
        let mut goals = Vec::new();
        
        // Generate social interaction goals
        if !interaction_results.detected_humans.is_empty() {
            goals.push(Goal {
                goal_id: format!("interact_{}", Utc::now().timestamp()),
                description: "Engage in social interaction".to_string(),
                goal_type: GoalType::Interact,
                priority: 0.7,
                deadline: Some(Utc::now() + chrono::Duration::minutes(10)),
                completion_criteria: vec![
                    CompletionCriterion {
                        criterion_type: "engagement_achieved".to_string(),
                        target_value: 0.8,
                        current_value: 0.0,
                        tolerance: 0.1,
                    }
                ],
                progress: 0.0,
            });
        }
        
        // Generate learning goals
        if context.current_situation.situation_type == SituationType::Normal {
            goals.push(Goal {
                goal_id: format!("observe_{}", Utc::now().timestamp()),
                description: "Observe and learn from environment".to_string(),
                goal_type: GoalType::Learn,
                priority: 0.3,
                deadline: None,
                completion_criteria: vec![
                    CompletionCriterion {
                        criterion_type: "observation_time".to_string(),
                        target_value: 300.0, // 5 minutes
                        current_value: 0.0,
                        tolerance: 30.0,
                    }
                ],
                progress: 0.0,
            });
        }
        
        Ok(goals)
    }
    
    async fn generate_behavior_alternatives(&self, tasks: &[Task], context: &PlanningContext) -> Result<Vec<AlternativeBehavior>> {
        let mut alternatives = Vec::new();
        
        // Get behavior templates from library
        let behavior_library = self.behavior_library.read().await;
        
        for task in tasks {
            // Find suitable behaviors for this task type
            let suitable_behaviors = behavior_library.get_behaviors_for_task(&task.task_type);
            
            for behavior_template in suitable_behaviors {
                let behavior = self.instantiate_behavior(behavior_template, task, context).await?;
                let utility_score = self.calculate_utility(&behavior, context).await;
                let feasibility = self.assess_feasibility(&behavior, context).await;
                let risk_level = self.assess_risk(&behavior, context).await;
                
                alternatives.push(AlternativeBehavior {
                    behavior,
                    utility_score,
                    feasibility,
                    risk_level,
                });
            }
        }
        
        // Always include idle behavior as fallback
        alternatives.push(AlternativeBehavior {
            behavior: Behavior {
                behavior_id: "idle_fallback".to_string(),
                behavior_type: BehaviorType::Idle,
                priority: 0.1,
                parameters: HashMap::new(),
                start_time: Utc::now(),
                expected_duration: None,
            },
            utility_score: 0.2,
            feasibility: 1.0,
            risk_level: 0.0,
        });
        
        Ok(alternatives)
    }
    
    async fn instantiate_behavior(&self, template: &BehaviorTemplate, task: &Task, _context: &PlanningContext) -> Result<Behavior> {
        let mut parameters = HashMap::new();
        
        // Set default parameters from template
        for (name, param_def) in &template.parameters {
            parameters.insert(name.clone(), param_def.default_value.clone());
        }
        
        // Override with task-specific parameters
        for (key, value) in &task.steps[0].action.parameters {
            parameters.insert(key.clone(), value.to_string());
        }
        
        Ok(Behavior {
            behavior_id: format!("{}_{}", template.name, task.task_id),
            behavior_type: template.behavior_type.clone(),
            priority: 0.5, // Default priority
            parameters,
            start_time: Utc::now(),
            expected_duration: Some(task.estimated_duration),
        })
    }
    
    async fn calculate_utility(&self, behavior: &Behavior, context: &PlanningContext) -> f64 {
        // Simplified utility calculation
        let mut utility = 0.5; // Base utility
        
        // Add utility based on behavior type and situation
        match (&behavior.behavior_type, &context.current_situation.situation_type) {
            (BehaviorType::Interacting, SituationType::Social) => utility += 0.3,
            (BehaviorType::Emergency, SituationType::Emergency) => utility += 0.5,
            (BehaviorType::Observing, SituationType::Normal) => utility += 0.2,
            _ => {}
        }
        
        // Adjust for resource availability
        utility *= context.available_resources.computational_capacity;
        
        utility.min(1.0)
    }
    
    async fn assess_feasibility(&self, behavior: &Behavior, context: &PlanningContext) -> f64 {
        let mut feasibility = 1.0;
        
        // Check resource requirements
        match behavior.behavior_type {
            BehaviorType::Navigating => {
                feasibility *= context.available_resources.physical_capabilities.mobility;
            },
            BehaviorType::Manipulating => {
                feasibility *= context.available_resources.physical_capabilities.manipulation;
            },
            BehaviorType::Speaking => {
                feasibility *= context.available_resources.physical_capabilities.communication;
            },
            _ => {}
        }
        
        // Check constraints
        for constraint in &context.environmental_constraints {
            if constraint.severity > 0.8 {
                feasibility *= 0.7; // High severity constraints reduce feasibility
            }
        }
        
        feasibility
    }
    
    async fn assess_risk(&self, behavior: &Behavior, context: &PlanningContext) -> f64 {
        let mut risk = 0.0;
        
        // Add risk based on behavior type
        match behavior.behavior_type {
            BehaviorType::Emergency => risk += 0.2, // Emergency behaviors are inherently risky
            BehaviorType::Navigating => risk += 0.1,
            BehaviorType::Manipulating => risk += 0.15,
            _ => {}
        }
        
        // Add risk based on situation complexity
        risk += context.current_situation.complexity_level * 0.2;
        
        // Add risk based on ambiguity
        risk += context.current_situation.ambiguity_level * 0.3;
        
        risk.min(1.0)
    }
    
    async fn record_experience(&self, decision: &BehaviorDecision, context: &PlanningContext) -> Result<()> {
        let experience = Experience {
            id: format!("exp_{}", Utc::now().timestamp()),
            timestamp: Utc::now(),
            situation: context.current_situation.clone(),
            behavior_executed: decision.selected_behavior.behavior_id.clone(),
            outcome: ExperienceOutcome {
                success: decision.confidence > 0.7,
                utility_achieved: decision.confidence,
                side_effects: Vec::new(),
                satisfaction: decision.confidence,
            },
            learned_lessons: Vec::new(),
            importance: decision.confidence,
        };
        
        let mut memory = self.experience_memory.write().await;
        memory.add_experience(experience);
        
        Ok(())
    }
    
    pub async fn get_current_state(&self) -> BehaviorState {
        self.current_state.read().await.clone()
    }
    
    pub fn send_update(&self, update: BehaviorUpdate) -> Result<()> {
        self.update_tx.send(update)
            .context("Failed to send behavior update")?;
        Ok(())
    }
}

// Implementation of subsystem components

impl TaskPlanner {
    async fn new(config: &PlanningConfig) -> Result<Self> {
        let mut planning_algorithms: HashMap<PlannerType, Box<dyn PlanningAlgorithm>> = HashMap::new();
        
        // Add planning algorithms based on configuration
        // For now, we'll use simplified implementations
        
        Ok(Self {
            config: config.clone(),
            planning_algorithms,
        })
    }
    
    async fn plan_tasks(&self, context: &PlanningContext, goals: &[Goal]) -> Result<Vec<Task>> {
        let mut tasks = Vec::new();
        
        for goal in goals {
            let task = self.create_task_for_goal(goal, context).await?;
            tasks.push(task);
        }
        
        Ok(tasks)
    }
    
    async fn create_task_for_goal(&self, goal: &Goal, _context: &PlanningContext) -> Result<Task> {
        let steps = match goal.goal_type {
            GoalType::Interact => {
                vec![
                    TaskStep {
                        step_id: "approach".to_string(),
                        description: "Approach the person".to_string(),
                        action: Action {
                            action_type: ActionType::MoveTo,
                            parameters: HashMap::new(),
                            target: Some("person".to_string()),
                        },
                        preconditions: Vec::new(),
                        postconditions: Vec::new(),
                        timeout: Some(Duration::from_secs(30)),
                    },
                    TaskStep {
                        step_id: "greet".to_string(),
                        description: "Greet the person".to_string(),
                        action: Action {
                            action_type: ActionType::Speak,
                            parameters: {
                                let mut params = HashMap::new();
                                params.insert("message".to_string(), 0.0);
                                params
                            },
                            target: Some("person".to_string()),
                        },
                        preconditions: Vec::new(),
                        postconditions: Vec::new(),
                        timeout: Some(Duration::from_secs(10)),
                    },
                ]
            },
            GoalType::Learn => {
                vec![
                    TaskStep {
                        step_id: "observe".to_string(),
                        description: "Observe the environment".to_string(),
                        action: Action {
                            action_type: ActionType::RecordData,
                            parameters: HashMap::new(),
                            target: None,
                        },
                        preconditions: Vec::new(),
                        postconditions: Vec::new(),
                        timeout: Some(Duration::from_secs(300)),
                    },
                ]
            },
            _ => {
                vec![
                    TaskStep {
                        step_id: "default".to_string(),
                        description: "Execute default action".to_string(),
                        action: Action {
                            action_type: ActionType::WaitFor,
                            parameters: HashMap::new(),
                            target: None,
                        },
                        preconditions: Vec::new(),
                        postconditions: Vec::new(),
                        timeout: Some(Duration::from_secs(60)),
                    },
                ]
            }
        };
        
        Ok(Task {
            task_id: format!("task_{}", goal.goal_id),
            task_type: match goal.goal_type {
                GoalType::Interact => TaskType::Social,
                GoalType::Navigate => TaskType::Navigation,
                GoalType::Learn => TaskType::Perception,
                _ => TaskType::Motion,
            },
            description: goal.description.clone(),
            steps,
            current_step: 0,
            estimated_duration: Duration::from_secs(60),
            start_time: Utc::now(),
        })
    }
}

impl GoalManager {
    async fn new(config: &GoalManagementConfig) -> Result<Self> {
        Ok(Self {
            config: config.clone(),
            active_goals: Arc::new(RwLock::new(VecDeque::new())),
            goal_history: Arc::new(RwLock::new(Vec::new())),
            goal_prioritizer: Box::new(DefaultGoalPrioritizer::new()),
        })
    }
    
    async fn start(&self) -> Result<()> {
        info!("Starting goal manager");
        Ok(())
    }
    
    async fn get_active_goals(&self) -> Vec<Goal> {
        self.active_goals.read().await.iter().cloned().collect()
    }
    
    async fn add_goal(&self, goal: Goal) -> Result<()> {
        let mut goals = self.active_goals.write().await;
        
        // Check if we can add more goals
        if goals.len() >= self.config.max_concurrent_goals {
            warn!("Maximum concurrent goals reached, removing oldest goal");
            goals.pop_front();
        }
        
        goals.push_back(goal);
        Ok(())
    }
}

struct DefaultGoalPrioritizer;

impl DefaultGoalPrioritizer {
    fn new() -> Self {
        Self
    }
}

impl GoalPrioritizer for DefaultGoalPrioritizer {
    fn prioritize_goals(&self, goals: &mut VecDeque<Goal>, _context: &PlanningContext) {
        // Simple priority-based sorting
        let mut goals_vec: Vec<Goal> = goals.drain(..).collect();
        goals_vec.sort_by(|a, b| b.priority.partial_cmp(&a.priority).unwrap());
        goals.extend(goals_vec);
    }
    
    fn should_add_goal(&self, _goal: &Goal, current_goals: &VecDeque<Goal>) -> bool {
        current_goals.len() < 5 // Simple check
    }
}

impl DecisionEngine {
    async fn new(config: &DecisionMakingConfig) -> Result<Self> {
        let utility_calculator = Arc::new(UtilityCalculator::new());
        
        Ok(Self {
            config: config.clone(),
            decision_strategies: HashMap::new(),
            utility_calculator,
        })
    }
    
    async fn make_decision(&self, alternatives: &[AlternativeBehavior], context: &PlanningContext) -> Result<BehaviorDecision> {
        if alternatives.is_empty() {
            return Err(anyhow::anyhow!("No behavior alternatives provided"));
        }
        
        // Simple utility-based decision making
        let mut best_alternative = &alternatives[0];
        let mut best_score = 0.0;
        
        for alternative in alternatives {
            let score = alternative.utility_score * alternative.feasibility * (1.0 - alternative.risk_level);
            if score > best_score {
                best_score = score;
                best_alternative = alternative;
            }
        }
        
        let confidence = best_score;
        let reasoning = format!("Selected behavior '{}' with utility {:.2}, feasibility {:.2}, risk {:.2}",
                              best_alternative.behavior.behavior_id, 
                              best_alternative.utility_score,
                              best_alternative.feasibility,
                              best_alternative.risk_level);
        
        Ok(BehaviorDecision {
            selected_behavior: best_alternative.behavior.clone(),
            confidence,
            reasoning,
            alternative_behaviors: alternatives.to_vec(),
            expected_outcomes: vec![
                ExpectedOutcome {
                    outcome_type: OutcomeType::GoalAchievement,
                    probability: confidence,
                    utility: best_alternative.utility_score,
                    time_to_achieve: Duration::from_secs(60),
                }
            ],
            risk_assessment: RiskAssessment {
                overall_risk: best_alternative.risk_level,
                safety_risk: best_alternative.risk_level * 0.3,
                social_risk: best_alternative.risk_level * 0.2,
                task_failure_risk: 1.0 - best_alternative.feasibility,
                mitigation_strategies: Vec::new(),
            },
        })
    }
}

impl UtilityCalculator {
    fn new() -> Self {
        Self {
            utility_functions: HashMap::new(),
        }
    }
}

impl AdaptationEngine {
    async fn new(config: &AdaptationConfig) -> Result<Self> {
        Ok(Self {
            config: config.clone(),
            adaptation_history: Arc::new(RwLock::new(Vec::new())),
            personality_model: Arc::new(RwLock::new(PersonalityModel {
                traits: {
                    let mut traits = HashMap::new();
                    traits.insert("extroversion".to_string(), 0.7);
                    traits.insert("agreeableness".to_string(), 0.8);
                    traits.insert("conscientiousness".to_string(), 0.9);
                    traits.insert("neuroticism".to_string(), 0.2);
                    traits.insert("openness".to_string(), 0.8);
                    traits
                },
                adaptation_rate: config.learning_rate,
                stability: 0.8,
            })),
        })
    }
    
    async fn start(&self) -> Result<()> {
        info!("Starting adaptation engine");
        Ok(())
    }
    
    async fn adapt_behavior(&self, behavior: &Behavior, _context: &PlanningContext) -> Result<Behavior> {
        if !self.config.adaptation_enabled {
            return Ok(behavior.clone());
        }
        
        // Simple adaptation: adjust parameters based on personality
        let mut adapted_behavior = behavior.clone();
        
        let personality = self.personality_model.read().await;
        
        // Adjust behavior intensity based on extroversion
        if let Some(extroversion) = personality.traits.get("extroversion") {
            if matches!(behavior.behavior_type, BehaviorType::Interacting | BehaviorType::Speaking) {
                adapted_behavior.priority *= extroversion;
            }
        }
        
        Ok(adapted_behavior)
    }
}

impl SocialBehaviorManager {
    async fn new(config: &SocialBehaviorConfig) -> Result<Self> {
        Ok(Self {
            config: config.clone(),
            social_rules: Arc::new(RwLock::new(SocialRuleSet::default())),
            interaction_patterns: Arc::new(RwLock::new(InteractionPatterns::default())),
        })
    }
    
    async fn adapt_behavior(&self, behavior: &Behavior, context: &PlanningContext) -> Result<Behavior> {
        if !self.config.social_awareness {
            return Ok(behavior.clone());
        }
        
        let mut adapted_behavior = behavior.clone();
        
        // Adjust behavior based on social context
        match context.social_context.interaction_mode {
            InteractionMode::Formal => {
                adapted_behavior.priority *= 0.8; // Be more reserved
            },
            InteractionMode::Casual => {
                adapted_behavior.priority *= 1.2; // Be more expressive
            },
            _ => {}
        }
        
        // Respect personal space
        if matches!(behavior.behavior_type, BehaviorType::Following | BehaviorType::Interacting) {
            let mut params = adapted_behavior.parameters.clone();
            params.insert("min_distance".to_string(), self.config.personal_space_radius.to_string());
            adapted_behavior.parameters = params;
        }
        
        Ok(adapted_behavior)
    }
}

impl BehaviorLibrary {
    async fn new() -> Result<Self> {
        let mut behaviors = HashMap::new();
        
        // Add basic behavior templates
        behaviors.insert("idle".to_string(), BehaviorTemplate {
            name: "idle".to_string(),
            behavior_type: BehaviorType::Idle,
            preconditions: Vec::new(),
            effects: Vec::new(),
            parameters: HashMap::new(),
            success_criteria: Vec::new(),
        });
        
        behaviors.insert("greet".to_string(), BehaviorTemplate {
            name: "greet".to_string(),
            behavior_type: BehaviorType::Interacting,
            preconditions: Vec::new(),
            effects: Vec::new(),
            parameters: {
                let mut params = HashMap::new();
                params.insert("greeting_type".to_string(), ParameterDefinition {
                    name: "greeting_type".to_string(),
                    parameter_type: "string".to_string(),
                    default_value: "hello".to_string(),
                    constraints: Vec::new(),
                });
                params
            },
            success_criteria: Vec::new(),
        });
        
        Ok(Self {
            behaviors,
            behavior_hierarchies: Vec::new(),
        })
    }
    
    fn get_behaviors_for_task(&self, task_type: &TaskType) -> Vec<&BehaviorTemplate> {
        self.behaviors.values()
            .filter(|template| {
                match (task_type, &template.behavior_type) {
                    (TaskType::Social, BehaviorType::Interacting) => true,
                    (TaskType::Communication, BehaviorType::Speaking) => true,
                    (TaskType::Navigation, BehaviorType::Navigating) => true,
                    (TaskType::Motion, BehaviorType::Idle) => true,
                    _ => false,
                }
            })
            .collect()
    }
}

impl ExperienceMemory {
    fn new(max_size: usize) -> Self {
        Self {
            experiences: VecDeque::new(),
            experience_index: HashMap::new(),
            max_size,
        }
    }
    
    fn add_experience(&mut self, experience: Experience) {
        if self.experiences.len() >= self.max_size {
            if let Some(old_exp) = self.experiences.pop_front() {
                // Remove from index
                if let Some(indices) = self.experience_index.get_mut(&old_exp.situation.situation_type.to_string()) {
                    indices.retain(|&idx| idx != 0);
                    // Update all indices
                    for idx in indices.iter_mut() {
                        *idx -= 1;
                    }
                }
            }
        }
        
        let new_index = self.experiences.len();
        self.experiences.push_back(experience.clone());
        
        // Update index
        let situation_key = experience.situation.situation_type.to_string();
        self.experience_index.entry(situation_key)
            .or_insert_with(Vec::new)
            .push(new_index);
    }
}

impl WorldModel {
    async fn new() -> Result<Self> {
        Ok(Self {
            entities: HashMap::new(),
            relationships: Vec::new(),
            environmental_state: EnvironmentalState {
                location: "unknown".to_string(),
                physical_conditions: HashMap::new(),
                social_conditions: HashMap::new(),
                dynamic_factors: Vec::new(),
            },
            temporal_state: TemporalState {
                current_time: Utc::now(),
                time_zone: "UTC".to_string(),
                schedule_state: ScheduleState {
                    current_activities: Vec::new(),
                    upcoming_activities: Vec::new(),
                    free_time_slots: Vec::new(),
                },
                temporal_patterns: Vec::new(),
            },
        })
    }
}

impl Default for SocialRuleSet {
    fn default() -> Self {
        Self {
            rules: vec![
                SocialRule {
                    rule_id: "personal_space".to_string(),
                    condition: SocialCondition {
                        context_requirements: vec!["human_present".to_string()],
                        participant_requirements: Vec::new(),
                        situation_requirements: Vec::new(),
                    },
                    action: SocialAction {
                        action_type: "maintain_distance".to_string(),
                        parameters: {
                            let mut params = HashMap::new();
                            params.insert("min_distance".to_string(), "1.2".to_string());
                            params
                        },
                        expected_outcome: "respectful_interaction".to_string(),
                    },
                    priority: 0.8,
                }
            ],
        }
    }
}

impl Default for InteractionPatterns {
    fn default() -> Self {
        Self {
            patterns: {
                let mut patterns = HashMap::new();
                patterns.insert("greeting".to_string(), InteractionPattern {
                    pattern_name: "greeting".to_string(),
                    triggers: vec!["human_approached".to_string()],
                    sequence: vec![
                        InteractionStep {
                            step_type: "approach".to_string(),
                            timing: Duration::from_secs(2),
                            required_actions: vec!["move_closer".to_string()],
                            expected_responses: vec!["attention".to_string()],
                        },
                        InteractionStep {
                            step_type: "greet".to_string(),
                            timing: Duration::from_secs(1),
                            required_actions: vec!["say_hello".to_string(), "wave".to_string()],
                            expected_responses: vec!["greeting_response".to_string()],
                        },
                    ],
                    success_criteria: vec!["mutual_acknowledgment".to_string()],
                });
                patterns
            },
        }
    }
}

impl ToString for SituationType {
    fn to_string(&self) -> String {
        match self {
            SituationType::Normal => "normal".to_string(),
            SituationType::Emergency => "emergency".to_string(),
            SituationType::Social => "social".to_string(),
            SituationType::Task => "task".to_string(),
            SituationType::Learning => "learning".to_string(),
            SituationType::Maintenance => "maintenance".to_string(),
        }
    }
}

impl Default for BehaviorConfig {
    fn default() -> Self {
        Self {
            planning: PlanningConfig {
                planner_type: PlannerType::HybridApproach,
                planning_horizon: Duration::from_secs(300),
                replanning_interval: Duration::from_secs(30),
                max_plan_depth: 5,
                contingency_planning: true,
            },
            decision_making: DecisionMakingConfig {
                decision_strategy: DecisionStrategy::UtilityBased,
                uncertainty_threshold: 0.3,
                confidence_required: 0.6,
                risk_tolerance: 0.4,
                time_pressure_factor: 0.5,
            },
            goal_management: GoalManagementConfig {
                max_concurrent_goals: 3,
                goal_prioritization: PrioritizationStrategy::Hybrid,
                goal_expiry_time: Duration::from_secs(3600),
                automatic_goal_generation: true,
            },
            adaptation: AdaptationConfig {
                adaptation_enabled: true,
                learning_rate: 0.1,
                adaptation_threshold: 0.2,
                personality_adaptation: true,
                context_adaptation: true,
            },
            social_behavior: SocialBehaviorConfig {
                social_awareness: true,
                personal_space_radius: 1.2,
                eye_contact_probability: 0.7,
                gesture_frequency: 0.5,
                politeness_level: 0.8,
                cultural_adaptation: true,
            },
            learning: LearningConfig {
                learning_enabled: true,
                experience_buffer_size: 1000,
                learning_algorithm: LearningAlgorithm::ReinforcementLearning,
                exploration_rate: 0.2,
                memory_retention: Duration::from_secs(86400), // 24 hours
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_behavior_planner_creation() {
        let config = BehaviorConfig::default();
        let planner = BehaviorPlanner::new(&config).await;
        assert!(planner.is_ok());
    }
    
    #[test]
    fn test_situation_assessment() {
        let situation = SituationAssessment {
            situation_type: SituationType::Social,
            urgency_level: 0.3,
            complexity_level: 0.5,
            ambiguity_level: 0.2,
            social_dynamics: SocialDynamics {
                human_count: 2,
                interaction_intensity: 0.6,
                social_roles: HashMap::new(),
                group_mood: Emotion::Happy,
                authority_structure: Vec::new(),
            },
        };
        
        assert_eq!(situation.situation_type.to_string(), "social");
        assert_eq!(situation.social_dynamics.human_count, 2);
    }
    
    #[test]
    fn test_behavior_decision() {
        let behavior = Behavior {
            behavior_id: "test_behavior".to_string(),
            behavior_type: BehaviorType::Interacting,
            priority: 0.8,
            parameters: HashMap::new(),
            start_time: Utc::now(),
            expected_duration: Some(Duration::from_secs(30)),
        };
        
        let decision = BehaviorDecision {
            selected_behavior: behavior,
            confidence: 0.9,
            reasoning: "High confidence interaction".to_string(),
            alternative_behaviors: Vec::new(),
            expected_outcomes: Vec::new(),
            risk_assessment: RiskAssessment {
                overall_risk: 0.1,
                safety_risk: 0.05,
                social_risk: 0.03,
                task_failure_risk: 0.02,
                mitigation_strategies: Vec::new(),
            },
        };
        
        assert_eq!(decision.confidence, 0.9);
        assert_eq!(decision.risk_assessment.overall_risk, 0.1);
    }
    
    #[test]
    fn test_goal_creation() {
        let goal = Goal {
            goal_id: "test_goal".to_string(),
            description: "Test interaction goal".to_string(),
            goal_type: GoalType::Interact,
            priority: 0.7,
            deadline: Some(Utc::now() + chrono::Duration::minutes(10)),
            completion_criteria: vec![
                CompletionCriterion {
                    criterion_type: "engagement".to_string(),
                    target_value: 0.8,
                    current_value: 0.0,
                    tolerance: 0.1,
                }
            ],
            progress: 0.0,
        };
        
        assert_eq!(goal.goal_type, GoalType::Interact);
        assert_eq!(goal.priority, 0.7);
        assert_eq!(goal.completion_criteria.len(), 1);
    }
    
    #[tokio::test]
    async fn test_experience_memory() {
        let mut memory = ExperienceMemory::new(3);
        
        for i in 0..5 {
            let experience = Experience {
                id: format!("exp_{}", i),
                timestamp: Utc::now(),
                situation: SituationAssessment {
                    situation_type: SituationType::Normal,
                    urgency_level: 0.1,
                    complexity_level: 0.1,
                    ambiguity_level: 0.1,
                    social_dynamics: SocialDynamics {
                        human_count: 0,
                        interaction_intensity: 0.0,
                        social_roles: HashMap::new(),
                        group_mood: Emotion::Neutral,
                        authority_structure: Vec::new(),
                    },
                },
                behavior_executed: format!("behavior_{}", i),
                outcome: ExperienceOutcome {
                    success: true,
                    utility_achieved: 0.8,
                    side_effects: Vec::new(),
                    satisfaction: 0.9,
                },
                learned_lessons: Vec::new(),
                importance: 0.5,
            };
            
            memory.add_experience(experience);
        }
        
        // Should only keep the last 3 experiences
        assert_eq!(memory.experiences.len(), 3);
        assert_eq!(memory.experiences[0].id, "exp_2");
        assert_eq!(memory.experiences[2].id, "exp_4");
    }
}