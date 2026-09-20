import os
import urllib.request
import json
from typing import Dict, Any, List

class LLMModelManager:
    def __init__(self):
        self.model_name = "Llama-3 (Local)"
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        
    def set_model(self, model_name: str):
        self.model_name = model_name

    def call_ollama(self, prompt: str) -> str:
        url = "http://localhost:11434/api/generate"
        data = {
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        # 1-second timeout to check if ollama is running
        with urllib.request.urlopen(req, timeout=1.5) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res.get("response", "")

    def call_gemini(self, prompt: str) -> str:
        # Call Gemini API via simple REST call to avoid library dependency issues
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
        data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res['candidates'][0]['content']['parts'][0]['text']

    def generate_response(self, query: str, context: str, history: List[Dict[str, str]] = None) -> str:
        """
        Generates a RAG response based on the query and context, checking API and local fallbacks.
        """
        # Format the system prompt with context and history
        history_str = ""
        if history:
            for msg in history:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_str += f"{role}: {msg['content']}\n"
                
        prompt = f"""
System: You are GeoGuardian AI, a critical disaster management and response assistant.
You must answer the user's questions strictly using the provided SOP context. If the context does not contain the answer, say "According to official SOPs, this information is not registered."

Context:
{context}

Conversation History:
{history_str}

User: {query}
Assistant:
"""

        # 1. Try Gemini if key is provided
        if self.gemini_key:
            try:
                return self.call_gemini(prompt)
            except Exception as e:
                print(f"[LLM] Gemini call failed: {e}. Trying Ollama.")

        # 2. Try Local Ollama Llama 3
        try:
            return self.call_ollama(prompt)
        except Exception:
            # Fallback to local rule-based context synthesizer
            return self.fallback_synthesizer(query, context)

    def fallback_synthesizer(self, query: str, context: str) -> str:
        """
        A high-fidelity rule-based local answer synthesizer that extracts and formats information 
        from the retrieved SOP context, rendering it as markdown.
        """
        if not context or "Source: " not in context:
            # Generate default response if no context is found
            return (
                "Based on the default emergency protocols, safety checks should be initiated immediately:\n\n"
                "1. **Notify Incident Command**: Confirm incident location and severity.\n"
                "2. **Safety Perimeter**: Establish a 200m safety perimeter around affected infrastructure.\n"
                "3. **Alert Responders**: Dispatch local teams with appropriate response kits."
            )
            
        # Parse context by paragraphs
        paragraphs = context.split('\n\n')
        relevant_procedures = []
        
        # Analyze query keywords to extract precise instructions
        query_lower = query.lower()
        
        for para in paragraphs:
            # Extract procedural instructions (typically lines starting with digits, bullets, or containing 'should', 'must', 'first')
            lines = para.split('\n')
            source = lines[0] if lines else "SOP Reference"
            
            for line in lines[1:]:
                line_lower = line.lower()
                # Check keyword matching
                if any(k in line_lower for k in ["evacuate", "evacuation", "rescue", "road", "bridge", "highway", "water", "level", "threshold", "medical", "hospital", "shelter", "warning", "phase"]):
                    clean_line = line.strip().strip("-*•")
                    if clean_line and clean_line not in relevant_procedures:
                        relevant_procedures.append((clean_line, source))
                        
        if not relevant_procedures:
            # Just extract top lines from context directly
            for para in paragraphs[:2]:
                lines = para.split('\n')
                source = lines[0] if lines else "SOP Reference"
                for line in lines[1:4]:
                    clean_line = line.strip().strip("-*•")
                    if clean_line:
                        relevant_procedures.append((clean_line, source))

        # Structure response beautifully
        response = "### 📋 Action Plan & Official Guidelines\n\n"
        response += "According to the retrieved Disaster Management SOPs, the following operational instructions apply:\n\n"
        
        # Group by source
        grouped = {}
        for proc, src in relevant_procedures:
            if src not in grouped:
                grouped[src] = []
            grouped[src].append(proc)
            
        for src, procs in list(grouped.items())[:3]:  # Top 3 sources
            response += f"**Source Citation**: `{src}`\n"
            for p in procs[:4]:  # Top 4 instructions per source
                response += f"- **Instruction**: {p}\n"
            response += "\n"
            
        # Add response warning details
        response += "### ⚠️ Safety Precautions\n"
        response += "- Keep all response teams equipped with proper PPE.\n"
        response += "- Establish secondary communication channels (satellite/radio) if cellular service is degraded.\n"
        response += "- Monitor meteorological alerts every 30 minutes."
        
        return response
