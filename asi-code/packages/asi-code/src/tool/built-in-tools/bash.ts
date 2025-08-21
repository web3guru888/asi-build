/**
 * Bash Tool - Execute shell commands with safety controls
 * 
 * Provides secure execution of bash commands with permission checking,
 * timeout controls, and output capturing.
 */

import { spawn, exec } from 'child_process';
import { promisify } from 'util';
import { BaseTool, ToolDefinition, ToolExecutionContext, ToolResult } from '../base-tool.js';

const execAsync = promisify(exec);

export interface BashExecutionOptions {
  timeout?: number;
  cwd?: string;
  env?: Record<string, string>;
  shell?: string;
  maxBuffer?: number;
  captureStderr?: boolean;
  interactive?: boolean;
}

export class BashTool extends BaseTool {
  private readonly allowedCommands: Set<string>;
  private readonly blockedCommands: Set<string>;

  constructor() {
    const definition: ToolDefinition = {
      name: 'bash',
      description: 'Execute bash commands with safety controls and permission checking',
      parameters: [
        {
          name: 'command',
          type: 'string',
          description: 'The bash command to execute',
          required: true,
          validation: {
            custom: (value: string) => {
              if (!value.trim()) return 'Command cannot be empty';
              if (value.length > 1000) return 'Command too long (max 1000 characters)';
              return true;
            }
          }
        },
        {
          name: 'timeout',
          type: 'number',
          description: 'Timeout in milliseconds (default: 30000)',
          default: 30000,
          validation: {
            min: 1000,
            max: 300000 // 5 minutes max
          }
        },
        {
          name: 'cwd',
          type: 'string',
          description: 'Working directory for command execution',
        },
        {
          name: 'captureStderr',
          type: 'boolean',
          description: 'Whether to capture stderr separately',
          default: true
        },
        {
          name: 'shell',
          type: 'string',
          description: 'Shell to use for execution',
          default: '/bin/bash',
          enum: ['/bin/bash', '/bin/sh', '/usr/bin/zsh']
        }
      ],
      category: 'system',
      version: '1.0.0',
      author: 'ASI Team',
      permissions: ['execute_commands'],
      safetyLevel: 'high-risk',
      tags: ['system', 'execution', 'shell'],
      examples: [
        {
          description: 'List files in current directory',
          parameters: {
            command: 'ls -la'
          }
        },
        {
          description: 'Check disk usage with timeout',
          parameters: {
            command: 'df -h',
            timeout: 5000
          }
        }
      ]
    };

    super(definition);

    // Define allowed commands (whitelist approach for maximum safety)
    this.allowedCommands = new Set([
      'ls', 'pwd', 'echo', 'cat', 'head', 'tail', 'grep', 'find', 'wc', 'sort',
      'uniq', 'cut', 'awk', 'sed', 'df', 'du', 'ps', 'top', 'whoami', 'id',
      'date', 'uptime', 'which', 'whereis', 'file', 'stat', 'uname', 'hostname',
      'git', 'npm', 'node', 'python', 'python3', 'pip', 'pip3', 'bun', 'deno'
    ]);

    // Define blocked commands (extra protection)
    this.blockedCommands = new Set([
      'rm', 'rmdir', 'mv', 'cp', 'chmod', 'chown', 'sudo', 'su', 'passwd',
      'useradd', 'userdel', 'usermod', 'groupadd', 'groupdel', 'kill', 'killall',
      'pkill', 'reboot', 'shutdown', 'halt', 'init', 'systemctl', 'service',
      'mount', 'umount', 'fdisk', 'mkfs', 'fsck', 'dd', 'crontab', 'at',
      'exec', 'eval', 'source', '.', 'bash', 'sh', 'zsh'
    ]);
  }

