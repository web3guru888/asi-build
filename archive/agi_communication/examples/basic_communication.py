#!/usr/bin/env python3
"""
Basic Communication Example
===========================

Demonstrates basic AGI-to-AGI communication using the protocol suite.
Shows message exchange, session management, and basic protocol features.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agi_communication import (
    AGICommunicationProtocol, AGIIdentity, CommunicationMessage, MessageType
)


class BasicCommunicationDemo:
    """Demonstrates basic AGI-to-AGI communication."""
    
    def __init__(self):
        self.agi1_protocol = None
        self.agi2_protocol = None
    
    async def setup_agis(self):
        """Set up two AGI instances for communication."""
        # Create first AGI
        agi1_identity = AGIIdentity(
            id="demo_agi_001",
            name="Reasoning AGI",
            architecture="hybrid_neuro_symbolic",
            version="1.0.0",
            capabilities=["reasoning", "planning", "learning"]
        )
        
        # Create second AGI
        agi2_identity = AGIIdentity(
            id="demo_agi_002", 
            name="Knowledge AGI",
            architecture="symbolic_ai",
            version="1.0.0",
            capabilities=["knowledge_management", "inference", "explanation"]
        )
        
        # Initialize protocols
        self.agi1_protocol = AGICommunicationProtocol(agi1_identity)
        self.agi2_protocol = AGICommunicationProtocol(agi2_identity)
        
        # Cross-register AGIs (in real scenario, this would be done through discovery)
        self.agi1_protocol.known_agis[agi2_identity.id] = agi2_identity
        self.agi2_protocol.known_agis[agi1_identity.id] = agi1_identity
        
        # Start protocols
        await self.agi1_protocol.start()
        await self.agi2_protocol.start()
        
        print("✓ Two AGI instances initialized and started")
    
    async def demonstrate_handshake(self):
        """Demonstrate AGI handshake and session establishment."""
        print("\n--- Handshake Demonstration ---")
        
        # AGI1 initiates communication with AGI2
        session_id = await self.agi1_protocol.initiate_communication("demo_agi_002")
        print(f"✓ Communication session initiated: {session_id}")
        
        # Wait a moment for protocol negotiation
        await asyncio.sleep(1)
        
        # Check session status
        status = self.agi1_protocol.get_session_status(session_id)
        print(f"✓ Session status: {status.value if status else 'Unknown'}")
        
        return session_id
    
    async def demonstrate_basic_messaging(self, session_id: str):
        """Demonstrate basic message exchange."""
        print("\n--- Basic Messaging ---")
        
        # AGI1 sends a knowledge sharing message
        knowledge_message = CommunicationMessage(
            id="msg_001",
            sender_id="demo_agi_001",
            receiver_id="demo_agi_002",
            message_type=MessageType.KNOWLEDGE_SHARE,
            timestamp=datetime.now(),
            payload={
                "knowledge_type": "factual",
                "domain": "mathematics",
                "content": "The Pythagorean theorem: a² + b² = c²",
                "confidence": 0.95
            },
            session_id=session_id
        )
        
        await self.agi1_protocol.send_message(knowledge_message)
        print("✓ AGI1 sent knowledge sharing message")
        
        # Simulate message processing time
        await asyncio.sleep(0.5)
        
        # AGI2 responds with a reasoning request
        reasoning_message = CommunicationMessage(
            id="msg_002",
            sender_id="demo_agi_002",
            receiver_id="demo_agi_001",
            message_type=MessageType.COLLABORATION_INVITE,
            timestamp=datetime.now(),
            payload={
                "collaboration_type": "reasoning",
                "problem": "Apply Pythagorean theorem to triangle with sides 3 and 4",
                "expected_output": "hypotenuse length"
            },
            session_id=session_id
        )
        
        await self.agi2_protocol.send_message(reasoning_message)
        print("✓ AGI2 sent collaboration invitation")
        
        await asyncio.sleep(0.5)
    
    async def demonstrate_capability_discovery(self):
        """Demonstrate capability discovery between AGIs."""
        print("\n--- Capability Discovery ---")
        
        # AGI1 discovers capabilities of AGI2
        discovery_results = await self.agi1_protocol.capability_discovery.discover_capabilities({
            'capability_type': 'knowledge_management',
            'min_proficiency': 0.7
        })
        
        print(f"✓ Discovered {len(discovery_results)} matching capabilities")
        for result in discovery_results[:2]:  # Show first 2 results
            capability = result.get('capability', {})
            print(f"  - {capability.get('name', 'Unknown')}: {capability.get('description', 'No description')}")
    
    async def demonstrate_trust_establishment(self):
        """Demonstrate trust scoring and authentication."""
        print("\n--- Trust & Authentication ---")
        
        # Check initial trust levels
        agi2_trust = self.agi1_protocol.authenticator.get_trust_level("demo_agi_002")
        print(f"✓ Initial trust level for AGI2: {agi2_trust.value}")
        
        # Simulate successful interactions to build trust
        for i in range(3):
            self.agi1_protocol.authenticator.update_trust("demo_agi_002", success=True, impact=0.1)
        
        # Check updated trust
        updated_trust = self.agi1_protocol.authenticator.get_trust_level("demo_agi_002")
        print(f"✓ Updated trust level for AGI2: {updated_trust.value}")
        
        # Get authentication statistics
        auth_stats = self.agi1_protocol.authenticator.get_authentication_statistics()
        print(f"✓ Trust records managed: {auth_stats.get('total_trust_records', 0)}")
    
    async def demonstrate_statistics(self):
        """Show communication statistics."""
        print("\n--- Communication Statistics ---")
        
        # Get communication stats from both AGIs
        stats1 = self.agi1_protocol.get_communication_stats()
        stats2 = self.agi2_protocol.get_communication_stats()
        
        print("AGI1 Statistics:")
        print(f"  - Active sessions: {stats1.get('active_sessions', 0)}")
        print(f"  - Known AGIs: {stats1.get('known_agis', 0)}")
        print(f"  - Total messages: {stats1.get('total_messages', 0)}")
        
        print("AGI2 Statistics:")
        print(f"  - Active sessions: {stats2.get('active_sessions', 0)}")
        print(f"  - Known AGIs: {stats2.get('known_agis', 0)}")
        print(f"  - Total messages: {stats2.get('total_messages', 0)}")
    
    async def cleanup(self):
        """Clean up resources."""
        print("\n--- Cleanup ---")
        
        if self.agi1_protocol:
            await self.agi1_protocol.stop()
            print("✓ AGI1 protocol stopped")
        
        if self.agi2_protocol:
            await self.agi2_protocol.stop()
            print("✓ AGI2 protocol stopped")
    
    async def run_demo(self):
        """Run the complete basic communication demo."""
        print("🤖 AGI-to-AGI Communication Protocol - Basic Demo")
        print("=" * 50)
        
        try:
            # Setup
            await self.setup_agis()
            
            # Demonstrations
            session_id = await self.demonstrate_handshake()
            await self.demonstrate_basic_messaging(session_id)
            await self.demonstrate_capability_discovery()
            await self.demonstrate_trust_establishment()
            await self.demonstrate_statistics()
            
            print("\n🎉 Demo completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            raise
            
        finally:
            await self.cleanup()


async def main():
    """Main entry point for the basic communication demo."""
    demo = BasicCommunicationDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())