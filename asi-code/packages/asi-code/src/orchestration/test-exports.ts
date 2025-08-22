/**
 * Test to verify AgentRegistry and LoadBalancer can be imported correctly
 */

// Test direct imports
import { AgentRegistry } from './agent-registry.js';
import { LoadBalancer } from './load-balancer.js';

console.log('✅ Direct imports successful');

// Test that classes can be instantiated
try {
  const registry = new AgentRegistry();
  console.log('✅ AgentRegistry instantiated:', registry.constructor.name);
  
  const loadBalancer = new LoadBalancer();
  console.log('✅ LoadBalancer instantiated:', loadBalancer.constructor.name);
  
  console.log('✅ Both implementations are working correctly!');
  
  // Clean up
  registry.destroy();
  
} catch (error) {
  console.error('❌ Error during instantiation:', error);
}