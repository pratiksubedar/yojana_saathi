"""
Yojana Saathi - Multilingual Intent Router
Milestone 6.3: Routes citizen messages into structured intents across English,
Hindi, Kannada, and Telugu, and identifies mentioned scheme targets accurately.
"""

import re
from typing import List, Optional, Tuple
from app.schemas.orchestration import CitizenIntentEnum, IntentClassificationResult

# Scheme keyword detection dictionary
SCHEME_PATTERNS = {
    "pm-kisan": [
        "pm-kisan", "pmkisan", "pm kisan", "kisan samman", "samman nidhi",
        "किसान सम्मान", "पीएम किसान", "ಕಿಸಾನ್ ಸಮ್ಮಾನ್", "ಪಿಎಂ ಕಿಸಾನ್", "కిసాన్ సమ్మాన్", "పీఎం కిసాన్"
    ],
    "pm-jay": [
        "pm-jay", "pmjay", "pm jay", "ayushman", "ayushman bharat", "golden card", "health cover",
        "आयुष्मान", "आयुष्मान भारत", "ಆಯುಷ್ಮಾನ್", "ಆಯುಷ್ಮಾನ್ ಭಾರತ್", "ఆయుష్మాన్", "ఆయుష్మాన్ భారత్"
    ],
    "pm-svanidhi": [
        "pm-svanidhi", "svanidhi", "pmsvanidhi", "street vendor", "vendor loan",
        "स्वनिधि", "स्ट्रीट वेंडर", "ಸ್ವನಿಧಿ", "ಬೀದಿ ವ್ಯಾಪಾರಿ", "స్వనిధి", "వీధి వ్యాపారి"
    ],
    "pmay-g": [
        "pmay-g", "pmayg", "pmay", "awaas", "gramin housing", "indira awaas", "rural housing",
        "आवास", "पीएमएवाई", "ಆವಾಸ್", "ಗ್ರಾಮೀಣ ವಸತಿ", "ఆవాస్", "గ్రామీణ గృహ"
    ],
    "pm-kmy": [
        "pm-kmy", "pmkmy", "kisan maandhan", "maandhan", "kisan pension",
        "मानधन", "किसान पेंशन", "ಮಾನ್‌ಧನ್", "ರೈತ ಪಿಂಚಣಿ", "మాన్‌ధన్", "రైతు పెన్షన్"
    ],
    "pmmvy": [
        "pmmvy", "matru vandana", "maternity benefit", "pregnancy grant", "lactating",
        "मातृ वंदना", "ಗರ್ಭಿಣಿ ಯೋಜನೆ", "ಮಾತೃ ವಂದನ", "గర్భిణీ పథకం", "మాతృ వందన"
    ],
    "pm-kusum": [
        "pm-kusum", "pmkusum", "kusum", "solar pump", "solar agriculture",
        "कुसुम", "सोलर पंप", "ಕುಸುಮ್", "ಸೌರ ಪಂಪ್", "కుసుమ్", "సోలార్ పంప్"
    ],
    "pm-mudra": [
        "mudra", "pmmy", "pm-mudra", "shishu", "kishore", "tarun", "mudra loan",
        "मुद्रा", "मुद्रा लोन", "ಮುದ್ರಾ", "ಮುದ್ರಾ ಸಾಲ", "ముద్రా", "ముద్రా రుణం"
    ],
    "nsap-ignoaps": [
        "ignoaps", "nsap", "old age pension", "widow pension", "senior citizen pension",
        "वृद्धावस्था पेंशन", "ವೃದ್ಧಾಪ್ಯ ವೇತನ", "వృద్ధాప్య పెన్షన్"
    ],
    "apy": [
        "atal pension", "apy", "अटल पेंशन", "ಅಟಲ್ ಪಿಂಚಣಿ", "అటల్ పెన్షన్"
    ],
    "pm-sym": [
        "pm-sym", "pmsym", "shram yogi", "श्रम योगी", "ಶ್ರಮ್ ಯೋಗಿ", "శ్రమ్ యోగి"
    ],
    "pm-vishwakarma": [
        "vishwakarma", "pm-vishwakarma", "artisan", "carpenter", "blacksmith", "potter",
        "विश्वकर्मा", "ವಿಶ್ವಕರ್ಮ", "విశ్వకర్మ"
    ],
    "stand-up-india": [
        "stand up india", "stand-up india", "standup india", "स्टैंड अप इंडिया", "ಸ್ಟ್ಯಾಂಡ್ ಅಪ್ ಇಂಡಿಯಾ"
    ],
    "day-nrlm": [
        "nrlm", "day-nrlm", "aajeevika", "self help group", "shg", "lakhpati didi",
        "आजीविका", "स्वयं सहायता समूह", "ಸ್ವಸಹಾಯ ಗುಂಪು", "స్వయం సహాయక సంఘం"
    ],
    "pm-surya-ghar": [
        "surya ghar", "pm-surya-ghar", "muft bijli", "rooftop solar", "300 units",
        "सूर्य घर", "मुफ्त बिजली", "ಸೂರ್ಯ ಘರ್", "సూర్య ఘర్"
    ],
    "pmuy": [
        "ujjwala", "pmuy", "free gas", "lpg connection",
        "उज्ज्वला", "ಉಜ್ವಲ", "ఉజ్వల"
    ],
    "ssy": [
        "sukanya", "samriddhi", "ssy", "girl child", "सुकन्या समृद्धि", "ಸುಕನ್ಯಾ ಸಮೃದ್ಧಿ", "సుకన్య సమృద్ధి"
    ],
    "kcc": [
        "kcc", "kisan credit card", "किसान क्रेडिट कार्ड", "ಕಿಸಾನ್ ಕ್ರೆಡಿಟ್ ಕಾರ್ಡ್", "కిసాన్ క్రెడిట్ కార్డ్"
    ],
    "pmjjby": [
        "pmjjby", "jeevan jyoti", "life insurance", "जीवन ज्योति", "ಜೀವನ್ ಜ್ಯೋತಿ", "జీవన్ జ్యోతి"
    ],
    "pmsby": [
        "pmsby", "suraksha bima", "accident insurance", "सुरक्षा बीमा", "ಸುರಕ್ಷಾ ಭೀಮಾ", "సురక్షా బీమా"
    ],
}

