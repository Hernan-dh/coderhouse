"""Prueba manual de generación normal y streaming."""

import asyncio
import os

from dotenv import load_dotenv

from manager import AsyncLLMManager
from schemas import ChatMessage, ModelConfig


async def main() -> None:
    load_dotenv()
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    model_env = "OPENAI_MODEL" if provider == "openai" else "ANTHROPIC_MODEL"
    default_model = "gpt-4o-mini" if provider == "openai" else "claude-3-5-haiku-latest"

    config = ModelConfig(
        provider=provider,
        model=os.getenv(model_env, default_model),
        temperature=0.3,
        max_tokens=250,
    )
    manager = AsyncLLMManager(config)
    messages = [ChatMessage(role="user", content="¿Qué es la entropía?")]

    print("=== Respuesta normal ===")
    response = await manager.client.generate(messages)
    if response.ok:
        print(response.content)
    else:
        print(f"Error [{response.error.code}]: {response.error.message}")

    print("\n=== Respuesta streaming ===")
    async for chunk in manager.client.stream(messages):
        if chunk.error:
            print(f"\nError [{chunk.error.code}]: {chunk.error.message}")
            break
        print(chunk.content, end="", flush=True)
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (ValueError, KeyboardInterrupt) as exc:
        print(f"No se pudo iniciar: {exc}")
