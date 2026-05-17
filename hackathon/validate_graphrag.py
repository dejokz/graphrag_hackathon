"""
Convenience wrapper for validating GraphRAG queries
Run this script to test your knowledge graph with drug mechanism questions
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Change to hackathon directory to ensure .env is found
os.chdir(str(Path(__file__).parent))

from validation.graphrag_validation import validate_graphrag_queries

if __name__ == "__main__":
    result = validate_graphrag_queries()
    sys.exit(0 if result.get('success', False) else 1)