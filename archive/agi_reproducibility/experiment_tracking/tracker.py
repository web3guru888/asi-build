"""
Experiment Tracker

Comprehensive experiment tracking system that records all aspects of AGI experiments
for reproducibility, comparison, and analysis.
"""

import asyncio
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import aiosqlite
import git
import os

from ..core.config import PlatformConfig
from ..core.exceptions import *


class ExperimentStatus(Enum):
    """Experiment status enumeration."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    ARCHIVED = "archived"


@dataclass
class ExperimentMetadata:
    """Experiment metadata structure."""
    id: str
    title: str
    description: str
    author: str
    email: str
    tags: List[str]
    agi_framework: str  # hyperon, opencog, etc.
    research_area: str  # symbolic_reasoning, consciousness, etc.
    hypothesis: str
    expected_outcomes: List[str]
    ethical_considerations: str
    computational_requirements: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentRecord:
    """Complete experiment record."""
    metadata: ExperimentMetadata
    status: ExperimentStatus
    created_at: datetime
    updated_at: datetime
    version: str
    git_commit: Optional[str]
    environment_snapshot: Dict[str, Any]
    code_hash: str
    data_hash: str
    config_hash: str
    parameters: Dict[str, Any]
    results: Optional[Dict[str, Any]]
    benchmarks: Optional[Dict[str, Any]]
    verification_results: Optional[Dict[str, Any]]
    peer_reviews: List[Dict[str, Any]]
    citations: List[str]
    reproductions: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        record_dict = asdict(self)
        # Convert datetime objects to ISO strings
        record_dict['created_at'] = self.created_at.isoformat()
        record_dict['updated_at'] = self.updated_at.isoformat()
        record_dict['status'] = self.status.value
        return record_dict


class ExperimentTracker:
    """
    Main experiment tracking system.
    
    Provides comprehensive tracking of AGI experiments including:
    - Metadata management
    - Version control integration  
    - Environment snapshots
    - Result storage
    - Reproducibility tracking
    """
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.db_path = os.path.join(config.base_path, "experiments.db")
        self.experiments_dir = Path(config.get_experiment_path(""))
        self.git_repo = None
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def initialize(self) -> None:
        """Initialize the experiment tracker."""
        # Create experiments directory
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        await self._initialize_database()
        
        # Initialize Git repository for experiment tracking
        await self._initialize_git_repo()
    
    async def _initialize_database(self) -> None:
        """Initialize SQLite database for experiments."""
        self._connection = await aiosqlite.connect(self.db_path)
        
        # Create experiments table
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                author TEXT NOT NULL,
                email TEXT NOT NULL,
                tags TEXT,  -- JSON array
                agi_framework TEXT,
                research_area TEXT,
                hypothesis TEXT,
                expected_outcomes TEXT,  -- JSON array
                ethical_considerations TEXT,
                computational_requirements TEXT,  -- JSON object
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                version TEXT NOT NULL,
                git_commit TEXT,
                environment_snapshot TEXT,  -- JSON object
                code_hash TEXT NOT NULL,
                data_hash TEXT,
                config_hash TEXT,
                parameters TEXT,  -- JSON object
                results TEXT,  -- JSON object
                benchmarks TEXT,  -- JSON object
                verification_results TEXT,  -- JSON object
                peer_reviews TEXT,  -- JSON array
                citations TEXT,  -- JSON array
                reproductions TEXT  -- JSON array
            )
        """)
        
        # Create indices for performance
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_experiments_author ON experiments(author)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_experiments_framework ON experiments(agi_framework)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at)
        """)
        
        await self._connection.commit()
    
    async def _initialize_git_repo(self) -> None:
        """Initialize Git repository for version control."""
        git_dir = self.experiments_dir / ".git"
        
        if not git_dir.exists():
            # Initialize new repository
            self.git_repo = git.Repo.init(str(self.experiments_dir))
            
            # Configure repository
            with self.git_repo.config_writer() as git_config:
                git_config.set_value("user", "name", "AGI Reproducibility Platform")
                git_config.set_value("user", "email", "agi-platform@reproducibility.ai")
                git_config.set_value("init", "defaultBranch", "main")
            
            # Create initial commit
            gitignore_path = self.experiments_dir / ".gitignore"
            with open(gitignore_path, 'w') as f:
                f.write("*.tmp\n*.log\n__pycache__/\n.DS_Store\n")
            
            self.git_repo.index.add([".gitignore"])
            self.git_repo.index.commit("Initial commit - AGI Reproducibility Platform")
        else:
            # Use existing repository
            self.git_repo = git.Repo(str(self.experiments_dir))
    
    async def create_experiment(self, experiment_id: str, 
                              metadata: Dict[str, Any]) -> ExperimentRecord:
        """Create a new experiment record."""
        validate_experiment_id(experiment_id)
        
        # Check if experiment already exists
        if await self.experiment_exists(experiment_id):
            raise ExperimentAlreadyExistsError(f"Experiment {experiment_id} already exists")
        
        # Create experiment metadata
        experiment_metadata = ExperimentMetadata(
            id=experiment_id,
            title=metadata.get('title', f'Experiment {experiment_id}'),
            description=metadata.get('description', ''),
            author=metadata.get('author', 'Unknown'),
            email=metadata.get('email', 'unknown@example.com'),
            tags=metadata.get('tags', []),
            agi_framework=metadata.get('agi_framework', 'unknown'),
            research_area=metadata.get('research_area', 'general'),
            hypothesis=metadata.get('hypothesis', ''),
            expected_outcomes=metadata.get('expected_outcomes', []),
            ethical_considerations=metadata.get('ethical_considerations', ''),
            computational_requirements=metadata.get('computational_requirements', {})
        )
        
        # Create experiment directory
        experiment_dir = self.experiments_dir / experiment_id
        experiment_dir.mkdir(parents=True, exist_ok=True)
        
        # Create initial hashes (will be updated when content is added)
        code_hash = self._compute_hash("")
        data_hash = self._compute_hash("")
        config_hash = self._compute_hash("")
        
        # Create experiment record
        now = datetime.now(timezone.utc)
        experiment_record = ExperimentRecord(
            metadata=experiment_metadata,
            status=ExperimentStatus.CREATED,
            created_at=now,
            updated_at=now,
            version="0.1.0",
            git_commit=None,
            environment_snapshot={},
            code_hash=code_hash,
            data_hash=data_hash,
            config_hash=config_hash,
            parameters=metadata.get('parameters', {}),
            results=None,
            benchmarks=None,
            verification_results=None,
            peer_reviews=[],
            citations=metadata.get('citations', []),
            reproductions=[]
        )
        
        # Store in database
        await self._store_experiment_record(experiment_record)
        
        # Create initial Git commit for experiment
        await self._commit_experiment_changes(experiment_id, "Create experiment")
        
        return experiment_record
    
    async def get_experiment(self, experiment_id: str) -> Optional[ExperimentRecord]:
        """Get experiment record by ID."""
        async with self._connection.execute(
            "SELECT * FROM experiments WHERE id = ?", (experiment_id,)
        ) as cursor:
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_experiment_record(row)
    
    async def experiment_exists(self, experiment_id: str) -> bool:
        """Check if experiment exists."""
        async with self._connection.execute(
            "SELECT COUNT(*) FROM experiments WHERE id = ?", (experiment_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] > 0
    
    async def update_experiment_status(self, experiment_id: str, 
                                     status: str) -> None:
        """Update experiment status."""
        try:
            experiment_status = ExperimentStatus(status)
        except ValueError:
            raise ValidationError(f"Invalid experiment status: {status}")
        
        now = datetime.now(timezone.utc).isoformat()
        
        await self._connection.execute("""
            UPDATE experiments 
            SET status = ?, updated_at = ?
            WHERE id = ?
        """, (status, now, experiment_id))
        
        await self._connection.commit()
        
        # Commit status change to Git
        await self._commit_experiment_changes(
            experiment_id, f"Update status to {status}"
        )
    
    async def update_experiment_results(self, experiment_id: str, 
                                      results: Dict[str, Any],
                                      validation_results: Dict[str, Any] = None) -> None:
        """Update experiment results."""
        now = datetime.now(timezone.utc).isoformat()
        results_json = json.dumps(results)
        validation_json = json.dumps(validation_results) if validation_results else None
        
        await self._connection.execute("""
            UPDATE experiments 
            SET results = ?, updated_at = ?
            WHERE id = ?
        """, (results_json, now, experiment_id))
        
        if validation_json:
            await self._connection.execute("""
                UPDATE experiments 
                SET verification_results = ?
                WHERE id = ?
            """, (validation_json, experiment_id))
        
        await self._connection.commit()
        
        # Save results to files
        experiment_dir = self.experiments_dir / experiment_id
        
        # Save results
        results_file = experiment_dir / "results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save validation results
        if validation_results:
            validation_file = experiment_dir / "validation_results.json"
            with open(validation_file, 'w') as f:
                json.dump(validation_results, f, indent=2)
        
        # Commit results to Git
        await self._commit_experiment_changes(
            experiment_id, "Update experiment results"
        )
    
    async def update_experiment_benchmarks(self, experiment_id: str, 
                                         benchmarks: Dict[str, Any]) -> None:
        """Update experiment benchmark results."""
        now = datetime.now(timezone.utc).isoformat()
        benchmarks_json = json.dumps(benchmarks)
        
        await self._connection.execute("""
            UPDATE experiments 
            SET benchmarks = ?, updated_at = ?
            WHERE id = ?
        """, (benchmarks_json, now, experiment_id))
        
        await self._connection.commit()
        
        # Save benchmarks to file
        experiment_dir = self.experiments_dir / experiment_id
        benchmarks_file = experiment_dir / "benchmarks.json"
        with open(benchmarks_file, 'w') as f:
            json.dump(benchmarks, f, indent=2)
        
        # Commit benchmarks to Git
        await self._commit_experiment_changes(
            experiment_id, "Update benchmark results"
        )
    
    async def update_experiment_verification(self, experiment_id: str, 
                                           verification_results: Dict[str, Any]) -> None:
        """Update experiment verification results."""
        now = datetime.now(timezone.utc).isoformat()
        verification_json = json.dumps(verification_results)
        
        await self._connection.execute("""
            UPDATE experiments 
            SET verification_results = ?, updated_at = ?
            WHERE id = ?
        """, (verification_json, now, experiment_id))
        
        await self._connection.commit()
        
        # Save verification results to file
        experiment_dir = self.experiments_dir / experiment_id
        verification_file = experiment_dir / "verification_results.json"
        with open(verification_file, 'w') as f:
            json.dump(verification_results, f, indent=2)
        
        # Commit verification results to Git
        await self._commit_experiment_changes(
            experiment_id, "Update verification results"
        )
    
    async def add_reproduction_record(self, original_experiment_id: str,
                                    reproduction_experiment_id: str,
                                    reproduction_results: Dict[str, Any]) -> None:
        """Add a reproduction record to an experiment."""
        # Get current reproductions
        experiment = await self.get_experiment(original_experiment_id)
        if not experiment:
            raise ExperimentNotFoundError(f"Experiment {original_experiment_id} not found")
        
        # Add new reproduction record
        reproduction_record = {
            'experiment_id': reproduction_experiment_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'results': reproduction_results,
            'reproducible': reproduction_results.get('reproducible', False),
            'similarity_score': reproduction_results.get('similarity_score', 0.0)
        }
        
        experiment.reproductions.append(reproduction_record)
        
        # Update database
        reproductions_json = json.dumps(experiment.reproductions)
        now = datetime.now(timezone.utc).isoformat()
        
        await self._connection.execute("""
            UPDATE experiments 
            SET reproductions = ?, updated_at = ?
            WHERE id = ?
        """, (reproductions_json, now, original_experiment_id))
        
        await self._connection.commit()
    
    async def search_experiments(self, filters: Dict[str, Any] = None,
                               limit: int = 100, offset: int = 0) -> List[ExperimentRecord]:
        """Search experiments with filters."""
        query = "SELECT * FROM experiments WHERE 1=1"
        params = []
        
        if filters:
            if filters.get('status'):
                query += " AND status = ?"
                params.append(filters['status'])
            
            if filters.get('author'):
                query += " AND author LIKE ?"
                params.append(f"%{filters['author']}%")
            
            if filters.get('agi_framework'):
                query += " AND agi_framework = ?"
                params.append(filters['agi_framework'])
            
            if filters.get('research_area'):
                query += " AND research_area = ?"
                params.append(filters['research_area'])
            
            if filters.get('tags'):
                # Search in JSON tags array
                for tag in filters['tags']:
                    query += " AND tags LIKE ?"
                    params.append(f"%{tag}%")
        
        query += f" ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"
        
        async with self._connection.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_experiment_record(row) for row in rows]
    
    async def get_experiment_statistics(self) -> Dict[str, Any]:
        """Get platform experiment statistics."""
        stats = {}
        
        # Total experiments
        async with self._connection.execute("SELECT COUNT(*) FROM experiments") as cursor:
            result = await cursor.fetchone()
            stats['total_experiments'] = result[0]
        
        # Experiments by status
        async with self._connection.execute("""
            SELECT status, COUNT(*) FROM experiments GROUP BY status
        """) as cursor:
            status_counts = await cursor.fetchall()
            stats['by_status'] = {status: count for status, count in status_counts}
        
        # Experiments by framework
        async with self._connection.execute("""
            SELECT agi_framework, COUNT(*) FROM experiments GROUP BY agi_framework
        """) as cursor:
            framework_counts = await cursor.fetchall()
            stats['by_framework'] = {framework: count for framework, count in framework_counts}
        
        # Recent activity (last 30 days)
        async with self._connection.execute("""
            SELECT COUNT(*) FROM experiments 
            WHERE created_at > datetime('now', '-30 days')
        """) as cursor:
            result = await cursor.fetchone()
            stats['recent_experiments'] = result[0]
        
        return stats
    
    async def _store_experiment_record(self, record: ExperimentRecord) -> None:
        """Store experiment record in database."""
        await self._connection.execute("""
            INSERT INTO experiments (
                id, title, description, author, email, tags, agi_framework,
                research_area, hypothesis, expected_outcomes, ethical_considerations,
                computational_requirements, status, created_at, updated_at,
                version, git_commit, environment_snapshot, code_hash, data_hash,
                config_hash, parameters, results, benchmarks, verification_results,
                peer_reviews, citations, reproductions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.metadata.id,
            record.metadata.title,
            record.metadata.description,
            record.metadata.author,
            record.metadata.email,
            json.dumps(record.metadata.tags),
            record.metadata.agi_framework,
            record.metadata.research_area,
            record.metadata.hypothesis,
            json.dumps(record.metadata.expected_outcomes),
            record.metadata.ethical_considerations,
            json.dumps(record.metadata.computational_requirements),
            record.status.value,
            record.created_at.isoformat(),
            record.updated_at.isoformat(),
            record.version,
            record.git_commit,
            json.dumps(record.environment_snapshot),
            record.code_hash,
            record.data_hash,
            record.config_hash,
            json.dumps(record.parameters),
            json.dumps(record.results) if record.results else None,
            json.dumps(record.benchmarks) if record.benchmarks else None,
            json.dumps(record.verification_results) if record.verification_results else None,
            json.dumps(record.peer_reviews),
            json.dumps(record.citations),
            json.dumps(record.reproductions)
        ))
        
        await self._connection.commit()
    
    def _row_to_experiment_record(self, row) -> ExperimentRecord:
        """Convert database row to ExperimentRecord."""
        # Parse metadata
        metadata = ExperimentMetadata(
            id=row[0],
            title=row[1],
            description=row[2] or "",
            author=row[3],
            email=row[4],
            tags=json.loads(row[5]) if row[5] else [],
            agi_framework=row[6] or "unknown",
            research_area=row[7] or "general",
            hypothesis=row[8] or "",
            expected_outcomes=json.loads(row[9]) if row[9] else [],
            ethical_considerations=row[10] or "",
            computational_requirements=json.loads(row[11]) if row[11] else {}
        )
        
        # Create experiment record
        return ExperimentRecord(
            metadata=metadata,
            status=ExperimentStatus(row[12]),
            created_at=datetime.fromisoformat(row[13]),
            updated_at=datetime.fromisoformat(row[14]),
            version=row[15],
            git_commit=row[16],
            environment_snapshot=json.loads(row[17]) if row[17] else {},
            code_hash=row[18],
            data_hash=row[19] or "",
            config_hash=row[20] or "",
            parameters=json.loads(row[21]) if row[21] else {},
            results=json.loads(row[22]) if row[22] else None,
            benchmarks=json.loads(row[23]) if row[23] else None,
            verification_results=json.loads(row[24]) if row[24] else None,
            peer_reviews=json.loads(row[25]) if row[25] else [],
            citations=json.loads(row[26]) if row[26] else [],
            reproductions=json.loads(row[27]) if row[27] else []
        )
    
    async def _commit_experiment_changes(self, experiment_id: str, message: str) -> str:
        """Commit experiment changes to Git."""
        if not self.git_repo:
            return ""
        
        try:
            # Stage experiment directory changes
            experiment_path = f"{experiment_id}/"
            if os.path.exists(os.path.join(self.experiments_dir, experiment_path)):
                self.git_repo.index.add([experiment_path])
            
            # Create commit
            commit = self.git_repo.index.commit(f"[{experiment_id}] {message}")
            return commit.hexsha
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Warning: Failed to commit to Git: {e}")
            return ""
    
    def _compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on experiment tracker."""
        try:
            # Check database connection
            async with self._connection.execute("SELECT 1") as cursor:
                await cursor.fetchone()
            
            # Check experiments directory
            experiments_accessible = self.experiments_dir.exists()
            
            # Check Git repository
            git_healthy = self.git_repo is not None
            
            return {
                'status': 'healthy',
                'database': 'connected',
                'experiments_dir': experiments_accessible,
                'git_repo': git_healthy,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._connection:
            await self._connection.close()
            self._connection = None