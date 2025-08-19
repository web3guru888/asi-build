# AGI Component Benchmark Suite

A comprehensive benchmark suite for measuring genuine AGI progress across core cognitive capabilities, addressing Ben Goertzel's need for objective AGI progress measurement.

## Overview

The AGI Component Benchmark Suite provides a standardized framework for evaluating Artificial General Intelligence systems across eight fundamental cognitive domains:

- **Reasoning**: Deductive, inductive, abductive, and analogical reasoning
- **Learning**: One-shot, few-shot, continual, and transfer learning  
- **Memory**: Episodic, semantic, procedural, and working memory
- **Creativity**: Novel problem solving, artistic generation, conceptual combination
- **Consciousness**: Self-awareness, metacognition, qualia indicators, theory of mind
- **Symbolic AI**: PLN inference, first-order logic, probabilistic reasoning, temporal logic
- **Neural-Symbolic Integration**: Symbol grounding, concept formation, abstract reasoning
- **Real-World Challenges**: Robotics, NLU, scientific discovery, economic reasoning, ethics

## Key Features

### Comprehensive Coverage
- 8 core AGI capability domains
- 100+ individual benchmark tests
- Multiple difficulty levels and complexity settings
- Domain-specific and cross-domain evaluation

### Hyperon/PRIMUS Support
- Specific tests for Hyperon MeTTa interpreter
- PRIMUS cognitive architecture benchmarks
- AtomSpace operations testing
- Distributed processing evaluation

### Progress Tracking
- Historical benchmark results database
- Performance trend analysis over time
- Leaderboards for different AGI approaches
- Capability gap identification and recommendations

### Hardware Agnostic
- Reproducible across different hardware configurations
- Configurable resource limits and timeouts
- Support for GPU and CPU-only execution
- Containerized environments for consistency

### Analysis and Visualization
- Statistical analysis of results
- Performance comparison between systems
- Capability profiling and visualization
- Automated report generation

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd agi_reproducibility/benchmarks/agi_components

# Install dependencies
pip install -r requirements.txt

# Optional: Install visualization dependencies
pip install matplotlib seaborn scipy
```

### Basic Usage

```python
from agi_components import AGIBenchmarkSuite, BenchmarkConfig
from agi_components.core import AGISystem

# Create configuration
config = BenchmarkConfig(
    output_dir="results",
    run_reasoning=True,
    run_learning=True,
    max_workers=4
)

# Initialize benchmark suite
suite = AGIBenchmarkSuite(config)

# Implement your AGI system
class MyAGISystem(AGISystem):
    def __init__(self):
        super().__init__("MyAGI", "1.0.0")
    
    def initialize(self, config):
        # Initialize your system
        self.initialized = True
        return True
    
    def process_reasoning_task(self, task):
        # Implement reasoning capabilities
        return {"answer": "result"}
    
    # Implement other required methods...

# Run benchmarks
system = MyAGISystem()
results = suite.benchmark_system(system)

