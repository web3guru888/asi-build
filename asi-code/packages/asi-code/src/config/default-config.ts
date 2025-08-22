/**
 * Default ASI-Code Configuration
 * 
 * Comprehensive default configuration for the ASI-Code system.
 * This configuration provides sensible defaults for all system components.
 */

import { ASICodeConfig } from './config-types.js';

/**
 * Default ASI-Code configuration
 * 
 * This configuration is designed to work out-of-the-box for development
 * and can be overridden for production deployments.
 */
export const DEFAULT_ASI_CONFIG: ASICodeConfig = {
  // Base configuration
  id: 'asi-code-default',
  name: 'ASI-Code',
  version: '0.2.0',
  environment: 'development',
  description: 'Advanced System Intelligence Code Assistant',
  dataDirectory: './data',
  cacheDirectory: './cache',

  // Logging configuration
  logging: {
    level: 'info',
    format: 'pretty',
    enabled: true,
    outputs: [
      {
        type: 'console',
        enabled: true,
        level: 'info',
        format: 'pretty',
        options: {}
      },
      {
        type: 'file',
        enabled: true,
        level: 'debug',
        format: 'json',
        options: {
          filename: './logs/asi-code.log'
        }
      }
    ],
    maxFileSize: 100, // 100MB
    maxFiles: 5,
    dateFormat: 'YYYY-MM-DD HH:mm:ss.SSS',
    includeStack: true,
    includeTimestamp: true,
    colorize: true,
    metadata: {
      service: 'asi-code',
      version: '0.2.0'
    }
  },

  // Provider configurations
  providers: {
    default: 'anthropic',
    anthropic: {
      enabled: true,
      priority: 1,
      model: 'claude-3-sonnet-20240229',
      maxTokens: 4000,
      temperature: 0.7,
      topP: 0.9,
      timeout: 30000,
      retries: 3,
      rateLimiting: {
        enabled: true,
        requestsPerSecond: 2,
        requestsPerMinute: 100,
        requestsPerHour: 1000
      },
      systemPrompt: 'You are ASI-Code, an advanced AI assistant specialized in software development and system architecture.'
    },
    openai: {
      enabled: false,
      priority: 2,
      model: 'gpt-4',
      maxTokens: 4000,
      temperature: 0.7,
      topP: 0.9,
      timeout: 30000,
      retries: 3,
      rateLimiting: {
        enabled: true,
        requestsPerSecond: 1,
        requestsPerMinute: 50,
        requestsPerHour: 500
      }
    }
  },

  // Kenny Integration configuration
  kenny: {
    enabled: true,
    contextWindowSize: 20,
    adaptationRate: 0.1,
    memoryPersistence: true,
    learningEnabled: true,
    personalityTraits: {
      curiosity: 85,
      helpfulness: 90,
      creativity: 75,
      analytical: 88,
      empathy: 80,
      precision: 92,
      innovation: 78,
      patience: 85
    },
    behaviorConfig: {
      responseStyle: 'adaptive',
      verbosity: 'adaptive',
      proactiveness: 75
    }
  },

  // Consciousness configuration
  consciousness: {
    enabled: true,
    awarenessThreshold: 70,
    memoryRetentionHours: 24,
    selfReflectionEnabled: true,
    emotionalModelingEnabled: true,
    metacognitionEnabled: true,
    personalityTraits: {
      curiosity: 85,
      helpfulness: 90,
      creativity: 75,
      analytical: 88,
      empathy: 80,
      precision: 92,
      innovation: 78,
      patience: 85
    },
    learningConfig: {
      enabled: true,
      adaptationRate: 0.05,
      memoryConsolidationInterval: 30, // 30 minutes
      experienceWeighting: 0.8
    }
  },

  // Session configuration
  session: {
    maxMessages: 100,
    ttl: 86400000, // 24 hours
    persistHistory: true,
    storageProvider: 'file',
    storageConfig: {
      filePath: './data/sessions'
    },
    compression: {
      enabled: true,
      algorithm: 'gzip',
      level: 6
    },
    encryption: {
      enabled: false,
      algorithm: 'aes-256-gcm'
    }
  },

  // Server configuration
  server: {
    port: 3000,
    host: 'localhost',
    ssl: {
      enabled: false
    },
    cors: {
      origin: ['http://localhost:3000', 'http://localhost:3001'],
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
    },
    auth: {
      enabled: false,
      type: 'jwt',
      expiresIn: '24h'
    },
    middleware: {
      compression: true,
      helmet: true,
      rateLimiting: {
        enabled: true,
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 1000, // limit each IP to 1000 requests per windowMs
        message: 'Too many requests from this IP, please try again later.'
      },
      requestLogging: true
    },
    static: {
      enabled: true,
      path: './public',
      maxAge: 86400000 // 1 day
    },
    websocket: {
      enabled: true,
      path: '/ws',
      maxConnections: 1000,
      heartbeat: {
        enabled: true,
        interval: 30000, // 30 seconds
        timeout: 5000 // 5 seconds
      },
      compression: {
        enabled: true,
        threshold: 1024,
        level: 6
      },
      auth: {
        enabled: false,
        type: 'jwt',
        timeout: 300
      },
      rateLimiting: {
        enabled: true,
        messagesPerSecond: 10,
        messagesPerMinute: 100,
        bytesPerSecond: 1024
      },
      messageQueue: {
        enabled: true,
        maxSize: 1000,
        persistence: false,
        ttl: 300
      },
      channels: {
        enabled: true,
        maxChannelsPerConnection: 10,
        channelNamePattern: '^[a-zA-Z0-9_-]+$'
      },
      binary: {
        enabled: false,
        maxSize: 1048576, // 1MB
        allowedTypes: ['application/octet-stream']
      },
      reconnection: {
        enabled: true,
        maxRetries: 5,
        backoffMultiplier: 1.5,
        maxBackoffTime: 30000
      }
    }
  },

  // Tools configuration
  tools: {
    builtinEnabled: true,
    allowCustom: true,
    customToolsPath: './tools',
    permissions: {
      fileAccess: true,
      commandExecution: false,
      networkAccess: false,
      systemInfo: true,
      processManagement: false,
      databaseAccess: false
    },
    sandbox: {
      enabled: true,
      timeout: 30, // 30 seconds
      memoryLimit: 512, // 512MB
      cpuLimit: 80, // 80%
      networkIsolation: true
    },
    registry: {
      autoRegister: true,
      loadPaths: ['./tools', './plugins/tools'],
      enableVersioning: true
    }
  },

  // Storage configuration
  storage: {
    provider: 'file',
    options: {
      filePath: './data/storage'
    },
    encryption: {
      enabled: false
    },
    backup: {
      enabled: true,
      interval: 60, // 1 hour
      retention: 7, // 7 days
      location: './backups'
    }
  },

  // Database configuration  
  database: {
    host: process.env.DATABASE_HOST || 'localhost',
    port: parseInt(process.env.DATABASE_PORT || '5432'),
    database: process.env.DATABASE_NAME || 'asicode',
    username: process.env.DATABASE_USER || 'asicode',
    password: process.env.DATABASE_PASSWORD || 'password',
    pool: {
      min: 2,
      max: 20,
      acquireTimeoutMillis: 30000,
      createTimeoutMillis: 30000,
      destroyTimeoutMillis: 5000,
      idleTimeoutMillis: 30000,
      reapIntervalMillis: 1000,
      createRetryIntervalMillis: 100
    },
    retry: {
      maxAttempts: 3,
      initialDelayMs: 1000,
      maxDelayMs: 10000,
      exponentialBackoff: true
    },
    migrations: {
      directory: './src/database/migrations',
      tableName: 'knex_migrations',
      extension: '.ts',
      loadExtensions: ['.ts', '.js'],
      disableTransactions: false,
      sortDirsSeparately: false
    },
    seeds: {
      directory: './src/database/seeds',
      loadExtensions: ['.ts', '.js'],
      recursive: true
    },
    audit: {
      enabled: true,
      tableName: 'audit_log',
      trackChanges: true,
      trackDeletes: true,
      excludeTables: ['knex_migrations']
    },
    softDelete: {
      enabled: true,
      columnName: 'deleted_at',
      defaultValue: null,
      deletedValue: new Date()
    },
    monitoring: {
      enabled: true,
      slowQueryThreshold: 1000,
      logQueries: false,
      trackMetrics: true
    },
    backup: {
      enabled: true,
      schedule: '0 2 * * *',
      retention: 30,
      location: './backups/database',
      compression: true
    },
    cleanup: {
      enabled: true,
      schedule: '0 3 * * 0',
      retentionPeriods: {
        audit_log: 365,
        sessions: 30
      }
    }
  },

  // Performance configuration
  performance: {
    monitoring: {
      enabled: true,
      metricsInterval: 30, // 30 seconds
      healthCheckInterval: 60 // 60 seconds
    },
    caching: {
      enabled: true,
      provider: 'memory',
      ttl: 3600, // 1 hour
      maxSize: 100 // 100MB
    },
    optimization: {
      lazyLoading: true,
      preloadModules: ['kenny', 'consciousness', 'tools'],
      memoryThreshold: 1024, // 1GB
      gcStrategy: 'default'
    }
  },

  // Security configuration
  security: {
    encryption: {
      algorithm: 'aes-256-gcm',
      keySize: 256
    },
    authentication: {
      required: false,
      methods: ['jwt', 'basic'],
      sessionTimeout: 60 // 1 hour
    },
    authorization: {
      enabled: false,
      defaultRole: 'user',
      roleHierarchy: {
        admin: ['user', 'moderator'],
        moderator: ['user'],
        user: []
      }
    },
    audit: {
      enabled: true,
      logLevel: 'detailed',
      retention: 30 // 30 days
    }
  },

  // Development configuration
  development: {
    devMode: true,
    debugging: {
      enabled: true,
      level: 'verbose',
      breakpoints: false,
      profiling: false
    },
    hotReload: {
      enabled: true,
      watchPaths: ['./src'],
      excludePaths: ['./node_modules', './dist', './logs', './data']
    },
    testing: {
      mockEnabled: true,
      testDataPath: './test/data',
      coverageEnabled: false
    }
  },

  // Plugin system
  plugins: {
    enabled: true,
    loadPaths: ['./plugins', './node_modules/@asi-code/plugins'],
    autoLoad: true
  },

  // External integrations
  integrations: {
    github: {
      enabled: false,
      config: {
        webhooks: false,
        apiVersion: '2022-11-28'
      }
    },
    slack: {
      enabled: false,
      config: {
        botToken: '',
        signingSecret: ''
      }
    },
    discord: {
      enabled: false,
      config: {
        botToken: '',
        clientId: ''
      }
    }
  }
} as const;

