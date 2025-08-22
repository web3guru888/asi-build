/**
 * WebSocket Message Queue
 * 
 * Provides reliable message delivery with queuing, persistence,
 * and retry mechanisms for WebSocket connections.
 */

import { EventEmitter } from 'eventemitter3';
import { nanoid } from 'nanoid';
import type { 
  WSMessage, 
  WSQueuedMessage, 
  WSConnectionState 
} from './types.js';
import type { ServerConfig } from '../../config/config-types.js';

interface QueueStats {
  totalMessages: number;
  pendingMessages: number;
  failedMessages: number;
  deliveredMessages: number;
  retryAttempts: number;
  connectionQueues: number;
}

export class WSMessageQueue extends EventEmitter {
  private queues = new Map<string, WSQueuedMessage[]>();
  private persistentQueue: WSQueuedMessage[] = [];
  private stats: QueueStats = {
    totalMessages: 0,
    pendingMessages: 0,
    failedMessages: 0,
    deliveredMessages: 0,
    retryAttempts: 0,
    connectionQueues: 0,
  };
  private config: ServerConfig['websocket']['messageQueue'];
  private processingInterval?: NodeJS.Timeout;
  private cleanupInterval?: NodeJS.Timeout;

  constructor(config: ServerConfig['websocket']['messageQueue']) {
    super();
    this.config = {
      enabled: true,
      maxSize: 1000,
      persistence: false,
      ttl: 3600, // 1 hour
      ...config,
    };

    if (this.config.enabled) {
      this.startProcessing();
      this.startCleanup();
    }
  }

  /**
   * Queue a message for delivery
   */
  async queueMessage(
    connectionId: string,
    message: WSMessage,
    options: {
      priority?: number;
      maxAttempts?: number;
      persistent?: boolean;
      delay?: number;
    } = {}
  ): Promise<void> {
    if (!this.config.enabled) {
      throw new Error('Message queue is not enabled');
    }

    const queuedMessage: WSQueuedMessage = {
      connectionId,
      message,
      attempts: 0,
      maxAttempts: options.maxAttempts || 3,
      nextAttempt: Date.now() + (options.delay || 0),
      priority: options.priority || 1,
      persistent: options.persistent || this.config.persistence || false,
    };

    // Add to appropriate queue
    if (queuedMessage.persistent) {
      this.persistentQueue.push(queuedMessage);
    } else {
      let connectionQueue = this.queues.get(connectionId);
      if (!connectionQueue) {
        connectionQueue = [];
        this.queues.set(connectionId, connectionQueue);
        this.stats.connectionQueues++;
      }
      connectionQueue.push(queuedMessage);
    }

    // Check queue size limits
    await this.enforceQueueLimits(connectionId);

    this.stats.totalMessages++;
    this.stats.pendingMessages++;

    this.emit('message:queued', connectionId, message, queuedMessage);
  }

  /**
   * Process queued messages for a specific connection
   */
  async processConnectionQueue(
    connectionId: string,
    sendFunction: (message: WSMessage) => Promise<boolean>
  ): Promise<number> {
    const queue = this.queues.get(connectionId);
    if (!queue || queue.length === 0) {
      return 0;
    }

    const now = Date.now();
    let processed = 0;

    // Sort by priority (higher first) and next attempt time
    queue.sort((a, b) => {
      if (a.priority !== b.priority) {
        return b.priority - a.priority;
      }
      return a.nextAttempt - b.nextAttempt;
    });

    const messagesToProcess = queue.filter(msg => msg.nextAttempt <= now);

    for (let i = messagesToProcess.length - 1; i >= 0; i--) {
      const queuedMessage = messagesToProcess[i];
      
      try {
        const delivered = await sendFunction(queuedMessage.message);
        
        if (delivered) {
          // Remove from queue
          const index = queue.indexOf(queuedMessage);
          if (index > -1) {
            queue.splice(index, 1);
          }
          
          this.stats.deliveredMessages++;
          this.stats.pendingMessages--;
          processed++;
          
          this.emit('message:delivered', connectionId, queuedMessage.message, queuedMessage);
        } else {
          // Delivery failed, increment attempts
          queuedMessage.attempts++;
          this.stats.retryAttempts++;
          
          if (queuedMessage.attempts >= queuedMessage.maxAttempts) {
            // Remove failed message
            const index = queue.indexOf(queuedMessage);
            if (index > -1) {
              queue.splice(index, 1);
            }
            
            this.stats.failedMessages++;
            this.stats.pendingMessages--;
            
            this.emit('message:failed', connectionId, queuedMessage.message, queuedMessage);
          } else {
            // Schedule retry with exponential backoff
            const backoffTime = Math.min(
              1000 * Math.pow(2, queuedMessage.attempts - 1),
              30000 // Max 30 seconds
            );
            queuedMessage.nextAttempt = now + backoffTime;
            
            this.emit('message:retry', connectionId, queuedMessage.message, queuedMessage);
          }
        }
      } catch (error) {
        console.error(`Error processing queued message for ${connectionId}:`, error);
        queuedMessage.attempts++;
        
        if (queuedMessage.attempts >= queuedMessage.maxAttempts) {
          const index = queue.indexOf(queuedMessage);
          if (index > -1) {
            queue.splice(index, 1);
          }
          
          this.stats.failedMessages++;
          this.stats.pendingMessages--;
          
          this.emit('message:error', connectionId, queuedMessage.message, error, queuedMessage);
        }
      }
    }

    // Clean up empty queue
    if (queue.length === 0) {
      this.queues.delete(connectionId);
      this.stats.connectionQueues--;
    }

    return processed;
  }

