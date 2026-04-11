#!/usr/bin/env python3
"""
Neptune Integration for AGI Model Registry
Comprehensive integration with Neptune for experiment tracking, model management, and metadata
"""

import asyncio
import logging
import json
import os
import tempfile
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import neptune
from neptune.types import File
import pickle
import yaml
import hashlib

@dataclass
class NeptuneModelMetadata:
    """Neptune Model metadata structure"""
    model_id: str
    version: str
    description: str
    project: str
    tags: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    stage: str = "none"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class NeptuneRun:
    """Neptune run data structure"""
    run_id: str
    project: str
    state: str
    properties: Dict[str, Any]
    parameters: Dict[str, Any] 
    metrics: Dict[str, float]
    tags: List[str]
    created_at: datetime
    updated_at: datetime

class NeptuneIntegration:
    """
    Comprehensive Neptune integration for AGI models
    """
    
    def __init__(self, project: str, api_token: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.project = project
        
        # Initialize Neptune
        if api_token:
            os.environ['NEPTUNE_API_TOKEN'] = api_token
        
        self.current_run: Optional[neptune.Run] = None
        self.model_registry = {}
        
        self.logger.info(f"Neptune integration initialized for project: {project}")
    
    async def start_experiment(self, experiment_name: str, parameters: Dict[str, Any],
                              tags: List[str] = None, description: str = None) -> str:
        """Start a new Neptune experiment run"""
        self.logger.info(f"Starting Neptune experiment: {experiment_name}")
        
        try:
            # Initialize run
            self.current_run = neptune.init_run(
                project=self.project,
                name=experiment_name,
                description=description,
                tags=tags or [],
                source_files=["*.py"],  # Track Python files by default
                capture_stdout=True,
                capture_stderr=True,
                capture_hardware_metrics=True
            )
            
            # Log parameters
            for key, value in parameters.items():
                self.current_run[f"parameters/{key}"] = value
            
            # Log system information
            await self._log_system_info()
            
            run_id = self.current_run._short_id
            self.logger.info(f"Neptune run started: {run_id}")
            
            return run_id
            
        except Exception as e:
            self.logger.error(f"Failed to start Neptune experiment: {e}")
            raise
    
    async def _log_system_info(self):
        """Log system information to Neptune"""
        try:
            if not self.current_run:
                return
                
            self.current_run["system/framework"] = "kenny-agi"
            self.current_run["system/timestamp"] = datetime.now().isoformat()
            self.current_run["system/python_version"] = os.sys.version
            
            # Log environment variables (filtered)
            env_vars = {k: v for k, v in os.environ.items() 
                       if not k.startswith(('NEPTUNE_', 'SECRET_', 'PASSWORD_', 'TOKEN_'))}
            
            for key, value in list(env_vars.items())[:10]:  # Limit to first 10
                self.current_run[f"system/env/{key}"] = value
                
        except Exception as e:
            self.logger.warning(f"Failed to log system info: {e}")
    
    async def log_metrics(self, metrics: Dict[str, Any], step: Optional[int] = None) -> bool:
        """Log metrics to current Neptune run"""
        try:
            if not self.current_run:
                self.logger.warning("No active Neptune run. Call start_experiment() first.")
                return False
            
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    if step is not None:
                        self.current_run[f"metrics/{key}"].append(value, step=step)
                    else:
                        self.current_run[f"metrics/{key}"].append(value)
                else:
                    # Log non-numeric data as properties
                    self.current_run[f"properties/{key}"] = str(value)
            
            self.logger.debug(f"Logged {len(metrics)} metrics to Neptune")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log metrics: {e}")
            return False
    
    async def log_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Log parameters to current Neptune run"""
        try:
            if not self.current_run:
                self.logger.warning("No active Neptune run.")
                return False
            
            for key, value in parameters.items():
                self.current_run[f"parameters/{key}"] = value
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log parameters: {e}")
            return False
    
    async def log_artifacts(self, artifacts: Dict[str, str], artifact_type: str = "file") -> bool:
        """Log artifacts to Neptune"""
        try:
            if not self.current_run:
                self.logger.warning("No active Neptune run.")
                return False
            
            for name, path in artifacts.items():
                if os.path.exists(path):
                    if os.path.isfile(path):
                        self.current_run[f"artifacts/{artifact_type}/{name}"].upload(File(path))
                    elif os.path.isdir(path):
                        # Upload directory contents
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                relative_path = os.path.relpath(file_path, path)
                                self.current_run[f"artifacts/{artifact_type}/{name}/{relative_path}"].upload(File(file_path))
                    
                    self.logger.info(f"Uploaded artifact: {name}")
                else:
                    self.logger.warning(f"Artifact path not found: {path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log artifacts: {e}")
            return False
    
    async def log_model(self, model_path: str, model_name: str, 
                       metadata: Dict[str, Any] = None, stage: str = "none") -> Optional[str]:
        """Log model to Neptune"""
        self.logger.info(f"Logging model: {model_name}")
        
        try:
            if not self.current_run:
                self.logger.warning("No active Neptune run.")
                return None
            
            # Create model version identifier
            model_version = metadata.get("version", datetime.now().strftime("%Y%m%d_%H%M%S"))
            model_id = f"{model_name}_v{model_version}"
            
            # Log model files
            if os.path.exists(model_path):
                await self.log_artifacts({"model": model_path}, "models")
                
                # Calculate model hash for integrity
                model_hash = await self._calculate_path_hash(model_path)
                self.current_run[f"models/{model_name}/hash"] = model_hash
            
            # Log model metadata
            self.current_run[f"models/{model_name}/name"] = model_name
            self.current_run[f"models/{model_name}/version"] = model_version
            self.current_run[f"models/{model_name}/stage"] = stage
            self.current_run[f"models/{model_name}/created_at"] = datetime.now().isoformat()
            
            if metadata:
                for key, value in metadata.items():
                    self.current_run[f"models/{model_name}/metadata/{key}"] = value
            
            # Store in local registry for tracking
            self.model_registry[model_id] = {
                "name": model_name,
                "version": model_version,
                "stage": stage,
                "run_id": self.current_run._short_id,
                "metadata": metadata or {},
                "created_at": datetime.now()
            }
            
            self.logger.info(f"Model logged: {model_id}")
            return model_id
            
        except Exception as e:
            self.logger.error(f"Failed to log model: {e}")
            return None
    
    async def _calculate_path_hash(self, path: str) -> str:
        """Calculate hash of file or directory"""
        hasher = hashlib.sha256()
        
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
        elif os.path.isdir(path):
            for root, dirs, files in sorted(os.walk(path)):
                for file in sorted(files):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hasher.update(chunk)
        
        return hasher.hexdigest()
    
    async def log_dataset(self, dataset_path: str, dataset_name: str, 
                         metadata: Dict[str, Any] = None) -> bool:
        """Log dataset to Neptune"""
        try:
            if not self.current_run:
                return False
            
            # Log dataset files
            await self.log_artifacts({"dataset": dataset_path}, "datasets")
            
            # Log dataset metadata
            self.current_run[f"datasets/{dataset_name}/name"] = dataset_name
            self.current_run[f"datasets/{dataset_name}/path"] = dataset_path
            self.current_run[f"datasets/{dataset_name}/created_at"] = datetime.now().isoformat()
            
            if metadata:
                for key, value in metadata.items():
                    self.current_run[f"datasets/{dataset_name}/metadata/{key}"] = value
            
            # Calculate dataset statistics if it's a directory
            if os.path.isdir(dataset_path):
                file_count = sum(len(files) for _, _, files in os.walk(dataset_path))
                total_size = sum(os.path.getsize(os.path.join(root, file)) 
                               for root, _, files in os.walk(dataset_path) 
                               for file in files)
                
                self.current_run[f"datasets/{dataset_name}/stats/file_count"] = file_count
                self.current_run[f"datasets/{dataset_name}/stats/total_size_mb"] = total_size / (1024 * 1024)
            
            self.logger.info(f"Dataset logged: {dataset_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log dataset: {e}")
            return False
    
    async def log_code_snapshot(self, source_path: str = ".", exclude_patterns: List[str] = None) -> bool:
        """Log code snapshot to Neptune"""
        try:
            if not self.current_run:
                return False
            
            # Default exclusions
            default_excludes = [
                "__pycache__", ".git", "*.pyc", "*.pyo", "*.log", 
                ".neptune", "wandb", ".wandb", "*.tmp", "*.pkl", "*.pt"
            ]
            
            exclude_patterns = exclude_patterns or []
            all_excludes = default_excludes + exclude_patterns
            
            # Create temporary archive of source code
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                import zipfile
                
                with zipfile.ZipFile(tmp_file.name, 'w') as zipf:
                    for root, dirs, files in os.walk(source_path):
                        # Filter directories
                        dirs[:] = [d for d in dirs if not any(pattern in d for pattern in all_excludes)]
                        
                        for file in files:
                            if not any(pattern in file for pattern in all_excludes):
                                file_path = os.path.join(root, file)
                                arc_name = os.path.relpath(file_path, source_path)
                                zipf.write(file_path, arc_name)
                
                # Upload code snapshot
                self.current_run["source_code/snapshot"].upload(File(tmp_file.name))
                
                # Cleanup
                os.unlink(tmp_file.name)
            
            self.logger.info("Source code snapshot logged")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log code snapshot: {e}")
            return False
    
    async def finish_experiment(self) -> bool:
        """Finish current Neptune run"""
        try:
            if self.current_run:
                self.current_run.stop()
                self.current_run = None
                self.logger.info("Neptune run finished")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to finish Neptune run: {e}")
            return False
    
    async def get_run_data(self, run_id: str) -> Optional[NeptuneRun]:
        """Get run data from Neptune"""
        try:
            run = neptune.init_run(
                project=self.project,
                with_id=run_id,
                mode="read-only"
            )
            
            # Fetch run data
            properties = {}
            parameters = {}
            metrics = {}
            
            try:
                # Get all logged data
                run_data = run.get_structure()
                
                # Extract properties
                if "properties" in run_data:
                    for key in run_data["properties"]:
                        try:
                            properties[key] = run[f"properties/{key}"].fetch()
                        except:
                            pass
                
                # Extract parameters
                if "parameters" in run_data:
                    for key in run_data["parameters"]:
                        try:
                            parameters[key] = run[f"parameters/{key}"].fetch()
                        except:
                            pass
                
                # Extract metrics (get last values)
                if "metrics" in run_data:
                    for key in run_data["metrics"]:
                        try:
                            metric_values = run[f"metrics/{key}"].fetch_values()
                            if metric_values:
                                metrics[key] = metric_values["value"].iloc[-1]
                        except:
                            pass
                
                neptune_run = NeptuneRun(
                    run_id=run_id,
                    project=self.project,
                    state=run["sys/state"].fetch(),
                    properties=properties,
                    parameters=parameters,
                    metrics=metrics,
                    tags=run["sys/tags"].fetch() if "sys/tags" in run else [],
                    created_at=run["sys/creation_time"].fetch(),
                    updated_at=run["sys/modification_time"].fetch()
                )
                
                run.stop()
                return neptune_run
                
            except Exception as e:
                run.stop()
                raise e
                
        except Exception as e:
            self.logger.error(f"Failed to get run data: {e}")
            return None
    
    async def get_model_metadata(self, model_name: str, run_id: Optional[str] = None) -> Optional[NeptuneModelMetadata]:
        """Get model metadata from Neptune"""
        try:
            if run_id:
                run = neptune.init_run(
                    project=self.project,
                    with_id=run_id,
                    mode="read-only"
                )
            else:
                # Find most recent run with this model
                # This would require Neptune's querying capabilities
                self.logger.warning("Model search without run_id not fully implemented")
                return None
            
            try:
                # Check if model exists in this run
                run_structure = run.get_structure()
                
                if "models" not in run_structure or model_name not in run_structure["models"]:
                    return None
                
                # Extract model data
                model_data = run_structure["models"][model_name]
                
                metadata = NeptuneModelMetadata(
                    model_id=model_name,
                    version=run[f"models/{model_name}/version"].fetch(),
                    description=run[f"models/{model_name}/metadata/description"].fetch() if "metadata" in model_data and "description" in model_data["metadata"] else "",
                    project=self.project,
                    tags=run["sys/tags"].fetch() if "sys/tags" in run else [],
                    stage=run[f"models/{model_name}/stage"].fetch(),
                    created_at=datetime.fromisoformat(run[f"models/{model_name}/created_at"].fetch())
                )
                
                # Extract metadata
                if "metadata" in model_data:
                    for key in model_data["metadata"]:
                        try:
                            value = run[f"models/{model_name}/metadata/{key}"].fetch()
                            metadata.properties[key] = value
                        except:
                            pass
                
                run.stop()
                return metadata
                
            except Exception as e:
                run.stop()
                raise e
                
        except Exception as e:
            self.logger.error(f"Failed to get model metadata: {e}")
            return None
    
    async def download_model_artifact(self, run_id: str, model_name: str, output_path: str) -> bool:
        """Download model artifact from Neptune"""
        self.logger.info(f"Downloading model {model_name} from run {run_id}")
        
        try:
            run = neptune.init_run(
                project=self.project,
                with_id=run_id,
                mode="read-only"
            )
            
            try:
                # Create output directory
                os.makedirs(output_path, exist_ok=True)
                
                # Download model artifacts
                run_structure = run.get_structure()
                
                if "artifacts" in run_structure and "models" in run_structure["artifacts"]:
                    if "model" in run_structure["artifacts"]["models"]:
                        # Download all model files
                        model_artifacts = run_structure["artifacts"]["models"]["model"]
                        
                        for artifact_path in model_artifacts:
                            try:
                                artifact_data = run[f"artifacts/models/model/{artifact_path}"].download(output_path)
                                self.logger.info(f"Downloaded: {artifact_path}")
                            except Exception as e:
                                self.logger.warning(f"Failed to download {artifact_path}: {e}")
                
                run.stop()
                self.logger.info(f"Model downloaded to: {output_path}")
                return True
                
            except Exception as e:
                run.stop()
                raise e
                
        except Exception as e:
            self.logger.error(f"Failed to download model artifact: {e}")
            return False
    
    async def update_model_stage(self, run_id: str, model_name: str, new_stage: str) -> bool:
        """Update model stage"""
        try:
            # Neptune doesn't support direct model stage updates on closed runs
            # This would typically be done by creating a new run or using model registry features
            
            # For now, we'll track stage changes in the local registry
            model_key = f"{model_name}_run_{run_id}"
            
            if model_key in self.model_registry:
                self.model_registry[model_key]["stage"] = new_stage
                self.model_registry[model_key]["stage_updated_at"] = datetime.now()
                
                self.logger.info(f"Model stage updated to {new_stage} (tracked locally)")
                return True
            else:
                self.logger.warning(f"Model {model_key} not found in local registry")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update model stage: {e}")
            return False
    
    async def log_deployment_info(self, model_name: str, environment: str, 
                                 deployment_data: Dict[str, Any]) -> bool:
        """Log deployment information"""
        try:
            # Create deployment tracking run
            deployment_run = neptune.init_run(
                project=self.project,
                name=f"deployment-{model_name}-{environment}",
                description=f"Deployment of {model_name} to {environment}",
                tags=["deployment", environment, model_name]
            )
            
            # Log deployment data
            deployment_run["deployment/model_name"] = model_name
            deployment_run["deployment/environment"] = environment
            deployment_run["deployment/timestamp"] = datetime.now().isoformat()
            
            for key, value in deployment_data.items():
                if isinstance(value, (int, float)):
                    deployment_run[f"deployment/metrics/{key}"] = value
                else:
                    deployment_run[f"deployment/info/{key}"] = str(value)
            
            deployment_run.stop()
            self.logger.info(f"Deployment info logged for {model_name} in {environment}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log deployment info: {e}")
            return False
    
    async def track_model_performance(self, model_name: str, environment: str, 
                                    performance_metrics: Dict[str, float]) -> bool:
        """Track model performance in production"""
        try:
            # Create performance tracking run
            perf_run = neptune.init_run(
                project=self.project,
                name=f"performance-{model_name}-{environment}",
                description=f"Performance tracking for {model_name} in {environment}",
                tags=["performance", "monitoring", environment, model_name]
            )
            
            # Log performance metrics
            perf_run["monitoring/model_name"] = model_name
            perf_run["monitoring/environment"] = environment
            perf_run["monitoring/timestamp"] = datetime.now().isoformat()
            
            for metric_name, metric_value in performance_metrics.items():
                perf_run[f"monitoring/metrics/{metric_name}"].append(metric_value)
            
            perf_run.stop()
            self.logger.info(f"Performance metrics tracked for {model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to track performance metrics: {e}")
            return False
    
    async def compare_models(self, run_ids: List[str], comparison_metrics: List[str]) -> Dict[str, Any]:
        """Compare models across multiple runs"""
        try:
            comparison_data = {}
            run_data = []
            
            for run_id in run_ids:
                run = await self.get_run_data(run_id)
                if run:
                    run_data.append(run)
            
            if not run_data:
                return {"error": "No valid runs found"}
            
            # Compare metrics
            metric_comparison = {}
            for metric in comparison_metrics:
                metric_values = []
                for run in run_data:
                    if metric in run.metrics:
                        metric_values.append({
                            "run_id": run.run_id,
                            "value": run.metrics[metric]
                        })
                
                if metric_values:
                    # Find best performing
                    best_run = max(metric_values, key=lambda x: x["value"])
                    worst_run = min(metric_values, key=lambda x: x["value"])
                    
                    metric_comparison[metric] = {
                        "values": metric_values,
                        "best": best_run,
                        "worst": worst_run,
                        "range": best_run["value"] - worst_run["value"]
                    }
            
            comparison_data = {
                "runs_compared": len(run_data),
                "run_ids": [run.run_id for run in run_data],
                "metric_comparison": metric_comparison,
                "comparison_timestamp": datetime.now().isoformat()
            }
            
            return comparison_data
            
        except Exception as e:
            self.logger.error(f"Failed to compare models: {e}")
            return {"error": str(e)}
    
    async def get_project_statistics(self) -> Dict[str, Any]:
        """Get project-level statistics"""
        try:
            # Note: This requires Neptune's API for listing runs
            # For now, we'll return local registry statistics
            
            total_models = len(self.model_registry)
            stages = {}
            
            for model_data in self.model_registry.values():
                stage = model_data.get("stage", "none")
                stages[stage] = stages.get(stage, 0) + 1
            
            return {
                "project": self.project,
                "total_models_tracked": total_models,
                "stage_distribution": stages,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get project statistics: {e}")
            return {"error": str(e)}
    
    async def cleanup_old_runs(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """Cleanup old runs (placeholder - requires Neptune API)"""
        try:
            # This would require Neptune's management API
            # For now, return a placeholder response
            
            self.logger.warning("Cleanup functionality requires Neptune management API access")
            
            return {
                "status": "not_implemented",
                "message": "Cleanup requires Neptune management API access",
                "suggestion": "Use Neptune web interface or management API for cleanup"
            }
            
        except Exception as e:
            self.logger.error(f"Cleanup operation failed: {e}")
            return {"error": str(e)}

# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Initialize Neptune integration
        neptune_integration = NeptuneIntegration(
            project="kenny-ai-team/kenny-agi-test"
        )
        
        try:
            # Start experiment
            run_id = await neptune_integration.start_experiment(
                experiment_name="test-agi-training",
                parameters={
                    "learning_rate": 0.001,
                    "batch_size": 32,
                    "epochs": 10,
                    "model_architecture": "transformer",
                    "dataset": "kenny-corpus-v1"
                },
                tags=["test", "agi", "transformer"],
                description="Test run for Neptune integration"
            )
            
            # Log training metrics
            for epoch in range(5):
                metrics = {
                    "epoch": epoch,
                    "loss": 2.5 - (epoch * 0.3),
                    "accuracy": 0.6 + (epoch * 0.05),
                    "learning_rate": 0.001 * (0.9 ** epoch),
                    "validation_loss": 2.3 - (epoch * 0.25)
                }
                
                await neptune_integration.log_metrics(metrics, step=epoch)
            
            # Create temporary model for testing
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create dummy model files
                model_file = os.path.join(temp_dir, "model.json")
                with open(model_file, 'w') as f:
                    json.dump({"model_type": "kenny-agi", "version": "1.0.0"}, f)
                
                config_file = os.path.join(temp_dir, "config.yaml")
                with open(config_file, 'w') as f:
                    yaml.dump({"architecture": "transformer", "layers": 24}, f)
                
                # Log model
                model_id = await neptune_integration.log_model(
                    model_path=temp_dir,
                    model_name="kenny-agi-test-model",
                    metadata={
                        "description": "Test AGI model for Neptune integration",
                        "architecture": "transformer",
                        "parameters": "7B",
                        "version": "1.0.0"
                    },
                    stage="staging"
                )
                
                if model_id:
                    print(f"Model logged: {model_id}")
                
                # Log dataset
                dataset_logged = await neptune_integration.log_dataset(
                    dataset_path=temp_dir,
                    dataset_name="test-dataset",
                    metadata={
                        "description": "Test dataset for integration",
                        "size": "100MB",
                        "type": "text"
                    }
                )
                
                if dataset_logged:
                    print("Dataset logged successfully")
                
                # Log code snapshot
                await neptune_integration.log_code_snapshot()
                
                # Finish experiment
                await neptune_integration.finish_experiment()
                
                # Test retrieving run data
                run_data = await neptune_integration.get_run_data(run_id)
                if run_data:
                    print(f"Retrieved run data: {run_data.run_id}")
                    print(f"Metrics: {list(run_data.metrics.keys())}")
                
                # Get project statistics
                stats = await neptune_integration.get_project_statistics()
                print(f"Project statistics: {json.dumps(stats, indent=2)}")
        
        except Exception as e:
            print(f"Test failed: {e}")
            raise
    
    asyncio.run(main())