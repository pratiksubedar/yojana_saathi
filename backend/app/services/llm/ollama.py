"""
Yojana Saathi - Ollama Local LLM Provider
Milestone 6.2: Optional local AI provider connecting to a locally running
Ollama daemon. Never auto-downloads models; handles connection, timeout,
and model-missing errors gracefully.
"""

from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx

from app.services.llm.base import (
    BaseLLMProvider,
    LLMResponse,
    ProviderStatus,
    ProviderTypeEnum,
    SlotExtractionResponse,
)
from app.services.llm.deterministic import DeterministicProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Connects to a local Ollama instance (default: http://127.0.0.1:11434).
    Keeps all data local; zero internet connection required.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "llama3.2:3b",
        timeout_seconds: float = 10.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._fallback_deterministic = DeterministicProvider()

    @property
    def provider_type(self) -> ProviderTypeEnum:
        return ProviderTypeEnum.OLLAMA

    @property
    def model_name(self) -> str:
        return self._model

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = None,
    ) -> LLMResponse:
        """
        Generates text using local Ollama daemon via /api/generate endpoint.
        """
        start_time = time.perf_counter()
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        url = f"{self._base_url}/api/generate"

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                resp = await client.post(url, json=payload)

                if resp.status_code == 404:
                    raise RuntimeError(f"Ollama model '{self._model}' not found locally. Please run 'ollama pull {self._model}'.")

                resp.raise_for_status()
                data = resp.json()
                generated_text = data.get("response", "").strip()
                tokens_count = data.get("eval_count")

                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return LLMResponse(
                    text=generated_text,
                    provider=self.provider_type,
                    model=self.model_name,
                    tokens_used=tokens_count,
                    latency_ms=latency_ms,
                    fallback_chain=["ollama (local)"],
                )

        except httpx.ConnectError as e:
            logger.warning(f"Ollama connection refused at {self._base_url}: {e}")
            raise ConnectionError(f"Cannot connect to local Ollama daemon at {self._base_url}.") from e
        except httpx.TimeoutException as e:
            logger.warning(f"Ollama request timed out after {self._timeout_seconds}s: {e}")
            raise TimeoutError(f"Ollama inference timed out after {self._timeout_seconds}s.") from e
        except Exception as e:
            logger.warning(f"Ollama generation failure: {e}")
            raise

    async def extract_slots(
        self,
        text: str,
        allowed_slots: List[str],
        language: str = "en",
    ) -> SlotExtractionResponse:
        """
        Extracts typed attributes using Ollama with JSON output instruction,
        falling back to deterministic extraction if JSON parsing fails.
        """
        start_time = time.perf_counter()
        system_instruction = (
            "You are an accurate, confidential data extractor for Indian welfare schemes. "
            f"Extract ONLY the following allowlisted fields from the citizen's query if explicitly mentioned: {allowed_slots}. "
            "Never extract or request Aadhaar, PAN, passwords, or bank account numbers. "
            "Output strictly valid JSON with no additional explanation or markdown."
        )

        try:
            response = await self.generate_text(
                prompt=f"Extract allowlisted attributes from text: \"{text}\"",
                system_prompt=system_instruction,
                temperature=0.0,
            )
            raw = response.text
            # Extract JSON block if wrapped in markdown
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("Extracted JSON is not an object.")

            # Filter to allowed slots only
            sanitized_slots = {
                k: v for k, v in parsed.items()
                if k in allowed_slots and v is not None
            }

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return SlotExtractionResponse(
                extracted_slots=sanitized_slots,
                confidence=0.9 if sanitized_slots else 0.0,
                raw_response=response.text,
                provider=self.provider_type,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.info(f"Ollama slot extraction failed ({e}); falling back to deterministic extraction.")
            # Gracefully fallback to deterministic extraction
            fallback_res = await self._fallback_deterministic.extract_slots(text, allowed_slots, language)
            fallback_res.provider = self.provider_type
            return fallback_res

    async def stream_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        """
        Streams response chunks from local Ollama daemon.
        """
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        url = f"{self._base_url}/api/generate"

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            if token:
                                yield token
                        except Exception:
                            continue
        except Exception as e:
            logger.warning(f"Ollama streaming failure: {e}")
            raise

    async def health_check(self) -> ProviderStatus:
        """
        Pings local Ollama daemon at /api/tags to verify connectivity and model availability.
        """
        start = time.perf_counter()
        url = f"{self._base_url}/api/tags"

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url)
                latency_ms = round((time.perf_counter() - start) * 1000, 2)

                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    # Check if requested model or tag matches
                    has_model = any(
                        self._model == m or m.startswith(f"{self._model}:") or self._model.split(":")[0] in m
                        for m in models
                    )
                    msg = (
                        f"Ollama online; model '{self._model}' available."
                        if has_model
                        else f"Ollama online, but model '{self._model}' not found locally. Available: {models[:3]}."
                    )
                    return ProviderStatus(
                        provider=self.provider_type,
                        is_available=has_model,
                        model=self._model,
                        latency_ms=latency_ms,
                        message=msg,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                else:
                    return ProviderStatus(
                        provider=self.provider_type,
                        is_available=False,
                        model=self._model,
                        latency_ms=latency_ms,
                        message=f"Ollama returned HTTP {resp.status_code}.",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
        except Exception as e:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return ProviderStatus(
                provider=self.provider_type,
                is_available=False,
                model=self._model,
                latency_ms=latency_ms,
                message=f"Ollama unreachable at {self._base_url} ({type(e).__name__}).",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

