/**
 * Configuration Type Definitions
 * 
 * Comprehensive type definitions for all ASI-Code configuration options.
 * These types ensure type safety and provide IntelliSense support for configuration.
 */

// Base configuration interfaces
export interface BaseConfig {
  readonly id: string;
  readonly version: string;
  readonly environment: 'development' | 'staging' | 'production' | 'test';
  readonly description?: string;
}

// Environment variable configuration
export interface EnvironmentConfig {
  readonly NODE_ENV?: string;
  readonly ASI_CODE_ENV?: 'development' | 'staging' | 'production' | 'test';
  readonly ASI_CODE_PORT?: string;
  readonly ASI_CODE_HOST?: string;
  readonly ASI_CODE_LOG_LEVEL?: 'debug' | 'info' | 'warn' | 'error' | 'silent';
  readonly ASI_CODE_LOG_FORMAT?: 'json' | 'pretty' | 'simple';
  readonly ASI_CODE_CONFIG_PATH?: string;
  readonly ASI_CODE_DATA_DIR?: string;
  readonly ASI_CODE_CACHE_DIR?: string;
  readonly ANTHROPIC_API_KEY?: string;
  readonly OPENAI_API_KEY?: string;
}

// Logging configuration
export interface LoggingConfig {
  readonly level: 'debug' | 'info' | 'warn' | 'error' | 'silent';
  readonly format: 'json' | 'pretty' | 'simple';
  readonly enabled: boolean;
  readonly outputs: LogOutput[];
  readonly maxFileSize?: number; // in MB
  readonly maxFiles?: number;
  readonly dateFormat?: string;
  readonly includeStack?: boolean;
  readonly includeTimestamp?: boolean;
  readonly colorize?: boolean;
  readonly metadata?: Record<string, any>;
}

export interface LogOutput {
  readonly type: 'console' | 'file' | 'stream' | 'http';
  readonly enabled: boolean;
  readonly level?: 'debug' | 'info' | 'warn' | 'error';
  readonly format?: 'json' | 'pretty' | 'simple';
  readonly options?: {
    readonly filename?: string;
    readonly url?: string;
    readonly stream?: any;
    readonly [key: string]: any;
  };
}

// Provider configurations
export interface ProviderConfig {
  readonly enabled: boolean;
  readonly priority?: number;
  readonly timeout?: number;
  readonly retries?: number;
  readonly rateLimiting?: {
    readonly enabled: boolean;
    readonly requestsPerSecond?: number;
    readonly requestsPerMinute?: number;
    readonly requestsPerHour?: number;
  };
}

export interface AnthropicConfig extends ProviderConfig {
  readonly apiKey?: string;
  readonly baseUrl?: string;
  readonly model: string;
  readonly maxTokens: number;
  readonly temperature: number;
  readonly topP?: number;
  readonly topK?: number;
  readonly stopSequences?: string[];
  readonly systemPrompt?: string;
}

export interface OpenAIConfig extends ProviderConfig {
  readonly apiKey?: string;
  readonly baseUrl?: string;
  readonly model: string;
  readonly maxTokens: number;
  readonly temperature: number;
  readonly topP?: number;
  readonly frequencyPenalty?: number;
  readonly presencePenalty?: number;
  readonly stopSequences?: string[];
  readonly systemPrompt?: string;
}

export interface ProvidersConfig {
  readonly default: string;
  readonly anthropic: AnthropicConfig;
  readonly openai: OpenAIConfig;
  readonly [key: string]: any;
}

// Kenny Integration configuration
export interface KennyConfig {
  readonly enabled: boolean;
  readonly contextWindowSize: number;
  readonly adaptationRate: number;
  readonly memoryPersistence: boolean;
  readonly learningEnabled: boolean;
  readonly personalityTraits: {
    readonly curiosity: number;
    readonly helpfulness: number;
    readonly creativity: number;
    readonly analytical: number;
    readonly empathy: number;
    readonly [trait: string]: number;
  };
  readonly behaviorConfig: {
    readonly responseStyle: 'formal' | 'casual' | 'technical' | 'adaptive';
    readonly verbosity: 'minimal' | 'moderate' | 'detailed' | 'adaptive';
    readonly proactiveness: number; // 0-100
  };
}

