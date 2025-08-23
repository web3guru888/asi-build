/**
 * Performance Benchmarking Suite
 * Comprehensive performance testing utilities with detailed metrics
 */

import { bench, describe } from 'vitest';
import { performance } from 'perf_hooks';
import { PerformanceFixtures } from '../fixtures/index.js';

// =============================================================================
// PERFORMANCE METRICS COLLECTOR
// =============================================================================

export interface PerformanceMetrics {
  // Timing metrics
  duration: number;
  avgDuration: number;
  minDuration: number;
  maxDuration: number;
  
  // Memory metrics
  memoryUsed: number;
  peakMemory: number;
  memoryDelta: number;
  
  // Throughput metrics
  operationsPerSecond: number;
  itemsProcessed: number;
  
  // System metrics
  cpuUsage?: number;
  gcCount?: number;
  gcDuration?: number;
  
  // Custom metrics
  [key: string]: any;
}

export class PerformanceCollector {
  private startTime: number = 0;
  private endTime: number = 0;
  private startMemory: NodeJS.MemoryUsage;
  private endMemory: NodeJS.MemoryUsage;
  private measurements: number[] = [];
  private customMetrics: Record<string, any> = {};

  constructor() {
    this.startMemory = process.memoryUsage();
  }

  /**
   * Start performance measurement
   */
  start() {
    // Force garbage collection if available
    if (global.gc) {
      global.gc();
    }
    
    this.startMemory = process.memoryUsage();
    this.startTime = performance.now();
  }

  /**
   * End performance measurement
   */
  end() {
    this.endTime = performance.now();
    this.endMemory = process.memoryUsage();
    
    const duration = this.endTime - this.startTime;
    this.measurements.push(duration);
    
    return duration;
  }

  /**
   * Add a measurement without start/end
   */
  addMeasurement(duration: number) {
    this.measurements.push(duration);
  }

  /**
   * Add custom metric
   */
  addCustomMetric(key: string, value: any) {
    this.customMetrics[key] = value;
  }

  /**
   * Get comprehensive metrics
   */
  getMetrics(itemsProcessed: number = 1): PerformanceMetrics {
    const durations = this.measurements;
    const totalDuration = durations.reduce((sum, d) => sum + d, 0);
    
    return {
      // Timing metrics
      duration: this.endTime - this.startTime,
      avgDuration: totalDuration / durations.length,
      minDuration: Math.min(...durations),
      maxDuration: Math.max(...durations),
      
      // Memory metrics
      memoryUsed: this.endMemory.heapUsed,
      peakMemory: Math.max(this.startMemory.heapUsed, this.endMemory.heapUsed),
      memoryDelta: this.endMemory.heapUsed - this.startMemory.heapUsed,
      
      // Throughput metrics
      operationsPerSecond: (itemsProcessed * 1000) / (this.endTime - this.startTime),
      itemsProcessed,
      
      // Custom metrics
      ...this.customMetrics
    };
  }

  /**
   * Reset collector
   */
  reset() {
    this.measurements = [];
    this.customMetrics = {};
    this.startMemory = process.memoryUsage();
  }
}

// =============================================================================
// BENCHMARK SUITE
// =============================================================================

export class BenchmarkSuite {
  private collector = new PerformanceCollector();
  private results = new Map<string, PerformanceMetrics>();

  /**
   * Run a single benchmark
   */
  async runBenchmark(
    name: string,
    fn: () => Promise<any> | any,
    options: {
      iterations?: number;
      warmupIterations?: number;
      itemsProcessed?: number;
    } = {}
  ) {
    const {
      iterations = 10,
      warmupIterations = 3,
      itemsProcessed = 1
    } = options;

    console.log(`Running benchmark: ${name}`);

    // Warmup
    console.log(`  Warmup (${warmupIterations} iterations)...`);
    for (let i = 0; i < warmupIterations; i++) {
      await fn();
    }

    // Reset and start measuring
    this.collector.reset();
    
    console.log(`  Measuring (${iterations} iterations)...`);
    for (let i = 0; i < iterations; i++) {
      this.collector.start();
      await fn();
      this.collector.end();
    }

    const metrics = this.collector.getMetrics(itemsProcessed);
    this.results.set(name, metrics);

    console.log(`  Completed: ${metrics.avgDuration.toFixed(2)}ms avg, ${metrics.operationsPerSecond.toFixed(2)} ops/sec`);
    
    return metrics;
  }

