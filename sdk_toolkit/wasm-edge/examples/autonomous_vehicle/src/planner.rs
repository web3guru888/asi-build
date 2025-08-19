/*!
# Path Planning Module

Advanced path planning for autonomous vehicles using hybrid A* algorithm.
Provides global route planning, local trajectory generation, and dynamic obstacle avoidance.
*/

use anyhow::{Context, Result};
use log::{info, warn, error};
use nalgebra::{Point2, Point3, Vector2, Vector3};
use std::collections::{BinaryHeap, HashMap, HashSet, VecDeque};
use std::cmp::Ordering;
use tokio::time::Instant;
use wasm_edge_ai_sdk::prelude::*;

use crate::{DetectedObject, LaneMarking, TrafficSign, TrafficSignType};

/// Path planning configuration
#[derive(Debug, Clone)]
pub struct PlannerConfig {
    pub vehicle_dimensions: VehicleDimensions,
    pub kinematic_constraints: KinematicConstraints,
    pub planning_horizon: f64,        // seconds
    pub planning_resolution: f64,     // meters
    pub angular_resolution: f64,      // radians
    pub max_planning_time_ms: u64,
    pub safety_margins: SafetyMargins,
    pub cost_weights: CostWeights,
    pub smoothing_params: SmoothingParams,
}

#[derive(Debug, Clone)]
pub struct VehicleDimensions {
    pub length: f64,
    pub width: f64,
    pub wheelbase: f64,
    pub front_overhang: f64,
    pub rear_overhang: f64,
    pub turning_radius: f64,
}

#[derive(Debug, Clone)]
pub struct KinematicConstraints {
    pub max_speed: f64,              // m/s
    pub max_acceleration: f64,       // m/s²
    pub max_deceleration: f64,       // m/s²
    pub max_steering_angle: f64,     // radians
    pub max_steering_rate: f64,      // rad/s
    pub max_lateral_acceleration: f64, // m/s²
}

#[derive(Debug, Clone)]
pub struct SafetyMargins {
    pub static_obstacle_margin: f64,   // meters
    pub dynamic_obstacle_margin: f64,  // meters
    pub lane_boundary_margin: f64,     // meters
    pub following_distance: f64,       // meters
    pub time_to_collision_threshold: f64, // seconds
}

#[derive(Debug, Clone)]
pub struct CostWeights {
    pub distance_weight: f64,
    pub smoothness_weight: f64,
    pub speed_weight: f64,
    pub lane_keeping_weight: f64,
    pub obstacle_avoidance_weight: f64,
    pub traffic_rule_weight: f64,
}

#[derive(Debug, Clone)]
pub struct SmoothingParams {
    pub enable_smoothing: bool,
    pub smoothing_iterations: usize,
    pub smoothing_factor: f64,
    pub curvature_limit: f64,        // 1/meters
}

/// Path planning input data
#[derive(Debug, Clone)]
pub struct PlanningInput {
    pub current_pose: Pose2D,
    pub current_velocity: f64,
    pub goal_pose: Pose2D,
    pub lane_markings: Vec<LaneMarking>,
    pub detected_objects: Vec<DetectedObject>,
    pub traffic_signs: Vec<TrafficSign>,
    pub road_boundaries: Vec<RoadBoundary>,
    pub speed_limit: f64,
    pub timestamp: Instant,
}

#[derive(Debug, Clone)]
pub struct Pose2D {
    pub x: f64,
    pub y: f64,
    pub theta: f64, // heading angle in radians
}

#[derive(Debug, Clone)]
pub struct RoadBoundary {
    pub points: Vec<Point2<f64>>,
    pub boundary_type: BoundaryType,
}

#[derive(Debug, Clone, PartialEq)]
pub enum BoundaryType {
    LeftCurb,
    RightCurb,
    CenterLine,
    LaneBoundary,
    Construction,
}

/// Planned path output
#[derive(Debug, Clone)]
pub struct PlannedPath {
    pub trajectory: Trajectory,
    pub maneuver_type: ManeuverType,
    pub confidence: f64,
    pub planning_time_ms: f64,
    pub total_cost: f64,
    pub safety_assessment: SafetyAssessment,
    pub timestamp: Instant,
}

#[derive(Debug, Clone)]
pub struct Trajectory {
    pub waypoints: Vec<Waypoint>,
    pub total_distance: f64,
    pub estimated_duration: f64,
    pub max_curvature: f64,
    pub smoothness_score: f64,
}