# Intent keyword patterns
INTENT_PATTERNS = {
    CitizenIntentEnum.ELIGIBILITY_CHECK: [
        "eligible", "eligibility", "qualify", "am i eligible", "can i get", "who can",
        "years old", "year old", "hectare", "acres", "bpl", "income tax", "farmer with",
        "पात्र", "पात्रता", "क्या मुझे मिल", "क्या मैं पात्र",
        "ಅರ್ಹ", "ಅರ್ಹತೆ", "ನನಗೆ ಸಿಗುತ್ತದೆಯೇ", "ನಾನು ಅರ್ಹನೇ",
        "అర్హ", "అర్హు", "అర్హత", "అర్హులు", "నాకు వస్తుందా", "నేను అర్హుడినా"
    ],
    CitizenIntentEnum.DOCUMENT_REQUIREMENTS: [
        "document", "documents", "documents required", "papers", "id proof", "certificate", "ration card",
        "दस्तावेज", "दस्तावेज़", "कागजात", "प्रमाण पत्र",
        "ದಾಖಲೆ", "ದಾಖಲೆಗಳು", "ಪ್ರಮಾಣಪತ್ರ", "ರೇಷನ್ ಕಾರ್ಡ್",
        "పత్రాలు", "ధ్రువీకరణ", "రేషన్ కార్డు", "సర్టిఫికేట్"
    ],
    CitizenIntentEnum.APPLICATION_GUIDANCE: [
        "apply", "how to apply", "application", "how to register", "registration", "portal", "process", "where to apply",
        "already applied", "check status", "application status", "track application",
        "आवेदन", "आवेदन कैसे करें", "पंजीकरण", "रजिस्ट्रेशन", "पोर्टल", "स्थिति जांच",
        "ಅರ್ಜಿ", "ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು ಹೇಗೆ", "ನೋಂದಣಿ", "ಪ್ರಕ್ರಿಯೆ", "ಸ್ಥಿತಿ ಪರಿಶೀಲನೆ",
        "దరఖాస్తు", "ఎలా దరఖాస్తు చేయాలి", "నమోదు", "విధానం", "స్థితి తనిఖీ"
    ],
    CitizenIntentEnum.SCHEME_INFORMATION: [
        "tell me about", "what is", "benefits of", "details of", "information on", "about",
        "के बारे में बताएं", "क्या है", "जानकारी", "लाभ क्या हैं",
        "ಬಗ್ಗೆ ತಿಳಿಸಿ", "ಎಂದರೇನು", "ವಿವರಗಳು", "ಪ್ರಯೋಜನಗಳೇನು",
        "గురించి చెప్పండి", "అంటే ఏమిటి", "వివరాలు", "ప్రయోజనాలు ఏమిటి"
    ],
    CitizenIntentEnum.SCHEME_DISCOVERY: [
        "all schemes", "list schemes", "which schemes", "schemes for", "find schemes", "available schemes",
        "what schemes", "what financial support", "any government loans", "government loans", "small business",
        "what can she apply", "what can i apply", "support can i receive", "schemes are available",
        "योजनाएं", "सभी योजनाएं", "कौन सी योजनाएं", "योजनाओं की सूची", "कौन सी सरकारी",
        "ಯೋಜನೆಗಳು", "ಎಲ್ಲಾ ಯೋಜನೆಗಳು", "ಯಾವ ಯೋಜನೆಗಳು", "ಪಟ್ಟಿ", "ಯಾವ ಸರ್ಕಾರಿ",
        "పథకాలు", "అన్ని పథకాలు", "ఏ పథకాలు", "జాబితా", "ఏ ప్రభుత్వ"
    ],
    CitizenIntentEnum.GENERAL_HELP: [
        "hello", "hi", "hey", "namaste", "help", "who are you", "what can you do", "thank you", "thanks",
        "नमस्ते", "प्रणाम", "मदद", "आप कौन हैं", "धन्यवाद",
        "ನಮಸ್ಕಾರ", "ಸಹಾಯ", "ನೀವು ಯಾರು", "ಧನ್ಯವಾದ",
        "నమస్కారం", "హలో", "సహాయం", "మీరు ఎవరు", "ధన్యవాదాలు"
    ],
}

