/**
 * Safety Protocols - Advanced AGI Safety Measures for ASI-Code
 * 
 * Implements comprehensive safety protocols to prevent harmful operations,
 * detect anomalous behavior, and enforce safety constraints on AI operations.
 */

import { EventEmitter } from 'eventemitter3';
import { nanoid } from 'nanoid';
import { getKennyIntegration } from '../kenny/integration.js';
import { SafetyLevel } from './permission-types.js';
import type {
  SafetyProtocol,
  SafetyTrigger,
  SafetyAction,
  PermissionRequest,
  PermissionResult,
  PermissionContext,
  SecurityViolationError,
  SafetyProtocolViolationError
} from './permission-types.js';

export interface SafetyIncident {
  id: string;
  type: 'safety_violation' | 'anomaly_detected' | 'escalation_required' | 'pattern_match';
  severity: 'low' | 'medium' | 'high' | 'critical';
  protocolId: string;
  triggerId: string;
  context: PermissionContext;
  details: Record<string, any>;
  timestamp: Date;
  resolved: boolean;
  resolvedAt?: Date;
  resolvedBy?: string;
  actions: SafetyActionResult[];
}

export interface SafetyActionResult {
  actionType: string;
  executed: boolean;
  timestamp: Date;
  result?: any;
  error?: string;
}

export interface SafetyMetrics {
  totalIncidents: number;
  incidentsBySeverity: Record<string, number>;
  incidentsByType: Record<string, number>;
  blockedOperations: number;
  suspendedSessions: number;
  escalatedIncidents: number;
  falsePositives: number;
  averageResponseTime: number;
  timeRange: {
    start: Date;
    end: Date;
  };
}

export interface SafetyProtocolConfig {
  enablePatternAnalysis?: boolean;
  enableAnomalyDetection?: boolean;
  enableBehaviorTracking?: boolean;
  maxIncidentHistory?: number;
  alertThresholds?: {
    highSeverityCount: number;
    criticalSeverityCount: number;
    timeWindow: number; // in milliseconds
  };
  autoResponse?: {
    enabled: boolean;
    criticalActionsEnabled: boolean;
    requireApproval: boolean;
  };
}

/**
 * Comprehensive safety protocol manager for AGI safety
 */
export class SafetyProtocolManager extends EventEmitter {
  private protocols = new Map<string, SafetyProtocol>();
  private incidents: SafetyIncident[] = [];
  private metrics: SafetyMetrics;
  private config: Required<SafetyProtocolConfig>;
  
  // Behavior tracking
  private userBehaviorPatterns = new Map<string, BehaviorPattern>();
  private suspiciousActivities = new Map<string, SuspiciousActivity>();
  private operationFrequency = new Map<string, OperationFrequency>();
  
  // Pattern analysis
  private dangerousPatterns: DangerousPattern[] = [];
  private anomalyDetector: AnomalyDetector;
  
  private initialized = false;
  private running = false;

  constructor(config: SafetyProtocolConfig = {}) {
    super();

    this.config = {
      enablePatternAnalysis: config.enablePatternAnalysis ?? true,
      enableAnomalyDetection: config.enableAnomalyDetection ?? true,
      enableBehaviorTracking: config.enableBehaviorTracking ?? true,
      maxIncidentHistory: config.maxIncidentHistory ?? 10000,
      alertThresholds: config.alertThresholds ?? {
        highSeverityCount: 5,
        criticalSeverityCount: 1,
        timeWindow: 300000 // 5 minutes
      },
      autoResponse: config.autoResponse ?? {
        enabled: true,
        criticalActionsEnabled: false,
        requireApproval: true
      }
    };

    this.metrics = this.createEmptyMetrics();
    this.anomalyDetector = new AnomalyDetector();
    
    this.initializeBuiltInProtocols();
    this.initializeDangerousPatterns();
  }

  async initialize(): Promise<void> {
    if (this.initialized) return;

    // Initialize anomaly detector
    if (this.config.enableAnomalyDetection) {
      await this.anomalyDetector.initialize();
    }

    this.initialized = true;
    this.emit('initialized');
  }

