"""Reasoning-layer ports — stable interfaces for external reasoning capabilities.

LLM-powered reasoners depend on ``LLMProvider``, never on specific vendor
SDKs.  Concrete providers (Anthropic, OpenAI, local models) are
infrastructure adapters injected through the composition root.

Current status: protocol only — no concrete provider is implemented yet.
"""

from typing import Protocol

from psf_reasoner.schemas.common import Provenance


class LLMProvider(Protocol):
    """Stable interface for structured LLM completions.

    Reasoners call ``complete()`` with a system prompt, a user prompt, and
    a JSON Schema that constrains the output.  The provider returns a
    parsed dict that MUST conform to the schema.  Token usage metadata is
    recorded so every LLM-generated claim is traceable.
    """

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict,
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> "LLMCompletion": ...


class LLMUsage:
    """Vendor-neutral token usage snapshot."""

    def __init__(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
    ) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class LLMCompletion:
    """Result of a single structured LLM call.

    The ``provenance()`` method produces ``Provenance`` entries whose
    ``parameters`` dict only contains scalar values (no nested dicts),
    keeping them compatible with the ``ParameterValue`` union in
    ``schemas/common.py``.
    """

    def __init__(
        self,
        content: dict,
        model: str,
        usage: LLMUsage | None = None,
        finish_reason: str = "stop",
    ) -> None:
        self.content = content
        self.model = model
        self.usage = usage
        self.finish_reason = finish_reason

    def provenance(self, method: str) -> tuple[Provenance, ...]:
        """Build provenance entries for claims derived from this completion.

        Token counts are expanded to scalar ``prompt_tokens`` /
        ``completion_tokens`` / ``total_tokens`` fields so they conform
        to ``Provenance.parameters: dict[str, ParameterValue]``.
        """
        from psf_reasoner.schemas.common import Provenance, ProvenanceKind

        return (
            Provenance(
                kind=ProvenanceKind.COMPUTATION,
                source=f"LLM ({self.model})",
                method=method,
                parameters={
                    "finish_reason": self.finish_reason,
                    "prompt_tokens": self.usage.prompt_tokens if self.usage else None,
                    "completion_tokens": self.usage.completion_tokens if self.usage else None,
                    "total_tokens": self.usage.total_tokens if self.usage else None,
                },
            ),
        )
