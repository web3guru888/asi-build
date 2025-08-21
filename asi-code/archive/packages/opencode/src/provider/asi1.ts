/**
 * ASI1 Provider Implementation
 * Connects ASI_Code to the ASI1 LLM API
 */

import { 
  LanguageModel,
  NoSuchModelError,
  streamText
} from "ai"
import { Log } from "../util/log"

export namespace ASI1Provider {
  const log = Log.create({ service: "asi1-provider" })

  /**
   * ASI1 API Configuration
   */
  export interface Config {
    apiKey: string
    baseURL?: string
    sessionId?: string
    delegatedFor?: string
  }

  /**
   * ASI1 Model IDs
   */
  export enum ModelID {
    MINI = "asi1-mini",          // Default model
    FAST = "asi1-fast",          // Fast inference
    EXTENDED = "asi1-extended",  // Extended context
    GRAPH = "asi1-graph"         // Graph processing
  }

  /**
   * ASI1 Chat Message
   */
  interface ChatMessage {
    role: "user" | "assistant" | "system"
    content: string
  }

  /**
   * ASI1 Tool Definition
   */
  interface Tool {
    name: string
    description: string
    parameters: Record<string, any>
  }

  /**
   * ASI1 Completion Request
   */
  interface CompletionRequest {
    messages: ChatMessage[]
    model: string
    agent_address?: string
    max_tokens?: number
    planner_mode?: boolean
    stream?: boolean
    study_mode?: boolean
    temperature?: number
    tools?: Tool[]
    web_search?: boolean
  }

  /**
   * ASI1 Completion Response
   */
  interface CompletionResponse {
    choices: Array<{
      finish_reason: string
      delta?: {
        content: string
        role: string
        reasoning?: string
        tool_calls?: Array<{
          id: string
          tool_name: string
          args: Record<string, any>
          result: Record<string, any>
        }>
      }
      index: number
      message?: {
        content: string
        role: string
        reasoning?: string
        tool_calls?: Array<{
          id: string
          tool_name: string
          args: Record<string, any>
          result: Record<string, any>
        }>
      }
    }>
    id: string
    model?: string
    usage: {
      completion_tokens: number
      prompt_tokens: number
      total_tokens: number
    }
    executable_data?: any[]
    intermediate_steps?: any[]
    conversation_id?: string | null
    thought?: string[]
    metadata?: Record<string, any>
  }

  /**
   * ASI1 Language Model Implementation
   * Implements the AI SDK v2 LanguageModel interface
   */
  export class ASI1LanguageModel implements LanguageModel {
    readonly specificationVersion = "v1" as const
    readonly provider = "asi1"
    readonly modelId: string
    readonly defaultObjectGenerationMode = "json" as const
    readonly supportedUrls = []  // Required by LanguageModelV2

    private config: Config

    constructor(modelId: string, config: Config) {
      this.modelId = modelId
      this.config = {
        baseURL: "https://api.asi1.ai",
        ...config
      }
      
      log.info("ASI1 model initialized", { modelId })
    }

    async doGenerate(options: any): Promise<any> {
      log.info("ASI1 doGenerate called", { 
        modelId: this.modelId,
        hasOptions: !!options,
        messageCount: options?.messages?.length || 0
      })
      
      const messages = this.convertMessages(options.messages)
      const tools = this.convertTools(options.tools)

      const request: CompletionRequest = {
        messages,
        model: this.modelId,
        max_tokens: options.maxTokens,
        temperature: options.temperature,
        stream: false,
        tools: tools.length > 0 ? tools : undefined,
        web_search: options.webSearch,
        planner_mode: options.plannerMode,
        study_mode: options.studyMode
      }

      const response = await this.callAPI(request)
      
      return this.convertResponse(response)
    }

