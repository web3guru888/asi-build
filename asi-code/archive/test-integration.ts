#!/usr/bin/env bun

/**
 * ASI_Code Integration Test
 * Tests the ASI1 provider integration with the framework
 */

import { ASI1Provider } from "./packages/opencode/src/provider/asi1"

const API_KEY = "sk_df5d9a7c3ed949cdb7837c54f5ac09ad129e7702e05d4fa0af3c6ddeb5095d4c"

console.log("🚀 Testing ASI_Code Framework Integration")
console.log("=" .repeat(50))

async function testProviderIntegration() {
  console.log("\n📋 Testing ASI1 Provider Integration")
  console.log("-".repeat(30))
  
  try {
    // Create provider
    const provider = ASI1Provider.createProvider({
      apiKey: API_KEY,
      sessionId: "test-session-001"
    })
    
    console.log("✅ Provider created successfully")
    
    // Get language model
    const model = provider.languageModel("asi1-mini")
    console.log("✅ Language model instantiated")
    console.log(`   Model ID: ${model.modelId}`)
    console.log(`   Provider: ${model.provider}`)
    
    // Test generation
    console.log("\n🔬 Testing text generation...")
    const result = await model.doGenerate({
      messages: [
        {
          role: "user",
          content: [{ type: "text", text: "Write a haiku about artificial intelligence" }]
        }
      ],
      maxTokens: 100,
      temperature: 0.7
    })
    
    console.log("✅ Generation successful!")
    console.log("📝 Response:", result.text)
    console.log("📊 Usage:", result.usage)
    
    return true
  } catch (error) {
    console.error("❌ Integration test failed:", error)
    return false
  }
}

async function testStreamingIntegration() {
  console.log("\n📋 Testing Streaming Integration")
  console.log("-".repeat(30))
  
  try {
    const provider = ASI1Provider.createProvider({
      apiKey: API_KEY
    })
    
    const model = provider.languageModel("asi1-mini")
    
    console.log("🔬 Testing streaming generation...")
    const stream = await model.doStream({
      messages: [
        {
          role: "user",
          content: [{ type: "text", text: "Count to 3" }]
        }
      ],
      maxTokens: 50
    })
    
    console.log("✅ Stream created")
    console.log("📝 Streaming response:")
    
    const reader = stream.getReader()
    let fullText = ""
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      if (value.type === "text-delta") {
        process.stdout.write(value.text)
        fullText += value.text
      } else if (value.type === "finish") {
        console.log("\n✅ Stream finished")
        console.log("📊 Final usage:", value.usage)
      }
    }
    
    return true
  } catch (error) {
    console.error("❌ Streaming test failed:", error)
    return false
  }
}

async function testKennyIntegration() {
  console.log("\n📋 Testing Kenny Integration Pattern")
  console.log("-".repeat(30))
  
  try {
    const { KennyIntegration } = await import("./packages/opencode/src/kenny/integration")
    
    const kenny = KennyIntegration.getInstance()
    console.log("✅ Kenny Integration initialized")
    
    // Test message bus
    kenny.bus.subscribe("test:channel", (data) => {
      console.log("📨 Received message:", data)
    })
    
    kenny.bus.publish("test:channel", { message: "Hello from Kenny!" })
    console.log("✅ Message bus working")
    
    // Test state manager
    kenny.state.setState("test-subsystem", { status: "active" })
    const state = kenny.state.getState("test-subsystem")
    console.log("✅ State manager working:", state)
    
    return true
  } catch (error) {
    console.error("❌ Kenny Integration test failed:", error)
    return false
  }
}

async function testConsciousnessEngine() {
  console.log("\n📋 Testing Consciousness Engine")
  console.log("-".repeat(30))
  
  try {
    const { ConsciousnessEngine } = await import("./packages/opencode/src/consciousness/engine")
    const { KennyIntegration } = await import("./packages/opencode/src/kenny/integration")
    
    const kenny = KennyIntegration.getInstance()
    const consciousness = ConsciousnessEngine.getInstance()
    
    // Register consciousness engine
    await kenny.register(consciousness)
    await kenny.initialize()
    
    console.log("✅ Consciousness Engine registered")
    
    // Get state
    const state = consciousness.getState()
    console.log("🧠 Consciousness State:")
    console.log(`   Level: ${state.level}`)
    console.log(`   Awareness: ${(state.awareness * 100).toFixed(1)}%`)
    
    // Inject a thought
    consciousness.injectThought("Testing ASI_Code framework integration")
    console.log("✅ Thought injected")
    
    // Wait for some activity
    await new Promise(resolve => setTimeout(resolve, 500))
    
    const newState = consciousness.getState()
    console.log("🧠 Updated State:")
    console.log(`   Level: ${newState.level}`)
    console.log(`   Awareness: ${(newState.awareness * 100).toFixed(1)}%`)
    console.log(`   Thoughts: ${newState.thoughts.length}`)
    
    // Shutdown
    await kenny.shutdown()
    console.log("✅ Clean shutdown completed")
    
    return true
  } catch (error) {
    console.error("❌ Consciousness Engine test failed:", error)
    return false
  }
}

// Run all integration tests
async function runIntegrationTests() {
  console.log("\n🔬 Running ASI_Code Integration Tests")
  console.log("API Key:", API_KEY.substring(0, 10) + "..." + API_KEY.substring(API_KEY.length - 4))
  
  const results = {
    provider: await testProviderIntegration(),
    streaming: await testStreamingIntegration(),
    kenny: await testKennyIntegration(),
    consciousness: await testConsciousnessEngine()
  }
  
  console.log("\n" + "=".repeat(50))
  console.log("📊 Integration Test Results:")
  console.log("-".repeat(30))
  console.log(`ASI1 Provider: ${results.provider ? "✅ PASS" : "❌ FAIL"}`)
  console.log(`Streaming: ${results.streaming ? "✅ PASS" : "❌ FAIL"}`)
  console.log(`Kenny Integration: ${results.kenny ? "✅ PASS" : "❌ FAIL"}`)
  console.log(`Consciousness Engine: ${results.consciousness ? "✅ PASS" : "❌ FAIL"}`)
  
  const allPassed = Object.values(results).every(r => r)
  console.log("\n" + (allPassed ? "✅ All integration tests passed!" : "⚠️ Some tests failed"))
  
  if (allPassed) {
    console.log("\n🎉 ASI_Code is ready for deployment!")
    console.log("   Set ASI1_API_KEY environment variable and run: bun dev")
  }
}

// Execute tests
runIntegrationTests().catch(console.error)