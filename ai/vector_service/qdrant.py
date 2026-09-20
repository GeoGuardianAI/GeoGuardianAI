import os
import json
import numpy as np
from typing import List, Dict, Any, Optional

class QdrantVectorDB:
    def __init__(self, db_path: str = "database"):
        self.db_path = db_path
        self.db_file = os.path.join(self.db_path, "qdrant_db.json")
        self.client = None
        self.initialized = False
        self.documents = []  # List of Dict: {id, vector, text, metadata}
        
        # Ensure database directory exists
        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path)
            
        self.load_local_db()
        
    def initialize_qdrant(self):
        if self.initialized:
            return
        try:
            from qdrant_client import QdrantClient
            # Connect to local docker Qdrant or memory client
            self.client = QdrantClient(path=os.path.join(self.db_path, "qdrant_storage"))
            self.initialized = True
        except ImportError:
            print("[VectorDB] qdrant-client not installed. Running local JSON-backed vector DB.")
            self.client = None

    def load_local_db(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, "r") as f:
                    self.documents = json.load(f)
                print(f"[VectorDB] Loaded {len(self.documents)} chunks from local DB.")
            except Exception as e:
                print(f"[VectorDB] Failed to load local DB: {e}. Starting fresh.")
                self.documents = []
        else:
            self.documents = []

    def save_local_db(self):
        try:
            with open(self.db_file, "w") as f:
                json.dump(self.documents, f, indent=2)
        except Exception as e:
            print(f"[VectorDB] Failed to save local DB: {e}")

    def upsert(self, doc_id: str, vector: List[float], text: str, metadata: Dict[str, Any]):
        # Save locally
        doc = {
            "id": doc_id,
            "vector": vector,
            "text": text,
            "metadata": metadata
        }
        # Update if exists, else append
        self.documents = [d for d in self.documents if d["id"] != doc_id]
        self.documents.append(doc)
        self.save_local_db()
        
        # Also try Qdrant client upsert
        self.initialize_qdrant()
        if self.client:
            try:
                from qdrant_client.models import PointStruct, VectorParams, Distance
                # Ensure collection exists
                collections = self.client.get_collections().collections
                exists = any(c.name == "disaster_sops" for c in collections)
                if not exists:
                    self.client.create_collection(
                        collection_name="disaster_sops",
                        vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
                    )
                
                # Check point ID conversion
                # qdrant requires int or uuid. We can hash doc_id string to int
                import uuid
                u_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id))
                self.client.upsert(
                    collection_name="disaster_sops",
                    points=[
                        PointStruct(
                            id=u_id,
                            vector=vector,
                            payload={"text": text, **metadata}
                        )
                    ]
                )
            except Exception as e:
                print(f"[VectorDB] Qdrant upsert failed: {e}")

    def clear(self):
        self.documents = []
        self.save_local_db()
        self.initialize_qdrant()
        if self.client:
            try:
                self.client.delete_collection("disaster_sops")
            except Exception:
                pass

    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        a = np.array(v1)
        b = np.array(v2)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def sparse_score(self, query: str, document_text: str) -> float:
        """
        Simple BM25-like keyword matching score for sparse search.
        """
        query_words = set(query.lower().split())
        doc_words = document_text.lower().split()
        if not query_words or not doc_words:
            return 0.0
            
        score = 0.0
        for word in query_words:
            # Term Frequency in doc
            tf = doc_words.count(word)
            if tf > 0:
                # Add word length and frequency scaling
                score += (tf / (tf + 1.5)) * 1.5
        return score

    def search(self, 
               query_vector: List[float], 
               query_text: str, 
               top_k: int = 5, 
               mode: str = "hybrid", 
               filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Performs vector, keyword, or hybrid search with metadata filters.
        """
        # Filter documents first
        filtered_docs = []
        for doc in self.documents:
            match = True
            if filters:
                for k, v in filters.items():
                    if v and v != "Any" and v != "All":
                        doc_val = doc["metadata"].get(k)
                        if str(doc_val).lower() != str(v).lower():
                            match = False
                            break
            if match:
                filtered_docs.append(doc)
                
        results = []
        
        if mode == "vector":
            # Dense Vector Search
            for doc in filtered_docs:
                sim = self.cosine_similarity(query_vector, doc["vector"])
                results.append({
                    "id": doc["id"],
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "score": round(sim, 4),
                    "search_type": "vector"
                })
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
            
        elif mode == "keyword":
            # Sparse Keyword Search
            for doc in filtered_docs:
                k_score = self.sparse_score(query_text, doc["text"])
                if k_score > 0:
                    results.append({
                        "id": doc["id"],
                        "text": doc["text"],
                        "metadata": doc["metadata"],
                        "score": round(k_score, 4),
                        "search_type": "keyword"
                    })
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
            
        else:  # Hybrid search
            # We score both Vector and Keyword, then use Reciprocal Rank Fusion (RRF) 
            # or normalized weighted addition. Let's do a weighted addition of normalized scores.
            dense_scores = []
            sparse_scores = []
            
            for doc in filtered_docs:
                d_val = self.cosine_similarity(query_vector, doc["vector"])
                s_val = self.sparse_score(query_text, doc["text"])
                dense_scores.append((doc, d_val))
                sparse_scores.append((doc, s_val))
                
            # Normalize sparse scores
            max_s = max([s for _, s in sparse_scores], default=1.0)
            if max_s == 0:
                max_s = 1.0
                
            for idx, doc in enumerate(filtered_docs):
                d_val = dense_scores[idx][1]
                s_val_norm = sparse_scores[idx][1] / max_s
                
                # Hybrid score: 70% vector + 30% keyword
                hybrid_score = 0.7 * d_val + 0.3 * s_val_norm
                
                results.append({
                    "id": doc["id"],
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "score": round(hybrid_score, 4),
                    "search_type": "hybrid",
                    "breakdown": {
                        "vector_score": round(d_val, 4),
                        "keyword_score_norm": round(s_val_norm, 4)
                    }
                })
                
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
