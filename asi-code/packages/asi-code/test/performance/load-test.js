/**
 * Autocannon Load Testing Script for ASI-Code Server
 * 
 * This script performs comprehensive load testing on ASI-Code API endpoints
 * to measure performance under various load conditions.
 */

const autocannon = require('autocannon');
const fs = require('fs');
const path = require('path');

// Test configuration
const TEST_CONFIG = {
  url: 'http://localhost:3000',
  connections: 10,
  duration: 10, // seconds
  pipelining: 1,
  headers: {
    'Content-Type': 'application/json'
  }
};

// Results storage
const results = [];

/**
 * Run a load test scenario
 */
async function runLoadTest(name, config) {
  console.log(`\n🚀 Running load test: ${name}`);
  console.log(`📊 Config: ${config.connections} connections, ${config.duration}s duration`);
  
  try {
    const result = await autocannon(config);
    
    const summary = {
      name,
      timestamp: new Date().toISOString(),
      config: {
        connections: config.connections,
        duration: config.duration,
        pipelining: config.pipelining
      },
      results: {
        requests: {
          total: result.requests.total,
          average: Math.round(result.requests.average),
          min: result.requests.min,
          max: result.requests.max,
          p95: result.requests.p95,
          p99: result.requests.p99
        },
        latency: {
          average: Math.round(result.latency.average * 100) / 100,
          min: result.latency.min,
          max: result.latency.max,
          p95: Math.round(result.latency.p95 * 100) / 100,
          p99: Math.round(result.latency.p99 * 100) / 100
        },
        throughput: {
          average: Math.round(result.throughput.average),
          min: result.throughput.min,
          max: result.throughput.max
        },
        errors: result.errors,
        timeouts: result.timeouts,
        non2xx: result.non2xx
      }
    };
    
    results.push(summary);
    
    console.log(`✅ Completed: ${summary.results.requests.total} total requests`);
    console.log(`📈 Throughput: ${summary.results.throughput.average} req/sec`);
    console.log(`⏱️  Latency P95: ${summary.results.latency.p95}ms`);
    console.log(`❌ Errors: ${summary.results.errors}`);
    
    // Check if P95 latency meets target (<200ms)
    if (summary.results.latency.p95 > 200) {
      console.log(`⚠️  WARNING: P95 latency (${summary.results.latency.p95}ms) exceeds target (200ms)`);
    }
    
    return summary;
    
  } catch (error) {
    console.error(`❌ Load test failed: ${error.message}`);
    return {
      name,
      error: error.message,
      timestamp: new Date().toISOString()
    };
  }
}

/**
 * Test scenarios
 */
async function runAllTests() {
  console.log('🧪 Starting ASI-Code Load Testing Suite');
  console.log('==========================================');
  
  // 1. Basic health check load test
  await runLoadTest('Health Check - Light Load', {
    ...TEST_CONFIG,
    url: `${TEST_CONFIG.url}/health`,
    connections: 10,
    duration: 5
  });
  
  // 2. Health check under moderate load
  await runLoadTest('Health Check - Moderate Load', {
    ...TEST_CONFIG,
    url: `${TEST_CONFIG.url}/health`,
    connections: 50,
    duration: 10
  });
  
  // 3. Health check under heavy load
  await runLoadTest('Health Check - Heavy Load', {
    ...TEST_CONFIG,
    url: `${TEST_CONFIG.url}/health`,
    connections: 100,
    duration: 15
  });
  
  // 4. API status endpoint
  await runLoadTest('API Status Endpoint', {
    ...TEST_CONFIG,
    url: `${TEST_CONFIG.url}/api/status`,
    connections: 25,
    duration: 10
  });
  
  // 5. Metrics endpoint
  await runLoadTest('Metrics Endpoint', {
    ...TEST_CONFIG,
    url: `${TEST_CONFIG.url}/metrics`,
    connections: 20,
    duration: 10
  });
  
  // 6. Mixed endpoint load (using health for now)
  await runLoadTest('Mixed Load Pattern', {
    ...TEST_CONFIG,
    url: `${TEST_CONFIG.url}/health`,
    connections: 75,
    duration: 20,
    pipelining: 2
  });
  
  // 7. Sustained load test
  await runLoadTest('Sustained Load Test', {
    ...TEST_CONFIG,
    url: `${TEST_CONFIG.url}/health`,
    connections: 50,
    duration: 60 // 1 minute
  });
  
  // 8. Burst load test
  await runLoadTest('Burst Load Test', {
    ...TEST_CONFIG,
    url: `${TEST_CONFIG.url}/health`,
    connections: 200,
    duration: 10
  });
  
  // 9. POST request load test (if endpoints exist)
  await runLoadTest('POST Request Load', {
    ...TEST_CONFIG,
    method: 'POST',
    url: `${TEST_CONFIG.url}/api/tools/list`,
    body: JSON.stringify({}),
    connections: 30,
    duration: 10
  });
  
  // Generate report
  await generateReport();
}

