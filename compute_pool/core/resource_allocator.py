"""
Resource Allocator - Manages dynamic resource allocation across multiple providers
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid


class ResourceType(Enum):
    GPU = "gpu"
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"


class AllocationStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    RELEASED = "released"
    FAILED = "failed"


@dataclass
class ResourceRequest:
    """Resource request specification"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    gpu_count: int = 0
    gpu_memory: int = 0  # GB
    cpu_cores: int = 0
    memory: int = 0  # GB
    storage: int = 0  # GB
    network_bandwidth: int = 0  # Mbps
    duration: Optional[float] = None  # seconds
    priority: int = 5  # 1-10 scale
    user_id: Optional[str] = None
    job_id: Optional[str] = None
    requirements: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "gpu_count": self.gpu_count,
            "gpu_memory": self.gpu_memory,
            "cpu_cores": self.cpu_cores,
            "memory": self.memory,
            "storage": self.storage,
            "network_bandwidth": self.network_bandwidth,
            "duration": self.duration,
            "priority": self.priority,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "requirements": self.requirements
        }


@dataclass
class ResourceAllocation:
    """Resource allocation response"""
    allocation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    resources: Dict[str, Any] = field(default_factory=dict)
    provider: str = ""
    status: AllocationStatus = AllocationStatus.PENDING
    allocated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    cost_estimate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allocation_id": self.allocation_id,
            "request_id": self.request_id,
            "resources": self.resources,
            "provider": self.provider,
            "status": self.status.value,
            "allocated_at": self.allocated_at,
            "expires_at": self.expires_at,
            "cost_estimate": self.cost_estimate
        }


class ResourceProvider:
    """Abstract base class for resource providers"""
    
    def __init__(self, provider_id: str, provider_type: str):
        self.provider_id = provider_id
        self.provider_type = provider_type
        self.available_resources: Dict[str, int] = {}
        self.allocated_resources: Dict[str, int] = {}
        self.utilization: Dict[str, float] = {}
        self.enabled = True
        
    async def get_available_resources(self) -> Dict[str, int]:
        """Get currently available resources"""
        raise NotImplementedError
        
    async def allocate_resources(self, request: ResourceRequest) -> Optional[ResourceAllocation]:
        """Allocate resources for a request"""
        raise NotImplementedError
        
    async def deallocate_resources(self, allocation: ResourceAllocation) -> bool:
        """Deallocate previously allocated resources"""
        raise NotImplementedError
        
    async def get_utilization(self) -> Dict[str, float]:
        """Get current resource utilization"""
        raise NotImplementedError
        
    async def health_check(self) -> bool:
        """Check if provider is healthy"""
        return self.enabled


class LocalProvider(ResourceProvider):
    """Local machine resource provider"""
    
    def __init__(self, provider_id: str = "local"):
        super().__init__(provider_id, "local")
        self.logger = logging.getLogger(f"provider.{provider_id}")
        
        # Initialize with default local resources (can be configured)
        self.total_resources = {
            "gpu_count": 8,
            "gpu_memory": 64,
            "cpu_cores": 32,
            "memory": 128,
            "storage": 1000,
            "network_bandwidth": 10000
        }
        
        self.available_resources = self.total_resources.copy()
        self.allocated_resources = {k: 0 for k in self.total_resources.keys()}
        
    async def get_available_resources(self) -> Dict[str, int]:
        return self.available_resources.copy()
        
    async def allocate_resources(self, request: ResourceRequest) -> Optional[ResourceAllocation]:
        """Allocate local resources"""
        required = {
            "gpu_count": request.gpu_count,
            "gpu_memory": request.gpu_memory,
            "cpu_cores": request.cpu_cores,
            "memory": request.memory,
            "storage": request.storage,
            "network_bandwidth": request.network_bandwidth
        }
        
        # Check availability
        for resource, amount in required.items():
            if amount > 0 and self.available_resources.get(resource, 0) < amount:
                self.logger.warning(f"Insufficient {resource}: requested {amount}, available {self.available_resources.get(resource, 0)}")
                return None
        
        # Allocate resources
        allocation = ResourceAllocation(
            request_id=request.request_id,
            provider=self.provider_id,
            resources=required.copy(),
            status=AllocationStatus.ACTIVE
        )
        
        for resource, amount in required.items():
            if amount > 0:
                self.available_resources[resource] -= amount
                self.allocated_resources[resource] += amount
        
        if request.duration:
            allocation.expires_at = time.time() + request.duration
        
        self.logger.info(f"Allocated resources: {required}")
        return allocation
        
    async def deallocate_resources(self, allocation: ResourceAllocation) -> bool:
        """Deallocate local resources"""
        try:
            for resource, amount in allocation.resources.items():
                if amount > 0:
                    self.available_resources[resource] += amount
                    self.allocated_resources[resource] = max(0, self.allocated_resources[resource] - amount)
            
            allocation.status = AllocationStatus.RELEASED
            self.logger.info(f"Deallocated resources: {allocation.resources}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deallocate resources: {e}")
            return False
            
    async def get_utilization(self) -> Dict[str, float]:
        """Get current utilization percentages"""
        utilization = {}
        for resource, total in self.total_resources.items():
            if total > 0:
                used = self.allocated_resources.get(resource, 0)
                utilization[f"local_{resource}"] = (used / total) * 100
            else:
                utilization[f"local_{resource}"] = 0.0
        
        return utilization


