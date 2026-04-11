"""
Tests for asi_build.agi_economics package.

Patches sys.modules for missing submodules before any imports from the package.
"""

import sys
import types

# ---------------------------------------------------------------------------
# Fake-module patching — must happen BEFORE any from…import of agi_economics
# ---------------------------------------------------------------------------

def _fake_module(name, attrs):
    """Register a fake module in sys.modules with stub classes."""
    mod = types.ModuleType(name)
    for attr in attrs:
        setattr(mod, attr, type(attr, (), {}))
    sys.modules[name] = mod

_fake_module('asi_build.agi_economics.engines.liquidity_pools', ['LiquidityPoolEngine'])
_fake_module('asi_build.agi_economics.analysis.nash_equilibrium', ['NashEquilibriumCalculator'])
_fake_module('asi_build.agi_economics.analysis.mechanism_design', ['MechanismDesignEngine'])
_fake_module('asi_build.agi_economics.algorithms.auction_mechanisms',
             ['AuctionMechanism', 'VickreyAuction', 'DutchAuction'])
_fake_module('asi_build.agi_economics.algorithms.optimization', ['OptimizationEngine'])
_fake_module('asi_build.agi_economics.systems.governance', ['GovernanceSystem'])
_fake_module('asi_build.agi_economics.simulation.supply_demand_model', ['SupplyDemandModel'])
_fake_module('asi_build.agi_economics.simulation.price_discovery', ['PriceDiscoveryEngine'])

# ---------------------------------------------------------------------------
# Now safe to import from the package
# ---------------------------------------------------------------------------

import time
import uuid
import pytest
import numpy as np
from decimal import Decimal
from abc import ABC

from asi_build.agi_economics.core.types import (
    TokenType, TokenBalance, Resource, ResourceType, Agent, AgentType,
    EconomicTransaction, TransactionType, MarketData, MarketState,
)
from asi_build.agi_economics.core.base_engine import BaseEconomicEngine, EconomicEvent
from asi_build.agi_economics.core.exceptions import (
    AGIEconomicsError, TokenError, InsufficientFundsError,
    ResourceError, ResourceUnavailableError, ReputationError,
    MarketplaceError, SecurityError, GovernanceError,
    BlockchainError, ValidationError as EconValidationError,
    AgentError,
)
from asi_build.agi_economics.engines.bonding_curves import (
    BondingCurve, BondingCurveConfig, BondingCurveEngine, CurveType,
)
from asi_build.agi_economics.engines.token_economics import (
    TokenEconomicsEngine, TokenSupplyInfo, StakingPool,
)
from asi_build.agi_economics.analysis.game_theory import (
    GameTheoryAnalyzer, Game, Player, GameType, StrategyProfile,
)
from asi_build.agi_economics.algorithms.resource_allocator import (
    ResourceAllocator, ResourceProvider, AllocationStrategy,
)
from asi_build.agi_economics.core.types import ServiceRequest
from asi_build.agi_economics.systems.reputation_system import (
    ReputationSystem, ReputationDimension, ReputationValidator,
)
from asi_build.agi_economics.core.types import ReputationEvent
from asi_build.agi_economics.systems.value_alignment import (
    ValueAlignmentEngine, ValueCategory, ValueMeasurement,
)
from asi_build.agi_economics.simulation.marketplace_dynamics import (
    MarketplaceDynamics, MarketOrder, OrderType, OrderStatus, AuctionType,
)


# ============================================================================
# 1. core/types.py — ~6 tests
# ============================================================================

class TestCoreTypes:

    def test_token_type_enum_values(self):
        assert TokenType.AGIX.value == "AGIX"
        assert TokenType.SERVICE.value == "SERVICE"
        assert TokenType.REPUTATION.value == "REPUTATION"

    def test_token_balance_available_amount(self):
        tb = TokenBalance(token_type=TokenType.AGIX, amount=Decimal('100'), locked_amount=Decimal('30'))
        assert tb.available_amount == Decimal('70')

    def test_token_balance_defaults(self):
        tb = TokenBalance(token_type=TokenType.AGIX, amount=Decimal('50'))
        assert tb.locked_amount == Decimal('0')
        assert tb.available_amount == Decimal('50')
        assert tb.last_updated is not None

    def test_resource_total_cost(self):
        r = Resource(resource_type=ResourceType.GPU, amount=Decimal('10'),
                     cost_per_unit=Decimal('5'), provider_id='p1')
        assert r.total_cost == Decimal('50')

    def test_agent_dataclass(self):
        a = Agent(agent_id='a1', agent_type=AgentType.VALIDATOR,
                  reputation_score=0.9, trust_score=0.8,
                  token_balances={}, resources=[])
        assert a.agent_id == 'a1'
        assert a.is_active is True
        assert a.stake_amount == Decimal('0')

    def test_market_data_namedtuple(self):
        md = MarketData(timestamp=time.time(), token_type=TokenType.AGIX,
                        price=Decimal('10'), volume=Decimal('100'),
                        market_cap=Decimal('1000'), supply=Decimal('500'),
                        demand=Decimal('200'), state=MarketState.BALANCED)
        assert md.token_type == TokenType.AGIX
        assert md.state == MarketState.BALANCED

    def test_economic_transaction(self):
        tx = EconomicTransaction(
            transaction_id=None, transaction_type=TransactionType.TOKEN_TRANSFER,
            from_agent='a1', to_agent='a2', token_type=TokenType.AGIX,
            amount=Decimal('10'), timestamp=None)
        assert tx.transaction_id is not None  # auto-generated
        assert tx.timestamp is not None
        assert tx.metadata == {}


