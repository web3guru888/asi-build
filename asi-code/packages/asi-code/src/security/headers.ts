import { Context, Next } from 'hono';
import { cors } from 'hono/cors';
import { logger } from '../logging/logger.js';

export interface SecurityHeadersConfig {
  contentSecurityPolicy?: CSPConfig;
  cors?: CORSConfig;
  hsts?: HSTSConfig;
  frameOptions?: 'DENY' | 'SAMEORIGIN' | 'ALLOW-FROM';
  contentTypeOptions?: boolean;
  xssProtection?: boolean;
  referrerPolicy?: ReferrerPolicyValue;
  permissionsPolicy?: PermissionsPolicyConfig;
  reportingEndpoints?: ReportingEndpoint[];
}

export interface CSPConfig {
  directives?: {
    'default-src'?: string[];
    'script-src'?: string[];
    'style-src'?: string[];
    'img-src'?: string[];
    'connect-src'?: string[];
    'font-src'?: string[];
    'object-src'?: string[];
    'media-src'?: string[];
    'frame-src'?: string[];
    'child-src'?: string[];
    'worker-src'?: string[];
    'manifest-src'?: string[];
    'base-uri'?: string[];
    'form-action'?: string[];
    'frame-ancestors'?: string[];
    'upgrade-insecure-requests'?: boolean;
    'block-all-mixed-content'?: boolean;
  };
  reportOnly?: boolean;
  reportUri?: string;
  reportTo?: string;
}

export interface CORSConfig {
  origin?: string | string[] | ((origin: string) => boolean);
  credentials?: boolean;
  methods?: string[];
  allowedHeaders?: string[];
  exposedHeaders?: string[];
  maxAge?: number;
  preflightContinue?: boolean;
  optionsSuccessStatus?: number;
}

export interface HSTSConfig {
  maxAge: number;
  includeSubDomains?: boolean;
  preload?: boolean;
}

export interface PermissionsPolicyConfig {
  accelerometer?: PermissionsPolicyDirective;
  'ambient-light-sensor'?: PermissionsPolicyDirective;
  autoplay?: PermissionsPolicyDirective;
  battery?: PermissionsPolicyDirective;
  camera?: PermissionsPolicyDirective;
  'cross-origin-isolated'?: PermissionsPolicyDirective;
  'display-capture'?: PermissionsPolicyDirective;
  'document-domain'?: PermissionsPolicyDirective;
  'encrypted-media'?: PermissionsPolicyDirective;
  'execution-while-not-rendered'?: PermissionsPolicyDirective;
  'execution-while-out-of-viewport'?: PermissionsPolicyDirective;
  fullscreen?: PermissionsPolicyDirective;
  geolocation?: PermissionsPolicyDirective;
  gyroscope?: PermissionsPolicyDirective;
  magnetometer?: PermissionsPolicyDirective;
  microphone?: PermissionsPolicyDirective;
  midi?: PermissionsPolicyDirective;
  'navigation-override'?: PermissionsPolicyDirective;
  payment?: PermissionsPolicyDirective;
  'picture-in-picture'?: PermissionsPolicyDirective;
  'publickey-credentials-get'?: PermissionsPolicyDirective;
  'screen-wake-lock'?: PermissionsPolicyDirective;
  'sync-xhr'?: PermissionsPolicyDirective;
  usb?: PermissionsPolicyDirective;
  'web-share'?: PermissionsPolicyDirective;
  'xr-spatial-tracking'?: PermissionsPolicyDirective;
}

export interface ReportingEndpoint {
  name: string;
  url: string;
  includeSubdomains?: boolean;
}

type PermissionsPolicyDirective = '*' | 'self' | 'none' | string[];
type ReferrerPolicyValue =
  | 'no-referrer'
  | 'no-referrer-when-downgrade'
  | 'origin'
  | 'origin-when-cross-origin'
  | 'same-origin'
  | 'strict-origin'
  | 'strict-origin-when-cross-origin'
  | 'unsafe-url';

