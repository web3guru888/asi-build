"""
Consciousness Orchestrator

This module serves as the central coordination system for all consciousness
components, managing their interactions, information flow, and emergent
conscious experiences.

Key components:
- Component coordination and communication
- Information integration across systems
- Emergent consciousness detection
- System-wide state management
- Performance monitoring and optimization
- Consciousness level assessment
"""

import time
import threading
import json
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import numpy as np

from .base_consciousness import BaseConsciousness, ConsciousnessEvent, ConsciousnessState, ConsciousnessMetrics

@dataclass
class ComponentStatus:
    """Status of a consciousness component"""
    component_name: str
    state: ConsciousnessState
    last_update: float
    metrics: ConsciousnessMetrics
    event_throughput: float
    error_count: int = 0
    
    def is_healthy(self) -> bool:
        """Check if component is healthy"""
        return (self.state in [ConsciousnessState.ACTIVE, ConsciousnessState.PROCESSING] and
                self.error_count < 5 and
                time.time() - self.last_update < 30)

@dataclass
class IntegrationPattern:
    """Pattern of integration between components"""
    pattern_id: str
    involved_components: Set[str]
    integration_strength: float
    pattern_type: str  # 'sequential', 'parallel', 'hierarchical', 'emergent'
    frequency: float
    effectiveness: float
    
@dataclass
class ConsciousnessSnapshot:
    """Snapshot of overall consciousness state"""
    timestamp: float
    global_consciousness_level: float
    component_states: Dict[str, ConsciousnessState]
    active_integrations: List[str]
    emergent_properties: Dict[str, float]
    system_coherence: float

