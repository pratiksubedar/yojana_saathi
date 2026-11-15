import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.eligibility import (
    EligibilityStatusEnum,
    RuleCompletenessEnum,
    ConditionStatusEnum,
    EvaluatedCondition,
    MissingFieldInfo,
    SchemeEligibilityResult,
)


class RuleEngineError(Exception):
    """Base exception for deterministic rule evaluation errors."""
    pass


class MalformedRuleException(RuleEngineError):
    """Raised when a rule AST is missing essential structural keys or has invalid types."""
    pass


class UnsupportedOperatorException(RuleEngineError):
    """Raised when a condition specifies an unknown comparison operator."""
    pass


# Supported operator aliases
OPERATOR_MAP = {
    "equals": "equals",
    "eq": "equals",
    "==": "equals",
    "not_equals": "not_equals",
    "neq": "not_equals",
    "!=": "not_equals",
    "in": "in",
    "contains": "in",
    "not_in": "not_in",
    "greater_than": "greater_than",
    "gt": "greater_than",
    ">": "greater_than",
    "less_than": "less_than",
    "lt": "less_than",
    "<": "less_than",
    "greater_than_or_equal": "greater_than_or_equal",
    "gte": "greater_than_or_equal",
    ">=": "greater_than_or_equal",
    "less_than_or_equal": "less_than_or_equal",
    "lte": "less_than_or_equal",
    "<=": "less_than_or_equal",
}

# Standard multilingual disclaimers across all 4 project languages
STANDARD_DISCLAIMERS: Dict[str, str] = {
    "en": (
        "This eligibility assessment is preliminary automated guidance based on publicly available "
        "government scheme guidelines and does not constitute official approval, certification, "
        "or guarantee of benefit disbursement."
    ),
    "hi": (
        "यह पात्रता मूल्यांकन सार्वजनिक रूप से उपलब्ध सरकारी योजना दिशानिर्देशों पर आधारित "
        "प्रारंभिक स्वचालित मार्गदर्शन है और यह किसी भी प्रकार का आधिकारिक सरकारी अनुमोदन, "
        "प्रमाणन या लाभ की गारंटी नहीं है।"
    ),
    "kn": (
        "ಈ ಅರ್ಹತಾ ಮೌಲ್ಯಮಾಪನವು ಸಾರ್ವಜನಿಕವಾಗಿ ಲಭ್ಯವಿರುವ ಸರ್ಕಾರಿ ಯೋಜನೆ ಮಾರ್ಗಸೂಚಿಗಳನ್ನು ಆಧರಿಸಿದ "
        "ಪ್ರಾಥಮಿಕ ಸ್ವಯಂಚಾಲಿತ ಮಾರ್ಗದರ್ಶನವಾಗಿದೆ ಮತ್ತು ಇದು ಅಧಿಕೃತ ಸರ್ಕಾರಿ ಅನುಮೋದನೆ, ಪ್ರಮಾಣಪತ್ರ ಅಥವಾ ಖಾತರಿಯಾಗಿರುವುದಿಲ್ಲ."
    ),
    "te": (
        "ఈ అర్హత అంచనా అనేది బహిరంగంగా అందుబాటులో ఉన్న ప్రభుత్వ పథక మార్గదర్శకాల ఆధారంగా అందించబడిన "
        "ప్రాథమిక ఆటోమేటెడ్ మార్గదర్శకత్వం మాత్రమే. ఇది అధికారిక ప్రభుత్వ ఆమోదం, ధృవీకరణ లేదా ప్రయోజన హామీ కాదు."
    ),
}

# Standard multilingual outcome summaries
OUTCOME_SUMMARIES: Dict[EligibilityStatusEnum, Dict[str, str]] = {
    EligibilityStatusEnum.ELIGIBLE: {
        "en": "You satisfy all evaluated eligibility requirements for this scheme.",
        "hi": "आप इस योजना के लिए सभी मूल्यांकित पात्रता शर्तों को पूरा करते हैं।",
        "kn": "ನೀವು ಈ ಯೋಜನೆಗಾಗಿ ಮೌಲ್ಯಮಾಪನ ಮಾಡಲಾದ ಎಲ್ಲಾ ಅರ್ಹತಾ ಮಾನದಂಡಗಳನ್ನು ಪೂರೈಸುತ್ತೀರಿ.",
        "te": "మీరు ఈ పథకానికి సంబంధించిన అన్ని అర్హత ప్రమాణాలను పూర్తి చేశారు.",
    },
    EligibilityStatusEnum.NOT_ELIGIBLE: {
        "en": "You do not meet one or more mandatory eligibility or exclusion criteria for this scheme.",
        "hi": "आप इस योजना के लिए एक या अधिक अनिवार्य पात्रता या बहिष्करण मानदंडों को पूरा नहीं करते हैं।",
        "kn": "ನೀವು ಈ ಯೋಜನೆಯ ಒಂದು ಅಥವಾ ಹೆಚ್ಚಿನ ಕಡ್ಡಾಯ ಅರ್ಹತೆ ಅಥವಾ ಹೊರಗಿಡುವ ಮಾನದಂಡಗಳನ್ನು ಪೂರೈಸುವುದಿಲ್ಲ.",
        "te": "మీరు ఈ పథకానికి సంబంధించిన ఒకటి లేదా అంతకంటే ఎక్కువ తప్పనిసరి అర్హతలు లేదా మినహాయింపు ప్రమాణాలను పూర్తి చేయలేదు.",
    },
    EligibilityStatusEnum.POSSIBLY_ELIGIBLE: {
        "en": "You may be eligible, but additional information is required to complete the verification.",
        "hi": "आप पात्र हो सकते हैं, लेकिन सत्यापन पूरा करने के लिए अतिरिक्त जानकारी की आवश्यकता है।",
        "kn": "ನೀವು ಅರ್ಹರಾಗಿರಬಹುದು, ಆದರೆ ಪರಿಶೀಲನೆ ಪೂರ್ಣಗೊಳಿಸಲು ಹೆಚ್ಚುವರಿ ಮಾಹಿತಿಯ ಅಗತ್ಯವಿದೆ.",
        "te": "మీరు అర్హులు కావచ్చు, కానీ ధృవీకరణ పూర్తి చేయడానికి అదనపు సమాచారం అవసరం.",
    },
}

# Conservative multilingual summaries for PARTIAL or UNVERIFIED scheme rules
PARTIAL_VERIFICATION_SUMMARIES: Dict[str, str] = {
    "en": (
        "Preliminary criteria satisfied. However, this scheme's rule set is partially verified "
        "against official guidelines. Manual verification of unresolved statutory criteria is required "
        "before official government approval."
    ),
    "hi": (
        "प्रारंभिक मानदंड पूरे हो गए हैं। हालांकि, इस योजना के नियमों का केवल आंशिक सत्यापन हुआ है। "
        "आधिकारिक सरकारी अनुमोदन से पहले शेष वैधानिक मानदंडों का सत्यापन आवश्यक है।"
    ),
    "kn": (
        "ಪ್ರಾಥಮಿಕ ಮಾನದಂಡಗಳನ್ನು ಪೂರೈಸಲಾಗಿದೆ. ಆದರೆ ಈ ಯೋಜನೆಯ ನಿಯಮಗಳು ಅಧಿಕೃತ ಮಾರ್ಗಸೂಚಿಗಳೊಂದಿಗೆ ಭಾಗಶಃ "
        "ಪರಿಶೀಲಿಸಲ್ಪಟ್ಟಿವೆ. ಅಂತಿಮ ಅಧಿಕೃತ ಅನುಮೋದನೆಗೆ ಮೊದಲು ಉಳಿದ ಶಾಸನಬದ್ಧ ಮಾನದಂಡಗಳ ಪರಿಶೀಲನೆ ಅಗತ್ಯವಿದೆ."
    ),
    "te": (
        "ప్రాథమిక ప్రమాణాలు నెరవేరాయి. అయితే ఈ పథకం యొక్క నిబంధనలు అధికారిక మార్గదర్శకాలతో పాక్షికంగా మాత్రమే "
        "ధృవీకరించబడ్డాయి. అధికారిక ప్రభుత్వ ఆమోదానికి ముందు మిగిలిన చట్టబద్ధమైన ప్రమాణాల ధృవీకరణ అవసరం."
    ),
}

