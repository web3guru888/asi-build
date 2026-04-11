"""
Resource Allocation Engine
=========================

Advanced resource allocation algorithms for compute, memory, bandwidth,
and other computational resources in the AGI ecosystem.
"""

import heapq
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from decimal import Decimal, getcontext
from dataclasses import dataclass, field
from enum import Enum
import time
import logging

from ..core.base_engine import BaseEconomicEngine, EconomicEvent
from ..core.types import (
    ResourceType, Agent, Resource, ServiceRequest, AgentID,
    TokenType, TokenAmount
)
from ..core.exceptions import (
    ResourceUnavailableError, ResourceAllocationError, InsufficientFundsError
)

# Set decimal precision
getcontext().prec = 28

logger = logging.getLogger(__name__)

class AllocationStrategy(Enum):
    """Resource allocation strategies"""
    FIRST_FIT = "first_fit"
    BEST_FIT = "best_fit"
    WORST_FIT = "worst_fit"
    PROPORTIONAL_SHARE = "proportional_share"
    AUCTION_BASED = "auction_based"
    UTILITY_MAXIMIZATION = "utility_maximization"
    FAIR_SHARE = "fair_share"
    PRIORITY_BASED = "priority_based"

@dataclass
class ResourceAllocation:
    """Represents a resource allocation decision"""
    request_id: str
    requester_id: str
    provider_id: str
    resource_type: ResourceType
    allocated_amount: Decimal
    price_per_unit: Decimal
    total_cost: Decimal
    allocation_time: float
    expiry_time: float
    quality_score: float
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.expiry_time

@dataclass
class ResourceProvider:
    """Represents a resource provider"""
    provider_id: str
    resources: Dict[ResourceType, Resource]
    reputation_score: float
    reliability_score: float
    pricing_model: str = "fixed"
    is_active: bool = True
    
    def get_available_resource(self, resource_type: ResourceType) -> Optional[Resource]:
        """Get available resource if exists"""
        if resource_type in self.resources and self.is_active:
            resource = self.resources[resource_type]
            if resource.availability > 0:
                return resource
        return None
    
    def calculate_price(self, resource_type: ResourceType, amount: Decimal, 
                       demand_factor: float = 1.0) -> Decimal:
        """Calculate price based on demand and provider's model"""
        if resource_type not in self.resources:
            raise ResourceUnavailableError(f"Resource {resource_type.value} not available")
        
        base_cost = self.resources[resource_type].cost_per_unit * amount
        
        # Apply dynamic pricing based on demand
        dynamic_price = base_cost * Decimal(str(demand_factor))
        
        # Apply quality bonus
        quality_multiplier = Decimal(str(1 + (self.reputation_score - 0.5)))
        final_price = dynamic_price * quality_multiplier
        
        return final_price

