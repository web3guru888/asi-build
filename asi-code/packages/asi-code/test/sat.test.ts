/**
 * Software Architecture Taskforce (SAT) Tests
 */

import { describe, it, expect, beforeEach, afterEach } from 'bun:test';
import { mkdirSync, writeFileSync, rmSync } from 'fs';
import { join } from 'path';
import { createSATEngine, type SATEngine } from '../src/sat/index.js';

describe('SAT Engine', () => {
  let satEngine: SATEngine;
  let testProjectPath: string;

  beforeEach(() => {
    satEngine = createSATEngine();
    testProjectPath = join(process.cwd(), 'test-project-' + Date.now());
    
    // Create test project structure
    mkdirSync(testProjectPath, { recursive: true });
    mkdirSync(join(testProjectPath, 'src'), { recursive: true });
    mkdirSync(join(testProjectPath, 'src', 'controllers'), { recursive: true });
    mkdirSync(join(testProjectPath, 'src', 'models'), { recursive: true });
    mkdirSync(join(testProjectPath, 'src', 'views'), { recursive: true });
    mkdirSync(join(testProjectPath, 'services'), { recursive: true });
    mkdirSync(join(testProjectPath, 'tests'), { recursive: true });
  });

  afterEach(async () => {
    await satEngine.cleanup();
    
    // Clean up test project
    try {
      rmSync(testProjectPath, { recursive: true, force: true });
    } catch (error) {
      // Ignore cleanup errors
    }
  });

  it('should create SAT engine successfully', () => {
    expect(satEngine).toBeDefined();
    expect(typeof satEngine.analyzeProject).toBe('function');
    expect(typeof satEngine.detectPatterns).toBe('function');
    expect(typeof satEngine.calculateMetrics).toBe('function');
  });

  it('should detect MVC pattern in project structure', async () => {
    // Create MVC-like files
    writeFileSync(join(testProjectPath, 'src', 'controllers', 'UserController.ts'), `
      export class UserController {
        public async getUsers() {
          const users = await UserModel.findAll();
          return this.render('users/index', { users });
        }
      }
    `);

    writeFileSync(join(testProjectPath, 'src', 'models', 'UserModel.ts'), `
      export class UserModel {
        static async findAll() {
          // Database logic here
          return [];
        }
      }
    `);

    writeFileSync(join(testProjectPath, 'src', 'views', 'UserView.tsx'), `
      export const UserView = ({ users }) => {
        return <div>User List</div>;
      };
    `);

    const analysis = await satEngine.analyzeProject(testProjectPath);
    
    expect(analysis).toBeDefined();
    expect(analysis.patterns.length).toBeGreaterThan(0);
    
    const mvcPattern = analysis.patterns.find(p => p.name === 'Model-View-Controller');
    expect(mvcPattern).toBeDefined();
    expect(mvcPattern!.confidence).toBeGreaterThan(30);
  });

  it('should detect microservices pattern', async () => {
    // Create microservices-like structure
    writeFileSync(join(testProjectPath, 'docker-compose.yml'), `
      version: '3'
      services:
        user-service:
          build: ./user-service
        order-service:
          build: ./order-service
    `);

    writeFileSync(join(testProjectPath, 'services', 'UserService.ts'), `
      import express from 'express';
      
      const app = express();
      
      app.get('/api/users', (req, res) => {
        // Microservice endpoint
      });
      
      export default app;
    `);

    writeFileSync(join(testProjectPath, 'services', 'OrderService.ts'), `
      import express from 'express';
      
      const app = express();
      
      app.get('/api/orders', (req, res) => {
        // Another microservice endpoint
      });
      
      export default app;
    `);

    const analysis = await satEngine.analyzeProject(testProjectPath);
    
    const microservicesPattern = analysis.patterns.find(p => p.name === 'Microservices Architecture');
    expect(microservicesPattern).toBeDefined();
    expect(microservicesPattern!.confidence).toBeGreaterThan(20);
  });

  it('should detect event-driven pattern', async () => {
    writeFileSync(join(testProjectPath, 'src', 'EventBus.ts'), `
      export class EventBus {
        private listeners = new Map();
        
        publish(event: string, data: any) {
          // Event publishing logic
        }
        
        subscribe(event: string, callback: Function) {
          // Event subscription logic
        }
      }
    `);

    writeFileSync(join(testProjectPath, 'src', 'EventHandler.ts'), `
      import { EventBus } from './EventBus';
      
      export class EventHandler {
        constructor(private eventBus: EventBus) {
          this.eventBus.subscribe('user.created', this.handleUserCreated);
        }
        
        private handleUserCreated(data: any) {
          // Handle event
        }
      }
    `);

    const analysis = await satEngine.analyzeProject(testProjectPath);
    
    const eventDrivenPattern = analysis.patterns.find(p => p.name === 'Event-Driven Architecture');
    expect(eventDrivenPattern).toBeDefined();
    expect(eventDrivenPattern!.confidence).toBeGreaterThan(30);
  });

  it('should calculate code metrics correctly', async () => {
    // Create files with known metrics
    writeFileSync(join(testProjectPath, 'simple.ts'), `
      // Simple file with 5 lines
      function hello() {
        return 'world';
      }
    `);

    writeFileSync(join(testProjectPath, 'complex.ts'), `
      // Complex file with high cyclomatic complexity
      function complexFunction(x: number, y: number) {
        if (x > 10) {
          for (let i = 0; i < y; i++) {
            if (i % 2 === 0) {
              console.log(i);
            } else {
              while (x > 0) {
                x--;
                if (x === 5) {
                  break;
                }
              }
            }
          }
        } else {
          switch (y) {
            case 1:
              return x + 1;
            case 2:
              return x + 2;
            default:
              return x;
          }
        }
      }
    `);

    writeFileSync(join(testProjectPath, 'dependencies.ts'), `
      import express from 'express';
      import lodash from 'lodash';
      import moment from 'moment';
      const fs = require('fs');
    `);

    const files = [
      join(testProjectPath, 'simple.ts'),
      join(testProjectPath, 'complex.ts'),
      join(testProjectPath, 'dependencies.ts')
    ];

    const metrics = await satEngine.calculateMetrics(files);
    
    expect(metrics).toBeDefined();
    expect(metrics.linesOfCode).toBeGreaterThan(0);
    expect(metrics.cyclomaticComplexity).toBeGreaterThan(5); // Complex file has multiple branches
    expect(metrics.dependencies).toContain('express');
    expect(metrics.dependencies).toContain('lodash');
    expect(metrics.dependencies).toContain('moment');
    expect(metrics.dependencies).toContain('fs');
    expect(metrics.coupling).toBeGreaterThan(0);
    expect(metrics.cohesion).toBeGreaterThanOrEqual(0);
    expect(metrics.cohesion).toBeLessThanOrEqual(100);
  });

  it('should generate relevant recommendations', async () => {
    // Create a project with some issues
    writeFileSync(join(testProjectPath, 'messy.ts'), `
      // High complexity function
      function messyFunction(a: any, b: any, c: any, d: any) {
        if (a) {
          if (b) {
            if (c) {
              if (d) {
                for (let i = 0; i < 100; i++) {
                  for (let j = 0; j < 100; j++) {
                    if (i % j === 0) {
                      console.log('complex logic');
                    }
                  }
                }
              }
            }
          }
        }
      }
    `);

    writeFileSync(join(testProjectPath, 'tightly-coupled.ts'), `
      import a from './a';
      import b from './b';
      import c from './c';
      import d from './d';
      import e from './e';
      import f from './f';
      import g from './g';
      
      // Too many dependencies
    `);

    const analysis = await satEngine.analyzeProject(testProjectPath);
    
    expect(analysis.recommendations).toBeDefined();
    expect(analysis.recommendations.length).toBeGreaterThan(0);
    
    // Should recommend refactoring for high complexity
    const complexityRecommendation = analysis.recommendations.find(r => 
      r.includes('cyclomatic complexity') || r.includes('refactoring')
    );
    expect(complexityRecommendation).toBeDefined();

    // Should include general recommendations
    expect(analysis.recommendations).toContain('Consider implementing automated architecture testing');
    expect(analysis.recommendations).toContain('Document architectural decisions and patterns');
  });

  it('should handle empty project gracefully', async () => {
    const emptyProjectPath = join(process.cwd(), 'empty-project-' + Date.now());
    mkdirSync(emptyProjectPath, { recursive: true });

    try {
      const analysis = await satEngine.analyzeProject(emptyProjectPath);
      
      expect(analysis).toBeDefined();
      expect(analysis.patterns).toHaveLength(0);
      expect(analysis.metrics.linesOfCode).toBe(0);
      expect(analysis.metrics.dependencies).toHaveLength(0);
      expect(analysis.recommendations).toContain('No clear architectural patterns detected. Consider implementing a well-defined architecture');
    } finally {
      rmSync(emptyProjectPath, { recursive: true, force: true });
    }
  });

  it('should emit events during analysis', async () => {
    let analysisStarted = false;
    let analysisCompleted = false;
    let patternsDetected = false;
    let metricsCalculated = false;

    satEngine.on('sat:analysis_started', () => {
      analysisStarted = true;
    });

    satEngine.on('sat:analysis_completed', () => {
      analysisCompleted = true;
    });

    satEngine.on('sat:patterns_detected', () => {
      patternsDetected = true;
    });

    satEngine.on('sat:metrics_calculated', () => {
      metricsCalculated = true;
    });

    // Create a simple file for analysis
    writeFileSync(join(testProjectPath, 'test.ts'), `
      export function test() {
        return 'test';
      }
    `);

    await satEngine.analyzeProject(testProjectPath);

    expect(analysisStarted).toBe(true);
    expect(analysisCompleted).toBe(true);
    expect(patternsDetected).toBe(true);
    expect(metricsCalculated).toBe(true);
  });

  it('should handle file reading errors gracefully', async () => {
    // Create a file with restrictive permissions (if supported by OS)
    const restrictedFile = join(testProjectPath, 'restricted.ts');
    writeFileSync(restrictedFile, 'export const test = "test";');

    // The analysis should complete without throwing errors
    const analysis = await satEngine.analyzeProject(testProjectPath);
    expect(analysis).toBeDefined();
  });

  it('should sort patterns by confidence', async () => {
    // Create files that match multiple patterns with different strengths
    
    // Strong MVC indicators
    writeFileSync(join(testProjectPath, 'Controller.ts'), 'class Controller {}');
    writeFileSync(join(testProjectPath, 'Model.ts'), 'class Model {}');
    writeFileSync(join(testProjectPath, 'View.tsx'), 'const View = () => {};');
    
    // Weak microservices indicators  
    writeFileSync(join(testProjectPath, 'service.ts'), 'const service = {};');

    const files = [
      join(testProjectPath, 'Controller.ts'),
      join(testProjectPath, 'Model.ts'), 
      join(testProjectPath, 'View.tsx'),
      join(testProjectPath, 'service.ts')
    ];

    const patterns = await satEngine.detectPatterns(files);
    
    // Patterns should be sorted by confidence (highest first)
    for (let i = 0; i < patterns.length - 1; i++) {
      expect(patterns[i].confidence).toBeGreaterThanOrEqual(patterns[i + 1].confidence);
    }
  });
});