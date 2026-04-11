"""
Energy Efficiency Metrics

Comprehensive energy efficiency measurement and optimization system
for bio-inspired cognitive architectures, modeled after biological
neural network energy consumption patterns.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
import logging
from collections import deque

from ..core import BioCognitiveModule, BiologicalMetrics

logger = logging.getLogger(__name__)

class EnergyType(Enum):
    """Types of energy consumption"""
    COMPUTATIONAL = "computational"
    COMMUNICATION = "communication"
    MAINTENANCE = "maintenance"
    PLASTICITY = "plasticity"
    MEMORY = "memory"

@dataclass
class MetabolicCost:
    """Represents metabolic cost of neural operations"""
    spike_cost: float = 0.001  # Energy per spike (normalized)
    synapse_maintenance: float = 0.0001  # Energy per synapse per time unit
    neuron_maintenance: float = 0.0005  # Energy per neuron per time unit
    plasticity_cost: float = 0.01  # Energy per synaptic weight change
    memory_cost: float = 0.0002  # Energy per memory operation
    
    def total_cost(self, num_spikes: int, num_synapses: int, num_neurons: int,
                   plasticity_events: int, memory_operations: int, dt: float) -> float:
        """Calculate total metabolic cost"""
        return (
            self.spike_cost * num_spikes +
            self.synapse_maintenance * num_synapses * dt +
            self.neuron_maintenance * num_neurons * dt +
            self.plasticity_cost * plasticity_events +
            self.memory_cost * memory_operations
        )

class EnergyCalculator:
    """
    Biological neural network energy calculator
    
    Models energy consumption based on biological neural networks:
    - Human brain: ~20W (20% of body's energy)
    - ~86 billion neurons, ~100 trillion synapses
    - Energy per spike: ~10^-14 to 10^-12 joules
    """
    
    def __init__(self):
        # Biological reference values (human brain)
        self.brain_power = 20.0  # Watts
        self.num_neurons_brain = 86e9  # neurons
        self.num_synapses_brain = 100e12  # synapses
        self.spikes_per_second_brain = 86e9 * 5  # ~5 Hz average firing rate
        
        # Energy per operation (joules)
        self.energy_per_spike = 1e-13  # 0.1 picojoules
        self.energy_per_synapse_per_second = 2e-16  # 0.0002 picojoules
        self.energy_per_neuron_per_second = 2.3e-13  # 0.23 picojoules
        
        # Metabolic costs
        self.metabolic_costs = MetabolicCost()
        
        # Efficiency benchmarks
        self.biological_efficiency = self._calculate_biological_efficiency()
        
    def _calculate_biological_efficiency(self) -> Dict[str, float]:
        """Calculate biological efficiency benchmarks"""
        # Operations per joule
        spikes_per_joule = 1.0 / self.energy_per_spike
        synapses_per_joule_per_second = 1.0 / self.energy_per_synapse_per_second
        
        # Information processing capacity
        brain_ops_per_second = self.spikes_per_second_brain
        brain_ops_per_joule = brain_ops_per_second / self.brain_power
        
        return {
            'spikes_per_joule': spikes_per_joule,
            'synapses_per_joule_per_second': synapses_per_joule_per_second,
            'brain_ops_per_joule': brain_ops_per_joule,
            'energy_density': self.brain_power / 1400,  # W/kg (brain weight ~1.4kg)
            'computational_density': brain_ops_per_second / 1400  # ops/s/kg
        }
    
    def calculate_spike_energy(self, num_spikes: int) -> float:
        """Calculate energy for spike generation"""
        return num_spikes * self.energy_per_spike
    
    def calculate_synaptic_energy(self, num_synapses: int, dt: float) -> float:
        """Calculate energy for synaptic maintenance"""
        return num_synapses * self.energy_per_synapse_per_second * dt
    
    def calculate_neuronal_energy(self, num_neurons: int, dt: float) -> float:
        """Calculate energy for neuronal maintenance"""
        return num_neurons * self.energy_per_neuron_per_second * dt
    
    def calculate_plasticity_energy(self, weight_changes: int) -> float:
        """Calculate energy for synaptic plasticity"""
        # Plasticity is expensive - protein synthesis, etc.
        return weight_changes * self.energy_per_spike * 100
    
    def calculate_total_energy(self, 
                              num_spikes: int,
                              num_synapses: int, 
                              num_neurons: int,
                              plasticity_events: int,
                              dt: float) -> Dict[str, float]:
        """Calculate total energy consumption breakdown"""
        
        spike_energy = self.calculate_spike_energy(num_spikes)
        synaptic_energy = self.calculate_synaptic_energy(num_synapses, dt)
        neuronal_energy = self.calculate_neuronal_energy(num_neurons, dt)
        plasticity_energy = self.calculate_plasticity_energy(plasticity_events)
        
        total_energy = spike_energy + synaptic_energy + neuronal_energy + plasticity_energy
        
        return {
            'spike_energy': spike_energy,
            'synaptic_energy': synaptic_energy,
            'neuronal_energy': neuronal_energy,
            'plasticity_energy': plasticity_energy,
            'total_energy': total_energy,
            'power': total_energy / dt if dt > 0 else 0.0
        }
    
    def calculate_efficiency_ratio(self, system_energy: float, system_operations: int) -> float:
        """Calculate efficiency ratio compared to biological neural networks"""
        if system_operations == 0:
            return 0.0
        
        system_ops_per_joule = system_operations / (system_energy + 1e-12)
        biological_ops_per_joule = self.biological_efficiency['brain_ops_per_joule']
        
        return system_ops_per_joule / biological_ops_per_joule

class EnergyMetrics(BioCognitiveModule):
    """
    Energy Metrics and Monitoring System
    
    Tracks and optimizes energy consumption in bio-inspired cognitive architectures
    with comparison to biological neural network efficiency.
    """
    
    def __init__(self, name: str = "EnergyMetrics"):
        super().__init__(name)
        
        self.energy_calculator = EnergyCalculator()
        
        # Energy tracking
        self.energy_history = deque(maxlen=10000)
        self.power_history = deque(maxlen=1000)
        self.efficiency_history = deque(maxlen=1000)
        
        # Current measurements
        self.current_power = 0.0
        self.total_energy_consumed = 0.0
        self.efficiency_ratio = 0.0
        
        # Operation counters
        self.spike_count = 0
        self.plasticity_count = 0
        self.memory_operations = 0
        
        # System parameters
        self.num_neurons = 0
        self.num_synapses = 0
        
        # Optimization targets
        self.target_efficiency_ratio = 0.1  # 10% of biological efficiency (ambitious but realistic)
        self.max_power_budget = 1.0  # 1 Watt power budget
        
        # Thermal tracking
        self.temperature = 25.0  # Celsius
        self.thermal_resistance = 10.0  # K/W
        
        logger.info("Initialized energy metrics system")
    
    async def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process energy measurements and optimization"""
        
        # Extract system state
        num_spikes = inputs.get('num_spikes', 0)
        num_neurons = inputs.get('num_neurons', self.num_neurons)
        num_synapses = inputs.get('num_synapses', self.num_synapses)
        plasticity_events = inputs.get('plasticity_events', 0)
        memory_ops = inputs.get('memory_operations', 0)
        dt = inputs.get('dt', 0.001)  # 1ms default
        
        # Update system parameters
        self.num_neurons = num_neurons
        self.num_synapses = num_synapses
        
        # Update counters
        self.spike_count += num_spikes
        self.plasticity_count += plasticity_events
        self.memory_operations += memory_ops
        
        # Calculate energy consumption
        energy_breakdown = self.energy_calculator.calculate_total_energy(
            num_spikes, num_synapses, num_neurons, plasticity_events, dt
        )
        
        # Update tracking
        self.total_energy_consumed += energy_breakdown['total_energy']
        self.current_power = energy_breakdown['power']
        
        # Calculate efficiency
        total_operations = num_spikes + plasticity_events + memory_ops
        self.efficiency_ratio = self.energy_calculator.calculate_efficiency_ratio(
            energy_breakdown['total_energy'], total_operations
        )
        
        # Update histories
        self.energy_history.append({
            'timestamp': time.time(),
            'energy': energy_breakdown['total_energy'],
            'power': self.current_power,
            'efficiency': self.efficiency_ratio
        })
        
        self.power_history.append(self.current_power)
        self.efficiency_history.append(self.efficiency_ratio)
        
        # Update temperature
        self._update_temperature()
        
        # Generate optimization recommendations
        optimization_recommendations = self._generate_optimization_recommendations()
        
        # Prepare output
        output = {
            'energy_breakdown': energy_breakdown,
            'current_power': self.current_power,
            'total_energy': self.total_energy_consumed,
            'efficiency_ratio': self.efficiency_ratio,
            'biological_comparison': self._get_biological_comparison(),
            'thermal_state': {
                'temperature': self.temperature,
                'thermal_resistance': self.thermal_resistance
            },
            'optimization_recommendations': optimization_recommendations,
            'performance_metrics': self._calculate_performance_metrics(),
            'energy_budget_status': self._check_energy_budget()
        }
        
        return output
    
    def _update_temperature(self):
        """Update thermal state based on power consumption"""
        ambient_temp = 25.0  # Celsius
        temp_rise = self.current_power * self.thermal_resistance
        self.temperature = ambient_temp + temp_rise
    
    def _generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate energy optimization recommendations"""
        recommendations = []
        
        # Check efficiency ratio
        if self.efficiency_ratio < self.target_efficiency_ratio * 0.5:
            recommendations.append({
                'type': 'efficiency_improvement',
                'priority': 'high',
                'description': 'System efficiency significantly below biological benchmark',
                'actions': [
                    'reduce_unnecessary_spikes',
                    'optimize_network_topology',
                    'implement_sparse_coding'
                ]
            })
        
        # Check power budget
        if self.current_power > self.max_power_budget * 0.8:
            recommendations.append({
                'type': 'power_reduction',
                'priority': 'high',
                'description': 'Power consumption approaching budget limit',
                'actions': [
                    'reduce_firing_rates',
                    'implement_power_gating',
                    'optimize_synaptic_weights'
                ]
            })
        
        # Check thermal state
        if self.temperature > 60.0:  # Thermal limit
            recommendations.append({
                'type': 'thermal_management',
                'priority': 'critical',
                'description': 'Temperature exceeding safe operating limits',
                'actions': [
                    'reduce_computational_load',
                    'implement_thermal_throttling',
                    'improve_cooling'
                ]
            })
        
        # Check plasticity energy
        if len(self.energy_history) > 100:
            recent_energy = [e['energy'] for e in list(self.energy_history)[-100:]]
            plasticity_ratio = sum(recent_energy) / (self.plasticity_count + 1)
            
            if plasticity_ratio > 0.3:  # Plasticity using >30% of energy
                recommendations.append({
                    'type': 'plasticity_optimization',
                    'priority': 'medium',
                    'description': 'Plasticity consuming excessive energy',
                    'actions': [
                        'implement_homeostatic_plasticity',
                        'use_sparse_plasticity_updates',
                        'optimize_learning_schedules'
                    ]
                })
        
        return recommendations
    
    def _get_biological_comparison(self) -> Dict[str, float]:
        """Get comparison metrics to biological neural networks"""
        bio_efficiency = self.energy_calculator.biological_efficiency
        
        # Calculate relative metrics
        if self.num_neurons > 0:
            neurons_ratio = self.num_neurons / self.energy_calculator.num_neurons_brain
            synapses_ratio = self.num_synapses / self.energy_calculator.num_synapses_brain
            power_ratio = self.current_power / self.energy_calculator.brain_power
        else:
            neurons_ratio = synapses_ratio = power_ratio = 0.0
        
        return {
            'efficiency_ratio': self.efficiency_ratio,
            'neurons_ratio': neurons_ratio,
            'synapses_ratio': synapses_ratio,
            'power_ratio': power_ratio,
            'energy_density_ratio': (self.current_power / 1.0) / bio_efficiency['energy_density'],  # Assuming 1kg system
            'biological_benchmark_spikes_per_joule': bio_efficiency['spikes_per_joule'],
            'system_spikes_per_joule': self.spike_count / (self.total_energy_consumed + 1e-12)
        }
    
    def _calculate_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics"""
        if len(self.efficiency_history) < 2:
            return {'efficiency_trend': 0.0, 'power_stability': 1.0}
        
        # Efficiency trend
        recent_efficiency = list(self.efficiency_history)[-10:]
        if len(recent_efficiency) > 1:
            efficiency_trend = (recent_efficiency[-1] - recent_efficiency[0]) / len(recent_efficiency)
        else:
            efficiency_trend = 0.0
        
        # Power stability (inverse of coefficient of variation)
        recent_power = list(self.power_history)[-100:]
        if len(recent_power) > 1:
            power_cv = np.std(recent_power) / (np.mean(recent_power) + 1e-6)
            power_stability = 1.0 / (1.0 + power_cv)
        else:
            power_stability = 1.0
        
        # Energy efficiency score (0-1, where 1 is biological efficiency)
        efficiency_score = min(1.0, self.efficiency_ratio)
        
        return {
            'efficiency_trend': efficiency_trend,
            'power_stability': power_stability,
            'efficiency_score': efficiency_score,
            'thermal_efficiency': max(0.0, 1.0 - (self.temperature - 25.0) / 50.0)  # Penalty for heating
        }
    
    def _check_energy_budget(self) -> Dict[str, Any]:
        """Check energy budget status"""
        power_utilization = self.current_power / self.max_power_budget
        
        if power_utilization > 1.0:
            status = 'over_budget'
            severity = 'critical'
        elif power_utilization > 0.8:
            status = 'approaching_limit'
            severity = 'warning'
        elif power_utilization > 0.6:
            status = 'moderate_usage'
            severity = 'normal'
        else:
            status = 'low_usage'
            severity = 'good'
        
        return {
            'status': status,
            'severity': severity,
            'power_utilization': power_utilization,
            'remaining_budget': max(0.0, self.max_power_budget - self.current_power),
            'efficiency_target_met': self.efficiency_ratio >= self.target_efficiency_ratio
        }
    
    def get_biological_metrics(self) -> BiologicalMetrics:
        """Get biological metrics for energy system"""
        efficiency_score = min(1.0, self.efficiency_ratio)
        
        self.metrics = BiologicalMetrics(
            energy_efficiency=efficiency_score,
            plasticity_index=min(1.0, self.plasticity_count / 1000.0),  # Normalize
            neurotransmitter_levels={
                'atp': max(0.1, 1.0 - self.current_power / self.max_power_budget),  # Energy availability
                'lactate': min(1.0, self.current_power / self.max_power_budget),  # Metabolic byproduct
                'glucose': 0.7  # Baseline energy substrate
            }
        )
        
        return self.metrics
    
    def update_parameters(self, learning_signal: float):
        """Update energy parameters based on learning signal"""
        # Adjust efficiency targets based on performance
        if learning_signal > 0.8:
            # High performance - can afford slightly higher energy usage
            self.target_efficiency_ratio = min(1.0, self.target_efficiency_ratio * 1.01)
        elif learning_signal < 0.3:
            # Poor performance - need to be more energy efficient
            self.target_efficiency_ratio = max(0.01, self.target_efficiency_ratio * 0.99)
    
    def set_power_budget(self, budget: float):
        """Set power budget in watts"""
        self.max_power_budget = max(0.1, budget)
        logger.info(f"Set power budget to {budget}W")
    
    def get_energy_statistics(self) -> Dict[str, Any]:
        """Get comprehensive energy statistics"""
        if not self.energy_history:
            return {}
        
        energies = [e['energy'] for e in self.energy_history]
        powers = [e['power'] for e in self.energy_history]
        efficiencies = [e['efficiency'] for e in self.energy_history]
        
        return {
            'total_energy_consumed': self.total_energy_consumed,
            'average_power': np.mean(powers),
            'peak_power': np.max(powers),
            'average_efficiency': np.mean(efficiencies),
            'peak_efficiency': np.max(efficiencies),
            'energy_per_spike': self.total_energy_consumed / (self.spike_count + 1),
            'energy_per_plasticity_event': self.total_energy_consumed / (self.plasticity_count + 1),
            'uptime': len(self.energy_history) * 0.001,  # Assuming 1ms timesteps
            'thermal_efficiency': 1.0 / (1.0 + (self.temperature - 25.0) / 25.0)
        }
    
    def reset_energy_tracking(self):
        """Reset energy tracking"""
        self.energy_history.clear()
        self.power_history.clear()
        self.efficiency_history.clear()
        
        self.current_power = 0.0
        self.total_energy_consumed = 0.0
        self.efficiency_ratio = 0.0
        
        self.spike_count = 0
        self.plasticity_count = 0
        self.memory_operations = 0
        
        self.temperature = 25.0
        
        logger.info("Reset energy tracking")
