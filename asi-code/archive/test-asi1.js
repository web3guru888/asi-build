#!/usr/bin/env node
/**
 * Test ASI1 API directly
 */

const API_KEY = process.env.ASI1_API_KEY || 'test-key'
const BASE_URL = process.env.ASI1_BASE_URL || 'https://api.asi1.ai'

async function testASI1() {
  console.log('Testing ASI1 API...')
  console.log('API Key:', API_KEY ? 'SET' : 'NOT SET')
  console.log('Base URL:', BASE_URL)
  
  const request = {
    messages: [
      { role: 'user', content: 'Say hello' }
    ],
    model: 'asi1-mini',
    stream: true,
    max_tokens: 100,
    temperature: 0.7
  }
  
  console.log('\nRequest:', JSON.stringify(request, null, 2))
  
  try {
    const response = await fetch(`${BASE_URL}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    })
    
    console.log('\nResponse status:', response.status, response.statusText)
    console.log('Response headers:', Object.fromEntries(response.headers.entries()))
    
    if (!response.ok) {
      const error = await response.text()
      console.log('Error body:', error)
      return
    }
    
    // Read streaming response
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    
    console.log('\nStreaming response:')
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue
        
        if (trimmed.startsWith('data: ')) {
          const data = trimmed.slice(6)
          if (data === '[DONE]') {
            console.log('Stream completed')
            return
          }
          
          try {
            const parsed = JSON.parse(data)
            console.log('Chunk:', JSON.stringify(parsed, null, 2))
            
            // Extract text content
            const choice = parsed.choices?.[0]
            if (choice?.delta?.content) {
              process.stdout.write(choice.delta.content)
            }
          } catch (e) {
            console.log('Failed to parse:', data)
          }
        }
      }
    }
  } catch (error) {
    console.error('Error:', error)
  }
}

testASI1()