# Kenny AGI Compute Resource Pooling System

A comprehensive compute resource pooling system with dynamic resource allocation, advanced scheduling algorithms, fault tolerance, and support for multiple compute providers including Kubernetes, Slurm, and custom schedulers.

## 🌟 Features

### Core Infrastructure
- **Dynamic Resource Allocation**: Intelligent allocation across multiple providers
- **Advanced Queue Management**: Priority-based resource allocation with multiple scheduling strategies
- **Fair-Share Algorithms**: Multi-tenant resource sharing with configurable policies
- **Preemption & Migration**: Job preemption with live migration capabilities
- **Fault Tolerance**: Automatic checkpointing, failure detection, and recovery

### Resource Managers
- **GPU Pool Manager**: Support for NVIDIA, AMD, and Intel GPUs with utilization monitoring
- **CPU Pool Manager**: Multi-architecture support (x86_64, ARM64, RISC-V) with NUMA awareness
- **Memory Pool Manager**: NUMA-aware allocation with huge pages and swap management
- **Storage Pool Manager**: Tiered storage with distributed datasets support
- **Network Manager**: Bandwidth allocation and QoS management

### Scheduling Algorithms
- **FIFO**: First In, First Out scheduling
- **Priority Queue**: Priority-based job scheduling
- **Fair Queuing**: Fair resource sharing among users
- **Backfill Scheduling**: Maximum resource utilization with gap filling
- **Gang Scheduling**: Coordinated scheduling for distributed jobs
- **Elastic Scheduling**: Dynamic resource scaling based on demand
- **Deadline-Aware**: Priority scheduling based on job deadlines

### Monitoring & Analytics
- **Real-time Dashboards**: Resource utilization and job progress monitoring
- **Predictive Analytics**: Job completion time and resource demand prediction
- **Cost Allocation**: Per-user and per-project resource usage tracking
- **Anomaly Detection**: Automated detection of resource waste and inefficiencies
- **Capacity Planning**: Intelligent recommendations for resource scaling

### Integrations
- **Kubernetes**: Native integration with Kubernetes clusters
- **Slurm**: Support for Slurm Workload Manager
- **Custom Schedulers**: Extensible API for custom scheduler integration

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kenny AGI Compute Pool                       │
├─────────────────────────────────────────────────────────────────┤
│  Core Components                                                │
│  ├── Pool Manager          ├── Job Scheduler                    │
│  ├── Resource Allocator    ├── Fair Share Manager              │
│  ├── Preemption Manager    └── Queue Management                │
├─────────────────────────────────────────────────────────────────┤
│  Resource Managers                                              │
│  ├── GPU Manager           ├── Memory Manager                  │
│  ├── CPU Manager           ├── Storage Manager                 │
│  └── Network Manager                                            │
├─────────────────────────────────────────────────────────────────┤
│  Fault Tolerance                                                │
│  ├── Checkpoint Manager    ├── Recovery Manager                │
│  └── Health Monitoring                                          │
├─────────────────────────────────────────────────────────────────┤
│  Monitoring & Analytics                                         │
│  ├── Metrics Collector     ├── Performance Predictor          │
│  ├── Alert Manager         └── Dashboard                       │
├─────────────────────────────────────────────────────────────────┤
│  Integrations                                                   │
│  ├── Kubernetes           ├── Slurm                            │
│  └── Custom Schedulers                                         │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/kenny-agi/kenny.git
cd kenny/systems/compute_pool

# Install dependencies
pip install -r requirements.txt

# Optional: Install Kubernetes client
pip install kubernetes

# Optional: Ensure Slurm is installed for Slurm integration
```

### Basic Usage

```python
import asyncio
from core.pool_manager import ComputePoolManager, PoolConfig