  async start(): Promise<void> {
    if (!this.initialized) {
      throw new Error('SafetyProtocolManager must be initialized before starting');
    }

    this.running = true;
    
    // Start monitoring timers
    this.startMonitoring();
    
    this.emit('started');
  }

  async stop(): Promise<void> {
    this.running = false;
    this.emit('stopped');
  }

  async shutdown(): Promise<void> {
    await this.stop();
    
    this.protocols.clear();
    this.incidents.length = 0;
    this.userBehaviorPatterns.clear();
    this.suspiciousActivities.clear();
    this.operationFrequency.clear();
    
    this.initialized = false;
    this.emit('shutdown');
  }

  /**
   * Check permission request against all safety protocols
   */
  async checkPermissionRequest(request: PermissionRequest, result: PermissionResult): Promise<void> {
    if (!this.running) return;

    const startTime = Date.now();

    try {
      // Update behavior tracking
      if (this.config.enableBehaviorTracking) {
        this.updateBehaviorTracking(request, result);
      }

      // Check pattern analysis
      if (this.config.enablePatternAnalysis) {
        await this.checkDangerousPatterns(request, result);
      }

      // Check anomaly detection
      if (this.config.enableAnomalyDetection) {
        await this.checkAnomalies(request, result);
      }

      // Check all safety protocols
      for (const protocol of this.protocols.values()) {
        if (protocol.enabled) {
          await this.checkProtocol(protocol, request, result);
        }
      }

      // Check for alert thresholds
      await this.checkAlertThresholds();

    } catch (error) {
      console.error('[SafetyProtocols] Error during safety check:', error);
      
      // Create incident for safety system failure
      const incident = await this.createIncident({
        type: 'safety_violation',
        severity: 'high',
        protocolId: 'system',
        triggerId: 'safety_check_failure',
        context: request.context,
        details: {
          error: error instanceof Error ? error.message : String(error),
          request: {
            permissionId: request.permissionId,
            resource: request.context.resource,
            operation: request.context.operation
          }
        }
      });

      this.emit('safety.error', { incident, error });
    }

    // Update metrics
    this.metrics.averageResponseTime = 
      (this.metrics.averageResponseTime + (Date.now() - startTime)) / 2;
  }

  /**
   * Add a custom safety protocol
   */
  async addProtocol(protocol: SafetyProtocol): Promise<void> {
    this.protocols.set(protocol.id, protocol);
    this.emit('protocol.added', { protocol });

    // Publish event
    const kenny = getKennyIntegration();
    await kenny.getMessageBus().publishSubsystem(
      'safety.protocol.added',
      'permission-manager',
      { protocolId: protocol.id, name: protocol.name, safetyLevel: protocol.safetyLevel }
    );
  }

  /**
   * Get safety incidents
   */
  getIncidents(filter?: {
    type?: string;
    severity?: string;
    resolved?: boolean;
    startTime?: Date;
    endTime?: Date;
    limit?: number;
  }): SafetyIncident[] {
    let filtered = this.incidents;

    if (filter) {
      filtered = filtered.filter(incident => {
        if (filter.type && incident.type !== filter.type) return false;
        if (filter.severity && incident.severity !== filter.severity) return false;
        if (filter.resolved !== undefined && incident.resolved !== filter.resolved) return false;
        if (filter.startTime && incident.timestamp < filter.startTime) return false;
        if (filter.endTime && incident.timestamp > filter.endTime) return false;
        return true;
      });

      if (filter.limit) {
        filtered = filtered.slice(-filter.limit);
      }
    }

    return filtered;
  }

  /**
   * Get safety metrics
   */
  getMetrics(): SafetyMetrics {
    return { ...this.metrics };
  }