#[derive(Debug, Clone)]
pub struct Waypoint {
    pub pose: Pose2D,
    pub velocity: f64,
    pub acceleration: f64,
    pub steering_angle: f64,
    pub curvature: f64,
    pub time: f64,
    pub lane_offset: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ManeuverType {
    LaneKeeping,
    LaneChange,
    Overtaking,
    Merging,
    TurnLeft,
    TurnRight,
    UTurn,
    Parking,
    Emergency,
}

#[derive(Debug, Clone)]
pub struct SafetyAssessment {
    pub collision_risk: f64,
    pub time_to_collision: Option<f64>,
    pub closest_obstacle_distance: f64,
    pub lane_departure_risk: f64,
    pub traffic_rule_violations: Vec<TrafficRuleViolation>,
    pub overall_safety_score: f64,
}

#[derive(Debug, Clone)]
pub struct TrafficRuleViolation {
    pub violation_type: ViolationType,
    pub severity: Severity,
    pub description: String,
    pub position: Point2<f64>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ViolationType {
    SpeedLimit,
    StopSign,
    RedLight,
    YieldSign,
    NoEntry,
    WrongWay,
    LaneViolation,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Severity {
    Low,
    Medium,
    High,
    Critical,
}

/// A* search node for path planning
#[derive(Debug, Clone)]
struct SearchNode {
    pose: Pose2D,
    g_cost: f64,      // cost from start
    h_cost: f64,      // heuristic cost to goal
    f_cost: f64,      // g_cost + h_cost
    parent: Option<Box<SearchNode>>,
    velocity: f64,
    steering_angle: f64,
}

impl PartialEq for SearchNode {
    fn eq(&self, other: &Self) -> bool {
        self.f_cost == other.f_cost
    }
}

impl Eq for SearchNode {}

impl PartialOrd for SearchNode {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for SearchNode {
    fn cmp(&self, other: &Self) -> Ordering {
        // Reverse ordering for min-heap
        other.f_cost.partial_cmp(&self.f_cost).unwrap_or(Ordering::Equal)
    }
}

/// Main path planning system
pub struct PathPlanner {
    config: PlannerConfig,
    occupancy_grid: OccupancyGrid,
    lane_map: LaneMap,
    traffic_rules: TrafficRuleEngine,
    motion_primitives: Vec<MotionPrimitive>,
    path_smoother: PathSmoother,
    collision_checker: CollisionChecker,
}

struct OccupancyGrid {
    grid: Vec<Vec<f64>>,
    resolution: f64,
    width: usize,
    height: usize,
    origin: Point2<f64>,
}

struct LaneMap {
    lanes: Vec<Lane>,
    lane_graph: HashMap<usize, Vec<usize>>, // lane connections
}

#[derive(Debug, Clone)]
struct Lane {
    id: usize,
    centerline: Vec<Point2<f64>>,
    left_boundary: Vec<Point2<f64>>,
    right_boundary: Vec<Point2<f64>>,
    width: f64,
    speed_limit: f64,
    lane_type: LaneType,
}

#[derive(Debug, Clone, PartialEq)]
enum LaneType {
    Driving,
    Parking,
    Emergency,
    BusLane,
    TurnLane,
    MergeLane,
}

struct TrafficRuleEngine {
    traffic_signs: Vec<TrafficSign>,
    speed_limits: HashMap<usize, f64>, // lane_id -> speed_limit
    right_of_way_rules: Vec<RightOfWayRule>,
}

#[derive(Debug, Clone)]
struct RightOfWayRule {
    intersection_id: usize,
    priority_lanes: Vec<usize>,
    yield_lanes: Vec<usize>,
}

#[derive(Debug, Clone)]
struct MotionPrimitive {
    id: usize,
    trajectory: Vec<Pose2D>,
    duration: f64,
    final_velocity: f64,
    final_steering_angle: f64,
    curvature: f64,
}

struct PathSmoother {
    params: SmoothingParams,
}

struct CollisionChecker {
    vehicle_dims: VehicleDimensions,
    safety_margins: SafetyMargins,
}

impl PathPlanner {
    /// Create new path planner
    pub fn new(config: &PlannerConfig) -> Result<Self> {
        info!("Initializing path planner");
        
        // Initialize occupancy grid
        let grid_size = (100.0 / config.planning_resolution) as usize; // 100m x 100m grid
        let occupancy_grid = OccupancyGrid::new(grid_size, grid_size, config.planning_resolution);
        
        // Initialize lane map
        let lane_map = LaneMap::new();
        
        // Initialize traffic rule engine
        let traffic_rules = TrafficRuleEngine::new();
        
        // Generate motion primitives
        let motion_primitives = Self::generate_motion_primitives(config)?;
        
        // Initialize path smoother
        let path_smoother = PathSmoother::new(&config.smoothing_params);
        
        // Initialize collision checker
        let collision_checker = CollisionChecker::new(
            &config.vehicle_dimensions,
            &config.safety_margins,
        );
        
        Ok(Self {
            config: config.clone(),
            occupancy_grid,
            lane_map,
            traffic_rules,
            motion_primitives,
            path_smoother,
            collision_checker,
        })
    }
    
    /// Plan path from current pose to goal
    pub async fn plan_path(&mut self, input: &PlanningInput) -> Result<PlannedPath> {
        let start_time = Instant::now();
        
        info!("Planning path from ({:.2}, {:.2}) to ({:.2}, {:.2})",
              input.current_pose.x, input.current_pose.y,
              input.goal_pose.x, input.goal_pose.y);
        
        // Update world model
        self.update_world_model(input).await?;
        
        // Determine maneuver type
        let maneuver_type = self.classify_maneuver(input)?;
        
        // Plan global path using A*
        let global_path = self.plan_global_path(&input.current_pose, &input.goal_pose).await?;
        
        // Generate local trajectory
        let local_trajectory = self.generate_local_trajectory(&global_path, input).await?;
        
        // Smooth trajectory
        let smoothed_trajectory = if self.config.smoothing_params.enable_smoothing {
            self.path_smoother.smooth(&local_trajectory)?
        } else {
            local_trajectory
        };
        
        // Assess safety
        let safety_assessment = self.assess_path_safety(&smoothed_trajectory, input)?;
        
        // Calculate total cost
        let total_cost = self.calculate_path_cost(&smoothed_trajectory, input)?;
        
        // Calculate confidence
        let confidence = self.calculate_confidence(&smoothed_trajectory, &safety_assessment);
        
        let planning_time = start_time.elapsed();
        
        info!("Path planning completed in {:.2}ms, confidence: {:.2}", 
              planning_time.as_millis(), confidence);
        
        Ok(PlannedPath {
            trajectory: smoothed_trajectory,
            maneuver_type,
            confidence,
            planning_time_ms: planning_time.as_secs_f64() * 1000.0,
            total_cost,
            safety_assessment,
            timestamp: start_time,
        })
    }
    
    /// Update world model with sensor data
    async fn update_world_model(&mut self, input: &PlanningInput) -> Result<()> {
        // Update occupancy grid with detected objects
        self.occupancy_grid.clear();
        
        for object in &input.detected_objects {
            self.occupancy_grid.add_obstacle(
                Point2::new(object.position.x, object.position.y),
                object.dimensions.x.max(object.dimensions.y), // use max dimension as radius
                1.0, // full occupancy
            );
        }
        
        // Update lane map
        self.lane_map.update_from_markings(&input.lane_markings);
        
        // Update traffic rules
        self.traffic_rules.update_signs(&input.traffic_signs);
        
        Ok(())
    }
    
    /// Classify the type of maneuver needed
    fn classify_maneuver(&self, input: &PlanningInput) -> Result<ManeuverType> {
        let distance_to_goal = ((input.goal_pose.x - input.current_pose.x).powi(2) +
                               (input.goal_pose.y - input.current_pose.y).powi(2)).sqrt();
        
        let heading_diff = (input.goal_pose.theta - input.current_pose.theta).abs();
        
        // Simple heuristic-based classification
        if distance_to_goal < 5.0 {
            if heading_diff > std::f64::consts::PI / 2.0 {
                return Ok(ManeuverType::UTurn);
            } else {
                return Ok(ManeuverType::Parking);
            }
        }
        
        // Check for lane change requirement
        if self.requires_lane_change(input) {
            Ok(ManeuverType::LaneChange)
        } else if heading_diff > std::f64::consts::PI / 4.0 {
            if input.goal_pose.theta > input.current_pose.theta {
                Ok(ManeuverType::TurnLeft)
            } else {
                Ok(ManeuverType::TurnRight)
            }
        } else {
            Ok(ManeuverType::LaneKeeping)
        }
    }
    
    /// Check if lane change is required
    fn requires_lane_change(&self, input: &PlanningInput) -> bool {
        // Check if goal is in a different lane
        let current_lane = self.lane_map.find_closest_lane(&Point2::new(
            input.current_pose.x, 
            input.current_pose.y
        ));
        
        let goal_lane = self.lane_map.find_closest_lane(&Point2::new(
            input.goal_pose.x, 
            input.goal_pose.y
        ));
        
        current_lane != goal_lane
    }
    
    /// Plan global path using hybrid A*
    async fn plan_global_path(&self, start: &Pose2D, goal: &Pose2D) -> Result<Vec<Pose2D>> {
        let mut open_set = BinaryHeap::new();
        let mut closed_set = HashSet::new();
        let mut came_from: HashMap<String, SearchNode> = HashMap::new();
        
        // Create start node
        let start_node = SearchNode {
            pose: start.clone(),
            g_cost: 0.0,
            h_cost: self.heuristic_cost(start, goal),
            f_cost: 0.0,
            parent: None,
            velocity: 0.0,
            steering_angle: 0.0,
        };
        
        let mut start_node = start_node;
        start_node.f_cost = start_node.g_cost + start_node.h_cost;
        
        open_set.push(start_node);
        
        let max_iterations = (self.config.max_planning_time_ms * 10) as usize; // Rough estimate
        let mut iterations = 0;
        
        while let Some(current) = open_set.pop() {
            iterations += 1;
            if iterations > max_iterations {
                warn!("Path planning reached maximum iterations");
                break;
            }
            
            // Check if goal reached
            if self.is_goal_reached(&current.pose, goal) {
                return Ok(self.reconstruct_path(current));
            }
            
            let current_key = self.pose_to_key(&current.pose);
            closed_set.insert(current_key.clone());
            
            // Expand neighbors using motion primitives
            for primitive in &self.motion_primitives {
                let next_pose = self.apply_motion_primitive(&current.pose, primitive);
                let next_key = self.pose_to_key(&next_pose);
                
                if closed_set.contains(&next_key) {
                    continue;
                }
                
                // Check collision
                if self.collision_checker.check_path_collision(&current.pose, &next_pose, &self.occupancy_grid) {
                    continue;
                }
                
                let tentative_g_cost = current.g_cost + self.motion_cost(&current.pose, &next_pose, primitive);
                
                let neighbor = SearchNode {
                    pose: next_pose,
                    g_cost: tentative_g_cost,
                    h_cost: self.heuristic_cost(&next_pose, goal),
                    f_cost: tentative_g_cost + self.heuristic_cost(&next_pose, goal),
                    parent: Some(Box::new(current.clone())),
                    velocity: primitive.final_velocity,
                    steering_angle: primitive.final_steering_angle,
                };
                
                // Check if this path to neighbor is better
                if let Some(existing) = came_from.get(&next_key) {
                    if tentative_g_cost >= existing.g_cost {
                        continue;
                    }
                }
                
                came_from.insert(next_key, neighbor.clone());
                open_set.push(neighbor);
            }
        }
        
        Err(anyhow::anyhow!("No path found to goal"))
    }
    
    /// Generate motion primitives for vehicle motion
    fn generate_motion_primitives(config: &PlannerConfig) -> Result<Vec<MotionPrimitive>> {
        let mut primitives = Vec::new();
        let mut id = 0;
        
        let dt = 0.5; // time step
        let velocities = vec![0.0, 5.0, 10.0, 15.0]; // m/s
        let steering_angles = vec![-0.5, -0.25, 0.0, 0.25, 0.5]; // radians
        
        for &velocity in &velocities {
            for &steering_angle in &steering_angles {
                if steering_angle.abs() > config.kinematic_constraints.max_steering_angle {
                    continue;
                }
                
                let mut trajectory = Vec::new();
                let mut pose = Pose2D { x: 0.0, y: 0.0, theta: 0.0 };
                
                // Generate trajectory using bicycle model
                for step in 0..10 { // 5 second primitive
                    trajectory.push(pose.clone());
                    
                    // Bicycle model kinematics
                    let angular_velocity = velocity * steering_angle.tan() / config.vehicle_dimensions.wheelbase;
                    
                    pose.x += velocity * pose.theta.cos() * dt;
                    pose.y += velocity * pose.theta.sin() * dt;
                    pose.theta += angular_velocity * dt;
                }
                
                let curvature = if velocity > 0.1 {
                    steering_angle.tan() / config.vehicle_dimensions.wheelbase
                } else {
                    0.0
                };
                
                primitives.push(MotionPrimitive {
                    id,
                    trajectory,
                    duration: dt * 10.0,
                    final_velocity: velocity,
                    final_steering_angle: steering_angle,
                    curvature,
                });
                
                id += 1;
            }
        }
        
        Ok(primitives)
    }
    
    /// Apply motion primitive to current pose
    fn apply_motion_primitive(&self, current_pose: &Pose2D, primitive: &MotionPrimitive) -> Pose2D {
        if primitive.trajectory.is_empty() {
            return current_pose.clone();
        }
        
        let final_offset = primitive.trajectory.last().unwrap();
        
        // Transform primitive trajectory to current pose
        let cos_theta = current_pose.theta.cos();
        let sin_theta = current_pose.theta.sin();
        
        Pose2D {
            x: current_pose.x + final_offset.x * cos_theta - final_offset.y * sin_theta,
            y: current_pose.y + final_offset.x * sin_theta + final_offset.y * cos_theta,
            theta: current_pose.theta + final_offset.theta,
        }
    }
    
    /// Calculate heuristic cost (Euclidean distance + heading difference)
    fn heuristic_cost(&self, pose: &Pose2D, goal: &Pose2D) -> f64 {
        let distance = ((goal.x - pose.x).powi(2) + (goal.y - pose.y).powi(2)).sqrt();
        let heading_diff = (goal.theta - pose.theta).abs().min(2.0 * std::f64::consts::PI - (goal.theta - pose.theta).abs());
        
        distance + heading_diff * 5.0 // Weight heading difference
    }
    
    /// Calculate motion cost
    fn motion_cost(&self, from: &Pose2D, to: &Pose2D, primitive: &MotionPrimitive) -> f64 {
        let distance = ((to.x - from.x).powi(2) + (to.y - from.y).powi(2)).sqrt();
        let heading_change = (to.theta - from.theta).abs();
        let curvature_cost = primitive.curvature.abs() * 2.0;
        
        distance + heading_change + curvature_cost
    }
    
    /// Check if goal is reached
    fn is_goal_reached(&self, pose: &Pose2D, goal: &Pose2D) -> bool {
        let distance = ((goal.x - pose.x).powi(2) + (goal.y - pose.y).powi(2)).sqrt();
        let heading_diff = (goal.theta - pose.theta).abs();
        
        distance < self.config.planning_resolution && heading_diff < self.config.angular_resolution
    }
    
    /// Convert pose to discretized key
    fn pose_to_key(&self, pose: &Pose2D) -> String {
        let x_discrete = (pose.x / self.config.planning_resolution).round() as i32;
        let y_discrete = (pose.y / self.config.planning_resolution).round() as i32;
        let theta_discrete = (pose.theta / self.config.angular_resolution).round() as i32;
        
        format!("{}_{}_{}",x_discrete, y_discrete, theta_discrete)
    }
    
    /// Reconstruct path from goal node
    fn reconstruct_path(&self, goal_node: SearchNode) -> Vec<Pose2D> {
        let mut path = Vec::new();
        let mut current = Some(Box::new(goal_node));
        
        while let Some(node) = current {
            path.push(node.pose.clone());
            current = node.parent;
        }
        
        path.reverse();
        path
    }
    
    /// Generate local trajectory with velocities and timing
    async fn generate_local_trajectory(&self, global_path: &[Pose2D], input: &PlanningInput) -> Result<Trajectory> {
        if global_path.is_empty() {
            return Err(anyhow::anyhow!("Empty global path"));
        }
        
        let mut waypoints = Vec::new();
        let mut total_distance = 0.0;
        let mut current_time = 0.0;
        
        for (i, pose) in global_path.iter().enumerate() {
            let (velocity, acceleration) = self.calculate_speed_profile(i, global_path, input)?;
            
            let steering_angle = if i < global_path.len() - 1 {
                self.calculate_steering_angle(&global_path[i], &global_path[i + 1])?
            } else {
                0.0
            };
            
            let curvature = if i > 0 && i < global_path.len() - 1 {
                self.calculate_curvature(&global_path[i - 1], &global_path[i], &global_path[i + 1])
            } else {
                0.0
            };
            
            let lane_offset = self.calculate_lane_offset(pose, input);
            
            if i > 0 {
                let segment_distance = ((pose.x - global_path[i - 1].x).powi(2) + 
                                      (pose.y - global_path[i - 1].y).powi(2)).sqrt();
                total_distance += segment_distance;
                
                if velocity > 0.01 {
                    current_time += segment_distance / velocity;
                }
            }
            
            waypoints.push(Waypoint {
                pose: pose.clone(),
                velocity,
                acceleration,
                steering_angle,
                curvature,
                time: current_time,
                lane_offset,
            });
        }
        
        let max_curvature = waypoints.iter()
            .map(|w| w.curvature.abs())
            .max_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal))
            .unwrap_or(0.0);
        
        let smoothness_score = self.calculate_smoothness_score(&waypoints);
        
        Ok(Trajectory {
            waypoints,
            total_distance,
            estimated_duration: current_time,
            max_curvature,
            smoothness_score,
        })
    }
    
    /// Calculate speed profile for trajectory
    fn calculate_speed_profile(&self, index: usize, path: &[Pose2D], input: &PlanningInput) -> Result<(f64, f64)> {
        let base_speed = input.speed_limit.min(self.config.kinematic_constraints.max_speed);
        
        // Apply speed limits from traffic signs
        let mut speed_limit = base_speed;
        for sign in &input.traffic_signs {
            if let TrafficSignType::SpeedLimit(limit) = sign.sign_type {
                let distance_to_sign = ((sign.position.x - path[index].x).powi(2) + 
                                       (sign.position.y - path[index].y).powi(2)).sqrt();
                if distance_to_sign < 50.0 { // Within 50m of sign
                    speed_limit = speed_limit.min(limit as f64 / 3.6); // Convert km/h to m/s
                }
            }
        }
        
        // Reduce speed for curvature
        if index > 0 && index < path.len() - 1 {
            let curvature = self.calculate_curvature(&path[index - 1], &path[index], &path[index + 1]);
            if curvature.abs() > 0.01 {
                let curve_speed = (self.config.kinematic_constraints.max_lateral_acceleration / curvature.abs()).sqrt();
                speed_limit = speed_limit.min(curve_speed);
            }
        }
        
        // Reduce speed near obstacles
        for object in &input.detected_objects {
            let distance_to_obstacle = ((object.position.x - path[index].x).powi(2) + 
                                       (object.position.y - path[index].y).powi(2)).sqrt();
            if distance_to_obstacle < self.config.safety_margins.dynamic_obstacle_margin * 3.0 {
                speed_limit *= 0.5; // Reduce speed by 50%
            }
        }
        
        // Simple acceleration calculation
        let acceleration = if index > 0 {
            let prev_velocity = speed_limit; // Simplified
            0.0 // Constant velocity for now
        } else {
            0.0
        };
        
        Ok((speed_limit, acceleration))
    }
    
    /// Calculate steering angle between two poses
    fn calculate_steering_angle(&self, current: &Pose2D, next: &Pose2D) -> Result<f64> {
        let dx = next.x - current.x;
        let dy = next.y - current.y;
        let desired_heading = dy.atan2(dx);
        let heading_error = desired_heading - current.theta;
        
        // Normalize angle
        let mut normalized_error = heading_error;
        while normalized_error > std::f64::consts::PI {
            normalized_error -= 2.0 * std::f64::consts::PI;
        }
        while normalized_error < -std::f64::consts::PI {
            normalized_error += 2.0 * std::f64::consts::PI;
        }
        
        // Simple proportional control for steering
        let steering_angle = normalized_error * 0.5; // Proportional gain
        
        Ok(steering_angle.max(-self.config.kinematic_constraints.max_steering_angle)
                        .min(self.config.kinematic_constraints.max_steering_angle))
    }
    
    /// Calculate curvature at a point
    fn calculate_curvature(&self, prev: &Pose2D, current: &Pose2D, next: &Pose2D) -> f64 {
        let dx1 = current.x - prev.x;
        let dy1 = current.y - prev.y;
        let dx2 = next.x - current.x;
        let dy2 = next.y - current.y;
        
        let cross_product = dx1 * dy2 - dy1 * dx2;
        let distance1 = (dx1.powi(2) + dy1.powi(2)).sqrt();
        let distance2 = (dx2.powi(2) + dy2.powi(2)).sqrt();
        
        if distance1 < 1e-6 || distance2 < 1e-6 {
            return 0.0;
        }
        
        2.0 * cross_product / (distance1 * distance2 * (distance1 + distance2))
    }
    
    /// Calculate offset from lane center
    fn calculate_lane_offset(&self, pose: &Pose2D, input: &PlanningInput) -> f64 {
        // Find closest lane marking
        let position = Point2::new(pose.x, pose.y);
        
        let mut min_distance = f64::INFINITY;
        for marking in &input.lane_markings {
            for point in &marking.points {
                let distance = ((point.x - position.x).powi(2) + (point.y - position.y).powi(2)).sqrt();
                if distance < min_distance {
                    min_distance = distance;
                }
            }
        }
        
        min_distance // Simplified - would calculate signed distance
    }
    
    /// Calculate smoothness score for trajectory
    fn calculate_smoothness_score(&self, waypoints: &[Waypoint]) -> f64 {
        if waypoints.len() < 3 {
            return 1.0;
        }
        
        let mut total_jerk = 0.0;
        for i in 1..waypoints.len() - 1 {
            let accel_change = waypoints[i + 1].acceleration - waypoints[i].acceleration;
            let time_diff = waypoints[i + 1].time - waypoints[i].time;
            if time_diff > 0.0 {
                let jerk = accel_change / time_diff;
                total_jerk += jerk.abs();
            }
        }
        
        // Convert to score (0-1, higher is smoother)
        let avg_jerk = total_jerk / (waypoints.len() - 2) as f64;
        (1.0 / (1.0 + avg_jerk)).max(0.0).min(1.0)
    }
    
    /// Assess safety of planned path
    fn assess_path_safety(&self, trajectory: &Trajectory, input: &PlanningInput) -> Result<SafetyAssessment> {
        let mut collision_risk = 0.0;
        let mut time_to_collision: Option<f64> = None;
        let mut closest_obstacle_distance = f64::INFINITY;
        let mut lane_departure_risk = 0.0;
        let mut traffic_rule_violations = Vec::new();
        
        // Check collision risk with detected objects
        for waypoint in &trajectory.waypoints {
            for object in &input.detected_objects {
                let distance = ((object.position.x - waypoint.pose.x).powi(2) + 
                               (object.position.y - waypoint.pose.y).powi(2)).sqrt();
                
                closest_obstacle_distance = closest_obstacle_distance.min(distance);
                
                if distance < self.config.safety_margins.dynamic_obstacle_margin {
                    collision_risk = collision_risk.max(1.0 - distance / self.config.safety_margins.dynamic_obstacle_margin);
                    
                    if time_to_collision.is_none() && waypoint.velocity > 0.1 {
                        time_to_collision = Some(distance / waypoint.velocity);
                    }
                }
            }
            
            // Check lane departure risk
            if waypoint.lane_offset.abs() > 1.5 { // Assuming 3m lane width
                lane_departure_risk = lane_departure_risk.max(waypoint.lane_offset.abs() / 1.5 - 1.0);
            }
        }
        
        // Check traffic rule violations
        for waypoint in &trajectory.waypoints {
            for sign in &input.traffic_signs {
                let distance_to_sign = ((sign.position.x - waypoint.pose.x).powi(2) + 
                                       (sign.position.y - waypoint.pose.y).powi(2)).sqrt();
                
                if distance_to_sign < 10.0 { // Within 10m of sign
                    match sign.sign_type {
                        TrafficSignType::Stop => {
                            if waypoint.velocity > 0.1 {
                                traffic_rule_violations.push(TrafficRuleViolation {
                                    violation_type: ViolationType::StopSign,
                                    severity: Severity::High,
                                    description: "Vehicle not stopping at stop sign".to_string(),
                                    position: Point2::new(waypoint.pose.x, waypoint.pose.y),
                                });
                            }
                        },
                        TrafficSignType::SpeedLimit(limit) => {
                            if waypoint.velocity > (limit as f64 / 3.6) * 1.1 { // 10% tolerance
                                traffic_rule_violations.push(TrafficRuleViolation {
                                    violation_type: ViolationType::SpeedLimit,
                                    severity: Severity::Medium,
                                    description: format!("Speed limit violation: {} km/h", waypoint.velocity * 3.6),
                                    position: Point2::new(waypoint.pose.x, waypoint.pose.y),
                                });
                            }
                        },
                        _ => {}
                    }
                }
            }
        }
        
        // Calculate overall safety score
        let overall_safety_score = (1.0 - collision_risk) * 
                                  (1.0 - lane_departure_risk.min(1.0)) * 
                                  if traffic_rule_violations.is_empty() { 1.0 } else { 0.5 };
        
        Ok(SafetyAssessment {
            collision_risk,
            time_to_collision,
            closest_obstacle_distance,
            lane_departure_risk,
            traffic_rule_violations,
            overall_safety_score: overall_safety_score.max(0.0).min(1.0),
        })
    }
    
    /// Calculate total cost of path
    fn calculate_path_cost(&self, trajectory: &Trajectory, input: &PlanningInput) -> Result<f64> {
        let mut total_cost = 0.0;
        
        // Distance cost
        total_cost += trajectory.total_distance * self.config.cost_weights.distance_weight;
        
        // Smoothness cost (inverse of smoothness score)
        total_cost += (1.0 - trajectory.smoothness_score) * self.config.cost_weights.smoothness_weight;
        
        // Speed cost (prefer higher speeds within limits)
        let avg_speed = trajectory.waypoints.iter()
            .map(|w| w.velocity)
            .sum::<f64>() / trajectory.waypoints.len() as f64;
        let normalized_speed = 1.0 - (avg_speed / input.speed_limit).min(1.0);
        total_cost += normalized_speed * self.config.cost_weights.speed_weight;
        
        // Lane keeping cost
        let avg_lane_offset = trajectory.waypoints.iter()
            .map(|w| w.lane_offset.abs())
            .sum::<f64>() / trajectory.waypoints.len() as f64;
        total_cost += avg_lane_offset * self.config.cost_weights.lane_keeping_weight;
        
        // Obstacle avoidance cost
        let min_obstacle_distance = input.detected_objects.iter()
            .map(|obj| {
                trajectory.waypoints.iter()
                    .map(|w| ((obj.position.x - w.pose.x).powi(2) + (obj.position.y - w.pose.y).powi(2)).sqrt())
                    .min_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal))
                    .unwrap_or(f64::INFINITY)
            })
            .min_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal))
            .unwrap_or(f64::INFINITY);
        
        if min_obstacle_distance < self.config.safety_margins.dynamic_obstacle_margin * 2.0 {
            total_cost += (1.0 - min_obstacle_distance / (self.config.safety_margins.dynamic_obstacle_margin * 2.0)) * 
                         self.config.cost_weights.obstacle_avoidance_weight;
        }
        
        Ok(total_cost)
    }
    
    /// Calculate confidence in planned path
    fn calculate_confidence(&self, trajectory: &Trajectory, safety: &SafetyAssessment) -> f64 {
        let factors = vec![
            safety.overall_safety_score,
            trajectory.smoothness_score,
            if trajectory.max_curvature < self.config.smoothing_params.curvature_limit { 1.0 } else { 0.5 },
            if safety.traffic_rule_violations.is_empty() { 1.0 } else { 0.3 },
        ];
        
        factors.iter().sum::<f64>() / factors.len() as f64
    }
}

