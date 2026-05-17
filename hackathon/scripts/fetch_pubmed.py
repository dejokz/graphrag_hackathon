"""
PubMed Research Papers Fetcher
Fetches accurate medical research from PubMed (NIH/NLM)
"""

import requests
import json
import time
from typing import List, Dict, Optional
from pathlib import Path
import re

class PubMedFetcher:
    """Fetches medical research papers from PubMed"""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    API_KEY = ""  # Add your NCBI API key if you have one for higher rate limits

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GraphRAG-Hackathon/1.0 (Medical Research)'
        })

    def search_pubmed(self, query: str, max_results: int = 100, days_back: int = 365) -> List[str]:
        """
        Search PubMed for research papers

        Args:
            query: PubMed search query
            max_results: Maximum number of results
            days_back: Search papers from last N days (0 for all time)

        Returns:
            List of PubMed IDs (PMIDs)
        """
        search_url = f"{self.BASE_URL}esearch.fcgi"

        params = {
            'db': 'pubmed',
            'term': query,
            'retmode': 'json',
            'retmax': max_results,
            'sort': 'relevance'
        }

        # Add date filter if specified
        if days_back > 0:
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
            params['term'] = f"{query} AND ({cutoff_date}:3000[Date - Publication])"

        if self.API_KEY:
            params['api_key'] = self.API_KEY

        try:
            response = self.session.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('esearchresult', {}).get('idlist', [])
        except Exception as e:
            print(f"Error searching PubMed: {e}")
            return []

    def get_abstract_details(self, pmid: str) -> Optional[Dict]:
        """
        Get detailed information for a specific PubMed abstract

        Args:
            pmid: PubMed ID

        Returns:
            Abstract details or None if not found
        """
        fetch_url = f"{self.BASE_URL}efetch.fcgi"

        params = {
            'db': 'pubmed',
            'id': pmid,
            'retmode': 'json',
            'rettype': 'abstract'
        }

        if self.API_KEY:
            params['api_key'] = self.API_KEY

        try:
            response = self.session.get(fetch_url, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract the first result
            result = data.get('result', {})
            if pmid in result:
                return result[pmid]
            return None
        except Exception as e:
            print(f"Error fetching PMID {pmid}: {e}")
            return None

    def extract_paper_info(self, paper_data: Dict) -> Dict:
        """
        Extract relevant information from PubMed paper

        Args:
            paper_data: Raw PubMed paper data

        Returns:
            Structured paper information
        """
        info = {
            'pmid': paper_data.get('pmid', ''),
            'title': '',
            'abstract': '',
            'authors': [],
            'journal': '',
            'publication_date': '',
            'keywords': [],
            'doi': '',
            'publication_types': []
        }

        # Extract title
        if 'title' in paper_data:
            info['title'] = paper_data['title']

        # Extract abstract
        if 'abstract' in paper_data:
            abstract_text = paper_data['abstract']
            if isinstance(abstract_text, dict) and 'AbstractText' in abstract_text:
                abstract_parts = abstract_text['AbstractText']
                if isinstance(abstract_parts, list):
                    info['abstract'] = ' '.join([str(part) for part in abstract_parts])
                else:
                    info['abstract'] = str(abstract_parts)
            else:
                info['abstract'] = str(abstract_text)

        # Extract authors
        if 'authors' in paper_data:
            authors = paper_data['authors']
            if isinstance(authors, list):
                for author in authors[:10]:  # Limit to first 10 authors
                    if isinstance(author, dict):
                        name_parts = []
                        if 'lastname' in author:
                            name_parts.append(author['lastname'])
                        if 'forename' in author:
                            name_parts.append(author['forename'])
                        elif 'initials' in author:
                            name_parts.append(author['initials'])
                        if name_parts:
                            info['authors'].append(' '.join(name_parts))

        # Extract journal info
        if 'journal' in paper_data:
            journal = paper_data['journal']
            if isinstance(journal, dict):
                if 'title' in journal:
                    info['journal'] = journal['title']
                if 'pubdate' in journal:
                    pubdate = journal['pubdate']
                    if isinstance(pubdate, dict):
                        year = pubdate.get('year', '')
                        month = pubdate.get('month', '')
                        info['publication_date'] = f"{year} {month}".strip()

        # Extract keywords
        if 'keywords' in paper_data:
            keywords = paper_data['keywords']
            if isinstance(keywords, list):
                for keyword in keywords[:15]:  # Limit to first 15 keywords
                    if isinstance(keyword, dict) and '#text' in keyword:
                        info['keywords'].append(keyword['#text'])

        # Extract DOI
        if 'articleids' in paper_data:
            article_ids = paper_data['articleids']
            if isinstance(article_ids, list):
                for article_id in article_ids:
                    if isinstance(article_id, dict) and article_id.get('idtype') == 'doi':
                        info['doi'] = article_id.get('#text', '')
                        break

        # Extract publication types
        if 'publicationtypes' in paper_data:
            pub_types = paper_data['publicationtypes']
            if isinstance(pub_types, list):
                for pub_type in pub_types:
                    if isinstance(pub_type, dict) and '#text' in pub_type:
                        info['publication_types'].append(pub_type['#text'])

        return info

    def create_documents(self, paper_info: Dict, topic: str) -> List[Dict]:
        """
        Create GraphRAG documents from research paper

        Args:
            paper_info: Structured paper information
            topic: Topic for document organization

        Returns:
            List of documents in GraphRAG format
        """
        documents = []

        # Main abstract document
        if paper_info['abstract']:
            authors_text = ', '.join(paper_info['authors'][:5])  # First 5 authors
            if len(paper_info['authors']) > 5:
                authors_text += f" et al. ({len(paper_info['authors'])} authors total)"

            keywords_text = ', '.join(paper_info['keywords'][:10]) if paper_info['keywords'] else 'N/A'

            doc = {
                'doc_id': f"pubmed_{paper_info['pmid']}",
                'doc_type': 'content',
                'source': 'PubMed',
                'content': f"Research Paper: {paper_info['title']}\n"
                          f"Authors: {authors_text}\n"
                          f"Journal: {paper_info['journal']}\n"
                          f"Publication Date: {paper_info['publication_date']}\n"
                          f"PMID: {paper_info['pmid']}\n"
                          f"DOI: {paper_info['doi'] or 'N/A'}\n"
                          f"Publication Types: {', '.join(paper_info['publication_types'])}\n"
                          f"Keywords: {keywords_text}\n\n"
                          f"Abstract:\n{paper_info['abstract']}\n\n"
                          f"Source: PubMed (NIH/NLM) - Peer-reviewed Medical Research\n"
                          f"Topic: {topic}"
            }
            documents.append(doc)

        # Methodology document (if available from abstract structure)
        if 'methods' in paper_info['abstract'].lower() or 'methodology' in paper_info['abstract'].lower():
            # This is a simple heuristic - in reality, abstracts often don't separate methods
            pass

        return documents

    def fetch_research_by_topic(self, topics: List[str], output_file: str, papers_per_topic: int = 20) -> int:
        """
        Fetch research papers for multiple topics

        Args:
            topics: List of research topics
            papers_per_topic: Number of papers per topic
            output_file: Output file path

        Returns:
            Number of documents created
        """
        all_documents = []

        for topic in topics:
            print(f"Fetching papers for topic: {topic}")

            # Search for papers
            pmids = self.search_pubmed(topic, max_results=papers_per_topic)

            if not pmids:
                print(f"  No papers found for {topic}")
                continue

            print(f"  Found {len(pmids)} papers")

            # Fetch abstracts
            for i, pmid in enumerate(pmids):
                print(f"  Fetching abstract {i+1}/{len(pmids)}: PMID {pmid}")

                paper_data = self.get_abstract_details(pmid)
                if not paper_data:
                    continue

                # Extract and create documents
                paper_info = self.extract_paper_info(paper_data)
                documents = self.create_documents(paper_info, topic)
                all_documents.extend(documents)

                # Rate limiting - NCBI allows 3 requests per second without API key
                time.sleep(0.4)

        # Save to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for doc in all_documents:
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')

        print(f"\nCreated {len(all_documents)} documents from {len(topics)} topics")
        print(f"Saved to {output_file}")

        return len(all_documents)

def main():
    """Main function to fetch PubMed research"""
    fetcher = PubMedFetcher()

    # Medical research topics aligned with your dataset
    research_topics = [
        # Diabetes research
        'type 2 diabetes metformin mechanism',
        'SGLT2 inhibitors cardiovascular outcomes',
        'GLP-1 agonists diabetes treatment',

        # Cardiovascular research
        'ACE inhibitors hypertension mechanism',
        'statins cardiovascular prevention',
        'beta blockers heart failure',

        # Drug interactions and safety
        'drug-drug interactions cardiovascular medications',
        'adverse drug reactions diabetes medications',
        'pharmacogenomics drug response',

        # Clinical pharmacology
        'drug metabolism liver enzymes',
        'renal drug dosing elderly',
        'pharmacokinetics drug interactions',

        # Treatment guidelines
        'diabetes treatment guidelines',
        'hypertension management guidelines',
        'heart failure pharmacotherapy',

        # Emerging research
        'diabetes cardiovascular outcomes',
        'metformin AMPK mechanism',
        'SGLT2 inhibitors renal protection',

        # Drug classes
        'ACE inhibitors clinical trials',
        'statins mechanism action',
        'beta blockers cardiovascular',
    ]

    # Fetch research papers
    output_file = "hackathon/data/pubmed_research_documents.jsonl"
    document_count = fetcher.fetch_research_by_topic(research_topics, papers_per_topic=15, output_file=output_file)

    print(f"\nTotal documents created: {document_count}")
    print(f"Estimated tokens: ~{document_count * 1200} tokens")

if __name__ == "__main__":
    main()