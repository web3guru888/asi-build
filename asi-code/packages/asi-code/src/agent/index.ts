/**
 * Agent Configuration System - Agent definitions and behavior management
 *
 * Manages AI agent configurations, personalities, and specialized behaviors
 * for different use cases and domains.
 */

import { EventEmitter } from 'eventemitter3';

export interface AgentConfig {
  id: string;
  name: string;
  description: string;
  personality: Record<string, number>;
  capabilities: string[];
  tools: string[];
  provider: string;
  model: string;
  systemPrompt: string;
  constraints: string[];
  metadata: Record<string, any>;
}

export interface Agent extends EventEmitter {
  config: AgentConfig;
  initialize(): Promise<void>;
  execute(input: string, context?: any): Promise<string>;
  updateConfig(updates: Partial<AgentConfig>): Promise<void>;
  cleanup(): Promise<void>;
}

export class DefaultAgent extends EventEmitter implements Agent {
  public config: AgentConfig;

  constructor(config: AgentConfig) {
    super();
    this.config = config;
  }

  async initialize(): Promise<void> {
    this.emit('agent:initialized', { id: this.config.id });
  }

  async execute(input: string, context?: any): Promise<string> {
    // TODO: Implement agent execution logic
    this.emit('agent:executed', { id: this.config.id, input });
    return `Agent ${this.config.name} processed: ${input}`;
  }

  async updateConfig(updates: Partial<AgentConfig>): Promise<void> {
    Object.assign(this.config, updates);
    this.emit('agent:config_updated', { id: this.config.id, updates });
  }

  async cleanup(): Promise<void> {
    this.removeAllListeners();
  }
}

export class AgentManager extends EventEmitter {
  private readonly agents = new Map<string, Agent>();

  async register(config: AgentConfig): Promise<void> {
    const agent = new DefaultAgent(config);
    await agent.initialize();
    this.agents.set(config.id, agent);
    this.emit('agent:registered', { id: config.id });
  }

  get(id: string): Agent | undefined {
    return this.agents.get(id);
  }

  list(): AgentConfig[] {
    return Array.from(this.agents.values()).map(agent => agent.config);
  }

  async unregister(id: string): Promise<void> {
    const agent = this.agents.get(id);
    if (agent) {
      await agent.cleanup();
      this.agents.delete(id);
      this.emit('agent:unregistered', { id });
    }
  }

  async cleanup(): Promise<void> {
    for (const agent of this.agents.values()) {
      await agent.cleanup();
    }
    this.agents.clear();
    this.removeAllListeners();
  }
}

export function createAgentManager(): AgentManager {
  return new AgentManager();
}
