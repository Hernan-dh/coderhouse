"""Adaptadores asíncronos de OpenAI y Anthropic."""

from collections.abc import AsyncIterator, Sequence
from typing import Any

import anthropic
import openai
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from base import BaseLLMClient, ProviderError
from schemas import ChatMessage, ModelConfig, ModelResponse, StreamChunk


def _safe_message(exc: Exception) -> str:
    """Evita propagar representaciones extensas o detalles internos del SDK."""
    return str(exc).strip() or exc.__class__.__name__


class OpenAIClient(BaseLLMClient):
    def __init__(self, config: ModelConfig, api_key: str) -> None:
        super().__init__(config)
        self._client = AsyncOpenAI(api_key=api_key, timeout=config.timeout_seconds, max_retries=0)

    def _translate(self, exc: Exception) -> ProviderError:
        if isinstance(exc, openai.RateLimitError):
            return ProviderError("rate_limit", _safe_message(exc), retryable=True)
        if isinstance(exc, (openai.APIConnectionError, openai.APITimeoutError)):
            return ProviderError("network_error", _safe_message(exc), retryable=True)
        if isinstance(exc, openai.AuthenticationError):
            return ProviderError("authentication_error", _safe_message(exc))
        if isinstance(exc, openai.APIStatusError):
            retryable = exc.status_code >= 500
            return ProviderError("api_error", _safe_message(exc), retryable=retryable)
        return ProviderError("unexpected_error", _safe_message(exc))

    def _messages(self, messages: Sequence[ChatMessage]) -> list[dict[str, str]]:
        return [message.model_dump() for message in messages]

    async def generate(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        async def request() -> Any:
            try:
                return await self._client.chat.completions.create(
                    model=self.config.model,
                    messages=self._messages(messages),  # type: ignore[arg-type]
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
            except Exception as exc:
                raise self._translate(exc) from exc

        try:
            response = await self._retry(request)
            choice = response.choices[0]
            return ModelResponse(
                content=choice.message.content or "",
                provider="openai",
                model=response.model,
                finish_reason=choice.finish_reason,
                input_tokens=response.usage.prompt_tokens if response.usage else None,
                output_tokens=response.usage.completion_tokens if response.usage else None,
            )
        except ProviderError as exc:
            return self._error_response(exc)

    async def stream(self, messages: Sequence[ChatMessage]) -> AsyncIterator[StreamChunk]:
        emitted = False
        for attempt in range(self.config.max_retries + 1):
            try:
                stream = await self._client.chat.completions.create(
                    model=self.config.model,
                    messages=self._messages(messages),  # type: ignore[arg-type]
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    stream=True,
                )
                async for chunk in stream:
                    text = chunk.choices[0].delta.content if chunk.choices else None
                    if text:
                        emitted = True
                        yield StreamChunk(content=text)
                return
            except Exception as raw_exc:
                exc = self._translate(raw_exc)
                if exc.info.retryable and not emitted and attempt < self.config.max_retries:
                    import asyncio

                    await asyncio.sleep(min(2**attempt, 8))
                    continue
                yield StreamChunk(error=exc.info)
                return

class AnthropicClient(BaseLLMClient):
    def __init__(self, config: ModelConfig, api_key: str) -> None:
        super().__init__(config)
        self._client = AsyncAnthropic(api_key=api_key, timeout=config.timeout_seconds, max_retries=0)

    def _translate(self, exc: Exception) -> ProviderError:
        if isinstance(exc, anthropic.RateLimitError):
            return ProviderError("rate_limit", _safe_message(exc), retryable=True)
        if isinstance(exc, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
            return ProviderError("network_error", _safe_message(exc), retryable=True)
        if isinstance(exc, anthropic.AuthenticationError):
            return ProviderError("authentication_error", _safe_message(exc))
        if isinstance(exc, anthropic.APIStatusError):
            retryable = exc.status_code >= 500
            return ProviderError("api_error", _safe_message(exc), retryable=retryable)
        return ProviderError("unexpected_error", _safe_message(exc))

    def _payload(self, messages: Sequence[ChatMessage]) -> tuple[str | None, list[dict[str, str]]]:
        system_parts = [message.content for message in messages if message.role == "system"]
        conversation = [
            {"role": message.role, "content": message.content}
            for message in messages
            if message.role != "system"
        ]
        return "\n\n".join(system_parts) or None, conversation

    async def generate(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        system, conversation = self._payload(messages)

        async def request() -> Any:
            try:
                kwargs: dict[str, Any] = {
                    "model": self.config.model,
                    "messages": conversation,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                }
                if system:
                    kwargs["system"] = system
                return await self._client.messages.create(**kwargs)
            except Exception as exc:
                raise self._translate(exc) from exc

        try:
            response = await self._retry(request)
            text = "".join(block.text for block in response.content if block.type == "text")
            return ModelResponse(
                content=text,
                provider="anthropic",
                model=response.model,
                finish_reason=response.stop_reason,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        except ProviderError as exc:
            return self._error_response(exc)

    async def stream(self, messages: Sequence[ChatMessage]) -> AsyncIterator[StreamChunk]:
        import asyncio

        system, conversation = self._payload(messages)
        emitted = False
        for attempt in range(self.config.max_retries + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": self.config.model,
                    "messages": conversation,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                }
                if system:
                    kwargs["system"] = system
                async with self._client.messages.stream(**kwargs) as stream:
                    async for text in stream.text_stream:
                        emitted = True
                        yield StreamChunk(content=text)
                return
            except Exception as raw_exc:
                exc = self._translate(raw_exc)
                if exc.info.retryable and not emitted and attempt < self.config.max_retries:
                    await asyncio.sleep(min(2**attempt, 8))
                    continue
                yield StreamChunk(error=exc.info)
                return
