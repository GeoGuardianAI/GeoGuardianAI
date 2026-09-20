import re

class TextCleaner:
    @staticmethod
    def clean(text: str) -> str:
        if not text:
            return ""
        
        # Remove repeated page headers/footers (common in SOPs like "Page X of Y", "GeoGuardian Confidential")
        text = re.sub(r'(?i)page\s+\d+(\s+of\s+\d+)?', '', text)
        text = re.sub(r'(?i)standard\s+operating\s+procedure', '', text)
        text = re.sub(r'(?i)disaster\s+management\s+guidelines', '', text)
        
        # Remove lines that are just numbers or page markers
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line_stripped = line.strip()
            # If line is just numbers or very short page labels, ignore
            if re.match(r'^\d+$', line_stripped) or re.match(r'^[-*_]+$', line_stripped):
                continue
            cleaned_lines.append(line)
            
        text = '\n'.join(cleaned_lines)
        
        # Remove non-ASCII characters (or clean them to printable ASCII)
        text = text.encode('ascii', errors='ignore').decode('ascii')
        
        # Remove random dots/ellipses used in tables of contents
        text = re.sub(r'\.{3,}', ' ', text)
        
        # Replace multiple spaces with a single space
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Replace multiple newlines with a double newline to preserve paragraph structure
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
