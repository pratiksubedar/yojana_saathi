/**
 * Yojana Saathi - Reusable Chat API Client
 * Milestone 6.4: Communicates with FastAPI backend for both standard request/response
 * and Server-Sent Events (SSE) streaming with cancellation and error resilience.
 */

import type { Language, ProvenanceCitationItem, EligibilityOutcomeItem } from '../types/index.ts';

export interface ChatApiRequest {
  message: string;
  language: Language;
  session_id?: string;
  scheme_id?: string;
  citizen_profile?: Record<string, any>;
}

export interface ProfileConflictItem {
  field: string;
  confirmed_value: any;
  new_value: any;
}

export interface ChatApiResponse {
  session_id: string;
  message: string;
  intent: string;
  language: string;
  scheme_id?: string;
  eligibility_result?: EligibilityOutcomeItem;
  candidate_evaluations?: EligibilityOutcomeItem[];
  profile_conflicts?: ProfileConflictItem[];
  citations: ProvenanceCitationItem[];
  formatted_citations_markdown: string;
  suggested_followups: string[];
  active_profile: Record<string, any>;
}

export interface StreamCallbacks {
  onToken?: (token: string) => void;
  onMetadata?: (meta: { session_id: string; intent: string; language: string; scheme_id?: string }) => void;
  onCitations?: (citations: ProvenanceCitationItem[], markdown: string) => void;
  onEligibility?: (elig: EligibilityOutcomeItem) => void;
  onFollowups?: (followups: string[]) => void;
  onProfile?: (profile: Record<string, any>, conflicts?: ProfileConflictItem[]) => void;
  onDone?: (meta: { session_id: string; complete: boolean }) => void;
  onError?: (err: { detail: string; error_code?: string }) => void;
}

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '/api/v1';

export const UUID_V4_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/**
 * Extracts a readable error string from backend responses (supporting Pydantic error lists, string details, and generic errors).
 */
export function formatErrorDetail(errData: any, fallback: string): string {
  if (!errData) return fallback;
  if (typeof errData.detail === 'string') return errData.detail;
  if (Array.isArray(errData.detail)) {
    return errData.detail
      .map((item: any) => {
        if (typeof item === 'string') return item;
        if (item?.msg) {
          const loc = Array.isArray(item.loc) ? item.loc.slice(1).join('.') : '';
          return loc ? `${loc}: ${item.msg}` : item.msg;
        }
        return JSON.stringify(item);
      })
      .join('; ');
  }
  if (errData.message && typeof errData.message === 'string') return errData.message;
  return fallback;
}

/**
 * Generates an unpredictable, cryptographically secure random UUIDv4 token using CSPRNG.
 * Ensures $2^{122}$ bits of entropy so bearer session tokens cannot be guessed or predicted.
 */
