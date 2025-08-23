/**
 * Enhanced Configuration Manager
 *
 * Advanced configuration management with environment variable support,
 * file loading, validation, watching, and Kenny Integration Pattern integration.
 */

import { EventEmitter } from 'eventemitter3';
import {
  existsSync,
  readFileSync,
  unwatchFile,
  watchFile,
  writeFileSync,
} from 'fs';
import { dirname, extname, resolve } from 'path';
import { mkdirSync } from 'fs';
import { parse as parseYaml, stringify as stringifyYaml } from 'yaml';
import {
  ASICodeConfig,
  ConfigEvent,
  ConfigLoadOptions,
  ConfigValidationRule,
  ConfigValidationSchema,
  DeepPartial,
  EnvironmentConfig,
} from './config-types.js';
import { DEFAULT_ASI_CONFIG, getDefaultConfig } from './default-config.js';

/**
 * Enhanced Configuration Manager
 *
 * Provides comprehensive configuration management with features like:
 * - Environment variable integration
 * - Multiple file format support (JSON, YAML)
 * - Configuration validation
 * - File watching and hot reloading
 * - Deep merging and path-based access
 * - Type-safe configuration access
 */
export class ConfigManager extends EventEmitter {
  private config: ASICodeConfig;
  private readonly schema?: ConfigValidationSchema;
  private readonly watchedFiles = new Set<string>();
  private loadOptions: ConfigLoadOptions;

  constructor(schema?: ConfigValidationSchema) {
    super();
    this.config = { ...DEFAULT_ASI_CONFIG };
    this.schema = schema;
    this.loadOptions = {
      validateSchema: true,
      mergeEnvironment: true,
      mergeFiles: true,
      configPaths: [],
      environmentPrefix: 'ASI_CODE_',
      strict: false,
      watch: false,
    };
  }

  /**
   * Load configuration from various sources
   */
  async load(options: Partial<ConfigLoadOptions> = {}): Promise<void> {
    this.loadOptions = { ...this.loadOptions, ...options };

    try {
      // Start with default configuration
      let config = getDefaultConfig(process.env.NODE_ENV);

      // Merge environment variables if enabled
      if (this.loadOptions.mergeEnvironment) {
        const envConfig = this.loadEnvironmentVariables();
        config = this.deepMerge(config, envConfig);
      }

      // Load and merge configuration files if specified
      if (
        this.loadOptions.mergeFiles &&
        this.loadOptions.configPaths.length > 0
      ) {
        for (const configPath of this.loadOptions.configPaths) {
          if (existsSync(configPath)) {
            const fileConfig = await this.loadConfigurationFile(configPath);
            config = this.deepMerge(config, fileConfig);

            // Set up file watching if enabled
            if (this.loadOptions.watch) {
              this.watchConfigurationFile(configPath);
            }
          } else if (this.loadOptions.strict) {
            throw new Error(`Configuration file not found: ${configPath}`);
          }
        }
      }

      this.config = config;

      // Validate configuration if schema is provided
      if (this.loadOptions.validateSchema && this.schema) {
        this.validateConfiguration();
      }

      // Emit configuration loaded event
      this.emit('loaded', {
        type: 'loaded',
        data: this.config,
        timestamp: new Date(),
      } as ConfigEvent);
    } catch (error) {
      const configError = {
        type: 'error',
        error: error instanceof Error ? error : new Error(String(error)),
        timestamp: new Date(),
      } as ConfigEvent;

      this.emit('error', configError);
      throw error;
    }
  }

  /**
   * Save current configuration to file
   */
  async save(filePath: string): Promise<void> {
    try {
      // Ensure directory exists
      const dir = dirname(filePath);
      if (!existsSync(dir)) {
        mkdirSync(dir, { recursive: true });
      }

      const ext = extname(filePath).toLowerCase();
      let content: string;

      switch (ext) {
        case '.json':
          content = JSON.stringify(this.config, null, 2);
          break;
        case '.yml':
        case '.yaml':
          content = stringifyYaml(this.config);
          break;
        default:
          throw new Error(`Unsupported file format: ${ext}`);
      }

      writeFileSync(filePath, content, 'utf8');

      this.emit('saved', {
        type: 'updated',
        path: filePath,
        timestamp: new Date(),
      } as ConfigEvent);
    } catch (error) {
      this.emit('error', {
        type: 'error',
        path: filePath,
        error: error instanceof Error ? error : new Error(String(error)),
        timestamp: new Date(),
      } as ConfigEvent);
      throw error;
    }
  }

