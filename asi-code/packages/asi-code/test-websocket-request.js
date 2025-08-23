#!/usr/bin/env node
/**
 * Test WebSocket request to verify IntelligentGenerator is working
 */

import WebSocket from 'ws';

const ws = new WebSocket('ws://localhost:3333/ws');

ws.on('open', () => {
  console.log('Connected to WebSocket server');
  
  // Send orchestration request
  const message = {
    type: 'command',
    data: 'orchestrate: Build a simple React dashboard with charts',
    message: 'orchestrate: Build a simple React dashboard with charts'
  };
  
  console.log('Sending:', message);
  ws.send(JSON.stringify(message));
});

ws.on('message', (data) => {
  const msg = JSON.parse(data.toString());
  console.log('Received:', msg.type);
  
  if (msg.type === 'orchestration-completed') {
    console.log('\n✅ Orchestration completed!');
    console.log('Output path:', msg.outputPath);
    console.log('Files generated:', msg.filesGenerated);
    ws.close();
  } else if (msg.type === 'error') {
    console.error('\n❌ Error:', msg.message);
    ws.close();
  } else if (msg.type === 'code-generation') {
    console.log('📝', msg.message);
  }
});

ws.on('error', (error) => {
  console.error('WebSocket error:', error);
});

ws.on('close', () => {
  console.log('Connection closed');
  process.exit(0);
});

// Timeout after 30 seconds
setTimeout(() => {
  console.log('Timeout - closing connection');
  ws.close();
  process.exit(1);
}, 30000);