/**
 * Database Schema Versioning System
 *
 * Provides comprehensive schema version management with:
 * - Semantic versioning for database schemas
 * - Version compatibility checking
 * - Schema evolution tracking
 * - Breaking change detection
 * - Automatic version bumping
 */

import { DatabaseAdapter, MigrationInfo } from '../types';
import { Logger } from '../../logging';
import semver from 'semver';

export interface SchemaVersion {
  major: number;
  minor: number;
  patch: number;
  prerelease?: string;
  build?: string;
  full: string; // e.g., "1.2.3-beta.1+build.123"
}

export interface SchemaVersionInfo {
  version: SchemaVersion;
  timestamp: Date;
  description: string;
  migrations: string[];
  breaking: boolean;
  deprecated: string[];
  added: string[];
  changed: string[];
  removed: string[];
  metadata?: Record<string, any>;
}

export interface CompatibilityCheck {
  compatible: boolean;
  reason?: string;
  requiredVersion?: string;
  currentVersion: string;
  targetVersion: string;
  warnings: string[];
  errors: string[];
}

export class SchemaVersioning {
  private readonly adapter: DatabaseAdapter;
  private readonly logger: Logger;
  private readonly versionTable = 'schema_versions';
  private readonly compatibilityTable = 'schema_compatibility';

  constructor(adapter: DatabaseAdapter, logger: Logger) {
    this.adapter = adapter;
    this.logger = logger;
  }

  /**
   * Initialize schema versioning system
   */
  async initialize(): Promise<void> {
    try {
      this.logger.info('Initializing schema versioning system');

      await this.ensureVersioningTables();

      // Initialize with version 0.0.0 if no versions exist
      const currentVersion = await this.getCurrentVersion();
      if (!currentVersion) {
        await this.setVersion('0.0.0', 'Initial schema version', [], false);
      }

      this.logger.info('Schema versioning system initialized');
    } catch (error) {
      this.logger.error('Failed to initialize schema versioning', { error });
      throw error;
    }
  }

  /**
   * Ensure versioning tables exist
   */
  private async ensureVersioningTables(): Promise<void> {
    // Schema versions table
    const hasVersionTable = await this.adapter.hasTable(this.versionTable);
    if (!hasVersionTable) {
      await this.adapter.knex.schema.createTable(this.versionTable, table => {
        table.increments('id').primary();
        table.string('version', 50).notNullable().unique();
        table.integer('major').notNullable();
        table.integer('minor').notNullable();
        table.integer('patch').notNullable();
        table.string('prerelease', 50).nullable();
        table.string('build', 50).nullable();
        table.timestamp('created_at').defaultTo(this.adapter.knex.fn.now());
        table.string('description').notNullable();
        table.json('migrations').notNullable();
        table.boolean('breaking').defaultTo(false);
        table.json('deprecated').nullable();
        table.json('added').nullable();
        table.json('changed').nullable();
        table.json('removed').nullable();
        table.json('metadata').nullable();
        table.boolean('active').defaultTo(true);

        table.index(['version']);
        table.index(['major', 'minor', 'patch']);
        table.index(['created_at']);
        table.index(['breaking']);
        table.index(['active']);
      });
    }

    // Schema compatibility table
    const hasCompatibilityTable = await this.adapter.hasTable(
      this.compatibilityTable
    );
    if (!hasCompatibilityTable) {
      await this.adapter.knex.schema.createTable(
        this.compatibilityTable,
        table => {
          table.increments('id').primary();
          table.string('from_version', 50).notNullable();
          table.string('to_version', 50).notNullable();
          table.boolean('compatible').notNullable();
          table.string('reason').nullable();
          table.json('warnings').nullable();
          table.json('errors').nullable();
          table.timestamp('checked_at').defaultTo(this.adapter.knex.fn.now());
          table.json('metadata').nullable();

          table.unique(['from_version', 'to_version']);
          table.index(['compatible']);
          table.index(['checked_at']);
        }
      );
    }
  }

