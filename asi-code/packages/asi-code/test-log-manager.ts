// Test log-manager import specifically
console.log('Testing log-manager import...');

try {
  const { LogManagerConfig, LogManager } = await import('./src/logging/log-manager.js');
  console.log('✓ log-manager imported successfully');
  console.log('LogManagerConfig type:', typeof LogManagerConfig);
  console.log('LogManager type:', typeof LogManager);
} catch (error) {
  console.error('log-manager import failed:', error);
}