# ============================================================================
# 2. core/base_engine.py — ~8 tests
# ============================================================================

class ConcreteEngine(BaseEconomicEngine):
    """Minimal concrete subclass for testing the ABC."""

    def start(self):
        self.is_active = True
        return True

    def stop(self):
        self.is_active = False
        return True

    def process_event(self, event):
        return {'processed': True}


class TestBaseEconomicEngine:

    def test_is_abstract(self):
        assert issubclass(BaseEconomicEngine, ABC)

    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            BaseEconomicEngine()

    def test_log_event(self):
        eng = ConcreteEngine(config={})
        evt = eng.log_event('test_event', agent_id='a1', data={'key': 'val'})
        assert evt.event_type == 'test_event'
        assert evt.agent_id == 'a1'
        assert evt.data == {'key': 'val'}
        assert len(eng.events) == 1

    def test_update_and_get_metrics(self):
        eng = ConcreteEngine(config={})
        eng.update_metrics({'foo': 42})
        m = eng.get_metrics()
        assert m['foo'] == 42
        assert m['total_events'] == 0
        assert 'engine_id' in m

    def test_get_events_filter_by_type(self):
        eng = ConcreteEngine(config={})
        eng.log_event('alpha', agent_id='a1')
        eng.log_event('beta', agent_id='a2')
        eng.log_event('alpha', agent_id='a3')
        assert len(eng.get_events(event_type='alpha')) == 2

    def test_get_events_filter_by_agent(self):
        eng = ConcreteEngine(config={})
        eng.log_event('x', agent_id='a1')
        eng.log_event('y', agent_id='a2')
        assert len(eng.get_events(agent_id='a1')) == 1

    def test_get_events_limit(self):
        eng = ConcreteEngine(config={})
        for i in range(10):
            eng.log_event(f'e{i}')
        assert len(eng.get_events(limit=3)) == 3

    def test_reset_state(self):
        eng = ConcreteEngine(config={})
        eng.log_event('test')
        eng.update_metrics({'x': 1})
        eng.state['key'] = 'val'
        eng.is_active = True
        eng.reset_state()
        assert len(eng.events) == 0
        assert eng.metrics == {}
        assert eng.state == {}
        assert eng.is_active is False

    def test_health_check(self):
        eng = ConcreteEngine(config={})
        hc = eng.health_check()
        assert hc['status'] == 'inactive'
        assert hc['event_count'] == 0
        assert hc['error_count'] == 0
        eng.start()
        hc2 = eng.health_check()
        assert hc2['status'] == 'healthy'


# ============================================================================
# 3. core/exceptions.py — ~5 tests
# ============================================================================

class TestExceptions:

    def test_base_exception_hierarchy(self):
        assert issubclass(AGIEconomicsError, Exception)

    def test_insufficient_funds_is_token_error(self):
        assert issubclass(InsufficientFundsError, TokenError)
        assert issubclass(TokenError, AGIEconomicsError)

    def test_resource_error_hierarchy(self):
        assert issubclass(ResourceUnavailableError, ResourceError)
        assert issubclass(ResourceError, AGIEconomicsError)

    def test_marketplace_error_hierarchy(self):
        assert issubclass(MarketplaceError, AGIEconomicsError)

    def test_message_propagation(self):
        try:
            raise InsufficientFundsError("not enough tokens")
        except AGIEconomicsError as e:
            assert "not enough tokens" in str(e)

    def test_security_error_hierarchy(self):
        assert issubclass(SecurityError, AGIEconomicsError)

    def test_governance_blockchain_agent_error(self):
        assert issubclass(GovernanceError, AGIEconomicsError)
        assert issubclass(BlockchainError, AGIEconomicsError)
        assert issubclass(AgentError, AGIEconomicsError)


