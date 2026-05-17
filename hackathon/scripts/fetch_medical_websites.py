"""
Medical Website Scraper
Fetches accurate medical information from reputable medical websites
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Optional
from pathlib import Path
import re

class MedicalWebsiteScraper:
    """Scrapes medical information from reputable websites"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def scrape_drugs_com(self, drug_name: str) -> Optional[Dict]:
        """
        Scrape drug information from Drugs.com

        Args:
            drug_name: Name of the drug

        Returns:
            Drug information or None if not found
        """
        url = f"https://www.drugs.com/{drug_name.lower().replace(' ', '-')}.html"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            drug_info = {
                'source': 'Drugs.com',
                'url': url,
                'drug_name': drug_name,
                'description': '',
                'side_effects': '',
                'interactions': '',
                'dosage': '',
                'warnings': '',
                'uses': ''
            }

            # Extract description
            description = soup.find('div', class_='drug-content')
            if description:
                drug_info['description'] = description.get_text(strip=True)[:2000]

            # Extract side effects
            side_effects = soup.find('h2', string=re.compile('Side Effects'))
            if side_effects:
                content = side_effects.find_next('div', class_='content-box')
                if content:
                    drug_info['side_effects'] = content.get_text(strip=True)[:1500]

            # Extract interactions
            interactions = soup.find('h2', string=re.compile('Drug Interactions'))
            if interactions:
                content = interactions.find_next('div', class_='content-box')
                if content:
                    drug_info['interactions'] = content.get_text(strip=True)[:1500]

            return drug_info

        except Exception as e:
            print(f"Error scraping Drugs.com for {drug_name}: {e}")
            return None

    def scrape_mayo_clinic(self, condition: str) -> Optional[Dict]:
        """
        Scrape disease/condition information from Mayo Clinic

        Args:
            condition: Name of the medical condition

        Returns:
            Condition information or None if not found
        """
        search_url = f"https://www.mayoclinic.org/diseases-conditions/{condition.lower().replace(' ', '-')}/symptoms-causes/syc-20350879"

        try:
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            condition_info = {
                'source': 'Mayo Clinic',
                'url': search_url,
                'condition': condition,
                'overview': '',
                'symptoms': '',
                'causes': '',
                'risk_factors': '',
                'complications': '',
                'treatment': ''
            }

            # Extract overview
            overview = soup.find('div', class_='content')
            if overview:
                condition_info['overview'] = overview.get_text(strip=True)[:2000]

            # Extract symptoms
            symptoms = soup.find('h2', string=re.compile('Symptoms'))
            if symptoms:
                content = symptoms.find_next('div', class_='content')
                if content:
                    condition_info['symptoms'] = content.get_text(strip=True)[:1500]

            return condition_info

        except Exception as e:
            print(f"Error scraping Mayo Clinic for {condition}: {e}")
            return None

    def scrape_medline_plus(self, topic: str) -> Optional[Dict]:
        """
        Scrape medical information from MedlinePlus (NIH)

        Args:
            topic: Medical topic

        Returns:
            Medical information or None if not found
        """
        search_url = f"https://medlineplus.gov/{topic.lower().replace(' ', '_')}.html"

        try:
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            topic_info = {
                'source': 'MedlinePlus',
                'url': search_url,
                'topic': topic,
                'summary': '',
                'causes': '',
                'symptoms': '',
                'treatment': '',
                'prevention': ''
            }

            # Extract main content
            main_content = soup.find('div', id='topic-summary')
            if main_content:
                topic_info['summary'] = main_content.get_text(strip=True)[:2000]

            # Try to find sections
            for section_name in ['causes', 'symptoms', 'treatment', 'prevention']:
                section = soup.find('h2', string=re.compile(section_name.capitalize()))
                if section:
                    content = section.find_next('div')
                    if content:
                        topic_info[section_name] = content.get_text(strip=True)[:1500]

            return topic_info

        except Exception as e:
            print(f"Error scraping MedlinePlus for {topic}: {e}")
            return None

    def create_drug_documents(self, drug_info: Dict) -> List[Dict]:
        """
        Create GraphRAG documents from drug information

        Args:
            drug_info: Drug information from scraping

        Returns:
            List of documents
        """
        documents = []
        drug_name = drug_info['drug_name']

        # Overview document
        if drug_info['description']:
            doc = {
                'doc_id': f"drugscom_{drug_name.lower().replace(' ', '_')}_overview",
                'doc_type': 'content',
                'source': 'Drugs.com',
                'content': f"Drug Overview: {drug_name}\n\n"
                          f"{drug_info['description']}\n\n"
                          f"Source: Drugs.com - Reputable Drug Information"
            }
            documents.append(doc)

        # Side effects document
        if drug_info['side_effects']:
            doc = {
                'doc_id': f"drugscom_{drug_name.lower().replace(' ', '_')}_side_effects",
                'doc_type': 'content',
                'source': 'Drugs.com',
                'content': f"Side Effects: {drug_name}\n\n"
                          f"{drug_info['side_effects']}\n\n"
                          f"Source: Drugs.com - Adverse Reaction Information"
            }
            documents.append(doc)

        # Interactions document
        if drug_info['interactions']:
            doc = {
                'doc_id': f"drugscom_{drug_name.lower().replace(' ', '_')}_interactions",
                'doc_type': 'content',
                'source': 'Drugs.com',
                'content': f"Drug Interactions: {drug_name}\n\n"
                          f"{drug_info['interactions']}\n\n"
                          f"Source: Drugs.com - Drug Interaction Data"
            }
            documents.append(doc)

        return documents

    def create_condition_documents(self, condition_info: Dict) -> List[Dict]:
        """
        Create GraphRAG documents from medical condition information

        Args:
            condition_info: Condition information from scraping

        Returns:
            List of documents
        """
        documents = []
        condition = condition_info['condition']

        # Overview document
        if condition_info['overview']:
            doc = {
                'doc_id': f"{condition_info['source'].lower()}_{condition.lower().replace(' ', '_')}_overview",
                'doc_type': 'content',
                'source': condition_info['source'],
                'content': f"Condition Overview: {condition}\n\n"
                          f"{condition_info['overview']}\n\n"
                          f"Source: {condition_info['source']} - Medical Reference"
            }
            documents.append(doc)

        # Symptoms document
        if condition_info['symptoms']:
            doc = {
                'doc_id': f"{condition_info['source'].lower()}_{condition.lower().replace(' ', '_')}_symptoms",
                'doc_type': 'content',
                'source': condition_info['source'],
                'content': f"Symptoms: {condition}\n\n"
                          f"{condition_info['symptoms']}\n\n"
                          f"Source: {condition_info['source']} - Clinical Information"
            }
            documents.append(doc)

        # Causes document
        if condition_info['causes']:
            doc = {
                'doc_id': f"{condition_info['source'].lower()}_{condition.lower().replace(' ', '_')}_causes",
                'doc_type': 'content',
                'source': condition_info['source'],
                'content': f"Causes: {condition}\n\n"
                          f"{condition_info['causes']}\n\n"
                          f"Source: {condition_info['source']} - Pathophysiology Information"
            }
            documents.append(doc)

        return documents

    def scrape_multiple_drugs(self, drug_list: List[str], output_file: str) -> int:
        """
        Scrape multiple drugs from Drugs.com

        Args:
            drug_list: List of drug names
            output_file: Output file path

        Returns:
            Number of documents created
        """
        all_documents = []

        for i, drug_name in enumerate(drug_list):
            print(f"Scraping {i+1}/{len(drug_list)}: {drug_name}")

            drug_info = self.scrape_drugs_com(drug_name)
            if not drug_info:
                print(f"  No data found for {drug_name}")
                continue

            documents = self.create_drug_documents(drug_info)
            all_documents.extend(documents)

            # Rate limiting
            time.sleep(1.0)

        # Save to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for doc in all_documents:
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')

        print(f"\nCreated {len(all_documents)} documents from {len(drug_list)} drugs")
        print(f"Saved to {output_file}")

        return len(all_documents)

    def scrape_multiple_conditions(self, condition_list: List[str], output_file: str) -> int:
        """
        Scrape multiple conditions from Mayo Clinic

        Args:
            condition_list: List of condition names
            output_file: Output file path

        Returns:
            Number of documents created
        """
        all_documents = []

        for i, condition in enumerate(condition_list):
            print(f"Scraping {i+1}/{len(condition_list)}: {condition}")

            # Try Mayo Clinic first, then MedlinePlus
            condition_info = self.scrape_mayo_clinic(condition)
            if not condition_info:
                condition_info = self.scrape_medline_plus(condition)

            if not condition_info:
                print(f"  No data found for {condition}")
                continue

            documents = self.create_condition_documents(condition_info)
            all_documents.extend(documents)

            # Rate limiting
            time.sleep(1.0)

        # Save to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for doc in all_documents:
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')

        print(f"\nCreated {len(all_documents)} documents from {len(condition_list)} conditions")
        print(f"Saved to {output_file}")

        return len(all_documents)

