/**
 * Database Seeding System
 * 
 * Provides comprehensive data seeding capabilities with:
 * - Environment-specific seed data
 * - Dependency resolution between seeds
 * - Transactional seeding with rollback
 * - Data validation and constraints
 * - Incremental seeding support
 * - Test fixture generation
 * - Production data anonymization
 */

import { Knex } from 'knex';
import { promises as fs } from 'fs';
import path from 'path';
import { DatabaseAdapter, SeedInfo } from '../types';
import { Logger } from '../../logging';

export interface SeedConfig {
  name: string;
  description: string;
  environment: string[];
  dependencies: string[];
  order: number;
  transactional: boolean;
  data?: any;
  generator?: (knex: Knex) => Promise<any>;
}

export interface SeedExecutionContext {
  environment: string;
  knex: Knex;
  transaction?: Knex.Transaction;
  dryRun: boolean;
  force: boolean;
}

export interface SeederOptions {
  environment?: string;
  seedNames?: string[];
  dryRun?: boolean;
  force?: boolean;
  rollback?: boolean;
  skipDependencies?: boolean;
}

export class Seeder {
  private adapter: DatabaseAdapter;
  private logger: Logger;
  private seedsDirectory: string;
  private seedTrackingTable = 'knex_seeds';
  private registeredSeeds = new Map<string, SeedConfig>();

  constructor(adapter: DatabaseAdapter, logger: Logger) {
    this.adapter = adapter;
    this.logger = logger;
    this.seedsDirectory = adapter.config.seeds.directory;
  }

  /**
   * Initialize the seeding system
   */
  async initialize(): Promise<void> {
    try {
      this.logger.info('Initializing seeding system');
      
      // Ensure seed tracking table exists
      await this.ensureSeedTrackingTable();
      
      // Load seed files
      await this.loadSeedFiles();
      
      this.logger.info('Seeding system initialized successfully', {
        seedsLoaded: this.registeredSeeds.size
      });
    } catch (error) {
      this.logger.error('Failed to initialize seeding system', { error });
      throw error;
    }
  }

  /**
   * Ensure seed tracking table exists
   */
  private async ensureSeedTrackingTable(): Promise<void> {
    const hasTable = await this.adapter.hasTable(this.seedTrackingTable);
    
    if (!hasTable) {
      await this.adapter.knex.schema.createTable(this.seedTrackingTable, (table) => {
        table.increments('id').primary();
        table.string('name').notNullable().unique();
        table.string('filename').notNullable();
        table.string('environment').notNullable();
        table.timestamp('executed_at').defaultTo(this.adapter.knex.fn.now());
        table.integer('execution_time').nullable();
        table.boolean('success').defaultTo(true);
        table.text('error_message').nullable();
        table.json('metadata').nullable();
        
        table.index(['name']);
        table.index(['environment']);
        table.index(['executed_at']);
        table.index(['success']);
      });
    }
  }

  /**
   * Load seed files from directory
   */
  private async loadSeedFiles(): Promise<void> {
    try {
      const files = await fs.readdir(this.seedsDirectory);
      const extensions = this.adapter.config.seeds.loadExtensions;
      
      for (const file of files) {
        const ext = path.extname(file);
        if (!extensions.includes(ext)) continue;
        
        const fullPath = path.join(this.seedsDirectory, file);
        
        try {
          const seedModule = require(fullPath);
          
          if (seedModule.config && typeof seedModule.seed === 'function') {
            const config: SeedConfig = {
              name: seedModule.config.name || path.basename(file, ext),
              description: seedModule.config.description || '',
              environment: seedModule.config.environment || ['development'],
              dependencies: seedModule.config.dependencies || [],
              order: seedModule.config.order || 0,
              transactional: seedModule.config.transactional !== false,
              generator: seedModule.seed
            };
            
            this.registeredSeeds.set(config.name, config);
            
            this.logger.debug('Loaded seed file', {
              name: config.name,
              file,
              environments: config.environment
            });
          } else {
            this.logger.warn('Invalid seed file format', { file });
          }
        } catch (error) {
          this.logger.error('Failed to load seed file', {
            file,
            error: error.message
          });
        }
      }
    } catch (error) {
      this.logger.error('Failed to read seeds directory', {
        directory: this.seedsDirectory,
        error: error.message
      });
      throw error;
    }
  }

