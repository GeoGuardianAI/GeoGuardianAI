"""
AI Reasoning Engine tests (priority 3).

The console derives its 5-card explainability payload in ai.reasoning.
These tests validate the schema, the branch routing, and that structured
evidence propagates real source names from retrieved documents.

A representative mock incident (the user's example) drives the scenario:
    {"location": "Pune", "disaster": "Flood", "river_level": 1.9,
     "critical_level": 1.8, "population_at_risk": 22400}
"""
import pytest

from ai.reasoning import ReasoningEngine
from ai.agents.document_agent import DocumentAgent
from ai.agents.report_agent import ReportAgent

MOCK_INCIDENT = {
    "location": "Pune",
    "disaster": "Flood",
    "river_level": 1.9,
    "critical_level": 1.8,
    "population_at_risk": 22400,
}

EXPECTED_KEYS = {
    "decision", "confidence", "severity", "reasoning", "evidence",
    "alternatives", "impact", "recommendations", "knowledge_graph_path",
}


def _fake_retrieval(title="Flood_SOP.txt", pages=1, text="Evacuation must begin when water exceeds the warning threshold of 1.8 meters."):
    return {
        "context": f"[Source: {title} - Page {pages}]\n{text}",
        "hits": [{
            "id": "flood_sop_1",
            "text": text,
            "metadata": {"title": title, "pages": pages, "disaster_type": "Flood"},
            "score": 0.94,
            "search_type": "hybrid",
        }],
        "confidence": 93.0,
        "evidence": {"primary_source": title, "citations": [{"document": title}]},
    }


@pytest.fixture()
def mock_incident_retrieval():
    """Retrieval whose sole hit carries the load-bearing 1.8m threshold clause."""
    return _fake_retrieval()


def test_schema_always_complete():
    payload = ReasoningEngine.process("What is the flood warning level?")
    assert EXPECTED_KEYS <= set(payload.keys())
    assert isinstance(payload["confidence"], (int, float))
    assert isinstance(payload["severity"], str)
    assert isinstance(payload["reasoning"], list)
    assert isinstance(payload["recommendations"], list)
    assert isinstance(payload["evidence"], list)
    assert isinstance(payload["alternatives"], list)


def test_evidence_card_shape():
    payload = ReasoningEngine.process("deploy rescue", retrieval_context=_fake_retrieval(), llm_response="ok")
    ev = payload["evidence"][0]
    assert {"source", "page", "section", "paragraph", "highlight", "confidence"} <= set(ev.keys())
    assert ev["source"] == "Flood_SOP.txt"  # real doc title, not a placeholder
    assert ev["page"] == 1
    assert "1.8 meters" in ev["paragraph"]


@pytest.mark.parametrize("query,expected_decision_fragment", [
    ("Where should we deploy rescue teams?", "Deploy Rescue Teams to Highway 48"),
    ("What should we do in the next 30 minutes?", "Zone A Phase 1 Evacuation"),
    ("What happens if we delay the evacuation?", "Delay Will Sever Primary Escape Routes"),
    ("What is the most critical decision right now?", "Rule 4.2 Hospital Reserve Beds"),
    ("Show me the evidence behind the flood warning", "Multi-Source Empirical Verification"),
])
def test_branch_routing(query, expected_decision_fragment):
    payload = ReasoningEngine.process(query, retrieval_context=_fake_retrieval())
    assert expected_decision_fragment in payload["decision"]


def test_general_branch_for_plain_query():
    payload = ReasoningEngine.process("What is the flood warning level?")
    assert "Operational Assessment" in payload["decision"]


def test_recommendations_have_required_fields():
    payload = ReasoningEngine.process("Where should we deploy rescue teams?")
    rec = payload["recommendations"][0]
    assert {"priority", "action", "reason", "confidence", "eta"} <= set(rec.keys())
    assert rec["priority"] >= 1
    assert rec["action"]
    assert rec["reason"]


def test_impact_card_populated():
    payload = ReasoningEngine.process("Where should we deploy rescue teams?")
    assert {"people", "roads_blocked", "bridges_damaged", "eta"} <= set(payload["impact"].keys())
    assert payload["impact"]["bridges_damaged"] >= 0


def test_no_context_uses_default_ndma_evidence():
    payload = ReasoningEngine.process("unrelated question", llm_response="hi")
    assert payload["evidence"][0]["source"] == "NDMA Master SOP 2026"


