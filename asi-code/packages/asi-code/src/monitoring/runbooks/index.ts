/**
 * Runbook Automation System for ASI-Code
 * 
 * Automated response system for common operational issues:
 * - Automatic remediation scripts
 * - Escalation procedures
 * - Diagnostic information gathering
 * - Recovery procedures
 * - Documentation generation
 */

import { EventEmitter } from 'eventemitter3';
import { spawn } from 'child_process';
import * as fs from 'fs/promises';
import * as path from 'path';

export interface RunbookStep {
  id: string;
  name: string;
  description: string;
  type: 'diagnostic' | 'remediation' | 'escalation' | 'notification';
  command?: string;
  script?: string;
  timeout?: number;
  retries?: number;
  conditions?: string[];
  metadata?: Record<string, any>;
}

export interface RunbookExecution {
  id: string;
  runbookName: string;
  alertName: string;
  triggeredBy: string;
  startTime: number;
  endTime?: number;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  steps: RunbookStepExecution[];
  metadata: Record<string, any>;
}

export interface RunbookStepExecution {
  stepId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  startTime?: number;
  endTime?: number;
  output?: string;
  error?: string;
  retryCount: number;
}

export interface Runbook {
  name: string;
  description: string;
  triggers: string[]; // Alert names that trigger this runbook
  steps: RunbookStep[];
  enabled: boolean;
  priority: number;
  timeout: number;
  metadata: Record<string, any>;
}

export class RunbookAutomation extends EventEmitter {
  private readonly runbooks: Map<string, Runbook> = new Map();
  private readonly executions: Map<string, RunbookExecution> = new Map();
  private readonly runbookDirectory: string;
  
  constructor(runbookDirectory = './runbooks') {
    super();
    this.runbookDirectory = runbookDirectory;
    this.initializeDefaultRunbooks();
  }
  
