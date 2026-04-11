"""
Data Ingestion Pipeline for Kenny Graph Intelligence System

Converts Kenny's existing data (OCR results, UI elements, workflows) into graph nodes and edges.
"""

import hashlib
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json

from .schema import (
    NodeType, RelationshipType, KnowledgeGraphSchema,
    create_ui_element, create_community, create_workflow,
    UIElementNode, WorkflowNode, CommunityNode, ApplicationNode, ScreenNode
)
from .schema_manager import SchemaManager

logger = logging.getLogger(__name__)


@dataclass
class OCRElement:
    """Represents an OCR-detected element."""
    text: str
    bbox: List[int]  # [x, y, width, height] or [x1, y1, x2, y2]
    confidence: float
    element_type: str = "unknown"


@dataclass
class IngestionResult:
    """Result of data ingestion operation."""
    nodes_created: int = 0
    relationships_created: int = 0
    nodes_updated: int = 0
    errors: List[str] = None
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class UIElementClassifier:
    """Classifies UI elements based on OCR data and context."""
    
    def __init__(self):
        self.button_keywords = ['save', 'cancel', 'ok', 'apply', 'close', 'open', 'new', 'delete', 'edit', 'send', 'submit']
        self.menu_keywords = ['file', 'edit', 'view', 'tools', 'help', 'settings', 'options', 'window']
        self.field_keywords = ['username', 'password', 'email', 'search', 'filename', 'name', 'address']
        
    def classify_element(self, ocr_element: OCRElement, context: Dict[str, Any] = None) -> str:
        """Classify UI element type based on OCR data."""
        text = ocr_element.text.lower().strip()
        bbox = ocr_element.bbox
        
        # Calculate dimensions
        if len(bbox) == 4:
            width = bbox[2] - bbox[0] if bbox[2] > bbox[0] else bbox[2]
            height = bbox[3] - bbox[1] if bbox[3] > bbox[1] else bbox[3]
        else:
            width = bbox[2] if len(bbox) > 2 else 100
            height = bbox[3] if len(bbox) > 3 else 30
        
        # Classification logic
        if any(keyword in text for keyword in self.button_keywords):
            return 'button'
        
        if any(keyword in text for keyword in self.menu_keywords):
            return 'menu'
        
        if any(keyword in text for keyword in self.field_keywords):
            return 'text_field'
        
        # Size-based classification
        if width > 200 and height < 50:
            return 'text_field'
        elif width < 100 and height < 40:
            return 'button'
        elif len(text) > 20:
            return 'label'
        elif text.endswith(':'):
            return 'label'
        elif text.isupper() and len(text) < 10:
            return 'button'
        elif '/' in text or '\\' in text:
            return 'path'
        
        return 'label'


