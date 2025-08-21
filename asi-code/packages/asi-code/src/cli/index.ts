#!/usr/bin/env node

/**
 * ASI-Code CLI - Command Line Interface
 * 
 * Main CLI entry point for the ASI-Code system.
 */

import { Command } from 'commander';
import { readFileSync } from 'fs';
import { join } from 'path';
import chalk from 'chalk';
import ora from 'ora';

// Import core modules
import { createMinimalASICode } from '../index.js';
import { AppContext } from '../app/app-context.js';
import { createLogManager } from '../logging/log-manager.js';
import { createConfigManager } from '../config/config-manager.js';
import { createEventBus } from '../bus/index.js';
import { createProviderManager } from '../provider/index.js';
import { createToolManager } from '../tool/index.js';
import { createSessionStorage, createSessionManager } from '../session/index.js';
import { createConsciousnessEngine, defaultConsciousnessConfig } from '../consciousness/index.js';
import { createAgentManager } from '../agent/index.js';
import { createPermissionManager } from '../permission/index.js';
import { createSATEngine } from '../sat/index.js';
import { createASIServer, defaultServerConfig } from '../server/index.js';

import type { ProviderConfig, ASICodeConfig } from '../index.js';

const program = new Command();

// Read package.json for version
let packageJson: any = {};
try {
  const packagePath = join(import.meta.url.replace('file://', '').replace('/src/cli/index.js', ''), '../../package.json');
  packageJson = JSON.parse(readFileSync(packagePath, 'utf8'));
} catch (error) {
  packageJson = { version: '0.1.0' };
}

program
  .name('asi-code')
  .description('ASI-Code - Advanced Software Intelligence Code Generation and Analysis Platform')
  .version(packageJson.version || '0.1.0');

// Initialize command
program
  .command('init')
  .description('Initialize ASI-Code in the current directory')
  .option('-p, --provider <provider>', 'AI provider (anthropic|openai)', 'anthropic')
  .option('-m, --model <model>', 'AI model to use')
  .option('-k, --api-key <key>', 'API key for the provider')
  .action(async (options) => {
    const spinner = ora('Initializing ASI-Code...').start();
    
    try {
      const configManager = createConfigManager();
      
      // Set provider configuration
      const providerConfig: ProviderConfig = {
        name: 'default',
        type: options.provider,
        apiKey: options.apiKey || process.env.ANTHROPIC_API_KEY || process.env.OPENAI_API_KEY || '',
        model: options.model || (options.provider === 'anthropic' ? 'claude-3-sonnet-20240229' : 'gpt-4')
      };

      configManager.set('providers.default', providerConfig);
      await configManager.save('./asi-code.config.yml');
      
      spinner.succeed('ASI-Code initialized successfully!');
      console.log(chalk.green('Configuration saved to asi-code.config.yml'));
      console.log(chalk.blue('Run "asi-code start" to start the server'));
    } catch (error) {
      spinner.fail('Failed to initialize ASI-Code');
      console.error(chalk.red((error as Error).message));
      process.exit(1);
    }
  });

// Start server command
program
  .command('start')
  .description('Start the ASI-Code server')
  .option('-p, --port <port>', 'Server port', '3000')
  .option('-h, --host <host>', 'Server host', 'localhost')
  .option('-c, --config <config>', 'Configuration file', './asi-code.config.yml')
  .action(async (options) => {
    const spinner = ora('Starting ASI-Code server...').start();
    
    try {
      // Load configuration
      const configManager = createConfigManager();
      try {
        await configManager.load(options.config);
        spinner.text = 'Configuration loaded';
      } catch (error) {
        spinner.warn('No configuration file found, using defaults');
      }

      // Create core managers
      const eventBus = createEventBus();
      const providerManager = createProviderManager();
      const toolManager = createToolManager();
      const sessionStorage = createSessionStorage('memory');
      const sessionManager = createSessionManager(sessionStorage);
      const consciousnessEngine = createConsciousnessEngine(defaultConsciousnessConfig);
      const agentManager = createAgentManager();
      const permissionManager = createPermissionManager();

      // Register providers from config
      const defaultProvider = configManager.get('providers.default') as ProviderConfig;
      if (defaultProvider) {
        await providerManager.register(defaultProvider);
        await consciousnessEngine.initialize(providerManager.get('default')!);
      }

      // Create and start server
      const serverConfig = {
        ...defaultServerConfig,
        port: parseInt(options.port),
        host: options.host
      };

      const server = createASIServer(serverConfig, sessionManager, providerManager, toolManager);
      
      // Setup event listeners
      server.on('server:started', ({ host, port }) => {
        spinner.succeed(`ASI-Code server started on http://${host}:${port}`);
        console.log(chalk.green('✓ Kenny Integration Pattern initialized'));
        console.log(chalk.green('✓ Consciousness Engine active'));
        console.log(chalk.green('✓ Provider system ready'));
        console.log(chalk.green('✓ Tool system ready'));
        console.log(chalk.blue('\nAPI endpoints:'));
        console.log(`  GET  http://${host}:${port}/health`);
        console.log(`  POST http://${host}:${port}/api/sessions`);
        console.log(`  GET  http://${host}:${port}/api/events (SSE)`);
        console.log(chalk.yellow('\nPress Ctrl+C to stop the server'));
      });

      server.on('server:stopped', () => {
        console.log(chalk.yellow('ASI-Code server stopped'));
      });

      await server.start();

      // Handle graceful shutdown
      process.on('SIGINT', async () => {
        console.log(chalk.yellow('\nShutting down ASI-Code server...'));
        await server.stop();
        await sessionManager.cleanup();
        await providerManager.cleanup();
        await toolManager.cleanup();
        await consciousnessEngine.cleanup();
        await agentManager.cleanup();
        await permissionManager.cleanup();
        await eventBus.cleanup();
        process.exit(0);
      });

    } catch (error) {
      spinner.fail('Failed to start ASI-Code server');
      console.error(chalk.red((error as Error).message));
      process.exit(1);
    }
  });