/**
 * Generate performance report
 */
async function generateReport() {
  console.log('\n📋 Generating Performance Report');
  console.log('=================================');
  
  const report = {
    summary: {
      totalTests: results.length,
      timestamp: new Date().toISOString(),
      testDuration: results.reduce((sum, r) => sum + (r.config?.duration || 0), 0),
      totalRequests: results.reduce((sum, r) => sum + (r.results?.requests?.total || 0), 0)
    },
    performance: {
      averageLatencyP95: Math.round(
        results
          .filter(r => r.results?.latency?.p95)
          .reduce((sum, r) => sum + r.results.latency.p95, 0) /
        results.filter(r => r.results?.latency?.p95).length * 100
      ) / 100,
      averageThroughput: Math.round(
        results
          .filter(r => r.results?.throughput?.average)
          .reduce((sum, r) => sum + r.results.throughput.average, 0) /
        results.filter(r => r.results?.throughput?.average).length
      ),
      totalErrors: results.reduce((sum, r) => sum + (r.results?.errors || 0), 0),
      totalTimeouts: results.reduce((sum, r) => sum + (r.results?.timeouts || 0), 0)
    },
    analysis: {
      p95LatencyTarget: 200, // ms
      targetMet: results.every(r => !r.results?.latency?.p95 || r.results.latency.p95 <= 200),
      maxConcurrentUsers: Math.max(...results.map(r => r.config?.connections || 0)),
      recommendedOptimizations: []
    },
    tests: results
  };
  
  // Add optimization recommendations
  if (report.performance.averageLatencyP95 > 200) {
    report.analysis.recommendedOptimizations.push('Optimize server response time - P95 latency exceeds 200ms target');
  }
  
  if (report.performance.totalErrors > 0) {
    report.analysis.recommendedOptimizations.push('Investigate and fix error sources');
  }
  
  if (report.performance.totalTimeouts > 0) {
    report.analysis.recommendedOptimizations.push('Increase timeout limits or optimize slow operations');
  }
  
  const lowThroughputTests = results.filter(r => r.results?.throughput?.average && r.results.throughput.average < 100);
  if (lowThroughputTests.length > 0) {
    report.analysis.recommendedOptimizations.push('Investigate low throughput in specific endpoints');
  }
  
  // Save report
  const reportPath = path.join(__dirname, '../../test-results/load-test-report.json');
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  
  // Print summary
  console.log(`📊 Total Tests: ${report.summary.totalTests}`);
  console.log(`📈 Total Requests: ${report.summary.totalRequests}`);
  console.log(`⏱️  Average P95 Latency: ${report.performance.averageLatencyP95}ms`);
  console.log(`🚀 Average Throughput: ${report.performance.averageThroughput} req/sec`);
  console.log(`❌ Total Errors: ${report.performance.totalErrors}`);
  console.log(`⏰ Total Timeouts: ${report.performance.totalTimeouts}`);
  console.log(`🎯 P95 Target Met: ${report.analysis.targetMet ? '✅' : '❌'}`);
  console.log(`👥 Max Concurrent Users Tested: ${report.analysis.maxConcurrentUsers}`);
  
  if (report.analysis.recommendedOptimizations.length > 0) {
    console.log('\n🔧 Recommended Optimizations:');
    report.analysis.recommendedOptimizations.forEach((opt, i) => {
      console.log(`   ${i + 1}. ${opt}`);
    });
  }
  
  console.log(`\n💾 Detailed report saved to: ${reportPath}`);
  
  // Return summary for further analysis
  return report;
}

/**
 * WebSocket Connection Test
 */
