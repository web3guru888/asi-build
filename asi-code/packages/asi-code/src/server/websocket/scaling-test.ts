#!/usr/bin/env node
/**
 * WebSocket Scaling Test
 * 
 * Load testing script to validate 10,000+ concurrent WebSocket connections
 * and monitor performance metrics, backpressure handling, and system health.
 */

import WebSocket from 'ws';
import { performance } from 'perf_hooks';

interface TestConfig {
  targetConnections: number;
  connectionRampUp: number; // connections per second
  testDuration: number; // milliseconds
  messageRate: number; // messages per second per connection
  messageSize: number; // bytes
  serverUrl: string;
}

interface TestMetrics {
  connectionsCreated: number;
  connectionsActive: number;
  connectionsFailed: number;
  messagesReceived: number;
  messagesSent: number;
  averageLatency: number;
  memoryUsage: number;
  errors: string[];
  startTime: number;
  endTime?: number;
}

class WebSocketScalingTest {
  private config: TestConfig;
  private connections: Map<string, WebSocket> = new Map();
  private metrics: TestMetrics;
  private testInterval?: NodeJS.Timeout;
  private monitoringInterval?: NodeJS.Timeout;
  private startTime: number = 0;

  constructor(config: Partial<TestConfig> = {}) {
    this.config = {
      targetConnections: 10000,
      connectionRampUp: 100, // 100 connections per second
      testDuration: 300000, // 5 minutes
      messageRate: 1, // 1 message per second per connection
      messageSize: 1024, // 1KB messages
      serverUrl: 'ws://localhost:3000/ws',
      ...config,
    };

    this.metrics = {
      connectionsCreated: 0,
      connectionsActive: 0,
      connectionsFailed: 0,
      messagesReceived: 0,
      messagesSent: 0,
      averageLatency: 0,
      memoryUsage: 0,
      errors: [],
      startTime: Date.now(),
    };

    console.log('🚀 WebSocket Scaling Test Configuration:');
    console.log(`   Target Connections: ${this.config.targetConnections.toLocaleString()}`);
    console.log(`   Connection Ramp-up: ${this.config.connectionRampUp}/sec`);
    console.log(`   Test Duration: ${this.config.testDuration / 1000}s`);
    console.log(`   Message Rate: ${this.config.messageRate}/sec per connection`);
    console.log(`   Message Size: ${this.config.messageSize} bytes`);
    console.log(`   Server URL: ${this.config.serverUrl}`);
    console.log('');
  }

  /**
   * Start the scaling test
   */
  async start(): Promise<TestMetrics> {
    console.log('🎬 Starting WebSocket scaling test...\n');
    this.startTime = performance.now();
    this.metrics.startTime = Date.now();

    // Start connection ramp-up
    await this.rampUpConnections();

    // Start message sending
    this.startMessageLoop();

    // Start monitoring
    this.startMonitoring();

    // Wait for test duration
    await this.waitForTestCompletion();

    // Cleanup and return results
    return this.cleanup();
  }

  /**
   * Gradually create connections at the specified rate
   */
  private async rampUpConnections(): Promise<void> {
    const rampUpInterval = 1000 / this.config.connectionRampUp; // milliseconds between connections
    let connectionsToCreate = this.config.targetConnections;

    console.log(`📈 Ramping up ${this.config.targetConnections.toLocaleString()} connections at ${this.config.connectionRampUp}/sec...\n`);

    return new Promise((resolve) => {
      const createConnection = () => {
        if (connectionsToCreate <= 0) {
          console.log(`✅ Connection ramp-up complete: ${this.connections.size.toLocaleString()} connections\n`);
          resolve();
          return;
        }

        this.createConnection()
          .then(() => {
            connectionsToCreate--;
            if (connectionsToCreate % 1000 === 0) {
              console.log(`   Created ${(this.config.targetConnections - connectionsToCreate).toLocaleString()}/${this.config.targetConnections.toLocaleString()} connections`);
            }
          })
          .catch((error) => {
            this.metrics.connectionsFailed++;
            this.metrics.errors.push(`Connection failed: ${error.message}`);
          });

        if (connectionsToCreate > 0) {
          setTimeout(createConnection, rampUpInterval);
        }
      };

      createConnection();
    });
  }

