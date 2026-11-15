"""
Yojana Saathi - Milestone 6.2 Test Suite
Tests for Pluggable Zero-Cost LLM Provider Gateway.

Covers:
1. DeterministicProvider zero-network baseline generation, streaming, and slot extraction
2. Multilingual deterministic slot extraction (en, hi, kn, te) without PII leakage
3. OllamaProvider error handling (connection failure, timeout, model 404, malformed JSON)
4. GeminiProvider mocking (success, 429 rate limit, timeout, malformed payload)
5. Zero secrets leakage in errors, URLs, or fallback chains
6. No structured citizen profiles passed to external cloud providers
7. LLMGateway cascading fallback flow (Primary -> Secondary -> Deterministic)
8. Administrative /api/v1/health/llm endpoint integration
"""

import asyncio
import json
import pytest
import httpx
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.core.config import settings
from app.services.llm.base import ProviderTypeEnum
from app.services.llm.deterministic import DeterministicProvider
from app.services.llm.groq import GroqProvider, sanitize_url
from app.services.llm.gemini import GeminiProvider
from app.services.llm.gateway import LLMGateway
from app.services.llm.ollama import OllamaProvider

client = TestClient(app)


# ==============================================================================
# 1. DETERMINISTIC PROVIDER TESTS (ZERO-NETWORK BASELINE)
# ==============================================================================

@pytest.mark.asyncio
async def test_deterministic_provider_text_generation():
    """Verify deterministic provider produces predictable responses with zero external dependencies."""
    provider = DeterministicProvider()
    assert provider.provider_type == ProviderTypeEnum.DETERMINISTIC
    assert provider.model_name == "deterministic-rules-v1"

    # Greeting query
    res_greet = await provider.generate_text("Namaste, can you help me?")
    assert "Yojana Saathi" in res_greet.text
    assert res_greet.provider == ProviderTypeEnum.DETERMINISTIC
    assert res_greet.tokens_used is not None
    assert res_greet.latency_ms >= 0.0

    # Scheme context synthesis query
    context_prompt = (
        "Context:\n"
        "- PM-KISAN provides ₹6,000 per year directly to bank accounts.\n"
        "### Official Sources & Provenance\n"
        "1. PM-KISAN Guidelines"
    )
    res_ctx = await provider.generate_text(context_prompt)
    assert "PM-KISAN provides ₹6,000 per year" in res_ctx.text
    assert "Based on the official government scheme guidelines" in res_ctx.text


@pytest.mark.asyncio
async def test_deterministic_provider_streaming():
    """Verify deterministic provider yields streaming chunks with zero delay."""
    provider = DeterministicProvider()
    stream_chunks = []
    async for chunk in provider.stream_text("Hello Yojana Saathi"):
        stream_chunks.append(chunk)

    full_text = "".join(stream_chunks)
    assert len(stream_chunks) > 1
    assert "Yojana Saathi" in full_text


