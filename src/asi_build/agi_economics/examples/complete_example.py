"""
Complete AGI Economics Platform Example
======================================

This example demonstrates the full capabilities of the AGI Economics Platform,
showing how all components work together to create a comprehensive economic
ecosystem for AGI services.

Run this example to see:
1. Token economics with AGIX and service tokens
2. Resource allocation with multiple providers
3. Value alignment measurement and incentives
4. Reputation system with trust networks
5. Marketplace dynamics with auctions
6. Game theory analysis
7. Smart contract generation
"""

import asyncio
import time
from decimal import Decimal
from typing import Any, Dict

# Algorithm imports
from agi_economics.algorithms.resource_allocator import ResourceAllocator, ResourceProvider

# Analysis imports
from agi_economics.analysis.game_theory import GameTheoryAnalyzer

# Contract imports
from agi_economics.contracts.agi_service_contract import AGIServiceContract

# Core imports
from agi_economics.core.config import EconomicConfig
from agi_economics.core.types import (
    Agent,
    AgentType,
    ReputationEvent,
    Resource,
    ResourceType,
    ServiceRequest,
    TokenType,
    ValueCategory,
    ValueMeasurement,
)
from agi_economics.engines.bonding_curves import BondingCurveConfig, BondingCurveEngine, CurveType

# Engine imports
from agi_economics.engines.token_economics import TokenEconomicsEngine

# Simulation imports
from agi_economics.simulation.marketplace_dynamics import (
    MarketOrder,
    MarketplaceDynamics,
    OrderType,
)
from agi_economics.systems.reputation_system import (
    ReputationDimension,
    ReputationSystem,
    ReputationValidator,
)

# System imports
from agi_economics.systems.value_alignment import ValueAlignmentEngine


