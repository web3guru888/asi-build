"""
Marketplace Dynamics Simulation
===============================

Advanced marketplace simulation with supply/demand modeling, price discovery,
and multi-agent economic interactions in the AGI ecosystem.
"""

import math
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from decimal import Decimal, getcontext
from dataclasses import dataclass, field
from enum import Enum
import time
import logging
import heapq
from collections import defaultdict

from ..core.base_engine import BaseEconomicEngine, EconomicEvent
from ..core.types import (
    TokenType, ResourceType, Agent, ServiceRequest, MarketData, MarketState,
    EconomicTransaction, TransactionType
)
from ..core.exceptions import MarketplaceError, PriceDiscoveryError

# Set decimal precision
getcontext().prec = 28

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Types of market orders"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """Status of market orders"""
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"

class AuctionType(Enum):
    """Types of auctions supported"""
    ENGLISH = "english"  # Ascending price
    DUTCH = "dutch"     # Descending price
    SEALED_BID = "sealed_bid"
    VICKREY = "vickrey"  # Second-price sealed-bid
    DOUBLE = "double"    # Continuous double auction

@dataclass
class MarketOrder:
    """Represents a market order"""
    order_id: str
    agent_id: str
    order_type: OrderType
    service_type: str
    quantity: Decimal
    price: Decimal
    max_price: Optional[Decimal] = None  # For buy orders
    min_price: Optional[Decimal] = None  # For sell orders
    timestamp: float = field(default_factory=time.time)
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = field(default=Decimal('0'))
    
    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity
    
    @property
    def is_buy(self) -> bool:
        return self.order_type == OrderType.BUY
    
    @property
    def is_sell(self) -> bool:
        return self.order_type == OrderType.SELL

@dataclass
class MarketTrade:
    """Represents a completed trade"""
    trade_id: str
    buy_order_id: str
    sell_order_id: str
    buyer_id: str
    seller_id: str
    service_type: str
    quantity: Decimal
    price: Decimal
    timestamp: float = field(default_factory=time.time)

@dataclass
class ServiceMarket:
    """Represents a market for a specific service type"""
    service_type: str
    buy_orders: List[MarketOrder] = field(default_factory=list)
    sell_orders: List[MarketOrder] = field(default_factory=list)
    recent_trades: List[MarketTrade] = field(default_factory=list)
    current_price: Decimal = field(default=Decimal('0'))
    volume_24h: Decimal = field(default=Decimal('0'))
    price_change_24h: Decimal = field(default=Decimal('0'))
    
    def get_best_bid(self) -> Optional[Decimal]:
        """Get highest buy price"""
        active_buys = [o for o in self.buy_orders if o.status == OrderStatus.PENDING]
        return max([o.price for o in active_buys], default=None)
    
    def get_best_ask(self) -> Optional[Decimal]:
        """Get lowest sell price"""
        active_sells = [o for o in self.sell_orders if o.status == OrderStatus.PENDING]
        return min([o.price for o in active_sells], default=None)
    
    def get_spread(self) -> Optional[Decimal]:
        """Get bid-ask spread"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid is not None and best_ask is not None:
            return best_ask - best_bid
        return None

