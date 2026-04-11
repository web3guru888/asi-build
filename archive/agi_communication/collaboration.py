"""
Collaborative Problem-Solving Framework
=======================================

Advanced framework for enabling multiple AGIs to collaborate
on complex problem-solving tasks with distributed cognition.
"""

import asyncio
import json
import numpy as np
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
import uuid
import heapq
from collections import defaultdict

from .core import CommunicationMessage, MessageType, AGIIdentity

logger = logging.getLogger(__name__)

class ProblemType(Enum):
    """Types of problems for collaborative solving."""
    OPTIMIZATION = "optimization"
    SEARCH = "search"
    PLANNING = "planning"
    REASONING = "reasoning"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    PREDICTIVE = "predictive"
    CLASSIFICATION = "classification"
    DESIGN = "design"
    SIMULATION = "simulation"

class CollaborationStrategy(Enum):
    """Strategies for collaboration."""
    DIVIDE_AND_CONQUER = "divide_and_conquer"
    PARALLEL_PROCESSING = "parallel_processing"
    HIERARCHICAL = "hierarchical"
    PEER_TO_PEER = "peer_to_peer"
    ENSEMBLE = "ensemble"
    CONSENSUS = "consensus"
    COMPETITION = "competition"
    HYBRID = "hybrid"

