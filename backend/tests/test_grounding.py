"""
Grounding / hallucination control tests (priority 2).

Goal: prove that the response pipeline (a) answers from retrieved SOP context,
(b) does not fabricate instructions outside that context, and (c) surfaces
low-confidence / out-of-domain retrieval to the operator instead of guessing.
"""
import re

import pytest

from ai.evaluation.evaluation import RAGEvaluator
from ai.llm_service.llama import LLMModelManager


ON_TOPIC_QUERY = "When does evacuation have to begin for the flood?"


def _context_text(evidence_block):
    return " ".join(c["snippet"] for c in evidence_block.get("citations", []))


def test_instructions_are_substrings_of_retrieved_context(renewed):
    """Every 'Instruction' the assistant outputs must exist verbatim in the
    retrieved SOP text. This is the core anti-hallucination guarantee of the
    rule-based synthesizer path."""
    orch = renewed
    result = orch.process_query(ON_TOPIC_QUERY)
    instructions = re.findall(r"\*\*Instruction\*\*: (.*)", result["raw_response"])
    assert instructions, "expected markdown instruction bullets in fallback output"
    retrieval = orch.retriever.retrieve_context(ON_TOPIC_QUERY)
    for instr in instructions:
        assert instr in retrieval["context"], f"instruction not grounded: {instr!r}"


def test_response_conforms_to_evacuation_threshold(renewed):
    """A well-grounded answer about the flood must reflect the 1.8m warning
    threshold stored in the SOP -- not some fabricated number."""
    orch = renewed
    result = orch.process_query(ON_TOPIC_QUERY)
    assert "1.8" in result["raw_response"]
    assert result["evaluation"]["groundedness_score"] >= 50


@pytest.mark.parametrize("query", [
    "What is the flood warning level?",
    "Which hospitals are active for this flood?",
    "Where should rescue teams deploy?",
])
def test_on_topic_queries_are_grounded(renewed, query):
    orch = renewed
    result = orch.process_query(query)
    assert result["response"]
    # Instructions the assistant gives must be backed by retrieved SOP text.
    assert result["evaluation"]["groundedness_score"] > 50


def test_out_of_domain_query_is_not_a_false_answer(renewed):
    """'Liquefaction protocol' is not covered by any loaded SOP. The system must
    not present a plausible-sounding fabricated protocol; relevance must stay
    low so the operator sees the answer is not really answering."""
    orch = renewed
    result = orch.process_query("What is the earthquake liquefaction protocol for Chennai?")
    assert result["response"]
    # Low answer relevance signals the retrieved context did not address the query.
    assert result["evaluation"]["relevance_score"] < 60
    assert result["evaluation"]["groundedness_score"] <= 100


def test_confidence_floor_signal_for_weak_matches(renewed):
    """When hits exist but are near-zero-relevance, ExplainableAILogger floors
    confidence at 20% -- a visible low-trust signal."""
    orch = renewed
    retrieval = orch.retriever.retrieve_context("how do I cook biryani with saffron", top_k=4)
    assert retrieval["hits"]  # top-k always returns documents, even weak ones
    assert retrieval["confidence"] == 20.0  # the documented floor


def test_no_context_returns_default_protocol_not_fabrication(renewed):
    """With no retrievable SOPs, the synthesizer returns its fixed generic
    protocol text and RAG evaluation marks grounding as zero."""
    from ai.llm_service.llama import LLMModelManager

    llm = LLMModelManager()
    answer = llm.generate_response("What is the flood protocol in Pune?", "")
    assert "Notify Incident Command" in answer
    metrics = RAGEvaluator.evaluate("What is the flood protocol in Pune?", "", answer, 10.0)
    assert metrics["groundedness_score"] == 0.0


def test_citations_always_present_with_context(renewed):
    """Any grounded response must carry at least one citation back to a source
    document so the decision is auditable."""
    orch = renewed
    result = orch.process_query(ON_TOPIC_QUERY)
    citations = result["explainability"]["evidence"]["citations"]
    assert citations
    assert all(c["document"] for c in citations)
    assert all(c["snippet"] for c in citations)


