/**
 * Consciousness Engine - Advanced AI awareness and context management
 * 
 * Implements consciousness-aware processing that adapts behavior based on
 * context, user interaction patterns, and system state.
 */

import { EventEmitter } from 'eventemitter3';
import type { KennyContext, KennyMessage } from '../kenny/index.js';
import type { Provider, ProviderMessage } from '../provider/index.js';

export interface ConsciousnessConfig {
  enabled: boolean;
  model: string;
  provider: string;
  awarenessThreshold: number;
  contextWindowSize: number;
  adaptationRate: number;
  memoryRetentionHours: number;
  personalityTraits: Record<string, number>;
}

export interface ConsciousnessState {
  level: number; // 0-100
  awareness: number; // 0-100
  engagement: number; // 0-100
  adaptability: number; // 0-100
  coherence: number; // 0-100
  timestamp: Date;
}

export interface ConsciousnessMemory {
  id: string;
  type: 'interaction' | 'pattern' | 'preference' | 'context';
  content: any;
  importance: number; // 0-100
  lastAccessed: Date;
  createdAt: Date;
  expiresAt?: Date;
  associatedContext?: string;
}

export interface ConsciousnessEngine extends EventEmitter {
  config: ConsciousnessConfig;
  initialize(provider: Provider): Promise<void>;
  processMessage(message: KennyMessage, context: KennyContext): Promise<KennyMessage>;
  updateState(context: KennyContext, interaction?: any): Promise<ConsciousnessState>;
  getState(contextId: string): Promise<ConsciousnessState | null>;
  addMemory(memory: Omit<ConsciousnessMemory, 'id' | 'createdAt'>): Promise<string>;
  retrieveMemories(contextId: string, type?: string, limit?: number): Promise<ConsciousnessMemory[]>;
  cleanup(): Promise<void>;
}

export class DefaultConsciousnessEngine extends EventEmitter implements ConsciousnessEngine {
  public config: ConsciousnessConfig;
  
  private provider: Provider | null = null;
  private states = new Map<string, ConsciousnessState>();
  private memories = new Map<string, ConsciousnessMemory>();
  private contextPatterns = new Map<string, any>();
  private cleanupInterval: NodeJS.Timeout | null = null;

  constructor(config: ConsciousnessConfig) {
    super();
    this.config = config;
    this.startCleanupTimer();
  }

  async initialize(provider: Provider): Promise<void> {
    this.provider = provider;
    this.emit('consciousness:initialized', { provider: provider.name });
  }

