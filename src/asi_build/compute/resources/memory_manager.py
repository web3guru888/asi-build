"""
Memory Pool Manager - Manages memory resources with advanced allocation strategies
"""

import asyncio
import logging
import mmap
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import psutil


class MemoryType(Enum):
    SYSTEM_RAM = "system_ram"
    HUGE_PAGES = "huge_pages"
    SHARED_MEMORY = "shared_memory"
    GPU_MEMORY = "gpu_memory"  # For unified memory systems
    PERSISTENT_MEMORY = "persistent_memory"  # Intel Optane, etc.


class MemoryState(Enum):
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    RESERVED = "reserved"
    SWAPPING = "swapping"
    ERROR = "error"


@dataclass
class MemorySegment:
    """Memory segment information"""

    segment_id: str
    memory_type: MemoryType
    size_bytes: int
    physical_address: Optional[int] = None
    virtual_address: Optional[int] = None
    numa_node: int = 0
    page_size: int = 4096  # Default page size in bytes
    huge_pages: bool = False
    state: MemoryState = MemoryState.AVAILABLE
    allocated_at: Optional[float] = None
    access_pattern: str = "random"  # random, sequential, mixed

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024 * 1024 * 1024)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "memory_type": self.memory_type.value,
            "size_bytes": self.size_bytes,
            "size_mb": self.size_mb,
            "size_gb": self.size_gb,
            "physical_address": self.physical_address,
            "virtual_address": self.virtual_address,
            "numa_node": self.numa_node,
            "page_size": self.page_size,
            "huge_pages": self.huge_pages,
            "state": self.state.value,
            "allocated_at": self.allocated_at,
            "access_pattern": self.access_pattern,
        }


@dataclass
class SwapSpace:
    """Swap space information"""

    device: str
    size_bytes: int
    used_bytes: int = 0
    priority: int = 0
    encrypted: bool = False

    @property
    def free_bytes(self) -> int:
        return self.size_bytes - self.used_bytes

    @property
    def utilization_percent(self) -> float:
        return (self.used_bytes / self.size_bytes * 100) if self.size_bytes > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device": self.device,
            "size_bytes": self.size_bytes,
            "used_bytes": self.used_bytes,
            "free_bytes": self.free_bytes,
            "utilization_percent": self.utilization_percent,
            "priority": self.priority,
            "encrypted": self.encrypted,
        }


@dataclass
class MemoryAllocation:
    """Memory allocation tracking"""

    allocation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""
    user_id: str = ""
    memory_type: MemoryType = MemoryType.SYSTEM_RAM
    size_bytes: int = 0
    numa_nodes: List[int] = field(default_factory=list)
    segments: List[str] = field(default_factory=list)  # segment_ids
    huge_pages_enabled: bool = False
    memory_policy: str = "default"  # default, bind, interleave, preferred
    swap_enabled: bool = True
    allocated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    max_resident_set: int = 0  # Maximum RSS observed
    peak_usage: int = 0

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024 * 1024 * 1024)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allocation_id": self.allocation_id,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "memory_type": self.memory_type.value,
            "size_bytes": self.size_bytes,
            "size_mb": self.size_mb,
            "size_gb": self.size_gb,
            "numa_nodes": self.numa_nodes,
            "segments": self.segments,
            "huge_pages_enabled": self.huge_pages_enabled,
            "memory_policy": self.memory_policy,
            "swap_enabled": self.swap_enabled,
            "allocated_at": self.allocated_at,
            "expires_at": self.expires_at,
            "max_resident_set": self.max_resident_set,
            "peak_usage": self.peak_usage,
        }