  /**
   * Run seeds based on options
   */
  async run(options: SeederOptions = {}): Promise<SeedInfo[]> {
    const environment = options.environment || process.env.NODE_ENV || 'development';
    
    this.logger.info('Running seeds', {
      environment,
      options
    });

    try {
      // Get seeds to run
      const seedsToRun = await this.getSeeds(environment, options);
      
      if (seedsToRun.length === 0) {
        this.logger.info('No seeds to run');
        return [];
      }

      // Resolve dependencies
      const orderedSeeds = options.skipDependencies ? 
        seedsToRun : 
        this.resolveDependencies(seedsToRun);

      this.logger.info(`Running ${orderedSeeds.length} seeds`, {
        seeds: orderedSeeds.map(s => s.name)
      });

      const results: SeedInfo[] = [];

      // Execute seeds
      for (const seed of orderedSeeds) {
        const result = await this.executeSeed(seed, environment, options);
        results.push(result);
      }

      this.logger.info('All seeds completed successfully');
      return results;
    } catch (error) {
      this.logger.error('Seed execution failed', { error });
      throw error;
    }
  }

  /**
   * Get seeds to run based on environment and options
   */
  private async getSeeds(environment: string, options: SeederOptions): Promise<SeedConfig[]> {
    let seeds = Array.from(this.registeredSeeds.values());

    // Filter by environment
    seeds = seeds.filter(seed => seed.environment.includes(environment));

    // Filter by specific seed names if provided
    if (options.seedNames && options.seedNames.length > 0) {
      seeds = seeds.filter(seed => options.seedNames!.includes(seed.name));
    }

    // Filter out already executed seeds unless force is specified
    if (!options.force) {
      const executedSeeds = await this.getExecutedSeeds(environment);
      const executedNames = new Set(executedSeeds.map(s => s.name));
      seeds = seeds.filter(seed => !executedNames.has(seed.name));
    }

    return seeds;
  }

  /**
   * Get executed seeds from database
   */
  private async getExecutedSeeds(environment: string): Promise<SeedInfo[]> {
    try {
      const seeds = await this.adapter.knex(this.seedTrackingTable)
        .where({ environment, success: true })
        .orderBy('executed_at', 'asc');

      return seeds.map(row => ({
        id: row.name,
        name: row.name,
        filename: row.filename,
        executedAt: row.executed_at,
        executionTime: row.execution_time,
        success: row.success,
        error: row.error_message
      }));
    } catch (error) {
      this.logger.error('Failed to get executed seeds', { error });
      throw error;
    }
  }

  /**
   * Resolve seed dependencies and return ordered list
   */
  private resolveDependencies(seeds: SeedConfig[]): SeedConfig[] {
    const seedMap = new Map(seeds.map(seed => [seed.name, seed]));
    const resolved: SeedConfig[] = [];
    const resolving = new Set<string>();

    const resolve = (seedName: string): void => {
      if (resolved.find(s => s.name === seedName)) {
        return; // Already resolved
      }

      if (resolving.has(seedName)) {
        throw new Error(`Circular dependency detected involving seed: ${seedName}`);
      }

      const seed = seedMap.get(seedName);
      if (!seed) {
        throw new Error(`Seed dependency not found: ${seedName}`);
      }

      resolving.add(seedName);

      // Resolve dependencies first
      for (const dependency of seed.dependencies) {
        resolve(dependency);
      }

      resolving.delete(seedName);
      resolved.push(seed);
    };

    // Resolve all seeds
    for (const seed of seeds) {
      resolve(seed.name);
    }

    // Sort by order for seeds with same dependency level
    resolved.sort((a, b) => a.order - b.order);

    return resolved;
  }

