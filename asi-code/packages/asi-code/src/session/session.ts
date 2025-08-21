/**
 * Session Class Implementation
 * 
 * Core session class with message history, context management,
 * and Kenny Integration Pattern support.
 */

import { EventEmitter } from 'eventemitter3';
import type { KennyContext, KennyMessage } from '../kenny/index.js';
import type { SessionConfig, SessionData } from './session-manager.js';

export interface Session extends EventEmitter {
  data: SessionData;
  addMessage(message: KennyMessage): void;
  getMessages(limit?: number): KennyMessage[];
  updateContext(updates: Partial<KennyContext>): void;
  updateMetadata(updates: Record<string, any>): void;
  isExpired(): boolean;
  cleanup(): Promise<void>;
  getMessageById(messageId: string): KennyMessage | null;
  deleteMessage(messageId: string): boolean;
  clearMessages(): void;
  getContextSummary(): string;
  getActivityStats(): SessionActivityStats;
}

export interface SessionActivityStats {
  totalMessages: number;
  userMessages: number;
  assistantMessages: number;
  systemMessages: number;
  toolMessages: number;
  firstMessageAt?: Date;
  lastMessageAt?: Date;
  averageResponseTime?: number;
}

export class DefaultSession extends EventEmitter implements Session {
  public data: SessionData;
  private messageResponseTimes: number[] = [];

  constructor(data: SessionData) {
    super();
    this.data = data;
    
    // Ensure data integrity
    this.validateAndFixData();
  }

  private validateAndFixData(): void {
    // Ensure messages array exists
    if (!Array.isArray(this.data.messages)) {
      this.data.messages = [];
    }

    // Ensure metadata exists
    if (!this.data.metadata || typeof this.data.metadata !== 'object') {
      this.data.metadata = {};
    }

    // Ensure dates are Date objects
    if (!(this.data.createdAt instanceof Date)) {
      this.data.createdAt = new Date(this.data.createdAt);
    }

    if (!(this.data.lastActivity instanceof Date)) {
      this.data.lastActivity = new Date(this.data.lastActivity);
    }

    // Ensure kenny context exists
    if (!this.data.kennyContext) {
      this.data.kennyContext = {
        id: `ctx_${this.data.id}`,
        sessionId: this.data.id,
        userId: this.data.userId,
        metadata: {},
        consciousness: {
          level: 1,
          state: 'active',
          lastActivity: new Date()
        }
      };
    }

    // Ensure consciousness state is valid
    if (!this.data.kennyContext.consciousness) {
      this.data.kennyContext.consciousness = {
        level: 1,
        state: 'active',
        lastActivity: new Date()
      };
    }
  }

  addMessage(message: KennyMessage): void {
    // Validate message
    if (!message.id || !message.content) {
      throw new Error('Message must have id and content');
    }

    // Check for duplicate message IDs
    if (this.data.messages.some(m => m.id === message.id)) {
      throw new Error(`Message with ID ${message.id} already exists`);
    }

    // Add message to history
    this.data.messages.push(message);
    this.data.lastActivity = new Date();

    // Update consciousness activity
    this.data.kennyContext.consciousness.lastActivity = this.data.lastActivity;
    if (message.type === 'user') {
      this.data.kennyContext.consciousness.state = 'active';
    }

    // Calculate response time for assistant messages
    if (message.type === 'assistant') {
      const userMessages = this.data.messages.filter(m => m.type === 'user');
      const lastUserMessage = userMessages[userMessages.length - 1];
      
      if (lastUserMessage) {
        const responseTime = message.timestamp.getTime() - lastUserMessage.timestamp.getTime();
        this.messageResponseTimes.push(responseTime);
        
        // Keep only last 50 response times
        if (this.messageResponseTimes.length > 50) {
          this.messageResponseTimes.shift();
        }
      }
    }

    // Trim messages if exceeded max
    if (this.data.messages.length > this.data.config.maxMessages) {
      const removed = this.data.messages.splice(
        0, 
        this.data.messages.length - this.data.config.maxMessages
      );
      this.emit('messages:trimmed', { 
        removed: removed.length, 
        remaining: this.data.messages.length,
        removedMessages: removed.map(m => ({ id: m.id, type: m.type }))
      });
    }

    this.emit('message:added', { message, session: this.data.id });
  }

  getMessages(limit?: number): KennyMessage[] {
    if (limit && limit > 0) {
      return this.data.messages.slice(-limit);
    }
    return [...this.data.messages];
  }

  getMessageById(messageId: string): KennyMessage | null {
    return this.data.messages.find(m => m.id === messageId) || null;
  }

  deleteMessage(messageId: string): boolean {
    const index = this.data.messages.findIndex(m => m.id === messageId);
    if (index !== -1) {
      const deleted = this.data.messages.splice(index, 1)[0];
      this.data.lastActivity = new Date();
      this.emit('message:deleted', { messageId, message: deleted, session: this.data.id });
      return true;
    }
    return false;
  }

  clearMessages(): void {
    const count = this.data.messages.length;
    this.data.messages = [];
    this.messageResponseTimes = [];
    this.data.lastActivity = new Date();
    this.emit('messages:cleared', { count, session: this.data.id });
  }

