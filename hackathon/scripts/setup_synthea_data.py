"""
Synthea Data Extraction Script

This script connects to the existing Synthea dataset in TigerGraph
and extracts relevant medical documents formatted for GraphRAG ingestion.

Focus areas: medications, conditions, drug-disease relationships
Target: 30-40 documents from Synthea
"""

import json
import os
from pathlib import Path
from typing import List, Dict
import pyTigerGraph as tg

# Configuration
SYNTHEA_BUCKET = "s3://tigergraph-public-data/Synthea/"
OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "synthea_documents.jsonl"


def connect_to_tigergraph() -> tg.TigerGraphConnection:
    """Connect to TigerGraph instance using environment variables."""
    conn = tg.TigerGraphConnection(
        host=os.getenv("TIGERGRAPH_HOSTNAME", "http://localhost:14240"),
        username=os.getenv("TIGERGRAPH_USERNAME", "tigergraph"),
        password=os.getenv("TIGERGRAPH_PASSWORD", "tigergraph"),
        graphname=os.getenv("TIGERGRAPH_GRAPHNAME", "Synthea")
    )

    # Connect and authenticate
    conn.connect()
    return conn


def extract_patient_records(conn: tg.TigerGraphConnection, limit: int = 15) -> List[Dict]:
    """Extract patient medical records formatted as documents."""
    documents = []

    # Query for patients with medications and conditions
    query = """
    SELECT
        p.id,
        p.given_name,
        p.family_name,
        p.birthdate,
        p.gender,
        p.race,
        p.ethnicity
    FROM Patient p
    LIMIT {}
    """.format(limit)

    try:
        patients = conn.runInterpretedQuery(query)

        for patient in patients:
            # Get patient's medications
            med_query = f"""
            SELECT
                m.description,
                m.start,
                m.stop,
                m.reason_description
            FROM Medication m
            WHERE m.patient_id = '{patient['id']}'
            """

            # Get patient's conditions
            cond_query = f"""
            SELECT
                c.description,
                c.start,
                c.stop
            FROM Condition c
            WHERE c.patient_id = '{patient['id']}'
            """

            try:
                medications = conn.runInterpretedQuery(med_query)
                conditions = conn.runInterpretedQuery(cond_query)

                # Create document from patient record
                doc_content = f"Patient Record: {patient['given_name']} {patient['family_name']}\n"
                doc_content += f"Demographics: {patient['gender']}, {patient['race']}, {patient['ethnicity']}\n"
                doc_content += f"Birthdate: {patient['birthdate']}\n\n"

                if medications:
                    doc_content += "Medications:\n"
                    for med in medications[:5]:  # Limit to 5 medications per patient
                        doc_content += f"- {med['description']}"
                        if med.get('reason_description'):
                            doc_content += f" (Reason: {med['reason_description']})"
                        doc_content += f" from {med['start']} to {med['stop']}\n"
                    doc_content += "\n"

                if conditions:
                    doc_content += "Medical Conditions:\n"
                    for cond in conditions[:5]:  # Limit to 5 conditions per patient
                        doc_content += f"- {cond['description']} from {cond['start']} to {cond['stop']}\n"

                document = {
                    "doc_id": f"synthea_patient_{patient['id']}",
                    "doc_type": "content",
                    "content": doc_content.strip()
                }
                documents.append(document)

            except Exception as e:
                print(f"Error processing patient {patient['id']}: {e}")
                continue

    except Exception as e:
        print(f"Error querying patients: {e}")

    return documents


