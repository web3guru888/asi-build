import crypto from 'crypto';
import { Context, Next } from 'hono';
import { logger } from '../logging/logger.js';

export interface SigningConfig {
  algorithm: 'HMAC-SHA256' | 'HMAC-SHA512' | 'RSA-SHA256' | 'ECDSA-SHA256';
  secret?: string;
  privateKey?: string;
  publicKey?: string;
  timestampTolerance: number; // seconds
  nonceWindow: number; // seconds
  requiredHeaders?: string[];
}

export interface SignatureComponents {
  timestamp: number;
  nonce: string;
  method: string;
  path: string;
  query: string;
  headers: Record<string, string>;
  bodyHash: string;
}

export interface SignatureResult {
  signature: string;
  timestamp: number;
  nonce: string;
  algorithm: string;
}

export interface VerificationResult {
  isValid: boolean;
  reason?: string;
  components?: SignatureComponents;
}

/**
 * Request signing and verification utility
 */
export class RequestSigner {
  private config: SigningConfig;
  private usedNonces: Map<string, number> = new Map();

  constructor(config: SigningConfig) {
    this.config = {
      timestampTolerance: 300, // 5 minutes default
      nonceWindow: 300, // 5 minutes default
      ...config
    };

    this.validateConfig();
    this.startNonceCleanup();
  }

  /**
   * Validate configuration
   */
  private validateConfig(): void {
    if (this.config.algorithm.startsWith('HMAC') && !this.config.secret) {
      throw new Error('HMAC algorithms require a secret key');
    }

    if (this.config.algorithm.startsWith('RSA') && (!this.config.privateKey || !this.config.publicKey)) {
      throw new Error('RSA algorithms require both private and public keys');
    }

    if (this.config.algorithm.startsWith('ECDSA') && (!this.config.privateKey || !this.config.publicKey)) {
      throw new Error('ECDSA algorithms require both private and public keys');
    }
  }

  /**
   * Sign a request
   */
  async signRequest(
    method: string,
    path: string,
    query: string = '',
    headers: Record<string, string> = {},
    body: string = ''
  ): Promise<SignatureResult> {
    try {
      const timestamp = Math.floor(Date.now() / 1000);
      const nonce = this.generateNonce();

      const components: SignatureComponents = {
        timestamp,
        nonce,
        method: method.toUpperCase(),
        path,
        query,
        headers: this.normalizeHeaders(headers),
        bodyHash: this.hashBody(body)
      };

      const stringToSign = this.createStringToSign(components);
      const signature = this.sign(stringToSign);

      logger.debug('Request signed', {
        method,
        path,
        timestamp,
        nonce,
        algorithm: this.config.algorithm
      });

      return {
        signature,
        timestamp,
        nonce,
        algorithm: this.config.algorithm
      };
    } catch (error) {
      logger.error('Request signing failed', error);
      throw new Error('Request signing failed');
    }
  }

  /**
   * Verify a signed request
   */
  async verifyRequest(
    signature: string,
    timestamp: number,
    nonce: string,
    method: string,
    path: string,
    query: string = '',
    headers: Record<string, string> = {},
    body: string = ''
  ): Promise<VerificationResult> {
    try {
      // Check timestamp
      const now = Math.floor(Date.now() / 1000);
      if (Math.abs(now - timestamp) > this.config.timestampTolerance) {
        return {
          isValid: false,
          reason: `Request timestamp is outside tolerance window (${this.config.timestampTolerance}s)`
        };
      }

      // Check nonce replay
      if (this.isNonceUsed(nonce, timestamp)) {
        return {
          isValid: false,
          reason: 'Nonce has already been used (replay attack detected)'
        };
      }

      // Reconstruct signature components
      const components: SignatureComponents = {
        timestamp,
        nonce,
        method: method.toUpperCase(),
        path,
        query,
        headers: this.normalizeHeaders(headers),
        bodyHash: this.hashBody(body)
      };

      // Check required headers
      if (this.config.requiredHeaders) {
        for (const requiredHeader of this.config.requiredHeaders) {
          if (!components.headers[requiredHeader.toLowerCase()]) {
            return {
              isValid: false,
              reason: `Required header missing: ${requiredHeader}`
            };
          }
        }
      }

      // Verify signature
      const stringToSign = this.createStringToSign(components);
      const isValid = this.verify(stringToSign, signature);

      if (isValid) {
        // Mark nonce as used
        this.markNonceUsed(nonce, timestamp);
        
        logger.debug('Request signature verified', {
          method,
          path,
          timestamp,
          nonce
        });
      } else {
        logger.warn('Request signature verification failed', {
          method,
          path,
          timestamp,
          nonce,
          reason: 'Invalid signature'
        });
      }

      return {
        isValid,
        reason: isValid ? undefined : 'Invalid signature',
        components
      };
    } catch (error) {
      logger.error('Request verification failed', error);
      return {
        isValid: false,
        reason: 'Verification error'
      };
    }
  }

