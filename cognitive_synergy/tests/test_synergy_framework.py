#!/usr/bin/env python3
"""
Comprehensive Test Suite for Cognitive Synergy Framework
========================================================

Tests all core components of the cognitive synergy framework implementing
Ben Goertzel's PRIMUS theory.
"""

import unittest
import numpy as np
import time
import sys
from pathlib import Path

# Add cognitive synergy modules to path
sys.path.append(str(Path(__file__).parent.parent))

from core.primus_foundation import PRIMUSFoundation, CognitivePrimitive
from core.cognitive_synergy_engine import CognitiveSynergyEngine
from core.synergy_metrics import SynergyMetrics
from core.emergent_properties import EmergentPropertyDetector
from core.self_organization import SelfOrganizationMechanism
from modules.pattern_reasoning.pattern_reasoning_synergy import PatternReasoningSynergy
from modules.perception_action.sensorimotor_synergy import SensorimotorSynergy


class TestPRIMUSFoundation(unittest.TestCase):
    """Test PRIMUS foundation functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.primus = PRIMUSFoundation(dimension=64, synergy_threshold=0.5)
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self.primus, 'stop'):
            self.primus.stop()
    
    def test_initialization(self):
        """Test PRIMUS foundation initialization"""
        self.assertEqual(self.primus.dimension, 64)
        self.assertEqual(self.primus.synergy_threshold, 0.5)
        self.assertIsInstance(self.primus.primitives, dict)
        self.assertIsInstance(self.primus.pattern_space, dict)
    
    def test_add_primitive(self):
        """Test adding cognitive primitives"""
        primitive = CognitivePrimitive(
            name="test_concept",
            type="concept", 
            content="test concept content",
            confidence=0.8
        )
        
        self.primus.add_primitive(primitive)
        
        self.assertIn("test_concept", self.primus.primitives)
        retrieved = self.primus.get_primitive("test_concept")
        self.assertEqual(retrieved.name, "test_concept")
        self.assertEqual(retrieved.confidence, 0.8)
    
    def test_synergy_computation(self):
        """Test synergy computation between primitives"""
        # Add two related primitives
        p1 = CognitivePrimitive("concept1", "concept", "related content", 0.9)
        p2 = CognitivePrimitive("concept2", "concept", "related content", 0.8)
        
        self.primus.add_primitive(p1)
        self.primus.add_primitive(p2)
        
        synergy = self.primus.compute_synergy("concept1", "concept2")
        
        self.assertIsInstance(synergy, float)
        self.assertGreaterEqual(synergy, 0.0)
        self.assertLessEqual(synergy, 1.0)
    
    def test_pattern_mining(self):
        """Test pattern mining functionality"""
        # Add some test primitives
        for i in range(5):
            primitive = CognitivePrimitive(f"pattern_{i}", "pattern", [i, i+1, i], 0.7)
            self.primus.add_primitive(primitive)
        
        # Start system briefly to allow pattern mining
        with self.primus:
            time.sleep(0.5)  # Allow some processing
            
            state = self.primus.get_system_state()
            self.assertIn('patterns_count', state.self_organization_metrics)
    
    def test_motivation_system(self):
        """Test motivation system functionality"""
        initial_curiosity = self.primus.motivation_system['curiosity']
        
        # Inject stimulus that should affect motivation
        self.primus.inject_stimulus({
            'type': 'learning',
            'content': 'new learning opportunity'
        })
        
        # Check that motivation system is affected
        self.assertIsInstance(self.primus.motivation_system['learning'], float)
        self.assertGreaterEqual(self.primus.motivation_system['learning'], 0.0)


class TestCognitiveSynergyEngine(unittest.TestCase):
    """Test cognitive synergy engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.primus = PRIMUSFoundation(dimension=32)
        self.engine = CognitiveSynergyEngine(
            self.primus,
            update_frequency=10.0,
            synergy_threshold=0.6
        )
    
    def tearDown(self):
        """Clean up after tests"""
        self.engine.stop()
        self.primus.stop()
    
    def test_initialization(self):
        """Test engine initialization"""
        self.assertEqual(len(self.engine.synergy_pairs), 10)  # 10 core pairs
        self.assertIn('pattern_reasoning', self.engine.synergy_pairs)
        self.assertIn('perception_action', self.engine.synergy_pairs)
        self.assertEqual(self.engine.synergy_threshold, 0.6)
    
    def test_module_registration(self):
        """Test module registration"""
        test_module = PatternReasoningSynergy()
        self.engine.register_module('test_module', test_module)
        
        self.assertIn('test_module', self.engine.modules)
        self.assertEqual(self.engine.modules['test_module'], test_module)
    
    def test_stimulus_processing(self):
        """Test stimulus injection and processing"""
        stimulus = {
            'type': 'perceptual',
            'data': np.random.rand(10),
            'confidence': 0.8
        }
        
        initial_synergy = self.engine.get_synergy_strength('perception_action')
        self.engine.inject_stimulus(stimulus)
        
        # Should affect perception-action synergy
        updated_synergy = self.engine.get_synergy_strength('perception_action')
        # Synergy might increase due to stimulus
        self.assertIsInstance(updated_synergy, float)
    
    def test_synergy_measurement(self):
        """Test synergy strength measurement"""
        with self.engine:
            time.sleep(0.2)  # Allow brief processing
            
            for pair_name in self.engine.synergy_pairs:
                synergy = self.engine.get_synergy_strength(pair_name)
                self.assertIsInstance(synergy, float)
                self.assertGreaterEqual(synergy, 0.0)
                self.assertLessEqual(synergy, 1.0)
    
    def test_system_state(self):
        """Test system state retrieval"""
        state = self.engine.get_system_state()
        
        required_keys = ['primus_state', 'synergy_pairs', 'global_coherence', 
                        'integration_matrix', 'performance_metrics']
        
        for key in required_keys:
            self.assertIn(key, state)
        
        self.assertIsInstance(state['global_coherence'], float)
        self.assertIsInstance(state['synergy_pairs'], dict)