  private initializeDefaultRunbooks(): void {
    // High CPU Usage Runbook
    this.addRunbook({
      name: 'high-cpu-remediation',
      description: 'Automated response to high CPU usage',
      triggers: ['HighCPUUsage', 'CriticalCPUUsage'],
      enabled: true,
      priority: 1,
      timeout: 300000, // 5 minutes
      steps: [
        {
          id: 'gather-cpu-info',
          name: 'Gather CPU Information',
          description: 'Collect detailed CPU usage information',
          type: 'diagnostic',
          command: 'top -n 1 -b',
          timeout: 10000,
        },
        {
          id: 'check-processes',
          name: 'Check Top Processes',
          description: 'Identify processes consuming most CPU',
          type: 'diagnostic',
          command: 'ps aux --sort=-%cpu | head -20',
          timeout: 10000,
        },
        {
          id: 'check-load-average',
          name: 'Check Load Average',
          description: 'Check system load average',
          type: 'diagnostic',
          command: 'uptime',
          timeout: 5000,
        },
        {
          id: 'restart-high-cpu-services',
          name: 'Restart High CPU Services',
          description: 'Restart services consuming excessive CPU',
          type: 'remediation',
          script: `
            # Check if ASI-Code process is consuming high CPU
            CPU_USAGE=$(ps -o pid,pcpu,comm -C node | grep -v PID | sort -k2 -nr | head -1 | awk '{print $2}')
            if (( $(echo "$CPU_USAGE > 80" | bc -l) )); then
              echo "High CPU usage detected: $CPU_USAGE%"
              echo "Restarting ASI-Code service..."
              systemctl restart asi-code
            fi
          `,
          timeout: 60000,
          conditions: ['cpu_usage > 90'],
        },
        {
          id: 'scale-up',
          name: 'Scale Up Resources',
          description: 'Scale up the service if running in Kubernetes',
          type: 'remediation',
          script: `
            if kubectl get deployment asi-code &>/dev/null; then
              echo "Scaling up ASI-Code deployment..."
              kubectl scale deployment asi-code --replicas=3
            fi
          `,
          timeout: 30000,
          conditions: ['kubernetes_deployment_exists'],
        },
        {
          id: 'notify-team',
          name: 'Notify Engineering Team',
          description: 'Send notification to engineering team',
          type: 'notification',
          script: 'curl -X POST "$SLACK_WEBHOOK_URL" -d "{\\"text\\": \\"High CPU usage detected and remediation attempted\\"}"',
          timeout: 10000,
        },
      ],
      metadata: {
        documentation: 'https://docs.asi-code.com/runbooks/high-cpu',
      },
    });
    
    // Service Down Runbook
    this.addRunbook({
      name: 'service-down-recovery',
      description: 'Automated recovery for service downtime',
      triggers: ['ServiceDown', 'HealthCheckFailing'],
      enabled: true,
      priority: 1,
      timeout: 600000, // 10 minutes
      steps: [
        {
          id: 'check-service-status',
          name: 'Check Service Status',
          description: 'Check the current status of ASI-Code service',
          type: 'diagnostic',
          command: 'systemctl status asi-code',
          timeout: 10000,
        },
        {
          id: 'check-logs',
          name: 'Check Recent Logs',
          description: 'Check recent error logs',
          type: 'diagnostic',
          command: 'journalctl -u asi-code --since "5 minutes ago" --no-pager',
          timeout: 15000,
        },
        {
          id: 'check-disk-space',
          name: 'Check Disk Space',
          description: 'Ensure sufficient disk space is available',
          type: 'diagnostic',
          command: 'df -h',
          timeout: 5000,
        },
        {
          id: 'check-memory',
          name: 'Check Memory Usage',
          description: 'Check if system has sufficient memory',
          type: 'diagnostic',
          command: 'free -h',
          timeout: 5000,
        },
        {
          id: 'restart-service',
          name: 'Restart Service',
          description: 'Attempt to restart the ASI-Code service',
          type: 'remediation',
          command: 'systemctl restart asi-code',
          timeout: 60000,
          retries: 2,
        },
        {
          id: 'verify-restart',
          name: 'Verify Service Recovery',
          description: 'Verify that the service is running after restart',
          type: 'diagnostic',
          command: 'curl -f http://localhost:3000/health || exit 1',
          timeout: 30000,
          retries: 3,
        },
        {
          id: 'escalate-to-oncall',
          name: 'Escalate to On-Call',
          description: 'Escalate to on-call engineer if restart failed',
          type: 'escalation',
          script: `
            echo "Service restart failed, escalating to on-call engineer"
            curl -X POST "$PAGERDUTY_API_URL" \\
              -H "Authorization: Token $PAGERDUTY_TOKEN" \\
              -H "Content-Type: application/json" \\
              -d '{
                "routing_key": "$PAGERDUTY_INTEGRATION_KEY",
                "event_action": "trigger",
                "payload": {
                  "summary": "ASI-Code service down - automated recovery failed",
                  "severity": "critical",
                  "source": "runbook-automation"
                }
              }'
          `,
          timeout: 10000,
          conditions: ['service_restart_failed'],
        },
      ],
      metadata: {
        documentation: 'https://docs.asi-code.com/runbooks/service-down',
      },
    });
    
    // High Error Rate Runbook
    this.addRunbook({
      name: 'high-error-rate-investigation',
      description: 'Investigate and mitigate high error rates',
      triggers: ['HighErrorRate', 'CriticalErrorRate'],
      enabled: true,
      priority: 2,
      timeout: 300000, // 5 minutes
      steps: [
        {
          id: 'analyze-error-patterns',
          name: 'Analyze Error Patterns',
          description: 'Analyze recent error patterns and types',
          type: 'diagnostic',
          script: `
            echo "Recent error patterns:"
            journalctl -u asi-code --since "10 minutes ago" | grep -i error | tail -20
            echo "\\nError distribution:"
            journalctl -u asi-code --since "10 minutes ago" | grep -i error | awk '{print $6}' | sort | uniq -c
          `,
          timeout: 30000,
        },
        {
          id: 'check-dependencies',
          name: 'Check External Dependencies',
          description: 'Check status of external dependencies',
          type: 'diagnostic',
          script: `
            echo "Checking database connectivity..."
            timeout 5 pg_isready -h localhost -p 5432 || echo "Database connection failed"
            
            echo "Checking external APIs..."
            timeout 5 curl -f https://api.anthropic.com/health || echo "Anthropic API unreachable"
            timeout 5 curl -f https://api.openai.com/health || echo "OpenAI API unreachable"
          `,
          timeout: 20000,
        },
        {
          id: 'restart-failing-components',
          name: 'Restart Failing Components',
          description: 'Restart components with high error rates',
          type: 'remediation',
          script: `
            # Check if errors are concentrated in specific components
            ERROR_COMPONENT=$(journalctl -u asi-code --since "5 minutes ago" | grep -i error | grep -o "component:[a-zA-Z]*" | sort | uniq -c | sort -nr | head -1 | awk '{print $2}')
            
            if [[ "$ERROR_COMPONENT" == "component:provider" ]]; then
              echo "Restarting provider connections..."
              curl -X POST http://localhost:3000/admin/restart-providers
            elif [[ "$ERROR_COMPONENT" == "component:tool" ]]; then
              echo "Clearing tool cache..."
              curl -X POST http://localhost:3000/admin/clear-tool-cache
            fi
          `,
          timeout: 30000,
        },
        {
          id: 'enable-circuit-breaker',
          name: 'Enable Circuit Breaker',
          description: 'Enable circuit breaker for failing services',
          type: 'remediation',
          script: `
            echo "Enabling circuit breaker for external services..."
            curl -X POST http://localhost:3000/admin/circuit-breaker/enable
          `,
          timeout: 10000,
        },
        {
          id: 'notify-engineering',
          name: 'Notify Engineering Team',
          description: 'Notify engineering team of high error rate',
          type: 'notification',
          script: `
            ERROR_RATE=$(curl -s "http://localhost:9090/api/v1/query?query=rate(asi_code_errors_total[5m])" | jq -r '.data.result[0].value[1]')
            curl -X POST "$SLACK_WEBHOOK_URL" -d "{\\"text\\": \\"High error rate detected: $ERROR_RATE errors/sec. Automated mitigation attempted.\\"}"
          `,
          timeout: 10000,
        },
      ],
      metadata: {
        documentation: 'https://docs.asi-code.com/runbooks/high-error-rate',
      },
    });
    
    // Memory Leak Detection Runbook
    this.addRunbook({
      name: 'memory-leak-investigation',
      description: 'Investigate and handle memory leaks',
      triggers: ['HighMemoryUsage', 'CriticalMemoryUsage'],
      enabled: true,
      priority: 2,
      timeout: 600000, // 10 minutes
      steps: [
        {
          id: 'memory-snapshot',
          name: 'Take Memory Snapshot',
          description: 'Capture current memory usage details',
          type: 'diagnostic',
          script: `
            echo "=== Memory Usage Summary ==="
            free -h
            echo "\\n=== Process Memory Usage ==="
            ps aux --sort=-%mem | head -20
            echo "\\n=== ASI-Code Process Details ==="
            pgrep -f asi-code | xargs -I {} ps -o pid,vsz,rss,pmem,comm -p {}
          `,
          timeout: 15000,
        },
        {
          id: 'heap-dump',
          name: 'Generate Heap Dump',
          description: 'Generate heap dump for analysis (if Node.js)',
          type: 'diagnostic',
          script: `
            ASI_PID=$(pgrep -f asi-code | head -1)
            if [ ! -z "$ASI_PID" ]; then
              echo "Generating heap dump for PID $ASI_PID..."
              kill -USR2 $ASI_PID
              echo "Heap dump generated"
            fi
          `,
          timeout: 30000,
        },
        {
          id: 'check-memory-leaks',
          name: 'Check for Memory Leaks',
          description: 'Analyze memory growth patterns',
          type: 'diagnostic',
          script: `
            echo "Memory growth analysis:"
            # Check memory usage trend over last hour
            journalctl -u asi-code --since "1 hour ago" | grep -i "memory\\|heap" | tail -10
          `,
          timeout: 20000,
        },
        {
          id: 'garbage-collection',
          name: 'Force Garbage Collection',
          description: 'Trigger garbage collection if possible',
          type: 'remediation',
          script: `
            echo "Triggering garbage collection..."
            curl -X POST http://localhost:3000/admin/gc || echo "GC endpoint not available"
          `,
          timeout: 15000,
        },
        {
          id: 'restart-if-critical',
          name: 'Restart if Critical',
          description: 'Restart service if memory usage is critical',
          type: 'remediation',
          script: `
            MEMORY_PERCENT=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
            if [ "$MEMORY_PERCENT" -gt 95 ]; then
              echo "Critical memory usage ($MEMORY_PERCENT%), restarting service..."
              systemctl restart asi-code
            else
              echo "Memory usage is $MEMORY_PERCENT%, within acceptable range"
            fi
          `,
          timeout: 60000,
        },
      ],
      metadata: {
        documentation: 'https://docs.asi-code.com/runbooks/memory-leak',
      },
    });
  }
  
