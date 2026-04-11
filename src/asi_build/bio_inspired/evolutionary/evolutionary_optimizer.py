"""
Evolutionary Optimizer Module

Main evolutionary optimization framework that integrates genetic algorithms,
genetic programming, and evolutionary strategies for adaptive optimization
of bio-inspired cognitive architectures.
"""

import asyncio
import copy
import logging
import pickle
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

from ..core import BioCognitiveModule, BiologicalMetrics

logger = logging.getLogger(__name__)


class OptimizationMethod(Enum):
    """Evolutionary optimization methods"""

    GENETIC_ALGORITHM = "genetic_algorithm"
    GENETIC_PROGRAMMING = "genetic_programming"
    EVOLUTIONARY_STRATEGY = "evolutionary_strategy"
    DIFFERENTIAL_EVOLUTION = "differential_evolution"
    PARTICLE_SWARM = "particle_swarm"
    MULTI_OBJECTIVE = "multi_objective"


@dataclass
class Individual:
    """Represents an individual in the evolutionary population"""

    genome: Union[List[float], Dict[str, Any]]
    fitness: float = 0.0
    age: int = 0
    generation: int = 0
    phenotype: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def copy(self):
        """Create a deep copy of the individual"""
        return Individual(
            genome=copy.deepcopy(self.genome),
            fitness=self.fitness,
            age=self.age,
            generation=self.generation,
            phenotype=copy.deepcopy(self.phenotype),
            metadata=copy.deepcopy(self.metadata),
        )


class FitnessFunction(ABC):
    """Abstract base class for fitness functions"""

    @abstractmethod
    async def evaluate(self, individual: Individual) -> float:
        """Evaluate fitness of an individual"""
        pass

    @abstractmethod
    def get_objectives(self) -> List[str]:
        """Get list of optimization objectives"""
        pass


class BiologicalFitnessFunction(FitnessFunction):
    """
    Biological fitness function for cognitive architectures

    Evaluates fitness based on biological plausibility metrics such as
    energy efficiency, processing speed, adaptability, and robustness.
    """

    def __init__(self, objectives: List[str] = None, weights: Dict[str, float] = None):

        self.objectives = objectives or [
            "energy_efficiency",
            "processing_speed",
            "adaptability",
            "robustness",
            "learning_capacity",
            "generalization",
        ]

        self.weights = weights or {
            "energy_efficiency": 0.25,
            "processing_speed": 0.20,
            "adaptability": 0.20,
            "robustness": 0.15,
            "learning_capacity": 0.15,
            "generalization": 0.05,
        }

        # Normalize weights
        total_weight = sum(self.weights.values())
        self.weights = {k: v / total_weight for k, v in self.weights.items()}

    async def evaluate(self, individual: Individual) -> float:
        """Evaluate biological fitness of individual"""
        if individual.phenotype is None:
            return 0.0

        fitness_components = {}

        # Energy efficiency
        fitness_components["energy_efficiency"] = self._evaluate_energy_efficiency(individual)

        # Processing speed
        fitness_components["processing_speed"] = self._evaluate_processing_speed(individual)

        # Adaptability
        fitness_components["adaptability"] = self._evaluate_adaptability(individual)

        # Robustness
        fitness_components["robustness"] = self._evaluate_robustness(individual)

        # Learning capacity
        fitness_components["learning_capacity"] = self._evaluate_learning_capacity(individual)

        # Generalization
        fitness_components["generalization"] = self._evaluate_generalization(individual)

        # Weighted combination
        total_fitness = sum(
            self.weights.get(obj, 0.0) * fitness_components.get(obj, 0.0) for obj in self.objectives
        )

        # Store component scores in metadata
        individual.metadata["fitness_components"] = fitness_components

        return np.clip(total_fitness, 0.0, 1.0)

    def _evaluate_energy_efficiency(self, individual: Individual) -> float:
        """Evaluate energy efficiency (higher is better)"""
        phenotype = individual.phenotype

        if hasattr(phenotype, "get_biological_metrics"):
            metrics = phenotype.get_biological_metrics()
            return metrics.energy_efficiency

        # Simulate energy efficiency based on genome
        if isinstance(individual.genome, dict):
            complexity = len(individual.genome)
            efficiency = 1.0 / (1.0 + complexity * 0.01)
            return efficiency

        return 0.5  # Default moderate efficiency

    def _evaluate_processing_speed(self, individual: Individual) -> float:
        """Evaluate processing speed (higher is better)"""
        phenotype = individual.phenotype

        if hasattr(phenotype, "get_processing_time"):
            processing_time = phenotype.get_processing_time()
            speed = 1.0 / (1.0 + processing_time)
            return np.clip(speed, 0.0, 1.0)

        # Simulate based on genome complexity
        if isinstance(individual.genome, list):
            complexity = len(individual.genome)
            speed = 1.0 / (1.0 + complexity * 0.001)
            return np.clip(speed, 0.0, 1.0)

        return 0.5

    def _evaluate_adaptability(self, individual: Individual) -> float:
        """Evaluate adaptability (higher is better)"""
        phenotype = individual.phenotype

        if hasattr(phenotype, "get_biological_metrics"):
            metrics = phenotype.get_biological_metrics()
            return metrics.plasticity_index

        # Simulate adaptability based on genome diversity
        if isinstance(individual.genome, list):
            diversity = np.std(individual.genome) if len(individual.genome) > 1 else 0.0
            adaptability = min(1.0, diversity / 10.0)
            return adaptability

        return 0.5

    def _evaluate_robustness(self, individual: Individual) -> float:
        """Evaluate robustness to noise and perturbations"""
        # Simulate by adding noise to genome and measuring stability
        if isinstance(individual.genome, list):
            original_genome = np.array(individual.genome)
            noisy_genome = original_genome + np.random.normal(0, 0.1, len(original_genome))

            # Robustness is inverse of sensitivity to noise
            sensitivity = np.mean(np.abs(noisy_genome - original_genome))
            robustness = 1.0 / (1.0 + sensitivity * 10)
            return robustness

        return 0.5

    def _evaluate_learning_capacity(self, individual: Individual) -> float:
        """Evaluate learning and memory capacity"""
        phenotype = individual.phenotype

        if hasattr(phenotype, "get_learning_metrics"):
            learning_metrics = phenotype.get_learning_metrics()
            return learning_metrics.get("capacity", 0.5)

        # Simulate based on age and experience
        age_factor = min(1.0, individual.age / 100.0)
        experience_factor = min(1.0, individual.generation / 50.0)
        learning_capacity = 0.5 * (age_factor + experience_factor)

        return learning_capacity

    def _evaluate_generalization(self, individual: Individual) -> float:
        """Evaluate generalization ability"""
        # Simulate based on genome complexity and structure
        if isinstance(individual.genome, dict):
            structure_complexity = len(individual.genome)
            balance = 1.0 / (1.0 + abs(structure_complexity - 10))  # Optimal around 10 components
            return balance

        return 0.5

    def get_objectives(self) -> List[str]:
        """Get optimization objectives"""
        return self.objectives


