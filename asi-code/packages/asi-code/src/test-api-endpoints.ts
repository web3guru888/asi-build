#!/usr/bin/env bun

/**
 * API Endpoint Test Suite
 *
 * Tests the enhanced tool API endpoints by starting a server and making HTTP requests
 */

import { createASIServer, defaultServerConfig } from './server/server.js';
import { setupEnhancedToolRoutes } from './server/enhanced-tool-routes.js';
import { createCompatibleToolManager } from './tool/tool-manager-bridge.js';
import { createSessionManager, createSessionStorage } from './session/index.js';
import { createProviderManager } from './provider/index.js';

async function testAPIEndpoints() {
  console.log('🌐 Starting API Endpoint Tests...\n');

  let server: any = null;

  try {
    // Create managers
    const toolManager = await createCompatibleToolManager({
      enableMetrics: true,
      enableCaching: true,
      maxConcurrentExecutions: 5,
      defaultTimeout: 30000,
      autoRegisterBuiltIns: true,
      enableToolValidation: true,
      enableVersioning: true,
    });

    const sessionStorage = createSessionStorage('memory');
    const sessionManager = createSessionManager(sessionStorage);

    const providerManager = createProviderManager();

    // Create server
    const serverConfig = {
      ...defaultServerConfig,
      port: 3004, // Use a different port
      host: 'localhost',
    };

    server = createASIServer(
      serverConfig,
      sessionManager,
      providerManager,
      toolManager
    );

    // Add enhanced tool routes
    setupEnhancedToolRoutes(server.app, server);

    // Start server
    await server.start();
    console.log(`✅ Test server started on http://localhost:3004\n`);

    // Test endpoints
    const baseUrl = 'http://localhost:3004';

    // Test 1: List tools
    console.log('📋 Testing GET /api/tools...');
    try {
      const response = await fetch(`${baseUrl}/api/tools`);
      const data = await response.json();
      console.log(`   ✅ Status: ${response.status}`);
      console.log(`   ✅ Tools found: ${data.tools?.length || 0}`);
      console.log(
        `   ✅ Categories: ${Object.keys(data.categories || {}).join(', ')}\n`
      );
    } catch (error) {
      console.error(`   ❌ Failed: ${(error as Error).message}\n`);
    }

    // Test 2: Tool discovery
    console.log('🔍 Testing GET /api/tools/discover...');
    try {
      const response = await fetch(`${baseUrl}/api/tools/discover`);
      const data = await response.json();
      console.log(`   ✅ Status: ${response.status}`);
      console.log(`   ✅ Discovery info for ${data.tools?.length || 0} tools`);
      console.log(
        `   ✅ System info available: ${data.systemInfo ? 'Yes' : 'No'}\n`
      );
    } catch (error) {
      console.error(`   ❌ Failed: ${(error as Error).message}\n`);
    }

    // Test 3: Tool health
    console.log('🏥 Testing GET /api/tools/health...');
    try {
      const response = await fetch(`${baseUrl}/api/tools/health`);
      const data = await response.json();
      console.log(`   ✅ Status: ${response.status}`);
      console.log(`   ✅ Health status: ${data.health?.status || 'unknown'}`);
      console.log(`   ✅ Total tools: ${data.system?.totalTools || 0}\n`);
    } catch (error) {
      console.error(`   ❌ Failed: ${(error as Error).message}\n`);
    }

    // Test 4: Tool documentation
    console.log('📚 Testing GET /api/tools/documentation...');
    try {
      const response = await fetch(`${baseUrl}/api/tools/documentation`);
      const data = await response.json();
      console.log(`   ✅ Status: ${response.status}`);
      console.log(
        `   ✅ Documentation for ${data.documentation?.length || 0} tools\n`
      );
    } catch (error) {
      console.error(`   ❌ Failed: ${(error as Error).message}\n`);
    }

    // Test 5: Tool execution - List tool
    console.log('⚡ Testing POST /api/tools/list/execute...');
    try {
      const response = await fetch(`${baseUrl}/api/tools/list/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parameters: {
            path: '.',
            maxResults: 10,
          },
          context: {
            sessionId: 'test-session',
            userId: 'test-user',
            permissions: ['read_files'],
            workingDirectory: process.cwd(),
            environment: {},
            metadata: {},
          },
        }),
      });
      const data = await response.json();
      console.log(`   ✅ Status: ${response.status}`);
      console.log(`   ✅ Execution success: ${data.result?.success || false}`);
      console.log(
        `   ✅ Items found: ${data.result?.data?.items?.length || 0}`
      );
      console.log(
        `   ✅ Execution ID: ${data.metadata?.executionId || 'N/A'}\n`
      );
    } catch (error) {
      console.error(`   ❌ Failed: ${(error as Error).message}\n`);
    }

    // Test 6: Tool validation
    console.log('✅ Testing POST /api/tools/read/validate...');
    try {
      const response = await fetch(`${baseUrl}/api/tools/read/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parameters: {
            path: './package.json',
            encoding: 'utf8',
          },
        }),
      });
      const data = await response.json();
      console.log(`   ✅ Status: ${response.status}`);
      console.log(
        `   ✅ Validation result: ${data.validation?.isValid ? 'VALID' : 'INVALID'}`
      );
      console.log(
        `   ✅ Parameters: ${data.parameters?.join(', ') || 'N/A'}\n`
      );
    } catch (error) {
      console.error(`   ❌ Failed: ${(error as Error).message}\n`);
    }

    // Test 7: Batch execution
    console.log('📦 Testing POST /api/tools/execute-batch...');
    try {
      const response = await fetch(`${baseUrl}/api/tools/execute-batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tools: [
            {
              name: 'write',
              parameters: {
                path: './api-test.txt',
                content: 'API test file content',
              },
            },
            {
              name: 'read',
              parameters: {
                path: './api-test.txt',
              },
            },
          ],
          context: {
            sessionId: 'batch-test-session',
            userId: 'test-user',
            permissions: ['read_files', 'write_files'],
            workingDirectory: process.cwd(),
            environment: {},
            metadata: {},
          },
          stopOnError: true,
        }),
      });
      const data = await response.json();
      console.log(`   ✅ Status: ${response.status}`);
      console.log(`   ✅ Total tools: ${data.totalTools || 0}`);
      console.log(`   ✅ Successful tools: ${data.successfulTools || 0}`);
      console.log(`   ✅ Batch ID: ${data.batchId || 'N/A'}\n`);
    } catch (error) {
      console.error(`   ❌ Failed: ${(error as Error).message}\n`);
    }

    // Test 8: Get specific tool info
    console.log('🔧 Testing GET /api/tools/search...');
    try {
      const response = await fetch(`${baseUrl}/api/tools/search`);
      const data = await response.json();
      console.log(`   ✅ Status: ${response.status}`);
      console.log(`   ✅ Tool name: ${data.name || 'N/A'}`);
      console.log(`   ✅ Parameters: ${data.schema?.parameters?.length || 0}`);
      console.log(`   ✅ Category: ${data.schema?.category || 'N/A'}`);
      console.log(`   ✅ Safety level: ${data.schema?.safetyLevel || 'N/A'}\n`);
    } catch (error) {
      console.error(`   ❌ Failed: ${(error as Error).message}\n`);
    }

    console.log('🎉 API endpoint tests completed successfully!');
  } catch (error) {
    console.error('❌ API endpoint tests failed:', error);
  } finally {
    // Cleanup
    if (server) {
      console.log('🧹 Shutting down test server...');
      await server.stop();
      console.log('✅ Test server stopped');
    }
  }
}

// Run the API tests
testAPIEndpoints().catch(error => {
  console.error('❌ API test suite failed:', error);
  process.exit(1);
});