# Truly unsupported / alien domain markers
UNSUPPORTED_PATTERNS = [
    "cricket", "ipl", "football", "match score", "movie", "song", "actor", "actress",
    "bitcoin", "crypto", "cryptocurrency", "stock market", "share market", "stocks", "trading",
    "weather forecast", "horoscope", "astrology", "recipe", "cook", "restaurant",
    "quantum computing", "alien spaceship", "mars mission rover", "spacex",
    "क्रिकेट", "फिल्म", "मौसम", "राशिफल", "ಪಂದ್ಯ", "ಸಿನಿಮಾ", "హోరోస్కోప్"
]


# Code-mixed and Romanized language detection dictionaries
HINGLISH_MARKERS = {
    "meri", "mera", "mere", "mujhe", "main", "mein", "hum", "aap", "aapka", "aapki",
    "hai", "hain", "hoon", "hun", "tha", "thi", "kheti", "aur",
    "umar", "umra", "umr", "aayu", "saal", "dastavej", "aavedan",
    "kaise", "kya", "kyu", "kyon", "kaun", "kitna", "kitni", "kitne", "paise", "rupaye",
    "sahi", "galat", "nahi", "nahin", "haan", "bilkul", "theek", "accha", "achha",
    "chahiye", "milega", "milta", "namaste", "pranam", "dhanyawad", "shukriya",
    "batao", "bataiye", "suno", "sunao", "sarkar", "sarkari", "paatra", "patrata",
    "bigha", "khet", "zameen", "zamin", "paas", "wala", "wali"
}

KANGLISH_MARKERS = {
    "nanna", "nanage", "naanu", "namma", "neevu", "nimma", "ninna", "beku", "beda",
    "yojane", "yojanegalu", "raitha", "rayitha", "krushi", "thumba", "tumba", "hege",
    "yavaga", "yellige", "enu", "yavudu", "yava", "haudu", "houdhu", "illa", "alla",
    "ide", "ideya", "ayitu", "aithu", "namaskara", "namaskar", "vayassu", "varsha",
    "dakhele", "dakhalegalu", "arji", "arjigalu", "sallisu", "siguthe", "sigutte",
    "sigalla", "kelasa", "madodu", "madabeku", "dhanyavadagalu", "bhoomi", "jameenu",
    "ekare", "huchu", "sahaya", "sarkara"
}

TENGLISH_MARKERS = {
    "naa", "naaku", "nenu", "memu", "meeru", "mee", "manam", "kavali", "vaddu", "vaddhu",
    "pathakam", "padhakam", "pathakalu", "yojana", "raithu", "rythu", "vyavasayam",
    "chala", "ela", "eppudu", "ekkada", "enti", "edhi", "evaru", "avunu", "kadu", "kadhukadhu",
    "ledu", "ledhu", "undhi", "undi", "namaskaram", "namaskar", "vayassu", "samvathsaram",
    "yellu", "patralu", "darakhasthu", "cheyali", "vastunda", "vasthundi", "radhu",
    "pani", "cheyadam", "dhanyavadamulu", "bhoomi", "ekaram", "sahayam", "prabhutvam"
}

