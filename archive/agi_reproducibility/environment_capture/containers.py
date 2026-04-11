"""
Container Manager

Advanced containerization system for creating reproducible execution environments
with support for multiple container runtimes and hardware configurations.
"""

import os
import json
import yaml
import asyncio
import hashlib
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass
import docker
import subprocess

from ..core.config import PlatformConfig, ContainerRuntime, ReplicationTarget
from ..core.exceptions import *


@dataclass
class ContainerSpec:
    """Container specification for experiment execution."""
    experiment_id: str
    base_image: str
    python_version: str
    packages: List[str]
    environment_variables: Dict[str, str]
    hardware_requirements: Dict[str, Any]
    volumes: List[Dict[str, str]]
    network_mode: str
    security_context: Dict[str, Any]
    resource_limits: Dict[str, Any]
    labels: Dict[str, str]
    
    def to_dockerfile(self) -> str:
        """Generate Dockerfile from container spec."""
        dockerfile_lines = [
            f"FROM {self.base_image}",
            "",
            "# Set working directory",
            "WORKDIR /experiment",
            "",
            "# Install system dependencies",
            "RUN apt-get update && apt-get install -y \\",
            "    git \\",
            "    curl \\",
            "    wget \\",
            "    build-essential \\",
            "    && rm -rf /var/lib/apt/lists/*",
            "",
            "# Install Python packages"
        ]
        
        if self.packages:
            dockerfile_lines.extend([
                "COPY requirements.txt /tmp/requirements.txt",
                "RUN pip install --no-cache-dir -r /tmp/requirements.txt",
                ""
            ])
        
        # Set environment variables
        if self.environment_variables:
            dockerfile_lines.append("# Set environment variables")
            for key, value in self.environment_variables.items():
                dockerfile_lines.append(f"ENV {key}={value}")
            dockerfile_lines.append("")
        
        # Copy experiment code
        dockerfile_lines.extend([
            "# Copy experiment code",
            "COPY . /experiment/",
            "",
            "# Set entrypoint",
            "ENTRYPOINT [\"python\", \"main.py\"]"
        ])
        
        return "\n".join(dockerfile_lines)
    
    def to_docker_compose(self) -> Dict[str, Any]:
        """Generate docker-compose configuration."""
        service_config = {
            'build': '.',
            'container_name': f"agi-experiment-{self.experiment_id}",
            'environment': self.environment_variables,
            'volumes': [f"{vol['host']}:{vol['container']}" for vol in self.volumes],
            'network_mode': self.network_mode,
            'labels': self.labels,
            'restart': 'no'
        }
        
        # Add resource limits
        if self.resource_limits:
            service_config['deploy'] = {
                'resources': {
                    'limits': self.resource_limits,
                    'reservations': {
                        'memory': self.resource_limits.get('memory', '1G'),
                        'cpus': str(float(self.resource_limits.get('cpus', '1.0')) * 0.5)
                    }
                }
            }
        
        # Add GPU support if required
        if self.hardware_requirements.get('gpu'):
            service_config['runtime'] = 'nvidia'
            service_config['environment']['NVIDIA_VISIBLE_DEVICES'] = 'all'
        
        return {
            'version': '3.8',
            'services': {
                'experiment': service_config
            }
        }