print(f"Overall Score: {results.average_score:.2f}")
print(f"Success Rate: {results.success_rate:.1f}%")
```

### Configuration

The benchmark suite is highly configurable through the `BenchmarkConfig` class:

```python
config = BenchmarkConfig(
    # General settings
    output_dir="benchmark_results",
    log_level="INFO",
    max_workers=4,
    timeout_seconds=300,
    
    # Benchmark categories
    run_reasoning=True,
    run_learning=True,
    run_memory=True,
    run_creativity=True,
    run_consciousness=True,
    run_symbolic=True,
    run_neural_symbolic=True,
    run_real_world=True,
    
    # Hardware settings
    use_gpu=True,
    gpu_memory_limit=8192,  # MB
    cpu_cores=8,
    
    # Hyperon/PRIMUS specific
    hyperon_enabled=True,
    primus_enabled=True
)
```

## Benchmark Categories

### 1. Reasoning Benchmarks

Tests logical reasoning capabilities across four types:

**Deductive Reasoning**
- Syllogisms (Aristotelian logic)
- Propositional logic inference
- First-order logic theorem proving

**Inductive Reasoning**
- Pattern recognition in sequences
- Rule learning from examples
- Statistical inference

**Abductive Reasoning**
- Explanation generation
- Hypothesis formation
- Best explanation selection

**Analogical Reasoning**
- Abstract analogies
- Causal analogies
- Cross-domain mapping

Example reasoning test:
```python
{
    "type": "deductive_reasoning",
    "premises": [
        "All humans are mortal",
        "Socrates is human"
    ],
    "question": "Is Socrates mortal?",
    "expected_answer": True
}
```

### 2. Learning Benchmarks

Evaluates learning efficiency and adaptability:

**One-Shot Learning**
- Visual concept learning
- Linguistic pattern acquisition
- Rapid generalization from single examples

**Few-Shot Learning**
- Meta-learning evaluation
- k-shot classification (k=2,5,10,20)
- Cross-domain adaptation

**Continual Learning**
- Sequential task learning
- Catastrophic forgetting measurement
- Replay mechanism evaluation

**Transfer Learning**
- Cross-domain knowledge transfer
- Feature extraction quality
- Adaptation efficiency

### 3. Memory Benchmarks

Tests different memory systems:

**Episodic Memory**
- Autobiographical event recall
- Temporal ordering
- Context-dependent retrieval

**Semantic Memory**
- Factual knowledge storage
- Conceptual hierarchies
- Semantic network navigation

**Procedural Memory**
- Skill acquisition and retention
- Motor sequence learning
- Habit formation

**Working Memory**
- N-back tasks
- Dual-task performance
- Complex span tests

### 4. Creativity Benchmarks

Measures creative and innovative thinking:

**Novel Problem Solving**
- Insight problems (candle problem, nine dots)
- Ill-defined challenges
- Open-ended scenarios

**Artistic Generation**
- Visual art creation
- Musical composition
- Literary generation
- Style transfer

**Conceptual Combination**
- Emergent property generation
- Hybrid concept creation
- Cross-domain blending

**Divergent Thinking**
- Alternative uses tasks
- Consequences generation
- Improvement suggestions

### 5. Consciousness Benchmarks

Evaluates indicators of consciousness (behavioral markers):

**Self-Awareness**
- Mirror test analogues
- Self-recognition tasks
- Introspective reporting

**Metacognition**
- Feeling of knowing
- Confidence calibration
- Strategy monitoring

**Qualia Indicators**
- Subjective experience reports
- Phenomenological richness
- Binding problem tasks

**Theory of Mind**
- False belief tests
- Mental state attribution
- Intentionality understanding

### 6. Symbolic AI Benchmarks

Tests symbolic reasoning capabilities:

**PLN Inference**
- Probabilistic syllogisms
- Uncertain reasoning
- Belief updating

**First-Order Logic**
- Theorem proving
- Model checking
- Satisfiability testing

**Probabilistic Reasoning**
- Bayesian networks
- Markov models
- Causal inference

**Temporal Logic**
- LTL formulas
- CTL specifications
- Temporal planning

### 7. Neural-Symbolic Integration

Evaluates integration between neural and symbolic processing:

**Symbol Grounding**
- Visual symbol grounding
- Linguistic grounding
- Cross-modal grounding

**Concept Formation**
- Prototype learning
- Hierarchical concepts
- Compositional concepts

**Abstract Reasoning**
- Ravens Progressive Matrices
- Bongard problems
- Abstract visual reasoning

**Explainable AI**
- Local explanations
- Global model behavior
- Counterfactual reasoning

### 8. Real-World Challenges

Tests practical AGI capabilities:

**Robotic Manipulation**
- Pick and place tasks
- Assembly operations
- Tool use scenarios

**Natural Language Understanding**
- Reading comprehension
- Dialogue systems
- Question answering

**Scientific Discovery**
- Hypothesis generation
- Experiment design
- Data interpretation

**Economic Reasoning**
- Market prediction
- Game theory scenarios
- Auction mechanisms

**Ethical Reasoning**
- Moral dilemma resolution
- Value alignment
- Stakeholder consideration

## Implementing Your AGI System

To benchmark your AGI system, implement the `AGISystem` abstract base class:

```python
from agi_components.core import AGISystem

