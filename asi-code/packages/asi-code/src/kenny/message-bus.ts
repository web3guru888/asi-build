/**
 * Kenny Integration Pattern - Message Bus
 * 
 * Provides a typed event system for inter-subsystem communication
 * with event filtering, routing, and subscription management.
 */

import { EventEmitter } from 'eventemitter3';

// Core event types
export interface BaseEvent {
  id: string;
  type: string;
  timestamp: Date;
  source: string;
  target?: string;
  data?: any;
  metadata?: Record<string, any>;
}

export interface SystemEvent extends BaseEvent {
  type: 'system.startup' | 'system.shutdown' | 'system.error' | 'system.health';
}

export interface SubsystemEvent extends BaseEvent {
  type: 'subsystem.register' | 'subsystem.unregister' | 'subsystem.ready' | 'subsystem.error';
  data: {
    subsystemId: string;
    subsystemName: string;
    version?: string;
  };
}

export interface MessageEvent extends BaseEvent {
  type: 'message.send' | 'message.receive' | 'message.process' | 'message.complete';
  data: {
    messageId: string;
    content: any;
    contextId?: string;
  };
}

export type KennyEvent = SystemEvent | SubsystemEvent | MessageEvent | BaseEvent;

// Event filter types
export interface EventFilter {
  type?: string | RegExp;
  source?: string | RegExp;
  target?: string | RegExp;
  predicate?: (event: KennyEvent) => boolean;
}

// Subscription types
export interface EventSubscription {
  id: string;
  filter: EventFilter;
  callback: (event: KennyEvent) => void | Promise<void>;
  once?: boolean;
  priority?: number;
}

export class MessageBus extends EventEmitter {
  private subscriptions = new Map<string, EventSubscription>();
  private eventHistory: KennyEvent[] = [];
  private maxHistorySize = 1000;

  constructor() {
    super();
  }

  /**
   * Subscribe to events with optional filtering
   */
  subscribe(
    filter: EventFilter,
    callback: (event: KennyEvent) => void | Promise<void>,
    options: { once?: boolean; priority?: number } = {}
  ): string {
    const subscriptionId = `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const subscription: EventSubscription = {
      id: subscriptionId,
      filter,
      callback,
      once: options.once,
      priority: options.priority ?? 0
    };

    this.subscriptions.set(subscriptionId, subscription);
    return subscriptionId;
  }

  /**
   * Subscribe to events by type (convenience method)
   */
  subscribeToType(
    eventType: string,
    callback: (event: KennyEvent) => void | Promise<void>,
    options: { once?: boolean; priority?: number } = {}
  ): string {
    return this.subscribe({ type: eventType }, callback, options);
  }

  /**
   * Subscribe to events from a specific source
   */
  subscribeToSource(
    source: string,
    callback: (event: KennyEvent) => void | Promise<void>,
    options: { once?: boolean; priority?: number } = {}
  ): string {
    return this.subscribe({ source }, callback, options);
  }

  /**
   * Unsubscribe from events
   */
  unsubscribe(subscriptionId: string): boolean {
    return this.subscriptions.delete(subscriptionId);
  }

  /**
   * Publish an event to all matching subscribers
   */
  async publish(event: Omit<KennyEvent, 'id' | 'timestamp'>): Promise<void> {
    const fullEvent: KennyEvent = {
      id: `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      ...event
    };

    // Add to history
    this.addToHistory(fullEvent);

