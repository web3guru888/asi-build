/**
 * Connection Optimizations for WebSocket Scaling
 *
 * Implements connection pooling, backpressure handling, and performance monitoring
 * to support 10,000+ concurrent WebSocket connections efficiently.
 */

import { EventEmitter } from 'eventemitter3';
import WebSocket from 'ws';
import { nanoid } from 'nanoid';
import type { WSConnectionState } from './types.js';

export interface ConnectionMetrics {
  messagesPerSecond: number;
  bytesPerSecond: number;
  lastResetTime: number;
  connectionTime: number;
  totalMessages: number;
  totalBytes: number;
  memoryUsage: number;
  cpuUsage: number;
}

export interface ConnectionPoolConfig {
  maxPoolSize: number;
  maxBufferSize: number;
  backpressureThreshold: number;
  flushInterval: number;
}

export class ConnectionOptimizer extends EventEmitter {
  private readonly connectionMetrics = new Map<string, ConnectionMetrics>();
  private readonly messageBuffer = new Map<string, Buffer[]>();
  private readonly backpressureActive = new Set<string>();
  private readonly connectionPools = new Map<string, Set<string>>();
  private flushInterval?: NodeJS.Timeout;

  constructor(
    private config: ConnectionPoolConfig = {
      maxPoolSize: 10000,
      maxBufferSize: 100,
      backpressureThreshold: 1024 * 50, // 50KB buffer threshold
      flushInterval: 16, // ~60fps buffer flushing
    }
  ) {
    super();
    this.startBufferFlushing();
  }

  /**
   * Initialize connection with metrics tracking
   */
  initializeConnection(connectionId: string, ws: WebSocket): void {
    this.connectionMetrics.set(connectionId, {
      messagesPerSecond: 0,
      bytesPerSecond: 0,
      lastResetTime: Date.now(),
      connectionTime: Date.now(),
      totalMessages: 0,
      totalBytes: 0,
      memoryUsage: 0,
      cpuUsage: 0,
    });

    this.messageBuffer.set(connectionId, []);

    // Set up WebSocket buffer optimization
    if (ws.bufferedAmount !== undefined) {
      // Monitor buffer backpressure
      const checkBackpressure = () => {
        if (ws.bufferedAmount > this.config.backpressureThreshold) {
          this.backpressureActive.add(connectionId);
          this.emit('backpressure:active', connectionId, ws.bufferedAmount);
        } else {
          this.backpressureActive.delete(connectionId);
        }
      };

      // Check backpressure periodically
      const backpressureInterval = setInterval(checkBackpressure, 100);

      ws.on('close', () => {
        clearInterval(backpressureInterval);
      });
    }
  }

  /**
   * Add message to buffer for batched sending
   */
  bufferMessage(connectionId: string, data: Buffer): boolean {
    if (this.backpressureActive.has(connectionId)) {
      return false; // Drop message due to backpressure
    }

    const buffer = this.messageBuffer.get(connectionId);
    if (!buffer) return false;

    buffer.push(data);

    // Force flush if buffer is full
    if (buffer.length >= this.config.maxBufferSize) {
      this.flushConnection(connectionId);
    }

    return true;
  }

  /**
   * Flush buffered messages for a connection
   */
  private flushConnection(connectionId: string): void {
    const buffer = this.messageBuffer.get(connectionId);
    if (!buffer || buffer.length === 0) return;

    const metrics = this.connectionMetrics.get(connectionId);
    if (!metrics) return;

    // Combine all buffered messages
    const combinedBuffer = Buffer.concat(buffer);
    buffer.length = 0; // Clear the buffer

    // Update metrics
    metrics.totalMessages += buffer.length;
    metrics.totalBytes += combinedBuffer.length;

    // Calculate per-second metrics
    const now = Date.now();
    const timeDiff = (now - metrics.lastResetTime) / 1000;
    if (timeDiff >= 1) {
      metrics.messagesPerSecond = metrics.totalMessages / timeDiff;
      metrics.bytesPerSecond = metrics.totalBytes / timeDiff;
      metrics.lastResetTime = now;
    }

    this.emit('message:flushed', connectionId, combinedBuffer.length);
  }

