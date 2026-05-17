"""
Convenience wrapper for extracting medical entities
Run this script to extract drugs, diseases, proteins, pathways, etc.
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Change to hackathon directory to ensure .env is found
os.chdir(str(Path(__file__).parent))

from graph_construction.entity_extraction import extract_medical_entities

if __name__ == "__main__":
    result = extract_medical_entities()
    sys.exit(0 if result.get('success', False) else 1)