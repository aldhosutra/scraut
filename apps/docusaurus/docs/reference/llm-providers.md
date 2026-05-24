---
sidebar_position: 5
---

# LLM Providers

Scraut supports four LLM providers and custom endpoints. Configure your choice in `workspace/scraut.yml`.

---

## Anthropic (default)

```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-6    # recommended
  base_url: ""                # leave empty for default
```

**API key:** `ANTHROPIC_API_KEY` GitHub Secret

**Available models:**
| Model | Notes |
|-------|-------|
| `claude-sonnet-4-6` | Recommended — best balance of speed and quality |
| `claude-opus-4-7` | Highest quality, higher cost |
| `claude-haiku-4-5-20251001` | Fastest, lowest cost |

**Custom endpoint (Anthropic-compatible proxy):**
```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-6
  base_url: "https://your-proxy.example.com"
```

---

## OpenAI

```yaml
llm:
  provider: openai
  model: gpt-4o
  base_url: ""
```

**API key:** `OPENAI_API_KEY` GitHub Secret

**Available models:**
| Model | Notes |
|-------|-------|
| `gpt-4o` | Recommended |
| `gpt-4o-mini` | Faster, lower cost |
| `gpt-4-turbo` | Large context window |

**Custom endpoint (OpenAI-compatible):**

Scraut's OpenAI provider works with any OpenAI-compatible API:

```yaml
# Groq (fast inference)
llm:
  provider: openai
  model: llama-3.1-70b-versatile
  base_url: "https://api.groq.com/openai/v1"

# DeepSeek
llm:
  provider: openai
  model: deepseek-chat
  base_url: "https://api.deepseek.com/v1"

# LM Studio (local)
llm:
  provider: openai
  model: your-local-model
  base_url: "http://localhost:1234/v1"
  # Note: LM Studio doesn't need an API key —
  # set OPENAI_API_KEY to any non-empty string like "lm-studio"
```

For local endpoints with no authentication, set `OPENAI_API_KEY` to any non-empty value (e.g. `"local"`).

---

## Google Gemini

```yaml
llm:
  provider: gemini
  model: gemini-1.5-pro
  base_url: ""
```

**API key:** `GOOGLE_API_KEY` GitHub Secret (get from [Google AI Studio](https://aistudio.google.com))

**Available models:**
| Model | Notes |
|-------|-------|
| `gemini-1.5-pro` | Recommended |
| `gemini-1.5-flash` | Faster, lower cost |
| `gemini-2.0-flash` | Latest flash model |

---

## Ollama (local, no API key)

```yaml
llm:
  provider: ollama
  model: llama3
  base_url: ""   # defaults to http://localhost:11434
```

**API key:** None required

**Requirements:**
- Ollama installed and running locally: [ollama.ai](https://ollama.ai)
- Model pulled: `ollama pull llama3`

:::caution GitHub Actions limitation
Ollama runs locally — GitHub Actions workflows **cannot** reach your local machine. Ollama is only usable when you run Scraut scripts locally (not via GitHub Actions). For GitHub Actions, use a cloud provider.
:::

**Custom Ollama endpoint:**
```yaml
llm:
  provider: ollama
  model: llama3
  base_url: "http://your-ollama-server:11434"
```

---

## Choosing a provider

| Factor | Anthropic | OpenAI | Gemini | Ollama |
|--------|----------|--------|--------|--------|
| Quality | Excellent | Excellent | Very good | Good (depends on model) |
| Speed | Fast | Fast | Fast | Varies |
| Cost | Medium | Medium | Low | Free |
| Privacy | Cloud | Cloud | Cloud | Local |
| GitHub Actions | ✓ | ✓ | ✓ | ✗ (local only) |
| Free tier | No | Limited | Yes (AI Studio) | Yes |

**Recommendation:** Start with Anthropic (`claude-sonnet-4-6`) for the best out-of-box experience. Switch to Gemini or Groq (via OpenAI-compat) if cost is a concern.

---

## Token cost estimation

A typical sprint with 5 team members uses roughly:

| Ceremony | Approx tokens/sprint |
|----------|---------------------|
| Daily standups (10 days × 1 summary) | ~15,000 |
| Sprint planning | ~8,000 |
| Sprint review | ~5,000 |
| Retrospective synthesis | ~4,000 |
| Backlog grooming (2×/sprint) | ~10,000 |
| Issue triage (10 new issues) | ~5,000 |
| **Total** | **~47,000 tokens/sprint** |

At `claude-sonnet-4-6` pricing (~$3/MTok input, ~$15/MTok output), a typical sprint costs **$0.50–$2.00**.

The `cost_controls.max_daily_tokens` setting (default: 100,000) acts as a hard fail-safe.