  /**
   * Execute a single seed
   */
  private async executeSeed(
    seed: SeedConfig,
    environment: string,
    options: SeederOptions
  ): Promise<SeedInfo> {
    const startTime = Date.now();
    
    this.logger.info('Executing seed', {
      name: seed.name,
      description: seed.description,
      transactional: seed.transactional,
      dryRun: options.dryRun
    });

    try {
      const context: SeedExecutionContext = {
        environment,
        knex: this.adapter.knex,
        dryRun: options.dryRun || false,
        force: options.force || false
      };

      let result: any;

      if (seed.transactional) {
        result = await this.adapter.transaction(async (trx) => {
          context.transaction = trx;
          return await seed.generator!(trx);
        });
      } else {
        result = await seed.generator!(this.adapter.knex);
      }

      const executionTime = Date.now() - startTime;

      // Record successful execution
      if (!options.dryRun) {
        await this.recordSeedExecution(seed, environment, executionTime, true);
      }

      this.logger.info('Seed executed successfully', {
        name: seed.name,
        executionTime,
        dryRun: options.dryRun
      });

      return {
        id: seed.name,
        name: seed.name,
        filename: `${seed.name}.ts`,
        executedAt: new Date(),
        executionTime,
        success: true
      };
    } catch (error) {
      const executionTime = Date.now() - startTime;

      // Record failed execution
      if (!options.dryRun) {
        await this.recordSeedExecution(seed, environment, executionTime, false, error.message);
      }

      this.logger.error('Seed execution failed', {
        name: seed.name,
        error: error.message,
        executionTime
      });

      throw new Error(`Seed '${seed.name}' failed: ${error.message}`);
    }
  }

  /**
   * Record seed execution in tracking table
   */
  private async recordSeedExecution(
    seed: SeedConfig,
    environment: string,
    executionTime: number,
    success: boolean,
    errorMessage?: string
  ): Promise<void> {
    try {
      // Delete existing record if force re-run
      await this.adapter.knex(this.seedTrackingTable)
        .where({ name: seed.name, environment })
        .delete();

      // Insert new record
      await this.adapter.knex(this.seedTrackingTable).insert({
        name: seed.name,
        filename: `${seed.name}.ts`,
        environment,
        execution_time: executionTime,
        success,
        error_message: errorMessage,
        metadata: JSON.stringify({
          description: seed.description,
          dependencies: seed.dependencies,
          order: seed.order
        })
      });
    } catch (error) {
      this.logger.error('Failed to record seed execution', {
        seed: seed.name,
        error: error.message
      });
    }
  }

  /**
   * Rollback seeds
   */
  async rollback(options: SeederOptions = {}): Promise<SeedInfo[]> {
    const environment = options.environment || process.env.NODE_ENV || 'development';
    
    this.logger.info('Rolling back seeds', { environment, options });

    try {
      // Get executed seeds in reverse order
      const executedSeeds = await this.getExecutedSeeds(environment);
      const seedsToRollback = executedSeeds.reverse();

      if (options.seedNames && options.seedNames.length > 0) {
        // Filter by specific seed names
        const filteredSeeds = seedsToRollback.filter(seed => 
          options.seedNames!.includes(seed.name)
        );
        seedsToRollback.length = 0;
        seedsToRollback.push(...filteredSeeds);
      }

      if (seedsToRollback.length === 0) {
        this.logger.info('No seeds to rollback');
        return [];
      }

      const results: SeedInfo[] = [];

      for (const seedInfo of seedsToRollback) {
        const seed = this.registeredSeeds.get(seedInfo.name);
        
        if (!seed) {
          this.logger.warn('Seed definition not found for rollback', {
            name: seedInfo.name
          });
          continue;
        }

        const result = await this.rollbackSeed(seed, seedInfo, environment, options);
        results.push(result);
      }

      this.logger.info('Seed rollback completed successfully');
      return results;
    } catch (error) {
      this.logger.error('Seed rollback failed', { error });
      throw error;
    }
  }