    async doStream(options: any): Promise<{ stream: ReadableStream<any> }> {
      log.info("ASI1 doStream called", { 
        modelId: this.modelId, 
        apiKey: this.config.apiKey ? "SET" : "NOT_SET",
        hasOptions: !!options,
        messageCount: options?.messages?.length || 0
      })
      
      // Debug: Log the stream creation
      log.info("Creating stream for ASI1")
      
      if (!options) {
        throw new Error("ASI1 doStream called with undefined options")
      }
      
      // Ensure messages are provided
      if (!options.messages || !Array.isArray(options.messages)) {
        log.warn("No messages provided, creating default")
        options.messages = []
      }
      
      // Log raw messages for debugging
      log.info("Raw messages before conversion", { 
        messages: options.messages,
        messagesDetail: options.messages?.map((m: any) => ({
          role: m?.role,
          contentType: typeof m?.content,
          contentLength: Array.isArray(m?.content) ? m.content.length : undefined,
          content: m?.content
        }))
      })
      
      let messages = this.convertMessages(options.messages)
      
      // ASI1 requires at least one user or assistant message - add a default if empty
      if (messages.length === 0) {
        log.warn("No messages provided, adding default user message")
        messages = [{
          role: "user" as const,
          content: "Hello"
        }]
      }
      
      const tools = this.convertTools(options.tools)

      const request: CompletionRequest = {
        messages,
        model: this.modelId,
        max_tokens: options.maxTokens,
        temperature: options.temperature,
        stream: true,
        tools: tools.length > 0 ? tools : undefined,
        web_search: options.webSearch,
        planner_mode: options.plannerMode,
        study_mode: options.studyMode
      }

      log.info("ASI1 streaming request", { url: `${this.config.baseURL}/v1/chat/completions`, request })

      const response = await fetch(`${this.config.baseURL}/v1/chat/completions`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${this.config.apiKey}`,
          "Content-Type": "application/json",
          ...(this.config.sessionId && { "x-session-id": this.config.sessionId }),
          ...(this.config.delegatedFor && { "X-Delegated-For": this.config.delegatedFor })
        },
        body: JSON.stringify(request)
      })

      log.info("Fetch completed", { status: response.status, ok: response.ok })

      if (!response.ok) {
        const errorBody = await response.text()
        log.error("ASI1 API error", { 
          status: response.status, 
          statusText: response.statusText, 
          body: errorBody
        })
        
        // Handle authentication errors specifically
        if (response.status === 401) {
          throw new Error(`ASI1 Authentication failed: ${errorBody}. Please check your ASI1_API_KEY environment variable.`)
        }
        
        throw new Error(`ASI1 API error: ${response.status} ${response.statusText}: ${errorBody}`)
      }

      // Process the stream immediately with proper SSE parsing
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      
      // Create and return the stream using standard ReadableStream
      const resultStream = new ReadableStream<any>({
        async pull(controller) {
          try {
            const { done, value } = await reader.read()
            
            if (done) {
              // Process any remaining buffer
              if (buffer.trim()) {
                log.warn("Incomplete SSE data in buffer", { buffer })
              }
              controller.close()
              return
            }

            // Decode and add to buffer
            buffer += decoder.decode(value, { stream: true })
            
            // Split by newlines but keep incomplete lines
            const lines = buffer.split("\n")
            buffer = lines.pop() || ""

            for (const line of lines) {
              const trimmed = line.trim()
              if (!trimmed) continue
              
              if (trimmed.startsWith("data: ")) {
                const data = trimmed.slice(6)
                
                if (data === "[DONE]") {
                  controller.close()
                  return
                }

                try {
                  const parsed = JSON.parse(data) as CompletionResponse
                  const choice = parsed.choices?.[0]
                  
                  if (!choice) continue
                  
                  // Emit text delta
                  if (choice.delta?.content) {
                    const event = {
                      type: "text-delta" as const,
                      text: choice.delta.content,
                      // Also include delta for compatibility
                      delta: choice.delta.content
                    }
                    log.info("Emitting text-delta", { content: choice.delta.content })
                    controller.enqueue(event)
                  }
                  
                  // Emit tool calls
                  if (choice.delta?.tool_calls) {
                    for (const tc of choice.delta.tool_calls) {
                      controller.enqueue({
                        type: "tool-call",
                        toolCallType: "function",
                        toolCallId: tc.id,
                        toolName: tc.tool_name,
                        args: JSON.stringify(tc.args)
                      })
                    }
                  }

                  // Emit finish event
                  if (choice.finish_reason) {
                    controller.enqueue({
                      type: "finish",
                      finishReason: choice.finish_reason,
                      usage: {
                        promptTokens: parsed.usage?.prompt_tokens || 0,
                        completionTokens: parsed.usage?.completion_tokens || 0
                      }
                    })
                  }
                } catch (e) {
                  log.error("Failed to parse SSE data", { 
                    error: e, 
                    data,
                    line: trimmed 
                  })
                }
              }
            }
          } catch (error) {
            log.error("Stream pull error", { error })
            controller.error(error)
          }
        },
        
        cancel() {
          log.info("Stream cancelled")
          reader.cancel()
        }
      })
      
      log.info("ASI1 doStream returning stream", { 
        streamType: typeof resultStream,
        hasStream: !!resultStream,
        streamConstructor: resultStream?.constructor?.name
      })
      
      // Return in the format expected by AI SDK v2
      return { 
        stream: resultStream,
        // Optional: can add request and response metadata if needed
        // request: { body: request },
        // response: { headers: {} }
      }
    }

    private async callAPI(request: CompletionRequest): Promise<CompletionResponse> {
      const response = await fetch(`${this.config.baseURL}/v1/chat/completions`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${this.config.apiKey}`,
          "Content-Type": "application/json",
          ...(this.config.sessionId && { "x-session-id": this.config.sessionId }),
          ...(this.config.delegatedFor && { "X-Delegated-For": this.config.delegatedFor })
        },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        const errorBody = await response.text()
        log.error("ASI1 API error (non-streaming)", { 
          status: response.status, 
          statusText: response.statusText, 
          body: errorBody,
          url: `${this.config.baseURL}/v1/chat/completions`,
          request
        })
        if (response.status === 404) {
          throw new NoSuchModelError({ modelId: this.modelId, modelType: "languageModel" as const })
        }
        
        // Handle authentication errors specifically
        if (response.status === 401) {
          throw new Error(`ASI1 Authentication failed: ${errorBody}. Please check your ASI1_API_KEY environment variable.`)
        }
        
        throw new Error(`ASI1 API error: ${response.status} ${response.statusText}: ${errorBody}`)
      }

