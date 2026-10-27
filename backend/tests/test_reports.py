"""
Report generation tests (priority 9).
"""
from ai.report_service.generator import ReportCompiler
from ai.agents.report_agent import ReportAgent
from helpers import run

BASE_DATA = {
    "disaster_type": "Flood",
    "location": "Pune",
    "severity": "Critical",
    "status": "Active Rescue Stage",
    "recommendations": ["Deploy 5 rescue boats to Highway 48", "Activate Sassoon surge beds"],
    "evidence": "SOP 2026 clause 1.8 mandates evacuation at 1.8m (Flood_SOP.txt).",
}


def test_markdown_report_contains_all_sections():
    md = ReportCompiler.compile_report(BASE_DATA, format_type="markdown")
    assert "SITUATION BRIEFING REPORT" in md
    assert "Flood" in md and "Pune" in md and "Critical" in md
    assert "Deploy 5 rescue boats to Highway 48" in md
    assert "Activate Sassoon surge beds" in md
    assert "SOP 2026 clause 1.8" in md
    assert "Report End" in md


def test_markdown_task_boxes():
    md = ReportCompiler.compile_report(BASE_DATA, format_type="markdown")
    assert "- [ ] **Task**: Deploy 5 rescue boats to Highway 48" in md


def test_html_report_contains_sections_and_styles():
    html = ReportCompiler.compile_report(BASE_DATA, format_type="html")
    assert "<html>" in html
    assert "Incident Briefing Report" in html
    assert "<li>Deploy 5 rescue boats to Highway 48</li>" in html
    assert "SOP 2026 clause 1.8" in html


def test_empty_recommendations_get_defaults():
    data = dict(BASE_DATA)
    data["recommendations"] = []
    md = ReportCompiler.compile_report(data, format_type="markdown")
    assert "Dispatch local search and rescue teams" in md


def test_report_agent_brief():
    brief = ReportAgent().generate_brief(
        disaster_type="Flood",
        location="Pune",
        severity="Critical",
        recommendations=["Deploy 5 rescue boats"],
        evidence="SOP clause 1.8.",
    )
    assert "Pune" in brief["summary"]
    assert "#" in brief["markdown"]
    assert "<html>" in brief["html"].lower()


def test_generate_report_endpoint(api_orchestrator):
    from ai.api.chat import ReportRequest, generate_report_endpoint

    req = ReportRequest(
        disaster_type="Flood",
        location="Pune District",
        severity="Critical",
        recommendations=["Deploy 5 rescue boats to Highway 48"],
        evidence="SOP 1.8 threshold.",
        format="markdown",
    )
    res = run(generate_report_endpoint(req))
    assert "report_content" in res
    assert res["filename"].endswith(".md")
    assert "Pune_District" in res["filename"]
    assert "Deploy 5 rescue boats" in res["report_content"]


def test_generate_report_endpoint_html_format(api_orchestrator):
    from ai.api.chat import ReportRequest, generate_report_endpoint

    req = ReportRequest(
        disaster_type="Wildfire",
        location="Satara",
        severity="High",
        recommendations=["Block mountain pass"],
        evidence="Wildfire_SOP.txt page 1.",
        format="html",
    )
    res = run(generate_report_endpoint(req))
    assert res["filename"].endswith(".html")
    assert "<html>" in res["report_content"]


# ---------------------------------------------------------------------------
# #10 Reports: incident -> evidence -> reasoning -> recommendations -> report
# must chain verbatim with no contradictions between stages.
# ---------------------------------------------------------------------------

MOCK_INCIDENT = {
    "location": "Pune",
    "disaster": "Flood",
    "river_level": 1.9,
    "critical_level": 1.8,
    "population_at_risk": 22400,
}


def _incident_chain(orch, incident):
    """Run the pipeline and compile a report strictly from its outputs."""
    result = orch.process_query("Flood evacuation decision for Pune", incident=incident)
    payload = result["structured_reasoning"]
    evidence = "\n".join(
        f"[{ev['source']} - page {ev['page']}] {ev['paragraph']}"
        for ev in payload["evidence"]
    )
    md = ReportCompiler.compile_report(
        {
            "disaster_type": incident["disaster"],
            "location": incident["location"],
            "severity": payload["severity"],
            "recommendations": [r["action"] for r in payload["recommendations"]],
            "evidence": evidence,
        },
        format_type="markdown",
    )
    return result, payload, md


