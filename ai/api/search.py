from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from ai.api.upload import get_orchestrator

router = APIRouter()

@router.get("/search")
async def search_endpoint(
    q: str = Query(..., description="The query string to search for"),
    top_k: int = Query(5, description="Number of results to return"),
    mode: str = Query("hybrid", description="Search mode: vector, keyword, or hybrid"),
    disaster_type: Optional[str] = Query(None, description="Filter by disaster type"),
    state: Optional[str] = Query(None, description="Filter by geographic state"),
    district: Optional[str] = Query(None, description="Filter by geographic district")
):
    """
    Performs hybrid, vector, or keyword search across indexed SOP documents.
    """
    try:
        orch = get_orchestrator()
        
        # Build filters
        filters = {}
        if disaster_type:
            filters["disaster_type"] = disaster_type
        if state:
            filters["state"] = state
        if district:
            filters["district"] = district
            
        # Get query embedding
        query_vector = orch.embedder.get_embedding(q)
        
        # Search Qdrant/local DB
        hits = orch.db.search(
            query_vector=query_vector,
            query_text=q,
            top_k=top_k,
            mode=mode,
            filters=filters
        )
        
        # Compile evidence summary
        from ai.retrieval_service.explainability import ExplainableAILogger
        evidence = ExplainableAILogger.compile_evidence(hits)
        confidence = ExplainableAILogger.calculate_confidence(hits)
        
        return {
            "query": q,
            "search_mode": mode,
            "filters_applied": filters,
            "confidence_score": confidence,
            "evidence_block": evidence,
            "hits": hits
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
