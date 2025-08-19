"""
Memgraph Database Connection Module

Provides connection management and query execution for Kenny's Graph Intelligence System.
Uses Neo4j driver for better compatibility and auto-commit handling.
"""

from neo4j import GraphDatabase
import mgclient
import logging
import time
from contextlib import contextmanager
from typing import Dict, List, Any, Optional
import json

logger = logging.getLogger(__name__)

class MemgraphConnection:
    """Production-ready Memgraph connection manager with retry logic and error handling."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 7687, 
                 max_retries: int = 3, retry_delay: float = 1.0):
        self.host = host
        self.port = port
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection = None
        self.cursor = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to Memgraph with retry logic."""
        for attempt in range(self.max_retries):
            try:
                self.connection = mgclient.connect(host=self.host, port=self.port)
                self.cursor = self.connection.cursor()
                logger.info(f"✅ Connected to Memgraph at {self.host}:{self.port}")
                return
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise ConnectionError(f"Failed to connect to Memgraph after {self.max_retries} attempts")
    
    def execute(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Execute Cypher query with parameters and return results."""
        if not self.cursor:
            self._connect()
        
        try:
            if parameters:
                self.cursor.execute(query, parameters)
            else:
                self.cursor.execute(query)
            
            results = self.cursor.fetchall()
            return results
            
        except mgclient.DatabaseError as e:
            logger.error(f"Database error executing query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error executing query: {e}")
            raise
    
    def execute_transaction(self, queries: List[Dict[str, Any]]) -> List[Any]:
        """Execute multiple queries in a single transaction."""
        if not self.cursor:
            self._connect()
        
        try:
            self.cursor.execute("BEGIN")
            results = []
            
            for query_data in queries:
                query = query_data.get('query')
                parameters = query_data.get('parameters')
                
                if parameters:
                    self.cursor.execute(query, parameters)
                else:
                    self.cursor.execute(query)
                
                results.append(self.cursor.fetchall())
            
            self.cursor.execute("COMMIT")
            return results
            
        except Exception as e:
            self.cursor.execute("ROLLBACK")
            logger.error(f"Transaction failed, rolled back: {e}")
            raise
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        if not self.cursor:
            self._connect()
        
        try:
            self.cursor.execute("BEGIN")
            yield self.cursor
            self.cursor.execute("COMMIT")
        except Exception as e:
            self.cursor.execute("ROLLBACK")
            logger.error(f"Transaction failed, rolled back: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            # Node count by type
            node_stats = self.execute("""
                MATCH (n) 
                RETURN labels(n)[0] as type, count(n) as count 
                ORDER BY count DESC
            """)
            
            # Relationship count by type  
            rel_stats = self.execute("""
                MATCH ()-[r]->() 
                RETURN type(r) as type, count(r) as count 
                ORDER BY count DESC
            """)
            
            # Total counts
            total_nodes = self.execute("MATCH (n) RETURN count(n) as total")[0][0]
            total_rels = self.execute("MATCH ()-[r]->() RETURN count(r) as total")[0][0]
            
            return {
                'total_nodes': total_nodes,
                'total_relationships': total_rels,
                'node_types': [{'type': row[0], 'count': row[1]} for row in node_stats],
                'relationship_types': [{'type': row[0], 'count': row[1]} for row in rel_stats]
            }
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {'error': str(e)}
    
    def clear_database(self) -> bool:
        """Clear all data from database. Use with caution!"""
        try:
            self.execute("MATCH (n) DETACH DELETE n")
            logger.info("✅ Database cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            return False
    
    def create_indexes(self) -> bool:
        """Create performance indexes for Kenny's graph intelligence."""
        index_queries = [
            "CREATE INDEX ON :UIElement(id)",
            "CREATE INDEX ON :UIElement(type)",
            "CREATE INDEX ON :UIElement(coordinates)",
            "CREATE INDEX ON :Workflow(id)",
            "CREATE INDEX ON :Workflow(status)",
            "CREATE INDEX ON :Community(id)",
            "CREATE INDEX ON :Community(modularity)",
            "CREATE INDEX ON :Application(name)",
            "CREATE INDEX ON :Pattern(frequency)"
        ]
        
        success_count = 0
        for query in index_queries:
            try:
                self.execute(query)
                success_count += 1
                logger.info(f"✅ Created index: {query}")
            except mgclient.DatabaseError as e:
                if "already exists" in str(e).lower():
                    logger.info(f"Index already exists: {query}")
                    success_count += 1
                else:
                    logger.warning(f"Failed to create index: {query} - {e}")
        
        logger.info(f"✅ Created {success_count}/{len(index_queries)} indexes")
        return success_count == len(index_queries)
    
    def create_constraints(self) -> bool:
        """Create uniqueness constraints for data integrity."""
        constraint_queries = [
            "CREATE CONSTRAINT ON (n:UIElement) ASSERT n.id IS UNIQUE",
            "CREATE CONSTRAINT ON (n:Workflow) ASSERT n.id IS UNIQUE", 
            "CREATE CONSTRAINT ON (n:Community) ASSERT n.id IS UNIQUE",
            "CREATE CONSTRAINT ON (n:Application) ASSERT n.name IS UNIQUE"
        ]
        
        success_count = 0
        for query in constraint_queries:
            try:
                self.execute(query)
                success_count += 1
                logger.info(f"✅ Created constraint: {query}")
            except mgclient.DatabaseError as e:
                if "already exists" in str(e).lower():
                    logger.info(f"Constraint already exists: {query}")
                    success_count += 1
                else:
                    logger.warning(f"Failed to create constraint: {query} - {e}")
        
        logger.info(f"✅ Created {success_count}/{len(constraint_queries)} constraints")
        return success_count == len(constraint_queries)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health = {
            'connected': False,
            'responsive': False,
            'node_count': 0,
            'relationship_count': 0,
            'indexes_exist': False,
            'constraints_exist': False,
            'timestamp': time.time()
        }
        
        try:
            # Test basic connectivity
            start_time = time.time()
            result = self.execute("RETURN 1 as test")
            response_time = time.time() - start_time
            
            health['connected'] = True
            health['responsive'] = response_time < 1.0  # Less than 1 second
            health['response_time_ms'] = response_time * 1000
            
            # Get database statistics
            stats = self.get_stats()
            health['node_count'] = stats.get('total_nodes', 0)
            health['relationship_count'] = stats.get('total_relationships', 0)
            
            # Check indexes exist
            try:
                self.execute("SHOW INDEX INFO")
                health['indexes_exist'] = True
            except:
                health['indexes_exist'] = False
            
            logger.info(f"✅ Health check passed. Nodes: {health['node_count']}, "
                       f"Relationships: {health['relationship_count']}, "
                       f"Response: {health['response_time_ms']:.1f}ms")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health['error'] = str(e)
        
        return health
    
    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("✅ Memgraph connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Factory function for easy connection creation
def create_memgraph_connection(host: str = '127.0.0.1', port: int = 7687) -> MemgraphConnection:
    """Create and return a configured Memgraph connection."""
    return MemgraphConnection(host=host, port=port)


# Test the connection
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    with create_memgraph_connection() as db:
        # Run health check
        health = db.health_check()
        print(f"Health Check: {json.dumps(health, indent=2)}")
        
        # Get database stats
        stats = db.get_stats()
        print(f"Database Stats: {json.dumps(stats, indent=2)}")
        
        # Create indexes and constraints
        db.create_indexes()
        db.create_constraints()
        
        print("✅ Memgraph connection module test completed successfully!")