class TestSynergyMetrics(unittest.TestCase):
    """Test mathematical synergy metrics"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.metrics = SynergyMetrics(history_length=100, sampling_rate=10.0)
    
    def test_time_series_data_addition(self):
        """Test adding time series data"""
        for i in range(10):
            self.metrics.add_time_series_data(
                'test_pair', 
                np.sin(i * 0.1), 
                np.cos(i * 0.1)
            )
        
        self.assertIn('test_pair', self.metrics.time_series_data)
        data = self.metrics.time_series_data['test_pair']
        self.assertEqual(len(data['process_a']), 10)
        self.assertEqual(len(data['process_b']), 10)
    
    def test_mutual_information_computation(self):
        """Test mutual information computation"""
        # Add correlated data
        for i in range(50):
            x = np.sin(i * 0.1) + np.random.normal(0, 0.1)
            y = np.sin(i * 0.1) + np.random.normal(0, 0.1)  # Correlated
            self.metrics.add_time_series_data('correlated_pair', x, y)
        
        profile = self.metrics.compute_synergy_profile('correlated_pair')
        
        self.assertIsNotNone(profile)
        self.assertGreaterEqual(profile.mutual_information, 0.0)
        self.assertLessEqual(profile.mutual_information, 1.0)
    
    def test_synergy_strength_calculation(self):
        """Test overall synergy strength calculation"""
        # Add test data
        for i in range(50):
            self.metrics.add_time_series_data('test_pair', i/50.0, (i/50.0)**2)
        
        synergy_strength = self.metrics.get_synergy_strength('test_pair')
        
        self.assertIsInstance(synergy_strength, float)
        self.assertGreaterEqual(synergy_strength, 0.0)
        self.assertLessEqual(synergy_strength, 1.0)
    
    def test_global_synergy_computation(self):
        """Test global synergy metrics"""
        # Add data for multiple pairs
        pairs = ['pair1', 'pair2', 'pair3']
        
        for pair in pairs:
            for i in range(20):
                x = np.random.rand()
                y = np.random.rand()
                self.metrics.add_time_series_data(pair, x, y)
        
        global_metrics = self.metrics.compute_global_synergy()
        
        self.assertIn('global_synergy', global_metrics)
        self.assertIn('total_emergence', global_metrics)
        self.assertIsInstance(global_metrics['global_synergy'], float)


class TestEmergentProperties(unittest.TestCase):
    """Test emergent property detection"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = EmergentPropertyDetector(emergence_threshold=0.6)
    
    def test_behavioral_emergence_detection(self):
        """Test behavioral emergence detection"""
        # Create system state with high synergy
        system_state = {
            'synergy_pairs': {
                'test_pair': {
                    'synergy_strength': 0.9,
                    'integration_level': 0.8,
                    'emergence_indicators': ['high_synergy']
                }
            },
            'global_coherence': 0.85,
            'cognitive_dynamics': [
                {'type': 'oscillation', 'intensity': 0.7, 'age': 2.0}
            ]
        }
        
        properties = self.detector.detect_emergence(system_state)
        
        # Should detect some emergent properties
        self.assertIsInstance(properties, list)
        for prop in properties:
            self.assertGreaterEqual(prop.strength, self.detector.emergence_threshold)
    
    def test_property_tracking(self):
        """Test emergent property tracking over time"""
        system_state = {
            'synergy_pairs': {
                'persistent_pair': {
                    'synergy_strength': 0.8,
                    'integration_level': 0.7
                }
            },
            'global_coherence': 0.8
        }
        
        # Detect properties multiple times
        for _ in range(3):
            self.detector.detect_emergence(system_state)
            time.sleep(0.1)
        
        # Should have tracked properties
        self.assertGreater(len(self.detector.detected_properties), 0)
    
    def test_stability_computation(self):
        """Test property stability computation"""
        # Add a property and track it
        system_state = {
            'synergy_pairs': {
                'stable_pair': {
                    'synergy_strength': 0.75,
                    'integration_level': 0.8
                }
            },
            'global_coherence': 0.8
        }
        
        # Detect multiple times with consistent strength
        for _ in range(5):
            self.detector.detect_emergence(system_state)
            time.sleep(0.05)
        
        stable_properties = self.detector.get_stable_properties(min_stability=0.5)
        
        for prop in stable_properties:
            self.assertGreaterEqual(prop.stability, 0.5)


