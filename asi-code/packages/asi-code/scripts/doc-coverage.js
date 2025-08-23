#!/usr/bin/env node

/**
 * Documentation Coverage Reporting System
 * 
 * Analyzes code coverage for documentation, generates detailed reports,
 * and provides actionable insights for improving documentation quality.
 * 
 * Usage: npm run docs:coverage
 */

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');

// Console colors
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m'
};

class DocumentationCoverageAnalyzer {
  constructor() {
    this.sourceFiles = new Map();
    this.documentationFiles = new Map();
    this.apiEndpoints = new Map();
    this.coverage = {
      timestamp: new Date().toISOString(),
      summary: {
        totalSourceFiles: 0,
        documentedSourceFiles: 0,
        sourceFilesCoverage: 0,
        totalExports: 0,
        documentedExports: 0,
        exportsCoverage: 0,
        totalEndpoints: 0,
        documentedEndpoints: 0,
        endpointsCoverage: 0,
        overallScore: 0
      },
      files: {},
      endpoints: {},
      suggestions: [],
      metrics: {
        jsDocCoverage: 0,
        typeDocCoverage: 0,
        examplesCoverage: 0,
        linkValidation: 0
      }
    };
  }

  log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
  }

  /**
   * Find all source files in the project
   */
  async findSourceFiles() {
    const srcDir = path.join(PROJECT_ROOT, 'src');
    const files = [];
    
    const walk = async (dir) => {
      try {
        const entries = await fs.readdir(dir, { withFileTypes: true });
        
        for (const entry of entries) {
          const fullPath = path.join(dir, entry.name);
          
          if (entry.isDirectory()) {
            await walk(fullPath);
          } else if (entry.name.endsWith('.ts') && 
                     !entry.name.endsWith('.test.ts') && 
                     !entry.name.endsWith('.spec.ts') &&
                     !entry.name.endsWith('.d.ts')) {
            files.push(fullPath);
          }
        }
      } catch (error) {
        // Directory doesn't exist or can't be read
      }
    };
    
    await walk(srcDir);
    return files;
  }

  /**
   * Find all documentation files
   */
  async findDocumentationFiles() {
    const docFiles = [];
    const searchPaths = [
      path.join(PROJECT_ROOT, 'README.md'),
      path.join(PROJECT_ROOT, 'API.md'),
      path.join(PROJECT_ROOT, 'DEPLOYMENT.md'),
      path.join(PROJECT_ROOT, 'docs')
    ];

    for (const searchPath of searchPaths) {
      try {
        const stat = await fs.stat(searchPath);
        if (stat.isFile() && searchPath.endsWith('.md')) {
          docFiles.push(searchPath);
        } else if (stat.isDirectory()) {
          const files = await this.findMarkdownInDir(searchPath);
          docFiles.push(...files);
        }
      } catch (error) {
        // Path doesn't exist
      }
    }

    return docFiles;
  }

  /**
   * Recursively find markdown files in directory
   */
  async findMarkdownInDir(dir) {
    const files = [];
    
    try {
      const entries = await fs.readdir(dir, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        
        if (entry.isDirectory()) {
          const subFiles = await this.findMarkdownInDir(fullPath);
          files.push(...subFiles);
        } else if (entry.name.endsWith('.md')) {
          files.push(fullPath);
        }
      }
    } catch (error) {
      // Directory can't be read
    }
    
    return files;
  }

  /**
   * Analyze a TypeScript source file for documentation
   */
  async analyzeSourceFile(filePath) {
    const content = await fs.readFile(filePath, 'utf-8');
    const relativePath = path.relative(PROJECT_ROOT, filePath);
    
    const analysis = {
      path: relativePath,
      fileSize: content.length,
      exports: [],
      classes: [],
      interfaces: [],
      functions: [],
      hasFileDoc: false,
      jsDocBlocks: 0,
      commentLines: 0,
      codeLines: 0,
      documentationRatio: 0,
      coverage: {
        hasJSDoc: false,
        hasTypeDoc: false,
        hasComments: false,
        hasExamples: false,
        score: 0
      }
    };

    // Count lines
    const lines = content.split('\n');
    analysis.codeLines = lines.filter(line => 
      line.trim() && !line.trim().startsWith('//') && !line.trim().startsWith('*')
    ).length;
    analysis.commentLines = lines.filter(line => 
      line.trim().startsWith('//') || line.trim().startsWith('*')
    ).length;

    // Check for file-level documentation
    analysis.hasFileDoc = /^\/\*\*[\s\S]*?\*\//.test(content);
    
    // Count JSDoc blocks
    const jsDocMatches = content.match(/\/\*\*[\s\S]*?\*\//g) || [];
    analysis.jsDocBlocks = jsDocMatches.length;
    
    // Extract exports, classes, interfaces, functions
    this.extractCodeElements(content, analysis);
    
    // Calculate documentation ratio
    analysis.documentationRatio = analysis.commentLines / (analysis.codeLines + analysis.commentLines) || 0;
    
    // Determine coverage scores
    analysis.coverage.hasJSDoc = analysis.jsDocBlocks > 0;
    analysis.coverage.hasTypeDoc = /@param|@returns|@description|@example/.test(content);
    analysis.coverage.hasComments = analysis.commentLines > 0;
    analysis.coverage.hasExamples = /@example/.test(content);
    
    // Calculate overall score
    let score = 0;
    if (analysis.hasFileDoc) score += 20;
    if (analysis.coverage.hasJSDoc) score += 30;
    if (analysis.coverage.hasTypeDoc) score += 25;
    if (analysis.coverage.hasComments) score += 15;
    if (analysis.coverage.hasExamples) score += 10;
    
    analysis.coverage.score = score;
    
    return analysis;
  }

  /**
   * Extract code elements (exports, classes, functions, etc.)
   */
  extractCodeElements(content, analysis) {
    // Extract exports
    const exportMatches = content.match(/export\s+(class|function|const|interface|type)\s+(\w+)/g) || [];
    for (const match of exportMatches) {
      const [, type, name] = match.match(/export\s+(class|function|const|interface|type)\s+(\w+)/) || [];
      if (name) {
        const hasDoc = new RegExp(`/\\*\\*[\\s\\S]*?\\*/\\s*export\\s+${type}\\s+${name}`).test(content);
        analysis.exports.push({ type, name, hasDoc });
      }
    }
    
    // Extract classes
    const classMatches = content.match(/class\s+(\w+)/g) || [];
    for (const match of classMatches) {
      const name = match.split(/\s+/)[1];
      const hasDoc = new RegExp(`/\\*\\*[\\s\\S]*?\\*/\\s*(?:export\\s+)?class\\s+${name}`).test(content);
      analysis.classes.push({ name, hasDoc });
    }
    
    // Extract interfaces
    const interfaceMatches = content.match(/interface\s+(\w+)/g) || [];
    for (const match of interfaceMatches) {
      const name = match.split(/\s+/)[1];
      const hasDoc = new RegExp(`/\\*\\*[\\s\\S]*?\\*/\\s*(?:export\\s+)?interface\\s+${name}`).test(content);
      analysis.interfaces.push({ name, hasDoc });
    }
    
    // Extract functions
    const functionMatches = content.match(/(?:function\s+(\w+)|(\w+)\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*\{)/g) || [];
    for (const match of functionMatches) {
      const functionName = match.match(/function\s+(\w+)|(\w+)\s*\(/);
      const name = functionName?.[1] || functionName?.[2];
      if (name && !['constructor', 'if', 'for', 'while', 'switch'].includes(name)) {
        const hasDoc = new RegExp(`/\\*\\*[\\s\\S]*?\\*/\\s*(?:export\\s+)?(?:async\\s+)?function\\s+${name}|/\\*\\*[\\s\\S]*?\\*/\\s*${name}\\s*\\(`).test(content);
        analysis.functions.push({ name, hasDoc });
      }
    }
  }

  /**
   * Extract API endpoints from routes file
   */
  async extractAPIEndpoints() {
    const routesFile = path.join(PROJECT_ROOT, 'src', 'server', 'routes.ts');
    
    try {
      const content = await fs.readFile(routesFile, 'utf-8');
      const endpointPattern = /app\.(get|post|put|delete|patch)\s*\(\s*['"`]([^'"`]+)['"`]/g;
      let match;
      
      while ((match = endpointPattern.exec(content)) !== null) {
        const [, method, path] = match;
        const key = `${method.toUpperCase()} ${path}`;
        this.apiEndpoints.set(key, {
          method: method.toUpperCase(),
          path,
          line: content.substring(0, match.index).split('\n').length,
          documented: false
        });
      }
    } catch (error) {
      this.log(`Warning: Could not analyze routes file: ${error.message}`, 'yellow');
    }
  }

  /**
   * Check API documentation coverage
   */
  async checkAPIDocumentation() {
    const apiFile = path.join(PROJECT_ROOT, 'API.md');
    
    try {
      const content = await fs.readFile(apiFile, 'utf-8');
      const documentedPattern = /#### (GET|POST|PUT|DELETE|PATCH) ([^\s]+)/g;
      let match;
      
      const documented = new Set();
      while ((match = documentedPattern.exec(content)) !== null) {
        const [, method, path] = match;
        const key = `${method.toUpperCase()} ${path}`;
        documented.add(key);
      }
      
      // Update endpoint documentation status
      for (const [key, endpoint] of this.apiEndpoints) {
        const normalizedKey = this.normalizeEndpointForComparison(key);
        let isDocumented = false;
        
        for (const docKey of documented) {
          if (this.endpointsMatch(normalizedKey, this.normalizeEndpointForComparison(docKey))) {
            isDocumented = true;
            break;
          }
        }
        
        endpoint.documented = isDocumented;
        this.coverage.endpoints[key] = {
          ...endpoint,
          documented: isDocumented
        };
      }
      
    } catch (error) {
      this.log(`Warning: Could not analyze API documentation: ${error.message}`, 'yellow');
    }
  }

  /**
   * Normalize endpoint paths for comparison
   */
  normalizeEndpointForComparison(endpoint) {
    return endpoint.replace(/:([^/]+)/g, ':param').replace(/\/+/g, '/').replace(/\/$/, '');
  }

  /**
   * Check if two endpoints match (accounting for parameters)
   */
  endpointsMatch(endpoint1, endpoint2) {
    const normalize = (ep) => ep.replace(/:param/g, ':x').replace(/\/+/g, '/').replace(/\/$/, '');
    return normalize(endpoint1) === normalize(endpoint2);
  }

  /**
   * Analyze documentation files for coverage information
   */
  async analyzeDocumentationFiles() {
    const docFiles = await this.findDocumentationFiles();
    
    for (const filePath of docFiles) {
      try {
        const content = await fs.readFile(filePath, 'utf-8');
        const relativePath = path.relative(PROJECT_ROOT, filePath);
        
        const analysis = {
          path: relativePath,
          wordCount: content.split(/\s+/).length,
          codeBlocks: (content.match(/```[\s\S]*?```/g) || []).length,
          links: (content.match(/\[.*?\]\(.*?\)/g) || []).length,
          images: (content.match(/!\[.*?\]\(.*?\)/g) || []).length,
          headings: (content.match(/^#+\s+/gm) || []).length,
          examples: (content.match(/```(?:javascript|typescript|bash|json)/gi) || []).length,
          lastModified: null
        };
        
        this.documentationFiles.set(relativePath, analysis);
      } catch (error) {
        this.log(`Warning: Could not analyze ${filePath}: ${error.message}`, 'yellow');
      }
    }
  }

  /**
   * Generate coverage suggestions
   */
  generateSuggestions() {
    const suggestions = [];
    
    // Source file suggestions
    const undocumentedFiles = Array.from(this.sourceFiles.values())
      .filter(file => file.coverage.score < 50)
      .sort((a, b) => a.coverage.score - b.coverage.score);
    
    if (undocumentedFiles.length > 0) {
      suggestions.push({
        type: 'source_files',
        priority: 'high',
        title: `${undocumentedFiles.length} source files need better documentation`,
        description: 'Add JSDoc comments, TypeDoc annotations, and examples to improve coverage',
        files: undocumentedFiles.slice(0, 5).map(f => f.path)
      });
    }
    
    // API endpoint suggestions
    const undocumentedEndpoints = Array.from(this.apiEndpoints.values())
      .filter(endpoint => !endpoint.documented);
    
    if (undocumentedEndpoints.length > 0) {
      suggestions.push({
        type: 'api_endpoints',
        priority: 'high',
        title: `${undocumentedEndpoints.length} API endpoints are not documented`,
        description: 'Add these endpoints to API.md with request/response examples',
        endpoints: undocumentedEndpoints.slice(0, 5).map(e => `${e.method} ${e.path}`)
      });
    }
    
    // Missing examples suggestion
    const filesWithoutExamples = Array.from(this.sourceFiles.values())
      .filter(file => !file.coverage.hasExamples && file.exports.length > 0);
    
    if (filesWithoutExamples.length > 0) {
      suggestions.push({
        type: 'examples',
        priority: 'medium',
        title: `${filesWithoutExamples.length} files could benefit from usage examples`,
        description: 'Add @example tags to JSDoc comments to show how to use exported functions/classes',
        files: filesWithoutExamples.slice(0, 3).map(f => f.path)
      });
    }
    
    // Documentation structure suggestions
    if (!this.documentationFiles.has('README.md')) {
      suggestions.push({
        type: 'structure',
        priority: 'high',
        title: 'Missing README.md',
        description: 'Create a comprehensive README with project overview, setup instructions, and usage examples'
      });
    }
    
    if (!this.documentationFiles.has('API.md') && this.apiEndpoints.size > 0) {
      suggestions.push({
        type: 'structure',
        priority: 'high',
        title: 'Missing API.md',
        description: 'Create API documentation with endpoint descriptions, request/response examples'
      });
    }
    
    return suggestions;
  }

  /**
   * Calculate overall coverage metrics
   */
  calculateOverallMetrics() {
    const sourceFilesArray = Array.from(this.sourceFiles.values());
    
    // Source files coverage
    this.coverage.summary.totalSourceFiles = sourceFilesArray.length;
    this.coverage.summary.documentedSourceFiles = sourceFilesArray.filter(f => f.coverage.score >= 50).length;
    this.coverage.summary.sourceFilesCoverage = this.coverage.summary.totalSourceFiles > 0 
      ? (this.coverage.summary.documentedSourceFiles / this.coverage.summary.totalSourceFiles) * 100 
      : 0;
    
    // Exports coverage
    const allExports = sourceFilesArray.flatMap(f => f.exports);
    this.coverage.summary.totalExports = allExports.length;
    this.coverage.summary.documentedExports = allExports.filter(e => e.hasDoc).length;
    this.coverage.summary.exportsCoverage = this.coverage.summary.totalExports > 0
      ? (this.coverage.summary.documentedExports / this.coverage.summary.totalExports) * 100
      : 0;
    
    // API endpoints coverage
    this.coverage.summary.totalEndpoints = this.apiEndpoints.size;
    this.coverage.summary.documentedEndpoints = Array.from(this.apiEndpoints.values()).filter(e => e.documented).length;
    this.coverage.summary.endpointsCoverage = this.coverage.summary.totalEndpoints > 0
      ? (this.coverage.summary.documentedEndpoints / this.coverage.summary.totalEndpoints) * 100
      : 0;
    
    // Specific metrics
    this.coverage.metrics.jsDocCoverage = sourceFilesArray.filter(f => f.coverage.hasJSDoc).length / sourceFilesArray.length * 100;
    this.coverage.metrics.typeDocCoverage = sourceFilesArray.filter(f => f.coverage.hasTypeDoc).length / sourceFilesArray.length * 100;
    this.coverage.metrics.examplesCoverage = sourceFilesArray.filter(f => f.coverage.hasExamples).length / sourceFilesArray.length * 100;
    
    // Overall score (weighted average)
    const weights = {
      sourceFiles: 0.4,
      exports: 0.3,
      endpoints: 0.3
    };
    
    this.coverage.summary.overallScore = 
      (this.coverage.summary.sourceFilesCoverage * weights.sourceFiles +
       this.coverage.summary.exportsCoverage * weights.exports +
       this.coverage.summary.endpointsCoverage * weights.endpoints);
  }

  /**
   * Generate HTML report
   */
  async generateHTMLReport() {
    const htmlTemplate = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentation Coverage Report</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f7fa; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; margin-bottom: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric { background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; }
        .metric h3 { margin: 0 0 10px 0; color: #495057; font-size: 14px; text-transform: uppercase; }
        .metric .value { font-size: 2em; font-weight: bold; margin-bottom: 5px; }
        .metric .label { color: #6c757d; font-size: 14px; }
        .high { color: #28a745; }
        .medium { color: #ffc107; }
        .low { color: #dc3545; }
        .section { margin-bottom: 30px; }
        .section h2 { color: #495057; border-bottom: 2px solid #e9ecef; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e9ecef; }
        th { background-color: #f8f9fa; font-weight: 600; }
        .progress-bar { width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%); transition: width 0.3s ease; }
        .suggestion { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 15px; border-radius: 0 4px 4px 0; }
        .suggestion.high { border-left-color: #dc3545; background: #f8d7da; }
        .suggestion.medium { border-left-color: #ffc107; background: #fff3cd; }
        .suggestion.low { border-left-color: #17a2b8; background: #d1ecf1; }
        .file-list { max-height: 200px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; }
        .timestamp { color: #6c757d; font-size: 14px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Documentation Coverage Report</h1>
        <div class="timestamp">Generated: ${new Date(this.coverage.timestamp).toLocaleString()}</div>
        
        <div class="summary">
            <div class="metric">
                <h3>Overall Score</h3>
                <div class="value ${this.getScoreClass(this.coverage.summary.overallScore)}">${Math.round(this.coverage.summary.overallScore)}%</div>
                <div class="label">Documentation Quality</div>
            </div>
            <div class="metric">
                <h3>Source Files</h3>
                <div class="value ${this.getScoreClass(this.coverage.summary.sourceFilesCoverage)}">${Math.round(this.coverage.summary.sourceFilesCoverage)}%</div>
                <div class="label">${this.coverage.summary.documentedSourceFiles}/${this.coverage.summary.totalSourceFiles} files</div>
            </div>
            <div class="metric">
                <h3>Exports</h3>
                <div class="value ${this.getScoreClass(this.coverage.summary.exportsCoverage)}">${Math.round(this.coverage.summary.exportsCoverage)}%</div>
                <div class="label">${this.coverage.summary.documentedExports}/${this.coverage.summary.totalExports} exports</div>
            </div>
            <div class="metric">
                <h3>API Endpoints</h3>
                <div class="value ${this.getScoreClass(this.coverage.summary.endpointsCoverage)}">${Math.round(this.coverage.summary.endpointsCoverage)}%</div>
                <div class="label">${this.coverage.summary.documentedEndpoints}/${this.coverage.summary.totalEndpoints} endpoints</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Coverage Metrics</h2>
            <table>
                <tr><td>JSDoc Coverage</td><td>${Math.round(this.coverage.metrics.jsDocCoverage)}%</td></tr>
                <tr><td>TypeDoc Coverage</td><td>${Math.round(this.coverage.metrics.typeDocCoverage)}%</td></tr>
                <tr><td>Examples Coverage</td><td>${Math.round(this.coverage.metrics.examplesCoverage)}%</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>🔧 Improvement Suggestions</h2>
            ${this.coverage.suggestions.map(suggestion => `
                <div class="suggestion ${suggestion.priority}">
                    <strong>${suggestion.title}</strong>
                    <p>${suggestion.description}</p>
                    ${suggestion.files ? `<div class="file-list">${suggestion.files.join('<br>')}</div>` : ''}
                    ${suggestion.endpoints ? `<div class="file-list">${suggestion.endpoints.join('<br>')}</div>` : ''}
                </div>
            `).join('')}
        </div>
        
        <div class="section">
            <h2>📁 Source Files Analysis</h2>
            <table>
                <tr><th>File</th><th>Score</th><th>JSDoc</th><th>TypeDoc</th><th>Examples</th><th>Exports</th></tr>
                ${Array.from(this.sourceFiles.values()).sort((a, b) => a.coverage.score - b.coverage.score).map(file => `
                    <tr>
                        <td><code>${file.path}</code></td>
                        <td><span class="${this.getScoreClass(file.coverage.score)}">${file.coverage.score}%</span></td>
                        <td>${file.coverage.hasJSDoc ? '✅' : '❌'}</td>
                        <td>${file.coverage.hasTypeDoc ? '✅' : '❌'}</td>
                        <td>${file.coverage.hasExamples ? '✅' : '❌'}</td>
                        <td>${file.exports.length}</td>
                    </tr>
                `).join('')}
            </table>
        </div>
    </div>
</body>
</html>`;
    
    const reportsDir = path.join(PROJECT_ROOT, 'docs', 'validation-reports');
    await fs.mkdir(reportsDir, { recursive: true });
    
    const htmlFile = path.join(reportsDir, `doc-coverage-${Date.now()}.html`);
    await fs.writeFile(htmlFile, htmlTemplate);
    
    return htmlFile;
  }

  /**
   * Get CSS class for score color coding
   */
  getScoreClass(score) {
    if (score >= 80) return 'high';
    if (score >= 50) return 'medium';
    return 'low';
  }

  /**
   * Save JSON report
   */
  async saveJSONReport() {
    const reportsDir = path.join(PROJECT_ROOT, 'docs', 'validation-reports');
    await fs.mkdir(reportsDir, { recursive: true });
    
    const jsonFile = path.join(reportsDir, `doc-coverage-${Date.now()}.json`);
    await fs.writeFile(jsonFile, JSON.stringify(this.coverage, null, 2));
    
    return jsonFile;
  }

  /**
   * Main analysis runner
   */
  async analyze() {
    this.log('\n📊 Starting Documentation Coverage Analysis\n', 'cyan');

    // Find and analyze source files
    const sourceFiles = await this.findSourceFiles();
    this.log(`Found ${sourceFiles.length} source files to analyze`, 'blue');
    
    for (const filePath of sourceFiles) {
      const analysis = await this.analyzeSourceFile(filePath);
      this.sourceFiles.set(analysis.path, analysis);
      this.coverage.files[analysis.path] = analysis;
    }

    // Analyze documentation files
    await this.analyzeDocumentationFiles();
    this.log(`Found ${this.documentationFiles.size} documentation files`, 'blue');

    // Extract and analyze API endpoints
    await this.extractAPIEndpoints();
    this.log(`Found ${this.apiEndpoints.size} API endpoints`, 'blue');
    
    await this.checkAPIDocumentation();

    // Calculate overall metrics
    this.calculateOverallMetrics();

    // Generate suggestions
    this.coverage.suggestions = this.generateSuggestions();

    // Generate reports
    const htmlReport = await this.generateHTMLReport();
    const jsonReport = await this.saveJSONReport();

    // Print summary
    this.log('\n📊 COVERAGE ANALYSIS SUMMARY', 'magenta');
    this.log('='.repeat(50), 'magenta');
    this.log(`Overall Score: ${Math.round(this.coverage.summary.overallScore)}%`, 
             this.getScoreClass(this.coverage.summary.overallScore));
    this.log(`Source Files: ${Math.round(this.coverage.summary.sourceFilesCoverage)}% (${this.coverage.summary.documentedSourceFiles}/${this.coverage.summary.totalSourceFiles})`, 'cyan');
    this.log(`Exports: ${Math.round(this.coverage.summary.exportsCoverage)}% (${this.coverage.summary.documentedExports}/${this.coverage.summary.totalExports})`, 'cyan');
    this.log(`API Endpoints: ${Math.round(this.coverage.summary.endpointsCoverage)}% (${this.coverage.summary.documentedEndpoints}/${this.coverage.summary.totalEndpoints})`, 'cyan');
    
    this.log('\n📁 Reports Generated:', 'blue');
    this.log(`HTML Report: ${htmlReport}`, 'green');
    this.log(`JSON Report: ${jsonReport}`, 'green');
    
    if (this.coverage.suggestions.length > 0) {
      this.log('\n🔧 Top Suggestions:', 'yellow');
      this.coverage.suggestions.slice(0, 3).forEach(suggestion => {
        this.log(`• ${suggestion.title}`, 'yellow');
      });
    }

    return this.coverage;
  }
}

// Run analysis if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const analyzer = new DocumentationCoverageAnalyzer();
  analyzer.analyze()
    .then(coverage => {
      const score = Math.round(coverage.summary.overallScore);
      console.log(`\n🎯 Final Score: ${score}%`);
      
      // Exit with appropriate code
      if (score >= 80) {
        console.log('🎉 Excellent documentation coverage!');
        process.exit(0);
      } else if (score >= 50) {
        console.log('📈 Good start, but room for improvement!');
        process.exit(0);
      } else {
        console.log('📚 Significant documentation improvements needed');
        process.exit(1);
      }
    })
    .catch(error => {
      console.error('Coverage analysis failed:', error);
      process.exit(1);
    });
}

export default DocumentationCoverageAnalyzer;