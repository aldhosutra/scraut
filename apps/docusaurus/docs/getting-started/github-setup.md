---
sidebar_position: 4
---

# GitHub Setup

Scraut requires a few one-time setup steps in your GitHub repository settings before workflows can run.

---

## Step 1: Add GitHub Secrets

Go to your repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

Add the following secrets:

### Required

| Secret name | Value | Used by |
|------------|-------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | All LLM-powered workflows |
| *(or)* `OPENAI_API_KEY` | Your OpenAI API key | If using OpenAI provider |
| *(or)* `GOOGLE_API_KEY` | Your Google AI key | If using Gemini provider |

### Recommended

| Secret name | Value | Used by |
|------------|-------|---------|
| `SLACK_WEBHOOK` | Slack incoming webhook URL | Standup, ceremonies, alerts |
| `SLACK_BOT_TOKEN` | Slack bot OAuth token | Personal morning DMs |

### Optional

| Secret name | Value | Used by |
|------------|-------|---------|
| `SCRAUT_GITHUB_TOKEN` | PAT with repo:read | Repo sync (connected repos) |
| `SMTP_HOST` | SMTP server hostname | Weekly email digest |
| `SMTP_PORT` | SMTP port (e.g. `587`) | Weekly email digest |
| `SMTP_USER` | SMTP username | Weekly email digest |
| `SMTP_PASS` | SMTP password | Weekly email digest |

:::tip GITHUB_TOKEN is automatic
You do NOT need to add `GITHUB_TOKEN` — GitHub provides it automatically to every workflow run.
:::

---

## Step 2: Create GitHub Labels

Scraut uses a specific set of labels for story points, priority, type, and status. Create them with:

```bash
# If GITHUB_TOKEN is set locally:
export GITHUB_TOKEN=your_personal_access_token
python apps/automation/scraut/platform/setup/create_labels.py --repo myorg/my-repo
```

Or let `scraut init` / `npx create-scraut` do it automatically when run with `GITHUB_TOKEN` set.

The labels created are documented in the [Labels Reference](../reference/labels).

---

## Step 3: Enable GitHub Actions

Actions should be enabled by default, but verify:

1. Go to **Settings** → **Actions** → **General**
2. Select **Allow all actions and reusable workflows**
3. Under **Workflow permissions**, select **Read and write permissions**
4. Check **Allow GitHub Actions to create and approve pull requests**

The "read and write permissions" is required so workflows can commit generated summaries back to the repo (with `[skip ci]` to avoid loops).

---

## Step 4: Enable GitHub Pages (for the Visibility Portal)

1. Go to **Settings** → **Pages**
2. Under **Source**, select **Deploy from a branch**
3. Select branch: `main`, folder: `/ (root)` or `/docs` depending on your portal config
4. Click **Save**

The portal URL will be `https://your-org.github.io/your-repo/`.

:::info
The portal publish workflow (`portal-publish.yml`) handles the actual deployment. GitHub Pages just needs to be enabled once.
:::

---

## Step 5: Set up GitHub Projects (optional but recommended)

The Visibility Engine syncs sprint state to a GitHub Projects board.

1. Go to **Projects** → **New project** → **Board** template
2. Name it something like "Sprint Board"
3. Note the project number from the URL (e.g. `https://github.com/orgs/myorg/projects/5` → number is `5`)
4. Add it to `workspace/scraut.yml`:

```yaml
portal:
  project_number: 5   # add this field
```

---

## Step 6: Verify everything works

Trigger the first workflow manually to confirm your secrets are wired correctly:

1. Go to **Actions** tab in your repo
2. Find **Scraut — Daily Standup Summary**
3. Click **Run workflow** → **Run workflow**
4. Watch the logs — if it completes successfully, you're ready

Common issues:
- `ANTHROPIC_API_KEY` not set → workflow fails with `AuthenticationError`
- `SLACK_WEBHOOK` not set → workflow completes but no Slack message (check logs for "SLACK_WEBHOOK not configured")
- Permissions error on git push → check "Read and write permissions" in Step 3

---

## Slack webhook setup

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Name it "Scraut", select your workspace
3. Go to **Incoming Webhooks** → toggle **On**
4. Click **Add New Webhook to Workspace** → select `#scraut-bot`
5. Copy the webhook URL (starts with `https://hooks.slack.com/services/...`)
6. Add it as the `SLACK_WEBHOOK` GitHub Secret

---

Next: [Your First Sprint →](./first-sprint)