  updateContext(updates: Partial<KennyContext>): void {
    // Deep merge the updates
    if (updates.metadata) {
      Object.assign(this.data.kennyContext.metadata, updates.metadata);
    }
    
    if (updates.consciousness) {
      Object.assign(this.data.kennyContext.consciousness, updates.consciousness);
    }

    // Apply other updates
    Object.assign(this.data.kennyContext, {
      ...updates,
      // Preserve existing metadata and consciousness if not being updated
      metadata: this.data.kennyContext.metadata,
      consciousness: this.data.kennyContext.consciousness
    });

    this.data.lastActivity = new Date();
    this.data.kennyContext.consciousness.lastActivity = this.data.lastActivity;
    
    this.emit('context:updated', { 
      updates, 
      context: this.data.kennyContext, 
      session: this.data.id 
    });
  }

  updateMetadata(updates: Record<string, any>): void {
    Object.assign(this.data.metadata, updates);
    this.data.lastActivity = new Date();
    
    this.emit('metadata:updated', { 
      updates, 
      metadata: this.data.metadata, 
      session: this.data.id 
    });
  }

  isExpired(): boolean {
    const now = Date.now();
    const expiry = this.data.lastActivity.getTime() + this.data.config.ttl;
    return now > expiry;
  }

  getContextSummary(): string {
    const messageCount = this.data.messages.length;
    const lastActivity = this.data.lastActivity.toISOString();
    const consciousness = this.data.kennyContext.consciousness;
    
    let summary = `Session ${this.data.id}:\n`;
    summary += `- Messages: ${messageCount}\n`;
    summary += `- Last Activity: ${lastActivity}\n`;
    summary += `- Consciousness Level: ${consciousness.level}\n`;
    summary += `- State: ${consciousness.state}\n`;
    
    if (this.data.userId) {
      summary += `- User: ${this.data.userId}\n`;
    }

    if (messageCount > 0) {
      const firstMessage = this.data.messages[0];
      const lastMessage = this.data.messages[messageCount - 1];
      summary += `- First Message: ${firstMessage.timestamp.toISOString()}\n`;
      summary += `- Last Message: ${lastMessage.timestamp.toISOString()}\n`;
    }

    return summary;
  }

  getActivityStats(): SessionActivityStats {
    const stats: SessionActivityStats = {
      totalMessages: this.data.messages.length,
      userMessages: 0,
      assistantMessages: 0,
      systemMessages: 0,
      toolMessages: 0
    };

    // Count messages by type
    for (const message of this.data.messages) {
      switch (message.type) {
        case 'user':
          stats.userMessages++;
          break;
        case 'assistant':
          stats.assistantMessages++;
          break;
        case 'system':
          stats.systemMessages++;
          break;
        case 'tool':
          stats.toolMessages++;
          break;
      }
    }

    // Set first and last message timestamps
    if (this.data.messages.length > 0) {
      stats.firstMessageAt = this.data.messages[0].timestamp;
      stats.lastMessageAt = this.data.messages[this.data.messages.length - 1].timestamp;
    }

    // Calculate average response time
    if (this.messageResponseTimes.length > 0) {
      const totalTime = this.messageResponseTimes.reduce((sum, time) => sum + time, 0);
      stats.averageResponseTime = totalTime / this.messageResponseTimes.length;
    }

    return stats;
  }

  async cleanup(): Promise<void> {
    // Update consciousness state to dormant
    this.data.kennyContext.consciousness.state = 'dormant';
    
    // Clear any event listeners
    this.removeAllListeners();
    
    // Clear response time tracking
    this.messageResponseTimes = [];
    
    this.emit('session:cleanup', { 
      session: this.data.id,
      messageCount: this.data.messages.length,
      duration: Date.now() - this.data.createdAt.getTime()
    });
  }

  // Helper methods for message filtering
  getUserMessages(): KennyMessage[] {
    return this.data.messages.filter(m => m.type === 'user');
  }

  getAssistantMessages(): KennyMessage[] {
    return this.data.messages.filter(m => m.type === 'assistant');
  }

  getSystemMessages(): KennyMessage[] {
    return this.data.messages.filter(m => m.type === 'system');
  }

  getRecentMessages(minutes: number = 30): KennyMessage[] {
    const cutoff = new Date(Date.now() - minutes * 60 * 1000);
    return this.data.messages.filter(m => m.timestamp > cutoff);
  }

  // Search messages by content
  searchMessages(query: string, caseSensitive: boolean = false): KennyMessage[] {
    const searchQuery = caseSensitive ? query : query.toLowerCase();
    return this.data.messages.filter(message => {
      const content = caseSensitive ? message.content : message.content.toLowerCase();
      return content.includes(searchQuery);
    });
  }

  // Export session data for backup/transfer
  exportData(): {
    session: SessionData;
    stats: SessionActivityStats;
    summary: string;
  } {
    return {
      session: JSON.parse(JSON.stringify(this.data)), // Deep clone
      stats: this.getActivityStats(),
      summary: this.getContextSummary()
    };
  }
}