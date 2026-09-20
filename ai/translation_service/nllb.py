class NLLBTranslator:
    def __init__(self):
        # A dictionary of core disaster response terms translated for high fidelity
        self.dictionary = {
            "hi": {  # Hindi
                "according to the retrieved disaster management sops": "प्राप्त आपदा प्रबंधन मानक संचालन प्रक्रिया (SOP) के अनुसार",
                "action plan & official guidelines": "कार्य योजना और आधिकारिक दिशा-निर्देश",
                "evacuate immediately": "तुरंत खाली करें",
                "notify incident command": "घटना कमांड को सूचित करें",
                "safety perimeter": "सुरक्षा परिधि",
                "alert responders": "प्रतिक्रिया दल को सतर्क करें",
                "hospitals": "अस्पताल",
                "roads": "सड़कें",
                "bridges": "पुल",
                "shelters": "आश्रय स्थल",
                "status": "स्थिति",
                "capacity": "क्षमता",
                "active": "सक्रिय",
                "at risk": "जोखिम में",
                "blocked": "अवरुद्ध",
                "severe": "गंभीर",
                "warning": "चेतावनी",
                "danger": "खतरा",
                "evacuation rules": "निकासी नियम",
                "rescue guidelines": "बचाव दिशा-निर्देश",
                "safety precautions": "सुरक्षा सावधानियां",
                "monitor meteorological alerts": "मौसम संबंधी अलर्ट की निगरानी करें",
                "keep all response teams equipped with proper ppe": "सभी प्रतिक्रिया टीमों को उचित पीपीई से लैस रखें",
                "establish secondary communication channels": "द्वितीयक संचार चैनल स्थापित करें",
                "water warning thresholds": "पानी की चेतावनी सीमा"
            },
            "mr": {  # Marathi
                "according to the retrieved disaster management sops": "मिळालेल्या आपत्ती व्यवस्थापन SOP नुसार",
                "action plan & official guidelines": "कृती योजना आणि अधिकृत मार्गदर्शक तत्त्वे",
                "evacuate immediately": "त्वरित बाहेर पडा",
                "notify incident command": "इन्सिडेंट कमांडला सूचित करा",
                "safety perimeter": "सुरक्षा सीमा",
                "alert responders": "बचाव पथकांना सतर्क करा",
                "hospitals": "रुग्णालय",
                "roads": "रस्ते",
                "bridges": "पूल",
                "shelters": "निवारा केंद्रे",
                "status": "स्थिती",
                "capacity": "क्षमता",
                "active": "सक्रिय",
                "at risk": "धोक्यात",
                "blocked": "बंद",
                "severe": "गंभीर",
                "warning": "इशारा",
                "danger": "धोका",
                "evacuation rules": "स्थलांतर नियम",
                "rescue guidelines": "बचाव मार्गदर्शक तत्त्वे",
                "safety precautions": "सुरक्षा खबरदारी",
                "monitor meteorological alerts": "हवामान इशाऱ्यांवर लक्ष ठेवा",
                "keep all response teams equipped with proper ppe": "सर्व बचाव पथकांना योग्य पीपीई किट द्या",
                "establish secondary communication channels": "दुय्यम संपर्क यंत्रणा सुरू करा"
            },
            "es": {  # Spanish
                "according to the retrieved disaster management sops": "De acuerdo con los SOP de gestión de desastres recuperados",
                "action plan & official guidelines": "Plan de acción y directrices oficiales",
                "evacuate immediately": "Evacuar inmediatamente",
                "notify incident command": "Notificar al comando de incidentes",
                "safety perimeter": "Perímetro de seguridad",
                "alert responders": "Alertar a los equipos de rescate",
                "hospitals": "Hospitales",
                "roads": "Carreteras",
                "bridges": "Puentes",
                "shelters": "Refugios",
                "status": "Estado",
                "capacity": "Capacidad",
                "active": "Activo",
                "at risk": "En riesgo",
                "blocked": "Bloqueado",
                "severe": "Severo",
                "warning": "Advertencia",
                "danger": "Peligro",
                "evacuation rules": "Reglas de evacuación",
                "rescue guidelines": "Pautas de rescate",
                "safety precautions": "Precauciones de seguridad"
            }
        }

    def translate(self, text: str, target_lang: str) -> str:
        """
        Translates text into target language (hi, mr, es).
        """
        target = target_lang.lower()
        if target == "en" or target not in self.dictionary:
            return text
            
        translated_text = text
        lang_dict = self.dictionary[target]
        
        # Replace matches case-insensitively
        for eng_phrase, trans_phrase in lang_dict.items():
            # Find and replace
            # We use regex to replace case-insensitively
            pattern = r'(?i)' + re.escape(eng_phrase)
            translated_text = re.sub(pattern, trans_phrase, translated_text)
            
        # If it's a fallback translation, add a footer indicating dictionary translation
        if target == "hi" and translated_text == text:
            return f"[अनुवादित] {text} (अनुवाद उपलब्ध नहीं है)"
        elif target == "mr" and translated_text == text:
            return f"[भाषांतरित] {text} (भाषांतर उपलब्ध नाही)"
        elif target == "es" and translated_text == text:
            return f"[Traducido] {text} (Traducción no disponible)"
            
        return translated_text
        
# Import re inside translation module to avoid scoping issues
import re