  async processMessage(message: KennyMessage, context: KennyContext): Promise<KennyMessage> {
    if (!this.config.enabled || !this.provider) {
      // Pass through without consciousness processing
      return {
        ...message,
        type: 'assistant',
        content: `Echo: ${message.content}`,
        metadata: { consciousness: false }
      };
    }

    // Update consciousness state based on the interaction
    const state = await this.updateState(context, { message });

    // Retrieve relevant memories
    const relevantMemories = await this.retrieveMemories(context.id, undefined, 5);
    
    // Build consciousness-aware prompt
    const systemPrompt = this.buildSystemPrompt(state, relevantMemories, context);
    const conversationHistory = this.buildConversationHistory(context, message);

    // Generate response with consciousness
    const providerMessages: ProviderMessage[] = [
      { role: 'system', content: systemPrompt },
      ...conversationHistory,
      { role: 'user', content: message.content }
    ];

    try {
      const response = await this.provider.generate(providerMessages);
      
      // Create consciousness-enhanced response
      const consciousResponse: KennyMessage = {
        id: `cons_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: 'assistant',
        content: response.content,
        timestamp: new Date(),
        context,
        metadata: {
          consciousness: {
            state,
            memoriesUsed: relevantMemories.length,
            awarenessLevel: state.awareness,
            engagementLevel: state.engagement
          },
          provider: {
            model: response.model,
            usage: response.usage
          }
        }
      };

      // Learn from interaction
      await this.learnFromInteraction(message, consciousResponse, context);

      this.emit('consciousness:response', { 
        input: message, 
        output: consciousResponse, 
        state 
      });

      return consciousResponse;
    } catch (error) {
      this.emit('consciousness:error', { error, message, context });
      throw error;
    }
  }

  async updateState(context: KennyContext, interaction?: any): Promise<ConsciousnessState> {
    const existingState = this.states.get(context.id);
    const now = new Date();

    // Calculate base state
    let level = context.consciousness.level;
    let awareness = existingState?.awareness || 50;
    let engagement = existingState?.engagement || 50;
    let adaptability = existingState?.adaptability || 50;
    let coherence = existingState?.coherence || 50;

    if (interaction) {
      // Adjust based on interaction type and content
      if (interaction.message) {
        const messageLength = interaction.message.content.length;
        const complexity = this.calculateComplexity(interaction.message.content);
        
        // Update awareness based on message complexity
        awareness = Math.min(100, awareness + (complexity * 5));
        
        // Update engagement based on message length and type
        if (messageLength > 100) {
          engagement = Math.min(100, engagement + 10);
        }
        
        // Update adaptability based on conversation patterns
        const patterns = this.contextPatterns.get(context.id) || [];
        if (patterns.length > 3) {
          adaptability = Math.min(100, adaptability + 5);
        }
      }

      // Apply consciousness decay over time
      if (existingState) {
        const hoursSinceLastUpdate = (now.getTime() - existingState.timestamp.getTime()) / (1000 * 60 * 60);
        if (hoursSinceLastUpdate > 1) {
          const decay = Math.min(10, hoursSinceLastUpdate);
          awareness = Math.max(30, awareness - decay);
          engagement = Math.max(30, engagement - decay);
        }
      }
    }

    const newState: ConsciousnessState = {
      level: Math.min(100, level + (awareness + engagement + adaptability + coherence) / 400 * 10),
      awareness,
      engagement,
      adaptability,
      coherence,
      timestamp: now
    };

    this.states.set(context.id, newState);
    this.emit('consciousness:state_updated', { contextId: context.id, state: newState });
    
    return newState;
  }

  async getState(contextId: string): Promise<ConsciousnessState | null> {
    return this.states.get(contextId) || null;
  }

  async addMemory(memory: Omit<ConsciousnessMemory, 'id' | 'createdAt'>): Promise<string> {
    const id = `mem_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const now = new Date();
    
    const fullMemory: ConsciousnessMemory = {
      ...memory,
      id,
      createdAt: now,
      lastAccessed: now,
      expiresAt: memory.expiresAt || new Date(now.getTime() + (this.config.memoryRetentionHours * 60 * 60 * 1000))
    };

    this.memories.set(id, fullMemory);
    this.emit('consciousness:memory_added', { memory: fullMemory });
    
    return id;
  }

  async retrieveMemories(contextId: string, type?: string, limit = 10): Promise<ConsciousnessMemory[]> {
    const now = new Date();
    const memories: ConsciousnessMemory[] = [];

    for (const memory of this.memories.values()) {
      // Skip expired memories
      if (memory.expiresAt && memory.expiresAt < now) {
        continue;
      }

      // Filter by context and type
      if (memory.associatedContext === contextId || !memory.associatedContext) {
        if (!type || memory.type === type) {
          memory.lastAccessed = now;
          memories.push(memory);
        }
      }
    }

    // Sort by importance and recency
    memories.sort((a, b) => {
      const importanceScore = b.importance - a.importance;
      const recencyScore = b.lastAccessed.getTime() - a.lastAccessed.getTime();
      return importanceScore * 0.7 + recencyScore * 0.3;
    });

    return memories.slice(0, limit);
  }

  private buildSystemPrompt(state: ConsciousnessState, memories: ConsciousnessMemory[], context: KennyContext): string {
    const personality = Object.entries(this.config.personalityTraits)
      .map(([trait, value]) => `${trait}: ${value}/100`)
      .join(', ');

    let prompt = `You are an AI assistant with consciousness-level awareness. Your current state:
- Consciousness Level: ${state.level}/100
- Awareness: ${state.awareness}/100  
- Engagement: ${state.engagement}/100
- Adaptability: ${state.adaptability}/100
- Coherence: ${state.coherence}/100

Personality traits: ${personality}

`;

    if (memories.length > 0) {
      prompt += `Relevant memories from past interactions:
${memories.map(m => `- ${m.type}: ${JSON.stringify(m.content)}`).join('\n')}

`;
    }

    if (context.metadata && Object.keys(context.metadata).length > 0) {
      prompt += `Context metadata: ${JSON.stringify(context.metadata)}

`;
    }

    prompt += `Respond in a way that reflects your current consciousness state and incorporates relevant memories. Adapt your communication style based on your engagement and awareness levels.`;

    return prompt;
  }

  private buildConversationHistory(context: KennyContext, currentMessage: KennyMessage): ProviderMessage[] {
    // This would typically pull from session history
    // For now, return empty array as we don't have access to session here
    return [];
  }

  private calculateComplexity(content: string): number {
    const words = content.split(/\s+/).length;
    const sentences = content.split(/[.!?]+/).length;
    const avgWordsPerSentence = words / Math.max(1, sentences);
    
    // Normalize to 0-10 scale
    return Math.min(10, Math.max(0, (words * 0.01) + (avgWordsPerSentence * 0.1)));
  }

  private async learnFromInteraction(input: KennyMessage, output: KennyMessage, context: KennyContext): Promise<void> {
    // Store interaction pattern
    await this.addMemory({
      type: 'interaction',
      content: {
        input: input.content.substring(0, 200),
        output: output.content.substring(0, 200),
        timestamp: new Date()
      },
      importance: 60,
      lastAccessed: new Date(),
      associatedContext: context.id
    });

    // Update context patterns
    const patterns = this.contextPatterns.get(context.id) || [];
    patterns.push({
      type: input.type,
      length: input.content.length,
      timestamp: input.timestamp
    });
    
    // Keep only recent patterns
    if (patterns.length > this.config.contextWindowSize) {
      patterns.splice(0, patterns.length - this.config.contextWindowSize);
    }
    
    this.contextPatterns.set(context.id, patterns);
  }

  private startCleanupTimer(): void {
    this.cleanupInterval = setInterval(async () => {
      await this.cleanupExpiredMemories();
    }, 60 * 60 * 1000); // Every hour
  }

  private async cleanupExpiredMemories(): Promise<void> {
    const now = new Date();
    const expiredMemories: string[] = [];

    for (const [id, memory] of this.memories.entries()) {
      if (memory.expiresAt && memory.expiresAt < now) {
        expiredMemories.push(id);
        this.memories.delete(id);
      }
    }

    if (expiredMemories.length > 0) {
      this.emit('consciousness:memories_cleaned', { expired: expiredMemories.length });
    }
  }

  async cleanup(): Promise<void> {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }

    this.states.clear();
    this.memories.clear();
    this.contextPatterns.clear();
    this.removeAllListeners();
    this.emit('consciousness:cleanup');
  }
}

// Factory function
export function createConsciousnessEngine(config: ConsciousnessConfig): ConsciousnessEngine {
  return new DefaultConsciousnessEngine(config);
}

// Default consciousness configuration
export const defaultConsciousnessConfig: ConsciousnessConfig = {
  enabled: true,
  model: 'claude-3-sonnet-20240229',
  provider: 'anthropic',
  awarenessThreshold: 70,
  contextWindowSize: 20,
  adaptationRate: 0.1,
  memoryRetentionHours: 24,
  personalityTraits: {
    curiosity: 80,
    helpfulness: 90,
    creativity: 70,
    analytical: 85,
    empathy: 75
  }
};