// Analyze project command
program
  .command('analyze')
  .description('Analyze project architecture with SAT (Software Architecture Taskforce)')
  .argument('[path]', 'Project path to analyze', '.')
  .option('-o, --output <file>', 'Output file for analysis results')
  .option('-f, --format <format>', 'Output format (json|yaml|text)', 'text')
  .action(async (path, options) => {
    const spinner = ora('Analyzing project architecture...').start();
    
    try {
      const satEngine = createSATEngine();
      const analysis = await satEngine.analyzeProject(path);
      
      spinner.succeed('Architecture analysis completed');
      
      // Display results
      console.log(chalk.blue('\n🏗️  Architecture Analysis Results\n'));
      console.log(chalk.green(`Project: ${analysis.projectPath}`));
      console.log(chalk.green(`Analysis time: ${analysis.timestamp.toISOString()}\n`));
      
      // Patterns
      console.log(chalk.blue('📋 Detected Patterns:'));
      if (analysis.patterns.length > 0) {
        analysis.patterns.forEach(pattern => {
          const confidence = pattern.confidence.toFixed(1);
          console.log(`  • ${pattern.name} (${confidence}% confidence)`);
          console.log(`    ${chalk.gray(pattern.description)}`);
        });
      } else {
        console.log(chalk.yellow('  No clear patterns detected'));
      }
      
      // Metrics
      console.log(chalk.blue('\n📊 Code Metrics:'));
      console.log(`  • Lines of Code: ${analysis.metrics.linesOfCode.toLocaleString()}`);
      console.log(`  • Cyclomatic Complexity: ${analysis.metrics.cyclomaticComplexity}`);
      console.log(`  • Dependencies: ${analysis.metrics.dependencies.length}`);
      console.log(`  • Coupling: ${analysis.metrics.coupling}`);
      console.log(`  • Cohesion: ${analysis.metrics.cohesion}%`);
      
      // Recommendations
      console.log(chalk.blue('\n💡 Recommendations:'));
      analysis.recommendations.forEach(rec => {
        console.log(`  • ${rec}`);
      });
      
      // Save to file if requested
      if (options.output) {
        const content = options.format === 'json' 
          ? JSON.stringify(analysis, null, 2)
          : options.format === 'yaml'
            ? require('yaml').stringify(analysis)
            : `Architecture Analysis Report\n\n${JSON.stringify(analysis, null, 2)}`;
        
        require('fs').writeFileSync(options.output, content);
        console.log(chalk.green(`\nResults saved to ${options.output}`));
      }
      
    } catch (error) {
      spinner.fail('Architecture analysis failed');
      console.error(chalk.red((error as Error).message));
      process.exit(1);
    }
  });

// Session management commands
const sessionCmd = program
  .command('session')
  .description('Manage ASI-Code sessions');

sessionCmd
  .command('list')
  .description('List active sessions')
  .action(async () => {
    console.log(chalk.blue('Active Sessions:'));
    // TODO: Implement session listing
    console.log(chalk.yellow('Session management requires a running server'));
  });

// Provider management commands
const providerCmd = program
  .command('provider')
  .description('Manage AI providers');

providerCmd
  .command('list')
  .description('List configured providers')
  .action(async () => {
    console.log(chalk.blue('Configured Providers:'));
    // TODO: Implement provider listing
  });

// Tool management commands
const toolCmd = program
  .command('tool')
  .description('Manage tools');

toolCmd
  .command('list')
  .description('List available tools')
  .action(async () => {
    console.log(chalk.blue('Available Tools:'));
    const toolManager = createToolManager();
    const tools = toolManager.list();
    
    tools.forEach(tool => {
      console.log(`  • ${chalk.green(tool.name)} - ${tool.description}`);
      console.log(`    ${chalk.gray(`Category: ${tool.category}, Version: ${tool.version}`)}`);
    });
  });

// Version command (already handled by commander)

// Main function for external use
export async function main(args: string[] = process.argv.slice(2)): Promise<void> {
  try {
    await program.parseAsync(args);
  } catch (error) {
    console.error(chalk.red('CLI Error:', (error as Error).message));
    if (process.env.DEBUG) {
      console.error(error);
    }
    process.exit(1);
  }
}

// Parse command line arguments when run directly
if (import.meta.url === `file://${process.argv[1]}`) {
  await main();
}