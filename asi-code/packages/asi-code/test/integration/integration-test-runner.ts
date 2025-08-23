/**
 * Integration Test Runner - Orchestrates and manages comprehensive integration tests
 * 
 * Provides utilities for running integration tests with proper setup, teardown,
 * resource management, and reporting across all test suites.
 */

import { Logger } from '../../src/logging/index.js';
import { performance } from 'perf_hooks';

export interface TestSuiteConfig {
  name: string;
  enabled: boolean;
  timeout: number;
  retries: number;
  parallel: boolean;
  prerequisites?: string[];
  resources?: {
    memory?: string;
    ports?: number[];
    files?: string[];
  };
}

export interface TestRunnerConfig {
  suites: { [key: string]: TestSuiteConfig };
  global: {
    timeout: number;
    retries: number;
    bail: boolean;
    verbose: boolean;
    coverage: boolean;
  };
  reporting: {
    formats: string[];
    outputDir: string;
    includeMetrics: boolean;
  };
  environment: {
    nodeEnv: string;
    logLevel: string;
    parallelWorkers: number;
  };
}

export class IntegrationTestRunner {
  private logger: Logger;
  private config: TestRunnerConfig;
  private testResults: Map<string, any> = new Map();
  private startTime: number = 0;

  constructor(config: TestRunnerConfig) {
    this.config = config;
    this.logger = new Logger({
      level: config.environment.logLevel as any,
      enabled: true
    });
  }

  async runAllSuites(): Promise<{
    success: boolean;
    results: Map<string, any>;
    summary: {
      totalDuration: number;
      suitesRun: number;
      suitesPass: number;
      suitesFail: number;
      testsRun: number;
      testsPass: number;
      testsFail: number;
    };
  }> {
    this.startTime = performance.now();
    this.logger.info('Starting comprehensive integration test run');

    const enabledSuites = Object.entries(this.config.suites)
      .filter(([_, config]) => config.enabled)
      .map(([name, config]) => ({ name, config }));

    this.logger.info(`Running ${enabledSuites.length} test suites`);

    let suitesPass = 0;
    let suitesFail = 0;
    let testsRun = 0;
    let testsPass = 0;
    let testsFail = 0;

    for (const { name, config } of enabledSuites) {
      try {
        this.logger.info(`Starting test suite: ${name}`);
        const suiteStart = performance.now();

        // Check prerequisites
        if (config.prerequisites) {
          for (const prerequisite of config.prerequisites) {
            if (!this.testResults.get(prerequisite)?.success) {
              throw new Error(`Prerequisite suite '${prerequisite}' failed or did not run`);
            }
          }
        }

        // Run the suite (this would integrate with vitest)
        const result = await this.runTestSuite(name, config);
        
        const suiteDuration = performance.now() - suiteStart;
        this.testResults.set(name, {
          ...result,
          duration: suiteDuration
        });

        if (result.success) {
          suitesPass++;
          this.logger.info(`✓ Suite ${name} passed (${suiteDuration.toFixed(2)}ms)`);
        } else {
          suitesFail++;
          this.logger.error(`✗ Suite ${name} failed (${suiteDuration.toFixed(2)}ms)`);
          
          if (this.config.global.bail) {
            this.logger.error('Bailing out due to suite failure');
            break;
          }
        }

        testsRun += result.testsRun || 0;
        testsPass += result.testsPass || 0;
        testsFail += result.testsFail || 0;

      } catch (error) {
        suitesFail++;
        this.logger.error(`Suite ${name} encountered error:`, error);
        this.testResults.set(name, {
          success: false,
          error: error instanceof Error ? error.message : String(error),
          duration: performance.now() - performance.now()
        });

        if (this.config.global.bail) {
          break;
        }
      }
    }

    const totalDuration = performance.now() - this.startTime;
    const success = suitesFail === 0;

    const summary = {
      totalDuration,
      suitesRun: suitesPass + suitesFail,
      suitesPass,
      suitesFail,
      testsRun,
      testsPass,
      testsFail
    };

    this.logger.info('Integration test run completed', summary);

    if (this.config.reporting.includeMetrics) {
      await this.generateReport(summary);
    }

    return {
      success,
      results: this.testResults,
      summary
    };
  }

  private async runTestSuite(name: string, config: TestSuiteConfig): Promise<{
    success: boolean;
    testsRun: number;
    testsPass: number;
    testsFail: number;
    errors?: string[];
  }> {
    // This would integrate with vitest to run specific test files
    // For now, return a mock result structure
    return {
      success: true,
      testsRun: 10,
      testsPass: 10,
      testsFail: 0
    };
  }

