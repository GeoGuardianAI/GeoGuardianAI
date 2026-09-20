from typing import List, Dict, Any, Optional
from ai.embedding_service.bge import BGEEmbeddingModel
from ai.vector_service.qdrant import QdrantVectorDB
from ai.retrieval_service.explainability import ExplainableAILogger

class SOPRetriever:
    def __init__(self, db: QdrantVectorDB, embedder: BGEEmbeddingModel):
        self.db = db
        self.embedder = embedder
        
    def retrieve_context(self, 
                         query: str, 
                         top_k: int = 4, 
                         search_mode: str = "hybrid", 
                         filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Retrieves matching SOP chunks, filters them, and formats evidence/confidence.
        """
        # Step 1: Embed the query
        query_vector = self.embedder.get_embedding(query)
        
        # Step 2: Search vector DB (hybrid, vector, or keyword)
        hits = self.db.search(
            query_vector=query_vector,
            query_text=query,
            top_k=top_k,
            mode=search_mode,
            filters=filters
        )
        
        # Step 3: Compile explainable evidence & calculate confidence
        confidence = ExplainableAILogger.calculate_confidence(hits)
        evidence = ExplainableAILogger.compile_evidence(hits)
        
        # Combined context string
        context_str = "\n\n".join([f"[Source: {hit['metadata'].get('title', 'SOP')} - Page {hit['metadata'].get('pages', 1)}]\n{hit['text']}" for hit in hits])
        
        return {
            "context": context_str,
            "hits": hits,
            "confidence": confidence,
            "evidence": evidence
        }
