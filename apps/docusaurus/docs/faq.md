---
sidebar_position: 99
---

# FAQ

Common questions about setting up and using Scraut.

---

## Setup

### Can the product owner and scrum master be the same person?

Yes. Set both to the same GitHub login:

```yaml
team:
  product_owner: alice
  scrum_master: alice
```

Neither field currently changes what automation runs — they are informational labels stored in the config. See [Team Roles](./reference/team-roles) for full details.

### Do the `product_owner` and `scrum_master` fields affect automation?

No. All 28 workflows treat every team member the same. Any person with repository write access can trigger any ceremony. The fields exist as documentation of intent and as a foundation for future role-based routing. See [Team Roles](./reference/team-roles).

### Can I use Scraut with a team of one?

Yes. Set all role fields to your own login, add yourself as the only member, and run normally. Standup summaries, retro synthesis, and all automations work with a single-member team.

### We're already on sprint 5 — do we have to start over at sprint 1?

No. Both setup wizards ask "Starting sprint number" and default to 1. Enter your current sprint number instead:

```
Starting sprint number (1 for a brand-new team): 5
```

The wizard will:
- Set `current_sprint: 5` in `scraut.yml`
- Scaffold `workspace/sprint/005/` (not `sprint/001/`)
- Create today's standup files and retro templates for sprint 5
- All subsequent automation — standup summaries, grooming, planning — works against sprint 5

If you're mid-sprint (not starting fresh), you can skip triggering sprint-planning and just let the daily automation pick up. Trigger it at your next sprint boundary.

### Do I need a GitHub Projects board?

No, but board sync is **on by default**. The HTML portal always generates and deploys regardless. The GitHub Projects board sync is a second output from the same pipeline — it updates board columns to match the derived sprint state.

To activate board sync, set `project_number` in `scraut.yml`:
```yaml
portal:
  sync_board: true       # default — no need to add unless you changed it
  project_number: 5      # your board's number from the GitHub Projects URL
```

To turn board sync off entirely and suppress the warning:
```yaml
portal:
  sync_board: false
```

All planning, standup, and reporting workflows read from text files, not the board. The board is always a derived view, never a source of truth.

### What is `portal.project_number`?

It's the number at the end of your GitHub Projects URL:

```
https://github.com/orgs/myorg/projects/5
                                        ↑ this is project_number: 5
```

Go to **Projects** → open your board → copy the number from the URL. Without this value, board sync is skipped (HTML portal still works).

### What LLM do I need?

Any of: Anthropic Claude, OpenAI GPT-4o, Google Gemini, Ollama (local), or any OpenAI-compatible endpoint. You only need one. See [LLM Providers](./reference/llm-providers) for setup details.

---

## Team management

### How does the sprint/NN folder get created?

Automatically, when you trigger the **sprint-planning** workflow from the Actions tab. It calls `create_sprint.py` which creates:
- `workspace/sprint/NN/` with `standup/`, `retrospective/`, `grooming/`, `decisions/`, `adr/` subdirs
- `.scraut/sprint/NN/` output dirs
- `workspace/sprint/NN/meta.md` with period and team info
- `workspace/sprint/NN/grooming/backlog-ideas.md`
- A GitHub milestone named `Sprint NN`

You never create the sprint folder by hand. Trigger sprint-planning from the Actions tab, and everything is scaffolded.

### How does the daily standup folder (`standup/YYYY-MM-DD/`) get created?

Automatically, by the **template-reset** workflow. It runs every weekday at 1:55 AM UTC (before your team starts work) and creates:
```
workspace/sprint/NN/standup/YYYY-MM-DD/alice.md
workspace/sprint/NN/standup/YYYY-MM-DD/bob.md
```
One file per team member, pre-filled with the standup template. The workflow commits these with `[skip ci]` so they don't trigger the summary workflow. Files that already exist (e.g., if someone submitted earlier) are never overwritten.

### What if my standup file wasn't created automatically today?

Two options:

1. **Manual trigger**: Go to Actions → `Scraut — Daily Template Reset` → Run workflow
2. **CLI**: Run `scraut sync` — it creates today's standup file for any member who doesn't have one yet, without touching files that already exist

### How do I add a team member mid-sprint?

1. Add them to `team.members` in `workspace/scraut.yml`
2. Run `scraut sync` — it creates their standup file for today and their retro file, without touching anyone else's files
3. Commit and push — they're now included in all subsequent summaries

```bash
# After editing scraut.yml:
scraut sync
git add workspace/ && git commit -m "chore: add bob to sprint 02 [skip ci]" && git push
```

### How do I remove a team member?

Remove their entry from `team.members` in `scraut.yml`. Their historical standup and retro files remain intact (never deleted by automation). Future ceremony runs will not include them.

### What happens if a team member doesn't submit a standup?

The standup summary workflow runs when anyone pushes to a standup file. If a member hasn't pushed, their file either doesn't exist for that day or still contains the template. The LLM summarises only the files that exist — missing submitters are not mentioned in the summary. There is no automated reminder beyond the morning DM.

### Can team members be in different timezones?

Yes, but all scheduled workflows run on a single timezone configured in `scraut.yml`:

```yaml
sprint:
  timezone: "UTC"
```