@pytest.mark.asyncio
async def test_deterministic_provider_multilingual_slot_extraction():
    """Verify regex/pattern slot extraction across English, Hindi, Kannada, and Telugu."""
    provider = DeterministicProvider()
    allowed_slots = [
        "age", "occupation", "landholding_hectares", "has_bpl_card",
        "pays_income_tax", "gender", "is_pregnant_or_lactating",
        "owns_motorized_three_or_four_wheeler",
    ]

    # 1. English farmer profile
    en_text = "I am a 42 years old farmer with 1.5 hectares of land, and I have a BPL card. I do not pay income tax."
    res_en = await provider.extract_slots(en_text, allowed_slots, "en")
    assert res_en.extracted_slots["age"] == 42
    assert res_en.extracted_slots["occupation"] == "Farmer"
    assert res_en.extracted_slots["landholding_hectares"] == 1.5
    assert res_en.extracted_slots["has_bpl_card"] is True
    assert res_en.extracted_slots["pays_income_tax"] is False

    # 2. Hindi street vendor
    hi_text = "मेरी उम्र 35 साल है और मैं एक स्ट्रीट वेंडर (फेरीवाला) हूँ। मेरे पास राशन कार्ड है।"
    res_hi = await provider.extract_slots(hi_text, allowed_slots, "hi")
    assert res_hi.extracted_slots["age"] == 35
    assert res_hi.extracted_slots["occupation"] == "Street Vendor"
    assert res_hi.extracted_slots["has_bpl_card"] is True

    # 3. Kannada farmer with acres (3 acres -> 1.21 hectares)
    kn_text = "ನನ್ನ ವಯಸ್ಸು 45 ವರ್ಷ, ನಾನು ರೈತ. ನನ್ನ ಬಳಿ 3 acres ಕೃಷಿ ಜಮೀನು ಇದೆ."
    res_kn = await provider.extract_slots(kn_text, allowed_slots, "kn")
    assert res_kn.extracted_slots["age"] == 45
    assert res_kn.extracted_slots["occupation"] == "Farmer"
    assert res_kn.extracted_slots["landholding_hectares"] == 1.21

    # 4. Telugu farmer
    te_text = "నా వయస్సు 50 సంవత్సరాలు, నేను రైతు."
    res_te = await provider.extract_slots(te_text, allowed_slots, "te")
    assert res_te.extracted_slots["age"] == 50
    assert res_te.extracted_slots["occupation"] == "Farmer"


@pytest.mark.asyncio
async def test_deterministic_slot_extraction_does_not_extract_pii():
    """Verify that sensitive citizen PII (Aadhaar, PAN, passwords) are never extracted."""
    provider = DeterministicProvider()
    allowed_slots = ["age", "occupation"]

    malicious_text = (
        "I am 30 years old farmer. My Aadhaar number is 2345 6789 0123, "
        "PAN is ABCDE1234F, and bank account is 987654321098."
    )
    res = await provider.extract_slots(malicious_text, allowed_slots, "en")
    # Only allowlisted fields extracted
    assert set(res.extracted_slots.keys()) == {"age", "occupation"}
    assert "aadhaar" not in res.extracted_slots
    assert "pan" not in res.extracted_slots
    assert "bank_account" not in res.extracted_slots


@pytest.mark.asyncio
async def test_deterministic_health_check():
    """Verify deterministic provider health status is always available."""
    provider = DeterministicProvider()
    status = await provider.health_check()
    assert status.is_available is True
    assert status.provider == ProviderTypeEnum.DETERMINISTIC
    assert "100% offline" in status.message


# ==============================================================================
# 2. OLLAMA PROVIDER ERROR HANDLING & FALLBACK TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_ollama_provider_connection_failure():
    """Verify Ollama gracefully catches connection refused when daemon is not running."""
    # Use non-existent port to force connection failure
    provider = OllamaProvider(base_url="http://127.0.0.1:54321", timeout_seconds=1.0)
    with pytest.raises(ConnectionError) as exc_info:
        await provider.generate_text("Test prompt")
    assert "Cannot connect to local Ollama daemon" in str(exc_info.value)

    # Health check should report unavailable without crashing
    status = await provider.health_check()
    assert status.is_available is False
    assert "unreachable" in status.message.lower()


@pytest.mark.asyncio
async def test_ollama_provider_model_missing_404():
    """Verify Ollama handles HTTP 404 model missing without downloading large files."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        provider = OllamaProvider(model="nonexistent-model:latest")
        with pytest.raises(RuntimeError) as exc_info:
            await provider.generate_text("Test prompt")
        assert "not found locally" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_provider_timeout_handling():
    """Verify Ollama handles request timeout cleanly."""
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")):
        provider = OllamaProvider(timeout_seconds=0.5)
        with pytest.raises(TimeoutError) as exc_info:
            await provider.generate_text("Test prompt")
        assert "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_slot_extraction_fallback_on_malformed_json():
    """Verify Ollama falls back to deterministic extraction when output is invalid JSON."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "response": "Sure! I think the user might be 40 years old farmer with some land."  # Non-JSON
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        provider = OllamaProvider()
        res = await provider.extract_slots(
            "I am 40 years old farmer with 2.5 hectares.",
            ["age", "occupation", "landholding_hectares"],
            "en",
        )
        # Should gracefully extract slots via deterministic fallback
        assert res.extracted_slots.get("age") == 40
        assert res.extracted_slots.get("occupation") == "Farmer"
        assert res.extracted_slots.get("landholding_hectares") == 2.5


