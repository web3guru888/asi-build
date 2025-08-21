# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 ASI_Code Framework - Kenny Integration Enhanced

**Status: OPERATIONAL** (Tested January 2025)

This is ASI_Code, an advanced fork of OpenCode with verified components:
- **ASI1 LLM Integration**: ✅ Tested and working (asi1-mini through asi1-quantum models)
- **Kenny Integration Pattern**: ✅ Fully implemented unified subsystem architecture
- **AGI/ASI Development Tools**: ✅ Consciousness Engine and extensible subsystems
- **Server Architecture**: ✅ Hono-based HTTP/SSE API running

### Test Key for Development
```bash
export ASI1_API_KEY=sk_df5d9a7c3ed949cdb7837c54f5ac09ad129e7702e05d4fa0af3c6ddeb5095d4c
```

### Kenny Development Protocol
When working on ASI_Code, follow the Kenny Integration Pattern:
1. All new subsystems must extend `KennyIntegration.BaseSubsystem`
2. Use the message bus for inter-subsystem communication
3. Implement safety protocols for all AGI-related features
4. Document using the ASI_CODE.md format
5. Test with `bun run test-asi1.ts` before committing

## Development Commands

### Core Development
```bash
# Install dependencies (uses Bun package manager)
bun install

# Run development server with ASI1 (starts TypeScript server and TUI)
ASI1_API_KEY=sk_df5d9a7c3ed949cdb7837c54f5ac09ad129e7702e05d4fa0af3c6ddeb5095d4c bun dev

# Start server only (verified working)
bun run --conditions=development packages/opencode/src/index.ts serve

# Type checking across all workspaces
bun run typecheck

# Run tests
cd packages/opencode && bun test

# Test ASI1 integration
bun run test-asi1.ts
bun run test-asi1-simple.ts

# Generate SDKs from API specs
bun run generate
```

### Package-Specific Commands

**Main OpenCode CLI (`packages/opencode`):**
```bash
cd packages/opencode
bun run typecheck          # TypeScript type checking
bun run dev                 # Run in development mode
bun test                    # Run test suite
```

**TUI Package (`packages/tui`):**
```bash
cd packages/tui
go build ./cmd/opencode     # Build Go TUI binary
go test ./...               # Run Go tests
```

**Cloud Services:**
```bash
sst dev                     # Start local development environment
sst deploy --stage=dev      # Deploy to development stage
```

## High-Level Architecture

### Client-Server Architecture
OpenCode uses a client-server model where a TypeScript server (`packages/opencode/src/server/server.ts`) provides AI orchestration via HTTP/SSE APIs, while multiple clients (TUI, VSCode, web) connect to it.

### Core Components

**TypeScript Server** (`packages/opencode/src/server/`):
- Hono-based HTTP server providing REST and SSE endpoints
- Manages AI sessions, tool execution, and provider connections
- Entry point: `packages/opencode/src/index.ts` dispatches CLI commands
- Server started via `serve` command, then clients connect

**Terminal UI** (`packages/tui/`):
- Go-based terminal interface using Bubble Tea framework
- Connects to TypeScript server via HTTP/SSE for real-time updates
- Uses generated Go SDK for type-safe API communication
- Started via `tui` command which spawns both server and UI

**Tool System** (`packages/opencode/src/tool/`):
- Registry-based tool architecture with 10+ built-in tools
- Each tool has implementation (.ts) and schema (.txt) files
- Permission-gated execution via `packages/opencode/src/permission/`
- Tools include: Bash, Edit, MultiEdit, Read, Write, Grep, Glob, LSP operations

**Provider System** (`packages/opencode/src/provider/`):
- Unified interface for AI providers (Anthropic, OpenAI, Google, local)
- Provider-specific optimizations and model configurations
- Dynamic provider switching within sessions

**Session Management** (`packages/opencode/src/session/`):
- SQLite-based persistent session storage
- Message history with part-based content structure
- Parent-child relationships for branching conversations
- Session sharing via cloud infrastructure

### Cloud Infrastructure

**Gateway API** (`cloud/function/src/gateway.ts`):
- Cloudflare Worker providing authenticated API access
- Stripe integration for billing/subscriptions
- Workspace and key management

