"""
CPU Pool Manager - Manages CPU resources across multiple architectures
"""

import asyncio
import logging
import time
import psutil
import platform
import subprocess
import os
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
import threading


class CPUArchitecture(Enum):
    X86_64 = "x86_64"
    ARM64 = "arm64"
    RISCV = "riscv"
    UNKNOWN = "unknown"


class CPUState(Enum):
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    OVERSUBSCRIBED = "oversubscribed"
    MAINTENANCE = "maintenance"
    ERROR = "error"


@dataclass
class CPUCore:
    """CPU core information"""
    core_id: int
    physical_id: int
    thread_id: int
    frequency: float = 0.0  # MHz
    cache_size: int = 0  # KB
    utilization: float = 0.0  # Percentage
    temperature: float = 0.0  # Celsius
    governor: str = ""
    available: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "core_id": self.core_id,
            "physical_id": self.physical_id,
            "thread_id": self.thread_id,
            "frequency": self.frequency,
            "cache_size": self.cache_size,
            "utilization": self.utilization,
            "temperature": self.temperature,
            "governor": self.governor,
            "available": self.available
        }


@dataclass
class CPUSocket:
    """CPU socket/package information"""
    socket_id: int
    model_name: str
    architecture: CPUArchitecture
    physical_cores: int
    logical_cores: int
    base_frequency: float = 0.0  # MHz
    max_frequency: float = 0.0  # MHz
    cache_l1d: int = 0  # KB
    cache_l1i: int = 0  # KB
    cache_l2: int = 0  # KB
    cache_l3: int = 0  # KB
    tdp: float = 0.0  # Watts
    cores: Dict[int, CPUCore] = field(default_factory=dict)
    
    @property
    def available_cores(self) -> int:
        return sum(1 for core in self.cores.values() if core.available)
    
    @property
    def average_utilization(self) -> float:
        if not self.cores:
            return 0.0
        return sum(core.utilization for core in self.cores.values()) / len(self.cores)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "socket_id": self.socket_id,
            "model_name": self.model_name,
            "architecture": self.architecture.value,
            "physical_cores": self.physical_cores,
            "logical_cores": self.logical_cores,
            "available_cores": self.available_cores,
            "base_frequency": self.base_frequency,
            "max_frequency": self.max_frequency,
            "cache_l1d": self.cache_l1d,
            "cache_l1i": self.cache_l1i,
            "cache_l2": self.cache_l2,
            "cache_l3": self.cache_l3,
            "tdp": self.tdp,
            "average_utilization": self.average_utilization,
            "cores": {core_id: core.to_dict() for core_id, core in self.cores.items()}
        }


@dataclass
class CPUAllocation:
    """CPU allocation tracking"""
    allocation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""
    user_id: str = ""
    socket_ids: List[int] = field(default_factory=list)
    core_ids: List[int] = field(default_factory=list)
    cpu_shares: int = 1024  # CPU shares (Linux CFS)
    cpu_quota: int = -1  # CPU quota in microseconds
    cpu_period: int = 100000  # CPU period in microseconds (default 100ms)
    memory_nodes: List[int] = field(default_factory=list)  # NUMA nodes
    allocated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    exclusive: bool = False
    affinity_set: bool = False
    
    @property
    def cpu_limit_percent(self) -> float:
        """Calculate CPU limit as percentage"""
        if self.cpu_quota > 0:
            return (self.cpu_quota / self.cpu_period) * 100
        return 100.0 * len(self.core_ids)  # Default to number of cores * 100%
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allocation_id": self.allocation_id,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "socket_ids": self.socket_ids,
            "core_ids": self.core_ids,
            "cpu_shares": self.cpu_shares,
            "cpu_quota": self.cpu_quota,
            "cpu_period": self.cpu_period,
            "cpu_limit_percent": self.cpu_limit_percent,
            "memory_nodes": self.memory_nodes,
            "allocated_at": self.allocated_at,
            "expires_at": self.expires_at,
            "exclusive": self.exclusive,
            "affinity_set": self.affinity_set
        }