/**
 * Security headers middleware
 */
export class SecurityHeaders {
  private readonly config: SecurityHeadersConfig;

  constructor(config: SecurityHeadersConfig = {}) {
    this.config = {
      ...this.getDefaultConfig(),
      ...config,
    };
  }

  /**
   * Get default security configuration
   */
  private getDefaultConfig(): SecurityHeadersConfig {
    return {
      contentSecurityPolicy: {
        directives: {
          'default-src': ["'self'"],
          'script-src': ["'self'", "'unsafe-inline'"],
          'style-src': ["'self'", "'unsafe-inline'"],
          'img-src': ["'self'", 'data:', 'https:'],
          'connect-src': ["'self'"],
          'font-src': ["'self'"],
          'object-src': ["'none'"],
          'media-src': ["'self'"],
          'frame-src': ["'none'"],
          'base-uri': ["'self'"],
          'form-action': ["'self'"],
          'frame-ancestors': ["'none'"],
          'upgrade-insecure-requests': true,
        },
        reportOnly: false,
      },
      cors: {
        origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
        credentials: true,
        methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allowedHeaders: [
          'Content-Type',
          'Authorization',
          'X-API-Key',
          'X-Requested-With',
          'Accept',
          'Origin',
        ],
        exposedHeaders: [
          'X-RateLimit-Limit',
          'X-RateLimit-Remaining',
          'X-RateLimit-Reset',
        ],
        maxAge: 86400,
      },
      hsts: {
        maxAge: 31536000, // 1 year
        includeSubDomains: true,
        preload: true,
      },
      frameOptions: 'DENY',
      contentTypeOptions: true,
      xssProtection: true,
      referrerPolicy: 'strict-origin-when-cross-origin',
      permissionsPolicy: {
        camera: 'none',
        microphone: 'none',
        geolocation: 'none',
        gyroscope: 'none',
        magnetometer: 'none',
        payment: 'none',
        usb: 'none',
      },
    };
  }

  /**
   * Create middleware function
   */
  middleware() {
    return async (c: Context, next: Next) => {
      try {
        // Set security headers
        this.setSecurityHeaders(c);

        await next();
      } catch (error) {
        logger.error('Security headers middleware error', error);
        await next();
      }
    };
  }

  /**
   * Set all security headers
   */
  private setSecurityHeaders(c: Context): void {
    // Content Security Policy
    if (this.config.contentSecurityPolicy) {
      this.setCSPHeader(c, this.config.contentSecurityPolicy);
    }

    // HTTP Strict Transport Security
    if (this.config.hsts) {
      this.setHSTSHeader(c, this.config.hsts);
    }

    // X-Frame-Options
    if (this.config.frameOptions) {
      c.header('X-Frame-Options', this.config.frameOptions);
    }

    // X-Content-Type-Options
    if (this.config.contentTypeOptions) {
      c.header('X-Content-Type-Options', 'nosniff');
    }

    // X-XSS-Protection
    if (this.config.xssProtection) {
      c.header('X-XSS-Protection', '1; mode=block');
    }

    // Referrer Policy
    if (this.config.referrerPolicy) {
      c.header('Referrer-Policy', this.config.referrerPolicy);
    }

    // Permissions Policy
    if (this.config.permissionsPolicy) {
      this.setPermissionsPolicyHeader(c, this.config.permissionsPolicy);
    }

    // Additional security headers
    c.header('X-Download-Options', 'noopen');
    c.header('X-Permitted-Cross-Domain-Policies', 'none');
    c.header('Cross-Origin-Embedder-Policy', 'require-corp');
    c.header('Cross-Origin-Opener-Policy', 'same-origin');
    c.header('Cross-Origin-Resource-Policy', 'cross-origin');

    // Remove server information
    c.header('Server', '');

    // Set reporting endpoints if configured
    if (this.config.reportingEndpoints) {
      this.setReportingEndpoints(c, this.config.reportingEndpoints);
    }
  }

