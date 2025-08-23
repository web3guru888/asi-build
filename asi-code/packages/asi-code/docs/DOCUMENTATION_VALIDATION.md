# 📚 Documentation Validation System

Comprehensive automated validation system for ASI-Code documentation that prevents documentation drift and ensures high-quality, up-to-date documentation.

## Overview

The documentation validation system implements multiple layers of validation:

1. **API Documentation Validation** - Ensures API.md stays in sync with actual route implementations
2. **Code Examples Testing** - Validates that all code examples in documentation actually work
3. **Documentation Coverage Analysis** - Measures and reports on documentation completeness
4. **Pre-commit Hooks** - Catches documentation issues before they're committed
5. **CI/CD Integration** - Automated validation in GitHub Actions workflows

## System Components

### 🔗 API Documentation Validation

**Script:** `scripts/validate-api-docs.js`  
**Command:** `npm run docs:validate:api`

Compares documented API endpoints in `API.md` with actual implementation in `src/server/routes.ts`:

- Extracts all HTTP endpoints from route definitions
- Parses API.md for documented endpoints
- Reports missing or undocumented endpoints
- Validates HTTP method consistency
- Checks for missing request/response examples

**Features:**
- Handles parameterized routes (`:id`, `*`)
- Skips utility endpoints (health checks, static files)
- Generates detailed JSON reports
- Provides actionable error messages

### 🧪 Code Examples Testing

**Script:** `scripts/test-examples.js`  
**Command:** `npm run docs:validate:examples`

Extracts and tests all code examples from documentation files:

- **JSON Validation** - Verifies JSON examples are syntactically correct
- **JavaScript/TypeScript** - Checks syntax and basic compilation
- **curl Commands** - Tests HTTP requests against running server
- **Bash Scripts** - Validates safe shell commands

**Smart Features:**
- Starts test server automatically
- Skips incomplete examples and placeholders
- Replaces external URLs with localhost for testing
- Handles authentication placeholders gracefully
- Provides detailed error reporting with file locations

### 📊 Documentation Coverage Analysis

**Script:** `scripts/doc-coverage.js`  
**Command:** `npm run docs:coverage`

Comprehensive analysis of documentation completeness:

**Source Code Analysis:**
- JSDoc coverage for functions, classes, and exports
- TypeDoc annotations (`@param`, `@returns`, etc.)
- Usage examples in code comments
- File-level documentation

**API Coverage:**
- Endpoint documentation completeness
- Request/response examples
- Error handling documentation

**Output:**
- Interactive HTML reports with metrics and suggestions
- JSON reports for programmatic analysis
- Coverage scores and improvement recommendations

### 🔍 Pre-commit Hooks

**Config:** `.pre-commit-config.yaml`

Lightweight validation that runs before each commit:

- **Markdown Linting** - Ensures consistent formatting
- **Link Validation** - Checks internal documentation links
- **Quick Example Check** - Basic syntax validation
- **Documentation Freshness** - Alerts for outdated files

### 🚀 CI/CD Integration

**Workflow:** `.github/workflows/docs-validation.yml`

Comprehensive validation in GitHub Actions:

- **Documentation Lint** - Format and style checks
- **API Validation** - Full endpoint synchronization check
- **Examples Testing** - Complete code example validation
- **Coverage Analysis** - Documentation completeness reporting
- **Freshness Check** - Identifies outdated documentation

**PR Integration:**
- Automatic comments with validation results
- Artifact uploads for detailed reports
- Combined status reporting

## Usage Guide

### Initial Setup

1. **Install pre-commit hooks:**
   ```bash
   npm install
   npm run prepare  # Installs husky hooks
   pip install pre-commit
   pre-commit install
   ```

2. **First validation run:**
   ```bash
   npm run docs:validate
   ```

### Daily Workflow

**Before committing changes:**
```bash
# Quick validation (runs automatically on commit)
npm run docs:validate:quick

# Full validation (recommended for major changes)
npm run docs:validate
```

**Generate coverage reports:**
```bash
npm run docs:coverage
# Open docs/validation-reports/doc-coverage-*.html
```

**Check specific aspects:**
```bash
npm run docs:validate:api      # API documentation sync
npm run docs:validate:examples # Code examples testing
npm run docs:freshness         # File age analysis
npm run docs:links            # Internal link validation
```

### Understanding Reports

#### API Validation Report

```json
{
  "summary": {
    "documentedEndpoints": 24,
    "implementedEndpoints": 26,
    "errors": 2,
    "warnings": 3
  },
  "errors": [
    "Endpoint POST /api/v1/tools/:name/execute is implemented but not documented"
  ],
  "warnings": [
    "GET /api/v1/sessions/:id: Missing request example"
  ]
}
```

