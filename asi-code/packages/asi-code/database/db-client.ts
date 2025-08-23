/**
 * PostgreSQL Database Client for ASI-Code
 * Handles all database operations and stores ALL platform data
 */

import { Pool, PoolConfig } from 'pg';
import { v4 as uuidv4 } from 'uuid';
import crypto from 'crypto';

// Database configuration
const dbConfig: PoolConfig = {
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5433'),
  database: process.env.DB_NAME || 'asi_code_db',
  user: process.env.DB_USER || 'asi_admin',
  password: process.env.DB_PASSWORD || 'asi_secure_pass_2024',
  max: 20, // Maximum number of clients in the pool
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
};

export class DatabaseClient {
  private pool: Pool;
  private static instance: DatabaseClient;

  private constructor() {
    this.pool = new Pool(dbConfig);
    this.setupErrorHandlers();
  }

  static getInstance(): DatabaseClient {
    if (!DatabaseClient.instance) {
      DatabaseClient.instance = new DatabaseClient();
    }
    return DatabaseClient.instance;
  }

  private setupErrorHandlers() {
    this.pool.on('error', (err) => {
      console.error('Unexpected database error:', err);
    });
  }

  // ==========================================
  // SESSION MANAGEMENT
  // ==========================================

  async createSession(sessionId: string, ipAddress?: string, userAgent?: string): Promise<string> {
    const query = `
      INSERT INTO sessions (session_id, ip_address, user_agent)
      VALUES ($1, $2, $3)
      RETURNING id
    `;
    const result = await this.pool.query(query, [sessionId, ipAddress, userAgent]);
    return result.rows[0].id;
  }

  async getSession(sessionId: string) {
    const query = 'SELECT * FROM sessions WHERE session_id = $1';
    const result = await this.pool.query(query, [sessionId]);
    return result.rows[0];
  }

  // ==========================================
  // ASI1 CHAT HISTORY
  // ==========================================

  async createConversation(sessionId: string, model: string = 'asi1-mini') {
    const conversationId = `conv_${Date.now()}`;
    const query = `
      INSERT INTO asi1_conversations (session_id, conversation_id, model_used)
      VALUES ($1, $2, $3)
      RETURNING id
    `;
    const session = await this.getSession(sessionId);
    const result = await this.pool.query(query, [session.id, conversationId, model]);
    return { id: result.rows[0].id, conversationId };
  }

  async saveMessage(
    conversationId: string,
    role: string,
    content: string,
    tokens?: { prompt?: number; completion?: number; total?: number }
  ) {
    const query = `
      INSERT INTO asi1_messages (
        conversation_id, message_index, role, content,
        tokens_used, prompt_tokens, completion_tokens
      )
      VALUES (
        (SELECT id FROM asi1_conversations WHERE conversation_id = $1),
        (SELECT COALESCE(MAX(message_index), 0) + 1 FROM asi1_messages WHERE conversation_id = (SELECT id FROM asi1_conversations WHERE conversation_id = $1)),
        $2, $3, $4, $5, $6
      )
      RETURNING id
    `;
    const result = await this.pool.query(query, [
      conversationId,
      role,
      content,
      tokens?.total || 0,
      tokens?.prompt || 0,
      tokens?.completion || 0
    ]);
    return result.rows[0].id;
  }

  // ==========================================
  // ASI1 API CALLS LOGGING
  // ==========================================

  async logAPICall(data: {
    sessionId: string;
    conversationId?: string;
    endpoint: string;
    method: string;
    requestBody: any;
    responseStatus: number;
    responseBody: any;
    responseTimeMs: number;
    errorMessage?: string;
    retryCount?: number;
  }) {
    const requestId = `req_${Date.now()}_${uuidv4().substring(0, 8)}`;
    const query = `
      INSERT INTO asi1_api_calls (
        session_id, conversation_id, request_id, endpoint, method,
        request_body, response_status, response_body, response_time_ms,
        error_message, retry_count
      )
      VALUES (
        (SELECT id FROM sessions WHERE session_id = $1),
        (SELECT id FROM asi1_conversations WHERE conversation_id = $2),
        $3, $4, $5, $6, $7, $8, $9, $10, $11
      )
    `;
    await this.pool.query(query, [
      data.sessionId,
      data.conversationId,
      requestId,
      data.endpoint,
      data.method,
      JSON.stringify(data.requestBody),
      data.responseStatus,
      JSON.stringify(data.responseBody),
      data.responseTimeMs,
      data.errorMessage,
      data.retryCount || 0
    ]);
  }

