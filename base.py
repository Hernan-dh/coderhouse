"""Interfaz abstracta y utilidades de resiliencia."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import TypeVar

from schemas import ChatMessage, ErrorInfo, ModelConfig, ModelResponse, StreamChunk

T = TypeVar("T")


class ProviderError(Exception):
    """Excepción interna normalizada antes de exponerla al consumidor."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.info = ErrorInfo(code=code, message=message, retryable=retryable)


class BaseLLMClient(ABC):
    """Contrato común para cualquier proveedor asíncrono de LLM."""

    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    async def _retry(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Reintenta sólo errores transitorios sin bloquear el event loop."""
        for attempt in range(self.config.max_retries + 1):
            try:
                return await operation()
            except ProviderError as exc:
                if not exc.info.retryable or attempt >= self.config.max_retries:
                    raise
                await asyncio.sleep(min(2**attempt, 8))
        raise RuntimeError("unreachable")

    def _error_response(self, error: ProviderError) -> ModelResponse:
        return ModelResponse(
            provider=self.config.provider,
            model=self.config.model,
            error=error.info,
        )

    @abstractmethod
    async def generate(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        """Genera una respuesta completa sin bloquear."""

    @abstractmethod
    def stream(self, messages: Sequence[ChatMessage]) -> AsyncIterator[StreamChunk]:
        """Produce fragmentos conforme llegan desde el proveedor."""
