from typing import Dict, Any, List
from ai.report_service.generator import ReportCompiler

class ReportAgent:
    """
    Specialized agent representing the Reporting Officer.
    Formats incident files and generates disaster summaries.
    """
    def __init__(self):
        self.agent_name = "Reporting Agent"
        
    def generate_brief(self, 
                       disaster_type: str, 
                       location: str, 
                       severity: str, 
                       recommendations: List[str], 
                       evidence: str) -> Dict[str, Any]:
        """
        Creates a structured summary briefing and generates markdown.
        """
        data = {
            "disaster_type": disaster_type,
            "location": location,
            "severity": severity,
            "status": "Active Response",
            "recommendations": recommendations,
            "evidence": evidence
        }
        
        md_report = ReportCompiler.compile_report(data, format_type="markdown")
        html_report = ReportCompiler.compile_report(data, format_type="html")
        
        return {
            "markdown": md_report,
            "html": html_report,
            "summary": f"{disaster_type} response briefing generated for {location}. Severity: {severity}. {len(recommendations)} tasks compiled."
        }