  addRunbook(runbook: Runbook): void {
    this.runbooks.set(runbook.name, runbook);
    this.emit('runbook-added', runbook);
  }
  
  async executeRunbook(runbookName: string, alertName: string, triggeredBy: string, metadata: Record<string, any> = {}): Promise<RunbookExecution> {
    const runbook = this.runbooks.get(runbookName);
    if (!runbook) {
      throw new Error(`Runbook not found: ${runbookName}`);
    }
    
    if (!runbook.enabled) {
      throw new Error(`Runbook is disabled: ${runbookName}`);
    }
    
    const execution: RunbookExecution = {
      id: this.generateExecutionId(),
      runbookName,
      alertName,
      triggeredBy,
      startTime: Date.now(),
      status: 'running',
      steps: runbook.steps.map(step => ({
        stepId: step.id,
        status: 'pending',
        retryCount: 0,
      })),
      metadata,
    };
    
    this.executions.set(execution.id, execution);
    this.emit('runbook-started', execution);
    
    try {
      await this.executeSteps(runbook, execution);
      execution.status = 'completed';
      execution.endTime = Date.now();
      this.emit('runbook-completed', execution);
    } catch (error) {
      execution.status = 'failed';
      execution.endTime = Date.now();
      execution.metadata.error = error instanceof Error ? error.message : 'Unknown error';
      this.emit('runbook-failed', execution);
    }
    
    return execution;
  }
  
