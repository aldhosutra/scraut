"""
scripts/llm/prompts.py
All LLM prompts for Scraut. Import from here — never embed prompts in scripts.
"""

SYSTEM_SCRUM_ASSISTANT = """You are an expert Scrum Master and agile coach.
You have deep knowledge of Scrum, Kanban, and agile methodologies.
You write clearly, concisely, and actionably.
You never use vague language like "consider" or "think about" — you give specific recommendations.
You format output as clean markdown."""

STANDUP_SUMMARY = """
You are generating a team standup summary from individual team member updates.

Today's date: {date}
Sprint: Sprint {sprint_num}
Team: {team_names}

## Individual standup files:
{standup_contents}

## Instructions:
1. Write a concise team standup digest (not longer than 300 words)
2. Summarise WHAT was accomplished yesterday (group similar work)
3. List TODAY's plan by person
4. Highlight ALL blockers prominently at the top if any exist
5. Note if any team member did not submit an update
6. Use plain language — no jargon
7. Format as markdown with clear sections

Output only the markdown. No preamble.
"""

STORY_POINT_ESTIMATE = """
You are estimating the complexity of a GitHub issue using story points.
Use the Fibonacci sequence: 1, 2, 3, 5, 8, 13.

Issue title: {title}
Issue body: {body}
Labels: {labels}

Team's historical context:
- Sprint velocity: {velocity} sp/sprint
- Recent sp:1 examples: {sp1_examples}
- Recent sp:5 examples: {sp5_examples}

Instructions:
- Reply with ONLY a JSON object: {{"estimate": N, "reasoning": "one sentence"}}
- Consider: scope, technical complexity, uncertainty, dependencies
- sp:1 = very small, well-understood change
- sp:3 = moderate, some uncertainty
- sp:5 = significant, some unknowns
- sp:8 = large, considerable uncertainty
- sp:13 = very large or poorly understood — should be broken down
"""

BACKLOG_TRIAGE = """
You are triaging a newly opened GitHub issue for a Scrum team.

Issue: {title}
Body: {body}

Available labels: story, bug, task, spike, chore, p:high, p:medium, p:low

Instructions:
Reply with ONLY a JSON object:
{{
  "type_label": "story|bug|task|spike|chore",
  "priority_label": "p:high|p:medium|p:low",
  "story_point_estimate": N,
  "reasoning": "one sentence justifying the estimate and priority",
  "suggested_acceptance_criteria": ["criterion 1", "criterion 2"]
}}
"""

SPRINT_GOAL_SUGGESTION = """
You are helping a Scrum team set their sprint goal.
Based on the top-priority backlog items, suggest a clear, meaningful sprint goal.

Current sprint: {sprint_num}
Top backlog issues:
{backlog_items}

Team velocity: {velocity} sp/sprint
Previous sprint goal: {prev_goal}

Instructions:
- Suggest 1 sprint goal (one sentence, outcome-focused, not task-focused)
- Suggest which issues should be in this sprint (up to {capacity} sp total)
- Reply with ONLY JSON:
{{
  "suggested_goal": "...",
  "proposed_issues": [123, 456, 789],
  "total_sp": N,
  "rationale": "one sentence"
}}
"""

RETROSPECTIVE_SYNTHESIS = """
You are synthesising individual retrospective entries from team members into a team retrospective summary.

Sprint: Sprint {sprint_num}
Sprint goal: {sprint_goal}
Sprint velocity: {velocity} sp / {planned_sp} sp planned

## Individual entries:
{retro_contents}

## Instructions:
1. "Went well" — group and summarise common themes
2. "Could improve" — group by theme, note frequency
3. "Action items" — extract ALL concrete action items from all entries
4. Add a "Patterns" section if you notice recurring themes from context
5. Be specific — quote specific observations where illuminating
6. Maximum 400 words

Output only the markdown. No preamble.
"""

SPRINT_REVIEW_NARRATIVE = """
You are writing the sprint review narrative for Sprint {sprint_num}.

## Sprint data:
- Goal: {sprint_goal}
- Planned: {planned_sp} story points across {planned_issues} issues
- Completed: {completed_sp} story points across {completed_issues} issues
- Deferred: {deferred_issues}
- Velocity: {velocity} sp (avg last 3 sprints: {avg_velocity})
- CI status: {ci_status}

## What was completed:
{completed_list}

## What was deferred and why:
{deferred_list}

## Key decisions made this sprint:
{decisions}

## Instructions:
Write a sprint review narrative suitable for stakeholders (2–3 paragraphs).
Plain English, no technical jargon, no PR numbers.
Focus on outcomes and value delivered, not tasks completed.
Note what was learned and how it affects the next sprint.

Output only the markdown. No preamble.
"""

