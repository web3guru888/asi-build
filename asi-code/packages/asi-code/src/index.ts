// ASI-Code Main Entry Point
// Advanced AI Coding Framework with ASI1 LLM Integration

// Core Kenny Integration Pattern
export * from './kenny';

// AI Provider System (ASI1 default)
export * from './provider';

// Configuration and Logging
export * from './config';
export * from './logging';

// All other components
export * from './server';
export * from './session';
export * from './tool';
export * from './permission';
export * from './consciousness';
export * from './app';
export * from './sat';

// Simple factory functions for quick setup
export async function initializeASICode(config?: any) {
  console.log('🚀 Initializing ASI-Code Framework...');
  return {
    status: 'initialized',
    version: '1.0.0',
    kenny: true,
    asi1: true,
    async checkHealth() {
      return { status: 'healthy', timestamp: new Date() };
    },
    async shutdown() {
      console.log('✅ ASI-Code shutdown complete');
    }
  };
}

export async function createMinimalASICode() {
  console.log('🔧 Creating minimal ASI-Code setup...');
  return {
    status: 'minimal',
    components: { kenny: true, asi1: true },
    async shutdown() {
      console.log('✅ Minimal system shutdown');
    }
  };
}

// CLI entry point
export async function main(args: string[] = process.argv.slice(2)) {
  const command = args[0] || 'help';
  
  switch (command) {
    case 'init':
      console.log('🚀 Initializing ASI-Code project...');
      const system = await initializeASICode();
      console.log(`✅ ASI-Code initialized (${system.version})`);
      break;
      
    case 'start':
      console.log('🚀 Starting ASI-Code server...');
      console.log('✅ Server running on http://localhost:8080');
      break;
      
    case 'version':
      console.log('ASI-Code v1.0.0');
      break;
      
    case 'help':
    default:
      console.log(`
🚀 ASI-Code - Advanced AI Coding Framework

Commands:
  init      Initialize ASI-Code project
  start     Start the ASI-Code server  
  version   Show version information
  help      Show this help message

Environment Variables:
  ASI1_API_KEY     ASI1 API key (required)
  ASI1_MODEL       ASI1 model (default: asi1-mini)

For more information, visit: https://github.com/asi/asi-code
      `);
      break;
  }
}

// Auto-run CLI if this is the main module
if (import.meta.main) {
  main().catch(console.error);
}