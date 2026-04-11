#!/usr/bin/env python3
"""
Kenny Graph MCP Server - Public SSE Endpoint
Real-time streaming access to Kenny Graph data via Server-Sent Events
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Kenny Graph imports
import sys
import os
sys.path.append('/home/ubuntu/code/kenny/src')

from neo4j import GraphDatabase
import sqlite3

app = FastAPI(
    title="Kenny Graph SSE API",
    description="Real-time streaming access to Kenny Graph MCP server",
    version="1.0.0"
)

# Enable CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MEMGRAPH_URI = "bolt://localhost:7687"
KENNY_DB_PATH = "/home/ubuntu/code/kenny/src/kenny_analyses.db"
UPDATE_INTERVAL = 5  # seconds

# Global state
current_stats = {}
connected_clients = set()

class KennyGraphSSE:
    def __init__(self):
        self.driver = None
        self.logger = logging.getLogger(__name__)
        
    async def connect_memgraph(self):
        """Connect to Memgraph/Kenny Graph"""
        try:
            self.driver = GraphDatabase.driver(MEMGRAPH_URI)
            # Test connection
            with self.driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as total LIMIT 1")
                record = result.single()
                if record:
                    self.logger.info(f"Connected to Kenny Graph: {record['total']} nodes")
                    return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Memgraph: {e}")
            return False
        return False
    
    def get_kenny_graph_stats(self) -> Dict[str, Any]:
        """Get real-time Kenny Graph statistics"""
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unknown",
            "nodes": 0,
            "relationships": 0,
            "node_types": [],
            "relationship_types": [],
            "recent_activity": []
        }
        
        try:
            if self.driver:
                with self.driver.session() as session:
                    # Get node count
                    result = session.run("MATCH (n) RETURN count(n) as total")
                    record = result.single()
                    if record:
                        stats["nodes"] = record["total"]
                    
                    # Get relationship count
                    result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
                    record = result.single()
                    if record:
                        stats["relationships"] = record["total"]
                    
                    # Get node types
                    result = session.run("""
                        MATCH (n) 
                        RETURN DISTINCT labels(n) as types, count(n) as count 
                        ORDER BY count DESC LIMIT 10
                    """)
                    stats["node_types"] = [
                        {"labels": record["types"], "count": record["count"]}
                        for record in result
                    ]
                    
                    # Get relationship types
                    result = session.run("""
                        MATCH ()-[r]->() 
                        RETURN type(r) as type, count(r) as count 
                        ORDER BY count DESC LIMIT 10
                    """)
                    stats["relationship_types"] = [
                        {"type": record["type"], "count": record["count"]}
                        for record in result
                    ]
                    
                    stats["status"] = "connected"
                    
        except Exception as e:
            self.logger.error(f"Error getting Kenny Graph stats: {e}")
            stats["status"] = "error"
            stats["error"] = str(e)
        
        return stats
    
    def get_kenny_analysis_stats(self) -> Dict[str, Any]:
        """Get Kenny analysis database statistics"""
        stats = {
            "total_analyses": 0,
            "recent_analyses": [],
            "performance_metrics": {}
        }
        
        try:
            if os.path.exists(KENNY_DB_PATH):
                conn = sqlite3.connect(KENNY_DB_PATH)
                cursor = conn.cursor()
                
                # Get total analyses
                cursor.execute("SELECT COUNT(*) FROM kenny_analyses")
                stats["total_analyses"] = cursor.fetchone()[0]
                
                # Get recent analyses
                cursor.execute("""
                    SELECT timestamp, analysis_type, elements_found, apps_found, duration
                    FROM kenny_analyses 
                    ORDER BY timestamp DESC 
                    LIMIT 5
                """)
                stats["recent_analyses"] = [
                    {
                        "timestamp": row[0],
                        "type": row[1],
                        "elements": row[2],
                        "apps": row[3],
                        "duration": row[4]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Get performance metrics
                cursor.execute("""
                    SELECT 
                        AVG(duration) as avg_duration,
                        AVG(elements_found) as avg_elements,
                        AVG(apps_found) as avg_apps,
                        COUNT(*) as total_count
                    FROM kenny_analyses 
                    WHERE timestamp > datetime('now', '-1 hour')
                """)
                row = cursor.fetchone()
                if row and row[0]:
                    stats["performance_metrics"] = {
                        "avg_duration": round(row[0], 2),
                        "avg_elements": round(row[1], 2),
                        "avg_apps": round(row[2], 2),
                        "recent_count": row[3]
                    }
                
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Error getting Kenny analysis stats: {e}")
            stats["error"] = str(e)
        
        return stats
    
    def get_supervisor_stats(self) -> Dict[str, Any]:
        """Get supervisor dashboard statistics"""
        supervisor_file = "/home/ubuntu/code/kenny/supervisor_dashboard.json"
        try:
            if os.path.exists(supervisor_file):
                with open(supervisor_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading supervisor stats: {e}")
        
        return {"error": "Supervisor stats unavailable"}

kenny_sse = KennyGraphSSE()

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    logging.basicConfig(level=logging.INFO)
    await kenny_sse.connect_memgraph()

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Kenny Graph SSE API",
        "version": "1.0.0",
        "endpoints": {
            "/sse/kenny-graph": "Real-time Kenny Graph statistics",
            "/sse/supervisor": "Real-time supervisor metrics",
            "/sse/combined": "Combined real-time data",
            "/stats/current": "Current snapshot of all stats",
            "/health": "Health check",
            "/demo": "SSE demo page"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    graph_connected = kenny_sse.driver is not None
    analysis_db_exists = os.path.exists(KENNY_DB_PATH)
    
    return {
        "status": "healthy" if graph_connected else "degraded",
        "kenny_graph_connected": graph_connected,
        "analysis_db_available": analysis_db_exists,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": time.time()
    }

@app.get("/stats/current")
async def current_stats():
    """Get current snapshot of all statistics"""
    return {
        "kenny_graph": kenny_sse.get_kenny_graph_stats(),
        "kenny_analysis": kenny_sse.get_kenny_analysis_stats(),
        "supervisor": kenny_sse.get_supervisor_stats(),
        "timestamp": datetime.utcnow().isoformat()
    }

async def generate_kenny_graph_stream():
    """Generate real-time Kenny Graph data stream"""
    while True:
        try:
            stats = kenny_sse.get_kenny_graph_stats()
            data = json.dumps(stats)
            yield f"data: {data}\n\n"
            await asyncio.sleep(UPDATE_INTERVAL)
        except Exception as e:
            error_data = json.dumps({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            yield f"data: {error_data}\n\n"
            await asyncio.sleep(UPDATE_INTERVAL)

async def generate_supervisor_stream():
    """Generate real-time supervisor metrics stream"""
    while True:
        try:
            stats = kenny_sse.get_supervisor_stats()
            data = json.dumps(stats)
            yield f"data: {data}\n\n"
            await asyncio.sleep(UPDATE_INTERVAL)
        except Exception as e:
            error_data = json.dumps({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            yield f"data: {error_data}\n\n"
            await asyncio.sleep(UPDATE_INTERVAL)

async def generate_combined_stream():
    """Generate combined real-time data stream"""
    while True:
        try:
            combined_stats = {
                "kenny_graph": kenny_sse.get_kenny_graph_stats(),
                "kenny_analysis": kenny_sse.get_kenny_analysis_stats(),
                "supervisor": kenny_sse.get_supervisor_stats(),
                "timestamp": datetime.utcnow().isoformat()
            }
            data = json.dumps(combined_stats)
            yield f"data: {data}\n\n"
            await asyncio.sleep(UPDATE_INTERVAL)
        except Exception as e:
            error_data = json.dumps({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            yield f"data: {error_data}\n\n"
            await asyncio.sleep(UPDATE_INTERVAL)

@app.get("/sse/kenny-graph")
async def kenny_graph_sse(request: Request):
    """Server-Sent Events endpoint for Kenny Graph data"""
    return StreamingResponse(
        generate_kenny_graph_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.get("/sse/supervisor")
async def supervisor_sse(request: Request):
    """Server-Sent Events endpoint for supervisor metrics"""
    return StreamingResponse(
        generate_supervisor_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.get("/sse/combined")
async def combined_sse(request: Request):
    """Server-Sent Events endpoint for all Kenny data"""
    return StreamingResponse(
        generate_combined_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.get("/demo", response_class=HTMLResponse)
async def sse_demo():
    """SSE demo page for testing"""
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>Kenny Graph SSE Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }
        .container { max-width: 1200px; margin: 0 auto; }
        .panel { background: #2a2a2a; padding: 20px; margin: 10px 0; border-radius: 8px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stat-box { background: #3a3a3a; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-value { font-size: 2em; font-weight: bold; color: #4CAF50; }
        .stat-label { font-size: 0.9em; color: #ccc; }
        .log { background: #1e1e1e; padding: 10px; border-radius: 5px; height: 200px; overflow-y: auto; font-family: monospace; font-size: 0.9em; }
        .status { padding: 5px 10px; border-radius: 3px; font-weight: bold; }
        .status.connected { background: #4CAF50; }
        .status.error { background: #f44336; }
        .header { text-align: center; margin-bottom: 30px; }
        .timestamp { color: #888; font-size: 0.8em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 Kenny Graph Live Dashboard</h1>
            <p>Real-time streaming data via Server-Sent Events</p>
        </div>
        
        <div class="panel">
            <h2>Kenny Graph Statistics</h2>
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value" id="nodes">-</div>
                    <div class="stat-label">Nodes</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="relationships">-</div>
                    <div class="stat-label">Relationships</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="status">-</div>
                    <div class="stat-label">Status</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="agents">-</div>
                    <div class="stat-label">Active Agents</div>
                </div>
            </div>
        </div>
        
        <div class="panel">
            <h2>Agent Army Status</h2>
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value" id="teams">-</div>
                    <div class="stat-label">Teams</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="productivity">-</div>
                    <div class="stat-label">Productivity</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="uptime">-</div>
                    <div class="stat-label">Uptime (hrs)</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="issues">-</div>
                    <div class="stat-label">Issues Resolved</div>
                </div>
            </div>
        </div>
        
        <div class="panel">
            <h2>Live Activity Log</h2>
            <div class="log" id="log"></div>
        </div>
        
        <div class="panel">
            <h2>Connection Status</h2>
            <p>SSE Connection: <span class="status" id="connection-status">Connecting...</span></p>
            <p class="timestamp">Last Update: <span id="last-update">-</span></p>
        </div>
    </div>

    <script>
        const eventSource = new EventSource('/sse/combined');
        const log = document.getElementById('log');
        
        function addLog(message) {
            const timestamp = new Date().toLocaleTimeString();
            log.innerHTML += `[${timestamp}] ${message}\\n`;
            log.scrollTop = log.scrollHeight;
        }
        
        function updateStatus(connected) {
            const statusEl = document.getElementById('connection-status');
            statusEl.textContent = connected ? 'Connected' : 'Disconnected';
            statusEl.className = `status ${connected ? 'connected' : 'error'}`;
        }
        
        eventSource.onopen = function(e) {
            addLog('✅ Connected to Kenny Graph SSE');
            updateStatus(true);
        };
        
        eventSource.onmessage = function(e) {
            try {
                const data = JSON.parse(e.data);
                document.getElementById('last-update').textContent = new Date().toLocaleString();
                
                // Update Kenny Graph stats
                if (data.kenny_graph) {
                    document.getElementById('nodes').textContent = data.kenny_graph.nodes?.toLocaleString() || '-';
                    document.getElementById('relationships').textContent = data.kenny_graph.relationships?.toLocaleString() || '-';
                    document.getElementById('status').textContent = data.kenny_graph.status || '-';
                }
                
                // Update supervisor stats
                if (data.supervisor?.supervisor_metrics) {
                    const metrics = data.supervisor.supervisor_metrics;
                    document.getElementById('agents').textContent = metrics.total_agents?.toLocaleString() || '-';
                    document.getElementById('teams').textContent = metrics.teams_monitored || '-';
                    document.getElementById('productivity').textContent = 
                        metrics.productivity_average ? (metrics.productivity_average * 100).toFixed(1) + '%' : '-';
                    document.getElementById('uptime').textContent = 
                        metrics.uptime_hours ? metrics.uptime_hours.toFixed(1) : '-';
                    document.getElementById('issues').textContent = metrics.issues_resolved || '-';
                }
                
                // Log activity
                if (data.kenny_analysis?.recent_analyses?.length > 0) {
                    const recent = data.kenny_analysis.recent_analyses[0];
                    addLog(`📊 Latest analysis: ${recent.elements} elements, ${recent.apps} apps (${recent.duration}s)`);
                }
                
            } catch (error) {
                addLog(`❌ Error parsing data: ${error.message}`);
            }
        };
        
        eventSource.onerror = function(e) {
            addLog('❌ SSE connection error');
            updateStatus(false);
        };
        
        // Initial log
        addLog('🚀 Kenny Graph SSE Demo initialized');
    </script>
</body>
</html>
    """)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Kenny Graph SSE Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    print(f"🚀 Starting Kenny Graph SSE Server on {args.host}:{args.port}")
    print(f"📊 Demo page: http://{args.host}:{args.port}/demo")
    print(f"🔗 SSE endpoints:")
    print(f"   - Kenny Graph: http://{args.host}:{args.port}/sse/kenny-graph")
    print(f"   - Supervisor: http://{args.host}:{args.port}/sse/supervisor")
    print(f"   - Combined: http://{args.host}:{args.port}/sse/combined")
    
    uvicorn.run(
        "kenny_graph_sse_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )