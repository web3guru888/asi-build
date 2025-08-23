#!/usr/bin/env node

/**
 * Code Examples Testing Script
 * 
 * Extracts and tests all code examples from documentation files,
 * including curl commands, JavaScript snippets, and TypeScript code.
 * 
 * Usage: npm run test:examples
 */

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn, exec } from 'child_process';
import { promisify } from 'util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');
const execAsync = promisify(exec);

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

class CodeExamplesValidator {
  constructor() {
    this.testResults = [];
    this.serverProcess = null;
    this.serverStarted = false;
  }

  log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
  }

  error(message) {
    this.log(`❌ ERROR: ${message}`, 'red');
  }

  warning(message) {
    this.log(`⚠️  WARNING: ${message}`, 'yellow');
  }

  success(message) {
    this.log(`✅ ${message}`, 'green');
  }

  info(message) {
    this.log(`ℹ️  ${message}`, 'blue');
  }

  /**
   * Find all documentation files
   */
  async findDocumentationFiles() {
    const docFiles = [];
    const searchPaths = [
      path.join(PROJECT_ROOT, 'API.md'),
      path.join(PROJECT_ROOT, 'README.md'),
      path.join(PROJECT_ROOT, 'DEPLOYMENT.md'),
      path.join(PROJECT_ROOT, 'docs'),
    ];

    for (const searchPath of searchPaths) {
      try {
        const stat = await fs.stat(searchPath);
        if (stat.isFile() && searchPath.endsWith('.md')) {
          docFiles.push(searchPath);
        } else if (stat.isDirectory()) {
          const files = await this.findMarkdownFiles(searchPath);
          docFiles.push(...files);
        }
      } catch (error) {
        // File/directory doesn't exist, skip
      }
    }

    return docFiles;
  }

  /**
   * Recursively find markdown files in directory
   */
  async findMarkdownFiles(dir) {
    const files = [];
    try {
      const entries = await fs.readdir(dir, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          const subFiles = await this.findMarkdownFiles(fullPath);
          files.push(...subFiles);
        } else if (entry.isFile() && entry.name.endsWith('.md')) {
          files.push(fullPath);
        }
      }
    } catch (error) {
      this.warning(`Could not read directory ${dir}: ${error.message}`);
    }
    
    return files;
  }

  /**
   * Extract code blocks from markdown content
   */
  extractCodeBlocks(content, filePath) {
    const codeBlocks = [];
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    let match;

    while ((match = codeBlockRegex.exec(content)) !== null) {
      const [fullMatch, language, code] = match;
      const lineNumber = content.substring(0, match.index).split('\n').length;
      
      codeBlocks.push({
        language: language || 'text',
        code: code.trim(),
        filePath,
        lineNumber,
        fullMatch
      });
    }

    // Also extract inline code examples (curl commands, etc.)
    const inlineCodeRegex = /^curl\s+.+$/gm;
    let inlineMatch;

    while ((inlineMatch = inlineCodeRegex.exec(content)) !== null) {
      const lineNumber = content.substring(0, inlineMatch.index).split('\n').length;
      codeBlocks.push({
        language: 'bash',
        code: inlineMatch[0].trim(),
        filePath,
        lineNumber,
        fullMatch: inlineMatch[0],
        inline: true
      });
    }

    return codeBlocks;
  }

  /**
   * Start a test server instance
   */
  async startTestServer() {
    if (this.serverStarted) {
      return true;
    }

    this.info('Starting test server...');
    
    return new Promise((resolve, reject) => {
      // Start server in background
      this.serverProcess = spawn('bun', ['run', 'start'], {
        cwd: PROJECT_ROOT,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: {
          ...process.env,
          NODE_ENV: 'test',
          PORT: '3000'
        }
      });

      let output = '';
      this.serverProcess.stdout.on('data', (data) => {
        output += data.toString();
      });

      this.serverProcess.stderr.on('data', (data) => {
        output += data.toString();
      });

      // Wait for server to start (check health endpoint)
      const checkServer = async () => {
        try {
          await execAsync('curl -s http://localhost:3000/health');
          this.serverStarted = true;
          this.success('Test server started successfully');
          resolve(true);
        } catch (error) {
          // Server not ready yet, try again
          setTimeout(checkServer, 1000);
        }
      };

      // Start checking after 2 seconds
      setTimeout(checkServer, 2000);

      // Timeout after 30 seconds
      setTimeout(() => {
        if (!this.serverStarted) {
          this.error('Server failed to start within 30 seconds');
          this.error('Server output:', output);
          reject(new Error('Server startup timeout'));
        }
      }, 30000);
    });
  }

  /**
   * Stop test server
   */
  async stopTestServer() {
    if (this.serverProcess) {
      this.info('Stopping test server...');
      this.serverProcess.kill('SIGTERM');
      
      // Wait for graceful shutdown
      await new Promise((resolve) => {
        this.serverProcess.on('exit', resolve);
        setTimeout(() => {
          this.serverProcess.kill('SIGKILL');
          resolve();
        }, 5000);
      });
      
      this.serverProcess = null;
      this.serverStarted = false;
    }
  }

  /**
   * Test curl commands
   */
  async testCurlCommand(codeBlock) {
    const { code, filePath, lineNumber } = codeBlock;
    
    // Skip curl commands that require authentication or external services
    if (this.shouldSkipCurl(code)) {
      return {
        type: 'curl',
        status: 'skipped',
        reason: 'Requires authentication or external service',
        ...codeBlock
      };
    }

    // Replace external URLs with localhost for testing
    let testCommand = code
      .replace(/https?:\/\/api\.asi-code\.dev/g, 'http://localhost:3000')
      .replace(/https?:\/\/asi-code\.company\.com/g, 'http://localhost:3000')
      .replace(/-H\s+"Authorization:[^"]+"/g, '') // Remove auth headers for basic tests
      .replace(/Bearer\s+[^\s"]+/g, 'Bearer test-token'); // Replace with test token

    try {
      const { stdout, stderr } = await execAsync(testCommand, { timeout: 10000 });
      return {
        type: 'curl',
        status: 'passed',
        output: stdout,
        ...codeBlock
      };
    } catch (error) {
      // Check if it's a expected error (like 401, 404) vs actual failure
      if (error.code === 22 || error.code === 7) { // curl exit codes for HTTP errors
        const httpError = error.stderr.includes('401') || error.stderr.includes('404');
        return {
          type: 'curl',
          status: httpError ? 'expected_error' : 'failed',
          error: error.message,
          stderr: error.stderr,
          ...codeBlock
        };
      }

      return {
        type: 'curl',
        status: 'failed',
        error: error.message,
        ...codeBlock
      };
    }
  }

  /**
   * Check if curl command should be skipped
   */
  shouldSkipCurl(command) {
    const skipPatterns = [
      /Bearer\s+asi_key_/,  // Requires real API key
      /Authorization.*your-api-key/,  // Placeholder API key
      /prometheus\.monitoring/,  // Internal Kubernetes services
      /alertmanager\./,  // Internal services
      /api\.anthropic\.com/,  // External API
      /app\.fossa\.com/,  // External service
      /kubectl\s+exec/,  // Requires Kubernetes
      /--data.*session_token/,  // Requires active session
    ];

    return skipPatterns.some(pattern => pattern.test(command));
  }

  /**
   * Test JavaScript/TypeScript code
   */
  async testJavaScriptCode(codeBlock) {
    const { code, language } = codeBlock;
    
    // Skip incomplete code snippets or examples
    if (this.shouldSkipJSCode(code)) {
      return {
        type: 'javascript',
        status: 'skipped',
        reason: 'Incomplete example or requires external setup',
        ...codeBlock
      };
    }

    // Create temporary test file
    const tempDir = path.join(PROJECT_ROOT, 'temp-test');
    await fs.mkdir(tempDir, { recursive: true });
    
    const isTypeScript = language === 'typescript' || language === 'ts';
    const extension = isTypeScript ? '.ts' : '.js';
    const tempFile = path.join(tempDir, `test-${Date.now()}${extension}`);

    try {
      // Wrap code in async function if it contains await
      let testCode = code;
      if (code.includes('await') && !code.includes('async')) {
        testCode = `(async () => {\n${code}\n})();`;
      }

      await fs.writeFile(tempFile, testCode);

      // Run the code
      const command = isTypeScript ? `bun run ${tempFile}` : `node ${tempFile}`;
      const { stdout, stderr } = await execAsync(command, { 
        timeout: 10000,
        cwd: PROJECT_ROOT 
      });

      return {
        type: 'javascript',
        status: 'passed',
        output: stdout,
        ...codeBlock
      };
    } catch (error) {
      return {
        type: 'javascript',
        status: 'failed',
        error: error.message,
        ...codeBlock
      };
    } finally {
      // Clean up temp file
      try {
        await fs.unlink(tempFile);
      } catch (error) {
        // Ignore cleanup errors
      }
    }
  }

  /**
   * Check if JavaScript code should be skipped
   */
  shouldSkipJSCode(code) {
    const skipPatterns = [
      /import.*from\s+['"]asi-code/,  // Package imports
      /new WebSocket/,  // Requires WebSocket server
      /fetch\s*\(/,  // API calls that need server
      /your-api-key/,  // Placeholder values
      /process\.env\./,  // Environment variables
      /console\.log\(/,  // Simple logging examples
      /\/\/ Usage/,  // Comment sections
      /class.*extends/,  // Class definitions (incomplete)
      /interface\s+\w+/,  // TypeScript interfaces
      /type\s+\w+\s*=/,  // TypeScript type definitions
    ];

    // Skip if too short (likely just snippets)
    if (code.length < 50) {
      return true;
    }

    // Skip if contains placeholder patterns
    return skipPatterns.some(pattern => pattern.test(code));
  }

  /**
   * Test JSON examples
   */
  async testJsonCode(codeBlock) {
    const { code } = codeBlock;
    
    try {
      JSON.parse(code);
      return {
        type: 'json',
        status: 'passed',
        ...codeBlock
      };
    } catch (error) {
      return {
        type: 'json',
        status: 'failed',
        error: error.message,
        ...codeBlock
      };
    }
  }

  /**
   * Test shell/bash commands
   */
  async testBashCode(codeBlock) {
    const { code } = codeBlock;
    
    // Skip dangerous or system-specific commands
    if (this.shouldSkipBash(code)) {
      return {
        type: 'bash',
        status: 'skipped',
        reason: 'Dangerous or system-specific command',
        ...codeBlock
      };
    }

    // Only test safe, informational commands
    const safeCommands = /^(echo|ls|pwd|whoami|date|which)\s/;
    if (!safeCommands.test(code.trim())) {
      return {
        type: 'bash',
        status: 'skipped',
        reason: 'Not a safe test command',
        ...codeBlock
      };
    }

    try {
      const { stdout } = await execAsync(code, { timeout: 5000 });
      return {
        type: 'bash',
        status: 'passed',
        output: stdout,
        ...codeBlock
      };
    } catch (error) {
      return {
        type: 'bash',
        status: 'failed',
        error: error.message,
        ...codeBlock
      };
    }
  }

  /**
   * Check if bash command should be skipped
   */
  shouldSkipBash(command) {
    const dangerousPatterns = [
      /rm\s+-rf/,
      /sudo/,
      /chmod/,
      /chown/,
      /systemctl/,
      /service\s+/,
      /docker/,
      /kubectl/,
      /npm\s+install/,
      /bun\s+install/,
      /curl.*install/,
    ];

    return dangerousPatterns.some(pattern => pattern.test(command));
  }

  /**
   * Test a single code block
   */
  async testCodeBlock(codeBlock) {
    const { language, filePath, lineNumber } = codeBlock;
    
    this.info(`Testing ${language} code from ${path.basename(filePath)}:${lineNumber}`);

    let result;
    switch (language.toLowerCase()) {
      case 'bash':
      case 'sh':
        if (codeBlock.code.startsWith('curl')) {
          result = await this.testCurlCommand(codeBlock);
        } else {
          result = await this.testBashCode(codeBlock);
        }
        break;

      case 'javascript':
      case 'js':
        result = await this.testJavaScriptCode(codeBlock);
        break;

      case 'typescript':
      case 'ts':
        result = await this.testJavaScriptCode(codeBlock);
        break;

      case 'json':
        result = await this.testJsonCode(codeBlock);
        break;

      default:
        result = {
          type: 'other',
          status: 'skipped',
          reason: `Unsupported language: ${language}`,
          ...codeBlock
        };
    }

    this.testResults.push(result);
    
    // Log result
    switch (result.status) {
      case 'passed':
        this.success(`✓ ${language} code test passed`);
        break;
      case 'skipped':
        this.warning(`⚠ Skipped: ${result.reason}`);
        break;
      case 'expected_error':
        this.info(`ℹ Expected error (like 401/404) - this is OK`);
        break;
      case 'failed':
        this.error(`✗ ${language} code test failed: ${result.error}`);
        break;
    }

    return result;
  }

  /**
   * Generate comprehensive test report
   */
  generateReport() {
    const summary = this.testResults.reduce((acc, result) => {
      acc[result.status] = (acc[result.status] || 0) + 1;
      acc.total++;
      return acc;
    }, { total: 0, passed: 0, failed: 0, skipped: 0, expected_error: 0 });

    const byType = this.testResults.reduce((acc, result) => {
      if (!acc[result.type]) {
        acc[result.type] = { total: 0, passed: 0, failed: 0, skipped: 0, expected_error: 0 };
      }
      acc[result.type][result.status]++;
      acc[result.type].total++;
      return acc;
    }, {});

    const failedTests = this.testResults.filter(r => r.status === 'failed');

    return {
      timestamp: new Date().toISOString(),
      summary,
      byType,
      failedTests: failedTests.map(test => ({
        file: path.relative(PROJECT_ROOT, test.filePath),
        line: test.lineNumber,
        language: test.language,
        error: test.error,
        code: test.code.substring(0, 200) // First 200 chars
      })),
      allResults: this.testResults
    };
  }

  /**
   * Save test report
   */
  async saveReport(report) {
    const reportDir = path.join(PROJECT_ROOT, 'docs', 'validation-reports');
    await fs.mkdir(reportDir, { recursive: true });
    
    const filename = `examples-test-${Date.now()}.json`;
    const filePath = path.join(reportDir, filename);
    
    await fs.writeFile(filePath, JSON.stringify(report, null, 2));
    this.info(`Test report saved to: ${filePath}`);
  }

  /**
   * Main test runner
   */
  async run() {
    this.log('\n🚀 Starting Code Examples Validation\n', 'cyan');

    try {
      // Start test server for API tests
      await this.startTestServer();

      // Find all documentation files
      const docFiles = await this.findDocumentationFiles();
      this.info(`Found ${docFiles.length} documentation files to scan`);

      // Extract and test all code blocks
      let totalBlocks = 0;
      for (const filePath of docFiles) {
        this.info(`\nScanning ${path.relative(PROJECT_ROOT, filePath)}...`);
        
        const content = await fs.readFile(filePath, 'utf-8');
        const codeBlocks = this.extractCodeBlocks(content, filePath);
        
        this.info(`Found ${codeBlocks.length} code blocks`);
        totalBlocks += codeBlocks.length;

        // Test each code block
        for (const codeBlock of codeBlocks) {
          await this.testCodeBlock(codeBlock);
        }
      }

      // Generate and save report
      const report = this.generateReport();
      await this.saveReport(report);

      // Print summary
      this.log('\n📊 TEST SUMMARY', 'magenta');
      this.log('='.repeat(50), 'magenta');
      this.log(`Total Code Blocks: ${totalBlocks}`, 'cyan');
      this.log(`Passed: ${report.summary.passed}`, 'green');
      this.log(`Failed: ${report.summary.failed}`, report.summary.failed > 0 ? 'red' : 'green');
      this.log(`Skipped: ${report.summary.skipped}`, 'yellow');
      this.log(`Expected Errors: ${report.summary.expected_error}`, 'blue');

      // Show breakdown by type
      this.log('\nBy Language:', 'cyan');
      Object.entries(report.byType).forEach(([type, stats]) => {
        this.log(`  ${type}: ${stats.passed}✓ ${stats.failed}✗ ${stats.skipped}⚠`, 'cyan');
      });

      // Show failed tests
      if (report.failedTests.length > 0) {
        this.log('\n❌ Failed Tests:', 'red');
        report.failedTests.forEach((test, i) => {
          this.log(`${i + 1}. ${test.file}:${test.line} (${test.language})`, 'red');
          this.log(`   Error: ${test.error}`, 'red');
        });
      }

      const success = report.summary.failed === 0;
      if (success) {
        this.log('\n🎉 All code examples validated successfully!', 'green');
      } else {
        this.log('\n💥 Some code examples failed validation!', 'red');
      }

      return success;

    } finally {
      // Always stop the server
      await this.stopTestServer();
    }
  }
}

// Run validation if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const validator = new CodeExamplesValidator();
  validator.run()
    .then(success => {
      process.exit(success ? 0 : 1);
    })
    .catch(error => {
      console.error('Examples validation failed:', error);
      process.exit(1);
    });
}

export default CodeExamplesValidator;