"""
GPU Pool Manager - Manages GPU resources across multiple providers
"""

import asyncio
import logging
import time
import subprocess
import json
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid


class GPUVendor(Enum):
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    UNKNOWN = "unknown"


class GPUState(Enum):
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    MAINTENANCE = "maintenance"
    ERROR = "error"


@dataclass
class GPUDevice:
    """GPU device information"""
    device_id: str
    vendor: GPUVendor
    model: str
    memory_total: int  # MB
    memory_free: int  # MB
    compute_capability: str = ""
    power_limit: float = 0.0  # Watts
    temperature: float = 0.0  # Celsius
    utilization: float = 0.0  # Percentage
    processes: List[Dict[str, Any]] = field(default_factory=list)
    state: GPUState = GPUState.AVAILABLE
    node_id: str = "local"
    last_updated: float = field(default_factory=time.time)
    
    @property
    def memory_used(self) -> int:
        return self.memory_total - self.memory_free
    
    @property
    def memory_utilization(self) -> float:
        if self.memory_total > 0:
            return (self.memory_used / self.memory_total) * 100
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "vendor": self.vendor.value,
            "model": self.model,
            "memory_total": self.memory_total,
            "memory_free": self.memory_free,
            "memory_used": self.memory_used,
            "memory_utilization": self.memory_utilization,
            "compute_capability": self.compute_capability,
            "power_limit": self.power_limit,
            "temperature": self.temperature,
            "utilization": self.utilization,
            "processes": self.processes,
            "state": self.state.value,
            "node_id": self.node_id,
            "last_updated": self.last_updated
        }


@dataclass
class GPUAllocation:
    """GPU allocation tracking"""
    allocation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""
    user_id: str = ""
    device_ids: List[str] = field(default_factory=list)
    memory_reserved: Dict[str, int] = field(default_factory=dict)  # device_id -> MB
    allocated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    exclusive: bool = False  # Exclusive access to GPU
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allocation_id": self.allocation_id,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "device_ids": self.device_ids,
            "memory_reserved": self.memory_reserved,
            "allocated_at": self.allocated_at,
            "expires_at": self.expires_at,
            "exclusive": self.exclusive
        }


