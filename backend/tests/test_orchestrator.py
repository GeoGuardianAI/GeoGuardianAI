"""
Orchestrator multi-agent workflow tests (priority 4).

Covers the full lifecycle: guardrail -> planner -> retriever -> KG -> LLM ->
fact-verification -> translation -- plus an upload-then-query end-to-end loop.
"""
import re
import uuid

from helpers import make_upload, run


def test_full_pipeline_agent_sequence(renewed):
    orch = renewed
    result = orch.process_query("What should we do in the next 30 minutes?")
    assert result["response"]
    assert result["raw_response"]
    assert result["explainability"]["evidence"]["citations"]
    assert result["structured_reasoning"]["recommendations"] or result["structured_reasoning"]["impact"]
    assert result["evaluation"]["groundedness_score"] >= 0

    log_statuses = [log["status"] for log in result["agent_logs"]]
    assert "SUCCESS" in log_statuses and "ACTIVE" in log_statuses
    assert result["latency_breakdown"]["total_latency_ms"] >= 0


def test_orchestrator_plurality_of_agent_types(renewed):
    orch = renewed
    result = orch.process_query("Which hospitals should be activated?")
    names = [log["agent"] for log in result["agent_logs"]]
    assert len(set(names)) >= 5


def test_graph_lookup_returns_active_hospitals(renewed):
    orch = renewed
    safe = orch.graph.path_find_safe_hospital("Pune")
    assert safe
    sassoon = [s for s in safe if "Sassoon" in s["hospital"]]
    assert sassoon and sassoon[0]["status"] == "Active"


def test_translation_route_hi(renewed):
    orch = renewed
    result = orch.process_query("What is the flood warning level?", target_lang="hi")
    assert result["raw_response"]
    assert re.search(r"[\u0900-\u097F]", result["response"]), "response was not translated to Devanagari"
    assert result["response"] == result["raw_response"] or re.search(r"[\u0900-\u097F]", result["response"])


def test_translation_route_en_identity(renewed):
    orch = renewed
    result = orch.process_query("What is the flood warning level?", target_lang="en")
    assert result["response"] == result["raw_response"]


def test_unknown_model_choice_falls_back_gracefully(renewed):
    orch = renewed
    result = orch.process_query("What is the flood warning level?", model_choice="NotARealModel")
    assert result["response"]


def test_upload_then_query_end_to_end(fresh_orchestrator_factory):
    """Ingest a new SOP then ask a question whose answer only exists in it."""
    orch = fresh_orchestrator_factory(seed=True)
    from ai.api.upload import upload_document

    content = (
        "Route 7 closure protocol: the district must close Route 7 to all traffic "
        "when the river water level exceeds 2.1 meters anywhere along the corridor."
    )
    resp = run(upload_document(
        make_upload("route7_protocol.txt", content.encode("utf-8")),
        disaster_type="Flood", state="Maharashtra", district="Pune",
    ))
    assert resp["status"] == "success"

    result = orch.process_query("What is the water level threshold for closing Route 7?")
    combined = result["response"] + result["raw_response"]
    assert "Route 7" in combined
    assert "2.1" in combined
    top_doc = result["explainability"]["evidence"]["citations"][0]["document"]
    assert top_doc == "route7_protocol.txt"


def test_orchestrator_concurrent_sessions_isolated(renewed):
    orch = renewed
    s1, s2 = f"s-{uuid.uuid4().hex}", f"s-{uuid.uuid4().hex}"
    orch.process_query("What is the flood warning level?", session_id=s1)
    orch.process_query("Which roads are blocked?", session_id=s2)
    assert orch.memory.get_history(s1)
    assert orch.memory.get_history(s2)
    assert orch.memory.get_history(s1) != orch.memory.get_history(s2)


def test_cached_response_still_has_structured_reasoning(renewed):
    orch = renewed
    query = f"navigate cache reasoning {uuid.uuid4().hex}"
    orch.process_query(query)
    cached = orch.process_query(query)
    assert cached["cache_hit"] is True
    assert cached["structured_reasoning"]["decision"]


def test_process_query_requires_no_external_services(renewed):
    """The whole pipeline must complete even with no Ollama/Gemini available,
    because the rule-based synthesizer is the safety net."""
    orch = renewed
    result = orch.process_query("Summarize the flood situation for district command")
    assert result["response"]
    assert "### " in result["raw_response"] or "Operational" in result["structured_reasoning"]["decision"]


def test_monitoring_metrics_endpoint(api_orchestrator):
    from ai.api.chat import monitoring_metrics

    orch = api_orchestrator
    monkeys = run(monitoring_metrics())
    assert monkeys["indexed_documents_count"] >= 1
    assert monkeys["total_chunks_count"] >= 1
    assert monkeys["system_health"] == "Healthy"
    assert monkeys["indexed_documents"][0]["title"]


def test_speech_endpoint_transcribes_and_answers(api_orchestrator):
    from ai.api.chat import speech_endpoint

    orch = api_orchestrator
    result = run(speech_endpoint(
        make_upload("warning_level.wav", b"fake audio"),
        session_id=None, search_mode="hybrid", target_lang="en", model_choice="Llama-3 (Local)",
    ))
    assert result["transcribed_query"] == "What is the flood warning level?"
    assert result["response"]
    assert result["evaluation"]["groundedness_score"] > 0
    assert not __import__("os").path.exists(__import__("os").path.join("temp_speech", "warning_level.wav"))


# ---------------------------------------------------------------------------
# #4 Orchestrator hardening: agent data-flow, incident pass-through, evidence
# survival, and graceful degradation on empty/malformed inputs.
# ---------------------------------------------------------------------------

