"""
Convenience wrapper for creating semantic chunks
Run this script to chunk documents into smaller pieces for better retrieval
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Change to hackathon directory to ensure .env is found
os.chdir(str(Path(__file__).parent))

from graph_construction.semantic_chunking import create_semantic_chunks

if __name__ == "__main__":
    result = create_semantic_chunks()
    sys.exit(0 if result.get('success', False) else 1)