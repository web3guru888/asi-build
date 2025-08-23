/**
 * Quality Metrics Dashboard Configuration
 * Defines thresholds and monitoring for code quality metrics
 */

module.exports = {
  // ESLint Quality Thresholds
  eslint: {
    errorThreshold: 0,      // Zero errors allowed
    warningThreshold: 50,   // Maximum warnings before alert
    complexityThreshold: 10, // Maximum cyclomatic complexity
    maxLinesPerFunction: 50, // Maximum lines per function
    maxLinesPerFile: 500,   // Maximum lines per file
    maxDepth: 4,            // Maximum nesting depth
    maxParams: 4,           // Maximum function parameters
  },

  // TypeScript Quality Thresholds
  typescript: {
    strictMode: true,
    noImplicitAny: true,
    strictNullChecks: true,
    noUnusedLocals: true,
    noUnusedParameters: true,
    exactOptionalPropertyTypes: true,
  },

  // Code Coverage Thresholds
  coverage: {
    lines: 80,              // Minimum line coverage %
    functions: 80,          // Minimum function coverage %
    branches: 70,           // Minimum branch coverage %
    statements: 80,         // Minimum statement coverage %
  },

  // Performance Thresholds
  performance: {
    buildTime: 120,         // Maximum build time in seconds
    testTime: 60,           // Maximum test execution time in seconds
    bundleSize: 5242880,    // Maximum bundle size in bytes (5MB)
  },

  // Security Thresholds
  security: {
    vulnerabilities: {
      critical: 0,          // Zero critical vulnerabilities
      high: 0,              // Zero high vulnerabilities
      moderate: 5,          // Maximum moderate vulnerabilities
      low: 10,              // Maximum low vulnerabilities
    },
  },

  // Technical Debt Metrics
  technicalDebt: {
    codeSmells: 50,         // Maximum code smells
    duplicatedLines: 3,     // Maximum duplicated lines percentage
    maintainabilityIndex: 70, // Minimum maintainability index
  },

  // Quality Gates
  qualityGates: {
    // Pre-commit requirements
    preCommit: {
      eslintErrors: 0,
      typescriptErrors: 0,
      testsPass: true,
      formattingCheck: true,
    },
    
    // CI/CD requirements
    ci: {
      eslintErrors: 0,
      eslintWarnings: 50,
      codeCoverage: 80,
      securityScan: true,
      performanceTests: true,
    },
    
    // Release requirements
    release: {
      eslintErrors: 0,
      eslintWarnings: 0,
      codeCoverage: 85,
      allTestsPass: true,
      securityAudit: true,
      performanceBenchmark: true,
    },
  },

  // Reporting Configuration
  reporting: {
    formats: ['json', 'html', 'xml'],
    outputDir: './quality-reports',
    includeHistory: true,
    trending: {
      enabled: true,
      retentionDays: 30,
    },
  },

  // Integration Configuration
  integrations: {
    sonarqube: {
      enabled: false,
      serverUrl: process.env.SONAR_HOST_URL,
      projectKey: 'asi-code',
      sources: 'src',
      exclusions: '**/node_modules/**,**/dist/**,**/*.test.ts',
    },
    
    codeclimate: {
      enabled: false,
      testReporter: true,
    },
    
    github: {
      enabled: true,
      checksEnabled: true,
      statusChecks: [
        'lint',
        'typecheck',
        'test',
        'security',
      ],
    },
  },

  // Monitoring Configuration
  monitoring: {
    alerts: {
      enabled: true,
      channels: ['console', 'file'],
      thresholds: {
        eslintErrors: 1,      // Alert on any error
        coverageDrops: 5,     // Alert on 5% coverage drop
        buildFailures: 1,     // Alert on build failure
      },
    },
    
    metrics: {
      collectInterval: '1h',
      retentionPeriod: '30d',
      aggregations: ['hourly', 'daily', 'weekly'],
    },
  },
};