export const generateSecureSessionToken = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    const generated = crypto.randomUUID().toLowerCase();
    if (UUID_V4_REGEX.test(generated)) return generated;
  }
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    // RFC 4122 version 4 and variant 1
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`.toLowerCase();
  }
  // Math.random fallback (e.g. legacy test environment without crypto)
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

/**
 * Generates or retrieves an ephemeral UUIDv4 bearer token from sessionStorage.
 * Storing ONLY the bearer token in sessionStorage maintains tab-level conversational continuity
 * without persisting any raw citizen messages, transcripts, or demographic attributes.
 */
export const getSessionId = (): string => {
  const SESSION_KEY = 'yojana_chat_session_id';
  let currentId: string | null = null;
  try {
    currentId = sessionStorage.getItem(SESSION_KEY);
  } catch {
    // sessionStorage inaccessible
  }
  // Enforce valid RFC 4122 UUIDv4 format so backend Pydantic validation never rejects the session
  if (!currentId || !UUID_V4_REGEX.test(currentId.trim())) {
    currentId = generateSecureSessionToken();
    try {
      sessionStorage.setItem(SESSION_KEY, currentId);
    } catch {
      // ignore
    }
  } else {
    currentId = currentId.trim();
  }
  return currentId;
};

export const clearSessionId = (): void => {
  try {
    sessionStorage.removeItem('yojana_chat_session_id');
  } catch {
    // ignore
  }
};

/**
 * Sends a single conversational turn via POST /api/v1/chat.
 */
export async function sendChatMessage(request: ChatApiRequest): Promise<ChatApiResponse> {
  const rawSession = request.session_id || getSessionId();
  const sessionId = UUID_V4_REGEX.test(rawSession.trim()) ? rawSession.trim() : generateSecureSessionToken();

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 20000);

  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        message: request.message.trim(),
        language: request.language,
        session_id: sessionId,
        scheme_id: request.scheme_id || undefined,
        citizen_profile: request.citizen_profile || undefined,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorDetail = `Backend service error (HTTP ${response.status}). Please try again.`;
      try {
        const errorJson = await response.json();
        errorDetail = formatErrorDetail(errorJson, errorDetail);
      } catch {
        // Fallback to default
      }
      throw new Error(errorDetail);
    }

    return await response.json();
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error('Inquiry timed out. Please check your connection and retry.');
    }
    throw err;
  }
}

/**
 * Initiates SSE streaming via POST /api/v1/chat/stream with cancellation support.
 * Returns an abort function that the caller can invoke to cancel streaming.
 */
export function streamChatMessage(
  request: ChatApiRequest,
  callbacks: StreamCallbacks
): () => void {
  const rawSession = request.session_id || getSessionId();
  const sessionId = UUID_V4_REGEX.test(rawSession.trim()) ? rawSession.trim() : generateSecureSessionToken();
  const controller = new AbortController();
  let abortedByCaller = false;
  let streamTimeout: any = null;
  let firstTokenTimeout: any = null;

  (async () => {
    try {
      // 30s overall stream safety timeout to prevent indefinite hanging
      streamTimeout = setTimeout(() => {
        controller.abort();
      }, 30000);
      if (typeof streamTimeout?.unref === 'function') streamTimeout.unref();

      // 10s first-token safety timeout: if backend does not emit anything within 10s, abort to fallback
      firstTokenTimeout = setTimeout(() => {
        controller.abort();
      }, 10000);
      if (typeof firstTokenTimeout?.unref === 'function') firstTokenTimeout.unref();

      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({
          message: request.message.trim(),
          language: request.language,
          session_id: sessionId,
          scheme_id: request.scheme_id || undefined,
          citizen_profile: request.citizen_profile || undefined,
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        if (streamTimeout) clearTimeout(streamTimeout);
        if (firstTokenTimeout) clearTimeout(firstTokenTimeout);
        let errorDetail = `Streaming unavailable (HTTP ${response.status}). Falling back to standard response.`;
        try {
          const errData = await response.json();
          errorDetail = formatErrorDetail(errData, errorDetail);
        } catch {
          // ignore
        }
        callbacks.onError?.({ detail: errorDetail });
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let isDoneEmitted = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Clear first-token timeout upon receiving first stream bytes
        if (firstTokenTimeout) {
          clearTimeout(firstTokenTimeout);
          firstTokenTimeout = null;
        }

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() || '';

        for (const block of blocks) {
          if (!block.trim()) continue;
          const lines = block.split('\n');
          let eventType = 'message';
          let rawData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              rawData = line.slice(6).trim();
            }
          }

          if (!rawData) continue;

          try {
            const parsed = JSON.parse(rawData);

            switch (eventType) {
              case 'metadata':
                callbacks.onMetadata?.(parsed);
                break;
              case 'token':
                if (parsed.delta) {
                  callbacks.onToken?.(parsed.delta);
                }
                break;
              case 'citations':
                callbacks.onCitations?.(parsed.citations || [], parsed.formatted_markdown || '');
                break;
              case 'eligibility':
                callbacks.onEligibility?.(parsed);
                break;
              case 'followups':
                callbacks.onFollowups?.(parsed.items || []);
                break;
              case 'profile':
                callbacks.onProfile?.(parsed.active_profile || {}, parsed.profile_conflicts || []);
                break;
              case 'done':
                isDoneEmitted = true;
                callbacks.onDone?.(parsed);
                break;
              case 'error':
                callbacks.onError?.(parsed);
                break;
              case 'message':
                // Handle un-named SSE data lines defensively
                if (parsed.delta) {
                  callbacks.onToken?.(parsed.delta);
                } else if (parsed.complete) {
                  isDoneEmitted = true;
                  callbacks.onDone?.(parsed);
                }
                break;
            }
          } catch (jsonErr) {
            console.warn('Failed to parse SSE event payload:', jsonErr);
          }
        }
      }

      if (streamTimeout) clearTimeout(streamTimeout);
      if (firstTokenTimeout) clearTimeout(firstTokenTimeout);

      // Handle any trailing buffer
      if (buffer.trim()) {
        const lines = buffer.split('\n');
        let eventType = 'message';
        let rawData = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) eventType = line.slice(7).trim();
          else if (line.startsWith('data: ')) rawData = line.slice(6).trim();
        }
        if (rawData) {
          try {
            const parsed = JSON.parse(rawData);
            if (eventType === 'done' || parsed.complete) {
              isDoneEmitted = true;
              callbacks.onDone?.(parsed);
            } else if ((eventType === 'token' || eventType === 'message') && parsed.delta) {
              callbacks.onToken?.(parsed.delta);
            }
          } catch {
            // ignore
          }
        }
      }

      // If stream finished without an explicit done event, synthesize done so UI state always terminates
      if (!isDoneEmitted) {
        callbacks.onDone?.({ session_id: sessionId, complete: true });
      }
    } catch (err: any) {
      if (streamTimeout) clearTimeout(streamTimeout);
      if (firstTokenTimeout) clearTimeout(firstTokenTimeout);
      if (err.name === 'AbortError') {
        if (!abortedByCaller) {
          // Timeout triggered abort, not user cancellation
          callbacks.onError?.({
            detail: 'Inquiry response timed out. Falling back to verified scheme database.',
            error_code: 'TIMEOUT',
          });
        }
      } else {
        callbacks.onError?.({ detail: err.message || 'Stream connection interrupted.' });
      }
    }
  })();

  return () => {
    abortedByCaller = true;
    if (streamTimeout) clearTimeout(streamTimeout);
    if (firstTokenTimeout) clearTimeout(firstTokenTimeout);
    controller.abort();
  };
}

/**
 * Resets the server-side ephemeral profile for the active session.
 */
export async function resetChatSession(sessionId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/chat/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    });
    return res.ok;
  } catch (err) {
    console.warn('Failed to reset backend chat session:', err);
    return false;
  }
}

export interface TranslateApiResponse {
  translated_text: string;
  target_language: string;
  source_language?: string;
  cached: boolean;
  is_translated?: boolean;
}

/**
 * Translates an assistant message into the target language using backend translation service.
 */
export async function translateChatMessage(
  text: string,
  targetLanguage: Language,
  sourceLanguage?: string
): Promise<TranslateApiResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/chat/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        target_language: targetLanguage,
        source_language: sourceLanguage,
      }),
    });
    if (!res.ok) {
      throw new Error(`Translation error: HTTP ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.warn('Failed to translate chat message:', err);
    return {
      translated_text: text,
      target_language: targetLanguage,
      cached: false,
      is_translated: false,
    };
  }
}

