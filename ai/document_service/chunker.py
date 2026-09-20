from typing import List, Dict, Any

class DocumentChunker:
    @staticmethod
    def chunk(text: str, chunk_size: int = 800, overlap: int = 100) -> List[Dict[str, Any]]:
        if not text:
            return []
            
        chunks = []
        start = 0
        text_len = len(text)
        chunk_index = 0
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            
            # If we are not at the end of the text, back up to the nearest whitespace to avoid splitting words
            if end < text_len:
                while end > start and text[end] not in (' ', '\n', '\t'):
                    end -= 1
                if end == start:  # If no whitespace found, just force chunk size
                    end = min(start + chunk_size, text_len)
            
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) > 50:  # Only index substantial chunks
                chunks.append({
                    "chunk_id": chunk_index,
                    "text": chunk_text,
                    "char_start": start,
                    "char_end": end
                })
                chunk_index += 1
                
            start = end - overlap
            if start < 0:
                start = 0
            if end == text_len:
                break
                
        return chunks
