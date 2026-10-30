import assert from 'node:assert/strict';
import test from 'node:test';
import worker from '../worker.mjs';

test('legacy domains and www use the canonical host without losing the URL', async () => {
  for (const host of ['adamant.cc', 'www.adamant.cc', 'www.creed.sh']) {
    for (const path of ['/', '/skills/repo-intelligence/SKILL.md?from=agent&v=1', '/docs/evidence.html?next=https://example.org']) {
      const response = await worker.fetch(new Request(`https://${host}${path}`), {});
      assert.equal(response.status, 308);
      assert.equal(response.headers.get('location'), `https://creed.sh${path}`);
    }
  }
});

test('canonical and worker preview requests go directly to static assets', async () => {
  for (const host of ['creed.sh', 'adamant.example.workers.dev', 'adamant.cc.example.org']) {
    const request = new Request(`https://${host}/creed.md?source=test`);
    let received;
    const response = await worker.fetch(request, { ASSETS: { fetch: async (value) => {
      received = value;
      return new Response('creed');
    } } });
    assert.equal(received, request);
    assert.equal(await response.text(), 'creed');
  }
});