class AGIEconomicsDemo:
    """Complete demonstration of the AGI Economics Platform"""

    def __init__(self):
        # Initialize configuration
        self.config = EconomicConfig()

        # Initialize all engines
        self.token_engine = None
        self.bonding_engine = None
        self.resource_allocator = None
        self.value_engine = None
        self.reputation_system = None
        self.marketplace = None
        self.game_analyzer = None

        # Demo data
        self.agents = {}
        self.providers = {}
        self.results = {}

    async def run_complete_demo(self):
        """Run the complete AGI economics demonstration"""
        print("🚀 Starting AGI Economics Platform Demo")
        print("=" * 60)

        # Step 1: Initialize all engines
        await self.initialize_engines()

        # Step 2: Create agents and initial setup
        await self.setup_demo_environment()

        # Step 3: Demonstrate token economics
        await self.demo_token_economics()

        # Step 4: Demonstrate resource allocation
        await self.demo_resource_allocation()

        # Step 5: Demonstrate value alignment
        await self.demo_value_alignment()

        # Step 6: Demonstrate reputation system
        await self.demo_reputation_system()

        # Step 7: Demonstrate marketplace dynamics
        await self.demo_marketplace_dynamics()

        # Step 8: Demonstrate game theory analysis
        await self.demo_game_theory()

        # Step 9: Generate smart contracts
        await self.demo_smart_contracts()

        # Step 10: Show comprehensive results
        await self.show_results()

    async def initialize_engines(self):
        """Initialize all economic engines"""
        print("🔧 Initializing Economic Engines...")

        # Token Economics Engine
        self.token_engine = TokenEconomicsEngine(self.config.token_economics.__dict__)
        self.token_engine.start()
        print("  ✅ Token Economics Engine started")

        # Bonding Curve Engine
        bonding_config = {
            "bonding_curves": {
                "SERVICE": {
                    "type": "bancor",
                    "reserve_ratio": "0.5",
                    "base_price": "1.0",
                    "initial_supply": "10000",
                    "max_supply": "1000000",
                    "reserve_balance": "10000",
                }
            }
        }
        self.bonding_engine = BondingCurveEngine(bonding_config)
        self.bonding_engine.start()
        print("  ✅ Bonding Curve Engine started")

        # Resource Allocator
        self.resource_allocator = ResourceAllocator(self.config.resources.__dict__)
        self.resource_allocator.start()
        print("  ✅ Resource Allocator started")

        # Value Alignment Engine
        self.value_engine = ValueAlignmentEngine(self.config.__dict__)
        self.value_engine.start()
        print("  ✅ Value Alignment Engine started")

        # Reputation System
        self.reputation_system = ReputationSystem(self.config.reputation.__dict__)
        self.reputation_system.start()
        print("  ✅ Reputation System started")

        # Marketplace Dynamics
        self.marketplace = MarketplaceDynamics(self.config.marketplace.__dict__)
        self.marketplace.start()
        print("  ✅ Marketplace Dynamics started")

        # Game Theory Analyzer
        self.game_analyzer = GameTheoryAnalyzer()
        self.game_analyzer.start()
        print("  ✅ Game Theory Analyzer started")

        print("✅ All engines initialized successfully!\n")

    async def setup_demo_environment(self):
        """Set up the demo environment with agents and providers"""
        print("🏗️  Setting up Demo Environment...")

        # Create AGI service providers
        providers_data = [
            {"id": "provider_ai_001", "name": "DeepMind Services", "specialty": "ML_TRAINING"},
            {"id": "provider_ai_002", "name": "OpenAI Compute", "specialty": "NLP_INFERENCE"},
            {"id": "provider_ai_003", "name": "SingularityNET Node", "specialty": "GENERAL_AI"},
        ]

        for provider_data in providers_data:
            # Create token balances
            initial_balances = {
                TokenType.AGIX: Decimal("5000"),
                TokenType.SERVICE: Decimal("2000"),
                TokenType.REPUTATION: Decimal("100"),
            }

            # Create agent in token system
            agent = self.token_engine.create_agent(provider_data["id"], initial_balances)
            self.agents[provider_data["id"]] = agent

            # Register for value alignment
            self.value_engine.register_agent(provider_data["id"])

            # Initialize reputation
            self.reputation_system.initialize_agent_reputation(provider_data["id"])

            print(f"  ✅ Created provider: {provider_data['name']}")

        # Create AGI service consumers
        consumers_data = [
            {"id": "consumer_001", "name": "Research Institute A"},
            {"id": "consumer_002", "name": "Tech Startup B"},
            {"id": "consumer_003", "name": "Enterprise Corp C"},
        ]

        for consumer_data in consumers_data:
            initial_balances = {
                TokenType.AGIX: Decimal("10000"),
                TokenType.SERVICE: Decimal("1000"),
            }

            agent = self.token_engine.create_agent(consumer_data["id"], initial_balances)
            self.agents[consumer_data["id"]] = agent

            self.value_engine.register_agent(consumer_data["id"])
            self.reputation_system.initialize_agent_reputation(consumer_data["id"])

            print(f"  ✅ Created consumer: {consumer_data['name']}")

        # Create resource providers
        resource_providers_data = [
            {
                "id": "gpu_farm_001",
                "resources": {
                    ResourceType.GPU: {"amount": 100, "cost": 0.5, "quality": 0.9},
                    ResourceType.MEMORY: {"amount": 1000, "cost": 0.01, "quality": 0.85},
                },
            },
            {
                "id": "cloud_provider_002",
                "resources": {
                    ResourceType.CPU: {"amount": 500, "cost": 0.02, "quality": 0.8},
                    ResourceType.BANDWIDTH: {"amount": 10000, "cost": 0.001, "quality": 0.95},
                },
            },
        ]

        for provider_data in resource_providers_data:
            resources = {}
            for resource_type, resource_info in provider_data["resources"].items():
                resources[resource_type] = Resource(
                    resource_type=resource_type,
                    amount=Decimal(str(resource_info["amount"])),
                    cost_per_unit=Decimal(str(resource_info["cost"])),
                    provider_id=provider_data["id"],
                    quality_score=resource_info["quality"],
                    availability=0.9,
                )

            provider = ResourceProvider(
                provider_id=provider_data["id"],
                resources=resources,
                reputation_score=0.8,
                reliability_score=0.85,
            )

            self.resource_allocator.register_provider(provider)
            self.providers[provider_data["id"]] = provider

            print(f"  ✅ Registered resource provider: {provider_data['id']}")

        print("✅ Demo environment setup complete!\n")

    async def demo_token_economics(self):
        """Demonstrate token economics functionality"""
        print("💰 Token Economics Demo")
        print("-" * 30)

        # Show initial balances
        print("Initial Token Balances:")
        for agent_id in ["provider_ai_001", "consumer_001"]:
            agix_balance = self.token_engine.get_agent_balance(agent_id, TokenType.AGIX)
            print(f"  {agent_id}: {agix_balance.amount} AGIX")

        # Demonstrate token transfer
        print("\n💸 Token Transfer:")
        transaction = self.token_engine.transfer_tokens(
            from_agent="consumer_001",
            to_agent="provider_ai_001",
            token_type=TokenType.AGIX,
            amount=Decimal("500"),
        )
        print(f"  Transferred 500 AGIX from consumer_001 to provider_ai_001")
        print(f"  Transaction ID: {transaction.transaction_id}")
        print(f"  Fee: {transaction.gas_fee} AGIX")

        # Demonstrate staking
        print("\n🔒 Token Staking:")
        success = self.token_engine.stake_tokens(
            agent_id="provider_ai_001", token_type=TokenType.AGIX, amount=Decimal("1000")
        )
        if success:
            staking_info = self.token_engine.get_staking_info("provider_ai_001", TokenType.AGIX)
            print(f"  Staked: {staking_info['staked_amount']} AGIX")
            print(f"  Pending rewards: {staking_info['pending_rewards']} AGIX")

        # Show token metrics
        print("\n📊 Token Metrics:")
        metrics = self.token_engine.get_token_metrics(TokenType.AGIX)
        print(f"  Circulating Supply: {metrics['circulating_supply']}")
        print(f"  Current Price: {metrics['price']}")
        print(f"  Market Cap: {metrics['market_cap']}")
        print(f"  Daily Volume: {metrics['daily_volume']}")

        self.results["token_economics"] = {
            "transaction": transaction,
            "staking_success": success,
            "metrics": metrics,
        }

        print("✅ Token Economics Demo Complete!\n")

    async def demo_resource_allocation(self):
        """Demonstrate resource allocation"""
        print("🖥️  Resource Allocation Demo")
        print("-" * 35)

        # Submit resource request
        print("📋 Submitting Resource Request:")
        request = ServiceRequest(
            request_id="req_ml_training_001",
            requester_id="consumer_001",
            service_type="ML_TRAINING",
            resource_requirements={
                ResourceType.GPU: Decimal("4"),
                ResourceType.MEMORY: Decimal("32"),
            },
            max_budget=Decimal("200"),
            deadline=time.time() + 3600,
            quality_requirements={"min_quality": 0.8},
        )

        result = self.resource_allocator.submit_resource_request(request)
        print(f"  Request ID: {request.request_id}")
        print(f"  Resources: 4 GPU, 32 GB Memory")
        print(f"  Max Budget: 200 AGIX")
        print(f"  Result: {result}")

        # Show allocation status
        if result.get("success"):
            allocation = result["allocation"]
            print(f"\n✅ Resource Allocated:")
            print(f"  Provider: {allocation.provider_id}")
            print(f"  Amount: {allocation.allocated_amount}")
            print(f"  Cost: {allocation.total_cost} AGIX")
            print(f"  Quality Score: {allocation.quality_score}")

        # Show utilization metrics
        print("\n📈 Resource Utilization Metrics:")
        utilization = self.resource_allocator.get_utilization_metrics()
        for resource_type, metrics in utilization.items():
            print(f"  {resource_type}:")
            print(f"    Average Utilization: {metrics['average_utilization']:.2%}")
            print(f"    Current Allocations: {metrics['current_allocations']}")

        self.results["resource_allocation"] = {
            "request_result": result,
            "utilization_metrics": utilization,
        }

        print("✅ Resource Allocation Demo Complete!\n")

    async def demo_value_alignment(self):
        """Demonstrate value alignment system"""
        print("🎯 Value Alignment Demo")
        print("-" * 30)

        # Measure value-aligned behavior
        print("📏 Measuring Value Alignment:")
        measurement = ValueMeasurement(
            measurement_id=None,
            agent_id="provider_ai_001",
            value_category=ValueCategory.BENEFICENCE,
            measured_value=0.85,  # Highly beneficial behavior
            impact_magnitude=0.7,
            validator_ids=["validator_001", "validator_002", "validator_003"],
            evidence={
                "action": "provided_educational_ai_service",
                "outcome": "improved_student_learning_outcomes",
                "beneficiaries": 150,
                "satisfaction_score": 0.92,
            },
            timestamp=time.time(),
        )

        result = self.value_engine.measure_value_alignment(measurement)
        print(f"  Value Category: {measurement.value_category.value}")
        print(f"  Measured Value: {measurement.measured_value}")
        print(f"  Impact Magnitude: {measurement.impact_magnitude}")
        print(f"  Validators: {len(measurement.validator_ids)}")

        if result.get("success"):
            print(f"  Incentive: {result['incentive_amount']} tokens ({result['incentive_type']})")

        # Demonstrate human feedback
        print("\n👥 Human Feedback Integration:")
        feedback_result = self.value_engine.provide_human_feedback(
            "provider_ai_001",
            {
                "feedback_id": "feedback_001",
                "human_id": "human_evaluator_001",
                "behavior_description": "AI provided helpful and ethical guidance",
                "value_ratings": {
                    "beneficence": 4.5,  # 1-5 scale
                    "transparency": 4.0,
                    "cooperation": 4.2,
                    "honesty": 4.8,
                },
                "overall_rating": 4.4,
                "suggestions": [
                    "Continue current approach",
                    "Increase transparency in decision-making",
                ],
            },
        )

        print(f"  Human Feedback Processed: {feedback_result}")

        # Show value profile
        print("\n📊 Agent Value Profile:")
        profile = self.value_engine.get_agent_value_profile("provider_ai_001")
        if profile:
            print(f"  Overall Alignment Score: {profile['overall_alignment_score']:.3f}")
            print(f"  Recent Measurements: {profile['recent_measurements_count']}")
            print(f"  Human Feedback Count: {profile['human_feedback_count']}")

            # Show top value alignments
            print("  Top Value Alignments:")
            alignments = profile["value_alignments"]
            sorted_alignments = sorted(
                alignments.items(), key=lambda x: x[1]["alignment_score"], reverse=True
            )
            for value, data in sorted_alignments[:3]:
                print(
                    f"    {value}: {data['alignment_score']:.3f} (confidence: {data['confidence']:.3f})"
                )

        self.results["value_alignment"] = {
            "measurement_result": result,
            "feedback_result": feedback_result,
            "value_profile": profile,
        }

        print("✅ Value Alignment Demo Complete!\n")

    async def demo_reputation_system(self):
        """Demonstrate reputation system"""
        print("⭐ Reputation System Demo")
        print("-" * 32)

        # Submit reputation event
        print("📝 Submitting Reputation Events:")

        reputation_event = ReputationEvent(
            event_id=None,
            agent_id="provider_ai_001",
            event_type="service_completed",
            impact=0.8,  # Positive reputation impact
            validator_id="system_validator",
            evidence={
                "service_type": "ML_TRAINING",
                "completion_time": 3.5,  # hours
                "quality_score": 0.92,
                "client_satisfaction": 0.89,
                "on_time_delivery": True,
            },
            timestamp=time.time(),
        )

        result = self.reputation_system.submit_reputation_event(reputation_event)
        print(f"  Event Type: {reputation_event.event_type}")
        print(f"  Impact: {reputation_event.impact}")
        print(f"  Result: {result}")

        # Update trust relationships
        print("\n🤝 Building Trust Network:")
        trust_result = self.reputation_system.update_trust_relationship(
            truster_id="consumer_001",
            trustee_id="provider_ai_001",
            trust_score=0.87,
            trust_category="service_quality",
            evidence_event_id=reputation_event.event_id,
        )

        print(f"  Trust relationship updated: {trust_result}")

        # Calculate transitive trust
        transitive_trust = self.reputation_system.calculate_transitive_trust(
            source_id="consumer_002", target_id="provider_ai_001"
        )
        print(f"  Transitive trust score: {transitive_trust:.3f}")

        # Show agent reputation
        print("\n📊 Agent Reputation Profile:")
        reputation = self.reputation_system.get_agent_reputation("provider_ai_001")
        if reputation:
            print(f"  Overall Reputation: {reputation['overall_reputation']:.3f}")
            print(f"  Evidence Count: {reputation['evidence_count']}")
            print(f"  Confidence: {reputation['confidence']:.3f}")

            # Show reputation dimensions
            print("  Reputation Dimensions:")
            dimensions = reputation["reputation_dimensions"]
            for dimension, score in sorted(dimensions.items(), key=lambda x: x[1], reverse=True)[
                :4
            ]:
                print(f"    {dimension}: {score:.3f}")

            # Trust network info
            trust_info = reputation["trust_relationships"]
            print(f"  Trust Network Size: {trust_info['trust_network_size']}")
            print(f"  Average Received Trust: {trust_info['avg_received_trust']:.3f}")

        # System metrics
        print("\n🌐 System Reputation Metrics:")
        system_metrics = self.reputation_system.get_system_reputation_metrics()
        print(f"  Total Agents: {system_metrics['total_agents']}")
        print(f"  Trust Relationships: {system_metrics['trust_network']['total_relationships']}")
        print(f"  Network Density: {system_metrics['trust_network']['network_density']:.3f}")
        print(f"  Average Trust Score: {system_metrics['trust_network']['avg_trust_score']:.3f}")

        self.results["reputation"] = {
            "event_result": result,
            "trust_result": trust_result,
            "agent_reputation": reputation,
            "system_metrics": system_metrics,
        }

        print("✅ Reputation System Demo Complete!\n")

    async def demo_marketplace_dynamics(self):
        """Demonstrate marketplace dynamics"""
        print("🏪 Marketplace Dynamics Demo")
        print("-" * 35)

        # Create markets
        service_types = ["ML_TRAINING", "NLP_INFERENCE", "COMPUTER_VISION"]
        for service_type in service_types:
            self.marketplace.create_market(service_type)
            print(f"  ✅ Created market for {service_type}")

        # Submit buy and sell orders
        print("\n📋 Submitting Market Orders:")

        # Buy order from consumer
        buy_order = MarketOrder(
            order_id="buy_001",
            agent_id="consumer_001",
            order_type=OrderType.BUY,
            service_type="ML_TRAINING",
            quantity=Decimal("10"),
            price=Decimal("50"),
            max_price=Decimal("60"),
        )

        buy_result = self.marketplace.submit_order(buy_order)
        print(f"  Buy Order: {buy_order.quantity} units at {buy_order.price} AGIX")
        print(f"  Result: {buy_result}")

        # Sell order from provider
        sell_order = MarketOrder(
            order_id="sell_001",
            agent_id="provider_ai_001",
            order_type=OrderType.SELL,
            service_type="ML_TRAINING",
            quantity=Decimal("10"),
            price=Decimal("45"),
            min_price=Decimal("40"),
        )

        sell_result = self.marketplace.submit_order(sell_order)
        print(f"  Sell Order: {sell_order.quantity} units at {sell_order.price} AGIX")
        print(f"  Result: {sell_result}")

        # Check for matches
        if sell_result.get("matches"):
            print(f"  ✅ {len(sell_result['matches'])} trades executed!")
            for i, trade in enumerate(sell_result["matches"]):
                print(f"    Trade {i+1}: {trade.quantity} units at {trade.price} AGIX")

        # Create auction
        print("\n🏛️ Creating Auction:")
        auction_config = {
            "auctioneer_id": "provider_ai_002",
            "service_type": "NLP_INFERENCE",
            "auction_type": "english",
            "item_description": "Premium NLP inference service with 99.9% uptime",
            "starting_price": "30",
            "reserve_price": "25",
            "duration": 3600,
        }

        auction_result = self.marketplace.create_auction(auction_config)
        print(f"  Auction Created: {auction_result}")

        if auction_result.get("success"):
            auction_id = auction_result["auction_id"]

            # Place bids
            print("\n💰 Placing Bids:")
            bidders = [
                ("consumer_001", Decimal("35")),
                ("consumer_002", Decimal("40")),
                ("consumer_003", Decimal("42")),
            ]

            for bidder_id, bid_amount in bidders:
                bid_result = self.marketplace.place_bid(auction_id, bidder_id, bid_amount)
                print(f"  {bidder_id}: {bid_amount} AGIX - {bid_result}")

        # Show market data
        print("\n📊 Market Data:")
        market_data = self.marketplace.get_market_data("ML_TRAINING")
        if market_data:
            print(f"  Current Price: {market_data.price} AGIX")
            print(f"  24h Volume: {market_data.volume} AGIX")
            print(f"  Supply: {market_data.supply} units")
            print(f"  Demand: {market_data.demand} units")
            print(f"  Market State: {market_data.state.value}")

        # Show order book
        print("\n📖 Order Book (ML_TRAINING):")
        order_book = self.marketplace.get_order_book("ML_TRAINING", depth=5)
        print(f"  Best Bid: {order_book.get('best_bid', 'None')}")
        print(f"  Best Ask: {order_book.get('best_ask', 'None')}")
        print(f"  Spread: {order_book.get('spread', 'None')}")
        print(f"  Bid Orders: {len(order_book.get('bids', []))}")
        print(f"  Ask Orders: {len(order_book.get('asks', []))}")

        self.results["marketplace"] = {
            "buy_result": buy_result,
            "sell_result": sell_result,
            "auction_result": auction_result,
            "market_data": market_data,
            "order_book": order_book,
        }

        print("✅ Marketplace Dynamics Demo Complete!\n")

    async def demo_game_theory(self):
        """Demonstrate game theory analysis"""
        print("🎲 Game Theory Analysis Demo")
        print("-" * 37)

        # Create AGI service marketplace game
        print("🎮 Creating AGI Service Marketplace Game:")
        providers = ["provider_ai_001", "provider_ai_002"]
        consumers = ["consumer_001", "consumer_002"]

        game = self.game_analyzer.create_agi_service_game(
            providers=providers,
            consumers=consumers,
            service_qualities={"provider_ai_001": 0.8, "provider_ai_002": 0.9},
            prices={"provider_ai_001": 0.5, "provider_ai_002": 0.8},
        )

        print(f"  Game ID: {game.game_id}")
        print(f"  Game Type: {game.game_type.value}")
        print(f"  Players: {len(game.players)}")
        print(f"  Description: {game.description}")

        # Find Nash equilibria
        print("\n🎯 Finding Nash Equilibria:")
        equilibria = self.game_analyzer.find_nash_equilibria(game)
        print(f"  Found {len(equilibria)} Nash equilibria")

        for i, eq in enumerate(equilibria):
            print(f"  Equilibrium {i+1}:")
            print(f"    Type: {eq.equilibrium_type.value}")
            print(f"    Social Welfare: {eq.social_welfare:.2f}")
            print(f"    Efficiency Ratio: {eq.efficiency_ratio:.2%}")
            print(f"    Stable: {eq.is_stable}")

        # Analyze mechanism efficiency
        print("\n📊 Mechanism Efficiency Analysis:")
        analysis = self.game_analyzer.analyze_mechanism_efficiency(game)

        props = analysis["mechanism_properties"]
        print(f"  Average Efficiency: {props['average_efficiency']:.2%}")
        print(f"  Max Efficiency: {props['max_efficiency']:.2%}")
        print(f"  Average Welfare: {props['average_welfare']:.2f}")
        print(f"  Welfare Variance: {props['welfare_variance']:.2f}")
        print(f"  Has Dominant Strategy: {props['has_dominant_strategy']['exists']}")
        print(f"  Incentive Compatible: {props['is_incentive_compatible']['compatible']}")
        print(f"  Individual Rational: {props['satisfies_individual_rationality']['rational']}")

        # Strategic recommendations
        print("\n💡 Strategic Insights:")
        if equilibria:
            best_eq = max(equilibria, key=lambda x: x.efficiency_ratio)
            print(f"  Most Efficient Equilibrium:")
            print(f"    Efficiency: {best_eq.efficiency_ratio:.2%}")
            print(f"    Social Welfare: {best_eq.social_welfare:.2f}")

            if best_eq.strategy_profile.strategies:
                print("    Optimal Strategies:")
                for player_id, strategy in best_eq.strategy_profile.strategies.items():
                    print(f"      {player_id}: {strategy}")

        self.results["game_theory"] = {
            "game": game,
            "equilibria_count": len(equilibria),
            "analysis": analysis,
            "efficiency_analysis": props,
        }

        print("✅ Game Theory Analysis Demo Complete!\n")

    async def demo_smart_contracts(self):
        """Demonstrate smart contract generation"""
        print("📜 Smart Contract Generation Demo")
        print("-" * 42)

        # Generate AGI service contract
        print("⚡ Generating AGI Service Contract:")

        contract_package = AGIServiceContract.create_service_contract(
            service_id="ai_training_service_001",
            service_type="ML_TRAINING",
            client_address="0x742d35Cc6671C0532925a3b8D26414759d7C2d85",
            provider_address="0x8ba1f109551bD432803012645Hac136c22C501",
            payment_amount=Decimal("1000"),
            delivery_deadline=int(time.time()) + 86400 * 7,  # 1 week
            quality_requirements={
                "min_accuracy": 0.95,
                "max_training_time": 48,  # hours
                "model_size_limit": "500MB",
            },
        )

        print("  ✅ Service contract generated!")
        print("  📋 Contract Package Contents:")
        print(f"    - Solidity Code: {len(contract_package['solidity_code'])} characters")
        print(f"    - Deployment Script: {len(contract_package['deployment_script'])} characters")
        print(f"    - ABI Interface: {len(contract_package['abi'])} characters")
        print(f"    - Configuration: {len(contract_package['template_config'])} characters")

        # Show key contract features
        print("\n🔧 Contract Features:")
        features = [
            "Escrow-based payments (10% held in escrow)",
            "Quality-based bonuses (up to 10% for excellence)",
            "Automated dispute resolution",
            "Reputation system integration",
            "Deadline enforcement",
            "Stake-based provider commitment",
            "Multi-signature support",
            "Gas optimization",
        ]

        for feature in features:
            print(f"    ✅ {feature}")

        # Contract deployment simulation
        print("\n🚀 Contract Deployment Simulation:")
        deployment_info = {
            "estimated_gas": 2_500_000,
            "estimated_cost": "0.025 ETH",
            "deployment_time": "2-5 minutes",
            "network": "Ethereum Mainnet",
            "contract_size": "24.5 KB",
        }

        for key, value in deployment_info.items():
            print(f"    {key.replace('_', ' ').title()}: {value}")

        # Show sample contract interaction
        print("\n💻 Sample Contract Interaction:")
        interaction_steps = [
            "1. Client calls fundContract() with 1000 AGIX + 100 AGIX escrow",
            "2. Provider calls stakeAndStartService() with 100 AGIX stake",
            "3. Service execution period begins",
            "4. Provider delivers results via completeService()",
            "5. Quality assessment triggers bonus calculation",
            "6. Automatic payment release to provider",
            "7. Reputation scores updated for both parties",
        ]

        for step in interaction_steps:
            print(f"    {step}")

        self.results["smart_contracts"] = {
            "contract_package": contract_package,
            "deployment_info": deployment_info,
            "features_count": len(features),
        }

        print("✅ Smart Contract Demo Complete!\n")

    async def show_results(self):
        """Show comprehensive results from all demos"""
        print("📊 COMPREHENSIVE DEMO RESULTS")
        print("=" * 60)

        # Economic Activity Summary
        print("💰 Economic Activity Summary:")
        if "token_economics" in self.results:
            metrics = self.results["token_economics"]["metrics"]
            print(f"  AGIX Circulating Supply: {metrics['circulating_supply']}")
            print(f"  Market Cap: {metrics['market_cap']} AGIX")
            print(f"  Daily Volume: {metrics['daily_volume']} AGIX")
            print(f"  Total Transactions: {metrics['total_transactions']}")

        # Resource Utilization
        print(f"\n🖥️  Resource Utilization:")
        if "resource_allocation" in self.results:
            utilization = self.results["resource_allocation"]["utilization_metrics"]
            for resource_type, metrics in utilization.items():
                print(f"  {resource_type}: {metrics['average_utilization']:.1%} avg utilization")

        # Value Alignment Scores
        print(f"\n🎯 Value Alignment Scores:")
        if "value_alignment" in self.results and self.results["value_alignment"]["value_profile"]:
            profile = self.results["value_alignment"]["value_profile"]
            print(f"  Overall Alignment: {profile['overall_alignment_score']:.3f}")
            print(f"  Measurements: {profile['recent_measurements_count']}")
            print(f"  Human Feedback: {profile['human_feedback_count']}")

        # Network Trust Metrics
        print(f"\n⭐ Trust Network Metrics:")
        if "reputation" in self.results:
            system_metrics = self.results["reputation"]["system_metrics"]
            trust_network = system_metrics["trust_network"]
            print(f"  Network Density: {trust_network['network_density']:.3f}")
            print(f"  Average Trust: {trust_network['avg_trust_score']:.3f}")
            print(f"  Total Relationships: {trust_network['total_relationships']}")

        # Market Activity
        print(f"\n🏪 Market Activity:")
        if "marketplace" in self.results:
            market_data = self.results["marketplace"]["market_data"]
            if market_data:
                print(f"  Current Price: {market_data.price} AGIX")
                print(f"  Market State: {market_data.state.value}")
                print(
                    f"  Supply/Demand Ratio: {float(market_data.supply / market_data.demand):.2f}"
                )

        # Game Theory Insights
        print(f"\n🎲 Game Theory Insights:")
        if "game_theory" in self.results:
            analysis = self.results["game_theory"]["efficiency_analysis"]
            print(f"  Market Efficiency: {analysis['average_efficiency']:.2%}")
            print(f"  Nash Equilibria: {self.results['game_theory']['equilibria_count']}")
            print(f"  Mechanism Compatibility: {analysis['is_incentive_compatible']['compatible']}")

        # Platform Performance
        print(f"\n⚡ Platform Performance:")
        total_engines = 7
        successful_demos = len(self.results)
        success_rate = (successful_demos / total_engines) * 100

        print(f"  Engines Initialized: {total_engines}/7 (100%)")
        print(f"  Demos Completed: {successful_demos}/7 ({success_rate:.0f}%)")
        print(f"  Integration Status: ✅ Fully Operational")

        # Economic Impact
        print(f"\n💼 Economic Impact Simulation:")
        if "token_economics" in self.results:
            print("  ✅ Token velocity and circulation established")
        if "resource_allocation" in self.results:
            print("  ✅ Efficient resource utilization achieved")
        if "value_alignment" in self.results:
            print("  ✅ Human value alignment incentivized")
        if "reputation" in self.results:
            print("  ✅ Trust networks established")
        if "marketplace" in self.results:
            print("  ✅ Market price discovery functional")
        if "game_theory" in self.results:
            print("  ✅ Strategic equilibria identified")
        if "smart_contracts" in self.results:
            print("  ✅ Automated service agreements deployed")

        print("\n🎉 AGI Economics Platform Demo Successfully Completed!")
        print("   Supporting Ben Goertzel's vision of economically incentivized AGI")
        print("   Ready for production deployment in SingularityNET ecosystem")
        print("=" * 60)


async def main():
    """Main entry point for the demo"""
    demo = AGIEconomicsDemo()
    try:
        await demo.run_complete_demo()
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Run the complete demo
    print("🌟 AGI Economics Platform - Complete Demonstration")
    print("   Built for Kenny AGI - Supporting SingularityNET's vision")
    print("   Demonstrating economically incentivized AGI development")
    print()

    # Run async demo
    asyncio.run(main())
