"""
Yojana Saathi - Google Gemini Cloud LLM Provider
Milestone 6.2: Optional cloud provider communicating with Google Gemini API
strictly from the backend using standard REST interfaces and header-based
authentication (x-goog-api-key). Never leaks API credentials, provides
actionable errors on unsupported models without silent fallback to paid tiers,
and enforces strict citizen privacy.
"""

from datetime import datetime, timezone
import json
import logging
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx

from app.core.config import settings
from app.services.llm.base import (
    BaseLLMProvider,
    LLMResponse,
    ProviderStatus,
    ProviderTypeEnum,
    SlotExtractionResponse,
)
from app.services.llm.deterministic import DeterministicProvider

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def sanitize_url(text: str) -> str:
    """
    Removes API keys or tokens from text strings to prevent credential leakage in logs.
    Handles both query parameter format (key=...) and header/token patterns.
    """
    sanitized = re.sub(r"key=[^&\s'\"]+", "key=[REDACTED]", str(text))
    sanitized = re.sub(r"x-goog-api-key['\":\s]+[^,\s'\"]+", "x-goog-api-key: [REDACTED]", sanitized, flags=re.IGNORECASE)
    return sanitized


class GeminiProvider(BaseLLMProvider):
    """
    Connects to Google Gemini API via backend HTTP REST calls.
    Uses header-based authentication (x-goog-api-key) so secret credentials never
    appear in request URLs, query parameters, or web server logs.
    
    Enforces privacy by transmitting only de-identified natural language text and
    retrieved public scheme context. Never forwards structured citizen demographic profiles.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self._api_key = api_key if api_key is not None else settings.gemini_api_key
        self._model = (model or settings.gemini_model).strip()
        self._timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.gemini_timeout_seconds
        self._fallback_deterministic = DeterministicProvider()

    @property
    def provider_type(self) -> ProviderTypeEnum:
        return ProviderTypeEnum.GEMINI

    @property
    def model_name(self) -> str:
        return self._model

    def _get_headers(self) -> Dict[str, str]:
        """Header-based authentication (x-goog-api-key)."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["x-goog-api-key"] = self._api_key
        return headers

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = None,
    ) -> LLMResponse:
        """
        Invokes Gemini generateContent endpoint.
        """
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is not configured in backend environment.")

        call_timeout = timeout_seconds if timeout_seconds is not None else self._timeout_seconds
        start_time = time.perf_counter()
        # Clean URL: no API key query parameter; authentication handled via x-goog-api-key header
        url = f"{GEMINI_API_BASE}/{self._model}:generateContent"

        body: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_prompt:
            body["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        try:
            async with httpx.AsyncClient(timeout=call_timeout) as client:
                resp = await client.post(url, json=body, headers=self._get_headers())

                # Explicit actionable handling for unsupported/missing model (404)
                if resp.status_code == 404:
                    raise RuntimeError(
                        f"Configured Gemini model '{self._model}' was not found or is unsupported on this API key/project (HTTP 404). "
                        "Please update GEMINI_MODEL in backend/.env to a supported model."
                    )

                if resp.status_code == 401:
                    raise PermissionError(
                        "Gemini API authentication failed (HTTP 401). Please verify GEMINI_API_KEY in backend/.env."
                    )

                if resp.status_code == 403:
                    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    err_msg = data.get("error", {}).get("message", "Permission denied.")
                    raise PermissionError(
                        f"Gemini API access denied (HTTP 403): {err_msg}."
                    )

                if resp.status_code == 429:
                    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    err_msg = data.get("error", {}).get("message", "Quota exceeded.")
                    raise RuntimeError(f"Gemini API free-tier quota/rate limit exhausted (HTTP 429): {err_msg}")

                if resp.status_code == 400:
                    data = resp.json()
                    err_msg = data.get("error", {}).get("message", "Bad request.")
                    if "not found" in err_msg.lower() or "models/" in err_msg.lower():
                        raise RuntimeError(
                            f"Configured Gemini model '{self._model}' is not accessible on this account (HTTP 400): {err_msg}. "
                            "Please configure a valid supported model in GEMINI_MODEL."
                        )
                    raise ValueError(f"Gemini API bad request (HTTP 400): {err_msg}")

                resp.raise_for_status()
                data = resp.json()

                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError("Gemini returned empty candidate response.")

                first_candidate = candidates[0]
                content = first_candidate.get("content", {})
                parts = content.get("parts", [])
                text_out = "".join(p.get("text", "") for p in parts).strip()

                usage = data.get("usageMetadata", {})
                total_tokens = usage.get("totalTokenCount")

                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                return LLMResponse(
                    text=text_out,
                    provider=self.provider_type,
                    model=self.model_name,
                    tokens_used=total_tokens,
                    latency_ms=latency_ms,
                    fallback_chain=["gemini (cloud)"],
                )

        except httpx.TimeoutException as e:
            logger.warning(f"Gemini API request timed out after {self._timeout_seconds}s.")
            raise TimeoutError(f"Gemini API timed out after {self._timeout_seconds}s.") from e
        except Exception as e:
            clean_err = sanitize_url(str(e))
            logger.warning(f"Gemini API request failure: {clean_err}")
            raise RuntimeError(f"Gemini provider failure: {clean_err}") from None

    async def extract_slots(
        self,
        text: str,
        allowed_slots: List[str],
        language: str = "en",
    ) -> SlotExtractionResponse:
        """
        Extracts allowlisted attributes from citizen text via Gemini.
        Transmits ONLY the natural language string, never any structured profile dict.
        Falls back to deterministic extraction on malformed JSON or error.
        """
        start_time = time.perf_counter()
        system_instruction = (
            "You are a confidential data extractor for Indian welfare schemes. "
            f"Extract ONLY the following allowlisted fields if explicitly stated: {allowed_slots}. "
            "Never extract or request Aadhaar, PAN, passwords, or bank account numbers. "
            "Output strictly valid JSON with no additional explanation."
        )

        try:
            response = await self.generate_text(
                prompt=f"Extract allowlisted attributes from text: \"{text}\"",
                system_prompt=system_instruction,
                temperature=0.0,
            )
            raw = response.text
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("Parsed Gemini output is not a JSON object.")

            sanitized = {
                k: v for k, v in parsed.items()
                if k in allowed_slots and v is not None
            }

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return SlotExtractionResponse(
                extracted_slots=sanitized,
                confidence=0.95 if sanitized else 0.0,
                raw_response=response.text,
                provider=self.provider_type,
                latency_ms=latency_ms,
            )

        except Exception as e:
            clean_err = sanitize_url(str(e))
            logger.info(f"Gemini slot extraction failed ({clean_err}); falling back to deterministic extraction.")
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
        Streams response chunks via Gemini streamGenerateContent SSE endpoint.
        """
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is not configured in backend environment.")

        # Clean SSE endpoint URL; authentication via x-goog-api-key header
        url = f"{GEMINI_API_BASE}/{self._model}:streamGenerateContent?alt=sse"

        body: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_prompt:
            body["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                async with client.stream("POST", url, json=body, headers=self._get_headers()) as resp:
                    if resp.status_code == 404:
                        raise RuntimeError(
                            f"Configured Gemini model '{self._model}' is unavailable on this account."
                        )
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        json_str = line[6:].strip()
                        try:
                            chunk = json.loads(json_str)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    t = p.get("text", "")
                                    if t:
                                        yield t
                        except Exception:
                            continue
        except Exception as e:
            clean_err = sanitize_url(str(e))
            logger.warning(f"Gemini streaming failure: {clean_err}")
            raise RuntimeError(f"Gemini streaming failure: {clean_err}") from None

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """
        Queries the official models list endpoint to discover models accessible on the current API key.
        """
        if not self._api_key:
            return []
        url = GEMINI_API_BASE
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 200:
                data = resp.json()
                return data.get("models", [])
            return []

    async def health_check(self) -> ProviderStatus:
        """
        Validates configuration without exposing API key in response or logs.
        """
        if not self._api_key:
            return ProviderStatus(
                provider=self.provider_type,
                is_available=False,
                model=self._model,
                latency_ms=0.0,
                message="Gemini API key not configured in backend environment.",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        start = time.perf_counter()
        url = f"{GEMINI_API_BASE}/{self._model}"

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                latency_ms = round((time.perf_counter() - start) * 1000, 2)

                if resp.status_code == 200:
                    return ProviderStatus(
                        provider=self.provider_type,
                        is_available=True,
                        model=self._model,
                        latency_ms=latency_ms,
                        message=f"Gemini cloud endpoint operational (model: {self._model}).",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                elif resp.status_code == 404:
                    return ProviderStatus(
                        provider=self.provider_type,
                        is_available=False,
                        model=self._model,
                        latency_ms=latency_ms,
                        message=f"Configured Gemini model '{self._model}' is not found or unsupported on this account.",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                else:
                    return ProviderStatus(
                        provider=self.provider_type,
                        is_available=False,
                        model=self._model,
                        latency_ms=latency_ms,
                        message=f"Gemini returned HTTP {resp.status_code}.",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
        except Exception as e:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            clean_err = sanitize_url(str(e))
            return ProviderStatus(
                provider=self.provider_type,
                is_available=False,
                model=self._model,
                latency_ms=latency_ms,
                message=f"Gemini connection failed ({type(e).__name__}).",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