  /**
   * Run multiple benchmarks and compare
   */
  async runComparison(benchmarks: Array<{
    name: string;
    fn: () => Promise<any> | any;
    itemsProcessed?: number;
  }>, iterations = 10) {
    console.log(`Running ${benchmarks.length} benchmarks for comparison...`);
    
    for (const benchmark of benchmarks) {
      await this.runBenchmark(benchmark.name, benchmark.fn, {
        iterations,
        itemsProcessed: benchmark.itemsProcessed
      });
    }

    return this.getComparisonResults();
  }

  /**
   * Get comparison results
   */
  getComparisonResults() {
    const results = Array.from(this.results.entries()).map(([name, metrics]) => ({
      name,
      ...metrics
    }));

    // Sort by average duration (fastest first)
    results.sort((a, b) => a.avgDuration - b.avgDuration);

    // Calculate relative performance
    const fastest = results[0];
    const comparison = results.map(result => ({
      ...result,
      relativeSpeed: result.avgDuration / fastest.avgDuration,
      percentSlower: ((result.avgDuration / fastest.avgDuration - 1) * 100)
    }));

    return comparison;
  }

  /**
   * Get all results
   */
  getAllResults() {
    return new Map(this.results);
  }

  /**
   * Clear results
   */
  clearResults() {
    this.results.clear();
  }
}

// =============================================================================
// PREDEFINED BENCHMARKS
// =============================================================================

export const CommonBenchmarks = {
  /**
   * Data Processing Benchmarks
   */
  dataProcessing: {
    arrayMap: (data: any[]) => data.map(item => ({ ...item, processed: true })),
    
    arrayFilter: (data: any[]) => data.filter(item => item.value > 50),
    
    arrayReduce: (data: any[]) => data.reduce((sum, item) => sum + item.value, 0),
    
    objectTransform: (data: any[]) => data.map(item => ({
      id: item.id,
      name: item.name?.toUpperCase(),
      category: item.metadata?.category,
      score: item.value * 2
    })),
    
    jsonStringify: (data: any) => JSON.stringify(data),
    
    jsonParse: (jsonString: string) => JSON.parse(jsonString)
  },

  /**
   * String Processing Benchmarks
   */
  stringProcessing: {
    concatenation: (strings: string[]) => strings.join(' '),
    
    templateLiteral: (data: any) => `Hello ${data.name}, your score is ${data.value}`,
    
    regexMatch: (text: string, pattern: RegExp) => pattern.test(text),
    
    stringReplace: (text: string) => text.replace(/test/g, 'production'),
    
    stringSplit: (text: string) => text.split(' ')
  },

  /**
   * Algorithm Benchmarks
   */
  algorithms: {
    bubbleSort: (arr: number[]) => {
      const sorted = [...arr];
      for (let i = 0; i < sorted.length; i++) {
        for (let j = 0; j < sorted.length - 1; j++) {
          if (sorted[j] > sorted[j + 1]) {
            [sorted[j], sorted[j + 1]] = [sorted[j + 1], sorted[j]];
          }
        }
      }
      return sorted;
    },
    
    quickSort: (arr: number[]): number[] => {
      if (arr.length <= 1) return arr;
      const pivot = arr[Math.floor(arr.length / 2)];
      const left = arr.filter(x => x < pivot);
      const middle = arr.filter(x => x === pivot);
      const right = arr.filter(x => x > pivot);
      return [...CommonBenchmarks.algorithms.quickSort(left), ...middle, ...CommonBenchmarks.algorithms.quickSort(right)];
    },
    
    binarySearch: (arr: number[], target: number) => {
      let left = 0;
      let right = arr.length - 1;
      
      while (left <= right) {
        const mid = Math.floor((left + right) / 2);
        if (arr[mid] === target) return mid;
        if (arr[mid] < target) left = mid + 1;
        else right = mid - 1;
      }
      return -1;
    }
  },

  /**
   * Memory Allocation Benchmarks
   */
  memory: {
    arrayAllocation: (size: number) => new Array(size).fill(0),
    
    objectAllocation: (count: number) => Array.from({ length: count }, (_, i) => ({ id: i, value: Math.random() })),
    
    stringAllocation: (length: number) => 'x'.repeat(length),
    
    mapOperations: (size: number) => {
      const map = new Map();
      for (let i = 0; i < size; i++) {
        map.set(i, `value_${i}`);
      }
      return map;
    },
    
    setOperations: (size: number) => {
      const set = new Set();
      for (let i = 0; i < size; i++) {
        set.add(i);
      }
      return set;
    }
  }
};

