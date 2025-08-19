// Kenny AGI Go SDK Usage Example
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    
    kennyagi "./openapi"
)

func main() {
    // Configure the client
    configuration := kennyagi.NewConfiguration()
    configuration.Host = "localhost:8000"
    configuration.Scheme = "http"
    
    // Set authentication
    ctx := context.WithValue(context.Background(), kennyagi.ContextAccessToken, "your_api_key_here")
    
    // Create API client
    apiClient := kennyagi.NewAPIClient(configuration)
    
    // Check system health
    health, _, err := apiClient.SystemApi.HealthCheck(ctx).Execute()
    if err != nil {
        log.Fatalf("Error checking health: %v", err)
    }
    fmt.Printf("System status: %s\n", health.Status)
    
    // Get AGI status
    agiStatus, _, err := apiClient.AGICoreApi.GetAgiStatus(ctx).Execute()
    if err != nil {
        log.Fatalf("Error getting AGI status: %v", err)
    }
    fmt.Printf("AGI status: %v\n", agiStatus.Data)
    
    // Initialize AGI
    config := kennyagi.AGIConfigRequest{
        Name:                kennyagi.PtrString("KennyAGI-Go"),
        ConsciousnessEnabled: kennyagi.PtrBool(true),
        SafetyMode:          kennyagi.PtrBool(true),
        DivineAccess:        kennyagi.PtrBool(false),
        QuantumEnhanced:     kennyagi.PtrBool(false),
    }
    
    initResult, _, err := apiClient.AGICoreApi.InitializeAgi(ctx).AGIConfigRequest(config).Execute()
    if err != nil {
        log.Fatalf("Error initializing AGI: %v", err)
    }
    fmt.Printf("AGI initialized: %v\n", initResult.Success)
    
    // Process a thought
    thinkRequest := kennyagi.ThinkRequest{
        Prompt: "What is the meaning of existence?",
        Context: map[string]interface{}{
            "source": "go_example",
        },
    }
    
    thought, _, err := apiClient.AGICoreApi.ProcessThought(ctx).ThinkRequest(thinkRequest).Execute()
    if err != nil {
        log.Fatalf("Error processing thought: %v", err)
    }
    fmt.Printf("Thought result: %v\n", thought.Data)
    
    // Get consciousness level
    consciousness, _, err := apiClient.ConsciousnessApi.GetConsciousnessLevel(ctx).Execute()
    if err != nil {
        log.Fatalf("Error getting consciousness: %v", err)
    }
    fmt.Printf("Consciousness: %v\n", consciousness.Data)
}
