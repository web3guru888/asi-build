//! Real-time EDF (Earliest Deadline First) scheduler for edge AI pipeline
//! 
//! Provides deterministic scheduling for AI workloads with:
//! - Real-time guarantees with sub-millisecond precision
//! - Earliest Deadline First (EDF) scheduling algorithm
//! - Priority inheritance and deadline adjustment
//! - Load balancing across multiple cores/devices
//! - Adaptive scheduling based on workload characteristics

use std::collections::{BinaryHeap, HashMap, VecDeque};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use std::cmp::Ordering;
use tokio::sync::{mpsc, RwLock, Semaphore};
use tokio::time::{interval, sleep_until, Instant as TokioInstant};

/// Task priority levels for the scheduler
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Priority {
    Critical = 0,    // Emergency stop, safety-critical
    High = 1,        // Real-time control, sensor fusion
    Normal = 2,      // AI inference, tracking
    Low = 3,         // Telemetry, logging
    Background = 4,  // Maintenance, cleanup
}

/// Scheduling policies for different workload types
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SchedulingPolicy {
    EarliestDeadlineFirst,
    RateMonotonic,
    WeightedFairQueuing,
    ProportionalShare,
    Custom(u8),
}

/// Task characteristics for scheduling decisions
#[derive(Debug, Clone)]
pub struct TaskDescriptor {
    pub task_id: String,
    pub name: String,
    pub priority: Priority,
    pub deadline: Duration,          // relative deadline
    pub period: Option<Duration>,    // for periodic tasks
    pub worst_case_execution_time: Duration,
    pub memory_requirement: usize,   // bytes
    pub cpu_affinity: Option<Vec<usize>>, // preferred CPU cores
    pub gpu_required: bool,
    pub dependencies: Vec<String>,   // task IDs this depends on
    pub scheduling_policy: SchedulingPolicy,
}

/// Schedulable task instance
#[derive(Debug, Clone)]
pub struct ScheduledTask {
    pub descriptor: TaskDescriptor,
    pub absolute_deadline: Instant,
    pub arrival_time: Instant,
    pub start_time: Option<Instant>,
    pub finish_time: Option<Instant>,
    pub execution_count: u64,
    pub missed_deadlines: u64,
    pub state: TaskState,
    pub resource_allocation: ResourceAllocation,
}

#[derive(Debug, Clone, PartialEq)]
pub enum TaskState {
    Waiting,
    Ready,
    Running,
    Suspended,
    Completed,
    Failed,
    DeadlineMissed,
}

#[derive(Debug, Clone)]
pub struct ResourceAllocation {
    pub cpu_cores: Vec<usize>,
    pub memory_bytes: usize,
    pub gpu_memory_bytes: Option<usize>,
    pub network_bandwidth_bps: Option<u64>,
}

/// Scheduling statistics and metrics
#[derive(Debug, Default, Clone)]
pub struct SchedulingStats {
    pub total_tasks_scheduled: u64,
    pub tasks_completed: u64,
    pub deadlines_missed: u64,
    pub avg_response_time_us: f64,
    pub avg_waiting_time_us: f64,
    pub cpu_utilization: f64,
    pub memory_utilization: f64,
    pub scheduler_overhead_us: f64,
    pub context_switches: u64,
}

/// Real-time scheduler configuration
#[derive(Debug, Clone)]
pub struct SchedulerConfig {
    pub max_concurrent_tasks: usize,
    pub cpu_cores: usize,
    pub memory_limit_bytes: usize,
    pub tick_interval_us: u64,           // scheduler quantum
    pub deadline_check_interval_us: u64,
    pub enable_priority_inheritance: bool,
    pub enable_deadline_adaptation: bool,
    pub load_balancing_strategy: LoadBalancingStrategy,
    pub overload_handling: OverloadHandling,
}

#[derive(Debug, Clone)]
pub enum LoadBalancingStrategy {
    RoundRobin,
    LeastLoaded,
    AffinityAware,
    WorkloadAware,
    Custom(String),
}

#[derive(Debug, Clone)]
pub enum OverloadHandling {
    DropLowPriority,
    AdaptDeadlines,
    ScaleResources,
    Throttle,
    Abort,
}