  /**
   * Get configuration value by path
   */
  get<T = any>(path: string): T | undefined {
    return this.getValueByPath(this.config, path) as T;
  }

  /**
   * Set configuration value by path
   */
  set(path: string, value: any): void {
    this.setValueByPath(this.config, path, value);

    this.emit('updated', {
      type: 'updated',
      path,
      data: { path, value },
      timestamp: new Date(),
    } as ConfigEvent);
  }

  /**
   * Check if configuration has a specific path
   */
  has(path: string): boolean {
    return this.getValueByPath(this.config, path) !== undefined;
  }

  /**
   * Delete configuration value by path
   */
  delete(path: string): void {
    this.deleteValueByPath(this.config, path);

    this.emit('updated', {
      type: 'updated',
      path,
      data: { path, deleted: true },
      timestamp: new Date(),
    } as ConfigEvent);
  }

  /**
   * Get entire configuration object
   */
  getAll(): ASICodeConfig {
    return JSON.parse(JSON.stringify(this.config));
  }

  /**
   * Merge configuration object
   */
  merge(config: DeepPartial<ASICodeConfig>): void {
    this.config = this.deepMerge(this.config, config);

    this.emit('updated', {
      type: 'updated',
      data: config,
      timestamp: new Date(),
    } as ConfigEvent);
  }

  /**
   * Reset configuration to defaults
   */
  reset(environment?: string): void {
    this.config = getDefaultConfig(environment);

    this.emit('updated', {
      type: 'updated',
      data: { reset: true },
      timestamp: new Date(),
    } as ConfigEvent);
  }

  /**
   * Validate current configuration against schema
   */
  validate(): boolean {
    if (!this.schema) {
      return true;
    }

    try {
      this.validateConfiguration();
      return true;
    } catch (error) {
      this.emit('error', {
        type: 'error',
        error: error instanceof Error ? error : new Error(String(error)),
        timestamp: new Date(),
      } as ConfigEvent);
      return false;
    }
  }

  /**
   * Cleanup resources and stop watching files
   */
  async cleanup(): Promise<void> {
    // Stop watching all files
    for (const filePath of this.watchedFiles) {
      unwatchFile(filePath);
    }
    this.watchedFiles.clear();

    // Clear configuration
    this.config = { ...DEFAULT_ASI_CONFIG };

    // Remove all event listeners
    this.removeAllListeners();

    this.emit('cleanup', {
      type: 'updated',
      data: { cleanup: true },
      timestamp: new Date(),
    } as ConfigEvent);
  }

  /**
   * Get configuration for specific subsystem
   */
  getSubsystemConfig<T = any>(subsystemName: string): T | undefined {
    return this.get(subsystemName) as T;
  }

  /**
   * Update configuration for specific subsystem
   */
  updateSubsystemConfig(subsystemName: string, config: any): void {
    this.set(subsystemName, config);
  }

