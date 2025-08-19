#!/usr/bin/env python3
"""
Knowledge Collaboration Example
===============================

Demonstrates advanced knowledge graph merging, goal negotiation,
and collaborative problem-solving between multiple AGIs.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agi_communication import (
    AGICommunicationProtocol, AGIIdentity, KnowledgeGraph, KnowledgeNode, KnowledgeEdge,
    Goal, GoalType, NegotiationStrategy, Problem, ProblemType, CollaborationStrategy
)


class KnowledgeCollaborationDemo:
    """Demonstrates advanced knowledge collaboration between AGIs."""
    
    def __init__(self):
        self.physics_agi = None
        self.math_agi = None
        self.ai_agi = None
    
    async def setup_specialist_agis(self):
        """Set up three specialist AGIs for collaboration."""
        # Physics specialist AGI
        physics_identity = AGIIdentity(
            id="physics_specialist_001",
            name="Physics Reasoning AGI",
            architecture="symbolic_ai",
            version="1.0.0",
            capabilities=["physics_reasoning", "equation_solving", "theoretical_modeling"]
        )
        
        # Mathematics specialist AGI  
        math_identity = AGIIdentity(
            id="math_specialist_001",
            name="Mathematics AGI",
            architecture="hybrid_neuro_symbolic",
            version="1.0.0", 
            capabilities=["mathematical_proof", "optimization", "statistical_analysis"]
        )
        
        # AI research specialist AGI
        ai_identity = AGIIdentity(
            id="ai_researcher_001",
            name="AI Research AGI",
            architecture="neural_network",
            version="1.0.0",
            capabilities=["machine_learning", "algorithm_design", "knowledge_synthesis"]
        )
        
        # Initialize protocols
        self.physics_agi = AGICommunicationProtocol(physics_identity)
        self.math_agi = AGICommunicationProtocol(math_identity)
        self.ai_agi = AGICommunicationProtocol(ai_identity)
        
        # Cross-register all AGIs
        agis = {
            physics_identity.id: physics_identity,
            math_identity.id: math_identity, 
            ai_identity.id: ai_identity
        }
        
        for protocol in [self.physics_agi, self.math_agi, self.ai_agi]:
            for agi_id, identity in agis.items():
                if agi_id != protocol.identity.id:
                    protocol.known_agis[agi_id] = identity
        
        # Start all protocols
        await self.physics_agi.start()
        await self.math_agi.start() 
        await self.ai_agi.start()
        
        print("✓ Three specialist AGIs initialized:")
        print("  - Physics Specialist (Symbolic AI)")
        print("  - Mathematics Specialist (Hybrid)")
        print("  - AI Research Specialist (Neural)")
    
    async def create_knowledge_graphs(self):
        """Create domain-specific knowledge graphs for each AGI."""
        print("\n--- Creating Domain Knowledge Graphs ---")
        
        # Physics knowledge graph
        physics_kg = KnowledgeGraph(
            id="physics_knowledge_001",
            source_agi="physics_specialist_001"
        )
        
        # Add physics concepts
        physics_nodes = [
            KnowledgeNode(id="einstein", type="Scientist", label="Albert Einstein", 
                         properties={"birth_year": 1879, "field": "theoretical_physics"}),
            KnowledgeNode(id="relativity", type="Theory", label="Theory of Relativity",
                         properties={"year_proposed": 1905, "type": "physical_theory"}),
            KnowledgeNode(id="energy_mass", type="Equation", label="E=mc²",
                         properties={"domain": "physics", "type": "mass_energy_equivalence"}),
            KnowledgeNode(id="spacetime", type="Concept", label="Spacetime",
                         properties={"dimensions": 4, "curvature": "variable"})
        ]
        
        physics_edges = [
            KnowledgeEdge(id="einstein_developed", source="einstein", target="relativity", 
                         relation_type="developed", confidence=0.99),
            KnowledgeEdge(id="relativity_includes", source="relativity", target="energy_mass",
                         relation_type="includes", confidence=0.95),
            KnowledgeEdge(id="relativity_describes", source="relativity", target="spacetime",
                         relation_type="describes", confidence=0.98)
        ]
        
        for node in physics_nodes:
            physics_kg.add_node(node)
        for edge in physics_edges:
            physics_kg.add_edge(edge)
        
        # Mathematics knowledge graph
        math_kg = KnowledgeGraph(
            id="math_knowledge_001", 
            source_agi="math_specialist_001"
        )
        
        math_nodes = [
            KnowledgeNode(id="einstein", type="Person", label="A. Einstein",
                         properties={"contributions": ["tensor_calculus"], "field": "mathematical_physics"}),
            KnowledgeNode(id="tensor_calculus", type="Mathematical_Framework", label="Tensor Calculus",
                         properties={"complexity": "advanced", "applications": ["general_relativity"]}),
            KnowledgeNode(id="differential_geometry", type="Mathematical_Field", label="Differential Geometry",
                         properties={"foundational_for": ["general_relativity"]}),
            KnowledgeNode(id="optimization", type="Mathematical_Method", label="Optimization Theory",
                         properties={"applications": ["physics", "ai", "engineering"]})
        ]
        
        math_edges = [
            KnowledgeEdge(id="einstein_used", source="einstein", target="tensor_calculus",
                         relation_type="used", confidence=0.95),
            KnowledgeEdge(id="tensor_extends", source="tensor_calculus", target="differential_geometry", 
                         relation_type="extends", confidence=0.90),
            KnowledgeEdge(id="optimization_applies", source="optimization", target="tensor_calculus",
                         relation_type="applies_to", confidence=0.80)
        ]
        
        for node in math_nodes:
            math_kg.add_node(node)
        for edge in math_edges:
            math_kg.add_edge(edge)
        
        # AI knowledge graph
        ai_kg = KnowledgeGraph(
            id="ai_knowledge_001",
            source_agi="ai_researcher_001"
        )
        
        ai_nodes = [
            KnowledgeNode(id="neural_networks", type="AI_Architecture", label="Neural Networks",
                         properties={"inspired_by": "biology", "learning_type": "connectionist"}),
            KnowledgeNode(id="optimization", type="AI_Method", label="Optimization Algorithms", 
                         properties={"essential_for": ["training", "inference"]}),
            KnowledgeNode(id="physics_informed_nn", type="AI_Approach", label="Physics-Informed Neural Networks",
                         properties={"combines": ["physics", "machine_learning"]}),
            KnowledgeNode(id="symbolic_ai", type="AI_Paradigm", label="Symbolic AI",
                         properties={"based_on": "logic", "reasoning_type": "explicit"})
        ]
        
        ai_edges = [
            KnowledgeEdge(id="nn_uses", source="neural_networks", target="optimization",
                         relation_type="uses", confidence=0.99),
            KnowledgeEdge(id="pinn_combines", source="physics_informed_nn", target="neural_networks",
                         relation_type="combines_with", confidence=0.95),
            KnowledgeEdge(id="pinn_incorporates", source="physics_informed_nn", target="optimization",
                         relation_type="incorporates", confidence=0.90)
        ]
        
        for node in ai_nodes:
            ai_kg.add_node(node)
        for edge in ai_edges:
            ai_kg.add_edge(edge)
        
        print(f"✓ Physics KG: {len(physics_kg.nodes)} nodes, {len(physics_kg.edges)} edges")
        print(f"✓ Math KG: {len(math_kg.nodes)} nodes, {len(math_kg.edges)} edges")
        print(f"✓ AI KG: {len(ai_kg.nodes)} nodes, {len(ai_kg.edges)} edges")
        
        return physics_kg, math_kg, ai_kg
    
    async def demonstrate_knowledge_merging(self, physics_kg, math_kg, ai_kg):
        """Demonstrate knowledge graph merging with conflict resolution."""
        print("\n--- Knowledge Graph Merging ---")
        
        # Use the physics AGI's knowledge merger to merge all graphs
        merger = self.physics_agi.knowledge_merger
        
        # Merge all three knowledge graphs
        merge_result = await merger.merge_graphs([physics_kg, math_kg, ai_kg])
        
        merged_graph = merge_result.merged_graph
        print(f"✓ Merged graph created with {len(merged_graph.nodes)} nodes and {len(merged_graph.edges)} edges")
        
        # Analyze conflicts
        print(f"✓ Total conflicts detected: {len(merge_result.conflicts)}")
        print(f"✓ Resolved conflicts: {len(merge_result.resolved_conflicts)}")
        print(f"✓ Unresolved conflicts: {len(merge_result.unresolved_conflicts)}")
        print(f"✓ Overall confidence score: {merge_result.confidence_score:.3f}")
        
        # Show some resolved conflicts
        if merge_result.resolved_conflicts:
            print("\nResolved Conflicts:")
            for conflict in merge_result.resolved_conflicts[:2]:
                print(f"  - {conflict.conflict_type.value}: {conflict.description}")
        
        # Show merge statistics
        stats = merge_result.merge_statistics
        print(f"\nMerge Statistics:")
        print(f"  - Node reduction ratio: {stats['node_reduction_ratio']:.2%}")
        print(f"  - Edge reduction ratio: {stats['edge_reduction_ratio']:.2%}")
        
        return merged_graph
    
    async def demonstrate_goal_negotiation(self):
        """Demonstrate goal negotiation between specialist AGIs."""
        print("\n--- Goal Negotiation ---")
        
        # Create collaborative research goals
        physics_goal = Goal(
            id="physics_research_goal",
            description="Develop quantum gravity theory using mathematical frameworks",
            goal_type=GoalType.COLLABORATIVE,
            priority=0.9,
            owner_agi="physics_specialist_001",
            resource_requirements={"computational_power": 0.7, "theoretical_expertise": 0.9}
        )
        
        math_goal = Goal(
            id="math_optimization_goal", 
            description="Create advanced optimization methods for AI training",
            goal_type=GoalType.COLLABORATIVE,
            priority=0.8,
            owner_agi="math_specialist_001",
            resource_requirements={"computational_power": 0.6, "algorithmic_expertise": 0.8}
        )
        
        ai_goal = Goal(
            id="ai_integration_goal",
            description="Develop physics-informed AI architectures", 
            goal_type=GoalType.COLLABORATIVE,
            priority=0.85,
            owner_agi="ai_researcher_001",
            resource_requirements={"computational_power": 0.8, "domain_knowledge": 0.7}
        )
        
        # Physics AGI initiates negotiation
        negotiator = self.physics_agi.goal_negotiator
        session_id = await negotiator.initiate_negotiation(
            goals=[physics_goal, math_goal, ai_goal],
            participants=["math_specialist_001", "ai_researcher_001"],
            strategy=NegotiationStrategy.INTEGRATIVE
        )
        
        print(f"✓ Goal negotiation session initiated: {session_id}")
        
        # Wait for negotiation to proceed
        await asyncio.sleep(2)
        
        # Evaluate proposals
        evaluation = await negotiator.evaluate_proposals(session_id)
        
        if evaluation.get('social_welfare_scores'):
            best_proposal = evaluation['best_social_welfare']
            most_fair = evaluation['most_fair']
            
            print(f"✓ Best social welfare proposal: {best_proposal[0]} (score: {best_proposal[1]:.3f})")
            print(f"✓ Most fair proposal: {most_fair[0]} (score: {most_fair[1]:.3f})")
            print(f"✓ Pareto optimal proposals: {len(evaluation['pareto_optimal_proposals'])}")
        
        # Find optimal agreement
        optimal_agreement = await negotiator.find_optimal_agreement(session_id)
        if optimal_agreement:
            print(f"✓ Optimal agreement found for {len(optimal_agreement.goals_addressed)} goals")
        
        return session_id
    
    async def demonstrate_collaborative_problem_solving(self, merged_graph):
        """Demonstrate collaborative problem solving using merged knowledge."""
        print("\n--- Collaborative Problem Solving ---")
        
        # Define a complex interdisciplinary problem
        problem = Problem(
            id="interdisciplinary_research_problem",
            description="Design a physics-informed neural network for quantum field theory predictions",
            problem_type=ProblemType.CREATIVE,
            complexity=0.9,
            constraints={
                "computational_budget": 1000000,  # computational units
                "accuracy_requirement": 0.95,
                "interpretability": 0.8
            },
            success_criteria={
                "prediction_accuracy": 0.95,
                "theoretical_consistency": 0.90,
                "computational_efficiency": 0.75
            },
            input_data={
                "domain": "quantum_field_theory", 
                "available_data": "simulated_quantum_experiments",
                "constraints": ["quantum_principles", "relativity_compatibility"]
            }
        )
        
        # AI AGI coordinates the collaborative problem solving
        problem_solver = self.ai_agi.problem_solver
        collaboration_id = await problem_solver.start_collaboration(
            problem=problem,
            participants=["physics_specialist_001", "math_specialist_001"],
            strategy=CollaborationStrategy.HYBRID
        )
        
        print(f"✓ Collaborative problem-solving session started: {collaboration_id}")
        
        # Wait for task assignment and initial processing
        await asyncio.sleep(3)
        
        # Check collaboration progress
        if collaboration_id in problem_solver.active_sessions:
            session = problem_solver.active_sessions[collaboration_id]
            completion_rate = session.get_completion_rate()
            
            print(f"✓ Collaboration progress: {completion_rate:.1%}")
            print(f"✓ Tasks created: {len(session.tasks)}")
            print(f"✓ Participants: {len(session.participants)}")
            
            # Show task breakdown
            available_tasks = session.get_available_tasks()
            print(f"✓ Available tasks: {len(available_tasks)}")
            
            if available_tasks:
                for task in available_tasks[:3]:  # Show first 3 tasks
                    print(f"  - {task.description}")
        
        return collaboration_id
    
    async def demonstrate_multi_modal_knowledge_sharing(self):
        """Demonstrate multi-modal knowledge sharing between AGIs."""
        print("\n--- Multi-Modal Knowledge Sharing ---")
        
        # Create multi-modal data combining text, logic, and embeddings
        multimodal_data = await self.physics_agi.multimodal_communicator.create_multimodal_data(
            primary_data="Quantum entanglement is a physical phenomenon occurring when particles remain connected",
            primary_modality="text"
        )
        
        # Add logical representation
        await self.physics_agi.multimodal_communicator.add_auxiliary_modality(
            multimodal_data,
            auxiliary_data="entangled(particle_a, particle_b) -> correlated_states(particle_a, particle_b)",
            modality="logic"
        )
        
        # Enhance with cross-modal translations
        await self.physics_agi.multimodal_communicator.enhance_with_cross_modal_data(multimodal_data)
        
        print(f"✓ Multi-modal data created with {len(multimodal_data.get_modalities())} modalities")
        print(f"✓ Total data size: {multimodal_data.get_total_size()} bytes")
        
        # Send to math AGI
        success = await self.physics_agi.multimodal_communicator.send_multimodal_data(
            recipient_id="math_specialist_001",
            data=multimodal_data
        )
        
        if success:
            print("✓ Multi-modal knowledge successfully shared with Math AGI")
        
        await asyncio.sleep(1)  # Allow processing time
    
    async def demonstrate_emergent_language(self):
        """Demonstrate emergent language evolution between AGIs."""
        print("\n--- Emergent Language Evolution ---")
        
        # Generate novel expressions for scientific concepts
        concepts = ["quantum_superposition", "neural_plasticity", "mathematical_optimization"]
        
        for concept in concepts:
            # Physics AGI generates expression
            result = await self.physics_agi.language_evolver.generate_novel_expression(
                concept=concept,
                population_id="default" 
            )
            
            print(f"✓ Physics AGI expression for '{concept}': '{result['expression']}' (confidence: {result['confidence']:.3f})")
            
            # Math AGI interprets the expression
            interpretation = await self.math_agi.language_evolver.interpret_novel_expression(
                expression=result['expression'],
                population_id="default"
            )
            
            print(f"  → Math AGI interpretation: '{interpretation['interpretation']}' (confidence: {interpretation['confidence']:.3f})")
        
        # Record communication success for language evolution
        await self.physics_agi.language_evolver.record_communication_event(
            sender_id="physics_specialist_001",
            receiver_id="math_specialist_001", 
            message_content="quantum_superposition",
            genes_used=["symbol_001", "grammar_001"],
            success=True,
            understanding_score=0.8,
            efficiency_score=0.7,
            context="scientific_collaboration"
        )
        
        print("✓ Communication feedback recorded for language evolution")
    
    async def show_collaboration_statistics(self):
        """Display comprehensive collaboration statistics."""
        print("\n--- Collaboration Statistics ---")
        
        # Communication statistics
        for name, protocol in [("Physics AGI", self.physics_agi), ("Math AGI", self.math_agi), ("AI AGI", self.ai_agi)]:
            stats = protocol.get_communication_stats()
            print(f"\n{name}:")
            print(f"  - Active sessions: {stats.get('active_sessions', 0)}")
            print(f"  - Known AGIs: {stats.get('known_agis', 0)}")
            print(f"  - Protocol version: {stats.get('protocol_version', 'N/A')}")
        
        # Knowledge merger statistics
        merger_stats = self.physics_agi.knowledge_merger.get_merge_statistics()
        print(f"\nKnowledge Merging:")
        print(f"  - Total merges: {merger_stats.get('total_merges', 0)}")
        print(f"  - Average confidence: {merger_stats.get('average_confidence', 0):.3f}")
        print(f"  - Resolution rate: {merger_stats.get('resolution_rate', 0):.1%}")
        
        # Goal negotiation statistics
        negotiation_stats = self.physics_agi.goal_negotiator.get_negotiation_statistics()
        print(f"\nGoal Negotiation:")
        print(f"  - Total negotiations: {negotiation_stats.get('total_negotiations', 0)}")
        print(f"  - Success rate: {negotiation_stats.get('success_rate', 0):.1%}")
        print(f"  - Average duration: {negotiation_stats.get('average_duration_seconds', 0):.1f}s")
        
        # Problem solving statistics
        problem_stats = self.ai_agi.problem_solver.get_collaboration_statistics()
        print(f"\nProblem Solving:")
        print(f"  - Total collaborations: {problem_stats.get('total_collaborations', 0)}")
        print(f"  - Success rate: {problem_stats.get('success_rate', 0):.1%}")
        print(f"  - Average completion rate: {problem_stats.get('average_completion_rate', 0):.1%}")
    
    async def cleanup(self):
        """Clean up all AGI protocols."""
        print("\n--- Cleanup ---")
        
        for name, protocol in [("Physics", self.physics_agi), ("Math", self.math_agi), ("AI", self.ai_agi)]:
            if protocol:
                await protocol.stop()
                print(f"✓ {name} AGI protocol stopped")
    
    async def run_demo(self):
        """Run the complete knowledge collaboration demo."""
        print("🧠 AGI Knowledge Collaboration Demo")
        print("=" * 50)
        
        try:
            # Setup
            await self.setup_specialist_agis()
            
            # Create and merge knowledge
            physics_kg, math_kg, ai_kg = await self.create_knowledge_graphs()
            merged_graph = await self.demonstrate_knowledge_merging(physics_kg, math_kg, ai_kg)
            
            # Collaborative activities
            await self.demonstrate_goal_negotiation()
            await self.demonstrate_collaborative_problem_solving(merged_graph)
            await self.demonstrate_multi_modal_knowledge_sharing()
            await self.demonstrate_emergent_language()
            
            # Results
            await self.show_collaboration_statistics()
            
            print("\n🎉 Knowledge collaboration demo completed successfully!")
            print("Multiple AGIs successfully collaborated on complex interdisciplinary problems!")
            
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            raise
            
        finally:
            await self.cleanup()


async def main():
    """Main entry point for the knowledge collaboration demo."""
    demo = KnowledgeCollaborationDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())