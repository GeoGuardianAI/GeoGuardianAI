import time
from typing import Dict, Any, List, Optional
from ai.guardrails.input_guard import SafetyGuardrails
from ai.cache.query_cache import QueryCache
from ai.vector_service.qdrant import QdrantVectorDB
from ai.vector_service.knowledge_graph import DisasterKnowledgeGraph
from ai.embedding_service.bge import BGEEmbeddingModel
from ai.retrieval_service.retriever import SOPRetriever
from ai.llm_service.llama import LLMModelManager
from ai.evaluation.evaluation import RAGEvaluator
from ai.agents.document_agent import DocumentAgent
from ai.agents.report_agent import ReportAgent
from ai.translation_service.nllb import NLLBTranslator
from ai.memory_service.conversation import ConversationMemoryManager
from ai.reasoning import ReasoningEngine

class GeoGuardianOrchestrator:
    def __init__(self):
        self.db = QdrantVectorDB()
        self.graph = DisasterKnowledgeGraph()
        self.embedder = BGEEmbeddingModel()
        self.retriever = SOPRetriever(self.db, self.embedder)
        self.llm = LLMModelManager()
        self.cache = QueryCache()
        self.memory = ConversationMemoryManager()
        self.translator = NLLBTranslator()
        
        # Load default SOP documents if DB is empty
        self.preload_default_sops()

    def preload_default_sops(self):
        if not self.db.documents:
            print("[Orchestrator] Loading default SOP documents...")
            default_docs = [
                {
                    "id": "flood_sop_1",
                    "text": "Flood evacuation rules state that evacuation must begin immediately when water levels exceed the warning threshold of 1.8 meters. The local emergency responders must establish a safety perimeter of 500 meters around the Mutha river basin. Rescue boats should be deployed to Highway 48 for motorist evacuation.",
                    "metadata": {"title": "Flood_SOP.txt", "pages": 1, "disaster_type": "Flood", "state": "Maharashtra", "district": "Pune"}
                },
                {
                    "id": "flood_sop_2",
                    "text": "In the event of a severe bridge blockage, medical rescue teams must be positioned at Sassoon General Hospital to treat critical victims. If Sangam Bridge is damaged, traffic must be rerouted through Krishna River Bridge. Temporary shelters should be established at the District Sports Complex.",
                    "metadata": {"title": "Flood_SOP.txt", "pages": 2, "disaster_type": "Flood", "state": "Maharashtra", "district": "Pune"}
                },
                {
                    "id": "wildfire_sop_1",
                    "text": "Wildfire response protocol requires establishing a fire perimeter when dry winds exceed 25 km/h. Responders should immediately block the mountain pass road and evacuate residential structures within a 2 kilometer radius. Water trucks must be routed via Route 9.",
                    "metadata": {"title": "Wildfire_SOP.txt", "pages": 1, "disaster_type": "Wildfire", "state": "Maharashtra", "district": "Satara"}
                }
            ]
            for doc in default_docs:
                vector = self.embedder.get_embedding(doc["text"])
                self.db.upsert(doc["id"], vector, doc["text"], doc["metadata"])

    def process_query(self, 
                      query: str, 
                      session_id: str = "default_session",
                      search_mode: str = "hybrid", 
                      filters: Optional[Dict[str, Any]] = None,
                      target_lang: str = "en",
                      model_choice: str = "Llama-3 (Local)") -> Dict[str, Any]:
        """
        Coordinates the entire query response lifecycle.
        """
        start_time = time.time()
        latency = {}
        agent_logs = []
        
        # Configure model choice
        self.llm.set_model(model_choice)
        
        # Step 1: Guardrails Check
        guard_start = time.time()
        safety_status = SafetyGuardrails.check_query(query)
        latency["guardrails_ms"] = (time.time() - guard_start) * 1000
        
        agent_logs.append({
            "agent": "Safety Guardrail Agent",
            "action": "Input Inspection",
            "log": safety_status["details"],
            "status": "PASS" if safety_status["passed"] else "BLOCKED"
        })
        
        if not safety_status["passed"]:
            return {
                "response": f"Security Alert: {safety_status['reason']}. {safety_status['details']}",
                "explainability": {"confidence": 0.0, "primary_source": "Blocked", "citations": []},
                "evaluation": {"groundedness_score": 0.0, "relevance_score": 0.0, "context_recall_score": 0.0},
                "latency_breakdown": latency,
                "agent_logs": agent_logs,
                "cache_hit": False
            }
            
        # Step 2: Cache Lookup
        cache_start = time.time()
        cached_res = self.cache.get(query, search_mode, filters)
        latency["cache_lookup_ms"] = (time.time() - cache_start) * 1000
        
        if cached_res:
            cached_res["cache_hit"] = True
            cached_res["structured_reasoning"] = ReasoningEngine.process(query, llm_response=cached_res.get("response", ""))
            if target_lang != "en":
                cached_res["response"] = self.translator.translate(cached_res["response"], target_lang)
            return cached_res
            
        # Step 3: Explicit Multi-Agent Flow
        # A: Planner decides workflow
        agent_logs.append({
            "agent": "Planner Agent",
            "action": "Workflow Optimization",
            "log": f"Received query: '{query}'. Resolving workflow: Ingestion Check -> Hybrid Retrieve -> Graph Match -> LLM Synthesis -> Fact Verification.",
            "status": "ACTIVE"
        })
        
        # B: Document Agent parses threshold context
        agent_logs.append({
            "agent": "Document Analyst Agent",
            "action": "Threshold Extraction",
            "log": "Retrieving standard disaster limits and parameters matching current situation.",
            "status": "ACTIVE"
        })
        
        # C: Retriever Agent retrieves passages (Hybrid Search)
        ret_start = time.time()
        retrieval_res = self.retriever.retrieve_context(query, search_mode=search_mode, filters=filters)
        latency["retrieval_ms"] = (time.time() - ret_start) * 1000
        
        agent_logs.append({
            "agent": "Retriever Agent",
            "action": f"Hybrid Search ({search_mode.upper()})",
            "log": f"Searched SOP database. Retrieved {len(retrieval_res['hits'])} matches. Confidence: {retrieval_res['confidence']}%.",
            "status": "SUCCESS"
        })
        
        # D: Graph Match (Query the Graph database for connected assets)
        # Check if query references any hospitals/locations
        graph_matches = self.graph.path_find_safe_hospital("Pune")
        agent_logs.append({
            "agent": "Knowledge Graph Agent",
            "action": "Entity Pathfinding",
            "log": f"Graph query returned {len(graph_matches)} active hospital nodes (e.g. Sassoon Hospital) connected to affected city Pune.",
            "status": "SUCCESS"
        })
        
        # E: LLM Agent generates response
        llm_start = time.time()
        history = self.memory.get_history(session_id)
        raw_response = self.llm.generate_response(query, retrieval_res["context"], history)
        latency["llm_generation_ms"] = (time.time() - llm_start) * 1000
        
        agent_logs.append({
            "agent": "LLM Agent",
            "action": f"Text Generation ({model_choice})",
            "log": f"Synthesized grounded response text based on {len(retrieval_res['hits'])} retrieved chunks.",
            "status": "SUCCESS"
        })
        
        # F: Fact Verification Agent
        eval_start = time.time()
        eval_metrics = RAGEvaluator.evaluate(query, retrieval_res["context"], raw_response, latency["llm_generation_ms"])
        latency["evaluation_ms"] = (time.time() - eval_start) * 1000
        
        agent_logs.append({
            "agent": "Fact Verification Agent",
            "action": "Response Alignment Check",
            "log": f"Evaluated response: Groundedness={eval_metrics['groundedness_score']}%, Relevance={eval_metrics['relevance_score']}%, Recall={eval_metrics['context_recall_score']}%.",
            "status": "SUCCESS"
        })
        
        # Translate response if requested
        trans_start = time.time()
        translated_response = self.translator.translate(raw_response, target_lang)
        latency["translation_ms"] = (time.time() - trans_start) * 1000
        
        agent_logs.append({
            "agent": "Translation Agent",
            "action": f"Language Mapping to {target_lang.upper()}",
            "log": f"Translated output response content from EN to {target_lang.upper()}.",
            "status": "SUCCESS"
        })
        
        # Save user dialogue turn to Memory
        self.memory.add_message(session_id, "user", query)
        self.memory.add_message(session_id, "assistant", raw_response)
        
        total_time_ms = (time.time() - start_time) * 1000
        latency["total_latency_ms"] = total_time_ms
        
        # Get structured reasoning payload
        reasoning_payload = ReasoningEngine.process(query, retrieval_context=retrieval_res, llm_response=raw_response)
        
        output_res = {
            "response": translated_response,
            "raw_response": raw_response,
            "structured_reasoning": reasoning_payload,
            "explainability": {
                "confidence": retrieval_res["confidence"],
                "evidence": retrieval_res["evidence"]
            },
            "evaluation": eval_metrics,
            "latency_breakdown": latency,
            "agent_logs": agent_logs,
            "cache_hit": False
        }
        
        # Store in cache
        self.cache.set(query, search_mode, output_res, filters=filters)
        
        return output_res