# Conversational prompts for known citizen attributes
FIELD_PROMPTS: Dict[str, Dict[str, Any]] = {
    "occupation": {
        "type": "select",
        "prompts": {
            "en": "Please state your primary occupation (e.g., Farmer, Street Vendor, Laborer).",
            "hi": "कृपया अपना मुख्य व्यवसाय बताएं (जैसे किसान, स्ट्रीट वेंडर, मजदूर)।",
            "kn": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಾಥಮಿಕ ಉದ್ಯೋಗವನ್ನು ತಿಳಿಸಿ (ಉದಾ: ರೈತ, ಬೀದಿ ವ್ಯಾಪಾರಿ, ಕೂಲಿ ಕಾರ್ಮಿಕ).",
            "te": "దయచేసి మీ ప్రాథమిక వృత్తిని తెలియజేయండి (ఉదా: రైతు, వీధి వ్యాపారి, కూలీ).",
        },
    },
    "landholding_hectares": {
        "type": "number",
        "prompts": {
            "en": "Please specify your agricultural landholding size in hectares.",
            "hi": "कृपया हेक्टेयर में अपनी कृषि भूमि का आकार बताएं।",
            "kn": "ದಯವಿಟ್ಟು ಹೆಕ್ಟೇರ್‌ಗಳಲ್ಲಿ ನಿಮ್ಮ ಕೃಷಿ ಭೂಮಿಯ ವಿಸ್ತೀರ್ಣವನ್ನು ನಮೂದಿಸಿ.",
            "te": "దయచేసి హెక్టార్లలో మీ వ్యవసాయ భూమి విస్తీర్ణాన్ని తెలపండి.",
        },
    },
    "has_bpl_card": {
        "type": "boolean",
        "prompts": {
            "en": "Do you possess an active Below Poverty Line (BPL) or Ration Card?",
            "hi": "क्या आपके पास सक्रिय गरीबी रेखा से नीचे (BPL) या राशन कार्ड है?",
            "kn": "ನಿಮ್ಮ ಬಳಿ ಸಕ್ರಿಯ ಬಿಪಿಎಲ್ (BPL) ಅಥವಾ ರೇಷನ್ ಕಾರ್ಡ್ ಇದೆಯೇ?",
            "te": "మీ వద్ద సక్రియ బిపిఎల్ (BPL) లేదా రేషన్ కార్డు ఉందా?",
        },
    },
    "has_nfsa_priority_or_secc_entitlement": {
        "type": "boolean",
        "prompts": {
            "en": "Is your household enrolled under the National Food Security Act (NFSA Priority / Antyodaya Ration Card) or identified in the SECC 2011 deprivation list?",
            "hi": "क्या आपका परिवार राष्ट्रीय खाद्य सुरक्षा अधिनियम (एनएफएसए प्राथमिकता / अंत्योदय राशन कार्ड) के तहत पंजीकृत है या एसईसीसी 2011 वंचना सूची में शामिल है?",
            "kn": "ನಿಮ್ಮ ಕುಟುಂಬವು ರಾಷ್ಟ್ರೀಯ ಆಹಾರ ಭದ್ರತಾ ಕಾಯ್ದೆ (NFSA ಆದ್ಯತಾ / ಅಂತ್ಯೋದಯ ಪಡಿತರ ಚೀಟಿ) ಅಡಿಯಲ್ಲಿ ನೋಂದಾಯಿತವಾಗಿದೆಯೇ ಅಥವಾ ಎಸ್‌ಇಸಿಸಿ 2011 ಪಟ್ಟಿಯಲ್ಲಿದೆಯೇ?",
            "te": "మీ కుటుంబం జాతీయ ఆహార భద్రతా చట్టం (NFSA ప్రాధాన్యత / అంత్యోదయ రేషన్ కార్డు) కింద నమోదై ఉందా లేదా SECC 2011 జాబಿತాలో ఉందా?",
        },
    },
    "owns_motorized_three_or_four_wheeler": {
        "type": "boolean",
        "prompts": {
            "en": "Does your household own any motorised three-wheeler or four-wheeler vehicle? (Note: Motorised two-wheelers are exempt under revised PMAY-G guidelines).",
            "hi": "क्या आपके परिवार के पास कोई तिपहिया या चारपहिया मोटर वाहन है? (नोट: संशोधित पीएमएवाई-जी दिशानिर्देशों के तहत दोपहिया वाहन छूट प्राप्त हैं)।",
            "kn": "ನಿಮ್ಮ ಕುಟುಂಬದ ಬಳಿ ತ್ರಿಚಕ್ರ ಅಥವಾ ನಾಲ್ಕು ಚಕ್ರದ ಮೋಟಾರು ವಾಹನವಿದೆಯೇ? (ಗಮನಿಸಿ: ಪರಿಷ್ಕೃತ ನಿಯಮಗಳಡಿ ದ್ವಿಚಕ್ರ ವಾಹನಗಳಿಗೆ ವಿನಾಯಿತಿ ಇದೆ).",
            "te": "మీ కుటుంబానికి త్రిచక్ర లేదా నాలుగు చక్రాల మోటారు వాహనం ఉందా? (గమనిక: సవరించిన నిబంధనల ప్రకారం ద్విచక్ర వాహనాలకు మినహాయింపు కలదు).",
        },
    },
    "household_monthly_income_inr": {
        "type": "number",
        "prompts": {
            "en": "What is the highest monthly income earned by any individual member of your household in rupees?",
            "hi": "आपके परिवार के किसी भी सदस्य द्वारा अर्जित अधिकतम मासिक आय (रुपये में) कितनी है?",
            "kn": "ನಿಮ್ಮ ಕುಟುಂಬದ ಯಾವುದೇ ಸದಸ್ಯರು ಗಳಿಸುವ ಗರಿಷ್ಠ ಮಾಸಿಕ ಆದಾಯ ಎಷ್ಟು (ರೂಪಾಯಿಗಳಲ್ಲಿ)?",
            "te": "మీ కుటుంబంలోని ఏ సభ్యుడైనా సంపాదించే గరిష్ట నెలవారీ ఆదాయం ఎంత (రూపాయలలో)?",
        },
    },
    "pays_income_tax": {
        "type": "boolean",
        "prompts": {
            "en": "Did you or your family pay income tax in the last assessment year?",
            "hi": "क्या आपने या आपके परिवार ने पिछले निर्धारण वर्ष में आयकर का भुगतान किया है?",
            "kn": "ನೀವು ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬವು ಕಳೆದ ಮೌಲ್ಯಮಾಪನ ವರ್ಷದಲ್ಲಿ ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿಸಿದ್ದೀರಾ?",
            "te": "మీరు లేదా మీ కుటుంబం గత అసెస్‌మెంట్ సంవత్సరంలో ఆదాయపు పన్ను చెల్లించారా?",
        },
    },
    "is_institutional_landholder": {
        "type": "boolean",
        "prompts": {
            "en": "Is the agricultural land registered in the name of an institution or trust?",
            "hi": "क्या कृषि भूमि किसी संस्था या ट्रस्ट के नाम पर दर्ज है?",
            "kn": "ಕೃಷಿ ಭೂಮಿಯು ಯಾವುದೇ ಸಂಸ್ಥೆ ಅಥವಾ ಟ್ರಸ್ಟ್‌ನ ಹೆಸರಿನಲ್ಲಿ ನೋಂದಾಯಿಸಲಾಗಿದೆಯೇ?",
            "te": "వ్యవసాయ భూమి ఏదైనా సంస్థ లేదా ట్రస్ట్ పేరు మీద నమోదై ఉందా?",
        },
    },
    "age": {
        "type": "number",
        "prompts": {
            "en": "Please provide your age in years.",
            "hi": "कृपया अपनी आयु (वर्षों में) बताएं।",
            "kn": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ವಯಸ್ಸನ್ನು ನಮೂದಿಸಿ.",
            "te": "దయచేసి మీ వయస్సును తెలపండి.",
        },
    },
    "owns_pucca_house": {
        "type": "boolean",
        "prompts": {
            "en": "Do you or any member of your household own a pucca (permanent concrete) house?",
            "hi": "क्या आपके या आपके परिवार के किसी सदस्य के पास पक्का मकान है?",
            "kn": "ನಿಮ್ಮ ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬದ ಸದಸ್ಯರ ಹೆಸರಿನಲ್ಲಿ ಪಕ್ಕಾ ಮನೆ ಇದೆಯೇ?",
            "te": "మీకు లేదా మీ కుటుంబ సభ్యులకు పక్కా ఇల్లు ఉందా?",
        },
    },
    "has_government_health_insurance": {
        "type": "boolean",
        "prompts": {
            "en": "Are you covered under any other government or statutory health insurance scheme (e.g., CGHS, ESIC)?",
            "hi": "क्या आप किसी अन्य सरकारी स्वास्थ्य बीमा योजना (जैसे सीजीएचएस, ईएसआईसी) के तहत कवर हैं?",
            "kn": "ನೀವು ಯಾವುದೇ ಇತರ ಸರ್ಕಾರಿ ಆರೋಗ್ಯ ವಿಮಾ ಯೋಜನೆಯಡಿ (ಉದಾ: CGHS, ESIC) ಒಳಪಟ್ಟಿದ್ದೀರಾ?",
            "te": "మీరు ఏదైనా ఇతర ప్రభుత్వ ఆరోగ్య బీమా పథకం (ఉదా: CGHS, ESIC) పరిధిలో ఉన్నారా?",
        },
    },
    "is_regular_govt_employee": {
        "type": "boolean",
        "prompts": {
            "en": "Are you or any family member a regular government/PSU employee? (Exempt: Multi-Tasking Staff / Class IV / Group D employees).",
            "hi": "क्या आप या आपके परिवार का कोई सदस्य नियमित सरकारी/पीएसयू कर्मचारी हैं? (छूट: मल्टी-टास्किंग स्टाफ / क्लास IV / ग्रुप डी कर्मचारी पात्र हैं)।",
            "kn": "ನೀವು ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬದ ಸದಸ್ಯರು ಕಾಯಂ ಸರ್ಕಾರಿ ನೌಕರರೇ? (ವಿನಾಯಿತಿ: ಗ್ರೂಪ್ ಡಿ / ಮಲ್ಟಿ-ಟಾಸ್ಕಿಂಗ್ ಸಿಬ್ಬಂದಿಗೆ ವಿನಾಯಿತಿ ಇದೆ).",
            "te": "మీరు లేదా మీ కుటుంబ సభ్యులు శాశ్వత ప్రభుత్వ ఉద్యోగులా? (మినహాయింపు: గ్రూప్ డి / మల్టీ-టాస్కింగ్ సిబ్బందికి మినహాయింపు కలదు).",
        },
    },
    "monthly_pension_inr": {
        "type": "number",
        "prompts": {
            "en": "If retired, what is your monthly pension in rupees? (Group D / Class IV / MTS pensioners are exempt).",
            "hi": "यदि सेवानिवृत्त हैं, तो आपकी मासिक पेंशन (रुपये में) कितनी है? (ग्रुप डी / एमटीएस पेंशनभोगी इस शर्त से मुक्त हैं)।",
            "kn": "ನಿವೃತ್ತರಾಗಿದ್ದರೆ ನಿಮ್ಮ ಮಾಸಿಕ ಪಿಂಚಣಿ ಮೊತ್ತ ಎಷ್ಟು? (ಗ್ರೂಪ್ ಡಿ / ಎಂಟಿಎಸ್ ಪಿಂಚಣಿದಾರರಿಗೆ ವಿನಾಯಿತಿ ಇದೆ).",
            "te": "రిటైర్ అయితే మీ నెలవారీ పెన్షన్ మొత్తం ఎంత? (గ్రూప్ డి / ఎంటీఎస్ పెన్షనర్లకు మినహాయింపు కలదు).",
        },
    },
    "is_registered_professional": {
        "type": "boolean",
        "prompts": {
            "en": "Are you a professional registered with a statutory body (Doctor, Engineer, Lawyer, Chartered Accountant, Architect)?",
            "hi": "क्या आप किसी वैधानिक निकाय में पंजीकृत पेशेवर हैं (डॉक्टर, इंजीनियर, वकील, सीए, वास्तुकार)?",
            "kn": "ನೀವು ವೃತ್ತಿಪರ ಮಂಡಳಿಯಲ್ಲಿ ನೋಂದಾಯಿತ ವೃತ್ತಿಪರರೇ (ವೈದ್ಯರು, ಇಂಜಿನಿಯರ್, ವಕೀಲರು, ಸಿಎ)?",
            "te": "మీరు చట్టబద్ధమైన మండలిలో నమోదైన వృత్తి నిపుణులా (వైద్యులు, ఇంజనీర్, న్యాయవాది, సిఏ)?",
        },
    },
    "has_willful_bank_default": {
        "type": "boolean",
        "prompts": {
            "en": "Do you have any history of willful loan default with a commercial bank or financial institution?",
            "hi": "क्या आपके पास किसी वाणिज्यिक बैंक या वित्तीय संस्थान में जानबूझकर ऋण न चुकाने (डिफ़ॉल्ट) का इतिहास है?",
            "kn": "ವಾಣಿಜ್ಯ ಬ್ಯಾಂಕ್‌ಗಳಲ್ಲಿ ಉದ್ದೇಶಪೂರ್ವಕ ಸಾಲ ಮರುಪಾವತಿ ಮಾಡದ ಇತಿಹಾಸ ನಿಮ್ಮ ಹೆಸರಿನಲ್ಲಿದೆಯೇ?",
            "te": "వాణిజ్య బ్యాంకులలో ఉద్దేశపూర్వక రుణ ఎగవేత (డిఫాల్ట్) రికార్డు మీ వద్ద ఉందా?",
        },
    },
    "owns_motorized_vehicle": {
        "type": "boolean",
        "prompts": {
            "en": "Does your household own any motorized two, three, or four-wheeler vehicle or mechanized farm equipment?",
            "hi": "क्या आपके परिवार के पास कोई दोपहिया, तिपहिया, चारपहिया मोटर वाहन या मशीनीकृत कृषि उपकरण है?",
            "kn": "ನಿಮ್ಮ ಕುಟುಂಬದ ಬಳಿ ದ್ವಿಚಕ್ರ, ತ್ರಿಚಕ್ರ, ನಾಲ್ಕು ಚಕ್ರದ ವಾಹನ ಅಥವಾ ಯಾಂತ್ರಿಕ ಕೃಷಿ ಉಪಕರಣಗಳಿವೆಯೇ?",
            "te": "మీ కుటుంబానికి ద్విచక్ర, త్రిచక్ర లేదా నాలుగు చక్రాల వాహనం లేదా యాంత్రిక వ్యవసాయ పరికరాలు ఉన్నాయా?",
        },
    },
    "has_regular_govt_job": {
        "type": "boolean",
        "prompts": {
            "en": "Is any member of your household a regular employee of the Central or State government or PSU?",
            "hi": "क्या आपके परिवार का कोई सदस्य केंद्र/राज्य सरकार या सार्वजनिक उपक्रम में नियमित कर्मचारी है?",
            "kn": "ನಿಮ್ಮ ಕುಟುಂಬದ ಯಾವುದೇ ಸದಸ್ಯರು ಕೇಂದ್ರ ಅಥವಾ ರಾಜ್ಯ ಸರ್ಕಾರ/ಸಾರ್ವಜನಿಕ ವಲಯದ ಕಾಯಂ ಉದ್ಯೋಗಿಯೇ?",
            "te": "మీ కుటుంబంలో ఎవరైనా కేంద్ర లేదా రాష్ట్ర ప్రభుత్వంలో లేదా పీఎస్‌యూలో శాశ్వత ఉద్యోగా?",
        },
    },
    "owns_unirrigated_land_gte_5_acres": {
        "type": "boolean",
        "prompts": {
            "en": "Does your household own 5 acres or more of unirrigated land?",
            "hi": "क्या आपके परिवार के पास 5 एकड़ या उससे अधिक असिंचित भूमि है?",
            "kn": "ನಿಮ್ಮ ಕುಟುಂಬದ ಬಳಿ 5 ಎಕರೆ ಅಥವಾ ಅದಕ್ಕಿಂತ ಹೆಚ್ಚಿನ ನೀರಾವರಿ ರಹಿತ (ಖುಷ್ಕಿ) ಭೂಮಿ ಇದೆಯೇ?",
            "te": "మీ కుటుంబానికి 5 ఎకరాలు లేదా అంతకంటే ఎక్కువ సాగునీటి సౌకర్యం లేని (మెట్ట) భూమి ఉందా?",
        },
    },
    "is_enrolled_in_other_pension_nps_esic_epfo": {
        "type": "boolean",
        "prompts": {
            "en": "Are you currently enrolled in any other statutory pension or social security scheme (NPS, ESIC, EPFO, PM-SYM, PM-LVM)?",
            "hi": "क्या आप वर्तमान में किसी अन्य वैधानिक पेंशन या सामाजिक सुरक्षा योजना (NPS, ESIC, EPFO, PM-SYM, PM-LVM) में नामांकित हैं?",
            "kn": "ನೀವು ಪ್ರಸ್ತುತ ಇತರ ಯಾವುದೇ ಶಾಸನಬದ್ಧ ಪಿಂಚಣಿ ಅಥವಾ ಸಾಮಾಜಿಕ ಭದ್ರತಾ ಯೋಜನೆಯಲ್ಲಿ (NPS, ESIC, EPFO, PM-SYM) ನೋಂದಾಯಿಸಿಕೊಂಡಿದ್ದೀರಾ?",
            "te": "మీరు ప్రస్తుతం ఏదైనా ఇతర చట్టబద్ధమైన పెన్షన్ లేదా సామాజిక భద్రతా పథకంలో (NPS, ESIC, EPFO, PM-SYM) నమోదై ఉన్నారా?",
        },
    },
    "gender": {
        "type": "select",
        "prompts": {
            "en": "What is your gender (Female, Male, Other)?",
            "hi": "आपका लिंग क्या है (महिला, पुरुष, अन्य)?",
            "kn": "ನಿಮ್ಮ ಲಿಂಗ ಯಾವುದು (ಮಹಿಳೆ, ಪುರುಷ, ಇತರ)?",
            "te": "మీ లింగం ఏమిటి (మహిళ, పురుషుడు, ఇతరులు)?",
        },
    },
    "is_pregnant_or_lactating": {
        "type": "boolean",
        "prompts": {
            "en": "Are you currently pregnant or a lactating mother?",
            "hi": "क्या आप वर्तमान में गर्भवती महिला अथवा धात्री (स्तनपान कराने वाली) माता हैं?",
            "kn": "ನೀವು ಪ್ರಸ್ತುತ ಗರ್ಭಿಣಿ ಅಥವಾ ಹಾಲುಣಿಸುವ ತಾಯಿಯಾಗಿದ್ದೀರಾ?",
            "te": "మీరు ప్రస్తుతం గర్భిణీ లేదా పాలిచ్చే తల్లా?",
        },
    },
    "has_eshram_or_mgnrega_card": {
        "type": "boolean",
        "prompts": {
            "en": "Do you hold an active e-Shram card or MGNREGA Job Card?",
            "hi": "क्या आपके पास सक्रिय ई-श्रम कार्ड या मनरेगा जॉब कार्ड है?",
            "kn": "ನೀವು ಸಕ್ರಿಯ ಇ-ಶ್ರಮ್ ಕಾರ್ಡ್ ಅಥವಾ ನರೇಗಾ ಜಾಬ್ ಕಾರ್ಡ್ ಹೊಂದಿದ್ದೀರಾ?",
            "te": "మీ వద్ద సక్రియ ఇ-శ్రమ్ కార్డు లేదా ఉపాధి హామీ జాబ్ కార్డు ఉందా?",
        },
    },
    "receives_formal_paid_maternity_benefits": {
        "type": "boolean",
        "prompts": {
            "en": "Do you receive paid maternity leave or benefits under any other statutory law (such as Maternity Benefit Act or ESIC)?",
            "hi": "क्या आप किसी अन्य वैधानिक कानून (जैसे मातृत्व लाभ अधिनियम या ईएसआईसी) के तहत सवैतनिक मातृत्व लाभ प्राप्त कर रही हैं?",
            "kn": "ನೀವು ಯಾವುದೇ ಇತರ ಶಾಸನಬದ್ಧ ಕಾನೂನಿನಡಿಯಲ್ಲಿ (ಉದಾ: ಮಾತೃತ್ವ ಪ್ರಯೋಜನ ಕಾಯ್ದೆ ಅಥವಾ ESIC) ವೇತನ ಸಹಿತ ಮಾತೃತ್ವ ರಜೆ/ಸೌಲಭ್ಯ ಪಡೆಯುತ್ತಿದ್ದೀರಾ?",
            "te": "మీరు ఏదైనా ఇతర చట్టబద్ధమైన చట్టం కింద (ఉదా: ప్రసూతి ప్రయోజన చట్టం లేదా ESIC) వేతనంతో కూడిన ప్రసూతి ప్రయోజనాలను పొందుతున్నారా?",
        },
    },
    "has_water_source_for_irrigation": {
        "type": "boolean",
        "prompts": {
            "en": "Does your agricultural farmland have a functional water source (borewell, open well, tubewell, or stream)?",
            "hi": "क्या आपकी कृषि भूमि पर कोई चालू जल स्रोत (बोरवेल, खुला कुआं, नलकूप, या जलधारा) उपलब्ध है?",
            "kn": "ನಿಮ್ಮ ಕೃಷಿ ಜಮೀನಿನಲ್ಲಿ ಚಾಲ್ತಿಯಲ್ಲಿರುವ ನೀರಿನ ಮೂಲ (ಬೋರ್‌ವೆಲ್, ತೆರೆದ ಬಾವಿ, ಕೊಳವೆಬಾವಿ ಅಥವಾ ಕಾಲುವೆ) ಇದೆಯೇ?",
            "te": "మీ వ్యవసాయ భూమిలో పని చేసే నీటి వనరు (బోరుబావి, బావి, గొట్టపుబావి లేదా వాగు) ఉందా?",
        },
    },
    "has_existing_grid_connected_agri_pump": {
        "type": "boolean",
        "prompts": {
            "en": "Does your farmland already have an active grid-connected electric pump connection?",
            "hi": "क्या आपकी कृषि भूमि पर पहले से ही ग्रिड से जुड़ा बिजली पंप कनेक्शन मौजूद है?",
            "kn": "ನಿಮ್ಮ ಕೃಷಿ ಜಮೀನಿನಲ್ಲಿ ಈಗಾಗಲೇ ವಿದ್ಯುತ್ ಗ್ರಿಡ್ ಸಂಪರ್ಕ ಹೊಂದಿರುವ ಪಂಪ್‌ಸೆಟ್ ಇದೆಯೇ?",
            "te": "మీ వ్యవసాయ భూమికి ఇప్పటికే విద్యుత్ గ్రిడ్ అనుసంధాన పంపు కనెక్షన్ ఉందా?",
        },
    },
    "availed_solar_pump_subsidy_in_past_5_years": {
        "type": "boolean",
        "prompts": {
            "en": "Have you or your household availed a government subsidy for a solar agriculture pump in the past 5 years?",
            "hi": "क्या आपने या आपके परिवार ने पिछले 5 वर्षों में सौर कृषि पंप के लिए कोई सरकारी सब्सिडी प्राप्त की है?",
            "kn": "ನೀವು ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬವು ಕಳೆದ 5 ವರ್ಷಗಳಲ್ಲಿ ಸೌರ ಕೃಷಿ ಪಂಪ್‌ಗಾಗಿ ಯಾವುದೇ ಸರ್ಕಾರಿ ಸಬ್ಸಿಡಿ ಪಡೆದಿದ್ದೀರಾ?",
            "te": "మీరు లేదా మీ కుటుంబం గత 5 సంవత్సరాలలో సోలార్ వ్యవసాయ పంపు కోసం ఏదైనా ప్రభుత్వ సబ్సిడీని పొందారా?",
        },
    },
    "is_enrolled_in_pm_sym_or_pm_lvm": {
        "type": "boolean",
        "prompts": {
            "en": "Are you currently enrolled in Pradhan Mantri Shram Yogi Maandhan (PM-SYM) or Pradhan Mantri Laghu Vyapari Maandhan (PM-LVM)?",
            "hi": "क्या आप वर्तमान में प्रधानमंत्री श्रम योगी मानधन (PM-SYM) या प्रधानमंत्री लघु व्यापारी मानधन (PM-LVM) में पंजीकृत हैं?",
            "kn": "ನೀವು ಪ್ರಸ್ತುತ ಪ್ರಧಾನ ಮಂತ್ರಿ ಶ್ರಮ ಯೋಗಿ ಮಾನ್‌ಧನ್ (PM-SYM) ಅಥವಾ ಪ್ರಧಾನ ಮಂತ್ರಿ ಲಘು ವ್ಯಾಪಾರಿ ಮಾನ್‌ಧನ್ (PM-LVM) ಯೋಜನೆಯಲ್ಲಿ ನೋಂದಾಯಿಸಿಕೊಂಡಿದ್ದೀರಾ?",
            "te": "మీరు ప్రస్తుతం ప్రధాన మంత్రి శ్రమ యోగి మాన్‌ధన్ (PM-SYM) లేదా ప్రధాన మంత్రి లఘు వ్యాపారి మాన్‌ధన్ (PM-LVM) లో చేరి ఉన్నారా?",
        },
    },
    "is_constitutional_post_holder_or_elected_representative": {
        "type": "boolean",
        "prompts": {
            "en": "Are you or any family member a former or present holder of a constitutional post, Minister, MP, MLA, MLC, Mayor, or District Panchayat Chairperson?",
            "hi": "क्या आप या आपके परिवार का कोई सदस्य पूर्व या वर्तमान संवैधानिक पद धारक, मंत्री, सांसद, विधायक, एमएलसी, नगर निगम मेयर या जिला पंचायत अध्यक्ष हैं?",
            "kn": "ನೀವು ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬದ ಯಾವುದೇ ಸದಸ್ಯರು ಮಾಜಿ ಅಥವಾ ಹಾಲಿ ಸಾಂವಿಧಾನಿಕ ಹುದ್ದೆ ಹೊಂದಿದವರೇ, ಸಚಿವರು, ಸಂಸದರು, ಶಾಸಕರು, ಎಂಎಲ್‌ಸಿ, ಮೇಯರ್ ಅಥವಾ ಜಿಲ್ಲಾ ಪಂಚಾಯತ್ ಅಧ್ಯಕ್ಷರೇ?",
            "te": "మీరు లేదా మీ కుటుంబంలో ఎవరైనా మాజీ లేదా ప్రస్తుత రాజ్యాంగ పదవిని నిర్వహించినవారా, మంత్రులు, ఎంపీలు, ఎమ్మెల్యేలు, ఎమ్మెల్సీలు, మేయర్లు లేదా జిల్లా పరిషత్ చైర్మన్లా?",
        },
    },
    "is_mts_or_class_iv_or_group_d_employee": {
        "type": "boolean",
        "prompts": {
            "en": "Are you employed as Multi-Tasking Staff (MTS), Class IV, or Group D staff?",
            "hi": "क्या आप मल्टी-टास्किंग स्टाफ (MTS), चतुर्थ श्रेणी (Class IV), या ग्रुप डी कर्मचारी हैं?",
            "kn": "ನೀವು ಮಲ್ಟಿ-ಟಾಸ್ಕಿಂಗ್ ಸಿಬ್ಬಂದಿ (MTS), ವರ್ಗ IV, ಅಥವಾ ಗ್ರೂಪ್ ಡಿ ಉದ್ಯೋಗಿಯಾಗಿದ್ದೀರಾ?",
            "te": "మీరు మల్టీ-టాస్కింగ్ స్టాఫ్ (MTS), క్లాస్ IV, లేదా గ్రూప్ డి ఉద్యోగిగా పనిచేస్తున్నారా?",
        },
    },
    "is_bank_defaulter": {
        "type": "boolean",
        "prompts": {
            "en": "Do you have any existing unresolved default on a bank loan?",
            "hi": "क्या आपके पास किसी बैंक ऋण पर कोई मौजूदा बकाया डिफॉल्ट है?",
            "kn": "ನೀವು ಯಾವುದೇ ಬ್ಯಾಂಕ್ ಸಾಲದಲ್ಲಿ ಸುಸ್ತಿದಾರರಾಗಿದ್ದೀರಾ?",
            "te": "మీకు ఏదైనా బ్యాంకు రుణంపై బకాయి డిఫాల్ట్ ఉందా?",
        },
    },
    "is_tenant_farmer": {
        "type": "boolean",
        "prompts": {
            "en": "Do you cultivate agricultural land as a tenant, sharecropper, or oral lessee?",
            "hi": "क्या आप बटाईदार, पट्टेदार या किरायेदार के रूप में कृषि भूमि पर खेती करते हैं?",
            "kn": "ನೀವು ಗೇಣಿದಾರರು ಅಥವಾ ಪಾಲುದಾರರಾಗಿ ಕೃಷಿ ಭೂಮಿಯಲ್ಲಿ ಸಾಗುವಳಿ ಮಾಡುತ್ತಿದ್ದೀರಾ?",
            "te": "మీరు కౌలు రైతుగా లేదా వాటాదారుగా వ్యవసాయ భూమిని సాగు చేస్తున్నారా?",
        },
    },
    "is_allied_activity_worker": {
        "type": "boolean",
        "prompts": {
            "en": "Are you engaged in animal husbandry, dairy, poultry, or fisheries activities?",
            "hi": "क्या आप पशुपालन, डेयरी, मुर्गीपालन या मत्स्य पालन गतिविधियों में संलग्न हैं?",
            "kn": "ನೀವು ಪಶುಸಂಗೋಪನೆ, ಡೈರಿ, ಕೋಳಿ ಸಾಕಣೆ ಅಥವಾ ಮೀನುಗಾರಿಕೆ ಚಟುವಟಿಕೆಗಳಲ್ಲಿ ತೊಡಗಿದ್ದೀರಾ?",
            "te": "మీరు పశుసంవర్ధక, పాడి, పౌల్ట్రీ లేదా మత్స్య సంబంధిత కార్యకలాపాలలో నిమగ్నమై ఉన్నారా?",
        },
    },
    "has_savings_account": {
        "type": "boolean",
        "prompts": {
            "en": "Do you hold an active savings bank account with a passbook for direct benefit transfers (DBT)?",
            "hi": "क्या आपके पास प्रत्यक्ष लाभ अंतरण (DBT) के लिए पासबुक सहित सक्रिय बचत बैंक खाता है?",
            "kn": "ನೇರ ಲಾಭ ವರ್ಗಾವಣೆಗಾಗಿ (ಡಿಬಿಟಿ) ನಿಮ್ಮ ಬಳಿ ಪಾಸ್‌ಬುಕ್ ಹೊಂದಿರುವ ಸಕ್ರಿಯ ಉಳಿತಾಯ ಬ್ಯಾಂಕ್ ಖಾತೆ ಇದೆಯೇ?",
            "te": "ప్రత్యక్ష నగదు బదిలీ (DBT) కోసం మీ వద్ద పాస్‌బుక్‌తో కూడిన సక్రియ సేవింగ్స్ బ్యాంక్ ఖాతా ఉందా?",
        },
    },
    "has_basic_savings_bank_account": {
        "type": "boolean",
        "prompts": {
            "en": "Do you hold an active basic savings bank deposit (BSBD) account with a commercial bank?",
            "hi": "क्या आपके पास किसी वाणिज्यिक बैंक में सक्रिय मूल बचत बैंक जमा (BSBD) खाता है?",
            "kn": "ವಾಣಿಜ್ಯ ಬ್ಯಾಂಕ್‌ನಲ್ಲಿ ನಿಮ್ಮ ಬಳಿ ಸಕ್ರಿಯ ಮೂಲ ಉಳಿತಾಯ ಬ್ಯಾಂಕ್ ಠೇವಣಿ ಖಾತೆ ಇದೆಯೇ?",
            "te": "వాణిజ్య బ్యాంకులో మీ వద్ద సక్రియ బేసిక్ సేవింగ్స్ బ్యాంక్ డిపాజిట్ ఖాతా ఉందా?",
        },
    },
    "has_bank_passbook": {
        "type": "boolean",
        "prompts": {
            "en": "Do you possess an active bank account passbook with IFSC code and Aadhaar linkage?",
            "hi": "क्या आपके पास आईएफएससी कोड और आधार लिंकेज वाली सक्रिय बैंक खाता पासबुक है?",
            "kn": "ಐಎಫ್‌ಎಸ್‌ಸಿ ಕೋಡ್ ಮತ್ತು ಆಧಾರ್ ಲಿಂಕ್ ಆಗಿರುವ ಸಕ್ರಿಯ ಬ್ಯಾಂಕ್ ಪಾಸ್‌ಬುಕ್ ನಿಮ್ಮ ಬಳಿ ಇದೆಯೇ?",
            "te": "IFSC కోడ్ మరియు ఆధార్ అనుసంధానంతో ఉన్న సక్రియ బ్యాంక్ పాస్‌బుక్ మీ వద్ద ఉందా?",
        },
    },
    "social_category": {
        "type": "select",
        "prompts": {
            "en": "What is your social / reservation category (General, OBC, SC, ST)?",
            "hi": "आपकी सामाजिक/आरक्षण श्रेणी क्या है (सामान्य, ओबीसी, एससी, एसटी)?",
            "kn": "ನಿಮ್ಮ ಸಾಮಾಜಿಕ ಅಥವಾ ಮೀಸಲಾತಿ ವರ್ಗ ಯಾವುದು (ಜನರಲ್, ಒಬಿಸಿ, ಎಸ್‌ಸಿ, ಎಸ್‌ಟಿ)?",
            "te": "మీ సామాజಿಕ లేదా రిజర్వేషన్ వర్గం ఏమిటి (జనరల్, ఓబీసీ, ఎస్సీ, ఎస్టీ)?",
        },
    },
    "is_differently_abled": {
        "type": "boolean",
        "prompts": {
            "en": "Are you a person with benchmark disability (differently abled / Divyangjan)?",
            "hi": "क्या आप दिव्यांगजन (विशेष रूप से सक्षम) हैं?",
            "kn": "ನೀವು ವಿಶೇಷ ಚೇತನರೇ (ಅಂಗವಿಕಲತೆ ಹೊಂದಿರುವವರೇ)?",
            "te": "మీరు దివ్యాంగులా (ప్రత్యేక ప్రతిభావంతులా)?",
        },
    },
    "anc_checkups_completed": {
        "type": "number",
        "prompts": {
            "en": "How many Antenatal Check-ups (ANC) have you completed during this pregnancy?",
            "hi": "इस गर्भावस्था के दौरान आपने कितनी प्रसव पूर्व जांचें (ANC) पूरी की हैं?",
            "kn": "ಈ ಗರ್ಭಧಾರಣೆಯ ಸಮಯದಲ್ಲಿ ನೀವು ಎಷ್ಟು ಪ್ರಸವಪೂರ್ವ ತಪಾಸಣೆಗಳನ್ನು (ANC) ಪೂರ್ಣಗೊಳಿಸಿದ್ದೀರಿ?",
            "te": "ఈ గర్భధారణ సమయంలో మీరు ఎన్ని ప్రసవ పూర్వ తనిఖీలను (ANC) పూర్తి చేశారు?",
        },
    },
    "date_of_birth": {
        "type": "string",
        "prompts": {
            "en": "Please provide your date of birth (YYYY-MM-DD).",
            "hi": "कृपया अपनी जन्म तिथि (YYYY-MM-DD) बताएं।",
            "kn": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಜನ್ಮ ದಿನಾಂಕವನ್ನು ನಮೂದಿಸಿ (YYYY-MM-DD).",
            "te": "దయచేసి మీ పుట్టిన తేదీని నమోదు చేయండి (YYYY-MM-DD).",
        },
    },
}


