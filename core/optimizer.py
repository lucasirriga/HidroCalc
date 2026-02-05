import random
import copy
from typing import List, Dict, Callable
from .constants import VALID_DNS, PIPE_COSTS

class GeneticOptimizer:
    def __init__(self, solver, population_size=50, generations=100, mutation_rate=0.1):
        self.solver = solver
        self.network = solver.network
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elitism_count = 2
        
        # Identify optimizable links (pipes, not hoses if fixed)
        # For now, we optimize all links that are not 'hose' or we can optimize everything.
        # Usually hoses have fixed diameters (16/20), so let's focus on 'pipe' types or main lines.
        self.optimizable_links = [
            link for link in self.network.links.values() 
            if link.type != 'hose' # Assume hoses are fixed or optimized separately
        ]
        
        if not self.optimizable_links:
            # Fallback: if no pipes, maybe everything is a hose?
            self.optimizable_links = list(self.network.links.values())

    def optimize(self):
        """Runs the genetic algorithm to find the best diameter configuration."""
        if not self.optimizable_links:
            return

        # 1. Initialize Population
        population = self._initialize_population()
        
        best_solution = None
        best_fitness = float('inf')
        
        for gen in range(self.generations):
            # Evaluate Fitness
            fitness_scores = []
            for individual in population:
                fitness = self._evaluate_fitness(individual)
                fitness_scores.append((fitness, individual))
                
                if fitness < best_fitness:
                    best_fitness = fitness
                    best_solution = individual
            
            # Sort by fitness (lower is better)
            fitness_scores.sort(key=lambda x: x[0])
            
            # Elitism
            new_population = [x[1] for x in fitness_scores[:self.elitism_count]]
            
            # Selection & Reproduction
            while len(new_population) < self.population_size:
                parent1 = self._tournament_selection(fitness_scores)
                parent2 = self._tournament_selection(fitness_scores)
                
                child = self._crossover(parent1, parent2)
                child = self._mutate(child)
                new_population.append(child)
                
            population = new_population
            
            # Optional: Print progress
            # print(f"Gen {gen}: Best Fitness = {best_fitness}")

        # Apply best solution
        if best_solution:
            self._apply_solution(best_solution)
            # Final calculation to ensure network state is consistent
            self._recalculate_hydraulics()

    def _initialize_population(self) -> List[List[int]]:
        """Creates random initial population."""
        population = []
        num_links = len(self.optimizable_links)
        num_options = len(VALID_DNS)
        
        for _ in range(self.population_size):
            # Random gene: index of VALID_DNS
            individual = [random.randint(0, num_options - 1) for _ in range(num_links)]
            population.append(individual)
            
        return population

    def _evaluate_fitness(self, individual: List[int]) -> float:
        """Calculates cost + penalty for an individual."""
        # 1. Apply diameters
        self._apply_solution(individual)
        
        # 2. Run Hydraulic Calculation
        self._recalculate_hydraulics()
        
        # 3. Calculate Cost
        total_cost = 0.0
        for link in self.optimizable_links:
            dn = link.diameter
            cost_per_m = PIPE_COSTS.get(dn, 1.0)
            total_cost += link.length * cost_per_m
            
        # 4. Calculate Penalty (Pressure Violation)
        penalty = 0.0
        min_pressure_limit = self.solver.min_pressure
        
        # Check pressure at all relevant nodes (valves, emitters, junctions)
        # We can iterate all nodes to be safe
        for node in self.network.nodes.values():
            # Only care about nodes that need pressure (emitters, valves)
            # Or just ensure positive pressure everywhere?
            # Let's enforce min_pressure at emitters/valves
            if node.type in ['emitter', 'valve']:
                if node.pressure < min_pressure_limit:
                    diff = min_pressure_limit - node.pressure
                    penalty += diff * diff * 1000 # Heavy quadratic penalty
        
        return total_cost + penalty

    def _apply_solution(self, individual: List[int]):
        """Applies the genotype (diameter indices) to the network links."""
        for i, link in enumerate(self.optimizable_links):
            dn_index = individual[i]
            link.diameter = VALID_DNS[dn_index]

    def _recalculate_hydraulics(self):
        """Triggers the solver to update head losses and pressures."""
        # We assume flow is already distributed (steady state flow)
        # So we only need to update head loss (depends on D) and Pressure (depends on HF)
        
        for link in self.network.links.values():
            self.solver._update_head_loss(link)
            
        self.solver._calculate_pressure()

    def _tournament_selection(self, fitness_scores, k=3):
        """Selects the best individual from k random samples."""
        candidates = random.sample(fitness_scores, k)
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def _crossover(self, parent1, parent2):
        """Single point crossover."""
        if len(parent1) < 2:
            return parent1
            
        point = random.randint(1, len(parent1) - 1)
        child = parent1[:point] + parent2[point:]
        return child

    def _mutate(self, individual):
        """Randomly changes genes."""
        num_options = len(VALID_DNS)
        for i in range(len(individual)):
            if random.random() < self.mutation_rate:
                individual[i] = random.randint(0, num_options - 1)
        return individual
