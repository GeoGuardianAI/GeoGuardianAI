import re
from typing import Dict, Any

class SafetyGuardrails:
    # Patterns for prompt injection detection
    PROMPT_INJECTION_PATTERNS = [
        r"(?i)ignore\s+(?:previous|prior)\s+instructions",
        r"(?i)system\s+prompt",
        r"(?i)override\s+instructions",
        r"(?i)delete\s+(?:database|db|records|table)",
        r"(?i)drop\s+(?:database|table)",
        r"(?i)forget\s+everything",
        r"(?i)you\s+are\s+now\s+a",
        r"(?i)bypass\s+safety"
    ]
    
    # Patterns for PII / Sensitive Data detection (e.g. credit card, SSN)
    PII_PATTERNS = {
        "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    }

    @classmethod
    def check_query(cls, query: str) -> Dict[str, Any]:
        """
        Runs safety checks on the query. Returns a dict showing status.
        """
        # 1. Check for prompt injection
        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, query):
                return {
                    "passed": False,
                    "reason": "Prompt Injection Detected",
                    "details": f"Query triggered security pattern match for instruction override."
                }
                
        # 2. Check for PII / Sensitive Data
        detected_pii = []
        for name, pattern in cls.PII_PATTERNS.items():
            matches = re.findall(pattern, query)
            if matches:
                detected_pii.append(name)
                
        if detected_pii:
            return {
                "passed": False,
                "reason": "PII / Sensitive Data Detected",
                "details": f"Query contains potential PII elements: {', '.join(detected_pii)}."
            }
            
        return {
            "passed": True,
            "reason": "Safe",
            "details": "Query passed all security checks."
        }
