import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add parent directory to path to allow importing the ai/ folder cleanly
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.api.upload import router as upload_router, get_orchestrator
from ai.api.chat import router as chat_router
from ai.api.search import router as search_router

app = FastAPI(
    title="GeoGuardian AI - RAG Assistant Backend",
    description="FastAPI Backend for Disaster Response & Critical Infrastructure Document Analysis Module",
    version="1.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For MVP, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register AI APIRouters
app.include_router(upload_router, tags=["Document Ingestion"])
app.include_router(chat_router, tags=["Conversational AI"])
app.include_router(search_router, tags=["Semantic Search"])

@app.get("/")
async def root():
    return {
        "app": "GeoGuardian AI RAG Assistant",
        "status": "Online",
        "api_docs": "/docs"
    }

@app.get("/api/graph")
async def get_graph_data():
    """
    Returns the compiled node-relationship network graph for visualization.
    """
    try:
        orch = get_orchestrator()
        graph_data = orch.graph.get_graph_data()
        return graph_data
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
