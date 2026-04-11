"""
Tests for asi_build.compute module.

All 4 core files import cleanly:
- job_scheduler (Job, JobQueue, JobScheduler, etc.)
- resource_allocator (ResourceAllocator, LocalProvider, etc.)
- metrics_collector (MetricsCollector, MetricSeries, etc.)
- pool_manager (ComputePoolManager, PoolConfig) — imports from sub-modules

Strategy: test synchronous logic directly; for async methods use asyncio.run().
Pool manager depends on many sub-modules — test its dataclasses and state
management, mock heavy async initialization.
"""

import pytest
pytest.importorskip("psutil")
import asyncio
import time
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock

from asi_build.compute.core.job_scheduler import (
    Job,
    JobStatus,
    JobPriority,
    JobQueue,
    JobScheduler,
    SchedulingAlgorithm,
    SchedulingPolicy,
)
from asi_build.compute.core.resource_allocator import (
    ResourceAllocator,
    ResourceRequest,
    ResourceAllocation,
    ResourceType,
    AllocationStatus,
    LocalProvider,
    ResourceProvider,
)
from asi_build.compute.monitoring.metrics_collector import (
    MetricsCollector,
    MetricType,
    MetricPoint,
    MetricSeries,
)
from asi_build.compute.core.pool_manager import (
    ComputePoolManager,
    PoolConfig,
    PoolStatus,
)


# ===== helpers =====

