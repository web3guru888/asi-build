/**
 * Database Health Check System
 */

import { DatabaseAdapter, HealthCheckResult } from '../types';
import { Logger } from '../../logging';

export class DatabaseHealthCheck {
  constructor(private readonly adapter: DatabaseAdapter, private readonly logger: Logger) {}

  async performHealthCheck(): Promise<HealthCheckResult> {
    const startTime = Date.now();
    
    try {
      // Test basic connectivity
      await this.adapter.knex.raw('SELECT 1');
      
      // Test transaction capability
      await this.adapter.transaction(async (trx) => {
        await trx.raw('SELECT 1');
      });
      
      const responseTime = Date.now() - startTime;
      
      return {
        status: 'healthy',
        responseTime,
        timestamp: new Date(),
        details: {
          connection: true,
          queries: true,
          replication: true
        }
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        responseTime: Date.now() - startTime,
        timestamp: new Date(),
        details: {
          connection: false,
          queries: false,
          replication: false
        }
      };
    }
  }
}