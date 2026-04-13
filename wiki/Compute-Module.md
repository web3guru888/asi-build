# Compute Module

> **Status**: Alpha | **LOC**: ~11,700 | **Files**: 25 | **Path**: `src/asi_build/compute/`

The `compute` module is the **Kenny AGI Compute Resource Pooling System** — ASI:BUILD's infrastructure backbone for dynamic resource allocation, multi-provider job scheduling, fair-share prioritization, and fault-tolerant compute management across cognitive module workloads.

## Architecture Overview

```
ComputePoolManager (orchestrator)
├── Core
│   ├── ResourceAllocator      # Bin-packing allocation
│   ├── JobScheduler           # Priority queue, 10 levels
│   ├── FairShareManager       # Decaying usage history
│   └── PreemptionManager      # 6 preemption policies
├── Resources
│   ├── CPUPoolManager         # Thread affinity, NUMA
│   ├── GPUPoolManager         # MIG slicing, multi-instance
│   ├── MemoryPoolManager      # Huge pages, NUMA pinning
│   ├── NetworkManager         # QoS, RDMA, bandwidth reservation
│   └── StoragePoolManager     # Tiered storage (NVMe→SSD→HDD)
├── Fault Tolerance
│   ├── CheckpointManager      # 60s interval snapshots
│   └── RecoveryManager        # Checkpoint-restart
├── Monitoring
│   └── MetricsCollector       # Counter, Gauge, Histogram, Timer series
└── Integrations
    ├── KubernetesIntegration  # Pod scheduling, resource requests
    └── SlurmIntegration       # HPC batch submission, job arrays
```

## Pool Configuration

```python
from asi_build.compute import ComputePoolManager
from asi_build.compute.core.pool_manager import PoolConfig

config = PoolConfig(
    name="asi-build-pool",
    max_concurrent_jobs=1000,
    resource_timeout=300.0,       # 5 minutes
    preemption_enabled=True,
    fair_share_enabled=True,
    checkpoint_interval=60.0,     # 1 minute
    monitoring_interval=10.0,     # 10 seconds
    auto_scaling_enabled=True,
    providers=["local", "kubernetes", "slurm"],
    priority_levels=10,
)

pool = ComputePoolManager(config)
await pool.start()
```

## Job Scheduling

Jobs enter a priority queue with 10 priority levels. The scheduler supports:

- **Deadline-aware scheduling**: jobs with approaching deadlines get boosted
- **Priority preemption**: higher-priority jobs can interrupt lower-priority ones
- **Gang scheduling**: multi-node jobs that must start together

```python
from asi_build.compute.core.job_scheduler import Job, JobStatus

job = Job(
    job_id="phi-computation-001",
    name="IIT Phi Full Graph",
    priority=8,               # 0-9, higher = more urgent
    resource_request=ResourceRequest(cpu=4, memory_gb=16, gpu=1),
    deadline=time.time() + 3600,  # 1 hour from now
    tags={"module": "consciousness", "type": "analysis"},
)

job_id = await pool.submit_job(job)
status = await pool.get_job_status(job_id)
```

## Fair Share Scheduling

`FairShareManager` implements four algorithms to prevent resource monopolization:

| Algorithm | Description |
|-----------|-------------|
| `PROPORTIONAL` | Allocate resources proportional to declared shares |
| `LOTTERY` | Probabilistic — each share = 1 lottery ticket |
| `WFQ` | Weighted Fair Queuing — bit-by-bit round-robin |
| `DRR` | Deficit Round-Robin — handles variable job sizes |

The key innovation is **decaying usage history**:

```python
def effective_priority(self, current_time: float, decay_rate: float = 0.9) -> float:
    """Priority inversely proportional to recent usage, exponentially decayed."""
    decayed_usage = 0.0
    for timestamp, usage in self.usage_history:
        age_hours = (current_time - timestamp) / 3600.0
        decay_factor = decay_rate ** age_hours
        decayed_usage += usage * decay_factor
    
    usage_ratio = (decayed_usage + self.current_usage) / self.shares
    return self.priority_boost / max(usage_ratio, 0.1)
```

Agents that have been consuming more compute than their fair share are deprioritized. Agents that haven't run recently naturally float to the top.

## Preemption Policies

When a higher-priority job needs resources, `PreemptionManager` selects which running jobs to interrupt:

| Policy | Logic |
|--------|-------|
| `PRIORITY_BASED` | Preempt lowest-priority jobs first |
| `FAIR_SHARE` | Preempt agents who have exceeded their share |
| `DEADLINE_AWARE` | Protect jobs close to their deadline |
| `RESOURCE_BASED` | Preempt largest resource consumers first |
| `COST_BASED` | Minimize total preemption cost (checkpoint time + restart overhead) |
| `HYBRID` | Weighted combination of all signals |

