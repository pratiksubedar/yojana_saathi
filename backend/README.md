# Yojana Saathi (योजना साथी) — Backend Service

FastAPI-powered backend service for **Yojana Saathi**, a multilingual voice AI assistant helping Indian citizens discover government welfare schemes, understand eligibility criteria, and access application information.

Supports **English (`en`)**, **Hindi (`hi`)**, **Kannada (`kn`)**, and **Telugu (`te`)**.

---

## 1. Zero-Cost Local Architecture

This backend is designed to run **100% locally with zero monetary cost**:
- **Framework:** FastAPI (Python 3.11+)
- **Server:** Uvicorn ASGI
- **Data Validation:** Pydantic v2 & `pydantic-settings`
- **Database (Local MVP):** SQLite (Async SQLAlchemy via `aiosqlite`)
- **Testing:** Pytest with HTTP test client

---

## 2. Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app factory, CORS, routes mount
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # Settings management via pydantic-settings
│   └── api/
│       ├── __init__.py
│       ├── router.py        # Master API router
│       └── v1/
│           ├── __init__.py
│           └── health.py    # Health & diagnostic endpoint
├── tests/
│   ├── __init__.py
│   └── test_health.py       # Automated endpoint tests
├── .env.example             # Configuration template
├── .env                     # Local environment settings
├── .gitignore               # Ignored files (.venv, __pycache__, .env, *.db)
├── pytest.ini               # Pytest configuration
├── requirements.txt         # Pinned Python package dependencies
└── README.md                # This documentation
```

---

## 3. Quick Start & Local Setup

### Step 1: Navigate to the Backend Directory
```bash
cd backend
```

### Step 2: Set Up and Activate the Virtual Environment
```bash
# Create the virtual environment (if not already created)
python3 -m venv .venv

# Activate on macOS / Linux:
source .venv/bin/activate

# (On Windows: .venv\Scripts\activate)
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
```bash
cp .env.example .env
```
*(The default `.env` configuration runs with zero external API keys in local development mode).*

---

## 4. Running the Development Server

Start the FastAPI application with auto-reload:

```bash
uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
```

Once started:
- **API Base:** `http://127.0.0.1:8000/`
- **Health Check:** `http://127.0.0.1:8000/api/v1/health`
- **Interactive Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc Documentation:** `http://127.0.0.1:8000/redoc`

---

## 5. Running Automated Tests

Run the test suite with `pytest`:

```bash
pytest
```

To run with verbose output:
```bash
pytest -v
```

---

## 6. Frontend Integration & CORS

The backend is pre-configured with CORS middleware allowing local requests from:
- `http://localhost:5173`
- `http://127.0.0.1:5173`

In the Vite React frontend (located at the root `PS5_hack/`), API requests can be sent directly to `http://127.0.0.1:8000/api/v1/...` or via Vite proxying.

---

## 7. Phase 6, Milestone 6.1: RAG Chunking, Retrieval & Citations

Milestone 6.1 provides a zero-cost, local-first RAG retrieval infrastructure:
- **Semantic Chunker (`SchemeChunkingService`):**
  Generates 460 atomic semantic chunks across all 7 central schemes (`pm-kisan`, `pm-jay`, `pm-svanidhi`, `pmay-g`, `pm-kmy`, `pmmvy`, `pm-kusum`) in English, Hindi, Kannada, and Telugu across 6 categories:
  1. `scheme_overview`
  2. `scheme_benefit`
  3. `eligibility_clause`
  4. `exclusion_clause`
  5. `document_requirement`
  6. `application_procedure`
- **FTS5/BM25 Retriever (`RAGRetrieverService`):**
  - Searches over `scheme_chunks_fts` virtual table with BM25 ranking (`bm25(...)`).
  - Unicode combining mark and virama preservation across Devanagari, Kannada, and Telugu scripts.
  - Substring fallback for compound Indic words.
  - Substantive token overlap scoring to suppress irrelevant queries.
  - Endpoint: `GET /api/v1/schemes/rag/retrieve?query=...&language=...&limit=...`
- **Provenance-Aware Citation Engine (`CitationFormatter`):**
  - Grounds all citations strictly in verified chunk provenance metadata.
  - Clearly distinguishes `[Curated Summary from Official Guidelines]` from `[Official Quotation (Verbatim)]`.
  - Discloses all 4 verification tiers (`VERIFIED`, `PARTIALLY_VERIFIED`, `REQUIRES_OFFICIAL_VERIFICATION`, `UNVERIFIED`).
  - Generates structured citations and multilingual markdown reference lists without fabricating missing clauses or page numbers.