class CPUPoolManager:
    """
    Comprehensive CPU pool manager supporting multiple architectures
    and advanced scheduling features
    """
    
    def __init__(self):
        self.logger = logging.getLogger("cpu_pool_manager")
        
        # System information
        self.sockets: Dict[int, CPUSocket] = {}
        self.numa_nodes: Dict[int, List[int]] = {}  # numa_node -> core_ids
        self.architecture: CPUArchitecture = CPUArchitecture.UNKNOWN
        
        # Allocations
        self.allocations: Dict[str, CPUAllocation] = {}
        self.core_allocations: Dict[int, str] = {}  # core_id -> allocation_id
        
        # Monitoring
        self.monitoring_interval = 10.0  # 10 seconds
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # CPU governor and frequency management
        self.frequency_governors = ["performance", "powersave", "ondemand", "conservative"]
        self.current_governor = "ondemand"
        
        # Statistics
        self._stats = {
            "total_sockets": 0,
            "total_physical_cores": 0,
            "total_logical_cores": 0,
            "available_cores": 0,
            "allocated_cores": 0,
            "average_utilization": 0.0,
            "average_frequency": 0.0,
            "average_temperature": 0.0,
            "total_allocations": 0,
            "active_allocations": 0,
            "numa_nodes": 0
        }
        
    async def initialize(self) -> None:
        """Initialize the CPU pool manager"""
        self.logger.info("Initializing CPU pool manager")
        
        # Detect system architecture
        await self._detect_architecture()
        
        # Discover CPU topology
        await self._discover_cpu_topology()
        
        # Discover NUMA topology
        await self._discover_numa_topology()
        
        # Initialize CPU monitoring
        await self._initialize_cpu_monitoring()
        
        # Start monitoring loop
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        total_cores = sum(socket.logical_cores for socket in self.sockets.values())
        self.logger.info(f"CPU pool initialized with {total_cores} logical cores across {len(self.sockets)} sockets")
        
    async def _detect_architecture(self) -> None:
        """Detect CPU architecture"""
        machine = platform.machine().lower()
        
        if machine in ["x86_64", "amd64"]:
            self.architecture = CPUArchitecture.X86_64
        elif machine in ["arm64", "aarch64"]:
            self.architecture = CPUArchitecture.ARM64
        elif machine.startswith("riscv"):
            self.architecture = CPUArchitecture.RISCV
        else:
            self.architecture = CPUArchitecture.UNKNOWN
            
        self.logger.info(f"Detected CPU architecture: {self.architecture.value}")
        
    async def _discover_cpu_topology(self) -> None:
        """Discover CPU socket and core topology"""
        try:
            # Use psutil for basic CPU info
            cpu_info = {}
            
            # Try to get detailed CPU info from /proc/cpuinfo on Linux
            if os.path.exists("/proc/cpuinfo"):
                cpu_info = await self._parse_proc_cpuinfo()
            
            # Get logical CPU count
            logical_cpu_count = psutil.cpu_count(logical=True)
            physical_cpu_count = psutil.cpu_count(logical=False)
            
            if not cpu_info:
                # Fallback: create a simple topology
                socket = CPUSocket(
                    socket_id=0,
                    model_name=platform.processor() or "Unknown CPU",
                    architecture=self.architecture,
                    physical_cores=physical_cpu_count,
                    logical_cores=logical_cpu_count
                )
                
                # Create cores
                for core_id in range(logical_cpu_count):
                    core = CPUCore(
                        core_id=core_id,
                        physical_id=0,
                        thread_id=core_id
                    )
                    socket.cores[core_id] = core
                
                self.sockets[0] = socket
                
            else:
                # Build topology from detailed info
                await self._build_topology_from_cpuinfo(cpu_info)
                
            # Try to get frequency information
            await self._discover_cpu_frequencies()
            
            # Try to get cache information
            await self._discover_cpu_caches()
            
        except Exception as e:
            self.logger.error(f"Error discovering CPU topology: {e}")
            
    async def _parse_proc_cpuinfo(self) -> Dict[int, Dict[str, str]]:
        """Parse /proc/cpuinfo for detailed CPU information"""
        cpu_info = {}
        current_cpu = {}
        
        try:
            with open("/proc/cpuinfo", 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        if current_cpu and "processor" in current_cpu:
                            cpu_id = int(current_cpu["processor"])
                            cpu_info[cpu_id] = current_cpu.copy()
                        current_cpu = {}
                        continue
                    
                    if ":" in line:
                        key, value = line.split(":", 1)
                        current_cpu[key.strip()] = value.strip()
                
                # Don't forget the last CPU
                if current_cpu and "processor" in current_cpu:
                    cpu_id = int(current_cpu["processor"])
                    cpu_info[cpu_id] = current_cpu.copy()
                    
        except Exception as e:
            self.logger.error(f"Error parsing /proc/cpuinfo: {e}")
            
        return cpu_info
        
    async def _build_topology_from_cpuinfo(self, cpu_info: Dict[int, Dict[str, str]]) -> None:
        """Build CPU topology from parsed cpuinfo"""
        socket_map = {}
        
        for cpu_id, info in cpu_info.items():
            physical_id = int(info.get("physical id", 0))
            core_id = int(info.get("core id", cpu_id))
            
            # Create socket if not exists
            if physical_id not in self.sockets:
                socket = CPUSocket(
                    socket_id=physical_id,
                    model_name=info.get("model name", "Unknown CPU"),
                    architecture=self.architecture
                )
                
                # Parse frequency info if available
                if "cpu MHz" in info:
                    socket.base_frequency = float(info["cpu MHz"])
                
                self.sockets[physical_id] = socket
            
            # Create core
            core = CPUCore(
                core_id=cpu_id,
                physical_id=physical_id,
                thread_id=core_id
            )
            
            if "cpu MHz" in info:
                core.frequency = float(info["cpu MHz"])
                
            self.sockets[physical_id].cores[cpu_id] = core
            
        # Update socket core counts
        for socket in self.sockets.values():
            socket.logical_cores = len(socket.cores)
            # Count unique physical cores (same core_id within socket)
            physical_cores = set()
            for core in socket.cores.values():
                physical_cores.add(core.thread_id)
            socket.physical_cores = len(physical_cores)
            
    async def _discover_cpu_frequencies(self) -> None:
        """Discover CPU frequency information"""
        try:
            # Try to get frequency info from /sys/devices/system/cpu/
            cpu_dirs = [d for d in os.listdir("/sys/devices/system/cpu/") if d.startswith("cpu") and d[3:].isdigit()]
            
            for cpu_dir in cpu_dirs:
                cpu_id = int(cpu_dir[3:])
                base_path = f"/sys/devices/system/cpu/{cpu_dir}/cpufreq"
                
                if os.path.exists(base_path):
                    # Find the socket and core for this CPU
                    core = None
                    for socket in self.sockets.values():
                        if cpu_id in socket.cores:
                            core = socket.cores[cpu_id]
                            break
                    
                    if not core:
                        continue
                    
                    # Read frequency files
                    try:
                        with open(f"{base_path}/scaling_cur_freq", 'r') as f:
                            core.frequency = float(f.read().strip()) / 1000.0  # Convert kHz to MHz
                    except:
                        pass
                    
                    try:
                        with open(f"{base_path}/scaling_governor", 'r') as f:
                            core.governor = f.read().strip()
                    except:
                        pass
                        
        except Exception as e:
            self.logger.error(f"Error discovering CPU frequencies: {e}")
            
    async def _discover_cpu_caches(self) -> None:
        """Discover CPU cache information"""
        try:
            for socket in self.sockets.values():
                # Try lscpu command for cache info
                result = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if "L1d cache" in line:
                            cache_str = line.split(':')[1].strip()
                            socket.cache_l1d = self._parse_cache_size(cache_str)
                        elif "L1i cache" in line:
                            cache_str = line.split(':')[1].strip()
                            socket.cache_l1i = self._parse_cache_size(cache_str)
                        elif "L2 cache" in line:
                            cache_str = line.split(':')[1].strip()
                            socket.cache_l2 = self._parse_cache_size(cache_str)
                        elif "L3 cache" in line:
                            cache_str = line.split(':')[1].strip()
                            socket.cache_l3 = self._parse_cache_size(cache_str)
                            
        except Exception as e:
            self.logger.error(f"Error discovering CPU caches: {e}")
            
    def _parse_cache_size(self, cache_str: str) -> int:
        """Parse cache size string to KB"""
        cache_str = cache_str.upper()
        if 'KB' in cache_str:
            return int(cache_str.replace('KB', '').strip())
        elif 'MB' in cache_str:
            return int(float(cache_str.replace('MB', '').strip()) * 1024)
        elif 'K' in cache_str:
            return int(cache_str.replace('K', '').strip())
        elif 'M' in cache_str:
            return int(float(cache_str.replace('M', '').strip()) * 1024)
        return 0
        
    async def _discover_numa_topology(self) -> None:
        """Discover NUMA topology"""
        try:
            # Try numactl command
            result = subprocess.run(["numactl", "--hardware"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                await self._parse_numactl_output(result.stdout)
            else:
                # Fallback: assume single NUMA node
                self.numa_nodes[0] = list(range(sum(socket.logical_cores for socket in self.sockets.values())))
                
        except Exception as e:
            self.logger.error(f"Error discovering NUMA topology: {e}")
            # Default to single NUMA node
            self.numa_nodes[0] = list(range(sum(socket.logical_cores for socket in self.sockets.values())))
            
    async def _parse_numactl_output(self, output: str) -> None:
        """Parse numactl --hardware output"""
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("node") and "cpus:" in line:
                parts = line.split()
                node_id = int(parts[1])
                cpus_start = line.find("cpus:") + 5
                cpus_str = line[cpus_start:].strip()
                
                if cpus_str and cpus_str != "(null)":
                    # Parse CPU list (can be ranges like "0-7" or individual "0 1 2 3")
                    cpu_ids = []
                    for cpu_part in cpus_str.split():
                        if '-' in cpu_part:
                            start, end = cpu_part.split('-')
                            cpu_ids.extend(range(int(start), int(end) + 1))
                        else:
                            cpu_ids.append(int(cpu_part))
                    
                    self.numa_nodes[node_id] = cpu_ids
                    
    async def _initialize_cpu_monitoring(self) -> None:
        """Initialize CPU monitoring capabilities"""
        try:
            # Check if we can monitor CPU temperatures
            if os.path.exists("/sys/class/thermal/"):
                thermal_zones = [d for d in os.listdir("/sys/class/thermal/") if d.startswith("thermal_zone")]
                if thermal_zones:
                    self.logger.info(f"Found {len(thermal_zones)} thermal zones for temperature monitoring")
                    
            # Check CPU frequency scaling support
            if os.path.exists("/sys/devices/system/cpu/cpu0/cpufreq/"):
                self.logger.info("CPU frequency scaling supported")
                
        except Exception as e:
            self.logger.error(f"Error initializing CPU monitoring: {e}")
            
    async def allocate_cpu(
        self,
        job_id: str,
        user_id: str,
        cpu_cores: int = 1,
        cpu_shares: int = 1024,
        cpu_quota: int = -1,
        memory_nodes: Optional[List[int]] = None,
        exclusive: bool = False,
        numa_affinity: bool = True,
        duration: Optional[float] = None
    ) -> Optional[CPUAllocation]:
        """Allocate CPU resources"""
        self.logger.info(f"Allocating {cpu_cores} CPU cores for job {job_id} (exclusive: {exclusive})")
        
        # Find suitable cores
        suitable_cores = await self._find_suitable_cores(cpu_cores, numa_affinity, exclusive)
        
        if len(suitable_cores) < cpu_cores:
            self.logger.warning(f"Insufficient CPU cores: need {cpu_cores}, found {len(suitable_cores)}")
            return None
        
        selected_cores = suitable_cores[:cpu_cores]
        
        # Determine sockets and NUMA nodes
        socket_ids = list(set(self._get_socket_for_core(core_id) for core_id in selected_cores))
        
        if memory_nodes is None:
            # Auto-select NUMA nodes based on core allocation
            memory_nodes = []
            for core_id in selected_cores:
                for numa_node, cores in self.numa_nodes.items():
                    if core_id in cores and numa_node not in memory_nodes:
                        memory_nodes.append(numa_node)
        
        # Create allocation
        allocation = CPUAllocation(
            job_id=job_id,
            user_id=user_id,
            socket_ids=socket_ids,
            core_ids=selected_cores,
            cpu_shares=cpu_shares,
            cpu_quota=cpu_quota,
            memory_nodes=memory_nodes,
            exclusive=exclusive
        )
        
        if duration:
            allocation.expires_at = time.time() + duration
        
        # Mark cores as allocated
        for core_id in selected_cores:
            self.core_allocations[core_id] = allocation.allocation_id
            # Mark core as unavailable if exclusive
            if exclusive:
                socket_id = self._get_socket_for_core(core_id)
                if socket_id is not None:
                    self.sockets[socket_id].cores[core_id].available = False
        
        self.allocations[allocation.allocation_id] = allocation
        self._stats["total_allocations"] += 1
        self._stats["active_allocations"] += 1
        
        # Set CPU affinity if requested
        if exclusive or numa_affinity:
            await self._set_cpu_affinity(allocation)
        
        self.logger.info(f"Allocated CPU cores {selected_cores} to job {job_id}")
        return allocation
        
    async def _find_suitable_cores(self, cpu_cores: int, numa_affinity: bool, exclusive: bool) -> List[int]:
        """Find suitable CPU cores for allocation"""
        suitable_cores = []
        
        if numa_affinity:
            # Try to allocate from the same NUMA node first
            for numa_node, node_cores in self.numa_nodes.items():
                available_cores = []
                
                for core_id in node_cores:
                    if self._is_core_available(core_id, exclusive):
                        available_cores.append(core_id)
                
                if len(available_cores) >= cpu_cores:
                    # Sort by utilization (prefer less utilized cores)
                    available_cores.sort(key=lambda core_id: self._get_core_utilization(core_id))
                    return available_cores[:cpu_cores]
                
                # Add partial allocation from this NUMA node
                suitable_cores.extend(available_cores)
                if len(suitable_cores) >= cpu_cores:
                    break
        else:
            # Allocate from any available cores
            for socket in self.sockets.values():
                for core_id, core in socket.cores.items():
                    if self._is_core_available(core_id, exclusive):
                        suitable_cores.append(core_id)
                        
                    if len(suitable_cores) >= cpu_cores:
                        break
                        
                if len(suitable_cores) >= cpu_cores:
                    break
        
        # Sort by utilization and NUMA locality
        suitable_cores.sort(key=lambda core_id: (
            self._get_core_utilization(core_id),
            self._get_numa_node_for_core(core_id)
        ))
        
        return suitable_cores
        
    def _is_core_available(self, core_id: int, exclusive: bool) -> bool:
        """Check if a core is available for allocation"""
        if core_id in self.core_allocations:
            if exclusive:
                return False
            # Check if current allocation allows sharing
            current_allocation = self.allocations.get(self.core_allocations[core_id])
            if current_allocation and current_allocation.exclusive:
                return False
        
        # Check core state
        socket_id = self._get_socket_for_core(core_id)
        if socket_id is not None and socket_id in self.sockets:
            core = self.sockets[socket_id].cores.get(core_id)
            if core and not core.available:
                return False
        
        return True
        
    def _get_core_utilization(self, core_id: int) -> float:
        """Get current utilization for a core"""
        socket_id = self._get_socket_for_core(core_id)
        if socket_id is not None and socket_id in self.sockets:
            core = self.sockets[socket_id].cores.get(core_id)
            if core:
                return core.utilization
        return 0.0
        
    def _get_socket_for_core(self, core_id: int) -> Optional[int]:
        """Get socket ID for a given core ID"""
        for socket_id, socket in self.sockets.items():
            if core_id in socket.cores:
                return socket_id
        return None
        
    def _get_numa_node_for_core(self, core_id: int) -> int:
        """Get NUMA node for a given core ID"""
        for numa_node, cores in self.numa_nodes.items():
            if core_id in cores:
                return numa_node
        return 0  # Default to node 0
        
    async def _set_cpu_affinity(self, allocation: CPUAllocation) -> None:
        """Set CPU affinity for the allocation"""
        try:
            # This would typically involve setting cgroup cpu.affinity
            # For now, just mark that affinity has been set
            allocation.affinity_set = True
            self.logger.info(f"Set CPU affinity for allocation {allocation.allocation_id}")
            
        except Exception as e:
            self.logger.error(f"Error setting CPU affinity: {e}")
            
    async def deallocate_cpu(self, allocation_id: str) -> bool:
        """Deallocate CPU resources"""
        if allocation_id not in self.allocations:
            self.logger.warning(f"Allocation {allocation_id} not found")
            return False
        
        allocation = self.allocations.pop(allocation_id)
        
        # Free cores
        for core_id in allocation.core_ids:
            if core_id in self.core_allocations:
                del self.core_allocations[core_id]
            
            # Mark core as available
            socket_id = self._get_socket_for_core(core_id)
            if socket_id is not None and socket_id in self.sockets:
                core = self.sockets[socket_id].cores.get(core_id)
                if core:
                    core.available = True
        
        self._stats["active_allocations"] -= 1
        self.logger.info(f"Deallocated CPU cores {allocation.core_ids}")
        
        return True
        
    async def get_cpu_status(self, socket_id: Optional[int] = None) -> Dict[str, Any]:
        """Get CPU status information"""
        if socket_id is not None:
            if socket_id in self.sockets:
                return self.sockets[socket_id].to_dict()
            return {}
        
        # Return status for all sockets
        return {
            f"socket_{socket_id}": socket.to_dict()
            for socket_id, socket in self.sockets.items()
        }
        
    async def get_utilization(self) -> Dict[str, float]:
        """Get CPU utilization metrics"""
        if not self.sockets:
            return {}
        
        total_cores = sum(socket.logical_cores for socket in self.sockets.values())
        available_cores = sum(socket.available_cores for socket in self.sockets.values())
        allocated_cores = total_cores - available_cores
        
        avg_utilization = sum(socket.average_utilization for socket in self.sockets.values()) / len(self.sockets)
        avg_frequency = sum(
            sum(core.frequency for core in socket.cores.values()) / len(socket.cores) if socket.cores else 0
            for socket in self.sockets.values()
        ) / len(self.sockets) if self.sockets else 0
        
        return {
            "cpu_sockets": len(self.sockets),
            "cpu_cores_total": total_cores,
            "cpu_cores_available": available_cores,
            "cpu_cores_allocated": allocated_cores,
            "cpu_utilization_avg": avg_utilization,
            "cpu_frequency_avg": avg_frequency,
            "numa_nodes": len(self.numa_nodes)
        }
        
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop for CPU metrics updates"""
        while True:
            try:
                await self._update_cpu_metrics()
                await self._cleanup_expired_allocations()
                self._update_cpu_stats()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in CPU monitoring loop: {e}")
                await asyncio.sleep(30.0)
                
    async def _update_cpu_metrics(self) -> None:
        """Update CPU metrics from system"""
        try:
            # Update CPU utilization using psutil
            cpu_percent_per_cpu = psutil.cpu_percent(percpu=True, interval=None)
            
            core_index = 0
            for socket in self.sockets.values():
                for core in socket.cores.values():
                    if core_index < len(cpu_percent_per_cpu):
                        core.utilization = cpu_percent_per_cpu[core_index]
                        core_index += 1
                        
            # Update frequencies if available
            await self._update_cpu_frequencies()
            
            # Update temperatures if available  
            await self._update_cpu_temperatures()
            
        except Exception as e:
            self.logger.error(f"Error updating CPU metrics: {e}")
            
    async def _update_cpu_frequencies(self) -> None:
        """Update CPU frequencies from system"""
        try:
            for socket in self.sockets.values():
                for core_id, core in socket.cores.items():
                    freq_path = f"/sys/devices/system/cpu/cpu{core_id}/cpufreq/scaling_cur_freq"
                    if os.path.exists(freq_path):
                        with open(freq_path, 'r') as f:
                            freq_khz = int(f.read().strip())
                            core.frequency = freq_khz / 1000.0  # Convert to MHz
                            
        except Exception as e:
            self.logger.error(f"Error updating CPU frequencies: {e}")
            
    async def _update_cpu_temperatures(self) -> None:
        """Update CPU temperatures from thermal zones"""
        try:
            thermal_zones = []
            if os.path.exists("/sys/class/thermal/"):
                thermal_zones = [d for d in os.listdir("/sys/class/thermal/") if d.startswith("thermal_zone")]
            
            for zone in thermal_zones:
                temp_path = f"/sys/class/thermal/{zone}/temp"
                if os.path.exists(temp_path):
                    with open(temp_path, 'r') as f:
                        temp_millicelsius = int(f.read().strip())
                        temp_celsius = temp_millicelsius / 1000.0
                        
                        # Assign temperature to cores (simplified approach)
                        # In reality, you'd need to map thermal zones to specific cores
                        for socket in self.sockets.values():
                            for core in socket.cores.values():
                                core.temperature = temp_celsius
                                break  # Just update one core per thermal zone for now
                            break
                        
        except Exception as e:
            self.logger.error(f"Error updating CPU temperatures: {e}")
            
    async def _cleanup_expired_allocations(self) -> None:
        """Clean up expired allocations"""
        current_time = time.time()
        expired_allocations = []
        
        for allocation_id, allocation in self.allocations.items():
            if allocation.expires_at and allocation.expires_at <= current_time:
                expired_allocations.append(allocation_id)
        
        for allocation_id in expired_allocations:
            await self.deallocate_cpu(allocation_id)
            self.logger.info(f"Cleaned up expired CPU allocation: {allocation_id}")
            
    def _update_cpu_stats(self) -> None:
        """Update CPU statistics"""
        self._stats["total_sockets"] = len(self.sockets)
        self._stats["total_physical_cores"] = sum(socket.physical_cores for socket in self.sockets.values())
        self._stats["total_logical_cores"] = sum(socket.logical_cores for socket in self.sockets.values())
        self._stats["available_cores"] = sum(socket.available_cores for socket in self.sockets.values())
        self._stats["allocated_cores"] = self._stats["total_logical_cores"] - self._stats["available_cores"]
        self._stats["numa_nodes"] = len(self.numa_nodes)
        
        if self.sockets:
            self._stats["average_utilization"] = sum(socket.average_utilization for socket in self.sockets.values()) / len(self.sockets)
            
            total_freq = 0
            freq_count = 0
            total_temp = 0
            temp_count = 0
            
            for socket in self.sockets.values():
                for core in socket.cores.values():
                    if core.frequency > 0:
                        total_freq += core.frequency
                        freq_count += 1
                    if core.temperature > 0:
                        total_temp += core.temperature
                        temp_count += 1
                        
            self._stats["average_frequency"] = total_freq / freq_count if freq_count > 0 else 0
            self._stats["average_temperature"] = total_temp / temp_count if temp_count > 0 else 0
        
        self._stats["active_allocations"] = len(self.allocations)
        
    async def get_pool_statistics(self) -> Dict[str, Any]:
        """Get comprehensive CPU pool statistics"""
        architecture_stats = {
            "architecture": self.architecture.value,
            "sockets": len(self.sockets),
            "numa_nodes": len(self.numa_nodes)
        }
        
        socket_details = {}
        for socket_id, socket in self.sockets.items():
            socket_details[f"socket_{socket_id}"] = {
                "model": socket.model_name,
                "physical_cores": socket.physical_cores,
                "logical_cores": socket.logical_cores,
                "available_cores": socket.available_cores,
                "base_frequency": socket.base_frequency,
                "cache_l3": socket.cache_l3
            }
        
        return {
            **self._stats,
            "architecture_info": architecture_stats,
            "socket_details": socket_details,
            "numa_topology": self.numa_nodes
        }
        
    async def shutdown(self) -> None:
        """Shutdown the CPU pool manager"""
        self.logger.info("Shutting down CPU pool manager")
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Deallocate all active allocations
        allocation_ids = list(self.allocations.keys())
        for allocation_id in allocation_ids:
            await self.deallocate_cpu(allocation_id)
        
        self.logger.info("CPU pool manager shutdown complete")