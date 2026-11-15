# Yojana Saathi — Chat & Voice Runtime Fix Report
**Milestone:** Phase 7 & 8 / Conversational Assistant Runtime Stabilization  
**Date:** November 11, 2026  
**Status:** Resolved & Verified  

---

## 1. Executive Summary

Citizens attempting to query government welfare schemes via text or voice input experienced an indefinite loading state in the Assistant Chat view:
```
"Analyzing verified scheme rules..."
```
While voice capture successfully populated transcripts and backend endpoints returned HTTP 200 via the Vite reverse proxy, the assistant response bubble was never presented in the UI.

A systematic investigation covering network traffic, browser console logs, backend streaming telemetry, SSE parser behavior, and React state lifecycles isolated three interconnected root causes:
1. **Silent Timeout Abort Suppression:** `streamChatMessage` suppressed errors when `err.name === 'AbortError'`. When safety timeouts fired, `callbacks.onError` was bypassed, leaving `isSubmitting === true` permanently.
2. **Missing Guaranteed State Reset on Failure / Exceptions:** State updates in `onDone` and `onError` lacked enclosing `try / finally` guarantees. If an exception occurred during profile attribute formatting or fallback REST execution, `setIsSubmitting(false)` and `setStreamingText('')` were not executed.
3. **Unstable Dependency Closures & Duplicate Submissions:** `handleSendMessage` depended directly on `isSubmitting` and was used across reactive hooks without a synchronized ref guard (`isSubmittingRef`), allowing concurrent re-entry and stale state traps.

All issues have been resolved without altering backend eligibility logic, RAG retrieval schemas, or design system tokens. Full verification via headless Chrome DevTools Protocol (CDP), 88 frontend unit tests, 194 backend pytest cases, and production build succeeded.

---

## 2. Investigation Protocol & Findings (Steps 1–9)

### Step 1: Browser Network Requests
- **Target Endpoint:** Frontend called `POST /api/v1/chat/stream` through the Vite reverse proxy.
- **HTTP Status:** `200 OK`.
- **Response Headers:**
  - `Content-Type: text/event-stream; charset=utf-8`
  - `Transfer-Encoding: chunked`
  - `Cache-Control: no-cache`
  - `X-Accel-Buffering: no`
  - `Server: uvicorn`
- **Data Delivery:** Real-time chunks arrived incrementally via chunked transfer encoding containing valid SSE data.

### Step 2: Browser Console & Runtime Errors
- No unhandled promise rejections or fatal React rendering crashes.
- Web Speech API gracefully fell back to interactive sample queries in headless test environments (`SpeechRecognitionErrorEvent: not-allowed` handled cleanly).
- SpeechSynthesis chunk playback warning in headless audio environments did not block chat message delivery.

### Step 3: FastAPI Backend Logs & SSE Stream Execution
- Backend log trace:
  ```
  INFO: 127.0.0.1:64006 - "POST /api/v1/chat/stream HTTP/1.1" 200 OK
  ```
- Conversational orchestrator completed RAG retrieval and statutory rule evaluation in ~200ms.
- Full sequence of SSE events emitted:
  1. `event: metadata` (session ID, intent, scheme ID)
  2. `event: citations` (grounded statutory citations)
  3. `event: eligibility` (evaluated statutory conditions)
  4. `event: token` (streamed in 3-word chunks with natural pacing)
  5. `event: followups` (suggested next inquiries)
  6. `event: profile` (accumulated demographic attributes)
  7. `event: done` (`complete: true`)

### Step 4 & 5: Backend SSE Formatting vs. Frontend Parser
- Verified exact event naming parity:
  - Backend `backend/app/api/v1/chat.py` generates `event: <name>\ndata: <json>\n\n`.
  - Frontend `src/services/chatApi.ts` parser splits on `\n\n` boundaries, parses `event: ` and `data: ` headers, and dispatches to registered callbacks.

### Step 6: Mismatched Events & Un-named Payloads
- Backend always prefixes event names. However, to guard against intermediate proxies stripping `event:` lines, `chatApi.ts` was enhanced with defensive handling for standard un-named `message` events containing `delta` or `complete`.

### Step 7: Stream Parsing & State Update Exceptions
- If an exception occurred inside `onDone` (e.g. during message formatting) or inside `onError` (e.g. when REST fallback failed), execution halted before `setIsSubmitting(false)` was invoked.
- Fix: Enclosed message building and fallback execution in `try / catch / finally` blocks with unconditional state clearing.

### Step 8: Guaranteed State Reset Across All Branches
Verified that `isSubmitting` and `streamingText` reset across all five operational branches:
1. **Normal Completion:** `event: done` or stream EOF triggers `onDone` -> resets state.
2. **Partial Streaming Error:** Abort after tokens -> flushes accumulated text to chat, displays banner, resets state.
3. **Early Backend Failure:** 4xx/5xx before tokens -> falls back to REST `sendChatMessage`; resets state in `finally`.
4. **Network Drop / Offline:** `isOnline === false` blocks immediately with localized alert; fetch failure caught and resets state.
5. **Stream Timeout:** 10s first-token safety timer and 30s overall timer abort stalled streams and invoke `onError`, resetting state.