class YourAGISystem(AGISystem):
    def __init__(self, name="YourAGI", version="1.0"):
        super().__init__(name, version)
        # Initialize your system components
    
    def initialize(self, config):
        """Initialize the system with given configuration"""
        # Set up your system
        self.initialized = True
        return True
    
    def shutdown(self):
        """Clean shutdown of the system"""
        # Cleanup resources
        return True
    
    def process_reasoning_task(self, task):
        """Process reasoning tasks"""
        # Implement your reasoning logic
        return {
            "answer": your_reasoning_result,
            "confidence": confidence_score,
            "reasoning_steps": explanation
        }
    
    def process_learning_task(self, task):
        """Process learning tasks"""
        # Implement your learning logic
        return {
            "learned_model": your_model,
            "predictions": predictions,
            "learning_time": time_taken
        }
    
    def process_memory_task(self, task):
        """Process memory tasks"""
        # Implement your memory systems
        return {
            "recalled_information": recall_result,
            "confidence": confidence_score
        }
    
    def process_creativity_task(self, task):
        """Process creativity tasks"""
        # Implement your creativity mechanisms
        return {
            "creative_output": generated_content,
            "novelty_score": novelty_rating,
            "explanation": creative_process
        }
    
    def process_consciousness_task(self, task):
        """Process consciousness indicator tasks"""
        # Implement consciousness-related processing
        return {
            "response": your_response,
            "self_reflection": introspective_content,
            "meta_awareness": metacognitive_insights
        }
    
    def process_symbolic_task(self, task):
        """Process symbolic reasoning tasks"""
        # Implement symbolic processing
        return {
            "result": logical_result,
            "proof_steps": reasoning_trace,
            "confidence": certainty_level
        }
    
    def process_neural_symbolic_task(self, task):
        """Process neural-symbolic integration tasks"""
        # Implement hybrid processing
        return {
            "neural_representation": neural_output,
            "symbolic_explanation": symbolic_reasoning,
            "integration_quality": integration_score
        }
    
    def process_real_world_task(self, task):
        """Process real-world challenge tasks"""
        # Implement practical problem solving
        return {
            "solution": practical_solution,
            "execution_plan": action_sequence,
            "success_probability": likelihood
        }
    
    def get_system_info(self):
        """Return system information for tracking"""
        return {
            "name": self.name,
            "version": self.version,
            "architecture_type": "hybrid",  # neural, symbolic, hybrid
            "parameters": self.get_parameter_count(),
            "capabilities": self.list_capabilities()
        }
```

## Progress Tracking and Analysis

The suite includes comprehensive tracking and analysis tools:

### Progress Tracking

```python
from agi_components.tracking import ProgressTracker, SystemProfile

# Initialize tracker
tracker = ProgressTracker(config.tracking_config)

# Register your system
profile = SystemProfile(
    system_id="your_agi_v1",
    name="Your AGI System",
    version="1.0.0",
    architecture_type="hybrid",
    description="Description of your system",
    tags=["research", "experimental"],
    created_date=datetime.now()
)
tracker.register_system(profile)

# Results are automatically stored when running benchmarks
results = suite.benchmark_system(your_system)

# Query progress over time
progress = tracker.get_system_progress("your_agi_v1", days=30)

# Get leaderboards
leaderboard = tracker.get_leaderboard(category="reasoning", limit=10)

# Identify capability gaps
gaps = tracker.identify_capability_gaps("your_agi_v1")
```

### Analysis and Reporting

```python
from agi_components.analysis import BenchmarkAnalyzer

# Initialize analyzer
analyzer = BenchmarkAnalyzer(tracker)

# Compare systems
comparison = analyzer.compare_systems(results_a, results_b)

# Analyze trends
trend = analyzer.analyze_trends("your_agi_v1", metric="overall_score")

# Create capability profile
profile = analyzer.create_capability_profile(results)