  /**
   * Create string to sign from components
   */
  private createStringToSign(components: SignatureComponents): string {
    const parts = [
      components.method,
      components.path,
      components.query,
      components.timestamp.toString(),
      components.nonce,
      components.bodyHash
    ];

    // Add normalized headers
    const headerNames = Object.keys(components.headers).sort();
    for (const headerName of headerNames) {
      parts.push(`${headerName}:${components.headers[headerName]}`);
    }

    return parts.join('\n');
  }

  /**
   * Sign string using configured algorithm
   */
  private sign(stringToSign: string): string {
    switch (this.config.algorithm) {
      case 'HMAC-SHA256':
        return crypto
          .createHmac('sha256', this.config.secret!)
          .update(stringToSign)
          .digest('base64');

      case 'HMAC-SHA512':
        return crypto
          .createHmac('sha512', this.config.secret!)
          .update(stringToSign)
          .digest('base64');

      case 'RSA-SHA256':
        return crypto
          .sign('sha256', Buffer.from(stringToSign))
          .update(this.config.privateKey!)
          .digest('base64');

      case 'ECDSA-SHA256':
        return crypto
          .sign('sha256', Buffer.from(stringToSign))
          .update(this.config.privateKey!)
          .digest('base64');

      default:
        throw new Error(`Unsupported signing algorithm: ${this.config.algorithm}`);
    }
  }

  /**
   * Verify signature using configured algorithm
   */
  private verify(stringToSign: string, signature: string): boolean {
    try {
      switch (this.config.algorithm) {
        case 'HMAC-SHA256':
          const expectedHmac256 = crypto
            .createHmac('sha256', this.config.secret!)
            .update(stringToSign)
            .digest('base64');
          return crypto.timingSafeEqual(
            Buffer.from(signature),
            Buffer.from(expectedHmac256)
          );

        case 'HMAC-SHA512':
          const expectedHmac512 = crypto
            .createHmac('sha512', this.config.secret!)
            .update(stringToSign)
            .digest('base64');
          return crypto.timingSafeEqual(
            Buffer.from(signature),
            Buffer.from(expectedHmac512)
          );

        case 'RSA-SHA256':
          return crypto.verify(
            'sha256',
            Buffer.from(stringToSign),
            this.config.publicKey!,
            Buffer.from(signature, 'base64')
          );

        case 'ECDSA-SHA256':
          return crypto.verify(
            'sha256',
            Buffer.from(stringToSign),
            this.config.publicKey!,
            Buffer.from(signature, 'base64')
          );

        default:
          return false;
      }
    } catch (error) {
      logger.error('Signature verification error', error);
      return false;
    }
  }

  /**
   * Generate cryptographically secure nonce
   */
  private generateNonce(): string {
    return crypto.randomBytes(16).toString('hex');
  }

  /**
   * Hash request body
   */
  private hashBody(body: string): string {
    return crypto.createHash('sha256').update(body).digest('hex');
  }

  /**
   * Normalize headers for consistent signing
   */
  private normalizeHeaders(headers: Record<string, string>): Record<string, string> {
    const normalized: Record<string, string> = {};
    
    for (const [key, value] of Object.entries(headers)) {
      const normalizedKey = key.toLowerCase().trim();
      const normalizedValue = value.trim().replace(/\s+/g, ' ');
      
      // Skip certain headers that can change in transit
      if (!this.isSkippedHeader(normalizedKey)) {
        normalized[normalizedKey] = normalizedValue;
      }
    }
    
    return normalized;
  }

  /**
   * Check if header should be skipped in signing
   */
  private isSkippedHeader(headerName: string): boolean {
    const skippedHeaders = [
      'authorization',
      'content-length',
      'user-agent',
      'accept-encoding',
      'connection',
      'cache-control',
      'pragma'
    ];
    
    return skippedHeaders.includes(headerName);
  }

  /**
   * Check if nonce has been used
   */
  private isNonceUsed(nonce: string, timestamp: number): boolean {
    const usedTimestamp = this.usedNonces.get(nonce);
    if (!usedTimestamp) {
      return false;
    }

    // Allow reuse if outside the nonce window
    return Math.abs(timestamp - usedTimestamp) <= this.config.nonceWindow;
  }

  /**
   * Mark nonce as used
   */
  private markNonceUsed(nonce: string, timestamp: number): void {
    this.usedNonces.set(nonce, timestamp);
  }

  /**
   * Start nonce cleanup job
   */
  private startNonceCleanup(): void {
    setInterval(() => {
      this.cleanupUsedNonces();
    }, 60 * 1000); // Cleanup every minute
  }

  /**
   * Cleanup expired nonces
   */
  private cleanupUsedNonces(): void {
    const now = Math.floor(Date.now() / 1000);
    const cutoff = now - this.config.nonceWindow * 2; // Keep some buffer

    let cleaned = 0;
    for (const [nonce, timestamp] of this.usedNonces.entries()) {
      if (timestamp < cutoff) {
        this.usedNonces.delete(nonce);
        cleaned++;
      }
    }

    if (cleaned > 0) {
      logger.debug('Cleaned up expired nonces', { 
        cleaned, 
        remaining: this.usedNonces.size 
      });
    }
  }
}

