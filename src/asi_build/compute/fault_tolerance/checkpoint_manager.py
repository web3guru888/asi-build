"""
Checkpoint Manager - Handles job checkpointing and state persistence
"""

import asyncio
import gzip
import hashlib
import json
import logging
import os
import pickle
import shutil
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CheckpointType(Enum):
    FULL = "full"  # Complete job state
    INCREMENTAL = "incremental"  # Changes since last checkpoint
    MEMORY_ONLY = "memory_only"  # In-memory state only
    PERSISTENT = "persistent"  # Stored to persistent storage


class CheckpointStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CORRUPTED = "corrupted"


@dataclass
class CheckpointMetadata:
    """Checkpoint metadata"""

    checkpoint_id: str
    job_id: str
    checkpoint_type: CheckpointType
    status: CheckpointStatus
    created_at: float
    completed_at: Optional[float] = None
    file_path: Optional[str] = None
    size_bytes: int = 0
    checksum: Optional[str] = None
    parent_checkpoint_id: Optional[str] = None  # For incremental checkpoints
    compression_enabled: bool = True
    encryption_enabled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "job_id": self.job_id,
            "checkpoint_type": self.checkpoint_type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "file_path": self.file_path,
            "size_bytes": self.size_bytes,
            "size_mb": self.size_bytes / (1024 * 1024),
            "checksum": self.checksum,
            "parent_checkpoint_id": self.parent_checkpoint_id,
            "compression_enabled": self.compression_enabled,
            "encryption_enabled": self.encryption_enabled,
            "metadata": self.metadata,
        }


@dataclass
class CheckpointPolicy:
    """Checkpoint policy configuration"""

    interval_seconds: float = 300.0  # 5 minutes
    max_checkpoints_per_job: int = 5
    compression_enabled: bool = True
    encryption_enabled: bool = False
    incremental_enabled: bool = True
    automatic_cleanup: bool = True
    retention_days: int = 7
    storage_path: str = "/tmp/checkpoints"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interval_seconds": self.interval_seconds,
            "max_checkpoints_per_job": self.max_checkpoints_per_job,
            "compression_enabled": self.compression_enabled,
            "encryption_enabled": self.encryption_enabled,
            "incremental_enabled": self.incremental_enabled,
            "automatic_cleanup": self.automatic_cleanup,
            "retention_days": self.retention_days,
            "storage_path": self.storage_path,
        }


