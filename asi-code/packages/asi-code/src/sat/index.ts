/**
 * Software Architecture Taskforce (SAT) - Advanced architectural analysis
 *
 * Provides sophisticated software architecture analysis, pattern detection,
 * and architectural decision support for complex software systems.
 */

import { EventEmitter } from 'eventemitter3';
import { glob } from 'glob';
import { readFileSync } from 'fs';

export interface ArchitecturalPattern {
  id: string;
  name: string;
  description: string;
  indicators: string[];
  confidence: number;
  impact: 'low' | 'medium' | 'high';
}

export interface CodeMetrics {
  linesOfCode: number;
  cyclomaticComplexity: number;
  dependencies: string[];
  coupling: number;
  cohesion: number;
}

export interface ArchitecturalAnalysis {
  projectPath: string;
  patterns: ArchitecturalPattern[];
  metrics: CodeMetrics;
  recommendations: string[];
  timestamp: Date;
}

export interface SATEngine extends EventEmitter {
  analyzeProject(projectPath: string): Promise<ArchitecturalAnalysis>;
  detectPatterns(files: string[]): Promise<ArchitecturalPattern[]>;
  calculateMetrics(files: string[]): Promise<CodeMetrics>;
  generateRecommendations(analysis: ArchitecturalAnalysis): Promise<string[]>;
  cleanup(): Promise<void>;
}

export class DefaultSATEngine extends EventEmitter implements SATEngine {
  private readonly knownPatterns: ArchitecturalPattern[] = [
    {
      id: 'mvc',
      name: 'Model-View-Controller',
      description:
        'Separates application logic into three interconnected components',
      indicators: ['model', 'view', 'controller', 'mvc'],
      confidence: 0,
      impact: 'high',
    },
    {
      id: 'microservices',
      name: 'Microservices Architecture',
      description:
        'Structures application as a collection of loosely coupled services',
      indicators: ['service', 'api', 'docker', 'kubernetes', 'microservice'],
      confidence: 0,
      impact: 'high',
    },
    {
      id: 'layered',
      name: 'Layered Architecture',
      description: 'Organizes system into horizontal layers',
      indicators: ['layer', 'tier', 'presentation', 'business', 'data'],
      confidence: 0,
      impact: 'medium',
    },
    {
      id: 'event_driven',
      name: 'Event-Driven Architecture',
      description: 'Uses events to trigger and communicate between services',
      indicators: ['event', 'publish', 'subscribe', 'queue', 'bus'],
      confidence: 0,
      impact: 'high',
    },
  ];

  async analyzeProject(projectPath: string): Promise<ArchitecturalAnalysis> {
    this.emit('sat:analysis_started', { projectPath });

    try {
      // Find all relevant files
      const files = await this.findProjectFiles(projectPath);

      // Detect architectural patterns
      const patterns = await this.detectPatterns(files);

      // Calculate metrics
      const metrics = await this.calculateMetrics(files);

      const analysis: ArchitecturalAnalysis = {
        projectPath,
        patterns,
        metrics,
        recommendations: [],
        timestamp: new Date(),
      };

      // Generate recommendations
      analysis.recommendations = await this.generateRecommendations(analysis);

      this.emit('sat:analysis_completed', { analysis });
      return analysis;
    } catch (error) {
      this.emit('sat:analysis_error', { error, projectPath });
      throw error;
    }
  }

  async detectPatterns(files: string[]): Promise<ArchitecturalPattern[]> {
    const detectedPatterns: ArchitecturalPattern[] = [];

    for (const pattern of this.knownPatterns) {
      let confidence = 0;
      let indicatorCount = 0;

      for (const file of files) {
        try {
          const content = readFileSync(file, 'utf8').toLowerCase();
          const fileName = file.toLowerCase();

          for (const indicator of pattern.indicators) {
            if (content.includes(indicator) || fileName.includes(indicator)) {
              indicatorCount++;
            }
          }
        } catch (error) {
          // Skip files that can't be read
          continue;
        }
      }

      // Calculate confidence based on indicator frequency
      confidence = Math.min(
        100,
        (indicatorCount / pattern.indicators.length) * 100
      );

      if (confidence > 30) {
        // Threshold for detection
        detectedPatterns.push({
          ...pattern,
          confidence,
        });
      }
    }

    this.emit('sat:patterns_detected', { patterns: detectedPatterns });
    return detectedPatterns.sort((a, b) => b.confidence - a.confidence);
  }

