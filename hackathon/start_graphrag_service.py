"""
Convenience script: Start the GraphRAG service locally
Usage: python hackathon/start_graphrag_service.py
"""
import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=== Starting GraphRAG Service ===")
print(f"Project root: {project_root}")
print(f"Graph name: {os.getenv('TIGERGRAPH_GRAPH_NAME', 'graphRAG_hackathon')}")
print(f"GraphRAG Base URL: {os.getenv('GRAPHRAG_BASE_URL', 'http://localhost:8000')}")
print("\nStarting service on http://localhost:8000")
print("Press Ctrl+C to stop the service\n")

try:
    # Start uvicorn server
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "graphrag.app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ], check=True)
except KeyboardInterrupt:
    print("\n\nGraphRAG service stopped by user")
except Exception as e:
    print(f"\nError starting GraphRAG service: {e}")
    sys.exit(1)