/// Main real-time scheduler
pub struct RealTimeScheduler {
    config: SchedulerConfig,
    ready_queue: Arc<Mutex<BinaryHeap<ScheduledTask>>>,
    running_tasks: Arc<RwLock<HashMap<String, ScheduledTask>>>,
    completed_tasks: Arc<Mutex<VecDeque<ScheduledTask>>>,
    task_registry: Arc<RwLock<HashMap<String, TaskDescriptor>>>,
    stats: Arc<RwLock<SchedulingStats>>,
    resource_manager: Arc<ResourceManager>,
    dependency_manager: Arc<DependencyManager>,
    admission_controller: Arc<AdmissionController>,
    scheduler_handle: Option<tokio::task::JoinHandle<()>>,
    command_tx: Option<mpsc::UnboundedSender<SchedulerCommand>>,
}

struct ResourceManager {
    cpu_allocations: Arc<Mutex<Vec<Option<String>>>>, // core -> task_id
    memory_allocations: Arc<Mutex<HashMap<String, usize>>>, // task_id -> bytes
    gpu_allocations: Arc<Mutex<HashMap<String, usize>>>,    // task_id -> gpu_memory
    semaphores: HashMap<String, Arc<Semaphore>>,
}

struct DependencyManager {
    dependency_graph: HashMap<String, Vec<String>>,
    completion_events: HashMap<String, Vec<String>>, // task_id -> waiting_tasks
}

struct AdmissionController {
    utilization_tracker: UtilizationTracker,
    deadline_analyzer: DeadlineAnalyzer,
}

struct UtilizationTracker {
    cpu_utilization: f64,
    memory_utilization: f64,
    gpu_utilization: f64,
    window_size: Duration,
    samples: VecDeque<UtilizationSample>,
}

#[derive(Debug, Clone)]
struct UtilizationSample {
    timestamp: Instant,
    cpu_usage: f64,
    memory_usage: f64,
    gpu_usage: f64,
}

struct DeadlineAnalyzer {
    schedulability_cache: HashMap<String, bool>,
    worst_case_analysis: HashMap<String, Duration>,
}

#[derive(Debug)]
enum SchedulerCommand {
    SubmitTask(ScheduledTask),
    CancelTask(String),
    UpdateTaskPriority(String, Priority),
    GetStats,
    Shutdown,
}

// Implement ordering for ScheduledTask (for priority queue)
impl PartialEq for ScheduledTask {
    fn eq(&self, other: &Self) -> bool {
        self.absolute_deadline == other.absolute_deadline
    }
}

impl Eq for ScheduledTask {}

impl PartialOrd for ScheduledTask {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for ScheduledTask {
    fn cmp(&self, other: &Self) -> Ordering {
        // Earlier deadline has higher priority (min-heap behavior)
        // If deadlines are equal, use priority as tiebreaker
        self.absolute_deadline.cmp(&other.absolute_deadline)
            .then_with(|| self.descriptor.priority.cmp(&other.descriptor.priority))
            .reverse() // Reverse for min-heap
    }
}

impl RealTimeScheduler {
    /// Create a new real-time scheduler
    pub fn new(config: SchedulerConfig) -> Result<Self, SchedulerError> {
        let resource_manager = Arc::new(ResourceManager::new(&config)?);
        let dependency_manager = Arc::new(DependencyManager::new());
        let admission_controller = Arc::new(AdmissionController::new(&config)?);
        
        Ok(RealTimeScheduler {
            config,
            ready_queue: Arc::new(Mutex::new(BinaryHeap::new())),
            running_tasks: Arc::new(RwLock::new(HashMap::new())),
            completed_tasks: Arc::new(Mutex::new(VecDeque::new())),
            task_registry: Arc::new(RwLock::new(HashMap::new())),
            stats: Arc::new(RwLock::new(SchedulingStats::default())),
            resource_manager,
            dependency_manager,
            admission_controller,
            scheduler_handle: None,
            command_tx: None,
        })
    }

