import test from "node:test";
import assert from "node:assert/strict";

import { describeAiAvailability, runChatCompletion } from "../src/ai/suggestPhrase.js";

test("LM Studio provider discovers a model and uses chat completions", async () => {
  let receivedBody = null;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options = {}) => {
    if (String(url) === "http://127.0.0.1:1234/v1/models" && (!options.method || options.method === "GET")) {
      return new Response(JSON.stringify({ data: [{ id: "local-test-model" }] }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    }
    if (String(url) === "http://127.0.0.1:1234/v1/chat/completions" && options.method === "POST") {
      receivedBody = JSON.parse(options.body);
      return new Response(JSON.stringify({ choices: [{ message: { content: "borrador local" } }] }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    }
    return new Response("Not found", { status: 404 });
  };

  const previous = {
    provider: process.env.CGV_TRANSLATOR_PROVIDER,
    baseUrl: process.env.CGV_TRANSLATOR_LMSTUDIO_BASE_URL,
    model: process.env.CGV_TRANSLATOR_LMSTUDIO_MODEL
  };

  try {
    process.env.CGV_TRANSLATOR_PROVIDER = "lmstudio";
    process.env.CGV_TRANSLATOR_LMSTUDIO_BASE_URL = "http://127.0.0.1:1234/v1";
    process.env.CGV_TRANSLATOR_LMSTUDIO_MODEL = "";

    const availability = await describeAiAvailability();
    assert.equal(availability.available, true);
    assert.equal(availability.provider, "lmstudio");
    assert.equal(availability.model, "local-test-model");

    const result = await runChatCompletion({ prompt: "Propón español", system: "Solo borrador" });
    assert.equal(result, "borrador local");
    assert.equal(receivedBody.model, "local-test-model");
    assert.equal(receivedBody.stream, false);
  } finally {
    globalThis.fetch = originalFetch;
    for (const [key, value] of Object.entries({
      CGV_TRANSLATOR_PROVIDER: previous.provider,
      CGV_TRANSLATOR_LMSTUDIO_BASE_URL: previous.baseUrl,
      CGV_TRANSLATOR_LMSTUDIO_MODEL: previous.model
    })) {
      if (value == null) delete process.env[key];
      else process.env[key] = value;
    }
  }
});

test("Ollama availability reports a configured model that is not installed", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async url => {
    if (String(url) === "http://127.0.0.1:11434/api/tags") {
      return new Response(JSON.stringify({ models: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    }
    return new Response("Not found", { status: 404 });
  };

  const previous = {
    provider: process.env.CGV_TRANSLATOR_PROVIDER,
    baseUrl: process.env.CGV_TRANSLATOR_OLLAMA_BASE_URL,
    model: process.env.CGV_TRANSLATOR_OLLAMA_MODEL
  };

  try {
    process.env.CGV_TRANSLATOR_PROVIDER = "ollama";
    process.env.CGV_TRANSLATOR_OLLAMA_BASE_URL = "http://127.0.0.1:11434";
    process.env.CGV_TRANSLATOR_OLLAMA_MODEL = "qwen2.5:7b";

    const availability = await describeAiAvailability();
    assert.equal(availability.available, false);
    assert.equal(availability.provider, "ollama");
    assert.match(availability.message, /qwen2\.5:7b is not installed/);
  } finally {
    globalThis.fetch = originalFetch;
    for (const [key, value] of Object.entries({
      CGV_TRANSLATOR_PROVIDER: previous.provider,
      CGV_TRANSLATOR_OLLAMA_BASE_URL: previous.baseUrl,
      CGV_TRANSLATOR_OLLAMA_MODEL: previous.model
    })) {
      if (value == null) delete process.env[key];
      else process.env[key] = value;
    }
  }
});
