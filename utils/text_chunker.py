"""
utils/text_chunker.py — Splits long text into smaller chunks.
"""

import uuid

class TextChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_documents(self, documents: list) -> list:
        """
        Takes a list of document dictionaries and returns a list of chunk dictionaries.
        """
        chunks = []
        for doc in documents:
            text = doc["content"]
            # Basic naive chunking by character length
            start = 0
            while start < len(text):
                end = min(start + self.chunk_size, len(text))
                
                # If we're not at the end of the text, try to find a natural break (space or newline)
                if end < len(text):
                    last_space = text.rfind(' ', start, end)
                    last_newline = text.rfind('\n', start, end)
                    best_break = max(last_space, last_newline)
                    if best_break != -1 and best_break > start + (self.chunk_size // 2):
                        end = best_break + 1
                        
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append({
                        "chunk_id": str(uuid.uuid4()),
                        "text": chunk_text,
                        "source": doc["source"],
                        "filename": doc["filename"],
                        "title": doc["title"]
                    })
                
                if end >= len(text):
                    break
                    
                # Move start forward, accounting for overlap
                start = end - self.chunk_overlap
                if start >= end:  # Prevent infinite loops if overlap is too large
                    start = end
                    
        return chunks