  async execute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult> {
    const {
      command,
      timeout = 30000,
      cwd = context.workingDirectory,
      captureStderr = true,
      shell = '/bin/bash'
    } = parameters;

    const startTime = Date.now();

    try {
      // Safety checks
      const safetyCheck = this.performSafetyCheck(command, context);
      if (!safetyCheck.safe) {
        return {
          success: false,
          error: `Command blocked: ${safetyCheck.reason}`,
          performance: {
            executionTime: Date.now() - startTime
          }
        };
      }

      // Execute command
      const result = await this.executeCommand(command, {
        timeout,
        cwd,
        env: { ...process.env, ...context.environment },
        shell,
        captureStderr
      });

      this.emit('executed', {
        command: command.substring(0, 100), // Truncate for logging
        success: true,
        executionTime: Date.now() - startTime
      });

      return {
        success: true,
        data: {
          stdout: result.stdout,
          stderr: result.stderr,
          exitCode: result.exitCode,
          command,
          cwd,
          shell
        },
        performance: {
          executionTime: Date.now() - startTime,
          resourcesAccessed: [cwd]
        }
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      
      this.emit('error', {
        command: command.substring(0, 100),
        error: errorMessage,
        executionTime: Date.now() - startTime
      });

      return {
        success: false,
        error: `Command execution failed: ${errorMessage}`,
        performance: {
          executionTime: Date.now() - startTime
        }
      };
    }
  }

  private performSafetyCheck(command: string, context: ToolExecutionContext): { safe: boolean; reason?: string } {
    // Check for dangerous patterns
    const dangerousPatterns = [
      /rm\s+(-rf|--recursive|--force)/i,
      /sudo\s/i,
      /su\s/i,
      /chmod\s+777/i,
      />\s*\/dev\/(sda|sdb|sdc)/i,
      /mkfs\./i,
      /dd\s+if=/i,
      /:\(\)\{\s*:\|:\&\s*\}:/i, // Fork bomb
      /curl.*\|\s*(bash|sh)/i,
      /wget.*\|\s*(bash|sh)/i,
      /eval\s/i,
      /exec\s/i,
      /\$\(/i, // Command substitution
      /`.*`/i, // Backtick command substitution
    ];

    for (const pattern of dangerousPatterns) {
      if (pattern.test(command)) {
        return { safe: false, reason: 'Command contains dangerous pattern' };
      }
    }

    // Extract the main command (first word)
    const mainCommand = command.trim().split(/\s+/)[0];
    const baseCommand = mainCommand.split('/').pop() || mainCommand;

    // Check blocked commands
    if (this.blockedCommands.has(baseCommand)) {
      return { safe: false, reason: `Command '${baseCommand}' is blocked` };
    }

    // For high-risk operations, require dangerous_operations permission
    if (!context.permissions.includes('dangerous_operations')) {
      // Only allow whitelisted commands
      if (!this.allowedCommands.has(baseCommand)) {
        return { safe: false, reason: `Command '${baseCommand}' requires dangerous_operations permission` };
      }
    }

    // Check command length
    if (command.length > 1000) {
      return { safe: false, reason: 'Command too long' };
    }

    return { safe: true };
  }

  private async executeCommand(
    command: string, 
    options: BashExecutionOptions
  ): Promise<{ stdout: string; stderr: string; exitCode: number }> {
    const {
      timeout = 30000,
      cwd = process.cwd(),
      env = process.env,
      shell = '/bin/bash',
      maxBuffer = 1024 * 1024, // 1MB
      captureStderr = true
    } = options;

    return new Promise((resolve, reject) => {
      const child = spawn(shell, ['-c', command], {
        cwd,
        env,
        stdio: ['ignore', 'pipe', captureStderr ? 'pipe' : 'ignore'],
        timeout
      });

      let stdout = '';
      let stderr = '';

      child.stdout?.on('data', (data) => {
        stdout += data.toString();
        if (stdout.length > maxBuffer) {
          child.kill('SIGTERM');
          reject(new Error('Output buffer exceeded'));
        }
      });

      if (captureStderr && child.stderr) {
        child.stderr.on('data', (data) => {
          stderr += data.toString();
          if (stderr.length > maxBuffer) {
            child.kill('SIGTERM');
            reject(new Error('Error buffer exceeded'));
          }
        });
      }

      child.on('close', (code) => {
        resolve({
          stdout: stdout.trim(),
          stderr: stderr.trim(),
          exitCode: code || 0
        });
      });

      child.on('error', (error) => {
        reject(error);
      });

      // Setup timeout
      setTimeout(() => {
        if (!child.killed) {
          child.kill('SIGTERM');
          // Force kill after additional 5 seconds
          setTimeout(() => {
            if (!child.killed) {
              child.kill('SIGKILL');
            }
          }, 5000);
          reject(new Error(`Command timed out after ${timeout}ms`));
        }
      }, timeout);
    });
  }

  async beforeExecute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<void> {
    await super.beforeExecute(parameters, context);
    
    // Additional checks for bash execution
    if (!context.permissions.includes('execute_commands')) {
      throw new Error('Bash tool requires execute_commands permission');
    }

    // Log the command execution attempt
    console.log(`[BashTool] Executing command for user ${context.userId}: ${parameters.command.substring(0, 50)}...`);
  }
}

export default BashTool;