class ContainerManager:
    """
    Advanced container management for AGI experiments.
    
    Features:
    - Multi-runtime support (Docker, Podman, Singularity, Kubernetes)
    - Hardware-specific container builds
    - Automated dependency resolution
    - Security sandbox configuration
    - Resource monitoring and limits
    - Container registry integration
    - Reproducible builds with content hashing
    """
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.runtime = config.containers.runtime
        self.registry = config.containers.registry
        self.namespace = config.containers.namespace
        self.containers_dir = Path(config.base_path) / "containers"
        self.docker_client = None
        
    async def initialize(self) -> None:
        """Initialize the container manager."""
        self.containers_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize container runtime
        if self.runtime == ContainerRuntime.DOCKER:
            await self._initialize_docker()
        elif self.runtime == ContainerRuntime.PODMAN:
            await self._initialize_podman()
        elif self.runtime == ContainerRuntime.SINGULARITY:
            await self._initialize_singularity()
        elif self.runtime == ContainerRuntime.KUBERNETES:
            await self._initialize_kubernetes()
    
    async def _initialize_docker(self) -> None:
        """Initialize Docker client."""
        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
        except Exception as e:
            raise ContainerBuildError(f"Failed to initialize Docker: {str(e)}")
    
    async def _initialize_podman(self) -> None:
        """Initialize Podman."""
        try:
            # Check if Podman is available
            result = await asyncio.create_subprocess_exec(
                'podman', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            if result.returncode != 0:
                raise ContainerBuildError("Podman not available")
        except FileNotFoundError:
            raise ContainerBuildError("Podman not found")
    
    async def _initialize_singularity(self) -> None:
        """Initialize Singularity."""
        try:
            # Check if Singularity is available
            result = await asyncio.create_subprocess_exec(
                'singularity', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            if result.returncode != 0:
                raise ContainerBuildError("Singularity not available")
        except FileNotFoundError:
            raise ContainerBuildError("Singularity not found")
    
    async def _initialize_kubernetes(self) -> None:
        """Initialize Kubernetes client."""
        try:
            # Check if kubectl is available
            result = await asyncio.create_subprocess_exec(
                'kubectl', 'version', '--client',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            if result.returncode != 0:
                raise ContainerBuildError("kubectl not available")
        except FileNotFoundError:
            raise ContainerBuildError("kubectl not found")
    
    async def create_experiment_container(self, experiment_id: str, code_path: str,
                                        parameters: Dict[str, Any],
                                        target: ReplicationTarget = ReplicationTarget.CPU_X86) -> Dict[str, Any]:
        """Create a container for experiment execution."""
        validate_experiment_id(experiment_id)
        
        # Generate container specification
        container_spec = await self._generate_container_spec(
            experiment_id, code_path, parameters, target
        )
        
        # Build container
        container_info = await self._build_container(container_spec)
        
        return container_info
    
    async def _generate_container_spec(self, experiment_id: str, code_path: str,
                                     parameters: Dict[str, Any],
                                     target: ReplicationTarget) -> ContainerSpec:
        """Generate container specification based on requirements."""
        # Determine base image based on target
        base_image = self._get_base_image(target)
        
        # Analyze code dependencies
        requirements = await self._analyze_dependencies(code_path)
        
        # Generate environment variables
        env_vars = {
            'EXPERIMENT_ID': experiment_id,
            'PYTHONPATH': '/experiment',
            'PYTHONUNBUFFERED': '1'
        }
        env_vars.update(parameters.get('environment', {}))
        
        # Configure volumes
        volumes = [
            {'host': code_path, 'container': '/experiment/code'},
            {'host': str(self.containers_dir / experiment_id / 'data'), 'container': '/experiment/data'},
            {'host': str(self.containers_dir / experiment_id / 'output'), 'container': '/experiment/output'}
        ]
        
        # Configure hardware requirements
        hardware_requirements = self._get_hardware_requirements(target, parameters)
        
        # Configure security context
        security_context = self.config.containers.security_constraints.copy()
        
        # Configure resource limits
        resource_limits = self.config.containers.resource_limits.copy()
        if parameters.get('resources'):
            resource_limits.update(parameters['resources'])
        
        # Generate labels
        labels = {
            'agi.experiment_id': experiment_id,
            'agi.platform_version': self.config.version,
            'agi.target': target.value,
            'agi.created_at': datetime.now(timezone.utc).isoformat()
        }
        
        container_spec = ContainerSpec(
            experiment_id=experiment_id,
            base_image=base_image,
            python_version=requirements.get('python_version', '3.9'),
            packages=requirements.get('packages', []),
            environment_variables=env_vars,
            hardware_requirements=hardware_requirements,
            volumes=volumes,
            network_mode=self._get_network_mode(),
            security_context=security_context,
            resource_limits=resource_limits,
            labels=labels
        )
        
        return container_spec
    
    def _get_base_image(self, target: ReplicationTarget) -> str:
        """Get appropriate base image for target platform."""
        base_images = {
            ReplicationTarget.CPU_X86: "python:3.9-slim",
            ReplicationTarget.CPU_ARM: "arm64v8/python:3.9-slim",
            ReplicationTarget.GPU_NVIDIA: "nvidia/cuda:11.8-runtime-ubuntu20.04",
            ReplicationTarget.GPU_AMD: "rocm/pytorch:rocm5.4_ubuntu20.04_py3.8_pytorch_1.12.1",
            ReplicationTarget.TPU_GOOGLE: "gcr.io/tpu-pytorch/xla:r1.13_3.8_tpuvm",
            ReplicationTarget.QUANTUM_IBM: "python:3.9-slim",  # Custom quantum libraries will be added
            ReplicationTarget.NEUROMORPHIC: "python:3.9-slim",  # Custom neuromorphic libraries
            ReplicationTarget.CUSTOM: "python:3.9-slim"
        }
        
        return base_images.get(target, "python:3.9-slim")
    
    async def _analyze_dependencies(self, code_path: str) -> Dict[str, Any]:
        """Analyze code dependencies."""
        requirements = {
            'python_version': '3.9',
            'packages': [],
            'system_packages': []
        }
        
        code_path = Path(code_path)
        
        # Check for requirements.txt
        requirements_txt = code_path / 'requirements.txt'
        if requirements_txt.exists():
            with open(requirements_txt, 'r') as f:
                requirements['packages'] = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        # Check for pyproject.toml
        pyproject_toml = code_path / 'pyproject.toml'
        if pyproject_toml.exists():
            try:
                import tomllib
                with open(pyproject_toml, 'rb') as f:
                    data = tomllib.load(f)
                    
                dependencies = data.get('project', {}).get('dependencies', [])
                requirements['packages'].extend(dependencies)
                
                # Check for Python version requirement
                python_requires = data.get('project', {}).get('requires-python')
                if python_requires:
                    # Parse Python version (simplified)
                    if '>=' in python_requires:
                        version = python_requires.split('>=')[1].strip()
                        requirements['python_version'] = version
            except Exception:
                pass  # Continue without pyproject.toml parsing
        
        # Scan for import statements to detect additional dependencies
        python_files = list(code_path.rglob('*.py'))
        detected_imports = set()
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Simple regex to find import statements
                import re
                imports = re.findall(r'^(?:from\s+(\w+)|import\s+(\w+))', content, re.MULTILINE)
                for imp in imports:
                    module = imp[0] or imp[1]
                    if module:
                        detected_imports.add(module.split('.')[0])
            except Exception:
                continue
        
        # Map common imports to packages
        import_to_package = {
            'numpy': 'numpy',
            'pandas': 'pandas',
            'sklearn': 'scikit-learn',
            'torch': 'torch',
            'tensorflow': 'tensorflow',
            'keras': 'keras',
            'matplotlib': 'matplotlib',
            'seaborn': 'seaborn',
            'requests': 'requests',
            'asyncio': None,  # Built-in
            'json': None,     # Built-in
            'os': None,       # Built-in
            'sys': None,      # Built-in
            'hyperon': 'hyperon-experimental',
            'opencog': 'opencog'
        }
        
        for imp in detected_imports:
            if imp in import_to_package:
                package = import_to_package[imp]
                if package and package not in requirements['packages']:
                    requirements['packages'].append(package)
        
        return requirements
    
    def _get_hardware_requirements(self, target: ReplicationTarget, 
                                 parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get hardware requirements for target platform."""
        requirements = {}
        
        if target == ReplicationTarget.GPU_NVIDIA:
            requirements['gpu'] = True
            requirements['gpu_type'] = 'nvidia'
            requirements['gpu_memory'] = parameters.get('gpu_memory', '8GB')
        elif target == ReplicationTarget.GPU_AMD:
            requirements['gpu'] = True
            requirements['gpu_type'] = 'amd'
        elif target == ReplicationTarget.TPU_GOOGLE:
            requirements['tpu'] = True
            requirements['tpu_type'] = parameters.get('tpu_type', 'v3-8')
        elif target == ReplicationTarget.QUANTUM_IBM:
            requirements['quantum'] = True
            requirements['quantum_backend'] = parameters.get('quantum_backend', 'qasm_simulator')
        
        return requirements
    
    def _get_network_mode(self) -> str:
        """Get appropriate network mode based on security settings."""
        if self.config.containers.network_isolation:
            return 'none'
        else:
            return 'bridge'
    
    async def _build_container(self, container_spec: ContainerSpec) -> Dict[str, Any]:
        """Build container from specification."""
        if self.runtime == ContainerRuntime.DOCKER:
            return await self._build_docker_container(container_spec)
        elif self.runtime == ContainerRuntime.PODMAN:
            return await self._build_podman_container(container_spec)
        elif self.runtime == ContainerRuntime.SINGULARITY:
            return await self._build_singularity_container(container_spec)
        elif self.runtime == ContainerRuntime.KUBERNETES:
            return await self._build_kubernetes_container(container_spec)
        else:
            raise ContainerBuildError(f"Unsupported runtime: {self.runtime}")
    
    async def _build_docker_container(self, container_spec: ContainerSpec) -> Dict[str, Any]:
        """Build Docker container."""
        if not self.docker_client:
            raise ContainerBuildError("Docker client not initialized")
        
        # Create build directory
        build_dir = self.containers_dir / container_spec.experiment_id
        build_dir.mkdir(parents=True, exist_ok=True)
        
        # Write Dockerfile
        dockerfile_path = build_dir / 'Dockerfile'
        with open(dockerfile_path, 'w') as f:
            f.write(container_spec.to_dockerfile())
        
        # Write requirements.txt
        if container_spec.packages:
            requirements_path = build_dir / 'requirements.txt'
            with open(requirements_path, 'w') as f:
                for package in container_spec.packages:
                    f.write(f"{package}\n")
        
        # Write docker-compose.yml
        compose_path = build_dir / 'docker-compose.yml'
        with open(compose_path, 'w') as f:
            yaml.dump(container_spec.to_docker_compose(), f, default_flow_style=False)
        
        # Build image
        image_tag = f"{self.namespace}/experiment-{container_spec.experiment_id}:latest"
        
        try:
            image, build_logs = self.docker_client.images.build(
                path=str(build_dir),
                tag=image_tag,
                rm=True,
                pull=True
            )
            
            container_info = {
                'runtime': 'docker',
                'image_id': image.id,
                'image_tag': image_tag,
                'build_dir': str(build_dir),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'spec': container_spec.__dict__
            }
            
            return container_info
            
        except docker.errors.BuildError as e:
            raise ContainerBuildError(f"Docker build failed: {str(e)}")
    
    async def _build_podman_container(self, container_spec: ContainerSpec) -> Dict[str, Any]:
        """Build Podman container."""
        # Create build directory
        build_dir = self.containers_dir / container_spec.experiment_id
        build_dir.mkdir(parents=True, exist_ok=True)
        
        # Write Dockerfile
        dockerfile_path = build_dir / 'Dockerfile'
        with open(dockerfile_path, 'w') as f:
            f.write(container_spec.to_dockerfile())
        
        # Write requirements.txt
        if container_spec.packages:
            requirements_path = build_dir / 'requirements.txt'
            with open(requirements_path, 'w') as f:
                for package in container_spec.packages:
                    f.write(f"{package}\n")
        
        # Build image using Podman
        image_tag = f"{self.namespace}/experiment-{container_spec.experiment_id}:latest"
        
        build_cmd = [
            'podman', 'build',
            '-t', image_tag,
            str(build_dir)
        ]
        
        try:
            result = await asyncio.create_subprocess_exec(
                *build_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                raise ContainerBuildError(f"Podman build failed: {stderr.decode()}")
            
            container_info = {
                'runtime': 'podman',
                'image_tag': image_tag,
                'build_dir': str(build_dir),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'spec': container_spec.__dict__
            }
            
            return container_info
            
        except Exception as e:
            raise ContainerBuildError(f"Podman build failed: {str(e)}")
    
    async def _build_singularity_container(self, container_spec: ContainerSpec) -> Dict[str, Any]:
        """Build Singularity container."""
        # Create build directory
        build_dir = self.containers_dir / container_spec.experiment_id
        build_dir.mkdir(parents=True, exist_ok=True)
        
        # Write Singularity definition file
        def_file = build_dir / 'experiment.def'
        with open(def_file, 'w') as f:
            f.write(self._generate_singularity_def(container_spec))
        
        # Build SIF file
        sif_file = build_dir / f"{container_spec.experiment_id}.sif"
        
        build_cmd = [
            'singularity', 'build',
            '--fakeroot',
            str(sif_file),
            str(def_file)
        ]
        
        try:
            result = await asyncio.create_subprocess_exec(
                *build_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                raise ContainerBuildError(f"Singularity build failed: {stderr.decode()}")
            
            container_info = {
                'runtime': 'singularity',
                'sif_file': str(sif_file),
                'build_dir': str(build_dir),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'spec': container_spec.__dict__
            }
            
            return container_info
            
        except Exception as e:
            raise ContainerBuildError(f"Singularity build failed: {str(e)}")
    
    def _generate_singularity_def(self, container_spec: ContainerSpec) -> str:
        """Generate Singularity definition file."""
        lines = [
            "Bootstrap: docker",
            f"From: {container_spec.base_image}",
            "",
            "%environment",
            "    export PYTHONPATH=/experiment",
            "    export PYTHONUNBUFFERED=1"
        ]
        
        for key, value in container_spec.environment_variables.items():
            lines.append(f"    export {key}={value}")
        
        lines.extend([
            "",
            "%post",
            "    apt-get update && apt-get install -y git curl wget build-essential",
            "    rm -rf /var/lib/apt/lists/*"
        ])
        
        if container_spec.packages:
            lines.append("    pip install --no-cache-dir " + " ".join(container_spec.packages))
        
        lines.extend([
            "",
            "%runscript",
            "    exec python /experiment/main.py \"$@\""
        ])
        
        return "\n".join(lines)
    
    async def _build_kubernetes_container(self, container_spec: ContainerSpec) -> Dict[str, Any]:
        """Build container for Kubernetes deployment."""
        # For Kubernetes, we build with Docker first, then create K8s manifests
        docker_info = await self._build_docker_container(container_spec)
        
        # Generate Kubernetes manifests
        build_dir = Path(docker_info['build_dir'])
        k8s_manifests = self._generate_k8s_manifests(container_spec, docker_info['image_tag'])
        
        # Write manifests
        manifests_dir = build_dir / 'k8s'
        manifests_dir.mkdir(exist_ok=True)
        
        for name, manifest in k8s_manifests.items():
            manifest_file = manifests_dir / f"{name}.yaml"
            with open(manifest_file, 'w') as f:
                yaml.dump(manifest, f, default_flow_style=False)
        
        docker_info['runtime'] = 'kubernetes'
        docker_info['k8s_manifests'] = str(manifests_dir)
        
        return docker_info
    
    def _generate_k8s_manifests(self, container_spec: ContainerSpec, 
                               image_tag: str) -> Dict[str, Any]:
        """Generate Kubernetes manifests."""
        manifests = {}
        
        # Job manifest
        manifests['job'] = {
            'apiVersion': 'batch/v1',
            'kind': 'Job',
            'metadata': {
                'name': f"agi-experiment-{container_spec.experiment_id}",
                'labels': container_spec.labels
            },
            'spec': {
                'template': {
                    'spec': {
                        'containers': [{
                            'name': 'experiment',
                            'image': image_tag,
                            'env': [
                                {'name': k, 'value': v} 
                                for k, v in container_spec.environment_variables.items()
                            ],
                            'resources': {
                                'limits': container_spec.resource_limits,
                                'requests': {
                                    'memory': '512Mi',
                                    'cpu': '0.5'
                                }
                            },
                            'volumeMounts': [
                                {
                                    'name': 'experiment-data',
                                    'mountPath': '/experiment/data'
                                },
                                {
                                    'name': 'experiment-output',
                                    'mountPath': '/experiment/output'
                                }
                            ]
                        }],
                        'volumes': [
                            {
                                'name': 'experiment-data',
                                'emptyDir': {}
                            },
                            {
                                'name': 'experiment-output',
                                'emptyDir': {}
                            }
                        ],
                        'restartPolicy': 'Never',
                        'securityContext': container_spec.security_context
                    }
                }
            }
        }
        
        return manifests
    
    async def run_container(self, container_info: Dict[str, Any], 
                          command: List[str] = None) -> Dict[str, Any]:
        """Run a built container."""
        runtime = container_info.get('runtime')
        
        if runtime == 'docker':
            return await self._run_docker_container(container_info, command)
        elif runtime == 'podman':
            return await self._run_podman_container(container_info, command)
        elif runtime == 'singularity':
            return await self._run_singularity_container(container_info, command)
        elif runtime == 'kubernetes':
            return await self._run_kubernetes_container(container_info, command)
        else:
            raise ContainerBuildError(f"Unsupported runtime: {runtime}")
    
    async def _run_docker_container(self, container_info: Dict[str, Any],
                                  command: List[str] = None) -> Dict[str, Any]:
        """Run Docker container."""
        if not self.docker_client:
            raise ContainerBuildError("Docker client not initialized")
        
        try:
            image_tag = container_info['image_tag']
            spec = container_info['spec']
            
            # Configure container run parameters
            run_kwargs = {
                'image': image_tag,
                'detach': True,
                'remove': True,
                'environment': spec['environment_variables'],
                'volumes': {
                    vol['host']: {'bind': vol['container'], 'mode': 'rw'}
                    for vol in spec['volumes']
                },
                'network_mode': spec['network_mode'],
                'labels': spec['labels']
            }
            
            if command:
                run_kwargs['command'] = command
            
            # Add resource limits
            if spec.get('resource_limits'):
                limits = spec['resource_limits']
                if 'memory' in limits:
                    run_kwargs['mem_limit'] = limits['memory']
                if 'cpus' in limits:
                    run_kwargs['cpu_quota'] = int(float(limits['cpus']) * 100000)
                    run_kwargs['cpu_period'] = 100000
            
            # Run container
            container = self.docker_client.containers.run(**run_kwargs)
            
            execution_info = {
                'container_id': container.id,
                'status': 'running',
                'started_at': datetime.now(timezone.utc).isoformat()
            }
            
            return execution_info
            
        except docker.errors.ContainerError as e:
            raise ReplayError(f"Container execution failed: {str(e)}")
    
    async def _run_podman_container(self, container_info: Dict[str, Any],
                                  command: List[str] = None) -> Dict[str, Any]:
        """Run Podman container."""
        image_tag = container_info['image_tag']
        spec = container_info['spec']
        
        run_cmd = ['podman', 'run', '--rm', '-d']
        
        # Add environment variables
        for key, value in spec['environment_variables'].items():
            run_cmd.extend(['-e', f"{key}={value}"])
        
        # Add volumes
        for vol in spec['volumes']:
            run_cmd.extend(['-v', f"{vol['host']}:{vol['container']}"])
        
        # Add network mode
        run_cmd.extend(['--network', spec['network_mode']])
        
        # Add image
        run_cmd.append(image_tag)
        
        # Add command
        if command:
            run_cmd.extend(command)
        
        try:
            result = await asyncio.create_subprocess_exec(
                *run_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                raise ReplayError(f"Podman run failed: {stderr.decode()}")
            
            container_id = stdout.decode().strip()
            
            execution_info = {
                'container_id': container_id,
                'status': 'running',
                'started_at': datetime.now(timezone.utc).isoformat()
            }
            
            return execution_info
            
        except Exception as e:
            raise ReplayError(f"Podman execution failed: {str(e)}")
    
    async def _run_singularity_container(self, container_info: Dict[str, Any],
                                       command: List[str] = None) -> Dict[str, Any]:
        """Run Singularity container."""
        sif_file = container_info['sif_file']
        spec = container_info['spec']
        
        run_cmd = ['singularity', 'exec']
        
        # Add volumes
        for vol in spec['volumes']:
            run_cmd.extend(['--bind', f"{vol['host']}:{vol['container']}"])
        
        # Add SIF file
        run_cmd.append(sif_file)
        
        # Add command
        if command:
            run_cmd.extend(command)
        else:
            run_cmd.append('python')
            run_cmd.append('/experiment/main.py')
        
        try:
            result = await asyncio.create_subprocess_exec(
                *run_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            execution_info = {
                'process': result,
                'status': 'running',
                'started_at': datetime.now(timezone.utc).isoformat()
            }
            
            return execution_info
            
        except Exception as e:
            raise ReplayError(f"Singularity execution failed: {str(e)}")
    
    async def _run_kubernetes_container(self, container_info: Dict[str, Any],
                                      command: List[str] = None) -> Dict[str, Any]:
        """Run container on Kubernetes."""
        k8s_manifests_dir = container_info['k8s_manifests']
        
        # Apply job manifest
        apply_cmd = [
            'kubectl', 'apply',
            '-f', f"{k8s_manifests_dir}/job.yaml"
        ]
        
        try:
            result = await asyncio.create_subprocess_exec(
                *apply_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                raise ReplayError(f"Kubernetes job creation failed: {stderr.decode()}")
            
            execution_info = {
                'job_name': f"agi-experiment-{container_info['spec']['experiment_id']}",
                'status': 'running',
                'started_at': datetime.now(timezone.utc).isoformat()
            }
            
            return execution_info
            
        except Exception as e:
            raise ReplayError(f"Kubernetes execution failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on container manager."""
        try:
            # Check containers directory
            containers_accessible = self.containers_dir.exists()
            
            # Check runtime availability
            runtime_available = False
            if self.runtime == ContainerRuntime.DOCKER and self.docker_client:
                try:
                    self.docker_client.ping()
                    runtime_available = True
                except:
                    pass
            
            return {
                'status': 'healthy' if runtime_available else 'degraded',
                'containers_dir': containers_accessible,
                'runtime': self.runtime.value,
                'runtime_available': runtime_available,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def cleanup(self) -> None:
        """Cleanup container manager resources."""
        if self.docker_client:
            self.docker_client.close()