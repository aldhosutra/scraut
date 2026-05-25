---
sidebar_position: 5
---

# LLM Providers

Scraut supports five LLM providers and custom endpoints. Configure your choice in `workspace/scraut.yml`.

## Which model should I use?

| Goal | Provider | Model | Setup |
|------|----------|-------|-------|
| Just get started | `github` | `gpt-4o-mini` | Nothing — `GITHUB_TOKEN` auto-provided ✓ |
| Free + better quality | `gemini` | `gemma-4-31b-it` | Add `GOOGLE_API_KEY` secret |
| Best reasoning | `anthropic` | `claude-sonnet-4-6` | Add `ANTHROPIC_API_KEY` secret |
| Fully offline / self-hosted | `ollama` | `qwen2.5:0.5b` | Ollama on your runner |

**GitHub Models is the default** — it requires zero extra configuration and covers all Scraut tasks well. Upgrade when you need better output quality or higher throughput.

---

---

## GitHub Models (default — zero setup) {#github}

:::tip Zero configuration
GitHub Models uses `GITHUB_TOKEN` — automatically injected into every GitHub Actions workflow. No API key, no billing account, no secrets to configure. This is the Scraut default.
:::

```yaml
llm:
  provider: github
  model: gpt-4o-mini    # default
```

**API key:** None — `GITHUB_TOKEN` is auto-provided by GitHub Actions

**Inference endpoint:** `https://models.inference.ai.azure.com` (OpenAI-compatible)

**Free tier rate limits (per personal account):**
| Model tier | RPM | RPD | TPM |
|-----------|-----|-----|-----|
| Low (gpt-4o-mini, Phi-3.5-mini) | 15 | 150 | 8,000 |
| High (gpt-4o) | 10 | 50 | 8,000 |

**Available models (sample):**
| Model | Notes |
|-------|-------|
| `gpt-4o-mini` | **Default** — fast, capable, low-tier rate limits |
| `gpt-4o` | Better reasoning, lower daily limit |
| `Phi-3.5-mini-instruct` | Microsoft's 3.8B open model, same low-tier limits |
| `meta-llama-3.1-70b-instruct` | Open model alternative |

