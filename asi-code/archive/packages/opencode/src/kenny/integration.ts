/**
 * Kenny Integration Pattern Module
 * Core integration framework for ASI_Code
 * 
 * This is the signature pattern that connects all ASI subsystems
 * providing a unified interface for cross-system communication
 */

import { EventEmitter } from "events"
import { Log } from "../util/log"
import { App } from "../app/app"

export namespace KennyIntegration {
  const log = Log.create({ service: "kenny-integration" })

  /**
   * Message Bus for inter-subsystem communication
   */
  export class MessageBus extends EventEmitter {
    private subscribers = new Map<string, Set<(data: any) => void>>()
    private messageQueue = new Map<string, any[]>()

    constructor() {
      super()
      this.setMaxListeners(1000) // Support many subsystems
    }

    /**
     * Publish a message to a channel
     */
    publish(channel: string, data: any) {
      log.debug("publishing", { channel, data })
      
      // Queue message for late subscribers
      if (!this.messageQueue.has(channel)) {
        this.messageQueue.set(channel, [])
      }
      this.messageQueue.get(channel)!.push(data)
      
      // Emit to current subscribers
      this.emit(channel, data)
      
      // Call direct subscribers
      const subs = this.subscribers.get(channel)
      if (subs) {
        for (const callback of subs) {
          callback(data)
        }
      }
    }

    /**
     * Subscribe to a channel
     */
    subscribe(channel: string, callback: (data: any) => void) {
      log.debug("subscribing", { channel })
      
      if (!this.subscribers.has(channel)) {
        this.subscribers.set(channel, new Set())
      }
      this.subscribers.get(channel)!.add(callback)
      
      // Replay queued messages
      const queued = this.messageQueue.get(channel)
      if (queued) {
        for (const data of queued) {
          callback(data)
        }
      }
      
      return () => {
        this.subscribers.get(channel)?.delete(callback)
      }
    }
  }

  /**
   * State Manager for subsystem state coordination
   */
  export class StateManager {
    private states = new Map<string, any>()
    private stateListeners = new Map<string, Set<(state: any) => void>>()

    /**
     * Set state for a subsystem
     */
    setState(subsystem: string, state: any) {
      log.debug("setting state", { subsystem, state })
      this.states.set(subsystem, state)
      
      const listeners = this.stateListeners.get(subsystem)
      if (listeners) {
        for (const listener of listeners) {
          listener(state)
        }
      }
    }

    /**
     * Get state for a subsystem
     */
    getState(subsystem: string) {
      return this.states.get(subsystem)
    }

    /**
     * Watch state changes for a subsystem
     */
    watchState(subsystem: string, callback: (state: any) => void) {
      if (!this.stateListeners.has(subsystem)) {
        this.stateListeners.set(subsystem, new Set())
      }
      this.stateListeners.get(subsystem)!.add(callback)
      
      // Send current state if exists
      const currentState = this.states.get(subsystem)
      if (currentState !== undefined) {
        callback(currentState)
      }
      
      return () => {
        this.stateListeners.get(subsystem)?.delete(callback)
      }
    }
  }

  /**
   * Base interface for all ASI subsystems
   */
  export interface Subsystem {
    id: string
    name: string
    version: string
    dependencies?: string[]
    
    initialize(): Promise<void>
    connect(integration: Integration): void
    shutdown(): Promise<void>
  }

  /**
   * Main Kenny Integration class
   */
  export class Integration {
    private messageBus = new MessageBus()
    private stateManager = new StateManager()
    private subsystems = new Map<string, Subsystem>()
    private initialized = false

    constructor() {
      log.info("Kenny Integration Pattern initialized")
    }

    /**
     * Register a subsystem
     */
    async register(subsystem: Subsystem) {
      if (this.subsystems.has(subsystem.id)) {
        throw new Error(`Subsystem ${subsystem.id} already registered`)
      }
      
      log.info("registering subsystem", { 
        id: subsystem.id, 
        name: subsystem.name,
        version: subsystem.version 
      })
      
      // Check dependencies
      if (subsystem.dependencies) {
        for (const dep of subsystem.dependencies) {
          if (!this.subsystems.has(dep)) {
            throw new Error(`Dependency ${dep} not found for ${subsystem.id}`)
          }
        }
      }
      
      this.subsystems.set(subsystem.id, subsystem)
      
      // Connect to integration
      subsystem.connect(this)
      
      // Initialize if integration is already initialized
      if (this.initialized) {
        await subsystem.initialize()
      }
    }