// Helper struct implementations

impl OccupancyGrid {
    fn new(width: usize, height: usize, resolution: f64) -> Self {
        Self {
            grid: vec![vec![0.0; height]; width],
            resolution,
            width,
            height,
            origin: Point2::new(0.0, 0.0),
        }
    }
    
    fn clear(&mut self) {
        for row in &mut self.grid {
            for cell in row {
                *cell = 0.0;
            }
        }
    }
    
    fn add_obstacle(&mut self, position: Point2<f64>, radius: f64, occupancy: f64) {
        let grid_x = ((position.x - self.origin.x) / self.resolution) as i32;
        let grid_y = ((position.y - self.origin.y) / self.resolution) as i32;
        let grid_radius = (radius / self.resolution) as i32;
        
        for dx in -grid_radius..=grid_radius {
            for dy in -grid_radius..=grid_radius {
                let x = grid_x + dx;
                let y = grid_y + dy;
                
                if x >= 0 && x < self.width as i32 && y >= 0 && y < self.height as i32 {
                    let distance = ((dx * dx + dy * dy) as f64).sqrt() * self.resolution;
                    if distance <= radius {
                        let x = x as usize;
                        let y = y as usize;
                        self.grid[x][y] = self.grid[x][y].max(occupancy);
                    }
                }
            }
        }
    }
    
