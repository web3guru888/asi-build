"""
Bonding Curves Engine
====================

Advanced bonding curve implementations for automated market making
and price discovery in the AGI token ecosystem.
"""

import logging
import math
import time
from dataclasses import dataclass
from decimal import Decimal, getcontext
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.base_engine import BaseEconomicEngine, EconomicEvent
from ..core.exceptions import MarketplaceError, TokenError
from ..core.types import MarketData, MarketState, TokenType

# Set decimal precision for financial calculations
getcontext().prec = 28

logger = logging.getLogger(__name__)


class CurveType(Enum):
    """Types of bonding curves"""

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    SIGMOID = "sigmoid"
    BANCOR = "bancor"
    AUGMENTED_BONDING_CURVE = "augmented"


@dataclass
class BondingCurveConfig:
    """Configuration for a bonding curve"""

    curve_type: CurveType
    reserve_ratio: Decimal  # For Bancor curves
    slope: Decimal  # For linear curves
    base_price: Decimal  # Base price parameter
    max_supply: Decimal  # Maximum token supply
    initial_supply: Decimal  # Initial token supply
    reserve_balance: Decimal  # Reserve token balance


class BondingCurve:
    """
    Advanced bonding curve implementation supporting multiple curve types
    and sophisticated price discovery mechanisms.
    """

    def __init__(self, config: BondingCurveConfig):
        self.config = config
        self.current_supply = config.initial_supply
        self.reserve_balance = config.reserve_balance
        self.price_history: List[Tuple[float, Decimal]] = []

        # Select pricing function based on curve type
        self.pricing_function = self._get_pricing_function()

    def _get_pricing_function(self) -> Callable[[Decimal], Decimal]:
        """Get the appropriate pricing function for the curve type"""
        if self.config.curve_type == CurveType.LINEAR:
            return self._linear_price
        elif self.config.curve_type == CurveType.EXPONENTIAL:
            return self._exponential_price
        elif self.config.curve_type == CurveType.LOGARITHMIC:
            return self._logarithmic_price
        elif self.config.curve_type == CurveType.SIGMOID:
            return self._sigmoid_price
        elif self.config.curve_type == CurveType.BANCOR:
            return self._bancor_price
        elif self.config.curve_type == CurveType.AUGMENTED_BONDING_CURVE:
            return self._augmented_bonding_curve_price
        else:
            raise ValueError(f"Unsupported curve type: {self.config.curve_type}")

    def _linear_price(self, supply: Decimal) -> Decimal:
        """Linear bonding curve: P = base_price + slope * supply"""
        return self.config.base_price + (self.config.slope * supply)

    def _exponential_price(self, supply: Decimal) -> Decimal:
        """Exponential bonding curve: P = base_price * e^(slope * supply)"""
        exponent = float(self.config.slope * supply)
        return self.config.base_price * Decimal(str(math.exp(exponent)))

    def _logarithmic_price(self, supply: Decimal) -> Decimal:
        """Logarithmic bonding curve: P = base_price * ln(1 + slope * supply)"""
        if supply == 0:
            return self.config.base_price
        arg = float(Decimal("1") + self.config.slope * supply)
        return self.config.base_price * Decimal(str(math.log(arg)))

    def _sigmoid_price(self, supply: Decimal) -> Decimal:
        """Sigmoid bonding curve: P = base_price / (1 + e^(-slope * (supply - mid_point)))"""
        mid_point = self.config.max_supply / Decimal("2")
        exponent = float(-self.config.slope * (supply - mid_point))
        denominator = Decimal("1") + Decimal(str(math.exp(exponent)))
        return self.config.base_price / denominator

    def _bancor_price(self, supply: Decimal) -> Decimal:
        """Bancor formula: P = reserve_balance * ((1 + supply_change/current_supply)^(1/reserve_ratio) - 1)"""
        if supply == 0 or self.current_supply == 0:
            return self.config.base_price

        # Bancor formula: Price = Reserve_Balance / (Current_Supply * Reserve_Ratio)
        price = self.reserve_balance / (self.current_supply * self.config.reserve_ratio)
        return price

    def _augmented_bonding_curve_price(self, supply: Decimal) -> Decimal:
        """Augmented bonding curve with hatch and commons phases"""
        # This is a simplified version of the Augmented Bonding Curve
        # In reality, it would have multiple phases and complex mechanisms

        hatch_supply = self.config.max_supply * Decimal("0.1")  # 10% for hatch

        if supply <= hatch_supply:
            # Hatch phase: fixed price
            return self.config.base_price
        else:
            # Commons phase: Bancor-style curve
            commons_supply = supply - hatch_supply
            return self._bancor_price(commons_supply) * Decimal("1.1")  # 10% premium

    def get_price(self, supply: Optional[Decimal] = None) -> Decimal:
        """Get current price or price at specific supply level"""
        target_supply = supply if supply is not None else self.current_supply
        price = self.pricing_function(target_supply)

        # Record price history
        self.price_history.append((time.time(), price))

        # Keep only last 1000 price points
        if len(self.price_history) > 1000:
            self.price_history = self.price_history[-1000:]

        return price

    def calculate_buy_cost(self, token_amount: Decimal) -> Decimal:
        """Calculate cost to buy tokens using integral of bonding curve"""
        if token_amount <= 0:
            return Decimal("0")

        if self.config.curve_type == CurveType.LINEAR:
            return self._linear_buy_cost(token_amount)
        elif self.config.curve_type == CurveType.BANCOR:
            return self._bancor_buy_cost(token_amount)
        else:
            # For other curves, use numerical integration (simplified)
            return self._numerical_integration_buy_cost(token_amount)

    def _linear_buy_cost(self, token_amount: Decimal) -> Decimal:
        """Calculate buy cost for linear curve using integration"""
        # Integral of (base_price + slope * x) from current_supply to current_supply + token_amount
        s1 = self.current_supply
        s2 = self.current_supply + token_amount

        cost = self.config.base_price * token_amount + self.config.slope * (
            s2 * s2 - s1 * s1
        ) / Decimal("2")
        return cost

    def _bancor_buy_cost(self, token_amount: Decimal) -> Decimal:
        """Calculate buy cost for Bancor curve"""
        if token_amount <= 0:
            return Decimal("0")

        # Bancor buy formula
        new_supply = self.current_supply + token_amount
        ratio = new_supply / self.current_supply

        # Cost = reserve_balance * ((ratio ^ reserve_ratio) - 1)
        power = float(self.config.reserve_ratio)
        cost = self.reserve_balance * (Decimal(str(float(ratio) ** power)) - Decimal("1"))

        return cost

    def _numerical_integration_buy_cost(self, token_amount: Decimal, steps: int = 1000) -> Decimal:
        """Numerical integration for complex curves"""
        step_size = token_amount / Decimal(str(steps))
        total_cost = Decimal("0")

        for i in range(steps):
            supply_at_step = self.current_supply + (Decimal(str(i)) * step_size)
            price_at_step = self.pricing_function(supply_at_step)
            total_cost += price_at_step * step_size

        return total_cost

    def calculate_sell_return(self, token_amount: Decimal) -> Decimal:
        """Calculate return from selling tokens"""
        if token_amount <= 0 or token_amount > self.current_supply:
            return Decimal("0")

        if self.config.curve_type == CurveType.LINEAR:
            return self._linear_sell_return(token_amount)
        elif self.config.curve_type == CurveType.BANCOR:
            return self._bancor_sell_return(token_amount)
        else:
            return self._numerical_integration_sell_return(token_amount)

    def _linear_sell_return(self, token_amount: Decimal) -> Decimal:
        """Calculate sell return for linear curve"""
        s1 = self.current_supply - token_amount
        s2 = self.current_supply

        return_value = self.config.base_price * token_amount + self.config.slope * (
            s2 * s2 - s1 * s1
        ) / Decimal("2")
        return return_value

    def _bancor_sell_return(self, token_amount: Decimal) -> Decimal:
        """Calculate sell return for Bancor curve"""
        if token_amount <= 0:
            return Decimal("0")

        new_supply = self.current_supply - token_amount
        ratio = new_supply / self.current_supply

        # Return = reserve_balance * (1 - (ratio ^ reserve_ratio))
        power = float(self.config.reserve_ratio)
        return_value = self.reserve_balance * (Decimal("1") - Decimal(str(float(ratio) ** power)))

        return return_value

    def _numerical_integration_sell_return(
        self, token_amount: Decimal, steps: int = 1000
    ) -> Decimal:
        """Numerical integration for sell return on complex curves"""
        step_size = token_amount / Decimal(str(steps))
        total_return = Decimal("0")

        for i in range(steps):
            supply_at_step = self.current_supply - (Decimal(str(i)) * step_size)
            price_at_step = self.pricing_function(supply_at_step)
            total_return += price_at_step * step_size

        return total_return

    def execute_buy(
        self, buyer_id: str, token_amount: Decimal, max_cost: Decimal
    ) -> Dict[str, Any]:
        """Execute a buy order on the bonding curve"""
        if token_amount <= 0:
            raise ValueError("Token amount must be positive")

        cost = self.calculate_buy_cost(token_amount)
        if cost > max_cost:
            raise MarketplaceError(f"Buy cost {cost} exceeds maximum {max_cost}")

        # Update supply and reserve balance
        self.current_supply += token_amount
        if self.config.curve_type == CurveType.BANCOR:
            self.reserve_balance += cost

        return {
            "buyer_id": buyer_id,
            "token_amount": str(token_amount),
            "cost": str(cost),
            "new_supply": str(self.current_supply),
            "new_price": str(self.get_price()),
            "timestamp": time.time(),
        }

    def execute_sell(
        self, seller_id: str, token_amount: Decimal, min_return: Decimal
    ) -> Dict[str, Any]:
        """Execute a sell order on the bonding curve"""
        if token_amount <= 0:
            raise ValueError("Token amount must be positive")

        if token_amount > self.current_supply:
            raise MarketplaceError(
                f"Cannot sell {token_amount} tokens, only {self.current_supply} available"
            )

        return_value = self.calculate_sell_return(token_amount)
        if return_value < min_return:
            raise MarketplaceError(f"Sell return {return_value} below minimum {min_return}")

        # Update supply and reserve balance
        self.current_supply -= token_amount
        if self.config.curve_type == CurveType.BANCOR:
            self.reserve_balance -= return_value

        return {
            "seller_id": seller_id,
            "token_amount": str(token_amount),
            "return_value": str(return_value),
            "new_supply": str(self.current_supply),
            "new_price": str(self.get_price()),
            "timestamp": time.time(),
        }

    def get_market_data(self) -> MarketData:
        """Get current market data for this bonding curve"""
        current_price = self.get_price()

        # Calculate 24h volume and price change (simplified)
        recent_history = [(t, p) for t, p in self.price_history if time.time() - t < 86400]

        if len(recent_history) >= 2:
            old_price = recent_history[0][1]
            price_change = (
                (current_price - old_price) / old_price if old_price > 0 else Decimal("0")
            )
        else:
            price_change = Decimal("0")

        # Determine market state
        if abs(price_change) > Decimal("0.1"):
            state = MarketState.VOLATILE
        elif price_change > Decimal("0.05"):
            state = MarketState.OVER_SUPPLY
        elif price_change < Decimal("-0.05"):
            state = MarketState.UNDER_SUPPLY
        else:
            state = MarketState.BALANCED

        return MarketData(
            timestamp=time.time(),
            token_type=TokenType.SERVICE,  # Default, should be configurable
            price=current_price,
            volume=Decimal("0"),  # Would need to track actual volume
            market_cap=self.current_supply * current_price,
            supply=self.current_supply,
            demand=Decimal("0"),  # Would need to track demand
            state=state,
        )


