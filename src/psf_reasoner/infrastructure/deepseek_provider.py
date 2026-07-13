"""DeepSeek API provider — implements the LLMProvider protocol.

DeepSeek offers an OpenAI-compatible chat-completions endpoint.
"""

from __future__ import annotations

import json
import os

import httpx

from psf_reasoner.reasoning.ports import LLMCompletion, LLMUsage

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_CHAT_MODEL = "deepseek-chat"


class DeepSeekProvider:
    """Structured completion via the DeepSeek API.

    Requires ``DEEPSEEK_API_KEY`` in the environment or passed directly.
    Uses the OpenAI-compatible ``/v1/chat/completions`` endpoint.
    """

    def __init__(
        self,
        model: str = DEEPSEEK_CHAT_MODEL,
        api_key: str | None = None,
        base_url: str = DEEPSEEK_BASE_URL,
        timeout: float = 120.0,
    ) -> None:
        self._model = model
        self._api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self._base_url = base_url
        self._timeout = timeout

    # ------------------------------------------------------------------
    # LLMProvider protocol
    # ------------------------------------------------------------------

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict,
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMCompletion:
        if not self._api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not set")

        schema_json = json.dumps(output_schema, ensure_ascii=False)

        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"{user_prompt}\n\n"
                        f"Output must be valid JSON conforming to this JSON Schema:\n"
                        f"```json\n{schema_json}\n```\n"
                        f"Respond with ONLY the JSON object, no markdown fences."
                    ),
                },
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        response = httpx.post(
            f"{self._base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        text = choice["message"]["content"]

        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        content = json.loads(text)
        usage_payload = data.get("usage", {})

        return LLMCompletion(
            content=content,
            model=data.get("model", self._model),
            usage=LLMUsage(
                prompt_tokens=usage_payload.get("prompt_tokens", 0),
                completion_tokens=usage_payload.get("completion_tokens", 0),
                total_tokens=usage_payload.get("total_tokens", 0),
            ),
            finish_reason=choice.get("finish_reason", "stop"),
        )
