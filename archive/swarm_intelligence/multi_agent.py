"""
Multi-Agent Coordination System

This module implements advanced multi-agent coordination capabilities
for swarm intelligence systems, including task allocation, consensus
algorithms, and emergent behavior management.
"""

import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple, Set
import logging
from dataclasses import dataclass
from enum import Enum
import threading
import time
from .base import SwarmAgent, SwarmCoordinator


class AgentRole(Enum):
    """Roles that agents can take in the multi-agent system"""
    LEADER = "leader"
    FOLLOWER = "follower"
    SCOUT = "scout"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    WORKER = "worker"


class TaskType(Enum):
    """Types of tasks in the multi-agent system"""
    EXPLORATION = "exploration"
    EXPLOITATION = "exploitation"
    COMMUNICATION = "communication"
    OPTIMIZATION = "optimization"
    COORDINATION = "coordination"
    MONITORING = "monitoring"


class ConsensusAlgorithm(Enum):
    """Consensus algorithms for multi-agent coordination"""
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_AVERAGE = "weighted_average"
    LEADER_DECISION = "leader_decision"
    AUCTION_BASED = "auction_based"
    BYZANTINE_FAULT_TOLERANT = "byzantine_fault_tolerant"


@dataclass
class Task:
    """Represents a task in the multi-agent system"""
    task_id: str
    task_type: TaskType
    priority: float
    requirements: Dict[str, Any]
    deadline: Optional[float] = None
    assigned_agents: List[str] = None
    status: str = "pending"
    progress: float = 0.0
    
    def __post_init__(self):
        if self.assigned_agents is None:
            self.assigned_agents = []


@dataclass
class Message:
    """Represents a message between agents"""
    sender_id: str
    receiver_id: str
    message_type: str
    content: Dict[str, Any]
    timestamp: float
    priority: int = 0


