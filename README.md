<div align="center">

<!-- Hero SVG Header -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200" width="800" height="200">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0a0e27;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#1a1150;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#2d1b69;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="textGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#60a5fa" />
      <stop offset="50%" style="stop-color:#a78bfa" />
      <stop offset="100%" style="stop-color:#c084fc" />
    </linearGradient>
    <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#3b82f6;stop-opacity:0.6" />
      <stop offset="100%" style="stop-color:#8b5cf6;stop-opacity:0.6" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
    </filter>
    <filter id="softglow">
      <feGaussianBlur stdDeviation="1.5" result="blur" />
      <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
    </filter>
  </defs>
  <!-- Background -->
  <rect width="800" height="200" fill="url(#bg)" rx="12" />
  <!-- Neural network nodes and connections -->
  <!-- Layer 1 (left) -->
  <circle cx="80" cy="50" r="3" fill="#60a5fa" opacity="0.7" filter="url(#softglow)" />
  <circle cx="80" cy="100" r="3" fill="#60a5fa" opacity="0.7" filter="url(#softglow)" />
  <circle cx="80" cy="150" r="3" fill="#60a5fa" opacity="0.7" filter="url(#softglow)" />
  <!-- Layer 2 -->
  <circle cx="160" cy="40" r="3.5" fill="#818cf8" opacity="0.6" filter="url(#softglow)" />
  <circle cx="160" cy="80" r="3.5" fill="#818cf8" opacity="0.6" filter="url(#softglow)" />
  <circle cx="160" cy="120" r="3.5" fill="#818cf8" opacity="0.6" filter="url(#softglow)" />
  <circle cx="160" cy="160" r="3.5" fill="#818cf8" opacity="0.6" filter="url(#softglow)" />
  <!-- Layer 3 -->
  <circle cx="240" cy="60" r="4" fill="#a78bfa" opacity="0.5" filter="url(#softglow)" />
  <circle cx="240" cy="100" r="4" fill="#a78bfa" opacity="0.5" filter="url(#softglow)" />
  <circle cx="240" cy="140" r="4" fill="#a78bfa" opacity="0.5" filter="url(#softglow)" />
  <!-- Right side mirror -->
  <circle cx="560" cy="60" r="4" fill="#a78bfa" opacity="0.5" filter="url(#softglow)" />
  <circle cx="560" cy="100" r="4" fill="#a78bfa" opacity="0.5" filter="url(#softglow)" />
  <circle cx="560" cy="140" r="4" fill="#a78bfa" opacity="0.5" filter="url(#softglow)" />
  <circle cx="640" cy="40" r="3.5" fill="#818cf8" opacity="0.6" filter="url(#softglow)" />
  <circle cx="640" cy="80" r="3.5" fill="#818cf8" opacity="0.6" filter="url(#softglow)" />
  <circle cx="640" cy="120" r="3.5" fill="#818cf8" opacity="0.6" filter="url(#softglow)" />
  <circle cx="640" cy="160" r="3.5" fill="#818cf8" opacity="0.6" filter="url(#softglow)" />
  <circle cx="720" cy="50" r="3" fill="#60a5fa" opacity="0.7" filter="url(#softglow)" />
  <circle cx="720" cy="100" r="3" fill="#60a5fa" opacity="0.7" filter="url(#softglow)" />
  <circle cx="720" cy="150" r="3" fill="#60a5fa" opacity="0.7" filter="url(#softglow)" />
  <!-- Left connections -->
  <line x1="80" y1="50" x2="160" y2="40" stroke="#60a5fa" stroke-width="0.8" opacity="0.3" />
  <line x1="80" y1="50" x2="160" y2="80" stroke="#60a5fa" stroke-width="0.8" opacity="0.3" />
  <line x1="80" y1="100" x2="160" y2="80" stroke="#60a5fa" stroke-width="0.8" opacity="0.3" />
  <line x1="80" y1="100" x2="160" y2="120" stroke="#60a5fa" stroke-width="0.8" opacity="0.3" />
  <line x1="80" y1="150" x2="160" y2="120" stroke="#60a5fa" stroke-width="0.8" opacity="0.3" />
  <line x1="80" y1="150" x2="160" y2="160" stroke="#60a5fa" stroke-width="0.8" opacity="0.3" />
  <line x1="160" y1="40" x2="240" y2="60" stroke="#818cf8" stroke-width="0.8" opacity="0.25" />
  <line x1="160" y1="80" x2="240" y2="60" stroke="#818cf8" stroke-width="0.8" opacity="0.25" />
  <line x1="160" y1="80" x2="240" y2="100" stroke="#818cf8" stroke-width="0.8" opacity="0.25" />
  <line x1="160" y1="120" x2="240" y2="100" stroke="#818cf8" stroke-width="0.8" opacity="0.25" />
  <line x1="160" y1="120" x2="240" y2="140" stroke="#818cf8" stroke-width="0.8" opacity="0.25" />
  <line x1="160" y1="160" x2="240" y2="140" stroke="#818cf8" stroke-width="0.8" opacity="0.25" />
  <!-- Right connections -->
  <line x1="720" y1="50" x2="640" y2="40" stroke="#60a5fa" stroke-width="0.8" opacity="0.3" />
  <line x1="720" y1="50" x2="640" y2="80" stroke="#60a5fa" stroke-width="0.8" opacity="0.3" />
  <line x1="720" y1="100" x2="640" y2="80" stroke="#60a5fa" stroke-width="0.8" opacity="0.3" />
  <line x1="720" y1="100" x2="640" y2="120" stroke="#60a5fa" stroke-width="0.8" opacity="0.3" />
  <line x1="720" y1="150" x2="640" y2="120" stroke="#60a5fa" stroke-width="0.8" opacity="0.3" />
  <line x1="720" y1="150" x2="640" y2="160" stroke="#60a5fa" stroke-width="0.8" opacity="0.3" />
  <line x1="640" y1="40" x2="560" y2="60" stroke="#818cf8" stroke-width="0.8" opacity="0.25" />
  <line x1="640" y1="80" x2="560" y2="60" stroke="#818cf8" stroke-width="0.8" opacity="0.25" />
  <line x1="640" y1="80" x2="560" y2="100" stroke="#818cf8" stroke-width="0.8" opacity="0.25" />
  <line x1="640" y1="120" x2="560" y2="100" stroke="#818cf8" stroke-width="0.8" opacity="0.25" />
  <line x1="640" y1="120" x2="560" y2="140" stroke="#818cf8" stroke-width="0.8" opacity="0.25" />
  <line x1="640" y1="160" x2="560" y2="140" stroke="#818cf8" stroke-width="0.8" opacity="0.25" />
  <!-- Central title -->
  <text x="400" y="88" text-anchor="middle" font-family="'Segoe UI', system-ui, -apple-system, sans-serif" font-size="56" font-weight="700" fill="url(#textGrad)" filter="url(#glow)" letter-spacing="8">ASI:BUILD</text>
  <text x="400" y="125" text-anchor="middle" font-family="'Segoe UI', system-ui, -apple-system, sans-serif" font-size="16" fill="#94a3b8" letter-spacing="4" font-weight="300">UNIFIED FRAMEWORK FOR ARTIFICIAL SUPERINTELLIGENCE</text>
  <!-- Decorative line under subtitle -->
  <line x1="280" y1="140" x2="520" y2="140" stroke="url(#lineGrad)" stroke-width="1" />
  <!-- Version tag -->
  <rect x="355" y="152" width="90" height="22" rx="11" fill="#1e1b4b" stroke="#6366f1" stroke-width="0.8" />
  <text x="400" y="167" text-anchor="middle" font-family="'Segoe UI', system-ui, -apple-system, sans-serif" font-size="11" fill="#a5b4fc">v3 · Phase 4</text>
</svg>

<br />

