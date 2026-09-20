import time
from typing import List, Dict, Any

class ConversationMemoryManager:
    def __init__(self):
        # session_id -> list of message dicts: {role, content, timestamp}
        self.sessions = {}
        
    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
            
        self.sessions[session_id].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        
        # Bounded history to prevent context window explosion (keep last 12 messages)
        if len(self.sessions[session_id]) > 12:
            self.sessions[session_id] = self.sessions[session_id][-12:]
            
    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        if session_id not in self.sessions:
            return []
        # Return only role and content
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.sessions[session_id]
        ]
        
    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id] = []
