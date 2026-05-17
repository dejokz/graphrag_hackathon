# Medical Dataset Guide for GraphRAG Hackathon

## Overview

This guide explains the medical dataset created for the GraphRAG hackathon benchmark. The dataset focuses on **drug mechanisms and interactions** and is designed to evaluate three retrieval approaches: LLM-Only, Basic RAG, and GraphRAG.

## Dataset Summary

- **Total Documents:** 50
- **Primary Focus:** Drug mechanisms, targets, pathways, and interactions
- **Document Types:** Medical content (drug information, clinical contexts, pathophysiology)
- **Average Length:** 699 characters per document
- **Content Coverage:**
  - Drugs: 12/12 (100%) - All evaluation question drugs covered
  - Diseases: 6/7 (85.7%) - Major cardiovascular and metabolic conditions
  - Mechanisms: 9/10 (90%) - Primary drug action mechanisms
  - Proteins: 10/10 (100%) - Key drug targets and proteins

## Dataset Composition

### Drug Mechanism Documents (18 documents)

Comprehensive information about 12 key medications:

**Antidiabetic Agents:**
- Metformin (AMPK activator)
- Canagliflozin & Empagliflozin (SGLT2 inhibitors)
- Semaglutide (GLP-1 agonist)
- Insulin Glargine (basal insulin)

**Cardiovascular Medications:**
- Atorvastatin (HMG-CoA reductase inhibitor)
- Lisinopril (ACE inhibitor)
- Metoprolol (beta blocker)
- Amlodipine (calcium channel blocker)

**Other Medications:**
- Aspirin (COX inhibitor)
- Amoxicillin (penicillin antibiotic)
- Ciprofloxacin (fluoroquinolone antibiotic)

**Drug Class Comparisons:**
- ACE Inhibitors class overview
- Statins class overview
- SGLT2 Inhibitors class overview

### Medical Context Documents (32 documents)

Additional clinical and pharmacological context covering:

- **Disease Pathophysiology:** Type 2 diabetes, hypertension, heart failure
- **Treatment Guidelines:** Cardiovascular disease management, hypertension protocols
- **Pharmacology Principles:** Drug metabolism, renal dosing, drug interactions
- **Special Populations:** Geriatric pharmacology, pregnancy considerations
- **Clinical Topics:** Antibiotic resistance, pharmacogenomics, polypharmacy

## Key Drugs and Mechanisms Covered

### Metformin
- **Mechanism:** AMPK activation, inhibition of gluconeogenesis
- **Targets:** AMPK, mitochondrial complex I, GLUT4 transporters
- **Pathway:** AMPK signaling, insulin signaling pathway
- **Indications:** Type 2 Diabetes, PCOS

### ACE Inhibitors (Lisinopril)
- **Mechanism:** ACE inhibition, angiotensin II reduction
- **Targets:** Angiotensin-converting enzyme, angiotensin II receptors
- **Pathway:** Renin-angiotensin-aldosterone system (RAAS)
- **Indications:** Hypertension, heart failure, diabetic nephropathy

### SGLT2 Inhibitors (Canagliflozin, Empagliflozin)
- **Mechanism:** Renal glucose reabsorption inhibition
- **Targets:** SGLT2 transporter, SGLT1 transporter (canagliflozin)
- **Pathway:** Renal glucose handling, sodium-glucose transport
- **Indications:** Type 2 Diabetes, cardiovascular protection, renal protection

### Statins (Atorvastatin)
- **Mechanism:** HMG-CoA reductase inhibition
- **Targets:** HMG-CoA reductase, LDL receptors
- **Pathway:** Mevalonate pathway, cholesterol biosynthesis
- **Indications:** Hypercholesterolemia, cardiovascular risk reduction

## Graph Representation

### Entity Types (as defined in medical domain prompt)
- `drug` - Medications and pharmaceutical compounds
- `disease` - Medical conditions and disorders
- `protein` - Proteins, enzymes, and receptors
- `pathway` - Biological and metabolic pathways
- `side_effect` - Adverse effects and complications
- `population` - Patient groups and demographics
- `procedure` - Medical tests and diagnostic methods
- `organ` - Anatomical structures and systems

