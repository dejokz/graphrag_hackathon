"""
FDA Drug Labels API Fetcher
Fetches accurate drug information from official FDA sources
"""

import requests
import json
import time
from typing import List, Dict, Optional
from pathlib import Path

class FDADrugFetcher:
    """Fetches drug data from FDA Drug Labels API"""

    BASE_URL = "https://api.fda.gov/drug/label.json"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GraphRAG-Hackathon/1.0 (Medical Research)'
        })

    def search_drugs(self, search_term: str, limit: int = 100) -> List[Dict]:
        """
        Search for drugs by name, condition, or manufacturer

        Args:
            search_term: Drug name, condition, or manufacturer
            limit: Maximum number of results

        Returns:
            List of drug label data
        """
        params = {
            'search': search_term,
            'limit': limit
        }

        try:
            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])
        except Exception as e:
            print(f"Error searching for '{search_term}': {e}")
            return []

    def get_drug_details(self, drug_name: str) -> Optional[Dict]:
        """
        Get detailed information for a specific drug

        Args:
            drug_name: Exact or partial drug name

        Returns:
            Drug label data or None if not found
        """
        results = self.search_drugs(drug_name, limit=5)
        if not results:
            return None

        # Return the most relevant result (first one)
        return results[0]

    def extract_drug_info(self, drug_label: Dict) -> Dict:
        """
        Extract relevant information from FDA drug label

        Args:
            drug_label: Raw FDA drug label data

        Returns:
            Structured drug information
        """
        info = {
            'source': 'FDA',
            'drug_name': '',
            'generic_name': '',
            'manufacturer': '',
            'indications': '',
            'mechanism_of_action': '',
            'contraindications': '',
            'warnings': '',
            'adverse_reactions': '',
            'drug_interactions': '',
            'dosage': '',
            'pharmacology': ''
        }

        # Extract fields with fallbacks
        def get_field(field_names: List[str]) -> str:
            for field in field_names:
                if field in drug_label:
                    value = drug_label[field]
                    if isinstance(value, list):
                        return ' '.join([str(item) for item in value[:3]])  # First 3 items
                    return str(value)
            return ''

        # Handle nested openfda structure
        if 'openfda' in drug_label:
            openfda = drug_label['openfda']
            if 'brand_name' in openfda and isinstance(openfda['brand_name'], list) and len(openfda['brand_name']) > 0:
                info['drug_name'] = openfda['brand_name'][0]
            if 'generic_name' in openfda and isinstance(openfda['generic_name'], list) and len(openfda['generic_name']) > 0:
                info['generic_name'] = openfda['generic_name'][0]
            if 'manufacturer_name' in openfda and isinstance(openfda['manufacturer_name'], list) and len(openfda['manufacturer_name']) > 0:
                info['manufacturer'] = openfda['manufacturer_name'][0]
        info['indications'] = get_field(['indications_and_usage'])
        info['mechanism_of_action'] = get_field(['mechanism_of_action'])
        info['contraindications'] = get_field(['contraindications'])
        info['warnings'] = get_field(['warnings_and_precautions', 'boxed_warning'])
        info['adverse_reactions'] = get_field(['adverse_reactions'])
        info['drug_interactions'] = get_field(['drug_interactions'])
        info['dosage'] = get_field(['dosage_and_administration'])
        info['pharmacology'] = get_field(['clinical_pharmacology'])

        return info

    def create_documents(self, drug_info: Dict, drug_name: str) -> List[Dict]:
        """
        Create GraphRAG documents from drug information

        Args:
            drug_info: Structured drug information
            drug_name: Name for document IDs

        Returns:
            List of documents in GraphRAG format
        """
        documents = []

        # Main drug overview document
        if drug_info['indications'] or drug_info['mechanism_of_action']:
            doc = {
                'doc_id': f"fda_{drug_name.lower()}_overview",
                'doc_type': 'content',
                'source': 'FDA Drug Label',
                'content': f"Drug: {drug_info['drug_name'] or drug_name}\n"
                          f"Generic Name: {drug_info['generic_name'] or 'N/A'}\n"
                          f"Manufacturer: {drug_info['manufacturer'] or 'N/A'}\n\n"
                          f"Indications and Usage:\n{drug_info['indications']}\n\n"
                          f"Mechanism of Action:\n{drug_info['mechanism_of_action']}\n\n"
                          f"Source: FDA Drug Labels API - Official FDA Information"
            }
            documents.append(doc)

        # Contraindications and warnings document
        if drug_info['contraindications'] or drug_info['warnings']:
            doc = {
                'doc_id': f"fda_{drug_name.lower()}_safety",
                'doc_type': 'content',
                'source': 'FDA Drug Label',
                'content': f"Drug Safety Profile: {drug_info['drug_name'] or drug_name}\n\n"
                          f"Contraindications:\n{drug_info['contraindications']}\n\n"
                          f"Warnings and Precautions:\n{drug_info['warnings']}\n\n"
                          f"Source: FDA Drug Labels API - Official FDA Safety Information"
            }
            documents.append(doc)

        # Adverse reactions document
        if drug_info['adverse_reactions']:
            doc = {
                'doc_id': f"fda_{drug_name.lower()}_adverse",
                'doc_type': 'content',
                'source': 'FDA Drug Label',
                'content': f"Adverse Reactions: {drug_info['drug_name'] or drug_name}\n\n"
                          f"{drug_info['adverse_reactions']}\n\n"
                          f"Source: FDA Drug Labels API - Official FDA Adverse Event Data"
            }
            documents.append(doc)

        # Drug interactions document
        if drug_info['drug_interactions']:
            doc = {
                'doc_id': f"fda_{drug_name.lower()}_interactions",
                'doc_type': 'content',
                'source': 'FDA Drug Label',
                'content': f"Drug Interactions: {drug_info['drug_name'] or drug_name}\n\n"
                          f"{drug_info['drug_interactions']}\n\n"
                          f"Source: FDA Drug Labels API - Official FDA Interaction Data"
            }
            documents.append(doc)

        # Pharmacology document
        if drug_info['pharmacology'] or drug_info['dosage']:
            doc = {
                'doc_id': f"fda_{drug_name.lower()}_pharmacology",
                'doc_type': 'content',
                'source': 'FDA Drug Label',
                'content': f"Clinical Pharmacology: {drug_info['drug_name'] or drug_name}\n\n"
                          f"Pharmacology:\n{drug_info['pharmacology']}\n\n"
                          f"Dosage and Administration:\n{drug_info['dosage']}\n\n"
                          f"Source: FDA Drug Labels API - Official FDA Pharmacology Data"
            }
            documents.append(doc)

        return documents

    def fetch_multiple_drugs(self, drug_list: List[str], output_file: str) -> int:
        """
        Fetch data for multiple drugs and save to file

        Args:
            drug_list: List of drug names to fetch
            output_file: Output file path

        Returns:
            Number of documents created
        """
        all_documents = []

        for i, drug_name in enumerate(drug_list):
            print(f"Fetching {i+1}/{len(drug_list)}: {drug_name}")

            # Get drug data
            drug_label = self.get_drug_details(drug_name)
            if not drug_label:
                print(f"  No data found for {drug_name}")
                continue

            # Extract and create documents
            drug_info = self.extract_drug_info(drug_label)
            documents = self.create_documents(drug_info, drug_name)
            all_documents.extend(documents)

            # Rate limiting - be respectful to the API
            time.sleep(0.5)

        # Save to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for doc in all_documents:
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')

        print(f"Created {len(all_documents)} documents from {len(drug_list)} drugs")
        print(f"Saved to {output_file}")

        return len(all_documents)