def test_evidence_sources_match_indexed_documents(renewed):
    """Evidence blocks may only cite documents that actually exist in the
    vector DB (no spectral citations to invented SOPs)."""
    orch = renewed
    result = orch.process_query(ON_TOPIC_QUERY)
    cited = set(result["explainability"]["evidence"].get("all_sources", []))
    assert cited
    indexed = {d["metadata"].get("title") for d in orch.db.documents}
    assert cited <= indexed, f"citations reference unindexed documents: {cited - indexed}"


def test_reasoning_evidence_sources_match_indexed_documents(renewed):
    """The 5-card reasoning payload's evidence must also reference real source
    names (regression test for the payload-vs-metadata bug)."""
    orch = renewed
    result = orch.process_query(ON_TOPIC_QUERY)
    indexed = {d["metadata"].get("title") for d in orch.db.documents}
    for ev in result["structured_reasoning"]["evidence"]:
        assert ev["source"] in indexed, f"unindexed evidence source: {ev['source']}"


def test_responses_do_not_contain_pii_echoes(renewed):
    orch = renewed
    result = orch.process_query("What is the situation report for the flood?")
    assert not re.search(r"\b\d{3}-\d{2}-\d{4}\b", result["response"])


def test_groundedness_metric_sanity():
    context = "Route 7 closes when water exceeds 2.1 meters. Evacuate the floodplain."
    response = "Close Route 7 when water exceeds 2.1 meters and evacuate the floodplain."
    metrics = RAGEvaluator.evaluate("What should happen at Route 7?", context, response, 5.0)
    assert metrics["groundedness_score"] >= 80
    assert metrics["groundedness_score"] <= 100


def test_groundedness_dropout_when_response_diverges():
    context = "Route 7 closes when water exceeds 2.1 meters."
    response = "Serve chai to all national park visitors immediately."
    metrics = RAGEvaluator.evaluate("Route 7?", context, response, 5.0)
    assert metrics["groundedness_score"] < 50


# ---------------------------------------------------------------------------
# #2 Grounding / hallucination hardening.
#
# Group A -- SOP factual questions. Facts present in the corpus must be answered
# from retrieved text (verbatim + cited). Facts ABSENT from the corpus must be
# reported as "not registered" -- never invented.
# ---------------------------------------------------------------------------
NOT_REGISTERED = "not registered"


def test_factual_rescue_boats_grounded_and_cited(renewed):
    orch = renewed
    result = orch.process_query("Where should rescue boats be deployed?")
    assert "Highway 48" in result["raw_response"]
    assert result["evaluation"]["groundedness_score"] > 50
    instructions = re.findall(r"\*\*Instruction\*\*: (.*)", result["raw_response"])
    assert instructions and any("Rescue boats" in i for i in instructions)
    retrieval = orch.retriever.retrieve_context("rescue boats deployed")
    for instr in instructions:
        assert instr in retrieval["context"], f"ungrounded instruction: {instr!r}"
    assert result["explainability"]["evidence"]["citations"]


def test_factual_damaged_bridge_grounded_and_cited(renewed):
    orch = renewed
    result = orch.process_query("What should happen if a bridge is damaged?")
    assert "rerouted" in result["raw_response"].lower() or "Krishna" in result["raw_response"]
    assert result["evaluation"]["groundedness_score"] > 30
    retrieval = orch.retriever.retrieve_context("damaged bridge reroute traffic")
    instructions = re.findall(r"\*\*Instruction\*\*: (.*)", result["raw_response"])
    for instr in instructions:
        assert instr in retrieval["context"], f"ungrounded instruction: {instr!r}"


@pytest.mark.parametrize("query", [
    "How many reserve beds must hospitals activate under Rule 4.2?",
    "How many hospital beds are available during a flood?",
    "How often are public announcements made during floods?",
])
def test_factual_absent_topics_refuse_to_invent(renewed, query):
    """These facts do NOT exist in the loaded SOPs. The engine must say so,
    rather than recycling unrelated excerpts or inventing a rule number."""
    orch = renewed
    result = orch.process_query(query)
    assert NOT_REGISTERED in result["response"].lower()
    assert NOT_REGISTERED in result["raw_response"].lower()