    fn is_occupied(&self, position: Point2<f64>, threshold: f64) -> bool {
        let grid_x = ((position.x - self.origin.x) / self.resolution) as i32;
        let grid_y = ((position.y - self.origin.y) / self.resolution) as i32;
        
        if grid_x >= 0 && grid_x < self.width as i32 && grid_y >= 0 && grid_y < self.height as i32 {
            self.grid[grid_x as usize][grid_y as usize] > threshold
        } else {
            true // Unknown areas considered occupied
        }
    }
}

impl LaneMap {
    fn new() -> Self {
        Self {
            lanes: Vec::new(),
            lane_graph: HashMap::new(),
        }
    }
    
    fn update_from_markings(&mut self, _markings: &[LaneMarking]) {
        // Simplified - would process lane markings to build lane map
    }
    
    fn find_closest_lane(&self, position: &Point2<f64>) -> Option<usize> {
        let mut closest_lane = None;
        let mut min_distance = f64::INFINITY;
        
        for (i, lane) in self.lanes.iter().enumerate() {
            for point in &lane.centerline {
                let distance = ((point.x - position.x).powi(2) + (point.y - position.y).powi(2)).sqrt();
                if distance < min_distance {
                    min_distance = distance;
                    closest_lane = Some(i);
                }
            }
        }
        
        closest_lane
    }
}