# Generate comprehensive report
report = analyzer.generate_performance_report([results_a, results_b])
```

## Hyperon/PRIMUS Integration

The suite includes specific support for Hyperon and PRIMUS architectures:

### Hyperon Support

```python
# Enable Hyperon-specific tests
config.hyperon_enabled = True
config.hyperon_config = {
    "metta_interpreter": {
        "enabled": True,
        "reasoning_tests": True,
        "learning_tests": True
    },
    "atomspace_operations": {
        "enabled": True,
        "pattern_matching": True,
        "inference_control": True
    }
}

# The suite will automatically include Hyperon-specific benchmarks
```

### PRIMUS Support

```python
# Enable PRIMUS-specific tests
config.primus_enabled = True
config.primus_config = {
    "cognitive_architecture": {
        "enabled": True,
        "module_integration": True,
        "cognitive_cycles": True
    },
    "goal_oriented_behavior": {
        "enabled": True,
        "planning_tests": True,
        "execution_monitoring": True
    }
}
```

## Visualization and Reporting

The suite generates comprehensive visualizations and reports:

### Automatic Visualizations

- Overall performance comparison charts
- Capability radar charts
- Category performance heatmaps
- Progress trend graphs
- Capability gap analysis

### Report Generation

```python
# Generate HTML report
from agi_components.reporting import ReportGenerator

generator = ReportGenerator()
html_report = generator.generate_html_report(results, output_dir="reports")

# Generate PDF summary
pdf_report = generator.generate_pdf_summary(results, "summary.pdf")

# Export data for external analysis
generator.export_csv(results, "data.csv")
generator.export_json(results, "data.json")
```

## Best Practices

### System Implementation

1. **Modular Design**: Implement clear separation between different cognitive capabilities
2. **Error Handling**: Gracefully handle edge cases and unexpected inputs
3. **Resource Management**: Implement proper cleanup and resource management
4. **Logging**: Provide detailed logging for debugging and analysis
5. **Configuration**: Make your system configurable for different test scenarios

### Benchmarking

1. **Reproducibility**: Ensure consistent results across runs
2. **Hardware Considerations**: Test on multiple hardware configurations
3. **Baseline Comparison**: Compare against established baselines
4. **Statistical Significance**: Run multiple trials for reliable statistics
5. **Documentation**: Document system capabilities and limitations

### Analysis

1. **Multiple Metrics**: Don't rely on single performance metrics
2. **Temporal Analysis**: Track performance over time
3. **Capability Profiling**: Understand strengths and weaknesses
4. **Gap Analysis**: Identify areas for improvement
5. **Comparative Analysis**: Compare against other systems

## Contributing

We welcome contributions to the benchmark suite:

1. **New Benchmarks**: Propose additional test scenarios
2. **Improvements**: Enhance existing benchmark implementations
3. **Bug Fixes**: Report and fix issues
4. **Documentation**: Improve documentation and examples
5. **Analysis Tools**: Add new analysis and visualization capabilities

## Citation

If you use this benchmark suite in your research, please cite:

```bibtex
@software{agi_component_benchmark_suite,
  title={AGI Component Benchmark Suite},
  author={Kenny AGI Reproducibility Platform},
  year={2024},
  url={https://github.com/kenny-agi/agi-reproducibility/benchmarks/agi_components}
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions, suggestions, or collaborations, please contact:
- Email: contact@kenny-agi.org
- GitHub Issues: [Create an issue](https://github.com/kenny-agi/agi-reproducibility/issues)
- Documentation: [Full documentation](https://kenny-agi.org/docs/benchmarks)

## Acknowledgments

This benchmark suite was developed to address the need for objective AGI progress measurement as advocated by Ben Goertzel and the AGI research community. Special thanks to:

- The OpenCog and SingularityNET communities
- Hyperon and PRIMUS development teams
- AGI researchers and practitioners who provided feedback
- The broader AI safety and alignment community

---

*The AGI Component Benchmark Suite - Measuring genuine progress toward Artificial General Intelligence*