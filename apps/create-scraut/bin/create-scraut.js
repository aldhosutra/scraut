#!/usr/bin/env node
/**
 * create-scraut — interactive setup wizard for Scraut
 *
 * Usage:
 *   npx create-scraut              — set up in the current directory
 *   npx create-scraut my-team      — clone into ./my-team/ and set up
 *   node apps/create-scraut/bin/create-scraut.js   — same, from within a clone
 *
 * What it does:
 *   1. Clones the Scraut repo (if not already inside one)
 *   2. Asks questions about your team and preferences
 *   3. Writes workspace/scraut.yml
 *   4. Creates the workspace/ and .scraut/ directory skeletons
 *   5. Scaffolds template files so team members see the expected format
 *   6. Creates GitHub labels (if GITHUB_TOKEN env var is set)
 *   7. Prints the secrets checklist and next steps
 */

import inquirer from 'inquirer';
import { Octokit } from '@octokit/rest';
import yaml from 'js-yaml';
import chalk from 'chalk';
import ora from 'ora';
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const SCRAUT_REPO = 'https://github.com/aldhosutra/scraut.git';
const SENTINEL_FILE = '.github/workflows/daily-standup.yml';

// ---------------------------------------------------------------------------
// GitHub label definitions — kept in sync with create_labels.py
// ---------------------------------------------------------------------------
const LABELS = [
  // Story points
  { name: 'sp:1',  color: '0075ca', description: '1 story point' },
  { name: 'sp:2',  color: '0075ca', description: '2 story points' },
  { name: 'sp:3',  color: '0075ca', description: '3 story points' },
  { name: 'sp:5',  color: '0075ca', description: '5 story points' },
  { name: 'sp:8',  color: '0075ca', description: '8 story points' },
  { name: 'sp:13', color: '0075ca', description: '13 story points' },
  // Type
  { name: 'story', color: 'bfd4f2', description: 'User story' },
  { name: 'bug',   color: 'd73a4a', description: "Something isn't working" },
  { name: 'task',  color: 'e4e669', description: 'Technical task' },
  { name: 'spike', color: 'fbca04', description: 'Research/investigation' },
  { name: 'chore', color: 'fef2c0', description: 'Maintenance' },
  // Status
  { name: 'in-sprint',      color: '0052cc', description: 'In current sprint' },
  { name: 'in-review',      color: '5319e7', description: 'Under review' },
  { name: 'blocked',        color: 'b60205', description: 'Blocked by dependency' },
  { name: 'escalate:human', color: 'e11d48', description: 'Needs human intervention' },
  // Priority
  { name: 'p:high',   color: 'b60205', description: 'High priority' },
  { name: 'p:medium', color: 'e4e669', description: 'Medium priority' },
  { name: 'p:low',    color: '0e8a16', description: 'Low priority' },
  // Ceremony
  { name: 'standup',         color: 'c5def5', description: 'Daily standup' },
  { name: 'retrospective',   color: 'bfd4f2', description: 'Sprint retrospective' },
  { name: 'sprint-review',   color: 'd4c5f9', description: 'Sprint review' },
  { name: 'sprint-planning', color: 'f9d0c4', description: 'Sprint planning' },
  // Agent
  { name: 'agent-assigned', color: 'f9ca24', description: 'Assigned to AI agent' },
  { name: 'agent-blocked',  color: 'f0932b', description: 'Agent is blocked' },
  // DoD
  { name: 'dod:pending',  color: 'ffeaa7', description: 'Definition of Done check pending' },
  { name: 'dod:approved', color: '00b894', description: 'Definition of Done approved' },
  // Milestone
  { name: 'milestone-risk', color: 'd63031', description: 'Milestone at risk' },
];

// ---------------------------------------------------------------------------
// Model defaults per provider
// ---------------------------------------------------------------------------
const DEFAULT_MODEL = {
  anthropic: 'claude-sonnet-4-6',
  openai: 'gpt-4o',
  gemini: 'gemini-1.5-pro',
  ollama: 'llama3',
};

const LLM_KEY_NAME = {
  anthropic: 'ANTHROPIC_API_KEY',
  openai: 'OPENAI_API_KEY',
  gemini: 'GOOGLE_API_KEY',
  ollama: '(no key needed)',
};

