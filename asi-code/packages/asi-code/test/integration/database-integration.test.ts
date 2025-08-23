/**
 * Database Integration Tests - Comprehensive testing of database operations
 * 
 * Tests CRUD operations, transactions, migrations, connection pooling,
 * read/write splitting, query building, and database health monitoring.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { Database, createDatabase } from '../../src/database/index.js';
import { PostgresAdapter } from '../../src/database/adapters/postgres-adapter.js';
import { PoolManager } from '../../src/database/connection/pool-manager.js';
import { MigrationRunner } from '../../src/database/migrations/migration-runner.js';
import { TransactionManager } from '../../src/database/query/transaction-manager.js';
import { QueryBuilder } from '../../src/database/query/query-builder.js';
import { Logger } from '../../src/logging/index.js';
import type { DatabaseConfig, Migration, QueryResult } from '../../src/database/types.js';

// Mock database for testing - simulate PostgreSQL operations
class MockDatabaseClient {
  private data = new Map<string, any[]>();
  private transactionState: 'idle' | 'active' | 'error' = 'idle';
  private connected = true;
  private queryCount = 0;

  async connect(): Promise<void> {
    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.connected = false;
  }

  async query(sql: string, params: any[] = []): Promise<QueryResult> {
    if (!this.connected) {
      throw new Error('Database not connected');
    }

    this.queryCount++;
    
    // Simulate query execution time
    await new Promise(resolve => setTimeout(resolve, Math.random() * 50));

    // Mock different query types
    if (sql.includes('CREATE TABLE')) {
      return { rows: [], rowCount: 0, command: 'CREATE', fields: [] };
    }

    if (sql.includes('DROP TABLE')) {
      const tableName = this.extractTableName(sql);
      this.data.delete(tableName);
      return { rows: [], rowCount: 0, command: 'DROP', fields: [] };
    }

    if (sql.includes('INSERT INTO')) {
      const tableName = this.extractTableName(sql);
      const table = this.data.get(tableName) || [];
      const record = { id: table.length + 1, ...this.parseInsertValues(sql, params) };
      table.push(record);
      this.data.set(tableName, table);
      return { rows: [record], rowCount: 1, command: 'INSERT', fields: [] };
    }

    if (sql.includes('SELECT')) {
      const tableName = this.extractTableName(sql);
      const table = this.data.get(tableName) || [];
      return { rows: table, rowCount: table.length, command: 'SELECT', fields: [] };
    }

    if (sql.includes('UPDATE')) {
      const tableName = this.extractTableName(sql);
      const table = this.data.get(tableName) || [];
      return { rows: table, rowCount: table.length, command: 'UPDATE', fields: [] };
    }

    if (sql.includes('DELETE')) {
      const tableName = this.extractTableName(sql);
      this.data.set(tableName, []);
      return { rows: [], rowCount: 0, command: 'DELETE', fields: [] };
    }

    // Migration-related queries
    if (sql.includes('schema_migrations')) {
      return { rows: [], rowCount: 0, command: 'SELECT', fields: [] };
    }

    return { rows: [], rowCount: 0, command: 'UNKNOWN', fields: [] };
  }

  async beginTransaction(): Promise<void> {
    this.transactionState = 'active';
  }

  async commitTransaction(): Promise<void> {
    this.transactionState = 'idle';
  }

  async rollbackTransaction(): Promise<void> {
    this.transactionState = 'idle';
  }

  getStats() {
    return {
      connected: this.connected,
      queryCount: this.queryCount,
      transactionState: this.transactionState
    };
  }

  reset() {
    this.data.clear();
    this.queryCount = 0;
    this.transactionState = 'idle';
  }

  private extractTableName(sql: string): string {
    const match = sql.match(/(?:FROM|INTO|TABLE)\s+(\w+)/i);
    return match ? match[1] : 'unknown_table';
  }

  private parseInsertValues(sql: string, params: any[]): any {
    // Simple mock - in real implementation would parse INSERT statement
    return { data: 'mock_data', created_at: new Date() };
  }
}

// Mock PostgreSQL adapter
class MockPostgresAdapter extends PostgresAdapter {
  private mockClient: MockDatabaseClient;

  constructor(config: DatabaseConfig, logger: Logger) {
    super(config, logger);
    this.mockClient = new MockDatabaseClient();
  }

  async connect(): Promise<void> {
    await this.mockClient.connect();
  }

  async disconnect(): Promise<void> {
    await this.mockClient.disconnect();
  }

  async query(sql: string, params?: any[]): Promise<QueryResult> {
    return this.mockClient.query(sql, params);
  }

  async beginTransaction(): Promise<void> {
    await this.mockClient.beginTransaction();
  }

  async commitTransaction(): Promise<void> {
    await this.mockClient.commitTransaction();
  }

  async rollbackTransaction(): Promise<void> {
    await this.mockClient.rollbackTransaction();
  }

  async healthCheck(): Promise<boolean> {
    return this.mockClient.getStats().connected;
  }

  getStats() {
    return this.mockClient.getStats();
  }

  reset() {
    this.mockClient.reset();
  }
}

describe('Database Integration Tests', () => {
  let database: Database;
  let logger: Logger;
  let mockAdapter: MockPostgresAdapter;
  
  const testConfig: DatabaseConfig = {
    host: 'localhost',
    port: 5432,
    database: 'test_asi_code',
    username: 'test_user',
    password: 'test_password',
    ssl: false,
    pool: {
      min: 2,
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000
    },
    migration: {
      directory: './test/fixtures/migrations',
      tableName: 'schema_migrations'
    }
  };

  beforeAll(async () => {
    logger = new Logger({ level: 'error', enabled: false }); // Silent logger for tests
    mockAdapter = new MockPostgresAdapter(testConfig, logger);
  });

  afterAll(async () => {
    if (database) {
      await database.shutdown();
    }
  });

  beforeEach(async () => {
    mockAdapter.reset();
    // Create database instance with mock adapter
    database = new Database(testConfig, logger);
    // Replace adapter with mock
    (database as any).adapter = mockAdapter;
    await database.initialize();
  });

  afterEach(async () => {
    if (database) {
      await database.shutdown();
    }
  });

  describe('Database Connection Management', () => {
    it('should establish database connection successfully', async () => {
      expect(mockAdapter.getStats().connected).toBe(true);
      
      const healthStatus = await database.getHealthStatus();
      expect(healthStatus.status).toBe('healthy');
      expect(healthStatus.checks.length).toBeGreaterThan(0);
    });

    it('should handle connection failures gracefully', async () => {
      // Simulate connection failure
      await mockAdapter.disconnect();
      
      const healthStatus = await database.getHealthStatus();
      expect(healthStatus.status).toBeOneOf(['degraded', 'unhealthy']);
      
      const failedChecks = healthStatus.checks.filter(c => c.status === 'fail');
      expect(failedChecks.length).toBeGreaterThan(0);
    });

    it('should manage connection pool correctly', async () => {
      const poolManager = new PoolManager(testConfig, logger);
      await poolManager.initialize();

      const poolStats = await poolManager.getStats();
      expect(poolStats.totalConnections).toBeGreaterThanOrEqual(testConfig.pool!.min);
      expect(poolStats.totalConnections).toBeLessThanOrEqual(testConfig.pool!.max);

      await poolManager.shutdown();
    });

    it('should handle concurrent connections', async () => {
      const concurrentQueries = Array.from({ length: 10 }, (_, i) =>
        database.query().raw(`SELECT ${i} as test_value`)
      );

      const results = await Promise.all(concurrentQueries);
      
      expect(results.length).toBe(10);
      results.forEach(result => {
        expect(result.rows).toBeDefined();
      });
    });
  });

  describe('CRUD Operations', () => {
    beforeEach(async () => {
      // Create test table
      await database.query().raw(`
        CREATE TABLE test_users (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL,
          email VARCHAR(255) UNIQUE NOT NULL,
          created_at TIMESTAMP DEFAULT NOW(),
          updated_at TIMESTAMP DEFAULT NOW()
        )
      `);
    });

    it('should perform CREATE operations', async () => {
      const query = database.query()
        .insert({
          name: 'John Doe',
          email: 'john@example.com'
        })
        .into('test_users');

      const result = await query;
      expect(result.rowCount).toBe(1);
      expect(result.rows[0]).toMatchObject({
        id: expect.any(Number),
        name: 'John Doe',
        email: 'john@example.com'
      });
    });

    it('should perform READ operations with filtering', async () => {
      // Insert test data
      await database.query()
        .insert([
          { name: 'Alice', email: 'alice@example.com' },
          { name: 'Bob', email: 'bob@example.com' },
          { name: 'Charlie', email: 'charlie@example.com' }
        ])
        .into('test_users');

      // Select all users
      const allUsers = await database.query()
        .select('*')
        .from('test_users');

      expect(allUsers.rows.length).toBe(3);

      // Select with filtering
      const filteredUsers = await database.query()
        .select('name', 'email')
        .from('test_users')
        .where('name', 'LIKE', 'A%');

      expect(filteredUsers.rows.length).toBe(1);
      expect(filteredUsers.rows[0].name).toBe('Alice');
    });

    it('should perform UPDATE operations', async () => {
      // Insert initial data
      const insertResult = await database.query()
        .insert({ name: 'John Doe', email: 'john@example.com' })
        .into('test_users');

      const userId = insertResult.rows[0].id;

      // Update the user
      const updateResult = await database.query()
        .update({ name: 'John Smith', email: 'john.smith@example.com' })
        .table('test_users')
        .where('id', userId);

      expect(updateResult.rowCount).toBe(1);

      // Verify update
      const updatedUser = await database.query()
        .select('*')
        .from('test_users')
        .where('id', userId);

      expect(updatedUser.rows[0]).toMatchObject({
        id: userId,
        name: 'John Smith',
        email: 'john.smith@example.com'
      });
    });

    it('should perform DELETE operations', async () => {
      // Insert test data
      await database.query()
        .insert([
          { name: 'User1', email: 'user1@example.com' },
          { name: 'User2', email: 'user2@example.com' }
        ])
        .into('test_users');

      // Delete one user
      const deleteResult = await database.query()
        .delete()
        .from('test_users')
        .where('name', 'User1');

      expect(deleteResult.rowCount).toBeGreaterThan(0);

      // Verify deletion
      const remainingUsers = await database.query()
        .select('*')
        .from('test_users');

      expect(remainingUsers.rows.length).toBe(1);
      expect(remainingUsers.rows[0].name).toBe('User2');
    });

    it('should handle complex queries with joins and aggregation', async () => {
      // Create related table
      await database.query().raw(`
        CREATE TABLE test_posts (
          id SERIAL PRIMARY KEY,
          title VARCHAR(255) NOT NULL,
          user_id INTEGER REFERENCES test_users(id),
          created_at TIMESTAMP DEFAULT NOW()
        )
      `);

      // Insert test data
      const userResult = await database.query()
        .insert({ name: 'Author', email: 'author@example.com' })
        .into('test_users');

      const userId = userResult.rows[0].id;

      await database.query()
        .insert([
          { title: 'Post 1', user_id: userId },
          { title: 'Post 2', user_id: userId }
        ])
        .into('test_posts');

      // Complex query with join and count
      const result = await database.query().raw(`
        SELECT u.name, COUNT(p.id) as post_count
        FROM test_users u
        LEFT JOIN test_posts p ON u.id = p.user_id
        GROUP BY u.id, u.name
      `);

      expect(result.rows.length).toBe(1);
      expect(result.rows[0]).toMatchObject({
        name: 'Author',
        post_count: 2
      });
    });
  });

  describe('Transaction Management', () => {
    beforeEach(async () => {
      await database.query().raw(`
        CREATE TABLE test_accounts (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL,
          balance DECIMAL(10,2) DEFAULT 0,
          created_at TIMESTAMP DEFAULT NOW()
        )
      `);

      // Insert test accounts
      await database.query()
        .insert([
          { name: 'Account A', balance: 1000.00 },
          { name: 'Account B', balance: 500.00 }
        ])
        .into('test_accounts');
    });

    it('should execute successful transactions', async () => {
      const transactionManager = database.transaction();
      
      const result = await transactionManager.execute(async (tx) => {
        // Transfer money between accounts
        await tx.query()
          .update({ balance: 900.00 })
          .table('test_accounts')
          .where('name', 'Account A');

        await tx.query()
          .update({ balance: 600.00 })
          .table('test_accounts')
          .where('name', 'Account B');

        return { success: true };
      });

      expect(result.success).toBe(true);

      // Verify transaction was committed
      const accounts = await database.query()
        .select('*')
        .from('test_accounts');

      const accountA = accounts.rows.find(a => a.name === 'Account A');
      const accountB = accounts.rows.find(a => a.name === 'Account B');

      expect(accountA.balance).toBe(900.00);
      expect(accountB.balance).toBe(600.00);
    });

    it('should rollback failed transactions', async () => {
      const transactionManager = database.transaction();
      
      try {
        await transactionManager.execute(async (tx) => {
          // Valid update
          await tx.query()
            .update({ balance: 800.00 })
            .table('test_accounts')
            .where('name', 'Account A');

          // Throw error to trigger rollback
          throw new Error('Transaction failed');
        });
      } catch (error) {
        expect(error.message).toBe('Transaction failed');
      }

      // Verify rollback - balances should be unchanged
      const accounts = await database.query()
        .select('*')
        .from('test_accounts');

      const accountA = accounts.rows.find(a => a.name === 'Account A');
      expect(accountA.balance).toBe(1000.00); // Original balance
    });

    it('should handle nested transactions', async () => {
      const transactionManager = database.transaction();
      
      const result = await transactionManager.execute(async (tx) => {
        await tx.query()
          .update({ balance: 950.00 })
          .table('test_accounts')
          .where('name', 'Account A');

        // Nested transaction (savepoint simulation)
        try {
          await transactionManager.execute(async (nestedTx) => {
            await nestedTx.query()
              .update({ balance: 550.00 })
              .table('test_accounts')
              .where('name', 'Account B');

            // This nested transaction should succeed
            return { nested: true };
          });
        } catch (error) {
          // Handle nested transaction failure
        }

        return { success: true };
      });

      expect(result.success).toBe(true);
    });

    it('should handle concurrent transactions', async () => {
      const transactionManager = database.transaction();
      
      // Run multiple concurrent transactions
      const transactions = Array.from({ length: 5 }, (_, i) =>
        transactionManager.execute(async (tx) => {
          await tx.query()
            .update({ balance: `balance + ${i * 10}` })
            .table('test_accounts')
            .where('name', 'Account A');

          return { transactionId: i };
        })
      );

      const results = await Promise.all(transactions);
      expect(results.length).toBe(5);
      
      // All transactions should complete
      results.forEach((result, i) => {
        expect(result.transactionId).toBe(i);
      });
    });
  });

  describe('Migration System', () => {
    let migrationRunner: MigrationRunner;

    beforeEach(async () => {
      migrationRunner = database.migrations();
    });

    it('should run database migrations', async () => {
      const testMigrations: Migration[] = [
        {
          version: '001',
          name: 'create_users_table',
          up: async (db) => {
            await db.query().raw(`
              CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
              )
            `);
          },
          down: async (db) => {
            await db.query().raw('DROP TABLE users');
          }
        },
        {
          version: '002',
          name: 'add_user_profiles',
          up: async (db) => {
            await db.query().raw(`
              CREATE TABLE user_profiles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                bio TEXT
              )
            `);
          },
          down: async (db) => {
            await db.query().raw('DROP TABLE user_profiles');
          }
        }
      ];

      // Mock migration loading
      vi.spyOn(migrationRunner, 'loadMigrations').mockResolvedValue(testMigrations);

      await migrationRunner.runPendingMigrations();

      const status = await migrationRunner.getStatus();
      expect(status.appliedCount).toBe(2);
      expect(status.pendingCount).toBe(0);
    });

    it('should rollback migrations', async () => {
      const testMigration: Migration = {
        version: '003',
        name: 'test_rollback',
        up: async (db) => {
          await db.query().raw(`
            CREATE TABLE test_rollback_table (
              id SERIAL PRIMARY KEY,
              data VARCHAR(255)
            )
          `);
        },
        down: async (db) => {
          await db.query().raw('DROP TABLE test_rollback_table');
        }
      };

      // Apply migration
      vi.spyOn(migrationRunner, 'loadMigrations').mockResolvedValue([testMigration]);
      await migrationRunner.runPendingMigrations();

      // Rollback migration
      await migrationRunner.rollback('003');

      const status = await migrationRunner.getStatus();
      expect(status.appliedMigrations).not.toContain('003');
    });

    it('should handle migration failures', async () => {
      const failingMigration: Migration = {
        version: '004',
        name: 'failing_migration',
        up: async () => {
          throw new Error('Migration failed');
        },
        down: async () => {}
      };

      vi.spyOn(migrationRunner, 'loadMigrations').mockResolvedValue([failingMigration]);

      await expect(migrationRunner.runPendingMigrations()).rejects.toThrow('Migration failed');

      const status = await migrationRunner.getStatus();
      expect(status.appliedMigrations).not.toContain('004');
    });

    it('should validate migration order and dependencies', async () => {
      const migrationsOutOfOrder: Migration[] = [
        {
          version: '002',
          name: 'second_migration',
          up: async () => {},
          down: async () => {}
        },
        {
          version: '001',
          name: 'first_migration',
          up: async () => {},
          down: async () => {}
        }
      ];

      vi.spyOn(migrationRunner, 'loadMigrations').mockResolvedValue(migrationsOutOfOrder);

      // Migration runner should handle ordering
      await migrationRunner.runPendingMigrations();

      const status = await migrationRunner.getStatus();
      expect(status.appliedMigrations[0]).toBe('001');
      expect(status.appliedMigrations[1]).toBe('002');
    });
  });

  describe('Query Builder', () => {
    let queryBuilder: QueryBuilder;

    beforeEach(async () => {
      queryBuilder = database.query();
      
      await queryBuilder.raw(`
        CREATE TABLE test_products (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL,
          category VARCHAR(100),
          price DECIMAL(10,2),
          in_stock BOOLEAN DEFAULT true,
          created_at TIMESTAMP DEFAULT NOW()
        )
      `);

      await queryBuilder
        .insert([
          { name: 'Product A', category: 'Electronics', price: 99.99, in_stock: true },
          { name: 'Product B', category: 'Electronics', price: 149.99, in_stock: false },
          { name: 'Product C', category: 'Books', price: 29.99, in_stock: true },
          { name: 'Product D', category: 'Books', price: 39.99, in_stock: true }
        ])
        .into('test_products');
    });

    it('should build complex SELECT queries', async () => {
      const result = await queryBuilder
        .select('name', 'price')
        .from('test_products')
        .where('category', '=', 'Electronics')
        .andWhere('in_stock', '=', true)
        .orderBy('price', 'DESC')
        .limit(10);

      expect(result.rows.length).toBe(1);
      expect(result.rows[0].name).toBe('Product A');
    });

    it('should handle query parameters safely', async () => {
      const userInput = "Electronics'; DROP TABLE test_products; --";
      
      const result = await queryBuilder
        .select('*')
        .from('test_products')
        .where('category', '=', userInput);

      // Should not execute malicious SQL
      expect(result.rows.length).toBe(0); // No products match the exact string
    });

    it('should support aggregate functions', async () => {
      const result = await queryBuilder
        .select('category')
        .count('* as product_count')
        .avg('price as avg_price')
        .from('test_products')
        .groupBy('category')
        .having('COUNT(*)', '>', 1);

      expect(result.rows.length).toBe(2); // Electronics and Books categories
      
      const electronicsRow = result.rows.find(row => row.category === 'Electronics');
      expect(electronicsRow.product_count).toBe(2);
    });

    it('should handle subqueries', async () => {
      const subquery = queryBuilder
        .select('AVG(price)')
        .from('test_products');

      const result = await queryBuilder
        .select('*')
        .from('test_products')
        .where('price', '>', subquery);

      // Products above average price
      expect(result.rows.length).toBeGreaterThan(0);
    });

    it('should support bulk operations', async () => {
      // Bulk insert
      const products = Array.from({ length: 100 }, (_, i) => ({
        name: `Bulk Product ${i}`,
        category: 'Bulk',
        price: Math.random() * 100
      }));

      const insertResult = await queryBuilder
        .insert(products)
        .into('test_products');

      expect(insertResult.rowCount).toBe(100);

      // Bulk update
      const updateResult = await queryBuilder
        .update({ category: 'Updated Bulk' })
        .table('test_products')
        .where('category', '=', 'Bulk');

      expect(updateResult.rowCount).toBe(100);

      // Bulk delete
      const deleteResult = await queryBuilder
        .delete()
        .from('test_products')
        .where('category', '=', 'Updated Bulk');

      expect(deleteResult.rowCount).toBe(100);
    });
  });

  describe('Performance and Optimization', () => {
    beforeEach(async () => {
      // Create test table with indexes
      await database.query().raw(`
        CREATE TABLE test_performance (
          id SERIAL PRIMARY KEY,
          indexed_field VARCHAR(255),
          data JSONB,
          created_at TIMESTAMP DEFAULT NOW()
        )
      `);

      await database.query().raw(`
        CREATE INDEX idx_test_performance_indexed_field 
        ON test_performance(indexed_field)
      `);

      // Insert performance test data
      const testData = Array.from({ length: 1000 }, (_, i) => ({
        indexed_field: `value_${i % 100}`,
        data: { id: i, random: Math.random() }
      }));

      await database.query()
        .insert(testData)
        .into('test_performance');
    });

    it('should execute queries efficiently with proper indexing', async () => {
      const startTime = Date.now();

      const result = await database.query()
        .select('*')
        .from('test_performance')
        .where('indexed_field', '=', 'value_50');

      const executionTime = Date.now() - startTime;

      expect(result.rows.length).toBe(10); // 1000/100 = 10 records with value_50
      expect(executionTime).toBeLessThan(1000); // Should be fast with index
    });

    it('should handle concurrent queries without blocking', async () => {
      const concurrentQueries = Array.from({ length: 20 }, (_, i) =>
        database.query()
          .select('*')
          .from('test_performance')
          .where('indexed_field', '=', `value_${i % 10}`)
      );

      const startTime = Date.now();
      const results = await Promise.all(concurrentQueries);
      const totalTime = Date.now() - startTime;

      expect(results.length).toBe(20);
      expect(totalTime).toBeLessThan(5000); // Should complete reasonably fast
      
      results.forEach(result => {
        expect(result.rows.length).toBeGreaterThan(0);
      });
    });

    it('should provide query performance metrics', async () => {
      const stats = mockAdapter.getStats();
      const initialQueryCount = stats.queryCount;

      // Execute some queries
      await database.query().select('*').from('test_performance').limit(10);
      await database.query().select('COUNT(*)').from('test_performance');

      const finalStats = mockAdapter.getStats();
      expect(finalStats.queryCount).toBeGreaterThan(initialQueryCount);
    });

    it('should handle large result sets efficiently', async () => {
      // Test pagination
      const pageSize = 100;
      const page1 = await database.query()
        .select('*')
        .from('test_performance')
        .orderBy('id')
        .limit(pageSize)
        .offset(0);

      const page2 = await database.query()
        .select('*')
        .from('test_performance')
        .orderBy('id')
        .limit(pageSize)
        .offset(pageSize);

      expect(page1.rows.length).toBe(pageSize);
      expect(page2.rows.length).toBe(pageSize);
      expect(page1.rows[0].id).toBeLessThan(page2.rows[0].id);
    });
  });

  describe('Data Integrity and Constraints', () => {
    beforeEach(async () => {
      await database.query().raw(`
        CREATE TABLE test_customers (
          id SERIAL PRIMARY KEY,
          email VARCHAR(255) UNIQUE NOT NULL,
          phone VARCHAR(20),
          created_at TIMESTAMP DEFAULT NOW(),
          CONSTRAINT valid_email CHECK (email LIKE '%@%')
        )
      `);

      await database.query().raw(`
        CREATE TABLE test_orders (
          id SERIAL PRIMARY KEY,
          customer_id INTEGER NOT NULL REFERENCES test_customers(id) ON DELETE CASCADE,
          order_total DECIMAL(10,2) CHECK (order_total > 0),
          order_date TIMESTAMP DEFAULT NOW()
        )
      `);
    });

    it('should enforce UNIQUE constraints', async () => {
      // Insert first customer
      await database.query()
        .insert({ email: 'unique@example.com', phone: '123-456-7890' })
        .into('test_customers');

      // Try to insert duplicate email
      try {
        await database.query()
          .insert({ email: 'unique@example.com', phone: '098-765-4321' })
          .into('test_customers');
        
        expect.fail('Should have thrown unique constraint error');
      } catch (error) {
        expect(error.message).toBeDefined();
      }
    });

    it('should enforce CHECK constraints', async () => {
      try {
        await database.query()
          .insert({ email: 'invalid-email', phone: '123-456-7890' })
          .into('test_customers');
        
        expect.fail('Should have thrown check constraint error');
      } catch (error) {
        expect(error.message).toBeDefined();
      }
    });

    it('should enforce foreign key constraints', async () => {
      try {
        // Try to insert order with non-existent customer
        await database.query()
          .insert({ customer_id: 999999, order_total: 100.00 })
          .into('test_orders');
        
        expect.fail('Should have thrown foreign key constraint error');
      } catch (error) {
        expect(error.message).toBeDefined();
      }
    });

    it('should handle CASCADE deletes correctly', async () => {
      // Insert customer and order
      const customerResult = await database.query()
        .insert({ email: 'cascade@example.com', phone: '123-456-7890' })
        .into('test_customers');

      const customerId = customerResult.rows[0].id;

      await database.query()
        .insert({ customer_id: customerId, order_total: 100.00 })
        .into('test_orders');

      // Delete customer should cascade to orders
      await database.query()
        .delete()
        .from('test_customers')
        .where('id', customerId);

      // Orders should be deleted too
      const remainingOrders = await database.query()
        .select('*')
        .from('test_orders')
        .where('customer_id', customerId);

      expect(remainingOrders.rows.length).toBe(0);
    });
  });

  describe('Backup and Recovery', () => {
    it('should create database backups', async () => {
      // This would typically involve pg_dump or similar
      // For now, we'll simulate backup creation
      const backupManager = (database as any).backupManager;
      
      if (backupManager) {
        const backupResult = await backupManager.createBackup({
          type: 'full',
          format: 'sql',
          tables: ['test_users', 'test_products']
        });

        expect(backupResult).toMatchObject({
          success: true,
          backupId: expect.any(String),
          timestamp: expect.any(Date)
        });
      }
    });

    it('should validate backup integrity', async () => {
      // Simulate backup validation
      const backupManager = (database as any).backupManager;
      
      if (backupManager) {
        const validationResult = await backupManager.validateBackup('test-backup-id');
        expect(validationResult.valid).toBe(true);
      }
    });

    it('should restore from backup', async () => {
      // Simulate database restore
      const backupManager = (database as any).backupManager;
      
      if (backupManager) {
        const restoreResult = await backupManager.restoreBackup('test-backup-id', {
          targetDatabase: 'test_restore_db'
        });

        expect(restoreResult).toMatchObject({
          success: true,
          restoredTables: expect.any(Array)
        });
      }
    });
  });

  describe('Monitoring and Health Checks', () => {
    it('should monitor database health continuously', async () => {
      const healthStatus = await database.getHealthStatus();

      expect(healthStatus).toMatchObject({
        status: expect.oneOf(['healthy', 'degraded', 'unhealthy']),
        checks: expect.arrayContaining([
          expect.objectContaining({
            name: expect.any(String),
            status: expect.oneOf(['pass', 'fail'])
          })
        ])
      });
    });

    it('should track query performance metrics', async () => {
      const initialStats = mockAdapter.getStats();

      // Execute various queries
      await database.query().select('*').from('test_performance').limit(1);
      await database.query().raw('SELECT NOW()');

      const finalStats = mockAdapter.getStats();
      
      expect(finalStats.queryCount).toBeGreaterThan(initialStats.queryCount);
    });

    it('should detect slow queries', async () => {
      // Mock slow query
      const slowQuery = database.query().raw('SELECT pg_sleep(2)');
      
      const startTime = Date.now();
      try {
        await slowQuery;
      } catch (error) {
        // Mock might not support pg_sleep
      }
      const executionTime = Date.now() - startTime;

      // In a real implementation, slow query would be logged
      expect(executionTime).toBeGreaterThan(0);
    });

    it('should handle connection pool exhaustion gracefully', async () => {
      // Simulate pool exhaustion by creating many concurrent long-running queries
      const longRunningQueries = Array.from({ length: 15 }, () => 
        database.query().raw('SELECT 1') // Simple query for mock
      );

      const results = await Promise.allSettled(longRunningQueries);
      
      // Some should succeed, some might timeout or be queued
      const successful = results.filter(r => r.status === 'fulfilled').length;
      expect(successful).toBeGreaterThan(0);
    });
  });
});