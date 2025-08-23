/**
 * Database Backup Manager
 */

import { BackupInfo, BackupOptions, DatabaseAdapter } from '../types';
import { Logger } from '../../logging';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export class BackupManager {
  constructor(
    private readonly adapter: DatabaseAdapter,
    private readonly logger: Logger
  ) {}

  async createBackup(
    options: BackupOptions = { type: 'full', compression: true }
  ): Promise<BackupInfo> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `backup_${timestamp}.sql${options.compression ? '.gz' : ''}`;

    this.logger.info('Creating database backup', { filename, options });

    try {
      const command = this.buildBackupCommand(filename, options);
      await execAsync(command);

      const backup: BackupInfo = {
        id: timestamp,
        filename,
        size: 0, // Would calculate actual size
        createdAt: new Date(),
        type: options.type || 'full',
        compressed: options.compression || false,
        checksum: 'sha256-placeholder',
      };

      this.logger.info('Database backup completed', backup);
      return backup;
    } catch (error) {
      this.logger.error('Database backup failed', { error });
      throw error;
    }
  }

  private buildBackupCommand(filename: string, options: BackupOptions): string {
    const config = this.adapter.config;
    let command = `pg_dump -h ${config.host} -p ${config.port} -U ${config.username} -d ${config.database}`;

    if (options.schemaOnly) command += ' --schema-only';
    if (options.dataOnly) command += ' --data-only';
    if (options.compression) command += ' | gzip';

    command += ` > ${filename}`;
    return command;
  }
}
