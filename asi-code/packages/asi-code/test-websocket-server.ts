/**
 * WebSocket Test Server
 * 
 * Simple test server to verify WebSocket functionality with wscat
 */

import { Hono } from 'hono';
import { serve } from '@hono/node-server';
import { createNodeWebSocket } from '@hono/node-ws';
import { nanoid } from 'nanoid';

const app = new Hono();

// Create WebSocket instance
const { injectWebSocket, upgradeWebSocket } = createNodeWebSocket({ app });

// Simple WebSocket echo server for testing
app.get('/ws', upgradeWebSocket((c) => {
  return {
    onOpen(event, ws) {
      console.log('WebSocket connection opened');
      
      // Send welcome message
      ws.send(JSON.stringify({
        id: nanoid(),
        type: 'connection:ready',
        timestamp: Date.now(),
        data: {
          connectionId: nanoid(),
          capabilities: ['messaging', 'channels', 'heartbeat'],
          maxMessageSize: 1024 * 1024,
          heartbeatInterval: 30000,
        },
      }));
    },
    
    onMessage(event, ws) {
      try {
        const message = JSON.parse(event.data.toString());
        console.log('Received message:', message);
        
        // Handle different message types
        switch (message.type) {
          case 'connection:ping':
            // Respond with pong
            ws.send(JSON.stringify({
              id: nanoid(),
              type: 'connection:pong',
              timestamp: Date.now(),
              data: {
                timestamp: Date.now(),
                latency: message.data?.timestamp ? Date.now() - message.data.timestamp : 0,
              },
            }));
            break;
            
          case 'channel:join':
            // Mock channel join success
            ws.send(JSON.stringify({
              id: nanoid(),
              type: 'channel:message',
              timestamp: Date.now(),
              data: {
                channel: message.data?.channel,
                message: {
                  type: 'member_joined',
                  connectionId: 'test-connection',
                },
                sender: 'system',
              },
            }));
            break;
            
          case 'ai:stream:start':
            // Mock AI streaming
            const { requestId } = message.data || {};
            
            // Send multiple chunks
            const chunks = [
              'Hello, ',
              'this is ',
              'a streaming ',
              'AI response ',
              'for testing ',
              'purposes.'
            ];
            
            chunks.forEach((chunk, index) => {
              setTimeout(() => {
                ws.send(JSON.stringify({
                  id: nanoid(),
                  type: 'ai:stream:chunk',
                  timestamp: Date.now(),
                  data: {
                    requestId,
                    chunk,
                    index,
                    finished: index === chunks.length - 1,
                  },
                }));
                
                // Send end message after last chunk
                if (index === chunks.length - 1) {
                  setTimeout(() => {
                    ws.send(JSON.stringify({
                      id: nanoid(),
                      type: 'ai:stream:end',
                      timestamp: Date.now(),
                      data: {
                        requestId,
                        totalChunks: chunks.length,
                        totalTokens: 100,
                        duration: 1000,
                      },
                    }));
                  }, 100);
                }
              }, index * 200);
            });
            break;
            
          case 'tool:execute:start':
            // Mock tool execution
            const { executionId, toolName } = message.data || {};
            
            // Send progress updates
            [25, 50, 75, 100].forEach((progress, index) => {
              setTimeout(() => {
                ws.send(JSON.stringify({
                  id: nanoid(),
                  type: 'tool:execute:progress',
                  timestamp: Date.now(),
                  data: {
                    executionId,
                    progress,
                    status: progress === 100 ? 'completed' : 'running',
                    output: `Progress: ${progress}%`,
                  },
                }));
                
                // Send result after completion
                if (progress === 100) {
                  setTimeout(() => {
                    ws.send(JSON.stringify({
                      id: nanoid(),
                      type: 'tool:execute:result',
                      timestamp: Date.now(),
                      data: {
                        executionId,
                        result: `Tool ${toolName} executed successfully`,
                        success: true,
                        duration: 1000,
                      },
                    }));
                  }, 100);
                }
              }, index * 250);
            });
            break;
            
          default:
            // Echo back unknown messages
            ws.send(JSON.stringify({
              id: nanoid(),
              type: 'echo',
              timestamp: Date.now(),
              data: {
                originalMessage: message,
                echo: true,
              },
            }));
        }
      } catch (error) {
        console.error('Error parsing message:', error);
        ws.send(JSON.stringify({
          id: nanoid(),
          type: 'connection:error',
          timestamp: Date.now(),
          data: {
            error: 'Invalid JSON message',
            code: 'INVALID_JSON',
          },
        }));
      }
    },
    
    onClose(event, ws) {
      console.log('WebSocket connection closed');
    },
    
    onError(event, ws) {
      console.error('WebSocket error:', event);
    },
  };
}));

// Status endpoint
app.get('/status', (c) => {
  return c.json({
    status: 'ok',
    websocket: {
      enabled: true,
      path: '/ws',
      features: [
        'echo',
        'heartbeat',
        'channels',
        'ai-streaming',
        'tool-execution'
      ],
    },
    timestamp: Date.now(),
  });
});

// Test endpoints for generating messages
app.post('/test/ping', (c) => {
  return c.json({
    message: 'Use wscat to send this message:',
    example: JSON.stringify({
      id: 'ping-test',
      type: 'connection:ping',
      timestamp: Date.now(),
      data: { timestamp: Date.now() },
    }),
  });
});

app.post('/test/ai-stream', (c) => {
  return c.json({
    message: 'Use wscat to send this message:',
    example: JSON.stringify({
      id: 'ai-stream-test',
      type: 'ai:stream:start',
      timestamp: Date.now(),
      data: {
        requestId: 'test-request-1',
        provider: 'anthropic',
        model: 'claude-3-sonnet',
        prompt: 'Hello, world!',
      },
    }),
  });
});

app.post('/test/tool-execution', (c) => {
  return c.json({
    message: 'Use wscat to send this message:',
    example: JSON.stringify({
      id: 'tool-execution-test',
      type: 'tool:execute:start',
      timestamp: Date.now(),
      data: {
        executionId: 'exec-test-1',
        toolName: 'bash',
        parameters: { command: 'echo "Hello World"' },
        sessionId: 'session-123',
      },
    }),
  });
});

const PORT = process.env.PORT || 3001;

console.log(`Starting WebSocket test server on port ${PORT}`);
console.log('WebSocket endpoint: ws://localhost:' + PORT + '/ws');
console.log('Status endpoint: http://localhost:' + PORT + '/status');
console.log('\nTest with wscat:');
console.log(`wscat -c ws://localhost:${PORT}/ws`);

const server = serve({
  fetch: app.fetch,
  port: Number(PORT),
});

// Inject WebSocket support
injectWebSocket(server);

console.log('\nExample messages to test:');
console.log('1. Ping test:');
console.log('{"id":"ping-1","type":"connection:ping","timestamp":' + Date.now() + ',"data":{"timestamp":' + Date.now() + '}}');
console.log('\n2. Channel join:');
console.log('{"id":"channel-1","type":"channel:join","timestamp":' + Date.now() + ',"data":{"channel":"test-room"}}');
console.log('\n3. AI stream test:');
console.log('{"id":"ai-1","type":"ai:stream:start","timestamp":' + Date.now() + ',"data":{"requestId":"req-1","provider":"anthropic","prompt":"Hello"}}');
console.log('\n4. Tool execution test:');
console.log('{"id":"tool-1","type":"tool:execute:start","timestamp":' + Date.now() + ',"data":{"executionId":"exec-1","toolName":"bash","parameters":{"command":"echo test"}}}');