class MarketplaceDynamics(BaseEconomicEngine):
    """
    Advanced marketplace dynamics simulation engine supporting:
    - Continuous double auctions
    - Multiple auction mechanisms
    - Supply and demand modeling
    - Price discovery algorithms
    - Market maker functionality
    - Liquidity provision
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # Service markets
        self.markets: Dict[str, ServiceMarket] = {}
        
        # Order books for each market
        self.order_books: Dict[str, Dict[str, List[MarketOrder]]] = {}
        
        # All orders (for tracking)
        self.all_orders: Dict[str, MarketOrder] = {}
        
        # Trade history
        self.all_trades: List[MarketTrade] = []
        
        # Market makers
        self.market_makers: Dict[str, Dict[str, Any]] = {}
        
        # Price history for each service
        self.price_history: Dict[str, List[Tuple[float, Decimal]]] = {}
        
        # Market parameters
        self.transaction_fee_rate = Decimal(config.get('transaction_fee_rate', '0.001'))
        self.market_maker_fee_rate = Decimal(config.get('market_maker_fee_rate', '0.0005'))
        self.min_order_size = Decimal(config.get('min_order_size', '0.01'))
        self.max_spread_threshold = Decimal(config.get('max_spread_threshold', '0.1'))
        
        # Auction parameters
        self.default_auction_duration = config.get('auction_duration', 3600)  # 1 hour
        self.active_auctions: Dict[str, Dict[str, Any]] = {}
    
    def start(self) -> bool:
        """Start the marketplace dynamics engine"""
        try:
            self.is_active = True
            self.metrics['start_time'] = time.time()
            self.log_event('marketplace_engine_started')
            logger.info("Marketplace Dynamics Engine started")
            return True
        except Exception as e:
            logger.error(f"Failed to start Marketplace Dynamics Engine: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the marketplace dynamics engine"""
        try:
            self.is_active = False
            self.log_event('marketplace_engine_stopped')
            logger.info("Marketplace Dynamics Engine stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop Marketplace Dynamics Engine: {e}")
            return False
    
    def process_event(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process marketplace events"""
        if not self.is_active:
            return {'error': 'Engine not active'}
        
        try:
            if event.event_type == 'submit_order':
                return self._process_order_submission(event)
            elif event.event_type == 'cancel_order':
                return self._process_order_cancellation(event)
            elif event.event_type == 'create_auction':
                return self._process_auction_creation(event)
            elif event.event_type == 'place_bid':
                return self._process_auction_bid(event)
            elif event.event_type == 'market_making':
                return self._process_market_making(event)
            elif event.event_type == 'price_update':
                return self._process_price_update(event)
            else:
                return {'error': f'Unknown event type: {event.event_type}'}
        except Exception as e:
            logger.error(f"Error processing marketplace event {event.event_type}: {e}")
            return {'error': str(e)}
    
    def create_market(self, service_type: str) -> bool:
        """Create a new market for a service type"""
        try:
            if service_type in self.markets:
                return True  # Market already exists
            
            self.markets[service_type] = ServiceMarket(service_type=service_type)
            self.order_books[service_type] = {'buy': [], 'sell': []}
            self.price_history[service_type] = []
            
            self.log_event('market_created', data={'service_type': service_type})
            logger.info(f"Created market for service type: {service_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create market for {service_type}: {e}")
            return False
    
    def submit_order(self, order: MarketOrder) -> Dict[str, Any]:
        """Submit an order to the marketplace"""
        try:
            # Validate order
            if not self._validate_order(order):
                raise MarketplaceError("Invalid order")
            
            # Ensure market exists
            if order.service_type not in self.markets:
                self.create_market(order.service_type)
            
            # Add to tracking
            self.all_orders[order.order_id] = order
            
            # Add to appropriate order book
            market = self.markets[order.service_type]
            if order.is_buy:
                market.buy_orders.append(order)
                # Keep buy orders sorted by price (highest first)
                market.buy_orders.sort(key=lambda x: x.price, reverse=True)
            else:
                market.sell_orders.append(order)
                # Keep sell orders sorted by price (lowest first)
                market.sell_orders.sort(key=lambda x: x.price)
            
            # Try to match orders immediately
            matches = self._match_orders(order.service_type)
            
            self.log_event('order_submitted', order.agent_id, {
                'order_id': order.order_id,
                'order_type': order.order_type.value,
                'service_type': order.service_type,
                'quantity': str(order.quantity),
                'price': str(order.price),
                'matches_found': len(matches)
            })
            
            return {
                'success': True,
                'order_id': order.order_id,
                'matches': matches,
                'order_status': order.status.value
            }
            
        except Exception as e:
            logger.error(f"Failed to submit order: {e}")
            return {'success': False, 'error': str(e)}
    
    def _validate_order(self, order: MarketOrder) -> bool:
        """Validate an order"""
        if order.quantity < self.min_order_size:
            return False
        
        if order.price <= 0:
            return False
        
        if order.is_buy and order.max_price and order.price > order.max_price:
            return False
        
        if order.is_sell and order.min_price and order.price < order.min_price:
            return False
        
        return True
    
    def _match_orders(self, service_type: str) -> List[MarketTrade]:
        """Match buy and sell orders for a service type"""
        market = self.markets[service_type]
        trades = []
        
        # Get active orders
        buy_orders = [o for o in market.buy_orders if o.status == OrderStatus.PENDING and o.remaining_quantity > 0]
        sell_orders = [o for o in market.sell_orders if o.status == OrderStatus.PENDING and o.remaining_quantity > 0]
        
        # Sort orders for matching
        buy_orders.sort(key=lambda x: (-x.price, x.timestamp))  # Highest price first, then earliest
        sell_orders.sort(key=lambda x: (x.price, x.timestamp))   # Lowest price first, then earliest
        
        i, j = 0, 0
        while i < len(buy_orders) and j < len(sell_orders):
            buy_order = buy_orders[i]
            sell_order = sell_orders[j]
            
            # Check if orders can be matched
            if buy_order.price >= sell_order.price:
                # Execute trade
                trade_quantity = min(buy_order.remaining_quantity, sell_order.remaining_quantity)
                
                # Price determination (using mid-point of bid-ask)
                trade_price = (buy_order.price + sell_order.price) / 2
                
                # Create trade
                trade = MarketTrade(
                    trade_id=f"trade_{len(self.all_trades) + 1}_{int(time.time())}",
                    buy_order_id=buy_order.order_id,
                    sell_order_id=sell_order.order_id,
                    buyer_id=buy_order.agent_id,
                    seller_id=sell_order.agent_id,
                    service_type=service_type,
                    quantity=trade_quantity,
                    price=trade_price
                )
                
                # Update orders
                buy_order.filled_quantity += trade_quantity
                sell_order.filled_quantity += trade_quantity
                
                # Update order status
                if buy_order.filled_quantity >= buy_order.quantity:
                    buy_order.status = OrderStatus.FILLED
                else:
                    buy_order.status = OrderStatus.PARTIALLY_FILLED
                
                if sell_order.filled_quantity >= sell_order.quantity:
                    sell_order.status = OrderStatus.FILLED
                else:
                    sell_order.status = OrderStatus.PARTIALLY_FILLED
                
                # Add to trades
                trades.append(trade)
                self.all_trades.append(trade)
                market.recent_trades.append(trade)
                
                # Update market data
                market.current_price = trade_price
                self._update_market_statistics(service_type, trade)
                
                self.log_event('trade_executed', data={
                    'trade_id': trade.trade_id,
                    'buyer_id': trade.buyer_id,
                    'seller_id': trade.seller_id,
                    'service_type': service_type,
                    'quantity': str(trade_quantity),
                    'price': str(trade_price)
                })
                
                # Move to next order if current one is filled
                if buy_order.status == OrderStatus.FILLED:
                    i += 1
                if sell_order.status == OrderStatus.FILLED:
                    j += 1
            else:
                # No more matches possible
                break
        
        return trades
    
    def _update_market_statistics(self, service_type: str, trade: MarketTrade):
        """Update market statistics after a trade"""
        market = self.markets[service_type]
        
        # Update price history
        current_time = time.time()
        self.price_history[service_type].append((current_time, trade.price))
        
        # Keep only recent price history (last 24 hours)
        cutoff_time = current_time - 86400
        self.price_history[service_type] = [
            (t, p) for t, p in self.price_history[service_type] if t > cutoff_time
        ]
        
        # Calculate 24h volume
        recent_trades = [t for t in market.recent_trades if current_time - t.timestamp < 86400]
        market.volume_24h = sum(t.quantity * t.price for t in recent_trades)
        
        # Calculate 24h price change
        if len(self.price_history[service_type]) >= 2:
            oldest_price = self.price_history[service_type][0][1]
            current_price = trade.price
            market.price_change_24h = ((current_price - oldest_price) / oldest_price) * 100
        
        # Keep only recent trades
        market.recent_trades = recent_trades[-1000:]  # Keep last 1000 trades
    
    def cancel_order(self, order_id: str, agent_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        try:
            if order_id not in self.all_orders:
                return {'success': False, 'error': 'Order not found'}
            
            order = self.all_orders[order_id]
            
            # Verify ownership
            if order.agent_id != agent_id:
                return {'success': False, 'error': 'Not authorized to cancel this order'}
            
            # Check if order can be cancelled
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                return {'success': False, 'error': f'Cannot cancel order with status {order.status.value}'}
            
            # Update order status
            order.status = OrderStatus.CANCELLED
            
            # Remove from order book
            market = self.markets[order.service_type]
            if order.is_buy:
                market.buy_orders = [o for o in market.buy_orders if o.order_id != order_id]
            else:
                market.sell_orders = [o for o in market.sell_orders if o.order_id != order_id]
            
            self.log_event('order_cancelled', agent_id, {
                'order_id': order_id,
                'service_type': order.service_type
            })
            
            return {'success': True, 'order_id': order_id}
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_auction(self, auction_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new auction"""
        try:
            auction_id = auction_config.get('auction_id', f"auction_{len(self.active_auctions) + 1}_{int(time.time())}")
            
            auction = {
                'auction_id': auction_id,
                'auctioneer_id': auction_config['auctioneer_id'],
                'service_type': auction_config['service_type'],
                'auction_type': AuctionType(auction_config.get('auction_type', 'english')),
                'item_description': auction_config['item_description'],
                'reserve_price': Decimal(str(auction_config.get('reserve_price', '0'))),
                'starting_price': Decimal(str(auction_config.get('starting_price', '1'))),
                'current_price': Decimal(str(auction_config.get('starting_price', '1'))),
                'increment': Decimal(str(auction_config.get('increment', '0.1'))),
                'duration': auction_config.get('duration', self.default_auction_duration),
                'start_time': time.time(),
                'end_time': time.time() + auction_config.get('duration', self.default_auction_duration),
                'bids': [],
                'highest_bidder': None,
                'status': 'active'
            }
            
            self.active_auctions[auction_id] = auction
            
            self.log_event('auction_created', auction_config['auctioneer_id'], {
                'auction_id': auction_id,
                'auction_type': auction['auction_type'].value,
                'service_type': auction_config['service_type'],
                'starting_price': str(auction['starting_price'])
            })
            
            return {
                'success': True,
                'auction_id': auction_id,
                'end_time': auction['end_time']
            }
            
        except Exception as e:
            logger.error(f"Failed to create auction: {e}")
            return {'success': False, 'error': str(e)}
    
    def place_bid(self, auction_id: str, bidder_id: str, bid_amount: Decimal) -> Dict[str, Any]:
        """Place a bid in an auction"""
        try:
            if auction_id not in self.active_auctions:
                return {'success': False, 'error': 'Auction not found'}
            
            auction = self.active_auctions[auction_id]
            
            # Check if auction is still active
            if auction['status'] != 'active' or time.time() > auction['end_time']:
                return {'success': False, 'error': 'Auction is not active'}
            
            # Validate bid based on auction type
            if auction['auction_type'] == AuctionType.ENGLISH:
                if bid_amount <= auction['current_price']:
                    return {'success': False, 'error': f'Bid must be higher than current price {auction["current_price"]}'}
            
            elif auction['auction_type'] == AuctionType.DUTCH:
                # In Dutch auction, price decreases over time
                time_elapsed = time.time() - auction['start_time']
                current_dutch_price = auction['starting_price'] - (auction['increment'] * Decimal(str(time_elapsed / 60)))  # Decrease every minute
                if bid_amount < current_dutch_price:
                    return {'success': False, 'error': f'Bid must be at least current price {current_dutch_price}'}
            
            # Create bid
            bid = {
                'bid_id': f"bid_{len(auction['bids']) + 1}_{int(time.time())}",
                'bidder_id': bidder_id,
                'amount': bid_amount,
                'timestamp': time.time()
            }
            
            auction['bids'].append(bid)
            
            # Update auction state
            if auction['auction_type'] in [AuctionType.ENGLISH, AuctionType.DUTCH]:
                auction['current_price'] = bid_amount
                auction['highest_bidder'] = bidder_id
            
            self.log_event('bid_placed', bidder_id, {
                'auction_id': auction_id,
                'bid_amount': str(bid_amount),
                'auction_type': auction['auction_type'].value
            })
            
            # Check if auction should end (Dutch auction)
            if auction['auction_type'] == AuctionType.DUTCH:
                result = self._finalize_auction(auction_id)
                return {
                    'success': True,
                    'bid_accepted': True,
                    'auction_ended': True,
                    'winner': bidder_id,
                    'final_price': str(bid_amount)
                }
            
            return {
                'success': True,
                'bid_accepted': True,
                'current_price': str(auction['current_price']),
                'highest_bidder': auction['highest_bidder']
            }
            
        except Exception as e:
            logger.error(f"Failed to place bid: {e}")
            return {'success': False, 'error': str(e)}
    
    def _finalize_auction(self, auction_id: str) -> Dict[str, Any]:
        """Finalize an auction and determine winner"""
        try:
            auction = self.active_auctions[auction_id]
            auction['status'] = 'completed'
            
            if auction['auction_type'] == AuctionType.VICKREY:
                # Second-price sealed-bid auction
                if len(auction['bids']) >= 2:
                    sorted_bids = sorted(auction['bids'], key=lambda x: x['amount'], reverse=True)
                    winner = sorted_bids[0]
                    second_price = sorted_bids[1]['amount']
                    final_price = second_price
                    winner_id = winner['bidder_id']
                elif len(auction['bids']) == 1:
                    winner = auction['bids'][0]
                    final_price = winner['amount']
                    winner_id = winner['bidder_id']
                else:
                    winner_id = None
                    final_price = Decimal('0')
            else:
                # Standard highest bid wins
                if auction['bids']:
                    winner = max(auction['bids'], key=lambda x: x['amount'])
                    winner_id = winner['bidder_id']
                    final_price = winner['amount']
                else:
                    winner_id = None
                    final_price = Decimal('0')
            
            result = {
                'auction_id': auction_id,
                'winner': winner_id,
                'final_price': str(final_price),
                'total_bids': len(auction['bids']),
                'auction_type': auction['auction_type'].value
            }
            
            auction['winner'] = winner_id
            auction['final_price'] = final_price
            
            self.log_event('auction_finalized', auction['auctioneer_id'], result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to finalize auction {auction_id}: {e}")
            return {'error': str(e)}
    
    def get_market_data(self, service_type: str) -> Optional[MarketData]:
        """Get current market data for a service type"""
        if service_type not in self.markets:
            return None
        
        market = self.markets[service_type]
        current_time = time.time()
        
        # Determine market state
        spread = market.get_spread()
        if spread is None:
            state = MarketState.STABLE
        elif spread > self.max_spread_threshold:
            state = MarketState.VOLATILE
        elif market.price_change_24h > 5:
            state = MarketState.OVER_SUPPLY
        elif market.price_change_24h < -5:
            state = MarketState.UNDER_SUPPLY
        else:
            state = MarketState.BALANCED
        
        # Calculate supply and demand indicators
        active_sell_orders = [o for o in market.sell_orders if o.status == OrderStatus.PENDING]
        active_buy_orders = [o for o in market.buy_orders if o.status == OrderStatus.PENDING]
        
        total_supply = sum(o.remaining_quantity for o in active_sell_orders)
        total_demand = sum(o.remaining_quantity for o in active_buy_orders)
        
        return MarketData(
            timestamp=current_time,
            token_type=TokenType.SERVICE,  # Default
            price=market.current_price,
            volume=market.volume_24h,
            market_cap=market.current_price * total_supply if total_supply > 0 else Decimal('0'),
            supply=total_supply,
            demand=total_demand,
            state=state
        )
    
    def get_order_book(self, service_type: str, depth: int = 10) -> Dict[str, Any]:
        """Get order book for a service type"""
        if service_type not in self.markets:
            return {}
        
        market = self.markets[service_type]
        
        # Get active orders
        active_buys = [o for o in market.buy_orders if o.status == OrderStatus.PENDING][:depth]
        active_sells = [o for o in market.sell_orders if o.status == OrderStatus.PENDING][:depth]
        
        return {
            'service_type': service_type,
            'timestamp': time.time(),
            'bids': [
                {
                    'price': str(o.price),
                    'quantity': str(o.remaining_quantity),
                    'agent_id': o.agent_id,
                    'order_id': o.order_id
                }
                for o in active_buys
            ],
            'asks': [
                {
                    'price': str(o.price),
                    'quantity': str(o.remaining_quantity),
                    'agent_id': o.agent_id,
                    'order_id': o.order_id
                }
                for o in active_sells
            ],
            'spread': str(market.get_spread()) if market.get_spread() else None,
            'best_bid': str(market.get_best_bid()) if market.get_best_bid() else None,
            'best_ask': str(market.get_best_ask()) if market.get_best_ask() else None
        }
    
    def _process_order_submission(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process order submission event"""
        data = event.data
        try:
            order = MarketOrder(
                order_id=data.get('order_id', f"order_{event.agent_id}_{int(time.time())}"),
                agent_id=event.agent_id,
                order_type=OrderType(data['order_type']),
                service_type=data['service_type'],
                quantity=Decimal(str(data['quantity'])),
                price=Decimal(str(data['price'])),
                max_price=Decimal(str(data['max_price'])) if data.get('max_price') else None,
                min_price=Decimal(str(data['min_price'])) if data.get('min_price') else None
            )
            
            return self.submit_order(order)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_order_cancellation(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process order cancellation event"""
        data = event.data
        try:
            return self.cancel_order(data['order_id'], event.agent_id)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_auction_creation(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process auction creation event"""
        data = event.data
        data['auctioneer_id'] = event.agent_id
        return self.create_auction(data)
    
    def _process_auction_bid(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process auction bid event"""
        data = event.data
        try:
            return self.place_bid(
                auction_id=data['auction_id'],
                bidder_id=event.agent_id,
                bid_amount=Decimal(str(data['bid_amount']))
            )
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_market_making(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process market making event"""
        # Market making implementation would go here
        return {'success': True, 'message': 'Market making not yet implemented'}
    
    def _process_price_update(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process price update event"""
        # Price oracle or external price update
        return {'success': True, 'message': 'Price update processed'}