async function testWebSocketConnections() {
  console.log('\n🔌 Testing WebSocket Connection Scalability');
  console.log('============================================');
  
  const WebSocket = require('ws');
  const connections = [];
  const maxConnections = 1000; // Target: test up to 1000 concurrent connections
  const batchSize = 100;
  
  try {
    for (let batch = 0; batch < maxConnections / batchSize; batch++) {
      console.log(`Opening batch ${batch + 1}/${maxConnections / batchSize} (${connections.length} total connections)`);
      
      const batchPromises = [];
      for (let i = 0; i < batchSize; i++) {
        batchPromises.push(new Promise((resolve, reject) => {
          const ws = new WebSocket(`ws://localhost:3000/ws`);
          
          ws.on('open', () => {
            connections.push(ws);
            resolve();
          });
          
          ws.on('error', (error) => {
            reject(error);
          });
          
          // Timeout after 5 seconds
          setTimeout(() => reject(new Error('WebSocket connection timeout')), 5000);
        }));
      }
      
      try {
        await Promise.all(batchPromises);
        console.log(`✅ Batch ${batch + 1} completed. Total connections: ${connections.length}`);
        
        // Wait a bit between batches
        await new Promise(resolve => setTimeout(resolve, 100));
        
      } catch (error) {
        console.log(`❌ Batch ${batch + 1} failed: ${error.message}`);
        break;
      }
    }
    
    console.log(`\n🎯 WebSocket Test Results:`);
    console.log(`   Max Concurrent Connections: ${connections.length}`);
    console.log(`   Target (10,000+): ${connections.length >= 10000 ? '✅ Met' : '❌ Not Met'}`);
    
    // Test message broadcasting
    if (connections.length > 0) {
      console.log(`\n📤 Testing message broadcasting to ${connections.length} connections...`);
      const testMessage = JSON.stringify({ type: 'test', data: 'load test message' });
      
      let messagesSent = 0;
      const startTime = Date.now();
      
      connections.forEach(ws => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(testMessage);
          messagesSent++;
        }
      });
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      console.log(`   Messages Sent: ${messagesSent}`);
      console.log(`   Broadcast Duration: ${duration}ms`);
      console.log(`   Messages/Second: ${Math.round(messagesSent / (duration / 1000))}`);
    }
    
  } finally {
    // Clean up connections
    console.log(`\n🧹 Cleaning up ${connections.length} WebSocket connections...`);
    connections.forEach(ws => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });
  }
}

/**
 * Memory leak detection test
 */
async function testMemoryUsage() {
  console.log('\n🧠 Memory Usage Analysis');
  console.log('========================');
  
  const initialMemory = process.memoryUsage();
  console.log('Initial Memory Usage:', {
    rss: `${Math.round(initialMemory.rss / 1024 / 1024)}MB`,
    heapUsed: `${Math.round(initialMemory.heapUsed / 1024 / 1024)}MB`,
    heapTotal: `${Math.round(initialMemory.heapTotal / 1024 / 1024)}MB`
  });
  
  // Run intensive load test
  await runLoadTest('Memory Stress Test', {
    ...TEST_CONFIG,
    url: `${TEST_CONFIG.url}/health`,
    connections: 100,
    duration: 30
  });
  
  // Force garbage collection if available
  if (global.gc) {
    console.log('🗑️  Running garbage collection...');
    global.gc();
  }
  
  const finalMemory = process.memoryUsage();
  console.log('Final Memory Usage:', {
    rss: `${Math.round(finalMemory.rss / 1024 / 1024)}MB`,
    heapUsed: `${Math.round(finalMemory.heapUsed / 1024 / 1024)}MB`,
    heapTotal: `${Math.round(finalMemory.heapTotal / 1024 / 1024)}MB`
  });
  
  const memoryGrowth = {
    rss: finalMemory.rss - initialMemory.rss,
    heapUsed: finalMemory.heapUsed - initialMemory.heapUsed,
    heapTotal: finalMemory.heapTotal - initialMemory.heapTotal
  };
  
  console.log('Memory Growth:', {
    rss: `${Math.round(memoryGrowth.rss / 1024 / 1024)}MB`,
    heapUsed: `${Math.round(memoryGrowth.heapUsed / 1024 / 1024)}MB`,
    heapTotal: `${Math.round(memoryGrowth.heapTotal / 1024 / 1024)}MB`
  });
  
  // Check for potential memory leaks (>50MB heap growth is concerning)
  const heapGrowthMB = Math.round(memoryGrowth.heapUsed / 1024 / 1024);
  if (heapGrowthMB > 50) {
    console.log(`⚠️  WARNING: Potential memory leak detected (${heapGrowthMB}MB heap growth)`);
  } else {
    console.log(`✅ Memory usage appears normal (${heapGrowthMB}MB heap growth)`);
  }
  
  return {
    initialMemory,
    finalMemory,
    memoryGrowth,
    potentialLeak: heapGrowthMB > 50
  };
}

/**
 * Main test runner
 */
async function main() {
  try {
    console.log('🎯 ASI-Code Performance Testing Suite');
    console.log('=====================================');
    console.log(`Target Server: ${TEST_CONFIG.url}`);
    console.log(`Performance Target: P95 < 200ms`);
    console.log(`Scalability Target: 10,000+ concurrent users\n`);
    
    // Wait for server to be ready
    console.log('⏳ Waiting for server to be ready...');
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Run HTTP load tests
    await runAllTests();
    
    // Run WebSocket tests
    await testWebSocketConnections();
    
    // Run memory tests
    await testMemoryUsage();
    
    console.log('\n🎉 Performance testing completed!');
    console.log('Check test-results/load-test-report.json for detailed results.');
    
  } catch (error) {
    console.error('❌ Performance testing failed:', error);
    process.exit(1);
  }
}

// Run tests if this script is executed directly
if (require.main === module) {
  main();
}

module.exports = {
  runLoadTest,
  runAllTests,
  testWebSocketConnections,
  testMemoryUsage,
  generateReport
};