---

## 8. Phase 6, Milestone 6.2: Pluggable Zero-Cost LLM Provider Gateway

Milestone 6.2 establishes a provider-independent AI gateway in `backend/app/services/llm/`:
- **Common Provider Contract (`BaseLLMProvider`):** Standardizes `generate_text()`, `extract_slots()`, `stream_text()`, and `health_check()`.
- **Deterministic Baseline (`DeterministicProvider`):**
  - 100% offline, zero network requests, zero API keys, and zero model daemon dependencies.
  - Generates responses from verified scheme context and handles multilingual slot extraction across `FIELD_PROMPTS` allowlisted attributes.
  - Acts as the guaranteed final fallback.
- **Local Ollama Provider (`OllamaProvider`):**
  - Connects to local Ollama daemon (`http://127.0.0.1:11434`, configurable model `llama3.2:3b`).
  - Never auto-downloads large models.
  - Gracefully handles daemon offline, model 404, request timeout, and malformed JSON.
- **Cloud Gemini Provider (`GeminiProvider`):**
  - Optional cloud free-tier provider communicating directly with Google Gemini API from the backend.
  - Configurable model (default `gemini-3.8-flash`), timeout, and rate-limit handling.
  - Never exposes API keys in logs, responses, or error messages (redacted via `sanitize_url`).
  - Privacy guard: Transmits only de-identified query text and verified scheme context; never forwards structured citizen demographic profiles.
- **Gateway Orchestrator (`LLMGateway`):**
  - Coordinates execution across `Primary -> Secondary -> Deterministic Baseline`.
  - Safe observability via `GET /api/v1/health/llm`.

---

## 9. Phase 6, Milestone 6.3: Multilingual Slot-Filling, Intent Routing & Deterministic Orchestrator

Milestone 6.3 establishes the conversational orchestration layer in `backend/app/services/orchestration/`:
- **Intent Router (`IntentRouter`):**
  - Classifies queries into 7 standardized intents across English, Hindi, Kannada, and Telugu:
    1. `SCHEME_DISCOVERY`
    2. `SCHEME_INFORMATION`
    3. `ELIGIBILITY_CHECK`
    4. `DOCUMENT_REQUIREMENTS`
    5. `APPLICATION_GUIDANCE`
    6. `GENERAL_HELP`
    7. `UNSUPPORTED_QUERY`
  - Accurately detects target schemes across all 7 central schemes without defaulting every message to eligibility.
  - Safeguards against out-of-scope non-welfare domain inquiries (cricket, crypto, movies, stocks).
- **Multilingual Attribute Extractor (`AttributeExtractor`):**
  - Extracts only allowlisted demographic/socio-economic attributes defined in `CitizenProfileAttributes`.
  - Strict Pydantic validation (`extra="forbid"`) rejects out-of-bounds numbers and unauthorized fields.
  - Zero PII: Instantly detects and discards Aadhaar numbers, PAN cards, phone numbers, and financial credentials.
  - Detects multi-turn corrections (e.g. updating age from 25 to 45).
- **Ephemeral Session Profile Manager (`SessionProfileManager`):**
  - In-memory state storage with 30-minute idle TTL (`DEFAULT_SESSION_TTL_SECONDS = 1800`).
  - Never persists conversational transcripts or PII to disk.
  - Automatically purges expired sessions.
- **Deterministic Eligibility Orchestrator (`EligibilityOrchestrator`):**
  - Sole authority on citizen eligibility: routes validated profile attributes directly to `RuleEngineService.evaluate_scheme()`.
  - The LLM never alters or hallucinates statutory outcomes.
  - Formulates localized follow-up questions for missing required criteria using `FIELD_PROMPTS`.
  - Preserves unresolved criteria notes (e.g. statutory exclusions requiring gazette/CSC verification).
  - Clarification prompt requested if scheme is ambiguous or unspecified.
- **Response Synthesizer (`ResponseSynthesizer`):**
  - Formulates structured, citizen-friendly explanations in `en`, `hi`, `kn`, or `te`.
  - Integrates `CitationFormatter` markdown references.
  - Supplies contextual suggested follow-up questions.
