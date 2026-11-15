"""
Yojana Saathi - Grounded Chat Message Translation Service
Preserves markdown formatting, numbers, currency symbols, and official scheme names
across English, Hindi, Kannada, and Telugu with in-memory caching.
"""

from typing import Dict, Optional, Tuple
import re

# In-memory translation cache: (text_hash, target_lang) -> translated_text
_TRANSLATION_CACHE: Dict[Tuple[str, str], str] = {}

# Canonical Scheme Names that must NEVER be mangled or translated into corrupt words
CANONICAL_SCHEME_NAMES = [
    "PM-KISAN", "PM-KISAN Samman Nidhi",
    "Kisan Credit Card", "KCC",
    "PM-JAY", "Ayushman Bharat PM-JAY", "Ayushman Bharat",
    "PM-SVANidhi", "PM SVANidhi",
    "PMAY-G", "Pradhan Mantri Awaas Yojana - Gramin",
    "PM-KMY", "Pradhan Mantri Kisan Maandhan Yojana",
    "PMMVY", "Pradhan Mantri Matru Vandana Yojana",
    "PM-KUSUM",
]

# High-frequency phrases dictionary for assistant messages
PHRASE_DICTIONARY: Dict[str, Dict[str, str]] = {
    "Hello! I am Yojana Saathi. I can help you discover government schemes you may be eligible for. You can speak naturally or type your question.": {
        "hi": "नमस्ते! मैं योजना साथी हूँ। मैं आपको सरकारी कल्याणकारी योजनाएं खोजने में मदद कर सकता हूँ। आप स्वाभाविक रूप से बोल सकते हैं या अपना प्रश्न लिख सकते हैं।",
        "kn": "ನಮಸ್ಕಾರ! ನಾನು ಯೋಜನಾ ಸಾಥಿ. ನೀವು ಅರ್ಹರಾಗಿರುವ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಲು ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡುತ್ತೇನೆ. ನೀವು ಸ್ವಾಭಾವಿಕವಾಗಿ ಮಾತನಾಡಬಹುದು ಅಥವಾ ಟೈಪ್ ಮಾಡಬಹುದು.",
        "te": "నమస్కారం! నేను యోజన సాథి. మీరు అర్హులైన ప్రభుత్వ పథకాలను కనుగొనడంలో నేను మీకు సహాయపడతాను. మీరు సహజంగా మాట్లాడవచ్చు లేదా మీ ప్రశ్నను టైప్ చేయవచ్చు.",
    },
    "How can I help you with government welfare schemes today? You can check your eligibility or search for a scheme.": {
        "hi": "सरकारी योजनाओं के लिए मैं आपकी क्या सहायता कर सकता हूँ? आप अपनी पात्रता जांच सकते हैं या योजनाएं खोज सकते हैं।",
        "kn": "ಸರ್ಕಾರಿ ಯೋಜನೆಗಳ ಬಗ್ಗೆ ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ? ನಿಮ್ಮ ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಬಹುದು ಅಥವಾ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಬಹುದು.",
        "te": "ప్రభుత్వ పథకాల గురించి నేను మీకు ఎలా సహాయపడగలను? మీ అర్హతను తనిఖీ చేయవచ్చు లేదా పథకాలను శోధించవచ్చు.",
    },
    "Did you or your family pay income tax in the last assessment year?": {
        "hi": "क्या आपने या आपके परिवार ने पिछले आकलन वर्ष में आयकर का भुगतान किया था?",
        "kn": "ನೀವು ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬ ಕಳೆದ ಮೌಲ್ಯಮಾಪನ ವರ್ಷದಲ್ಲಿ ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿಸಿದ್ದೀರಾ?",
        "te": "మీరు లేదా మీ కుటుంబం గత అసెస్‌మెంట్ సంవత్సరంలో ఆదాయపు పన్ను చెల్లించారా?",
    },
    "Is the agricultural land registered in the name of an institution or trust?": {
        "hi": "क्या कृषि भूमि किसी संस्था या ट्रस्ट के नाम पर पंजीकृत है?",
        "kn": "ಕೃಷಿ ಭೂಮಿ ಯಾವುದೇ ಸಂಸ್ಥೆ ಅಥವಾ ಟ್ರಸ್ಟ್ ಹೆಸರಿನಲ್ಲಿ ನೋಂದಣಿಯಾಗಿದೆಯೇ?",
        "te": "వ్యవసాయ భూమి ఏదైనా సంస్థ లేదా ట్రస్ట్ పేరు మీద నమోదై ఉందా?",
    },
    "Are you or any family member a regular government/PSU employee?": {
        "hi": "क्या आप या आपके परिवार का कोई सदस्य नियमित सरकारी/पीएसयू कर्मचारी है?",
        "kn": "ನೀವು ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬದ ಯಾವುದೇ ಸದಸ್ಯರು ನಿಯಮಿತ ಸರ್ಕಾರಿ/ಪಿಎಸ್‌ಯು ಉದ್ಯೋಗಿಯೇ?",
        "te": "మీరు లేదా మీ కుటుంబ సభ్యులు ఎవరైనా ప్రభుత్వ/పీఎస్‌యూ ఉద్యోగా?",
    },
    "If retired, what is your monthly pension in rupees?": {
        "hi": "यदि सेवानिवृत्त हैं, तो आपकी मासिक पेंशन रुपये में कितनी है?",
        "kn": "ನಿವೃತ್ತರಾಗಿದ್ದರೆ, ನಿಮ್ಮ ಮಾಸಿಕ ಪಿಂಚಣಿ ರೂಪಾಯಿಗಳಲ್ಲಿ ಎಷ್ಟು?",
        "te": "పదవీ విరమణ చేసినట్లయితే, మీ నెలవారీ పెన్షన్ ఎంత?",
    },
    "Required Documents for": {
        "hi": "के लिए आवश्यक दस्तावेज",
        "kn": "ಗಾಗಿ ಅಗತ್ಯ ದಾಖಲೆಗಳು",
        "te": "కోసం అవసరమైన పత్రాలు",
    },
    "How to Apply for": {
        "hi": "के लिए आवेदन कैसे करें",
        "kn": "ಗೆ ಅರ್ಜಿ ಸಲ್ಲಿಸುವ ವಿಧಾನ",
        "te": "కోసం దరఖాస్తు విధానం",
    },
    "Official Portal": {
        "hi": "आधिकारिक पोर्टल",
        "kn": "ಅಧಿಕೃತ ಪೋರ್ಟಲ್",
        "te": "అధికారిక పోర్టల్",
    },
    "Mandatory": {
        "hi": "अनिवार्य",
        "kn": "ಕಡ್ಡಾಯ",
        "te": "తప్పనిసరి",
    },
    "Optional": {
        "hi": "वैकल्पिक",
        "kn": "ಐಚ್ಛಿಕ",
        "te": "ఐచ్ఛికం",
    },

    "Great news! Based on your verified details, you qualify for": {
        "hi": "अच्छी खबर! आपके सत्यापित विवरण के आधार पर, आप इसके लिए पात्र हैं:",
        "kn": "ಉತ್ತಮ ಸುದ್ದಿ! ನಿಮ್ಮ ವಿವರಗಳ ಪ್ರಕಾರ ನೀವು ಅರ್ಹರಾಗಿದ್ದೀರಿ:",
        "te": "శుభవార్త! మీ వివరాల ప్రకారం మీరు అర్హులు:",
    },
    "To check if you also qualify for": {
        "hi": "इसके लिए भी अपनी पात्रता जांचने हेतु:",
        "kn": "ಇದಕ್ಕೂ ನಿಮ್ಮ ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಲು:",
        "te": "దీనికి కూడా మీ అర్హత తనిఖీకి:",
    },
    "one question:": {
        "hi": "एक प्रश्न:",
        "kn": "ಒಂದು ಪ್ರಶ್ನೆ:",
        "te": "ఒక ప్రశ్న:",
    },
    "I found verified welfare schemes for your profile": {
        "hi": "मुझे आपकी प्रोफाइल के लिए सत्यापित सरकारी योजनाएं मिली हैं",
        "kn": "ನಿಮ್ಮ ವಿವರಗಳಿಗೆ ಸೂಕ್ತ ಯೋಜನೆಗಳು ಕಂಡುಬಂದಿವೆ",
        "te": "మీ కోసం ధృవీకరించిన ప్రభుత్వ పథకాలు గుర్తించాము",
    },
    "Key criteria met:": {
        "hi": "संतुष्ट मानदंड:",
        "kn": "ಪೂರೈಸಿದ ಮಾನದಂಡಗಳು:",
        "te": "నెరవేర్చిన నిబంధనలు:",
    },
    "Condition not met:": {
        "hi": "अपूर्ण शर्त:",
        "kn": "ಪೂರೈಸದ ಷರತ್ತು:",
        "te": "పూర్తికాని నిబంధన:",
    },
    "Own agricultural land": {
        "hi": "अपनी कृषि भूमि है",
        "kn": "ಸ್ವಂತ ಕೃಷಿ ಭೂಮಿ ಇದೆ",
        "te": "స్వంత వ్యవసాయ భూమి ఉంది",
    },
    "Cultivate land as a tenant": {
        "hi": "किरायेदार/पट्टेदार",
        "kn": "ಗೇಣಿದಾರ ರೈತ",
        "te": "కౌలు రైతు",
    },
    "Sharecropper": {
        "hi": "बटाईदार",
        "kn": "ಪಾಲುದಾರ",
        "te": "వాటాదారు",
    },
    "Animal husbandry": {
        "hi": "पशुपालन/डेयरी",
        "kn": "ಪಶುಸಂಗೋಪನೆ/ಡೈರಿ",
        "te": "పశుసంవర్ధక/పాడి",
    },
    "Fisheries": {
        "hi": "मत्स्य पालन",
        "kn": "ಮೀನುಗಾರಿಕೆ",
        "te": "మత్స్య సాగు",
    },
    "No default": {
        "hi": "कोई डिफ़ॉल्ट नहीं",
        "kn": "ಸುಸ್ತಿದಾರನಲ್ಲ",
        "te": "డిఫాల్ట్ లేదు",
    },
    "Yes, loan default": {
        "hi": "हाँ, बैंक डिफ़ॉल्ट है",
        "kn": "ಹೌದು, ಸುಸ್ತಿದಾರ",
        "te": "అవును, డిఫాల్ట్ ఉంది",
    },
    "Not sure": {
        "hi": "पक्का नहीं पता",
        "kn": "ಖಚಿತವಿಲ್ಲ",
        "te": "ఖచ్చితంగా తెలియదు",
    },
    "Yes": {
        "hi": "हाँ",
        "kn": "ಹೌದು",
        "te": "అవును",
    },
    "No": {
        "hi": "नहीं",
        "kn": "ಇಲ್ಲ",
        "te": "కాదు",
    },

    # Outcomes & headers
    "Satisfied Criteria:": {
        "hi": "संतुष्ट मानदंड:",
        "kn": "ಪೂರೈಸಲಾದ ಮಾನದಂಡಗಳು:",
        "te": "నెరవేర్చిన ప్రమాణాలు:",
    },
    "Unmet Criteria / Disqualifications:": {
        "hi": "अपूर्ण मानदंड / अपात्रता:",
        "kn": "ಅಪೂರ್ಣ ಮಾನದಂಡಗಳು / ಅನರ್ಹತೆ:",
        "te": "పూర్తికాని ప్రమాణాలు / అనర్హత:",
    },
    "Important Statutory Verification Requirements:": {
        "hi": "महत्वपूर्ण वैधानिक सत्यापन आवश्यकताएं:",
        "kn": "ಮುಖ್ಯ ಶಾಸನಬದ್ಧ ಪರಿಶೀಲನಾ ಅಗತ್ಯತೆಗಳು:",
        "te": "ముఖ్యమైన చట్టబద్ధమైన ధృవీకరణ అవసరాలు:",
    },
    "To continue checking your eligibility:": {
        "hi": "आपकी पात्रता जांच जारी रखने के लिए:",
        "kn": "ನಿಮ್ಮ ಅರ್ಹತಾ ಪರಿಶೀಲನೆಯನ್ನು ಮುಂದುವರಿಸಲು:",
        "te": "మీ అర్హత తనిఖీని కొనసాగించడానికి:",
    },
    "You satisfy all evaluated eligibility requirements for this scheme.": {
        "hi": "आप इस योजना के लिए सभी मूल्यांकित पात्रता शर्तों को पूरा करते हैं।",
        "kn": "ನೀವು ಈ ಯೋಜನೆಗಾಗಿ ಮೌಲ್ಯಮಾಪನ ಮಾಡಲಾದ ಎಲ್ಲಾ ಅರ್ಹತಾ ಮಾನದಂಡಗಳನ್ನು ಪೂರೈಸುತ್ತೀರಿ.",
        "te": "మీరు ఈ పథకానికి సంబంధించిన అన్ని అర్హత ప్రమాణాలను పూర్తి చేశారు.",
    },
    "You do not meet one or more mandatory eligibility or exclusion criteria for this scheme.": {
        "hi": "आप इस योजना के लिए एक या अधिक अनिवार्य पात्रता या बहिष्करण मानदंडों को पूरा नहीं करते हैं।",
        "kn": "ನೀವು ಈ ಯೋಜನೆಯ ಒಂದು ಅಥವಾ ಹೆಚ್ಚಿನ ಕಡ್ಡಾಯ ಅರ್ಹತೆ ಅಥವಾ ಹೊರಗಿಡುವ ಮಾನದಂಡಗಳನ್ನು ಪೂರೈಸುವುದಿಲ್ಲ.",
        "te": "మీరు ఈ పథకానికి సంబంధించిన ఒకటి లేదా అంతకంటే ఎక్కువ తప్పనిసరి అర్హతలు లేదా మినహాయింపు ప్రమాణాలను పూర్తి చేయలేదు.",
    },
    "You may be eligible, but additional information is required to complete the verification.": {
        "hi": "आप पात्र हो सकते हैं, लेकिन सत्यापन पूरा करने के लिए अतिरिक्त जानकारी की आवश्यकता है।",
        "kn": "ನೀವು ಅರ್ಹರಾಗಿರಬಹುದು, ಆದರೆ ಪರಿಶೀಲನೆ ಪೂರ್ಣಗೊಳಿಸಲು ಹೆಚ್ಚುವರಿ ಮಾಹಿತಿಯ ಅಗತ್ಯವಿದೆ.",
        "te": "మీరు అర్హులు కావచ్చు, కానీ ధృవీకరణ పూర్తి చేయడానికి అదనపు సమాచారం అవసరం.",
    },
    "Great news! You are eligible for": {
        "hi": "अच्छी खबर! आप पात्र हैं:",
        "kn": "ಉತ್ತಮ ಸುದ್ದಿ! ನೀವು ಅರ್ಹರಾಗಿದ್ದೀರಿ:",
        "te": "శుభవార్త! మీరు అర్హులు:",
    },
    "What would you like to check next?": {
        "hi": "आप आगे क्या जांचना चाहेंगे?",
        "kn": "ಮುಂದೆ ನೀವು ಏನನ್ನು ಪರಿಶೀಲಿಸಲು ಬಯಸುತ್ತೀರಿ?",
        "te": "తర్వాత మీరు ఏమి తనిಖీ చేయాలనుకుంటున్నారు?",
    },
    "You are currently not eligible for": {
        "hi": "आप वर्तमान में इसके लिए पात्र नहीं हैं:",
        "kn": "ನೀವು ಪ್ರಸ್ತುತ ಇದಕ್ಕೆ ಅರ್ಹರಲ್ಲ:",
        "te": "మీరు ప్రస్తుతం దీనికి అర్హులు కారు:",
    },
    "because:": {
        "hi": "क्योंकि:",
        "kn": "ಏಕೆಂದರೆ:",
        "te": "ఎందుకంటే:",
    },
    "One question to check your eligibility for": {
        "hi": "आपकी पात्रता जांचने के लिए एक प्रश्न:",
        "kn": "ನಿಮ್ಮ ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಲು ಒಂದು ಪ್ರಶ್ನೆ:",
        "te": "మీ అర్హతను తనిఖీ చేయడానికి ఒక ప్రశ్న:",
    },
    "Are you engaged in agricultural cultivation or an allied agricultural activity?": {
        "hi": "क्या आप कृषि खेती या उससे संबंधित संबद्ध कृषि गतिविधि में संलग्न हैं?",
        "kn": "ನೀವು ಕೃಷಿ ಸಾಗುವಳಿ ಅಥವಾ ಕೃಷಿ ಸಂಬಂಧಿತ ಚಟುವಟಿಕೆಯಲ್ಲಿ ತೊಡಗಿದ್ದೀರಾ?",
        "te": "మీరు వ్యవసాయ సాగు లేదా అనుబంధ వ్యవసాయ కార్యకలాపాలలో నిమగ్నమై ఉన్నారా?",
    },
    "Do you have any existing unresolved default on a bank loan?": {
        "hi": "क्या आपके पास किसी बैंक ऋण पर कोई मौजूदा बकाया डिफॉल्ट है?",
        "kn": "ನೀವು ಯಾವುದೇ ಬ್ಯಾಂಕ್ ಸಾಲದಲ್ಲಿ ಸುಸ್ತಿದಾರರಾಗಿದ್ದೀರಾ?",
        "te": "మీకు ఏదైనా బ్యాంకు రుణంపై బకాయి డిఫాల్ట్ ఉందా?",
    },
    "Do you cultivate agricultural land as a tenant, sharecropper, or oral lessee?": {
        "hi": "क्या आप बटाईदार, पट्टेदार या किरायेदार के रूप में कृषि भूमि पर खेती करते हैं?",
        "kn": "ನೀವು ಗೇಣಿದಾರರು ಅಥವಾ ಪಾಲುದಾರರಾಗಿ ಕೃಷಿ ಭೂಮಿಯಲ್ಲಿ ಸಾಗುವಳಿ ಮಾಡುತ್ತಿದ್ದೀರಾ?",
        "te": "మీరు కౌలు రైతుగా లేదా వాటాదారుగా వ్యవసాయ భూమిని సాగు చేస్తున్నారా?",
    },
    "Are you engaged in animal husbandry, dairy, poultry, or fisheries activities?": {
        "hi": "क्या आप पशुपालन, डेयरी, मुर्गीपालन या मत्स्य पालन गतिविधियों में संलग्न हैं?",
        "kn": "ನೀವು ಪಶುಸಂಗೋಪನೆ, ಡೈರಿ, ಕೋಳಿ ಸಾಕಣೆ ಅಥವಾ ಮೀನುಗಾರಿಕೆ ಚಟುವಟಿಕೆಗಳಲ್ಲಿ ತೊಡಗಿದ್ದೀರಾ?",
        "te": "మీరు పశుసంవర్ధక, పాడి, పౌల్ట్రీ లేదా మత్స్య సంబంధిత కార్యకలాపాలలో నిమగ్నమై ఉన్నారా?",
    },
    "Got it! You're not a bank defaulter.": {
        "hi": "समझ गया! आप बैंक डिफॉल्टर नहीं हैं।",
        "kn": "ತಿಳಿಯಿತು! ನೀವು ಬ್ಯಾಂಕ್ ಸುಸ್ತಿದಾರರಲ್ಲ.",
        "te": "అర్థమైంది! మీరు బ్యాంక్ డిఫాల్టర్ కాదు.",
    },
    "One more question:": {
        "hi": "एक और प्रश्न:",
        "kn": "ಇನ್ನೊಂದು ಪ್ರಶ್ನೆ:",
        "te": "మరొక ప్రశ్న:",
    },
    "Do you own agricultural land or cultivate land as a tenant?": {
        "hi": "क्या आपके पास कृषि भूमि है या आप किरायेदार के रूप में खेती करते हैं?",
        "kn": "ನೀವು ಕೃಷಿ ಭೂಮಿ ಹೊಂದಿದ್ದೀರಾ ಅಥವಾ ಗೇಣಿದಾರರಾಗಿ ಸಾಗುವಳಿ ಮಾಡುತ್ತಿದ್ದೀರಾ?",
        "te": "మీకు వ్యవసాయ భూమి ఉందా లేదా కౌలుదారుగా సాగు చేస్తున్నారా?",
    },
    "Are you currently a bank loan defaulter?": {
        "hi": "क्या आप वर्तमान में किसी बैंक ऋण के डिफ़ॉल्टर हैं?",
        "kn": "ನೀವು ಪ್ರಸ್ತುತ ಬ್ಯಾಂಕ್ ಸಾಲ ಸುಸ್ತಿದಾರರಾಗಿದ್ದೀರಾ?",
        "te": "మీరు ప్రస్తుతం బ్యాంక్ రుణ డిఫాల్టరా?",
    },
    "Are you a farmer?": {
        "hi": "क्या आप एक किसान हैं?",
        "kn": "ನೀವು ರೈತರಾಗಿದ್ದೀರಾ?",
        "te": "మీరు రైతులా?",
    },
    "Check eligibility": {
        "hi": "पात्रता जांचें",
        "kn": "ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ",
        "te": "అర్హతను తనిఖీ చేయండి",
    },
    "View benefits": {
        "hi": "लाभ देखें",
        "kn": "ಪ್ರಯೋಜನಗಳನ್ನು ನೋಡಿ",
        "te": "ప్రయోజనాలను చూడండి",
    },
    "Required documents": {
        "hi": "आवश्यक दस्तावेज",
        "kn": "ಅಗತ್ಯ ದಾಖಲೆಗಳು",
        "te": "అవసరమైన పత్రాలు",
    },
    "How to apply": {
        "hi": "आवेदन कैसे करें",
        "kn": "ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು ಹೇಗೆ",
        "te": "ఎలా దరఖాస్తు చేయాలి",
    },
    "Why this scheme?": {
        "hi": "यही योजना क्यों?",
        "kn": "ಈ ಯೋಜನೆ ಏಕೆ?",
        "te": "ఈ పథకం ఎందుకు?",
    },
    "Explore other schemes": {
        "hi": "अन्य योजनाएं देखें",
        "kn": "ಇತರ ಯೋಜನೆಗಳನ್ನು ಅನ್ವೇಷಿಸಿ",
        "te": "ఇతర పథకాలను అన్వేషించండి",
    },
    "Edit my details": {
        "hi": "मेरे विवरण संपादित करें",
        "kn": "ನನ್ನ ವಿವರಗಳನ್ನು ತಿದ್ದಿ",
        "te": "నా వివరాలను సవరించండి",
    },
    "Application steps": {
        "hi": "आवेदन के चरण",
        "kn": "ಅರ್ಜಿ ಸಲ್ಲಿಕೆಯ ಹಂತಗಳು",
        "te": "దరఖాస్తు దశలు",
    },
    "Based on what you've told me:": {
        "hi": "आपके द्वारा दी गई जानकारी के आधार पर:",
        "kn": "ನೀವು ನೀಡಿದ ಮಾಹಿತಿಯ ಆಧಾರದ ಮೇಲೆ:",
        "te": "మీరు తెలిపిన సమాచారం ప్రకారం:",
    },
    "I found these relevant schemes and checked your details with our deterministic rules engine:": {
        "hi": "मुझे ये प्रासंगिक योजनाएं मिलीं और नियमों के आधार पर आपके विवरण की जांच की:",
        "kn": "ಸೂಕ್ತ ಯೋಜನೆಗಳು ಕಂಡುಬಂದಿದ್ದು ನಿಯಮಗಳ ಪ್ರಕಾರ ಪರಿಶೀಲಿಸಲಾಗಿದೆ:",
        "te": "సంబంధిత పథకాలను గుర్తించి నిబంధనల ప్రకారం పరిశీలించాము:",
    },
    "Schemes You May Be Eligible For": {
        "hi": "योजनाएं जिनके लिए आप पात्र हो सकते हैं",
        "kn": "ನೀವು ಅರ್ಹರಾಗಿರಬಹುದಾದ ಯೋಜನೆಗಳು",
        "te": "మీరు అర్హులయ్యే అవకాశమున్న పథకాలు",
    },
    "Schemes Needing a Little More Information": {
        "hi": "योजनाएं जिनके लिए थोड़ी और जानकारी चाहिए",
        "kn": "ಹೆಚ್ಚಿನ ಮಾಹಿತಿಯ ಅಗತ್ಯವಿರುವ ಯೋಜನೆಗಳು",
        "te": "కొద్దిగా సమాచారం అవసరమైన పథకాలు",
    },
    "Schemes You Currently Do Not Qualify For": {
        "hi": "योजनाएं जिनके लिए आप वर्तमान में पात्र नहीं हैं",
        "kn": "ನೀವು ಪ್ರಸ್ತುತ ಅರ್ಹರಲ್ಲದ ಯೋಜನೆಗಳು",
        "te": "మీరు ప్రస్తుతం అర్హులు కాని పథకాలు",
    },
    "Hello! I am Yojana Saathi, your trusted guide for discovering Indian government welfare schemes.": {
        "hi": "नमस्ते! मैं योजना साथी हूँ, भारतीय सरकारी कल्याणकारी योजनाओं को खोजने के लिए आपका विश्वसनीय मार्गदर्शक।",
        "kn": "ನಮಸ್ಕಾರ! ನಾನು ಯೋಜನೆ ಸಾಥಿ, ಭಾರತೀಯ ಸರ್ಕಾರಿ ಕಲ್ಯಾಣ ಯೋಜನೆಗಳನ್ನು ಅನ್ವೇಷಿಸಲು ನಿಮ್ಮ ವಿಶ್ವಾಸಾರ್ಹ ಮಾರ್ಗದರ್ಶಿ.",
        "te": "నమస్కారం! నేను యోజనా సాథి, భారత ప్రభుత్వ సంక్షేమ పథకాలను కనుగొనడానికి మీ నమ్మకమైన మార్గదర్శి.",
    },
    "I can help you:": {
        "hi": "मैं आपकी सहायता कर सकता हूँ:",
        "kn": "ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ:",
        "te": "నేను మీకు సహాయం చేయగలను:",
    },
    "Find schemes you might be eligible for.": {
        "hi": "उन योजनाओं को खोजें जिनके लिए आप पात्र हो सकते हैं।",
        "kn": "ನೀವು ಅರ್ಹರಾಗಬಹುದಾದ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಿ.",
        "te": "మీరు అర్హత సాధించే పథకాలను కనుగొనండి.",
    },
    "Understand the benefits and requirements of specific programs.": {
        "hi": "विशिष्ट कार्यक्रमों के लाभों और आवश्यकताओं को समझें।",
        "kn": "ನಿರ್ದಿಷ್ಟ ಯೋಜನೆಗಳ ಪ್ರಯೋಜನಗಳು ಮತ್ತು ಅಗತ್ಯತೆಗಳನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳಿ.",
        "te": "నిర్దిష్ట పథకాల ప్రయోజనాలు మరియు అవసరాలను అర్థం చేసుకోండి.",
    },
    "Guide you on how to apply.": {
        "hi": "आवेदन करने के तरीके पर आपका मार्गदर्शन करें।",
        "kn": "ಹೇಗೆ ಅರ್ಜಿ ಸಲ್ಲಿಸಬೇಕು ಎಂದು ನಿಮಗೆ ಮಾರ್ಗದರ್ಶನ ನೀಡಿ.",
        "te": "ఎలా దరఖాస్తు చేయాలో మీకు మార్గదర్శకత్వం చేయండి.",
    },
    "To get started, please tell me:": {
        "hi": "शुरू करने के लिए, कृपया मुझे बताएं:",
        "kn": "ಪ್ರಾರಂಭಿಸಲು, ದಯವಿಟ್ಟು ನನಗೆ ತಿಳಿಸಿ:",
        "te": "ప్రారంభించడానికి, దయచేసి నాకు చెప్పండి:",
    },
    "What is your primary need?": {
        "hi": "आपकी प्राथमिक आवश्यकता क्या है?",
        "kn": "ನಿಮ್ಮ ಪ್ರಾಥಮಿಕ ಅಗತ್ಯತೆ ಏನು?",
        "te": "మీ ప్రాథమిక అవసరం ఏమిటి?",
    },
    "(e.g., financial assistance, housing, education, health, or livelihood support)": {
        "hi": "(उदा. वित्तीय सहायता, आवास, शिक्षा, स्वास्थ्य, या आजीविका सहायता)",
        "kn": "(ಉದಾ., ಆರ್ಥಿಕ ನೆರವು, ವಸತಿ, ಶಿಕ್ಷಣ, ಆರೋಗ್ಯ, ಅಥವಾ ಜೀವನೋಪಾಯ ಬೆಂಬಲ)",
        "te": "(ఉదా., ఆర్థిక సహాయం, గృహనిర్మాణం, విద్య, ఆరోగ్యం లేదా జీవనోపాధి మద్దతు)",
    },
    "Which state or union territory do you reside in?": {
        "hi": "आप किस राज्य या केंद्र शासित प्रदेश में रहते हैं?",
        "kn": "ನೀವು ಯಾವ ರಾಜ್ಯ ಅಥವಾ ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶದಲ್ಲಿ ವಾಸಿಸುತ್ತೀರಿ?",
        "te": "మీరు ఏ రాష్ట్రం లేదా కేంద్రపాలిత ప్రాంతంలో నివసిస్తున్నారు?",
    },
    "Alternatively, if you have a specific scheme in mind, you can ask me about it directly!": {
        "hi": "वैकल्पिक रूप से, यदि आपके मन में कोई विशिष्ट योजना है, तो आप सीधे उसके बारे में पूछ सकते हैं!",
        "kn": "ಪರ್ಯಾಯವಾಗಿ, ನಿಮ್ಮ ಮನಸ್ಸಿನಲ್ಲಿ ಯಾವುದೇ ನಿರ್ದಿಷ್ಟ ಯೋಜನೆ ಇದ್ದರೆ, ನೀವು ನೇರವಾಗಿ ಅದರ ಬಗ್ಗೆ ಕೇಳಬಹುದು!",
        "te": "ప్రత్యామ్నాయంగా, మీ మనస్సులో ఏదైనా నిర్దిష్ట పథకం ఉంటే, మీరు నేరుగా దాని గురించి నన్ను అడగవచ్చు!",
    },
    "What is your current age?": {
        "hi": "आपकी वर्तमान आयु क्या है?",
        "kn": "ನಿಮ್ಮ ಪ್ರಸ್ತುತ ವಯಸ್ಸು ಎಷ್ಟು?",
        "te": "మీ ప్రస్తుత వయస్సు ఎంత?",
    },
    "What is your gender?": {
        "hi": "आपका लिंग क्या है?",
        "kn": "ನಿಮ್ಮ ಲಿಂಗ ಯಾವುದು?",
        "te": "మీ లింగం ఏమిటి?",
    },
    "What is your primary occupation or livelihood?": {
        "hi": "आपका मुख्य व्यवसाय या आजीविका क्या है?",
        "kn": "ನಿಮ್ಮ ಮುಖ್ಯ ಉದ್ಯೋಗ ಅಥವಾ ಜೀವನೋಪಾಯ ಯಾವುದು?",
        "te": "మీ ప్రధాన వృత్తి లేదా జీవనోపాధి ఏమిటి?",
    },
    "Do you own cultivable agricultural land or cultivate as a tenant?": {
        "hi": "क्या आपके पास कृषि योग्य भूमि है या आप बटाईदार/पट्टेदार किसान हैं?",
        "kn": "ನಿಮ್ಮ ಹೆಸರಿನಲ್ಲಿ ಕೃಷಿ ಭೂಮಿ ಇದೆಯೇ ಅಥವಾ ಗೇಣಿ ರೈತರಾಗಿದ್ದೀರಾ?",
        "te": "మీకు సాగు భూమి ఉందా లేదా కౌలు రైతులా?",
    },
    "What is your estimated annual family income?": {
        "hi": "आपकी अनुमानित वार्षिक पारिवारिक आय कितनी है?",
        "kn": "ನಿಮ್ಮ ಕುಟುಂಬದ ಅಂದಾಜು ವಾರ್ಷಿಕ ಆದಾಯ ಎಷ್ಟು?",
        "te": "మీ కుటుంబ వార్షಿಕ ఆదాయం సుమారు ఎంత?",
    },
    "Do you pay income tax or have a permanent regular government job?": {
        "hi": "क्या आप आयकर देते हैं या नियमित सरकारी नौकरी करते हैं?",
        "kn": "ನೀವು ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿಸುತ್ತೀರಾ ಅಥವಾ ಕಾಯಂ ಸರ್ಕಾರಿ ಉದ್ಯೋಗ ಹೊಂದಿದ್ದೀರಾ?",
        "te": "మీరు ఆదాయపు పన్ను చెల్లిస్తున్నారా లేదా శాశ్వత ప్రభుత్వ ఉద్యోగం ఉందా?",
    },
    "Hello! I am **Yojana Saathi**, your trusted guide for discovering Indian government welfare schemes.": {
        "hi": "नमस्ते! मैं **योजना साथी** हूँ, भारतीय सरकारी कल्याणकारी योजनाओं को खोजने के लिए आपका विश्वसनीय मार्गदर्शक।",
        "kn": "ನಮಸ್ಕಾರ! ನಾನು **ಯೋಜನಾ ಸಾಥಿ**, ಭಾರತೀಯ ಸರ್ಕಾರಿ ಕಲ್ಯಾಣ ಯೋಜನೆಗಳನ್ನು ಅನ್ವೇಷಿಸಲು ನಿಮ್ಮ ವಿಶ್ವಾಸಾರ್ಹ ಮಾರ್ಗದರ್ಶಿ.",
        "te": "నమస్కారం! నేను **యోజనా సాథి**, భారత ప్రభుత్వ సంక్షేమ పథకాలను కనుగొనడానికి మీ నమ్మకమైన మార్గదర్శి.",
    },
    "What is your annual family income?": {
        "hi": "आपकी वार्षिक पारिवारिक आय कितनी है?",
        "kn": "ನಿಮ್ಮ ಕುಟುಂಬದ ವಾರ್ಷಿಕ ಆದಾಯ ಎಷ್ಟು?",
        "te": "మీ కుటుంబ వార్ಷಿಕ ఆదాయం ఎంత?",
    },
    "Has Bank passbook": {
        "hi": "सक्रिय बैंक खाता एवं पासबुक (डीबीटी हेतु)",
        "kn": "ಸಕ್ರಿಯ ಬ್ಯಾಂಕ್ ಖಾತೆ ಮತ್ತು ಪಾಸ್‌ಬುಕ್ (ಡಿಬಿಟಿಗಾಗಿ)",
        "te": "సక్రియ బ్యాంక్ ఖాతా మరియు పాస్‌బుక్ (డిబిటి కోసం)",
    },
    "Active savings bank account for direct benefit transfer (DBT)": {
        "hi": "प्रत्यक्ष लाभ अंतरण (डीबीटी) के लिए सक्रिय बचत बैंक खाता",
        "kn": "ನೇರ ಲಾಭ ವರ್ಗಾವಣೆಗಾಗಿ (ಡಿಬಿಟಿ) ಸಕ್ರಿಯ ಉಳಿತಾಯ ಬ್ಯಾಂಕ್ ಖಾತೆ",
        "te": "ప్రత్యక్ష ప్రయోజన బదిలీ (DBT) కోసం సక్రియ సేవిಂಗ್స్ బ్యాంక్ ఖాతా",
    },
    "Has savings account": {
        "hi": "सक्रिय बचत बैंक खाता",
        "kn": "ಸಕ್ರಿಯ ಉಳಿತಾಯ ಬ್ಯಾಂಕ್ ಖಾತೆ",
        "te": "సక్రియ సేవింగ్స్ బ్యాంక్ ఖాతా",
    },
    "Has basic savings bank account": {
        "hi": "वाणिज्यिक बचत बैंक खाता",
        "kn": "ವಾಣಿಜ್ಯ ಉಳಿತಾಯ ಬ್ಯಾಂಕ್ ಖಾತೆ",
        "te": "వాణిజ్య సేవింగ్స్ బ్యాంక్ ఖాతా",
    },
    "Social Category": {
        "hi": "सामाजिक श्रेणी (आरक्षण)",
        "kn": "ಸಾಮಾಜಿಕ ವರ್ಗ (ಮೀಸಲಾತಿ)",
        "te": "సామాజిక వర్గం (రిజర్వేషన్)",
    },
    "Social / Reservation Category": {
        "hi": "सामाजिक / आरक्षण श्रेणी",
        "kn": "ಸಾಮಾಜಿಕ / ಮೀಸಲಾತಿ ವರ್ಗ",
        "te": "సామాಜಿಕ / రిజర్వేషన్ వర్గం",
    },
    "Differently Abled (PwD)": {
        "hi": "दिव्यांगजन (विशेष योग्यता)",
        "kn": "ವಿಕಲಾಂಗತೆ (ವಿಶೇಷ ಚೇತನರು)",
        "te": "దివ్యాంగులు (ప్రత్యేక ప్రతిభావంతులు)",
    },
    "Permanent Concrete (Pucca) House": {
        "hi": "पक्का (कंक्रीट) मकान",
        "kn": "ಪಕ್ಕಾ (ಕಾಂಕ್ರೀಟ್) ಮನೆ",
        "te": "పక్కా (కాంక్రీట్) ఇల్లు",
    },
    "Active Bank Account with Passbook": {
        "hi": "पासबुक सहित सक्रिय बैंक खाता",
        "kn": "ಪಾಸ್‌ಬುಕ್ ಹೊಂದಿರುವ ಸಕ್ರಿಯ ಬ್ಯಾಂಕ್ ಖಾತೆ",
        "te": "పాస్‌బుక్‌తో కూడిన సక్రియ బ్యాంక్ ఖాతా",
    },
}

