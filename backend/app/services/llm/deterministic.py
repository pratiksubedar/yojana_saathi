"""
Yojana Saathi - Deterministic LLM Provider
Milestone 6.2: Guaranteed baseline provider operating 100% locally with
zero external network calls, zero API keys, and zero model daemon dependencies.
"""

import asyncio
from datetime import datetime, timezone
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from app.services.llm.base import (
    BaseLLMProvider,
    LLMResponse,
    ProviderStatus,
    ProviderTypeEnum,
    SlotExtractionResponse,
)
from app.services.rule_engine import FIELD_PROMPTS


class DeterministicProvider(BaseLLMProvider):
    """
    Deterministic rule-based fallback provider.
    Guarantees that the assistant never crashes or halts even in air-gapped environments.
    """

    @property
    def provider_type(self) -> ProviderTypeEnum:
        return ProviderTypeEnum.DETERMINISTIC

    @property
    def model_name(self) -> str:
        return "deterministic-rules-v1"

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = None,
    ) -> LLMResponse:
        """
        Generates a deterministic template response.
        If prompt contains RAG context chunks or citations, extracts and synthesizes
        them strictly without fabricating unprovided facts.
        """
        start_time = time.perf_counter()

        lower_prompt = prompt.lower()
        response_text = ""

        is_hi = bool(re.search(r"[\u0900-\u097F]", prompt)) or "hindi" in (system_prompt or "").lower()
        is_kn = bool(re.search(r"[\u0C80-\u0CFF]", prompt)) or "kannada" in (system_prompt or "").lower()
        is_te = bool(re.search(r"[\u0C00-\u0C7F]", prompt)) or "telugu" in (system_prompt or "").lower()

        # 0. Check if this prompt is an Indic translation request
        if "indic language translator" in lower_prompt or "text to translate:" in lower_prompt or "translate the following text" in lower_prompt:
            from app.services.translation_service import translate_assistant_text
            target_code = "hi" if ("hindi" in lower_prompt or is_hi) else ("kn" if ("kannada" in lower_prompt or is_kn) else ("te" if ("telugu" in lower_prompt or is_te) else "en"))
            text_to_trans = prompt
            if "text to translate:" in lower_prompt:
                idx = lower_prompt.find("text to translate:")
                text_to_trans = prompt[idx + len("text to translate:"):].strip()
            translated_result, _ = translate_assistant_text(text_to_trans, target_code)
            return LLMResponse(
                text=translated_result,
                model_used=self.model_name,
                provider="deterministic",
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 1. Scheme Context Present in Prompt
        if "### official sources & provenance" in lower_prompt or "chunk:" in lower_prompt:
            # Context synthesis: extracts verified statements from provided context
            if is_hi:
                response_text = "सत्यापित आधिकारिक रिकॉर्ड के आधार पर, यहाँ प्रमाणिक जानकारी दी गई है:\n\n"
            elif is_kn:
                response_text = "ಪರಿಶೀಲಿಸಿದ ಅಧಿಕೃತ ದಾಖಲೆಗಳ ಆಧಾರದ ಮೇಲೆ, ಇಲ್ಲಿದೆ ಮಾಹಿತಿ:\n\n"
            elif is_te:
                response_text = "ధృవీకరించిన అధికారిక రికార్డుల ఆధారంగా, సమాచారం ఇక్కడ ఉంది:\n\n"
            else:
                response_text = (
                    "Based on the official government scheme guidelines retrieved from verified public records, "
                    "here is the authoritative information:\n\n"
                )
            # Extract bullet points or sentences from prompt context if present
            context_lines = [
                line.strip()
                for line in prompt.split("\n")
                if line.strip().startswith("-") or line.strip().startswith("•")
            ]
            if context_lines:
                response_text += "\n".join(context_lines[:4])
            else:
                if is_hi:
                    response_text += "कृपया विस्तृत शर्तों, आवश्यक दस्तावेजों और आवेदन प्रक्रिया के लिए आधिकारिक स्रोत देखें।"
                elif is_kn:
                    response_text = "ಹೆಚ್ಚಿನ ವಿವರಗಳು ಮತ್ತು ಅರ್ಜಿ ವಿಧಾನಕ್ಕಾಗಿ ಅಧಿಕೃತ ಸರ್ಕಾರಿ ಮೂಲವನ್ನು ನೋಡಿ."
                elif is_te:
                    response_text = "పూర్తి వివరాలు మరియు దరఖాస్తు విధానం కోసం అధికారిక పోర్టల్ చూడండి."
                else:
                    response_text += (
                        "Please refer to the official citations and guidelines below for comprehensive "
                        "terms, required documentation, and application procedures."
                    )
        # 2. Multilingual Greetings & Help
        elif any(w in lower_prompt for w in ["hello", "hi", "namaste", "help", "नमस्ते", "ನಮಸ್ಕಾರ", "నమస్కారం"]):
            if is_hi:
                response_text = (
                    "योजना साथी पर सरकारी योजनाओं के लिए मैं आपकी क्या सहायता कर सकता हूँ? "
                    "आप अपनी पात्रता जांच सकते हैं या योजनाएं खोज सकते हैं।"
                )
            elif is_kn:
                response_text = (
                    "ಯೋಜನೆ ಸಾಥಿಯಲ್ಲಿ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳ ಬಗ್ಗೆ ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ? "
                    "ನಿಮ್ಮ ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಬಹುದು ಅಥವಾ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಬಹುದು."
                )
            elif is_te:
                response_text = (
                    "యోజన సాథిలో ప్రభుత్వ పథకాల గురించి నేను మీకు ఎలా సహాయపడగలను? "
                    "మీ అర్హతను తనిఖీ చేయవచ్చు లేదా పథకాలను శోధించవచ్చు."
                )
            else:
                response_text = (
                    "How can I help you on Yojana Saathi today? "
                    "You can check your eligibility or search for verified government welfare schemes."
                )
        # 3. Fallback Guided Response
        else:
            if is_hi:
                response_text = (
                    "मैंने आपका अनुरोध दर्ज कर लिया है। सटीक पात्रता जांच के लिए कृपया अपना व्यवसाय, "
                    "आयु, कृषि भूमि या राज्य बताएं।"
                )
            elif is_kn:
                response_text = (
                    "ನಿಮ್ಮ ಅರ್ಹತೆಯನ್ನು ನಿಖರವಾಗಿ ಪರಿಶೀಲಿಸಲು ದಯವಿಟ್ಟು ನಿಮ್ಮ ಉದ್ಯೋಗ, ವಯಸ್ಸು ಅಥವಾ ರಾಜ್ಯವನ್ನು ತಿಳಿಸಿ."
                )
            elif is_te:
                response_text = (
                    "ఖచ్చితమైన అర్హత తనిఖీ కోసం దయచేసి మీ వృత్తి, వయస్సు లేదా రాష్ట్రాన్ని తెలపండి."
                )
            else:
                response_text = (
                    "To provide you with precise eligibility assessment and guidance, "
                    "please specify your occupation, landholding size, age, or state of residence."
                )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return LLMResponse(
            text=response_text,
            provider=self.provider_type,
            model=self.model_name,
            tokens_used=len(response_text.split()),
            latency_ms=latency_ms,
            fallback_chain=["deterministic (baseline)"],
        )

    async def extract_slots(
        self,
        text: str,
        allowed_slots: List[str],
        language: str = "en",
    ) -> SlotExtractionResponse:
        """
        Extracts typed profile attributes using deterministic regex and pattern matching
        strictly constrained to allowed_slots. Never extracts or asks for sensitive PII.
        """
        start_time = time.perf_counter()
        extracted: Dict[str, Any] = {}
        clean_text = text.lower()

        # 1. AGE: match numbers near age keywords or explicit years
        if "age" in allowed_slots:
            # Check explicit correction first: "actually, i am 46, not 45" or "46 not 45" or "not 45, i am 46"
            corr_match1 = re.search(r"\b(?:actually\s*,?\s*)?(?:i am|i'm|im|my age is|age is)?\s*(\d{1,3})\s*(?:,\s*)?(?:not|aur nahi)\s*(\d{1,3})\b", clean_text)
            corr_match2 = re.search(r"\b(?:not|nahi)\s*(\d{1,3})\s*(?:,|but|\s*)\s*(?:i am|my age is|actually)?\s*(\d{1,3})\b", clean_text)
            if corr_match1:
                val = int(corr_match1.group(1))
                if 0 <= val <= 120:
                    extracted["age"] = val
            elif corr_match2:
                val = int(corr_match2.group(2))
                if 0 <= val <= 120:
                    extracted["age"] = val
            else:
                age_match = re.search(
                    r"\b(?:age|aged|उम्र|आयु|ವಯಸ್ಸು|వయస్సు)\s*(?:is|of|:|=|hai|ide|undi)?\s*(\d{1,3})\b",
                    clean_text,
                )
                if not age_match:
                    # "turned 45", "turned 45 last month", "became 45"
                    age_match = re.search(r"\b(?:turned|turn|became)\s+(\d{1,3})\b", clean_text)
                if not age_match:
                    # e.g., "42 years old", "25-year-old", "25 years age", "25 yrs", "45 वर्षीय"
                    age_match = re.search(
                        r"(\d{1,3})[\s-]*(?:years?[\s-]*(?:old|of\s*age|age)|year[\s-]*old|yrs?\b|साल|वर्षीय|वर्ष|ವಯಸ್ಸಿನ|ವರ್ಷ|సంవత్సరాల|సంవత్సరాలు)",
                        clean_text,
                    )
                if not age_match:
                    # e.g., "i am 25" (when not followed by hectares/acres/rupees/lakh)
                    age_match = re.search(
                        r"\b(?:i am|i'm|im)\s+(\d{1,2})\b(?!\s*(?:hectare|acre|rs|rupee|lakh|thousand|%|percent))",
                        clean_text,
                    )
                if not age_match:
                    # Standalone number answering age: "45", "45 years"
                    age_match = re.search(r"^\s*(\d{1,3})\s*(?:years?|yrs?|साल|ವರ್ಷ|సంవత్సరాలు)?\s*\.?$", clean_text)
                if age_match:
                    val = int(age_match.group(1))
                    if 0 <= val <= 120:
                        extracted["age"] = val

        # 2. LANDHOLDING & LAND OWNERSHIP: match hectares/hectors or acres, plus explicit yes/no
        if "landholding_hectares" in allowed_slots:
            norm_land_text = clean_text
            for w_num, d_num in [
                ("one", "1"), ("two", "2"), ("three", "3"), ("four", "4"), ("five", "5"),
                ("एक", "1"), ("दो", "2"), ("तीन", "3"), ("ಒಂದು", "1"), ("ಎರಡು", "2"),
                ("ఒక", "1"), ("రెండు", "2")
            ]:
                norm_land_text = re.sub(rf"\b{w_num}\s*(?=acres?|hectares?|एकड़|ಎಕರೆ|ఎకరాలు)", f"{d_num} ", norm_land_text)

            ha_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hectare|hectares|hector|hectors|ha\b|हेक्टेयर|ಹೆಕ್ಟೇರ್|హెక్టార్లు)", norm_land_text)
            if ha_match:
                extracted["landholding_hectares"] = float(ha_match.group(1))
            else:
                acre_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:acre|acres|एकड़|ಎಕರೆ|ఎకరాలు)", norm_land_text)
                if acre_match:
                    acres = float(acre_match.group(1))
                    extracted["landholding_hectares"] = round(acres * 0.404686, 2)

        if "owns_agricultural_land" in allowed_slots:
            if any(p in clean_text for p in ["no land", "don't have land", "do not have land", "do not own land", "don't own land", "don't own agricultural land", "do not own agricultural land", "landless", "जमीन नहीं", "ಭೂಮಿ ಇಲ್ಲ", "భూమి లేదు"]):
                extracted["owns_agricultural_land"] = False
                if "landholding_hectares" in extracted:
                    del extracted["landholding_hectares"]
            elif (
                ("landholding_hectares" in extracted and extracted["landholding_hectares"] > 0)
                or any(p in clean_text for p in ["have land", "own land", "owns land", "have agricultural land", "own agricultural land", "have some land", "own some land", "some land", "of land", "acres of land", "भूमि है", "जमीन है", "ಭೂಮಿ ಇದೆ", "ಜಮೀನು ಇದೆ", "భూమి ఉంది"])
            ):
                extracted["owns_agricultural_land"] = True

        # 3. OCCUPATION
        if "occupation" in allowed_slots:
            if any(w in clean_text for w in ["kisaan", "raitha", "raithu", "farmer", "farming", "agriculture", "किसान", "खेती", "ರೈತ", "ಕೃಷಿ", "రైతు", "వ్యవసాయ"]):
                extracted["occupation"] = "Farmer"
            elif any(w in clean_text for w in ["thela", "vyapari", "street vendor", "vendor", "hawker", "वेंडर", "फेरीवाला", "ಬೀದಿ ವ್ಯಾಪಾರಿ", "వీధి ವ್ಯಾಪಾರಿ"]):
                extracted["occupation"] = "Street Vendor"
            elif any(w in clean_text for w in ["kooli", "mazdoor", "laborer", "labourer", "worker", "मजदूर", "ಕೂಲಿ", "కూలీ"]):
                extracted["occupation"] = "Laborer"

        # 4. HAS_BPL_CARD / RATION CARD
        if "has_bpl_card" in allowed_slots:
            if any(w in clean_text for w in ["have bpl", "bpl card", "ration card", "बीपीएल कार्ड", "राशन कार्ड", "ಬಿಪಿಎಲ್", "ರೇಷನ್", "బిపిఎల్", "రేషన్"]):
                extracted["has_bpl_card"] = True
            elif any(w in clean_text for w in ["no bpl", "no ration card", "बीपीएल नहीं", "ಬಿಪಿಎಲ್ ಇಲ್ಲ", "బిపిఎల్ లేదు"]):
                extracted["has_bpl_card"] = False

        # 5. PAYS_INCOME_TAX (check negation first to avoid substring collision)
        if "pays_income_tax" in allowed_slots:
            if any(w in clean_text for w in ["no income tax", "don't pay", "do not pay", "not paying", "not pay income tax", "आयकर नहीं", "ತೆರಿಗೆ ಇಲ್ಲ", "ಪಾವತಿಸುವುದಿಲ್ಲ", "పన్ను లేదు"]):
                extracted["pays_income_tax"] = False
            elif any(w in clean_text for w in ["pay income tax", "taxpayer", "paying tax", "आयकर दाता", "ತೆರಿಗೆ ಪಾವತಿ", "ఆదాయపు పన్ను"]):
                extracted["pays_income_tax"] = True

        # 6. GENDER
        if "gender" in allowed_slots:
            if re.search(r"\b(?:female|woman)\b", clean_text) or any(w in clean_text for w in ["महिला", "ಮಹಿಳೆ", "మహిళ"]):
                extracted["gender"] = "Female"
            elif re.search(r"\b(?:male|man)\b", clean_text) or any(w in clean_text for w in ["पुरुष", "ಪುರುಷ", "పురుషుడు"]):
                extracted["gender"] = "Male"

        # 7. IS_PREGNANT_OR_LACTATING
        if "is_pregnant_or_lactating" in allowed_slots:
            if any(w in clean_text for w in ["pregnant", "lactating", "pregnancy", "गर्भवती", "ಗರ್ಭಿಣಿ", "గర్భవతి", "గర్భిణీ", "గర్భిణి"]):
                extracted["is_pregnant_or_lactating"] = True

        # 8. ANC_CHECKUPS_COMPLETED
        if "anc_checkups_completed" in allowed_slots:
            anc_match = re.search(r"(\d+)\s*(?:anc|checkup|checkups|एंटीनेटल|ಪರೀಕ್ಷೆ|తనిఖీ)", clean_text)
            if anc_match:
                extracted["anc_checkups_completed"] = int(anc_match.group(1))

        # 9. HOUSEHOLD_MONTHLY_INCOME_INR
        if "household_monthly_income_inr" in allowed_slots:
            inc_match = re.search(r"(?:income|salary|earns?|आय|ಆದಾಯ|ఆదాయం)\s*(?:is|of|:)?\s*(?:₹|rs\.?)?\s*(\d{4,7})\b", clean_text)
            if inc_match:
                extracted["household_monthly_income_inr"] = float(inc_match.group(1))

        # 10. OWNS_MOTORIZED_THREE_OR_FOUR_WHEELER
        if "owns_motorized_three_or_four_wheeler" in allowed_slots:
            if re.search(r"\b(?:car|tractor|truck|four[- ]wheeler|4[- ]wheeler)\b", clean_text) or any(w in clean_text for w in ["कार", "गाड़ी", "ಕಾರು", "కారు"]):
                extracted["owns_motorized_three_or_four_wheeler"] = True
            elif re.search(r"\b(?:no car|no vehicle|no four[- ]wheeler)\b", clean_text) or any(w in clean_text for w in ["दोपहिया", "ದ್ವಿಚಕ್ರ"]):
                # Two-wheelers are exempt under revised PMAY-G guidelines
                extracted["owns_motorized_three_or_four_wheeler"] = False

        # 11. OWNS_UNIRRIGATED_LAND_GTE_5_ACRES
        if "owns_unirrigated_land_gte_5_acres" in allowed_slots:
            if any(w in clean_text for w in ["5 acres or more unirrigated", "5+ acres unirrigated", "5 एकड़ असिंचित"]):
                extracted["owns_unirrigated_land_gte_5_acres"] = True

        # 12. IS_REGULAR_GOVT_EMPLOYEE
        if "is_regular_govt_employee" in allowed_slots:
            if any(w in clean_text for w in ["not a government employee", "not govt employee", "no govt job", "not a govt employee", "not in govt", "सरकारी कर्मचारी नहीं", "ಸರ್ಕಾರಿ ನೌಕರನಲ್ಲ", "ప్రభుత్వ ఉద్యోగి కాదు"]):
                extracted["is_regular_govt_employee"] = False
            elif any(w in clean_text for w in ["government employee", "govt employee", "govt job", "सरकारी कर्मचारी", "ಸರ್ಕಾರಿ ನೌಕರ", "ప్రభుత్వ ఉద్యోగి"]):
                extracted["is_regular_govt_employee"] = True

        # 13. IS_REGISTERED_PROFESSIONAL
        if "is_registered_professional" in allowed_slots:
            if any(w in clean_text for w in ["not a registered professional", "not a professional", "not doctor", "not lawyer", "पंजीकृत पेशेवर नहीं", "ವೃತ್ತಿಪರನಲ್ಲ"]):
                extracted["is_registered_professional"] = False
            elif any(w in clean_text for w in ["registered professional", "practising doctor", "practicing lawyer", "chartered accountant"]):
                extracted["is_registered_professional"] = True

        # 14. IS_INSTITUTIONAL_LANDHOLDER
        if "is_institutional_landholder" in allowed_slots:
            if any(w in clean_text for w in ["not institutional", "own land", "individual land", "personal land", "not in trust", "ಸಂಸ್ಥೆಯ ಭೂಮಿಯಲ್ಲ"]):
                extracted["is_institutional_landholder"] = False
            elif any(w in clean_text for w in ["institutional land", "trust land", "registered under trust"]):
                extracted["is_institutional_landholder"] = True

        # 15. MONTHLY_PENSION_INR
        if "monthly_pension_inr" in allowed_slots:
            if any(w in clean_text for w in ["no pension", "zero pension", "not retired", "0 pension", "ಪಿಂಚಣಿ ಇಲ್ಲ", "పెన్షన్ లేదు"]):
                extracted["monthly_pension_inr"] = 0.0

        # 16. STATE
        if "state" in allowed_slots:
            # Check native scripts first
            if any(w in clean_text for w in ["ಕರ್ನಾಟಕ", "कर्नाटक", "కర్ణాటక"]):
                extracted["state"] = "Karnataka"
            elif any(w in clean_text for w in ["ಆಂಧ್ರ ಪ್ರದೇಶ", "आंध्र प्रदेश", "ఆంధ్రప్రదేశ్"]):
                extracted["state"] = "Andhra Pradesh"
            elif any(w in clean_text for w in ["ತೆಲಂಗಾಣ", "तेलंगाना", "తెలంగాణ"]):
                extracted["state"] = "Telangana"
            elif any(w in clean_text for w in ["ತಮಿಳುನಾಡು", "तमिलनाडु", "తమిళనాడు"]):
                extracted["state"] = "Tamil Nadu"
            elif any(w in clean_text for w in ["ಮಹಾರಾಷ್ಟ್ರ", "महाराष्ट्र", "మహారాష్ట్ర"]):
                extracted["state"] = "Maharashtra"
            elif any(w in clean_text for w in ["ಉತ್ತರ ಪ್ರದೇಶ", "उत्तर प्रदेश", "ఉత్తరప్రదేశ్"]):
                extracted["state"] = "Uttar Pradesh"
            elif any(w in clean_text for w in ["ಬಿಹಾರ", "बिहार", "బీహార్"]):
                extracted["state"] = "Bihar"
            elif any(w in clean_text for w in ["ಕೇರಳ", "केरल", "కేరళ"]):
                extracted["state"] = "Kerala"
            elif any(w in clean_text for w in ["ದೆಹಲಿ", "दिल्ली", "ఢిల్లీ"]):
                extracted["state"] = "Delhi"
            elif any(w in clean_text for w in ["ರಾಜಸ್ಥಾನ", "राजस्थान", "రాజస్థాన్"]):
                extracted["state"] = "Rajasthan"
            elif any(w in clean_text for w in ["ಮಧ್ಯ ಪ್ರದೇಶ", "मध्य प्रदेश", "మధ్యప్రదేశ్"]):
                extracted["state"] = "Madhya Pradesh"
            elif any(w in clean_text for w in ["ಗುಜರಾತ್", "गुजरात", "గుజరాత్"]):
                extracted["state"] = "Gujarat"
            elif any(w in clean_text for w in ["ಪಂಜಾಬ್", "पंजाब", "పంజాబ్"]):
                extracted["state"] = "Punjab"
            elif any(w in clean_text for w in ["ಹರಿಯಾಣ", "हरियाणा", "హర్యానా"]):
                extracted["state"] = "Haryana"
            elif any(w in clean_text for w in ["ಪಶ್ಚಿಮ ಬಂಗಾಳ", "पश्चिम बंगाल", "పశ్చిమ బెంగాల్"]):
                extracted["state"] = "West Bengal"
            elif any(w in clean_text for w in ["ಒಡಿಶಾ", "ओडिशा", "ఒడిశా"]):
                extracted["state"] = "Odisha"
            states_list = [
                "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "delhi", "goa",
                "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka", "kerala",
                "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland",
                "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
                "uttar pradesh", "uttarakhand", "west bengal", "chandigarh", "jammu and kashmir",
                "ladakh", "puducherry",
            ]
            for st in states_list:
                if re.search(rf"\b{re.escape(st)}\b", clean_text):
                    extracted["state"] = st.title()
                    break

        # 17. SOCIAL_CATEGORY
        if "social_category" in allowed_slots:
            if re.search(r"\b(?:sc|scheduled caste)\b", clean_text):
                extracted["social_category"] = "SC"
            elif re.search(r"\b(?:st|scheduled tribe)\b", clean_text):
                extracted["social_category"] = "ST"
            elif re.search(r"\b(?:obc|other backward)\b", clean_text):
                extracted["social_category"] = "OBC"
            elif re.search(r"\b(?:ews|economically weaker)\b", clean_text):
                extracted["social_category"] = "EWS"
            elif re.search(r"\bgeneral category\b", clean_text):
                extracted["social_category"] = "General"

        # 18. ANNUAL_INCOME_INR
        if "annual_income_inr" in allowed_slots:
            clean_num_text = re.sub(r"(\d),(\d)", r"\1\2", clean_text)
            lakh_match = re.search(
                r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*lakhs?\b",
                clean_num_text,
            )
            if lakh_match:
                extracted["annual_income_inr"] = float(lakh_match.group(1)) * 100000.0
            else:
                ann_match = re.search(
                    r"(?:annual\s*(?:household\s*)?income|yearly\s*income|per\s*year)\s*(?:is|of|:)?\s*(?:₹|rs\.?|inr)?\s*(\d{4,8})\b",
                    clean_num_text,
                )
                if ann_match:
                    extracted["annual_income_inr"] = float(ann_match.group(1))

        if "monthly_pension_inr" in allowed_slots and "monthly_pension_inr" not in extracted:
            pension_match = re.search(r"(?:pension|monthly pension)\s*(?:is|of|:)?\s*(?:₹|rs\.?)?\s*(\d{3,6})\b", clean_text)
            if pension_match:
                extracted["monthly_pension_inr"] = float(pension_match.group(1))

        # 16. OWNS_PUCCA_HOUSE
        if "owns_pucca_house" in allowed_slots:
            if any(w in clean_text for w in ["no pucca house", "no permanent house", "kuccha house", "kuchha house", "कच्चा मकान", "पक्का मकान नहीं", "ಪಕ್ಕಾ ಮನೆ ಇಲ್ಲ", "పక్కా ఇల్లు లేదు"]):
                extracted["owns_pucca_house"] = False
            elif any(w in clean_text for w in ["pucca house", "permanent house", "पक्का मकान", "ಪಕ್ಕಾ ಮನೆ", "పక్కా ఇల్లు"]):
                extracted["owns_pucca_house"] = True

        # 17. IS_BANK_DEFAULTER
        if "is_bank_defaulter" in allowed_slots or "has_willful_bank_default" in allowed_slots:
            if any(w in clean_text for w in [
                "no default", "not a defaulter", "never defaulted", "clean credit",
                "no loan default", "no bank default", "clean record", "never default",
                "डिफ़ॉल्ट नहीं", "बकाया नहीं", "ಸುಸ್ತಿದಾರನಲ್ಲ", "ಡಿಫಾಲ್ಟ್ ಇಲ್ಲ", "డిఫాల్ట్ లేదు"
            ]):
                if "is_bank_defaulter" in allowed_slots:
                    extracted["is_bank_defaulter"] = False
                if "has_willful_bank_default" in allowed_slots:
                    extracted["has_willful_bank_default"] = False
            elif any(w in clean_text for w in [
                "bank defaulter", "loan default", "defaulter", "have default", "unpaid default",
                "yes, loan default", "yes loan default", "डिफ़ॉल्ट है", "ಸುಸ್ತಿದಾರ", "ಡಿಫಾಲ್ಟ್ ಇದೆ", "డిఫాల్ట్ ఉంది"
            ]):
                if "is_bank_defaulter" in allowed_slots:
                    extracted["is_bank_defaulter"] = True
                if "has_willful_bank_default" in allowed_slots:
                    extracted["has_willful_bank_default"] = True

        # 18. FARMER_TYPE & KCC ACTIVITY CATEGORY
        if any(slot in allowed_slots for slot in ["farmer_type", "kcc_activity_category", "is_tenant_farmer", "is_allied_activity_worker", "owns_agricultural_land"]):
            if any(w in clean_text for w in ["landowner", "own agricultural land", "owner cultivator", "own land", "yes, landowner", "भूमि मालिक", "ಜಮೀನ್ದಾರ"]):
                if "farmer_type" in allowed_slots:
                    extracted["farmer_type"] = "Landowner"
                if "kcc_activity_category" in allowed_slots:
                    extracted["kcc_activity_category"] = "owner"
                if "owns_agricultural_land" in allowed_slots:
                    extracted["owns_agricultural_land"] = True
            elif any(w in clean_text for w in ["tenant", "sharecropper", "cultivate land as a tenant", "oral lessee", "बटाईदार", "पट्टेदार", "किरायेदार", "ಗೇಣಿದಾರ", "ಪಾಲುದಾರ", "ಕೌಲು", "వాటాదారు"]):
                if "farmer_type" in allowed_slots:
                    extracted["farmer_type"] = "Tenant"
                if "kcc_activity_category" in allowed_slots:
                    extracted["kcc_activity_category"] = "tenant"
                if "is_tenant_farmer" in allowed_slots:
                    extracted["is_tenant_farmer"] = True
            elif any(w in clean_text for w in ["allied", "allied agricultural activity", "animal husbandry", "dairy", "poultry", "fisheries", "pisciculture", "पशुपालन", "डेयरी", "ಪಶುಸಂಗೋಪನೆ", "ಮೀನುಗಾರಿಕೆ", "పాడి", "మత్స్య"]):
                if "farmer_type" in allowed_slots:
                    extracted["farmer_type"] = "Allied"
                if "kcc_activity_category" in allowed_slots:
                    extracted["kcc_activity_category"] = "allied"
                if "is_allied_activity_worker" in allowed_slots:
                    extracted["is_allied_activity_worker"] = True

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return SlotExtractionResponse(
            extracted_slots=extracted,
            confidence=1.0 if extracted else 0.0,
            raw_response=str(extracted),
            provider=self.provider_type,
            latency_ms=latency_ms,
        )

    async def stream_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        """
        Simulates streaming generation by yielding word chunks asynchronously.
        """
        response = await self.generate_text(prompt, system_prompt, max_tokens, temperature)
        words = response.text.split(" ")
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i : i + 3])
            if i + 3 < len(words):
                chunk += " "
            yield chunk
            await asyncio.sleep(0.001)

    async def health_check(self) -> ProviderStatus:
        """
        Always reports healthy without external dependencies.
        """
        return ProviderStatus(
            provider=self.provider_type,
            is_available=True,
            model=self.model_name,
            latency_ms=0.1,
            message="Deterministic baseline operational (100% offline).",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
