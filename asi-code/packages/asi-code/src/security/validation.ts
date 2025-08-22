import { Context, Next } from 'hono';
import { validator } from 'hono/validator';
import DOMPurify from 'isomorphic-dompurify';
import { z } from 'zod';
import { logger } from '../logging/logger.js';

export interface ValidationRule {
  field: string;
  type: 'string' | 'number' | 'boolean' | 'email' | 'url' | 'uuid' | 'json' | 'array' | 'object';
  required?: boolean;
  min?: number;
  max?: number;
  pattern?: RegExp;
  enum?: any[];
  sanitize?: boolean;
  customValidator?: (value: any) => boolean | string;
}

export interface SanitizationOptions {
  allowedTags?: string[];
  allowedAttributes?: Record<string, string[]>;
  stripTags?: boolean;
  encodeEntities?: boolean;
  maxLength?: number;
}

export interface ValidationResult {
  isValid: boolean;
  errors: Array<{
    field: string;
    message: string;
    value?: any;
  }>;
  sanitizedData?: any;
}

/**
 * Input validation and sanitization utility
 */
export class InputValidator {
  private static domPurifyConfig = {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
    ALLOWED_ATTR: ['href', 'title'],
    ALLOW_DATA_ATTR: false,
    FORBID_TAGS: ['script', 'object', 'embed', 'form', 'input'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover']
  };

  /**
   * Validate data against rules
   */
  static validate(data: any, rules: ValidationRule[]): ValidationResult {
    const errors: Array<{ field: string; message: string; value?: any }> = [];
    const sanitizedData: any = Array.isArray(data) ? [] : {};

    for (const rule of rules) {
      const value = this.getNestedValue(data, rule.field);
      const validationResult = this.validateField(value, rule);
      
      if (!validationResult.isValid) {
        errors.push({
          field: rule.field,
          message: validationResult.error!,
          value: value
        });
      } else {
        this.setNestedValue(sanitizedData, rule.field, validationResult.sanitizedValue);
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      sanitizedData
    };
  }

  /**
   * Validate single field
   */
  private static validateField(value: any, rule: ValidationRule): { 
    isValid: boolean; 
    error?: string; 
    sanitizedValue?: any 
  } {
    // Check required
    if (rule.required && (value === undefined || value === null || value === '')) {
      return { isValid: false, error: `${rule.field} is required` };
    }

    // Skip validation if value is not provided and not required
    if (!rule.required && (value === undefined || value === null)) {
      return { isValid: true, sanitizedValue: value };
    }

    let sanitizedValue = value;

    // Type validation and sanitization
    switch (rule.type) {
      case 'string':
        if (typeof value !== 'string') {
          return { isValid: false, error: `${rule.field} must be a string` };
        }
        sanitizedValue = rule.sanitize ? this.sanitizeString(value) : value;
        break;

      case 'number':
        const num = Number(value);
        if (isNaN(num)) {
          return { isValid: false, error: `${rule.field} must be a number` };
        }
        sanitizedValue = num;
        break;

      case 'boolean':
        if (typeof value !== 'boolean' && value !== 'true' && value !== 'false') {
          return { isValid: false, error: `${rule.field} must be a boolean` };
        }
        sanitizedValue = typeof value === 'boolean' ? value : value === 'true';
        break;

      case 'email':
        if (!this.isValidEmail(String(value))) {
          return { isValid: false, error: `${rule.field} must be a valid email` };
        }
        sanitizedValue = String(value).toLowerCase().trim();
        break;

      case 'url':
        if (!this.isValidURL(String(value))) {
          return { isValid: false, error: `${rule.field} must be a valid URL` };
        }
        sanitizedValue = String(value).trim();
        break;

      case 'uuid':
        if (!this.isValidUUID(String(value))) {
          return { isValid: false, error: `${rule.field} must be a valid UUID` };
        }
        sanitizedValue = String(value).toLowerCase();
        break;

      case 'json':
        try {
          sanitizedValue = typeof value === 'string' ? JSON.parse(value) : value;
        } catch {
          return { isValid: false, error: `${rule.field} must be valid JSON` };
        }
        break;

      case 'array':
        if (!Array.isArray(value)) {
          return { isValid: false, error: `${rule.field} must be an array` };
        }
        sanitizedValue = value;
        break;

      case 'object':
        if (typeof value !== 'object' || Array.isArray(value) || value === null) {
          return { isValid: false, error: `${rule.field} must be an object` };
        }
        sanitizedValue = value;
        break;
    }

    // Length validation
    if (rule.min !== undefined) {
      const length = typeof sanitizedValue === 'string' ? sanitizedValue.length : 
                     Array.isArray(sanitizedValue) ? sanitizedValue.length :
                     typeof sanitizedValue === 'number' ? sanitizedValue : 0;
      
      if (length < rule.min) {
        return { 
          isValid: false, 
          error: `${rule.field} must be at least ${rule.min} ${rule.type === 'number' ? 'value' : 'characters'}` 
        };
      }
    }

    if (rule.max !== undefined) {
      const length = typeof sanitizedValue === 'string' ? sanitizedValue.length : 
                     Array.isArray(sanitizedValue) ? sanitizedValue.length :
                     typeof sanitizedValue === 'number' ? sanitizedValue : 0;
      
      if (length > rule.max) {
        return { 
          isValid: false, 
          error: `${rule.field} must be at most ${rule.max} ${rule.type === 'number' ? 'value' : 'characters'}` 
        };
      }
    }

    // Pattern validation
    if (rule.pattern && typeof sanitizedValue === 'string') {
      if (!rule.pattern.test(sanitizedValue)) {
        return { isValid: false, error: `${rule.field} format is invalid` };
      }
    }

    // Enum validation
    if (rule.enum && !rule.enum.includes(sanitizedValue)) {
      return { 
        isValid: false, 
        error: `${rule.field} must be one of: ${rule.enum.join(', ')}` 
      };
    }

    // Custom validator
    if (rule.customValidator) {
      const customResult = rule.customValidator(sanitizedValue);
      if (customResult !== true) {
        return { 
          isValid: false, 
          error: typeof customResult === 'string' ? customResult : `${rule.field} is invalid` 
        };
      }
    }

    return { isValid: true, sanitizedValue };
  }

  /**
   * Sanitize string input
   */
  static sanitizeString(input: string, options?: SanitizationOptions): string {
    if (!input || typeof input !== 'string') {
      return '';
    }

    let sanitized = input;

    // Trim whitespace
    sanitized = sanitized.trim();

    // Limit length
    if (options?.maxLength) {
      sanitized = sanitized.substring(0, options.maxLength);
    }

    // Strip or sanitize HTML
    if (options?.stripTags) {
      sanitized = sanitized.replace(/<[^>]*>/g, '');
    } else {
      const purifyOptions = {
        ...this.domPurifyConfig,
        ...(options?.allowedTags && { ALLOWED_TAGS: options.allowedTags }),
        ...(options?.allowedAttributes && { ALLOWED_ATTR: Object.values(options.allowedAttributes).flat() })
      };
      
      sanitized = DOMPurify.sanitize(sanitized, purifyOptions);
    }

    // Encode HTML entities
    if (options?.encodeEntities) {
      sanitized = this.encodeHTMLEntities(sanitized);
    }

    return sanitized;
  }

  /**
   * Sanitize HTML content
   */
  static sanitizeHTML(html: string, options?: SanitizationOptions): string {
    if (!html || typeof html !== 'string') {
      return '';
    }

    const purifyOptions = {
      ...this.domPurifyConfig,
      ...(options?.allowedTags && { ALLOWED_TAGS: options.allowedTags }),
      ...(options?.allowedAttributes && { ALLOWED_ATTR: Object.values(options.allowedAttributes).flat() })
    };

    return DOMPurify.sanitize(html, purifyOptions);
  }

  /**
   * Sanitize object recursively
   */
  static sanitizeObject(obj: any, options?: SanitizationOptions): any {
    if (!obj || typeof obj !== 'object') {
      return obj;
    }

    if (Array.isArray(obj)) {
      return obj.map(item => this.sanitizeObject(item, options));
    }

    const sanitized: any = {};
    
    for (const [key, value] of Object.entries(obj)) {
      if (typeof value === 'string') {
        sanitized[key] = this.sanitizeString(value, options);
      } else if (typeof value === 'object' && value !== null) {
        sanitized[key] = this.sanitizeObject(value, options);
      } else {
        sanitized[key] = value;
      }
    }

    return sanitized;
  }

  /**
   * SQL injection prevention
   */
  static sanitizeSQL(input: string): string {
    if (!input || typeof input !== 'string') {
      return '';
    }

    // Remove common SQL injection patterns
    const sqlPatterns = [
      /('|(\\')|(;)|(\|)|(\*)|(%)|(<)|(>)|(\{)|(\})|(\[)|(\])|(\()|(\))/gi,
      /((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))/gi,
      /\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))/gi,
      /((\%27)|(\'))union/gi,
      /exec(\s|\+)+(s|x)p\w+/gi,
      /UNION[^a-zA-Z0-9]/gi,
      /SELECT[^a-zA-Z0-9]/gi,
      /INSERT[^a-zA-Z0-9]/gi,
      /UPDATE[^a-zA-Z0-9]/gi,
      /DELETE[^a-zA-Z0-9]/gi,
      /DROP[^a-zA-Z0-9]/gi,
      /CREATE[^a-zA-Z0-9]/gi,
      /ALTER[^a-zA-Z0-9]/gi
    ];

    let sanitized = input;
    
    sqlPatterns.forEach(pattern => {
      sanitized = sanitized.replace(pattern, '');
    });

    return sanitized.trim();
  }

  /**
   * NoSQL injection prevention
   */
  static sanitizeNoSQL(input: any): any {
    if (typeof input === 'string') {
      return input.replace(/[${}]/g, '');
    }
    
    if (typeof input === 'object' && input !== null) {
      if (Array.isArray(input)) {
        return input.map(item => this.sanitizeNoSQL(item));
      }
      
      const sanitized: any = {};
      for (const [key, value] of Object.entries(input)) {
        // Prevent prototype pollution
        if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
          continue;
        }
        
        // Remove MongoDB operators
        if (typeof key === 'string' && key.startsWith('$')) {
          continue;
        }
        
        sanitized[key] = this.sanitizeNoSQL(value);
      }
      return sanitized;
    }
    
    return input;
  }

  /**
   * Validate email format
   */
  private static isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email) && email.length <= 254;
  }

  /**
   * Validate URL format
   */
  private static isValidURL(url: string): boolean {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Validate UUID format
   */
  private static isValidUUID(uuid: string): boolean {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
  }

  /**
   * Encode HTML entities
   */
  private static encodeHTMLEntities(str: string): string {
    const entityMap: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#x27;',
      '/': '&#x2F;'
    };
    
    return str.replace(/[&<>"'\/]/g, (s) => entityMap[s]);
  }

  /**
   * Get nested value from object
   */
  private static getNestedValue(obj: any, path: string): any {
    return path.split('.').reduce((current, key) => {
      return current && current[key] !== undefined ? current[key] : undefined;
    }, obj);
  }

  /**
   * Set nested value in object
   */
  private static setNestedValue(obj: any, path: string, value: any): void {
    const keys = path.split('.');
    const lastKey = keys.pop()!;
    
    const target = keys.reduce((current, key) => {
      if (current[key] === undefined) {
        current[key] = {};
      }
      return current[key];
    }, obj);
    
    target[lastKey] = value;
  }
}

/**
 * Zod-based validation schemas
 */
export const ValidationSchemas = {
  user: z.object({
    id: z.string().uuid().optional(),
    email: z.string().email().max(254),
    name: z.string().min(1).max(100),
    password: z.string().min(8).max(128).optional(),
    roles: z.array(z.string()).optional()
  }),

  session: z.object({
    id: z.string().uuid().optional(),
    userId: z.string().uuid(),
    data: z.record(z.any()).optional(),
    expiresAt: z.date().optional()
  }),

  toolExecution: z.object({
    toolName: z.string().min(1).max(50),
    args: z.record(z.any()),
    sessionId: z.string().uuid()
  }),

  fileOperation: z.object({
    path: z.string().min(1).max(1000),
    content: z.string().max(10 * 1024 * 1024).optional(), // 10MB limit
    encoding: z.enum(['utf8', 'base64']).optional()
  }),

  apiKey: z.object({
    name: z.string().min(1).max(100),
    permissions: z.array(z.string()),
    expiresAt: z.date().optional()
  })
};

/**
 * Create validation middleware
 */
export function createValidationMiddleware(schema: z.ZodSchema) {
  return validator('json', (value, c) => {
    try {
      const parsed = schema.parse(value);
      return parsed;
    } catch (error) {
      if (error instanceof z.ZodError) {
        logger.warn('Validation failed', { 
          errors: error.errors,
          path: c.req.path,
          method: c.req.method
        });
        
        return c.json({
          error: 'Validation failed',
          details: error.errors.map(err => ({
            field: err.path.join('.'),
            message: err.message,
            code: err.code
          }))
        }, 400);
      }
      
      logger.error('Validation error', error);
      return c.json({ error: 'Validation error' }, 400);
    }
  });
}

/**
 * Sanitization middleware
 */
export function sanitizationMiddleware(options?: SanitizationOptions) {
  return async (c: Context, next: Next) => {
    try {
      // Sanitize request body
      if (c.req.header('content-type')?.includes('application/json')) {
        const body = await c.req.json();
        const sanitized = InputValidator.sanitizeObject(body, options);
        
        // Replace the request body (implementation depends on framework)
        c.set('sanitizedBody', sanitized);
      }

      // Sanitize query parameters
      const query = c.req.query();
      const sanitizedQuery: Record<string, string> = {};
      
      for (const [key, value] of Object.entries(query)) {
        if (typeof value === 'string') {
          sanitizedQuery[key] = InputValidator.sanitizeString(value, options);
        }
      }
      
      c.set('sanitizedQuery', sanitizedQuery);
      
      await next();
    } catch (error) {
      logger.error('Sanitization error', error);
      await next(); // Continue on error
    }
  };
}

/**
 * File upload validation
 */
export function validateFileUpload(options: {
  maxSize?: number;
  allowedTypes?: string[];
  allowedExtensions?: string[];
}) {
  return async (c: Context, next: Next) => {
    try {
      const contentType = c.req.header('content-type');
      const contentLength = parseInt(c.req.header('content-length') || '0');

      // Check file size
      if (options.maxSize && contentLength > options.maxSize) {
        return c.json({
          error: 'File too large',
          maxSize: options.maxSize,
          actualSize: contentLength
        }, 413);
      }

      // Check content type
      if (options.allowedTypes && contentType && !options.allowedTypes.includes(contentType)) {
        return c.json({
          error: 'File type not allowed',
          allowedTypes: options.allowedTypes,
          actualType: contentType
        }, 400);
      }

      await next();
    } catch (error) {
      logger.error('File validation error', error);
      return c.json({ error: 'File validation failed' }, 400);
    }
  };
}

export default InputValidator;