Preempted jobs don't necessarily lose state — migration types include:

- `CHECKPOINT_RESTART` — save state, restart from checkpoint on new node
- `LIVE_MIGRATION` — stream memory pages to destination while running
- `CONTAINER_MIGRATION` — checkpoint OCI container, restore elsewhere
- `PROCESS_MIGRATION` — OS-level process migration (Linux only)

## Resource Managers

### CPU (`CPUPoolManager`)
- Thread affinity pinning to specific cores
- NUMA topology awareness (prefer local memory)
- Hyper-threading on/off configuration
- cgroup-based isolation

### GPU (`GPUPoolManager`)
- NVIDIA MIG (Multi-Instance GPU) slicing
- Multi-instance sharing across jobs
- PCIe topology-aware placement
- VRAM reservation and tracking

### Memory (`MemoryPoolManager`)
- Huge page allocation (2MB, 1GB)
- NUMA node pinning
- OOM killer priority (oom_score_adj)
- Swap-to-NVMe for large inactive allocations

### Network (`NetworkManager`)
- Bandwidth reservation per job
- QoS traffic shaping (HTB qdisc)
- RDMA path selection for low-latency workloads
- Ingress/egress accounting

### Storage (`StoragePoolManager`)
- Tiered storage: NVMe → SSD → HDD → distributed FS
- Hot data promotion / cold data demotion
- Distributed filesystem support (Lustre, GPFS, CephFS)
- Per-job scratch space with automatic cleanup

## Fault Tolerance

```python
# Checkpoint every 60 seconds
checkpoint_manager = CheckpointManager(interval=60.0)
await checkpoint_manager.checkpoint_job(job_id, state)

# Recovery after node failure
recovery_manager = RecoveryManager(checkpoint_manager)
await recovery_manager.recover_jobs(failed_node_id)
```

`CheckpointManager` snapshots job state to durable storage. `RecoveryManager` detects node failures (via health heartbeats) and automatically restarts affected jobs from their last checkpoint.

## Monitoring

`MetricsCollector` records four metric types with time-series storage:

```python
from asi_build.compute.monitoring.metrics_collector import MetricsCollector, MetricType

collector = MetricsCollector()

# Counter: total jobs submitted
collector.increment("jobs_submitted", labels={"provider": "kubernetes"})

# Gauge: current utilization
collector.set_gauge("gpu_utilization", value=0.87, labels={"node": "gpu-01"})

# Histogram: job duration distribution
collector.record_histogram("job_duration_seconds", value=42.3)

# Timer: scheduling latency
with collector.timer("scheduling_latency"):
    job_id = await scheduler.schedule(job)
```

Each metric series retains up to 1,000 data points (configurable). The collector stores to SQLite for persistence across restarts.

## Multi-Provider Integration

### Kubernetes
```python
from asi_build.compute.integrations.kubernetes_integration import KubernetesIntegration

k8s = KubernetesIntegration(namespace="asi-build")
await k8s.submit_pod(job, resources={"cpu": "4", "memory": "16Gi", "nvidia.com/gpu": "1"})
```

### SLURM
```python
from asi_build.compute.integrations.slurm_integration import SlurmIntegration

slurm = SlurmIntegration(partition="gpu", account="asi-build")
await slurm.submit_job(job, nodes=4, ntasks_per_node=8, time="04:00:00")
```

## Cognitive Blackboard Integration

**Planned** — Issue [#70](https://github.com/web3guru888/asi-build/issues/70) tracks `ComputeBlackboardAdapter`.

Two design options are under discussion:

**Option A — Observability only**: Publish `ComputeMetricsEntry` (utilization, queue depth) to Blackboard as read-only telemetry. Modules see resource pressure but don't control scheduling.

**Option B — Bidirectional control**: Modules publish `ComputeRequestEntry` items; adapter reads and submits to pool. Makes Blackboard the unified control plane.

See [Discussion #114](https://github.com/web3guru888/asi-build/discussions/114) for the active design conversation.

## Related Pages

- [Cognitive Blackboard](Cognitive-Blackboard) — integration target
- [Blackboard Integration Status](Blackboard-Integration-Status) — adapter tracking
- [Distributed Training](Distributed-Training) — uses compute pool for ML workloads
- [Rings Network](Rings-Network) — P2P network layer (complementary infrastructure)
- [Architecture](Architecture) — overall system design