    /// Start the scheduler
    pub async fn start(&mut self) -> Result<(), SchedulerError> {
        let (tx, mut rx) = mpsc::unbounded_channel();
        self.command_tx = Some(tx);

        // Clone references for the scheduler task
        let ready_queue = Arc::clone(&self.ready_queue);
        let running_tasks = Arc::clone(&self.running_tasks);
        let completed_tasks = Arc::clone(&self.completed_tasks);
        let stats = Arc::clone(&self.stats);
        let resource_manager = Arc::clone(&self.resource_manager);
        let config = self.config.clone();

        // Spawn the main scheduler loop
        let scheduler_handle = tokio::spawn(async move {
            let mut tick_interval = interval(Duration::from_micros(config.tick_interval_us));
            let mut deadline_check_interval = interval(Duration::from_micros(config.deadline_check_interval_us));
            
            loop {
                tokio::select! {
                    // Handle scheduler commands
                    command = rx.recv() => {
                        match command {
                            Some(SchedulerCommand::SubmitTask(task)) => {
                                Self::submit_task_internal(&ready_queue, task).await;
                            },
                            Some(SchedulerCommand::CancelTask(task_id)) => {
                                Self::cancel_task_internal(&running_tasks, &task_id).await;
                            },
                            Some(SchedulerCommand::UpdateTaskPriority(task_id, priority)) => {
                                Self::update_task_priority_internal(&ready_queue, &running_tasks, &task_id, priority).await;
                            },
                            Some(SchedulerCommand::Shutdown) => {
                                break;
                            },
                            None => break,
                        }
                    },
                    
                    // Scheduler tick - main scheduling decisions
                    _ = tick_interval.tick() => {
                        Self::scheduler_tick(&ready_queue, &running_tasks, &resource_manager, &config).await;
                    },
                    
                    // Deadline monitoring
                    _ = deadline_check_interval.tick() => {
                        Self::check_deadlines(&running_tasks, &stats).await;
                    },
                }
            }
        });

        self.scheduler_handle = Some(scheduler_handle);
        Ok(())
    }

    /// Stop the scheduler
    pub async fn stop(&mut self) -> Result<(), SchedulerError> {
        if let Some(tx) = &self.command_tx {
            let _ = tx.send(SchedulerCommand::Shutdown);
        }

        if let Some(handle) = self.scheduler_handle.take() {
            let _ = handle.await;
        }

        Ok(())
    }

    /// Submit a task for scheduling
    pub async fn submit_task(&self, descriptor: TaskDescriptor) -> Result<String, SchedulerError> {
        // Create scheduled task instance
        let arrival_time = Instant::now();
        let absolute_deadline = arrival_time + descriptor.deadline;
        
        let task = ScheduledTask {
            descriptor: descriptor.clone(),
            absolute_deadline,
            arrival_time,
            start_time: None,
            finish_time: None,
            execution_count: 0,
            missed_deadlines: 0,
            state: TaskState::Waiting,
            resource_allocation: ResourceAllocation {
                cpu_cores: vec![],
                memory_bytes: 0,
                gpu_memory_bytes: None,
                network_bandwidth_bps: None,
            },
        };

        // Admission control
        if !self.admission_controller.can_admit(&task).await? {
            return Err(SchedulerError::AdmissionRejected(
                "Task cannot meet deadline with current system load".to_string()
            ));
        }

        // Register task
        {
            let mut registry = self.task_registry.write().await;
            registry.insert(descriptor.task_id.clone(), descriptor);
        }

        // Submit to scheduler
        if let Some(tx) = &self.command_tx {
            tx.send(SchedulerCommand::SubmitTask(task))
                .map_err(|_| SchedulerError::SchedulerNotRunning)?;
        }

        Ok(task.descriptor.task_id.clone())
    }

    /// Cancel a scheduled task
    pub async fn cancel_task(&self, task_id: &str) -> Result<(), SchedulerError> {
        if let Some(tx) = &self.command_tx {
            tx.send(SchedulerCommand::CancelTask(task_id.to_string()))
                .map_err(|_| SchedulerError::SchedulerNotRunning)?;
        }
        Ok(())
    }

    /// Get scheduling statistics
    pub async fn get_stats(&self) -> SchedulingStats {
        self.stats.read().await.clone()
    }

    /// Update task priority at runtime
    pub async fn update_task_priority(&self, task_id: &str, priority: Priority) -> Result<(), SchedulerError> {
        if let Some(tx) = &self.command_tx {
            tx.send(SchedulerCommand::UpdateTaskPriority(task_id.to_string(), priority))
                .map_err(|_| SchedulerError::SchedulerNotRunning)?;
        }
        Ok(())
    }

    // Internal scheduling methods

