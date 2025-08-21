// Complete Integration Example for ASI-Code
import { ConfigSystemFactory } from './config';
import { LoggingSystemFactory } from './logging';
import { initializeASICode, createMinimalASICode } from '.';

async function demonstrateFullIntegration() {
  console.log('🚀 ASI-Code Full Integration Demonstration');

  // Create and register configuration system
  const configManager = await ConfigSystemFactory.createAndRegister();
  await configManager.waitForInitialization();

  // Create and register logging system  
  const logManager = await LoggingSystemFactory.createAndRegister();
  await logManager.waitForInitialization();

  // Initialize complete ASI-Code system
  const system = await initializeASICode({
    asiCodeConfig: {
      providers: {
        asi1: {
          apiKey: process.env.ASI1_API_KEY || 'test-key',
          defaultModel: 'asi1-mini'
        }
      }
    }
  });

  console.log('✅ ASI-Code system fully initialized');
  console.log(`Status: ${system.status}`);

  // Demonstrate health monitoring
  const healthStatus = await system.checkHealth();
  console.log('📊 System Health:', healthStatus);

  // Graceful shutdown
  await system.shutdown();
  console.log('✅ System shutdown complete');
}

async function demonstrateMinimalSetup() {
  console.log('🔧 ASI-Code Minimal Setup Demonstration');

  // Create minimal system for development
  const system = await createMinimalASICode();
  
  console.log('✅ Minimal ASI-Code system ready');
  console.log(`Components active: ${Object.keys(system.components || {}).length}`);

  await system.shutdown();
  console.log('✅ Minimal system shutdown complete');
}

export { demonstrateFullIntegration, demonstrateMinimalSetup };