#!/usr/bin/env python3
"""
Kenny AGI Python SDK Usage Example
"""

import asyncio
from kenny_agi_sdk import ApiClient, Configuration, SystemApi, AGICoreApi, ConsciousnessApi

async def main():
    # Configure the client
    configuration = Configuration(
        host="http://localhost:8000",
        access_token="your_api_key_here"
    )
    
    async with ApiClient(configuration) as api_client:
        # Create API instances
        system_api = SystemApi(api_client)
        agi_api = AGICoreApi(api_client)
        consciousness_api = ConsciousnessApi(api_client)
        
        try:
            # Check system health
            health = await system_api.health_check()
            print(f"System status: {health.status}")
            
            # Get AGI status
            agi_status = await agi_api.get_agi_status()
            print(f"AGI status: {agi_status.data}")
            
            # Get consciousness level
            consciousness = await consciousness_api.get_consciousness_level()
            print(f"Consciousness: {consciousness.data}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
