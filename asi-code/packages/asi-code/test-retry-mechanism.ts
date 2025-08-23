#!/usr/bin/env bun
/**
 * Test the retry mechanism for ASI1 API calls
 */

import { IntelligentGenerator } from './agents/intelligent-generator';

console.log('🧪 Testing ASI1 API Retry Mechanism\n');
console.log('=' * 50);

// Test with custom retry configuration
const testConfigs = [
  {
    name: 'Default Configuration',
    config: undefined
  },
  {
    name: 'Aggressive Retry (5s base, 3x multiplier)',
    config: {
      maxRetries: 3,
      baseDelayMs: 5000,
      maxDelayMs: 60000,
      backoffMultiplier: 3,
      enableRetry: true
    }
  },
  {
    name: 'No Retry',
    config: {
      enableRetry: false
    }
  }
];

async function testRetryWithConfig(name: string, config?: any) {
  console.log(`\n📋 Test: ${name}`);
  console.log('-' * 40);
  
  const generator = new IntelligentGenerator(config);
  
  // Test a simple generation that might hit rate limits
  const startTime = Date.now();
  
  try {
    const result = await generator.generateProject(
      'Create a simple hello world function',
      `test_session_${Date.now()}`
    );
    
    const duration = Date.now() - startTime;
    console.log(`✅ Generation completed in ${(duration/1000).toFixed(1)}s`);
    console.log(`   Files generated: ${result.files.length}`);
    
  } catch (error) {
    const duration = Date.now() - startTime;
    console.log(`❌ Generation failed after ${(duration/1000).toFixed(1)}s`);
    console.log(`   Error: ${error.message}`);
  }
}

async function runTests() {
  for (const test of testConfigs) {
    await testRetryWithConfig(test.name, test.config);
    
    // Wait between tests to avoid hitting rate limits
    console.log('\n⏱️  Waiting 5s before next test...');
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  
  console.log('\n' + '=' * 50);
  console.log('✅ All retry mechanism tests completed!\n');
  
  console.log('📊 Retry Delay Progression Examples:');
  console.log('   10s base, 2x multiplier: 10s → 20s → 40s → 80s → 120s (capped)');
  console.log('   10s base, 3x multiplier: 10s → 30s → 90s → 120s (capped)');
  console.log('   5s base, 2x multiplier: 5s → 10s → 20s → 40s → 80s');
}

// Run the tests
runTests().catch(console.error);