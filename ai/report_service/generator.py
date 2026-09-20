import os
from typing import Dict, Any

class ReportCompiler:
    @staticmethod
    def compile_report(data: Dict[str, Any], format_type: str = "markdown") -> str:
        """
        Compiles disaster data into structured Markdown or HTML briefing reports.
        """
        disaster_type = data.get("disaster_type", "Flood")
        location = data.get("location", "District A")
        severity = data.get("severity", "High")
        status = data.get("status", "Active")
        recommendations = data.get("recommendations", [])
        evidence = data.get("evidence", "Monitor water levels.")
        
        # Build list items
        rec_list = ""
        for rec in recommendations:
            rec_list += f"- [ ] **Task**: {rec}\n"
            
        if not rec_list:
            rec_list = "- [ ] **Task**: Dispatch local search and rescue teams.\n- [ ] **Task**: Secure major route bridges."

        markdown_content = f"""# 🚨 GEOGUARDIAN AI - SITUATION BRIEFING REPORT
**Incident Management Center** | Generated: 2026-07-29

---

## 📈 Incident Overview
- **Event Type**: {disaster_type}
- **Location**: {location}
- **Severity Rating**: {severity}
- **Current Status**: {status}

---

## 📋 Recommended Action Plan (Derived from SOP)
{rec_list}

---

## 🔍 Grounding & SOP Citations
*Source documents referenced during assessment:*
> {evidence}

---

## ⚠️ Tactical Safety Warnings
1. Clear all civilian vehicles within a 5km radius.
2. Confirm secondary satellite links are functional.
3. Responders must remain equipped with flood safety gear.

**Report End**
"""

        if format_type.lower() == "html":
            # Convert Markdown to a clean styled HTML template
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #0d1117; color: #c9d1d9; padding: 25px; }}
                    h1 {{ color: #ff7b72; border-bottom: 2px solid #30363d; padding-bottom: 10px; }}
                    h2 {{ color: #58a6ff; }}
                    ul {{ list-style-type: square; }}
                    .box {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 15px; margin: 15px 0; }}
                    .warning {{ border-left: 4px solid #f0883e; background: #261d15; padding: 10px; }}
                </style>
            </head>
            <body>
                <h1>🚨 GeoGuardian AI - Incident Briefing Report</h1>
                <div class="box">
                    <h2>Incident Overview</h2>
                    <p><strong>Event Type:</strong> {disaster_type}</p>
                    <p><strong>Location:</strong> {location}</p>
                    <p><strong>Severity:</strong> {severity}</p>
                    <p><strong>Status:</strong> {status}</p>
                </div>
                <h2>Recommended Action Plan</h2>
                <ul>
                    {"".join([f"<li>{rec}</li>" for rec in recommendations]) if recommendations else "<li>Dispatch search and rescue boats.</li><li>Set up safety barricades.</li>"}
                </ul>
                <div class="box warning">
                    <h2>SOP Grounding Citations</h2>
                    <p>{evidence}</p>
                </div>
            </body>
            </html>
            """
            return html_content
            
        return markdown_content
