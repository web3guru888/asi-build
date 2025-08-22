/**
 * Configuration System - Enhanced Centralized Configuration Management
 * 
 * Comprehensive configuration system with environment variable support,
 * validation, file watching, and Kenny Integration Pattern support.
 */

// Core configuration exports
export {
  ConfigManager,
  createConfigManager,
  createValidationSchema,
  DEFAULT_VALIDATION_SCHEMA
} from './config-manager.js';

// Configuration types
export type {
  ASICodeConfig,
  BaseConfig,
  EnvironmentConfig,
  LoggingConfig,
  LogOutput,
  AnthropicConfig,
  OpenAIConfig,
  ProvidersConfig,
  KennyConfig,
  ConsciousnessConfig,
  SessionConfig,
  ServerConfig,
  ToolsConfig,
  StorageConfig,
  PerformanceConfig,
  SecurityConfig,
  DevelopmentConfig,
  ConfigValidationRule,
  ConfigValidationSchema,
  ConfigLoadOptions,
  ConfigEvent,
  ConfigFactoryOptions,
  DeepPartial,
  ConfigPath,
  ConfigValue
} from './config-types.js';

// Default configurations
export {
  DEFAULT_ASI_CONFIG,
  PRODUCTION_CONFIG_OVERRIDES,
  TEST_CONFIG_OVERRIDES,
  getEnvironmentConfig,
  getDefaultConfig
} from './default-config.js';

import { ConfigManager, createConfigManager, DEFAULT_VALIDATION_SCHEMA } from './config-manager.js';
import { DEFAULT_ASI_CONFIG, getDefaultConfig } from './default-config.js';
import { ASICodeConfig, ConfigFactoryOptions, ConfigLoadOptions } from './config-types.js';
import { BaseSubsystem } from '../kenny/base-subsystem.js';
import { KennyIntegration } from '../kenny/integration.js';

/**
 * Global configuration instance
 */
let globalConfigManager: ConfigManager | null = null;

/**
 * Initialize global configuration system
 */
export function initializeConfig(options?: ConfigLoadOptions): Promise<ConfigManager> {
  if (globalConfigManager) {
    throw new Error('Configuration system is already initialized');
  }

  globalConfigManager = createConfigManager(DEFAULT_VALIDATION_SCHEMA);
  
  if (options) {
    return globalConfigManager.load(options).then(() => globalConfigManager!);
  }
  
  return Promise.resolve(globalConfigManager);
}

/**
 * Get global configuration manager
 */
export function getConfigManager(): ConfigManager {
  if (!globalConfigManager) {
    throw new Error('Configuration system not initialized. Call initializeConfig() first.');
  }
  return globalConfigManager;
}

/**
 * Get configuration value (convenience function)
 */
export function getConfig<T = any>(path: string): T | undefined {
  return getConfigManager().get<T>(path);
}

/**
 * Set configuration value (convenience function)
 */
export function setConfig(path: string, value: any): void {
  getConfigManager().set(path, value);
}

/**
 * Cleanup global configuration system
 */
export async function cleanupConfig(): Promise<void> {
  if (globalConfigManager) {
    await globalConfigManager.cleanup();
    globalConfigManager = null;
  }
}

/**
 * Configuration System Factory - Integrated with Kenny Pattern
 */
export class ConfigSystemFactory {
  /**
   * Create configuration manager with Kenny Integration
   */
  static async createAndRegister(
    kennyIntegration: KennyIntegration,
    options?: ConfigFactoryOptions
  ): Promise<ConfigManager> {
    const configSubsystem = new ConfigManagerSubsystem();
    
    // Register with Kenny Integration
    await kennyIntegration.registerSubsystem(configSubsystem);
    
    // Initialize the subsystem
    await configSubsystem.initialize(options || {});
    await configSubsystem.start();
    
    // Get the config manager instance
    const configManager = configSubsystem.getConfigManager();
    if (!configManager) {
      throw new Error('Failed to create config manager instance');
    }

    // Set as global instance if not already set
    if (!globalConfigManager) {
      globalConfigManager = configManager;
    }

    return configManager;
  }