  // ==========================================
  // ORCHESTRATION & TASKS
  // ==========================================

  async createOrchestration(sessionId: string, taskDescription: string, originalRequest: string) {
    const orchestrationId = `orch_${Date.now()}`;
    const query = `
      INSERT INTO orchestrations (
        session_id, orchestration_id, task_description, original_request
      )
      VALUES (
        (SELECT id FROM sessions WHERE session_id = $1),
        $2, $3, $4
      )
      RETURNING id, orchestration_id
    `;
    const result = await this.pool.query(query, [sessionId, orchestrationId, taskDescription, originalRequest]);
    return result.rows[0];
  }

  async createTask(data: {
    orchestrationId: string;
    taskId: string;
    name: string;
    description?: string;
    taskType?: string;
    assignedAgent?: string;
    canParallel?: boolean;
    dependencies?: any[];
    estimatedHours?: number;
  }) {
    const query = `
      INSERT INTO tasks (
        orchestration_id, task_id, name, description, task_type,
        assigned_agent, can_parallel, dependencies, estimated_hours
      )
      VALUES (
        (SELECT id FROM orchestrations WHERE orchestration_id = $1),
        $2, $3, $4, $5, $6, $7, $8, $9
      )
      RETURNING id
    `;
    const result = await this.pool.query(query, [
      data.orchestrationId,
      data.taskId,
      data.name,
      data.description,
      data.taskType,
      data.assignedAgent,
      data.canParallel || false,
      JSON.stringify(data.dependencies || []),
      data.estimatedHours
    ]);
    return result.rows[0].id;
  }

  async updateTaskStatus(taskId: string, status: string, result?: string, errorMessage?: string) {
    const query = `
      UPDATE tasks 
      SET 
        status = $2,
        result = $3,
        error_message = $4,
        completed_at = CASE WHEN $2 IN ('completed', 'failed') THEN CURRENT_TIMESTAMP ELSE completed_at END,
        started_at = CASE WHEN $2 = 'in_progress' AND started_at IS NULL THEN CURRENT_TIMESTAMP ELSE started_at END
      WHERE task_id = $1
    `;
    await this.pool.query(query, [taskId, status, result, errorMessage]);
  }

  // ==========================================
  // GENERATED FILES & PROJECTS
  // ==========================================

  async createProject(data: {
    sessionId: string;
    orchestrationId?: string;
    projectName: string;
    projectType?: string;
    framework?: string;
    language?: string;
    outputPath?: string;
    features?: string[];
    dependencies?: string[];
  }) {
    const query = `
      INSERT INTO projects (
        session_id, orchestration_id, project_name, project_type,
        framework, language, output_path, features, dependencies
      )
      VALUES (
        (SELECT id FROM sessions WHERE session_id = $1),
        (SELECT id FROM orchestrations WHERE orchestration_id = $2),
        $3, $4, $5, $6, $7, $8, $9
      )
      RETURNING id
    `;
    const result = await this.pool.query(query, [
      data.sessionId,
      data.orchestrationId,
      data.projectName,
      data.projectType,
      data.framework,
      data.language,
      data.outputPath,
      JSON.stringify(data.features || []),
      JSON.stringify(data.dependencies || [])
    ]);
    return result.rows[0].id;
  }

  async saveGeneratedFile(data: {
    projectId: string;
    taskId?: string;
    filePath: string;
    fileName: string;
    content: string;
    language?: string;
    purpose?: string;
    generationMethod?: string;
  }) {
    const fileExtension = data.fileName.split('.').pop();
    const contentHash = crypto.createHash('sha256').update(data.content).digest('hex');
    const fileSizeBytes = Buffer.byteLength(data.content, 'utf8');

    const query = `
      INSERT INTO generated_files (
        project_id, task_id, file_path, file_name, file_extension,
        file_size_bytes, content, content_hash, language, purpose, generation_method
      )
      VALUES (
        $1,
        (SELECT id FROM tasks WHERE task_id = $2),
        $3, $4, $5, $6, $7, $8, $9, $10, $11
      )
      RETURNING id
    `;
    const result = await this.pool.query(query, [
      data.projectId,
      data.taskId,
      data.filePath,
      data.fileName,
      fileExtension,
      fileSizeBytes,
      data.content,
      contentHash,
      data.language,
      data.purpose,
      data.generationMethod || 'asi1'
    ]);
    return result.rows[0].id;
  }