- **Master Coordinator (`ConversationalOrchestrator`):**
  - Seamlessly links intent classification, attribute extraction, session state, RAG chunk retrieval, deterministic evaluation, and synthesis.

---

## 10. Phase 6, Milestone 6.4: Backend Chat API & Frontend AssistantChat Integration

Milestone 6.4 connects the React frontend (`src/pages/AssistantChat.tsx`) to the backend `ConversationalOrchestrator` via production-grade synchronous and streaming chat APIs.

### 10.1 Endpoints Specification

#### 1. Synchronous Chat: `POST /api/v1/chat`
Performs intent classification, multilingual slot extraction, profile updates, RAG retrieval, deterministic eligibility evaluation (when applicable), and grounded response generation in a single atomic request.

- **Request Schema (`ChatRequest`):**
  ```json
  {
    "message": "I am a 35 year old farmer with 1.5 hectares of land in Telangana. Am I eligible for PM-KISAN?",
    "language": "en",
    "session_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "selected_scheme_id": "pm-kisan"
  }
  ```
  - `message`: Citizen inquiry text (1 to 2,000 characters).
  - `language`: Target language code (`en`, `hi`, `kn`, `te`).
  - `session_id`: Client-generated UUIDv4 string for ephemeral session continuity.
  - `selected_scheme_id`: Optional target scheme identifier.

- **Response Schema (`ChatResponse`):**
  ```json
  {
    "answer": "Based on official guidelines for PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)...",
    "intent": "ELIGIBILITY_CHECK",
    "selected_scheme_id": "pm-kisan",
    "citations": [
      {
        "chunk_id": "pm-kisan_eligibility_clause_en_0",
        "scheme_id": "pm-kisan",
        "category": "eligibility_clause",
        "language": "en",
        "source_url": "https://pmkisan.gov.in/",
        "issuing_authority": "Ministry of Agriculture and Farmers Welfare",
        "document_title": "PM-KISAN Operational Guidelines",
        "relevant_clause": "Para 2.1 - Definition of Eligible Beneficiary Family",
        "verification_status": "VERIFIED",
        "quotation_type": "Curated Summary from Official Guidelines",
        "retrieval_score": 0.88
      }
    ],
    "formatted_citations_markdown": "### Official Sources & Provenance\n1. [PM-KISAN Operational Guidelines](https://pmkisan.gov.in/) — Para 2.1...",
    "eligibility_result": {
      "scheme_id": "pm-kisan",
      "scheme_name": {
        "en": "PM-KISAN Samman Nidhi",
        "hi": "पीएम किसान सम्मान निधि",
        "kn": "ಪಿಎಂ ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ",
        "te": "పీఎం కిసాన్ సమ్మాన్ నిధి"
      },
      "status": "ELIGIBLE",
      "summary": "You are likely eligible for PM-KISAN.",
      "satisfied_conditions": ["Citizen is a farmer", "Cultivable landholding is 1.5 hectares (≤ 2.0 hectares)"],
      "failed_conditions": [],
      "missing_prompts": [],
      "unresolved_notes": ["Exclusion: Constitutional post holders or institutional landholders"],
      "citations": []
    },
    "missing_fields": [],
    "suggested_followups": [
      "What documents are required for PM-KISAN registration?",
      "How do I apply online for PM-KISAN?"
    ],
    "profile_attributes": {
      "age": 35,
      "occupation": "farmer",
      "landholding_hectares": 1.5,
      "state": "Telangana"
    },
    "session_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
  }
  ```

#### 2. Streaming Chat: `POST /api/v1/chat/stream`
Streams Server-Sent Events (SSE) for low-latency conversational feedback, delivering incremental tokens, grounding citations, eligibility determinations, follow-up chips, and real-time profile updates.

- **SSE Event Protocol:**
  | Event Name | Payload Description |
  | :--- | :--- |
  | `metadata` | Initial classification metadata (`intent`, `selected_scheme_id`, `language`, `session_id`). |
  | `token` | Incremental generated text token: `{"text": "Based on "}`. |
  | `citations` | Structured citation items and formatted markdown reference list. |
  | `eligibility` | Statutory deterministic eligibility assessment outcome. |
  | `followups` | Suggested contextual follow-up questions. |
  | `profile` | Current cumulative validated citizen profile attributes. |
  | `done` | Lifecycle completion signal: `{"status": "completed", "session_id": "..."}`. |
  | `error` | Safe error envelope if generation encounters an exception. |

