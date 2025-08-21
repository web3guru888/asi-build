/**
 * Event Bus System - Centralized event management and communication
 * 
 * Provides event-driven communication between different components of the ASI-Code system.
 */

import { EventEmitter } from 'eventemitter3';

export interface EventBus extends EventEmitter {
  publish(event: string, data: any): void;
  subscribe(event: string, handler: (data: any) => void): () => void;
  subscribeOnce(event: string, handler: (data: any) => void): () => void;
  unsubscribe(event: string, handler?: (data: any) => void): void;
  cleanup(): Promise<void>;
}

export class DefaultEventBus extends EventEmitter implements EventBus {
  private subscriptionCount = new Map<string, number>();

  publish(event: string, data: any): void {
    this.emit(event, data);
    this.emit('bus:event', { event, data, timestamp: new Date() });
  }

  subscribe(event: string, handler: (data: any) => void): () => void {
    this.on(event, handler);
    
    const count = this.subscriptionCount.get(event) || 0;
    this.subscriptionCount.set(event, count + 1);
    
    this.emit('bus:subscribed', { event, totalSubscriptions: count + 1 });
    
    // Return unsubscribe function
    return () => {
      this.off(event, handler);
      const newCount = (this.subscriptionCount.get(event) || 1) - 1;
      if (newCount <= 0) {
        this.subscriptionCount.delete(event);
      } else {
        this.subscriptionCount.set(event, newCount);
      }
      this.emit('bus:unsubscribed', { event, totalSubscriptions: newCount });
    };
  }

  subscribeOnce(event: string, handler: (data: any) => void): () => void {
    this.once(event, handler);
    
    const count = this.subscriptionCount.get(event) || 0;
    this.subscriptionCount.set(event, count + 1);
    
    this.emit('bus:subscribed_once', { event, totalSubscriptions: count + 1 });
    
    // Return unsubscribe function
    return () => {
      this.off(event, handler);
      const newCount = (this.subscriptionCount.get(event) || 1) - 1;
      if (newCount <= 0) {
        this.subscriptionCount.delete(event);
      } else {
        this.subscriptionCount.set(event, newCount);
      }
    };
  }

  unsubscribe(event: string, handler?: (data: any) => void): void {
    if (handler) {
      this.off(event, handler);
      const count = (this.subscriptionCount.get(event) || 1) - 1;
      if (count <= 0) {
        this.subscriptionCount.delete(event);
      } else {
        this.subscriptionCount.set(event, count);
      }
    } else {
      this.removeAllListeners(event);
      this.subscriptionCount.delete(event);
    }
    
    this.emit('bus:unsubscribed', { event });
  }

  async cleanup(): Promise<void> {
    this.removeAllListeners();
    this.subscriptionCount.clear();
    this.emit('bus:cleanup');
  }
}

export function createEventBus(): EventBus {
  return new DefaultEventBus();
}