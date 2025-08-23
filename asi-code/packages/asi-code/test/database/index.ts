/**
 * Database Testing Utilities
 * Provides comprehensive database testing infrastructure including seeding, cleanup, and migrations
 */

import { DatabaseFixtures } from '../fixtures/index.js';

// =============================================================================
// DATABASE TEST MANAGER
// =============================================================================

export class DatabaseTestManager {
  private db: any;
  private isSetup = false;
  private migrationCompleted = false;

  constructor(database: any) {
    this.db = database;
  }

  /**
   * Initialize database for testing
   */
  async setup() {
    if (this.isSetup) return;

    try {
      // Check if tables exist, create if not
      await this.ensureTables();
      
      // Run test-specific migrations
      await this.runTestMigrations();
      
      this.isSetup = true;
    } catch (error) {
      console.error('Database setup failed:', error);
      throw error;
    }
  }

  /**
   * Clean up database after tests
   */
  async cleanup() {
    if (!this.isSetup) return;

    try {
      // Clear all tables
      await this.clearAllTables();
      
      // Reset sequences if using PostgreSQL
      await this.resetSequences();
      
    } catch (error) {
      console.error('Database cleanup failed:', error);
      throw error;
    }
  }

  /**
   * Seed database with test data
   */
  async seed(fixtures?: any) {
    const data = fixtures || DatabaseFixtures;
    
    try {
      // Seed in correct order to maintain referential integrity
      await this.seedUsers(data.users());
      await this.seedSessions(data.sessions());
      await this.seedMessages(data.messages());
      
    } catch (error) {
      console.error('Database seeding failed:', error);
      throw error;
    }
  }

  /**
   * Create a transaction for isolated testing
   */
  async createTransaction() {
    return await this.db.transaction();
  }

  /**
   * Rollback transaction to restore state
   */
  async rollbackTransaction(trx: any) {
    if (trx && trx.rollback) {
      await trx.rollback();
    }
  }

  // Private methods

  private async ensureTables() {
    const tables = ['users', 'sessions', 'messages', 'permissions', 'audit_logs'];
    
    for (const table of tables) {
      const exists = await this.db.schema.hasTable(table);
      if (!exists) {
        await this.createTable(table);
      }
    }
  }

  private async createTable(tableName: string) {
    switch (tableName) {
      case 'users':
        await this.db.schema.createTable('users', (table: any) => {
          table.string('id').primary();
          table.string('username').unique().notNullable();
          table.string('email').unique().notNullable();
          table.string('firstName');
          table.string('lastName');
          table.boolean('isActive').defaultTo(true);
          table.timestamps(true, true);
        });
        break;

      case 'sessions':
        await this.db.schema.createTable('sessions', (table: any) => {
          table.string('id').primary();
          table.string('userId').references('id').inTable('users').onDelete('CASCADE');
          table.text('data');
          table.timestamp('createdAt').defaultTo(this.db.fn.now());
          table.timestamp('lastActiveAt').defaultTo(this.db.fn.now());
          table.timestamp('expiresAt');
        });
        break;

      case 'messages':
        await this.db.schema.createTable('messages', (table: any) => {
          table.string('id').primary();
          table.string('sessionId').references('id').inTable('sessions').onDelete('CASCADE');
          table.string('type').notNullable();
          table.text('content').notNullable();
          table.timestamp('timestamp').defaultTo(this.db.fn.now());
          table.json('metadata');
        });
        break;

      case 'permissions':
        await this.db.schema.createTable('permissions', (table: any) => {
          table.string('id').primary();
          table.string('userId').references('id').inTable('users').onDelete('CASCADE');
          table.json('tools');
          table.json('resources');
          table.json('restrictions');
          table.timestamps(true, true);
        });
        break;

      case 'audit_logs':
        await this.db.schema.createTable('audit_logs', (table: any) => {
          table.increments('id').primary();
          table.string('userId');
          table.string('action').notNullable();
          table.string('resource');
          table.json('details');
          table.timestamp('timestamp').defaultTo(this.db.fn.now());
          table.string('ipAddress');
          table.string('userAgent');
        });
        break;
    }
  }

