"""
TigerGraph Connection Utility Module

Provides centralized connection management and common operations
for TigerGraph GraphRAG applications.
"""

import pyTigerGraph as tg
import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TigerGraphConnectionManager:
    """Manages TigerGraph connections with environment-based configuration"""

    def __init__(self, host: Optional[str] = None, graph_name: Optional[str] = None,
                 gsql_secret: Optional[str] = None, api_token: Optional[str] = None):
        """
        Initialize connection manager with optional parameters

        Args:
            host: TigerGraph host URL (defaults to env var TIGERGRAPH_HOST)
            graph_name: Graph name (defaults to env var TIGERGRAPH_GRAPH_NAME)
            gsql_secret: GSQL secret (defaults to env var GSQL_SECRET)
            api_token: API token (defaults to env var API_TOKEN)
        """
        self.host = host or os.getenv('TIGERGRAPH_HOST')
        self.graph_name = graph_name or os.getenv('TIGERGRAPH_GRAPH_NAME')
        self.gsql_secret = gsql_secret or os.getenv('GSQL_SECRET')
        self.api_token = api_token or os.getenv('API_TOKEN')

        if not all([self.host, self.graph_name, self.gsql_secret]):
            raise ValueError("Missing required configuration. Please set TIGERGRAPH_HOST, "
                           "TIGERGRAPH_GRAPH_NAME, and GSQL_SECRET in .env file")

        self._connection: Optional[tg.TigerGraphConnection] = None
        self._api_token: Optional[str] = None

    def get_connection(self, use_global: bool = False) -> tg.TigerGraphConnection:
        """
        Get or create TigerGraph connection

        Args:
            use_global: If True, connect to global context (for admin operations)

        Returns:
            TigerGraphConnection object
        """
        if self._connection is None:
            self._connection = self._create_connection(use_global)
        return self._connection

    def _create_connection(self, use_global: bool = False) -> tg.TigerGraphConnection:
        """Create a new TigerGraph connection"""
        graph = "" if use_global else self.graph_name

        if self.api_token:
            # Use provided API token
            return tg.TigerGraphConnection(
                host=self.host,
                graphname=graph,
                apiToken=self.api_token,
                tgCloud=True
            )
        elif self.gsql_secret:
            # Use GSQL secret to get token
            temp_conn = tg.TigerGraphConnection(
                host=self.host,
                graphname="global",
                gsqlSecret=self.gsql_secret,
                tgCloud=True
            )

            token, _ = temp_conn.getToken(self.gsql_secret)
            self._api_token = token

            return tg.TigerGraphConnection(
                host=self.host,
                graphname=graph,
                gsqlSecret=self.gsql_secret,
                apiToken=token,
                tgCloud=True
            )
        else:
            raise ValueError("Either API token or GSQL secret must be provided")

    def get_token(self) -> str:
        """
        Get API token (creates new connection if needed)

        Returns:
            API token string
        """
        if self._api_token is None:
            conn = self.get_connection(use_global=True)
            self._api_token = conn.getToken(self.gsql_secret)[0]
        return self._api_token

    def test_connection(self) -> bool:
        """
        Test if connection is working

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            conn = self.get_connection()
            result = conn.echo()
            print(f"SUCCESS Connection successful! Echo: {result}")
            return True
        except Exception as e:
            print(f"FAILED Connection failed: {e}")
            return False

    def list_graphs(self) -> list:
        """
        List all available graphs

        Returns:
            List of graph names
        """
        try:
            conn = self.get_connection(use_global=True)
            graphs = conn.listGraphs()
            print(f"Available graphs: {graphs}")
            return graphs
        except Exception as e:
            print(f"Failed to list graphs: {e}")
            return []

    def run_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Run a GSQL query

        Args:
            query: GSQL query string
            params: Query parameters (optional)

        Returns:
            Query result
        """
        conn = self.get_connection()
        return conn.runInterpretedQuery(query, params=params)

    def get_vertex_count(self, vertex_type: str) -> int:
        """
        Get count of vertices of a specific type

        Args:
            vertex_type: Name of vertex type

        Returns:
            Number of vertices
        """
        try:
            conn = self.get_connection()
            return conn.getVertexCount(vertex_type)
        except Exception as e:
            print(f"Error getting vertex count for {vertex_type}: {e}")
            return 0

    def get_edge_count(self, edge_type: str) -> int:
        """
        Get count of edges of a specific type

        Args:
            edge_type: Name of edge type

        Returns:
            Number of edges
        """
        try:
            conn = self.get_connection()
            return conn.getEdgeCount(edge_type)
        except Exception as e:
            print(f"Error getting edge count for {edge_type}: {e}")
            return 0

    def get_graph_statistics(self) -> Dict[str, int]:
        """
        Get comprehensive graph statistics using individual count methods

        Returns:
            Dictionary with vertex and edge counts
        """
        result = {
            'vertices': {},
            'edges': {},
            'total_vertices': 0,
            'total_edges': 0
        }

        try:
            conn = self.get_connection()

            # Get schema to know what vertex/edge types exist
            schema = conn.getSchema()

            # Get vertex counts
            if 'VertexTypes' in schema:
                for vtype in schema['VertexTypes']:
                    vtype_name = vtype.get('Name', 'unknown')
                    count = self.get_vertex_count(vtype_name)
                    result['vertices'][vtype_name] = count
                    result['total_vertices'] += count

            # Get edge counts
            if 'EdgeTypes' in schema:
                for etype in schema['EdgeTypes']:
                    etype_name = etype.get('Name', 'unknown')
                    count = self.get_edge_count(etype_name)
                    result['edges'][etype_name] = count
                    result['total_edges'] += count

            return result

        except Exception as e:
            print(f"Error getting graph statistics: {e}")
            # Fallback: try to get specific known types
            known_vertices = ['DrugDoc', 'DrugChunk', 'DrugEntity', 'DrugRelation']
            known_edges = ['DOC_HAS_CHUNK', 'CHUNK_HAS_ENTITY', 'ENTITY_RELATED_TO',
                          'CHUNK_MENTIONS_RELATION', 'DOC_HAS_ENTITY']

            for vtype in known_vertices:
                count = self.get_vertex_count(vtype)
                if count > 0:
                    result['vertices'][vtype] = count
                    result['total_vertices'] += count

            for etype in known_edges:
                count = self.get_edge_count(etype)
                if count > 0:
                    result['edges'][etype] = count
                    result['total_edges'] += count

            return result

    def upsert_vertex(self, vertex_type: str, vertex_id: str, attributes: Dict[str, Any]) -> bool:
        """
        Upsert a vertex into the graph

        Args:
            vertex_type: Type of vertex
            vertex_id: Unique identifier for the vertex
            attributes: Dictionary of vertex attributes

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_connection()
            conn.upsertVertex(vertex_type, vertex_id, attributes)
            return True
        except Exception as e:
            print(f"Error upserting vertex {vertex_id}: {e}")
            return False

    def upsert_edge(self, edge_type: str, source_type: str, source_id: str,
                   target_type: str, target_id: str, attributes: Optional[Dict[str, Any]] = None) -> bool:
        """
        Upsert an edge into the graph

        Args:
            edge_type: Type of edge
            source_type: Type of source vertex
            source_id: ID of source vertex
            target_type: Type of target vertex
            target_id: ID of target vertex
            attributes: Dictionary of edge attributes (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_connection()
            conn.upsertEdge(
                edge_type,
                source_type, source_id,
                target_type, target_id,
                attributes
            )
            return True
        except Exception as e:
            print(f"Error upserting edge {edge_type}: {e}")
            return False


def get_connection_manager() -> TigerGraphConnectionManager:
    """
    Convenience function to get a connection manager with default configuration

    Returns:
        TigerGraphConnectionManager instance
    """
    return TigerGraphConnectionManager()


# Convenience functions for quick access
def get_connection(use_global: bool = False) -> tg.TigerGraphConnection:
    """Get a TigerGraph connection with default configuration"""
    return get_connection_manager().get_connection(use_global)


def test_connection() -> bool:
    """Test the default connection"""
    return get_connection_manager().test_connection()


def get_graph_stats() -> Dict[str, int]:
    """Get graph statistics using default configuration"""
    return get_connection_manager().get_graph_statistics()