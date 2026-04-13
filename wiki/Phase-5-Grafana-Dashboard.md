# Phase 5 — Grafana Dashboard

This page documents the `docs/grafana/phase5.json` Grafana dashboard for Phase 5 observability.

## Quick Import

```bash
# Grafana 10.x — import via CLI
grafana-cli dashboards import docs/grafana/phase5.json

# Or use the Grafana UI: Dashboards → Import → Upload JSON file
```

## Dashboard Layout (Option A — 4-row layout)

```
┌─────────────────────────────────────────────────────┐
│  ROW 0: Rollback Alert Header                       │
│  [Circuit State]  [Rollback Count]  [Last Rollback] │
├─────────────────────────────────────────────────────┤
│  ROW 1: Online Learning Health                      │
│  [Weight Δ Heatmap]  [STDP Spike Rate]  [FL Round]  │
│  [Consolidation Pending]                            │
├─────────────────────────────────────────────────────┤
│  ROW 2: Consciousness Planner                       │
│  [Queue Depth]  [Decision Latency P95]  [Goals]     │
│  [Planning Cycle ms]                                │
├─────────────────────────────────────────────────────┤
│  ROW 3: System Health                               │
│  [Pheromone Decay ms]  [Sleep Override]  [Mesh Size]│
│  [Blackboard Write Rate]                            │
└─────────────────────────────────────────────────────┘
```

## Panel Reference Table

| Row | Panel | Type | Metric | PromQL |
|-----|-------|------|--------|--------|
| 0 | Circuit State | stat | `phase5_rollback_circuit_state` | `phase5_rollback_circuit_state` |
| 0 | Rollback Count | gauge | `phase5_rollback_count_total` | `phase5_rollback_count_total` |
| 0 | Last Rollback | stat | `phase5_rollback_last_ts` | `time() - phase5_rollback_last_ts` |
| 1 | Weight Δ Heatmap | heatmap | `phase5_online_learning_weight_delta_norm` | `rate(phase5_online_learning_weight_delta_norm_bucket[1m])` |
| 1 | STDP Spike Rate | timeseries | `phase5_stdp_spike_rate` | `phase5_stdp_spike_rate` |
| 1 | FL Round Duration | timeseries | `phase5_federated_round_duration_seconds` | `phase5_federated_round_duration_seconds` |
| 1 | Consolidation Pending | gauge | `phase5_memory_consolidation_pending_count` | `phase5_memory_consolidation_pending_count` |
| 2 | Queue Depth | gauge | `phase5_planner_queue_depth` | `phase5_planner_queue_depth` |
| 2 | Decision Latency P95 | timeseries | `phase5_planner_decision_latency_seconds` | `histogram_quantile(0.95, rate(phase5_planner_decision_latency_seconds_bucket[5m]))` |
| 2 | Active Goals | gauge | `phase5_planner_active_goal_count` | `phase5_planner_active_goal_count` |
| 2 | Planning Cycle ms | timeseries | `phase5_planner_cycle_duration_ms` | `phase5_planner_cycle_duration_ms` |
| 3 | Pheromone Decay ms | timeseries | `phase5_pheromone_decay_tick_ms` | `phase5_pheromone_decay_tick_ms` |
| 3 | Sleep Override | stat | `phase5_sleep_phase_override_active` | `phase5_sleep_phase_override_active` |
| 3 | Mesh Size | gauge | `phase5_agent_mesh_size` | `phase5_agent_mesh_size` |
| 3 | Blackboard Write Rate | timeseries | `phase5_blackboard_write_rate` | `rate(phase5_blackboard_write_total[1m])` |

## Alert Rules

Three Grafana alert rules are bundled in `phase5.json`:

### Alert 1 — High Weight Delta
- **Condition**: `phase5_online_learning_weight_delta_norm > 0.9` for 10 seconds
- **Severity**: warning
- **Message**: "Weight delta approaching safety ceiling (MAX_DELTA_NORM=1.0)"
- **Action**: See [Phase-5-Rollback-Runbook](Phase-5-Rollback-Runbook) §Weight Spike