def main():
    """Main function to scrape medical websites"""
    scraper = MedicalWebsiteScraper()

    # Drugs to scrape from Drugs.com
    drug_list = [
        # Your existing drugs plus additional ones
        'metformin', 'lisinopril', 'atorvastatin', 'aspirin', 'amoxicillin',
        'canagliflozin', 'empagliflozin', 'semaglutide', 'metoprolol',
        'amlodipine', 'ciprofloxacin', 'insulin glargine',

        # Additional cardiovascular drugs
        'losartan', 'valsartan', 'carvedilol', 'diltiazem', 'furosemide',

        # Additional diabetes drugs
        'sitagliptin', 'exenatide', 'dapagliflozin', 'glipizide',

        # Additional antibiotics
        'azithromycin', 'doxycycline', 'levofloxacin', 'cephalexin',

        # Pain medications
        'ibuprofen', 'naproxen', 'celecoxib', 'tramadol',

        # Respiratory medications
        'albuterol', 'fluticasone', 'montelukast',

        # Gastrointestinal medications
        'omeprazole', 'pantoprazole', 'famotidine',

        # Mental health medications
        'sertraline', 'fluoxetine', 'gabapentin', 'pregabalin',
    ]

    # Medical conditions to scrape
    condition_list = [
        'type 2 diabetes',
        'hypertension',
        'heart failure',
        'high cholesterol',
        'kidney disease',
        'liver disease',
        'depression',
        'anxiety',
        'chronic pain',
        'asthma',
        'copd',
        'arthritis',
        'infection',
        'pneumonia',
    ]

    # Scrape drugs
    print("Scraping drug information from Drugs.com...")
    drugs_output = "hackathon/data/drugscom_documents.jsonl"
    drug_docs = scraper.scrape_multiple_drugs(drug_list, drugs_output)

    # Scrape conditions
    print("\nScraping condition information from Mayo Clinic/MedlinePlus...")
    conditions_output = "hackathon/data/condition_documents.jsonl"
    condition_docs = scraper.scrape_multiple_conditions(condition_list, conditions_output)

    total_docs = drug_docs + condition_docs
    print(f"\nTotal documents created: {total_docs}")
    print(f"Estimated tokens: ~{total_docs * 900} tokens")

if __name__ == "__main__":
    main()