class RelationshipDetector:
    """Detects relationships between UI elements."""
    
    def __init__(self):
        self.proximity_threshold = 50  # pixels
        self.containment_threshold = 10  # pixels for container detection
        
    def detect_relationships(self, elements: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
        """Detect relationships between UI elements."""
        relationships = []
        
        for i, elem1 in enumerate(elements):
            for elem2 in elements[i+1:]:
                rel_type = self._detect_relationship_type(elem1, elem2)
                if rel_type:
                    relationships.append((elem1['id'], elem2['id'], rel_type))
        
        return relationships
    
    def _detect_relationship_type(self, elem1: Dict[str, Any], elem2: Dict[str, Any]) -> Optional[str]:
        """Detect specific relationship type between two elements."""
        coords1 = elem1.get('coordinates', [])
        coords2 = elem2.get('coordinates', [])
        
        if len(coords1) < 2 or len(coords2) < 2:
            return None
        
        # Check containment
        if self._is_contained(coords1, coords2):
            return RelationshipType.CONTAINS.value
        elif self._is_contained(coords2, coords1):
            return RelationshipType.CONTAINS.value
        
        # Check proximity for triggers
        if self._is_adjacent(coords1, coords2):
            type1 = elem1.get('type', '')
            type2 = elem2.get('type', '')
            
            if type1 == 'button' and type2 == 'dialog':
                return RelationshipType.TRIGGERS.value
            elif type1 == 'menu' and type2 == 'button':
                return RelationshipType.CONTAINS.value
        
        # Check sequential arrangement
        if self._is_sequential(coords1, coords2):
            return RelationshipType.PRECEDES.value
        
        return None
    
    def _is_contained(self, inner_coords: List[int], outer_coords: List[int]) -> bool:
        """Check if inner element is contained within outer element."""
        if len(inner_coords) < 2 or len(outer_coords) < 2:
            return False
        
        # Simple containment check
        return (outer_coords[0] - self.containment_threshold <= inner_coords[0] and
                outer_coords[1] - self.containment_threshold <= inner_coords[1])
    
    def _is_adjacent(self, coords1: List[int], coords2: List[int]) -> bool:
        """Check if elements are adjacent (close to each other)."""
        if len(coords1) < 2 or len(coords2) < 2:
            return False
        
        distance = ((coords1[0] - coords2[0]) ** 2 + (coords1[1] - coords2[1]) ** 2) ** 0.5
        return distance <= self.proximity_threshold
    
    def _is_sequential(self, coords1: List[int], coords2: List[int]) -> bool:
        """Check if elements are in sequential arrangement."""
        if len(coords1) < 2 or len(coords2) < 2:
            return False
        
        # Check if elements are horizontally or vertically aligned
        horizontal_aligned = abs(coords1[1] - coords2[1]) < 20
        vertical_aligned = abs(coords1[0] - coords2[0]) < 20
        
        return horizontal_aligned or vertical_aligned


class DataIngestionPipeline:
    """Main data ingestion pipeline."""
    
    def __init__(self, schema_manager: SchemaManager):
        self.sm = schema_manager
        self.classifier = UIElementClassifier()
        self.relationship_detector = RelationshipDetector()
        self.schema = KnowledgeGraphSchema()
        
    def ingest_ocr_results(self, ocr_data: List[Dict[str, Any]], 
                          context: Dict[str, Any] = None) -> IngestionResult:
        """Convert OCR results to graph nodes."""
        start_time = time.time()
        result = IngestionResult()
        
        if context is None:
            context = {}
        
        try:
            # Create screen node for this OCR session
            screen_id = self._create_screen_node(ocr_data, context)
            
            # Process OCR elements
            element_nodes = []
            for ocr_element in ocr_data:
                try:
                    element_node = self._process_ocr_element(ocr_element, context, screen_id)
                    if element_node:
                        element_nodes.append(element_node)
                        result.nodes_created += 1
                except Exception as e:
                    logger.error(f"Failed to process OCR element: {e}")
                    result.errors.append(f"OCR element processing error: {e}")
            
            # Detect and create relationships
            if len(element_nodes) > 1:
                relationships = self.relationship_detector.detect_relationships(element_nodes)
                for from_id, to_id, rel_type in relationships:
                    try:
                        rel = self.schema.create_relationship(
                            from_node=from_id,
                            to_node=to_id,
                            rel_type=RelationshipType(rel_type),
                            weight=1.0,
                            confidence=0.8
                        )
                        if self.sm.create_relationship(rel):
                            result.relationships_created += 1
                    except Exception as e:
                        logger.error(f"Failed to create relationship: {e}")
                        result.errors.append(f"Relationship creation error: {e}")
            
            # Link elements to screen
            for element in element_nodes:
                try:
                    rel = self.schema.create_relationship(
                        from_node=screen_id,
                        to_node=element['id'],
                        rel_type=RelationshipType.CONTAINS,
                        weight=1.0
                    )
                    self.sm.create_relationship(rel)
                    result.relationships_created += 1
                except Exception as e:
                    logger.error(f"Failed to link element to screen: {e}")
            
            result.processing_time = time.time() - start_time
            logger.info(f"✅ OCR ingestion completed: {result.nodes_created} nodes, "
                       f"{result.relationships_created} relationships in {result.processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ OCR ingestion failed: {e}")
            result.errors.append(f"General ingestion error: {e}")
        
        return result
    
    def _create_screen_node(self, ocr_data: List[Dict[str, Any]], 
                           context: Dict[str, Any]) -> str:
        """Create a screen node for the OCR session."""
        # Generate screen hash from OCR data
        ocr_text = " ".join([elem.get('text', '') for elem in ocr_data])
        screen_hash = hashlib.md5(ocr_text.encode()).hexdigest()
        
        screen = ScreenNode(
            resolution=context.get('resolution', [1920, 1080]),
            screenshot_path=context.get('screenshot_path', ''),
            screenshot_hash=screen_hash,
            active_window=context.get('active_window', ''),
            ui_elements_count=len(ocr_data),
            processing_time=context.get('processing_time', 0.0),
            ocr_confidence=context.get('ocr_confidence', 0.9)
        )
        
        return self.sm.create_node(screen, NodeType.SCREEN)
    
    def _process_ocr_element(self, ocr_data: Dict[str, Any], 
                            context: Dict[str, Any], screen_id: str) -> Optional[Dict[str, Any]]:
        """Process a single OCR element."""
        try:
            # Extract OCR data
            text = ocr_data.get('text', '').strip()
            bbox = ocr_data.get('bbox', ocr_data.get('coordinates', []))
            confidence = ocr_data.get('confidence', 0.9)
            
            if not text or len(bbox) < 2:
                return None
            
            # Create OCR element object for classification
            ocr_element = OCRElement(
                text=text,
                bbox=bbox,
                confidence=confidence
            )
            
            # Classify element type
            element_type = self.classifier.classify_element(ocr_element, context)
            
            # Create UI element node
            ui_element = create_ui_element(
                element_type=element_type,
                text=text,
                coordinates=bbox[:2],  # Take x, y coordinates
                confidence=confidence,
                application=context.get('application', 'unknown'),
                screen_id=screen_id,
                properties={
                    'bbox': bbox,
                    'processing_method': 'ocr',
                    'timestamp': time.time()
                }
            )
            
            # Create node in database
            element_id = self.sm.create_node(ui_element, NodeType.UI_ELEMENT)
            
            return {
                'id': element_id,
                'type': element_type,
                'text': text,
                'coordinates': bbox[:2],
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"Failed to process OCR element {ocr_data}: {e}")
            return None
    
    def ingest_workflow_data(self, workflow_data: Dict[str, Any]) -> IngestionResult:
        """Convert workflow data to graph nodes."""
        start_time = time.time()
        result = IngestionResult()
        
        try:
            # Create workflow node
            workflow = create_workflow(
                name=workflow_data.get('name', 'Unnamed Workflow'),
                description=workflow_data.get('description', ''),
                steps=workflow_data.get('steps', []),
                status=workflow_data.get('status', 'pending'),
                success_rate=workflow_data.get('success_rate', 0.0),
                avg_duration=workflow_data.get('avg_duration', 0.0),
                execution_count=workflow_data.get('execution_count', 0),
                complexity=workflow_data.get('complexity', 'simple')
            )
            
            workflow_id = self.sm.create_node(workflow, NodeType.WORKFLOW)
            result.nodes_created += 1
            
            # Create relationships to related UI elements
            related_elements = workflow_data.get('related_elements', [])
            for element_id in related_elements:
                try:
                    rel = self.schema.create_relationship(
                        from_node=workflow_id,
                        to_node=element_id,
                        rel_type=RelationshipType.REQUIRES,
                        weight=1.0
                    )
                    if self.sm.create_relationship(rel):
                        result.relationships_created += 1
                except Exception as e:
                    logger.error(f"Failed to create workflow relationship: {e}")
                    result.errors.append(f"Workflow relationship error: {e}")
            
            result.processing_time = time.time() - start_time
            logger.info(f"✅ Workflow ingestion completed: {workflow_data['name']}")
            
        except Exception as e:
            logger.error(f"❌ Workflow ingestion failed: {e}")
            result.errors.append(f"Workflow ingestion error: {e}")
        
        return result
    
    def ingest_application_data(self, app_data: Dict[str, Any]) -> IngestionResult:
        """Convert application data to graph nodes."""
        start_time = time.time()
        result = IngestionResult()
        
        try:
            app = ApplicationNode(
                name=app_data.get('name', 'Unknown'),
                version=app_data.get('version', '1.0'),
                process_id=app_data.get('process_id', 0),
                window_title=app_data.get('window_title', ''),
                executable_path=app_data.get('executable_path', ''),
                ui_framework=app_data.get('ui_framework', 'unknown'),
                automation_confidence=app_data.get('automation_confidence', 0.7),
                last_active=app_data.get('last_active', time.time())
            )
            
            app_id = self.sm.create_node(app, NodeType.APPLICATION)
            result.nodes_created += 1
            
            result.processing_time = time.time() - start_time
            logger.info(f"✅ Application ingestion completed: {app_data['name']}")
            
        except Exception as e:
            logger.error(f"❌ Application ingestion failed: {e}")
            result.errors.append(f"Application ingestion error: {e}")
        
        return result
    
    def batch_ingest(self, data_batch: List[Dict[str, Any]], 
                    batch_type: str = "mixed") -> IngestionResult:
        """Process multiple data items in a batch."""
        start_time = time.time()
        total_result = IngestionResult()
        
        logger.info(f"🔄 Starting batch ingestion: {len(data_batch)} items of type {batch_type}")
        
        for i, data_item in enumerate(data_batch):
            try:
                if batch_type == "ocr" or data_item.get('type') == 'ocr':
                    result = self.ingest_ocr_results(
                        data_item.get('ocr_data', []),
                        data_item.get('context', {})
                    )
                elif batch_type == "workflow" or data_item.get('type') == 'workflow':
                    result = self.ingest_workflow_data(data_item)
                elif batch_type == "application" or data_item.get('type') == 'application':
                    result = self.ingest_application_data(data_item)
                else:
                    logger.warning(f"Unknown data type for item {i}: {data_item.get('type')}")
                    continue
                
                # Aggregate results
                total_result.nodes_created += result.nodes_created
                total_result.relationships_created += result.relationships_created
                total_result.nodes_updated += result.nodes_updated
                total_result.errors.extend(result.errors)
                
            except Exception as e:
                logger.error(f"Failed to process batch item {i}: {e}")
                total_result.errors.append(f"Batch item {i} error: {e}")
        
        total_result.processing_time = time.time() - start_time
        
        logger.info(f"✅ Batch ingestion completed: {total_result.nodes_created} nodes, "
                   f"{total_result.relationships_created} relationships, "
                   f"{len(total_result.errors)} errors in {total_result.processing_time:.2f}s")
        
        return total_result
    
    def validate_ingestion(self) -> Dict[str, Any]:
        """Validate the ingested data."""
        validation_result = self.sm.validate_schema_consistency()
        
        # Add ingestion-specific validations
        try:
            # Check for orphaned nodes
            orphaned_ui_elements = len(self.sm.find_nodes(
                NodeType.UI_ELEMENT, 
                filters={'screen_id': ''}
            ))
            
            if orphaned_ui_elements > 0:
                validation_result['issues'].append(
                    f"{orphaned_ui_elements} UI elements not linked to screens"
                )
            
            # Check for duplicate elements
            # This would require more complex queries
            
        except Exception as e:
            validation_result['issues'].append(f"Validation error: {e}")
        
        return validation_result


# Test the ingestion pipeline
if __name__ == "__main__":
    print("🧪 Testing Data Ingestion Pipeline...")
    
    from .schema_manager import SchemaManager
    
    with SchemaManager() as sm:
        pipeline = DataIngestionPipeline(sm)
        
        # Test OCR ingestion
        sample_ocr_data = [
            {'text': 'Save', 'bbox': [150, 200, 200, 230], 'confidence': 0.95},
            {'text': 'Cancel', 'bbox': [220, 200, 270, 230], 'confidence': 0.93},
            {'text': 'File', 'bbox': [50, 180, 80, 200], 'confidence': 0.98}
        ]
        
        context = {
            'application': 'test_app',
            'resolution': [1920, 1080],
            'screenshot_path': '/test/screenshot.png'
        }
        
        result = pipeline.ingest_ocr_results(sample_ocr_data, context)
        print(f"✅ OCR ingestion: {result.nodes_created} nodes, {result.relationships_created} relationships")
        
        # Test workflow ingestion
        sample_workflow = {
            'name': 'Test Save Workflow',
            'description': 'Test workflow for saving documents',
            'steps': [
                {'action': 'click', 'target': 'file_menu'},
                {'action': 'click', 'target': 'save_option'},
                {'action': 'type', 'target': 'filename_field', 'text': 'test.txt'}
            ],
            'status': 'completed',
            'success_rate': 0.95
        }
        
        workflow_result = pipeline.ingest_workflow_data(sample_workflow)
        print(f"✅ Workflow ingestion: {workflow_result.nodes_created} nodes")
        
        # Validate ingestion
        validation = pipeline.validate_ingestion()
        print(f"✅ Validation: {'PASSED' if validation['consistent'] else 'ISSUES FOUND'}")
        
        if validation['issues']:
            print(f"   Issues: {validation['issues']}")
    
    print("✅ Data Ingestion Pipeline testing completed!")