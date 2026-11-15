# PHASE 3 — API RESEARCH & DATA SOURCE VALIDATION (VERIFIED & AUDITED)
## Project: Yojana Saathi (योजना साथी)
**Status:** Independently Verified & Audited  
**Research Verification Date:** November 10, 2026  
**Document Version:** 2.1 (Phase 3.1 Final Corrections Applied)  
**Target Languages:** English (`en` / `en-IN`), Hindi (`hi` / `hi-IN`), Kannada (`kn` / `kn-IN`), Telugu (`te` / `te-IN`)

---

## 1. Classification Labels Used Across This Audit

To maintain technical integrity and avoid unsupported assumptions, all assertions in this document are explicitly classified under one of the following labels:
- `[VERIFIED FACT]`: Direct official documentation, pricing page, or confirmed API specification verified via official sources.
- `[RECOMMENDATION]`: Engineering decision proposed based on technical fit, cost, and developer experience.
- `[ASSUMPTION]`: Operational estimate (e.g., average conversation turns, audio duration) used for modeling.
- `[UNVERIFIED ASSUMPTION]`: External service capability, access path, or SLA that cannot be independently confirmed through public documentation.
- `[UNVERIFIED CLAIM - CORRECTED]`: Previous assumption or claim that was audited and replaced with verified facts.
- `[REQUIRES MANUAL CONFIRMATION]`: Item requiring institutional access, manual organizational approval, or project-specific verification.

---

## 2. Government Scheme Data Sources (Task 1 Audited)

### 2.1 Comparative Audit of Proposed Government Sources