class ResourceAllocator:
    """
    Main resource allocator that manages multiple providers
    and implements intelligent allocation strategies
    """
    
    def __init__(self):
        self.logger = logging.getLogger("resource_allocator")
        self.providers: Dict[str, ResourceProvider] = {}
        self.allocations: Dict[str, ResourceAllocation] = {}
        self.allocation_history: List[ResourceAllocation] = []
        
        # Allocation strategies
        self.allocation_strategies = {
            "best_fit": self._best_fit_allocation,
            "first_fit": self._first_fit_allocation,
            "balanced": self._balanced_allocation,
            "cost_optimized": self._cost_optimized_allocation
        }
        
        self.default_strategy = "balanced"
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "successful_allocations": 0,
            "failed_allocations": 0,
            "total_allocated_resources": 0,
            "average_allocation_time": 0.0
        }
        
    async def initialize(self) -> None:
        """Initialize the resource allocator"""
        self.logger.info("Initializing resource allocator")
        
        # Add default local provider
        local_provider = LocalProvider()
        await self.add_provider(local_provider)
        
    async def add_provider(self, provider: ResourceProvider) -> None:
        """Add a new resource provider"""
        self.providers[provider.provider_id] = provider
        self.logger.info(f"Added provider: {provider.provider_id} ({provider.provider_type})")
        
    async def remove_provider(self, provider_id: str) -> bool:
        """Remove a resource provider"""
        if provider_id in self.providers:
            # TODO: Handle graceful migration of allocations
            del self.providers[provider_id]
            self.logger.info(f"Removed provider: {provider_id}")
            return True
        return False
        
    async def allocate_resources(
        self, 
        request: ResourceRequest, 
        strategy: Optional[str] = None
    ) -> Optional[ResourceAllocation]:
        """
        Allocate resources using the specified strategy
        """
        start_time = time.time()
        self._stats["total_requests"] += 1
        
        strategy = strategy or self.default_strategy
        allocation_func = self.allocation_strategies.get(strategy, self._balanced_allocation)
        
        try:
            allocation = await allocation_func(request)
            
            if allocation:
                self.allocations[allocation.allocation_id] = allocation
                self.allocation_history.append(allocation)
                self._stats["successful_allocations"] += 1
                
                self.logger.info(
                    f"Successfully allocated resources for request {request.request_id} "
                    f"using {strategy} strategy"
                )
            else:
                self._stats["failed_allocations"] += 1
                self.logger.warning(f"Failed to allocate resources for request {request.request_id}")
            
            # Update timing statistics
            allocation_time = time.time() - start_time
            self._stats["average_allocation_time"] = (
                (self._stats["average_allocation_time"] * (self._stats["total_requests"] - 1) + allocation_time) 
                / self._stats["total_requests"]
            )
            
            return allocation
            
        except Exception as e:
            self.logger.error(f"Error during resource allocation: {e}")
            self._stats["failed_allocations"] += 1
            return None
            
    async def deallocate_resources(self, resources: Dict[str, Any]) -> bool:
        """Deallocate resources by allocation ID or resource dict"""
        if isinstance(resources, str):
            # Allocation ID
            allocation_id = resources
            if allocation_id not in self.allocations:
                return False
            allocation = self.allocations[allocation_id]
        else:
            # Find allocation by resource dict
            allocation = None
            for alloc in self.allocations.values():
                if alloc.resources == resources:
                    allocation = alloc
                    break
            
            if not allocation:
                self.logger.warning("Could not find allocation to deallocate")
                return False
        
        # Deallocate from provider
        provider = self.providers.get(allocation.provider)
        if provider:
            success = await provider.deallocate_resources(allocation)
            if success and allocation.allocation_id in self.allocations:
                del self.allocations[allocation.allocation_id]
            return success
        
        return False
        
    async def _best_fit_allocation(self, request: ResourceRequest) -> Optional[ResourceAllocation]:
        """
        Best fit allocation - choose provider with least waste
        """
        best_provider = None
        best_score = float('inf')
        
        for provider in self.providers.values():
            if not provider.enabled:
                continue
                
            available = await provider.get_available_resources()
            
            # Calculate waste score
            waste_score = 0
            can_satisfy = True
            
            required_resources = {
                "gpu_count": request.gpu_count,
                "gpu_memory": request.gpu_memory,
                "cpu_cores": request.cpu_cores,
                "memory": request.memory,
                "storage": request.storage,
                "network_bandwidth": request.network_bandwidth
            }
            
            for resource, required in required_resources.items():
                if required > 0:
                    available_amount = available.get(resource, 0)
                    if available_amount < required:
                        can_satisfy = False
                        break
                    waste_score += available_amount - required
            
            if can_satisfy and waste_score < best_score:
                best_score = waste_score
                best_provider = provider
        
        if best_provider:
            return await best_provider.allocate_resources(request)
        
        return None
        
    async def _first_fit_allocation(self, request: ResourceRequest) -> Optional[ResourceAllocation]:
        """
        First fit allocation - use first provider that can satisfy request
        """
        for provider in self.providers.values():
            if not provider.enabled:
                continue
                
            allocation = await provider.allocate_resources(request)
            if allocation:
                return allocation
        
        return None
        
    async def _balanced_allocation(self, request: ResourceRequest) -> Optional[ResourceAllocation]:
        """
        Balanced allocation - distribute load evenly across providers
        """
        provider_scores = []
        
        for provider in self.providers.values():
            if not provider.enabled:
                continue
                
            utilization = await provider.get_utilization()
            avg_utilization = sum(utilization.values()) / len(utilization) if utilization else 0
            
            # Prefer providers with lower utilization
            score = 100 - avg_utilization
            provider_scores.append((score, provider))
        
        # Sort by score (highest first)
        provider_scores.sort(reverse=True)
        
        for score, provider in provider_scores:
            allocation = await provider.allocate_resources(request)
            if allocation:
                return allocation
        
        return None
        
    async def _cost_optimized_allocation(self, request: ResourceRequest) -> Optional[ResourceAllocation]:
        """
        Cost optimized allocation - choose cheapest provider
        """
        # This would integrate with cost models for different providers
        # For now, prefer local resources (assumed cheaper)
        
        local_providers = [p for p in self.providers.values() if p.provider_type == "local"]
        cloud_providers = [p for p in self.providers.values() if p.provider_type != "local"]
        
        # Try local first
        for provider in local_providers:
            if provider.enabled:
                allocation = await provider.allocate_resources(request)
                if allocation:
                    return allocation
        
        # Then try cloud providers
        for provider in cloud_providers:
            if provider.enabled:
                allocation = await provider.allocate_resources(request)
                if allocation:
                    return allocation
        
        return None
        
    async def get_resource_availability(self) -> Dict[str, Dict[str, int]]:
        """Get available resources from all providers"""
        availability = {}
        
        for provider_id, provider in self.providers.items():
            if provider.enabled:
                availability[provider_id] = await provider.get_available_resources()
        
        return availability
        
    async def get_total_utilization(self) -> Dict[str, float]:
        """Get total utilization across all providers"""
        total_utilization = {}
        
        for provider in self.providers.values():
            if provider.enabled:
                utilization = await provider.get_utilization()
                total_utilization.update(utilization)
        
        return total_utilization
        
    async def get_statistics(self) -> Dict[str, Any]:
        """Get allocator statistics"""
        return {
            **self._stats,
            "active_allocations": len(self.allocations),
            "providers_count": len(self.providers),
            "enabled_providers": len([p for p in self.providers.values() if p.enabled])
        }
        
    async def cleanup_expired_allocations(self) -> int:
        """Clean up expired allocations"""
        current_time = time.time()
        expired_count = 0
        
        expired_allocations = []
        for allocation_id, allocation in self.allocations.items():
            if allocation.expires_at and allocation.expires_at <= current_time:
                expired_allocations.append(allocation_id)
        
        for allocation_id in expired_allocations:
            allocation = self.allocations[allocation_id]
            success = await self.deallocate_resources(allocation_id)
            if success:
                expired_count += 1
                self.logger.info(f"Cleaned up expired allocation: {allocation_id}")
        
        return expired_count