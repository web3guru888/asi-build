#!/usr/bin/env python3
"""
Weights & Biases Integration for AGI Model Registry
Comprehensive integration with W&B for experiment tracking, model versioning, and artifacts
"""

import asyncio
import logging
import json
import os
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import wandb
from wandb.sdk.lib import RunDisabled
import pickle
import yaml

@dataclass
class WandBModelMetadata:
    """W&B Model metadata structure"""
    model_id: str
    version: str
    description: str
    project: str
    entity: str
    tags: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None

@dataclass
class WandBExperiment:
    """W&B Experiment tracking data"""
    run_id: str
    run_name: str
    project: str
    entity: str
    state: str
    config: Dict[str, Any]
    summary: Dict[str, Any]
    tags: List[str]
    created_at: datetime
    updated_at: datetime

class WandBIntegration:
    """
    Comprehensive Weights & Biases integration for AGI models
    """
    
    def __init__(self, project: str, entity: str, api_key: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.project = project
        self.entity = entity
        
        # Initialize W&B
        if api_key:
            wandb.login(key=api_key)
        
        self.api = wandb.Api()
        self.current_run: Optional[wandb.sdk.wandb_run.Run] = None
        
        self.logger.info(f"W&B integration initialized for project: {entity}/{project}")
    
    async def start_experiment(self, experiment_name: str, config: Dict[str, Any], 
                              tags: List[str] = None, notes: str = None) -> str:
        """Start a new W&B experiment run"""
        self.logger.info(f"Starting W&B experiment: {experiment_name}")
        
        try:
            # Initialize run
            self.current_run = wandb.init(
                project=self.project,
                entity=self.entity,
                name=experiment_name,
                config=config,
                tags=tags or [],
                notes=notes,
                reinit=True
            )
            
            # Log system information
            await self._log_system_info()
            
            self.logger.info(f"W&B run started: {self.current_run.id}")
            return self.current_run.id
            
        except Exception as e:
            self.logger.error(f"Failed to start W&B experiment: {e}")
            raise
    
    async def _log_system_info(self):
        """Log system information to W&B"""
        try:
            system_info = {
                "framework": "kenny-agi",
                "timestamp": datetime.now().isoformat(),
                "python_version": os.sys.version,
            }
            
            if self.current_run:
                self.current_run.config.update({"system_info": system_info})
                
        except Exception as e:
            self.logger.warning(f"Failed to log system info: {e}")
    
    async def log_metrics(self, metrics: Dict[str, Any], step: Optional[int] = None) -> bool:
        """Log metrics to current W&B run"""
        try:
            if not self.current_run:
                self.logger.warning("No active W&B run. Call start_experiment() first.")
                return False
            
            # Filter numeric metrics
            numeric_metrics = {k: v for k, v in metrics.items() 
                             if isinstance(v, (int, float))}
            
            if numeric_metrics:
                self.current_run.log(numeric_metrics, step=step)
                self.logger.debug(f"Logged {len(numeric_metrics)} metrics to W&B")
            
            # Log non-numeric data as summary
            non_numeric = {k: v for k, v in metrics.items() 
                          if not isinstance(v, (int, float))}
            
            if non_numeric:
                for key, value in non_numeric.items():
                    self.current_run.summary[key] = value
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log metrics: {e}")
            return False
    
    async def log_model_artifacts(self, model_path: str, model_name: str, 
                                 aliases: List[str] = None, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Log model artifacts to W&B"""
        self.logger.info(f"Logging model artifacts: {model_name}")
        
        try:
            if not self.current_run:
                self.logger.warning("No active W&B run. Call start_experiment() first.")
                return None
            
            # Create model artifact
            model_artifact = wandb.Artifact(
                name=model_name,
                type="model",
                description=metadata.get("description", f"AGI model {model_name}") if metadata else f"AGI model {model_name}",
                metadata=metadata or {}
            )
            
            # Add model files
            if os.path.isdir(model_path):
                model_artifact.add_dir(model_path)
            elif os.path.isfile(model_path):
                model_artifact.add_file(model_path)
            else:
                raise FileNotFoundError(f"Model path not found: {model_path}")
            
            # Log the artifact
            self.current_run.log_artifact(model_artifact, aliases=aliases or ["latest"])
            
            artifact_name = f"{self.entity}/{self.project}/{model_name}:latest"
            self.logger.info(f"Model artifacts logged: {artifact_name}")
            
            return artifact_name
            
        except Exception as e:
            self.logger.error(f"Failed to log model artifacts: {e}")
            return None
    
    async def log_dataset(self, dataset_path: str, dataset_name: str, 
                         metadata: Dict[str, Any] = None) -> Optional[str]:
        """Log dataset to W&B"""
        self.logger.info(f"Logging dataset: {dataset_name}")
        
        try:
            if not self.current_run:
                self.logger.warning("No active W&B run. Call start_experiment() first.")
                return None
            
            # Create dataset artifact
            dataset_artifact = wandb.Artifact(
                name=dataset_name,
                type="dataset",
                description=metadata.get("description", f"Dataset {dataset_name}") if metadata else f"Dataset {dataset_name}",
                metadata=metadata or {}
            )
            
            # Add dataset files
            if os.path.isdir(dataset_path):
                dataset_artifact.add_dir(dataset_path)
            elif os.path.isfile(dataset_path):
                dataset_artifact.add_file(dataset_path)
            else:
                raise FileNotFoundError(f"Dataset path not found: {dataset_path}")
            
            # Log the artifact
            self.current_run.log_artifact(dataset_artifact)
            
            artifact_name = f"{self.entity}/{self.project}/{dataset_name}:latest"
            self.logger.info(f"Dataset logged: {artifact_name}")
            
            return artifact_name
            
        except Exception as e:
            self.logger.error(f"Failed to log dataset: {e}")
            return None
    
    async def log_code(self, code_path: str = ".", exclude_patterns: List[str] = None) -> bool:
        """Log code to W&B"""
        try:
            if not self.current_run:
                return False
            
            # Default exclusions
            default_excludes = [
                "*.pyc", "__pycache__", ".git", "*.log", "*.tmp", 
                "wandb", ".wandb", "*.pkl", "*.pt", "*.pth"
            ]
            
            exclude_patterns = exclude_patterns or []
            all_excludes = default_excludes + exclude_patterns
            
            # Save code
            self.current_run.log_code(
                root=code_path,
                name="source_code",
                exclude_fn=lambda path: any(pattern in path for pattern in all_excludes)
            )
            
            self.logger.info("Source code logged to W&B")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log code: {e}")
            return False
    
    async def finish_experiment(self, exit_code: int = 0) -> bool:
        """Finish current W&B run"""
        try:
            if self.current_run:
                self.current_run.finish(exit_code=exit_code)
                self.current_run = None
                self.logger.info("W&B run finished")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to finish W&B run: {e}")
            return False
    
    async def download_model_artifact(self, artifact_name: str, output_path: str) -> bool:
        """Download model artifact from W&B"""
        self.logger.info(f"Downloading model artifact: {artifact_name}")
        
        try:
            # Get artifact
            artifact = self.api.artifact(artifact_name)
            
            # Download to specified path
            download_path = artifact.download(root=output_path)
            
            self.logger.info(f"Model artifact downloaded to: {download_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download model artifact: {e}")
            return False
    
    async def get_model_metadata(self, model_name: str, alias: str = "latest") -> Optional[WandBModelMetadata]:
        """Get model metadata from W&B"""
        try:
            artifact_name = f"{self.entity}/{self.project}/{model_name}:{alias}"
            artifact = self.api.artifact(artifact_name)
            
            return WandBModelMetadata(
                model_id=model_name,
                version=artifact.version,
                description=artifact.description,
                project=self.project,
                entity=self.entity,
                tags=artifact.tags,
                config=artifact.metadata,
                summary={},  # W&B artifacts don't have summary directly
                artifacts=[f.name for f in artifact.files()],
                aliases=artifact.aliases,
                created_at=datetime.fromisoformat(artifact.created_at.replace('Z', '+00:00'))
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get model metadata: {e}")
            return None
    
    async def list_models(self, model_type: str = "model") -> List[WandBModelMetadata]:
        """List all models in the project"""
        try:
            models = []
            artifacts = self.api.artifacts(type_name=model_type, project=f"{self.entity}/{self.project}")
            
            for artifact in artifacts:
                try:
                    model_metadata = WandBModelMetadata(
                        model_id=artifact.name,
                        version=artifact.version,
                        description=artifact.description,
                        project=self.project,
                        entity=self.entity,
                        tags=artifact.tags,
                        config=artifact.metadata,
                        summary={},
                        artifacts=[f.name for f in artifact.files()],
                        aliases=artifact.aliases,
                        created_at=datetime.fromisoformat(artifact.created_at.replace('Z', '+00:00'))
                    )
                    models.append(model_metadata)
                except Exception as e:
                    self.logger.warning(f"Failed to process artifact {artifact.name}: {e}")
            
            return models
            
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
            return []
    
    async def get_experiment_runs(self, filters: Dict[str, Any] = None) -> List[WandBExperiment]:
        """Get experiment runs from W&B"""
        try:
            # Build filter string
            filter_conditions = []
            if filters:
                for key, value in filters.items():
                    if key == "state":
                        filter_conditions.append(f"state = '{value}'")
                    elif key == "tags":
                        if isinstance(value, list):
                            tag_conditions = [f"tags = '{tag}'" for tag in value]
                            filter_conditions.append(f"({' OR '.join(tag_conditions)})")
                        else:
                            filter_conditions.append(f"tags = '{value}'")
                    elif key == "config":
                        for config_key, config_value in value.items():
                            filter_conditions.append(f"config.{config_key} = {config_value}")
            
            filter_string = " AND ".join(filter_conditions) if filter_conditions else None
            
            # Get runs
            runs = self.api.runs(
                path=f"{self.entity}/{self.project}",
                filters={"$and": [{"state": {"$ne": "crashed"}}]} if not filter_string else None
            )
            
            experiments = []
            for run in runs:
                try:
                    experiment = WandBExperiment(
                        run_id=run.id,
                        run_name=run.name,
                        project=self.project,
                        entity=self.entity,
                        state=run.state,
                        config=dict(run.config),
                        summary=dict(run.summary),
                        tags=run.tags,
                        created_at=run.created_at,
                        updated_at=run.updated_at
                    )
                    experiments.append(experiment)
                except Exception as e:
                    self.logger.warning(f"Failed to process run {run.id}: {e}")
            
            return experiments
            
        except Exception as e:
            self.logger.error(f"Failed to get experiment runs: {e}")
            return []
    
    async def compare_experiments(self, run_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple experiment runs"""
        try:
            runs_data = []
            
            for run_id in run_ids:
                try:
                    run = self.api.run(f"{self.entity}/{self.project}/{run_id}")
                    
                    run_data = {
                        "run_id": run_id,
                        "run_name": run.name,
                        "state": run.state,
                        "config": dict(run.config),
                        "summary": dict(run.summary),
                        "tags": run.tags,
                        "duration": (run.updated_at - run.created_at).total_seconds() if run.updated_at and run.created_at else None
                    }
                    runs_data.append(run_data)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get run data for {run_id}: {e}")
            
            # Extract common metrics for comparison
            all_metrics = set()
            for run_data in runs_data:
                all_metrics.update(run_data["summary"].keys())
            
            comparison = {
                "runs": runs_data,
                "common_metrics": list(all_metrics),
                "comparison_summary": {},
                "best_performing": {}
            }
            
            # Find best performing runs for each metric
            for metric in all_metrics:
                values = []
                for run_data in runs_data:
                    if metric in run_data["summary"]:
                        try:
                            value = float(run_data["summary"][metric])
                            values.append((run_data["run_id"], value))
                        except (ValueError, TypeError):
                            continue
                
                if values:
                    # Assume higher is better (can be configured)
                    best_run = max(values, key=lambda x: x[1])
                    comparison["best_performing"][metric] = {
                        "run_id": best_run[0],
                        "value": best_run[1]
                    }
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Failed to compare experiments: {e}")
            return {}
    
    async def create_model_registry_entry(self, model_artifact_name: str, stage: str = "staging",
                                         description: str = None) -> bool:
        """Create model registry entry (W&B Model Registry)"""
        try:
            # W&B uses a different approach - we'll use artifact aliases and tags
            artifact = self.api.artifact(model_artifact_name)
            
            # Add stage as alias
            stage_aliases = [alias for alias in artifact.aliases if alias != "latest"]
            stage_aliases.append(stage)
            
            # Link artifact with new aliases
            # Note: This is a simplified version - actual implementation may vary
            if self.current_run:
                linked_artifact = self.current_run.use_artifact(model_artifact_name)
                self.current_run.log_artifact(linked_artifact, aliases=stage_aliases)
            
            self.logger.info(f"Model {model_artifact_name} promoted to {stage}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create model registry entry: {e}")
            return False
    
    async def log_deployment_metrics(self, deployment_id: str, environment: str, 
                                   metrics: Dict[str, Any], model_name: str) -> bool:
        """Log deployment metrics"""
        try:
            # Create a new run for deployment tracking
            deployment_run = wandb.init(
                project=f"{self.project}-deployments",
                entity=self.entity,
                name=f"deployment-{deployment_id}",
                tags=["deployment", environment, model_name],
                config={
                    "deployment_id": deployment_id,
                    "environment": environment,
                    "model_name": model_name,
                    "deployment_timestamp": datetime.now().isoformat()
                },
                reinit=True
            )
            
            # Log deployment metrics
            numeric_metrics = {k: v for k, v in metrics.items() 
                             if isinstance(v, (int, float))}
            deployment_run.log(numeric_metrics)
            
            # Log non-numeric data as summary
            non_numeric = {k: v for k, v in metrics.items() 
                          if not isinstance(v, (int, float))}
            for key, value in non_numeric.items():
                deployment_run.summary[key] = value
            
            deployment_run.finish()
            self.logger.info(f"Deployment metrics logged for {deployment_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log deployment metrics: {e}")
            return False
    
    async def track_model_performance(self, model_name: str, environment: str, 
                                    performance_data: Dict[str, Any]) -> bool:
        """Track model performance in production"""
        try:
            # Create performance tracking run
            perf_run = wandb.init(
                project=f"{self.project}-monitoring",
                entity=self.entity,
                name=f"performance-{model_name}-{environment}",
                tags=["performance", "monitoring", environment, model_name],
                config={
                    "model_name": model_name,
                    "environment": environment,
                    "tracking_timestamp": datetime.now().isoformat()
                },
                reinit=True
            )
            
            # Log performance metrics
            for metric_name, metric_value in performance_data.items():
                if isinstance(metric_value, (int, float)):
                    perf_run.log({f"perf_{metric_name}": metric_value})
                else:
                    perf_run.summary[f"perf_{metric_name}"] = metric_value
            
            perf_run.finish()
            self.logger.info(f"Performance data tracked for {model_name} in {environment}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to track model performance: {e}")
            return False
    
    async def get_project_statistics(self) -> Dict[str, Any]:
        """Get project-level statistics"""
        try:
            # Get runs statistics
            runs = self.api.runs(f"{self.entity}/{self.project}")
            
            total_runs = len(runs)
            states = {}
            tags_count = {}
            
            for run in runs:
                # Count states
                states[run.state] = states.get(run.state, 0) + 1
                
                # Count tags
                for tag in run.tags:
                    tags_count[tag] = tags_count.get(tag, 0) + 1
            
            # Get artifacts statistics
            artifacts = self.api.artifacts(type_name="model", project=f"{self.entity}/{self.project}")
            model_artifacts = len(list(artifacts))
            
            dataset_artifacts = len(list(self.api.artifacts(type_name="dataset", project=f"{self.entity}/{self.project}")))
            
            return {
                "project": self.project,
                "entity": self.entity,
                "total_runs": total_runs,
                "run_states": states,
                "popular_tags": sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[:10],
                "model_artifacts": model_artifacts,
                "dataset_artifacts": dataset_artifacts,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get project statistics: {e}")
            return {}
    
    async def cleanup_old_artifacts(self, days_to_keep: int = 30, keep_tagged: bool = True) -> Dict[str, int]:
        """Cleanup old artifacts"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Get all artifacts
            all_artifacts = list(self.api.artifacts(project=f"{self.entity}/{self.project}"))
            
            deleted_count = 0
            kept_count = 0
            
            for artifact in all_artifacts:
                created_date = datetime.fromisoformat(artifact.created_at.replace('Z', '+00:00'))
                
                if created_date < cutoff_date:
                    # Check if artifact should be kept due to tags/aliases
                    if keep_tagged and (artifact.tags or len(artifact.aliases) > 1):
                        kept_count += 1
                        continue
                    
                    try:
                        artifact.delete()
                        deleted_count += 1
                        self.logger.info(f"Deleted old artifact: {artifact.name}:{artifact.version}")
                    except Exception as e:
                        self.logger.warning(f"Failed to delete artifact {artifact.name}: {e}")
                        kept_count += 1
                else:
                    kept_count += 1
            
            return {
                "deleted": deleted_count,
                "kept": kept_count,
                "total_processed": len(all_artifacts)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup artifacts: {e}")
            return {"error": str(e)}

# Example usage and testing
if __name__ == "__main__":
    async def main():
        from datetime import timedelta
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Initialize W&B integration
        wandb_integration = WandBIntegration(
            project="kenny-agi-test",
            entity="kenny-ai-team"
        )
        
        try:
            # Start experiment
            run_id = await wandb_integration.start_experiment(
                experiment_name="test-agi-training",
                config={
                    "learning_rate": 0.001,
                    "batch_size": 32,
                    "epochs": 10,
                    "model_architecture": "transformer",
                    "dataset": "kenny-corpus-v1"
                },
                tags=["test", "agi", "transformer"],
                notes="Test run for W&B integration"
            )
            
            # Log metrics during training
            for epoch in range(5):
                metrics = {
                    "epoch": epoch,
                    "loss": 2.5 - (epoch * 0.3) + (epoch * 0.05 * random.random()),
                    "accuracy": 0.6 + (epoch * 0.05) + (epoch * 0.01 * random.random()),
                    "learning_rate": 0.001 * (0.9 ** epoch)
                }
                
                await wandb_integration.log_metrics(metrics, step=epoch)
            
            # Create temporary model directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create dummy model files
                model_file = os.path.join(temp_dir, "model.json")
                with open(model_file, 'w') as f:
                    json.dump({"model_type": "kenny-agi", "version": "1.0.0"}, f)
                
                config_file = os.path.join(temp_dir, "config.yaml")
                with open(config_file, 'w') as f:
                    yaml.dump({"architecture": "transformer", "layers": 24}, f)
                
                # Log model artifacts
                artifact_name = await wandb_integration.log_model_artifacts(
                    model_path=temp_dir,
                    model_name="kenny-agi-test-model",
                    aliases=["v1.0", "latest"],
                    metadata={
                        "description": "Test AGI model for W&B integration",
                        "architecture": "transformer",
                        "parameters": "7B",
                        "training_duration": "4 hours"
                    }
                )
                
                if artifact_name:
                    print(f"Model artifact logged: {artifact_name}")
                
                # Log source code
                await wandb_integration.log_code(".")
                
                # Finish experiment
                await wandb_integration.finish_experiment(exit_code=0)
                
                # Test model retrieval
                model_metadata = await wandb_integration.get_model_metadata("kenny-agi-test-model")
                if model_metadata:
                    print(f"Retrieved model metadata: {model_metadata.model_id} v{model_metadata.version}")
                
                # List all models
                models = await wandb_integration.list_models()
                print(f"Found {len(models)} models in project")
                
                # Get project statistics
                stats = await wandb_integration.get_project_statistics()
                print(f"Project statistics: {json.dumps(stats, indent=2)}")
        
        except Exception as e:
            print(f"Test failed: {e}")
            raise
    
    import random
    from datetime import timedelta
    asyncio.run(main())