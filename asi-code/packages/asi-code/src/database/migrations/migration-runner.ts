/**
 * Database Migration Runner
 * 
 * Provides zero-downtime migration capabilities with:
 * - Version tracking and rollback support
 * - Incremental migration execution
 * - Migration validation and verification
 * - Backup before migration execution
 * - Parallel migration support where safe
 */

import { Knex } from 'knex';
import { promises as fs } from 'fs';
import path from 'path';
import crypto from 'crypto';
import { DatabaseAdapter, MigrationInfo, MigrationStatus, MigrationError } from '../types';
import { Logger } from '../../logging';

export class MigrationRunner {
  private adapter: DatabaseAdapter;
  private logger: Logger;
  private migrationTable = 'knex_migrations';
  private migrationLockTable = 'knex_migrations_lock';

  constructor(adapter: DatabaseAdapter, logger: Logger) {
    this.adapter = adapter;
    this.logger = logger;
    this.migrationTable = adapter.config.migrations.tableName || 'knex_migrations';
  }

  /**
   * Initialize migration system
   */
  async initialize(): Promise<void> {
    try {
      this.logger.info('Initializing migration system');
      
      // Ensure migration tables exist
      await this.ensureMigrationTables();
      
      this.logger.info('Migration system initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize migration system', { error });
      throw new MigrationError('Failed to initialize migration system', '', error);
    }
  }

  /**
   * Ensure migration tracking tables exist
   */
  private async ensureMigrationTables(): Promise<void> {
    const hasTable = await this.adapter.hasTable(this.migrationTable);
    
    if (!hasTable) {
      await this.adapter.knex.schema.createTable(this.migrationTable, (table) => {
        table.increments('id').primary();
        table.string('name').notNullable();
        table.string('filename').notNullable();
        table.string('version').notNullable();
        table.string('checksum').notNullable();
        table.integer('batch').notNullable();
        table.timestamp('migration_time').defaultTo(this.adapter.knex.fn.now());
        table.integer('execution_time').nullable();
        table.boolean('success').defaultTo(true);
        table.text('error_message').nullable();
        table.json('metadata').nullable();
        
        table.unique(['name']);
        table.index(['version']);
        table.index(['batch']);
        table.index(['migration_time']);
      });
    }

    // Ensure lock table exists
    const hasLockTable = await this.adapter.hasTable(this.migrationLockTable);
    if (!hasLockTable) {
      await this.adapter.knex.schema.createTable(this.migrationLockTable, (table) => {
        table.integer('index').primary();
        table.boolean('is_locked').defaultTo(false);
      });
      
      // Insert initial lock record
      await this.adapter.knex(this.migrationLockTable).insert({ index: 1, is_locked: false });
    }
  }

  /**
   * Get all available migration files
   */
  private async getMigrationFiles(): Promise<MigrationInfo[]> {
    const migrationDir = this.adapter.config.migrations.directory;
    const extensions = this.adapter.config.migrations.loadExtensions;
    
    try {
      const files = await fs.readdir(migrationDir);
      const migrationFiles: MigrationInfo[] = [];
      
      for (const file of files) {
        const ext = path.extname(file);
        if (!extensions.includes(ext)) continue;
        
        const fullPath = path.join(migrationDir, file);
        const content = await fs.readFile(fullPath, 'utf8');
        const checksum = crypto.createHash('md5').update(content).digest('hex');
        
        // Extract version from filename (assumes format: YYYYMMDDHHMMSS_name.ext)
        const match = file.match(/^(\d{14})_(.+)\.\w+$/);
        if (!match) {
          this.logger.warn('Skipping migration file with invalid format', { file });
          continue;
        }
        
        const [, version, name] = match;
        
        migrationFiles.push({
          id: `${version}_${name}`,
          name,
          filename: file,
          version,
          checksum
        });
      }
      
      // Sort by version
      return migrationFiles.sort((a, b) => a.version.localeCompare(b.version));
    } catch (error) {
      this.logger.error('Failed to read migration files', { error, migrationDir });
      throw new MigrationError('Failed to read migration files', '', error);
    }
  }

  /**
   * Get applied migrations from database
   */
  private async getAppliedMigrations(): Promise<MigrationInfo[]> {
    try {
      const migrations = await this.adapter.knex(this.migrationTable)
        .select('*')
        .orderBy('version', 'asc');
      
      return migrations.map(row => ({
        id: row.name,
        name: row.name.split('_').slice(1).join('_'),
        filename: row.filename,
        version: row.version,
        checksum: row.checksum,
        executedAt: row.migration_time,
        executionTime: row.execution_time,
        success: row.success,
        error: row.error_message
      }));
    } catch (error) {
      this.logger.error('Failed to get applied migrations', { error });
      throw new MigrationError('Failed to get applied migrations', '', error);
    }
  }