### Relationship Types
- `TREATS` (drug → disease)
- `INHIBITS` (drug → protein/pathway)
- `ACTIVATES` (drug → protein/pathway)
- `TARGETS` (drug → protein/pathway)
- `METABOLIZED_BY` (drug → organ)
- `CONTRAINDICATED_FOR` (drug → population)
- `ASSOCIATED_WITH` (gene → disease, disease → population)

## Usage Instructions

### 1. Dataset Files

The dataset consists of the following files:

- `hackathon/data/medical_documents.jsonl` - Main dataset (50 documents)
- `hackathon/data/drug_mechanisms.jsonl` - Drug-specific documents (18 documents)
- `hackathon/data/validation_report.txt` - Dataset quality validation report

### 2. Loading the Dataset

```python
import json
from pathlib import Path

# Load medical documents
data_file = Path("hackathon/data/medical_documents.jsonl")
documents = []

with open(data_file, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            documents.append(json.loads(line))

print(f"Loaded {len(documents)} medical documents")
```

### 3. Document Format

Each document follows this structure:

```json
{
  "doc_id": "drug_mechanism_metformin",
  "doc_type": "content",
  "content": "Drug Mechanism: Metformin\n\nMechanism of Action: Metformin works primarily..."
}
```

### 4. GraphRAG Ingestion

To ingest this dataset into GraphRAG:

```python
import pyTigerGraph as tg

# Connect to your TigerGraph instance
conn = tg.TigerGraphConnection(
    host="your_tigergraph_host",
    username="your_username",
    password="your_password",
    graphname="your_graph_name"
)

conn.connect()

# Initialize GraphRAG
conn.ai.initializeGraphRAG()

# Load documents
for doc in documents:
    conn.ai.upsertDocument(
        docId=doc['doc_id'],
        docType=doc['doc_type'],
        text=doc['content']
    )

# Update graph consistency
conn.ai.forceConsistencyUpdate("your_graph_name")
```

## Evaluation Coverage

The dataset is designed to support the 20 evaluation questions in `hackathon/eval_questions.json`, with particular strength in:

### Simple Questions (Drug Mechanisms)
- "What is the mechanism of action of metformin?"
- "How does aspirin work to prevent cardiovascular events?"
- "What is the primary target of statins?"

### Relational Questions (Drug-Drug/Drug-Disease)
- "How do ACE inhibitors and SGLT2 inhibitors work together?"
- "What is the relationship between metformin and AMPK?"
- "How do beta blockers differ from calcium channel blockers?"

### Multi-hop Questions (Complex Reasoning)
- "Explain the pathway from metformin to glucose control"
- "How do SGLT2 inhibitors provide cardiovascular benefits beyond glucose lowering?"
- "What are the connections between hypertension, diabetes, and cardiovascular disease?"

## Dataset Quality Metrics

### Coverage Analysis
- **Drug Coverage:** 100% (12/12 target drugs)
- **Disease Coverage:** 85.7% (6/7 major conditions)
- **Mechanism Coverage:** 90% (9/10 primary mechanisms)
- **Protein Coverage:** 100% (10/10 key targets)

### Content Quality
- **Average Document Length:** 699 characters
- **Content Range:** 466 - 958 characters
- **Total Content:** 34,943 characters
- **Document Types:** Consistent "content" type for uniform processing

### Validation Status
✅ **PASS** - Dataset meets all quality standards
- Document count within target range (50-100)
- Excellent drug and protein coverage
- Good mechanism and disease coverage
- Ready for GraphRAG ingestion

## Expected Graph Structure

When ingested into GraphRAG with the medical domain entity extraction prompt, this dataset should produce:

