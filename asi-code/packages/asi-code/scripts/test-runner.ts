#!/usr/bin/env bun
/**
 * Comprehensive Test Runner for ASI-Code
 * Orchestrates all testing types with detailed reporting and CI integration
 */

import { spawn, exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';
import { CoverageHelpers } from '../test/coverage/analyzer.js';

const execAsync = promisify(exec);

interface TestResult {
  suite: string;
  passed: boolean;
  duration: number;
  coverage?: {
    lines: number;
    functions: number;
    branches: number;
    statements: number;
  };
  output: string;
  error?: string;
}

interface TestSummary {
  totalTests: number;
  passedTests: number;
  failedTests: number;
  totalDuration: number;
  overallCoverage: {
    lines: number;
    functions: number;
    branches: number;
    statements: number;
  };
  results: TestResult[];
  timestamp: string;
}

class TestRunner {
  private results: TestResult[] = [];
  private startTime: number = 0;

  async run(options: {
    suites?: string[];
    coverage?: boolean;
    parallel?: boolean;
    watch?: boolean;
    verbose?: boolean;
    ci?: boolean;
  } = {}) {
    console.log('🚀 Starting ASI-Code Test Runner...\n');
    
    this.startTime = Date.now();
    
    // Setup test environment
    await this.setupEnvironment();
    
    // Define test suites
    const availableSuites = {
      unit: {
        command: 'bun run test:unit',
        description: 'Unit Tests',
        essential: true
      },
      integration: {
        command: 'bun run test:integration',
        description: 'Integration Tests',
        essential: true
      },
      e2e: {
        command: 'bun run test:e2e',
        description: 'End-to-End Tests',
        essential: false
      },
      performance: {
        command: 'bun run test:performance',
        description: 'Performance Tests',
        essential: false
      },
      security: {
        command: 'bun run test:security',
        description: 'Security Tests',
        essential: false
      }
    };

    // Determine which suites to run
    const suitesToRun = options.suites || Object.keys(availableSuites);
    
    console.log(`📋 Running test suites: ${suitesToRun.join(', ')}\n`);

    // Run test suites
    if (options.parallel && !options.watch) {
      await this.runParallel(suitesToRun, availableSuites, options);
    } else {
      await this.runSequential(suitesToRun, availableSuites, options);
    }

    // Generate reports
    await this.generateReports(options);

    // Print summary
    this.printSummary();

    // Exit with appropriate code
    const hasFailures = this.results.some(r => !r.passed);
    process.exit(hasFailures ? 1 : 0);
  }

  private async setupEnvironment() {
    console.log('🔧 Setting up test environment...');
    
    // Ensure test directories exist
    const testDirs = [
      'test-results',
      'coverage',
      'test-results/screenshots',
      'test-results/videos',
      'test-results/traces'
    ];

    for (const dir of testDirs) {
      await fs.mkdir(dir, { recursive: true });
    }

    // Set environment variables
    process.env.NODE_ENV = 'test';
    process.env.LOG_LEVEL = 'error';
    
    console.log('✅ Environment setup complete\n');
  }

  private async runSequential(
    suites: string[],
    availableSuites: Record<string, any>,
    options: any
  ) {
    for (const suite of suites) {
      if (!availableSuites[suite]) {
        console.warn(`⚠️ Unknown test suite: ${suite}`);
        continue;
      }

      await this.runSuite(suite, availableSuites[suite], options);
    }
  }

  private async runParallel(
    suites: string[],
    availableSuites: Record<string, any>,
    options: any
  ) {
    const promises = suites
      .filter(suite => availableSuites[suite])
      .map(suite => this.runSuite(suite, availableSuites[suite], options));

    await Promise.allSettled(promises);
  }

  private async runSuite(
    name: string,
    suite: any,
    options: any
  ): Promise<void> {
    console.log(`🧪 Running ${suite.description}...`);
    
    const startTime = Date.now();
    let command = suite.command;
    
    // Add coverage flag if requested
    if (options.coverage && name !== 'e2e') {
      command += ' --coverage';
    }
    
    // Add watch flag if requested
    if (options.watch) {
      command += ' --watch';
    }

    try {
      const { stdout, stderr } = await execAsync(command, {
        env: { ...process.env },
        maxBuffer: 1024 * 1024 * 10 // 10MB buffer
      });

      const duration = Date.now() - startTime;
      
      this.results.push({
        suite: name,
        passed: true,
        duration,
        output: stdout,
        ...(await this.extractCoverage(name))
      });

      console.log(`✅ ${suite.description} completed in ${duration}ms`);
      
      if (options.verbose) {
        console.log(stdout);
      }

    } catch (error: any) {
      const duration = Date.now() - startTime;
      
      this.results.push({
        suite: name,
        passed: false,
        duration,
        output: error.stdout || '',
        error: error.stderr || error.message
      });

      console.log(`❌ ${suite.description} failed in ${duration}ms`);
      
      if (options.verbose || options.ci) {
        console.error(error.stderr || error.message);
      }
    }
  }

  private async extractCoverage(suite: string): Promise<{ coverage?: any }> {
    try {
      const coveragePath = `coverage/${suite}/coverage-summary.json`;
      const coverageData = await fs.readFile(coveragePath, 'utf8');
      const coverage = JSON.parse(coverageData);
      
      if (coverage.total) {
        return {
          coverage: {
            lines: coverage.total.lines.pct,
            functions: coverage.total.functions.pct,
            branches: coverage.total.branches.pct,
            statements: coverage.total.statements.pct
          }
        };
      }
    } catch (error) {
      // Coverage data not available for this suite
    }
    
    return {};
  }

  private async generateReports(options: any) {
    console.log('\n📊 Generating test reports...');

    // Generate test summary
    const summary = this.createTestSummary();
    await fs.writeFile(
      'test-results/test-summary.json',
      JSON.stringify(summary, null, 2)
    );

    // Generate coverage report if coverage was collected
    if (options.coverage) {
      try {
        await CoverageHelpers.generateAllReports();
      } catch (error) {
        console.warn('⚠️ Could not generate coverage reports:', error);
      }
    }

    // Generate CI-friendly output
    if (options.ci) {
      await this.generateCIOutput(summary);
    }

    // Generate HTML report
    await this.generateHTMLReport(summary);
    
    console.log('✅ Reports generated');
  }

  private createTestSummary(): TestSummary {
    const passedTests = this.results.filter(r => r.passed).length;
    const failedTests = this.results.filter(r => !r.passed).length;
    const totalDuration = Date.now() - this.startTime;

    // Calculate overall coverage
    const coverageResults = this.results.filter(r => r.coverage);
    const overallCoverage = coverageResults.length > 0 ? {
      lines: Math.round(coverageResults.reduce((sum, r) => sum + (r.coverage?.lines || 0), 0) / coverageResults.length),
      functions: Math.round(coverageResults.reduce((sum, r) => sum + (r.coverage?.functions || 0), 0) / coverageResults.length),
      branches: Math.round(coverageResults.reduce((sum, r) => sum + (r.coverage?.branches || 0), 0) / coverageResults.length),
      statements: Math.round(coverageResults.reduce((sum, r) => sum + (r.coverage?.statements || 0), 0) / coverageResults.length)
    } : { lines: 0, functions: 0, branches: 0, statements: 0 };

    return {
      totalTests: this.results.length,
      passedTests,
      failedTests,
      totalDuration,
      overallCoverage,
      results: this.results,
      timestamp: new Date().toISOString()
    };
  }

  private async generateCIOutput(summary: TestSummary) {
    let output = '## 🧪 Test Results Summary\n\n';
    output += `- **Total Suites**: ${summary.totalTests}\n`;
    output += `- **Passed**: ${summary.passedTests} ✅\n`;
    output += `- **Failed**: ${summary.failedTests} ${summary.failedTests > 0 ? '❌' : ''}\n`;
    output += `- **Duration**: ${Math.round(summary.totalDuration / 1000)}s\n\n`;

    if (summary.overallCoverage.lines > 0) {
      output += '### Coverage\n';
      output += `- **Lines**: ${summary.overallCoverage.lines}%\n`;
      output += `- **Functions**: ${summary.overallCoverage.functions}%\n`;
      output += `- **Branches**: ${summary.overallCoverage.branches}%\n`;
      output += `- **Statements**: ${summary.overallCoverage.statements}%\n\n`;
    }

    output += '### Test Suites\n';
    for (const result of summary.results) {
      const status = result.passed ? '✅' : '❌';
      const duration = Math.round(result.duration / 1000);
      output += `- **${result.suite}**: ${status} (${duration}s)\n`;
      
      if (!result.passed && result.error) {
        output += `  - Error: ${result.error.split('\n')[0]}\n`;
      }
    }

    // Write to GitHub Step Summary if in CI
    if (process.env.GITHUB_STEP_SUMMARY) {
      await fs.appendFile(process.env.GITHUB_STEP_SUMMARY, output);
    }

    // Also write to file
    await fs.writeFile('test-results/ci-summary.md', output);
  }

  private async generateHTMLReport(summary: TestSummary) {
    const html = `
<!DOCTYPE html>
<html>
<head>
    <title>ASI-Code Test Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .summary-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
        .summary-card h3 { margin: 0 0 10px 0; color: #495057; }
        .summary-card .value { font-size: 2em; font-weight: bold; }
        .passed { color: #28a745; }
        .failed { color: #dc3545; }
        .coverage { color: #007bff; }
        .results { margin-top: 30px; }
        .result { margin: 15px 0; padding: 15px; border-radius: 8px; border-left: 4px solid; }
        .result.passed { background: #d4edda; border-color: #28a745; }
        .result.failed { background: #f8d7da; border-color: #dc3545; }
        .result h4 { margin: 0 0 10px 0; }
        .result .meta { color: #666; font-size: 0.9em; }
        .error { background: #f8f8f8; padding: 10px; border-radius: 4px; margin-top: 10px; font-family: monospace; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ASI-Code Test Results</h1>
            <p>Generated on ${new Date(summary.timestamp).toLocaleString()}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Suites</h3>
                <div class="value">${summary.totalTests}</div>
            </div>
            <div class="summary-card">
                <h3>Passed</h3>
                <div class="value passed">${summary.passedTests}</div>
            </div>
            <div class="summary-card">
                <h3>Failed</h3>
                <div class="value failed">${summary.failedTests}</div>
            </div>
            <div class="summary-card">
                <h3>Duration</h3>
                <div class="value">${Math.round(summary.totalDuration / 1000)}s</div>
            </div>
            ${summary.overallCoverage.lines > 0 ? `
            <div class="summary-card">
                <h3>Coverage</h3>
                <div class="value coverage">${summary.overallCoverage.lines}%</div>
            </div>
            ` : ''}
        </div>
        
        <div class="results">
            <h2>Test Suite Results</h2>
            ${summary.results.map(result => `
                <div class="result ${result.passed ? 'passed' : 'failed'}">
                    <h4>${result.suite} ${result.passed ? '✅' : '❌'}</h4>
                    <div class="meta">
                        Duration: ${Math.round(result.duration / 1000)}s
                        ${result.coverage ? `| Coverage: Lines ${result.coverage.lines}%, Functions ${result.coverage.functions}%` : ''}
                    </div>
                    ${result.error ? `<div class="error">${result.error}</div>` : ''}
                </div>
            `).join('')}
        </div>
    </div>
</body>
</html>
    `;

    await fs.writeFile('test-results/test-report.html', html);
  }

  private printSummary() {
    const summary = this.createTestSummary();
    
    console.log('\n' + '='.repeat(60));
    console.log('📊 TEST RESULTS SUMMARY');
    console.log('='.repeat(60));
    console.log(`Total Suites: ${summary.totalTests}`);
    console.log(`Passed: ${summary.passedTests} ✅`);
    console.log(`Failed: ${summary.failedTests} ${summary.failedTests > 0 ? '❌' : ''}`);
    console.log(`Duration: ${Math.round(summary.totalDuration / 1000)}s`);
    
    if (summary.overallCoverage.lines > 0) {
      console.log(`Coverage: ${summary.overallCoverage.lines}%`);
    }
    
    console.log('='.repeat(60));
    
    if (summary.failedTests > 0) {
      console.log('\n❌ FAILED SUITES:');
      summary.results
        .filter(r => !r.passed)
        .forEach(result => {
          console.log(`  - ${result.suite}: ${result.error?.split('\n')[0] || 'Unknown error'}`);
        });
    }
    
    console.log(`\n📄 Reports generated in test-results/`);
    console.log(`   - test-results/test-report.html`);
    console.log(`   - test-results/test-summary.json`);
    if (summary.overallCoverage.lines > 0) {
      console.log(`   - coverage/enhanced-report.html`);
    }
  }
}

// CLI interface
async function main() {
  const args = process.argv.slice(2);
  const options: any = {
    suites: [],
    coverage: false,
    parallel: false,
    watch: false,
    verbose: false,
    ci: false
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    
    switch (arg) {
      case '--coverage':
        options.coverage = true;
        break;
      case '--parallel':
        options.parallel = true;
        break;
      case '--watch':
        options.watch = true;
        break;
      case '--verbose':
      case '-v':
        options.verbose = true;
        break;
      case '--ci':
        options.ci = true;
        break;
      case '--suites':
        i++;
        if (args[i]) {
          options.suites = args[i].split(',');
        }
        break;
      case '--help':
      case '-h':
        printHelp();
        process.exit(0);
        break;
      default:
        if (!arg.startsWith('--')) {
          options.suites.push(arg);
        }
    }
  }

  const runner = new TestRunner();
  await runner.run(options);
}

function printHelp() {
  console.log(`
ASI-Code Test Runner

Usage: bun run scripts/test-runner.ts [options] [suites...]

Options:
  --coverage     Generate coverage reports
  --parallel     Run test suites in parallel
  --watch        Run tests in watch mode
  --verbose, -v  Show detailed output
  --ci           Generate CI-friendly output
  --suites <list> Comma-separated list of suites to run
  --help, -h     Show this help message

Test Suites:
  unit           Unit tests (fast, isolated)
  integration    Integration tests (with database)
  e2e            End-to-end tests (browser-based)
  performance    Performance and benchmark tests
  security       Security and vulnerability tests

Examples:
  bun run scripts/test-runner.ts --coverage
  bun run scripts/test-runner.ts unit integration --parallel
  bun run scripts/test-runner.ts --watch --verbose
  bun run scripts/test-runner.ts --ci --coverage
  `);
}

// Run if called directly
if (import.meta.main) {
  main().catch((error) => {
    console.error('Test runner failed:', error);
    process.exit(1);
  });
}

export { TestRunner };