  private async executeSteps(runbook: Runbook, execution: RunbookExecution): Promise<void> {
    for (let i = 0; i < runbook.steps.length; i++) {
      const step = runbook.steps[i];
      const stepExecution = execution.steps[i];
      
      // Check if we should skip this step based on conditions
      if (step.conditions && !this.evaluateConditions(step.conditions, execution.metadata)) {
        stepExecution.status = 'skipped';
        continue;
      }
      
      stepExecution.status = 'running';
      stepExecution.startTime = Date.now();
      
      this.emit('runbook-step-started', { execution, step, stepExecution });
      
      try {
        const result = await this.executeStep(step, execution.metadata);
        stepExecution.output = result.output;
        stepExecution.status = 'completed';
        stepExecution.endTime = Date.now();
        
        // Update execution metadata with step results
        execution.metadata[`${step.id}_output`] = result.output;
        execution.metadata[`${step.id}_success`] = true;
        
        this.emit('runbook-step-completed', { execution, step, stepExecution });
      } catch (error) {
        stepExecution.error = error instanceof Error ? error.message : 'Unknown error';
        stepExecution.endTime = Date.now();
        
        // Retry logic
        if (step.retries && stepExecution.retryCount < step.retries) {
          stepExecution.retryCount++;
          i--; // Retry current step
          continue;
        }
        
        stepExecution.status = 'failed';
        execution.metadata[`${step.id}_success`] = false;
        
        this.emit('runbook-step-failed', { execution, step, stepExecution });
        
        // Stop execution on critical failures
        if (step.type === 'remediation') {
          throw error;
        }
      }
    }
  }
  
