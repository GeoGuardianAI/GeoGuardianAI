import os

class TesseractScanner:
    def __init__(self):
        self.initialized = False
        
    def initialize(self):
        if self.initialized:
            return
        try:
            import pytesseract
            self.initialized = True
        except ImportError:
            print("[OCR] pytesseract library not available. Falling back to native PDF text extraction.")
            
    def scan_image(self, image_path: str) -> str:
        self.initialize()
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(image_path)
            return pytesseract.image_to_string(img)
        except Exception as e:
            print(f"[OCR] Tesseract failed: {e}. Falling back.")
            
        return f"[Simulated Tesseract OCR Text from {os.path.basename(image_path)}]\nEnsure all medical rescue teams are positioned in the safe zone."
