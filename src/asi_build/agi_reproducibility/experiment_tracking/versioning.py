"""
Version Manager

Advanced versioning system for AGI experiments with semantic versioning,
branching strategies, and reproducibility tracking.
"""

import asyncio
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import git
from git import GitCommandError, Repo

from ..core.config import PlatformConfig
from ..core.exceptions import *


class VersionType(Enum):
    """Version increment types following semantic versioning."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"
    SNAPSHOT = "snapshot"


@dataclass
class VersionInfo:
    """Version information structure."""

    version: str
    commit_hash: str
    branch: str
    timestamp: datetime
    author: str
    message: str
    changes: List[str]
    experiment_hash: str
    parent_versions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class BranchInfo:
    """Branch information structure."""

    name: str
    base_version: str
    purpose: str
    created_at: datetime
    author: str
    active: bool
    merged_at: Optional[datetime] = None
    merged_into: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        if self.merged_at:
            data["merged_at"] = self.merged_at.isoformat()
        return data


class VersionManager:
    """
    Advanced version management system for AGI experiments.

    Features:
    - Semantic versioning with automatic increment detection
    - Branching strategies for experimental variations
    - Content-based versioning with hash validation
    - Reproducibility tracking across versions
    - Version comparison and diff analysis
    """

    def __init__(self, config: PlatformConfig):
        self.config = config
        self.experiments_dir = Path(config.get_experiment_path(""))
        self.versions_dir = self.experiments_dir / ".versions"
        self.git_repo: Optional[Repo] = None

    async def initialize(self) -> None:
        """Initialize the version manager."""
        # Create versions directory
        self.versions_dir.mkdir(parents=True, exist_ok=True)

        # Initialize or open Git repository
        await self._initialize_git_repo()

        # Setup version tracking files
        await self._setup_version_files()

    async def _initialize_git_repo(self) -> None:
        """Initialize Git repository for version control."""
        git_dir = self.experiments_dir / ".git"

        if not git_dir.exists():
            # Initialize new repository
            self.git_repo = Repo.init(str(self.experiments_dir))

            # Configure repository
            with self.git_repo.config_writer() as git_config:
                git_config.set_value("user", "name", "AGI Version Manager")
                git_config.set_value("user", "email", "versions@agi-reproducibility.ai")
                git_config.set_value("init", "defaultBranch", "main")
                git_config.set_value("core", "autocrlf", "input")
                git_config.set_value("merge", "ours", "union")
        else:
            # Use existing repository
            self.git_repo = Repo(str(self.experiments_dir))

    async def _setup_version_files(self) -> None:
        """Setup version tracking files."""
        # Create version registry
        version_registry = self.versions_dir / "registry.json"
        if not version_registry.exists():
            initial_registry = {
                "experiments": {},
                "global_versions": [],
                "branches": {},
                "tags": {},
            }
            with open(version_registry, "w") as f:
                json.dump(initial_registry, f, indent=2)

        # Create branch tracking file
        branch_file = self.versions_dir / "branches.json"
        if not branch_file.exists():
            initial_branches = {
                "main": {
                    "name": "main",
                    "base_version": "0.0.0",
                    "purpose": "Main development branch",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "author": "system",
                    "active": True,
                }
            }
            with open(branch_file, "w") as f:
                json.dump(initial_branches, f, indent=2)

    async def initialize_experiment_versioning(self, experiment_id: str) -> VersionInfo:
        """Initialize versioning for a new experiment."""
        validate_experiment_id(experiment_id)

        # Create experiment directory
        experiment_dir = self.experiments_dir / experiment_id
        experiment_dir.mkdir(parents=True, exist_ok=True)

        # Create initial version info
        initial_version = "0.1.0"
        experiment_hash = await self._compute_experiment_hash(experiment_id)

        version_info = VersionInfo(
            version=initial_version,
            commit_hash="",
            branch="main",
            timestamp=datetime.now(timezone.utc),
            author="system",
            message="Initialize experiment versioning",
            changes=["Initial experiment creation"],
            experiment_hash=experiment_hash,
            parent_versions=[],
        )

        # Create version file
        version_file = experiment_dir / "version.json"
        with open(version_file, "w") as f:
            json.dump(version_info.to_dict(), f, indent=2)

        # Update registry
        await self._update_version_registry(experiment_id, version_info)

        # Create initial Git commit
        if self.git_repo:
            try:
                self.git_repo.index.add([str(experiment_dir.relative_to(self.experiments_dir))])
                commit = self.git_repo.index.commit(f"Initialize versioning for {experiment_id}")
                version_info.commit_hash = commit.hexsha

                # Update version file with commit hash
                with open(version_file, "w") as f:
                    json.dump(version_info.to_dict(), f, indent=2)
            except GitCommandError as e:
                # Continue without Git commit if it fails
                print(f"Warning: Git commit failed: {e}")

        return version_info

    async def create_version(
        self,
        experiment_id: str,
        version_type: VersionType = VersionType.PATCH,
        message: str = "",
        changes: List[str] = None,
    ) -> VersionInfo:
        """Create a new version for an experiment."""
        current_version = await self.get_latest_version(experiment_id)
        if not current_version:
            raise VersioningError(f"No existing version found for experiment {experiment_id}")

        # Calculate next version number
        next_version = self._increment_version(current_version.version, version_type)

        # Compute experiment hash
        experiment_hash = await self._compute_experiment_hash(experiment_id)

        # Check if content has actually changed
        if experiment_hash == current_version.experiment_hash:
            raise VersioningError(f"No changes detected for experiment {experiment_id}")

        # Create new version info
        version_info = VersionInfo(
            version=next_version,
            commit_hash="",
            branch=current_version.branch,
            timestamp=datetime.now(timezone.utc),
            author="system",  # TODO: Get from context
            message=message or f"Version {next_version}",
            changes=changes or ["Automated version increment"],
            experiment_hash=experiment_hash,
            parent_versions=[current_version.version],
        )

        # Save version file
        experiment_dir = self.experiments_dir / experiment_id
        version_file = experiment_dir / "version.json"
        with open(version_file, "w") as f:
            json.dump(version_info.to_dict(), f, indent=2)

        # Create snapshot of current state
        await self._create_version_snapshot(experiment_id, version_info)

        # Update registry
        await self._update_version_registry(experiment_id, version_info)

        # Create Git commit
        if self.git_repo:
            try:
                self.git_repo.index.add([str(experiment_dir.relative_to(self.experiments_dir))])
                commit_msg = f"[{experiment_id}] {version_info.message}"
                commit = self.git_repo.index.commit(commit_msg)
                version_info.commit_hash = commit.hexsha

                # Update version file with commit hash
                with open(version_file, "w") as f:
                    json.dump(version_info.to_dict(), f, indent=2)

                # Create Git tag for version
                tag_name = f"{experiment_id}-v{next_version}"
                self.git_repo.create_tag(tag_name, message=version_info.message)
            except GitCommandError as e:
                print(f"Warning: Git operations failed: {e}")

        return version_info

    async def get_version(self, experiment_id: str, version: str) -> Optional[VersionInfo]:
        """Get specific version of an experiment."""
        # Try to load from snapshot first
        snapshot_file = self.versions_dir / experiment_id / f"v{version}.json"
        if snapshot_file.exists():
            with open(snapshot_file, "r") as f:
                data = json.load(f)
                data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                return VersionInfo(**data)

        # Fall back to current version if it matches
        current_version = await self.get_latest_version(experiment_id)
        if current_version and current_version.version == version:
            return current_version

        return None

    async def get_latest_version(self, experiment_id: str) -> Optional[VersionInfo]:
        """Get the latest version of an experiment."""
        experiment_dir = self.experiments_dir / experiment_id
        version_file = experiment_dir / "version.json"

        if not version_file.exists():
            return None

        try:
            with open(version_file, "r") as f:
                data = json.load(f)
                data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                return VersionInfo(**data)
        except (json.JSONDecodeError, KeyError) as e:
            raise VersioningError(f"Invalid version file for experiment {experiment_id}: {e}")

    async def get_version_history(self, experiment_id: str) -> List[VersionInfo]:
        """Get complete version history for an experiment."""
        versions = []

        # Get all version snapshots
        experiment_versions_dir = self.versions_dir / experiment_id
        if experiment_versions_dir.exists():
            for version_file in experiment_versions_dir.glob("v*.json"):
                with open(version_file, "r") as f:
                    data = json.load(f)
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                    versions.append(VersionInfo(**data))

        # Add current version
        current_version = await self.get_latest_version(experiment_id)
        if current_version:
            # Check if current version is already in snapshots
            if not any(v.version == current_version.version for v in versions):
                versions.append(current_version)

        # Sort by timestamp
        versions.sort(key=lambda v: v.timestamp)
        return versions

    async def compare_versions(
        self, experiment_id: str, version1: str, version2: str
    ) -> Dict[str, Any]:
        """Compare two versions of an experiment."""
        v1_info = await self.get_version(experiment_id, version1)
        v2_info = await self.get_version(experiment_id, version2)

        if not v1_info:
            raise VersioningError(f"Version {version1} not found for experiment {experiment_id}")
        if not v2_info:
            raise VersioningError(f"Version {version2} not found for experiment {experiment_id}")

        comparison = {
            "experiment_id": experiment_id,
            "version1": v1_info.to_dict(),
            "version2": v2_info.to_dict(),
            "content_changed": v1_info.experiment_hash != v2_info.experiment_hash,
            "time_diff": (v2_info.timestamp - v1_info.timestamp).total_seconds(),
            "changes": {"added": [], "modified": [], "removed": []},
        }

        # Analyze changes using Git diff if available
        if self.git_repo and v1_info.commit_hash and v2_info.commit_hash:
            try:
                diffs = self.git_repo.git.diff(
                    v1_info.commit_hash, v2_info.commit_hash, f"{experiment_id}/", name_only=True
                ).splitlines()

                for diff_file in diffs:
                    if diff_file.startswith(f"{experiment_id}/"):
                        relative_path = diff_file[len(f"{experiment_id}/") :]
                        comparison["changes"]["modified"].append(relative_path)

            except GitCommandError:
                pass  # Continue without detailed diff

        return comparison

    async def create_branch(
        self, experiment_id: str, branch_name: str, base_version: str = None, purpose: str = ""
    ) -> BranchInfo:
        """Create a new branch for experiment development."""
        # Validate branch name
        if not branch_name or not branch_name.replace("-", "").replace("_", "").isalnum():
            raise ValidationError("Invalid branch name")

        # Check if branch already exists
        branches = await self._load_branches()
        branch_key = f"{experiment_id}:{branch_name}"
        if branch_key in branches:
            raise VersioningError(
                f"Branch {branch_name} already exists for experiment {experiment_id}"
            )

        # Get base version
        if base_version:
            base_version_info = await self.get_version(experiment_id, base_version)
            if not base_version_info:
                raise VersioningError(f"Base version {base_version} not found")
        else:
            base_version_info = await self.get_latest_version(experiment_id)
            base_version = base_version_info.version if base_version_info else "0.1.0"

        # Create branch info
        branch_info = BranchInfo(
            name=branch_name,
            base_version=base_version,
            purpose=purpose,
            created_at=datetime.now(timezone.utc),
            author="system",  # TODO: Get from context
            active=True,
        )

        # Save branch info
        branches[branch_key] = branch_info.to_dict()
        await self._save_branches(branches)

        # Create Git branch if repository exists
        if self.git_repo:
            try:
                git_branch_name = f"{experiment_id}-{branch_name}"
                self.git_repo.create_head(git_branch_name)
            except GitCommandError as e:
                print(f"Warning: Failed to create Git branch: {e}")

        return branch_info

    async def merge_branch(
        self, experiment_id: str, source_branch: str, target_branch: str = "main"
    ) -> VersionInfo:
        """Merge a branch back into the target branch."""
        branches = await self._load_branches()
        source_key = f"{experiment_id}:{source_branch}"

        if source_key not in branches:
            raise VersioningError(f"Source branch {source_branch} not found")

        # Get current version from target branch
        current_version = await self.get_latest_version(experiment_id)
        if not current_version:
            raise VersioningError(f"No versions found for experiment {experiment_id}")

        # Create merge version
        merge_version = await self.create_version(
            experiment_id,
            VersionType.MINOR,
            f"Merge branch {source_branch} into {target_branch}",
            [f"Merged changes from {source_branch} branch"],
        )

        # Mark source branch as merged
        branches[source_key]["merged_at"] = datetime.now(timezone.utc).isoformat()
        branches[source_key]["merged_into"] = target_branch
        branches[source_key]["active"] = False
        await self._save_branches(branches)

        # Perform Git merge if available
        if self.git_repo:
            try:
                source_git_branch = f"{experiment_id}-{source_branch}"
                target_git_branch = (
                    f"{experiment_id}-{target_branch}" if target_branch != "main" else "main"
                )

                # Switch to target branch and merge
                self.git_repo.heads[target_git_branch].checkout()
                self.git_repo.git.merge(
                    source_git_branch, m=f"Merge {source_branch} into {target_branch}"
                )

                # Delete the feature branch
                self.git_repo.delete_head(source_git_branch)
            except GitCommandError as e:
                print(f"Warning: Git merge failed: {e}")

        return merge_version

    async def tag_version(
        self, experiment_id: str, version: str, tag_name: str, message: str = ""
    ) -> None:
        """Tag a specific version with a meaningful name."""
        version_info = await self.get_version(experiment_id, version)
        if not version_info:
            raise VersioningError(f"Version {version} not found for experiment {experiment_id}")

        # Update registry with tag info
        registry = await self._load_version_registry()
        if "tags" not in registry:
            registry["tags"] = {}

        tag_key = f"{experiment_id}:{tag_name}"
        registry["tags"][tag_key] = {
            "version": version,
            "message": message,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        await self._save_version_registry(registry)

        # Create Git tag if available
        if self.git_repo and version_info.commit_hash:
            try:
                git_tag_name = f"{experiment_id}-{tag_name}"
                self.git_repo.create_tag(
                    git_tag_name, ref=version_info.commit_hash, message=message
                )
            except GitCommandError as e:
                print(f"Warning: Git tag creation failed: {e}")

    def _increment_version(self, current_version: str, version_type: VersionType) -> str:
        """Increment version number based on type."""
        try:
            parts = current_version.split(".")
            if len(parts) < 3:
                raise ValueError("Invalid version format")

            major, minor, patch = map(int, parts[:3])

            if version_type == VersionType.MAJOR:
                return f"{major + 1}.0.0"
            elif version_type == VersionType.MINOR:
                return f"{major}.{minor + 1}.0"
            elif version_type == VersionType.PATCH:
                return f"{major}.{minor}.{patch + 1}"
            elif version_type == VersionType.PRERELEASE:
                return f"{major}.{minor}.{patch + 1}-alpha"
            elif version_type == VersionType.SNAPSHOT:
                timestamp = int(datetime.now().timestamp())
                return f"{major}.{minor}.{patch + 1}-SNAPSHOT-{timestamp}"
            else:
                return f"{major}.{minor}.{patch + 1}"

        except (ValueError, IndexError):
            raise VersioningError(f"Invalid version format: {current_version}")

    async def _compute_experiment_hash(self, experiment_id: str) -> str:
        """Compute hash of experiment content for change detection."""
        experiment_dir = self.experiments_dir / experiment_id

        if not experiment_dir.exists():
            return hashlib.sha256(b"").hexdigest()

        # Collect all relevant file contents
        content_parts = []

        for file_path in sorted(experiment_dir.rglob("*")):
            if file_path.is_file() and not file_path.name.startswith("."):
                try:
                    with open(file_path, "rb") as f:
                        file_content = f.read()
                    relative_path = file_path.relative_to(experiment_dir)
                    content_parts.append(
                        f"{relative_path}:{hashlib.sha256(file_content).hexdigest()}"
                    )
                except (IOError, OSError):
                    continue  # Skip files that can't be read

        # Compute hash of all content
        combined_content = "\n".join(content_parts)
        return hashlib.sha256(combined_content.encode()).hexdigest()

    async def _create_version_snapshot(self, experiment_id: str, version_info: VersionInfo) -> None:
        """Create a snapshot of the experiment at a specific version."""
        experiment_versions_dir = self.versions_dir / experiment_id
        experiment_versions_dir.mkdir(parents=True, exist_ok=True)

        # Save version info
        snapshot_file = experiment_versions_dir / f"v{version_info.version}.json"
        with open(snapshot_file, "w") as f:
            json.dump(version_info.to_dict(), f, indent=2)

        # Create content snapshot (optional, for critical versions)
        # This would copy the entire experiment directory
        # snapshot_dir = experiment_versions_dir / f"v{version_info.version}"
        # shutil.copytree(self.experiments_dir / experiment_id, snapshot_dir)

    async def _update_version_registry(self, experiment_id: str, version_info: VersionInfo) -> None:
        """Update the version registry with new version info."""
        registry = await self._load_version_registry()

        if experiment_id not in registry["experiments"]:
            registry["experiments"][experiment_id] = []

        # Add version to experiment history
        version_record = {
            "version": version_info.version,
            "timestamp": version_info.timestamp.isoformat(),
            "commit_hash": version_info.commit_hash,
            "experiment_hash": version_info.experiment_hash,
        }
        registry["experiments"][experiment_id].append(version_record)

        # Add to global versions list
        global_version_record = {"experiment_id": experiment_id, **version_record}
        registry["global_versions"].append(global_version_record)

        await self._save_version_registry(registry)

    async def _load_version_registry(self) -> Dict[str, Any]:
        """Load version registry from file."""
        registry_file = self.versions_dir / "registry.json"
        try:
            with open(registry_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"experiments": {}, "global_versions": [], "branches": {}, "tags": {}}

    async def _save_version_registry(self, registry: Dict[str, Any]) -> None:
        """Save version registry to file."""
        registry_file = self.versions_dir / "registry.json"
        with open(registry_file, "w") as f:
            json.dump(registry, f, indent=2)

    async def _load_branches(self) -> Dict[str, Any]:
        """Load branch information from file."""
        branch_file = self.versions_dir / "branches.json"
        try:
            with open(branch_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def _save_branches(self, branches: Dict[str, Any]) -> None:
        """Save branch information to file."""
        branch_file = self.versions_dir / "branches.json"
        with open(branch_file, "w") as f:
            json.dump(branches, f, indent=2)

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on version manager."""
        try:
            # Check versions directory
            versions_accessible = self.versions_dir.exists()

            # Check Git repository
            git_healthy = self.git_repo is not None

            # Check registry file
            registry = await self._load_version_registry()
            registry_healthy = isinstance(registry, dict)

            return {
                "status": "healthy",
                "versions_dir": versions_accessible,
                "git_repo": git_healthy,
                "registry": registry_healthy,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
