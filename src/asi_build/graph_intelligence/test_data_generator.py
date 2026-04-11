"""
Test Data Generator for Kenny Graph Intelligence System

Generates realistic test data for development and testing purposes.
"""

import random
import time
from typing import List, Dict, Any, Tuple
from .schema import (
    create_ui_element, create_community, create_workflow,
    NodeType, RelationshipType, KnowledgeGraphSchema,
    ApplicationNode, ScreenNode, PatternNode, ErrorNode, Relationship
)
from .schema_manager import SchemaManager


class TestDataGenerator:
    """Generates realistic test data for the knowledge graph."""
    
    def __init__(self, schema_manager: SchemaManager):
        self.sm = schema_manager
        self.schema = KnowledgeGraphSchema()
        
        # Sample data for realistic generation
        self.ui_element_types = ['button', 'menu', 'text_field', 'label', 'dialog', 'icon', 'checkbox', 'dropdown']
        self.button_texts = ['Save', 'Cancel', 'OK', 'Apply', 'Close', 'Open', 'New', 'Delete', 'Edit', 'Send']
        self.menu_texts = ['File', 'Edit', 'View', 'Tools', 'Help', 'Settings', 'Options', 'Window']
        self.applications = ['vscode', 'chrome', 'notepad', 'calculator', 'file_manager', 'terminal', 'email_client']
        self.workflow_names = [
            'Save Document', 'Create New File', 'Send Email', 'Open Browser', 
            'Copy File', 'Install Software', 'Search Files', 'Change Settings'
        ]
        self.community_purposes = [
            'file_operations', 'email_composition', 'web_browsing', 'system_settings',
            'text_editing', 'media_playback', 'file_management', 'communication'
        ]
        
    def generate_ui_elements(self, count: int = 50) -> List[str]:
        """Generate realistic UI elements."""
        element_ids = []
        
        for _ in range(count):
            element_type = random.choice(self.ui_element_types)
            
            # Generate realistic text based on element type
            if element_type == 'button':
                text = random.choice(self.button_texts)
            elif element_type == 'menu':
                text = random.choice(self.menu_texts)
            elif element_type == 'text_field':
                text = random.choice(['Username', 'Password', 'Email', 'Search', 'Filename'])
            elif element_type == 'label':
                text = random.choice(['Name:', 'Date:', 'Status:', 'Type:', 'Size:'])
            else:
                text = f"{element_type.title()} {random.randint(1, 10)}"
            
            # Generate realistic coordinates
            x = random.randint(50, 1200)
            y = random.randint(50, 800)
            
            element = create_ui_element(
                element_type=element_type,
                text=text,
                coordinates=[x, y],
                confidence=random.uniform(0.8, 1.0),
                application=random.choice(self.applications),
                properties={
                    'clickable': element_type in ['button', 'menu', 'icon'],
                    'visible': True,
                    'enabled': random.choice([True, True, True, False])  # Mostly enabled
                }
            )
            
            element_id = self.sm.create_node(element, NodeType.UI_ELEMENT)
            element_ids.append(element_id)
        
        return element_ids
    
    def generate_applications(self, count: int = 7) -> List[str]:
        """Generate application nodes."""
        app_ids = []
        
        for i, app_name in enumerate(self.applications[:count]):
            app = ApplicationNode(
                name=app_name,
                version=f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                process_id=random.randint(1000, 9999),
                window_title=f"{app_name.title()} - Main Window",
                ui_framework=random.choice(['qt', 'gtk', 'electron', 'native']),
                automation_confidence=random.uniform(0.7, 0.95),
                last_active=time.time() - random.randint(0, 3600)
            )
            
            app_id = self.sm.create_node(app, NodeType.APPLICATION)
            app_ids.append(app_id)
        
        return app_ids
    
    def generate_communities(self, ui_element_ids: List[str], count: int = 15) -> List[str]:
        """Generate communities containing UI elements."""
        community_ids = []
        
        # Ensure we have enough elements
        if len(ui_element_ids) < count * 2:
            return community_ids
        
        # Shuffle elements for random distribution
        shuffled_elements = ui_element_ids.copy()
        random.shuffle(shuffled_elements)
        
        elements_per_community = len(ui_element_ids) // count
        
        for i in range(count):
            start_idx = i * elements_per_community
            end_idx = start_idx + elements_per_community + random.randint(0, 3)
            
            if start_idx >= len(shuffled_elements):
                break
                
            members = shuffled_elements[start_idx:min(end_idx, len(shuffled_elements))]
            
            if not members:
                continue
            
            community = create_community(
                purpose=random.choice(self.community_purposes),
                members=members,
                modularity=random.uniform(0.3, 0.9),
                frequency=random.randint(1, 200),
                success_rate=random.uniform(0.7, 0.98),
                avg_completion_time=random.uniform(1.0, 10.0),
                detection_algorithm=random.choice(['louvain', 'girvan_newman', 'spectral'])
            )
            
            community_id = self.sm.create_node(community, NodeType.COMMUNITY)
            community_ids.append(community_id)
            
            # Create CONTAINS relationships to members
            for member_id in members:
                rel = self.schema.create_relationship(
                    from_node=community_id,
                    to_node=member_id,
                    rel_type=RelationshipType.CONTAINS,
                    weight=1.0,
                    confidence=random.uniform(0.8, 1.0)
                )
                self.sm.create_relationship(rel)
        
        return community_ids
    
    def generate_workflows(self, community_ids: List[str], count: int = 10) -> List[str]:
        """Generate workflow nodes."""
        workflow_ids = []
        
        for i in range(count):
            if i >= len(self.workflow_names):
                name = f"Workflow {i + 1}"
            else:
                name = self.workflow_names[i]
            
            # Generate realistic workflow steps
            steps = []
            step_count = random.randint(3, 8)
            
            for step_num in range(step_count):
                steps.append({
                    'step_number': step_num + 1,
                    'action': random.choice(['click', 'type', 'wait', 'verify']),
                    'target': f"element_{random.randint(1, 100)}",
                    'description': f"Step {step_num + 1} description"
                })
            
            workflow = create_workflow(
                name=name,
                description=f"Automated workflow for {name.lower()}",
                steps=steps,
                status=random.choice(['completed', 'completed', 'pending', 'failed']),
                success_rate=random.uniform(0.6, 0.95),
                avg_duration=random.uniform(5.0, 30.0),
                execution_count=random.randint(1, 100),
                complexity=random.choice(['simple', 'medium', 'complex'])
            )
            
            workflow_id = self.sm.create_node(workflow, NodeType.WORKFLOW)
            workflow_ids.append(workflow_id)
            
            # Link workflow to communities
            related_communities = random.sample(
                community_ids, 
                min(random.randint(1, 3), len(community_ids))
            )
            
            for community_id in related_communities:
                rel = self.schema.create_relationship(
                    from_node=workflow_id,
                    to_node=community_id,
                    rel_type=RelationshipType.REQUIRES,
                    weight=random.uniform(0.5, 1.0)
                )
                self.sm.create_relationship(rel)
        
        return workflow_ids
    
    def generate_patterns(self, count: int = 20) -> List[str]:
        """Generate learned pattern nodes."""
        pattern_ids = []
        
        pattern_types = ['sequence', 'prediction', 'optimization', 'error_recovery']
        
        for i in range(count):
            pattern = PatternNode(
                pattern_type=random.choice(pattern_types),
                sequence=[f"action_{j}" for j in range(random.randint(2, 6))],
                frequency=random.randint(1, 50),
                confidence=random.uniform(0.6, 0.95),
                context={
                    'application': random.choice(self.applications),
                    'user_type': random.choice(['beginner', 'intermediate', 'expert']),
                    'time_of_day': random.choice(['morning', 'afternoon', 'evening'])
                },
                success_rate=random.uniform(0.7, 0.98),
                last_used=time.time() - random.randint(0, 86400 * 7),  # Last week
                generalization_score=random.uniform(0.4, 0.9)
            )
            
            pattern_id = self.sm.create_node(pattern, NodeType.PATTERN)
            pattern_ids.append(pattern_id)
        
        return pattern_ids
    
    def generate_screen_captures(self, count: int = 5) -> List[str]:
        """Generate screen capture nodes."""
        screen_ids = []
        
        for i in range(count):
            screen = ScreenNode(
                resolution=[1920, 1080],
                screenshot_path=f"/screenshots/screen_{i:03d}.png",
                screenshot_hash=f"hash_{random.randint(100000, 999999)}",
                active_window=random.choice(self.applications),
                ui_elements_count=random.randint(20, 100),
                processing_time=random.uniform(0.5, 2.0),
                ocr_confidence=random.uniform(0.8, 0.98)
            )
            
            screen_id = self.sm.create_node(screen, NodeType.SCREEN)
            screen_ids.append(screen_id)
        
        return screen_ids
    
    def generate_errors(self, count: int = 10) -> List[str]:
        """Generate error nodes for testing error recovery."""
        error_ids = []
        
        error_categories = ['ui_not_found', 'timeout', 'permission_denied', 'network_error', 'validation_error']
        severities = ['low', 'medium', 'high', 'critical']
        
        for i in range(count):
            error = ErrorNode(
                category=random.choice(error_categories),
                message=f"Test error {i + 1}: {random.choice(error_categories)} occurred",
                severity=random.choice(severities),
                frequency=random.randint(1, 10),
                resolved=random.choice([True, True, False]),  # Mostly resolved
                resolution_strategy=random.choice(['retry', 'alternative_path', 'user_intervention', 'skip'])
            )
            
            error_id = self.sm.create_node(error, NodeType.ERROR)
            error_ids.append(error_id)
        
        return error_ids
    
    def generate_relationships(self, all_node_ids: Dict[str, List[str]], 
                             relationship_count: int = 50) -> int:
        """Generate additional relationships between nodes."""
        created_count = 0
        
        # Flatten all node IDs
        all_nodes = []
        for node_list in all_node_ids.values():
            all_nodes.extend(node_list)
        
        if len(all_nodes) < 2:
            return created_count
        
        relationship_types = [RelationshipType.TRIGGERS, RelationshipType.NAVIGATES_TO, 
                            RelationshipType.PRECEDES, RelationshipType.SIMILAR_TO]
        
        for _ in range(relationship_count):
            # Pick two random nodes
            from_node = random.choice(all_nodes)
            to_node = random.choice(all_nodes)
            
            if from_node == to_node:
                continue
            
            rel = self.schema.create_relationship(
                from_node=from_node,
                to_node=to_node,
                rel_type=random.choice(relationship_types),
                weight=random.uniform(0.3, 1.0),
                confidence=random.uniform(0.6, 0.9)
            )
            
            if self.sm.create_relationship(rel):
                created_count += 1
        
        return created_count
    
    def generate_complete_test_dataset(self) -> Dict[str, Any]:
        """Generate a complete test dataset."""
        print("🏗️ Generating complete test dataset...")
        
        # Generate all node types
        ui_element_ids = self.generate_ui_elements(50)
        print(f"✅ Generated {len(ui_element_ids)} UI elements")
        
        app_ids = self.generate_applications(7)
        print(f"✅ Generated {len(app_ids)} applications")
        
        community_ids = self.generate_communities(ui_element_ids, 15)
        print(f"✅ Generated {len(community_ids)} communities")
        
        workflow_ids = self.generate_workflows(community_ids, 10)
        print(f"✅ Generated {len(workflow_ids)} workflows")
        
        pattern_ids = self.generate_patterns(20)
        print(f"✅ Generated {len(pattern_ids)} patterns")
        
        screen_ids = self.generate_screen_captures(5)
        print(f"✅ Generated {len(screen_ids)} screen captures")
        
        error_ids = self.generate_errors(10)
        print(f"✅ Generated {len(error_ids)} error records")
        
        # Generate additional relationships
        all_node_ids = {
            'ui_elements': ui_element_ids,
            'applications': app_ids,
            'communities': community_ids,
            'workflows': workflow_ids,
            'patterns': pattern_ids,
            'screens': screen_ids,
            'errors': error_ids
        }
        
        rel_count = self.generate_relationships(all_node_ids, 50)
        print(f"✅ Generated {rel_count} additional relationships")
        
        # Validate the generated data
        validation = self.sm.validate_schema_consistency()
        print(f"✅ Schema validation: {'PASSED' if validation['consistent'] else 'ISSUES FOUND'}")
        
        if validation['issues']:
            print(f"⚠️ Issues found: {validation['issues']}")
        
        # Generate summary statistics
        stats = validation['statistics']
        total_nodes = sum(stats.get('nodes', {}).values())
        total_rels = sum(stats.get('relationships', {}).values())
        
        dataset_info = {
            'total_nodes': total_nodes,
            'total_relationships': total_rels,
            'node_types': stats.get('nodes', {}),
            'relationship_types': stats.get('relationships', {}),
            'validation_passed': validation['consistent'],
            'generation_timestamp': time.time()
        }
        
        print(f"🎯 Dataset complete: {total_nodes} nodes, {total_rels} relationships")
        return dataset_info


# Test the data generator
if __name__ == "__main__":
    print("🧪 Testing Test Data Generator...")
    
    with SchemaManager() as sm:
        generator = TestDataGenerator(sm)
        
        # Generate complete test dataset
        dataset_info = generator.generate_complete_test_dataset()
        
        print(f"✅ Test dataset generated successfully!")
        print(f"   - Nodes: {dataset_info['total_nodes']}")
        print(f"   - Relationships: {dataset_info['total_relationships']}")
        print(f"   - Validation: {'PASSED' if dataset_info['validation_passed'] else 'FAILED'}")
    
    print("✅ Test Data Generator testing completed!")