"""
Universe Lock

System for creating deterministic probability locks that enforce
specific outcomes and prevent random variation in critical events.
"""

import numpy as np
import logging
import math
import time
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import threading


class LockType(Enum):
    """Types of deterministic locks."""
    ABSOLUTE = "absolute"           # 100% certainty
    CONSTRAINED = "constrained"     # Within bounds
    TRENDING = "trending"           # Force trend direction
    OSCILLATING = "oscillating"     # Stable oscillation
    ASYMPTOTIC = "asymptotic"       # Approach limit
    CONDITIONAL = "conditional"     # Based on conditions


@dataclass
class ProbabilityLock:
    """Represents a deterministic probability lock."""
    lock_id: str
    lock_type: LockType
    target_probability: float
    tolerance: float
    strength: float
    duration: float
    conditions: Dict[str, Any]
    affected_fields: Set[str] = field(default_factory=set)
    creation_time: float = field(default_factory=time.time)
    expiration_time: float = 0.0
    enforcement_count: int = 0
    violations: List[Dict[str, Any]] = field(default_factory=list)


class UniverseLock:
    """
    Deterministic universe lock system.
    
    Creates and maintains probability locks that enforce deterministic
    outcomes by constraining probability fields within specific bounds
    or forcing them to specific values.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Core state
        self.probability_locks: Dict[str, ProbabilityLock] = {}
        self.active_locks: Set[str] = set()
        
        # Threading
        self.lock_lock = threading.RLock()
        
        # System parameters
        self.max_locks = 100
        self.enforcement_frequency = 10.0  # Hz
        self.violation_threshold = 0.01
        self.max_lock_strength = 1.0
        
        # Start enforcement thread
        self._start_lock_enforcement()
        
        self.logger.info("UniverseLock initialized")
    
    def create_probability_lock(
        self,
        target_probability: float,
        lock_type: LockType = LockType.ABSOLUTE,
        tolerance: float = 0.01,
        strength: float = 1.0,
        duration: float = 3600.0,
        conditions: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new probability lock."""
        with self.lock_lock:
            if len(self.probability_locks) >= self.max_locks:
                raise ValueError("Maximum number of probability locks reached")
            
            lock_id = f"lock_{lock_type.value}_{int(time.time() * 1000000)}"
            
            # Validate parameters
            target_probability = max(0.0, min(1.0, target_probability))
            tolerance = max(0.0, min(0.5, tolerance))
            strength = max(0.0, min(self.max_lock_strength, strength))
            
            lock = ProbabilityLock(
                lock_id=lock_id,
                lock_type=lock_type,
                target_probability=target_probability,
                tolerance=tolerance,
                strength=strength,
                duration=duration,
                conditions=conditions or {},
                expiration_time=time.time() + duration
            )
            
            self.probability_locks[lock_id] = lock
            self.active_locks.add(lock_id)
            
            self.logger.info(f"Created {lock_type.value} probability lock {lock_id}")
            return lock_id
    
    def apply_lock_to_field(self, lock_id: str, field_id: str) -> bool:
        """Apply a probability lock to a specific field."""
        if lock_id not in self.probability_locks:
            return False
        
        lock = self.probability_locks[lock_id]
        lock.affected_fields.add(field_id)
        
        self.logger.info(f"Applied lock {lock_id} to field {field_id}")
        return True
    
    def enforce_locks(self) -> Dict[str, Any]:
        """Enforce all active probability locks."""
        with self.lock_lock:
            enforcement_results = {
                'enforced_locks': 0,
                'violations_detected': 0,
                'violations_corrected': 0,
                'expired_locks': 0
            }
            
            current_time = time.time()
            expired_locks = []
            
            for lock_id in list(self.active_locks):
                lock = self.probability_locks[lock_id]
                
                # Check expiration
                if current_time > lock.expiration_time:
                    expired_locks.append(lock_id)
                    continue
                
                # Enforce lock
                enforcement_result = self._enforce_single_lock(lock)
                
                if enforcement_result['enforced']:
                    enforcement_results['enforced_locks'] += 1
                
                if enforcement_result['violation_detected']:
                    enforcement_results['violations_detected'] += 1
                
                if enforcement_result['violation_corrected']:
                    enforcement_results['violations_corrected'] += 1
            
            # Remove expired locks
            for lock_id in expired_locks:
                self.active_locks.discard(lock_id)
                enforcement_results['expired_locks'] += 1
                self.logger.debug(f"Expired probability lock {lock_id}")
            
            return enforcement_results
    
    def _enforce_single_lock(self, lock: ProbabilityLock) -> Dict[str, Any]:
        """Enforce a single probability lock."""
        result = {
            'enforced': False,
            'violation_detected': False,
            'violation_corrected': False
        }
        
        # Check conditions if any
        if not self._check_lock_conditions(lock):
            return result
        
        # For each affected field, enforce the lock
        for field_id in lock.affected_fields:
            field_probability = self._get_field_probability(field_id)
            
            if field_probability is None:
                continue
            
            # Check for violation
            if self._is_lock_violated(lock, field_probability):
                result['violation_detected'] = True
                
                # Record violation
                violation = {
                    'timestamp': time.time(),
                    'field_id': field_id,
                    'expected_probability': lock.target_probability,
                    'actual_probability': field_probability,
                    'deviation': abs(field_probability - lock.target_probability)
                }
                lock.violations.append(violation)
                
                # Correct violation
                corrected_probability = self._calculate_corrected_probability(lock, field_probability)
                
                if self._set_field_probability(field_id, corrected_probability):
                    result['violation_corrected'] = True
                    lock.enforcement_count += 1
        
        result['enforced'] = len(lock.affected_fields) > 0
        return result
    
    def _check_lock_conditions(self, lock: ProbabilityLock) -> bool:
        """Check if lock conditions are satisfied."""
        if not lock.conditions:
            return True
        
        # Implement condition checking based on lock conditions
        # This is a simplified implementation
        for condition_key, condition_value in lock.conditions.items():
            if condition_key == 'time_window':
                start_time, end_time = condition_value
                current_time = time.time()
                if not (start_time <= current_time <= end_time):
                    return False
            
            elif condition_key == 'probability_threshold':
                # Check if some other probability meets threshold
                threshold_field, threshold_value = condition_value
                field_prob = self._get_field_probability(threshold_field)
                if field_prob is None or field_prob < threshold_value:
                    return False
        
        return True
    
    def _is_lock_violated(self, lock: ProbabilityLock, current_probability: float) -> bool:
        """Check if a lock is violated by current probability."""
        if lock.lock_type == LockType.ABSOLUTE:
            return abs(current_probability - lock.target_probability) > lock.tolerance
        
        elif lock.lock_type == LockType.CONSTRAINED:
            lower_bound = lock.target_probability - lock.tolerance
            upper_bound = lock.target_probability + lock.tolerance
            return not (lower_bound <= current_probability <= upper_bound)
        
        elif lock.lock_type == LockType.TRENDING:
            # Check if probability is moving in wrong direction
            # This would require historical data in a real implementation
            return False  # Simplified
        
        elif lock.lock_type == LockType.OSCILLATING:
            # Check if probability is within oscillation bounds
            oscillation_amplitude = lock.tolerance
            expected_range = (lock.target_probability - oscillation_amplitude,
                            lock.target_probability + oscillation_amplitude)
            return not (expected_range[0] <= current_probability <= expected_range[1])
        
        elif lock.lock_type == LockType.ASYMPTOTIC:
            # Check if probability is approaching target
            distance = abs(current_probability - lock.target_probability)
            return distance > lock.tolerance
        
        elif lock.lock_type == LockType.CONDITIONAL:
            # Conditional locks are only enforced when conditions are met
            return abs(current_probability - lock.target_probability) > lock.tolerance
        
        return False
    
    def _calculate_corrected_probability(
        self,
        lock: ProbabilityLock,
        current_probability: float
    ) -> float:
        """Calculate corrected probability to enforce lock."""
        if lock.lock_type == LockType.ABSOLUTE:
            # Force to exact target
            return lock.target_probability
        
        elif lock.lock_type == LockType.CONSTRAINED:
            # Move towards target within bounds
            if current_probability < lock.target_probability - lock.tolerance:
                return lock.target_probability - lock.tolerance
            elif current_probability > lock.target_probability + lock.tolerance:
                return lock.target_probability + lock.tolerance
            else:
                return current_probability
        
        elif lock.lock_type == LockType.TRENDING:
            # Apply gradual correction towards target
            correction_factor = lock.strength * 0.1
            delta = lock.target_probability - current_probability
            return current_probability + delta * correction_factor
        
        elif lock.lock_type == LockType.OSCILLATING:
            # Create oscillating pattern around target
            time_factor = time.time() * 2 * math.pi * 0.1  # 0.1 Hz oscillation
            oscillation = lock.tolerance * math.sin(time_factor)
            return lock.target_probability + oscillation
        
        elif lock.lock_type == LockType.ASYMPTOTIC:
            # Move gradually towards target
            correction_factor = lock.strength * 0.05
            delta = lock.target_probability - current_probability
            return current_probability + delta * correction_factor
        
        else:  # CONDITIONAL
            # Apply strong correction when conditions are met
            correction_factor = lock.strength * 0.2
            delta = lock.target_probability - current_probability
            return current_probability + delta * correction_factor
    
    def _get_field_probability(self, field_id: str) -> Optional[float]:
        """Get current probability of a field."""
        # This would interface with the actual probability field system
        # For now, return a placeholder
        return 0.5  # Placeholder
    
    def _set_field_probability(self, field_id: str, probability: float) -> bool:
        """Set probability of a field."""
        # This would interface with the actual probability field system
        # For now, return success
        return True  # Placeholder
    
    def _start_lock_enforcement(self) -> None:
        """Start the lock enforcement thread."""
        def enforcement_loop():
            while True:
                try:
                    self.enforce_locks()
                    time.sleep(1.0 / self.enforcement_frequency)
                except Exception as e:
                    self.logger.error(f"Lock enforcement error: {e}")
                    time.sleep(1.0)
        
        enforcement_thread = threading.Thread(target=enforcement_loop, daemon=True)
        enforcement_thread.start()
        
        self.logger.info("Started lock enforcement thread")
    
    def get_lock_status(self, lock_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a probability lock."""
        if lock_id not in self.probability_locks:
            return None
        
        lock = self.probability_locks[lock_id]
        
        # Calculate efficiency
        total_violations = len(lock.violations)
        efficiency = 1.0 - (total_violations / max(1, lock.enforcement_count + total_violations))
        
        return {
            'lock_id': lock_id,
            'lock_type': lock.lock_type.value,
            'target_probability': lock.target_probability,
            'tolerance': lock.tolerance,
            'strength': lock.strength,
            'affected_fields': list(lock.affected_fields),
            'enforcement_count': lock.enforcement_count,
            'violation_count': total_violations,
            'efficiency': efficiency,
            'is_active': lock_id in self.active_locks,
            'time_remaining': max(0, lock.expiration_time - time.time()),
            'age': time.time() - lock.creation_time
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        total_locks = len(self.probability_locks)
        active_locks = len(self.active_locks)
        
        # Calculate statistics
        total_enforcements = sum(lock.enforcement_count for lock in self.probability_locks.values())
        total_violations = sum(len(lock.violations) for lock in self.probability_locks.values())
        
        # Lock type distribution
        lock_type_counts = {}
        for lock in self.probability_locks.values():
            lock_type = lock.lock_type.value
            lock_type_counts[lock_type] = lock_type_counts.get(lock_type, 0) + 1
        
        # System efficiency
        system_efficiency = 1.0 - (total_violations / max(1, total_enforcements + total_violations))
        
        return {
            'total_locks': total_locks,
            'active_locks': active_locks,
            'total_enforcements': total_enforcements,
            'total_violations': total_violations,
            'system_efficiency': system_efficiency,
            'lock_type_distribution': lock_type_counts,
            'enforcement_frequency': self.enforcement_frequency,
            'max_locks': self.max_locks,
            'violation_threshold': self.violation_threshold
        }