  /**
   * Load environment variables into configuration
   */
  private loadEnvironmentVariables(): DeepPartial<ASICodeConfig> {
    const envConfig: any = {};
    const prefix = this.loadOptions.environmentPrefix;

    // Map environment variables to configuration paths
    const envMappings: Record<string, string> = {
      [`${prefix}PORT`]: 'server.port',
      [`${prefix}HOST`]: 'server.host',
      [`${prefix}LOG_LEVEL`]: 'logging.level',
      [`${prefix}LOG_FORMAT`]: 'logging.format',
      [`${prefix}ENV`]: 'environment',
      [`${prefix}DATA_DIR`]: 'dataDirectory',
      [`${prefix}CACHE_DIR`]: 'cacheDirectory',
      ANTHROPIC_API_KEY: 'providers.anthropic.apiKey',
      OPENAI_API_KEY: 'providers.openai.apiKey',
    };

    // Process environment variables
    for (const [envVar, configPath] of Object.entries(envMappings)) {
      const value = process.env[envVar];
      if (value !== undefined) {
        this.setValueByPath(
          envConfig,
          configPath,
          this.parseEnvironmentValue(value)
        );
      }
    }

    // Process boolean flags
    const booleanFlags = [
      [`${prefix}KENNY_ENABLED`, 'kenny.enabled'],
      [`${prefix}CONSCIOUSNESS_ENABLED`, 'consciousness.enabled'],
      [`${prefix}DEV_MODE`, 'development.devMode'],
      [`${prefix}SSL_ENABLED`, 'server.ssl.enabled'],
    ];

    for (const [envVar, configPath] of booleanFlags) {
      const value = process.env[envVar];
      if (value !== undefined) {
        this.setValueByPath(
          envConfig,
          configPath,
          value.toLowerCase() === 'true'
        );
      }
    }

    return envConfig;
  }

  /**
   * Load configuration from file
   */
  private async loadConfigurationFile(
    filePath: string
  ): Promise<DeepPartial<ASICodeConfig>> {
    const absolutePath = resolve(filePath);
    const content = readFileSync(absolutePath, 'utf8');
    const ext = extname(absolutePath).toLowerCase();

    let parsed: any;

    switch (ext) {
      case '.json':
        parsed = JSON.parse(content);
        break;
      case '.yml':
      case '.yaml':
        parsed = parseYaml(content);
        break;
      default:
        throw new Error(`Unsupported configuration file format: ${ext}`);
    }

    return parsed;
  }

  /**
   * Set up file watching for configuration hot reloading
   */
  private watchConfigurationFile(filePath: string): void {
    const absolutePath = resolve(filePath);

    if (this.watchedFiles.has(absolutePath)) {
      return; // Already watching
    }

    this.watchedFiles.add(absolutePath);

    watchFile(absolutePath, async (curr, prev) => {
      if (curr.mtime !== prev.mtime) {
        try {
          // Reload configuration
          await this.load(this.loadOptions);

          this.emit('changed', {
            type: 'changed',
            path: absolutePath,
            timestamp: new Date(),
          } as ConfigEvent);
        } catch (error) {
          this.emit('error', {
            type: 'error',
            path: absolutePath,
            error: error instanceof Error ? error : new Error(String(error)),
            timestamp: new Date(),
          } as ConfigEvent);
        }
      }
    });
  }

  /**
   * Validate configuration against schema
   */
  private validateConfiguration(): void {
    if (!this.schema) {
      return;
    }

    const errors: string[] = [];

    for (const rule of this.schema.rules) {
      const value = this.getValueByPath(this.config, rule.path);

      // Check if required field is missing
      if (rule.required && value === undefined) {
        errors.push(`Required configuration missing: ${rule.path}`);
        continue;
      }

      // Skip validation if value is undefined and not required
      if (value === undefined) {
        continue;
      }

      // Type validation
      if (!this.validateType(value, rule.type)) {
        errors.push(
          `Invalid type for ${rule.path}: expected ${rule.type}, got ${typeof value}`
        );
      }

      // Custom validation
      if (rule.validator && typeof rule.validator === 'function') {
        const validationResult = rule.validator(value);
        if (validationResult !== true) {
          errors.push(
            typeof validationResult === 'string'
              ? validationResult
              : `Validation failed for ${rule.path}`
          );
        }
      }
    }

    if (errors.length > 0) {
      throw new Error(`Configuration validation failed:\n${errors.join('\n')}`);
    }

    this.emit('validated', {
      type: 'validated',
      data: { valid: true },
      timestamp: new Date(),
    } as ConfigEvent);
  }