See the full [GitHub Models catalog](https://github.com/marketplace/models) for current model IDs and limits — they change frequently.

:::note Rate limits in practice
150 RPD is enough for a 5-person team running all daily automations (~10–15 LLM calls/day). If you hit limits, switch to `gemini: gemma-4-31b-it` for 10× the daily headroom.
:::

---

## Anthropic (best reasoning) {#anthropic}

:::tip Best output quality
Claude leads on reasoning, nuance, and instruction-following — particularly for sprint planning questions, retrospective synthesis, and milestone decomposition. Recommended when output quality matters more than cost.
:::

```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-6
  small_model: claude-haiku-4-5-20251001   # optional: faster model for summaries/triage
```

**API key:** `ANTHROPIC_API_KEY` GitHub Secret

**Cost:** ~$3/MTok input, ~$15/MTok output (Sonnet). A typical sprint costs **$0.50–$2.00** — see [token cost estimation](#token-cost-estimation).

**Available models:**
| Model | Notes |
|-------|-------|
| `claude-sonnet-4-6` | **Recommended** — best balance of reasoning and speed |
| `claude-opus-4-7` | Highest reasoning quality, higher cost |
| `claude-haiku-4-5-20251001` | Fastest, lowest cost — good as `small_model` |

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

## Google Gemini (free tier, high limits) {#gemini}

:::tip Best free-tier upgrade from GitHub Models
Gemini's free tier via Google AI Studio gives significantly higher daily limits than GitHub Models, with comparable quality. `gemma-4-31b-it` is a 31B open model with unlimited tokens per day.
:::

```yaml
llm:
  provider: gemini
  model: gemma-4-31b-it
```

**API key:** `GOOGLE_API_KEY` GitHub Secret — get a free key at [Google AI Studio](https://aistudio.google.com) (no credit card required)

**Free tier rate limits (Google AI Studio):**
| Model | RPM | RPD | TPD |
|-------|-----|-----|-----|
| `gemma-4-31b-it` | 15 | 1,500 | Unlimited |
| `gemini-2.0-flash` | 15 | 1,500 | Unlimited |
| `gemini-2.5-flash` | 10 | 500 | Unlimited |
| `gemini-2.5-pro` | 5 | 25 | — |

1,500 RPD is 10× GitHub Models' 150 RPD — comfortable for larger teams or repos with high issue volume.

**Available models:**
| Model | Notes |
|-------|-------|
| `gemma-4-31b-it` | **Recommended** — 31B open model, best free-tier quality |
| `gemini-2.0-flash` | Google's fast general model, same free limits |
| `gemini-2.5-flash` | Improved reasoning, slightly lower daily limit |
| `gemini-2.5-pro` | Highest quality, very low free tier (25 RPD) |

Check the [Google AI Studio model list](https://aistudio.google.com) for exact model IDs — names may change between releases.

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
  model: claude-sonnet-4-6               # full model — planning, synthesis, review
  small_model: claude-haiku-4-5-20251001 # fast model — summaries, triage, coach DMs
```

With the default GitHub provider, `small_model` can be omitted — `gpt-4o-mini` is already a small model:

```yaml
llm:
  provider: github
  model: gpt-4o-mini   # already small; small_model: "" is fine
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
  provider: github          # default — zero setup
  model: gpt-4o-mini

  # Upgrade options (uncomment one):
  # fallback:
  #   provider: gemini
  #   model: gemma-4-31b-it       # free, 1.5k RPD, unlimited TPD, better quality
  #
  # fallback:
  #   provider: anthropic
  #   model: claude-sonnet-4-6    # best reasoning, paid
  #
  # fallback:
  #   provider: ollama
  #   model: qwen2.5:0.5b         # offline, self-hosted runners
```

**When to configure a fallback:**

| Fallback | Best for | Free limits | Requirement |
|---------|---------|------------|------------|
| `gemini:gemma-4-31b-it` | Quality upgrade, higher throughput | 1,500 RPD, unlimited TPD | `GOOGLE_API_KEY` secret |
| `anthropic:claude-sonnet-4-6` | Best reasoning | Paid only | `ANTHROPIC_API_KEY` secret |
| `ollama:qwen2.5:0.5b` | Offline, data-privacy-sensitive | Unlimited (local) | Ollama on runner; ~60s startup |

With GitHub as the primary provider, the fallback rarely fires — `GITHUB_TOKEN` is always available in Actions. Configure a fallback only if you want to upgrade quality or handle offline scenarios.

:::tip qwen2.5:0.5b — the best sub-1B model
`qwen2.5:0.5b` (394 MB) is Alibaba's Qwen 2.5 0.5B model. At sub-1B parameters it outperforms much larger models on instruction-following benchmarks and runs comfortably on CPU. It covers all of Scraut's simple tasks — standup summaries, triage, coaching nudges — without a GPU.
:::

The fallback only applies to LLM calls. GitHub API calls (labels, comments, Projects) are not affected.

---

## Choosing a provider

| | GitHub Models | Gemini | Anthropic | OpenAI | Ollama |
|--|-------------|--------|-----------|--------|--------|
| **Setup** | Zero — auto token | Add `GOOGLE_API_KEY` | Add `ANTHROPIC_API_KEY` | Add `OPENAI_API_KEY` | Install Ollama |
| **Reasoning quality** | Good | Good | **Best** | Very good | Varies by model |
| **Free tier RPD** | 150 | **1,500** | None | Limited | Unlimited (local) |
| **Free tier TPD** | ~80k | **Unlimited** | None | Limited | Unlimited (local) |
| **Cost (paid)** | Free | Free / pay-as-you-go | ~$1–2/sprint | ~$1–2/sprint | Free |
| **Data privacy** | Cloud (GitHub/Azure) | Cloud (Google) | Cloud (Anthropic) | Cloud (OpenAI) | **Local** |
| **Actions: no extra steps** | ✓ | ✓ | ✓ | ✓ | Needs `setup-ollama` |

**How to choose:**
- **Starting out / zero friction** → `github: gpt-4o-mini` (default, nothing to configure)
- **Free + more headroom** → `gemini: gemma-4-31b-it` (1,500 RPD, unlimited tokens, one API key)
- **Best output quality** → `anthropic: claude-sonnet-4-6` (strongest reasoning, ~$1–2/sprint)
- **Data stays on-prem** → `ollama: qwen2.5:0.5b` (fully local, self-hosted runner)

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
