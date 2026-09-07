import assert from "node:assert/strict";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the MockMate interview setup", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>MockMate — AI Interview Practice<\/title>/i);
  assert.match(html, /Shape your interview/i);
  assert.match(html, /Start my interview/i);
  assert.match(html, /Practice like it’s the real thing|Walk into your next interview/i);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|react-loading-skeleton/i);
});

test("includes accessible product controls and social metadata", async () => {
  const response = await render();
  const html = await response.text();

  assert.match(html, /aria-label="Primary navigation"/i);
  assert.match(html, /name="twitter:card" content="summary_large_image"/i);
  assert.match(html, /property="og:image" content="http:\/\/localhost(?::3000)?\/og.png"/i);
  assert.match(html, /AI-powered practice space/i);
});