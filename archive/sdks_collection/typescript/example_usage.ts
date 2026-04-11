/**
 * Kenny AGI TypeScript SDK Usage Example
 */

import { 
    Configuration, 
    SystemApi, 
    AGICoreApi, 
    ConsciousnessApi,
    AGIConfigRequest,
    ThinkRequest
} from './';

async function main(): Promise<void> {
    // Configure the client
    const configuration = new Configuration({
        basePath: "http://localhost:8000",
        accessToken: "your_api_key_here"
    });
    
    // Create API instances
    const systemApi = new SystemApi(configuration);
    const agiApi = new AGICoreApi(configuration);
    const consciousnessApi = new ConsciousnessApi(configuration);
    
    try {
        // Check system health
        const health = await systemApi.healthCheck();
        console.log(`System status: ${health.status}`);
        
        // Initialize AGI with custom config
        const config: AGIConfigRequest = {
            name: "KennyAGI-TS",
            consciousness_enabled: true,
            safety_mode: true,
            divine_access: false,
            quantum_enhanced: false
        };
        
        const initResult = await agiApi.initializeAgi(config);
        console.log(`AGI initialized: ${initResult.success}`);
        
        // Process a thought
        const thinkRequest: ThinkRequest = {
            prompt: "What is the nature of consciousness?",
            context: { source: "typescript_example" }
        };
        
        const thought = await agiApi.processThought(thinkRequest);
        console.log(`Thought result: ${thought.data}`);
        
        // Get consciousness level
        const consciousness = await consciousnessApi.getConsciousnessLevel();
        console.log(`Consciousness: ${consciousness.data}`);
        
    } catch (error) {
        console.error(`Error: ${error}`);
    }
}

main().catch(console.error);