### Expected Entity Distribution
- **Drug Entities:** ~15-20 nodes (12 main drugs + drug classes)
- **Protein Entities:** ~10-15 nodes (HMG-CoA reductase, ACE, SGLT2, etc.)
- **Pathway Entities:** ~8-12 nodes (AMPK signaling, RAAS, etc.)
- **Disease Entities:** ~10-15 nodes (diabetes, hypertension, etc.)
- **Organ/Population Entities:** ~5-10 nodes (liver, kidneys, elderly, etc.)

### Expected Relationship Patterns
- **Drug → Protein:** INHIBITS, ACTIVATES, TARGETS relationships
- **Drug → Pathway:** Modulates biological pathways
- **Drug → Disease:** TREATS relationships
- **Protein → Pathway:** REGULATES relationships
- **Drug → Population:** CONTRAINDICATED_FOR relationships

## Performance Expectations

### Benchmark Targets
Based on the hackathon evaluation criteria:

- **LLM-as-a-Judge Pass Rate:** ≥80% (bonus: ≥90%)
- **BERTScore F1 (raw):** ≥0.80 (bonus: ≥0.88)
- **BERTScore F1 (rescaled):** ≥0.40 (bonus: ≥0.55)
- **Token Reduction vs Basic RAG:** ≥40%

### Expected Performance by Pipeline

**LLM-Only Pipeline:**
- Strength: Simple factual questions about well-known drugs
- Weakness: Complex relational and multi-hop reasoning
- Expected: Lower pass rate on complex questions

**Basic RAG Pipeline:**
- Strength: Retrieving relevant drug mechanism information
- Weakness: Missing connections between related concepts
- Expected: Moderate performance, higher token usage

**GraphRAG Pipeline:**
- Strength: Finding connected drug-protein-pathway relationships
- Weakness: May retrieve more context than needed
- Expected: Highest pass rate, significant token reduction vs Basic RAG

## Troubleshooting

### Common Issues

**Issue:** Low entity extraction quality
**Solution:** Ensure medical domain prompt is correctly configured in `hackathon/configs/prompts/entity_relationship_extraction.txt`

**Issue:** Missing drug-protein connections
**Solution:** Verify that relationship extraction is enabled and the similarity threshold is appropriate (0.85 recommended)

**Issue:** Poor retrieval on complex questions
**Solution:** Adjust retrieval parameters: increase `num_hops` to 2-3, ensure `top_k` is adequate (3-5)

**Issue:** High token usage
**Solution:** Enable `chunk_only: true`, reduce `top_k`, or increase `similarity_threshold`

## Maintenance and Updates

### Adding New Drugs

To add additional drug mechanism documents:

1. Update `hackathon/scripts/prepare_drug_mechanisms.py`
2. Add drug information to the `DRUG_MECHANISMS` dictionary
3. Run the script to regenerate `drug_mechanisms.jsonl`
4. Re-run validation script to integrate updated dataset

### Updating Clinical Context

To add new medical context documents:

1. Add content to the `medical_contexts` list in `validate_medical_dataset.py`
2. Re-run validation script to regenerate dataset
3. Verify coverage metrics remain acceptable

## References and Sources

This dataset was compiled from reputable medical and pharmacological sources:

- **Drug Mechanisms:** FDA drug labels, pharmaceutical documentation, clinical pharmacology references
- **Clinical Guidelines:** ACC/AHA, ADA, and other professional society guidelines
- **Pharmacology Principles:** Standard pharmacology textbooks and peer-reviewed literature
- **Medical Knowledge:** Clinical practice guidelines and evidenced-based medicine resources

## Contact and Support

For questions about this dataset or the GraphRAG hackathon:

- **Documentation:** See main README in `hackathon/README.md`
- **Evaluation Questions:** `hackathon/eval_questions.json`
- **Configuration:** `hackathon/configs/server_config.json`
- **Entity Extraction:** `hackathon/configs/prompts/entity_relationship_extraction.txt`

---

**Last Updated:** 2026-05-08
**Dataset Version:** 1.0
**Status:** Ready for GraphRAG Ingestion