  /**
   * Create a single WebSocket connection
   */
  private async createConnection(): Promise<void> {
    return new Promise((resolve, reject) => {
      const connectionId = `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const ws = new WebSocket(this.config.serverUrl);
      
      const connectionTimeout = setTimeout(() => {
        ws.terminate();
        reject(new Error('Connection timeout'));
      }, 30000); // 30 second timeout

      ws.on('open', () => {
        clearTimeout(connectionTimeout);
        this.connections.set(connectionId, ws);
        this.metrics.connectionsCreated++;
        this.metrics.connectionsActive++;

        // Send initial ready message
        ws.send(JSON.stringify({
          id: `${connectionId}_ready`,
          type: 'connection:ping',
          timestamp: Date.now(),
        }));

        resolve();
      });

      ws.on('message', (data) => {
        this.handleMessage(connectionId, data);
      });

      ws.on('close', () => {
        this.connections.delete(connectionId);
        this.metrics.connectionsActive--;
      });

      ws.on('error', (error) => {
        clearTimeout(connectionTimeout);
        this.metrics.errors.push(`Connection error ${connectionId}: ${error.message}`);
        reject(error);
      });
    });
  }

  /**
   * Handle incoming WebSocket message
   */
  private handleMessage(connectionId: string, data: Buffer): void {
    try {
      const message = JSON.parse(data.toString());
      this.metrics.messagesReceived++;

      // Calculate latency if message has timestamp
      if (message.timestamp) {
        const latency = Date.now() - message.timestamp;
        // Simple moving average for latency
        this.metrics.averageLatency = 
          (this.metrics.averageLatency * (this.metrics.messagesReceived - 1) + latency) / this.metrics.messagesReceived;
      }
    } catch (error) {
      this.metrics.errors.push(`Message parse error: ${error.message}`);
    }
  }

  /**
   * Start the message sending loop
   */
  private startMessageLoop(): void {
    const messageInterval = 1000 / this.config.messageRate; // milliseconds between messages

    this.testInterval = setInterval(() => {
      this.sendMessagesToAllConnections();
    }, messageInterval);

    console.log(`💬 Started message loop: ${this.config.messageRate} messages/sec per connection\n`);
  }

  /**
   * Send test messages to all active connections
   */
  private sendMessagesToAllConnections(): void {
    const messagePayload = 'x'.repeat(this.config.messageSize - 100); // Reserve space for metadata
    
    for (const [connectionId, ws] of this.connections) {
      if (ws.readyState === WebSocket.OPEN) {
        const message = {
          id: `${connectionId}_${Date.now()}`,
          type: 'test:message',
          timestamp: Date.now(),
          payload: messagePayload,
        };

        try {
          ws.send(JSON.stringify(message));
          this.metrics.messagesSent++;
        } catch (error) {
          this.metrics.errors.push(`Send error ${connectionId}: ${error.message}`);
        }
      }
    }
  }

  /**
   * Start performance monitoring
   */
  private startMonitoring(): void {
    this.monitoringInterval = setInterval(() => {
      this.updateMetrics();
      this.printStatus();
    }, 5000); // Every 5 seconds

    console.log('📊 Started performance monitoring (updates every 5s)\n');
  }

  /**
   * Update performance metrics
   */
  private updateMetrics(): void {
    const memUsage = process.memoryUsage();
    this.metrics.memoryUsage = memUsage.heapUsed / 1024 / 1024; // MB
  }

  /**
   * Print current test status
   */
  private printStatus(): void {
    const elapsed = Math.floor((performance.now() - this.startTime) / 1000);
    const remaining = Math.max(0, Math.floor(this.config.testDuration / 1000) - elapsed);

    console.log(`📊 Status Update (${elapsed}s elapsed, ${remaining}s remaining):`);
    console.log(`   Active Connections: ${this.metrics.connectionsActive.toLocaleString()}`);
    console.log(`   Messages Sent: ${this.metrics.messagesSent.toLocaleString()}`);
    console.log(`   Messages Received: ${this.metrics.messagesReceived.toLocaleString()}`);
    console.log(`   Average Latency: ${this.metrics.averageLatency.toFixed(2)}ms`);
    console.log(`   Memory Usage: ${this.metrics.memoryUsage.toFixed(2)}MB`);
    console.log(`   Error Count: ${this.metrics.errors.length}`);
    console.log('');

    // Check server health if available
    this.checkServerHealth();
  }

  /**
   * Check server health via API
   */
  private async checkServerHealth(): Promise<void> {
    try {
      const healthUrl = this.config.serverUrl.replace('ws://', 'http://').replace('/ws', '/api/websocket/health');
      const response = await fetch(healthUrl);
      const health = await response.json();

      if (health && health.overallStatus) {
        console.log(`🏥 Server Health: ${health.overallStatus} (${health.totalConnections || 0} server-side connections)`);
        
        if (health.overallStatus === 'critical' || health.overallStatus === 'unhealthy') {
          console.warn('⚠️  Server is reporting health issues!');
        }
      }
    } catch (error) {
      // Ignore health check errors to avoid spamming logs
    }
  }

  /**
   * Wait for test completion
   */
  private async waitForTestCompletion(): Promise<void> {
    return new Promise((resolve) => {
      setTimeout(() => {
        console.log('⏰ Test duration reached, beginning cleanup...\n');
        resolve();
      }, this.config.testDuration);
    });
  }

  /**
   * Cleanup and return final results
   */
  private cleanup(): TestMetrics {
    // Clear intervals
    if (this.testInterval) clearInterval(this.testInterval);
    if (this.monitoringInterval) clearInterval(this.monitoringInterval);

    // Close all connections
    console.log('🧹 Closing all connections...');
    for (const ws of this.connections.values()) {
      ws.terminate();
    }

    this.metrics.endTime = Date.now();
    const totalDuration = (performance.now() - this.startTime) / 1000;

    console.log('\n🏁 Test completed!\n');
    console.log('📋 Final Results:');
    console.log(`   Test Duration: ${totalDuration.toFixed(2)}s`);
    console.log(`   Target Connections: ${this.config.targetConnections.toLocaleString()}`);
    console.log(`   Connections Created: ${this.metrics.connectionsCreated.toLocaleString()}`);
    console.log(`   Connections Failed: ${this.metrics.connectionsFailed.toLocaleString()}`);
    console.log(`   Success Rate: ${((this.metrics.connectionsCreated / this.config.targetConnections) * 100).toFixed(2)}%`);
    console.log(`   Messages Sent: ${this.metrics.messagesSent.toLocaleString()}`);
    console.log(`   Messages Received: ${this.metrics.messagesReceived.toLocaleString()}`);
    console.log(`   Message Success Rate: ${this.metrics.messagesSent > 0 ? ((this.metrics.messagesReceived / this.metrics.messagesSent) * 100).toFixed(2) : 0}%`);
    console.log(`   Average Latency: ${this.metrics.averageLatency.toFixed(2)}ms`);
    console.log(`   Peak Memory Usage: ${this.metrics.memoryUsage.toFixed(2)}MB`);
    console.log(`   Total Errors: ${this.metrics.errors.length}`);
    
    if (this.metrics.errors.length > 0) {
      console.log('\n❌ Errors encountered:');
      const uniqueErrors = [...new Set(this.metrics.errors)];
      uniqueErrors.slice(0, 10).forEach(error => console.log(`   - ${error}`));
      if (uniqueErrors.length > 10) {
        console.log(`   ... and ${uniqueErrors.length - 10} more unique errors`);
      }
    }

    console.log('');
    return this.metrics;
  }
}

// CLI execution
if (require.main === module) {
  const args = process.argv.slice(2);
  const config: Partial<TestConfig> = {};

  // Parse CLI arguments
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i]?.replace('--', '');
    const value = args[i + 1];
    
    if (key && value) {
      switch (key) {
        case 'connections':
          config.targetConnections = parseInt(value);
          break;
        case 'rampup':
          config.connectionRampUp = parseInt(value);
          break;
        case 'duration':
          config.testDuration = parseInt(value) * 1000;
          break;
        case 'message-rate':
          config.messageRate = parseInt(value);
          break;
        case 'message-size':
          config.messageSize = parseInt(value);
          break;
        case 'server':
          config.serverUrl = value;
          break;
      }
    }
  }

  // Run the test
  const test = new WebSocketScalingTest(config);
  test.start()
    .then((results) => {
      process.exit(results.connectionsFailed > results.connectionsCreated * 0.1 ? 1 : 0);
    })
    .catch((error) => {
      console.error('💥 Test failed:', error);
      process.exit(1);
    });
}

export { WebSocketScalingTest, TestConfig, TestMetrics };