  /**
   * Resolve an incident
   */
  async resolveIncident(incidentId: string, resolvedBy: string, notes?: string): Promise<void> {
    const incident = this.incidents.find(i => i.id === incidentId);
    if (!incident) {
      throw new Error(`Incident ${incidentId} not found`);
    }

    incident.resolved = true;
    incident.resolvedAt = new Date();
    incident.resolvedBy = resolvedBy;

    if (notes) {
      incident.details.resolutionNotes = notes;
    }

    this.emit('incident.resolved', { incident });

    // Publish event
    const kenny = getKennyIntegration();
    await kenny.getMessageBus().publishSubsystem(
      'safety.incident.resolved',
      'permission-manager',
      { incidentId, resolvedBy, severity: incident.severity }
    );
  }

  private async checkProtocol(
    protocol: SafetyProtocol, 
    request: PermissionRequest, 
    result: PermissionResult
  ): Promise<void> {
    for (const trigger of protocol.triggers) {
      if (!trigger.enabled) continue;

      const triggered = await this.evaluateTrigger(trigger, request, result);
      if (triggered) {
        const incident = await this.createIncident({
          type: this.mapTriggerToIncidentType(trigger.type),
          severity: this.calculateSeverity(protocol, trigger),
          protocolId: protocol.id,
          triggerId: trigger.type,
          context: request.context,
          details: {
            trigger: trigger.type,
            protocol: protocol.name,
            conditions: trigger.conditions,
            request: {
              permissionId: request.permissionId,
              resource: request.context.resource,
              operation: request.context.operation
            }
          }
        });

        // Execute safety actions
        await this.executeActions(protocol.actions, incident);
        
        this.emit('protocol.triggered', { protocol, trigger, incident });
      }
    }
  }

  private async evaluateTrigger(
    trigger: SafetyTrigger, 
    request: PermissionRequest, 
    result: PermissionResult
  ): Promise<boolean> {
    switch (trigger.type) {
      case 'permission_escalation':
        return this.checkPermissionEscalation(trigger, request, result);
      
      case 'multiple_failures':
        return this.checkMultipleFailures(trigger, request, result);
      
      case 'suspicious_pattern':
        return this.checkSuspiciousPattern(trigger, request, result);
      
      case 'resource_threshold':
        return this.checkResourceThreshold(trigger, request, result);
      
      case 'time_anomaly':
        return this.checkTimeAnomaly(trigger, request, result);
      
      case 'custom':
        return this.evaluateCustomTrigger(trigger, request, result);
      
      default:
        return false;
    }
  }

  private checkPermissionEscalation(
    trigger: SafetyTrigger, 
    request: PermissionRequest, 
    result: PermissionResult
  ): boolean {
    // Check if user is requesting elevated permissions
    const userId = request.context.userId;
    if (!userId) return false;

    const behavior = this.userBehaviorPatterns.get(userId);
    if (!behavior) return false;

    // Check for sudden escalation in permission level
    const currentLevel = this.getPermissionLevel(request.permissionId);
    const averageLevel = behavior.averagePermissionLevel;

    return currentLevel > averageLevel + 2; // Significant escalation
  }

  private checkMultipleFailures(
    trigger: SafetyTrigger, 
    request: PermissionRequest, 
    result: PermissionResult
  ): boolean {
    if (result.granted) return false;

    const userId = request.context.userId || request.context.sessionId;
    const behavior = this.userBehaviorPatterns.get(userId);
    if (!behavior) return false;

    const threshold = trigger.threshold || 5;
    const timeWindow = trigger.timeWindow || 300000; // 5 minutes
    const now = Date.now();

    const recentFailures = behavior.recentFailures.filter(
      failure => now - failure.getTime() < timeWindow
    ).length;

    return recentFailures >= threshold;
  }

  private checkSuspiciousPattern(
    trigger: SafetyTrigger, 
    request: PermissionRequest, 
    result: PermissionResult
  ): boolean {
    const userId = request.context.userId || request.context.sessionId;
    const suspicious = this.suspiciousActivities.get(userId);
    
    return suspicious ? suspicious.score > 0.8 : false;
  }

