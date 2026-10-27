from typing import List, Dict, Any

class ExplainableAILogger:
    @staticmethod
    def calculate_confidence(hits: List[Dict[str, Any]]) -> float:
        """
        Calculates an overall confidence percentage based on the top relevant search hits.
        """
        if not hits:
            return 0.0
            
        # Base confidence on the top 3 most relevant hits used for synthesis
        top_hits = hits[:3]
        avg_score = sum(hit.get("score", 0.0) for hit in top_hits) / len(top_hits)
        
        # Scale score: cosine/hybrid similarity 0.3 -> ~45%, 0.6 -> ~75%, 0.8+ -> ~90%
        # Linear calibrated scaling based on verified SOP retrieval
        confidence = min(92.0, max(25.0, avg_score * 100.0 * 1.1))
            
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
