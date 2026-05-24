"""
lib/llm/client.py
Swappable LLM provider. Reads provider from scraut.yml.
All calls include token tracking and cost controls.
"""
import os
import logging
import re
import json
from typing import Optional
from scraut.platform.utils.config import get_llm_config

logger = logging.getLogger(__name__)

_daily_tokens_used = 0


def complete(prompt: str, system: Optional[str] = None,
             max_tokens: Optional[int] = None) -> str:
    """
    Call the configured LLM provider with a prompt.
    Returns the text response.
    Falls back to empty string on failure.
    """
    global _daily_tokens_used
    config = get_llm_config()
    provider = config.get("provider", "anthropic")
    max_tok = max_tokens or config.get("max_tokens", 1000)
    daily_limit = config.get("cost_controls", {}).get("max_daily_tokens", 100000)

    if _daily_tokens_used >= daily_limit:
        logger.warning("Daily token limit reached. Returning empty response.")
        return ""

    try:
        if provider == "anthropic":
            return _call_anthropic(prompt, system, max_tok)
        elif provider == "openai":
            return _call_openai(prompt, system, max_tok)
        elif provider == "ollama":
            return _call_ollama(prompt, system, max_tok)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return ""


def _call_anthropic(prompt: str, system: Optional[str], max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    config = get_llm_config()
    messages = [{"role": "user", "content": prompt}]
    kwargs = {
        "model": config.get("model", "claude-sonnet-4-6"),
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    global _daily_tokens_used
    _daily_tokens_used += response.usage.input_tokens + response.usage.output_tokens
    return response.content[0].text


def _call_openai(prompt: str, system: Optional[str], max_tokens: int) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    config = get_llm_config()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=config.get("model", "gpt-4o"),
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.choices[0].message.content


def _call_ollama(prompt: str, system: Optional[str], max_tokens: int) -> str:
    import requests
    config = get_llm_config()
    url = config.get("ollama_url", "http://localhost:11434/api/generate")
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    response = requests.post(url, json={
        "model": config.get("model", "llama3"),
        "prompt": full_prompt,
        "stream": False,
    })
    return response.json()["response"]


def complete_batch(prompts: list, system: Optional[str] = None,
                   max_tokens: Optional[int] = None) -> list:
    """
    Process multiple prompts in a single LLM call to reduce token overhead.
    Each prompt is separated with a numbered marker.
    Use when batching multiple independent requests (e.g., triage 5 issues at once).
    """
    config = get_llm_config()
    if not config.get("cost_controls", {}).get("batch_where_possible"):
        return [complete(p, system, max_tokens) for p in prompts]

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

    raw = complete(batch_prompt, system, max_tokens=max_tokens or 2000)
    try:
        clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        results = json.loads(clean)
        if isinstance(results, list) and len(results) == len(prompts):
            return results
    except Exception:
        pass

    return [complete(p, system, max_tokens) for p in prompts]


def complete_json(prompt: str, system: Optional[str] = None) -> dict:
    """Call LLM expecting JSON output. Strips markdown fences before parsing."""
    text = complete(prompt, system)
    if not text:
        return {}
    # Strip ```json fences
    clean = re.sub(r"```(?:json)?\s*", "", text)
    clean = re.sub(r"```\s*$", "", clean).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}\nResponse: {text}")
        return {}