class ResourceAllocator(BaseEconomicEngine):
    """
    Advanced resource allocation engine supporting multiple strategies
    and optimization algorithms for AGI computational resources.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # Resource providers and their resources
        self.providers: Dict[str, ResourceProvider] = {}
        
        # Active allocations
        self.active_allocations: Dict[str, ResourceAllocation] = {}
        
        # Pending requests queue
        self.pending_requests: List[ServiceRequest] = []
        
        # Resource utilization tracking
        self.utilization_history: Dict[ResourceType, List[Tuple[float, float]]] = {
            rt: [] for rt in ResourceType
        }
        
        # Allocation strategy
        self.allocation_strategy = AllocationStrategy(
            config.get('allocation_strategy', 'utility_maximization')
        )
        
        # Economic parameters
        self.demand_sensitivity = config.get('demand_sensitivity', 1.5)
        self.quality_weight = config.get('quality_weight', 0.3)
        self.price_weight = config.get('price_weight', 0.4)
        self.availability_weight = config.get('availability_weight', 0.3)
    
    def start(self) -> bool:
        """Start the resource allocator"""
        try:
            self.is_active = True
            self.metrics['start_time'] = time.time()
            self.log_event('resource_allocator_started')
            logger.info("Resource Allocator started")
            return True
        except Exception as e:
            logger.error(f"Failed to start Resource Allocator: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the resource allocator"""
        try:
            self.is_active = False
            self.log_event('resource_allocator_stopped')
            logger.info("Resource Allocator stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop Resource Allocator: {e}")
            return False
    
    def process_event(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process resource allocation events"""
        if not self.is_active:
            return {'error': 'Engine not active'}
        
        try:
            if event.event_type == 'request_resources':
                return self._process_resource_request(event)
            elif event.event_type == 'release_resources':
                return self._process_resource_release(event)
            elif event.event_type == 'add_provider':
                return self._process_add_provider(event)
            elif event.event_type == 'update_provider':
                return self._process_update_provider(event)
            elif event.event_type == 'optimize_allocations':
                return self._process_optimization(event)
            else:
                return {'error': f'Unknown event type: {event.event_type}'}
        except Exception as e:
            logger.error(f"Error processing resource allocation event {event.event_type}: {e}")
            return {'error': str(e)}
    
    def register_provider(self, provider: ResourceProvider) -> bool:
        """Register a new resource provider"""
        try:
            self.providers[provider.provider_id] = provider
            self.log_event('provider_registered', provider.provider_id, {
                'resources': [rt.value for rt in provider.resources.keys()],
                'reputation': provider.reputation_score
            })
            return True
        except Exception as e:
            logger.error(f"Failed to register provider {provider.provider_id}: {e}")
            return False
    
    def submit_resource_request(self, request: ServiceRequest) -> Dict[str, Any]:
        """Submit a resource request for allocation"""
        try:
            # Validate request
            if not self._validate_request(request):
                raise ResourceAllocationError("Invalid resource request")
            
            # Try immediate allocation
            allocation_result = self._allocate_resources(request)
            
            if allocation_result['success']:
                return allocation_result
            else:
                # Add to pending queue if immediate allocation fails
                self.pending_requests.append(request)
                return {
                    'success': False,
                    'message': 'Request queued for later allocation',
                    'request_id': request.request_id,
                    'queue_position': len(self.pending_requests)
                }
                
        except Exception as e:
            logger.error(f"Failed to submit resource request: {e}")
            return {'success': False, 'error': str(e)}
    
    def _validate_request(self, request: ServiceRequest) -> bool:
        """Validate a resource request"""
        if not request.resource_requirements:
            return False
        
        if request.max_budget <= 0:
            return False
        
        if request.deadline < time.time():
            return False
        
        return True
    
    def _allocate_resources(self, request: ServiceRequest) -> Dict[str, Any]:
        """Allocate resources based on the configured strategy"""
        if self.allocation_strategy == AllocationStrategy.UTILITY_MAXIMIZATION:
            return self._utility_maximizing_allocation(request)
        elif self.allocation_strategy == AllocationStrategy.AUCTION_BASED:
            return self._auction_based_allocation(request)
        elif self.allocation_strategy == AllocationStrategy.FIRST_FIT:
            return self._first_fit_allocation(request)
        elif self.allocation_strategy == AllocationStrategy.BEST_FIT:
            return self._best_fit_allocation(request)
        elif self.allocation_strategy == AllocationStrategy.PROPORTIONAL_SHARE:
            return self._proportional_share_allocation(request)
        else:
            return self._utility_maximizing_allocation(request)  # Default
    
    def _utility_maximizing_allocation(self, request: ServiceRequest) -> Dict[str, Any]:
        """
        Utility-maximizing allocation algorithm that considers price, quality, and availability
        """
        best_allocation = None
        best_utility = -float('inf')
        
        for resource_type, required_amount in request.resource_requirements.items():
            candidates = []
            
            # Find all providers with this resource type
            for provider_id, provider in self.providers.items():
                resource = provider.get_available_resource(resource_type)
                if resource and resource.amount >= required_amount:
                    
                    # Calculate demand factor
                    demand_factor = self._calculate_demand_factor(resource_type)
                    
                    # Calculate price
                    price = provider.calculate_price(resource_type, required_amount, demand_factor)
                    
                    if price <= request.max_budget:
                        # Calculate utility score
                        utility = self._calculate_utility_score(
                            provider, resource, price, request.max_budget,
                            required_amount, request.quality_requirements
                        )
                        
                        candidates.append({
                            'provider_id': provider_id,
                            'provider': provider,
                            'resource': resource,
                            'price': price,
                            'utility': utility,
                            'resource_type': resource_type,
                            'amount': required_amount
                        })
            
            # Select best candidate for this resource type
            if candidates:
                best_candidate = max(candidates, key=lambda x: x['utility'])
                
                if best_candidate['utility'] > best_utility:
                    best_allocation = best_candidate
                    best_utility = best_candidate['utility']
        
        if best_allocation:
            return self._execute_allocation(request, best_allocation)
        else:
            return {
                'success': False,
                'message': 'No suitable providers found',
                'request_id': request.request_id
            }
    
    def _calculate_utility_score(self, provider: ResourceProvider, resource: Resource,
                                price: Decimal, max_budget: Decimal, amount: Decimal,
                                quality_requirements: Dict[str, float]) -> float:
        """Calculate utility score for a resource allocation option"""
        
        # Price utility (higher is better, lower price)
        price_ratio = float(price / max_budget)
        price_utility = 1.0 - min(price_ratio, 1.0)
        
        # Quality utility
        quality_utility = (provider.reputation_score * resource.quality_score)
        
        # Availability utility
        availability_utility = resource.availability
        
        # Reliability utility
        reliability_utility = provider.reliability_score
        
        # Combined utility with weights
        total_utility = (
            self.price_weight * price_utility +
            self.quality_weight * quality_utility +
            self.availability_weight * availability_utility +
            0.2 * reliability_utility  # Fixed weight for reliability
        )
        
        # Apply quality requirements bonus/penalty
        quality_bonus = 1.0
        for req_name, req_value in quality_requirements.items():
            if req_name == 'min_quality' and resource.quality_score >= req_value:
                quality_bonus += 0.1
            elif req_name == 'min_availability' and resource.availability >= req_value:
                quality_bonus += 0.1
        
        return total_utility * quality_bonus
    
    def _calculate_demand_factor(self, resource_type: ResourceType) -> float:
        """Calculate demand factor for dynamic pricing"""
        # Simple demand calculation based on active allocations
        active_count = sum(1 for alloc in self.active_allocations.values() 
                          if alloc.resource_type == resource_type)
        
        total_providers = sum(1 for provider in self.providers.values()
                            if resource_type in provider.resources)
        
        if total_providers == 0:
            return 1.0
        
        # Demand factor increases with utilization
        utilization_ratio = active_count / max(total_providers, 1)
        demand_factor = 1.0 + (utilization_ratio * self.demand_sensitivity)
        
        return min(demand_factor, 5.0)  # Cap at 5x
    
    def _execute_allocation(self, request: ServiceRequest, allocation_candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a resource allocation"""
        try:
            provider = allocation_candidate['provider']
            resource = allocation_candidate['resource']
            price = allocation_candidate['price']
            resource_type = allocation_candidate['resource_type']
            amount = allocation_candidate['amount']
            
            # Create allocation record
            allocation = ResourceAllocation(
                request_id=request.request_id,
                requester_id=request.requester_id,
                provider_id=provider.provider_id,
                resource_type=resource_type,
                allocated_amount=amount,
                price_per_unit=price / amount,
                total_cost=price,
                allocation_time=time.time(),
                expiry_time=request.deadline,
                quality_score=resource.quality_score
            )
            
            # Update resource availability
            resource.amount -= amount
            if resource.amount < 0:
                resource.amount = Decimal('0')
            
            # Store allocation
            self.active_allocations[request.request_id] = allocation
            
            # Update utilization tracking
            self._update_utilization_tracking(resource_type)
            
            self.log_event('resource_allocated', request.requester_id, {
                'request_id': request.request_id,
                'provider_id': provider.provider_id,
                'resource_type': resource_type.value,
                'amount': str(amount),
                'cost': str(price)
            })
            
            return {
                'success': True,
                'allocation': allocation,
                'message': f'Resources allocated successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to execute allocation: {e}")
            return {'success': False, 'error': str(e)}
    
    def _update_utilization_tracking(self, resource_type: ResourceType):
        """Update resource utilization tracking"""
        current_time = time.time()
        active_allocations = sum(1 for alloc in self.active_allocations.values() 
                               if alloc.resource_type == resource_type and not alloc.is_expired)
        
        total_capacity = sum(resource.amount for provider in self.providers.values() 
                           for rt, resource in provider.resources.items() 
                           if rt == resource_type)
        
        utilization_rate = float(active_allocations) / max(float(total_capacity), 1.0)
        
        self.utilization_history[resource_type].append((current_time, utilization_rate))
        
        # Keep only recent history (last 24 hours)
        cutoff_time = current_time - 86400
        self.utilization_history[resource_type] = [
            (t, rate) for t, rate in self.utilization_history[resource_type] 
            if t > cutoff_time
        ]
    
    def release_allocation(self, request_id: str) -> bool:
        """Release a resource allocation"""
        try:
            if request_id not in self.active_allocations:
                return False
            
            allocation = self.active_allocations[request_id]
            
            # Return resources to provider
            provider = self.providers[allocation.provider_id]
            if allocation.resource_type in provider.resources:
                resource = provider.resources[allocation.resource_type]
                resource.amount += allocation.allocated_amount
            
            # Remove allocation
            del self.active_allocations[request_id]
            
            self.log_event('resource_released', allocation.requester_id, {
                'request_id': request_id,
                'provider_id': allocation.provider_id,
                'resource_type': allocation.resource_type.value,
                'amount': str(allocation.allocated_amount)
            })
            
            # Try to allocate pending requests
            self._process_pending_requests()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to release allocation {request_id}: {e}")
            return False
    
    def _process_pending_requests(self):
        """Process pending resource requests"""
        processed_requests = []
        
        for request in self.pending_requests[:]:
            result = self._allocate_resources(request)
            if result['success']:
                processed_requests.append(request)
                self.pending_requests.remove(request)
        
        if processed_requests:
            self.log_event('pending_requests_processed', data={
                'processed_count': len(processed_requests)
            })
    
    def _first_fit_allocation(self, request: ServiceRequest) -> Dict[str, Any]:
        """First-fit allocation algorithm"""
        for resource_type, required_amount in request.resource_requirements.items():
            for provider_id, provider in self.providers.items():
                resource = provider.get_available_resource(resource_type)
                if resource and resource.amount >= required_amount:
                    demand_factor = self._calculate_demand_factor(resource_type)
                    price = provider.calculate_price(resource_type, required_amount, demand_factor)
                    
                    if price <= request.max_budget:
                        candidate = {
                            'provider_id': provider_id,
                            'provider': provider,
                            'resource': resource,
                            'price': price,
                            'resource_type': resource_type,
                            'amount': required_amount
                        }
                        return self._execute_allocation(request, candidate)
        
        return {
            'success': False,
            'message': 'No available resources found',
            'request_id': request.request_id
        }
    
    def _best_fit_allocation(self, request: ServiceRequest) -> Dict[str, Any]:
        """Best-fit allocation algorithm (minimize waste)"""
        best_candidate = None
        min_waste = float('inf')
        
        for resource_type, required_amount in request.resource_requirements.items():
            for provider_id, provider in self.providers.items():
                resource = provider.get_available_resource(resource_type)
                if resource and resource.amount >= required_amount:
                    demand_factor = self._calculate_demand_factor(resource_type)
                    price = provider.calculate_price(resource_type, required_amount, demand_factor)
                    
                    if price <= request.max_budget:
                        waste = float(resource.amount - required_amount)
                        if waste < min_waste:
                            min_waste = waste
                            best_candidate = {
                                'provider_id': provider_id,
                                'provider': provider,
                                'resource': resource,
                                'price': price,
                                'resource_type': resource_type,
                                'amount': required_amount
                            }
        
        if best_candidate:
            return self._execute_allocation(request, best_candidate)
        else:
            return {
                'success': False,
                'message': 'No suitable resources found',
                'request_id': request.request_id
            }
    
    def _auction_based_allocation(self, request: ServiceRequest) -> Dict[str, Any]:
        """Auction-based allocation using sealed-bid auction"""
        # This is a simplified version - real implementation would be more complex
        bids = []
        
        for resource_type, required_amount in request.resource_requirements.items():
            for provider_id, provider in self.providers.items():
                resource = provider.get_available_resource(resource_type)
                if resource and resource.amount >= required_amount:
                    demand_factor = self._calculate_demand_factor(resource_type)
                    bid_price = provider.calculate_price(resource_type, required_amount, demand_factor)
                    
                    if bid_price <= request.max_budget:
                        utility = self._calculate_utility_score(
                            provider, resource, bid_price, request.max_budget,
                            required_amount, request.quality_requirements
                        )
                        
                        bids.append({
                            'provider_id': provider_id,
                            'provider': provider,
                            'resource': resource,
                            'price': bid_price,
                            'utility': utility,
                            'resource_type': resource_type,
                            'amount': required_amount
                        })
        
        if bids:
            # Select winner (highest utility, lowest price in case of tie)
            winner = max(bids, key=lambda x: (x['utility'], -float(x['price'])))
            return self._execute_allocation(request, winner)
        else:
            return {
                'success': False,
                'message': 'No bids received',
                'request_id': request.request_id
            }
    
    def _proportional_share_allocation(self, request: ServiceRequest) -> Dict[str, Any]:
        """Proportional share allocation based on resource contributions"""
        # Simplified implementation
        return self._utility_maximizing_allocation(request)
    
    def get_allocation_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a resource allocation"""
        if request_id in self.active_allocations:
            allocation = self.active_allocations[request_id]
            return {
                'request_id': request_id,
                'status': 'active' if not allocation.is_expired else 'expired',
                'provider_id': allocation.provider_id,
                'resource_type': allocation.resource_type.value,
                'allocated_amount': str(allocation.allocated_amount),
                'total_cost': str(allocation.total_cost),
                'quality_score': allocation.quality_score,
                'expiry_time': allocation.expiry_time
            }
        return None
    
    def get_utilization_metrics(self) -> Dict[str, Any]:
        """Get resource utilization metrics"""
        metrics = {}
        
        for resource_type in ResourceType:
            if self.utilization_history[resource_type]:
                recent_rates = [rate for _, rate in self.utilization_history[resource_type][-100:]]
                avg_utilization = sum(recent_rates) / len(recent_rates) if recent_rates else 0
                max_utilization = max(recent_rates) if recent_rates else 0
                min_utilization = min(recent_rates) if recent_rates else 0
                
                metrics[resource_type.value] = {
                    'average_utilization': avg_utilization,
                    'max_utilization': max_utilization,
                    'min_utilization': min_utilization,
                    'current_allocations': len([a for a in self.active_allocations.values() 
                                              if a.resource_type == resource_type])
                }
        
        return metrics
    
    def optimize_allocations(self) -> Dict[str, Any]:
        """Optimize current resource allocations"""
        try:
            optimizations = []
            
            # Clean up expired allocations
            expired_allocations = [rid for rid, alloc in self.active_allocations.items() 
                                 if alloc.is_expired]
            
            for request_id in expired_allocations:
                self.release_allocation(request_id)
                optimizations.append(f"Released expired allocation {request_id}")
            
            # Process pending requests
            initial_pending = len(self.pending_requests)
            self._process_pending_requests()
            processed = initial_pending - len(self.pending_requests)
            
            if processed > 0:
                optimizations.append(f"Processed {processed} pending requests")
            
            return {
                'success': True,
                'optimizations': optimizations,
                'active_allocations': len(self.active_allocations),
                'pending_requests': len(self.pending_requests)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_resource_request(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process resource request event"""
        data = event.data
        try:
            request = ServiceRequest(
                request_id=data.get('request_id'),
                requester_id=event.agent_id,
                service_type=data['service_type'],
                resource_requirements={
                    ResourceType(rt): Decimal(str(amount)) 
                    for rt, amount in data['resource_requirements'].items()
                },
                max_budget=Decimal(str(data['max_budget'])),
                deadline=data['deadline'],
                quality_requirements=data.get('quality_requirements', {})
            )
            
            return self.submit_resource_request(request)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_resource_release(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process resource release event"""
        data = event.data
        try:
            success = self.release_allocation(data['request_id'])
            return {'success': success}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_add_provider(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process add provider event"""
        data = event.data
        try:
            resources = {}
            for rt_str, resource_data in data['resources'].items():
                rt = ResourceType(rt_str)
                resources[rt] = Resource(
                    resource_type=rt,
                    amount=Decimal(str(resource_data['amount'])),
                    cost_per_unit=Decimal(str(resource_data['cost_per_unit'])),
                    provider_id=data['provider_id'],
                    quality_score=resource_data.get('quality_score', 1.0),
                    availability=resource_data.get('availability', 1.0)
                )
            
            provider = ResourceProvider(
                provider_id=data['provider_id'],
                resources=resources,
                reputation_score=data.get('reputation_score', 0.5),
                reliability_score=data.get('reliability_score', 0.5),
                pricing_model=data.get('pricing_model', 'fixed')
            )
            
            success = self.register_provider(provider)
            return {'success': success}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_update_provider(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process provider update event"""
        # Implementation for updating provider information
        return {'success': True, 'message': 'Provider update not yet implemented'}
    
    def _process_optimization(self, event: EconomicEvent) -> Dict[str, Any]:
        """Process optimization event"""
        return self.optimize_allocations()