### Step 9: Real Browser UI Testing
Verified both typed chat input and voice modal sample queries in real Chrome browser instances via Chrome DevTools Protocol (CDP).

---

## 3. Root Causes & Code Modifications

### 1. `src/services/chatApi.ts`
- **Distinguish User Cancellation from Timeout Aborts:**
  Introduced `abortedByCaller` flag in `streamChatMessage`. When `controller.abort()` is triggered by timeout rather than the caller, `callbacks.onError` is called with a descriptive timeout message instead of silently swallowed.
- **Fast First-Token Timeout (10s):**
  Added a 10s timer for initial stream chunks alongside the 30s total stream timeout. Cleared immediately upon receiving the first byte. Timers use `.unref()` to avoid holding the Node.js test process open.
- **Defensive Un-named SSE Parsing:**
  Added fallback handling for `eventType === 'message'` containing `delta` or `complete` payloads.

### 2. `src/pages/AssistantChat.tsx`
- **Synchronized Submission Guard (`isSubmittingRef`):**
  Added `isSubmittingRef = useRef<boolean>(false)` to prevent race conditions and duplicate submissions.
- **Stable Callback Dependencies:**
  Removed `isSubmitting` from `handleSendMessage`'s dependency array, preventing callback invalidation on every state change.
- **Guaranteed Cleanup in `finally` and Unmount:**
  Enclosed fallback execution in `try ... finally` ensuring `isSubmittingRef.current = false`, `setIsSubmitting(false)`, and `setStreamingText('')` execute under all conditions.
  Added state reset to the unmount cleanup effect.
- **Initial Query Handled Reset on New Session:**
  Reset `initialQueryHandledRef.current = false` inside `handleResetChat()` so subsequent conversations can accept incoming navigation queries.

---

## 4. Verification Evidence

### A. Frontend Unit & Regression Tests
```
> node --test scripts/test_speech.mjs scripts/test_pwa_offline.mjs scripts/test_scheme_api.mjs scripts/test_batch1_screens.mjs scripts/test_batch2_screens.mjs scripts/test_chat_voice_debugging.mjs

ℹ tests 88
ℹ suites 26
ℹ pass 88
ℹ fail 0
ℹ duration_ms 534ms
```

### B. Production Frontend Build
```
> tsc && vite build
vite v6.4.6 building for production...
✓ 2103 modules transformed.
dist/index.html                   1.56 kB │ gzip:   0.77 kB
dist/assets/index-DGlSDSWd.css   39.91 kB │ gzip:   7.17 kB
dist/assets/index-CZBo93jN.js   471.04 kB │ gzip: 126.67 kB
✓ built in 1.23s
```

### C. Backend Test Suite
```
backend/.venv/bin/pytest
======================= 194 passed, 2 warnings in 4.26s ========================
```

### D. End-to-End Browser Automation via Chrome CDP
```
--- VERIFICATION 1: Typed Text Input ---
[NETWORK REQUEST] POST http://localhost:5173/api/v1/chat/stream
[NETWORK RESPONSE] 200 http://localhost:5173/api/v1/chat/stream
Result 1 (Typed): {
  messageCount: 6,
  lastMessage: 'Ministry of Petroleum and Natural Gas, Government of India • Section 1 (Eligible',
  thinking: false
}

--- VERIFICATION 2: Voice Modal Query ---
[NETWORK REQUEST] POST http://localhost:5173/api/v1/chat/stream
[NETWORK RESPONSE] 200 http://localhost:5173/api/v1/chat/stream
Result 2 (Voice): {
  messageCount: 8,
  lastMessage: 'Which scheme would you like to check eligibility for? (e.g., PM-KISAN, PM-JAY, P',
  thinking: false
}
```

---

## 5. Manual Verification Instructions

1. Ensure the backend and frontend servers are running:
   - Backend: `http://127.0.0.1:8000` (FastAPI)
   - Frontend: `http://localhost:5173` (Vite)
2. Open `http://localhost:5173/assistant` in Chrome.
3. **Verify Typed Chat:**
   - Type `"What is PM Surya Ghar?"` into the text box and press Enter or click the Send button.
   - Observe the brief indicator `"Analyzing verified scheme rules..."` transition immediately into streaming text.
   - Verify the assistant's message appears with statutory citations and suggested follow-up questions.
4. **Verify Voice Chat:**
   - Click the orange microphone button at the bottom left to open the Voice Assistant Modal.
   - Select the sample farmer query: *"I am a 38-year-old farmer with 1.2 hectares land. Which welfare schemes can I get?"*.
   - Click **"Submit Question"**.
   - Verify the modal closes, the user question appears, the stream delivers the response, and `"thinking"` resets cleanly to `false`.
5. **Verify New Conversation Reset:**
   - Click **"New Conversation"** in the top bar.
   - Verify previous messages are cleared and the initial welcome prompt is restored.

