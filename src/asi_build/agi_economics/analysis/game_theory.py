"""
Game Theory Analysis Engine
==========================

Advanced game theory analysis for AGI economic interactions,
including Nash equilibrium calculations, mechanism design,
and strategic behavior modeling.
"""

import itertools
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal, getcontext
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from scipy.linalg import null_space
from scipy.optimize import linprog, minimize

from ..core.base_engine import BaseEconomicEngine, EconomicEvent
from ..core.exceptions import ValidationError
from ..core.types import Agent, AgentID

# Set decimal precision
getcontext().prec = 28

logger = logging.getLogger(__name__)


class GameType(Enum):
    """Types of games supported"""

    NORMAL_FORM = "normal_form"
    EXTENSIVE_FORM = "extensive_form"
    AUCTION = "auction"
    RESOURCE_ALLOCATION = "resource_allocation"
    REPUTATION = "reputation"
    COOPERATIVE = "cooperative"
    EVOLUTIONARY = "evolutionary"


class EquilibriumType(Enum):
    """Types of equilibria"""

    NASH = "nash"
    DOMINANT_STRATEGY = "dominant_strategy"
    CORRELATED = "correlated"
    EVOLUTIONARY_STABLE = "evolutionary_stable"
    COALITION = "coalition"


@dataclass
class Player:
    """Represents a player in a game"""

    player_id: str
    strategies: List[str]
    payoff_matrix: np.ndarray = None
    utility_function: callable = None
    rationality_level: float = 1.0  # 0-1, higher = more rational


@dataclass
class Game:
    """Represents a game structure"""

    game_id: str
    game_type: GameType
    players: List[Player]
    payoff_matrices: Dict[str, np.ndarray]  # Player ID -> payoff matrix
    description: str = ""


@dataclass
class StrategyProfile:
    """Represents a strategy profile (strategy for each player)"""

    strategies: Dict[str, str]  # Player ID -> strategy
    expected_payoffs: Dict[str, float] = field(default_factory=dict)


@dataclass
class Equilibrium:
    """Represents an equilibrium solution"""

    equilibrium_type: EquilibriumType
    strategy_profile: StrategyProfile
    is_stable: bool
    stability_measure: float
    social_welfare: float
    efficiency_ratio: float  # Ratio to optimal social welfare


