"""
Yojana Saathi - Groq Cloud LLM Provider
Cloud provider communicating with Groq's high-speed API
strictly from the backend using standard REST interfaces and Bearer token
authentication. Never leaks API credentials, provides actionable errors
on unsupported models, and enforces strict citizen privacy.
"""

from datetime import datetime, timezone
import asyncio
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

GROQ_API_BASE = "https://api.groq.com/openai/v1"


def sanitize_url(text: str) -> str:
    """
    Removes API keys or tokens from text strings to prevent credential leakage in logs.
    Handles Groq API keys (gsk_...), Bearer headers, query parameter tokens, and legacy headers.
    """
    sanitized = re.sub(r"gsk_[A-Za-z0-9_-]+", "[REDACTED]", str(text))
    sanitized = re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"key=[^&\s'\"]+", "key=[REDACTED]", sanitized)
    sanitized = re.sub(r"x-goog-api-key['\":\s]+[^,\s'\"]+", "x-goog-api-key: [REDACTED]", sanitized, flags=re.IGNORECASE)
    return sanitized


class GroqProvider(BaseLLMProvider):
    """
    Connects to Groq API via backend HTTP REST calls.
    Uses header-based Bearer authentication so secret credentials never
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
        self._api_key = api_key if api_key is not None else settings.groq_api_key
        self._model = (model or settings.groq_model).strip()
        self._timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.groq_timeout_seconds
        self._fallback_deterministic = DeterministicProvider()

    @property
    def provider_type(self) -> ProviderTypeEnum:
        return ProviderTypeEnum.GROQ

    @property
    def model_name(self) -> str:
        return self._model

    def _get_headers(self) -> Dict[str, str]:
        """Header-based Bearer token authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
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
        Invokes Groq chat completions endpoint.
        """
        if not self._api_key:
            raise ValueError("GROQ_API_KEY is not configured in backend environment.")

        call_timeout = timeout_seconds if timeout_seconds is not None else self._timeout_seconds
        start_time = time.perf_counter()
        url = f"{GROQ_API_BASE}/chat/completions"

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=call_timeout) as client:
                resp = await client.post(url, json=body, headers=self._get_headers())

                # If rate limited, perform a single brief backoff retry
                if resp.status_code == 429:
                    await asyncio.sleep(0.8)
                    resp = await client.post(url, json=body, headers=self._get_headers())

                if resp.status_code == 404:
                    raise RuntimeError(
                        f"Configured Groq model '{self._model}' was not found or is unsupported (HTTP 404). "
                        "Please update GROQ_MODEL in backend/.env to a supported model."
                    )

                if resp.status_code == 401:
                    raise PermissionError(
                        "Groq API authentication failed (HTTP 401). Please verify GROQ_API_KEY in backend/.env."
                    )

                if resp.status_code == 403:
                    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    err_msg = data.get("error", {}).get("message", "Permission denied.")
                    raise PermissionError(
                        f"Groq API access denied (HTTP 403): {err_msg}."
                    )

                if resp.status_code == 429:
                    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    err_msg = data.get("error", {}).get("message", "Rate limit or quota exceeded.")
                    raise RuntimeError(f"Groq API rate limit or quota exhausted (HTTP 429): {err_msg}")

                if resp.status_code == 400:
                    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    err_msg = data.get("error", {}).get("message", "Bad request.")
                    if "model" in err_msg.lower() and ("not found" in err_msg.lower() or "decommissioned" in err_msg.lower()):
                        raise RuntimeError(
                            f"Configured Groq model '{self._model}' is not accessible on this account (HTTP 400): {err_msg}. "
                            "Please configure a valid supported model in GROQ_MODEL."
                        )
                    raise ValueError(f"Groq API bad request (HTTP 400): {err_msg}")

                resp.raise_for_status()
                data = resp.json()

                choices = data.get("choices", [])
                if not choices:
                    raise RuntimeError("Groq returned empty candidate response.")

                first_choice = choices[0]
                msg = first_choice.get("message", {})
                text_out = (msg.get("content") or msg.get("reasoning") or "").strip()

                usage = data.get("usage", {})
                total_tokens = usage.get("total_tokens")

                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                return LLMResponse(
                    text=text_out,
                    provider=self.provider_type,
                    model=self.model_name,
                    tokens_used=total_tokens,
                    latency_ms=latency_ms,
                    fallback_chain=["groq (cloud)"],
                )

        except httpx.TimeoutException as e:
            logger.warning(f"Groq API request timed out after {call_timeout}s.")
            raise TimeoutError(f"Groq API timed out after {call_timeout}s.") from e
        except Exception as e:
            clean_err = sanitize_url(str(e))
            logger.warning(f"Groq API request failure: {clean_err}")
            raise RuntimeError(f"Groq provider failure: {clean_err}") from None

    async def extract_slots(
        self,
        text: str,
        allowed_slots: List[str],
        language: str = "en",
    ) -> SlotExtractionResponse:
        """
        Extracts allowlisted attributes from citizen text via Groq.
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
                raise ValueError("Parsed Groq output is not a JSON object.")

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
            logger.info(f"Groq slot extraction failed ({clean_err}); falling back to deterministic extraction.")
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
        Streams response chunks via Groq chat completions SSE endpoint.
        """
        if not self._api_key:
            raise ValueError("GROQ_API_KEY is not configured in backend environment.")

        url = f"{GROQ_API_BASE}/chat/completions"

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                async with client.stream("POST", url, json=body, headers=self._get_headers()) as resp:
                    if resp.status_code == 404:
                        raise RuntimeError(
                            f"Configured Groq model '{self._model}' is unavailable on this account."
                        )
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content") or delta.get("reasoning") or ""
                                if content:
                                    yield content
                        except Exception:
                            continue
        except Exception as e:
            clean_err = sanitize_url(str(e))
            logger.warning(f"Groq streaming failure: {clean_err}")
            raise RuntimeError(f"Groq streaming failure: {clean_err}") from None

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """
        Queries the official Groq models endpoint to discover models accessible on the current API key.
        """
        if not self._api_key:
            return []
        url = f"{GROQ_API_BASE}/models"
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", [])
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
                message="Groq API key not configured in backend environment.",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        start = time.perf_counter()
        url = f"{GROQ_API_BASE}/models"

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
                        message=f"Groq cloud endpoint operational (model: {self._model}).",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                elif resp.status_code == 401:
                    return ProviderStatus(
                        provider=self.provider_type,
                        is_available=False,
                        model=self._model,
                        latency_ms=latency_ms,
                        message="Groq authentication failed (invalid GROQ_API_KEY).",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                else:
                    return ProviderStatus(
                        provider=self.provider_type,
                        is_available=False,
                        model=self._model,
                        latency_ms=latency_ms,
                        message=f"Groq returned HTTP {resp.status_code}.",
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
                message=f"Groq connection failed ({type(e).__name__}).",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

