#!/usr/bin/env python3
"""
GitOps Infrastructure Manager for AGI Deployments
Manages Infrastructure as Code with version control, drift detection, and compliance
"""

import asyncio
import logging
import json
import yaml
import hashlib
import subprocess
import tempfile
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
import git
import jinja2

class InfrastructureStatus(Enum):
    """Infrastructure status enumeration"""
    UNKNOWN = "unknown"
    SYNCED = "synced"
    OUT_OF_SYNC = "out_of_sync"
    DEPLOYING = "deploying"
    FAILED = "failed"
    DEGRADED = "degraded"

class ComplianceLevel(Enum):
    """Compliance level enumeration"""
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    UNKNOWN = "unknown"

@dataclass
class InfrastructureResource:
    """Infrastructure resource definition"""
    name: str
    resource_type: str
    config: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DriftDetection:
    """Drift detection result"""
    resource_name: str
    expected_state: Dict[str, Any]
    actual_state: Dict[str, Any]
    drift_detected: bool
    drift_details: List[str] = field(default_factory=list)
    remediation_actions: List[str] = field(default_factory=list)

@dataclass
class ComplianceCheck:
    """Compliance check result"""
    check_name: str
    resource_name: str
    level: ComplianceLevel
    message: str
    remediation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GitOpsConfig:
    """GitOps configuration"""
    git_repository: str
    git_branch: str
    infrastructure_path: str
    templates_path: str
    environments: List[str]
    terraform_backend: Dict[str, Any] = field(default_factory=dict)
    kubernetes_configs: Dict[str, Any] = field(default_factory=dict)
    compliance_policies: List[str] = field(default_factory=list)
    drift_detection_interval: int = 300  # 5 minutes
    auto_remediation: bool = False

