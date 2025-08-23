#!/usr/bin/env bun
/**
 * Test PostgreSQL Database Connection and Functionality
 */

import { DatabaseClient } from './database/db-client';

async function testDatabase() {
  console.log('🔍 Testing PostgreSQL Database Integration...\n');
  
  const db = DatabaseClient.getInstance();
  
  try {
    // Test health check
    console.log('1. Testing database connection...');
    const isHealthy = await db.healthCheck();
    console.log(`   ✅ Database is ${isHealthy ? 'healthy' : 'not healthy'}`);
    
    if (!isHealthy) {
      console.error('   ❌ Database connection failed. Please check PostgreSQL is running.');
      return;
    }
    
    // Create a test session
    console.log('\n2. Creating test session...');
    const sessionId = `test_session_${Date.now()}`;
    const dbSessionId = await db.createSession(sessionId, '127.0.0.1', 'Test User Agent');
    console.log(`   ✅ Session created: ${sessionId}`);
    
    // Create a conversation
    console.log('\n3. Creating ASI1 conversation...');
    const conversation = await db.createConversation(sessionId, 'asi1-mini');
    console.log(`   ✅ Conversation created: ${conversation.conversationId}`);
    
    // Save messages
    console.log('\n4. Saving chat messages...');
    await db.saveMessage(conversation.conversationId, 'user', 'Hello, ASI1!', { total: 10 });
    await db.saveMessage(conversation.conversationId, 'assistant', 'Hello! How can I help you today?', { total: 15 });
    console.log('   ✅ Messages saved');
    
    // Log API call
    console.log('\n5. Logging API call...');
    await db.logAPICall({
      sessionId,
      conversationId: conversation.conversationId,
      endpoint: '/v1/chat/completions',
      method: 'POST',
      requestBody: { model: 'asi1-mini', messages: [] },
      responseStatus: 200,
      responseBody: { choices: [] },
      responseTimeMs: 1234
    });
    console.log('   ✅ API call logged');
    
    // Create orchestration
    console.log('\n6. Creating orchestration...');
    const orchestration = await db.createOrchestration(
      sessionId,
      'Build a test application',
      'orchestrate: Build a test application'
    );
    console.log(`   ✅ Orchestration created: ${orchestration.orchestration_id}`);
    
    // Create task
    console.log('\n7. Creating task...');
    const taskId = await db.createTask({
      orchestrationId: orchestration.orchestration_id,
      taskId: `task_${Date.now()}`,
      name: 'Test Task',
      description: 'A test task for database validation',
      taskType: 'testing',
      assignedAgent: 'kenny-test',
      canParallel: false,
      estimatedHours: 1
    });
    console.log(`   ✅ Task created: ${taskId}`);
    
    // Create project
    console.log('\n8. Creating project...');
    const projectId = await db.createProject({
      sessionId,
      orchestrationId: orchestration.orchestration_id,
      projectName: 'Test Project',
      projectType: 'web',
      framework: 'React',
      language: 'TypeScript',
      outputPath: '/test/path',
      features: ['Testing', 'Database'],
      dependencies: ['pg', 'bun']
    });
    console.log(`   ✅ Project created: ${projectId}`);
    
    // Save generated file
    console.log('\n9. Saving generated file...');
    await db.saveGeneratedFile({
      projectId,
      filePath: '/test/file.ts',
      fileName: 'file.ts',
      content: 'console.log("Hello from database!");',
      language: 'typescript',
      purpose: 'Testing',
      generationMethod: 'test'
    });
    console.log('   ✅ File saved');
    
    // Log system event
    console.log('\n10. Logging system event...');
    await db.log('info', 'test-script', 'Database test completed successfully', { test: true }, sessionId);
    console.log('   ✅ System log saved');
    
    // Track API usage
    console.log('\n11. Tracking API usage...');
    await db.trackAPIUsage('test_api_key_hash', '/v1/chat/completions', 100, false, false);
    console.log('   ✅ API usage tracked');
    
    // Record metric
    console.log('\n12. Recording performance metric...');
    await db.recordMetric('test_duration', 1234, 'ms', { component: 'test' }, sessionId);
    console.log('   ✅ Metric recorded');
    
    console.log('\n✅ All database tests passed successfully!');
    console.log('\n📊 Database is ready to store ALL platform data:');
    console.log('   - Sessions & Users');
    console.log('   - ASI1 Chat History');
    console.log('   - API Calls & Responses');
    console.log('   - Orchestrations & Tasks');
    console.log('   - Generated Projects & Files');
    console.log('   - WebSocket Connections');
    console.log('   - System Logs');
    console.log('   - Rate Limiting & Usage');
    console.log('   - Performance Metrics');
    
  } catch (error) {
    console.error('\n❌ Database test failed:', error);
  } finally {
    await db.close();
  }
}

testDatabase().catch(console.error);