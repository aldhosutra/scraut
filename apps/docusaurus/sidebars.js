// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    {
      type: 'doc',
      id: 'intro',
      label: 'What is Scraut?',
    },
    {
      type: 'category',
      label: 'Getting Started',
      collapsed: false,
      items: [
        'getting-started/prerequisites',
        'getting-started/installation',
        'getting-started/configuration',
        'getting-started/github-setup',
        'getting-started/first-sprint',
      ],
    },
    {
      type: 'category',
      label: 'Daily Workflows',
      items: [
        'daily-workflows/morning-routine',
        'daily-workflows/standup',
        'daily-workflows/status',
        'daily-workflows/blockers',
      ],
    },
    {
      type: 'category',
      label: 'Scrum Ceremonies',
      items: [
        'ceremonies/sprint-planning',
        'ceremonies/sprint-review',
        'ceremonies/retrospective',
        'ceremonies/backlog-grooming',
        'ceremonies/estimation',
      ],
    },
    {
      type: 'category',
      label: 'Features',
      items: [
        'features/velocity',
        'features/milestones',
        'features/definition-of-done',
        'features/issue-triage',
        'features/visibility-portal',
        'features/suggestions',
        'features/notifications',
        'features/repo-sync',
        'features/incidents',
        'features/weekly-digest',
      ],
    },
    {
      type: 'category',
      label: 'Agent Mode',
      items: [
        'agent-mode/overview',
        'agent-mode/roles',
        'agent-mode/autonomy-levels',
        'agent-mode/human-checkpoints',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'reference/cli',
        'reference/configuration',
        'reference/team-roles',
        'reference/workflows',
        'reference/file-structure',
        'reference/llm-providers',
        'reference/labels',
      ],
    },
    {
      type: 'doc',
      id: 'faq',
      label: 'FAQ',
    },
  ],
};

module.exports = sidebars;
