"""
Progress Tracking System for AGI Component Benchmark Suite

Implements comprehensive progress tracking including:
- Database management for benchmark results
- Historical performance tracking
- Leaderboards for different AGI approaches
- Progress visualization over time
- Capability coverage analysis
- Gap identification for AGI completeness
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import statistics
from pathlib import Path

from .core import BenchmarkSuiteResult, BenchmarkResult


@dataclass
class SystemProfile:
    """Profile of an AGI system for tracking"""
    system_id: str
    name: str
    version: str
    architecture_type: str  # neural, symbolic, hybrid, etc.
    description: str
    tags: List[str]
    created_date: datetime


@dataclass
class ProgressMetrics:
    """Progress metrics for a system"""
    system_id: str
    timestamp: datetime
    overall_score: float
    category_scores: Dict[str, float]
    capability_coverage: float
    improvement_rate: float
    consistency_score: float


@dataclass
class CapabilityGap:
    """Identified capability gap"""
    capability: str
    current_score: float
    target_score: float
    gap_size: float
    priority: str  # high, medium, low
    recommendations: List[str]


class ProgressTracker:
    """Tracks progress of AGI systems over time"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_path = config.get("database", {}).get("path", "agi_benchmark_results.db")
        self.backup_enabled = config.get("database", {}).get("backup_enabled", True)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Systems table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS systems (
                    system_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    architecture_type TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    created_date TEXT NOT NULL
                )
            ''')
            
            # Benchmark runs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    run_id TEXT PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    config_hash TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    total_execution_time REAL NOT NULL,
                    success_rate REAL NOT NULL,
                    average_score REAL NOT NULL,
                    system_info TEXT,
                    FOREIGN KEY (system_id) REFERENCES systems (system_id)
                )
            ''')
            
            # Individual test results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_results (
                    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    benchmark_name TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    normalized_score REAL NOT NULL,
                    execution_time REAL NOT NULL,
                    success INTEGER NOT NULL,
                    error_message TEXT,
                    details TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES benchmark_runs (run_id)
                )
            ''')
            
            # Progress metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS progress_metrics (
                    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    system_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    overall_score REAL NOT NULL,
                    category_scores TEXT NOT NULL,
                    capability_coverage REAL NOT NULL,
                    improvement_rate REAL NOT NULL,
                    consistency_score REAL NOT NULL,
                    FOREIGN KEY (system_id) REFERENCES systems (system_id)
                )
            ''')
            
            # Capability gaps table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS capability_gaps (
                    gap_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    system_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    current_score REAL NOT NULL,
                    target_score REAL NOT NULL,
                    gap_size REAL NOT NULL,
                    priority TEXT NOT NULL,
                    recommendations TEXT,
                    identified_date TEXT NOT NULL,
                    FOREIGN KEY (system_id) REFERENCES systems (system_id)
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_benchmark_runs_system_id ON benchmark_runs(system_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_results_run_id ON test_results(run_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_results_benchmark ON test_results(benchmark_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_metrics_system_id ON progress_metrics(system_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_metrics_timestamp ON progress_metrics(timestamp)')
            
            conn.commit()
    
    def register_system(self, system_profile: SystemProfile) -> bool:
        """Register a new AGI system for tracking"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO systems 
                    (system_id, name, version, architecture_type, description, tags, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    system_profile.system_id,
                    system_profile.name,
                    system_profile.version,
                    system_profile.architecture_type,
                    system_profile.description,
                    json.dumps(system_profile.tags),
                    system_profile.created_date.isoformat()
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error registering system: {e}")
            return False
    
    def store_benchmark_results(self, suite_result: BenchmarkSuiteResult) -> bool:
        """Store benchmark results in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Generate run ID
                run_id = f"{suite_result.system_name}_{suite_result.start_time.strftime('%Y%m%d_%H%M%S')}"
                
                # Store benchmark run
                cursor.execute('''
                    INSERT INTO benchmark_runs 
                    (run_id, system_id, config_hash, start_time, end_time, total_execution_time, 
                     success_rate, average_score, system_info)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    run_id,
                    suite_result.system_name,
                    str(suite_result.config_hash),
                    suite_result.start_time.isoformat(),
                    suite_result.end_time.isoformat(),
                    suite_result.total_execution_time,
                    suite_result.success_rate,
                    suite_result.average_score,
                    json.dumps(suite_result.system_info)
                ))
                
                # Store individual test results
                for result in suite_result.results:
                    cursor.execute('''
                        INSERT INTO test_results 
                        (run_id, benchmark_name, test_name, score, max_score, normalized_score,
                         execution_time, success, error_message, details, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        run_id,
                        result.benchmark_name,
                        result.test_name,
                        result.score,
                        result.max_score,
                        result.normalized_score,
                        result.execution_time,
                        1 if result.success else 0,
                        result.error_message,
                        json.dumps(result.details),
                        result.timestamp.isoformat()
                    ))
                
                conn.commit()
                
                # Update progress metrics
                self._update_progress_metrics(suite_result.system_name, suite_result)
                
                return True
        except Exception as e:
            print(f"Error storing benchmark results: {e}")
            return False
    
    def _update_progress_metrics(self, system_id: str, suite_result: BenchmarkSuiteResult):
        """Update progress metrics for a system"""
        category_scores = self._calculate_category_scores(suite_result.results)
        capability_coverage = self._calculate_capability_coverage(suite_result.results)
        improvement_rate = self._calculate_improvement_rate(system_id, suite_result.average_score)
        consistency_score = self._calculate_consistency_score(suite_result.results)
        
        progress_metrics = ProgressMetrics(
            system_id=system_id,
            timestamp=suite_result.end_time,
            overall_score=suite_result.average_score,
            category_scores=category_scores,
            capability_coverage=capability_coverage,
            improvement_rate=improvement_rate,
            consistency_score=consistency_score
        )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO progress_metrics 
                    (system_id, timestamp, overall_score, category_scores, capability_coverage,
                     improvement_rate, consistency_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    progress_metrics.system_id,
                    progress_metrics.timestamp.isoformat(),
                    progress_metrics.overall_score,
                    json.dumps(progress_metrics.category_scores),
                    progress_metrics.capability_coverage,
                    progress_metrics.improvement_rate,
                    progress_metrics.consistency_score
                ))
                conn.commit()
        except Exception as e:
            print(f"Error updating progress metrics: {e}")
    
    def get_system_progress(self, system_id: str, days: int = 30) -> List[ProgressMetrics]:
        """Get progress metrics for a system over time"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT system_id, timestamp, overall_score, category_scores, capability_coverage,
                           improvement_rate, consistency_score
                    FROM progress_metrics 
                    WHERE system_id = ? AND timestamp >= ?
                    ORDER BY timestamp ASC
                ''', (system_id, cutoff_date.isoformat()))
                
                rows = cursor.fetchall()
                return [
                    ProgressMetrics(
                        system_id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        overall_score=row[2],
                        category_scores=json.loads(row[3]),
                        capability_coverage=row[4],
                        improvement_rate=row[5],
                        consistency_score=row[6]
                    )
                    for row in rows
                ]
        except Exception as e:
            print(f"Error getting system progress: {e}")
            return []
    
    def get_leaderboard(self, category: Optional[str] = None, architecture_type: Optional[str] = None,
                       limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard of top performing systems"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if category:
                    # Category-specific leaderboard
                    query = '''
                        SELECT s.name, s.version, s.architecture_type, tr.benchmark_name,
                               AVG(tr.normalized_score) as avg_score, COUNT(tr.result_id) as test_count,
                               MAX(br.end_time) as last_run
                        FROM systems s
                        JOIN benchmark_runs br ON s.system_id = br.system_id
                        JOIN test_results tr ON br.run_id = tr.run_id
                        WHERE tr.benchmark_name LIKE ?
                    '''
                    params = [f"%{category}%"]
                    
                    if architecture_type:
                        query += " AND s.architecture_type = ?"
                        params.append(architecture_type)
                    
                    query += '''
                        GROUP BY s.system_id, tr.benchmark_name
                        ORDER BY avg_score DESC
                        LIMIT ?
                    '''
                    params.append(limit)
                else:
                    # Overall leaderboard
                    query = '''
                        SELECT s.name, s.version, s.architecture_type,
                               AVG(br.average_score) as avg_score, COUNT(br.run_id) as run_count,
                               MAX(br.end_time) as last_run
                        FROM systems s
                        JOIN benchmark_runs br ON s.system_id = br.system_id
                    '''
                    params = []
                    
                    if architecture_type:
                        query += " WHERE s.architecture_type = ?"
                        params.append(architecture_type)
                    
                    query += '''
                        GROUP BY s.system_id
                        ORDER BY avg_score DESC
                        LIMIT ?
                    '''
                    params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                if category:
                    return [
                        {
                            "rank": i + 1,
                            "name": row[0],
                            "version": row[1],
                            "architecture_type": row[2],
                            "category": row[3],
                            "score": row[4],
                            "test_count": row[5],
                            "last_run": row[6]
                        }
                        for i, row in enumerate(rows)
                    ]
                else:
                    return [
                        {
                            "rank": i + 1,
                            "name": row[0],
                            "version": row[1],
                            "architecture_type": row[2],
                            "score": row[3],
                            "run_count": row[4],
                            "last_run": row[5]
                        }
                        for i, row in enumerate(rows)
                    ]
        except Exception as e:
            print(f"Error getting leaderboard: {e}")
            return []
    
    def identify_capability_gaps(self, system_id: str, target_scores: Dict[str, float] = None) -> List[CapabilityGap]:
        """Identify capability gaps for a system"""
        if target_scores is None:
            target_scores = {
                "reasoning": 85.0,
                "learning": 80.0,
                "memory": 80.0,
                "creativity": 70.0,
                "consciousness": 60.0,
                "symbolic": 85.0,
                "neural_symbolic": 75.0,
                "real_world": 70.0
            }
        
        gaps = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get latest scores for each category
                for category, target_score in target_scores.items():
                    cursor.execute('''
                        SELECT AVG(tr.normalized_score) as avg_score
                        FROM test_results tr
                        JOIN benchmark_runs br ON tr.run_id = br.run_id
                        WHERE br.system_id = ? AND tr.benchmark_name LIKE ?
                        AND br.end_time = (
                            SELECT MAX(br2.end_time) 
                            FROM benchmark_runs br2 
                            WHERE br2.system_id = ?
                        )
                    ''', (system_id, f"%{category}%", system_id))
                    
                    result = cursor.fetchone()
                    current_score = result[0] if result and result[0] else 0.0
                    
                    if current_score < target_score:
                        gap_size = target_score - current_score
                        priority = "high" if gap_size > 20 else "medium" if gap_size > 10 else "low"
                        
                        recommendations = self._generate_gap_recommendations(category, current_score, target_score)
                        
                        gap = CapabilityGap(
                            capability=category,
                            current_score=current_score,
                            target_score=target_score,
                            gap_size=gap_size,
                            priority=priority,
                            recommendations=recommendations
                        )
                        gaps.append(gap)
                        
                        # Store gap in database
                        self._store_capability_gap(system_id, gap)
            
            return sorted(gaps, key=lambda x: x.gap_size, reverse=True)
        except Exception as e:
            print(f"Error identifying capability gaps: {e}")
            return []
    
    def _store_capability_gap(self, system_id: str, gap: CapabilityGap):
        """Store capability gap in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO capability_gaps 
                    (system_id, capability, current_score, target_score, gap_size, priority, 
                     recommendations, identified_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    system_id,
                    gap.capability,
                    gap.current_score,
                    gap.target_score,
                    gap.gap_size,
                    gap.priority,
                    json.dumps(gap.recommendations),
                    datetime.now().isoformat()
                ))
                conn.commit()
        except Exception as e:
            print(f"Error storing capability gap: {e}")
    
    def get_benchmark_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get overall benchmark statistics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total systems
                cursor.execute("SELECT COUNT(DISTINCT system_id) FROM systems")
                total_systems = cursor.fetchone()[0]
                
                # Total benchmark runs
                cursor.execute('''
                    SELECT COUNT(*) FROM benchmark_runs 
                    WHERE end_time >= ?
                ''', (cutoff_date.isoformat(),))
                recent_runs = cursor.fetchone()[0]
                
                # Average scores by category
                cursor.execute('''
                    SELECT tr.benchmark_name, AVG(tr.normalized_score) as avg_score,
                           COUNT(tr.result_id) as test_count
                    FROM test_results tr
                    JOIN benchmark_runs br ON tr.run_id = br.run_id
                    WHERE br.end_time >= ?
                    GROUP BY tr.benchmark_name
                    ORDER BY avg_score DESC
                ''', (cutoff_date.isoformat(),))
                category_stats = [
                    {
                        "category": row[0],
                        "average_score": row[1],
                        "test_count": row[2]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Architecture type performance
                cursor.execute('''
                    SELECT s.architecture_type, AVG(br.average_score) as avg_score,
                           COUNT(br.run_id) as run_count
                    FROM systems s
                    JOIN benchmark_runs br ON s.system_id = br.system_id
                    WHERE br.end_time >= ?
                    GROUP BY s.architecture_type
                    ORDER BY avg_score DESC
                ''', (cutoff_date.isoformat(),))
                architecture_stats = [
                    {
                        "architecture": row[0],
                        "average_score": row[1],
                        "run_count": row[2]
                    }
                    for row in cursor.fetchall()
                ]
                
                return {
                    "total_systems": total_systems,
                    "recent_runs": recent_runs,
                    "category_performance": category_stats,
                    "architecture_performance": architecture_stats,
                    "analysis_period_days": days
                }
        except Exception as e:
            print(f"Error getting benchmark statistics: {e}")
            return {}
    
    def _calculate_category_scores(self, results: List[BenchmarkResult]) -> Dict[str, float]:
        """Calculate average scores by benchmark category"""
        category_scores = {}
        category_results = {}
        
        for result in results:
            category = result.benchmark_name.split('_')[0]  # Extract category from benchmark name
            if category not in category_results:
                category_results[category] = []
            category_results[category].append(result.normalized_score)
        
        for category, scores in category_results.items():
            category_scores[category] = statistics.mean(scores) if scores else 0.0
        
        return category_scores
    
    def _calculate_capability_coverage(self, results: List[BenchmarkResult]) -> float:
        """Calculate what percentage of AGI capabilities are covered"""
        expected_categories = {
            "reasoning", "learning", "memory", "creativity", 
            "consciousness", "symbolic", "neural_symbolic", "real_world"
        }
        
        tested_categories = set()
        for result in results:
            category = result.benchmark_name.split('_')[0]
            tested_categories.add(category)
        
        coverage = len(tested_categories.intersection(expected_categories)) / len(expected_categories)
        return coverage * 100.0
    
    def _calculate_improvement_rate(self, system_id: str, current_score: float) -> float:
        """Calculate improvement rate compared to previous runs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT average_score, end_time 
                    FROM benchmark_runs 
                    WHERE system_id = ? 
                    ORDER BY end_time DESC 
                    LIMIT 3
                ''', (system_id,))
                
                scores = [row[0] for row in cursor.fetchall()]
                
                if len(scores) < 2:
                    return 0.0  # Not enough data
                
                # Calculate improvement rate over recent runs
                if len(scores) >= 3:
                    recent_improvement = scores[0] - scores[1]
                    previous_improvement = scores[1] - scores[2]
                    improvement_rate = recent_improvement - previous_improvement
                else:
                    improvement_rate = scores[0] - scores[1]
                
                return improvement_rate
        except Exception:
            return 0.0
    
    def _calculate_consistency_score(self, results: List[BenchmarkResult]) -> float:
        """Calculate consistency of performance across tests"""
        if not results:
            return 0.0
        
        scores = [r.normalized_score for r in results if r.success]
        if len(scores) < 2:
            return 100.0  # Perfect consistency with single score
        
        # Calculate coefficient of variation (lower is more consistent)
        mean_score = statistics.mean(scores)
        if mean_score == 0:
            return 0.0
        
        std_dev = statistics.stdev(scores)
        cv = std_dev / mean_score
        
        # Convert to consistency score (higher is better)
        consistency_score = max(0, 100 - (cv * 100))
        return consistency_score
    
    def _generate_gap_recommendations(self, capability: str, current_score: float, target_score: float) -> List[str]:
        """Generate recommendations for addressing capability gaps"""
        recommendations = []
        gap_size = target_score - current_score
        
        base_recommendations = {
            "reasoning": [
                "Focus on logical inference training",
                "Implement formal reasoning modules",
                "Enhance pattern recognition capabilities",
                "Add causal reasoning components"
            ],
            "learning": [
                "Improve meta-learning algorithms",
                "Implement continual learning mechanisms",
                "Enhance few-shot learning capabilities",
                "Add transfer learning components"
            ],
            "memory": [
                "Implement episodic memory systems",
                "Enhance working memory capacity",
                "Add procedural memory mechanisms",
                "Improve memory consolidation"
            ],
            "creativity": [
                "Add divergent thinking modules",
                "Implement novelty detection",
                "Enhance conceptual combination",
                "Add artistic generation capabilities"
            ],
            "consciousness": [
                "Implement self-monitoring systems",
                "Add metacognitive components",
                "Enhance introspective capabilities",
                "Develop theory of mind modules"
            ],
            "symbolic": [
                "Strengthen logical reasoning",
                "Implement probabilistic logic",
                "Add temporal reasoning capabilities",
                "Enhance symbolic manipulation"
            ],
            "neural_symbolic": [
                "Improve symbol grounding",
                "Enhance concept formation",
                "Add explainability modules",
                "Strengthen neural-symbolic integration"
            ],
            "real_world": [
                "Add robotic control modules",
                "Enhance natural language understanding",
                "Implement scientific reasoning",
                "Add ethical reasoning components"
            ]
        }
        
        if capability in base_recommendations:
            recommendations.extend(base_recommendations[capability])
        
        # Add priority-based recommendations
        if gap_size > 20:
            recommendations.insert(0, f"Priority: Address {capability} as critical capability gap")
        elif gap_size > 10:
            recommendations.insert(0, f"Priority: Improve {capability} performance systematically")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def backup_database(self) -> bool:
        """Create a backup of the database"""
        if not self.backup_enabled:
            return True
        
        try:
            backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create backup directory if it doesn't exist
            backup_dir = Path(backup_path).parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            # Copy database file
            import shutil
            shutil.copy2(self.db_path, backup_dir / Path(backup_path).name)
            
            return True
        except Exception as e:
            print(f"Error creating database backup: {e}")
            return False
    
    def cleanup_old_data(self, days: int = 90) -> bool:
        """Clean up old benchmark data"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old test results
                cursor.execute('''
                    DELETE FROM test_results 
                    WHERE run_id IN (
                        SELECT run_id FROM benchmark_runs 
                        WHERE end_time < ?
                    )
                ''', (cutoff_date.isoformat(),))
                
                # Delete old benchmark runs
                cursor.execute('''
                    DELETE FROM benchmark_runs 
                    WHERE end_time < ?
                ''', (cutoff_date.isoformat(),))
                
                # Delete old progress metrics
                cursor.execute('''
                    DELETE FROM progress_metrics 
                    WHERE timestamp < ?
                ''', (cutoff_date.isoformat(),))
                
                # Delete old capability gaps
                cursor.execute('''
                    DELETE FROM capability_gaps 
                    WHERE identified_date < ?
                ''', (cutoff_date.isoformat(),))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error cleaning up old data: {e}")
            return False