"""
Convenience wrapper for loading documents into the graph
Run this script to load the expanded medical dataset into TigerGraph
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Change to hackathon directory to ensure .env is found
os.chdir(str(Path(__file__).parent))

from graph_construction.load_documents import load_documents_to_graph

if __name__ == "__main__":
    result = load_documents_to_graph()
    sys.exit(0 if result.get('success', False) else 1)