  /**
   * Validate value type
   */
  private validateType(value: any, expectedType: string): boolean {
    switch (expectedType) {
      case 'string':
        return typeof value === 'string';
      case 'number':
        return typeof value === 'number' && !isNaN(value);
      case 'boolean':
        return typeof value === 'boolean';
      case 'object':
        return (
          typeof value === 'object' && value !== null && !Array.isArray(value)
        );
      case 'array':
        return Array.isArray(value);
      default:
        return true;
    }
  }

  /**
   * Parse environment variable value to appropriate type
   */
  private parseEnvironmentValue(value: string): any {
    // Try to parse as number
    const numberValue = Number(value);
    if (!isNaN(numberValue)) {
      return numberValue;
    }

    // Try to parse as boolean
    if (value.toLowerCase() === 'true') return true;
    if (value.toLowerCase() === 'false') return false;

    // Try to parse as JSON
    try {
      return JSON.parse(value);
    } catch {
      // Return as string
      return value;
    }
  }

  /**
   * Get value by dot notation path
   */
  private getValueByPath(obj: any, path: string): any {
    const keys = path.split('.');
    let current = obj;

    for (const key of keys) {
      if (current && typeof current === 'object' && key in current) {
        current = current[key];
      } else {
        return undefined;
      }
    }

    return current;
  }

  /**
   * Set value by dot notation path
   */
  private setValueByPath(obj: any, path: string, value: any): void {
    const keys = path.split('.');
    let current = obj;

    for (let i = 0; i < keys.length - 1; i++) {
      const key = keys[i];
      if (
        !(key in current) ||
        typeof current[key] !== 'object' ||
        current[key] === null
      ) {
        current[key] = {};
      }
      current = current[key];
    }

    current[keys[keys.length - 1]] = value;
  }

  /**
   * Delete value by dot notation path
   */
  private deleteValueByPath(obj: any, path: string): void {
    const keys = path.split('.');
    let current = obj;

    for (let i = 0; i < keys.length - 1; i++) {
      const key = keys[i];
      if (!(key in current) || typeof current[key] !== 'object') {
        return; // Path doesn't exist
      }
      current = current[key];
    }

    delete current[keys[keys.length - 1]];
  }

  /**
   * Deep merge two objects
   */
  private deepMerge<T extends Record<string, any>>(target: T, source: any): T {
    const result = { ...target } as any;

    for (const key in source) {
      if (
        source[key] &&
        typeof source[key] === 'object' &&
        !Array.isArray(source[key])
      ) {
        result[key] = this.deepMerge(result[key] || {}, source[key]);
      } else {
        result[key] = source[key];
      }
    }

    return result;
  }
}

/**
 * Factory function to create a configured ConfigManager instance
 */
export function createConfigManager(
  schema?: ConfigValidationSchema,
  options?: Partial<ConfigLoadOptions>
): ConfigManager {
  const manager = new ConfigManager(schema);

  // Load configuration immediately if options are provided
  if (options) {
    manager.load(options).catch(error => {
      console.error('Failed to load initial configuration:', error);
    });
  }

  return manager;
}

/**
 * Create configuration validation schema
 */
export function createValidationSchema(
  rules: ConfigValidationRule[]
): ConfigValidationSchema {
  return {
    rules,
    strictMode: false,
    allowUnknown: true,
  };
}

/**
 * Default validation schema for ASI-Code configuration
 */
export const DEFAULT_VALIDATION_SCHEMA = createValidationSchema([
  {
    path: 'name',
    type: 'string',
    required: true,
  },
  {
    path: 'version',
    type: 'string',
    required: true,
  },
  {
    path: 'environment',
    type: 'string',
    required: true,
    validator: value =>
      ['development', 'staging', 'production', 'test'].includes(value),
  },
  {
    path: 'server.port',
    type: 'number',
    required: true,
    validator: value => value > 0 && value <= 65535,
  },
  {
    path: 'server.host',
    type: 'string',
    required: true,
  },
  {
    path: 'logging.level',
    type: 'string',
    required: true,
    validator: value =>
      ['debug', 'info', 'warn', 'error', 'silent'].includes(value),
  },
  {
    path: 'providers.default',
    type: 'string',
    required: true,
  },
]);