# ==============================================================================
# 3. GEMINI PROVIDER TESTS & CREDENTIAL PROTECTION
# ==============================================================================

def test_gemini_provider_default_and_configurable_model():
    """Verify GeminiProvider defaults to candidate primary gemini-3.5-flash-lite and respects env overrides."""
    # Default model
    p_default = GeminiProvider(api_key="mock-key")
    assert p_default.model_name == "gemini-3.5-flash-lite"
    assert p_default.provider_type == ProviderTypeEnum.GEMINI

    # Custom model configured via parameter or env
    p_custom = GeminiProvider(api_key="mock-key", model="gemini-3.5-flash")
    assert p_custom.model_name == "gemini-3.5-flash"


def test_sanitize_url_redacts_api_keys():
    """Verify sanitize_url cleanly replaces secret API key tokens across query params and headers."""
    raw_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=AIzaSySecretToken12345"
    sanitized = sanitize_url(raw_url)
    assert "AIzaSySecretToken12345" not in sanitized
    assert "key=[REDACTED]" in sanitized

    raw_header = "Error in request with x-goog-api-key: AIzaSyHeaderSecretKey"
    sanitized_header = sanitize_url(raw_header)
    assert "AIzaSyHeaderSecretKey" not in sanitized_header
    assert "x-goog-api-key: [REDACTED]" in sanitized_header


@pytest.mark.asyncio
async def test_gemini_provider_unconfigured_key_behavior():
    """Verify Gemini provider cleanly fails when no API key is provided."""
    provider = GeminiProvider(api_key="")
    with pytest.raises(ValueError) as exc:
        await provider.generate_text("Test prompt")
    assert "GEMINI_API_KEY is not configured" in str(exc.value)

    status = await provider.health_check()
    assert status.is_available is False
    assert "not configured" in status.message


@pytest.mark.asyncio
async def test_gemini_provider_mock_successful_generation():
    """Verify Gemini uses header-based auth (x-goog-api-key), clean URL, and parses valid responses."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "PM-KISAN provides ₹6,000 per year."}]
                },
                "finishReason": "STOP"
            }
        ],
        "usageMetadata": {"totalTokenCount": 42}
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        provider = GeminiProvider(api_key="mock-key-123", model="gemini-3.8-flash")
        res = await provider.generate_text("What is PM-KISAN?")

        assert res.text == "PM-KISAN provides ₹6,000 per year."
        assert res.provider == ProviderTypeEnum.GEMINI
        assert res.model == "gemini-3.8-flash"
        assert res.tokens_used == 42

        # Verify call arguments: URL must NOT contain API key in query string!
        call_args = mock_post.call_args
        url_called = call_args[0][0]
        headers_called = call_args[1].get("headers", {})

        assert "key=" not in url_called  # URL is clean
        assert headers_called.get("x-goog-api-key") == "mock-key-123"  # Header-based auth


@pytest.mark.asyncio
async def test_gemini_provider_unsupported_model_actionable_error():
    """Verify HTTP 404 on unsupported model returns actionable error and does NOT silently switch to paid model."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        provider = GeminiProvider(api_key="mock-key-123", model="gemini-retired-model")
        with pytest.raises(RuntimeError) as exc_info:
            await provider.generate_text("Test prompt")
        err_msg = str(exc_info.value)
        assert "unsupported" in err_msg.lower() or "not found" in err_msg.lower()
        assert "update GEMINI_MODEL in backend/.env" in err_msg
        # Model name must remain unchanged (no silent switch)
        assert provider.model_name == "gemini-retired-model"


