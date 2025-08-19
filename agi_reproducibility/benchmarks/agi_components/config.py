"""
Configuration for AGI Component Benchmark Suite
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from pathlib import Path


@dataclass
class BenchmarkConfig:
    """Configuration for AGI benchmark suite"""
    
    # General settings
    output_dir: str = "benchmark_results"
    log_level: str = "INFO"
    max_workers: int = 4
    timeout_seconds: int = 300
    
    # Benchmark categories to run
    run_reasoning: bool = True
    run_learning: bool = True
    run_memory: bool = True
    run_creativity: bool = True
    run_consciousness: bool = True
    run_symbolic: bool = True
    run_neural_symbolic: bool = True
    run_real_world: bool = True
    
    # Reasoning benchmark settings
    reasoning_config: Dict[str, Any] = None
    
    # Learning benchmark settings  
    learning_config: Dict[str, Any] = None
    
    # Memory benchmark settings
    memory_config: Dict[str, Any] = None
    
    # Creativity benchmark settings
    creativity_config: Dict[str, Any] = None
    
    # Consciousness benchmark settings
    consciousness_config: Dict[str, Any] = None
    
    # Symbolic AI benchmark settings
    symbolic_config: Dict[str, Any] = None
    
    # Neural-symbolic integration settings
    neural_symbolic_config: Dict[str, Any] = None
    
    # Real-world challenge settings
    real_world_config: Dict[str, Any] = None
    
    # Progress tracking settings
    tracking_config: Dict[str, Any] = None
    
    # Hardware settings
    use_gpu: bool = True
    gpu_memory_limit: Optional[int] = None
    cpu_cores: Optional[int] = None
    
    # Hyperon/PRIMUS specific settings
    hyperon_enabled: bool = True
    hyperon_config: Dict[str, Any] = None
    primus_enabled: bool = True
    primus_config: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default configurations"""
        if self.reasoning_config is None:
            self.reasoning_config = {
                "deductive_reasoning": {
                    "enabled": True,
                    "test_sets": ["syllogisms", "propositional_logic", "first_order_logic"],
                    "difficulty_levels": ["basic", "intermediate", "advanced"],
                    "max_inference_steps": 50
                },
                "inductive_reasoning": {
                    "enabled": True,
                    "test_sets": ["pattern_recognition", "sequence_completion", "rule_learning"],
                    "sample_sizes": [10, 50, 100, 500],
                    "noise_levels": [0.0, 0.1, 0.2, 0.3]
                },
                "abductive_reasoning": {
                    "enabled": True,
                    "test_sets": ["explanation_generation", "hypothesis_formation", "best_explanation"],
                    "evidence_completeness": [0.3, 0.5, 0.7, 0.9],
                    "multiple_hypotheses": True
                },
                "analogical_reasoning": {
                    "enabled": True,
                    "test_sets": ["abstract_analogies", "causal_analogies", "structural_analogies"],
                    "similarity_thresholds": [0.3, 0.5, 0.7, 0.9],
                    "cross_domain": True
                }
            }
            
        if self.learning_config is None:
            self.learning_config = {
                "one_shot_learning": {
                    "enabled": True,
                    "domains": ["visual", "linguistic", "symbolic", "numerical"],
                    "complexity_levels": ["simple", "medium", "complex"],
                    "generalization_tests": True
                },
                "few_shot_learning": {
                    "enabled": True,
                    "shot_counts": [2, 5, 10, 20],
                    "domains": ["classification", "regression", "sequence_modeling"],
                    "meta_learning": True
                },
                "continual_learning": {
                    "enabled": True,
                    "task_sequences": ["permuted_mnist", "split_cifar", "continual_nlp"],
                    "catastrophic_forgetting_metrics": True,
                    "replay_mechanisms": ["none", "experience_replay", "elastic_weight_consolidation"]
                },
                "transfer_learning": {
                    "enabled": True,
                    "source_domains": ["vision", "language", "reasoning", "control"],
                    "target_domains": ["vision", "language", "reasoning", "control"],
                    "adaptation_methods": ["fine_tuning", "feature_extraction", "domain_adaptation"]
                }
            }
            
        if self.memory_config is None:
            self.memory_config = {
                "episodic_memory": {
                    "enabled": True,
                    "test_sets": ["autobiographical_events", "narrative_recall", "temporal_ordering"],
                    "retention_intervals": ["immediate", "short_term", "long_term"],
                    "interference_tests": True
                },
                "semantic_memory": {
                    "enabled": True,
                    "test_sets": ["factual_knowledge", "conceptual_hierarchies", "semantic_networks"],
                    "knowledge_domains": ["common_sense", "scientific", "cultural"],
                    "consistency_checks": True
                },
                "procedural_memory": {
                    "enabled": True,
                    "test_sets": ["skill_learning", "habit_formation", "motor_sequences"],
                    "practice_schedules": ["massed", "distributed", "interleaved"],
                    "transfer_tests": True
                },
                "working_memory": {
                    "enabled": True,
                    "test_sets": ["n_back", "dual_task", "complex_span"],
                    "load_levels": [2, 4, 6, 8],
                    "modalities": ["verbal", "visual", "spatial"]
                }
            }
            
        if self.creativity_config is None:
            self.creativity_config = {
                "novel_problem_solving": {
                    "enabled": True,
                    "problem_types": ["insight_problems", "ill_defined_problems", "open_ended_challenges"],
                    "novelty_metrics": ["originality", "flexibility", "elaboration"],
                    "domain_generalization": True
                },
                "artistic_generation": {
                    "enabled": True,
                    "modalities": ["visual", "musical", "literary", "multimodal"],
                    "style_transfer": True,
                    "aesthetic_evaluation": True,
                    "coherence_metrics": True
                },
                "conceptual_combination": {
                    "enabled": True,
                    "combination_types": ["emergent", "hybrid", "relational"],
                    "creativity_assessment": ["novelty", "appropriateness", "elaboration"],
                    "cross_domain": True
                },
                "divergent_thinking": {
                    "enabled": True,
                    "test_types": ["alternative_uses", "consequences", "improvements"],
                    "fluency_measures": True,
                    "originality_scoring": True
                }
            }
            
        if self.consciousness_config is None:
            self.consciousness_config = {
                "self_awareness": {
                    "enabled": True,
                    "test_sets": ["mirror_test_analogues", "self_recognition", "introspective_reports"],
                    "metacognitive_awareness": True,
                    "confidence_calibration": True
                },
                "metacognition": {
                    "enabled": True,
                    "test_sets": ["feeling_of_knowing", "confidence_judgments", "strategy_monitoring"],
                    "metamemory_tests": True,
                    "cognitive_control": True
                },
                "qualia_indicators": {
                    "enabled": True,
                    "test_sets": ["subjective_experience_reports", "phenomenological_richness", "binding_problems"],
                    "hard_problem_tests": True,
                    "integrated_information": True
                },
                "theory_of_mind": {
                    "enabled": True,
                    "test_sets": ["false_belief", "mental_state_attribution", "intentionality"],
                    "recursive_theory_of_mind": True,
                    "social_cognition": True
                }
            }
            
        if self.symbolic_config is None:
            self.symbolic_config = {
                "pln_inference": {
                    "enabled": True,
                    "test_sets": ["probabilistic_syllogisms", "uncertain_reasoning", "belief_updating"],
                    "truth_value_types": ["simple", "indefinite", "distributional"],
                    "inference_rules": ["deduction", "induction", "abduction", "revision"]
                },
                "first_order_logic": {
                    "enabled": True,
                    "test_sets": ["theorem_proving", "model_checking", "satisfiability"],
                    "complexity_classes": ["propositional", "first_order", "higher_order"],
                    "automated_reasoning": True
                },
                "probabilistic_reasoning": {
                    "enabled": True,
                    "test_sets": ["bayesian_networks", "markov_models", "causal_inference"],
                    "uncertainty_types": ["aleatory", "epistemic", "ambiguity"],
                    "approximate_inference": True
                },
                "temporal_logic": {
                    "enabled": True,
                    "test_sets": ["ltl_formulas", "ctl_specifications", "temporal_planning"],
                    "time_models": ["linear", "branching", "metric"],
                    "verification_tasks": True
                }
            }
            
        if self.neural_symbolic_config is None:
            self.neural_symbolic_config = {
                "symbol_grounding": {
                    "enabled": True,
                    "test_sets": ["visual_symbol_grounding", "linguistic_grounding", "sensorimotor_grounding"],
                    "abstraction_levels": ["perceptual", "conceptual", "symbolic"],
                    "cross_modal": True
                },
                "concept_formation": {
                    "enabled": True,
                    "test_sets": ["prototype_learning", "exemplar_models", "theory_based_concepts"],
                    "hierarchical_concepts": True,
                    "compositional_concepts": True
                },
                "abstract_reasoning": {
                    "enabled": True,
                    "test_sets": ["ravens_progressive_matrices", "bongard_problems", "abstract_visual_reasoning"],
                    "neural_representations": True,
                    "symbolic_explanation": True
                },
                "explainable_ai": {
                    "enabled": True,
                    "explanation_types": ["local", "global", "counterfactual", "causal"],
                    "fidelity_metrics": True,
                    "human_interpretability": True
                }
            }
            
        if self.real_world_config is None:
            self.real_world_config = {
                "robotic_manipulation": {
                    "enabled": True,
                    "test_sets": ["pick_and_place", "assembly_tasks", "tool_use"],
                    "simulation_environments": ["pybullet", "mujoco", "gazebo"],
                    "real_robot_validation": False
                },
                "natural_language_understanding": {
                    "enabled": True,
                    "test_sets": ["reading_comprehension", "dialogue_systems", "question_answering"],
                    "scale_levels": ["sentence", "paragraph", "document", "multi_document"],
                    "domain_adaptation": True
                },
                "scientific_discovery": {
                    "enabled": True,
                    "test_sets": ["hypothesis_generation", "experiment_design", "data_interpretation"],
                    "domains": ["physics", "chemistry", "biology", "medicine"],
                    "literature_integration": True
                },
                "economic_reasoning": {
                    "enabled": True,
                    "test_sets": ["market_prediction", "game_theory", "auction_mechanisms"],
                    "multi_agent_scenarios": True,
                    "behavioral_economics": True
                }
            }
            
        if self.tracking_config is None:
            self.tracking_config = {
                "database": {
                    "type": "sqlite",
                    "path": "agi_benchmark_results.db",
                    "backup_enabled": True
                },
                "visualization": {
                    "enabled": True,
                    "plot_types": ["progress_curves", "capability_radar", "leaderboards"],
                    "interactive_plots": True
                },
                "comparison": {
                    "baseline_systems": ["random", "human_average", "domain_experts"],
                    "statistical_tests": True,
                    "effect_sizes": True
                }
            }
            
        if self.hyperon_config is None:
            self.hyperon_config = {
                "metta_interpreter": {
                    "enabled": True,
                    "reasoning_tests": True,
                    "learning_tests": True,
                    "memory_tests": True
                },
                "atomspace_operations": {
                    "enabled": True,
                    "pattern_matching": True,
                    "inference_control": True,
                    "attention_allocation": True
                },
                "distributed_processing": {
                    "enabled": False,
                    "node_count": 1,
                    "communication_overhead": True
                }
            }
            
        if self.primus_config is None:
            self.primus_config = {
                "cognitive_architecture": {
                    "enabled": True,
                    "module_integration": True,
                    "cognitive_cycles": True,
                    "attention_mechanisms": True
                },
                "goal_oriented_behavior": {
                    "enabled": True,
                    "planning_tests": True,
                    "execution_monitoring": True,
                    "goal_adaptation": True
                },
                "learning_integration": {
                    "enabled": True,
                    "procedural_learning": True,
                    "declarative_learning": True,
                    "meta_learning": True
                }
            }
    
    def save_config(self, filepath: str) -> None:
        """Save configuration to JSON file"""
        config_dict = asdict(self)
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    @classmethod
    def load_config(cls, filepath: str) -> 'BenchmarkConfig':
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            config_dict = json.load(f)
        return cls(**config_dict)
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Check output directory
        if not os.path.exists(os.path.dirname(self.output_dir)):
            issues.append(f"Output directory parent does not exist: {os.path.dirname(self.output_dir)}")
        
        # Check worker count
        if self.max_workers <= 0:
            issues.append("max_workers must be positive")
        
        # Check timeout
        if self.timeout_seconds <= 0:
            issues.append("timeout_seconds must be positive")
        
        # Check at least one benchmark is enabled
        benchmark_flags = [
            self.run_reasoning, self.run_learning, self.run_memory,
            self.run_creativity, self.run_consciousness, self.run_symbolic,
            self.run_neural_symbolic, self.run_real_world
        ]
        if not any(benchmark_flags):
            issues.append("At least one benchmark category must be enabled")
        
        return issues


# Default configuration instance
DEFAULT_CONFIG = BenchmarkConfig()