def _run(coro):
    """Run async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ===================================================================
# Job dataclass
# ===================================================================

class TestJob:

    def test_defaults(self):
        j = Job()
        assert j.status == JobStatus.PENDING
        assert j.priority == 3
        assert j.progress == 0

    def test_from_spec(self):
        spec = {"name": "train_model", "user_id": "alice", "priority": 1}
        j = Job.from_spec(spec)
        assert j.name == "train_model"
        assert j.user_id == "alice"
        assert j.priority == 1

    def test_from_spec_generates_id(self):
        j = Job.from_spec({})
        assert j.job_id  # non-empty

    def test_to_dict(self):
        j = Job(name="test")
        d = j.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "pending"
        assert "resource_requirements" in d

    def test_to_dict_roundtrip(self):
        j = Job(name="x", priority=2, user_id="bob")
        d = j.to_dict()
        j2 = Job.from_spec(d)
        assert j2.name == "x"
        assert j2.user_id == "bob"


# ===================================================================
# JobStatus / JobPriority enums
# ===================================================================

class TestEnums:

    def test_job_statuses(self):
        assert len(JobStatus) == 7
        assert JobStatus.RUNNING.value == "running"

    def test_job_priorities(self):
        assert JobPriority.CRITICAL.value == 1
        assert JobPriority.BATCH.value == 5

    def test_scheduling_algorithms(self):
        assert len(SchedulingAlgorithm) == 8

    def test_resource_types(self):
        assert ResourceType.GPU.value == "gpu"

    def test_allocation_statuses(self):
        assert AllocationStatus.ACTIVE.value == "active"


# ===================================================================
# SchedulingPolicy
# ===================================================================

class TestSchedulingPolicy:

    def test_defaults(self):
        p = SchedulingPolicy()
        assert p.algorithm == SchedulingAlgorithm.FAIR_SHARE
        assert p.max_concurrent_jobs == 1000
        assert p.aging_enabled is True

    def test_custom(self):
        p = SchedulingPolicy(
            algorithm=SchedulingAlgorithm.PRIORITY,
            max_concurrent_jobs=10,
        )
        assert p.algorithm == SchedulingAlgorithm.PRIORITY


# ===================================================================
# JobQueue
# ===================================================================

class TestJobQueue:

    def _make_queue(self, alg=SchedulingAlgorithm.PRIORITY):
        return JobQueue("test", SchedulingPolicy(algorithm=alg))

    def test_submit_job(self):
        q = self._make_queue()
        j = Job(user_id="alice")
        assert q.submit_job(j) is True
        assert q._stats["jobs_submitted"] == 1

    def test_user_limit(self):
        q = self._make_queue()
        q.policy.max_jobs_per_user = 2
        j1 = Job(user_id="alice")
        j2 = Job(user_id="alice")
        j3 = Job(user_id="alice")
        assert q.submit_job(j1) is True
        assert q.submit_job(j2) is True
        assert q.submit_job(j3) is False  # limit reached

    def test_capacity_limit(self):
        q = self._make_queue()
        q.policy.max_concurrent_jobs = 1
        j1 = Job(user_id="a")
        j2 = Job(user_id="b")
        assert q.submit_job(j1) is True
        assert q.submit_job(j2) is False

    def test_priority_scheduling(self):
        q = self._make_queue(SchedulingAlgorithm.PRIORITY)
        j_low = Job(user_id="a", priority=5)
        j_high = Job(user_id="a", priority=1)
        q.submit_job(j_low)
        q.submit_job(j_high)
        next_job = q.get_next_job({})
        assert next_job.priority == 1

    def test_fifo_scheduling(self):
        q = self._make_queue(SchedulingAlgorithm.FIFO)
        j1 = Job(user_id="a", priority=5)
        j2 = Job(user_id="a", priority=1)
        q.submit_job(j1)
        q.submit_job(j2)
        # FIFO uses the heap which already sorts by priority
        next_job = q.get_next_job({})
        assert next_job is not None

    def test_start_job(self):
        q = self._make_queue()
        j = Job(user_id="a")
        q.submit_job(j)
        next_job = q.get_next_job({})
        assert q.start_job(next_job) is True
        assert next_job.status == JobStatus.RUNNING
        assert next_job.started_at is not None

    def test_complete_job(self):
        q = self._make_queue()
        j = Job(user_id="a")
        q.submit_job(j)
        q.start_job(q.get_next_job({}))
        assert q.complete_job(j.job_id, success=True) is True
        assert j.status == JobStatus.COMPLETED
        assert q._stats["jobs_completed"] == 1

    def test_complete_job_failure(self):
        q = self._make_queue()
        j = Job(user_id="a")
        q.submit_job(j)
        q.start_job(q.get_next_job({}))
        q.complete_job(j.job_id, success=False)
        assert j.status == JobStatus.FAILED
        assert q._stats["jobs_failed"] == 1

    def test_cancel_running(self):
        q = self._make_queue()
        j = Job(user_id="a")
        q.submit_job(j)
        q.start_job(q.get_next_job({}))
        assert q.cancel_job(j.job_id) is True
        assert j.status == JobStatus.CANCELLED

    def test_cancel_pending(self):
        q = self._make_queue()
        j = Job(user_id="a")
        q.submit_job(j)
        assert q.cancel_job(j.job_id) is True
        assert j.status == JobStatus.CANCELLED

    def test_cancel_nonexistent(self):
        q = self._make_queue()
        assert q.cancel_job("fake_id") is False

    def test_queue_status(self):
        q = self._make_queue()
        j = Job(user_id="a")
        q.submit_job(j)
        status = q.get_queue_status()
        assert status["name"] == "test"
        assert status["pending_jobs"] == 1

    def test_deadline_scheduling(self):
        q = self._make_queue(SchedulingAlgorithm.DEADLINE)
        j1 = Job(user_id="a", deadline=time.time() + 1000, priority=3)
        j2 = Job(user_id="a", deadline=time.time() + 10, priority=5)
        q.submit_job(j1)
        q.submit_job(j2)
        next_job = q.get_next_job({})
        # j2 has closer deadline → higher urgency
        assert next_job.job_id == j2.job_id

    def test_gang_scheduling(self):
        q = self._make_queue(SchedulingAlgorithm.GANG)
        j1 = Job(user_id="a", gang_id="g1", gang_size=2, priority=3)
        j2 = Job(user_id="a", gang_id="g1", gang_size=2, priority=3)
        q.submit_job(j1)
        q.submit_job(j2)
        next_job = q.get_next_job({})
        assert next_job is not None
        assert next_job.gang_id == "g1"

    def test_backfill_scheduling(self):
        q = self._make_queue(SchedulingAlgorithm.BACKFILL)
        j = Job(user_id="a", resource_requirements={"cpu": 2}, priority=3)
        q.submit_job(j)
        next_job = q.get_next_job({"cpu": 4})
        assert next_job is not None

    def test_can_job_run(self):
        q = self._make_queue()
        j = Job(resource_requirements={"cpu": 4, "gpu": 2})
        assert q._can_job_run(j, {"cpu": 8, "gpu": 4}) is True
        assert q._can_job_run(j, {"cpu": 2, "gpu": 4}) is False


# ===================================================================
# JobScheduler
# ===================================================================

class TestJobScheduler:

    def test_init(self):
        s = JobScheduler(max_concurrent_jobs=500)
        assert s.max_concurrent_jobs == 500

    def test_initialize(self):
        s = JobScheduler()
        _run(s.initialize())
        assert "default" in s.queues

    def test_create_queue(self):
        s = JobScheduler()
        _run(s.initialize())
        created = _run(s.create_queue("gpu", SchedulingPolicy(algorithm=SchedulingAlgorithm.PRIORITY)))
        assert created is True
        assert "gpu" in s.queues

    def test_create_duplicate_queue(self):
        s = JobScheduler()
        _run(s.initialize())
        assert _run(s.create_queue("default", SchedulingPolicy())) is False

    def test_submit_and_get_status(self):
        s = JobScheduler()
        _run(s.initialize())
        job_id = _run(s.submit_job({"name": "test", "user_id": "alice"}))
        status = _run(s.get_job_status(job_id))
        assert status is not None
        assert status["name"] == "test"

    def test_submit_bad_queue(self):
        s = JobScheduler()
        _run(s.initialize())
        with pytest.raises(ValueError):
            _run(s.submit_job({"name": "test"}, queue_name="nonexistent"))

    def test_start_job(self):
        s = JobScheduler()
        _run(s.initialize())
        job_id = _run(s.submit_job({"name": "x", "user_id": "a"}))
        # Get next jobs
        jobs = _run(s.get_next_jobs({}))
        assert len(jobs) > 0
        assert _run(s.start_job(jobs[0].job_id)) is True

    def test_complete_job(self):
        s = JobScheduler()
        _run(s.initialize())
        job_id = _run(s.submit_job({"name": "x", "user_id": "a"}))
        jobs = _run(s.get_next_jobs({}))
        _run(s.start_job(jobs[0].job_id))
        assert _run(s.complete_job(jobs[0].job_id)) is True

    def test_cancel_job(self):
        s = JobScheduler()
        _run(s.initialize())
        job_id = _run(s.submit_job({"name": "x", "user_id": "a"}))
        assert _run(s.cancel_job(job_id)) is True

    def test_scheduler_status(self):
        s = JobScheduler()
        _run(s.initialize())
        status = _run(s.get_scheduler_status())
        assert "queues" in status
        assert "default" in status["queues"]

    def test_elastic_job_group(self):
        s = JobScheduler()
        _run(s.initialize())
        jobs = [Job(user_id="a") for _ in range(3)]
        assert _run(s.create_elastic_job_group("eg1", jobs)) is True
        assert _run(s.create_elastic_job_group("eg1", jobs)) is False  # duplicate


# ===================================================================
# ResourceRequest & ResourceAllocation
# ===================================================================

class TestResourceRequest:

    def test_defaults(self):
        r = ResourceRequest()
        assert r.gpu_count == 0
        assert r.priority == 5

    def test_to_dict(self):
        r = ResourceRequest(gpu_count=4, cpu_cores=16, memory=64)
        d = r.to_dict()
        assert d["gpu_count"] == 4
        assert d["cpu_cores"] == 16

    def test_custom(self):
        r = ResourceRequest(
            gpu_count=2,
            memory=32,
            duration=3600,
            user_id="bob",
        )
        assert r.duration == 3600
        assert r.user_id == "bob"


class TestResourceAllocation:

    def test_defaults(self):
        a = ResourceAllocation()
        assert a.status == AllocationStatus.PENDING

    def test_to_dict(self):
        a = ResourceAllocation(provider="local", resources={"gpu": 2})
        d = a.to_dict()
        assert d["provider"] == "local"
        assert d["status"] == "pending"


# ===================================================================
# LocalProvider
# ===================================================================

class TestLocalProvider:

    def test_init(self):
        lp = LocalProvider()
        assert lp.provider_type == "local"
        assert lp.total_resources["gpu_count"] == 8

    def test_available_resources(self):
        lp = LocalProvider()
        avail = _run(lp.get_available_resources())
        assert avail["cpu_cores"] == 32

    def test_allocate_success(self):
        lp = LocalProvider()
        req = ResourceRequest(gpu_count=2, cpu_cores=4, memory=16)
        alloc = _run(lp.allocate_resources(req))
        assert alloc is not None
        assert alloc.status == AllocationStatus.ACTIVE
        # Available should decrease
        avail = _run(lp.get_available_resources())
        assert avail["gpu_count"] == 6

    def test_allocate_insufficient(self):
        lp = LocalProvider()
        req = ResourceRequest(gpu_count=100)  # way too many
        alloc = _run(lp.allocate_resources(req))
        assert alloc is None

    def test_deallocate(self):
        lp = LocalProvider()
        req = ResourceRequest(gpu_count=2, cpu_cores=4)
        alloc = _run(lp.allocate_resources(req))
        assert alloc is not None
        success = _run(lp.deallocate_resources(alloc))
        assert success is True
        avail = _run(lp.get_available_resources())
        assert avail["gpu_count"] == 8  # restored

    def test_utilization(self):
        lp = LocalProvider()
        req = ResourceRequest(gpu_count=4)
        _run(lp.allocate_resources(req))
        util = _run(lp.get_utilization())
        assert util["local_gpu_count"] == 50.0  # 4/8 * 100

    def test_health_check(self):
        lp = LocalProvider()
        assert _run(lp.health_check()) is True
        lp.enabled = False
        assert _run(lp.health_check()) is False

    def test_duration_sets_expiry(self):
        lp = LocalProvider()
        req = ResourceRequest(gpu_count=1, duration=60.0)
        alloc = _run(lp.allocate_resources(req))
        assert alloc.expires_at is not None
        assert alloc.expires_at > time.time()


# ===================================================================
# ResourceAllocator
# ===================================================================

class TestResourceAllocator:

    def test_init(self):
        ra = ResourceAllocator()
        assert len(ra.providers) == 0

    def test_initialize_adds_local(self):
        ra = ResourceAllocator()
        _run(ra.initialize())
        assert "local" in ra.providers

    def test_add_remove_provider(self):
        ra = ResourceAllocator()
        p = LocalProvider("custom")
        _run(ra.add_provider(p))
        assert "custom" in ra.providers
        assert _run(ra.remove_provider("custom")) is True
        assert "custom" not in ra.providers

    def test_allocate_balanced(self):
        ra = ResourceAllocator()
        _run(ra.initialize())
        req = ResourceRequest(cpu_cores=4)
        alloc = _run(ra.allocate_resources(req, strategy="balanced"))
        assert alloc is not None
        assert ra._stats["successful_allocations"] == 1

    def test_allocate_best_fit(self):
        ra = ResourceAllocator()
        _run(ra.initialize())
        req = ResourceRequest(cpu_cores=2)
        alloc = _run(ra.allocate_resources(req, strategy="best_fit"))
        assert alloc is not None

    def test_allocate_first_fit(self):
        ra = ResourceAllocator()
        _run(ra.initialize())
        req = ResourceRequest(memory=8)
        alloc = _run(ra.allocate_resources(req, strategy="first_fit"))
        assert alloc is not None

    def test_allocate_cost_optimized(self):
        ra = ResourceAllocator()
        _run(ra.initialize())
        req = ResourceRequest(cpu_cores=1)
        alloc = _run(ra.allocate_resources(req, strategy="cost_optimized"))
        assert alloc is not None

    def test_allocate_failure(self):
        ra = ResourceAllocator()
        _run(ra.initialize())
        req = ResourceRequest(gpu_count=999)
        alloc = _run(ra.allocate_resources(req))
        assert alloc is None
        assert ra._stats["failed_allocations"] == 1

    def test_deallocate_by_dict(self):
        ra = ResourceAllocator()
        _run(ra.initialize())
        req = ResourceRequest(cpu_cores=4)
        alloc = _run(ra.allocate_resources(req))
        assert alloc is not None
        # Deallocate by matching resource dict
        success = _run(ra.deallocate_resources(alloc.resources))
        assert success is True

    def test_get_availability(self):
        ra = ResourceAllocator()
        _run(ra.initialize())
        avail = _run(ra.get_resource_availability())
        assert "local" in avail

    def test_get_utilization(self):
        ra = ResourceAllocator()
        _run(ra.initialize())
        util = _run(ra.get_total_utilization())
        assert isinstance(util, dict)

    def test_statistics(self):
        ra = ResourceAllocator()
        _run(ra.initialize())
        stats = _run(ra.get_statistics())
        assert "total_requests" in stats
        assert "active_allocations" in stats

    def test_cleanup_expired(self):
        ra = ResourceAllocator()
        _run(ra.initialize())
        # Create an allocation that's already expired
        req = ResourceRequest(cpu_cores=1, duration=0.001)
        alloc = _run(ra.allocate_resources(req))
        assert alloc is not None
        time.sleep(0.01)
        alloc.expires_at = time.time() - 1  # force expired
        count = _run(ra.cleanup_expired_allocations())
        assert count >= 1

    def test_timing_stats(self):
        ra = ResourceAllocator()
        _run(ra.initialize())
        req = ResourceRequest(cpu_cores=1)
        _run(ra.allocate_resources(req))
        assert ra._stats["average_allocation_time"] > 0


# ===================================================================
# MetricPoint
# ===================================================================

class TestMetricPoint:

    def test_creation(self):
        p = MetricPoint(
            metric_id="m1", name="cpu_usage", value=75.0,
            timestamp=time.time(), metric_type=MetricType.GAUGE
        )
        assert p.value == 75.0

    def test_to_dict(self):
        p = MetricPoint(
            metric_id="m1", name="cpu_usage", value=50.0,
            timestamp=1000.0, labels={"host": "node1"}
        )
        d = p.to_dict()
        assert d["name"] == "cpu_usage"
        assert d["labels"]["host"] == "node1"


# ===================================================================
# MetricSeries
# ===================================================================

class TestMetricSeries:

    def test_add_point(self):
        s = MetricSeries(name="test", metric_type=MetricType.GAUGE)
        s.add_point(1.0)
        s.add_point(2.0)
        assert len(s.points) == 2

    def test_get_latest(self):
        s = MetricSeries(name="test", metric_type=MetricType.GAUGE)
        assert s.get_latest() is None
        s.add_point(42.0)
        assert s.get_latest().value == 42.0

    def test_get_range(self):
        s = MetricSeries(name="test", metric_type=MetricType.GAUGE)
        now = time.time()
        s.add_point(1.0, now - 10)
        s.add_point(2.0, now - 5)
        s.add_point(3.0, now)
        results = s.get_range(now - 7, now + 1)
        assert len(results) == 2  # 2.0 and 3.0

    def test_statistics(self):
        s = MetricSeries(name="test", metric_type=MetricType.GAUGE)
        now = time.time()
        for i in range(10):
            s.add_point(float(i), now - i)
        stats = s.get_statistics(window_seconds=20)
        assert stats["count"] == 10
        assert stats["min"] == 0.0
        assert stats["max"] == 9.0

    def test_statistics_empty(self):
        s = MetricSeries(name="test", metric_type=MetricType.GAUGE)
        assert s.get_statistics() == {}

    def test_maxlen(self):
        s = MetricSeries(name="test", metric_type=MetricType.GAUGE)
        for i in range(1100):
            s.add_point(float(i))
        assert len(s.points) == 1000  # maxlen


# ===================================================================
# MetricsCollector
# ===================================================================

class TestMetricsCollector:

    def test_init(self):
        mc = MetricsCollector(collection_interval=5.0)
        assert mc.collection_interval == 5.0
        assert len(mc.metrics) == 0

    def test_record_metric(self):
        mc = MetricsCollector()
        mc.record_metric("cpu_usage", 75.0)
        assert mc._stats["total_points"] == 1
        assert mc._stats["total_metrics"] == 1

    def test_record_with_labels(self):
        mc = MetricsCollector()
        mc.record_metric("latency", 0.5, labels={"endpoint": "/api"})
        mc.record_metric("latency", 0.3, labels={"endpoint": "/health"})
        assert mc._stats["total_metrics"] == 2

    def test_record_counter(self):
        mc = MetricsCollector()
        mc.record_counter("requests")
        mc.record_counter("requests")
        val = mc.get_metric_value("requests")
        assert val is not None

    def test_record_timer(self):
        mc = MetricsCollector()
        mc.record_timer("response_time", 0.123)
        assert mc.get_metric_value("response_time") == 0.123

    def test_record_histogram(self):
        mc = MetricsCollector()
        mc.record_histogram("payload_size", 1024.5)
        assert mc.get_metric_value("payload_size") == 1024.5

    def test_get_metric(self):
        mc = MetricsCollector()
        mc.record_metric("test", 1.0)
        series = mc.get_metric("test")
        assert series is not None
        assert series.name == "test"

    def test_get_metric_missing(self):
        mc = MetricsCollector()
        assert mc.get_metric("nonexistent") is None
        assert mc.get_metric_value("nonexistent") is None

    def test_query_metrics(self):
        mc = MetricsCollector()
        now = time.time()
        mc.record_metric("test", 1.0, timestamp=now - 10)
        mc.record_metric("test", 2.0, timestamp=now)
        results = mc.query_metrics("test", now - 5, now + 1)
        assert len(results) == 1  # only the second point

    def test_metrics_list(self):
        mc = MetricsCollector()
        mc.record_metric("alpha", 1.0)
        mc.record_metric("beta", 2.0)
        mc.record_metric("alpha", 3.0, labels={"x": "1"})
        names = mc.get_metrics_list()
        assert "alpha" in names
        assert "beta" in names

    def test_alert_threshold_max(self):
        mc = MetricsCollector()
        mc.set_alert_threshold("cpu", "max", 90.0)
        mc.record_metric("cpu", 95.0)  # exceeds threshold
        alerts = mc.get_active_alerts()
        assert len(alerts) == 1
        assert alerts[0]["threshold_type"] == "max"

    def test_alert_threshold_min(self):
        mc = MetricsCollector()
        mc.set_alert_threshold("memory_free", "min", 100.0)
        mc.record_metric("memory_free", 50.0)  # below min
        alerts = mc.get_active_alerts()
        assert len(alerts) == 1

    def test_alert_no_duplicate(self):
        mc = MetricsCollector()
        mc.set_alert_threshold("cpu", "max", 90.0)
        mc.record_metric("cpu", 95.0)
        mc.record_metric("cpu", 96.0)  # within 5 min → no duplicate
        assert len(mc.get_active_alerts()) == 1

    def test_clear_alert(self):
        mc = MetricsCollector()
        mc.set_alert_threshold("cpu", "max", 90.0)
        mc.record_metric("cpu", 95.0)
        alerts = mc.get_active_alerts()
        assert mc.clear_alert(alerts[0]["alert_id"]) is True
        assert len(mc.get_active_alerts()) == 0

    def test_clear_nonexistent_alert(self):
        mc = MetricsCollector()
        assert mc.clear_alert("fake") is False

    def test_severity_calculation(self):
        mc = MetricsCollector()
        assert mc._calculate_severity("max", 200.0, 100.0) == "critical"
        assert mc._calculate_severity("max", 150.0, 100.0) == "high"
        assert mc._calculate_severity("max", 120.0, 100.0) == "medium"
        assert mc._calculate_severity("max", 105.0, 100.0) == "low"

    def test_collector_status(self):
        mc = MetricsCollector()
        mc.record_metric("x", 1.0)
        status = mc.get_collector_status()
        assert status["metrics_count"] == 1
        assert status["database_enabled"] is False

    def test_export_json(self):
        mc = MetricsCollector()
        now = time.time()
        mc.record_metric("test", 42.0, timestamp=now)
        exported = _run(mc.export_metrics(now - 1, now + 1, format="json"))
        data = json.loads(exported)
        assert "metrics" in data
        assert len(data["metrics"]) == 1

    def test_export_prometheus(self):
        mc = MetricsCollector()
        now = time.time()
        mc.record_metric("test", 42.0, timestamp=now)
        exported = _run(mc.export_metrics(now - 1, now + 1, format="prometheus"))
        assert "# TYPE test" in exported

    def test_export_bad_format(self):
        mc = MetricsCollector()
        with pytest.raises(ValueError):
            _run(mc.export_metrics(0, time.time(), format="xml"))

    def test_record_utilization(self):
        mc = MetricsCollector()
        _run(mc.record_utilization({"cpu": 50.0, "gpu": 75.0}))
        assert mc._stats["total_points"] == 2


# ===================================================================
# PoolConfig
# ===================================================================

class TestPoolConfig:

    def test_defaults(self):
        c = PoolConfig(name="test")
        assert c.max_concurrent_jobs == 1000
        assert c.preemption_enabled is True
        assert "local" in c.providers

    def test_custom(self):
        c = PoolConfig(name="gpu_pool", max_concurrent_jobs=10, auto_scaling_enabled=False)
        assert c.max_concurrent_jobs == 10
        assert c.auto_scaling_enabled is False


# ===================================================================
# PoolStatus enum
# ===================================================================

class TestPoolStatus:

    def test_values(self):
        assert PoolStatus.ACTIVE.value == "active"
        assert PoolStatus.SHUTDOWN.value == "shutdown"


# ===================================================================
# ComputePoolManager (constructor + state only)
#
# NOTE: ComputePoolManager.__init__ passes config.checkpoint_interval (float)
# to CheckpointManager() which expects a CheckpointPolicy — this is a
# pre-existing bug in pool_manager.py. We mock the sub-managers to test
# the pool manager's own logic.
# ===================================================================

class TestComputePoolManager:

    @pytest.fixture(autouse=True)
    def _mock_sub_managers(self, monkeypatch):
        """Mock all sub-manager constructors to avoid real initialization."""
        from asi_build.compute.core import pool_manager as pm_mod

        for cls_name in [
            "GPUPoolManager", "CPUPoolManager", "MemoryPoolManager",
            "StoragePoolManager", "NetworkManager", "MetricsCollector",
            "CheckpointManager", "RecoveryManager", "FairShareManager",
            "PreemptionManager",
        ]:
            monkeypatch.setattr(pm_mod, cls_name, lambda *a, **kw: MagicMock())

    def test_constructor(self):
        config = PoolConfig(name="test_pool")
        pm = ComputePoolManager(config)
        assert pm.status == PoolStatus.INITIALIZING
        assert pm.config.name == "test_pool"
        assert len(pm._active_jobs) == 0
        assert pm._stats["jobs_submitted"] == 0

    def test_constructor_no_fair_share(self):
        config = PoolConfig(name="test", fair_share_enabled=False)
        pm = ComputePoolManager(config)
        assert pm.fair_share_manager is None

    def test_constructor_no_preemption(self):
        config = PoolConfig(name="test", preemption_enabled=False)
        pm = ComputePoolManager(config)
        assert pm.preemption_manager is None

    def test_stats_initial(self):
        config = PoolConfig(name="test")
        pm = ComputePoolManager(config)
        assert pm._stats["jobs_completed"] == 0
        assert pm._stats["total_compute_time"] == 0.0

    def test_pool_id_generated(self):
        c1 = ComputePoolManager(PoolConfig(name="a"))
        c2 = ComputePoolManager(PoolConfig(name="b"))
        assert c1.pool_id != c2.pool_id
