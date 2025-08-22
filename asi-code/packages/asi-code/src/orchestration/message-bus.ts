/**
 * ASI-Code Orchestration Message Bus
 * 
 * Event-driven message passing system for agent-to-agent communication
 * with pub/sub pattern, message routing, queuing, and delivery guarantees.
 */

import { EventEmitter } from 'eventemitter3';
import { AgentMessage, MessageType, Agent } from './types.js';

// Message routing modes
export type MessageRoutingMode = 'broadcast' | 'multicast' | 'unicast' | 'round_robin' | 'load_balanced';

// Message delivery guarantees
export type DeliveryGuarantee = 'at_most_once' | 'at_least_once' | 'exactly_once';

// Message persistence options
export interface MessagePersistenceOptions {
  enabled: boolean;
  maxMessages: number;
  ttl?: number; // Time to live in milliseconds
  persistFailedMessages: boolean;
}

// Message subscription
export interface MessageSubscription {
  id: string;
  subscriberId: string;
  messageTypes: MessageType[];
  filter?: (message: AgentMessage) => boolean;
  callback: (message: AgentMessage) => Promise<void> | void;
  deliveryGuarantee: DeliveryGuarantee;
  retryPolicy?: RetryPolicy;
}

export interface RetryPolicy {
  maxRetries: number;
  backoffMultiplier: number;
  initialDelay: number;
  maxDelay: number;
}

// Message queue entry
interface QueuedMessage {
  message: AgentMessage;
  subscribers: string[];
  attempts: number;
  lastAttempt?: number;
  scheduledFor?: number;
}

// Message delivery status
export interface DeliveryStatus {
  messageId: string;
  subscriberId: string;
  status: 'pending' | 'delivered' | 'failed' | 'retrying';
  attempts: number;
  lastAttempt?: number;
  error?: Error;
}

// Message bus configuration
export interface MessageBusConfig {
  persistence: MessagePersistenceOptions;
  defaultDeliveryGuarantee: DeliveryGuarantee;
  defaultRetryPolicy: RetryPolicy;
  maxQueueSize: number;
  processingInterval: number;
}

export class MessageBus extends EventEmitter {
  private subscriptions = new Map<string, MessageSubscription>();
  private messageQueue: QueuedMessage[] = [];
  private persistedMessages: AgentMessage[] = [];
  private deliveryStatuses = new Map<string, DeliveryStatus[]>();
  private processingTimer?: NodeJS.Timeout;
  private config: MessageBusConfig;

  constructor(config?: Partial<MessageBusConfig>) {
    super();
    
    this.config = {
      persistence: {
        enabled: true,
        maxMessages: 10000,
        ttl: 24 * 60 * 60 * 1000, // 24 hours
        persistFailedMessages: true
      },
      defaultDeliveryGuarantee: 'at_least_once',
      defaultRetryPolicy: {
        maxRetries: 3,
        backoffMultiplier: 2,
        initialDelay: 1000,
        maxDelay: 30000
      },
      maxQueueSize: 50000,
      processingInterval: 100,
      ...config
    };

    this.startProcessing();
  }