/**
 * Production configuration overrides
 * 
 * These settings are recommended for production deployments.
 */
export const PRODUCTION_CONFIG_OVERRIDES: Partial<ASICodeConfig> = {
  environment: 'production',
  
  logging: {
    level: 'info',
    format: 'json',
    enabled: true,
    outputs: [
      {
        type: 'file',
        enabled: true,
        level: 'info',
        format: 'json',
        options: {
          filename: '/var/log/asi-code/asi-code.log'
        }
      }
    ],
    colorize: false
  },

  server: {
    port: 80,
    host: '0.0.0.0',
    ssl: {
      enabled: true,
      certFile: '/etc/ssl/certs/asi-code.crt',
      keyFile: '/etc/ssl/private/asi-code.key'
    },
    cors: {
      origin: ['*'],
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE'],
      allowedHeaders: ['Content-Type', 'Authorization']
    },
    auth: {
      enabled: true,
      type: 'jwt',
      secretKey: 'production-secret',
      expiresIn: '24h'
    },
    middleware: {
      compression: true,
      helmet: true,
      requestLogging: true,
      rateLimiting: {
        enabled: true,
        windowMs: 15 * 60 * 1000,
        max: 100 // More restrictive in production
      }
    },
    static: {
      enabled: false,
      path: './public'
    },
    websocket: {
      enabled: true,
      path: '/ws',
      maxConnections: 500, // More restrictive in production
      heartbeat: {
        enabled: true,
        interval: 30000,
        timeout: 10000
      },
      compression: {
        enabled: true,
        threshold: 512,
        level: 9
      },
      auth: {
        enabled: true,
        type: 'jwt',
        timeout: 300
      },
      rateLimiting: {
        enabled: true,
        messagesPerSecond: 5,
        messagesPerMinute: 50,
        bytesPerSecond: 512
      },
      messageQueue: {
        enabled: true,
        maxSize: 500,
        persistence: true,
        ttl: 600
      },
      channels: {
        enabled: false,
        maxChannelsPerConnection: 5,
        channelNamePattern: '^[a-zA-Z0-9_-]+$'
      },
      binary: {
        enabled: false,
        maxSize: 1048576, // 1MB
        allowedTypes: ['application/octet-stream']
      },
      reconnection: {
        enabled: true,
        maxRetries: 3,
        backoffMultiplier: 2.0,
        maxBackoffTime: 60000
      }
    }
  },

  tools: {
    builtinEnabled: true,
    allowCustom: false,
    sandbox: {
      enabled: true,
      timeout: 30000,
      memoryLimit: 256
    },
    registry: {
      autoRegister: true,
      loadPaths: ['./tools'],
      enableVersioning: true
    },
    permissions: {
      fileAccess: true,
      commandExecution: false,
      networkAccess: false,
      systemInfo: false,
      processManagement: false,
      databaseAccess: false
    }
  },

  storage: {
    provider: 'postgres',
    connectionString: 'postgresql://user:password@localhost:5432/asi_code_prod',
    options: {
      database: 'asi_code_prod',
      maxConnections: 50,
      connectionTimeout: 30000
    },
    encryption: {
      enabled: true,
      algorithm: 'aes-256-gcm',
      keyFile: '/etc/asi-code/encryption.key'
    },
    backup: {
      enabled: true,
      interval: 60, // minutes
      retention: 30, // days
      location: '/backup/asi-code'
    }
  },

  security: {
    authentication: {
      required: true,
      methods: ['api-key', 'oauth2'],
      sessionTimeout: 3600
    },
    authorization: {
      enabled: true,
      defaultRole: 'user',
      roleHierarchy: {
        admin: ['user'],
        user: []
      }
    },
    encryption: {
      algorithm: 'aes-256-gcm',
      keySize: 256,
      keyRotationInterval: 168 // weekly
    },
    audit: {
      enabled: true,
      logLevel: 'detailed',
      retention: 90
    }
  },

  development: {
    devMode: false,
    debugging: {
      enabled: false,
      level: 'basic',
      breakpoints: false,
      profiling: false
    },
    hotReload: {
      enabled: false,
      watchPaths: ['src/**'],
      excludePaths: ['node_modules/**']
    },
    testing: {
      mockEnabled: false,
      coverageEnabled: false
    }
  }
} as const;