class GPUPoolManager:
    """
    Comprehensive GPU pool manager supporting NVIDIA, AMD, and Intel GPUs
    """
    
    def __init__(self):
        self.logger = logging.getLogger("gpu_pool_manager")
        
        # GPU device tracking
        self.devices: Dict[str, GPUDevice] = {}
        self.allocations: Dict[str, GPUAllocation] = {}
        
        # Monitoring
        self.monitoring_interval = 30.0  # 30 seconds
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # GPU vendor support
        self.nvidia_available = False
        self.amd_available = False
        self.intel_available = False
        
        # Statistics
        self._stats = {
            "total_gpus": 0,
            "available_gpus": 0,
            "allocated_gpus": 0,
            "total_memory": 0,
            "allocated_memory": 0,
            "average_utilization": 0.0,
            "average_temperature": 0.0,
            "total_allocations": 0,
            "active_allocations": 0
        }
        
    async def initialize(self) -> None:
        """Initialize the GPU pool manager"""
        self.logger.info("Initializing GPU pool manager")
        
        # Detect available GPU vendors
        await self._detect_gpu_vendors()
        
        # Discover GPU devices
        await self._discover_gpu_devices()
        
        # Start monitoring
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info(f"GPU pool initialized with {len(self.devices)} devices")
        
    async def _detect_gpu_vendors(self) -> None:
        """Detect which GPU vendors are available"""
        # Check NVIDIA
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.nvidia_available = True
                self.logger.info("NVIDIA GPU support detected")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Check AMD (ROCm)
        try:
            result = subprocess.run(
                ["rocm-smi", "--showproductname"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.amd_available = True
                self.logger.info("AMD GPU support detected")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Check Intel (Level Zero)
        try:
            result = subprocess.run(
                ["clinfo"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and "Intel" in result.stdout:
                self.intel_available = True
                self.logger.info("Intel GPU support detected")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        if not any([self.nvidia_available, self.amd_available, self.intel_available]):
            self.logger.warning("No GPU vendors detected")
            
    async def _discover_gpu_devices(self) -> None:
        """Discover and catalog all available GPU devices"""
        if self.nvidia_available:
            await self._discover_nvidia_gpus()
        
        if self.amd_available:
            await self._discover_amd_gpus()
            
        if self.intel_available:
            await self._discover_intel_gpus()
            
        # Update statistics
        self._update_device_stats()
        
    async def _discover_nvidia_gpus(self) -> None:
        """Discover NVIDIA GPUs using nvidia-ml-py or nvidia-smi"""
        try:
            # Try nvidia-ml-py first
            try:
                import pynvml
                pynvml.nvmlInit()
                
                device_count = pynvml.nvmlDeviceGetCount()
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    
                    # Get device info
                    name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                    memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    
                    device = GPUDevice(
                        device_id=f"nvidia-{i}",
                        vendor=GPUVendor.NVIDIA,
                        model=name,
                        memory_total=memory_info.total // (1024 * 1024),  # Convert to MB
                        memory_free=memory_info.free // (1024 * 1024),
                        node_id="local"
                    )
                    
                    # Get additional info if available
                    try:
                        major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
                        device.compute_capability = f"{major}.{minor}"
                        
                        device.power_limit = pynvml.nvmlDeviceGetPowerManagementLimitConstraints(handle)[1] / 1000.0
                        device.temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                        device.utilization = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                    except:
                        pass
                    
                    self.devices[device.device_id] = device
                    self.logger.info(f"Discovered NVIDIA GPU: {device.model} ({device.memory_total} MB)")
                
            except ImportError:
                # Fallback to nvidia-smi
                await self._discover_nvidia_gpus_smi()
                
        except Exception as e:
            self.logger.error(f"Error discovering NVIDIA GPUs: {e}")
            
    async def _discover_nvidia_gpus_smi(self) -> None:
        """Discover NVIDIA GPUs using nvidia-smi command"""
        try:
            # Get GPU information using nvidia-smi
            result = subprocess.run([
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,memory.free,compute_cap,power.limit,temperature.gpu,utilization.gpu",
                "--format=csv,noheader,nounits"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 4:
                            index = parts[0]
                            name = parts[1]
                            memory_total = int(parts[2]) if parts[2].isdigit() else 0
                            memory_free = int(parts[3]) if parts[3].isdigit() else 0
                            
                            device = GPUDevice(
                                device_id=f"nvidia-{index}",
                                vendor=GPUVendor.NVIDIA,
                                model=name,
                                memory_total=memory_total,
                                memory_free=memory_free,
                                node_id="local"
                            )
                            
                            # Parse optional fields
                            if len(parts) > 4 and parts[4] != "N/A":
                                device.compute_capability = parts[4]
                            if len(parts) > 5 and parts[5].replace('.', '').isdigit():
                                device.power_limit = float(parts[5])
                            if len(parts) > 6 and parts[6].replace('.', '').isdigit():
                                device.temperature = float(parts[6])
                            if len(parts) > 7 and parts[7].replace('.', '').isdigit():
                                device.utilization = float(parts[7])
                            
                            self.devices[device.device_id] = device
                            self.logger.info(f"Discovered NVIDIA GPU: {device.model} ({device.memory_total} MB)")
                            
        except Exception as e:
            self.logger.error(f"Error discovering NVIDIA GPUs with nvidia-smi: {e}")
            
    async def _discover_amd_gpus(self) -> None:
        """Discover AMD GPUs using ROCm tools"""
        try:
            # Use rocm-smi to get GPU information
            result = subprocess.run([
                "rocm-smi", "--showproductname", "--showmeminfo", "vram", "--showuse", "--showtemp"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Parse rocm-smi output (format varies)
                lines = result.stdout.split('\n')
                current_gpu = 0
                
                for line in lines:
                    if "GPU[" in line and "]:" in line:
                        # Extract GPU info from rocm-smi output
                        gpu_id = f"amd-{current_gpu}"
                        
                        device = GPUDevice(
                            device_id=gpu_id,
                            vendor=GPUVendor.AMD,
                            model="AMD GPU",  # rocm-smi doesn't always provide model name
                            memory_total=8192,  # Default, would need more parsing
                            memory_free=8192,
                            node_id="local"
                        )
                        
                        self.devices[device.device_id] = device
                        current_gpu += 1
                        
        except Exception as e:
            self.logger.error(f"Error discovering AMD GPUs: {e}")
            
    async def _discover_intel_gpus(self) -> None:
        """Discover Intel GPUs using Intel GPU tools"""
        try:
            # Intel GPU discovery is more complex and depends on the specific tools available
            # This is a placeholder implementation
            device = GPUDevice(
                device_id="intel-0",
                vendor=GPUVendor.INTEL,
                model="Intel GPU",
                memory_total=4096,  # Default
                memory_free=4096,
                node_id="local"
            )
            
            self.devices[device.device_id] = device
            
        except Exception as e:
            self.logger.error(f"Error discovering Intel GPUs: {e}")
            
    async def allocate_gpu(
        self,
        job_id: str,
        user_id: str,
        gpu_count: int = 1,
        memory_per_gpu: int = 0,  # MB, 0 = allocate entire GPU
        exclusive: bool = False,
        vendor_preference: Optional[GPUVendor] = None,
        duration: Optional[float] = None
    ) -> Optional[GPUAllocation]:
        """Allocate GPU resources"""
        self.logger.info(
            f"Allocating {gpu_count} GPU(s) for job {job_id} "
            f"(memory: {memory_per_gpu} MB per GPU, exclusive: {exclusive})"
        )
        
        # Find suitable GPUs
        suitable_gpus = await self._find_suitable_gpus(
            gpu_count, memory_per_gpu, exclusive, vendor_preference
        )
        
        if len(suitable_gpus) < gpu_count:
            self.logger.warning(f"Insufficient GPU resources: need {gpu_count}, found {len(suitable_gpus)}")
            return None
        
        # Create allocation
        allocation = GPUAllocation(
            job_id=job_id,
            user_id=user_id,
            device_ids=[gpu.device_id for gpu in suitable_gpus[:gpu_count]],
            exclusive=exclusive
        )
        
        if duration:
            allocation.expires_at = time.time() + duration
        
        # Reserve memory on each GPU
        for gpu in suitable_gpus[:gpu_count]:
            if memory_per_gpu > 0:
                allocation.memory_reserved[gpu.device_id] = memory_per_gpu
                # Update available memory
                self.devices[gpu.device_id].memory_free -= memory_per_gpu
            else:
                # Allocate entire GPU
                allocation.memory_reserved[gpu.device_id] = gpu.memory_free
                self.devices[gpu.device_id].memory_free = 0
            
            # Update GPU state
            if exclusive or memory_per_gpu == 0:
                self.devices[gpu.device_id].state = GPUState.ALLOCATED
        
        self.allocations[allocation.allocation_id] = allocation
        self._stats["total_allocations"] += 1
        self._stats["active_allocations"] += 1
        
        self.logger.info(f"Allocated GPUs {allocation.device_ids} to job {job_id}")
        return allocation
        
    async def _find_suitable_gpus(
        self,
        gpu_count: int,
        memory_per_gpu: int,
        exclusive: bool,
        vendor_preference: Optional[GPUVendor]
    ) -> List[GPUDevice]:
        """Find suitable GPUs for allocation"""
        suitable_gpus = []
        
        # Filter available GPUs
        for device in self.devices.values():
            # Check basic availability
            if device.state != GPUState.AVAILABLE:
                continue
            
            # Check vendor preference
            if vendor_preference and device.vendor != vendor_preference:
                continue
            
            # Check memory requirements
            if memory_per_gpu > 0 and device.memory_free < memory_per_gpu:
                continue
            
            # For exclusive access, GPU must be completely free
            if exclusive and device.memory_used > 0:
                continue
            
            suitable_gpus.append(device)
            
            if len(suitable_gpus) >= gpu_count:
                break
        
        # Sort by preference (free memory, low utilization)
        suitable_gpus.sort(
            key=lambda gpu: (gpu.memory_free, -gpu.utilization, -gpu.temperature)
        )
        
        return suitable_gpus
        
    async def deallocate_gpu(self, allocation_id: str) -> bool:
        """Deallocate GPU resources"""
        if allocation_id not in self.allocations:
            self.logger.warning(f"Allocation {allocation_id} not found")
            return False
        
        allocation = self.allocations.pop(allocation_id)
        
        # Free resources on each GPU
        for device_id in allocation.device_ids:
            if device_id in self.devices:
                device = self.devices[device_id]
                
                # Restore memory
                reserved_memory = allocation.memory_reserved.get(device_id, 0)
                device.memory_free += reserved_memory
                device.memory_free = min(device.memory_free, device.memory_total)
                
                # Update state
                if device.memory_free == device.memory_total:
                    device.state = GPUState.AVAILABLE
        
        self._stats["active_allocations"] -= 1
        self.logger.info(f"Deallocated GPUs {allocation.device_ids}")
        
        return True
        
    async def get_gpu_status(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Get GPU status information"""
        if device_id:
            if device_id in self.devices:
                return self.devices[device_id].to_dict()
            return {}
        
        # Return status for all GPUs
        return {
            device_id: device.to_dict()
            for device_id, device in self.devices.items()
        }
        
    async def get_utilization(self) -> Dict[str, float]:
        """Get GPU utilization metrics"""
        if not self.devices:
            return {}
        
        total_memory = sum(device.memory_total for device in self.devices.values())
        used_memory = sum(device.memory_used for device in self.devices.values())
        
        avg_gpu_util = sum(device.utilization for device in self.devices.values()) / len(self.devices)
        avg_memory_util = (used_memory / total_memory * 100) if total_memory > 0 else 0
        
        return {
            "gpu_count_total": len(self.devices),
            "gpu_count_available": len([d for d in self.devices.values() if d.state == GPUState.AVAILABLE]),
            "gpu_count_allocated": len([d for d in self.devices.values() if d.state == GPUState.ALLOCATED]),
            "gpu_utilization_avg": avg_gpu_util,
            "gpu_memory_total_mb": total_memory,
            "gpu_memory_used_mb": used_memory,
            "gpu_memory_utilization": avg_memory_util,
            "gpu_temperature_avg": sum(device.temperature for device in self.devices.values()) / len(self.devices)
        }
        
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop for GPU status updates"""
        while True:
            try:
                await self._update_gpu_metrics()
                await self._cleanup_expired_allocations()
                self._update_device_stats()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in GPU monitoring loop: {e}")
                await asyncio.sleep(30.0)
                
    async def _update_gpu_metrics(self) -> None:
        """Update GPU metrics from hardware"""
        # Update NVIDIA GPUs
        if self.nvidia_available:
            await self._update_nvidia_metrics()
        
        # Update AMD GPUs
        if self.amd_available:
            await self._update_amd_metrics()
        
        # Update Intel GPUs
        if self.intel_available:
            await self._update_intel_metrics()
            
    async def _update_nvidia_metrics(self) -> None:
        """Update NVIDIA GPU metrics"""
        try:
            import pynvml
            
            for device_id, device in self.devices.items():
                if device.vendor != GPUVendor.NVIDIA:
                    continue
                
                # Extract GPU index from device_id
                gpu_index = int(device_id.split('-')[1])
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
                
                # Update memory info
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                device.memory_total = memory_info.total // (1024 * 1024)
                device.memory_free = memory_info.free // (1024 * 1024)
                
                # Update utilization
                device.utilization = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                
                # Update temperature
                device.temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                
                # Update processes
                device.processes = []
                try:
                    processes = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
                    for process in processes:
                        device.processes.append({
                            "pid": process.pid,
                            "memory_used": process.usedGpuMemory // (1024 * 1024)
                        })
                except:
                    pass
                
                device.last_updated = time.time()
                
        except Exception as e:
            # Fallback to nvidia-smi
            try:
                await self._update_nvidia_metrics_smi()
            except Exception as e2:
                self.logger.error(f"Error updating NVIDIA metrics: {e2}")
                
    async def _update_nvidia_metrics_smi(self) -> None:
        """Update NVIDIA GPU metrics using nvidia-smi"""
        try:
            result = subprocess.run([
                "nvidia-smi",
                "--query-gpu=index,memory.total,memory.free,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 5:
                            index = parts[0]
                            device_id = f"nvidia-{index}"
                            
                            if device_id in self.devices:
                                device = self.devices[device_id]
                                device.memory_total = int(parts[1]) if parts[1].isdigit() else device.memory_total
                                device.memory_free = int(parts[2]) if parts[2].isdigit() else device.memory_free
                                device.utilization = float(parts[3]) if parts[3].replace('.', '').isdigit() else device.utilization
                                device.temperature = float(parts[4]) if parts[4].replace('.', '').isdigit() else device.temperature
                                device.last_updated = time.time()
                                
        except Exception as e:
            self.logger.error(f"Error updating NVIDIA metrics with nvidia-smi: {e}")
            
    async def _update_amd_metrics(self) -> None:
        """Update AMD GPU metrics"""
        # Implementation would depend on available ROCm tools
        pass
        
    async def _update_intel_metrics(self) -> None:
        """Update Intel GPU metrics"""
        # Implementation would depend on available Intel GPU tools
        pass
        
    async def _cleanup_expired_allocations(self) -> None:
        """Clean up expired allocations"""
        current_time = time.time()
        expired_allocations = []
        
        for allocation_id, allocation in self.allocations.items():
            if allocation.expires_at and allocation.expires_at <= current_time:
                expired_allocations.append(allocation_id)
        
        for allocation_id in expired_allocations:
            await self.deallocate_gpu(allocation_id)
            self.logger.info(f"Cleaned up expired GPU allocation: {allocation_id}")
            
    def _update_device_stats(self) -> None:
        """Update device statistics"""
        if not self.devices:
            return
        
        self._stats["total_gpus"] = len(self.devices)
        self._stats["available_gpus"] = len([d for d in self.devices.values() if d.state == GPUState.AVAILABLE])
        self._stats["allocated_gpus"] = len([d for d in self.devices.values() if d.state == GPUState.ALLOCATED])
        
        self._stats["total_memory"] = sum(device.memory_total for device in self.devices.values())
        self._stats["allocated_memory"] = sum(device.memory_used for device in self.devices.values())
        
        if self.devices:
            self._stats["average_utilization"] = sum(device.utilization for device in self.devices.values()) / len(self.devices)
            self._stats["average_temperature"] = sum(device.temperature for device in self.devices.values()) / len(self.devices)
        
        self._stats["active_allocations"] = len(self.allocations)
        
    async def get_pool_statistics(self) -> Dict[str, Any]:
        """Get comprehensive GPU pool statistics"""
        vendor_stats = {
            "nvidia": len([d for d in self.devices.values() if d.vendor == GPUVendor.NVIDIA]),
            "amd": len([d for d in self.devices.values() if d.vendor == GPUVendor.AMD]),
            "intel": len([d for d in self.devices.values() if d.vendor == GPUVendor.INTEL])
        }
        
        return {
            **self._stats,
            "vendor_distribution": vendor_stats,
            "vendor_support": {
                "nvidia": self.nvidia_available,
                "amd": self.amd_available,
                "intel": self.intel_available
            }
        }
        
    async def shutdown(self) -> None:
        """Shutdown the GPU pool manager"""
        self.logger.info("Shutting down GPU pool manager")
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Deallocate all active allocations
        allocation_ids = list(self.allocations.keys())
        for allocation_id in allocation_ids:
            await self.deallocate_gpu(allocation_id)
        
        self.logger.info("GPU pool manager shutdown complete")