# Reverse lookups for translating native back to English
REVERSE_DICTIONARY: Dict[str, str] = {}
for en_text, translations in PHRASE_DICTIONARY.items():
    for l_code, localized in translations.items():
        REVERSE_DICTIONARY[localized.strip()] = en_text.strip()


def detect_text_script(text: str) -> str:
    """Identifies primary script of input text."""
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "kn"
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "te"
    return "en"


def translate_assistant_text(
    text: str,
    target_language: str,
    source_language: Optional[str] = None
) -> Tuple[str, bool]:
    """
    Translates assistant message to target language.
    Returns (translated_text, is_cached).
    """
    if not text or not text.strip():
        return text, False

    target_lang = target_language.lower().strip()
    if target_lang not in ("en", "hi", "kn", "te"):
        target_lang = "en"

    cache_key = (text.strip(), target_lang)
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key], True

    # Check if text is already in the target script/language
    detected = detect_text_script(text)
    if detected == target_lang:
        _TRANSLATION_CACHE[cache_key] = text
        return text, False

    # Perform phrase and structural translation
    # Line-by-line translation with prefix/suffix preservation (e.g. bullets, numbers, markdown)
    lines = text.split("\n")
    processed_lines = []
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            processed_lines.append(line)
            continue

        indent_len = len(line) - len(line.lstrip())
        indent = line[:indent_len]

        m_bullet = re.match(r"^([\s*•\-–#]+|\d+[\.\)]\s*)(.*)$", stripped_line)
        if m_bullet:
            prefix = m_bullet.group(1)
            core = m_bullet.group(2).strip()
        else:
            prefix = ""
            core = stripped_line

        matched_trans = None
        # Target is English (translate from native)
        if target_lang == "en":
            for native_phrase, en_equiv in sorted(REVERSE_DICTIONARY.items(), key=lambda x: len(x[0]), reverse=True):
                if native_phrase.strip().lower() == core.lower():
                    matched_trans = en_equiv
                    break
        else:
            # Check exact core match
            for en_phrase, lang_map in PHRASE_DICTIONARY.items():
                if target_lang in lang_map and en_phrase.strip().lower() == core.lower():
                    matched_trans = lang_map[target_lang]
                    break
            # Check core without markdown asterisks
            if not matched_trans:
                clean_core = core.replace("**", "").replace("*", "").strip()
                for en_phrase, lang_map in PHRASE_DICTIONARY.items():
                    clean_en = en_phrase.replace("**", "").replace("*", "").strip()
                    if target_lang in lang_map and clean_en.lower() == clean_core.lower():
                        matched_trans = lang_map[target_lang]
                        break

        if matched_trans:
            processed_lines.append(f"{indent}{prefix}{matched_trans}")
        else:
            # Sub-phrase replacement within line
            line_trans = line
            if target_lang == "en":
                for native_phrase, en_equiv in sorted(REVERSE_DICTIONARY.items(), key=lambda x: len(x[0]), reverse=True):
                    if native_phrase in line_trans:
                        line_trans = line_trans.replace(native_phrase, en_equiv)
            else:
                for en_phrase, lang_map in sorted(PHRASE_DICTIONARY.items(), key=lambda x: len(x[0]), reverse=True):
                    if target_lang in lang_map and en_phrase in line_trans:
                        line_trans = line_trans.replace(en_phrase, lang_map[target_lang])
            processed_lines.append(line_trans)

    translated = "\n".join(processed_lines)
    _TRANSLATION_CACHE[cache_key] = translated
    return translated, False