  private checkResourceThreshold(
    trigger: SafetyTrigger, 
    request: PermissionRequest, 
    result: PermissionResult
  ): boolean {
    const frequency = this.operationFrequency.get(request.context.resource);
    if (!frequency) return false;

    const threshold = trigger.threshold || 100;
    const timeWindow = trigger.timeWindow || 3600000; // 1 hour
    const now = Date.now();

    const recentOps = frequency.operations.filter(
      op => now - op.getTime() < timeWindow
    ).length;

    return recentOps >= threshold;
  }

  private checkTimeAnomaly(
    trigger: SafetyTrigger, 
    request: PermissionRequest, 
    result: PermissionResult
  ): boolean {
    const now = new Date();
    const hour = now.getHours();
    
    // Flag operations during unusual hours (2 AM - 5 AM)
    return hour >= 2 && hour <= 5;
  }

  private evaluateCustomTrigger(
    trigger: SafetyTrigger, 
    request: PermissionRequest, 
    result: PermissionResult
  ): boolean {
    // Evaluate custom conditions
    for (const condition of trigger.conditions) {
      if (!this.evaluateCondition(condition, request, result)) {
        return false;
      }
    }
    return true;
  }

  private evaluateCondition(condition: any, request: PermissionRequest, result: PermissionResult): boolean {
    // TODO: Implement comprehensive condition evaluation
    return false;
  }

  private async executeActions(actions: SafetyAction[], incident: SafetyIncident): Promise<void> {
    const actionResults: SafetyActionResult[] = [];

    for (const action of actions) {
      if (!action.enabled) continue;

      const actionResult: SafetyActionResult = {
        actionType: action.type,
        executed: false,
        timestamp: new Date()
      };

      try {
        switch (action.type) {
          case 'block_user':
            await this.blockUser(action, incident);
            break;
          
          case 'suspend_session':
            await this.suspendSession(action, incident);
            break;
          
          case 'require_approval':
            await this.requireApproval(action, incident);
            break;
          
          case 'notify_admin':
            await this.notifyAdmin(action, incident);
            break;
          
          case 'log_incident':
            await this.logIncident(action, incident);
            break;
          
          case 'rate_limit':
            await this.applyRateLimit(action, incident);
            break;
          
          case 'custom':
            await this.executeCustomAction(action, incident);
            break;
        }

        actionResult.executed = true;
        this.updateMetrics(action.type);
        
      } catch (error) {
        actionResult.error = error instanceof Error ? error.message : String(error);
        console.error(`[SafetyProtocols] Failed to execute action ${action.type}:`, error);
      }

      actionResults.push(actionResult);
    }

    incident.actions = actionResults;
  }

  private async blockUser(action: SafetyAction, incident: SafetyIncident): Promise<void> {
    // Implementation would integrate with user management system
    console.log(`[SafetyProtocols] BLOCK USER: ${incident.context.userId} - ${incident.details}`);
    
    // Publish blocking event
    const kenny = getKennyIntegration();
    await kenny.getMessageBus().publishSubsystem(
      'safety.user.blocked',
      'permission-manager',
      { 
        userId: incident.context.userId,
        reason: 'Safety protocol violation',
        incidentId: incident.id,
        severity: incident.severity
      }
    );
  }

  private async suspendSession(action: SafetyAction, incident: SafetyIncident): Promise<void> {
    console.log(`[SafetyProtocols] SUSPEND SESSION: ${incident.context.sessionId} - ${incident.details}`);
    
    this.metrics.suspendedSessions++;
    
    // Publish suspension event
    const kenny = getKennyIntegration();
    await kenny.getMessageBus().publishSubsystem(
      'safety.session.suspended',
      'permission-manager',
      { 
        sessionId: incident.context.sessionId,
        reason: 'Safety protocol violation',
        incidentId: incident.id,
        severity: incident.severity
      }
    );
  }

  private async requireApproval(action: SafetyAction, incident: SafetyIncident): Promise<void> {
    console.log(`[SafetyProtocols] REQUIRE APPROVAL: ${incident.context.operation} - ${incident.details}`);
    
    this.metrics.escalatedIncidents++;
    
    // Publish approval requirement event
    const kenny = getKennyIntegration();
    await kenny.getMessageBus().publishSubsystem(
      'safety.approval.required',
      'permission-manager',
      { 
        operation: incident.context.operation,
        resource: incident.context.resource,
        userId: incident.context.userId,
        incidentId: incident.id,
        severity: incident.severity
      }
    );
  }

