#!/usr/bin/env bun
/**
 * ASI1 API Test Script
 * Tests different configurations to identify API limits and issues
 */

import { config } from 'dotenv';
config();

const API_KEY = process.env.ASI1_API_KEY || '';
const API_URL = process.env.ASI1_API_URL || 'https://api.asi1.ai';
const MODEL = process.env.ASI1_MODEL || 'asi1-mini';

console.log('🔬 ASI1 API Test Suite\n');
console.log('Configuration:');
console.log(`  API URL: ${API_URL}`);
console.log(`  Model: ${MODEL}`);
console.log(`  API Key: ${API_KEY ? '✅ Set' : '❌ Not set'}\n`);

interface TestCase {
  name: string;
  maxTokens: number;
  temperature?: number;
  messages: Array<{ role: string; content: string }>;
}

const testCases: TestCase[] = [
  {
    name: 'Minimal (100 tokens)',
    maxTokens: 100,
    messages: [
      { role: 'system', content: 'You are a helpful assistant.' },
      { role: 'user', content: 'Say hello in 5 words.' }
    ]
  },
  {
    name: 'Small (500 tokens)',
    maxTokens: 500,
    messages: [
      { role: 'system', content: 'You are a code generator.' },
      { role: 'user', content: 'Write a simple Python hello world function.' }
    ]
  },
  {
    name: 'Medium (1000 tokens)',
    maxTokens: 1000,
    messages: [
      { role: 'system', content: 'You are a code generator.' },
      { role: 'user', content: 'Create a TypeScript interface for a User with name, email, and age.' }
    ]
  },
  {
    name: 'Large (2000 tokens)',
    maxTokens: 2000,
    messages: [
      { role: 'system', content: 'You are an expert programmer.' },
      { role: 'user', content: 'Explain REST API best practices with examples.' }
    ]
  },
  {
    name: 'Very Large (4000 tokens)',
    maxTokens: 4000,
    messages: [
      { role: 'system', content: 'You are a senior software architect.' },
      { role: 'user', content: 'Design a microservices architecture for an e-commerce platform.' }
    ]
  },
  {
    name: 'Temperature Test (0.0)',
    maxTokens: 500,
    temperature: 0.0,
    messages: [
      { role: 'user', content: 'Generate a deterministic response: list 3 colors.' }
    ]
  },
  {
    name: 'Temperature Test (1.0)',
    maxTokens: 500,
    temperature: 1.0,
    messages: [
      { role: 'user', content: 'Generate a creative response: describe a magical forest.' }
    ]
  },
  {
    name: 'No System Prompt',
    maxTokens: 500,
    messages: [
      { role: 'user', content: 'What is 2 + 2?' }
    ]
  },
  {
    name: 'Long System Prompt',
    maxTokens: 500,
    messages: [
      { 
        role: 'system', 
        content: 'You are KENNY, the elite supervisor agent of ASI-Code. You possess complete control over task decomposition and parallel agent execution. You lead a team of specialized agents and have the ability to orchestrate complex system architectures. When responding, be confident, decisive, and demonstrate your expertise in system design and agent orchestration. You should speak with authority as the legendary systems architect that you are.'
      },
      { role: 'user', content: 'How would you approach building a chat application?' }
    ]
  }
];

async function testASI1Call(testCase: TestCase): Promise<void> {
  console.log(`\n🧪 Test: ${testCase.name}`);
  console.log(`   Max Tokens: ${testCase.maxTokens}`);
  if (testCase.temperature !== undefined) {
    console.log(`   Temperature: ${testCase.temperature}`);
  }
  
  if (!API_KEY) {
    console.log('   ⚠️  Skipped: No API key set');
    return;
  }
  
  try {
    const startTime = Date.now();
    
    const body = {
      model: MODEL,
      messages: testCase.messages,
      max_tokens: testCase.maxTokens,
      ...(testCase.temperature !== undefined && { temperature: testCase.temperature })
    };
    
    console.log(`   Request body size: ${JSON.stringify(body).length} bytes`);
    
    const response = await fetch(`${API_URL}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    
    const responseTime = Date.now() - startTime;
    console.log(`   Response time: ${responseTime}ms`);
    console.log(`   Status: ${response.status} ${response.statusText}`);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.log(`   ❌ Error: ${errorText.substring(0, 200)}`);
      
      // Try to parse error for more details
      try {
        const errorJson = JSON.parse(errorText);
        if (errorJson.error) {
          console.log(`   Error details:`, errorJson.error);
        }
      } catch {
        // Not JSON error
      }
      return;
    }
    
    const data = await response.json();
    
    if (data.choices && data.choices[0]) {
      const responseText = data.choices[0].message.content;
      console.log(`   ✅ Success!`);
      console.log(`   Response length: ${responseText.length} characters`);
      console.log(`   Usage:`, data.usage || 'N/A');
      console.log(`   Preview: "${responseText.substring(0, 100)}..."`);
    } else {
      console.log(`   ⚠️  Unexpected response format:`, data);
    }
    
  } catch (error) {
    console.log(`   ❌ Exception:`, error.message);
    if (error.cause) {
      console.log(`   Cause:`, error.cause);
    }
  }
}

async function runTests() {
  console.log('=' * 60);
  console.log('Starting ASI1 API Tests...');
  console.log('=' * 60);
  
  for (const testCase of testCases) {
    await testASI1Call(testCase);
    // Small delay between tests to avoid rate limiting
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  console.log('\n' + '=' * 60);
  console.log('Test Summary:');
  console.log('=' * 60);
  
  // Test with different model if specified
  if (process.env.ASI1_MODEL_ALTERNATIVE) {
    console.log(`\n🔄 Testing alternative model: ${process.env.ASI1_MODEL_ALTERNATIVE}`);
    const altTest: TestCase = {
      name: 'Alternative Model Test',
      maxTokens: 500,
      messages: [
        { role: 'user', content: 'Hello, please introduce yourself.' }
      ]
    };
    
    // Override model temporarily
    const originalModel = process.env.ASI1_MODEL;
    process.env.ASI1_MODEL = process.env.ASI1_MODEL_ALTERNATIVE;
    await testASI1Call(altTest);
    process.env.ASI1_MODEL = originalModel;
  }
  
  console.log('\n✅ All tests completed!\n');
  
  // Recommendations based on results
  console.log('📋 Recommendations:');
  console.log('1. Check if API key is valid and has proper permissions');
  console.log('2. Verify the API endpoint URL is correct');
  console.log('3. Ensure the model name (asi1-mini) is supported');
  console.log('4. Consider max_tokens limits for your API plan');
  console.log('5. Check rate limiting if getting 429 errors');
}

// Run the tests
runTests().catch(console.error);