  /**
   * Set Content Security Policy header
   */
  private setCSPHeader(c: Context, csp: CSPConfig): void {
    const directives: string[] = [];

    if (csp.directives) {
      for (const [directive, values] of Object.entries(csp.directives)) {
        if (typeof values === 'boolean' && values) {
          directives.push(directive);
        } else if (Array.isArray(values) && values.length > 0) {
          directives.push(`${directive} ${values.join(' ')}`);
        }
      }
    }

    // Add report directives
    if (csp.reportUri) {
      directives.push(`report-uri ${csp.reportUri}`);
    }

    if (csp.reportTo) {
      directives.push(`report-to ${csp.reportTo}`);
    }

    const cspValue = directives.join('; ');
    const headerName = csp.reportOnly
      ? 'Content-Security-Policy-Report-Only'
      : 'Content-Security-Policy';

    c.header(headerName, cspValue);
  }

  /**
   * Set HSTS header
   */
  private setHSTSHeader(c: Context, hsts: HSTSConfig): void {
    let hstsValue = `max-age=${hsts.maxAge}`;

    if (hsts.includeSubDomains) {
      hstsValue += '; includeSubDomains';
    }

    if (hsts.preload) {
      hstsValue += '; preload';
    }

    c.header('Strict-Transport-Security', hstsValue);
  }

  /**
   * Set Permissions Policy header
   */
  private setPermissionsPolicyHeader(
    c: Context,
    policy: PermissionsPolicyConfig
  ): void {
    const directives: string[] = [];

    for (const [feature, value] of Object.entries(policy)) {
      if (value === '*') {
        directives.push(`${feature}=*`);
      } else if (value === 'self') {
        directives.push(`${feature}=(self)`);
      } else if (value === 'none') {
        directives.push(`${feature}=()`);
      } else if (Array.isArray(value)) {
        const origins = value
          .map(origin => (origin === 'self' ? 'self' : `"${origin}"`))
          .join(' ');
        directives.push(`${feature}=(${origins})`);
      }
    }

    if (directives.length > 0) {
      c.header('Permissions-Policy', directives.join(', '));
    }
  }

  /**
   * Set reporting endpoints
   */
  private setReportingEndpoints(
    c: Context,
    endpoints: ReportingEndpoint[]
  ): void {
    const reportingValue = endpoints
      .map(endpoint => {
        let value = `"${endpoint.name}"="${endpoint.url}"`;
        if (endpoint.includeSubdomains) {
          value += '; include_subdomains';
        }
        return value;
      })
      .join(', ');

    c.header('Report-To', reportingValue);
  }
}

/**
 * CORS middleware with enhanced security
 */
export function createCORSMiddleware(config?: CORSConfig) {
  const corsConfig = {
    origin:
      config?.origin || process.env.CORS_ORIGIN || 'http://localhost:3000',
    credentials: config?.credentials ?? true,
    methods: config?.methods || ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: config?.allowedHeaders || [
      'Content-Type',
      'Authorization',
      'X-API-Key',
      'X-Requested-With',
      'Accept',
      'Origin',
    ],
    exposedHeaders: config?.exposedHeaders || [
      'X-RateLimit-Limit',
      'X-RateLimit-Remaining',
      'X-RateLimit-Reset',
    ],
    maxAge: config?.maxAge || 86400,
  };

  return cors(corsConfig);
}

/**
 * Create CSP middleware for different environments
 */
