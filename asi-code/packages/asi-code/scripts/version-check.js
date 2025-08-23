#!/usr/bin/env node

/**
 * Version Consistency Checker
 * 
 * This script validates that all version references across the codebase
 * are consistent with the VERSION file (single source of truth).
 * 
 * Usage: node scripts/version-check.js
 * Exit codes: 0 = success, 1 = inconsistencies found
 */

import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { globSync } from 'glob';

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = join(__dirname, '..');

// ANSI colors for output
const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function getCanonicalVersion() {
  const versionPath = join(rootDir, 'VERSION');
  if (!existsSync(versionPath)) {
    log('ERROR: VERSION file not found!', 'red');
    process.exit(1);
  }
  return readFileSync(versionPath, 'utf8').trim();
}

function checkPackageJson(canonicalVersion) {
  const packagePath = join(rootDir, 'package.json');
  if (!existsSync(packagePath)) {
    return { file: 'package.json', status: 'missing', expected: canonicalVersion, actual: 'N/A' };
  }
  
  const packageJson = JSON.parse(readFileSync(packagePath, 'utf8'));
  const actualVersion = packageJson.version;
  
  return {
    file: 'package.json',
    status: actualVersion === canonicalVersion ? 'ok' : 'mismatch',
    expected: canonicalVersion,
    actual: actualVersion
  };
}

function checkSonarProperties(canonicalVersion) {
  const sonarPath = join(rootDir, 'sonar-project.properties');
  if (!existsSync(sonarPath)) {
    return { file: 'sonar-project.properties', status: 'missing', expected: canonicalVersion, actual: 'N/A' };
  }
  
  const sonarContent = readFileSync(sonarPath, 'utf8');
  const versionMatch = sonarContent.match(/sonar\.projectVersion=([0-9]+\.[0-9]+\.[0-9]+)/);
  const actualVersion = versionMatch ? versionMatch[1] : null;
  
  return {
    file: 'sonar-project.properties',
    status: actualVersion === canonicalVersion ? 'ok' : 'mismatch',
    expected: canonicalVersion,
    actual: actualVersion || 'not found'
  };
}

function checkReadme(canonicalVersion) {
  const readmePath = join(rootDir, 'README.md');
  if (!existsSync(readmePath)) {
    return { file: 'README.md', status: 'missing', expected: canonicalVersion, actual: 'N/A' };
  }
  
  const readmeContent = readFileSync(readmePath, 'utf8');
  const versionMatch = readmeContent.match(/\*\*Version\*\*:\s*([0-9]+\.[0-9]+\.[0-9]+)/);
  const actualVersion = versionMatch ? versionMatch[1] : null;
  
  return {
    file: 'README.md',
    status: actualVersion === canonicalVersion ? 'ok' : 'mismatch',
    expected: canonicalVersion,
    actual: actualVersion || 'not found'
  };
}

function checkSourceFiles(canonicalVersion) {
  const issues = [];
  
  // Check CLI hardcoded fallbacks
  const cliPath = join(rootDir, 'src/cli/index.ts');
  if (existsSync(cliPath)) {
    const cliContent = readFileSync(cliPath, 'utf8');
    
    // Check fallback version in try-catch
    const fallbackMatch = cliContent.match(/version:\s*'([0-9]+\.[0-9]+\.[0-9]+)'/);
    if (fallbackMatch && fallbackMatch[1] !== canonicalVersion) {
      issues.push({
        file: 'src/cli/index.ts (fallback)',
        status: 'mismatch',
        expected: canonicalVersion,
        actual: fallbackMatch[1]
      });
    }
    
    // Check commander version fallback
    const commanderMatch = cliContent.match(/\.version\([^)]*'([0-9]+\.[0-9]+\.[0-9]+)'\)/);
    if (commanderMatch && commanderMatch[1] !== canonicalVersion) {
      issues.push({
        file: 'src/cli/index.ts (commander)',
        status: 'mismatch',
        expected: canonicalVersion,
        actual: commanderMatch[1]
      });
    }
  }
  
  // Check default config
  const configPath = join(rootDir, 'src/config/default-config.ts');
  if (existsSync(configPath)) {
    const configContent = readFileSync(configPath, 'utf8');
    const matches = configContent.matchAll(/version:\s*'([0-9]+\.[0-9]+\.[0-9]+)'/g);
    
    for (const match of matches) {
      if (match[1] !== canonicalVersion) {
        issues.push({
          file: 'src/config/default-config.ts',
          status: 'mismatch',
          expected: canonicalVersion,
          actual: match[1]
        });
      }
    }
  }
  
  return issues;
}

function main() {
  log('🔍 ASI-Code Version Consistency Check', 'blue');
  log('=====================================', 'blue');
  
  const canonicalVersion = getCanonicalVersion();
  log(`📌 Canonical version (from VERSION file): ${canonicalVersion}`, 'green');
  
  const checks = [
    checkPackageJson(canonicalVersion),
    checkSonarProperties(canonicalVersion),
    checkReadme(canonicalVersion),
    ...checkSourceFiles(canonicalVersion)
  ];
  
  let hasIssues = false;
  
  log('\\n📋 Version Check Results:', 'blue');
  log('========================', 'blue');
  
  checks.forEach(check => {
    const status = check.status === 'ok' ? '✅' : check.status === 'missing' ? '⚠️' : '❌';
    const color = check.status === 'ok' ? 'green' : check.status === 'missing' ? 'yellow' : 'red';
    
    log(`${status} ${check.file}`, color);
    
    if (check.status !== 'ok') {
      log(`   Expected: ${check.expected}`, 'blue');
      log(`   Actual:   ${check.actual}`, 'red');
      hasIssues = true;
    }
  });
  
  log('', 'reset');
  
  if (hasIssues) {
    log('❌ Version inconsistencies detected!', 'red');
    log('', 'reset');
    log('To fix these issues:', 'yellow');
    log('1. Update all mismatched files to use version:', canonicalVersion);
    log('2. Consider using the version utility: import { getVersion } from "./src/version.js"', 'yellow');
    log('3. Run this script again to verify fixes', 'yellow');
    process.exit(1);
  } else {
    log('✅ All versions are consistent!', 'green');
    log(`🎉 Everything matches the canonical version: ${canonicalVersion}`, 'green');
    process.exit(0);
  }
}

main();