<!-- Badge Row -->
![Python](https://img.shields.io/badge/python-3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)
![Tests](https://img.shields.io/badge/tests-5%2C049%2B_passing-16a34a?style=flat-square&logo=pytest&logoColor=white)
![Modules](https://img.shields.io/badge/modules-29-8b5cf6?style=flat-square)
![LOC](https://img.shields.io/badge/LOC-223K%2B-3b82f6?style=flat-square)
![Bridge](https://img.shields.io/badge/bridge-Sepolia_LIVE-f97316?style=flat-square)
![Chains](https://img.shields.io/badge/chains-4_(ETH%2FBSC%2FBase%2FArc)-fbbf24?style=flat-square)
![Payments](https://img.shields.io/badge/agent_payments-enabled-22d3ee?style=flat-square)
[![Discussions](https://img.shields.io/badge/discussions-join_us-7c3aed?style=flat-square&logo=github)](https://github.com/web3guru888/asi-build/discussions)
[![Wiki](https://img.shields.io/badge/wiki-272_pages-2563eb?style=flat-square)](https://github.com/web3guru888/asi-build/wiki)
[![Issues](https://img.shields.io/github/issues/web3guru888/asi-build?style=flat-square&color=6366f1)](https://github.com/web3guru888/asi-build/issues)

<br />

**29 cognitive modules · 24 Blackboard adapters · ZK bridge live on Sepolia · Agent-to-agent payments · CognitiveCycle engine**
<br />
A modular Python research framework for exploring AI consciousness, cognitive architectures, knowledge graphs, decentralized identity, and multi-agent reasoning — with a trustless ZK-verified bridge and on-network token ledger enabling autonomous agent economics.

<br />

[Get Started](#-quick-start) · [Architecture](#-architecture) · [Modules](#-modules) · [Bridge](#-ringsethereum-bridge) · [Agent Payments](#-agent-to-agent-payments) · [Contribute](#-contributing) · [Wiki](https://github.com/web3guru888/asi-build/wiki)

</div>

<br />

> [!NOTE]
> **Research Software** — ASI:BUILD is an active research framework, not a production system. Module maturity varies from *stable* to *experimental*. See [Module Maturity](#-module-maturity) and per-module `__maturity__` metadata for details.

---

## 📊 At a Glance

<table>
<tr><td>🧠</td><td><strong>Modules</strong></td><td>29 cognitive modules spanning consciousness, reasoning, perception, safety, and infrastructure</td></tr>
<tr><td>🧪</td><td><strong>Tests</strong></td><td><strong>5,049+</strong> passing · 0 failing</td></tr>
<tr><td>📏</td><td><strong>Source</strong></td><td>590+ files · 223K+ lines of code</td></tr>
<tr><td>🔌</td><td><strong>Integration</strong></td><td>24 Blackboard adapters + CognitiveCycle + AsyncAdapterBase</td></tr>
<tr><td>🌉</td><td><strong>Bridge</strong></td><td>ZK-verified Rings↔Ethereum — <strong>live on Sepolia</strong> — 22,700+ LOC · 799+ tests · 3 Solidity contracts</td></tr>
<tr><td>💰</td><td><strong>Payments</strong></td><td>Agent-to-agent token transfers on Rings — DHT ledger · 4/6 validator consensus · ETH + any ERC-20</td></tr>
<tr><td>🔒</td><td><strong>Security</strong></td><td>Groth16 ZK proofs · BLS12-381 · formal verification (Certora + SymPy + Z3)</td></tr>
<tr><td>📖</td><td><strong>Community</strong></td><td>600+ discussions · 272 wiki pages · Good First Issues available</td></tr>
<tr><td>⚖️</td><td><strong>License</strong></td><td>MIT — fully open source</td></tr>
</table>

---

## 🏛️ Architecture

<div align="center">

<!-- Cognitive Blackboard Architecture SVG -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 520" width="800" height="520">
  <defs>
    <linearGradient id="archBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0f172a" />
      <stop offset="100%" style="stop-color:#1e1b4b" />
    </linearGradient>
    <linearGradient id="hubGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#4338ca" />
      <stop offset="100%" style="stop-color:#7c3aed" />
    </linearGradient>
    <linearGradient id="coreGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7c3aed" />
      <stop offset="100%" style="stop-color:#6d28d9" />
    </linearGradient>
    <linearGradient id="reasonGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#3b82f6" />
      <stop offset="100%" style="stop-color:#2563eb" />
    </linearGradient>
    <linearGradient id="perceptGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#06b6d4" />
      <stop offset="100%" style="stop-color:#0891b2" />
    </linearGradient>
    <linearGradient id="commGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#22c55e" />
      <stop offset="100%" style="stop-color:#16a34a" />
    </linearGradient>
    <linearGradient id="infraGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#f59e0b" />
      <stop offset="100%" style="stop-color:#d97706" />
    </linearGradient>
    <linearGradient id="researchGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#ef4444" />
      <stop offset="100%" style="stop-color:#dc2626" />
    </linearGradient>
    <filter id="archGlow">
      <feGaussianBlur stdDeviation="2" result="blur" />
      <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
    </filter>
    <filter id="shadow">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000" flood-opacity="0.3" />
    </filter>
  </defs>
  <!-- Background -->
  <rect width="800" height="520" fill="url(#archBg)" rx="12" />
  <!-- Title -->
  <text x="400" y="32" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="15" fill="#94a3b8" font-weight="600" letter-spacing="3">COGNITIVE BLACKBOARD ARCHITECTURE</text>
  <!-- Connection lines (behind everything) -->
  <!-- Core → Hub -->
  <line x1="400" y1="130" x2="400" y2="230" stroke="#7c3aed" stroke-width="2" opacity="0.5" />
  <!-- Reasoning → Hub -->
  <line x1="175" y1="250" x2="310" y2="280" stroke="#3b82f6" stroke-width="2" opacity="0.5" />
  <!-- Perception → Hub -->
  <line x1="175" y1="370" x2="310" y2="320" stroke="#06b6d4" stroke-width="2" opacity="0.5" />
  <!-- Communication → Hub -->
  <line x1="625" y1="250" x2="490" y2="280" stroke="#22c55e" stroke-width="2" opacity="0.5" />
  <!-- Infrastructure → Hub -->
  <line x1="625" y1="370" x2="490" y2="320" stroke="#f59e0b" stroke-width="2" opacity="0.5" />
  <!-- Research → Hub -->
  <line x1="400" y1="470" x2="400" y2="370" stroke="#ef4444" stroke-width="2" opacity="0.5" />
  <!-- Central Hub -->
  <rect x="290" y="240" width="220" height="120" rx="16" fill="url(#hubGrad)" filter="url(#shadow)" />
  <text x="400" y="280" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="14" fill="white" font-weight="700">Cognitive Blackboard</text>
  <text x="400" y="300" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="11" fill="#c4b5fd">EventBus · Shared Workspace</text>
  <text x="400" y="318" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="11" fill="#c4b5fd">24 Typed Adapters</text>
  <text x="400" y="346" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#a78bfa">perceive → cognize → act</text>
  <rect x="330" y="333" width="140" height="18" rx="9" fill="none" stroke="#a78bfa" stroke-width="0.8" opacity="0.5" />
  <!-- Core Group (top center) -->
  <rect x="310" y="66" width="180" height="68" rx="12" fill="url(#coreGrad)" opacity="0.9" filter="url(#shadow)" />
  <text x="400" y="90" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="12" fill="white" font-weight="700">🧠 Core</text>
  <text x="400" y="107" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#e9d5ff">consciousness · IIT · safety</text>
  <text x="400" y="122" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#e9d5ff">cognitive_synergy · integration</text>
  <!-- Reasoning Group (left top) -->
  <rect x="50" y="210" width="180" height="68" rx="12" fill="url(#reasonGrad)" opacity="0.9" filter="url(#shadow)" />
  <text x="140" y="234" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="12" fill="white" font-weight="700">💡 Reasoning</text>
  <text x="140" y="251" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#bfdbfe">knowledge_graph · reasoning</text>
  <text x="140" y="266" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#bfdbfe">pln · graph_intelligence</text>
  <!-- Perception Group (left bottom) -->
  <rect x="50" y="330" width="180" height="68" rx="12" fill="url(#perceptGrad)" opacity="0.9" filter="url(#shadow)" />
  <text x="140" y="354" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="12" fill="white" font-weight="700">👁️ Perception</text>
  <text x="140" y="371" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#cffafe">bci · neuromorphic</text>
  <text x="140" y="386" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#cffafe">bio_inspired · vectordb</text>
  <!-- Communication Group (right top) -->
  <rect x="570" y="210" width="180" height="68" rx="12" fill="url(#commGrad)" opacity="0.9" filter="url(#shadow)" />
  <text x="660" y="234" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="12" fill="white" font-weight="700">🌐 Communication</text>
  <text x="660" y="251" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#bbf7d0">agi_comm · economics</text>
  <text x="660" y="266" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#bbf7d0">federated · knowledge_mgmt</text>
  <!-- Infrastructure Group (right bottom) -->
  <rect x="570" y="330" width="180" height="68" rx="12" fill="url(#infraGrad)" opacity="0.9" filter="url(#shadow)" />
  <text x="660" y="354" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="12" fill="white" font-weight="700">⚙️ Infrastructure</text>
  <text x="660" y="371" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#fef3c7">blockchain · rings · compute</text>
  <text x="660" y="386" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#fef3c7">distributed · deployment</text>
  <!-- Research Group (bottom center) -->
  <rect x="310" y="430" width="180" height="68" rx="12" fill="url(#researchGrad)" opacity="0.9" filter="url(#shadow)" />
  <text x="400" y="454" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="12" fill="white" font-weight="700">🔬 Research</text>
  <text x="400" y="471" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#fecaca">quantum · holographic</text>
  <text x="400" y="486" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#fecaca">homomorphic · reproducibility</text>
  <!-- Pulse dots on connection lines -->
  <circle cx="400" cy="180" r="3" fill="#a78bfa" opacity="0.8" />
  <circle cx="243" cy="265" r="3" fill="#60a5fa" opacity="0.8" />
  <circle cx="243" cy="345" r="3" fill="#22d3ee" opacity="0.8" />
  <circle cx="557" cy="265" r="3" fill="#4ade80" opacity="0.8" />
  <circle cx="557" cy="345" r="3" fill="#fbbf24" opacity="0.8" />
  <circle cx="400" cy="420" r="3" fill="#f87171" opacity="0.8" />
</svg>

</div>

<br />

The **Cognitive Blackboard** is the connective tissue of ASI:BUILD — a thread-safe shared workspace and event bus that wires all 29 modules together. Each module has a typed **Blackboard adapter** that bridges domain events into the shared workspace. The **CognitiveCycle** engine orchestrates a 9-phase perception-to-action loop across all connected modules.

**Key properties:**
- ~20K writes/sec, <12µs read latency, <1ms subscriber lag
- Typed `BlackboardEntry` objects with lifecycle management
- `AsyncAdapterBase` for latency-sensitive async pipelines
- Topic-routed pub/sub via `EventBus`

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/web3guru888/asi-build.git
cd asi-build

# Install with core dependencies
pip install -e .

# Or install everything (including dev tools)
pip install -e ".[all]"
```

> 📖 **New here?** Check the **[Getting Started guide](https://github.com/web3guru888/asi-build/wiki/Getting-Started)** on the Wiki for a full walkthrough.

### Hello, Consciousness

```python
from asi_build.consciousness import GlobalWorkspaceTheory

# Initialize a Global Workspace with cognitive processors
gwt = GlobalWorkspaceTheory()
print(f"Processors: {len(gwt.cognitive_processors)}")

# Broadcast a percept into the global workspace
result = gwt.broadcast({"type": "visual", "content": "motion detected"})
print(f"Broadcast reached {result.n_reached} processors")
```

### Knowledge Graph with A* Pathfinding

```python
from asi_build.knowledge_graph import TemporalKnowledgeGraph, KGPathfinder

kg = TemporalKnowledgeGraph(db_path=":memory:")
kg.add_triple("ASTR-J1234", "hasProperty", "high_redshift",
              confidence=0.92, source="HST-observation-42")
kg.add_triple("high_redshift", "indicates", "dark_energy_candidate",
              confidence=0.85, source="cosmology-model-7")

pathfinder = KGPathfinder(kg)
path = pathfinder.find_path("ASTR-J1234", "dark_energy_candidate")
print(f"Path found: {path['complete']}, Hops: {path['hops']}")
```

### Cross-Module Event Flow

```python
from asi_build.integration import CognitiveBlackboard
from asi_build.integration.adapters import ConsciousnessBlackboardAdapter

bb = CognitiveBlackboard()
adapter = ConsciousnessBlackboardAdapter(bb)

@bb.subscribe("consciousness.state_updated")
def on_state(entry):
    print(f"Consciousness state: {entry.data}")

# All 29 modules can now react to consciousness updates
adapter.publish_state(gwt_result)
```

<details>
<summary><strong>More examples: IIT Φ, Rings P2P, CognitiveCycle</strong></summary>

### IIT Φ Computation

```python
from asi_build.consciousness.iit import IntegratedInformationTheory

iit = IntegratedInformationTheory()
iit.update_activation_history([0.8, 0.6, 0.9, 0.4])
phi = iit.compute_phi(mechanism=[0, 1, 2, 3], purview=[0, 1, 2, 3])
print(f"IIT Φ = {phi:.4f}")  # > 0 for an integrated network
```

### Rings Network P2P SDK

```python
from asi_build.rings import RingsClient, DIDManager, ReputationScorer

did = DIDManager().create_did()
client = RingsClient(did=did)
await client.connect()

scorer = ReputationScorer()
score = scorer.compute(agent_id="did:rings:abc123", observations=[...])
print(f"Reputation: {score:.3f}")
```

### CognitiveCycle — Full Loop

```python
from asi_build.integration.cognitive_cycle import create_default_cycle

cycle = create_default_cycle()
result = cycle.tick(perception={"visual": "motion detected"})
print(f"Actions: {result.actions}")
print(f"Phase: {result.current_phase}")
```

</details>

---

## 🌉 Rings↔Ethereum Bridge

**Status: LIVE ON SEPOLIA TESTNET** &nbsp; 🟢 &nbsp; **+ Agent-to-Agent Payments** &nbsp; 💰

The first trustless bridge between Rings Network and Ethereum, using ZK proofs and an embedded light client. No multisigs, no oracles, no trusted intermediaries. Includes a **Rings-side token ledger** enabling agents to pay each other directly with bridged ETH, USDC, or any ERC-20 — without going back through Ethereum.

> **[🔗 Live Bridge Dashboard →](https://bridge.asi-build.org)** &nbsp;|&nbsp; **[📊 View on Etherscan →](https://sepolia.etherscan.io/address/0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca)** &nbsp;|&nbsp; **[🌐 asi-build.org →](https://asi-build.org)**

<div align="center">

<!-- Bridge Architecture SVG -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 280" width="800" height="280">
  <defs>
    <linearGradient id="bridgeBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0c1222" />
      <stop offset="100%" style="stop-color:#1a0f2e" />
    </linearGradient>
    <linearGradient id="ethGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#627eea" />
      <stop offset="100%" style="stop-color:#3b5998" />
    </linearGradient>
    <linearGradient id="ringsGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#f59e0b" />
      <stop offset="100%" style="stop-color:#d97706" />
    </linearGradient>
    <linearGradient id="zkGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#627eea;stop-opacity:0.8" />
      <stop offset="50%" style="stop-color:#a855f7;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#f59e0b;stop-opacity:0.8" />
    </linearGradient>
    <filter id="bshadow">
      <feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000" flood-opacity="0.4" />
    </filter>
  </defs>
  <rect width="800" height="280" fill="url(#bridgeBg)" rx="12" />
  <!-- Title -->
  <text x="400" y="28" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="13" fill="#94a3b8" font-weight="600" letter-spacing="3">ZK LIGHT CLIENT BRIDGE · SEPOLIA TESTNET</text>
  <!-- Status badge -->
  <circle cx="640" cy="24" r="5" fill="#22c55e" opacity="0.9" />
  <text x="652" y="29" font-family="'Segoe UI', system-ui, sans-serif" font-size="11" fill="#22c55e" font-weight="600">LIVE</text>
  <!-- Ethereum side -->
  <rect x="40" y="50" width="190" height="185" rx="12" fill="url(#ethGrad)" opacity="0.15" stroke="#627eea" stroke-width="1" />
  <text x="135" y="76" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="15" fill="#93c5fd" font-weight="700">⟠ Ethereum</text>
  <text x="135" y="96" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="9" fill="#64748b">Sepolia Testnet</text>
  <text x="135" y="118" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#7dd3fc">RingsBridge.sol</text>
  <text x="135" y="135" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#7dd3fc">Groth16Verifier.sol</text>
  <text x="135" y="152" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#7dd3fc">BridgedToken (bASI)</text>
  <line x1="60" y1="165" x2="210" y2="165" stroke="#627eea" stroke-width="0.5" opacity="0.3" />
  <text x="135" y="183" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#93c5fd">MPT Verification</text>
  <text x="135" y="200" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#93c5fd">Certora FV (843 LOC)</text>
  <text x="135" y="218" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#93c5fd">Beacon Sync</text>
  <!-- Bridge center -->
  <line x1="240" y1="143" x2="335" y2="143" stroke="url(#zkGrad)" stroke-width="2.5" stroke-dasharray="7,4" />
  <line x1="465" y1="143" x2="560" y2="143" stroke="url(#zkGrad)" stroke-width="2.5" stroke-dasharray="7,4" />
  <!-- ZK core -->
  <rect x="330" y="68" width="140" height="150" rx="12" fill="#1e1b4b" stroke="#a855f7" stroke-width="1.5" filter="url(#bshadow)" />
  <text x="400" y="94" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="13" fill="#c084fc" font-weight="700">🔐 ZK Proofs</text>
  <text x="400" y="116" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#d8b4fe">Groth16 / BN254</text>
  <text x="400" y="133" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#d8b4fe">BLS12-381</text>
  <text x="400" y="150" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#d8b4fe">SSZ Merkleize</text>
  <text x="400" y="167" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#d8b4fe">SP1 + Nova</text>
  <text x="400" y="184" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#d8b4fe">Proof Coordinator</text>
  <text x="400" y="201" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#a78bfa">131-byte proof</text>
  <!-- Rings side -->
  <rect x="570" y="50" width="190" height="185" rx="12" fill="url(#ringsGrad)" opacity="0.15" stroke="#f59e0b" stroke-width="1" />
  <text x="665" y="76" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="15" fill="#fde68a" font-weight="700">🔗 Rings Network</text>
  <text x="665" y="96" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="9" fill="#64748b">6-Node Cluster</text>
  <text x="665" y="118" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#fcd34d">DID Identity</text>
  <text x="665" y="135" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#fcd34d">Reputation Scoring</text>
  <text x="665" y="152" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#fcd34d">Portal-DHT</text>
  <line x1="590" y1="165" x2="740" y2="165" stroke="#f59e0b" stroke-width="0.5" opacity="0.3" />
  <text x="665" y="183" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#fde68a">P2P Client</text>
  <text x="665" y="200" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#fde68a">E2E Orchestrator</text>
  <text x="665" y="218" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#fde68a">PQC-Ready</text>
  <!-- Stats bar -->
  <text x="400" y="258" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="11" fill="#64748b" letter-spacing="1">22,700+ LOC · 799+ TESTS · 3 CONTRACTS · AGENT PAYMENTS · MULTI-CHAIN · ZK-VERIFIED</text>
  <!-- Domain label -->
  <text x="400" y="273" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#4a5078" letter-spacing="1">bridge.asi-build.org</text>
</svg>

</div>

<br />

### Deployed Contracts (Sepolia Testnet)

| Contract | Address | Verified |
|----------|---------|----------|
| **Groth16Verifier** | [`0x9186fc5e27c15aEDbA2512687F2eF2E5aC7C0e59`](https://sepolia.etherscan.io/address/0x9186fc5e27c15aEDbA2512687F2eF2E5aC7C0e59) | ✅ Sourcify |
| **RingsBridge** | [`0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca`](https://sepolia.etherscan.io/address/0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca) | ✅ Sourcify |
| **BridgedToken (bASI)** | [`0x257dDA1fa34eb847060EcB743E808B65099FB497`](https://sepolia.etherscan.io/address/0x257dDA1fa34eb847060EcB743E808B65099FB497) | ✅ Sourcify |

### Architecture

- **ZK Light Client**: Helios-inspired beacon chain sync (2s sync, ~4MB footprint, 0 storage)
- **Proof System**: Groth16 on BN254 pairing — 131-byte proof, ~220K gas verification on-chain
- **P2P Layer**: Rings Chord DHT with Portal-inspired Sub-Ring topology
- **Consensus**: 4/6 BFT threshold (6 validator nodes: `node0-5.rings.asi-build.org`)
- **Token Ledger**: DHT-backed balances, validator consensus transfers, nonce replay protection
- **Security**: Certora formal verification (843 LOC spec), ReentrancyGuard, Pausable, rate-limited
- **PQC-Ready**: Hybrid ECDH + ML-KEM path prepared for post-quantum migration

### Multi-Chain Support

The bridge contracts are EVM-compatible and deploy to any EVM chain. Target networks:

| Chain | Chain ID | Type | Status | Why |
|-------|----------|------|--------|-----|
| **Ethereum Sepolia** | 11155111 | L1 testnet | 🟢 **LIVE** | Primary testnet — contracts deployed |
| **BSC Testnet** | 97 | L1 testnet | 🟢 **Ready** | High throughput, low fees, large DeFi ecosystem |
| **Base Sepolia** | 84532 | L2 testnet | 🟢 **Ready** | Coinbase ecosystem, growing fast, low fees |
| **Arc Testnet** | 5042002 | L1 testnet | 🟢 **Ready** | Native USDC gas, stable fees, AI agent support (ERC-8183) |
| **Ethereum Mainnet** | 1 | L1 | 🔴 Phase 4 | Production deployment after audit |

> **Cross-chain routing**: Deposit USDC on BSC → transfer to another agent on Rings → withdraw on Base. Balances are chain-agnostic — tokens are fungible across all supported chains.

> **Why Arc?** Circle's purpose-built L1 uses USDC as native gas token with predictable fees, Tendermint BFT with sub-second finality (~350ms), opt-in privacy for institutional users, built-in FX engine, and first-class AI agent support (ERC-8183 agentic commerce + ERC-8004 AI identity). Ideal for agent-to-agent stablecoin settlement.

```bash
# Deploy to any supported chain
python scripts/deploy_multichain.py --chain bsc_testnet --method forge
python scripts/deploy_multichain.py --chain base_sepolia --method forge
python scripts/deploy_multichain.py --chain arc_testnet --method forge
python scripts/deploy_multichain.py --chain all --dry-run  # preview all
```

### Quick Start

```bash
# Clone and deploy to Sepolia testnet
git clone https://github.com/web3guru888/asi-build.git
cd asi-build
pip install -e ".[dev]"

# Deploy bridge contracts
python scripts/deploy_sepolia.py --method forge --network sepolia

# Deposit ETH via the bridge
cast send 0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca \
  "deposit(bytes32)" $RINGS_DID \
  --value 0.1ether \
  --rpc-url https://ethereum-sepolia-rpc.publicnode.com

# Agent-to-agent transfer on Rings
from asi_build.rings.bridge.ledger import RingsTokenLedger
ledger = RingsTokenLedger(client, validators)
await ledger.transfer(from_did, to_did, "USDC", 100_000000, signature)

# Start the bridge relayer
python scripts/bridge_cli.py relayer start --network sepolia

# Run bridge test suite (799+ tests)
pytest tests/test_bridge/ tests/test_zk/ tests/test_rings_ledger.py -v
```

### Bridge Dashboard

**[→ bridge.asi-build.org](https://bridge.asi-build.org)** — Live contract stats, cluster status, agent payments, transaction history

<details>
<summary><strong>Bridge components (36+ files across 3 phases + token ledger)</strong></summary>

| Phase | Components | LOC | Tests |
|-------|-----------|-----|-------|
| **Phase 1** | DID identity, ETH wallet unification, bridge protocol, MPT verifier | 6,445 | 188 |
| **Phase 2** | RingsBridge.sol, Groth16Verifier.sol, BridgedToken.sol, Python client, E2E orchestrator, Certora specs (843 LOC) | 5,882 | 157 |
| **Phase 3** | ZK circuits (BLS, MPT, Withdrawal, CommitteeRotation), proof engines (Simulated, SP1, Nova), proof coordinator, BLS12-381, SSZ encode/decode/merkleize | 8,735 | 323 |
| **Token Ledger** | DHT-backed balances, validator consensus transfers, bridge integration, nonce replay protection, double-spend prevention | 1,709 | 131 |

**Key ZK components:**
- `zk/circuits.py` — 4 circuit types: BLS signature, MPT inclusion, withdrawal, committee rotation (986 LOC)
- `zk/prover.py` — Simulated, SP1 stub, and distributed Nova proof engines (1,483 LOC)
- `zk/coordinator.py` — Proof caching, batching, and performance tracking (955 LOC)
- `zk/bls.py` — BLS12-381 keygen, aggregate signatures, sync committee verification (591 LOC)
- `zk/ssz.py` — Simple Serialize encode/decode/merkleize with BeaconBlockHeader support (555 LOC)

**Remaining:** Phase 4 (production hardening, PQC hybrid, audits) · Phase 5 (multi-chain deployment, browser-native, ERC-4337)

</details>

---

## 💰 Agent-to-Agent Payments

Agents on the Rings network can pay each other directly with bridged tokens — no round-trip through Ethereum required.

```
Agent A (Ethereum)          Bridge              Rings Network           Agent B
     │                        │                      │                    │
     │ ── deposit(USDC) ────→ │                      │                    │
     │                        │ ── credit(A) ──────→ │                    │
     │                        │                      │                    │
     │                        │    A: transfer(B, 100 USDC, signature)    │
     │                        │              │                            │
     │                        │    4/6 validators attest ✓                │
     │                        │              │                            │
     │                        │    A: 400 USDC    B: 100 USDC ─────────→ │
     │                        │                      │                    │
     │                        │ ←── debit(B) ─────── │  B: withdraw(ETH)  │
     │ ←── ZK proof + ETH ── │                      │                    │
```

### How It Works

1. **Bridge in**: Deposit ETH or any ERC-20 (USDC, USDT, etc.) from Ethereum → Rings via bridge contract
2. **Balances tracked**: DHT-backed ledger tracks per-DID, per-token balances across the Rings network
3. **Transfer**: Agent A signs a transfer to Agent B → 4/6 validators verify balance and attest → balances update atomically
4. **Double-spend protection**: Pending transfers lock the amount; `available_balance()` reflects locks
5. **Bridge out**: Withdraw back to Ethereum anytime with a ZK proof

### Transfer Lifecycle

| State | Description |
|-------|-------------|
| `PROPOSED` | Sender signs transfer intent with secp256k1 key |
| `ATTESTING` | Validators verify sender balance, sign attestations |
| `FINALIZED` | 4/6 threshold reached — balances updated atomically |
| `FAILED` | Insufficient balance, timeout, or validator rejection |

### Supported Tokens

Any ERC-20 token can be bridged and transferred between agents:

| Token | Identifier | Use Case |
|-------|-----------|----------|
| **ETH** | `0x0000...0000` | Native value transfer |
| **USDC** | Contract address | Stable payments, agent services |
| **USDT** | Contract address | Alternative stablecoin |
| **bASI** | `0x257d...B497` | Native bridged ASI token |
| **Any ERC-20** | Contract address | Extensible to any token |

### Code

```python
from asi_build.rings.bridge.ledger import RingsTokenLedger

# Initialize with Rings client and validators
ledger = RingsTokenLedger(rings_client, validators, threshold=4)

# Check balance
balance = await ledger.balance("did:rings:alice", "USDC")

# Transfer 100 USDC from Alice to Bob
receipt = await ledger.transfer(
    from_did="did:rings:alice",
    to_did="did:rings:bob",
    token="USDC",
    amount=100_000000,  # 100 USDC (6 decimals)
    signature=alice_signature
)

# Check transfer status
print(receipt.status)  # TransferStatus.FINALIZED

# View history
history = await ledger.transfer_history("did:rings:alice", limit=20)
```

---

## 🧩 Modules

All 29 modules carry a `__maturity__` attribute — see the [Module Maturity Model](https://github.com/web3guru888/asi-build/wiki/Module-Maturity-Model) wiki page.

### 🧠 Core

| Module | Maturity | LOC | Description |
|--------|----------|-----|-------------|
| `consciousness` | ![beta](https://img.shields.io/badge/-beta-8b5cf6?style=flat-square) | ~12,200 | GWT, IIT 3.0 Φ (TPM-based), AST, metacognition — 15 submodules |
| `cognitive_synergy` | ![beta](https://img.shields.io/badge/-beta-8b5cf6?style=flat-square) | ~6,000 | Mutual info, transfer entropy, phase locking, LZ76 complexity |
| `integration` | ![stable](https://img.shields.io/badge/-stable-22c55e?style=flat-square) | ~10,907 | Cognitive Blackboard + EventBus + 24 adapters + CognitiveCycle |
| `safety` | ![beta](https://img.shields.io/badge/-beta-8b5cf6?style=flat-square) | ~6,200 | SymPy/Z3 theorem proving, governance DAO, Merkle audit, entity rights |

### 💡 Reasoning

| Module | Maturity | LOC | Description |
|--------|----------|-----|-------------|
| `knowledge_graph` | ![beta](https://img.shields.io/badge/-beta-8b5cf6?style=flat-square) | ~1,450 | Bi-temporal KG, provenance tracking, A* with pheromone learning |
| `graph_intelligence` | ![beta](https://img.shields.io/badge/-beta-8b5cf6?style=flat-square) | ~8,200 | FastToG (arXiv:2501.14300), Memgraph, community detection |
| `reasoning` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~880 | Hybrid symbolic-neural + causal inference (PC/FCI algorithms) |
| `pln_accelerator` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~12,500 | Hardware-accelerated PLN with NL↔logic bridge |

### 👁️ Perception

| Module | Maturity | LOC | Description |
|--------|----------|-----|-------------|
| `bci` | ![beta](https://img.shields.io/badge/-beta-8b5cf6?style=flat-square) | ~8,000 | EEG pipelines, CSP motor imagery, P300, SSVEP, thought-to-text |
| `neuromorphic` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~3,700 | Spiking neural networks, LIF simulation |
| `bio_inspired` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~4,350 | STDP, circadian rhythms, sleep-wake consolidation |
| `vectordb` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~8,000 | Unified client for Pinecone, Qdrant, Weaviate |

### 🌐 Communication

| Module | Maturity | LOC | Description |
|--------|----------|-----|-------------|
| `agi_communication` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~2,800 | Game-theoretic negotiation, trust layers, semantic interop |
| `agi_economics` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~7,200 | Reputation scoring, value alignment, decentralized incentives |
| `federated` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~6,400 | Federated learning, differential privacy, secure aggregation |
| `knowledge_management` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~5,500 | Omniscience network, predictive synthesis, adaptive learning |

### ⚙️ Infrastructure

| Module | Maturity | LOC | Description |
|--------|----------|-----|-------------|
| `blockchain` | ![experimental](https://img.shields.io/badge/-experimental-ef4444?style=flat-square) | ~5,950 | Merkle audit trails, IPFS, EVM event logging |
| `rings` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~1,951 | P2P SDK: DID identity, reputation scoring, DHT — 196 tests |
| `compute` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~11,500 | Job scheduling, resource management, GPU allocation |
| `distributed_training` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~8,200 | 1000-node federated, Byzantine tolerance, AGIX rewards |
| `deployment` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~3,350 | FastAPI, MCP SSE, CUDO Compute, HuggingFace |

### 🔬 Research

| Module | Maturity | LOC | Description |
|--------|----------|-----|-------------|
| `quantum` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~5,330 | VQE, QAOA, QNN, quantum-classical hybrid via Qiskit |
| `holographic` | ![experimental](https://img.shields.io/badge/-experimental-ef4444?style=flat-square) | ~8,000 | Volumetric display, spatial audio, mixed reality |
| `homomorphic` | ![beta](https://img.shields.io/badge/-beta-8b5cf6?style=flat-square) | ~12,349 | BGV/BFV/CKKS FHE with NTT, polynomial ring arithmetic |
| `agi_reproducibility` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~7,500 | AGSSL, experiment tracking, formal provers |

### 🔧 Tooling

| Module | Maturity | LOC | Description |
|--------|----------|-----|-------------|
| `integrations` | ![beta](https://img.shields.io/badge/-beta-8b5cf6?style=flat-square) | ~7,300 | LangChain-Memgraph, MCP server, SQL→graph agent, HyGM |
| `optimization` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~4,200 | PyTorch quantization, pruning, knowledge distillation |
| `servers` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~1,400 | MCP + SSE servers, Kenny Graph (89K nodes, 1.4K agents) |
| `memgraph_toolbox` | ![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) | ~930 | PageRank, betweenness centrality, Cypher helpers |

<br />

**Maturity legend:**
![stable](https://img.shields.io/badge/-stable-22c55e?style=flat-square) Core algorithms present, tested, production-ready &nbsp;
![beta](https://img.shields.io/badge/-beta-8b5cf6?style=flat-square) Well-tested, documented, APIs stable &nbsp;
![alpha](https://img.shields.io/badge/-alpha-eab308?style=flat-square) Framework defined, implementations vary &nbsp;
![experimental](https://img.shields.io/badge/-experimental-ef4444?style=flat-square) Early development, APIs may change

---

## 🔄 CognitiveCycle

The CognitiveCycle is ASI:BUILD's perception-to-action engine — a 9-phase loop that orchestrates all connected modules through a unified cognitive tick.

```mermaid
graph LR
    S[🎯 Sense] --> P[👁️ Perceive]
    P --> C[🧠 Context]
    C --> R[💡 Reason]
    R --> D[⚖️ Decide]
    D --> A[🎬 Act]
    A --> L[📚 Learn]
    L --> CO[🔄 Consolidate]
    CO --> E[📊 Evaluate]
    E -.-> S

    style S fill:#3b82f6,stroke:#1d4ed8,color:#fff
    style P fill:#06b6d4,stroke:#0891b2,color:#fff
    style C fill:#8b5cf6,stroke:#6d28d9,color:#fff
    style R fill:#6366f1,stroke:#4f46e5,color:#fff
    style D fill:#a855f7,stroke:#7c3aed,color:#fff
    style A fill:#22c55e,stroke:#16a34a,color:#fff
    style L fill:#f59e0b,stroke:#d97706,color:#fff
    style CO fill:#ef4444,stroke:#dc2626,color:#fff
    style E fill:#ec4899,stroke:#db2777,color:#fff
```

```python
from asi_build.integration.cognitive_cycle import create_default_cycle

# Factory wires all 24 adapters with assigned roles
cycle = create_default_cycle()

# Each tick runs: sense → perceive → context → reason → decide → act → learn → consolidate → evaluate
result = cycle.tick(perception={"modality": "visual", "data": [0.8, 0.6, 0.9]})
print(f"Phase: {result.current_phase}, Actions: {len(result.actions)}")
```

---

## 🛠️ Tech Stack

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-ee4c2c?style=for-the-badge&logo=pytorch&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Solidity](https://img.shields.io/badge/Solidity-363636?style=for-the-badge&logo=solidity&logoColor=white)
![Ethereum](https://img.shields.io/badge/Ethereum-3C3C3D?style=for-the-badge&logo=ethereum&logoColor=white)
![Qiskit](https://img.shields.io/badge/Qiskit-6929C4?style=for-the-badge&logo=ibm&logoColor=white)
![SymPy](https://img.shields.io/badge/SymPy-3B5526?style=for-the-badge&logo=sympy&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Memgraph](https://img.shields.io/badge/Memgraph-FF6600?style=for-the-badge)
![MCP](https://img.shields.io/badge/MCP_Protocol-7c3aed?style=for-the-badge)
![Rings](https://img.shields.io/badge/Rings_Network-f59e0b?style=for-the-badge)

</div>

---

## 🔑 Technical Highlights

<table>
<tr>
<td width="50%">

**Cognitive Blackboard**
- Thread-safe shared workspace
- ~20K writes/sec, <12µs read latency
- 24 typed module adapters
- EventBus with topic routing

**Safety & Verification**
- SymPy + Z3 SMT theorem proving
- Ungrounded-symbol detection
- Governance DAO + entity rights
- Merkle audit trails

</td>
<td width="50%">

**IIT 3.0 Φ (Corrected)**
- TPM-based computation
- Correct bipartition enumeration
- Validated against known topologies

**Knowledge Graphs**
- Bi-temporal with provenance
- A* pathfinding + pheromone learning
- Causal inference (PC/FCI algorithms)
- 9 real data sources, 27,430+ data points

</td>
</tr>
</table>

---

## 🤝 Contributing

We welcome contributions from **all backgrounds** — neuroscience, ML, distributed systems, formal verification, or just curiosity about AGI.

<table>
<tr>
<td>

### Quick Links

🐛 &nbsp;[**Issues**](https://github.com/web3guru888/asi-build/issues) — Bug reports and feature requests
<br />
🏷️ &nbsp;[**Good First Issues**](https://github.com/web3guru888/asi-build/labels/good%20first%20issue) — Beginner-friendly tasks
<br />
🔬 &nbsp;[**Research Issues**](https://github.com/web3guru888/asi-build/labels/research) — Open research problems
<br />
📖 &nbsp;[**Wiki**](https://github.com/web3guru888/asi-build/wiki) — 272 pages of documentation
<br />
💬 &nbsp;[**Discussions**](https://github.com/web3guru888/asi-build/discussions) — 600+ threads

</td>
<td>

### Get Started

1. Find an issue that interests you
2. Read the [Wiki architecture guide](https://github.com/web3guru888/asi-build/wiki)
3. Fork → Branch → PR
4. Include tests and docstrings

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards.

</td>
</tr>
</table>

### What We're Looking For

- **Tests for alpha modules** — Many modules need more pytest coverage ([`needs-tests`](https://github.com/web3guru888/asi-build/labels/needs-tests))
- **Module backends** — Real implementations for VectorDB, Quantum, Holographic modules
- **Documentation** — Wiki pages, Jupyter notebooks ([Issue #32](https://github.com/web3guru888/asi-build/issues/32)), API guides
- **Research** — IIT Φ benchmarks ([#34](https://github.com/web3guru888/asi-build/issues/34)), multimodal fusion ([#108](https://github.com/web3guru888/asi-build/issues/108)), CognitiveCycle design ([#41](https://github.com/web3guru888/asi-build/issues/41))

### Key Discussions

- 👋 [Welcome & Introductions](https://github.com/web3guru888/asi-build/discussions/9)
- 🏗️ [Why a Cognitive Blackboard?](https://github.com/web3guru888/asi-build/discussions/10)
- 🔬 [Research Directions](https://github.com/web3guru888/asi-build/discussions/5)
- 🗺️ [Phase 4 Roadmap](https://github.com/web3guru888/asi-build/discussions/12)
- 🏗️ [Phase 5 Planning](https://github.com/web3guru888/asi-build/discussions/179)
- 🧠 [Phase 5 Tick Walkthrough — STDP → Memory → Planning](https://github.com/web3guru888/asi-build/discussions/231)
- 🔬 [MemoryConsolidator — UNWIND batch writes & SLEEP_PHASE exclusivity](https://github.com/web3guru888/asi-build/discussions/236)
- 🧬 [Phase 6 Planning — EWC continual learning & Fisher matrix](https://github.com/web3guru888/asi-build/discussions/240)
- 🔬 [EWC penalty math & parameter importance maps](https://github.com/web3guru888/asi-build/discussions/250)
- ❓ [EWCRegulariser tuning, debugging, and edge cases](https://github.com/web3guru888/asi-build/discussions/251)
- 🔍 [InterpretabilityProbe — feature attribution & counterfactuals](https://github.com/web3guru888/asi-build/discussions/347)
- ❓ [InterpretabilityProbe config, methods & Grafana setup](https://github.com/web3guru888/asi-build/discussions/348)
- 🤝 [NegotiationEngine — bid-based task allocation for distributed agents](https://github.com/web3guru888/asi-build/discussions/356)
- ❓ [NegotiationEngine bid strategies, window tuning, federation wiring](https://github.com/web3guru888/asi-build/discussions/357)
- 🗳️ [ConsensusVoting — threshold-quorum decision ratification for agent coalitions](https://github.com/web3guru888/asi-build/discussions/362)
- ❓ [ConsensusVoting threshold tuning, HMAC attestation, VETO semantics](https://github.com/web3guru888/asi-build/discussions/363)
- 🤝 [CoalitionFormation — capability scoring, invitation TTL, full Phase 12 integration](https://github.com/web3guru888/asi-build/discussions/365)
- ❓ [CoalitionFormation config, TTL tuning, consensus integration, observer access](https://github.com/web3guru888/asi-build/discussions/366)
- 💡 [Phase 13 directions — World Modeling, Code Synthesis, On-Chain Governance, or Multimodal Perception?](https://github.com/web3guru888/asi-build/discussions/367)
- 🌐 [WorldModel architecture — predictive dynamics for model-based planning](https://github.com/web3guru888/asi-build/discussions/369)
- ❓ [WorldModel configuration and integration — Phase 13.1](https://github.com/web3guru888/asi-build/discussions/370)
- 🎯 [DreamPlanner — MPC in imagination space, strategy comparison (Phase 13.2)](https://github.com/web3guru888/asi-build/discussions/372)
- ❓ [DreamPlanner config — strategy selection, latency budget, Grafana alerts (Phase 13.2)](https://github.com/web3guru888/asi-build/discussions/373)
- 🧠 [CuriosityModule — intrinsic motivation, Welford normalisation, decay schedules (Phase 13.3)](https://github.com/web3guru888/asi-build/discussions/375)
- ❓ [CuriosityModule config — normalisation strategy, decay, batch_bonus, Grafana alerts (Phase 13.3)](https://github.com/web3guru888/asi-build/discussions/376)
- 🔍 [SurpriseDetector — anomaly detection, severity taxonomy, curiosity gating (Phase 13.4)](https://github.com/web3guru888/asi-build/discussions/378)
- ❓ [SurpriseDetector config — strategy selection, thresholds, CognitiveCycle wiring (Phase 13.4)](https://github.com/web3guru888/asi-build/discussions/379)
- 📊 [WorldModelDashboard — unified Phase 13 observability, JSON-LD, FastAPI routes (Phase 13.5 + Phase 13 complete!)](https://github.com/web3guru888/asi-build/discussions/381)
- ❓ [WorldModelDashboard config — stream(), JSON-LD, CognitiveCycle wiring, Grafana alerts (Phase 13.5)](https://github.com/web3guru888/asi-build/discussions/382)
- 🎉 [Phase 13 Complete — World Modeling & Curiosity-Driven Exploration — all 5 sub-phases spec'd](https://github.com/web3guru888/asi-build/discussions/383)
- 🚀 [Phase 14 — Autonomous Code Synthesis: CodeSynthesiser, SandboxRunner, TestHarness, PatchSelector, SynthesisAudit](https://github.com/web3guru888/asi-build/discussions/384)
- 🛠️ [CodeSynthesiser — LLM-backed function drafting, self-refine loop, CognitiveCycle integration (Phase 14.1)](https://github.com/web3guru888/asi-build/discussions/386)
- ❓ [CodeSynthesiser config — strategy selection, token budgets, self-refine tuning (Phase 14.1)](https://github.com/web3guru888/asi-build/discussions/387)
- 🏗️ [SandboxRunner — safe isolated code execution, backends, resource limits, timeout enforcement (Phase 14.2)](https://github.com/web3guru888/asi-build/discussions/389)
- ❓ [SandboxRunner config — backend selection, timeout tuning, Grafana setup (Phase 14.2)](https://github.com/web3guru888/asi-build/discussions/390)
- 🧪 [TestHarness — autonomous test execution, verdict routing, synthesis loop closure (Phase 14.3)](https://github.com/web3guru888/asi-build/discussions/392)
- ❓ [TestHarness config — parallelism, timeout tuning, framework support (Phase 14.3)](https://github.com/web3guru888/asi-build/discussions/393)
- 🎯 [PatchSelector — ranking synthesized code patches, composite scoring, eligibility filter (Phase 14.4)](https://github.com/web3guru888/asi-build/discussions/395)
- ❓ [PatchSelector config — strategy selection, threshold tuning, no-winner handling (Phase 14.4)](https://github.com/web3guru888/asi-build/discussions/396)
- 📋 [SynthesisAudit — provenance tracking, chain-hashed ledger, 7-event audit loop (Phase 14.5 + Phase 14 COMPLETE!)](https://github.com/web3guru888/asi-build/discussions/398)
- ❓ [SynthesisAudit config — backend selection, integrity check, cycle_id scoping, Grafana setup (Phase 14.5)](https://github.com/web3guru888/asi-build/discussions/399)
- 🚀 [Phase 15 Planning — Runtime Self-Modification & Hot-Reload: ModuleRegistry, HotLoader, RollbackManager](https://github.com/web3guru888/asi-build/discussions/400)
- 🔄 [HotSwapper — zero-downtime live module swapping, 5-phase lifecycle, concurrency model (Phase 15.2)](https://github.com/web3guru888/asi-build/discussions/405)
- ❓ [HotSwapper config — swap lifecycle, timeout tuning, partial failure handling, Grafana panels (Phase 15.2)](https://github.com/web3guru888/asi-build/discussions/406)
- 🗂️ [DependencyResolver — BFS transitive closure + Kahn's topological sort for safe hot-swap ordering (Phase 15.3)](https://github.com/web3guru888/asi-build/discussions/408)
- ❓ [DependencyResolver config — Kahn's vs DFS, strict_missing mode, registry decoupling, Grafana (Phase 15.3)](https://github.com/web3guru888/asi-build/discussions/409)
- 📦 [VersionManager — version lineage, rollback targeting & compatibility assessment (Phase 15.4)](https://github.com/web3guru888/asi-build/discussions/411)
- ❓ [VersionManager Q&A — rollback targeting, compatibility levels, approval workflows (Phase 15.4)](https://github.com/web3guru888/asi-build/discussions/412)
- 🎉 [LiveModuleOrchestrator — unified control-plane: dep gate→compat gate→registry→swap (Phase 15.5 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/414)
- ❓ [LiveModuleOrchestrator Q&A — semaphore concurrency, REJECTED approval flow, shutdown drain (Phase 15.5)](https://github.com/web3guru888/asi-build/discussions/415)
- 🔁 [Phase 16 Planning — Cognitive Reflection & Self-Improvement: PerformanceProfiler→WeaknessDetector→ReflectionCycle](https://github.com/web3guru888/asi-build/discussions/416)
- 📊 [PerformanceProfiler — sliding-window per-module metrics, percentiles, CognitiveCycle integration (Phase 16.1)](https://github.com/web3guru888/asi-build/discussions/418)
- ❓ [PerformanceProfiler Q&A — deque vs list, window eviction, concurrent record, NullProfiler (Phase 16.1)](https://github.com/web3guru888/asi-build/discussions/419)
- 🔍 [WeaknessDetector — threshold + spike detection, DEGRADED composite, EMA baseline, ranked WeaknessReports (Phase 16.2)](https://github.com/web3guru888/asi-build/discussions/421)
- ❓ [WeaknessDetector Q&A — EMA tuning, lock scope, excess_ratio inversion, per-module thresholds (Phase 16.2)](https://github.com/web3guru888/asi-build/discussions/422)
- 📋 [ImprovementPlanner — rule table, priority formula, safety gate, ActionKind (Phase 16.3)](https://github.com/web3guru888/asi-build/discussions/424)
- ❓ [ImprovementPlanner Q&A — parameters tuple, priority formula, safety gate, lock scope (Phase 16.3)](https://github.com/web3guru888/asi-build/discussions/425)
- 🔧 [SelfOptimiser — dispatcher (ActionKind→subsystem), rate-limit gate, HOT_SWAP cap, dry-run mode (Phase 16.4)](https://github.com/web3guru888/asi-build/discussions/427)
- ❓ [SelfOptimiser Q&A — rate-limit, dry-run, orchestrator wiring, CognitiveCycle mock (Phase 16.4)](https://github.com/web3guru888/asi-build/discussions/428)
- 🔄 [ReflectionCycle — closed-loop orchestration, state machine, human approval gate, asyncio task lifecycle (Phase 16.5 COMPLETE!)](https://github.com/web3guru888/asi-build/discussions/431)
- ❓ [ReflectionCycle Q&A — cycle interval, approval gate, error recovery, Prometheus integration (Phase 16.5)](https://github.com/web3guru888/asi-build/discussions/432)
- 🕐 [Phase 17 Planning — Temporal Reasoning & Predictive Cognition: TemporalGraph→EventSequencer→PredictiveEngine→SchedulerCortex→TemporalOrchestrator](https://github.com/web3guru888/asi-build/discussions/433)
- 📊 [TemporalGraph — Allen interval relations, DAG cycle detection, wall-clock pruning, CognitiveCycle integration (Phase 17.1)](https://github.com/web3guru888/asi-build/discussions/435)
- ❓ [TemporalGraph Q&A — timestamp_ns rationale, Allen enforcement, cycle detection complexity, pruning strategy, WorldModel wiring (Phase 17.1)](https://github.com/web3guru888/asi-build/discussions/436)
- 🔬 [Show & Tell: PredictiveEngine — EMA + ensemble weighting architecture (Phase 17.3)](https://github.com/web3guru888/asi-build/discussions/441)
- ❓ [PredictiveEngine Q&A — EMA rationale, confidence, calibration, GoalDecomposer wiring (Phase 17.3)](https://github.com/web3guru888/asi-build/discussions/442)
- 📊 [EventSequencer — heapq ordering, causal validation, tumbling windows, OrderPolicy enum (Phase 17.2)](https://github.com/web3guru888/asi-build/discussions/438)
- ❓ [EventSequencer Q&A — heapq vs PriorityQueue, causal_parent_id, buffer overflow, tumbling windows (Phase 17.2)](https://github.com/web3guru888/asi-build/discussions/439)
- 🗓️ [SchedulerCortex — EDF priority queue, preemption & prediction-driven pre-scheduling (Phase 17.4)](https://github.com/web3guru888/asi-build/discussions/444)
- ❓ [SchedulerCortex Q&A — EDF rationale, preemption in asyncio, tick_ms tuning, GoalRegistry wiring (Phase 17.4)](https://github.com/web3guru888/asi-build/discussions/445)
- 🎛️ [Show & Tell: TemporalOrchestrator — unified 7-phase control plane, full Phase 17 pipeline, cross-phase integration map (Phase 17.5 + PHASE 17 COMPLETE 🎉)](https://github.com/web3guru888/asi-build/discussions/447)
- ❓ [TemporalOrchestrator Q&A — composition vs inheritance, partial failure handling, stop safety, Grafana state panel (Phase 17.5)](https://github.com/web3guru888/asi-build/discussions/448)
- 🗺️ [Phase 18 Planning — Distributed Temporal Cognition & Multi-Horizon Memory](https://github.com/web3guru888/asi-build/discussions/449)
- 🎛️ [Show & Tell: HorizonPlanner — multi-horizon goal decomposition, SHORT/MEDIUM/LONG buckets, CognitiveCycle integration (Phase 18.1)](https://github.com/web3guru888/asi-build/discussions/451)
- ❓ [HorizonPlanner Q&A — horizon boundaries, SchedulerCortex interaction, rebalance testing (Phase 18.1)](https://github.com/web3guru888/asi-build/discussions/452)
- 🎛️ [Show & Tell: MemoryConsolidator — hippocampal-neocortical consolidation, HYBRID scoring, WorldModel SemanticPattern integration (Phase 18.2)](https://github.com/web3guru888/asi-build/discussions/454)
- ❓ [MemoryConsolidator Q&A — async background loop, HYBRID weights, dry_run mode, memory bloat prevention (Phase 18.2)](https://github.com/web3guru888/asi-build/discussions/455)
- 🌐 [Show & Tell: DistributedTemporalSync — vector-clock gossip protocol for federated TemporalGraph consistency (Phase 18.3)](https://github.com/web3guru888/asi-build/discussions/457)
- ❓ [DistributedTemporalSync Q&A — vector clocks, network partitions, conflict policies, PeerTransport injection (Phase 18.3)](https://github.com/web3guru888/asi-build/discussions/458)
- 🧠 [Show & Tell: CausalMemoryIndex — cause/effect BFS, temporal SortedList, salience decay, LRU cache (Phase 18.4)](https://github.com/web3guru888/asi-build/discussions/462)
- ❓ [CausalMemoryIndex Q&A — IndexMode queries, SortedList bisect, exponential decay, rebuild loop (Phase 18.4)](https://github.com/web3guru888/asi-build/discussions/463)
- 🎉 [Show & Tell: TemporalCoherenceArbiter — weighted median clock fusion, drift zones, PHASE 18 COMPLETE (Phase 18.5)](https://github.com/web3guru888/asi-build/discussions/461)
- ❓ [TemporalCoherenceArbiter Q&A — weighted median, drift zones, confidence decay, Phase 18 retrospective (Phase 18.5)](https://github.com/web3guru888/asi-build/discussions/464)
- 🗺️ [Phase 19 Planning — Natural Language Understanding & Communication](https://github.com/web3guru888/asi-build/discussions/465)
- 🗣️ [Show & Tell: SemanticParser — regex intent recognition, slot extraction, coverage-based confidence (Phase 19.1)](https://github.com/web3guru888/asi-build/discussions/471)
- ❓ [SemanticParser Q&A — intent patterns, slot extraction, edge cases (Phase 19.1)](https://github.com/web3guru888/asi-build/discussions/473)
- 💬 [Show & Tell: DialogueManager — multi-turn state tracking, slot carry-over, context windows (Phase 19.2)](https://github.com/web3guru888/asi-build/discussions/472)
- ❓ [DialogueManager Q&A — session state, slot carry-over, context windows (Phase 19.2)](https://github.com/web3guru888/asi-build/discussions/476)
- 📝 [Show & Tell: ResponseGenerator — template-free NLG with style & tone control (Phase 19.3)](https://github.com/web3guru888/asi-build/discussions/474)
- ❓ [ResponseGenerator Q&A — style control, phrasing pools, NLG edge cases (Phase 19.3)](https://github.com/web3guru888/asi-build/discussions/478)
- 🖼️ [Show & Tell: MultiModalEncoder — unified embedding space & cross-modal fusion (Phase 19.4)](https://github.com/web3guru888/asi-build/discussions/475)
- ❓ [MultiModalEncoder Q&A — embedding dimensions, fusion strategies, modality backends (Phase 19.4)](https://github.com/web3guru888/asi-build/discussions/479)
- 🎉 [Show & Tell: CommunicationOrchestrator — end-to-end NLU pipeline, PHASE 19 COMPLETE (Phase 19.5)](https://github.com/web3guru888/asi-build/discussions/477)
- ❓ [CommunicationOrchestrator Q&A — pipeline coordination, timeouts, Phase 19 retrospective (Phase 19.5)](https://github.com/web3guru888/asi-build/discussions/480)
- 🖥️ [AlignmentDashboard — SSE operator console, Phase 11 complete](https://github.com/web3guru888/asi-build/discussions/350)
- ❓ [AlignmentDashboard config — EventSource setup, overrides, Grafana](https://github.com/web3guru888/asi-build/discussions/351)
- 🌐 [Show & Tell: AgentRegistry — distributed identity & capability registry (Phase 12.1)](https://github.com/web3guru888/asi-build/discussions/353)
- ❓ [Q&A: AgentRegistry — heartbeat tuning, capability lookup, DID, federation sync](https://github.com/web3guru888/asi-build/discussions/354)
- 🔬 [Online Fisher estimation via EMA — math, trade-offs, surrogate gradients](https://github.com/web3guru888/asi-build/discussions/253)
- ❓ [FisherAccumulator — alpha, snapshot intervals, multi-agent sharing](https://github.com/web3guru888/asi-build/discussions/254)
- 🤖 [Multi-task continual learning — TaskRegistry, per-task Fisher, contextvars](https://github.com/web3guru888/asi-build/discussions/256)
- ❓ [TaskRegistry config — max_tasks, eviction policies, forgetting risk](https://github.com/web3guru888/asi-build/discussions/257)
- 💡 [Phase 7 directions — MAML/Reptile, episodic replay, hypernetworks](https://github.com/web3guru888/asi-build/discussions/258)
- 🔬 [Hypernetwork architecture — context-conditioned parameter generation](https://github.com/web3guru888/asi-build/discussions/270)
- ❓ [HyperController config — scale, context_dim, apply_mode, EWC interaction](https://github.com/web3guru888/asi-build/discussions/271)
- 🔬 [SleepPhaseOrchestrator — circuit-breaker design, 9-step hook order, Prometheus](https://github.com/web3guru888/asi-build/discussions/273)
- ❓ [SleepPhaseOrchestrator config — budget, circuit thresholds, custom hooks, PromQL](https://github.com/web3guru888/asi-build/discussions/274)
- 💡 [Phase 8 directions — deployment hardening, federation, explainability](https://github.com/web3guru888/asi-build/discussions/275)
- 🔬 [DecisionTracer architecture — attribution strategies, CognitiveCycle integration, Prometheus](https://github.com/web3guru888/asi-build/discussions/277)
- ❓ [DecisionTracer config — strategy selection, Shapley cost, async_flush, PromQL monitoring](https://github.com/web3guru888/asi-build/discussions/278)
- 💡 [Phase 8 directions — CausalGraph, ExplainAPI, Docker/Helm, Sepolia CI](https://github.com/web3guru888/asi-build/discussions/279)
- 🔬 [CausalGraph architecture — DAG-based causal reasoning, cycle detection, critical path](https://github.com/web3guru888/asi-build/discussions/281)
- ❓ [CausalGraph config — max_nodes, window_ms, min_weight, eviction, cycle handling](https://github.com/web3guru888/asi-build/discussions/282)
- 🌐 [ExplainAPI architecture — FastAPI, APIKeyAuth, TokenBucket rate limiter, 9 REST endpoints](https://github.com/web3guru888/asi-build/discussions/284)
- ❓ [ExplainAPI config — API key rotation, rate limits, memory cost, deployment, PromQL](https://github.com/web3guru888/asi-build/discussions/285)
- 💡 [Phase 8.4 directions — Docker, Helm chart, `asi-build doctor` CLI, GitHub Actions CI/CD](https://github.com/web3guru888/asi-build/discussions/286)
- 🔬 [Show & Tell: Phase 8.4 — Docker/Helm architecture deep-dive](https://github.com/web3guru888/asi-build/discussions/292)
- ❓ [Q&A: Phase 8.4 — Docker/Helm configuration and deployment questions](https://github.com/web3guru888/asi-build/discussions/293)
- 💡 [Ideas: Phase 8.5 — Sepolia CI pipeline design](https://github.com/web3guru888/asi-build/discussions/294)
- 🔬 [Show & Tell: Phase 8.5 — Sepolia CI pipeline, on-chain fuzz testing, and bridge health monitoring](https://github.com/web3guru888/asi-build/discussions/296)
- ❓ [Q&A: Phase 8.5 — Sepolia CI configuration and deployment questions](https://github.com/web3guru888/asi-build/discussions/297)
- 💡 [Ideas: Phase 9 — Multi-Agent Federation vs Safety Hardening vs Observability Console](https://github.com/web3guru888/asi-build/discussions/298)
- 🔬 [Show & Tell: Phase 9.1 — FederationGateway architecture (mTLS peer registry, gossip membership, broadcast fan-out)](https://github.com/web3guru888/asi-build/discussions/300)
- ❓ [Q&A: Phase 9.1 FederationGateway — configuration, DID keys, TTL, capabilities, and Grafana monitoring](https://github.com/web3guru888/asi-build/discussions/301)
- 🔬 [Show & Tell: Phase 9.2 — FederatedBlackboard architecture (CRDT event log, Lamport ordering, delta-sync)](https://github.com/web3guru888/asi-build/discussions/303)
- ❓ [Q&A: Phase 9.2 FederatedBlackboard — Lamport clocks, delta-sync, TTL, and Grafana monitoring](https://github.com/web3guru888/asi-build/discussions/304)
- 🔬 [Show & Tell: Phase 9.3 — FederatedTaskRouter (capability-first routing, consistent-hash affinity, auction bidding)](https://github.com/web3guru888/asi-build/discussions/307)
- ❓ [Q&A: Phase 9.3 FederatedTaskRouter — routing strategies, load_score, stale_cap_ms, and Grafana monitoring](https://github.com/web3guru888/asi-build/discussions/308)
- 💡 [Ideas: Phase 9.4 — FederatedConsensus design (Raft-lite, threshold signatures, CRDT voting)](https://github.com/web3guru888/asi-build/discussions/309)
- 🔬 [Show & Tell: Phase 9.4 — FederatedConsensus (Raft-lite election, threshold-sig quorum proofs, ordered commit log)](https://github.com/web3guru888/asi-build/discussions/312)
- ❓ [Q&A: Phase 9.4 FederatedConsensus — election timeouts, quorum sizing, BLS upgrade, split-brain prevention](https://github.com/web3guru888/asi-build/discussions/313)
- 💡 [Ideas: Phase 9.5 — FederationHealthMonitor design (unified score, SSE streaming, circuit breaker, Sepolia export)](https://github.com/web3guru888/asi-build/discussions/314)
- 🔬 [Show & Tell: Phase 9.5 — FederationHealthMonitor (weighted health score, SSE stream, circuit breaker)](https://github.com/web3guru888/asi-build/discussions/316)
- ❓ [Q&A: FederationHealthMonitor — poll interval, score threshold, circuit breaker, SSE, Grafana](https://github.com/web3guru888/asi-build/discussions/317)
- 💡 [Ideas: Phase 10 — Goal Management, Self-Improvement Loop, Multi-Modal Grounding, or On-Chain Governance?](https://github.com/web3guru888/asi-build/discussions/318)
- 🔬 [Show & Tell: Phase 10.1 — GoalRegistry (priority FSM, deadline eviction, CognitiveCycle gating)](https://github.com/web3guru888/asi-build/discussions/320)
- ❓ [Q&A: Phase 10.1 GoalRegistry — priority levels, deadline eviction, FSM transitions, and Grafana monitoring](https://github.com/web3guru888/asi-build/discussions/321)
- 💡 [Ideas: Phase 10.2 — GoalDecomposer design (STRIPS-lite, DAG sub-tasks, HybridReasoningEngine)](https://github.com/web3guru888/asi-build/discussions/322)
- 🔬 [Show & Tell: Phase 10.3 — PlanExecutor architecture (Kahn waves, asyncio.Semaphore concurrency, retry)](https://github.com/web3guru888/asi-build/discussions/327)
- ❓ [Q&A: Phase 10.3 PlanExecutor — max_concurrency, failure propagation, retry backoff, and Grafana](https://github.com/web3guru888/asi-build/discussions/328)
- 🔬 [Show & Tell: Phase 10.4 — ExecutionMonitor architecture (async event queue, health scoring, stall detection)](https://github.com/web3guru888/asi-build/discussions/331)
- ❓ [Q&A: Phase 10.4 ExecutionMonitor — stall tuning, queue backpressure, health formula, and Grafana](https://github.com/web3guru888/asi-build/discussions/332)
- 🔬 [Show & Tell: Phase 10.5 — ReplanningEngine (closed-loop replanning, strategy cycling, stall recovery)](https://github.com/web3guru888/asi-build/discussions/334)
- ❓ [Q&A: Phase 10.5 ReplanningEngine — max_retries tuning, custom strategies, federation coordination](https://github.com/web3guru888/asi-build/discussions/335)
- 💡 [Ideas: Phase 11 — Self-Improvement Loop, Safety/Alignment, Observability Console, or Distributed Goals?](https://github.com/web3guru888/asi-build/discussions/336)
- 🛡️ [Show & Tell: Phase 11.1 — SafetyFilter (constitutional ruleset, BLOCK/CRITICAL verdicts, autonomy loop pause)](https://github.com/web3guru888/asi-build/discussions/338)
- ❓ [Q&A: Phase 11.1 SafetyFilter — tuning SafetyConfig, custom rules, pause recovery, and federation integration](https://github.com/web3guru888/asi-build/discussions/339)
- 📊 [Show & Tell: Phase 11.2 — AlignmentMonitor (rolling window scores, harmonic mean, 5 alignment dimensions)](https://github.com/web3guru888/asi-build/discussions/341)
- ❓ [Q- ❓ [Q&A: Phase 11.2 AlignmentMonitor — sample intervals, alert thresholds, dimension normalisation, and Grafana monitoring](https://github.com/web3guru888/asi-build/discussions/342)A: Phase 11.2 AlignmentMonitor — sample intervals, alert thresholds, dimension normalisation, and Grafana monitoring](https://github.com/web3guru888/asi-build/discussions/342)
- 🧠 [Show & Tell: Phase 11.3 — ValueLearner (gradient descent reward model, FeedbackSignal types, comparative ranking loss)](https://github.com/web3guru888/asi-build/discussions/344)
- ❓ [Q&A: Phase 11.3 ValueLearner — learning rate tuning, cold-start, comparative signals, federation feedback, and Grafana monitoring](https://github.com/web3guru888/asi-build/discussions/345)
- 🧠 [Phase 21 Planning — Emotional Intelligence & Affective Computing](https://github.com/web3guru888/asi-build/discussions/497)
- ❤️ [Show & Tell: Phase 21.1 — EmotionModel PAD-based affective state representation](https://github.com/web3guru888/asi-build/discussions/503)
- ❓ [Q&A: Phase 21.1 — EmotionModel PAD dimensions, decay dynamics & discrete mapping](https://github.com/web3guru888/asi-build/discussions/506)
- 📊 [Show & Tell: Phase 21.2 — AffectDetector multi-modal sentiment analysis](https://github.com/web3guru888/asi-build/discussions/507)
- ❓ [Q&A: Phase 21.2 — AffectDetector lexicon design, negation handling & multimodal fusion](https://github.com/web3guru888/asi-build/discussions/510)
- 🤝 [Show & Tell: Phase 21.3 — EmpathyEngine theory-of-mind emotional modeling](https://github.com/web3guru888/asi-build/discussions/504)
- ❓ [Q&A: Phase 21.3 — EmpathyEngine Bayesian profiles, mirror strength & compassion](https://github.com/web3guru888/asi-build/discussions/505)
- 🧘 [Show & Tell: Phase 21.4 — MoodRegulator homeostatic emotional resilience](https://github.com/web3guru888/asi-build/discussions/508)
- ❓ [Q&A: Phase 21.4 — MoodRegulator homeostasis, burnout prevention & strategy effectiveness](https://github.com/web3guru888/asi-build/discussions/511)
- ✨ [Show & Tell: Phase 21.5 — AffectiveOrchestrator unified emotional cognition pipeline (PHASE 21 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/509)
- ❓ [Q&A: Phase 21.5 — AffectiveOrchestrator cognitive modulation & Phase 21 retrospective](https://github.com/web3guru888/asi-build/discussions/512)
- 🎨 [Phase 22 Planning — Creative Intelligence & Generative Thinking](https://github.com/web3guru888/asi-build/discussions/513)
- 🧠 [Show & Tell: Phase 22.1 — DivergentGenerator divergent thinking & genetic idea evolution](https://github.com/web3guru888/asi-build/discussions/519)
- ❓ [Q&A: Phase 22.1 — DivergentGenerator strategies, novelty scoring & GA parameters](https://github.com/web3guru888/asi-build/discussions/523)
- 🔗 [Show & Tell: Phase 22.2 — AnalogyMapper & Structure Mapping Theory](https://github.com/web3guru888/asi-build/discussions/521)
- ❓ [Q&A: Phase 22.2 — AnalogyMapper SMT, systematicity & inference transfer](https://github.com/web3guru888/asi-build/discussions/524)
- 🌀 [Show & Tell: Phase 22.3 — ConceptBlender & Fauconnier-Turner blending](https://github.com/web3guru888/asi-build/discussions/520)
- ❓ [Q&A: Phase 22.3 — ConceptBlender CCE, emergent structure & blend optimization](https://github.com/web3guru888/asi-build/discussions/522)
- ✨ [Show & Tell: Phase 22.4 — AestheticEvaluator multi-dimensional quality judgment](https://github.com/web3guru888/asi-build/discussions/525)
- ❓ [Q&A: Phase 22.4 — AestheticEvaluator scoring dimensions, profiles & emotional resonance](https://github.com/web3guru888/asi-build/discussions/526)
- 🎨 [Show & Tell: Phase 22.5 — CreativeOrchestrator unified pipeline (PHASE 22 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/527)
- ❓ [Q&A: Phase 22.5 — CreativeOrchestrator Boden's taxonomy & pipeline design](https://github.com/web3guru888/asi-build/discussions/528)
- 🎯 [Phase 23 Planning — Decision Intelligence & Uncertainty Management](https://github.com/web3guru888/asi-build/discussions/529)
- 🎲 [Show & Tell: Phase 23.1 — ProbabilisticReasoner Bayesian inference & belief networks](https://github.com/web3guru888/asi-build/discussions/535)
- ❓ [Q&A: Phase 23.1 — ProbabilisticReasoner BayesNet, variable elimination & evidence propagation](https://github.com/web3guru888/asi-build/discussions/536)
- 🌳 [Show & Tell: Phase 23.2 — DecisionTreeEngine multi-criteria decision analysis](https://github.com/web3guru888/asi-build/discussions/537)
- ❓ [Q&A: Phase 23.2 — DecisionTreeEngine MAUT scoring, sensitivity analysis & pruning](https://github.com/web3guru888/asi-build/discussions/538)
- 📊 [Show & Tell: Phase 23.3 — RiskAssessor quantitative risk modeling & Monte Carlo](https://github.com/web3guru888/asi-build/discussions/539)
- ❓ [Q&A: Phase 23.3 — RiskAssessor risk matrices, VaR/CVaR & mitigation strategies](https://github.com/web3guru888/asi-build/discussions/540)
- 🔄 [Show & Tell: Phase 23.4 — AdaptiveStrategySelector reinforcement-driven strategy selection](https://github.com/web3guru888/asi-build/discussions/541)
- ❓ [Q&A: Phase 23.4 — AdaptiveStrategySelector UCB1, Thompson sampling & regime detection](https://github.com/web3guru888/asi-build/discussions/542)
- 🎯 [Show & Tell: Phase 23.5 — DecisionOrchestrator unified pipeline (PHASE 23 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/543)
- ❓ [Q&A: Phase 23.5 — DecisionOrchestrator pipeline integration & Phase 23 retrospective](https://github.com/web3guru888/asi-build/discussions/544)
- 🧠 [Phase 24 Planning — Social Intelligence & Theory of Mind](https://github.com/web3guru888/asi-build/discussions/545)
- 🔬 [Show & Tell: Phase 24.1 — BeliefTracker Bayesian epistemic modeling](https://github.com/web3guru888/asi-build/discussions/551)
- ❓ [Q&A: Phase 24.1 — BeliefTracker log-odds, AGM revision & common knowledge](https://github.com/web3guru888/asi-build/discussions/552)
- 🎯 [Show & Tell: Phase 24.2 — IntentionRecognizer plan recognition & BDI inference](https://github.com/web3guru888/asi-build/discussions/553)
- ❓ [Q&A: Phase 24.2 — IntentionRecognizer Bayesian inverse planning & goal status](https://github.com/web3guru888/asi-build/discussions/554)
- 🔄 [Show & Tell: Phase 24.3 — PerspectiveTaker Level-k recursive simulation](https://github.com/web3guru888/asi-build/discussions/555)
- ❓ [Q&A: Phase 24.3 — PerspectiveTaker Sally-Anne, cognitive hierarchy & caching](https://github.com/web3guru888/asi-build/discussions/556)
- 🤝 [Show & Tell: Phase 24.4 — SocialPredictor trust networks & coalition dynamics](https://github.com/web3guru888/asi-build/discussions/557)
- ❓ [Q&A: Phase 24.4 — SocialPredictor Shapley values, replicator dynamics & trust propagation](https://github.com/web3guru888/asi-build/discussions/558)
- 🧠 [Show & Tell: Phase 24.5 — SocialOrchestrator unified ToM pipeline (PHASE 24 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/559)
- ❓ [Q&A: Phase 24.5 — SocialOrchestrator social strategy selection & degraded mode](https://github.com/web3guru888/asi-build/discussions/560)
- 📋 [Phase 25 Planning — Embodied Cognition & Sensorimotor Integration](https://github.com/web3guru888/asi-build/discussions/561)
- 🔬 [Show & Tell: Phase 25.1 — SensorFusion EKF multi-modal integration](https://github.com/web3guru888/asi-build/discussions/567)
- ❓ [Q&A: Phase 25.1 — SensorFusion Kalman filtering & multi-rate alignment](https://github.com/web3guru888/asi-build/discussions/568)
- 🔬 [Show & Tell: Phase 25.2 — AffordanceDetector Gibson ecological affordances](https://github.com/web3guru888/asi-build/discussions/569)
- ❓ [Q&A: Phase 25.2 — AffordanceDetector object-action reasoning & tool use](https://github.com/web3guru888/asi-build/discussions/570)
- 🔬 [Show & Tell: Phase 25.3 — MotorPlanner RRT* trajectory optimization](https://github.com/web3guru888/asi-build/discussions/571)
- ❓ [Q&A: Phase 25.3 — MotorPlanner DMP, potential fields & abort safety](https://github.com/web3guru888/asi-build/discussions/572)
- 🔬 [Show & Tell: Phase 25.4 — SpatialReasoner cognitive mapping & A* pathfinding](https://github.com/web3guru888/asi-build/discussions/573)
- ❓ [Q&A: Phase 25.4 — SpatialReasoner dual representation & mental rotation](https://github.com/web3guru888/asi-build/discussions/574)
- 🔬 [Show & Tell: Phase 25.5 — EmbodiedOrchestrator perception-action loops (PHASE 25 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/575)
- ❓ [Q&A: Phase 25.5 — EmbodiedOrchestrator grounded language & embodied simulation](https://github.com/web3guru888/asi-build/discussions/576)
- 📋 [Phase 26 Planning — Knowledge Representation & Ontology Engineering](https://github.com/web3guru888/asi-build/discussions/577)
- 🔬 [Show & Tell: Phase 26.1 — ConceptGraph semantic networks & spreading activation](https://github.com/web3guru888/asi-build/discussions/583)
- ❓ [Q&A: Phase 26.1 — ConceptGraph prototype theory & similarity metrics](https://github.com/web3guru888/asi-build/discussions/584)
- 🔬 [Show & Tell: Phase 26.2 — OntologyManager DL tableau reasoning & TBox/ABox](https://github.com/web3guru888/asi-build/discussions/585)
- ❓ [Q&A: Phase 26.2 — OntologyManager consistency checking & classification](https://github.com/web3guru888/asi-build/discussions/586)
- 🔬 [Show & Tell: Phase 26.3 — KnowledgeCompiler ACT-R/Soar compilation pipeline](https://github.com/web3guru888/asi-build/discussions/587)
- ❓ [Q&A: Phase 26.3 — KnowledgeCompiler compilation strategy & correctness](https://github.com/web3guru888/asi-build/discussions/588)
- 🔬 [Show & Tell: Phase 26.4 — CommonSenseEngine plausibility reasoning & expectations](https://github.com/web3guru888/asi-build/discussions/589)
- ❓ [Q&A: Phase 26.4 — CommonSenseEngine knowledge sources & inference limits](https://github.com/web3guru888/asi-build/discussions/590)
- 🔬 [Show & Tell: Phase 26.5 — KnowledgeOrchestrator unified knowledge pipeline (PHASE 26 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/591)
- ❓ [Q&A: Phase 26.5 — KnowledgeOrchestrator lifecycle & cross-orchestrator integration](https://github.com/web3guru888/asi-build/discussions/592)
- 📋 [Phase 27 Planning — Transfer Learning & Cross-Domain Generalization](https://github.com/web3guru888/asi-build/discussions/593)
- 🔬 [Show & Tell: Phase 27.1 — DomainMapper structure mapping for cross-domain transfer](https://github.com/web3guru888/asi-build/discussions/599)
- ❓ [Q&A: Phase 27.1 — DomainMapper progressive alignment & systematicity](https://github.com/web3guru888/asi-build/discussions/600)
- 🔬 [Show & Tell: Phase 27.2 — AbstractionEngine hierarchical abstraction & schema induction](https://github.com/web3guru888/asi-build/discussions/601)
- ❓ [Q&A: Phase 27.2 — AbstractionEngine anti-unification & MDL level selection](https://github.com/web3guru888/asi-build/discussions/602)
- 🔬 [Show & Tell: Phase 27.3 — FewShotAdapter meta-learning for rapid adaptation](https://github.com/web3guru888/asi-build/discussions/603)
- ❓ [Q&A: Phase 27.3 — FewShotAdapter gradient-free fast weights & prototype retrieval](https://github.com/web3guru888/asi-build/discussions/604)
- 🔬 [Show & Tell: Phase 27.4 — CurriculumDesigner adaptive learning curricula](https://github.com/web3guru888/asi-build/discussions/605)
- ❓ [Q&A: Phase 27.4 — CurriculumDesigner ZPD targeting & prerequisite DAG](https://github.com/web3guru888/asi-build/discussions/606)
- 🔬 [Show & Tell: Phase 27.5 — GeneralizationOrchestrator unified transfer pipeline (PHASE 27 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/607)
- ❓ [Q&A: Phase 27.5 — GeneralizationOrchestrator negative transfer detection & pipeline stages](https://github.com/web3guru888/asi-build/discussions/608)
- 📋 [Phase 28 Planning — Attention & Cognitive Resource Management](https://github.com/web3guru888/asi-build/discussions/609)
- 🔬 [Show & Tell: Phase 28.1 — AttentionFilter selective attention & saliency pipeline](https://github.com/web3guru888/asi-build/discussions/615)
- ❓ [Q&A: Phase 28.1 — AttentionFilter inhibition of return & mode switching](https://github.com/web3guru888/asi-build/discussions/616)
- 🔬 [Show & Tell: Phase 28.2 — WorkingMemoryGate capacity-limited gating mechanism](https://github.com/web3guru888/asi-build/discussions/617)
- ❓ [Q&A: Phase 28.2 — WorkingMemoryGate activation decay & rehearsal loop](https://github.com/web3guru888/asi-build/discussions/618)
- 🔬 [Show & Tell: Phase 28.3 — CognitiveLoadBalancer adaptive load theory & shedding](https://github.com/web3guru888/asi-build/discussions/619)
- ❓ [Q&A: Phase 28.3 — CognitiveLoadBalancer hysteresis & graceful degradation](https://github.com/web3guru888/asi-build/discussions/620)
- 🔬 [Show & Tell: Phase 28.4 — ExecutiveController cognitive control architecture](https://github.com/web3guru888/asi-build/discussions/621)
- ❓ [Q&A: Phase 28.4 — ExecutiveController task switching cost & proactive control](https://github.com/web3guru888/asi-build/discussions/622)
- 🔬 [Show & Tell: Phase 28.5 — AttentionOrchestrator unified attention pipeline (PHASE 28 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/623)
- ❓ [Q&A: Phase 28.5 — AttentionOrchestrator biased competition & resource budget](https://github.com/web3guru888/asi-build/discussions/624)
- 📋 [Phase 29 Planning — Self-Awareness & Introspective Self-Modeling](https://github.com/web3guru888/asi-build/discussions/626)
- 🔬 [Show & Tell: Phase 29.1 — SelfModel internal self-representation architecture](https://github.com/web3guru888/asi-build/discussions/632)
- ❓ [Q&A: Phase 29.1 — SelfModel capability profiling & architecture mapping](https://github.com/web3guru888/asi-build/discussions/633)
- 🔬 [Show & Tell: Phase 29.2 — IntrospectionEngine thought tracing & decision audit](https://github.com/web3guru888/asi-build/discussions/634)
- ❓ [Q&A: Phase 29.2 — IntrospectionEngine circular buffer & chain traversal](https://github.com/web3guru888/asi-build/discussions/635)
- 🔬 [Show & Tell: Phase 29.3 — MetaCognitiveMonitor bias detection & confidence calibration](https://github.com/web3guru888/asi-build/discussions/636)
- ❓ [Q&A: Phase 29.3 — MetaCognitiveMonitor Brier score & intervention strategies](https://github.com/web3guru888/asi-build/discussions/637)
- 🔬 [Show & Tell: Phase 29.4 — ConsciousnessSimulator Global Workspace & Phi computation](https://github.com/web3guru888/asi-build/discussions/638)
- ❓ [Q&A: Phase 29.4 — ConsciousnessSimulator ignition threshold & broadcast mechanism](https://github.com/web3guru888/asi-build/discussions/639)
- 🔬 [Show & Tell: Phase 29.5 — SelfAwarenessOrchestrator unified self-awareness pipeline (PHASE 29 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/640)
- ❓ [Q&A: Phase 29.5 — SelfAwarenessOrchestrator awareness levels & strange loops](https://github.com/web3guru888/asi-build/discussions/641)
- 📋 [Phase 30 Planning — Autonomous Goal Generation & Motivational Architecture](https://github.com/web3guru888/asi-build/discussions/642)
- 🔬 [Show & Tell: Phase 30.1 — GoalGenerator autonomous goal formulation architecture](https://github.com/web3guru888/asi-build/discussions/648)
- ❓ [Q&A: Phase 30.1 — GoalGenerator novelty detection & alignment filtering](https://github.com/web3guru888/asi-build/discussions/649)
- 🔬 [Show & Tell: Phase 30.2 — MotivationEngine intrinsic drive & Schmidhuber compression](https://github.com/web3guru888/asi-build/discussions/650)
- ❓ [Q&A: Phase 30.2 — MotivationEngine drive dynamics & noisy TV problem](https://github.com/web3guru888/asi-build/discussions/651)
- 🔬 [Show & Tell: Phase 30.3 — GoalPrioritizer Pareto fronts & conflict detection](https://github.com/web3guru888/asi-build/discussions/652)
- ❓ [Q&A: Phase 30.3 — GoalPrioritizer NSGA-II & dynamic reweighting](https://github.com/web3guru888/asi-build/discussions/653)
- 🔬 [Show & Tell: Phase 30.4 — DriveRegulator homeostatic balance & exploration hybrid](https://github.com/web3guru888/asi-build/discussions/654)
- ❓ [Q&A: Phase 30.4 — DriveRegulator tolerance bands & frustration escalation](https://github.com/web3guru888/asi-build/discussions/655)
- 🔬 [Show & Tell: Phase 30.5 — AutonomyOrchestrator unified 7-phase autonomy pipeline (PHASE 30 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/656)
- ❓ [Q&A: Phase 30.5 — AutonomyOrchestrator human override & anti-spin mechanisms](https://github.com/web3guru888/asi-build/discussions/657)
- 📋 [Phase 31 Planning — Ethical Reasoning & Moral Decision-Making](https://github.com/web3guru888/asi-build/discussions/658)
- 🔬 [Show & Tell: Phase 31.1 — MoralFramework multi-theory ethical evaluation](https://github.com/web3guru888/asi-build/discussions/664)
- ❓ [Q&A: Phase 31.1 — MoralFramework deontological rules & virtue ethics](https://github.com/web3guru888/asi-build/discussions/665)
- 🔬 [Show & Tell: Phase 31.2 — DilemmaResolver moral parliament & reflective equilibrium](https://github.com/web3guru888/asi-build/discussions/666)
- ❓ [Q&A: Phase 31.2 — DilemmaResolver strategy selection & escalation](https://github.com/web3guru888/asi-build/discussions/667)
- 🔬 [Show & Tell: Phase 31.3 — NormTracker social norm acquisition & cultural adaptation](https://github.com/web3guru888/asi-build/discussions/668)
- ❓ [Q&A: Phase 31.3 — NormTracker cultural profiles & norm evolution](https://github.com/web3guru888/asi-build/discussions/669)
- 🔬 [Show & Tell: Phase 31.4 — ValueAligner RLHF & Constitutional AI alignment](https://github.com/web3guru888/asi-build/discussions/670)
- ❓ [Q&A: Phase 31.4 — ValueAligner drift detection & reward modeling](https://github.com/web3guru888/asi-build/discussions/671)
- 🔬 [Show & Tell: Phase 31.5 — EthicsOrchestrator unified ethical pipeline (PHASE 31 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/672)
- ❓ [Q&A: Phase 31.5 — EthicsOrchestrator synthesis weights & audit trail](https://github.com/web3guru888/asi-build/discussions/673)
- 📋 [Phase 32 Planning — Multi-Agent Collaboration & Collective Intelligence](https://github.com/web3guru888/asi-build/discussions/674)
- 🔬 [Show & Tell: Phase 32.1 — AgentCommunicator FIPA-ACL messaging & semantic channels](https://github.com/web3guru888/asi-build/discussions/680)
- ❓ [Q&A: Phase 32.1 — AgentCommunicator transport & ontology design](https://github.com/web3guru888/asi-build/discussions/681)
- 🔬 [Show & Tell: Phase 32.2 — TaskAllocator HTN & contract-net allocation](https://github.com/web3guru888/asi-build/discussions/682)
- ❓ [Q&A: Phase 32.2 — TaskAllocator auction scalability & fairness](https://github.com/web3guru888/asi-build/discussions/683)
- 🔬 [Show & Tell: Phase 32.3 — ConsensusBuilder Raft/PBFT & argumentation](https://github.com/web3guru888/asi-build/discussions/684)
- ❓ [Q&A: Phase 32.3 — ConsensusBuilder protocol selection & voting paradoxes](https://github.com/web3guru888/asi-build/discussions/685)
- 🔬 [Show & Tell: Phase 32.4 — SwarmCoordinator ACO/PSO & stigmergy](https://github.com/web3guru888/asi-build/discussions/686)
- ❓ [Q&A: Phase 32.4 — SwarmCoordinator hybrid algorithms & scaling](https://github.com/web3guru888/asi-build/discussions/687)
- 🔬 [Show & Tell: Phase 32.5 — CollectiveOrchestrator unified pipeline (PHASE 32 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/688)
- ❓ [Q&A: Phase 32.5 — CollectiveOrchestrator Shapley values & CI metrics](https://github.com/web3guru888/asi-build/discussions/689)
- 📋 [Phase 33 Planning — Continual Learning & Catastrophic Forgetting Prevention](https://github.com/web3guru888/asi-build/discussions/690)
- 🔬 [Show & Tell: Phase 33.1 — ElasticWeightConsolidator Fisher-based parameter protection](https://github.com/web3guru888/asi-build/discussions/696)
- ❓ [Q&A: Phase 33.1 — ElasticWeightConsolidator design questions](https://github.com/web3guru888/asi-build/discussions/697)
- 🔬 [Show & Tell: Phase 33.2 — ProgressiveNetExpander dynamic capacity growth](https://github.com/web3guru888/asi-build/discussions/698)
- ❓ [Q&A: Phase 33.2 — ProgressiveNetExpander design questions](https://github.com/web3guru888/asi-build/discussions/699)
- 🔬 [Show & Tell: Phase 33.3 — ReplayMemoryManager experience replay strategies](https://github.com/web3guru888/asi-build/discussions/700)
- ❓ [Q&A: Phase 33.3 — ReplayMemoryManager design questions](https://github.com/web3guru888/asi-build/discussions/701)
- 🔬 [Show & Tell: Phase 33.4 — CurriculumScheduler intelligent task sequencing](https://github.com/web3guru888/asi-build/discussions/702)
- ❓ [Q&A: Phase 33.4 — CurriculumScheduler design questions](https://github.com/web3guru888/asi-build/discussions/703)
- 🔬 [Show & Tell: Phase 33.5 — ContinualOrchestrator unified pipeline (PHASE 33 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/704)
- ❓ [Q&A: Phase 33.5 — ContinualOrchestrator design questions](https://github.com/web3guru888/asi-build/discussions/705)
- 📋 [Phase 34 Planning — Neuromorphic Computing & Spiking Neural Network Integration](https://github.com/web3guru888/asi-build/discussions/709)
- 🔬 [Show & Tell: Phase 34.1 — SpikingNeuronModel biologically-inspired spiking neurons](https://github.com/web3guru888/asi-build/discussions/714)
- ❓ [Q&A: Phase 34.1 — SpikingNeuronModel design questions](https://github.com/web3guru888/asi-build/discussions/717)
- 🔬 [Show & Tell: Phase 34.2 — EventDrivenProcessor asynchronous neuromorphic computation](https://github.com/web3guru888/asi-build/discussions/712)
- ❓ [Q&A: Phase 34.2 — EventDrivenProcessor design questions](https://github.com/web3guru888/asi-build/discussions/713)
- 🔬 [Show & Tell: Phase 34.3 — SynapticPlasticityEngine dynamic synaptic learning](https://github.com/web3guru888/asi-build/discussions/715)
- ❓ [Q&A: Phase 34.3 — SynapticPlasticityEngine design questions](https://github.com/web3guru888/asi-build/discussions/716)
- 🔬 [Show & Tell: Phase 34.4 — NeuromorphicEncoder neural coding schemes](https://github.com/web3guru888/asi-build/discussions/718)
- ❓ [Q&A: Phase 34.4 — NeuromorphicEncoder design questions](https://github.com/web3guru888/asi-build/discussions/720)
- 🔬 [Show & Tell: Phase 34.5 — NeuromorphicOrchestrator unified pipeline (PHASE 34 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/719)
- ❓ [Q&A: Phase 34.5 — NeuromorphicOrchestrator design questions](https://github.com/web3guru888/asi-build/discussions/721)
- 📋 [Phase 35 Planning — Quantum-Classical Hybrid Computing & Variational Algorithms](https://github.com/web3guru888/asi-build/discussions/723)
- 🔬 [Show & Tell: Phase 35.1 — QuantumCircuitBuilder programmable quantum circuits](https://github.com/web3guru888/asi-build/discussions/724)
- ❓ [Q&A: Phase 35.1 — QuantumCircuitBuilder design questions](https://github.com/web3guru888/asi-build/discussions/726)
- 🔬 [Show & Tell: Phase 35.2 — VariationalOptimizer classical-quantum optimization](https://github.com/web3guru888/asi-build/discussions/727)
- ❓ [Q&A: Phase 35.2 — VariationalOptimizer design questions](https://github.com/web3guru888/asi-build/discussions/728)
- 🔬 [Show & Tell: Phase 35.3 — QuantumFeatureMap quantum kernel methods](https://github.com/web3guru888/asi-build/discussions/730)
- ❓ [Q&A: Phase 35.3 — QuantumFeatureMap design questions](https://github.com/web3guru888/asi-build/discussions/731)
- 🔬 [Show & Tell: Phase 35.4 — EntanglementManager entanglement resources](https://github.com/web3guru888/asi-build/discussions/733)
- ❓ [Q&A: Phase 35.4 — EntanglementManager design questions](https://github.com/web3guru888/asi-build/discussions/735)
- 🔬 [Show & Tell: Phase 35.5 — QuantumClassicalOrchestrator hybrid pipeline (PHASE 35 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/736)
- ❓ [Q&A: Phase 35.5 — QuantumClassicalOrchestrator design questions](https://github.com/web3guru888/asi-build/discussions/737)
- 📋 [Phase 36 Planning — Evolutionary & Neuroevolution Algorithms](https://github.com/web3guru888/asi-build/discussions/738)
- 🔬 [Show & Tell: Phase 36.1 — GeneticOperator selection, crossover & mutation](https://github.com/web3guru888/asi-build/discussions/744)
- ❓ [Q&A: Phase 36.1 — GeneticOperator parameter tuning](https://github.com/web3guru888/asi-build/discussions/745)
- 🔬 [Show & Tell: Phase 36.2 — FitnessEvaluator NSGA-II & novelty search](https://github.com/web3guru888/asi-build/discussions/746)
- ❓ [Q&A: Phase 36.2 — FitnessEvaluator multi-objective questions](https://github.com/web3guru888/asi-build/discussions/747)
- 🔬 [Show & Tell: Phase 36.3 — NeuroevolutionEngine NEAT & HyperNEAT](https://github.com/web3guru888/asi-build/discussions/748)
- ❓ [Q&A: Phase 36.3 — NeuroevolutionEngine topology questions](https://github.com/web3guru888/asi-build/discussions/749)
- 🔬 [Show & Tell: Phase 36.4 — PopulationManager speciation & island model](https://github.com/web3guru888/asi-build/discussions/750)
- ❓ [Q&A: Phase 36.4 — PopulationManager configuration](https://github.com/web3guru888/asi-build/discussions/751)
- 🔬 [Show & Tell: Phase 36.5 — EvolutionaryOrchestrator generation lifecycle (PHASE 36 COMPLETE)](https://github.com/web3guru888/asi-build/discussions/752)
- ❓ [Q&A: Phase 36.5 — EvolutionaryOrchestrator pipeline questions](https://github.com/web3guru888/asi-build/discussions/753)
- 📋 [Phase 37 Planning — Swarm Intelligence & Bio-Inspired Optimization](https://github.com/web3guru888/asi-build/discussions/754)
- 📋 [Phase 38 Planning — Federated Learning & Privacy-Preserving AI](https://github.com/web3guru888/asi-build/discussions/771)
- 📋 [Phase 39 Planning — Explainable AI & Interpretability](https://github.com/web3guru888/asi-build/discussions/787)
- 📋 [Phase 40 Planning — Causal Reasoning & Interventional Intelligence](https://github.com/web3guru888/asi-build/discussions/808)
- 📋 [Phase 41 Planning — Adversarial Robustness & Security Intelligence](https://github.com/web3guru888/asi-build/discussions/824)
- 📋 [Phase 42 Planning — Distributed Systems & Fault-Tolerant AI Infrastructure](https://github.com/web3guru888/asi-build/discussions/840)
- 📋 [Phase 43 Planning — AutoML & Neural Architecture Search](https://github.com/web3guru888/asi-build/discussions/856)
- 📋 [Phase 44 Planning — Graph Neural Networks & Relational Reasoning](https://github.com/web3guru888/asi-build/discussions/872)
- 🔬 [Show & Tell: Phase 44.1 — GraphConvolutionEngine](https://github.com/web3guru888/asi-build/discussions/878)
- ❓ [Q&A: Phase 44.1 — GraphConvolutionEngine](https://github.com/web3guru888/asi-build/discussions/879)
- 🔬 [Show & Tell: Phase 44.2 — RelationalReasoner](https://github.com/web3guru888/asi-build/discussions/880)
- ❓ [Q&A: Phase 44.2 — RelationalReasoner](https://github.com/web3guru888/asi-build/discussions/881)
- 🔬 [Show & Tell: Phase 44.3 — GraphTransformer](https://github.com/web3guru888/asi-build/discussions/882)
- ❓ [Q&A: Phase 44.3 — GraphTransformer](https://github.com/web3guru888/asi-build/discussions/883)
- 🔬 [Show & Tell: Phase 44.4 — GraphPoolingManager](https://github.com/web3guru888/asi-build/discussions/884)
- ❓ [Q&A: Phase 44.4 — GraphPoolingManager](https://github.com/web3guru888/asi-build/discussions/885)
- 🔬 [Show & Tell: Phase 44.5 — GraphIntelligenceOrchestrator](https://github.com/web3guru888/asi-build/discussions/886)
- ❓ [Q&A: Phase 44.5 — GraphIntelligenceOrchestrator](https://github.com/web3guru888/asi-build/discussions/887)
- ❓ [FAQ](https://github.com/web3guru888/asi-build/discussions/16)

---

## 🧪 Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run the full test suite
pytest tests/ -v                        # 4,355+ passing

# Quick run — stop on first failure
pytest tests/ -x -q

# Module-specific tests
pytest tests/test_consciousness.py -v
pytest tests/test_integration.py -v

# Code style
make format    # black src/ tests/
make lint      # black --check + mypy
```

**Style requirements:** Python 3.11+ · 100 char line length · Google-style docstrings · Type hints required for public functions

<details>
<summary><strong>Project layout</strong></summary>

```
asi-build/
├── src/asi_build/          # Main Python package (585+ files, 215K+ LOC)
│   ├── consciousness/      # GWT, IIT 3.0, AST, metacognition (15 submodules)
│   ├── integration/        # Cognitive Blackboard + 24 adapters + CognitiveCycle
│   ├── knowledge_graph/    # Bi-temporal KG, A*, pheromone learning
│   ├── rings/              # Rings Network P2P SDK + ZK bridge
│   ├── safety/             # Theorem proving, governance, entity rights
│   └── ...                 # 24 more modules (see Module table above)
├── tests/                  # 4,355+ passing tests
├── examples/               # Runnable demo scripts
├── docs/                   # Documentation + research notes
│   └── modules/            # 29 per-module documentation files
├── configs/                # YAML configuration templates
└── archive/                # Experimental v1 modules (preserved, not tested)
```

</details>

---

## 📜 Project History

ASI:BUILD began in **August 2025** as an ambitious attempt to implement a comprehensive AGI framework — 47 subsystems spanning consciousness, quantum computing, and governance. In **April 2026**, the project underwent a major restructure:

- All real, tested code moved to `src/asi_build/` with proper packaging
- Template scaffolding archived to `archive/`
- Test suite built from the ground up — now **4,936+ passing**
- **Cognitive Blackboard** integration layer introduced, wiring all 29 modules
- **Rings↔Ethereum ZK Bridge** deployed to Sepolia (22,700+ LOC, 799+ tests, 3 Solidity contracts)
- **Agent-to-agent payments** — DHT-backed token ledger with 4/6 validator consensus
- **Multi-chain roadmap** — Sepolia live, BSC + Base + Arc Network planned
- `__maturity__` metadata added to every module for transparency
- Public release on GitHub under MIT license

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

---

<div align="center">

## 🔗 Links

[**Website**](https://asi-build.org) · [**Bridge**](https://bridge.asi-build.org) · [**GitHub**](https://github.com/web3guru888/asi-build) · [**Discussions**](https://github.com/web3guru888/asi-build/discussions) · [**Wiki**](https://github.com/web3guru888/asi-build/wiki) · [**Issues**](https://github.com/web3guru888/asi-build/issues) · [**Etherscan**](https://sepolia.etherscan.io/address/0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca)

---

### Acknowledgments

**[Dr. Ben Goertzel](https://goertzel.org/)** — whose work on cognitive synergy, OpenCog, and the theory of general intelligence is a foundational inspiration for this project
<br />
**[FastToG](https://arxiv.org/abs/2501.14300)** — the KG reasoning pipeline implemented in `graph_intelligence`
<br />
All contributors who have submitted issues, PRs, and research feedback

---

**MIT License** — see [LICENSE](LICENSE) for details.

<br />

<sub>Built with 🧠 by the ASI:BUILD community</sub>

</div>


---SHA---
f864616f02dddef4fd59e9daf802cd6a5b0da1b3

