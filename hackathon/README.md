# GraphRAG Inference Hackathon - Medical Knowledge Benchmark

Three-pipeline benchmark comparing LLM-Only, Basic RAG, and GraphRAG on medical/pharmaceutical knowledge data.

## 🚀 **Quick Start - Refactored Structure**

### **Prerequisites**
- Python 3.10+
- Google API key (Gemini free tier)
- TigerGraph Savanna account
- `.env` file with credentials

### **Setup**

```bash
# 1. Install dependencies
pip install -r hackathon/requirements.txt

# 2. Set environment variables (SECURE - DO NOT commit these to git)
cp .env.example .env
# Edit .env with your API keys and TigerGraph credentials

# 3. Quick graph status check
python hackathon/check_graph_status.py

# 4. Graph construction (if needed)
python hackathon/load_documents.py         # Load documents
python hackathon/create_chunks.py          # Create semantic chunks
python hackathon/extract_entities.py       # Extract medical entities
python hackathon/extract_relationships.py  # Extract relationships

# 5. Validation
python hackathon/validate_graphrag.py      # Test GraphRAG queries

# 6. Deploy GraphRAG service (from repo root)
# Create a local config file:
cp hackathon/configs/server_config.json configs/server_config.json
# Edit configs/server_config.json with your Savanna hostname
docker compose up -d --build

# 7. Run the dashboard
streamlit run hackathon/dashboard/app.py
```

### **📁 New Project Structure**

```
hackathon/
├── .env*                              # 🔒 SECURE: Credentials (NEVER commit)
├── .env.example                       # Template for credentials
├── check_graph_status.py              # ✅ Convenience: Check graph state
├── load_documents.py                  # ✅ Convenience: Load documents
├── create_chunks.py                   # ✅ Convenience: Create semantic chunks
├── extract_entities.py                # ✅ Convenience: Extract entities
├── extract_relationships.py           # ✅ Convenience: Extract relationships
├── validate_graphrag.py               # ✅ Convenience: Validate GraphRAG queries
│
├── configs/                           # Configuration files
│   ├── server_config.json             # Tuned GraphRAG config
│   └── prompts/                       # Medical domain prompts
│
├── graph_construction/               # 🏗️ Graph building modules
│   ├── __init__.py
│   ├── load_documents.py              # Document loading logic
│   ├── semantic_chunking.py           # Text chunking logic
│   ├── entity_extraction.py          # Entity extraction logic
│   └── relationship_extraction.py     # Relationship extraction logic
│
├── validation/                        # ✅ Validation modules
│   ├── __init__.py
│   ├── check_current_state.py         # Graph state checking logic
│   └── graphrag_validation.py         # GraphRAG query validation logic
│
├── pipelines/                         # 🚀 Evaluation pipelines
│   ├── __init__.py
│   ├── llm_only.py                    # Pipeline 1: LLM-Only
│   ├── basic_rag.py                   # Pipeline 2: Basic RAG
│   └── graphrag_pipeline.py           # Pipeline 3: GraphRAG
│
├── evaluation/                        # 📈 Evaluation metrics
│   ├── __init__.py
│   ├── judge.py                       # LLM-as-a-Judge evaluation
│   └── bertscore_eval.py              # BERTScore evaluation
│
├── dashboard/                         # 🖥️ Comparison dashboard
│   └── app.py                         # Web application
│
├── scripts/                           # 🔧 Data fetching scripts
│   ├── fetch_expanded_fda.py          # FDA data fetching
│   ├── fetch_pubmed.py                # PubMed research fetching
│   └── process_medical_data.py        # Data processing logic
│
└── utils/                             # 🛠️ Utility modules
    ├── __init__.py
    ├── tigergraph_connection.py       # Connection management
    ├── document_loader.py             # Document loading utilities
    └── graph_operations.py            # Graph operation utilities

## 📊 **Current Dataset Status**

**✅ Complete Pipeline**:
- **Documents**: 1,135 documents (1.48M tokens - exceeds 2M requirement)
- **Chunks**: 1,475 semantic chunks (1.3 chunks/doc average)
- **Entities**: 93 medical entities (3.4 entities/chunk average)
- **Relationships**: 81 medical relationships (0.4 relationships/entity average)

**🔒 Security Features**:
- All credentials stored in `.env` file
- No hardcoded credentials in code
- Centralized connection management
- Environment-based configuration

**🏗️ Modular Design**:
- Reusable utility modules
- Clear separation of concerns
- Comprehensive error handling
- Type hints and documentation

## 💻 **Programmatic Usage**

```python
# Import modules programmatically
from graph_construction import (
    load_documents_to_graph,
    create_semantic_chunks,
    extract_medical_entities,
    extract_medical_relationships
)

from validation import (
    check_graph_state,
    validate_graphrag_queries
)

from utils import (
    get_connection_manager,
    get_graph_stats
)

# Use connection manager
conn_mgr = get_connection_manager()
stats = conn_mgr.get_graph_statistics()

# Run operations
state = check_graph_state()
result = validate_graphrag_queries()
```

## 🔧 **Configuration**

All configuration is done via `.env` file:

```bash
# TigerGraph Settings
TIGERGRAPH_HOST=https://your-host.tgcloud.io
TIGERGRAPH_GRAPH_NAME=graphRAG_hackathon
GSQL_SECRET=your_secret

# API Keys
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# Processing Settings
BATCH_SIZE=100
CHUNK_SIZE=1000
OVERLAP_SIZE=200
```

### Key Tuning Parameters (Path B)

| Parameter | Value | Rationale |
|---|---|---|
| `chunker` | semantic | Better topic boundaries in medical text |
| `chunk_size` | 2048 | Balances context richness vs precision |
| `top_k` | 3 | Fewer seeds = fewer tokens, graph traversal compensates |
| `num_hops` | 2 | 2 hops covers most medical relationships |
| `chunk_only` | true | Prevents pulling full documents |
| `token_limit` | 4096 | Hard context truncation for token reduction |
| `similarity_threshold` | 0.85 | Wider initial net, filtered by graph quality |

### Evaluation Targets

| Metric | Target | Bonus Threshold |
|---|---|---|
| LLM-as-a-Judge Pass Rate | >= 80% | >= 90% |
| BERTScore F1 (raw) | >= 0.80 | >= 0.88 |
| BERTScore F1 (rescaled) | >= 0.40 | >= 0.55 |
| Token Reduction vs Basic RAG | >= 40% | - |