async def main():
    # Configure the compute pool
    config = PoolConfig(
        name="my_compute_pool",
        max_concurrent_jobs=100,
        fair_share_enabled=True,
        preemption_enabled=True,
        providers=["local", "kubernetes"]
    )
    
    # Initialize the pool manager
    pool_manager = ComputePoolManager(config)
    await pool_manager.initialize()
    
    # Submit a job
    job_spec = {
        "name": "example_job",
        "command": "python my_script.py",
        "resource_requirements": {
            "cpu_cores": 4,
            "memory": 8,  # GB
            "gpu_count": 1
        },
        "user_id": "my_user",
        "priority": 2
    }
    
    job_id = await pool_manager.submit_job(job_spec)
    print(f"Submitted job: {job_id}")
    
    # Monitor job status
    status = await pool_manager.get_job_status(job_id)
    print(f"Job status: {status}")
    
    # Cleanup
    await pool_manager.shutdown()

# Run the example
asyncio.run(main())
```

### Configuration

The system uses YAML configuration files located in the `config/` directory:

- `pool_config.yaml`: Main compute pool configuration
- `kubernetes_config.yaml`: Kubernetes integration settings
- `slurm_config.yaml`: Slurm integration settings

Key configuration options:

```yaml
pool:
  name: "kenny_compute_pool"
  max_concurrent_jobs: 1000
  fair_share_enabled: true
  preemption_enabled: true
  auto_scaling_enabled: true

scheduling:
  algorithm: "fair_share"
  backfill_enabled: true
  gang_scheduling_enabled: true

resources:
  gpu:
    vendors: ["nvidia", "amd", "intel"]
    monitoring_interval: 30.0
  
  cpu:
    numa_awareness: true
    frequency_scaling: true
```

## 📊 Examples

The `examples/` directory contains comprehensive demonstrations:

### Basic Usage
```bash
python examples/basic_usage.py
```
Demonstrates fundamental compute pool operations including job submission, monitoring, and resource management.

### Kubernetes Integration
```bash
python examples/kubernetes_example.py
```
Shows how to integrate with Kubernetes clusters for container-based job execution.

### Slurm Integration
```bash
python examples/slurm_example.py
```
Demonstrates integration with Slurm Workload Manager for HPC environments.

## 🔧 Advanced Features

### Fair Share Scheduling

Configure fair share policies for multi-tenant environments:

```python
from core.fair_share import FairShareManager, FairShareModel

# Initialize fair share manager
fair_share = FairShareManager(model=FairShareModel.PROPORTIONAL)

# Add users with different share allocations
await fair_share.add_user("research_user", shares=5.0)
await fair_share.add_user("production_user", shares=3.0)
await fair_share.add_user("batch_user", shares=1.0)

# Create user groups
await fair_share.add_group("research_group", shares=10.0)
await fair_share.add_user_to_group("research_user", "research_group")
```

### Preemption and Migration

Enable job preemption with migration support:

```python
from core.preemption import PreemptionManager, PreemptionPolicy

# Configure preemption
preemption = PreemptionManager(policy=PreemptionPolicy.HYBRID)

# Report a failure to trigger recovery
await preemption.report_failure(
    failure_type=FailureType.NODE_FAILURE,
    affected_component="worker-node-1",
    description="Node became unresponsive"
)
```

### Checkpointing and Recovery

Configure automatic checkpointing:

```python
from fault_tolerance.checkpoint_manager import CheckpointManager, CheckpointPolicy

# Configure checkpointing
policy = CheckpointPolicy(
    interval_seconds=300.0,  # Checkpoint every 5 minutes
    compression_enabled=True,
    encryption_enabled=True,
    retention_days=7
)

checkpoint_manager = CheckpointManager(policy)
await checkpoint_manager.initialize()

# Create a checkpoint
checkpoint_id = await checkpoint_manager.create_checkpoint(
    job_id="my_job",
    job_state={"progress": 50, "data": "important_state"}
)
```

### Resource Monitoring

Set up comprehensive monitoring:

```python
from monitoring.metrics_collector import MetricsCollector

# Initialize metrics collection
metrics = MetricsCollector(collection_interval=10.0)
await metrics.initialize(db_path="/var/lib/kenny/metrics.db")

# Set alert thresholds
metrics.set_alert_threshold("cpu_utilization", "max", 90.0)
metrics.set_alert_threshold("memory_utilization", "max", 85.0)
metrics.set_alert_threshold("gpu_utilization", "max", 95.0)