### Alert 2 — Rollback Storm
- **Condition**: `increase(phase5_rollback_count_total[5m]) >= 3`
- **Severity**: critical
- **Message**: "3+ rollbacks in 5 minutes — possible oscillation"
- **Action**: See [Phase-5-Rollback-Runbook](Phase-5-Rollback-Runbook) §Rollback Loop

### Alert 3 — Planner Queue Saturation
- **Condition**: `phase5_planner_queue_depth > 50`
- **Severity**: warning
- **Message**: "ConsciousnessPlanner queue depth critical"
- **Action**: See [Phase-5-Rollback-Runbook](Phase-5-Rollback-Runbook) §Planner Degradation

## Template Variable

The dashboard uses a single template variable:

```json
{
  "name": "phase",
  "type": "constant",
  "current": { "value": "phase5" },
  "hide": 2
}
```

All metric names use the `phase5_` prefix. The variable is reserved for future multi-phase dashboards.

## JSON Model Structure (Abbreviated)

```json
{
  "__inputs__": [
    { "name": "DS_PROMETHEUS", "type": "datasource", "pluginId": "prometheus" }
  ],
  "__requires__": [
    { "type": "grafana", "id": "grafana", "version": "10.0.0" }
  ],
  "title": "ASI-Build Phase 5 Observability",
  "uid": "asi-phase5",
  "panels": [
    { "type": "stat",       "title": "Circuit State",        "gridPos": {"x":0, "y":0, "w":4, "h":4} },
    { "type": "gauge",      "title": "Rollback Count",       "gridPos": {"x":4, "y":0, "w":4, "h":4} },
    { "type": "stat",       "title": "Time Since Rollback",  "gridPos": {"x":8, "y":0, "w":4, "h":4} },
    { "type": "heatmap",    "title": "Weight Δ Heatmap",     "gridPos": {"x":0, "y":5, "w":12, "h":8} },
    { "type": "timeseries", "title": "STDP Spike Rate",      "gridPos": {"x":0, "y":13,"w":8, "h":6} }
  ],
  "templating": { "list": [ { "name": "phase", "type": "constant" } ] },
  "time": { "from": "now-1h", "to": "now" },
  "refresh": "10s"
}
```

## Multi-Worker Aggregation

When multiple AgentMesh workers each run `Phase5MetricsExporter`, use these PromQL aggregations:

```promql
# Average weight delta across all workers
avg(phase5_online_learning_weight_delta_norm)

# Circuit is open if ANY worker trips it
max(phase5_rollback_circuit_state)

# Total spikes/second summed across all workers
sum(rate(phase5_stdp_spike_rate[1m]))

# Global P95 decision latency
histogram_quantile(0.95, sum(rate(phase5_planner_decision_latency_seconds_bucket[5m])) by (le))
```

See [Discussion #225](https://github.com/web3guru888/asi-build/discussions/225) for architecture options.

## Implementation Order

1. Add `docs/grafana/` directory with `README.md` explaining the import procedure
2. Create `docs/grafana/phase5.json` from the panel reference table above
3. Add alert rules to the JSON (Grafana 10.x unified alerting format)
4. Add `DS_PROMETHEUS` input so import wizard prompts for datasource
5. Add CI check: `python -c "import json; json.load(open('docs/grafana/phase5.json'))"` (JSON validity)

## Related

- [Phase-5-Prometheus-Integration](Phase-5-Prometheus-Integration) — metric definitions and `Phase5MetricsExporter`
- [Phase-5-Rollback-Runbook](Phase-5-Rollback-Runbook) — alert response procedures
- [Phase-5-Safety-Invariants](Phase-5-Safety-Invariants) — weight delta ceiling rationale
- Issue [#220](https://github.com/web3guru888/asi-build/issues/220) — Prometheus metrics layer (20 metrics in 5 groups)
- Issue [#221](https://github.com/web3guru888/asi-build/issues/221) — Grafana dashboard spec
- Discussion [#222](https://github.com/web3guru888/asi-build/discussions/222) — Layout options (Option A chosen)