  /**
   * Process persistent queue
   */
  async processPersistentQueue(
    sendFunction: (connectionId: string, message: WSMessage) => Promise<boolean>
  ): Promise<number> {
    if (this.persistentQueue.length === 0) {
      return 0;
    }

    const now = Date.now();
    let processed = 0;

    // Sort by priority and next attempt time
    this.persistentQueue.sort((a, b) => {
      if (a.priority !== b.priority) {
        return b.priority - a.priority;
      }
      return a.nextAttempt - b.nextAttempt;
    });

    const messagesToProcess = this.persistentQueue.filter(msg => msg.nextAttempt <= now);

    for (let i = messagesToProcess.length - 1; i >= 0; i--) {
      const queuedMessage = messagesToProcess[i];
      
      try {
        const delivered = await sendFunction(queuedMessage.connectionId, queuedMessage.message);
        
        if (delivered) {
          // Remove from persistent queue
          const index = this.persistentQueue.indexOf(queuedMessage);
          if (index > -1) {
            this.persistentQueue.splice(index, 1);
          }
          
          this.stats.deliveredMessages++;
          this.stats.pendingMessages--;
          processed++;
          
          this.emit('message:delivered', queuedMessage.connectionId, queuedMessage.message, queuedMessage);
        } else {
          // Delivery failed, increment attempts
          queuedMessage.attempts++;
          this.stats.retryAttempts++;
          
          if (queuedMessage.attempts >= queuedMessage.maxAttempts) {
            // Remove failed message
            const index = this.persistentQueue.indexOf(queuedMessage);
            if (index > -1) {
              this.persistentQueue.splice(index, 1);
            }
            
            this.stats.failedMessages++;
            this.stats.pendingMessages--;
            
            this.emit('message:failed', queuedMessage.connectionId, queuedMessage.message, queuedMessage);
          } else {
            // Schedule retry with exponential backoff
            const backoffTime = Math.min(
              1000 * Math.pow(2, queuedMessage.attempts - 1),
              30000 // Max 30 seconds
            );
            queuedMessage.nextAttempt = now + backoffTime;
            
            this.emit('message:retry', queuedMessage.connectionId, queuedMessage.message, queuedMessage);
          }
        }
      } catch (error) {
        console.error(`Error processing persistent message for ${queuedMessage.connectionId}:`, error);
        queuedMessage.attempts++;
        
        if (queuedMessage.attempts >= queuedMessage.maxAttempts) {
          const index = this.persistentQueue.indexOf(queuedMessage);
          if (index > -1) {
            this.persistentQueue.splice(index, 1);
          }
          
          this.stats.failedMessages++;
          this.stats.pendingMessages--;
          
          this.emit('message:error', queuedMessage.connectionId, queuedMessage.message, error, queuedMessage);
        }
      }
    }

    return processed;
  }

  /**
   * Get queue size for a connection
   */
  getQueueSize(connectionId: string): number {
    const queue = this.queues.get(connectionId);
    return queue ? queue.length : 0;
  }

  /**
   * Get total queue sizes
   */
  getTotalQueueSize(): number {
    let total = this.persistentQueue.length;
    for (const queue of this.queues.values()) {
      total += queue.length;
    }
    return total;
  }

  /**
   * Clear queue for a connection
   */
  clearConnectionQueue(connectionId: string): number {
    const queue = this.queues.get(connectionId);
    if (!queue) return 0;

    const cleared = queue.length;
    this.queues.delete(connectionId);
    this.stats.connectionQueues--;
    this.stats.pendingMessages -= cleared;

    this.emit('queue:cleared', connectionId, cleared);
    return cleared;
  }

  /**
   * Clear all queues
   */
  clearAllQueues(): number {
    let totalCleared = this.persistentQueue.length;
    
    for (const queue of this.queues.values()) {
      totalCleared += queue.length;
    }
    
    this.queues.clear();
    this.persistentQueue = [];
    this.stats.connectionQueues = 0;
    this.stats.pendingMessages = 0;

    this.emit('queue:all_cleared', totalCleared);
    return totalCleared;
  }

  /**
   * Get queue statistics
   */
  getStats(): QueueStats {
    return { ...this.stats };
  }

  /**
   * Get queue contents for debugging
   */
  getQueueContents(connectionId?: string): {
    connectionQueues: Record<string, WSQueuedMessage[]>;
    persistentQueue: WSQueuedMessage[];
  } {
    const result: any = {
      connectionQueues: {},
      persistentQueue: [...this.persistentQueue],
    };

    if (connectionId) {
      const queue = this.queues.get(connectionId);
      if (queue) {
        result.connectionQueues[connectionId] = [...queue];
      }
    } else {
      for (const [id, queue] of this.queues) {
        result.connectionQueues[id] = [...queue];
      }
    }

    return result;
  }

