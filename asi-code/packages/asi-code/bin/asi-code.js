#!/usr/bin/env node

/**
 * ASI-Code CLI Entry Point
 */

// Import and run the CLI
import('../dist/cli/index.js').catch((error) => {
  console.error('Failed to start ASI-Code CLI:', error.message);
  process.exit(1);
});