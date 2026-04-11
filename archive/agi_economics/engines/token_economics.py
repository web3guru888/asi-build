"""
Token Economics Engine
=====================

Comprehensive token economics engine for AGIX and AGI service tokens.
Handles token supply, inflation, burning, staking, and complex economic mechanisms.
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal, getcontext
from dataclasses import dataclass, field
import time
import logging

from ..core.base_engine import BaseEconomicEngine, EconomicEvent
from ..core.types import (
    TokenType, Agent, TokenBalance, EconomicTransaction, 
    TransactionType, MarketData, MarketState
)
from ..core.exceptions import (
    InsufficientFundsError, InvalidTokenError, TokenError
)

# Set decimal precision for financial calculations
getcontext().prec = 28

logger = logging.getLogger(__name__)

@dataclass
class TokenSupplyInfo:
    """Information about token supply"""
    current_supply: Decimal
    max_supply: Decimal
    burned_supply: Decimal
    inflation_rate: Decimal
    last_inflation_update: float
    
    @property
    def circulating_supply(self) -> Decimal:
        return self.current_supply - self.burned_supply

@dataclass
class StakingPool:
    """Staking pool for a specific token"""
    token_type: TokenType
    total_staked: Decimal = Decimal('0')
    total_rewards: Decimal = Decimal('0')
    reward_rate: Decimal = Decimal('0.05')  # 5% APY
    stakers: Dict[str, Decimal] = field(default_factory=dict)
    last_reward_distribution: float = field(default_factory=time.time)
    
    def calculate_rewards(self, agent_id: str, duration: float) -> Decimal:
        """Calculate staking rewards for an agent"""
        if agent_id not in self.stakers:
            return Decimal('0')
        
        stake_amount = self.stakers[agent_id]
        annual_reward = stake_amount * self.reward_rate
        reward = annual_reward * Decimal(duration) / Decimal(365 * 24 * 3600)
        return reward

class TokenEconomicsEngine(BaseEconomicEngine):
    """
    Advanced token economics engine supporting:
    - Multiple token types (AGIX, service tokens, etc.)
    - Inflation and deflationary mechanisms
    - Staking and rewards
    - Transaction fees and burning
    - Dynamic supply management
    - Economic incentive alignment
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # Token supply tracking
        self.token_supplies: Dict[TokenType, TokenSupplyInfo] = {}
        
        # Agent token balances
        self.agent_balances: Dict[str, Dict[TokenType, TokenBalance]] = {}
        
        # Staking pools
        self.staking_pools: Dict[TokenType, StakingPool] = {}
        
        # Transaction history
        self.transactions: List[EconomicTransaction] = []
        
        # Market data
        self.market_data: Dict[TokenType, List[MarketData]] = {}
        
        # Economic parameters
        self.transaction_fee_rate = Decimal(config.get('transaction_fee_rate', '0.001'))
        self.burn_rate = Decimal(config.get('burn_rate', '0.01'))
        self.inflation_interval = config.get('inflation_interval', 86400)  # Daily
        
        self._initialize_token_supplies()
        self._initialize_staking_pools()
    
    def _initialize_token_supplies(self):
        """Initialize token supply information"""
        initial_supplies = self.config.get('initial_supplies', {})
        max_supplies = self.config.get('max_supplies', {})
        inflation_rates = self.config.get('inflation_rates', {})
        
        for token_type in TokenType:
            supply_info = TokenSupplyInfo(
                current_supply=Decimal(initial_supplies.get(token_type.value, '1000000')),
                max_supply=Decimal(max_supplies.get(token_type.value, '100000000')),
                burned_supply=Decimal('0'),
                inflation_rate=Decimal(inflation_rates.get(token_type.value, '0.02')),
                last_inflation_update=time.time()
            )
            self.token_supplies[token_type] = supply_info
    
    def _initialize_staking_pools(self):
        """Initialize staking pools"""
        reward_rates = self.config.get('staking_reward_rates', {})
        
        for token_type in [TokenType.AGIX, TokenType.SERVICE, TokenType.GOVERNANCE]:
            pool = StakingPool(
                token_type=token_type,
                reward_rate=Decimal(reward_rates.get(token_type.value, '0.05'))
            )
            self.staking_pools[token_type] = pool
    
    def start(self) -> bool:
        """Start the token economics engine"""
        try:
            self.is_active = True
            self.metrics['start_time'] = time.time()
            self.log_event('engine_started', data={'engine_type': 'token_economics'})
            logger.info("Token Economics Engine started")
            return True
        except Exception as e:
            logger.error(f"Failed to start Token Economics Engine: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the token economics engine"""
        try:
            self.is_active = False
            self.log_event('engine_stopped', data={'engine_type': 'token_economics'})
            logger.info("Token Economics Engine stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop Token Economics Engine: {e}")
            return False
    
    def process_event(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process economic events"""
        if not self.is_active:
            return {'error': 'Engine not active'}
        
        try:
            if event.event_type == 'token_transfer':
                return self._process_token_transfer(event)
            elif event.event_type == 'stake_tokens':
                return self._process_staking(event)
            elif event.event_type == 'unstake_tokens':
                return self._process_unstaking(event)
            elif event.event_type == 'distribute_rewards':
                return self._process_reward_distribution(event)
            elif event.event_type == 'burn_tokens':
                return self._process_token_burning(event)
            else:
                return {'error': f'Unknown event type: {event.event_type}'}
        except Exception as e:
            logger.error(f"Error processing event {event.event_type}: {e}")
            return {'error': str(e)}
    
    def create_agent(self, agent_id: str, initial_balances: Dict[TokenType, Decimal] = None) -> Agent:
        """Create a new agent with initial token balances"""
        if agent_id in self.agent_balances:
            raise ValueError(f"Agent {agent_id} already exists")
        
        initial_balances = initial_balances or {}
        token_balances = {}
        
        for token_type in TokenType:
            amount = initial_balances.get(token_type, Decimal('0'))
            token_balances[token_type] = TokenBalance(
                token_type=token_type,
                amount=amount
            )
        
        self.agent_balances[agent_id] = token_balances
        
        # Create agent object
        from ..core.types import AgentType
        agent = Agent(
            agent_id=agent_id,
            agent_type=AgentType.SERVICE_PROVIDER,  # Default type
            reputation_score=0.5,
            trust_score=0.5,
            token_balances=token_balances,
            resources=[]
        )
        
        self.log_event('agent_created', agent_id, {
            'initial_balances': {k.value: str(v) for k, v in initial_balances.items()}
        })
        
        return agent
    
    def transfer_tokens(self, from_agent: str, to_agent: str, 
                       token_type: TokenType, amount: Decimal) -> EconomicTransaction:
        """Transfer tokens between agents"""
        if from_agent not in self.agent_balances:
            raise ValueError(f"Agent {from_agent} not found")
        if to_agent not in self.agent_balances:
            raise ValueError(f"Agent {to_agent} not found")
        
        from_balance = self.agent_balances[from_agent][token_type]
        to_balance = self.agent_balances[to_agent][token_type]
        
        # Calculate fees
        fee = amount * self.transaction_fee_rate
        total_deduction = amount + fee
        
        if from_balance.available_amount < total_deduction:
            raise InsufficientFundsError(
                f"Insufficient {token_type.value} balance. "
                f"Required: {total_deduction}, Available: {from_balance.available_amount}"
            )
        
        # Execute transfer
        from_balance.amount -= total_deduction
        to_balance.amount += amount
        
        # Burn the fee
        self._burn_tokens(token_type, fee)
        
        # Create transaction record
        transaction = EconomicTransaction(
            transaction_id=None,  # Auto-generated
            transaction_type=TransactionType.TOKEN_TRANSFER,
            from_agent=from_agent,
            to_agent=to_agent,
            token_type=token_type,
            amount=amount,
            gas_fee=fee,
            timestamp=time.time()
        )
        
        self.transactions.append(transaction)
        self.log_event('token_transfer', from_agent, {
            'to_agent': to_agent,
            'token_type': token_type.value,
            'amount': str(amount),
            'fee': str(fee)
        })
        
        return transaction
    
    def stake_tokens(self, agent_id: str, token_type: TokenType, amount: Decimal) -> bool:
        """Stake tokens for rewards"""
        if agent_id not in self.agent_balances:
            raise ValueError(f"Agent {agent_id} not found")
        
        if token_type not in self.staking_pools:
            raise InvalidTokenError(f"Token {token_type.value} cannot be staked")
        
        balance = self.agent_balances[agent_id][token_type]
        if balance.available_amount < amount:
            raise InsufficientFundsError(
                f"Insufficient {token_type.value} balance for staking"
            )
        
        # Lock tokens
        balance.locked_amount += amount
        
        # Add to staking pool
        pool = self.staking_pools[token_type]
        pool.total_staked += amount
        if agent_id not in pool.stakers:
            pool.stakers[agent_id] = Decimal('0')
        pool.stakers[agent_id] += amount
        
        self.log_event('tokens_staked', agent_id, {
            'token_type': token_type.value,
            'amount': str(amount),
            'total_staked': str(pool.stakers[agent_id])
        })
        
        return True
    
    def unstake_tokens(self, agent_id: str, token_type: TokenType, amount: Decimal) -> bool:
        """Unstake tokens and claim rewards"""
        if agent_id not in self.agent_balances:
            raise ValueError(f"Agent {agent_id} not found")
        
        if token_type not in self.staking_pools:
            raise InvalidTokenError(f"Token {token_type.value} is not stakeable")
        
        pool = self.staking_pools[token_type]
        if agent_id not in pool.stakers or pool.stakers[agent_id] < amount:
            raise InsufficientFundsError(
                f"Insufficient staked {token_type.value} balance"
            )
        
        # Calculate and distribute rewards
        current_time = time.time()
        duration = current_time - pool.last_reward_distribution
        rewards = pool.calculate_rewards(agent_id, duration)
        
        # Update balances
        balance = self.agent_balances[agent_id][token_type]
        balance.locked_amount -= amount
        balance.amount += rewards  # Add rewards
        
        # Update staking pool
        pool.stakers[agent_id] -= amount
        pool.total_staked -= amount
        pool.total_rewards += rewards
        
        # Mint new tokens for rewards (inflationary)
        self._mint_tokens(token_type, rewards)
        
        self.log_event('tokens_unstaked', agent_id, {
            'token_type': token_type.value,
            'amount': str(amount),
            'rewards': str(rewards),
            'remaining_staked': str(pool.stakers[agent_id])
        })
        
        return True
    
    def _burn_tokens(self, token_type: TokenType, amount: Decimal):
        """Burn tokens from circulation"""
        supply_info = self.token_supplies[token_type]
        supply_info.burned_supply += amount
        
        self.log_event('tokens_burned', data={
            'token_type': token_type.value,
            'amount': str(amount),
            'total_burned': str(supply_info.burned_supply)
        })
    
    def _mint_tokens(self, token_type: TokenType, amount: Decimal):
        """Mint new tokens (for rewards, etc.)"""
        supply_info = self.token_supplies[token_type]
        
        if supply_info.current_supply + amount > supply_info.max_supply:
            amount = supply_info.max_supply - supply_info.current_supply
        
        supply_info.current_supply += amount
        
        self.log_event('tokens_minted', data={
            'token_type': token_type.value,
            'amount': str(amount),
            'total_supply': str(supply_info.current_supply)
        })
    
    def apply_inflation(self, token_type: TokenType) -> Decimal:
        """Apply inflation to token supply"""
        supply_info = self.token_supplies[token_type]
        current_time = time.time()
        
        # Check if it's time for inflation
        time_since_last = current_time - supply_info.last_inflation_update
        if time_since_last < self.inflation_interval:
            return Decimal('0')
        
        # Calculate inflation amount
        inflation_amount = (supply_info.circulating_supply * 
                          supply_info.inflation_rate * 
                          Decimal(time_since_last) / 
                          Decimal(365 * 24 * 3600))  # Annual rate
        
        # Apply inflation
        self._mint_tokens(token_type, inflation_amount)
        supply_info.last_inflation_update = current_time
        
        return inflation_amount
    
    def get_token_price(self, token_type: TokenType, base_currency: TokenType = TokenType.AGIX) -> Decimal:
        """Get current token price using bonding curve or market data"""
        # Simple bonding curve pricing: P = k * S^n
        supply_info = self.token_supplies[token_type]
        k = Decimal('0.001')  # Curve parameter
        n = Decimal('1.5')    # Curve exponent
        
        # Calculate price based on circulating supply
        supply = supply_info.circulating_supply
        if supply == 0:
            return Decimal('0')
        
        price = k * (supply ** n)
        return price
    
    def calculate_market_cap(self, token_type: TokenType) -> Decimal:
        """Calculate market capitalization"""
        supply_info = self.token_supplies[token_type]
        price = self.get_token_price(token_type)
        return supply_info.circulating_supply * price
    
    def get_agent_balance(self, agent_id: str, token_type: TokenType) -> TokenBalance:
        """Get agent's token balance"""
        if agent_id not in self.agent_balances:
            raise ValueError(f"Agent {agent_id} not found")
        return self.agent_balances[agent_id][token_type]
    
    def get_staking_info(self, agent_id: str, token_type: TokenType) -> Dict[str, Any]:
        """Get staking information for an agent"""
        if token_type not in self.staking_pools:
            return {}
        
        pool = self.staking_pools[token_type]
        staked_amount = pool.stakers.get(agent_id, Decimal('0'))
        
        # Calculate pending rewards
        current_time = time.time()
        duration = current_time - pool.last_reward_distribution
        pending_rewards = pool.calculate_rewards(agent_id, duration)
        
        return {
            'staked_amount': str(staked_amount),
            'pending_rewards': str(pending_rewards),
            'reward_rate': str(pool.reward_rate),
            'pool_total_staked': str(pool.total_staked)
        }
    
    def get_token_metrics(self, token_type: TokenType) -> Dict[str, Any]:
        """Get comprehensive token metrics"""
        supply_info = self.token_supplies[token_type]
        price = self.get_token_price(token_type)
        market_cap = self.calculate_market_cap(token_type)
        
        # Calculate velocity (transaction volume / circulating supply)
        recent_transactions = [t for t in self.transactions 
                             if t.token_type == token_type and 
                             time.time() - t.timestamp < 86400]  # Last 24h
        daily_volume = sum(t.amount for t in recent_transactions)
        velocity = (daily_volume / supply_info.circulating_supply 
                   if supply_info.circulating_supply > 0 else Decimal('0'))
        
        return {
            'token_type': token_type.value,
            'current_supply': str(supply_info.current_supply),
            'circulating_supply': str(supply_info.circulating_supply),
            'burned_supply': str(supply_info.burned_supply),
            'max_supply': str(supply_info.max_supply),
            'price': str(price),
            'market_cap': str(market_cap),
            'inflation_rate': str(supply_info.inflation_rate),
            'daily_volume': str(daily_volume),
            'velocity': str(velocity),
            'total_transactions': len([t for t in self.transactions if t.token_type == token_type])
        }
    
    def _process_token_transfer(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process token transfer event"""
        data = event.data
        try:
            transaction = self.transfer_tokens(
                from_agent=data['from_agent'],
                to_agent=data['to_agent'],
                token_type=TokenType(data['token_type']),
                amount=Decimal(data['amount'])
            )
            return {'success': True, 'transaction_id': transaction.transaction_id}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_staking(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process token staking event"""
        data = event.data
        try:
            success = self.stake_tokens(
                agent_id=event.agent_id,
                token_type=TokenType(data['token_type']),
                amount=Decimal(data['amount'])
            )
            return {'success': success}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_unstaking(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process token unstaking event"""
        data = event.data
        try:
            success = self.unstake_tokens(
                agent_id=event.agent_id,
                token_type=TokenType(data['token_type']),
                amount=Decimal(data['amount'])
            )
            return {'success': success}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_reward_distribution(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process reward distribution event"""
        try:
            distributed_rewards = {}
            for token_type, pool in self.staking_pools.items():
                total_distributed = Decimal('0')
                for agent_id in pool.stakers.keys():
                    current_time = time.time()
                    duration = current_time - pool.last_reward_distribution
                    rewards = pool.calculate_rewards(agent_id, duration)
                    
                    if rewards > 0:
                        # Add rewards to agent balance
                        self.agent_balances[agent_id][token_type].amount += rewards
                        total_distributed += rewards
                
                pool.last_reward_distribution = time.time()
                pool.total_rewards += total_distributed
                distributed_rewards[token_type.value] = str(total_distributed)
                
                # Mint tokens for rewards
                if total_distributed > 0:
                    self._mint_tokens(token_type, total_distributed)
            
            return {'success': True, 'distributed_rewards': distributed_rewards}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_token_burning(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process token burning event"""
        data = event.data
        try:
            self._burn_tokens(
                token_type=TokenType(data['token_type']),
                amount=Decimal(data['amount'])
            )
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}