# ============================================================================
# 4. engines/bonding_curves.py — ~20 tests
# ============================================================================

def _make_bc(curve_type: CurveType, **overrides) -> BondingCurve:
    """Helper to build a BondingCurve with sensible defaults."""
    defaults = dict(
        curve_type=curve_type,
        reserve_ratio=Decimal('0.5'),
        slope=Decimal('0.001'),
        base_price=Decimal('1.0'),
        max_supply=Decimal('1000000'),
        initial_supply=Decimal('10000'),
        reserve_balance=Decimal('10000'),
    )
    defaults.update(overrides)
    cfg = BondingCurveConfig(**defaults)
    return BondingCurve(cfg)


class TestBondingCurves:

    # --- get_price per CurveType ---

    def test_linear_price_increases(self):
        bc = _make_bc(CurveType.LINEAR)
        p1 = bc.get_price(Decimal('100'))
        p2 = bc.get_price(Decimal('200'))
        assert p2 > p1

    def test_exponential_price_increases(self):
        bc = _make_bc(CurveType.EXPONENTIAL)
        p1 = bc.get_price(Decimal('100'))
        p2 = bc.get_price(Decimal('200'))
        assert p2 > p1

    def test_logarithmic_price_zero_supply(self):
        bc = _make_bc(CurveType.LOGARITHMIC)
        p = bc.get_price(Decimal('0'))
        assert p == bc.config.base_price  # returns base_price for supply=0

    def test_logarithmic_price_increases(self):
        bc = _make_bc(CurveType.LOGARITHMIC)
        p1 = bc.get_price(Decimal('100'))
        p2 = bc.get_price(Decimal('200'))
        assert p2 > p1

    def test_sigmoid_price_increases(self):
        bc = _make_bc(CurveType.SIGMOID)
        p1 = bc.get_price(Decimal('100'))
        p2 = bc.get_price(Decimal('200'))
        assert p2 > p1

    def test_bancor_price_positive(self):
        bc = _make_bc(CurveType.BANCOR)
        p = bc.get_price()
        assert p > 0

    def test_augmented_bonding_curve_hatch_phase(self):
        bc = _make_bc(CurveType.AUGMENTED_BONDING_CURVE, initial_supply=Decimal('10000'))
        hatch_limit = bc.config.max_supply * Decimal('0.1')
        p = bc.get_price(Decimal('1'))  # well within hatch phase
        assert p == bc.config.base_price

    # --- calculate_buy_cost ---

    def test_linear_buy_cost_positive(self):
        bc = _make_bc(CurveType.LINEAR)
        cost = bc.calculate_buy_cost(Decimal('100'))
        assert cost > 0

    def test_bancor_buy_cost_positive(self):
        bc = _make_bc(CurveType.BANCOR)
        cost = bc.calculate_buy_cost(Decimal('100'))
        assert cost > 0

    def test_buy_cost_zero_amount_returns_zero(self):
        bc = _make_bc(CurveType.LINEAR)
        assert bc.calculate_buy_cost(Decimal('0')) == Decimal('0')

    # --- calculate_sell_return ---

    def test_linear_sell_return_positive(self):
        bc = _make_bc(CurveType.LINEAR)
        ret = bc.calculate_sell_return(Decimal('100'))
        assert ret > 0

    def test_sell_return_zero_amount_returns_zero(self):
        bc = _make_bc(CurveType.LINEAR)
        assert bc.calculate_sell_return(Decimal('0')) == Decimal('0')

    def test_sell_return_exceeding_supply_returns_zero(self):
        bc = _make_bc(CurveType.LINEAR, initial_supply=Decimal('50'))
        assert bc.calculate_sell_return(Decimal('100')) == Decimal('0')

    # --- execute_buy / execute_sell ---

    def test_execute_buy_updates_supply(self):
        bc = _make_bc(CurveType.LINEAR)
        old_supply = bc.current_supply
        result = bc.execute_buy('buyer1', Decimal('100'), Decimal('999999'))
        assert bc.current_supply == old_supply + Decimal('100')
        assert 'cost' in result

    def test_execute_buy_exceeds_max_cost_raises(self):
        bc = _make_bc(CurveType.LINEAR)
        with pytest.raises(MarketplaceError):
            bc.execute_buy('buyer1', Decimal('100'), Decimal('0.00001'))

    def test_execute_sell_updates_supply(self):
        bc = _make_bc(CurveType.LINEAR, initial_supply=Decimal('10000'))
        old_supply = bc.current_supply
        result = bc.execute_sell('seller1', Decimal('100'), Decimal('0'))
        assert bc.current_supply == old_supply - Decimal('100')
        assert 'return_value' in result

    def test_execute_sell_below_min_return_raises(self):
        bc = _make_bc(CurveType.LINEAR, initial_supply=Decimal('10000'))
        with pytest.raises(MarketplaceError):
            bc.execute_sell('seller1', Decimal('100'), Decimal('99999999'))

    # --- get_market_data ---

    def test_get_market_data_keys(self):
        bc = _make_bc(CurveType.LINEAR)
        md = bc.get_market_data()
        assert hasattr(md, 'price')
        assert hasattr(md, 'supply')
        assert hasattr(md, 'state')

    # --- BondingCurveEngine ---

    def test_engine_start_stop(self):
        eng = BondingCurveEngine(config={})
        assert eng.start() is True
        assert eng.is_active is True
        assert eng.stop() is True
        assert eng.is_active is False

    def test_engine_add_and_buy_sell(self):
        eng = BondingCurveEngine(config={})
        eng.start()
        cfg = BondingCurveConfig(
            curve_type=CurveType.LINEAR, reserve_ratio=Decimal('0.5'),
            slope=Decimal('0.001'), base_price=Decimal('1.0'),
            max_supply=Decimal('1000000'), initial_supply=Decimal('10000'),
            reserve_balance=Decimal('10000'))
        eng.add_bonding_curve(TokenType.SERVICE, cfg)
        result = eng.buy_tokens('b1', TokenType.SERVICE, Decimal('100'), Decimal('999999'))
        assert 'cost' in result
        result2 = eng.sell_tokens('s1', TokenType.SERVICE, Decimal('50'), Decimal('0'))
        assert 'return_value' in result2

    def test_engine_missing_curve_raises(self):
        eng = BondingCurveEngine(config={})
        with pytest.raises(TokenError):
            eng.get_price(TokenType.GOVERNANCE)


