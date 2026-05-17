"""
Convenience script: Start the Streamlit comparison dashboard
Usage: python hackathon/start_dashboard.py
"""
import sys
import os
from pathlib import Path

# Add hackathon root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check required configuration
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not found in .env file")

graphrag_url = os.getenv("GRAPHRAG_BASE_URL")
if not graphrag_url:
    print("Warning: GRAPHRAG_BASE_URL not found in .env file, using default")

print("=== Starting GraphRAG Comparison Dashboard ===\n")
print(f"GraphRAG Service URL: {graphrag_url or 'http://localhost:8000'}")
print(f"Graph Name: {os.getenv('TIGERGRAPH_GRAPH_NAME', 'graphRAG_hackathon')}")
print(f"LLM Model: {os.getenv('DEFAULT_MODEL', 'gemini-2.0-flash')}")
print("\nDashboard will open at: http://localhost:8501")
print("Press Ctrl+C to stop the dashboard\n")

# Import and run Streamlit app
import subprocess

try:
    # Use subprocess to run streamlit to avoid import issues
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "hackathon/dashboard/app.py",
        "--server.port", "8501",
        "--server.headless", "true"
    ], check=True)
except KeyboardInterrupt:
    print("\nDashboard stopped by user")
except Exception as e:
    print(f"Error starting dashboard: {e}")
    sys.exit(1)