import { spawn } from 'node:child_process';

async function waitPort(port, maxTries = 30) {
  for (let i = 0; i < maxTries; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (res.ok) return await res.json();
    } catch {}
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`Port ${port} did not respond`);
}

async function main() {
  const chromeProc = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [
    '--headless=new',
    '--remote-debugging-port=9222',
    '--user-data-dir=/tmp/chrome-profile-' + Date.now(),
    '--no-first-run',
    '--no-default-browser-check',
  ]);

  try {
    const version = await waitPort(9222);
    console.log('Connected to Chrome:', version['User-Agent']);

    const targetRes = await fetch('http://127.0.0.1:9222/json/new?http://localhost:5173/assistant', { method: 'PUT' });
    const target = await targetRes.json();
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((res) => (ws.onopen = res));

    let id = 1;
    const send = (method, params = {}) => {
      const msgId = id++;
      return new Promise((resolve) => {
        const handler = (evt) => {
          const data = JSON.parse(evt.data);
          if (data.id === msgId) {
            ws.removeEventListener('message', handler);
            resolve(data.result);
          }
        };
        ws.addEventListener('message', handler);
        ws.send(JSON.stringify({ id: msgId, method, params }));
      });
    };

    await send('Network.enable');
    await send('Runtime.enable');
    await send('Page.enable');

    ws.addEventListener('message', (evt) => {
      const msg = JSON.parse(evt.data);
      if (msg.method === 'Runtime.consoleAPICalled') {
        const text = msg.params.args.map((a) => a.value || a.description).join(' ');
        if (!text.includes('SpeechSynthesis chunk playback error')) {
          console.log('[BROWSER CONSOLE]', msg.params.type, text);
        }
      }
      if (msg.method === 'Runtime.exceptionThrown') {
        console.error('[BROWSER EXCEPTION]', msg.params.exceptionDetails);
      }
      if (msg.method === 'Network.requestWillBeSent') {
        if (msg.params.request.url.includes('/api/v1/chat')) {
          console.log('[NETWORK REQUEST]', msg.params.request.method, msg.params.request.url);
        }
      }
      if (msg.method === 'Network.responseReceived') {
        if (msg.params.response.url.includes('/api/v1/chat')) {
          console.log('[NETWORK RESPONSE]', msg.params.response.status, msg.params.response.url);
        }
      }
    });

    console.log('Waiting 3s for page load...');
    await new Promise((r) => setTimeout(r, 3000));

    // TEST 1: Typed input submission
    console.log('\n--- VERIFICATION 1: Typed Text Input ---');
    await send('Runtime.evaluate', {
      expression: `
        (() => {
          const input = document.querySelector('input[type="text"]');
          const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          nativeInputValueSetter.call(input, 'What is PM Surya Ghar?');
          input.dispatchEvent(new Event('input', { bubbles: true }));
          setTimeout(() => {
            const btn = document.querySelector('button[aria-label="Send Message"], button[type="submit"]');
            if (btn) btn.click();
          }, 200);
        })()
      `,
    });

    console.log('Waiting 8s for assistant response...');
    await new Promise((r) => setTimeout(r, 8000));

    const state1 = await send('Runtime.evaluate', {
      returnByValue: true,
      expression: `
        (() => {
          const messages = Array.from(document.querySelectorAll('main p')).map(p => p.textContent);
          const bodyText = document.body.innerText;
          const thinking = bodyText.includes('Analyzing verified scheme rules');
          return { messageCount: messages.length, lastMessage: messages[messages.length - 1]?.slice(0, 80), thinking };
        })()
      `,
    });
    console.log('Result 1 (Typed):', state1.result.value);

    // TEST 2: Voice Modal Sample Query Submission
    console.log('\n--- VERIFICATION 2: Voice Modal Query ---');
    await send('Runtime.evaluate', {
      expression: `
        (() => {
          const btn = document.querySelector('button[aria-label="Start with Voice"]');
          if (btn) btn.click();
        })()
      `,
    });

    await new Promise((r) => setTimeout(r, 1000));

    await send('Runtime.evaluate', {
      expression: `
        (() => {
          const sampleBtns = Array.from(document.querySelectorAll('div[role="dialog"] button')).filter(b => b.textContent.includes('farmer') || b.textContent.includes('Farmer'));
          if (sampleBtns.length > 0) sampleBtns[0].click();
          setTimeout(() => {
            const submitBtn = Array.from(document.querySelectorAll('div[role="dialog"] button')).find(b => b.textContent.includes('Submit Question') || b.textContent.includes('प्रश्न') || b.textContent.includes('ಪ್ರಶ್ನೆ') || b.textContent.includes('ప్రశ్న'));
            if (submitBtn) submitBtn.click();
          }, 400);
        })()
      `,
    });

    console.log('Waiting 8s for voice response...');
    await new Promise((r) => setTimeout(r, 8000));

    const state2 = await send('Runtime.evaluate', {
      returnByValue: true,
      expression: `
        (() => {
          const messages = Array.from(document.querySelectorAll('main p')).map(p => p.textContent);
          const bodyText = document.body.innerText;
          const thinking = bodyText.includes('Analyzing verified scheme rules');
          return { messageCount: messages.length, lastMessage: messages[messages.length - 1]?.slice(0, 80), thinking };
        })()
      `,
    });
    console.log('Result 2 (Voice):', state2.result.value);

    ws.close();
  } finally {
    chromeProc.kill();
  }
}

main().catch(console.error);