// ---------------------------------------------------------------------------
// Workspace template content
// ---------------------------------------------------------------------------
function standupTemplate(display, login, sprintNum, today) {
  const nn = String(sprintNum).padStart(2, '0');
  return `# Standup — ${display}
<!--
  Sprint: sprint-${nn}
  Date: ${today}
  Author: ${login}

  ─── NAVIGATION ──────────────────────────────────────────
  📁 Sprint folder:   sprint-${nn}/
  📋 Sprint meta:     sprint-${nn}/meta.md
  📝 Your standup:    sprint-${nn}/standup/${today}/${login}.md
  💬 Retro (when due): sprint-${nn}/retrospective/${login}.md
  🗒️  Backlog ideas:   sprint-${nn}/grooming/backlog-ideas.md
  🏁 Board:           [GitHub Projects - see scraut.yml portal.project_number]
  ─────────────────────────────────────────────────────────
-->

## Yesterday
<!-- What did you complete? Reference issues/PRs where applicable. -->

## Today
<!-- What will you work on today? Reference issues if possible. -->

## Blockers
<!-- Anything blocking your progress? Scraut tracks these automatically. -->
<!-- Write "None" if no blockers. -->
None

## Notes
<!-- Optional: OOO, reduced availability, context for the team -->
`;
}

function retroTemplate(display, sprintNum) {
  const nn = String(sprintNum).padStart(2, '0');
  return `# Retro — ${display} — Sprint ${nn}

## Went well
<!-- What went well this sprint? Be specific. -->

## Could improve
<!-- What would you change? Focus on process, not people. -->

## Action items I'll own
<!-- Personal commitments for next sprint. -->
`;
}

function metaTemplate(teamNames) {
  return `# Sprint 1
- Period: [Set when sprint starts]
- Goal: [Set during sprint planning]
- Team: ${teamNames}
- Committed: TBD story points across TBD issues
- Capacity note: [Check team/capacity.md for OOO]

## Issues in sprint
| Issue | Title | Epic | SP | Assignee |
|-------|-------|------|----|---------|
`;
}

function capacityTemplate(members) {
  const rows = members.map(m => `| ${m.login} | 10 | |`).join('\n');
  return `# Team Capacity — Sprint 1

<!-- Record OOO days, part-time availability, or any capacity reductions.
     Scraut uses this to adjust sprint planning recommendations. -->

| Login | Available Days | Notes |
|-------|---------------|-------|
${rows}
`;
}

const OKR_TEMPLATE = `# Objectives & Key Results

<!-- Define team OKRs here. Scraut references these during sprint planning
     to ensure sprint goals align with strategic objectives. -->

## Objective 1
[Describe what you want to achieve]

### Key Result 1.1
- Target: [Measurable outcome]
- Current: [Current value]

### Key Result 1.2
- Target: [Measurable outcome]
- Current: [Current value]
`;

function customerFeedbackTemplate(today) {
  return `# Customer Feedback

<!-- Record customer feedback, support tickets, user research findings.
     Scraut's backlog grooming agent uses this to suggest story priorities. -->

## Feedback Log

| Date | Source | Summary | Priority | Linked Issue |
|------|--------|---------|----------|-------------|
| ${today} | [Channel/user] | [Summary] | medium | — |

## Themes
<!-- Recurring patterns the team has identified -->

- [Theme 1]: [Description]
`;
}

function milestonesReadmeTemplate(repo) {
  return `# Milestones

<!-- Each milestone gets its own file: milestones/<name>.md
     Scraut's milestone agent reads these to track health and generate forecasts. -->

## Milestone file format

Create \`milestones/v1.0.md\` (or any name) with:

\`\`\`markdown
# Milestone: v1.0
- Due: YYYY-MM-DD
- Goal: [What this release delivers]
- GitHub milestone: https://github.com/${repo}/milestone/1

## Epics
- [ ] Epic: [Name] — [linked issue or description]

## Risks
- [Risk description] — Mitigation: [how you're handling it]

## Definition of Done
- [ ] All committed issues closed
- [ ] Release notes drafted
- [ ] Stakeholders notified
\`\`\`
`;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function writeIfMissing(filePath, content) {
  if (!fs.existsSync(filePath)) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, content);
  }
}

function todayStr() {
  return new Date().toISOString().split('T')[0];
}

function isInsideScrautRepo(dir) {
  return fs.existsSync(path.join(dir, SENTINEL_FILE));
}

