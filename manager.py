"""Factory que selecciona el proveedor bajo una interfaz única."""

import os

from base import BaseLLMClient
from providers import AnthropicClient, OpenAIClient
from schemas import ModelConfig


class AsyncLLMManager:
    """Construye el adaptador indicado en ModelConfig."""

    def __init__(self, config: ModelConfig) -> None:
        self.config = config
        self.client = self._build_client()

    def _build_client(self) -> BaseLLMClient:
        if self.config.provider == "openai":
            return OpenAIClient(self.config, self._required_env("OPENAI_API_KEY"))
        return AnthropicClient(self.config, self._required_env("ANTHROPIC_API_KEY"))

    @staticmethod
    def _required_env(name: str) -> str:
        value = os.getenv(name)
        if not value or value.startswith("your-"):
            raise ValueError(f"Falta configurar la variable de entorno {name}")
        return value