  /**
   * Create standalone configuration manager
   */
  static createStandalone(options?: ConfigFactoryOptions): Promise<ConfigManager> {
    const configManager = createConfigManager(DEFAULT_VALIDATION_SCHEMA);
    
    if (options?.configPath) {
      const loadOptions: ConfigLoadOptions = {
        validateSchema: options.validateOnCreate !== false,
        mergeEnvironment: true,
        mergeFiles: true,
        configPaths: [options.configPath],
        environmentPrefix: 'ASI_CODE_',
        strict: false,
        watch: options.autoWatch || false
      };
      
      return configManager.load(loadOptions).then(() => configManager);
    }
    
    return Promise.resolve(configManager);
  }

  /**
   * Create development configuration manager
   */
  static createDevelopmentConfig(): ConfigManager {
    const configManager = createConfigManager();
    const devConfig = getDefaultConfig('development');
    configManager.merge(devConfig);
    return configManager;
  }

  /**
   * Create production configuration manager
   */
  static createProductionConfig(configPath: string): Promise<ConfigManager> {
    return this.createStandalone({
      environment: 'production',
      configPath,
      validateOnCreate: true,
      autoWatch: false
    });
  }

  /**
   * Create test configuration manager
   */
  static createTestConfig(): ConfigManager {
    const configManager = createConfigManager();
    const testConfig = getDefaultConfig('test');
    configManager.merge(testConfig);
    return configManager;
  }
}

/**
 * Configuration Manager Subsystem - Kenny Integration
 */
export class ConfigManagerSubsystem extends BaseSubsystem {
  private configManager?: ConfigManager;

  constructor() {
    super({
      id: 'config-manager',
      name: 'Configuration Manager',
      version: '1.0.0',
      description: 'Central configuration management system'
    });
  }

  protected async onInitialize(config: Record<string, any>): Promise<void> {
    try {
      this.configManager = await ConfigSystemFactory.createStandalone(config);
      
      // Forward events
      this.configManager.on('error', (error) => this.emit('error', error));
      this.configManager.on('loaded', (event) => this.emit('config.loaded', event));
      this.configManager.on('updated', (event) => this.emit('config.updated', event));
      this.configManager.on('validated', (event) => this.emit('config.validated', event));
      
      this.emit('initialized', { config });
    } catch (error) {
      this.emit('error', error);
      throw error;
    }
  }

  protected async onStart(): Promise<void> {
    this.emit('started');
  }

  protected async onStop(): Promise<void> {
    this.emit('stopped');
  }

  async initialize(options: ConfigFactoryOptions): Promise<void> {
    return super.initialize(options);
  }

  async start(): Promise<void> {
    if (this.status !== 'ready') {
      throw new Error('Config Manager subsystem must be initialized before starting');
    }

    this.status = 'running';
    this.emit('started');
  }

  async stop(): Promise<void> {
    if (this.status !== 'running') {
      return;
    }

    this.status = 'stopped';
    this.emit('stopped');
  }

  async shutdown(): Promise<void> {
    if (this.configManager) {
      await this.configManager.cleanup();
      this.configManager = undefined;
    }

    this.status = 'uninitialized';
    this.emit('shutdown');
  }

  async healthCheck() {
    if (!this.configManager) {
      return {
        status: 'unhealthy' as const,
        message: 'Config Manager not initialized',
        timestamp: new Date()
      };
    }

    try {
      const config = this.configManager.getAll();
      const isValid = this.configManager.validate();
      
      return {
        status: isValid ? 'healthy' as const : 'degraded' as const,
        message: `Config Manager running - ${Object.keys(config).length} config keys loaded`,
        timestamp: new Date(),
        details: {
          configKeys: Object.keys(config).length,
          isValid,
          environment: config.environment || 'unknown'
        }
      };
    } catch (error) {
      return {
        status: 'unhealthy' as const,
        message: `Config Manager error: ${error instanceof Error ? error.message : String(error)}`,
        timestamp: new Date()
      };
    }
  }

  getConfigManager(): ConfigManager | undefined {
    return this.configManager;
  }
}

/**
 * Configuration presets for different environments
 */
export const CONFIG_PRESETS = {
  development: () => ConfigSystemFactory.createDevelopmentConfig(),
  production: (configPath: string) => ConfigSystemFactory.createProductionConfig(configPath),
  test: () => ConfigSystemFactory.createTestConfig()
};

// Export factory as default
export default ConfigSystemFactory;

// Legacy exports for backward compatibility
export const defaultASIConfig = DEFAULT_ASI_CONFIG;