LANGUAGE_SWITCH_PATTERNS = {
    "hi": [
        r"\b(?:switch\s+to|speak\s+in|talk\s+in|explain\s+in)\s+hindi\b",
        r"\bhindi\s+me\s+(?:baat\s+karo|batao|bataiye|samjhao)\b",
        r"\bhindi\s+mein\b", r"\bin\s+hindi\b",
        r"हिंदी\s+में", r"हिन्दी\s+में",
    ],
    "kn": [
        r"\b(?:switch\s+to|speak\s+in|talk\s+in|explain\s+in)\s+kannada\b",
        r"\bkannada\s+(?:dalli|nali)\s+(?:heli|mathadi|helu)\b",
        r"\bkannada\s+dalli\b", r"\bin\s+kannada\b",
        r"ಕನ್ನಡದಲ್ಲಿ\s+ಹೇಳಿ", r"ಕನ್ನಡದಲ್ಲಿ",
    ],
    "te": [
        r"\b(?:switch\s+to|speak\s+in|talk\s+in|explain\s+in)\s+telugu\b",
        r"\btelugu\s+lo\s+(?:cheppandi|matladandi|cheppu)\b",
        r"\btelugu\s+lo\b", r"\bin\s+telugu\b",
        r"తెలుగులో\s+చెప్పండి", r"తెలుగులో",
    ],
    "en": [
        r"\b(?:switch\s+to|speak\s+in|talk\s+in|explain\s+in)\s+english\b",
        r"\bin\s+english\b", r"\benglish\s+please\b",
        r"अंग्रेजी\s+में", r"ಇಂಗ್ಲಿಷ್\s+ನಲ್ಲಿ", r"ఇంగ్లీష్\s+లో",
    ],
}

SHORT_SLOT_PATTERN = re.compile(
    r"^(?:yes|no|yeah|yep|nope|true|false|correct|right|ok|okay|"
    r"\d+(?:\.\d+)?(?:\s*(?:years?|yrs?|acres?|hectares?|lakhs?|cr|k|rs\.?|inr|साल|ವರ್ಷ|సంవత్సరాలు))?|"
    r"farmer|street\s*vendor|laborer|labourer|worker|karnataka|andhra\s*pradesh|telangana|"
    r"haan|ha|nahi|nahin|sahi|bilkul|haudu|illa|avunu|ledu|kadu|"
    r"हाँ|हां|नहीं|हौदु|ಇಲ್ಲ|ಅವುನು|అవును|లేదు|కాదు)$",
    re.IGNORECASE
)


# Code-mixed and Romanized language detection dictionaries
HINGLISH_MARKERS = {
    "meri", "mera", "mere", "mujhe", "main", "mein", "hum", "aap", "aapka", "aapki",
    "hai", "hain", "hoon", "hun", "tha", "thi", "the", "kisan", "kisaan", "kheti",
    "umar", "umra", "umr", "aayu", "saal", "yojana", "yojna", "dastavej", "aavedan",
    "kaise", "kya", "kyu", "kyon", "kaun", "kitna", "kitni", "kitne", "paise", "rupaye",
    "sahi", "galat", "nahi", "nahin", "haan", "bilkul", "theek", "accha", "achha",
    "chahiye", "milega", "milta", "namaste", "pranam", "dhanyawad", "shukriya",
    "batao", "bataiye", "suno", "sunao", "sarkar", "sarkari", "paatra", "patrata",
    "bigha", "khet", "zameen", "zamin", "paas", "wala", "wali"
}

KANGLISH_MARKERS = {
    "nanna", "nanage", "naanu", "namma", "neevu", "nimma", "ninna", "beku", "beda",
    "yojane", "yojanegalu", "raitha", "rayitha", "krushi", "thumba", "tumba", "hege",
    "yavaga", "yellige", "enu", "yavudu", "yava", "haudu", "houdhu", "illa", "alla",
    "ide", "ideya", "ayitu", "aithu", "namaskara", "namaskar", "vayassu", "varsha",
    "dakhele", "dakhalegalu", "arji", "arjigalu", "sallisu", "siguthe", "sigutte",
    "sigalla", "kelasa", "madodu", "madabeku", "dhanyavadagalu", "bhoomi", "jameenu",
    "ekare", "huchu", "sahaya", "sarkara"
}

TENGLISH_MARKERS = {
    "naa", "naaku", "nenu", "memu", "meeru", "mee", "manam", "kavali", "vaddu", "vaddhu",
    "pathakam", "padhakam", "pathakalu", "yojana", "raithu", "rythu", "vyavasayam",
    "chala", "ela", "eppudu", "ekkada", "enti", "edhi", "evaru", "avunu", "kadu", "kadhukadhu",
    "ledu", "ledhu", "undhi", "undi", "namaskaram", "namaskar", "vayassu", "samvathsaram",
    "yellu", "patralu", "darakhasthu", "cheyali", "vastunda", "vasthundi", "radhu",
    "pani", "cheyadam", "dhanyavadamulu", "bhoomi", "ekaram", "sahayam", "prabhutvam"
}