#### 3. Reset Session: `POST /api/v1/chat/reset`
Explicitly clears session profile attributes when a user clicks "Start New Conversation" or switches citizens.
- **Request:** `{"session_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"}`
- **Response:** `{"session_id": "...", "status": "cleared", "message": "Session profile cleared successfully."}`

---

### 10.2 Privacy & Security Architecture

1. **Active PII Scrubbing (`scrub_pii`):**
   - Non-destructive regex scrubber cleans raw user input before logging, caching, or LLM invocation.
   - Redacts 12-digit Aadhaar (`[AADHAAR_REDACTED]`), 10-character PAN (`[PAN_REDACTED]`), 10-digit Indian mobile numbers (`[PHONE_REDACTED]`), bank account numbers (`[BANK_ACCOUNT_REDACTED]`), and security pins/OTPs (`[SECRET_REDACTED]`).
   - Carefully avoids false positives on ordinary numbers (e.g. age 35, 2 hectares, ₹6,000 benefit amounts).
2. **Zero Profile Forwarding to Cloud LLMs:**
   - Structured citizen profile attributes (`age`, `income`, `caste`, `state`, etc.) are processed **exclusively by the local deterministic rule engine**.
   - Cloud providers (Gemini) receive only sanitized query text and retrieved official scheme text chunks.
3. **Zero Transcript Persistence:**
   - In accordance with DPDP Act best practices, raw conversational transcripts are never persisted to SQLite, disk, or remote analytics.
4. **Ephemeral Session Management:**
   - In-memory single-process session store with a 30-minute idle TTL (`DEFAULT_SESSION_TTL_SECONDS = 1800`).
   - Unauthenticated sessions automatically expire and self-purge.
   - Server restarts or cluster reloads cleanly reset sessions to empty profiles without corrupting state.
5. **Strict Input Sanitization:**
   - All Pydantic models enforce `extra="forbid"`.
   - String length bounded to 2,000 characters.
   - Session identifiers strictly validated against UUIDv4 regex.

---

### 10.3 Frontend Integration (`AssistantChat.tsx`)

The React frontend integrates with the backend chat APIs via `src/services/chatApi.ts`:
- **Real-Time Streaming:** Uses Fetch API with `ReadableStream` to consume SSE events incrementally, rendering text as it arrives.
- **Cancellation / Abort:** Incorporates `AbortController` to cancel ongoing streams if the user navigates away or submits a new query.
- **REST Fallback:** Automatically falls back to synchronous `POST /api/v1/chat` if SSE connection drops or is unsupported.
- **Visual Citations & Provenance:** Renders collapsible/expandable citation cards linking to official government portals with explicit verification badges (`VERIFIED`, `PARTIALLY_VERIFIED`).
- **Interactive Eligibility Cards:** Directly renders authoritative statutory outcomes (`ELIGIBLE`, `NOT_ELIGIBLE`, `POSSIBLY_ELIGIBLE`), satisfied rules, and missing-field inquiry chips. Frontend labels (e.g. "Preliminary / Possibly Eligible") are strictly presentation-level mappings that cannot alter statutory status.
- **Profile Synchronization:** Updates the UI profile attribute drawer in real-time as attributes are extracted during natural dialogue.
- **Voice Integration:** Integrates speech-to-text mic modal and browser text-to-speech read-aloud for accessibility across `en`, `hi`, `kn`, and `te`.

### 10.4 Single-Process In-Memory Session Limitations
- **Memory Footprint:** Conversational session profiles are stored strictly in Python process heap memory via `SessionProfileManager`.
- **Horizontal Scaling:** When scaling backend instances horizontally across multiple Uvicorn worker processes or cluster nodes, sticky sessions (IP-hash or ingress affinity) or a shared cache (e.g. Redis) is required to ensure multi-turn continuity across requests.
- **Process Restarts:** Restarting the FastAPI service clears active session state, safely falling back to fresh default profiles without corrupted database artifacts.

