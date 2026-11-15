"""
Yojana Saathi - Multilingual Scheme Synonyms & Search Keywords
Curated terminology, transliterations, and colloquial citizen query mappings
for English, Hindi, Kannada, and Telugu.

Rules:
- Strictly verified terminology; no accidental scheme conflation.
- Telangana KCR Kit is NOT mapped to central PMMVY.
- Telangana Rythu Bharosa is NOT mapped to central PM-KISAN.
"""

from typing import Dict, List

# Curated keywords and synonyms for each verified scheme
SCHEME_SEARCH_METADATA: Dict[str, Dict[str, List[str]]] = {
    "pm-kisan": {
        "keywords": [
            "pmkisan", "pm kisan", "samman", "nidhi", "farmer", "agriculture",
            "landholding", "dbt", "6000", "installment", "kisan credit"
        ],
        "synonyms_en": [
            "income support", "farmer grant", "pm kisan samman nidhi",
            "cultivable land", "agricultural input support"
        ],
        "synonyms_hi": [
            "किसान", "पीएम किसान", "किसान सम्मान निधि", "कृषि", "खेती",
            "भूमि", "खाद बीज", "वार्षिक 6000", "डीबीटी किस्त"
        ],
        "synonyms_kn": [
            "ರೈತ", "ಪಿಎಂ ಕಿಸಾನ್", "ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ", "ಕೃಷಿ", "ಭೂಮಿ",
            "ಕೃಷಿ ನೆರವು", "ವರ್ಷಕ್ಕೆ 6000", "ನೇರ ನಗದು ವರ್ಗಾವಣೆ"
        ],
        "synonyms_te": [
            "రైతు", "పీఎం కిసాన్", "కిసాన్ సమ్మాన్ నిధి", "వ్యవసాయం", "భూమి",
            "రైతు పెట్టుబడి సాయం", "ఏడాదికి 6000", "డీబీటీ వాయిదా"
        ]
    },
    "pm-jay": {
        "keywords": [
            "pmjay", "pm jay", "ayushman", "bharat", "health", "insurance",
            "hospital", "500000", "5 lakh", "golden card", "bis", "cashless"
        ],
        "synonyms_en": [
            "health insurance", "hospital treatment", "medical coverage",
            "free operation", "senior citizen 70 health cover", "ayushman card"
        ],
        "synonyms_hi": [
            "आयुष्मान", "आयुष्मान भारत", "स्वास्थ्य बीमा", "अस्पताल", "इलाज",
            "मुफ्त इलाज", "5 लाख बीमा", "वरिष्ठ नागरिक स्वास्थ्य", "गोल्डन कार्ड"
        ],
        "synonyms_kn": [
            "ಆರೋಗ್ಯ", "ಆಯುಷ್ಮಾನ್ ಭಾರತ್", "ಆರೋಗ್ಯ ವಿಮೆ", "ಆಸ್ಪತ್ರೆ", "ಚಿಕಿತ್ಸೆ",
            "ಉಚಿತ ಚಿಕಿತ್ಸೆ", "5 ಲಕ್ಷ ವಿಮೆ", "ಹಿರಿಯ ನಾಗರಿಕರ ಆರೋಗ್ಯ ರಕ್ಷಣೆ", "ಗೋಲ್ಡನ್ ಕಾರ್ಡ್"
        ],
        "synonyms_te": [
            "ఆరోగ్యం", "ఆయుష్మాన్ భారత్", "ఆరోగ్య బీమా", "ఆసుపత్రి", "చికిత్స",
            "ఉచిత వైద్యం", "5 లక్షల బీమా", "సీనియర్ సిటిజన్ ఆరోగ్య పథకం", "గోల్డెన్ కార్డు"
        ]
    },
    "pm-svanidhi": {
        "keywords": [
            "svanidhi", "pmsvanidhi", "street vendor", "hawker", "loan",
            "working capital", "thela", "rehri", "15000", "25000", "50000",
            "cashback", "urban livelihoods"
        ],
        "synonyms_en": [
            "vendor loan", "street vendor subsidy", "micro credit",
            "working capital loan", "interest subsidy", "digital cashback"
        ],
        "synonyms_hi": [
            "स्ट्रीट वेंडर", "फेरीवाला", "रेहड़ी", "पटरी", "ठेला", "दुकानदार",
            "स्वनिधि ऋण", "कार्यशील पूंजी", "कैशबैक", "सड़क विक्रेता ऋण",
            "विक्रेता", "स्ट्रीट विक्रेता"
        ],
        "synonyms_kn": [
            "ಬೀದಿ ವ್ಯಾಪಾರಿ", "ಬೀದಿ ಬದಿ ವ್ಯಾಪಾರಿ", "ಕಿರು ಸಾಲ", "ಸ್ವನಿಧಿ",
            "ದುಡಿಯುವ ಬಂಡವಾಳ", "ವ್ಯಾಪಾರ ಸಾಲ", "ಡಿಜಿಟಲ್ ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್",
            "ಮಾರಾಟಗಾರ", "ಬೀದಿ ಮಾರಾಟಗಾರ"
        ],
        "synonyms_te": [
            "చిరువ్యాపారి", "వీధి వ్యాపారులు", "చిరు రుణం", "స్వనిధి",
            "వ్యాపార పెట్టుబడి రుణం", "వడ్డీ సబ్సిడీ", "డిజిటల్ క్యాష్‌బ్యాక్",
            "విక్రేత", "చిరు విక్రేత"
        ]
    },
    "pmay-g": {
        "keywords": [
            "pmay", "pmayg", "awas", "housing", "pucca house", "rural house",
            "shelter", "makan", "ghar", "120000", "130000", "kutcha house"
        ],
        "synonyms_en": [
            "rural housing scheme", "free house", "pucca house grant",
            "home construction financial assistance", "pradhan mantri awas yojana"
        ],
        "synonyms_hi": [
            "आवास", "पीएम आवास ग्रामीण", "पक्का मकान", "घर", "ग्रामीण घर",
            "मकान निर्माण सहायता", "कच्चा घर से पक्का घर", "आवास योजना"
        ],
        "synonyms_kn": [
            "ಆವಾಸ್", "ಪಿಎಂ ಆವಾಸ್ ಯೋಜನೆ ಗ್ರಾಮೀಣ", "ಪಕ್ಕಾ ಮನೆ", "ಮನೆ ನಿರ್ಮಾಣ",
            "ಗ್ರಾಮೀಣ ವಸತಿ", "ಮನೆ ಸಹಾಯಧನ", "ಉಚಿತ ಮನೆ ಯೋಜನೆ"
        ],
        "synonyms_te": [
            "ఆవాస్", "పీఎం ఆవాస్ యోజన గ్రామీణ్", "పక్కా ఇల్లు", "ఇంటి నిర్మాణం",
            "గ్రామీణ గృహ నిర్మాణం", "ఇంటి మంజూరు", "ఉచిత ఇళ్ల పథకం"
        ]
    },
    "pm-kmy": {
        "keywords": [
            "pmkmy", "pm kmy", "maandhan", "pension", "old age", "farmer pension",
            "3000", "60 years", "smf", "lic", "voluntary contribution", "55"
        ],
        "synonyms_en": [
            "kisan pension scheme", "farmer old age pension", "monthly pension 3000",
            "small marginal farmer pension", "kisan maandhan yojana"
        ],
        "synonyms_hi": [
            "किसान पेंशन", "प्रधानमंत्री किसान मानधन", "वृद्धावस्था पेंशन",
            "60 वर्ष बाद 3000", "मासिक पेंशन", "छोटे किसान पेंशन"
        ],
        "synonyms_kn": [
            "ಕಿಸಾನ್ ಪಿಂಚಣಿ", "ಪ್ರಧಾನ ಮಂತ್ರಿ ಕಿಸಾನ್ ಮಾನ್ ಧನ್", "ವೃದ್ಧಾಪ್ಯ ಪಿಂಚಣಿ",
            "60 ವರ್ಷದ ನಂತರ 3000", "ಮಾಸಿಕ ಪಿಂಚಣಿ ಯೋಜನೆ", "ಸಣ್ಣ ರೈತರ ಪಿಂಚಣಿ"
        ],
        "synonyms_te": [
            "కిసాన్ పెన్షన్", "ప్రధాన మంత్రి కిసాన్ మాన్‌ధన్", "వృద్ధాప్య పింఛను",
            "60 ఏళ్ల తర్వాత 3000", "నెలవారీ పెన్షన్ పథకం", "చిన్న రైతుల పెన్షన్"
        ]
    },
    "pmmvy": {
        "keywords": [
            "pmmvy", "matru", "vandana", "maternity", "pregnant", "lactating",
            "mother", "childbirth", "3000", "2000", "5000", "6000", "mcp card", "anc", "samarthya"
        ],
        "synonyms_en": [
            "maternity benefit scheme", "pregnancy financial support",
            "mother care cash incentive", "first installment 3000", "second installment 2000",
            "first child 5000", "second girl child 6000"
        ],
        "synonyms_hi": [
            "मातृ वंदना", "गर्भवती महिला सहायता", "मातृत्व लाभ", "प्रसव पूर्व जांच",
            "पहली किस्त 3000", "दूसरी किस्त 2000",
            "पहले बच्चे के लिए 5000", "दूसरी कन्या के लिए 6000", "धात्री माता योजना"
        ],
        "synonyms_kn": [
            "ಮಾತೃ ವಂದನಾ", "ಗರ್ಭಿಣಿ ಮಹಿಳೆಯರ ಧನಸಹಾಯ", "ಮಾತೃತ್ವ ಸೌಲಭ್ಯ", "ಹೆರಿಗೆ ನೆರವು",
            "ಮೊದಲ ಕಂತು 3000", "ಎರಡನೇ ಕಂತು 2000",
            "ಮೊದಲ ಮಗುವಿಗೆ 5000", "ಎರಡನೇ ಹೆಣ್ಣು ಮಗುವಿಗೆ 6000", "ತಾಯಿ ಮತ್ತು ಮಗು ರಕ್ಷಣೆ"
        ],
        "synonyms_te": [
            "మాతృ వందన", "గర్భిణుల ఆర్థిక సాయం", "ప్రసూతి ప్రయోజనం", "డెలివరీ సహాయం",
            "మొదటి విడత 3000", "రెండవ విడత 2000",
            "మొదటి బిడ్డకు 5000", "రెండవ ఆడపిల్లకు 6000", "తల్లీ బిడ్డల పథకం"
        ]
    },
    "pm-kusum": {
        "keywords": [
            "kusum", "pmkusum", "component b", "solar pump", "solar agri pump",
            "irrigation", "offgrid", "diesel pump replacement", "cfa", "borewell", "7.5 hp",
            "solar", "pump", "सौर", "ಸೌರ", "సౌర"
        ],
        "synonyms_en": [
            "solar water pump subsidy", "standalone solar agriculture pump",
            "farm irrigation solar scheme", "pm kusum component b", "solar tubewell",
            "solar pump"
        ],
        "synonyms_hi": [
            "सोलर पंप", "पीएम कुसुम घटक बी", "सौर कृषि पंप", "खेत सिंचाई पंप",
            "डीजल पंप सब्सिडी", "सौर जल पंप योजना", "कुसुम बोरवेल पंप", "सौर"
        ],
        "synonyms_kn": [
            "ಸೌರ ಪಂಪ್", "ಪಿಎಂ ಕುಸುಮ್ ಕಾಂಪೊನೆಂಟ್ ಬಿ", "ಸೌರ ಕೃಷಿ ಪಂಪ್", "ಜಮೀನು ನೀರಾವರಿ",
            "ಡೀಸೆಲ್ ಪಂಪ್ ಸಬ್ಸಿಡಿ", "ಸೌರ ನೀರಾವರಿ ಪಂಪ್ ಯೋಜನೆ", "ಬೋರ್‌ವೆಲ್ ಸೋಲಾರ್ ಪಂಪ್", "ಸೌರ"
        ],
        "synonyms_te": [
            "సోలార్ పంప్", "పీఎం కుసుమ్ కాంపోనెంట్ బి", "సౌర వ్యవసాయ పంపు", "సాగునీటి పంపు",
            "డీజిల్ పంపు సబ్సిడీ", "సౌర నీటిపారుదల పథకం", "బోరుబావి సోలార్ పంపు", "సౌర"
        ]
    },
    "apy": {
        "keywords": [
            "apy", "atal", "pension", "yojana", "pfrda", "unorganised", "retirement",
            "1000", "2000", "3000", "4000", "5000", "monthly pension", "savings bank"
        ],
        "synonyms_en": [
            "atal pension yojana", "unorganised sector pension", "old age pension scheme",
            "monthly guaranteed pension", "pfrda pension", "retirement savings"
        ],
        "synonyms_hi": [
            "अटल पेंशन योजना", "अटल पेंशन", "पेंशन", "मासिक पेंशन", "बुढ़ापा पेंशन",
            "असंगठित क्षेत्र पेंशन", "पीएफआरडीए पेंशन", "सेवानिवृत्ति बचत"
        ],
        "synonyms_kn": [
            "ಅಟಲ್ ಪಿಂಚಣಿ ಯೋಜನೆ", "ಅಟಲ್ ಪಿಂಚಣಿ", "ಪಿಂಚಣಿ", "ಮಾಸಿಕ ಪಿಂಚಣಿ", "ವೃದ್ಧಾಪ್ಯ ಪಿಂಚಣಿ",
            "ಅಸಂಘಟಿತ ವಲಯದ ಪಿಂಚಣಿ", "ನಿವೃತ್ತಿ ಉಳಿತಾಯ"
        ],
        "synonyms_te": [
            "అటల్ పెన్షన్ యోజన", "అటల్ పెన్షన్", "పెన్షన్", "నెలవారీ పెన్షన్", "వృద్ధాప్య పింఛను",
            "అసంఘటిత రంగ పెన్షన్", "రిటైర్మెంట్ పొదుపు"
        ]
    },
    "pmjjby": {
        "keywords": [
            "pmjjby", "jeevan", "jyoti", "bima", "life insurance", "term insurance",
            "200000", "2 lakh", "436", "death benefit", "nominee", "auto debit"
        ],
        "synonyms_en": [
            "pradhan mantri jeevan jyoti bima yojana", "term life insurance", "death insurance",
            "2 lakh life cover", "bank life insurance", "pmjjby scheme"
        ],
        "synonyms_hi": [
            "जीवन ज्योति बीमा", "प्रधानमंत्री जीवन ज्योति बीमा योजना", "जीवन बीमा",
            "मियादी जीवन बीमा", "2 लाख मृत्यु लाभ", "436 प्रीमियम"
        ],
        "synonyms_kn": [
            "ಜೀವನ್ ಜ್ಯೋತಿ ಬಿಮಾ", "ಪ್ರಧಾನಮಂತ್ರಿ ಜೀವನ್ ಜ್ಯೋತಿ ಬಿಮಾ ಯೋಜನೆ", "ಜೀವ ವಿಮೆ",
            "ಅವಧಿ ಜೀವ ವಿಮೆ", "2 ಲಕ್ಷ ಪರಿಹಾರ", "436 ಪ್ರೀಮಿಯಂ"
        ],
        "synonyms_te": [
            "జీవన్ జ్యోతి బీమా", "ప్రధానమంత్రి జీవన్ జ్యోతి బీమా యోజన", "జీవిత బీమా",
            "టర్మ్ ఇన్సూరెన్స్", "2 లక్షల జీవిత బీమా", "436 ప్రీమియం"
        ]
    },
    "pmsby": {
        "keywords": [
            "pmsby", "suraksha", "bima", "accidental insurance", "accident cover",
            "disability cover", "200000", "2 lakh", "20", "rupees 20", "auto debit"
        ],
        "synonyms_en": [
            "pradhan mantri suraksha bima yojana", "accident insurance", "accidental death cover",
            "permanent disability cover", "20 rupees bima", "pmsby insurance"
        ],
        "synonyms_hi": [
            "सुरक्षा बीमा योजना", "प्रधानमंत्री सुरक्षा बीमा योजना", "दुर्घटना बीमा",
            "अकस्मात मृत्यु कवर", "दिव्यांगता बीमा", "20 रुपये बीमा"
        ],
        "synonyms_kn": [
            "ಸುರಕ್ಷಾ ಬಿಮಾ ಯೋಜನೆ", "ಪ್ರಧಾನಮಂತ್ರಿ ಸುರಕ್ಷಾ ಬಿಮಾ ಯೋಜನೆ", "ಅಪಘಾತ ವಿಮೆ",
            "ಅಪಘಾತ ಮರಣ ಪರಿಹಾರ", "ಅಂಗವೈಕಲ್ಯ ವಿಮೆ", "20 ರೂಪಾಯಿ ವಿಮೆ"
        ],
        "synonyms_te": [
            "సురక్ష బీమా యోజన", "ప్రధానమంత్రి సురక్ష బీమా యోజన", "ప్రమాద బీమా",
            "ప్రమాదవశాత్తు మరణ పరిహారం", "అంగవైకల్యం బీమా", "20 రూపాయల బీమా"
        ]
    },
    "pm-mudra": {
        "keywords": [
            "mudra", "pmmy", "shishu", "kishore", "tarun", "micro enterprise loan",
            "small business loan", "50000", "5 lakh", "10 lakh", "20 lakh", "collateral free"
        ],
        "synonyms_en": [
            "pradhan mantri mudra yojana", "mudra loan", "shishu mudra loan",
            "kishore mudra loan", "tarun mudra loan", "small business collateral free loan"
        ],
        "synonyms_hi": [
            "मुद्रा योजना", "प्रधानमंत्री मुद्रा योजना", "मुद्रा लोन", "शिशु लोन",
            "किशोर लोन", "तरुण लोन", "लघु उद्योग ऋण", "बिना गारंटी व्यापार ऋण"
        ],
        "synonyms_kn": [
            "ಮುದ್ರಾ ಯೋಜನೆ", "ಪ್ರಧಾನಮಂತ್ರಿ ಮುದ್ರಾ ಯೋಜನೆ", "ಮುದ್ರಾ ಸಾಲ", "ಶಿಶು ಸಾಲ",
            "ಕಿಶೋರ್ ಸಾಲ", "ತರುಣ್ ಸಾಲ", "ಸಣ್ಣ ವ್ಯಾಪಾರ ಸಾಲ", "ಅಡಮಾನ ರಹಿತ ಸಾಲ"
        ],
        "synonyms_te": [
            "ముద్రా యోజన", "ప్రధానమంత్రి ముద్రా యోజన", "ముద్రా రుణం", "శిశు రుణం",
            "కిశోర్ రుణం", "తరుణ్ రుణం", "చిన్న వ్యాపార రుణం", "పూచీకత్తు లేని రుణం"
        ]
    },
    "ssy": {
        "keywords": [
            "ssy", "sukanya", "samriddhi", "girl child", "daughter", "post office savings",
            "beti bachao", "80c tax exemption", "high interest", "21 years maturity"
        ],
        "synonyms_en": [
            "sukanya samriddhi yojana", "girl child savings scheme", "daughter education fund",
            "post office girl child account", "ssy deposit", "tax free daughter scheme"
        ],
        "synonyms_hi": [
            "सुकन्या समृद्धि योजना", "सुकन्या योजना", "बेटी बचत योजना", "बालिका खाता",
            "डाकघर सुकन्या", "बेटी पढ़ाई विवाह योजना", "उच्च ब्याज बचत"
        ],
        "synonyms_kn": [
            "ಸುಕನ್ಯಾ ಸಮೃದ್ಧಿ ಯೋಜನೆ", "ಸುಕನ್ಯಾ ಯೋಜನೆ", "ಹೆಣ್ಣು ಮಗುವಿನ ಉಳಿತಾಯ ಯೋಜನೆ",
            "ಅಂಚೆ ಕಚೇರಿ ಸುಕನ್ಯಾ ಖಾತೆ", "ಹೆಣ್ಣು ಮಗುವಿನ ಭವಿಷ್ಯ ನಿಧಿ"
        ],
        "synonyms_te": [
            "సుకున్య సమృద్ధి యోజన", "సుకున్య పథకం", "ఆడపిల్ల పొదుపు పథకం",
            "పోస్ట్ ఆఫీస్ సుకున్య ఖాతా", "ఆడపిల్లల భవిష్యత్ నిధి"
        ]
    },
    "pm-vishwakarma": {
        "keywords": [
            "vishwakarma", "artisan", "craftsperson", "traditional trade", "carpenter",
            "blacksmith", "potter", "weaver", "barber", "cobbler", "toolkit 15000",
            "concessional loan 3 lakh", "5 percent interest", "pm vishwakarma"
        ],
        "synonyms_en": [
            "pm vishwakarma yojana", "artisan support scheme", "traditional craftsperson loan",
            "tool kit incentive ₹15000", "collateral free artisan credit", "carpenter blacksmith scheme"
        ],
        "synonyms_hi": [
            "विश्वकर्मा योजना", "पीएम विश्वकर्मा", "कारीगर योजना", "शिल्पकार योजना",
            "बढ़ई लोहार कुम्हार दर्जी", "टूलकिट 15000", "सस्ता कारीगर ऋण"
        ],
        "synonyms_kn": [
            "ವಿಶ್ವಕರ್ಮ ಯೋಜನೆ", "ಪಿಎಂ ವಿಶ್ವಕರ್ಮ", "ಕುಶಲಕರ್ಮಿ ಯೋಜನೆ", "ಸಾಂಪ್ರದಾಯಿಕ ಕಸುಬುದಾರರು",
            "ಬಡಗಿ ಕಮ್ಮಾರ ಕುಂಬಾರ", "ಟೂಲ್‌ಕಿಟ್ 15000", "ಕಡಿಮೆ ಬಡ್ಡಿ ಕುಶಲಕರ್ಮಿ ಸಾಲ"
        ],
        "synonyms_te": [
            "విశ్వకర్మ యోజన", "పీఎం విశ్వకర్మ", "చేతివృత్తుల పథకం", "కుమ్మరి కమ్మరి వడ్రంగి",
            "సాంప్రదాయ కళాకారులు", "టూల్‌కిట్ 15000", "రాయితీ చేతివృత్తుల రుణం"
        ]
    },
    "day-nrlm": {
        "keywords": [
            "nrlm", "day nrlm", "aajeevika", "shg", "self help group", "women shg",
            "revolving fund", "community investment fund", "cif", "collateral free 20 lakh",
            "rural livelihoods", "7 percent interest subvention"
        ],
        "synonyms_en": [
            "deendayal antyodaya yojana nrlm", "national rural livelihoods mission",
            "women self help group loan", "shg revolving fund", "rural women livelihood"
        ],
        "synonyms_hi": [
            "दीनदयाल अंत्योदय योजना", "राष्ट्रीय ग्रामीण आजीविका मिशन", "आजीविका मिशन",
            "महिला स्वयं सहायता समूह", "एसएचजी ऋण", "रिवॉल्विंग फंड", "सस्ता समूह ऋण"
        ],
        "synonyms_kn": [
            "ದೀನದಯಾಳ್ ಅಂತ್ಯೋದಯ ಯೋಜನೆ", "ರಾಷ್ಟ್ರೀಯ ಗ್ರಾಮೀಣ ಜೀವನೋಪಾಯ ಮಿಷನ್", "ಆಜೀವಿಕಾ",
            "ಸ್ವಸಹಾಯ ಸಂಘ", "ಮಹಿಳಾ ಸ್ವಸಹಾಯ ಸಂಘಗಳ ಸಾಲ", "ಆವರ್ತಕ ನಿಧಿ"
        ],
        "synonyms_te": [
            "దీనదయాళ్ అంత్యోదయ యోజన", "జాతీయ గ్రామీణ జీవనోపాధి మిషన్", "ఆజీవిక",
            "స్వయం సహాయక సంఘం", "మహిళా పొదుపు సంఘాల రుణం", "రివాల్వింగ్ ఫండ్"
        ]
    },
    "stand-up-india": {
        "keywords": [
            "stand up india", "sc st loan", "women entrepreneur", "greenfield enterprise",
            "manufacturing loan", "service sector loan", "10 lakh to 1 crore", "standupmitra"
        ],
        "synonyms_en": [
            "stand-up india scheme", "sc st entrepreneur bank loan", "women business loan up to 1 crore",
            "greenfield venture bank loan", "stand up india collateral loan"
        ],
        "synonyms_hi": [
            "स्टैंड-अप इंडिया", "एससी एसटी उद्यमी ऋण", "महिला उद्यमी बैंक लोन",
            "10 लाख से 1 करोड़ लोन", "नया उद्योग ऋण", "स्टैंडअप मित्र"
        ],
        "synonyms_kn": [
            "ಸ್ಟ್ಯಾಂಡ್‌-ಅಪ್ ಇಂಡಿಯಾ", "ಪರಿಶಿಷ್ಟ ಜಾತಿ ಪರಿಶಿಷ್ಟ ಪಂಗಡ ಸಾಲ", "ಮಹಿಳಾ ಉದ್ಯಮಿ ಸಾಲ",
            "10 ಲಕ್ಷದಿಂದ 1 ಕೋಟಿ ಸಾಲ", "ಹೊಸ ಉದ್ದಿಮೆ ಸಾಲ"
        ],
        "synonyms_te": [
            "స్టాండ్-అప్ ఇండియా", "ఎస్సీ ఎస్టీ వ్యాపార రుణం", "మహిళా వ్యవస్థాపక రుణం",
            "10 లక్షల నుండి 1 కోటి రుణం", "కొత్త వ్యాపార బ్యాంకు రుణం"
        ]
    },
    "pm-surya-ghar": {
        "keywords": [
            "surya ghar", "muft bijli", "rooftop solar", "solar subsidy", "300 units",
            "free electricity", "grid connected solar", "mnre", "78000 subsidy", "1 kw", "2 kw", "3 kw"
        ],
        "synonyms_en": [
            "pm surya ghar muft bijli yojana", "rooftop solar panel subsidy", "free electricity solar scheme",
            "home solar power plant", "grid rooftop solar installation"
        ],
        "synonyms_hi": [
            "पीएम सूर्य घर मुफ्त बिजली योजना", "सूर्य घर योजना", "छत पर सोलर पैनल",
            "300 यूनिट मुफ्त बिजली", "रूफटॉप सोलर सब्सिडी", "सौर ऊर्जा घर"
        ],
        "synonyms_kn": [
            "ಪಿಎಂ ಸೂರ್ಯ ಘರ್ ಮುಫ್ಟ್ ಬಿಜ್ಲಿ ಯೋಜನೆ", "ಸೂರ್ಯ ಘರ್", "ಮನೆ ಮೇಲ್ಛಾವಣಿ ಸೋಲಾರ್",
            "300 ಯೂನಿಟ್ ಉಚಿತ ವಿದ್ಯುತ್", "ರೂಫ್‌ಟಾಪ್ ಸೌರ ಸಬ್ಸಿಡಿ", "ಸೌರ ವಿದ್ಯುತ್"
        ],
        "synonyms_te": [
            "పీఎం సూర్య ఘర్ ఉచిత విద్యుత్ యోజన", "సూర్య ఘర్", "ఇంటి పైకప్పు సౌర విద్యుత్",
            "300 యూనిట్ల ఉచిత కరెంట్", "రూఫ్‌టాప్ సోలార్ సబ్సిడీ", "సౌర విద్యుత్ ప్లాంట్"
        ]
    },
    "pmuy": {
        "keywords": [
            "pmuy", "ujjwala", "lpg connection", "gas cylinder", "clean cooking fuel",
            "bpl women gas", "free gas cylinder", "pmuy 2.0", "oil marketing companies"
        ],
        "synonyms_en": [
            "pradhan mantri ujjwala yojana", "ujjwala gas scheme", "free lpg connection",
            "women gas cylinder scheme", "clean cooking lpg subsidy"
        ],
        "synonyms_hi": [
            "उज्ज्वला योजना", "प्रधानमंत्री उज्ज्वला योजना", "मुफ्त गैस कनेक्शन",
            "एलपीजी गैस सिलेंडर", "रसोई गैस चूल्हा", "गरीब महिला गैस योजना"
        ],
        "synonyms_kn": [
            "ಉಜ್ವಲ ಯೋಜನೆ", "ಪ್ರಧಾನಮಂತ್ರಿ ಉಜ್ವಲ ಯೋಜನೆ", "ಉಚಿತ ಗ್ಯಾಸ್ ಸಂಪರ್ಕ",
            "ಎಲ್‌ಪಿಜಿ ಸಿಲಿಂಡರ್", "ಮಹಿಳಾ ಗ್ಯಾಸ್ ಯೋಜನೆ", "ಉಚಿತ ಅಡುಗೆ ಅನಿಲ"
        ],
        "synonyms_te": [
            "ఉజ్వల యోజన", "ప్రధానమంత్రి ఉజ్వల యోజన", "ఉచిత గ్యాస్ కనెక్షన్",
            "ఎల్‌పీజీ సిలిండర్", "మహిళా గ్యాస్ పథకం", "ఉచిత వంట గ్యాస్"
        ]
    },
    "kcc": {
        "keywords": [
            "kcc", "kisan credit card", "crop loan", "short term agri credit", "interest subvention",
            "3 lakh limit", "4 percent interest", "ahdf", "animal husbandry dairy fisheries", "fasal rin"
        ],
        "synonyms_en": [
            "kisan credit card scheme", "crop loan card", "short term agricultural credit",
            "subsidized farm loan 4 percent", "dairy fisheries credit card"
        ],
        "synonyms_hi": [
            "किसान क्रेडिट कार्ड", "केसीसी", "फसल ऋण", "अल्पकालिक कृषि ऋण",
            "4 प्रतिशत ब्याज दर लोन", "पशुपालन डेयरी ऋण", "खेती कार्ड"
        ],
        "synonyms_kn": [
            "ಕಿಸಾನ್ ಕ್ರೆಡಿಟ್ ಕಾರ್ಡ್", "ಕೆಸಿಸಿ", "ಬೆಳೆ ಸಾಲ", "ಅಲ್ಪಾವಧಿ ಕೃಷಿ ಸಾಲ",
            "4 ಪ್ರತಿಶತ ಬಡ್ಡಿದರ ಸಾಲ", "ಪಶುಸಂಗೋಪನೆ ಡೇರಿ ಸಾಲ"
        ],
        "synonyms_te": [
            "కిసాన్ క్రెడిట్ కార్డు", "కేసీసీ", "పంట రుణం", "స్వల్పకాలిక వ్యవసాయ రుణం",
            "4 శాతం వడ్డీ రుణం", "పశుసంవర్ధక డెయిరీ రుణం"
        ]
    },
    "pm-sym": {
        "keywords": [
            "pm-sym", "shram yogi", "maan-dhan", "unorganised worker pension", "3000 pension",
            "street vendor rickshaw driver", "construction worker", "domestic maid", "csc enrollment"
        ],
        "synonyms_en": [
            "pradhan mantri shram yogi maan-dhan", "unorganised worker pension",
            "monthly 3000 old age pension", "labour pension scheme", "informal worker social security"
        ],
        "synonyms_hi": [
            "श्रम योगी मान-धन", "पीएम श्रम योगी", "असंगठित मजदूर पेंशन",
            "मासिक 3000 पेंशन", "रिक्शा चालक निर्माण मजदूर पेंशन", "मजदूर सामाजिक सुरक्षा"
        ],
        "synonyms_kn": [
            "ಶ್ರಮ ಯೋಗಿ ಮಾನ್‌-ಧನ್", "ಪಿಎಂ ಶ್ರಮ ಯೋಗಿ", "ಅಸಂಘಟಿತ ಕಾರ್ಮಿಕರ ಪಿಂಚಣಿ",
            "ಮಾಸಿಕ 3000 ಪಿಂಚಣಿ", "ಕಟ್ಟಡ ಕಾರ್ಮಿಕ ಆಟೋ ಚಾಲಕ ಪಿಂಚಣಿ"
        ],
        "synonyms_te": [
            "శ్రమ యోగి మాన్-ధన్", "పీఎం శ్రమ యోగి", "అసంఘటిత కార్మికుల పెన్షన్",
            "నెలవారీ 3000 పెన్షన్", "భవన నిర్మాణ కార్మికుల పెన్షన్"
        ]
    },
    "nsap-ignoaps": {
        "keywords": [
            "nsap", "ignoaps", "indira gandhi national old age pension", "destitute elderly",
            "bpl pension", "senior citizen 60 plus", "social assistance program", "rural development"
        ],
        "synonyms_en": [
            "indira gandhi national old age pension scheme", "nsap old age pension",
            "bpl elderly assistance", "destitute senior citizen pension", "central old age grant"
        ],
        "synonyms_hi": [
            "इंदिरा गांधी राष्ट्रीय वृद्धावस्था पेंशन", "वृद्धावस्था पेंशन", "बीपीएल वृद्ध पेंशन",
            "बुजुर्ग सहायता", "एनएसएपी वृद्धावस्था सहायता"
        ],
        "synonyms_kn": [
            "ಇಂದಿರಾ ಗಾಂಧಿ ರಾಷ್ಟ್ರೀಯ ವೃದ್ಧಾಪ್ಯ ಪಿಂಚಣಿ", "ವೃದ್ಧಾಪ್ಯ ಪಿಂಚಣಿ", "ಬಿಪಿಎಲ್ ಹಿರಿಯ ನಾಗರಿಕರ ಪಿಂಚಣಿ",
            "ಅಸಹಾಯಕ ಹಿರಿಯರ ಮಾಸಿಕ ನೆರವು"
        ],
        "synonyms_te": [
            "ఇందిరా గాంధీ జాతీయ వృద్ధాప్య పింఛను", "వృద్ధాప్య పెన్షన్", "బీపీఎల్ వృద్ధుల సహాయం",
            "నిరుపేద వృద్ధుల నెలవారీ సహాయం"
        ]
    },
    "pmjdy": {
        "keywords": [
            "pmjdy", "jan dhan", "zero balance account", "rupay card", "financial inclusion",
            "bank account", "overdraft 10000", "200000 accidental cover", "direct benefit transfer"
        ],
        "synonyms_en": [
            "pradhan mantri jan dhan yojana", "jan dhan bank account", "zero balance savings account",
            "basic savings bank deposit account", "rupay debit card accident insurance"
        ],
        "synonyms_hi": [
            "जन धन योजना", "प्रधानमंत्री जन धन योजना", "जीरो बैलेंस खाता",
            "जन धन बैंक खाता", "रुपे डेबिट कार्ड", "ओवरड्राफ्ट 10000"
        ],
        "synonyms_kn": [
            "ಜನ್ ಧನ್ ಯೋಜನೆ", "ಪ್ರಧಾನಮಂತ್ರಿ ಜನ್ ಧನ್ ಯೋಜನೆ", "ಶೂನ್ಯ ಬ್ಯಾಲೆನ್ಸ್ ಖಾತೆ",
            "ಜನ್ ಧನ್ ಬ್ಯಾಂಕ್ ಖಾತೆ", "ರೂಪೇ ಡೆಬಿಟ್ ಕಾರ್ಡ್", "ಓವರ್‌ಡ್ರಾಫ್ಟ್ 10000"
        ],
        "synonyms_te": [
            "జన్ ధన్ యోజన", "ప్రధానమంత్రి జన్ ధన్ యోజన", "జీరో బ్యాలెన్స్ అకౌంట్",
            "జన్ ధన్ బ్యాంకు ఖాతా", "రూపే డెబిట్ కార్డు", "ఓవర్‌డ్రాఫ్ట్ 10000"
        ]
    }
}

