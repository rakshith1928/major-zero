import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { stripTypeScriptTypes } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../src/pages/Chat.tsx', import.meta.url), 'utf8');
function evaluate(code: string, globals: Record<string, unknown>) {
  const context = vm.createContext(globals);
  vm.runInContext(stripTypeScriptTypes(code), context);
  return context;
}

function loaderHarness() {
  const scripts: Script[] = [];
  const timers = new Map<number, () => void>();
  let timerId = 0;
  class Script {
    dataset = {};
    src = '';
    listeners = new Map<string, () => void>();
    addEventListener(event: string, fn: () => void) { this.listeners.set(event, fn); }
    removeEventListener(event: string) { this.listeners.delete(event); }
    remove() { const index = scripts.indexOf(this); if (index >= 0) scripts.splice(index, 1); }
  }
  const window = {
    Razorpay: undefined as unknown,
    setTimeout(fn: () => void) { timers.set(++timerId, fn); return timerId; },
    clearTimeout(id: number) { timers.delete(id); },
  };
  const code = source.slice(source.indexOf('let razorpayLoader:'), source.indexOf('interface ChatMessage'));
  const context = evaluate(code, {
    window, HTMLScriptElement: Script,
    document: { querySelector: () => scripts[0], createElement: () => new Script(), body: { appendChild: (s: Script) => scripts.push(s) } },
  });
  return { context, scripts, timers, window };
}

test('loader timeout removes stale script and allows a new attempt', async () => {
  const h = loaderHarness();
  const first = h.context.loadRazorpay();
  const rejected = assert.rejects(first, /timed out/);
  for (const callback of [...h.timers.values()]) callback();
  await rejected;
  assert.equal(h.scripts.length, 0);
  const retry = h.context.loadRazorpay();
  assert.notEqual(retry, first);
  h.window.Razorpay = function () {};
  h.scripts[0].listeners.get('load')!();
  await retry;
});

test('loader rejects a loaded script without a checkout constructor', async () => {
  const h = loaderHarness();
  const result = h.context.loadRazorpay();
  const rejected = assert.rejects(result, /unavailable|failed/i);
  h.scripts[0].listeners.get('load')!();
  await rejected;
  assert.equal(h.scripts.length, 0);
});

function paymentHarness(overrides: Record<string, unknown> = {}) {
  let paying = false;
  let messages: { content: string }[] = [];
  let options: Record<string, any> = {};
  const code = source.slice(source.indexOf('  function pay()') >= 0 ? source.indexOf('  function pay()') : source.indexOf('  async function pay()'), source.indexOf('  function voiceInput()'));
  const context = evaluate(code, {
    booking: { booking_ref: 'B1', status: 'PENDING_PAYMENT' }, paying: false,
    paymentInFlight: { current: false },
    setPaying: (value: boolean) => { paying = value; },
    setDemoPay: () => {},
    setBooking: () => {},
    setMessages: (update: (m: typeof messages) => typeof messages) => { messages = update(messages); },
    api: { createOrder: async () => ({ checkout_mode: 'razorpay_test', key_id: 'rzp_test_stub', order_id: 'order_stub', amount: 100, currency: 'INR' }), verifyPayment: async () => { throw new Error('verification unavailable'); } },
    loadRazorpay: async () => {},
    window: { Razorpay: function (value: typeof options) { options = value; return { open() {} }; } },
    ...overrides,
  });
  return { context, get paying() { return paying; }, get messages() { return messages; }, get options() { return options; } };
}

async function flush() {
  await new Promise(resolve => setImmediate(resolve));
  await new Promise(resolve => setImmediate(resolve));
}

async function settle(h: ReturnType<typeof paymentHarness>) {
  await h.context.pay();
  await flush();
}

test('missing checkout constructor releases the Pay button', async () => {
  const h = paymentHarness({ window: {} });
  await settle(h);
  assert.equal(h.paying, false);
  assert.match(h.messages.at(-1)!.content, /didn't go through|failed|unavailable/i);
});

test('verification rejection is caught and shown in chat', async () => {
  const h = paymentHarness();
  await settle(h);
  await h.options.handler({ razorpay_order_id: 'order_stub', razorpay_payment_id: 'pay_stub', razorpay_signature: 'signature' });
  await flush();
  assert.match(h.messages.at(-1)!.content, /verification unavailable/);
});

test('incomplete gateway callback does not fabricate verification credentials', async () => {
  let called = false;
  const h = paymentHarness({ api: { createOrder: async () => ({ checkout_mode: 'razorpay_test', key_id: 'rzp_test_stub' }), verifyPayment: async () => { called = true; return { status: 'PAID' }; } } });
  await settle(h);
  await h.options.handler({});
  assert.equal(called, false);
  assert.match(h.messages.at(-1)!.content, /incomplete/i);
});