### 10.5 Anonymous Session Token Bearer Security & Limitations
- **Anonymous Data Minimization:** In adherence to the Digital Personal Data Protection (DPDP) Act, Yojana Saathi does not require user accounts, phone numbers, or passwords to discover welfare schemes and evaluate eligibility.
- **Unpredictable Bearer Tokens:** Each ephemeral session is identified by a cryptographically secure random UUIDv4 token ($2^{122}$ bits of entropy generated via CSPRNG). This unpredictable token acts as an anonymous bearer credential for the duration of the conversation.
- **Token Protection & Privacy:**
  - Session tokens are strictly excluded from all application logs and telemetry.
  - Raw citizen messages and demographic profiles are kept in volatile React memory only; they are never written to `localStorage`, `sessionStorage`, SQLite, or disk.
  - Ephemeral session profiles auto-expire after 30 minutes of inactivity and are permanently erased on server-side cleanup.
- **Architectural Limitations:**
  - UUIDv4 validation enforces syntax and entropy, but does not provide cryptographically signed identity authentication. Possession of the bearer token authorizes access to that specific ephemeral in-memory profile.
  - If a device is shared (e.g. at a public Common Service Centre kiosk), a subsequent user on the exact same browser tab could access recent in-memory dialogue unless "Start New Conversation" or tab close is triggered.
  - For kiosk and public device deployments, always trigger `resetSession()` / `clearChat()` upon citizen departure.

---

## 11. Phase 6, Milestone 6.5: Speech Subsystem Hardening (STT & TTS)

Milestone 6.5 hardens the multilingual speech recognition (STT) and speech synthesis (TTS) subsystems across **English (`en-IN`)**, **Hindi (`hi-IN`)**, **Kannada (`kn-IN`)**, and **Telugu (`te-IN`)** under a zero-cost, local-first architecture.