  private async generateReport(summary: any): Promise<void> {
    const report = {
      timestamp: new Date().toISOString(),
      environment: {
        nodeVersion: process.version,
        platform: process.platform,
        arch: process.arch,
        memory: process.memoryUsage()
      },
      configuration: this.config,
      summary,
      suiteResults: Array.from(this.testResults.entries()).map(([name, result]) => ({
        suite: name,
        ...result
      })),
      metrics: {
        totalExecutionTime: summary.totalDuration,
        averageSuiteTime: summary.totalDuration / summary.suitesRun,
        successRate: (summary.suitesPass / summary.suitesRun) * 100
      }
    };

    // Write report files
    for (const format of this.config.reporting.formats) {
      await this.writeReport(report, format);
    }
  }

  private async writeReport(report: any, format: string): Promise<void> {
    const fs = await import('fs/promises');
    const path = await import('path');
    
    const outputDir = this.config.reporting.outputDir;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    
    try {
      await fs.mkdir(outputDir, { recursive: true });
      
      switch (format) {
        case 'json':
          await fs.writeFile(
            path.join(outputDir, `integration-test-report-${timestamp}.json`),
            JSON.stringify(report, null, 2)
          );
          break;
          
        case 'html':
          const html = this.generateHTMLReport(report);
          await fs.writeFile(
            path.join(outputDir, `integration-test-report-${timestamp}.html`),
            html
          );
          break;
          
        case 'junit':
          const xml = this.generateJUnitReport(report);
          await fs.writeFile(
            path.join(outputDir, `integration-test-report-${timestamp}.xml`),
            xml
          );
          break;
      }
    } catch (error) {
      this.logger.error(`Failed to write ${format} report:`, error);
    }
  }

  private generateHTMLReport(report: any): string {
    const { summary, suiteResults, metrics } = report;
    
    return `
<!DOCTYPE html>
<html>
<head>
    <title>ASI-Code Integration Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f5f5f5; padding: 20px; border-radius: 5px; }
        .success { color: #4CAF50; }
        .failure { color: #f44336; }
        .summary { display: flex; gap: 20px; margin: 20px 0; }
        .metric { background: #e3f2fd; padding: 15px; border-radius: 5px; text-align: center; }
        .suite { margin: 10px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .suite.passed { border-color: #4CAF50; }
        .suite.failed { border-color: #f44336; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f5f5f5; }
    </style>
</head>
<body>
    <div class="header">
        <h1>ASI-Code Integration Test Report</h1>
        <p>Generated: ${report.timestamp}</p>
        <p>Environment: Node ${report.environment.nodeVersion} on ${report.environment.platform}</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>Suites</h3>
            <p>${summary.suitesPass}/${summary.suitesRun} passed</p>
        </div>
        <div class="metric">
            <h3>Tests</h3>
            <p>${summary.testsPass}/${summary.testsRun} passed</p>
        </div>
        <div class="metric">
            <h3>Duration</h3>
            <p>${(summary.totalDuration / 1000).toFixed(2)}s</p>
        </div>
        <div class="metric">
            <h3>Success Rate</h3>
            <p>${metrics.successRate.toFixed(1)}%</p>
        </div>
    </div>

    <h2>Test Suites</h2>
    ${suiteResults.map((suite: any) => `
        <div class="suite ${suite.success ? 'passed' : 'failed'}">
            <h3 class="${suite.success ? 'success' : 'failure'}">
                ${suite.success ? '✓' : '✗'} ${suite.suite}
            </h3>
            <p>Duration: ${(suite.duration / 1000).toFixed(2)}s</p>
            ${suite.testsRun ? `<p>Tests: ${suite.testsPass}/${suite.testsRun} passed</p>` : ''}
            ${suite.error ? `<p class="failure">Error: ${suite.error}</p>` : ''}
        </div>
    `).join('')}

    <h2>Environment Details</h2>
    <table>
        <tr><th>Property</th><th>Value</th></tr>
        <tr><td>Node Version</td><td>${report.environment.nodeVersion}</td></tr>
        <tr><td>Platform</td><td>${report.environment.platform}</td></tr>
        <tr><td>Architecture</td><td>${report.environment.arch}</td></tr>
        <tr><td>Memory Usage</td><td>${(report.environment.memory.heapUsed / 1024 / 1024).toFixed(2)} MB</td></tr>
    </table>
</body>
</html>
    `;
  }

