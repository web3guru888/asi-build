#!/usr/bin/env python3
"""
MLflow Integration for AGI Model Registry
Comprehensive integration with MLflow for model versioning, metadata, and lifecycle management
"""

import asyncio
import logging
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import mlflow
import mlflow.tracking
from mlflow.tracking import MlflowClient
from mlflow.entities import ViewType
from mlflow.store.artifact.runs_artifact_repo import RunsArtifactRepository
import tempfile
import shutil

@dataclass
class ModelMetadata:
    """Model metadata structure"""
    model_id: str
    version: str
    description: str
    tags: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    stage: str = "None"
    creation_timestamp: Optional[datetime] = None

@dataclass
class DeploymentInfo:
    """Deployment information"""
    environment: str
    endpoint: str
    status: str
    deployment_id: str
    timestamp: datetime
    metrics: Dict[str, Any] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)

class MLflowIntegration:
    """
    Comprehensive MLflow integration for AGI models
    """
    
    def __init__(self, tracking_uri: str, registry_uri: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Setup MLflow
        mlflow.set_tracking_uri(tracking_uri)
        if registry_uri:
            mlflow.set_registry_uri(registry_uri)
            
        self.client = MlflowClient()
        self.experiment_name = "agi-model-experiments"
        
        # Initialize experiment
        try:
            self.experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if self.experiment is None:
                self.experiment_id = mlflow.create_experiment(self.experiment_name)
                self.experiment = mlflow.get_experiment(self.experiment_id)
            else:
                self.experiment_id = self.experiment.experiment_id
        except Exception as e:
            self.logger.error(f"Failed to setup MLflow experiment: {e}")
            raise
            
        self.logger.info(f"MLflow integration initialized with experiment: {self.experiment_name}")
    
    async def register_model(self, model_path: str, model_metadata: ModelMetadata) -> str:
        """Register a new model version in MLflow"""
        self.logger.info(f"Registering model {model_metadata.model_id} version {model_metadata.version}")
        
        try:
            with mlflow.start_run(experiment_id=self.experiment_id) as run:
                # Log parameters
                for key, value in model_metadata.parameters.items():
                    mlflow.log_param(key, value)
                
                # Log metrics
                for key, value in model_metadata.metrics.items():
                    if isinstance(value, (int, float)):
                        mlflow.log_metric(key, value)
                
                # Log artifacts
                if os.path.exists(model_path):
                    mlflow.log_artifacts(model_path, "model")
                    
                    # Log model signature if available
                    await self._log_model_signature(model_path, run.info.run_id)
                
                # Set tags
                for key, value in model_metadata.tags.items():
                    mlflow.set_tag(key, value)
                
                # Additional AGI-specific tags
                mlflow.set_tag("model_type", "agi")
                mlflow.set_tag("framework", "kenny-agi")
                mlflow.set_tag("registration_timestamp", datetime.now().isoformat())
                
                # Register the model
                model_uri = f"runs:/{run.info.run_id}/model"
                
                try:
                    # Try to create a new registered model
                    self.client.create_registered_model(
                        name=model_metadata.model_id,
                        description=model_metadata.description
                    )
                except mlflow.exceptions.RestException as e:
                    if "RESOURCE_ALREADY_EXISTS" not in str(e):
                        raise
                
                # Create model version
                model_version = self.client.create_model_version(
                    name=model_metadata.model_id,
                    source=model_uri,
                    run_id=run.info.run_id,
                    description=f"Version {model_metadata.version}: {model_metadata.description}"
                )
                
                # Set version tags
                for key, value in model_metadata.tags.items():
                    self.client.set_model_version_tag(
                        name=model_metadata.model_id,
                        version=model_version.version,
                        key=key,
                        value=value
                    )
                
                self.logger.info(f"Model registered successfully: {model_metadata.model_id} v{model_version.version}")
                return model_version.version
                
        except Exception as e:
            self.logger.error(f"Failed to register model: {e}")
            raise
    
    async def _log_model_signature(self, model_path: str, run_id: str):
        """Log model signature and input/output schema"""
        try:
            # This would be implemented based on the specific model format
            # For now, we'll create a basic signature
            
            signature_info = {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"},
                        "max_length": {"type": "integer"},
                        "temperature": {"type": "number"}
                    },
                    "required": ["input"]
                },
                "output_schema": {
                    "type": "object", 
                    "properties": {
                        "output": {"type": "string"},
                        "confidence": {"type": "number"},
                        "metadata": {"type": "object"}
                    }
                }
            }
            
            # Log as artifact
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(signature_info, f, indent=2)
                temp_path = f.name
            
            mlflow.log_artifact(temp_path, "model_schema/signature.json")
            os.unlink(temp_path)
            
        except Exception as e:
            self.logger.warning(f"Failed to log model signature: {e}")
    
    async def get_model(self, model_id: str, version: Optional[str] = None, stage: Optional[str] = None) -> Optional[ModelMetadata]:
        """Get model metadata from MLflow"""
        try:
            if version:
                model_version = self.client.get_model_version(model_id, version)
            elif stage:
                model_versions = self.client.get_latest_versions(model_id, stages=[stage])
                if not model_versions:
                    return None
                model_version = model_versions[0]
            else:
                model_versions = self.client.get_latest_versions(model_id)
                if not model_versions:
                    return None
                model_version = model_versions[0]
            
            # Get run information
            run = self.client.get_run(model_version.run_id)
            
            # Extract metrics and parameters
            metrics = {k: v for k, v in run.data.metrics.items()}
            parameters = {k: v for k, v in run.data.params.items()}
            
            # Get tags
            tags = {}
            if hasattr(model_version, 'tags') and model_version.tags:
                tags.update(model_version.tags)
            if run.data.tags:
                tags.update(run.data.tags)
            
            return ModelMetadata(
                model_id=model_id,
                version=model_version.version,
                description=model_version.description or "",
                tags=tags,
                metrics=metrics,
                parameters=parameters,
                stage=model_version.current_stage,
                creation_timestamp=datetime.fromtimestamp(model_version.creation_timestamp / 1000)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get model {model_id}: {e}")
            return None
    
    async def list_models(self, filter_string: Optional[str] = None) -> List[ModelMetadata]:
        """List all registered models"""
        try:
            models = []
            registered_models = self.client.search_registered_models(filter_string=filter_string)
            
            for registered_model in registered_models:
                latest_versions = self.client.get_latest_versions(registered_model.name)
                
                for model_version in latest_versions:
                    try:
                        model_metadata = await self.get_model(
                            model_id=registered_model.name,
                            version=model_version.version
                        )
                        if model_metadata:
                            models.append(model_metadata)
                    except Exception as e:
                        self.logger.warning(f"Failed to get model version {model_version.version}: {e}")
            
            return models
            
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
            return []
    
    async def download_model(self, model_id: str, version: str, output_path: str) -> bool:
        """Download model artifacts from MLflow"""
        self.logger.info(f"Downloading model {model_id} version {version} to {output_path}")
        
        try:
            model_version = self.client.get_model_version(model_id, version)
            model_uri = f"models:/{model_id}/{version}"
            
            # Create output directory
            os.makedirs(output_path, exist_ok=True)
            
            # Download model artifacts
            local_path = mlflow.artifacts.download_artifacts(
                artifact_uri=model_uri,
                dst_path=output_path
            )
            
            # Download additional run artifacts
            run_id = model_version.run_id
            run_artifacts_path = os.path.join(output_path, "run_artifacts")
            os.makedirs(run_artifacts_path, exist_ok=True)
            
            artifacts = self.client.list_artifacts(run_id)
            for artifact in artifacts:
                if artifact.path != "model":  # Model already downloaded
                    try:
                        artifact_path = mlflow.artifacts.download_artifacts(
                            artifact_uri=f"runs:/{run_id}/{artifact.path}",
                            dst_path=run_artifacts_path
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to download artifact {artifact.path}: {e}")
            
            self.logger.info(f"Model downloaded successfully to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download model: {e}")
            return False
    
    async def promote_model(self, model_id: str, version: str, stage: str) -> bool:
        """Promote model to a specific stage"""
        self.logger.info(f"Promoting model {model_id} version {version} to {stage}")
        
        try:
            # Validate stage
            valid_stages = ["Staging", "Production", "Archived"]
            if stage not in valid_stages:
                raise ValueError(f"Invalid stage '{stage}'. Must be one of: {valid_stages}")
            
            # Transition model version stage
            self.client.transition_model_version_stage(
                name=model_id,
                version=version,
                stage=stage,
                archive_existing_versions=(stage == "Production")
            )
            
            # Add promotion metadata
            self.client.set_model_version_tag(
                name=model_id,
                version=version,
                key="promoted_at",
                value=datetime.now().isoformat()
            )
            
            self.client.set_model_version_tag(
                name=model_id,
                version=version,
                key="promoted_to",
                value=stage
            )
            
            self.logger.info(f"Model promoted successfully to {stage}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to promote model: {e}")
            return False
    
    async def log_deployment(self, model_id: str, version: str, deployment_info: DeploymentInfo) -> bool:
        """Log deployment information"""
        self.logger.info(f"Logging deployment for model {model_id} version {version}")
        
        try:
            # Get model version
            model_version = self.client.get_model_version(model_id, version)
            
            # Create deployment tags
            deployment_tags = {
                f"deployment_{deployment_info.environment}_endpoint": deployment_info.endpoint,
                f"deployment_{deployment_info.environment}_status": deployment_info.status,
                f"deployment_{deployment_info.environment}_id": deployment_info.deployment_id,
                f"deployment_{deployment_info.environment}_timestamp": deployment_info.timestamp.isoformat()
            }
            
            # Set deployment tags on model version
            for key, value in deployment_tags.items():
                self.client.set_model_version_tag(
                    name=model_id,
                    version=version,
                    key=key,
                    value=str(value)
                )
            
            # Log deployment metrics in a new run
            with mlflow.start_run(experiment_id=self.experiment_id) as run:
                # Set tags to link this run to the model deployment
                mlflow.set_tag("model_id", model_id)
                mlflow.set_tag("model_version", version)
                mlflow.set_tag("deployment_environment", deployment_info.environment)
                mlflow.set_tag("deployment_id", deployment_info.deployment_id)
                mlflow.set_tag("run_type", "deployment")
                
                # Log deployment metrics
                for key, value in deployment_info.metrics.items():
                    if isinstance(value, (int, float)):
                        mlflow.log_metric(f"deployment_{key}", value)
                
                # Log deployment configuration
                config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
                json.dump(deployment_info.configuration, config_file, indent=2)
                config_file.close()
                
                mlflow.log_artifact(config_file.name, f"deployment_{deployment_info.environment}/config.json")
                os.unlink(config_file.name)
            
            self.logger.info("Deployment information logged successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log deployment: {e}")
            return False
    
    async def get_model_deployments(self, model_id: str, version: str) -> List[DeploymentInfo]:
        """Get deployment information for a model version"""
        try:
            model_version = self.client.get_model_version(model_id, version)
            deployments = []
            
            if hasattr(model_version, 'tags') and model_version.tags:
                # Parse deployment tags
                environments = set()
                for tag_key in model_version.tags.keys():
                    if tag_key.startswith("deployment_") and tag_key.endswith("_endpoint"):
                        env = tag_key.split("_")[1]  # Extract environment name
                        environments.add(env)
                
                # Build deployment info for each environment
                for env in environments:
                    try:
                        endpoint_key = f"deployment_{env}_endpoint"
                        status_key = f"deployment_{env}_status"
                        id_key = f"deployment_{env}_id"
                        timestamp_key = f"deployment_{env}_timestamp"
                        
                        if all(key in model_version.tags for key in [endpoint_key, status_key, id_key, timestamp_key]):
                            deployment = DeploymentInfo(
                                environment=env,
                                endpoint=model_version.tags[endpoint_key],
                                status=model_version.tags[status_key],
                                deployment_id=model_version.tags[id_key],
                                timestamp=datetime.fromisoformat(model_version.tags[timestamp_key])
                            )
                            deployments.append(deployment)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse deployment info for environment {env}: {e}")
            
            return deployments
            
        except Exception as e:
            self.logger.error(f"Failed to get model deployments: {e}")
            return []
    
    async def log_performance_metrics(self, model_id: str, version: str, metrics: Dict[str, float], 
                                    environment: str, timestamp: Optional[datetime] = None) -> bool:
        """Log performance metrics for a deployed model"""
        try:
            timestamp = timestamp or datetime.now()
            
            with mlflow.start_run(experiment_id=self.experiment_id) as run:
                # Set run metadata
                mlflow.set_tag("model_id", model_id)
                mlflow.set_tag("model_version", version)
                mlflow.set_tag("environment", environment)
                mlflow.set_tag("run_type", "performance_monitoring")
                mlflow.set_tag("timestamp", timestamp.isoformat())
                
                # Log metrics
                for metric_name, metric_value in metrics.items():
                    if isinstance(metric_value, (int, float)):
                        mlflow.log_metric(metric_name, metric_value, step=int(timestamp.timestamp()))
                
                self.logger.info(f"Performance metrics logged for {model_id} v{version} in {environment}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to log performance metrics: {e}")
            return False
    
    async def get_model_lineage(self, model_id: str, version: str) -> Dict[str, Any]:
        """Get model lineage and provenance information"""
        try:
            model_version = self.client.get_model_version(model_id, version)
            run = self.client.get_run(model_version.run_id)
            
            # Get parent runs (if any)
            parent_runs = []
            if run.data.tags.get("mlflow.parentRunId"):
                try:
                    parent_run = self.client.get_run(run.data.tags["mlflow.parentRunId"])
                    parent_runs.append({
                        "run_id": parent_run.info.run_id,
                        "experiment_id": parent_run.info.experiment_id,
                        "start_time": parent_run.info.start_time,
                        "tags": dict(parent_run.data.tags)
                    })
                except Exception:
                    pass
            
            # Get child runs
            child_runs = []
            experiment_runs = self.client.search_runs(
                experiment_ids=[run.info.experiment_id],
                filter_string=f"tags.mlflow.parentRunId = '{run.info.run_id}'"
            )
            
            for child_run in experiment_runs:
                child_runs.append({
                    "run_id": child_run.info.run_id,
                    "start_time": child_run.info.start_time,
                    "tags": dict(child_run.data.tags)
                })
            
            # Get dataset information
            datasets = []
            if "dataset_name" in run.data.tags:
                datasets.append({
                    "name": run.data.tags["dataset_name"],
                    "version": run.data.tags.get("dataset_version", "unknown"),
                    "source": run.data.tags.get("dataset_source", "unknown")
                })
            
            lineage = {
                "model_id": model_id,
                "version": version,
                "run_id": model_version.run_id,
                "creation_timestamp": model_version.creation_timestamp,
                "parent_runs": parent_runs,
                "child_runs": child_runs,
                "datasets": datasets,
                "parameters": dict(run.data.params),
                "tags": dict(run.data.tags),
                "artifacts": [artifact.path for artifact in self.client.list_artifacts(run.info.run_id)]
            }
            
            return lineage
            
        except Exception as e:
            self.logger.error(f"Failed to get model lineage: {e}")
            return {}
    
    async def search_models(self, query: Dict[str, Any]) -> List[ModelMetadata]:
        """Search models based on query criteria"""
        try:
            # Build filter string for MLflow
            filter_conditions = []
            
            if "stage" in query:
                # This requires searching through model versions
                pass  # Will be handled separately
            
            if "tags" in query:
                for key, value in query["tags"].items():
                    filter_conditions.append(f"tag.{key} = '{value}'")
            
            if "name" in query:
                filter_conditions.append(f"name LIKE '%{query['name']}%'")
            
            filter_string = " AND ".join(filter_conditions) if filter_conditions else None
            
            # Search registered models
            registered_models = self.client.search_registered_models(filter_string=filter_string)
            
            models = []
            for registered_model in registered_models:
                # Get all versions or filter by stage
                if "stage" in query:
                    model_versions = self.client.get_latest_versions(
                        registered_model.name, 
                        stages=[query["stage"]]
                    )
                else:
                    model_versions = self.client.get_latest_versions(registered_model.name)
                
                for model_version in model_versions:
                    model_metadata = await self.get_model(
                        model_id=registered_model.name,
                        version=model_version.version
                    )
                    
                    if model_metadata:
                        # Apply additional filters
                        if self._matches_query(model_metadata, query):
                            models.append(model_metadata)
            
            return models
            
        except Exception as e:
            self.logger.error(f"Failed to search models: {e}")
            return []
    
    def _matches_query(self, model: ModelMetadata, query: Dict[str, Any]) -> bool:
        """Check if model matches additional query criteria"""
        
        # Filter by metrics
        if "metrics" in query:
            for metric_name, metric_criteria in query["metrics"].items():
                if metric_name not in model.metrics:
                    return False
                
                model_value = model.metrics[metric_name]
                
                if isinstance(metric_criteria, dict):
                    if "min" in metric_criteria and model_value < metric_criteria["min"]:
                        return False
                    if "max" in metric_criteria and model_value > metric_criteria["max"]:
                        return False
                else:
                    if model_value != metric_criteria:
                        return False
        
        # Filter by creation time
        if "created_after" in query:
            if model.creation_timestamp < query["created_after"]:
                return False
        
        if "created_before" in query:
            if model.creation_timestamp > query["created_before"]:
                return False
        
        return True
    
    async def delete_model_version(self, model_id: str, version: str) -> bool:
        """Delete a specific model version"""
        try:
            self.client.delete_model_version(model_id, version)
            self.logger.info(f"Model version {model_id} v{version} deleted successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete model version: {e}")
            return False
    
    async def archive_model(self, model_id: str, version: str) -> bool:
        """Archive a model version"""
        return await self.promote_model(model_id, version, "Archived")
    
    async def get_model_statistics(self) -> Dict[str, Any]:
        """Get overall model registry statistics"""
        try:
            registered_models = self.client.search_registered_models()
            
            total_models = len(registered_models)
            total_versions = 0
            stages_count = {"None": 0, "Staging": 0, "Production": 0, "Archived": 0}
            
            for registered_model in registered_models:
                model_versions = self.client.get_latest_versions(registered_model.name)
                total_versions += len(model_versions)
                
                for version in model_versions:
                    stages_count[version.current_stage] = stages_count.get(version.current_stage, 0) + 1
            
            return {
                "total_registered_models": total_models,
                "total_model_versions": total_versions,
                "stages_distribution": stages_count,
                "tracking_uri": mlflow.get_tracking_uri(),
                "registry_uri": mlflow.get_registry_uri()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get model statistics: {e}")
            return {}

# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Initialize MLflow integration
        mlflow_integration = MLflowIntegration(
            tracking_uri="http://localhost:5000",
            registry_uri="http://localhost:5000"
        )
        
        # Test model registration
        model_metadata = ModelMetadata(
            model_id="kenny-agi-test",
            version="1.0.0",
            description="Test AGI model for MLflow integration",
            tags={
                "framework": "kenny-agi",
                "architecture": "transformer",
                "training_data": "kenny-corpus-v1"
            },
            metrics={
                "accuracy": 0.89,
                "latency_p95": 150.0,
                "throughput_rps": 100.0
            },
            parameters={
                "learning_rate": 0.001,
                "batch_size": 32,
                "epochs": 10
            }
        )
        
        # Create temporary model directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create dummy model file
            model_file = os.path.join(temp_dir, "model.json")
            with open(model_file, 'w') as f:
                json.dump({"model_type": "kenny-agi", "version": "1.0.0"}, f)
            
            try:
                # Register model
                version = await mlflow_integration.register_model(temp_dir, model_metadata)
                print(f"Model registered with version: {version}")
                
                # Get model
                retrieved_model = await mlflow_integration.get_model("kenny-agi-test", version)
                if retrieved_model:
                    print(f"Retrieved model: {retrieved_model.model_id} v{retrieved_model.version}")
                
                # Promote to staging
                success = await mlflow_integration.promote_model("kenny-agi-test", version, "Staging")
                if success:
                    print("Model promoted to Staging")
                
                # Log deployment
                deployment_info = DeploymentInfo(
                    environment="staging",
                    endpoint="https://staging.kenny-agi.example.com",
                    status="deployed",
                    deployment_id="deploy-123",
                    timestamp=datetime.now(),
                    metrics={"cpu_usage": 45.0, "memory_usage": 60.0},
                    configuration={"replicas": 3, "timeout": 30}
                )
                
                deployment_logged = await mlflow_integration.log_deployment("kenny-agi-test", version, deployment_info)
                if deployment_logged:
                    print("Deployment information logged")
                
                # Get model statistics
                stats = await mlflow_integration.get_model_statistics()
                print(f"Registry statistics: {json.dumps(stats, indent=2)}")
                
            except Exception as e:
                print(f"Test failed: {e}")
    
    asyncio.run(main())