  /**
   * Parse version string into SchemaVersion object
   */
  private parseVersion(versionString: string): SchemaVersion {
    const parsed = semver.parse(versionString);
    if (!parsed) {
      throw new Error(`Invalid version format: ${versionString}`);
    }

    return {
      major: parsed.major,
      minor: parsed.minor,
      patch: parsed.patch,
      prerelease: parsed.prerelease.join('.') || undefined,
      build: parsed.build.join('.') || undefined,
      full: versionString,
    };
  }

  /**
   * Get current schema version
   */
  async getCurrentVersion(): Promise<SchemaVersionInfo | null> {
    try {
      const result = await this.adapter
        .knex(this.versionTable)
        .where({ active: true })
        .orderBy('created_at', 'desc')
        .first();

      if (!result) {
        return null;
      }

      return {
        version: {
          major: result.major,
          minor: result.minor,
          patch: result.patch,
          prerelease: result.prerelease,
          build: result.build,
          full: result.version,
        },
        timestamp: result.created_at,
        description: result.description,
        migrations: result.migrations,
        breaking: result.breaking,
        deprecated: result.deprecated || [],
        added: result.added || [],
        changed: result.changed || [],
        removed: result.removed || [],
        metadata: result.metadata,
      };
    } catch (error) {
      this.logger.error('Failed to get current version', { error });
      throw error;
    }
  }

  /**
   * Get all schema versions
   */
  async getAllVersions(): Promise<SchemaVersionInfo[]> {
    try {
      const results = await this.adapter
        .knex(this.versionTable)
        .orderBy('major', 'asc')
        .orderBy('minor', 'asc')
        .orderBy('patch', 'asc')
        .orderBy('created_at', 'asc');

      return results.map(result => ({
        version: {
          major: result.major,
          minor: result.minor,
          patch: result.patch,
          prerelease: result.prerelease,
          build: result.build,
          full: result.version,
        },
        timestamp: result.created_at,
        description: result.description,
        migrations: result.migrations,
        breaking: result.breaking,
        deprecated: result.deprecated || [],
        added: result.added || [],
        changed: result.changed || [],
        removed: result.removed || [],
        metadata: result.metadata,
      }));
    } catch (error) {
      this.logger.error('Failed to get all versions', { error });
      throw error;
    }
  }

  /**
   * Set new schema version
   */
  async setVersion(
    versionString: string,
    description: string,
    migrations: string[],
    breaking = false,
    changes?: {
      deprecated?: string[];
      added?: string[];
      changed?: string[];
      removed?: string[];
    },
    metadata?: Record<string, any>
  ): Promise<void> {
    try {
      const version = this.parseVersion(versionString);

      this.logger.info('Setting new schema version', {
        version: version.full,
        description,
        breaking,
        migrations: migrations.length,
      });

      // Deactivate current version
      await this.adapter
        .knex(this.versionTable)
        .where({ active: true })
        .update({ active: false });

      // Insert new version
      await this.adapter.knex(this.versionTable).insert({
        version: version.full,
        major: version.major,
        minor: version.minor,
        patch: version.patch,
        prerelease: version.prerelease,
        build: version.build,
        description,
        migrations: JSON.stringify(migrations),
        breaking,
        deprecated: JSON.stringify(changes?.deprecated || []),
        added: JSON.stringify(changes?.added || []),
        changed: JSON.stringify(changes?.changed || []),
        removed: JSON.stringify(changes?.removed || []),
        metadata: metadata ? JSON.stringify(metadata) : null,
        active: true,
      });

      this.logger.info('Schema version set successfully', {
        version: version.full,
      });
    } catch (error) {
      this.logger.error('Failed to set schema version', {
        error,
        version: versionString,
      });
      throw error;
    }
  }

