"""
Swarm Intelligence Visualization Tools

This module provides comprehensive visualization capabilities for
swarm intelligence algorithms, including real-time plotting,
animations, and performance dashboards.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    from matplotlib.patches import Circle
    from mpl_toolkits.mplot3d import Axes3D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from .base import SwarmOptimizer
from .metrics import BenchmarkResult


class SwarmVisualizer:
    """Comprehensive visualization system for swarm intelligence algorithms"""
    
    def __init__(self, use_plotly: bool = False):
        self.use_plotly = use_plotly and PLOTLY_AVAILABLE
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if not MATPLOTLIB_AVAILABLE and not PLOTLY_AVAILABLE:
            self.logger.warning("No visualization libraries available. Install matplotlib or plotly.")
    
    def plot_convergence(self, convergence_histories: Dict[str, List[float]], 
                        title: str = "Convergence Comparison",
                        save_path: Optional[str] = None) -> None:
        """Plot convergence curves for multiple algorithms"""
        if self.use_plotly:
            self._plotly_convergence(convergence_histories, title, save_path)
        else:
            self._matplotlib_convergence(convergence_histories, title, save_path)
    
    def _matplotlib_convergence(self, convergence_histories: Dict[str, List[float]], 
                               title: str, save_path: Optional[str]) -> None:
        """Matplotlib convergence plot"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        plt.figure(figsize=(12, 8))
        
        for algo_name, history in convergence_histories.items():
            plt.plot(history, label=algo_name, linewidth=2)
        
        plt.xlabel('Iteration')
        plt.ylabel('Best Fitness')
        plt.title(title)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.yscale('log')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        plt.close()
    
    def _plotly_convergence(self, convergence_histories: Dict[str, List[float]], 
                           title: str, save_path: Optional[str]) -> None:
        """Plotly convergence plot"""
        if not PLOTLY_AVAILABLE:
            return
        
        fig = go.Figure()
        
        for algo_name, history in convergence_histories.items():
            fig.add_trace(go.Scatter(
                y=history,
                mode='lines',
                name=algo_name,
                line=dict(width=2)
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title='Iteration',
            yaxis_title='Best Fitness',
            yaxis_type='log',
            hovermode='x unified'
        )
        
        if save_path:
            fig.write_html(save_path)
        else:
            fig.show()
    
    def plot_swarm_animation(self, swarm: SwarmOptimizer, 
                           objective_function,
                           iterations: int = 100,
                           save_path: Optional[str] = None) -> None:
        """Create animated visualization of swarm movement"""
        if not MATPLOTLIB_AVAILABLE or swarm.params.dimension != 2:
            self.logger.warning("Animation requires matplotlib and 2D problems")
            return
        
        # Initialize swarm
        swarm.initialize_population()
        
        # Collect animation data
        positions_history = []
        fitness_history = []
        
        for _ in range(iterations):
            swarm.update_agents(objective_function)
            
            positions = np.array([agent.position for agent in swarm.agents])
            positions_history.append(positions.copy())
            fitness_history.append(swarm.global_best_fitness)
        
        # Create animation
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Swarm plot
        ax1.set_xlim(swarm.params.bounds[0], swarm.params.bounds[1])
        ax1.set_ylim(swarm.params.bounds[0], swarm.params.bounds[1])
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_title('Swarm Movement')
        
        scatter = ax1.scatter([], [], s=50, alpha=0.7)
        best_point = ax1.scatter([], [], s=200, c='red', marker='*')
        
        # Convergence plot
        ax2.set_xlabel('Iteration')
        ax2.set_ylabel('Best Fitness')
        ax2.set_title('Convergence')
        ax2.set_yscale('log')
        
        line, = ax2.plot([], [], 'b-', linewidth=2)
        
        def animate(frame):
            # Update swarm positions
            positions = positions_history[frame]
            scatter.set_offsets(positions)
            
            # Update best position
            if swarm.global_best_position is not None:
                best_point.set_offsets([swarm.global_best_position])
            
            # Update convergence
            line.set_data(range(frame + 1), fitness_history[:frame + 1])
            ax2.set_xlim(0, frame + 1)
            if fitness_history:
                ax2.set_ylim(min(fitness_history[:frame + 1]) * 0.1, 
                           max(fitness_history[:frame + 1]) * 2)
            
            return scatter, best_point, line
        
        anim = animation.FuncAnimation(fig, animate, frames=iterations, 
                                     interval=100, blit=True, repeat=True)
        
        if save_path:
            anim.save(save_path, writer='pillow', fps=10)
        else:
            plt.show()
        
        plt.close()
    
    def plot_performance_comparison(self, benchmark_results: List[BenchmarkResult],
                                  save_path: Optional[str] = None) -> None:
        """Plot performance comparison across algorithms and problems"""
        if self.use_plotly:
            self._plotly_performance_comparison(benchmark_results, save_path)
        else:
            self._matplotlib_performance_comparison(benchmark_results, save_path)
    
    def _matplotlib_performance_comparison(self, benchmark_results: List[BenchmarkResult],
                                         save_path: Optional[str]) -> None:
        """Matplotlib performance comparison"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        # Organize data
        algorithms = list(set(r.algorithm_name for r in benchmark_results))
        problems = list(set(r.problem_name for r in benchmark_results))
        
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Algorithm Performance Comparison', fontsize=16)
        
        # Best fitness comparison
        ax = axes[0, 0]
        fitness_data = {}
        for algo in algorithms:
            fitness_data[algo] = [r.best_fitness for r in benchmark_results 
                                if r.algorithm_name == algo]
        
        ax.boxplot(fitness_data.values(), labels=fitness_data.keys())
        ax.set_ylabel('Best Fitness')
        ax.set_title('Best Fitness Distribution')
        ax.set_yscale('log')
        
        # Execution time comparison
        ax = axes[0, 1]
        time_data = {}
        for algo in algorithms:
            time_data[algo] = [r.execution_time for r in benchmark_results 
                             if r.algorithm_name == algo]
        
        ax.boxplot(time_data.values(), labels=time_data.keys())
        ax.set_ylabel('Execution Time (s)')
        ax.set_title('Execution Time Distribution')
        
        # Success rate comparison
        ax = axes[1, 0]
        success_rates = {}
        for algo in algorithms:
            rates = [r.success_rate for r in benchmark_results 
                    if r.algorithm_name == algo]
            success_rates[algo] = np.mean(rates) if rates else 0
        
        ax.bar(success_rates.keys(), success_rates.values())
        ax.set_ylabel('Success Rate')
        ax.set_title('Average Success Rate')
        ax.set_ylim(0, 1)
        
        # Efficiency vs Quality scatter
        ax = axes[1, 1]
        for algo in algorithms:
            algo_results = [r for r in benchmark_results if r.algorithm_name == algo]
            x = [r.efficiency_score for r in algo_results]
            y = [1.0 / (1.0 + r.best_fitness) for r in algo_results]
            ax.scatter(x, y, label=algo, alpha=0.7)
        
        ax.set_xlabel('Efficiency Score')
        ax.set_ylabel('Quality Score')
        ax.set_title('Efficiency vs Quality')
        ax.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        plt.close()
    
    def _plotly_performance_comparison(self, benchmark_results: List[BenchmarkResult],
                                     save_path: Optional[str]) -> None:
        """Plotly performance comparison"""
        if not PLOTLY_AVAILABLE:
            return
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Best Fitness', 'Execution Time', 
                          'Success Rate', 'Efficiency vs Quality'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        algorithms = list(set(r.algorithm_name for r in benchmark_results))
        colors = px.colors.qualitative.Set1[:len(algorithms)]
        
        # Best fitness box plots
        for i, algo in enumerate(algorithms):
            fitness_values = [r.best_fitness for r in benchmark_results 
                            if r.algorithm_name == algo]
            fig.add_trace(
                go.Box(y=fitness_values, name=algo, 
                      marker_color=colors[i], showlegend=False),
                row=1, col=1
            )
        
        # Execution time box plots
        for i, algo in enumerate(algorithms):
            time_values = [r.execution_time for r in benchmark_results 
                         if r.algorithm_name == algo]
            fig.add_trace(
                go.Box(y=time_values, name=algo, 
                      marker_color=colors[i], showlegend=False),
                row=1, col=2
            )
        
        # Success rate bar chart
        success_rates = {}
        for algo in algorithms:
            rates = [r.success_rate for r in benchmark_results 
                    if r.algorithm_name == algo]
            success_rates[algo] = np.mean(rates) if rates else 0
        
        fig.add_trace(
            go.Bar(x=list(success_rates.keys()), y=list(success_rates.values()),
                  marker_color=colors[:len(success_rates)], showlegend=False),
            row=2, col=1
        )
        
        # Efficiency vs Quality scatter
        for i, algo in enumerate(algorithms):
            algo_results = [r for r in benchmark_results if r.algorithm_name == algo]
            x = [r.efficiency_score for r in algo_results]
            y = [1.0 / (1.0 + r.best_fitness) for r in algo_results]
            
            fig.add_trace(
                go.Scatter(x=x, y=y, mode='markers', name=algo,
                          marker=dict(color=colors[i], size=8)),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            title_text="Algorithm Performance Comparison",
            height=800
        )
        
        fig.update_yaxes(type="log", row=1, col=1)
        fig.update_yaxes(title_text="Best Fitness", row=1, col=1)
        fig.update_yaxes(title_text="Execution Time (s)", row=1, col=2)
        fig.update_yaxes(title_text="Success Rate", row=2, col=1)
        fig.update_yaxes(title_text="Quality Score", row=2, col=2)
        fig.update_xaxes(title_text="Efficiency Score", row=2, col=2)
        
        if save_path:
            fig.write_html(save_path)
        else:
            fig.show()


class SwarmDashboard:
    """Interactive dashboard for swarm intelligence monitoring"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        if not PLOTLY_AVAILABLE:
            self.logger.warning("Dashboard requires plotly. Install with: pip install plotly")
    
    def create_real_time_dashboard(self, swarms: Dict[str, SwarmOptimizer]) -> None:
        """Create real-time monitoring dashboard"""
        if not PLOTLY_AVAILABLE:
            self.logger.error("Real-time dashboard requires plotly")
            return
        
        # This would typically integrate with Dash for real-time updates
        self.logger.info("Real-time dashboard would be implemented with Dash")
        self.logger.info("Install with: pip install dash")


# Utility functions for creating visualizations
def quick_convergence_plot(swarm: SwarmOptimizer, objective_function,
                          iterations: int = 100) -> None:
    """Quick convergence plot for a single swarm"""
    if not MATPLOTLIB_AVAILABLE:
        print("Matplotlib not available for visualization")
        return
    
    swarm.initialize_population()
    
    for _ in range(iterations):
        swarm.update_agents(objective_function)
    
    plt.figure(figsize=(10, 6))
    plt.plot(swarm.convergence_history, linewidth=2)
    plt.xlabel('Iteration')
    plt.ylabel('Best Fitness')
    plt.title(f'{swarm.__class__.__name__} Convergence')
    plt.grid(True, alpha=0.3)
    plt.yscale('log')
    plt.show()


def plot_2d_swarm_state(swarm: SwarmOptimizer, title: str = "Swarm State") -> None:
    """Plot current state of 2D swarm"""
    if not MATPLOTLIB_AVAILABLE or swarm.params.dimension != 2:
        print("2D plotting requires matplotlib and 2D problems")
        return
    
    if not hasattr(swarm, 'agents'):
        print("Swarm has no agents to plot")
        return
    
    positions = np.array([agent.position for agent in swarm.agents])
    fitness_values = [agent.fitness for agent in swarm.agents]
    
    plt.figure(figsize=(10, 8))
    scatter = plt.scatter(positions[:, 0], positions[:, 1], 
                         c=fitness_values, cmap='viridis', alpha=0.7)
    plt.colorbar(scatter, label='Fitness')
    
    # Highlight best agent
    if swarm.global_best_position is not None:
        plt.scatter(swarm.global_best_position[0], swarm.global_best_position[1],
                   c='red', s=200, marker='*', label='Global Best')
        plt.legend()
    
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.show()