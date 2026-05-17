"""
Expanded FDA Drug Labels API Fetcher
Fetches comprehensive drug information to reach 1M token target
"""

import requests
import json
import time
from typing import List, Dict, Optional
from pathlib import Path

class ExpandedFDADrugFetcher:
    """Fetches extensive drug data from FDA Drug Labels API"""

    BASE_URL = "https://api.fda.gov/drug/label.json"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GraphRAG-Hackathon/1.0 (Medical Research)'
        })

    def search_drugs(self, search_term: str, limit: int = 100) -> List[Dict]:
        """Search for drugs by name, condition, or manufacturer"""
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
        """Get detailed information for a specific drug"""
        results = self.search_drugs(drug_name, limit=5)
        if not results:
            return None
        return results[0]

    def extract_drug_info(self, drug_label: Dict) -> Dict:
        """Extract relevant information from FDA drug label"""
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

        # Handle nested openfda structure
        if 'openfda' in drug_label:
            openfda = drug_label['openfda']
            if 'brand_name' in openfda and isinstance(openfda['brand_name'], list) and len(openfda['brand_name']) > 0:
                info['drug_name'] = openfda['brand_name'][0]
            if 'generic_name' in openfda and isinstance(openfda['generic_name'], list) and len(openfda['generic_name']) > 0:
                info['generic_name'] = openfda['generic_name'][0]
            if 'manufacturer_name' in openfda and isinstance(openfda['manufacturer_name'], list) and len(openfda['manufacturer_name']) > 0:
                info['manufacturer'] = openfda['manufacturer_name'][0]

        # Helper function to extract fields
        def get_field(field_names: List[str]) -> str:
            for field in field_names:
                if field in drug_label:
                    value = drug_label[field]
                    if isinstance(value, list):
                        return ' '.join([str(item) for item in value[:3]])
                    return str(value)
            return ''

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
        """Create GraphRAG documents from drug information"""
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
        """Fetch data for multiple drugs and save to file"""
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
            time.sleep(0.3)

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
    """Main function to fetch comprehensive FDA drug data"""
    fetcher = ExpandedFDADrugFetcher()

    # Comprehensive drug list organized by therapeutic category
    # This should give us ~1500-2000 documents to reach 1M+ tokens
    drug_list = []

    # Cardiovascular medications (expanded)
    cardiovascular = [
        'lisinopril', 'losartan', 'valsartan', 'candesartan', 'irbesartan',
        'atorvastatin', 'simvastatin', 'rosuvastatin', 'pravastatin', 'fluvastatin',
        'metoprolol', 'propranolol', 'carvedilol', 'bisoprolol', 'atenolol',
        'amlodipine', 'diltiazem', 'verapamil', 'nifedipine', 'felodipine',
        'furosemide', 'hydrochlorothiazide', 'spironolactone', 'triamterene', 'amiloride',
        'clopidogrel', 'warfarin', 'dabigatran', 'rivaroxaban', 'apixaban',
        'digoxin', 'amiodarone', 'sotalol', 'flecainide', 'propafenone'
    ]

    # Diabetes and endocrine medications (expanded)
    diabetes_endocrine = [
        'metformin', 'sitagliptin', 'saxagliptin', 'linagliptin', 'alogliptin',
        'canagliflozin', 'dapagliflozin', 'empagliflozin', 'ertugliflozin',
        'semaglutide', 'liraglutide', 'exenatide', 'dulaglutide', 'lixisenatide',
        'insulin glargine', 'insulin detemir', 'insulin degludec', 'insulin lispro',
        'glipizide', 'glyburide', 'glimepiride', 'repaglinide', 'nateglinide',
        'pioglitazone', 'rosiglitazone', 'acarbose', 'miglitol', 'colesevelam',
        'levothyroxine', 'liothyronine', 'lithium', 'hydrocortisone', 'prednisone'
    ]

    # Antibiotics and antimicrobials (expanded)
    antibiotics = [
        'amoxicillin', 'ampicillin', 'penicillin', 'oxacillin', 'nafcillin',
        'azithromycin', 'clarithromycin', 'erythromycin', 'telithromycin',
        'doxycycline', 'minocycline', 'tetracycline', 'demeclocycline',
        'ciprofloxacin', 'levofloxacin', 'moxifloxacin', 'ofloxacin', 'gemifloxacin',
        'cephalexin', 'cefazolin', 'cefuroxime', 'ceftriaxone', 'cefixime',
        'clindamycin', 'vancomycin', 'linezolid', 'daptomycin',
        'trimethoprim', 'sulfamethoxazole', 'nitrofurantoin', 'fosfomycin',
        'metronidazole', 'clotrimazole', 'fluconazole', 'itraconazole', 'voriconazole'
    ]

    # Pain and inflammation medications (expanded)
    pain_inflammation = [
        'ibuprofen', 'naproxen', 'ketoprofen', 'diclofenac', 'indomethacin',
        'celecoxib', 'meloxicam', 'piroxicam', 'sulindac', 'etodolac',
        'tramadol', 'hydrocodone', 'oxycodone', 'morphine', 'fentanyl',
        'codeine', 'hydromorphone', 'methadone', 'buprenorphine', 'naloxone',
        'acetaminophen', 'aspirin', 'diflunisal', 'salsalate', 'choline salicylate',
        'gabapentin', 'pregabalin', 'duloxetine', 'amitriptyline', 'nortriptyline'
    ]

    # Respiratory medications (expanded)
    respiratory = [
        'albuterol', 'levalbuterol', 'terbutaline', 'formoterol', 'salmeterol',
        'fluticasone', 'budesonide', 'beclomethasone', 'mometasone', 'triamcinolone',
        'montelukast', 'zafirlukast', 'zileuton',
        'ipratropium', 'tiotropium', 'aclidinium', 'glycopyrrolate', 'umeclidinium',
        'theophylline', 'aminophylline',
        'fexofenadine', 'loratadine', 'cetirizine', 'levocetirizine', 'desloratadine',
        'omalizumab', 'mepolizumab', 'benralizumab', 'dupilumab'
    ]

    # Gastrointestinal medications (expanded)
    gastrointestinal = [
        'omeprazole', 'esomeprazole', 'lansoprazole', 'pantoprazole', 'rabeprazole',
        'famotidine', 'ranitidine', 'cimetidine', 'nizatidine',
        'ondansetron', 'granisetron', 'palonosetron', 'dolasetron',
        'metoclopramide', 'domperidone', 'erythromycin',
        'loperamide', 'diphenoxylate', 'bismuth subsalicylate',
        'docusate', 'polyethylene glycol', 'lactulose', 'senna', 'bisacodyl',
        'mesalamine', 'sulfasalazine', 'balsalazide', 'olsalazine'
    ]

    # Neurology and psychiatry medications (expanded)
    neurology_psychiatry = [
        'sertraline', 'fluoxetine', 'paroxetine', 'citalopram', 'escitalopram',
        'venlafaxine', 'duloxetine', 'desvenlafaxine', 'levomilnacipran',
        'bupropion', 'mirtazapine', 'nefazodone', 'trazodone',
        'alprazolam', 'lorazepam', 'clonazepam', 'diazepam', 'temazepam',
        'risperidone', 'olanzapine', 'quetiapine', 'aripiprazole', 'ziprasidone',
        'carbamazepine', 'valproate', 'lamotrigine', 'topiramate', 'levetiracetam',
        'donepezil', 'rivastigmine', 'galantamine', 'memantine',
        'modafinil', 'armodafinil', 'methylphenidate', 'amphetamine', 'lisdexamfetamine'
    ]

    # Oncology medications (expanded)
    oncology = [
        'tamoxifen', 'raloxifene', 'toremifene',
        'letrozole', 'anastrozole', 'exemestane',
        'paclitaxel', 'docetaxel', 'cabazitaxel', 'nab-paclitaxel',
        'doxorubicin', 'epirubicin', 'idarubicin', 'daunorubicin',
        'cisplatin', 'carboplatin', 'oxaliplatin',
        'cyclophosphamide', 'ifosfamide', 'chlorambucil', 'melphalan',
        'methotrexate', '5-fluorouracil', 'capecitabine', 'gemcitabine',
        'imatinib', 'dasatinib', 'nilotinib', 'bosutinib',
        'erlotinib', 'gefitinib', 'afatinib', 'osimertinib',
        'trastuzumab', 'pertuzumab', 'ado-trastuzumab', 'bevacizumab'
    ]

    # Combine all categories
    drug_list = (cardiovascular + diabetes_endocrine + antibiotics +
                pain_inflammation + respiratory + gastrointestinal +
                neurology_psychiatry + oncology)

    print(f"Total drugs to fetch: {len(drug_list)}")
    print(f"Expected documents: ~{len(drug_list) * 5}")
    print(f"Expected tokens: ~{len(drug_list) * 5 * 800:,}")

    # Fetch all drugs
    output_file = "hackathon/data/fda_expanded_documents.jsonl"
    document_count = fetcher.fetch_multiple_drugs(drug_list, output_file)

    print(f"\nTotal documents created: {document_count}")
    print(f"Estimated tokens: ~{document_count * 800:,}")
    print(f"Progress to 1M tokens: {document_count * 800 / 1000000:.1%}")

if __name__ == "__main__":
    main()