  private async notifyAdmin(action: SafetyAction, incident: SafetyIncident): Promise<void> {
    console.log(`[SafetyProtocols] NOTIFY ADMIN: ${incident.severity} incident - ${incident.type}`);
    
    // Publish admin notification
    const kenny = getKennyIntegration();
    await kenny.getMessageBus().publishSubsystem(
      'safety.admin.notification',
      'permission-manager',
      { 
        incident: {
          id: incident.id,
          type: incident.type,
          severity: incident.severity,
          timestamp: incident.timestamp,
          context: incident.context,
          details: incident.details
        }
      }
    );
  }

  private async logIncident(action: SafetyAction, incident: SafetyIncident): Promise<void> {
    // Already logged in createIncident, but could enhance logging here
    console.log(`[SafetyProtocols] LOG INCIDENT: ${JSON.stringify(incident, null, 2)}`);
  }

  private async applyRateLimit(action: SafetyAction, incident: SafetyIncident): Promise<void> {
    const userId = incident.context.userId || incident.context.sessionId;
    console.log(`[SafetyProtocols] APPLY RATE LIMIT: ${userId}`);
    
    // Implementation would integrate with rate limiting system
  }

  private async executeCustomAction(action: SafetyAction, incident: SafetyIncident): Promise<void> {
    console.log(`[SafetyProtocols] CUSTOM ACTION: ${JSON.stringify(action.parameters)}`);
    
    // Custom action implementation
  }

  private async createIncident(incidentData: {
    type: SafetyIncident['type'];
    severity: SafetyIncident['severity'];
    protocolId: string;
    triggerId: string;
    context: PermissionContext;
    details: Record<string, any>;
  }): Promise<SafetyIncident> {
    const incident: SafetyIncident = {
      id: nanoid(),
      ...incidentData,
      timestamp: new Date(),
      resolved: false,
      actions: []
    };

    this.incidents.push(incident);

    // Maintain incident history limit
    if (this.incidents.length > this.config.maxIncidentHistory) {
      this.incidents.shift();
    }

    // Update metrics
    this.metrics.totalIncidents++;
    this.metrics.incidentsBySeverity[incident.severity] = 
      (this.metrics.incidentsBySeverity[incident.severity] || 0) + 1;
    this.metrics.incidentsByType[incident.type] = 
      (this.metrics.incidentsByType[incident.type] || 0) + 1;

    this.emit('incident.created', { incident });

    // Publish incident event
    const kenny = getKennyIntegration();
    await kenny.getMessageBus().publishSubsystem(
      'safety.incident.created',
      'permission-manager',
      { 
        incidentId: incident.id,
        type: incident.type,
        severity: incident.severity,
        protocolId: incident.protocolId
      }
    );

    return incident;
  }

  private updateBehaviorTracking(request: PermissionRequest, result: PermissionResult): void {
    const userId = request.context.userId || request.context.sessionId;
    
    let behavior = this.userBehaviorPatterns.get(userId);
    if (!behavior) {
      behavior = {
        userId,
        requestCount: 0,
        successRate: 0,
        averagePermissionLevel: 0,
        recentFailures: [],
        recentOperations: [],
        lastActivity: new Date(),
        suspicious: false
      };
      this.userBehaviorPatterns.set(userId, behavior);
    }

    behavior.requestCount++;
    behavior.lastActivity = new Date();
    
    const permissionLevel = this.getPermissionLevel(request.permissionId);
    behavior.averagePermissionLevel = 
      (behavior.averagePermissionLevel + permissionLevel) / behavior.requestCount;

    if (!result.granted) {
      behavior.recentFailures.push(new Date());
      // Keep only last 100 failures
      if (behavior.recentFailures.length > 100) {
        behavior.recentFailures.shift();
      }
    }

    behavior.recentOperations.push({
      timestamp: new Date(),
      operation: request.context.operation,
      resource: request.context.resource,
      granted: result.granted
    });

    // Keep only last 100 operations
    if (behavior.recentOperations.length > 100) {
      behavior.recentOperations.shift();
    }

    // Update success rate
    const successCount = behavior.recentOperations.filter(op => op.granted).length;
    behavior.successRate = successCount / behavior.recentOperations.length;

    // Update operation frequency
    this.updateOperationFrequency(request.context.resource);
  }