export function createCSPMiddleware(
  environment: 'development' | 'production' | 'test'
) {
  const baseCSP: CSPConfig = {
    directives: {
      'default-src': ["'self'"],
      'base-uri': ["'self'"],
      'form-action': ["'self'"],
      'frame-ancestors': ["'none'"],
      'object-src': ["'none'"],
      'upgrade-insecure-requests': true,
    },
  };

  switch (environment) {
    case 'development':
      return new SecurityHeaders({
        contentSecurityPolicy: {
          ...baseCSP,
          directives: {
            ...baseCSP.directives,
            'script-src': [
              "'self'",
              "'unsafe-inline'",
              "'unsafe-eval'",
              'localhost:*',
            ],
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", 'data:', 'localhost:*'],
            'connect-src': ["'self'", 'localhost:*', 'ws:', 'wss:'],
          },
          reportOnly: true,
        },
      });

    case 'production':
      return new SecurityHeaders({
        contentSecurityPolicy: {
          ...baseCSP,
          directives: {
            ...baseCSP.directives,
            'script-src': ["'self'"],
            'style-src': ["'self'"],
            'img-src': ["'self'", 'data:', 'https:'],
            'connect-src': ["'self'", 'https:'],
          },
          reportOnly: false,
          reportUri: '/api/csp-report',
        },
      });

    case 'test':
      return new SecurityHeaders({
        contentSecurityPolicy: {
          ...baseCSP,
          directives: {
            ...baseCSP.directives,
            'script-src': ["'self'", "'unsafe-inline'"],
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", 'data:'],
            'connect-src': ["'self'"],
          },
          reportOnly: true,
        },
      });

    default:
      return new SecurityHeaders();
  }
}

/**
 * Security headers for API endpoints
 */
export function createAPISecurityHeaders() {
  return new SecurityHeaders({
    contentSecurityPolicy: {
      directives: {
        'default-src': ["'none'"],
        'frame-ancestors': ["'none'"],
      },
    },
    frameOptions: 'DENY',
    contentTypeOptions: true,
    referrerPolicy: 'no-referrer',
  });
}

/**
 * Presets for common scenarios
 */
export const SecurityHeaderPresets = {
  strict: new SecurityHeaders({
    contentSecurityPolicy: {
      directives: {
        'default-src': ["'none'"],
        'script-src': ["'self'"],
        'style-src': ["'self'"],
        'img-src': ["'self'"],
        'connect-src': ["'self'"],
        'font-src': ["'self'"],
        'object-src': ["'none'"],
        'base-uri': ["'none'"],
        'form-action': ["'none'"],
        'frame-ancestors': ["'none'"],
        'upgrade-insecure-requests': true,
        'block-all-mixed-content': true,
      },
    },
    frameOptions: 'DENY',
    referrerPolicy: 'no-referrer',
  }),

  moderate: new SecurityHeaders({
    contentSecurityPolicy: {
      directives: {
        'default-src': ["'self'"],
        'script-src': ["'self'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", 'data:', 'https:'],
        'connect-src': ["'self'", 'https:'],
        'font-src': ["'self'", 'https:'],
        'object-src': ["'none'"],
        'frame-ancestors': ["'none'"],
        'upgrade-insecure-requests': true,
      },
    },
    frameOptions: 'SAMEORIGIN',
  }),

  relaxed: new SecurityHeaders({
    contentSecurityPolicy: {
      directives: {
        'default-src': ["'self'", 'https:'],
        'script-src': ["'self'", "'unsafe-inline'", 'https:'],
        'style-src': ["'self'", "'unsafe-inline'", 'https:'],
        'img-src': ["'self'", 'data:', 'https:', 'http:'],
        'connect-src': ["'self'", 'https:', 'wss:'],
        'font-src': ["'self'", 'https:'],
        'frame-ancestors': ["'self'"],
      },
    },
  }),
};

/**
 * CSP violation report handler
 */
export function handleCSPReport() {
  return async (c: Context) => {
    try {
      const report = await c.req.json();

      logger.warn('CSP violation reported', {
        report,
        userAgent: c.req.header('user-agent'),
        ip: c.req.header('x-forwarded-for') || c.env?.remoteAddr,
      });

      return c.json({ status: 'received' }, 204);
    } catch (error) {
      logger.error('Error handling CSP report', error);
      return c.json({ error: 'Invalid report' }, 400);
    }
  };
}

export default SecurityHeaders;