def test_mock_incident_sop_threshold_matches_reasoning(renewed):
    """The mock incident (river_level 1.9 > critical 1.8) must line up with the
    load-bearing SOP clause: evacuation begins at the 1.8m warning threshold."""
    orch = renewed
    doc_text = next(
        d["text"] for d in orch.db.documents
        if d["id"] == "flood_sop_1"
    )
    assert "1.8" in doc_text
    assert MOCK_INCIDENT["river_level"] > MOCK_INCIDENT["critical_level"]
    # The reasoning payload derived from that SOP must keep that number visible.
    payload = ReasoningEngine.process(
        "What is the evacuation threshold from the flood SOP?",
        retrieval_context=orch.retriever.retrieve_context("flood evacuation threshold 1.8 meters"),
    )
    joined = " ".join([ev.get("paragraph", "") for ev in payload["evidence"]])
    assert "1.8" in joined


def test_document_agent_extracts_thresholds():
    text = "Standard procedure: when the water level exceeds 1.8 m and within a 5 km zone, evacuate."
    thresholds = DocumentAgent().analyze_thresholds(text)
    assert thresholds["warning_threshold"].startswith("1.8")
    assert "5 km" in thresholds["evacuation_radius"]
    assert thresholds["recommended_supplies"]


def test_report_agent_generates_both_formats():
    brief = ReportAgent().generate_brief(
        disaster_type="Flood",
        location="Pune",
        severity="Critical",
        recommendations=["Deploy 5 rescue boats to Highway 48"],
        evidence=MOCK_INCIDENT and "SOP 2026 clause 1.8 mandates evacuation at 1.8m.",
    )
    assert "#" in brief["markdown"]
    assert "<html>" in brief["html"].lower()
    assert "Pune" in brief["summary"]


# ---------------------------------------------------------------------------
# #3 Reasoning-engine hardening: incident-driven logic, SOP provenance, and
# anti-fabrication guarantees.
# ---------------------------------------------------------------------------


def test_fixture_db_isolation(renewed):
    """The retriever must serve chunks from the SAME isolated DB as the rail."""
    orch = renewed
    assert orch.db is orch.retriever.db
    assert "gg_rag_db_" in str(orch.db.db_path)  # temp dir, not prod database/


def test_incident_severity_priority_risk(mock_incident_retrieval):
    payload = ReasoningEngine.process(
        "Pune flood", retrieval_context=mock_incident_retrieval, incident=MOCK_INCIDENT
    )
    assert payload["severity"] == "Critical"
    assert payload["priority"] == 1
    assert payload["risk"]["level"] == "Critical"
    assert "CRITICAL" in payload["decision"]
    assert payload["decision"].startswith("CRITICAL: Begin Flood evacuation for Pune")
    assert payload["impact"]["eta"] in ("Immediate", "Ongoing")


def test_incident_drives_recommendations_tied_to_sop(mock_incident_retrieval):
    payload = ReasoningEngine.process(
        "Pune flood", retrieval_context=mock_incident_retrieval, incident=MOCK_INCIDENT
    )
    rec = payload["recommendations"][0]
    assert rec["priority"] == 1
    assert "evacuation" in rec["action"].lower()
    assert "1.8" in rec["reason"]
    assert rec["sop_rule"] is not None  # threshold clause surfaced verbatim
    assert rec["evidence_used"]                 # card text cited back
    assert rec["inference"]                     # AI interpretation labeled
    assert any("threshold of 1.8" in r["rule"] for r in payload["sop_rules"])


def test_incident_confidence_reflects_evidence_and_sop_match(mock_incident_retrieval):
    payload = ReasoningEngine.process(
        "Pune flood", retrieval_context=mock_incident_retrieval, incident=MOCK_INCIDENT
    )
    assert 0 < payload["confidence"] <= 99
    assert payload["confidence"] >= 50  # matched threshold rule + strong hits


def test_below_threshold_incident_asks_to_monitor_not_evacuate(mock_incident_retrieval):
    incident = {**MOCK_INCIDENT, "river_level": 1.5}
    payload = ReasoningEngine.process(
        "Pune flood", retrieval_context=mock_incident_retrieval, incident=incident
    )
    assert payload["decision"].startswith("MONITOR:")
    assert "below" in payload["decision"]
    assert "Monit" in payload["recommendations"][0]["action"]
    assert not any("evacuat" in r["action"].lower() for r in payload["recommendations"])