LANGUAGE_SWITCH_PATTERNS = {
    "hi": [
        r"\b(?:switch\s+to|speak\s+in|talk\s+in|explain\s+in)\s+hindi\b",
        r"\bhindi\s+me\s+(?:baat\s+karo|batao|bataiye|samjhao)\b",
        r"\bhindi\s+mein\b", r"\bin\s+hindi\b",
        r"हिंदी\s+में", r"हिन्दी\s+में",
    ],
    "kn": [
        r"\b(?:switch\s+to|speak\s+in|talk\s+in|explain\s+in)\s+kannada\b",
        r"\bkannada\s+(?:dalli|nali)\s+(?:heli|mathadi|helu)\b",
        r"\bkannada\s+dalli\b", r"\bin\s+kannada\b",
        r"ಕನ್ನಡದಲ್ಲಿ\s+ಹೇಳಿ", r"ಕನ್ನಡದಲ್ಲಿ",
    ],
    "te": [
        r"\b(?:switch\s+to|speak\s+in|talk\s+in|explain\s+in)\s+telugu\b",
        r"\btelugu\s+lo\s+(?:cheppandi|matladandi|cheppu)\b",
        r"\btelugu\s+lo\b", r"\bin\s+telugu\b",
        r"తెలుగులో\s+చెప్పండి", r"తెలుగులో",
    ],
    "en": [
        r"\b(?:switch\s+to|speak\s+in|talk\s+in|explain\s+in)\s+english\b",
        r"\bin\s+english\b", r"\benglish\s+please\b",
        r"अंग्रेजी\s+में", r"ಇಂಗ್ಲಿಷ್\s+ನಲ್ಲಿ", r"ఇంగ్లీష్\s+లో",
    ],
}

SHORT_SLOT_PATTERN = re.compile(
    r"^(?:yes|no|yeah|yep|nope|true|false|correct|right|ok|okay|"
    r"\d+(?:\.\d+)?(?:\s*(?:years?|yrs?|acres?|hectares?|lakhs?|cr|k|rs\.?|inr|साल|ವರ್ಷ|సంవత్సరాలు))?|"
    r"farmer|street\s*vendor|laborer|labourer|worker|karnataka|andhra\s*pradesh|telangana|"
    r"haan|ha|nahi|nahin|sahi|bilkul|haudu|illa|avunu|ledu|kadu|"
    r"हाँ|हां|नहीं|हौदु|ಇಲ್ಲ|ಅವುನು|అవును|లేదు|కాదు)$",
    re.IGNORECASE
)