  private async executeStep(step: RunbookStep, metadata: Record<string, any>): Promise<{ output: string }> {
    const timeout = step.timeout || 30000;
    
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(`Step timeout after ${timeout}ms`));
      }, timeout);
      
      let command: string;
      
      if (step.command) {
        command = this.interpolateVariables(step.command, metadata);
      } else if (step.script) {
        command = this.interpolateVariables(step.script, metadata);
      } else {
        clearTimeout(timer);
        resolve({ output: 'No command or script specified' });
        return;
      }
      
      const child = spawn('bash', ['-c', command], {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, ...metadata },
      });
      
      let output = '';
      let error = '';
      
      child.stdout?.on('data', (data) => {
        output += data.toString();
      });
      
      child.stderr?.on('data', (data) => {
        error += data.toString();
      });
      
      child.on('close', (code) => {
        clearTimeout(timer);
        
        if (code === 0) {
          resolve({ output: output.trim() });
        } else {
          reject(new Error(`Command failed with code ${code}: ${error.trim()}`));
        }
      });
      
      child.on('error', (err) => {
        clearTimeout(timer);
        reject(err);
      });
    });
  }
  
  private interpolateVariables(text: string, variables: Record<string, any>): string {
    return text.replace(/\$\{([^}]+)\}/g, (match, varName) => {
      return variables[varName] || match;
    });
  }
  
  private evaluateConditions(conditions: string[], metadata: Record<string, any>): boolean {
    return conditions.every(condition => {
      // Simple condition evaluation
      // In a real implementation, you'd want a more sophisticated expression evaluator
      if (condition.includes('>')) {
        const [left, right] = condition.split('>').map(s => s.trim());
        const leftValue = metadata[left] || parseFloat(left);
        const rightValue = parseFloat(right);
        return leftValue > rightValue;
      }
      
      if (condition.includes('==')) {
        const [left, right] = condition.split('==').map(s => s.trim());
        return metadata[left] === right;
      }
      
      // Check if variable exists and is truthy
      return !!metadata[condition];
    });
  }
  
  private generateExecutionId(): string {
    return `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
  
  // Alert integration
  async handleAlert(alertName: string, alertData: Record<string, any>): Promise<RunbookExecution[]> {
    const executions: RunbookExecution[] = [];
    
    // Find runbooks that should be triggered by this alert
    const triggeredRunbooks = Array.from(this.runbooks.values())
      .filter(runbook => runbook.enabled && runbook.triggers.includes(alertName))
      .sort((a, b) => a.priority - b.priority);
    
    for (const runbook of triggeredRunbooks) {
      try {
        const execution = await this.executeRunbook(
          runbook.name,
          alertName,
          'alert-manager',
          alertData
        );
        executions.push(execution);
        
        // If a high-priority runbook succeeds, we might skip lower priority ones
        if (runbook.priority === 1 && execution.status === 'completed') {
          break;
        }
      } catch (error) {
        console.error(`Failed to execute runbook ${runbook.name}:`, error);
      }
    }
    
    return executions;
  }
  
  // Management methods
  
  getRunbooks(): Runbook[] {
    return Array.from(this.runbooks.values());
  }
  
  getExecution(executionId: string): RunbookExecution | undefined {
    return this.executions.get(executionId);
  }
  
  getRecentExecutions(limit = 50): RunbookExecution[] {
    return Array.from(this.executions.values())
      .sort((a, b) => b.startTime - a.startTime)
      .slice(0, limit);
  }
  
  getExecutionsByRunbook(runbookName: string): RunbookExecution[] {
    return Array.from(this.executions.values())
      .filter(exec => exec.runbookName === runbookName)
      .sort((a, b) => b.startTime - a.startTime);
  }
  
  enableRunbook(runbookName: string): boolean {
    const runbook = this.runbooks.get(runbookName);
    if (runbook) {
      runbook.enabled = true;
      return true;
    }
    return false;
  }
  
  disableRunbook(runbookName: string): boolean {
    const runbook = this.runbooks.get(runbookName);
    if (runbook) {
      runbook.enabled = false;
      return true;
    }
    return false;
  }
  
  // Reporting
  
  getExecutionStatistics(): {
    total: number;
    successful: number;
    failed: number;
    running: number;
    averageDuration: number;
    byRunbook: Record<string, { count: number; successRate: number }>;
  } {
    const executions = Array.from(this.executions.values());
    const completed = executions.filter(e => e.endTime);
    
    const stats = {
      total: executions.length,
      successful: executions.filter(e => e.status === 'completed').length,
      failed: executions.filter(e => e.status === 'failed').length,
      running: executions.filter(e => e.status === 'running').length,
      averageDuration: completed.length > 0 
        ? completed.reduce((sum, e) => sum + (e.endTime! - e.startTime), 0) / completed.length
        : 0,
      byRunbook: {} as Record<string, { count: number; successRate: number }>,
    };
    
    // Group by runbook
    const byRunbook = new Map<string, RunbookExecution[]>();
    executions.forEach(exec => {
      const list = byRunbook.get(exec.runbookName) || [];
      list.push(exec);
      byRunbook.set(exec.runbookName, list);
    });
    
    byRunbook.forEach((execs, runbookName) => {
      const successful = execs.filter(e => e.status === 'completed').length;
      stats.byRunbook[runbookName] = {
        count: execs.length,
        successRate: execs.length > 0 ? (successful / execs.length) * 100 : 0,
      };
    });
    
    return stats;
  }
}

export function createRunbookAutomation(runbookDirectory?: string): RunbookAutomation {
  return new RunbookAutomation(runbookDirectory);
}