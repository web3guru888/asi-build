import { Context, Next } from 'hono';
import { logger } from '../logging/logger.js';

export interface SQLInjectionDetectionResult {
  isSuspicious: boolean;
  confidence: number; // 0-1
  patterns: string[];
  sanitized?: string;
}

export interface SQLProtectionConfig {
  strictMode: boolean;
  blockSuspiciousQueries: boolean;
  logSuspiciousActivity: boolean;
  sanitizeInput: boolean;
  whitelistPatterns?: RegExp[];
  customPatterns?: RegExp[];
}

/**
 * SQL injection protection utility
 */
export class SQLInjectionProtector {
  private readonly config: SQLProtectionConfig;

  // Common SQL injection patterns
  private readonly patterns = {
    // Union-based attacks
    union: /(\bunion\b.*\bselect\b)|(\bselect\b.*\bunion\b)/gi,

    // Comment-based attacks
    comments: /(\/\*[\s\S]*?\*\/)|(--[^\r\n]*)|(\#[^\r\n]*)/gi,

    // Boolean-based attacks
    booleanLogic:
      /(\b(and|or)\b\s*\d+\s*[=<>!]+\s*\d+)|(\b(and|or)\b\s*\d+\s*[=<>!]+\s*\d+\s*--)/gi,

    // Time-based attacks
    timeBased: /(\bwaitfor\b|\bdelay\b|\bsleep\b|\bbenchmark\b)/gi,

    // Error-based attacks
    errorBased: /(convert\(int|cast\(.*as)/gi,

    // Stacked queries
    stackedQueries:
      /;\s*(drop|alter|create|insert|update|delete|exec|execute)/gi,

    // Information schema attacks
    infoSchema: /(information_schema|sysobjects|syscolumns)/gi,

    // Function-based attacks
    functions:
      /(\bchar\b|\bascii\b|\bsubstring\b|\bmid\b|\bleft\b|\bright\b|\blen\b|\blength\b)/gi,

    // Hex encoding
    hexEncoding: /0x[0-9a-f]+/gi,

    // SQL keywords in suspicious contexts
    keywords:
      /(\bdrop\s+(table|database|schema)\b)|(\btruncate\s+table\b)|(\balter\s+table\b)/gi,

    // Conditional statements
    conditionals: /(\bif\b\s*\(.*\bselect\b)|(\bcase\s+when\b)/gi,

    // Version/database info functions
    systemInfo: /(\b(version|user|database|schema|current_user)\s*\(\s*\))/gi,

    // Blind injection patterns
    blindInjection:
      /(\b\d+\s*[=<>!]+\s*\d+\s*(and|or)\s*\d+\s*[=<>!]+\s*\d+)/gi,

    // Load file attacks
    fileOperations: /(\bload_file\b|\binto\s+outfile\b|\binto\s+dumpfile\b)/gi,

    // Privilege escalation
    privileges: /(\bgrant\b|\brevoke\b|\bcreate\s+user\b)/gi,

    // Special characters in dangerous contexts
    dangerousChars: /(['"]\s*(;|\||&|\$))|(\$\{.*\})/gi,

    // XPath injection (often combined with SQL)
    xpath: /(\bextractvalue\b|\bupdatexml\b)/gi,

    // NoSQL injection patterns (for MongoDB etc.)
    nosql: /(\$where|\$ne|\$gt|\$lt|\$regex|\$or|\$and)/gi,
  };

  constructor(config: Partial<SQLProtectionConfig> = {}) {
    this.config = {
      strictMode: false,
      blockSuspiciousQueries: true,
      logSuspiciousActivity: true,
      sanitizeInput: true,
      ...config,
    };
  }

  /**
   * Analyze input for SQL injection patterns
   */
  analyzeInput(input: string): SQLInjectionDetectionResult {
    if (!input || typeof input !== 'string') {
      return {
        isSuspicious: false,
        confidence: 0,
        patterns: [],
      };
    }

    const detectedPatterns: string[] = [];
    let totalMatches = 0;
    let maxSeverity = 0;

    // Check against all patterns
    for (const [patternName, pattern] of Object.entries(this.patterns)) {
      const matches = input.match(pattern);
      if (matches) {
        detectedPatterns.push(patternName);
        totalMatches += matches.length;

        // Assign severity weights
        const severity = this.getPatternSeverity(patternName);
        maxSeverity = Math.max(maxSeverity, severity);
      }
    }

    // Check custom patterns if provided
    if (this.config.customPatterns) {
      for (const pattern of this.config.customPatterns) {
        if (pattern.test(input)) {
          detectedPatterns.push('custom');
          totalMatches += 1;
          maxSeverity = Math.max(maxSeverity, 0.8);
        }
      }
    }

    // Calculate confidence based on matches and severity
    const confidence = Math.min(totalMatches * 0.2 + maxSeverity * 0.8, 1.0);

    const isSuspicious = this.config.strictMode
      ? confidence > 0.1
      : confidence > 0.5;

    let sanitized: string | undefined;
    if (this.config.sanitizeInput && isSuspicious) {
      sanitized = this.sanitizeInput(input);
    }

    return {
      isSuspicious,
      confidence,
      patterns: detectedPatterns,
      sanitized,
    };
  }

  /**
   * Get severity weight for a pattern
   */
  private getPatternSeverity(patternName: string): number {
    const severityMap: Record<string, number> = {
      union: 0.9,
      stackedQueries: 0.95,
      keywords: 0.8,
      timeBased: 0.85,
      errorBased: 0.7,
      fileOperations: 0.9,
      privileges: 0.95,
      comments: 0.6,
      booleanLogic: 0.7,
      infoSchema: 0.8,
      functions: 0.4,
      hexEncoding: 0.5,
      conditionals: 0.6,
      systemInfo: 0.7,
      blindInjection: 0.75,
      dangerousChars: 0.5,
      xpath: 0.8,
      nosql: 0.6,
    };

    return severityMap[patternName] || 0.5;
  }

  /**
   * Sanitize potentially malicious input
   */
  sanitizeInput(input: string): string {
    if (!input || typeof input !== 'string') {
      return '';
    }

    let sanitized = input;

    // Remove SQL comments
    sanitized = sanitized.replace(
      /(\/\*[\s\S]*?\*\/)|(--[^\r\n]*)|(\#[^\r\n]*)/gi,
      ''
    );

    // Remove dangerous SQL keywords
    const dangerousKeywords = [
      'union',
      'select',
      'insert',
      'update',
      'delete',
      'drop',
      'create',
      'alter',
      'exec',
      'execute',
      'sp_',
      'xp_',
      'waitfor',
      'delay',
      'sleep',
      'benchmark',
    ];

    for (const keyword of dangerousKeywords) {
      const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
      sanitized = sanitized.replace(regex, '');
    }

    // Remove or escape dangerous characters
    sanitized = sanitized.replace(/['"`;|&${}]/g, '');

    // Remove hex encoding
    sanitized = sanitized.replace(/0x[0-9a-f]+/gi, '');

    // Remove excessive whitespace
    sanitized = sanitized.replace(/\s+/g, ' ').trim();

    // Limit length
    if (sanitized.length > 1000) {
      sanitized = sanitized.substring(0, 1000);
    }

    return sanitized;
  }

  /**
   * Create parameterized query helper
   */
  static createParameterizedQuery(
    query: string,
    params: Record<string, any>
  ): { query: string; values: any[] } {
    const values: any[] = [];
    let paramIndex = 1;

    // Replace named parameters with positional parameters
    const processedQuery = query.replace(/:(\w+)/g, (match, paramName) => {
      if (params.hasOwnProperty(paramName)) {
        values.push(params[paramName]);
        return `$${paramIndex++}`;
      }
      return match;
    });

    return {
      query: processedQuery,
      values,
    };
  }

  /**
   * Validate parameter types
   */
  static validateParameters(params: Record<string, any>): boolean {
    for (const [key, value] of Object.entries(params)) {
      // Check for null/undefined
      if (value === null || value === undefined) {
        continue;
      }

      // Validate parameter name
      if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(key)) {
        logger.warn('Invalid parameter name', { paramName: key });
        return false;
      }

      // Check for object injection
      if (
        typeof value === 'object' &&
        !Array.isArray(value) &&
        !(value instanceof Date)
      ) {
        logger.warn('Object parameter detected', {
          paramName: key,
          type: typeof value,
        });
        return false;
      }

      // Validate string parameters
      if (typeof value === 'string') {
        if (value.length > 10000) {
          // Reasonable string length limit
          logger.warn('Parameter too long', {
            paramName: key,
            length: value.length,
          });
          return false;
        }
      }
    }

    return true;
  }

  /**
   * Escape SQL identifiers (table names, column names)
   */
  static escapeIdentifier(identifier: string): string {
    if (!identifier || typeof identifier !== 'string') {
      throw new Error('Identifier must be a non-empty string');
    }

    // Validate identifier format
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(identifier)) {
      throw new Error('Invalid identifier format');
    }

    // Double quote for PostgreSQL, backticks for MySQL
    return `"${identifier}"`;
  }

  /**
   * Escape SQL string literals
   */
  static escapeString(value: string): string {
    if (typeof value !== 'string') {
      return value;
    }

    // Escape single quotes by doubling them
    return value.replace(/'/g, "''");
  }
}

/**
 * SQL injection protection middleware
 */
export function createSQLProtectionMiddleware(
  config?: Partial<SQLProtectionConfig>
) {
  const protector = new SQLInjectionProtector(config);

  return async (c: Context, next: Next) => {
    try {
      const suspiciousInputs: Array<{
        source: string;
        field: string;
        value: string;
        analysis: SQLInjectionDetectionResult;
      }> = [];

      // Check query parameters
      const queryParams = c.req.query();
      for (const [key, value] of Object.entries(queryParams)) {
        if (typeof value === 'string') {
          const analysis = protector.analyzeInput(value);
          if (analysis.isSuspicious) {
            suspiciousInputs.push({
              source: 'query',
              field: key,
              value,
              analysis,
            });
          }
        }
      }

      // Check request body if JSON
      if (c.req.header('content-type')?.includes('application/json')) {
        try {
          const body = await c.req.json();
          const flattenedBody = flattenObject(body);

          for (const [key, value] of Object.entries(flattenedBody)) {
            if (typeof value === 'string') {
              const analysis = protector.analyzeInput(value);
              if (analysis.isSuspicious) {
                suspiciousInputs.push({
                  source: 'body',
                  field: key,
                  value,
                  analysis,
                });
              }
            }
          }
        } catch (error) {
          // Invalid JSON, but not necessarily malicious
          logger.debug('Invalid JSON in request body');
        }
      }

      // Handle suspicious inputs
      if (suspiciousInputs.length > 0) {
        if (config?.logSuspiciousActivity !== false) {
          logger.warn('SQL injection attempt detected', {
            ip: c.req.header('x-forwarded-for') || c.env?.remoteAddr,
            userAgent: c.req.header('user-agent'),
            path: c.req.path,
            method: c.req.method,
            suspiciousInputs: suspiciousInputs.map(input => ({
              source: input.source,
              field: input.field,
              confidence: input.analysis.confidence,
              patterns: input.analysis.patterns,
            })),
          });
        }

        if (config?.blockSuspiciousQueries !== false) {
          return c.json(
            {
              error: 'Potentially malicious input detected',
              message: 'Request blocked for security reasons',
              details: suspiciousInputs.map(input => ({
                field: `${input.source}.${input.field}`,
                confidence: input.analysis.confidence,
                patterns: input.analysis.patterns,
              })),
            },
            400
          );
        }
      }

      // Store analysis results for potential use in handlers
      c.set('sqlAnalysis', suspiciousInputs);

      await next();
    } catch (error) {
      logger.error('SQL protection middleware error', error);
      await next(); // Continue on error
    }
  };
}

/**
 * Query builder with built-in SQL injection protection
 */
export class SecureQueryBuilder {
  private query: string = '';
  private parameters: Record<string, any> = {};
  private readonly protector: SQLInjectionProtector;

  constructor() {
    this.protector = new SQLInjectionProtector({ strictMode: true });
  }

  /**
   * Add SELECT clause
   */
  select(columns: string[]): this {
    // Validate and escape column names
    const escapedColumns = columns.map(col =>
      SQLInjectionProtector.escapeIdentifier(col)
    );

    this.query = `SELECT ${escapedColumns.join(', ')}`;
    return this;
  }

  /**
   * Add FROM clause
   */
  from(table: string): this {
    const escapedTable = SQLInjectionProtector.escapeIdentifier(table);
    this.query += ` FROM ${escapedTable}`;
    return this;
  }

  /**
   * Add WHERE clause with parameterized conditions
   */
  where(conditions: Record<string, any>): this {
    const whereClauses: string[] = [];

    for (const [column, value] of Object.entries(conditions)) {
      const escapedColumn = SQLInjectionProtector.escapeIdentifier(column);
      const paramName = `param_${Object.keys(this.parameters).length}`;

      whereClauses.push(`${escapedColumn} = :${paramName}`);
      this.parameters[paramName] = value;
    }

    if (whereClauses.length > 0) {
      this.query += ` WHERE ${whereClauses.join(' AND ')}`;
    }

    return this;
  }

  /**
   * Add ORDER BY clause
   */
  orderBy(column: string, direction: 'ASC' | 'DESC' = 'ASC'): this {
    const escapedColumn = SQLInjectionProtector.escapeIdentifier(column);
    this.query += ` ORDER BY ${escapedColumn} ${direction}`;
    return this;
  }

  /**
   * Add LIMIT clause
   */
  limit(count: number): this {
    if (typeof count !== 'number' || count < 0 || !Number.isInteger(count)) {
      throw new Error('Limit must be a non-negative integer');
    }

    this.query += ` LIMIT ${count}`;
    return this;
  }

  /**
   * Build the final query with parameters
   */
  build(): { query: string; values: any[] } {
    // Validate parameters
    if (!SQLInjectionProtector.validateParameters(this.parameters)) {
      throw new Error('Invalid parameters detected');
    }

    return SQLInjectionProtector.createParameterizedQuery(
      this.query,
      this.parameters
    );
  }

  /**
   * Reset the builder
   */
  reset(): this {
    this.query = '';
    this.parameters = {};
    return this;
  }
}

/**
 * Flatten nested object for analysis
 */
function flattenObject(obj: any, prefix: string = ''): Record<string, any> {
  const flattened: Record<string, any> = {};

  for (const [key, value] of Object.entries(obj)) {
    const newKey = prefix ? `${prefix}.${key}` : key;

    if (value && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(flattened, flattenObject(value, newKey));
    } else {
      flattened[newKey] = value;
    }
  }

  return flattened;
}

export default SQLInjectionProtector;
