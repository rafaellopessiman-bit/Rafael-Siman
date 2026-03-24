from groq import AsyncGroq, Groq

from src.core.config import get_settings
from src.core.llm_cache import get_cache
from src.exceptions import (
    AtlasProviderAuthError,
    AtlasProviderRateLimitError,
    AtlasProviderSchemaError,
    AtlasProviderTransientError,
)


def generate_fast_completion(prompt: str, temperature: float = 0.0) -> str:
    """
    Generate completion from LLM with caching.
    
    Checks cache first to avoid redundant API calls.
    If cache miss, calls Groq API and stores result.
    """
    # Try cache first
    cache = get_cache()
    cached_response = cache.get(prompt)
    if cached_response:
        return cached_response
    
    settings = get_settings()

    try:
        client = Groq(api_key=settings.groq_api_key)

        response = client.chat.completions.create(
            model=settings.groq_model,
            temperature=temperature,
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente técnico objetivo. Responda de forma clara, curta e fiel ao contexto recebido.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise AtlasProviderSchemaError("O provider retornou resposta vazia.")

        content = content.strip()
        
        # Store in cache for future use
        cache.put(prompt, content)
        
        return content

    except Exception as exc:
        status_code = getattr(exc, "status_code", None)

        if status_code == 401:
            raise AtlasProviderAuthError(
                "Falha de autenticação no Groq: verifique a GROQ_API_KEY."
            ) from exc

        if status_code == 429:
            raise AtlasProviderRateLimitError(
                "Rate limit do Groq atingido. Tente novamente em instantes."
            ) from exc

        if status_code == 422:
            raise AtlasProviderSchemaError(
                f"Requisição inválida para o Groq: {exc}"
            ) from exc

        if status_code in {500, 502, 503}:
            raise AtlasProviderTransientError(
                "Falha transitória no Groq. Tente novamente."
            ) from exc

        raise AtlasProviderTransientError(
            f"Erro inesperado na comunicação com o Groq: {exc}"
        ) from exc



# =========================
# Structured output helper
# =========================

from typing import Type, TypeVar
import asyncio
import inspect
import json

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def structured_call(
    prompt: str,
    response_model: Type[T],
    *,
    system_prompt: str | None = None,
    temperature: float = 0.0,
) -> T:
    """
    Helper síncrono e conservador para structured output.
    Tenta reutilizar a função de completion já existente no módulo.
    """

    generator = globals().get("generate_completion") or globals().get("generate_fast_completion")
    if generator is None:
        raise RuntimeError("Nenhuma função de geração encontrada em src.core.llm_client")

    kwargs = {}
    try:
        params = inspect.signature(generator).parameters
    except (TypeError, ValueError):
        params = {}

    if "json_mode" in params:
        kwargs["json_mode"] = True
    if "temperature" in params:
        kwargs["temperature"] = temperature
    if "system_prompt" in params and system_prompt is not None:
        kwargs["system_prompt"] = system_prompt

    raw = generator(prompt, **kwargs)

    if inspect.isawaitable(raw):
        raw = asyncio.run(raw)

    if hasattr(raw, "choices"):
        try:
            raw = raw.choices[0].message.content
        except Exception as exc:
            raise RuntimeError(f"Resposta do provider em formato inesperado: {exc}") from exc

    if not isinstance(raw, str):
        raw = str(raw)

    try:
        return response_model.model_validate_json(raw)
    except ValidationError as exc:
        raise RuntimeError(f"Schema do provider inválido: {exc}") from exc
    except Exception:
        try:
            data = json.loads(raw)
            return response_model.model_validate(data)
        except Exception as exc:
            raise RuntimeError(f"Falha ao interpretar structured output: {exc}") from exc


# =========================
# Async completion helper (optional, for parallel requests)
# =========================

async def generate_fast_completion_async(
    prompt: str,
    temperature: float = 0.0,
    timeout: int = 30,
) -> str:
    """
    Async LLM completion using native AsyncGroq client.

    Checks cache first (shared with sync version). On cache miss,
    makes a true async API call — does not block the event loop.

    Args:
        prompt: The prompt text
        temperature: Temperature for generation (0.0 = deterministic)
        timeout: Per-request timeout in seconds

    Returns:
        Generated completion string
    """
    cache = get_cache()
    cached = cache.get(prompt)
    if cached:
        return cached

    settings = get_settings()
    client = AsyncGroq(api_key=settings.groq_api_key)

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.groq_model,
                temperature=temperature,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um assistente técnico objetivo. Responda de forma clara, curta e fiel ao contexto recebido.",
                    },
                    {"role": "user", "content": prompt},
                ],
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise AtlasProviderTransientError(
            f"Timeout durante geração (>{timeout}s). Tente novamente."
        ) from None

    content = response.choices[0].message.content
    if not content or not content.strip():
        raise AtlasProviderSchemaError("O provider retornou resposta vazia.")
    content = content.strip()
    cache.put(prompt, content)
    return content


async def generate_multiple_completions_async(
    prompts: list[str],
    temperature: float = 0.0,
    timeout: int = 30,
) -> list[str]:
    """
    Generate multiple completions in parallel (concurrently).
    
    Useful for generating multiple steps in a plan.
    More efficient than sequential calls.
    
    Args:
        prompts: List of prompts to generate completions for
        temperature: Temperature for all generations
        timeout: Per-request timeout in seconds
    
    Returns:
        List of completions (ordered same as prompts)
    """
    tasks = [
        generate_fast_completion_async(prompt, temperature, timeout)
        for prompt in prompts
    ]
    
    try:
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results
    except Exception:
        # Fallback: generate sequentially
        return [generate_fast_completion(p, temperature) for p in prompts]