def test_sop_rules_are_verbatim_and_only_from_documents(mock_incident_retrieval):
    payload = ReasoningEngine.process(
        "Pune flood", retrieval_context=mock_incident_retrieval, incident=MOCK_INCIDENT
    )
    sources = [ev["source"] for ev in payload["evidence"]]
    for rule in payload["sop_rules"]:
        assert {"rule", "source", "page", "clause"} <= set(rule.keys())
        assert rule["source"] in sources
        assert rule["rule"] in mock_incident_retrieval["hits"][0]["text"]  # verbatim


def test_no_rule_markers_means_no_invented_sop_payload():
    """If no retrieved sentence carries rule language, the engine must NOT
    claim the SOP mandates anything -> every rec is labeled pure AI inference."""
    text = "The city of Pune has a river that flows east. Many residents live near the banks."
    retrieval = {
        "context": f"[Source: Pune_Flood_Notes.txt - Page 1]\n{text}",
        "hits": [{
            "id": "notes_1",
            "text": text,
            "metadata": {"title": "Pune_Flood_Notes.txt", "pages": 1, "disaster_type": "Flood"},
            "score": 0.90,
            "search_type": "hybrid",
        }],
        "confidence": 90.0,
        "evidence": {"primary_source": "Pune_Flood_Notes.txt"},
    }
    payload = ReasoningEngine.process("Pune flood", retrieval_context=retrieval, incident=MOCK_INCIDENT)
    assert payload["sop_rules"] == []
    assert "no SOP threshold rule" in payload["decision"]
    assert any("AI interpretation, not a cited SOP mandate" in r for r in payload["reasoning"])
    for rec in payload["recommendations"]:
        assert rec["sop_rule"] is None
        assert rec["inference"]


def test_no_evidence_drops_confidence_to_zero(mock_incident_retrieval):
    empty = {**mock_incident_retrieval, "hits": [], "context": "", "confidence": 0.0}
    payload = ReasoningEngine.process("Pune flood", retrieval_context=empty, incident=MOCK_INCIDENT)
    assert payload["confidence"] == 0
    assert any("No SOP documents were retrieved" in r for r in payload["reasoning"])
    assert payload["sop_rules"] == []


def test_conflicting_sop_thresholds_downgrade_confidence():
    text_a = "Evacuation must begin when water exceeds the warning threshold of 1.8 meters."
    text_b = "Evacuation shall begin once water exceeds the critical level of 2.4 meters."
    retrieval = {
        "context": f"[Source: A - Page 1]\n{text_a}\n\n[Source: B - Page 2]\n{text_b}",
        "hits": [
            {"id": "a", "text": text_a, "metadata": {"title": "SOP_A", "pages": 1}, "score": 0.94, "search_type": "hybrid"},
            {"id": "b", "text": text_b, "metadata": {"title": "SOP_B", "pages": 2}, "score": 0.88, "search_type": "hybrid"},
        ],
        "confidence": 91.0,
        "evidence": {"primary_source": "SOP_A"},
    }
    payload = ReasoningEngine.process("Pune flood", retrieval_context=retrieval, incident=MOCK_INCIDENT)
    assert payload["risk"]["threshold_conflict"] is True
    assert payload["risk"]["conflicting_thresholds"] == ["1.8 meters", "2.4 meters"]
    assert payload["confidence"] <= 60
    assert any("conflicting thresholds" in r for r in payload["reasoning"])


def test_missing_incident_telemetry_yields_insufficient_information():
    incident = {"location": "Pune", "disaster": "Flood"}
    payload = ReasoningEngine.process("Pune flood", retrieval_context=mock_incident_retrieval, incident=incident)
    assert payload["decision"].startswith("INSUFFICIENT INFORMATION")
    assert payload["severity"] == "Unknown"
    assert payload["priority"] == 3
    assert payload["confidence"] <= 50
    assert any("telemetry" in r["action"].lower() for r in payload["recommendations"])


def test_no_incident_still_uses_query_branching():
    payload = ReasoningEngine.process("Where should rescue teams deploy?", retrieval_context=_fake_retrieval())
    assert "Deploy Rescue Teams to Highway 48" in payload["decision"]


