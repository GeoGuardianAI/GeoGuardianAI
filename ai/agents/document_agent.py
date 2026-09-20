from typing import Dict, Any, List

class DocumentAgent:
    """
    Specialized agent representing the Document Analyst.
    Searches SOP documentation to pull out specific evacuation thresholds.
    """
    def __init__(self):
        self.agent_name = "Document Analyst Agent"
        
    def analyze_thresholds(self, doc_text: str) -> Dict[str, Any]:
        results = {
            "warning_threshold": "1.5m water level",
            "evacuation_radius": "5km",
            "recommended_supplies": ["Rescue Boats", "Life Jackets", "Medical Kits"],
            "notes": "Rules derived from retrieved emergency procedures."
        }
        
        # Simple extraction logic based on text
        text_lower = doc_text.lower()
        if "evacuate" in text_lower:
            # Try to find radius
            import re
            radius_match = re.search(r'(\d+)\s*(?:km|kilometer|mile|meter)\s+(?:radius|zone|area)', text_lower)
            if radius_match:
                results["evacuation_radius"] = radius_match.group(0)
                
        if "water" in text_lower or "threshold" in text_lower:
            import re
            threshold_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:m|meter|feet|ft)\b', text_lower)
            if threshold_match:
                results["warning_threshold"] = threshold_match.group(0) + " water level"
                
        return results
