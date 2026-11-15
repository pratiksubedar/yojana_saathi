"""
Yojana Saathi - Conversational Response Synthesizer
Milestone 6.3: Synthesizes multilingual, citizen-friendly responses grounded in
authoritative rule engine outcomes and RAG retrieval citations across English,
Hindi, Kannada, and Telugu. Guarantees zero hallucinations and clear next steps.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.schemas.eligibility import EligibilityStatusEnum
from app.schemas.orchestration import (
    CitizenIntentEnum,
    EligibilityOrchestrationResult,
    SynthesizedResponse,
    ValidationResult,
)
from app.schemas.rag import ProvenanceCitation
from app.services.citation_formatter import CitationFormatter

SEED_FILE_PATH = Path(__file__).resolve().parents[3] / "data" / "schemes_seed.json"
_SEED_SCHEMES_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def get_seed_scheme(scheme_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Retrieves structured scheme data from schemes_seed.json cache."""
    global _SEED_SCHEMES_CACHE
    if not scheme_id:
        return None
    if _SEED_SCHEMES_CACHE is None:
        if SEED_FILE_PATH.exists():
            try:
                with open(SEED_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _SEED_SCHEMES_CACHE = {s["id"]: s for s in data}
            except Exception:
                _SEED_SCHEMES_CACHE = {}
        else:
            _SEED_SCHEMES_CACHE = {}
    return _SEED_SCHEMES_CACHE.get(scheme_id.strip())


# Greetings and help messages
HELP_RESPONSES = {
    "en": (
        "How can I help you on Yojana Saathi today? "
        "You can check your eligibility or search for verified government welfare schemes."
    ),
    "hi": (
        "योजना साथी पर सरकारी योजनाओं के लिए मैं आपकी क्या सहायता कर सकता हूँ? "
        "आप अपनी पात्रता जांच सकते हैं या अपने लिए उपयुक्त योजनाएं खोज सकते हैं।"
    ),
    "kn": (
        "ಯೋಜನೆ ಸಾಥಿಯಲ್ಲಿ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳ ಬಗ್ಗೆ ನಾನು ನಿಮಗೆ ಹೇಗೆ ನೆರವಾಗಲಿ? "
        "ನಿಮ್ಮ ಅರ್ಹತೆಯನ್ನು ಪರಿಶೀಲಿಸಬಹುದು ಅಥವಾ ಯೋಜನೆಗಳನ್ನು ಅನ್ವೇಷಿಸಬಹುದು."
    ),
    "te": (
        "యోజన సాథిలో ప్రభుత్వ పథకాల గురించి నేను మీకు ఎలా సహాయపడగలను? "
        "మీ అర్హతను తనిఖీ చేసుకోవచ్చు లేదా పథకాలను అన్వేషించవచ్చు."
    ),
}

# Unsupported / out-of-domain query responses
UNSUPPORTED_RESPONSES = {
    "en": (
        "I specialize exclusively in official Government of India welfare schemes and citizen benefits. "
        "I cannot assist with commercial queries, entertainment, sports, or unrelated topics. "
        "Please ask about central schemes such as PM-KISAN, PM-JAY (Ayushman Bharat), PM-SVANidhi, "
        "PMAY-G, PM-KMY, PMMVY, or PM-KUSUM."
    ),
    "hi": (
        "मैं विशेष रूप से भारत सरकार की आधिकारिक कल्याणकारी योजनाओं और नागरिक लाभों के लिए सहायक हूँ। "
        "मैं खेल, मनोरंजन, व्यापार या असंबंधित विषयों में सहायता नहीं कर सकता। "
        "कृपया सरकारी योजनाओं (जैसे पीएम-किसान, आयुष्मान भारत, पीएम-स्वनिधि आदि) के बारे में पूछें।"
    ),
    "kn": (
        "ನಾನು ಭಾರತ ಸರ್ಕಾರದ ಅಧಿಕೃತ ಕಲ್ಯಾಣ ಯೋಜನೆಗಳು ಮತ್ತು ನಾಗರಿಕ ಸೌಲಭ್ಯಗಳಿಗೆ ಮಾತ್ರ ಮೀಸಲಾದ ಸಹಾಯಕ. "
        "ಮನರಂಜನೆ, ಕ್ರೀಡೆ, ವಾಣಿಜ್ಯ ಅಥವಾ ಅಸಂಬಂಧಿತ ವಿಷಯಗಳಿಗೆ ನಾನು ಉತ್ತರಿಸುವುದಿಲ್ಲ. "
        "ದಯವಿಟ್ಟು ಪಿಎಂ-ಕಿಸಾನ್, ಆಯುಷ್ಮಾನ್ ಭಾರತ್, ಪಿಎಂ-ಸ್ವನಿಧಿ ಮೊದಲಾದ ಕೇಂದ್ರ ಯೋಜನೆಗಳ ಕುರಿತು ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ."
    ),
    "te": (
        "నేను ప్రత్యేకంగా భారత ప్రభుత్వ సంక్షేమ పథకాలు మరియు పౌర ప్రయోజనాలకు మాత్రమే సహాయం అందించగలను. "
        "వినోదం, క్రీడలు, వాణిజ్యం లేదా ఇతర సంబంధం లేని అంశాలపై నేను స్పందించలేను. "
        "దయచేసి పీఎం-కిసాన్, ఆయుష్మాన్ భారత్, పీఎం-స్వనిధి వంటి ప్రభుత్వ పథకాల గురించి అడగండి."
    ),
}

SCHEME_DISCOVERY_SUMMARY = {
    "en": (
        "Here are the verified central government welfare schemes available in Yojana Saathi:\n\n"
        "1. **PM-KISAN Samman Nidhi**: ₹6,000/year income support for landholding farmer families.\n"
        "2. **PM-JAY (Ayushman Bharat)**: ₹5 lakh/year cashless health coverage for vulnerable families.\n"
        "3. **PM-SVANidhi**: Collateral-free working capital micro-loans for urban street vendors.\n"
        "4. **PMAY-G (Gramin Awaas)**: Financial assistance for constructing pucca rural houses.\n"
        "5. **PM-KMY (Kisan Maandhan)**: Assured ₹3,000/month pension for small & marginal farmers aged 60+.\n"
        "6. **PMMVY (Matru Vandana)**: ₹5,000 maternity cash benefit for pregnant and lactating mothers.\n"
        "7. **PM-KUSUM**: 60% subsidy for installing standalone solar agriculture irrigation pumps.\n\n"
        "Tell me about yourself or choose a scheme to check your eligibility!"
    ),
    "hi": (
        "योजना साथी में उपलब्ध सत्यापित केंद्रीय सरकारी योजनाएं निम्नलिखित हैं:\n\n"
        "1. **पीएम-किसान सम्मान निधि**: भूमिधारक किसान परिवारों के लिए ₹6,000/वर्ष की आय सहायता।\n"
        "2. **पीएम-जय (आयुष्मान भारत)**: पात्र परिवारों के लिए प्रति वर्ष ₹5 लाख का कैशलेस स्वास्थ्य कवर।\n"
        "3. **पीएम-स्वनिधि**: शहरी स्ट्रीट वेंडरों के लिए बिना गारंटी कार्यशील पूंजी ऋण।\n"
        "4. **पीएमएवाई-जी (ग्रामीण आवास)**: बेघर एवं कच्चे घरों में रहने वाले ग्रामीण परिवारों के लिए पक्का मकान सहायता।\n"
        "5. **पीएम-केएमवाई (किसान मानधन)**: 60 वर्ष की आयु के बाद लघु एवं सीमांत किसानों के लिए ₹3,000/माह पेंशन।\n"
        "6. **पीएमएमवीवाई (मातृ वंदना)**: गर्भवती और धात्री माताओं के लिए ₹5,000 का मातृत्व नकद लाभ।\n"
        "7. **पीएम-कुसुम**: स्टैंडअलोन सौर कृषि सिंचाई पंपों की स्थापना हेतु 60% तक सब्सिडी।\n\n"
        "अपनी पात्रता जांचने के लिए अपने बारे में बताएं या किसी योजना का चयन करें!"
    ),
    "kn": (
        "ಯೋಜನೆ ಸಾಥಿಯಲ್ಲಿ ಲಭ್ಯವಿರುವ ಪರಿಶೀಲಿಸಿದ ಕೇಂದ್ರ ಸರ್ಕಾರದ ಯೋಜನೆಗಳು:\n\n"
        "1. **ಪಿಎಂ-ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ**: ಭೂಮಾಲೀಕ ರೈತ ಕುಟುಂಬಗಳಿಗೆ ವಾರ್ಷಿಕ ₹6,000 ಆದಾಯ ಬೆಂಬಲ.\n"
        "2. **ಪಿಎಂ-ಜೆಎವೈ (ಆಯುಷ್ಮಾನ್ ಭಾರತ್)**: ಅರ್ಹ ಕುಟುಂಬಗಳಿಗೆ ವಾರ್ಷಿಕ ₹5 ಲಕ್ಷದವರೆಗೆ ನಗದು ರಹಿತ ಆರೋಗ್ಯ ವಿಮೆ.\n"
        "3. **ಪಿಎಂ-ಸ್ವನಿಧಿ**: ನಗರ ಬೀದಿ ವ್ಯಾಪಾರಿಗಳಿಗೆ ಭದ್ರತೆ ರಹಿತ ದುಡಿಯುವ ಬಂಡವಾಳ ಸಾಲ.\n"
        "4. **ಪಿಎಂಎವೈ-ಜಿ (ಗ್ರಾಮೀಣ ಆವಾಸ್)**: ಗ್ರಾಮೀಣ ಭಾಗದ ಅರ್ಹರಿಗೆ ಪಕ್ಕಾ ಮನೆ ನಿರ್ಮಾಣಕ್ಕೆ ಆರ್ಥಿಕ ನೆರವು.\n"
        "5. **ಪಿಎಂ-ಕೆಎಂವೈ (ಕಿಸಾನ್ ಮಾನ್‌ಧನ್)**: 60 ವರ್ಷ ದಾಟಿದ ಸಣ್ಣ ಮತ್ತು ಅತಿ ಸಣ್ಣ ರೈತರಿಗೆ ಮಾಸಿಕ ₹3,000 ಖಚಿತ ಪಿಂಚಣಿ.\n"
        "6. **ಪಿಎಂಎಂವಿವೈ (ಮಾತೃ ವಂದನ)**: ಗರ್ಭಿಣಿ ಮತ್ತು ಬಾಣಂತಿ ತಾಯಂದಿರಿಗೆ ₹5,000 ಹೆರಿಗೆ ಧನಸಹಾಯ.\n"
        "7. **ಪಿಎಂ-ಕುಸುಮ್**: ರೈತರಿಗೆ ಸ್ವತಂತ್ರ ಸೌರ ಕೃಷಿ ಪಂಪ್‌ಸೆಟ್ ಅಳವಡಿಕೆಗೆ 60% ಸಹಾಯಧನ.\n\n"
        "ನಿಮ್ಮ ಅರ್ಹತೆಯನ್ನು ತಿಳಿಯಲು ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಹಂಚಿಕೊಳ್ಳಿ ಅಥವಾ ಯೋಜನೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ!"
    ),
    "te": (
        "యోజన సాథిలో ధృవీకరించబడిన కేంద్ర ప్రభుత్వ పథకాలు:\n\n"
        "1. **పీఎం-కిసాన్ సమ్మాన్ నిధి**: భూమి ఉన్న రైతు కుటుంబాలకు ఏటా ₹6,000 ఆర్థిక సహాయం.\n"
        "2. **పీఎం-జేఏవై (ఆయుష్మాన్ భారత్)**: పేద కుటుంబాలకు ఏటా ₹5 లక్షల వరకు ఉచిత నగదు రహిత వైద్యం.\n"
        "3. **పీఎం-స్వనిధి**: వీధి వ్యాపారులకు పూచీకత్తు లేని వ్యాపార పెట్టుబడి రుణాలు.\n"
        "4. **పీఎంఏవై-జీ (గ్రామీణ గృహ)**: గ్రామీణ పేదలకు పక్కా ఇళ్ల నిర్మాణానికి ఆర్థిక సాయం.\n"
        "5. **పీఎం-కేఎంవై (కిసాన్ మాన్‌ధన్)**: 60 ఏళ్లు దాటిన చిన్న, సన్నకారు రైతులకు నెలకు ₹3,000 పింఛను.\n"
        "6. **పీఎంఎంవీవై (మాతృ వందన)**: గర్భిణులు, బాలింతలకు ₹5,000 ప్రసూతి ఆర్థిక ప్రయోజనం.\n"
        "7. **పీఎం-కుసుమ్**: సోలార్ వ్యవసాయ పంపుల ఏర్పాటుకు 60% రాయితీ.\n\n"
        "మీ అర్హతను పరిశీలించడానికి మీ వివరాలను తెలపండి లేదా పథకాన్ని ఎంచుకోండి!"
    ),
}


def get_contextual_quick_replies(
    scheme_id: Optional[str] = None,
    question_text: Optional[str] = None,
    status: Optional[EligibilityStatusEnum] = None,
    language: str = "en",
) -> List[str]:
    """Generates concise, contextual quick-reply buttons based on question/scheme/status."""
    lang = language if language in ("en", "hi", "kn", "te") else "en"
    q_lower = (question_text or "").lower()

    # 1. KCC agricultural cultivation or allied activity question
    if (
        "agricultural cultivation or an allied" in q_lower
        or "संबद्ध कृषि गतिविधि" in q_lower
        or "ಕೃಷಿ ಸಂಬಂಧಿತ ಚಟುವಟಿಕೆ" in q_lower
        or "అనుబంధ వ్యవసాయ" in q_lower
        or (scheme_id == "kcc" and any(k in q_lower for k in ["cultivat", "tenant", "allied", "sharecropper", "बटाईदार", "पट्टेदार", "ಗೇಣಿದಾರ", "కౌలు"]))
    ):
        return {
            "en": ["Own agricultural land", "Cultivate land as a tenant", "Sharecropper", "Animal husbandry", "Fisheries"],
            "hi": ["अपनी कृषि भूमि है", "किरायेदार/पट्टेदार", "बटाईदार", "पशुपालन/डेयरी", "मत्स्य पालन"],
            "kn": ["ಸ್ವಂತ ಕೃಷಿ ಭೂಮಿ ಇದೆ", "ಗೇಣಿದಾರ ರೈತ", "ಪಾಲುದಾರ", "ಪಶುಸಂಗೋಪನೆ/ಡೈರಿ", "ಮೀನುಗಾರಿಕೆ"],
            "te": ["స్వంత వ్యవసాయ భూమి ఉంది", "కౌలు రైతు", "వాటాదారు", "పశుసంవర్ధక/పాడి", "మత్స్య సాగు"],
        }.get(lang, ["Own agricultural land", "Cultivate land as a tenant", "Sharecropper", "Animal husbandry", "Fisheries"])

    # 2. Bank loan default question
    if any(k in q_lower for k in ["defaulter", "bank default", "unresolved default", "डिफ़ॉल्ट", "ಸುಸ್ತಿದಾರ", "డిఫాల్ట్"]):
        return {
            "en": ["No default", "Yes, loan default", "Not sure"],
            "hi": ["कोई डिफ़ॉल्ट नहीं", "हाँ, बैंक डिफ़ॉल्ट है", "पक्का नहीं पता"],
            "kn": ["ಸುಸ್ತಿದಾರನಲ್ಲ", "ಹೌದು, ಸುಸ್ತಿದಾರ", "ಖಚಿತವಿಲ್ಲ"],
            "te": ["డిఫాల్ట్ లేదు", "అవును, డిఫాల్ట్ ఉంది", "ఖచ్చితంగా తెలియదు"],
        }.get(lang, ["No default", "Yes, loan default", "Not sure"])

    # 3. Primary occupation question
    if "occupation" in q_lower or ("farmer" in q_lower and "are you a farmer" in q_lower) or "किसान" in q_lower:
        return {
            "en": ["Yes, landowner", "Yes, tenant farmer", "Allied agricultural activity", "No"],
            "hi": ["हाँ, भूमिधारक किसान", "हाँ, पट्टेदार किसान", "संबद्ध कृषि गतिविधि", "नहीं"],
            "kn": ["ಹೌದು, ಭೂಮಾಲೀಕ", "ಹೌದು, ಗೇಣಿದಾರ ರೈತ", "ಕೃಷಿ ಸಂಬಂಧಿತ ಚಟುವಟಿಕೆ", "ಇಲ್ಲ"],
            "te": ["అవును, భూయజమాని", "అవును, కౌలు రైతు", "అనుబంధ వ్యవసాయం", "కాదు"],
        }.get(lang, ["Yes, landowner", "Yes, tenant farmer", "Allied agricultural activity", "No"])

    # 4. Monthly pension question
    if any(k in q_lower for k in ["monthly pension", "pension in rupees", "पेंशन", "ಪಿಂಚಣಿ", "పెన్షన్"]):
        return {
            "en": ["No pension / Not retired", "Under ₹10,000", "₹10,000 or more", "Group D / MTS (Exempt)"],
            "hi": ["कोई पेंशन नहीं / सेवानिवृत्त नहीं", "₹10,000 से कम", "₹10,000 या अधिक", "ग्रुप D / MTS (छूट)"],
            "kn": ["ಪಿಂಚಣಿ ಇಲ್ಲ / ನಿವೃತ್ತರಲ್ಲ", "₹10,000 ಕ್ಕಿಂತ ಕಡಿಮೆ", "₹10,000 ಅಥವಾ ಹೆಚ್ಚು", "ಗ್ರೂಪ್ ಡಿ / ಎಂಟಿಎಸ್ (ವಿನಾಯಿತಿ)"],
            "te": ["పెన్షన్ లేదు / పదవీ విరమణ చేయలేదు", "₹10,000 కంటే తక్కువ", "₹10,000 లేదా అంతకంటే ఎక్కువ", "గ్రూప్ డి / ఎంటిఎస్ (మినహాయింపు)"],
        }.get(lang, ["No pension / Not retired", "Under ₹10,000", "₹10,000 or more", "Group D / MTS (Exempt)"])

    # 5. Annual family income question
    if any(k in q_lower for k in ["family income", "annual income", "वार्षिक आय", "ಆದಾಯ", "ఆదాయం"]):
        return {
            "en": ["Under ₹1.5 Lakh", "₹1.5 - ₹3 Lakh", "₹3 - ₹8 Lakh", "Above ₹8 Lakh"],
            "hi": ["₹1.5 लाख से कम", "₹1.5 - ₹3 लाख", "₹3 - ₹8 लाख", "₹8 लाख से अधिक"],
            "kn": ["₹1.5 ಲಕ್ಷಕ್ಕಿಂತ ಕಡಿಮೆ", "₹1.5 - ₹3 ಲಕ್ಷ", "₹3 - ₹8 ಲಕ್ಷ", "₹8 ಲಕ್ಷಕ್ಕಿಂತ ಹೆಚ್ಚು"],
            "te": ["₹1.5 లక్షల కంటే తక్కువ", "₹1.5 - ₹3 లక్షలు", "₹3 - ₹8 లక్షలు", "₹8 లక్షల కంటే ఎక్కువ"],
        }.get(lang, ["Under ₹1.5 Lakh", "₹1.5 - ₹3 Lakh", "₹3 - ₹8 Lakh", "Above ₹8 Lakh"])

    # 6. Landholding question
    if any(k in q_lower for k in ["how much agricultural land", "landholding size", "landholding", "कितनी भूमि", "कितनी जमीन", "ಎಷ್ಟು ಭೂಮಿ", "ಎಷ್ಟು ಎಕರೆ", "ఎంత భూమి"]) and not any(k in q_lower for k in ["cultivat", "tenant", "संस्था", "trust"]):
        return {
            "en": ["Less than 2 acres", "2 to 5 acres", "More than 5 acres", "No land / Landless"],
            "hi": ["2 एकड़ से कम", "2 से 5 एकड़", "5 एकड़ से अधिक", "भूमिहीन"],
            "kn": ["2 ಎಕರೆಗಿಂತ ಕಡಿಮೆ", "2 ರಿಂದ 5 ಎಕರೆ", "5 ಎಕರೆಗಿಂತ ಹೆಚ್ಚು", "ಭೂಹೀನ"],
            "te": ["2 ఎకరాల కంటే తక్కువ", "2 నుండి 5 ఎకరాలు", "5 ఎకరాల కంటే ఎక్కువ", "భూమిలేని"],
        }.get(lang, ["Less than 2 acres", "2 to 5 acres", "More than 5 acres", "No land / Landless"])

    # 7. Age question
    if any(k in q_lower for k in ["how old are you", "what is your age", "आपकी उम्र", "ನಿಮ್ಮ ವಯಸ್ಸು", "మీ వయస్సు"]):
        return {
            "en": ["18 - 40 years", "41 - 59 years", "60+ years (Senior)"],
            "hi": ["18 - 40 वर्ष", "41 - 59 वर्ष", "60+ वर्ष (वरिष्ठ नागरिक)"],
            "kn": ["18 - 40 ವರ್ಷ", "41 - 59 ವರ್ಷ", "60+ ವರ್ಷ (ಹಿರಿಯ ನಾಗರಿಕ)"],
            "te": ["18 - 40 సంవత్సరాలు", "41 - 59 సంవత్సరాలు", "60+ సంవత్సరాలు (సీనియర్ సిటిజన్)"],
        }.get(lang, ["18 - 40 years", "41 - 59 years", "60+ years (Senior)"])

    # 8. Category question
    if any(k in q_lower for k in ["social category", "caste category", "सामाजिक वर्ग", "ಸಾಮಾಜಿಕ ವರ್ಗ", "సామాజిక వర్గం"]):
        return {
            "en": ["General", "OBC", "SC", "ST"],
            "hi": ["सामान्य (General)", "ओबीसी (OBC)", "एससी (SC)", "एसटी (ST)"],
            "kn": ["ಸಾಮಾನ್ಯ (General)", "ಒಬಿಸಿ (OBC)", "ಎಸ್‌ಸಿ (SC)", "ಎಸ್‌ಟಿ (ST)"],
            "te": ["జనరల్ (General)", "ఓబీసీ (OBC)", "ఎస్సీ (SC)", "ఎస్టీ (ST)"],
        }.get(lang, ["General", "OBC", "SC", "ST"])

    # 9. Standard yes/no question
    if any(q_lower.startswith(w) for w in ["do you", "are you", "have you", "is your", "does your", "did you", "can you", "क्या", "ನೀವು", "ನಿಮ್ಮ", "మీరు"]) or any(k in q_lower for k in ["नामांकित", "card", "कार्ड"]):
        return {
            "en": ["Yes", "No", "Not sure"],
            "hi": ["हाँ", "नहीं", "पक्का नहीं पता"],
            "kn": ["ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ"],
            "te": ["అవును", "కాదు", "ఖచ్చితంగా తెలియదు"],
        }.get(lang, ["Yes", "No", "Not sure"])

    # 5. Outcome status-based actions
    if status == EligibilityStatusEnum.ELIGIBLE:
        return {
            "en": ["Required documents", "Application steps", "Why this scheme?", "Explore other schemes"],
            "hi": ["आवश्यक दस्तावेज", "आवेदन कैसे करें", "पात्रता कारण", "अन्य योजनाएं"],
            "kn": ["ಅಗತ್ಯ ದಾಖಲೆಗಳು", "ಅರ್ಜಿ ಸಲ್ಲಿಸುವ ವಿಧಾನ", "ಅರ್ಹತೆಯ ಕಾರಣ", "ಇತರ ಯೋಜನೆಗಳು"],
            "te": ["అవసరమైన పత్రాలు", "దరఖాస్తు విధానం", "అర్హత కారణం", "ఇతర పథకాలు"],
        }.get(lang, ["Required documents", "Application steps", "Why this scheme?", "Explore other schemes"])

    if status == EligibilityStatusEnum.NOT_ELIGIBLE:
        return {
            "en": ["Why this scheme?", "Explore other schemes", "Edit my details"],
            "hi": ["अपात्रता का कारण", "अन्य योजनाएं खोजें", "विवरण बदलें"],
            "kn": ["ಅನರ್ಹತೆಯ ಕಾರಣ", "ಇತರ ಯೋಜನೆಗಳು", "ವಿವರ ಬದಲಿಸಿ"],
            "te": ["అనర్హత కారణం", "ఇతర పథకాలు", "వివరాలు మార్చండి"],
        }.get(lang, ["Why this scheme?", "Explore other schemes", "Edit my details"])

    if status in (EligibilityStatusEnum.POSSIBLY_ELIGIBLE, EligibilityStatusEnum.NEEDS_MORE_INFORMATION):
        return {
            "en": ["Yes", "No", "Not sure"],
            "hi": ["हाँ", "नहीं", "पक्का नहीं पता"],
            "kn": ["ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ"],
            "te": ["అవును", "కాదు", "ఖచ్చితంగా తెలియదు"],
        }.get(lang, ["Yes", "No", "Not sure"])

    return {
        "en": ["Check eligibility", "View benefits", "Required documents", "How to apply", "Why this scheme?"],
        "hi": ["पात्रता जांचें", "लाभ देखें", "आवश्यक दस्तावेज", "आवेदन कैसे करें", "योजना की जानकारी"],
        "kn": ["ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ", "ಪ್ರಯೋಜನಗಳನ್ನು ನೋಡಿ", "ಅಗತ್ಯ ದಾಖಲೆಗಳು", "ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು ಹೇಗೆ", "ಯೋಜನೆಯ ವಿವರ"],
        "te": ["అర్హతను తనిఖీ చేయండి", "ప్రయోజనాలను చూడండి", "అవసరమైన పత్రాలు", "ఎలా దరఖాస్తు చేయాలి", "పథకం వివరాలు"],
    }.get(lang, ["Check eligibility", "View benefits", "Required documents", "How to apply", "Why this scheme?"])


class ResponseSynthesizer:
    """
    Synthesizes multilingual responses with strict grounding, provenance citations,
    and structured guidance based on intent and deterministic evaluation results.
    """

    @classmethod
    def synthesize(
        cls,
        intent: CitizenIntentEnum,
        language: str = "en",
        scheme_id: Optional[str] = None,
        retrieved_text: Optional[str] = None,
        citations: Optional[List[ProvenanceCitation]] = None,
        eligibility_result: Optional[EligibilityOrchestrationResult] = None,
        validation_result: Optional[ValidationResult] = None,
        active_profile: Optional[Dict[str, Any]] = None,
        candidate_evaluations: Optional[List[EligibilityOrchestrationResult]] = None,
        profile_conflicts: Optional[List[Dict[str, Any]]] = None,
        has_sufficient_evidence: bool = True,
        llm_synthesized_message: Optional[str] = None,
    ) -> SynthesizedResponse:
        """
        Synthesizes the complete conversational response.
        """
        lang = language if language in ["en", "hi", "kn", "te"] else "en"
        citations = citations or []
        active_profile = active_profile or {}
        candidate_evaluations = candidate_evaluations or []
        profile_conflicts = profile_conflicts or []
        suggested_followups: List[str] = []

        # Build conflict notice if latest message contradicted a stored/confirmed attribute
        conflict_notice = ""
        if profile_conflicts:
            conflict_lines = []
            for c in profile_conflicts:
                field_label = str(c.get("field", "")).replace("_", " ").title()
                conflict_lines.append(
                    f"Note: You mentioned **{field_label}: {c.get('new_value')}**, while your saved profile had **{c.get('confirmed_value')}**. "
                    f"I used **{c.get('new_value')}** for this check — would you like to update your profile?"
                )
            conflict_notice = "\n".join(conflict_lines) + "\n\n"

        # 0. If real LLM synthesized a grounded response, preserve all structured metadata & citations
        if llm_synthesized_message:
            all_citations = list(citations)
            if eligibility_result:
                seen_ids = {c.chunk_id for c in all_citations}
                for c in eligibility_result.citations:
                    if c.chunk_id not in seen_ids:
                        seen_ids.add(c.chunk_id)
                        all_citations.append(c)
            for ev in candidate_evaluations:
                seen_ids = {c.chunk_id for c in all_citations}
                for c in ev.citations:
                    if c.chunk_id not in seen_ids:
                        seen_ids.add(c.chunk_id)
                        all_citations.append(c)

            citations_md = CitationFormatter.format_citations_markdown(all_citations, lang)
            if eligibility_result and eligibility_result.missing_prompts:
                suggested_followups = [eligibility_result.missing_prompts[0]]
            elif candidate_evaluations:
                suggested_followups = {
                    "en": [f"Check {ev.scheme_id.upper()} eligibility" for ev in candidate_evaluations[:3]],
                    "hi": [f"{ev.scheme_id.upper()} पात्रता जांचें" for ev in candidate_evaluations[:3]],
                    "kn": [f"{ev.scheme_id.upper()} ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ" for ev in candidate_evaluations[:3]],
                    "te": [f"{ev.scheme_id.upper()} అర్హత తనిಖీ చేయండి" for ev in candidate_evaluations[:3]],
                }.get(lang, [f"Check {ev.scheme_id.upper()} eligibility" for ev in candidate_evaluations[:3]])
            else:
                s_label = scheme_id.upper() if scheme_id else ""
                suggested_followups = {
                    "en": [f"Am I eligible for {s_label}?" if s_label else "Check my eligibility", f"Documents required for {s_label}" if s_label else "Which schemes are available?"],
                    "hi": [f"क्या मैं {s_label} के लिए पात्र हूँ?" if s_label else "मेरी पात्रता जांचें", f"{s_label} के आवश्यक दस्तावेज" if s_label else "उपलब्ध योजनाएं देखें"],
                    "kn": [f"ನಾನು {s_label} ಗೆ ಅರ್ಹನೇ?" if s_label else "ನನ್ನ ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ", f"{s_label} ದಾಖಲೆಗಳು" if s_label else "ಲಭ್ಯವಿರುವ ಯೋಜನೆಗಳು"],
                    "te": [f"నేను {s_label} కి అర్హుడనా?" if s_label else "నా అర్హత తనిఖీ చేయండి", f"{s_label} పత్రాలు" if s_label else "అందుబాటులో ఉన్న పథకాలు"],
                }.get(lang, [f"Am I eligible for {s_label}?" if s_label else "Check my eligibility", f"Documents required for {s_label}" if s_label else "Which schemes are available?"])

            final_msg = llm_synthesized_message
            if conflict_notice and "update your profile" not in final_msg.lower():
                final_msg = f"{conflict_notice}{final_msg}"

            return SynthesizedResponse(
                message=final_msg,
                intent=intent,
                language=lang,
                scheme_id=scheme_id or (eligibility_result.scheme_id if eligibility_result else None),
                eligibility_result=eligibility_result,
                candidate_evaluations=candidate_evaluations,
                profile_conflicts=profile_conflicts,
                citations=all_citations,
                formatted_citations_markdown=citations_md,
                suggested_followups=suggested_followups,
                active_profile=active_profile,
            )

        # 0b. Explicit unknown-information disclosure when specific local/contact detail is absent
        if not has_sufficient_evidence:
            unknown_detail_msgs = {
                "en": (
                    "I could not find that specific detail (such as a local district office phone number, "
                    "exact address, or unlisted grievance contact) in our verified scheme records.\n\n"
                    "Please check the official government portal or toll-free national helpline listed in the "
                    "verified source citations below rather than relying on unverified third-party numbers."
                ),
                "hi": (
                    "मुझे हमारे सत्यापित योजना रिकॉर्ड में यह विशिष्ट जानकारी (जैसे जिला कार्यालय का फोन नंबर, "
                    "सटीक पता या स्थानीय शिकायत संपर्क) नहीं मिली।\n\n"
                    "कृपया नीचे दिए गए आधिकारिक सरकारी पोर्टल या राष्ट्रीय हेल्पलाइन की जांच करें।"
                ),
                "kn": (
                    "ನಮ್ಮ ಪರಿಶೀಲಿಸಿದ ಯೋಜನೆ ದಾಖಲೆಗಳಲ್ಲಿ ಆ ನಿರ್ದಿಷ್ಟ ಮಾಹಿತಿ (ಜಿಲ್ಲಾ ಕಚೇರಿ ದೂರವಾಣಿ ಸಂಖ್ಯೆ, "
                    "ನಿಖರ ವಿಳಾಸ ಅಥವಾ ಸ್ಥಳೀಯ ಕುಂದುಕೊರತೆ ಸಂಪರ್ಕ) ಕಂಡುಬಂದಿಲ್ಲ.\n\n"
                    "ದಯವಿಟ್ಟು ಕೆಳಗಿನ ಅಧಿಕೃತ ಸರ್ಕಾರಿ ಪೋರ್ಟಲ್ ಅಥವಾ ರಾಷ್ಟ್ರೀಯ ಸಹಾಯವಾಣಿಯನ್ನು ಪರಿಶೀಲಿಸಿ."
                ),
                "te": (
                    "మా ధృవీకరించిన పథకం రికార్డులలో ఆ నిర్దిಷ್ಟ వివరాలు (జిల్లా కార్యాలయ ఫోన్ నంబర్, "
                    "ఖచ్చితమైన చిరునామా లేదా స్థానిక ఫిర్యాదుల సంప్రదింపు) అందుబాటులో లేవు.\n\n"
                    "దయచేసి క్రింద ఉన్న అధికారిక ప్రభుత్వ పోర్టల్ లేదా జాతీయ హెల్ప్‌లైన్‌ను తనిఖీ చేయండి."
                ),
            }
            citations_md = CitationFormatter.format_citations_markdown(citations, lang)
            return SynthesizedResponse(
                message=unknown_detail_msgs.get(lang, unknown_detail_msgs["en"]),
                intent=intent,
                language=lang,
                scheme_id=scheme_id,
                citations=citations,
                formatted_citations_markdown=citations_md,
                suggested_followups={
                    "en": [f"Tell me about {scheme_id.upper()}" if scheme_id else "Which schemes are available?", f"How to apply for {scheme_id.upper()}?" if scheme_id else "Check my eligibility"],
                    "hi": [f"{scheme_id.upper()} की जानकारी" if scheme_id else "उपलब्ध योजनाएं देखें", f"{scheme_id.upper()} के लिए आवेदन कैसे करें" if scheme_id else "मेरी पात्रता जांचें"],
                    "kn": [f"{scheme_id.upper()} ವಿವರ ತಿಳಿಸಿ" if scheme_id else "ಲಭ್ಯವಿರುವ ಯೋಜನೆಗಳು", f"{scheme_id.upper()} ಗೆ ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು ಹೇಗೆ" if scheme_id else "ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ"],
                    "te": [f"{scheme_id.upper()} వివరాలు తెలపండి" if scheme_id else "అందుబాటులో ఉన్న పథకాలు", f"{scheme_id.upper()} కోసం ఎలా దరఖాస్తు చేయాలి" if scheme_id else "అర్హతను తనిఖీ చేయండి"],
                }.get(lang, [f"Tell me about {scheme_id.upper()}" if scheme_id else "Which schemes are available?", f"How to apply for {scheme_id.upper()}?" if scheme_id else "Check my eligibility"]),
                active_profile=active_profile,
            )

        # 1. Unsupported domain
        if intent == CitizenIntentEnum.UNSUPPORTED_QUERY:
            msg = UNSUPPORTED_RESPONSES.get(lang, UNSUPPORTED_RESPONSES["en"])
            suggested_followups = {
                "en": ["Tell me about PM-KISAN", "Who is eligible for Ayushman Bharat?", "What is PM-SVANidhi?"],
                "hi": ["PM-KISAN की जानकारी", "आयुष्मान भारत के लिए कौन पात्र है?", "PM-SVANidhi क्या है?"],
                "kn": ["PM-KISAN ಬಗ್ಗೆ ತಿಳಿಸಿ", "ಆಯುಷ್ಮಾನ್ ಭಾರತ್‌ಗೆ ಯಾರು ಅರ್ಹರು?", "PM-SVANidhi ಎಂದರೇನು?"],
                "te": ["PM-KISAN గురించి చెప్పండి", "ఆయుష్మాన్ భారత్‌కు ఎవరు అర్హులు?", "PM-SVANidhi అంటే ఏమిటి?"],
            }.get(lang, ["Tell me about PM-KISAN", "Who is eligible for Ayushman Bharat?", "What is PM-SVANidhi?"])
            return SynthesizedResponse(
                message=msg,
                intent=intent,
                language=lang,
                scheme_id=scheme_id,
                suggested_followups=suggested_followups,
                active_profile=active_profile,
            )

        # 2. General Help / Greetings
        if intent == CitizenIntentEnum.GENERAL_HELP:
            msg = HELP_RESPONSES.get(lang, HELP_RESPONSES["en"])
            suggested_followups = {
                "en": ["Which schemes are available?", "Am I eligible for PM-KISAN?", "How to apply for PM-SVANidhi loan?"],
                "hi": ["उपलब्ध योजनाएं देखें", "क्या मैं PM-KISAN के लिए पात्र हूँ?", "PM-SVANidhi के लिए आवेदन कैसे करें?"],
                "kn": ["ಲಭ್ಯವಿರುವ ಯೋಜನೆಗಳನ್ನು ನೋಡಿ", "ನಾನು PM-KISAN ಗೆ ಅರ್ಹನೇ?", "PM-SVANidhi ಗೆ ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು ಹೇಗೆ?"],
                "te": ["అందుబాటులో ఉన్న పథకాలు చూడండి", "నేను PM-KISAN కి అర్హుడనా?", "PM-SVANidhi కి ఎలా దరఖాస్తు చేయాలి?"],
            }.get(lang, ["Which schemes are available?", "Am I eligible for PM-KISAN?", "How to apply for PM-SVANidhi loan?"])
            return SynthesizedResponse(
                message=msg,
                intent=intent,
                language=lang,
                scheme_id=scheme_id,
                suggested_followups=suggested_followups,
                active_profile=active_profile,
            )

        # 3. Scheme Discovery (with deterministic shortlist evaluation)
        if intent == CitizenIntentEnum.SCHEME_DISCOVERY:
            if candidate_evaluations:
                parts: List[str] = []
                if conflict_notice:
                    parts.append(conflict_notice.strip())

                all_eval_citations: List[ProvenanceCitation] = list(citations)
                seen_chunk_ids = {c.chunk_id for c in all_eval_citations}

                bucket_eligible = [ev for ev in candidate_evaluations if ev.status == EligibilityStatusEnum.ELIGIBLE]
                bucket_needs_info = [
                    ev for ev in candidate_evaluations
                    if ev.status in (
                        EligibilityStatusEnum.NEEDS_MORE_INFORMATION,
                        EligibilityStatusEnum.POSSIBLY_ELIGIBLE,
                        EligibilityStatusEnum.NOT_VERIFIED,
                    )
                ]
                bucket_not_eligible = [ev for ev in candidate_evaluations if ev.status == EligibilityStatusEnum.NOT_ELIGIBLE]

                scheme_buckets = {
                    "eligible": [ev.scheme_id for ev in bucket_eligible],
                    "needs_info": [ev.scheme_id for ev in bucket_needs_info],
                    "not_eligible": [ev.scheme_id for ev in bucket_not_eligible],
                }

                for ev in candidate_evaluations:
                    for c in ev.citations:
                        if c.chunk_id not in seen_chunk_ids:
                            seen_chunk_ids.add(c.chunk_id)
                            all_eval_citations.append(c)

                # 1. State qualified scheme(s) cleanly without bloated dumps
                if bucket_eligible:
                    top_el = bucket_eligible[0]
                    el_title = top_el.scheme_name.get(lang) or top_el.scheme_name.get("en") or top_el.scheme_id.upper()
                    if top_el.scheme_id == "pm-kisan" and "pm-kisan" not in el_title.lower():
                        el_title = f"PM-KISAN ({el_title})"
                    qual_msg = {
                        "en": f"Great news! Based on your verified details, you qualify for **{el_title}**.",
                        "hi": f"अच्छी खबर! आपके सत्यापित विवरण के आधार पर, आप **{el_title}** के लिए पात्र हैं।",
                        "kn": f"ಉತ್ತಮ ಸುದ್ದಿ! ನಿಮ್ಮ ವಿವರಗಳ ಪ್ರಕಾರ, ನೀವು **{el_title}** ಯೋಜನೆಗೆ ಅರ್ಹರಾಗಿದ್ದೀರಿ.",
                        "te": f"శుభవార్త! మీ వివరాల ప్రకారం, మీరు **{el_title}** పథకానికి అర్హులు.",
                    }.get(lang, f"Great news! Based on your verified details, you qualify for **{el_title}**.")
                    parts.append(f"### ✅ {qual_msg}")

                has_pmkisan_large_land = (
                    active_profile.get("landholding_hectares") is not None
                    and float(active_profile["landholding_hectares"]) > 2.0
                    and any(ev.scheme_id == "pm-kisan" for ev in candidate_evaluations)
                )
                if has_pmkisan_large_land:
                    large_land_note = {
                        "en": "**Important:** For **PM-KISAN**, owning more than 2 hectares does **not** by itself disqualify you under the expanded scheme (w.e.f. 01.06.2019). Other scheme conditions and exclusion criteria still need to be checked.",
                        "hi": "**महत्वपूर्ण:** **पीएम-किसान** के लिए, 2 हेक्टेयर से अधिक भूमि होने पर भी संशोधित नियमों (01.06.2019 से प्रभावी) के तहत आप अयोग्य नहीं होते। अन्य बहिष्करण शर्तें जांची जाएंगी।",
                        "kn": "**ಪ್ರಮುಖ:** **ಪಿಎಂ-ಕಿಸಾನ್** ಗಾಗಿ 2 ಹೆಕ್ಟೇರ್‌ಗಿಂತ ಹೆಚ್ಚಿನ ಭೂಮಿ ಹೊಂದಿದ್ದರೂ (01.06.2019 ರಿಂದ) ಅರ್ಹತೆ ಇರುತ್ತದೆ. ಇತರ ಷರತ್ತುಗಳನ್ನು ಪರಿಶೀಲಿಸಬೇಕಾಗಿದೆ.",
                        "te": "**ముఖ్య గమనిక:** **పీఎం-కిసాన్** పథకానికి 2 హెక్టార్ల కంటే ఎక్కువ భూమి ఉన్నప్పటికీ (01.06.2019 నుండి) అర్హత ఉంటుంది.",
                    }.get(lang, "**Important:** For **PM-KISAN**, owning more than 2 hectares does **not** by itself disqualify you under the expanded scheme (w.e.f. 01.06.2019). Other scheme conditions and exclusion criteria still need to be checked.")
                    parts.append(large_land_note)

                # 2. Progressive next question for the top incomplete scheme (strictly ONE question)
                top_incomplete = next(
                    (ev for ev in candidate_evaluations if ev.status in (EligibilityStatusEnum.NEEDS_MORE_INFORMATION, EligibilityStatusEnum.POSSIBLY_ELIGIBLE) and ev.missing_prompts),
                    None,
                )
                if top_incomplete:
                    top_name = top_incomplete.scheme_name.get(lang) or top_incomplete.scheme_name.get("en") or top_incomplete.scheme_id.upper()
                    if top_incomplete.scheme_id == "pm-kisan" and "pm-kisan" not in top_name.lower():
                        top_name = f"PM-KISAN ({top_name})"
                    first_q = top_incomplete.missing_prompts[0]
                    sep = "\n\n"
                    if bucket_eligible:
                        check_next = {
                            "en": f"Checking **{top_name}** next:{sep}**{first_q}**",
                            "hi": f"**{top_name}** के लिए अगला प्रश्न:{sep}**{first_q}**",
                            "kn": f"**{top_name}** ಗಾಗಿ ಮುಂದಿನ ಪ್ರಶ್ನೆ:{sep}**{first_q}**",
                            "te": f"**{top_name}** కోసం తదుపరి ప్రశ్న:{sep}**{first_q}**",
                        }.get(lang, f"Checking **{top_name}** next:{sep}**{first_q}**")
                    else:
                        check_next = {
                            "en": f"Found **{top_name}** for your profile.{sep}**{first_q}**",
                            "hi": f"आपकी प्रोफाइल के लिए **{top_name}** मिली है।{sep}**{first_q}**",
                            "kn": f"ನಿಮ್ಮ ವಿವರಗಳಿಗೆ **{top_name}** ಲಭ್ಯವಿದೆ.{sep}**{first_q}**",
                            "te": f"మీ ప్రొఫైల్ కోసం **{top_name}** గుర్తించాము.{sep}**{first_q}**",
                        }.get(lang, f"Found **{top_name}** for your profile.{sep}**{first_q}**")
                    parts.append(check_next)
                    suggested_followups = get_contextual_quick_replies(
                        scheme_id=top_incomplete.scheme_id,
                        question_text=first_q,
                        status=top_incomplete.status,
                        language=lang,
                    )
                else:
                    if bucket_eligible:
                        next_action = {
                            "en": "What would you like to check next?",
                            "hi": "आप आगे क्या जांचना चाहेंगे?",
                            "kn": "ಮುಂದೆ ನೀವು ಏನನ್ನು ಪರಿಶೀಲಿಸಲು ಬಯಸುತ್ತೀರಿ?",
                            "te": "తర్వాత మీరు ఏమి తనిఖీ చేయాలనుకుంటున్నారు?",
                        }.get(lang, "What would you like to check next?")
                        parts.append(next_action)
                        suggested_followups = get_contextual_quick_replies(
                            status=EligibilityStatusEnum.ELIGIBLE,
                            language=lang,
                        )
                    else:
                        not_el_msg = {
                            "en": "Based on current criteria, you do not currently qualify for the central schemes checked.",
                            "hi": "वर्तमान मानदंडों के आधार पर, आप जांची गई केंद्रीय योजनाओं के लिए पात्र नहीं हैं।",
                            "kn": "ಪ್ರಸ್ತುತ ಮಾನದಂಡಗಳ ಪ್ರಕಾರ, ನೀವು ಪರಿಶೀಲಿಸಿದ ಕೇಂದ್ರ ಯೋಜನೆಗಳಿಗೆ ಅರ್ಹರಲ್ಲ.",
                            "te": "ప్రస్తుత నిబంధనల ప్రకారం, మీరు పరిశీలించిన కేంద్ర పథకాలకు అర్హులు కారు.",
                        }.get(lang, "Based on current criteria, you do not currently qualify for the central schemes checked.")
                        parts.append(not_el_msg)
                        suggested_followups = get_contextual_quick_replies(
                            status=EligibilityStatusEnum.NOT_ELIGIBLE,
                            language=lang,
                        )

                msg = "\n\n".join(parts)
                citations_md = CitationFormatter.format_citations_markdown(all_eval_citations, lang)
                return SynthesizedResponse(
                    message=msg,
                    intent=intent,
                    language=lang,
                    scheme_id=candidate_evaluations[0].scheme_id if len(candidate_evaluations) == 1 else None,
                    eligibility_result=candidate_evaluations[0] if len(candidate_evaluations) == 1 else None,
                    candidate_evaluations=candidate_evaluations,
                    scheme_buckets=scheme_buckets,
                    profile_conflicts=profile_conflicts,
                    citations=all_eval_citations,
                    formatted_citations_markdown=citations_md,
                    suggested_followups=suggested_followups,
                    active_profile=active_profile,
                )

            if retrieved_text:
                intro_map = {
                    "en": "Based on your question, here are the most relevant verified government schemes:\n\n",
                    "hi": "आपके प्रश्न के आधार पर, यहाँ सबसे प्रासंगिक सत्यापित सरकारी योजनाएं दी गई हैं:\n\n",
                    "kn": "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯ ಆಧಾರದ ಮೇಲೆ, ಅತ್ಯಂತ ಸೂಕ್ತವಾದ ಪರಿಶೀಲಿಸಿದ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಇಲ್ಲಿವೆ:\n\n",
                    "te": "మీ ప్రశ్న ఆధారంగా, అత్యంత సంబంధిత ధృవీకరించిన ప్రభుత్వ పథకాలు ఇక్కడ ఉన్నాయి:\n\n",
                }
                eligibility_note = {
                    "en": "\n\n*Note: Final eligibility depends on official scheme criteria. Ask me to check your eligibility for any scheme above.*",
                    "hi": "\n\n*नोट: अंतिम पात्रता आधिकारिक योजना मानदंडों पर निर्भर करती है। ऊपर दी गई किसी भी योजना के लिए अपनी पात्रता जांचने के लिए पूछें।*",
                    "kn": "\n\n*ಗಮನಿಸಿ: ಅಂತಿಮ ಅರ್ಹತೆಯು ಅಧಿಕೃತ ಯೋಜನೆಯ ಮಾನದಂಡಗಳನ್ನು ಅವಲಂಬಿಸಿರುತ್ತದೆ. ಮೇಲಿನ ಯಾವುದೇ ಯೋಜನೆಗೆ ನಿಮ್ಮ ಅರ್ಹತೆಯನ್ನು ಪರಿಶೀಲಿಸಲು ಕೇಳಿ.*",
                    "te": "\n\n*గమనిక: తుది అర్హత అధికారిక పథకం నిబంధనలపై ఆధారపడి ఉంటుంది. పైన ఉన్న ఏదైనా పథకానికి మీ అర్హతను తనిఖీ చేయమని అడగండి.*",
                }
                msg = (
                    intro_map.get(lang, intro_map["en"])
                    + retrieved_text
                    + eligibility_note.get(lang, eligibility_note["en"])
                )
                cited_schemes = []
                for c in citations:
                    if c.scheme_id and c.scheme_id not in cited_schemes:
                        cited_schemes.append(c.scheme_id)
                if cited_schemes:
                    top_sid = cited_schemes[0].upper()
                    suggested_followups = {
                        "en": [f"Am I eligible for {top_sid}?", f"Required documents for {top_sid}", "Explore other schemes"],
                        "hi": [f"{top_sid} के लिए पात्रता जांचें", f"{top_sid} के लिए दस्तावेज", "अन्य योजनाएं"],
                        "kn": [f"{top_sid} ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ", f"{top_sid} ದಾಖಲೆಗಳು", "ಇತರ ಯೋಜನೆಗಳು"],
                        "te": [f"{top_sid} అర్హత తనిఖీ", f"{top_sid} పత్రాలు", "ఇతర పథకాలు"],
                    }.get(lang, [f"Am I eligible for {top_sid}?", f"Required documents for {top_sid}", "Explore other schemes"])
                else:
                    suggested_followups = {
                        "en": ["Check my eligibility", "Required documents", "Explore other schemes"],
                        "hi": ["मेरी पात्रता जांचें", "आवश्यक दस्तावेज", "अन्य योजनाएं"],
                        "kn": ["ನನ್ನ ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ", "ಅಗತ್ಯ ದಾಖಲೆಗಳು", "ಇತರ ಯೋಜನೆಗಳು"],
                        "te": ["నా అర్హత తనిఖీ చేయండి", "అవసరమైన పత్రాలు", "ఇతర పథకాలు"],
                    }.get(lang, ["Check my eligibility", "Required documents", "Explore other schemes"])
                citations_md = CitationFormatter.format_citations_markdown(citations, lang)
                return SynthesizedResponse(
                    message=msg,
                    intent=intent,
                    language=lang,
                    scheme_id=cited_schemes[0] if len(cited_schemes) == 1 else None,
                    citations=citations,
                    formatted_citations_markdown=citations_md,
                    suggested_followups=suggested_followups,
                    active_profile=active_profile,
                )

            msg = SCHEME_DISCOVERY_SUMMARY.get(lang, SCHEME_DISCOVERY_SUMMARY["en"])
            suggested_followups = {
                "en": ["Check PM-KISAN eligibility", "Check Ayushman Bharat (PM-JAY)", "Check PM-SVANidhi vendor loan"],
                "hi": ["PM-KISAN पात्रता जांचें", "आयुष्मान भारत (PM-JAY) जांचें", "PM-SVANidhi ऋण जांचें"],
                "kn": ["PM-KISAN ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ", "ಆಯುಷ್ಮಾನ್ ಭಾರತ್ ಪರಿಶೀಲಿಸಿ", "PM-SVANidhi ಸಾಲ ಪರಿಶೀಲಿಸಿ"],
                "te": ["PM-KISAN అర్హత తనిఖీ", "ఆయుష్మాన్ భారత్ తనిఖీ", "PM-SVANidhi ఋణం తనిఖీ"],
            }.get(lang, ["Check PM-KISAN eligibility", "Check Ayushman Bharat (PM-JAY)", "Check PM-SVANidhi vendor loan"])
            return SynthesizedResponse(
                message=msg,
                intent=intent,
                language=lang,
                scheme_id=scheme_id,
                suggested_followups=suggested_followups,
                active_profile=active_profile,
            )

        # 4. Eligibility Check
        if intent == CitizenIntentEnum.ELIGIBILITY_CHECK and eligibility_result:
            if eligibility_result.is_clarification_needed:
                return SynthesizedResponse(
                    message=eligibility_result.summary,
                    intent=intent,
                    language=lang,
                    scheme_id=scheme_id,
                    eligibility_result=eligibility_result,
                    suggested_followups=[
                        "PM-KISAN", "PM-JAY", "PM-SVANidhi", "PMAY-G", "PM-KMY", "PMMVY", "PM-KUSUM"
                    ],
                    active_profile=active_profile,
                )

            # Build concise, customer-support style outcome explanation
            lines: List[str] = []
            if conflict_notice:
                lines.append(conflict_notice.strip())
                lines.append("")

            s_name = (
                eligibility_result.scheme_name.get(lang)
                or eligibility_result.scheme_name.get("en")
                or (scheme_id or "").upper()
            )

            # 4a. Pending slot clarification: ask strictly ONE concise question
            if eligibility_result.missing_prompts:
                next_question = eligibility_result.missing_prompts[0]
                ask_prefix = {
                    "en": "Got it. Next question:",
                    "hi": "समझ गया। अगला प्रश्न:",
                    "kn": "ಅರ್ಥವಾಯಿತು. ಮುಂದಿನ ಪ್ರಶ್ನೆ:",
                    "te": "అర్థమైంది. తదుపరి ప్రశ్న:",
                }.get(lang, "Got it. Next question:")
                lines.append(f"{ask_prefix}\n\n**{next_question}**")
                suggested_followups = get_contextual_quick_replies(
                    scheme_id=eligibility_result.scheme_id,
                    question_text=next_question,
                    status=eligibility_result.status,
                    language=lang,
                )
            # 4b. Eligible outcome: concise confirmation + action buttons
            elif eligibility_result.status == EligibilityStatusEnum.ELIGIBLE:
                congrats = {
                    "en": f"Great news! You satisfy all evaluated eligibility criteria for **{s_name}**.",
                    "hi": f"अच्छी खबर! आप **{s_name}** के लिए सभी मूल्यांकित पात्रता मानदंडों को पूरा करते हैं।",
                    "kn": f"ಉತ್ತಮ ಸುದ್ದಿ! ನೀವು **{s_name}** ಗಾಗಿ ಎಲ್ಲಾ ಮೌಲ್ಯಮಾಪನ ಮಾನದಂಡಗಳನ್ನು ಪೂರೈಸುತ್ತೀರಿ.",
                    "te": f"శుభవార్త! మీరు **{s_name}** కోసం అన్ని అర్హత ప్రమాణాలను పూర్తి చేశారు.",
                }.get(lang, f"Great news! You satisfy all evaluated criteria for **{s_name}**.")
                lines.append(f"### ✅ {congrats}\n")

                if eligibility_result.satisfied_conditions:
                    sat_summary = "; ".join(eligibility_result.satisfied_conditions[:2])
                    lines.append(f"- **Key criteria met:** {sat_summary}\n")

                next_prompt = {
                    "en": "What would you like to check next?",
                    "hi": "आप आगे क्या देखना चाहेंगे?",
                    "kn": "ಮುಂದೆ ನೀವು ಏನನ್ನು ಪರಿಶೀಲಿಸಲು ಬಯಸುತ್ತೀರಿ?",
                    "te": "తర్వాత మీరు ఏమి తనిఖీ చేయాలనుకుంటున్నారు?",
                }.get(lang, "What would you like to check next?")
                lines.append(next_prompt)
                suggested_followups = {
                    "en": ["Required documents", "Application steps", "Why this scheme?", "Explore other schemes"],
                    "hi": ["आवश्यक दस्तावेज", "आवेदन कैसे करें", "पात्रता कारण", "अन्य योजनाएं"],
                    "kn": ["ಅಗತ್ಯ ದಾಖಲೆಗಳು", "ಅರ್ಜಿ ಸಲ್ಲಿಸುವ ವಿಧಾನ", "ಅರ್ಹತೆಯ ಕಾರಣ", "ಇತರ ಯೋಜನೆಗಳು"],
                    "te": ["అవసరమైన పత్రాలు", "దరఖాస్తు విధానం", "అర్హత కారణం", "ఇతర పథకాలు"],
                }.get(lang, ["Required documents", "Application steps", "Why this scheme?", "Explore other schemes"])
            # 4c. Not eligible outcome: concise reason + action buttons
            elif eligibility_result.status == EligibilityStatusEnum.NOT_ELIGIBLE:
                not_elig_msg = {
                    "en": f"You do not currently qualify for **{s_name}**.",
                    "hi": f"आप वर्तमान में **{s_name}** के लिए पात्र नहीं हैं।",
                    "kn": f"ನೀವು ಪ್ರಸ್ತುತ **{s_name}** ಗೆ ಅರ್ಹರಲ್ಲ.",
                    "te": f"మీరు ప్రస్తుతం **{s_name}** కి అర్హులు కారు.",
                }.get(lang, f"You do not currently qualify for **{s_name}**.")
                lines.append(f"### ℹ️ {not_elig_msg}\n")

                if eligibility_result.failed_conditions:
                    fail_summary = "; ".join(eligibility_result.failed_conditions[:2])
                    reason_label = {
                        "en": "Condition not met:",
                        "hi": "अपूर्ण शर्त:",
                        "kn": "ಪೂರೈಸದ ಷರತ್ತು:",
                        "te": "పూర్తికాని నిబంధన:",
                    }.get(lang, "Condition not met:")
                    lines.append(f"- **{reason_label}** {fail_summary}\n")

                suggested_followups = {
                    "en": ["Why this scheme?", "Explore other schemes", "Edit my details"],
                    "hi": ["अपात्रता का कारण", "अन्य योजनाएं खोजें", "विवरण बदलें"],
                    "kn": ["ಅನರ್ಹತೆಯ ಕಾರಣ", "ಇತರ ಯೋಜನೆಗಳು", "ವಿವರ ಬದಲಿಸಿ"],
                    "te": ["అనర్హత కారణం", "ఇతర పథకాలు", "వివరాలు మార్చండి"],
                }.get(lang, ["Why this scheme?", "Explore other schemes", "Edit my details"])
            # 4d. Other outcomes
            else:
                lines.append(f"### {eligibility_result.summary}\n")
                suggested_followups = {
                    "en": ["Check eligibility", "Required documents", "How to apply", "Explore other schemes"],
                    "hi": ["पात्रता जांचें", "आवश्यक दस्तावेज", "आवेदन कैसे करें", "अन्य योजनाएं"],
                    "kn": ["ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ", "ಅಗತ್ಯ ದಾಖಲೆಗಳು", "ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು ಹೇಗೆ", "ಇತರ ಯೋಜನೆಗಳು"],
                    "te": ["అర్హతను తనిఖీ చేయండి", "అవసరమైన పత్రాలు", "ఎలా దరఖాస్తు చేయాలి", "ఇతర పథకాలు"],
                }.get(lang, ["Check eligibility", "Required documents", "How to apply", "Explore other schemes"])

            msg = "\n".join(lines).strip()
            all_citations = list(eligibility_result.citations) + citations
            citations_md = CitationFormatter.format_citations_markdown(all_citations, lang)

            return SynthesizedResponse(
                message=msg,
                intent=intent,
                language=lang,
                scheme_id=eligibility_result.scheme_id,
                eligibility_result=eligibility_result,
                profile_conflicts=profile_conflicts,
                citations=all_citations,
                formatted_citations_markdown=citations_md,
                suggested_followups=suggested_followups,
                active_profile=active_profile,
            )

        # 5. Informational, Document, Application, or Discovery with structured data & retrieved text
        message_body = retrieved_text or ""
        s_display = (scheme_id or "this scheme").upper()
        seed_s = get_seed_scheme(scheme_id)
        if seed_s:
            s_name = seed_s.get("names", {}).get(lang) or seed_s.get("names", {}).get("en") or s_display
        else:
            s_name = s_display

        if intent == CitizenIntentEnum.DOCUMENT_REQUIREMENTS and seed_s and seed_s.get("documents"):
            hdr = {
                "en": f"### 📄 Required Documents for {s_name}:",
                "hi": f"### 📄 {s_name} के लिए आवश्यक दस्तावेज:",
                "kn": f"### 📄 {s_name} ಗಾಗಿ ಅಗತ್ಯ ದಾಖಲೆಗಳು:",
                "te": f"### 📄 {s_name} కోసం అవసరమైన పత్రాలు:",
            }.get(lang, f"### 📄 Required Documents for {s_name}:")
            doc_lines = [hdr, ""]
            for doc in seed_s["documents"]:
                d_name = doc.get("names", {}).get(lang) or doc.get("names", {}).get("en", "Document")
                d_desc = doc.get("descriptions", {}).get(lang) or doc.get("descriptions", {}).get("en", "")
                mand_label = {
                    "en": "Mandatory" if doc.get("is_mandatory") else "Optional",
                    "hi": "अनिवार्य" if doc.get("is_mandatory") else "वैकल्पिक",
                    "kn": "ಕಡ್ಡಾಯ" if doc.get("is_mandatory") else "ಐಚ್ಛಿಕ",
                    "te": "తప్పనిసరి" if doc.get("is_mandatory") else "ఐచ్ఛికం",
                }.get(lang, "Mandatory")
                doc_lines.append(f"- **{d_name}** ({mand_label}): {d_desc}")
            sep = chr(10)
            message_body = sep.join(doc_lines).strip()

        elif intent == CitizenIntentEnum.APPLICATION_GUIDANCE and seed_s and seed_s.get("application_procedure"):
            hdr = {
                "en": f"### 📝 How to Apply for {s_name}:",
                "hi": f"### 📝 {s_name} के लिए आवेदन कैसे करें:",
                "kn": f"### 📝 {s_name} ಗೆ ಅರ್ಜಿ ಸಲ್ಲಿಸುವ ವಿಧಾನ:",
                "te": f"### 📝 {s_name} కోసం దరఖాస్తు విధానం:",
            }.get(lang, f"### 📝 How to Apply for {s_name}:")
            step_lines = [hdr, ""]
            for step in seed_s["application_procedure"][:4]:
                st_num = step.get("step_number", 1)
                st_title = step.get("titles", {}).get(lang) or step.get("titles", {}).get("en", "")
                st_desc = step.get("descriptions", {}).get(lang) or step.get("descriptions", {}).get("en", "")
                step_lines.append(f"{st_num}. **{st_title}**: {st_desc}")
            portal_url = seed_s.get("official_url") or "https://www.myscheme.gov.in"
            portal_label = {
                "en": "Official Portal",
                "hi": "आधिकारिक पोर्टल",
                "kn": "ಅಧಿಕೃತ ಪೋರ್ಟಲ್",
                "te": "అధికారిక పోర్టల్",
            }.get(lang, "Official Portal")
            step_lines.append(f"🌐 **{portal_label}:** [{portal_url}]({portal_url})")
            sep = chr(10)
            message_body = sep.join(step_lines).strip()

        if not message_body:
            fallback_msgs = {
                "en": f"Here is the verified information for {s_name}.",
                "hi": f"{s_name} के लिए सत्यापित जानकारी यहाँ दी गई है।",
                "kn": f"{s_name} ಕುರಿತ ಪರಿಶೀಲಿಸಿದ ಮಾಹಿತಿ ಇಲ್ಲಿದೆ.",
                "te": f"{s_name} కోసం ధృవీకరించిన సమాచారం ఇక్కడ ఉంది.",
            }
            message_body = fallback_msgs.get(lang, fallback_msgs["en"])

        citations_md = CitationFormatter.format_citations_markdown(citations, lang)

        if intent == CitizenIntentEnum.DOCUMENT_REQUIREMENTS:
            suggested_followups = {
                "en": ["How to apply", "Check eligibility", "Explore other schemes"],
                "hi": ["आवेदन कैसे करें", "पात्रता जांचें", "अन्य योजनाएं"],
                "kn": ["ಅರ್ಜಿ ಸಲ್ಲಿಸುವ ವಿಧಾನ", "ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ", "ಇತರ ಯೋಜನೆಗಳು"],
                "te": ["దరఖాస్తు విధానం", "అర్హత తనిఖీ", "ఇతర పథకాలు"],
            }.get(lang, ["How to apply", "Check eligibility", "Explore other schemes"])
        elif intent == CitizenIntentEnum.APPLICATION_GUIDANCE:
            suggested_followups = {
                "en": ["Required documents", "Check eligibility", "Explore other schemes"],
                "hi": ["आवश्यक दस्तावेज", "पात्रता जांचें", "अन्य योजनाएं"],
                "kn": ["ಅಗತ್ಯ ದಾಖಲೆಗಳು", "ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ", "ಇತರ ಯೋಜನೆಗಳು"],
                "te": ["అవసరమైన పత్రాలు", "అర్హత తనిఖీ", "ఇతర పథకాలు"],
            }.get(lang, ["Required documents", "Check eligibility", "Explore other schemes"])
        else:
            suggested_followups = {
                "en": ["Check eligibility", "Required documents", "How to apply"],
                "hi": ["पात्रता जांचें", "आवश्यक दस्तावेज", "आवेदन कैसे करें"],
                "kn": ["ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ", "ಅಗತ್ಯ ದಾಖಲೆಗಳು", "ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು ಹೇಗೆ"],
                "te": ["అర్హత తనిఖీ", "అవసరమైన పత్రాలు", "దరఖాస్తు విధానం"],
            }.get(lang, ["Check eligibility", "Required documents", "How to apply"])

        return SynthesizedResponse(
            message=message_body,
            intent=intent,
            language=lang,
            scheme_id=scheme_id,
            citations=citations,
            formatted_citations_markdown=citations_md,
            suggested_followups=suggested_followups,
            active_profile=active_profile,
        )

