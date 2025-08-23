#!/usr/bin/env node
/**
 * Quality Check Script
 * Runs comprehensive quality checks and generates reports
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const qualityConfig = require('../quality-metrics.config.cjs');

class QualityChecker {
  constructor() {
    this.results = {
      timestamp: new Date().toISOString(),
      eslint: null,
      typescript: null,
      coverage: null,
      security: null,
      performance: null,
      overall: {
        passed: false,
        score: 0,
        issues: [],
      },
    };
    
    this.reportDir = qualityConfig.reporting.outputDir;
    this.ensureReportDirectory();
  }

  ensureReportDirectory() {
    if (!fs.existsSync(this.reportDir)) {
      fs.mkdirSync(this.reportDir, { recursive: true });
    }
  }

  async run() {
    console.log('🔍 Starting comprehensive quality check...\n');

    try {
      await this.runESLintCheck();
      await this.runTypeScriptCheck();
      await this.runSecurityCheck();
      await this.calculateOverallScore();
      await this.generateReport();
      
      this.printSummary();
      
      if (!this.results.overall.passed) {
        process.exit(1);
      }
    } catch (error) {
      console.error('❌ Quality check failed:', error.message);
      process.exit(1);
    }
  }

  async runESLintCheck() {
    console.log('📋 Running ESLint analysis...');
    
    try {
      const output = execSync('npm run lint -- --format=json', { 
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'pipe'],
      });
      
      const eslintResults = JSON.parse(output);
      const summary = this.summarizeESLintResults(eslintResults);
      
      this.results.eslint = {
        passed: summary.errorCount === 0,
        errorCount: summary.errorCount,
        warningCount: summary.warningCount,
        fixableCount: summary.fixableErrorCount + summary.fixableWarningCount,
        files: eslintResults.length,
        details: summary,
      };
      
      console.log(`   ✅ Files analyzed: ${eslintResults.length}`);
      console.log(`   🚨 Errors: ${summary.errorCount}`);
      console.log(`   ⚠️  Warnings: ${summary.warningCount}`);
      console.log(`   🔧 Fixable: ${summary.fixableErrorCount + summary.fixableWarningCount}`);
      
    } catch (error) {
      // ESLint exits with code 1 when issues are found
      const errorOutput = error.stdout || error.message;
      
      try {
        const eslintResults = JSON.parse(errorOutput);
        const summary = this.summarizeESLintResults(eslintResults);
        
        this.results.eslint = {
          passed: false,
          errorCount: summary.errorCount,
          warningCount: summary.warningCount,
          fixableCount: summary.fixableErrorCount + summary.fixableWarningCount,
          files: eslintResults.length,
          details: summary,
        };
        
        console.log(`   ❌ Files analyzed: ${eslintResults.length}`);
        console.log(`   🚨 Errors: ${summary.errorCount}`);
        console.log(`   ⚠️  Warnings: ${summary.warningCount}`);
        
      } catch (parseError) {
        this.results.eslint = {
          passed: false,
          errorCount: -1,
          error: 'Failed to parse ESLint output',
        };
      }
    }
  }

  async runTypeScriptCheck() {
    console.log('\n🔧 Running TypeScript check...');
    
    try {
      execSync('npm run typecheck', { 
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'pipe'],
      });
      
      this.results.typescript = {
        passed: true,
        errors: 0,
      };
      
      console.log('   ✅ TypeScript check passed');
      
    } catch (error) {
      const errorOutput = error.stderr || error.stdout || error.message;
      const errorCount = (errorOutput.match(/error TS\d+:/g) || []).length;
      
      this.results.typescript = {
        passed: false,
        errors: errorCount,
        details: errorOutput,
      };
      
      console.log(`   ❌ TypeScript errors found: ${errorCount}`);
    }
  }

  async runSecurityCheck() {
    console.log('\n🔒 Running security audit...');
    
    try {
      const auditOutput = execSync('npm audit --json', { 
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'pipe'],
      });
      
      const auditResults = JSON.parse(auditOutput);
      const vulnerabilities = auditResults.vulnerabilities || {};
      
      const summary = Object.values(vulnerabilities).reduce((acc, vuln) => {
        const severity = vuln.severity;
        acc[severity] = (acc[severity] || 0) + 1;
        acc.total++;
        return acc;
      }, { critical: 0, high: 0, moderate: 0, low: 0, total: 0 });
      
      this.results.security = {
        passed: summary.critical === 0 && summary.high === 0,
        vulnerabilities: summary,
        auditId: auditResults.auditReportVersion,
      };
      
      console.log(`   🔍 Vulnerabilities found:`);
      console.log(`      Critical: ${summary.critical}`);
      console.log(`      High: ${summary.high}`);
      console.log(`      Moderate: ${summary.moderate}`);
      console.log(`      Low: ${summary.low}`);
      
    } catch (error) {
      // npm audit can exit with non-zero code when vulnerabilities are found
      try {
        const auditOutput = error.stdout;
        const auditResults = JSON.parse(auditOutput);
        const vulnerabilities = auditResults.vulnerabilities || {};
        
        const summary = Object.values(vulnerabilities).reduce((acc, vuln) => {
          const severity = vuln.severity;
          acc[severity] = (acc[severity] || 0) + 1;
          acc.total++;
          return acc;
        }, { critical: 0, high: 0, moderate: 0, low: 0, total: 0 });
        
        this.results.security = {
          passed: summary.critical === 0 && summary.high === 0,
          vulnerabilities: summary,
        };
        
        console.log(`   ⚠️  Vulnerabilities found:`);
        console.log(`      Critical: ${summary.critical}`);
        console.log(`      High: ${summary.high}`);
        console.log(`      Moderate: ${summary.moderate}`);
        console.log(`      Low: ${summary.low}`);
        
      } catch (parseError) {
        this.results.security = {
          passed: false,
          error: 'Failed to parse security audit results',
        };
      }
    }
  }

  summarizeESLintResults(results) {
    return results.reduce((summary, result) => {
      summary.errorCount += result.errorCount || 0;
      summary.warningCount += result.warningCount || 0;
      summary.fixableErrorCount += result.fixableErrorCount || 0;
      summary.fixableWarningCount += result.fixableWarningCount || 0;
      
      // Analyze rule violations
      result.messages?.forEach(message => {
        const rule = message.ruleId || 'unknown';
        summary.ruleViolations[rule] = (summary.ruleViolations[rule] || 0) + 1;
      });
      
      return summary;
    }, {
      errorCount: 0,
      warningCount: 0,
      fixableErrorCount: 0,
      fixableWarningCount: 0,
      ruleViolations: {},
    });
  }

  calculateOverallScore() {
    console.log('\n📊 Calculating overall quality score...');
    
    let score = 100;
    const issues = [];
    
    // ESLint scoring
    if (this.results.eslint) {
      if (this.results.eslint.errorCount > 0) {
        score -= this.results.eslint.errorCount * 2;
        issues.push(`${this.results.eslint.errorCount} ESLint errors`);
      }
      if (this.results.eslint.warningCount > qualityConfig.eslint.warningThreshold) {
        score -= Math.min(10, (this.results.eslint.warningCount - qualityConfig.eslint.warningThreshold) * 0.1);
        issues.push(`Excessive ESLint warnings (${this.results.eslint.warningCount})`);
      }
    }
    
    // TypeScript scoring
    if (this.results.typescript && !this.results.typescript.passed) {
      score -= this.results.typescript.errors * 3;
      issues.push(`${this.results.typescript.errors} TypeScript errors`);
    }
    
    // Security scoring
    if (this.results.security) {
      const vuln = this.results.security.vulnerabilities;
      if (vuln.critical > 0) {
        score -= vuln.critical * 20;
        issues.push(`${vuln.critical} critical security vulnerabilities`);
      }
      if (vuln.high > 0) {
        score -= vuln.high * 10;
        issues.push(`${vuln.high} high security vulnerabilities`);
      }
    }
    
    score = Math.max(0, score);
    
    this.results.overall = {
      passed: score >= 80 && issues.length === 0,
      score: Math.round(score),
      issues,
      grade: this.getGrade(score),
    };
    
    console.log(`   📈 Quality Score: ${this.results.overall.score}/100 (${this.results.overall.grade})`);
  }

  getGrade(score) {
    if (score >= 95) return 'A+';
    if (score >= 90) return 'A';
    if (score >= 85) return 'B+';
    if (score >= 80) return 'B';
    if (score >= 75) return 'C+';
    if (score >= 70) return 'C';
    if (score >= 65) return 'D+';
    if (score >= 60) return 'D';
    return 'F';
  }

  async generateReport() {
    console.log('\n📝 Generating quality report...');
    
    const reportPath = path.join(this.reportDir, `quality-report-${Date.now()}.json`);
    fs.writeFileSync(reportPath, JSON.stringify(this.results, null, 2));
    
    const htmlReportPath = path.join(this.reportDir, 'quality-report.html');
    const htmlContent = this.generateHTMLReport();
    fs.writeFileSync(htmlReportPath, htmlContent);
    
    console.log(`   📄 JSON Report: ${reportPath}`);
    console.log(`   🌐 HTML Report: ${htmlReportPath}`);
  }

  generateHTMLReport() {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ASI-Code Quality Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .score { font-size: 48px; font-weight: bold; color: ${this.results.overall.score >= 80 ? '#22c55e' : this.results.overall.score >= 60 ? '#f59e0b' : '#ef4444'}; }
        .grade { font-size: 24px; margin-top: 10px; }
        .section { margin: 20px 0; padding: 20px; border: 1px solid #e5e7eb; border-radius: 6px; }
        .passed { background-color: #f0fdf4; border-color: #22c55e; }
        .failed { background-color: #fef2f2; border-color: #ef4444; }
        .metric { display: flex; justify-content: space-between; margin: 10px 0; }
        .metric-label { font-weight: bold; }
        .metric-value { color: #6b7280; }
        .issues { margin-top: 15px; }
        .issue { background: #fef2f2; padding: 8px 12px; margin: 5px 0; border-radius: 4px; border-left: 4px solid #ef4444; }
        .timestamp { text-align: center; color: #6b7280; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ASI-Code Quality Report</h1>
            <div class="score">${this.results.overall.score}/100</div>
            <div class="grade">Grade: ${this.results.overall.grade}</div>
        </div>
        
        <div class="section ${this.results.eslint?.passed ? 'passed' : 'failed'}">
            <h2>ESLint Analysis</h2>
            ${this.results.eslint ? `
                <div class="metric">
                    <span class="metric-label">Status:</span>
                    <span class="metric-value">${this.results.eslint.passed ? '✅ Passed' : '❌ Failed'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Errors:</span>
                    <span class="metric-value">${this.results.eslint.errorCount}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Warnings:</span>
                    <span class="metric-value">${this.results.eslint.warningCount}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Fixable Issues:</span>
                    <span class="metric-value">${this.results.eslint.fixableCount}</span>
                </div>
            ` : '<p>ESLint check not completed</p>'}
        </div>
        
        <div class="section ${this.results.typescript?.passed ? 'passed' : 'failed'}">
            <h2>TypeScript Analysis</h2>
            ${this.results.typescript ? `
                <div class="metric">
                    <span class="metric-label">Status:</span>
                    <span class="metric-value">${this.results.typescript.passed ? '✅ Passed' : '❌ Failed'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Type Errors:</span>
                    <span class="metric-value">${this.results.typescript.errors}</span>
                </div>
            ` : '<p>TypeScript check not completed</p>'}
        </div>
        
        <div class="section ${this.results.security?.passed ? 'passed' : 'failed'}">
            <h2>Security Analysis</h2>
            ${this.results.security ? `
                <div class="metric">
                    <span class="metric-label">Status:</span>
                    <span class="metric-value">${this.results.security.passed ? '✅ Passed' : '❌ Failed'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Critical:</span>
                    <span class="metric-value">${this.results.security.vulnerabilities?.critical || 0}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">High:</span>
                    <span class="metric-value">${this.results.security.vulnerabilities?.high || 0}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Moderate:</span>
                    <span class="metric-value">${this.results.security.vulnerabilities?.moderate || 0}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Low:</span>
                    <span class="metric-value">${this.results.security.vulnerabilities?.low || 0}</span>
                </div>
            ` : '<p>Security check not completed</p>'}
        </div>
        
        ${this.results.overall.issues.length > 0 ? `
            <div class="section failed">
                <h2>Issues to Address</h2>
                <div class="issues">
                    ${this.results.overall.issues.map(issue => `<div class="issue">${issue}</div>`).join('')}
                </div>
            </div>
        ` : ''}
        
        <div class="timestamp">
            Generated: ${this.results.timestamp}
        </div>
    </div>
</body>
</html>`;
  }

  printSummary() {
    console.log('\n' + '='.repeat(60));
    console.log('🎯 QUALITY CHECK SUMMARY');
    console.log('='.repeat(60));
    console.log(`📊 Overall Score: ${this.results.overall.score}/100 (${this.results.overall.grade})`);
    console.log(`🎯 Status: ${this.results.overall.passed ? '✅ PASSED' : '❌ FAILED'}`);
    
    if (this.results.overall.issues.length > 0) {
      console.log('\n🚨 Issues to address:');
      this.results.overall.issues.forEach(issue => {
        console.log(`   • ${issue}`);
      });
    }
    
    console.log('\n📝 Detailed reports generated in ./quality-reports/');
    console.log('='.repeat(60));
  }
}

// Run the quality check
if (require.main === module) {
  const checker = new QualityChecker();
  checker.run().catch(error => {
    console.error('Quality check failed:', error);
    process.exit(1);
  });
}

module.exports = QualityChecker;