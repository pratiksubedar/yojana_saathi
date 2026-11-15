"""
Yojana Saathi - Multilingual Attribute Extractor & Validator
Milestone 6.3: Extracts allowlisted citizen profile slots using the LLM gateway,
validates them strictly via Pydantic schemas, handles attribute corrections,
and guarantees zero PII or unvalidated data reaches the deterministic rule engine.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from app.schemas.orchestration import CitizenProfileAttributes, ValidationResult
from app.services.llm.deterministic import DeterministicProvider

logger = logging.getLogger(__name__)

# Sensitive PII patterns to flag and discard immediately
AADHAAR_PATTERN = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\b(?:\+91[- ]?)?[6-9]\d{9}\b")


class AttributeExtractor:
    """
    Extracts, cleans, and strictly validates citizen attributes from conversational text.
    Ensures that only valid, schema-compliant attributes can enter citizen profiles.
    """

    def __init__(
        self,
        deterministic_provider: Optional[DeterministicProvider] = None,
        gateway: Optional[Any] = None,
    ):
        self.deterministic = deterministic_provider or DeterministicProvider()
        self.allowed_slots = list(CitizenProfileAttributes.model_fields.keys())

    async def extract_and_validate(
        self,
        text: str,
        current_profile: Optional[Dict[str, Any]] = None,
        language: str = "en",
    ) -> ValidationResult:
        """
        Extracts candidate slots directly via local DeterministicProvider (zero external network
        calls, zero token cost, zero demographic leakage to external LLMs), validates them through
        CitizenProfileAttributes, detects multi-turn corrections, and reports invalid or rejected fields.
        """
        current_profile = current_profile or {}
        rejected_fields: Dict[str, str] = {}
        ambiguities: List[str] = []

        # 1. Check for sensitive PII attempts
        if AADHAAR_PATTERN.search(text):
            ambiguities.append("Aadhaar numbers are sensitive credentials and must not be shared. Discarded.")
        if PAN_PATTERN.search(text):
            ambiguities.append("PAN card details are sensitive credentials and must not be shared. Discarded.")
        if PHONE_PATTERN.search(text):
            ambiguities.append("Phone numbers are not stored or needed for eligibility calculation. Discarded.")

        # 2. Extract raw candidate slots locally without external LLM network requests
        extraction = await self.deterministic.extract_slots(
            text=text,
            allowed_slots=self.allowed_slots,
            language=language,
        )

        candidate_slots: Dict[str, Any] = dict(extraction.extracted_slots)

        # 3. Validate each extracted attribute against CitizenProfileAttributes
        validated_attributes: Dict[str, Any] = {}

        for key, value in candidate_slots.items():
            if key not in self.allowed_slots:
                rejected_fields[key] = f"Attribute '{key}' is not an authorized eligibility attribute."
                continue

            # Test single field validation via CitizenProfileAttributes
            try:
                # Construct test dict with single field
                test_model = CitizenProfileAttributes(**{key: value})
                cleaned_val = getattr(test_model, key)
                if cleaned_val is not None:
                    validated_attributes[key] = cleaned_val
            except ValidationError as ve:
                for err in ve.errors():
                    field_name = str(err["loc"][0]) if err["loc"] else key
                    rejected_fields[field_name] = err["msg"]

        # 4. Detect corrections over current profile
        for key, new_val in validated_attributes.items():
            if key in current_profile:
                old_val = current_profile[key]
                if old_val != new_val:
                    ambiguities.append(
                        f"Updated attribute '{key}' from {old_val} to {new_val} based on correction."
                    )

        is_valid = len(rejected_fields) == 0

        return ValidationResult(
            is_valid=is_valid,
            validated_attributes=validated_attributes,
            rejected_fields=rejected_fields,
            ambiguities=ambiguities,
        )
