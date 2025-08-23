# System Constraints

## Coding Standards
- TypeScript strict mode enabled
- ESLint configuration enforced
- Prettier formatting required
- No any types without justification
- All async operations properly handled

## Performance Requirements
- Task decomposition < 500ms
- Agent response time < 2s
- WebSocket latency < 100ms
- UI updates < 16ms (60fps)
- Memory usage < 512MB

## Security Rules
- No direct file system access outside /generated
- API keys must use environment variables
- Input sanitization required
- No eval() or dynamic code execution
- WebSocket messages validated

## Agent Constraints
- Agents can only modify assigned files
- Context limited to 8000 tokens
- Parallel execution max 4 agents
- Retry limit 3 attempts
- Timeout 30 seconds per task

## Code Generation Rules
- Generated code must compile/run
- Tests required for all features
- Documentation comments required
- Error handling mandatory
- Type safety enforced

## Compliance
- ASI Alliance coding guidelines
- Open source license compatibility
- No proprietary dependencies
- Accessibility standards (WCAG 2.1)
- Data privacy (no user data storage)