class Population:
    """Manages a population of individuals for evolutionary optimization"""

    def __init__(self, size: int = 100, individuals: Optional[List[Individual]] = None):

        self.size = size
        self.individuals = individuals or []
        self.generation = 0
        self.best_individual = None
        self.fitness_history = deque(maxlen=1000)
        self.diversity_history = deque(maxlen=1000)

    def add_individual(self, individual: Individual):
        """Add individual to population"""
        individual.generation = self.generation
        self.individuals.append(individual)

        # Update best individual
        if self.best_individual is None or individual.fitness > self.best_individual.fitness:
            self.best_individual = individual.copy()

    def get_best_individuals(self, n: int = 10) -> List[Individual]:
        """Get top n individuals by fitness"""
        sorted_individuals = sorted(self.individuals, key=lambda x: x.fitness, reverse=True)
        return sorted_individuals[:n]

    def get_worst_individuals(self, n: int = 10) -> List[Individual]:
        """Get bottom n individuals by fitness"""
        sorted_individuals = sorted(self.individuals, key=lambda x: x.fitness)
        return sorted_individuals[:n]

    def calculate_diversity(self) -> float:
        """Calculate population diversity"""
        if len(self.individuals) < 2:
            return 0.0

        # Calculate pairwise distances between genomes
        distances = []
        for i in range(len(self.individuals)):
            for j in range(i + 1, len(self.individuals)):
                distance = self._genome_distance(
                    self.individuals[i].genome, self.individuals[j].genome
                )
                distances.append(distance)

        return np.mean(distances) if distances else 0.0

    def _genome_distance(self, genome1: Union[List, Dict], genome2: Union[List, Dict]) -> float:
        """Calculate distance between two genomes"""
        if isinstance(genome1, list) and isinstance(genome2, list):
            if len(genome1) != len(genome2):
                return 1.0
            return np.linalg.norm(np.array(genome1) - np.array(genome2))

        elif isinstance(genome1, dict) and isinstance(genome2, dict):
            # Jaccard distance for dictionaries
            keys1 = set(genome1.keys())
            keys2 = set(genome2.keys())
            intersection = len(keys1.intersection(keys2))
            union = len(keys1.union(keys2))

            if union == 0:
                return 0.0

            return 1.0 - (intersection / union)

        return 1.0  # Different types

    def update_statistics(self):
        """Update population statistics"""
        if self.individuals:
            fitnesses = [ind.fitness for ind in self.individuals]
            self.fitness_history.append(
                {
                    "generation": self.generation,
                    "mean_fitness": np.mean(fitnesses),
                    "max_fitness": np.max(fitnesses),
                    "min_fitness": np.min(fitnesses),
                    "std_fitness": np.std(fitnesses),
                }
            )

            diversity = self.calculate_diversity()
            self.diversity_history.append({"generation": self.generation, "diversity": diversity})

    def evolve_generation(self):
        """Advance to next generation"""
        self.generation += 1

        # Age all individuals
        for individual in self.individuals:
            individual.age += 1

        self.update_statistics()