@pytest.mark.asyncio
async def test_gemini_provider_rate_limit_and_secret_suppression():
    """Verify HTTP 429 rate limit is handled and API key is NOT leaked in exception message."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        provider = GeminiProvider(api_key="super-secret-key-xyz", model="gemini-3.8-flash")
        with pytest.raises(RuntimeError) as exc_info:
            await provider.generate_text("Test prompt")
        err_msg = str(exc_info.value)
        assert "super-secret-key-xyz" not in err_msg
        assert "rate limit exceeded" in err_msg.lower() or "gemini provider failure" in err_msg.lower()


@pytest.mark.asyncio
async def test_gemini_never_receives_structured_citizen_profiles():
    """Verify that extract_slots transmits only de-identified query text, never structured profile objects."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "{\"age\": 45, \"occupation\": \"Farmer\"}"}]
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        provider = GeminiProvider(api_key="mock-key-123", model="gemini-3.8-flash")
        citizen_raw_text = "I am a 45 years old farmer."
        res = await provider.extract_slots(
            text=citizen_raw_text,
            allowed_slots=["age", "occupation"],
            language="en",
        )

        assert res.extracted_slots["age"] == 45
        assert res.extracted_slots["occupation"] == "Farmer"

        # Check payload sent to Gemini: verify only the prompt text was included
        call_body = mock_post.call_args[1].get("json", {})
        prompt_sent = call_body["contents"][0]["parts"][0]["text"]
        assert citizen_raw_text in prompt_sent
        # Ensure no structured profile dictionary was serialized into the request
        assert "citizen_profile" not in json.dumps(call_body)
        assert "aadhaar" not in json.dumps(call_body)


# ==============================================================================
# 3B. GROQ PROVIDER TESTS & CREDENTIAL PROTECTION
# ==============================================================================

def test_groq_provider_default_and_configurable_model():
    """Verify GroqProvider defaults to primary openai/gpt-oss-120b and respects env overrides."""
    p_default = GroqProvider(api_key="mock-key")
    assert p_default.model_name == settings.groq_model
    assert p_default.provider_type == ProviderTypeEnum.GROQ

    p_custom = GroqProvider(api_key="mock-key", model="llama-3.1-8b-instant")
    assert p_custom.model_name == "llama-3.1-8b-instant"


def test_sanitize_url_redacts_groq_keys():
    """Verify sanitize_url cleanly replaces Groq API key tokens and Bearer headers."""
    raw_header = "Authorization: Bearer gsk_999999SecretKeyAbcDefGhi"
    sanitized = sanitize_url(raw_header)
    assert "gsk_999999SecretKeyAbcDefGhi" not in sanitized
    assert "Bearer [REDACTED]" in sanitized or "[REDACTED]" in sanitized


@pytest.mark.asyncio
async def test_groq_provider_unconfigured_key_behavior():
    """Verify Groq provider cleanly fails when no API key is provided."""
    provider = GroqProvider(api_key="")
    with pytest.raises(ValueError) as exc:
        await provider.generate_text("Test prompt")
    assert "GROQ_API_KEY is not configured" in str(exc.value)

    status = await provider.health_check()
    assert status.is_available is False
    assert "not configured" in status.message


@pytest.mark.asyncio
async def test_groq_provider_mock_successful_generation():
    """Verify Groq uses Bearer auth, OpenAI-compatible JSON structure, and parses valid responses."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "chatcmpl-test-123",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "PM-KISAN provides ₹6,000 per year in three installments."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {"total_tokens": 36}
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        provider = GroqProvider(api_key="gsk_mock_test_key_123", model="openai/gpt-oss-120b")
        res = await provider.generate_text("What is PM-KISAN?")

        assert res.text == "PM-KISAN provides ₹6,000 per year in three installments."
        assert res.provider == ProviderTypeEnum.GROQ
        assert res.model == "openai/gpt-oss-120b"
        assert res.tokens_used == 36

        call_args = mock_post.call_args
        url_called = call_args[0][0]
        headers_called = call_args[1].get("headers", {})
        body_called = call_args[1].get("json", {})

        assert "api.groq.com/openai/v1/chat/completions" in url_called
        assert headers_called.get("Authorization") == "Bearer gsk_mock_test_key_123"
        assert body_called.get("model") == "openai/gpt-oss-120b"
        assert body_called.get("messages")[-1]["content"] == "What is PM-KISAN?"


@pytest.mark.asyncio
async def test_groq_provider_rate_limit_and_secret_suppression():
    """Verify HTTP 429 rate limit is handled and Groq key is NOT leaked in exception message."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        provider = GroqProvider(api_key="gsk_super_secret_key_xyz", model="openai/gpt-oss-120b")
        with pytest.raises(RuntimeError) as exc_info:
            await provider.generate_text("Test prompt")
        err_msg = str(exc_info.value)
        assert "gsk_super_secret_key_xyz" not in err_msg
        assert "rate limit" in err_msg.lower() or "groq provider failure" in err_msg.lower()