    // Get matching subscriptions, sorted by priority
    const matchingSubscriptions = Array.from(this.subscriptions.values())
      .filter(sub => this.matchesFilter(fullEvent, sub.filter))
      .sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0));

    // Execute callbacks
    const promises: Promise<void>[] = [];
    const toRemove: string[] = [];

    for (const subscription of matchingSubscriptions) {
      try {
        const result = subscription.callback(fullEvent);
        if (result instanceof Promise) {
          promises.push(result);
        }

        // Mark for removal if it's a once subscription
        if (subscription.once) {
          toRemove.push(subscription.id);
        }
      } catch (error) {
        console.error(`Error in event subscription ${subscription.id}:`, error);
        // Emit error event
        this.emit('subscription.error', {
          subscriptionId: subscription.id,
          event: fullEvent,
          error
        });
      }
    }

    // Wait for all async callbacks
    if (promises.length > 0) {
      await Promise.allSettled(promises);
    }

    // Remove once subscriptions
    toRemove.forEach(id => this.unsubscribe(id));

    // Emit to EventEmitter for legacy compatibility
    this.emit(fullEvent.type, fullEvent);
    this.emit('*', fullEvent);
  }

  /**
   * Publish a system event
   */
  async publishSystem(
    type: SystemEvent['type'],
    data?: any,
    metadata?: Record<string, any>
  ): Promise<void> {
    await this.publish({
      type,
      source: 'system',
      data,
      metadata
    });
  }

  /**
   * Publish a subsystem event
   */
  async publishSubsystem(
    type: string,
    source: string,
    data: any,
    metadata?: Record<string, any>
  ): Promise<void> {
    await this.publish({
      type,
      source,
      data,
      metadata
    });
  }

  /**
   * Publish a message event
   */
  async publishMessage(
    type: MessageEvent['type'],
    source: string,
    data: MessageEvent['data'],
    target?: string,
    metadata?: Record<string, any>
  ): Promise<void> {
    await this.publish({
      type,
      source,
      target,
      data,
      metadata
    });
  }

  /**
   * Get event history
   */
  getHistory(filter?: EventFilter, limit?: number): KennyEvent[] {
    let events = this.eventHistory;

    if (filter) {
      events = events.filter(event => this.matchesFilter(event, filter));
    }

    if (limit && limit > 0) {
      events = events.slice(-limit);
    }

    return events;
  }

  /**
   * Clear event history
   */
  clearHistory(): void {
    this.eventHistory = [];
  }

  /**
   * Get active subscriptions
   */
  getSubscriptions(): EventSubscription[] {
    return Array.from(this.subscriptions.values());
  }

  /**
   * Clear all subscriptions
   */
  clearSubscriptions(): void {
    this.subscriptions.clear();
  }

  /**
   * Check if an event matches a filter
   */
  private matchesFilter(event: KennyEvent, filter: EventFilter): boolean {
    // Check type filter
    if (filter.type) {
      if (filter.type instanceof RegExp) {
        if (!filter.type.test(event.type)) return false;
      } else {
        if (event.type !== filter.type) return false;
      }
    }

    // Check source filter
    if (filter.source) {
      if (filter.source instanceof RegExp) {
        if (!filter.source.test(event.source)) return false;
      } else {
        if (event.source !== filter.source) return false;
      }
    }

    // Check target filter
    if (filter.target && event.target) {
      if (filter.target instanceof RegExp) {
        if (!filter.target.test(event.target)) return false;
      } else {
        if (event.target !== filter.target) return false;
      }
    }

    // Check custom predicate
    if (filter.predicate) {
      if (!filter.predicate(event)) return false;
    }

    return true;
  }

  /**
   * Add event to history with size management
   */
  private addToHistory(event: KennyEvent): void {
    this.eventHistory.push(event);
    
    // Maintain history size
    if (this.eventHistory.length > this.maxHistorySize) {
      this.eventHistory = this.eventHistory.slice(-this.maxHistorySize);
    }
  }

  /**
   * Set maximum history size
   */
  setMaxHistorySize(size: number): void {
    this.maxHistorySize = size;
    if (this.eventHistory.length > size) {
      this.eventHistory = this.eventHistory.slice(-size);
    }
  }
}

// Singleton instance
let messageBusInstance: MessageBus | null = null;

/**
 * Get the global message bus instance
 */
export function getMessageBus(): MessageBus {
  if (!messageBusInstance) {
    messageBusInstance = new MessageBus();
  }
  return messageBusInstance;
}

/**
 * Reset the global message bus instance (for testing)
 */
export function resetMessageBus(): void {
  messageBusInstance = null;
}