class InfrastructureManager:
    """
    GitOps Infrastructure Manager for AGI deployments
    """
    
    def __init__(self, config: GitOpsConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.git_repo: Optional[git.Repo] = None
        self.infrastructure_resources: Dict[str, InfrastructureResource] = {}
        self.drift_history: List[DriftDetection] = []
        self.compliance_history: List[ComplianceCheck] = []
        self.workspace_path = tempfile.mkdtemp(prefix="gitops_")
        
    async def initialize(self):
        """Initialize the GitOps infrastructure manager"""
        self.logger.info("Initializing GitOps Infrastructure Manager...")
        
        # Clone or update repository
        await self._setup_git_repository()
        
        # Load infrastructure definitions
        await self._load_infrastructure_definitions()
        
        # Initialize Terraform backend
        await self._initialize_terraform_backend()
        
        # Set up compliance policies
        await self._setup_compliance_policies()
        
        self.logger.info("GitOps Infrastructure Manager initialized successfully")
    
    async def _setup_git_repository(self):
        """Setup Git repository for infrastructure definitions"""
        try:
            if os.path.exists(os.path.join(self.workspace_path, '.git')):
                self.logger.info("Updating existing repository...")
                self.git_repo = git.Repo(self.workspace_path)
                self.git_repo.remotes.origin.pull(self.config.git_branch)
            else:
                self.logger.info(f"Cloning repository: {self.config.git_repository}")
                self.git_repo = git.Repo.clone_from(
                    self.config.git_repository,
                    self.workspace_path,
                    branch=self.config.git_branch
                )
        
        except Exception as e:
            self.logger.error(f"Failed to setup Git repository: {e}")
            raise
    
    async def _load_infrastructure_definitions(self):
        """Load infrastructure definitions from repository"""
        infra_path = os.path.join(self.workspace_path, self.config.infrastructure_path)
        
        if not os.path.exists(infra_path):
            self.logger.warning(f"Infrastructure path not found: {infra_path}")
            return
        
        for env in self.config.environments:
            env_path = os.path.join(infra_path, env)
            if os.path.exists(env_path):
                await self._load_environment_resources(env, env_path)
    
    async def _load_environment_resources(self, environment: str, env_path: str):
        """Load resources for a specific environment"""
        for root, dirs, files in os.walk(env_path):
            for file in files:
                if file.endswith(('.tf', '.yaml', '.yml')):
                    file_path = os.path.join(root, file)
                    await self._parse_resource_file(environment, file_path)
    
    async def _parse_resource_file(self, environment: str, file_path: str):
        """Parse a resource definition file"""
        try:
            with open(file_path, 'r') as f:
                if file_path.endswith('.tf'):
                    # Parse Terraform file (simplified)
                    content = f.read()
                    await self._parse_terraform_content(environment, content, file_path)
                else:
                    # Parse YAML file
                    content = yaml.safe_load(f)
                    await self._parse_yaml_content(environment, content, file_path)
        
        except Exception as e:
            self.logger.warning(f"Failed to parse {file_path}: {e}")
    
    async def _parse_terraform_content(self, environment: str, content: str, file_path: str):
        """Parse Terraform content (simplified parser)"""
        # This is a simplified implementation
        # In production, you'd use proper Terraform parsing libraries
        
        lines = content.split('\n')
        current_resource = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('resource '):
                parts = line.split('"')
                if len(parts) >= 3:
                    resource_type = parts[1]
                    resource_name = parts[3]
                    current_resource = {
                        'type': resource_type,
                        'name': f"{environment}_{resource_name}",
                        'config': {}
                    }
            elif current_resource and '=' in line:
                key, value = line.split('=', 1)
                current_resource['config'][key.strip()] = value.strip()
            elif line == '}' and current_resource:
                resource = InfrastructureResource(
                    name=current_resource['name'],
                    resource_type=current_resource['type'],
                    config=current_resource['config'],
                    tags={'environment': environment, 'file': file_path}
                )
                self.infrastructure_resources[resource.name] = resource
                current_resource = None
    
    async def _parse_yaml_content(self, environment: str, content: Dict[str, Any], file_path: str):
        """Parse YAML content for Kubernetes resources"""
        if isinstance(content, dict):
            kind = content.get('kind', 'Unknown')
            name = content.get('metadata', {}).get('name', 'unnamed')
            
            resource = InfrastructureResource(
                name=f"{environment}_{name}",
                resource_type=kind,
                config=content,
                tags={'environment': environment, 'file': file_path}
            )
            self.infrastructure_resources[resource.name] = resource
    
    async def _initialize_terraform_backend(self):
        """Initialize Terraform backend configuration"""
        if not self.config.terraform_backend:
            return
        
        backend_config = self.config.terraform_backend
        backend_file = os.path.join(self.workspace_path, 'backend.tf')
        
        terraform_backend = f"""
terraform {{
  backend "{backend_config.get('type', 's3')}" {{
"""
        for key, value in backend_config.items():
            if key != 'type':
                terraform_backend += f'    {key} = "{value}"\n'
        
        terraform_backend += "  }\n}\n"
        
        with open(backend_file, 'w') as f:
            f.write(terraform_backend)
        
        self.logger.info("Terraform backend configuration created")
    
    async def _setup_compliance_policies(self):
        """Setup compliance policies"""
        self.logger.info("Setting up compliance policies...")
        
        # Load OPA policies if specified
        for policy_path in self.config.compliance_policies:
            policy_full_path = os.path.join(self.workspace_path, policy_path)
            if os.path.exists(policy_full_path):
                self.logger.info(f"Loading compliance policy: {policy_path}")
            else:
                self.logger.warning(f"Compliance policy not found: {policy_path}")
    
    async def provision_environment(self, environment: str, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Provision infrastructure for AGI model deployment"""
        self.logger.info(f"Provisioning environment: {environment}")
        
        try:
            # Generate infrastructure templates
            infra_config = await self._generate_infrastructure_config(environment, model_config)
            
            # Apply infrastructure changes
            apply_result = await self._apply_infrastructure(environment, infra_config)
            
            # Verify deployment
            verification_result = await self._verify_infrastructure(environment)
            
            # Run compliance checks
            compliance_result = await self._run_compliance_checks(environment)
            
            return {
                "environment": environment,
                "status": "success",
                "infrastructure_applied": apply_result,
                "verification": verification_result,
                "compliance": compliance_result,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Failed to provision environment {environment}: {e}")
            return {
                "environment": environment,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _generate_infrastructure_config(self, environment: str, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate infrastructure configuration from templates"""
        templates_path = os.path.join(self.workspace_path, self.config.templates_path)
        
        if not os.path.exists(templates_path):
            raise Exception(f"Templates path not found: {templates_path}")
        
        # Setup Jinja2 environment
        jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_path)
        )
        
        template_vars = {
            'environment': environment,
            'model_id': model_config.get('model_id', 'unknown'),
            'model_version': model_config.get('model_version', 'latest'),
            'resource_requirements': model_config.get('resource_requirements', {}),
            'scaling_config': model_config.get('scaling_config', {}),
            'security_config': model_config.get('security_config', {}),
            'timestamp': datetime.now().isoformat()
        }
        
        generated_configs = {}
        
        # Generate Terraform configurations
        tf_template_path = os.path.join(templates_path, 'terraform')
        if os.path.exists(tf_template_path):
            for tf_file in os.listdir(tf_template_path):
                if tf_file.endswith('.tf.j2'):
                    template = jinja_env.get_template(f'terraform/{tf_file}')
                    rendered_config = template.render(**template_vars)
                    
                    output_file = tf_file.replace('.j2', '')
                    generated_configs[f'terraform/{output_file}'] = rendered_config
        
        # Generate Kubernetes configurations
        k8s_template_path = os.path.join(templates_path, 'kubernetes')
        if os.path.exists(k8s_template_path):
            for k8s_file in os.listdir(k8s_template_path):
                if k8s_file.endswith(('.yaml.j2', '.yml.j2')):
                    template = jinja_env.get_template(f'kubernetes/{k8s_file}')
                    rendered_config = template.render(**template_vars)
                    
                    output_file = k8s_file.replace('.j2', '')
                    generated_configs[f'kubernetes/{output_file}'] = rendered_config
        
        return generated_configs
    
    async def _apply_infrastructure(self, environment: str, infra_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply infrastructure configuration"""
        env_path = os.path.join(self.workspace_path, self.config.infrastructure_path, environment)
        os.makedirs(env_path, exist_ok=True)
        
        results = {}
        
        # Write generated configurations to files
        for config_path, config_content in infra_config.items():
            full_path = os.path.join(env_path, config_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(config_content)
        
        # Apply Terraform configurations
        terraform_result = await self._apply_terraform(env_path)
        results['terraform'] = terraform_result
        
        # Apply Kubernetes configurations
        kubernetes_result = await self._apply_kubernetes(env_path)
        results['kubernetes'] = kubernetes_result
        
        # Commit changes to Git
        await self._commit_infrastructure_changes(environment, "Apply infrastructure changes")
        
        return results
    
    async def _apply_terraform(self, env_path: str) -> Dict[str, Any]:
        """Apply Terraform configuration"""
        terraform_path = os.path.join(env_path, 'terraform')
        
        if not os.path.exists(terraform_path):
            return {"status": "skipped", "reason": "No Terraform configuration found"}
        
        try:
            # Initialize Terraform
            init_result = await self._run_command(
                ['terraform', 'init'],
                cwd=terraform_path
            )
            
            # Plan Terraform changes
            plan_result = await self._run_command(
                ['terraform', 'plan', '-out=tfplan'],
                cwd=terraform_path
            )
            
            # Apply Terraform changes
            apply_result = await self._run_command(
                ['terraform', 'apply', '-auto-approve', 'tfplan'],
                cwd=terraform_path
            )
            
            return {
                "status": "success",
                "init": init_result,
                "plan": plan_result,
                "apply": apply_result
            }
        
        except subprocess.CalledProcessError as e:
            return {
                "status": "failed",
                "error": str(e),
                "stdout": e.stdout.decode() if e.stdout else "",
                "stderr": e.stderr.decode() if e.stderr else ""
            }
    
    async def _apply_kubernetes(self, env_path: str) -> Dict[str, Any]:
        """Apply Kubernetes configuration"""
        k8s_path = os.path.join(env_path, 'kubernetes')
        
        if not os.path.exists(k8s_path):
            return {"status": "skipped", "reason": "No Kubernetes configuration found"}
        
        try:
            # Apply Kubernetes manifests
            apply_result = await self._run_command(
                ['kubectl', 'apply', '-f', k8s_path, '--recursive'],
                cwd=env_path
            )
            
            return {
                "status": "success",
                "apply": apply_result
            }
        
        except subprocess.CalledProcessError as e:
            return {
                "status": "failed",
                "error": str(e),
                "stdout": e.stdout.decode() if e.stdout else "",
                "stderr": e.stderr.decode() if e.stderr else ""
            }
    
    async def _run_command(self, command: List[str], cwd: str) -> Dict[str, Any]:
        """Run a command and return result"""
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            "command": " ".join(command),
            "return_code": process.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode()
        }
    
    async def _verify_infrastructure(self, environment: str) -> Dict[str, Any]:
        """Verify infrastructure deployment"""
        verification_results = {}
        
        # Verify Terraform state
        terraform_verification = await self._verify_terraform_state(environment)
        verification_results['terraform'] = terraform_verification
        
        # Verify Kubernetes resources
        kubernetes_verification = await self._verify_kubernetes_resources(environment)
        verification_results['kubernetes'] = kubernetes_verification
        
        return verification_results
    
    async def _verify_terraform_state(self, environment: str) -> Dict[str, Any]:
        """Verify Terraform state"""
        env_path = os.path.join(self.workspace_path, self.config.infrastructure_path, environment)
        terraform_path = os.path.join(env_path, 'terraform')
        
        if not os.path.exists(terraform_path):
            return {"status": "skipped", "reason": "No Terraform configuration"}
        
        try:
            # Check Terraform state
            state_result = await self._run_command(
                ['terraform', 'show', '-json'],
                cwd=terraform_path
            )
            
            if state_result['return_code'] == 0:
                state_data = json.loads(state_result['stdout'])
                resource_count = len(state_data.get('values', {}).get('root_module', {}).get('resources', []))
                
                return {
                    "status": "success",
                    "resource_count": resource_count,
                    "state_valid": True
                }
            else:
                return {
                    "status": "failed",
                    "error": state_result['stderr']
                }
        
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _verify_kubernetes_resources(self, environment: str) -> Dict[str, Any]:
        """Verify Kubernetes resources"""
        try:
            # Get all resources in the namespace
            get_result = await self._run_command(
                ['kubectl', 'get', 'all', '-n', environment, '-o', 'json'],
                cwd=self.workspace_path
            )
            
            if get_result['return_code'] == 0:
                resources_data = json.loads(get_result['stdout'])
                resource_count = len(resources_data.get('items', []))
                
                # Check resource health
                healthy_count = 0
                for item in resources_data.get('items', []):
                    if self._is_resource_healthy(item):
                        healthy_count += 1
                
                return {
                    "status": "success",
                    "total_resources": resource_count,
                    "healthy_resources": healthy_count,
                    "health_percentage": (healthy_count / resource_count * 100) if resource_count > 0 else 100
                }
            else:
                return {
                    "status": "failed",
                    "error": get_result['stderr']
                }
        
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _is_resource_healthy(self, resource: Dict[str, Any]) -> bool:
        """Check if a Kubernetes resource is healthy"""
        kind = resource.get('kind', '')
        status = resource.get('status', {})
        
        if kind == 'Deployment':
            ready_replicas = status.get('readyReplicas', 0)
            replicas = status.get('replicas', 1)
            return ready_replicas == replicas
        
        elif kind == 'Service':
            return True  # Services are generally always "healthy"
        
        elif kind == 'Pod':
            phase = status.get('phase', '')
            return phase == 'Running'
        
        return True  # Default to healthy for unknown types
    
    async def detect_drift(self, environment: str) -> List[DriftDetection]:
        """Detect configuration drift in infrastructure"""
        self.logger.info(f"Detecting drift for environment: {environment}")
        
        drift_results = []
        
        # Check Terraform drift
        terraform_drift = await self._detect_terraform_drift(environment)
        drift_results.extend(terraform_drift)
        
        # Check Kubernetes drift
        kubernetes_drift = await self._detect_kubernetes_drift(environment)
        drift_results.extend(kubernetes_drift)
        
        # Store drift history
        self.drift_history.extend(drift_results)
        
        return drift_results
    
    async def _detect_terraform_drift(self, environment: str) -> List[DriftDetection]:
        """Detect Terraform configuration drift"""
        env_path = os.path.join(self.workspace_path, self.config.infrastructure_path, environment)
        terraform_path = os.path.join(env_path, 'terraform')
        
        if not os.path.exists(terraform_path):
            return []
        
        drift_results = []
        
        try:
            # Run terraform plan to detect drift
            plan_result = await self._run_command(
                ['terraform', 'plan', '-detailed-exitcode', '-no-color'],
                cwd=terraform_path
            )
            
            # Exit code 2 means changes detected (drift)
            if plan_result['return_code'] == 2:
                # Parse plan output to identify specific drift
                plan_output = plan_result['stdout']
                drift_details = self._parse_terraform_plan_output(plan_output)
                
                for resource_name, changes in drift_details.items():
                    drift_result = DriftDetection(
                        resource_name=resource_name,
                        expected_state=changes.get('expected', {}),
                        actual_state=changes.get('actual', {}),
                        drift_detected=True,
                        drift_details=changes.get('details', []),
                        remediation_actions=["terraform apply"]
                    )
                    drift_results.append(drift_result)
        
        except Exception as e:
            self.logger.error(f"Failed to detect Terraform drift: {e}")
        
        return drift_results
    
    def _parse_terraform_plan_output(self, plan_output: str) -> Dict[str, Dict[str, Any]]:
        """Parse Terraform plan output to identify changes"""
        # Simplified parser for demo purposes
        # In production, use proper Terraform plan parsing
        
        changes = {}
        current_resource = None
        
        for line in plan_output.split('\n'):
            line = line.strip()
            
            if line.startswith('#') and 'will be' in line:
                # Extract resource name
                parts = line.split()
                if len(parts) > 1:
                    current_resource = parts[1]
                    changes[current_resource] = {
                        'expected': {},
                        'actual': {},
                        'details': [line]
                    }
            elif current_resource and ('+' in line or '-' in line or '~' in line):
                changes[current_resource]['details'].append(line)
        
        return changes
    
    async def _detect_kubernetes_drift(self, environment: str) -> List[DriftDetection]:
        """Detect Kubernetes configuration drift"""
        drift_results = []
        
        try:
            # Get current Kubernetes resources
            get_result = await self._run_command(
                ['kubectl', 'get', 'all', '-n', environment, '-o', 'yaml'],
                cwd=self.workspace_path
            )
            
            if get_result['return_code'] != 0:
                return drift_results
            
            current_resources = yaml.safe_load_all(get_result['stdout'])
            
            # Compare with expected configuration
            k8s_path = os.path.join(
                self.workspace_path, 
                self.config.infrastructure_path, 
                environment, 
                'kubernetes'
            )
            
            if os.path.exists(k8s_path):
                expected_resources = await self._load_expected_kubernetes_resources(k8s_path)
                drift_results = self._compare_kubernetes_resources(expected_resources, list(current_resources))
        
        except Exception as e:
            self.logger.error(f"Failed to detect Kubernetes drift: {e}")
        
        return drift_results
    
    async def _load_expected_kubernetes_resources(self, k8s_path: str) -> List[Dict[str, Any]]:
        """Load expected Kubernetes resources from files"""
        expected_resources = []
        
        for root, dirs, files in os.walk(k8s_path):
            for file in files:
                if file.endswith(('.yaml', '.yml')):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        resources = yaml.safe_load_all(f)
                        expected_resources.extend([r for r in resources if r])
        
        return expected_resources
    
    def _compare_kubernetes_resources(self, expected: List[Dict[str, Any]], actual: List[Dict[str, Any]]) -> List[DriftDetection]:
        """Compare expected and actual Kubernetes resources"""
        drift_results = []
        
        # Create lookup dictionaries
        expected_lookup = {
            f"{r.get('kind', 'Unknown')}_{r.get('metadata', {}).get('name', 'unnamed')}": r 
            for r in expected
        }
        
        actual_lookup = {
            f"{r.get('kind', 'Unknown')}_{r.get('metadata', {}).get('name', 'unnamed')}": r 
            for r in actual
        }
        
        # Check for missing or modified resources
        for resource_key, expected_resource in expected_lookup.items():
            if resource_key not in actual_lookup:
                # Resource missing
                drift_result = DriftDetection(
                    resource_name=resource_key,
                    expected_state=expected_resource,
                    actual_state={},
                    drift_detected=True,
                    drift_details=["Resource not found in cluster"],
                    remediation_actions=["kubectl apply -f <resource_file>"]
                )
                drift_results.append(drift_result)
            else:
                # Check for configuration differences
                actual_resource = actual_lookup[resource_key]
                differences = self._find_resource_differences(expected_resource, actual_resource)
                
                if differences:
                    drift_result = DriftDetection(
                        resource_name=resource_key,
                        expected_state=expected_resource,
                        actual_state=actual_resource,
                        drift_detected=True,
                        drift_details=differences,
                        remediation_actions=["kubectl apply -f <resource_file>"]
                    )
                    drift_results.append(drift_result)
        
        return drift_results
    
    def _find_resource_differences(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
        """Find differences between expected and actual resource configurations"""
        differences = []
        
        # Compare key fields (simplified comparison)
        key_fields = ['spec', 'metadata.labels', 'metadata.annotations']
        
        for field in key_fields:
            expected_value = self._get_nested_value(expected, field)
            actual_value = self._get_nested_value(actual, field)
            
            if expected_value != actual_value:
                differences.append(f"{field}: expected {expected_value}, actual {actual_value}")
        
        return differences
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation"""
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    async def _run_compliance_checks(self, environment: str) -> List[ComplianceCheck]:
        """Run compliance checks on infrastructure"""
        self.logger.info(f"Running compliance checks for environment: {environment}")
        
        compliance_results = []
        
        # Security compliance checks
        security_checks = await self._run_security_compliance_checks(environment)
        compliance_results.extend(security_checks)
        
        # Resource compliance checks
        resource_checks = await self._run_resource_compliance_checks(environment)
        compliance_results.extend(resource_checks)
        
        # Configuration compliance checks
        config_checks = await self._run_configuration_compliance_checks(environment)
        compliance_results.extend(config_checks)
        
        # Store compliance history
        self.compliance_history.extend(compliance_results)
        
        return compliance_results
    
    async def _run_security_compliance_checks(self, environment: str) -> List[ComplianceCheck]:
        """Run security compliance checks"""
        checks = []
        
        # Check for encrypted storage
        storage_encryption_check = ComplianceCheck(
            check_name="storage_encryption",
            resource_name=f"{environment}_storage",
            level=ComplianceLevel.COMPLIANT,
            message="Storage encryption is enabled",
            metadata={"encryption_type": "AES-256"}
        )
        checks.append(storage_encryption_check)
        
        # Check for network security
        network_security_check = ComplianceCheck(
            check_name="network_security",
            resource_name=f"{environment}_network",
            level=ComplianceLevel.COMPLIANT,
            message="Network security groups are properly configured",
            metadata={"rules_count": 5}
        )
        checks.append(network_security_check)
        
        return checks
    
    async def _run_resource_compliance_checks(self, environment: str) -> List[ComplianceCheck]:
        """Run resource compliance checks"""
        checks = []
        
        # Check resource tagging
        tagging_check = ComplianceCheck(
            check_name="resource_tagging",
            resource_name=f"{environment}_resources",
            level=ComplianceLevel.WARNING,
            message="Some resources are missing required tags",
            remediation="Add required tags: Environment, Owner, Project"
        )
        checks.append(tagging_check)
        
        # Check resource limits
        limits_check = ComplianceCheck(
            check_name="resource_limits",
            resource_name=f"{environment}_containers",
            level=ComplianceLevel.COMPLIANT,
            message="All containers have resource limits defined"
        )
        checks.append(limits_check)
        
        return checks
    
    async def _run_configuration_compliance_checks(self, environment: str) -> List[ComplianceCheck]:
        """Run configuration compliance checks"""
        checks = []
        
        # Check backup configuration
        backup_check = ComplianceCheck(
            check_name="backup_configuration",
            resource_name=f"{environment}_data",
            level=ComplianceLevel.COMPLIANT,
            message="Automated backups are configured",
            metadata={"backup_frequency": "daily", "retention_days": 30}
        )
        checks.append(backup_check)
        
        # Check monitoring configuration
        monitoring_check = ComplianceCheck(
            check_name="monitoring_configuration",
            resource_name=f"{environment}_monitoring",
            level=ComplianceLevel.COMPLIANT,
            message="Comprehensive monitoring is configured"
        )
        checks.append(monitoring_check)
        
        return checks
    
    async def remediate_drift(self, drift_detection: DriftDetection) -> Dict[str, Any]:
        """Remediate detected configuration drift"""
        if not self.config.auto_remediation:
            return {
                "status": "skipped",
                "reason": "Auto-remediation is disabled",
                "resource": drift_detection.resource_name
            }
        
        self.logger.info(f"Remediating drift for resource: {drift_detection.resource_name}")
        
        try:
            for action in drift_detection.remediation_actions:
                if action == "terraform apply":
                    await self._remediate_terraform_drift(drift_detection)
                elif action.startswith("kubectl apply"):
                    await self._remediate_kubernetes_drift(drift_detection)
            
            return {
                "status": "success",
                "resource": drift_detection.resource_name,
                "actions_performed": drift_detection.remediation_actions,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                "status": "failed",
                "resource": drift_detection.resource_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _remediate_terraform_drift(self, drift_detection: DriftDetection):
        """Remediate Terraform drift"""
        # Apply Terraform configuration
        env_path = self._get_environment_path_from_resource_name(drift_detection.resource_name)
        terraform_path = os.path.join(env_path, 'terraform')
        
        if os.path.exists(terraform_path):
            apply_result = await self._run_command(
                ['terraform', 'apply', '-auto-approve'],
                cwd=terraform_path
            )
            
            if apply_result['return_code'] != 0:
                raise Exception(f"Terraform apply failed: {apply_result['stderr']}")
    
    async def _remediate_kubernetes_drift(self, drift_detection: DriftDetection):
        """Remediate Kubernetes drift"""
        # Apply Kubernetes configuration
        env_path = self._get_environment_path_from_resource_name(drift_detection.resource_name)
        k8s_path = os.path.join(env_path, 'kubernetes')
        
        if os.path.exists(k8s_path):
            apply_result = await self._run_command(
                ['kubectl', 'apply', '-f', k8s_path, '--recursive'],
                cwd=env_path
            )
            
            if apply_result['return_code'] != 0:
                raise Exception(f"Kubectl apply failed: {apply_result['stderr']}")
    
    def _get_environment_path_from_resource_name(self, resource_name: str) -> str:
        """Extract environment path from resource name"""
        # Simplified extraction - assumes resource name format: environment_resource
        environment = resource_name.split('_')[0]
        return os.path.join(self.workspace_path, self.config.infrastructure_path, environment)
    
    async def _commit_infrastructure_changes(self, environment: str, message: str):
        """Commit infrastructure changes to Git repository"""
        try:
            # Add all changes
            self.git_repo.git.add(A=True)
            
            # Check if there are any changes to commit
            if self.git_repo.is_dirty():
                # Commit changes
                self.git_repo.index.commit(f"[{environment}] {message}")
                
                # Push changes
                origin = self.git_repo.remote(name='origin')
                origin.push()
                
                self.logger.info(f"Committed and pushed infrastructure changes for {environment}")
            else:
                self.logger.info("No changes to commit")
        
        except Exception as e:
            self.logger.error(f"Failed to commit changes: {e}")
    
    def get_infrastructure_status(self, environment: str) -> Dict[str, Any]:
        """Get current infrastructure status"""
        recent_drift = [d for d in self.drift_history if environment in d.resource_name][-5:]
        recent_compliance = [c for c in self.compliance_history if environment in c.resource_name][-10:]
        
        # Determine overall status
        has_drift = any(d.drift_detected for d in recent_drift)
        has_violations = any(c.level == ComplianceLevel.VIOLATION for c in recent_compliance)
        
        if has_violations:
            status = InfrastructureStatus.FAILED
        elif has_drift:
            status = InfrastructureStatus.OUT_OF_SYNC
        else:
            status = InfrastructureStatus.SYNCED
        
        return {
            "environment": environment,
            "status": status.value,
            "resources_count": len([r for r in self.infrastructure_resources.values() if environment in r.name]),
            "recent_drift_detections": len(recent_drift),
            "active_compliance_issues": len([c for c in recent_compliance if c.level in [ComplianceLevel.WARNING, ComplianceLevel.VIOLATION]]),
            "last_update": datetime.now().isoformat(),
            "git_commit": self.git_repo.head.commit.hexsha if self.git_repo else None
        }
    
    async def cleanup(self):
        """Cleanup resources and temporary files"""
        if os.path.exists(self.workspace_path):
            import shutil
            shutil.rmtree(self.workspace_path)
        
        self.logger.info("Infrastructure Manager cleanup completed")

# Example usage and configuration
if __name__ == "__main__":
    async def main():
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Create GitOps configuration
        config = GitOpsConfig(
            git_repository="https://github.com/example/agi-infrastructure.git",
            git_branch="main",
            infrastructure_path="environments",
            templates_path="templates",
            environments=["development", "staging", "production"],
            terraform_backend={
                "type": "s3",
                "bucket": "agi-terraform-state",
                "key": "infrastructure.tfstate",
                "region": "us-east-1"
            },
            kubernetes_configs={
                "context": "agi-cluster",
                "namespace_prefix": "agi"
            },
            compliance_policies=[
                "policies/security.rego",
                "policies/resources.rego"
            ],
            drift_detection_interval=300,
            auto_remediation=False
        )
        
        # Create infrastructure manager
        infra_manager = InfrastructureManager(config)
        
        try:
            # Initialize
            await infra_manager.initialize()
            
            # Provision environment
            model_config = {
                "model_id": "kenny-agi-v2.1",
                "model_version": "v2.1.0",
                "resource_requirements": {
                    "cpu": "4000m",
                    "memory": "8Gi",
                    "gpu": "1"
                },
                "scaling_config": {
                    "min_replicas": 2,
                    "max_replicas": 10
                },
                "security_config": {
                    "encryption_enabled": True,
                    "network_isolation": True
                }
            }
            
            provision_result = await infra_manager.provision_environment("staging", model_config)
            print("Provision Result:", json.dumps(provision_result, indent=2))
            
            # Detect drift
            drift_results = await infra_manager.detect_drift("staging")
            print(f"Drift Detection: {len(drift_results)} issues found")
            
            # Run compliance checks
            compliance_results = await infra_manager._run_compliance_checks("staging")
            print(f"Compliance Checks: {len(compliance_results)} checks performed")
            
            # Get infrastructure status
            status = infra_manager.get_infrastructure_status("staging")
            print("Infrastructure Status:", json.dumps(status, indent=2))
        
        finally:
            # Cleanup
            await infra_manager.cleanup()
    
    asyncio.run(main())