function hasGit() {
  try { execSync('git --version', { stdio: 'ignore' }); return true; }
  catch { return false; }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  console.log(chalk.bold('\n  Scraut Setup Wizard\n'));

  // ── Step 1: Resolve target directory ──────────────────────────────────────
  const argDir = process.argv[2];
  let targetDir = process.cwd();
  let cloned = false;

  if (argDir) {
    // User passed a directory name: npx create-scraut my-team
    targetDir = path.resolve(process.cwd(), argDir);
    if (fs.existsSync(targetDir)) {
      console.log(chalk.yellow(`  Directory "${argDir}" already exists — using it as-is.\n`));
    } else {
      if (!hasGit()) {
        console.error(chalk.red('  Error: git is required to clone the Scraut repository.'));
        console.error(chalk.dim('  Install git from https://git-scm.com and try again.'));
        process.exit(1);
      }
      const spinner = ora(`Cloning Scraut into ${argDir}...`).start();
      try {
        execSync(`git clone --depth 1 ${SCRAUT_REPO} "${targetDir}"`, { stdio: 'pipe' });
        spinner.succeed(`Cloned Scraut into ${argDir}/`);
        cloned = true;
      } catch (e) {
        spinner.fail('Clone failed');
        console.error(chalk.red(`  ${e.message}`));
        process.exit(1);
      }
    }
  } else if (!isInsideScrautRepo(targetDir)) {
    // Not in a Scraut repo and no directory given — clone into current dir
    if (!hasGit()) {
      console.error(chalk.red('  Error: git is required to clone the Scraut repository.'));
      console.error(chalk.dim('  Install git from https://git-scm.com and try again.'));
      process.exit(1);
    }
    const cwd = path.basename(targetDir);
    const isEmpty = fs.readdirSync(targetDir).length === 0;

    if (isEmpty) {
      console.log(chalk.dim('  Current directory is empty — cloning Scraut here.\n'));
      const spinner = ora('Cloning Scraut...').start();
      try {
        execSync(`git clone --depth 1 ${SCRAUT_REPO} .`, { cwd: targetDir, stdio: 'pipe' });
        spinner.succeed('Scraut cloned into current directory');
        cloned = true;
      } catch (e) {
        spinner.fail('Clone failed');
        console.error(chalk.red(`  ${e.message}`));
        process.exit(1);
      }
    } else {
      console.log(chalk.yellow('  Not inside a Scraut repository.\n'));
      console.log('  Run one of:');
      console.log(chalk.cyan('    npx create-scraut my-team-name') + chalk.dim('  — creates ./my-team-name/ with Scraut'));
      console.log(chalk.cyan('    mkdir my-team && cd my-team && npx create-scraut') + chalk.dim('  — set up in an empty directory'));
      console.log('');
      process.exit(1);
    }
  }

  // Change into target directory for all subsequent operations
  process.chdir(targetDir);
  const repoRoot = process.cwd();

  if (!cloned) {
    console.log(chalk.dim('  Answers populate workspace/scraut.yml.\n'));
  }

  // ── Step 2: Interactive prompts ──────────────────────────────────────────
  const answers = await inquirer.prompt([
    {
      type: 'input',
      name: 'repo',
      message: 'GitHub repository (org/repo):',
      validate: (v) => v.trim().includes('/') || 'Must be org/repo format (e.g. myorg/my-repo)',
    },
    {
      type: 'input',
      name: 'team',
      message: 'Team member GitHub logins (comma-separated):',
      validate: (v) => v.trim().length > 0 || 'At least one team member required',
    },
    {
      type: 'input',
      name: 'product_owner',
      message: 'Product owner login:',
      validate: (v) => v.trim().length > 0 || 'Required',
    },
    {
      type: 'input',
      name: 'scrum_master',
      message: 'Scrum master login:',
      validate: (v) => v.trim().length > 0 || 'Required',
    },
    {
      type: 'input',
      name: 'slack_channel',
      message: 'Slack channel:',
      default: '#scraut-bot',
    },
    {
      type: 'list',
      name: 'sprint_length',
      message: 'Sprint length:',
      choices: [
        { name: '1 week  (7 days)',  value: 7 },
        { name: '2 weeks (14 days)', value: 14 },
        { name: '3 weeks (21 days)', value: 21 },
      ],
      default: 1,
    },
    {
      type: 'input',
      name: 'timezone',
      message: 'Timezone (IANA format, e.g. UTC, Asia/Jakarta):',
      default: 'UTC',
    },
    {
      type: 'list',
      name: 'llm_provider',
      message: 'LLM provider:',
      choices: ['anthropic', 'openai', 'gemini', 'ollama'],
      default: 0,
    },
    {
      type: 'input',
      name: 'slack_webhook',
      message: 'Slack webhook URL (Enter to skip):',
      default: '',
    },
  ]);

  const logins = answers.team.split(',').map((l) => l.trim()).filter(Boolean);
  const members = logins.map((login) => ({
    login,
    display: login.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    role: 'developer',
    slack_id: '',
    email: '',
  }));

  // ── Step 3: Build config ─────────────────────────────────────────────────
  const config = {
    sprint: {
      length_days: answers.sprint_length,
      start_day: 'monday',
      start_time: '09:00',
      timezone: answers.timezone,
      capacity_buffer: 0.85,
      current_sprint: 1,
    },
    team: {
      members,
      product_owner: answers.product_owner || logins[0] || '',
      scrum_master: answers.scrum_master || logins[0] || '',
      slack_channel: answers.slack_channel,
    },
    ceremonies: {
      planning: true, standup: true, grooming: true,
      review: true, retrospective: true, estimation: true,
    },
    definition_of_done: [
      'Tests written for new functionality',
      'PR reviewed by at least one team member',
      'Acceptance criteria mentioned in PR description',
      'No open review comments',
      'CI passing',
    ],
    repos: [],
    llm: {
      provider: answers.llm_provider,
      model: DEFAULT_MODEL[answers.llm_provider],
      base_url: '',
      max_tokens: 1000,
      cost_controls: { max_daily_tokens: 100000, batch_where_possible: true },
    },
    agents: { enabled: false },
    notifications: {
      slack_webhook: answers.slack_webhook || '',
      morning_dm: true,
      weekly_email: false,
      stakeholder_emails: [],
    },
    portal: {
      enabled: true,
      title: `${answers.repo.split('/')[0]} Dashboard`,
      public: true,
      refresh_minutes: 30,
    },
    suggestions: { enabled: true, min_evidence_count: 3, measurement_sprints: 2 },
    paths: { workspace: 'workspace', scraut: '.scraut', portal: 'apps/portal' },
  };

  // ── Step 4: Write workspace/scraut.yml ───────────────────────────────────
  const spinner = ora('Writing workspace/scraut.yml...').start();
  fs.mkdirSync('workspace', { recursive: true });
  fs.writeFileSync('workspace/scraut.yml', yaml.dump(config, { lineWidth: 120, sortKeys: false }));
  spinner.succeed('workspace/scraut.yml written');

  // ── Step 5: Create directory skeleton ────────────────────────────────────
  spinner.start('Creating directory structure...');
  const workspaceDirs = [
    'workspace/team', 'workspace/okr', 'workspace/customer',
    'workspace/knowledge', 'workspace/milestones',
    'workspace/sprint/01/standup', 'workspace/sprint/01/retrospective',
    'workspace/sprint/01/grooming', 'workspace/sprint/01/decisions', 'workspace/sprint/01/adr',
  ];
  const scrautDirs = [
    '.scraut/sprint/01/standup/summary', '.scraut/sprint/01/review',
    '.scraut/sprint/01/code', '.scraut/sprint/01/incidents',
    '.scraut/insights', '.scraut/milestones',
    '.scraut/suggestions/active', '.scraut/suggestions/implemented', '.scraut/suggestions/resolved',
  ];
  for (const d of workspaceDirs) fs.mkdirSync(d, { recursive: true });
  for (const d of scrautDirs) {
    fs.mkdirSync(d, { recursive: true });
    fs.writeFileSync(path.join(d, '.gitkeep'), '');
  }
  spinner.succeed('workspace/ and .scraut/ structure created');

  // ── Step 6: Scaffold template files ─────────────────────────────────────
  spinner.start('Scaffolding workspace template files...');
  const today = todayStr();
  const teamNames = members.map(m => m.display).join(', ');

  for (const member of members) {
    const standupDir = `workspace/sprint/01/standup/${today}`;
    writeIfMissing(`${standupDir}/${member.login}.md`,
      standupTemplate(member.display, member.login, 1, today));
    writeIfMissing(`workspace/sprint/01/retrospective/${member.login}.md`,
      retroTemplate(member.display, 1));
  }
  writeIfMissing('workspace/sprint/01/meta.md', metaTemplate(teamNames));
  writeIfMissing('workspace/sprint/01/grooming/backlog-ideas.md',
    '# Backlog Ideas\n<!-- Append new ideas below. Anyone can add. -->\n\n');
  writeIfMissing('workspace/team/capacity.md', capacityTemplate(members));
  writeIfMissing('workspace/okr/okr.md', OKR_TEMPLATE);
  writeIfMissing('workspace/customer/feedback.md', customerFeedbackTemplate(today));
  writeIfMissing('workspace/milestones/README.md', milestonesReadmeTemplate(answers.repo));
  spinner.succeed('Workspace template files scaffolded');

  // ── Step 7: GitHub labels ────────────────────────────────────────────────
  const token = process.env.GITHUB_TOKEN;
  if (token && answers.repo !== 'your-org/your-repo') {
    spinner.start(`Creating ${LABELS.length} GitHub labels in ${answers.repo}...`);
    const octokit = new Octokit({ auth: token });
    const [owner, repo] = answers.repo.split('/');
    let created = 0, skipped = 0;
    for (const label of LABELS) {
      try {
        await octokit.rest.issues.createLabel({ owner, repo, ...label });
        created++;
      } catch (e) {
        if (e.status === 422) { skipped++; }
        else { console.error(chalk.yellow(`  Warning: could not create label "${label.name}": ${e.message}`)); }
      }
    }
    spinner.succeed(`GitHub labels: ${created} created, ${skipped} already existed`);
  } else {
    const reason = !token ? 'GITHUB_TOKEN not set' : 'placeholder repo — skipping';
    console.log(chalk.yellow(`\n  Skipping label creation (${reason})`));
    if (token) {
      console.log(chalk.dim('  Run later: python apps/automation/scraut/platform/setup/create_labels.py --repo ' + answers.repo));
    } else {
      console.log(chalk.dim('  Set GITHUB_TOKEN and re-run, or create labels later:'));
      console.log(chalk.dim('  python apps/automation/scraut/platform/setup/create_labels.py --repo ' + answers.repo));
    }
  }

  // ── Step 8: Next steps ───────────────────────────────────────────────────
  const dirNote = argDir ? ` ${argDir}/` : '';
  const llmKey = LLM_KEY_NAME[answers.llm_provider];

  console.log('\n' + chalk.bold('  Done! Next steps:\n'));

  if (cloned) {
    console.log(`  ${chalk.dim('Enter your project directory:')}`);
    console.log(`    cd ${argDir || '.'}\n`);
  }

  console.log('  1. ' + chalk.cyan('Fill in team details in workspace/scraut.yml'));
  console.log(chalk.dim('       Add slack_id and email for each team member.\n'));

  console.log(`  2. ` + chalk.cyan("Fill in today's standup"));
  console.log(chalk.dim(`       workspace/sprint/01/standup/${today}/<login>.md\n`));

  console.log('  3. ' + chalk.cyan('Set GitHub Secrets') + chalk.dim('  (Settings → Secrets → Actions)'));
  console.log(`     [ ] ${llmKey}`);
  console.log('     [ ] SLACK_WEBHOOK');
  console.log('     [ ] SLACK_BOT_TOKEN\n');

  console.log('  4. ' + chalk.cyan('Install the scraut CLI'));
  console.log(chalk.dim('       pip install -r apps/automation/requirements.txt\n'));

  console.log('  5. ' + chalk.cyan('Enable GitHub Actions') + chalk.dim('  (Settings → Actions → General)'));
  console.log(chalk.dim('       Allow all actions + Read and write permissions\n'));

  console.log('  6. ' + chalk.cyan('Enable GitHub Pages') + chalk.dim('  (Settings → Pages → Branch: main, Folder: /docs)\n'));

  console.log('  7. ' + chalk.cyan('Commit and push'));
  console.log(chalk.dim("       git add . && git commit -m 'chore: scraut setup [skip ci]' && git push\n"));

  console.log('  8. ' + chalk.cyan('Trigger sprint-planning') + chalk.dim(' from the GitHub Actions UI'));
  console.log('');
  console.log(chalk.dim('  Full docs: https://aldhosutra.github.io/scraut/'));
  console.log('');
}

main().catch((e) => { console.error(chalk.red('\n  Error: ' + e.message)); process.exit(1); });
