"""
Yojana Saathi - LLM Gateway & Provider Orchestrator
Milestone 6.2: Pluggable AI gateway managing provider selection,
cascading fallback, and observable health status without credential leakage.
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
from app.core.config import settings
from app.services.llm.base import (
    BaseLLMProvider,
    LLMResponse,
    ProviderStatus,
    ProviderTypeEnum,
    SlotExtractionResponse,
)
from app.services.llm.deterministic import DeterministicProvider
from app.services.llm.groq import GroqProvider, sanitize_url
from app.services.llm.gemini import GeminiProvider
from app.services.llm.ollama import OllamaProvider

logger = logging.getLogger(__name__)


class LLMGateway:
    """
    Gateway coordinating Primary, Secondary, and guaranteed Deterministic fallback providers.
    Ensures zero downtime, zero unhandled network crashes, and zero secret leakage.
    """

    def __init__(
        self,
        primary_provider: Optional[BaseLLMProvider] = None,
        secondary_provider: Optional[BaseLLMProvider] = None,
        deterministic_provider: Optional[BaseLLMProvider] = None,
    ):
        # 1. Guaranteed baseline fallback
        self.deterministic = deterministic_provider or DeterministicProvider()

        # 2. Initialize from explicit instances or backend configuration
        self.primary = primary_provider or self._create_provider(
            settings.llm_primary_provider, is_primary=True
        )
        self.secondary = secondary_provider or (
            self._create_provider(settings.llm_secondary_provider, is_primary=False)
            if settings.llm_secondary_provider
            else None
        )

    def _create_provider(self, provider_name: Optional[str], is_primary: bool = True) -> BaseLLMProvider:
        """Instantiates a provider based on configuration name."""
        name = (provider_name or "deterministic").strip().lower()

        if name == ProviderTypeEnum.DETERMINISTIC:
            return self.deterministic
        elif name == ProviderTypeEnum.OLLAMA:
            return OllamaProvider(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                timeout_seconds=settings.ollama_timeout_seconds,
            )
        elif name in (ProviderTypeEnum.GROQ, "groq"):
            return GroqProvider(
                api_key=settings.groq_api_key,
                model=settings.groq_model,
                timeout_seconds=settings.groq_timeout_seconds,
            )
        elif name in (ProviderTypeEnum.GEMINI, "gemini"):
            if settings.groq_api_key:
                return GroqProvider(
                    api_key=settings.groq_api_key,
                    model=settings.groq_model,
                    timeout_seconds=settings.groq_timeout_seconds,
                )
            return GeminiProvider(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                timeout_seconds=settings.gemini_timeout_seconds,
            )
        else:
            logger.warning(
                f"Unknown LLM provider '{provider_name}' configured; defaulting to deterministic baseline."
            )
            return self.deterministic

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = None,
    ) -> LLMResponse:
        """
        Executes text generation across the cascading fallback chain:
        Primary -> (on error) Secondary -> (on error) Deterministic.
        """
        chain_log: List[str] = []

        # 1. Attempt Primary Provider
        try:
            resp = await self.primary.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
            )
            resp.fallback_chain = [f"{self.primary.provider_type.value} (ok)"]
            return resp
        except Exception as e:
            err_reason = sanitize_url(f"{type(e).__name__}: {str(e)[:60]}")
            msg = f"{self.primary.provider_type.value} failed ({err_reason})"
            chain_log.append(msg)
            logger.warning(f"Primary provider failed: {msg}; cascading to next provider.")

        # 2. Attempt Secondary Provider if configured and distinct
        if self.secondary and self.secondary.provider_type != self.primary.provider_type:
            try:
                resp = await self.secondary.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout_seconds=timeout_seconds,
                )
                chain_log.append(f"{self.secondary.provider_type.value} (ok)")
                resp.fallback_chain = chain_log
                return resp
            except Exception as e:
                err_reason = sanitize_url(f"{type(e).__name__}: {str(e)[:60]}")
                msg = f"{self.secondary.provider_type.value} failed ({err_reason})"
                chain_log.append(msg)
                logger.warning(f"Secondary provider failed: {msg}; cascading to deterministic fallback.")

        # 3. Guaranteed Deterministic Fallback
        chain_log.append("deterministic (fallback)")
        resp = await self.deterministic.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        resp.fallback_chain = chain_log
        return resp

    async def extract_slots(
        self,
        text: str,
        allowed_slots: List[str],
        language: str = "en",
    ) -> SlotExtractionResponse:
        """
        Cascades slot extraction across providers, guaranteeing deterministic completion.
        """
        # 1. Try Primary Provider
        try:
            return await self.primary.extract_slots(text, allowed_slots, language)
        except Exception as e:
            logger.info(f"Primary slot extraction failed ({type(e).__name__}); cascading.")

        # 2. Try Secondary Provider
        if self.secondary and self.secondary.provider_type != self.primary.provider_type:
            try:
                return await self.secondary.extract_slots(text, allowed_slots, language)
            except Exception as e:
                logger.info(f"Secondary slot extraction failed ({type(e).__name__}); cascading.")

        # 3. Guaranteed Deterministic Baseline
        return await self.deterministic.extract_slots(text, allowed_slots, language)

    async def stream_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        """
        Streams response chunks from active provider, falling back before stream begins if needed.
        """
        # 1. Attempt Primary Provider
        try:
            async for chunk in self.primary.stream_text(prompt, system_prompt, max_tokens, temperature):
                yield chunk
            return
        except Exception as e:
            logger.warning(f"Primary streaming failed ({type(e).__name__}); falling back to deterministic stream.")

        # 2. Attempt Secondary Provider
        if self.secondary and self.secondary.provider_type != self.primary.provider_type:
            try:
                async for chunk in self.secondary.stream_text(prompt, system_prompt, max_tokens, temperature):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"Secondary streaming failed ({type(e).__name__}); falling back to deterministic stream.")

        # 3. Guaranteed Deterministic Baseline Stream
        async for chunk in self.deterministic.stream_text(prompt, system_prompt, max_tokens, temperature):
            yield chunk

    async def get_gateway_status(self) -> Dict[str, Any]:
        """
        Evaluates health of all registered providers without exposing API keys or secrets.
        """
        statuses: Dict[str, Any] = {}

        # 1. Deterministic status
        det_status = await self.deterministic.health_check()
        statuses["deterministic"] = det_status.model_dump()

        # 2. Primary provider status (if different from deterministic)
        if self.primary.provider_type != ProviderTypeEnum.DETERMINISTIC:
            p_status = await self.primary.health_check()
            statuses[self.primary.provider_type.value] = p_status.model_dump()

        # 3. Secondary provider status
        if self.secondary and self.secondary.provider_type not in statuses:
            s_status = await self.secondary.health_check()
            statuses[self.secondary.provider_type.value] = s_status.model_dump()

        return {
            "active_primary": self.primary.provider_type.value,
            "active_secondary": self.secondary.provider_type.value if self.secondary else None,
            "providers": statuses,
        }

    def is_real_llm_configured(self) -> bool:
        """Returns True when a non-deterministic LLM provider (Groq, Gemini, or Ollama) is configured."""
        if self.primary.provider_type != ProviderTypeEnum.DETERMINISTIC:
            return True
        if self.secondary and self.secondary.provider_type != ProviderTypeEnum.DETERMINISTIC:
            return True
        return False

    def get_configured_provider_info(self) -> Tuple[str, str]:
        """Returns (provider_name, model_name) of the primary configured provider."""
        return self.primary.provider_type.value, self.primary.model_name

