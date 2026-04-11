"""
Multi-Modal Communication Layer
===============================

Advanced multi-modal communication system supporting text, logic,
embeddings, graphs, images, audio, and other data modalities
for comprehensive AGI-to-AGI information exchange.
"""

import asyncio
import json
import base64
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import uuid
import hashlib
from io import BytesIO

from .core import CommunicationMessage, MessageType

logger = logging.getLogger(__name__)

class DataModality(Enum):
    """Types of data modalities."""
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"
    GRAPH = "graph"
    EMBEDDING = "embedding"
    LOGIC = "logic"
    SYMBOLIC = "symbolic"
    NUMERICAL = "numerical"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    MULTIMODAL = "multimodal"

class EncodingFormat(Enum):
    """Data encoding formats."""
    JSON = "json"
    XML = "xml"
    BINARY = "binary"
    BASE64 = "base64"
    PROTOBUF = "protobuf"
    MSGPACK = "msgpack"
    NUMPY = "numpy"
    TENSOR = "tensor"
    GRAPH_JSON = "graph_json"
    RDF = "rdf"
    WAV = "wav"
    MP3 = "mp3"
    PNG = "png"
    JPEG = "jpeg"
    MP4 = "mp4"

class CompressionType(Enum):
    """Compression types for data."""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    ZLIB = "zlib"
    BROTLI = "brotli"

@dataclass
class ModalityMetadata:
    """Metadata for a data modality."""
    modality: DataModality
    format: EncodingFormat
    compression: CompressionType = CompressionType.NONE
    quality: float = 1.0  # Quality score 0-1
    size_bytes: int = 0
    checksum: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    processing_hints: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MultiModalData:
    """Container for multi-modal data."""
    id: str
    primary_modality: DataModality
    data: Any
    metadata: ModalityMetadata
    auxiliary_data: Dict[str, Tuple[Any, ModalityMetadata]] = field(default_factory=dict)
    relationships: List[Dict[str, Any]] = field(default_factory=list)  # Cross-modal relationships
    temporal_info: Optional[Dict[str, Any]] = None
    spatial_info: Optional[Dict[str, Any]] = None
    
    def add_auxiliary_modality(self, modality: DataModality, data: Any, metadata: ModalityMetadata):
        """Add auxiliary data modality."""
        self.auxiliary_data[modality.value] = (data, metadata)
    
    def get_total_size(self) -> int:
        """Get total size of all modalities."""
        total_size = self.metadata.size_bytes
        for _, (_, metadata) in self.auxiliary_data.items():
            total_size += metadata.size_bytes
        return total_size
    
    def get_modalities(self) -> List[DataModality]:
        """Get all modalities present in this data."""
        modalities = [self.primary_modality]
        for modality_str in self.auxiliary_data.keys():
            modalities.append(DataModality(modality_str))
        return modalities