def _normalize_bool(val: Any) -> Optional[bool]:
    """Safely converts boolean-like values to bool without eval/exec."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("true", "yes", "1", "y", "t"):
            return True
        if v in ("false", "no", "0", "n", "f"):
            return False
    return None


def _to_float(val: Any) -> Optional[float]:
    """Safely converts numeric values to float."""
    try:
        if isinstance(val, bool):
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def evaluate_atomic_operator(op: str, target: Any, citizen: Any) -> bool:
    """
    Deterministic evaluation of standard operators.
    Zero eval/exec, zero external calls, completely safe.
    """
    norm_op = OPERATOR_MAP.get(op.lower().strip())
    if not norm_op:
        raise UnsupportedOperatorException(f"Unsupported rule operator '{op}'.")

    # 1. equals
    if norm_op == "equals":
        # Boolean comparison
        c_bool = _normalize_bool(citizen)
        t_bool = _normalize_bool(target)
        if c_bool is not None and t_bool is not None:
            return c_bool == t_bool

        # Numeric comparison
        c_num = _to_float(citizen)
        t_num = _to_float(target)
        if c_num is not None and t_num is not None:
            return math.isclose(c_num, t_num, rel_tol=1e-9)

        # String comparison (case-insensitive)
        return str(citizen).strip().lower() == str(target).strip().lower()

    # 2. not_equals
    if norm_op == "not_equals":
        return not evaluate_atomic_operator("equals", target, citizen)

    # 3. in
    if norm_op == "in":
        target_list = target if isinstance(target, (list, tuple, set)) else [target]
        for item in target_list:
            if evaluate_atomic_operator("equals", item, citizen):
                return True
        return False

    # 4. not_in
    if norm_op == "not_in":
        return not evaluate_atomic_operator("in", target, citizen)

    # Numeric comparisons
    c_num = _to_float(citizen)
    t_num = _to_float(target)
    if c_num is None or t_num is None:
        return False

    if norm_op == "greater_than":
        return c_num > t_num and not math.isclose(c_num, t_num, abs_tol=1e-5)
    if norm_op == "less_than":
        return c_num < t_num and not math.isclose(c_num, t_num, abs_tol=1e-5)
    if norm_op == "greater_than_or_equal":
        return c_num >= t_num or math.isclose(c_num, t_num, abs_tol=1e-5)
    if norm_op == "less_than_or_equal":
        return c_num <= t_num or math.isclose(c_num, t_num, abs_tol=1e-5)

    raise UnsupportedOperatorException(f"Operator '{op}' logic could not be executed.")


FIELD_HUMAN_LABELS: Dict[str, Dict[str, str]] = {
    "has_savings_account": {
        "en": "Active Savings Bank Account with Passbook",
        "hi": "पासबुक सहित सक्रिय बचत बैंक खाता",
        "kn": "ಪಾಸ್‌ಬುಕ್ ಹೊಂದಿರುವ ಸಕ್ರಿಯ ಉಳಿತಾಯ ಬ್ಯಾಂಕ್ ಖಾತೆ",
        "te": "పాస్‌బుక్‌తో కూడిన సక్రియ సేవింగ్స్ బ్యాంక్ ఖాతా",
    },
    "has_basic_savings_bank_account": {
        "en": "Commercial Basic Savings Bank Deposit Account",
        "hi": "वाणिज्यिक मूल बचत बैंक खाता",
        "kn": "ವಾಣಿಜ್ಯ ಮೂಲ ಉಳಿತಾಯ ಬ್ಯಾಂಕ್ ಖಾತೆ",
        "te": "వాణిజ్య మూల సేవింగ్స్ బ్యాంక్ ఖాతా",
    },
    "has_bank_passbook": {
        "en": "Bank Account Passbook for Direct Benefit Transfer",
        "hi": "डीबीटी हेतु बैंक खाता एवं पासबुक",
        "kn": "ನೇರ ಲಾಭ ವರ್ಗಾವಣೆಗಾಗಿ ಬ್ಯಾಂಕ್ ಪಾಸ್‌ಬುಕ್",
        "te": "ప్రత్యక్ష బదిలీ కోసం బ్యాంక్ పాస్‌బుక్",
    },
    "is_bank_defaulter": {
        "en": "Bank Loan Default Status",
        "hi": "बैंक ऋण डिफ़ॉल्ट स्थिति",
        "kn": "ಬ್ಯಾಂಕ್ ಸಾಲ ಸುಸ್ತಿದಾರ ಸ್ಥಿತಿ",
        "te": "బ్యాంక్ రుణ డిఫాల్ట్ స్థితి",
    },
    "has_willful_bank_default": {
        "en": "Bank Default Record",
        "hi": "बैंक डिफ़ॉल्ट रिकॉर्ड",
        "kn": "ಬ್ಯಾಂಕ್ ಸುಸ್ತಿದಾರ ದಾಖಲೆ",
        "te": "బ్యాంక్ డిఫాల్ట్ రికార్డు",
    },
    "social_category": {
        "en": "Social Reservation Category",
        "hi": "सामाजिक आरक्षण श्रेणी",
        "kn": "ಸಾಮಾಜಿಕ ಮೀಸಲಾತಿ ವರ್ಗ",
        "te": "సామాజిక రిజర్వేషన్ వర్గం",
    },
    "is_differently_abled": {
        "en": "Benchmark Disability / Divyangjan Status",
        "hi": "दिव्यांगता / दिव्यांगजन स्थिति",
        "kn": "ಅಂಗವಿಕಲತೆ / ವಿಶೇಷ ಚೇತನರ ಸ್ಥಿತಿ",
        "te": "దివ్యాంగుల / వికలాంగుల స్థితి",
    },
    "owns_pucca_house": {
        "en": "Permanent Concrete (Pucca) House Ownership",
        "hi": "पक्का (कंक्रीट) मकान स्वामित्व",
        "kn": "ಪಕ್ಕಾ (ಕಾಂಕ್ರೀಟ್) ಮನೆ ಮಾಲೀಕತ್ವ",
        "te": "పక్కా (కాంక్రీట్) ఇల్లు యాజమాన్యం",
    },
    "pays_income_tax": {
        "en": "Income Tax Payment Status",
        "hi": "आयकर भुगतान स्थिति",
        "kn": "ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿ ಸ್ಥಿತಿ",
        "te": "ఆదాయపు పన్ను చెల్లింపు స్థితి",
    },
    "is_regular_govt_employee": {
        "en": "Regular Government Employment Status",
        "hi": "नियमित सरकारी नौकरी स्थिति",
        "kn": "ಕಾಯಂ ಸರ್ಕಾರಿ ಉದ್ಯೋಗ ಸ್ಥಿತಿ",
        "te": "శాశ్వత ప్రభుత్వ ఉద్యోగ స్థితి",
    },
    "has_regular_govt_job": {
        "en": "Regular Government Employment Status",
        "hi": "नियमित सरकारी नौकरी स्थिति",
        "kn": "ಕಾಯಂ ಸರ್ಕಾರಿ ಉದ್ಯೋಗ ಸ್ಥಿತಿ",
        "te": "శాశ్వత ప్రభుత్వ ఉద్యోగ స్థితి",
    },
    "owns_agricultural_land": {
        "en": "Cultivable Agricultural Land Ownership",
        "hi": "कृषि योग्य भूमि स्वामित्व",
        "kn": "ಕೃಷಿ ಯೋಗ್ಯ ಭೂಮಿ ಮಾಲೀಕತ್ವ",
        "te": "సాగు భూమి యాజమాన్యం",
    },
    "is_tenant_farmer": {
        "en": "Tenant Cultivator / Sharecropper Status",
        "hi": "बटाईदार / पट्टेदार किसान स्थिति",
        "kn": "ಗೇಣಿದಾರ / ಪಾಲುದಾರ ರೈತ ಸ್ಥಿತಿ",
        "te": "కౌలు రైతు / వాటాదారు స్థితి",
    },
    "landholding_hectares": {
        "en": "Agricultural Landholding Area",
        "hi": "कृषि भूमि का क्षेत्रफल",
        "kn": "ಕೃಷಿ ಭೂಮಿಯ ವಿಸ್ತೀರ್ಣ",
        "te": "వ్యవసాయ భూమి విస్తీర్ణం",
    },
}


def _generate_satisfaction_reason(
    field: str,
    operator: str,
    target_val: Any,
    citizen_val: Any,
    is_exclusion: bool = False
) -> Dict[str, str]:
    """Generates natural multilingual satisfaction explanations."""
    labels = FIELD_HUMAN_LABELS.get(field)
    en_label = labels["en"] if labels else field.replace("_", " ").title()
    hi_label = labels["hi"] if labels else en_label
    kn_label = labels["kn"] if labels else en_label
    te_label = labels["te"] if labels else en_label

    if is_exclusion:
        return {
            "en": f"Cleared statutory exclusion: {en_label}.",
            "hi": f"वैधानिक अपवर्जन उत्तीर्ण: {hi_label}।",
            "kn": f"ಶಾಸನಬದ್ಧ ವಿನಾಯಿತಿ ದೃಢೀಕರಿಸಲಾಗಿದೆ: {kn_label}.",
            "te": f"చట్టబద్ధమైన మినహాయింపు ధృవీకరించబడింది: {te_label}.",
        }

    return {
        "en": f"Verified condition for {en_label} (provided: {citizen_val}).",
        "hi": f"{hi_label} की शर्त सत्यापित (प्रदत्त: {citizen_val})।",
        "kn": f"{kn_label} ಷರತ್ತು ದೃಢೀಕರಿಸಲಾಗಿದೆ (ನೀಡಿದ ವಿವರ: {citizen_val}).",
        "te": f"{te_label} నిబంధన ధృవీకరించబడింది (అందించిన సమాచారం: {citizen_val}).",
    }


def _get_missing_field_prompt(field: str) -> Tuple[Dict[str, str], str]:
    """Returns conversational prompts in all 4 languages for a missing field."""
    if field in FIELD_PROMPTS:
        return FIELD_PROMPTS[field]["prompts"], FIELD_PROMPTS[field]["type"]

    # Fallback prompt for dynamic/unregistered fields
    clean_name = field.replace("_", " ").title()
    fallback_prompts = {
        "en": f"Please provide information regarding your {clean_name}.",
        "hi": f"कृपया अपने {clean_name} के संबंध में जानकारी प्रदान करें।",
        "kn": f"ದಯವಿಟ್ಟು ನಿಮ್ಮ {clean_name} ಕುರಿತು ವಿವರಗಳನ್ನು ಒದಗಿಸಿ.",
        "te": f"దయచేసి మీ {clean_name} గురించి వివరాలను అందించండి.",
    }
    return fallback_prompts, "string"


class DeterministicRuleEvaluator:
    """
    Deterministic Rule Evaluator for Government Welfare Schemes.
    Evaluates declarative JSON condition ASTs using Three-Valued Logic.
    
    Guarantees:
    - Zero eval/exec execution.
    - Zero LLM dependency.
    - Zero inference of missing citizen attributes.
    - Preserves clause-level citations.
    - Provides authentic 4-language explanations (en, hi, kn, te).
    """

    @classmethod
    def evaluate_condition_item(
        cls,
        cond: Dict[str, Any],
        citizen_attributes: Dict[str, Any],
        is_exclusion: bool = False,
    ) -> Tuple[ConditionStatusEnum, EvaluatedCondition, Optional[MissingFieldInfo]]:
        """
        Evaluates a single condition dictionary against citizen attributes.
        Returns:
            (status, EvaluatedCondition, MissingFieldInfo or None)
        """
        # Validate AST structure
        if not isinstance(cond, dict):
            raise MalformedRuleException(f"Condition entry must be a dictionary, got {type(cond).__name__}")

        cond_id = str(cond.get("id") or "cond_unknown")
        field = cond.get("field")
        op = cond.get("operator")
        target_val = cond.get("value")

        if not field or not op:
            raise MalformedRuleException(f"Condition '{cond_id}' is missing required 'field' or 'operator'.")

        citation = cond.get("citation")
        raw_failure_reason = cond.get("failure_reason") or {}
        if isinstance(raw_failure_reason, str):
            failure_reason = {
                "en": raw_failure_reason,
                "hi": raw_failure_reason,
                "kn": raw_failure_reason,
                "te": raw_failure_reason,
            }
        elif isinstance(raw_failure_reason, dict):
            failure_reason = raw_failure_reason
        else:
            failure_reason = {}

        # 1. Check if citizen provided this attribute (or can be derived from date_of_birth)
        if field == "age" and (field not in citizen_attributes or citizen_attributes[field] is None) and "date_of_birth" in citizen_attributes:
            from datetime import date
            try:
                dob = date.fromisoformat(str(citizen_attributes["date_of_birth"]).strip())
                today = date.today()
                months = (today.year - dob.year) * 12 + (today.month - dob.month)
                if today.day < dob.day:
                    months -= 1
                citizen_attributes = dict(citizen_attributes)
                citizen_attributes["age"] = round(months / 12.0, 4)
            except Exception:
                pass

        if field == "owns_agricultural_land" and (field not in citizen_attributes or citizen_attributes[field] is None):
            if citizen_attributes.get("landholding_hectares") is not None and float(citizen_attributes["landholding_hectares"]) > 0:
                citizen_attributes = dict(citizen_attributes)
                citizen_attributes["owns_agricultural_land"] = True
            elif str(citizen_attributes.get("farmer_type", "")).lower() in ("landowner", "owner", "owner_cultivator"):
                citizen_attributes = dict(citizen_attributes)
                citizen_attributes["owns_agricultural_land"] = True

        if field == "is_tenant_farmer" and (field not in citizen_attributes or citizen_attributes[field] is None):
            if str(citizen_attributes.get("farmer_type", "")).lower() in ("tenant", "tenant_farmer", "sharecropper", "oral_lessee"):
                citizen_attributes = dict(citizen_attributes)
                citizen_attributes["is_tenant_farmer"] = True

        if field == "is_allied_activity_worker" and (field not in citizen_attributes or citizen_attributes[field] is None):
            occ = str(citizen_attributes.get("occupation", "")).lower()
            ft = str(citizen_attributes.get("farmer_type", "")).lower()
            if any(w in occ or w in ft for w in ["dairy", "fisher", "poultry", "animal", "husbandry", "livestock"]):
                citizen_attributes = dict(citizen_attributes)
                citizen_attributes["is_allied_activity_worker"] = True

        if field not in citizen_attributes or citizen_attributes[field] is None:
            prompt_dict, expected_type = _get_missing_field_prompt(field)
            missing_info = MissingFieldInfo(
                field=field,
                prompt=prompt_dict,
                expected_type=expected_type,
                citation=citation,
            )
            evaluated = EvaluatedCondition(
                condition_id=cond_id,
                field=field,
                operator=op,
                target_value=target_val,
                citizen_value=None,
                status=ConditionStatusEnum.UNKNOWN,
                reason={
                    "en": f"Information for '{field}' was not provided.",
                    "hi": f"'{field}' के लिए जानकारी प्रदान नहीं की गई।",
                    "kn": f"'{field}' ಕುರಿತು ಮಾಹಿತಿಯನ್ನು ಒದಗಿಸಲಾಗಿಲ್ಲ.",
                    "te": f"'{field}' కొరకు సమాచారం అందించబడలేదు.",
                },
                citation=citation,
            )
            return ConditionStatusEnum.UNKNOWN, evaluated, missing_info

        # 2. Citizen provided the attribute — evaluate operator
        citizen_val = citizen_attributes[field]
        is_satisfied = evaluate_atomic_operator(op, target_val, citizen_val)

        # Check if an explicit statutory exemption condition applies (e.g. MTS / Class IV staff exception)
        except_if = cond.get("except_if")
        is_exempt = False
        if is_satisfied and except_if and isinstance(except_if, dict):
            ex_field = except_if.get("field")
            ex_op = except_if.get("operator")
            ex_target = except_if.get("value")
            if ex_field in citizen_attributes and citizen_attributes[ex_field] is not None:
                if evaluate_atomic_operator(ex_op, ex_target, citizen_attributes[ex_field]):
                    is_exempt = True
                    is_satisfied = False  # Exemption applies; exclusion not triggered

        if is_exclusion:
            # For exclusions (none_of):
            # If the atomic condition IS satisfied, citizen triggered the exclusion -> ELIGIBILITY FAILED!
            # If atomic condition is NOT satisfied, citizen cleared the exclusion -> ELIGIBILITY SATISFIED!
            if is_satisfied:
                evaluated = EvaluatedCondition(
                    condition_id=cond_id,
                    field=field,
                    operator=op,
                    target_value=target_val,
                    citizen_value=citizen_val,
                    status=ConditionStatusEnum.FAILED,
                    reason=failure_reason or {
                        "en": f"Exclusion triggered: '{field}' matches exclusion criterion.",
                        "hi": f"अपवर्जन लागू: '{field}' बहिष्करण मानदंड से मेल खाता है।",
                        "kn": f"ಹೊರಗಿಡುವಿಕೆ ಅನ್ವಯವಾಗಿದೆ: '{field}' ಹೊರಗಿಡುವ ಮಾನದಂಡಕ್ಕೆ ಹೊಂದಾಣಿಕೆಯಾಗಿದೆ.",
                        "te": f"మినహాయింపు వర్తించింది: '{field}' మినహాయింపు ప్రమాణానికి సరిపోలింది.",
                    },
                    citation=citation,
                )
                return ConditionStatusEnum.FAILED, evaluated, None
            else:
                if is_exempt:
                    satisfaction_reason = {
                        "en": f"Exclusion for '{field}' waived: statutory exemption applies (Multi-Tasking Staff / Class IV / Group D).",
                        "hi": f"'{field}' के लिए बहिष्करण लागू नहीं: वैधानिक छूट लागू होती है (मल्टी-टास्किंग स्टाफ / चतुर्थ श्रेणी)।",
                        "kn": f"'{field}' ಹೊರಗಿಡುವಿಕೆಗೆ ಶಾಸನಬದ್ಧ ವಿನಾಯಿತಿ ಅನ್ವಯಿಸುತ್ತದೆ (ಮಲ್ಟಿ-ಟಾಸ್ಕಿಂಗ್ ಸಿಬ್ಬಂದಿ / ವರ್ಗ IV).",
                        "te": f"'{field}' మినహాయింపుకు చట్టబద్ధమైన సడలింపు వర్తిస్తుంది (మల్టీ-టాస్కింగ్ స్టాఫ్ / క్లాస్ IV).",
                    }
                else:
                    satisfaction_reason = _generate_satisfaction_reason(field, op, target_val, citizen_val, is_exclusion=True)
                evaluated = EvaluatedCondition(
                    condition_id=cond_id,
                    field=field,
                    operator=op,
                    target_value=target_val,
                    citizen_value=citizen_val,
                    status=ConditionStatusEnum.SATISFIED,
                    reason=satisfaction_reason,
                    citation=citation,
                )
                return ConditionStatusEnum.SATISFIED, evaluated, None
        else:
            # Standard requirement (all_of / any_of)
            if is_satisfied:
                evaluated = EvaluatedCondition(
                    condition_id=cond_id,
                    field=field,
                    operator=op,
                    target_value=target_val,
                    citizen_value=citizen_val,
                    status=ConditionStatusEnum.SATISFIED,
                    reason=_generate_satisfaction_reason(field, op, target_val, citizen_val, is_exclusion=False),
                    citation=citation,
                )
                return ConditionStatusEnum.SATISFIED, evaluated, None
            else:
                evaluated = EvaluatedCondition(
                    condition_id=cond_id,
                    field=field,
                    operator=op,
                    target_value=target_val,
                    citizen_value=citizen_val,
                    status=ConditionStatusEnum.FAILED,
                    reason=failure_reason or {
                        "en": f"Criterion for '{field}' was not met.",
                        "hi": f"'{field}' के लिए मानदंड पूरा नहीं हुआ।",
                        "kn": f"'{field}' ಮಾನದಂಡವು ಪೂರೈಸಲ್ಪಟ್ಟಿಲ್ಲ.",
                        "te": f"'{field}' ప్రమాణం పూర్తి కాలేదు.",
                    },
                    citation=citation,
                )
                return ConditionStatusEnum.FAILED, evaluated, None

    @classmethod
    def evaluate_scheme(
        cls,
        scheme_id: str,
        scheme_name: Dict[str, str],
        rule_ast: Dict[str, Any],
        citizen_attributes: Dict[str, Any],
    ) -> SchemeEligibilityResult:
        """
        Evaluates a scheme's rule AST against a citizen profile.
        Returns a SchemeEligibilityResult with ELIGIBLE, NOT_ELIGIBLE, or POSSIBLY_ELIGIBLE.
        """
        if not isinstance(rule_ast, dict):
            raise MalformedRuleException(f"Rule AST must be a dict, got {type(rule_ast).__name__}")

        conditions_root = rule_ast.get("conditions") if "conditions" in rule_ast else rule_ast
        if not isinstance(conditions_root, dict):
            raise MalformedRuleException("Rule AST missing 'conditions' object.")

        all_of_list = conditions_root.get("all_of") or []
        any_of_list = conditions_root.get("any_of") or []
        none_of_list = conditions_root.get("none_of") or []

        if not isinstance(all_of_list, list) or not isinstance(any_of_list, list) or not isinstance(none_of_list, list):
            raise MalformedRuleException("all_of, any_of, and none_of entries must be lists.")

        conditions_satisfied: List[EvaluatedCondition] = []
        conditions_failed: List[EvaluatedCondition] = []
        missing_info_map: Dict[str, MissingFieldInfo] = {}
        citations: List[Dict[str, Any]] = []

        all_of_statuses: List[ConditionStatusEnum] = []
        any_of_statuses: List[ConditionStatusEnum] = []
        none_of_statuses: List[ConditionStatusEnum] = []

        # 1. Evaluate all_of (mandatory requirements)
        for cond in all_of_list:
            status, eval_cond, missing = cls.evaluate_condition_item(cond, citizen_attributes, is_exclusion=False)
            all_of_statuses.append(status)
            if status == ConditionStatusEnum.SATISFIED:
                conditions_satisfied.append(eval_cond)
            elif status == ConditionStatusEnum.FAILED:
                conditions_failed.append(eval_cond)
            elif status == ConditionStatusEnum.UNKNOWN:
                if missing and missing.field not in missing_info_map:
                    missing_info_map[missing.field] = missing

            if eval_cond.citation:
                citations.append(eval_cond.citation)

        # 2. Evaluate any_of (alternative paths)
        for cond in any_of_list:
            status, eval_cond, missing = cls.evaluate_condition_item(cond, citizen_attributes, is_exclusion=False)
            any_of_statuses.append(status)
            if status == ConditionStatusEnum.SATISFIED:
                conditions_satisfied.append(eval_cond)
            elif status == ConditionStatusEnum.FAILED:
                conditions_failed.append(eval_cond)
            elif status == ConditionStatusEnum.UNKNOWN:
                if missing and missing.field not in missing_info_map:
                    missing_info_map[missing.field] = missing

            if eval_cond.citation:
                citations.append(eval_cond.citation)

        # 3. Evaluate none_of (statutory exclusions)
        for cond in none_of_list:
            status, eval_cond, missing = cls.evaluate_condition_item(cond, citizen_attributes, is_exclusion=True)
            none_of_statuses.append(status)
            if status == ConditionStatusEnum.SATISFIED:
                # Exclusion cleared
                conditions_satisfied.append(eval_cond)
            elif status == ConditionStatusEnum.FAILED:
                # Exclusion triggered -> failure!
                conditions_failed.append(eval_cond)
            elif status == ConditionStatusEnum.UNKNOWN:
                if missing and missing.field not in missing_info_map:
                    missing_info_map[missing.field] = missing

            if eval_cond.citation:
                citations.append(eval_cond.citation)

        # --- THREE-VALUED EVALUATION COMBINATOR LOGIC ---
        # A. Evaluate all_of
        if not all_of_statuses:
            all_of_outcome = ConditionStatusEnum.SATISFIED
        elif ConditionStatusEnum.FAILED in all_of_statuses:
            all_of_outcome = ConditionStatusEnum.FAILED
        elif ConditionStatusEnum.UNKNOWN in all_of_statuses:
            all_of_outcome = ConditionStatusEnum.UNKNOWN
        else:
            all_of_outcome = ConditionStatusEnum.SATISFIED

        # B. Evaluate any_of
        if not any_of_statuses:
            any_of_outcome = ConditionStatusEnum.SATISFIED
        elif ConditionStatusEnum.SATISFIED in any_of_statuses:
            any_of_outcome = ConditionStatusEnum.SATISFIED
        elif ConditionStatusEnum.UNKNOWN in any_of_statuses:
            any_of_outcome = ConditionStatusEnum.UNKNOWN
        else:
            any_of_outcome = ConditionStatusEnum.FAILED

        # C. Evaluate none_of
        if not none_of_statuses:
            none_of_outcome = ConditionStatusEnum.SATISFIED
        elif ConditionStatusEnum.FAILED in none_of_statuses:
            # An exclusion was triggered!
            none_of_outcome = ConditionStatusEnum.FAILED
        elif ConditionStatusEnum.UNKNOWN in none_of_statuses:
            none_of_outcome = ConditionStatusEnum.UNKNOWN
        else:
            none_of_outcome = ConditionStatusEnum.SATISFIED

        # Check Rule Completeness mechanism (Milestone 4.4.1 safety audit)
        raw_completeness = (
            rule_ast.get("rule_completeness")
            or conditions_root.get("rule_completeness")
            or RuleCompletenessEnum.VERIFIED_COMPLETE
        )
        if isinstance(raw_completeness, str):
            try:
                completeness = RuleCompletenessEnum(raw_completeness.upper())
            except ValueError:
                completeness = RuleCompletenessEnum.UNVERIFIED
        else:
            completeness = raw_completeness

        unresolved_criteria = (
            rule_ast.get("unresolved_criteria")
            or conditions_root.get("unresolved_criteria")
            or []
        )

        # Final Status determination
        if (
            all_of_outcome == ConditionStatusEnum.FAILED
            or any_of_outcome == ConditionStatusEnum.FAILED
            or none_of_outcome == ConditionStatusEnum.FAILED
        ):
            final_status = EligibilityStatusEnum.NOT_ELIGIBLE
            summary = OUTCOME_SUMMARIES[final_status]
        elif (
            all_of_outcome == ConditionStatusEnum.SATISFIED
            and any_of_outcome == ConditionStatusEnum.SATISFIED
            and none_of_outcome == ConditionStatusEnum.SATISFIED
        ):
            # A scheme with PARTIAL or UNVERIFIED rules must NEVER return an unqualified ELIGIBLE result!
            if completeness in (RuleCompletenessEnum.PARTIAL, RuleCompletenessEnum.UNVERIFIED):
                final_status = EligibilityStatusEnum.POSSIBLY_ELIGIBLE
                summary = PARTIAL_VERIFICATION_SUMMARIES
            else:
                final_status = EligibilityStatusEnum.ELIGIBLE
                summary = OUTCOME_SUMMARIES[final_status]
        else:
            final_status = EligibilityStatusEnum.POSSIBLY_ELIGIBLE
            summary = OUTCOME_SUMMARIES[final_status]

        # Deduplicate citations by source_id or clause
        unique_citations: List[Dict[str, Any]] = []
        seen_clauses: Set[str] = set()
        for cit in citations:
            key = cit.get("clause") or cit.get("source_id") or str(cit)
            if key not in seen_clauses:
                seen_clauses.add(key)
                unique_citations.append(cit)

        return SchemeEligibilityResult(
            scheme_id=scheme_id,
            scheme_name=scheme_name,
            status=final_status,
            rule_completeness=completeness,
            summary=summary,
            conditions_satisfied=conditions_satisfied,
            conditions_failed=conditions_failed,
            missing_information=list(missing_info_map.values()),
            unresolved_criteria=unresolved_criteria,
            disclaimer=STANDARD_DISCLAIMERS,
            source_citations=unique_citations,
        )
