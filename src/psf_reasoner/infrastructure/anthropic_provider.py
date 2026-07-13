"""Anthropic Claude provider — implements the LLMProvider protocol."""

from __future__ import annotations

import json
import os

from anthropic import Anthropic

from psf_reasoner.reasoning.ports import LLMCompletion, LLMUsage


class AnthropicProvider:
    """Structured completion via the Anthropic Messages API.

    Requires ``ANTHROPIC_API_KEY`` in the environment or passed directly.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-5",
        api_key: str | None = None,
        max_retries: int = 1,
    ) -> None:
        self._model = model
        self._client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self._max_retries = max_retries

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
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = response.content[0].text

        # Anthropic may wrap JSON in ```json fences — strip them.
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        content = json.loads(text)

        usage = None
        if response.usage is not None:
            usage = LLMUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

        return LLMCompletion(
            content=content,
            model=self._model,
            usage=usage,
            finish_reason=response.stop_reason or "stop",
        )