// =============================================================================
// LOAD TESTING UTILITIES
// =============================================================================

export class LoadTester {
  private concurrentRequests: number;
  private duration: number;
  private results: Array<{
    timestamp: number;
    duration: number;
    success: boolean;
    error?: string;
  }> = [];

  constructor(concurrentRequests = 10, duration = 10000) {
    this.concurrentRequests = concurrentRequests;
    this.duration = duration;
  }

  /**
   * Run load test
   */
  async runLoadTest(
    testFunction: () => Promise<any>,
    options: {
      rampUpTime?: number;
      coolDownTime?: number;
    } = {}
  ) {
    const { rampUpTime = 1000, coolDownTime = 1000 } = options;
    
    console.log(`Starting load test: ${this.concurrentRequests} concurrent requests for ${this.duration}ms`);
    
    this.results = [];
    const startTime = Date.now();
    const endTime = startTime + this.duration;
    
    // Ramp up
    await this.rampUp(testFunction, rampUpTime);
    
    // Steady state
    const workers = Array.from({ length: this.concurrentRequests }, () => 
      this.runWorker(testFunction, endTime)
    );
    
    await Promise.all(workers);
    
    // Cool down
    await new Promise(resolve => setTimeout(resolve, coolDownTime));
    
    return this.analyzeResults();
  }

  private async rampUp(testFunction: () => Promise<any>, duration: number) {
    const interval = duration / this.concurrentRequests;
    
    for (let i = 0; i < this.concurrentRequests; i++) {
      setTimeout(() => this.runSingleRequest(testFunction), i * interval);
    }
    
    await new Promise(resolve => setTimeout(resolve, duration));
  }

  private async runWorker(testFunction: () => Promise<any>, endTime: number) {
    while (Date.now() < endTime) {
      await this.runSingleRequest(testFunction);
      
      // Small delay to prevent overwhelming
      await new Promise(resolve => setTimeout(resolve, 10));
    }
  }

  private async runSingleRequest(testFunction: () => Promise<any>) {
    const startTime = Date.now();
    
    try {
      await testFunction();
      
      this.results.push({
        timestamp: startTime,
        duration: Date.now() - startTime,
        success: true
      });
    } catch (error) {
      this.results.push({
        timestamp: startTime,
        duration: Date.now() - startTime,
        success: false,
        error: error instanceof Error ? error.message : String(error)
      });
    }
  }

  private analyzeResults() {
    const successful = this.results.filter(r => r.success);
    const failed = this.results.filter(r => !r.success);
    const durations = successful.map(r => r.duration);
    
    const analysis = {
      totalRequests: this.results.length,
      successfulRequests: successful.length,
      failedRequests: failed.length,
      successRate: (successful.length / this.results.length) * 100,
      
      // Timing statistics
      avgResponseTime: durations.reduce((sum, d) => sum + d, 0) / durations.length,
      minResponseTime: Math.min(...durations),
      maxResponseTime: Math.max(...durations),
      
      // Percentiles
      p50: this.calculatePercentile(durations, 50),
      p95: this.calculatePercentile(durations, 95),
      p99: this.calculatePercentile(durations, 99),
      
      // Throughput
      requestsPerSecond: (this.results.length * 1000) / this.duration,
      
      // Errors
      errors: failed.map(r => r.error),
      errorTypes: this.groupErrorsByType(failed)
    };

    console.log('Load test results:');
    console.log(`  Total requests: ${analysis.totalRequests}`);
    console.log(`  Success rate: ${analysis.successRate.toFixed(2)}%`);
    console.log(`  Avg response time: ${analysis.avgResponseTime.toFixed(2)}ms`);
    console.log(`  Requests/sec: ${analysis.requestsPerSecond.toFixed(2)}`);
    console.log(`  95th percentile: ${analysis.p95.toFixed(2)}ms`);

    return analysis;
  }

  private calculatePercentile(values: number[], percentile: number): number {
    const sorted = values.sort((a, b) => a - b);
    const index = Math.ceil((percentile / 100) * sorted.length) - 1;
    return sorted[index] || 0;
  }

