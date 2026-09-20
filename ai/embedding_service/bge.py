import hashlib
import numpy as np
from typing import List

class BGEEmbeddingModel:
    def __init__(self):
        self.model = None
        self.initialized = False
        
    def initialize(self):
        if self.initialized:
            return
        try:
            from sentence_transformers import SentenceTransformer
            # Load BGE-M3. In a real environment, it might download.
            # To prevent blocking the user if it's not pre-downloaded, we can specify local_files_only=False
            self.model = SentenceTransformer('BAAI/bge-m3')
            self.initialized = True
        except ImportError:
            print("[Embedding] sentence-transformers or torch not installed. Running pure-Python fallback vectorizer.")
            self.model = None
            
    def get_embedding(self, text: str) -> List[float]:
        self.initialize()
        if self.model:
            try:
                embedding = self.model.encode(text)
                return embedding.tolist()
            except Exception as e:
                print(f"[Embedding] sentence-transformers encoding failed: {e}. Falling back.")
                
        # Pure-Python fallback vectorizer:
        # We generate a 1024-dimensional normalized vector based on the hash values of the text.
        # This guarantees that similar texts (sharing words) get somewhat correlated vectors, 
        # and it's extremely stable and fast.
        
        # Initialize an empty vector
        vector = np.zeros(1024)
        
        # Tokenize text
        words = [w.strip(".,!?;:()[]\"'") for w in text.lower().split() if len(w) > 2]
        
        if not words:
            # Return a deterministic random-like normalized vector
            h = hashlib.sha255(text.encode('utf-8')).digest()
            for i in range(1024):
                val = h[i % len(h)] ^ (i & 0xFF)
                vector[i] = val
        else:
            # Map each word to a few dimensions in the 1024 space
            for word in words:
                # Calculate deterministic hash values for the word
                h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
                
                # Activate 5 features for this word
                for offset in range(5):
                    dim = (h + offset * 137) % 1024
                    # Accumulate weight (could be simple count)
                    vector[dim] += 1.0
                    
        # Apply L2 normalization
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector.tolist()
        
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self.get_embedding(t) for t in texts]
