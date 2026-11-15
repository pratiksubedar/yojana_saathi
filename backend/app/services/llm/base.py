"""
Yojana Saathi - Common LLM Provider Interface
Milestone 6.2: Standardized provider contract, response schemas,
and observability models for the pluggable AI gateway.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ProviderTypeEnum(str, Enum):
    """Supported LLM provider types."""
    DETERMINISTIC = "deterministic"
    OLLAMA = "ollama"
    GROQ = "groq"
    GEMINI = "gemini"


class ProviderStatus(BaseModel):
    """Health and connectivity status of an LLM provider."""
    model_config = ConfigDict(from_attributes=True)

    provider: ProviderTypeEnum = Field(..., description="Provider identifier")
    is_available: bool = Field(..., description="Whether provider is online and operational")
    model: Optional[str] = Field(None, description="Configured model name/identifier")
    latency_ms: Optional[float] = Field(None, description="Round-trip ping/evaluation latency in ms")
    message: str = Field(..., description="Operational status or error explanation (sanitized)")
    timestamp: str = Field(..., description="ISO 8601 timestamp of health evaluation")


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""
    model_config = ConfigDict(from_attributes=True)

    text: str = Field(..., description="Generated text response")
    provider: ProviderTypeEnum = Field(..., description="Provider that produced this response")
    model: str = Field(..., description="Exact model identifier used")
    tokens_used: Optional[int] = Field(None, description="Reported token count if available")
    latency_ms: float = Field(..., description="Execution time in milliseconds")
    fallback_chain: List[str] = Field(
        default_factory=list,
        description="Safe diagnostic history of provider attempts (e.g. ['ollama (timeout)', 'deterministic (ok)'])"
    )


class SlotExtractionResponse(BaseModel):
    """Standardized attribute extraction output from any LLM provider."""
    model_config = ConfigDict(from_attributes=True)

    extracted_slots: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value mapping of allowlisted citizen profile attributes"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score of extracted slots"
    )
    raw_response: str = Field(
        default="",
        description="Raw output from provider before parsing"
    )
    provider: ProviderTypeEnum = Field(..., description="Provider that performed the extraction")
    latency_ms: float = Field(..., description="Execution time in milliseconds")


class BaseLLMProvider(ABC):
    """
    Abstract base class for all Yojana Saathi LLM providers.
    Enforces standardized generation, slot extraction, streaming, and health checks.
    """

    @property
    @abstractmethod
    def provider_type(self) -> ProviderTypeEnum:
        """Unique provider type identifier."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the active model."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = None,
    ) -> LLMResponse:
        """
        Generates a non-streaming conversational response.
        """
        pass

    @abstractmethod
    async def extract_slots(
        self,
        text: str,
        allowed_slots: List[str],
        language: str = "en",
    ) -> SlotExtractionResponse:
        """
        Extracts typed profile attributes strictly constrained to the allowed_slots list.
        """
        pass

    @abstractmethod
    async def stream_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        """
        Yields text chunks as an asynchronous stream.
        """
        pass

    @abstractmethod
    async def health_check(self) -> ProviderStatus:
        """
        Checks provider availability and connectivity without leaking credentials.
        """
        pass

