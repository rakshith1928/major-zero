import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, friendlyError } from '../src/errors.ts';

test('passes through plain string details', () => {
  assert.equal(friendlyError(400, '{"detail":"travel date cannot be in the past"}'), 'travel date cannot be in the past');
});

test('summarizes FastAPI validation arrays without braces', () => {
  const body = '{"detail":[{"loc":["body","email"],"msg":"Field required","type":"missing"}]}';
  const out = friendlyError(422, body);
  assert.ok(out.includes('email'), out);
  assert.ok(!out.includes('{'), out);
});

test('renders corridor hints from object details', () => {
  const body = '{"detail":{"message":"Nowhere is not on this bus\'s corridor","stops":["Bangalore","Vellore","Chennai"]}}';
  const out = friendlyError(422, body);
  assert.ok(out.includes('Vellore'), out);
  assert.ok(!out.includes('{'), out);
});

test('never pastes markup or empty bodies', () => {
  assert.ok(!friendlyError(502, '<html>Bad Gateway</html>').includes('<'));
  assert.ok(friendlyError(0, '').includes('connection'));
});

test('ApiError carries status for auth guards', () => {
  const err = new ApiError(401, 'nope');
  assert.equal(err.status, 401);
  assert.ok(err instanceof Error);
});