class MultiAgent(SwarmAgent):
    """
    Enhanced agent with multi-agent coordination capabilities
    
    Extends the base SwarmAgent with role management, task handling,
    communication protocols, and consensus participation.
    """
    
    def __init__(self, agent_id: str, dimension: int, bounds: Tuple[float, float]):
        super().__init__(dimension, bounds)
        
        self.agent_id = agent_id
        self.role = AgentRole.WORKER
        self.capabilities = set()
        self.trust_scores = {}  # Trust scores for other agents
        
        # Task management
        self.assigned_tasks = []
        self.completed_tasks = []
        self.task_history = []
        
        # Communication
        self.message_queue = []
        self.communication_range = 5.0
        self.neighbors = set()
        self.known_agents = set()
        
        # Coordination
        self.consensus_data = {}
        self.voting_power = 1.0
        self.coordination_state = "active"
        
        # Performance tracking
        self.task_success_rate = 0.0
        self.communication_efficiency = 0.0
        self.coordination_contributions = 0
        
        # Learning and adaptation
        self.learning_rate = 0.1
        self.experience_buffer = []
        self.strategy_weights = np.random.random(5)  # 5 different strategies
        
        # Multi-agent specific properties
        self.properties.update({
            'leadership_potential': np.random.random(),
            'cooperation_tendency': np.random.uniform(0.6, 1.0),
            'communication_skill': np.random.uniform(0.5, 1.0),
            'task_efficiency': np.random.uniform(0.4, 0.9),
            'adaptability': np.random.random()
        })
    
    def update_position(self, **kwargs) -> None:
        """Update position considering multi-agent coordination"""
        # Base position update
        coordination_info = kwargs.get('coordination_info', {})
        
        if self.role == AgentRole.LEADER:
            self._leader_movement(coordination_info)
        elif self.role == AgentRole.SCOUT:
            self._scout_movement(coordination_info)
        elif self.role == AgentRole.FOLLOWER:
            self._follower_movement(coordination_info)
        else:
            self._worker_movement(coordination_info)
        
        self.clip_to_bounds()
        self.age += 1
        
        # Update task progress
        self._update_task_progress()
    
    def update_velocity(self, **kwargs) -> None:
        """Update velocity with coordination considerations"""
        # Base velocity update
        momentum = kwargs.get('momentum', 0.1)
        self.velocity *= momentum
        
        # Add coordination influence
        coordination_influence = self._calculate_coordination_influence()
        self.velocity += coordination_influence
    
    def _leader_movement(self, coordination_info: Dict[str, Any]) -> None:
        """Movement pattern for leader agents"""
        # Leaders make strategic moves considering global information
        global_best = coordination_info.get('global_best_position')
        if global_best is not None:
            direction = global_best - self.position
            step_size = 0.1 * self.properties['leadership_potential']
            self.position += step_size * direction
        
        # Add exploration component
        exploration = 0.05 * np.random.randn(self.dimension)
        self.position += exploration
    
    def _scout_movement(self, coordination_info: Dict[str, Any]) -> None:
        """Movement pattern for scout agents"""
        # Scouts explore aggressively
        exploration_radius = coordination_info.get('exploration_radius', 1.0)
        random_direction = np.random.randn(self.dimension)
        random_direction /= np.linalg.norm(random_direction)
        
        step_size = exploration_radius * 0.3
        self.position += step_size * random_direction
    
    def _follower_movement(self, coordination_info: Dict[str, Any]) -> None:
        """Movement pattern for follower agents"""
        # Followers move towards leaders
        leaders = coordination_info.get('leaders', [])
        if leaders:
            # Move towards closest leader
            leader_positions = [leader.position for leader in leaders]
            distances = [np.linalg.norm(pos - self.position) for pos in leader_positions]
            closest_leader_pos = leader_positions[np.argmin(distances)]
            
            direction = closest_leader_pos - self.position
            if np.linalg.norm(direction) > 0:
                direction /= np.linalg.norm(direction)
            
            step_size = 0.2 * self.properties['cooperation_tendency']
            self.position += step_size * direction
    
    def _worker_movement(self, coordination_info: Dict[str, Any]) -> None:
        """Movement pattern for worker agents"""
        # Workers balance exploration and exploitation
        best_position = coordination_info.get('local_best_position', self.best_position)
        
        if best_position is not None:
            # Move towards best known position
            direction = best_position - self.position
            step_size = 0.15 * self.properties['task_efficiency']
            self.position += step_size * direction
        
        # Add small random component
        random_component = 0.05 * np.random.randn(self.dimension)
        self.position += random_component
    
    def _calculate_coordination_influence(self) -> np.ndarray:
        """Calculate influence from coordination with other agents"""
        if not self.neighbors:
            return np.zeros(self.dimension)
        
        total_influence = np.zeros(self.dimension)
        total_weight = 0.0
        
        for neighbor_id in self.neighbors:
            trust = self.trust_scores.get(neighbor_id, 0.5)
            cooperation = self.properties['cooperation_tendency']
            
            # Simplified influence calculation
            influence_weight = trust * cooperation
            # In a real implementation, we'd have neighbor positions
            neighbor_influence = influence_weight * np.random.randn(self.dimension) * 0.01
            
            total_influence += neighbor_influence
            total_weight += influence_weight
        
        if total_weight > 0:
            return total_influence / total_weight
        return np.zeros(self.dimension)
    
    def assign_task(self, task: Task) -> bool:
        """Assign a task to this agent"""
        # Check if agent can handle this task
        if self._can_handle_task(task):
            self.assigned_tasks.append(task)
            task.assigned_agents.append(self.agent_id)
            task.status = "assigned"
            return True
        return False
    
    def _can_handle_task(self, task: Task) -> bool:
        """Check if agent can handle a specific task"""
        # Check task requirements against agent capabilities
        required_capabilities = task.requirements.get('capabilities', set())
        return required_capabilities.issubset(self.capabilities)
    
    def _update_task_progress(self) -> None:
        """Update progress on assigned tasks"""
        for task in self.assigned_tasks:
            if task.status == "assigned":
                task.status = "in_progress"
            
            # Simulate task progress
            progress_increment = self.properties['task_efficiency'] * 0.1
            task.progress = min(1.0, task.progress + progress_increment)
            
            if task.progress >= 1.0:
                task.status = "completed"
                self.completed_tasks.append(task)
                self.assigned_tasks.remove(task)
    
    def send_message(self, receiver_id: str, message_type: str, content: Dict[str, Any]) -> Message:
        """Send a message to another agent"""
        message = Message(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            timestamp=time.time()
        )
        return message
    
    def receive_message(self, message: Message) -> None:
        """Receive and process a message"""
        self.message_queue.append(message)
        self._process_message(message)
    
    def _process_message(self, message: Message) -> None:
        """Process a received message"""
        if message.message_type == "task_assignment":
            task_data = message.content.get('task')
            if task_data:
                task = Task(**task_data)
                self.assign_task(task)
        
        elif message.message_type == "coordination_update":
            coordination_data = message.content.get('coordination_data', {})
            self.consensus_data.update(coordination_data)
        
        elif message.message_type == "trust_update":
            agent_id = message.content.get('agent_id')
            trust_score = message.content.get('trust_score')
            if agent_id and trust_score is not None:
                self.trust_scores[agent_id] = trust_score
    
    def participate_in_consensus(self, proposal: Dict[str, Any], 
                               algorithm: ConsensusAlgorithm) -> Any:
        """Participate in a consensus decision"""
        if algorithm == ConsensusAlgorithm.MAJORITY_VOTE:
            return self._majority_vote(proposal)
        elif algorithm == ConsensusAlgorithm.WEIGHTED_AVERAGE:
            return self._weighted_average(proposal)
        elif algorithm == ConsensusAlgorithm.LEADER_DECISION:
            return self._leader_decision(proposal)
        else:
            return self._default_consensus(proposal)
    
    def _majority_vote(self, proposal: Dict[str, Any]) -> bool:
        """Cast a vote in majority voting"""
        # Simple voting based on agent's assessment
        proposal_quality = proposal.get('quality', 0.5)
        agent_threshold = 0.5 + 0.2 * (self.properties['leadership_potential'] - 0.5)
        return proposal_quality > agent_threshold
    
    def _weighted_average(self, proposal: Dict[str, Any]) -> float:
        """Contribute to weighted average consensus"""
        proposal_value = proposal.get('value', 0.0)
        agent_confidence = self.properties['leadership_potential']
        return proposal_value * agent_confidence
    
    def _leader_decision(self, proposal: Dict[str, Any]) -> Optional[Any]:
        """Make a leader decision if this agent is a leader"""
        if self.role == AgentRole.LEADER:
            return proposal.get('default_decision')
        return None
    
    def _default_consensus(self, proposal: Dict[str, Any]) -> Any:
        """Default consensus behavior"""
        return proposal.get('default_value')
    
    def update_trust_scores(self, interaction_results: Dict[str, float]) -> None:
        """Update trust scores based on interaction results"""
        for agent_id, result in interaction_results.items():
            current_trust = self.trust_scores.get(agent_id, 0.5)
            
            # Update trust using exponential moving average
            alpha = 0.1  # Learning rate for trust updates
            new_trust = (1 - alpha) * current_trust + alpha * result
            self.trust_scores[agent_id] = np.clip(new_trust, 0.0, 1.0)
    
    def get_status_report(self) -> Dict[str, Any]:
        """Generate a comprehensive status report"""
        return {
            'agent_id': self.agent_id,
            'role': self.role.value,
            'position': self.position.tolist(),
            'fitness': self.fitness,
            'assigned_tasks': len(self.assigned_tasks),
            'completed_tasks': len(self.completed_tasks),
            'trust_scores': dict(self.trust_scores),
            'neighbors': list(self.neighbors),
            'coordination_state': self.coordination_state,
            'task_success_rate': self.task_success_rate,
            'communication_efficiency': self.communication_efficiency,
            'properties': dict(self.properties)
        }