  /**
   * Bump version automatically based on changes
   */
  async bumpVersion(
    bumpType: 'major' | 'minor' | 'patch',
    description: string,
    migrations: string[],
    changes?: {
      deprecated?: string[];
      added?: string[];
      changed?: string[];
      removed?: string[];
    },
    metadata?: Record<string, any>
  ): Promise<string> {
    try {
      const currentVersion = await this.getCurrentVersion();
      if (!currentVersion) {
        throw new Error('No current version found');
      }

      const currentVersionString = currentVersion.version.full;
      let newVersionString: string;

      switch (bumpType) {
        case 'major':
          newVersionString = semver.inc(currentVersionString, 'major')!;
          break;
        case 'minor':
          newVersionString = semver.inc(currentVersionString, 'minor')!;
          break;
        case 'patch':
          newVersionString = semver.inc(currentVersionString, 'patch')!;
          break;
        default:
          throw new Error(`Invalid bump type: ${bumpType}`);
      }

      const breaking =
        bumpType === 'major' ||
        (changes?.removed && changes.removed.length > 0) ||
        (changes?.changed && changes.changed.length > 0);

      await this.setVersion(
        newVersionString,
        description,
        migrations,
        breaking,
        changes,
        metadata
      );

      return newVersionString;
    } catch (error) {
      this.logger.error('Failed to bump version', { error, bumpType });
      throw error;
    }
  }

  /**
   * Check compatibility between versions
   */
  async checkCompatibility(
    fromVersion: string,
    toVersion: string
  ): Promise<CompatibilityCheck> {
    try {
      this.logger.debug('Checking version compatibility', {
        fromVersion,
        toVersion,
      });

      // Check cached compatibility result
      const cached = await this.adapter
        .knex(this.compatibilityTable)
        .where({ from_version: fromVersion, to_version: toVersion })
        .first();

      if (cached) {
        return {
          compatible: cached.compatible,
          reason: cached.reason,
          currentVersion: fromVersion,
          targetVersion: toVersion,
          warnings: cached.warnings || [],
          errors: cached.errors || [],
        };
      }

      // Perform compatibility check
      const result = await this.performCompatibilityCheck(
        fromVersion,
        toVersion
      );

      // Cache result
      await this.adapter.knex(this.compatibilityTable).insert({
        from_version: fromVersion,
        to_version: toVersion,
        compatible: result.compatible,
        reason: result.reason,
        warnings: JSON.stringify(result.warnings),
        errors: JSON.stringify(result.errors),
      });

      return result;
    } catch (error) {
      this.logger.error('Failed to check compatibility', {
        error,
        fromVersion,
        toVersion,
      });
      throw error;
    }
  }

  /**
   * Perform actual compatibility check
   */
  private async performCompatibilityCheck(
    fromVersion: string,
    toVersion: string
  ): Promise<CompatibilityCheck> {
    const warnings: string[] = [];
    const errors: string[] = [];
    let compatible = true;
    let reason: string | undefined;

    try {
      // Get version information
      const fromVersionInfo = await this.getVersionInfo(fromVersion);
      const toVersionInfo = await this.getVersionInfo(toVersion);

      if (!fromVersionInfo || !toVersionInfo) {
        return {
          compatible: false,
          reason: 'Version not found',
          currentVersion: fromVersion,
          targetVersion: toVersion,
          warnings,
          errors: ['One or both versions not found in database'],
        };
      }

      // Check semantic version compatibility
      const semverCompatible = semver.gte(toVersion, fromVersion);
      if (!semverCompatible) {
        compatible = false;
        reason = 'Target version is older than current version';
        errors.push('Cannot downgrade to an older version');
      }

      // Check for breaking changes
      const versionsInRange = await this.getVersionsInRange(
        fromVersion,
        toVersion
      );
      const hasBreakingChanges = versionsInRange.some(v => v.breaking);

      if (hasBreakingChanges) {
        const breakingVersions = versionsInRange.filter(v => v.breaking);
        warnings.push(
          `Breaking changes found in versions: ${breakingVersions.map(v => v.version.full).join(', ')}`
        );
      }

      // Check major version difference
      const majorDiff = semver.major(toVersion) - semver.major(fromVersion);
      if (majorDiff > 1) {
        warnings.push(
          'Skipping major versions may require manual intervention'
        );
      }

      // Check deprecated features
      const deprecatedFeatures = versionsInRange.flatMap(v => v.deprecated);
      if (deprecatedFeatures.length > 0) {
        warnings.push(`Deprecated features: ${deprecatedFeatures.join(', ')}`);
      }

      // Check removed features
      const removedFeatures = versionsInRange.flatMap(v => v.removed);
      if (removedFeatures.length > 0) {
        errors.push(`Removed features: ${removedFeatures.join(', ')}`);
        compatible = false;
        reason = 'Target version removes features that may be in use';
      }

      return {
        compatible,
        reason,
        currentVersion: fromVersion,
        targetVersion: toVersion,
        warnings,
        errors,
      };
    } catch (error) {
      return {
        compatible: false,
        reason: 'Compatibility check failed',
        currentVersion: fromVersion,
        targetVersion: toVersion,
        warnings,
        errors: [`Compatibility check error: ${error.message}`],
      };
    }
  }