# Record custom metrics
metrics.record_metric("custom_throughput", 150.0, labels={"service": "ml_training"})
```

## 🔌 Integration Guides

### Kubernetes Integration

1. **Setup**: Ensure kubectl is configured with cluster access
2. **Namespace**: Create a dedicated namespace for compute pool jobs
3. **RBAC**: Apply necessary roles and service accounts
4. **Resource Quotas**: Configure resource limits and quotas

```yaml
# kubernetes-setup.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: kenny-compute-pool
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kenny-compute-pool
  namespace: kenny-compute-pool
```

### Slurm Integration

1. **Installation**: Ensure Slurm commands are available in PATH
2. **Authentication**: Configure MUNGE authentication
3. **Partitions**: Set up appropriate partitions for different workloads
4. **Accounting**: Enable job accounting for resource tracking

```bash
# Test Slurm integration
sinfo  # List partitions
squeue # Show job queue
sbatch --version # Verify sbatch is available
```

## 📈 Performance Tuning

### Resource Allocation

Optimize resource allocation for your workloads:

```yaml
# pool_config.yaml
performance:
  max_parallel_jobs: 1000
  allocation_timeout: 30.0
  
  # Resource-specific tuning
  cpu:
    numa_awareness: true
    frequency_scaling: true
  
  memory:
    huge_pages_enabled: true
    numa_balancing: true
  
  gpu:
    memory_optimization: true
    power_management: true
```

### Scheduling Optimization

Configure scheduling for optimal throughput:

```yaml
scheduling:
  algorithm: "backfill"  # Use backfill for high utilization
  backfill:
    max_backfill_jobs: 100
    conservative_backfill: false
  
  fair_share:
    decay_rate: 0.9
    update_interval: 60.0
```

## 🔍 Monitoring and Troubleshooting

### Metrics and Alerts

Monitor system health and performance:

```python
# Get system metrics
pool_status = await pool_manager.get_pool_status()
utilization = pool_status["resource_utilization"]

# Check for active alerts
alerts = metrics_collector.get_active_alerts()
for alert in alerts:
    print(f"Alert: {alert['metric_name']} - {alert['severity']}")
```

### Logs and Debugging

Enable detailed logging for troubleshooting:

```yaml
# pool_config.yaml
logging:
  level: "DEBUG"
  handlers:
    file:
      enabled: true
      path: "/var/log/kenny-compute-pool.log"
      level: "DEBUG"
```

### Health Checks

Monitor component health:

```python
# Check resource manager health
gpu_status = await gpu_manager.get_pool_statistics()
cpu_status = await cpu_manager.get_pool_statistics()
memory_status = await memory_manager.get_pool_statistics()

# Verify integration connectivity
k8s_status = await k8s_integration.get_integration_status()
slurm_status = await slurm_integration.get_integration_status()
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/kenny-agi/kenny.git
cd kenny/systems/compute_pool

# Create development environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Run examples
python examples/basic_usage.py
```

### Code Structure

```
compute_pool/
├── core/                   # Core pooling infrastructure
│   ├── pool_manager.py
│   ├── resource_allocator.py
│   ├── job_scheduler.py
│   ├── fair_share.py
│   └── preemption.py
├── resources/              # Resource managers
│   ├── gpu_manager.py
│   ├── cpu_manager.py
│   ├── memory_manager.py
│   ├── storage_manager.py
│   └── network_manager.py
├── fault_tolerance/        # Fault tolerance components
│   ├── checkpoint_manager.py
│   └── recovery_manager.py
├── monitoring/             # Monitoring and analytics
│   └── metrics_collector.py
├── integrations/           # External integrations
│   ├── kubernetes_integration.py
│   └── slurm_integration.py
├── examples/               # Usage examples
├── config/                 # Configuration files
└── tests/                  # Test suite
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- The Kenny AGI team for the vision and architecture
- The open-source community for inspiration and contributions
- Kubernetes, Slurm, and other projects that made integration possible

## 📧 Support

For support, feature requests, or questions:

- Create an issue on GitHub
- Contact the Kenny AGI team
- Check the documentation and examples

---

**Kenny AGI Compute Resource Pooling System** - Intelligent resource management for the future of AI computing.