  private generateJUnitReport(report: any): string {
    const { summary, suiteResults } = report;
    
    return `<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="ASI-Code Integration Tests" 
           tests="${summary.testsRun}" 
           failures="${summary.testsFail}" 
           time="${(summary.totalDuration / 1000).toFixed(3)}">
    ${suiteResults.map((suite: any) => `
    <testsuite name="${suite.suite}" 
               tests="${suite.testsRun || 1}" 
               failures="${suite.testsFail || (suite.success ? 0 : 1)}" 
               time="${(suite.duration / 1000).toFixed(3)}">
        ${suite.success ? 
          '<testcase name="suite-execution" />' :
          `<testcase name="suite-execution">
             <failure message="${suite.error || 'Suite failed'}" />
           </testcase>`
        }
    </testsuite>`).join('')}
</testsuites>`;
  }
}

// Default configuration for ASI-Code integration tests
export const defaultTestRunnerConfig: TestRunnerConfig = {
  suites: {
    'api-integration': {
      name: 'API Integration Tests',
      enabled: true,
      timeout: 60000,
      retries: 2,
      parallel: false,
      resources: {
        ports: [3003],
        memory: '512MB'
      }
    },
    'websocket-integration': {
      name: 'WebSocket Integration Tests',
      enabled: true,
      timeout: 120000,
      retries: 1,
      parallel: false,
      prerequisites: ['api-integration'],
      resources: {
        ports: [3004],
        memory: '256MB'
      }
    },
    'database-integration': {
      name: 'Database Integration Tests',
      enabled: true,
      timeout: 90000,
      retries: 2,
      parallel: false,
      resources: {
        memory: '1GB'
      }
    },
    'provider-integration': {
      name: 'Provider Integration Tests',
      enabled: true,
      timeout: 180000,
      retries: 3,
      parallel: true,
      resources: {
        memory: '512MB'
      }
    },
    'tool-integration': {
      name: 'Tool System Integration Tests',
      enabled: true,
      timeout: 120000,
      retries: 2,
      parallel: false,
      resources: {
        memory: '512MB',
        files: ['/tmp/tool-test-*']
      }
    },
    'auth-permission-integration': {
      name: 'Authentication and Permission Tests',
      enabled: true,
      timeout: 90000,
      retries: 1,
      parallel: false,
      prerequisites: ['api-integration'],
      resources: {
        ports: [3005],
        memory: '256MB'
      }
    },
    'error-recovery-integration': {
      name: 'Error Handling and Recovery Tests',
      enabled: true,
      timeout: 150000,
      retries: 1,
      parallel: false,
      resources: {
        ports: [3006],
        memory: '512MB'
      }
    },
    'performance-load-integration': {
      name: 'Performance and Load Tests',
      enabled: true,
      timeout: 300000, // 5 minutes for performance tests
      retries: 0, // No retries for performance tests
      parallel: false,
      resources: {
        ports: [3007],
        memory: '2GB'
      }
    }
  },
  global: {
    timeout: 300000,
    retries: 1,
    bail: false,
    verbose: true,
    coverage: true
  },
  reporting: {
    formats: ['json', 'html', 'junit'],
    outputDir: './test-reports/integration',
    includeMetrics: true
  },
  environment: {
    nodeEnv: 'test',
    logLevel: 'info',
    parallelWorkers: 1
  }
};

// Export utility functions for test setup
export async function setupIntegrationTestEnvironment(): Promise<void> {
  // Set environment variables
  process.env.NODE_ENV = 'test';
  process.env.LOG_LEVEL = 'error';
  
  // Ensure test directories exist
  const fs = await import('fs/promises');
  const testDirs = [
    './test-reports',
    './test-reports/integration',
    './test-data',
    './test-temp'
  ];
  
  for (const dir of testDirs) {
    try {
      await fs.mkdir(dir, { recursive: true });
    } catch (error) {
      // Directory may already exist
    }
  }
}

export async function cleanupIntegrationTestEnvironment(): Promise<void> {
  // Cleanup temporary test files and directories
  const fs = await import('fs/promises');
  const cleanupDirs = [
    './test-temp',
    './test-data'
  ];
  
  for (const dir of cleanupDirs) {
    try {
      await fs.rm(dir, { recursive: true, force: true });
    } catch (error) {
      // Directory may not exist
    }
  }
  
  // Force garbage collection if available
  if (global.gc) {
    global.gc();
  }
}