class CheckpointManager:
    """
    Advanced checkpoint manager with compression, incremental checkpoints,
    and automatic recovery capabilities
    """

    def __init__(self, policy: Optional[CheckpointPolicy] = None):
        self.policy = policy or CheckpointPolicy()
        self.logger = logging.getLogger("checkpoint_manager")

        # Checkpoint storage
        self.checkpoints: Dict[str, CheckpointMetadata] = {}
        self.job_checkpoints: Dict[str, List[str]] = {}  # job_id -> checkpoint_ids
        self.storage_path = Path(self.policy.storage_path)

        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None

        # Statistics
        self._stats = {
            "total_checkpoints": 0,
            "successful_checkpoints": 0,
            "failed_checkpoints": 0,
            "total_size_bytes": 0,
            "average_checkpoint_time": 0.0,
            "compression_ratio": 0.0,
            "active_jobs": 0,
        }

    async def initialize(self) -> None:
        """Initialize the checkpoint manager"""
        self.logger.info("Initializing checkpoint manager")

        # Create storage directory
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Load existing checkpoints
        await self._load_existing_checkpoints()

        # Start cleanup task
        if self.policy.automatic_cleanup:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())

        self.logger.info(
            f"Checkpoint manager initialized with {len(self.checkpoints)} existing checkpoints"
        )

    async def _load_existing_checkpoints(self) -> None:
        """Load existing checkpoint metadata from storage"""
        try:
            metadata_dir = self.storage_path / "metadata"
            if metadata_dir.exists():
                for metadata_file in metadata_dir.glob("*.json"):
                    try:
                        with open(metadata_file, "r") as f:
                            checkpoint_data = json.load(f)

                        checkpoint = CheckpointMetadata(
                            checkpoint_id=checkpoint_data["checkpoint_id"],
                            job_id=checkpoint_data["job_id"],
                            checkpoint_type=CheckpointType(checkpoint_data["checkpoint_type"]),
                            status=CheckpointStatus(checkpoint_data["status"]),
                            created_at=checkpoint_data["created_at"],
                            completed_at=checkpoint_data.get("completed_at"),
                            file_path=checkpoint_data.get("file_path"),
                            size_bytes=checkpoint_data.get("size_bytes", 0),
                            checksum=checkpoint_data.get("checksum"),
                            parent_checkpoint_id=checkpoint_data.get("parent_checkpoint_id"),
                            compression_enabled=checkpoint_data.get("compression_enabled", True),
                            encryption_enabled=checkpoint_data.get("encryption_enabled", False),
                            metadata=checkpoint_data.get("metadata", {}),
                        )

                        self.checkpoints[checkpoint.checkpoint_id] = checkpoint

                        if checkpoint.job_id not in self.job_checkpoints:
                            self.job_checkpoints[checkpoint.job_id] = []
                        self.job_checkpoints[checkpoint.job_id].append(checkpoint.checkpoint_id)

                    except Exception as e:
                        self.logger.error(
                            f"Error loading checkpoint metadata from {metadata_file}: {e}"
                        )

        except Exception as e:
            self.logger.error(f"Error loading existing checkpoints: {e}")

    async def create_checkpoint(
        self,
        job_id: str,
        job_state: Dict[str, Any],
        checkpoint_type: CheckpointType = CheckpointType.FULL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new checkpoint for a job"""
        checkpoint_id = str(uuid.uuid4())
        start_time = time.time()

        self.logger.info(f"Creating checkpoint {checkpoint_id} for job {job_id}")

        try:
            # Create checkpoint metadata
            checkpoint = CheckpointMetadata(
                checkpoint_id=checkpoint_id,
                job_id=job_id,
                checkpoint_type=checkpoint_type,
                status=CheckpointStatus.IN_PROGRESS,
                created_at=start_time,
                compression_enabled=self.policy.compression_enabled,
                encryption_enabled=self.policy.encryption_enabled,
                metadata=metadata or {},
            )

            # Store in memory
            self.checkpoints[checkpoint_id] = checkpoint

            if job_id not in self.job_checkpoints:
                self.job_checkpoints[job_id] = []
            self.job_checkpoints[job_id].append(checkpoint_id)

            # Save checkpoint data
            await self._save_checkpoint_data(checkpoint, job_state)

            # Update checkpoint metadata
            checkpoint.status = CheckpointStatus.COMPLETED
            checkpoint.completed_at = time.time()

            # Save metadata to disk
            await self._save_checkpoint_metadata(checkpoint)

            # Update statistics
            self._stats["total_checkpoints"] += 1
            self._stats["successful_checkpoints"] += 1
            self._stats["total_size_bytes"] += checkpoint.size_bytes

            checkpoint_time = checkpoint.completed_at - checkpoint.created_at
            self._stats["average_checkpoint_time"] = (
                self._stats["average_checkpoint_time"] * (self._stats["successful_checkpoints"] - 1)
                + checkpoint_time
            ) / self._stats["successful_checkpoints"]

            # Clean up old checkpoints if needed
            await self._cleanup_job_checkpoints(job_id)

            self.logger.info(
                f"Checkpoint {checkpoint_id} completed in {checkpoint_time:.2f} seconds"
            )
            return checkpoint_id

        except Exception as e:
            self.logger.error(f"Error creating checkpoint {checkpoint_id}: {e}")

            # Update status to failed
            if checkpoint_id in self.checkpoints:
                self.checkpoints[checkpoint_id].status = CheckpointStatus.FAILED
                await self._save_checkpoint_metadata(self.checkpoints[checkpoint_id])

            self._stats["failed_checkpoints"] += 1
            raise

    async def _save_checkpoint_data(
        self, checkpoint: CheckpointMetadata, job_state: Dict[str, Any]
    ) -> None:
        """Save checkpoint data to storage"""
        # Create checkpoint file path
        checkpoint_dir = self.storage_path / "data" / checkpoint.job_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_file = checkpoint_dir / f"{checkpoint.checkpoint_id}.checkpoint"

        try:
            # Serialize job state
            serialized_data = pickle.dumps(job_state)
            original_size = len(serialized_data)

            # Apply compression if enabled
            if checkpoint.compression_enabled:
                compressed_data = gzip.compress(serialized_data)
                data_to_write = compressed_data

                # Calculate compression ratio
                compression_ratio = (
                    len(compressed_data) / original_size if original_size > 0 else 1.0
                )
                self._stats["compression_ratio"] = (
                    (
                        (
                            self._stats["compression_ratio"]
                            * (self._stats["total_checkpoints"] - 1)
                            + compression_ratio
                        )
                        / self._stats["total_checkpoints"]
                    )
                    if self._stats["total_checkpoints"] > 0
                    else compression_ratio
                )

            else:
                data_to_write = serialized_data

            # Apply encryption if enabled
            if checkpoint.encryption_enabled:
                data_to_write = await self._encrypt_data(data_to_write)

            # Write to file
            with open(checkpoint_file, "wb") as f:
                f.write(data_to_write)

            # Calculate checksum
            checksum = hashlib.sha256(data_to_write).hexdigest()

            # Update checkpoint metadata
            checkpoint.file_path = str(checkpoint_file)
            checkpoint.size_bytes = len(data_to_write)
            checkpoint.checksum = checksum

        except Exception as e:
            self.logger.error(f"Error saving checkpoint data: {e}")
            raise

    async def _save_checkpoint_metadata(self, checkpoint: CheckpointMetadata) -> None:
        """Save checkpoint metadata to disk"""
        try:
            metadata_dir = self.storage_path / "metadata"
            metadata_dir.mkdir(parents=True, exist_ok=True)

            metadata_file = metadata_dir / f"{checkpoint.checkpoint_id}.json"

            with open(metadata_file, "w") as f:
                json.dump(checkpoint.to_dict(), f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving checkpoint metadata: {e}")

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Load job state from a checkpoint"""
        if checkpoint_id not in self.checkpoints:
            self.logger.error(f"Checkpoint {checkpoint_id} not found")
            return None

        checkpoint = self.checkpoints[checkpoint_id]

        if checkpoint.status != CheckpointStatus.COMPLETED:
            self.logger.error(f"Checkpoint {checkpoint_id} is not in completed state")
            return None

        if not checkpoint.file_path or not os.path.exists(checkpoint.file_path):
            self.logger.error(f"Checkpoint file not found: {checkpoint.file_path}")
            checkpoint.status = CheckpointStatus.CORRUPTED
            await self._save_checkpoint_metadata(checkpoint)
            return None

        try:
            self.logger.info(f"Loading checkpoint {checkpoint_id}")

            # Read checkpoint file
            with open(checkpoint.file_path, "rb") as f:
                data = f.read()

            # Verify checksum
            if checkpoint.checksum:
                calculated_checksum = hashlib.sha256(data).hexdigest()
                if calculated_checksum != checkpoint.checksum:
                    self.logger.error(f"Checkpoint {checkpoint_id} checksum mismatch")
                    checkpoint.status = CheckpointStatus.CORRUPTED
                    await self._save_checkpoint_metadata(checkpoint)
                    return None

            # Decrypt if needed
            if checkpoint.encryption_enabled:
                data = await self._decrypt_data(data)

            # Decompress if needed
            if checkpoint.compression_enabled:
                data = gzip.decompress(data)

            # Deserialize job state
            job_state = pickle.loads(data)

            self.logger.info(f"Successfully loaded checkpoint {checkpoint_id}")
            return job_state

        except Exception as e:
            self.logger.error(f"Error loading checkpoint {checkpoint_id}: {e}")
            checkpoint.status = CheckpointStatus.CORRUPTED
            await self._save_checkpoint_metadata(checkpoint)
            return None

    async def save_job_checkpoint(self, job_id: str, job_data: Dict[str, Any]) -> str:
        """Save a checkpoint for a specific job (convenience method)"""
        return await self.create_checkpoint(job_id, job_data)

    async def get_latest_checkpoint(self, job_id: str) -> Optional[CheckpointMetadata]:
        """Get the latest successful checkpoint for a job"""
        if job_id not in self.job_checkpoints:
            return None

        job_checkpoint_ids = self.job_checkpoints[job_id]
        latest_checkpoint = None
        latest_time = 0

        for checkpoint_id in job_checkpoint_ids:
            if checkpoint_id in self.checkpoints:
                checkpoint = self.checkpoints[checkpoint_id]
                if (
                    checkpoint.status == CheckpointStatus.COMPLETED
                    and checkpoint.created_at > latest_time
                ):
                    latest_checkpoint = checkpoint
                    latest_time = checkpoint.created_at

        return latest_checkpoint

    async def list_job_checkpoints(self, job_id: str) -> List[CheckpointMetadata]:
        """List all checkpoints for a job"""
        if job_id not in self.job_checkpoints:
            return []

        checkpoints = []
        for checkpoint_id in self.job_checkpoints[job_id]:
            if checkpoint_id in self.checkpoints:
                checkpoints.append(self.checkpoints[checkpoint_id])

        # Sort by creation time (newest first)
        checkpoints.sort(key=lambda c: c.created_at, reverse=True)
        return checkpoints

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint"""
        if checkpoint_id not in self.checkpoints:
            return False

        checkpoint = self.checkpoints[checkpoint_id]

        try:
            # Delete checkpoint file
            if checkpoint.file_path and os.path.exists(checkpoint.file_path):
                os.remove(checkpoint.file_path)

            # Delete metadata file
            metadata_file = self.storage_path / "metadata" / f"{checkpoint_id}.json"
            if metadata_file.exists():
                metadata_file.unlink()

            # Remove from memory
            del self.checkpoints[checkpoint_id]

            # Remove from job checkpoint list
            if checkpoint.job_id in self.job_checkpoints:
                self.job_checkpoints[checkpoint.job_id] = [
                    cid for cid in self.job_checkpoints[checkpoint.job_id] if cid != checkpoint_id
                ]

                if not self.job_checkpoints[checkpoint.job_id]:
                    del self.job_checkpoints[checkpoint.job_id]

            # Update statistics
            self._stats["total_size_bytes"] -= checkpoint.size_bytes

            self.logger.info(f"Deleted checkpoint {checkpoint_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting checkpoint {checkpoint_id}: {e}")
            return False

    async def _cleanup_job_checkpoints(self, job_id: str) -> None:
        """Clean up old checkpoints for a job based on policy"""
        if job_id not in self.job_checkpoints:
            return

        job_checkpoint_ids = self.job_checkpoints[job_id]

        # Keep only the latest N checkpoints
        if len(job_checkpoint_ids) > self.policy.max_checkpoints_per_job:
            # Sort by creation time
            checkpoints = [
                self.checkpoints[cid] for cid in job_checkpoint_ids if cid in self.checkpoints
            ]
            checkpoints.sort(key=lambda c: c.created_at, reverse=True)

            # Delete old checkpoints
            for checkpoint in checkpoints[self.policy.max_checkpoints_per_job :]:
                await self.delete_checkpoint(checkpoint.checkpoint_id)

    async def _cleanup_loop(self) -> None:
        """Background cleanup task"""
        while True:
            try:
                await self._cleanup_expired_checkpoints()
                await asyncio.sleep(3600)  # Run every hour

            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)

    async def _cleanup_expired_checkpoints(self) -> None:
        """Clean up expired checkpoints based on retention policy"""
        if not self.policy.automatic_cleanup:
            return

        current_time = time.time()
        retention_cutoff = current_time - (self.policy.retention_days * 86400)

        expired_checkpoints = []

        for checkpoint in self.checkpoints.values():
            if checkpoint.created_at < retention_cutoff:
                expired_checkpoints.append(checkpoint.checkpoint_id)

        for checkpoint_id in expired_checkpoints:
            await self.delete_checkpoint(checkpoint_id)

        if expired_checkpoints:
            self.logger.info(f"Cleaned up {len(expired_checkpoints)} expired checkpoints")

    async def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt checkpoint data (placeholder implementation)"""
        # This would use proper encryption like AES
        # For now, just return the data as-is
        return data

    async def _decrypt_data(self, data: bytes) -> bytes:
        """Decrypt checkpoint data (placeholder implementation)"""
        # This would use proper decryption like AES
        # For now, just return the data as-is
        return data

    async def verify_checkpoint_integrity(self, checkpoint_id: str) -> bool:
        """Verify the integrity of a checkpoint"""
        if checkpoint_id not in self.checkpoints:
            return False

        checkpoint = self.checkpoints[checkpoint_id]

        if not checkpoint.file_path or not os.path.exists(checkpoint.file_path):
            return False

        try:
            # Read file and verify checksum
            with open(checkpoint.file_path, "rb") as f:
                data = f.read()

            if checkpoint.checksum:
                calculated_checksum = hashlib.sha256(data).hexdigest()
                return calculated_checksum == checkpoint.checksum

            return True  # No checksum to verify

        except Exception as e:
            self.logger.error(f"Error verifying checkpoint {checkpoint_id}: {e}")
            return False

    async def get_checkpoint_statistics(self) -> Dict[str, Any]:
        """Get checkpoint system statistics"""
        # Update active jobs count
        self._stats["active_jobs"] = len(self.job_checkpoints)

        # Calculate status distribution
        status_counts = {}
        for status in CheckpointStatus:
            status_counts[status.value] = len(
                [c for c in self.checkpoints.values() if c.status == status]
            )

        # Calculate type distribution
        type_counts = {}
        for checkpoint_type in CheckpointType:
            type_counts[checkpoint_type.value] = len(
                [c for c in self.checkpoints.values() if c.checkpoint_type == checkpoint_type]
            )

        return {
            **self._stats,
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "policy": self.policy.to_dict(),
            "storage_path": str(self.storage_path),
        }

    async def export_checkpoint_manifest(self) -> Dict[str, Any]:
        """Export checkpoint manifest for backup/recovery"""
        manifest = {
            "version": "1.0",
            "created_at": time.time(),
            "policy": self.policy.to_dict(),
            "checkpoints": {},
        }

        for checkpoint_id, checkpoint in self.checkpoints.items():
            manifest["checkpoints"][checkpoint_id] = checkpoint.to_dict()

        return manifest

    async def import_checkpoint_manifest(self, manifest: Dict[str, Any]) -> None:
        """Import checkpoint manifest for recovery"""
        try:
            for checkpoint_id, checkpoint_data in manifest["checkpoints"].items():
                if checkpoint_id not in self.checkpoints:
                    checkpoint = CheckpointMetadata(
                        checkpoint_id=checkpoint_data["checkpoint_id"],
                        job_id=checkpoint_data["job_id"],
                        checkpoint_type=CheckpointType(checkpoint_data["checkpoint_type"]),
                        status=CheckpointStatus(checkpoint_data["status"]),
                        created_at=checkpoint_data["created_at"],
                        completed_at=checkpoint_data.get("completed_at"),
                        file_path=checkpoint_data.get("file_path"),
                        size_bytes=checkpoint_data.get("size_bytes", 0),
                        checksum=checkpoint_data.get("checksum"),
                        parent_checkpoint_id=checkpoint_data.get("parent_checkpoint_id"),
                        compression_enabled=checkpoint_data.get("compression_enabled", True),
                        encryption_enabled=checkpoint_data.get("encryption_enabled", False),
                        metadata=checkpoint_data.get("metadata", {}),
                    )

                    self.checkpoints[checkpoint_id] = checkpoint

                    if checkpoint.job_id not in self.job_checkpoints:
                        self.job_checkpoints[checkpoint.job_id] = []
                    self.job_checkpoints[checkpoint.job_id].append(checkpoint_id)

            self.logger.info(f"Imported {len(manifest['checkpoints'])} checkpoints from manifest")

        except Exception as e:
            self.logger.error(f"Error importing checkpoint manifest: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the checkpoint manager"""
        self.logger.info("Shutting down checkpoint manager")

        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Save final metadata for all checkpoints
        for checkpoint in self.checkpoints.values():
            await self._save_checkpoint_metadata(checkpoint)

        self.logger.info("Checkpoint manager shutdown complete")
