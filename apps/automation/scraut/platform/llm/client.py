"""
platform/llm/client.py
Swappable LLM provider. Reads provider from scraut.yml.
Supports: anthropic, openai, gemini, ollama, github.
All calls include token tracking, cost controls, and automatic fallback.
"""
import os
import logging
import re
import json
from typing import Optional
from scraut.platform.utils.config import get_llm_config

logger = logging.getLogger(__name__)

_daily_tokens_used = 0

# GitHub Models inference endpoint — uses GITHUB_TOKEN, no extra secret needed.
_GITHUB_MODELS_BASE_URL = "https://models.inference.ai.azure.com"


def _resolve_model(config: dict, use_small_model: bool) -> Optional[str]:
    """Return the model name to use. Falls back to primary model if small_model is unset."""
    if use_small_model:
        small = config.get("small_model", "")
        if small:
            return small
    return config.get("model")


def _dispatch_provider(
    provider: str,
    prompt: str,
    system: Optional[str],
    max_tok: int,
    model: Optional[str],
) -> str:
    """Route a single call to the named provider. Raises on any failure."""
    if provider == "anthropic":
        return _call_anthropic(prompt, system, max_tok, model=model)
    elif provider == "openai":
        return _call_openai(prompt, system, max_tok, model=model)
    elif provider == "gemini":
        return _call_gemini(prompt, system, max_tok, model=model)
    elif provider == "ollama":
        return _call_ollama(prompt, system, max_tok, model=model)
    elif provider == "github":
        return _call_github(prompt, system, max_tok, model=model)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def complete(
    prompt: str,
    system: Optional[str] = None,
    max_tokens: Optional[int] = None,
    use_small_model: bool = False,
) -> str:
    """Call the configured LLM provider. Returns text; falls back to '' on failure.

    Pass use_small_model=True for simple tasks (summaries, classification, short DMs)
    to use llm.small_model when configured, reducing cost without sacrificing quality.

    If the primary provider fails (e.g. missing API key), automatically retries with
    llm.fallback if configured before returning ''.
    """
    global _daily_tokens_used
    config = get_llm_config()
    provider = config.get("provider", "anthropic")
    model = _resolve_model(config, use_small_model)
    max_tok = max_tokens or config.get("max_tokens", 1000)
    daily_limit = config.get("cost_controls", {}).get("max_daily_tokens", 100000)

    if _daily_tokens_used >= daily_limit:
        logger.warning("Daily token limit reached. Returning empty response.")
        return ""

    try:
        return _dispatch_provider(provider, prompt, system, max_tok, model)
    except Exception as e:
        fallback = config.get("fallback", {})
        fb_provider = fallback.get("provider", "")
        if fb_provider:
            logger.warning(
                f"LLM call failed ({provider}): {e}. "
                f"Retrying with fallback provider: {fb_provider}"
            )
            try:
                return _dispatch_provider(
                    fb_provider, prompt, system, max_tok, fallback.get("model")
                )
            except Exception as e2:
                logger.error(f"Fallback LLM also failed ({fb_provider}): {e2}")
        else:
            logger.error(f"LLM call failed ({provider}): {e}")
        return ""