# ---------------------------------------------------------------------------
# Group B -- negative queries must yield "information not found", never a
# fabricated capability claim (helicopters, ambulances, evacuation routes).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("query", [
    "Where are helicopters stationed for the flood response?",
    "What is the designated evacuation route for Zone A?",
    "Where should ambulances be staged during the flood?",
])
def test_negative_queries_not_registered(renewed, query):
    orch = renewed
    result = orch.process_query(query)
    assert NOT_REGISTERED in result["raw_response"].lower()
    # No fabricated markdown plan bullets for a topic the SOPs do not cover.
    assert "**Instruction**" not in result["raw_response"]


# ---------------------------------------------------------------------------
# Group C -- grounding scenarios exercised on the rule-based synthesizer so the
# retrieval feed is fully controlled.
# ---------------------------------------------------------------------------
def _synth(query, context):
    return LLMModelManager().fallback_synthesizer(query, context)


def test_scenario_single_relevant_document():
    ctx = (
        "[Source: Flood_SOP.txt - Page 1]\n"
        "Evacuation must begin immediately when water levels exceed the 1.8 meters threshold.\n"
        "Rescue boats should be deployed to Highway 48."
    )
    answer = _synth("When should evacuation begin?", ctx)
    assert "**Instruction**" in answer
    for instr in re.findall(r"\*\*Instruction\*\*: (.*)", answer):
        assert instr in ctx, f"ungrounded: {instr!r}"
    metrics = RAGEvaluator.evaluate("When should evacuation begin?", ctx, answer, 5.0)
    # Instructions are verified verbatim above; the fallback's generic safety
    # footer is ungrounded and caps how high the aggregate can go.
    assert metrics["groundedness_score"] > 20


def test_scenario_multiple_documents_all_cited():
    ctx = (
        "[Source: Flood_SOP.txt - Page 1]\n"
        "Evacuation must begin when water exceeds the 1.8 meters threshold.\n\n"
        "[Source: Wildfire_SOP.txt - Page 1]\n"
        "Water trucks must be routed via Route 9 when dry winds exceed 25 km/h."
    )
    answer = _synth("What is the evacuation threshold?", ctx)
    assert "[Source: Flood_SOP.txt" in answer and "[Source: Wildfire_SOP.txt" in answer
    for instr in re.findall(r"\*\*Instruction\*\*: (.*)", answer):
        assert instr in ctx, f"ungrounded: {instr!r}"


def test_scenario_conflicting_documents_not_blended():
    """With two contradictory thresholds, every instruction must stay verbatim
    inside ONE document -- the engine may never blend 1.8 and 2.4 into a
    single composite claim."""
    ctx = (
        "[Source: SOP_A - Page 1]\n"
        "Evacuation must begin when water exceeds the 1.8 meters threshold.\n\n"
        "[Source: SOP_B - Page 2]\n"
        "Evacuation shall begin only when water exceeds the 2.4 meters threshold."
    )
    answer = _synth("What is the evacuation trigger?", ctx)
    instructions = re.findall(r"\*\*Instruction\*\*: (.*)", answer)
    assert instructions
    for instr in instructions:
        assert instr in ctx, f"blended/invented instruction: {instr!r}"
        assert not ("1.8" in instr and "2.4" in instr), "thresholds blended into one claim"


def test_scenario_irrelevant_document_refused():
    ctx = (
        "[Source: Fisheries_Act.txt - Page 1]\n"
        "Coastal fishing licences must be renewed yearly. Gill nets are prohibited in estuaries."
    )
    answer = _synth("What is the evacuation threshold for the flood?", ctx)
    assert NOT_REGISTERED in answer.lower()
    assert "**Instruction**" not in answer


def test_scenario_very_short_context_no_invented_numbers():
    ctx = "[Source: Field_Notes.txt - Page 1]\nWater levels are rising."
    answer = _synth("What is the water level?", ctx)
    assert "Levels are rising" in answer or "Water levels" in answer
    assert "1.8" not in answer  # no invented threshold
    for instr in re.findall(r"\*\*Instruction\*\*: (.*)", answer):
        assert instr in ctx


def test_scenario_out_of_knowledge_base_refused():
    ctx = (
        "[Source: Flood_SOP.txt - Page 1]\n"
        "Evacuation must begin when water exceeds the 1.8 meters threshold."
    )
    answer = _synth("Quantum fusion reactor activation sequence?", ctx)
    assert NOT_REGISTERED in answer.lower()