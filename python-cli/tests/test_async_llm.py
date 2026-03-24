"""
Tests for Async LLM Client (C3 — real AsyncGroq).

All tests use monkeypatch / unittest.mock to avoid real API calls.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.llm_client import (
    generate_fast_completion_async,
    generate_multiple_completions_async,
)
from src.exceptions import AtlasProviderSchemaError, AtlasProviderTransientError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_async_response(content: str) -> MagicMock:
    """Build a fake Groq chat-completion response object."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_generate_fast_completion(monkeypatch):
    """generate_fast_completion_async returns content from AsyncGroq."""
    from src.core.llm_cache import reset_cache
    reset_cache()

    fake_response = _make_async_response("resposta async")

    async_client = MagicMock()
    async_client.chat = MagicMock()
    async_client.chat.completions = MagicMock()
    async_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("src.core.llm_client.AsyncGroq", return_value=async_client):
        result = await generate_fast_completion_async("Prompt de teste")

    assert result == "resposta async"


@pytest.mark.asyncio
async def test_async_generate_multiple_completions(monkeypatch):
    """generate_multiple_completions_async retorna uma lista com mesmo tamanho."""
    from src.core.llm_cache import reset_cache
    reset_cache()

    call_count = 0

    async def _fake_create(**kwargs):
        nonlocal call_count
        call_count += 1
        return _make_async_response(f"resposta {call_count}")

    async_client = MagicMock()
    async_client.chat.completions.create = _fake_create

    prompts = ["A", "B", "C"]
    with patch("src.core.llm_client.AsyncGroq", return_value=async_client):
        results = await generate_multiple_completions_async(prompts)

    assert len(results) == len(prompts)
    assert all(isinstance(r, str) for r in results)


def test_async_can_be_called_from_sync():
    """generate_fast_completion_async pode ser chamada de contexto síncrono."""
    from src.core.llm_cache import reset_cache
    reset_cache()

    fake_response = _make_async_response("sync wrapper ok")

    async_client = MagicMock()
    async_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("src.core.llm_client.AsyncGroq", return_value=async_client):
        result = asyncio.run(generate_fast_completion_async("Teste sync"))

    assert result == "sync wrapper ok"


@pytest.mark.asyncio
async def test_async_hits_cache_without_api_call():
    """Se o cache já tem a resposta, AsyncGroq não é chamado."""
    from src.core.llm_cache import reset_cache, get_cache
    reset_cache()

    cache = get_cache()
    prompt = "prompt em cache"
    cache.put(prompt, "resposta em cache")

    async_client = MagicMock()
    async_client.chat.completions.create = AsyncMock(side_effect=AssertionError("API não deveria ser chamada"))

    with patch("src.core.llm_client.AsyncGroq", return_value=async_client):
        result = await generate_fast_completion_async(prompt)

    assert result == "resposta em cache"


@pytest.mark.asyncio
async def test_async_timeout_raises_transient_error():
    """Timeout deve virar AtlasProviderTransientError."""
    from src.core.llm_cache import reset_cache
    reset_cache()

    async def _slow_create(**kwargs):
        await asyncio.sleep(0.05)
        return _make_async_response("não deve chegar aqui")

    async_client = MagicMock()
    async_client.chat.completions.create = _slow_create

    with patch("src.core.llm_client.AsyncGroq", return_value=async_client):
        with pytest.raises(AtlasProviderTransientError):
            await generate_fast_completion_async("prompt timeout", timeout=0.001)


@pytest.mark.asyncio
async def test_async_empty_content_raises_schema_error():
    """Resposta vazia deve levantar AtlasProviderSchemaError."""
    from src.core.llm_cache import reset_cache
    reset_cache()

    fake_response = _make_async_response("   ")
    async_client = MagicMock()
    async_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("src.core.llm_client.AsyncGroq", return_value=async_client):
        with pytest.raises(AtlasProviderSchemaError):
            await generate_fast_completion_async("prompt vazio")

