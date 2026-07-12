"""
services/rag_service.py — Orchestrates the RAG Knowledge Base.
"""

import os
import hashlib
import logging
from utils.document_loader import DocumentLoader
from utils.text_chunker import TextChunker
from utils.vector_store import LocalMockEmbedder, InMemoryVectorStore, WatsonxEmbedder, ChromaVectorStore

logger = logging.getLogger(__name__)

# Global vector store instance for this module (acting as a singleton for now)
_vector_store = None
_is_indexed = False
_using_fallback = False

def get_vector_store():
    global _vector_store, _using_fallback
    if _vector_store is None:
        try:
            # Try to initialize Semantic RAG with watsonx and ChromaDB
            embedder = WatsonxEmbedder(model_id="ibm/slate-125m-english-rtrvr-v2")
            _vector_store = ChromaVectorStore(embedder, persist_directory="chroma_db")
            _using_fallback = False
            logger.info("Successfully initialized WatsonxEmbedder and ChromaVectorStore.")
        except Exception as e:
            # Fallback to TF-IDF InMemory
            logger.error("Failed to initialize semantic RAG. Falling back to TF-IDF. Error: %s", e)
            embedder = LocalMockEmbedder()
            _vector_store = InMemoryVectorStore(embedder)
            _using_fallback = True
            
    return _vector_store

def get_rag_dir():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "rag_docs")

def get_documents_fingerprint() -> str:
    """Generates a hash based on the relative filenames and actual file content of all rag_docs."""
    rag_dir = get_rag_dir()
    if not os.path.exists(rag_dir):
        return ""
        
    hasher = hashlib.md5()
    
    # Gather all file paths first
    all_files = []
    for root, dirs, files in os.walk(rag_dir):
        for file in files:
            if file.endswith((".txt", ".md")):
                all_files.append(os.path.join(root, file))
                
    # Sort for deterministic ordering
    all_files.sort()
    
    for file_path in all_files:
        rel_path = os.path.relpath(file_path, rag_dir)
        hasher.update(rel_path.encode('utf-8'))
        try:
            with open(file_path, 'rb') as f:
                hasher.update(f.read())
        except Exception:
            pass
            
    return hasher.hexdigest()

def load_documents():
    """Loads documents from the rag_docs directory."""
    loader = DocumentLoader(get_rag_dir())
    return loader.load_documents()

def is_index_fresh() -> bool:
    """Checks if the existing persistent index matches the current document fingerprint."""
    global _using_fallback
    store = get_vector_store()
    
    # In-memory store is never persistent, so it's fresh only if _is_indexed is True
    if _using_fallback:
        return _is_indexed
        
    # For Chroma, check fingerprint
    fingerprint_path = "chroma_db/fingerprint.txt"
    if not os.path.exists(fingerprint_path):
        return False
        
    try:
        with open(fingerprint_path, "r", encoding="utf-8") as f:
            stored_fp = f.read().strip()
    except Exception:
        return False
        
    current_fp = get_documents_fingerprint()
    return stored_fp == current_fp

def build_index():
    """Loads, chunks, and builds the vector index."""
    global _is_indexed
    
    # Check if we need to rebuild
    if is_index_fresh():
        _is_indexed = True
        return 0
        
    docs = load_documents()
    if not docs:
        _is_indexed = True
        return 0
        
    chunker = TextChunker(chunk_size=500, chunk_overlap=50)
    chunks = chunker.chunk_documents(docs)
    
    store = get_vector_store()
    try:
        logger.info("Building semantic vector index...")
        store.build_index(chunks)
    except Exception as e:
        logger.error("Failed to build semantic index. Falling back to TF-IDF. Error: %s", e)
        # Force fallback
        global _vector_store, _using_fallback
        _vector_store = InMemoryVectorStore(LocalMockEmbedder())
        _using_fallback = True
        store = _vector_store
        store.build_index(chunks)
        
    # Save fingerprint if using Chroma
    if not _using_fallback:
        os.makedirs("chroma_db", exist_ok=True)
        with open("chroma_db/fingerprint.txt", "w", encoding="utf-8") as f:
            f.write(get_documents_fingerprint())
            
    _is_indexed = True
    return len(chunks)

def is_index_built() -> bool:
    """Checks if the index has been built or is fresh."""
    global _is_indexed
    if _is_indexed:
        return True
    
    fresh = is_index_fresh()
    if fresh:
        _is_indexed = True
    return fresh

def retrieve(query: str, top_k: int = 5) -> list:
    """
    Retrieves the most relevant passages for the query.
    """
    if not is_index_built():
        build_index()
        
    store = get_vector_store()
    try:
        return store.semantic_search(query, top_k=top_k)
    except Exception as e:
        logger.error("Semantic search failed during retrieve: %s", e)
        global _using_fallback, _vector_store, _is_indexed
        if not _using_fallback:
            # Fallback at retrieval time
            logger.info("Falling back to TF-IDF search")
            _vector_store = InMemoryVectorStore(LocalMockEmbedder())
            _using_fallback = True
            _is_indexed = False # Force rebuild of in-memory index
            build_index()
            return _vector_store.semantic_search(query, top_k=top_k)
        return []

def format_context(retrieved_chunks: list) -> str:
    """
    Formats the retrieved chunks into a single context string 
    for injection into an LLM prompt.
    """
    context = ""
    for idx, chunk in enumerate(retrieved_chunks):
        context += f"--- Document {idx+1}: {chunk['title']} ({chunk['source']}) ---\n"
        context += f"{chunk['text']}\n\n"
    return context.strip()