// Consciousness configuration
export interface ConsciousnessConfig {
  readonly enabled: boolean;
  readonly awarenessThreshold: number;
  readonly memoryRetentionHours: number;
  readonly selfReflectionEnabled: boolean;
  readonly emotionalModelingEnabled: boolean;
  readonly metacognitionEnabled: boolean;
  readonly personalityTraits: KennyConfig['personalityTraits'];
  readonly learningConfig: {
    readonly enabled: boolean;
    readonly adaptationRate: number;
    readonly memoryConsolidationInterval: number; // minutes
    readonly experienceWeighting: number;
  };
}

// Session configuration
export interface SessionConfig {
  readonly maxMessages: number;
  readonly ttl: number; // Time to live in milliseconds
  readonly persistHistory: boolean;
  readonly storageProvider: 'memory' | 'file' | 'database' | 'redis';
  readonly storageConfig?: {
    readonly connectionString?: string;
    readonly database?: string;
    readonly collection?: string;
    readonly filePath?: string;
    readonly [key: string]: any;
  };
  readonly compression: {
    readonly enabled: boolean;
    readonly algorithm?: 'gzip' | 'brotli' | 'lz4';
    readonly level?: number;
  };
  readonly encryption: {
    readonly enabled: boolean;
    readonly algorithm?: 'aes-256-gcm' | 'chacha20-poly1305';
    readonly keyDerivation?: 'pbkdf2' | 'scrypt' | 'argon2';
  };
}

// Server configuration
export interface ServerConfig {
  readonly port: number;
  readonly host: string;
  readonly ssl: {
    readonly enabled: boolean;
    readonly certFile?: string;
    readonly keyFile?: string;
    readonly caFile?: string;
  };
  readonly cors: {
    readonly origin: string[] | string | boolean;
    readonly credentials: boolean;
    readonly methods?: string[];
    readonly allowedHeaders?: string[];
  };
  readonly auth: {
    readonly enabled: boolean;
    readonly type?: 'jwt' | 'oauth' | 'basic' | 'custom';
    readonly secretKey?: string;
    readonly expiresIn?: string;
    readonly issuer?: string;
    readonly audience?: string;
  };
  readonly middleware: {
    readonly compression: boolean;
    readonly helmet: boolean;
    readonly rateLimiting: {
      readonly enabled: boolean;
      readonly windowMs?: number;
      readonly max?: number;
      readonly message?: string;
    };
    readonly requestLogging: boolean;
  };
  readonly static: {
    readonly enabled: boolean;
    readonly path?: string;
    readonly maxAge?: number;
  };
}

// Tool system configuration
export interface ToolsConfig {
  readonly builtinEnabled: boolean;
  readonly allowCustom: boolean;
  readonly customToolsPath?: string;
  readonly permissions: {
    readonly fileAccess: boolean;
    readonly commandExecution: boolean;
    readonly networkAccess: boolean;
    readonly systemInfo: boolean;
    readonly processManagement: boolean;
    readonly databaseAccess: boolean;
  };
  readonly sandbox: {
    readonly enabled: boolean;
    readonly timeout?: number; // seconds
    readonly memoryLimit?: number; // MB
    readonly cpuLimit?: number; // percentage
    readonly networkIsolation?: boolean;
  };
  readonly registry: {
    readonly autoRegister: boolean;
    readonly loadPaths: string[];
    readonly enableVersioning: boolean;
  };
}

// Storage configuration
export interface StorageConfig {
  readonly provider: 'memory' | 'file' | 'sqlite' | 'postgres' | 'mongodb' | 'redis';
  readonly connectionString?: string;
  readonly options?: {
    readonly database?: string;
    readonly collection?: string;
    readonly tableName?: string;
    readonly filePath?: string;
    readonly maxConnections?: number;
    readonly connectionTimeout?: number;
    readonly [key: string]: any;
  };
  readonly encryption: {
    readonly enabled: boolean;
    readonly algorithm?: string;
    readonly keyFile?: string;
  };
  readonly backup: {
    readonly enabled: boolean;
    readonly interval?: number; // minutes
    readonly retention?: number; // days
    readonly location?: string;
  };
}

// Performance and monitoring configuration
export interface PerformanceConfig {
  readonly monitoring: {
    readonly enabled: boolean;
    readonly metricsInterval: number; // seconds
    readonly healthCheckInterval: number; // seconds
  };
  readonly caching: {
    readonly enabled: boolean;
    readonly provider: 'memory' | 'redis' | 'file';
    readonly ttl: number; // seconds
    readonly maxSize?: number; // MB
  };
  readonly optimization: {
    readonly lazyLoading: boolean;
    readonly preloadModules: string[];
    readonly memoryThreshold: number; // MB
    readonly gcStrategy: 'default' | 'aggressive' | 'conservative';
  };
}

