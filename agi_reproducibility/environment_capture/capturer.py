"""
Environment Capturer

Comprehensive environment capture system that records all aspects of the
execution environment for perfect reproducibility.
"""

import os
import sys
import json
import hashlib
import platform
import subprocess
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set, Tuple
from pathlib import Path
import importlib
import importlib.util
import pkg_resources
import psutil

from ..core.config import PlatformConfig
from ..core.exceptions import *


class EnvironmentCapturer:
    """
    Comprehensive environment capture system.
    
    Captures:
    - System information (OS, hardware, kernel)
    - Python environment (version, packages, virtual env)
    - Environment variables
    - Hardware specifications
    - GPU/accelerator information
    - Hyperon/OpenCog specific environment
    - Custom AGI framework configurations
    - File system permissions and paths
    - Network configuration (for distributed experiments)
    """
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.snapshots_dir = Path(config.base_path) / "environment_snapshots"
    
    async def initialize(self) -> None:
        """Initialize the environment capturer."""
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    async def capture_environment(self, experiment_id: str, 
                                capture_level: str = "full") -> Dict[str, Any]:
        """
        Capture complete environment for an experiment.
        
        Args:
            experiment_id: Unique experiment identifier
            capture_level: Level of detail (basic, standard, full, custom)
        """
        validate_experiment_id(experiment_id)
        
        try:
            environment_data = {
                'experiment_id': experiment_id,
                'capture_timestamp': datetime.now(timezone.utc).isoformat(),
                'capture_level': capture_level,
                'platform_version': self.config.version
            }
            
            # Capture different aspects based on level
            if capture_level in ["basic", "standard", "full"]:
                environment_data.update(await self._capture_system_info())
                environment_data.update(await self._capture_python_environment())
                environment_data.update(await self._capture_environment_variables())
            
            if capture_level in ["standard", "full"]:
                environment_data.update(await self._capture_hardware_info())
                environment_data.update(await self._capture_gpu_info())
                environment_data.update(await self._capture_process_info())
            
            if capture_level == "full":
                environment_data.update(await self._capture_hyperon_environment())
                environment_data.update(await self._capture_opencog_environment())
                environment_data.update(await self._capture_network_info())
                environment_data.update(await self._capture_filesystem_info())
                environment_data.update(await self._capture_security_context())
            
            # Save environment snapshot
            await self._save_environment_snapshot(experiment_id, environment_data)
            
            return environment_data
            
        except Exception as e:
            raise EnvironmentCaptureError(f"Failed to capture environment: {str(e)}")
    
    async def _capture_system_info(self) -> Dict[str, Any]:
        """Capture basic system information."""
        return {
            'system': {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'architecture': platform.architecture(),
                'hostname': platform.node(),
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                'timezone': str(datetime.now().astimezone().tzinfo)
            }
        }
    
    async def _capture_python_environment(self) -> Dict[str, Any]:
        """Capture Python environment details."""
        # Get Python version and implementation
        python_info = {
            'version': sys.version,
            'version_info': {
                'major': sys.version_info.major,
                'minor': sys.version_info.minor,
                'micro': sys.version_info.micro,
                'releaselevel': sys.version_info.releaselevel,
                'serial': sys.version_info.serial
            },
            'implementation': platform.python_implementation(),
            'executable': sys.executable,
            'path': sys.path.copy()
        }
        
        # Virtual environment detection
        virtual_env_info = {
            'in_virtualenv': hasattr(sys, 'real_prefix') or (
                hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
            ),
            'virtual_env': os.environ.get('VIRTUAL_ENV'),
            'conda_env': os.environ.get('CONDA_DEFAULT_ENV'),
            'prefix': sys.prefix,
            'base_prefix': getattr(sys, 'base_prefix', sys.prefix)
        }
        
        # Installed packages
        packages = {}
        try:
            for dist in pkg_resources.working_set:
                packages[dist.project_name] = {
                    'version': dist.version,
                    'location': dist.location,
                    'requires': [str(req) for req in dist.requires()]
                }
        except Exception as e:
            packages['_error'] = f"Failed to enumerate packages: {str(e)}"
        
        # Pip freeze equivalent
        pip_freeze = []
        try:
            result = await asyncio.create_subprocess_exec(
                sys.executable, '-m', 'pip', 'freeze',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            if result.returncode == 0:
                pip_freeze = stdout.decode().strip().split('\n')
        except Exception:
            pip_freeze = ['_error: Failed to run pip freeze']
        
        return {
            'python': python_info,
            'virtual_environment': virtual_env_info,
            'packages': packages,
            'pip_freeze': pip_freeze
        }
    
    async def _capture_environment_variables(self) -> Dict[str, Any]:
        """Capture relevant environment variables."""
        # Filter sensitive variables
        sensitive_patterns = ['password', 'secret', 'key', 'token', 'auth']
        
        filtered_env = {}
        sensitive_vars = []
        
        for key, value in os.environ.items():
            if any(pattern.lower() in key.lower() for pattern in sensitive_patterns):
                sensitive_vars.append(key)
                filtered_env[key] = '<REDACTED>'
            else:
                filtered_env[key] = value
        
        return {
            'environment_variables': filtered_env,
            'sensitive_variables': sensitive_vars,
            'total_variables': len(os.environ)
        }
    
    async def _capture_hardware_info(self) -> Dict[str, Any]:
        """Capture hardware information."""
        hardware_info = {
            'cpu': {
                'physical_cores': psutil.cpu_count(logical=False),
                'logical_cores': psutil.cpu_count(logical=True),
                'max_frequency': psutil.cpu_freq().max if psutil.cpu_freq() else None,
                'current_frequency': psutil.cpu_freq().current if psutil.cpu_freq() else None,
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'used': psutil.virtual_memory().used,
                'percentage': psutil.virtual_memory().percent
            },
            'disk': {}
        }
        
        # Disk information
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                hardware_info['disk'][partition.device] = {
                    'mountpoint': partition.mountpoint,
                    'filesystem': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percentage': (usage.used / usage.total) * 100
                }
            except PermissionError:
                continue
        
        return {'hardware': hardware_info}
    
    async def _capture_gpu_info(self) -> Dict[str, Any]:
        """Capture GPU and accelerator information."""
        gpu_info = {
            'nvidia_gpus': [],
            'amd_gpus': [],
            'other_accelerators': []
        }
        
        # NVIDIA GPUs using nvidia-ml-py or nvidia-smi
        try:
            result = await asyncio.create_subprocess_exec(
                'nvidia-smi', '--query-gpu=index,name,driver_version,memory.total,memory.used',
                '--format=csv,noheader,nounits',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                lines = stdout.decode().strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 5:
                            gpu_info['nvidia_gpus'].append({
                                'index': int(parts[0]),
                                'name': parts[1],
                                'driver_version': parts[2],
                                'memory_total_mb': int(parts[3]),
                                'memory_used_mb': int(parts[4])
                            })
        except Exception as e:
            gpu_info['nvidia_error'] = str(e)
        
        # Try to get ROCm/AMD GPU info
        try:
            result = await asyncio.create_subprocess_exec(
                'rocm-smi', '--showproductname', '--showmeminfo',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                gpu_info['amd_rocm_output'] = stdout.decode()
        except Exception:
            pass  # ROCm not available
        
        # Check for other accelerators (TPU, Intel GPUs, etc.)
        # This would require specific libraries for each accelerator type
        
        return {'accelerators': gpu_info}
    
    async def _capture_process_info(self) -> Dict[str, Any]:
        """Capture current process information."""
        process = psutil.Process()
        
        return {
            'process': {
                'pid': process.pid,
                'ppid': process.ppid(),
                'name': process.name(),
                'exe': process.exe(),
                'cmdline': process.cmdline(),
                'cwd': process.cwd(),
                'create_time': datetime.fromtimestamp(process.create_time()).isoformat(),
                'memory_info': process.memory_info()._asdict(),
                'cpu_percent': process.cpu_percent(),
                'num_threads': process.num_threads(),
                'nice': process.nice(),
                'ionice': process.ionice()._asdict() if hasattr(process, 'ionice') else None
            }
        }
    
    async def _capture_hyperon_environment(self) -> Dict[str, Any]:
        """Capture Hyperon-specific environment information."""
        hyperon_info = {
            'hyperon_available': False,
            'hyperon_path': self.config.hyperon_path,
            'metta_interpreter': self.config.metta_interpreter,
            'pln_config': {},
            'atomspace_config': {}
        }
        
        # Check if Hyperon is available
        try:
            import hyperon
            hyperon_info['hyperon_available'] = True
            hyperon_info['hyperon_version'] = getattr(hyperon, '__version__', 'unknown')
            
            # Get Hyperon configuration
            # This would depend on specific Hyperon API
            
        except ImportError:
            hyperon_info['hyperon_import_error'] = "Hyperon not available"
        except Exception as e:
            hyperon_info['hyperon_error'] = str(e)
        
        # Check for MeTTa interpreter
        if self.config.metta_interpreter:
            try:
                result = await asyncio.create_subprocess_exec(
                    self.config.metta_interpreter, '--version',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    hyperon_info['metta_version'] = stdout.decode().strip()
                else:
                    hyperon_info['metta_error'] = stderr.decode().strip()
            except Exception as e:
                hyperon_info['metta_check_error'] = str(e)
        
        return {'hyperon': hyperon_info}
    
    async def _capture_opencog_environment(self) -> Dict[str, Any]:
        """Capture OpenCog-specific environment information."""
        opencog_info = {
            'opencog_available': False,
            'atomspace_available': False,
            'pln_available': False,
            'moses_available': False
        }
        
        # Check OpenCog components
        try:
            from opencog.atomspace import AtomSpace
            opencog_info['atomspace_available'] = True
            opencog_info['atomspace_version'] = getattr(AtomSpace, '__version__', 'unknown')
        except ImportError:
            pass
        except Exception as e:
            opencog_info['atomspace_error'] = str(e)
        
        try:
            from opencog.pln import ForwardChainer
            opencog_info['pln_available'] = True
        except ImportError:
            pass
        except Exception as e:
            opencog_info['pln_error'] = str(e)
        
        try:
            import moses
            opencog_info['moses_available'] = True
            opencog_info['moses_version'] = getattr(moses, '__version__', 'unknown')
        except ImportError:
            pass
        except Exception as e:
            opencog_info['moses_error'] = str(e)
        
        return {'opencog': opencog_info}
    
    async def _capture_network_info(self) -> Dict[str, Any]:
        """Capture network configuration."""
        network_info = {
            'interfaces': {},
            'connections': []
        }
        
        # Network interfaces
        for interface, addrs in psutil.net_if_addrs().items():
            network_info['interfaces'][interface] = []
            for addr in addrs:
                network_info['interfaces'][interface].append({
                    'family': addr.family.name,
                    'address': addr.address,
                    'netmask': addr.netmask,
                    'broadcast': addr.broadcast,
                    'ptp': addr.ptp
                })
        
        # Network statistics
        net_io = psutil.net_io_counters()
        if net_io:
            network_info['io_stats'] = net_io._asdict()
        
        # Active connections (limited for security)
        try:
            connections = psutil.net_connections(kind='inet')
            network_info['connection_count'] = len(connections)
            network_info['listening_ports'] = [
                conn.laddr.port for conn in connections 
                if conn.status == psutil.CONN_LISTEN
            ]
        except psutil.AccessDenied:
            network_info['connections_access_denied'] = True
        
        return {'network': network_info}
    
    async def _capture_filesystem_info(self) -> Dict[str, Any]:
        """Capture filesystem information."""
        filesystem_info = {
            'working_directory': os.getcwd(),
            'temp_directory': os.path.expandvars('$TMPDIR') or '/tmp',
            'home_directory': os.path.expanduser('~'),
            'permissions': {},
            'mount_points': []
        }
        
        # Check permissions on key directories
        key_dirs = [
            os.getcwd(),
            self.config.base_path,
            os.path.expanduser('~'),
            '/tmp'
        ]
        
        for dir_path in key_dirs:
            if os.path.exists(dir_path):
                stat_info = os.stat(dir_path)
                filesystem_info['permissions'][dir_path] = {
                    'readable': os.access(dir_path, os.R_OK),
                    'writable': os.access(dir_path, os.W_OK),
                    'executable': os.access(dir_path, os.X_OK),
                    'mode': oct(stat_info.st_mode)[-3:],
                    'owner': stat_info.st_uid,
                    'group': stat_info.st_gid
                }
        
        # Mount points
        for partition in psutil.disk_partitions():
            filesystem_info['mount_points'].append({
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'filesystem': partition.fstype,
                'options': partition.opts
            })
        
        return {'filesystem': filesystem_info}
    
    async def _capture_security_context(self) -> Dict[str, Any]:
        """Capture security context information."""
        security_info = {
            'user_id': os.getuid() if hasattr(os, 'getuid') else None,
            'group_id': os.getgid() if hasattr(os, 'getgid') else None,
            'effective_user_id': os.geteuid() if hasattr(os, 'geteuid') else None,
            'effective_group_id': os.getegid() if hasattr(os, 'getegid') else None,
            'umask': None,
            'capabilities': [],
            'selinux_context': None,
            'apparmor_profile': None
        }
        
        # Get umask (temporarily change and restore)
        if hasattr(os, 'umask'):
            try:
                current_umask = os.umask(0o022)
                os.umask(current_umask)
                security_info['umask'] = oct(current_umask)
            except Exception:
                pass
        
        # Check for SELinux
        try:
            with open('/proc/self/attr/current', 'r') as f:
                security_info['selinux_context'] = f.read().strip()
        except (FileNotFoundError, PermissionError):
            pass
        
        # Check for AppArmor
        try:
            with open('/proc/self/attr/apparmor/current', 'r') as f:
                security_info['apparmor_profile'] = f.read().strip()
        except (FileNotFoundError, PermissionError):
            pass
        
        return {'security': security_info}
    
    async def _save_environment_snapshot(self, experiment_id: str, 
                                       environment_data: Dict[str, Any]) -> None:
        """Save environment snapshot to file."""
        snapshot_file = self.snapshots_dir / f"{experiment_id}_environment.json"
        
        try:
            with open(snapshot_file, 'w') as f:
                json.dump(environment_data, f, indent=2, default=str)
        except Exception as e:
            raise EnvironmentCaptureError(f"Failed to save environment snapshot: {str(e)}")
    
    async def load_environment_snapshot(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Load environment snapshot from file."""
        snapshot_file = self.snapshots_dir / f"{experiment_id}_environment.json"
        
        if not snapshot_file.exists():
            return None
        
        try:
            with open(snapshot_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise EnvironmentCaptureError(f"Failed to load environment snapshot: {str(e)}")
    
    async def compare_environments(self, env1: Dict[str, Any], 
                                 env2: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two environment snapshots."""
        comparison = {
            'identical': False,
            'differences': [],
            'compatibility_score': 0.0,
            'critical_differences': [],
            'warnings': []
        }
        
        # Check system compatibility
        if env1.get('system', {}).get('platform') != env2.get('system', {}).get('platform'):
            comparison['critical_differences'].append(
                f"Platform mismatch: {env1.get('system', {}).get('platform')} vs {env2.get('system', {}).get('platform')}"
            )
        
        # Check Python version
        if env1.get('python', {}).get('version') != env2.get('python', {}).get('version'):
            comparison['critical_differences'].append(
                f"Python version mismatch: {env1.get('python', {}).get('version')} vs {env2.get('python', {}).get('version')}"
            )
        
        # Check package differences
        packages1 = env1.get('packages', {})
        packages2 = env2.get('packages', {})
        
        all_packages = set(packages1.keys()) | set(packages2.keys())
        package_differences = []
        
        for package in all_packages:
            if package not in packages1:
                package_differences.append(f"Package {package} missing in environment 1")
            elif package not in packages2:
                package_differences.append(f"Package {package} missing in environment 2")
            elif packages1[package].get('version') != packages2[package].get('version'):
                package_differences.append(
                    f"Package {package} version mismatch: {packages1[package].get('version')} vs {packages2[package].get('version')}"
                )
        
        comparison['differences'].extend(package_differences)
        
        # Calculate compatibility score
        total_checks = len(all_packages) + 5  # packages + system checks
        issues = len(comparison['critical_differences']) + len(comparison['differences'])
        comparison['compatibility_score'] = max(0.0, 1.0 - (issues / total_checks))
        
        comparison['identical'] = len(comparison['differences']) == 0 and len(comparison['critical_differences']) == 0
        
        return comparison
    
    async def generate_reproducibility_requirements(self, experiment_id: str) -> Dict[str, Any]:
        """Generate requirements for reproducing an experiment."""
        environment = await self.load_environment_snapshot(experiment_id)
        
        if not environment:
            raise EnvironmentCaptureError(f"No environment snapshot found for experiment {experiment_id}")
        
        requirements = {
            'system_requirements': {
                'platform': environment.get('system', {}).get('platform'),
                'architecture': environment.get('system', {}).get('architecture'),
                'min_memory_gb': (environment.get('hardware', {}).get('memory', {}).get('total', 0)) // (1024**3),
                'min_disk_space_gb': 10  # Default minimum
            },
            'python_requirements': {
                'version': environment.get('python', {}).get('version_info', {}),
                'pip_requirements': environment.get('pip_freeze', [])
            },
            'environment_variables': {
                key: value for key, value in environment.get('environment_variables', {}).items()
                if not key.endswith('PASSWORD') and not key.endswith('SECRET')
            },
            'accelerator_requirements': environment.get('accelerators', {}),
            'hyperon_requirements': environment.get('hyperon', {}),
            'opencog_requirements': environment.get('opencog', {})
        }
        
        return requirements
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on environment capturer."""
        try:
            # Check snapshots directory
            snapshots_accessible = self.snapshots_dir.exists()
            
            # Test basic system info capture
            system_info = await self._capture_system_info()
            system_capture_working = 'system' in system_info
            
            return {
                'status': 'healthy',
                'snapshots_dir': snapshots_accessible,
                'system_capture': system_capture_working,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }