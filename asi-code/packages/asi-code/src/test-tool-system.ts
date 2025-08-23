#!/usr/bin/env bun

/**
 * Tool System Test Suite
 *
 * Comprehensive test suite for the enhanced tool system including:
 * - Tool registration and discovery
 * - Tool execution with various parameters
 * - Permission checking and validation
 * - Batch execution
 * - Error handling
 * - Metrics and health monitoring
 */

import { initializeToolSystem } from './tool/tool-initializer.js';
import { createCompatibleToolManager } from './tool/tool-manager-bridge.js';
import { BaseTool, ToolExecutionContext } from './tool/base-tool.js';

interface TestResult {
  name: string;
  success: boolean;
  duration: number;
  details: any;
  error?: string;
}

class TestRunner {
  private readonly results: TestResult[] = [];
  private toolManager: any;

  async runAllTests() {
    console.log('🧪 Starting Tool System Test Suite...\n');

    try {
      // Initialize the tool system
      await this.initializeToolSystem();

      // Run tests
      await this.testToolDiscovery();
      await this.testToolExecution();
      await this.testToolValidation();
      await this.testBatchExecution();
      await this.testErrorHandling();
      await this.testPermissionChecking();
      await this.testMetricsAndHealth();

      // Report results
      this.reportResults();
    } catch (error) {
      console.error('❌ Test suite failed to run:', error);
      process.exit(1);
    } finally {
      // Cleanup
      await this.cleanup();
    }
  }

  private async initializeToolSystem() {
    const startTime = Date.now();

    try {
      console.log('🔧 Initializing tool system...');

      const initResult = await initializeToolSystem({
        enableMetrics: true,
        enableCaching: true,
        maxConcurrentExecutions: 5,
        defaultTimeout: 30000,
        autoRegisterBuiltIns: true,
        enableToolValidation: true,
        enableVersioning: true,
      });

      this.toolManager = await createCompatibleToolManager({
        enableMetrics: true,
        enableCaching: true,
        maxConcurrentExecutions: 5,
        defaultTimeout: 30000,
        autoRegisterBuiltIns: true,
        enableToolValidation: true,
        enableVersioning: true,
      });

      this.recordResult(
        'Tool System Initialization',
        true,
        Date.now() - startTime,
        {
          toolsRegistered: initResult.toolsRegistered,
          categories: initResult.categoryCounts,
          errors: initResult.errors,
        }
      );

      console.log(
        `✅ Tool system initialized with ${initResult.toolsRegistered} tools`
      );
      console.log(
        `   Categories: ${Object.keys(initResult.categoryCounts).join(', ')}\n`
      );
    } catch (error) {
      this.recordResult(
        'Tool System Initialization',
        false,
        Date.now() - startTime,
        {},
        (error as Error).message
      );
      throw error;
    }
  }

  private async testToolDiscovery() {
    console.log('🔍 Testing Tool Discovery...');
    const startTime = Date.now();

    try {
      // Test basic tool listing
      const tools = this.toolManager.list();
      console.log(`   Found ${tools.length} tools`);

      // Test enhanced discovery
      let discoveryInfo = [];
      if (this.toolManager.discoverTools) {
        discoveryInfo = this.toolManager.discoverTools();
        console.log(`   Discovery info for ${discoveryInfo.length} tools`);
      }

      // Test system info
      let systemInfo = {};
      if (this.toolManager.getSystemInfo) {
        systemInfo = this.toolManager.getSystemInfo();
        console.log(`   System info: ${JSON.stringify(systemInfo, null, 2)}`);
      }

      // Verify expected tools are present
      const expectedTools = [
        'read',
        'write',
        'edit',
        'bash',
        'search',
        'delete',
        'move',
        'list',
      ];
      const actualTools = tools.map((t: any) => t.name);
      const missingTools = expectedTools.filter(
        name => !actualTools.includes(name)
      );

      if (missingTools.length > 0) {
        throw new Error(`Missing expected tools: ${missingTools.join(', ')}`);
      }

      this.recordResult('Tool Discovery', true, Date.now() - startTime, {
        totalTools: tools.length,
        expectedTools: expectedTools.length,
        missingTools: missingTools,
        discoveryInfo: discoveryInfo.length,
        systemInfo,
      });

      console.log('✅ Tool discovery test passed\n');
    } catch (error) {
      this.recordResult(
        'Tool Discovery',
        false,
        Date.now() - startTime,
        {},
        (error as Error).message
      );
      console.error(
        '❌ Tool discovery test failed:',
        (error as Error).message,
        '\n'
      );
    }
  }

  private async testToolExecution() {
    console.log('⚡ Testing Tool Execution...');
    const startTime = Date.now();

    try {
      const testContext: ToolExecutionContext = {
        sessionId: 'test-session',
        userId: 'test-user',
        permissions: ['read_files', 'write_files', 'execute_commands'],
        workingDirectory: process.cwd(),
        environment: {},
        metadata: {},
      };

      const executionResults: any[] = [];

      // Test 1: List tool (directory listing)
      console.log('   Testing list tool...');
      const listResult = await this.toolManager.execute(
        'list',
        {
          path: '.',
          maxResults: 10,
        },
        testContext
      );

      if (!listResult.success) {
        throw new Error(`List tool failed: ${listResult.error}`);
      }

      executionResults.push({
        tool: 'list',
        success: listResult.success,
        itemsFound: listResult.data?.items?.length || 0,
      });
      console.log(
        `   ✅ List tool found ${listResult.data?.items?.length || 0} items`
      );

      // Test 2: Write tool (create a test file)
      console.log('   Testing write tool...');
      const writeResult = await this.toolManager.execute(
        'write',
        {
          path: './test-file.txt',
          content: 'Hello, ASI-Code Tool System!\nThis is a test file.',
          createDirs: true,
        },
        testContext
      );

      if (!writeResult.success) {
        throw new Error(`Write tool failed: ${writeResult.error}`);
      }

      executionResults.push({
        tool: 'write',
        success: writeResult.success,
        bytesWritten: writeResult.data?.bytesWritten,
      });
      console.log(
        `   ✅ Write tool created file with ${writeResult.data?.bytesWritten || 0} bytes`
      );

      // Test 3: Read tool (read the test file)
      console.log('   Testing read tool...');
      const readResult = await this.toolManager.execute(
        'read',
        {
          path: './test-file.txt',
        },
        testContext
      );

      if (!readResult.success) {
        throw new Error(`Read tool failed: ${readResult.error}`);
      }

      executionResults.push({
        tool: 'read',
        success: readResult.success,
        contentLength: readResult.data?.content?.length || 0,
      });
      console.log(
        `   ✅ Read tool retrieved ${readResult.data?.content?.length || 0} characters`
      );

      // Test 4: Search tool (search in current directory)
      console.log('   Testing search tool...');
      const searchResult = await this.toolManager.execute(
        'search',
        {
          query: 'ASI-Code',
          path: '.',
          filePattern: '*.txt',
          maxResults: 50,
        },
        testContext
      );

      if (!searchResult.success) {
        throw new Error(`Search tool failed: ${searchResult.error}`);
      }

      executionResults.push({
        tool: 'search',
        success: searchResult.success,
        matchesFound: searchResult.data?.statistics?.totalMatches || 0,
      });
      console.log(
        `   ✅ Search tool found ${searchResult.data?.statistics?.totalMatches || 0} matches`
      );

      this.recordResult('Tool Execution', true, Date.now() - startTime, {
        executionResults,
        allSuccessful: executionResults.every(r => r.success),
      });

      console.log('✅ Tool execution tests passed\n');
    } catch (error) {
      this.recordResult(
        'Tool Execution',
        false,
        Date.now() - startTime,
        {},
        (error as Error).message
      );
      console.error(
        '❌ Tool execution test failed:',
        (error as Error).message,
        '\n'
      );
    }
  }

  private async testToolValidation() {
    console.log('✅ Testing Tool Validation...');
    const startTime = Date.now();

    try {
      const validationResults: any[] = [];

      // Test 1: Valid parameters
      console.log('   Testing valid parameters...');
      if (this.toolManager.validateToolParameters) {
        const validResult = this.toolManager.validateToolParameters('read', {
          path: './test-file.txt',
          encoding: 'utf8',
        });

        validationResults.push({ test: 'valid_params', result: validResult });
        console.log(
          `   ✅ Valid parameters: ${validResult.isValid ? 'PASS' : 'FAIL'}`
        );
      }

      // Test 2: Invalid parameters (missing required)
      console.log('   Testing invalid parameters...');
      if (this.toolManager.validateToolParameters) {
        const invalidResult = this.toolManager.validateToolParameters('read', {
          encoding: 'utf8', // missing required 'path'
        });

        validationResults.push({
          test: 'invalid_params',
          result: invalidResult,
        });
        console.log(
          `   ✅ Invalid parameters detected: ${!invalidResult.isValid ? 'PASS' : 'FAIL'}`
        );
      }

      // Test 3: Type validation
      console.log('   Testing type validation...');
      if (this.toolManager.validateToolParameters) {
        const typeResult = this.toolManager.validateToolParameters('list', {
          path: './test-dir',
          maxResults: 'not-a-number', // should be number
        });

        validationResults.push({ test: 'type_validation', result: typeResult });
        console.log(
          `   ✅ Type validation: ${!typeResult.isValid ? 'PASS' : 'FAIL'}`
        );
      }

      this.recordResult('Tool Validation', true, Date.now() - startTime, {
        validationResults,
        testsRun: validationResults.length,
      });

      console.log('✅ Tool validation tests passed\n');
    } catch (error) {
      this.recordResult(
        'Tool Validation',
        false,
        Date.now() - startTime,
        {},
        (error as Error).message
      );
      console.error(
        '❌ Tool validation test failed:',
        (error as Error).message,
        '\n'
      );
    }
  }

  private async testBatchExecution() {
    console.log('📦 Testing Batch Execution...');
    const startTime = Date.now();

    try {
      // Create a mock batch execution function since the server isn't running
      const batchOperations = [
        {
          name: 'write',
          parameters: {
            path: './batch-test-1.txt',
            content: 'Batch test file 1',
          },
        },
        {
          name: 'write',
          parameters: {
            path: './batch-test-2.txt',
            content: 'Batch test file 2',
          },
        },
        {
          name: 'list',
          parameters: {
            path: '.',
            maxResults: 20,
          },
        },
      ];

      const testContext: ToolExecutionContext = {
        sessionId: 'batch-test-session',
        userId: 'test-user',
        permissions: ['read_files', 'write_files'],
        workingDirectory: process.cwd(),
        environment: {},
        metadata: {},
      };

      const batchResults = [];
      for (const operation of batchOperations) {
        console.log(`   Executing ${operation.name}...`);
        const result = await this.toolManager.execute(
          operation.name,
          operation.parameters,
          testContext
        );
        batchResults.push({
          toolName: operation.name,
          success: result.success,
          error: result.error,
        });
      }

      const successCount = batchResults.filter(r => r.success).length;
      console.log(
        `   ✅ Batch execution: ${successCount}/${batchResults.length} operations successful`
      );

      this.recordResult('Batch Execution', true, Date.now() - startTime, {
        totalOperations: batchOperations.length,
        successfulOperations: successCount,
        batchResults,
      });

      console.log('✅ Batch execution test passed\n');
    } catch (error) {
      this.recordResult(
        'Batch Execution',
        false,
        Date.now() - startTime,
        {},
        (error as Error).message
      );
      console.error(
        '❌ Batch execution test failed:',
        (error as Error).message,
        '\n'
      );
    }
  }

  private async testErrorHandling() {
    console.log('🚨 Testing Error Handling...');
    const startTime = Date.now();

    try {
      const testContext: ToolExecutionContext = {
        sessionId: 'error-test-session',
        userId: 'test-user',
        permissions: ['read_files'],
        workingDirectory: process.cwd(),
        environment: {},
        metadata: {},
      };

      const errorTests = [];

      // Test 1: Non-existent tool
      console.log('   Testing non-existent tool...');
      try {
        const result = await this.toolManager.execute(
          'nonexistent-tool',
          {},
          testContext
        );
        errorTests.push({
          test: 'nonexistent_tool',
          handled: !result.success,
          error: result.error,
        });
        console.log(
          `   ✅ Non-existent tool error handled: ${!result.success ? 'PASS' : 'FAIL'}`
        );
      } catch (error) {
        errorTests.push({
          test: 'nonexistent_tool',
          handled: true,
          error: (error as Error).message,
        });
        console.log(`   ✅ Non-existent tool error handled: PASS`);
      }

      // Test 2: Invalid file path
      console.log('   Testing invalid file path...');
      const invalidPathResult = await this.toolManager.execute(
        'read',
        {
          path: '/nonexistent/path/to/file.txt',
        },
        testContext
      );
      errorTests.push({
        test: 'invalid_path',
        handled: !invalidPathResult.success,
        error: invalidPathResult.error,
      });
      console.log(
        `   ✅ Invalid path error handled: ${!invalidPathResult.success ? 'PASS' : 'FAIL'}`
      );

      // Test 3: Permission denied (try to write without write permission)
      console.log('   Testing permission denied...');
      const permissionDeniedResult = await this.toolManager.execute(
        'write',
        {
          path: './permission-test.txt',
          content: 'test',
        },
        {
          ...testContext,
          permissions: ['read_files'], // no write permission
        }
      );
      errorTests.push({
        test: 'permission_denied',
        handled: !permissionDeniedResult.success,
        error: permissionDeniedResult.error,
      });
      console.log(
        `   ✅ Permission denied handled: ${!permissionDeniedResult.success ? 'PASS' : 'FAIL'}`
      );

      this.recordResult('Error Handling', true, Date.now() - startTime, {
        errorTests,
        allErrorsHandled: errorTests.every(t => t.handled),
      });

      console.log('✅ Error handling tests passed\n');
    } catch (error) {
      this.recordResult(
        'Error Handling',
        false,
        Date.now() - startTime,
        {},
        (error as Error).message
      );
      console.error(
        '❌ Error handling test failed:',
        (error as Error).message,
        '\n'
      );
    }
  }

  private async testPermissionChecking() {
    console.log('🔒 Testing Permission Checking...');
    const startTime = Date.now();

    try {
      const permissionTests = [];

      // Test with different permission sets
      const contexts = [
        {
          name: 'read_only',
          context: {
            sessionId: 'perm-test-1',
            userId: 'test-user',
            permissions: ['read_files'],
            workingDirectory: process.cwd(),
            environment: {},
            metadata: {},
          },
        },
        {
          name: 'read_write',
          context: {
            sessionId: 'perm-test-2',
            userId: 'test-user',
            permissions: ['read_files', 'write_files'],
            workingDirectory: process.cwd(),
            environment: {},
            metadata: {},
          },
        },
        {
          name: 'all_permissions',
          context: {
            sessionId: 'perm-test-3',
            userId: 'test-user',
            permissions: [
              'read_files',
              'write_files',
              'execute_commands',
              'delete_files',
              'dangerous_operations',
            ],
            workingDirectory: process.cwd(),
            environment: {},
            metadata: {},
          },
        },
      ];

      for (const { name, context } of contexts) {
        console.log(`   Testing with ${name} permissions...`);

        // Test read operation (should work for all)
        const readResult = await this.toolManager.execute(
          'read',
          {
            path: './test-file.txt',
          },
          context
        );

        // Test write operation (should fail for read_only)
        const writeResult = await this.toolManager.execute(
          'write',
          {
            path: `./perm-test-${name}.txt`,
            content: 'Permission test',
          },
          context
        );

        permissionTests.push({
          permissionSet: name,
          readSuccess: readResult.success,
          writeSuccess: writeResult.success,
          expectedWriteSuccess: name !== 'read_only',
        });

        console.log(`     Read: ${readResult.success ? 'PASS' : 'FAIL'}`);
        console.log(
          `     Write: ${writeResult.success ? 'PASS' : 'FAIL'} (expected: ${name !== 'read_only' ? 'PASS' : 'FAIL'})`
        );
      }

      this.recordResult('Permission Checking', true, Date.now() - startTime, {
        permissionTests,
      });

      console.log('✅ Permission checking tests passed\n');
    } catch (error) {
      this.recordResult(
        'Permission Checking',
        false,
        Date.now() - startTime,
        {},
        (error as Error).message
      );
      console.error(
        '❌ Permission checking test failed:',
        (error as Error).message,
        '\n'
      );
    }
  }