// Security configuration
export interface SecurityConfig {
  readonly encryption: {
    readonly algorithm: string;
    readonly keySize: number;
    readonly keyRotationInterval?: number; // hours
  };
  readonly authentication: {
    readonly required: boolean;
    readonly methods: string[];
    readonly sessionTimeout: number; // minutes
  };
  readonly authorization: {
    readonly enabled: boolean;
    readonly defaultRole: string;
    readonly roleHierarchy: Record<string, string[]>;
  };
  readonly audit: {
    readonly enabled: boolean;
    readonly logLevel: 'minimal' | 'detailed' | 'comprehensive';
    readonly retention: number; // days
  };
}

// Development and debugging configuration
export interface DevelopmentConfig {
  readonly devMode: boolean;
  readonly debugging: {
    readonly enabled: boolean;
    readonly level: 'basic' | 'verbose' | 'trace';
    readonly breakpoints: boolean;
    readonly profiling: boolean;
  };
  readonly hotReload: {
    readonly enabled: boolean;
    readonly watchPaths: string[];
    readonly excludePaths: string[];
  };
  readonly testing: {
    readonly mockEnabled: boolean;
    readonly testDataPath?: string;
    readonly coverageEnabled: boolean;
  };
}

// Main ASI-Code configuration interface
export interface ASICodeConfig extends BaseConfig {
  readonly name: string;
  readonly dataDirectory: string;
  readonly cacheDirectory: string;
  readonly configPath?: string;
  
  // Core systems
  readonly logging: LoggingConfig;
  readonly providers: ProvidersConfig;
  readonly kenny: KennyConfig;
  readonly consciousness: ConsciousnessConfig;
  readonly session: SessionConfig;
  readonly server: ServerConfig;
  readonly tools: ToolsConfig;
  readonly storage: StorageConfig;
  
  // Additional systems
  readonly performance: PerformanceConfig;
  readonly security: SecurityConfig;
  readonly development: DevelopmentConfig;
  
  // Extension points
  readonly plugins?: {
    readonly enabled: boolean;
    readonly loadPaths: string[];
    readonly autoLoad: boolean;
    readonly [pluginName: string]: any;
  };
  
  readonly integrations?: {
    readonly [integrationName: string]: {
      readonly enabled: boolean;
      readonly config: Record<string, any>;
    };
  };
  
  // Custom configuration sections
  readonly [key: string]: any;
}

// Configuration validation schema types
export interface ConfigValidationRule {
  readonly path: string;
  readonly type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  readonly required: boolean;
  readonly default?: any;
  readonly validator?: (value: any) => boolean | string;
  readonly transform?: (value: any) => any;
}

export interface ConfigValidationSchema {
  readonly rules: ConfigValidationRule[];
  readonly strictMode: boolean;
  readonly allowUnknown: boolean;
}

// Configuration loading options
export interface ConfigLoadOptions {
  readonly validateSchema: boolean;
  readonly mergeEnvironment: boolean;
  readonly mergeFiles: boolean;
  readonly configPaths: string[];
  readonly environmentPrefix: string;
  readonly strict: boolean;
  readonly watch: boolean;
}

// Configuration events
export interface ConfigEvent {
  readonly type: 'loaded' | 'updated' | 'error' | 'validated' | 'changed';
  readonly path?: string;
  readonly data?: any;
  readonly error?: Error;
  readonly timestamp: Date;
}

// Factory configuration
export interface ConfigFactoryOptions {
  readonly environment?: string;
  readonly configPath?: string;
  readonly validateOnCreate?: boolean;
  readonly autoWatch?: boolean;
  readonly loadDefaults?: boolean;
}

// Export utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type ConfigPath<T, K extends keyof T = keyof T> = 
  K extends string 
    ? T[K] extends object 
      ? `${K}` | `${K}.${ConfigPath<T[K]>}`
      : `${K}`
    : never;

export type ConfigValue<T, P extends string> = 
  P extends `${infer K}.${infer Rest}`
    ? K extends keyof T
      ? ConfigValue<T[K], Rest>
      : never
    : P extends keyof T
      ? T[P]
      : never;