MILESTONE_DECOMPOSITION = """
You are decomposing a product milestone into epics, user stories, and technical tasks.

## Milestone:
Title: {title}
Goal: {goal}
Success criteria:
{success_criteria}

Out of scope:
{out_of_scope}

Known risks:
{known_risks}

## Instructions:
Decompose this milestone into a structured breakdown.
Reply with ONLY JSON (no markdown fences):
{{
  "epics": [
    {{
      "id": "E1",
      "title": "Epic title",
      "description": "what this epic covers",
      "estimated_sp_range": [min, max],
      "stories": [
        {{
          "title": "As a [user], I want [action] so that [benefit]",
          "acceptance_criteria": ["criterion 1", "criterion 2"],
          "estimated_sp": N,
          "type": "story|task|spike",
          "depends_on": []
        }}
      ]
    }}
  ],
  "total_sp_range": [min, max],
  "suggested_sprint_count": N,
  "risks": ["risk 1", "risk 2"],
  "confidence": "high|medium|low"
}}
"""

ROADMAP_GENERATION = """
You are generating a sprint-by-sprint roadmap for a milestone.

## Decomposed milestone:
{breakdown}

## Constraints:
- Total sprints: {total_sprints}
- Team capacity: {capacity_per_sprint} sp/sprint
- Priority order: {priority_order}
- Hard deadlines: {hard_deadlines}
- Team: {team_composition}

## Instructions:
Generate a sprint-by-sprint plan. Respect:
1. Story dependencies (don't schedule before dependencies)
2. Team capacity (never exceed capacity_per_sprint per sprint)
3. Include a 10-15% buffer in each sprint for unplanned work
4. Put highest-risk stories early to surface uncertainty

Reply with ONLY JSON:
{{
  "sprints": [
    {{
      "sprint_number": N,
      "theme": "short theme name",
      "stories": [
        {{"title": "...", "sp": N, "epic": "E1", "assignee_type": "backend|frontend|any"}}
      ],
      "total_sp": N,
      "buffer_sp": N,
      "notes": "any special notes for this sprint"
    }}
  ],
  "milestone_sp_total": N,
  "risk_assessment": "paragraph",
  "confidence_interval": {{"p50": N_sprints, "p90": N_sprints}}
}}
"""

SUGGESTION_DRAFT = """
You are drafting an improvement suggestion for a Scrum team based on detected patterns.

## Detected pattern:
Type: {detector_name}
Evidence:
{evidence}

Estimated impact: {estimated_impact}

## Instructions:
Write a concrete, actionable suggestion. Include:
1. A clear title (max 8 words)
2. Why this was flagged (2 sentences referencing the evidence)
3. 2–3 specific action options (Option A recommended, B and C as alternatives)
4. Expected measurable impact for each option
5. How Scraut will auto-measure success in 2 sprints

Reply with ONLY JSON:
{{
  "title": "...",
  "why_flagged": "...",
  "options": [
    {{
      "label": "A",
      "description": "specific action",
      "expected_impact": "metric: X → Y",
      "recommended": true
    }}
  ],
  "measurement_criteria": ["criterion 1", "criterion 2"]
}}
"""

BLOCKER_CLUSTER = """
You are clustering blocker mentions from team standup files by theme.

## Blocker mentions (one per line, format: "sprint|date|person|text"):
{blockers}

## Instructions:
Group these by underlying theme.
Reply with ONLY JSON:
{{
  "clusters": [
    {{
      "theme": "short theme name",
      "instances": [index numbers from the input list],
      "description": "one sentence describing the pattern"
    }}
  ]
}}
"""

HEALTH_REPORT_NARRATIVE = """
You are generating a milestone health report after Sprint {sprint_num} ends.

## Data:
- Milestone: {milestone_title}
- Sprint {sprint_num} of {total_sprints} planned
- Points delivered this sprint: {sprint_delivered_sp}
- Total delivered to date: {total_delivered_sp} of {total_sp} ({percent_done}%)
- Expected at this point: {expected_percent}%
- Board state: {board_state}
- Active blockers: {blockers}
- Agent velocities (if agent mode): {agent_velocities}

## Instructions:
Generate a health report with:
1. One-sentence verdict (on track / watch / at risk)
2. Updated ETA based on current velocity
3. Key risk factors (if any)
4. Specific recommendation (what the team or orchestrator should do now)
Maximum 200 words. Plain English.

Output only the markdown. No preamble.
"""

SENTIMENT_SCORE = """
Rate the overall sentiment/morale of the following standup and retrospective entries.
Score from 1 (very negative/burned out) to 10 (very positive/energised).

## Entries:
{entries}

Reply with ONLY JSON:
{{
  "score": N,
  "signals": ["positive signal 1", "negative signal 1"],
  "concern_level": "none|low|medium|high"
}}
"""
