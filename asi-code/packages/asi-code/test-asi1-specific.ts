#!/usr/bin/env bun
/**
 * Test the exact API call that's failing in IntelligentGenerator
 */

import { config } from 'dotenv';
config();

const API_KEY = process.env.ASI1_API_KEY || '';
const API_URL = process.env.ASI1_API_URL || 'https://api.asi1.ai';

async function testExactCall() {
  console.log('Testing exact IntelligentGenerator API call...\n');
  
  const prompt = `Analyze this task and provide a JSON object with project details:
Task: "develop a website for dog breeding with custom svgs"

Respond with a valid JSON object containing:
{
  "projectType": "one of: web, mobile, android, ios, api, cli, library",
  "framework": "appropriate framework",
  "language": "primary language",
  "features": ["list", "of", "key", "features"],
  "structure": {
    "directories": ["list", "of", "main", "directories"],
    "keyFiles": ["list", "of", "important", "files"]
  },
  "dependencies": ["main", "dependencies"],
  "description": "brief description"
}`;

  const body = {
    model: 'asi1-mini',
    messages: [
      { 
        role: 'system', 
        content: `You are an expert software engineer and code generator. 
Generate production-ready code following best practices.
Output exactly what is requested - no extra explanations or formatting.
When outputting JSON, ensure it is valid and parseable.
When outputting code, provide complete implementations.` 
      },
      { role: 'user', content: prompt }
    ],
    temperature: 0.3,
    max_tokens: 4000
  };
  
  console.log('Request body:', JSON.stringify(body, null, 2));
  console.log('\nSending request...\n');
  
  try {
    const response = await fetch(`${API_URL}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    
    console.log('Response status:', response.status, response.statusText);
    console.log('Response headers:', Object.fromEntries(response.headers.entries()));
    
    const responseText = await response.text();
    console.log('\nRaw response:', responseText);
    
    if (!response.ok) {
      console.error('\n❌ Request failed!');
      
      // Try to parse as JSON error
      try {
        const errorJson = JSON.parse(responseText);
        console.log('Error details:', errorJson);
      } catch {
        console.log('Error is not JSON formatted');
      }
      
      return;
    }
    
    // Parse successful response
    const data = JSON.parse(responseText);
    console.log('\n✅ Success!');
    console.log('Response content:', data.choices[0].message.content);
    
    // Try to parse the content as JSON
    try {
      const projectData = JSON.parse(data.choices[0].message.content);
      console.log('\nParsed project data:', projectData);
    } catch {
      console.log('\nNote: Response is not valid JSON (might be code or text)');
    }
    
  } catch (error) {
    console.error('\n❌ Exception:', error);
  }
}

// Test with different max_tokens values
async function testMaxTokens() {
  console.log('\n\n=== Testing different max_tokens values ===\n');
  
  const maxTokensValues = [500, 1000, 2000, 3000, 3500, 4000, 4096, 5000];
  
  for (const maxTokens of maxTokensValues) {
    console.log(`\nTesting max_tokens: ${maxTokens}`);
    
    const response = await fetch(`${API_URL}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'asi1-mini',
        messages: [{ role: 'user', content: 'Say hello' }],
        max_tokens: maxTokens
      })
    });
    
    if (response.ok) {
      console.log(`  ✅ ${maxTokens} tokens: OK`);
    } else {
      const error = await response.text();
      console.log(`  ❌ ${maxTokens} tokens: Failed - ${response.status}`);
      try {
        const errorJson = JSON.parse(error);
        if (errorJson.error?.message) {
          console.log(`     Error: ${errorJson.error.message}`);
        }
      } catch {}
    }
  }
}

// Run tests
async function main() {
  await testExactCall();
  await testMaxTokens();
}

main().catch(console.error);