# ---------------------------------------------------------------------------
# #6 Recommendation verification: every recommendation must be traceable,
# honestly labeled (SOP-based vs AI inference), free of unsupported assets,
# and carry confidence that reflects the quality of the evidence behind it.
# ---------------------------------------------------------------------------

def test_every_recommendation_is_traceable(mock_incident_retrieval):
    payload = ReasoningEngine.process(
        "Pune flood", retrieval_context=mock_incident_retrieval, incident=MOCK_INCIDENT
    )
    rule_texts = {r["rule"] for r in payload["sop_rules"]}
    for rec in payload["recommendations"]:
        assert {"sop_rule", "evidence_used", "inference"} <= set(rec.keys())
        assert rec["inference"], "every recommendation needs a labeled AI interpretation"
        if rec["sop_rule"] is not None:
            assert rec["sop_rule"] in rule_texts, "recommendation cites a rule that was never extracted"
    # The evacuation rec must point at the real 1.8m clause.
    assert payload["recommendations"][0]["sop_rule"] is not None


def test_ai_inference_recommendation_is_not_mislabeled():
    """A surge-capacity recommendation is a pure interpretation (no SOP clause
    states it) -- it must carry sop_rule=None and an explicit inference note."""
    incident = {**MOCK_INCIDENT, "population_at_risk": 250000}
    payload = ReasoningEngine.process(
        "Pune flood", retrieval_context=mock_incident_retrieval, incident=incident
    )
    surge = next(r for r in payload["recommendations"] if "surge" in r["action"].lower())
    assert surge["sop_rule"] is None
    assert surge["inference"]
    assert "capacity" in surge["reason"].lower() or "population" in surge["reason"].lower()


def test_no_unsupported_assets_in_recommendations(mock_incident_retrieval):
    payload = ReasoningEngine.process(
        "Pune flood", retrieval_context=mock_incident_retrieval, incident=MOCK_INCIDENT
    )
    actions = " ".join(r["action"].lower() for r in payload["recommendations"])
    for asset in ("helicopter", "ambulance", "drone", "army"):
        assert asset not in actions, f"recommendation invents unsupported asset: {asset}"


def test_weak_evidence_downgrades_recommendation_confidence():
    weak = {
        "context": "[Source: Weak.txt - Page 1]\nFlood notes for Pune.",
        "hits": [
            {"id": "w1", "text": "Flood notes for Pune.", "metadata": {"title": "Weak.txt", "pages": 1}, "score": 0.30, "search_type": "hybrid"},
            {"id": "w2", "text": "River information.", "metadata": {"title": "Weak.txt", "pages": 2}, "score": 0.25, "search_type": "hybrid"},
        ],
        "confidence": 27.0,
        "evidence": {"primary_source": "Weak.txt"},
    }
    payload = ReasoningEngine.process("Pune flood", retrieval_context=weak, incident=MOCK_INCIDENT)
    for rec in payload["recommendations"]:
        assert rec["confidence"] <= 40


def test_no_evidence_recommendation_confidence_zero():
    empty = {"hits": [], "context": "", "confidence": 0.0, "evidence": {}}
    payload = ReasoningEngine.process("Pune flood", retrieval_context=empty, incident=MOCK_INCIDENT)
    assert payload["confidence"] == 0
    for rec in payload["recommendations"]:
        assert rec["confidence"] == 0


def test_conflicting_thresholds_downgrade_recommendation_confidence():
    text_a = "Evacuation must begin when water exceeds the warning threshold of 1.8 meters."
    text_b = "Evacuation shall begin once water exceeds the critical level of 2.4 meters."
    conflict = {
        "context": f"[Source: A - Page 1]\n{text_a}\n\n[Source: B - Page 2]\n{text_b}",
        "hits": [
            {"id": "a", "text": text_a, "metadata": {"title": "A", "pages": 1}, "score": 0.94, "search_type": "hybrid"},
            {"id": "b", "text": text_b, "metadata": {"title": "B", "pages": 2}, "score": 0.88, "search_type": "hybrid"},
        ],
        "confidence": 91.0,
        "evidence": {"primary_source": "A"},
    }
    payload = ReasoningEngine.process("Pune flood", retrieval_context=conflict, incident=MOCK_INCIDENT)
    assert payload["risk"]["threshold_conflict"] is True
    for rec in payload["recommendations"]:
        assert rec["confidence"] <= 60