class MemoryPoolManager:
    """
    Comprehensive memory pool manager with NUMA awareness,
    huge pages support, and intelligent swap management
    """

    def __init__(self):
        self.logger = logging.getLogger("memory_pool_manager")

        # Memory segments and NUMA topology
        self.segments: Dict[str, MemorySegment] = {}
        self.numa_nodes: Dict[int, List[str]] = {}  # numa_node -> segment_ids
        self.allocations: Dict[str, MemoryAllocation] = {}

        # Swap management
        self.swap_spaces: Dict[str, SwapSpace] = {}
        self.swap_enabled = True

        # Huge pages support
        self.huge_page_sizes = [2048, 1048576]  # 2MB and 1GB in KB
        self.huge_pages_available: Dict[int, int] = {}  # page_size -> count

        # Memory monitoring
        self.monitoring_interval = 5.0  # 5 seconds
        self.monitoring_task: Optional[asyncio.Task] = None

        # Memory policies
        self.default_memory_policy = "default"
        self.numa_balancing_enabled = True

        # Statistics
        self._stats = {
            "total_memory_bytes": 0,
            "available_memory_bytes": 0,
            "allocated_memory_bytes": 0,
            "cached_memory_bytes": 0,
            "swap_total_bytes": 0,
            "swap_used_bytes": 0,
            "numa_nodes": 0,
            "huge_pages_2mb_total": 0,
            "huge_pages_2mb_available": 0,
            "huge_pages_1gb_total": 0,
            "huge_pages_1gb_available": 0,
            "total_allocations": 0,
            "active_allocations": 0,
            "memory_pressure": 0.0,
            "swap_pressure": 0.0,
        }

    async def initialize(self) -> None:
        """Initialize the memory pool manager"""
        self.logger.info("Initializing memory pool manager")

        # Discover system memory
        await self._discover_system_memory()

        # Discover NUMA topology
        await self._discover_numa_memory_topology()

        # Initialize huge pages
        await self._initialize_huge_pages()

        # Discover swap spaces
        await self._discover_swap_spaces()

        # Start memory monitoring
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        total_gb = self._stats["total_memory_bytes"] / (1024**3)
        self.logger.info(
            f"Memory pool initialized with {total_gb:.1f} GB across {self._stats['numa_nodes']} NUMA nodes"
        )

    async def _discover_system_memory(self) -> None:
        """Discover system memory information"""
        try:
            # Get basic memory info using psutil
            memory = psutil.virtual_memory()

            self._stats["total_memory_bytes"] = memory.total
            self._stats["available_memory_bytes"] = memory.available
            self._stats["cached_memory_bytes"] = getattr(memory, "cached", 0)

            # Create a default memory segment for system RAM
            segment = MemorySegment(
                segment_id="system_ram_0",
                memory_type=MemoryType.SYSTEM_RAM,
                size_bytes=memory.total,
                numa_node=0,
            )

            self.segments[segment.segment_id] = segment

            # Initialize NUMA node 0 with default segment
            if 0 not in self.numa_nodes:
                self.numa_nodes[0] = []
            self.numa_nodes[0].append(segment.segment_id)

            self.logger.info(f"Discovered {memory.total / (1024**3):.1f} GB system memory")

        except Exception as e:
            self.logger.error(f"Error discovering system memory: {e}")

    async def _discover_numa_memory_topology(self) -> None:
        """Discover NUMA memory topology"""
        try:
            # Try to get NUMA memory info from /sys/devices/system/node/
            numa_path = "/sys/devices/system/node/"

            if os.path.exists(numa_path):
                node_dirs = [
                    d for d in os.listdir(numa_path) if d.startswith("node") and d[4:].isdigit()
                ]

                if len(node_dirs) > 1:  # More than one NUMA node
                    # Clear default segment and rebuild with NUMA awareness
                    self.segments.clear()
                    self.numa_nodes.clear()

                    for node_dir in node_dirs:
                        node_id = int(node_dir[4:])

                        # Read memory info for this node
                        meminfo_path = f"{numa_path}/{node_dir}/meminfo"
                        if os.path.exists(meminfo_path):
                            node_memory = await self._parse_numa_meminfo(meminfo_path)

                            if node_memory > 0:
                                segment = MemorySegment(
                                    segment_id=f"numa_ram_{node_id}",
                                    memory_type=MemoryType.SYSTEM_RAM,
                                    size_bytes=node_memory,
                                    numa_node=node_id,
                                )

                                self.segments[segment.segment_id] = segment

                                if node_id not in self.numa_nodes:
                                    self.numa_nodes[node_id] = []
                                self.numa_nodes[node_id].append(segment.segment_id)

                    self.logger.info(f"Discovered NUMA topology with {len(node_dirs)} nodes")

            self._stats["numa_nodes"] = len(self.numa_nodes)

        except Exception as e:
            self.logger.error(f"Error discovering NUMA memory topology: {e}")

    async def _parse_numa_meminfo(self, meminfo_path: str) -> int:
        """Parse NUMA node meminfo file"""
        try:
            with open(meminfo_path, "r") as f:
                for line in f:
                    if "MemTotal:" in line:
                        # Extract memory size in kB and convert to bytes
                        parts = line.split()
                        if len(parts) >= 3:
                            memory_kb = int(parts[3])
                            return memory_kb * 1024

        except Exception as e:
            self.logger.error(f"Error parsing NUMA meminfo {meminfo_path}: {e}")

        return 0

    async def _initialize_huge_pages(self) -> None:
        """Initialize huge pages support"""
        try:
            # Check for 2MB huge pages
            hugepages_2mb_path = "/sys/kernel/mm/hugepages/hugepages-2048kB/"
            if os.path.exists(hugepages_2mb_path):
                nr_hugepages_path = f"{hugepages_2mb_path}/nr_hugepages"
                free_hugepages_path = f"{hugepages_2mb_path}/free_hugepages"

                if os.path.exists(nr_hugepages_path) and os.path.exists(free_hugepages_path):
                    with open(nr_hugepages_path, "r") as f:
                        total_2mb = int(f.read().strip())
                    with open(free_hugepages_path, "r") as f:
                        free_2mb = int(f.read().strip())

                    self._stats["huge_pages_2mb_total"] = total_2mb
                    self._stats["huge_pages_2mb_available"] = free_2mb
                    self.huge_pages_available[2048] = free_2mb

            # Check for 1GB huge pages
            hugepages_1gb_path = "/sys/kernel/mm/hugepages/hugepages-1048576kB/"
            if os.path.exists(hugepages_1gb_path):
                nr_hugepages_path = f"{hugepages_1gb_path}/nr_hugepages"
                free_hugepages_path = f"{hugepages_1gb_path}/free_hugepages"

                if os.path.exists(nr_hugepages_path) and os.path.exists(free_hugepages_path):
                    with open(nr_hugepages_path, "r") as f:
                        total_1gb = int(f.read().strip())
                    with open(free_hugepages_path, "r") as f:
                        free_1gb = int(f.read().strip())

                    self._stats["huge_pages_1gb_total"] = total_1gb
                    self._stats["huge_pages_1gb_available"] = free_1gb
                    self.huge_pages_available[1048576] = free_1gb

            total_huge_pages = sum(self.huge_pages_available.values())
            if total_huge_pages > 0:
                self.logger.info(f"Huge pages available: {self.huge_pages_available}")

        except Exception as e:
            self.logger.error(f"Error initializing huge pages: {e}")

    async def _discover_swap_spaces(self) -> None:
        """Discover available swap spaces"""
        try:
            # Use psutil to get swap info
            swap = psutil.swap_memory()

            self._stats["swap_total_bytes"] = swap.total
            self._stats["swap_used_bytes"] = swap.used

            if swap.total > 0:
                # Try to get detailed swap info from /proc/swaps
                if os.path.exists("/proc/swaps"):
                    with open("/proc/swaps", "r") as f:
                        lines = f.readlines()[1:]  # Skip header

                        for line in lines:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                device = parts[0]
                                size_kb = int(parts[2])
                                used_kb = int(parts[3])
                                priority = int(parts[4])

                                swap_space = SwapSpace(
                                    device=device,
                                    size_bytes=size_kb * 1024,
                                    used_bytes=used_kb * 1024,
                                    priority=priority,
                                )

                                self.swap_spaces[device] = swap_space
                else:
                    # Create default swap entry
                    self.swap_spaces["default"] = SwapSpace(
                        device="default", size_bytes=swap.total, used_bytes=swap.used
                    )

                self.logger.info(
                    f"Discovered {len(self.swap_spaces)} swap spaces totaling {swap.total / (1024**3):.1f} GB"
                )

        except Exception as e:
            self.logger.error(f"Error discovering swap spaces: {e}")

    async def allocate_memory(
        self,
        job_id: str,
        user_id: str,
        size_bytes: int,
        memory_type: MemoryType = MemoryType.SYSTEM_RAM,
        numa_nodes: Optional[List[int]] = None,
        huge_pages: bool = False,
        memory_policy: str = "default",
        swap_enabled: bool = True,
        duration: Optional[float] = None,
    ) -> Optional[MemoryAllocation]:
        """Allocate memory resources"""
        self.logger.info(f"Allocating {size_bytes / (1024**2):.1f} MB memory for job {job_id}")

        # Find suitable memory segments
        suitable_segments = await self._find_suitable_segments(
            size_bytes, memory_type, numa_nodes, huge_pages
        )

        if not suitable_segments:
            self.logger.warning(f"No suitable memory segments found for {size_bytes} bytes")
            return None

        # Check if we have enough memory
        total_available = sum(
            segment.size_bytes
            for segment in suitable_segments
            if segment.state == MemoryState.AVAILABLE
        )

        if total_available < size_bytes:
            self.logger.warning(
                f"Insufficient memory: need {size_bytes}, available {total_available}"
            )
            return None

        # Create allocation
        allocation = MemoryAllocation(
            job_id=job_id,
            user_id=user_id,
            memory_type=memory_type,
            size_bytes=size_bytes,
            numa_nodes=numa_nodes or [0],
            huge_pages_enabled=huge_pages,
            memory_policy=memory_policy,
            swap_enabled=swap_enabled,
        )

        if duration:
            allocation.expires_at = time.time() + duration

        # Allocate from segments
        remaining_bytes = size_bytes
        for segment in suitable_segments:
            if remaining_bytes <= 0:
                break

            if segment.state == MemoryState.AVAILABLE:
                allocated_from_segment = min(remaining_bytes, segment.size_bytes)

                # For simplicity, we'll mark the entire segment as allocated
                # In a real implementation, you'd track partial allocations
                segment.state = MemoryState.ALLOCATED
                segment.allocated_at = time.time()
                allocation.segments.append(segment.segment_id)

                remaining_bytes -= allocated_from_segment

        self.allocations[allocation.allocation_id] = allocation
        self._stats["total_allocations"] += 1
        self._stats["active_allocations"] += 1
        self._stats["allocated_memory_bytes"] += size_bytes

        self.logger.info(f"Allocated {size_bytes / (1024**2):.1f} MB to job {job_id}")
        return allocation

    async def _find_suitable_segments(
        self,
        size_bytes: int,
        memory_type: MemoryType,
        numa_nodes: Optional[List[int]],
        huge_pages: bool,
    ) -> List[MemorySegment]:
        """Find suitable memory segments for allocation"""
        suitable_segments = []

        # Filter segments by criteria
        for segment in self.segments.values():
            # Check memory type
            if segment.memory_type != memory_type:
                continue

            # Check NUMA node preference
            if numa_nodes and segment.numa_node not in numa_nodes:
                continue

            # Check huge pages requirement
            if huge_pages and not segment.huge_pages:
                continue

            # Check availability
            if segment.state == MemoryState.AVAILABLE:
                suitable_segments.append(segment)

        # Sort by NUMA node preference and size
        numa_preference = numa_nodes[0] if numa_nodes else 0
        suitable_segments.sort(
            key=lambda s: (
                abs(s.numa_node - numa_preference),  # Prefer closer NUMA nodes
                -s.size_bytes,  # Prefer larger segments
            )
        )

        return suitable_segments

    async def deallocate_memory(self, allocation_id: str) -> bool:
        """Deallocate memory resources"""
        if allocation_id not in self.allocations:
            self.logger.warning(f"Allocation {allocation_id} not found")
            return False

        allocation = self.allocations.pop(allocation_id)

        # Free segments
        for segment_id in allocation.segments:
            if segment_id in self.segments:
                segment = self.segments[segment_id]
                segment.state = MemoryState.AVAILABLE
                segment.allocated_at = None

        self._stats["active_allocations"] -= 1
        self._stats["allocated_memory_bytes"] -= allocation.size_bytes

        self.logger.info(f"Deallocated {allocation.size_mb:.1f} MB memory")
        return True

    async def get_memory_status(self) -> Dict[str, Any]:
        """Get comprehensive memory status"""
        memory = psutil.virtual_memory()

        # Update current memory stats
        self._stats["available_memory_bytes"] = memory.available
        self._stats["cached_memory_bytes"] = getattr(memory, "cached", 0)

        # Calculate memory pressure
        memory_utilization = (memory.used / memory.total) * 100 if memory.total > 0 else 0
        self._stats["memory_pressure"] = (
            max(0, memory_utilization - 80) / 20
        )  # 0-1 scale, starts at 80% usage

        # Calculate swap pressure
        if self._stats["swap_total_bytes"] > 0:
            swap_utilization = (
                self._stats["swap_used_bytes"] / self._stats["swap_total_bytes"]
            ) * 100
            self._stats["swap_pressure"] = (
                max(0, swap_utilization - 50) / 50
            )  # 0-1 scale, starts at 50% usage

        return {
            "memory_stats": self._stats.copy(),
            "numa_topology": {
                f"node_{node_id}": {
                    "segments": segment_ids,
                    "total_bytes": sum(
                        self.segments[seg_id].size_bytes
                        for seg_id in segment_ids
                        if seg_id in self.segments
                    ),
                }
                for node_id, segment_ids in self.numa_nodes.items()
            },
            "swap_spaces": {device: swap.to_dict() for device, swap in self.swap_spaces.items()},
            "huge_pages": self.huge_pages_available.copy(),
        }

    async def get_utilization(self) -> Dict[str, float]:
        """Get memory utilization metrics"""
        memory = psutil.virtual_memory()

        memory_util = (memory.used / memory.total * 100) if memory.total > 0 else 0
        available_percent = (memory.available / memory.total * 100) if memory.total > 0 else 0

        swap_util = 0.0
        if self._stats["swap_total_bytes"] > 0:
            swap_util = self._stats["swap_used_bytes"] / self._stats["swap_total_bytes"] * 100

        return {
            "memory_total_bytes": memory.total,
            "memory_used_bytes": memory.used,
            "memory_available_bytes": memory.available,
            "memory_utilization": memory_util,
            "memory_available_percent": available_percent,
            "swap_total_bytes": self._stats["swap_total_bytes"],
            "swap_used_bytes": self._stats["swap_used_bytes"],
            "swap_utilization": swap_util,
            "memory_pressure": self._stats["memory_pressure"],
            "swap_pressure": self._stats["swap_pressure"],
            "active_allocations": self._stats["active_allocations"],
            "huge_pages_2mb_available": self._stats["huge_pages_2mb_available"],
            "huge_pages_1gb_available": self._stats["huge_pages_1gb_available"],
        }

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop for memory metrics"""
        while True:
            try:
                await self._update_memory_metrics()
                await self._update_swap_metrics()
                await self._update_huge_pages_metrics()
                await self._cleanup_expired_allocations()
                await self._check_memory_pressure()

                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.error(f"Error in memory monitoring loop: {e}")
                await asyncio.sleep(30.0)

    async def _update_memory_metrics(self) -> None:
        """Update system memory metrics"""
        try:
            memory = psutil.virtual_memory()

            self._stats["total_memory_bytes"] = memory.total
            self._stats["available_memory_bytes"] = memory.available
            self._stats["cached_memory_bytes"] = getattr(memory, "cached", 0)

            # Update memory pressure
            memory_utilization = (memory.used / memory.total) * 100 if memory.total > 0 else 0
            self._stats["memory_pressure"] = max(0, memory_utilization - 80) / 20

        except Exception as e:
            self.logger.error(f"Error updating memory metrics: {e}")

    async def _update_swap_metrics(self) -> None:
        """Update swap space metrics"""
        try:
            swap = psutil.swap_memory()

            self._stats["swap_total_bytes"] = swap.total
            self._stats["swap_used_bytes"] = swap.used

            # Update swap spaces
            for device, swap_space in self.swap_spaces.items():
                if device == "default":
                    swap_space.size_bytes = swap.total
                    swap_space.used_bytes = swap.used

            # Calculate swap pressure
            if swap.total > 0:
                swap_utilization = (swap.used / swap.total) * 100
                self._stats["swap_pressure"] = max(0, swap_utilization - 50) / 50

        except Exception as e:
            self.logger.error(f"Error updating swap metrics: {e}")

    async def _update_huge_pages_metrics(self) -> None:
        """Update huge pages metrics"""
        try:
            # Update 2MB huge pages
            hugepages_2mb_path = "/sys/kernel/mm/hugepages/hugepages-2048kB/free_hugepages"
            if os.path.exists(hugepages_2mb_path):
                with open(hugepages_2mb_path, "r") as f:
                    free_2mb = int(f.read().strip())
                    self._stats["huge_pages_2mb_available"] = free_2mb
                    self.huge_pages_available[2048] = free_2mb

            # Update 1GB huge pages
            hugepages_1gb_path = "/sys/kernel/mm/hugepages/hugepages-1048576kB/free_hugepages"
            if os.path.exists(hugepages_1gb_path):
                with open(hugepages_1gb_path, "r") as f:
                    free_1gb = int(f.read().strip())
                    self._stats["huge_pages_1gb_available"] = free_1gb
                    self.huge_pages_available[1048576] = free_1gb

        except Exception as e:
            self.logger.error(f"Error updating huge pages metrics: {e}")

    async def _cleanup_expired_allocations(self) -> None:
        """Clean up expired memory allocations"""
        current_time = time.time()
        expired_allocations = []

        for allocation_id, allocation in self.allocations.items():
            if allocation.expires_at and allocation.expires_at <= current_time:
                expired_allocations.append(allocation_id)

        for allocation_id in expired_allocations:
            await self.deallocate_memory(allocation_id)
            self.logger.info(f"Cleaned up expired memory allocation: {allocation_id}")

    async def _check_memory_pressure(self) -> None:
        """Check and respond to memory pressure"""
        memory_pressure = self._stats["memory_pressure"]
        swap_pressure = self._stats["swap_pressure"]

        if memory_pressure > 0.8:  # High memory pressure
            self.logger.warning(f"High memory pressure detected: {memory_pressure:.2f}")
            # Could trigger memory reclamation, job eviction, etc.

        if swap_pressure > 0.8:  # High swap pressure
            self.logger.warning(f"High swap pressure detected: {swap_pressure:.2f}")
            # Could trigger more aggressive memory management

    async def enable_swap_for_allocation(self, allocation_id: str, enable: bool = True) -> bool:
        """Enable or disable swap for a specific allocation"""
        if allocation_id not in self.allocations:
            return False

        allocation = self.allocations[allocation_id]
        allocation.swap_enabled = enable

        # In a real implementation, this would update cgroup memory.swappiness
        self.logger.info(
            f"{'Enabled' if enable else 'Disabled'} swap for allocation {allocation_id}"
        )
        return True

    async def set_memory_policy(self, allocation_id: str, policy: str) -> bool:
        """Set NUMA memory policy for an allocation"""
        if allocation_id not in self.allocations:
            return False

        valid_policies = ["default", "bind", "interleave", "preferred"]
        if policy not in valid_policies:
            return False

        allocation = self.allocations[allocation_id]
        allocation.memory_policy = policy

        # In a real implementation, this would use numactl or similar
        self.logger.info(f"Set memory policy to {policy} for allocation {allocation_id}")
        return True

    async def get_pool_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory pool statistics"""
        return {
            **self._stats,
            "numa_topology": {
                f"node_{node_id}": len(segment_ids)
                for node_id, segment_ids in self.numa_nodes.items()
            },
            "memory_types": {
                memory_type.value: len(
                    [s for s in self.segments.values() if s.memory_type == memory_type]
                )
                for memory_type in MemoryType
            },
        }

    async def shutdown(self) -> None:
        """Shutdown the memory pool manager"""
        self.logger.info("Shutting down memory pool manager")

        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        # Deallocate all active allocations
        allocation_ids = list(self.allocations.keys())
        for allocation_id in allocation_ids:
            await self.deallocate_memory(allocation_id)

        self.logger.info("Memory pool manager shutdown complete")