# ============================================================================
# 5. engines/token_economics.py — ~12 tests
# ============================================================================

class TestTokenEconomics:

    def _engine(self) -> TokenEconomicsEngine:
        return TokenEconomicsEngine(config={})

    def test_create_agent(self):
        eng = self._engine()
        agent = eng.create_agent('a1', {TokenType.AGIX: Decimal('1000')})
        assert agent.agent_id == 'a1'
        bal = eng.get_agent_balance('a1', TokenType.AGIX)
        assert bal.amount == Decimal('1000')

    def test_create_duplicate_agent_raises(self):
        eng = self._engine()
        eng.create_agent('dup')
        with pytest.raises(ValueError, match="already exists"):
            eng.create_agent('dup')

    def test_transfer_tokens(self):
        eng = self._engine()
        eng.create_agent('from', {TokenType.AGIX: Decimal('1000')})
        eng.create_agent('to', {TokenType.AGIX: Decimal('0')})
        tx = eng.transfer_tokens('from', 'to', TokenType.AGIX, Decimal('100'))
        assert tx.amount == Decimal('100')
        # Receiver gets exactly 100 (fee deducted from sender)
        assert eng.get_agent_balance('to', TokenType.AGIX).amount == Decimal('100')
        # Sender loses 100 + fee
        assert eng.get_agent_balance('from', TokenType.AGIX).amount < Decimal('900')

    def test_transfer_insufficient_funds_raises(self):
        eng = self._engine()
        eng.create_agent('poor', {TokenType.AGIX: Decimal('1')})
        eng.create_agent('rich')
        with pytest.raises(InsufficientFundsError):
            eng.transfer_tokens('poor', 'rich', TokenType.AGIX, Decimal('9999'))

    def test_stake_tokens(self):
        eng = self._engine()
        eng.create_agent('staker', {TokenType.AGIX: Decimal('500')})
        result = eng.stake_tokens('staker', TokenType.AGIX, Decimal('200'))
        assert result is True
        bal = eng.get_agent_balance('staker', TokenType.AGIX)
        assert bal.locked_amount == Decimal('200')
        assert bal.available_amount == Decimal('300')

    def test_unstake_tokens(self):
        eng = self._engine()
        eng.create_agent('staker', {TokenType.AGIX: Decimal('500')})
        eng.stake_tokens('staker', TokenType.AGIX, Decimal('200'))
        result = eng.unstake_tokens('staker', TokenType.AGIX, Decimal('200'))
        assert result is True
        bal = eng.get_agent_balance('staker', TokenType.AGIX)
        assert bal.locked_amount == Decimal('0')

    def test_apply_inflation(self):
        eng = self._engine()
        # Force last inflation update far in the past
        for si in eng.token_supplies.values():
            si.last_inflation_update = time.time() - 200000
        amount = eng.apply_inflation(TokenType.AGIX)
        assert amount > 0

    def test_get_token_price(self):
        eng = self._engine()
        price = eng.get_token_price(TokenType.AGIX)
        assert price > 0

    def test_calculate_market_cap(self):
        eng = self._engine()
        cap = eng.calculate_market_cap(TokenType.AGIX)
        assert cap > 0

    def test_get_token_metrics(self):
        eng = self._engine()
        m = eng.get_token_metrics(TokenType.AGIX)
        assert 'token_type' in m
        assert 'price' in m
        assert 'market_cap' in m
        assert 'circulating_supply' in m

    def test_token_supply_info_circulating(self):
        si = TokenSupplyInfo(
            current_supply=Decimal('1000'), max_supply=Decimal('10000'),
            burned_supply=Decimal('200'), inflation_rate=Decimal('0.02'),
            last_inflation_update=time.time())
        assert si.circulating_supply == Decimal('800')

    def test_staking_pool_calculate_rewards(self):
        pool = StakingPool(token_type=TokenType.AGIX, reward_rate=Decimal('0.05'))
        pool.stakers['a1'] = Decimal('1000')
        # 1 year duration
        one_year = 365 * 24 * 3600
        reward = pool.calculate_rewards('a1', float(one_year))
        assert reward == Decimal('1000') * Decimal('0.05')  # 50

    def test_start_stop(self):
        eng = self._engine()
        assert eng.start() is True
        assert eng.is_active is True
        assert eng.stop() is True
        assert eng.is_active is False


