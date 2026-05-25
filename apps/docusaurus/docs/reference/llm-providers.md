---
sidebar_position: 5
---

# LLM Providers

Scraut supports five LLM providers and custom endpoints. Configure your choice in `workspace/scraut.yml`.

---

## GitHub Models (zero extra secrets) {#github}

:::tip Best for getting started in GitHub Actions
GitHub Models uses your `GITHUB_TOKEN` — which is automatically available in every GitHub Actions workflow. No API key setup, no billing account. Ideal for teams that want to try Scraut before committing to a cloud provider.
:::

```yaml
llm:
  provider: github
  model: gpt-4o                # or gpt-4o-mini for even lower cost
  small_model: gpt-4o-mini     # optional: cheaper model for simple tasks
```

**API key:** None — `GITHUB_TOKEN` is auto-provided by GitHub Actions

**Inference endpoint:** `https://models.inference.ai.azure.com` (OpenAI-compatible)

**Available models:**
| Model | Notes |
|-------|-------|
| `gpt-4o` | Best quality — recommended for planning and review |
| `gpt-4o-mini` | Faster, very low cost — good as `small_model` |
| `meta-llama-3.1-70b-instruct` | Open model alternative |
| `mistral-large` | Strong reasoning, European data residency |

See the full [GitHub Models catalog](https://github.com/marketplace/models) for the complete list.

:::caution Rate limits
GitHub Models has per-model rate limits (typically 15–50 req/min on the free tier). For high-volume sprints, consider setting `cost_controls.batch_where_possible: true` or switching to a paid provider.
:::

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

## Ollama (local and self-hosted, no API key)

```yaml
llm:
  provider: ollama
  model: qwen2.5:0.5b     # recommended: fast, sub-1B, good quality
  base_url: ""             # defaults to http://localhost:11434
```

**API key:** None required

**Requirements:**
- Ollama installed and running: [ollama.ai](https://ollama.ai)
- Model pulled: `ollama pull qwen2.5:0.5b`

**Recommended models:**
| Model | Size | Notes |
|-------|------|-------|
| `qwen2.5:0.5b` | 394 MB | **Recommended** — best sub-1B quality, fast on CPU |
| `llama3.2:1b` | 1.3 GB | Meta's small model, slightly better at longer outputs |
| `llama3` | 4.7 GB | Full quality, needs more RAM |

**GitHub Actions:** Ollama can run inside a GitHub Actions workflow by adding a setup step. Every LLM-using workflow in Scraut already includes the `setup-ollama` composite action — it's a no-op unless you configure `provider: ollama` or `fallback.provider: ollama`. When active, it installs Ollama, starts the daemon, and pulls your configured model automatically.

```yaml
# From any workflow — already included by default:
- name: Set up Ollama (if configured)
  uses: ./.github/actions/setup-ollama
```

This adds roughly 60–90 seconds to workflow runtime (install + pull `qwen2.5:0.5b`).

**Custom Ollama endpoint (self-hosted runner or remote server):**
```yaml
llm:
  provider: ollama
  model: qwen2.5:0.5b
  base_url: "http://your-ollama-server:11434"
```

---

## Small model support

Set `small_model` to a cheaper/faster model for tasks that don't need full reasoning power (standup summaries, issue classification, coaching nudges). The primary `model` is still used for complex tasks (sprint planning, retrospective synthesis, milestone decomposition).

```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-6          # full model — planning, synthesis, review
  small_model: claude-haiku-4-5-20251001  # fast model — summaries, triage, coach DMs
```

**Tasks that use `small_model` when set:**
- Daily standup summary
- Issue triage
- Standup coach DMs

**Tasks that always use the primary `model`:**
- Sprint planning
- Retrospective synthesis
- Milestone decomposition
- Backlog prioritisation

Leave `small_model: ""` to use the primary model for everything.

---

## Automatic fallback

When the primary provider fails — missing API key, quota exceeded, network error — Scraut retries once with `llm.fallback` before returning an empty string. No configuration is needed on your scripts; the fallback is wired into `complete()`.

```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-6
  # Option A — GitHub Models: zero setup, GITHUB_TOKEN is always available in Actions
  fallback:
    provider: github
    model: gpt-4o-mini

  # Option B — Ollama: fully local, no API key, works offline or on self-hosted runners
  # (requires the setup-ollama composite action in workflows — already included)
  # fallback:
  #   provider: ollama
  #   model: qwen2.5:0.5b
```

**When to use each option:**

| Fallback | Best for | Requirement |
|---------|---------|------------|
| `github` (default) | GitHub Actions, any team, free tier | None — `GITHUB_TOKEN` auto-provided |
| `ollama:qwen2.5:0.5b` | Local dev, offline, data-privacy-sensitive | Ollama installed; ~60s added to CI |

:::tip qwen2.5:0.5b — the best sub-1B model
`qwen2.5:0.5b` (394 MB) is Alibaba's Qwen 2.5 0.5B model. At sub-1B parameters it outperforms much larger models on instruction-following benchmarks and runs comfortably on CPU. It covers all of Scraut's simple tasks — standup summaries, triage, coaching nudges — without a GPU.
:::

The fallback only applies to LLM calls. GitHub API calls (labels, comments, Projects) are not affected.

---

## Choosing a provider

| Factor | GitHub Models | Anthropic | OpenAI | Gemini | Ollama |
|--------|-------------|----------|--------|--------|--------|
| Quality | Very good | Excellent | Excellent | Very good | Good (depends on model) |
| Speed | Fast | Fast | Fast | Fast | Varies |
| Cost | Free (rate-limited) | Medium | Medium | Low | Free |
| Privacy | Cloud | Cloud | Cloud | Cloud | Local |
| GitHub Actions | ✓ (no setup) | ✓ | ✓ | ✓ | ✓ (with setup-ollama step) |
| Free tier | Yes | No | Limited | Yes (AI Studio) | Yes |

**Recommendation:** Start with **GitHub Models** (`gpt-4o`) if you want zero setup — `GITHUB_TOKEN` is already available in every workflow. Switch to **Anthropic** (`claude-sonnet-4-6`) for the highest quality. Use **Gemini** or **Groq** (via OpenAI-compat) for low cost at scale.

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
