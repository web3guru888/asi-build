/**
 * Simple WebSocket Test Server
 * 
 * Basic WebSocket server using the ws library directly to test our implementation
 */

import { WebSocketServer } from 'ws';
import { nanoid } from 'nanoid';
import type { WSMessage } from './src/server/websocket/types.js';

const PORT = process.env.PORT || 3001;

const wss = new WebSocketServer({ 
  port: Number(PORT),
  path: '/ws'
});

console.log(`WebSocket server running on ws://localhost:${PORT}/ws`);
console.log('Test with wscat: wscat -c ws://localhost:' + PORT + '/ws');

wss.on('connection', (ws) => {
  console.log('New WebSocket connection');
  
  // Send welcome message
  const welcomeMessage: WSMessage = {
    id: nanoid(),
    type: 'connection:ready',
    timestamp: Date.now(),
    data: {
      connectionId: nanoid(),
      capabilities: ['messaging', 'channels', 'heartbeat', 'ai-streaming', 'tool-execution'],
      maxMessageSize: 1024 * 1024,
      heartbeatInterval: 30000,
    },
  };
  
  ws.send(JSON.stringify(welcomeMessage));
  
  ws.on('message', (data) => {
    try {
      const message: WSMessage = JSON.parse(data.toString());
      console.log('Received message:', message.type, message.id);
      
      // Handle different message types
      switch (message.type) {
        case 'connection:ping':
          // Respond with pong
          const pongMessage: WSMessage = {
            id: nanoid(),
            type: 'connection:pong',
            timestamp: Date.now(),
            data: {
              timestamp: Date.now(),
              latency: message.data?.timestamp ? Date.now() - message.data.timestamp : 0,
            },
          };
          ws.send(JSON.stringify(pongMessage));
          break;
          
        case 'channel:join':
          // Mock channel join success
          const channelJoinMessage: WSMessage = {
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
          };
          ws.send(JSON.stringify(channelJoinMessage));
          break;
          
        case 'ai:stream:start':
          // Mock AI streaming
          const { requestId } = message.data || {};
          console.log('Starting AI stream for request:', requestId);
          
          // Send multiple chunks
          const chunks = [
            'Hello, ',
            'this is ',
            'a streaming ',
            'AI response ',
            'for testing ',
            'WebSocket ',
            'real-time ',
            'communication. ',
            'Each chunk ',
            'is sent ',
            'separately ',
            'to simulate ',
            'streaming ',
            'from an ',
            'AI model.'
          ];
          
          chunks.forEach((chunk, index) => {
            setTimeout(() => {
              const chunkMessage: WSMessage = {
                id: nanoid(),
                type: 'ai:stream:chunk',
                timestamp: Date.now(),
                data: {
                  requestId,
                  chunk,
                  index,
                  finished: false,
                },
              };
              ws.send(JSON.stringify(chunkMessage));
              
              // Send end message after last chunk
              if (index === chunks.length - 1) {
                setTimeout(() => {
                  const endMessage: WSMessage = {
                    id: nanoid(),
                    type: 'ai:stream:end',
                    timestamp: Date.now(),
                    data: {
                      requestId,
                      totalChunks: chunks.length,
                      totalTokens: 150,
                      duration: chunks.length * 200,
                    },
                  };
                  ws.send(JSON.stringify(endMessage));
                }, 100);
              }
            }, index * 200);
          });
          break;
          
        case 'tool:execute:start':
          // Mock tool execution
          const { executionId, toolName, parameters } = message.data || {};
          console.log('Starting tool execution:', toolName, executionId);
          
          // Send progress updates
          const progressSteps = [10, 25, 50, 75, 90, 100];
          progressSteps.forEach((progress, index) => {
            setTimeout(() => {
              const progressMessage: WSMessage = {
                id: nanoid(),
                type: 'tool:execute:progress',
                timestamp: Date.now(),
                data: {
                  executionId,
                  progress,
                  status: progress === 100 ? 'completed' : 'running',
                  output: `Executing ${toolName}... ${progress}%`,
                  stage: progress < 50 ? 'initializing' : progress < 100 ? 'processing' : 'finalizing',
                },
              };
              ws.send(JSON.stringify(progressMessage));
              
              // Send result after completion
              if (progress === 100) {
                setTimeout(() => {
                  const resultMessage: WSMessage = {
                    id: nanoid(),
                    type: 'tool:execute:result',
                    timestamp: Date.now(),
                    data: {
                      executionId,
                      result: {
                        output: `Tool ${toolName} executed successfully with parameters: ${JSON.stringify(parameters)}`,
                        exitCode: 0,
                        stdout: `Hello from ${toolName}!\n`,
                        stderr: '',
                      },
                      success: true,
                      duration: progressSteps.length * 300,
                    },
                  };
                  ws.send(JSON.stringify(resultMessage));
                }, 100);
              }
            }, index * 300);
          });
          break;
          
        case 'subscription:subscribe':
          // Mock subscription success
          const subscribeMessage: WSMessage = {
            id: nanoid(),
            type: 'subscription:event',
            timestamp: Date.now(),
            data: {
              event: message.data?.event,
              payload: {
                message: `Subscribed to ${message.data?.event}`,
                timestamp: Date.now(),
              },
              source: 'system',
            },
          };
          ws.send(JSON.stringify(subscribeMessage));
          break;
          
        default:
          // Echo back unknown messages
          const echoMessage: WSMessage = {
            id: nanoid(),
            type: 'echo',
            timestamp: Date.now(),
            data: {
              originalMessage: message,
              echo: true,
              server: 'simple-websocket-test',
            },
          };
          ws.send(JSON.stringify(echoMessage));
      }
    } catch (error) {
      console.error('Error parsing message:', error);
      const errorMessage: WSMessage = {
        id: nanoid(),
        type: 'connection:error',
        timestamp: Date.now(),
        data: {
          error: 'Invalid JSON message',
          code: 'INVALID_JSON',
          timestamp: Date.now(),
        },
      };
      ws.send(JSON.stringify(errorMessage));
    }
  });
  
  ws.on('close', () => {
    console.log('WebSocket connection closed');
  });
  
  ws.on('error', (error) => {
    console.error('WebSocket error:', error);
  });
  
  // Send periodic heartbeat
  const heartbeatInterval = setInterval(() => {
    if (ws.readyState === ws.OPEN) {
      const heartbeatMessage: WSMessage = {
        id: nanoid(),
        type: 'system:status',
        timestamp: Date.now(),
        data: {
          status: 'healthy',
          components: {
            websocket: {
              status: 'healthy',
              connections: wss.clients.size,
            },
          },
          timestamp: Date.now(),
        },
      };
      ws.send(JSON.stringify(heartbeatMessage));
    } else {
      clearInterval(heartbeatInterval);
    }
  }, 30000); // 30 seconds
});