impl TrafficRuleEngine {
    fn new() -> Self {
        Self {
            traffic_signs: Vec::new(),
            speed_limits: HashMap::new(),
            right_of_way_rules: Vec::new(),
        }
    }
    
    fn update_signs(&mut self, signs: &[TrafficSign]) {
        self.traffic_signs = signs.to_vec();
    }
}

impl PathSmoother {
    fn new(params: &SmoothingParams) -> Self {
        Self {
            params: params.clone(),
        }
    }
    
    fn smooth(&self, trajectory: &Trajectory) -> Result<Trajectory> {
        if !self.params.enable_smoothing || trajectory.waypoints.len() < 3 {
            return Ok(trajectory.clone());
        }
        
        let mut smoothed_waypoints = trajectory.waypoints.clone();
        
        // Apply smoothing iterations
        for _ in 0..self.params.smoothing_iterations {
            for i in 1..smoothed_waypoints.len() - 1 {
                let prev = &smoothed_waypoints[i - 1];
                let next = &smoothed_waypoints[i + 1];
                let current = &mut smoothed_waypoints[i];
                
                // Smooth position
                let smoothed_x = current.pose.x + 
                    self.params.smoothing_factor * ((prev.pose.x + next.pose.x) / 2.0 - current.pose.x);
                let smoothed_y = current.pose.y + 
                    self.params.smoothing_factor * ((prev.pose.y + next.pose.y) / 2.0 - current.pose.y);
                
                current.pose.x = smoothed_x;
                current.pose.y = smoothed_y;
                
                // Smooth velocity
                let smoothed_velocity = current.velocity + 
                    self.params.smoothing_factor * ((prev.velocity + next.velocity) / 2.0 - current.velocity);
                current.velocity = smoothed_velocity;
            }
        }
        
        // Recalculate trajectory properties
        let mut smoothed_trajectory = trajectory.clone();
        smoothed_trajectory.waypoints = smoothed_waypoints;
        smoothed_trajectory.smoothness_score = self.calculate_smoothness(&smoothed_trajectory.waypoints);
        
        Ok(smoothed_trajectory)
    }
    