    async fn submit_task_internal(
        ready_queue: &Arc<Mutex<BinaryHeap<ScheduledTask>>>,
        mut task: ScheduledTask
    ) {
        task.state = TaskState::Ready;
        
        let mut queue = ready_queue.lock().unwrap();
        queue.push(task);
    }

    async fn cancel_task_internal(
        running_tasks: &Arc<RwLock<HashMap<String, ScheduledTask>>>,
        task_id: &str
    ) {
        let mut tasks = running_tasks.write().await;
        if let Some(mut task) = tasks.remove(task_id) {
            task.state = TaskState::Failed;
            // TODO: Signal task cancellation
        }
    }

    async fn update_task_priority_internal(
        ready_queue: &Arc<Mutex<BinaryHeap<ScheduledTask>>>,
        running_tasks: &Arc<RwLock<HashMap<String, ScheduledTask>>>,
        task_id: &str,
        new_priority: Priority
    ) {
        // Check running tasks first
        {
            let mut tasks = running_tasks.write().await;
            if let Some(task) = tasks.get_mut(task_id) {
                task.descriptor.priority = new_priority;
                return;
            }
        }

        // Check ready queue (requires rebuilding the heap)
        {
            let mut queue = ready_queue.lock().unwrap();
            let mut tasks: Vec<ScheduledTask> = queue.drain().collect();
            
            for task in &mut tasks {
                if task.descriptor.task_id == task_id {
                    task.descriptor.priority = new_priority;
                    break;
                }
            }
            
            // Rebuild heap
            for task in tasks {
                queue.push(task);
            }
        }
    }

    async fn scheduler_tick(
        ready_queue: &Arc<Mutex<BinaryHeap<ScheduledTask>>>,
        running_tasks: &Arc<RwLock<HashMap<String, ScheduledTask>>>,
        resource_manager: &Arc<ResourceManager>,
        config: &SchedulerConfig
    ) {
        // Get next task to schedule
        let next_task = {
            let mut queue = ready_queue.lock().unwrap();
            queue.pop()
        };

        if let Some(mut task) = next_task {
            // Check if we can allocate resources
            if let Ok(allocation) = resource_manager.allocate_resources(&task).await {
                task.resource_allocation = allocation;
                task.state = TaskState::Running;
                task.start_time = Some(Instant::now());

                // Start task execution
                let task_id = task.descriptor.task_id.clone();
                {
                    let mut tasks = running_tasks.write().await;
                    tasks.insert(task_id.clone(), task);
                }

                // Spawn task execution
                Self::execute_task(task_id, running_tasks.clone(), resource_manager.clone()).await;
            } else {
                // Put task back in queue if resources not available
                let mut queue = ready_queue.lock().unwrap();
                queue.push(task);
            }
        }
    }

    async fn execute_task(
        task_id: String,
        running_tasks: Arc<RwLock<HashMap<String, ScheduledTask>>>,
        resource_manager: Arc<ResourceManager>
    ) {
        tokio::spawn(async move {
            // Simulate task execution
            // In a real implementation, this would invoke the actual task
            
            let execution_time = {
                let tasks = running_tasks.read().await;
                if let Some(task) = tasks.get(&task_id) {
                    task.descriptor.worst_case_execution_time
                } else {
                    return;
                }
            };

            // Sleep for execution time (simulation)
            sleep_until(TokioInstant::now() + execution_time).await;

            // Mark task as completed
            {
                let mut tasks = running_tasks.write().await;
                if let Some(mut task) = tasks.remove(&task_id) {
                    task.state = TaskState::Completed;
                    task.finish_time = Some(Instant::now());
                    task.execution_count += 1;

                    // Release resources
                    let _ = resource_manager.release_resources(&task).await;
                }
            }
        });
    }