def extract_drug_information(conn: tg.TigerGraphConnection, limit: int = 10) -> List[Dict]:
    """Extract drug and condition relationships from Synthea."""
    documents = []

    # Query for common medications and their associated conditions
    query = """
    SELECT
        m.description as medication,
        c.description as condition,
        COUNT(*) as frequency
    FROM Medication m
    JOIN Condition c ON m.patient_id = c.patient_id
    WHERE m.description IS NOT NULL AND c.description IS NOT NULL
    GROUP BY medication, condition
    ORDER BY frequency DESC
    LIMIT {}
    """.format(limit)

    try:
        drug_conditions = conn.runInterpretedQuery(query)

        for item in drug_conditions:
            doc_content = f"Drug-Condition Relationship: {item['medication']}\n"
            doc_content += f"Commonly prescribed for: {item['condition']}\n"
            doc_content += f"Frequency: {item['frequency']} patients\n"

            # Additional context about the medication
            med_details_query = f"""
            SELECT
                m.description,
                m.reason_description,
                COUNT(*) as total_prescriptions
            FROM Medication m
            WHERE m.description = '{item['medication'].replace("'", "''")}'
            GROUP BY m.description, m.reason_description
            LIMIT 5
            """

            try:
                med_details = conn.runInterpretedQuery(med_details_query)
                if med_details:
                    doc_content += "\nPrescription Reasons:\n"
                    for detail in med_details:
                        if detail.get('reason_description'):
                            doc_content += f"- {detail['reason_description']} ({detail['total_prescriptions']} prescriptions)\n"
            except:
                pass

            document = {
                "doc_id": f"synthea_drug_{item['medication'].replace(' ', '_').lower()[:50]}",
                "doc_type": "content",
                "content": doc_content.strip()
            }
            documents.append(document)

    except Exception as e:
        print(f"Error querying drug conditions: {e}")

    return documents


def extract_condition_patterns(conn: tg.TigerGraphConnection, limit: int = 10) -> List[Dict]:
    """Extract disease patterns and co-morbidities."""
    documents = []

    # Query for common conditions and their co-occurring conditions
    query = """
    SELECT
        c1.description as primary_condition,
        c2.description as comorbid_condition,
        COUNT(*) as co_occurrence
    FROM Condition c1
    JOIN Condition c2 ON c1.patient_id = c2.patient_id
    WHERE c1.description != c2.description
    GROUP BY primary_condition, comorbid_condition
    ORDER BY co_occurrence DESC
    LIMIT {}
    """.format(limit)

    try:
        comorbidities = conn.runInterpretedQuery(query)

        for item in comorbidities:
            doc_content = f"Condition Co-morbidity Pattern: {item['primary_condition']}\n"
            doc_content += f"Commonly co-occurs with: {item['comorbid_condition']}\n"
            doc_content += f"Co-occurrence frequency: {item['co_occurrence']} patients\n"

            document = {
                "doc_id": f"synthea_comorbidity_{item['primary_condition'].replace(' ', '_').lower()[:40]}",
                "doc_type": "content",
                "content": doc_content.strip()
            }
            documents.append(document)

    except Exception as e:
        print(f"Error querying comorbidities: {e}")

    return documents


def save_documents(documents: List[Dict], output_file: Path):
    """Save documents in JSONL format."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        for doc in documents:
            f.write(json.dumps(doc, ensure_ascii=False) + '\n')

    print(f"Saved {len(documents)} documents to {output_file}")


def main():
    """Main execution function."""
    print("Starting Synthea data extraction...")

    try:
        # Connect to TigerGraph
        print("Connecting to TigerGraph...")
        conn = connect_to_tigergraph()
        print("Connected successfully!")

        # Extract different types of documents
        all_documents = []

        print("\nExtracting patient records...")
        patient_docs = extract_patient_records(conn, limit=15)
        all_documents.extend(patient_docs)
        print(f"Extracted {len(patient_docs)} patient records")

        print("\nExtracting drug-condition relationships...")
        drug_docs = extract_drug_information(conn, limit=10)
        all_documents.extend(drug_docs)
        print(f"Extracted {len(drug_docs)} drug-condition documents")

        print("\nExtracting condition patterns...")
        condition_docs = extract_condition_patterns(conn, limit=10)
        all_documents.extend(condition_docs)
        print(f"Extracted {len(condition_docs)} condition pattern documents")

        # Save all documents
        print(f"\nTotal documents extracted: {len(all_documents)}")
        save_documents(all_documents, OUTPUT_FILE)

        print("\n✅ Synthea data extraction completed successfully!")

    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        raise


if __name__ == "__main__":
    main()