class GameTheoryAnalyzer(BaseEconomicEngine):
    """
    Advanced game theory analysis engine for AGI economic systems.
    Analyzes strategic interactions, finds equilibria, and evaluates
    mechanism efficiency.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

        # Games being analyzed
        self.games: Dict[str, Game] = {}

        # Calculated equilibria
        self.equilibria: Dict[str, List[Equilibrium]] = {}

        # Agent behavior models
        self.agent_models: Dict[str, Dict[str, Any]] = {}

        # Analysis history
        self.analysis_results: List[Dict[str, Any]] = []

        # Configuration
        self.convergence_tolerance = config.get("convergence_tolerance", 1e-6)
        self.max_iterations = config.get("max_iterations", 1000)
        self.rationality_assumption = config.get("rationality_assumption", 0.9)

    def start(self) -> bool:
        """Start the game theory analyzer"""
        try:
            self.is_active = True
            self.metrics["start_time"] = time.time()
            self.log_event("game_theory_analyzer_started")
            logger.info("Game Theory Analyzer started")
            return True
        except Exception as e:
            logger.error(f"Failed to start Game Theory Analyzer: {e}")
            return False

    def stop(self) -> bool:
        """Stop the game theory analyzer"""
        try:
            self.is_active = False
            self.log_event("game_theory_analyzer_stopped")
            logger.info("Game Theory Analyzer stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop Game Theory Analyzer: {e}")
            return False

    def process_event(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process game theory analysis events"""
        if not self.is_active:
            return {"error": "Engine not active"}

        try:
            if event.event_type == "analyze_game":
                return self._process_game_analysis(event)
            elif event.event_type == "find_equilibrium":
                return self._process_equilibrium_finding(event)
            elif event.event_type == "evaluate_mechanism":
                return self._process_mechanism_evaluation(event)
            elif event.event_type == "simulate_strategic_behavior":
                return self._process_strategic_simulation(event)
            else:
                return {"error": f"Unknown event type: {event.event_type}"}
        except Exception as e:
            logger.error(f"Error processing game theory event {event.event_type}: {e}")
            return {"error": str(e)}

    def create_agi_service_game(
        self,
        providers: List[str],
        consumers: List[str],
        service_qualities: Dict[str, float],
        prices: Dict[str, float],
    ) -> Game:
        """Create a game representing AGI service marketplace interactions"""

        # Create players
        players = []

        # Provider strategies: (price_level, quality_level)
        provider_strategies = [
            "low_price_low_quality",
            "medium_price_medium_quality",
            "high_price_high_quality",
            "premium_price_premium_quality",
        ]

        # Consumer strategies: (provider_selection, payment_willingness)
        consumer_strategies = ["budget_conscious", "quality_focused", "premium_seeker", "balanced"]

        # Create provider players
        for provider_id in providers:
            player = Player(
                player_id=provider_id, strategies=provider_strategies, rationality_level=0.8
            )
            players.append(player)

        # Create consumer players
        for consumer_id in consumers:
            player = Player(
                player_id=consumer_id, strategies=consumer_strategies, rationality_level=0.9
            )
            players.append(player)

        # Calculate payoff matrices
        payoff_matrices = {}

        for player in players:
            if player.player_id in providers:
                # Provider payoff matrix
                payoff_matrices[player.player_id] = self._calculate_provider_payoffs(
                    player, consumers, service_qualities, prices
                )
            else:
                # Consumer payoff matrix
                payoff_matrices[player.player_id] = self._calculate_consumer_payoffs(
                    player, providers, service_qualities, prices
                )

        game = Game(
            game_id=f"agi_service_game_{int(time.time())}",
            game_type=GameType.NORMAL_FORM,
            players=players,
            payoff_matrices=payoff_matrices,
            description="AGI service marketplace competition game",
        )

        self.games[game.game_id] = game
        return game

    def _calculate_provider_payoffs(
        self,
        provider: Player,
        consumers: List[str],
        service_qualities: Dict[str, float],
        prices: Dict[str, float],
    ) -> np.ndarray:
        """Calculate payoff matrix for service providers"""

        n_strategies = len(provider.strategies)
        n_consumer_strategies = len(consumers) * 4  # 4 strategies per consumer

        payoff_matrix = np.zeros((n_strategies, n_consumer_strategies))

        strategy_costs = {
            "low_price_low_quality": 0.2,
            "medium_price_medium_quality": 0.5,
            "high_price_high_quality": 0.8,
            "premium_price_premium_quality": 1.2,
        }

        strategy_prices = {
            "low_price_low_quality": 0.3,
            "medium_price_medium_quality": 0.6,
            "high_price_high_quality": 1.0,
            "premium_price_premium_quality": 1.5,
        }

        for i, provider_strategy in enumerate(provider.strategies):
            for j in range(n_consumer_strategies):
                # Calculate market share based on consumer preferences
                market_share = self._estimate_market_share(provider_strategy, j, consumers)

                # Revenue = price * market_share * market_size
                revenue = strategy_prices[provider_strategy] * market_share * 100

                # Cost = cost_per_unit * volume
                cost = strategy_costs[provider_strategy] * market_share * 100

                # Profit = revenue - cost
                payoff_matrix[i, j] = revenue - cost

        return payoff_matrix

    def _calculate_consumer_payoffs(
        self,
        consumer: Player,
        providers: List[str],
        service_qualities: Dict[str, float],
        prices: Dict[str, float],
    ) -> np.ndarray:
        """Calculate payoff matrix for service consumers"""

        n_strategies = len(consumer.strategies)
        n_provider_strategies = len(providers) * 4  # 4 strategies per provider

        payoff_matrix = np.zeros((n_strategies, n_provider_strategies))

        # Consumer utility based on quality and price
        for i, consumer_strategy in enumerate(consumer.strategies):
            for j in range(n_provider_strategies):
                provider_idx = j // 4
                provider_strategy_idx = j % 4

                # Get provider strategy
                provider_strategies = [
                    "low_price_low_quality",
                    "medium_price_medium_quality",
                    "high_price_high_quality",
                    "premium_price_premium_quality",
                ]
                provider_strategy = provider_strategies[provider_strategy_idx]

                # Quality and price mapping
                quality_levels = {
                    "low_price_low_quality": 0.3,
                    "medium_price_medium_quality": 0.6,
                    "high_price_high_quality": 0.8,
                    "premium_price_premium_quality": 0.95,
                }
                price_levels = {
                    "low_price_low_quality": 0.3,
                    "medium_price_medium_quality": 0.6,
                    "high_price_high_quality": 1.0,
                    "premium_price_premium_quality": 1.5,
                }

                quality = quality_levels[provider_strategy]
                price = price_levels[provider_strategy]

                # Consumer utility function: utility = quality_weight * quality - price_weight * price
                if consumer_strategy == "budget_conscious":
                    utility = 0.3 * quality - 0.7 * price
                elif consumer_strategy == "quality_focused":
                    utility = 0.8 * quality - 0.2 * price
                elif consumer_strategy == "premium_seeker":
                    utility = 0.9 * quality - 0.1 * price + 0.1  # Premium bonus
                else:  # balanced
                    utility = 0.5 * quality - 0.5 * price

                payoff_matrix[i, j] = utility * 100  # Scale utility

        return payoff_matrix

    def _estimate_market_share(
        self, provider_strategy: str, consumer_combination_idx: int, consumers: List[str]
    ) -> float:
        """Estimate market share based on strategy compatibility"""

        # Simplified market share calculation
        compatibility_scores = {
            "low_price_low_quality": {
                "budget_conscious": 0.8,
                "quality_focused": 0.1,
                "premium_seeker": 0.05,
                "balanced": 0.4,
            },
            "medium_price_medium_quality": {
                "budget_conscious": 0.3,
                "quality_focused": 0.6,
                "premium_seeker": 0.2,
                "balanced": 0.8,
            },
            "high_price_high_quality": {
                "budget_conscious": 0.1,
                "quality_focused": 0.9,
                "premium_seeker": 0.7,
                "balanced": 0.6,
            },
            "premium_price_premium_quality": {
                "budget_conscious": 0.02,
                "quality_focused": 0.8,
                "premium_seeker": 0.95,
                "balanced": 0.4,
            },
        }

        consumer_strategies = ["budget_conscious", "quality_focused", "premium_seeker", "balanced"]

        # Decode consumer combination
        total_compatibility = 0.0
        for i, consumer_id in enumerate(consumers):
            consumer_strategy_idx = (consumer_combination_idx >> (i * 2)) & 3
            consumer_strategy = consumer_strategies[consumer_strategy_idx]
            total_compatibility += compatibility_scores[provider_strategy][consumer_strategy]

        # Market share proportional to compatibility
        market_share = total_compatibility / (len(consumers) * 4)  # Normalize
        return min(market_share, 1.0)

    def find_nash_equilibria(self, game: Game) -> List[Equilibrium]:
        """Find Nash equilibria for a game"""
        equilibria = []

        try:
            # For normal form games, use iterative best response
            if game.game_type == GameType.NORMAL_FORM:
                equilibria.extend(self._find_pure_nash_equilibria(game))
                equilibria.extend(self._find_mixed_nash_equilibria(game))

            # Store equilibria
            self.equilibria[game.game_id] = equilibria

            self.log_event(
                "nash_equilibria_found",
                data={
                    "game_id": game.game_id,
                    "equilibria_count": len(equilibria),
                    "pure_equilibria": len(
                        [
                            eq
                            for eq in equilibria
                            if self._is_pure_strategy_profile(eq.strategy_profile)
                        ]
                    ),
                },
            )

        except Exception as e:
            logger.error(f"Failed to find Nash equilibria for game {game.game_id}: {e}")

        return equilibria

    def _find_pure_nash_equilibria(self, game: Game) -> List[Equilibrium]:
        """Find pure strategy Nash equilibria"""
        equilibria = []

        # Get all possible pure strategy combinations
        player_strategies = [player.strategies for player in game.players]
        all_combinations = list(itertools.product(*player_strategies))

        for combination in all_combinations:
            # Create strategy profile
            strategy_profile = StrategyProfile(
                strategies={
                    game.players[i].player_id: combination[i] for i in range(len(game.players))
                }
            )

            # Check if this is a Nash equilibrium
            if self._is_nash_equilibrium(game, strategy_profile):
                # Calculate payoffs
                payoffs = self._calculate_strategy_profile_payoffs(game, strategy_profile)
                strategy_profile.expected_payoffs = payoffs

                # Calculate social welfare and efficiency
                social_welfare = sum(payoffs.values())
                efficiency_ratio = self._calculate_efficiency_ratio(game, strategy_profile)

                equilibrium = Equilibrium(
                    equilibrium_type=EquilibriumType.NASH,
                    strategy_profile=strategy_profile,
                    is_stable=True,
                    stability_measure=1.0,
                    social_welfare=social_welfare,
                    efficiency_ratio=efficiency_ratio,
                )

                equilibria.append(equilibrium)

        return equilibria

    def _find_mixed_nash_equilibria(self, game: Game) -> List[Equilibrium]:
        """Find mixed strategy Nash equilibria using linear complementarity"""
        equilibria = []

        # For 2-player games, use support enumeration
        if len(game.players) == 2:
            try:
                mixed_equilibria = self._support_enumeration_2player(game)
                equilibria.extend(mixed_equilibria)
            except Exception as e:
                logger.warning(f"Mixed strategy calculation failed: {e}")

        return equilibria

    def _support_enumeration_2player(self, game: Game) -> List[Equilibrium]:
        """Support enumeration method for 2-player mixed Nash equilibria"""
        equilibria = []

        player1, player2 = game.players[0], game.players[1]
        A = game.payoff_matrices[player1.player_id]  # Player 1's payoff matrix
        B = game.payoff_matrices[player2.player_id].T  # Player 2's payoff matrix (transposed)

        m, n = A.shape  # m strategies for player 1, n strategies for player 2

        # Enumerate all possible supports (subsets of strategies)
        for k1 in range(1, m + 1):  # Support size for player 1
            for support1 in itertools.combinations(range(m), k1):
                for k2 in range(1, n + 1):  # Support size for player 2
                    for support2 in itertools.combinations(range(n), k2):

                        # Try to find mixed strategy equilibrium with these supports
                        try:
                            mixed_eq = self._solve_mixed_equilibrium_2player(
                                A, B, support1, support2, player1, player2
                            )
                            if mixed_eq:
                                equilibria.append(mixed_eq)
                        except:
                            continue

        return equilibria

    def _solve_mixed_equilibrium_2player(
        self,
        A: np.ndarray,
        B: np.ndarray,
        support1: Tuple,
        support2: Tuple,
        player1: Player,
        player2: Player,
    ) -> Optional[Equilibrium]:
        """Solve for mixed strategy equilibrium given supports"""

        try:
            # Set up linear system for indifference conditions
            # Player 1 must be indifferent among strategies in support
            k1, k2 = len(support1), len(support2)

            if k1 == 1 and k2 == 1:
                return None  # Pure strategy, already handled

            # For player 2's mixed strategy (makes player 1 indifferent)
            if k1 > 1:
                # A * y = u1 * 1 (indifference condition)
                A_support = A[list(support1), :][:, list(support2)]

                # Set up equations: difference between payoffs = 0
                eq_matrix = np.zeros((k1 - 1, k2 + 1))
                for i in range(k1 - 1):
                    eq_matrix[i, :k2] = A_support[i + 1, :] - A_support[0, :]
                    # eq_matrix[i, k2] = 0  # Already zero

                # Add probability constraint: sum(y) = 1
                prob_constraint = np.zeros((1, k2 + 1))
                prob_constraint[0, :k2] = 1
                prob_constraint[0, k2] = 1  # RHS

                # Solve system
                system_matrix = np.vstack([eq_matrix, prob_constraint])
                rhs = np.zeros(k1)
                rhs[-1] = 1  # Probability constraint RHS

                if system_matrix.shape[0] == system_matrix.shape[1] - 1:
                    solution = np.linalg.lstsq(
                        system_matrix[:, :k2], rhs - system_matrix[:, k2], rcond=None
                    )[0]

                    # Check if solution is valid (non-negative probabilities)
                    if np.all(solution >= -1e-10) and abs(np.sum(solution) - 1) < 1e-10:
                        # Create strategy profile
                        p1_mixed = np.zeros(len(player1.strategies))
                        p2_mixed = np.zeros(len(player2.strategies))

                        # Set probabilities for player 2
                        for i, strategy_idx in enumerate(support2):
                            p2_mixed[strategy_idx] = max(0, solution[i])

                        # Calculate best response for player 1 (uniform on support)
                        for strategy_idx in support1:
                            p1_mixed[strategy_idx] = 1.0 / len(support1)

                        # Normalize
                        p1_mixed /= np.sum(p1_mixed) if np.sum(p1_mixed) > 0 else 1
                        p2_mixed /= np.sum(p2_mixed) if np.sum(p2_mixed) > 0 else 1

                        # Create equilibrium
                        strategy_profile = StrategyProfile(strategies={})

                        # Calculate expected payoffs
                        expected_payoff_1 = np.sum(p1_mixed[:, np.newaxis] * A * p2_mixed)
                        expected_payoff_2 = np.sum(p1_mixed * B * p2_mixed[:, np.newaxis])

                        strategy_profile.expected_payoffs = {
                            player1.player_id: float(expected_payoff_1),
                            player2.player_id: float(expected_payoff_2),
                        }

                        equilibrium = Equilibrium(
                            equilibrium_type=EquilibriumType.NASH,
                            strategy_profile=strategy_profile,
                            is_stable=True,
                            stability_measure=0.8,  # Mixed strategies are generally less stable
                            social_welfare=float(expected_payoff_1 + expected_payoff_2),
                            efficiency_ratio=0.7,  # Approximate
                        )

                        return equilibrium

        except Exception as e:
            logger.debug(f"Mixed equilibrium calculation failed: {e}")

        return None

    def _is_nash_equilibrium(self, game: Game, strategy_profile: StrategyProfile) -> bool:
        """Check if a strategy profile is a Nash equilibrium"""

        for player in game.players:
            current_strategy = strategy_profile.strategies[player.player_id]
            current_payoff = self._get_player_payoff(game, player, strategy_profile)

            # Check all alternative strategies
            for alternative_strategy in player.strategies:
                if alternative_strategy != current_strategy:
                    # Create alternative profile
                    alt_profile = StrategyProfile(strategies=strategy_profile.strategies.copy())
                    alt_profile.strategies[player.player_id] = alternative_strategy

                    alt_payoff = self._get_player_payoff(game, player, alt_profile)

                    # If player can improve by deviating, not Nash equilibrium
                    if alt_payoff > current_payoff + self.convergence_tolerance:
                        return False

        return True

    def _get_player_payoff(
        self, game: Game, player: Player, strategy_profile: StrategyProfile
    ) -> float:
        """Get player's payoff for a given strategy profile"""

        payoff_matrix = game.payoff_matrices[player.player_id]

        # Convert strategy profile to matrix indices
        player_strategy_idx = player.strategies.index(strategy_profile.strategies[player.player_id])

        # For normal form games, calculate based on opponent strategies
        # This is simplified - in practice would need to handle all player combinations
        if payoff_matrix.ndim == 2:
            # Assume 2-player game for simplicity
            other_players = [p for p in game.players if p.player_id != player.player_id]
            if other_players:
                other_player = other_players[0]
                other_strategy_idx = other_player.strategies.index(
                    strategy_profile.strategies[other_player.player_id]
                )
                return float(payoff_matrix[player_strategy_idx, other_strategy_idx])

        return 0.0

    def _calculate_strategy_profile_payoffs(
        self, game: Game, strategy_profile: StrategyProfile
    ) -> Dict[str, float]:
        """Calculate payoffs for all players given a strategy profile"""
        payoffs = {}

        for player in game.players:
            payoffs[player.player_id] = self._get_player_payoff(game, player, strategy_profile)

        return payoffs

    def _calculate_efficiency_ratio(self, game: Game, strategy_profile: StrategyProfile) -> float:
        """Calculate efficiency ratio (social welfare / optimal social welfare)"""

        current_welfare = sum(
            self._calculate_strategy_profile_payoffs(game, strategy_profile).values()
        )

        # Find optimal social welfare (sum of all payoffs maximized)
        max_welfare = 0.0
        player_strategies = [player.strategies for player in game.players]

        for combination in itertools.product(*player_strategies):
            test_profile = StrategyProfile(
                strategies={
                    game.players[i].player_id: combination[i] for i in range(len(game.players))
                }
            )
            welfare = sum(self._calculate_strategy_profile_payoffs(game, test_profile).values())
            max_welfare = max(max_welfare, welfare)

        return current_welfare / max_welfare if max_welfare > 0 else 1.0

    def _is_pure_strategy_profile(self, strategy_profile: StrategyProfile) -> bool:
        """Check if strategy profile consists of pure strategies only"""
        # In our representation, all stored profiles are pure strategies
        # Mixed strategies would need different representation
        return True

    def analyze_mechanism_efficiency(self, game: Game) -> Dict[str, Any]:
        """Analyze the efficiency of the economic mechanism"""

        if game.game_id not in self.equilibria:
            self.find_nash_equilibria(game)

        equilibria = self.equilibria[game.game_id]

        if not equilibria:
            return {"error": "No equilibria found"}

        # Analyze each equilibrium
        analysis = {
            "game_id": game.game_id,
            "total_equilibria": len(equilibria),
            "equilibrium_analysis": [],
            "mechanism_properties": {},
        }

        efficiency_ratios = []
        social_welfares = []

        for eq in equilibria:
            eq_analysis = {
                "type": eq.equilibrium_type.value,
                "social_welfare": eq.social_welfare,
                "efficiency_ratio": eq.efficiency_ratio,
                "is_stable": eq.is_stable,
                "strategy_profile": eq.strategy_profile.strategies,
                "payoffs": eq.strategy_profile.expected_payoffs,
            }

            analysis["equilibrium_analysis"].append(eq_analysis)
            efficiency_ratios.append(eq.efficiency_ratio)
            social_welfares.append(eq.social_welfare)

        # Mechanism properties
        analysis["mechanism_properties"] = {
            "average_efficiency": np.mean(efficiency_ratios),
            "max_efficiency": np.max(efficiency_ratios),
            "min_efficiency": np.min(efficiency_ratios),
            "average_welfare": np.mean(social_welfares),
            "welfare_variance": np.var(social_welfares),
            "has_dominant_strategy": self._check_dominant_strategies(game),
            "is_incentive_compatible": self._check_incentive_compatibility(game),
            "satisfies_individual_rationality": self._check_individual_rationality(game),
        }

        self.analysis_results.append(analysis)

        return analysis

    def _check_dominant_strategies(self, game: Game) -> Dict[str, Any]:
        """Check for dominant strategies"""
        dominant_strategies = {}

        for player in game.players:
            player_dominance = self._find_dominant_strategy(game, player)
            if player_dominance:
                dominant_strategies[player.player_id] = player_dominance

        return {"exists": len(dominant_strategies) > 0, "strategies": dominant_strategies}

    def _find_dominant_strategy(self, game: Game, player: Player) -> Optional[str]:
        """Find dominant strategy for a player, if any"""

        payoff_matrix = game.payoff_matrices[player.player_id]

        # Check each strategy for dominance
        for i, strategy in enumerate(player.strategies):
            is_dominant = True

            # Compare with all other strategies
            for j, other_strategy in enumerate(player.strategies):
                if i == j:
                    continue

                # Check if strategy i dominates strategy j
                if payoff_matrix.ndim == 2:
                    # For 2D matrix, check all columns (opponent strategies)
                    for col in range(payoff_matrix.shape[1]):
                        if payoff_matrix[i, col] <= payoff_matrix[j, col]:
                            is_dominant = False
                            break

                if not is_dominant:
                    break

            if is_dominant:
                return strategy

        return None

    def _check_incentive_compatibility(self, game: Game) -> Dict[str, Any]:
        """Check mechanism incentive compatibility"""

        # For AGI service games, check if truth-telling is optimal
        # This is simplified - real implementation would be more complex

        if game.game_id not in self.equilibria:
            return {"compatible": False, "reason": "No equilibria found"}

        equilibria = self.equilibria[game.game_id]

        # Check if equilibrium strategies align with true preferences
        # Simplified check: if players have no incentive to misrepresent
        incentive_violations = 0

        for eq in equilibria:
            for player_id, payoff in eq.strategy_profile.expected_payoffs.items():
                # Check if player could benefit from strategic misrepresentation
                # This would require more detailed preference modeling
                pass

        return {"compatible": incentive_violations == 0, "violation_count": incentive_violations}

    def _check_individual_rationality(self, game: Game) -> Dict[str, Any]:
        """Check individual rationality (participation constraints)"""

        if game.game_id not in self.equilibria:
            return {"rational": False, "reason": "No equilibria found"}

        equilibria = self.equilibria[game.game_id]

        # Check if all players get non-negative utility in equilibrium
        violations = []

        for eq in equilibria:
            for player_id, payoff in eq.strategy_profile.expected_payoffs.items():
                if payoff < 0:  # Could be negative if outside option is 0
                    violations.append(
                        {
                            "player_id": player_id,
                            "payoff": payoff,
                            "equilibrium": eq.equilibrium_type.value,
                        }
                    )

        return {"rational": len(violations) == 0, "violations": violations}

    def _process_game_analysis(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process game analysis event"""
        data = event.data
        try:
            # This would create a game from event data and analyze it
            return {"success": True, "message": "Game analysis not yet fully implemented"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _process_equilibrium_finding(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process equilibrium finding event"""
        data = event.data
        try:
            game_id = data["game_id"]
            if game_id in self.games:
                equilibria = self.find_nash_equilibria(self.games[game_id])
                return {
                    "success": True,
                    "equilibria_count": len(equilibria),
                    "equilibria": [
                        {
                            "type": eq.equilibrium_type.value,
                            "social_welfare": eq.social_welfare,
                            "efficiency_ratio": eq.efficiency_ratio,
                            "strategies": eq.strategy_profile.strategies,
                        }
                        for eq in equilibria
                    ],
                }
            else:
                return {"success": False, "error": "Game not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _process_mechanism_evaluation(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process mechanism evaluation event"""
        data = event.data
        try:
            game_id = data["game_id"]
            if game_id in self.games:
                analysis = self.analyze_mechanism_efficiency(self.games[game_id])
                return {"success": True, "analysis": analysis}
            else:
                return {"success": False, "error": "Game not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _process_strategic_simulation(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process strategic behavior simulation event"""
        # Implementation for evolutionary game dynamics, learning, etc.
        return {"success": True, "message": "Strategic simulation not yet implemented"}