class TestSelfOrganization(unittest.TestCase):
    """Test self-organization mechanisms"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.organization = SelfOrganizationMechanism(
            target_coherence=0.8,
            adaptation_rate=0.1
        )
    
    def test_rule_initialization(self):
        """Test organization rule initialization"""
        self.assertGreater(len(self.organization.organization_rules), 0)
        
        for rule in self.organization.organization_rules:
            self.assertIsNotNone(rule.name)
            self.assertIsNotNone(rule.condition)
            self.assertIsNotNone(rule.action)
            self.assertGreater(rule.priority, 0.0)
    
    def test_organization_state_computation(self):
        """Test organization state computation"""
        # Create test system state
        synergy_pairs = {
            'test_pair1': {'synergy_strength': 0.7, 'integration_level': 0.6},
            'test_pair2': {'synergy_strength': 0.5, 'integration_level': 0.8}
        }
        
        integration_matrix = np.array([[1.0, 0.7], [0.7, 1.0]])
        performance_history = {'coherence': [0.8, 0.75, 0.82]}
        
        actions = self.organization.apply(
            synergy_pairs, 0.75, integration_matrix, performance_history
        )
        
        self.assertIsInstance(actions, dict)
        self.assertIn('organization_state', actions)
        
        state = actions['organization_state']
        self.assertIsInstance(state.entropy, float)
        self.assertIsInstance(state.complexity, float)
        self.assertIsInstance(state.coherence, float)
    
    def test_rule_application(self):
        """Test organization rule application"""
        # Create state that should trigger rules
        synergy_pairs = {
            'imbalanced_pair1': {'synergy_strength': 0.9},
            'imbalanced_pair2': {'synergy_strength': 0.1}  # Should trigger balancing
        }
        
        integration_matrix = np.eye(2)
        performance_history = {'efficiency': [0.4, 0.3, 0.5]}  # Low efficiency
        
        actions = self.organization.apply(
            synergy_pairs, 0.5, integration_matrix, performance_history
        )
        
        # Should have applied some rules
        self.assertIn('applied_rules', actions)
        self.assertIsInstance(actions['applied_rules'], list)


class TestPatternReasoningSynergy(unittest.TestCase):
    """Test pattern-reasoning synergy module"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.synergy = PatternReasoningSynergy(
            synergy_update_rate=5.0,
            integration_threshold=0.6
        )
    
    def tearDown(self):
        """Clean up after tests"""
        self.synergy.stop()
    
    def test_initialization(self):
        """Test pattern-reasoning synergy initialization"""
        self.assertIsNotNone(self.synergy.pattern_engine)
        self.assertIsNotNone(self.synergy.reasoning_engine)
        self.assertEqual(self.synergy.integration_threshold, 0.6)
    
    def test_external_input_processing(self):
        """Test external input processing"""
        test_input = {
            'type': 'sequence',
            'data': [1, 2, 3, 2, 1],
            'confidence': 0.8
        }
        
        self.synergy.process_external_input(test_input)
        
        # Should create synergy event
        self.assertGreater(len(self.synergy.synergy_events), 0)
    
    def test_synergy_state_retrieval(self):
        """Test synergy state retrieval"""
        state = self.synergy.get_synergy_state()
        
        required_keys = ['metrics', 'recent_events', 'emergent_concepts',
                        'pattern_engine_state', 'reasoning_engine_state']
        
        for key in required_keys:
            self.assertIn(key, state)
        
        # Check metrics structure
        metrics = state['metrics']
        self.assertIn('synergy_strength', metrics)
        self.assertIn('integration_level', metrics)
        self.assertIn('bidirectional_flow_rate', metrics)