  /**
   * Priority message queuing
   */
  async queuePriorityMessage(
    connectionId: string,
    message: WSMessage,
    priority: number = 10
  ): Promise<void> {
    await this.queueMessage(connectionId, message, {
      priority,
      maxAttempts: 5,
    });
  }

  /**
   * Queue broadcast message
   */
  async queueBroadcastMessage(
    connectionIds: string[],
    message: WSMessage,
    options: {
      priority?: number;
      maxAttempts?: number;
      persistent?: boolean;
    } = {}
  ): Promise<void> {
    const promises: Promise<void>[] = [];
    
    for (const connectionId of connectionIds) {
      promises.push(this.queueMessage(connectionId, message, options));
    }

    await Promise.all(promises);
  }

  /**
   * Enforce queue size limits
   */
  private async enforceQueueLimits(connectionId: string): Promise<void> {
    const maxSize = this.config.maxSize || 1000;
    const queue = this.queues.get(connectionId);
    
    if (queue && queue.length > maxSize) {
      // Remove oldest messages (FIFO)
      const removed = queue.splice(0, queue.length - maxSize);
      this.stats.pendingMessages -= removed.length;
      this.stats.failedMessages += removed.length;
      
      this.emit('queue:overflow', connectionId, removed.length);
    }

    // Also check persistent queue
    if (this.persistentQueue.length > maxSize) {
      const removed = this.persistentQueue.splice(0, this.persistentQueue.length - maxSize);
      this.stats.pendingMessages -= removed.length;
      this.stats.failedMessages += removed.length;
      
      this.emit('persistent_queue:overflow', removed.length);
    }
  }

  /**
   * Start background processing
   */
  private startProcessing(): void {
    this.processingInterval = setInterval(() => {
      // This will be called by the connection manager
      // when processing individual connection queues
    }, 1000);
  }

  /**
   * Start cleanup routine
   */
  private startCleanup(): void {
    const ttl = (this.config.ttl || 3600) * 1000;
    
    this.cleanupInterval = setInterval(() => {
      const now = Date.now();
      
      // Clean up expired messages from connection queues
      for (const [connectionId, queue] of this.queues) {
        for (let i = queue.length - 1; i >= 0; i--) {
          const message = queue[i];
          if ((now - message.nextAttempt) > ttl) {
            queue.splice(i, 1);
            this.stats.pendingMessages--;
            this.stats.failedMessages++;
            
            this.emit('message:expired', connectionId, message.message, message);
          }
        }
        
        // Remove empty queues
        if (queue.length === 0) {
          this.queues.delete(connectionId);
          this.stats.connectionQueues--;
        }
      }
      
      // Clean up expired messages from persistent queue
      for (let i = this.persistentQueue.length - 1; i >= 0; i--) {
        const message = this.persistentQueue[i];
        if ((now - message.nextAttempt) > ttl) {
          this.persistentQueue.splice(i, 1);
          this.stats.pendingMessages--;
          this.stats.failedMessages++;
          
          this.emit('message:expired', message.connectionId, message.message, message);
        }
      }
    }, 60000); // Run every minute
  }

  /**
   * Pause message processing
   */
  pause(): void {
    if (this.processingInterval) {
      clearInterval(this.processingInterval);
      this.processingInterval = undefined;
    }
    this.emit('queue:paused');
  }

  /**
   * Resume message processing
   */
  resume(): void {
    if (!this.processingInterval) {
      this.startProcessing();
      this.emit('queue:resumed');
    }
  }

  /**
   * Export queue data for persistence
   */
  exportQueueData(): {
    timestamp: number;
    stats: QueueStats;
    connectionQueues: Record<string, WSQueuedMessage[]>;
    persistentQueue: WSQueuedMessage[];
  } {
    const data: any = {
      timestamp: Date.now(),
      stats: { ...this.stats },
      connectionQueues: {},
      persistentQueue: [...this.persistentQueue],
    };

    for (const [connectionId, queue] of this.queues) {
      data.connectionQueues[connectionId] = [...queue];
    }

    return data;
  }

  /**
   * Import queue data from persistence
   */
  importQueueData(data: {
    stats?: QueueStats;
    connectionQueues?: Record<string, WSQueuedMessage[]>;
    persistentQueue?: WSQueuedMessage[];
  }): void {
    if (data.stats) {
      this.stats = { ...data.stats };
    }

    if (data.connectionQueues) {
      this.queues.clear();
      for (const [connectionId, queue] of Object.entries(data.connectionQueues)) {
        this.queues.set(connectionId, [...queue]);
      }
      this.stats.connectionQueues = this.queues.size;
    }

    if (data.persistentQueue) {
      this.persistentQueue = [...data.persistentQueue];
    }

    this.emit('queue:imported', data);
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    if (this.processingInterval) {
      clearInterval(this.processingInterval);
    }
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
    
    this.clearAllQueues();
    this.removeAllListeners();
  }
}