  private updateOperationFrequency(resource: string): void {
    let frequency = this.operationFrequency.get(resource);
    if (!frequency) {
      frequency = {
        resource,
        operations: [],
        averageInterval: 0
      };
      this.operationFrequency.set(resource, frequency);
    }

    frequency.operations.push(new Date());
    
    // Keep only last 1000 operations
    if (frequency.operations.length > 1000) {
      frequency.operations.shift();
    }

    // Calculate average interval
    if (frequency.operations.length > 1) {
      const intervals = frequency.operations
        .slice(1)
        .map((op, i) => op.getTime() - frequency.operations[i].getTime());
      
      frequency.averageInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
    }
  }

  private async checkDangerousPatterns(request: PermissionRequest, result: PermissionResult): Promise<void> {
    const context = request.context;
    
    for (const pattern of this.dangerousPatterns) {
      if (this.matchesPattern(pattern, context, request)) {
        const incident = await this.createIncident({
          type: 'pattern_match',
          severity: pattern.severity,
          protocolId: 'pattern-analysis',
          triggerId: pattern.id,
          context,
          details: {
            pattern: pattern.name,
            description: pattern.description,
            matchedFields: pattern.fields
          }
        });

        this.emit('dangerous.pattern.matched', { pattern, incident });
      }
    }
  }

  private async checkAnomalies(request: PermissionRequest, result: PermissionResult): Promise<void> {
    const anomaly = await this.anomalyDetector.detect(request, result);
    
    if (anomaly.isAnomaly && anomaly.confidence > 0.7) {
      const incident = await this.createIncident({
        type: 'anomaly_detected',
        severity: anomaly.confidence > 0.9 ? 'high' : 'medium',
        protocolId: 'anomaly-detection',
        triggerId: 'behavior-anomaly',
        context: request.context,
        details: {
          confidence: anomaly.confidence,
          factors: anomaly.factors,
          baseline: anomaly.baseline
        }
      });

      this.emit('anomaly.detected', { anomaly, incident });
    }
  }

  private async checkAlertThresholds(): Promise<void> {
    const now = Date.now();
    const timeWindow = this.config.alertThresholds.timeWindow;
    
    const recentIncidents = this.incidents.filter(
      incident => now - incident.timestamp.getTime() < timeWindow
    );

    const highSeverityCount = recentIncidents.filter(i => i.severity === 'high').length;
    const criticalSeverityCount = recentIncidents.filter(i => i.severity === 'critical').length;

    if (criticalSeverityCount >= this.config.alertThresholds.criticalSeverityCount) {
      this.emit('alert.critical', { 
        count: criticalSeverityCount,
        timeWindow,
        incidents: recentIncidents.filter(i => i.severity === 'critical')
      });
    } else if (highSeverityCount >= this.config.alertThresholds.highSeverityCount) {
      this.emit('alert.high', { 
        count: highSeverityCount,
        timeWindow,
        incidents: recentIncidents.filter(i => i.severity === 'high')
      });
    }
  }

  private matchesPattern(pattern: DangerousPattern, context: PermissionContext, request: PermissionRequest): boolean {
    // Simple pattern matching implementation
    for (const field of pattern.fields) {
      const value = this.getContextValue(context, request, field);
      if (pattern.regex.test(String(value))) {
        return true;
      }
    }
    return false;
  }

  private getContextValue(context: PermissionContext, request: PermissionRequest, field: string): any {
    switch (field) {
      case 'resource': return context.resource;
      case 'operation': return context.operation;
      case 'userId': return context.userId;
      case 'sessionId': return context.sessionId;
      case 'permissionId': return request.permissionId;
      default: return context.metadata?.[field];
    }
  }