MOCK_INCIDENT = {
    "location": "Pune",
    "disaster": "Flood",
    "river_level": 1.9,
    "critical_level": 1.8,
    "population_at_risk": 22400,
}


def test_incident_flows_from_orchestrator_into_reasoning(renewed):
    """process_query(incident=...) must thread telemetry into the Reasoning
    Agent so the structured payload derives severity/priority from it."""
    orch = renewed
    result = orch.process_query(
        "Flood evacuation threshold for Pune", incident=MOCK_INCIDENT
    )
    payload = result["structured_reasoning"]
    assert payload["severity"] == "Critical"
    assert payload["priority"] == 1
    assert payload["decision"].startswith("CRITICAL: Begin Flood evacuation for Pune")
    assert any(line.startswith("[SOP]") for line in payload["reasoning"])
    rec = payload["recommendations"][0]
    assert "evacuation" in rec["action"].lower()
    assert rec["sop_rule"] is not None  # the 1.8m threshold clause, verbatim
    assert 0 < payload["confidence"] <= 99


def test_agent_logs_ordered_and_complete(renewed):
    orch = renewed
    result = orch.process_query(f"flood status probe {uuid.uuid4().hex}")
    names = [log["agent"] for log in result["agent_logs"]]
    assert names == [
        "Safety Guardrail Agent",
        "Planner Agent",
        "Document Analyst Agent",
        "Retriever Agent",
        "Knowledge Graph Agent",
        "LLM Agent",
        "Fact Verification Agent",
        "Translation Agent",
    ]
    for log in result["agent_logs"]:
        assert {"agent", "action", "log", "status"} <= set(log.keys())
        assert log["status"] in {"PASS", "BLOCKED", "ACTIVE", "SUCCESS"}
    retriever_log = next(l for l in result["agent_logs"] if l["agent"] == "Retriever Agent")
    assert "matches" in retriever_log["log"].lower()


def test_document_agent_thresholds_flow_into_reasoning(renewed):
    """Document Agent threshold extraction -> retrieval evidence -> reasoning
    payload must all surface the SAME 1.8m number for the seed flood SOP."""
    from ai.agents.document_agent import DocumentAgent

    orch = renewed
    doc_text = next(
        d["text"] for d in orch.db.documents if d["id"] == "flood_sop_1"
    )
    thresholds = DocumentAgent().analyze_thresholds(doc_text)
    assert thresholds["warning_threshold"].startswith("1.8")

    result = orch.process_query("What is the flood warning level?")
    payload = result["structured_reasoning"]
    joined_evidence = " ".join(ev["paragraph"] for ev in payload["evidence"])
    assert "1.8" in joined_evidence
    assert any(ev["source"] == "Flood_SOP.txt" for ev in payload["evidence"])


def test_empty_retrieval_degrades_gracefully(fresh_orchestrator_factory):
    """With no indexed documents the orchestrator must still return a full
    response envelope (default protocol + zero-confidence signals), not crash."""
    orch = fresh_orchestrator_factory(seed=False)
    result = orch.process_query("What is the flood protocol?")
    assert result["response"]                       # default safety-net protocol
    assert result["explainability"]["confidence"] == 0.0
    assert result["explainability"]["evidence"]["citations"] == []
    assert result["evaluation"]["groundedness_score"] == 0.0
    assert result["structured_reasoning"]["decision"]
    assert [l["agent"] for l in result["agent_logs"]] == [
        "Safety Guardrail Agent",
        "Planner Agent",
        "Document Analyst Agent",
        "Retriever Agent",
        "Knowledge Graph Agent",
        "LLM Agent",
        "Fact Verification Agent",
        "Translation Agent",
    ]


def test_malformed_empty_llm_response_is_absorbed(renewed, monkeypatch):
    """A degenerate/empty LLM output must not crash the pipeline; the reasoning
    payload and evaluation metadata still get emitted."""
    orch = renewed
    monkeypatch.setattr(orch.llm.__class__, "generate_response",
                        lambda self, query, context, history=None: "")
    result = orch.process_query(f"empty response probe {uuid.uuid4().hex}")
    assert result["raw_response"] == ""
    assert result["structured_reasoning"]["decision"]
    assert "groundedness_score" in result["evaluation"]
    assert result["cache_hit"] is False
    assert result["explainability"]["confidence"] > 0 or result["explainability"]["confidence"] == 0.0


def test_upload_reason_report_end_to_end(fresh_orchestrator_factory):
    """Upload -> retrieve -> reason -> report: the uploaded doc must surface in
    both the reasoning evidence AND the compiled report briefing."""
    from ai.agents.report_agent import ReportAgent
    from ai.api.upload import upload_document

    orch = fresh_orchestrator_factory(seed=True)
    content = (
        "Railway crossing safety SOP: the district must close the Kamshet railway "
        "crossing to vehicles when river level exceeds 3.1 meters at the bridge gauge."
    )
    resp = run(upload_document(
        make_upload("railway_sop.txt", content.encode("utf-8")),
        disaster_type="Flood", state="Maharashtra", district="Pune",
    ))
    assert resp["status"] == "success"

    result = orch.process_query("What is the railway crossing closure threshold?")
    payload = result["structured_reasoning"]
    assert any(ev["source"] == "railway_sop.txt" for ev in payload["evidence"])

    brief = ReportAgent().generate_brief(
        disaster_type="Flood",
        location="Pune",
        severity=payload["severity"],
        recommendations=[r["action"] for r in payload["recommendations"]] or ["Monitor"],
        evidence=payload["evidence"][0]["paragraph"],
    )
    assert "railway_sop.txt" in brief["markdown"] or "3.1" in brief["markdown"]
    assert "Pune" in brief["summary"]