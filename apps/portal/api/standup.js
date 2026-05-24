/**
 * Serverless edge function: receives standup form submission,
 * writes to GitHub repo via Contents API.
 * Deploy to Vercel or Netlify Functions.
 *
 * Required environment variables:
 *   GITHUB_TOKEN  — scoped write token for the Scraut repo
 *   SCRAUT_REPO   — org/repo of the Scraut repository
 *   PORTAL_TOKEN  — simple shared secret to prevent abuse
 */

export default async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { login, yesterday, today, blockers, date } = req.body;

  if (!login || !yesterday || !today || !date) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  // Build standup markdown content
  const content = `# Standup — ${login}
<!--
  Sprint: auto-detected
  Date: ${date}
  Author: ${login}
  Submitted via: web form
-->

## Yesterday
${yesterday}

## Today
${today}

## Blockers
${blockers || 'None'}

## Notes
_Submitted via Scraut web form_
`;

  // Encode for GitHub API
  const encoded = Buffer.from(content).toString('base64');

  // Determine current sprint from scraut.yml (simplified: use date math)
  // In production, fetch scraut.yml from repo and parse current_sprint
  const sprintNum = '01'; // TODO: fetch from scraut.yml

  const filePath = `workspace/sprint/${sprintNum}/standup/${date}/${login}.md`;
  const apiUrl = `https://api.github.com/repos/${process.env.SCRAUT_REPO}/contents/${filePath}`;

  try {
    // Check if file exists (to get SHA for update)
    let sha = undefined;
    const checkResp = await fetch(apiUrl, {
      headers: {
        Authorization: `token ${process.env.GITHUB_TOKEN}`,
        Accept: 'application/vnd.github.v3+json',
      },
    });
    if (checkResp.ok) {
      const existing = await checkResp.json();
      sha = existing.sha;
    }

    // Create or update file
    const body = {
      message: `standup: ${login} ${date} [skip ci]`,
      content: encoded,
      branch: 'main',
    };
    if (sha) body.sha = sha;

    const writeResp = await fetch(apiUrl, {
      method: 'PUT',
      headers: {
        Authorization: `token ${process.env.GITHUB_TOKEN}`,
        Accept: 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!writeResp.ok) {
      const err = await writeResp.text();
      throw new Error(`GitHub API error: ${err}`);
    }

    return res.status(200).json({ success: true, file: filePath });
  } catch (err) {
    console.error('Standup submission error:', err);
    return res.status(500).json({ error: err.message });
  }
}
