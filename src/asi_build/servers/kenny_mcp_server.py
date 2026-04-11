#!/usr/bin/env python3
"""
Kenny Graph MCP Server
Provides access to Kenny Graph (89,574 nodes, 96,871 relationships) via MCP protocol
"""

import asyncio
import json
import sys
from typing import Dict, List, Any, Optional
import logging

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("kenny-mcp")

# Kenny Graph connection
MEMGRAPH_URI = "bolt://localhost:7687"

class KennyGraphMCP:
    def __init__(self):
        self.driver = None
        self.server = Server("kenny-graph")
        self.setup_handlers()
        
    async def connect_to_graph(self):
        """Connect to Kenny Graph database"""
        try:
            self.driver = GraphDatabase.driver(MEMGRAPH_URI)
            # Test connection
            with self.driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as total LIMIT 1")
                record = result.single()
                if record:
                    logger.info(f"Connected to Kenny Graph: {record['total']} nodes")
                    return True
        except Exception as e:
            logger.error(f"Failed to connect to Kenny Graph: {e}")
            return False
        return False
    
    def setup_handlers(self):
        """Set up MCP protocol handlers"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available Kenny Graph resources"""
            return [
                Resource(
                    uri="kenny://graph/stats",
                    name="Kenny Graph Statistics",
                    description="Overall statistics about Kenny Graph nodes and relationships",
                    mimeType="application/json"
                ),
                Resource(
                    uri="kenny://graph/nodes",
                    name="Kenny Graph Nodes",
                    description="Browse nodes in Kenny Graph by type",
                    mimeType="application/json"
                ),
                Resource(
                    uri="kenny://graph/relationships", 
                    name="Kenny Graph Relationships",
                    description="Browse relationships in Kenny Graph",
                    mimeType="application/json"
                ),
                Resource(
                    uri="kenny://agent/status",
                    name="Agent Army Status",
                    description="Current status of Kenny's 1,405 autonomous agents",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read Kenny Graph resources"""
            
            if uri == "kenny://graph/stats":
                return await self.get_graph_stats()
            elif uri == "kenny://graph/nodes":
                return await self.get_node_summary()
            elif uri == "kenny://graph/relationships":
                return await self.get_relationship_summary()
            elif uri == "kenny://agent/status":
                return await self.get_agent_status()
            else:
                raise ValueError(f"Unknown resource: {uri}")
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available Kenny Graph tools"""
            return [
                Tool(
                    name="query_kenny_graph",
                    description="Execute Cypher queries against Kenny Graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Cypher query to execute"
                            },
                            "limit": {
                                "type": "integer", 
                                "description": "Maximum number of results (default: 10)",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="search_kenny_concepts",
                    description="Search for concepts in Kenny Graph by name or description",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "Term to search for in concept names"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 10)", 
                                "default": 10
                            }
                        },
                        "required": ["search_term"]
                    }
                ),
                Tool(
                    name="get_node_relationships",
                    description="Get all relationships for a specific node",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node_name": {
                                "type": "string",
                                "description": "Name of the node to get relationships for"
                            }
                        },
                        "required": ["node_name"]
                    }
                ),
                Tool(
                    name="analyze_connectivity",
                    description="Analyze connectivity patterns in Kenny Graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "analysis_type": {
                                "type": "string",
                                "enum": ["centrality", "clusters", "shortest_path"],
                                "description": "Type of connectivity analysis"
                            },
                            "parameters": {
                                "type": "object", 
                                "description": "Additional parameters for analysis"
                            }
                        },
                        "required": ["analysis_type"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle Kenny Graph tool calls"""
            
            if name == "query_kenny_graph":
                return await self.execute_cypher_query(arguments)
            elif name == "search_kenny_concepts":
                return await self.search_concepts(arguments)
            elif name == "get_node_relationships":
                return await self.get_node_relationships(arguments)
            elif name == "analyze_connectivity":
                return await self.analyze_connectivity(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def get_graph_stats(self) -> str:
        """Get Kenny Graph statistics"""
        try:
            if not self.driver:
                return json.dumps({"error": "Not connected to Kenny Graph"})
            
            with self.driver.session() as session:
                # Get node count
                result = session.run("MATCH (n) RETURN count(n) as total")
                node_count = result.single()["total"]
                
                # Get relationship count
                result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
                rel_count = result.single()["total"]
                
                # Get node labels
                result = session.run("MATCH (n) RETURN DISTINCT labels(n) as labels, count(n) as count ORDER BY count DESC")
                node_types = [{"labels": record["labels"], "count": record["count"]} for record in result]
                
                # Get relationship types
                result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC")
                rel_types = [{"type": record["type"], "count": record["count"]} for record in result]
                
                stats = {
                    "timestamp": "2025-08-17T07:56:00Z",
                    "kenny_graph": {
                        "nodes": node_count,
                        "relationships": rel_count,
                        "database": "Memgraph",
                        "status": "connected"
                    },
                    "node_types": node_types[:10],
                    "relationship_types": rel_types[:10],
                    "agent_army": {
                        "total_agents": 1405,
                        "teams": 48,
                        "status": "operational"
                    }
                }
                
                return json.dumps(stats, indent=2)
                
        except Exception as e:
            logger.error(f"Error getting graph stats: {e}")
            return json.dumps({"error": str(e)})
    
    async def get_node_summary(self) -> str:
        """Get node summary"""
        try:
            if not self.driver:
                return json.dumps({"error": "Not connected to Kenny Graph"})
            
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n) 
                    RETURN DISTINCT labels(n) as labels, count(n) as count 
                    ORDER BY count DESC LIMIT 20
                """)
                
                node_summary = [
                    {"labels": record["labels"], "count": record["count"]}
                    for record in result
                ]
                
                return json.dumps({
                    "node_types": node_summary,
                    "total_types": len(node_summary)
                }, indent=2)
                
        except Exception as e:
            logger.error(f"Error getting node summary: {e}")
            return json.dumps({"error": str(e)})
    
    async def get_relationship_summary(self) -> str:
        """Get relationship summary"""
        try:
            if not self.driver:
                return json.dumps({"error": "Not connected to Kenny Graph"})
            
            with self.driver.session() as session:
                result = session.run("""
                    MATCH ()-[r]->() 
                    RETURN type(r) as type, count(r) as count 
                    ORDER BY count DESC LIMIT 20
                """)
                
                rel_summary = [
                    {"type": record["type"], "count": record["count"]}
                    for record in result
                ]
                
                return json.dumps({
                    "relationship_types": rel_summary,
                    "total_types": len(rel_summary)
                }, indent=2)
                
        except Exception as e:
            logger.error(f"Error getting relationship summary: {e}")
            return json.dumps({"error": str(e)})
    
    async def get_agent_status(self) -> str:
        """Get agent army status"""
        try:
            supervisor_file = "/home/ubuntu/code/kenny/supervisor_dashboard.json"
            with open(supervisor_file, 'r') as f:
                supervisor_data = json.load(f)
            
            return json.dumps(supervisor_data, indent=2)
            
        except Exception as e:
            logger.error(f"Error getting agent status: {e}")
            return json.dumps({"error": str(e)})
    
    async def execute_cypher_query(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute Cypher query against Kenny Graph"""
        query = arguments.get("query")
        limit = arguments.get("limit", 10)
        
        try:
            if not self.driver:
                return [TextContent(type="text", text="Error: Not connected to Kenny Graph")]
            
            with self.driver.session() as session:
                # Add LIMIT if not present
                if "LIMIT" not in query.upper():
                    query += f" LIMIT {limit}"
                
                result = session.run(query)
                records = []
                
                for record in result:
                    records.append(dict(record))
                
                response = {
                    "query": query,
                    "results": records,
                    "count": len(records)
                }
                
                return [TextContent(type="text", text=json.dumps(response, indent=2))]
                
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return [TextContent(type="text", text=f"Error executing query: {e}")]
    
    async def search_concepts(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Search for concepts in Kenny Graph"""
        search_term = arguments.get("search_term")
        limit = arguments.get("limit", 10)
        
        try:
            if not self.driver:
                return [TextContent(type="text", text="Error: Not connected to Kenny Graph")]
            
            with self.driver.session() as session:
                query = """
                    MATCH (n)
                    WHERE any(label IN labels(n) WHERE toLower(label) CONTAINS toLower($search_term))
                       OR (exists(n.name) AND toLower(n.name) CONTAINS toLower($search_term))
                       OR (exists(n.description) AND toLower(n.description) CONTAINS toLower($search_term))
                    RETURN n.name as name, labels(n) as labels, n.description as description
                    LIMIT $limit
                """
                
                result = session.run(query, search_term=search_term, limit=limit)
                
                concepts = []
                for record in result:
                    concepts.append({
                        "name": record["name"],
                        "labels": record["labels"],
                        "description": record["description"]
                    })
                
                response = {
                    "search_term": search_term,
                    "concepts": concepts,
                    "count": len(concepts)
                }
                
                return [TextContent(type="text", text=json.dumps(response, indent=2))]
                
        except Exception as e:
            logger.error(f"Error searching concepts: {e}")
            return [TextContent(type="text", text=f"Error searching concepts: {e}")]
    
    async def get_node_relationships(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Get relationships for a specific node"""
        node_name = arguments.get("node_name")
        
        try:
            if not self.driver:
                return [TextContent(type="text", text="Error: Not connected to Kenny Graph")]
            
            with self.driver.session() as session:
                query = """
                    MATCH (a)-[r]-(b)
                    WHERE a.name = $node_name OR $node_name IN labels(a)
                    RETURN type(r) as relationship, 
                           a.name as source_name, labels(a) as source_labels,
                           b.name as target_name, labels(b) as target_labels
                    LIMIT 50
                """
                
                result = session.run(query, node_name=node_name)
                
                relationships = []
                for record in result:
                    relationships.append({
                        "relationship": record["relationship"],
                        "source": {
                            "name": record["source_name"],
                            "labels": record["source_labels"]
                        },
                        "target": {
                            "name": record["target_name"], 
                            "labels": record["target_labels"]
                        }
                    })
                
                response = {
                    "node": node_name,
                    "relationships": relationships,
                    "count": len(relationships)
                }
                
                return [TextContent(type="text", text=json.dumps(response, indent=2))]
                
        except Exception as e:
            logger.error(f"Error getting node relationships: {e}")
            return [TextContent(type="text", text=f"Error getting node relationships: {e}")]
    
    async def analyze_connectivity(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Analyze connectivity patterns"""
        analysis_type = arguments.get("analysis_type")
        
        try:
            if not self.driver:
                return [TextContent(type="text", text="Error: Not connected to Kenny Graph")]
            
            with self.driver.session() as session:
                if analysis_type == "centrality":
                    # Find most connected nodes
                    query = """
                        MATCH (n)
                        RETURN n.name as name, labels(n) as labels, 
                               size((n)--()) as degree
                        ORDER BY degree DESC LIMIT 10
                    """
                    result = session.run(query)
                    analysis = [{"name": r["name"], "labels": r["labels"], "degree": r["degree"]} for r in result]
                    
                elif analysis_type == "clusters":
                    # Find densely connected clusters
                    query = """
                        MATCH (n)-[r]-(m)
                        WITH n, count(r) as connections
                        WHERE connections > 5
                        RETURN n.name as name, labels(n) as labels, connections
                        ORDER BY connections DESC LIMIT 10
                    """
                    result = session.run(query)
                    analysis = [{"name": r["name"], "labels": r["labels"], "connections": r["connections"]} for r in result]
                    
                else:
                    analysis = {"error": f"Unknown analysis type: {analysis_type}"}
                
                response = {
                    "analysis_type": analysis_type,
                    "results": analysis
                }
                
                return [TextContent(type="text", text=json.dumps(response, indent=2))]
                
        except Exception as e:
            logger.error(f"Error analyzing connectivity: {e}")
            return [TextContent(type="text", text=f"Error analyzing connectivity: {e}")]

    async def run(self):
        """Run the MCP server"""
        # Connect to Kenny Graph
        connected = await self.connect_to_graph()
        if not connected:
            logger.error("Failed to connect to Kenny Graph")
            sys.exit(1)
        
        # Run MCP server
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="kenny-graph",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )

async def main():
    """Main entry point"""
    kenny_mcp = KennyGraphMCP()
    await kenny_mcp.run()

if __name__ == "__main__":
    asyncio.run(main())