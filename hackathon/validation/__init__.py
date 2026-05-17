"""
Validation Module

Handles validation and testing of the GraphRAG implementation:
- Graph state checking
- GraphRAG query validation
- Performance benchmarking
"""

from .check_current_state import check_graph_state
from .graphrag_validation import validate_graphrag_queries

__all__ = [
    'check_graph_state',
    'validate_graphrag_queries'
]