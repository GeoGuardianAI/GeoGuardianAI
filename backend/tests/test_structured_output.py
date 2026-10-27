"""
Structured AI output / response schema validation (priority 5).

The public API contract (chat, search, upload, reasoning payload) is a
JSON payload the frontend serializes and renders. These tests pin that
contract with pydantic-schema validation and JSON-serializability checks.
"""
import json

import pytest
from pydantic import BaseModel, Field

from ai.reasoning import ReasoningEngine
from helpers import make_upload, run


class Recommendation(BaseModel):
    priority: int = Field(ge=1)
    action: str
    reason: str
    confidence: int = Field(ge=0, le=100)
    eta: str


class EvidenceCard(BaseModel):
    source: str
    page: int
    section: str
    paragraph: str
    highlight: str
    confidence: int = Field(ge=0, le=100)


class ReasoningPayload(BaseModel):
    decision: str
    confidence: int = Field(ge=0, le=100)
    severity: str
    reasoning: list[str]
    evidence: list[EvidenceCard]
    alternatives: list[dict]
    impact: dict
    recommendations: list[Recommendation]
    knowledge_graph_path: list[str]


class Citation(BaseModel):
    rank: int = Field(ge=1)
    document: str
    page: int = Field(ge=1)
    snippet: str
    score: float
    type: str


class Explainability(BaseModel):
    confidence: float = Field(ge=0, le=100)
    evidence: dict


class Evaluation(BaseModel):
    groundedness_score: float = Field(ge=0, le=100)
    relevance_score: float = Field(ge=0, le=100)
    context_recall_score: float = Field(ge=0, le=100)
    latency_ms: float
    status: str


class ChatOutput(BaseModel):
    response: str
    raw_response: str
    structured_reasoning: ReasoningPayload
    explainability: Explainability
    evaluation: Evaluation
    latency_breakdown: dict
    agent_logs: list[dict]
    cache_hit: bool


def test_reasoning_payload_validates_against_schema():
    payload = ReasoningEngine.process("Where should we deploy rescue teams?", _retrieval())
    ReasoningPayload.model_validate(payload)


def test_reasoning_payload_is_json_serializable():
    payload = ReasoningEngine.process("What is the most critical decision right now?")
    dumped = json.dumps(payload)
    assert json.loads(dumped) == payload


def test_reasoning_payload_deterministic():
    a = ReasoningEngine.process("What is the flood warning level?")
    b = ReasoningEngine.process("What is the flood warning level?")
    assert a == b


def test_chat_output_validates_against_schema(renewed):
    orch = renewed
    result = orch.process_query("What is the flood warning level?")
    ChatOutput.model_validate(result)


def test_chat_output_confidence_in_range(renewed):
    orch = renewed
    result = orch.process_query("What is the flood warning level?")
    conf = result["explainability"]["confidence"]
    assert 0.0 <= conf <= 100.0


def test_chat_output_is_json_serializable(renewed):
    """The full chat response must survive json.dumps (the API boundary)."""
    orch = renewed
    result = orch.process_query("Where should rescue teams deploy?")
    dumped = json.dumps(result)
    round_tripped = json.loads(dumped)
    assert round_tripped["response"] == result["response"]
    assert round_tripped["cache_hit"] == result["cache_hit"]


def test_evaluation_scores_clamped(renewed):
    orch = renewed
    result = orch.process_query("What is the flood warning level?")
    ev = result["evaluation"]
    for key in ("groundedness_score", "relevance_score", "context_recall_score"):
        assert 0.0 <= ev[key] <= 100.0


def test_evidence_citations_validate(renewed):
    orch = renewed
    result = orch.process_query("What is the flood warning level?")
    for c in result["explainability"]["evidence"]["citations"]:
        Citation.model_validate(c)


def test_search_output_json_serializable(api_orchestrator):
    from ai.api.search import search_endpoint

    result = {"hits": None}
    result = run(search_endpoint(
        q="rescue boats",
        top_k=2,
        mode="hybrid",
        disaster_type=None,
        state=None,
        district=None,
    ))
    dumped = json.dumps(result)
    assert json.loads(dumped)["query"] == "rescue boats"


def test_upload_output_json_serializable(api_orchestrator):
    from ai.api.upload import upload_document

    result = run(upload_document(
        make_upload("serialize_sop.txt", b"Evacuation procedure: alert shelters within 5 km."),
        disaster_type="Flood", state="Maharashtra", district="Pune",
    ))
    json.loads(json.dumps(result))