# Automatically generate the combined synonyms list for each scheme
for _scheme_id, _meta in SCHEME_SEARCH_METADATA.items():
    _combined_synonyms: List[str] = []
    for _lang_key in ("synonyms_en", "synonyms_hi", "synonyms_kn", "synonyms_te"):
        _combined_synonyms.extend(_meta.get(_lang_key, []))
    _meta["synonyms"] = _combined_synonyms

# Common colloquial user queries mapped to intent expansion terms
COMMON_QUERY_EXPANSIONS: Dict[str, List[str]] = {
    # Agriculture / Farming
    "farmer": ["farmer", "kisan", "agriculture", "cultivator"],
    "farmers": ["farmer", "kisan", "agriculture"],
    "kisan": ["kisan", "farmer", "agriculture", "samman"],
    "agriculture": ["agriculture", "farmer", "kisan", "farming"],
    "krishi": ["agriculture", "kisan", "farmer"],
    "kheti": ["agriculture", "kisan", "farmer"],
    "fasal": ["agriculture", "crop"],
    "land": ["landholding", "cultivable"],
    "cultivable": ["landholding", "agriculture"],
    "రైతు": ["రైతు", "రైతులు", "వ్యవసాయం", "farmer"],
    "రైతులు": ["రైతు", "వ్యవసాయం"],
    "వ్యవసాయం": ["వ్యవసాయం", "రైతు"],
    "ರೈತ": ["ರೈತ", "ರೈತರು", "ಕೃಷಿ", "farmer"],
    "ರೈತರು": ["ರೈತ", "ಕೃಷಿ"],
    "ಕೃಷಿ": ["ಕೃಷಿ", "ರೈತ"],
    "किसान": ["किसान", "खेती", "कृषि", "farmer"],
    "खेती": ["खेती", "किसान", "कृषि"],

    # Health & Medical
    "health": ["health", "insurance", "ayushman", "swasthya"],
    "hospital": ["hospital", "treatment", "ayushman", "medical"],
    "doctor": ["medical", "treatment", "hospital"],
    "medical": ["medical", "treatment", "health", "hospital"],
    "medicine": ["medical", "treatment"],
    "illness": ["treatment", "medical", "hospital"],
    "treatment": ["treatment", "hospital", "cashless"],
    "surgery": ["surgery", "treatment", "hospital"],
    "operation": ["surgery", "treatment", "hospital"],
    "bimari": ["treatment", "hospital", "swasthya"],
    "ilaj": ["treatment", "hospital", "swasthya"],
    "swasthya": ["swasthya", "health", "ayushman"],
    "aarogya": ["aarogya", "health", "ayushman"],
    "arogya": ["arogya", "health", "ayushman"],
    "aspathre": ["hospital", "aspathre"],
    "asupatri": ["hospital", "asupatri"],
    "chikitsa": ["treatment", "chikitsa"],
    "ಆರೋಗ್ಯ": ["ಆರೋಗ್ಯ", "ಆಸ್ಪತ್ರೆ", "ಚಿಕಿತ್ಸೆ"],
    "ಆಸ್ಪತ್ರೆ": ["ಆಸ್ಪತ್ರೆ", "ಚಿಕಿತ್ಸೆ"],
    "ಚಿಕಿತ್ಸೆ": ["ಚಿಕಿತ್ಸೆ", "ಆಸ್ಪತ್ರೆ"],
    "ఆరోగ్యం": ["ఆరోగ్యం", "ఆసుపత్రి", "చికిత్స"],
    "ఆసుపత్రి": ["ఆసుపత్రి", "చికిత్స"],
    "చికిత్స": ["చికిత్స", "ఆసుపత్రి"],
    "आयुष्मान": ["आयुष्मान", "इलाज", "अस्पताल"],
    "अस्पताल": ["अस्पताल", "इलाज", "स्वास्थ्य"],
    "इलाज": ["इलाज", "अस्पताल", "स्वास्थ्य"],

    # Housing & Shelter
    "house": ["housing", "house", "pucca", "awas"],
    "home": ["housing", "home", "awas"],
    "housing": ["housing", "house", "pucca", "shelter"],
    "shelter": ["shelter", "housing", "house"],
    "pucca": ["pucca", "house", "awas"],
    "kutcha": ["kutcha", "house", "awas"],
    "awas": ["awas", "housing", "house", "makan"],
    "ghar": ["ghar", "makan", "awas", "house"],
    "makan": ["makan", "ghar", "awas", "house"],
    "mane": ["mane", "vasati", "awas"],
    "illu": ["illu", "gruham", "awas"],
    "ಗ್ರಾಮೀಣ": ["ಗ್ರಾಮೀಣ", "ವಸತಿ", "ಮನೆ"],
    "ಮನೆ": ["ಮನೆ", "ವಸತಿ", "ಆವಾಸ್"],
    "ವಸತಿ": ["ವಸತಿ", "ಮನೆ", "ಆವಾಸ್"],
    "ఇల్లు": ["ఇల్లు", "గృహం", "ఆవాస్"],
    "గృహం": ["గృహం", "ఇల్లు", "ఆవాస్"],
    "ఆవాస్": ["ఆవాస్", "ఇల్లు", "గృహం"],
    "आवास": ["आवास", "मकान", "घर"],
    "घर": ["घर", "मकान", "आवास"],
    "मकान": ["मकान", "घर", "आवास"],

    # Street Vendors & Microloans
    "vendor": ["vendor", "street vendor", "hawker", "thela", "svanidhi"],
    "vendors": ["vendor", "street vendor", "hawker", "svanidhi"],
    "street": ["street vendor", "vendor", "svanidhi"],
    "hawker": ["hawker", "street vendor", "thela", "svanidhi"],
    "thela": ["thela", "rehri", "vendor", "svanidhi"],
    "rehri": ["rehri", "thela", "vendor", "svanidhi"],
    "patri": ["patri", "thela", "vendor"],
    "shop": ["vendor", "shopkeeper", "retail"],
    "shopkeeper": ["vendor", "shopkeeper"],
    "loan": ["loan", "working capital", "credit"],
    "credit": ["credit", "loan", "micro credit"],
    "vyapari": ["vyapari", "vendor", "svanidhi"],
    "ಬೀದಿ": ["ಬೀದಿ ವ್ಯಾಪಾರಿ", "ಮಾರಾಟಗಾರ", "ಸ್ವನಿಧಿ"],
    "ವ್ಯಾಪಾರಿ": ["ವ್ಯಾಪಾರಿ", "ಮಾರಾಟಗಾರ", "ಸ್ವನಿಧಿ"],
    "ಮಾರಾಟಗಾರ": ["ಮಾರಾಟಗಾರ", "ಬೀದಿ ವ್ಯಾಪಾರಿ", "ಸ್ವನಿಧಿ"],
    "ಸಾಲ": ["ಸಾಲ", "ಕಿರು ಸಾಲ", "ಸ್ವನಿಧಿ"],
    "చిరువ్యాపారి": ["చిరువ్యాపారి", "విక్రేత", "స్వనిధి"],
    "రుణం": ["రుణం", "చిరు రుణం", "స్వనిధి"],
    "వ్యాపారం": ["వ్యాపారం", "చిరువ్యాపారి", "స్వనిధి"],
    "ठेला": ["ठेला", "फेरीवाला", "विक्रेता", "स्वनिधि"],
    "फेरीवाला": ["फेरीवाला", "ठेला", "विक्रेता", "स्वनिधि"],
    "दुकानदार": ["दुकानदार", "विक्रेता", "स्वनिधि"],
    "विक्रेता": ["विक्रेता", "फेरीवाला", "ठेला", "स्वनिधि"],
    "ऋण": ["ऋण", "कार्यशील पूंजी", "स्वनिधि"],

    # Pension & Senior Citizens
    "pension": ["pension", "old age", "maandhan"],
    "old age": ["old age", "pension", "senior citizen"],
    "senior": ["senior citizen", "old age"],
    "senior citizen": ["senior citizen", "old age"],
    "maandhan": ["maandhan", "pension"],
    "mandhan": ["maandhan", "pension"],
    "vriddhapya": ["vriddhapya", "pension"],
    "ವೃದ್ಧಾಪ್ಯ": ["ವೃದ್ಧಾಪ್ಯ", "ಪಿಂಚಣಿ"],
    "ಪಿಂಚಣಿ": ["ಪಿಂಚಣಿ", "ವೃದ್ಧಾಪ್ಯ ವೇತನ"],
    "ವೃದ್ಧಾಪ್ಯ ವೇತನ": ["ವೃದ್ಧಾಪ್ಯ ವೇತನ", "ಪಿಂಚಣಿ"],
    "వృద్ధాప్య": ["వృద్ధాప్య", "పింఛను"],
    "పెన్షన్": ["పెన్షన్", "పింఛను"],
    "పింఛను": ["పింఛను", "వృద్ధాప్య పింఛను"],
    "पेंशन": ["पेंशन", "वृद्धावस्था"],
    "वृद्धावस्था": ["वृद्धावस्था", "पेंशन"],

    # Maternity & Pregnancy
    "pregnant": ["pregnant", "pregnancy", "maternity", "mother"],
    "pregnancy": ["pregnancy", "maternity", "pregnant"],
    "maternity": ["maternity", "pregnant", "mother", "vandana"],
    "mother": ["mother", "maternity", "lactating"],
    "delivery": ["childbirth", "maternity", "delivery"],
    "childbirth": ["childbirth", "maternity", "delivery"],
    "baby": ["childbirth", "mother"],
    "lactating": ["lactating", "mother", "maternity"],
    "garbh": ["garbh", "pregnant"],
    "prasav": ["prasav", "childbirth"],
    "anc": ["anc", "antenatal", "mcp"],
    "mcp": ["mcp", "anc"],
    "ಗರ್ಭಿಣಿ": ["ಗರ್ಭಿಣಿ", "ಮಾತೃತ್ವ", "ಹೆರಿಗೆ"],
    "ಹೆರಿಗೆ": ["ಹೆರಿಗೆ", "ಮಾತೃತ್ವ"],
    "ತಾಯಿ": ["ತಾಯಿ", "ಗರ್ಭಿಣಿ", "ಮಾತೃತ್ವ"],
    "ಗರ್ಭಧಾರಣೆ": ["ಗರ್ಭಧಾರಣೆ", "ಗರ್ಭಿಣಿ"],
    "గర్భిణి": ["గర్భిణి", "ప్రసూతి", "ప్రసవం"],
    "ప్రసవం": ["ప్రసవం", "ప్రసూతి"],
    "తల్లి": ["తల్లి", "గర్భిణి"],
    "గర్భం": ["గర్భం", "గర్భిణి"],
    "गर्भवती": ["गर्भवती", "मातृत्व", "प्रसव"],
    "प्रसव": ["प्रसव", "मातृत्व", "गर्भवती"],
    "मातृत्व": ["मातृत्व", "गर्भवती", "प्रसव"],

    # Solar & Irrigation Pumps
    "solar": ["solar", "pump", "kusum", "irrigation"],
    "pump": ["pump", "solar", "irrigation"],
    "solar pump": ["solar pump", "kusum", "irrigation"],
    "irrigation": ["irrigation", "pump", "solar"],
    "diesel pump": ["diesel pump replacement", "solar pump"],
    "borewell": ["borewell", "pump", "irrigation"],
    "tubewell": ["tubewell", "pump", "irrigation"],
    "sinchai": ["sinchai", "irrigation", "pump"],
    "ಸೌರ": ["ಸೌರ", "ಸೌರ ಪಂಪ್", "ಕುಸುಮ್"],
    "ಸೌರ ಪಂಪ್": ["ಸೌರ ಪಂಪ್", "ನೀರಾವರಿ"],
    "ನೀರಾವರಿ": ["ನೀರಾವರಿ", "ಸೌರ ಪಂಪ್"],
    "ಬೋರ್‌ವೆಲ್": ["ಬೋರ್‌ವೆಲ್", "ಸೌರ ಪಂಪ್"],
    "సోలార్": ["సోలార్", "సోలార్ ಪಂಪ್", "కుసుమ్"],
    "సోలార్ ಪಂಪ್": ["సోలార్ ಪಂప్", "సాగునీరు"],
    "సౌర": ["సౌర", "సోలార్ ಪಂಪ್", "కుసుమ్"],
    "సాగునీరు": ["సాగునీరు", "సోలార్ పంప్"],
    "బోరుబావి": ["బోరుబావి", "సోలార్ పంప్"],
    "सौर": ["सौर", "सौर पंप", "कुसुम"],
    "सौर पंप": ["सौर पंप", "सिंचाई"],
    "सिंचाई": ["सिंचाई", "सौर पंप"],
    "बोरवेल": ["बोरवेल", "सौर पंप"],
}