class EvolutionaryOptimizer(BioCognitiveModule):
    """
    Main Evolutionary Optimizer

    Implements various evolutionary algorithms for optimizing bio-inspired
    cognitive architectures using biological evolution principles.
    """

    def __init__(
        self,
        name: str = "EvolutionaryOptimizer",
        optimization_method: OptimizationMethod = OptimizationMethod.GENETIC_ALGORITHM,
        population_size: int = 100,
        fitness_function: Optional[FitnessFunction] = None,
        config: Optional[Dict[str, Any]] = None,
    ):

        super().__init__(name)

        self.optimization_method = optimization_method
        self.population_size = population_size
        self.fitness_function = fitness_function or BiologicalFitnessFunction()
        self.config = config or self._get_default_config()

        # Initialize population
        self.population = Population(size=population_size)

        # Evolution parameters
        self.mutation_rate = self.config["mutation_rate"]
        self.crossover_rate = self.config["crossover_rate"]
        self.selection_pressure = self.config["selection_pressure"]
        self.elitism_rate = self.config["elitism_rate"]

        # Evolution tracking
        self.generation_count = 0
        self.evaluation_count = 0
        self.convergence_threshold = self.config["convergence_threshold"]
        self.stagnation_generations = 0
        self.max_stagnation = self.config["max_stagnation_generations"]

        # Multi-objective optimization
        self.pareto_front = []
        self.archive_size = self.config["archive_size"]

        # Adaptive parameters
        self.adaptive_mutation = self.config["adaptive_mutation"]
        self.adaptive_crossover = self.config["adaptive_crossover"]

        logger.info(f"Initialized evolutionary optimizer with {optimization_method.value} method")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "mutation_rate": 0.01,
            "crossover_rate": 0.8,
            "selection_pressure": 0.2,
            "elitism_rate": 0.1,
            "convergence_threshold": 1e-6,
            "max_stagnation_generations": 50,
            "archive_size": 100,
            "adaptive_mutation": True,
            "adaptive_crossover": True,
            "tournament_size": 5,
            "max_generations": 1000,
            "genome_length": 50,
            "genome_bounds": (-10.0, 10.0),
            "diversity_threshold": 0.01,
            "niching_enabled": True,
            "speciation_threshold": 0.1,
        }

    async def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process evolutionary optimization step"""
        optimization_target = inputs.get("optimization_target")
        evaluation_data = inputs.get("evaluation_data", {})
        control_signals = inputs.get("control_signals", {})

        # Handle control signals
        await self._process_control_signals(control_signals)

        # Perform one generation of evolution
        evolution_result = await self._evolve_generation(optimization_target, evaluation_data)

        # Update metrics
        self._update_optimization_metrics()

        # Prepare output
        output = {
            "generation": self.generation_count,
            "population_size": len(self.population.individuals),
            "best_fitness": (
                self.population.best_individual.fitness if self.population.best_individual else 0.0
            ),
            "mean_fitness": (
                np.mean([ind.fitness for ind in self.population.individuals])
                if self.population.individuals
                else 0.0
            ),
            "diversity": self.population.calculate_diversity(),
            "convergence_status": self._check_convergence(),
            "pareto_front_size": len(self.pareto_front),
            "evolution_metrics": evolution_result,
            "best_individual": (
                self._serialize_individual(self.population.best_individual)
                if self.population.best_individual
                else None
            ),
            "optimization_progress": self._get_optimization_progress(),
        }

        return output

    async def _process_control_signals(self, control_signals: Dict[str, Any]):
        """Process control signals for optimization parameters"""
        for signal_type, signal_data in control_signals.items():
            if signal_type == "mutation_rate":
                self.mutation_rate = np.clip(signal_data, 0.001, 0.5)
            elif signal_type == "crossover_rate":
                self.crossover_rate = np.clip(signal_data, 0.1, 1.0)
            elif signal_type == "selection_pressure":
                self.selection_pressure = np.clip(signal_data, 0.05, 0.9)
            elif signal_type == "population_size":
                await self._adjust_population_size(int(signal_data))
            elif signal_type == "reset_population":
                await self._reset_population()

    async def _evolve_generation(
        self, optimization_target: Any, evaluation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform one generation of evolutionary optimization"""

        # Initialize population if empty
        if not self.population.individuals:
            await self._initialize_population(optimization_target)

        # Evaluate fitness for all individuals
        await self._evaluate_population(evaluation_data)

        # Selection
        parents = self._selection()

        # Create offspring through crossover and mutation
        offspring = await self._create_offspring(parents)

        # Evaluate offspring
        await self._evaluate_individuals(offspring, evaluation_data)

        # Survival selection (replacement)
        new_population = self._survival_selection(parents + offspring)

        # Update population
        self.population.individuals = new_population
        self.population.evolve_generation()
        self.generation_count += 1

        # Update Pareto front for multi-objective optimization
        if self.optimization_method == OptimizationMethod.MULTI_OBJECTIVE:
            self._update_pareto_front()

        # Adaptive parameter adjustment
        if self.adaptive_mutation or self.adaptive_crossover:
            self._adapt_parameters()

        return {
            "parents_count": len(parents),
            "offspring_count": len(offspring),
            "survivors_count": len(new_population),
            "evaluations_performed": len(offspring),
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate,
        }

    async def _initialize_population(self, optimization_target: Any):
        """Initialize population with random individuals"""
        for i in range(self.population_size):
            individual = self._create_random_individual(optimization_target)
            self.population.add_individual(individual)

        logger.info(f"Initialized population with {len(self.population.individuals)} individuals")

    def _create_random_individual(self, optimization_target: Any) -> Individual:
        """Create a random individual"""
        if self.optimization_method == OptimizationMethod.GENETIC_PROGRAMMING:
            # Create random program tree
            genome = self._create_random_program_tree()
        else:
            # Create random parameter vector
            genome_length = self.config["genome_length"]
            bounds = self.config["genome_bounds"]
            genome = np.random.uniform(bounds[0], bounds[1], genome_length).tolist()

        individual = Individual(genome=genome, generation=self.generation_count)

        # Create phenotype from genome
        individual.phenotype = self._genome_to_phenotype(individual.genome, optimization_target)

        return individual

    def _create_random_program_tree(self, max_depth: int = 5) -> Dict[str, Any]:
        """Create random program tree for genetic programming"""
        functions = ["add", "sub", "mul", "div", "sin", "cos", "exp", "log"]
        terminals = ["x", "y", "z", "1.0", "0.5", "2.0", "pi"]

        def create_node(depth: int = 0):
            if depth >= max_depth or (depth > 0 and np.random.random() < 0.3):
                # Create terminal node
                return {"type": "terminal", "value": np.random.choice(terminals)}
            else:
                # Create function node
                func = np.random.choice(functions)
                if func in ["sin", "cos", "exp", "log"]:
                    # Unary function
                    return {
                        "type": "function",
                        "function": func,
                        "children": [create_node(depth + 1)],
                    }
                else:
                    # Binary function
                    return {
                        "type": "function",
                        "function": func,
                        "children": [create_node(depth + 1), create_node(depth + 1)],
                    }

        return create_node()

    def _genome_to_phenotype(self, genome: Union[List, Dict], optimization_target: Any) -> Any:
        """Convert genome to phenotype"""
        # This would be implemented based on the specific optimization target
        # For now, return a simple wrapper
        return {
            "genome": genome,
            "target": optimization_target,
            "parameters": self._decode_parameters(genome),
        }

    def _decode_parameters(self, genome: Union[List, Dict]) -> Dict[str, Any]:
        """Decode genome into parameter dictionary"""
        if isinstance(genome, list):
            # Simple parameter encoding
            return {f"param_{i}": value for i, value in enumerate(genome)}
        else:
            return genome

    async def _evaluate_population(self, evaluation_data: Dict[str, Any]):
        """Evaluate fitness for entire population"""
        evaluation_tasks = []

        for individual in self.population.individuals:
            if individual.fitness == 0.0:  # Only evaluate if not already evaluated
                task = self._evaluate_individual(individual, evaluation_data)
                evaluation_tasks.append(task)

        if evaluation_tasks:
            await asyncio.gather(*evaluation_tasks)

    async def _evaluate_individuals(
        self, individuals: List[Individual], evaluation_data: Dict[str, Any]
    ):
        """Evaluate fitness for list of individuals"""
        evaluation_tasks = [
            self._evaluate_individual(individual, evaluation_data) for individual in individuals
        ]

        await asyncio.gather(*evaluation_tasks)

    async def _evaluate_individual(self, individual: Individual, evaluation_data: Dict[str, Any]):
        """Evaluate fitness for single individual"""
        try:
            individual.fitness = await self.fitness_function.evaluate(individual)
            self.evaluation_count += 1
        except Exception as e:
            logger.error(f"Error evaluating individual: {e}")
            individual.fitness = 0.0

    def _selection(self) -> List[Individual]:
        """Select parents for reproduction"""
        if self.optimization_method == OptimizationMethod.GENETIC_ALGORITHM:
            return self._tournament_selection()
        elif self.optimization_method == OptimizationMethod.GENETIC_PROGRAMMING:
            return self._fitness_proportionate_selection()
        else:
            return self._rank_selection()

    def _tournament_selection(self) -> List[Individual]:
        """Tournament selection"""
        parents = []
        tournament_size = self.config["tournament_size"]
        num_parents = int(len(self.population.individuals) * self.crossover_rate)

        for _ in range(num_parents):
            tournament = np.random.choice(
                self.population.individuals,
                size=min(tournament_size, len(self.population.individuals)),
                replace=False,
            )
            winner = max(tournament, key=lambda x: x.fitness)
            parents.append(winner.copy())

        return parents

    def _fitness_proportionate_selection(self) -> List[Individual]:
        """Fitness proportionate (roulette wheel) selection"""
        parents = []
        num_parents = int(len(self.population.individuals) * self.crossover_rate)

        # Calculate selection probabilities
        fitnesses = np.array([ind.fitness for ind in self.population.individuals])
        fitnesses = fitnesses - np.min(fitnesses) + 1e-6  # Ensure positive
        probabilities = fitnesses / np.sum(fitnesses)

        # Select parents
        selected_indices = np.random.choice(
            len(self.population.individuals), size=num_parents, p=probabilities, replace=True
        )

        for idx in selected_indices:
            parents.append(self.population.individuals[idx].copy())

        return parents

    def _rank_selection(self) -> List[Individual]:
        """Rank-based selection"""
        parents = []
        num_parents = int(len(self.population.individuals) * self.crossover_rate)

        # Sort by fitness
        sorted_individuals = sorted(
            self.population.individuals, key=lambda x: x.fitness, reverse=True
        )

        # Linear ranking
        ranks = np.arange(len(sorted_individuals), 0, -1)
        probabilities = ranks / np.sum(ranks)

        # Select parents
        selected_indices = np.random.choice(
            len(sorted_individuals), size=num_parents, p=probabilities, replace=True
        )

        for idx in selected_indices:
            parents.append(sorted_individuals[idx].copy())

        return parents

    async def _create_offspring(self, parents: List[Individual]) -> List[Individual]:
        """Create offspring through crossover and mutation"""
        offspring = []

        # Pair up parents for crossover
        np.random.shuffle(parents)

        for i in range(0, len(parents) - 1, 2):
            parent1 = parents[i]
            parent2 = parents[i + 1] if i + 1 < len(parents) else parents[0]

            if np.random.random() < self.crossover_rate:
                # Perform crossover
                child1, child2 = self._crossover(parent1, parent2)
            else:
                # No crossover - just copy parents
                child1, child2 = parent1.copy(), parent2.copy()

            # Apply mutation
            if np.random.random() < self.mutation_rate:
                self._mutate(child1)
            if np.random.random() < self.mutation_rate:
                self._mutate(child2)

            # Update phenotypes
            child1.phenotype = self._genome_to_phenotype(child1.genome, None)
            child2.phenotype = self._genome_to_phenotype(child2.genome, None)

            offspring.extend([child1, child2])

        return offspring

    def _crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """Perform crossover between two parents"""
        child1 = parent1.copy()
        child2 = parent2.copy()

        if isinstance(parent1.genome, list) and isinstance(parent2.genome, list):
            # Single-point crossover for list genomes
            if len(parent1.genome) == len(parent2.genome) and len(parent1.genome) > 1:
                crossover_point = np.random.randint(1, len(parent1.genome))

                child1.genome = parent1.genome[:crossover_point] + parent2.genome[crossover_point:]
                child2.genome = parent2.genome[:crossover_point] + parent1.genome[crossover_point:]

        elif isinstance(parent1.genome, dict) and isinstance(parent2.genome, dict):
            # Uniform crossover for dict genomes
            all_keys = set(parent1.genome.keys()) | set(parent2.genome.keys())

            for key in all_keys:
                if np.random.random() < 0.5:
                    if key in parent1.genome:
                        child1.genome[key] = parent1.genome[key]
                    if key in parent2.genome:
                        child2.genome[key] = parent2.genome[key]
                else:
                    if key in parent2.genome:
                        child1.genome[key] = parent2.genome[key]
                    if key in parent1.genome:
                        child2.genome[key] = parent1.genome[key]

        # Reset fitness (will be evaluated later)
        child1.fitness = 0.0
        child2.fitness = 0.0
        child1.generation = self.generation_count + 1
        child2.generation = self.generation_count + 1

        return child1, child2

    def _mutate(self, individual: Individual):
        """Apply mutation to an individual"""
        if isinstance(individual.genome, list):
            # Gaussian mutation for numeric genomes
            for i in range(len(individual.genome)):
                if np.random.random() < self.mutation_rate:
                    mutation_strength = 0.1 * (
                        self.config["genome_bounds"][1] - self.config["genome_bounds"][0]
                    )
                    individual.genome[i] += np.random.normal(0, mutation_strength)

                    # Clamp to bounds
                    individual.genome[i] = np.clip(
                        individual.genome[i],
                        self.config["genome_bounds"][0],
                        self.config["genome_bounds"][1],
                    )

        elif isinstance(individual.genome, dict):
            # Mutation for structured genomes
            for key, value in individual.genome.items():
                if np.random.random() < self.mutation_rate:
                    if isinstance(value, (int, float)):
                        individual.genome[key] = value + np.random.normal(
                            0, abs(value) * 0.1 + 0.01
                        )
                    elif isinstance(value, str):
                        # Simple string mutation (not implemented)
                        pass

        # Reset fitness
        individual.fitness = 0.0

    def _survival_selection(self, candidates: List[Individual]) -> List[Individual]:
        """Select survivors for next generation"""
        # Sort by fitness
        sorted_candidates = sorted(candidates, key=lambda x: x.fitness, reverse=True)

        # Elitism: always keep best individuals
        num_elite = int(self.population_size * self.elitism_rate)
        survivors = sorted_candidates[:num_elite]

        # Fill remaining spots
        remaining_spots = self.population_size - num_elite
        if remaining_spots > 0:
            # Tournament selection for remaining spots
            for _ in range(remaining_spots):
                tournament_size = min(5, len(sorted_candidates))
                tournament = np.random.choice(
                    sorted_candidates, size=tournament_size, replace=False
                )
                winner = max(tournament, key=lambda x: x.fitness)
                survivors.append(winner)

        return survivors[: self.population_size]

    def _update_pareto_front(self):
        """Update Pareto front for multi-objective optimization"""
        # Get all individuals with fitness components
        candidates = [
            ind for ind in self.population.individuals if "fitness_components" in ind.metadata
        ]

        # Find non-dominated individuals
        pareto_individuals = []
        for candidate in candidates:
            is_dominated = False
            candidate_objectives = list(candidate.metadata["fitness_components"].values())

            for other in candidates:
                if other == candidate:
                    continue

                other_objectives = list(other.metadata["fitness_components"].values())

                # Check if other dominates candidate
                if self._dominates(other_objectives, candidate_objectives):
                    is_dominated = True
                    break

            if not is_dominated:
                pareto_individuals.append(candidate)

        # Update Pareto front
        self.pareto_front = pareto_individuals[: self.archive_size]

    def _dominates(self, obj1: List[float], obj2: List[float]) -> bool:
        """Check if obj1 dominates obj2 (assuming maximization)"""
        if len(obj1) != len(obj2):
            return False

        at_least_one_better = False
        for o1, o2 in zip(obj1, obj2):
            if o1 < o2:
                return False
            elif o1 > o2:
                at_least_one_better = True

        return at_least_one_better

    def _adapt_parameters(self):
        """Adapt evolutionary parameters based on progress"""
        if len(self.population.fitness_history) < 10:
            return

        # Get recent fitness progress
        recent_history = list(self.population.fitness_history)[-10:]
        fitness_trend = recent_history[-1]["mean_fitness"] - recent_history[0]["mean_fitness"]

        # Adapt mutation rate
        if self.adaptive_mutation:
            if fitness_trend < self.convergence_threshold:
                # Increase mutation if stagnating
                self.mutation_rate = min(0.1, self.mutation_rate * 1.1)
            else:
                # Decrease mutation if improving
                self.mutation_rate = max(0.001, self.mutation_rate * 0.95)

        # Adapt crossover rate
        if self.adaptive_crossover:
            diversity = self.population.calculate_diversity()
            if diversity < self.config["diversity_threshold"]:
                # Increase crossover to promote diversity
                self.crossover_rate = min(1.0, self.crossover_rate * 1.05)
            else:
                # Normal crossover rate
                self.crossover_rate = max(0.1, self.crossover_rate * 0.98)

    def _check_convergence(self) -> Dict[str, Any]:
        """Check convergence status"""
        if len(self.population.fitness_history) < 10:
            return {"converged": False, "reason": "insufficient_data"}

        recent_history = list(self.population.fitness_history)[-10:]
        fitness_change = recent_history[-1]["mean_fitness"] - recent_history[0]["mean_fitness"]

        if abs(fitness_change) < self.convergence_threshold:
            self.stagnation_generations += 1
        else:
            self.stagnation_generations = 0

        converged = self.stagnation_generations >= self.max_stagnation

        return {
            "converged": converged,
            "stagnation_generations": self.stagnation_generations,
            "fitness_change": fitness_change,
            "reason": "stagnation" if converged else "evolving",
        }

    def _update_optimization_metrics(self):
        """Update optimization-specific metrics"""
        if self.population.individuals:
            fitnesses = [ind.fitness for ind in self.population.individuals]

            self.metrics.energy_efficiency = np.mean(fitnesses)
            self.metrics.plasticity_index = self.population.calculate_diversity()

            # Update neurotransmitter levels based on optimization state
            progress_rate = self.stagnation_generations / self.max_stagnation
            self.metrics.neurotransmitter_levels = {
                "dopamine": max(0.1, 1.0 - progress_rate),  # Reward signal
                "norepinephrine": min(1.0, 0.5 + progress_rate),  # Arousal from stagnation
                "serotonin": 0.5,  # Baseline mood
                "acetylcholine": self.population.calculate_diversity(),  # Attention to diversity
            }

    def _get_optimization_progress(self) -> Dict[str, Any]:
        """Get detailed optimization progress"""
        if not self.population.fitness_history:
            return {}

        history = list(self.population.fitness_history)

        return {
            "total_generations": self.generation_count,
            "total_evaluations": self.evaluation_count,
            "current_best_fitness": history[-1]["max_fitness"] if history else 0.0,
            "initial_best_fitness": history[0]["max_fitness"] if history else 0.0,
            "fitness_improvement": (
                (history[-1]["max_fitness"] - history[0]["max_fitness"])
                if len(history) > 1
                else 0.0
            ),
            "convergence_rate": (
                abs(history[-1]["mean_fitness"] - history[-10]["mean_fitness"])
                if len(history) >= 10
                else 0.0
            ),
            "population_diversity": self.population.calculate_diversity(),
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate,
        }

    def _serialize_individual(self, individual: Individual) -> Dict[str, Any]:
        """Serialize individual for output"""
        return {
            "fitness": individual.fitness,
            "age": individual.age,
            "generation": individual.generation,
            "genome_summary": self._summarize_genome(individual.genome),
            "metadata": individual.metadata,
        }

    def _summarize_genome(self, genome: Union[List, Dict]) -> Dict[str, Any]:
        """Create summary of genome for output"""
        if isinstance(genome, list):
            return {
                "type": "vector",
                "length": len(genome),
                "mean": np.mean(genome) if genome else 0.0,
                "std": np.std(genome) if len(genome) > 1 else 0.0,
                "min": np.min(genome) if genome else 0.0,
                "max": np.max(genome) if genome else 0.0,
            }
        elif isinstance(genome, dict):
            return {"type": "structured", "keys": list(genome.keys()), "size": len(genome)}
        else:
            return {"type": "unknown"}

    async def _adjust_population_size(self, new_size: int):
        """Adjust population size"""
        new_size = max(10, min(1000, new_size))  # Reasonable bounds

        if new_size > len(self.population.individuals):
            # Add new random individuals
            for _ in range(new_size - len(self.population.individuals)):
                individual = self._create_random_individual(None)
                self.population.add_individual(individual)
        elif new_size < len(self.population.individuals):
            # Remove worst individuals
            sorted_individuals = sorted(
                self.population.individuals, key=lambda x: x.fitness, reverse=True
            )
            self.population.individuals = sorted_individuals[:new_size]

        self.population_size = new_size
        logger.info(f"Adjusted population size to {new_size}")

    async def _reset_population(self):
        """Reset population to random individuals"""
        self.population = Population(size=self.population_size)
        await self._initialize_population(None)
        self.generation_count = 0
        self.stagnation_generations = 0
        logger.info("Population reset")

    def get_biological_metrics(self) -> BiologicalMetrics:
        """Get biological metrics for evolutionary optimizer"""
        return self.metrics

    def update_parameters(self, learning_signal: float):
        """Update evolutionary parameters based on learning signal"""
        if learning_signal > 0.7:
            # High learning signal - increase exploration
            self.mutation_rate = min(0.1, self.mutation_rate * 1.1)
        elif learning_signal < 0.3:
            # Low learning signal - increase exploitation
            self.mutation_rate = max(0.001, self.mutation_rate * 0.9)

        # Adjust selection pressure based on learning
        if learning_signal > 0.5:
            self.selection_pressure = min(0.5, self.selection_pressure * 1.02)
        else:
            self.selection_pressure = max(0.1, self.selection_pressure * 0.98)

    def save_evolution_state(self, filepath: str):
        """Save evolutionary state to file"""
        state = {
            "generation_count": self.generation_count,
            "evaluation_count": self.evaluation_count,
            "population": {
                "individuals": [
                    {
                        "genome": ind.genome,
                        "fitness": ind.fitness,
                        "age": ind.age,
                        "generation": ind.generation,
                        "metadata": ind.metadata,
                    }
                    for ind in self.population.individuals
                ],
                "generation": self.population.generation,
                "fitness_history": list(self.population.fitness_history),
                "diversity_history": list(self.population.diversity_history),
            },
            "config": self.config,
            "pareto_front": [
                {"genome": ind.genome, "fitness": ind.fitness, "metadata": ind.metadata}
                for ind in self.pareto_front
            ],
            "optimization_method": self.optimization_method.value,
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate,
            "selection_pressure": self.selection_pressure,
        }

        with open(filepath, "wb") as f:
            pickle.dump(state, f)

        logger.info(f"Evolution state saved to {filepath}")

    def load_evolution_state(self, filepath: str):
        """Load evolutionary state from file"""
        with open(filepath, "rb") as f:
            state = pickle.load(f)

        self.generation_count = state["generation_count"]
        self.evaluation_count = state["evaluation_count"]
        self.config = state["config"]
        self.optimization_method = OptimizationMethod(state["optimization_method"])
        self.mutation_rate = state["mutation_rate"]
        self.crossover_rate = state["crossover_rate"]
        self.selection_pressure = state["selection_pressure"]

        # Restore population
        self.population = Population()
        self.population.generation = state["population"]["generation"]
        self.population.fitness_history = deque(state["population"]["fitness_history"], maxlen=1000)
        self.population.diversity_history = deque(
            state["population"]["diversity_history"], maxlen=1000
        )

        for ind_data in state["population"]["individuals"]:
            individual = Individual(
                genome=ind_data["genome"],
                fitness=ind_data["fitness"],
                age=ind_data["age"],
                generation=ind_data["generation"],
                metadata=ind_data["metadata"],
            )
            individual.phenotype = self._genome_to_phenotype(individual.genome, None)
            self.population.add_individual(individual)

        # Restore Pareto front
        self.pareto_front = []
        for pf_data in state["pareto_front"]:
            individual = Individual(
                genome=pf_data["genome"], fitness=pf_data["fitness"], metadata=pf_data["metadata"]
            )
            self.pareto_front.append(individual)

        logger.info(f"Evolution state loaded from {filepath}")


