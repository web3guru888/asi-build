#!/usr/bin/env node

/**
 * API Documentation Validation Script
 * 
 * Compares documented API endpoints in API.md with actual implementation
 * in routes.ts to detect documentation drift and mismatches.
 * 
 * Usage: npm run validate:api-docs
 */

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');

// Console colors
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m'
};

class APIDocValidator {
  constructor() {
    this.errors = [];
    this.warnings = [];
    this.documentedEndpoints = new Map();
    this.implementedEndpoints = new Map();
  }

  log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
  }

  error(message) {
    this.errors.push(message);
    this.log(`❌ ERROR: ${message}`, 'red');
  }

  warning(message) {
    this.warnings.push(message);
    this.log(`⚠️  WARNING: ${message}`, 'yellow');
  }

  success(message) {
    this.log(`✅ ${message}`, 'green');
  }

  info(message) {
    this.log(`ℹ️  ${message}`, 'blue');
  }

  async readFile(filePath) {
    try {
      return await fs.readFile(filePath, 'utf-8');
    } catch (error) {
      this.error(`Failed to read ${filePath}: ${error.message}`);
      return null;
    }
  }

  /**
   * Parse API.md to extract documented endpoints
   */
  parseDocumentedEndpoints(content) {
    const endpointPattern = /#### (GET|POST|PUT|DELETE|PATCH) ([^\s]+)/g;
    let match;

    while ((match = endpointPattern.exec(content)) !== null) {
      const [, method, path] = match;
      const key = `${method.toUpperCase()} ${path}`;
      
      // Extract section context for better error reporting
      const sectionStart = content.lastIndexOf('###', match.index);
      const sectionEnd = content.indexOf('\n###', sectionStart + 1);
      const sectionContent = content.substring(sectionStart, sectionEnd > 0 ? sectionEnd : match.index + 200);
      const sectionMatch = sectionContent.match(/### (.+)/);
      const section = sectionMatch ? sectionMatch[1] : 'Unknown Section';

      this.documentedEndpoints.set(key, {
        method: method.toUpperCase(),
        path,
        section,
        line: content.substring(0, match.index).split('\n').length
      });
    }

    this.info(`Found ${this.documentedEndpoints.size} documented endpoints in API.md`);
  }

  /**
   * Parse routes.ts to extract implemented endpoints
   */
  parseImplementedEndpoints(content) {
    const patterns = [
      // Standard route patterns: app.get('/path', handler)
      /app\.(get|post|put|delete|patch)\s*\(\s*['"`]([^'"`]+)['"`]/g,
      // Destructured patterns: const { get, post } = app; get('/path', handler)
      /(get|post|put|delete|patch)\s*\(\s*['"`]([^'"`]+)['"`]/g
    ];

    patterns.forEach(pattern => {
      let match;
      while ((match = pattern.exec(content)) !== null) {
        const [, method, path] = match;
        const key = `${method.toUpperCase()} ${path}`;
        
        this.implementedEndpoints.set(key, {
          method: method.toUpperCase(),
          path,
          line: content.substring(0, match.index).split('\n').length
        });
      }
    });

    this.info(`Found ${this.implementedEndpoints.size} implemented endpoints in routes.ts`);
  }

  /**
   * Normalize paths for comparison (handle parameters and wildcards)
   */
  normalizePath(path) {
    return path
      .replace(/:([^/]+)/g, ':param')  // :id -> :param
      .replace(/\*/g, ':param')        // * -> :param
      .replace(/\/+/g, '/')            // multiple slashes -> single slash
      .replace(/\/$/, '');             // remove trailing slash
  }

  /**
   * Check for missing endpoints in documentation
   */
  checkMissingInDocs() {
    this.info('\n📋 Checking for undocumented endpoints...');
    let missing = 0;

    for (const [key, impl] of this.implementedEndpoints) {
      const normalizedPath = this.normalizePath(impl.path);
      const normalizedKey = `${impl.method} ${normalizedPath}`;
      
      let found = false;
      for (const [docKey] of this.documentedEndpoints) {
        if (this.pathsMatch(docKey, normalizedKey)) {
          found = true;
          break;
        }
      }

      if (!found) {
        // Skip some internal/utility endpoints
        if (this.shouldSkipEndpoint(impl.path)) {
          continue;
        }

        this.warning(`Endpoint ${key} is implemented but not documented`);
        missing++;
      }
    }

    if (missing === 0) {
      this.success('All implemented endpoints are documented');
    } else {
      this.error(`${missing} endpoints are missing from documentation`);
    }
  }

  /**
   * Check for documented endpoints that aren't implemented
   */
  checkMissingInCode() {
    this.info('\n🔧 Checking for documented but unimplemented endpoints...');
    let missing = 0;

    for (const [key, doc] of this.documentedEndpoints) {
      const normalizedPath = this.normalizePath(doc.path);
      const normalizedKey = `${doc.method} ${normalizedPath}`;
      
      let found = false;
      for (const [implKey] of this.implementedEndpoints) {
        if (this.pathsMatch(implKey, normalizedKey)) {
          found = true;
          break;
        }
      }

      if (!found) {
        this.warning(`Documented endpoint ${key} is not implemented (Section: ${doc.section}, Line: ${doc.line})`);
        missing++;
      }
    }

    if (missing === 0) {
      this.success('All documented endpoints are implemented');
    } else {
      this.error(`${missing} documented endpoints are not implemented`);
    }
  }

  /**
   * Check if two endpoint paths match (accounting for parameters)
   */
  pathsMatch(path1, path2) {
    const normalize = (p) => p.replace(/:param/g, ':x').replace(/\/+/g, '/').replace(/\/$/, '');
    return normalize(path1) === normalize(path2);
  }

  /**
   * Check if an endpoint should be skipped in validation
   */
  shouldSkipEndpoint(path) {
    const skipPatterns = [
      '/static/*',      // Static file serving
      '/health',        // Simple health check (not in API docs)
      '/models',        // Alias endpoint
    ];
    
    return skipPatterns.some(pattern => {
      if (pattern.includes('*')) {
        const regex = new RegExp(pattern.replace('*', '.*'));
        return regex.test(path);
      }
      return path === pattern;
    });
  }

  /**
   * Validate HTTP method consistency
   */
  validateMethodConsistency() {
    this.info('\n🔍 Validating HTTP method usage...');
    
    const methodGuidelines = {
      'GET': 'Should be used for retrieving data without side effects',
      'POST': 'Should be used for creating new resources or complex operations',
      'PUT': 'Should be used for updating entire resources',
      'PATCH': 'Should be used for partial updates',
      'DELETE': 'Should be used for removing resources'
    };

    // Check for potential method misuse
    const potentialIssues = [
      { pattern: /GET.*\/(create|add|insert|new)/i, message: 'GET endpoint appears to be creating data' },
      { pattern: /POST.*\/(get|list|fetch|retrieve)/i, message: 'POST endpoint appears to be retrieving data' },
      { pattern: /DELETE.*\/(get|list|fetch|retrieve)/i, message: 'DELETE endpoint appears to be retrieving data' }
    ];

    let issues = 0;
    for (const [key, endpoint] of this.implementedEndpoints) {
      for (const { pattern, message } of potentialIssues) {
        if (pattern.test(key)) {
          this.warning(`${key}: ${message}`);
          issues++;
        }
      }
    }

    if (issues === 0) {
      this.success('HTTP methods appear to be used correctly');
    } else {
      this.warning(`Found ${issues} potential HTTP method usage issues`);
    }
  }

  /**
   * Check for missing request/response examples
   */
  async validateExamples(apiContent) {
    this.info('\n📝 Checking for missing request/response examples...');
    
    let missingExamples = 0;
    
    for (const [key, doc] of this.documentedEndpoints) {
      // Skip GET endpoints without request bodies
      if (doc.method === 'GET') continue;

      // Look for request example after the endpoint definition
      const endpointIndex = apiContent.indexOf(`#### ${doc.method} ${doc.path}`);
      if (endpointIndex === -1) continue;

      const nextEndpointIndex = apiContent.indexOf('####', endpointIndex + 1);
      const sectionContent = nextEndpointIndex > 0 
        ? apiContent.substring(endpointIndex, nextEndpointIndex)
        : apiContent.substring(endpointIndex);

      const hasRequestExample = sectionContent.includes('**Request:**') || sectionContent.includes('```json');
      const hasResponseExample = sectionContent.includes('**Response:**');

      if (!hasRequestExample && ['POST', 'PUT', 'PATCH'].includes(doc.method)) {
        this.warning(`${key}: Missing request example`);
        missingExamples++;
      }

      if (!hasResponseExample) {
        this.warning(`${key}: Missing response example`);
        missingExamples++;
      }
    }

    if (missingExamples === 0) {
      this.success('All endpoints have appropriate examples');
    } else {
      this.warning(`${missingExamples} endpoints are missing request/response examples`);
    }
  }

  /**
   * Generate validation report
   */
  generateReport() {
    const timestamp = new Date().toISOString();
    const report = {
      timestamp,
      summary: {
        documentedEndpoints: this.documentedEndpoints.size,
        implementedEndpoints: this.implementedEndpoints.size,
        errors: this.errors.length,
        warnings: this.warnings.length
      },
      errors: this.errors,
      warnings: this.warnings,
      endpoints: {
        documented: Array.from(this.documentedEndpoints.entries()).map(([key, data]) => ({
          endpoint: key,
          ...data
        })),
        implemented: Array.from(this.implementedEndpoints.entries()).map(([key, data]) => ({
          endpoint: key,
          ...data
        }))
      }
    };

    return report;
  }

  /**
   * Save report to file
   */
  async saveReport(report) {
    const reportPath = path.join(PROJECT_ROOT, 'docs', 'validation-reports');
    await fs.mkdir(reportPath, { recursive: true });
    
    const filename = `api-validation-${Date.now()}.json`;
    const filePath = path.join(reportPath, filename);
    
    await fs.writeFile(filePath, JSON.stringify(report, null, 2));
    this.info(`Validation report saved to: ${filePath}`);
  }

  /**
   * Main validation runner
   */
  async validate() {
    this.log('\n🚀 Starting API Documentation Validation\n', 'cyan');

    // Read source files
    const apiContent = await this.readFile(path.join(PROJECT_ROOT, 'API.md'));
    const routesContent = await this.readFile(path.join(PROJECT_ROOT, 'src', 'server', 'routes.ts'));

    if (!apiContent || !routesContent) {
      this.error('Failed to read required files. Aborting validation.');
      return false;
    }

    // Parse endpoints
    this.parseDocumentedEndpoints(apiContent);
    this.parseImplementedEndpoints(routesContent);

    // Run validation checks
    this.checkMissingInDocs();
    this.checkMissingInCode();
    this.validateMethodConsistency();
    await this.validateExamples(apiContent);

    // Generate and save report
    const report = this.generateReport();
    await this.saveReport(report);

    // Print summary
    this.log('\n📊 VALIDATION SUMMARY', 'magenta');
    this.log('='.repeat(50), 'magenta');
    this.log(`Documented Endpoints: ${this.documentedEndpoints.size}`, 'cyan');
    this.log(`Implemented Endpoints: ${this.implementedEndpoints.size}`, 'cyan');
    this.log(`Errors: ${this.errors.length}`, this.errors.length > 0 ? 'red' : 'green');
    this.log(`Warnings: ${this.warnings.length}`, this.warnings.length > 0 ? 'yellow' : 'green');

    const success = this.errors.length === 0;
    if (success) {
      this.log('\n🎉 API documentation validation passed!', 'green');
    } else {
      this.log('\n💥 API documentation validation failed!', 'red');
      this.log('Please fix the errors above and run validation again.', 'red');
    }

    return success;
  }
}

// Run validation if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const validator = new APIDocValidator();
  validator.validate()
    .then(success => {
      process.exit(success ? 0 : 1);
    })
    .catch(error => {
      console.error('Validation failed with error:', error);
      process.exit(1);
    });
}

export default APIDocValidator;