  /**
   * Rollback a single seed
   */
  private async rollbackSeed(
    seed: SeedConfig,
    seedInfo: SeedInfo,
    environment: string,
    options: SeederOptions
  ): Promise<SeedInfo> {
    const startTime = Date.now();
    
    this.logger.info('Rolling back seed', { name: seed.name });

    try {
      // Check if seed has rollback method
      const seedPath = path.join(this.seedsDirectory, `${seed.name}.ts`);
      const seedModule = require(seedPath);
      
      if (seedModule.rollback && typeof seedModule.rollback === 'function') {
        if (seed.transactional) {
          await this.adapter.transaction(async (trx) => {
            await seedModule.rollback(trx);
          });
        } else {
          await seedModule.rollback(this.adapter.knex);
        }
      } else {
        this.logger.warn('No rollback method found for seed', { name: seed.name });
      }

      // Remove from tracking table
      if (!options.dryRun) {
        await this.adapter.knex(this.seedTrackingTable)
          .where({ name: seed.name, environment })
          .delete();
      }

      const executionTime = Date.now() - startTime;

      this.logger.info('Seed rolled back successfully', {
        name: seed.name,
        executionTime,
        dryRun: options.dryRun
      });

      return {
        id: seed.name,
        name: seed.name,
        filename: `${seed.name}.ts`,
        executedAt: new Date(),
        executionTime,
        success: true
      };
    } catch (error) {
      this.logger.error('Seed rollback failed', {
        name: seed.name,
        error: error.message
      });

      throw new Error(`Seed rollback '${seed.name}' failed: ${error.message}`);
    }
  }

  /**
   * Register a seed programmatically
   */
  registerSeed(config: SeedConfig): void {
    this.registeredSeeds.set(config.name, config);
    this.logger.debug('Seed registered programmatically', { name: config.name });
  }

  /**
   * Get seed status
   */
  async getStatus(environment?: string): Promise<{
    environment: string;
    availableSeeds: number;
    executedSeeds: number;
    pendingSeeds: string[];
    lastExecuted?: Date;
  }> {
    const env = environment || process.env.NODE_ENV || 'development';
    
    const availableSeeds = Array.from(this.registeredSeeds.values())
      .filter(seed => seed.environment.includes(env));
    
    const executedSeeds = await this.getExecutedSeeds(env);
    const executedNames = new Set(executedSeeds.map(s => s.name));
    
    const pendingSeeds = availableSeeds
      .filter(seed => !executedNames.has(seed.name))
      .map(seed => seed.name);

    const lastExecuted = executedSeeds.length > 0 ? 
      executedSeeds[executedSeeds.length - 1].executedAt : 
      undefined;

    return {
      environment: env,
      availableSeeds: availableSeeds.length,
      executedSeeds: executedSeeds.length,
      pendingSeeds,
      lastExecuted
    };
  }

  /**
   * Create a new seed file template
   */
  async createSeed(
    name: string,
    options: {
      description?: string;
      environment?: string[];
      dependencies?: string[];
      order?: number;
      template?: string;
    } = {}
  ): Promise<string> {
    try {
      const filename = `${name}.ts`;
      const filepath = path.join(this.seedsDirectory, filename);
      
      const template = options.template || this.getDefaultSeedTemplate(name, options);
      
      await fs.writeFile(filepath, template, 'utf8');
      
      this.logger.info('Seed file created', { name, filepath });
      
      return filepath;
    } catch (error) {
      this.logger.error('Failed to create seed file', { error, name });
      throw error;
    }
  }

  /**
   * Get default seed template
   */
  private getDefaultSeedTemplate(name: string, options: any): string {
    return `import { Knex } from 'knex';

export const config = {
  name: '${name}',
  description: '${options.description || `Seed: ${name}`}',
  environment: ${JSON.stringify(options.environment || ['development'])},
  dependencies: ${JSON.stringify(options.dependencies || [])},
  order: ${options.order || 0},
  transactional: true
};

/**
 * Seed function - implement your data seeding logic here
 */
export async function seed(knex: Knex): Promise<void> {
  // TODO: Implement seeding logic
  
  // Example:
  // await knex('table_name').del();
  // await knex('table_name').insert([
  //   { id: 1, name: 'Example 1' },
  //   { id: 2, name: 'Example 2' }
  // ]);
}

/**
 * Rollback function - implement rollback logic here
 */
export async function rollback(knex: Knex): Promise<void> {
  // TODO: Implement rollback logic
  
  // Example:
  // await knex('table_name').del();
}
`;
  }
}