class ModalityProcessor:
    """Processes different data modalities."""
    
    def __init__(self):
        self.processors = {
            DataModality.TEXT: self._process_text,
            DataModality.EMBEDDING: self._process_embedding,
            DataModality.GRAPH: self._process_graph,
            DataModality.LOGIC: self._process_logic,
            DataModality.NUMERICAL: self._process_numerical,
            DataModality.IMAGE: self._process_image,
            DataModality.AUDIO: self._process_audio,
        }
    
    def process_data(self, data: Any, modality: DataModality, 
                    target_format: EncodingFormat) -> Tuple[Any, ModalityMetadata]:
        """Process data for specific modality and format."""
        if modality in self.processors:
            return self.processors[modality](data, target_format)
        else:
            return self._process_generic(data, modality, target_format)
    
    def _process_text(self, data: str, target_format: EncodingFormat) -> Tuple[Any, ModalityMetadata]:
        """Process text data."""
        if target_format == EncodingFormat.JSON:
            processed_data = {"text": data, "language": "en"}  # Simplified
            metadata = ModalityMetadata(
                modality=DataModality.TEXT,
                format=target_format,
                size_bytes=len(json.dumps(processed_data).encode()),
                checksum=hashlib.md5(data.encode()).hexdigest()
            )
        else:
            processed_data = data
            metadata = ModalityMetadata(
                modality=DataModality.TEXT,
                format=EncodingFormat.JSON,
                size_bytes=len(data.encode()),
                checksum=hashlib.md5(data.encode()).hexdigest()
            )
        
        return processed_data, metadata
    
    def _process_embedding(self, data: Union[List, np.ndarray], 
                         target_format: EncodingFormat) -> Tuple[Any, ModalityMetadata]:
        """Process embedding data."""
        if isinstance(data, np.ndarray):
            embedding_list = data.tolist()
        else:
            embedding_list = data
        
        if target_format == EncodingFormat.JSON:
            processed_data = {"embedding": embedding_list, "dimension": len(embedding_list)}
        elif target_format == EncodingFormat.NUMPY:
            processed_data = np.array(embedding_list)
        else:
            processed_data = embedding_list
        
        size_bytes = len(json.dumps(embedding_list).encode())
        checksum = hashlib.md5(str(embedding_list).encode()).hexdigest()
        
        metadata = ModalityMetadata(
            modality=DataModality.EMBEDDING,
            format=target_format,
            size_bytes=size_bytes,
            checksum=checksum,
            processing_hints={"dimension": len(embedding_list)}
        )
        
        return processed_data, metadata
    
    def _process_graph(self, data: Dict[str, Any], 
                      target_format: EncodingFormat) -> Tuple[Any, ModalityMetadata]:
        """Process graph data."""
        if target_format == EncodingFormat.GRAPH_JSON:
            processed_data = {
                "nodes": data.get("nodes", []),
                "edges": data.get("edges", []),
                "metadata": data.get("metadata", {})
            }
        elif target_format == EncodingFormat.RDF:
            # Convert to RDF format (simplified)
            processed_data = self._convert_to_rdf(data)
        else:
            processed_data = data
        
        size_bytes = len(json.dumps(processed_data).encode())
        checksum = hashlib.md5(json.dumps(processed_data, sort_keys=True).encode()).hexdigest()
        
        metadata = ModalityMetadata(
            modality=DataModality.GRAPH,
            format=target_format,
            size_bytes=size_bytes,
            checksum=checksum,
            processing_hints={
                "node_count": len(data.get("nodes", [])),
                "edge_count": len(data.get("edges", []))
            }
        )
        
        return processed_data, metadata
    
    def _process_logic(self, data: Union[str, Dict], 
                      target_format: EncodingFormat) -> Tuple[Any, ModalityMetadata]:
        """Process logical expressions."""
        if isinstance(data, str):
            # Parse logical expression
            processed_data = {
                "expression": data,
                "type": "first_order_logic",
                "variables": self._extract_variables(data),
                "predicates": self._extract_predicates(data)
            }
        else:
            processed_data = data
        
        size_bytes = len(json.dumps(processed_data).encode())
        checksum = hashlib.md5(str(processed_data).encode()).hexdigest()
        
        metadata = ModalityMetadata(
            modality=DataModality.LOGIC,
            format=target_format,
            size_bytes=size_bytes,
            checksum=checksum
        )
        
        return processed_data, metadata
    
    def _process_numerical(self, data: Union[List, np.ndarray, Dict], 
                         target_format: EncodingFormat) -> Tuple[Any, ModalityMetadata]:
        """Process numerical data."""
        if isinstance(data, np.ndarray):
            processed_data = {
                "data": data.tolist(),
                "shape": data.shape,
                "dtype": str(data.dtype)
            }
        elif isinstance(data, list):
            processed_data = {
                "data": data,
                "shape": [len(data)],
                "dtype": "float64"
            }
        else:
            processed_data = data
        
        size_bytes = len(json.dumps(processed_data).encode())
        checksum = hashlib.md5(str(processed_data).encode()).hexdigest()
        
        metadata = ModalityMetadata(
            modality=DataModality.NUMERICAL,
            format=target_format,
            size_bytes=size_bytes,
            checksum=checksum,
            processing_hints={"shape": processed_data.get("shape", [])}
        )
        
        return processed_data, metadata
    
    def _process_image(self, data: Any, target_format: EncodingFormat) -> Tuple[Any, ModalityMetadata]:
        """Process image data."""
        # Simplified image processing
        if isinstance(data, bytes):
            # Encode as base64
            encoded_data = base64.b64encode(data).decode('utf-8')
            processed_data = {
                "image_data": encoded_data,
                "encoding": "base64",
                "format": "unknown"
            }
        elif isinstance(data, str):
            # Assume it's already base64 encoded
            processed_data = {
                "image_data": data,
                "encoding": "base64",
                "format": "unknown"
            }
        else:
            processed_data = {"error": "Unsupported image format"}
        
        size_bytes = len(str(processed_data).encode())
        checksum = hashlib.md5(str(processed_data).encode()).hexdigest()
        
        metadata = ModalityMetadata(
            modality=DataModality.IMAGE,
            format=target_format,
            size_bytes=size_bytes,
            checksum=checksum
        )
        
        return processed_data, metadata
    
    def _process_audio(self, data: Any, target_format: EncodingFormat) -> Tuple[Any, ModalityMetadata]:
        """Process audio data."""
        # Simplified audio processing
        if isinstance(data, bytes):
            encoded_data = base64.b64encode(data).decode('utf-8')
            processed_data = {
                "audio_data": encoded_data,
                "encoding": "base64",
                "format": "wav"  # Default
            }
        elif isinstance(data, list):
            # Assume it's raw audio samples
            processed_data = {
                "samples": data,
                "sample_rate": 44100,  # Default
                "channels": 1
            }
        else:
            processed_data = {"error": "Unsupported audio format"}
        
        size_bytes = len(str(processed_data).encode())
        checksum = hashlib.md5(str(processed_data).encode()).hexdigest()
        
        metadata = ModalityMetadata(
            modality=DataModality.AUDIO,
            format=target_format,
            size_bytes=size_bytes,
            checksum=checksum
        )
        
        return processed_data, metadata
    
    def _process_generic(self, data: Any, modality: DataModality, 
                        target_format: EncodingFormat) -> Tuple[Any, ModalityMetadata]:
        """Generic data processing."""
        processed_data = data
        size_bytes = len(str(data).encode())
        checksum = hashlib.md5(str(data).encode()).hexdigest()
        
        metadata = ModalityMetadata(
            modality=modality,
            format=target_format,
            size_bytes=size_bytes,
            checksum=checksum
        )
        
        return processed_data, metadata
    
    def _convert_to_rdf(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert graph to RDF format."""
        rdf_triples = []
        
        for node in graph_data.get("nodes", []):
            node_id = node.get("id", "")
            node_type = node.get("type", "Entity")
            
            rdf_triples.append({
                "subject": node_id,
                "predicate": "rdf:type",
                "object": node_type
            })
            
            for prop, value in node.get("properties", {}).items():
                rdf_triples.append({
                    "subject": node_id,
                    "predicate": prop,
                    "object": value
                })
        
        for edge in graph_data.get("edges", []):
            rdf_triples.append({
                "subject": edge.get("source", ""),
                "predicate": edge.get("type", "related_to"),
                "object": edge.get("target", "")
            })
        
        return {
            "@context": {"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"},
            "triples": rdf_triples
        }
    
    def _extract_variables(self, expression: str) -> List[str]:
        """Extract variables from logical expression."""
        import re
        variables = re.findall(r'\b[a-z][a-zA-Z0-9_]*\b', expression)
        return list(set(variables))
    
    def _extract_predicates(self, expression: str) -> List[str]:
        """Extract predicates from logical expression."""
        import re
        predicates = re.findall(r'\b[A-Z][a-zA-Z0-9_]*\b', expression)
        return list(set(predicates))

class CrossModalTranslator:
    """Translates between different modalities."""
    
    def __init__(self):
        self.translation_matrix = self._build_translation_matrix()
    
    def _build_translation_matrix(self) -> Dict[Tuple[DataModality, DataModality], Callable]:
        """Build matrix of cross-modal translation functions."""
        return {
            (DataModality.TEXT, DataModality.EMBEDDING): self._text_to_embedding,
            (DataModality.EMBEDDING, DataModality.TEXT): self._embedding_to_text,
            (DataModality.GRAPH, DataModality.TEXT): self._graph_to_text,
            (DataModality.TEXT, DataModality.GRAPH): self._text_to_graph,
            (DataModality.LOGIC, DataModality.TEXT): self._logic_to_text,
            (DataModality.TEXT, DataModality.LOGIC): self._text_to_logic,
            (DataModality.GRAPH, DataModality.LOGIC): self._graph_to_logic,
            (DataModality.LOGIC, DataModality.GRAPH): self._logic_to_graph,
        }
    
    def can_translate(self, from_modality: DataModality, to_modality: DataModality) -> bool:
        """Check if translation is possible between modalities."""
        return (from_modality, to_modality) in self.translation_matrix
    
    def translate(self, data: Any, from_modality: DataModality, 
                 to_modality: DataModality) -> Tuple[Any, float]:
        """Translate data between modalities. Returns (translated_data, confidence)."""
        if not self.can_translate(from_modality, to_modality):
            return None, 0.0
        
        translator = self.translation_matrix[(from_modality, to_modality)]
        return translator(data)
    
    def _text_to_embedding(self, text: str) -> Tuple[List[float], float]:
        """Convert text to embedding."""
        # Simplified text to embedding conversion
        # In practice, this would use sophisticated language models
        words = text.lower().split()
        # Create a simple hash-based embedding
        embedding = []
        for i in range(384):  # 384-dimensional embedding
            hash_input = f"{text}_{i}"
            hash_val = hash(hash_input) % 2000 - 1000
            embedding.append(hash_val / 1000.0)
        
        return embedding, 0.7  # Moderate confidence
    
    def _embedding_to_text(self, embedding: List[float]) -> Tuple[str, float]:
        """Convert embedding to text approximation."""
        # Very simplified embedding to text
        embedding_magnitude = np.linalg.norm(embedding)
        
        if embedding_magnitude > 0.8:
            description = "high-magnitude concept"
        elif embedding_magnitude > 0.5:
            description = "medium-magnitude concept"
        else:
            description = "low-magnitude concept"
        
        # Add some characteristics based on embedding values
        positive_dims = sum(1 for x in embedding if x > 0)
        negative_dims = sum(1 for x in embedding if x < 0)
        
        characteristics = f"with {positive_dims} positive and {negative_dims} negative dimensions"
        
        return f"{description} {characteristics}", 0.4  # Low confidence
    
    def _graph_to_text(self, graph_data: Dict[str, Any]) -> Tuple[str, float]:
        """Convert graph to text description."""
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        description = f"Graph with {len(nodes)} nodes and {len(edges)} edges. "
        
        if nodes:
            node_types = set(node.get("type", "unknown") for node in nodes)
            description += f"Node types: {', '.join(node_types)}. "
        
        if edges:
            edge_types = set(edge.get("type", "unknown") for edge in edges)
            description += f"Relationship types: {', '.join(edge_types)}."
        
        return description, 0.8  # Good confidence
    
    def _text_to_graph(self, text: str) -> Tuple[Dict[str, Any], float]:
        """Convert text to graph structure."""
        # Simplified text to graph conversion
        import re
        
        # Extract potential entities (capitalized words)
        entities = re.findall(r'\b[A-Z][a-z]+\b', text)
        
        nodes = []
        for i, entity in enumerate(set(entities)):
            nodes.append({
                "id": f"entity_{i}",
                "label": entity,
                "type": "Entity"
            })
        
        # Create edges between consecutive entities
        edges = []
        unique_entities = list(set(entities))
        for i in range(len(unique_entities) - 1):
            edges.append({
                "source": f"entity_{i}",
                "target": f"entity_{i+1}",
                "type": "related_to"
            })
        
        graph_data = {
            "nodes": nodes,
            "edges": edges,
            "metadata": {"source": "text_conversion"}
        }
        
        return graph_data, 0.6  # Moderate confidence
    
    def _logic_to_text(self, logic_data: Union[str, Dict]) -> Tuple[str, float]:
        """Convert logical expressions to text."""
        if isinstance(logic_data, str):
            # Convert logical operators to natural language
            text = logic_data
            text = text.replace("&", " and ")
            text = text.replace("|", " or ")
            text = text.replace("->", " implies ")
            text = text.replace("~", " not ")
            return text, 0.9
        elif isinstance(logic_data, dict):
            expression = logic_data.get("expression", "")
            return self._logic_to_text(expression)
        else:
            return str(logic_data), 0.5
    
    def _text_to_logic(self, text: str) -> Tuple[str, float]:
        """Convert text to logical expressions."""
        # Simplified text to logic conversion
        logic_text = text.lower()
        logic_text = logic_text.replace(" and ", " & ")
        logic_text = logic_text.replace(" or ", " | ")
        logic_text = logic_text.replace(" not ", " ~ ")
        logic_text = logic_text.replace(" implies ", " -> ")
        
        return logic_text, 0.6  # Moderate confidence
    
    def _graph_to_logic(self, graph_data: Dict[str, Any]) -> Tuple[str, float]:
        """Convert graph to logical expressions."""
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        logic_statements = []
        
        # Convert nodes to type assertions
        for node in nodes:
            node_id = node.get("id", "")
            node_type = node.get("type", "Entity")
            logic_statements.append(f"{node_type}({node_id})")
        
        # Convert edges to relations
        for edge in edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            relation = edge.get("type", "related")
            logic_statements.append(f"{relation}({source}, {target})")
        
        logic_expression = " & ".join(logic_statements)
        return logic_expression, 0.8
    
    def _logic_to_graph(self, logic_data: Union[str, Dict]) -> Tuple[Dict[str, Any], float]:
        """Convert logical expressions to graph."""
        import re
        
        if isinstance(logic_data, dict):
            expression = logic_data.get("expression", "")
        else:
            expression = str(logic_data)
        
        # Extract predicates and arguments
        predicates = re.findall(r'(\w+)\(([^)]+)\)', expression)
        
        nodes = set()
        edges = []
        
        for predicate, args in predicates:
            arg_list = [arg.strip() for arg in args.split(',')]
            
            if len(arg_list) == 1:
                # Unary predicate - represents node type
                nodes.add(arg_list[0])
            elif len(arg_list) == 2:
                # Binary predicate - represents edge
                source, target = arg_list
                nodes.add(source)
                nodes.add(target)
                edges.append({
                    "source": source,
                    "target": target,
                    "type": predicate
                })
        
        graph_nodes = [
            {"id": node, "label": node, "type": "Entity"}
            for node in nodes
        ]
        
        graph_data = {
            "nodes": graph_nodes,
            "edges": edges,
            "metadata": {"source": "logic_conversion"}
        }
        
        return graph_data, 0.7

class MultiModalCommunicator:
    """
    Multi-Modal Communication Layer
    
    Handles communication using multiple data modalities including
    text, audio, images, graphs, embeddings, and logical expressions.
    """
    
    def __init__(self, protocol):
        self.protocol = protocol
        self.processor = ModalityProcessor()
        self.translator = CrossModalTranslator()
        self.supported_modalities = [
            DataModality.TEXT,
            DataModality.EMBEDDING,
            DataModality.GRAPH,
            DataModality.LOGIC,
            DataModality.NUMERICAL,
            DataModality.IMAGE,
            DataModality.AUDIO
        ]
        self.communication_history: List[Dict[str, Any]] = []
    
    async def send_multimodal_data(self, recipient_id: str, data: MultiModalData, 
                                  session_id: Optional[str] = None) -> bool:
        """Send multi-modal data to another AGI."""
        try:
            # Prepare data for transmission
            serialized_data = await self._serialize_multimodal_data(data)
            
            # Create message
            message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=recipient_id,
                message_type=MessageType.MULTIMODAL_DATA,
                timestamp=datetime.now(),
                payload={
                    'data_id': data.id,
                    'primary_modality': data.primary_modality.value,
                    'serialized_data': serialized_data,
                    'total_size': data.get_total_size(),
                    'modalities': [m.value for m in data.get_modalities()]
                },
                session_id=session_id
            )
            
            # Send message
            await self.protocol.send_message(message)
            
            # Record communication
            self._record_communication(data, recipient_id, "sent")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending multimodal data: {e}")
            return False
    
    async def create_multimodal_data(self, primary_data: Any, primary_modality: DataModality,
                                   target_format: EncodingFormat = EncodingFormat.JSON) -> MultiModalData:
        """Create multi-modal data container."""
        data_id = str(uuid.uuid4())
        
        # Process primary data
        processed_data, metadata = self.processor.process_data(
            primary_data, primary_modality, target_format
        )
        
        multimodal_data = MultiModalData(
            id=data_id,
            primary_modality=primary_modality,
            data=processed_data,
            metadata=metadata
        )
        
        return multimodal_data
    
    async def add_auxiliary_modality(self, multimodal_data: MultiModalData, 
                                   auxiliary_data: Any, modality: DataModality,
                                   target_format: EncodingFormat = EncodingFormat.JSON):
        """Add auxiliary data modality to existing multimodal data."""
        processed_data, metadata = self.processor.process_data(
            auxiliary_data, modality, target_format
        )
        
        multimodal_data.add_auxiliary_modality(modality, processed_data, metadata)
    
    async def translate_modality(self, data: Any, from_modality: DataModality, 
                               to_modality: DataModality) -> Tuple[Any, float]:
        """Translate data between modalities."""
        return self.translator.translate(data, from_modality, to_modality)
    
    async def enhance_with_cross_modal_data(self, multimodal_data: MultiModalData):
        """Enhance multimodal data by generating cross-modal representations."""
        primary_modality = multimodal_data.primary_modality
        primary_data = multimodal_data.data
        
        # Generate complementary modalities
        for target_modality in self.supported_modalities:
            if (target_modality != primary_modality and 
                self.translator.can_translate(primary_modality, target_modality)):
                
                translated_data, confidence = await self.translate_modality(
                    primary_data, primary_modality, target_modality
                )
                
                if confidence > 0.5:  # Only add if reasonably confident
                    processed_data, metadata = self.processor.process_data(
                        translated_data, target_modality, EncodingFormat.JSON
                    )
                    
                    # Add translation confidence to metadata
                    metadata.processing_hints['translation_confidence'] = confidence
                    metadata.processing_hints['translated_from'] = primary_modality.value
                    
                    multimodal_data.add_auxiliary_modality(target_modality, processed_data, metadata)
    
    async def _serialize_multimodal_data(self, data: MultiModalData) -> Dict[str, Any]:
        """Serialize multi-modal data for transmission."""
        serialized = {
            'id': data.id,
            'primary_modality': data.primary_modality.value,
            'primary_data': data.data,
            'primary_metadata': {
                'modality': data.metadata.modality.value,
                'format': data.metadata.format.value,
                'compression': data.metadata.compression.value,
                'quality': data.metadata.quality,
                'size_bytes': data.metadata.size_bytes,
                'checksum': data.metadata.checksum,
                'created_at': data.metadata.created_at.isoformat(),
                'processing_hints': data.metadata.processing_hints
            },
            'auxiliary_data': {},
            'relationships': data.relationships,
            'temporal_info': data.temporal_info,
            'spatial_info': data.spatial_info
        }
        
        # Serialize auxiliary data
        for modality_str, (aux_data, aux_metadata) in data.auxiliary_data.items():
            serialized['auxiliary_data'][modality_str] = {
                'data': aux_data,
                'metadata': {
                    'modality': aux_metadata.modality.value,
                    'format': aux_metadata.format.value,
                    'compression': aux_metadata.compression.value,
                    'quality': aux_metadata.quality,
                    'size_bytes': aux_metadata.size_bytes,
                    'checksum': aux_metadata.checksum,
                    'created_at': aux_metadata.created_at.isoformat(),
                    'processing_hints': aux_metadata.processing_hints
                }
            }
        
        return serialized
    
    async def _deserialize_multimodal_data(self, serialized_data: Dict[str, Any]) -> MultiModalData:
        """Deserialize multi-modal data from transmission."""
        # Reconstruct primary metadata
        primary_meta_data = serialized_data['primary_metadata']
        primary_metadata = ModalityMetadata(
            modality=DataModality(primary_meta_data['modality']),
            format=EncodingFormat(primary_meta_data['format']),
            compression=CompressionType(primary_meta_data['compression']),
            quality=primary_meta_data['quality'],
            size_bytes=primary_meta_data['size_bytes'],
            checksum=primary_meta_data['checksum'],
            created_at=datetime.fromisoformat(primary_meta_data['created_at']),
            processing_hints=primary_meta_data['processing_hints']
        )
        
        # Create multimodal data object
        multimodal_data = MultiModalData(
            id=serialized_data['id'],
            primary_modality=DataModality(serialized_data['primary_modality']),
            data=serialized_data['primary_data'],
            metadata=primary_metadata,
            relationships=serialized_data.get('relationships', []),
            temporal_info=serialized_data.get('temporal_info'),
            spatial_info=serialized_data.get('spatial_info')
        )
        
        # Reconstruct auxiliary data
        for modality_str, aux_info in serialized_data.get('auxiliary_data', {}).items():
            aux_meta_data = aux_info['metadata']
            aux_metadata = ModalityMetadata(
                modality=DataModality(aux_meta_data['modality']),
                format=EncodingFormat(aux_meta_data['format']),
                compression=CompressionType(aux_meta_data['compression']),
                quality=aux_meta_data['quality'],
                size_bytes=aux_meta_data['size_bytes'],
                checksum=aux_meta_data['checksum'],
                created_at=datetime.fromisoformat(aux_meta_data['created_at']),
                processing_hints=aux_meta_data['processing_hints']
            )
            
            multimodal_data.add_auxiliary_modality(
                DataModality(modality_str),
                aux_info['data'],
                aux_metadata
            )
        
        return multimodal_data
    
    def _record_communication(self, data: MultiModalData, recipient_id: str, direction: str):
        """Record multimodal communication for analysis."""
        communication_record = {
            'timestamp': datetime.now().isoformat(),
            'data_id': data.id,
            'recipient_id': recipient_id,
            'direction': direction,
            'primary_modality': data.primary_modality.value,
            'auxiliary_modalities': list(data.auxiliary_data.keys()),
            'total_size': data.get_total_size(),
            'modality_count': len(data.get_modalities())
        }
        
        self.communication_history.append(communication_record)
    
    async def handle_multimodal_data(self, message: CommunicationMessage):
        """Handle incoming multimodal data from another AGI."""
        payload = message.payload
        
        try:
            # Deserialize multimodal data
            serialized_data = payload['serialized_data']
            multimodal_data = await self._deserialize_multimodal_data(serialized_data)
            
            # Record communication
            self._record_communication(multimodal_data, message.sender_id, "received")
            
            # Process received data (application-specific logic would go here)
            logger.info(f"Received multimodal data {multimodal_data.id} from {message.sender_id}")
            logger.info(f"Primary modality: {multimodal_data.primary_modality.value}")
            logger.info(f"Total modalities: {len(multimodal_data.get_modalities())}")
            
            # Send acknowledgment
            ack_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=message.sender_id,
                message_type=MessageType.MULTIMODAL_DATA,
                timestamp=datetime.now(),
                payload={
                    'action': 'acknowledgment',
                    'original_data_id': multimodal_data.id,
                    'received_modalities': [m.value for m in multimodal_data.get_modalities()],
                    'status': 'processed'
                }
            )
            
            await self.protocol.send_message(ack_message)
            
        except Exception as e:
            logger.error(f"Error handling multimodal data: {e}")
            
            # Send error response
            error_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=message.sender_id,
                message_type=MessageType.MULTIMODAL_DATA,
                timestamp=datetime.now(),
                payload={
                    'action': 'error',
                    'error': str(e),
                    'original_message_id': message.id
                }
            )
            
            await self.protocol.send_message(error_message)
    
    def get_supported_modalities(self) -> List[str]:
        """Get list of supported modalities."""
        return [modality.value for modality in self.supported_modalities]
    
    def get_supported_translations(self) -> Dict[str, List[str]]:
        """Get supported cross-modal translations."""
        translations = {}
        
        for (from_mod, to_mod) in self.translator.translation_matrix.keys():
            if from_mod.value not in translations:
                translations[from_mod.value] = []
            translations[from_mod.value].append(to_mod.value)
        
        return translations
    
    def get_communication_statistics(self) -> Dict[str, Any]:
        """Get multimodal communication statistics."""
        if not self.communication_history:
            return {'total_communications': 0}
        
        total_communications = len(self.communication_history)
        modality_counts = {}
        total_size = 0
        
        for record in self.communication_history:
            primary_modality = record['primary_modality']
            modality_counts[primary_modality] = modality_counts.get(primary_modality, 0) + 1
            total_size += record.get('total_size', 0)
        
        return {
            'total_communications': total_communications,
            'modality_distribution': modality_counts,
            'average_size_bytes': total_size / total_communications if total_communications > 0 else 0,
            'supported_modalities': len(self.supported_modalities),
            'supported_translations': len(self.translator.translation_matrix)
        }