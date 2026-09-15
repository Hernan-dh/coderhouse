# Coderhouse

Cliente unificado y completamente asíncrono para usar OpenAI o Anthropic con la misma interfaz. Incluye validación con Pydantic, generación normal, streaming, reintentos con backoff y errores controlados.

## Requisitos

- Python 3.12
- Una API key de OpenAI o Anthropic

## Instalación

En PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

En macOS o Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Editá `.env` y configurá el proveedor y su API key:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Para Anthropic:

```dotenv
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-haiku-latest
```

Nunca subas `.env`; ya está excluido mediante `.gitignore`.

## Ejecución

```powershell
python main.py
```

El script pregunta “¿Qué es la entropía?” primero con una respuesta completa y luego en streaming.

## Estructura

```text
.
├── base.py          # interfaz abstracta y retry asíncrono
├── manager.py       # selección del proveedor
├── providers.py     # adaptadores AsyncOpenAI y AsyncAnthropic
├── schemas.py       # modelos Pydantic
├── main.py          # prueba normal y streaming
├── requirements.txt
├── pyproject.toml
└── .env.example
```

`generate()` siempre devuelve `ModelResponse`. Los errores de autenticación, red, rate limit o API aparecen en `response.error` en lugar de cerrar el programa. `stream()` devuelve un generador asíncrono de `StreamChunk`; cada fragmento trae texto en `content`, y un fallo final se informa mediante `error`.

Los errores transitorios se reintentan con backoff exponencial usando `asyncio.sleep`, por lo que el event loop no queda bloqueado. En streaming sólo se reintenta si todavía no se emitió texto, evitando duplicar contenido.

## Commits automáticos

El proyecto incluye el mismo flujo interactivo de publicación que `portfolio`: verifica el código, genera un título Conventional Commit y una descripción con Gemini o Groq, muestra exactamente qué archivos incluirá y exige confirmación antes de modificar Git.

Primero configurá `GEMINI_API_KEY` o `GROQ_API_KEY` en `.env`. Después, dentro de un repositorio Git local:

```powershell
python scripts/install_hooks.py
python scripts/publish.py --preview
python scripts/publish.py
```

`--preview` no modifica Git. El comando normal sólo ejecuta `git add`, `git commit` y `git push` después de escribir exactamente `PUBLISH`. Nunca hace force-push.

El publicador usa automáticamente el intérprete de `.venv`, aunque la terminal tenga activado otro entorno virtual.

También se puede evitar la generación externa del mensaje:

```powershell
python scripts/publish.py --title "feat: add async client" --description "Add the unified asynchronous LLM client."
```
