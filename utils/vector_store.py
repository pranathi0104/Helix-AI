"""
utils/vector_store.py — Abstractions for embedding and vector storage.
"""

from abc import ABC, abstractmethod
import math
from collections import Counter
import re

def normalize_text(text: str) -> str:
    # replace hyphens with space, then lowercase and remove non-alphanumeric
    return re.sub(r'[^a-z0-9 ]', '', text.lower().replace('-', ' ')).strip()

# ---------------------------------------------------------------------------
# Embedding Abstractions
# ---------------------------------------------------------------------------

class EmbedderBase(ABC):
    @abstractmethod
    def embed(self, text: str) -> list:
        pass

    @abstractmethod
    def embed_batch(self, texts: list) -> list:
        pass


class LocalMockEmbedder(EmbedderBase):
    """
    A simple TF-IDF based 'embedder' that represents texts as sparse dictionaries 
    instead of dense vectors. This serves as a lightweight local placeholder 
    before integrating IBM watsonx embeddings.
    """
    def __init__(self):
        self.vocab = {}
        self.idf = {}
        self.num_docs = 0

    def _tokenize(self, text: str):
        text = text.lower()
        return re.findall(r'\b\w+\b', text)

    def fit(self, texts: list):
        self.num_docs = len(texts)
        doc_freqs = Counter()
        for text in texts:
            tokens = set(self._tokenize(text))
            for token in tokens:
                doc_freqs[token] += 1
                
        for token, freq in doc_freqs.items():
            self.idf[token] = math.log((1 + self.num_docs) / (1 + freq)) + 1

    def embed(self, text: str) -> dict:
        """Returns a dict of {token: tf_idf_score}."""
        tokens = self._tokenize(text)
        tf = Counter(tokens)
        
        vec = {}
        # compute magnitude for cosine similarity
        norm = 0.0
        for token, count in tf.items():
            weight = count * self.idf.get(token, 1.0) # default idf if unknown
            vec[token] = weight
            norm += weight * weight
            
        norm = math.sqrt(norm)
        if norm > 0:
            for k in vec:
                vec[k] /= norm
                
        return vec

    def embed_batch(self, texts: list) -> list:
        return [self.embed(t) for t in texts]


class WatsonxEmbedder(EmbedderBase):
    """
    Dense vector embedder using IBM watsonx.ai.
    """
    def __init__(self, model_id: str = "ibm/slate-125m-english-rtrvr-v2"):
        import os
        from ibm_watsonx_ai.foundation_models import Embeddings
        from ibm_watsonx_ai import APIClient, Credentials
        
        self.client = APIClient(
            credentials=Credentials(
                url=os.getenv("IBM_URL"),
                api_key=os.getenv("IBM_API_KEY")
            ),
            project_id=os.getenv("IBM_PROJECT_ID")
        )
        self.embeddings_model = Embeddings(
            model_id=model_id,
            api_client=self.client,
            project_id=os.getenv("IBM_PROJECT_ID")
        )

    def embed(self, text: str) -> list:
        return self.embeddings_model.embed_documents([text])[0]

    def embed_batch(self, texts: list) -> list:
        # watsonx embed_documents takes a list and returns a list of embeddings
        return self.embeddings_model.embed_documents(texts)



# ---------------------------------------------------------------------------
# Vector Store Abstractions
# ---------------------------------------------------------------------------

class VectorStoreBase(ABC):
    @abstractmethod
    def build_index(self, chunks: list):
        pass

    @abstractmethod
    def add_documents(self, chunks: list):
        pass

    @abstractmethod
    def semantic_search(self, query: str, top_k: int = 5) -> list:
        pass


