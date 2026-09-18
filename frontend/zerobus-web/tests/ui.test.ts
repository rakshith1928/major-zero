import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'rolldown';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';

const require = createRequire(import.meta.url);
async function load(relative: string, user: { email: string; is_admin: boolean } | null = null) {
  const entry = fileURLToPath(new URL(`../src/${relative}`, import.meta.url));
  const result = await build({
    input: entry, write: false, platform: 'node', external: (id) => /^(react|react-dom|react-router-dom)(\/|$)/.test(id),
    output: { format: 'cjs', exports: 'named' },
    transform: { jsx: { runtime: 'automatic' } },
    plugins: [{ name: 'render-test-boundaries',
      resolveId(source) {
        if (source.endsWith('/auth')) return { id: 'test-auth', external: true };
        if (relative === 'App.tsx' && source.startsWith('./pages/')) return { id: 'test-page', external: true };
      },
      load(id) {
        if (id === entry && relative === 'App.tsx') return readFileSync(id, 'utf8') + '\nexport { Nav };';
      },
    }],
  });
  const chunk = result.output.find((item) => item.type === 'chunk');
  assert.ok(chunk && chunk.type === 'chunk');
  const module = { exports: {} as any };
  vm.runInNewContext(chunk.code, { module, exports: module.exports, require: (name: string) => {
    if (name === 'test-auth') return { useAuth: () => ({ user, logout() {} }), AuthProvider: ({ children }: any) => children };
    if (name === 'test-page') return { default: () => null };
    return require(name);
  } });
  return module.exports;
}
function render(Component: any, path = '/') {
  return renderToStaticMarkup(React.createElement(MemoryRouter, { initialEntries: [path] }, React.createElement(Component)));
}

test('navigation marks exactly one current destination', async () => {
  const html = render((await load('App.tsx')).Nav, '/tickets');
  assert.match(html, /aria-current="page"[^>]*href="\/tickets"|href="\/tickets"[^>]*aria-current="page"/);
  assert.equal((html.match(/aria-current="page"/g) || []).length, 1);
});
test('navigation has a named landmark and branded home link', async () => {
  const html = render((await load('App.tsx')).Nav);
  assert.match(html, /aria-label="Main navigation"/);
  assert.match(html, /aria-label="ZeroBus home"/);
  assert.match(html, /favicon\.svg/);
});
test('guests see login but not admin navigation', async () => {
  const html = render((await load('App.tsx')).Nav);
  assert.match(html, /href="\/login"/);
  assert.doesNotMatch(html, /href="\/dashboard"/);
});
test('admin account navigation stays compact and retains its actions', async () => {
  const html = render((await load('App.tsx', { email: 'long-address@example.com', is_admin: true })).Nav, '/dashboard');
  assert.match(html, /href="\/dashboard"/);
  assert.match(html, /href="\/profile"/);
  assert.match(html, /Log out/);
  assert.doesNotMatch(html, /long-address@example.com/);
});
test('landing labels the illustrative conversation and prototype limitations', async () => {
  const html = render((await load('pages/Landing.tsx')).default);
  assert.match(html, /Your next trip/);
  assert.match(html, /Illustrative conversation/);
  assert.match(html, /simulated/i);
  assert.match(html, /no real money/i);
  assert.match(html, /href="\/chat"/);
});
