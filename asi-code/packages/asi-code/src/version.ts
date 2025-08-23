/**
 * Version utilities for ASI-Code
 *
 * This module provides a single source of truth for version information
 * by reading from the VERSION file at the root of the package.
 */

import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

/**
 * Get the current version from the VERSION file
 */
export function getVersion(): string {
  try {
    const versionPath = join(__dirname, '../VERSION');
    const version = readFileSync(versionPath, 'utf8').trim();
    return version || '0.2.0';
  } catch (error) {
    // Fallback to package.json if VERSION file is not available
    try {
      const packagePath = join(__dirname, '../package.json');
      const packageJson = JSON.parse(readFileSync(packagePath, 'utf8'));
      return packageJson.version || '0.2.0';
    } catch (packageError) {
      // Final fallback
      return '0.2.0';
    }
  }
}

/**
 * Get version information object
 */
export function getVersionInfo() {
  const version = getVersion();
  return {
    version,
    major: parseInt(version.split('.')[0]),
    minor: parseInt(version.split('.')[1]),
    patch: parseInt(version.split('.')[2] || '0'),
    toString: () => version,
  };
}

/**
 * Default export for convenience
 */
export default getVersion;
