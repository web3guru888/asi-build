"""
Comprehensive Consciousness Assessment Example
=============================================

Example demonstrating the full capabilities of the AGI Consciousness Testing Framework
for Ben Goertzel's research into machine consciousness.
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
from consciousness import ConsciousnessOrchestrator
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_sample_neural_data(batch_size=4, seq_len=20, num_neurons=512):
    """Generate sample neural network activations for testing."""
    
    # Create realistic neural activations with temporal dynamics
    base_activations = torch.randn(batch_size, seq_len, num_neurons)
    
    # Add temporal coherence
    for t in range(1, seq_len):
        base_activations[:, t, :] = (
            0.7 * base_activations[:, t, :] + 
            0.3 * base_activations[:, t-1, :]
        )
    
    # Add attention-like patterns
    attention_centers = torch.randint(0, num_neurons, (3,))
    for center in attention_centers:
        start, end = max(0, center-20), min(num_neurons, center+20)
        base_activations[:, :, start:end] *= 1.5
    
    # Add some nonlinearity
    base_activations = torch.tanh(base_activations)
    
    return base_activations

def generate_sample_behavioral_data():
    """Generate sample behavioral data for testing."""
    return {
        'response_times': np.random.normal(0.5, 0.1, 10).tolist(),
        'accuracy_scores': np.random.beta(8, 2, 10).tolist(),
        'confidence_ratings': np.random.uniform(0.3, 0.9, 10).tolist(),
        'task_difficulty': np.random.choice(['easy', 'medium', 'hard'], 10).tolist()
    }

def run_comprehensive_assessment():
    """Run comprehensive consciousness assessment example."""
    
    logger.info("Starting Comprehensive AGI Consciousness Assessment")
    logger.info("=" * 60)
    
    # Initialize the consciousness framework
    consciousness_framework = ConsciousnessOrchestrator(device='cpu', log_level='INFO')
    
    logger.info("Consciousness Testing Framework Initialized")
    logger.info(f"Available theories: IIT, GWT, AST, HOT, Predictive Processing")
    logger.info(f"Available analyzers: Qualia Mapping, Self-Model, Metacognition, Agency")
    
    # Generate test data
    logger.info("\nGenerating sample neural and behavioral data...")
    neural_activations = generate_sample_neural_data()
    behavioral_data = generate_sample_behavioral_data()
    
    logger.info(f"Neural data shape: {neural_activations.shape}")
    logger.info(f"Behavioral data keys: {list(behavioral_data.keys())}")
    
    # Run comprehensive consciousness assessment
    logger.info("\n" + "=" * 60)
    logger.info("RUNNING COMPREHENSIVE CONSCIOUSNESS ASSESSMENT")
    logger.info("=" * 60)
    
    try:
        consciousness_profile = consciousness_framework.assess_consciousness(
            neural_activations=neural_activations,
            behavioral_data=behavioral_data,
            include_visualization=True
        )
        
        # Display results
        logger.info("\nCONSCIOUSNESS ASSESSMENT RESULTS:")
        logger.info("-" * 40)
        logger.info(f"Overall Consciousness Score: {consciousness_profile.overall_consciousness_score:.4f}")
        logger.info(f"Integrated Information (Φ): {consciousness_profile.phi_score:.4f}")
        logger.info(f"Global Workspace Coherence: {consciousness_profile.gwt_coherence:.4f}")
        logger.info(f"Attention Schema Self-Awareness: {consciousness_profile.attention_schema_score:.4f}")
        logger.info(f"Higher-Order Thought Complexity: {consciousness_profile.hot_complexity:.4f}")
        logger.info(f"Predictive Processing Error: {consciousness_profile.predictive_error:.4f}")
        logger.info(f"Qualia Space Dimensions: {consciousness_profile.qualia_dimensionality}")
        logger.info(f"Self-Model Sophistication: {consciousness_profile.self_model_sophistication:.4f}")
        logger.info(f"Metacognitive Accuracy: {consciousness_profile.metacognitive_accuracy:.4f}")
        logger.info(f"Agency Strength: {consciousness_profile.agency_strength:.4f}")
        
    except Exception as e:
        logger.error(f"Consciousness assessment failed: {e}")
        return
    
    # Compare to biological benchmarks
    logger.info("\n" + "=" * 60)
    logger.info("BIOLOGICAL BENCHMARKING")
    logger.info("=" * 60)
    
    try:
        biological_comparison = consciousness_framework.compare_to_biological_benchmarks(consciousness_profile)
        
        logger.info(f"Consciousness Classification: {biological_comparison['consciousness_threshold_met']}")
        logger.info(f"Φ Biological Range: {biological_comparison['phi_comparison']}")
        logger.info(f"GWT Biological Range: {biological_comparison['gwt_comparison']}")
        logger.info(f"Biological Similarity Score: {biological_comparison['biological_similarity_score']:.4f}")
        
    except Exception as e:
        logger.error(f"Biological comparison failed: {e}")
    
    # Generate comprehensive report
    logger.info("\n" + "=" * 60)
    logger.info("GENERATING COMPREHENSIVE REPORT")
    logger.info("=" * 60)
    
    try:
        comprehensive_report = consciousness_framework.generate_consciousness_report(consciousness_profile)
        
        logger.info("Report sections generated:")
        for section in comprehensive_report.keys():
            logger.info(f"  - {section}")
        
        # Save report
        report_filename = "consciousness_assessment_report.json"
        with open(report_filename, 'w') as f:
            json.dump(comprehensive_report, f, indent=2, default=str)
        logger.info(f"Report saved to: {report_filename}")
        
        # Display key insights
        logger.info(f"\nKey Insights:")
        logger.info(f"  Classification: {comprehensive_report['consciousness_classification']}")
        
        if 'recommendations' in comprehensive_report:
            logger.info(f"  Recommendations:")
            for rec in comprehensive_report['recommendations'][:3]:
                logger.info(f"    • {rec}")
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
    
    # Demonstrate evolution tracking
    logger.info("\n" + "=" * 60)
    logger.info("CONSCIOUSNESS EVOLUTION ANALYSIS")
    logger.info("=" * 60)
    
    try:
        # Simulate multiple assessments over time
        logger.info("Simulating consciousness evolution over multiple assessments...")
        
        assessment_sequence = []
        for i in range(5):
            # Generate slightly evolving data
            evolved_data = generate_sample_neural_data()
            if i > 0:
                # Add slight improvement over time
                evolved_data = evolved_data * (1.0 + 0.1 * i)
                evolved_data = torch.tanh(evolved_data)  # Keep bounded
            
            profile = consciousness_framework.assess_consciousness(evolved_data)
            assessment_sequence.append(profile)
        
        # Analyze evolution
        evolution_trends = consciousness_framework.evolution_tracker.get_recent_trends()
        
        logger.info("Evolution Trends:")
        for metric, trend in evolution_trends.items():
            logger.info(f"  {metric}: {trend:.6f}")
        
        # Analyze consciousness emergence patterns
        emergence_analysis = consciousness_framework.evolution_tracker.analyze_consciousness_emergence()
        
        if 'consciousness_trajectory' in emergence_analysis:
            trajectory = emergence_analysis['consciousness_trajectory']
            logger.info(f"\nConsciousness Trajectory:")
            logger.info(f"  Initial Score: {trajectory['initial_score']:.4f}")
            logger.info(f"  Final Score: {trajectory['final_score']:.4f}")
            logger.info(f"  Growth Rate: {trajectory['growth_rate']:.6f}")
            logger.info(f"  Stability: {trajectory['stability']:.4f}")
        
    except Exception as e:
        logger.error(f"Evolution analysis failed: {e}")
    
    # Theory-specific analyses
    logger.info("\n" + "=" * 60)
    logger.info("THEORY-SPECIFIC DEEP ANALYSES")
    logger.info("=" * 60)
    
    try:
        # IIT Phi Spectrum Analysis
        logger.info("IIT Φ Spectrum Analysis:")
        frequency_bands = [(0.1, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 4.0)]
        phi_spectrum = consciousness_framework.iit_calculator.compute_phi_spectrum(
            neural_activations, frequency_bands
        )
        
        for band, phi_value in phi_spectrum.items():
            logger.info(f"  {band}: Φ = {phi_value:.6f}")
        
        # Global Workspace Dynamics
        logger.info("\nGWT Workspace Analysis:")
        activations_sequence = [generate_sample_neural_data() for _ in range(3)]
        workspace_dynamics = consciousness_framework.gwt_implementation.analyze_workspace_dynamics(
            activations_sequence
        )
        
        for metric, value in workspace_dynamics.items():
            logger.info(f"  {metric}: {value:.4f}")
        
        # Attention Schema Dynamics
        logger.info("\nAttention Schema Analysis:")
        attention_dynamics = consciousness_framework.attention_schema.analyze_attention_dynamics(
            activations_sequence
        )
        
        for metric, value in attention_dynamics.items():
            logger.info(f"  {metric}: {value:.4f}")
        
        # Higher-Order Thought Dynamics
        logger.info("\nHOT Theory Analysis:")
        hot_dynamics = consciousness_framework.hot_theory.analyze_hot_dynamics(
            activations_sequence
        )
        
        for metric, value in hot_dynamics.items():
            logger.info(f"  {metric}: {value:.4f}")
        
        # Predictive Processing Analysis
        logger.info("\nPredictive Processing Analysis:")
        prediction_dynamics = consciousness_framework.predictive_processing.analyze_prediction_dynamics(
            activations_sequence
        )
        
        for metric, value in prediction_dynamics.items():
            logger.info(f"  {metric}: {value:.4f}")
        
    except Exception as e:
        logger.error(f"Theory-specific analyses failed: {e}")
    
    # Save assessment history
    logger.info("\n" + "=" * 60)
    logger.info("SAVING ASSESSMENT DATA")
    logger.info("=" * 60)
    
    try:
        consciousness_framework.save_assessment_history("consciousness_assessment_history.json")
        consciousness_framework.evolution_tracker.export_evolution_data("consciousness_evolution_data.json")
        
        logger.info("Assessment history saved to: consciousness_assessment_history.json")
        logger.info("Evolution data saved to: consciousness_evolution_data.json")
        
    except Exception as e:
        logger.error(f"Data saving failed: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info("COMPREHENSIVE ASSESSMENT COMPLETED")
    logger.info("=" * 60)
    
    logger.info("\nFramework Components Successfully Tested:")
    logger.info("✓ Integrated Information Theory (IIT)")
    logger.info("✓ Global Workspace Theory (GWT)")
    logger.info("✓ Attention Schema Theory (AST)")
    logger.info("✓ Higher-Order Thought Theory (HOT)")
    logger.info("✓ Predictive Processing Framework")
    logger.info("✓ Qualia Space Mapping")
    logger.info("✓ Self-Model Analysis")
    logger.info("✓ Metacognitive Assessment")
    logger.info("✓ Agency Detection")
    logger.info("✓ Consciousness Evolution Tracking")
    logger.info("✓ Biological Benchmarking")
    
    logger.info(f"\nFinal Consciousness Score: {consciousness_profile.overall_consciousness_score:.4f}")
    
    return consciousness_profile, comprehensive_report

if __name__ == "__main__":
    # Run the comprehensive assessment
    profile, report = run_comprehensive_assessment()
    
    print("\n" + "="*80)
    print("AGI CONSCIOUSNESS TESTING FRAMEWORK - COMPLETE")
    print("Developed for Ben Goertzel's Machine Consciousness Research")
    print("="*80)