  // ==========================================
  // WEBSOCKET TRACKING
  // ==========================================

  async createWebSocketConnection(sessionId: string, ipAddress?: string) {
    const connectionId = `ws_${Date.now()}_${uuidv4().substring(0, 8)}`;
    const query = `
      INSERT INTO websocket_connections (session_id, connection_id, ip_address)
      VALUES (
        (SELECT id FROM sessions WHERE session_id = $1),
        $2, $3
      )
      RETURNING id, connection_id
    `;
    const result = await this.pool.query(query, [sessionId, connectionId, ipAddress]);
    return result.rows[0];
  }

  async logWebSocketMessage(connectionId: string, direction: 'inbound' | 'outbound', messageType: string, messageData: any) {
    const query = `
      INSERT INTO websocket_messages (connection_id, direction, message_type, message_data)
      VALUES (
        (SELECT id FROM websocket_connections WHERE connection_id = $1),
        $2, $3, $4
      )
    `;
    await this.pool.query(query, [connectionId, direction, messageType, JSON.stringify(messageData)]);
  }

  async closeWebSocketConnection(connectionId: string) {
    const query = `
      UPDATE websocket_connections
      SET disconnected_at = CURRENT_TIMESTAMP
      WHERE connection_id = $1
    `;
    await this.pool.query(query, [connectionId]);
  }

  // ==========================================
  // SYSTEM LOGGING
  // ==========================================

  async log(level: string, source: string, message: string, context?: any, sessionId?: string, stackTrace?: string) {
    const query = `
      INSERT INTO system_logs (log_level, source, message, context, session_id, stack_trace)
      VALUES (
        $1, $2, $3, $4,
        (SELECT id FROM sessions WHERE session_id = $5),
        $6
      )
    `;
    await this.pool.query(query, [level, source, message, JSON.stringify(context || {}), sessionId, stackTrace]);
  }

  // ==========================================
  // RETRY TRACKING
  // ==========================================

  async logRetryAttempt(sourceType: string, sourceId: string, attemptNumber: number, delayMs: number, errorMessage?: string, success: boolean = false) {
    const query = `
      INSERT INTO retry_attempts (source_type, source_id, attempt_number, delay_ms, error_message, success)
      VALUES ($1, $2::uuid, $3, $4, $5, $6)
    `;
    await this.pool.query(query, [sourceType, sourceId, attemptNumber, delayMs, errorMessage, success]);
  }

  // ==========================================
  // API USAGE TRACKING
  // ==========================================

  async trackAPIUsage(apiKeyHash: string, endpoint: string, tokenCount: number, hasError: boolean = false, hitRateLimit: boolean = false) {
    const usageDate = new Date().toISOString().split('T')[0];
    const query = `
      INSERT INTO api_usage (api_key_hash, endpoint, usage_date, request_count, token_count, error_count, rate_limit_hits)
      VALUES ($1, $2, $3, 1, $4, $5, $6)
      ON CONFLICT (api_key_hash, endpoint, usage_date)
      DO UPDATE SET
        request_count = api_usage.request_count + 1,
        token_count = api_usage.token_count + $4,
        error_count = api_usage.error_count + $5,
        rate_limit_hits = api_usage.rate_limit_hits + $6,
        updated_at = CURRENT_TIMESTAMP
    `;
    await this.pool.query(query, [
      apiKeyHash,
      endpoint,
      usageDate,
      tokenCount,
      hasError ? 1 : 0,
      hitRateLimit ? 1 : 0
    ]);
  }

  // ==========================================
  // METRICS & ANALYTICS
  // ==========================================

  async recordMetric(name: string, value: number, unit?: string, tags?: any, sessionId?: string) {
    const query = `
      INSERT INTO performance_metrics (metric_name, metric_value, metric_unit, tags, session_id)
      VALUES (
        $1, $2, $3, $4,
        (SELECT id FROM sessions WHERE session_id = $5)
      )
    `;
    await this.pool.query(query, [name, value, unit, JSON.stringify(tags || {}), sessionId]);
  }

  // ==========================================
  // UTILITY METHODS
  // ==========================================

  async healthCheck(): Promise<boolean> {
    try {
      const result = await this.pool.query('SELECT 1');
      return result.rows.length > 0;
    } catch (error) {
      console.error('Database health check failed:', error);
      return false;
    }
  }

  async close() {
    await this.pool.end();
  }

  // Get pool for direct queries if needed
  getPool() {
    return this.pool;
  }
}

export default DatabaseClient;