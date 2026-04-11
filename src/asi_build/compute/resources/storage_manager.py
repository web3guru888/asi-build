"""
Storage Pool Manager - Manages distributed storage resources and datasets
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import psutil


class StorageType(Enum):
    LOCAL_DISK = "local_disk"
    NETWORK_STORAGE = "network_storage"
    OBJECT_STORAGE = "object_storage"
    DISTRIBUTED_FS = "distributed_fs"
    MEMORY_FS = "memory_fs"
    CACHE_STORAGE = "cache_storage"


class StorageClass(Enum):
    NVME_SSD = "nvme_ssd"
    SATA_SSD = "sata_ssd"
    HDD = "hdd"
    NETWORK = "network"
    MEMORY = "memory"


class StorageState(Enum):
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    FULL = "full"
    MAINTENANCE = "maintenance"
    ERROR = "error"


@dataclass
class StorageDevice:
    """Storage device information"""

    device_id: str
    device_path: str
    mount_point: str
    storage_type: StorageType
    storage_class: StorageClass
    total_bytes: int
    free_bytes: int
    used_bytes: int
    file_system: str = ""
    io_scheduler: str = ""
    read_iops: float = 0.0
    write_iops: float = 0.0
    read_bandwidth_mbps: float = 0.0
    write_bandwidth_mbps: float = 0.0
    latency_ms: float = 0.0
    state: StorageState = StorageState.AVAILABLE
    node_id: str = "local"
    raid_level: Optional[str] = None
    encryption_enabled: bool = False

    @property
    def utilization_percent(self) -> float:
        return (self.used_bytes / self.total_bytes * 100) if self.total_bytes > 0 else 0

    @property
    def total_gb(self) -> float:
        return self.total_bytes / (1024**3)

    @property
    def free_gb(self) -> float:
        return self.free_bytes / (1024**3)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_path": self.device_path,
            "mount_point": self.mount_point,
            "storage_type": self.storage_type.value,
            "storage_class": self.storage_class.value,
            "total_bytes": self.total_bytes,
            "free_bytes": self.free_bytes,
            "used_bytes": self.used_bytes,
            "total_gb": self.total_gb,
            "free_gb": self.free_gb,
            "utilization_percent": self.utilization_percent,
            "file_system": self.file_system,
            "io_scheduler": self.io_scheduler,
            "read_iops": self.read_iops,
            "write_iops": self.write_iops,
            "read_bandwidth_mbps": self.read_bandwidth_mbps,
            "write_bandwidth_mbps": self.write_bandwidth_mbps,
            "latency_ms": self.latency_ms,
            "state": self.state.value,
            "node_id": self.node_id,
            "raid_level": self.raid_level,
            "encryption_enabled": self.encryption_enabled,
        }


@dataclass
class DatasetInfo:
    """Dataset information and metadata"""

    dataset_id: str
    name: str
    path: str
    size_bytes: int
    file_count: int
    storage_devices: List[str] = field(default_factory=list)
    replication_factor: int = 1
    access_pattern: str = "random"  # random, sequential, mixed
    compression_enabled: bool = False
    compression_ratio: float = 1.0
    checksum: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "size_gb": self.size_bytes / (1024**3),
            "file_count": self.file_count,
            "storage_devices": self.storage_devices,
            "replication_factor": self.replication_factor,
            "access_pattern": self.access_pattern,
            "compression_enabled": self.compression_enabled,
            "compression_ratio": self.compression_ratio,
            "checksum": self.checksum,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "metadata": self.metadata,
        }


@dataclass
class StorageAllocation:
    """Storage allocation tracking"""

    allocation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""
    user_id: str = ""
    storage_type: StorageType = StorageType.LOCAL_DISK
    requested_bytes: int = 0
    allocated_bytes: int = 0
    device_ids: List[str] = field(default_factory=list)
    mount_paths: List[str] = field(default_factory=list)
    access_mode: str = "rw"  # ro, rw, rwx
    io_priority: int = 4  # 0-7 scale (4 = normal)
    bandwidth_limit_mbps: Optional[float] = None
    iops_limit: Optional[int] = None
    allocated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allocation_id": self.allocation_id,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "storage_type": self.storage_type.value,
            "requested_bytes": self.requested_bytes,
            "allocated_bytes": self.allocated_bytes,
            "requested_gb": self.requested_bytes / (1024**3),
            "allocated_gb": self.allocated_bytes / (1024**3),
            "device_ids": self.device_ids,
            "mount_paths": self.mount_paths,
            "access_mode": self.access_mode,
            "io_priority": self.io_priority,
            "bandwidth_limit_mbps": self.bandwidth_limit_mbps,
            "iops_limit": self.iops_limit,
            "allocated_at": self.allocated_at,
            "expires_at": self.expires_at,
        }


class StoragePoolManager:
    """
    Comprehensive storage pool manager supporting various storage types
    and distributed datasets
    """

    def __init__(self):
        self.logger = logging.getLogger("storage_pool_manager")

        # Storage devices and allocations
        self.devices: Dict[str, StorageDevice] = {}
        self.allocations: Dict[str, StorageAllocation] = {}

        # Dataset management
        self.datasets: Dict[str, DatasetInfo] = {}

        # Storage tiers for automatic data placement
        self.storage_tiers = {
            "hot": [StorageClass.NVME_SSD],
            "warm": [StorageClass.SATA_SSD],
            "cold": [StorageClass.HDD],
            "archive": [StorageClass.NETWORK],
        }

        # Monitoring
        self.monitoring_interval = 30.0  # 30 seconds
        self.monitoring_task: Optional[asyncio.Task] = None

        # Caching
        self.cache_enabled = True
        self.cache_devices: Set[str] = set()

        # Statistics
        self._stats = {
            "total_storage_bytes": 0,
            "available_storage_bytes": 0,
            "allocated_storage_bytes": 0,
            "device_count": 0,
            "nvme_devices": 0,
            "ssd_devices": 0,
            "hdd_devices": 0,
            "network_devices": 0,
            "total_datasets": 0,
            "total_allocations": 0,
            "active_allocations": 0,
            "average_utilization": 0.0,
            "total_iops": 0.0,
            "total_bandwidth_mbps": 0.0,
        }

    async def initialize(self) -> None:
        """Initialize the storage pool manager"""
        self.logger.info("Initializing storage pool manager")

        # Discover storage devices
        await self._discover_storage_devices()

        # Initialize I/O monitoring
        await self._initialize_io_monitoring()

        # Start monitoring loop
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        total_gb = self._stats["total_storage_bytes"] / (1024**3)
        self.logger.info(
            f"Storage pool initialized with {total_gb:.1f} GB across {self._stats['device_count']} devices"
        )

    async def _discover_storage_devices(self) -> None:
        """Discover available storage devices"""
        try:
            # Get disk partitions
            partitions = psutil.disk_partitions()

            for partition in partitions:
                try:
                    # Get disk usage
                    usage = psutil.disk_usage(partition.mountpoint)

                    # Determine storage class from device path
                    storage_class = await self._determine_storage_class(partition.device)

                    device = StorageDevice(
                        device_id=f"disk_{len(self.devices)}",
                        device_path=partition.device,
                        mount_point=partition.mountpoint,
                        storage_type=StorageType.LOCAL_DISK,
                        storage_class=storage_class,
                        total_bytes=usage.total,
                        free_bytes=usage.free,
                        used_bytes=usage.used,
                        file_system=partition.fstype,
                    )

                    # Get additional device information
                    await self._enrich_device_info(device)

                    self.devices[device.device_id] = device

                    self.logger.info(
                        f"Discovered storage device: {device.device_path} "
                        f"({device.total_gb:.1f} GB, {device.storage_class.value})"
                    )

                except (PermissionError, OSError) as e:
                    self.logger.warning(f"Could not access partition {partition.mountpoint}: {e}")
                    continue

            # Update statistics
            self._update_device_stats()

        except Exception as e:
            self.logger.error(f"Error discovering storage devices: {e}")

    async def _determine_storage_class(self, device_path: str) -> StorageClass:
        """Determine storage class from device path"""
        try:
            # Check if it's an NVMe device
            if "nvme" in device_path:
                return StorageClass.NVME_SSD

            # Try to get device information from /sys/block/
            device_name = os.path.basename(device_path).rstrip("0123456789")
            sys_block_path = f"/sys/block/{device_name}"

            if os.path.exists(sys_block_path):
                # Check if it's an SSD
                rotational_path = f"{sys_block_path}/queue/rotational"
                if os.path.exists(rotational_path):
                    with open(rotational_path, "r") as f:
                        rotational = f.read().strip()
                        if rotational == "0":
                            return StorageClass.SATA_SSD
                        else:
                            return StorageClass.HDD

            # Default classification based on device name patterns
            if any(pattern in device_path for pattern in ["ssd", "nvme"]):
                return StorageClass.SATA_SSD
            elif any(pattern in device_path for pattern in ["nfs", "cifs", "fuse"]):
                return StorageClass.NETWORK
            else:
                return StorageClass.HDD

        except Exception as e:
            self.logger.error(f"Error determining storage class for {device_path}: {e}")
            return StorageClass.HDD

    async def _enrich_device_info(self, device: StorageDevice) -> None:
        """Enrich device information with additional details"""
        try:
            device_name = os.path.basename(device.device_path).rstrip("0123456789")

            # Get I/O scheduler
            scheduler_path = f"/sys/block/{device_name}/queue/scheduler"
            if os.path.exists(scheduler_path):
                with open(scheduler_path, "r") as f:
                    scheduler_line = f.read().strip()
                    # Extract current scheduler (marked with brackets)
                    import re

                    match = re.search(r"\[([^\]]+)\]", scheduler_line)
                    if match:
                        device.io_scheduler = match.group(1)

            # Check for RAID
            if os.path.exists("/proc/mdstat"):
                with open("/proc/mdstat", "r") as f:
                    mdstat_content = f.read()
                    if device_name in mdstat_content:
                        # This is a simplified RAID detection
                        if "raid1" in mdstat_content:
                            device.raid_level = "raid1"
                        elif "raid5" in mdstat_content:
                            device.raid_level = "raid5"
                        elif "raid6" in mdstat_content:
                            device.raid_level = "raid6"
                        elif "raid0" in mdstat_content:
                            device.raid_level = "raid0"

            # Check for encryption (LUKS)
            try:
                result = subprocess.run(
                    ["cryptsetup", "status", device.device_path],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and "active" in result.stdout:
                    device.encryption_enabled = True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        except Exception as e:
            self.logger.error(f"Error enriching device info for {device.device_path}: {e}")

    async def _initialize_io_monitoring(self) -> None:
        """Initialize I/O performance monitoring"""
        try:
            # Start baseline I/O counters
            psutil.disk_io_counters(perdisk=True)
            self.logger.info("I/O monitoring initialized")

        except Exception as e:
            self.logger.error(f"Error initializing I/O monitoring: {e}")

    async def allocate_storage(
        self,
        job_id: str,
        user_id: str,
        size_bytes: int,
        storage_type: StorageType = StorageType.LOCAL_DISK,
        storage_class: Optional[StorageClass] = None,
        access_mode: str = "rw",
        io_priority: int = 4,
        bandwidth_limit_mbps: Optional[float] = None,
        iops_limit: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> Optional[StorageAllocation]:
        """Allocate storage resources"""
        self.logger.info(f"Allocating {size_bytes / (1024**3):.2f} GB storage for job {job_id}")

        # Find suitable storage devices
        suitable_devices = await self._find_suitable_devices(
            size_bytes, storage_type, storage_class
        )

        if not suitable_devices:
            self.logger.warning(f"No suitable storage devices found for {size_bytes} bytes")
            return None

        # Select devices based on available space
        selected_devices = []
        remaining_bytes = size_bytes

        for device in suitable_devices:
            if remaining_bytes <= 0:
                break

            available_bytes = min(device.free_bytes, remaining_bytes)
            if available_bytes > 0:
                selected_devices.append(device)
                remaining_bytes -= available_bytes

        if remaining_bytes > 0:
            self.logger.warning(
                f"Insufficient storage: need {size_bytes}, can provide {size_bytes - remaining_bytes}"
            )
            return None

        # Create allocation
        allocation = StorageAllocation(
            job_id=job_id,
            user_id=user_id,
            storage_type=storage_type,
            requested_bytes=size_bytes,
            allocated_bytes=size_bytes - remaining_bytes,
            device_ids=[device.device_id for device in selected_devices],
            mount_paths=[device.mount_point for device in selected_devices],
            access_mode=access_mode,
            io_priority=io_priority,
            bandwidth_limit_mbps=bandwidth_limit_mbps,
            iops_limit=iops_limit,
        )

        if duration:
            allocation.expires_at = time.time() + duration

        # Update device usage
        allocated_per_device = size_bytes // len(selected_devices)
        for device in selected_devices:
            device.free_bytes -= allocated_per_device
            device.used_bytes += allocated_per_device

            if device.free_bytes < (device.total_bytes * 0.05):  # Less than 5% free
                device.state = StorageState.FULL

        self.allocations[allocation.allocation_id] = allocation
        self._stats["total_allocations"] += 1
        self._stats["active_allocations"] += 1
        self._stats["allocated_storage_bytes"] += allocation.allocated_bytes

        self.logger.info(
            f"Allocated {allocation.allocated_bytes / (1024**3):.2f} GB to job {job_id}"
        )
        return allocation

    async def _find_suitable_devices(
        self, size_bytes: int, storage_type: StorageType, storage_class: Optional[StorageClass]
    ) -> List[StorageDevice]:
        """Find suitable storage devices for allocation"""
        suitable_devices = []

        for device in self.devices.values():
            # Check storage type
            if device.storage_type != storage_type:
                continue

            # Check storage class if specified
            if storage_class and device.storage_class != storage_class:
                continue

            # Check availability
            if device.state not in [StorageState.AVAILABLE, StorageState.ALLOCATED]:
                continue

            # Check free space
            if device.free_bytes > 0:
                suitable_devices.append(device)

        # Sort by preference: storage class performance, free space, utilization
        class_priority = {
            StorageClass.NVME_SSD: 4,
            StorageClass.SATA_SSD: 3,
            StorageClass.HDD: 2,
            StorageClass.NETWORK: 1,
            StorageClass.MEMORY: 5,
        }

        suitable_devices.sort(
            key=lambda d: (
                -class_priority.get(d.storage_class, 0),
                -d.free_bytes,
                d.utilization_percent,
            )
        )

        return suitable_devices

    async def deallocate_storage(self, allocation_id: str) -> bool:
        """Deallocate storage resources"""
        if allocation_id not in self.allocations:
            self.logger.warning(f"Allocation {allocation_id} not found")
            return False

        allocation = self.allocations.pop(allocation_id)

        # Free space on devices
        freed_per_device = allocation.allocated_bytes // len(allocation.device_ids)

        for device_id in allocation.device_ids:
            if device_id in self.devices:
                device = self.devices[device_id]
                device.free_bytes += freed_per_device
                device.used_bytes -= freed_per_device

                # Ensure values don't go negative
                device.free_bytes = min(device.free_bytes, device.total_bytes)
                device.used_bytes = max(0, device.total_bytes - device.free_bytes)

                # Update device state
                if device.state == StorageState.FULL and device.free_bytes > 0:
                    device.state = StorageState.AVAILABLE

        self._stats["active_allocations"] -= 1
        self._stats["allocated_storage_bytes"] -= allocation.allocated_bytes

        self.logger.info(f"Deallocated {allocation.allocated_bytes / (1024**3):.2f} GB storage")
        return True

    async def create_dataset(
        self,
        name: str,
        path: str,
        replication_factor: int = 1,
        compression_enabled: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new dataset"""
        dataset_id = str(uuid.uuid4())

        # Calculate dataset size and file count
        size_bytes, file_count = await self._calculate_dataset_size(path)

        # Determine which storage devices contain the dataset
        storage_devices = await self._find_dataset_devices(path)

        dataset = DatasetInfo(
            dataset_id=dataset_id,
            name=name,
            path=path,
            size_bytes=size_bytes,
            file_count=file_count,
            storage_devices=storage_devices,
            replication_factor=replication_factor,
            compression_enabled=compression_enabled,
            metadata=metadata or {},
        )

        self.datasets[dataset_id] = dataset
        self._stats["total_datasets"] += 1

        self.logger.info(
            f"Created dataset {name}: {size_bytes / (1024**3):.2f} GB, {file_count} files"
        )
        return dataset_id

    async def _calculate_dataset_size(self, path: str) -> Tuple[int, int]:
        """Calculate total size and file count for a dataset path"""
        try:
            if os.path.exists(path):
                if os.path.isfile(path):
                    return os.path.getsize(path), 1
                elif os.path.isdir(path):
                    total_size = 0
                    file_count = 0

                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                total_size += os.path.getsize(file_path)
                                file_count += 1
                            except (OSError, IOError):
                                continue

                    return total_size, file_count

            return 0, 0

        except Exception as e:
            self.logger.error(f"Error calculating dataset size for {path}: {e}")
            return 0, 0

    async def _find_dataset_devices(self, path: str) -> List[str]:
        """Find which storage devices contain the dataset"""
        dataset_devices = []

        try:
            # Find the mount point that contains this path
            path_obj = Path(path).resolve()

            for device in self.devices.values():
                mount_path = Path(device.mount_point).resolve()

                try:
                    # Check if the dataset path is under this mount point
                    path_obj.relative_to(mount_path)
                    dataset_devices.append(device.device_id)
                except ValueError:
                    # Path is not under this mount point
                    continue

        except Exception as e:
            self.logger.error(f"Error finding dataset devices for {path}: {e}")

        return dataset_devices

    async def move_dataset(
        self, dataset_id: str, target_storage_class: StorageClass, preserve_copies: bool = True
    ) -> bool:
        """Move dataset to different storage tier"""
        if dataset_id not in self.datasets:
            self.logger.error(f"Dataset {dataset_id} not found")
            return False

        dataset = self.datasets[dataset_id]

        # Find target devices
        target_devices = [
            device
            for device in self.devices.values()
            if device.storage_class == target_storage_class
            and device.free_bytes > dataset.size_bytes
        ]

        if not target_devices:
            self.logger.error(f"No suitable {target_storage_class.value} devices with enough space")
            return False

        target_device = target_devices[0]  # Select first suitable device

        # Create new path on target device
        dataset_name = os.path.basename(dataset.path)
        new_path = os.path.join(target_device.mount_point, "datasets", dataset_name)

        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(new_path), exist_ok=True)

            # Move or copy dataset
            if preserve_copies:
                await self._copy_dataset(dataset.path, new_path)
            else:
                await self._move_dataset(dataset.path, new_path)

            # Update dataset information
            old_path = dataset.path
            dataset.path = new_path
            dataset.storage_devices = [target_device.device_id]

            self.logger.info(f"Moved dataset {dataset.name} from {old_path} to {new_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error moving dataset {dataset_id}: {e}")
            return False

    async def _copy_dataset(self, source: str, destination: str) -> None:
        """Copy dataset to new location"""
        if os.path.isfile(source):
            shutil.copy2(source, destination)
        elif os.path.isdir(source):
            shutil.copytree(source, destination)

    async def _move_dataset(self, source: str, destination: str) -> None:
        """Move dataset to new location"""
        shutil.move(source, destination)

    async def get_storage_status(self) -> Dict[str, Any]:
        """Get comprehensive storage status"""
        return {
            "devices": {device_id: device.to_dict() for device_id, device in self.devices.items()},
            "allocations": {
                allocation_id: allocation.to_dict()
                for allocation_id, allocation in self.allocations.items()
            },
            "datasets": {
                dataset_id: dataset.to_dict() for dataset_id, dataset in self.datasets.items()
            },
            "statistics": self._stats.copy(),
        }

    async def get_utilization(self) -> Dict[str, float]:
        """Get storage utilization metrics"""
        if not self.devices:
            return {}

        total_storage = sum(device.total_bytes for device in self.devices.values())
        used_storage = sum(device.used_bytes for device in self.devices.values())
        free_storage = sum(device.free_bytes for device in self.devices.values())

        utilization = (used_storage / total_storage * 100) if total_storage > 0 else 0

        # Calculate I/O metrics
        total_read_iops = sum(device.read_iops for device in self.devices.values())
        total_write_iops = sum(device.write_iops for device in self.devices.values())
        total_read_bw = sum(device.read_bandwidth_mbps for device in self.devices.values())
        total_write_bw = sum(device.write_bandwidth_mbps for device in self.devices.values())

        return {
            "storage_total_bytes": total_storage,
            "storage_used_bytes": used_storage,
            "storage_free_bytes": free_storage,
            "storage_utilization": utilization,
            "storage_total_gb": total_storage / (1024**3),
            "storage_used_gb": used_storage / (1024**3),
            "storage_free_gb": free_storage / (1024**3),
            "device_count": len(self.devices),
            "active_allocations": self._stats["active_allocations"],
            "total_datasets": self._stats["total_datasets"],
            "read_iops_total": total_read_iops,
            "write_iops_total": total_write_iops,
            "read_bandwidth_mbps_total": total_read_bw,
            "write_bandwidth_mbps_total": total_write_bw,
        }

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop for storage metrics"""
        while True:
            try:
                await self._update_storage_metrics()
                await self._update_io_metrics()
                await self._cleanup_expired_allocations()
                self._update_device_stats()

                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.error(f"Error in storage monitoring loop: {e}")
                await asyncio.sleep(60.0)

    async def _update_storage_metrics(self) -> None:
        """Update storage usage metrics"""
        try:
            partitions = psutil.disk_partitions()

            for device in self.devices.values():
                # Find matching partition
                for partition in partitions:
                    if partition.device == device.device_path:
                        try:
                            usage = psutil.disk_usage(partition.mountpoint)
                            device.total_bytes = usage.total
                            device.free_bytes = usage.free
                            device.used_bytes = usage.used

                            # Update state based on usage
                            if device.free_bytes < (device.total_bytes * 0.05):
                                device.state = StorageState.FULL
                            elif device.state == StorageState.FULL and device.free_bytes > (
                                device.total_bytes * 0.10
                            ):
                                device.state = StorageState.AVAILABLE

                        except (OSError, IOError):
                            device.state = StorageState.ERROR
                        break

        except Exception as e:
            self.logger.error(f"Error updating storage metrics: {e}")

    async def _update_io_metrics(self) -> None:
        """Update I/O performance metrics"""
        try:
            # Get current I/O counters
            io_counters = psutil.disk_io_counters(perdisk=True)

            if not hasattr(self, "_previous_io_counters"):
                self._previous_io_counters = io_counters
                self._previous_io_time = time.time()
                return

            current_time = time.time()
            time_delta = current_time - self._previous_io_time

            if time_delta <= 0:
                return

            for device in self.devices.values():
                device_name = os.path.basename(device.device_path).rstrip("0123456789")

                if device_name in io_counters and device_name in self._previous_io_counters:
                    current = io_counters[device_name]
                    previous = self._previous_io_counters[device_name]

                    # Calculate IOPS
                    read_ops_delta = current.read_count - previous.read_count
                    write_ops_delta = current.write_count - previous.write_count

                    device.read_iops = read_ops_delta / time_delta
                    device.write_iops = write_ops_delta / time_delta

                    # Calculate bandwidth (MB/s)
                    read_bytes_delta = current.read_bytes - previous.read_bytes
                    write_bytes_delta = current.write_bytes - previous.write_bytes

                    device.read_bandwidth_mbps = (read_bytes_delta / (1024 * 1024)) / time_delta
                    device.write_bandwidth_mbps = (write_bytes_delta / (1024 * 1024)) / time_delta

                    # Estimate latency (simplified)
                    read_time_delta = current.read_time - previous.read_time
                    write_time_delta = current.write_time - previous.write_time
                    total_ops = read_ops_delta + write_ops_delta

                    if total_ops > 0:
                        device.latency_ms = (read_time_delta + write_time_delta) / total_ops

            self._previous_io_counters = io_counters
            self._previous_io_time = current_time

        except Exception as e:
            self.logger.error(f"Error updating I/O metrics: {e}")

    async def _cleanup_expired_allocations(self) -> None:
        """Clean up expired storage allocations"""
        current_time = time.time()
        expired_allocations = []

        for allocation_id, allocation in self.allocations.items():
            if allocation.expires_at and allocation.expires_at <= current_time:
                expired_allocations.append(allocation_id)

        for allocation_id in expired_allocations:
            await self.deallocate_storage(allocation_id)
            self.logger.info(f"Cleaned up expired storage allocation: {allocation_id}")

    def _update_device_stats(self) -> None:
        """Update device statistics"""
        self._stats["device_count"] = len(self.devices)
        self._stats["total_storage_bytes"] = sum(
            device.total_bytes for device in self.devices.values()
        )
        self._stats["available_storage_bytes"] = sum(
            device.free_bytes for device in self.devices.values()
        )

        # Count devices by storage class
        self._stats["nvme_devices"] = len(
            [d for d in self.devices.values() if d.storage_class == StorageClass.NVME_SSD]
        )
        self._stats["ssd_devices"] = len(
            [d for d in self.devices.values() if d.storage_class == StorageClass.SATA_SSD]
        )
        self._stats["hdd_devices"] = len(
            [d for d in self.devices.values() if d.storage_class == StorageClass.HDD]
        )
        self._stats["network_devices"] = len(
            [d for d in self.devices.values() if d.storage_class == StorageClass.NETWORK]
        )

        # Calculate average utilization
        if self.devices:
            self._stats["average_utilization"] = sum(
                device.utilization_percent for device in self.devices.values()
            ) / len(self.devices)

            # Calculate total I/O metrics
            self._stats["total_iops"] = sum(
                device.read_iops + device.write_iops for device in self.devices.values()
            )
            self._stats["total_bandwidth_mbps"] = sum(
                device.read_bandwidth_mbps + device.write_bandwidth_mbps
                for device in self.devices.values()
            )

        self._stats["active_allocations"] = len(self.allocations)

    async def get_pool_statistics(self) -> Dict[str, Any]:
        """Get comprehensive storage pool statistics"""
        storage_class_distribution = {}
        for storage_class in StorageClass:
            devices = [d for d in self.devices.values() if d.storage_class == storage_class]
            if devices:
                storage_class_distribution[storage_class.value] = {
                    "count": len(devices),
                    "total_bytes": sum(d.total_bytes for d in devices),
                    "free_bytes": sum(d.free_bytes for d in devices),
                    "average_utilization": sum(d.utilization_percent for d in devices)
                    / len(devices),
                }

        return {
            **self._stats,
            "storage_class_distribution": storage_class_distribution,
            "storage_tiers": self.storage_tiers,
        }

    async def shutdown(self) -> None:
        """Shutdown the storage pool manager"""
        self.logger.info("Shutting down storage pool manager")

        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        # Deallocate all active allocations
        allocation_ids = list(self.allocations.keys())
        for allocation_id in allocation_ids:
            await self.deallocate_storage(allocation_id)

        self.logger.info("Storage pool manager shutdown complete")
