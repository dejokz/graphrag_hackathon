"""
Convenience wrapper for extracting medical relationships
Run this script to extract TREATS, INHIBITS, ACTIVATES, etc.
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Change to hackathon directory to ensure .env is found
os.chdir(str(Path(__file__).parent))

from graph_construction.relationship_extraction import extract_medical_relationships

if __name__ == "__main__":
    result = extract_medical_relationships()
    sys.exit(0 if result.get('success', False) else 1)