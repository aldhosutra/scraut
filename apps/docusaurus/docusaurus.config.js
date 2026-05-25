// @ts-check
const { themes: prismThemes } = require('prism-react-renderer');
const path = require('path');

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Scraut',
  tagline: 'Fully automated Scrum, built on GitHub. Text files in — automation out.',
  favicon: 'img/favicon.png',

  url: 'https://aldhosutra.github.io',
  baseUrl: '/scraut/',

  organizationName: 'aldhosutra',
  projectName: 'scraut',

  onBrokenLinks: 'warn',

  trailingSlash: false,

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          routeBasePath: '/',
          editUrl: 'https://github.com/aldhosutra/scraut/tree/main/apps/docusaurus/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      image: 'img/scraut-banner.png',
      navbar: {
        title: 'Scraut',
        logo: {
          alt: 'Scraut Logo',
          src: 'img/scraut-logo.png',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'docsSidebar',
            position: 'left',
            label: 'Docs',
          },
          {
            href: 'https://github.com/aldhosutra/scraut',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              { label: 'Getting Started', to: '/getting-started/prerequisites' },
              { label: 'Daily Workflows', to: '/daily-workflows/standup' },
              { label: 'CLI Reference', to: '/reference/cli' },
            ],
          },
          {
            title: 'Community',
            items: [
              { label: 'GitHub Issues', href: 'https://github.com/aldhosutra/scraut/issues' },
              { label: 'GitHub Discussions', href: 'https://github.com/aldhosutra/scraut/discussions' },
            ],
          },
          {
            title: 'More',
            items: [
              { label: 'GitHub', href: 'https://github.com/aldhosutra/scraut' },
              { label: 'NPM (create-scraut)', href: 'https://www.npmjs.com/package/create-scraut' },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Scraut. Built with Docusaurus.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['bash', 'yaml', 'python', 'markdown'],
      },
      colorMode: {
        defaultMode: 'light',
        disableSwitch: false,
        respectPrefersColorScheme: true,
      },
    }),
};

module.exports = config;