# ============================================================================
# 6. analysis/game_theory.py — ~8 tests
# ============================================================================

def _simple_pd_game(analyzer: GameTheoryAnalyzer) -> Game:
    """Create a simple Prisoner's Dilemma game for testing."""
    p1 = Player(player_id='p1', strategies=['cooperate', 'defect'])
    p2 = Player(player_id='p2', strategies=['cooperate', 'defect'])

    # Classic Prisoner's Dilemma payoff matrices
    # _get_player_payoff uses payoff[own_strategy_idx, other_strategy_idx]
    # p1 matrix: rows=p1 strats, cols=p2 strats
    # p2 matrix: rows=p2 strats, cols=p1 strats (symmetric PD → same matrix)
    payoff_p1 = np.array([[3, 0], [5, 1]], dtype=float)
    payoff_p2 = np.array([[3, 0], [5, 1]], dtype=float)

    game = Game(
        game_id='pd_test',
        game_type=GameType.NORMAL_FORM,
        players=[p1, p2],
        payoff_matrices={'p1': payoff_p1, 'p2': payoff_p2},
        description='Prisoner Dilemma test',
    )
    analyzer.games[game.game_id] = game
    return game


class TestGameTheory:

    def _analyzer(self) -> GameTheoryAnalyzer:
        return GameTheoryAnalyzer(config={})

    def test_game_and_player_dataclass(self):
        p = Player(player_id='x', strategies=['a', 'b'])
        assert p.player_id == 'x'
        assert p.rationality_level == 1.0

    def test_create_agi_service_game(self):
        a = self._analyzer()
        game = a.create_agi_service_game(
            providers=['prov1'], consumers=['cons1'],
            service_qualities={'prov1': 0.8}, prices={'prov1': 1.0})
        assert game.game_type == GameType.NORMAL_FORM
        assert len(game.players) == 2

    def test_find_nash_equilibria_pd(self):
        a = self._analyzer()
        game = _simple_pd_game(a)
        equilibria = a.find_nash_equilibria(game)
        # (defect, defect) is the unique pure Nash equilibrium
        pure_eq = [eq for eq in equilibria if eq.strategy_profile.strategies]
        assert any(
            eq.strategy_profile.strategies.get('p1') == 'defect'
            and eq.strategy_profile.strategies.get('p2') == 'defect'
            for eq in pure_eq
        )

    def test_is_nash_equilibrium_true(self):
        a = self._analyzer()
        game = _simple_pd_game(a)
        sp = StrategyProfile(strategies={'p1': 'defect', 'p2': 'defect'})
        assert a._is_nash_equilibrium(game, sp) is True

    def test_is_nash_equilibrium_false(self):
        a = self._analyzer()
        game = _simple_pd_game(a)
        sp = StrategyProfile(strategies={'p1': 'cooperate', 'p2': 'cooperate'})
        assert a._is_nash_equilibrium(game, sp) is False

    def test_analyze_mechanism_efficiency(self):
        a = self._analyzer()
        game = _simple_pd_game(a)
        analysis = a.analyze_mechanism_efficiency(game)
        assert 'mechanism_properties' in analysis
        assert 'has_dominant_strategy' in analysis['mechanism_properties']

    def test_dominant_strategy_in_pd(self):
        a = self._analyzer()
        game = _simple_pd_game(a)
        dom = a._check_dominant_strategies(game)
        # Both players should have 'defect' as dominant
        assert dom['exists'] is True

    def test_start_stop(self):
        a = self._analyzer()
        assert a.start() is True
        assert a.stop() is True


