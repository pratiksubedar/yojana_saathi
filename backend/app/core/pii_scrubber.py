"""
Yojana Saathi - Non-Destructive PII Redaction Filter
Milestone 6.4: Secondary defense-in-depth scrubber removing Aadhaar, PAN, phone numbers,
and bank details from untrusted text before logging or external LLM transmission.
Anchored strictly to prevent false-positive redaction of legitimate scheme numbers (acres, age, grants).
"""

import re

# Aadhaar: 12-digit grouped pattern starting with 2-9
AADHAAR_PATTERN = re.compile(r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b")

# PAN: 5 uppercase letters, 4 digits, 1 uppercase letter
PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)

# Indian mobile: 10 digits starting with 6-9, optional +91 prefix
PHONE_PATTERN = re.compile(r"\b(?:\+91[\-\s]?)?[6-9]\d{9}\b")

# Bank Account: 9 to 18 digits explicitly preceded or followed by banking terminology
BANK_ACCOUNT_PATTERN = re.compile(
    r"(?i)\b(?:account|acct|a/c|खाता|ಖಾತೆ|ఖాతా)\s*(?:no\.?|num\.?|number|:|=)?\s*(\d{9,18})\b"
)

# OTP / Secret PIN: 4-6 digits near authentication keywords
OTP_PATTERN = re.compile(
    r"(?i)\b(?:otp|one[\-\s]?time[\-\s]?password|pin|passcode)\s*(?:is|:|=)?\s*(\d{4,6})\b"
)

# Demographic patterns for LLM prompt privacy protection
AGE_PATTERN = re.compile(
    r"(?i)\b(?:age\s*(?:is|:|=)?\s*)?(\d{1,2}|1[01]\d)[\s-]*(?:years?[\s-]*old|yr[\s-]*old|years?[\s-]*of[\s-]*age|साल\s*की|साल\s*का|साल|वर्षದ|ವರ್ಷ|సంవత్సరాల|సంవత్సరాలు)\b"
)
AGE_IAM_PATTERN = re.compile(
    r"(?i)\b(?:i\s*am|i'm|मैं|ನಾನು|నేను)\s*(\d{1,2}|1[01]\d)\b"
)

INCOME_PHRASE_PATTERN = re.compile(
    r"(?i)\b(?:annual\s+(?:household\s+)?income|household\s+income|monthly\s+income|annual\s+earning|income|salary|आय|वार्षिक\s*आय|मासिक\s*आय|ಆದಾಯ|ఆదాయం)\s*(?:is|of|:|=)?\s*(?:₹|rs\.?|inr)?\s*[\d,]+(?:\.\d+)?\s*(?:lakhs?|lac|crores?|thousands?|लाख|हजार|ಲಕ್ಷ|లక్ష)?\b"
)
INCOME_CURRENCY_PATTERN = re.compile(
    r"(?i)(?:₹|rs\.?|inr)\s*[\d,]+(?:\.\d+)?\s*(?:lakhs?|lac|crores?|thousands?|लाख|हजार|ಲಕ್ಷ|లక్ష)?\b"
)
INCOME_LAKH_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:lakhs?|lac|crores?|लाख|ಲಕ್ಷ|లక్ష)\b",
    re.IGNORECASE,
)

LAND_PATTERN = re.compile(
    r"(?i)\b\d+(?:\.\d+)?\s*(?:hectares?|hectors?|acres?|हेक्टेयर|एकड़|ಹೆಕ್ಟೇರ್|ಎಕರೆ|హెక్టార్లు|ఎకరాలు)(?:\s*(?:of\s+)?(?:cultivable\s+)?(?:land|agri\s+land|agricultural\s+land|भूमि|ಜಮೀನು|భూమి))?\b"
)

OCCUPATION_PATTERN = re.compile(
    r"(?i)\b(?:farmers?|small\s+farmers?|marginal\s+farmers?|street\s+vendors?|vendors?|hawkers?|labourers?|laborers?|agricultural\s+laborers?|daily\s+wagers?|किसान|रैयत|स्ट्रीट\s*वेंडर|विक्रेता|फेरीवाले|मजदूर|श्रमिक|ರೈತರು|ರೈತ|ಬೀದಿ\s*ವ್ಯಾಪಾರಿ|ಕೂಲಿ\s*ಕಾರ್ಮಿಕ|ಕೂಲಿ|రైతులు|రైతు|వీధి\s*వ్యాపారి|కూలీ)\b"
)

LOCATION_PATTERN = re.compile(
    r"(?i)\b(?:karnataka|maharashtra|uttar\s+pradesh|madhya\s+pradesh|tamil\s+nadu|andhra\s+pradesh|telangana|kerala|gujarat|rajasthan|bihar|west\s+bengal|punjab|haryana|odisha|assam|tumakuru|bengaluru|bangalore|delhi|mumbai|कर्नाटक|महाराष्ट्र|उत्तर\s+प्रदेश|मध्य\s+प्रदेश|तमिलनाडु|आंध्र\s+प्रदेश|तेलंगाना|केरल|गुजरात|राजस्थान|बिहार|पश्चिम\s+बंगाल|पंजाब|हरियाणा|उड़ीसा|असम|तुमकुर|ಬೆಂಗಳೂರು|ಕರ್ನಾಟಕ|ಕರ್ನಾಟಕದ|ಕರ್ನಾಟಕದಲ್ಲಿ|ತುಮಕೂರು|ఆంధ్రప్రదేశ్|తెలంగాణ|హైదరాబాద్|తుమకూరు)\b"
)