  /**
   * Subscribe to messages with optional filtering and delivery guarantees
   */
  subscribe(
    subscriberId: string,
    messageTypes: MessageType[],
    callback: (message: AgentMessage) => Promise<void> | void,
    options: {
      filter?: (message: AgentMessage) => boolean;
      deliveryGuarantee?: DeliveryGuarantee;
      retryPolicy?: RetryPolicy;
    } = {}
  ): string {
    const subscriptionId = `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const subscription: MessageSubscription = {
      id: subscriptionId,
      subscriberId,
      messageTypes,
      filter: options.filter,
      callback,
      deliveryGuarantee: options.deliveryGuarantee || this.config.defaultDeliveryGuarantee,
      retryPolicy: options.retryPolicy || this.config.defaultRetryPolicy
    };

    this.subscriptions.set(subscriptionId, subscription);
    
    this.emit('subscription:created', { subscriptionId, subscriberId, messageTypes });
    
    return subscriptionId;
  }

  /**
   * Unsubscribe from messages
   */
  unsubscribe(subscriptionId: string): boolean {
    const subscription = this.subscriptions.get(subscriptionId);
    if (!subscription) return false;

    this.subscriptions.delete(subscriptionId);
    this.emit('subscription:removed', { subscriptionId, subscriberId: subscription.subscriberId });
    
    return true;
  }

  /**
   * Publish a message to subscribers
   */
  async publish(
    message: Omit<AgentMessage, 'id' | 'timestamp'>,
    routingMode: MessageRoutingMode = 'broadcast',
    targetSubscribers?: string[]
  ): Promise<string> {
    const fullMessage: AgentMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      ...message
    };

    // Persist message if enabled
    if (this.config.persistence.enabled) {
      this.persistMessage(fullMessage);
    }

    // Find matching subscribers
    const subscribers = this.findMatchingSubscribers(fullMessage, routingMode, targetSubscribers);
    
    if (subscribers.length === 0) {
      this.emit('message:no_subscribers', fullMessage);
      return fullMessage.id;
    }

    // Queue message for delivery
    const queuedMessage: QueuedMessage = {
      message: fullMessage,
      subscribers,
      attempts: 0
    };

    this.addToQueue(queuedMessage);
    
    this.emit('message:published', { 
      messageId: fullMessage.id, 
      subscriberCount: subscribers.length,
      routingMode 
    });

    return fullMessage.id;
  }

  /**
   * Broadcast message to all matching subscribers
   */
  async broadcast(message: Omit<AgentMessage, 'id' | 'timestamp'>): Promise<string> {
    return this.publish(message, 'broadcast');
  }

  /**
   * Multicast message to specific subscribers
   */
  async multicast(
    message: Omit<AgentMessage, 'id' | 'timestamp'>,
    targetSubscribers: string[]
  ): Promise<string> {
    return this.publish(message, 'multicast', targetSubscribers);
  }

  /**
   * Send unicast message to a specific subscriber
   */
  async unicast(
    message: Omit<AgentMessage, 'id' | 'timestamp' | 'to'>,
    to: string
  ): Promise<string> {
    return this.publish({ ...message, to }, 'unicast', [to]);
  }

  /**
   * Send message using round-robin routing
   */
  async roundRobin(message: Omit<AgentMessage, 'id' | 'timestamp'>): Promise<string> {
    return this.publish(message, 'round_robin');
  }

  /**
   * Send message using load-balanced routing
   */
  async loadBalanced(message: Omit<AgentMessage, 'id' | 'timestamp'>): Promise<string> {
    return this.publish(message, 'load_balanced');
  }

  /**
   * Get message delivery status
   */
  getDeliveryStatus(messageId: string): DeliveryStatus[] {
    return this.deliveryStatuses.get(messageId) || [];
  }

  /**
   * Get persisted messages with optional filtering
   */
  getPersistedMessages(filter?: {
    type?: MessageType;
    from?: string;
    to?: string;
    since?: number;
  }): AgentMessage[] {
    let messages = this.persistedMessages;

    if (filter) {
      messages = messages.filter(msg => {
        if (filter.type && msg.type !== filter.type) return false;
        if (filter.from && msg.from !== filter.from) return false;
        if (filter.to && msg.to !== filter.to) return false;
        if (filter.since && msg.timestamp < filter.since) return false;
        return true;
      });
    }

    return messages;
  }

  /**
   * Replay persisted messages to a subscriber
   */
  async replayMessages(
    subscriberId: string,
    filter?: {
      type?: MessageType;
      from?: string;
      since?: number;
      limit?: number;
    }
  ): Promise<number> {
    const messages = this.getPersistedMessages(filter);
    const subscription = Array.from(this.subscriptions.values())
      .find(sub => sub.subscriberId === subscriberId);

    if (!subscription) {
      throw new Error(`Subscriber ${subscriberId} not found`);
    }

    const messagesToReplay = messages
      .filter(msg => subscription.messageTypes.includes(msg.type))
      .filter(msg => !subscription.filter || subscription.filter(msg))
      .slice(0, filter?.limit || messages.length);

    let replayed = 0;
    for (const message of messagesToReplay) {
      try {
        await this.deliverMessage(message, subscription);
        replayed++;
      } catch (error) {
        this.emit('replay:error', { messageId: message.id, subscriberId, error });
      }
    }

    this.emit('replay:completed', { subscriberId, replayed, total: messagesToReplay.length });
    return replayed;
  }

  /**
   * Get queue statistics
   */
  getQueueStats() {
    return {
      queueSize: this.messageQueue.length,
      persistedMessages: this.persistedMessages.length,
      activeSubscriptions: this.subscriptions.size,
      maxQueueSize: this.config.maxQueueSize,
      processingInterval: this.config.processingInterval
    };
  }

  /**
   * Clear message queue and optionally persisted messages
   */
  clear(clearPersisted = false) {
    this.messageQueue = [];
    if (clearPersisted) {
      this.persistedMessages = [];
    }
    this.deliveryStatuses.clear();
    this.emit('bus:cleared', { clearPersisted });
  }

  /**
   * Shutdown the message bus
   */
  shutdown() {
    if (this.processingTimer) {
      clearInterval(this.processingTimer);
      this.processingTimer = undefined;
    }
    this.subscriptions.clear();
    this.messageQueue = [];
    this.emit('bus:shutdown');
  }

  // Private methods

  private findMatchingSubscribers(
    message: AgentMessage,
    routingMode: MessageRoutingMode,
    targetSubscribers?: string[]
  ): string[] {
    const allSubscriptions = Array.from(this.subscriptions.values());
    
    // Filter by message type and custom filters
    let matchingSubscriptions = allSubscriptions.filter(sub => {
      if (!sub.messageTypes.includes(message.type)) return false;
      if (sub.filter && !sub.filter(message)) return false;
      return true;
    });

    // Apply routing mode logic
    switch (routingMode) {
      case 'broadcast':
        return matchingSubscriptions.map(sub => sub.subscriberId);
        
      case 'multicast':
        if (!targetSubscribers) return [];
        return matchingSubscriptions
          .filter(sub => targetSubscribers.includes(sub.subscriberId))
          .map(sub => sub.subscriberId);
          
      case 'unicast':
        const targetSub = matchingSubscriptions.find(sub => 
          sub.subscriberId === message.to
        );
        return targetSub ? [targetSub.subscriberId] : [];
        
      case 'round_robin':
        if (matchingSubscriptions.length === 0) return [];
        const rrIndex = Date.now() % matchingSubscriptions.length;
        return [matchingSubscriptions[rrIndex].subscriberId];
        
      case 'load_balanced':
        // Simple load balancing - could be enhanced with actual load metrics
        if (matchingSubscriptions.length === 0) return [];
        const lbIndex = Math.floor(Math.random() * matchingSubscriptions.length);
        return [matchingSubscriptions[lbIndex].subscriberId];
        
      default:
        return [];
    }
  }

  private addToQueue(queuedMessage: QueuedMessage) {
    if (this.messageQueue.length >= this.config.maxQueueSize) {
      this.emit('queue:full', { 
        messageId: queuedMessage.message.id,
        queueSize: this.messageQueue.length 
      });
      return;
    }

    this.messageQueue.push(queuedMessage);
  }

  private startProcessing() {
    this.processingTimer = setInterval(() => {
      this.processQueue();
    }, this.config.processingInterval);
  }

  private async processQueue() {
    if (this.messageQueue.length === 0) return;

    const now = Date.now();
    const messagesToProcess = this.messageQueue.filter(qm => 
      !qm.scheduledFor || qm.scheduledFor <= now
    );

    for (const queuedMessage of messagesToProcess.slice(0, 10)) { // Process max 10 per cycle
      await this.processQueuedMessage(queuedMessage);
    }

    // Remove processed messages
    this.messageQueue = this.messageQueue.filter(qm => 
      !messagesToProcess.includes(qm)
    );
  }

  private async processQueuedMessage(queuedMessage: QueuedMessage) {
    const { message, subscribers } = queuedMessage;
    
    for (const subscriberId of subscribers) {
      const subscription = Array.from(this.subscriptions.values())
        .find(sub => sub.subscriberId === subscriberId);
        
      if (!subscription) continue;

      try {
        await this.deliverMessage(message, subscription);
        this.updateDeliveryStatus(message.id, subscriberId, 'delivered', 0);
      } catch (error) {
        await this.handleDeliveryFailure(message, subscription, error as Error, queuedMessage);
      }
    }
  }

  private async deliverMessage(message: AgentMessage, subscription: MessageSubscription) {
    const deliveryId = `${message.id}_${subscription.subscriberId}`;
    
    try {
      this.emit('message:delivering', { messageId: message.id, subscriberId: subscription.subscriberId });
      
      const result = subscription.callback(message);
      if (result instanceof Promise) {
        await result;
      }
      
      this.emit('message:delivered', { messageId: message.id, subscriberId: subscription.subscriberId });
      
    } catch (error) {
      this.emit('message:delivery_failed', { 
        messageId: message.id, 
        subscriberId: subscription.subscriberId, 
        error 
      });
      throw error;
    }
  }

  private async handleDeliveryFailure(
    message: AgentMessage,
    subscription: MessageSubscription,
    error: Error,
    queuedMessage: QueuedMessage
  ) {
    const retryPolicy = subscription.retryPolicy || this.config.defaultRetryPolicy;
    queuedMessage.attempts++;
    queuedMessage.lastAttempt = Date.now();

    this.updateDeliveryStatus(message.id, subscription.subscriberId, 'failed', queuedMessage.attempts, error);

    if (queuedMessage.attempts < retryPolicy.maxRetries) {
      // Schedule retry with exponential backoff
      const delay = Math.min(
        retryPolicy.initialDelay * Math.pow(retryPolicy.backoffMultiplier, queuedMessage.attempts - 1),
        retryPolicy.maxDelay
      );
      
      queuedMessage.scheduledFor = Date.now() + delay;
      this.updateDeliveryStatus(message.id, subscription.subscriberId, 'retrying', queuedMessage.attempts);
      
      this.emit('message:retry_scheduled', { 
        messageId: message.id, 
        subscriberId: subscription.subscriberId,
        attempt: queuedMessage.attempts,
        delay 
      });
    } else {
      // Max retries exceeded
      if (this.config.persistence.persistFailedMessages) {
        this.persistMessage(message);
      }
      
      this.emit('message:failed_permanently', { 
        messageId: message.id, 
        subscriberId: subscription.subscriberId,
        attempts: queuedMessage.attempts,
        error 
      });
    }
  }

  private updateDeliveryStatus(
    messageId: string,
    subscriberId: string,
    status: DeliveryStatus['status'],
    attempts: number,
    error?: Error
  ) {
    if (!this.deliveryStatuses.has(messageId)) {
      this.deliveryStatuses.set(messageId, []);
    }

    const statuses = this.deliveryStatuses.get(messageId)!;
    let statusEntry = statuses.find(s => s.subscriberId === subscriberId);

    if (!statusEntry) {
      statusEntry = {
        messageId,
        subscriberId,
        status,
        attempts
      };
      statuses.push(statusEntry);
    } else {
      statusEntry.status = status;
      statusEntry.attempts = attempts;
    }

    statusEntry.lastAttempt = Date.now();
    if (error) {
      statusEntry.error = error;
    }
  }

  private persistMessage(message: AgentMessage) {
    this.persistedMessages.push(message);

    // Maintain size limit
    if (this.persistedMessages.length > this.config.persistence.maxMessages) {
      this.persistedMessages = this.persistedMessages.slice(-this.config.persistence.maxMessages);
    }

    // Clean up expired messages
    if (this.config.persistence.ttl) {
      const cutoff = Date.now() - this.config.persistence.ttl;
      this.persistedMessages = this.persistedMessages.filter(msg => msg.timestamp >= cutoff);
    }
  }
}

// Singleton instance for global usage
let messageBusInstance: MessageBus | null = null;

/**
 * Get the global orchestration message bus instance
 */
export function getOrchestrationMessageBus(config?: Partial<MessageBusConfig>): MessageBus {
  if (!messageBusInstance) {
    messageBusInstance = new MessageBus(config);
  }
  return messageBusInstance;
}

/**
 * Reset the global message bus instance (for testing)
 */
export function resetOrchestrationMessageBus(): void {
  if (messageBusInstance) {
    messageBusInstance.shutdown();
    messageBusInstance = null;
  }
}