# ============================================================================
# 7. algorithms/resource_allocator.py — ~10 tests
# ============================================================================

def _make_provider(pid='prov1', amount=Decimal('100'), cost=Decimal('1'),
                   reputation=0.8, reliability=0.9) -> ResourceProvider:
    resources = {
        ResourceType.GPU: Resource(
            resource_type=ResourceType.GPU, amount=amount,
            cost_per_unit=cost, provider_id=pid, quality_score=0.9),
    }
    return ResourceProvider(provider_id=pid, resources=resources,
                            reputation_score=reputation,
                            reliability_score=reliability)


def _make_request(rid='req1', amount=Decimal('10'), budget=Decimal('999'),
                  deadline_offset=3600) -> ServiceRequest:
    return ServiceRequest(
        request_id=rid, requester_id='user1', service_type='compute',
        resource_requirements={ResourceType.GPU: amount},
        max_budget=budget, deadline=time.time() + deadline_offset,
        quality_requirements={'min_quality': 0.5})


class TestResourceAllocator:

    def _allocator(self, strategy='utility_maximization') -> ResourceAllocator:
        return ResourceAllocator(config={'allocation_strategy': strategy})

    def test_register_provider(self):
        alloc = self._allocator()
        prov = _make_provider()
        assert alloc.register_provider(prov) is True
        assert 'prov1' in alloc.providers

    def test_submit_and_allocate(self):
        alloc = self._allocator()
        alloc.register_provider(_make_provider())
        result = alloc.submit_resource_request(_make_request())
        assert result['success'] is True

    def test_submit_request_queued_when_no_provider(self):
        alloc = self._allocator()
        result = alloc.submit_resource_request(_make_request())
        assert result['success'] is False
        assert len(alloc.pending_requests) == 1

    def test_release_allocation(self):
        alloc = self._allocator()
        alloc.register_provider(_make_provider())
        alloc.submit_resource_request(_make_request('r1'))
        assert alloc.release_allocation('r1') is True
        assert 'r1' not in alloc.active_allocations

    def test_release_nonexistent_returns_false(self):
        alloc = self._allocator()
        assert alloc.release_allocation('nope') is False

    def test_first_fit_strategy(self):
        alloc = self._allocator('first_fit')
        alloc.register_provider(_make_provider())
        result = alloc.submit_resource_request(_make_request())
        assert result['success'] is True

    def test_best_fit_strategy(self):
        alloc = self._allocator('best_fit')
        alloc.register_provider(_make_provider('a', Decimal('15')))
        alloc.register_provider(_make_provider('b', Decimal('100')))
        result = alloc.submit_resource_request(_make_request(amount=Decimal('10')))
        assert result['success'] is True

    def test_utilization_metrics(self):
        alloc = self._allocator()
        alloc.register_provider(_make_provider())
        alloc.submit_resource_request(_make_request())
        metrics = alloc.get_utilization_metrics()
        assert isinstance(metrics, dict)

    def test_start_stop(self):
        alloc = self._allocator()
        assert alloc.start() is True
        assert alloc.stop() is True

    def test_budget_insufficient(self):
        alloc = self._allocator()
        alloc.register_provider(_make_provider(cost=Decimal('1000')))
        result = alloc.submit_resource_request(
            _make_request(amount=Decimal('10'), budget=Decimal('1')))
        # Should fail or be queued
        assert result['success'] is False


# ============================================================================
# 8. systems/reputation_system.py — ~10 tests
# ============================================================================