  async calculateMetrics(files: string[]): Promise<CodeMetrics> {
    let totalLines = 0;
    let totalComplexity = 0;
    const dependencies = new Set<string>();
    const fileCount = files.length;

    for (const file of files) {
      try {
        const content = readFileSync(file, 'utf8');
        const lines = content.split('\n').length;
        totalLines += lines;

        // Simple complexity calculation (count of if, for, while, switch)
        const complexityIndicators = content.match(
          /(if|for|while|switch|catch|&&|\|\|)/g
        );
        totalComplexity += complexityIndicators
          ? complexityIndicators.length
          : 1;

        // Extract dependencies (simple import/require detection)
        const importMatches = content.match(
          /(import|require|from)\s+['"][^'"]+['"]/g
        );
        if (importMatches) {
          importMatches.forEach(match => {
            const dep = match.match(/['"]([^'"]+)['"]/);
            if (dep) dependencies.add(dep[1]);
          });
        }
      } catch (error) {
        // Skip files that can't be read
        continue;
      }
    }

    // Calculate coupling (dependencies per file)
    const coupling = dependencies.size / Math.max(1, fileCount);

    // Calculate cohesion (inverse of complexity per line)
    const cohesion = Math.max(
      0,
      100 - (totalComplexity / Math.max(1, totalLines)) * 100
    );

    const metrics: CodeMetrics = {
      linesOfCode: totalLines,
      cyclomaticComplexity: totalComplexity,
      dependencies: Array.from(dependencies),
      coupling: Math.round(coupling * 100) / 100,
      cohesion: Math.round(cohesion * 100) / 100,
    };

    this.emit('sat:metrics_calculated', { metrics });
    return metrics;
  }

  async generateRecommendations(
    analysis: ArchitecturalAnalysis
  ): Promise<string[]> {
    const recommendations: string[] = [];

    // Pattern-based recommendations
    const primaryPattern = analysis.patterns[0];
    if (primaryPattern) {
      recommendations.push(
        `Detected ${primaryPattern.name} pattern with ${primaryPattern.confidence.toFixed(1)}% confidence`
      );

      if (primaryPattern.confidence < 60) {
        recommendations.push(
          `Consider strengthening ${primaryPattern.name} implementation for better architectural clarity`
        );
      }
    }

    // Metrics-based recommendations
    if (
      analysis.metrics.cyclomaticComplexity >
      analysis.metrics.linesOfCode * 0.1
    ) {
      recommendations.push(
        'High cyclomatic complexity detected. Consider refactoring complex functions'
      );
    }

    if (analysis.metrics.coupling > 5) {
      recommendations.push(
        'High coupling detected. Consider reducing dependencies between modules'
      );
    }

    if (analysis.metrics.cohesion < 70) {
      recommendations.push(
        'Low cohesion detected. Consider improving module organization'
      );
    }

    if (analysis.patterns.length === 0) {
      recommendations.push(
        'No clear architectural patterns detected. Consider implementing a well-defined architecture'
      );
    }

    // General recommendations
    recommendations.push(
      'Consider implementing automated architecture testing'
    );
    recommendations.push('Document architectural decisions and patterns');

    this.emit('sat:recommendations_generated', { recommendations });
    return recommendations;
  }

  private async findProjectFiles(projectPath: string): Promise<string[]> {
    const patterns = [
      '**/*.ts',
      '**/*.js',
      '**/*.tsx',
      '**/*.jsx',
      '**/*.py',
      '**/*.java',
      '**/*.cs',
      '**/*.go',
      '**/*.rs',
      '**/*.php',
    ];

    const files: string[] = [];
    for (const pattern of patterns) {
      try {
        const matchedFiles = await glob(pattern, {
          cwd: projectPath,
          absolute: true,
          ignore: [
            '**/node_modules/**',
            '**/dist/**',
            '**/build/**',
            '**/.git/**',
          ],
        });
        files.push(...matchedFiles);
      } catch (error) {
        // Continue with other patterns if one fails
        continue;
      }
    }

    return [...new Set(files)]; // Remove duplicates
  }

  async cleanup(): Promise<void> {
    this.removeAllListeners();
    this.emit('sat:cleanup');
  }
}

export function createSATEngine(): SATEngine {
  return new DefaultSATEngine();
}