    fn calculate_smoothness(&self, waypoints: &[Waypoint]) -> f64 {
        if waypoints.len() < 3 {
            return 1.0;
        }
        
        let mut total_curvature_change = 0.0;
        for i in 1..waypoints.len() - 1 {
            let curvature_change = (waypoints[i + 1].curvature - waypoints[i - 1].curvature).abs();
            total_curvature_change += curvature_change;
        }
        
        let avg_curvature_change = total_curvature_change / (waypoints.len() - 2) as f64;
        (1.0 / (1.0 + avg_curvature_change)).max(0.0).min(1.0)
    }
}

impl CollisionChecker {
    fn new(vehicle_dims: &VehicleDimensions, safety_margins: &SafetyMargins) -> Self {
        Self {
            vehicle_dims: vehicle_dims.clone(),
            safety_margins: safety_margins.clone(),
        }
    }
    
    fn check_path_collision(&self, _start: &Pose2D, _end: &Pose2D, grid: &OccupancyGrid) -> bool {
        // Simplified collision checking
        // In practice, would check vehicle footprint along entire path
        let mid_x = (_start.x + _end.x) / 2.0;
        let mid_y = (_start.y + _end.y) / 2.0;
        
        grid.is_occupied(Point2::new(mid_x, mid_y), 0.5)
    }
}