  /**
   * Get version information by version string
   */
  private async getVersionInfo(
    versionString: string
  ): Promise<SchemaVersionInfo | null> {
    try {
      const result = await this.adapter
        .knex(this.versionTable)
        .where({ version: versionString })
        .first();

      if (!result) {
        return null;
      }

      return {
        version: {
          major: result.major,
          minor: result.minor,
          patch: result.patch,
          prerelease: result.prerelease,
          build: result.build,
          full: result.version,
        },
        timestamp: result.created_at,
        description: result.description,
        migrations: result.migrations,
        breaking: result.breaking,
        deprecated: result.deprecated || [],
        added: result.added || [],
        changed: result.changed || [],
        removed: result.removed || [],
        metadata: result.metadata,
      };
    } catch (error) {
      this.logger.error('Failed to get version info', {
        error,
        version: versionString,
      });
      throw error;
    }
  }

  /**
   * Get versions in range (exclusive of fromVersion, inclusive of toVersion)
   */
  private async getVersionsInRange(
    fromVersion: string,
    toVersion: string
  ): Promise<SchemaVersionInfo[]> {
    try {
      const allVersions = await this.getAllVersions();

      return allVersions.filter(version => {
        const versionString = version.version.full;
        return (
          semver.gt(versionString, fromVersion) &&
          semver.lte(versionString, toVersion)
        );
      });
    } catch (error) {
      this.logger.error('Failed to get versions in range', {
        error,
        fromVersion,
        toVersion,
      });
      throw error;
    }
  }

  /**
   * Get version history
   */
  async getVersionHistory(limit = 50): Promise<SchemaVersionInfo[]> {
    try {
      const results = await this.adapter
        .knex(this.versionTable)
        .orderBy('created_at', 'desc')
        .limit(limit);

      return results.map(result => ({
        version: {
          major: result.major,
          minor: result.minor,
          patch: result.patch,
          prerelease: result.prerelease,
          build: result.build,
          full: result.version,
        },
        timestamp: result.created_at,
        description: result.description,
        migrations: result.migrations,
        breaking: result.breaking,
        deprecated: result.deprecated || [],
        added: result.added || [],
        changed: result.changed || [],
        removed: result.removed || [],
        metadata: result.metadata,
      }));
    } catch (error) {
      this.logger.error('Failed to get version history', { error });
      throw error;
    }
  }

  /**
   * Clean up old compatibility records
   */
  async cleanupCompatibilityCache(olderThanDays = 30): Promise<number> {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - olderThanDays);

      const result = await this.adapter
        .knex(this.compatibilityTable)
        .where('checked_at', '<', cutoffDate)
        .del();

      this.logger.info('Cleaned up compatibility cache', {
        deletedRecords: result,
      });
      return result;
    } catch (error) {
      this.logger.error('Failed to cleanup compatibility cache', { error });
      throw error;
    }
  }
}
