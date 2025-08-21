# ASI_Code API Reference

## Table of Contents

1. [Overview](#overview)
2. [Core APIs](#core-apis)
3. [Kenny Integration API](#kenny-integration-api)
4. [Provider System API](#provider-system-api)
5. [Session Management API](#session-management-api)
6. [Tool System API](#tool-system-api)
7. [Configuration API](#configuration-api)
8. [Event Bus API](#event-bus-api)
9. [Storage API](#storage-api)
10. [CLI API](#cli-api)

---

## Overview

This document provides comprehensive API documentation for ASI_Code's core systems. All APIs follow TypeScript interfaces and provide full type safety.

### API Design Principles

- **Type Safety**: All APIs are fully typed with TypeScript
- **Async/Await**: Modern async patterns throughout
- **Error Handling**: Comprehensive error types and handling
- **Context Aware**: All operations respect execution context
- **Event Driven**: APIs emit events for integration
- **Resource Management**: Automatic cleanup and lifecycle management

---

## Core APIs

### App Context API

The App API provides foundational context management for all operations.

```typescript
export namespace App {
  export interface Info {
    hostname: string
    git: boolean
    path: {
      config: string    // Configuration directory
      data: string      // Data storage directory
      root: string      // Project root directory
      cwd: string       // Current working directory
      state: string     // State directory
    }
    time: {
      initialized?: number
    }
  }

  export interface Input {
    cwd: string
  }

  /**
   * Provides application context for all operations
   * @param input - Application input with working directory
   * @param cb - Callback function that receives app context
   * @returns Promise that resolves to callback result
   */
  export function provide<T>(
    input: Input, 
    cb: (app: App.Info) => Promise<T>
  ): Promise<T>

  /**
   * Gets current application context
   * @returns Current app context
   * @throws {Context.NotFound} When no app context is available
   */
  export function use(): App.Info

  /**
   * Creates a managed service state
   * @param name - Service name
   * @param factory - Factory function to create service
   * @returns Function that returns service instance
   */
  export function state<T>(
    name: string, 
    factory: () => T | Promise<T>
  ): () => Promise<T>

  /**
   * Registers a service for cleanup
   * @param name - Service name
   * @param service - Service instance or factory
   */
  export function register(name: string, service: any): void
}
```

#### Usage Example

```typescript
import { App } from '@opencode/core'

// Basic app context usage
await App.provide({ cwd: process.cwd() }, async (app) => {
  console.log('Working in:', app.path.cwd)
  console.log('Config dir:', app.path.config)
  console.log('Is git repo:', app.git)
})

// Service state management
const databaseState = App.state('database', async () => {
  return new Database({ path: app.path.data })
})

// Use service
const db = await databaseState()
```

---

## Kenny Integration API

The Kenny Integration Pattern provides unified subsystem communication.

```typescript
export namespace KennyIntegration {
  export interface Subsystem {
    readonly id: string
    readonly name: string
    readonly version: string
    readonly dependencies?: string[]
    
    initialize(): Promise<void>
    connect(integration: Integration): void
    shutdown(): Promise<void>
  }

  export abstract class BaseSubsystem implements Subsystem {
    abstract readonly id: string
    abstract readonly name: string
    abstract readonly version: string
    readonly dependencies?: string[]

    protected integration!: Integration
    protected log: Log

    abstract initialize(): Promise<void>
    abstract shutdown(): Promise<void>

    /**
     * Connects to Kenny Integration system
     * @param integration - Integration instance
     */
    connect(integration: Integration): void

    /**
     * Publishes message to integration bus
     * @param channel - Message channel
     * @param data - Message data
     */
    protected publish(channel: string, data: any): void

    /**
     * Subscribes to messages from other subsystems
     * @param subsystemId - Source subsystem ID
     * @param channel - Message channel
     * @param callback - Message handler
     * @returns Unsubscribe function
     */
    protected subscribe(
      subsystemId: string, 
      channel: string, 
      callback: (data: any) => void
    ): () => void

    /**
     * Sets subsystem state
     * @param state - New state
     */
    protected setState(state: any): void

    /**
     * Gets another subsystem's state
     * @param subsystemId - Target subsystem ID
     */
    protected getState(subsystemId: string): any

    /**
     * Watches another subsystem's state changes
     * @param subsystemId - Target subsystem ID
     * @param callback - State change handler
     * @returns Unsubscribe function
     */
    protected watchState(
      subsystemId: string, 
      callback: (state: any) => void
    ): () => void
  }

  export class Integration {
    /**
     * Registers a subsystem with the integration
     * @param subsystem - Subsystem to register
     */
    async register(subsystem: Subsystem): Promise<void>

    /**
     * Initializes all registered subsystems
     */
    async initialize(): Promise<void>

    /**
     * Shuts down all subsystems
     */
    async shutdown(): Promise<void>

    /**
     * Gets a registered subsystem
     * @param id - Subsystem ID
     */
    getSubsystem(id: string): Subsystem | undefined

    /**
     * Lists all registered subsystems
     */
    listSubsystems(): Subsystem[]

    /**
     * Gets the message bus
     */
    get bus(): MessageBus

    /**
     * Gets the state manager
     */
    get state(): StateManager
  }

  export class MessageBus {
    /**
     * Publishes a message to a channel
     * @param channel - Message channel
     * @param data - Message data
     */
    publish(channel: string, data: any): void

    /**
     * Subscribes to a channel
     * @param channel - Message channel
     * @param callback - Message handler
     * @returns Unsubscribe function
     */
    subscribe(channel: string, callback: (data: any) => void): () => void
  }

  export class StateManager {
    /**
     * Sets state for a subsystem
     * @param subsystem - Subsystem ID
     * @param state - New state
     */
    setState(subsystem: string, state: any): void

    /**
     * Gets state for a subsystem
     * @param subsystem - Subsystem ID
     */
    getState(subsystem: string): any

    /**
     * Watches state changes for a subsystem
     * @param subsystem - Subsystem ID
     * @param callback - State change handler
     * @returns Unsubscribe function
     */
    watchState(
      subsystem: string, 
      callback: (state: any) => void
    ): () => void
  }

  /**
   * Gets the global Kenny Integration instance
   */
  export function getInstance(): Integration
}
```

#### Usage Example

```typescript
import { KennyIntegration } from '@opencode/core'

// Create a custom subsystem
class MySubsystem extends KennyIntegration.BaseSubsystem {
  id = "my-subsystem"
  name = "My Custom Subsystem"
  version = "1.0.0"
  dependencies = ["provider", "session"]

  async initialize(): Promise<void> {
    // Subscribe to events
    this.subscribe("session", "created", this.onSessionCreated.bind(this))
    
    // Set initial state
    this.setState({ status: "ready", processedCount: 0 })
    
    // Announce readiness
    this.publish("initialized", { timestamp: Date.now() })
  }

  async shutdown(): Promise<void> {
    this.setState({ status: "shutdown" })
  }

  private onSessionCreated(data: any): void {
    console.log("Session created:", data)
  }

  public async processRequest(request: any): Promise<any> {
    const state = this.getState(this.id)
    
    // Update state
    this.setState({
      ...state,
      processedCount: state.processedCount + 1
    })
    
    return { processed: true, request }
  }
}

// Register and use
const kenny = KennyIntegration.getInstance()
const mySubsystem = new MySubsystem()

await kenny.register(mySubsystem)
await kenny.initialize()

// Use the subsystem
await mySubsystem.processRequest({ data: "test" })
```

---

## Provider System API

The Provider API provides unified access to AI models across different providers.

```typescript
export namespace Provider {
  export interface ModelInfo {
    id: string
    provider: string
    capabilities: string[]
    contextWindow: number
    maxOutputTokens: number
    costPer1kTokens: {
      input: number
      output: number
    }
  }

  export interface ProviderInfo {
    id: string
    name: string
    version: string
    capabilities: string[]
    models: ModelInfo[]
  }

  export interface Provider {
    info: ProviderInfo
    
    /**
     * Gets a language model
     * @param modelId - Model identifier
     */
    languageModel(modelId: string): LanguageModel
    
    /**
     * Gets a text embedding model
     * @param modelId - Model identifier
     */
    textEmbeddingModel?(modelId: string): TextEmbeddingModel
    
    /**
     * Gets an image model
     * @param modelId - Model identifier
     */
    imageModel?(modelId: string): ImageModel
  }

  /**
   * Gets available providers
   */
  export function getProviders(): Promise<Provider[]>

  /**
   * Gets a specific provider
   * @param providerId - Provider identifier
   */
  export function getProvider(providerId: string): Promise<Provider>

  /**
   * Gets a language model
   * @param providerId - Provider identifier
   * @param modelId - Model identifier
   */
  export function getModel(
    providerId: string, 
    modelId: string
  ): Promise<LanguageModel>

  /**
   * Lists available models across all providers
   */
  export function listModels(): Promise<Array<{
    providerId: string
    modelId: string
    capabilities: string[]
  }>>
}
```

#### Usage Example

```typescript
import { Provider } from '@opencode/core'

// Get a provider
const provider = await Provider.getProvider('asi1')
console.log('Provider info:', provider.info)

// Get a model
const model = provider.languageModel('asi1-mini')

// Generate text
const result = await model.doGenerate({
  messages: [
    { role: 'user', content: [{ type: 'text', text: 'Hello!' }] }
  ],
  maxTokens: 100
})

console.log('Response:', result.text)
console.log('Usage:', result.usage)

// Stream text
const stream = await model.doStream({
  messages: [
    { role: 'user', content: [{ type: 'text', text: 'Count to 5' }] }
  ]
})

const reader = stream.getReader()
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  
  if (value.type === 'text-delta') {
    process.stdout.write(value.text)
  }
}
```

---

## Session Management API

The Session API manages persistent conversations with AI models.

```typescript
export namespace Session {
  export interface Info {
    id: string
    parentID?: string
    title: string
    version: string
    time: {
      created: number
      updated: number
    }
    revert?: {
      messageID: string
      partID?: string
      snapshot?: string
    }
    share?: {
      url: string
    }
  }

  export interface Config {
    providerID: string
    modelID: string
    agent: Agent.Info
    systemPrompt?: string
    temperature?: number
    maxTokens?: number
  }

  export interface ChatInput {
    content: string
    attachments?: Attachment[]
    metadata?: Record<string, any>
  }

  export interface ChatResponse {
    success: boolean
    message?: Message
    error?: string
    usage?: LanguageModelUsage
  }

  export class Session {
    readonly info: Session.Info
    readonly config: Session.Config

    /**
     * Sends a chat message
     * @param input - Chat input
     */
    async chat(input: ChatInput): Promise<ChatResponse>

    /**
     * Creates a branch from this session
     * @param fromMessageID - Optional message to branch from
     */
    async branch(fromMessageID?: string): Promise<Session>

    /**
     * Reverts to a previous state
     * @param messageID - Message to revert to
     * @param partID - Optional part to revert to
     */
    async revert(messageID: string, partID?: string): Promise<void>

    /**
     * Gets conversation history
     * @param limit - Maximum messages to retrieve
     */
    async getHistory(limit?: number): Promise<Message[]>

    /**
     * Exports session data
     */
    async export(): Promise<SessionExport>

    /**
     * Shares the session
     */
    async share(): Promise<{ url: string; secret: string }>
  }

  export class SessionManager {
    /**
     * Creates a new session
     * @param config - Session configuration
     */
    async create(config: SessionCreateConfig): Promise<Session>

    /**
     * Gets an existing session
     * @param sessionId - Session ID
     */
    async get(sessionId: string): Promise<Session | null>

    /**
     * Lists sessions
     * @param parentID - Filter by parent ID
     */
    async list(parentID?: string): Promise<Session.Info[]>

    /**
     * Deletes a session
     * @param sessionId - Session ID
     */
    async delete(sessionId: string): Promise<void>

    /**
     * Gets session tree (with branches)
     * @param sessionId - Root session ID
     */
    async getTree(sessionId: string): Promise<SessionTree>
  }

  export interface SessionCreateConfig {
    parentID?: string
    title?: string
    providerID: string
    modelID: string
    agent: Agent.Info
    systemPrompt?: string
    temperature?: number
    maxTokens?: number
  }
}
```

#### Usage Example

```typescript
import { Session, Agent } from '@opencode/core'

// Create session manager
const sessionManager = new Session.SessionManager()

// Create a new session
const session = await sessionManager.create({
  providerID: 'asi1',
  modelID: 'asi1-mini',
  agent: await Agent.get('general'),
  title: 'My Chat Session'
})

// Send a message
const response = await session.chat({
  content: 'Hello, how can you help me today?'
})

console.log('AI Response:', response.message?.parts[0]?.content)

// Get conversation history
const history = await session.getHistory()
console.log(`Conversation has ${history.length} messages`)

// Create a branch
const branch = await session.branch()
await branch.chat({ content: 'Let me try a different approach...' })

// Export session
const exported = await session.export()
console.log('Exported session:', exported.title)
```

---

## Tool System API

The Tool API provides AI models with controlled access to system operations.

```typescript
export namespace Tool {
  export interface ToolDefinition {
    id: string
    name: string
    description: string
    parameters: JSONSchema
  }

  export interface ToolContext {
    sessionId: string
    agentId: string
    workingDirectory: string
    permissions: AgentPermissions
    timestamp: number
  }

  export interface ToolResult {
    success: boolean
    data?: any
    error?: string
    metadata?: {
      executionTime: number
      warnings?: string[]
    }
  }

  export interface Tool {
    readonly id: string
    readonly name: string
    readonly description: string
    readonly parameters: JSONSchema

    /**
     * Executes the tool
     * @param params - Tool parameters
     * @param context - Execution context
     */
    execute(params: any, context: ToolContext): Promise<ToolResult>

    /**
     * Validates tool parameters
     * @param params - Parameters to validate
     */
    validate?(params: any): boolean

    /**
     * Gets cache key for result caching
     * @param params - Tool parameters
     */
    getCacheKey?(params: any): string
  }

  export abstract class AbstractTool implements Tool {
    abstract readonly id: string
    abstract readonly name: string
    abstract readonly description: string
    abstract readonly parameters: JSONSchema

    async execute(params: any, context: ToolContext): Promise<ToolResult>

    protected abstract executeImpl(
      params: any, 
      context: ToolContext
    ): Promise<any>

    protected validateParameters(params: any): boolean
  }

  export namespace Registry {
    /**
     * Gets all available tools for a provider/model
     * @param providerId - Provider ID
     * @param modelId - Model ID
     */
    export function tools(
      providerId: string, 
      modelId: string
    ): Promise<ToolDefinition[]>

    /**
     * Gets enabled tools for an agent
     * @param providerId - Provider ID
     * @param modelId - Model ID
     * @param agent - Agent configuration
     */
    export function enabled(
      providerId: string,
      modelId: string,
      agent: Agent.Info
    ): Promise<Record<string, boolean>>

    /**
     * Executes a tool
     * @param toolId - Tool ID
     * @param params - Tool parameters
     * @param context - Execution context
     */
    export function execute(
      toolId: string,
      params: any,
      context: ToolContext
    ): Promise<ToolResult>

    /**
     * Registers a custom tool
     * @param tool - Tool class
     */
    export function register(tool: new () => Tool): void
  }
}
```

#### Built-in Tools

##### Bash Tool

```typescript
export interface BashParams {
  command: string
  timeout?: number
  description: string
}

export interface BashResult {
  stdout: string
  stderr: string
  exitCode: number
  success: boolean
}

// Usage
const result = await Tool.Registry.execute('bash', {
  command: 'ls -la',
  description: 'List files in current directory'
}, context) as BashResult
```

##### File Tools

```typescript
// Read Tool
export interface ReadParams {
  filePath: string
  offset?: number
  limit?: number
}

// Edit Tool
export interface EditParams {
  filePath: string
  oldString: string
  newString: string
  replaceAll?: boolean
}

// Write Tool
export interface WriteParams {
  filePath: string
  content: string
  createDirectories?: boolean
}

// Usage examples
const fileContent = await Tool.Registry.execute('read', {
  filePath: '/path/to/file.txt'
}, context)

await Tool.Registry.execute('edit', {
  filePath: '/path/to/file.txt',
  oldString: 'old text',
  newString: 'new text'
}, context)

await Tool.Registry.execute('write', {
  filePath: '/path/to/new-file.txt',
  content: 'Hello, world!'
}, context)
```

##### Search Tools

```typescript
// Grep Tool
export interface GrepParams {
  pattern: string
  path?: string
  include?: string
  caseSensitive?: boolean
}

// Glob Tool
export interface GlobParams {
  pattern: string
  path?: string
  followSymlinks?: boolean
}

// Usage examples
const searchResults = await Tool.Registry.execute('grep', {
  pattern: 'function.*export',
  include: '*.ts'
}, context)

const files = await Tool.Registry.execute('glob', {
  pattern: '**/*.md'
}, context)
```

#### Custom Tool Example

```typescript
import { Tool } from '@opencode/core'

class MyCustomTool extends Tool.AbstractTool {
  readonly id = "my-tool"
  readonly name = "My Custom Tool"
  readonly description = "Does something useful"
  
  readonly parameters = {
    type: "object",
    properties: {
      input: { type: "string" },
      options: { type: "object" }
    },
    required: ["input"]
  }

  protected async executeImpl(params: any, context: Tool.ToolContext): Promise<any> {
    const { input, options = {} } = params
    
    // Your tool logic here
    return {
      processed: input,
      options,
      timestamp: Date.now()
    }
  }
}

// Register the tool
Tool.Registry.register(MyCustomTool)
```

---

## Configuration API

The Configuration API manages application settings and preferences.

```typescript
export namespace Config {
  export type Permission = "allow" | "deny" | "ask"

  export interface Config {
    // Model configuration
    model?: string
    smallModel?: string
    provider?: Record<string, ProviderConfig>
    
    // Agent configuration
    agent?: Record<string, AgentConfig>
    
    // Tool configuration
    tools?: Record<string, boolean>
    
    // Permission configuration
    permission?: {
      edit?: Permission
      bash?: Record<string, Permission>
      webfetch?: Permission
    }
    
    // UI configuration
    theme?: string
    layout?: string
    tui?: {
      scrollSpeed?: number
    }
    
    // Feature flags
    experimental?: Record<string, any>
    
    // MCP servers
    mcp?: Record<string, MCPConfig>
    
    // Other settings
    autoshare?: boolean
    autoupdate?: boolean
    username?: string
  }

  export interface ProviderConfig {
    apiKey?: string
    baseURL?: string
    region?: string
    models?: Record<string, ModelConfig>
  }

  export interface AgentConfig {
    prompt?: string
    description?: string
    temperature?: number
    topP?: number
    model?: string
    tools?: Record<string, boolean>
    permission?: {
      edit?: Permission
      bash?: Record<string, Permission>
      webfetch?: Permission
    }
  }

  export interface ModelConfig {
    enabled?: boolean
    maxTokens?: number
    temperature?: number
  }

  /**
   * Gets the current configuration
   */
  export function get(): Promise<Config>

  /**
   * Updates configuration
   * @param updates - Configuration updates
   */
  export function update(updates: Partial<Config>): Promise<void>

  /**
   * Gets configuration file path
   */
  export function getPath(): string

  /**
   * Watches for configuration changes
   * @param callback - Change handler
   * @returns Unwatch function
   */
  export function watch(callback: (config: Config) => void): () => void

  /**
   * Validates configuration
   * @param config - Configuration to validate
   */
  export function validate(config: any): Config

  /**
   * Gets default configuration
   */
  export function getDefaults(): Config
}
```

#### Usage Example

```typescript
import { Config } from '@opencode/core'

// Get current configuration
const config = await Config.get()
console.log('Current model:', config.model)

// Update configuration
await Config.update({
  model: 'asi1-extended',
  theme: 'dark',
  agent: {
    general: {
      temperature: 0.7,
      tools: {
        bash: true,
        webfetch: false
      }
    }
  }
})

// Watch for changes
const unwatch = Config.watch((newConfig) => {
  console.log('Configuration updated:', newConfig.model)
})

// Stop watching
unwatch()
```

---

## Event Bus API

The Event Bus API provides type-safe event communication across the system.

```typescript
export namespace Bus {
  export type EventDefinition = ReturnType<typeof event>

  /**
   * Defines an event type
   * @param type - Event type string
   * @param properties - Zod schema for event properties
   */
  export function event<Type extends string, Properties extends ZodType>(
    type: Type, 
    properties: Properties
  ): { type: Type; properties: Properties }

  /**
   * Publishes an event
   * @param def - Event definition
   * @param properties - Event properties
   */
  export function publish<Definition extends EventDefinition>(
    def: Definition,
    properties: z.output<Definition["properties"]>
  ): Promise<void>

  /**
   * Subscribes to an event
   * @param def - Event definition
   * @param callback - Event handler
   * @returns Unsubscribe function
   */
  export function subscribe<Definition extends EventDefinition>(
    def: Definition,
    callback: (event: {
      type: Definition["type"]
      properties: z.infer<Definition["properties"]>
    }) => void
  ): () => void

  /**
   * Subscribes to all events
   * @param callback - Event handler
   * @returns Unsubscribe function
   */
  export function subscribeAll(
    callback: (event: any) => void
  ): () => void
}
```

#### Built-in Events

```typescript
// Session events
export const SessionCreated = Bus.event("session.created", z.object({
  sessionId: z.string(),
  parentID: z.string().optional(),
  timestamp: z.number()
}))

export const SessionUpdated = Bus.event("session.updated", z.object({
  sessionId: z.string(),
  changes: z.record(z.any()),
  timestamp: z.number()
}))

// File events
export const FileEdited = Bus.event("file.edited", z.object({
  path: z.string(),
  sessionId: z.string(),
  timestamp: z.number()
}))

// Tool events
export const ToolExecuted = Bus.event("tool.executed", z.object({
  toolId: z.string(),
  params: z.any(),
  result: z.any(),
  executionTime: z.number(),
  timestamp: z.number()
}))
```

#### Usage Example

```typescript
import { Bus } from '@opencode/core'

// Define custom event
const MyEvent = Bus.event("my.event", z.object({
  message: z.string(),
  count: z.number()
}))

// Subscribe to event
const unsubscribe = Bus.subscribe(MyEvent, (event) => {
  console.log(`Received: ${event.properties.message}`)
  console.log(`Count: ${event.properties.count}`)
})

// Publish event
await Bus.publish(MyEvent, {
  message: "Hello World",
  count: 42
})

// Subscribe to all events
const unsubscribeAll = Bus.subscribeAll((event) => {
  console.log(`Event: ${event.type}`, event.properties)
})

// Cleanup
unsubscribe()
unsubscribeAll()
```

---

## Storage API

The Storage API provides persistent data storage with automatic serialization.

```typescript
export namespace Storage {
  export interface Storage {
    /**
     * Sets a value in storage
     * @param key - Storage key
     * @param value - Value to store
     */
    set(key: string, value: any): Promise<void>

    /**
     * Gets a value from storage
     * @param key - Storage key
     */
    get(key: string): Promise<any>

    /**
     * Deletes a value from storage
     * @param key - Storage key
     */
    delete(key: string): Promise<void>

    /**
     * Gets all keys matching a pattern
     * @param pattern - Glob pattern
     */
    keys(pattern?: string): Promise<string[]>

    /**
     * Checks if a key exists
     * @param key - Storage key
     */
    has(key: string): Promise<boolean>

    /**
     * Clears all storage
     */
    clear(): Promise<void>
  }

  /**
   * Gets the default storage instance
   */
  export function getInstance(): Storage

  /**
   * Creates a storage instance with custom path
   * @param path - Storage directory path
   */
  export function create(path: string): Storage
}
```

#### Usage Example

```typescript
import { Storage } from '@opencode/core'

// Get default storage
const storage = Storage.getInstance()

// Store data
await storage.set('user:preferences', {
  theme: 'dark',
  language: 'en',
  notifications: true
})

// Retrieve data
const preferences = await storage.get('user:preferences')
console.log('Theme:', preferences.theme)

// List keys
const userKeys = await storage.keys('user:*')
console.log('User keys:', userKeys)

// Check existence
const exists = await storage.has('user:preferences')
console.log('Preferences exist:', exists)

// Delete data
await storage.delete('user:preferences')
```

---

## CLI API

The CLI API provides programmatic access to ASI_Code's command-line interface.

```typescript
export namespace CLI {
  export interface CommandContext {
    args: string[]
    options: Record<string, any>
    cwd: string
    app: App.Info
  }

  export interface Command {
    name: string
    description: string
    options?: Record<string, OptionDefinition>
    
    /**
     * Executes the command
     * @param context - Command context
     */
    execute(context: CommandContext): Promise<void>
  }

  export interface OptionDefinition {
    type: 'string' | 'boolean' | 'number'
    description: string
    default?: any
    required?: boolean
  }

  export class CommandRegistry {
    /**
     * Registers a command
     * @param command - Command implementation
     */
    register(command: Command): void

    /**
     * Executes a command
     * @param name - Command name
     * @param args - Command arguments
     * @param options - Command options
     */
    async execute(
      name: string, 
      args: string[], 
      options: Record<string, any>
    ): Promise<void>

    /**
     * Lists all registered commands
     */
    list(): Command[]
  }

  /**
   * Runs the CLI with given arguments
   * @param args - Command line arguments
   */
  export function run(args: string[]): Promise<void>

  /**
   * Gets the command registry
   */
  export function getRegistry(): CommandRegistry
}
```

#### Built-in Commands

```typescript
// Chat command
await CLI.run(['chat', '--model', 'asi1-mini'])

// Session commands
await CLI.run(['session', 'list'])
await CLI.run(['session', 'create', '--title', 'My Session'])
await CLI.run(['session', 'delete', 'session-id'])

// Model commands
await CLI.run(['models', 'list'])
await CLI.run(['models', 'test', 'asi1-mini'])

// Configuration commands
await CLI.run(['config', 'get', 'model'])
await CLI.run(['config', 'set', 'model', 'asi1-extended'])
```

#### Custom Command Example

```typescript
import { CLI } from '@opencode/core'

// Define custom command
const myCommand: CLI.Command = {
  name: 'hello',
  description: 'Greets the user',
  options: {
    name: {
      type: 'string',
      description: 'Name to greet',
      default: 'World'
    }
  },
  
  async execute(context) {
    const name = context.options.name || 'World'
    console.log(`Hello, ${name}!`)
  }
}

// Register command
const registry = CLI.getRegistry()
registry.register(myCommand)

// Use command
await CLI.run(['hello', '--name', 'Alice'])
```

---

## Error Handling

All APIs use consistent error handling with typed error classes:

```typescript
// Base error class
export class OpenCodeError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly details?: any
  ) {
    super(message)
    this.name = this.constructor.name
  }
}

// Specific error types
export class ConfigurationError extends OpenCodeError {
  constructor(message: string, details?: any) {
    super(message, 'CONFIGURATION_ERROR', details)
  }
}

export class ProviderError extends OpenCodeError {
  constructor(message: string, details?: any) {
    super(message, 'PROVIDER_ERROR', details)
  }
}

export class SessionError extends OpenCodeError {
  constructor(message: string, details?: any) {
    super(message, 'SESSION_ERROR', details)
  }
}

export class ToolError extends OpenCodeError {
  constructor(message: string, details?: any) {
    super(message, 'TOOL_ERROR', details)
  }
}

// Usage
try {
  const session = await sessionManager.create(config)
} catch (error) {
  if (error instanceof SessionError) {
    console.error('Session error:', error.message)
    console.error('Details:', error.details)
  } else {
    console.error('Unexpected error:', error)
  }
}
```

---

## Type Definitions

### Common Types

```typescript
// Identifier types
export type SessionID = string & { readonly __brand: unique symbol }
export type MessageID = string & { readonly __brand: unique symbol }
export type UserID = string & { readonly __brand: unique symbol }

// AI Model types
export interface LanguageModelUsage {
  promptTokens: number
  completionTokens: number
  totalTokens: number
}

export interface Message {
  id: MessageID
  sessionID: SessionID
  role: 'user' | 'assistant' | 'system'
  content: MessageContent[]
  timestamp: number
  usage?: LanguageModelUsage
}

export type MessageContent = 
  | { type: 'text'; text: string }
  | { type: 'image'; image: string }
  | { type: 'tool-call'; toolCall: ToolCall }
  | { type: 'tool-result'; toolResult: ToolResult }

// Permission types
export type Permission = 'allow' | 'deny' | 'ask'

export interface AgentPermissions {
  edit: Permission
  bash: Record<string, Permission>
  webfetch: Permission
}

// JSON Schema type
export interface JSONSchema {
  type: string
  properties?: Record<string, JSONSchema>
  items?: JSONSchema
  required?: string[]
  additionalProperties?: boolean
  [key: string]: any
}
```

This comprehensive API reference provides complete documentation for all major ASI_Code APIs, enabling developers to effectively integrate with and extend the platform.