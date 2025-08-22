# AgentRegistry and LoadBalancer Implementations

## Overview

This document describes the implementation of two critical components for the ASI-Code orchestration system:

1. **AgentRegistry** - Manages agent registration, discovery, and health monitoring
2. **LoadBalancer** - Handles intelligent task distribution and load balancing

## AgentRegistry Implementation

### Location
`src/orchestration/agent-registry.ts`

### Key Features

#### Agent Management
- **Registration**: Thread-safe agent registration with proper indexing
- **Discovery**: Find agents by capability, type, availability, or specific criteria
- **Health Monitoring**: Automatic health checks with configurable intervals
- **Statistics**: Comprehensive agent statistics and metrics

#### Thread Safety
- Uses locks for concurrent operations
- Prevents race conditions during registration/unregistration
- Safe for multi-threaded environments

#### Health Monitoring
- Configurable health check intervals (default: 30 seconds)
- Automatic detection of unhealthy agents
- Recovery detection and notification
- Performance-based health evaluation

#### Indexing
- Capability-based indexing for fast lookups
- Type-based indexing for agent categorization
- Status-based indexing for availability queries
- Automatic index maintenance

### API Methods

```typescript
interface AgentRegistry {
  // Core methods
  register(agent: Agent): void
  unregister(agentId: string): void
  get(agentId: string): Agent | undefined
  
  // Discovery methods
  findByCapability(capability: string): Agent[]
  findByType(type: AgentType): Agent[]
  findAvailable(): Agent[]
  getAll(): Agent[]
  
  // Advanced methods
  findBestAgent(task: Task): Agent | undefined
  getAgentHealth(agentId: string): 'healthy' | 'unhealthy' | 'unknown' | undefined
  getStats(): RegistryStats
}
```

### Events
- `agent:registered` - When agent is registered
- `agent:unregistered` - When agent is unregistered
- `agent:health_failed` - When agent health check fails
- `agent:health_recovered` - When agent health recovers
- `agent:status_changed` - When agent status changes

## LoadBalancer Implementation

### Location
`src/orchestration/load-balancer.ts`

### Key Features

#### Multiple Balancing Strategies
- **Round Robin**: Simple round-robin distribution
- **Least Loaded**: Assigns to agent with lowest load
- **Capability Based**: Matches based on capability requirements
- **Performance Based**: Considers agent performance metrics
- **Resource Aware**: Considers resource availability
- **Hybrid**: Combines multiple factors with configurable weights

#### Smart Task Matching
- Analyzes task requirements vs agent capabilities
- Considers resource constraints
- Factors in agent performance history
- Supports preferred agent assignments

#### Load Calculation
- Multi-factor load assessment
- Configurable load factors (task count, resource utilization, response time, error rate)
- Performance-based load adjustments
- Real-time load monitoring

#### Rebalancing
- Automatic load imbalance detection
- Intelligent task redistribution
- Configurable rebalancing thresholds
- Prevents thrashing with minimum intervals

### API Methods

```typescript
interface LoadBalancer {
  // Core methods
  selectAgent(task: Task, agents: Agent[]): Agent | undefined
  getLoad(agent: Agent): number
  rebalance(agents: Agent[], tasks: Task[]): Map<string, string[]>
  
  // Configuration
  updateConfig(config: Partial<LoadBalancerConfig>): void
  
  // Monitoring
  getStats(): LoadBalancerStats
  trackPerformance(agent: Agent): void
  getPerformanceHistory(agentId: string): PerformanceHistory
}
```

### Configuration Options

```typescript
interface LoadBalancerConfig {
  strategy: LoadBalancingStrategy
  weights?: {
    performance?: number
    capacity?: number
    capability?: number
    resource?: number
  }
  loadFactors?: {
    taskCount?: number
    resourceUtilization?: number
    responseTime?: number
    errorRate?: number
  }
  rebalanceThresholds?: {
    maxLoadImbalance?: number
    minIdleAgents?: number
    maxQueueDepth?: number
  }
}
```