/**
 * Test configuration overrides
 * 
 * These settings are optimized for testing environments.
 */
export const TEST_CONFIG_OVERRIDES: Partial<ASICodeConfig> = {
  environment: 'test',
  
  logging: {
    level: 'silent',
    format: 'simple',
    enabled: false,
    outputs: [],
    includeTimestamp: false,
    colorize: false
  },

  session: {
    ttl: 60000, // 1 minute for faster test cleanup
    maxMessages: 100,
    persistHistory: false,
    storageProvider: 'memory',
    compression: {
      enabled: false,
      algorithm: 'gzip',
      level: 6
    },
    encryption: {
      enabled: false,
      algorithm: 'aes-256-gcm',
      keyDerivation: 'pbkdf2'
    }
  },

  server: {
    port: 0, // Random available port
    host: 'localhost',
    ssl: {
      enabled: false,
      certFile: '',
      keyFile: '',
      caFile: ''
    },
    cors: {
      origin: ['*'],
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE'],
      allowedHeaders: ['Content-Type', 'Authorization']
    },
    middleware: {
      compression: false,
      helmet: false,
      requestLogging: false,
      rateLimiting: { enabled: false }
    },
    static: {
      enabled: false,
      path: '/static'
    },
    auth: {
      enabled: false
    },
    websocket: {
      enabled: false,
      path: '/ws',
      maxConnections: 100,
      heartbeat: {
        enabled: false,
        interval: 30000,
        timeout: 5000
      },
      compression: {
        enabled: false,
        threshold: 1024,
        level: 1
      },
      auth: {
        enabled: false,
        type: 'jwt',
        timeout: 60
      },
      rateLimiting: {
        enabled: false,
        messagesPerSecond: 100,
        messagesPerMinute: 1000,
        bytesPerSecond: 10240
      },
      messageQueue: {
        enabled: false,
        maxSize: 100,
        persistence: false,
        ttl: 60
      },
      channels: {
        enabled: false,
        maxChannelsPerConnection: 1,
        channelNamePattern: '^test.*'
      },
      binary: {
        enabled: false,
        maxSize: 1048576, // 1MB
        allowedTypes: ['application/octet-stream']
      },
      reconnection: {
        enabled: false,
        maxRetries: 1,
        backoffMultiplier: 1.0,
        maxBackoffTime: 1000
      }
    }
  },

  storage: {
    provider: 'memory',
    encryption: {
      enabled: false,
      algorithm: 'aes-256-gcm',
      keyFile: ''
    },
    backup: {
      enabled: false,
      interval: 1440, // minutes (24h)
      retention: 7 // days
    }
  },

  performance: {
    monitoring: {
      enabled: false,
      metricsInterval: 30000,
      healthCheckInterval: 60000
    },
    caching: {
      enabled: false,
      provider: 'memory',
      ttl: 300000
    },
    optimization: {
      lazyLoading: false,
      preloadModules: [],
      memoryThreshold: 512,
      gcStrategy: 'default'
    }
  },

  development: {
    devMode: true,
    debugging: {
      enabled: true,
      level: 'basic',
      breakpoints: false,
      profiling: false
    },
    hotReload: {
      enabled: false,
      watchPaths: ['src/**'],
      excludePaths: ['node_modules/**']
    },
    testing: {
      mockEnabled: true,
      coverageEnabled: true
    }
  }
} as const;