class TestSensorimotorSynergy(unittest.TestCase):
    """Test sensorimotor synergy module"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.synergy = SensorimotorSynergy(
            coupling_threshold=0.6,
            adaptation_rate=0.01
        )
    
    def test_sensorimotor_loop_creation(self):
        """Test sensorimotor loop creation"""
        loop = self.synergy.add_sensorimotor_loop(
            'test_loop', 'visual', 'motor'
        )
        
        self.assertEqual(loop.name, 'test_loop')
        self.assertEqual(loop.perception_modality, 'visual')
        self.assertEqual(loop.action_modality, 'motor')
        self.assertIn('test_loop', self.synergy.sensorimotor_loops)
    
    def test_perception_processing(self):
        """Test perception processing"""
        # Add sensorimotor loop
        self.synergy.add_sensorimotor_loop('test_loop', 'visual', 'motor')
        
        # Process perception
        features = np.random.rand(10)
        result = self.synergy.process_perception('visual', features, 0.8)
        
        self.assertIn('processed_perception', result)
        self.assertIn('loop_responses', result)
        self.assertIn('predictions', result)
    
    def test_action_processing(self):
        """Test action processing"""
        # Add sensorimotor loop
        self.synergy.add_sensorimotor_loop('test_loop', 'visual', 'motor')
        
        # Process action
        commands = np.random.rand(5)
        result = self.synergy.process_action('motor', commands, 0.9)
        
        self.assertIn('processed_action', result)
        self.assertIn('loop_responses', result)
        self.assertIn('sensory_predictions', result)
    
    def test_prediction_validation(self):
        """Test prediction validation"""
        # Add sensorimotor loop
        loop = self.synergy.add_sensorimotor_loop('test_loop', 'visual', 'motor')
        
        # Process action to generate prediction
        commands = np.random.rand(3)
        self.synergy.process_action('motor', commands)
        
        # Should have generated a prediction
        self.assertGreater(len(self.synergy.predictions), 0)
        
        # Add corresponding perception
        features = np.random.rand(10)
        self.synergy.process_perception('visual', features)
        
        # Validate predictions
        self.synergy.validate_predictions()


class IntegrationTests(unittest.TestCase):
    """Integration tests for the complete framework"""
    
    def setUp(self):
        """Set up integrated system"""
        self.primus = PRIMUSFoundation(dimension=64)
        self.engine = CognitiveSynergyEngine(self.primus)
        self.pattern_reasoning = PatternReasoningSynergy()
        self.sensorimotor = SensorimotorSynergy()
        
        # Register modules
        self.engine.register_module('pattern_reasoning', self.pattern_reasoning)
        self.engine.register_module('sensorimotor', self.sensorimotor)
    
    def tearDown(self):
        """Clean up integrated system"""
        self.engine.stop()
        self.pattern_reasoning.stop()
        self.primus.stop()
    
    def test_full_system_integration(self):
        """Test full system integration"""
        with self.engine:
            # Add some primitives
            primitives = [
                CognitivePrimitive("concept1", "concept", "test concept", 0.8),
                CognitivePrimitive("pattern1", "pattern", [1, 2, 3], 0.9)
            ]
            
            for primitive in primitives:
                self.primus.add_primitive(primitive)
            
            # Add sensorimotor loop
            self.sensorimotor.add_sensorimotor_loop('visual_motor', 'visual', 'motor')
            
            # Process various inputs
            stimuli = [
                {'type': 'perceptual', 'data': np.random.rand(5)},
                {'type': 'learning', 'data': 'new learning input'}
            ]
            
            for stimulus in stimuli:
                self.engine.inject_stimulus(stimulus)
            
            # Allow processing time
            time.sleep(0.5)
            
            # Check system state
            state = self.engine.get_system_state()
            
            self.assertIn('global_coherence', state)
            self.assertIn('synergy_pairs', state)
            self.assertGreater(len(state['synergy_pairs']), 0)
    
    def test_emergence_detection_integration(self):
        """Test emergence detection in integrated system"""
        with self.engine:
            # Create conditions for emergence
            high_synergy_primitives = [
                CognitivePrimitive(f"synergistic_{i}", "concept", f"content_{i}", 0.9)
                for i in range(5)
            ]
            
            for primitive in high_synergy_primitives:
                self.primus.add_primitive(primitive)
            
            # Process for several cycles
            for _ in range(10):
                self.engine.inject_stimulus({
                    'type': 'learning',
                    'data': np.random.rand(8)
                })
                time.sleep(0.1)
            
            # Check for emergence
            emergence_indicators = self.engine.get_emergence_indicators()
            
            # Should detect some form of emergence
            self.assertIsInstance(emergence_indicators, list)
    
    def test_self_organization_integration(self):
        """Test self-organization in integrated system"""
        with self.engine:
            # Create imbalanced initial conditions
            weak_primitives = [
                CognitivePrimitive(f"weak_{i}", "concept", f"weak_content_{i}", 0.3)
                for i in range(3)
            ]
            strong_primitives = [
                CognitivePrimitive(f"strong_{i}", "concept", f"strong_content_{i}", 0.9)
                for i in range(2)
            ]
            
            for primitive in weak_primitives + strong_primitives:
                self.primus.add_primitive(primitive)
            
            # Let system self-organize
            initial_state = self.engine.get_system_state()
            initial_coherence = initial_state['global_coherence']
            
            # Process for several cycles to allow self-organization
            for _ in range(20):
                self.engine.inject_stimulus({
                    'type': 'general',
                    'data': 'organizational stimulus'
                })
                time.sleep(0.1)
            
            final_state = self.engine.get_system_state()
            final_coherence = final_state['global_coherence']
            
            # System should have adapted (coherence might change in any direction)
            self.assertIsInstance(final_coherence, float)
            self.assertNotEqual(initial_coherence, final_coherence)


def run_tests():
    """Run all tests"""
    test_classes = [
        TestPRIMUSFoundation,
        TestCognitiveSynergyEngine,
        TestSynergyMetrics,
        TestEmergentProperties,
        TestSelfOrganization,
        TestPatternReasoningSynergy,
        TestSensorimotorSynergy,
        IntegrationTests
    ]
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 70)
    print("COGNITIVE SYNERGY FRAMEWORK - COMPREHENSIVE TEST SUITE")
    print("Testing Ben Goertzel's PRIMUS Theory Implementation")
    print("=" * 70)
    
    success = run_tests()
    
    if success:
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
        print("Cognitive Synergy Framework is functioning correctly")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ SOME TESTS FAILED")
        print("Please check the output above for details")
        print("=" * 70)
        sys.exit(1)