class InMemoryVectorStore(VectorStoreBase):
    """
    An in-memory store that holds document chunks and their embeddings.
    Supports a pluggable EmbedderBase.
    """
    def __init__(self, embedder: EmbedderBase):
        self.embedder = embedder
        self.chunks = []
        self.embeddings = []

    def build_index(self, chunks: list):
        """Builds the index from scratch."""
        self.chunks = chunks
        texts = [chunk['text'] for chunk in chunks]
        
        # If using LocalMockEmbedder, we need to fit the TF-IDF first
        if hasattr(self.embedder, 'fit'):
            self.embedder.fit(texts)
            
        self.embeddings = self.embedder.embed_batch(texts)

    def add_documents(self, chunks: list):
        """Appends to the existing index."""
        self.chunks.extend(chunks)
        texts = [chunk['text'] for chunk in chunks]
        self.embeddings.extend(self.embedder.embed_batch(texts))

    def _cosine_similarity(self, vec1, vec2) -> float:
        """Computes similarity for sparse dictionary vectors."""
        # Check if vectors are dicts (LocalMockEmbedder) or lists (real embeddings)
        if isinstance(vec1, dict) and isinstance(vec2, dict):
            score = 0.0
            for k, v in vec1.items():
                if k in vec2:
                    score += v * vec2[k]
            return score
        else:
            # Placeholder for dense vector cosine similarity (for when IBM embedder is plugged in)
            dot = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = math.sqrt(sum(a * a for a in vec1))
            norm2 = math.sqrt(sum(b * b for b in vec2))
            if norm1 * norm2 == 0:
                return 0.0
            return dot / (norm1 * norm2)

    def semantic_search(self, query: str, top_k: int = 5, strict_topic_filtering: bool = False) -> list:
        """
        Returns a list of retrieved chunks sorted by relevance score.
        Each chunk is enhanced with a 'relevance_score' field.
        """
        if not self.chunks:
            return []
            
        chunks_to_search = self.chunks
        if strict_topic_filtering:
            norm_query = normalize_text(query)
            unique_titles = list(set([chunk['title'] for chunk in self.chunks]))
            
            matched_titles = []
            for title in unique_titles:
                norm_title = normalize_text(title)
                if re.search(r'\b' + re.escape(norm_title) + r'\b', norm_query):
                    matched_titles.append(title)
                    
            if not matched_titles:
                return []
                
            chunks_to_search = [c for c in self.chunks if c['title'] in matched_titles]
            
        query_vec = self.embedder.embed(query)
        
        results = []
        for chunk in chunks_to_search:
            # find original index to get embedding
            idx = self.chunks.index(chunk)
            doc_vec = self.embeddings[idx]
            
            score = self._cosine_similarity(query_vec, doc_vec)
            
            # Copy chunk and add score
            result = chunk.copy()
            result['relevance_score'] = round(score, 4)
            results.append(result)
            
        # Sort by relevance
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Return top_k results that have a score > 0
        return [r for r in results[:top_k] if r['relevance_score'] > 0.01]


class ChromaVectorStore(VectorStoreBase):
    """
    A persistent vector store using ChromaDB.
    """
    def __init__(self, embedder: EmbedderBase, persist_directory: str = "chroma_db"):
        self.embedder = embedder
        import chromadb
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # We explicitly configure the collection for cosine distance
        self.collection = self.client.get_or_create_collection(
            name="helix_medical_knowledge",
            metadata={"hnsw:space": "cosine"}
        )

    def build_index(self, chunks: list):
        """Clears existing and builds the index from scratch."""
        # Reset collection by deleting and recreating
        self.client.delete_collection("helix_medical_knowledge")
        self.collection = self.client.get_or_create_collection(
            name="helix_medical_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        if chunks:
            self.add_documents(chunks)

    def add_documents(self, chunks: list):
        """Appends to the existing index."""
        if not chunks:
            return
            
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.embedder.embed_batch(texts)
        
        ids = [chunk['chunk_id'] for chunk in chunks]
        metadatas = [
            {
                "title": chunk.get('title', ''),
                "source": chunk.get('source', ''),
                "filename": chunk.get('filename', '')
            }
            for chunk in chunks
        ]
        
        # Batch insert if large, though for this scale single insert is fine
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

    def semantic_search(self, query: str, top_k: int = 5) -> list:
        """
        Returns a list of retrieved chunks sorted by relevance score.
        """
        query_vec = self.embedder.embed(query)
        
        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=top_k
        )
        
        formatted_results = []
        if not results['documents'] or not results['documents'][0]:
            return []
            
        docs = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        ids = results['ids'][0]
        
        for doc, meta, distance, id_ in zip(docs, metadatas, distances, ids):
            # For cosine in Chroma, distance is 1 - cosine_similarity (0 is identical, 2 is opposite).
            # Convert to a standard relevance score where higher is better, ensuring it stays in [0, 1].
            relevance_score = max(0.0, min(1.0, 1.0 - distance))
            
            formatted_results.append({
                "chunk_id": id_,
                "title": meta.get("title", ""),
                "source": meta.get("source", ""),
                "filename": meta.get("filename", ""),
                "text": doc,
                "relevance_score": round(relevance_score, 4)
            })
            
        return formatted_results
