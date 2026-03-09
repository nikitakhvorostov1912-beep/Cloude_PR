"""Anthropic Claude SDK async client with structured output support."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import anthropic

from orchestrator.config import AISettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class ClaudeClient:
    """Async wrapper around Anthropic SDK for classification and dialog."""

    def __init__(self, settings: AISettings) -> None:
        self._settings = settings
        self._client: Optional[anthropic.AsyncAnthropic] = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(
                api_key=self._settings.api_key,
                timeout=self._settings.timeout_sec,
            )
        return self._client

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send a completion request to Claude.

        Args:
            system: System prompt.
            messages: Conversation messages [{role, content}].
            tools: Optional tool definitions for function calling.
            temperature: Override default temperature.
            max_tokens: Override default max_tokens.
        """
        client = self._get_client()

        kwargs: dict[str, Any] = {
            "model": self._settings.model,
            "system": system,
            "messages": messages,
            "max_tokens": max_tokens or self._settings.max_tokens,
            "temperature": temperature if temperature is not None else self._settings.temperature,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            response = await client.messages.create(**kwargs)
        except anthropic.APIStatusError as exc:
            logger.error("Claude API error: status=%s body=%s", exc.status_code, exc.body)
            raise
        except anthropic.APIConnectionError:
            logger.exception("Claude API connection error")
            raise

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        return LLMResponse(
            text="\n".join(text_parts),
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason or "end_turn",
            tool_calls=tool_calls,
        )

    async def classify(
        self,
        *,
        system: str,
        transcript: str,
        client_context: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Convenience method for classification tasks.

        Builds a single user message from transcript + optional context.
        """
        content_parts: list[str] = [f"Транскрипт звонка:\n{transcript}"]
        if client_context:
            content_parts.append(f"\nКонтекст клиента:\n{client_context}")

        messages = [{"role": "user", "content": "\n".join(content_parts)}]
        return await self.complete(
            system=system,
            messages=messages,
            tools=tools,
            temperature=0.0,
        )

    async def dialog(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Convenience method for voice dialog (higher temperature)."""
        return await self.complete(
            system=system,
            messages=messages,
            tools=tools,
            temperature=0.3,
            max_tokens=800,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