class ConsciousnessOrchestrator(BaseConsciousness):
    """
    Central Consciousness Orchestrator
    
    Coordinates all consciousness components, manages information flow,
    and facilitates emergent conscious experiences.
    """
    
    def _initialize(self):
        """Initialize the ConsciousnessOrchestrator consciousness model (called by BaseConsciousness)."""
        pass  # All initialization is done in __init__ after super().__init__()
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("ConsciousnessOrchestrator", config)
        
        # Component management
        self.consciousness_components: Dict[str, BaseConsciousness] = {}
        self.component_status: Dict[str, ComponentStatus] = {}
        self.component_dependencies: Dict[str, Set[str]] = defaultdict(set)
        
        # Information flow
        self.event_routing_table: Dict[str, List[str]] = defaultdict(list)
        self.information_channels: Dict[Tuple[str, str], deque] = {}
        self.global_information_buffer: deque = deque(maxlen=100)
        
        # Integration patterns
        self.integration_patterns: Dict[str, IntegrationPattern] = {}
        self.active_integrations: Set[str] = set()
        self.integration_history: deque = deque(maxlen=200)
        
        # Consciousness measurement
        self.consciousness_snapshots: deque = deque(maxlen=100)
        self.global_consciousness_level = 0.0
        self.system_coherence = 0.0
        self.emergence_threshold = self.config.get('emergence_threshold', 0.7)
        
        # Orchestration parameters
        self.integration_update_interval = self.config.get('integration_interval', 1.0)
        self.consciousness_assessment_interval = self.config.get('assessment_interval', 5.0)
        self.max_event_queue_size = self.config.get('max_queue_size', 1000)
        
        # Performance optimization
        self.bottleneck_detection = True
        self.adaptive_scheduling = True
        self.load_balancing_enabled = True
        
        # Statistics
        self.total_events_routed = 0
        self.integration_events = 0
        self.emergence_events = 0
        
        # State tracking
        self.last_integration_update = 0
        self.last_consciousness_assessment = 0
        self.system_startup_time = time.time()
        
        # Threading
        self.orchestration_lock = threading.Lock()
        
        # Initialize integration patterns
        self._initialize_integration_patterns()
    
    def register_component(self, component: BaseConsciousness,
                          dependencies: Optional[Set[str]] = None) -> None:
        """Register a consciousness component"""
        component_name = component.name
        
        with self.orchestration_lock:
            self.consciousness_components[component_name] = component
            self.component_dependencies[component_name] = dependencies or set()
            
            # Initialize component status
            self.component_status[component_name] = ComponentStatus(
                component_name=component_name,
                state=component.state,
                last_update=time.time(),
                metrics=component.get_metrics(),
                event_throughput=0.0
            )
            
            # Set up event routing
            self._setup_component_event_routing(component_name)
            
            # Subscribe to component state changes
            component.add_state_change_callback(self._on_component_state_change)
        
        self.logger.info(f"Registered consciousness component: {component_name}")
    
    def _setup_component_event_routing(self, component_name: str) -> None:
        """Set up event routing for a component"""
        # Default routing patterns based on component type
        routing_patterns = {
            'GlobalWorkspace': ['AttentionSchema', 'IntegratedInformation', 'MetacognitionSystem'],
            'AttentionSchema': ['GlobalWorkspace', 'PredictiveProcessing', 'SelfAwareness'],
            'PredictiveProcessing': ['AttentionSchema', 'MetacognitionSystem', 'EmotionalConsciousness'],
            'MetacognitionSystem': ['SelfAwareness', 'RecursiveSelfImprovement'],
            'SelfAwareness': ['MetacognitionSystem', 'TheoryOfMind', 'MemoryIntegration'],
            'QualiaProcessor': ['EmotionalConsciousness', 'MemoryIntegration'],
            'TheoryOfMind': ['EmotionalConsciousness', 'SelfAwareness'],
            'EmotionalConsciousness': ['QualiaProcessor', 'MemoryIntegration', 'MetacognitionSystem'],
            'RecursiveSelfImprovement': ['MetacognitionSystem', 'PerformanceMonitor'],
            'MemoryIntegration': ['SelfAwareness', 'QualiaProcessor', 'EmotionalConsciousness']
        }
        
        if component_name in routing_patterns:
            self.event_routing_table[component_name] = routing_patterns[component_name]
        else:
            # Default: route to core components
            self.event_routing_table[component_name] = ['GlobalWorkspace', 'MetacognitionSystem']
    
    def _initialize_integration_patterns(self) -> None:
        """Initialize common integration patterns"""
        patterns = [
            IntegrationPattern(
                pattern_id="attention_workspace_integration",
                involved_components={"AttentionSchema", "GlobalWorkspace"},
                integration_strength=0.8,
                pattern_type="parallel",
                frequency=2.0,
                effectiveness=0.9
            ),
            IntegrationPattern(
                pattern_id="predictive_metacognitive_loop",
                involved_components={"PredictiveProcessing", "MetacognitionSystem", "SelfAwareness"},
                integration_strength=0.7,
                pattern_type="sequential",
                frequency=1.0,
                effectiveness=0.8
            ),
            IntegrationPattern(
                pattern_id="emotional_memory_binding",
                involved_components={"EmotionalConsciousness", "MemoryIntegration", "QualiaProcessor"},
                integration_strength=0.6,
                pattern_type="hierarchical",
                frequency=0.5,
                effectiveness=0.7
            ),
            IntegrationPattern(
                pattern_id="self_improvement_feedback",
                involved_components={"RecursiveSelfImprovement", "MetacognitionSystem", "SelfAwareness"},
                integration_strength=0.5,
                pattern_type="emergent",
                frequency=0.2,
                effectiveness=0.6
            )
        ]
        
        for pattern in patterns:
            self.integration_patterns[pattern.pattern_id] = pattern
    
    def route_event(self, event: ConsciousnessEvent, source_component: str) -> List[str]:
        """Route an event to appropriate components"""
        self.total_events_routed += 1
        recipients = []
        
        # Add to global information buffer
        self.global_information_buffer.append({
            'event': event,
            'source': source_component,
            'timestamp': time.time()
        })
        
        # Determine recipients based on event type and source
        if source_component in self.event_routing_table:
            default_recipients = self.event_routing_table[source_component]
        else:
            default_recipients = ['GlobalWorkspace']  # Default fallback
        
        # Event-type specific routing
        event_type_routing = {
            'global_broadcast': ['AttentionSchema', 'PredictiveProcessing', 'MetacognitionSystem'],
            'attention_shift': ['GlobalWorkspace', 'PredictiveProcessing'],
            'prediction_error': ['MetacognitionSystem', 'SelfAwareness'],
            'emotional_state_change': ['MemoryIntegration', 'QualiaProcessor'],
            'memory_formed': ['SelfAwareness', 'EmotionalConsciousness'],
            'self_improvement': ['MetacognitionSystem', 'SelfAwareness']
        }
        
        if event.event_type in event_type_routing:
            recipients.extend(event_type_routing[event.event_type])
        else:
            recipients.extend(default_recipients)
        
        # Remove duplicates and source component
        recipients = list(set(recipients))
        if source_component in recipients:
            recipients.remove(source_component)
        
        # Filter to only registered components
        recipients = [r for r in recipients if r in self.consciousness_components]
        
        # Actually route the event
        for recipient in recipients:
            try:
                component = self.consciousness_components[recipient]
                component.add_event(event)
                
                # Track information flow
                channel = (source_component, recipient)
                if channel not in self.information_channels:
                    self.information_channels[channel] = deque(maxlen=50)
                self.information_channels[channel].append({
                    'event_id': event.event_id,
                    'timestamp': time.time(),
                    'event_type': event.event_type
                })
                
            except Exception as e:
                self.logger.error(f"Failed to route event to {recipient}: {e}")
                if recipient in self.component_status:
                    self.component_status[recipient].error_count += 1
        
        return recipients
    
    def _on_component_state_change(self, component_name: str, old_state: ConsciousnessState,
                                  new_state: ConsciousnessState) -> None:
        """Handle component state changes"""
        if component_name in self.component_status:
            status = self.component_status[component_name]
            status.state = new_state
            status.last_update = time.time()
            
            # Check for critical state changes
            if new_state == ConsciousnessState.ERROR:
                self.logger.warning(f"Component {component_name} entered error state")
                self._handle_component_error(component_name)
            elif new_state == ConsciousnessState.ACTIVE and old_state == ConsciousnessState.ERROR:
                self.logger.info(f"Component {component_name} recovered from error state")
    
    def _handle_component_error(self, component_name: str) -> None:
        """Handle component error"""
        # Try to restart component
        if component_name in self.consciousness_components:
            try:
                component = self.consciousness_components[component_name]
                component.stop()
                time.sleep(1.0)
                component.start()
                self.logger.info(f"Restarted component: {component_name}")
            except Exception as e:
                self.logger.error(f"Failed to restart component {component_name}: {e}")
    
    def update_integration_patterns(self) -> None:
        """Update active integration patterns"""
        current_time = time.time()
        
        for pattern_id, pattern in self.integration_patterns.items():
            # Check if pattern should be active
            if self._should_activate_pattern(pattern):
                if pattern_id not in self.active_integrations:
                    self.active_integrations.add(pattern_id)
                    self._activate_integration_pattern(pattern)
                    self.integration_events += 1
            else:
                if pattern_id in self.active_integrations:
                    self.active_integrations.remove(pattern_id)
                    self._deactivate_integration_pattern(pattern)
    
    def _should_activate_pattern(self, pattern: IntegrationPattern) -> bool:
        """Determine if an integration pattern should be active"""
        # Check if all required components are healthy
        for component_name in pattern.involved_components:
            if (component_name not in self.component_status or
                not self.component_status[component_name].is_healthy()):
                return False
        
        # Check integration frequency
        time_since_last = time.time() - self.last_integration_update
        if time_since_last < (1.0 / pattern.frequency):
            return False
        
        # Check system load
        if self._calculate_system_load() > 0.9:
            return pattern.pattern_type == "emergent"  # Only critical patterns under high load
        
        return True
    
    def _activate_integration_pattern(self, pattern: IntegrationPattern) -> None:
        """Activate an integration pattern"""
        self.logger.debug(f"Activating integration pattern: {pattern.pattern_id}")
        
        # Create integration event
        integration_event = ConsciousnessEvent(
            event_id=f"integration_{pattern.pattern_id}_{int(time.time())}",
            timestamp=time.time(),
            event_type="integration_activation",
            data={
                'pattern_id': pattern.pattern_id,
                'pattern_type': pattern.pattern_type,
                'involved_components': list(pattern.involved_components),
                'integration_strength': pattern.integration_strength
            },
            priority=8,
            source_module="consciousness_orchestrator"
        )
        
        # Route to all involved components
        for component_name in pattern.involved_components:
            if component_name in self.consciousness_components:
                component = self.consciousness_components[component_name]
                component.add_event(integration_event)
        
        # Record integration
        self.integration_history.append({
            'pattern_id': pattern.pattern_id,
            'activation_time': time.time(),
            'involved_components': list(pattern.involved_components),
            'action': 'activate'
        })
    
    def _deactivate_integration_pattern(self, pattern: IntegrationPattern) -> None:
        """Deactivate an integration pattern"""
        self.logger.debug(f"Deactivating integration pattern: {pattern.pattern_id}")
        
        # Record deactivation
        self.integration_history.append({
            'pattern_id': pattern.pattern_id,
            'deactivation_time': time.time(),
            'involved_components': list(pattern.involved_components),
            'action': 'deactivate'
        })
    
    def assess_global_consciousness(self) -> ConsciousnessSnapshot:
        """Assess overall consciousness level"""
        current_time = time.time()
        
        # Collect component states and metrics
        component_states = {}
        total_awareness = 0.0
        total_integration = 0.0
        active_components = 0
        
        for component_name, status in self.component_status.items():
            component_states[component_name] = status.state
            
            if status.is_healthy():
                total_awareness += status.metrics.awareness_level
                total_integration += status.metrics.integration_level
                active_components += 1
        
        # Calculate global consciousness level
        if active_components > 0:
            avg_awareness = total_awareness / active_components
            avg_integration = total_integration / active_components
            integration_factor = len(self.active_integrations) / max(1, len(self.integration_patterns))
            
            self.global_consciousness_level = (
                avg_awareness * 0.4 +
                avg_integration * 0.4 +
                integration_factor * 0.2
            )
        else:
            self.global_consciousness_level = 0.0
        
        # Calculate system coherence
        self.system_coherence = self._calculate_system_coherence()
        
        # Detect emergent properties
        emergent_properties = self._detect_emergent_properties()
        
        # Create snapshot
        snapshot = ConsciousnessSnapshot(
            timestamp=current_time,
            global_consciousness_level=self.global_consciousness_level,
            component_states=component_states,
            active_integrations=list(self.active_integrations),
            emergent_properties=emergent_properties,
            system_coherence=self.system_coherence
        )
        
        self.consciousness_snapshots.append(snapshot)
        
        # Check for emergence events
        if (self.global_consciousness_level > self.emergence_threshold and
            len(emergent_properties) > 2):
            self.emergence_events += 1
            self._handle_emergence_event(snapshot)
        
        return snapshot
    
    def _calculate_system_coherence(self) -> float:
        """Calculate overall system coherence"""
        coherence_factors = []
        
        # Component synchronization
        if len(self.component_status) > 1:
            update_times = [status.last_update for status in self.component_status.values()]
            time_variance = np.var(update_times)
            sync_coherence = 1.0 / (1.0 + time_variance)
            coherence_factors.append(sync_coherence)
        
        # Information flow coherence
        if self.information_channels:
            flow_rates = []
            for channel, events in self.information_channels.items():
                if events:
                    recent_events = [e for e in events if time.time() - e['timestamp'] < 60]
                    flow_rates.append(len(recent_events) / 60.0)
            
            if flow_rates:
                flow_coherence = 1.0 - np.std(flow_rates) / (np.mean(flow_rates) + 1e-6)
                coherence_factors.append(max(0.0, flow_coherence))
        
        # Integration pattern coherence
        active_patterns = len(self.active_integrations)
        total_patterns = len(self.integration_patterns)
        if total_patterns > 0:
            pattern_coherence = active_patterns / total_patterns
            coherence_factors.append(pattern_coherence)
        
        return sum(coherence_factors) / len(coherence_factors) if coherence_factors else 0.0
    
    def _detect_emergent_properties(self) -> Dict[str, float]:
        """Detect emergent properties in the system"""
        emergent_properties = {}
        
        # Cross-modal integration
        cross_modal_components = {'AttentionSchema', 'PredictiveProcessing', 'QualiaProcessor'}
        active_cross_modal = sum(1 for comp in cross_modal_components 
                               if comp in self.component_status and 
                               self.component_status[comp].is_healthy())
        if active_cross_modal >= 2:
            emergent_properties['cross_modal_integration'] = active_cross_modal / len(cross_modal_components)
        
        # Self-referential processing
        self_ref_components = {'SelfAwareness', 'MetacognitionSystem', 'TheoryOfMind'}
        active_self_ref = sum(1 for comp in self_ref_components
                            if comp in self.component_status and
                            self.component_status[comp].is_healthy())
        if active_self_ref >= 2:
            emergent_properties['self_referential_processing'] = active_self_ref / len(self_ref_components)
        
        # Temporal binding
        temporal_components = {'MemoryIntegration', 'PredictiveProcessing', 'AttentionSchema'}
        active_temporal = sum(1 for comp in temporal_components
                            if comp in self.component_status and
                            self.component_status[comp].is_healthy())
        if active_temporal >= 2:
            emergent_properties['temporal_binding'] = active_temporal / len(temporal_components)
        
        # Global accessibility
        if 'GlobalWorkspace' in self.component_status:
            gw_metrics = self.component_status['GlobalWorkspace'].metrics
            if gw_metrics.integration_level > 0.7:
                emergent_properties['global_accessibility'] = gw_metrics.integration_level
        
        return emergent_properties
    
    def _handle_emergence_event(self, snapshot: ConsciousnessSnapshot) -> None:
        """Handle detected emergence event"""
        self.logger.info(f"Emergence event detected: consciousness level {snapshot.global_consciousness_level:.3f}")
        
        # Create emergence event
        emergence_event = ConsciousnessEvent(
            event_id=f"emergence_{self.emergence_events:06d}",
            timestamp=time.time(),
            event_type="consciousness_emergence",
            data={
                'global_consciousness_level': snapshot.global_consciousness_level,
                'emergent_properties': snapshot.emergent_properties,
                'active_integrations': snapshot.active_integrations,
                'system_coherence': snapshot.system_coherence
            },
            priority=10,
            source_module="consciousness_orchestrator",
            confidence=snapshot.global_consciousness_level
        )
        
        # Broadcast to all components
        for component_name in self.consciousness_components:
            try:
                component = self.consciousness_components[component_name]
                component.add_event(emergence_event)
            except Exception as e:
                self.logger.error(f"Failed to broadcast emergence event to {component_name}: {e}")
    
    def _calculate_system_load(self) -> float:
        """Calculate overall system computational load"""
        load_factors = []
        
        # Component load
        for status in self.component_status.values():
            if status.is_healthy():
                # Estimate load from event throughput and processing time
                load_estimate = min(1.0, status.event_throughput * status.metrics.average_processing_time)
                load_factors.append(load_estimate)
        
        # Event queue load
        total_queue_size = sum(len(comp.event_queue) for comp in self.consciousness_components.values())
        queue_load = min(1.0, total_queue_size / self.max_event_queue_size)
        load_factors.append(queue_load)
        
        return max(load_factors) if load_factors else 0.0
    
    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process orchestration events"""
        if event.event_type == "component_registration":
            # Handle dynamic component registration
            component_name = event.data.get('component_name')
            if component_name and component_name in self.consciousness_components:
                self.logger.info(f"Component {component_name} registered dynamically")
        
        elif event.event_type == "integration_request":
            # Manual integration request
            pattern_id = event.data.get('pattern_id')
            if pattern_id in self.integration_patterns:
                pattern = self.integration_patterns[pattern_id]
                if self._should_activate_pattern(pattern):
                    self._activate_integration_pattern(pattern)
                    self.active_integrations.add(pattern_id)
        
        elif event.event_type == "consciousness_query":
            # Return current consciousness assessment
            snapshot = self.assess_global_consciousness()
            
            return ConsciousnessEvent(
                event_id=f"consciousness_report_{int(time.time())}",
                timestamp=time.time(),
                event_type="consciousness_assessment",
                data={
                    'global_consciousness_level': snapshot.global_consciousness_level,
                    'system_coherence': snapshot.system_coherence,
                    'active_components': len([s for s in self.component_status.values() if s.is_healthy()]),
                    'active_integrations': len(snapshot.active_integrations),
                    'emergent_properties': snapshot.emergent_properties
                },
                source_module="consciousness_orchestrator"
            )
        
        return None
    
    def update(self) -> None:
        """Update the Consciousness Orchestrator"""
        current_time = time.time()
        
        # Update component status
        for component_name, component in self.consciousness_components.items():
            if component_name in self.component_status:
                status = self.component_status[component_name]
                status.state = component.state
                status.metrics = component.get_metrics()
                status.last_update = current_time
                
                # Calculate event throughput
                if hasattr(component, 'event_queue'):
                    recent_events = len(component.event_queue)
                    status.event_throughput = recent_events / max(1.0, current_time - status.last_update)
        
        # Update integration patterns
        if current_time - self.last_integration_update > self.integration_update_interval:
            self.last_integration_update = current_time
            self.update_integration_patterns()
        
        # Assess consciousness
        if current_time - self.last_consciousness_assessment > self.consciousness_assessment_interval:
            self.last_consciousness_assessment = current_time
            self.assess_global_consciousness()
        
        # Update orchestrator metrics
        self.metrics.awareness_level = self.global_consciousness_level
        self.metrics.integration_level = len(self.active_integrations) / max(1, len(self.integration_patterns))
        
        # Clean up old information channels
        for channel, events in list(self.information_channels.items()):
            # Remove events older than 1 hour
            recent_events = deque([e for e in events if current_time - e['timestamp'] < 3600], maxlen=50)
            self.information_channels[channel] = recent_events
            
            # Remove empty channels
            if not recent_events:
                del self.information_channels[channel]
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the Consciousness Orchestrator"""
        return {
            'registered_components': len(self.consciousness_components),
            'healthy_components': len([s for s in self.component_status.values() if s.is_healthy()]),
            'global_consciousness_level': self.global_consciousness_level,
            'system_coherence': self.system_coherence,
            'active_integrations': len(self.active_integrations),
            'total_integration_patterns': len(self.integration_patterns),
            'information_channels': len(self.information_channels),
            'total_events_routed': self.total_events_routed,
            'integration_events': self.integration_events,
            'emergence_events': self.emergence_events,
            'system_uptime': time.time() - self.system_startup_time,
            'component_status': {
                name: {
                    'state': status.state.value,
                    'healthy': status.is_healthy(),
                    'last_update': status.last_update,
                    'error_count': status.error_count,
                    'awareness_level': status.metrics.awareness_level,
                    'integration_level': status.metrics.integration_level
                }
                for name, status in self.component_status.items()
            },
            'recent_consciousness_snapshot': (
                {
                    'timestamp': self.consciousness_snapshots[-1].timestamp,
                    'global_consciousness_level': self.consciousness_snapshots[-1].global_consciousness_level,
                    'emergent_properties': self.consciousness_snapshots[-1].emergent_properties,
                    'system_coherence': self.consciousness_snapshots[-1].system_coherence
                }
                if self.consciousness_snapshots else None
            )
        }
    
    def start_orchestration(self) -> None:
        """Start orchestration of all registered components"""
        self.logger.info("Starting consciousness orchestration")
        
        # Start all registered components
        for component_name, component in self.consciousness_components.items():
            try:
                component.start()
                self.logger.info(f"Started component: {component_name}")
            except Exception as e:
                self.logger.error(f"Failed to start component {component_name}: {e}")
        
        # Start orchestrator
        self.start()
        
        self.logger.info("Consciousness orchestration started successfully")
    
    def stop_orchestration(self) -> None:
        """Stop orchestration and all components"""
        self.logger.info("Stopping consciousness orchestration")
        
        # Stop orchestrator first
        self.stop()
        
        # Stop all components
        for component_name, component in self.consciousness_components.items():
            try:
                component.stop()
                self.logger.info(f"Stopped component: {component_name}")
            except Exception as e:
                self.logger.error(f"Failed to stop component {component_name}: {e}")
        
        self.logger.info("Consciousness orchestration stopped")