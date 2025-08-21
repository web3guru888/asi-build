#!/usr/bin/env bun

/**
 * ASI1 API Test Script
 * Tests connectivity and functionality of ASI1 endpoints
 */

const API_KEY = "sk_df5d9a7c3ed949cdb7837c54f5ac09ad129e7702e05d4fa0af3c6ddeb5095d4c"
const BASE_URL = "https://api.asi1.ai/v1/chat/completions"

console.log("🚀 Testing ASI1 API Endpoint...")
console.log("=" .repeat(50))

// Test 1: Basic completion request
async function testBasicCompletion() {
  console.log("\n📋 Test 1: Basic Completion")
  console.log("-".repeat(30))
  
  try {
    const response = await fetch(BASE_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        messages: [
          {
            role: "user",
            content: "Hello ASI1! Please respond with a brief greeting."
          }
        ],
        model: "asi1-mini",
        max_tokens: 100,
        temperature: 0.7
      })
    })

    console.log(`Status: ${response.status} ${response.statusText}`)
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error("❌ Error response:", errorText)
      return false
    }

    const data = await response.json()
    console.log("✅ Success! Response:")
    console.log(JSON.stringify(data, null, 2))
    
    if (data.choices?.[0]?.message?.content) {
      console.log("\n💬 ASI1 says:", data.choices[0].message.content)
    }
    
    return true
  } catch (error) {
    console.error("❌ Request failed:", error)
    return false
  }
}

// Test 2: Streaming request
async function testStreaming() {
  console.log("\n📋 Test 2: Streaming Response")
  console.log("-".repeat(30))
  
  try {
    const response = await fetch(BASE_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        messages: [
          {
            role: "user",
            content: "Count from 1 to 5 slowly."
          }
        ],
        model: "asi1-mini",
        stream: true,
        max_tokens: 100
      })
    })

    console.log(`Status: ${response.status} ${response.statusText}`)
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error("❌ Error response:", errorText)
      return false
    }

    console.log("✅ Streaming response received")
    console.log("📝 Stream content:")
    
    const reader = response.body?.getReader()
    if (!reader) {
      console.error("❌ No response body")
      return false
    }

    const decoder = new TextDecoder()
    let fullContent = ""
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value)
      const lines = chunk.split("\n")
      
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6)
          if (data === "[DONE]") {
            console.log("\n✅ Stream complete")
            break
          }
          
          try {
            const parsed = JSON.parse(data)
            if (parsed.choices?.[0]?.delta?.content) {
              const content = parsed.choices[0].delta.content
              process.stdout.write(content)
              fullContent += content
            }
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    }
    
    console.log("\n\n💬 Full response:", fullContent)
    return true
  } catch (error) {
    console.error("❌ Streaming failed:", error)
    return false
  }
}

// Test 3: Tool calling
async function testToolCalling() {
  console.log("\n📋 Test 3: Tool Calling")
  console.log("-".repeat(30))
  
  try {
    const response = await fetch(BASE_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        messages: [
          {
            role: "user",
            content: "What's the weather like? Use a tool if you can."
          }
        ],
        model: "asi1-mini",
        tools: [
          {
            name: "get_weather",
            description: "Get the current weather",
            parameters: {
              type: "object",
              properties: {
                location: {
                  type: "string",
                  description: "The location to get weather for"
                }
              }
            }
          }
        ],
        max_tokens: 200
      })
    })

    console.log(`Status: ${response.status} ${response.statusText}`)
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error("❌ Error response:", errorText)
      return false
    }

    const data = await response.json()
    console.log("✅ Success! Response:")
    console.log(JSON.stringify(data, null, 2))
    
    if (data.choices?.[0]?.message?.tool_calls) {
      console.log("\n🔧 Tool calls detected:", data.choices[0].message.tool_calls)
    }
    
    return true
  } catch (error) {
    console.error("❌ Tool calling test failed:", error)
    return false
  }
}

// Test 4: Model availability
async function testModels() {
  console.log("\n📋 Test 4: Model Availability")
  console.log("-".repeat(30))
  
  const models = ["asi1-mini", "asi1-standard", "asi1-pro", "asi1-ultra", "asi1-quantum"]
  
  for (const model of models) {
    process.stdout.write(`Testing ${model}... `)
    
    try {
      const response = await fetch(BASE_URL, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${API_KEY}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          messages: [{ role: "user", content: "Hi" }],
          model: model,
          max_tokens: 10
        })
      })
      
      if (response.ok) {
        console.log("✅ Available")
      } else if (response.status === 404) {
        console.log("❌ Not found")
      } else {
        console.log(`⚠️ Status ${response.status}`)
      }
    } catch (error) {
      console.log("❌ Error")
    }
  }
}

// Run all tests
async function runTests() {
  console.log("\n🔬 Starting ASI1 API Tests")
  console.log("API Key:", API_KEY.substring(0, 10) + "..." + API_KEY.substring(API_KEY.length - 4))
  console.log("Endpoint:", BASE_URL)
  
  const results = {
    basic: await testBasicCompletion(),
    streaming: await testStreaming(),
    toolCalling: await testToolCalling()
  }
  
  await testModels()
  
  console.log("\n" + "=".repeat(50))
  console.log("📊 Test Results Summary:")
  console.log("-".repeat(30))
  console.log(`Basic Completion: ${results.basic ? "✅ PASS" : "❌ FAIL"}`)
  console.log(`Streaming: ${results.streaming ? "✅ PASS" : "❌ FAIL"}`)
  console.log(`Tool Calling: ${results.toolCalling ? "✅ PASS" : "❌ FAIL"}`)
  
  const allPassed = Object.values(results).every(r => r)
  console.log("\n" + (allPassed ? "✅ All tests passed!" : "⚠️ Some tests failed"))
}

// Execute tests
runTests().catch(console.error)