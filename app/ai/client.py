"""Memori-wrapped Ollama OpenAI client initialization.

Two clients:
- _raw_client   : used by the internal NLU pipeline (intent engine, extraction).
- _memori_client: registered with Memori BYODB — every call through it
                  automatically persists and recalls memories.  Used for
                  user-facing chat only.
"""

import logging
import sqlite3

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


def create_ollama_client() -> OpenAI:
    """Create an OpenAI-compatible client pointing to Ollama cloud."""
    return OpenAI(
        base_url=settings.OLLAMA_BASE_URL,
        api_key=settings.OLLAMA_API_KEY,
    )


# ── singletons (initialised in FastAPI lifespan) ──────────────────────
_memori_instance = None
_raw_client: OpenAI | None = None
_memori_client: OpenAI | None = None


def init_ai(db_path: str | None = None):
    """Initialise AI clients.  Called once from FastAPI lifespan."""
    global _memori_instance, _raw_client, _memori_client

    # Raw client — NOT registered with Memori.
    _raw_client = create_ollama_client()

    # Separate client for Memori so the SDK can monkey-patch it
    # without affecting internal NLU pipeline calls.
    _memori_client = create_ollama_client()

    path = db_path or settings.DB_PATH

    try:
        from memori import Memori

        def get_db():
            return sqlite3.connect(path)

        mem = Memori(conn=get_db)
        mem.llm.register(client=_memori_client)   # patches client in-place
        _memori_instance = mem
        logger.info("Memori BYODB initialised (local, free)")
    except ImportError:
        logger.warning("memori package not installed — running without memory layer")
        _memori_instance = None
        _memori_client = _raw_client              # fallback to raw
    except Exception as exc:
        logger.warning("Memori setup failed (%s) — running without memory layer", exc)
        _memori_instance = None
        _memori_client = _raw_client


def get_memori():
    """Get the Memori instance (may be None)."""
    return _memori_instance


def get_ollama_client() -> OpenAI:
    """Get the RAW (non-Memori) OpenAI-compatible client."""
    global _raw_client
    if _raw_client is None:
        _raw_client = create_ollama_client()
    return _raw_client


def get_memori_client() -> OpenAI:
    """Get the Memori-registered client (falls back to raw if Memori unavailable)."""
    return _memori_client or get_ollama_client()


def chat_completion(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """Make a chat completion call to Ollama (raw, no memory)."""
    client = get_ollama_client()
    response = client.chat.completions.create(
        model=model or settings.OLLAMA_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def chat_completion_with_memori(
    user_message: str,
    system_prompt: str,
    session_id: str | None = None,
    entity_id: str = "user_local",
    process_id: str = "scheduling_agent",
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """Chat completion through the Memori-registered client.

    Memori BYODB auto-intercepts the call, persists the conversation,
    and augments with recalled memories — no manual recall() needed.
    """
    mem = get_memori()
    client = get_memori_client()

    if mem is not None:
        if session_id:
            mem.set_session(session_id)
        else:
            mem.new_session()
        mem.attribution(entity_id=entity_id, process_id=process_id)

    # The Memori-registered client handles memory automatically.
    try:
        response = client.chat.completions.create(
            model=model or settings.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        logger.warning("Memori client failed (%s), falling back to raw client", exc)
        # Fall back to raw client without memory augmentation
        raw = get_ollama_client()
        response = raw.chat.completions.create(
            model=model or settings.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
