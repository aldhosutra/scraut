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

Your GitHub Pages URL will become your team's sprint dashboard.

1. Go to **Settings** → **Pages**
2. Under **Source**, select **GitHub Actions** *(not "Deploy from a branch")*
3. Click **Save**

That's all. The `portal-publish.yml` workflow handles the actual deployment automatically — it fires whenever the visibility engine updates `apps/portal/`. Your dashboard will be live at:

```
https://your-org.github.io/your-repo/
```

:::info How the portal gets updated
The **Visibility Engine** workflow runs every 30 minutes and on every push to standup/sprint files. It generates `apps/portal/index.html` and `apps/portal/data.json` from the current sprint state, commits them, which triggers `portal-publish.yml` to redeploy Pages.
:::

:::warning Don't select "Deploy from a branch"
"Deploy from a branch → main → /docs" is the setting for the Scraut documentation site at [aldhosutra.github.io/scraut](https://aldhosutra.github.io/scraut/). That's the template repo's setup. Your team repo should use **GitHub Actions** as the source so the portal workflow controls deployment.
:::

---

## Step 4b: Standup web form (optional — requires Vercel or Netlify)

`apps/portal/form.html` is a web form that lets non-technical team members submit standups without knowing Git. It submits to `apps/portal/api/standup.js`, which is a serverless edge function.

**GitHub Pages cannot run server-side functions.** The form works as a static page but the submit button needs the edge function deployed separately.

To enable form submissions:

1. Deploy to **Vercel**: `cd apps/portal && npx vercel --prod`
   — or connect the repo to Vercel via the dashboard, set root to `apps/portal`
2. Set these environment variables in Vercel:
   - `GITHUB_TOKEN` — PAT with `repo` write scope for your team's repo
   - `SCRAUT_REPO` — `your-org/your-repo`
   - `PORTAL_TOKEN` — any shared secret string (prevents abuse)
3. Update `CONFIG.apiEndpoint` in `apps/portal/form.html` to your Vercel function URL

Without this deployment, the form HTML is still served (team members can see it), but submissions will fail. The primary standup flow — editing the Markdown file directly in GitHub — always works regardless.

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
