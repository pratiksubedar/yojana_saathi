# Site: Yojana Saathi (योजना साथी)
**Stitch Project ID:** 12693025408682747803
**Platform Architecture:** Responsive Web Application (React + TypeScript)

## 1. Core Identity & Platform Strategy

- **Project Name:** Yojana Saathi (योजना साथी)
- **Application Type:** **Responsive Web Application** built using **React** on the frontend, serving mobile, tablet, and desktop users from a unified codebase.
- **Mission:** A voice-first, multilingual AI assistant that helps Indian citizens discover government welfare schemes they may qualify for, explains benefits in simple language, and provides official source citations — without making unsupported eligibility claims.
- **Target Audience:** Indian citizens seeking welfare scheme information across all devices (smartphones, tablets, desktop computers at home, CSC kiosks, or cyber cafés). Ages 18-80+, diverse regional languages, varied digital confidence.
- **Voice:** Trustworthy, simple, reassuring, respectful, transparent. Never bureaucratic or condescending.

## 2. Platform Architecture & Responsive Design Rules

### 2.1 Unified React Frontend
- **Single Codebase:** The entire application runs on one React web client and one backend API across all form factors.
- **Responsive Methodology:** Mobile-first component design using Tailwind CSS responsive modifiers (`sm:`, `md:`, `lg:`, `xl:`).
- **Core Breakpoints:**
  - **Mobile (< 640px):** Single-column stacked layout, full-width touch cards, sticky top header, floating/sticky bottom voice & text input bar.
  - **Tablet (640px - 1023px):** Centered content column (max-width 640px - 768px), balanced whitespace, expanded 2-column card discovery grids.
  - **Desktop (≥ 1024px):** Purpose-built wide-screen layouts (not merely stretched mobile views):
    * Split-pane layouts for the main conversation (Left: active voice/chat dialogue; Right: live profile attribute panel & matching scheme cards).
    * Multi-column card grids for the Scheme Directory & Browse view.
    * Persistent, accessible desktop navigation header with quick language switcher and settings.
    * Centered reading columns (max-w-4xl) to prevent unreadable ultra-wide text lines.

### 2.2 Voice Interaction Across Screen Sizes
- **Central Feature on All Devices:** Voice input is a first-class citizen whether using a smartphone microphone, tablet, or desktop headset/webcam mic.
- **Desktop Voice Ergonomics:**
  - Dedicated, prominent desktop microphone button with visual state feedback (idle, listening wave, processing spinner).
  - Optional desktop hotkey support (e.g., hold Spacebar to speak) for high-efficiency navigation.
- **Audio Output:** Spoken response playback with dedicated replay controls and audio volume adjustments accessible across all devices.

### 2.3 Text Fallback Parity
- **100% Feature Parity:** Text input is permanently available alongside voice across mobile, tablet, and desktop.
- **Seamless Switching:** Users can speak one turn and type the next without losing conversation state or eligibility context.
- **Editable Transcripts:** ASR speech output is displayed in editable text boxes on all devices, allowing quick keyboard or touch corrections.

## 3. Visual Language

- **Primary Vibe:** Modern-friendly — warm, welcoming, and approachable like a helpful companion
- **Secondary Vibe:** Trustworthy — clean structure, consistent layout, reliable feel
- **Tertiary Vibe:** Accessible — large touch targets (48px+), high contrast (WCAG AAA text), multilingual-first typography

## 4. Architecture & File Structure

```
.stitch/
├── SITE.md              # This file — project constitution & responsive strategy
├── DESIGN.md            # Design system tokens, responsive tokens, and visual language
├── metadata.json        # Stitch project tracking
├── designs/             # Generated screen HTML and screenshots
│   ├── 01-home-screen.html
│   ├── 01-home-screen-refined.png
│   ├── 02-language-selection.html
│   ├── 02-language-selection.png
│   ├── 03-onboarding-welcome.html
│   ├── 04-main-conversation.html
│   ├── 05-profile-summary.html
│   ├── 06-eligibility-results.html
│   ├── 07-scheme-detail.html
│   ├── 08-document-checklist.html
│   ├── 09-application-steps.html
│   ├── 10-why-not-eligible.html
│   ├── 11-error-states.html
│   ├── 12-settings.html
│   └── 13-browse-schemes.html
└── next-prompt.md       # Current generation task (for stitch-loop)
```

## 5. Live Sitemap & Status