class TestReputationSystem:

    def _system(self) -> ReputationSystem:
        return ReputationSystem(config={})

    def test_initialize_agent_reputation(self):
        rs = self._system()
        assert rs.initialize_agent_reputation('a1') is True
        assert 'a1' in rs.reputation_scores

    def test_initialize_idempotent(self):
        rs = self._system()
        rs.initialize_agent_reputation('a1')
        assert rs.initialize_agent_reputation('a1') is True  # no error

    def test_submit_reputation_event_updates_score(self):
        np.random.seed(42)
        rs = self._system()
        rs.initialize_agent_reputation('a1')
        # Register enough validators
        for i in range(6):
            rs.register_validator(ReputationValidator(
                validator_id=f'v{i}', validator_type='agent',
                expertise_areas=[ReputationDimension.RELIABILITY],
                validation_history=[], own_reputation=0.9,
                stake_amount=Decimal('200')))
        evt = ReputationEvent(
            event_id=None, agent_id='a1', event_type='service_completed',
            impact=0.8, validator_id='v0',
            evidence={'task': 'test'}, timestamp=time.time())
        result = rs.submit_reputation_event(evt)
        assert result.get('success') is True or result.get('reputation_updated') is True

    def test_get_agent_reputation(self):
        rs = self._system()
        rs.initialize_agent_reputation('a1')
        rep = rs.get_agent_reputation('a1')
        assert rep is not None
        assert 'overall_reputation' in rep
        assert 'reputation_dimensions' in rep

    def test_get_agent_reputation_missing(self):
        rs = self._system()
        assert rs.get_agent_reputation('nonexistent') is None

    def test_update_trust_relationship(self):
        rs = self._system()
        result = rs.update_trust_relationship('a1', 'a2', 0.8, 'collaboration')
        assert result is True
        assert ('a1', 'a2') in rs.trust_relationships

    def test_trust_score_range_clamped(self):
        rs = self._system()
        # Score > 1.0 should be clamped
        rs.update_trust_relationship('a1', 'a2', 1.5, 'general')
        rel = rs.trust_relationships[('a1', 'a2')]
        assert rel.trust_score <= 1.0

    def test_calculate_transitive_trust(self):
        rs = self._system()
        rs.update_trust_relationship('a', 'b', 0.9, 'general')
        rs.update_trust_relationship('b', 'c', 0.8, 'general')
        trust = rs.calculate_transitive_trust('a', 'c')
        assert trust > 0

    def test_check_trust_threshold(self):
        rs = self._system()
        rs.initialize_agent_reputation('a1')
        # Initial overall_score is 0.5
        assert rs.check_trust_threshold('a1', 0.4) is True
        assert rs.check_trust_threshold('a1', 0.9) is False

    def test_start_stop(self):
        rs = self._system()
        assert rs.start() is True
        assert rs.stop() is True


# ============================================================================
# 9. systems/value_alignment.py — ~8 tests
# ============================================================================

class TestValueAlignment:

    def _engine(self) -> ValueAlignmentEngine:
        return ValueAlignmentEngine(config={})

    def test_register_agent(self):
        eng = self._engine()
        assert eng.register_agent('a1') is True
        assert 'a1' in eng.agent_alignments

    def test_register_agent_idempotent(self):
        eng = self._engine()
        eng.register_agent('a1')
        assert eng.register_agent('a1') is True

    def test_measure_value_alignment(self):
        eng = self._engine()
        eng.register_agent('a1')
        m = ValueMeasurement(
            measurement_id=None, agent_id='a1',
            value_category=ValueCategory.BENEFICENCE,
            measured_value=0.7, impact_magnitude=0.5,
            validator_ids=['v1'], evidence={'test': True},
            timestamp=time.time())
        result = eng.measure_value_alignment(m)
        assert result['success'] is True

    def test_measure_invalid_value_fails(self):
        eng = self._engine()
        eng.register_agent('a1')
        m = ValueMeasurement(
            measurement_id=None, agent_id='a1',
            value_category=ValueCategory.BENEFICENCE,
            measured_value=5.0,  # out of range
            impact_magnitude=0.5, validator_ids=['v1'],
            evidence={'t': True}, timestamp=time.time())
        result = eng.measure_value_alignment(m)
        assert result['success'] is False

    def test_provide_human_feedback(self):
        eng = self._engine()
        eng.register_agent('a1')
        feedback = {
            'human_id': 'h1',
            'behavior_description': 'helped with task',
            'value_ratings': {'beneficence': 4.0, 'transparency': 3.5},
            'overall_rating': 4.0,
        }
        assert eng.provide_human_feedback('a1', feedback) is True
        assert len(eng.human_feedback['a1']) == 1

    def test_get_agent_value_profile(self):
        eng = self._engine()
        eng.register_agent('a1')
        profile = eng.get_agent_value_profile('a1')
        assert profile is not None
        assert 'overall_alignment_score' in profile
        assert 'value_alignments' in profile

    def test_get_agent_value_profile_missing(self):
        eng = self._engine()
        assert eng.get_agent_value_profile('nope') is None

    def test_get_system_value_metrics(self):
        eng = self._engine()
        eng.register_agent('a1')
        eng.register_agent('a2')
        metrics = eng.get_system_value_metrics()
        assert 'system_summary' in metrics
        assert metrics['system_summary']['total_agents'] == 2

    def test_start_stop(self):
        eng = self._engine()
        assert eng.start() is True
        assert eng.stop() is True


# ============================================================================
# 10. simulation/marketplace_dynamics.py — ~12 tests
# ============================================================================