  private groupErrorsByType(failures: any[]) {
    const errorGroups = new Map<string, number>();
    
    failures.forEach(failure => {
      const errorType = failure.error?.split(':')[0] || 'Unknown';
      errorGroups.set(errorType, (errorGroups.get(errorType) || 0) + 1);
    });
    
    return Object.fromEntries(errorGroups);
  }
}

// =============================================================================
// PERFORMANCE TEST HELPERS
// =============================================================================

export const PerformanceTestHelpers = {
  /**
   * Create a performance collector
   */
  createCollector: () => new PerformanceCollector(),

  /**
   * Create a benchmark suite
   */
  createSuite: () => new BenchmarkSuite(),

  /**
   * Create a load tester
   */
  createLoadTester: (concurrent = 10, duration = 10000) => new LoadTester(concurrent, duration),

  /**
   * Quick benchmark function
   */
  async quickBench(name: string, fn: () => any, iterations = 100) {
    const suite = new BenchmarkSuite();
    return await suite.runBenchmark(name, fn, { iterations });
  },

  /**
   * Memory usage snapshot
   */
  getMemorySnapshot: () => {
    const usage = process.memoryUsage();
    return {
      heapUsed: Math.round(usage.heapUsed / 1024 / 1024 * 100) / 100, // MB
      heapTotal: Math.round(usage.heapTotal / 1024 / 1024 * 100) / 100, // MB
      external: Math.round(usage.external / 1024 / 1024 * 100) / 100, // MB
      rss: Math.round(usage.rss / 1024 / 1024 * 100) / 100 // MB
    };
  },

  /**
   * Generate test data of specific sizes
   */
  generateTestData: {
    small: () => PerformanceFixtures.smallDataset(),
    medium: () => PerformanceFixtures.mediumDataset(),
    large: () => PerformanceFixtures.largeDataset(),
    memory: (sizeMB: number) => PerformanceFixtures.memoryIntensiveData(sizeMB)
  },

  /**
   * Common benchmark runners
   */
  benchmarkDataProcessing: async (data: any[]) => {
    const suite = new BenchmarkSuite();
    
    await suite.runComparison([
      {
        name: 'Array Map',
        fn: () => CommonBenchmarks.dataProcessing.arrayMap(data),
        itemsProcessed: data.length
      },
      {
        name: 'Array Filter',
        fn: () => CommonBenchmarks.dataProcessing.arrayFilter(data),
        itemsProcessed: data.length
      },
      {
        name: 'Array Reduce',
        fn: () => CommonBenchmarks.dataProcessing.arrayReduce(data),
        itemsProcessed: data.length
      }
    ]);

    return suite.getComparisonResults();
  },

  /**
   * Memory leak detector
   */
  async detectMemoryLeak(fn: () => any, iterations = 100) {
    const measurements = [];
    
    for (let i = 0; i < iterations; i++) {
      const before = process.memoryUsage().heapUsed;
      await fn();
      
      if (global.gc) global.gc();
      
      const after = process.memoryUsage().heapUsed;
      measurements.push(after - before);
      
      // Log every 10 iterations
      if (i % 10 === 0) {
        console.log(`Iteration ${i}: ${Math.round((after - before) / 1024)}KB delta`);
      }
    }

    const avgGrowth = measurements.reduce((sum, m) => sum + m, 0) / measurements.length;
    const trend = this.calculateTrend(measurements);
    
    return {
      avgGrowthPerIteration: avgGrowth,
      totalGrowth: measurements.reduce((sum, m) => sum + m, 0),
      trend, // positive = increasing, negative = decreasing, ~0 = stable
      measurements,
      potentialLeak: trend > 1000 && avgGrowth > 1000 // Threshold for leak detection
    };
  },

  calculateTrend: (values: number[]) => {
    const n = values.length;
    const sumX = n * (n - 1) / 2;
    const sumY = values.reduce((sum, val) => sum + val, 0);
    const sumXY = values.reduce((sum, val, i) => sum + i * val, 0);
    const sumX2 = n * (n - 1) * (2 * n - 1) / 6;
    
    return (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  }
};

export default {
  PerformanceCollector,
  BenchmarkSuite,
  LoadTester,
  CommonBenchmarks,
  PerformanceTestHelpers
};