### Events
- `agent:selected` - When agent is selected for task
- `rebalance:completed` - When rebalancing is completed
- `config:updated` - When configuration is updated

## Integration Examples

### Basic Usage

```typescript
import { AgentRegistry, LoadBalancer } from './orchestration';

// Create components
const registry = new AgentRegistry();
const loadBalancer = new LoadBalancer({
  strategy: 'hybrid',
  weights: {
    performance: 0.3,
    capacity: 0.25,
    capability: 0.25,
    resource: 0.2
  }
});

// Register agents
agents.forEach(agent => registry.register(agent));

// Select agent for task
const availableAgents = registry.findAvailable();
const selectedAgent = loadBalancer.selectAgent(task, availableAgents);

// Rebalance if needed
const rebalanceMap = loadBalancer.rebalance(
  registry.getAll(), 
  pendingTasks
);
```

### Advanced Usage with Monitoring

```typescript
// Set up event listeners
registry.on('agent:health_failed', (agentId, failures) => {
  console.log(`Agent ${agentId} health failed (${failures} consecutive)`);
  // Handle unhealthy agent
});

loadBalancer.on('agent:selected', (selection) => {
  console.log(`Agent ${selection.agent} selected for task ${selection.task}`);
  console.log(`Score: ${selection.score}, Breakdown:`, selection.breakdown);
});

// Monitor performance
setInterval(() => {
  registry.getAll().forEach(agent => {
    loadBalancer.trackPerformance(agent);
  });
}, 60000); // Every minute

// Get statistics
const registryStats = registry.getStats();
const loadBalancerStats = loadBalancer.getStats();
```

## Performance Characteristics

### AgentRegistry
- **Registration**: O(1) average case with indexing
- **Lookup by ID**: O(1)
- **Lookup by capability**: O(k) where k is number of agents with capability
- **Health checks**: Parallel execution for all agents
- **Memory**: O(n) where n is number of agents

### LoadBalancer
- **Agent selection**: O(n log n) for sorting-based strategies
- **Load calculation**: O(1) per agent
- **Rebalancing**: O(n*m) where n is agents and m is tasks
- **Memory**: O(n) for agent history tracking

## Thread Safety

Both implementations are designed to be thread-safe:

- **AgentRegistry**: Uses locks for critical sections
- **LoadBalancer**: Immutable operations on data structures
- **Event emission**: Safe concurrent event handling
- **Statistics**: Atomic reads of current state

## Testing

Test files are provided:
- `test-implementations.ts` - Comprehensive integration tests
- `test-simple.ts` - Basic functionality tests  
- `test-exports.ts` - Import/export verification

Run tests with:
```bash
npx tsc --noEmit --skipLibCheck src/orchestration/agent-registry.ts src/orchestration/load-balancer.ts
```

## Integration with Existing System

The implementations integrate seamlessly with the existing ASI-Code orchestration system:

- **Types**: Fully compatible with `types.ts` interfaces
- **Events**: Uses EventEmitter3 for consistent event handling
- **Logging**: Can integrate with the logging system
- **Metrics**: Provides comprehensive metrics for monitoring
- **Configuration**: Flexible configuration system

## Future Enhancements

Potential improvements:
1. **Persistent storage**: Save agent registry state
2. **Distributed mode**: Support for multi-node deployments
3. **Machine learning**: AI-based load balancing optimization
4. **Custom strategies**: Plugin system for custom load balancing
5. **Advanced health checks**: Custom health check implementations
6. **Metrics export**: Integration with monitoring systems like Prometheus

## Conclusion

Both AgentRegistry and LoadBalancer provide robust, production-ready implementations that form the core of the ASI-Code agent orchestration system. They are designed for:

- **Scalability**: Handle hundreds of agents efficiently
- **Reliability**: Comprehensive error handling and recovery
- **Flexibility**: Configurable behavior for different use cases
- **Observability**: Extensive metrics and event emission
- **Integration**: Seamless integration with existing codebase