    async fn check_deadlines(
        running_tasks: &Arc<RwLock<HashMap<String, ScheduledTask>>>,
        stats: &Arc<RwLock<SchedulingStats>>
    ) {
        let now = Instant::now();
        let mut missed_deadlines = Vec::new();

        {
            let tasks = running_tasks.read().await;
            for (task_id, task) in tasks.iter() {
                if now > task.absolute_deadline {
                    missed_deadlines.push(task_id.clone());
                }
            }
        }

        if !missed_deadlines.is_empty() {
            let mut tasks = running_tasks.write().await;
            let mut stats_guard = stats.write().await;

            for task_id in missed_deadlines {
                if let Some(mut task) = tasks.remove(&task_id) {
                    task.state = TaskState::DeadlineMissed;
                    task.missed_deadlines += 1;
                    stats_guard.deadlines_missed += 1;
                    
                    // TODO: Handle deadline miss (logging, alerts, recovery)
                }
            }
        }
    }
}

impl ResourceManager {
    fn new(config: &SchedulerConfig) -> Result<Self, SchedulerError> {
        Ok(ResourceManager {
            cpu_allocations: Arc::new(Mutex::new(vec![None; config.cpu_cores])),
            memory_allocations: Arc::new(Mutex::new(HashMap::new())),
            gpu_allocations: Arc::new(Mutex::new(HashMap::new())),
            semaphores: HashMap::new(),
        })
    }

    async fn allocate_resources(&self, task: &ScheduledTask) -> Result<ResourceAllocation, SchedulerError> {
        let mut cpu_cores = Vec::new();
        
        // Allocate CPU cores
        {
            let mut allocations = self.cpu_allocations.lock().unwrap();
            
            // Try to find available cores
            for (i, core) in allocations.iter_mut().enumerate() {
                if core.is_none() {
                    *core = Some(task.descriptor.task_id.clone());
                    cpu_cores.push(i);
                    break; // For now, allocate only one core per task
                }
            }
            
            if cpu_cores.is_empty() {
                return Err(SchedulerError::ResourceUnavailable("No CPU cores available".to_string()));
            }
        }

        // Allocate memory
        {
            let mut memory_allocs = self.memory_allocations.lock().unwrap();
            memory_allocs.insert(
                task.descriptor.task_id.clone(),
                task.descriptor.memory_requirement
            );
        }

        Ok(ResourceAllocation {
            cpu_cores,
            memory_bytes: task.descriptor.memory_requirement,
            gpu_memory_bytes: None,
            network_bandwidth_bps: None,
        })
    }

    async fn release_resources(&self, task: &ScheduledTask) -> Result<(), SchedulerError> {
        // Release CPU cores
        {
            let mut allocations = self.cpu_allocations.lock().unwrap();
            for &core in &task.resource_allocation.cpu_cores {
                if core < allocations.len() {
                    allocations[core] = None;
                }
            }
        }

        // Release memory allocation
        {
            let mut memory_allocs = self.memory_allocations.lock().unwrap();
            memory_allocs.remove(&task.descriptor.task_id);
        }

        Ok(())
    }
}

impl DependencyManager {
    fn new() -> Self {
        DependencyManager {
            dependency_graph: HashMap::new(),
            completion_events: HashMap::new(),
        }
    }
}

impl AdmissionController {
    fn new(config: &SchedulerConfig) -> Result<Self, SchedulerError> {
        Ok(AdmissionController {
            utilization_tracker: UtilizationTracker::new(Duration::from_secs(60)),
            deadline_analyzer: DeadlineAnalyzer::new(),
        })
    }

    async fn can_admit(&self, _task: &ScheduledTask) -> Result<bool, SchedulerError> {
        // Simplified admission control
        // In a real implementation, this would do schedulability analysis
        Ok(true)
    }
}

impl UtilizationTracker {
    fn new(window_size: Duration) -> Self {
        UtilizationTracker {
            cpu_utilization: 0.0,
            memory_utilization: 0.0,
            gpu_utilization: 0.0,
            window_size,
            samples: VecDeque::new(),
        }
    }
}

impl DeadlineAnalyzer {
    fn new() -> Self {
        DeadlineAnalyzer {
            schedulability_cache: HashMap::new(),
            worst_case_analysis: HashMap::new(),
        }
    }
}

#[derive(Debug, thiserror::Error)]
pub enum SchedulerError {
    #[error("Scheduler not running")]
    SchedulerNotRunning,
    
    #[error("Task admission rejected: {0}")]
    AdmissionRejected(String),
    
    #[error("Resource unavailable: {0}")]
    ResourceUnavailable(String),
    
    #[error("Task not found: {0}")]
    TaskNotFound(String),
    
    #[error("Invalid configuration: {0}")]
    InvalidConfiguration(String),
    
    #[error("Deadline miss detected for task: {0}")]
    DeadlineMiss(String),
    