impl Default for PlannerConfig {
    fn default() -> Self {
        Self {
            vehicle_dimensions: VehicleDimensions {
                length: 4.5,
                width: 1.8,
                wheelbase: 2.7,
                front_overhang: 0.9,
                rear_overhang: 0.9,
                turning_radius: 5.5,
            },
            kinematic_constraints: KinematicConstraints {
                max_speed: 30.0,        // 30 m/s (108 km/h)
                max_acceleration: 3.0,   // 3 m/s²
                max_deceleration: 8.0,   // 8 m/s²
                max_steering_angle: 0.6, // ~35 degrees
                max_steering_rate: 1.0,  // 1 rad/s
                max_lateral_acceleration: 4.0, // 4 m/s²
            },
            planning_horizon: 10.0,      // 10 seconds
            planning_resolution: 0.5,    // 0.5 meters
            angular_resolution: 0.1,     // ~6 degrees
            max_planning_time_ms: 100,   // 100ms
            safety_margins: SafetyMargins {
                static_obstacle_margin: 0.5,   // 0.5m
                dynamic_obstacle_margin: 2.0,  // 2.0m
                lane_boundary_margin: 0.3,     // 0.3m
                following_distance: 20.0,      // 20m
                time_to_collision_threshold: 3.0, // 3s
            },
            cost_weights: CostWeights {
                distance_weight: 1.0,
                smoothness_weight: 2.0,
                speed_weight: 1.5,
                lane_keeping_weight: 3.0,
                obstacle_avoidance_weight: 5.0,
                traffic_rule_weight: 10.0,
            },
            smoothing_params: SmoothingParams {
                enable_smoothing: true,
                smoothing_iterations: 5,
                smoothing_factor: 0.3,
                curvature_limit: 0.1,  // 1/10m = 10m radius minimum
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_planner_creation() {
        let config = PlannerConfig::default();
        let planner = PathPlanner::new(&config);
        assert!(planner.is_ok());
    }
    
    #[test]
    fn test_motion_primitive_generation() {
        let config = PlannerConfig::default();
        let primitives = PathPlanner::generate_motion_primitives(&config);
        assert!(primitives.is_ok());
        
        let primitives = primitives.unwrap();
        assert!(!primitives.is_empty());
        
        // Check that primitives respect constraints
        for primitive in &primitives {
            assert!(primitive.final_steering_angle.abs() <= config.kinematic_constraints.max_steering_angle);
        }
    }
    
    #[test]
    fn test_heuristic_cost() {
        let config = PlannerConfig::default();
        let planner = PathPlanner::new(&config).unwrap();
        
        let start = Pose2D { x: 0.0, y: 0.0, theta: 0.0 };
        let goal = Pose2D { x: 10.0, y: 0.0, theta: 0.0 };
        
        let cost = planner.heuristic_cost(&start, &goal);
        assert!((cost - 10.0).abs() < 0.1); // Should be approximately 10m
    }
    
    #[test]
    fn test_occupancy_grid() {
        let mut grid = OccupancyGrid::new(100, 100, 0.1);
        
        grid.add_obstacle(Point2::new(5.0, 5.0), 1.0, 1.0);
        
        assert!(grid.is_occupied(Point2::new(5.0, 5.0), 0.5));
        assert!(!grid.is_occupied(Point2::new(10.0, 10.0), 0.5));
    }
}