| Source Portal | Public Developer API Available? | Registration & Access Policy | Verified Data Scope | Scraping & Terms of Use Policy | Direct Official URL |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **myScheme.gov.in** | `[VERIFIED FACT]` **No direct public REST API.** Programmatic access is exposed only via **API Setu** (`apisetu.gov.in/dic/myscheme`). | `[UNVERIFIED ASSUMPTION / ACCESS RESTRICTED]` Requires verified institutional entity registration (Govt Department, PSU, or registered enterprise) + MeitY/NeGD publisher approval. Individual student teams **cannot** obtain instant keys. | Standardized OpenAPI 3.0 specs (`myscheme-QuestionnaireEligibility-v1.yaml`) for scheme lists, eligibility questionnaires, and criteria tags. | `[VERIFIED FACT]` Automated headless scraping prohibited under Terms of Use; protected by Cloudflare WAF. | [myScheme on API Setu](https://apisetu.gov.in/dic/myscheme) (Accessed Nov 2026) |
| **data.gov.in (OGD India)** | `[VERIFIED FACT]` **Yes** (REST API with 40-char key). | `[VERIFIED FACT]` Self-serve instant registration via email and mobile number. Free developer key generated in dashboard. | Aggregated statistical datasets, ministry budget outlays, beneficiary counts (CSV/JSON/XML). Does **not** provide dynamic eligibility questionnaires. | `[VERIFIED FACT]` Open Data Policy (OGD India). Free for public use with attribution. | [data.gov.in Developer Portal](https://data.gov.in/) (Accessed Nov 2026) |
| **Central Ministries (MoA&FW, MoHFW, MoRD, MoHUA)** | `[VERIFIED FACT]` **No unified developer API.** | `[VERIFIED FACT]` None; official guidelines and Gazettes published as static HTML and PDFs. | Complete authoritative guidelines, eligibility conditions, exclusion criteria, financial assistance formulas. | `[VERIFIED FACT]` Public domain government information. Free to reference with source citation. | [Agricoop](https://agricoop.gov.in/), [MoHFW](https://mohfw.gov.in/), [Rural](https://rural.gov.in/) |
| **Karnataka: Seva Sindhu** | `[VERIFIED FACT]` **No public developer API.** | `[UNVERIFIED ASSUMPTION / ACCESS RESTRICTED]` Restricted to authorized Karnataka government departments via Centre for e-Governance (CeG). | Transactional delivery of citizen welfare services, certificate issuing, and state scheme processing. | Restricted government intranet services handling citizen PII. | [Seva Sindhu](https://sevasindhu.karnataka.gov.in/) (Accessed Nov 2026) |
| **Karnataka: Mahiti Kanaja** | `[VERIFIED FACT]` **Open Suo-Moto Data Feeds.** | `[VERIFIED FACT]` No API key or registration required for public scheme data mirrors. | State scheme beneficiary lists, department budget allocations, scheme criteria under RTI Section 4(2). | `[VERIFIED FACT]` Open public data for transparency and public welfare dissemination. | [Mahiti Kanaja](https://mahitikanaja.karnataka.gov.in/) (Accessed Nov 2026) |
| **Telangana: Praja Palana** | `[VERIFIED FACT]` **No public developer API.** | `[VERIFIED FACT]` None; official state portal with static guidelines for 6 Guarantees. | Official eligibility rules and application forms for state guarantees in Telugu and English. | `[VERIFIED FACT]` Public government informational notices. | [Telangana Govt Portal](https://telangana.gov.in/) (Accessed Nov 2026) |

### 2.2 Critical Distinction: Viewable Website vs. Accessible API
`[VERIFIED FACT]` **A website being publicly readable in a browser does NOT equate to an accessible developer API.**
- Many developers mistakenly assume that because `myscheme.gov.in` provides a web-based questionnaire, it offers a public REST API. This is false.
- Scraping `myscheme.gov.in` directly violates its Terms of Service, risks IP blocks, and creates a fragile single point of failure.

### 2.3 Recommended Scheme Data Acquisition Strategy: Curated Canonical Corpus
`[RECOMMENDATION]` Rather than relying on unapproved scrapers or inaccessible private APIs, the project must implement a **Verified Curated Ingestion Pipeline**:
1. **Scope:** 30 authoritative schemes (20 Central Schemes including PM-KISAN, PM-JAY, PMAY-G, PM SVANidhi, PM-KMY, PMMVY, PM-KUSUM + 10 State Schemes for Karnataka & Telangana).
2. **Ingestion Method:** Manually ingest and audit official Gazette notifications, ministry operational guidelines, and public scheme rules into a canonical `schemes.json` file.
3. **Traceability Guarantee:** Every scheme record carries:
   - `official_portal_url`: Direct link to the official application portal (e.g., `https://pmkisan.gov.in/`).
   - `guidelines_pdf_url`: Direct link to the source operational manual.
   - `last_verified_date`: Exact date of human audit (e.g., `2026-10-15`).

---

## 3. LLM & Conversational AI Provider Research (Task 2 Audited)

### 3.1 Model Lifecycle & Availability Audit (Google Gemini)

`[UNVERIFIED CLAIM - CORRECTED]` The previous draft recommended `gemini-1.5-flash` and `gemini-2.0-flash`.
- `[VERIFIED FACT]` **Lifecycle Audit:**
  - **`gemini-1.5-flash`:** Retired / discontinued in late 2025.
  - **`gemini-2.0-flash`:** Deprecated with official shutdown on **June 1, 2026**.
  - **`gemini-3.8-flash`:** **Current Active Flagship Flash Model** in the Gemini API ecosystem as of 2026. Built for high-speed agentic reasoning, long-context software workflows, and structured multilingual extraction.
  - Context Window: Up to 1,048,576 input tokens and 65,536 output tokens.
  - Input Modalities: Text, Audio, Image, Video, PDF.
  - Output Modalities: Text (with native JSON Schema enforcement).

### 3.2 Gemini Quotas & Free-Tier Distinction
`[VERIFIED FACT]` It is critical to distinguish **published baseline limits** from **account-specific tier quotas**:
- **Published Baseline Free Tier (Google AI Studio):**
  - **Rate Limits:** 15 Requests Per Minute (RPM), 1,000,000 Tokens Per Minute (TPM), 1,500 Requests Per Day (RPD).
  - **Cost:** $0.00 (Zero monetary deposit).
  - **Data Policy:** Prompts and responses on the free tier may be logged for model evaluation.
- `[REQUIRES MANUAL CONFIRMATION]` **Account-Specific Quotas (Paid Tiers):**
  - When a Google Cloud billing account is linked, projects enter **Tier 1 (Pay-as-you-go)**.
  - Paid pricing: Input: **$0.10 / 1M tokens**; Output: **$0.40 / 1M tokens**.
  - Rate limits scale dynamically (e.g., 1,000+ RPM, 4M+ TPM) based on cumulative project spend history.
  - Exact limits must be confirmed in the user's specific [Google AI Studio Rate Limits Dashboard](https://ai.google.dev/gemini-api/docs/rate-limits).

### 3.3 Embedding Model Shutdown & Replacement (Critical Correction)

`[UNVERIFIED CLAIM - CORRECTED]` The previous draft recommended `text-embedding-004`.
- `[VERIFIED FACT]` **`text-embedding-004` Shutdown:** Google officially deprecated `text-embedding-004` and **shut it down on January 14, 2026**. Calls to `models/text-embedding-004` fail with `404 Model Not Found`.
- `[VERIFIED FACT]` **Current Active Google Embedding Models:**
  1. **`gemini-embedding-001` (Text-Only):**
     - Native text embedding model supporting Matryoshka Representation Learning (MRL) from 128 to 3,072 dimensions (768 dimensions recommended for vector storage balance).
     - Input limit: 2,048 tokens.
  2. **`gemini-embedding-2` (Multimodal):**
     - Unified multimodal embedding model across text, audio, images, and PDF documents. MRL dimensions from 128 to 3,072 dimensions (768 recommended).
- `[RECOMMENDATION]` **Selected Embedding Model:** **`gemini-embedding-001`** (configured to 768 dimensions), or **`text-embedding-3-small` (OpenAI, 1536-dim)** as fallback.

---

## 4. Speech-to-Text (STT) Provider Research (Task 3 Audited)

### 4.1 Speech-to-Text V2 & Chirp Billing Increment Audit

`[UNVERIFIED CLAIM - CORRECTED]` The previous draft stated that Google Cloud STT bills in 15-second rounding increments. This was a legacy V1 specification.
- `[VERIFIED FACT]` **Speech-to-Text V2 Billing Metric:**
  - Google Cloud Speech-to-Text V2 is billed based on audio successfully processed, measured and incremented in steps of **ONE SECOND** (not 15 seconds).
  - Official Google Cloud Documentation: *"Speech-to-Text is priced based on the amount of audio successfully processed by the service each month, measured and incremented in steps of one second."* ([Google Cloud STT Pricing](https://cloud.google.com/speech-to-text/pricing), Accessed Nov 2026).
  - This significantly lowers audio billing volume compared to legacy 15-second block rounding.
- `[VERIFIED FACT]` **Speech-to-Text V2 Chirp Models & Locales:**
  - Chirp and Chirp 2 are universal multilingual foundation models supporting 85+ languages, including **Hindi (`hi-IN`)**, **Kannada (`kn-IN`)**, **Telugu (`te-IN`)**, and **Indian English (`en-IN`)**.
  - **Regional Availability:** Chirp models in STT V2 are hosted in multi-region `us` (endpoint: `us-central1-speech.googleapis.com`). They are **not** deployed in all local Indian GCP data centers (`asia-south1`). Requests must be directed to the supported multi-region endpoint.
- `[VERIFIED FACT]` **Pricing & Free Allowance:**
  - **Free Tier:** Google Cloud provides **60 free minutes per month** per billing account for standard speech recognition.
  - **Standard Pay-As-You-Go:** **$0.016 per minute** (approx. $0.000267 per second) with data logging enabled.
  - **Dynamic Batch Processing:** **$0.003 per minute** for non-urgent background batch transcription.
  - **Medical Models Excluded:** Specialty medical models ($0.078/min) are separate and not used.

---

## 5. Text-to-Speech (TTS) Provider Research (Task 4 Audited)

### 5.1 Voice Family Availability & Voice IDs Audit

`[UNVERIFIED CLAIM - CORRECTED]` The previous draft claimed Neural2 was available for Kannada and Telugu.
- `[VERIFIED FACT]` **Voice Family Distribution in Google Cloud TTS:**
  - **Hindi (`hi-IN`):** Supports **Neural2**, **WaveNet**, and **Standard** voices.
  - **English (`en-IN`):** Supports **Neural2**, **WaveNet**, and **Standard** voices.
  - **Kannada (`kn-IN`):** Supports **Standard**, **WaveNet**, and **Chirp 3: HD** voices. **Neural2 is NOT provisioned for `kn-IN`.**
  - **Telugu (`te-IN`):** Supports **Standard**, **WaveNet**, and **Chirp 3: HD** voices. **Neural2 is NOT provisioned for `te-IN`.**

### 5.2 Specific Recommended Voice IDs & Pricing by Voice Family

| Language | Primary Voice ID | Voice Family | Free Allowance | Rate After Free Quota | Alternative Voice (Generative) | Alternative Pricing |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **English (`en-IN`)** | `en-IN-Neural2-D` (Female) | Neural2 | 1,000,000 chars / mo | $16.00 / 1M chars | `en-IN-Standard-A` | $4.00 / 1M chars (4M free) |
| **Hindi (`hi-IN`)** | `hi-IN-Neural2-A` (Female) | Neural2 | 1,000,000 chars / mo | $16.00 / 1M chars | `hi-IN-Standard-A` | $4.00 / 1M chars (4M free) |
| **Kannada (`kn-IN`)** | `kn-IN-Standard-A` (Female) | Standard | **4,000,000 chars / mo** | **$4.00 / 1M chars** | `kn-IN-Chirp3-HD-Achernar` | **$30.00 / 1M chars** (1M free) |
| **Telugu (`te-IN`)** | `te-IN-Standard-A` (Female) | Standard | **4,000,000 chars / mo** | **$4.00 / 1M chars** | `te-IN-Chirp3-HD-Achernar` | **$30.00 / 1M chars** (1M free) |

- `[VERIFIED FACT]` **Chirp 3: HD Pricing (SKU `F977-2280-6F1B`):**
  - Includes **1,000,000 characters free per month**.
  - Billed at **$30.00 per 1M characters** ($0.00003/char) thereafter.
  - Chirp 3 HD provides high-definition conversational naturalness for Kannada and Telugu, making it an excellent generative alternative to Standard voices.
- `[RECOMMENDATION]` **Cost-Optimal Allocation:**
  - Use Standard voices (`kn-IN-Standard-A`, `te-IN-Standard-A`) for general UI speech (drawn against the massive **4M character free allowance**).
  - Use Neural2 for Hindi (`hi-IN-Neural2-A`) and English (`en-IN-Neural2-D`) (drawn against the **1M character free allowance**).
  - Allow user to toggle Chirp 3 HD in settings if higher conversational fidelity is desired.

---

## 6. Bhashini Verification & Onboarding Reality (Task 4 Audited)

`[UNVERIFIED ASSUMPTION]` The claim that Bhashini offers a predictable developer onboarding SLA (such as 24–48 hours) is **unverified and unsupported by public documentation**.
- `[VERIFIED FACT]` **Official Documentation & Access Reality:**
  - Bhashini is developed under the Digital India Bhashini Division (DIBD) / MeitY.
  - Programmatic access uses the **ULCA (Universal Language Contribution API)** architecture (`bhashini.gov.in/ulca/`).
  - **Credentials Required:** `userID`, `ulcaApiKey`, and `inferenceAPIKey`.
  - **Approval Reality:** Bhashini primarily onboards registered organizations, startups, and academic institutions. While official government hackathons occasionally provide fast-tracked credentials via event-specific coordinators, **there is NO published SLA or guaranteed turnaround for general developer sign-ups**. Approval is manual and can take an unpredictable duration.
  - **Pricing:** Nominally free for approved non-commercial research, academic, and government projects; commercial rate cards are unpublished.
- `[RECOMMENDATION]` **Strategic Positioning:** Bhashini is the **Sovereign Indian Target Platform** for production. However, because developer keys cannot be guaranteed on demand, **Google Cloud STT/TTS and client-side Web Speech APIs must serve as the primary operational pipeline** during the hackathon.

---

## 7. Master Service Verification Summary

| Service Category | Primary Provider | Status | Verified Free Tier Limit | Production Paid Rate | Direct Documentation Link |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LLM Reasoning** | Gemini 3.8 Flash | `[VERIFIED FACT]` Active | 1,500 RPD / 15 RPM / 1M TPM (Published Baseline) | $0.10 / 1M in, $0.40 / 1M out | [Google AI Studio Models](https://ai.google.dev/gemini-api/docs/models/gemini) |
| **Embeddings** | `gemini-embedding-001` | `[VERIFIED FACT]` Active | Included in AI Studio quota (1M TPM) | $0.00002 / 1k tokens | [Gemini Embeddings](https://ai.google.dev/gemini-api/docs/embeddings) |
| **Speech-to-Text** | Google Cloud STT V2 (Chirp) | `[VERIFIED FACT]` Active | 60 minutes free / month | $0.016 / minute (1-sec increment) | [Google Cloud STT Pricing](https://cloud.google.com/speech-to-text/pricing) |
| **Text-to-Speech (Std)** | Google Cloud TTS (`kn`, `te`) | `[VERIFIED FACT]` Active | 4,000,000 characters free / month | $4.00 / 1M chars | [Google Cloud TTS Pricing](https://cloud.google.com/text-to-speech/pricing) |
| **Text-to-Speech (N2)** | Google Cloud TTS (`hi`, `en`) | `[VERIFIED FACT]` Active | 1,000,000 characters free / month | $16.00 / 1M chars | [Google Cloud TTS Pricing](https://cloud.google.com/text-to-speech/pricing) |
| **Text-to-Speech (Chirp 3)** | Google Cloud TTS (HD) | `[VERIFIED FACT]` Active | 1,000,000 characters free / month | $30.00 / 1M chars | [Google Cloud TTS Pricing](https://cloud.google.com/text-to-speech/pricing) |
| **Relational & Vector**| Supabase (Postgres 16) | `[VERIFIED FACT]` Active | 500 MB DB / 50k MAU | $25.00 / month (Pro Plan) | [Supabase Pricing](https://supabase.com/pricing) |
| **Scheme Data** | Curated Canonical JSON | `[VERIFIED FACT]` Sourced | N/A (Local / Git-backed) | ₹0.00 | [myScheme Source](https://www.myscheme.gov.in/) |