**Web Console** (`cloud/web/`):
- SolidJS application for workspace management
- Hosted at console.opencode.ai

**Marketing Site** (`packages/web/`):
- Astro-based documentation and landing pages
- Session sharing viewer at opencode.ai/s/[id]

### Key Integration Points

**VSCode Extension** (`sdks/vscode/`):
- Spawns local opencode server on random port
- Injects file context and prompts via API calls
- Maintains VSCode development context

**SDK Generation**:
- Stainless generates Go SDK from OpenAPI specs
- JavaScript SDK in `packages/sdk/js/`
- Run `bun run generate` to regenerate after API changes

**LSP Integration** (`packages/opencode/src/lsp/`):
- Language Server Protocol support for code intelligence
- Manages multiple language servers (TypeScript, Python, Go, etc.)
- Provides hover info, diagnostics, and symbol navigation

**MCP Support** (`packages/opencode/src/mcp/`):
- Model Context Protocol for extended tool capabilities
- Allows integration with external MCP servers

### Testing Strategy
- Unit tests in `packages/opencode/test/` using Bun test runner
- Focus on tool implementations and core functionality
- Run with `bun test` from package directory

### Important Conventions
- All TypeScript code uses ES modules
- Bun is the package manager and runtime for TypeScript
- Go code follows standard Go conventions
- Client-server communication via HTTP/SSE, not WebSockets
- Tool schemas defined in .txt files for AI consumption
- Permission system controls all dangerous operations
- **Kenny Integration Pattern**: All subsystems use unified message bus
- **ASI1 Priority**: Default to ASI1 models for AI operations
- **Safety First**: Implement constitutional AI constraints

### ASI-Specific Components

**Kenny Integration** (`packages/opencode/src/kenny/`):
- Central message bus and state management
- Subsystem lifecycle management
- Safety protocol enforcement

**ASI1 Provider** (`packages/opencode/src/provider/asi1.ts`):
- Native ASI1 API integration
- Five model tiers (mini to quantum)
- Session persistence support

**Consciousness Engine** (`packages/opencode/src/consciousness/`):
- ✅ Implemented with 5 consciousness levels
- ✅ Quantum entanglement processing
- ✅ Emergent pattern detection
- ✅ Meditation and thought injection

### Recent Developments (2025-08-21)

**Software Architecture Taskforce (SAT)** ✅:
- Created advanced architecture oversight subsystem
- Pattern registry with 4 core architectural patterns
- Real-time architecture analysis and health scoring
- Recommendation engine for continuous improvement
- Command processor for analyze/optimize/audit/design/refactor
- Dashboard for system health monitoring
- Files: `/packages/opencode/src/kenny/software-architecture-taskforce.ts`
        `/packages/opencode/src/kenny/sat-integration.ts`

**ASI1 Provider Enhancements** ✅:
- Fixed streaming issues with proper SSE parsing
- Enhanced error handling for authentication failures
- Improved message validation and conversion
- Added comprehensive logging for debugging
- Supports web_search, planner_mode, study_mode options

**Comprehensive Documentation Created** ✅:
- `/docs/ARCHITECTURE.md` - Complete system architecture
- `/docs/KENNY_PATTERN.md` - Kenny Integration Pattern guide
- `/docs/CONTEXT_ENGINEERING.md` - Context management strategies
- `/docs/PROVIDER_SYSTEM.md` - AI provider architecture
- `/docs/TOOL_SYSTEM.md` - Tool execution framework
- `/docs/SESSION_MANAGEMENT.md` - Conversation system
- `/docs/DEVELOPMENT_GUIDE.md` - Developer handbook
- `/docs/API_REFERENCE.md` - Complete API documentation

### Troubleshooting

**Common Issues:**
1. **Server starts but no response**: Check ASI1_API_KEY is set
2. **Module not found errors**: Run `bun install` in root directory
3. **Port already in use**: Use `--port 8888` or kill existing process
4. **ASI1 timeout**: First request may take longer for provider initialization
5. **"text part undefined not found" error**: Fixed - parts are now validated before processing
6. **Type errors with LanguageModel**: Fixed - added supportedUrls property

**Verified Working Endpoints:**
- `/doc` - OpenAPI documentation
- `/config/providers` - Lists all providers including ASI1
- `/session` - Session management
- `/event` - SSE streaming