class TaskStatus(Enum):
    """Status of collaborative tasks."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Problem:
    """Represents a problem to be solved collaboratively."""
    id: str
    description: str
    problem_type: ProblemType
    complexity: float  # 0-1 scale
    constraints: Dict[str, Any] = field(default_factory=dict)
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    deadline: Optional[datetime] = None
    resources_required: Dict[str, float] = field(default_factory=dict)
    input_data: Any = None
    expected_output: Any = None
    priority: float = 1.0
    
    def estimate_complexity(self) -> float:
        """Estimate problem complexity based on characteristics."""
        # This is a simplified complexity estimation
        base_complexity = self.complexity
        
        # Adjust based on constraints
        constraint_factor = len(self.constraints) * 0.1
        
        # Adjust based on data size
        if isinstance(self.input_data, (list, dict)):
            try:
                data_size_factor = min(0.3, len(str(self.input_data)) / 10000)
            except:
                data_size_factor = 0.1
        else:
            data_size_factor = 0.05
        
        return min(1.0, base_complexity + constraint_factor + data_size_factor)

@dataclass
class Task:
    """A task within a collaborative problem-solving session."""
    id: str
    problem_id: str
    description: str
    assigned_agi: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # Other task IDs
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration: Optional[timedelta] = None
    actual_duration: Optional[timedelta] = None
    
    def mark_started(self):
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()
    
    def mark_completed(self, result: Any):
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result
        self.progress = 1.0
        
        if self.started_at:
            self.actual_duration = self.completed_at - self.started_at
    
    def mark_failed(self, error: str):
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()
        
        if self.started_at:
            self.actual_duration = self.completed_at - self.started_at

@dataclass
class Solution:
    """A solution to a problem."""
    id: str
    problem_id: str
    solution_data: Any
    confidence: float
    quality_score: float = 0.0
    contributors: List[str] = field(default_factory=list)  # AGI IDs
    methodology: str = ""
    computational_cost: float = 0.0
    validation_results: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class CollaborationSession:
    """A collaborative problem-solving session."""
    id: str
    problem: Problem
    participants: List[str]  # AGI IDs
    strategy: CollaborationStrategy
    tasks: Dict[str, Task] = field(default_factory=dict)
    solutions: List[Solution] = field(default_factory=list)
    coordinator_agi: str = ""
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    shared_memory: Dict[str, Any] = field(default_factory=dict)
    communication_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_task(self, task: Task):
        """Add task to session."""
        self.tasks[task.id] = task
    
    def get_available_tasks(self) -> List[Task]:
        """Get tasks that are ready to be executed."""
        available = []
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                # Check if all dependencies are completed
                dependencies_met = all(
                    dep_id in self.tasks and 
                    self.tasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )
                if dependencies_met:
                    available.append(task)
        return available
    
    def get_completion_rate(self) -> float:
        """Get overall completion rate of the session."""
        if not self.tasks:
            return 0.0
        
        completed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)
        return completed_tasks / len(self.tasks)
    
    def is_completed(self) -> bool:
        """Check if the collaboration session is completed."""
        return all(task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                  for task in self.tasks.values())

class ProblemDecomposer:
    """Decomposes complex problems into manageable tasks."""
    
    @staticmethod
    def decompose_optimization_problem(problem: Problem) -> List[Task]:
        """Decompose an optimization problem."""
        tasks = []
        
        # Task 1: Problem analysis
        analysis_task = Task(
            id=f"{problem.id}_analysis",
            problem_id=problem.id,
            description="Analyze optimization problem structure and constraints"
        )
        tasks.append(analysis_task)
        
        # Task 2: Solution space exploration
        exploration_task = Task(
            id=f"{problem.id}_exploration",
            problem_id=problem.id,
            description="Explore solution space and identify promising regions",
            dependencies=[analysis_task.id]
        )
        tasks.append(exploration_task)
        
        # Task 3: Algorithm selection/tuning
        algorithm_task = Task(
            id=f"{problem.id}_algorithm",
            problem_id=problem.id,
            description="Select and tune optimization algorithms",
            dependencies=[analysis_task.id]
        )
        tasks.append(algorithm_task)
        
        # Task 4: Optimization execution
        execution_task = Task(
            id=f"{problem.id}_execution",
            problem_id=problem.id,
            description="Execute optimization algorithms",
            dependencies=[exploration_task.id, algorithm_task.id]
        )
        tasks.append(execution_task)
        
        # Task 5: Results validation
        validation_task = Task(
            id=f"{problem.id}_validation",
            problem_id=problem.id,
            description="Validate and compare optimization results",
            dependencies=[execution_task.id]
        )
        tasks.append(validation_task)
        
        return tasks
    
    @staticmethod
    def decompose_search_problem(problem: Problem) -> List[Task]:
        """Decompose a search problem."""
        tasks = []
        
        # Task 1: Search space analysis
        space_analysis = Task(
            id=f"{problem.id}_space_analysis",
            problem_id=problem.id,
            description="Analyze search space characteristics"
        )
        tasks.append(space_analysis)
        
        # Task 2: Heuristic design
        heuristic_design = Task(
            id=f"{problem.id}_heuristics",
            problem_id=problem.id,
            description="Design search heuristics and strategies",
            dependencies=[space_analysis.id]
        )
        tasks.append(heuristic_design)
        
        # Task 3: Parallel search
        search_task = Task(
            id=f"{problem.id}_search",
            problem_id=problem.id,
            description="Execute parallel search algorithms",
            dependencies=[heuristic_design.id]
        )
        tasks.append(search_task)
        
        # Task 4: Result aggregation
        aggregation_task = Task(
            id=f"{problem.id}_aggregation",
            problem_id=problem.id,
            description="Aggregate and rank search results",
            dependencies=[search_task.id]
        )
        tasks.append(aggregation_task)
        
        return tasks
    
    @staticmethod
    def decompose_reasoning_problem(problem: Problem) -> List[Task]:
        """Decompose a reasoning problem."""
        tasks = []
        
        # Task 1: Knowledge extraction
        knowledge_task = Task(
            id=f"{problem.id}_knowledge",
            problem_id=problem.id,
            description="Extract relevant knowledge and facts"
        )
        tasks.append(knowledge_task)
        
        # Task 2: Inference rule generation
        rules_task = Task(
            id=f"{problem.id}_rules",
            problem_id=problem.id,
            description="Generate inference rules and logical connections",
            dependencies=[knowledge_task.id]
        )
        tasks.append(rules_task)
        
        # Task 3: Logical reasoning
        reasoning_task = Task(
            id=f"{problem.id}_reasoning",
            problem_id=problem.id,
            description="Apply logical reasoning and inference",
            dependencies=[rules_task.id]
        )
        tasks.append(reasoning_task)
        
        # Task 4: Conclusion validation
        validation_task = Task(
            id=f"{problem.id}_validation",
            problem_id=problem.id,
            description="Validate reasoning conclusions",
            dependencies=[reasoning_task.id]
        )
        tasks.append(validation_task)
        
        return tasks
    
    @staticmethod
    def decompose_creative_problem(problem: Problem) -> List[Task]:
        """Decompose a creative problem."""
        tasks = []
        
        # Task 1: Inspiration gathering
        inspiration_task = Task(
            id=f"{problem.id}_inspiration",
            problem_id=problem.id,
            description="Gather inspiration and reference materials"
        )
        tasks.append(inspiration_task)
        
        # Task 2: Ideation
        ideation_task = Task(
            id=f"{problem.id}_ideation",
            problem_id=problem.id,
            description="Generate creative ideas and concepts",
            dependencies=[inspiration_task.id]
        )
        tasks.append(ideation_task)
        
        # Task 3: Concept refinement
        refinement_task = Task(
            id=f"{problem.id}_refinement",
            problem_id=problem.id,
            description="Refine and develop promising concepts",
            dependencies=[ideation_task.id]
        )
        tasks.append(refinement_task)
        
        # Task 4: Creative synthesis
        synthesis_task = Task(
            id=f"{problem.id}_synthesis",
            problem_id=problem.id,
            description="Synthesize ideas into creative solutions",
            dependencies=[refinement_task.id]
        )
        tasks.append(synthesis_task)
        
        return tasks

class TaskScheduler:
    """Schedules and assigns tasks to AGIs."""
    
    def __init__(self):
        self.agi_capabilities: Dict[str, Set[str]] = {}
        self.agi_workloads: Dict[str, float] = {}
        self.task_priorities: Dict[str, float] = {}
    
    def assign_tasks(self, session: CollaborationSession) -> Dict[str, str]:
        """Assign tasks to AGIs based on capabilities and workload."""
        assignments = {}
        available_tasks = session.get_available_tasks()
        
        # Sort tasks by priority and dependencies
        sorted_tasks = sorted(available_tasks, 
                            key=lambda t: (len(t.dependencies), -self.task_priorities.get(t.id, 0.5)))
        
        for task in sorted_tasks:
            best_agi = self._find_best_agi_for_task(task, session.participants)
            if best_agi:
                assignments[task.id] = best_agi
                task.assigned_agi = best_agi
                # Update workload
                self.agi_workloads[best_agi] = self.agi_workloads.get(best_agi, 0) + 1
        
        return assignments
    
    def _find_best_agi_for_task(self, task: Task, participants: List[str]) -> Optional[str]:
        """Find the best AGI for a specific task."""
        if not participants:
            return None
        
        # Simple scoring based on workload (lower is better)
        scores = {}
        for agi_id in participants:
            workload = self.agi_workloads.get(agi_id, 0)
            # Lower workload gets higher score
            scores[agi_id] = 1.0 / (1 + workload)
        
        # Return AGI with highest score
        return max(scores.keys(), key=lambda k: scores[k])
    
    def update_agi_capabilities(self, agi_id: str, capabilities: Set[str]):
        """Update AGI capabilities."""
        self.agi_capabilities[agi_id] = capabilities
    
    def task_completed(self, task_id: str, agi_id: str):
        """Notify scheduler that a task is completed."""
        if agi_id in self.agi_workloads:
            self.agi_workloads[agi_id] = max(0, self.agi_workloads[agi_id] - 1)

class SolutionValidator:
    """Validates and ranks solutions."""
    
    @staticmethod
    def validate_solution(solution: Solution, problem: Problem) -> Dict[str, Any]:
        """Validate a solution against problem criteria."""
        validation_results = {
            'is_valid': True,
            'quality_score': 0.0,
            'issues': [],
            'metrics': {}
        }
        
        try:
            # Check basic validity
            if solution.solution_data is None:
                validation_results['is_valid'] = False
                validation_results['issues'].append("Solution data is None")
                return validation_results
            
            # Check against success criteria
            quality_score = 0.0
            metrics = {}
            
            for criterion, expected_value in problem.success_criteria.items():
                if criterion in ['accuracy', 'precision', 'recall']:
                    # Performance metrics
                    actual_value = getattr(solution, criterion, 0.0)
                    metrics[criterion] = actual_value
                    
                    if isinstance(expected_value, (int, float)):
                        if actual_value >= expected_value:
                            quality_score += 0.3
                        else:
                            validation_results['issues'].append(f"{criterion} below threshold: {actual_value} < {expected_value}")
            
            # Check constraints
            for constraint, limit in problem.constraints.items():
                if constraint == 'max_computation_time':
                    if solution.computational_cost > limit:
                        validation_results['issues'].append(f"Computation time exceeded: {solution.computational_cost} > {limit}")
                        quality_score -= 0.1
            
            # Base quality from confidence
            quality_score += solution.confidence * 0.4
            
            validation_results['quality_score'] = max(0.0, min(1.0, quality_score))
            validation_results['metrics'] = metrics
            
        except Exception as e:
            validation_results['is_valid'] = False
            validation_results['issues'].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    @staticmethod
    def rank_solutions(solutions: List[Solution]) -> List[Tuple[Solution, float]]:
        """Rank solutions by quality."""
        ranked = []
        
        for solution in solutions:
            # Combined score based on quality, confidence, and validation
            score = (
                solution.quality_score * 0.4 +
                solution.confidence * 0.3 +
                len(solution.contributors) * 0.1 +  # More contributors = more reliable
                (1.0 - solution.computational_cost / 100.0) * 0.2  # Lower cost is better
            )
            ranked.append((solution, score))
        
        return sorted(ranked, key=lambda x: x[1], reverse=True)

class CollaborativeProblemSolver:
    """
    Collaborative Problem-Solving Framework
    
    Enables multiple AGIs to work together on complex problems
    using distributed cognition and coordination mechanisms.
    """
    
    def __init__(self, protocol):
        self.protocol = protocol
        self.active_sessions: Dict[str, CollaborationSession] = {}
        self.completed_sessions: Dict[str, CollaborationSession] = {}
        self.problem_decomposer = ProblemDecomposer()
        self.task_scheduler = TaskScheduler()
        self.solution_validator = SolutionValidator()
        self.collaboration_history: List[Dict[str, Any]] = []
    
    async def start_collaboration(self, problem: Problem, participants: List[str],
                                strategy: CollaborationStrategy = CollaborationStrategy.HYBRID) -> str:
        """Start a new collaboration session."""
        session_id = str(uuid.uuid4())
        
        # Create collaboration session
        session = CollaborationSession(
            id=session_id,
            problem=problem,
            participants=participants + [self.protocol.identity.id],
            strategy=strategy,
            coordinator_agi=self.protocol.identity.id,
            deadline=problem.deadline
        )
        
        # Decompose problem into tasks
        tasks = await self._decompose_problem(problem)
        for task in tasks:
            session.add_task(task)
        
        # Store session
        self.active_sessions[session_id] = session
        
        # Invite participants
        for participant_id in participants:
            invitation_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=participant_id,
                message_type=MessageType.COLLABORATION_INVITE,
                timestamp=datetime.now(),
                payload={
                    'action': 'invitation',
                    'session_id': session_id,
                    'problem': self._serialize_problem(problem),
                    'strategy': strategy.value,
                    'tasks': [self._serialize_task(task) for task in tasks],
                    'deadline': problem.deadline.isoformat() if problem.deadline else None
                },
                requires_response=True
            )
            
            await self.protocol.send_message(invitation_message)
        
        logger.info(f"Started collaboration session {session_id} for problem {problem.id}")
        return session_id
    
    async def _decompose_problem(self, problem: Problem) -> List[Task]:
        """Decompose problem into tasks based on problem type."""
        if problem.problem_type == ProblemType.OPTIMIZATION:
            return self.problem_decomposer.decompose_optimization_problem(problem)
        elif problem.problem_type == ProblemType.SEARCH:
            return self.problem_decomposer.decompose_search_problem(problem)
        elif problem.problem_type == ProblemType.REASONING:
            return self.problem_decomposer.decompose_reasoning_problem(problem)
        elif problem.problem_type == ProblemType.CREATIVE:
            return self.problem_decomposer.decompose_creative_problem(problem)
        else:
            # Generic decomposition
            return [Task(
                id=f"{problem.id}_main",
                problem_id=problem.id,
                description=f"Solve {problem.problem_type.value} problem: {problem.description}"
            )]
    
    async def assign_next_tasks(self, session_id: str):
        """Assign available tasks to AGIs."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        assignments = self.task_scheduler.assign_tasks(session)
        
        # Send task assignments
        for task_id, agi_id in assignments.items():
            if agi_id == self.protocol.identity.id:
                # Execute locally
                await self._execute_task_locally(session_id, task_id)
            else:
                # Send to remote AGI
                task = session.tasks[task_id]
                task_message = CommunicationMessage(
                    id=str(uuid.uuid4()),
                    sender_id=self.protocol.identity.id,
                    receiver_id=agi_id,
                    message_type=MessageType.COLLABORATION_INVITE,
                    timestamp=datetime.now(),
                    payload={
                        'action': 'task_assignment',
                        'session_id': session_id,
                        'task': self._serialize_task(task),
                        'shared_memory': session.shared_memory
                    }
                )
                
                await self.protocol.send_message(task_message)
    
    async def _execute_task_locally(self, session_id: str, task_id: str):
        """Execute a task locally."""
        session = self.active_sessions[session_id]
        task = session.tasks[task_id]
        
        try:
            task.mark_started()
            
            # Simple task execution logic
            # In practice, this would be more sophisticated
            result = await self._perform_task_computation(task, session.problem, session.shared_memory)
            
            task.mark_completed(result)
            
            # Update shared memory
            session.shared_memory[f"task_{task_id}_result"] = result
            
            # Check if more tasks are available
            await self.assign_next_tasks(session_id)
            
        except Exception as e:
            task.mark_failed(str(e))
            logger.error(f"Task {task_id} failed: {e}")
    
    async def _perform_task_computation(self, task: Task, problem: Problem, shared_memory: Dict[str, Any]) -> Any:
        """Perform the actual computation for a task."""
        # This is a simplified implementation
        # Real implementation would involve sophisticated problem-solving logic
        
        if "analysis" in task.description.lower():
            return {"analysis": "Problem structure analyzed", "complexity": problem.estimate_complexity()}
        elif "search" in task.description.lower():
            return {"search_results": [f"result_{i}" for i in range(5)], "best_result": "result_0"}
        elif "optimization" in task.description.lower():
            return {"optimal_value": 0.85, "optimal_parameters": {"x": 1.0, "y": 2.0}}
        elif "validation" in task.description.lower():
            return {"validation_passed": True, "confidence": 0.9}
        else:
            return {"task_completed": True, "output": "Generic task result"}
    
    async def submit_solution(self, session_id: str, solution: Solution):
        """Submit a solution to a collaboration session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"No active session {session_id}")
        
        session = self.active_sessions[session_id]
        
        # Validate solution
        validation_results = self.solution_validator.validate_solution(solution, session.problem)
        solution.validation_results = validation_results
        solution.quality_score = validation_results['quality_score']
        
        # Add to session
        session.solutions.append(solution)
        
        logger.info(f"Solution {solution.id} submitted to session {session_id} with quality {solution.quality_score}")
    
    async def finalize_collaboration(self, session_id: str):
        """Finalize a collaboration session."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        
        # Rank solutions
        if session.solutions:
            ranked_solutions = self.solution_validator.rank_solutions(session.solutions)
            best_solution = ranked_solutions[0][0] if ranked_solutions else None
        else:
            best_solution = None
        
        session.status = "completed"
        
        # Move to completed sessions
        self.completed_sessions[session_id] = session
        del self.active_sessions[session_id]
        
        # Notify participants
        for participant_id in session.participants:
            if participant_id == self.protocol.identity.id:
                continue
            
            completion_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=participant_id,
                message_type=MessageType.COLLABORATION_RESPONSE,
                timestamp=datetime.now(),
                payload={
                    'action': 'completion',
                    'session_id': session_id,
                    'best_solution': self._serialize_solution(best_solution) if best_solution else None,
                    'completion_rate': session.get_completion_rate(),
                    'total_solutions': len(session.solutions)
                }
            )
            
            await self.protocol.send_message(completion_message)
        
        # Record collaboration
        self._record_collaboration(session)
        
        logger.info(f"Finalized collaboration session {session_id}")
    
    def _serialize_problem(self, problem: Problem) -> Dict[str, Any]:
        """Serialize problem to dictionary."""
        return {
            'id': problem.id,
            'description': problem.description,
            'problem_type': problem.problem_type.value,
            'complexity': problem.complexity,
            'constraints': problem.constraints,
            'success_criteria': problem.success_criteria,
            'deadline': problem.deadline.isoformat() if problem.deadline else None,
            'resources_required': problem.resources_required,
            'input_data': problem.input_data,
            'expected_output': problem.expected_output,
            'priority': problem.priority
        }
    
    def _serialize_task(self, task: Task) -> Dict[str, Any]:
        """Serialize task to dictionary."""
        return {
            'id': task.id,
            'problem_id': task.problem_id,
            'description': task.description,
            'assigned_agi': task.assigned_agi,
            'dependencies': task.dependencies,
            'status': task.status.value,
            'progress': task.progress,
            'result': task.result,
            'error': task.error,
            'created_at': task.created_at.isoformat(),
            'estimated_duration': task.estimated_duration.total_seconds() if task.estimated_duration else None
        }
    
    def _serialize_solution(self, solution: Solution) -> Dict[str, Any]:
        """Serialize solution to dictionary."""
        return {
            'id': solution.id,
            'problem_id': solution.problem_id,
            'solution_data': solution.solution_data,
            'confidence': solution.confidence,
            'quality_score': solution.quality_score,
            'contributors': solution.contributors,
            'methodology': solution.methodology,
            'computational_cost': solution.computational_cost,
            'validation_results': solution.validation_results,
            'created_at': solution.created_at.isoformat()
        }
    
    def _record_collaboration(self, session: CollaborationSession):
        """Record collaboration session for analysis."""
        collaboration_record = {
            'session_id': session.id,
            'problem_type': session.problem.problem_type.value,
            'participants_count': len(session.participants),
            'tasks_count': len(session.tasks),
            'completion_rate': session.get_completion_rate(),
            'solutions_count': len(session.solutions),
            'duration': (datetime.now() - session.created_at).total_seconds(),
            'success': len(session.solutions) > 0,
            'timestamp': datetime.now().isoformat()
        }
        
        self.collaboration_history.append(collaboration_record)
    
    async def handle_collaboration_invite(self, message: CommunicationMessage):
        """Handle collaboration invitation from another AGI."""
        payload = message.payload
        action = payload.get('action')
        
        try:
            if action == 'invitation':
                await self._handle_collaboration_invitation(message)
            elif action == 'task_assignment':
                await self._handle_task_assignment(message)
            elif action == 'task_result':
                await self._handle_task_result(message)
            elif action == 'solution_submission':
                await self._handle_solution_submission(message)
            else:
                logger.warning(f"Unknown collaboration action: {action}")
        
        except Exception as e:
            logger.error(f"Error handling collaboration invite: {e}")
    
    async def _handle_collaboration_invitation(self, message: CommunicationMessage):
        """Handle collaboration invitation."""
        payload = message.payload
        session_id = payload['session_id']
        
        # Accept invitation by default (can add logic for selective acceptance)
        response_message = CommunicationMessage(
            id=str(uuid.uuid4()),
            sender_id=self.protocol.identity.id,
            receiver_id=message.sender_id,
            message_type=MessageType.COLLABORATION_RESPONSE,
            timestamp=datetime.now(),
            payload={
                'action': 'invitation_response',
                'session_id': session_id,
                'accepted': True,
                'capabilities': list(self.protocol.identity.capabilities)
            }
        )
        
        await self.protocol.send_message(response_message)
    
    async def _handle_task_assignment(self, message: CommunicationMessage):
        """Handle task assignment."""
        payload = message.payload
        session_id = payload['session_id']
        task_data = payload['task']
        
        # Parse task
        task = Task(
            id=task_data['id'],
            problem_id=task_data['problem_id'],
            description=task_data['description'],
            dependencies=task_data['dependencies'],
            status=TaskStatus(task_data['status'])
        )
        
        # Execute task
        try:
            shared_memory = payload.get('shared_memory', {})
            result = await self._perform_task_computation(task, None, shared_memory)
            
            # Send result back
            result_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=message.sender_id,
                message_type=MessageType.COLLABORATION_RESPONSE,
                timestamp=datetime.now(),
                payload={
                    'action': 'task_result',
                    'session_id': session_id,
                    'task_id': task.id,
                    'result': result,
                    'success': True
                }
            )
            
            await self.protocol.send_message(result_message)
            
        except Exception as e:
            # Send error response
            error_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=message.sender_id,
                message_type=MessageType.COLLABORATION_RESPONSE,
                timestamp=datetime.now(),
                payload={
                    'action': 'task_result',
                    'session_id': session_id,
                    'task_id': task.id,
                    'success': False,
                    'error': str(e)
                }
            )
            
            await self.protocol.send_message(error_message)
    
    async def _handle_task_result(self, message: CommunicationMessage):
        """Handle task result from another AGI."""
        payload = message.payload
        session_id = payload['session_id']
        task_id = payload['task_id']
        
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        task = session.tasks.get(task_id)
        
        if not task:
            return
        
        if payload['success']:
            task.mark_completed(payload['result'])
            session.shared_memory[f"task_{task_id}_result"] = payload['result']
            
            # Check if more tasks can be assigned
            await self.assign_next_tasks(session_id)
        else:
            task.mark_failed(payload.get('error', 'Unknown error'))
    
    async def _handle_solution_submission(self, message: CommunicationMessage):
        """Handle solution submission."""
        payload = message.payload
        session_id = payload['session_id']
        solution_data = payload['solution']
        
        # Parse solution
        solution = Solution(
            id=solution_data['id'],
            problem_id=solution_data['problem_id'],
            solution_data=solution_data['solution_data'],
            confidence=solution_data['confidence'],
            contributors=solution_data['contributors'],
            methodology=solution_data.get('methodology', '')
        )
        
        # Add to session
        await self.submit_solution(session_id, solution)
    
    def get_collaboration_statistics(self) -> Dict[str, Any]:
        """Get collaboration statistics."""
        if not self.collaboration_history:
            return {'total_collaborations': 0}
        
        total_collaborations = len(self.collaboration_history)
        successful_collaborations = sum(1 for record in self.collaboration_history if record['success'])
        avg_duration = sum(record['duration'] for record in self.collaboration_history) / total_collaborations
        avg_completion_rate = sum(record['completion_rate'] for record in self.collaboration_history) / total_collaborations
        
        return {
            'total_collaborations': total_collaborations,
            'successful_collaborations': successful_collaborations,
            'success_rate': successful_collaborations / total_collaborations,
            'average_duration_seconds': avg_duration,
            'average_completion_rate': avg_completion_rate,
            'active_sessions': len(self.active_sessions)
        }