/**
 * Request signing middleware
 */
export function createSigningMiddleware(config: SigningConfig) {
  const signer = new RequestSigner(config);

  return async (c: Context, next: Next) => {
    try {
      // Extract signature components from headers
      const signature = c.req.header('x-signature');
      const timestamp = parseInt(c.req.header('x-timestamp') || '0');
      const nonce = c.req.header('x-nonce');
      const algorithm = c.req.header('x-signature-algorithm');

      if (!signature || !timestamp || !nonce) {
        return c.json({
          error: 'Missing signature headers',
          required: ['x-signature', 'x-timestamp', 'x-nonce']
        }, 401);
      }

      if (algorithm && algorithm !== config.algorithm) {
        return c.json({
          error: 'Algorithm mismatch',
          expected: config.algorithm,
          received: algorithm
        }, 401);
      }

      // Get request components
      const method = c.req.method;
      const path = c.req.path;
      const query = c.req.url.split('?')[1] || '';
      const headers = Object.fromEntries(
        Object.entries(c.req.header()).filter(([key]) => 
          !key.startsWith('x-signature') && !key.startsWith('x-timestamp') && !key.startsWith('x-nonce')
        )
      );

      // Get body
      let body = '';
      if (['POST', 'PUT', 'PATCH'].includes(method)) {
        body = await c.req.text();
      }

      // Verify signature
      const result = await signer.verifyRequest(
        signature,
        timestamp,
        nonce,
        method,
        path,
        query,
        headers,
        body
      );

      if (!result.isValid) {
        logger.warn('Request signature verification failed', {
          method,
          path,
          reason: result.reason,
          timestamp,
          nonce
        });

        return c.json({
          error: 'Invalid request signature',
          reason: result.reason
        }, 401);
      }

      // Store verification result for use in handlers
      c.set('signatureVerified', true);
      c.set('signatureComponents', result.components);

      await next();
    } catch (error) {
      logger.error('Signature verification middleware error', error);
      return c.json({ error: 'Signature verification failed' }, 500);
    }
  };
}

/**
 * Client helper for signing requests
 */
export class SignedRequestClient {
  private signer: RequestSigner;
  private baseURL: string;

  constructor(config: SigningConfig, baseURL: string) {
    this.signer = new RequestSigner(config);
    this.baseURL = baseURL.replace(/\/$/, '');
  }

  /**
   * Make signed HTTP request
   */
  async makeRequest(
    method: string,
    path: string,
    options: {
      query?: Record<string, string>;
      headers?: Record<string, string>;
      body?: any;
    } = {}
  ): Promise<Response> {
    try {
      const url = new URL(path, this.baseURL);
      
      // Add query parameters
      if (options.query) {
        for (const [key, value] of Object.entries(options.query)) {
          url.searchParams.set(key, value);
        }
      }

      const headers = { ...options.headers };
      let body = '';

      // Serialize body
      if (options.body && ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase())) {
        if (typeof options.body === 'object') {
          body = JSON.stringify(options.body);
          headers['Content-Type'] = 'application/json';
        } else {
          body = String(options.body);
        }
      }

      // Sign request
      const signatureResult = await this.signer.signRequest(
        method,
        url.pathname,
        url.search.substring(1),
        headers,
        body
      );

      // Add signature headers
      headers['X-Signature'] = signatureResult.signature;
      headers['X-Timestamp'] = signatureResult.timestamp.toString();
      headers['X-Nonce'] = signatureResult.nonce;
      headers['X-Signature-Algorithm'] = signatureResult.algorithm;

      // Make request
      return fetch(url.toString(), {
        method: method.toUpperCase(),
        headers,
        body: body || undefined
      });
    } catch (error) {
      logger.error('Signed request failed', error);
      throw error;
    }
  }
}

/**
 * Generate key pair for asymmetric algorithms
 */
export function generateKeyPair(algorithm: 'RSA' | 'ECDSA'): { privateKey: string; publicKey: string } {
  let keyPair: crypto.KeyPairSyncResult<string, string>;

  switch (algorithm) {
    case 'RSA':
      keyPair = crypto.generateKeyPairSync('rsa', {
        modulusLength: 2048,
        publicKeyEncoding: {
          type: 'spki',
          format: 'pem'
        },
        privateKeyEncoding: {
          type: 'pkcs8',
          format: 'pem'
        }
      });
      break;

    case 'ECDSA':
      keyPair = crypto.generateKeyPairSync('ec', {
        namedCurve: 'secp256k1',
        publicKeyEncoding: {
          type: 'spki',
          format: 'pem'
        },
        privateKeyEncoding: {
          type: 'pkcs8',
          format: 'pem'
        }
      });
      break;

    default:
      throw new Error(`Unsupported algorithm: ${algorithm}`);
  }

  return {
    privateKey: keyPair.privateKey,
    publicKey: keyPair.publicKey
  };
}

/**
 * Generate HMAC secret
 */
export function generateHMACSecret(length: number = 64): string {
  return crypto.randomBytes(length).toString('base64');
}

export default RequestSigner;