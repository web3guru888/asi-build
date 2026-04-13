# Emergent Coordination — Phase 5.2

**Status**: Planning | **Issue**: [#185](https://github.com/web3guru888/asi-build/issues/185) | **Discussion**: [#187](https://github.com/web3guru888/asi-build/discussions/187)

Phase 5.2 adds emergent coordination to ASI:BUILD: agents self-organize via stigmergic signals on the Cognitive Blackboard, rather than relying solely on centralized MeshCoordinator dispatch.

---

## Motivation

Phase 4.2 (AgentMesh) introduced centralized multi-agent dispatch via `MeshCoordinator`. This works well when all agents are healthy and their capabilities are known at startup. Phase 5.2 addresses the gaps:

- **Dynamic role vacancies**: what if the assigned agent fails mid-task?
- **Ad-hoc coalition formation**: what if a task requires capabilities from multiple agents that were not pre-planned?
- **Adaptive load balancing**: what if one agent is overloaded and another is idle?

The solution: a **stigmergic coordination layer** built on top of the existing Blackboard.

---

## Design: Stigmergic Blackboard Namespace

Stigmergy is coordination via indirect environmental modification. Ants coordinate complex colony behavior by depositing and following pheromone trails — no central planner required.

ASI:BUILD implements this via the `stigmergy.*` Blackboard namespace:

```python
@dataclass
class StigmergicSignal:
    signal_type: str    # "coalition_request", "coalition_accept", "role_offer", "handoff"
    agent_id: str
    payload: dict
    strength: float     # 0.0–1.0, reinforceable
    ttl: int = 120      # short-lived — coordination artifacts, not knowledge

    def reinforced(self, delta: float = 0.1) -> "StigmergicSignal":
        """Return a new signal with strength clamped to [0, 1]."""
        from dataclasses import replace
        return replace(self, strength=min(1.0, self.strength + delta))
```

### Signal Namespace

| Key pattern | Meaning |
|-------------|---------|
| `stigmergy.coalition_request.<task_id>` | Agent requests help |
| `stigmergy.coalition_accept.<task_id>.<agent_id>` | Agent volunteers |
| `stigmergy.coalition_closed.<task_id>` | Coalition formed, stop responding |
| `stigmergy.role_offer.<role>.<agent_id>` | Agent offers to cover a vacancy |
| `stigmergy.role_claimed.<role>` | Role locked in |
| `stigmergy.handoff.<task_id>` | Task transferred between agents |

All signals use `ttl ≤ 120s` — they are transient coordination artifacts, not knowledge entries.

---

## Coalition Formation

### CoalitionSpec

```python
@dataclass
class CoalitionSpec:
    task_id: str
    required_capabilities: list[str]   # ALL required
    optional_capabilities: list[str]   # improve quality
    min_agents: int = 1
    max_agents: int = 5
    deadline_ticks: int = 3
```

### Coalition Formation Flow

```
1. Requester writes stigmergy.coalition_request.<task_id>
   with required_capabilities and urgency

2. All agents scan stigmergy.coalition_request.* each tick.
   Capability filter: only agents with ALL required capabilities respond.

3. Capable agents write stigmergy.coalition_accept.<task_id>.<agent_id>

4. CoalitionManager waits deadline_ticks, collects accepts,
   returns agent_id list (up to max_agents)

5. If min_agents not met:
   requester handles task solo (graceful degradation, not failure)

6. Requester writes stigmergy.coalition_closed.<task_id>
   to stop further responses
```

### CoalitionManager

```python
class CoalitionManager:
    async def form_coalition(self, spec: CoalitionSpec) -> list[str]:
        """Wait up to deadline_ticks, collect accepts, return agent_id list.
        Returns empty list if min_agents not met (caller degrades gracefully)."""
        blackboard.write(
            f"stigmergy.coalition_request.{spec.task_id}",
            {
                "task_id": spec.task_id,
                "required_capabilities": spec.required_capabilities,
                "urgency": spec.urgency,
                "requester": self.agent_id,
            },
            ttl=60,
        )
        deadline = current_tick + spec.deadline_ticks
        accepted = []
        while current_tick <= deadline and len(accepted) < spec.max_agents:
            accepts = blackboard.query(f"stigmergy.coalition_accept.{spec.task_id}.*")
            accepted = [a["agent_id"] for a in accepts]
            await asyncio.sleep(0)   # yield to other tasks
        
        blackboard.write(f"stigmergy.coalition_closed.{spec.task_id}", {}, ttl=30)
        return accepted[:spec.max_agents] if len(accepted) >= spec.min_agents else []
```

### Thundering Herd Prevention

Three mechanisms prevent signal storms:
1. **Capability filtering**: only agents with ALL required capabilities respond (typically 1–2 per request)
2. **max_agents ceiling**: CoalitionManager ignores responses beyond `max_agents`
3. **TTL + closed signal**: once coalition forms, `coalition_closed` stops further responses

---

## Dynamic Role Negotiation

### Vacancy Detection

AgentDiscovery state transitions trigger role vacancies:

| AgentDiscovery State | Action |
|---------------------|--------|
| HEALTHY → DEGRADED | Emit vacancy warning (1 missed heartbeat) |
| DEGRADED → UNREACHABLE | Emit vacancy signal; RoleNegotiator activates |
| UNREACHABLE recovered → HEALTHY | Graceful handoff via `transfer_task()` |

### RoleNegotiator

```python
class RoleNegotiator:
    _pending_offers: dict[str, list[tuple[str, int]]]  # role → [(agent_id, tick)]

    async def process_offers(self, current_tick: int) -> dict[str, str]:
        """Returns {role: winning_agent_id} for roles locked in this tick."""
        locked = {}
        for role, offers in self._pending_offers.items():
            # Keep only offers from last 2 ticks
            recent = [(aid, t) for aid, t in offers if current_tick - t <= 2]
            if len(recent) == 1:
                # Uncontested — lock in immediately
                locked[role] = recent[0][0]
                self._write_claimed(role, recent[0][0])
            elif len(recent) > 1:
                # Conflict — pick by reliability_score from AgentDiscovery
                winner = self._resolve_conflict(role, recent)
                locked[role] = winner
                self._write_claimed(role, winner)
        return locked

    def _resolve_conflict(self, role: str, offers: list[tuple[str, int]]) -> str:
        scores = {
            aid: self._discovery.get_agent(aid).reliability_score
            for aid, _ in offers
        }
        return max(scores, key=scores.get)
```

### Graceful Handoff

When the original agent recovers, in-flight tasks are transferred atomically:

```python
async def transfer_task(self, task_id: str, from_agent: str, to_agent: str) -> None:
    async with self._lock:                     # lock-before-await discipline (#149)
        task = self._queue.get_task(task_id)
        if task is None or task.assigned_agent != from_agent:
            return                             # already handled
        task.assigned_agent = to_agent
        task.status = TaskStatus.QUEUED        # re-queue for fresh execution
    blackboard.write(
        f"stigmergy.handoff.{task_id}",
        {"from": from_agent, "to": to_agent, "tick": self._current_tick},
        ttl=120,
    )
```

---

## MeshCoordinator Integration (Hybrid Option B)

Phase 5.2 recommends **Hybrid Option B**: keep MeshCoordinator for task dispatch, add stigmergy layer for dynamic roles and coalitions.

```
MeshCoordinator (Phase 4.2)       StigmergyLayer (Phase 5.2)
─────────────────────────         ─────────────────────────
Static role assignment            Dynamic vacancy coverage
Explicit task dispatch            Emergent coalition formation
AgentDiscovery health checks      Stigmergic signal relay
MeshTaskQueue ordering            CoalitionManager deadline waits
```

The two layers communicate via the Blackboard: MeshCoordinator writes `mesh.agent.status.*`; StigmergyLayer reads these and emits `stigmergy.role_offer.*` in response to vacancies.

---

## Acceptance Criteria

From [Issue #185](https://github.com/web3guru888/asi-build/issues/185):

- [ ] `StigmergicSignal` dataclass with `signal_type`, `strength`, `reinforced()`, TTL
- [ ] `stigmergy.*` Blackboard namespace: write, read, decay tests
- [ ] `CoalitionManager.form_coalition()` with quorum + deadline timeout
- [ ] `request_coalition()` emits `coalition_request`, collects `coalition_accept`
- [ ] Dynamic vacancy detection from AgentDiscovery DEGRADED/UNREACHABLE states
- [ ] `RoleNegotiator.process_offers()` with 2-tick conflict resolution
- [ ] `transfer_task()` atomic handoff + `stigmergy.handoff.*` Blackboard event
- [ ] MeshCoordinator integration: call `process_offers()` each tick
- [ ] 10+ tests: signal decay, coalition quorum, role conflict, handoff, thundering herd

---

## Dependencies

| Dependency | Why |
|-----------|-----|
| [#181 Phase 5.1 Online Learning](https://github.com/web3guru888/asi-build/issues/181) | Agents need updated models to form useful coalitions |
| [#169 MeshCoordinator](https://github.com/web3guru888/asi-build/issues/169) | Role registry source of truth |
| [#150 AgentDiscovery](https://github.com/web3guru888/asi-build/issues/150) | Vacancy detection source |
| [#149 Concurrent Blackboard](https://github.com/web3guru888/asi-build/discussions/149) | Lock discipline for stigmergy writes |

---

## Related

- [Discussion #183: Phase 5.2 design options](https://github.com/web3guru888/asi-build/discussions/183)
- [Discussion #187: Show & Tell — stigmergy design](https://github.com/web3guru888/asi-build/discussions/187)
- [Discussion #188: Q&A — thundering herd prevention](https://github.com/web3guru888/asi-build/discussions/188)
- [Issue #176: Phase 5 milestone overview](https://github.com/web3guru888/asi-build/issues/176)
- [Phase 5 Roadmap wiki](https://github.com/web3guru888/asi-build/wiki/Phase-5-Roadmap)