/**
 * Environment-specific configuration getter
 */
export function getEnvironmentConfig(environment?: string): Partial<ASICodeConfig> {
  const env = environment || process.env.NODE_ENV || 'development';
  
  switch (env) {
    case 'production':
      return PRODUCTION_CONFIG_OVERRIDES;
    case 'test':
      return TEST_CONFIG_OVERRIDES;
    case 'development':
    case 'staging':
    default:
      return {};
  }
}

/**
 * Get default configuration with environment overrides
 */
export function getDefaultConfig(environment?: string): ASICodeConfig {
  const envConfig = getEnvironmentConfig(environment);
  return {
    ...DEFAULT_ASI_CONFIG,
    ...envConfig,
    // Deep merge for nested objects
    logging: {
      ...DEFAULT_ASI_CONFIG.logging,
      ...(envConfig.logging || {})
    },
    server: {
      ...DEFAULT_ASI_CONFIG.server,
      ...(envConfig.server || {})
    },
    tools: {
      ...DEFAULT_ASI_CONFIG.tools,
      ...(envConfig.tools || {})
    },
    storage: {
      ...DEFAULT_ASI_CONFIG.storage,
      ...(envConfig.storage || {})
    },
    security: {
      ...DEFAULT_ASI_CONFIG.security,
      ...(envConfig.security || {})
    },
    development: {
      ...DEFAULT_ASI_CONFIG.development,
      ...(envConfig.development || {})
    }
  } as ASICodeConfig;
}