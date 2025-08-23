#!/usr/bin/env node

/**
 * Version Bump Utility
 * 
 * This script safely updates the version across all files in the codebase
 * maintaining consistency by updating the VERSION file and all references.
 * 
 * Usage: 
 *   node scripts/version-bump.js <new-version>
 *   npm run version:bump <new-version>
 * 
 * Examples:
 *   node scripts/version-bump.js 0.3.0
 *   npm run version:bump 1.0.0
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

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

function validateVersion(version) {
  const versionRegex = /^([0-9]+)\.([0-9]+)\.([0-9]+)(?:-([a-zA-Z0-9-.]+))?$/;
  return versionRegex.test(version);
}

function getCurrentVersion() {
  const versionPath = join(rootDir, 'VERSION');
  if (!existsSync(versionPath)) {
    return null;
  }
  return readFileSync(versionPath, 'utf8').trim();
}

function updateVersionFile(newVersion) {
  const versionPath = join(rootDir, 'VERSION');
  writeFileSync(versionPath, newVersion);
  log(`✅ Updated VERSION file: ${newVersion}`, 'green');
}

function updatePackageJson(newVersion) {
  const packagePath = join(rootDir, 'package.json');
  if (!existsSync(packagePath)) {
    log('⚠️  package.json not found', 'yellow');
    return;
  }
  
  const packageJson = JSON.parse(readFileSync(packagePath, 'utf8'));
  const oldVersion = packageJson.version;
  packageJson.version = newVersion;
  
  writeFileSync(packagePath, JSON.stringify(packageJson, null, 2) + '\\n');
  log(`✅ Updated package.json: ${oldVersion} → ${newVersion}`, 'green');
}

function updateSonarProperties(newVersion) {
  const sonarPath = join(rootDir, 'sonar-project.properties');
  if (!existsSync(sonarPath)) {
    log('⚠️  sonar-project.properties not found', 'yellow');
    return;
  }
  
  let sonarContent = readFileSync(sonarPath, 'utf8');
  const oldVersionMatch = sonarContent.match(/sonar\.projectVersion=([0-9]+\.[0-9]+\.[0-9]+)/);
  const oldVersion = oldVersionMatch ? oldVersionMatch[1] : 'unknown';
  
  sonarContent = sonarContent.replace(
    /sonar\.projectVersion=[0-9]+\.[0-9]+\.[0-9]+/,
    `sonar.projectVersion=${newVersion}`
  );
  
  writeFileSync(sonarPath, sonarContent);
  log(`✅ Updated sonar-project.properties: ${oldVersion} → ${newVersion}`, 'green');
}

function updateReadme(newVersion) {
  const readmePath = join(rootDir, 'README.md');
  if (!existsSync(readmePath)) {
    log('⚠️  README.md not found', 'yellow');
    return;
  }
  
  let readmeContent = readFileSync(readmePath, 'utf8');
  const oldVersionMatch = readmeContent.match(/\*\*Version\*\*:\s*([0-9]+\.[0-9]+\.[0-9]+)/);
  const oldVersion = oldVersionMatch ? oldVersionMatch[1] : 'unknown';
  
  readmeContent = readmeContent.replace(
    /(\*\*Version\*\*:\s*)([0-9]+\.[0-9]+\.[0-9]+)/,
    `$1${newVersion}`
  );
  
  writeFileSync(readmePath, readmeContent);
  log(`✅ Updated README.md: ${oldVersion} → ${newVersion}`, 'green');
}

function updateCliFile(newVersion) {
  const cliPath = join(rootDir, 'src/cli/index.ts');
  if (!existsSync(cliPath)) {
    log('⚠️  src/cli/index.ts not found', 'yellow');
    return;
  }
  
  let cliContent = readFileSync(cliPath, 'utf8');
  
  // Update fallback version in try-catch
  cliContent = cliContent.replace(
    /packageJson = { version: '[0-9]+\.[0-9]+\.[0-9]+' };/,
    `packageJson = { version: '${newVersion}' };`
  );
  
  // Update commander version fallback
  cliContent = cliContent.replace(
    /\.version\(packageJson\.version \|\| '[0-9]+\.[0-9]+\.[0-9]+'\)/,
    `.version(packageJson.version || '${newVersion}')`
  );
  
  writeFileSync(cliPath, cliContent);
  log(`✅ Updated CLI fallback versions: ${newVersion}`, 'green');
}

function updateDefaultConfig(newVersion) {
  const configPath = join(rootDir, 'src/config/default-config.ts');
  if (!existsSync(configPath)) {
    log('⚠️  src/config/default-config.ts not found', 'yellow');
    return;
  }
  
  let configContent = readFileSync(configPath, 'utf8');
  
  // Replace all version occurrences
  configContent = configContent.replace(
    /version: '[0-9]+\.[0-9]+\.[0-9]+'/g,
    `version: '${newVersion}'`
  );
  
  writeFileSync(configPath, configContent);
  log(`✅ Updated default config versions: ${newVersion}`, 'green');
}

function runVersionCheck() {
  try {
    execSync('npm run version:check', { 
      cwd: rootDir, 
      stdio: 'pipe'
    });
    return true;
  } catch (error) {
    return false;
  }
}

function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    log('Usage: node scripts/version-bump.js <new-version>', 'red');
    log('Example: node scripts/version-bump.js 0.3.0', 'yellow');
    process.exit(1);
  }
  
  const newVersion = args[0];
  
  if (!validateVersion(newVersion)) {
    log(`Error: Invalid version format: ${newVersion}`, 'red');
    log('Version must follow semantic versioning (e.g., 1.2.3)', 'yellow');
    process.exit(1);
  }
  
  const currentVersion = getCurrentVersion();
  
  log('🚀 ASI-Code Version Bump Utility', 'blue');
  log('=================================', 'blue');
  
  if (currentVersion) {
    log(`📌 Current version: ${currentVersion}`, 'blue');
  }
  log(`🎯 New version: ${newVersion}`, 'green');
  log('', 'reset');
  
  // Update all version references
  log('📝 Updating version references...', 'blue');
  updateVersionFile(newVersion);
  updatePackageJson(newVersion);
  updateSonarProperties(newVersion);
  updateReadme(newVersion);
  updateCliFile(newVersion);
  updateDefaultConfig(newVersion);
  
  log('', 'reset');
  log('🔍 Verifying version consistency...', 'blue');
  
  if (runVersionCheck()) {
    log('✅ Version bump completed successfully!', 'green');
    log(`🎉 All files now use version: ${newVersion}`, 'green');
    log('', 'reset');
    log('Next steps:', 'yellow');
    log('1. Review the changes: git diff', 'yellow');
    log('2. Test the application: npm run build && npm test', 'yellow');
    log('3. Commit the changes: git add . && git commit -m "bump version to ' + newVersion + '"', 'yellow');
    log('4. Create a git tag: git tag v' + newVersion, 'yellow');
  } else {
    log('❌ Version consistency check failed!', 'red');
    log('Please run "npm run version:check" to see what went wrong.', 'red');
    process.exit(1);
  }
}

main();