      return response.json()
    }

    private convertMessages(messages: any[]): ChatMessage[] {
      if (!messages || !Array.isArray(messages)) {
        log.warn("convertMessages called with invalid messages", { messages, type: typeof messages })
        return []
      }
      
      const converted = messages.map(msg => {
        // Handle different message content formats
        let content = ""
        
        if (!msg) {
          log.warn("Undefined message in array")
          return null
        }
        
        if (typeof msg.content === "string") {
          content = msg.content
        } else if (Array.isArray(msg.content)) {
          content = msg.content.map((part: any) => {
            if (!part) {
              log.warn("Undefined part in message content")
              return ""
            }
            if (typeof part === "string") return part
            if (part?.type === "text" && part?.text) return part.text
            if (part?.text) return part.text
            log.warn("Unknown part format", { part })
            return ""
          }).join("")
        } else if (msg.content?.text) {
          content = msg.content.text
        } else {
          log.warn("Unknown message content format", { content: msg.content, type: typeof msg.content })
        }
        
        return {
          role: msg.role || "user",
          content
        }
      }).filter(msg => msg !== null)
      
      log.info("Converted messages", { 
        original: messages.length,
        converted: converted.length,
        messages: converted 
      })
      
      return converted
    }

    private convertTools(tools: any[] = []): Tool[] {
      if (!tools || !Array.isArray(tools)) {
        return []
      }
      return tools.filter(tool => tool && typeof tool === 'object').map(tool => ({
        name: tool.name || tool.id || "unknown",
        description: tool.description || "",
        parameters: tool.parameters || tool.inputSchema || {}
      }))
    }

    private convertResponse(response: CompletionResponse): any {
      const choice = response.choices[0]
      const message = choice.message || choice.delta

      return {
        finishReason: choice.finish_reason,
        usage: {
          promptTokens: response.usage.prompt_tokens,
          completionTokens: response.usage.completion_tokens
        },
        text: message?.content || "",
        toolCalls: message?.tool_calls?.map(tc => ({
          toolCallType: "function",
          toolCallId: tc.id,
          toolName: tc.tool_name,
          args: JSON.stringify(tc.args)
        })) || []
      }
    }

  }

  /**
   * Create an ASI1 provider instance
   */
  export function createProvider(config: Config) {
    return {
      languageModel(modelId: string) {
        if (!Object.values(ModelID).includes(modelId as ModelID)) {
          log.warn("Unknown ASI1 model", { modelId })
        }
        return new ASI1LanguageModel(modelId, config)
      }
    }
  }

  /**
   * Provider metadata for models.json
   */
  export const PROVIDER_METADATA = {
    id: "asi1",
    name: "ASI1",
    npm: undefined, // Built-in provider
    api: "https://api.asi1.ai",
    env: ["ASI1_API_KEY"],
    models: {
      [ModelID.MINI]: {
        id: ModelID.MINI,
        name: "ASI1 Mini",
        release_date: "2025-01-20",
        attachment: true,
        reasoning: true,
        temperature: true,
        tool_call: true,
        cost: {
          input: 0.001,
          output: 0.002,
          cache_read: 0.0005,
          cache_write: 0.001
        },
        limit: {
          context: 128000,
          output: 8192
        },
        options: {}
      },
      [ModelID.FAST]: {
        id: ModelID.FAST,
        name: "ASI1 Fast",
        release_date: "2025-01-20",
        attachment: true,
        reasoning: true,
        temperature: true,
        tool_call: true,
        cost: {
          input: 0.0005,
          output: 0.001,
          cache_read: 0.0002,
          cache_write: 0.0005
        },
        limit: {
          context: 64000,
          output: 4096
        },
        options: {}
      },
      [ModelID.EXTENDED]: {
        id: ModelID.EXTENDED,
        name: "ASI1 Extended",
        release_date: "2025-01-20",
        attachment: true,
        reasoning: true,
        temperature: true,
        tool_call: true,
        cost: {
          input: 0.005,
          output: 0.01,
          cache_read: 0.0025,
          cache_write: 0.005
        },
        limit: {
          context: 512000,
          output: 32768
        },
        options: {}
      },
      [ModelID.GRAPH]: {
        id: ModelID.GRAPH,
        name: "ASI1 Graph",
        release_date: "2025-01-20",
        attachment: true,
        reasoning: true,
        temperature: true,
        tool_call: true,
        cost: {
          input: 0.01,
          output: 0.02,
          cache_read: 0.005,
          cache_write: 0.01
        },
        limit: {
          context: 256000,
          output: 16384
        },
        options: {
          graph_processing: true
        }
      }
    }
  }
}