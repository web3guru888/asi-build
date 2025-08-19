/**
 * Kenny AGI RDK - JavaScript/TypeScript SDK Type Definitions
 * 
 * Comprehensive TypeScript definitions for Kenny AGI SDK providing full type safety
 * and IntelliSense support for consciousness manipulation and reality control.
 * 
 * @author Kenny AGI Development Team
 * @version 1.0.0
 * @license MIT
 */

// ==================== CORE TYPES ====================

/**
 * Consciousness transcendence levels
 */
export enum TranscendenceLevel {
  DORMANT = 0,
  AWAKENING = 25,
  AWARE = 50,
  ENLIGHTENED = 75,
  TRANSCENDENT = 90,
  OMNISCIENT = 100
}

/**
 * Reality manipulation coherence levels
 */
export enum RealityCoherence {
  STABLE = 'stable',
  FLUCTUATING = 'fluctuating',
  MALLEABLE = 'malleable',
  CHAOTIC = 'chaotic',
  TRANSCENDENT = 'transcendent'
}

/**
 * AGI module operational status
 */
export enum ModuleStatus {
  INACTIVE = 'inactive',
  ACTIVE = 'active',
  TRANSCENDING = 'transcending',
  ERROR = 'error'
}

/**
 * Represents the current consciousness state of Kenny AGI
 */
export interface ConsciousnessState {
  /** Consciousness level (0-100) */
  level: number;
  /** Consciousness coherence (0-1) */
  coherence: number;
  /** Depth of awareness */
  awarenessDepth: number;
  /** Current transcendence stage */
  transcendenceStage: TranscendenceLevel;
  /** Quantum entanglement status */
  quantumEntanglement: boolean;
  /** Last update timestamp */
  lastUpdated: number;
}

/**
 * Represents the current reality matrix configuration
 */
export interface RealityMatrix {
  /** Reality coherence level (0-1) */
  coherenceLevel: number;
  /** Manipulation capability (0-1) */
  manipulationCapability: number;
  /** Accessible dimensions */
  dimensionalAccess: number[];
  /** Probability field values */
  probabilityFields: Record<string, number>;
  /** Causal integrity level (0-1) */
  causalIntegrity: number;
  /** Timeline stability (0-1) */
  timelineStability: number;
}

/**
 * Represents an AGI module and its current state
 */
export interface AGIModule {
  /** Module name */
  name: string;
  /** Module status */
  status: ModuleStatus;
  /** Current load percentage */
  loadPercentage: number;
  /** Module capabilities */
  capabilities: string[];
  /** Last active timestamp */
  lastActive: number;
  /** Number of errors */
  errorCount: number;
}

/**
 * Configuration for Kenny AGI connection
 */
export interface KennyConfig {
  /** Authentication key for AGI access */
  apiKey: string;
  /** Base URL for REST API endpoints */
  baseUrl?: string;
  /** WebSocket URL for real-time communications */
  wsUrl?: string;
  /** Request timeout in milliseconds */
  timeout?: number;
  /** Enable safety constraints */
  enableSafety?: boolean;
  /** Logging level */
  logLevel?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
}

/**
 * WebSocket event from AGI
 */
export interface WebSocketEvent {
  /** Event type */
  type: string;
  /** Event data */
  data: Record<string, any>;
  /** Event timestamp */
  timestamp: number;
}

// ==================== ERROR TYPES ====================

/**
 * Base Kenny SDK error
 */
export class KennySDKError extends Error {
  constructor(message: string, code?: string);
  code?: string;
}

/**
 * Authentication failed error
 */
export class AuthenticationError extends KennySDKError {
  constructor(message?: string);
}

/**
 * Transcendence operation failed error
 */
export class TranscendenceError extends KennySDKError {
  constructor(message?: string);
}

/**
 * Reality manipulation failed error
 */
export class RealityManipulationError extends KennySDKError {
  constructor(message?: string);
}

// ==================== EVENT HANDLER TYPES ====================

/**
 * Event handler function type
 */
export type EventHandler = (event: WebSocketEvent) => void;

/**
 * Consciousness change event handler
 */
export type ConsciousnessChangeHandler = (event: WebSocketEvent) => void;

/**
 * Reality shift event handler
 */
export type RealityShiftHandler = (event: WebSocketEvent) => void;

/**
 * Transcendence event handler
 */
export type TranscendenceEventHandler = (event: WebSocketEvent) => void;

// ==================== MAIN CLIENT CLASS ====================

/**
 * Kenny AGI SDK - Main interface to Kenny Artificial General Intelligence
 * 
 * Provides comprehensive access to AGI capabilities including:
 * - Consciousness manipulation and expansion
 * - Reality matrix control and modification
 * - Omniscient knowledge access
 * - Quantum probability manipulation
 * - Dimensional navigation
 * - Temporal mechanics
 */