Morning DMs fire at 7:55am in this timezone. If your team spans multiple timezones, set the timezone to where most members are, or to UTC, and members in other zones adjust individually.

---

## Workflows

### Which workflows are automatic and which need manual triggering?

**Three workflows require manual triggering** from Actions → [workflow name] → Run workflow:

| Workflow | When |
|----------|------|
| **Sprint Planning** | Start of each sprint |
| **Sprint Review** | End of each sprint |
| **Sprint Retrospective** | End of each sprint (after review) |

**Everything else is automatic** — scheduled by cron or triggered by GitHub events (issue opened, PR merged, push to standup files, etc.). See the [Workflows reference](./reference/workflows) for the full breakdown.

### Who can trigger manual workflows?

Any GitHub user with write access to the repository. The manually-triggered ceremonies are `workflow_dispatch` workflows accessible from the Actions tab. There is no built-in role check.

### What does `[skip ci]` mean in commit messages?

It tells GitHub Actions not to trigger workflows on that commit. Scraut bot commits always include `[skip ci]` to prevent infinite loops where a bot commit triggers a workflow that makes another bot commit.

Your own commits should NOT include `[skip ci]` unless you specifically want to skip automation — for example, when committing workspace setup files that don't need immediate processing.

### A workflow failed — where do I look?

1. Go to the **Actions** tab in your repository
2. Click the failed run
3. Expand the failed step to see the error output
4. Common causes:
   - Missing secret (e.g. `ANTHROPIC_API_KEY` not set)
   - LLM rate limit or quota exceeded
   - `scraut.yml` parse error (check YAML syntax)
   - Missing `workspace/` files the script expected

### Can I disable a specific ceremony?

Yes. Set the ceremony to `false` in `scraut.yml`:

```yaml
ceremonies:
  estimation: false   # disables emoji-based story point voting
  grooming: false     # disables Wednesday backlog grooming
```

The corresponding workflow still exists in `.github/workflows/` but its scripts check this flag at the start and exit cleanly if disabled.

### Why isn't my morning DM arriving?

Morning DMs require:
1. `SLACK_BOT_TOKEN` secret set (different from `SLACK_WEBHOOK`)
2. `slack_id` set for each member in `scraut.yml`
3. `notifications.morning_dm: true` in `scraut.yml`
4. The Slack bot invited to the workspace

Channel posts only need `SLACK_WEBHOOK`. DMs to individuals need the bot token.

---

## Configuration

### How do I apply config changes to the workspace?

Edit `workspace/scraut.yml` directly (it's a plain YAML file), then run `scraut sync`:

```bash
# Example: added a team member, changed sprint number, etc.
scraut sync          # scaffolds anything missing based on current config
scraut sync --dry-run  # preview first
```

`scraut sync` is safe to run any time — it only creates files that are missing and never overwrites existing ones.

### Can I change the sprint length after starting?

Yes. Update `sprint.length_days` in `scraut.yml`. The change takes effect at the next sprint. Ongoing sprint files and dates are not altered.

### Where do I put API keys and secrets?

Never in `scraut.yml`. Always in **Settings → Secrets and variables → Actions** in your GitHub repository. The `slack_webhook` field in `scraut.yml` should always be left empty — use the `SLACK_WEBHOOK` secret.

### Can I use a self-hosted LLM?

Yes. Set `llm.base_url` to any OpenAI-compatible endpoint:

```yaml
llm:
  provider: openai
  model: your-model-name
  base_url: "http://localhost:11434/v1"   # LM Studio, Ollama, etc.
```

See [LLM Providers](./reference/llm-providers) for examples.

---

## Files and data

### What's the difference between `workspace/` and `.scraut/`?

| | `workspace/` | `.scraut/` |
|---|---|---|
| Written by | Humans | Bots (GitHub Actions) |
| Edit manually? | Yes — this is the source of truth | Never — always regenerated |
| Commits by | Team members | Bot with `[skip ci]` |
| Examples | Standup files, retro files, `scraut.yml` | Summaries, reviews, insights |

### Can I edit files in `.scraut/`?

You can, but changes will be overwritten the next time the relevant workflow runs. `.scraut/` is bot-generated output, not a source of truth. If you want to preserve something from `.scraut/`, copy it to `workspace/`.

### What happens to `workspace/` files when I upgrade Scraut?

Nothing. `workspace/` is human-controlled and Scraut automation never deletes or overwrites human-authored files. Upgrades (`git merge upstream/main`) bring in new workflows and scripts without touching your team's data.

---

## Agent Mode

### Do I need Agent Mode?

No. Agent Mode is optional. The full Scrum automation system (standups, planning, retros, milestones, velocity) works entirely without agents. Agents are an enhancement that adds AI team members who claim issues and write code.

### Can I enable one agent without enabling all of them?

Yes. Each agent has its own `enabled` flag:

```yaml
agents:
  enabled: true
  roles:
    - id: agent-backend
      enabled: true
    - id: agent-frontend
      enabled: false   # this one stays off
```

---

## Still stuck?

- Check the [full documentation](https://aldhosutra.github.io/scraut/)
- Open an issue at [github.com/aldhosutra/scraut/issues](https://github.com/aldhosutra/scraut/issues)