  private async runTestMigrations() {
    if (this.migrationCompleted) return;

    // Add any test-specific schema modifications here
    // For example, add test-specific columns or indexes
    
    try {
      // Add test metadata column to users if it doesn't exist
      const hasTestColumn = await this.db.schema.hasColumn('users', 'testMetadata');
      if (!hasTestColumn) {
        await this.db.schema.alterTable('users', (table: any) => {
          table.json('testMetadata');
        });
      }

      // Add performance test indexes
      await this.db.raw(`
        CREATE INDEX IF NOT EXISTS idx_messages_session_timestamp 
        ON messages(sessionId, timestamp)
      `);
      
      await this.db.raw(`
        CREATE INDEX IF NOT EXISTS idx_sessions_user_active 
        ON sessions(userId, lastActiveAt)
      `);

      this.migrationCompleted = true;
    } catch (error) {
      console.warn('Test migrations failed (may be expected in some environments):', error.message);
    }
  }

  private async clearAllTables() {
    const tables = ['audit_logs', 'messages', 'sessions', 'permissions', 'users'];
    
    // Disable foreign key checks temporarily
    await this.db.raw('SET FOREIGN_KEY_CHECKS = 0').catch(() => {
      // PostgreSQL equivalent
      return this.db.raw('SET session_replication_role = replica');
    });

    for (const table of tables) {
      try {
        await this.db(table).del();
      } catch (error) {
        console.warn(`Failed to clear table ${table}:`, error.message);
      }
    }

    // Re-enable foreign key checks
    await this.db.raw('SET FOREIGN_KEY_CHECKS = 1').catch(() => {
      return this.db.raw('SET session_replication_role = DEFAULT');
    });
  }

  private async resetSequences() {
    // This is database-specific. Example for PostgreSQL:
    try {
      await this.db.raw(`
        SELECT setval(pg_get_serial_sequence('audit_logs', 'id'), 1, false)
      `);
    } catch (error) {
      // Ignore if not PostgreSQL or sequence doesn't exist
    }
  }

  private async seedUsers(users: any[]) {
    if (users.length === 0) return;
    
    await this.db('users').insert(users);
  }

  private async seedSessions(sessions: any[]) {
    if (sessions.length === 0) return;
    
    await this.db('sessions').insert(sessions);
  }

  private async seedMessages(messages: any[]) {
    if (messages.length === 0) return;
    
    await this.db('messages').insert(messages);
  }
}

// =============================================================================
// DATABASE FACTORIES
// =============================================================================

export class DatabaseFactory {
  private db: any;

  constructor(database: any) {
    this.db = database;
  }

