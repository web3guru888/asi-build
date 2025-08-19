#!/usr/bin/env python3
"""
SingularityNET Integration Example
==================================

Demonstrates integration with the SingularityNET ecosystem,
including service registration, discovery, and marketplace interaction.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agi_communication import (
    AGICommunicationProtocol, AGIIdentity, ServiceMetadata, ServiceCategory
)


class SingularityNetDemo:
    """Demonstrates SingularityNET ecosystem integration."""
    
    def __init__(self):
        self.service_provider_agi = None
        self.service_consumer_agi = None
    
    async def setup_agis(self):
        """Set up service provider and consumer AGIs."""
        # Service provider AGI
        provider_identity = AGIIdentity(
            id="service_provider_001",
            name="Advanced Reasoning Service Provider",
            architecture="hybrid_neuro_symbolic", 
            version="1.0.0",
            capabilities=["reasoning", "inference", "problem_solving", "explanation"]
        )
        
        # Service consumer AGI
        consumer_identity = AGIIdentity(
            id="service_consumer_001",
            name="Research Assistant AGI",
            architecture="neural_network",
            version="1.0.0",
            capabilities=["research", "analysis", "synthesis"]
        )
        
        # Initialize protocols with SingularityNET integration
        self.service_provider_agi = AGICommunicationProtocol(provider_identity)
        self.service_consumer_agi = AGICommunicationProtocol(consumer_identity)
        
        # Cross-register AGIs
        self.service_provider_agi.known_agis[consumer_identity.id] = consumer_identity
        self.service_consumer_agi.known_agis[provider_identity.id] = provider_identity
        
        # Start protocols
        await self.service_provider_agi.start()
        await self.service_consumer_agi.start()
        
        print("✓ Service provider and consumer AGIs initialized")
        print(f"  - Provider: {provider_identity.name}")
        print(f"  - Consumer: {consumer_identity.name}")
    
    async def demonstrate_service_registration(self):
        """Demonstrate registering AGI services on SingularityNET."""
        print("\n--- Service Registration on SingularityNET ---")
        
        # Create service metadata for different AGI capabilities
        reasoning_service = ServiceMetadata(
            service_id="advanced_reasoning",
            organization_id="kenny_agi_org",
            service_name="Advanced AGI Reasoning Service",
            service_description="Provides sophisticated reasoning, inference, and problem-solving capabilities using hybrid neuro-symbolic architecture",
            service_category=ServiceCategory.AI_TRAINING,
            version="1.2.0",
            price_per_call=150,  # 150 cogs per call
            endpoints=[{
                "endpoint": "https://services.kenny-agi.io/reasoning",
                "group_name": "reasoning_group"
            }]
        )
        
        explanation_service = ServiceMetadata(
            service_id="explanation_generation", 
            organization_id="kenny_agi_org",
            service_name="AI Explanation Generator",
            service_description="Generates human-readable explanations for AI decisions and reasoning processes",
            service_category=ServiceCategory.NATURAL_LANGUAGE,
            version="1.1.0",
            price_per_call=100,
            endpoints=[{
                "endpoint": "https://services.kenny-agi.io/explanation", 
                "group_name": "explanation_group"
            }]
        )
        
        problem_solving_service = ServiceMetadata(
            service_id="collaborative_problem_solving",
            organization_id="kenny_agi_org",
            service_name="Collaborative Problem Solving",
            service_description="Multi-AGI collaborative problem solving for complex interdisciplinary challenges", 
            service_category=ServiceCategory.OPTIMIZATION,
            version="1.0.0",
            price_per_call=300,
            endpoints=[{
                "endpoint": "https://services.kenny-agi.io/collaboration",
                "group_name": "collaboration_group" 
            }]
        )
        
        # Register services on SingularityNET
        snet = self.service_provider_agi.singularitynet_integration
        
        reasoning_key = await snet.register_service_on_network(reasoning_service)
        print(f"✓ Registered reasoning service: {reasoning_key}")
        
        explanation_key = await snet.register_service_on_network(explanation_service)
        print(f"✓ Registered explanation service: {explanation_key}")
        
        problem_solving_key = await snet.register_service_on_network(problem_solving_service)
        print(f"✓ Registered problem-solving service: {problem_solving_key}")
        
        # Show registered services
        print(f"\nTotal services registered: {len(snet.registered_services)}")
        for service_id, metadata in snet.registered_services.items():
            print(f"  - {service_id}: {metadata.service_name} ({metadata.price_per_call} cogs)")
        
        return [reasoning_service, explanation_service, problem_solving_service]
    
    async def demonstrate_service_discovery(self):
        """Demonstrate discovering services on SingularityNET marketplace."""
        print("\n--- Service Discovery ---")
        
        snet = self.service_consumer_agi.singularitynet_integration
        
        # Discover AI training services
        ai_training_services = await snet.discover_services(
            category=ServiceCategory.AI_TRAINING,
            search_terms=["reasoning", "inference"]
        )
        
        print(f"✓ Found {len(ai_training_services)} AI training services:")
        for service in ai_training_services:
            print(f"  - {service['service_name']}: {service['description'][:60]}...")
            print(f"    Price: {service['price_per_call']} cogs | Org: {service['organization_id']}")
        
        # Discover optimization services
        optimization_services = await snet.discover_services(
            category=ServiceCategory.OPTIMIZATION
        )
        
        print(f"\n✓ Found {len(optimization_services)} optimization services:")
        for service in optimization_services:
            print(f"  - {service['service_name']}: {service['price_per_call']} cogs")
        
        # General search for problem solving
        problem_solving_services = await snet.discover_services(
            search_terms=["problem", "solving", "collaboration"]
        )
        
        print(f"\n✓ Found {len(problem_solving_services)} problem-solving services:")
        for service in problem_solving_services:
            print(f"  - {service['service_name']} ({service['organization_id']})")
        
        return ai_training_services + optimization_services + problem_solving_services
    
    async def demonstrate_payment_channels(self):
        """Demonstrate creating and managing payment channels."""
        print("\n--- Payment Channel Management ---")
        
        snet = self.service_consumer_agi.singularitynet_integration
        
        # Create payment channel for service calls
        recipient_address = "0x" + "1" * 40  # Mock Ethereum address
        channel_value = 10000  # 10,000 cogs
        
        channel_info = await snet.create_payment_channel(
            recipient_address=recipient_address,
            value_cogs=channel_value,
            expiration_blocks=1000
        )
        
        print(f"✓ Created payment channel:")
        print(f"  - Channel ID: {channel_info.channel_id}")
        print(f"  - Value: {channel_info.value} cogs")
        print(f"  - Expiration: Block {channel_info.expiration}")
        print(f"  - Status: {channel_info.state.value}")
        
        # Show active channels
        active_channels = len(snet.active_channels)
        print(f"\n✓ Total active payment channels: {active_channels}")
        
        return channel_info
    
    async def demonstrate_service_calls(self, services, payment_channel):
        """Demonstrate calling services through SingularityNET."""
        print("\n--- Service Execution ---")
        
        snet = self.service_consumer_agi.singularitynet_integration
        
        # Find reasoning service
        reasoning_services = [s for s in services if 'reasoning' in s.get('service_id', '').lower()]
        
        if reasoning_services:
            reasoning_service = reasoning_services[0]
            
            # Call reasoning service
            service_call = await snet.call_service(
                service_id=reasoning_service['service_id'],
                method_name="infer",
                input_data={
                    "premises": [
                        "All humans are mortal",
                        "Socrates is human"
                    ],
                    "question": "Is Socrates mortal?"
                },
                payment_channel_id=payment_channel.channel_id,
                payment_amount=150
            )
            
            print(f"✓ Called reasoning service:")
            print(f"  - Call ID: {service_call.call_id}")
            print(f"  - Status: {service_call.status}")
            print(f"  - Payment: {service_call.payment_amount} cogs")
            
            if service_call.result:
                result = service_call.result
                print(f"  - Result: {result.get('conclusion', 'No conclusion')}")
                print(f"  - Confidence: {result.get('confidence', 0):.2f}")
                if 'reasoning_chain' in result:
                    print(f"  - Steps: {len(result['reasoning_chain'])}")
        
        # Call explanation service if available
        explanation_services = [s for s in services if 'explanation' in s.get('service_id', '').lower()]
        
        if explanation_services:
            explanation_service = explanation_services[0]
            
            service_call = await snet.call_service(
                service_id=explanation_service['service_id'],
                method_name="explain",
                input_data={
                    "decision": "Socrates is mortal",
                    "context": "logical_reasoning",
                    "audience": "general"
                },
                payment_channel_id=payment_channel.channel_id,
                payment_amount=100
            )
            
            print(f"\n✓ Called explanation service:")
            print(f"  - Status: {service_call.status}")
            if service_call.result:
                print(f"  - Explanation generated: {bool(service_call.result)}")
        
        # Show service call statistics
        completed_calls = len([c for c in snet.service_calls.values() if c.status == 'completed'])
        total_calls = len(snet.service_calls)
        
        print(f"\n✓ Service call statistics:")
        print(f"  - Total calls made: {total_calls}")
        print(f"  - Completed calls: {completed_calls}")
        print(f"  - Success rate: {(completed_calls/total_calls*100):.1f}%" if total_calls > 0 else "  - Success rate: N/A")
    
    async def demonstrate_service_provision(self):
        """Demonstrate providing services to other AGIs."""
        print("\n--- Service Provision ---")
        
        snet = self.service_provider_agi.singularitynet_integration
        
        # Simulate incoming service call
        service_call_data = {
            'service_id': 'advanced_reasoning',
            'method_name': 'solve_problem',
            'input_data': {
                'problem_type': 'optimization',
                'parameters': {'variables': 3, 'constraints': 5},
                'objective': 'minimize_cost'
            },
            'payment': {
                'channel_id': 'mock_channel_123',
                'amount': 150,
                'signature': '0x' + '0' * 128
            }
        }
        
        # Provide service
        result = await snet.provide_service(service_call_data)
        
        print(f"✓ Service provided:")
        print(f"  - Success: {result['success']}")
        if result['success']:
            print(f"  - Call ID: {result.get('call_id', 'N/A')}")
            print(f"  - Result type: {type(result.get('result', {}).__class__.__name__)}")
        else:
            print(f"  - Error: {result.get('error', 'Unknown error')}")
        
        # Show provision statistics
        stats = snet.get_integration_statistics()
        print(f"\n✓ Service provision statistics:")
        print(f"  - Registered services: {stats['registered_services']}")
        print(f"  - Integration events: {stats['total_integration_events']}")
    
    async def demonstrate_marketplace_metadata(self):
        """Demonstrate retrieving and managing service metadata."""
        print("\n--- Marketplace Metadata ---")
        
        snet = self.service_provider_agi.singularitynet_integration
        
        # Get metadata for registered services
        for service_id in list(snet.registered_services.keys())[:2]:
            metadata = await snet.get_service_metadata("kenny_agi_org", service_id)
            
            if metadata:
                print(f"\n✓ Metadata for {service_id}:")
                print(f"  - Display name: {metadata.get('display_name', 'N/A')}")
                print(f"  - Version: {metadata.get('version', 'N/A')}")
                print(f"  - Encoding: {metadata.get('encoding', 'N/A')}")
                print(f"  - Price: {metadata.get('pricing', {}).get('price_in_cogs', 'N/A')} cogs")
                print(f"  - Groups: {len(metadata.get('groups', []))}")
                print(f"  - Endpoints: {len(metadata.get('endpoints', []))}")
        
        # Update service metadata
        if snet.registered_services:
            first_service_id = list(snet.registered_services.keys())[0]
            first_service = snet.registered_services[first_service_id]
            
            # Create updated metadata
            updated_service = ServiceMetadata(
                service_id=first_service_id,
                organization_id=first_service.organization_id,
                service_name=first_service.service_name + " (Updated)",
                service_description=first_service.service_description + " - Now with enhanced capabilities!",
                service_category=first_service.service_category,
                version="1.3.0",  # Bump version
                price_per_call=first_service.price_per_call - 25,  # Reduce price
                endpoints=first_service.endpoints
            )
            
            success = await snet.update_service_metadata(first_service_id, updated_service)
            if success:
                print(f"\n✓ Updated service metadata for {first_service_id}")
                print(f"  - New version: {updated_service.version}")
                print(f"  - New price: {updated_service.price_per_call} cogs")
    
    async def show_integration_statistics(self):
        """Display comprehensive SingularityNET integration statistics."""
        print("\n--- SingularityNET Integration Statistics ---")
        
        # Provider statistics
        provider_stats = self.service_provider_agi.singularitynet_integration.get_integration_statistics()
        print(f"\nService Provider AGI:")
        print(f"  - Registered services: {provider_stats['registered_services']}")
        print(f"  - Active payment channels: {provider_stats['active_payment_channels']}")
        print(f"  - Completed service calls: {provider_stats['completed_service_calls']}")
        print(f"  - Organization ID: {provider_stats['organization_id']}")
        print(f"  - Service categories: {', '.join(provider_stats['service_categories'])}")
        
        # Consumer statistics
        consumer_stats = self.service_consumer_agi.singularitynet_integration.get_integration_statistics()
        print(f"\nService Consumer AGI:")
        print(f"  - Active payment channels: {consumer_stats['active_payment_channels']}")
        print(f"  - Completed service calls: {consumer_stats['completed_service_calls']}")
        print(f"  - Failed service calls: {consumer_stats['failed_service_calls']}")
        print(f"  - Total integration events: {consumer_stats['total_integration_events']}")
        
        # Marketplace insights
        print(f"\nMarketplace Integration:")
        print(f"  - Total AGI services in ecosystem: 3+")
        print(f"  - Cross-AGI service calls: {consumer_stats['completed_service_calls']}")
        print(f"  - Economic activity: Multiple payment channels active")
        print(f"  - Decentralized service discovery: Enabled")
    
    async def cleanup(self):
        """Clean up resources."""
        print("\n--- Cleanup ---")
        
        if self.service_provider_agi:
            await self.service_provider_agi.stop()
            print("✓ Service provider AGI stopped")
        
        if self.service_consumer_agi:
            await self.service_consumer_agi.stop()
            print("✓ Service consumer AGI stopped")
    
    async def run_demo(self):
        """Run the complete SingularityNET integration demo."""
        print("🌐 SingularityNET Integration Demo")
        print("=" * 50)
        
        try:
            # Setup
            await self.setup_agis()
            
            # Service registration and discovery
            services = await self.demonstrate_service_registration()
            discovered_services = await self.demonstrate_service_discovery()
            
            # Payment and service execution
            payment_channel = await self.demonstrate_payment_channels()
            await self.demonstrate_service_calls(services, payment_channel)
            
            # Service provision and metadata
            await self.demonstrate_service_provision()
            await self.demonstrate_marketplace_metadata()
            
            # Results
            await self.show_integration_statistics()
            
            print("\n🎉 SingularityNET integration demo completed successfully!")
            print("AGI services are now fully integrated with the decentralized AI marketplace!")
            
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            raise
            
        finally:
            await self.cleanup()


async def main():
    """Main entry point for the SingularityNET integration demo."""
    demo = SingularityNetDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())