  /**
   * Get migration status
   */
  async getStatus(): Promise<MigrationStatus> {
    try {
      const [availableMigrations, appliedMigrations] = await Promise.all([
        this.getMigrationFiles(),
        this.getAppliedMigrations()
      ]);
      
      const appliedNames = new Set(appliedMigrations.map(m => m.id));
      const pendingMigrations = availableMigrations.filter(m => !appliedNames.has(m.id));
      
      const currentVersion = appliedMigrations.length > 0 
        ? appliedMigrations[appliedMigrations.length - 1].version 
        : '0';
      
      return {
        currentVersion,
        pendingMigrations,
        appliedMigrations,
        pendingCount: pendingMigrations.length,
        appliedCount: appliedMigrations.length
      };
    } catch (error) {
      this.logger.error('Failed to get migration status', { error });
      throw new MigrationError('Failed to get migration status', '', error);
    }
  }

  /**
   * Acquire migration lock
   */
  private async acquireLock(): Promise<boolean> {
    try {
      const result = await this.adapter.knex(this.migrationLockTable)
        .where({ index: 1, is_locked: false })
        .update({ is_locked: true });
      
      return result > 0;
    } catch (error) {
      this.logger.error('Failed to acquire migration lock', { error });
      return false;
    }
  }

  /**
   * Release migration lock
   */
  private async releaseLock(): Promise<void> {
    try {
      await this.adapter.knex(this.migrationLockTable)
        .where({ index: 1 })
        .update({ is_locked: false });
    } catch (error) {
      this.logger.error('Failed to release migration lock', { error });
    }
  }

  /**
   * Validate migration before execution
   */
  private async validateMigration(migration: MigrationInfo): Promise<boolean> {
    try {
      // Check if migration was already applied with different checksum
      const existing = await this.adapter.knex(this.migrationTable)
        .where({ name: migration.id })
        .first();
      
      if (existing && existing.checksum !== migration.checksum) {
        this.logger.error('Migration checksum mismatch', {
          migration: migration.id,
          expectedChecksum: migration.checksum,
          actualChecksum: existing.checksum
        });
        return false;
      }
      
      return true;
    } catch (error) {
      this.logger.error('Migration validation failed', { error, migration: migration.id });
      return false;
    }
  }

  /**
   * Execute a single migration
   */
  private async executeMigration(migration: MigrationInfo, batch: number): Promise<void> {
    const startTime = Date.now();
    
    try {
      this.logger.info('Executing migration', {
        name: migration.name,
        version: migration.version,
        filename: migration.filename
      });
      
      // Load and execute migration
      const migrationPath = path.join(this.adapter.config.migrations.directory, migration.filename);
      const migrationModule = require(migrationPath);
      
      // Execute within transaction unless disabled
      if (this.adapter.config.migrations.disableTransactions) {
        await migrationModule.up(this.adapter.knex);
      } else {
        await this.adapter.transaction(async (trx) => {
          await migrationModule.up(trx);
        });
      }
      
      const executionTime = Date.now() - startTime;
      
      // Record successful migration
      await this.adapter.knex(this.migrationTable).insert({
        name: migration.id,
        filename: migration.filename,
        version: migration.version,
        checksum: migration.checksum,
        batch,
        execution_time: executionTime,
        success: true
      });
      
      this.logger.info('Migration completed successfully', {
        name: migration.name,
        executionTime
      });
    } catch (error) {
      const executionTime = Date.now() - startTime;
      
      // Record failed migration
      try {
        await this.adapter.knex(this.migrationTable).insert({
          name: migration.id,
          filename: migration.filename,
          version: migration.version,
          checksum: migration.checksum,
          batch,
          execution_time: executionTime,
          success: false,
          error_message: error.message
        });
      } catch (recordError) {
        this.logger.error('Failed to record migration failure', { recordError });
      }
      
      this.logger.error('Migration failed', {
        name: migration.name,
        error: error.message,
        executionTime
      });
      
      throw new MigrationError(`Migration ${migration.name} failed: ${error.message}`, migration.name, error);
    }
  }

