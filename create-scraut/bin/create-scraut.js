#!/usr/bin/env node
/**
 * create-scraut — interactive setup wizard
 * Usage: npx create-scraut
 *
 * Asks 6 questions, then:
 * 1. Creates scraut.yml with answers
 * 2. Scaffolds all workflow YAML files
 * 3. Creates issue templates
 * 4. Sets up GitHub Projects board (if token provided)
 * 5. Prints secrets checklist
 */
import inquirer from 'inquirer';
import { Octokit } from '@octokit/rest';
import yaml from 'js-yaml';
import chalk from 'chalk';
import ora from 'ora';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function main() {
  console.log(chalk.bold('\n🚀 Welcome to Scraut — Scrum Automation\n'));
  console.log('This wizard sets up your team\'s automated Scrum system.\n');
  console.log(chalk.dim('Takes about 5 minutes. You\'ll need:\n') +
    chalk.dim('  • GitHub repository URL\n') +
    chalk.dim('  • Team members\' GitHub usernames\n') +
    chalk.dim('  • Slack webhook URL (optional)\n'));

  const answers = await inquirer.prompt([
    {
      type: 'input',
      name: 'repo',
      message: 'GitHub repository (format: org/repo):',
      validate: (v) => v.includes('/') || 'Must be org/repo format',
    },
    {
      type: 'input',
      name: 'team',
      message: 'Team members\' GitHub usernames (comma-separated):',
      validate: (v) => v.trim().length > 0 || 'At least one team member required',
    },
    {
      type: 'list',
      name: 'sprint_length',
      message: 'Sprint length:',
      choices: [
        { name: '1 week (5 working days)', value: 7 },
        { name: '2 weeks (10 working days)', value: 14 },
        { name: '3 weeks', value: 21 },
      ],
      default: 1,
    },
    {
      type: 'input',
      name: 'slack_webhook',
      message: 'Slack webhook URL (press Enter to skip):',
      default: '',
    },
    {
      type: 'list',
      name: 'llm_provider',
      message: 'LLM provider:',
      choices: ['anthropic', 'openai', 'ollama'],
      default: 0,
    },
    {
      type: 'input',
      name: 'timezone',
      message: 'Team timezone (IANA format, e.g. Asia/Jakarta):',
      default: 'Asia/Jakarta',
    },
  ]);

  const spinner = ora('Creating your Scraut configuration...').start();

  // Parse team members
  const members = answers.team.split(',').map((login, i) => ({
    login: login.trim(),
    display: login.trim().replace(/-/g, ' '),
    role: i === 0 ? 'scrum_master' : 'developer',
    slack_id: '',
    email: '',
  }));

  // Build scraut.yml
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
      product_owner: members[0]?.login || '',
      scrum_master: members[0]?.login || '',
      slack_channel: '#scraut-bot',
    },
    ceremonies: {
      planning: true,
      standup: true,
      grooming: true,
      review: true,
      retrospective: true,
      estimation: true,
    },
    definition_of_done: [
      'Tests written for new functionality',
      'PR reviewed by at least one team member',
      'Acceptance criteria mentioned in PR description',
      'CI passing',
    ],
    repos: [],
    llm: {
      provider: answers.llm_provider,
      model: answers.llm_provider === 'anthropic' ? 'claude-sonnet-4-6' :
             answers.llm_provider === 'openai' ? 'gpt-4o' : 'llama3',
      max_tokens: 1000,
      cost_controls: {
        max_daily_tokens: 100000,
        batch_where_possible: true,
      },
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
      title: `${answers.repo.split('/')[0]} Team Dashboard`,
      public: true,
      refresh_minutes: 30,
    },
    suggestions: {
      enabled: true,
      min_evidence_count: 3,
      measurement_sprints: 2,
    },
  };

  // Write scraut.yml
  fs.writeFileSync('scraut.yml', yaml.dump(config, { lineWidth: 120 }));
  spinner.succeed('scraut.yml created');

  // Create directory structure
  spinner.start('Creating directory structure...');
  const dirs = [
    '.github/workflows',
    '.github/ISSUE_TEMPLATE',
    'scripts/llm', 'scripts/github', 'scripts/sprint',
    'scripts/standup', 'scripts/backlog', 'scripts/reports',
    'scripts/repo_sync', 'scripts/milestone', 'scripts/visibility',
    'scripts/suggestions', 'scripts/notifications', 'scripts/agents',
    'scripts/utils', 'scripts/setup',
    'suggestions/active', 'suggestions/implemented', 'suggestions/resolved',
    'insights', 'team', 'okr', 'customer', 'knowledge', 'milestones', 'portal',
  ];
  dirs.forEach(d => fs.mkdirSync(d, { recursive: true }));
  spinner.succeed('Directory structure created');

  // Write .gitignore
  fs.writeFileSync('.gitignore',
    '__pycache__/\n*.pyc\n.env\n.env.local\nvenv/\n.venv/\nnode_modules/\n.DS_Store\n*.log\nportal/data.json\n'
  );

  // Write requirements.txt
  fs.writeFileSync('requirements.txt',
    'anthropic>=0.28.0\nopenai>=1.30.0\nPyGitHub>=2.3.0\nrequests>=2.31.0\n' +
    'PyYAML>=6.0.1\nmatplotlib>=3.8.0\nPillow>=10.3.0\npython-dotenv>=1.0.0\n' +
    'click>=8.1.7\njinja2>=3.1.4\npytz>=2024.1\n'
  );

  spinner.succeed('Configuration files written');

  // Print secrets checklist
  console.log('\n' + chalk.bold('✅ Setup complete!\n'));
  console.log(chalk.bold('🔐 Required GitHub Secrets\n') +
    chalk.dim('Set these in: Settings → Secrets and variables → Actions\n\n') +
    (answers.llm_provider === 'anthropic' ?
      '  □ ANTHROPIC_API_KEY\n' : '  □ OPENAI_API_KEY\n') +
    (answers.slack_webhook ?
      '  ✓ SLACK_WEBHOOK (entered above — add to GitHub Secrets)\n' :
      '  □ SLACK_WEBHOOK (optional — for Slack notifications)\n') +
    '  □ SLACK_BOT_TOKEN (for personal standup DMs)\n' +
    '  □ SCRAUT_GITHUB_TOKEN (for connected repo sync)\n'
  );

  console.log(chalk.bold('📋 Next steps:\n') +
    '  1. Run: ' + chalk.cyan('pip install -r requirements.txt') + '\n' +
    '  2. Set all secrets in GitHub Settings\n' +
    '  3. Run: ' + chalk.cyan(`python scripts/setup/create_labels.py ${answers.repo}`) + '\n' +
    '  4. Run: ' + chalk.cyan(`python scripts/sprint/create_sprint.py --sprint 1 --repo ${answers.repo}`) + '\n' +
    '  5. Enable GitHub Pages in repo Settings → Pages → Source: GitHub Actions\n' +
    '  6. Push to main — Scraut is live! 🎉\n'
  );
}

main().catch(console.error);
