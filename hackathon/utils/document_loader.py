"""
Document Loading Utilities

Provides functions for loading and processing documents from various formats
for the GraphRAG hackathon.
"""

import json
from pathlib import Path
from typing import List, Dict, Any


def load_documents_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load documents from a JSONL file

    Args:
        file_path: Path to the JSONL file

    Returns:
        List of document dictionaries

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file contains invalid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")

    documents = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    doc = json.loads(line)
                    documents.append(doc)
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON on line {line_num}: {e}")
                    continue

    return documents


def load_documents_json(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load documents from a JSON file

    Args:
        file_path: Path to the JSON file

    Returns:
        List of document dictionaries

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file contains invalid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                raise ValueError("JSON file must contain a list or object")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file: {e}")


def validate_document(doc: Dict[str, Any], required_fields: List[str] = None) -> tuple[bool, List[str]]:
    """
    Validate a document has required fields and meets quality standards

    Args:
        doc: Document dictionary to validate
        required_fields: List of required field names (default: ['doc_id', 'content'])

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    if required_fields is None:
        required_fields = ['doc_id', 'content']

    errors = []

    # Check required fields
    for field in required_fields:
        if field not in doc:
            errors.append(f"Missing required field: {field}")

    # Validate content
    if 'content' in doc:
        content = doc['content']
        if not isinstance(content, str):
            errors.append("Content must be a string")
        elif len(content.strip()) < 10:
            errors.append("Content too short (minimum 10 characters)")
        elif len(content) > 20000:
            errors.append(f"Content too long ({len(content)} characters, maximum 20000)")

    return len(errors) == 0, errors


def filter_valid_documents(documents: List[Dict[str, Any]],
                           required_fields: List[str] = None) -> List[Dict[str, Any]]:
    """
    Filter documents to only include valid ones

    Args:
        documents: List of documents to filter
        required_fields: Required field names for validation

    Returns:
        List of valid documents
    """
    valid_docs = []
    for doc in documents:
        is_valid, errors = validate_document(doc, required_fields)
        if is_valid:
            valid_docs.append(doc)
        else:
            doc_id = doc.get('doc_id', 'unknown')
            print(f"Skipping invalid document {doc_id}: {', '.join(errors)}")

    return valid_docs


def get_document_stats(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get statistics about a collection of documents

    Args:
        documents: List of documents

    Returns:
        Dictionary with document statistics
    """
    if not documents:
        return {
            'count': 0,
            'total_chars': 0,
            'avg_chars': 0,
            'estimated_tokens': 0
        }

    total_chars = sum(len(doc.get('content', '')) for doc in documents)
    avg_chars = total_chars / len(documents)
    estimated_tokens = total_chars // 4  # Rough estimate: 4 chars per token

    return {
        'count': len(documents),
        'total_chars': total_chars,
        'avg_chars': avg_chars,
        'estimated_tokens': estimated_tokens
    }


def merge_document_collections(*document_lists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge multiple document collections, removing duplicates based on doc_id

    Args:
        *document_lists: Variable number of document lists to merge

    Returns:
        Merged list of unique documents
    """
    seen_ids = set()
    merged = []

    for doc_list in document_lists:
        for doc in doc_list:
            doc_id = doc.get('doc_id')
            if doc_id and doc_id not in seen_ids:
                seen_ids.add(doc_id)
                merged.append(doc)

    return merged


def chunk_document_by_tokens(document: Dict[str, Any],
                             chunk_size: int = 1000,
                             overlap: int = 200) -> List[Dict[str, Any]]:
    """
    Split a document into chunks by approximate token count

    Args:
        document: Document to chunk
        chunk_size: Target chunk size in characters (rough approximation)
        overlap: Overlap between chunks in characters

    Returns:
        List of chunked documents
    """
    content = document.get('content', '')
    doc_id = document.get('doc_id', 'unknown')

    if len(content) <= chunk_size:
        return [document]

    chunks = []
    start = 0
    chunk_num = 0

    while start < len(content):
        end = start + chunk_size
        chunk_content = content[start:end]

        chunk = {
            'doc_id': f"{doc_id}_chunk_{chunk_num}",
            'doc_type': document.get('doc_type', 'chunk'),
            'source': document.get('source', 'unknown'),
            'content': chunk_content,
            'original_doc_id': doc_id,
            'chunk_number': chunk_num,
            'total_chunks': (len(content) // chunk_size) + 1
        }

        chunks.append(chunk)
        start = end - overlap
        chunk_num += 1

    return chunks