def test_critical_incident_report_contains_reasoning_without_contradiction(renewed):
    result, payload, md = _incident_chain(renewed, MOCK_INCIDENT)

    # Stage consistency: the report says exactly what the reasoning decided.
    assert payload["decision"].startswith("CRITICAL:")
    assert payload["severity"] == "Critical"
    assert f"**Severity Rating**: {payload['severity']}" in md
    assert f"**Location**: {MOCK_INCIDENT['location']}" in md
    assert f"**Event Type**: {MOCK_INCIDENT['disaster']}" in md

    # Every recommendation flows verbatim into the task list -- none dropped,
    # reworded, or invented along the way.
    actions = [r["action"] for r in payload["recommendations"]]
    assert actions
    for action in actions:
        assert f"- [ ] **Task**: {action}" in md
    task_lines = [line for line in md.splitlines() if line.startswith("- [ ] **Task**:")]
    assert len(task_lines) == len(actions), "report invented or dropped a task"
    assert any("evacuat" in t.lower() for t in task_lines), "CRITICAL decision must yield an evacuation task"

    # Evidence stage flows through: every cited source appears in the report.
    sources = {ev["source"] for ev in payload["evidence"]}
    assert sources
    for src in sources:
        assert src in md


def test_monitor_incident_report_matches_non_critical_decision(renewed):
    incident = {**MOCK_INCIDENT, "river_level": 1.4}
    result, payload, md = _incident_chain(renewed, incident)

    # Below the 1.8m threshold the decision is MONITOR, and the report must
    # not contradict it with an evacuation task or a Critical rating.
    assert payload["decision"].startswith("MONITOR:")
    assert f"**Severity Rating**: {payload['severity']}" in md
    actions = [r["action"] for r in payload["recommendations"]]
    assert actions
    for action in actions:
        assert f"- [ ] **Task**: {action}" in md
        assert "evacuat" not in action.lower(), "MONITOR decision leaked an evacuation task"
    assert "**Severity Rating**: Critical" not in md


def test_report_evidence_block_is_exactly_the_reasoning_evidence(renewed):
    result, payload, md = _incident_chain(renewed, MOCK_INCIDENT)

    for ev in payload["evidence"]:
        assert ev["paragraph"] in md
        assert ev["source"] in md
    # The reasoning evidence comes from real retrieved docs, not placeholders.
    citations = result["explainability"]["evidence"]["citations"]
    assert citations
    assert {ev["source"] for ev in payload["evidence"]} <= {c["document"] for c in citations}


def test_report_agent_brief_matches_compiler_output(renewed):
    """The ReportAgent and the raw compiler must agree on the content contract
    (recommendations, evidence, severity) regardless of the status string they
    default differently."""
    result, payload, _ = _incident_chain(renewed, MOCK_INCIDENT)
    actions = [r["action"] for r in payload["recommendations"]]
    evidence = "\n".join(
        f"[{ev['source']} - page {ev['page']}] {ev['paragraph']}"
        for ev in payload["evidence"]
    )
    brief = ReportAgent().generate_brief(
        disaster_type=MOCK_INCIDENT["disaster"],
        location=MOCK_INCIDENT["location"],
        severity=payload["severity"],
        recommendations=actions,
        evidence=evidence,
    )
    direct = ReportCompiler.compile_report(
        {
            "disaster_type": MOCK_INCIDENT["disaster"],
            "location": MOCK_INCIDENT["location"],
            "severity": payload["severity"],
            "recommendations": actions,
            "evidence": evidence,
        },
        format_type="markdown",
    )
    brief_tasks = [l for l in brief["markdown"].splitlines() if l.startswith("- [ ] **Task**:")]
    direct_tasks = [l for l in direct.splitlines() if l.startswith("- [ ] **Task**:")]
    assert brief_tasks == direct_tasks
    assert f"**Severity Rating**: {payload['severity']}" in brief["markdown"]
    assert evidence.splitlines()[0] in brief["markdown"]
    assert f"{len(actions)} tasks compiled" in brief["summary"]