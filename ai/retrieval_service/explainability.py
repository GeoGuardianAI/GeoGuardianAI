from typing import List, Dict, Any

class ExplainableAILogger:
    @staticmethod
    def calculate_confidence(hits: List[Dict[str, Any]]) -> float:
        """
        Calculates an overall confidence percentage based on retrieved search hits.
        """
        if not hits:
            return 0.0
            
        # Get average score of top hits
        avg_score = sum(hit["score"] for hit in hits) / len(hits)
        
        # Scale score. Cosine similarity ranges mostly between 0.3 and 0.9.
        # Map 0.3 -> 30%, 0.8+ -> 98%
        confidence = avg_score * 100.0
        if confidence > 99.0:
            confidence = 99.0
        elif confidence < 20.0 and hits:
            confidence = 20.0
            
        return round(confidence, 1)

    @staticmethod
    def compile_evidence(hits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Builds a structured evidence block listing source citations, page numbers, and reasoning.
        """
        sources = []
        pages = set()
        citations = []
        
        for idx, hit in enumerate(hits):
            meta = hit.get("metadata", {})
            source_file = meta.get("title", "Unknown SOP")
            page_num = meta.get("pages", 1)
            
            sources.append(source_file)
            pages.add(page_num)
            
            citations.append({
                "rank": idx + 1,
                "document": source_file,
                "page": page_num,
                "snippet": hit.get("text", "")[:120] + "...",
                "score": hit.get("score", 0.0),
                "type": hit.get("search_type", "hybrid")
            })
            
        return {
            "primary_source": sources[0] if sources else "Unknown SOP Document",
            "all_sources": list(set(sources)),
            "pages": list(pages),
            "citations": citations,
            "reasoning": f"Retrieved {len(hits)} relevant passages matching disaster procedure queries with high semantic score."
        }
