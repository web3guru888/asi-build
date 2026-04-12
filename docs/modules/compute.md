# Compute

> **Maturity**: `alpha` · **Adapter**: `ComputeBlackboardAdapter`

Compute resource management and job scheduling for distributed ASI workloads. Provides a compute pool manager for tracking available resources, a resource allocator for intelligent assignment, a job scheduler for prioritized task execution, metrics collection for utilization monitoring, and predictive analytics for capacity planning.

## Key Classes

| Class | Description |
|-------|-------------|
| `ComputePoolManager` | Compute pool lifecycle management |
| `ResourceAllocator` | Intelligent resource assignment |
| `JobScheduler` | Priority-based job scheduling |
| `MetricsCollector` | Resource utilization monitoring |
| `ResourcePredictor` | Capacity planning analytics |

## Example Usage

```python
from asi_build.compute import JobScheduler, ResourceAllocator
scheduler = JobScheduler()
allocator = ResourceAllocator(max_cpus=8, max_memory_gb=32)
job_id = scheduler.submit("train_model", resources=allocator.allocate(cpus=4, memory_gb=16))
status = scheduler.get_status(job_id)
```

## Blackboard Integration

ComputeBlackboardAdapter publishes job status updates, resource utilization metrics, and allocation events; consumes workload requests from other modules for centralized scheduling.
