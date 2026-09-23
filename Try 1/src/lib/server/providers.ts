import "server-only";
import type { ProviderConfig } from "../types";

function jsonFromText(text: string) {
  try { return JSON.parse(text) as unknown; } catch { /* Try JSON embedded in a reasoning response. */ }
  for (let start = text.lastIndexOf("{"); start >= 0; start = text.lastIndexOf("{", start - 1)) {
    for (let end = text.length - 1; end > start; end--) {
      if (text[end] !== "}") continue;
      try { return JSON.parse(text.slice(start, end + 1)) as unknown; } catch { /* Keep looking. */ }
    }
  }
  throw new Error("Provider did not return valid JSON");
}

export async function complete(provider: ProviderConfig, model: string, prompt: string, temperature = 0.2) {
  const base = provider.baseUrl.replace(/\/$/, "");
  const isOllama = provider.kind === "ollama";
  const endpoint = isOllama ? `${base.replace(/\/v1$/, "")}/api/chat` : `${base}/chat/completions`;
  const key = provider.apiKeyEnvVar ? process.env[provider.apiKeyEnvVar] : undefined;
  let lastError: unknown;
  // Local models occasionally emit prose despite JSON mode. Retry that role once;
  // this preserves the same harness and inputs rather than silently changing a result.
  for (let attempt = 0; attempt < 2; attempt++) {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(key ? { Authorization: `Bearer ${key}` } : {}) },
      body: JSON.stringify(isOllama ? {
        model,
        temperature,
        stream: false,
        format: "json",
        think: false,
        messages: [
          { role: "system", content: "You are a disciplined industrial RCA agent. Return exactly one valid JSON object and no prose or markdown. Do not invent document facts; reference only fact IDs supplied to you." },
          { role: "user", content: prompt },
        ],
      } : {
        model,
        temperature,
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: "You are a disciplined industrial RCA agent. Return exactly one valid JSON object and no prose or markdown. Do not invent document facts; reference only fact IDs supplied to you." },
          { role: "user", content: prompt },
        ],
      }),
    });
    if (!response.ok) throw new Error(`${provider.name} returned ${response.status}: ${await response.text()}`);
    const body = await response.json() as { choices?: { message?: { content?: string | null; reasoning?: string; reasoning_content?: string; thinking?: string } }[]; message?: { content?: string | null; reasoning?: string; reasoning_content?: string; thinking?: string } };
    const message = body.choices?.[0]?.message ?? body.message;
    const text = message?.content || message?.reasoning_content || message?.reasoning;
    try {
      if (!text) throw new Error(`Provider response did not contain usable content: ${JSON.stringify(message ?? {})}`);
      return jsonFromText(text);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}