def _buy_order(agent='buyer1', price=Decimal('10'), qty=Decimal('5'),
               service='compute', oid=None) -> MarketOrder:
    return MarketOrder(
        order_id=oid or f'buy_{uuid.uuid4().hex[:8]}',
        agent_id=agent, order_type=OrderType.BUY,
        service_type=service, quantity=qty, price=price)


def _sell_order(agent='seller1', price=Decimal('10'), qty=Decimal('5'),
                service='compute', oid=None) -> MarketOrder:
    return MarketOrder(
        order_id=oid or f'sell_{uuid.uuid4().hex[:8]}',
        agent_id=agent, order_type=OrderType.SELL,
        service_type=service, quantity=qty, price=price)


class TestMarketplaceDynamics:

    def _mp(self) -> MarketplaceDynamics:
        return MarketplaceDynamics(config={})

    def test_create_market(self):
        mp = self._mp()
        assert mp.create_market('compute') is True
        assert 'compute' in mp.markets

    def test_create_market_idempotent(self):
        mp = self._mp()
        mp.create_market('compute')
        assert mp.create_market('compute') is True

    def test_submit_order(self):
        mp = self._mp()
        result = mp.submit_order(_buy_order())
        assert result['success'] is True

    def test_cancel_order(self):
        mp = self._mp()
        order = _buy_order(oid='o1')
        mp.submit_order(order)
        result = mp.cancel_order('o1', 'buyer1')
        assert result['success'] is True
        assert mp.all_orders['o1'].status == OrderStatus.CANCELLED

    def test_cancel_wrong_agent(self):
        mp = self._mp()
        order = _buy_order(oid='o2')
        mp.submit_order(order)
        result = mp.cancel_order('o2', 'imposter')
        assert result['success'] is False

    def test_order_matching(self):
        mp = self._mp()
        mp.submit_order(_buy_order(price=Decimal('12'), qty=Decimal('5')))
        result = mp.submit_order(_sell_order(price=Decimal('10'), qty=Decimal('5')))
        assert result['success'] is True
        # Check that a trade was executed
        assert len(mp.all_trades) >= 1

    def test_no_match_when_spread_wrong(self):
        mp = self._mp()
        mp.submit_order(_buy_order(price=Decimal('5')))
        mp.submit_order(_sell_order(price=Decimal('10')))
        assert len(mp.all_trades) == 0

    def test_create_auction(self):
        mp = self._mp()
        result = mp.create_auction({
            'auctioneer_id': 'a1', 'service_type': 'compute',
            'item_description': 'GPU hours', 'auction_type': 'english',
            'starting_price': '1', 'reserve_price': '0',
        })
        assert result['success'] is True

    def test_place_bid_english(self):
        mp = self._mp()
        auction_res = mp.create_auction({
            'auctioneer_id': 'a1', 'service_type': 'compute',
            'item_description': 'GPU', 'auction_type': 'english',
            'starting_price': '1',
        })
        aid = auction_res['auction_id']
        bid_res = mp.place_bid(aid, 'b1', Decimal('5'))
        assert bid_res['success'] is True

    def test_vickrey_second_price(self):
        mp = self._mp()
        auction_res = mp.create_auction({
            'auctioneer_id': 'a1', 'service_type': 'compute',
            'item_description': 'GPU', 'auction_type': 'vickrey',
            'starting_price': '1',
        })
        aid = auction_res['auction_id']
        # Place bids directly into auction (Vickrey is sealed-bid)
        auction = mp.active_auctions[aid]
        auction['bids'].append({'bid_id': 'b1', 'bidder_id': 'bidder1',
                                'amount': Decimal('100'), 'timestamp': time.time()})
        auction['bids'].append({'bid_id': 'b2', 'bidder_id': 'bidder2',
                                'amount': Decimal('80'), 'timestamp': time.time()})
        auction['bids'].append({'bid_id': 'b3', 'bidder_id': 'bidder3',
                                'amount': Decimal('60'), 'timestamp': time.time()})
        result = mp._finalize_auction(aid)
        # Winner is bidder1 but pays second-highest price = 80
        assert result['winner'] == 'bidder1'
        assert result['final_price'] == str(Decimal('80'))

    def test_get_market_data(self):
        mp = self._mp()
        mp.create_market('compute')
        md = mp.get_market_data('compute')
        assert md is not None

    def test_get_order_book(self):
        mp = self._mp()
        mp.submit_order(_buy_order(price=Decimal('10')))
        mp.submit_order(_sell_order(price=Decimal('15')))
        book = mp.get_order_book('compute')
        assert 'bids' in book
        assert 'asks' in book
        assert len(book['bids']) == 1
        assert len(book['asks']) == 1

    def test_start_stop(self):
        mp = self._mp()
        assert mp.start() is True
        assert mp.stop() is True