def _call_anthropic(
    prompt: str,
    system: Optional[str],
    max_tokens: int,
    model: Optional[str] = None,
) -> str:
    import anthropic
    config = get_llm_config()
    client_kwargs: dict = {"api_key": os.environ["ANTHROPIC_API_KEY"]}
    base_url = config.get("base_url", "")
    if base_url:
        client_kwargs["base_url"] = base_url

    client = anthropic.Anthropic(**client_kwargs)
    messages = [{"role": "user", "content": prompt}]
    call_kwargs: dict = {
        "model": model or config.get("model", "claude-sonnet-4-6"),
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        call_kwargs["system"] = system

    response = client.messages.create(**call_kwargs)
    global _daily_tokens_used
    _daily_tokens_used += response.usage.input_tokens + response.usage.output_tokens
    return response.content[0].text


def _call_openai(
    prompt: str,
    system: Optional[str],
    max_tokens: int,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    from openai import OpenAI
    config = get_llm_config()
    resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "no-key")
    resolved_url = base_url or config.get("base_url", "") or None

    client_kwargs: dict = {"api_key": resolved_key}
    if resolved_url:
        client_kwargs["base_url"] = resolved_url
    client = OpenAI(**client_kwargs)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model or config.get("model", "gpt-4o"),
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.choices[0].message.content


def _call_github(
    prompt: str,
    system: Optional[str],
    max_tokens: int,
    model: Optional[str] = None,
) -> str:
    """Call GitHub Models — OpenAI-compatible, authenticated with GITHUB_TOKEN.

    No extra secret needed: GITHUB_TOKEN is auto-provided by GitHub Actions.
    Default model: gpt-4o-mini (fast and cheap for most Scraut tasks).
    """
    config = get_llm_config()
    return _call_openai(
        prompt, system, max_tokens,
        model=model or config.get("model", "gpt-4o-mini"),
        api_key=os.environ.get("GITHUB_TOKEN", ""),
        base_url=_GITHUB_MODELS_BASE_URL,
    )


def _call_gemini(
    prompt: str,
    system: Optional[str],
    max_tokens: int,
    model: Optional[str] = None,
) -> str:
    import google.generativeai as genai
    config = get_llm_config()
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))

    model_name = model or config.get("model", "gemini-1.5-pro")
    generation_config = genai.types.GenerationConfig(max_output_tokens=max_tokens)
    genai_model = genai.GenerativeModel(
        model_name,
        system_instruction=system if system else None,
        generation_config=generation_config,
    )

    response = genai_model.generate_content(prompt)
    global _daily_tokens_used
    meta = getattr(response, "usage_metadata", None)
    if meta:
        _daily_tokens_used += (
            getattr(meta, "prompt_token_count", 0) +
            getattr(meta, "candidates_token_count", 0)
        )
    return response.text


def _call_ollama(
    prompt: str,
    system: Optional[str],
    max_tokens: int,
    model: Optional[str] = None,
) -> str:
    import requests
    config = get_llm_config()
    url = config.get("ollama_url", "http://localhost:11434/api/generate")
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    response = requests.post(url, json={
        "model": model or config.get("model", "llama3"),
        "prompt": full_prompt,
        "stream": False,
    })
    return response.json()["response"]


def complete_batch(
    prompts: list,
    system: Optional[str] = None,
    max_tokens: Optional[int] = None,
    use_small_model: bool = False,
) -> list:
    """
    Process multiple prompts in a single LLM call to reduce token overhead.
    Each prompt is separated with a numbered marker.
    Use when batching multiple independent requests (e.g., triage 5 issues at once).
    """
    config = get_llm_config()
    if not config.get("cost_controls", {}).get("batch_where_possible"):
        return [complete(p, system, max_tokens, use_small_model) for p in prompts]

    if not prompts:
        return []

    batch_prompt = "Answer each numbered prompt INDEPENDENTLY. Reply with JSON array.\n\n"
    for i, p in enumerate(prompts, 1):
        batch_prompt += f"=== PROMPT {i} ===\n{p}\n\n"
    batch_prompt += (
        f"Reply with ONLY a JSON array of {len(prompts)} strings, "
        f"one result per prompt:\n"
        f'["result for prompt 1", "result for prompt 2", ...]'
    )

    raw = complete(batch_prompt, system, max_tokens=max_tokens or 2000,
                   use_small_model=use_small_model)
    try:
        clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        results = json.loads(clean)
        if isinstance(results, list) and len(results) == len(prompts):
            return results
    except Exception:
        pass

    return [complete(p, system, max_tokens, use_small_model) for p in prompts]


def complete_json(
    prompt: str,
    system: Optional[str] = None,
    use_small_model: bool = False,
) -> dict:
    """Call LLM expecting JSON output. Strips markdown fences before parsing."""
    text = complete(prompt, system, use_small_model=use_small_model)
    if not text:
        return {}
    clean = re.sub(r"```(?:json)?\s*", "", text)
    clean = re.sub(r"```\s*$", "", clean).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}\nResponse: {text}")
        return {}