### 11.1 Speech Recognition (STT) Architecture
- **Engine:** Browser-native W3C Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`).
- **Locales:** Explicitly mapped in `SPEECH_LOCALES` (`en-IN`, `hi-IN`, `kn-IN`, `te-IN`). Language selection immediately updates recognition locale without requiring page reloads.
- **Error Handling & State Recovery:**
  - `permission_denied` (`not-allowed`, `service-not-allowed`): Renders clear guidance on enabling microphone access in browser settings.
  - `no_microphone` (`audio-capture`): Detects missing audio input hardware.
  - `network_error` (`network`): Detects disconnection from browser vendor speech services.
  - `no_speech`: Handles silence timeouts gracefully without terminating the session.
  - Inactivity Timeout: Auto-terminates microphone capture after 12 seconds of silence to prevent resource leaks.
- **Transcript Assembly:** Aggregates interim and final transcripts without dropping syllables or repeating words.
- **Duplicate Prevention:** Modal submission buttons and Enter-key handlers use submission locks (`isSubmittingRef`) to reject rapid duplicate dispatches.
- **Accessible Alternatives:** Keyboard navigation (Escape to cancel, Enter to submit, Space to toggle mic) and one-click "Type Instead" switch.

### 11.2 Speech Synthesis (TTS) Architecture
- **Engine:** Browser-native `window.speechSynthesis`.
- **Chromium Cutoff Bug Fix (`splitTextIntoSpeechChunks`):** Chromium browsers silently pause or freeze utterances exceeding ~15 seconds / 200 characters. Yojana Saathi dynamically partitions long responses into punctuation-bounded chunks ($\le 160$ characters) along sentences, clauses, and Indic dandas (`।`), streaming them sequentially through an utterance queue.
- **Voice Matching & Graceful Fallback:**
  - Priority 1: Exact locale match (`hi-IN`, `kn-IN`, `te-IN`, `en-IN`).
  - Priority 2: Language prefix match (`hi`, `kn`, `te`).
  - Priority 3: Name hint matching (e.g. "Lekha", "Hindi", "Kannada", "Telugu").
  - Missing Voice Detection: If a client operating system lacks an installed Indic voice (e.g. Telugu voice missing on Linux/older macOS), the system detects this without throwing, flags `voiceUnavailableWarning`, shows an informative banner, and presents the complete text answer, citations, and eligibility results. It never mispronounces Indic text with an English synthesizer.
- **Speech Controls:** Supports `speak()`, `stop()`, `pause()`, `resume()`, speech rate adjustment (0.5x to 2.0x), and auto-read toggle.
- **Overlapping Prevention:** Cancels any ongoing synthesis before beginning new utterances or upon route transitions / conversation reset.

### 11.3 Privacy & Vendor Engine Disclosures
- **Zero Audio Storage:** Raw audio is never recorded, buffered to disk, or sent to backend servers.
- **Vendor Engine Transparency:** Clearly discloses in the UI that Web Speech API speech recognition may route audio through browser vendor servers (Google on Chrome/Android, Apple on Safari) and is not guaranteed to operate 100% offline.
- **Data Minimization:** No paid cloud speech APIs (AWS Polly, Google Cloud STT, ElevenLabs) are used. Transcripts remain in volatile memory and are scrubbed for PII via `scrub_pii()` before server evaluation.

### 11.4 Manual Testing Instructions across All 4 Languages
1. **English (`en-IN`)**:
   - Select English flag in header. Click mic icon. Speak: *"Am I eligible for PM-KISAN? I am a farmer with 1.5 hectares of land."*
   - Verify speech is captured as `en-IN`, eligibility card renders `ELIGIBLE`, and Listen Aloud plays English voice.
2. **Hindi (`hi-IN`)**:
   - Switch language to Hindi. Click mic icon. Speak: *"क्या मैं आयुष्मान भारत योजना के लिए पात्र हूँ?"*
   - Verify transcript renders in Devanagari script, intent classifies as `ELIGIBILITY_CHECK` / `SCHEME_INFORMATION`, and Hindi voice reads aloud.
3. **Kannada (`kn-IN`)**:
   - Switch language to Kannada. Click mic icon. Speak: *"ಪಿಎಂ ಕಿಸಾನ್ ಯೋಜನೆಗೆ ಯಾರು ಅರ್ಹರು?"*
   - Verify transcript renders in Kannada script, verified citations display in Kannada, and TTS uses Kannada voice if available.
4. **Telugu (`te-IN`)**:
   - Switch language to Telugu. Click mic icon. Speak: *"పీఎం స్వనిధి పథకం ద్వారా ఎంత రుణం లభిస్తుంది?"*
   - Verify transcript renders in Telugu script, response displays micro-loan benefits with official citations, and system handles Telugu voice appropriately.
5. **Microphone Permission Denial Test**:
   - Block microphone in browser site settings and click mic icon. Verify clear warning banner appears advising citizen to allow permission, with direct "Type Instead" button enabled.
6. **Long Response Utterance Test**:
   - Ask for detailed application steps. Verify speech synthesis chunks sentences sequentially without stalling at the 15-second boundary.

---

## 12. Phase 6, Milestone 6.6: Offline Edge Hardening & PWA/Service Worker

Milestone 6.6 establishes Progressive Web App (PWA) installability, robust offline application-shell caching, reactive network status indicators, and multilingual resilience states while strictly maintaining the zero-cost, local-first privacy architecture.

### 12.1 Web App Manifest & Installability
- **Manifest File:** `public/manifest.webmanifest` (served at `/manifest.webmanifest`).
  - App Name: `Yojana Saathi — Voice AI for Government Schemes`
  - Short Name: `Yojana Saathi`
  - Scope & Start URL: `/`
  - Display: `standalone`
  - Theme / Background Colors: `#4F46E5` (Brand Indigo) / `#F8FAFC` (Neutral Canvas)
  - Icons: High-resolution vector SVG (`/icon.svg`) and raster icons (`/icon-192.png`, `/icon-512.png`).
- **In-App Install Prompt:** Captures browser `beforeinstallprompt` event via `useNetworkStatus()` hook and presents an accessible "Install App" action bar without intrusive popups.

### 12.2 Service Worker Caching Strategies (`public/sw.js`)
- **Versioned Cache:** `yojana-saathi-shell-v1`
- **Precache Assets:** App shell files (`/`, `/index.html`, `/manifest.webmanifest`, `/icon.svg`, `/icon-192.png`, `/icon-512.png`).
- **Cache Management:** The `activate` event inspects `caches.keys()`, purging all obsolete versions automatically, followed by `clients.claim()` for immediate control.
- **Routing & Fetch Strategies:**
  1. **HTML Navigation Requests (`request.mode === 'navigate'`):** Network-first with cache fallback to `/index.html`. Enables client-side React routes (`/assistant`, `/browse`, `/language`, `/settings`) to load seamlessly even when offline.
  2. **Static Assets (JS, CSS, images, web fonts):** Cache-first with network fallback and background revalidation.
  3. **Non-GET Requests:** Immediately passed through to the network (`request.method !== 'GET'`). Non-idempotent dispatches are never intercepted.

