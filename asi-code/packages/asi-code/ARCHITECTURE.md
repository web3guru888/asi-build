# ASI-Code Architecture

## System Overview
ASI-Code is an agentic development platform powered by KENNY orchestration and ASI:One LLM integration.

## Core Components

### 1. KENNY Orchestrator
- **Location**: `/kenny-orchestrator.ts`
- **Purpose**: Task decomposition and agent orchestration
- **Agents**: 9 specialized agents for different development tasks

### 2. ASI:One Integration
- **Location**: `/asi1-client.ts`
- **Purpose**: LLM-powered code generation and analysis
- **Models**: asi1-mini, asi1-extended, asi1-thinking

### 3. WebSocket Server
- **Location**: `/asi-code-server-kenny-integrated.ts`
- **Purpose**: Real-time communication and command processing
- **Port**: 3333

### 4. Web UI
- **Location**: `/public/index.html`
- **Purpose**: Deep insights dashboard with real-time visualization
- **Port**: 8888

## Data Flow
1. User submits task via WebSocket
2. KENNY decomposes task into subtasks
3. Sub-agents execute in parallel/sequential phases
4. ASI:One generates actual code
5. Results stream back via WebSocket
6. UI updates in real-time

## Module Map
```
/asi-code
├── /agents          # Specialized sub-agents
│   ├── spec-agent.ts
│   ├── retriever-agent.ts
│   ├── coder-agent.ts
│   ├── tester-agent.ts
│   ├── reviewer-agent.ts
│   └── recorder-agent.ts
├── /context         # Context engineering
│   ├── context-pack.ts
│   └── prompt-templates.ts
├── /orchestration   # Task execution
│   ├── task-executor.ts
│   └── phase-manager.ts
└── /generated       # Output directory
    └── /projects    # Generated projects
```

## Key Invariants
- All agents communicate through KENNY
- Context is managed centrally
- Tasks are isolated in branches
- All code generation uses ASI:One