wss.on('error', (error) => {
  console.error('WebSocket Server error:', error);
});

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down WebSocket server...');
  wss.close(() => {
    console.log('WebSocket server closed');
    process.exit(0);
  });
});

console.log('\nExample messages to test:');
console.log('\n1. Ping test:');
console.log('{"id":"ping-1","type":"connection:ping","timestamp":' + Date.now() + ',"data":{"timestamp":' + Date.now() + '}}');
console.log('\n2. Channel join:');
console.log('{"id":"channel-1","type":"channel:join","timestamp":' + Date.now() + ',"data":{"channel":"test-room"}}');
console.log('\n3. AI stream test:');
console.log('{"id":"ai-1","type":"ai:stream:start","timestamp":' + Date.now() + ',"data":{"requestId":"req-1","provider":"anthropic","prompt":"Hello"}}');
console.log('\n4. Tool execution test:');
console.log('{"id":"tool-1","type":"tool:execute:start","timestamp":' + Date.now() + ',"data":{"executionId":"exec-1","toolName":"bash","parameters":{"command":"echo test"}}}');
console.log('\n5. Subscription test:');
console.log('{"id":"sub-1","type":"subscription:subscribe","timestamp":' + Date.now() + ',"data":{"event":"user-activity"}}');
console.log('\n6. Echo test:');
console.log('{"id":"echo-1","type":"custom:message","timestamp":' + Date.now() + ',"data":{"message":"Hello WebSocket!"}}');