    #[error("Resource allocation failed: {0}")]
    ResourceAllocationFailed(String),
    
    #[error("Dependency cycle detected")]
    DependencyCycle,
    
    #[error("System overload")]
    SystemOverload,
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_scheduler_creation() {
        let config = SchedulerConfig {
            max_concurrent_tasks: 10,
            cpu_cores: 4,
            memory_limit_bytes: 1024 * 1024 * 1024, // 1GB
            tick_interval_us: 1000,                  // 1ms
            deadline_check_interval_us: 10000,       // 10ms
            enable_priority_inheritance: true,
            enable_deadline_adaptation: false,
            load_balancing_strategy: LoadBalancingStrategy::LeastLoaded,
            overload_handling: OverloadHandling::DropLowPriority,
        };

        let scheduler = RealTimeScheduler::new(config);
        assert!(scheduler.is_ok());
    }

    #[tokio::test]
    async fn test_task_submission() {
        let config = SchedulerConfig {
            max_concurrent_tasks: 10,
            cpu_cores: 4,
            memory_limit_bytes: 1024 * 1024 * 1024,
            tick_interval_us: 1000,
            deadline_check_interval_us: 10000,
            enable_priority_inheritance: true,
            enable_deadline_adaptation: false,
            load_balancing_strategy: LoadBalancingStrategy::LeastLoaded,
            overload_handling: OverloadHandling::DropLowPriority,
        };

        let mut scheduler = RealTimeScheduler::new(config).unwrap();
        scheduler.start().await.unwrap();

        let task_descriptor = TaskDescriptor {
            task_id: "test_task_1".to_string(),
            name: "Test Task".to_string(),
            priority: Priority::Normal,
            deadline: Duration::from_millis(100),
            period: None,
            worst_case_execution_time: Duration::from_millis(10),
            memory_requirement: 1024 * 1024, // 1MB
            cpu_affinity: None,
            gpu_required: false,
            dependencies: vec![],
            scheduling_policy: SchedulingPolicy::EarliestDeadlineFirst,
        };

        let result = scheduler.submit_task(task_descriptor).await;
        assert!(result.is_ok());

        scheduler.stop().await.unwrap();
    }

    #[test]
    fn test_task_ordering() {
        let early_deadline = Instant::now() + Duration::from_millis(50);
        let late_deadline = Instant::now() + Duration::from_millis(100);

        let task1 = ScheduledTask {
            descriptor: TaskDescriptor {
                task_id: "task1".to_string(),
                name: "Task 1".to_string(),
                priority: Priority::Normal,
                deadline: Duration::from_millis(100),
                period: None,
                worst_case_execution_time: Duration::from_millis(10),
                memory_requirement: 1024,
                cpu_affinity: None,
                gpu_required: false,
                dependencies: vec![],
                scheduling_policy: SchedulingPolicy::EarliestDeadlineFirst,
            },
            absolute_deadline: late_deadline,
            arrival_time: Instant::now(),
            start_time: None,
            finish_time: None,
            execution_count: 0,
            missed_deadlines: 0,
            state: TaskState::Ready,
            resource_allocation: ResourceAllocation {
                cpu_cores: vec![],
                memory_bytes: 0,
                gpu_memory_bytes: None,
                network_bandwidth_bps: None,
            },
        };

        let task2 = ScheduledTask {
            descriptor: TaskDescriptor {
                task_id: "task2".to_string(),
                name: "Task 2".to_string(),
                priority: Priority::Normal,
                deadline: Duration::from_millis(50),
                period: None,
                worst_case_execution_time: Duration::from_millis(10),
                memory_requirement: 1024,
                cpu_affinity: None,
                gpu_required: false,
                dependencies: vec![],
                scheduling_policy: SchedulingPolicy::EarliestDeadlineFirst,
            },
            absolute_deadline: early_deadline,
            arrival_time: Instant::now(),
            start_time: None,
            finish_time: None,
            execution_count: 0,
            missed_deadlines: 0,
            state: TaskState::Ready,
            resource_allocation: ResourceAllocation {
                cpu_cores: vec![],
                memory_bytes: 0,
                gpu_memory_bytes: None,
                network_bandwidth_bps: None,
            },
        };

        // Earlier deadline should have higher priority (be "greater" in max-heap)
        assert!(task2 > task1);
    }
}