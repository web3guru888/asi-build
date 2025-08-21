/**
 * Unit tests for Kenny Message Bus
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MessageBus, resetMessageBus, getMessageBus } from '../../../src/kenny/message-bus.js';
import type { KennyEvent, EventFilter } from '../../../src/kenny/message-bus.js';

describe('MessageBus', () => {
  let messageBus: MessageBus;
  
  beforeEach(() => {
    resetMessageBus();
    messageBus = new MessageBus();
  });
  
  afterEach(() => {
    messageBus.clearSubscriptions();
    messageBus.clearHistory();
  });

  describe('Event Subscription', () => {
    it('should subscribe to events with filter', () => {
      const callback = vi.fn();
      const filter = { type: 'test.event' };
      
      const subscriptionId = messageBus.subscribe(filter, callback);
      
      expect(subscriptionId).toMatch(/^sub_\d+_/);
      expect(messageBus.getSubscriptions()).toHaveLength(1);
      expect(messageBus.getSubscriptions()[0]).toMatchObject({
        id: subscriptionId,
        filter,
        callback,
        priority: 0
      });
    });

    it('should subscribe to events by type', () => {
      const callback = vi.fn();
      const eventType = 'system.startup';
      
      const subscriptionId = messageBus.subscribeToType(eventType, callback);
      
      expect(subscriptionId).toMatch(/^sub_\d+_/);
      const subscription = messageBus.getSubscriptions()[0];
      expect(subscription.filter.type).toBe(eventType);
    });

    it('should subscribe to events by source', () => {
      const callback = vi.fn();
      const source = 'test-subsystem';
      
      const subscriptionId = messageBus.subscribeToSource(source, callback);
      
      expect(subscriptionId).toMatch(/^sub_\d+_/);
      const subscription = messageBus.getSubscriptions()[0];
      expect(subscription.filter.source).toBe(source);
    });

    it('should support subscription options', () => {
      const callback = vi.fn();
      const filter = { type: 'test.event' };
      const options = { once: true, priority: 10 };
      
      const subscriptionId = messageBus.subscribe(filter, callback, options);
      
      const subscription = messageBus.getSubscriptions()[0];
      expect(subscription.once).toBe(true);
      expect(subscription.priority).toBe(10);
    });

    it('should unsubscribe from events', () => {
      const callback = vi.fn();
      const subscriptionId = messageBus.subscribe({ type: 'test' }, callback);
      
      expect(messageBus.getSubscriptions()).toHaveLength(1);
      
      const result = messageBus.unsubscribe(subscriptionId);
      
      expect(result).toBe(true);
      expect(messageBus.getSubscriptions()).toHaveLength(0);
    });

    it('should return false when unsubscribing non-existent subscription', () => {
      const result = messageBus.unsubscribe('non-existent-id');
      expect(result).toBe(false);
    });
  });

  describe('Event Publishing', () => {
    it('should publish events to matching subscribers', async () => {
      const callback = vi.fn();
      messageBus.subscribe({ type: 'test.event' }, callback);
      
      await messageBus.publish({
        type: 'test.event',
        source: 'test',
        data: { message: 'Hello World' }
      });
      
      expect(callback).toHaveBeenCalledOnce();
      
      const calledEvent = callback.mock.calls[0][0] as KennyEvent;
      expect(calledEvent).toMatchObject({
        type: 'test.event',
        source: 'test',
        data: { message: 'Hello World' }
      });
      expect(calledEvent.id).toMatch(/^evt_\d+_/);
      expect(calledEvent.timestamp).toBeInstanceOf(Date);
    });

    it('should not publish to non-matching subscribers', async () => {
      const callback = vi.fn();
      messageBus.subscribe({ type: 'different.event' }, callback);
      
      await messageBus.publish({
        type: 'test.event',
        source: 'test'
      });
      
      expect(callback).not.toHaveBeenCalled();
    });

    it('should handle async callbacks', async () => {
      const asyncCallback = vi.fn().mockResolvedValue(undefined);
      messageBus.subscribe({ type: 'test.event' }, asyncCallback);
      
      await messageBus.publish({
        type: 'test.event',
        source: 'test'
      });
      
      expect(asyncCallback).toHaveBeenCalledOnce();
    });

    it('should execute subscribers by priority', async () => {
      const callOrder: number[] = [];
      
      messageBus.subscribe({ type: 'test' }, () => callOrder.push(1), { priority: 1 });
      messageBus.subscribe({ type: 'test' }, () => callOrder.push(5), { priority: 5 });
      messageBus.subscribe({ type: 'test' }, () => callOrder.push(3), { priority: 3 });
      
      await messageBus.publish({ type: 'test', source: 'test' });
      
      expect(callOrder).toEqual([5, 3, 1]);
    });

    it('should handle subscription errors gracefully', async () => {
      const errorCallback = vi.fn().mockImplementation(() => {
        throw new Error('Callback error');
      });
      const successCallback = vi.fn();
      
      messageBus.subscribe({ type: 'test' }, errorCallback);
      messageBus.subscribe({ type: 'test' }, successCallback);
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      await messageBus.publish({ type: 'test', source: 'test' });
      
      expect(errorCallback).toHaveBeenCalledOnce();
      expect(successCallback).toHaveBeenCalledOnce();
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Error in event subscription'),
        expect.any(Error)
      );
      
      consoleSpy.mockRestore();
    });

    it('should remove once subscriptions after execution', async () => {
      const callback = vi.fn();
      messageBus.subscribe({ type: 'test' }, callback, { once: true });
      
      expect(messageBus.getSubscriptions()).toHaveLength(1);
      
      await messageBus.publish({ type: 'test', source: 'test' });
      
      expect(callback).toHaveBeenCalledOnce();
      expect(messageBus.getSubscriptions()).toHaveLength(0);
    });
  });

  describe('System Events', () => {
    it('should publish system events', async () => {
      const callback = vi.fn();
      messageBus.subscribe({ type: 'system.startup' }, callback);
      
      await messageBus.publishSystem('system.startup', { version: '1.0.0' });
      
      expect(callback).toHaveBeenCalledOnce();
      const event = callback.mock.calls[0][0] as KennyEvent;
      expect(event.type).toBe('system.startup');
      expect(event.source).toBe('system');
      expect(event.data).toEqual({ version: '1.0.0' });
    });
  });

  describe('Message Events', () => {
    it('should publish message events', async () => {
      const callback = vi.fn();
      messageBus.subscribe({ type: 'message.send' }, callback);
      
      const messageData = {
        messageId: 'msg-123',
        content: 'Hello',
        contextId: 'ctx-456'
      };
      
      await messageBus.publishMessage('message.send', 'chat', messageData, 'user');
      
      expect(callback).toHaveBeenCalledOnce();
      const event = callback.mock.calls[0][0] as KennyEvent;
      expect(event.type).toBe('message.send');
      expect(event.source).toBe('chat');
      expect(event.target).toBe('user');
      expect(event.data).toEqual(messageData);
    });
  });

  describe('Event Filtering', () => {
    it('should filter by type string', async () => {
      const callback = vi.fn();
      messageBus.subscribe({ type: 'system.startup' }, callback);
      
      await messageBus.publish({ type: 'system.startup', source: 'test' });
      await messageBus.publish({ type: 'system.shutdown', source: 'test' });
      
      expect(callback).toHaveBeenCalledOnce();
    });

    it('should filter by type regex', async () => {
      const callback = vi.fn();
      messageBus.subscribe({ type: /^system\./ }, callback);
      
      await messageBus.publish({ type: 'system.startup', source: 'test' });
      await messageBus.publish({ type: 'system.shutdown', source: 'test' });
      await messageBus.publish({ type: 'message.send', source: 'test' });
      
      expect(callback).toHaveBeenCalledTimes(2);
    });

    it('should filter by source string', async () => {
      const callback = vi.fn();
      messageBus.subscribe({ source: 'subsystem-a' }, callback);
      
      await messageBus.publish({ type: 'test', source: 'subsystem-a' });
      await messageBus.publish({ type: 'test', source: 'subsystem-b' });
      
      expect(callback).toHaveBeenCalledOnce();
    });

    it('should filter by source regex', async () => {
      const callback = vi.fn();
      messageBus.subscribe({ source: /^subsystem-/ }, callback);
      
      await messageBus.publish({ type: 'test', source: 'subsystem-a' });
      await messageBus.publish({ type: 'test', source: 'subsystem-b' });
      await messageBus.publish({ type: 'test', source: 'other' });
      
      expect(callback).toHaveBeenCalledTimes(2);
    });

    it('should filter by target', async () => {
      const callback = vi.fn();
      messageBus.subscribe({ target: 'specific-target' }, callback);
      
      await messageBus.publish({ type: 'test', source: 'test', target: 'specific-target' });
      await messageBus.publish({ type: 'test', source: 'test', target: 'other-target' });
      await messageBus.publish({ type: 'test', source: 'test' }); // No target
      
      expect(callback).toHaveBeenCalledOnce();
    });

    it('should filter by custom predicate', async () => {
      const callback = vi.fn();
      const predicate = (event: KennyEvent) => event.data?.priority > 5;
      messageBus.subscribe({ predicate }, callback);
      
      await messageBus.publish({ type: 'test', source: 'test', data: { priority: 10 } });
      await messageBus.publish({ type: 'test', source: 'test', data: { priority: 3 } });
      
      expect(callback).toHaveBeenCalledOnce();
    });

    it('should combine multiple filters', async () => {
      const callback = vi.fn();
      messageBus.subscribe({
        type: /^system\./,
        source: 'core',
        predicate: (event: KennyEvent) => event.data?.level === 'critical'
      }, callback);
      
      await messageBus.publish({ 
        type: 'system.error', 
        source: 'core', 
        data: { level: 'critical' } 
      }); // Should match
      
      await messageBus.publish({ 
        type: 'system.error', 
        source: 'core', 
        data: { level: 'warning' } 
      }); // Should not match (predicate fails)
      
      await messageBus.publish({ 
        type: 'system.error', 
        source: 'other', 
        data: { level: 'critical' } 
      }); // Should not match (source fails)
      
      await messageBus.publish({ 
        type: 'user.action', 
        source: 'core', 
        data: { level: 'critical' } 
      }); // Should not match (type fails)
      
      expect(callback).toHaveBeenCalledOnce();
    });
  });

  describe('Event History', () => {
    it('should maintain event history', async () => {
      await messageBus.publish({ type: 'event1', source: 'test1' });
      await messageBus.publish({ type: 'event2', source: 'test2' });
      
      const history = messageBus.getHistory();
      
      expect(history).toHaveLength(2);
      expect(history[0].type).toBe('event1');
      expect(history[1].type).toBe('event2');
    });

    it('should filter history', () => {
      // Setup history by publishing events first
      vi.useFakeTimers();
      
      messageBus.publish({ type: 'system.startup', source: 'system' });
      messageBus.publish({ type: 'user.action', source: 'ui' });
      messageBus.publish({ type: 'system.shutdown', source: 'system' });
      
      vi.useRealTimers();
      
      const systemEvents = messageBus.getHistory({ type: /^system\./ });
      expect(systemEvents).toHaveLength(2);
      expect(systemEvents[0].type).toBe('system.startup');
      expect(systemEvents[1].type).toBe('system.shutdown');
    });

    it('should limit history results', async () => {
      for (let i = 0; i < 5; i++) {
        await messageBus.publish({ type: `event${i}`, source: 'test' });
      }
      
      const limitedHistory = messageBus.getHistory(undefined, 3);
      expect(limitedHistory).toHaveLength(3);
      expect(limitedHistory[0].type).toBe('event2'); // Last 3 events
    });

    it('should clear history', async () => {
      await messageBus.publish({ type: 'test', source: 'test' });
      expect(messageBus.getHistory()).toHaveLength(1);
      
      messageBus.clearHistory();
      expect(messageBus.getHistory()).toHaveLength(0);
    });

    it('should maintain history size limit', async () => {
      messageBus.setMaxHistorySize(3);
      
      for (let i = 0; i < 5; i++) {
        await messageBus.publish({ type: `event${i}`, source: 'test' });
      }
      
      const history = messageBus.getHistory();
      expect(history).toHaveLength(3);
      expect(history.map(e => e.type)).toEqual(['event2', 'event3', 'event4']);
    });
  });

  describe('Singleton Pattern', () => {
    it('should return same instance from getMessageBus', () => {
      const instance1 = getMessageBus();
      const instance2 = getMessageBus();
      
      expect(instance1).toBe(instance2);
    });

    it('should reset singleton instance', () => {
      const instance1 = getMessageBus();
      resetMessageBus();
      const instance2 = getMessageBus();
      
      expect(instance1).not.toBe(instance2);
    });
  });

  describe('EventEmitter Integration', () => {
    it('should emit events for legacy compatibility', async () => {
      const legacyCallback = vi.fn();
      messageBus.on('test.event', legacyCallback);
      
      await messageBus.publish({ type: 'test.event', source: 'test' });
      
      expect(legacyCallback).toHaveBeenCalledOnce();
    });

    it('should emit wildcard events', async () => {
      const wildcardCallback = vi.fn();
      messageBus.on('*', wildcardCallback);
      
      await messageBus.publish({ type: 'any.event', source: 'test' });
      
      expect(wildcardCallback).toHaveBeenCalledOnce();
    });
  });
});