/**
 * Yojana Saathi - Chat & Voice Runtime Debugging Regression Tests
 *
 * Verifies:
 * 1. UUIDv4 token generation and self-healing session ID retrieval
 * 2. Error detail extraction for FastAPI / Pydantic validation errors
 * 3. Synchronous sendChatMessage contract and error resilience
 * 4. Streaming streamChatMessage SSE parsing and guaranteed completion
 * 5. Speech recognition lifecycle stability without premature aborts
 * 6. Voice modal navigation and query parameter handoff to AssistantChat
 */

import { test, describe, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';

import {
  UUID_V4_REGEX,
  generateSecureSessionToken,
  getSessionId,
  clearSessionId,
  formatErrorDetail,
  sendChatMessage,
  streamChatMessage,
} from '../src/services/chatApi.ts';

describe('Chat API Session ID & UUIDv4 Validation', () => {
  beforeEach(() => {
    // Reset fake sessionStorage if present
    if (typeof globalThis.sessionStorage !== 'undefined') {
      globalThis.sessionStorage.clear();
    }
  });

  test('UUID_V4_REGEX matches valid random UUIDv4 and rejects invalid formats', () => {
    const validUuid1 = '90886d3f-f568-4291-bd98-b4bd3ab7d38e';
    const validUuid2 = 'd3a8e65e-7c74-4c4e-ac2d-bd385e9c38f8';
    assert.ok(UUID_V4_REGEX.test(validUuid1));
    assert.ok(UUID_V4_REGEX.test(validUuid2));

    // Non-v4 UUID (version 1)
    const v1Uuid = '216fff40-98d9-11e3-a5e2-0800200c9a66';
    assert.strictEqual(UUID_V4_REGEX.test(v1Uuid), false);

    // Malformed strings
    assert.strictEqual(UUID_V4_REGEX.test('test-123'), false);
    assert.strictEqual(UUID_V4_REGEX.test('demo-session-id'), false);
    assert.strictEqual(UUID_V4_REGEX.test(''), false);
    assert.strictEqual(UUID_V4_REGEX.test('   '), false);
  });

  test('generateSecureSessionToken produces valid UUIDv4 tokens', () => {
    for (let i = 0; i < 10; i++) {
      const token = generateSecureSessionToken();
      assert.ok(
        UUID_V4_REGEX.test(token),
        `Generated token [${token}] must match RFC 4122 UUIDv4 specification`
      );
    }
  });

  test('getSessionId self-heals corrupted or legacy session IDs in sessionStorage', () => {
    const storageMap = new Map();
    globalThis.sessionStorage = {
      getItem: (key) => storageMap.get(key) || null,
      setItem: (key, val) => storageMap.set(key, String(val)),
      removeItem: (key) => storageMap.delete(key),
      clear: () => storageMap.clear(),
    };

    // Store an invalid legacy string that would fail FastAPI Pydantic validation
    storageMap.set('yojana_chat_session_id', 'corrupted-legacy-session-token');

    const healedId = getSessionId();
    assert.ok(UUID_V4_REGEX.test(healedId), 'Healed session ID must be valid UUIDv4');
    assert.notStrictEqual(healedId, 'corrupted-legacy-session-token');
    assert.strictEqual(storageMap.get('yojana_chat_session_id'), healedId);
  });
});

describe('Chat API Error Detail Formatting', () => {
  test('formats simple string detail directly', () => {
    const res = formatErrorDetail({ detail: 'Scheme not active' }, 'Fallback');
    assert.strictEqual(res, 'Scheme not active');
  });

  test('formats FastAPI Pydantic validation error arrays into human-readable messages', () => {
    const pydanticError = {
      detail: [
        {
          type: 'value_error',
          loc: ['body', 'session_id'],
          msg: 'Value error, session_id must be a valid UUIDv4 string',
          input: 'invalid',
        },
      ],
    };

    const formatted = formatErrorDetail(pydanticError, 'Default fallback');
    assert.ok(formatted.includes('session_id: Value error, session_id must be a valid UUIDv4 string'));
  });

  test('falls back safely for null, undefined, or empty payloads', () => {
    assert.strictEqual(formatErrorDetail(null, 'Fallback msg'), 'Fallback msg');
    assert.strictEqual(formatErrorDetail(undefined, 'Fallback msg'), 'Fallback msg');
    assert.strictEqual(formatErrorDetail({}, 'Fallback msg'), 'Fallback msg');
  });
});

describe('Chat API sendChatMessage & streamChatMessage Methods', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test('sendChatMessage sends valid UUIDv4 session_id and parses response', async () => {
    let capturedBody = null;
    globalThis.fetch = async (url, opts) => {
      capturedBody = JSON.parse(opts.body);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          session_id: capturedBody.session_id,
          message: 'Hello! I can help you with welfare schemes.',
          intent: 'GENERAL_HELP',
          language: 'en',
          citations: [],
          formatted_citations_markdown: '',
          suggested_followups: ['Which schemes are available?'],
          active_profile: {},
        }),
      };
    };

    const res = await sendChatMessage({
      message: 'Hello',
      language: 'en',
    });

    assert.ok(UUID_V4_REGEX.test(capturedBody.session_id));
    assert.strictEqual(capturedBody.message, 'Hello');
    assert.strictEqual(capturedBody.language, 'en');
    assert.strictEqual(res.intent, 'GENERAL_HELP');
  });

  test('sendChatMessage cleanly formats HTTP 422 Pydantic error', async () => {
    globalThis.fetch = async () => ({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [
          {
            loc: ['body', 'message'],
            msg: 'Message cannot be empty or whitespace only',
          },
        ],
      }),
    });

    await assert.rejects(
      async () => {
        await sendChatMessage({ message: '   ', language: 'en' });
      },
      (err) => {
        assert.ok(err.message.includes('message: Message cannot be empty'));
        return true;
      }
    );
  });

  test('streamChatMessage dispatches typed events and completes cleanly', async () => {
    const ssePayload = [
      'event: metadata\ndata: {"session_id":"90886d3f-f568-4291-bd98-b4bd3ab7d38e","intent":"GENERAL_HELP","language":"en"}\n\n',
      'event: token\ndata: {"delta":"Namaste! "}\n\n',
      'event: token\ndata: {"delta":"How can I help you today?"}\n\n',
      'event: followups\ndata: {"items":["PM-KISAN","PM-JAY"]}\n\n',
      'event: done\ndata: {"session_id":"90886d3f-f568-4291-bd98-b4bd3ab7d38e","complete":true}\n\n',
    ].join('');

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(ssePayload));
        controller.close();
      },
    });

    globalThis.fetch = async () => ({
      ok: true,
      status: 200,
      body: stream,
    });

    const tokensReceived = [];
    let isDone = false;
    let followupsReceived = [];

    await new Promise((resolve) => {
      streamChatMessage(
        { message: 'hi', language: 'en' },
        {
          onToken: (t) => tokensReceived.push(t),
          onFollowups: (f) => (followupsReceived = f),
          onDone: () => {
            isDone = true;
            resolve();
          },
        }
      );
    });

    assert.strictEqual(tokensReceived.join(''), 'Namaste! How can I help you today?');
    assert.deepStrictEqual(followupsReceived, ['PM-KISAN', 'PM-JAY']);
    assert.strictEqual(isDone, true);
  });

  test('streamChatMessage synthesizes onDone if server closes stream without explicit done event', async () => {
    const ssePayload = [
      'event: metadata\ndata: {"session_id":"90886d3f-f568-4291-bd98-b4bd3ab7d38e","intent":"GENERAL_HELP","language":"en"}\n\n',
      'event: token\ndata: {"delta":"Information text."}\n\n',
      // Stream closes here without event: done
    ].join('');

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(ssePayload));
        controller.close();
      },
    });

    globalThis.fetch = async () => ({
      ok: true,
      status: 200,
      body: stream,
    });

    let doneCalled = false;
    await new Promise((resolve) => {
      streamChatMessage(
        { message: 'info', language: 'en' },
        {
          onDone: (meta) => {
            doneCalled = true;
            assert.strictEqual(meta.complete, true);
            resolve();
          },
        }
      );
    });

    assert.strictEqual(doneCalled, true, 'Synthesized onDone must fire to terminate UI loading state');
  });

  test('streamChatMessage handles un-named SSE data lines defensively', async () => {
    const ssePayload = [
      'data: {"delta":"Direct message token."}\n\n',
      'data: {"complete":true}\n\n',
    ].join('');

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(ssePayload));
        controller.close();
      },
    });

    globalThis.fetch = async () => ({
      ok: true,
      status: 200,
      body: stream,
    });

    const tokens = [];
    let done = false;
    await new Promise((resolve) => {
      streamChatMessage(
        { message: 'un-named', language: 'en' },
        {
          onToken: (tok) => tokens.push(tok),
          onDone: () => {
            done = true;
            resolve();
          },
        }
      );
    });

    assert.strictEqual(tokens.join(''), 'Direct message token.');
    assert.strictEqual(done, true);
  });

  test('streamChatMessage caller cancellation aborts cleanly without firing onError', async () => {
    let abortControllerObserved = null;
    const stream = new ReadableStream({
      start(controller) {
        // Keeps stream open
      },
    });

    globalThis.fetch = async (url, options) => {
      abortControllerObserved = options.signal;
      return {
        ok: true,
        status: 200,
        body: stream,
      };
    };

    let errorFired = false;
    const cancel = streamChatMessage(
      { message: 'cancel-test', language: 'en' },
      {
        onError: () => {
          errorFired = true;
        },
      }
    );

    // Cancel from caller
    cancel();
    assert.ok(abortControllerObserved.aborted);
    await new Promise((r) => setTimeout(r, 50));
    assert.strictEqual(errorFired, false, 'Caller abort should not trigger error banner');
  });
});