def main():
    """Main function to fetch FDA drug data"""
    fetcher = FDADrugFetcher()

    # Expanded list of drugs to fetch (mix of your existing + new ones)
    drug_list = [
        # Your existing drugs
        'metformin', 'lisinopril', 'atorvastatin', 'aspirin', 'amoxicillin',
        'canagliflozin', 'empagliflozin', 'semaglutide', 'metoprolol',
        'amlodipine', 'ciprofloxacin', 'insulin glargine',

        # Cardiovascular drugs (expanded)
        'losartan', 'valsartan', 'carvedilol', 'diltiazem', 'verapamil',
        'furosemide', 'spironolactone', 'digoxin', 'warfarin', 'clopidogrel',

        # Diabetes drugs (expanded)
        'sitagliptin', 'exenatide', 'liraglutide', 'dapagliflozin',
        'glipizide', 'glyburide', 'pioglitazone', 'rosiglitazone',

        # Antibiotics (expanded)
        'azithromycin', 'doxycycline', 'levofloxacin', 'cephalexin',
        'clindamycin', 'trimethoprim', 'sulfamethoxazole',

        # Pain/Inflammation
        'ibuprofen', 'naproxen', 'celecoxib', 'tramadol', 'hydrocodone',

        # Respiratory
        'albuterol', 'fluticasone', 'montelukast', 'ipratropium',

        # Gastrointestinal
        'omeprazole', 'pantoprazole', 'famotidine', 'ondansetron',

        # Neurology/Psychiatry
        'sertraline', 'fluoxetine', 'escitalopram', 'duloxetine',
        'gabapentin', 'pregabalin', 'alprazolam', 'lorazepam',

        # Oncology (common)
        'tamoxifen', 'letrozole', 'anastrozole', 'paclitaxel',
    ]

    # Fetch all drugs
    output_file = "hackathon/data/fda_drug_documents.jsonl"
    document_count = fetcher.fetch_multiple_drugs(drug_list, output_file)

    print(f"\nTotal documents created: {document_count}")
    print(f"Estimated tokens: ~{document_count * 800} tokens")

if __name__ == "__main__":
    main()