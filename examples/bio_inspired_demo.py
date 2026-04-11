#!/usr/bin/env python3
"""
Demonstrate bio-inspired evolutionary optimization:
- Run evolutionary optimization on a simple fitness function
- Show convergence over generations
- Display population diversity and adaptive parameters

Requires: numpy
"""

import asyncio
import numpy as np

from asi_build.bio_inspired.evolutionary.evolutionary_optimizer import (
    EvolutionaryOptimizer,
    OptimizationMethod,
    FitnessFunction,
    Individual,
    Population,
)

print("=" * 60)
print("Bio-Inspired Evolutionary Optimization Demo")
print("=" * 60)


# --- Define a simple fitness function ---
# We'll maximize the Rastrigin function's negative (i.e., minimize Rastrigin).
# Rastrigin: f(x) = 10n + Σ[x_i² - 10·cos(2π·x_i)]
# Global minimum at x = (0, 0, ..., 0) with f = 0.

class RastriginFitness(FitnessFunction):
    """Fitness = 1 / (1 + rastrigin(genome)).  Higher is better."""

    async def evaluate(self, individual: Individual) -> float:
        genome = np.array(individual.genome)
        n = len(genome)
        rastrigin = 10 * n + np.sum(genome ** 2 - 10 * np.cos(2 * np.pi * genome))
        # Invert so fitness ∈ (0, 1], with 1.0 at the global optimum
        return 1.0 / (1.0 + rastrigin)

    def get_objectives(self):
        return ["rastrigin_fitness"]


async def main():
    # --- Create the optimizer ---
    optimizer = EvolutionaryOptimizer(
        name="RastriginOptimizer",
        optimization_method=OptimizationMethod.GENETIC_ALGORITHM,
        population_size=50,
        fitness_function=RastriginFitness(),
        config={
            "mutation_rate": 0.05,
            "crossover_rate": 0.8,
            "selection_pressure": 0.2,
            "elitism_rate": 0.1,
            "convergence_threshold": 1e-8,
            "max_stagnation_generations": 100,
            "archive_size": 50,
            "adaptive_mutation": True,
            "adaptive_crossover": True,
            "tournament_size": 5,
            "max_generations": 200,
            "genome_length": 10,            # 10-dimensional search
            "genome_bounds": (-5.12, 5.12), # Rastrigin bounds
            "diversity_threshold": 0.01,
            "niching_enabled": False,
            "speciation_threshold": 0.1,
        },
    )

    print(f"\nOptimization target: minimize 10-D Rastrigin function")
    print(f"Population size   : {optimizer.population_size}")
    print(f"Genome length     : {optimizer.config['genome_length']}")
    print(f"Method            : {optimizer.optimization_method.value}")
    print(f"\n{'Gen':>4s}  {'Best':>8s}  {'Mean':>8s}  {'Diversity':>9s}  {'MutRate':>8s}")
    print("-" * 46)

    # --- Run evolution for several generations ---
    num_generations = 30
    for gen in range(num_generations):
        result = await optimizer.process({
            "optimization_target": "rastrigin_minimum",
            "evaluation_data": {},
            "control_signals": {},
        })

        if gen % 5 == 0 or gen == num_generations - 1:
            print(f"{result['generation']:4d}  "
                  f"{result['best_fitness']:8.5f}  "
                  f"{result['mean_fitness']:8.5f}  "
                  f"{result['diversity']:9.4f}  "
                  f"{optimizer.mutation_rate:8.5f}")

    # --- Final results ---
    best = optimizer.population.best_individual
    print(f"\n--- Final result after {optimizer.generation_count} generations ---")
    print(f"Best fitness : {best.fitness:.6f}  (1.0 = global optimum)")
    genome = np.array(best.genome)
    print(f"Best genome  : mean={genome.mean():.4f}, std={genome.std():.4f}")
    print(f"  (optimal genome is all zeros)")

    rastrigin_val = 10 * len(genome) + np.sum(genome ** 2 - 10 * np.cos(2 * np.pi * genome))
    print(f"Rastrigin(x) : {rastrigin_val:.4f}  (optimal = 0.0)")

    # --- Show convergence check ---
    convergence = result["convergence_status"]
    print(f"\nConvergence  : {'Yes' if convergence['converged'] else 'No'}")
    print(f"Stagnation   : {convergence['stagnation_generations']} generations")

    progress = optimizer._get_optimization_progress()
    print(f"Total evals  : {progress.get('total_evaluations', '?')}")
    print(f"Improvement  : {progress.get('fitness_improvement', 0):.6f}")


asyncio.run(main())

print("\n✅ Bio-inspired optimization demo complete.")