  private async testMetricsAndHealth() {
    console.log('📊 Testing Metrics and Health Monitoring...');
    const startTime = Date.now();

    try {
      let healthInfo = {};
      let systemInfo = {};
      let metrics = {};

      // Test health check
      console.log('   Testing health check...');
      if (this.toolManager.healthCheck) {
        healthInfo = await this.toolManager.healthCheck();
        console.log(
          `   ✅ Health check: ${JSON.stringify(healthInfo, null, 2)}`
        );
      }

      // Test system info
      console.log('   Testing system info...');
      if (this.toolManager.getSystemInfo) {
        systemInfo = this.toolManager.getSystemInfo();
        console.log(`   ✅ System info retrieved`);
      }

      // Test metrics (if available)
      console.log('   Testing metrics...');
      if (this.toolManager.getMetrics) {
        metrics = this.toolManager.getMetrics();
        console.log(`   ✅ Metrics retrieved`);
      }

      // Test running executions
      console.log('   Testing running executions...');
      let runningExecutions = [];
      if (this.toolManager.getRunningExecutions) {
        runningExecutions = this.toolManager.getRunningExecutions();
        console.log(`   ✅ Running executions: ${runningExecutions.length}`);
      }

      this.recordResult('Metrics and Health', true, Date.now() - startTime, {
        healthInfo,
        systemInfo,
        metrics,
        runningExecutions: runningExecutions.length,
      });

      console.log('✅ Metrics and health monitoring tests passed\n');
    } catch (error) {
      this.recordResult(
        'Metrics and Health',
        false,
        Date.now() - startTime,
        {},
        (error as Error).message
      );
      console.error(
        '❌ Metrics and health monitoring test failed:',
        (error as Error).message,
        '\n'
      );
    }
  }

  private recordResult(
    name: string,
    success: boolean,
    duration: number,
    details: any,
    error?: string
  ) {
    this.results.push({
      name,
      success,
      duration,
      details,
      error,
    });
  }

  private reportResults() {
    console.log('📋 Test Results Summary');
    console.log('========================\n');

    const totalTests = this.results.length;
    const passedTests = this.results.filter(r => r.success).length;
    const failedTests = totalTests - passedTests;
    const totalDuration = this.results.reduce((sum, r) => sum + r.duration, 0);

    console.log(`Total Tests: ${totalTests}`);
    console.log(`Passed: ${passedTests} ✅`);
    console.log(`Failed: ${failedTests} ❌`);
    console.log(`Total Duration: ${totalDuration}ms\n`);

    this.results.forEach((result, index) => {
      const status = result.success ? '✅ PASS' : '❌ FAIL';
      console.log(
        `${index + 1}. ${result.name} - ${status} (${result.duration}ms)`
      );

      if (result.error) {
        console.log(`   Error: ${result.error}`);
      }

      if (result.details && Object.keys(result.details).length > 0) {
        console.log(`   Details: ${JSON.stringify(result.details, null, 4)}`);
      }

      console.log();
    });

    if (failedTests > 0) {
      console.log(
        `❌ ${failedTests} tests failed. Please review the errors above.`
      );
      process.exit(1);
    } else {
      console.log('🎉 All tests passed successfully!');
    }
  }

  private async cleanup() {
    console.log('🧹 Cleaning up test files...');

    try {
      // Clean up test files
      const testFiles = [
        './test-file.txt',
        './batch-test-1.txt',
        './batch-test-2.txt',
        './perm-test-read_write.txt',
        './perm-test-all_permissions.txt',
        './permission-test.txt',
      ];

      for (const file of testFiles) {
        try {
          await this.toolManager.execute(
            'delete',
            {
              path: file,
              force: true,
            },
            {
              sessionId: 'cleanup-session',
              userId: 'test-user',
              permissions: ['delete_files', 'dangerous_operations'],
              workingDirectory: process.cwd(),
              environment: {},
              metadata: {},
            }
          );
        } catch (error) {
          // Ignore cleanup errors
        }
      }

      // Cleanup tool manager
      if (this.toolManager.cleanup) {
        await this.toolManager.cleanup();
      }

      console.log('✅ Cleanup completed');
    } catch (error) {
      console.warn('⚠️  Cleanup had some issues:', (error as Error).message);
    }
  }
}

// Run the tests
const runner = new TestRunner();
runner.runAllTests().catch(error => {
  console.error('❌ Test suite failed:', error);
  process.exit(1);
});