class BondingCurveEngine(BaseEconomicEngine):
    """
    Engine managing multiple bonding curves for different tokens
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.curves: Dict[TokenType, BondingCurve] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self._initialize_curves()

    def _initialize_curves(self):
        """Initialize bonding curves for different token types"""
        curves_config = self.config.get("bonding_curves", {})

        for token_type_str, curve_config in curves_config.items():
            try:
                token_type = TokenType(token_type_str)

                bonding_config = BondingCurveConfig(
                    curve_type=CurveType(curve_config.get("type", "linear")),
                    reserve_ratio=Decimal(str(curve_config.get("reserve_ratio", "0.5"))),
                    slope=Decimal(str(curve_config.get("slope", "0.001"))),
                    base_price=Decimal(str(curve_config.get("base_price", "1.0"))),
                    max_supply=Decimal(str(curve_config.get("max_supply", "1000000"))),
                    initial_supply=Decimal(str(curve_config.get("initial_supply", "10000"))),
                    reserve_balance=Decimal(str(curve_config.get("reserve_balance", "10000"))),
                )

                self.curves[token_type] = BondingCurve(bonding_config)

            except Exception as e:
                logger.error(f"Failed to initialize bonding curve for {token_type_str}: {e}")

    def start(self) -> bool:
        """Start the bonding curve engine"""
        try:
            self.is_active = True
            self.metrics["start_time"] = time.time()
            self.log_event("bonding_curve_engine_started")
            logger.info("Bonding Curve Engine started")
            return True
        except Exception as e:
            logger.error(f"Failed to start Bonding Curve Engine: {e}")
            return False

    def stop(self) -> bool:
        """Stop the bonding curve engine"""
        try:
            self.is_active = False
            self.log_event("bonding_curve_engine_stopped")
            logger.info("Bonding Curve Engine stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop Bonding Curve Engine: {e}")
            return False

    def process_event(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process bonding curve events"""
        if not self.is_active:
            return {"error": "Engine not active"}

        try:
            if event.event_type == "buy_tokens":
                return self._process_buy_order(event)
            elif event.event_type == "sell_tokens":
                return self._process_sell_order(event)
            elif event.event_type == "get_price":
                return self._process_price_query(event)
            else:
                return {"error": f"Unknown event type: {event.event_type}"}
        except Exception as e:
            logger.error(f"Error processing bonding curve event {event.event_type}: {e}")
            return {"error": str(e)}

    def add_bonding_curve(self, token_type: TokenType, config: BondingCurveConfig):
        """Add a new bonding curve for a token"""
        self.curves[token_type] = BondingCurve(config)
        self.log_event(
            "bonding_curve_added",
            data={"token_type": token_type.value, "curve_type": config.curve_type.value},
        )

    def get_price(self, token_type: TokenType) -> Decimal:
        """Get current price for a token"""
        if token_type not in self.curves:
            raise TokenError(f"No bonding curve found for {token_type.value}")

        return self.curves[token_type].get_price()

    def buy_tokens(
        self, buyer_id: str, token_type: TokenType, token_amount: Decimal, max_cost: Decimal
    ) -> Dict[str, Any]:
        """Buy tokens using bonding curve"""
        if token_type not in self.curves:
            raise TokenError(f"No bonding curve found for {token_type.value}")

        curve = self.curves[token_type]
        result = curve.execute_buy(buyer_id, token_amount, max_cost)

        # Record trade
        trade_record = {"type": "buy", "token_type": token_type.value, **result}
        self.trade_history.append(trade_record)

        self.log_event(
            "tokens_bought",
            buyer_id,
            {"token_type": token_type.value, "amount": str(token_amount), "cost": result["cost"]},
        )

        return result

    def sell_tokens(
        self, seller_id: str, token_type: TokenType, token_amount: Decimal, min_return: Decimal
    ) -> Dict[str, Any]:
        """Sell tokens using bonding curve"""
        if token_type not in self.curves:
            raise TokenError(f"No bonding curve found for {token_type.value}")

        curve = self.curves[token_type]
        result = curve.execute_sell(seller_id, token_amount, min_return)

        # Record trade
        trade_record = {"type": "sell", "token_type": token_type.value, **result}
        self.trade_history.append(trade_record)

        self.log_event(
            "tokens_sold",
            seller_id,
            {
                "token_type": token_type.value,
                "amount": str(token_amount),
                "return": result["return_value"],
            },
        )

        return result

    def get_all_market_data(self) -> Dict[str, MarketData]:
        """Get market data for all bonding curves"""
        market_data = {}
        for token_type, curve in self.curves.items():
            market_data[token_type.value] = curve.get_market_data()
        return market_data

    def _process_buy_order(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process buy order event"""
        data = event.data
        try:
            result = self.buy_tokens(
                buyer_id=event.agent_id,
                token_type=TokenType(data["token_type"]),
                token_amount=Decimal(data["token_amount"]),
                max_cost=Decimal(data["max_cost"]),
            )
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _process_sell_order(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process sell order event"""
        data = event.data
        try:
            result = self.sell_tokens(
                seller_id=event.agent_id,
                token_type=TokenType(data["token_type"]),
                token_amount=Decimal(data["token_amount"]),
                min_return=Decimal(data["min_return"]),
            )
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _process_price_query(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process price query event"""
        data = event.data
        try:
            token_type = TokenType(data["token_type"])
            price = self.get_price(token_type)
            return {"success": True, "price": str(price)}
        except Exception as e:
            return {"success": False, "error": str(e)}
