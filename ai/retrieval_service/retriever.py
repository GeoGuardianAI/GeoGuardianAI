from typing import List, Dict, Any, Optional
from ai.embedding_service.bge import BGEEmbeddingModel
from ai.vector_service.qdrant import QdrantVectorDB
from ai.retrieval_service.explainability import ExplainableAILogger

# Official document keyword mapping for document-specific queries
DOCUMENT_KEYWORDS = {
    "disaster_management_rule_2005.pdf": [
        "rule 2005", "rules 2005", "disaster management rule", "management rule 2005",
        "dm rule", "dm rules", "rules, 2005"
    ],
    "district_preparedness_sop.pdf": [
        "district disaster management authority sop", "district preparedness",
        "capacity building", "preparedness sop", "ddma sop"
    ],
    "urban_flooding_guidelines.pdf": [
        "management of urban flooding", "urban flooding guidelines", "urban flood guidelines"
    ],
    "flood_management_guidelines.pdf": [
        "management of floods", "flood management guidelines", "ndma flood guidelines"
    ],
    "urban_flooding_sop.pdf": [
        "urban flooding sop", "mohua sop", "mohua"
    ],
    "pune_district_disaster_management_plan.pdf": [
        "pune district disaster management plan", "pune ddmp", "ddmp pune"
    ],
    "state_disaster_management_plan_2023.pdf": [
        "state disaster management plan", "sdmp", "maharashtra sdmp"
    ],
}

class SOPRetriever:
    def __init__(self, db: QdrantVectorDB, embedder: BGEEmbeddingModel):
        self.db = db
        self.embedder = embedder
        
    def retrieve_context(self, 
                         query: str, 
                         top_k: int = 8, 
                         search_mode: str = "hybrid", 
                         filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Retrieves matching SOP chunks, filters them, and formats evidence/confidence.
        """
        # Auto-detect if user explicitly mentioned a specific document in the query
        q_low = query.lower()
        doc_filters = dict(filters) if filters else {}
        if "source_file" not in doc_filters:
            for filename, kw_list in DOCUMENT_KEYWORDS.items():
                if any(kw in q_low for kw in kw_list):
                    doc_filters["source_file"] = filename
                    break

        # Step 1: Embed the query
        query_vector = self.embedder.get_embedding(query)
        
        # Step 2: Search vector DB (hybrid, vector, or keyword)
        # Targeted document queries need wider chunk coverage to capture specific substantive clauses
        effective_top_k = max(top_k, 12) if doc_filters.get("source_file") else top_k
        hits = self.db.search(
            query_vector=query_vector,
            query_text=query,
            top_k=effective_top_k,
            mode=search_mode,
            filters=doc_filters if doc_filters else None
        )

        # Fallback: if targeted document returned 0 hits, fall back to global search
        if not hits and doc_filters.get("source_file"):
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
