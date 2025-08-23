/**
 * Kenny Integration Pattern (KIP) - Core implementation
 *
 * The Kenny Integration Pattern provides a standardized approach for integrating
 * AI capabilities into software systems through a consciousness-aware architecture.
 */

import { EventEmitter } from 'eventemitter3';
import type { ASICodeConfig } from '../config/config-types.js';

export interface KennyContext {
  id: string;
  sessionId: string;
  userId?: string;
  metadata: Record<string, any>;
  consciousness: {
    level: number;
    state: 'active' | 'passive' | 'dormant';
    lastActivity: Date;
  };
}

export interface KennyMessage {
  id: string;
  type: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: Date;
  context: KennyContext;
  metadata?: Record<string, any>;
}

export interface KennyIntegrationPattern extends EventEmitter {
  initialize(config: ASICodeConfig): Promise<void>;
  process(message: KennyMessage): Promise<KennyMessage>;
  createContext(sessionId: string, userId?: string): KennyContext;
  updateContext(
    contextId: string,
    updates: Partial<KennyContext>
  ): Promise<void>;
  getContext(contextId: string): Promise<KennyContext | null>;
  cleanup(): Promise<void>;
}

export class DefaultKennyIntegration
  extends EventEmitter
  implements KennyIntegrationPattern
{
  private config: ASICodeConfig | null = null;
  private readonly contexts = new Map<string, KennyContext>();

  async initialize(config: ASICodeConfig): Promise<void> {
    this.config = config;
    this.emit('initialized', { config });
  }

  async process(message: KennyMessage): Promise<KennyMessage> {
    if (!this.config) {
      throw new Error('Kenny Integration Pattern not initialized');
    }

    this.emit('message:received', message);

    // Update consciousness state
    const context = await this.getContext(message.context.id);
    if (context) {
      context.consciousness.lastActivity = new Date();
      context.consciousness.state = 'active';
      await this.updateContext(message.context.id, context);
    }

    // Process message through consciousness engine
    const response: KennyMessage = {
      id: `resp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type: 'assistant',
      content: `Processed: ${message.content}`,
      timestamp: new Date(),
      context: message.context,
      metadata: {
        processed: true,
        originalMessageId: message.id,
      },
    };

    this.emit('message:processed', { original: message, response });
    return response;
  }

  createContext(sessionId: string, userId?: string): KennyContext {
    const context: KennyContext = {
      id: `ctx_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      sessionId,
      userId,
      metadata: {},
      consciousness: {
        level: 1,
        state: 'active',
        lastActivity: new Date(),
      },
    };

    this.contexts.set(context.id, context);
    this.emit('context:created', context);
    return context;
  }

  async updateContext(
    contextId: string,
    updates: Partial<KennyContext>
  ): Promise<void> {
    const context = this.contexts.get(contextId);
    if (!context) {
      throw new Error(`Context not found: ${contextId}`);
    }

    Object.assign(context, updates);
    this.contexts.set(contextId, context);
    this.emit('context:updated', { contextId, updates, context });
  }

  async getContext(contextId: string): Promise<KennyContext | null> {
    return this.contexts.get(contextId) || null;
  }

  async cleanup(): Promise<void> {
    this.contexts.clear();
    this.removeAllListeners();
    this.emit('cleaned');
  }
}

// Factory function
export function createKennyIntegration(): KennyIntegrationPattern {
  return new DefaultKennyIntegration();
}

// Export types

// Re-export all core components
export * from './integration.js';
export * from './message-bus.js';
export * from './state-manager.js';
export * from './base-subsystem.js';