def _retrieval():
    return {
        "context": "[Source: Flood_SOP.txt - Page 1]\nEvacuate below the 1.8 meters threshold.",
        "hits": [{
            "id": "flood_sop_1",
            "text": "Evacuate below the 1.8 meters threshold.",
            "metadata": {"title": "Flood_SOP.txt", "pages": 1, "disaster_type": "Flood", "state": "Maharashtra", "district": "Pune"},
            "score": 0.95,
            "search_type": "hybrid",
        }],
        "confidence": 91.0,
        "evidence": {"primary_source": "Flood_SOP.txt", "citations": []},
    }


# ---------------------------------------------------------------------------
# #5 Structured-output hardening: the pydantic contract must REJECT missing
# fields, wrong datatypes, out-of-range confidence, invalid priority/rank --
# while still recovering cleanly from malformed / plain-text LLM output.
# ---------------------------------------------------------------------------
from pydantic import ValidationError


def test_missing_required_field_rejected():
    bad = ReasoningEngine.process("What is the flood warning level?")
    del bad["decision"]
    with pytest.raises(ValidationError):
        ReasoningPayload.model_validate(bad)


def test_wrong_datatype_rejected():
    bad = ReasoningEngine.process("What is the flood warning level?")
    bad["confidence"] = "high"          # int expected
    with pytest.raises(ValidationError):
        ReasoningPayload.model_validate(bad)
    bad = ReasoningEngine.process("What is the flood warning level?")
    bad["reasoning"] = "one string"      # list expected
    with pytest.raises(ValidationError):
        ReasoningPayload.model_validate(bad)


def test_priority_below_one_rejected():
    rec = ReasoningEngine.process("Where should rescue teams deploy?")["recommendations"][0]
    rec = {**rec, "priority": 0}
    with pytest.raises(ValidationError):
        Recommendation.model_validate(rec)


def test_confidence_out_of_range_rejected():
    rec = ReasoningEngine.process("Where should rescue teams deploy?")["recommendations"][0]
    for bad in (101, -1):
        with pytest.raises(ValidationError):
            Recommendation.model_validate({**rec, "confidence": bad})
    rec["confidence"] = 50
    Recommendation.model_validate({**rec, "confidence": 100})   # boundary ok
    Recommendation.model_validate({**rec, "confidence": 0})      # boundary ok


def test_evidence_card_confidence_bounds_rejected():
    ev = ReasoningEngine.process("What is the flood warning level?")["evidence"][0]
    with pytest.raises(ValidationError):
        EvidenceCard.model_validate({**ev, "confidence": 250})
    EvidenceCard.model_validate({**ev, "confidence": 100})


def test_empty_evidence_is_structurally_valid():
    payload = ReasoningEngine.process("What is the flood warning level?")
    payload["evidence"] = []
    ReasoningPayload.model_validate(payload)   # empty list satisfies list[EvidenceCard]


def test_invalid_citation_rank_and_page_rejected():
    with pytest.raises(ValidationError):
        Citation.model_validate({"rank": 0, "document": "Flood_SOP.txt", "page": 3, "snippet": "x", "score": 0.9, "type": "hybrid"})
    with pytest.raises(ValidationError):
        Citation.model_validate({"rank": 1, "document": "Flood_SOP.txt", "page": 0, "snippet": "x", "score": 0.9, "type": "hybrid"})
    Citation.model_validate({"rank": 2, "document": "Flood_SOP.txt", "page": 1, "snippet": "x", "score": 0.9, "type": "hybrid"})


def test_malformed_json_llm_response_does_not_break_payload():
    """A truncated/invalid JSON string from the LLM must not corrupt the
    structured reasoning payload -- the engine recovers with a valid schema."""
    payload = ReasoningEngine.process(
        "Where should rescue teams deploy?",
        retrieval_context=_retrieval(),
        llm_response='{"recommendations": [{"priority": ',
    )
    ReasoningPayload.model_validate(payload)


def test_plain_text_llm_response_does_not_break_payload():
    """An LLM that answers in markdown prose instead of JSON still yields a
    complete, schema-valid structured decision."""
    payload = ReasoningEngine.process(
        "What should we do in the next 30 minutes?",
        llm_response="### Action Plan\n- dispatch boats (plain text, not JSON)",
    )
    ReasoningPayload.model_validate(payload)


def test_chat_contract_survives_incident_reasoning(renewed):
    """The chat envelope must validate even when reasoning is incident-driven."""
    result = renewed.process_query(
        "Flood evacuation threshold for Pune",
        incident={"location": "Pune", "disaster": "Flood",
                  "river_level": 1.9, "critical_level": 1.8, "population_at_risk": 22400},
    )
    ChatOutput.model_validate(result)