# ==============================================================================
# 4. LLM GATEWAY CASCADING FALLBACK TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_gateway_default_deterministic_execution():
    """Verify gateway uses deterministic provider by default without network calls."""
    gateway = LLMGateway(primary_provider=DeterministicProvider())
    res = await gateway.generate_text("Hello Yojana Saathi")
    assert res.provider == ProviderTypeEnum.DETERMINISTIC
    assert "deterministic (ok)" in res.fallback_chain[0] or "deterministic (baseline)" in res.fallback_chain[0]


@pytest.mark.asyncio
async def test_gateway_cascades_from_failing_primary_to_deterministic():
    """Verify gateway cascades when primary provider (Ollama) throws connection failure."""
    failing_ollama = OllamaProvider(base_url="http://127.0.0.1:54321", timeout_seconds=0.1)
    deterministic = DeterministicProvider()

    gateway = LLMGateway(primary_provider=failing_ollama, deterministic_provider=deterministic)
    res = await gateway.generate_text("Can you help me with PM-KISAN?")

    # Execution must succeed via fallback without throwing
    assert res.provider == ProviderTypeEnum.DETERMINISTIC
    assert len(res.fallback_chain) >= 2
    assert "ollama failed" in res.fallback_chain[0]
    assert "deterministic (fallback)" in res.fallback_chain[-1]


@pytest.mark.asyncio
async def test_gateway_cascades_primary_to_secondary_to_deterministic():
    """Verify full 3-tier cascade: failing primary -> failing secondary -> deterministic baseline."""
    failing_primary = OllamaProvider(base_url="http://127.0.0.1:54321", timeout_seconds=0.1)
    failing_secondary = GeminiProvider(api_key=None)  # unconfigured key will fail
    deterministic = DeterministicProvider()

    gateway = LLMGateway(
        primary_provider=failing_primary,
        secondary_provider=failing_secondary,
        deterministic_provider=deterministic,
    )
    res = await gateway.generate_text("What is PM SVANidhi?")

    assert res.provider == ProviderTypeEnum.DETERMINISTIC
    assert any("ollama failed" in s for s in res.fallback_chain)
    assert any("gemini failed" in s for s in res.fallback_chain)
    assert "deterministic (fallback)" in res.fallback_chain[-1]


@pytest.mark.asyncio
async def test_gateway_extract_slots_cascades_cleanly():
    """Verify gateway cascades slot extraction seamlessly without crashing."""
    failing_primary = OllamaProvider(base_url="http://127.0.0.1:54321", timeout_seconds=0.1)
    gateway = LLMGateway(primary_provider=failing_primary)

    res = await gateway.extract_slots(
        "I am 38 years old street vendor with BPL card",
        ["age", "occupation", "has_bpl_card"],
        "en",
    )
    assert res.extracted_slots["age"] == 38
    assert res.extracted_slots["occupation"] == "Street Vendor"
    assert res.extracted_slots["has_bpl_card"] is True


# ==============================================================================
# 5. ADMINISTRATIVE HEALTH ENDPOINT INTEGRATION
# ==============================================================================

def test_api_health_llm_endpoint():
    """Verify GET /api/v1/health/llm returns status of all providers without leaking secrets."""
    response = client.get("/api/v1/health/llm")
    assert response.status_code == 200
    data = response.json()

    assert "active_primary" in data
    assert "providers" in data
    assert "deterministic" in data["providers"]
    assert data["providers"]["deterministic"]["is_available"] is True

    # Confirm no API key string exists in response
    serialized = json.dumps(data)
    assert "AIzaSy" not in serialized
    assert "key=" not in serialized

