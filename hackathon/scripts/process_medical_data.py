"""
Medical Data Processor and Validator
Processes fetched medical data and validates accuracy for GraphRAG
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple
import hashlib

class MedicalDataProcessor:
    """Processes and validates medical data for GraphRAG"""

    def __init__(self):
        self.validation_errors = []
        self.processing_stats = {
            'total_documents': 0,
            'valid_documents': 0,
            'invalid_documents': 0,
            'duplicate_documents': 0,
            'total_characters': 0,
            'estimated_tokens': 0
        }

    def load_jsonl(self, file_path: str) -> List[Dict]:
        """Load documents from JSONL file"""
        documents = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        documents.append(json.loads(line))
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
        return documents

    def validate_document(self, doc: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a medical document for quality and accuracy

        Args:
            doc: Document to validate

        Returns:
            (is_valid, list of errors)
        """
        errors = []

        # Required fields
        required_fields = ['doc_id', 'doc_type', 'content']
        for field in required_fields:
            if field not in doc:
                errors.append(f"Missing required field: {field}")

        # Content validation
        if 'content' in doc:
            content = doc['content']

            # Minimum content length
            if len(content) < 100:
                errors.append(f"Content too short: {len(content)} characters")

            # Maximum content length (increased for comprehensive medical data)
            if len(content) > 20000:
                errors.append(f"Content too long: {len(content)} characters")

            # Check for empty or whitespace-only content
            if not content.strip():
                errors.append("Content is empty or whitespace only")

            # Check for basic medical content indicators
            medical_keywords = ['drug', 'medication', 'treatment', 'patient', 'dose',
                              'effect', 'interaction', 'mechanism', 'clinical', 'medical',
                              'therapy', 'pharmacology', 'symptom', 'disease', 'condition']

            # Only check if content is substantial
            if len(content) > 200:
                has_medical_content = any(keyword.lower() in content.lower()
                                        for keyword in medical_keywords)
                if not has_medical_content:
                    errors.append("Content appears to lack medical terminology")

        # Check for proper source attribution
        if 'source' not in doc or not doc['source']:
            errors.append("Missing or empty source field")

        # Check doc_id format
        if 'doc_id' in doc:
            doc_id = doc['doc_id']
            if not re.match(r'^[a-zA-Z0-9_\-]+$', doc_id):
                errors.append(f"Invalid doc_id format: {doc_id}")

        is_valid = len(errors) == 0
        return is_valid, errors

    def clean_content(self, content: str) -> str:
        """
        Clean and normalize content

        Args:
            content: Raw content

        Returns:
            Cleaned content
        """
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Multiple empty lines to double
        content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces to single

        # Remove special characters that might cause issues
        content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)

        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        # Strip leading/trailing whitespace
        content = content.strip()

        return content

    def detect_duplicates(self, documents: List[Dict]) -> List[Dict]:
        """
        Detect and remove duplicate documents

        Args:
            documents: List of documents

        Returns:
            List of unique documents
        """
        seen_hashes = set()
        unique_documents = []

        for doc in documents:
            # Create hash based on content and doc_id
            content = doc.get('content', '')
            doc_id = doc.get('doc_id', '')

            # Normalize content for comparison
            normalized_content = self.clean_content(content.lower())
            content_hash = hashlib.md5(f"{doc_id}:{normalized_content}".encode()).hexdigest()

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_documents.append(doc)
            else:
                self.processing_stats['duplicate_documents'] += 1

        return unique_documents

    def process_document(self, doc: Dict) -> Dict:
        """
        Process and enhance a document

        Args:
            doc: Original document

        Returns:
            Processed document
        """
        processed_doc = doc.copy()

        # Clean content
        if 'content' in processed_doc:
            processed_doc['content'] = self.clean_content(processed_doc['content'])

        # Ensure required fields have defaults
        processed_doc.setdefault('doc_type', 'content')
        processed_doc.setdefault('source', 'Unknown')

        # Add processing timestamp
        from datetime import datetime
        processed_doc['processed_at'] = datetime.now().isoformat()

        # Calculate character count
        content = processed_doc.get('content', '')
        processed_doc['character_count'] = len(content)

        # Estimate token count (roughly 4 chars per token)
        processed_doc['estimated_tokens'] = max(1, len(content) // 4)

        return processed_doc

    def process_dataset(self, input_files: List[str], output_file: str) -> Dict:
        """
        Process multiple input files into a unified dataset

        Args:
            input_files: List of input file paths
            output_file: Output file path

        Returns:
            Processing statistics
        """
        all_documents = []

        # Load all documents
        for input_file in input_files:
            print(f"Loading {input_file}...")
            documents = self.load_jsonl(input_file)
            all_documents.extend(documents)
            print(f"  Loaded {len(documents)} documents")

        self.processing_stats['total_documents'] = len(all_documents)

        # Remove duplicates
        print("Removing duplicates...")
        all_documents = self.detect_duplicates(all_documents)
        print(f"  Removed {self.processing_stats['duplicate_documents']} duplicates")

        # Validate and process documents
        print("Validating and processing documents...")
        valid_documents = []

        for doc in all_documents:
            # Validate
            is_valid, errors = self.validate_document(doc)
            if not is_valid:
                self.validation_errors.append({
                    'doc_id': doc.get('doc_id', 'unknown'),
                    'errors': errors
                })
                self.processing_stats['invalid_documents'] += 1
                continue

            # Process
            processed_doc = self.process_document(doc)
            valid_documents.append(processed_doc)

            # Update statistics
            self.processing_stats['valid_documents'] += 1
            self.processing_stats['total_characters'] += processed_doc['character_count']
            self.processing_stats['estimated_tokens'] += processed_doc['estimated_tokens']

        # Save processed documents
        print(f"Saving to {output_file}...")
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            for doc in valid_documents:
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')

        # Generate validation report
        self.generate_validation_report(output_file.replace('.jsonl', '_report.txt'))

        return self.processing_stats

    def generate_validation_report(self, report_file: str):
        """Generate a validation report"""
        report_path = Path(report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("Medical Dataset Validation Report\n")
            f.write("="*50 + "\n\n")

            f.write("Processing Statistics:\n")
            f.write(f"  Total Documents: {self.processing_stats['total_documents']}\n")
            f.write(f"  Valid Documents: {self.processing_stats['valid_documents']}\n")
            f.write(f"  Invalid Documents: {self.processing_stats['invalid_documents']}\n")
            f.write(f"  Duplicate Documents Removed: {self.processing_stats['duplicate_documents']}\n")
            f.write(f"  Total Characters: {self.processing_stats['total_characters']:,}\n")
            f.write(f"  Estimated Tokens: {self.processing_stats['estimated_tokens']:,}\n")
            f.write(f"  Token Progress: {self.processing_stats['estimated_tokens']:,} / 1,000,000 ({self.processing_stats['estimated_tokens']/1000000:.1%})\n\n")

            f.write("Validation Status:\n")
            if self.processing_stats['invalid_documents'] == 0:
                f.write("  ✅ PASS - All documents are valid\n")
            else:
                f.write(f"  ❌ FAIL - {self.processing_stats['invalid_documents']} invalid documents\n\n")

            if self.validation_errors:
                f.write("Validation Errors:\n")
                for i, error in enumerate(self.validation_errors[:10]):  # Show first 10
                    f.write(f"\n  {i+1}. Document: {error['doc_id']}\n")
                    for err in error['errors']:
                        f.write(f"     - {err}\n")

                if len(self.validation_errors) > 10:
                    f.write(f"\n  ... and {len(self.validation_errors) - 10} more errors\n")

            f.write("\nData Quality Assessment:\n")
            if self.processing_stats['estimated_tokens'] >= 1000000:
                f.write("  ✅ PASS - Meets 1M token requirement\n")
            else:
                f.write(f"  ⚠️  NEEDS MORE DATA - Only {self.processing_stats['estimated_tokens']:,} tokens (need 1,000,000)\n")

            # Source distribution
            source_counts = {}
            # Would need to reload documents to get source counts
            f.write("\nNote: Detailed source distribution analysis requires additional processing\n")

        print(f"Validation report saved to {report_file}")

def main():
    """Main function to process medical data"""
    processor = MedicalDataProcessor()

    # Define input files (will be created by the fetch scripts)
    input_files = [
        "hackathon/data/fda_expanded_documents.jsonl",  # New expanded dataset
        "hackathon/data/fda_drug_documents.jsonl",
        "hackathon/data/pubmed_research_documents.jsonl",
        "hackathon/data/drugscom_documents.jsonl",
        "hackathon/data/condition_documents.jsonl",
        # Include existing medical documents
        "hackathon/data/medical_documents.jsonl",
        "hackathon/data/drug_mechanisms.jsonl"
    ]

    # Filter to only existing files
    existing_files = [f for f in input_files if Path(f).exists()]

    if not existing_files:
        print("No input files found. Please run the fetch scripts first:")
        print("  - python fetch_fda_drugs.py")
        print("  - python fetch_pubmed.py")
        print("  - python fetch_medical_websites.py")
        return

    # Process all data
    output_file = "hackathon/data/processed_medical_dataset.jsonl"
    stats = processor.process_dataset(existing_files, output_file)

    print(f"\nProcessing Complete!")
    print(f"Valid documents: {stats['valid_documents']:,}")
    print(f"Total characters: {stats['total_characters']:,}")
    print(f"Estimated tokens: {stats['estimated_tokens']:,}")
    print(f"Progress to 1M tokens: {stats['estimated_tokens']/1000000:.1%}")

    if stats['estimated_tokens'] < 1000000:
        print(f"\nWARNING: Still need {1000000 - stats['estimated_tokens']:,} more tokens")
        print("Consider running fetch scripts with more drugs/topics")
    else:
        print(f"\nSUCCESS: Dataset exceeds 1M token requirement!")

if __name__ == "__main__":
    main()