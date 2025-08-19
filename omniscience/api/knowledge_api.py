"""
Knowledge API - REST and WebSocket API for Omniscience Network
=============================================================

Comprehensive API interface for accessing omniscience network capabilities
through REST endpoints and real-time WebSocket connections.
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Import omniscience components
from ..core.knowledge_engine import KnowledgeEngine, KnowledgeQuery
from ..core.information_aggregator import InformationAggregator
from ..core.knowledge_graph_manager import KnowledgeGraphManager
from ..search.intelligent_search import IntelligentSearch
from ..synthesis.predictive_synthesizer import PredictiveSynthesizer
from ..validation.quality_controller import QualityController
from ..learning.contextual_learner import ContextualLearner


# API Models
class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    priority: Optional[int] = 1
    session_id: Optional[str] = None


class BatchQueryRequest(BaseModel):
    queries: List[str]
    context: Optional[Dict[str, Any]] = None
    parallel: Optional[bool] = True


class SystemConfigRequest(BaseModel):
    component: str
    config: Dict[str, Any]


class LearningFeedbackRequest(BaseModel):
    query_id: str
    feedback_type: str  # 'positive', 'negative', 'correction'
    feedback_data: Dict[str, Any]
    user_id: Optional[str] = None


# WebSocket Connection Manager
class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = {
            'client_id': client_id,
            'connected_at': time.time(),
            'query_count': 0
        }
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Connection might be closed
                pass


class KnowledgeAPI:
    """
    Main API class for the omniscience network.
    
    Provides REST and WebSocket endpoints for:
    - Knowledge queries and batch processing
    - System monitoring and statistics
    - Configuration management
    - Learning feedback and adaptation
    - Real-time updates and notifications
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.logger = self._setup_logging()
        
        # Initialize omniscience components
        self.knowledge_engine = KnowledgeEngine(self.config.get('engine', {}))
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Kenny Omniscience Network API",
            description="Advanced knowledge processing and synthesis API",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # WebSocket connection manager
        self.connection_manager = ConnectionManager()
        
        # API statistics
        self.api_stats = {
            'total_queries': 0,
            'total_batch_queries': 0,
            'total_websocket_connections': 0,
            'active_connections': 0,
            'uptime_start': time.time(),
            'average_response_time': 0.0
        }
        
        # Setup routes
        self._setup_routes()
        
        self.logger.info("Knowledge API initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default API configuration."""
        return {
            'host': '0.0.0.0',
            'port': 8001,
            'max_concurrent_queries': 20,
            'query_timeout': 60.0,
            'websocket_ping_interval': 30,
            'enable_real_time_updates': True,
            'enable_learning_feedback': True,
            'rate_limiting': {
                'enabled': True,
                'queries_per_minute': 60,
                'batch_queries_per_minute': 10
            },
            'authentication': {
                'enabled': False,
                'api_key_header': 'X-API-Key'
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        logger = logging.getLogger('kenny.omniscience.api')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _setup_routes(self):
        """Setup API routes."""
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "uptime": time.time() - self.api_stats['uptime_start'],
                "version": "1.0.0"
            }
        
        # Main knowledge query endpoint
        @self.app.post("/api/query")
        async def query_knowledge(request: QueryRequest):
            start_time = time.time()
            self.api_stats['total_queries'] += 1
            
            try:
                # Create knowledge query
                knowledge_query = KnowledgeQuery(
                    query=request.query,
                    context=request.context or {},
                    priority=request.priority,
                    session_id=request.session_id
                )
                
                # Process query
                result = await self.knowledge_engine.process_query(knowledge_query)
                
                # Update statistics
                response_time = time.time() - start_time
                self._update_response_time_stats(response_time)
                
                # Broadcast to WebSocket clients if enabled
                if self.config.get('enable_real_time_updates', True):
                    await self._broadcast_query_update(knowledge_query, result)
                
                return {
                    "success": True,
                    "result": self._serialize_result(result),
                    "processing_time": response_time,
                    "query_id": getattr(result.query, 'session_id', None) or str(time.time())
                }
                
            except Exception as e:
                self.logger.error(f"Error processing query: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Batch query endpoint
        @self.app.post("/api/batch-query")
        async def batch_query_knowledge(request: BatchQueryRequest):
            start_time = time.time()
            self.api_stats['total_batch_queries'] += 1
            
            try:
                # Convert to KnowledgeQuery objects
                knowledge_queries = [
                    KnowledgeQuery(query=q, context=request.context or {})
                    for q in request.queries
                ]
                
                # Process batch
                if request.parallel:
                    results = await self.knowledge_engine.batch_process_queries(knowledge_queries)
                else:
                    results = []
                    for query in knowledge_queries:
                        result = await self.knowledge_engine.process_query(query)
                        results.append(result)
                
                response_time = time.time() - start_time
                
                return {
                    "success": True,
                    "results": [self._serialize_result(r) for r in results],
                    "total_queries": len(request.queries),
                    "processing_time": response_time,
                    "batch_id": str(time.time())
                }
                
            except Exception as e:
                self.logger.error(f"Error processing batch query: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # System statistics endpoint
        @self.app.get("/api/stats")
        async def get_system_stats():
            try:
                # Get component statistics
                engine_stats = self.knowledge_engine.get_performance_metrics()
                
                # Combine with API statistics
                combined_stats = {
                    "api_stats": self.api_stats.copy(),
                    "engine_stats": engine_stats,
                    "active_websocket_connections": len(self.connection_manager.active_connections),
                    "system_uptime": time.time() - self.api_stats['uptime_start']
                }
                
                return combined_stats
                
            except Exception as e:
                self.logger.error(f"Error retrieving statistics: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Component-specific statistics
        @self.app.get("/api/stats/{component}")
        async def get_component_stats(component: str):
            try:
                if component == "aggregator":
                    stats = self.knowledge_engine.aggregator.get_aggregation_stats()
                elif component == "search":
                    stats = self.knowledge_engine.search_engine.get_search_statistics()
                elif component == "synthesis":
                    stats = self.knowledge_engine.synthesizer.get_synthesis_statistics()
                elif component == "validation":
                    stats = self.knowledge_engine.quality_controller.get_validation_statistics()
                elif component == "learning":
                    stats = self.knowledge_engine.learner.get_learning_insights()
                else:
                    raise HTTPException(status_code=404, detail=f"Component '{component}' not found")
                
                return {
                    "component": component,
                    "statistics": stats,
                    "timestamp": time.time()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error retrieving {component} statistics: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Configuration management
        @self.app.post("/api/config")
        async def update_config(request: SystemConfigRequest):
            try:
                # Update component configuration
                if request.component == "engine":
                    # Update engine config (simplified)
                    pass
                elif request.component == "api":
                    # Update API config
                    self.config.update(request.config)
                else:
                    raise HTTPException(status_code=404, detail=f"Component '{request.component}' not found")
                
                return {
                    "success": True,
                    "component": request.component,
                    "updated_config": request.config,
                    "timestamp": time.time()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error updating configuration: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Learning feedback endpoint
        @self.app.post("/api/feedback")
        async def submit_learning_feedback(request: LearningFeedbackRequest):
            try:
                if not self.config.get('enable_learning_feedback', True):
                    raise HTTPException(status_code=403, detail="Learning feedback is disabled")
                
                # Process feedback (simplified)
                feedback_result = {
                    "feedback_id": f"fb_{time.time()}",
                    "query_id": request.query_id,
                    "feedback_type": request.feedback_type,
                    "processed_at": time.time(),
                    "status": "processed"
                }
                
                return {
                    "success": True,
                    "feedback_result": feedback_result
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error processing feedback: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # WebSocket endpoint for real-time updates
        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await self.connection_manager.connect(websocket, client_id)
            self.api_stats['total_websocket_connections'] += 1
            self.api_stats['active_connections'] = len(self.connection_manager.active_connections)
            
            try:
                # Send welcome message
                await self.connection_manager.send_personal_message(
                    json.dumps({
                        "type": "connection",
                        "status": "connected",
                        "client_id": client_id,
                        "timestamp": time.time()
                    }),
                    websocket
                )
                
                # Keep connection alive
                while True:
                    try:
                        # Wait for messages or ping
                        await asyncio.wait_for(
                            websocket.receive_text(),
                            timeout=self.config.get('websocket_ping_interval', 30)
                        )
                    except asyncio.TimeoutError:
                        # Send ping
                        await self.connection_manager.send_personal_message(
                            json.dumps({"type": "ping", "timestamp": time.time()}),
                            websocket
                        )
                        
            except WebSocketDisconnect:
                self.connection_manager.disconnect(websocket)
                self.api_stats['active_connections'] = len(self.connection_manager.active_connections)
                self.logger.info(f"WebSocket client {client_id} disconnected")
            except Exception as e:
                self.logger.error(f"WebSocket error for client {client_id}: {str(e)}")
                self.connection_manager.disconnect(websocket)
        
        # Advanced query endpoint with real-time streaming
        @self.app.websocket("/ws/query/{client_id}")
        async def websocket_query_endpoint(websocket: WebSocket, client_id: str):
            await self.connection_manager.connect(websocket, client_id)
            
            try:
                while True:
                    # Receive query from client
                    data = await websocket.receive_text()
                    query_data = json.loads(data)
                    
                    # Create knowledge query
                    knowledge_query = KnowledgeQuery(
                        query=query_data.get('query', ''),
                        context=query_data.get('context', {}),
                        session_id=client_id
                    )
                    
                    # Send processing started message
                    await self.connection_manager.send_personal_message(
                        json.dumps({
                            "type": "query_started",
                            "query": knowledge_query.query,
                            "timestamp": time.time()
                        }),
                        websocket
                    )
                    
                    # Process query
                    try:
                        result = await self.knowledge_engine.process_query(knowledge_query)
                        
                        # Send result
                        await self.connection_manager.send_personal_message(
                            json.dumps({
                                "type": "query_result",
                                "result": self._serialize_result(result),
                                "timestamp": time.time()
                            }),
                            websocket
                        )
                        
                    except Exception as e:
                        await self.connection_manager.send_personal_message(
                            json.dumps({
                                "type": "query_error",
                                "error": str(e),
                                "timestamp": time.time()
                            }),
                            websocket
                        )
                        
            except WebSocketDisconnect:
                self.connection_manager.disconnect(websocket)
    
    def _serialize_result(self, result) -> Dict[str, Any]:
        """Serialize knowledge result for JSON response."""
        if hasattr(result, '__dict__'):
            # Convert dataclass to dict
            serialized = {}
            for key, value in result.__dict__.items():
                if hasattr(value, '__dict__'):
                    serialized[key] = value.__dict__
                else:
                    serialized[key] = value
            return serialized
        elif isinstance(result, dict):
            return result
        else:
            return {"result": str(result)}
    
    def _update_response_time_stats(self, response_time: float):
        """Update response time statistics."""
        current_avg = self.api_stats['average_response_time']
        total_queries = self.api_stats['total_queries']
        
        # Calculate rolling average
        if total_queries == 1:
            self.api_stats['average_response_time'] = response_time
        else:
            alpha = 0.1  # Smoothing factor
            self.api_stats['average_response_time'] = (alpha * response_time + 
                                                     (1 - alpha) * current_avg)
    
    async def _broadcast_query_update(self, query, result):
        """Broadcast query update to WebSocket clients."""
        if not self.connection_manager.active_connections:
            return
        
        try:
            update_message = json.dumps({
                "type": "query_update",
                "query_preview": query.query[:100] + "..." if len(query.query) > 100 else query.query,
                "confidence": getattr(result, 'confidence', 0.5),
                "processing_time": getattr(result, 'processing_time', 0.0),
                "timestamp": time.time()
            })
            
            await self.connection_manager.broadcast(update_message)
            
        except Exception as e:
            self.logger.warning(f"Error broadcasting query update: {str(e)}")
    
    def run(self, host: Optional[str] = None, port: Optional[int] = None):
        """Run the API server."""
        host = host or self.config.get('host', '0.0.0.0')
        port = port or self.config.get('port', 8001)
        
        self.logger.info(f"Starting Knowledge API server on {host}:{port}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
    
    async def shutdown(self):
        """Gracefully shutdown the API."""
        self.logger.info("Shutting down Knowledge API...")
        
        # Close WebSocket connections
        for connection in self.connection_manager.active_connections.copy():
            try:
                await connection.close()
            except:
                pass
        
        # Shutdown knowledge engine
        await self.knowledge_engine.shutdown()
        
        self.logger.info("Knowledge API shutdown complete")


# Standalone API server
def create_api_server(config: Optional[Dict[str, Any]] = None) -> KnowledgeAPI:
    """Create and return a KnowledgeAPI instance."""
    return KnowledgeAPI(config)


def run_api_server(config: Optional[Dict[str, Any]] = None):
    """Run the API server directly."""
    api = create_api_server(config)
    api.run()


# API client helper class
class KnowledgeAPIClient:
    """Client for interacting with the Knowledge API."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip('/')
        self.session = None  # Would use aiohttp.ClientSession in production
    
    async def query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Submit a knowledge query."""
        # This would be implemented with actual HTTP client in production
        pass
    
    async def batch_query(self, queries: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Submit a batch of knowledge queries."""
        pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        pass
    
    async def submit_feedback(self, query_id: str, feedback_type: str, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit learning feedback."""
        pass


if __name__ == "__main__":
    # Run API server if executed directly
    run_api_server()