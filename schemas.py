"""Esquemas Pydantic compartidos por todos los proveedores."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatMessage(BaseModel):
    """Un mensaje de conversación validado."""

    model_config = ConfigDict(str_strip_whitespace=True)

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ModelConfig(BaseModel):
    """Configuración independiente del proveedor."""

    model_config = ConfigDict(str_strip_whitespace=True)

    provider: Literal["openai", "anthropic"]
    model: str = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=500, ge=1, le=32_000)
    timeout_seconds: float = Field(default=30.0, gt=0.0, le=300.0)
    max_retries: int = Field(default=2, ge=0, le=10)

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value


class ErrorInfo(BaseModel):
    """Error normalizado que no depende del SDK utilizado."""

    code: str
    message: str
    retryable: bool = False


class ModelResponse(BaseModel):
    """Respuesta final común para generación no streaming."""

    content: str | None = None
    provider: Literal["openai", "anthropic"]
    model: str
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: ErrorInfo | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class StreamChunk(BaseModel):
    """Fragmento de streaming; el último puede contener un error controlado."""

    content: str = ""
    error: ErrorInfo | None = None