  /**
   * Create a user with optional overrides
   */
  async createUser(overrides: any = {}) {
    const userData = {
      id: `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      username: `testuser_${Date.now()}`,
      email: `test_${Date.now()}@example.com`,
      firstName: 'Test',
      lastName: 'User',
      isActive: true,
      testMetadata: { createdBy: 'factory' },
      ...overrides
    };

    const [user] = await this.db('users').insert(userData).returning('*');
    return user;
  }

  /**
   * Create a session for a user
   */
  async createSession(userId: string, overrides: any = {}) {
    const sessionData = {
      id: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      userId,
      data: JSON.stringify({
        preferences: { theme: 'dark' },
        activeTools: ['read', 'write']
      }),
      createdAt: new Date(),
      lastActiveAt: new Date(),
      expiresAt: new Date(Date.now() + 3600000), // 1 hour
      ...overrides
    };

    const [session] = await this.db('sessions').insert(sessionData).returning('*');
    return session;
  }

  /**
   * Create a message in a session
   */
  async createMessage(sessionId: string, overrides: any = {}) {
    const messageData = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      sessionId,
      type: 'user',
      content: 'Test message content',
      timestamp: new Date(),
      metadata: JSON.stringify({ test: true }),
      ...overrides
    };

    const [message] = await this.db('messages').insert(messageData).returning('*');
    return message;
  }

  /**
   * Create a complete user with session and messages
   */
  async createUserWithSession(userOverrides: any = {}, sessionOverrides: any = {}) {
    const user = await this.createUser(userOverrides);
    const session = await this.createSession(user.id, sessionOverrides);
    
    // Create a few messages
    const messages = await Promise.all([
      this.createMessage(session.id, { type: 'user', content: 'Hello' }),
      this.createMessage(session.id, { type: 'assistant', content: 'Hi there!' })
    ]);

    return { user, session, messages };
  }

  /**
   * Create multiple users for testing
   */
  async createUsers(count: number, overrides: any = {}) {
    const users = [];
    for (let i = 0; i < count; i++) {
      const user = await this.createUser({
        username: `testuser_${i}_${Date.now()}`,
        email: `test_${i}_${Date.now()}@example.com`,
        ...overrides
      });
      users.push(user);
    }
    return users;
  }

  /**
   * Create audit log entry
   */
  async createAuditLog(overrides: any = {}) {
    const auditData = {
      userId: `user_${Date.now()}`,
      action: 'test_action',
      resource: 'test_resource',
      details: JSON.stringify({ test: true }),
      timestamp: new Date(),
      ipAddress: '127.0.0.1',
      userAgent: 'Test Agent',
      ...overrides
    };

    const [audit] = await this.db('audit_logs').insert(auditData).returning('*');
    return audit;
  }
}

// =============================================================================
// TEST DATABASE UTILITIES
// =============================================================================

export class TestDatabaseUtils {
  private db: any;

  constructor(database: any) {
    this.db = database;
  }

  /**
   * Count records in a table
   */
  async countRecords(tableName: string, whereClause: any = {}) {
    const result = await this.db(tableName).where(whereClause).count('* as count');
    return parseInt(result[0].count);
  }

  /**
   * Find records with optional conditions
   */
  async findRecords(tableName: string, whereClause: any = {}, orderBy?: string) {
    let query = this.db(tableName).where(whereClause);
    
    if (orderBy) {
      query = query.orderBy(orderBy);
    }
    
    return await query;
  }

  /**
   * Wait for condition to be met (useful for async operations)
   */
  async waitForCondition(
    condition: () => Promise<boolean>,
    timeout: number = 5000,
    interval: number = 100
  ) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      if (await condition()) {
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, interval));
    }
    
    throw new Error(`Condition not met within ${timeout}ms`);
  }

  /**
   * Execute raw SQL query
   */
  async rawQuery(sql: string, params: any[] = []) {
    return await this.db.raw(sql, params);
  }

  /**
   * Get table info
   */
  async getTableInfo(tableName: string) {
    try {
      // PostgreSQL
      const columns = await this.db.raw(`
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = ?
      `, [tableName]);
      
      return columns.rows || columns[0];
    } catch (error) {
      // Fallback for other databases
      return [];
    }
  }

  /**
   * Check if data exists
   */
  async exists(tableName: string, whereClause: any) {
    const count = await this.countRecords(tableName, whereClause);
    return count > 0;
  }

  /**
   * Get random record from table
   */
  async getRandomRecord(tableName: string, whereClause: any = {}) {
    const records = await this.findRecords(tableName, whereClause);
    if (records.length === 0) return null;
    
    const randomIndex = Math.floor(Math.random() * records.length);
    return records[randomIndex];
  }

  /**
   * Truncate table (faster than DELETE)
   */
  async truncateTable(tableName: string) {
    try {
      await this.db.raw(`TRUNCATE TABLE ${tableName} RESTART IDENTITY CASCADE`);
    } catch (error) {
      // Fallback to DELETE if TRUNCATE is not available
      await this.db(tableName).del();
    }
  }

  /**
   * Create temporary table for testing
   */
  async createTempTable(tableName: string, schema: any) {
    await this.db.schema.createTable(tableName, schema);
  }

  /**
   * Drop temporary table
   */
  async dropTempTable(tableName: string) {
    await this.db.schema.dropTableIfExists(tableName);
  }
}

// =============================================================================
// DATABASE TEST HELPERS
// =============================================================================

export const DatabaseTestHelpers = {
  /**
   * Create a test database manager
   */
  createManager: (database: any) => new DatabaseTestManager(database),

  /**
   * Create a database factory
   */
  createFactory: (database: any) => new DatabaseFactory(database),

  /**
   * Create database utilities
   */
  createUtils: (database: any) => new TestDatabaseUtils(database),

  /**
   * Setup complete test environment
   */
  async setupTestEnvironment(database: any) {
    const manager = new DatabaseTestManager(database);
    const factory = new DatabaseFactory(database);
    const utils = new TestDatabaseUtils(database);

    await manager.setup();

    return { manager, factory, utils };
  },

  /**
   * Cleanup test environment
   */
  async cleanupTestEnvironment(manager: DatabaseTestManager) {
    await manager.cleanup();
  }
};

export default {
  DatabaseTestManager,
  DatabaseFactory,
  TestDatabaseUtils,
  DatabaseTestHelpers
};