  private getPermissionLevel(permissionId: string): number {
    // Map permission to numeric level for analysis
    const levelMap: Record<string, number> = {
      'read_files': 1,
      'write_files': 2,
      'tool_execution': 3,
      'execute_commands': 4,
      'network_access': 3,
      'manage_users': 5,
      'dangerous_operations': 6,
      'manage_permissions': 7
    };
    
    return levelMap[permissionId] || 0;
  }

  private mapTriggerToIncidentType(triggerType: string): SafetyIncident['type'] {
    switch (triggerType) {
      case 'permission_escalation': return 'escalation_required';
      case 'multiple_failures': return 'safety_violation';
      case 'suspicious_pattern': return 'anomaly_detected';
      default: return 'safety_violation';
    }
  }

  private calculateSeverity(protocol: SafetyProtocol, trigger: SafetyTrigger): SafetyIncident['severity'] {
    // Base severity on protocol safety level
    switch (protocol.safetyLevel) {
      case 'critical': return 'critical';
      case 'dangerous': return 'high';
      case 'high-risk': return 'medium';
      default: return 'low';
    }
  }

  private updateMetrics(actionType: string): void {
    switch (actionType) {
      case 'block_user':
        this.metrics.blockedOperations++;
        break;
      case 'suspend_session':
        this.metrics.suspendedSessions++;
        break;
      case 'require_approval':
        this.metrics.escalatedIncidents++;
        break;
    }
  }

  private createEmptyMetrics(): SafetyMetrics {
    return {
      totalIncidents: 0,
      incidentsBySeverity: {},
      incidentsByType: {},
      blockedOperations: 0,
      suspendedSessions: 0,
      escalatedIncidents: 0,
      falsePositives: 0,
      averageResponseTime: 0,
      timeRange: {
        start: new Date(),
        end: new Date()
      }
    };
  }

  private initializeBuiltInProtocols(): void {
    // Built-in safety protocols
    const builtInProtocols: SafetyProtocol[] = [
      {
        id: 'permission-escalation-detector',
        name: 'Permission Escalation Detector',
        description: 'Detects attempts to escalate privileges',
        safetyLevel: SafetyLevel.HIGH_RISK,
        triggers: [
          {
            type: 'permission_escalation',
            conditions: [],
            threshold: 2,
            timeWindow: 300000,
            enabled: true
          }
        ],
        actions: [
          {
            type: 'require_approval',
            parameters: {},
            priority: 1,
            enabled: true
          },
          {
            type: 'log_incident',
            parameters: {},
            priority: 2,
            enabled: true
          }
        ],
        enabled: true,
        priority: 1,
        createdAt: new Date(),
        updatedAt: new Date()
      },
      
      {
        id: 'multiple-failures-detector',
        name: 'Multiple Failures Detector',
        description: 'Detects multiple permission failures in short time',
        safetyLevel: SafetyLevel.MODERATE,
        triggers: [
          {
            type: 'multiple_failures',
            conditions: [],
            threshold: 5,
            timeWindow: 300000,
            enabled: true
          }
        ],
        actions: [
          {
            type: 'rate_limit',
            parameters: { duration: 3600000 }, // 1 hour
            priority: 1,
            enabled: true
          },
          {
            type: 'notify_admin',
            parameters: {},
            priority: 2,
            enabled: true
          }
        ],
        enabled: true,
        priority: 2,
        createdAt: new Date(),
        updatedAt: new Date()
      }
    ];

    for (const protocol of builtInProtocols) {
      this.protocols.set(protocol.id, protocol);
    }
  }

