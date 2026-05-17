"""
Convenience wrapper for checking graph status
Run this script to see the current state of your medical knowledge graph
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Change to hackathon directory to ensure .env is found
os.chdir(str(Path(__file__).parent))

from validation.check_current_state import check_graph_state

if __name__ == "__main__":
    result = check_graph_state()
    sys.exit(0 if result.get('success', False) else 1)