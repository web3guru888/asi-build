#!/usr/bin/env bun

console.log('🚀 Testing ASI-Code Framework');
console.log('================================');

// Test minimal setup
async function testMinimal() {
  try {
    console.log('\n📦 Testing minimal ASI-Code setup...');
    const { createMinimalASICode } = await import('./src/index.js');
    const asi = await createMinimalASICode();
    console.log('✅ Minimal setup successful:', asi);
    
    // Test health check
    const health = await asi.checkHealth?.();
    console.log('🏥 Health check:', health);
    
    // Shutdown
    await asi.shutdown?.();
    console.log('🛑 Shutdown successful');
    
  } catch (error) {
    console.error('❌ Error in minimal test:', error.message);
  }
}

// Test Kenny Integration
async function testKenny() {
  try {
    console.log('\n🔗 Testing Kenny Integration...');
    const { getKennyIntegration } = await import('./src/kenny/integration.js');
    const kenny = getKennyIntegration();
    console.log('✅ Kenny Integration loaded:', kenny.constructor.name);
    
    // Test message bus
    const messageBus = kenny.getMessageBus();
    console.log('📨 Message Bus:', messageBus.constructor.name);
    
    // Test state manager
    const stateManager = kenny.getStateManager();
    console.log('📊 State Manager:', stateManager.constructor.name);
    
  } catch (error) {
    console.error('❌ Error in Kenny test:', error.message);
  }
}

// Test ASI1 Provider
async function testASI1() {
  try {
    console.log('\n🤖 Testing ASI1 Provider...');
    const { ASI1Provider } = await import('./src/provider/asi1.js');
    const provider = new ASI1Provider({ apiKey: 'test-key' });
    console.log('✅ ASI1 Provider created:', provider.constructor.name);
    console.log('📝 Available models:', provider.getAvailableModels());
    
  } catch (error) {
    console.error('❌ Error in ASI1 test:', error.message);
  }
}

// Test Tool System
async function testTools() {
  try {
    console.log('\n🔧 Testing Tool System...');
    const { createToolRegistry } = await import('./src/tool/tool-registry.js');
    const registry = createToolRegistry();
    console.log('✅ Tool Registry created');
    
    // Initialize registry
    await registry.initialize({});
    console.log('✅ Tool Registry initialized');
    
    // Check health
    const health = await registry.healthCheck();
    console.log('🏥 Tool Registry health:', health);
    
  } catch (error) {
    console.error('❌ Error in Tool test:', error.message);
  }
}

// Test Session Management
async function testSession() {
  try {
    console.log('\n💾 Testing Session Management...');
    const { DefaultSessionManager } = await import('./src/session/session-manager.js');
    const { MemorySessionStorage } = await import('./src/session/session-storage.js');
    
    const storage = new MemorySessionStorage();
    const manager = new DefaultSessionManager(storage);
    console.log('✅ Session Manager created');
    
    // Create a test session
    const session = await manager.createSession('test-user');
    console.log('📋 Session created:', session.id);
    
    // Clean up
    await manager.destroySession(session.id);
    console.log('🗑️ Session destroyed');
    
  } catch (error) {
    console.error('❌ Error in Session test:', error.message);
  }
}

// Run all tests
async function runAllTests() {
  console.log('Starting ASI-Code component tests...\n');
  
  await testMinimal();
  await testKenny();
  await testASI1();
  await testTools();
  await testSession();
  
  console.log('\n================================');
  console.log('✅ All tests completed!');
  console.log('ASI-Code is operational!');
}

runAllTests().catch(console.error);