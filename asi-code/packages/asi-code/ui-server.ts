#!/usr/bin/env bun

import { Hono } from 'hono';
import { serve } from 'bun';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const app = new Hono();

// Enable CORS for all origins - this is crucial for the UI to work
app.use('*', async (c, next) => {
  c.header('Access-Control-Allow-Origin', '*');
  c.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  c.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  c.header('Access-Control-Max-Age', '86400');
  
  if (c.req.method === 'OPTIONS') {
    return c.text('', 204);
  }
  
  await next();
});

// Serve the UI
app.get('/', (c) => {
  const uiPath = join(process.cwd(), 'public', 'index.html');
  if (existsSync(uiPath)) {
    const html = readFileSync(uiPath, 'utf-8');
    return c.html(html);
  }
  return c.text('UI not found', 404);
});

// Serve favicon
app.get('/favicon.ico', (c) => {
  return c.text('🚀', 200);
});

// Proxy health endpoint with CORS
app.get('/health', async (c) => {
  try {
    const response = await fetch('http://localhost:3000/health');
    const data = await response.json();
    return c.json(data);
  } catch (error) {
    return c.json({ 
      status: 'error', 
      message: 'Cannot connect to ASI-Code server on port 3000',
      timestamp: new Date().toISOString()
    });
  }
});

// Proxy API endpoints with CORS
app.all('/api/*', async (c) => {
  const path = c.req.path;
  const method = c.req.method;
  const body = method !== 'GET' ? await c.req.text() : undefined;
  
  try {
    const response = await fetch(`http://localhost:3000${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body
    });
    
    const data = await response.json();
    return c.json(data);
  } catch (error) {
    return c.json({ 
      status: 'error', 
      message: `Cannot proxy request to ASI-Code server`,
      path,
      error: error.message
    }, 500);
  }
});

const port = 8090;
console.log(`🎨 ASI-Code UI Server with CORS Proxy`);
console.log(`📡 UI: http://localhost:${port}`);
console.log(`🔗 Proxying API requests to: http://localhost:3000`);
console.log(`✅ CORS enabled for all origins\n`);

serve({
  fetch: app.fetch,
  port
});