async def translate_text_async(
    text: str,
    target_language: str,
    source_language: Optional[str] = None
) -> Tuple[str, bool, bool]:
    """
    Translates text adhering to Bhashini & AI4Bharat IndicTrans2 standards.
    Uses in-memory cache, structural dictionaries, and cascading LLM Gateway translation.
    Returns (translated_text, was_cached, is_translated).
    """
    if not text or not text.strip():
        return text, False, True

    target_lang = target_language.lower().strip()
    if target_lang not in ("en", "hi", "kn", "te"):
        target_lang = "en"

    cache_key = (text.strip(), target_lang)
    if cache_key in _TRANSLATION_CACHE:
        cached_val = _TRANSLATION_CACHE[cache_key]
        return cached_val, True, True

    # 1. Exact or partial dictionary translation
    translated, hit = translate_assistant_text(text, target_lang, source_language)
    detected_target = detect_text_script(translated)
    if hit or (detected_target == target_lang and target_lang != "en") or (target_lang == "en" and detected_target == "en" and translated != text):
        _TRANSLATION_CACHE[cache_key] = translated
        return translated, False, True

    # 2. Dynamic AI translation via LLMGateway (Bhashini / AI4Bharat Indic standard)
    try:
        from app.services.llm.gateway import LLMGateway
        gw = LLMGateway()
        target_name = {
            "en": "English",
            "hi": "Hindi (Devanagari script)",
            "kn": "Kannada (Kannada script)",
            "te": "Telugu (Telugu script)",
        }.get(target_lang, "English")

        prompt = (
            f"You are an expert Indic language translator adhering to Project Bhashini and AI4Bharat IndicTrans2 standards "
            f"for Government of India welfare schemes.\n"
            f"Translate the following text accurately into {target_name}.\n"
            f"Requirements:\n"
            f"- Preserve official scheme names (e.g. PM-KISAN, Ayushman Bharat, PM-SVANidhi, KCC).\n"
            f"- Preserve all numbers, currency signs (₹), URLs, and markdown formatting.\n"
            f"- Return ONLY the translated text, with no preamble, commentary, or extra quotes.\n\n"
            f"Text to translate:\n{text}"
        )
        resp = await gw.generate_text(prompt=prompt, max_tokens=1024, temperature=0.1, timeout_seconds=6.0)
        ai_trans = (resp.text or "").strip()
        if ai_trans and ai_trans != text:
            ai_script = detect_text_script(ai_trans)
            if target_lang == "en" or ai_script == target_lang:
                _TRANSLATION_CACHE[cache_key] = ai_trans
                return ai_trans, False, True
    except Exception:
        pass

    # Check if translated is genuine
    is_genuine = False
    if target_lang != "en":
        is_genuine = (detect_text_script(translated) == target_lang)
    else:
        is_genuine = (detect_text_script(translated) == "en" and (translated != text or detect_text_script(text) == "en"))

    if is_genuine:
        _TRANSLATION_CACHE[cache_key] = translated
    return translated, False, is_genuine