  /**
   * Start periodic buffer flushing
   */
  private startBufferFlushing(): void {
    this.flushInterval = setInterval(() => {
      for (const connectionId of this.messageBuffer.keys()) {
        this.flushConnection(connectionId);
      }
    }, this.config.flushInterval);
  }

  /**
   * Update connection metrics
   */
  updateMetrics(connectionId: string, messageSize: number): void {
    const metrics = this.connectionMetrics.get(connectionId);
    if (!metrics) return;

    metrics.totalMessages++;
    metrics.totalBytes += messageSize;

    // Update per-second metrics
    const now = Date.now();
    const timeDiff = (now - metrics.lastResetTime) / 1000;
    if (timeDiff >= 1) {
      metrics.messagesPerSecond = metrics.totalMessages / timeDiff;
      metrics.bytesPerSecond = metrics.totalBytes / timeDiff;
      metrics.lastResetTime = now;

      // Reset counters for next window
      metrics.totalMessages = 0;
      metrics.totalBytes = 0;
    }

    // Update memory usage estimate
    const buffer = this.messageBuffer.get(connectionId);
    if (buffer) {
      metrics.memoryUsage = buffer.reduce((sum, buf) => sum + buf.length, 0);
    }
  }

  /**
   * Get connection metrics
   */
  getConnectionMetrics(connectionId: string): ConnectionMetrics | undefined {
    return this.connectionMetrics.get(connectionId);
  }

  /**
   * Get aggregated metrics for all connections
   */
  getAggregatedMetrics(): {
    totalConnections: number;
    totalMessagesPerSecond: number;
    totalBytesPerSecond: number;
    averageConnectionTime: number;
    backpressureConnections: number;
    totalMemoryUsage: number;
  } {
    let totalMessagesPerSecond = 0;
    let totalBytesPerSecond = 0;
    let totalConnectionTime = 0;
    let totalMemoryUsage = 0;

    const now = Date.now();

    for (const metrics of this.connectionMetrics.values()) {
      totalMessagesPerSecond += metrics.messagesPerSecond;
      totalBytesPerSecond += metrics.bytesPerSecond;
      totalConnectionTime += now - metrics.connectionTime;
      totalMemoryUsage += metrics.memoryUsage;
    }

    return {
      totalConnections: this.connectionMetrics.size,
      totalMessagesPerSecond,
      totalBytesPerSecond,
      averageConnectionTime:
        totalConnectionTime / this.connectionMetrics.size || 0,
      backpressureConnections: this.backpressureActive.size,
      totalMemoryUsage,
    };
  }

  /**
   * Check if connection has backpressure
   */
  hasBackpressure(connectionId: string): boolean {
    return this.backpressureActive.has(connectionId);
  }

  /**
   * Clean up connection resources
   */
  cleanupConnection(connectionId: string): void {
    this.connectionMetrics.delete(connectionId);
    this.messageBuffer.delete(connectionId);
    this.backpressureActive.delete(connectionId);

    // Remove from any connection pools
    for (const pool of this.connectionPools.values()) {
      pool.delete(connectionId);
    }
  }

  /**
   * Get health status of connections
   */
  getHealthStatus(): {
    healthy: string[];
    degraded: string[];
    unhealthy: string[];
  } {
    const healthy: string[] = [];
    const degraded: string[] = [];
    const unhealthy: string[] = [];

    for (const [connectionId, metrics] of this.connectionMetrics) {
      if (this.backpressureActive.has(connectionId)) {
        unhealthy.push(connectionId);
      } else if (
        metrics.messagesPerSecond > 100 ||
        metrics.bytesPerSecond > 10240
      ) {
        degraded.push(connectionId);
      } else {
        healthy.push(connectionId);
      }
    }

    return { healthy, degraded, unhealthy };
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    if (this.flushInterval) {
      clearInterval(this.flushInterval);
    }

    this.connectionMetrics.clear();
    this.messageBuffer.clear();
    this.backpressureActive.clear();
    this.connectionPools.clear();
    this.removeAllListeners();
  }
}