class MultiAgentCoordinator(SwarmCoordinator):
    """
    Advanced multi-agent coordination system
    
    Manages multiple agents with different roles, handles task allocation,
    facilitates communication, and coordinates consensus decisions.
    """
    
    def __init__(self, agents: List[MultiAgent]):
        # Convert MultiAgent list to SwarmOptimizer list for base class
        optimizers = []  # We'll handle this differently
        super().__init__(optimizers)
        
        self.agents = agents
        self.tasks = []
        self.message_bus = []
        
        # Role management
        self.role_assignments = {}
        self.leadership_hierarchy = []
        
        # Consensus management
        self.consensus_proposals = []
        self.consensus_results = []
        
        # Performance tracking
        self.coordination_metrics = {
            'task_completion_rate': 0.0,
            'communication_efficiency': 0.0,
            'consensus_success_rate': 0.0,
            'agent_satisfaction': 0.0
        }
        
        # Initialize system
        self._initialize_multi_agent_system()
    
    def _initialize_multi_agent_system(self) -> None:
        """Initialize the multi-agent system"""
        # Assign initial roles
        self._assign_initial_roles()
        
        # Setup communication networks
        self._setup_communication_networks()
        
        # Initialize trust networks
        self._initialize_trust_networks()
        
        self.logger.info(f"Initialized multi-agent system with {len(self.agents)} agents")
    
    def _assign_initial_roles(self) -> None:
        """Assign initial roles to agents"""
        num_agents = len(self.agents)
        num_leaders = max(1, num_agents // 10)  # 10% leaders
        num_scouts = max(1, num_agents // 20)   # 5% scouts
        num_coordinators = max(1, num_agents // 15)  # ~7% coordinators
        
        # Sort agents by leadership potential
        sorted_agents = sorted(self.agents, 
                             key=lambda a: a.properties['leadership_potential'], 
                             reverse=True)
        
        # Assign roles
        for i, agent in enumerate(sorted_agents):
            if i < num_leaders:
                agent.role = AgentRole.LEADER
                self.leadership_hierarchy.append(agent.agent_id)
            elif i < num_leaders + num_scouts:
                agent.role = AgentRole.SCOUT
            elif i < num_leaders + num_scouts + num_coordinators:
                agent.role = AgentRole.COORDINATOR
            else:
                agent.role = AgentRole.WORKER
            
            self.role_assignments[agent.agent_id] = agent.role
    
    def _setup_communication_networks(self) -> None:
        """Setup communication networks between agents"""
        for agent in self.agents:
            # Find neighbors within communication range
            for other_agent in self.agents:
                if agent != other_agent:
                    distance = np.linalg.norm(agent.position - other_agent.position)
                    if distance <= agent.communication_range:
                        agent.neighbors.add(other_agent.agent_id)
                        agent.known_agents.add(other_agent.agent_id)
    
    def _initialize_trust_networks(self) -> None:
        """Initialize trust scores between agents"""
        for agent in self.agents:
            for other_agent in self.agents:
                if agent != other_agent:
                    # Initialize with neutral trust, slightly influenced by cooperation tendency
                    base_trust = 0.5
                    cooperation_bonus = 0.1 * agent.properties['cooperation_tendency']
                    initial_trust = base_trust + cooperation_bonus * (np.random.random() - 0.5)
                    agent.trust_scores[other_agent.agent_id] = np.clip(initial_trust, 0.0, 1.0)
    
    def coordinate_swarms(self, objective_function: Callable) -> Dict[str, Any]:
        """Main coordination loop"""
        coordination_results = {
            'iteration_start': time.time(),
            'tasks_completed': 0,
            'messages_sent': 0,
            'consensus_decisions': 0
        }
        
        # Phase 1: Task allocation and management
        self._manage_tasks()
        
        # Phase 2: Agent updates and evaluation
        self._update_agents(objective_function)
        
        # Phase 3: Communication and information exchange
        self._handle_communications()
        
        # Phase 4: Consensus decisions
        self._process_consensus_decisions()
        
        # Phase 5: Role adaptation
        self._adapt_roles()
        
        # Phase 6: Performance evaluation
        self._evaluate_coordination_performance()
        
        coordination_results['execution_time'] = time.time() - coordination_results['iteration_start']
        return coordination_results
    
    def _manage_tasks(self) -> None:
        """Manage task allocation and execution"""
        # Generate new tasks based on current needs
        self._generate_adaptive_tasks()
        
        # Allocate unassigned tasks
        self._allocate_tasks()
        
        # Monitor task progress
        self._monitor_task_progress()
    
    def _generate_adaptive_tasks(self) -> None:
        """Generate tasks based on current system state"""
        # Analyze current performance
        exploration_needed = self._assess_exploration_needs()
        exploitation_needed = self._assess_exploitation_needs()
        
        # Generate exploration tasks
        if exploration_needed > 0.7:
            task = Task(
                task_id=f"explore_{time.time()}",
                task_type=TaskType.EXPLORATION,
                priority=0.8,
                requirements={'capabilities': {'exploration'}}
            )
            self.tasks.append(task)
        
        # Generate exploitation tasks
        if exploitation_needed > 0.7:
            task = Task(
                task_id=f"exploit_{time.time()}",
                task_type=TaskType.EXPLOITATION,
                priority=0.9,
                requirements={'capabilities': {'optimization'}}
            )
            self.tasks.append(task)
    
    def _assess_exploration_needs(self) -> float:
        """Assess the need for exploration"""
        # Simple heuristic based on diversity
        if len(self.agents) < 2:
            return 0.5
        
        positions = np.array([agent.position for agent in self.agents])
        diversity = np.std(positions)
        return max(0.0, 1.0 - diversity)  # Higher need when diversity is low
    
    def _assess_exploitation_needs(self) -> float:
        """Assess the need for exploitation"""
        # Simple heuristic based on convergence
        best_fitness = min(agent.fitness for agent in self.agents if agent.fitness != float('inf'))
        if best_fitness == float('inf'):
            return 0.0
        
        # Higher exploitation need when we have good solutions
        return min(1.0, 1.0 / (1.0 + best_fitness))
    
    def _allocate_tasks(self) -> None:
        """Allocate tasks to appropriate agents"""
        unassigned_tasks = [task for task in self.tasks if task.status == "pending"]
        available_agents = [agent for agent in self.agents 
                          if len(agent.assigned_tasks) < 3]  # Max 3 tasks per agent
        
        for task in unassigned_tasks:
            # Find best agent for this task
            best_agent = self._find_best_agent_for_task(task, available_agents)
            if best_agent and best_agent.assign_task(task):
                available_agents.remove(best_agent)
    
    def _find_best_agent_for_task(self, task: Task, available_agents: List[MultiAgent]) -> Optional[MultiAgent]:
        """Find the best agent for a specific task"""
        suitable_agents = [agent for agent in available_agents 
                          if agent._can_handle_task(task)]
        
        if not suitable_agents:
            return None
        
        # Score agents based on task suitability
        scores = []
        for agent in suitable_agents:
            score = agent.properties['task_efficiency']
            
            # Bonus for role alignment
            if task.task_type == TaskType.EXPLORATION and agent.role == AgentRole.SCOUT:
                score += 0.3
            elif task.task_type == TaskType.COORDINATION and agent.role == AgentRole.COORDINATOR:
                score += 0.3
            elif agent.role == AgentRole.LEADER:
                score += 0.1  # Leaders get small bonus for all tasks
            
            scores.append(score)
        
        # Return agent with highest score
        best_idx = np.argmax(scores)
        return suitable_agents[best_idx]
    
    def _monitor_task_progress(self) -> None:
        """Monitor progress of all tasks"""
        for task in self.tasks:
            if task.status == "completed":
                continue
            
            # Check for missed deadlines
            if task.deadline and time.time() > task.deadline:
                task.status = "expired"
            
            # Update task priority based on progress
            if task.progress < 0.5 and task.priority < 0.9:
                task.priority += 0.1
    
    def _update_agents(self, objective_function: Callable) -> None:
        """Update all agents"""
        # Prepare coordination information
        coordination_info = self._prepare_coordination_info()
        
        # Update each agent
        for agent in self.agents:
            agent.evaluate_fitness(objective_function)
            agent.update_position(coordination_info=coordination_info)
            agent.update_velocity()
    
    def _prepare_coordination_info(self) -> Dict[str, Any]:
        """Prepare coordination information for agents"""
        # Find global best
        best_agent = min(self.agents, key=lambda a: a.fitness)
        
        # Get leaders
        leaders = [agent for agent in self.agents if agent.role == AgentRole.LEADER]
        
        return {
            'global_best_position': best_agent.position,
            'global_best_fitness': best_agent.fitness,
            'leaders': leaders,
            'exploration_radius': 2.0,  # Dynamic value
            'local_best_position': best_agent.position  # Simplified
        }
    
    def _handle_communications(self) -> None:
        """Handle communication between agents"""
        # Process messages in the message bus
        for message in self.message_bus:
            recipient = self._find_agent_by_id(message.receiver_id)
            if recipient:
                recipient.receive_message(message)
        
        # Clear processed messages
        self.message_bus.clear()
        
        # Generate new communications
        self._generate_status_updates()
        self._generate_coordination_messages()
    
    def _find_agent_by_id(self, agent_id: str) -> Optional[MultiAgent]:
        """Find agent by ID"""
        for agent in self.agents:
            if agent.agent_id == agent_id:
                return agent
        return None
    
    def _generate_status_updates(self) -> None:
        """Generate status update messages"""
        for agent in self.agents:
            if agent.role in [AgentRole.LEADER, AgentRole.COORDINATOR]:
                # Leaders and coordinators broadcast status
                status = agent.get_status_report()
                
                for neighbor_id in agent.neighbors:
                    message = agent.send_message(
                        neighbor_id, 
                        "status_update", 
                        {'status': status}
                    )
                    self.message_bus.append(message)
    
    def _generate_coordination_messages(self) -> None:
        """Generate coordination messages"""
        leaders = [agent for agent in self.agents if agent.role == AgentRole.LEADER]
        
        for leader in leaders:
            # Leaders send coordination updates to followers
            coordination_data = {
                'leader_position': leader.position.tolist(),
                'global_strategy': 'explore',  # Simplified
                'task_priorities': [(task.task_id, task.priority) for task in self.tasks[:5]]
            }
            
            for follower in self.agents:
                if follower.role == AgentRole.FOLLOWER and leader.agent_id in follower.known_agents:
                    message = leader.send_message(
                        follower.agent_id,
                        "coordination_update",
                        {'coordination_data': coordination_data}
                    )
                    self.message_bus.append(message)
    
    def _process_consensus_decisions(self) -> None:
        """Process pending consensus decisions"""
        for proposal in self.consensus_proposals:
            if proposal.get('status') == 'pending':
                result = self._execute_consensus(proposal)
                proposal['status'] = 'completed'
                proposal['result'] = result
                self.consensus_results.append(result)
    
    def _execute_consensus(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a consensus decision"""
        algorithm = proposal.get('algorithm', ConsensusAlgorithm.MAJORITY_VOTE)
        
        # Collect votes/contributions from all agents
        contributions = []
        for agent in self.agents:
            contribution = agent.participate_in_consensus(proposal, algorithm)
            if contribution is not None:
                contributions.append({
                    'agent_id': agent.agent_id,
                    'contribution': contribution,
                    'weight': agent.voting_power
                })
        
        # Calculate consensus result
        if algorithm == ConsensusAlgorithm.MAJORITY_VOTE:
            votes = [c['contribution'] for c in contributions if isinstance(c['contribution'], bool)]
            result = sum(votes) > len(votes) / 2 if votes else False
        
        elif algorithm == ConsensusAlgorithm.WEIGHTED_AVERAGE:
            weighted_sum = sum(c['contribution'] * c['weight'] for c in contributions)
            total_weight = sum(c['weight'] for c in contributions)
            result = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        else:
            result = proposal.get('default_decision', None)
        
        return {
            'proposal_id': proposal.get('proposal_id'),
            'algorithm': algorithm.value,
            'result': result,
            'participation_rate': len(contributions) / len(self.agents),
            'contributions': contributions
        }
    
    def _adapt_roles(self) -> None:
        """Adapt agent roles based on performance"""
        # Evaluate agent performance
        performance_scores = {}
        for agent in self.agents:
            score = self._calculate_agent_performance(agent)
            performance_scores[agent.agent_id] = score
        
        # Promote high-performing agents
        self._promote_agents(performance_scores)
        
        # Demote under-performing agents
        self._demote_agents(performance_scores)
    
    def _calculate_agent_performance(self, agent: MultiAgent) -> float:
        """Calculate overall performance score for an agent"""
        # Base performance from task completion
        task_performance = len(agent.completed_tasks) / max(1, len(agent.task_history))
        
        # Communication effectiveness
        communication_score = agent.communication_efficiency
        
        # Fitness improvement
        fitness_score = 1.0 / (1.0 + agent.fitness) if agent.fitness != float('inf') else 0.0
        
        # Weighted combination
        performance = (0.4 * task_performance + 
                      0.3 * communication_score + 
                      0.3 * fitness_score)
        
        return performance
    
    def _promote_agents(self, performance_scores: Dict[str, float]) -> None:
        """Promote high-performing agents"""
        # Sort by performance
        sorted_agents = sorted(performance_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Promote top 10% of workers to higher roles
        num_promotions = max(1, len(self.agents) // 10)
        
        for agent_id, score in sorted_agents[:num_promotions]:
            agent = self._find_agent_by_id(agent_id)
            if agent and agent.role == AgentRole.WORKER and score > 0.7:
                # Promote based on capabilities
                if agent.properties['leadership_potential'] > 0.8:
                    agent.role = AgentRole.LEADER
                elif agent.properties['cooperation_tendency'] > 0.8:
                    agent.role = AgentRole.COORDINATOR
                else:
                    agent.role = AgentRole.SPECIALIST
                
                self.role_assignments[agent_id] = agent.role
    
    def _demote_agents(self, performance_scores: Dict[str, float]) -> None:
        """Demote under-performing agents"""
        # Sort by performance (worst first)
        sorted_agents = sorted(performance_scores.items(), key=lambda x: x[1])
        
        # Demote bottom 5% of leaders/coordinators
        num_demotions = max(1, len(self.agents) // 20)
        
        for agent_id, score in sorted_agents[:num_demotions]:
            agent = self._find_agent_by_id(agent_id)
            if (agent and 
                agent.role in [AgentRole.LEADER, AgentRole.COORDINATOR] and 
                score < 0.3):
                
                agent.role = AgentRole.WORKER
                self.role_assignments[agent_id] = agent.role
    
    def _evaluate_coordination_performance(self) -> None:
        """Evaluate overall coordination performance"""
        # Task completion rate
        completed_tasks = sum(len(agent.completed_tasks) for agent in self.agents)
        total_tasks = len(self.tasks)
        self.coordination_metrics['task_completion_rate'] = (
            completed_tasks / max(1, total_tasks)
        )
        
        # Communication efficiency
        total_comm_efficiency = sum(agent.communication_efficiency for agent in self.agents)
        self.coordination_metrics['communication_efficiency'] = (
            total_comm_efficiency / len(self.agents)
        )
        
        # Consensus success rate
        successful_consensus = sum(1 for result in self.consensus_results 
                                 if result.get('participation_rate', 0) > 0.7)
        total_consensus = len(self.consensus_results)
        self.coordination_metrics['consensus_success_rate'] = (
            successful_consensus / max(1, total_consensus)
        )
        
        # Agent satisfaction (simplified)
        avg_performance = np.mean([self._calculate_agent_performance(agent) 
                                 for agent in self.agents])
        self.coordination_metrics['agent_satisfaction'] = avg_performance
    
    def exchange_information(self) -> None:
        """Exchange information between agents"""
        # This is handled in _handle_communications
        pass
    
    def get_coordination_status(self) -> Dict[str, Any]:
        """Get comprehensive coordination status"""
        base_status = super().get_coordination_status()
        
        # Add multi-agent specific information
        multi_agent_status = {
            'total_agents': len(self.agents),
            'role_distribution': {
                role.value: sum(1 for agent in self.agents if agent.role == role)
                for role in AgentRole
            },
            'active_tasks': len([task for task in self.tasks if task.status != 'completed']),
            'completed_tasks': len([task for task in self.tasks if task.status == 'completed']),
            'pending_messages': len(self.message_bus),
            'consensus_proposals': len(self.consensus_proposals),
            'coordination_metrics': self.coordination_metrics,
            'leadership_hierarchy': self.leadership_hierarchy[:5],  # Top 5 leaders
            'average_trust_score': np.mean([
                np.mean(list(agent.trust_scores.values())) if agent.trust_scores else 0.5
                for agent in self.agents
            ])
        }
        
        base_status.update(multi_agent_status)
        return base_status


# Factory function for easy instantiation
def create_multi_agent_system(num_agents: int = 20,
                             dimension: int = 2,
                             bounds: Tuple[float, float] = (-10.0, 10.0)) -> MultiAgentCoordinator:
    """
    Create a multi-agent coordination system
    
    Args:
        num_agents: Number of agents in the system
        dimension: Problem dimension
        bounds: Search space bounds
        
    Returns:
        Configured MultiAgentCoordinator instance
    """
    agents = [
        MultiAgent(f"agent_{i}", dimension, bounds)
        for i in range(num_agents)
    ]
    
    return MultiAgentCoordinator(agents)