class MultiObjectiveOptimizer(EvolutionaryOptimizer):
    """
    Multi-objective evolutionary optimizer using NSGA-II algorithm
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, optimization_method=OptimizationMethod.MULTI_OBJECTIVE, **kwargs)
        self.crowding_distance_weight = 0.5

    def _survival_selection(self, candidates: List[Individual]) -> List[Individual]:
        """NSGA-II survival selection with non-dominated sorting and crowding distance"""
        # Perform non-dominated sorting
        fronts = self._non_dominated_sorting(candidates)

        survivors = []
        for front in fronts:
            if len(survivors) + len(front) <= self.population_size:
                # Include entire front
                survivors.extend(front)
            else:
                # Include partial front based on crowding distance
                remaining_spots = self.population_size - len(survivors)
                if remaining_spots > 0:
                    # Calculate crowding distances
                    self._calculate_crowding_distance(front)

                    # Sort by crowding distance (descending)
                    front.sort(key=lambda x: x.metadata.get("crowding_distance", 0), reverse=True)

                    survivors.extend(front[:remaining_spots])
                break

        return survivors

    def _non_dominated_sorting(self, individuals: List[Individual]) -> List[List[Individual]]:
        """Perform non-dominated sorting"""
        fronts = []

        # Initialize domination counts and dominated solutions
        for ind in individuals:
            ind.metadata["domination_count"] = 0
            ind.metadata["dominated_solutions"] = []

        # Calculate domination relationships
        for i, ind1 in enumerate(individuals):
            for j, ind2 in enumerate(individuals):
                if i != j:
                    if self._dominates_multi_objective(ind1, ind2):
                        ind1.metadata["dominated_solutions"].append(ind2)
                    elif self._dominates_multi_objective(ind2, ind1):
                        ind1.metadata["domination_count"] += 1

        # Create first front
        first_front = [ind for ind in individuals if ind.metadata["domination_count"] == 0]
        fronts.append(first_front)

        # Create subsequent fronts
        current_front = first_front
        while current_front:
            next_front = []
            for ind1 in current_front:
                for ind2 in ind1.metadata["dominated_solutions"]:
                    ind2.metadata["domination_count"] -= 1
                    if ind2.metadata["domination_count"] == 0:
                        next_front.append(ind2)

            if next_front:
                fronts.append(next_front)
            current_front = next_front

        return fronts

    def _dominates_multi_objective(self, ind1: Individual, ind2: Individual) -> bool:
        """Check if ind1 dominates ind2 in multi-objective space"""
        if "fitness_components" not in ind1.metadata or "fitness_components" not in ind2.metadata:
            return ind1.fitness > ind2.fitness

        obj1 = list(ind1.metadata["fitness_components"].values())
        obj2 = list(ind2.metadata["fitness_components"].values())

        return self._dominates(obj1, obj2)

    def _calculate_crowding_distance(self, front: List[Individual]):
        """Calculate crowding distance for individuals in a front"""
        if len(front) <= 2:
            for ind in front:
                ind.metadata["crowding_distance"] = float("inf")
            return

        # Initialize crowding distances
        for ind in front:
            ind.metadata["crowding_distance"] = 0.0

        # Get objective values
        if "fitness_components" in front[0].metadata:
            objectives = list(front[0].metadata["fitness_components"].keys())

            for obj in objectives:
                # Sort by this objective
                front.sort(key=lambda x: x.metadata["fitness_components"].get(obj, 0))

                # Set boundary individuals to infinite distance
                front[0].metadata["crowding_distance"] = float("inf")
                front[-1].metadata["crowding_distance"] = float("inf")

                # Calculate distances for intermediate individuals
                obj_range = front[-1].metadata["fitness_components"].get(obj, 0) - front[
                    0
                ].metadata["fitness_components"].get(obj, 0)

                if obj_range > 0:
                    for i in range(1, len(front) - 1):
                        distance = (
                            front[i + 1].metadata["fitness_components"].get(obj, 0)
                            - front[i - 1].metadata["fitness_components"].get(obj, 0)
                        ) / obj_range
                        front[i].metadata["crowding_distance"] += distance
