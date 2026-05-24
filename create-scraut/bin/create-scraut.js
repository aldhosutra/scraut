#!/usr/bin/env node
/**
 * create-scraut — interactive setup wizard for Scraut
 *
 * Usage (from the cloned Scraut repo root):
 *   node create-scraut/bin/create-scraut.js
 *
 * Or, after publishing to npm:
 *   npx create-scraut
 *
 * What it does:
 *   1. Asks 8 questions about your team and preferences
 *   2. Writes workspace/scraut.yml
 *   3. Creates the workspace/ and .scraut/ directory skeletons
 *   4. Creates GitHub labels (if GITHUB_TOKEN env var is set)
 *   5. Prints the secrets checklist and next steps
 */

import inquirer from 'inquirer';
import { Octokit } from '@octokit/rest';
import yaml from 'js-yaml';
import chalk from 'chalk';
import ora from 'ora';
import fs from 'fs';
import path from 'path';

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
// Main
// ---------------------------------------------------------------------------
async function main() {
  console.log(chalk.bold('\n  Scraut Setup Wizard\n'));
  console.log(chalk.dim('  Answers populate workspace/scraut.yml.\n'));

  const answers = await inquirer.prompt([
    {
      type: 'input',
      name: 'repo',
      message: 'GitHub repository (org/repo):',
      validate: (v) => v.includes('/') || 'Must be org/repo format',
    },
    {
      type: 'input',
      name: 'team',
      message: 'Team member GitHub logins (comma-separated):',
      validate: (v) => v.trim().length > 0 || 'At least one team member required',
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
      name: 'slack_channel',
      message: 'Slack channel:',
      default: '#scraut-bot',
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

  // Build config object
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
      product_owner: logins[0] || '',
      scrum_master: logins[0] || '',
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

  // Write workspace/scraut.yml
  const spinner = ora('Writing workspace/scraut.yml...').start();
  fs.mkdirSync('workspace', { recursive: true });
  fs.writeFileSync('workspace/scraut.yml', yaml.dump(config, { lineWidth: 120, sortKeys: false }));
  spinner.succeed('workspace/scraut.yml written');

  // Create workspace directory skeleton
  spinner.start('Creating workspace/ directory structure...');
  const workspaceDirs = [
    'workspace/team',
    'workspace/okr',
    'workspace/customer',
    'workspace/knowledge',
    'workspace/milestones',
    'workspace/sprint/01/standup',
    'workspace/sprint/01/retrospective',
    'workspace/sprint/01/grooming',
    'workspace/sprint/01/decisions',
    'workspace/sprint/01/adr',
  ];
  const scrautDirs = [
    '.scraut/sprint/01/standup/summary',
    '.scraut/sprint/01/review',
    '.scraut/sprint/01/code',
    '.scraut/sprint/01/incidents',
    '.scraut/insights',
    '.scraut/milestones',
    '.scraut/suggestions/active',
    '.scraut/suggestions/implemented',
    '.scraut/suggestions/resolved',
  ];
  for (const d of [...workspaceDirs, ...scrautDirs]) {
    fs.mkdirSync(d, { recursive: true });
    fs.writeFileSync(path.join(d, '.gitkeep'), '');
  }
  spinner.succeed('workspace/ and .scraut/ directory structure created');

  // Create GitHub labels (if GITHUB_TOKEN is available)
  const token = process.env.GITHUB_TOKEN;
  if (token) {
    spinner.start(`Creating ${LABELS.length} GitHub labels in ${answers.repo}...`);
    const octokit = new Octokit({ auth: token });
    const [owner, repo] = answers.repo.split('/');
    let created = 0;
    let skipped = 0;
    for (const label of LABELS) {
      try {
        await octokit.rest.issues.createLabel({ owner, repo, ...label });
        created++;
      } catch (e) {
        if (e.status === 422) { skipped++; }  // already exists
        else { console.error(`  Warning: could not create label "${label.name}": ${e.message}`); }
      }
    }
    spinner.succeed(`GitHub labels: ${created} created, ${skipped} already existed`);
  } else {
    console.log(chalk.yellow('\n  Skipping label creation (GITHUB_TOKEN not set)'));
    console.log(chalk.dim('  Run later: python apps/automation/scraut/platform/setup/create_labels.py --repo ' + answers.repo));
  }

  // Print checklist
  const llmKey = LLM_KEY_NAME[answers.llm_provider];
  console.log('\n' + chalk.bold('  Done! Next steps:\n'));
  console.log('  1. ' + chalk.cyan('Edit workspace/scraut.yml'));
  console.log(chalk.dim('       Fill in slack_id and email for each team member.\n'));
  console.log('  2. ' + chalk.cyan('Set GitHub Secrets') + chalk.dim('  (Settings → Secrets → Actions)'));
  console.log(`     [ ] ${llmKey}`);
  console.log('     [ ] SLACK_WEBHOOK');
  console.log('     [ ] SLACK_BOT_TOKEN\n');
  console.log('  3. ' + chalk.cyan('Install the scraut CLI'));
  console.log(chalk.dim('       pip install -r apps/automation/requirements.txt\n'));
  console.log('  4. ' + chalk.cyan('Create Sprint 1'));
  console.log(chalk.dim(`       python apps/automation/scraut/scrum/sprint/create_sprint.py --sprint 1 --repo ${answers.repo}\n`));
  console.log('  5. ' + chalk.cyan('Commit and push'));
  console.log(chalk.dim("       git add . && git commit -m 'chore: scraut setup [skip ci]' && git push\n"));
  console.log('  6. ' + chalk.cyan('Trigger sprint-planning') + chalk.dim(' from GitHub Actions UI'));
  console.log('');
}

main().catch((e) => { console.error(e); process.exit(1); });
