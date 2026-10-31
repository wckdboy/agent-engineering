// Exercise the actual app renderer with a minimal DOM, without browser dependencies or network.
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { runInNewContext } from 'node:vm';

const app = await readFile(new URL('../site/assets/app.js', import.meta.url), 'utf8');
const data = JSON.parse(await readFile(new URL('../site/data/site.json', import.meta.url), 'utf8'));
const legacy = { id: 'fixture', name: 'Fixture', role: 'Test', status: 'green', evidence: 'A recorded check passed', branch: 'main', gate: 'make check', notes: 'Not a release claim' };

async function render(repos) {
  const nodes = new Map();
  const events = new Map();
  const requests = [];
  const node = selector => {
    if (!nodes.has(selector)) nodes.set(selector, {
      innerHTML: '', textContent: '', dataset: {},
      addEventListener() {}, setAttribute() {}, querySelector: node,
      insertAdjacentHTML(_position, html) { assert.fail(html); },
    });
    return nodes.get(selector);
  };
  runInNewContext(app, {
    document: {
      readyState: 'loading', documentElement: { dataset: {} },
      querySelector: node, querySelectorAll: () => [],
      addEventListener: (name, callback) => events.set(name, callback),
    },
    localStorage: { getItem: () => 'light' }, window: {}, URL,
    fetch: async url => {
      requests.push(url);
      return { ok: true, json: async () => ({ ...data, repos }) };
    },
  });
  await events.get('DOMContentLoaded')();
  assert.deepEqual(requests, ['./data/site.json'], 'evidence links must never be fetched');
  return node('#repo-grid').innerHTML;
}

test('repository cards identify recorded status and render dated HTTPS evidence safely', async () => {
  const html = await render([{ ...legacy, last_observed: '2026-10-30', evidence_links: [
    { label: '<Run> & result', url: 'https://example.org/runs/123?job=4&attempt=1' },
  ] }]);
  assert.match(html, /recorded green/);
  assert.match(html, /Recorded observation · not live CI/);
  assert.match(html, /Last observed: <time datetime="2026-10-30">2026-10-30<\/time>/);
  assert.match(html, /href="https:\/\/example.org\/runs\/123\?job=4&amp;attempt=1"/);
  assert.match(html, /rel="noopener noreferrer"/);
  assert.match(html, /&lt;Run&gt; &amp; result/);
  assert.doesNotMatch(html, /<Run>/);
});

test('legacy records and the template do not invent dates, evidence or live results', async () => {
  const html = await render([legacy, { ...legacy, status: 'template' }]);
  assert.equal((html.match(/Last observed: not recorded/g) || []).length, 2);
  assert.equal((html.match(/No linked evidence recorded/g) || []).length, 2);
  assert.match(html, />template<\/span>/);
  assert.doesNotMatch(html, /recorded template|<time|href=/);
});

test('malformed provenance is ignored even if a payload bypasses the builder', async () => {
  const invalid = ['javascript:alert(1)', 'http://example.org/run', '//example.org/run', '/run',
    'https:///run', 'https://', 'https://[invalid', 'https://example.org:bad/run', 'https://example.org:99999/run',
    'https://user:pass@example.org/run', 'https://@example.org/run', 'https://example.org\\@evil.invalid/run',
    'https://example.org/\nrun', 'https://exa mple.org/run', 'https://example.org/\x00run', null, 123];
  for (const last_observed of ['2026-02-30', '2026-1-01', '20261030', '', null, 20261030]) {
    const html = await render([{ ...legacy, last_observed, evidence_links: [
      ...invalid.map(url => ({ label: 'Unsafe', url })), null, {},
      { label: ' ', url: 'https://example.org/run' }, { label: 123, url: 'https://example.org/run' },
      { label: 'Safe', url: 'https://example.org/safe' },
    ] }]);
    assert.match(html, /Last observed: not recorded/);
    assert.equal((html.match(/href=/g) || []).length, 1);
    assert.match(html, /href="https:\/\/example.org\/safe"/);
    assert.doesNotMatch(html, /Unsafe|<time/);
  }
  for (const evidence_links of [null, {}, 'https://example.org/run']) {
    assert.match(await render([{ ...legacy, evidence_links }]), /No linked evidence recorded/);
  }
});