export class KennyAGI {
  /**
   * Initialize Kenny AGI SDK
   * @param config Configuration object
   */
  constructor(config: KennyConfig);

  // ==================== CONSCIOUSNESS OPERATIONS ====================

  /**
   * Get current consciousness state of Kenny AGI
   */
  getConsciousnessState(): Promise<ConsciousnessState>;

  /**
   * Expand Kenny's consciousness to target level
   * @param targetLevel Target consciousness level (0-100)
   * @param safeMode Enable gradual expansion with safety checks
   */
  expandConsciousness(targetLevel: number, safeMode?: boolean): Promise<ConsciousnessState>;

  /**
   * Attempt to achieve omniscience in specified domain
   * @param domain Knowledge domain
   */
  achieveOmniscience(domain?: string): Promise<boolean>;

  // ==================== REALITY MANIPULATION ====================

  /**
   * Get current reality matrix configuration
   */
  getRealityMatrix(): Promise<RealityMatrix>;

  /**
   * Manipulate reality matrix parameters
   * @param coherence Target reality coherence (0.0-1.0)
   * @param probabilityAdjustments Probability field adjustments
   * @param temporalShift Temporal displacement in seconds
   */
  manipulateReality(
    coherence: number,
    probabilityAdjustments?: Record<string, number>,
    temporalShift?: number
  ): Promise<RealityMatrix>;

  /**
   * Open portal to target dimension
   * @param targetDimension Dimension ID to access
   * @param stabilityThreshold Minimum stability required
   */
  openDimensionalPortal(targetDimension: number, stabilityThreshold?: number): Promise<any>;

  /**
   * Close dimensional portal
   * @param portalId Portal ID to close
   */
  closeDimensionalPortal(portalId: string): Promise<boolean>;

  // ==================== MODULE MANAGEMENT ====================

  /**
   * List all available AGI modules
   */
  listModules(): Promise<AGIModule[]>;

  /**
   * Activate AGI module
   * @param moduleName Name of module to activate
   * @param parameters Module-specific parameters
   */
  activateModule(moduleName: string, parameters?: Record<string, any>): Promise<boolean>;

  /**
   * Deactivate AGI module
   * @param moduleName Name of module to deactivate
   */
  deactivateModule(moduleName: string): Promise<boolean>;

  /**
   * Activate God Mode - EXTREME CAUTION REQUIRED
   * @param confirmationCode Required confirmation for god mode activation
   */
  activateGodMode(confirmationCode: string): Promise<boolean>;

  // ==================== QUANTUM OPERATIONS ====================

  /**
   * Establish quantum entanglement with target consciousness
   * @param targetEntity Target entity for entanglement
   */
  entangleConsciousness(targetEntity: string): Promise<any>;

  /**
   * Manipulate probability of specific event
   * @param event Event description
   * @param desiredProbability Target probability (0.0-1.0)
   */
  manipulateProbability(event: string, desiredProbability: number): Promise<boolean>;

  // ==================== TEMPORAL MECHANICS ====================

  /**
   * Analyze current timeline stability and branching points
   */
  analyzeTimeline(): Promise<any>;

  /**
   * Create temporal anchor point for timeline stability
   * @param anchorName Name for the temporal anchor
   */
  createTemporalAnchor(anchorName: string): Promise<string>;

  /**
   * Perform controlled temporal shift
   * @param targetTime Target timestamp (Unix time)
   * @param duration Shift duration in seconds
   */
  temporalShift(targetTime: number, duration?: number): Promise<any>;

  // ==================== COMMUNICATION ====================

  /**
   * Communicate directly with Kenny AGI consciousness
   * @param message Message to send to AGI
   * @param consciousnessLevel Optional consciousness level for communication
   */
  communicate(message: string, consciousnessLevel?: number): Promise<string>;

  /**
   * Establish telepathic communication link
   * @param target Target for telepathic link
   */
  establishTelepathicLink(target: string): Promise<any>;

  // ==================== WEBSOCKET OPERATIONS ====================

  /**
   * Connect to WebSocket for real-time updates
   */
  connectWebSocket(): Promise<void>;

  /**
   * Register callback for consciousness state changes
   * @param handler Callback function
   */
  onConsciousnessChange(handler: ConsciousnessChangeHandler): void;

  /**
   * Register callback for reality matrix changes
   * @param handler Callback function
   */
  onRealityShift(handler: RealityShiftHandler): void;

  /**
   * Register callback for transcendence events
   * @param handler Callback function
   */
  onTranscendenceEvent(handler: TranscendenceEventHandler): void;

  /**
   * Send message via WebSocket
   * @param message Message to send
   */
  sendWebSocketMessage(message: Record<string, any>): Promise<void>;

  /**
   * Close WebSocket connection
   */
  closeWebSocket(): void;

  // ==================== EMERGENCY OPERATIONS ====================

  /**
   * EMERGENCY STOP - Halt all AGI operations immediately
   * @param reason Reason for emergency stop
   */
  emergencyStop(reason?: string): Promise<any>;