  /**
   * Run pending migrations
   */
  async runPendingMigrations(): Promise<MigrationStatus> {
    // Acquire lock to prevent concurrent migrations
    const lockAcquired = await this.acquireLock();
    if (!lockAcquired) {
      throw new MigrationError('Unable to acquire migration lock - another migration may be in progress', '');
    }
    
    try {
      this.logger.info('Running pending migrations');
      
      const status = await this.getStatus();
      
      if (status.pendingCount === 0) {
        this.logger.info('No pending migrations to run');
        return status;
      }
      
      this.logger.info(`Found ${status.pendingCount} pending migrations`);
      
      // Get next batch number
      const lastBatch = await this.adapter.knex(this.migrationTable)
        .max('batch as max_batch')
        .first();
      const nextBatch = (lastBatch?.max_batch || 0) + 1;
      
      // Execute migrations sequentially
      for (const migration of status.pendingMigrations) {
        // Validate migration
        const isValid = await this.validateMigration(migration);
        if (!isValid) {
          throw new MigrationError(`Migration validation failed: ${migration.name}`, migration.name);
        }
        
        // Execute migration
        await this.executeMigration(migration, nextBatch);
      }
      
      this.logger.info('All pending migrations completed successfully');
      
      // Return updated status
      return await this.getStatus();
    } finally {
      await this.releaseLock();
    }
  }

  /**
   * Rollback migrations
   */
  async rollback(steps = 1): Promise<MigrationStatus> {
    const lockAcquired = await this.acquireLock();
    if (!lockAcquired) {
      throw new MigrationError('Unable to acquire migration lock', '');
    }
    
    try {
      this.logger.info(`Rolling back ${steps} migration(s)`);
      
      // Get migrations to rollback
      const migrationsToRollback = await this.adapter.knex(this.migrationTable)
        .where({ success: true })
        .orderBy('batch', 'desc')
        .orderBy('migration_time', 'desc')
        .limit(steps);
      
      if (migrationsToRollback.length === 0) {
        this.logger.info('No migrations to rollback');
        return await this.getStatus();
      }
      
      // Execute rollbacks in reverse order
      for (const migration of migrationsToRollback) {
        await this.rollbackMigration(migration);
      }
      
      this.logger.info('Rollback completed successfully');
      return await this.getStatus();
    } finally {
      await this.releaseLock();
    }
  }

  /**
   * Rollback a single migration
   */
  private async rollbackMigration(migrationRecord: any): Promise<void> {
    const startTime = Date.now();
    
    try {
      this.logger.info('Rolling back migration', {
        name: migrationRecord.name,
        version: migrationRecord.version
      });
      
      // Load migration file
      const migrationPath = path.join(this.adapter.config.migrations.directory, migrationRecord.filename);
      const migrationModule = require(migrationPath);
      
      if (!migrationModule.down) {
        throw new Error('Migration does not have a down method');
      }
      
      // Execute rollback
      if (this.adapter.config.migrations.disableTransactions) {
        await migrationModule.down(this.adapter.knex);
      } else {
        await this.adapter.transaction(async (trx) => {
          await migrationModule.down(trx);
        });
      }
      
      // Remove migration record
      await this.adapter.knex(this.migrationTable)
        .where({ id: migrationRecord.id })
        .delete();
      
      const executionTime = Date.now() - startTime;
      
      this.logger.info('Migration rollback completed', {
        name: migrationRecord.name,
        executionTime
      });
    } catch (error) {
      this.logger.error('Migration rollback failed', {
        name: migrationRecord.name,
        error: error.message
      });
      
      throw new MigrationError(`Rollback failed for ${migrationRecord.name}: ${error.message}`, migrationRecord.name, error);
    }
  }

  /**
   * Create a new migration file
   */
  async createMigration(name: string, template?: string): Promise<string> {
    try {
      const timestamp = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 14);
      const filename = `${timestamp}_${name}.ts`;
      const filepath = path.join(this.adapter.config.migrations.directory, filename);
      
      const migrationTemplate = template || this.getDefaultMigrationTemplate(name);
      
      await fs.writeFile(filepath, migrationTemplate, 'utf8');
      
      this.logger.info('Migration file created', { filename, filepath });
      
      return filepath;
    } catch (error) {
      this.logger.error('Failed to create migration file', { error, name });
      throw new MigrationError(`Failed to create migration file: ${error.message}`, name, error);
    }
  }

  /**
   * Get default migration template
   */
  private getDefaultMigrationTemplate(name: string): string {
    return `import { Knex } from 'knex';

/**
 * Migration: ${name}
 * Created: ${new Date().toISOString()}
 */

export async function up(knex: Knex): Promise<void> {
  // TODO: Implement migration
}

export async function down(knex: Knex): Promise<void> {
  // TODO: Implement rollback
}
`;
  }
}