GENDER_PATTERN = re.compile(
    r"(?i)\b(?:woman|women|female|females|girl|girls|lady|ladies|man|men|male|males|boy|boys|महिलाएं?|महिला|स्त्री|औरत|पुरुष|मर्द|महिಳೆಯರು|ಮಹಿಳೆ|ಹೆಣ್ಣು|ಪುರುಷ|ಗಂಡು|మహిళలు|మహిళ|స్త్రీ|పురుషుడు|మగ)\b"
)

PREGNANT_PATTERN = re.compile(
    r"(?i)\b(?:pregnant|lactating|expecting\s+mother|lactating\s+mother|गर्भवती|धात्री|स्तनपान\s+कराने\s+वाली|ಗರ್ಭಿಣಿ|ಹಾಲುಣಿಸುವ\s+ತಾಯಿ|గర్భిణీ|పాలిచ్చే\s+తల్లి)\b"
)

CATEGORY_PATTERN = re.compile(
    r"(?i)\b(?:sc|st|obc|general\s+category|ews|अनुसूचित\s+जाति|अनुसूचित\s+जनजाति|अन्य\s+पिछड़ा\s+वर्ग)\b"
)


def scrub_pii(text: str) -> str:
    """
    Sanitizes citizen inputs by replacing sensitive credentials with explicit redaction tags.
    Preserves legitimate numerical quantities such as land size, age, income, and scheme grants.
    """
    if not text:
        return text

    scrubbed = text

    # Redact Aadhaar
    scrubbed = AADHAAR_PATTERN.sub("[AADHAAR_REDACTED]", scrubbed)

    # Redact PAN
    scrubbed = PAN_PATTERN.sub("[PAN_REDACTED]", scrubbed)

    # Redact Phone numbers
    scrubbed = PHONE_PATTERN.sub("[PHONE_REDACTED]", scrubbed)

    # Redact Bank Accounts
    def _sub_bank(match: re.Match) -> str:
        full_match = match.group(0)
        account_digits = match.group(1)
        return full_match.replace(account_digits, "[BANK_ACCOUNT_REDACTED]")

    scrubbed = BANK_ACCOUNT_PATTERN.sub(_sub_bank, scrubbed)

    # Redact OTP / PIN
    def _sub_otp(match: re.Match) -> str:
        full_match = match.group(0)
        digits = match.group(1)
        return full_match.replace(digits, "[SECRET_REDACTED]")

    scrubbed = OTP_PATTERN.sub(_sub_otp, scrubbed)

    return scrubbed


def mask_demographics_for_llm(
    text: str,
    extracted_attributes: dict = None,
) -> str:
    """
    Sanitizes citizen text before inclusion in any external Gemini prompt (NLU, synthesis, history).
    Preserves conversational intent while replacing personal attributes (age, income, land,
    gender, occupation, location) with semantic tokens ([AGE], [OCCUPATION], [LOCATION], [INCOME], etc.).
    Guarantees that sensitive demographic values never leave the local environment.
    """
    if not text:
        return text

    # 1. Scrub credentials (Aadhaar, PAN, phone, bank account, OTP)
    out = scrub_pii(text)

    # 2. Mask explicit extracted values if provided
    attrs = extracted_attributes or {}
    if attrs.get("state"):
        st = str(attrs["state"]).strip()
        if len(st) > 2:
            out = re.sub(re.escape(st), "[LOCATION]", out, flags=re.IGNORECASE)

    # 3. Mask demographic phrases using patterns
    out = INCOME_PHRASE_PATTERN.sub("[INCOME]", out)
    out = INCOME_CURRENCY_PATTERN.sub("[INCOME]", out)
    out = INCOME_LAKH_PATTERN.sub("[INCOME]", out)
    out = LAND_PATTERN.sub("[LANDHOLDING]", out)
    out = AGE_PATTERN.sub("[AGE]", out)
    out = AGE_IAM_PATTERN.sub(r"[AGE]", out)
    out = OCCUPATION_PATTERN.sub("[OCCUPATION]", out)
    out = LOCATION_PATTERN.sub("[LOCATION]", out)
    out = GENDER_PATTERN.sub("[GENDER]", out)
    out = PREGNANT_PATTERN.sub("[HEALTH_STAGE]", out)
    out = CATEGORY_PATTERN.sub("[CATEGORY]", out)

    # Clean multiple consecutive brackets (e.g. [AGE] [AGE] -> [AGE])
    out = re.sub(r"\[AGE\](?:\s*\[AGE\])+", "[AGE]", out)
    out = re.sub(r"\[INCOME\](?:\s*\[INCOME\])+", "[INCOME]", out)
    out = re.sub(r"\[OCCUPATION\](?:\s*\[OCCUPATION\])+", "[OCCUPATION]", out)

    return out