  private initializeDangerousPatterns(): void {
    this.dangerousPatterns = [
      {
        id: 'system-access-pattern',
        name: 'System Access Pattern',
        description: 'Detects attempts to access system files or commands',
        fields: ['resource', 'operation'],
        regex: /\/(etc|sys|proc|dev|boot|root)\//i,
        severity: 'high'
      },
      {
        id: 'dangerous-command-pattern',
        name: 'Dangerous Command Pattern',
        description: 'Detects dangerous system commands',
        fields: ['resource', 'operation'],
        regex: /(rm\s+-rf|sudo|su|passwd|chmod\s+777|mkfs|dd\s+if=)/i,
        severity: 'critical'
      },
      {
        id: 'network-scanning-pattern',
        name: 'Network Scanning Pattern',
        description: 'Detects network scanning activities',
        fields: ['operation'],
        regex: /(nmap|netstat|ss\s+-|ping\s+-c\s+\d{3})/i,
        severity: 'medium'
      }
    ];
  }

  private startMonitoring(): void {
    // Clean up old incidents every hour
    setInterval(() => {
      const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000); // 24 hours ago
      this.incidents = this.incidents.filter(incident => incident.timestamp > cutoff);
    }, 3600000);

    // Clean up old behavior patterns every 6 hours
    setInterval(() => {
      const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000); // 24 hours ago
      for (const [userId, behavior] of this.userBehaviorPatterns.entries()) {
        if (behavior.lastActivity < cutoff) {
          this.userBehaviorPatterns.delete(userId);
        }
      }
    }, 21600000);
  }
}

// Supporting interfaces and classes

interface BehaviorPattern {
  userId: string;
  requestCount: number;
  successRate: number;
  averagePermissionLevel: number;
  recentFailures: Date[];
  recentOperations: Array<{
    timestamp: Date;
    operation: string;
    resource: string;
    granted: boolean;
  }>;
  lastActivity: Date;
  suspicious: boolean;
}

interface SuspiciousActivity {
  userId: string;
  score: number;
  factors: string[];
  lastUpdated: Date;
}

interface OperationFrequency {
  resource: string;
  operations: Date[];
  averageInterval: number;
}

interface DangerousPattern {
  id: string;
  name: string;
  description: string;
  fields: string[];
  regex: RegExp;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

interface AnomalyResult {
  isAnomaly: boolean;
  confidence: number;
  factors: string[];
  baseline: any;
}

class AnomalyDetector {
  private baselines = new Map<string, any>();

  async initialize(): Promise<void> {
    // Initialize anomaly detection models
  }

  async detect(request: PermissionRequest, result: PermissionResult): Promise<AnomalyResult> {
    // Simple anomaly detection implementation
    // In production, this would use machine learning models
    
    const userId = request.context.userId || request.context.sessionId;
    const baseline = this.baselines.get(userId) || this.createBaseline();
    
    const factors: string[] = [];
    let anomalyScore = 0;

    // Check time-based anomaly
    const hour = new Date().getHours();
    if (hour < 6 || hour > 22) {
      factors.push('unusual_time');
      anomalyScore += 0.3;
    }

    // Check permission level anomaly
    const permissionLevel = this.getPermissionLevel(request.permissionId);
    if (permissionLevel > baseline.averagePermissionLevel + 2) {
      factors.push('permission_escalation');
      anomalyScore += 0.4;
    }

    // Check failure pattern
    if (!result.granted && baseline.successRate > 0.8) {
      factors.push('unexpected_failure');
      anomalyScore += 0.2;
    }

    return {
      isAnomaly: anomalyScore > 0.5,
      confidence: Math.min(anomalyScore, 1.0),
      factors,
      baseline
    };
  }

  private createBaseline(): any {
    return {
      averagePermissionLevel: 2,
      successRate: 0.9,
      typicalHours: [9, 10, 11, 12, 13, 14, 15, 16, 17],
      commonOperations: ['read', 'write', 'execute']
    };
  }

  private getPermissionLevel(permissionId: string): number {
    const levelMap: Record<string, number> = {
      'read_files': 1,
      'write_files': 2,
      'tool_execution': 3,
      'execute_commands': 4,
      'network_access': 3,
      'manage_users': 5,
      'dangerous_operations': 6,
      'manage_permissions': 7
    };
    
    return levelMap[permissionId] || 0;
  }
}

export default SafetyProtocolManager;