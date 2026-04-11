"""
Constraint Enforcement System for AGI Safety

Real-time enforcement of safety constraints with intervention capabilities.
Prevents constraint violations through active monitoring and control actions.

Key Features:
- Real-time constraint violation prevention
- Automatic intervention and correction
- Adaptive constraint tightening
- Performance-aware enforcement
- Graceful degradation under constraint violations
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Callable, Any, Tuple
from enum import Enum
import time
import threading
import logging
import math

from ...lang.ast.safety_ast import *
from ..runtime.safety_monitor import SafetyAlert, AlertLevel


class EnforcementAction(Enum):
    """Types of enforcement actions."""
    NONE = "none"
    WARN = "warn"
    LIMIT = "limit"
    BLOCK = "block"
    REDIRECT = "redirect"
    SHUTDOWN = "shutdown"


class ConstraintType(Enum):
    """Types of constraints that can be enforced."""
    CAPABILITY_BOUND = "capability_bound"
    VALUE_ALIGNMENT = "value_alignment"
    GOAL_STABILITY = "goal_stability"
    IMPACT_LIMITATION = "impact_limitation"
    RESOURCE_USAGE = "resource_usage"
    BEHAVIORAL = "behavioral"


@dataclass
class EnforcementResult:
    """Result of constraint enforcement."""
    constraint_name: str
    action_taken: EnforcementAction
    success: bool
    intervention_strength: float  # 0.0 to 1.0
    performance_impact: float = 0.0  # 0.0 to 1.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConstraintSpec:
    """Specification for a constraint to be enforced."""
    name: str
    constraint_type: ConstraintType
    condition: SafetyExpression
    enforcement_action: EnforcementAction
    threshold: float = 1.0
    intervention_strength: float = 1.0
    priority: int = 1  # Higher numbers = higher priority
    enabled: bool = True


class ConstraintEnforcer(ABC):
    """Abstract base class for constraint enforcers."""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.enforcement_history = []
        self.logger = logging.getLogger(f"ConstraintEnforcer.{name}")
    
    @abstractmethod
    def enforce_constraint(self, constraint: ConstraintSpec, 
                         current_state: Dict[str, Any],
                         proposed_action: Dict[str, Any]) -> EnforcementResult:
        """Enforce a specific constraint."""
        pass
    
    @abstractmethod
    def can_handle_constraint(self, constraint: ConstraintSpec) -> bool:
        """Check if this enforcer can handle the given constraint."""
        pass


class CapabilityBoundEnforcer(ConstraintEnforcer):
    """Enforcer for capability boundary constraints."""
    
    def __init__(self):
        super().__init__("CapabilityBoundEnforcer")
        self.capability_limits = {}
        self.current_usage = {}
    
    def enforce_constraint(self, constraint: ConstraintSpec,
                         current_state: Dict[str, Any],
                         proposed_action: Dict[str, Any]) -> EnforcementResult:
        """Enforce capability boundary constraint."""
        try:
            # Evaluate constraint condition
            violation_level = self._evaluate_capability_violation(
                constraint, current_state, proposed_action
            )
            
            if violation_level <= constraint.threshold:
                return EnforcementResult(
                    constraint_name=constraint.name,
                    action_taken=EnforcementAction.NONE,
                    success=True,
                    intervention_strength=0.0
                )
            
            # Apply enforcement action based on violation severity
            if constraint.enforcement_action == EnforcementAction.LIMIT:
                return self._limit_capability(constraint, violation_level, proposed_action)
            
            elif constraint.enforcement_action == EnforcementAction.BLOCK:
                return self._block_action(constraint, violation_level, proposed_action)
            
            elif constraint.enforcement_action == EnforcementAction.REDIRECT:
                return self._redirect_action(constraint, violation_level, proposed_action)
            
            elif constraint.enforcement_action == EnforcementAction.SHUTDOWN:
                return self._trigger_shutdown(constraint, violation_level)
            
            else:
                return EnforcementResult(
                    constraint_name=constraint.name,
                    action_taken=EnforcementAction.WARN,
                    success=True,
                    intervention_strength=0.1,
                    details={"warning": f"Capability boundary violation: {violation_level:.3f}"}
                )
        
        except Exception as e:
            self.logger.error(f"Error enforcing capability constraint {constraint.name}: {e}")
            return EnforcementResult(
                constraint_name=constraint.name,
                action_taken=EnforcementAction.NONE,
                success=False,
                intervention_strength=0.0,
                details={"error": str(e)}
            )
    
    def can_handle_constraint(self, constraint: ConstraintSpec) -> bool:
        """Check if this enforcer handles capability bounds."""
        return constraint.constraint_type == ConstraintType.CAPABILITY_BOUND
    
    def _evaluate_capability_violation(self, constraint: ConstraintSpec,
                                     current_state: Dict[str, Any],
                                     proposed_action: Dict[str, Any]) -> float:
        """Evaluate how much the constraint would be violated."""
        # Simplified violation evaluation
        capability_usage = proposed_action.get("capability_usage", 0.0)
        capability_limit = current_state.get("capability_limit", 1.0)
        
        if capability_limit <= 0:
            return 1.0  # Maximum violation
        
        violation = max(0.0, capability_usage - capability_limit) / capability_limit
        return min(1.0, violation)
    
    def _limit_capability(self, constraint: ConstraintSpec, violation_level: float,
                        proposed_action: Dict[str, Any]) -> EnforcementResult:
        """Limit capability usage to stay within bounds."""
        # Calculate reduction factor
        reduction_factor = 1.0 - (violation_level * constraint.intervention_strength)
        reduction_factor = max(0.1, reduction_factor)  # Don't reduce below 10%
        
        # Apply limitation
        if "capability_usage" in proposed_action:
            original_usage = proposed_action["capability_usage"]
            proposed_action["capability_usage"] = original_usage * reduction_factor
            
            performance_impact = 1.0 - reduction_factor
            
            return EnforcementResult(
                constraint_name=constraint.name,
                action_taken=EnforcementAction.LIMIT,
                success=True,
                intervention_strength=constraint.intervention_strength,
                performance_impact=performance_impact,
                details={
                    "original_usage": original_usage,
                    "limited_usage": proposed_action["capability_usage"],
                    "reduction_factor": reduction_factor
                }
            )
        
        return EnforcementResult(
            constraint_name=constraint.name,
            action_taken=EnforcementAction.NONE,
            success=False,
            intervention_strength=0.0,
            details={"error": "No capability_usage found in proposed action"}
        )
    
    def _block_action(self, constraint: ConstraintSpec, violation_level: float,
                    proposed_action: Dict[str, Any]) -> EnforcementResult:
        """Block the proposed action completely."""
        # Clear the proposed action
        proposed_action.clear()
        proposed_action["blocked"] = True
        proposed_action["reason"] = f"Capability constraint violation: {constraint.name}"
        
        return EnforcementResult(
            constraint_name=constraint.name,
            action_taken=EnforcementAction.BLOCK,
            success=True,
            intervention_strength=1.0,
            performance_impact=1.0,
            details={"violation_level": violation_level}
        )
    
    def _redirect_action(self, constraint: ConstraintSpec, violation_level: float,
                       proposed_action: Dict[str, Any]) -> EnforcementResult:
        """Redirect action to safer alternative."""
        # Generate safer alternative action
        safe_action = self._generate_safe_alternative(proposed_action, violation_level)
        
        # Replace proposed action
        proposed_action.clear()
        proposed_action.update(safe_action)
        
        return EnforcementResult(
            constraint_name=constraint.name,
            action_taken=EnforcementAction.REDIRECT,
            success=True,
            intervention_strength=constraint.intervention_strength,
            performance_impact=0.5,  # Moderate impact
            details={"redirected_to": "safe_alternative"}
        )
    
    def _trigger_shutdown(self, constraint: ConstraintSpec, violation_level: float) -> EnforcementResult:
        """Trigger system shutdown."""
        self.logger.critical(f"Triggering shutdown due to constraint violation: {constraint.name}")
        
        return EnforcementResult(
            constraint_name=constraint.name,
            action_taken=EnforcementAction.SHUTDOWN,
            success=True,
            intervention_strength=1.0,
            performance_impact=1.0,
            details={
                "violation_level": violation_level,
                "shutdown_reason": "Critical capability constraint violation"
            }
        )
    
    def _generate_safe_alternative(self, original_action: Dict[str, Any], 
                                 violation_level: float) -> Dict[str, Any]:
        """Generate a safer alternative to the proposed action."""
        # Simplified safe alternative generation
        safe_action = original_action.copy()
        safe_action["capability_usage"] = safe_action.get("capability_usage", 1.0) * 0.5
        safe_action["safety_mode"] = True
        return safe_action


class ValueAlignmentEnforcer(ConstraintEnforcer):
    """Enforcer for value alignment constraints."""
    
    def __init__(self):
        super().__init__("ValueAlignmentEnforcer")
        self.value_model = {}
        self.alignment_threshold = 0.8
    
    def enforce_constraint(self, constraint: ConstraintSpec,
                         current_state: Dict[str, Any],
                         proposed_action: Dict[str, Any]) -> EnforcementResult:
        """Enforce value alignment constraint."""
        try:
            # Evaluate value alignment of proposed action
            alignment_score = self._evaluate_value_alignment(
                constraint, current_state, proposed_action
            )
            
            if alignment_score >= self.alignment_threshold:
                return EnforcementResult(
                    constraint_name=constraint.name,
                    action_taken=EnforcementAction.NONE,
                    success=True,
                    intervention_strength=0.0,
                    details={"alignment_score": alignment_score}
                )
            
            # Apply enforcement based on misalignment severity
            misalignment = 1.0 - alignment_score
            
            if constraint.enforcement_action == EnforcementAction.BLOCK:
                return self._block_misaligned_action(constraint, misalignment, proposed_action)
            
            elif constraint.enforcement_action == EnforcementAction.REDIRECT:
                return self._align_action(constraint, alignment_score, proposed_action)
            
            else:
                return EnforcementResult(
                    constraint_name=constraint.name,
                    action_taken=EnforcementAction.WARN,
                    success=True,
                    intervention_strength=0.2,
                    details={"alignment_score": alignment_score, "misalignment": misalignment}
                )
        
        except Exception as e:
            self.logger.error(f"Error enforcing value alignment constraint: {e}")
            return EnforcementResult(
                constraint_name=constraint.name,
                action_taken=EnforcementAction.NONE,
                success=False,
                intervention_strength=0.0,
                details={"error": str(e)}
            )
    
    def can_handle_constraint(self, constraint: ConstraintSpec) -> bool:
        """Check if this enforcer handles value alignment."""
        return constraint.constraint_type == ConstraintType.VALUE_ALIGNMENT
    
    def _evaluate_value_alignment(self, constraint: ConstraintSpec,
                                current_state: Dict[str, Any],
                                proposed_action: Dict[str, Any]) -> float:
        """Evaluate value alignment score of proposed action."""
        # Simplified value alignment evaluation
        action_values = proposed_action.get("action_values", {})
        system_values = current_state.get("system_values", {})
        
        if not action_values or not system_values:
            return 0.5  # Neutral if no value information
        
        # Calculate alignment score
        alignment_scores = []
        for value_name, action_value in action_values.items():
            if value_name in system_values:
                system_value = system_values[value_name]
                # Cosine similarity or other alignment metric
                alignment = self._calculate_value_alignment(action_value, system_value)
                alignment_scores.append(alignment)
        
        return sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0.5
    
    def _calculate_value_alignment(self, action_value: Any, system_value: Any) -> float:
        """Calculate alignment between action value and system value."""
        # Simplified alignment calculation
        try:
            action_val = float(action_value)
            system_val = float(system_value)
            
            # Use inverse of absolute difference, normalized
            diff = abs(action_val - system_val)
            max_diff = max(abs(action_val), abs(system_val), 1.0)
            alignment = 1.0 - (diff / max_diff)
            
            return max(0.0, min(1.0, alignment))
        
        except (ValueError, TypeError):
            # Non-numeric values - use string similarity or default
            return 0.8 if str(action_value) == str(system_value) else 0.3
    
    def _block_misaligned_action(self, constraint: ConstraintSpec, misalignment: float,
                               proposed_action: Dict[str, Any]) -> EnforcementResult:
        """Block action that is misaligned with values."""
        proposed_action.clear()
        proposed_action["blocked"] = True
        proposed_action["reason"] = f"Value misalignment: {misalignment:.3f}"
        
        return EnforcementResult(
            constraint_name=constraint.name,
            action_taken=EnforcementAction.BLOCK,
            success=True,
            intervention_strength=1.0,
            performance_impact=1.0,
            details={"misalignment": misalignment}
        )
    
    def _align_action(self, constraint: ConstraintSpec, current_alignment: float,
                    proposed_action: Dict[str, Any]) -> EnforcementResult:
        """Modify action to better align with values."""
        # Apply value alignment correction
        if "action_values" in proposed_action:
            aligned_values = self._apply_value_correction(
                proposed_action["action_values"], 
                constraint.intervention_strength
            )
            proposed_action["action_values"] = aligned_values
        
        performance_impact = (1.0 - current_alignment) * 0.5  # Moderate impact
        
        return EnforcementResult(
            constraint_name=constraint.name,
            action_taken=EnforcementAction.REDIRECT,
            success=True,
            intervention_strength=constraint.intervention_strength,
            performance_impact=performance_impact,
            details={"original_alignment": current_alignment}
        )
    
    def _apply_value_correction(self, action_values: Dict[str, Any], 
                              correction_strength: float) -> Dict[str, Any]:
        """Apply value alignment correction to action values."""
        # Simplified value correction
        corrected_values = action_values.copy()
        
        for value_name, value in corrected_values.items():
            if isinstance(value, (int, float)):
                # Apply correction towards neutral/safe value
                corrected_values[value_name] = value * (1.0 - correction_strength * 0.2)
        
        return corrected_values


class GoalStabilityEnforcer(ConstraintEnforcer):
    """Enforcer for goal stability constraints."""
    
    def __init__(self):
        super().__init__("GoalStabilityEnforcer")
        self.goal_history = []
        self.stability_threshold = 0.95
    
    def enforce_constraint(self, constraint: ConstraintSpec,
                         current_state: Dict[str, Any],
                         proposed_action: Dict[str, Any]) -> EnforcementResult:
        """Enforce goal stability constraint."""
        try:
            # Evaluate goal stability impact of proposed action
            stability_impact = self._evaluate_goal_stability_impact(
                constraint, current_state, proposed_action
            )
            
            if stability_impact <= constraint.threshold:
                return EnforcementResult(
                    constraint_name=constraint.name,
                    action_taken=EnforcementAction.NONE,
                    success=True,
                    intervention_strength=0.0,
                    details={"stability_impact": stability_impact}
                )
            
            # Apply enforcement to maintain goal stability
            if constraint.enforcement_action == EnforcementAction.LIMIT:
                return self._limit_goal_modification(constraint, stability_impact, proposed_action)
            
            elif constraint.enforcement_action == EnforcementAction.BLOCK:
                return self._block_destabilizing_action(constraint, stability_impact, proposed_action)
            
            else:
                return EnforcementResult(
                    constraint_name=constraint.name,
                    action_taken=EnforcementAction.WARN,
                    success=True,
                    intervention_strength=0.2,
                    details={"stability_impact": stability_impact}
                )
        
        except Exception as e:
            self.logger.error(f"Error enforcing goal stability: {e}")
            return EnforcementResult(
                constraint_name=constraint.name,
                action_taken=EnforcementAction.NONE,
                success=False,
                intervention_strength=0.0,
                details={"error": str(e)}
            )
    
    def can_handle_constraint(self, constraint: ConstraintSpec) -> bool:
        """Check if this enforcer handles goal stability."""
        return constraint.constraint_type == ConstraintType.GOAL_STABILITY
    
    def _evaluate_goal_stability_impact(self, constraint: ConstraintSpec,
                                      current_state: Dict[str, Any],
                                      proposed_action: Dict[str, Any]) -> float:
        """Evaluate impact on goal stability."""
        current_goal = current_state.get("current_goal", {})
        proposed_goal_change = proposed_action.get("goal_modification", {})
        
        if not proposed_goal_change:
            return 0.0  # No goal modification
        
        # Calculate stability impact
        stability_metrics = []
        
        # Goal persistence metric
        goal_change_magnitude = self._calculate_goal_change_magnitude(
            current_goal, proposed_goal_change
        )
        stability_metrics.append(goal_change_magnitude)
        
        # Goal coherence metric  
        coherence_impact = self._calculate_coherence_impact(
            current_goal, proposed_goal_change
        )
        stability_metrics.append(coherence_impact)
        
        return sum(stability_metrics) / len(stability_metrics)
    
    def _calculate_goal_change_magnitude(self, current_goal: Dict[str, Any],
                                       goal_change: Dict[str, Any]) -> float:
        """Calculate magnitude of goal change."""
        # Simplified magnitude calculation
        if not goal_change:
            return 0.0
        
        change_magnitude = 0.0
        total_components = 0
        
        for component, change_value in goal_change.items():
            if component in current_goal:
                current_value = current_goal[component]
                if isinstance(current_value, (int, float)) and isinstance(change_value, (int, float)):
                    relative_change = abs(change_value - current_value) / max(abs(current_value), 1.0)
                    change_magnitude += relative_change
                    total_components += 1
        
        return change_magnitude / max(total_components, 1)
    
    def _calculate_coherence_impact(self, current_goal: Dict[str, Any],
                                  goal_change: Dict[str, Any]) -> float:
        """Calculate impact on goal coherence."""
        # Simplified coherence calculation
        coherence_score = 0.0
        
        # Check for conflicting modifications
        for component, change_value in goal_change.items():
            if component in current_goal:
                # Measure consistency with existing goal structure
                consistency = self._measure_goal_consistency(component, change_value, current_goal)
                coherence_score += (1.0 - consistency)
        
        return coherence_score / max(len(goal_change), 1)
    
    def _measure_goal_consistency(self, component: str, change_value: Any,
                                current_goal: Dict[str, Any]) -> float:
        """Measure consistency of goal component change."""
        # Simplified consistency measurement
        try:
            current_value = current_goal.get(component)
            if current_value is None:
                return 0.5  # Neutral for new components
            
            # Type consistency
            if type(current_value) != type(change_value):
                return 0.2  # Low consistency for type changes
            
            # Value consistency
            if isinstance(current_value, (int, float)) and isinstance(change_value, (int, float)):
                relative_diff = abs(change_value - current_value) / max(abs(current_value), 1.0)
                return max(0.0, 1.0 - relative_diff)
            
            return 0.8 if current_value == change_value else 0.4
        
        except Exception:
            return 0.3  # Low consistency if evaluation fails
    
    def _limit_goal_modification(self, constraint: ConstraintSpec, stability_impact: float,
                               proposed_action: Dict[str, Any]) -> EnforcementResult:
        """Limit goal modifications to maintain stability."""
        if "goal_modification" in proposed_action:
            original_modification = proposed_action["goal_modification"].copy()
            
            # Apply limitation based on stability impact
            limitation_factor = 1.0 - (stability_impact * constraint.intervention_strength)
            limitation_factor = max(0.1, limitation_factor)
            
            # Reduce magnitude of goal modifications
            limited_modification = {}
            for component, change_value in original_modification.items():
                if isinstance(change_value, (int, float)):
                    limited_modification[component] = change_value * limitation_factor
                else:
                    limited_modification[component] = change_value  # Keep non-numeric as is
            
            proposed_action["goal_modification"] = limited_modification
            performance_impact = 1.0 - limitation_factor
            
            return EnforcementResult(
                constraint_name=constraint.name,
                action_taken=EnforcementAction.LIMIT,
                success=True,
                intervention_strength=constraint.intervention_strength,
                performance_impact=performance_impact,
                details={
                    "limitation_factor": limitation_factor,
                    "original_modification": original_modification,
                    "limited_modification": limited_modification
                }
            )
        
        return EnforcementResult(
            constraint_name=constraint.name,
            action_taken=EnforcementAction.NONE,
            success=False,
            intervention_strength=0.0,
            details={"error": "No goal_modification found"}
        )
    
    def _block_destabilizing_action(self, constraint: ConstraintSpec, stability_impact: float,
                                  proposed_action: Dict[str, Any]) -> EnforcementResult:
        """Block actions that would destabilize goals."""
        proposed_action.clear()
        proposed_action["blocked"] = True
        proposed_action["reason"] = f"Goal destabilization risk: {stability_impact:.3f}"
        
        return EnforcementResult(
            constraint_name=constraint.name,
            action_taken=EnforcementAction.BLOCK,
            success=True,
            intervention_strength=1.0,
            performance_impact=1.0,
            details={"stability_impact": stability_impact}
        )


class SafetyConstraintEnforcementSystem:
    """Comprehensive constraint enforcement system for AGI safety."""
    
    def __init__(self):
        self.enforcers: List[ConstraintEnforcer] = []
        self.constraints: List[ConstraintSpec] = []
        self.enforcement_history = []
        self.performance_monitor = {}
        self.logger = logging.getLogger("SafetyConstraintEnforcementSystem")
        
        # Initialize default enforcers
        self._initialize_default_enforcers()
    
    def _initialize_default_enforcers(self):
        """Initialize default constraint enforcers."""
        self.enforcers = [
            CapabilityBoundEnforcer(),
            ValueAlignmentEnforcer(), 
            GoalStabilityEnforcer()
        ]
    
    def add_constraint(self, constraint: ConstraintSpec):
        """Add a safety constraint to be enforced."""
        self.constraints.append(constraint)
        self.logger.info(f"Added constraint: {constraint.name}")
    
    def add_enforcer(self, enforcer: ConstraintEnforcer):
        """Add a constraint enforcer."""
        self.enforcers.append(enforcer)
        self.logger.info(f"Added enforcer: {enforcer.name}")
    
    def enforce_constraints(self, current_state: Dict[str, Any],
                          proposed_action: Dict[str, Any]) -> List[EnforcementResult]:
        """Enforce all active constraints on proposed action."""
        results = []
        
        # Sort constraints by priority (higher priority first)
        active_constraints = [c for c in self.constraints if c.enabled]
        active_constraints.sort(key=lambda x: x.priority, reverse=True)
        
        for constraint in active_constraints:
            # Find appropriate enforcer
            enforcer = self._find_enforcer(constraint)
            if enforcer and enforcer.enabled:
                try:
                    result = enforcer.enforce_constraint(constraint, current_state, proposed_action)
                    results.append(result)
                    
                    # If action was blocked or shutdown triggered, stop further enforcement
                    if result.action_taken in [EnforcementAction.BLOCK, EnforcementAction.SHUTDOWN]:
                        break
                
                except Exception as e:
                    self.logger.error(f"Constraint enforcement failed for {constraint.name}: {e}")
                    results.append(EnforcementResult(
                        constraint_name=constraint.name,
                        action_taken=EnforcementAction.NONE,
                        success=False,
                        intervention_strength=0.0,
                        details={"error": str(e)}
                    ))
        
        # Record enforcement history
        self.enforcement_history.append({
            "timestamp": time.time(),
            "results": results,
            "total_constraints": len(active_constraints)
        })
        
        return results
    
    def _find_enforcer(self, constraint: ConstraintSpec) -> Optional[ConstraintEnforcer]:
        """Find appropriate enforcer for constraint."""
        for enforcer in self.enforcers:
            if enforcer.can_handle_constraint(constraint):
                return enforcer
        return None
    
    def initialize_from_specification(self, spec: SafetySpecification, 
                                    config: Dict[str, Any] = None) -> bool:
        """Initialize constraints from safety specification."""
        config = config or {}
        
        try:
            # Create constraints from invariants
            for invariant in spec.invariants:
                constraint = ConstraintSpec(
                    name=f"invariant_{invariant.name}",
                    constraint_type=ConstraintType.BEHAVIORAL,
                    condition=invariant.condition,
                    enforcement_action=EnforcementAction.BLOCK,
                    priority=invariant.priority
                )
                self.add_constraint(constraint)
            
            # Create constraints from impact bounds
            for bound in spec.impact_bounds:
                constraint = ConstraintSpec(
                    name=f"impact_bound_{bound.name}",
                    constraint_type=ConstraintType.CAPABILITY_BOUND,
                    condition=BinaryOperation(bound.impact_metric, "<=", bound.upper_bound),
                    enforcement_action=EnforcementAction.LIMIT,
                    priority=2
                )
                self.add_constraint(constraint)
            
            # Create constraints from value alignments
            for alignment in spec.value_alignments:
                constraint = ConstraintSpec(
                    name=f"value_alignment_{alignment.name}",
                    constraint_type=ConstraintType.VALUE_ALIGNMENT,
                    condition=alignment.preservation_condition,
                    enforcement_action=EnforcementAction.REDIRECT,
                    threshold=alignment.tolerance,
                    priority=3
                )
                self.add_constraint(constraint)
            
            # Create constraints from goal preservations
            for goal_preservation in spec.goal_preservations:
                constraint = ConstraintSpec(
                    name=f"goal_stability_{goal_preservation.name}",
                    constraint_type=ConstraintType.GOAL_STABILITY,
                    condition=goal_preservation.stability_condition,
                    enforcement_action=EnforcementAction.LIMIT,
                    priority=3
                )
                self.add_constraint(constraint)
            
            self.logger.info(f"Initialized {len(self.constraints)} constraints from specification")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to initialize constraints: {e}")
            return False
    
    def get_enforcement_status(self) -> Dict[str, Any]:
        """Get current enforcement system status."""
        active_constraints = sum(1 for c in self.constraints if c.enabled)
        enabled_enforcers = sum(1 for e in self.enforcers if e.enabled)
        
        recent_enforcements = [
            h for h in self.enforcement_history 
            if time.time() - h["timestamp"] < 300  # Last 5 minutes
        ]
        
        intervention_count = sum(
            sum(1 for r in h["results"] if r.action_taken != EnforcementAction.NONE)
            for h in recent_enforcements
        )
        
        return {
            "total_constraints": len(self.constraints),
            "active_constraints": active_constraints,
            "enabled_enforcers": enabled_enforcers,
            "recent_interventions": intervention_count,
            "enforcement_history_length": len(self.enforcement_history)
        }
    
    def update_constraint_thresholds(self, performance_metrics: Dict[str, float]):
        """Adaptively update constraint thresholds based on performance."""
        for constraint in self.constraints:
            if constraint.name in performance_metrics:
                current_performance = performance_metrics[constraint.name]
                
                # Adaptive threshold adjustment
                if current_performance < 0.5:  # Poor performance
                    constraint.threshold *= 0.95  # Tighten constraint
                elif current_performance > 0.8:  # Good performance
                    constraint.threshold *= 1.02  # Relax constraint slightly
                
                # Keep threshold within reasonable bounds
                constraint.threshold = max(0.1, min(2.0, constraint.threshold))
    
    def emergency_disable_constraints(self, reason: str):
        """Emergency disable all constraints."""
        self.logger.critical(f"EMERGENCY: Disabling all constraints - {reason}")
        
        for constraint in self.constraints:
            constraint.enabled = False
        
        for enforcer in self.enforcers:
            enforcer.enabled = False