- [x] `01-home-screen` — Splash / Welcome screen with app branding (Approved & Finalized, Screen ID: `1c801cdbb1e249d0afa60543e762e4cb`)
- [x] `02-language-selection` — Language picker (Hindi, Tamil, Bengali, English) (Generated & Reviewed, Screen ID: `8c6b900906bc4f518a3061b9a4ec300f`)
- [x] `03-onboarding-welcome` — Quick, skippable welcome card with purpose + disclaimer (Generated, Screen ID: `d89e6035267b48cb9b893e7cb579f80d`)
- [x] `04-main-conversation` — Core voice & text chat interface with live attribute strip (Generated, Screen ID: `1d331b0e39e6495383388df93dad9521`)
- [x] `05-profile-confirmation` — Collected attributes with edit capability & status badges (Generated, Screen ID: `8f6ef60bb1834b8d89e2cd6192ae704a`)
- [x] `06-browse-schemes` — Category directory, search, verified indicators (Generated, Screen ID: `e2568c656d674bb09f7fc300e25a6639`)
- [x] `07-eligibility-results` — Deterministic rule engine evaluation summary (Generated, Screen ID: `b5fb7ebf25b74b62adab1b50ecbee7eb`)
- [x] `08-scheme-detail` — PM-KISAN full scheme information card & benefits (Generated, Screen ID: `9f94be5189154c6098bd15c0e3b264fd`)
- [x] `09-document-checklist` — Required documents checklist & numbered application steps (Generated, Screen ID: `53ba94f8ba9347e6881bf9e3da0216a1`)
- [x] `10-why-not-eligible` — Transparent rejection explanation & alternative suggestions (Generated, Screen ID: `e5cf0176ebab49e490aa5f57c2e2d670`)
- [x] `11-my-locker` — Saved schemes, application checklist & offline summary (Generated, Screen ID: `f2f493d53b524e869301a8638686c907`)
- [x] `12-settings-profile` — Language preferences, voice speed, session reset (Generated, Screen ID: `079a8bedc930432789e17c0b0992796a`)
- [x] `13-error-fallback` — Mic blocked fallback, out-of-KB safe refusal, network retry (Generated, Screen ID: `4f86b533e08847148282d10f29ed3723`)

## 6. The Roadmap (Phase 1 UI Backlog)

### Batch A – Onboarding & Conversation (Complete)
- [x] Create Stitch project (`12693025408682747803`)
- [x] Establish design system in Stitch (`assets/17848978814858099422`)
- [x] Generate Home / Welcome screen (Approved & Finalized)
- [x] Generate Language Selection screen (Draft generated)
- [x] Generate Quick Onboarding Welcome card
- [x] Generate Main Conversation interface (Core Screen with voice wave, text input, attribute strip)
- [x] Generate Profile Confirmation screen

### Batch B – Scheme Discovery (Complete)
- [x] Generate Browse Schemes directory & category filters
- [x] Generate Eligibility Results screen (Rule engine evaluation)

### Batch C – Scheme Assistance (Complete)
- [x] Generate Scheme Detail screen (PM-KISAN deep dive)
- [x] Generate Document Checklist & Application Guidance
- [x] Generate "Why not eligible" transparent explanation

### Batch D – User Dashboard & Resilience (Complete)
- [x] Generate My Locker / Saved Schemes screen
- [x] Generate Settings & Profile screen (Voice speed, language preference, data purge)
- [x] Generate Error, Safe Refusal & Voice Fallback states screen

## 7. Creative Freedom & Implementation Guidelines

- **DO:** Design mobile-first, ensuring components scale cleanly to tablet and desktop.
- **DO:** Create distinct desktop multi-column structures for content-dense screens (e.g., Chat + Side Panel for schemes).
- **DO:** Keep voice interaction central and prominent across all screen widths.
- **DO:** Keep text fallback permanently accessible in all viewports.
- **DO:** Use realistic mock data for Indian government schemes (PM-KISAN, Ayushman Bharat, etc.).
- **DO:** Include Hindi/Tamil/Bengali text in examples where appropriate (bilingual mock content).
- **DO:** Show the unofficial disclaimer prominently across all screen sizes.
- **DO:** Use status colors consistently (green=eligible, amber=possibly, red=not eligible).
- **DON'T:** Create a mobile-only silo; ensure React responsive patterns are used throughout.
- **DON'T:** Use government logos or emblems (unofficial assistant).
- **DON'T:** Collect or mock actual Aadhaar numbers or sensitive data.
- **DON'T:** Allow desktop viewports to become giant empty containers or unreadably wide paragraphs.