#### Coverage Report Metrics

- **Overall Score**: Weighted combination of all coverage metrics
- **Source Files Coverage**: Percentage of files with adequate documentation
- **Exports Coverage**: Percentage of exported functions/classes with JSDoc
- **API Endpoints Coverage**: Percentage of endpoints documented in API.md

#### Example Test Results

```json
{
  "summary": {
    "total": 45,
    "passed": 38,
    "failed": 2,
    "skipped": 5
  },
  "failedTests": [
    {
      "file": "API.md",
      "line": 127,
      "language": "bash",
      "error": "curl command failed with status 404"
    }
  ]
}
```

## Configuration

### Validation Thresholds

Edit thresholds in validation scripts:

```javascript
// scripts/validate-api-docs.js
const REQUIRED_COVERAGE = 90; // Minimum API documentation coverage

// scripts/doc-coverage.js  
const SCORE_THRESHOLDS = {
  excellent: 80,
  good: 50,
  needsWork: 30
};
```

### Pre-commit Hook Configuration

Customize `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: validate-api-docs
      files: '^(API\.md|src/server/routes\.ts)$'
      # Only run on API-related changes
```

### CI/CD Triggers

Modify `.github/workflows/docs-validation.yml`:

```yaml
on:
  push:
    paths:
      - '**.md'
      - 'src/server/routes.ts'
      # Add more trigger patterns
```

## Best Practices

### Documentation Standards

1. **API Endpoints** - Every endpoint should have:
   - Clear description
   - Request/response examples
   - Error cases
   - Authentication requirements

2. **Code Examples** - All examples should:
   - Be complete and runnable
   - Use realistic (but safe) data
   - Include error handling
   - Work with current API version

3. **Source Code** - Functions and classes should have:
   - JSDoc comments with descriptions
   - `@param` and `@returns` annotations
   - Usage examples via `@example`
   - Clear parameter types

### Maintenance Workflow

**Weekly:**
- Run full documentation validation
- Review coverage reports for trends
- Update outdated documentation flagged by freshness checks

**Before Major Releases:**
- Ensure 90%+ API documentation coverage
- Validate all code examples work
- Update version-specific documentation

**When Adding New Features:**
- Document new API endpoints immediately
- Add working code examples
- Update relevant documentation sections

### Troubleshooting

**Common Issues:**

1. **"Endpoint not documented" errors**
   - Check if endpoint path matches exactly (including parameters)
   - Verify HTTP method is correct
   - Ensure endpoint is public-facing (not internal utility)

2. **"Code example failed" errors**
   - Check for placeholder values (`your-api-key`, etc.)
   - Verify external dependencies are available
   - Ensure examples work with current API version

3. **"Documentation outdated" warnings**
   - Update file timestamps with meaningful changes
   - Review if content needs updating after code changes
   - Consider if file is actually obsolete

4. **Pre-commit hook failures**
   - Run individual validation commands to identify specific issues
   - Use `--no-verify` flag only for urgent fixes (discouraged)
   - Fix issues before committing for better code quality

## Integration with Development Workflow

### VS Code Integration

Add to `.vscode/tasks.json`:

```json
{
  "label": "Validate Documentation",
  "type": "npm",
  "script": "docs:validate",
  "group": "test"
}
```

### IDE Setup

Configure your editor to:
- Highlight JSDoc syntax
- Validate markdown on save
- Show documentation coverage metrics
- Auto-format documentation files

### Team Adoption

1. **Training** - Ensure team understands validation requirements
2. **Guidelines** - Establish documentation standards and examples
3. **Code Reviews** - Include documentation quality in review checklist
4. **Metrics** - Track documentation coverage over time

## Extending the System

### Adding New Validation Rules

1. **Create validator function** in relevant script
2. **Add configuration options** for thresholds
3. **Include in reports** with actionable messages
4. **Test thoroughly** with various scenarios

### Custom Report Formats

Extend reporting by:
- Adding new output formats (PDF, CSV, etc.)
- Integrating with documentation sites
- Creating dashboard visualizations
- Sending notifications on quality changes

### Integration with Other Tools

- **Swagger/OpenAPI** - Auto-generate API documentation
- **TypeDoc** - Extract documentation from TypeScript code
- **JSDoc** - Generate API documentation from comments
- **Documentation sites** - Integrate with GitBook, Docusaurus, etc.

---

This documentation validation system ensures your project maintains high-quality, accurate documentation that evolves with your codebase. By catching documentation issues early and providing actionable feedback, it helps maintain the professional standards expected of the ASI-Code project.