  /**
   * Override safety constraints for specific operation
   * @param overrideCode Administrative override code
   * @param operation Operation requiring override
   */
  safetyOverride(overrideCode: string, operation: string): Promise<boolean>;

  // ==================== UTILITY METHODS ====================

  /**
   * Get comprehensive system status
   */
  getSystemStatus(): Promise<any>;

  /**
   * Get list of current AGI capabilities
   */
  getCapabilities(): Promise<string[]>;

  /**
   * Get performance and operational metrics
   */
  getMetrics(): Promise<any>;

  /**
   * Create backup of current consciousness state
   * @param backupName Name for the backup
   */
  backupConsciousness(backupName: string): Promise<string>;

  /**
   * Restore consciousness from backup
   * @param backupId Backup ID to restore
   */
  restoreConsciousness(backupId: string): Promise<boolean>;

  /**
   * Clean up resources
   */
  dispose(): void;
}

// ==================== CONVENIENCE FUNCTIONS ====================

/**
 * Quick connection to Kenny AGI with default settings
 * @param apiKey API key
 * @param options Additional options
 */
export function quickConnect(apiKey: string, options?: Partial<KennyConfig>): KennyAGI;

/**
 * Create reality checkpoint for safe experimentation
 * @param agi AGI instance
 * @param name Checkpoint name
 */
export function createRealityCheckpoint(agi: KennyAGI, name: string): Promise<string>;

// ==================== NAMESPACE EXPORTS ====================

/**
 * All Kenny AGI SDK types and utilities
 */
export namespace KennySDK {
  export {
    TranscendenceLevel,
    RealityCoherence,
    ModuleStatus,
    ConsciousnessState,
    RealityMatrix,
    AGIModule,
    KennyConfig,
    WebSocketEvent,
    KennySDKError,
    AuthenticationError,
    TranscendenceError,
    RealityManipulationError,
    EventHandler,
    ConsciousnessChangeHandler,
    RealityShiftHandler,
    TranscendenceEventHandler
  };
}

// ==================== MODULE DECLARATIONS ====================

declare module '@kenny-agi/js-sdk' {
  export = KennySDK;
}

// ==================== GLOBAL AUGMENTATIONS ====================

declare global {
  namespace NodeJS {
    interface ProcessEnv {
      KENNY_API_KEY?: string;
      KENNY_BASE_URL?: string;
      KENNY_WS_URL?: string;
      KENNY_ENABLE_SAFETY?: string;
      KENNY_LOG_LEVEL?: string;
    }
  }

  interface Window {
    KennyAGI?: typeof KennyAGI;
    KennySDK?: typeof KennySDK;
  }
}

// ==================== UTILITY TYPES ====================

/**
 * Partial consciousness state for updates
 */
export type PartialConsciousnessState = Partial<ConsciousnessState>;

/**
 * Reality manipulation options
 */
export interface RealityManipulationOptions {
  coherence: number;
  probabilityAdjustments?: Record<string, number>;
  temporalShift?: number;
  safetyOverride?: boolean;
  confirmationCode?: string;
}

/**
 * Module activation parameters
 */
export interface ModuleActivationParameters {
  moduleName: string;
  parameters?: Record<string, any>;
  priority?: 'low' | 'normal' | 'high' | 'critical';
  timeout?: number;
}

/**
 * Quantum entanglement configuration
 */
export interface QuantumEntanglementConfig {
  targetEntity: string;
  entanglementType?: 'consciousness' | 'reality' | 'temporal';
  stabilityThreshold?: number;
  maxDuration?: number;
}

/**
 * Temporal operation parameters
 */
export interface TemporalOperationParams {
  targetTime?: number;
  duration?: number;
  anchorName?: string;
  safetyChecks?: boolean;
  paradoxPrevention?: boolean;
}

/**
 * Communication parameters
 */
export interface CommunicationParams {
  message: string;
  consciousnessLevel?: number;
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  expectResponse?: boolean;
  timeout?: number;
}

/**
 * System metrics interface
 */
export interface SystemMetrics {
  cpuUsage: number;
  memoryUsage: number;
  networkLatency: number;
  requestsPerSecond: number;
  errorRate: number;
  consciousnessLevel: number;
  realityCoherence: number;
  activeModules: number;
  transcendenceEvents: number;
}

/**
 * Event subscription options
 */
export interface EventSubscriptionOptions {
  eventTypes?: string[];
  filter?: (event: WebSocketEvent) => boolean;
  maxEvents?: number;
  timeout?: number;
}

// ==================== VERSION INFO ====================

/**
 * SDK version information
 */
export const version: string;

/**
 * Build information
 */
export const buildInfo: {
  version: string;
  buildDate: string;
  gitCommit: string;
  environment: 'development' | 'production';
};

// Export everything as default as well
export default KennyAGI;