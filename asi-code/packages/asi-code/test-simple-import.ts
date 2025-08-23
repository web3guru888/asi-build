// Simple test to check imports
console.log('Testing imports...');

try {
  console.log('1. Testing formatters...');
  const { FormatterOptions, BaseFormatter } = await import('./src/logging/formatters.js');
  console.log('✓ Formatters imported successfully');
  
  console.log('2. Testing logging index...');
  const logging = await import('./src/logging/index.js');
  console.log('✓ Logging index imported successfully', Object.keys(logging));
  
  console.log('3. Testing kenny...');
  const kenny = await import('./src/kenny/index.js');
  console.log('✓ Kenny imported successfully');
  
  console.log('4. Testing main index...');
  const main = await import('./src/index.js');
  console.log('✓ Main index imported successfully');
  
} catch (error) {
  console.error('Import failed:', error);
}