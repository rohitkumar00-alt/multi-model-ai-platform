"""Real model providers that speak HTTP. Two shapes covered:
OpenAI-compatible chat completions (Groq, OpenRouter) and Gemini's
generateContent API."""
import os

import httpx

from app.adapters.base import Generation, ModelAdapter, ModelCallError

DEFAULT_ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}


class OpenAICompatibleAdapter(ModelAdapter):
    """Works for any provider using the OpenAI chat/completions shape."""

    async def generate(self, prompt: str) -> Generation:
        http_cfg = self.config.http
        api_key = os.environ.get(http_cfg.api_key_env)
        if not api_key:
            raise ModelCallError(f"Missing API key: set {http_cfg.api_key_env} in environment")

        endpoint = http_cfg.endpoint or DEFAULT_ENDPOINTS.get(self.config.provider)
        if not endpoint:
            raise ModelCallError(f"No endpoint configured for provider '{self.config.provider}'")

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": http_cfg.model,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(endpoint, headers=headers, json=payload)
        except httpx.RequestError as e:
            raise ModelCallError(f"Network error calling {self.config.provider}: {e}") from e

        if resp.status_code != 200:
            raise ModelCallError(f"{self.config.provider} returned HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ModelCallError(f"Unexpected response shape from {self.config.provider}") from e

        usage = data.get("usage", {})
        return Generation(
            text=text,
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
        )


class GeminiAdapter(ModelAdapter):
    async def generate(self, prompt: str) -> Generation:
        http_cfg = self.config.http
        api_key = os.environ.get(http_cfg.api_key_env)
        if not api_key:
            raise ModelCallError(f"Missing API key: set {http_cfg.api_key_env} in environment")

        endpoint = (
            http_cfg.endpoint
            or f"https://generativelanguage.googleapis.com/v1beta/models/{http_cfg.model}:generateContent"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(endpoint, params={"key": api_key}, json=payload)
        except httpx.RequestError as e:
            raise ModelCallError(f"Network error calling gemini: {e}") from e

        if resp.status_code != 200:
            raise ModelCallError(f"gemini returned HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ModelCallError("Unexpected response shape from gemini") from e

        usage = data.get("usageMetadata", {})
        return Generation(
            text=text,
            tokens_in=usage.get("promptTokenCount"),
            tokens_out=usage.get("candidatesTokenCount"),
        )