class IntentRouter:
    """
    Multilingual intent classification engine supporting English, Hindi, Kannada, and Telugu.
    Identifies citizen intent and target scheme without defaulting to eligibility.
    """

    @classmethod
    def detect_language(cls, text: str, current_language: Optional[str] = None) -> str:
        """
        Determines the primary language of the query across English, Hindi, Kannada, and Telugu.
        Supports native Indic scripts, explicit language switches, code-mixed Romanized sentences
        (Hinglish, Kanglish, Tenglish), and protects short slot answers from false language flips.
        """
        if not text:
            return current_language or "en"

        clean = text.strip()

        # 1. Native Indic Script Matching (Unambiguous 100% confidence)
        # Kannada Unicode block: \u0C80 - \u0CFF
        if re.search(r"[\u0C80-\u0CFF]", clean):
            return "kn"
        # Telugu Unicode block: \u0C00 - \u0C7F
        if re.search(r"[\u0C00-\u0C7F]", clean):
            return "te"
        # Devanagari Unicode block: \u0900 - \u097F
        if re.search(r"[\u0900-\u097F]", clean):
            return "hi"

        lower = clean.lower()

        # 2. Explicit Language Switch Requests (e.g. "talk in hindi", "ಕನ್ನಡದಲ್ಲಿ ಹೇಳಿ", "switch to english")
        for target_lang, patterns in LANGUAGE_SWITCH_PATTERNS.items():
            if any(re.search(pat, lower) for pat in patterns):
                return target_lang

        # 3. Short Slot Answers & Affirmations:
        # In multi-turn dialogue, answers like "45 years", "2 acres", "Farmer", "Yes", "No", "Karnataka"
        # should NOT cause the conversation to flip to English when the session is already in Hindi/Kannada/Telugu.
        lower_masked = re.sub(r"\b(?:pm[-\s]*)?kisan\b", "scheme_ref", lower)
        lower_masked = re.sub(r"\b(?:pm[-\s]*)?yojana\b", "scheme_ref", lower_masked)
        words = re.findall(r"\b\w+\b", lower_masked)
        word_set = set(words)

        if len(words) <= 3 and SHORT_SLOT_PATTERN.match(clean):
            if current_language in ["hi", "kn", "te"]:
                return current_language

        # 4. Code-Mixed Romanized Vocabulary Matching (Hinglish, Kanglish, Tenglish)
        hi_score = len(word_set.intersection(HINGLISH_MARKERS))
        kn_score = len(word_set.intersection(KANGLISH_MARKERS))
        te_score = len(word_set.intersection(TENGLISH_MARKERS))

        en_stop_words = {
            "i", "am", "my", "we", "our", "you", "your", "is", "are", "was", "were",
            "what", "how", "which", "who", "when", "where", "can", "tell", "eligible",
            "with", "from", "for", "the", "a", "an", "if", "have", "has", "had", "do",
            "does", "did", "please", "get", "about", "me", "to", "in", "of", "and", "or",
            "not", "all", "any", "no", "yes", "this", "that", "won", "price", "current",
            "exact", "office", "phone", "number", "grievance", "redressal", "subsidy",
            "available", "document", "documents", "required", "apply"
        }
        en_count = len(word_set.intersection(en_stop_words))

        # Check code-mixed Indic languages (e.g. Hinglish, Kanglish, Tenglish)
        if kn_score > 0 and kn_score >= hi_score and kn_score >= te_score:
            return "kn"
        if te_score > 0 and te_score >= hi_score and te_score >= kn_score:
            return "te"
        if hi_score > 0 and hi_score > en_count:
            return "hi"
        if hi_score >= 2:
            return "hi"

        # Dominant English sentence check
        if en_count >= 2 or (en_count > 0 and hi_score == 0 and kn_score == 0 and te_score == 0):
            return "en"

        if hi_score > 0:
            return "hi"

        # 6. Fallback to existing session language or English
        return current_language or "en"
        lower = clean.lower()

        # 2. Explicit Language Switch Requests (e.g. "talk in hindi", "ಕನ್ನಡದಲ್ಲಿ ಹೇಳಿ", "switch to english")
        for target_lang, patterns in LANGUAGE_SWITCH_PATTERNS.items():
            if any(re.search(pat, lower) for pat in patterns):
                return target_lang

        # 3. Short Slot Answers & Affirmations:
        # In multi-turn dialogue, answers like "45 years", "2 acres", "Farmer", "Yes", "No", "Karnataka"
        # should NOT cause the conversation to flip to English when the session is already in Hindi/Kannada/Telugu.
        words = re.findall(r"\b\w+\b", lower)
        if len(words) <= 3 and SHORT_SLOT_PATTERN.match(clean):
            if current_language in ["hi", "kn", "te"]:
                return current_language

        # 4. Code-Mixed Romanized Vocabulary Matching (Hinglish, Kanglish, Tenglish)
        word_set = set(words)
        hi_score = len(word_set.intersection(HINGLISH_MARKERS))
        kn_score = len(word_set.intersection(KANGLISH_MARKERS))
        te_score = len(word_set.intersection(TENGLISH_MARKERS))

        if hi_score > 0 or kn_score > 0 or te_score > 0:
            if hi_score > kn_score and hi_score > te_score:
                return "hi"
            if kn_score > hi_score and kn_score > te_score:
                return "kn"
            if te_score > hi_score and te_score > kn_score:
                return "te"
            # Tie breaker: prefer current language if part of the tie
            if current_language == "hi" and hi_score > 0:
                return "hi"
            if current_language == "kn" and kn_score > 0:
                return "kn"
            if current_language == "te" and te_score > 0:
                return "te"
            # Fall back to whichever scored highest
            if hi_score >= kn_score and hi_score >= te_score:
                return "hi"
            if kn_score >= te_score:
                return "kn"
            return "te"

        # 5. Full English Sentences (e.g. "I am a 45-year-old farmer from Karnataka")
        # If words contain English grammatical structure
        en_stop_words = {"i", "am", "my", "we", "our", "you", "your", "is", "are", "was", "were", "what", "how", "which", "can", "tell", "eligible", "with", "from", "for", "the", "a", "an"}
        en_count = len(word_set.intersection(en_stop_words))
        if en_count >= 2:
            return "en"

        # 6. Fallback to existing session language or English
        return current_language or "en"

    @classmethod
    def detect_scheme_ids(cls, text: str) -> List[str]:
        """
        Identifies all mentioned scheme IDs from keyword aliases across 4 languages.
        """
        lower = text.lower()
        found: List[str] = []
        for scheme_id, patterns in SCHEME_PATTERNS.items():
            if any(p in lower for p in patterns):
                if scheme_id not in found:
                    found.append(scheme_id)
        return found

    @classmethod
    def detect_scheme_id(cls, text: str) -> Optional[str]:
        """
        Identifies primary mentioned scheme ID from keyword aliases across 4 languages.
        """
        ids = cls.detect_scheme_ids(text)
        return ids[0] if ids else None

    @classmethod
    def classify_intent(
        cls,
        text: Optional[str] = None,
        preferred_language: Optional[str] = None,
        message: Optional[str] = None,
        current_language: Optional[str] = None,
    ) -> IntentClassificationResult:
        """
        Classifies citizen message into one of 7 standardized intents.
        """
        query_text = text if text is not None else (message or "")
        lang_pref = preferred_language or current_language

        lang = cls.detect_language(query_text, current_language=lang_pref)

        clean_text = query_text.strip()
        lower = clean_text.lower()

        if not clean_text:
            return IntentClassificationResult(
                intent=CitizenIntentEnum.GENERAL_HELP,
                confidence=1.0,
                detected_scheme_id=None,
                detected_language=lang,
                reasoning="Empty input defaulted to general help.",
            )

        detected_scheme = cls.detect_scheme_id(clean_text)

        # 1. UNSUPPORTED QUERY (word-boundary match AND must not contain welfare/scheme domain terms)
        has_welfare_context = bool(detected_scheme) or any(
            w in lower
            for w in [
                "scheme", "schemes", "welfare", "farmer", "land", "hectare", "acre",
                "pension", "loan", "eligible", "eligibility", "benefit", "benefits",
                "subsidy", "ration", "bpl", "योजना", "किसान", "ಯೋಜನೆ", "ರೈತ", "పథకం", "రైతు",
            ]
        )
        if not has_welfare_context and any(
            re.search(rf"\b{re.escape(un)}\b", lower) if un.isascii() else (un in lower)
            for un in UNSUPPORTED_PATTERNS
        ):
            return IntentClassificationResult(
                intent=CitizenIntentEnum.UNSUPPORTED_QUERY,
                confidence=0.95,
                detected_scheme_id=None,
                detected_language=lang,
                reasoning="Query matches out-of-scope non-welfare domain patterns.",
            )

        # 2. DOCUMENT REQUIREMENTS
        if any(w in lower for w in INTENT_PATTERNS[CitizenIntentEnum.DOCUMENT_REQUIREMENTS]):
            return IntentClassificationResult(
                intent=CitizenIntentEnum.DOCUMENT_REQUIREMENTS,
                confidence=0.9,
                detected_scheme_id=detected_scheme,
                detected_language=lang,
                reasoning="Citizen asked about required supporting documents or proofs.",
            )

        # 3. SCHEME DISCOVERY (when no specific scheme is named and query asks what schemes/support exist)
        is_discovery_phrase = (
            any(w in lower for w in INTENT_PATTERNS[CitizenIntentEnum.SCHEME_DISCOVERY])
            or (
                ("scheme" in lower or "schemes" in lower or "benefits" in lower)
                and any(kw in lower for kw in ["all", "list", "available", "find", "discover", "which", "show", "what", "any"])
            )
        )
        if not detected_scheme and is_discovery_phrase:
            return IntentClassificationResult(
                intent=CitizenIntentEnum.SCHEME_DISCOVERY,
                confidence=0.88,
                detected_scheme_id=None,
                detected_language=lang,
                reasoning="Open-ended inquiry into available welfare schemes or support.",
            )

        # 4. APPLICATION GUIDANCE
        if any(w in lower for w in INTENT_PATTERNS[CitizenIntentEnum.APPLICATION_GUIDANCE]):
            return IntentClassificationResult(
                intent=CitizenIntentEnum.APPLICATION_GUIDANCE,
                confidence=0.9,
                detected_scheme_id=detected_scheme,
                detected_language=lang,
                reasoning="Citizen asked about registration, portal, or filing steps.",
            )

        # 5. ELIGIBILITY CHECK
        # Matches if user explicitly asks about eligibility or states profile parameters
        if any(w in lower for w in INTENT_PATTERNS[CitizenIntentEnum.ELIGIBILITY_CHECK]):
            return IntentClassificationResult(
                intent=CitizenIntentEnum.ELIGIBILITY_CHECK,
                confidence=0.9,
                detected_scheme_id=detected_scheme,
                detected_language=lang,
                reasoning="Query asks for eligibility evaluation or provides citizen profile criteria.",
            )

        # 6. SCHEME INFORMATION (Specific scheme mentioned or information keywords)
        if detected_scheme or any(w in lower for w in INTENT_PATTERNS[CitizenIntentEnum.SCHEME_INFORMATION]):
            return IntentClassificationResult(
                intent=CitizenIntentEnum.SCHEME_INFORMATION,
                confidence=0.85,
                detected_scheme_id=detected_scheme,
                detected_language=lang,
                reasoning="Specific scheme mentioned or overview/benefit inquiry.",
            )

        # 7. Topic-based SCHEME DISCOVERY fallback before GENERAL_HELP
        welfare_topics = [
            # English
            "farmer", "farming", "agriculture", "pension", "loan", "business", "vendor",
            "women", "woman", "girl", "mother", "house", "housing", "health", "medical",
            "insurance", "solar", "artisan", "craft", "bpl", "ration", "subsidy", "support",
            "pregnant", "land", "acre", "hectare",
            # Hindi
            "किसान", "खेती", "कृषि", "पेंशन", "ऋण", "कर्ज", "व्यापारी", "दुकानदार", "फेरीवाला",
            "महिला", "माता", "आवास", "मकान", "घर", "स्वास्थ्य", "इलाज", "बीमा", "सौर", "सोलर",
            "राशन", "सब्सिडी", "सहायता", "गर्भवती", "सरकारी सहायता", "जमीन", "भूमि", "एकड़", "हेक्टेयर",
            # Kannada
            "ರೈತ", "ಕೃಷಿ", "ಸಾಗುವಳಿ", "ಪಿಂಚಣಿ", "ಸಾಲ", "ಬೀದಿ ವ್ಯಾಪಾರಿ", "ಮಹಿಳೆ", "ತಾಯಿ",
            "ಮನೆ", "ಆವಾಸ್", "ಆರೋಗ್ಯ", "ಚಿಕಿತ್ಸೆ", "ವಿಮೆ", "ಸೌರ", "ಸೋಲಾರ್", "ರೇಷನ್",
            "ಸಹಾಯಧನ", "ಗರ್ಭಿಣಿ", "ಸರ್ಕಾರಿ ಸಹಾಯ", "ಭೂಮಿ", "ಜಮೀನು", "ಎಕರೆ", "ಹೆಕ್ಟೇರ್",
            # Telugu
            "రైతు", "వ్యవసాయం", "వ్యవసాయ", "పింఛను", "పెన్షన్", "రుణం", "వీధి వ్యాపారి", "మహిళ", "తల్లి",
            "ఇల్లు", "గృహం", "ఆరోగ్యం", "వైద్యం", "బీమా", "సౌర", "సోలార్", "రేషన్",
            "సబ్సిడీ", "గర్భవతి", "గర్భిణీ", "గర్భిణి", "ప్రభుత్వ సహాయం", "భూమి", "ఎకరాలు", "హెక్టార్లు",
        ]
        if any(topic in lower for topic in welfare_topics):
            return IntentClassificationResult(
                intent=CitizenIntentEnum.SCHEME_DISCOVERY,
                confidence=0.78,
                detected_scheme_id=None,
                detected_language=lang,
                reasoning="Citizen mentioned welfare topic without naming a specific scheme.",
            )

        # 8. GENERAL HELP (Greetings, questions about assistant)
        if any(w in lower for w in INTENT_PATTERNS[CitizenIntentEnum.GENERAL_HELP]):
            return IntentClassificationResult(
                intent=CitizenIntentEnum.GENERAL_HELP,
                confidence=0.9,
                detected_scheme_id=None,
                detected_language=lang,
                reasoning="Greeting or conversational introductory query.",
            )

        # Fallback default: If scheme is detected, treat as information; otherwise general help
        if detected_scheme:
            return IntentClassificationResult(
                intent=CitizenIntentEnum.SCHEME_INFORMATION,
                confidence=0.7,
                detected_scheme_id=detected_scheme,
                detected_language=lang,
                reasoning="Target scheme detected without explicit action verb.",
            )

        return IntentClassificationResult(
            intent=CitizenIntentEnum.GENERAL_HELP,
            confidence=0.5,
            detected_scheme_id=None,
            detected_language=lang,
            reasoning="Unclassified conversational query routed to general guidance.",
        )

    # Class method alias
    classify = classify_intent