### 12.3 Strict Anti-Caching & Privacy Policies
To prevent leaking sensitive citizen information and misleading citizens with stale dynamic data:
- **Zero API Caching:** All `/api/*` endpoints (specifically `/api/v1/chat`, `/api/v1/chat/stream`, `/api/v1/documents/collect`, and `/api/v1/rules/evaluate`) are **strictly network-only**.
- **Offline API Fallback:** If an API endpoint is requested while offline, the service worker catches the network failure and returns an explicit `503 Service Unavailable` JSON response (`{"error": "offline", "detail": "..."}`) rather than fabricating an answer or reading stale cache.
- **Zero Sensitive Data Storage:** Citizen profile attributes, conversational chat transcripts, bearer session tokens, and authentication credentials are **never stored** in Cache Storage or disk databases.
- **Zero Third-Party Cloud Caching:** External LLM or cloud API endpoints (e.g. `googleapis.com`, `gemini`) are strictly excluded from caching.

### 12.4 Offline Capabilities vs. Online Requirements

| Feature / Domain | Offline Availability | Behavior when Disconnected |
| :--- | :--- | :--- |
| **App Shell & UI** | 100% Available | Cached app shell loads immediately. |
| **Scheme Directory** | Available (Static Guidelines) | 7 central schemes and static guidelines can be browsed. |
| **Document Checklists** | Available (Static Checklists) | Required documents and criteria guidelines can be reviewed. |
| **Live Conversational AI & RAG** | Requires Internet | Disabled in UI; displays offline banner; input and mic buttons disabled. |
| **Deterministic Rule Engine (Server)** | Requires Local/Server Network | In web deployment, dynamic API evaluation requires connection to backend. |
| **Speech Recognition (STT)** | Requires Browser Vendor Network | Web Speech API voice capture is disabled with guidance to connect. |

### 12.5 Network Resilience & Submission Safeguards
- **Reactive Status Banner (`OfflineBanner.tsx`):**
  - Displays localized offline banner with accessible `role="status"` and `aria-live="polite"`.
  - Includes expandable feature breakdown explaining offline capabilities vs. online requirements.
  - "Check Connection" button performs cache-busted connection verification.
  - Temporary green banner confirms reconnection when network is restored.
- **Zero Auto-Replay:**
  - The application **strictly forbids** automatic queuing or background replay of chat messages or eligibility requests upon reconnection.
  - When connection is restored, the citizen retains their draft in the input field and explicitly chooses to click Send, ensuring no unmonitored or unintended queries are fired.

### 12.6 Manual Testing Instructions for PWA & Offline Resilience
1. **Manifest & App Shell Verification:**
   - Open Chrome DevTools -> Application tab -> Manifest.
   - Verify App name (`Yojana Saathi — Voice AI for Government Schemes`), icons (192px, 512px, SVG), theme color (`#4F46E5`), and display mode (`standalone`).
2. **Service Worker Registration:**
   - Open Chrome DevTools -> Application tab -> Service Workers.
   - Verify `sw.js` is active and running with scope `/`.
3. **Offline App-Shell Loading:**
   - In Chrome DevTools -> Network tab, set throttling to "Offline".
   - Reload page (`Cmd+R` / `F5`).
   - Verify the application shell loads immediately from cache without browser error ("No internet").
   - Navigate to `/browse` and `/resilience-states` while offline; confirm routes render without network requests.
4. **Offline Chat Guard & Anti-Replay:**
   - While offline, navigate to `/assistant`.
   - Verify the top offline banner appears with "Offline Mode" badge.
   - Verify the input dock shows the offline alert: *"Conversational AI and RAG search are unavailable offline. Cached scheme details can be browsed without network."*
   - Verify microphone button and Send button are disabled.
   - In Network tab, switch back to "Online" (or No throttling).
   - Verify green reconnection notice appears: *"Connection restored. Live AI services are now available."*
   - Verify input is re-enabled and old messages were **not** auto-submitted.
5. **Cache Storage Privacy Audit:**
   - Open DevTools -> Application tab -> Storage -> Cache Storage -> `yojana-saathi-shell-v1`.
   - Inspect all cached URLs:
     - Verify **only** static assets exist (`/`, `/index.html`, `/manifest.webmanifest`, `/icon.svg`, `/icon-192.png`, `/icon-512.png`, CSS, JS).
     - Verify **no** `/api/` endpoints, `/api/v1/chat`, or transcripts appear in Cache Storage.