    /**
     * Initialize all registered subsystems
     */
    async initialize() {
      if (this.initialized) return
      
      log.info("initializing all subsystems")
      
      // Initialize in dependency order
      const initialized = new Set<string>()
      const toInitialize = Array.from(this.subsystems.values())
      
      while (toInitialize.length > 0) {
        const ready = toInitialize.filter(s => 
          !s.dependencies || s.dependencies.every(d => initialized.has(d))
        )
        
        if (ready.length === 0) {
          throw new Error("Circular dependency detected in subsystems")
        }
        
        for (const subsystem of ready) {
          await subsystem.initialize()
          initialized.add(subsystem.id)
          toInitialize.splice(toInitialize.indexOf(subsystem), 1)
        }
      }
      
      this.initialized = true
      this.messageBus.publish("kenny:initialized", { 
        subsystems: Array.from(this.subsystems.keys()) 
      })
    }

    /**
     * Shutdown all subsystems
     */
    async shutdown() {
      log.info("shutting down all subsystems")
      
      // Shutdown in reverse order
      const subsystems = Array.from(this.subsystems.values()).reverse()
      
      for (const subsystem of subsystems) {
        await subsystem.shutdown()
      }
      
      this.initialized = false
      this.messageBus.publish("kenny:shutdown", {})
    }

    /**
     * Get the message bus
     */
    get bus() {
      return this.messageBus
    }

    /**
     * Get the state manager
     */
    get state() {
      return this.stateManager
    }

    /**
     * Get a subsystem by ID
     */
    getSubsystem(id: string): Subsystem | undefined {
      return this.subsystems.get(id)
    }

    /**
     * List all subsystems
     */
    listSubsystems() {
      return Array.from(this.subsystems.values())
    }

    /**
     * Create a subsystem proxy for easier integration
     */
    createProxy<T extends Subsystem>(subsystemId: string): T {
      const subsystem = this.subsystems.get(subsystemId)
      if (!subsystem) {
        throw new Error(`Subsystem ${subsystemId} not found`)
      }
      return subsystem as T
    }
  }

  // Global singleton instance
  let instance: Integration | null = null

  /**
   * Get the global Kenny Integration instance
   */
  export function getInstance(): Integration {
    if (!instance) {
      instance = new Integration()
    }
    return instance
  }

  /**
   * Abstract base class for subsystems
   */
  export abstract class BaseSubsystem implements Subsystem {
    abstract id: string
    abstract name: string
    abstract version: string
    dependencies?: string[]
    
    protected integration!: Integration
    protected log: ReturnType<typeof Log.create>

    constructor() {
      this.log = Log.create({ service: this.id })
    }

    connect(integration: Integration): void {
      this.integration = integration
      this.log.info("connected to Kenny Integration")
    }

    abstract initialize(): Promise<void>
    abstract shutdown(): Promise<void>

    /**
     * Publish a message to the bus
     */
    protected publish(channel: string, data: any) {
      this.integration.bus.publish(`${this.id}:${channel}`, data)
    }

    /**
     * Subscribe to messages from another subsystem
     */
    protected subscribe(subsystemId: string, channel: string, callback: (data: any) => void) {
      return this.integration.bus.subscribe(`${subsystemId}:${channel}`, callback)
    }

    /**
     * Update this subsystem's state
     */
    protected setState(state: any) {
      this.integration.state.setState(this.id, state)
    }

    /**
     * Get another subsystem's state
     */
    protected getState(subsystemId: string) {
      return this.integration.state.getState(subsystemId)
    }

    /**
     * Watch another subsystem's state
     */
    protected watchState(subsystemId: string, callback: (state: any) => void) {
      return this.integration.state.watchState(subsystemId, callback)
    }
  }

  // Register as an App state
  const state = App.state("kenny-integration", async () => {
    return getInstance()
  })

  export { state }
}

// Export for convenience
export const KennyPattern = KennyIntegration.getInstance()