# Design System: Yojana Saathi | योजना साथी
**Project ID:** 12693025408682747803

## 1. Visual Theme & Atmosphere

The design language is **modern-friendly and welcoming** — an approachable, warm digital assistant that feels like a knowledgeable friend helping you navigate government schemes, not a cold bureaucratic portal. The atmosphere is **open, bright, and reassuring**, using rounded forms, warm accent colors, and generous whitespace to put users at ease.

The mood balances **trust with warmth** — clean enough to feel reliable, soft enough to feel inviting. Think of the friendliness of Google Pay or PhonePe combined with the clarity of a well-designed government service. The interface avoids both sterile institutional coldness and overly playful casualness.

The design is **mobile-first and responsive** — every screen is designed for small smartphone screens first, then scales gracefully to tablet and desktop viewports. On larger screens, content containers are centered with comfortable max-widths rather than stretching edge-to-edge.

## 2. Color Palette & Roles

### Primary Colors
- **Warm Indigo (#4F46E5)** — Primary brand color. A modern, slightly warm indigo that feels approachable and trustworthy without the coldness of pure government blue. Used for headers, primary buttons, active states, links, and the app identity.

- **Sunrise Orange (#F97316)** — Secondary accent. A warm, energetic orange for the microphone recording state, key call-to-action highlights, and elements that need to draw immediate attention. Culturally resonant with the saffron palette.

- **Teal Fresh (#0D9488)** — Tertiary accent. A lively teal for informational highlights, progress indicators, and interactive elements that complement but don't compete with the primary indigo.

### Status Colors
- **Success Green (#16A34A)** — "ELIGIBLE" status badge, confirmation states, and positive indicators. A clear, vibrant green paired with a soft mint tint background (#DCFCE7).

- **Pending Amber (#D97706)** — "POSSIBLY ELIGIBLE" status, missing information flags, and in-progress states. Paired with a soft cream tint background (#FEF3C7).

- **Alert Red (#DC2626)** — "NOT ELIGIBLE" status, error messages, and critical alerts. Paired with a soft rose tint background (#FEE2E2).

### Neutral Colors
- **Canvas Warm (#F8FAFC)** — Page background. A subtly cool-warm white that is easy on the eyes across varied screen brightness levels.

- **Surface White (#FFFFFF)** — Card backgrounds, input fields, and elevated containers. Creates gentle layering against the canvas.

- **Deep Ink (#0F172A)** — Primary text. A very deep blue-black that is softer than pure #000000 while maintaining excellent contrast ratios (WCAG AAA compliant on white).

- **Slate Calm (#64748B)** — Secondary text for metadata, timestamps, disclaimers, helper text, and supporting information.

- **Border Mist (#E2E8F0)** — Borders, dividers, and container outlines. Subtle enough to define structure without visual noise.

- **Indigo Tint (#EEF2FF)** — Light indigo wash for assistant chat bubbles, selected states, hover backgrounds, and subtle emphasis areas.

## 3. Typography Rules

**Font Family:** Noto Sans — selected for comprehensive glyph coverage across Devanagari (Hindi), Tamil (தமிழ்), and Bengali (বাংলা) scripts. This ensures consistent, readable typography across all supported languages without font-switching artifacts.

**Heading Treatment:**
- H1: Semi-bold (600), 22px mobile / 28px desktop, Deep Ink. Used for screen titles.
- H2: Semi-bold (600), 18px mobile / 22px desktop, Deep Ink. Used for section headings within cards.
- H3: Medium (500), 16px mobile / 18px desktop, Deep Ink. Used for card titles and subsections.

**Body Text:** Regular (400), 16px minimum across all breakpoints. Line height 1.6 for comfortable reading of Indic scripts with their taller ascenders/descenders. Deep Ink color.

**Labels & Metadata:** Medium (500), 13-14px, Slate Calm color. For scheme ministry names, dates, status labels, and input field labels.

**Button Text:** Semi-bold (600), 15-16px. Mixed case only — uppercase is avoided because it reduces readability in Hindi, Tamil, and Bengali.

**Accessibility note:** All text combinations maintain WCAG AA contrast ratios at minimum. Primary text on both Canvas and Surface backgrounds exceeds WCAG AAA (>7:1).

## 4. Component Stylings

### Buttons
- **Primary:** Warm Indigo background, white text, rounded corners (10px), full-width on mobile. Soft shadow (0 1px 3px rgba(0,0,0,0.12)). Hover: slightly darker (#4338CA). Active: pressed shadow effect.
- **Secondary:** White background, Warm Indigo border and text, same rounded shape. Hover: Indigo Tint background.
- **Text/Link:** No background or border, Warm Indigo text, underline on hover.
- **Minimum height:** 48px for all buttons (accessibility requirement).

### Microphone Button
- **Resting:** 68px circular button, Warm Indigo background with white microphone icon. Soft elevation shadow. Clear "Tap to speak" label below.
- **Recording:** Sunrise Orange background with animated pulsing ring. White waveform visualization. "Listening..." label.
- **Processing:** Returns to Indigo with a spinning indicator. "Understanding..." label.

### Chat Interface
- **User Bubbles:** Right-aligned, Warm Indigo background, white text. Rounded (14px) with bottom-right corner at 4px for tail effect.
- **Assistant Bubbles:** Left-aligned, Indigo Tint (#EEF2FF) background, Deep Ink text. Rounded (14px) with bottom-left corner at 4px. Small assistant avatar icon beside the bubble.
- **Transcript Display:** Within assistant bubble, a dashed-border inset shows the recognized speech text with a small "Edit" link in Warm Indigo for corrections.

### Cards & Containers
- **Standard Card:** Surface White background, Border Mist (1px) border, rounded (12px), soft shadow (0 1px 3px rgba(0,0,0,0.08)). 16px internal padding.
- **Scheme Result Card:** Standard card with a colored left border (4px) matching the eligibility status color. Status pill badge in top-right.
- **Expandable sections:** Chevron icon, tap to reveal details. Smooth expand animation.

### Status Badges
- **Shape:** Pill-shaped (full radius), compact (24px height).
- **ELIGIBLE:** Success Green text on mint tint background, small checkmark icon.
- **POSSIBLY ELIGIBLE:** Pending Amber text on cream tint background, small clock/question icon.
- **NOT ELIGIBLE:** Alert Red text on rose tint background, small cross icon.
- **Always paired with text — never color alone** for accessibility.

### Profile Attribute Chips
- Pill-shaped tags showing collected user info (e.g., "Age: 52", "State: UP").
- Indigo Tint background, Deep Ink text, small pencil/edit icon on tap.
- Displayed in a horizontal scrollable row in the "What I understood" strip.

### Input Fields
- Rounded (10px), white background, Border Mist border (1.5px).
- Focus: Warm Indigo border with soft indigo shadow glow.
- Label above field (not placeholder-only) for accessibility.
- Minimum height 48px, generous padding (14px).

### Language Selector
- **Onboarding:** Large, full-width buttons per language with the language name in its native script (हिन्दी, தமிழ், বাংলা, English). Each button 56px tall minimum.
- **In-header:** Compact dropdown showing current language flag/icon + abbreviated name.

## 5. Layout & Responsive Web Principles

**Mobile-First Responsive Architecture (React Web):** The application is built as a single responsive React web app serving mobile, tablet, and desktop viewports. Components are designed mobile-first and expand adaptively.

**Responsive Breakpoints & Structural Adaptation:**
- **Mobile (< 640px):** Single-column stacked layout, full-width touch cards, sticky top navigation header, sticky bottom voice action bar with integrated text input.
- **Tablet (640px - 1023px):** Centered content column (max-width 640px - 768px), 2-column discovery card grids, increased breathing room.
- **Desktop (≥ 1024px):** Purpose-built wide-screen layouts rather than stretched mobile views:
  * **Conversation Screen:** Split-pane interface (Left 60%: voice & text dialogue flow; Right 40%: live profile attribute chips, real-time matching schemes preview, and quick document summary).
  * **Browse Schemes Screen:** 3-column responsive card grid with left sidebar filter controls.
  * **Text Width Constraint:** Reading prose constrained to max-width 720px for optimal line lengths.

**Voice Interaction Parity across Devices:**
- **Mobile:** Large bottom thumb-accessible microphone button (68px).
- **Desktop:** Prominent voice action bar with microphone trigger, audio wave visualization, and optional push-to-talk hotkey indicator (e.g. `Hold Spacebar to speak`).
- **All Devices:** Audio replay buttons for assistant spoken responses with visible playback duration.

**Text Fallback & Transcript Parity:**
- Text input box is always visible and functional alongside voice on mobile, tablet, and desktop.
- Transcripts appear in editable text boxes on all form factors so users can correct ASR misunderstandings via touch or keyboard before evaluation.

**Generous touch and click targets:** All interactive elements minimum 48×48px tap/click area.

**Consistent spacing scale:**
- 4px — tight internal padding (within badges, chips)
- 8px — related item spacing (between chips, within button groups)
- 16px — horizontal page padding; spacing between card content elements
- 24px — spacing between distinct content sections
- 32px — spacing between major page regions

**Sticky regions:**
- **Top:** Responsive header with app name "Yojana Saathi | योजना साथी", language selector pill, settings gear. Slim disclaimer bar below: "Unofficial helper — verify on official portal"
- **Bottom (Mobile/Tablet) / Fixed Bar (Desktop):** Input area with centered mic button, text input field, and send button.

**Progressive disclosure:** Detailed information (full eligibility reasons, all application steps, complete document lists) starts collapsed with a clear "View details" / "Show more" affordance. Prevents overwhelming users with dense text.

**Onboarding:** Quick and skippable — a single welcome card explaining the app's purpose + a prominent "Skip" link. Disclaimer is integrated into the welcome, not a separate mandatory screen.
